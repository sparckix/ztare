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
from pathlib import Path
from typing import Any

from src.ztare.common.file_io import append_jsonl
from src.ztare.orchestrator.blitz_dispatch import BlitzDispatchInputs, dispatch_mutator_blitz
from src.ztare.reports.blitz_survival_report import build_blitz_survival_report
from src.ztare.reports.mechanism_consequence_audit import audit_mechanism_consequences
from src.ztare.research_director.primitive_class_rotation import (
    maybe_track_primitive_class_rotation,
)


REPO = Path(__file__).resolve().parents[3]
DEFAULT_PROJECT = "autoresearch_control_demo_20260613"


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
    _write(project_dir / "raw" / "source_type_map.json", "{}\n")
    _write(rubric_path, json.dumps(rubric, indent=2, sort_keys=True) + "\n")


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
    append_jsonl(
        workspace / "eval_history.jsonl",
        {"iteration": 1, "score": 51, "weakest_point": "controlled replay"},
    )
    append_jsonl(
        workspace / "iteration_telemetry.jsonl",
        {
            "record_type": "iteration",
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
        run_id="controlled_replay_20260613",
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
    blitz = _run_blitz_replay(project_dir, rubric)
    rotation = _run_rotation_replay(project_dir, rubric)
    eigenquestion_path = _write_eigenquestion(project_dir)
    audit = audit_mechanism_consequences(repo=repo, project=project)
    observed_optional = {
        row["mechanism_id"]: row["evidence_status"]
        for row in audit["rows"]
        if row["mechanism_id"]
        in {"parallel_blitz", "primitive_class_rotation", "eigenquestion_preflight"}
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
        "observed_optional_mechanisms": observed_optional,
        "audit_summary": audit.get("summary", {}),
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
