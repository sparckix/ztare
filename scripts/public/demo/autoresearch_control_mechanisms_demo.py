#!/usr/bin/env python3
"""Materialize a controlled autoresearch project for optional in-loop controls.

This is a local replay, not a live LLM experiment. It exercises the same local
dispatch/tracking/preflight surfaces that normal runs use, then lets the
mechanism consequence audit read the resulting project-scoped evidence.
"""
from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import asdict
from pathlib import Path
from typing import Any

from src.ztare.common.file_io import append_jsonl
from src.ztare.orchestrator.blitz_dispatch import BlitzDispatchInputs, dispatch_mutator_blitz
from src.ztare.orchestrator.control_followup_policy import (
    evaluate_control_followup,
    record_control_followup_decision,
)
from src.ztare.reports.blitz_survival_report import build_blitz_survival_report
from src.ztare.reports.autoresearch_trace import build_autoresearch_trace
from src.ztare.reports.hill_climb_behavior_audit import build_hill_climb_behavior_audit
from src.ztare.reports.mechanism_consequence_audit import audit_mechanism_consequences
from src.ztare.research_director.primitive_class_rotation import (
    maybe_track_primitive_class_rotation,
)
from src.ztare.scaffold.substrate_queue import (
    build_project_packet,
    validate_project_packet,
    write_project_packet,
)
from src.ztare.workspace.update_workspace import checkpoint_source_index


REPO = Path(__file__).resolve().parents[3]
DEFAULT_PROJECT = "autoresearch_control_demo_20260613"
CONTROL_REPLAY_RUN_ID = "controlled_replay_20260613"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _rubric() -> dict[str, Any]:
    return {
        "disable_evidence_fit_gate": True,
        "disable_evidence_fit_gate_reason": (
            "controlled qualitative replay; evidence fit gate does not apply"
        ),
        "disable_uniqueness_gap_gate": True,
        "disable_uniqueness_gap_gate_reason": (
            "controlled qualitative replay; uniqueness keyword gate does not apply"
        ),
        "holdout_hard_gate": False,
        "enable_fit_primitive": False,
        "fit_score_mode": "none",
        "require_i_model_in_submission": False,
        "discovery_mode": False,
        "falsification_mode": "bounded_discriminator",
        "rubric_mode": "calibration",
        "rubric_mode_reason": (
            "controlled replay for optional in-loop controls, not a discovery run"
        ),
        "parallel_mutator_k": 3,
        "parallel_mutator_force_iters": [1],
        "parallel_mutator_min_stagnation": 2,
        "parallel_mutator_force": False,
        "control_followup_window": 3,
        "enable_recombination": False,
        "enable_primitive_class_rotation": True,
        "cage_meta": {"class": "autoresearch_control"},
        "persona": (
            "Evaluate whether the controlled replay produces the expected "
            "autoresearch control artifacts without treating the replay as live "
            "scientific evidence."
        ),
        "dimensions": [
            {
                "name": "Control artifact validity",
                "weight": 40,
                "description": (
                    "Does the candidate name which control artifact changed and "
                    "why that artifact is inspectable?"
                ),
            },
            {
                "name": "Scope calibration",
                "weight": 35,
                "description": (
                    "Does the candidate distinguish controlled replay evidence "
                    "from live autoresearch outcome evidence?"
                ),
            },
            {
                "name": "Failure condition",
                "weight": 25,
                "description": (
                    "Does the candidate name a condition under which the replay "
                    "would fail to prove wiring?"
                ),
            },
        ],
        "criteria": {
            "1_Control_artifact_validity": (
                "Names concrete artifacts and their consumer in the audit."
            ),
            "2_Scope_calibration": (
                "Does not claim live scientific lift from a controlled replay."
            ),
            "3_Failure_condition": (
                "States what missing artifact or mismatch would falsify the replay."
            ),
        },
    }


