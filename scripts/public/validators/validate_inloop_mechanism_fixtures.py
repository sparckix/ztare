#!/usr/bin/env python3
"""Fixture matrix for underused in-loop autoresearch mechanisms.

This is intentionally cheap: it exercises extracted helpers and static wiring
without launching a full autoresearch run or making live LLM calls. It answers
"do the shipped mechanism surfaces still execute?" for the mechanisms that tend
to go dormant because they are opt-in rubric paths.
"""
from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import os
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
AUTORESEARCH_LOOP = REPO / "src" / "ztare" / "validator" / "autoresearch_loop.py"
BLITZ_DISPATCH = REPO / "src" / "ztare" / "orchestrator" / "blitz_dispatch.py"
RUBRIC_MODE_RESOLVER = REPO / "src" / "ztare" / "validator" / "rubric_mode_resolver.py"
INFORMATION_YIELD = REPO / "src" / "ztare" / "validator" / "core" / "information_yield.py"
VALIDATE_RUBRIC = REPO / "scripts" / "public" / "validators" / "validate_rubric.py"
MAKEFILE = REPO / "Makefile"
EIGENQUESTION_GENERATOR = (
    REPO / "src" / "ztare" / "research_director" / "eigenquestion_generator.py"
)
EIGENQUESTION_PREFLIGHT = (
    REPO / "scripts" / "public" / "control" / "preflight_eigenquestion_review.py"
)


@dataclass(frozen=True)
class FixtureResult:
    name: str
    passed: bool
    detail: str
    evidence: dict[str, Any]


MECHANISM_STATUS: dict[str, dict[str, str]] = {
    "pivot_heuristics": {
        "mechanism": "stagnation pivot routing",
        "status": "active",
        "proves": "rubric-aware stagnation thresholds and pivot-state selection still execute",
        "try_command": "make inloop-fixture-validate JSON=1",
        "test_reference": "src/ztare/validator/tests/pivot_heuristics_fixture_regression.py",
    },
    "primitive_class_rotation": {
        "mechanism": "primitive-class rotation",
        "status": "active",
        "proves": "judged structural class proposals write/read history for mutator and RD reuse",
        "try_command": "make inloop-fixture-validate JSON=1",
        "test_reference": "tests/research_director/test_primitive_class_rotation.py",
    },
    "parallel_mutator": {
        "mechanism": "parallel mutator workers",
        "status": "active",
        "proves": "parallel worker failures are isolated and scored winners are selectable",
        "try_command": "make inloop-fixture-validate JSON=1",
        "test_reference": "tests/orchestrator/test_parallel_mutator.py",
    },
    "recombination_r1_sanity": {
        "mechanism": "recombination candidate gate",
        "status": "active",
        "proves": "recombined candidates must still satisfy the R1 sanity surface",
        "try_command": "make inloop-fixture-validate JSON=1",
        "test_reference": "tests/validators/test_validate_inloop_mechanism_fixtures.py",
    },
    "blitz_survival_report": {
        "mechanism": "blitz survival telemetry",
        "status": "diagnostic",
        "proves": "parallel winners can be joined to downstream eval/gate/champion evidence",
        "try_command": "make blitz-survival-report PROJECT=<project>",
        "test_reference": "tests/reports/test_blitz_survival_report.py",
    },
    "eigenquestion_negative_evidence_validation": {
        "mechanism": "eigenquestion negative-evidence check",
        "status": "advisory",
        "proves": "falsified explored classes need evidence before shaping advisory eigenquestions",
        "try_command": "ztare eigenquestion validate --project <project>",
        "test_reference": "tests/test_cli.py::VerbRouterTests::test_eigenquestion_validate_delegates_to_validate_explored",
    },
    "eigenquestion_launch_preflight": {
        "mechanism": "eigenquestion launch preflight",
        "status": "advisory",
        "proves": "newer advisory proposals surface before launch without rewriting charters",
        "try_command": "ztare eigenquestion status --project <project>",
        "test_reference": "tests/control/test_preflight_eigenquestion_review.py",
    },
    "tried_failed_digest_provider": {
        "mechanism": "tried/failed mutator briefing",
        "status": "active",
        "proves": "R1, contract, fit, repeated-branch, and frontier failures reach the next prompt",
        "try_command": "make inloop-fixture-validate JSON=1",
        "test_reference": "tests/orchestrator/test_tried_failed_digest_provider.py",
    },
    "rubric_mode_defaults": {
        "mechanism": "rubric mode contract",
        "status": "active",
        "proves": "Newton/Kepler/calibration/invariant-search contracts resolve before launch",
        "try_command": "make autoresearch-rubric-mode-audit RUBRIC=<path> STRICT=1",
        "test_reference": "tests/validator/test_rubric_mode_resolver.py",
    },
    "run_surface_validation": {
        "mechanism": "Make/CLI run-surface validation",
        "status": "active",
        "proves": "normal run paths enforce deterministic rubric/project validation before launch",
        "try_command": "ztare autoresearch run --project <project> --rubric <rubric>",
        "test_reference": "tests/test_cli.py",
    },
    "hill_climb_prompt_boundary": {
        "mechanism": "hill-climb control prompt boundary",
        "status": "active",
        "proves": "charter, current state, pivots, thesis-control mode, primitive history, and briefings reach the mutator",
        "try_command": "make autoresearch-hillclimb-audit PROJECT=<project>",
        "test_reference": "tests/reports/test_hill_climb_behavior_audit.py",
    },
    "static_autoresearch_wiring": {
        "mechanism": "static loop wiring guard",
        "status": "diagnostic",
        "proves": "the main loop still contains expected executable call-sites and R1 retry feedback wiring",
        "try_command": "make inloop-fixture-validate JSON=1",
        "test_reference": "tests/validator/test_autoresearch_loop_static_guards.py",
    },
}


