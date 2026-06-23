# SPDX-License-Identifier: MIT
"""``ztare`` — the zero-trust workbench's public CLI.

A thin entry point that wraps the existing public control scripts under
``scripts/public/control/`` so the workbench is callable as a single
command instead of ``cd repo && python scripts/public/control/<name>.py``.

**Scope of this CLI.** ZTARE the workbench, not the maintainer's tenant
overlay. The subcommands cover the zero-trust kernel —
forecast pool, LeanMill, bundle gates, project charter, RD routine
review, action intelligence, project setup — and the project research-side
operations. The governance / org side (roles, mandates, role daemons,
closure daemons, OKR-tree polling) belongs to ``cognitive-firm`` and is
deliberately *not* exposed here; maintainers who want those primitives
should use the sibling ``cognitive-firm`` repository alongside ZTARE.

Design notes:

- Stdlib-only (``argparse`` + ``subprocess``). No new runtime deps.
- Subprocess delegation preserves each underlying script's full
  argument surface; pass ``--help`` to any subcommand to see what the
  underlying script accepts (e.g. ``ztare forecast --help``).
- The CLI assumes a ZTARE checkout is the working directory (the
  scripts read ledgers by relative path). Repo-root detection walks up
  from the current file location and falls back to the cwd; set
  ``ZTARE_REPO`` to override.

Current subcommands cover forecast, LeanMill, sealed bundles, charters,
routine review, action intelligence, eigenquestions, reflexive mining,
autoresearch, project setup, primitive health, audits, architecture
validation, and the self-describing ``version``, ``doctor``, and
``completion``. Add new subcommands by extending ``_SUBCOMMANDS`` and writing
a thin handler that delegates to a control script, module, or Make target.
"""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Callable, Iterable


# ---------------------------------------------------------------------------
# Repo / script-root discovery
# ---------------------------------------------------------------------------

_THIS_FILE = Path(__file__).resolve()


def _repo_root() -> Path:
    """Find the repo root containing ``scripts/public/control/``.

    Walks up from this file's location; falls back to the current
    working directory so a ``pip install -e .`` checkout still works.
    """
    env_root = os.environ.get("ZTARE_REPO")
    if env_root:
        root = Path(env_root).resolve()
        if (root / "scripts" / "public" / "control").is_dir():
            return root
    for parent in [_THIS_FILE, *_THIS_FILE.parents]:
        if (parent / "scripts" / "public" / "control").is_dir():
            return parent
    cwd = Path.cwd()
    if (cwd / "scripts" / "public" / "control").is_dir():
        return cwd
    raise RuntimeError(
        "ztare: cannot locate the repository root with "
        "`scripts/public/control/` — invoke the CLI from a ZTARE "
        "checkout, or set ZTARE_REPO to point at one."
    )


def _control_script(name: str) -> Path:
    """Return the absolute path to a control script, asserting it exists."""
    path = _repo_root() / "scripts" / "public" / "control" / name
    if not path.is_file():
        raise SystemExit(
            f"ztare: control script not found: {path}\n"
            "If you renamed or moved it, update the CLI dispatch table."
        )
    return path


def _delegate(script_name: str, args: Iterable[str]) -> int:
    """Run a control script with the given args; return its exit code."""
    script = _control_script(script_name)
    argv = [sys.executable, str(script), *args]
    sys.stdout.flush()
    sys.stderr.flush()
    completed = subprocess.run(argv, check=False)
    return completed.returncode


# ---------------------------------------------------------------------------
# Verb router factory (used by subcommands with verb-style sub-dispatch)
# ---------------------------------------------------------------------------


def _make_verb_router(name: str, verb_map: dict[str, str]) -> Callable[[list[str]], int]:
    """Build a router that dispatches ``ztare <name> <verb> [args...]`` to
    the script named in ``verb_map``. Returns a handler suitable for
    insertion into ``_SUBCOMMANDS``.

    The router prints its own help when called with no verb or
    ``-h`` / ``--help``, listing every known verb and the script it
    targets.
    """

    def router(rest: list[str]) -> int:
        if not rest or rest[0] in ("-h", "--help"):
            print(f"ztare {name} <verb> [args...]\n\nVerbs:")
            width = max(len(v) for v in verb_map) + 2
            for verb, script in verb_map.items():
                print(f"  {verb:<{width}}→ scripts/public/control/{script}")
            print(f"\nFor any verb's own --help, run:\n  ztare {name} <verb> --help")
            return 0
        verb, *args = rest
        script = verb_map.get(verb)
        if not script:
            print(
                f"ztare: unknown {name} verb {verb!r}. "
                f"Known: {', '.join(verb_map)}",
                file=sys.stderr,
            )
            return 2
        return _delegate(script, args)

    return router


# `ztare forecast <verb>` — verb router over the forecast control surface.
# Mixed delegation: reusable control scripts under scripts/public/control/,
# project-local experiment tools, and registered console-script modules under
# `ztare.forecasting`. Each tuple is (kind, target):
#   ("control", "<name>.py")        → scripts/public/control/<name>.py
#   ("script",  "<rel/path.py>")    → <repo_root>/<rel/path.py>
#   ("module",  "<dotted.path>")    → python -m <dotted.path>
_FORECAST_VERBS: dict[str, tuple[str, str]] = {
    "pool":              ("control", "forecast/pool.py"),
    "resolve":           ("control", "forecast/resolve_from_json.py"),
    "capability-audit":  ("module",  "ztare.reports.forecast_capability_audit"),
    "calibration-stats": ("module",  "ztare.forecasting.calibration_stats"),
    "calibration-db":    ("module",  "ztare.forecasting.calibration_db"),
    "score":             ("control", "forecast/score_prediction_ledger_calibration.py"),
    "ingest-smoke":      ("control", "forecast/ingest_smoke_jsonl.py"),
    "cutoff-panel-run": ("script", "projects/llm_forecasting_calibration_program/tools/cutoff_stage_b_dispatch_runner.py"),
    "cutoff-panel-ingest": ("script", "projects/llm_forecasting_calibration_program/tools/cutoff_stage_b_ingest_calls.py"),
    "cutoff-panel-score": ("script", "projects/llm_forecasting_calibration_program/tools/cutoff_stage_b_score.py"),
    "anti-bias-run":    ("script", "projects/llm_forecasting_calibration_program/tools/anti_bias_collapse_dispatch_runner.py"),
    "anti-bias-score":  ("script", "projects/llm_forecasting_calibration_program/tools/anti_bias_collapse_score.py"),
    "nurture-run":      ("script", "projects/llm_forecasting_calibration_program/tools/nurture_intervention_dispatch_runner.py"),
    "nurture-ingest":   ("script", "projects/llm_forecasting_calibration_program/tools/nurture_intervention_ingest.py"),
    "nurture-score":    ("script", "projects/llm_forecasting_calibration_program/tools/nurture_intervention_score.py"),
    "f47-freeze-packet": ("script", "projects/llm_forecasting_calibration_program/tools/f47_prospective_market_freeze_packet.py"),
    "f47-run":          ("script", "projects/llm_forecasting_calibration_program/tools/f47_source_balanced_consumer_dispatch.py"),
    "f47-score":        ("script", "projects/llm_forecasting_calibration_program/tools/f47_source_balanced_consumer_score.py"),
    "f47-external-bars": ("script", "projects/llm_forecasting_calibration_program/tools/f47_external_bar_score.py"),
    "f47-prospective-score": ("script", "projects/llm_forecasting_calibration_program/tools/f47_prospective_market_freeze_score.py"),
    "f47-production-readiness": ("script", "projects/llm_forecasting_calibration_program/tools/f47_production_readiness_audit.py"),
    "fred-pre-companion": ("script", "projects/llm_forecasting_calibration_program/tools/fred_pre_cutoff_companion_manifest.py"),
    "fred-pair-packet": ("script", "projects/llm_forecasting_calibration_program/tools/fred_cutoff_pair_dispatch_packet.py"),
    "fred-pair-score": ("script", "projects/llm_forecasting_calibration_program/tools/fred_cutoff_pair_score.py"),
    "fred-blind-value-packet": ("script", "projects/llm_forecasting_calibration_program/tools/fred_blinded_value_control_packet.py"),
    "fred-ingest": ("script", "projects/llm_forecasting_calibration_program/tools/fred_ingest_workspace_results.py"),
    "fred-vintage-audit": ("script", "projects/llm_forecasting_calibration_program/tools/fred_vintage_timing_audit.py"),
    "fred-vintage-bulk-repair": ("script", "projects/llm_forecasting_calibration_program/tools/fred_vintage_bulk_repair.py"),
    "fred-vintage-rescore": ("script", "projects/llm_forecasting_calibration_program/tools/fred_vintage_rescore.py"),
    "dataset-label-time-gate": ("script", "projects/llm_forecasting_calibration_program/tools/dataset_label_time_gate.py"),
    "source-currency-gate": ("script", "projects/llm_forecasting_calibration_program/tools/source_currency_gate.py"),
    "paper-readiness-audit": ("script", "projects/llm_forecasting_calibration_program/tools/paper_readiness_exhaustion_audit.py"),
    "equal-info-acquisition": ("script", "projects/llm_forecasting_calibration_program/tools/equal_information_baseline_acquisition_run.py"),
    "equal-info-export-packet": ("script", "projects/llm_forecasting_calibration_program/tools/equal_information_baseline_export_packet.py"),
    "equal-info-result-ingest": ("script", "projects/llm_forecasting_calibration_program/tools/equal_information_baseline_result_ingest.py"),
    "elo-refresh":       ("control", "forecast/compute_elo_by_corpus.py"),
    "brier-elo":         ("control", "forecast/brier_elo_report.py"),
    "resolve-open-metaculus": ("control", "forecast/resolve_open_metaculus.py"),
}


def _cmd_forecast_router(rest: list[str]) -> int:
    if not rest or rest[0] in ("-h", "--help"):
        print("ztare forecast <verb> [args...]\n\nVerbs:")
        width = max(len(v) for v in _FORECAST_VERBS) + 2
        for verb, (kind, target) in _FORECAST_VERBS.items():
            shown = _forecast_help_target_label(kind, target)
            print(f"  {verb:<{width}}→ {shown}")
        print("\nFor any verb's own --help, run:\n  ztare forecast <verb> --help")
        print("Run `ztare doctor` for exact target-resolution paths.")
        return 0
    verb, *args = rest
    entry = _FORECAST_VERBS.get(verb)
    if entry is None:
        print(
            f"ztare: unknown forecast verb {verb!r}. "
            f"Known: {', '.join(_FORECAST_VERBS)}",
            file=sys.stderr,
        )
        return 2
    kind, target = entry
    if kind == "control":
        return _delegate(target, args)
    if kind == "script":
        return _delegate_script(target, args)
    if kind == "module":
        return _delegate_module(target, args)
    print(f"ztare: bug — unknown forecast verb kind {kind!r}", file=sys.stderr)
    return 1


def _forecast_help_target_label(kind: str, target: str) -> str:
    if kind == "control":
        return f"public control: scripts/public/control/{target}"
    if kind == "module":
        return f"package module: python -m {target}"
    if kind == "script":
        return f"project tool: {Path(target).name}"
    return f"{kind}: {target}"


_LEANMILL_VERBS: dict[str, str] = {
    # control plane
    "schedule":    "leanmill/station_scheduler.py",
    "run":         "leanmill/24x7_runner.py",
    "andon":       "leanmill/andon_cord.py",
    "triage":      "leanmill/post_probe_triage.py",
    "backlog":     "leanmill/backlog_replenisher.py",
    # supervisor + lifecycle
    "watchdog":    "leanmill/watchdog.py",
    "shutdown":    "leanmill/shutdown.py",
    "restart-gate": "leanmill/restart_gate.py",
    # corpus + sourcing
    "mandate":     "leanmill/corpus_mandate_registry.py",
    "source-scout":"leanmill/source_scout_worker.py",
    "source-search":"leanmill/source_search_worker.py",
    "source-review":"leanmill/source_review_worker.py",
    "source-bind": "leanmill/source_binding_probe_worker.py",
    # families + probes
    "family-gate": "leanmill/family_spec_gate.py",
    "family-birth":"leanmill/family_birth_miner.py",
    "seeder":      "leanmill/learning_work_seeder.py",
    "probe":       "leanmill/probe_worker.py",
    # solver (Lane A direct attack)
    "solver":      "leanmill/solver_lane_worker.py",
    "slice-prep":  "leanmill/c_discriminating_slice_prep.py",
    "slice-emit":  "leanmill/emit_spectral_apn_solver_slice.py",
    "apn-candidates": "leanmill/emit_apn_lane_b_candidates.py",
    # Canonical name: `external-proof-audit` (batch audit of pre-cooked
    # external Lean proofs through the L1+L2+L3 stack). `lane-b-audit`
    # kept as a legacy alias for existing scripts.
    "external-proof-audit": "leanmill/external_proof_audit.py",
    "lane-b-audit":   "leanmill/external_proof_audit.py",
    # `proof-audit` is the GENERAL canonical L1+L2+L3 audit (compile +
    # axiom_allowlist + L3 anti-pattern gates from v33_*). Takes --target
    # for any Lean file; consumed by every audit lane (Lane B / future
    # Erdős / OEIS / NS Track B heldout).
    "proof-audit":    "leanmill/proof_audit.py",
    # governance + audit (Lane B)
    "governance":  "leanmill/governance_worker.py",
    "infra-gate":  "leanmill/infra_freeze_gate.py",
    "heldout-gate":"leanmill/heldout_receipt_gate.py",
    "harness":     "leanmill/evaluation_harness_runner.py",
    # read-models + intel
    "ui-state":    "leanmill/ui_state_dump.py",
    "corpus":      "leanmill/external_corpus_ingest.py",
    "intel":       "leanmill/factory_intelligence.py",
    "credit":      "leanmill/c_supply_credit.py",
    "growth":      "leanmill/c_supply_growth_controller.py",
    "convert":     "leanmill/c_supply_conversion_prioritizer.py",
}

