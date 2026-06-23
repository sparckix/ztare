"""Evidence-gap persistence helper (Phase 4g, 2026-05-06 PM).

Single helper extracted from autoresearch_loop. Writes the evidence
gaps from a freshly-produced eval result to
``latest_evidence_gaps.json`` so the next iter's evidence-fetch
sees up-to-date gaps (previously only rubric-review wrote this
file, leaving the loop reading stale gaps).

Pure-ish — takes paths + project name + score-regime callable as
explicit args. The autoresearch_loop wrapper fills in the
module-globals it needs. Rows are normalized through the recovery-contract
interface before they become shared trace/fetch/graph state.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable

from ztare.common.file_io import write_json
from ztare.workspace.evidence_gaps import canonicalize_evidence_gap_recovery_contract


def refresh_latest_evidence_gaps_from_eval(
    evaluation: dict,
    *,
    project: str,
    output_path: str | Path,
    score_regime_fingerprint_from_score_contract: Callable,
    artifact_role: str = "latest",
) -> None:
    """Write evidence gaps from the current eval result to a json file.

    Fixes: LATEST_EVIDENCE_GAPS_PATH was never written by the loop —
    only by rubric-review. This meant evidence-fetch always saw stale
    gaps from the last manual rubric-review run. This helper closes
    that gap (no pun intended) by re-writing the file at every iter
    boundary where eval produces a non-empty gap list.

    No-op when the eval payload has no evidence_gaps (don't overwrite
    a stale-but-valid file with nothing).
    """
    gaps = _canonical_evidence_gap_rows(evaluation.get("evidence_gaps"))
    if not gaps:
        return
    score_contract = evaluation.get("score_contract") or {}
    payload = {
        "project": project,
        "judge_model": score_contract.get("judge_model", ""),
        "generated_on": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
        "artifact_role": artifact_role,
        "describes_baseline": artifact_role,
        "score": evaluation.get("score"),
        "weakest_point": evaluation.get("weakest_point", ""),
        "evidence_boundary_ceiling_detected": score_contract.get(
            "evidence_boundary_ceiling_detected", False
        ),
        "cap_reason": score_contract.get("evidence_boundary_detail", ""),
        "cap_reason_detail": "",
        "score_regime_fingerprint": score_regime_fingerprint_from_score_contract(
            evaluation.get("score_contract")
        ),
        "evidence_gaps": gaps,
    }
    write_json(output_path, payload)


def _canonical_evidence_gap_rows(raw_gaps: Any) -> list[dict[str, Any]]:
    """Normalize producer rows before they become the shared gap surface."""
    if not isinstance(raw_gaps, list):
        return []
    rows: list[dict[str, Any]] = []
    for item in raw_gaps:
        if not isinstance(item, dict):
            continue
        rows.append(
            canonicalize_evidence_gap_recovery_contract(
                item,
                recovery_kind=str(item.get("recovery_kind") or "").strip() or None,
                recovery_channel=str(item.get("recovery_channel") or "").strip() or None,
                required_surface=str(item.get("required_surface") or "").strip() or None,
                can_public_fetch=item.get("can_public_fetch"),
                in_loop_consumable=item.get("in_loop_consumable"),
            )
        )
    return rows
