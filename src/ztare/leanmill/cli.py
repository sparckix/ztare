"""The one sanctioned LeanMill launcher.

A campaign is started here, not by hand-invoking `ztare.leanmill.solver.autoformalize_notes`, so the env that
arms a run — the leaf model, the budget shape — is set from a named profile instead of six environment variables
a caller assembles at the shell and gets wrong. That hand-assembled launch is the mislaunch class: a bare invoke
skips instrument standards, the liveness battery, run-tag attribution, theory consolidation, and the warm
substrate, and the run proves silently degraded while looking healthy. One door removes the chance to skip them.

  leanmill campaign <campaign.md> [--model claude-fable-5] [--profile hard]
  python -m ztare.leanmill.cli campaign <blueprint.md>            # same, uninstalled
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path
import uuid

import yaml

from ztare.leanmill.campaign_profile import (
    AUTOFORMALIZE_CAMPAIGN_PROFILES,
    apply_autoformalize_campaign_profile,
)


def _autoformalize_profile(name: str) -> str:
    if name in AUTOFORMALIZE_CAMPAIGN_PROFILES:
        return name
    if name in {"smoke_20m", "quick"}:
        return "smoke"
    if name in {"deep", "overnight"}:
        return "hard"
    return "default"


def _runtime_role(runtime: dict, name: str) -> dict:
    values = dict(runtime.get("defaults") or {})
    values.update(dict((runtime.get("role_overrides") or {}).get(name) or {}))
    return values


def _theory_file_receipt(notes: str) -> dict:
    """Bind a theory-first campaign to the file it is allowed to extend."""
    try:
        path, declared = _declared_theory_path(notes)
        if path is None:
            return {"declared_path": "", "exists": False}
        if not path.is_file():
            return {"declared_path": declared, "exists": False}
        payload = path.read_bytes()
        return {
            "declared_path": declared,
            "exists": True,
            "sha256": hashlib.sha256(payload).hexdigest(),
            "bytes": len(payload),
        }
    except Exception as exc:  # receipt collection must never block campaign work
        return {"declared_path": "", "exists": False, "error": type(exc).__name__}


def _declared_theory_path(notes: str) -> tuple[Path | None, str]:
    """Resolve the mutable theory-head identity without reading its contents."""
    try:
        from ztare.leanmill.solver.autoformalize_notes import (
            LEAN_ROOT_DEFAULT,
            parse_theory_file,
        )
        declared = str(parse_theory_file(notes) or "").strip()
    except Exception:
        return None, ""
    if not declared:
        return None, ""
    path = Path(declared)
    if not path.is_absolute():
        path = Path(LEAN_ROOT_DEFAULT) / path
    return path.resolve(), declared


def _run_formalization_campaign(manifest, args: argparse.Namespace) -> int:
    from ztare.common.subscription_agent_runtime import subscription_dispatch_budget_scope
    from ztare.leanmill.common import write_json_atomic, write_text_atomic
    from ztare.leanmill.exploration_budget import ExplorationBudgetLedger
    from ztare.leanmill import work_queue
    from ztare.leanmill.solver.solver_core import OUT_DIR

    profile = str(manifest.metadata.get("profile") or "default")
    apply_autoformalize_campaign_profile(_autoformalize_profile(profile))
    os.environ["ZTARE_LEANMILL_CAMPAIGN_WALL_S"] = str(manifest.budget.wall_clock_s)
    formalizer = _runtime_role(dict(manifest.runtime), "formalizer")
    reviewer = _runtime_role(dict(manifest.runtime), "faithfulness_reviewer")
    solver = _runtime_role(dict(manifest.runtime), "lean_solver")
    runtime = str(formalizer.get("runtime") or solver.get("runtime") or "codex")
    if runtime not in {"codex", "claude"}:
        raise ValueError("formalization campaigns require a subscription runtime")
    os.environ["ZTARE_DEFAULT_SUBSCRIPTION_RUNTIME"] = runtime
    os.environ["ZTARE_LEANMILL_LEAF_RUNTIME"] = str(
        solver.get("runtime") or runtime
    )
    os.environ["ZTARE_LEANMILL_SOLVE_PROVIDERS"] = os.environ[
        "ZTARE_LEANMILL_LEAF_RUNTIME"
    ]
    review_runtime = str(reviewer.get("runtime") or runtime)
    os.environ["ZTARE_LEANMILL_ROUNDTRIP_MODEL"] = review_runtime
    for role in (formalizer, reviewer, solver):
        role_runtime = str(role.get("runtime") or runtime)
        model = str(role.get("model") or "").strip()
        effort = str(role.get("reasoning_effort") or "").strip()
        if model:
            os.environ[
                "ZTARE_CODEX_AGENT_MODEL"
                if role_runtime == "codex" else "ZTARE_CLAUDE_AGENT_MODEL"
            ] = model
        if effort:
            os.environ[
                "ZTARE_CODEX_AGENT_REASONING_EFFORT"
                if role_runtime == "codex" else "ZTARE_CLAUDE_EFFORT"
            ] = effort
    os.environ["ZTARE_LEANMILL_PROPOSER_POOL"] = (
        "1" if bool(solver.get("governed_pool", False)) else "0"
    )
    os.environ["ZTARE_LEANMILL_NO_SUBSCRIPTION_FAILOVER"] = (
        "0" if bool(solver.get("allow_subscription_failover", False)) else "1"
    )
    if args.model:
        os.environ["ZTARE_CLAUDE_AGENT_MODEL"] = args.model
        os.environ["ZTARE_DEFAULT_SUBSCRIPTION_RUNTIME"] = "claude"
        os.environ["ZTARE_LEANMILL_LEAF_RUNTIME"] = "claude"
    if manifest.budget.hard_caps["metered_usd_micros"] == 0:
        os.environ["ZTARE_LEANMILL_FORMALIZE_API_FALLBACK"] = "0"
        os.environ["ZTARE_LEANMILL_ROUNDTRIP_API_FALLBACK"] = "0"
        os.environ["ZTARE_LEANMILL_JUDGE_PANEL"] = "0"

    attempt_id = "formalize-" + uuid.uuid4().hex
    state_root = Path(
        os.environ.get("ZTARE_LEANMILL_CAMPAIGN_STATE_ROOT")
        or (Path(OUT_DIR) / "campaign_runs")
    )
    directory = state_root / attempt_id
    directory.mkdir(parents=True, exist_ok=False)
    write_json_atomic(directory / "campaign_manifest.json", manifest.to_json())
    write_json_atomic(directory / "budget.json", manifest.budget.to_json())
    theory_path, declared_theory_path = _declared_theory_path(manifest.body)
    theory_lease = None
    lease_status = "not_applicable"
    lease_error = ""
    if theory_path is not None:
        theory_work_id = "leanmill_theory_head__" + hashlib.sha256(
            str(theory_path).encode("utf-8")
        ).hexdigest()[:24]
        theory_lease = work_queue.QueueLease(
            os.environ.get("ZTARE_LEANMILL_QUEUE_DB") or work_queue.DEFAULT_DB,
            work_id=theory_work_id,
            kind="leanmill_theory_head",
            worker_kind="formalization_campaign",
            worker_id=(
                f"leanmill-formalization:{work_queue.node_id()}:{os.getpid()}:"
                f"{attempt_id}"
            ),
            payload={
                "schema": "leanmill.theory_head_lease.v1",
                "theory_path": str(theory_path),
                "declared_path": declared_theory_path,
                "attempt_id": attempt_id,
                "campaign_id": manifest.campaign_id,
                "action": "formalization_campaign",
            },
            max_attempts=1_000_000_000,
            lease_s=max(
                30,
                int(os.environ.get("ZTARE_LEANMILL_THEORY_HEAD_LEASE_S", "900")),
            ),
        )
        try:
            theory_lease.__enter__()
            lease_status = "acquired"
        except work_queue.QueueLeaseBusy as exc:
            lease_status = "blocked_by_theory_owner"
            lease_error = str(exc)
            theory_lease = None
    theory_before = (
        _theory_file_receipt(manifest.body)
        if lease_status != "blocked_by_theory_owner"
        else {
            "declared_path": declared_theory_path,
            "exists": None,
            "status": "not_read_while_owner_active",
        }
    )
    write_json_atomic(directory / "theory_input.json", theory_before)
    if (
        theory_lease is not None
        and theory_path is not None
        and theory_path.is_file()
    ):
        try:
            theory_lease.update({"input_sha256": theory_before.get("sha256", "")})
            write_text_atomic(
                directory / "theory_input.lean",
                theory_path.read_text(encoding="utf-8"),
            )
        except work_queue.QueueLeaseLost as exc:
            lease_status = "ownership_lost"
            lease_error = str(exc)
    ledger = ExplorationBudgetLedger(
        directory / "budget.events.jsonl",
        manifest.budget,
        attempt_id=attempt_id,
    )
    # The formalization attempt owns its execution identity.  A caller may
    # name a campaign family, but reusing that name as a run tag would merge
    # retries' attempts, timings, and terminal diagnostics.
    requested_run_tag = os.environ.get("ZTARE_SOLVER_RUN_TAG", "")
    os.environ["ZTARE_SOLVER_RUN_TAG"] = attempt_id
    dispatch_index = 0

    def before_dispatch(runtime_name, _command):
        nonlocal dispatch_index
        if theory_lease is not None and theory_lease.lost:
            raise work_queue.QueueLeaseLost(
                "formalization theory-head lease was lost before dispatch"
            )
        dispatch_index += 1
        return ledger.reserve(
            f"formalize:{dispatch_index}:{runtime_name}",
            "compilation",
            {"provider_calls": 1, "agent_turns": 1},
        )

    def after_dispatch(reservation):
        ledger.commit(reservation)

    from ztare.leanmill.solver.autoformalize_notes import main as _run

    lease_blocked = lease_status in {"blocked_by_theory_owner", "ownership_lost"}
    returncode = 75 if lease_blocked else 1
    error = ""
    status = lease_status if lease_blocked else "running"
    try:
        if not lease_blocked:
            with subscription_dispatch_budget_scope(
                before_dispatch=before_dispatch,
                after_dispatch=after_dispatch,
            ):
                returncode = int(_run([str(manifest.source_path)]))
            status = "completed"
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        status = "failed"
        raise
    finally:
        state = ledger.state()
        theory_after = (
            _theory_file_receipt(manifest.body)
            if not lease_blocked
            else {
                "declared_path": declared_theory_path,
                "exists": None,
                "status": "not_read_while_owner_active",
            }
        )
        if (
            theory_lease is not None
            and theory_path is not None
            and theory_path.is_file()
            and theory_lease.lost is False
        ):
            write_text_atomic(
                directory / "theory_output.lean",
                theory_path.read_text(encoding="utf-8"),
            )
        write_json_atomic(
            directory / "theory_result.json",
            {
                "schema": "leanmill.formalization_theory_delta.v1",
                "before": theory_before,
                "after": theory_after,
                "changed": (
                    bool(theory_before.get("sha256"))
                    and bool(theory_after.get("sha256"))
                    and theory_before.get("sha256") != theory_after.get("sha256")
                ),
                "lease_status": lease_status,
            },
        )
        diagnostics = {}
        phase_timing = {}
        try:
            from ztare.leanmill.run_diagnostics import summarize_run
            diagnostics = summarize_run(run_tag=attempt_id)
            write_json_atomic(directory / "diagnostics.json", diagnostics)
        except Exception:  # diagnostics are a read model, never a completion blocker
            diagnostics = {}
        # A provider call with zero solver attempts is a distinct terminal
        # state. It may be a faithfulness rejection, an execution stop, or a
        # harness boundary; collapsing it into "completed" hides the reason
        # from campaign monitors.
        if (
            status == "completed"
            and int(state["usage"].get("provider_calls", 0) or 0) > 0
            and int(diagnostics.get("total", 0) or 0) == 0
        ):
            status = "completed_no_solver_attempts"
            error = error or "provider calls were spent but no governed solver attempt was recorded"
        try:
            from ztare.leanmill.phase_timing import summarize_phase_timings
            phase_timing = summarize_phase_timings(run_tag=attempt_id)
            write_json_atomic(directory / "phase_timing.json", phase_timing)
        except Exception:  # phase timing is likewise advisory
            phase_timing = {}
        if theory_lease is not None:
            try:
                theory_lease.release()
            except work_queue.QueueLeaseLost as exc:
                status = "ownership_lost"
                lease_error = str(exc)
                error = error or lease_error
        write_json_atomic(
            directory / "completion.json",
            {
                "schema": "leanmill.formalization_campaign_completion.v1",
                "status": status,
                "campaign_id": manifest.campaign_id,
                "attempt_id": attempt_id,
                "solver_run_tag": attempt_id,
                "requested_run_tag": requested_run_tag,
                "returncode": returncode,
                "error": error or lease_error,
                "theory_head_lease": {
                    "status": status if lease_blocked else lease_status,
                    "path": str(theory_path) if theory_path is not None else "",
                },
                "budget_digest": manifest.budget.digest,
                "usage": state["usage"],
                "diagnostics_path": "diagnostics.json" if diagnostics else "",
                "phase_timing_path": "phase_timing.json" if phase_timing else "",
                "theory_result_path": "theory_result.json",
            },
        )
    print(json.dumps({"attempt_dir": str(directory), "returncode": returncode}, sort_keys=True))
    return returncode


def _draft_slug(direction: str) -> str:
    words = re.findall(r"[a-z0-9]+", direction.lower())
    return "-".join(words[:6]) or "axiompack-direction"


def cmd_draft(args: argparse.Namespace) -> int:
    """Compile one plain-language research direction into a structure-first AxiomPack blueprint.

    This is the compile step only — from_direction(NL) -> brief -> reviewed typed draft — via the
    real subscription compiler/reviewer role pair (frontier_agent_role + compile_frontier_blueprint,
    the same machinery run_frontier_campaign_definition uses). It never builds a formal-theory context
    and never navigates, so it spends only the two compiler/reviewer provider calls. The typed draft is
    written as a `structure_first` blueprint + typed_blueprint.json sidecar so Preflight/Run replay it
    deterministically afterward with zero further provider calls for the compile step.
    """
    from ztare.leanmill.common import write_json_atomic, write_text_atomic
    from ztare.leanmill.frontier_agent_runtime import make_subscription_frontier_compiler_roles
    from ztare.leanmill.frontier_blueprint_compiler import _DRAFT_FIELDS, compile_frontier_blueprint
    from ztare.leanmill.frontier_campaign_definition import FrontierCampaignDefinition
    from ztare.leanmill.frontier_campaign_runner import (
        _load_predecessor_synthesis_input,
        frontier_agent_role,
    )

    direction = str(args.direction or "").strip()
    if not direction:
        print(json.dumps({"ok": False, "error": "direction must be non-empty"}, sort_keys=True))
        return 2
    profile = str(args.profile or "smoke_20m").strip() or "smoke_20m"
    source_mode = str(args.source_mode or "human_directed").strip() or "human_directed"

    out_path = (
        Path(args.out) if args.out
        else Path("ztare_proofs/leanmill-formalizations/blueprints") / f"{_draft_slug(direction)}.md"
    )
    typed_path = out_path.with_name(f"{out_path.stem}.typed_blueprint.json")
    # ponytail: durable agent-call artifacts live in a `.agent_calls/` subdir, invisible to the
    # flat `*.md` glob the workbench's blueprint picker uses (server_payloads/leanmill.py's
    # blueprint_list_payload) — campaign.md + its sidecar stay flat siblings so a drafted blueprint
    # is immediately visible there, same as a hand-saved one.
    agent_calls_dir = out_path.parent / ".agent_calls" / out_path.stem

    try:
        compile_definition = FrontierCampaignDefinition.from_mapping(
            {"direction": direction, "source_mode": source_mode, "profile": profile}
        )
        runtime_defaults = dict(compile_definition.runtime.get("defaults") or {})
        role_overrides = dict(compile_definition.runtime.get("role_overrides") or {})
        for role_name in ("blueprint_compiler", "semantic_reviewer"):
            binary = str(
                dict(role_overrides.get(role_name) or {}).get("runtime")
                or runtime_defaults.get("runtime")
                or "codex"
            )
            if shutil.which(binary) is None:
                raise RuntimeError(
                    f"subscription runtime unavailable: {binary!r} CLI not found on PATH "
                    "(AxiomPack drafting needs a live compiler + independent reviewer call)"
                )
        compiler = frontier_agent_role(
            compile_definition, role_name="blueprint_compiler",
            repo=Path.cwd(), artifact_dir=agent_calls_dir,
        )
        reviewer = frontier_agent_role(
            compile_definition, role_name="semantic_reviewer",
            repo=Path.cwd(), artifact_dir=agent_calls_dir,
        )
        draft_fn, review_fn = make_subscription_frontier_compiler_roles(compiler=compiler, reviewer=reviewer)
        blueprint = compile_frontier_blueprint(
            compile_definition.to_brief(),
            draft_fn=draft_fn,
            semantic_review_fn=review_fn,
            compiler_ref="frontier-blueprint-compiler",
            reviewer_ref="frontier-blueprint-reviewer",
        )
    except Exception as exc:  # fail-closed: never fabricate a typed_blueprint from a half compile
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True))
        return 1

    typed_blueprint = {
        key: value for key, value in blueprint.to_json(include_id=False).items() if key in _DRAFT_FIELDS
    }
    write_json_atomic(typed_path, typed_blueprint)

    # The compiled draft is now a concrete typed structure — write it back as `structure_first` so
    # Preflight/Run replay it deterministically (compile_structure_first_blueprint), with zero further
    # provider calls for the compile step itself. `requested_mode` echoes what the compiler chose.
    output_definition = FrontierCampaignDefinition.from_mapping(
        {
            "direction": direction,
            "source_mode": "structure_first",
            "requested_mode": blueprint.mode,
            "profile": profile,
        }
    )
    rendered = output_definition.to_json(include_id=False)
    frontmatter = {
        "schema": "leanmill.campaign.v1",
        "lane": "axiompack",
        **{
            key: rendered[key]
            for key in (
                "profile", "source_mode", "requested_mode", "evidence_refs",
                "deanchoring_intent", "forbidden_shortcuts", "created_by",
                "budget", "stop", "runtime",
            )
        },
        "typed_blueprint": typed_path.name,
    }
    text = (
        "---\n" + yaml.safe_dump(frontmatter, sort_keys=False, default_flow_style=False)
        + "---\n\n" + direction + "\n"
    )
    write_text_atomic(out_path, text)
    print(json.dumps(
        {"ok": True, "blueprint": str(out_path), "typed_blueprint": str(typed_path)},
        sort_keys=True,
    ))
    return 0


def _formalize_preflight(manifest) -> dict:
    """Provider-free admission receipt for the notes/formalization lane."""
    from ztare.leanmill.campaign_manifest import formalize_campaign_admission

    admission = formalize_campaign_admission(manifest)
    warnings: list[dict] = []
    try:
        from ztare.leanmill.blueprint_lint import lint_blueprint
        warnings = list(lint_blueprint(manifest.body))
    except Exception as exc:  # lint is advisory; admission remains deterministic
        warnings = [{"rule": "lint_unavailable", "msg": type(exc).__name__}]
    theory = _theory_file_receipt(manifest.body)
    blocking = list(admission.get("blocking") or [])
    advisory = list(admission.get("warnings") or []) + warnings
    return {
        "schema": "leanmill.campaign_preflight.v2",
        "status": "rejected" if blocking else "passed",
        "provider_calls": 0,
        "campaign_id": manifest.campaign_id,
        "lane": manifest.lane,
        "source_path": str(manifest.source_path),
        "source_sha256": manifest.source_sha256,
        "budget_digest": manifest.budget.digest,
        "admission": {**admission, "blocking": blocking, "warnings": advisory},
        "theory_input": theory,
    }


def cmd_campaign(args: argparse.Namespace) -> int:
    bp = Path(args.blueprint)
    if not bp.exists():
        print(f"leanmill: blueprint not found: {bp}", file=sys.stderr)
        return 2
    from ztare.leanmill.campaign_manifest import load_campaign_manifest

    manifest = load_campaign_manifest(bp, profile_override=args.profile or "")
    if manifest.lane == "formalize":
        admission = _formalize_preflight(manifest)
        if admission["status"] == "rejected":
            print(json.dumps(admission, sort_keys=True), file=sys.stderr)
            return 2
        if not manifest.explicit_envelope:
            apply_autoformalize_campaign_profile(
                _autoformalize_profile(args.profile or "default")
            )
            if args.model:
                os.environ.setdefault("ZTARE_CLAUDE_AGENT_MODEL", args.model)
                os.environ.setdefault("ZTARE_DEFAULT_SUBSCRIPTION_RUNTIME", "claude")
            from ztare.leanmill.solver.autoformalize_notes import main as _run

            return int(_run([str(bp)]))
        return _run_formalization_campaign(manifest, args)
    from ztare.leanmill.common import read_json
    from ztare.leanmill.frontier_campaign_actions import frontier_campaign_status
    from ztare.leanmill.frontier_campaign_runner import run_frontier_campaign_definition

    typed_path = manifest.typed_blueprint_path
    typed = read_json(typed_path, None) if typed_path is not None else None
    definition = manifest.to_frontier_definition()
    if definition.source_mode == "structure_first" and not isinstance(typed, dict):
        raise ValueError("structure-first AxiomPack campaign requires typed_blueprint in frontmatter")
    directory = run_frontier_campaign_definition(
        definition,
        output_root=Path(args.output_root),
        typed_draft=typed,
        campaign_manifest=manifest.to_json(),
    )
    print(json.dumps(frontier_campaign_status(directory), sort_keys=True))
    return 0


def cmd_preflight(args: argparse.Namespace) -> int:
    """Validate one campaign and its frozen deterministic inputs without dispatch."""

    from ztare.leanmill.campaign_manifest import load_campaign_manifest

    manifest = load_campaign_manifest(Path(args.blueprint))
    if manifest.lane == "formalize":
        receipt = _formalize_preflight(manifest)
        print(json.dumps(receipt, sort_keys=True))
        return 0 if receipt["status"] == "passed" else 2

    from ztare.leanmill.common import read_json
    from ztare.leanmill.explore_axiom_space import (
        compile_campaign_brief,
        _context_from_blueprint,
        _context_from_snapshot,
    )
    from ztare.leanmill.frontier_blueprint_compiler import (
        compile_structure_first_blueprint,
    )
    from ztare.leanmill.frontier_campaign_runner import (
        _load_predecessor_synthesis_input,
        frontier_agent_role,
    )
    from ztare.common.llm_runtime import (
        subscription_reasoning_effort,
        validate_subscription_model_cli,
    )
    from ztare.leanmill.theory_ir import content_hash

    definition = manifest.to_frontier_definition()
    typed_path = manifest.typed_blueprint_path
    typed = read_json(typed_path, None) if typed_path is not None else None
    if definition.source_mode != "structure_first" or not isinstance(typed, dict):
        raise ValueError(
            "provider-free AxiomPack preflight requires a structure-first typed blueprint"
        )
    brief, budget_contract, _budget_preference = compile_campaign_brief(definition)
    blueprint = compile_structure_first_blueprint(brief, typed)
    runtime_resolution = {}
    role_configs = {}
    for role_name in sorted(
        (definition.runtime.get("role_overrides") or {}).keys()
    ):
        config = frontier_agent_role(
            definition,
            role_name=str(role_name),
            repo=Path.cwd(),
            artifact_dir=Path("/tmp/leanmill-preflight-unused"),
        ).config
        role_configs[str(role_name)] = config
        runtime_resolution[str(role_name)] = {
            "runtime": config.runtime,
            "model": config.model,
            "reasoning_effort": config.reasoning_effort,
            "native_reasoning_effort": subscription_reasoning_effort(
                config.runtime, config.reasoning_effort, model=config.model
            ),
            "timeout_seconds": config.timeout_seconds,
        }
    import shutil
    import subprocess

    subscription_cli_versions = {}
    for runtime_name in sorted({config.runtime for config in role_configs.values()}):
        executable = shutil.which(runtime_name)
        version = ""
        if executable is not None:
            completed = subprocess.run(
                [executable, "--version"],
                capture_output=True,
                check=False,
                text=True,
                timeout=10,
            )
            version = (completed.stdout or completed.stderr).strip()
        subscription_cli_versions[runtime_name] = {
            "executable": executable or "",
            "version": version,
        }
    for config in role_configs.values():
        validate_subscription_model_cli(
            config.runtime,
            config.model,
            subscription_cli_versions[config.runtime]["version"],
        )
    context = (
        _context_from_snapshot(blueprint, definition.frozen_context_ref)
        if definition.frozen_context_ref is not None
        else _context_from_blueprint(blueprint)
    )
    predecessor_input = _load_predecessor_synthesis_input(
        definition, repo=Path.cwd()
    )
    if (
        predecessor_input is not None
        and predecessor_input.get("context_hash") != context.context_hash
    ):
        raise ValueError("predecessor synthesis input targets another context")
    observational_partition = context.incidence.observational_partition_summary()
    universe = getattr(context, "universe", None)
    universe_receipt = getattr(universe, "receipt", None)
    core = {
        "schema": "leanmill.campaign_preflight.v1",
        "status": "passed",
        "provider_calls": 0,
        "campaign_id": manifest.campaign_id,
        "lane": manifest.lane,
        "definition_id": definition.definition_id,
        "blueprint_id": blueprint.blueprint_id,
        "context_hash": context.context_hash,
        "formula_count": len(context.incidence.attribute_ids),
        "semantic_formula_profile_count": len(context.semantic_formula_classes()),
        "observational_partition": observational_partition,
        "object_contrast_admissible": context.object_contrast_admissible,
        "model_or_observation_count": len(context.incidence.object_ids),
        # Exact node topology is an interactive read model, not an admission
        # prerequisite.  Enumerating the full syntactic band here turns a
        # provider-free check into an unbounded combination search.
        "generated_theory_node_count": None,
        "generated_theory_node_count_policy": "deferred_to_semantic_navigator",
        "context_complete": context.complete,
        "model_universe_receipt": (
            universe_receipt.to_json() if universe_receipt is not None else None
        ),
        "source_sha256": manifest.source_sha256,
        "budget_digest": budget_contract.digest,
        "allocation_policy": budget_contract.allocation_policy,
        "runtime_resolution": runtime_resolution,
        "subscription_cli_versions": subscription_cli_versions,
        "predecessor_synthesis": (
            {
                "input_sha256": predecessor_input["input_sha256"],
                "formula_request_count": len(
                    predecessor_input.get("formula_requests") or ()
                ),
                "theory_language_request_count": len(
                    predecessor_input.get("theory_language_requests") or ()
                ),
            }
            if predecessor_input is not None else None
        ),
    }
    print(json.dumps({**core, "receipt_sha256": content_hash(core)}, sort_keys=True))
    return 0


def _formalization_campaign_view(directory: Path) -> dict | None:
    from ztare.leanmill.common import read_json
    from ztare.leanmill.exploration_budget import ExplorationBudget, ExplorationBudgetLedger

    manifest = read_json(directory / "campaign_manifest.json", None)
    if not isinstance(manifest, dict) or manifest.get("lane") != "formalize":
        return None
    completion = read_json(directory / "completion.json", None)
    diagnostics = read_json(directory / "diagnostics.json", {})
    phase_timing = read_json(directory / "phase_timing.json", {})
    theory_delta = read_json(directory / "theory_result.json", {})
    budget = ExplorationBudget.from_json(read_json(directory / "budget.json", {}))
    ledger = ExplorationBudgetLedger(
        directory / "budget.events.jsonl",
        budget,
        attempt_id=directory.name,
    )
    state = ledger.state()
    return {
        "schema": "leanmill.campaign_status.v1",
        "lane": "formalize",
        "status": (
            str(completion.get("status") or "completed")
            if isinstance(completion, dict) and completion.get("returncode") == 0
            else "failed" if isinstance(completion, dict)
            else "incomplete"
        ),
        "attempt_dir": str(directory),
        "campaign_id": manifest.get("campaign_id"),
        "source_path": manifest.get("source_path"),
        "budget": {
            "budget_digest": budget.digest,
            "elapsed_ms": ledger.elapsed_ms(),
            "usage": {key: value for key, value in state["usage"].items() if value},
            "soft_stop_reason": ledger.soft_stop_reason(),
        },
        "completion": completion,
        "diagnostics": diagnostics if isinstance(diagnostics, dict) else {},
        "phase_timing": phase_timing if isinstance(phase_timing, dict) else {},
        "theory_delta": theory_delta if isinstance(theory_delta, dict) else {},
    }


def cmd_status(args: argparse.Namespace) -> int:
    directory = Path(args.attempt_dir)
    formalization = _formalization_campaign_view(directory)
    if formalization is not None:
        print(json.dumps(formalization, sort_keys=True))
        return 0
    from ztare.leanmill.frontier_campaign_actions import frontier_campaign_status

    print(json.dumps(frontier_campaign_status(directory), sort_keys=True))
    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    directory = Path(args.attempt_dir)
    formalization = _formalization_campaign_view(directory)
    if formalization is not None:
        print(json.dumps(formalization, sort_keys=True))
        return 0
    from ztare.leanmill.frontier_campaign_actions import inspect_frontier_campaign

    print(json.dumps(inspect_frontier_campaign(directory), sort_keys=True))
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    from ztare.leanmill.frontier_campaign_runner import (
        execute_frontier_campaign_verification,
    )

    result = execute_frontier_campaign_verification(
        args.attempt_dir,
        with_lean=args.with_lean,
        with_isabelle=args.with_isabelle,
        lean_root=args.lean_root or None,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


def cmd_replay(args: argparse.Namespace) -> int:
    from ztare.leanmill.frontier_campaign_actions import replay_frontier_campaign

    receipt = replay_frontier_campaign(args.attempt_dir)
    print(json.dumps(receipt, sort_keys=True))
    return 0 if receipt.get("ok") is True else 1


def cmd_resume(args: argparse.Namespace) -> int:
    from ztare.leanmill.frontier_campaign_actions import frontier_campaign_status
    from ztare.leanmill.frontier_campaign_runner import (
        resume_frontier_campaign_navigation,
    )

    directory = resume_frontier_campaign_navigation(args.attempt_dir)
    print(json.dumps(frontier_campaign_status(directory), sort_keys=True))
    return 0


def cmd_continue_epoch(args: argparse.Namespace) -> int:
    from ztare.leanmill.frontier_campaign_actions import frontier_campaign_status
    from ztare.leanmill.frontier_campaign_runner import (
        continue_frontier_campaign_epoch,
    )

    directory = continue_frontier_campaign_epoch(args.attempt_dir)
    print(json.dumps(frontier_campaign_status(directory), sort_keys=True))
    return 0


def cmd_recover(args: argparse.Namespace) -> int:
    from ztare.leanmill.frontier_campaign_actions import frontier_campaign_status
    from ztare.leanmill.frontier_campaign_runner import (
        materialize_frontier_navigation_from_journal,
    )

    directory = materialize_frontier_navigation_from_journal(args.attempt_dir)
    print(json.dumps(frontier_campaign_status(directory), sort_keys=True))
    return 0


def cmd_recheck(args: argparse.Namespace) -> int:
    from ztare.leanmill.frontier_campaign_runner import (
        recheck_frontier_boundary_governance,
    )

    result = recheck_frontier_boundary_governance(
        args.attempt_dir,
        lean_root=args.lean_root,
        timeout_s=args.timeout_s,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


def cmd_interpret(args: argparse.Namespace) -> int:
    from ztare.leanmill.frontier_campaign_runner import (
        run_post_freeze_literature_review,
    )

    result = run_post_freeze_literature_review(
        args.attempt_dir,
        model=args.model,
        reasoning_effort=args.reasoning_effort,
        retry_inconclusive=args.retry_inconclusive,
        retry_failed=args.retry_failed,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


def cmd_adapter_forge(args: argparse.Namespace) -> int:
    from ztare.leanmill.frontier_campaign_runner import execute_frontier_adapter_forge

    result = execute_frontier_adapter_forge(
        args.attempt_dir,
        model=args.model,
        reasoning_effort=args.reasoning_effort,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


def cmd_extend_budget(args: argparse.Namespace) -> int:
    from ztare.leanmill.common import read_json
    from ztare.leanmill.exploration_budget import (
        ExplorationBudget,
        ExplorationBudgetLedger,
    )

    directory = Path(args.attempt_dir)
    budget = ExplorationBudget.from_json(read_json(directory / "budget.json", {}))
    ledger = ExplorationBudgetLedger(
        directory / "budget.events.jsonl", budget, attempt_id=directory.name
    )
    cap_s = ledger.wall_clock_cap_s()
    if int(args.seconds or 0):
        cap_s = ledger.extend_wall_clock(
            extra_s=int(args.seconds),
            authority_ref=str(args.authority_ref),
            reason=str(args.reason),
        )
    resources = {
        key: int(value)
        for key, value in {
            "provider_calls": args.provider_calls,
            "agent_turns": args.agent_turns,
            "workbench_actions": args.workbench_actions,
            "adapter_forge_attempts": args.adapter_forge_attempts,
        }.items()
        if int(value or 0)
    }
    resource_caps = (
        ledger.extend_resources(
            phase=str(args.phase), resources=resources,
            authority_ref=str(args.authority_ref), reason=str(args.reason),
        )
        if resources else {}
    )
    if not int(args.seconds or 0) and not resources:
        raise ValueError("budget extension requires time or resources")
    print(json.dumps({
        "schema": "leanmill.budget_extension.v2",
        "attempt_id": directory.name,
        "budget_digest": budget.digest,
        "wall_clock_cap_s": cap_s,
        "extra_s": int(args.seconds),
        "resource_caps": resource_caps,
        "authority_ref": str(args.authority_ref),
        "reason": str(args.reason),
    }, sort_keys=True))
    return 0


def cmd_stop(args: argparse.Namespace) -> int:
    from ztare.leanmill.frontier_campaign_actions import request_frontier_campaign_stop

    print(json.dumps(request_frontier_campaign_stop(
        args.attempt_dir,
        authority_ref=args.authority_ref,
    ), sort_keys=True))
    return 0


def cmd_retire(args: argparse.Namespace) -> int:
    from ztare.leanmill.frontier_campaign_actions import retire_frontier_campaign

    print(json.dumps(retire_frontier_campaign(
        args.attempt_dir,
        authority_ref=args.authority_ref,
        reason=args.reason,
    ), sort_keys=True))
    return 0


def main(argv: "list[str] | None" = None) -> int:
    parser = argparse.ArgumentParser(prog="leanmill", description="LeanMill — governed proof-search launcher.")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser(
        "draft",
        help="Compile one plain-language research direction into a structure-first AxiomPack blueprint.",
    )
    p.add_argument("direction", help="plain-language region/direction for AxiomPack to explore")
    p.add_argument("--source-mode", default="human_directed",
                    help="brief source_mode used for compiling (default human_directed)")
    p.add_argument("--out", default="",
                    help="blueprint markdown path (default ztare_proofs/leanmill-formalizations/blueprints/<slug>.md)")
    p.add_argument("--profile", default="smoke_20m", help="budget preset (default smoke_20m)")
    p.set_defaults(func=cmd_draft)
    p = sub.add_parser("campaign", help="Launch a formalization or AxiomPack campaign from Markdown.")
    p.add_argument("blueprint", help="campaign Markdown; optional YAML frontmatter selects lane and policy")
    p.add_argument("--profile", default="",
                   help="optional named-profile override; frontmatter remains the normal campaign policy")
    p.add_argument("--model", default="",
                   help="leaf model, e.g. claude-fable-5 — makes it the first leaf (claude runtime), codex the failover")
    p.add_argument("--output-root", default="/tmp/axiompack_campaigns",
                   help="AxiomPack attempt root (ignored by formalization campaigns)")
    p.set_defaults(func=cmd_campaign)
    p = sub.add_parser("preflight", help="Validate a campaign without provider dispatch.")
    p.add_argument("blueprint")
    p.set_defaults(func=cmd_preflight)
    p = sub.add_parser("status", help="Show the read model for any LeanMill campaign attempt.")
    p.add_argument("attempt_dir")
    p.set_defaults(func=cmd_status)
    p = sub.add_parser("inspect", help="Inspect a campaign without exposing sealed/private state.")
    p.add_argument("attempt_dir")
    p.set_defaults(func=cmd_inspect)
    p = sub.add_parser("verify", help="Run separately approved AxiomPack boundary checks.")
    p.add_argument("attempt_dir")
    p.add_argument("--with-isabelle", action="store_true")
    p.add_argument("--with-lean", action="store_true")
    p.add_argument("--lean-root", default="")
    p.set_defaults(func=cmd_verify)
    p = sub.add_parser("replay", help="Replay a frozen AxiomPack campaign without provider calls.")
    p.add_argument("attempt_dir")
    p.set_defaults(func=cmd_replay)
    p = sub.add_parser("resume", help="Continue an interrupted AxiomPack navigator from durable calls.")
    p.add_argument("attempt_dir")
    p.set_defaults(func=cmd_resume)
    p = sub.add_parser(
        "continue-epoch",
        help="Consume a frozen AxiomPack formula request in its successor context epoch.",
    )
    p.add_argument("attempt_dir")
    p.set_defaults(func=cmd_continue_epoch)
    p = sub.add_parser("recover", help="Materialize host-validated partial navigation after interruption.")
    p.add_argument("attempt_dir")
    p.set_defaults(func=cmd_recover)
    p = sub.add_parser("recheck", help="Re-govern saved AxiomPack Lean proof bytes without an agent call.")
    p.add_argument("attempt_dir")
    p.add_argument("--lean-root", required=True)
    p.add_argument("--timeout-s", type=int, default=180)
    p.set_defaults(func=cmd_recheck)
    p = sub.add_parser("interpret", help="Run a post-freeze, source-backed AxiomPack literature review.")
    p.add_argument("attempt_dir")
    p.add_argument("--model", default="gpt-5.5")
    p.add_argument(
        "--reasoning-effort", choices=("low", "medium", "high", "ultra"), default="medium"
    )
    p.add_argument("--retry-inconclusive", action="store_true")
    p.add_argument("--retry-failed", action="store_true")
    p.set_defaults(func=cmd_interpret)
    p = sub.add_parser(
        "adapter-forge",
        help="Execute a typed AxiomPack adapter/capability gap in quarantine.",
    )
    p.add_argument("attempt_dir")
    p.add_argument("--model", default="gpt-5.5")
    p.add_argument(
        "--reasoning-effort", choices=("low", "medium", "high", "ultra"), default="medium"
    )
    p.set_defaults(func=cmd_adapter_forge)
    p = sub.add_parser(
        "extend-budget",
        help="Add an explicit, authority-receipted campaign budget extension.",
    )
    p.add_argument("attempt_dir")
    p.add_argument("--seconds", type=int, default=0)
    p.add_argument(
        "--phase",
        choices=("compilation", "context", "navigation", "expansion", "boundary", "interpretation"),
        default="navigation",
    )
    p.add_argument("--provider-calls", type=int, default=0)
    p.add_argument("--agent-turns", type=int, default=0)
    p.add_argument("--workbench-actions", type=int, default=0)
    p.add_argument("--adapter-forge-attempts", type=int, default=0)
    p.add_argument("--authority-ref", required=True)
    p.add_argument("--reason", required=True)
    p.set_defaults(func=cmd_extend_budget)
    p = sub.add_parser("stop", help="Request a host-recorded AxiomPack campaign stop.")
    p.add_argument("attempt_dir")
    p.add_argument("--authority-ref", required=True)
    p.set_defaults(func=cmd_stop)
    p = sub.add_parser("retire", help="Retire an AxiomPack campaign attempt.")
    p.add_argument("attempt_dir")
    p.add_argument("--authority-ref", required=True)
    p.add_argument("--reason", required=True)
    p.set_defaults(func=cmd_retire)
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