_BUNDLE_VERBS: dict[str, str] = {
    "run": "bundle_run.py",
    "verify": "bundle_verify.py",
}

_cmd_leanmill_router = _make_verb_router("leanmill", _LEANMILL_VERBS)


_cmd_bundle_router = _make_verb_router("bundle", _BUNDLE_VERBS)


# ---------------------------------------------------------------------------
# Thin shells over Python modules / scripts / Make targets.
# Discipline: do not reimplement what the Makefile or a script already does.
# The CLI is a catalog over those entry points for the public workbench.
# ---------------------------------------------------------------------------


def _run_subprocess(argv: list[str], cwd: Path | None = None, env: dict[str, str] | None = None) -> int:
    """Run a subprocess, returning its exit code. Centralizes the stdout/err
    flush + the cwd handling for the Make / module shells below."""
    sys.stdout.flush()
    sys.stderr.flush()
    completed = subprocess.run(argv, cwd=cwd, check=False, env=env)
    return completed.returncode


def _delegate_module(module: str, args: Iterable[str]) -> int:
    """Run `python -m <module> [args]` from the repo root. Used for modules
    that already have a CLI but are not under scripts/public/control/."""
    root = _repo_root()
    argv = [sys.executable, "-m", module, *args]
    env = os.environ.copy()
    src_path = str(root / "src")
    env["PYTHONPATH"] = (
        src_path
        if not env.get("PYTHONPATH")
        else f"{src_path}{os.pathsep}{env['PYTHONPATH']}"
    )
    return _run_subprocess(argv, cwd=root, env=env)


def _delegate_script(rel_path: str, args: Iterable[str]) -> int:
    """Run `python <repo_root>/<rel_path> [args]`. Used for scripts that
    sit outside scripts/public/control/."""
    root = _repo_root()
    script = root / rel_path
    if not script.is_file():
        raise SystemExit(
            f"ztare: script not found: {script}\n"
            "If you renamed or moved it, update the CLI dispatch table."
        )
    argv = [sys.executable, str(script), *args]
    return _run_subprocess(argv, cwd=root)


def _delegate_make(target: str, vars_: dict[str, str], extra_args: Iterable[str] = ()) -> int:
    """Run `make <target> KEY=VALUE ...` from the repo root. Used for
    pipeline orchestrators where the Makefile is the canonical definition;
    the CLI provides only a stable, discoverable invocation surface."""
    root = _repo_root()
    argv = ["make", target]
    for k, v in vars_.items():
        if v is not None and v != "":
            argv.append(f"{k}={v}")
    argv.extend(extra_args)
    return _run_subprocess(argv, cwd=root)


_SAFE_ROUTE_ID = re.compile(r"[^A-Za-z0-9_.-]+")


def _safe_route_id(value: str) -> str:
    cleaned = _SAFE_ROUTE_ID.sub("_", value.strip()).strip("._-")
    return cleaned or "decision"