def _ok(name: str, detail: str, **evidence: Any) -> FixtureResult:
    return FixtureResult(name=name, passed=True, detail=detail, evidence=evidence)


def _fail(name: str, detail: str, **evidence: Any) -> FixtureResult:
    return FixtureResult(name=name, passed=False, detail=detail, evidence=evidence)


def _fixture_pivot_heuristics() -> FixtureResult:
    from src.ztare.validator.tests.pivot_heuristics_fixture_regression import (
        run_pivot_fixture_regression,
    )

    summary = run_pivot_fixture_regression()
    passed = bool(summary.get("all_passed"))
    detail = f"{summary.get('num_passed')}/{summary.get('num_cases')} pivot cases passed"
    return (_ok if passed else _fail)("pivot_heuristics", detail, summary=summary)


def _fixture_primitive_class_rotation() -> FixtureResult:
    from src.ztare.orchestrator.prompt import (
        maybe_track_primitive_class_rotation,
        primitive_class_history_packet,
    )

    with tempfile.TemporaryDirectory() as td:
        project_dir = Path(td) / "projects" / "fixture_project"
        (project_dir / "workspace").mkdir(parents=True)
        disabled = primitive_class_history_packet(
            {"enable_primitive_class_rotation": False},
            project_dir=project_dir,
        )
        empty = primitive_class_history_packet(
            {"enable_primitive_class_rotation": True},
            project_dir=project_dir,
        )
        tracked = maybe_track_primitive_class_rotation(
            rubric_data={
                "enable_primitive_class_rotation": True,
                "cage_meta": {"class": "audit"},
            },
            project_dir=project_dir,
            run_id="fixture-run",
            iter_index=1,
            thesis_text=(
                "## Structural Mutation: ACRR\n"
                "mechanism = propose_new_primitive_class\n"
            ),
            score=71.0,
            use_llm=False,
        )
        heading_tracked = maybe_track_primitive_class_rotation(
            rubric_data={
                "enable_primitive_class_rotation": True,
                "cage_meta": {"class": "audit"},
            },
            project_dir=project_dir,
            run_id="fixture-run",
            iter_index=2,
            thesis_text=(
                "## Gate: residual boundary detector\n"
                "Use a narrow residual-boundary check before proposing the next form.\n"
            ),
            score=53.0,
            use_llm=False,
        )
        marker_tracked = maybe_track_primitive_class_rotation(
            rubric_data={
                "enable_primitive_class_rotation": True,
                "cage_meta": {"class": "audit"},
            },
            project_dir=project_dir,
            run_id="fixture-run",
            iter_index=3,
            thesis_text=(
                "CATEGORY SWITCH: residual maps\n"
                "Use a different representation before proposing another refinement.\n"
            ),
            score=54.0,
            use_llm=False,
        )
        populated = primitive_class_history_packet(
            {"enable_primitive_class_rotation": True},
            project_dir=project_dir,
        )
        ledger = project_dir / "workspace" / "explored_primitive_classes.jsonl"
        passed = (
            disabled == ""
            and "no classes explored yet" in empty
            and "ACRR" in populated
            and "residual boundary detector" in populated
            and "residual maps" in populated
            and "current ceiling 95" in populated
            and ledger.exists()
            and tracked.tracked
            and heading_tracked.tracked
            and marker_tracked.tracked
        )
        return (_ok if passed else _fail)(
            "primitive_class_rotation",
            "packet disabled/enabled/populated states are coherent, including heading-only and marker class moves",
            ledger_exists=ledger.exists(),
            disabled_empty=disabled == "",
            empty_mentions_no_classes="no classes explored yet" in empty,
            populated_mentions_class="ACRR" in populated,
            populated_mentions_heading_class="residual boundary detector" in populated,
            populated_mentions_marker_class="residual maps" in populated,
            tracked_class=tracked.class_name,
            heading_tracked_class=heading_tracked.class_name,
            marker_tracked_class=marker_tracked.class_name,
        )


