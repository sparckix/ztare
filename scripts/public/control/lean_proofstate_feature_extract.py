#!/usr/bin/env python3
"""Extract pre-attempt Lean proof-state features from frozen module rows.

This is Path-A routing substrate, not a solver. It opens each row's
in-place `sorry` file through the persistent Lean REPL, finds the target
proof state, and records cheap visible features from the actual goal.

No proof search, no Codex, no governance claims. The live mode runs one
Lean process sequentially, so it is safe for VPS use when no other heavy
Lean job is active.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).parent))

DEFAULT_CORPUS = "/tmp/rung1/four_arm_frozen_corpus.json"
DEFAULT_OUT = "/tmp/rung1/lean_proofstate_features.jsonl"


def _load_rows(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text())
    rows = data.get("rows") if isinstance(data, dict) else data
    if not isinstance(rows, list):
        raise SystemExit(f"corpus has no rows list: {path}")
    return rows


def _split_goal(goal: str) -> tuple[list[str], str]:
    lines = [ln.rstrip() for ln in goal.splitlines() if ln.strip()]
    target = ""
    ctx: list[str] = []
    for i, line in enumerate(lines):
        if line.lstrip().startswith("⊢"):
            target = line.split("⊢", 1)[1].strip()
            ctx = lines[:i]
            break
    if not target and lines:
        target = lines[-1]
        ctx = lines[:-1]
    return ctx, target


def _type_heads(ctx: list[str]) -> Counter:
    heads: Counter = Counter()
    for line in ctx:
        if ":" not in line:
            continue
        ty = line.split(":", 1)[1].strip()
        m = re.match(r"(?:inst✝*\s*:\s*)?([A-Za-z_][A-Za-z0-9_'.]*)", ty)
        if m:
            heads[m.group(1)] += 1
    return heads


def features_from_goal(goal: str) -> dict[str, Any]:
    ctx, target = _split_goal(goal)
    text = f"{goal}\n{target}".lower()
    hyp_lines = [ln for ln in ctx if ":" in ln]
    type_heads = _type_heads(hyp_lines)
    return {
        "goal_chars": len(goal),
        "target_chars": len(target),
        "ctx_lines": len(ctx),
        "hyp_count": len(hyp_lines),
        "type_head_top": dict(type_heads.most_common(8)),
        "has_forall": int("∀" in goal or "forall" in text),
        "has_exists": int("∃" in goal or "exists" in text),
        "has_implication": int("→" in goal or "->" in goal),
        "has_equality": int("=" in target),
        "has_order": int(any(s in target for s in ("≤", "<", "≥", ">"))),
        "has_sum": int(any(s in text for s in ("finset", "sum", "range", "∑"))),
        "has_tendsto": int("tendsto" in text or "filter" in text),
        "has_integral": int(any(s in text for s in ("integral", "integrable", "mellin", "convolution"))),
        "has_set": int(any(s in text for s in ("set ", "∈", "⊆", "subset", "mem_"))),
        "has_norm": int(any(s in text for s in ("norm", "nnnorm", "abs", "‖"))),
        "has_nat_int": int(any(s in text for s in (" nat", ": nat", " int", ": int", "finset", "range"))),
        "has_real": int(any(s in text for s in (" real", ": real", "ℝ", "ennreal", "nnreal"))),
        "binder_like_count": len(re.findall(r"\b[A-Za-z_][A-Za-z0-9_']*\s*:", "\n".join(hyp_lines))),
        "arrow_count": goal.count("→") + goal.count("->"),
        "target_token_count": len(re.findall(r"[A-Za-z_][A-Za-z0-9_'.]*|[∀∃=≤≥<>→∧∨¬]", target)),
    }


def _target_sorry(opened: dict[str, Any], target_line: int) -> dict[str, Any] | None:
    sorries = opened.get("sorries") or []
    return next((s for s in sorries
                 if s.get("line") and abs(int(s["line"]) - target_line) <= 3), None)


def extract(corpus: Path, out: Path, sandbox: Path | None,
            limit: int, timeout: int) -> dict[str, Any]:
    import coherent_rung1 as cr
    from src.ztare.formal.lean_persistent import PersistentLean

    rows = _load_rows(corpus)
    if limit:
        rows = rows[:limit]
    sb = sandbox or cr.SB
    out.parent.mkdir(parents=True, exist_ok=True)
    summary = Counter()
    t0 = time.time()
    with PersistentLean(sb) as L, out.open("w") as fh:
        for row in rows:
            rr: dict[str, Any] = {
                "row_id": row.get("id"),
                "target_name": row.get("target_name"),
                "target_line": row.get("target_line"),
                "source": row.get("sorried_file"),
            }
            t_row = time.time()
            opened = L.open_file(str(row["sorried_file"]), timeout=timeout)
            rr["open_ok"] = bool(opened.get("ok"))
            rr["open_s"] = round(time.time() - t_row, 2)
            if not opened.get("ok"):
                rr["status"] = "open_failed"
                rr["err"] = opened.get("err")
                summary["open_failed"] += 1
            else:
                tgt = _target_sorry(opened, int(row.get("target_line") or 0))
                if not tgt:
                    rr["status"] = "target_sorry_not_found"
                    summary["target_sorry_not_found"] += 1
                else:
                    goal = str(tgt.get("goal") or "")
                    rr["status"] = "ok"
                    rr["proof_state"] = tgt.get("proofState")
                    rr["goal_preview"] = goal[:300]
                    rr["features"] = features_from_goal(goal)
                    summary["ok"] += 1
            fh.write(json.dumps(rr, sort_keys=True) + "\n")
            fh.flush()
            print(json.dumps({
                "row_id": rr["row_id"],
                "status": rr["status"],
                "open_s": rr["open_s"],
            }, sort_keys=True), flush=True)
    return {
        "corpus": str(corpus),
        "out": str(out),
        "sandbox": str(sb),
        "n": len(rows),
        "counts": dict(summary),
        "secs": round(time.time() - t0, 2),
    }


def self_test() -> int:
    goal = """α : Type u_1
inst✝ : TopologicalSpace α
f : ℕ → α
h : Tendsto f atTop (𝓝 x)
⊢ ∀ n, f n = x → n ≤ n
"""
    feats = features_from_goal(goal)
    assert feats["hyp_count"] == 4
    assert feats["has_forall"] == 1
    assert feats["has_tendsto"] == 1
    assert feats["has_order"] == 1
    assert feats["has_equality"] == 1
    print("lean_proofstate_feature_extract self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=DEFAULT_CORPUS)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--sandbox")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    summary = extract(Path(args.corpus), Path(args.out),
                      Path(args.sandbox).expanduser().resolve()
                      if args.sandbox else None,
                      args.limit, args.timeout)
    print(json.dumps(summary, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
