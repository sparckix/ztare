# SPDX-License-Identifier: MIT
"""``ztare`` — the adversarial-reasoning engine's operator CLI.

A thin entry point that wraps the existing operator scripts under
``scripts/public/control/`` so the apparatus is callable as a single
command instead of ``cd repo && python scripts/public/control/<name>.py``.

**Scope of this CLI.** ZTARE the engine, not the operator's tenant
overlay. The subcommands cover the adversarial-reasoning kernel —
forecast pool, LeanMill, bundle gates, project charter, RD routine
review, action intelligence — and the substrate's research-side
operations. The governance / org side (roles, mandates, role daemons,
closure daemons, OKR-tree polling) belongs to ``cognitive-firm`` and is
deliberately *not* exposed here; operators who want those primitives
should install ``cognitive-firm`` alongside ZTARE.

Design notes:

- Stdlib-only (``argparse`` + ``subprocess``). No new runtime deps.
- Subprocess delegation preserves each underlying script's full
  argument surface; pass ``--help`` to any subcommand to see what the
  underlying script accepts (e.g. ``ztare forecast --help``).
- The CLI assumes a ZTARE checkout is the working directory (the
  scripts read ledgers by relative path). Repo-root detection walks up
  from the current file location and falls back to the cwd; set
  ``ZTARE_REPO`` to override.

Current subcommands: ``forecast``, ``leanmill``, ``bundle``,
``charter``, ``routine-review``, ``action-intel``, plus the
self-describing ``version``, ``doctor``, and ``completion``. The set is
deliberately small. Add new subcommands by extending ``_SUBCOMMANDS``
and writing a thin handler that delegates to a control script.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
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


# `ztare forecast <verb>` — verb router over the forecast operator surface.
# Mixed delegation: reusable control scripts under scripts/public/control/,
# project-local experiment tools, and registered console-script modules under
# `ztare.forecasting`. Each tuple is (kind, target):
#   ("control", "<name>.py")        → scripts/public/control/<name>.py
#   ("script",  "<rel/path.py>")    → <repo_root>/<rel/path.py>
#   ("module",  "<dotted.path>")    → python -m <dotted.path>
_FORECAST_VERBS: dict[str, tuple[str, str]] = {
    "pool":              ("control", "forecast/pool.py"),
    "resolve":           ("control", "forecast/resolve_from_json.py"),
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
            if kind == "control":
                shown = f"scripts/public/control/{target}"
            elif kind == "script":
                shown = target
            else:
                shown = f"python -m {target}"
            print(f"  {verb:<{width}}→ {shown}")
        print("\nFor any verb's own --help, run:\n  ztare forecast <verb> --help")
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


_cmd_leanmill_router = _make_verb_router(
    "leanmill",
    {
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
        # kept as alias for back-compat with operator muscle memory.
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
    },
)


_cmd_bundle_router = _make_verb_router(
    "bundle",
    {
        "run": "bundle_run.py",
        "verify": "bundle_verify.py",
    },
)


# ---------------------------------------------------------------------------
# Thin shells over Python modules / scripts / Make targets.
# Discipline: do not reimplement what the Makefile or a script already does.
# The CLI is a catalog over those entry points — `gh` for the apparatus.
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
            "  health    → aggregate dispatch/catalog/fixture/rubric/control health\n"
            "               (shells to `make autoresearch-kernel-health`)\n"
            "  operations-intelligence → build the read-only RD operations packet\n"
            "               (shells to `make operations-intelligence`)\n"
            "  substrate-recommend → recommend next substrate/workbench surfaces\n"
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
            "  --iters <n>        optional (default per Makefile)\n"
            "  --mutator <model>  optional\n"
            "  --judge <model>    optional\n"
            "  --agent-mutator    route mutator calls through subscription worker\n"
            "  --agent-judge      route judge calls through subscription worker\n"
            "  --agent-committee  route dynamic committee calls through subscription worker\n"
            "  --agent-inverter   route GP-119 inverter calls through subscription worker\n"
            "  --agent-runtime <codex|claude> optional shared subscription runtime\n\n"
            "`route` flags:\n"
            "  --task <text>      required\n"
            "  --project <slug>   optional context label\n"
            "  --rubric <name>    optional context label\n"
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
            "  --iters <n>        optional, default Make ITERS\n"
            "  --pair-id <id>     optional, defaults to a timestamped pair id\n"
            "  --agent-runtime <codex|claude> optional, default codex in Make target\n"
            "  --run              execute both rows; omitted prints commands only\n\n"
            "`hillclimb-audit` flags:\n"
            "  --project <slug>   optional, restrict to one project and archives\n"
            "  --stagnation-threshold <n> optional, default 2\n"
            "  --limit <n>        optional row limit\n"
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
            "  --project <slug>   optional, restrict project-scoped checks where supported\n"
            "  --workspace <path> optional, inspect one workspace for mechanism evidence\n"
            "  --rubric <path>    optional, restrict rubric-mode audit to one rubric\n"
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
            "`substrate-recommend` flags:\n"
            "  --mode <cold|branch> optional, default cold\n"
            "  --n <count>        optional, default 3\n"
            "  --class <label>    optional operator class hint\n"
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
    if verb == "run":
        kv = _parse_kv_flags(args, allowed={"--project", "--rubric", "--iters",
                                             "--mutator", "--judge", "--agent-runtime"})
        bools = _parse_bool_flags(
            args,
            allowed={"--agent-mutator", "--agent-judge", "--agent-committee", "--agent-inverter"},
        )
        if not kv.get("--project") or not kv.get("--rubric"):
            print("ztare: `autoresearch run` requires --project <slug> --rubric <name>",
                  file=sys.stderr)
            return 2
        return _delegate_make("experiment-loop", {
            "PROJECT": kv.get("--project", ""),
            "RUBRIC": kv.get("--rubric", ""),
            "ITERS": kv.get("--iters", ""),
            "MUTATOR_MODEL": kv.get("--mutator", ""),
            "JUDGE_MODEL": kv.get("--judge", ""),
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
                "out of loop.\n\n"
                "Flags:\n"
                "  --task <text>      required\n"
                "  --project <slug>   optional context for surface inference\n"
                "  --rubric <name>    optional context for surface inference\n"
                "  --bounded-claim / --no-bounded-claim\n"
                "  --stable-evaluator / --no-stable-evaluator\n"
                "  --rubric-ready / --no-rubric-ready\n"
                "  --artifact-surface / --no-artifact-surface\n"
                "  --subscription-worker-available\n"
                "  --record-decision-id <id>   save route JSON and append an action-intelligence row\n"
                "  --route-json-out <path>     optional route JSON path for --record-decision-id\n"
                "  --selected-action <action>  optional override for the recorded row\n"
                "  --why-not-autoresearch <text> required when bypassing a ready workbench\n"
                "  --dedupe --materialize      optional action-intelligence write flags\n"
                "\nExample:\n"
                "  ztare autoresearch route --task \"test bounded claim\" --project gp_example --rubric gp_example > /tmp/autoresearch_route.json\n"
                "  ztare autoresearch route --task \"test bounded claim\" --project gp_example --rubric gp_example --record-decision-id decision_gp_example_route\n"
                "  ztare action-intel record-agentic-route --route-json /tmp/autoresearch_route.json --decision-id DECISION_ID\n"
            )
            return 0
        kv = _parse_kv_flags(
            args,
            allowed={
                "--task",
                "--project",
                "--rubric",
                "--record-decision-id",
                "--route-json-out",
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
            from src.ztare.research_director.autoresearch_workbench_router import (
                route_autoresearch_workbench_from_context,
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
                stable_evaluator=_bool_override("stable-evaluator"),
                bounded_claim=_bool_override("bounded-claim"),
                rubric_ready=_bool_override("rubric-ready"),
                artifact_surface=_bool_override("artifact-surface"),
                subscription_worker_available="--subscription-worker-available" in bools,
                repo_root=_repo_root(),
            )
            route = decision.to_dict()
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
            try:
                shown_route_path = str(route_path.relative_to(_repo_root()))
            except ValueError:
                shown_route_path = str(route_path)
            print(json.dumps({
                "route_json": shown_route_path,
                "route": route,
                "action_impact": action,
            }, indent=2, sort_keys=True))
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
            allowed={"--project", "--rubric", "--iters", "--pair-id", "--agent-runtime"},
        )
        bools = _parse_bool_flags(args, allowed={"--run"})
        if not kv.get("--project"):
            print("ztare: `autoresearch matched-transport-pair` requires --project <slug>",
                  file=sys.stderr)
            return 2
        return _delegate_make("autoresearch-matched-transport-pair", {
            "PROJECT": kv.get("--project", ""),
            "RUBRIC": kv.get("--rubric", ""),
            "ITERS": kv.get("--iters", ""),
            "MATCHED_RUN_ID": kv.get("--pair-id", ""),
            "AGENT_RUNTIME": kv.get("--agent-runtime", ""),
            "RUN_MATCHED_PAIR": "1" if "--run" in bools else "",
        })
    if verb == "hillclimb-audit":
        kv = _parse_kv_flags(args, allowed={"--project", "--stagnation-threshold", "--limit"})
        bools = _parse_bool_flags(args, allowed={"--json"})
        return _delegate_make("autoresearch-hillclimb-audit", {
            "PROJECT": kv.get("--project", ""),
            "STAGNATION_THRESHOLD": kv.get("--stagnation-threshold", ""),
            "LIMIT": kv.get("--limit", ""),
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
        kv = _parse_kv_flags(args, allowed={"--project", "--workspace", "--rubric", "--stagnation-threshold"})
        bools = _parse_bool_flags(args, allowed={"--json", "--strict"})
        return _delegate_make("autoresearch-kernel-health", {
            "PROJECT": kv.get("--project", ""),
            "WORKSPACE": kv.get("--workspace", ""),
            "RUBRIC": kv.get("--rubric", ""),
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
    if verb == "substrate-recommend":
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
        f"ztare: unknown autoresearch verb {verb!r}. Known: run, route, projection, dispatch-audit, dispatch-canary, dispatch-parity, subscription-outcomes, matched-transport-pair, hillclimb-audit, consequence-audit, rubric-mode-audit, health, operations-intelligence, substrate-recommend, catalog-health, parent-utility, fixtures, control-demo, hardening, portfolio",
        file=sys.stderr,
    )
    return 2


# `ztare primitive <verb>` — capability-catalog / primitive-amnesia preflight.
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


# `ztare audit <verb>` — verb router over the audit-gate-* Make targets.
def _cmd_audit_router(rest: list[str]) -> int:
    if not rest or rest[0] in ("-h", "--help"):
        print(
            "ztare audit <verb> [--strict] [--json] [--verbose]\n\n"
            "Verbs:\n"
            "  gates|effectiveness  →  audit-gate-effectiveness\n"
            "  coverage             →  audit-gate-coverage\n"
            "\nAll flags pass through to the underlying audit script.\n"
        )
        return 0
    verb, *args = rest
    flags = _parse_bool_flags(args, allowed={"--strict", "--json", "--verbose"})
    if verb in ("gates", "effectiveness"):
        target = "audit-gate-effectiveness"
    elif verb == "coverage":
        target = "audit-gate-coverage"
    else:
        print(
            f"ztare: unknown audit verb {verb!r}. "
            "Known: gates, effectiveness, coverage",
            file=sys.stderr,
        )
        return 2
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
    """Report the apparatus's runtime environment honestly. Never mutates
    anything; always exits 0 (doctor reports, the operator decides). The
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

    # Package importability — if any of these fail, the apparatus is broken
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
    print("subcommand → script (resolution check):")
    for name, (_, _handler, scripts) in _SUBCOMMANDS_METADATA.items():
        if not scripts:
            print(f"  {name:<14} (built-in)")
            continue
        for script in scripts:
            present = (control / script).is_file()
            mark = "ok" if present else "MISSING"
            print(f"  {name:<14}{script:<40} {mark}")

    # External CLIs the apparatus may shell out to
    print()
    print("external tools:")
    for binary in ("lean", "lake", "codex", "claude", "git"):
        found = _which(binary)
        print(f"  {binary:<8} {found or '(not on PATH)'}")

    # Env vars the apparatus reads
    print()
    print("environment:")
    for var in ("ZTARE_REPO", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY"):
        val = os.environ.get(var)
        if not val:
            shown = "(unset)"
        elif var.endswith("_API_KEY"):
            shown = f"set ({len(val)} chars)"
        else:
            shown = val
        print(f"  {var:<24} {shown}")
    return 0


# ---------------------------------------------------------------------------
# `ztare completion` — shell completion script emitter
# ---------------------------------------------------------------------------


_COMPLETION_SHELLS = ("bash", "zsh", "fish")


def _cmd_completion(rest: list[str]) -> int:
    """Emit a completion script for the named shell to stdout.

    Usage:  ztare completion <bash|zsh|fish>

    The scripts complete the top-level subcommands and the two verb
    routers (``leanmill``, ``bundle``). They do not introspect the
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
    leanmill_verbs = "schedule run andon triage backlog"
    bundle_verbs = "run verify"
    if shell == "bash":
        print(_BASH_COMPLETION_TEMPLATE.format(
            commands=commands,
            leanmill_verbs=leanmill_verbs,
            bundle_verbs=bundle_verbs,
        ))
    elif shell == "zsh":
        print(_ZSH_COMPLETION_TEMPLATE.format(
            commands=commands,
            leanmill_verbs=leanmill_verbs,
            bundle_verbs=bundle_verbs,
        ))
    elif shell == "fish":
        # Fish format: one completion per line. Build commands then verbs.
        lines = ["# ztare completion (fish)"]
        for cmd in _SUBCOMMANDS:
            help_text = _SUBCOMMANDS[cmd][0].splitlines()[0]
            lines.append(f"complete -c ztare -f -n '__fish_use_subcommand' -a '{cmd}' -d {help_text!r}")
        for verb in leanmill_verbs.split():
            lines.append(f"complete -c ztare -f -n '__fish_seen_subcommand_from leanmill' -a '{verb}'")
        for verb in bundle_verbs.split():
            lines.append(f"complete -c ztare -f -n '__fish_seen_subcommand_from bundle' -a '{verb}'")
        print("\n".join(lines))
    return 0


_BASH_COMPLETION_TEMPLATE = r"""# bash completion for ztare
_ztare_complete() {{
  local cur prev cmds leanmill_v bundle_v
  COMPREPLY=()
  cur="${{COMP_WORDS[COMP_CWORD]}}"
  prev="${{COMP_WORDS[COMP_CWORD-1]}}"
  cmds="{commands}"
  leanmill_v="{leanmill_verbs}"
  bundle_v="{bundle_verbs}"
  if [ "$COMP_CWORD" -eq 1 ]; then
    COMPREPLY=( $(compgen -W "$cmds" -- "$cur") )
    return 0
  fi
  if [ "$COMP_CWORD" -eq 2 ]; then
    case "$prev" in
      leanmill) COMPREPLY=( $(compgen -W "$leanmill_v" -- "$cur") ) ;;
      bundle)   COMPREPLY=( $(compgen -W "$bundle_v"   -- "$cur") ) ;;
    esac
  fi
}}
complete -F _ztare_complete ztare
"""


_ZSH_COMPLETION_TEMPLATE = r"""#compdef ztare
# zsh completion for ztare
_ztare() {{
  local -a commands leanmill_verbs bundle_verbs
  commands=({commands})
  leanmill_verbs=({leanmill_verbs})
  bundle_verbs=({bundle_verbs})
  if (( CURRENT == 2 )); then
    compadd -- "${{commands[@]}}"
    return
  fi
  case "${{words[2]}}" in
    leanmill) compadd -- "${{leanmill_verbs[@]}}" ;;
    bundle)   compadd -- "${{bundle_verbs[@]}}"   ;;
  esac
}}
compdef _ztare ztare
"""


# ---------------------------------------------------------------------------
# Subcommand registry
# ---------------------------------------------------------------------------


_SUBCOMMANDS: dict[str, tuple[str, Callable[[list[str]], int]]] = {
    "forecast": (
        "Forecast operations: pool | resolve | calibration-stats | calibration-db | score | ingest-smoke | cutoff-panel-run | cutoff-panel-ingest | cutoff-panel-score | anti-bias-run | anti-bias-score | nurture-run | nurture-ingest | nurture-score | elo-refresh | brier-elo | resolve-open-metaculus.",
        _cmd_forecast_router,
    ),
    "leanmill": (
        "LeanMill orchestration (GP-225): schedule | run | andon | triage | backlog.",
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
        "Action intelligence read surface (GP-243).",
        lambda rest: _delegate("action_intelligence.py", rest),
    ),
    "eigenquestion": (
        "Eigenquestion generator (GP-228): propose | validate.",
        _cmd_eigenquestion_router,
    ),
    "mine": (
        "Weekly reflexive-mining run (the canonical orchestrator).",
        _cmd_mine,
    ),
    "autoresearch": (
        "Autoresearch pipeline (in-loop validator): run | portfolio. Shells to Make.",
        _cmd_autoresearch_router,
    ),
    "primitive": (
        "Primitive catalog / amnesia health: health.",
        _cmd_primitive_router,
    ),
    "audit": (
        "Gate / coverage audits: gates | effectiveness | coverage. Shells to Make.",
        _cmd_audit_router,
    ),
    "arch-validate": (
        "GP-101 arch-map drift check: ex-ante | ex-post. Shells to Make.",
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
        "ZTARE — adversarial scientific-reasoning engine.\n"
        "Subcommands wrap the apparatus's operator scripts.\n\n"
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
