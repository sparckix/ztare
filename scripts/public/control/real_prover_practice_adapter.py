#!/usr/bin/env python3
"""Normalize local REAL-Prover benchmark rows into GP225 practice packets.

This is an external sourcing adapter, not a solver benchmark. Rows emitted here
are practice/control rows by default because public benchmark contamination risk
is high. Promotion to clean-heldout is forbidden unless a later gate proves
source anchoring, target-context isolation, no proof-body use, and Path-B
governance under the same rules as natural MCB rows.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import tempfile
from pathlib import Path
from typing import Any


DEFAULT_DATA_DIR = (
    "analytics/public/leanmill/external_benchmarks/repos/"
    "REAL-Prover/Realprover/data"
)
DEFAULT_OUT = "analytics/public/leanmill/path_curricula/REAL_PROVER_PRACTICE_PACKET.json"
DEFAULT_MD = "analytics/public/leanmill/path_curricula/REAL_PROVER_PRACTICE_PACKET.md"


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _formal_statement(value: Any) -> str:
    if isinstance(value, list) and len(value) >= 2:
        return str(value[1] or "")
    return str(value or "")


def _target_name(stmt: str, fallback: str) -> str:
    m = re.search(r"\b(?:theorem|lemma)\s+([^\s(:]+)", stmt)
    if m:
        return m.group(1)
    if re.search(r"\bexample\b", stmt):
        return f"example_{fallback}"
    return fallback


def _has_sorry(stmt: str) -> bool:
    return bool(re.search(r"\b(sorry|by\s+sorry)\b", stmt))


def _imports(stmt: str) -> list[str]:
    out: list[str] = []
    for line in stmt.splitlines():
        line = line.strip()
        if line.startswith("import "):
            out.append(line.removeprefix("import ").strip())
    return out


def _iter_dataset(path: Path, dataset: str, limit: int | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for i, line in enumerate(path.read_text(errors="ignore").splitlines(), start=1):
        if limit is not None and len(rows) >= limit:
            break
        if not line.strip():
            continue
        raw = json.loads(line)
        stmt = _formal_statement(raw.get("formal_statement"))
        proof = raw.get("formal_proof")
        external_id = str(raw.get("id") if raw.get("id") is not None else i)
        row_id = f"realprover_{dataset}_{external_id}"
        rows.append({
            "row_id": row_id,
            "external_id": external_id,
            "dataset": dataset,
            "source_path": str(path),
            "source_sha256": _sha(line),
            "target_name": _target_name(stmt, external_id),
            "formal_statement": stmt,
            "formal_statement_sha256": _sha(stmt),
            "informal_statement": str(raw.get("informal_statement") or ""),
            "imports": _imports(stmt),
            "has_sorry": _has_sorry(stmt),
            "formal_proof_present": bool(proof),
            "formal_proof_consumed": False,
            "row_split": "practice_external_problem",
            "clean_heldout_eligible": False,
            "exclusion_reason": (
                "public_external_benchmark_practice_only_until_source_order_"
                "target_context_and_no_prior_exposure_gates_pass"
            ),
            "allowed_uses": [
                "factory_canary",
                "negative_control",
                "template_debugging",
                "practice_repair_trajectory",
            ],
            "forbidden_uses": [
                "clean_heldout_solver_claim",
                "training_label_without_separate_split",
                "closure_credit_without_path_b_governance",
            ],
            "gates_before_any_value_credit": [
                "compile_target_context",
                "proof_body_excluded",
                "exact_target_not_used_as_candidate",
                "path_b_authoritative_governance",
            ],
        })
    return rows


def build(args: argparse.Namespace) -> dict[str, Any]:
    data_dir = Path(args.data_dir)
    datasets = [d.strip() for d in args.datasets.split(",") if d.strip()]
    rows: list[dict[str, Any]] = []
    per_dataset_limit = args.per_dataset_limit
    remaining = args.limit
    for dataset in datasets:
        if remaining is not None and remaining <= 0:
            break
        limit = per_dataset_limit
        if remaining is not None:
            limit = min(remaining, limit) if limit is not None else remaining
        got = _iter_dataset(data_dir / f"{dataset}.jsonl", dataset, limit)
        rows.extend(got)
        if remaining is not None:
            remaining -= len(got)
    payload = {
        "schema": "real-prover-practice-packet-v1",
        "generated_at": _now(),
        "data_dir": str(data_dir),
        "datasets": datasets,
        "row_count": len(rows),
        "practice_only": True,
        "science_boundary": (
            "Rows are external practice/control inventory. They do not support "
            "clean heldout or solver-lift claims without later pinned "
            "target-context and Path-B governance gates."
        ),
        "rows": rows,
    }
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    if args.markdown:
        _write_md(payload, Path(args.markdown), args.md_limit)
    return payload


def _write_md(payload: dict[str, Any], path: Path, limit: int) -> None:
    lines = [
        "# REAL-Prover Practice Packet",
        "",
        f"Rows: `{payload['row_count']}`",
        "",
        "Boundary: practice/control only; no clean heldout claim.",
        "",
        "| Row | Dataset | Target | Imports | Split |",
        "|---|---|---|---:|---|",
    ]
    for row in payload.get("rows", [])[:limit]:
        lines.append(
            f"| `{row['row_id']}` | `{row['dataset']}` | `{row['target_name']}` | "
            f"{len(row.get('imports') or [])} | `{row['row_split']}` |"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


def _self_test() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        data = root / "data"
        data.mkdir()
        (data / "fate_m.jsonl").write_text(
            json.dumps({
                "id": "1",
                "formal_statement": "import Mathlib\n\nexample : True := sorry\n",
                "formal_proof": "",
                "informal_statement": "trivial",
            }) + "\n"
        )
        out = root / "out.json"
        obj = build(argparse.Namespace(
            data_dir=str(data),
            datasets="fate_m",
            limit=1,
            per_dataset_limit=None,
            out=str(out),
            markdown=None,
            md_limit=20,
        ))
        assert obj["row_count"] == 1, obj
        row = obj["rows"][0]
        assert row["row_split"] == "practice_external_problem", row
        assert row["has_sorry"] is True, row
        assert row["formal_proof_consumed"] is False, row
        assert row["clean_heldout_eligible"] is False, row
    print("real_prover_practice_adapter self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=DEFAULT_DATA_DIR)
    ap.add_argument("--datasets", default="fate_m,minif2f_valid,minif2f_test,proofnet_valid,proofnet_test")
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--per-dataset-limit", type=int, default=None)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--markdown", default=DEFAULT_MD)
    ap.add_argument("--md-limit", type=int, default=30)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    obj = build(args)
    print(json.dumps({
        "out": args.out,
        "markdown": args.markdown,
        "row_count": obj["row_count"],
        "practice_only": obj["practice_only"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