def _fixture_parallel_mutator() -> FixtureResult:
    from src.ztare.orchestrator.parallel_mutator import (
        MutatorResult,
        MutatorTask,
        build_default_tasks,
        pick_best_candidate,
        run_parallel_mutators,
    )

    tasks = build_default_tasks(3)

    def worker(task: MutatorTask) -> MutatorResult:
        if task.worker_id == 1:
            raise RuntimeError("fixture failure")
        return MutatorResult(
            worker_id=task.worker_id,
            persona=task.persona,
            thesis_text=f"thesis {task.worker_id}",
            test_model_text=f"# test {task.worker_id}",
            score=float(task.worker_id),
        )

    results = run_parallel_mutators(tasks, worker)
    winner = pick_best_candidate(results)
    passed = (
        len(tasks) == 3
        and len({task.persona for task in tasks}) == 3
        and [result.worker_id for result in results] == [0, 1, 2]
        and "__error__" in results[1].extras
        and winner is not None
        and winner.worker_id == 2
    )
    return (_ok if passed else _fail)(
        "parallel_mutator",
        "parallel tasks preserve order, isolate failed workers, and pick scored winner",
        personas=[task.persona for task in tasks],
        result_worker_ids=[result.worker_id for result in results],
        failed_worker_has_error="__error__" in results[1].extras,
        winner_worker_id=winner.worker_id if winner else None,
    )


def _fixture_recombination_r1() -> FixtureResult:
    from src.ztare.orchestrator.recombination import candidate_passes_r1_sanity

    valid = """Candidate.

```python
PARAMETER_NAMES = ["a"]
PARAMETRIC_FORM = "params.get('a', 1.0) * features['x']"

def predict(features, params):
    return params.get('a', 1.0) * features['x']
```
"""
    valid_ok, valid_reason = candidate_passes_r1_sanity(valid)
    empty_ok, empty_reason = candidate_passes_r1_sanity("")
    no_param_ok, no_param_reason = candidate_passes_r1_sanity(
        "```python\nPARAMETRIC_FORM = \"features['x']\"\n```"
    )
    passed = valid_ok and not empty_ok and not no_param_ok
    return (_ok if passed else _fail)(
        "recombination_r1_sanity",
        "R1 sanity accepts a minimal valid candidate and rejects empty/no-param candidates",
        valid_reason=valid_reason,
        empty_reason=empty_reason,
        no_param_reason=no_param_reason,
    )


def _fixture_blitz_survival_report() -> FixtureResult:
    from src.ztare.reports.blitz_survival_report import build_blitz_survival_report

    with tempfile.TemporaryDirectory() as td:
        workspace = Path(td)

        def append_jsonl(name: str, row: dict[str, Any]) -> None:
            with (workspace / name).open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(row) + "\n")

        append_jsonl(
            "parallel_blitz_log.jsonl",
            {
                "iter": 1,
                "k": 3,
                "decision_reason": "fixture",
                "n_after_recombination": 3,
                "n_crossovers": 0,
                "fusion_succeeded": False,
                "winner_id": 0,
                "winner_persona": "newton_discovery",
                "winner_stage_origin": "mutator_newton_discovery",
                "scores": [
                    {"worker_id": 0, "persona": "newton_discovery", "score": 4.0}
                ],
            },
        )
        append_jsonl(
            "eval_history.jsonl",
            {"iteration": 1, "score": 51, "weakest_point": "fixture"},
        )
        append_jsonl(
            "iteration_telemetry.jsonl",
            {
                "record_type": "iteration",
                "iteration_index": 1,
                "score": 51,
                "champion_promoted": False,
                "gate_failure_count": 0,
                "failed_gate_ids": [],
            },
        )
        report = build_blitz_survival_report(workspace)

    summary = report.get("summary", {})
    passed = (
        summary.get("num_blitz_iterations") == 1
        and summary.get("downstream_eval_rate") == 1.0
        and summary.get("gate_clean_positive_rate") == 1.0
        and report["rows"][0]["survival_class"] == "evaluated_positive_score"
    )
    return (_ok if passed else _fail)(
        "blitz_survival_report",
        "blitz tournament winners join to downstream eval/gate survival metrics",
        summary=summary,
        rows=report.get("rows", []),
    )


