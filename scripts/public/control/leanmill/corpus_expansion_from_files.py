#!/usr/bin/env python3
"""Build active LeanMill corpus rows from a directory of Lean target files.

This is a deterministic corpus-ingestion bridge. It does not source proofs and
does not award proof credit; it only turns existing Lean files into row records
that downstream stations may reference safely.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


DEFAULT_DATA_DIR = "analytics/public/leanmill/dashboard_data"
DEFAULT_SOURCE_DIR = "/tmp/rung1/mcb_expand100/files"
DEFAULT_OUT = f"{DEFAULT_DATA_DIR}/mcb_expand100_active_corpus.json"


def _sha_file(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _row_id_from_path(path: Path) -> str:
    match = re.match(r"^mcb_(\d+)_(.+)\.lean$", path.name)
    if not match:
        return ""
    return f"MCB_{int(match.group(1)):03d}_{match.group(2)}"


def _first_decl(text: str) -> tuple[str, str]:
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        if stripped.startswith("@["):
            continue
        match = re.match(r"^(?:private\s+|protected\s+|public\s+)?(?:theorem|lemma)\s+([A-Za-z0-9_'.]+)\b", stripped)
        if not match:
            continue
        chunk: list[str] = []
        for follow in lines[idx : idx + 12]:
            follow = follow.strip()
            if follow and not follow.startswith("--"):
                chunk.append(follow)
            joined = " ".join(chunk)
            if " :=" in joined or " by" in joined:
                break
        goal = " ".join(chunk)
        goal = re.sub(r"\s+", " ", goal).strip()
        return match.group(1), goal[:1000]
    return "", ""


def build(source_dir: Path, *, out: Path, include_empty: bool = False) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    source_dir = source_dir.expanduser()
    for path in sorted(source_dir.glob("mcb_*.lean")):
        row_id = _row_id_from_path(path)
        if not row_id:
            skipped.append({"path": str(path), "reason": "filename_not_mcb_row"})
            continue
        text = path.read_text(errors="ignore")
        decl_name, goal = _first_decl(text)
        if not goal and not include_empty:
            skipped.append({"path": str(path), "row_id": row_id, "reason": "no_theorem_or_lemma_decl"})
            continue
        rows.append({
            "row_id": row_id,
            "id": row_id,
            "goal": goal,
            "source_hinge": goal,
            "theorem_name": decl_name,
            "source": "mcb_expand100_file_corpus",
            "source_file": str(path),
            "sorried_file": str(path),
            "file_sha256": _sha_file(path),
        })
    payload = {
        "schema": "leanmill-corpus-expansion-from-files-v1",
        "source_dir": str(source_dir),
        "source_dir_exists": source_dir.exists(),
        "row_count": len(rows),
        "skipped_count": len(skipped),
        "rows": rows,
        "skipped": skipped[:200],
        "credit_boundary": {
            "proof_credit_eligible": False,
            "source_credit_eligible": False,
            "purpose": "active target/corpus addressability only",
        },
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload


def _self_test() -> int:
    import tempfile

    with tempfile.TemporaryDirectory(prefix="leanmill_corpus_expansion_") as td:
        root = Path(td)
        src = root / "files"
        src.mkdir()
        (src / "mcb_9_isBigO_rpow_top_log_smul.lean").write_text(
            "import Mathlib\n\n"
            "theorem isBigO_rpow_top_log_smul (f : Nat -> Nat) : True := by\n"
            "  trivial\n",
            encoding="utf-8",
        )
        out = root / "corpus.json"
        payload = build(src, out=out)
        assert payload["row_count"] == 1
        row = payload["rows"][0]
        assert row["row_id"] == "MCB_009_isBigO_rpow_top_log_smul"
        assert row["theorem_name"] == "isBigO_rpow_top_log_smul"
        assert "proof_credit_eligible" in payload["credit_boundary"]
        assert out.exists()
    print("leanmill_corpus_expansion_from_files self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-dir", default=DEFAULT_SOURCE_DIR)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--include-empty", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    payload = build(Path(args.source_dir), out=Path(args.out), include_empty=bool(args.include_empty))
    print(json.dumps({
        "schema": payload["schema"],
        "out": args.out,
        "row_count": payload["row_count"],
        "skipped_count": payload["skipped_count"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
