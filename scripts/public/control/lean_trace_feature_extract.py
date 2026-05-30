#!/usr/bin/env python3
"""Extract lightweight proof-pattern features from ratified decider traces.

No Lean is run here. This reads completed four-arm checkpoint rows and
their persisted trace files, then emits JSONL features useful for the
next routing/action-selection dataset.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

DEFAULT_CKPT = "/tmp/rung1/four_arm_decider_ckpt.jsonl"
DEFAULT_OUT = "/tmp/rung1/lean_trace_features.jsonl"
TACTIC_TOKENS = [
    "simp_all", "simp", "aesop", "exact?", "apply?", "hammer", "duper",
    "linarith", "nlinarith", "ring", "norm_num", "omega", "refine",
    "exact", "rw", "rwa", "have", "calc", "intro", "gcongr",
    "constructor", "cases", "induction", "by_contra", "apply",
]


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines()
            if line.strip()]


def _proof_region(path: Path, target_name: str) -> str:
    if not path.exists():
        return ""
    lines = path.read_text(errors="ignore").splitlines()
    start = None
    pat = re.compile(rf"\b(theorem|lemma)\s+(?:_root_\.)?{re.escape(target_name)}\b")
    for i, line in enumerate(lines):
        if pat.search(line):
            start = i
            break
    if start is None:
        short = target_name.split(".")[-1]
        for i, line in enumerate(lines):
            if re.search(rf"\b(theorem|lemma)\s+(?:_root_\.)?{re.escape(short)}\b", line):
                start = i
                break
    if start is None:
        return ""
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if re.match(r"^\s*(theorem|lemma)\s+", lines[j]):
            end = j
            break
    return "\n".join(lines[start:end])


def _features(proof: str) -> dict[str, Any]:
    counts = Counter()
    for tok in TACTIC_TOKENS:
        counts[tok] = len(re.findall(rf"(?<![A-Za-z0-9_?]){re.escape(tok)}(?![A-Za-z0-9_?])", proof))
    nonzero = {k: v for k, v in counts.items() if v}
    lines = [ln for ln in proof.splitlines() if ln.strip()]
    return {
        "proof_lines": len(lines),
        "proof_chars": len(proof),
        "tactic_counts": nonzero,
        "has_structural_refine": int(bool(counts["refine"])),
        "has_local_lemmas": int(bool(counts["have"])),
        "has_rewrite": int(bool(counts["rw"] or counts["rwa"])),
        "has_automation": int(any(counts[t] for t in ("simp", "simp_all", "aesop", "linarith", "nlinarith", "ring", "norm_num", "omega"))),
        "has_external_tool_token": int(any(counts[t] for t in ("hammer", "duper"))),
    }


def build(ckpt: Path, out: Path) -> dict[str, Any]:
    rows = _load_jsonl(ckpt)
    out_rows: list[dict[str, Any]] = []
    arm_counts = Counter()
    tactic_totals = Counter()
    for row in rows:
        for arm in ("B1gs", "A"):
            meta = row.get(arm) or {}
            if not (meta.get("ratified") or meta.get("verdict") == "closure"):
                continue
            trace_dir = Path(str(meta.get("trace_dir") or ""))
            lean_files = sorted(trace_dir.glob("round_*.mcb_target.lean"))
            if not lean_files:
                continue
            proof = _proof_region(lean_files[-1], row["id"].split("_", 2)[-1])
            if not proof:
                # fall back to target_name unavailable in ckpt: use whole final file
                proof = lean_files[-1].read_text(errors="ignore")
            feats = _features(proof)
            tactic_totals.update(feats["tactic_counts"])
            arm_counts[arm] += 1
            out_rows.append({
                "row_id": row["id"],
                "arm": arm,
                "trace_file": str(lean_files[-1]),
                "calls": meta.get("calls"),
                "secs": meta.get("secs"),
                "features": feats,
            })
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(json.dumps(r, sort_keys=True) for r in out_rows) + "\n")
    summary = {
        "ckpt": str(ckpt),
        "out": str(out),
        "n_ratified_traces": len(out_rows),
        "arm_counts": dict(arm_counts),
        "tactic_totals": dict(tactic_totals),
    }
    print(json.dumps(summary, indent=1, sort_keys=True))
    return summary


def self_test() -> int:
    proof = """theorem t : True := by
  refine ?_
  have h : True := by simp
  exact h
"""
    feats = _features(proof)
    assert feats["tactic_counts"]["refine"] == 1
    assert feats["tactic_counts"]["have"] == 1
    assert feats["tactic_counts"]["simp"] == 1
    print("lean_trace_feature_extract self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", default=DEFAULT_CKPT)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    build(Path(args.ckpt), Path(args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
