from __future__ import annotations

import json
from pathlib import Path

from ztare.orchestrator.evidence_gap_persistence import (
    refresh_latest_evidence_gaps_from_eval,
)


def test_refresh_latest_evidence_gaps_canonicalizes_recovery_contract(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "latest_evidence_gaps.json"

    refresh_latest_evidence_gaps_from_eval(
        {
            "score": 41,
            "weakest_point": "local fixture is missing",
            "score_contract": {"judge_model": "fixture-judge"},
            "evidence_gaps": [
                {
                    "target": "healthy-cache fixture row",
                    "description": "Local verifier fixture is missing.",
                    "recovery_kind": "local_verification",
                }
            ],
        },
        project="demo",
        output_path=output_path,
        score_regime_fingerprint_from_score_contract=lambda _contract: "fp-demo",
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    row = payload["evidence_gaps"][0]

    assert row["recovery_kind"] == "local_verification"
    assert row["recovery_channel"] == "in_loop_focus_receipt"
    assert row["can_public_fetch"] is False
    assert row["in_loop_consumable"] is True
    assert row["recovery_contract"]["schema"] == (
        "ztare-evidence-gap-recovery-contract-v1"
    )
    assert row["recovery_contract"]["contract_ok"] is True
