#!/usr/bin/env python3
"""Replay the statement gate without mutating a historical target wave."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys


REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "src"))

from ztare.leanmill.common import read_json, write_json_atomic  # noqa: E402
from ztare.leanmill.target_curriculum import (  # noqa: E402
    build_target_conjecture_admission,
    build_target_statement_revision_feedback,
    preflight_target_conjecture_wave,
)
from ztare.leanmill.target_curriculum_adjudication import (  # noqa: E402
    continue_target_conjecture_admission,
)
from ztare.leanmill.theory_ir import content_hash  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wave", type=Path, required=True)
    parser.add_argument("--historical-guide", type=Path, required=True)
    parser.add_argument("--historical-admission", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--lean-root", type=Path, default=REPO / "ztare_proofs")
    args = parser.parse_args(argv)
    wave = read_json(args.wave, None)
    guide = read_json(args.historical_guide, None)
    historical_admission = read_json(args.historical_admission, None)
    if not all(isinstance(value, dict) for value in (
        wave, guide, historical_admission
    )):
        raise ValueError("statement replay inputs must be JSON objects")
    args.artifacts.mkdir(parents=True, exist_ok=True)
    elaboration = preflight_target_conjecture_wave(
        wave, lean_root=args.lean_root
    )
    write_json_atomic(args.artifacts / "statement_elaboration.json", elaboration)
    feedback = build_target_statement_revision_feedback(
        wave,
        elaboration,
        lean_root=args.lean_root,
        successor_revision_epoch=1,
    )
    write_json_atomic(args.artifacts / "statement_revision_feedback.json", feedback)
    eligible = set(elaboration["guide_eligible_candidate_ids"])
    selected = [
        str(value) for value in historical_admission["selected_candidate_ids"]
        if str(value) in eligible
    ]
    corrected_admission = build_target_conjecture_admission(
        wave,
        elaboration,
        run_tag=str(historical_admission["run_tag"]) + "-postfix-replay",
        deck_sha256=str(historical_admission["deck_sha256"]),
        replay_receipt_sha256=str(
            historical_admission["replay_receipt_sha256"]
        ),
        guide_receipt=guide,
        selected_candidate_ids=selected,
    )
    write_json_atomic(args.artifacts / "admission.json", corrected_admission)
    continuation = continue_target_conjecture_admission(
        wave,
        elaboration,
        guide,
        corrected_admission,
        lean_root=args.lean_root,
        artifact_dir=args.artifacts / "adjudication",
        solve_fn=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("all-rejected replay must dispatch no solver")
        ),
    )
    action_kernel_ids = [
        str(row["candidate_id"])
        for row in wave["candidates"]
        if row.get("candidate_family") == "action_kernel_quotient"
    ]
    boundary_core = {
        "schema": "leanmill.target_statement_gate_replay_boundary.v1",
        "source_wave_sha256": str(wave["wave_sha256"]),
        "historical_admission_receipt_sha256": str(
            historical_admission["receipt_sha256"]
        ),
        "statement_elaboration_receipt_sha256": str(elaboration["receipt_sha256"]),
        "corrected_admission_receipt_sha256": str(
            corrected_admission["receipt_sha256"]
        ),
        "continuation_receipt_sha256": str(continuation["receipt_sha256"]),
        "historical_executable_admission_status": "superseded",
        "candidate_count": int(elaboration["candidate_count"]),
        "elaborated_candidate_ids": list(
            elaboration["guide_eligible_candidate_ids"]
        ),
        "rejected_candidate_ids": list(elaboration["rejected_candidate_ids"]),
        "action_kernel_candidate_ids": action_kernel_ids,
        "action_kernel_statement_scope_status": "all_rejected",
        "later_source_adjacent_salvage_theorems": [
            "AxiomPackOrbitActionExtractionFiber.sameAction_iff_quotientDefect_actsTrivially",
            "AxiomPackOrbitActionExtractionFiber.orbitAction_sameExtractedFourOperations_iff_baseRowColumnActionsAgree",
            "AxiomPackOrbitActionExtractionFiber.orbitAction_reconstruction_iff_factorizationDefect_actsTrivially",
            "AxiomPackOrbitActionExtractionFiber.orbitAction_nested_reconstruction_iff_factorizationDefect_actsTrivially",
        ],
        "salvage_relation": (
            "manual_source_adjacent_repair_not_automatic_closure_of_rejected_candidate_bytes"
        ),
        "provider_calls_charged": 0,
        "authority": "postfix_replay_preserves_historical_wave",
    }
    boundary = {**boundary_core, "receipt_sha256": content_hash(boundary_core)}
    write_json_atomic(args.artifacts / "replay_boundary.json", boundary)
    print(
        f"statement_elaboration={elaboration['receipt_sha256']} "
        f"eligible={len(eligible)} rejected={len(elaboration['rejected_candidate_ids'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
