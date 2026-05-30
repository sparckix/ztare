#!/usr/bin/env python3
"""Build LeanSearch source-discovery queues from MCB corpus rows.

This is a machine-safe acquisition step. It does not call LeanSearch,
run Lean, replay proofs, or claim closure. It converts frozen corpus
rows into the source queue schema consumed by `leansearch_source_adapter`.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import tempfile
from pathlib import Path
from typing import Any
import re


DEFAULT_CORPUS = "/tmp/rung1/mcb_corpus_v2.json"
DEFAULT_EXCLUDE = "/tmp/rung1/four_arm_frozen_corpus.json"
DEFAULT_OUT = "analytics/public/leanmill/leansearch/LEANSEARCH_MCB_REMAINING_QUEUE.json"
DEFAULT_MD = "analytics/public/leanmill/leansearch/LEANSEARCH_MCB_REMAINING_QUEUE.md"


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_rows(path: Path) -> list[dict[str, Any]]:
    obj = json.loads(path.read_text(errors="ignore"))
    if isinstance(obj, list):
        return obj
    return list(obj.get("rows") or obj.get("corpus") or obj.get("targets") or [])


def _goal_keywords(goal: str, limit: int = 24) -> str:
    toks: list[str] = []
    seen: set[str] = set()
    for raw in goal.replace("\n", " ").replace("⊢", " ").split():
        tok = raw.strip("(){}[],:;")
        if len(tok) < 3:
            continue
        if tok.startswith(("inst", "?m.")):
            continue
        if tok in seen:
            continue
        seen.add(tok)
        toks.append(tok)
        if len(toks) >= limit:
            break
    return " ".join(toks)


def _source_file(row: dict[str, Any]) -> str:
    source = row.get("source") or {}
    f = str(source.get("file") or "")
    if not f:
        return ""
    return f if f.startswith("Mathlib/") else f"Mathlib/{f}"


def _target_decl_name(row: dict[str, Any]) -> str:
    src_path = Path(str(row.get("sorried_file") or ""))
    target_line = int(row.get("target_line") or 0)
    if not src_path.exists() or target_line <= 0:
        return ""
    lines = src_path.read_text(errors="ignore").splitlines()
    for i in range(max(0, target_line - 6), min(len(lines), target_line + 2)):
        m = re.match(r"\s*(?:theorem|lemma)\s+([^\s(:]+)", lines[i])
        if m:
            return m.group(1)
    return ""


def build(corpus: Path, exclude: Path | None, out: Path | None, markdown: Path | None,
          limit: int | None = None) -> dict[str, Any]:
    rows = _read_rows(corpus)
    exclude_ids: set[str] = set()
    exclude_names: set[str] = set()
    if exclude and exclude.exists():
        for r in _read_rows(exclude):
            name = str((r.get("source") or {}).get("mathlib_name") or r.get("target_name") or "")
            if name:
                exclude_names.add(name)
            else:
                exclude_ids.add(str(r.get("id") or r.get("row_id")))

    def is_excluded(row: dict[str, Any]) -> bool:
        name = str((row.get("source") or {}).get("mathlib_name") or row.get("target_name") or "")
        if str(row.get("id") or row.get("row_id")) in exclude_ids:
            return True
        if name:
            return name in exclude_names
        return str(row.get("id") or row.get("row_id")) in exclude_ids

    candidates = [r for r in rows if not is_excluded(r)]
    if limit is not None:
        candidates = candidates[:limit]

    queue: list[dict[str, Any]] = []
    for i, row in enumerate(candidates, start=1):
        source = row.get("source") or {}
        metadata_theorem = str(source.get("mathlib_name") or row.get("target_name") or row.get("id") or "")
        theorem = _target_decl_name(row) or metadata_theorem
        goal = str(row.get("goal") or "")
        source_hinge = f"{theorem} {_goal_keywords(goal)}".strip()
        queue.append({
            "row_id": str(row.get("id") or row.get("row_id") or f"mcb_row_{i}"),
            "theorem": theorem,
            "metadata_theorem": metadata_theorem,
            "source_file": _source_file(row),
            "source_hinge": source_hinge,
            "non_timeout_candidate_family": "LeanSearch external source acquisition from frozen MCB residual",
            "available_source_names": [theorem] if theorem else [],
            "priority": i,
            "priority_reason": "frozen remaining MCB row not in the completed four-arm band",
            "static_gate": [
                "LeanSearch proof bodies forbidden",
                "exact target declarations excluded",
                "post-target same-file declarations excluded",
                "static name-resolution before replay",
            ],
            "replay_gate": [
                "bounded one-row canary only after static filter",
                "Path-B authoritative governance required for any closure credit",
            ],
        })

    payload = {
        "schema": "leansearch-mcb-source-queue-v1",
        "generated_at": _now(),
        "corpus": str(corpus),
        "exclude": str(exclude) if exclude else None,
        "corpus_rows": len(rows),
        "excluded_rows": len(exclude_ids),
        "excluded_source_names": len(exclude_names),
        "source_discovery_queue_count": len(queue),
        "source_discovery_queue": queue,
        "source_policy": {
            "candidate_queue_only_no_external_call": True,
            "no_replay_or_training": True,
            "path_b_required_before_any_closure_credit": True,
        },
    }
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    if markdown:
        _write_md(payload, markdown)
    return payload


def _write_md(payload: dict[str, Any], path: Path) -> None:
    lines = [
        "# LeanSearch MCB Remaining Queue",
        "",
        f"Rows: `{payload['source_discovery_queue_count']}`",
        "",
        "| Rank | Row | Theorem | Source File | Query Seed |",
        "|---:|---|---|---|---|",
    ]
    for row in payload["source_discovery_queue"]:
        query = str(row.get("source_hinge") or "").replace("|", "/")[:100]
        lines.append(
            f"| {row['priority']} | `{row['row_id']}` | `{row['theorem']}` | "
            f"`{row['source_file']}` | {query} |"
        )
    lines.append("")
    lines.append("Boundary: queue construction only; LeanSearch, Lean replay, and Path-B governance are separate steps.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


def _self_test() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        corpus = root / "corpus.json"
        exclude = root / "exclude.json"
        out = root / "out.json"
        md = root / "out.md"
        corpus.write_text(json.dumps([
            {"id": "a", "source": {"mathlib_name": "foo", "file": "A/B.lean"}, "goal": "x : Nat ⊢ x = x"},
            {"id": "b", "source": {"mathlib_name": "bar", "file": "C.lean"}, "goal": "y : Real ⊢ 0 ≤ y"},
        ]))
        exclude.write_text(json.dumps({"rows": [{"id": "a"}]}))
        obj = build(corpus, exclude, out, md)
        assert obj["source_discovery_queue_count"] == 1, obj
        row = obj["source_discovery_queue"][0]
        assert row["row_id"] == "b", row
        assert row["source_file"] == "Mathlib/C.lean", row
        assert "bar" in row["source_hinge"], row
        sorried = root / "target.lean"
        sorried.write_text("lemma actual_target : True := by\n  sorry\n")
        corpus.write_text(json.dumps([{
            "id": "c",
            "source": {"mathlib_name": "metadata_target", "file": "D.lean"},
            "goal": "True",
            "sorried_file": str(sorried),
            "target_line": 1,
        }]))
        obj = build(corpus, None, None, None)
        assert obj["source_discovery_queue"][0]["theorem"] == "actual_target", obj
        assert obj["source_discovery_queue"][0]["metadata_theorem"] == "metadata_target", obj
        corpus.write_text(json.dumps([
            {"id": "a", "source": {"mathlib_name": "old_name", "file": "A.lean"}, "goal": "⊢ True"},
            {"id": "a", "source": {"mathlib_name": "fresh_name", "file": "B.lean"}, "goal": "⊢ True"},
        ]))
        exclude.write_text(json.dumps({"rows": [
            {"id": "a", "source": {"mathlib_name": "old_name", "file": "A.lean"}}
        ]}))
        obj = build(corpus, exclude, out, md)
        assert obj["source_discovery_queue_count"] == 1, obj
        assert obj["source_discovery_queue"][0]["theorem"] == "fresh_name", obj
    print("leansearch_mcb_queue self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=DEFAULT_CORPUS)
    ap.add_argument("--exclude", default=DEFAULT_EXCLUDE)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--markdown", default=DEFAULT_MD)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    obj = build(
        Path(args.corpus),
        Path(args.exclude) if args.exclude else None,
        Path(args.out) if args.out else None,
        Path(args.markdown) if args.markdown else None,
        args.limit,
    )
    print(json.dumps({
        "out": args.out,
        "markdown": args.markdown,
        "source_discovery_queue_count": obj["source_discovery_queue_count"],
        "corpus_rows": obj["corpus_rows"],
        "excluded_rows": obj["excluded_rows"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