def _seed_project(project_dir: Path, rubric_path: Path, rubric: dict[str, Any]) -> None:
    _write(
        project_dir / "project_charter.md",
        """# Project Charter - autoresearch control demo

## Core Question

Can optional in-loop controls produce project-scoped artifacts that the
mechanism consequence audit can observe?

## Eigenquestion

Which optional control changes a downstream artifact rather than only adding
operator-facing text?

## Task

Use only the local replay artifacts. Do not treat this project as evidence of
live research quality or transport advantage.
""",
    )
    _write(
        project_dir / "thesis.md",
        """# Controlled Replay Thesis

This project is a reproducibility surface for optional autoresearch controls.
The claim is narrow: when the replay calls the local dispatch and class-rotation
helpers, the standard project audit can observe their artifacts.

## Fit Declaration

```json
{"variables": [], "expression": "0", "parameter_names": []}
```
""",
    )
    _write(
        project_dir / "evidence.txt",
        """E1. This is a controlled local replay, not a live LLM run.
E2. The replay must materialize parallel_blitz_log.jsonl.
E3. The replay must materialize explored_primitive_classes.jsonl.
E4. The replay must materialize a proposed_eigenquestion markdown file.
E5. The replay must materialize control_followup_policy.jsonl.
""",
    )
    _write(
        project_dir / "raw" / "source.md",
        """---
source_type: source_evidence
---
Controlled source for the autoresearch control demo. The evidence boundary is
limited to local replay artifacts: blitz logs, class-rotation logs,
eigenquestion proposal, and control follow-up policy decisions.
""",
    )
    _write(
        project_dir / "test_model.py",
        """PARAMETER_NAMES = []
PARAMETRIC_FORM = "0"


def I_model(features=None, params=None):
    return 0.0


f = I_model
model = I_model
""",
    )
    _write(
        project_dir / "raw" / "source_type_map.json",
        json.dumps({"source.md": "source_evidence"}, indent=2, sort_keys=True) + "\n",
    )
    _write(rubric_path, json.dumps(rubric, indent=2, sort_keys=True) + "\n")


def _stamp_jsonl_run_id(path: Path, *, run_id: str) -> None:
    rows: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    changed = False
    for line in lines:
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            rows.append({"_raw": line})
            continue
        if isinstance(row, dict):
            if not row.get("run_id"):
                row["run_id"] = run_id
                changed = True
            rows.append(row)
    if changed:
        rendered = []
        for row in rows:
            if set(row) == {"_raw"}:
                rendered.append(str(row["_raw"]))
            else:
                rendered.append(json.dumps(row, sort_keys=True))
        path.write_text("\n".join(rendered) + "\n", encoding="utf-8")


def _run_blitz_replay(project_dir: Path, rubric: dict[str, Any]) -> dict[str, Any]:
    workspace = project_dir / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)

    def single_mutate(persona: str) -> str:
        label = persona or "single"
        return f"""# Candidate from {label}

## Structural Mutation: {label} residual-boundary control

mechanism = propose_new_primitive_class

PARAMETER_NAMES = []
PARAMETRIC_FORM = "0"
"""

    result = dispatch_mutator_blitz(
        BlitzDispatchInputs(
            stagnation_count=0,
            iter_idx=1,
            rubric_data=rubric,
            workspace_dir=workspace,
            current_thesis=(project_dir / "thesis.md").read_text(encoding="utf-8"),
            current_mutator="local_replay",
            single_mutate=single_mutate,
        )
    )
    _stamp_jsonl_run_id(workspace / "parallel_blitz_log.jsonl", run_id=CONTROL_REPLAY_RUN_ID)
    append_jsonl(
        workspace / "eval_history.jsonl",
        {
            "iteration": 1,
            "run_id": CONTROL_REPLAY_RUN_ID,
            "score": 51,
            "weakest_point": "controlled replay",
        },
    )
    append_jsonl(
        workspace / "iteration_telemetry.jsonl",
        {
            "record_type": "iteration",
            "run_id": CONTROL_REPLAY_RUN_ID,
            "iteration_index": 1,
            "score": 51,
            "champion_promoted": False,
            "gate_failure_count": 0,
            "failed_gate_ids": [],
            "stagnation_count": 0,
        },
    )
    report = build_blitz_survival_report(workspace)
    _write(
        workspace / "blitz_survival_report.json",
        json.dumps(report, indent=2, sort_keys=True) + "\n",
    )
    return {
        "K_used": result.K_used,
        "parallel_decision_reason": result.parallel_decision_reason,
        "winner_stage_origin": result.winner_stage_origin,
        "survival_summary": report.get("summary", {}),
    }


def _run_rotation_replay(project_dir: Path, rubric: dict[str, Any]) -> dict[str, Any]:
    thesis = """# Controlled class proposal

## Structural Mutation: residual-boundary replay ledger

mechanism = propose_new_primitive_class
"""
    result = maybe_track_primitive_class_rotation(
        rubric_data=rubric,
        project_dir=project_dir,
        run_id=CONTROL_REPLAY_RUN_ID,
        iter_index=1,
        thesis_text=thesis,
        score=51.0,
        outcome="controlled_replay",
        use_llm=False,
    )
    return {
        "tracked": result.tracked,
        "class_name": result.class_name,
        "reason": result.reason,
    }


