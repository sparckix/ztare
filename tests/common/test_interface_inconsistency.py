from __future__ import annotations

import json

from ztare.common.interface_inconsistency import write_interface_inconsistency_receipt


def test_interface_inconsistency_receipt_writes_latest_and_ledger(tmp_path) -> None:
    receipt = write_interface_inconsistency_receipt(
        project_dir=tmp_path,
        kind="patch_base_identity_mismatch",
        invariant="identity is full-digest bound",
        producer_surface="prompt",
        consumer_surface="gate",
        expected="full sha256",
        observed="prefix",
        evidence_refs=["workspace/submissions/base.py"],
        repair_status="blocked_by_gate",
    )

    latest = json.loads((tmp_path / "workspace" / "latest_interface_inconsistency.json").read_text())
    ledger_rows = (tmp_path / "workspace" / "interface_inconsistency_receipts.jsonl").read_text().splitlines()

    assert latest["schema"] == "ztare-interface-inconsistency-receipt-v1"
    assert latest["issue_sha256"] == receipt["issue_sha256"]
    assert len(ledger_rows) == 1
    assert json.loads(ledger_rows[0])["kind"] == "patch_base_identity_mismatch"
    assert "cannot promote candidates" in latest["authority"]
