"""Best-effort typed verdict telemetry for LeanMill.

Proof behavior still lives at the existing kernel/governance gates. This store
only serializes their typed control-plane verdicts so diagnostics and future
readers do not reconstruct proof-credit state from prose logs.
"""
from __future__ import annotations

import os
import json
from pathlib import Path
import time
from typing import Any

from ztare.leanmill.control_plane import Verdict


REPO = Path(__file__).resolve().parents[3]
DEFAULT_VERDICT_LEDGER = REPO / "analytics" / "public" / "queries" / "leanmill_verdicts.jsonl"


def verdict_ledger_path() -> Path:
    raw = os.environ.get("ZTARE_LEANMILL_VERDICT_TRACE", "")
    if raw and raw != "1":
        return Path(raw)
    return DEFAULT_VERDICT_LEDGER


def emit_verdict(verdict: Verdict, *, extra: dict[str, Any] | None = None) -> bool:
    """Append one typed verdict row. Never raises into proof search."""
    if os.environ.get("ZTARE_LEANMILL_VERDICT_TRACE", "1") == "0":
        return False
    try:
        from ztare.leanmill.common import append_jsonl_locked
        row = {
            "schema": "leanmill.verdict.v1",
            "ts": time.time(),
            "run_tag": os.environ.get("ZTARE_SOLVER_RUN_TAG", ""),
            "verdict": verdict.to_json(),
        }
        if extra:
            row["extra"] = dict(extra)
        return append_jsonl_locked(verdict_ledger_path(), row)
    except Exception:  # noqa: BLE001
        return False


def iter_verdict_rows(path: "str | Path | None" = None, *, run_tag: str = "",
                      target_name: str = "") -> list[dict[str, Any]]:
    """Read typed verdict rows, skipping malformed/legacy lines.

    This is diagnostics-only; missing files and bad rows return fewer rows, not
    exceptions.
    """
    p = Path(path) if path else verdict_ledger_path()
    if not p.exists():
        return []
    out: list[dict[str, Any]] = []
    try:
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except Exception:  # noqa: BLE001
                continue
            if row.get("schema") != "leanmill.verdict.v1":
                continue
            if run_tag and row.get("run_tag") != run_tag:
                continue
            if target_name:
                verdict = row.get("verdict") if isinstance(row.get("verdict"), dict) else {}
                sid = verdict.get("statement_id") if isinstance(verdict.get("statement_id"), dict) else {}
                extra = row.get("extra") if isinstance(row.get("extra"), dict) else {}
                if target_name not in {sid.get("target_name"), extra.get("target_name")}:
                    continue
            out.append(row)
    except Exception:  # noqa: BLE001
        return []
    return out


def summarize_verdicts(path: "str | Path | None" = None, *, run_tag: str = "",
                       target_name: str = "") -> dict[str, Any]:
    rows = iter_verdict_rows(path, run_tag=run_tag, target_name=target_name)
    by_kind: dict[str, int] = {}
    latest: dict[str, Any] = {}
    for row in rows:
        verdict = row.get("verdict") if isinstance(row.get("verdict"), dict) else {}
        kind = str(verdict.get("kind") or "unknown")
        by_kind[kind] = by_kind.get(kind, 0) + 1
        if not latest or float(row.get("ts") or 0.0) >= float(latest.get("ts") or 0.0):
            latest = row
    latest_verdict = latest.get("verdict") if isinstance(latest.get("verdict"), dict) else {}
    return {
        "total": len(rows),
        "by_kind": by_kind,
        "latest_kind": latest_verdict.get("kind") or "",
        "latest_provenance": latest_verdict.get("provenance") or "",
    }