def _write_eigenquestion(project_dir: Path) -> str:
    path = project_dir / "proposed_eigenquestion_20260613T000000Z.md"
    _write(
        path,
        """# Proposed Eigenquestion - controlled replay

What would show that an optional in-loop control changed the next candidate
selection boundary, rather than only creating a diagnostic artifact?

_Method:_ controlled local replay. This proposal is advisory and must not edit
`project_charter.md` automatically.
""",
    )
    return str(path)


def _run_followup_policy_replay(project_dir: Path, rubric: dict[str, Any]) -> dict[str, Any]:
    workspace = project_dir / "workspace"
    decision = evaluate_control_followup(
        workspace,
        current_iteration=2,
        rubric_data=rubric,
        candidate_control_kind="parallel_blitz",
    )
    record_control_followup_decision(
        workspace,
        decision,
        run_id=CONTROL_REPLAY_RUN_ID,
        project=project_dir.name,
        iteration_index=2,
    )
    append_jsonl(
        workspace / "loop_events.jsonl",
        {
            "event_type": "control_followup_observe",
            "iteration_index": 2,
            "candidate_control_kind": "parallel_blitz",
            "decision": decision.decision,
            "allowed": decision.allowed,
            "reason": decision.reason,
        },
    )
    append_jsonl(
        workspace / "iteration_telemetry.jsonl",
        {
            "record_type": "iteration",
            "run_id": CONTROL_REPLAY_RUN_ID,
            "iteration_index": 2,
            "score": 51,
            "champion_promoted": False,
            "gate_failure_count": 0,
            "failed_gate_ids": [],
            "stagnation_count": 1,
            "loop_control_action": "control_followup_observe",
            "pending_loop_action": "CONTINUE",
            "score_improved": False,
        },
    )
    payload = asdict(decision)
    return {
        "decision": payload,
        "expected_block": True,
        "observed_block": decision.allowed is False,
    }


def _write_validated_packet(
    *,
    repo: Path,
    project_dir: Path,
    project: str,
    rubric: str,
) -> dict[str, Any]:
    expected_command = (
        "ztare autoresearch route "
        "--task 'validate controlled follow-up policy replay handoff' "
        f"--project {project} --rubric {rubric}"
    )
    packet = build_project_packet(
        project=project,
        rubric=rubric,
        task="Validate the controlled autoresearch control-demo handoff.",
        bounded_claim=(
            "The controlled local replay emits source-ready intake metadata and "
            "observable in-loop control artifacts for audit."
        ),
        source_refs=[
            str((project_dir / "raw" / "source.md").relative_to(repo)),
        ],
        evidence_refs=[
            str((project_dir / "workspace" / "control_followup_policy.jsonl").relative_to(repo)),
            str((project_dir / "workspace" / "parallel_blitz_log.jsonl").relative_to(repo)),
            str((project_dir / "workspace" / "explored_primitive_classes.jsonl").relative_to(repo)),
        ],
        non_claims=[
            "This packet is not evidence of live research quality.",
            "This packet is not a transport comparison.",
        ],
        next_falsifier=(
            "Remove any declared replay artifact or break source typing; packet "
            "validation with source preflight must fail."
        ),
        expected_command=expected_command,
        notes="Generated by the controlled autoresearch control-demo replay.",
    )
    packet_path = project_dir / "control_demo_packet.json"
    write_project_packet(packet_path, packet)
    validation = validate_project_packet(
        packet,
        repo_root=repo,
        require_source_preflight=True,
    )
    return {
        "path": str(packet_path.relative_to(repo)),
        "packet_id": packet.get("packet_id"),
        "validation": validation,
        "expected_command": expected_command,
    }


def _write_source_index_checkpoint(*, repo: Path, project_dir: Path) -> dict[str, Any]:
    checkpoint = checkpoint_source_index(
        project_dir=project_dir,
        raw_dir=project_dir / "raw",
        workspace_dir=project_dir / "workspace",
        model_family="gemini",
        max_files=25,
        max_chars_per_file=12000,
        max_total_chars=100000,
    )
    normalized = dict(checkpoint)
    for key in ("workspace_dir", "source_index", "workspace_meta"):
        value = normalized.get(key)
        if value:
            try:
                normalized[key] = str(Path(str(value)).resolve().relative_to(repo))
            except ValueError:
                normalized[key] = str(value)
    return normalized


