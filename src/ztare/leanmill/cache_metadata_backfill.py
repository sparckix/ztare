"""Dry-run-first statement-id backfill for LeanMill cache stores.

This tool upgrades old JSONL rows that predate `statement_id` metadata. It is
not part of proof search and never runs implicitly. Default mode is a read-only
report; `--write` creates a timestamped backup and atomically replaces the
JSONL file.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from ztare.leanmill.common import write_text_atomic
from ztare.leanmill.control_plane import StatementId
from ztare.leanmill.run_observability import (
    DEFAULT_FAITHFULNESS_STORE,
    DEFAULT_NO_GOOD_STORE,
    DEFAULT_PROOF_CACHE,
)


DEFAULT_SURFACES = {
    "proof_cache": DEFAULT_PROOF_CACHE,
    "no_good": DEFAULT_NO_GOOD_STORE,
    "faithfulness": DEFAULT_FAITHFULNESS_STORE,
}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            rows.append({"_malformed_jsonl": line})
            continue
        rows.append(obj if isinstance(obj, dict) else {"_non_object_jsonl": obj})
    return rows


def _statement_name(statement: str) -> str:
    try:
        from ztare.leanmill.lean_source import theorem_names
        names = theorem_names(statement or "")
        return names[-1] if names else ""
    except Exception:  # noqa: BLE001
        return ""


def _statement_id_for(surface: str, row: dict[str, Any]) -> dict[str, Any] | None:
    statement = str(row.get("statement") or row.get("goal") or row.get("lean_statement") or "").strip()
    if not statement:
        return None
    nl = str(row.get("nl") or "").strip()
    if surface == "faithfulness" and not nl:
        return None
    sid = StatementId.from_parts(
        target_name=_statement_name(statement),
        source_text=statement,
        closed_prop=statement,
        nl_exact=nl,
    )
    payload = sid.to_json()
    return payload if any(payload.values()) else None


def backfill_rows(surface: str, rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    out: list[dict[str, Any]] = []
    changed = 0
    malformed = 0
    missing_statement_payload = 0
    already_has_statement_id = 0
    for row in rows:
        rec = dict(row)
        if "_malformed_jsonl" in rec or "_non_object_jsonl" in rec:
            malformed += 1
            out.append(rec)
            continue
        sid = rec.get("statement_id")
        if isinstance(sid, dict) and any(sid.values()):
            already_has_statement_id += 1
            out.append(rec)
            continue
        derived = _statement_id_for(surface, rec)
        if not derived:
            missing_statement_payload += 1
            out.append(rec)
            continue
        rec["statement_id"] = derived
        changed += 1
        out.append(rec)
    return out, {
        "schema": "leanmill.cache_metadata_backfill.v1",
        "surface": surface,
        "total": len(rows),
        "already_has_statement_id": already_has_statement_id,
        "backfilled": changed,
        "missing_statement_payload": missing_statement_payload,
        "malformed": malformed,
    }


def backfill_file(surface: str, path: str | Path, *, write: bool = False) -> dict[str, Any]:
    p = Path(path)
    rows = _read_jsonl(p)
    out, report = backfill_rows(surface, rows)
    report["path"] = str(p)
    report["write"] = bool(write)
    if write and report["backfilled"]:
        stamp = time.strftime("%Y%m%dT%H%M%S")
        backup = p.with_name(f"{p.name}.bak.{stamp}")
        backup.write_text(p.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
        text = "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in out) + "\n"
        write_text_atomic(p, text)
        report["backup_path"] = str(backup)
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Dry-run or apply statement_id backfill for LeanMill cache JSONL stores")
    ap.add_argument("--surface", choices=sorted(DEFAULT_SURFACES), required=True)
    ap.add_argument("--path", default="")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)
    path = Path(args.path) if args.path else DEFAULT_SURFACES[args.surface]
    print(json.dumps(backfill_file(args.surface, path, write=args.write), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