def _load_action_intelligence_module():
    script = _repo_root() / "scripts" / "public" / "control" / "action_intelligence.py"
    spec = importlib.util.spec_from_file_location("ztare_action_intelligence_cli", script)
    if spec is None or spec.loader is None:
        raise SystemExit(f"ztare: could not load action-intelligence module: {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _default_autoresearch_route_path(decision_id: str) -> Path:
    return (
        _repo_root()
        / "analytics"
        / "public"
        / "queries"
        / "rd"
        / "autoresearch_routes"
        / f"{_safe_route_id(decision_id)}.json"
    )


def _record_autoresearch_route_action(
    *,
    route: dict,
    route_path: Path,
    decision_id: str,
    selected_action: str | None,
    why_not_autoresearch: str | None,
    materialize: bool,
    dedupe: bool,
) -> dict:
    module = _load_action_intelligence_module()
    ns = argparse.Namespace(
        route_json=route_path,
        action_impact_id=None,
        recorded_at=None,
        decision_id=decision_id,
        tick_id=None,
        project_id=None,
        project_family=None,
        stage="pretick",
        task=route.get("task"),
        selected_action=selected_action,
        policy_source="rd",
        selection_rule="rd_workbench_router",
        why_selected=None,
        why_not_autoresearch=why_not_autoresearch,
        worker_archetype=None,
        worker_capability=None,
        worker_state=None,
        worker_identity=None,
        transport=None,
        forecast_contract_id=None,
        gp233_evidence_ref=None,
        source_refs_json="[]",
        prediction_ids_json="[]",
        catch_ids_json="[]",
        outcome_known=False,
        success_bool=None,
        decision_impact=None,
        yield_signal=None,
        actual_cost_agent_minutes=None,
        negative_externality_tags_json="[]",
        baseline_action=None,
        counterfactual_action=None,
        counterfactual_value_bucket=None,
        notes=None,
    )
    payload = module.agentic_workbench_impact_from_route_args(ns)
    errors = payload.get("validation_errors") or []
    if errors:
        raise SystemExit("invalid agentic-route impact row: " + "; ".join(errors))

    rows = module.read_jsonl(module.ACTION_IMPACT_LEDGER)
    if dedupe:
        for row in rows:
            if str(row.get("action_impact_id") or "") == str(payload.get("action_impact_id") or ""):
                return {"deduped": True, "existing": row}
    rows.append(payload)
    module.write_jsonl(module.ACTION_IMPACT_LEDGER, rows)
    if materialize:
        module.materialize_models(write=True)
    return payload


def _queue_autoresearch_missing_surfaces(
    *,
    route_path: Path,
    decision_id: str,
    action: dict,
    queue_dir: str | None,
) -> list[dict]:
    from ztare.scaffold.substrate_queue import enqueue_from_route, queue_dir_from_arg

    source_action_impact_id = str(action.get("action_impact_id") or "") or None
    return enqueue_from_route(
        queue_dir=queue_dir_from_arg(queue_dir),
        route_json=route_path,
        decision_id=decision_id,
        source_action_impact_id=source_action_impact_id,
    )


# `ztare eigenquestion <verb>` — wraps eigenquestion proposal / review helpers.
# `propose` calls the LLM; `validate` only lints the explored-classes JSONL for
# the §14 (negative-evidence backpressure) discipline; `status` is a launch
# preflight for advisory proposals that are newer than the charter.
def _cmd_eigenquestion_router(rest: list[str]) -> int:
    if not rest or rest[0] in ("-h", "--help"):
        print(
            "ztare eigenquestion <verb> [args...]\n\n"
            "Verbs:\n"
            "  propose   →  generate a fresh advisory eigenquestion (LLM call)\n"
            "  validate  →  lint workspace/explored_primitive_classes.jsonl for\n"
            "               falsified rows missing or pointing at nonexistent\n"
            "               evidence_path (§14 caveat lint; no LLM call)\n"
            "  status    →  warn/fail if advisory proposals are newer than the\n"
            "               project charter (no LLM call, no charter rewrite)\n\n"
            "Both verbs require --project <slug>. For full flags, run\n"
            "  ztare eigenquestion <verb> --help"
        )
        return 0
    verb, *args = rest
    module = "src.ztare.research_director.eigenquestion_generator"
    if verb == "propose":
        return _delegate_module(module, args)
    if verb == "validate":
        return _delegate_module(module, ["--validate-explored", *args])
    if verb == "status":
        parser = argparse.ArgumentParser(
            prog="ztare eigenquestion status",
            description=(
                "Warn or fail when advisory eigenquestion proposals are newer "
                "than project_charter.md."
            ),
        )
        parser.add_argument("--project", required=True)
        parser.add_argument("--strict", action="store_true")
        parser.add_argument("--json", action="store_true")
        try:
            ns = parser.parse_args(args)
        except SystemExit as exc:
            return int(exc.code) if isinstance(exc.code, int) else 2
        status_args = [ns.project]
        if ns.strict:
            status_args.append("--strict")
        if ns.json:
            status_args.append("--json")
        return _delegate_script(
            "scripts/public/control/preflight_eigenquestion_review.py",
            status_args,
        )
    print(
        f"ztare: unknown eigenquestion verb {verb!r}. Known: propose, validate, status",
        file=sys.stderr,
    )
    return 2


# `ztare mine` — the weekly reflexive-mining run.
# Bare invocation prints help rather than triggering the full pipeline:
# the underlying script defaults to a full cycle on no args, which is
# a multi-minute LLM-dispatching run; CLI discipline says destructive
# / expensive commands must be explicit.
def _cmd_mine(rest: list[str]) -> int:
    if not rest:
        print(
            "ztare mine [--index-only] [--skip-dashboard] [--resume-after-rating]\n\n"
            "Weekly reflexive-mining run. Bare invocation requires explicit\n"
            "intent — pass one of the flags above, or `--run-full-cycle` to\n"
            "run the entire pipeline (which may dispatch LLM calls and take\n"
            "minutes).\n\n"
            "For the underlying script's own --help (full flag list):\n"
            "  ztare mine --help\n"
        )
        return 0
    if rest == ["--run-full-cycle"]:
        rest = []  # convert the explicit-intent sentinel into the script's default
    return _delegate_script("scripts/public/mining/run_reflexive_mine.py", rest)


# `ztare autoresearch <verb>` — thin shell over the Makefile pipeline.
# Does NOT reimplement: the Makefile is canonical. CLI provides
# discovery + a stable invocation surface for RD-agents.
_AUTORESEARCH_LEAF_HELP: dict[str, str] = {
    "run": (
        "ztare autoresearch run --project <slug> --rubric <name> [flags]\n\n"
        "Run a full in-loop experiment loop through `make experiment-loop`.\n\n"
        "Flags:\n"
        "  --project <slug>   required\n"
        "  --rubric <name>    required (name or path)\n"
        "  --intake <path>    optional project-intake boundary; blocks launch unless kernel_entry.can_enter_kernel is true\n"
        "  --packet <path>    legacy alias for --intake\n"
        "  --iters <n>        optional\n"
        "  --preflight-only   validate launch and intake boundary, then exit before model calls\n"
        "  --mutator <model>  optional\n"
        "  --judge <model>    optional\n"
        "  --inverter <model> optional post-champion falsifier model\n"
        "  --llm-timeout-seconds <n> optional\n"
        "  --llm-retries <n> optional\n"
        "  --allow-model-fallback opt into cross-model provider fallback\n"
        "  --agent-mutator --agent-judge --agent-committee --agent-inverter\n"
        "  --agent-runtime <codex|claude>\n"
    ),
    "trace": (
        "ztare autoresearch trace --project <slug> [--rubric <name>] [--intake <intake.json>] [--model <label>] [--evidence-search-backend auto|openai|anthropic] [--full-health] [--brief|--json]\n\n"
        "Emit a read-only project trace over evidence, derived constraints,\n"
        "project-intake readiness, graph records, prediction receipts,\n"
        "projection, recovery commands, and bounded trace-local health.\n"
        "Does not run model calls.\n\n"
        "Flags:\n"
        "  --project <slug>   required\n"
        "  --rubric <name>    optional\n"
        "  --intake <path>    optional project-intake JSON readiness boundary\n"
        "  --packet <path>    legacy alias for --intake\n"
        "  --model <label>    model label for suggested evidence recovery commands\n"
        "  --evidence-search-backend <auto|openai|anthropic> search backend rendered in evidence-fetch recovery commands\n"
        "  --full-health      also run aggregate autoresearch health\n"
        "  --brief            compact human-readable trace\n"
        "  --json             optional JSON report\n"
    ),
    "carrier-replay": (
        "ztare autoresearch carrier-replay [--project <slug-or-path>] [--repo <path>] [--json] [--strict]\n\n"
        "Replay read-only projection records across selected projects and\n"
        "surface latest-eval, artifact-ref, worker provenance, and action-link\n"
        "coverage gaps. Does not run model calls or mutate project state.\n\n"
        "Flags:\n"
        "  --project <slug>   optional; repeat for multiple projects\n"
        "  --repo <path>      optional repo root for fixture/local audits\n"
        "  --max-projects <n> discovery limit when --project is omitted\n"
        "  --out <path>       optional JSON output path\n"
        "  --json             optional JSON report\n"
        "  --strict           exit non-zero on attention/error rows\n"
    ),
    "dispatch-audit": (
        "ztare autoresearch dispatch-audit [--json]\n\n"
        "Verify LLM call sites are dispatch-covered through\n"
        "`make autoresearch-dispatch-validate`.\n\n"
        "Flags:\n"
        "  --json             optional JSON report\n"
    ),
    "dispatch-canary": (
        "ztare autoresearch dispatch-canary [flags]\n\n"
        "Exercise one subscription dispatch path; mocked by default.\n\n"
        "Flags:\n"
        "  --call-site <name> optional (default mutator)\n"
        "  --contract <text|mutator|judge|committee|inverter>\n"
        "  --runtime <codex|claude>\n"
        "  --timeout-seconds <n>\n"
        "  --live             invoke the real subscription CLI\n"
        "  --full-auto        allow full-auto mode for the live canary\n"
        "  --json             optional JSON report\n"
    ),
    "dispatch-parity": (
        "ztare autoresearch dispatch-parity [flags]\n\n"
        "Compare API vs subscription contract, quality, and cost-proxy replay;\n"
        "mocked by default.\n\n"
        "Flags:\n"
        "  --contracts <csv>  optional (default text,mutator,judge,committee,inverter)\n"
        "  --runtime <codex|claude>\n"
        "  --timeout-seconds <n>\n"
        "  --live             invoke the real subscription CLI for the subscription leg\n"
        "  --full-auto        allow full-auto mode for the live subscription leg\n"
        "  --json             optional JSON report with quality_score and cost_proxy\n"
    ),
    "subscription-outcomes": (
        "ztare autoresearch subscription-outcomes [flags]\n\n"
        "Compare actual run outcomes by worker transport.\n\n"
        "Flags:\n"
        "  --project <slug>   optional, restrict to one project\n"
        "  --min-rows <n>     optional minimum rows per transport, default 1\n"
        "  --plan-limit <n>   optional matched-run suggestions, default 5\n"
        "  --strict           exit non-zero unless rows are comparable\n"
        "  --json             optional JSON report\n"
    ),
    "matched-transport-pair": (
        "ztare autoresearch matched-transport-pair --project <slug> [flags]\n\n"
        "Print or run a stamped API/subscription pair.\n\n"
        "Flags:\n"
        "  --project <slug>   required\n"
        "  --rubric <name>    optional, defaults to project slug\n"
        "  --intake <path>    optional project-intake JSON\n"
        "  --iters <n>        optional\n"
        "  --mutator <model>  optional mutator model\n"
        "  --judge <model>    optional judge model\n"
        "  --inverter <model> optional inverter model\n"
        "  --llm-timeout-seconds <n> optional API call timeout\n"
        "  --llm-retries <n> optional API retry count\n"
        "  --model-fallback   opt into cross-model provider fallback\n"
        "  --pair-id <id>     optional, defaults to a timestamped pair id\n"
        "  --agent-runtime <codex|claude>\n"
        "  --agent-timeout <n> optional subscription-agent timeout in seconds\n"
        "  --run              execute both rows; omitted prints commands only\n"
    ),
    "hillclimb-audit": (
        "ztare autoresearch hillclimb-audit [flags]\n\n"
        "Inspect stale run traces for stagnation escape evidence.\n\n"
        "Flags:\n"
        "  --project <slug>   optional\n"
        "  --stagnation-threshold <n> optional, default 2\n"
        "  --limit <n>        optional row limit\n"
        "  --recovery-queue   emit only loop-control recovery queue and episode counts\n"
        "  --recovery-limit <n> optional recovery rows, default 20; 0 means all\n"
        "  --record-resolution append a workspace review receipt for one queue row\n"
        "  --workspace <path> required with --record-resolution\n"
        "  --iteration <n>    required with --record-resolution\n"
        "  --last-control-iteration <n> optional with --record-resolution\n"
        "  --outcome-status <status> required with --record-resolution\n"
        "  --resolution-status <status> reason_recorded|reviewed_no_lift|superseded|deferred\n"
        "  --reason <text>    required with --record-resolution\n"
        "  --json             optional JSON report\n"
    ),
    "consequence-audit": (
        "ztare autoresearch consequence-audit [flags]\n\n"
        "Classify kernel mechanisms by consequence and evidence.\n\n"
        "Flags:\n"
        "  --project <slug>   optional\n"
        "  --workspace <path> optional\n"
        "  --json             optional JSON report\n"
    ),
    "rubric-mode-audit": (
        "ztare autoresearch rubric-mode-audit [flags]\n\n"
        "Audit Newton/Kepler/calibration coherence across rubrics.\n\n"
        "Flags:\n"
        "  --rubric <path>    optional\n"
        "  --limit <n>        optional text attention row limit\n"
        "  --freshness-days <n> optional active debt window\n"
        "  --strict           exit non-zero when attention rows exist\n"
        "  --json             optional JSON report\n"
    ),
    "health": (
        "ztare autoresearch health [flags]\n\n"
        "Aggregate dispatch, catalog, fixture, graph, forecast, rubric, control,\n"
        "project trace, and source-preflight health.\n\n"
        "Flags:\n"
        "  --project <slug>   optional; enables project trace and raw/source typing preflight\n"
        "  --workspace <path> optional\n"
        "  --rubric <path>    optional\n"
        "  --stagnation-threshold <n> optional, default 2\n"
        "  --strict           exit non-zero when any component is not ok\n"
        "  --json             optional JSON report\n"
    ),
    "operations-intelligence": (
        "ztare autoresearch operations-intelligence [flags]\n\n"
        "Build the read-only RD operations report.\n\n"
        "Flags:\n"
        "  --out <path>       optional JSON output path\n"
        "  --markdown <path>  optional Markdown output path\n"
        "  --html <path>      optional HTML output path\n"
        "  --freshness-days <n> optional source freshness window\n"
        "  --max-projects <n> optional project sample cap\n"
        "  --no-markdown      skip Markdown output\n"
        "  --json             also print JSON to stdout\n"
    ),
    "workbench-recommend": (
        "ztare autoresearch workbench-recommend [flags]\n\n"
        "Recommend next project/workbench inputs for inspection. Compatibility: "
        "`substrate-recommend` delegates to the same command.\n\n"
        "Flags:\n"
        "  --mode <cold|branch> optional, default cold\n"
        "  --n <count>        optional, default 3\n"
        "  --class <label>    optional review class hint\n"
        "  --substrate-class <label> optional substrate-class hint\n"
        "  --branch-grid <path> optional branch grid for branch mode\n"
        "  --inbox <path>     optional output inbox\n"
        "  --model <model>    optional API fallback model\n"
        "  --raw-payload <path> render a precomputed JSON payload\n"
        "  --prompt-only      emit prompt and exit without model call\n"
        "  --skip-llm         write prompt to inbox for manual model run\n"
        "  --agent-recommender route through subscription worker\n"
        "  --agent-runtime <codex|claude>\n"
    ),
    "substrate-recommend": (
        "ztare autoresearch substrate-recommend [flags]\n\n"
        "Compatibility spelling for `ztare autoresearch workbench-recommend`.\n"
        "Prefer `workbench-recommend` in new docs and scripts.\n\n"
        "Flags are identical to `workbench-recommend`.\n"
    ),
    "catalog-health": (
        "ztare autoresearch catalog-health [--json]\n\n"
        "Check primitive catalog taxonomy and freshness.\n\n"
        "Flags:\n"
        "  --json             optional JSON report\n"
    ),
    "parent-utility": (
        "ztare autoresearch parent-utility [--json]\n\n"
        "Check whether primitive parent nodes route to useful children.\n\n"
        "Flags:\n"
        "  --json             optional JSON report\n"
    ),
    "primitive-parent-utility": (
        "ztare autoresearch primitive-parent-utility [--json]\n\n"
        "Alias for `ztare autoresearch parent-utility`.\n\n"
        "Flags:\n"
        "  --json             optional JSON report\n"
    ),
    "fixtures": (
        "ztare autoresearch fixtures [--json]\n\n"
        "Run the cheap fixture matrix for dormant in-loop mechanisms.\n\n"
        "Flags:\n"
        "  --json             optional JSON report\n"
    ),
    "control-demo": (
        "ztare autoresearch control-demo [flags]\n\n"
        "Materialize a controlled replay for optional in-loop controls.\n\n"
        "Flags:\n"
        "  --project <slug>   optional, default demo slug\n"
        "  --force            rebuild the demo project/rubric if present\n"
        "  --json             optional JSON report\n"
    ),
    "portfolio": (
        "ztare autoresearch portfolio [flags]\n\n"
        "Run a substrate-portfolio sweep.\n\n"
        "Flags:\n"
        "  --iters <n>        optional (default 5)\n"
        "  --mutator <model>  optional (default gpt4.1)\n"
        "  --judge <model>    optional (default gpt4.1)\n"
        "  --only <substrate> optional\n"
    ),
}


def _print_autoresearch_leaf_help(verb: str) -> int:
    help_text = _AUTORESEARCH_LEAF_HELP.get(verb)
    if not help_text:
        return 2
    print(help_text)
    return 0


def _autoresearch_run_packet_blocker(*, project: str, rubric: str, packet: str) -> str | None:
    """Return a launch-blocking message when packet-backed run readiness fails."""
    trace_module = importlib.import_module("ztare.reports.autoresearch_trace")
    trace = trace_module.build_autoresearch_trace(
        project=project,
        rubric=rubric,
        packet=packet,
        repo=_repo_root(),
        full_health=False,
    )
    kernel_entry = trace.get("kernel_entry") if isinstance(trace, dict) else {}
    if isinstance(kernel_entry, dict) and kernel_entry.get("can_enter_kernel") is True:
        return None

    readiness_label = (
        kernel_entry.get("readiness_canonical")
        or kernel_entry.get("readiness")
        or trace.get("readiness_canonical")
        or trace.get("readiness")
    )
    lines = [
        "ztare: `autoresearch run --intake` blocked by run-readiness contract",
        f"readiness: {readiness_label}",
    ]
    blockers = kernel_entry.get("blockers") if isinstance(kernel_entry, dict) else []
    if blockers:
        lines.append("blockers:")
        for blocker in blockers:
            if not isinstance(blocker, dict):
                continue
            label = str(blocker.get("canonical_id") or blocker.get("id") or "unknown")
            channel = str(
                blocker.get("canonical_recovery_channel")
                or blocker.get("recovery_channel")
                or "unknown"
            )
            command = str(blocker.get("next_command") or "").strip()
            suffix = f"; next: {command}" if command else ""
            lines.append(f"  - {label} ({channel}){suffix}")
    else:
        missing = trace.get("blocking_missing") if isinstance(trace, dict) else []
        lines.append(f"blocking_missing: {missing}")
    lines.append(
        "Run `ztare autoresearch trace --project "
        f"{project} --rubric {rubric} --intake {packet} --json` for the full contract."
    )
    return "\n".join(lines)


def _project_intake_path(kv: dict[str, str]) -> str:
    """Return the preferred project-intake path from CLI aliases."""
    intake = str(kv.get("--intake") or "").strip()
    packet = str(kv.get("--packet") or "").strip()
    if intake and packet and intake != packet:
        raise ValueError(
            "ztare: use either --intake or --packet, not conflicting paths"
        )
    return intake or packet


def _autoresearch_packet_run_defaults(packet: str) -> dict[str, str]:
    """Extract launch defaults from a packet's explicit autoresearch run command."""
    if not packet:
        return {}
    packet_path = Path(packet)
    if not packet_path.is_absolute():
        packet_path = _repo_root() / packet
    try:
        payload = json.loads(packet_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    command = str(payload.get("expected_command") or "").strip()
    if not command:
        return {}
    try:
        tokens = shlex.split(command)
    except ValueError:
        return {}
    if tokens[:3] != ["ztare", "autoresearch", "run"]:
        return {}
    run_kv = _parse_kv_flags(
        tokens[3:],
        allowed={
            "--iters",
            "--mutator",
            "--judge",
            "--inverter",
            "--llm-timeout-seconds",
            "--llm-retries",
        },
    )
    return {
        "ITERS": run_kv.get("--iters", ""),
        "MUTATOR_MODEL": run_kv.get("--mutator", ""),
        "JUDGE_MODEL": run_kv.get("--judge", ""),
        "INVERTER_MODEL": run_kv.get("--inverter", ""),
        "AUTORESEARCH_LLM_TIMEOUT": run_kv.get("--llm-timeout-seconds", ""),
        "AUTORESEARCH_LLM_RETRIES": run_kv.get("--llm-retries", ""),
    }


def _cmd_autoresearch_router(rest: list[str]) -> int:
    if not rest or rest[0] in ("-h", "--help"):
        print(
            "ztare autoresearch <verb> [args...]\n\n"
            "Verbs:\n"
            "  run       →  run a full experiment-loop on a project + rubric\n"
            "               (shells to `make experiment-loop`)\n"
            "  route     →  decide whether an RD task should invoke autoresearch\n"
            "               (calls the kernel workbench router)\n"
            "  projection → emit read-only hypothesis/evidence projection\n"
            "               (shells to `make autoresearch-projection`)\n"
            "  trace     → inspect project evidence/projection/health surfaces\n"
            "               (shells to `make autoresearch-trace`)\n"
            "  carrier-replay → replay projection-record coverage across projects\n"
            "               (direct read-only report module)\n"
            "  dispatch-audit → verify LLM call sites are dispatch-covered\n"
            "               (shells to `make autoresearch-dispatch-validate`)\n"
            "  dispatch-canary → exercise one subscription dispatch path\n"
            "               (mocked by default; pass --live for real CLI)\n"
            "  dispatch-parity → compare API vs subscription contract, quality, and cost-proxy replay\n"
            "               (mocked by default; pass --live for real subscription CLI)\n"
            "  subscription-outcomes → compare actual run outcomes by worker transport\n"
            "               (shells to `make autoresearch-subscription-outcome-audit`)\n"
            "  matched-transport-pair → print or run a stamped API/subscription pair\n"
            "               (shells to `make autoresearch-matched-transport-pair`)\n"
            "  hillclimb-audit → inspect stale run traces for stagnation escape evidence\n"
            "               (shells to `make autoresearch-hillclimb-audit`)\n"
            "  consequence-audit → classify kernel mechanisms by consequence/evidence\n"
            "               (shells to `make autoresearch-consequence-audit`)\n"
            "  rubric-mode-audit → audit Newton/Kepler/calibration coherence across rubrics\n"
            "               (shells to `make autoresearch-rubric-mode-audit`)\n"
            "  health    → aggregate dispatch/catalog/fixture/graph/forecast/rubric/control health\n"
            "               plus project source preflight when --project is supplied\n"
            "               (shells to `make autoresearch-kernel-health`)\n"
            "  operations-intelligence → build the read-only RD operations report\n"
            "               (shells to `make operations-intelligence`)\n"
            "  workbench-recommend → recommend next project/workbench inputs\n"
            "               (shells to `make autoresearch-substrate-recommend`)\n"
            "  substrate-recommend → compatibility spelling for workbench-recommend\n"
            "               (shells to `make autoresearch-substrate-recommend`)\n"
            "  catalog-health → check primitive catalog taxonomy/freshness\n"
            "               (shells to `make primitive-catalog-health`)\n"
            "  parent-utility → check whether primitive parent nodes route to useful children\n"
            "               (shells to `make primitive-parent-utility`)\n"
            "  fixtures → cheap fixture matrix for dormant in-loop mechanisms\n"
            "               (shells to `make inloop-fixture-validate`)\n"
            "  control-demo → materialize a controlled replay for optional in-loop controls\n"
            "               (shells to `make autoresearch-control-demo`)\n"
            "  hardening → inspect or run anti-gaming promotion contracts\n"
            "               (shells to `make gaming-vector-hardening-*`)\n"
            "  portfolio →  run a substrate-portfolio sweep\n"
            "               (shells to `make portfolio-run`)\n\n"
            "`run` flags:\n"
            "  --project <slug>   required\n"
            "  --rubric <name>    required (name or path)\n"
            "  --intake <path>    optional project-intake boundary; blocks launch unless kernel_entry.can_enter_kernel is true\n"
            "  --packet <path>    legacy alias for --intake\n"
            "  --iters <n>        optional (default per Makefile)\n"
            "  --mutator <model>  optional\n"
            "  --judge <model>    optional\n"
            "  --inverter <model> optional post-champion falsifier model\n"
            "  --agent-mutator    route mutator calls through subscription worker\n"
            "  --agent-judge      route judge calls through subscription worker\n"
            "  --agent-committee  route dynamic committee calls through subscription worker\n"
            "  --agent-inverter   route inversion/review calls through subscription worker\n"
            "  --agent-runtime <codex|claude> optional shared subscription runtime\n\n"
            "`route` flags:\n"
            "  --task <text>      required\n"
            "  --project <slug>   optional context label\n"
            "  --rubric <name>    optional context label\n"
            "  --intake <path>    optional project-intake boundary for run readiness\n"
            "  --packet <path>    legacy alias for --intake\n"
            "  --bounded-claim --stable-evaluator --rubric-ready --artifact-surface\n"
            "  --no-bounded-claim --no-stable-evaluator --no-rubric-ready --no-artifact-surface\n"
            "  --subscription-worker-available\n"
            "  Output is JSON. To save the route and append a validated action row in one step:\n"
            "    ztare autoresearch route --task <text> --record-decision-id DECISION_ID\n"
            "  Or save it and record consumed RD/out-of-loop decisions later with:\n"
            "    ztare action-intel record-agentic-route --route-json <route.json> --decision-id DECISION_ID\n\n"
            "`projection` flags:\n"
            "  --project <slug>   required\n"
            "  --out <path>       optional JSON output path\n\n"
            "`trace` flags:\n"
            "  --project <slug>   required\n"
            "  --rubric <name>    optional\n"
            "  --intake <path>    optional project-intake boundary\n"
            "  --packet <path>    legacy alias for --intake\n"
            "  --model <label>    model label for suggested evidence recovery commands\n"
            "  --full-health      also run aggregate autoresearch health\n"
            "  --brief            compact human-readable trace\n"
            "  --json             optional JSON report\n\n"
            "`carrier-replay` flags:\n"
            "  --project <slug>   optional; repeat for multiple projects\n"
            "  --repo <path>      optional repo root for fixture/local audits\n"
            "  --max-projects <n> discovery limit when --project is omitted\n"
            "  --out <path>       optional JSON output path\n"
            "  --json             optional JSON report\n"
            "  --strict           exit non-zero on attention/error rows\n\n"
            "`dispatch-audit` flags:\n"
            "  --json             optional JSON report\n\n"
            "`dispatch-canary` flags:\n"
            "  --call-site <name> optional (default mutator)\n"
            "  --contract <text|mutator|judge|committee|inverter> optional (default text)\n"
            "  --runtime <codex|claude> optional\n"
            "  --timeout-seconds <n> optional\n"
            "  --live             invoke the real subscription CLI\n"
            "  --full-auto        allow full-auto mode for the live canary\n"
            "  --json             optional JSON report\n\n"
            "`dispatch-parity` flags:\n"
            "  --contracts <csv>  optional (default text,mutator,judge,committee,inverter)\n"
            "  --runtime <codex|claude> optional\n"
            "  --timeout-seconds <n> optional\n"
            "  --live             invoke the real subscription CLI for the subscription leg\n"
            "  --full-auto        allow full-auto mode for the live subscription leg\n"
            "  --json             optional JSON report with per-contract quality_score and cost_proxy\n\n"
            "`subscription-outcomes` flags:\n"
            "  --project <slug>   optional, restrict to one project\n"
            "  --min-rows <n>     optional minimum rows per transport, default 1\n"
            "  --plan-limit <n>   optional matched-run command suggestions, default 5\n"
            "  --strict           exit non-zero unless API and subscription rows are comparable\n"
            "  --json             optional JSON report\n\n"
            "`matched-transport-pair` flags:\n"
            "  --project <slug>   required\n"
            "  --rubric <name>    optional, defaults to project slug\n"
            "  --intake <path>    optional project-intake JSON\n"
            "  --iters <n>        optional, default Make ITERS\n"
            "  --mutator <model>  optional mutator model\n"
            "  --judge <model>    optional judge model\n"
            "  --inverter <model> optional inverter model\n"
            "  --llm-timeout-seconds <n> optional API call timeout\n"
            "  --llm-retries <n> optional API retry count\n"
            "  --model-fallback   opt into cross-model provider fallback\n"
            "  --pair-id <id>     optional, defaults to a timestamped pair id\n"
            "  --agent-runtime <codex|claude> optional, default codex in Make target\n"
            "  --agent-timeout <n> optional subscription-agent timeout in seconds\n"
            "  --run              execute both rows; omitted prints commands only\n\n"
            "`hillclimb-audit` flags:\n"
            "  --project <slug>   optional, restrict to one project and archives\n"
            "  --stagnation-threshold <n> optional, default 2\n"
            "  --limit <n>        optional row limit\n"
            "  --recovery-queue   emit only loop-control recovery queue and episode counts\n"
            "  --recovery-limit <n> optional recovery rows, default 20; 0 means all\n"
            "  --recovery-intake-status <status> optional intake-readiness filter\n"
            "  --recovery-packet-status <status> legacy alias for --recovery-intake-status\n"
            "  --record-resolution append a workspace review receipt for one queue row\n"
            "  --workspace <path> --iteration <n> --outcome-status <status> --reason <text>\n"
            "  --json             optional JSON report\n\n"
            "`consequence-audit` flags:\n"
            "  --project <slug>   optional, restrict project-scoped evidence\n"
            "  --workspace <path> optional, inspect one workspace directly\n"
            "  --json             optional JSON report\n\n"
            "`rubric-mode-audit` flags:\n"
            "  --rubric <path>    optional, inspect one rubric instead of rubrics/*.json\n"
            "  --limit <n>        optional text attention row limit\n"
            "  --freshness-days <n> optional window for active legacy-rubric debt\n"
            "  --strict           exit non-zero when attention rows exist\n"
            "  --json             optional JSON report\n\n"
            "`health` flags:\n"
            "  --project <slug>   optional, enables project source-preflight checks\n"
            "  --workspace <path> optional, inspect one workspace for mechanism evidence\n"
            "  --rubric <path>    optional, restrict rubric-mode audit to one rubric\n"
            "  --intake <path>    optional project-intake boundary for trace-local health\n"
            "  --packet <path>    legacy alias for --intake\n"
            "  --stagnation-threshold <n> optional, default 2\n"
            "  --strict           exit non-zero when any component is not ok\n"
            "  --json             optional JSON report\n\n"
            "`operations-intelligence` flags:\n"
            "  --out <path>       optional JSON output path\n"
            "  --markdown <path>  optional Markdown output path\n"
            "  --html <path>      optional HTML output path\n"
            "  --freshness-days <n> optional source freshness window\n"
            "  --max-projects <n> optional project sample cap\n"
            "  --no-markdown      skip Markdown output\n"
            "  --json             also print JSON to stdout\n\n"
            "`workbench-recommend` / `substrate-recommend` flags:\n"
            "  --mode <cold|branch> optional, default cold\n"
            "  --n <count>        optional, default 3\n"
            "  --class <label>    optional review class hint\n"
            "  --substrate-class <label> optional substrate-class hint\n"
            "  --branch-grid <path> optional branch grid for branch mode\n"
            "  --inbox <path>     optional output inbox\n"
            "  --model <model>    optional API fallback model\n"
            "  --raw-payload <path> render a precomputed JSON payload\n"
            "  --prompt-only      emit prompt and exit without model call\n"
            "  --skip-llm         write prompt to inbox for manual model run\n"
            "  --agent-recommender route through subscription worker\n"
            "  --agent-runtime <codex|claude> optional shared subscription runtime\n\n"
            "`catalog-health` flags:\n"
            "  --json             optional JSON report\n\n"
            "`fixtures` flags:\n"
            "  --json             optional JSON report\n\n"
            "`control-demo` flags:\n"
            "  --project <slug>   optional, default demo slug\n"
            "  --force            rebuild the demo project/rubric if present\n"
            "  --json             optional JSON report\n\n"
            "`hardening` actions:\n"
            "  show | check-plan | sync-plan | run-current | selftest\n"
            "  run-vector --vector <name> [--substrate autoresearch]\n\n"
            "`portfolio` flags:\n"
            "  --iters <n>        optional (default 5)\n"
            "  --mutator <model>  optional (default gpt4.1)\n"
            "  --judge <model>    optional (default gpt4.1)\n"
            "  --only <substrate> optional (restrict to one substrate)\n"
        )
        return 0
    verb, *args = rest
    if args and args[0] in ("-h", "--help") and verb in _AUTORESEARCH_LEAF_HELP:
        return _print_autoresearch_leaf_help(verb)
    if verb == "run":
        kv = _parse_kv_flags(args, allowed={"--project", "--rubric", "--iters",
                                             "--mutator", "--judge", "--inverter", "--agent-runtime",
                                             "--llm-timeout-seconds", "--llm-retries",
                                             "--intake", "--packet"})
        bools = _parse_bool_flags(
            args,
            allowed={
                "--agent-mutator",
                "--agent-judge",
                "--agent-committee",
                "--agent-inverter",
                "--preflight-only",
                "--allow-model-fallback",
            },
        )
        if not kv.get("--project") or not kv.get("--rubric"):
            print("ztare: `autoresearch run` requires --project <slug> --rubric <name>",
                  file=sys.stderr)
            return 2
        try:
            intake_path = _project_intake_path(kv)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        if intake_path:
            blocked = _autoresearch_run_packet_blocker(
                project=kv.get("--project", ""),
                rubric=kv.get("--rubric", ""),
                packet=intake_path,
            )
            if blocked:
                print(blocked, file=sys.stderr)
                return 2
        packet_defaults = _autoresearch_packet_run_defaults(intake_path)
        return _delegate_make("experiment-loop", {
            "PROJECT": kv.get("--project", ""),
            "RUBRIC": kv.get("--rubric", ""),
            "ITERS": kv.get("--iters", "") or packet_defaults.get("ITERS", ""),
            "MUTATOR_MODEL": kv.get("--mutator", "") or packet_defaults.get("MUTATOR_MODEL", ""),
            "JUDGE_MODEL": kv.get("--judge", "") or packet_defaults.get("JUDGE_MODEL", ""),
            "INVERTER_MODEL": kv.get("--inverter", "") or packet_defaults.get("INVERTER_MODEL", ""),
            "AUTORESEARCH_LLM_TIMEOUT": (
                kv.get("--llm-timeout-seconds", "")
                or packet_defaults.get("AUTORESEARCH_LLM_TIMEOUT", "")
            ),
            "AUTORESEARCH_LLM_RETRIES": (
                kv.get("--llm-retries", "")
                or packet_defaults.get("AUTORESEARCH_LLM_RETRIES", "")
            ),
            "MODEL_FALLBACK": "1" if "--allow-model-fallback" in bools else "",
            "INTAKE": intake_path,
            "PREFLIGHT_ONLY": "1" if "--preflight-only" in bools else "",
            "AGENT_MUTATOR": "1" if "--agent-mutator" in bools else "",
            "AGENT_JUDGE": "1" if "--agent-judge" in bools else "",
            "AGENT_COMMITTEE": "1" if "--agent-committee" in bools else "",
            "AGENT_INVERTER": "1" if "--agent-inverter" in bools else "",
            "AGENT_RUNTIME": kv.get("--agent-runtime", ""),
        })
    if verb == "route":
        if not args or args[0] in ("-h", "--help"):
            print(
                "ztare autoresearch route --task <text> [flags]\n\n"
                "Ask the kernel router whether a Research Director task should\n"
                "invoke in-loop autoresearch, prepare a missing surface, or stay\n"
                "outside the in-loop kernel until the task has a bounded claim,\n"
                "rubric, evaluator, artifact surface, and fresh source/evidence\n"
                "trace when those project surfaces exist. The route JSON includes\n"
                "plan_preview: the deterministic preflight command, dependency\n"
                "order, budget summary, and fallback policy before any paid run.\n\n"
                "Flags:\n"
                "  --task <text>      required\n"
                "  --project <slug>   optional context for surface inference\n"
                "  --rubric <name>    optional context for surface inference\n"
                "  --intake <path>    optional project-intake boundary for run readiness\n"
                "  --packet <path>    legacy alias for --intake\n"
                "  --bounded-claim / --no-bounded-claim\n"
                "  --stable-evaluator / --no-stable-evaluator\n"
                "  --rubric-ready / --no-rubric-ready\n"
                "  --artifact-surface / --no-artifact-surface\n"
                "  --subscription-worker-available\n"
                "  --record-decision-id <id>   save route JSON and append an action-intelligence row\n"
                "  --route-json-out <path>     optional route JSON path for --record-decision-id\n"
                "  --queue-missing-surface     also enqueue prepare_autoresearch_surface scaffolds\n"
                "  --queue-dir <path>          optional project/data prep ledger directory\n"
                "  --selected-action <action>  optional override for the recorded row\n"
                "  --why-not-autoresearch <text> required when bypassing a ready workbench\n"
                "  --dedupe --materialize      optional action-intelligence write flags\n"
                "\nExample:\n"
                "  ztare autoresearch route --task \"test bounded claim\" --project demo_claims --rubric demo_claims > autoresearch_route.json\n"
                "  ztare autoresearch route --task \"test bounded claim\" --project demo_claims --rubric demo_claims --record-decision-id decision_demo_claims_route\n"
                "  ztare autoresearch route --task \"test bounded claim\" --project demo_claims --rubric demo_claims --record-decision-id decision_demo_claims_route --queue-missing-surface\n"
                "  ztare action-intel record-agentic-route --route-json autoresearch_route.json --decision-id DECISION_ID\n"
            )
            return 0
        kv = _parse_kv_flags(
            args,
            allowed={
                "--task",
                "--project",
                "--rubric",
                "--intake",
                "--packet",
                "--record-decision-id",
                "--route-json-out",
                "--queue-dir",
                "--selected-action",
                "--why-not-autoresearch",
            },
        )
        bools = _parse_bool_flags(
            args,
            allowed={
                "--bounded-claim",
                "--no-bounded-claim",
                "--stable-evaluator",
                "--no-stable-evaluator",
                "--rubric-ready",
                "--no-rubric-ready",
                "--artifact-surface",
                "--no-artifact-surface",
                "--subscription-worker-available",
                "--queue-missing-surface",
                "--dedupe",
                "--materialize",
            },
        )
        task = kv.get("--task")
        if not task:
            print("ztare: `autoresearch route` requires --task <text>", file=sys.stderr)
            return 2
        route_args = [task]
        if kv.get("--project"):
            route_args.extend(["--project", kv["--project"]])
        if kv.get("--rubric"):
            route_args.extend(["--rubric", kv["--rubric"]])
        try:
            intake_path = _project_intake_path(kv)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        if intake_path:
            route_args.extend(["--intake", intake_path])
        if "--bounded-claim" in bools:
            route_args.append("--bounded-claim")
        if "--no-bounded-claim" in bools:
            route_args.append("--no-bounded-claim")
        if "--stable-evaluator" in bools:
            route_args.append("--stable-evaluator")
        if "--no-stable-evaluator" in bools:
            route_args.append("--no-stable-evaluator")
        if "--rubric-ready" in bools:
            route_args.append("--rubric-ready")
        if "--no-rubric-ready" in bools:
            route_args.append("--no-rubric-ready")
        if "--artifact-surface" in bools:
            route_args.append("--artifact-surface")
        if "--no-artifact-surface" in bools:
            route_args.append("--no-artifact-surface")
        if "--subscription-worker-available" in bools:
            route_args.append("--subscription-worker-available")
        decision_id = kv.get("--record-decision-id")
        if decision_id:
            router_module = importlib.import_module(
                "ztare.research_director.autoresearch_workbench_router"
            )
            route_autoresearch_workbench_from_context = (
                router_module.route_autoresearch_workbench_from_context
            )

            def _bool_override(name: str) -> bool | None:
                if f"--{name}" in bools:
                    return True
                if f"--no-{name}" in bools:
                    return False
                return None

            route_path = (
                Path(kv["--route-json-out"])
                if kv.get("--route-json-out")
                else _default_autoresearch_route_path(decision_id)
            )
            if not route_path.is_absolute():
                route_path = _repo_root() / route_path
            decision = route_autoresearch_workbench_from_context(
                task,
                project=kv.get("--project", ""),
                rubric=kv.get("--rubric", ""),
                packet=intake_path or None,
                stable_evaluator=_bool_override("stable-evaluator"),
                bounded_claim=_bool_override("bounded-claim"),
                rubric_ready=_bool_override("rubric-ready"),
                artifact_surface=_bool_override("artifact-surface"),
                subscription_worker_available="--subscription-worker-available" in bools,
                repo_root=_repo_root(),
            )
            route = decision.to_dict()
            queue_requested = "--queue-missing-surface" in bools
            if queue_requested and route.get("decision") != "prepare_autoresearch_surface":
                print(
                    "ztare: --queue-missing-surface only applies when the router returns "
                    "prepare_autoresearch_surface",
                    file=sys.stderr,
                )
                return 2
            route_path.parent.mkdir(parents=True, exist_ok=True)
            route_path.write_text(json.dumps(route, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            action = _record_autoresearch_route_action(
                route=route,
                route_path=route_path,
                decision_id=decision_id,
                selected_action=kv.get("--selected-action"),
                why_not_autoresearch=kv.get("--why-not-autoresearch"),
                materialize="--materialize" in bools,
                dedupe="--dedupe" in bools,
            )
            queued_surfaces = None
            if queue_requested:
                queued_surfaces = _queue_autoresearch_missing_surfaces(
                    route_path=route_path,
                    decision_id=decision_id,
                    action=action.get("existing") if action.get("deduped") and isinstance(action.get("existing"), dict) else action,
                    queue_dir=kv.get("--queue-dir"),
                )
            try:
                shown_route_path = str(route_path.relative_to(_repo_root()))
            except ValueError:
                shown_route_path = str(route_path)
            payload = {
                "route_json": shown_route_path,
                "route": route,
                "action_impact": action,
            }
            if queued_surfaces is not None:
                payload["queued_surface_prep"] = queued_surfaces
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0
        return _delegate_module("ztare.research_director.autoresearch_workbench_router", route_args)
    if verb == "projection":
        if not args or args[0] in ("-h", "--help"):
            print(
                "ztare autoresearch projection --project <slug> [--out <path>]\n\n"
                "Emit the read-only hypothesis/evidence projection over an\n"
                "autoresearch project's eval_history. Shells to\n"
                "`make autoresearch-projection`."
            )
            return 0
        kv = _parse_kv_flags(args, allowed={"--project", "--out"})
        if not kv.get("--project"):
            print("ztare: `autoresearch projection` requires --project <slug>",
                  file=sys.stderr)
            return 2
        return _delegate_make("autoresearch-projection", {
            "PROJECT": kv.get("--project", ""),
            "OUT": kv.get("--out", ""),
        })
    if verb == "trace":
        if not args or args[0] in ("-h", "--help"):
            print(
                "ztare autoresearch trace --project <slug> [--rubric <name>] [--intake <intake.json>] [--model <label>] [--evidence-search-backend auto|openai|anthropic] [--full-health] [--brief|--json]\n\n"
                "Emit a read-only project trace over evidence, derived constraints,\n"
                "project-intake readiness, graph records, prediction receipts,\n"
                "projection, recovery commands, and bounded trace-local health.\n"
                "Does not run model calls or steer by forecast scores.\n"
                "`--packet` remains a compatibility alias for `--intake`."
            )
            return 0
        kv = _parse_kv_flags(args, allowed={"--project", "--rubric", "--intake", "--packet", "--model", "--evidence-search-backend"})
        bools = _parse_bool_flags(args, allowed={"--full-health", "--brief", "--json"})
        if not kv.get("--project"):
            print("ztare: `autoresearch trace` requires --project <slug>",
                  file=sys.stderr)
            return 2
        try:
            intake_path = _project_intake_path(kv)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        return _delegate_make("autoresearch-trace", {
            "PROJECT": kv.get("--project", ""),
            "RUBRIC": kv.get("--rubric", ""),
            "INTAKE": intake_path,
            "MODEL": kv.get("--model", ""),
            "EVIDENCE_SEARCH_BACKEND": kv.get("--evidence-search-backend", ""),
            "FULL_HEALTH": "1" if "--full-health" in bools else "",
            "BRIEF": "1" if "--brief" in bools else "",
            "JSON": "1" if "--json" in bools else "",
        })
    if verb == "carrier-replay":
        if not args or args[0] in ("-h", "--help"):
            print(_AUTORESEARCH_LEAF_HELP["carrier-replay"])
            return 0
        return _delegate_module("ztare.reports.autoresearch_carrier_replay", args)
    if verb == "dispatch-audit":
        bools = _parse_bool_flags(args, allowed={"--json"})
        return _delegate_make("autoresearch-dispatch-validate", {
            "JSON": "1" if "--json" in bools else "",
        })
    if verb == "dispatch-canary":
        kv = _parse_kv_flags(args, allowed={"--call-site", "--contract", "--runtime", "--timeout-seconds"})
        bools = _parse_bool_flags(args, allowed={"--live", "--full-auto", "--json"})
        return _delegate_make("autoresearch-dispatch-canary", {
            "DISPATCH_CALL_SITE": kv.get("--call-site", ""),
            "CONTRACT": kv.get("--contract", ""),
            "AGENT_RUNTIME": kv.get("--runtime", ""),
            "AGENT_TIMEOUT": kv.get("--timeout-seconds", ""),
            "LIVE": "1" if "--live" in bools else "",
            "FULL_AUTO": "1" if "--full-auto" in bools else "",
            "JSON": "1" if "--json" in bools else "",
        })
    if verb == "dispatch-parity":
        kv = _parse_kv_flags(args, allowed={"--contracts", "--runtime", "--timeout-seconds"})
        bools = _parse_bool_flags(args, allowed={"--live", "--full-auto", "--json"})
        return _delegate_make("autoresearch-dispatch-parity", {
            "CONTRACTS": kv.get("--contracts", ""),
            "AGENT_RUNTIME": kv.get("--runtime", ""),
            "AGENT_TIMEOUT": kv.get("--timeout-seconds", ""),
            "LIVE": "1" if "--live" in bools else "",
            "FULL_AUTO": "1" if "--full-auto" in bools else "",
            "JSON": "1" if "--json" in bools else "",
        })
    if verb == "subscription-outcomes":
        kv = _parse_kv_flags(args, allowed={"--project", "--min-rows", "--plan-limit"})
        bools = _parse_bool_flags(args, allowed={"--json", "--strict"})
        return _delegate_make("autoresearch-subscription-outcome-audit", {
            "PROJECT": kv.get("--project", ""),
            "MIN_ROWS": kv.get("--min-rows", ""),
            "PLAN_LIMIT": kv.get("--plan-limit", ""),
            "STRICT": "1" if "--strict" in bools else "",
            "JSON": "1" if "--json" in bools else "",
        })
    if verb == "matched-transport-pair":
        kv = _parse_kv_flags(
            args,
            allowed={
                "--project",
                "--rubric",
                "--intake",
                "--iters",
                "--mutator",
                "--judge",
                "--inverter",
                "--llm-timeout-seconds",
                "--llm-retries",
                "--pair-id",
                "--agent-runtime",
                "--agent-timeout",
            },
        )
        bools = _parse_bool_flags(args, allowed={"--model-fallback", "--run"})
        if not kv.get("--project"):
            print("ztare: `autoresearch matched-transport-pair` requires --project <slug>",
                  file=sys.stderr)
            return 2
        return _delegate_make("autoresearch-matched-transport-pair", {
            "PROJECT": kv.get("--project", ""),
            "RUBRIC": kv.get("--rubric", ""),
            "INTAKE": kv.get("--intake", ""),
            "ITERS": kv.get("--iters", ""),
            "MUTATOR_MODEL": kv.get("--mutator", ""),
            "JUDGE_MODEL": kv.get("--judge", ""),
            "INVERTER_MODEL": kv.get("--inverter", ""),
            "AUTORESEARCH_LLM_TIMEOUT": kv.get("--llm-timeout-seconds", ""),
            "AUTORESEARCH_LLM_RETRIES": kv.get("--llm-retries", ""),
            "MODEL_FALLBACK": "1" if "--model-fallback" in bools else "",
            "MATCHED_RUN_ID": kv.get("--pair-id", ""),
            "AGENT_RUNTIME": kv.get("--agent-runtime", ""),
            "AGENT_TIMEOUT": kv.get("--agent-timeout", ""),
            "RUN_MATCHED_PAIR": "1" if "--run" in bools else "",
        })
    if verb == "hillclimb-audit":
        if "--record-resolution" in args:
            return _delegate_module("ztare.reports.hill_climb_behavior_audit", args)
        kv = _parse_kv_flags(
            args,
            allowed={
                "--project",
                "--stagnation-threshold",
                "--limit",
                "--recovery-limit",
                "--recovery-intake-status",
                "--recovery-packet-status",
            },
        )
        bools = _parse_bool_flags(args, allowed={"--json", "--recovery-queue"})
        return _delegate_make("autoresearch-hillclimb-audit", {
            "PROJECT": kv.get("--project", ""),
            "STAGNATION_THRESHOLD": kv.get("--stagnation-threshold", ""),
            "LIMIT": kv.get("--limit", ""),
            "RECOVERY_QUEUE": "1" if "--recovery-queue" in bools else "",
            "RECOVERY_LIMIT": kv.get("--recovery-limit", ""),
            "RECOVERY_INTAKE_STATUS": (
                kv.get("--recovery-intake-status", "")
                or kv.get("--recovery-packet-status", "")
            ),
            "JSON": "1" if "--json" in bools else "",
        })
    if verb == "consequence-audit":
        kv = _parse_kv_flags(args, allowed={"--project", "--workspace"})
        bools = _parse_bool_flags(args, allowed={"--json"})
        return _delegate_make("autoresearch-consequence-audit", {
            "PROJECT": kv.get("--project", ""),
            "WORKSPACE": kv.get("--workspace", ""),
            "JSON": "1" if "--json" in bools else "",
        })
    if verb == "rubric-mode-audit":
        kv = _parse_kv_flags(args, allowed={"--rubric", "--limit", "--freshness-days"})
        bools = _parse_bool_flags(args, allowed={"--json", "--strict"})
        return _delegate_make("autoresearch-rubric-mode-audit", {
            "RUBRIC": kv.get("--rubric", ""),
            "LIMIT": kv.get("--limit", ""),
            "FRESHNESS_DAYS": kv.get("--freshness-days", ""),
            "STRICT": "1" if "--strict" in bools else "",
            "JSON": "1" if "--json" in bools else "",
        })
    if verb == "health":
        kv = _parse_kv_flags(
            args,
            allowed={
                "--project",
                "--workspace",
                "--rubric",
                "--intake",
                "--packet",
                "--stagnation-threshold",
            },
        )
        bools = _parse_bool_flags(args, allowed={"--json", "--strict"})
        try:
            intake_path = _project_intake_path(kv)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        return _delegate_make("autoresearch-kernel-health", {
            "PROJECT": kv.get("--project", ""),
            "WORKSPACE": kv.get("--workspace", ""),
            "RUBRIC": kv.get("--rubric", ""),
            "INTAKE": intake_path,
            "STAGNATION_THRESHOLD": kv.get("--stagnation-threshold", ""),
            "STRICT": "1" if "--strict" in bools else "",
            "JSON": "1" if "--json" in bools else "",
        })
    if verb == "operations-intelligence":
        kv = _parse_kv_flags(
            args,
            allowed={"--out", "--markdown", "--html", "--freshness-days", "--max-projects"},
        )
        bools = _parse_bool_flags(args, allowed={"--no-markdown", "--json"})
        return _delegate_make("operations-intelligence", {
            "OUT": kv.get("--out", ""),
            "MD_OUT": kv.get("--markdown", ""),
            "HTML_OUT": kv.get("--html", ""),
            "FRESHNESS_DAYS": kv.get("--freshness-days", ""),
            "MAX_PROJECTS": kv.get("--max-projects", ""),
            "NO_MARKDOWN": "1" if "--no-markdown" in bools else "",
            "JSON": "1" if "--json" in bools else "",
        })
    if verb in ("workbench-recommend", "substrate-recommend"):
        kv = _parse_kv_flags(
            args,
            allowed={
                "--mode",
                "--n",
                "--class",
                "--substrate-class",
                "--branch-grid",
                "--inbox",
                "--model",
                "--raw-payload",
                "--agent-runtime",
            },
        )
        bools = _parse_bool_flags(args, allowed={"--prompt-only", "--skip-llm", "--agent-recommender"})
        return _delegate_make("autoresearch-substrate-recommend", {
            "RECOMMENDER_MODE": kv.get("--mode", ""),
            "RECOMMENDER_N": kv.get("--n", ""),
            "RECOMMENDER_CLASS": kv.get("--class", ""),
            "RECOMMENDER_SUBSTRATE_CLASS": kv.get("--substrate-class", ""),
            "BRANCH_GRID": kv.get("--branch-grid", ""),
            "INBOX": kv.get("--inbox", ""),
            "MODEL": kv.get("--model", ""),
            "RAW_PAYLOAD": kv.get("--raw-payload", ""),
            "PROMPT_ONLY": "1" if "--prompt-only" in bools else "",
            "SKIP_LLM": "1" if "--skip-llm" in bools else "",
            "AGENT_RECOMMENDER": "1" if "--agent-recommender" in bools else "",
            "AGENT_RUNTIME": kv.get("--agent-runtime", ""),
        })
    if verb == "catalog-health":
        bools = _parse_bool_flags(args, allowed={"--json"})
        return _delegate_make("primitive-catalog-health", {
            "JSON": "1" if "--json" in bools else "",
        })
    if verb in ("parent-utility", "primitive-parent-utility"):
        bools = _parse_bool_flags(args, allowed={"--json"})
        return _delegate_make("primitive-parent-utility", {
            "JSON": "1" if "--json" in bools else "",
        })
    if verb == "fixtures":
        bools = _parse_bool_flags(args, allowed={"--json"})
        return _delegate_make("inloop-fixture-validate", {
            "JSON": "1" if "--json" in bools else "",
        })
    if verb == "control-demo":
        kv = _parse_kv_flags(args, allowed={"--project"})
        bools = _parse_bool_flags(args, allowed={"--force", "--json"})
        return _delegate_make("autoresearch-control-demo", {
            "PROJECT": kv.get("--project", ""),
            "FORCE": "1" if "--force" in bools else "",
            "JSON": "1" if "--json" in bools else "",
        })
    if verb == "hardening":
        if not args or args[0] in ("-h", "--help"):
            print(
                "ztare autoresearch hardening <action> [flags]\n\n"
                "Actions:\n"
                "  show         show the current anti-gaming promotion queue\n"
                "  check-plan   verify materialized queue matches open registry rows\n"
                "  sync-plan    refresh the materialized queue from the registry\n"
                "  run-current  evaluate the current vector promotion contract\n"
                "  run-vector   evaluate one vector promotion contract\n"
                "  selftest     run the promotion-runner self-test\n\n"
                "`run-vector` flags:\n"
                "  --vector <name>       required\n"
                "  --substrate <name>    optional, defaults to autoresearch\n"
            )
            return 0
        action, *hargs = args
        target_by_action = {
            "show": "gaming-vector-hardening-show",
            "check-plan": "gaming-vector-hardening-check-plan",
            "sync-plan": "gaming-vector-hardening-sync-plan",
            "run-current": "gaming-vector-hardening-run-current",
            "selftest": "gaming-vector-hardening-selftest",
        }
        if action in target_by_action:
            return _delegate_make(target_by_action[action], {})
        if action == "run-vector":
            kv = _parse_kv_flags(hargs, allowed={"--vector", "--substrate"})
            if not kv.get("--vector"):
                print("ztare: `autoresearch hardening run-vector` requires --vector <name>",
                      file=sys.stderr)
                return 2
            return _delegate_make("gaming-vector-hardening-run-vector", {
                "VECTOR": kv.get("--vector", ""),
                "SUBSTRATE": kv.get("--substrate", ""),
            })
        print(
            f"ztare: unknown autoresearch hardening action {action!r}. Known: show, check-plan, sync-plan, run-current, run-vector, selftest",
            file=sys.stderr,
        )
        return 2
    if verb == "portfolio":
        kv = _parse_kv_flags(args, allowed={"--iters", "--mutator", "--judge", "--only"})
        return _delegate_make("portfolio-run", {
            "ITERS": kv.get("--iters", ""),
            "MUTATOR": kv.get("--mutator", ""),
            "JUDGE": kv.get("--judge", ""),
            "ONLY": kv.get("--only", ""),
        })
    print(
        f"ztare: unknown autoresearch verb {verb!r}. Known: run, route, projection, trace, carrier-replay, dispatch-audit, dispatch-canary, dispatch-parity, subscription-outcomes, matched-transport-pair, hillclimb-audit, consequence-audit, rubric-mode-audit, health, operations-intelligence, workbench-recommend, substrate-recommend, catalog-health, parent-utility, fixtures, control-demo, hardening, portfolio",
        file=sys.stderr,
    )
    return 2


# Shared router for `ztare project <verb>` plus the legacy `ztare substrate`
# namespace. `project` is the public front door for setup/scaffolding work that
# happens before a task has the surfaces needed for the in-loop autoresearch
# kernel. It does not duplicate the substrate generator or Make pipelines.
def _normalize_queue_dir_flag(args: list[str]) -> tuple[list[str], str | None] | None:
    normalized_args: list[str] = []
    queue_dir: str | None = None
    idx = 0
    while idx < len(args):
        if args[idx] == "--queue-dir":
            if idx + 1 >= len(args):
                print("ztare: --queue-dir requires a value", file=sys.stderr)
                return None
            queue_dir = args[idx + 1]
            idx += 2
            continue
        normalized_args.append(args[idx])
        idx += 1
    return normalized_args, queue_dir


def _cmd_substrate_router(rest: list[str], command_name: str = "substrate") -> int:
    if not rest or rest[0] in ("-h", "--help"):
        print(
            f"ztare {command_name} <verb> [args...]\n\n"
            "Verbs:\n"
            "  new       → create project/rubric/evidence surface artifacts\n"
            "              (shells to `python -m ztare.scaffold.generate_substrate`)\n"
            "  prepare   → run the standard project setup pipeline\n"
            "              (shells to `make setup-project`)\n"
            "  seal      → run the sentinel/integration seal for a project\n"
            "              (shells to `make seal`)\n"
            "  intake    → create, draft, validate, falsify, or enqueue bounded project intake\n"
            "              (create | draft-from-compiled | validate | falsify | enqueue)\n"
            "  packet    → legacy alias for intake\n"
            "  prep-ledger → optional append-only prep ledger before run readiness\n"
            "              (add | add-from-route | list | next | resolve-next)\n"
            "  queue     → compatibility alias for prep-ledger\n"
            "              legacy readiness aliases live here for compatibility; prefer `prep-ledger`\n"
            "  walkthrough → guided intake setup and validation tutorial\n"
            "              (no-arg demo, or --intake-out for a real intake file)\n"
            "  source-init → create source-ingest project surface\n"
            "              (raw/ + workspace/ + source_type_map; does not launch autoresearch)\n"
            "  source-check → inspect raw source typing before evidence compilation\n"
            "              (offline preflight; no model call)\n"
            "  source-index → write workspace source index from typed raw sources\n"
            "              (offline checkpoint; no model call, no evidence compilation)\n"
            "  evidence-bind → bind current rendered evidence outputs to compile provenance\n"
            "              (offline compatibility receipt; no model call, no evidence compilation)\n"
            "  evidence-replay → verify compiled evidence replay manifest against current files\n"
            "              (offline replay check; no model call, no evidence compilation)\n"
            "  claim-support → classify compiled-evidence claims by source support\n"
            "              (offline audit; no model call, no semantic entailment claim)\n"
            "  evidence-gap → resolve or justify current evidence gaps with receipts\n"
            "              (justify; offline receipt, no model call, no evidence fetch)\n"
            "  portfolio-list → list registered project portfolio entries\n"
            "              (shells to `make portfolio-list`)\n"
            "  portfolio-scaffold → scaffold registered project surfaces\n"
            "              (shells to `make portfolio-scaffold`)\n\n"
            "Aliases: `generate` = `new`; `setup` = `prepare`.\n\n"
            "`prepare` and `seal` flags:\n"
            "  --project <slug>   required\n"
            "  --rubric <name>    required\n"
            "  --model <model>    optional for prepare\n\n"
            "An intake `task` is the bounded work item intended for a later\n"
            "`ztare autoresearch route` or `ztare autoresearch run`; it is not\n"
            f"executed by the {command_name} CLI. The prep ledger is only an\n"
            "auditable record for intake-readiness work, not RD execution and not an\n"
            "autoresearch scheduler.\n\n"
            "For generator flags, run:\n"
            f"  ztare {command_name} new --help\n"
        )
        return 0
    verb, *args = rest
    if verb in ("new", "generate"):
        return _delegate_module("ztare.scaffold.generate_substrate", args)
    if verb in ("prepare", "setup"):
        kv = _parse_kv_flags(args, allowed={"--project", "--rubric", "--model"})
        if not kv.get("--project") or not kv.get("--rubric"):
            print(f"ztare: `{command_name} prepare` requires --project <slug> --rubric <name>",
                  file=sys.stderr)
            return 2
        return _delegate_make("setup-project", {
            "PROJECT": kv.get("--project", ""),
            "RUBRIC": kv.get("--rubric", ""),
            "MODEL": kv.get("--model", ""),
        })
    if verb == "seal":
        kv = _parse_kv_flags(args, allowed={"--project", "--rubric"})
        if not kv.get("--project") or not kv.get("--rubric"):
            print(f"ztare: `{command_name} seal` requires --project <slug> --rubric <name>",
                  file=sys.stderr)
            return 2
        return _delegate_make("seal", {
            "PROJECT": kv.get("--project", ""),
            "RUBRIC": kv.get("--rubric", ""),
        })
    if verb in ("queue", "prep-ledger"):
        normalized = _normalize_queue_dir_flag(args)
        if normalized is None:
            return 2
        normalized_args, queue_dir = normalized
        delegated_args = normalized_args
        if queue_dir:
            delegated_args = ["--queue-dir", queue_dir, *delegated_args]
        return _delegate_module("ztare.scaffold.substrate_queue", delegated_args)
    if verb in ("intake", "packet"):
        preferred = "intake"
        compatibility_note = (
            "\nCompatibility: `project packet` delegates to this same intake command.\n"
            if verb == "intake"
            else "\nCompatibility: `project packet` is the legacy spelling; prefer `project intake`.\n"
        )
        if not args or args[0] in ("-h", "--help"):
            print(
                f"ztare {command_name} {verb} <create|draft-from-compiled|validate|falsify|enqueue> [args...]\n\n"
                "Project intake makes the boundary explicit before in-loop\n"
                "autoresearch: task, bounded claim, source refs, evidence refs,\n"
                "non-claims, next falsifier, expected command, and local\n"
                "source-preflight. Enqueue requires the preflight to pass.\n"
                f"{compatibility_note}\n"
                "Examples:\n"
                f"  ztare {command_name} {preferred} create --path demo_intake.json --project demo --rubric demo --task \"test bounded claim\" ...\n"
                f"  ztare {command_name} {preferred} draft-from-compiled --project demo --path projects/demo/demo_intake.json\n"
                f"  ztare {command_name} {preferred} validate --path demo_intake.json\n"
                f"  ztare {command_name} {preferred} falsify --path demo_intake.json --remove-ref 'evidence_refs[1]' --write-workspace-receipt\n"
                f"  ztare {command_name} {preferred} validate --path demo_intake.json --source-preflight\n"
                f"  ztare {command_name} {preferred} enqueue --path demo_intake.json\n"
            )
            return 0
        action, *packet_args = args
        mapping = {
            "create": "create-packet",
            "draft-from-compiled": "draft-from-compiled",
            "validate": "validate-packet",
            "falsify": "falsify-packet",
            "enqueue": "enqueue-packet",
        }
        if action not in mapping:
            print(
                f"ztare: unknown {command_name} {verb} action {action!r}. Known: create, draft-from-compiled, validate, falsify, enqueue",
                file=sys.stderr,
            )
            return 2
        normalized = _normalize_queue_dir_flag(packet_args)
        if normalized is None:
            return 2
        normalized_args, queue_dir = normalized
        delegated_args = [mapping[action], *normalized_args]
        if queue_dir:
            delegated_args = ["--queue-dir", queue_dir, *delegated_args]
        return _delegate_module("ztare.scaffold.substrate_queue", delegated_args)
    if verb == "walkthrough":
        return _delegate_module("ztare.scaffold.substrate_walkthrough", args)
    if verb == "source-init":
        return _delegate_module("ztare.scaffold.source_project", args)
    if verb == "source-check":
        return _delegate_module("ztare.scaffold.source_check", args)
    if verb == "source-index":
        return _delegate_module("ztare.workspace.update_workspace", ["--index-only", *args])
    if verb == "evidence-bind":
        return _delegate_module("ztare.workspace.evidence_output_binding", args)
    if verb == "evidence-replay":
        return _delegate_module("ztare.workspace.evidence_replay", args)
    if verb == "claim-support":
        return _delegate_module("ztare.workspace.claim_support", args)
    if verb == "evidence-gap":
        return _delegate_module("ztare.workspace.evidence_gap_resolutions", args)
    if verb == "portfolio-list":
        return _delegate_make("portfolio-list", {})
    if verb == "portfolio-scaffold":
        return _delegate_make("portfolio-scaffold", {})
    print(
        f"ztare: unknown {command_name} verb "
        f"{verb!r}. Known: new, prepare, seal, intake, packet, prep-ledger, queue, walkthrough, source-init, source-check, source-index, evidence-bind, evidence-replay, claim-support, evidence-gap, portfolio-list, portfolio-scaffold",
        file=sys.stderr,
    )
    return 2


def _cmd_project_router(rest: list[str]) -> int:
    return _cmd_substrate_router(rest, command_name="project")


# `ztare primitive <verb>` — capability-catalog / primitive-amnesia preflight.
_PRIMITIVE_LEAF_HELP: dict[str, str] = {
    "health": (
        "ztare primitive health [flags]\n\n"
        "Run catalog health, semantic-atlas freshness, and optional live/eval checks.\n\n"
        "Flags:\n"
        "  --json           pass JSON mode to catalog-health\n"
        "  --semantic-live  also check live semantic embedder availability\n"
        "  --eval           also run primitive-amnesia retrieval eval\n"
    ),
    "parent-utility": (
        "ztare primitive parent-utility [--json]\n\n"
        "Check whether primitive parent nodes route to useful children.\n\n"
        "Flags:\n"
        "  --json           optional JSON report\n"
    ),
    "utility": (
        "ztare primitive utility [--json]\n\n"
        "Alias for `ztare primitive parent-utility`.\n\n"
        "Flags:\n"
        "  --json           optional JSON report\n"
    ),
}


def _print_primitive_leaf_help(verb: str) -> int:
    help_text = _PRIMITIVE_LEAF_HELP.get(verb)
    if not help_text:
        return 2
    print(help_text)
    return 0


def _cmd_primitive_router(rest: list[str]) -> int:
    if not rest or rest[0] in ("-h", "--help"):
        print(
            "ztare primitive <verb> [args...]\n\n"
            "Verbs:\n"
            "  health   →  run catalog health + atlas freshness checks\n\n"
            "  parent-utility → check whether primitive parent nodes route to useful children\n\n"
            "`health` flags:\n"
            "  --json           pass JSON mode to catalog-health\n"
            "  --semantic-live  also check live semantic embedder availability\n"
            "  --eval           also run primitive-amnesia retrieval eval\n"
        )
        return 0
    verb, *args = rest
    if args and args[0] in ("-h", "--help") and verb in _PRIMITIVE_LEAF_HELP:
        return _print_primitive_leaf_help(verb)
    if verb == "health":
        bools = _parse_bool_flags(args, allowed={"--json", "--semantic-live", "--eval"})
        rc = _delegate_make("primitive-catalog-health", {
            "JSON": "1" if "--json" in bools else "",
        })
        if rc != 0:
            return rc
        rc = _delegate_module(
            "ztare.research_director.primitive_amnesia",
            ["--atlas-status"],
        )
        if rc != 0:
            return rc
        if "--semantic-live" in bools:
            rc = _delegate_module(
                "ztare.research_director.primitive_amnesia",
                ["--semantic-live"],
            )
            if rc != 0:
                return rc
        if "--eval" in bools:
            rc = _delegate_module(
                "ztare.research_director.primitive_amnesia",
                ["--eval"],
            )
            if rc != 0:
                return rc
        return 0
    if verb in ("parent-utility", "utility"):
        bools = _parse_bool_flags(args, allowed={"--json"})
        return _delegate_make("primitive-parent-utility", {
            "JSON": "1" if "--json" in bools else "",
        })
    print(
        f"ztare: unknown primitive verb {verb!r}. Known: health, parent-utility",
        file=sys.stderr,
    )
    return 2


# `ztare audit <verb>` — verb router over public audit Make targets.
_AUDIT_TARGETS = {
    "gates": "audit-gate-effectiveness",
    "effectiveness": "audit-gate-effectiveness",
    "coverage": "audit-gate-coverage",
    "graph-capability": "graph-capability-audit",
    "forecast-capability": "forecast-capability-audit",
    "move-card-router": "move-card-router-audit",
    "operator-card-router": "operator-card-router-audit",
}

_AUDIT_MODULE_TARGETS = {
    "graph-capability": "ztare.reports.graph_capability_audit",
    "forecast-capability": "ztare.reports.forecast_capability_audit",
    "move-card-router": "ztare.reports.operator_card_router_audit",
    "operator-card-router": "ztare.reports.operator_card_router_audit",
}


def _cmd_audit_router(rest: list[str]) -> int:
    if not rest or rest[0] in ("-h", "--help"):
        print(
            "ztare audit <verb> [--strict] [--json] [--verbose]\n\n"
            "Verbs:\n"
            "  gates|effectiveness  →  audit-gate-effectiveness\n"
            "  coverage             →  audit-gate-coverage\n"
            "  graph-capability     →  graph-capability-audit\n"
            "  forecast-capability  →  forecast-capability-audit\n"
            "  move-card-router     →  move-card-router-audit\n"
            "  operator-card-router →  legacy alias\n"
            "\n`--json` is supported by the capability audits; gate audits also\n"
            "accept `--strict` and `--verbose`.\n"
        )
        return 0
    verb, *args = rest
    flags = _parse_bool_flags(args, allowed={"--strict", "--json", "--verbose"})
    target = _AUDIT_TARGETS.get(verb)
    if target is None:
        print(
            f"ztare: unknown audit verb {verb!r}. "
            f"Known: {', '.join(_AUDIT_TARGETS)}",
            file=sys.stderr,
        )
        return 2
    module_target = _AUDIT_MODULE_TARGETS.get(verb)
    if module_target is not None:
        if flags.get("--strict") or flags.get("--verbose"):
            print(
                f"ztare: audit {verb} supports --json only",
                file=sys.stderr,
            )
            return 2
        module_args = ["--json"] if flags.get("--json") else []
        return _delegate_module(module_target, module_args)
    return _delegate_make(target, {
        "STRICT": "1" if flags.get("--strict") else "",
        "JSON": "1" if flags.get("--json") else "",
        "VERBOSE": "1" if flags.get("--verbose") else "",
    })


# `ztare arch-validate <verb>` — wraps the GP-101 arch-map drift check.
def _cmd_arch_validate_router(rest: list[str]) -> int:
    if not rest or rest[0] in ("-h", "--help"):
        print(
            "ztare arch-validate <verb> [--only <map>]\n\n"
            "Verbs:\n"
            "  ex-ante  →  arch-validate-ex-ante (run before editing)\n"
            "  ex-post  →  arch-validate (run after editing; default)\n\n"
            "Optional: --only <label> restricts scope to one map\n"
            "(per MAP_REGISTRY in the validator).\n"
        )
        return 0
    verb, *args = rest
    kv = _parse_kv_flags(args, allowed={"--only"})
    if verb == "ex-ante":
        return _delegate_make("arch-validate-ex-ante", {"ARCH_MAP": kv.get("--only", "")})
    if verb == "ex-post":
        return _delegate_make("arch-validate", {"ARCH_MAP": kv.get("--only", "")})
    print(
        f"ztare: unknown arch-validate verb {verb!r}. Known: ex-ante, ex-post",
        file=sys.stderr,
    )
    return 2


def _parse_kv_flags(args: list[str], allowed: set[str]) -> dict[str, str]:
    """Parse a list of `--key value` flag pairs into a dict. Unknown flags
    are ignored silently so the shell-out target can complain itself."""
    out: dict[str, str] = {}
    i = 0
    while i < len(args):
        a = args[i]
        if a in allowed and i + 1 < len(args):
            out[a] = args[i + 1]
            i += 2
        else:
            i += 1
    return out


def _parse_bool_flags(args: list[str], allowed: set[str]) -> dict[str, bool]:
    """Parse a list of boolean flags into a dict of {flag: True} for the
    ones present in ``allowed``."""
    return {flag: True for flag in args if flag in allowed}


# ---------------------------------------------------------------------------
# Self-describing subcommands (no script delegation)
# ---------------------------------------------------------------------------


def _ztare_version() -> str:
    """Resolve the installed ZTARE version from package metadata, falling
    back to the ``[project].version`` field in ``pyproject.toml`` for a
    developer checkout, then to ``unknown``. Never raises."""
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version("ztare")
    except PackageNotFoundError:
        pass
    try:
        import tomllib

        root = _repo_root()
        pyproject = root / "pyproject.toml"
        if pyproject.is_file():
            with pyproject.open("rb") as fh:
                data = tomllib.load(fh)
            return data.get("project", {}).get("version", "unknown")
    except (RuntimeError, OSError, tomllib.TOMLDecodeError):
        pass
    return "unknown"


def _git_commit_short() -> str:
    """Short git HEAD for the repo; ``unknown`` if git is unavailable."""
    try:
        root = _repo_root()
    except RuntimeError:
        return "unknown"
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--short=12", "HEAD"],
            capture_output=True, text=True, timeout=3, check=False,
        )
        if proc.returncode == 0:
            return proc.stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        pass
    return "unknown"


def _cmd_version(_rest: list[str]) -> int:
    print(
        f"ztare {_ztare_version()} "
        f"(git {_git_commit_short()}, "
        f"python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro})"
    )
    return 0


# ---------------------------------------------------------------------------
# `ztare doctor` — environment health check
# ---------------------------------------------------------------------------


def _which(binary: str) -> str | None:
    """Resolve a binary on PATH; ``None`` if not found."""
    from shutil import which

    return which(binary)


def _cmd_doctor(_rest: list[str]) -> int:
    """Report the workbench runtime environment honestly. Never mutates
    anything; always exits 0 (doctor reports, the maintainer decides). The
    output is plain text so it is greppable and pipeable."""
    print(f"ztare {_ztare_version()}  (git {_git_commit_short()})")
    print(f"python  : {sys.version.splitlines()[0]}")
    print(f"platform: {sys.platform}")
    try:
        root = _repo_root()
        print(f"repo    : {root}")
    except RuntimeError as exc:
        print(f"repo    : NOT FOUND — {exc}")
        return 0
    control = root / "scripts" / "public" / "control"
    print(f"control : {control}  ({'ok' if control.is_dir() else 'MISSING'})")

    # Python floor — pyproject.toml pins requires-python = ">=3.11"
    print()
    py_ok = sys.version_info >= (3, 11)
    print(f"python floor (>=3.11): {'ok' if py_ok else f'FAIL (have {sys.version_info.major}.{sys.version_info.minor})'}")

    # Package importability: if any of these fail, the installed workbench is broken.
    print()
    print("package imports:")
    for mod in ("ztare", "ztare.cli", "ztare.leanmill.work_queue",
                "ztare.leanmill.paths", "ztare.leanmill.policy",
                "ztare.leanmill.common"):
        try:
            __import__(mod)
            print(f"  {mod:<30} ok")
        except Exception as exc:  # noqa: BLE001 — doctor is read-only and must not raise
            print(f"  {mod:<30} FAIL — {type(exc).__name__}: {exc}")

    # Per-subcommand dispatch resolution
    print()
    print("subcommand → target (resolution check):")
    name_width = 40
    kind_width = 9
    for verb, (kind, target) in _FORECAST_VERBS.items():
        mark = _forecast_resolution_status(root, control, kind, target)
        print(f"  {'forecast:' + verb:<{name_width}}{kind:<{kind_width}}{target:<72} {mark}")
    for name, (_, _handler, scripts) in _SUBCOMMANDS_METADATA.items():
        if name == "forecast":
            continue
        if not scripts:
            print(f"  {name:<{name_width}} (built-in)")
            continue
        for script in scripts:
            present = (control / script).is_file()
            mark = "ok" if present else "MISSING"
            print(f"  {name:<{name_width}}{'control':<{kind_width}}{script:<72} {mark}")

    # External CLIs the workbench may shell out to.
    print()
    print("external tools:")
    for binary in ("lean", "lake", "codex", "claude", "git"):
        found = _which(binary)
        print(f"  {binary:<8} {found or '(not on PATH)'}")

    # Env vars the workbench reads.
    print()
    print("environment:")
    try:
        from ztare.common.llm_runtime import _bootstrap_dotenv_if_needed

        _bootstrap_dotenv_if_needed()
    except Exception:
        pass
    for var in (
        "ZTARE_REPO",
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "GEMINI_API_KEY",
        "KIMI_API_KEY",
        "MOONSHOT_API_KEY",
        "XAI_API_KEY",
        "GROK_API_KEY",
    ):
        val = os.environ.get(var)
        if not val:
            shown = "(unset)"
        elif var.endswith("_API_KEY"):
            shown = f"set ({len(val)} chars)"
        else:
            shown = val
        print(f"  {var:<24} {shown}")
    return 0


def _forecast_resolution_status(root: Path, control: Path, kind: str, target: str) -> str:
    if kind == "control":
        return "ok" if (control / target).is_file() else "MISSING"
    if kind == "script":
        return "ok" if (root / target).is_file() else "MISSING"
    if kind == "module":
        return "ok" if importlib.util.find_spec(target) is not None else "MISSING"
    return "UNKNOWN_KIND"


# ---------------------------------------------------------------------------
# `ztare completion` — shell completion script emitter
# ---------------------------------------------------------------------------


_COMPLETION_SHELLS = ("bash", "zsh", "fish")
_AUTORESEARCH_VERBS = (
    "run",
    "route",
    "projection",
    "trace",
    "carrier-replay",
    "dispatch-audit",
    "dispatch-canary",
    "dispatch-parity",
    "subscription-outcomes",
    "matched-transport-pair",
    "hillclimb-audit",
    "consequence-audit",
    "rubric-mode-audit",
    "health",
    "operations-intelligence",
    "workbench-recommend",
    "substrate-recommend",
    "catalog-health",
    "parent-utility",
    "fixtures",
    "control-demo",
    "hardening",
    "portfolio",
)
_SUBSTRATE_VERBS = (
    "new",
    "prepare",
    "seal",
    "intake",
    "packet",
    "queue",
    "walkthrough",
    "source-init",
    "source-check",
    "source-index",
    "evidence-bind",
    "evidence-replay",
    "evidence-gap",
    "portfolio-list",
    "portfolio-scaffold",
    "generate",
    "setup",
)
_EIGENQUESTION_VERBS = ("propose", "validate", "status")
_PRIMITIVE_VERBS = ("health", "parent-utility", "utility")
_AUDIT_VERBS = tuple(_AUDIT_TARGETS)
_ARCH_VALIDATE_VERBS = ("ex-ante", "ex-post")


def _completion_word_list(words: Iterable[str]) -> str:
    return " ".join(words)


def _completion_verb_sets() -> dict[str, str]:
    return {
        "forecast": _completion_word_list(_FORECAST_VERBS),
        "leanmill": _completion_word_list(_LEANMILL_VERBS),
        "bundle": _completion_word_list(_BUNDLE_VERBS),
        "eigenquestion": _completion_word_list(_EIGENQUESTION_VERBS),
        "autoresearch": _completion_word_list(_AUTORESEARCH_VERBS),
        "project": _completion_word_list(_SUBSTRATE_VERBS),
        "substrate": _completion_word_list(_SUBSTRATE_VERBS),
        "primitive": _completion_word_list(_PRIMITIVE_VERBS),
        "audit": _completion_word_list(_AUDIT_VERBS),
        "arch-validate": _completion_word_list(_ARCH_VALIDATE_VERBS),
    }


def _bash_completion_case_arms(verb_sets: dict[str, str]) -> str:
    return "\n".join(
        f'      {command}) COMPREPLY=( $(compgen -W "{words}" -- "$cur") ) ;;'
        for command, words in verb_sets.items()
    )


def _zsh_completion_case_arms(verb_sets: dict[str, str]) -> str:
    return "\n".join(
        f"    {command}) compadd -- {words} ;;"
        for command, words in verb_sets.items()
    )


def _cmd_completion(rest: list[str]) -> int:
    """Emit a completion script for the named shell to stdout.

    Usage:  ztare completion <bash|zsh|fish>

    The scripts complete the top-level subcommands and the stable verb
    routers. They do not introspect the
    underlying control scripts' own flags — pipe to the right rc file
    and reload.
    """
    if not rest or rest[0] in ("-h", "--help"):
        print(f"ztare completion <{('|').join(_COMPLETION_SHELLS)}>")
        print("\nEmit a shell-completion script to stdout. Source the output:")
        print("  bash:  ztare completion bash  > ~/.local/share/bash-completion/completions/ztare")
        print("  zsh :  ztare completion zsh   > \"${fpath[1]}/_ztare\"")
        print("  fish:  ztare completion fish  > ~/.config/fish/completions/ztare.fish")
        return 0
    shell = rest[0].lower()
    if shell not in _COMPLETION_SHELLS:
        print(f"ztare: unsupported shell {shell!r}. Supported: {', '.join(_COMPLETION_SHELLS)}", file=sys.stderr)
        return 2
    commands = " ".join(_SUBCOMMANDS.keys())
    verb_sets = _completion_verb_sets()
    if shell == "bash":
        print(_BASH_COMPLETION_TEMPLATE.format(
            commands=commands,
            verb_case_arms=_bash_completion_case_arms(verb_sets),
        ))
    elif shell == "zsh":
        print(_ZSH_COMPLETION_TEMPLATE.format(
            commands=commands,
            verb_case_arms=_zsh_completion_case_arms(verb_sets),
        ))
    elif shell == "fish":
        # Fish format: one completion per line. Build commands then verbs.
        lines = ["# ztare completion (fish)"]
        for cmd in _SUBCOMMANDS:
            help_text = _SUBCOMMANDS[cmd][0].splitlines()[0]
            lines.append(f"complete -c ztare -f -n '__fish_use_subcommand' -a '{cmd}' -d {help_text!r}")
        for command, words in verb_sets.items():
            for verb in words.split():
                lines.append(f"complete -c ztare -f -n '__fish_seen_subcommand_from {command}' -a '{verb}'")
        print("\n".join(lines))
    return 0


_BASH_COMPLETION_TEMPLATE = r"""# bash completion for ztare
_ztare_complete() {{
  local cur prev cmds
  COMPREPLY=()
  cur="${{COMP_WORDS[COMP_CWORD]}}"
  prev="${{COMP_WORDS[COMP_CWORD-1]}}"
  cmds="{commands}"
  if [ "$COMP_CWORD" -eq 1 ]; then
    COMPREPLY=( $(compgen -W "$cmds" -- "$cur") )
    return 0
  fi
  if [ "$COMP_CWORD" -eq 2 ]; then
    case "$prev" in
{verb_case_arms}
    esac
  fi
}}
complete -F _ztare_complete ztare
"""


_ZSH_COMPLETION_TEMPLATE = r"""#compdef ztare
# zsh completion for ztare
_ztare() {{
  local -a commands
  commands=({commands})
  if (( CURRENT == 2 )); then
    compadd -- "${{commands[@]}}"
    return
  fi
  case "${{words[2]}}" in
{verb_case_arms}
  esac
}}
compdef _ztare ztare
"""


# ---------------------------------------------------------------------------
# Subcommand registry
# ---------------------------------------------------------------------------


_SUBCOMMANDS: dict[str, tuple[str, Callable[[list[str]], int]]] = {
    "forecast": (
        "Forecast operations: pool, calibration, validity gates, and experiment runners.",
        _cmd_forecast_router,
    ),
    "leanmill": (
        "LeanMill governed proof search: schedule | run | proof-audit | harness | source-scout.",
        _cmd_leanmill_router,
    ),
    "bundle": (
        "Sealed-bundle gates: run | verify.",
        _cmd_bundle_router,
    ),
    "charter": (
        "Project-charter commit (pre-registered hypothesis).",
        lambda rest: _delegate("charter_commit.py", rest),
    ),
    "routine-review": (
        "RD routine reviews (the standing reconciliation loop).",
        lambda rest: _delegate("rd_routine_review.py", rest),
    ),
    "action-intel": (
        "Action intelligence read surface: decisions, routes, and outcome impact.",
        lambda rest: _delegate("action_intelligence.py", rest),
    ),
    "eigenquestion": (
        "Eigenquestion generator: propose | validate | status.",
        _cmd_eigenquestion_router,
    ),
    "mine": (
        "Weekly reflexive-mining run (the canonical orchestrator).",
        _cmd_mine,
    ),
    "autoresearch": (
        "In-loop autoresearch kernel: route | run | trace | projection | replay | health.",
        _cmd_autoresearch_router,
    ),
    "forensic-workbench": (
        "Local review workbench: apply-review.",
        _make_verb_router("forensic-workbench", {"apply-review": "forensic_workbench_review.py"}),
    ),
    "project": (
        "Project userland: walkthrough | source-init | source-check | source-index | evidence-bind | evidence-replay | evidence-gap | new | prepare | seal | intake | prep-ledger.",
        _cmd_project_router,
    ),
    "substrate": (
        "Compatibility alias for project/data surface userland.",
        _cmd_substrate_router,
    ),
    "primitive": (
        "Primitive catalog / amnesia health: health.",
        _cmd_primitive_router,
    ),
    "audit": (
        "Audits: gates | effectiveness | coverage | graph-capability | forecast-capability | move-card-router. Shells to Make.",
        _cmd_audit_router,
    ),
    "arch-validate": (
        "Architecture-map drift check: ex-ante | ex-post. Shells to Make.",
        _cmd_arch_validate_router,
    ),
    "version": (
        "Print ZTARE version, git commit, and Python version.",
        _cmd_version,
    ),
    "doctor": (
        "Environment health check (paths, scripts, external tools, env vars).",
        _cmd_doctor,
    ),
    "completion": (
        "Emit shell completion script (bash | zsh | fish).",
        _cmd_completion,
    ),
}


# Metadata used by `doctor` to verify each subcommand's underlying script
# exists. Built-in subcommands (no script delegation) have an empty tuple.
_SUBCOMMANDS_METADATA: dict[str, tuple[str, Callable[[list[str]], int], tuple[str, ...]]] = {
    # doctor only verifies scripts under scripts/public/control/; the
    # `score` verb (analytics_shared) and module verbs are intentionally
    # excluded from the control-script presence check.
    "forecast": (_SUBCOMMANDS["forecast"][0], _SUBCOMMANDS["forecast"][1], (
        "forecast/pool.py", "forecast/resolve_from_json.py",
    )),
    "leanmill": (_SUBCOMMANDS["leanmill"][0], _SUBCOMMANDS["leanmill"][1], (
        "leanmill/station_scheduler.py", "leanmill/24x7_runner.py",
        "leanmill/andon_cord.py", "leanmill/post_probe_triage.py",
        "leanmill/backlog_replenisher.py",
    )),
    "bundle": (_SUBCOMMANDS["bundle"][0], _SUBCOMMANDS["bundle"][1], ("bundle_run.py", "bundle_verify.py")),
    "charter": (_SUBCOMMANDS["charter"][0], _SUBCOMMANDS["charter"][1], ("charter_commit.py",)),
    "routine-review": (_SUBCOMMANDS["routine-review"][0], _SUBCOMMANDS["routine-review"][1], ("rd_routine_review.py",)),
    "action-intel": (_SUBCOMMANDS["action-intel"][0], _SUBCOMMANDS["action-intel"][1], ("action_intelligence.py",)),
    # Non-control-script shells: empty tuple per the doctor-check contract
    # (doctor only verifies scripts/public/control/*.py existence; module
    # and Make targets are checked by their own validators / by Make itself).
    "eigenquestion": (_SUBCOMMANDS["eigenquestion"][0], _SUBCOMMANDS["eigenquestion"][1], ()),
    "mine": (_SUBCOMMANDS["mine"][0], _SUBCOMMANDS["mine"][1], ()),
    "autoresearch": (_SUBCOMMANDS["autoresearch"][0], _SUBCOMMANDS["autoresearch"][1], ()),
    "forensic-workbench": (
        _SUBCOMMANDS["forensic-workbench"][0],
        _SUBCOMMANDS["forensic-workbench"][1],
        ("forensic_workbench_review.py",),
    ),
    "project": (_SUBCOMMANDS["project"][0], _SUBCOMMANDS["project"][1], ()),
    "substrate": (_SUBCOMMANDS["substrate"][0], _SUBCOMMANDS["substrate"][1], ()),
    "primitive": (_SUBCOMMANDS["primitive"][0], _SUBCOMMANDS["primitive"][1], ()),
    "audit": (_SUBCOMMANDS["audit"][0], _SUBCOMMANDS["audit"][1], ()),
    "arch-validate": (_SUBCOMMANDS["arch-validate"][0], _SUBCOMMANDS["arch-validate"][1], ()),
    "version": (_SUBCOMMANDS["version"][0], _SUBCOMMANDS["version"][1], ()),
    "doctor": (_SUBCOMMANDS["doctor"][0], _SUBCOMMANDS["doctor"][1], ()),
    "completion": (_SUBCOMMANDS["completion"][0], _SUBCOMMANDS["completion"][1], ()),
}


# ---------------------------------------------------------------------------
# Top-level help + main
# ---------------------------------------------------------------------------


def _print_top_help() -> None:
    print(
        "usage: ztare COMMAND [args...]\n\n"
        "ZTARE — zero-trust workbench for generating, stress-testing, and auditing claims.\n"
        "Subcommands expose the public userland around the kernel.\n\n"
        "Commands:"
    )
    name_width = max(len(name) for name in _SUBCOMMANDS) + 2
    for name, (help_text, _) in _SUBCOMMANDS.items():
        print(f"  {name:<{name_width}}{help_text}")
    print(
        "\nFor a subcommand's full options, run `ztare COMMAND --help` — the\n"
        "flag flows through to the underlying control script."
    )


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help"):
        _print_top_help()
        return 0
    if argv[0] in ("-V", "--version"):
        return _cmd_version([])
    cmd, *rest = argv
    if cmd not in _SUBCOMMANDS:
        print(f"ztare: unknown command {cmd!r}\n", file=sys.stderr)
        _print_top_help()
        return 2
    try:
        result = _SUBCOMMANDS[cmd][1](rest)
    except KeyboardInterrupt:
        print("ztare: interrupted", file=sys.stderr)
        return 130
    # Handlers may return None (treated as success) or int. Anything else is
    # a programming error and should surface loudly rather than be coerced.
    if result is None:
        return 0
    if not isinstance(result, int):
        print(
            f"ztare: handler for {cmd!r} returned non-int {type(result).__name__}; "
            "treating as failure",
            file=sys.stderr,
        )
        return 1
    return result


if __name__ == "__main__":
    raise SystemExit(main())
