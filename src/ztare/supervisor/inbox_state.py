"""Pure logic for GP-071 Executive Inbox.

No Streamlit import. No UI state. Just the four primitives the wrapper
needs: list_pending, load_seam_text, resolve_gate, reconcile_pending_resolved.

Payload schema is the one written by
``supervisor.supervisor_findings_runner.emit_gate_escalation`` — see
GP-071 spec §3 for the contract this module codes against.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal


Decision = Literal["approve", "reject", "defer"]
_RESOLVED_DECISIONS: tuple[str, ...] = ("approve", "reject")


@dataclass(frozen=True)
class GatePayload:
    stem: str
    path: Path
    seam_path: str
    escalation_reason: str
    equivalent_gate_reason: str
    cycle_count: int
    total_cost_usd: float
    notes: tuple[str, ...]
    timestamp_utc: str
    advisory: bool
    raw: dict[str, Any] = field(default_factory=dict)


def _load_one(path: Path) -> GatePayload | None:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(
            f"[inbox_state] skipping malformed gate file {path.name}: {exc}",
            file=sys.stderr,
        )
        return None
    if not isinstance(raw, dict):
        print(
            f"[inbox_state] skipping non-object gate file {path.name}",
            file=sys.stderr,
        )
        return None
    try:
        return GatePayload(
            stem=path.stem,
            path=path,
            seam_path=str(raw.get("seam_path", "")),
            escalation_reason=str(raw.get("escalation_reason", "")),
            equivalent_gate_reason=str(raw.get("equivalent_gate_reason", "")),
            cycle_count=int(raw.get("cycle_count", 0)),
            total_cost_usd=float(raw.get("total_cost_usd", 0.0)),
            notes=tuple(str(n) for n in raw.get("notes", []) or ()),
            timestamp_utc=str(raw.get("timestamp_utc", "")),
            advisory=bool(raw.get("advisory", True)),
            raw=raw,
        )
    except (TypeError, ValueError) as exc:
        print(
            f"[inbox_state] skipping gate file {path.name} with bad field types: {exc}",
            file=sys.stderr,
        )
        return None


def list_pending(pending_dir: Path) -> list[GatePayload]:
    pending_dir.mkdir(parents=True, exist_ok=True)
    out: list[GatePayload] = []
    for entry in sorted(pending_dir.glob("*.json")):
        payload = _load_one(entry)
        if payload is not None:
            out.append(payload)
    out.sort(key=lambda p: (-p.total_cost_usd, p.timestamp_utc or ""))
    return out


def load_seam_text(seam_path: Path) -> str:
    try:
        return seam_path.read_text(encoding="utf-8")
    except OSError as exc:
        return f"[inbox_state] could not read seam at {seam_path}: {exc}"


def resolve_gate(
    stem: str,
    decision: Decision,
    operator_note: str,
    now_utc: datetime,
    pending_dir: Path,
    resolved_dir: Path,
) -> Path | None:
    if decision not in ("approve", "reject", "defer"):
        raise ValueError(f"unknown decision: {decision!r}")
    if operator_note is None:
        raise ValueError("operator_note field is mandatory (empty string allowed)")

    if decision == "defer":
        return None

    pending_dir.mkdir(parents=True, exist_ok=True)
    resolved_dir.mkdir(parents=True, exist_ok=True)

    pending_file = pending_dir / f"{stem}.json"
    if not pending_file.exists():
        raise FileNotFoundError(f"no pending gate for stem {stem!r}")

    original_payload = json.loads(pending_file.read_text(encoding="utf-8"))
    resolution = {
        "original_gate": original_payload,
        "decision": decision,
        "operator_note": operator_note,
        "resolved_at_utc": now_utc.isoformat(),
        "resolver": "operator",
    }

    resolved_file = resolved_dir / f"{stem}.json"
    tmp_file = resolved_dir / f"{stem}.json.tmp"
    with open(tmp_file, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(resolution, indent=2) + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp_file, resolved_file)

    try:
        pending_file.unlink()
    except FileNotFoundError:
        pass
    return resolved_file


def reconcile_pending_resolved(
    pending_dir: Path, resolved_dir: Path
) -> list[Path]:
    pending_dir.mkdir(parents=True, exist_ok=True)
    resolved_dir.mkdir(parents=True, exist_ok=True)

    deleted: list[Path] = []
    resolved_stems = {p.stem for p in resolved_dir.glob("*.json")}
    for entry in sorted(pending_dir.glob("*.json")):
        if entry.stem in resolved_stems:
            entry.unlink()
            deleted.append(entry)

    for stray_tmp in resolved_dir.glob("*.json.tmp"):
        try:
            stray_tmp.unlink()
        except OSError:
            pass

    return deleted