def _trace_kernel_entry(
    *,
    repo: Path,
    project: str,
    rubric: str,
    packet_path: str,
) -> dict[str, Any]:
    resolved_packet = Path(packet_path)
    if not resolved_packet.is_absolute():
        resolved_packet = repo / resolved_packet
    trace = build_autoresearch_trace(
        repo=repo,
        project=project,
        rubric=rubric,
        packet=str(resolved_packet),
        full_health=False,
    )
    kernel_entry = trace.get("kernel_entry") if isinstance(trace, dict) else {}
    if not isinstance(kernel_entry, dict):
        kernel_entry = {}
    return {
        "status": trace.get("status"),
        "readiness": trace.get("readiness"),
        "can_enter_kernel": bool(kernel_entry.get("can_enter_kernel")),
        "allowed_work_modes": list(kernel_entry.get("allowed_work_modes") or []),
        "blockers": list(kernel_entry.get("blockers") or []),
        "recovery_actions": list(trace.get("recovery_actions") or []),
        "next_commands": list(trace.get("next_commands") or []),
    }


def materialize_demo(
    *,
    repo: Path = REPO,
    project: str = DEFAULT_PROJECT,
    force: bool = False,
) -> dict[str, Any]:
    repo = repo.resolve()
    project_dir = repo / "projects" / project
    rubric_path = repo / "rubrics" / f"{project}.json"
    if force:
        if project_dir.exists():
            shutil.rmtree(project_dir)
        if rubric_path.exists():
            rubric_path.unlink()
    elif project_dir.exists() or rubric_path.exists():
        raise FileExistsError(
            f"{project} already exists; pass --force to rebuild the controlled demo"
        )

    rubric = _rubric()
    _seed_project(project_dir, rubric_path, rubric)
    source_index_checkpoint = _write_source_index_checkpoint(repo=repo, project_dir=project_dir)
    blitz = _run_blitz_replay(project_dir, rubric)
    rotation = _run_rotation_replay(project_dir, rubric)
    eigenquestion_path = _write_eigenquestion(project_dir)
    followup_policy = _run_followup_policy_replay(project_dir, rubric)
    packet_validation = _write_validated_packet(
        repo=repo,
        project_dir=project_dir,
        project=project,
        rubric=project,
    )
    kernel_entry_trace = _trace_kernel_entry(
        repo=repo,
        project=project,
        rubric=project,
        packet_path=packet_validation["path"],
    )
    audit = audit_mechanism_consequences(repo=repo, project=project)
    hill_climb = build_hill_climb_behavior_audit(repo=repo, project=project)
    observed_optional = {
        row["mechanism_id"]: row["evidence_status"]
        for row in audit["rows"]
        if row["mechanism_id"]
        in {
            "control_followup_policy",
            "parallel_blitz",
            "primitive_class_rotation",
            "eigenquestion_preflight",
        }
    }
    packet = {
        "schema": "ztare-autoresearch-control-mechanisms-demo-v1",
        "project": project,
        "project_dir": str(project_dir.relative_to(repo)),
        "rubric": str(rubric_path.relative_to(repo)),
        "evidence_kind": "controlled_local_replay",
        "live_llm_calls": False,
        "blitz": blitz,
        "primitive_class_rotation": rotation,
        "eigenquestion": {"path": str(Path(eigenquestion_path).relative_to(repo))},
        "control_followup_policy": followup_policy,
        "source_index_checkpoint": source_index_checkpoint,
        "project_packet": packet_validation,
        "kernel_entry_trace": kernel_entry_trace,
        "observed_optional_mechanisms": observed_optional,
        "audit_summary": audit.get("summary", {}),
        "hill_climb_summary": {
            "status_counts": hill_climb.get("status_counts", {}),
            "mechanism_status_totals": hill_climb.get("mechanism_status_totals", {}),
            "post_control_outcome_totals": hill_climb.get("post_control_outcome_totals", {}),
            "post_control_diagnostic_counts": hill_climb.get(
                "post_control_diagnostic_counts", {}
            ),
        },
        "hill_climb_control_followup_policy_totals": hill_climb.get(
            "control_followup_policy_totals", {}
        ),
    }
    _write(
        project_dir / "workspace" / "control_mechanisms_demo_summary.json",
        json.dumps(packet, indent=2, sort_keys=True) + "\n",
    )
    return packet


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=DEFAULT_PROJECT)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    packet = materialize_demo(project=args.project, force=args.force)
    if args.json:
        print(json.dumps(packet, indent=2, sort_keys=True))
    else:
        print("Autoresearch control mechanism demo")
        print(f"project={packet['project']} evidence_kind={packet['evidence_kind']}")
        print("live_llm_calls=false")
        print(
            "observed_optional_mechanisms="
            + json.dumps(packet["observed_optional_mechanisms"], sort_keys=True)
        )
        print(f"summary={packet['project_dir']}/workspace/control_mechanisms_demo_summary.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