def _fixture_eigenquestion_validation() -> FixtureResult:
    from src.ztare.research_director.eigenquestion_generator import validate_explored_classes

    with tempfile.TemporaryDirectory() as td:
        evidence = Path(td) / "falsifier.md"
        evidence.write_text("negative evidence\n", encoding="utf-8")
        missing = validate_explored_classes([
            {"class_name": "ACRR", "outcome": "FALSIFIED_BAD_FIT"},
        ])
        present = validate_explored_classes([
            {
                "class_name": "ACRR",
                "outcome": "FALSIFIED_BAD_FIT",
                "evidence_path": str(evidence),
            },
        ])
    passed = bool(missing) and not present
    return (_ok if passed else _fail)(
        "eigenquestion_negative_evidence_validation",
        "falsified explored classes require evidence_path before eigenquestion prompt use",
        missing_errors=missing,
        present_errors=present,
    )


def _load_eigenquestion_preflight_module():
    spec = importlib.util.spec_from_file_location(
        "preflight_eigenquestion_review_fixture",
        EIGENQUESTION_PREFLIGHT,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {EIGENQUESTION_PREFLIGHT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _fixture_eigenquestion_launch_preflight() -> FixtureResult:
    module = _load_eigenquestion_preflight_module()
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td)
        project = "fixture_project"
        project_dir = repo / "projects" / project
        project_dir.mkdir(parents=True)
        charter = project_dir / "project_charter.md"
        proposal = project_dir / "proposed_eigenquestion_20260612_010203.md"
        charter.write_text("charter\n", encoding="utf-8")
        proposal.write_text("proposal\n", encoding="utf-8")
        os.utime(charter, (1000, 1000))
        os.utime(proposal, (2000, 2000))

        warn = module.inspect_eigenquestion_review(project, repo=repo, strict=False)
        strict = module.inspect_eigenquestion_review(project, repo=repo, strict=True)
        rendered = module.render_text(warn)
        charter_text_after = charter.read_text(encoding="utf-8")

    passed = (
        warn.status == "pending_review"
        and warn.pending_count == 1
        and warn.ok
        and not strict.ok
        and "ztare eigenquestion validate --project fixture_project" in rendered
        and "never auto-rewrite project_charter.md" in rendered
        and charter_text_after == "charter\n"
    )
    return (_ok if passed else _fail)(
        "eigenquestion_launch_preflight",
        "launch preflight surfaces newer advisory eigenquestions without editing the charter",
        warn_status=warn.status,
        pending_count=warn.pending_count,
        warn_ok=warn.ok,
        strict_ok=strict.ok,
        charter_unchanged=charter_text_after == "charter\n",
    )


def _fixture_tried_failed_digest_provider() -> FixtureResult:
    from src.ztare.orchestrator.mutator_briefing import BriefingContext, default_briefing

    with tempfile.TemporaryDirectory() as td:
        project_dir = Path(td) / "project"
        workspace = project_dir / "workspace"
        r1_dir = workspace / "r1_debug"
        r1_dir.mkdir(parents=True)

        (r1_dir / "iter_001_r1_attempts.md").write_text(
            "**Rejection reason:**\n```candidate reuses an invalid hidden global during import.```\n",
            encoding="utf-8",
        )
        (workspace / "contract_violations.jsonl").write_text(
            json.dumps(
                {
                    "iter": 1,
                    "active_contract": "mutation_contract",
                    "adheres": False,
                    "violations": ["missing_contract_field"],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (workspace / "fit_result_iter_001.json").write_text(
            json.dumps(
                {
                    "status": "failure",
                    "failure_class": "solver_diverged",
                    "solver_diagnostics": "residual plateaued after multistart",
                }
            ),
            encoding="utf-8",
        )
        (workspace / "eval_history.jsonl").write_text(
            "".join(
                json.dumps(row) + "\n"
                for row in (
                    {"iteration": 1, "score": 40, "weakest_point": "initial"},
                    {
                        "iteration": 2,
                        "score": 35,
                        "weakest_point": "same boundary mismatch recurred",
                    },
                    {
                        "iteration": 3,
                        "score": 34,
                        "weakest_point": "same boundary mismatch recurred",
                    },
                )
            ),
            encoding="utf-8",
        )
        (workspace / "dag_steering_log.jsonl").write_text(
            "".join(
                json.dumps(row) + "\n"
                for row in (
                    {"selected_node_id": "alpha"},
                    {"selected_node_id": "beta"},
                    {"selected_node_id": "beta"},
                )
            ),
            encoding="utf-8",
        )

        ctx = BriefingContext(
            project_dir=project_dir,
            workspace_dir=workspace,
            iter_index=3,
            rubric={},
        )
        briefing = default_briefing()
        fragment = briefing.render(ctx)
        audit_path = workspace / "mutator_briefing_iter_003.md"
        audit_text = audit_path.read_text(encoding="utf-8") if audit_path.exists() else ""

    required = {
        "r1": "R1 rejected iter 1",
        "contract": "missing_contract_field",
        "fit": "solver_diverged",
        "negative_constraint": "negative constraint",
        "frontier": "frontier constraint",
        "registry": "Tried-and-Failed Digest",
    }
    missing = {name: needle for name, needle in required.items() if needle not in fragment}
    if "tried_failed_digest" not in audit_text:
        missing["persisted_audit"] = "tried_failed_digest"
    return (_ok if not missing else _fail)(
        "tried_failed_digest_provider",
        "default mutator briefing surfaces R1, contract, fit, repeated-branch, and frontier constraints",
        missing=missing,
        audit_persisted=bool(audit_text),
        fragment_excerpt=fragment[:500],
    )


def _fixture_rubric_mode_defaults() -> FixtureResult:
    from src.ztare.validator.rubric_mode_resolver import (
        apply_rubric_mode_defaults,
        describe_rubric_mode,
        validate_rubric_mode_contract,
    )

    invariant = {"rubric_modes": ["invariant_search"], "buckingham_strict": True}
    apply_rubric_mode_defaults(invariant)
    desc = describe_rubric_mode(invariant)
    kepler = {"rubric_mode": "kepler"}
    apply_rubric_mode_defaults(kepler)
    newton_ok = validate_rubric_mode_contract(
        {
            "rubric_mode": "newton",
            "dimensions": [{"name": "Generative Yield", "weight": 15}],
        }
    ).ok
    newton_missing_gy_rejected = not validate_rubric_mode_contract(
        {"rubric_mode": "newton", "dimensions": [{"name": "Fit", "weight": 100}]}
    ).ok
    calibration_ok = validate_rubric_mode_contract({"rubric_mode": "calibration"}).ok
    spec = importlib.util.spec_from_file_location("_ztare_validate_rubric_fixture", VALIDATE_RUBRIC)
    assert spec is not None and spec.loader is not None
    validate_rubric = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validate_rubric)
    valid_secondary_contract = not validate_rubric._secondary_observable_contract_errors({
        "secondary_observable_contract": {
            "observable": "held-out sibling behavior",
            "measurement": "sibling scorer",
            "expected_range": "positive lift",
            "falsifier": "only restates the primary fit",
        }
    })
    malformed_secondary_contract_rejected = bool(
        validate_rubric._secondary_observable_contract_errors({
            "secondary_observable_contract": {
                "observable": "held-out sibling behavior",
                "measurement": "",
                "expected_range": "positive lift",
                "falsifier": "only restates the primary fit",
            }
        })
    )
    newton_pivot_ok = False
    try:
        from src.ztare.validator.utilities.pivot_heuristics import get_pivot_thresholds

        newton_pivot_ok = get_pivot_thresholds(is_v4_project=False, rubric_mode="newton") == (2, 3)
    except Exception:
        newton_pivot_ok = False
    passed = (
        invariant.get("enable_lagrangian_derivation") is True
        and invariant.get("enable_buckingham_pi_gate") is True
        and invariant.get("buckingham_strict") is True
        and invariant.get("enable_cold_shot_seed") is True
        and kepler == {"rubric_mode": "kepler"}
        and newton_ok
        and newton_missing_gy_rejected
        and calibration_ok
        and valid_secondary_contract
        and malformed_secondary_contract_rejected
        and newton_pivot_ok
        and "invariant_search" in desc
    )
    return (_ok if passed else _fail)(
        "rubric_mode_defaults",
        "invariant_search defaults compose without overwriting operator values; Newton pivot threshold is early",
        invariant=invariant,
        kepler=kepler,
        description=desc,
        newton_contract_accepts_gy=newton_ok,
        newton_contract_rejects_missing_gy=newton_missing_gy_rejected,
        valid_secondary_contract=valid_secondary_contract,
        malformed_secondary_contract_rejected=malformed_secondary_contract_rejected,
        calibration_contract_accepts_without_gy=calibration_ok,
        newton_pivot_ok=newton_pivot_ok,
    )


def _fixture_run_surface_validation() -> FixtureResult:
    make_text = MAKEFILE.read_text(encoding="utf-8")
    cli_text = (REPO / "src" / "ztare" / "cli.py").read_text(encoding="utf-8")
    required = {
        "loop_depends_on_validate_rubric": "loop: validate-rubric",
        "experiment_loop_invokes_validate_rubric": "$(MAKE) validate-rubric PROJECT=$$PROJECT_BARE RUBRIC=$$RUBRIC_PATH",
        "validate_rubric_calls_shared_script": "scripts/public/validators/validate_rubric.py $(PROJECT) --rubric $$RUBRIC_PATH",
        "loop_uses_public_charter_patch_preflight": "scripts/public/control/preflight_charter_patches.py $(PROJECT)",
        "loop_exports_matched_run_id": "ZTARE_AUTORESEARCH_MATCHED_RUN_ID=$(MATCHED_RUN_ID)",
        "loop_exports_matched_run_role": "ZTARE_AUTORESEARCH_MATCHED_RUN_ROLE=$(MATCHED_RUN_ROLE)",
        "experiment_loop_forwards_matched_run_id": "MATCHED_RUN_ID=$(MATCHED_RUN_ID)",
        "experiment_loop_forwards_matched_run_role": "MATCHED_RUN_ROLE=$(MATCHED_RUN_ROLE)",
        "cli_run_delegates_to_experiment_loop": '"experiment-loop"',
    }
    haystacks = {
        "cli_run_delegates_to_experiment_loop": cli_text,
    }
    missing = {
        name: needle
        for name, needle in required.items()
        if needle not in haystacks.get(name, make_text)
    }
    return (_ok if not missing else _fail)(
        "run_surface_validation",
        "make loop, make experiment-loop, and ztare autoresearch run keep rubric validation on the launch path",
        missing=missing,
    )


def _fixture_hill_climb_prompt_boundary() -> FixtureResult:
    loop_text = AUTORESEARCH_LOOP.read_text(encoding="utf-8")
    information_yield_text = INFORMATION_YIELD.read_text(encoding="utf-8")
    eigen_text = EIGENQUESTION_GENERATOR.read_text(encoding="utf-8")
    required = {
        "project_charter_read": "project_charter = read_file(PROJECT_CHARTER_PATH)",
        "project_charter_prompt": "PROJECT CHARTER (MANDATORY CONTEXT):",
        "current_iteration_read": "current_thesis = read_file(WORKING_PATH)",
        "current_state_prompt": "### CURRENT SYSTEM STATE (FOR ANALYSIS ONLY)",
        "candidate_state_write": "write_file(WORKING_PATH, full_candidate)",
        "pivot_state": "pivot_state = resolve_stagnation_pivot_state(",
        "primitive_history_prompt": "primitive_class_history = _primitive_class_history_packet(",
        "mutator_briefing_general_context": "mutator_briefing_context = _briefing_block",
        "mutator_briefing_prompt_slot": "{mutator_briefing_context}",
        "thesis_control_mode_render": "thesis_control_mode:",
        "thesis_control_mode_declaration": "`thesis_control_mode`",
        "thesis_control_mode_saved": '"thesis_control_mode": mutation_declaration.thesis_control_mode.value',
        "eigenquestion_advisory": "This is an ADVISORY proposal.",
        "eigenquestion_manual_merge": "manually merge",
    }
    haystacks = {
        "thesis_control_mode_render": information_yield_text,
        "eigenquestion_advisory": eigen_text,
        "eigenquestion_manual_merge": eigen_text,
    }
    missing = {
        name: needle
        for name, needle in required.items()
        if needle not in haystacks.get(name, loop_text)
    }
    forbidden_charter_write_patterns = (
        'project_charter.md").write_text(',
        "project_charter.md').write_text(",
        'project_charter.md").open("w"',
        "project_charter.md').open('w'",
    )
    writes_charter = any(
        pattern in eigen_text for pattern in forbidden_charter_write_patterns
    )
    briefing_before_feature_contract = (
        loop_text.find("default_briefing()") != -1
        and loop_text.find("if fit_primitive_features_enabled:") != -1
        and loop_text.find("default_briefing()") < loop_text.find("if fit_primitive_features_enabled:")
    )
    if not briefing_before_feature_contract:
        missing["mutator_briefing_not_nested_under_feature_fit"] = (
            "default_briefing() must render before the feature-fit-only branch"
        )
    passed = not missing and not writes_charter
    return (_ok if passed else _fail)(
        "hill_climb_prompt_boundary",
        "charter/current state/pivots/thesis-control mode/primitive history/provider briefings reach the mutator; eigenquestions are advisory",
        missing=missing,
        eigenquestion_writes_charter=writes_charter,
        mutator_briefing_before_feature_contract=briefing_before_feature_contract,
    )


def _python_tree(path: Path) -> ast.AST:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _call_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name):
            names.add(func.id)
        elif isinstance(func, ast.Attribute):
            names.add(func.attr)
    return names


def _string_literals(tree: ast.AST) -> set[str]:
    return {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }


def _has_string_fragment(literals: set[str], fragment: str) -> bool:
    return any(fragment in literal for literal in literals)


def _fixture_static_autoresearch_wiring() -> FixtureResult:
    loop_source = AUTORESEARCH_LOOP.read_text(encoding="utf-8")
    loop_tree = _python_tree(AUTORESEARCH_LOOP)
    blitz_tree = _python_tree(BLITZ_DISPATCH)
    rubric_tree = _python_tree(RUBRIC_MODE_RESOLVER)
    loop_calls = _call_names(loop_tree)
    blitz_calls = _call_names(blitz_tree)
    blitz_literals = _string_literals(blitz_tree)
    rubric_literals = _string_literals(rubric_tree)
    loop_required_calls = {
        "rubric_mode_defaults": "apply_rubric_mode_defaults",
        "rubric_mode_contract": "validate_rubric_mode_contract",
        "primitive_history_packet": "_primitive_class_history_packet",
        "primitive_rotation_append": "maybe_track_primitive_class_rotation",
        "blitz_dispatch": "dispatch_mutator_blitz",
        "blitz_survival_run_end": "_materialize_blitz_survival_report_for_run",
        "pivot_state": "resolve_stagnation_pivot_state",
        "loop_control_prompt_context": "render_loop_control_prompt_context",
    }
    loop_required_fragments = {
        "r1_retry_error_history": "_r1_error_history.append(_r1_last_error)",
        "r1_retry_history_prompt": "retry_error_history=_r1_error_history",
    }
    blitz_required_calls = {
        "parallel_trigger": "should_run_parallel",
        "recombine_call": "recombine",
    }
    blitz_required_literals = {
        "recombination_flag": "enable_recombination",
    }
    rubric_required_literals = {
        "newton_gate": "rubric_mode='newton'",
        "kepler_banner": "Kepler-mode rubric",
    }
    missing = {
        f"autoresearch_loop.{name}": needle
        for name, needle in loop_required_calls.items()
        if needle not in loop_calls
    }
    missing.update({
        f"autoresearch_loop.{name}": needle
        for name, needle in loop_required_fragments.items()
        if needle not in loop_source
    })
    missing.update({
        f"blitz_dispatch.{name}": needle
        for name, needle in blitz_required_calls.items()
        if needle not in blitz_calls
    })
    missing.update({
        f"blitz_dispatch.{name}": needle
        for name, needle in blitz_required_literals.items()
        if needle not in blitz_literals
    })
    missing.update({
        f"rubric_mode_resolver.{name}": needle
        for name, needle in rubric_required_literals.items()
        if not _has_string_fragment(rubric_literals, needle)
    })
    return (_ok if not missing else _fail)(
        "static_autoresearch_wiring",
        "autoresearch loop and blitz dispatcher contain expected executable call-sites and retry feedback wiring",
        missing=missing,
    )


FIXTURES = (
    _fixture_pivot_heuristics,
    _fixture_primitive_class_rotation,
    _fixture_parallel_mutator,
    _fixture_recombination_r1,
    _fixture_blitz_survival_report,
    _fixture_eigenquestion_validation,
    _fixture_eigenquestion_launch_preflight,
    _fixture_tried_failed_digest_provider,
    _fixture_rubric_mode_defaults,
    _fixture_run_surface_validation,
    _fixture_hill_climb_prompt_boundary,
    _fixture_static_autoresearch_wiring,
)


def mechanism_status_summary(results: list[FixtureResult]) -> dict[str, Any]:
    """Summarize what the fixture matrix proves by mechanism status.

    `active` means the mechanism affects launch, prompt, state, or evaluation
    boundaries. `advisory` means it intentionally requires operator review
    before changing a run. `diagnostic` means it measures or guards the loop but
    does not steer proposals by itself.
    """

    rows: list[dict[str, Any]] = []
    by_status: dict[str, dict[str, int]] = {}
    known_names = set(MECHANISM_STATUS)
    result_names = {result.name for result in results}
    for result in results:
        meta = MECHANISM_STATUS.get(result.name, {})
        status = meta.get("status", "unclassified")
        bucket = by_status.setdefault(status, {"passed": 0, "total": 0})
        bucket["total"] += 1
        bucket["passed"] += int(result.passed)
        rows.append({
            "fixture": result.name,
            "mechanism": meta.get("mechanism", result.name),
            "status": status,
            "passed": result.passed,
            "proves": meta.get("proves", result.detail),
            "try_command": meta.get("try_command", "make inloop-fixture-validate JSON=1"),
            "test_reference": meta.get("test_reference", ""),
        })
    return {
        "legend": {
            "active": "affects launch, prompt, state, or evaluation boundaries",
            "advisory": "surfaces reviewable state but does not rewrite project intent",
            "diagnostic": "measures or guards the loop without steering proposals",
            "unclassified": "fixture lacks an explicit status entry",
        },
        "by_status": by_status,
        "rows": rows,
        "unmapped_fixtures": sorted(result_names - known_names),
        "missing_fixture_results": sorted(known_names - result_names),
    }


def run_fixtures() -> dict[str, Any]:
    results: list[FixtureResult] = []
    for fixture in FIXTURES:
        try:
            results.append(fixture())
        except Exception as exc:  # noqa: BLE001
            results.append(_fail(fixture.__name__, f"{type(exc).__name__}: {exc}"))
    return {
        "schema": "ztare-inloop-mechanism-fixtures-v1",
        "passed": all(result.passed for result in results),
        "num_fixtures": len(results),
        "num_passed": sum(1 for result in results if result.passed),
        "results": [asdict(result) for result in results],
        "mechanism_status": mechanism_status_summary(results),
    }


def render_text(summary: dict[str, Any]) -> str:
    lines = [
        "In-loop mechanism fixture matrix",
        f"passed: {summary['num_passed']}/{summary['num_fixtures']} (all_passed={summary['passed']})",
    ]
    status_summary = summary.get("mechanism_status") or {}
    by_status = status_summary.get("by_status") or {}
    if by_status:
        parts = [
            f"{status}={counts.get('passed', 0)}/{counts.get('total', 0)}"
            for status, counts in sorted(by_status.items())
        ]
        lines.append("coverage: " + ", ".join(parts))
    for result in summary["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        meta = next(
            (
                row for row in (status_summary.get("rows") or [])
                if row.get("fixture") == result["name"]
            ),
            {},
        )
        mechanism_status = meta.get("status", "unclassified")
        mechanism = meta.get("mechanism", result["name"])
        lines.append(
            f"- {status} {result['name']} [{mechanism_status}; {mechanism}]: "
            f"{result['detail']}"
        )
        if meta.get("try_command"):
            lines.append(f"  try: {meta['try_command']}")
        if meta.get("test_reference"):
            lines.append(f"  test: {meta['test_reference']}")
    unmapped = status_summary.get("unmapped_fixtures") or []
    missing = status_summary.get("missing_fixture_results") or []
    if unmapped:
        lines.append(f"unmapped fixtures: {', '.join(unmapped)}")
    if missing:
        lines.append(f"missing fixture results: {', '.join(missing)}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    args = parser.parse_args(argv)

    summary = run_fixtures()
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(render_text(summary))
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
