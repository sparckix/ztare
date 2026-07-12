from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from ztare.common.candidate_memory import admissible_candidate_memory_records
from ztare.common.control_state_machine import control_receipt_rows


def packed_control_receipts(text: str) -> str:
    rows = control_receipt_rows(text or "")
    return json.dumps(rows, sort_keys=True, separators=(",", ":"), default=str) if rows else ""


def candidate_memory_refs_for_retry(project_dir: str | Path | None) -> list[str]:
    if project_dir is None:
        return []
    project = Path(project_dir)
    try:
        payload = json.loads((project / "workspace" / "candidate_memory.json").read_text(encoding="utf-8"))
    except Exception:
        return []
    records = payload.get("records") if isinstance(payload, dict) else None
    if not isinstance(records, list):
        return []
    refs: list[str] = []
    for rec in admissible_candidate_memory_records(project, [row for row in records if isinstance(row, dict)]):
        rel = str(rec.get("submission") or "").strip()
        if rel and rel not in refs:
            refs.append(rel)
    return refs


def render_retry_pack_lines(
    *,
    receipts_text: str = "",
    candidate_memory_refs: Iterable[str] = (),
    heading: str = "RETRY PACK",
) -> str:
    lines = [heading + ":"]
    rows = control_receipt_rows(receipts_text or "")
    if rows:
        caps = [str(row.get("payload", {}).get("capability_id") or "") for row in rows if isinstance(row, dict)]
        caps = [cap for cap in caps if cap]
        lines.append(f"- control_receipts_count: {len(rows)}")
        if caps:
            lines.append("- receipt_capability_ids: " + ",".join(caps))
    refs = [str(ref).strip() for ref in candidate_memory_refs if str(ref).strip()]
    if refs:
        lines.append("- candidate_memory_refs:")
        lines.extend(f"  - {ref}" for ref in refs)
    return "\n".join(lines) + ("\n" if len(lines) > 1 else "")
