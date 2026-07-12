from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ztare.common.file_io import append_jsonl, write_json


SCHEMA = "ztare-interface-inconsistency-receipt-v1"
LEDGER = "interface_inconsistency_receipts.jsonl"
LATEST = "latest_interface_inconsistency.json"


def build_interface_inconsistency_receipt(
    *,
    project_dir: str | Path,
    kind: str,
    invariant: str,
    producer_surface: str,
    consumer_surface: str,
    expected: str,
    observed: str,
    evidence_refs: list[str] | None = None,
    repair_status: str = "open",
    severity: str = "warning",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a diagnostic receipt for interface-contract contradictions.

    These rows are routing evidence for harness cleanup. They are never
    candidate evidence and cannot promote or reject a transition model.
    """

    basis = {
        "kind": str(kind),
        "invariant": str(invariant),
        "producer_surface": str(producer_surface),
        "consumer_surface": str(consumer_surface),
        "expected": str(expected),
        "observed": str(observed),
        "evidence_refs": sorted(str(ref) for ref in (evidence_refs or [])),
    }
    issue_sha = hashlib.sha256(
        json.dumps(basis, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "schema": SCHEMA,
        "issue_sha256": issue_sha,
        "project": str(Path(project_dir)),
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "kind": str(kind),
        "severity": str(severity),
        "invariant": str(invariant),
        "producer_surface": str(producer_surface),
        "consumer_surface": str(consumer_surface),
        "expected": str(expected),
        "observed": str(observed),
        "evidence_refs": [str(ref) for ref in (evidence_refs or [])],
        "repair_status": str(repair_status),
        "metadata": metadata or {},
        "authority": (
            "diagnostic only; cannot promote candidates, satisfy Strategy "
            "cards, or override deterministic gates"
        ),
    }


def write_interface_inconsistency_receipt(
    *,
    project_dir: str | Path,
    kind: str,
    invariant: str,
    producer_surface: str,
    consumer_surface: str,
    expected: str,
    observed: str,
    evidence_refs: list[str] | None = None,
    repair_status: str = "open",
    severity: str = "warning",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    project = Path(project_dir)
    receipt = build_interface_inconsistency_receipt(
        project_dir=project,
        kind=kind,
        invariant=invariant,
        producer_surface=producer_surface,
        consumer_surface=consumer_surface,
        expected=expected,
        observed=observed,
        evidence_refs=evidence_refs,
        repair_status=repair_status,
        severity=severity,
        metadata=metadata,
    )
    workspace = project / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    write_json(workspace / LATEST, receipt)
    append_jsonl(workspace / LEDGER, receipt)
    return receipt
