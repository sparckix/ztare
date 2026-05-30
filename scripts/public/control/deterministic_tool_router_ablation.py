#!/usr/bin/env python3
"""deterministic_tool_router_ablation.py — cheap Path-A mechanism test.

Question: does a non-oracle live proof-state router beat a fixed static
tool order when Codex/LLM prompting is removed?

Both arms use the SAME:
  - rows
  - tactic/tool vocabulary
  - PersistentLean proof-state stepping primitive
  - authoritative_axioms.govern closure gate
  - budget / max steps / depth / beam cap

Only difference:
  fixed  : one global static tactic order.
  router : reorders the same module-safe tactics from the current live
           goal text and prior failed tactics. It does NOT use
           gold_n_steps.

This is Test 1 from the post-decider Meta-Darwin plan. It is not a new
SOTA claim; it is a cheap discriminator for whether Path A has a
mechanical tool-orchestration core worth scaling.
"""
from __future__ import annotations

import argparse
import hashlib
import heapq
import json
import os
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).parent))

FROZEN = "/tmp/rung1/four_arm_frozen_corpus.json"
CKPT = "/tmp/rung1/deterministic_router_ablation_ckpt.jsonl"
SUMMARY = "/tmp/rung1/deterministic_router_ablation_summary.json"
TRACE_ROOT = "/tmp/rung1/deterministic_router_ablation_traces"
TOOL_PRELUDE = "import Mathlib\nopen scoped ENNReal NNReal BigOperators"
# Hammer/Duper/Auto are intentionally NOT included here: importing them
# into Mathlib module-source rows imports broad Mathlib state and breaks
# or leaks the row environment. They need a separate backend adapter.
EXTRA_IMPORTS: list[str] = []

# The shared vocabulary. The arms may reorder it, but neither arm gets
# a private tool. Keep expensive/global tactics late by default.
TOOLS = [
    "rfl", "assumption", "contradiction",
    "simp_all", "simp", "norm_num",
    "exact?", "aesop", "solve_by_elim",
    "omega", "linarith", "nlinarith", "positivity", "gcongr",
    "ring", "ring_nf", "field_simp",
    "constructor", "intro _", "rcases ‹_› with ⟨⟩",
]

STATIC_ORDER = [
    "simp_all", "simp", "aesop", "exact?",
    "linarith", "nlinarith", "omega",
    "ring", "ring_nf", "norm_num", "field_simp",
    "rfl", "assumption", "constructor", "intro _",
    "solve_by_elim", "positivity", "gcongr",
    "contradiction", "rcases ‹_› with ⟨⟩",
]


def die(msg: str) -> None:
    print(f"FAIL-LOUD: {msg}", file=sys.stderr)
    raise SystemExit(2)


def _safe_id(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", str(s))


def _goal_hash(goals: list[str]) -> str:
    return hashlib.sha1("\u241e".join(g.strip() for g in goals)
                        .encode()).hexdigest()


def _dedupe_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in items:
        if x in TOOLS and x not in seen:
            seen.add(x)
            out.append(x)
    for x in TOOLS:
        if x not in seen:
            out.append(x)
    return out


def router_order(goals: list[str], failed: set[str] | None = None) -> list[str]:
    """Non-oracle heuristic over the live goal text. No gold proof
    length, no source proof, no Codex. This is intentionally small:
    enough to test whether deterministic ordering has signal."""
    failed = failed or set()
    g = "\n".join(goals)
    lo = g.lower()
    seed: list[str] = ["rfl", "assumption", "contradiction", "exact?"]

    has_num = bool(re.search(r"\b(nat|int|rat|real|nnreal|ennreal)\b", lo))
    has_arith = any(s in g for s in ("≤", "<", "≥", ">", "+", "-", "*", "^", "/"))
    has_eq = "=" in g
    has_logic = any(s in g for s in ("∧", "∨", "¬", "↔", "∃", "∀"))
    has_sum = any(s in lo for s in ("finset", "sum", "tsum", "summable", "has_sum"))
    has_analysis = any(s in lo for s in (
        "integral", "measure", "tendsto", "filter", "continuous",
        "differentiable", "convolution", "mellin", "lp", "norm"))

    if has_logic:
        seed += ["tauto", "aesop", "constructor", "intro _", "simp_all"]
    if has_num:
        seed += ["norm_num", "omega"]
    if has_arith:
        seed += ["nlinarith", "linarith", "positivity", "gcongr"]
    if has_eq:
        seed += ["simp_all", "simp", "ring_nf", "ring", "field_simp"]
    if has_sum or has_analysis:
        seed += ["simp_all", "aesop", "field_simp"]

    # If a class already failed at this state lineage, bias away from it
    # without deleting it completely; later fallback can still try it.
    seed = [x for x in seed if x not in failed] + [
        x for x in STATIC_ORDER if x not in failed]
    return _dedupe_order(seed)


def static_order(goals: list[str], failed: set[str] | None = None) -> list[str]:
    failed = failed or set()
    return _dedupe_order([x for x in STATIC_ORDER if x not in failed])


def _with_tool_imports(src: str, target_line: int) -> tuple[str, int]:
    """open_file(path) elaborates the file's own imports, not the REPL
    prelude. Add tool imports to the row copy and return the target-line
    delta for replay/governance. This is a per-experiment copy only; the
    source corpus is never mutated."""
    lines = src.splitlines()
    existing = {ln.strip() for ln in lines}
    missing = [imp for imp in EXTRA_IMPORTS if imp not in existing]
    if not missing:
        return src, 0
    module_idx = next((i for i, ln in enumerate(lines)
                       if ln.strip() == "module"), None)
    insert = (module_idx + 1) if module_idx is not None else 0
    j = insert
    last_import = None
    while j < len(lines):
        stripped = lines[j].strip()
        if stripped == "":
            j += 1
            continue
        if re.match(r"^(?:public\s+)?import\s+", stripped):
            last_import = j
            j += 1
            continue
        break
    if last_import is not None:
        insert = last_import + 1
    lines[insert:insert] = missing
    delta = len(missing) if target_line > insert else 0
    return "\n".join(lines) + ("\n" if src.endswith("\n") else ""), delta


def _tool_row_file(row: dict, trace_dir: Path) -> tuple[Path, int]:
    src = Path(row["sorried_file"]).read_text(errors="ignore")
    full, delta = _with_tool_imports(src, row["target_line"])
    p = trace_dir / "row_with_tools.lean"
    p.write_text(full)
    return p, row["target_line"] + delta


def _target_sorry_state(L: Any, row: dict, row_file: Path,
                        target_line: int, open_timeout: int) -> dict:
    of = L.open_file(str(row_file), timeout=open_timeout)
    if not of.get("ok"):
        return {"ok": False, "err": of.get("err") or "open_file_failed"}
    tl = target_line
    tgt = next((s for s in of.get("sorries", [])
                if s.get("line") and abs(s["line"] - tl) <= 3), None)
    if not tgt or tgt.get("proofState") is None:
        return {"ok": False, "err": "target_sorry_not_found"}
    return {"ok": True, "ps": tgt["proofState"],
            "goal": tgt.get("goal", ""), "open_errors": of.get("errors", [])}


def search(L: Any, row: dict, arm: str, order_fn,
           max_seconds: float, max_steps: int, max_depth: int,
           beam: int, step_timeout: int, open_timeout: int,
           trace_dir: Path) -> dict:
    trace_dir.mkdir(parents=True, exist_ok=True)
    row_file, adjusted_target_line = _tool_row_file(row, trace_dir)
    t_open = time.time()
    st = _target_sorry_state(L, row, row_file, adjusted_target_line,
                             open_timeout)
    open_s = round(time.time() - t_open, 3)
    if not st.get("ok"):
        return {"status": "open_failed", "reason": st.get("err"),
                "path": [], "steps": 0, "failed_calls": 0,
                "open_s": open_s, "search_s": 0.0,
                "trace_dir": str(trace_dir),
                "row_file": str(row_file),
                "adjusted_target_line": adjusted_target_line}

    t0 = time.time()
    ps0 = st["ps"]
    goal0 = st.get("goal", "")
    frontier: list = [(1, 0, 0, ps0, [goal0], [], set())]
    seen = {_goal_hash([goal0])}
    tie = 0
    steps = 0
    failed_calls = 0
    events: list[dict] = []
    while frontier and steps < max_steps and (time.time() - t0) < max_seconds:
        _ngoals, depth, _tie, ps, goals, path, failed = heapq.heappop(frontier)
        if depth >= max_depth:
            continue
        for tac in order_fn(goals, failed):
            if steps >= max_steps or (time.time() - t0) >= max_seconds:
                break
            steps += 1
            r = L.step(ps, tac, timeout=step_timeout)
            ev = {"step": steps, "depth": depth + 1,
                  "path": path, "tactic": tac,
                  "ok": bool(r.get("ok")),
                  "closed": bool(r.get("closed")),
                  "err": (r.get("err") or "")[:240],
                  "n_goals": len(r.get("goals") or [])}
            events.append(ev)
            if not r.get("ok"):
                failed_calls += 1
                if r.get("err") == "timeout_or_crash":
                    (trace_dir / "events.jsonl").write_text(
                        "\n".join(json.dumps(e) for e in events) + "\n")
                    return {"status": "tool_timeout", "reason": tac,
                            "path": path, "steps": steps,
                            "failed_calls": failed_calls,
                            "open_s": open_s,
                            "search_s": round(time.time() - t0, 3),
                            "trace_dir": str(trace_dir),
                            "row_file": str(row_file),
                            "adjusted_target_line": adjusted_target_line}
                continue
            npath = path + [tac]
            if r.get("closed"):
                (trace_dir / "events.jsonl").write_text(
                    "\n".join(json.dumps(e) for e in events) + "\n")
                return {"status": "candidate_closed", "reason": "closed",
                        "path": npath, "steps": steps,
                        "failed_calls": failed_calls,
                        "open_s": open_s,
                        "search_s": round(time.time() - t0, 3),
                        "trace_dir": str(trace_dir),
                        "row_file": str(row_file),
                        "adjusted_target_line": adjusted_target_line}
            ngoals = r.get("goals") or []
            gh = _goal_hash(ngoals)
            if gh in seen:
                continue
            seen.add(gh)
            tie += 1
            heapq.heappush(frontier, (
                len(ngoals), depth + 1, tie, r.get("ps"),
                ngoals, npath, set()))
            if len(frontier) > beam * 4:
                frontier = heapq.nsmallest(beam, frontier)
                heapq.heapify(frontier)
    (trace_dir / "events.jsonl").write_text(
        "\n".join(json.dumps(e) for e in events) + ("\n" if events else ""))
    return {"status": "exhausted_or_budget", "reason": "no_close",
            "path": [], "steps": steps, "failed_calls": failed_calls,
            "open_s": open_s, "search_s": round(time.time() - t0, 3),
            "trace_dir": str(trace_dir),
            "row_file": str(row_file),
            "adjusted_target_line": adjusted_target_line}


def _replace_target_sorry(src: str, target_line: int, path: list[str]) -> str:
    lines = src.splitlines()
    if not path:
        return src
    start = max(0, target_line - 6)
    stop = min(len(lines), target_line + 12)
    proof = path
    for i in range(start, stop):
        ln = lines[i]
        if "sorry" not in ln:
            continue
        if re.search(r":=\s*by\s+sorry\b", ln):
            indent = re.match(r"^(\s*)", ln).group(1)
            lines[i] = re.sub(r":=\s*by\s+sorry\b", ":= by", ln)
            lines[i:i + 1] = [lines[i]] + [indent + "  " + t for t in proof]
            return "\n".join(lines) + "\n"
        if re.match(r"^\s*sorry\b", ln):
            indent = re.match(r"^(\s*)", ln).group(1)
            lines[i:i + 1] = [indent + t for t in proof]
            return "\n".join(lines) + "\n"
    raise ValueError("target sorry line not found for replay")


def govern_candidate(L: Any, row: dict, path: list[str],
                     timeout: int, persist: bool = True) -> dict:
    import authoritative_axioms as _AX
    try:
        src = Path(row["sorried_file"]).read_text(errors="ignore")
        src, delta = _with_tool_imports(src, row["target_line"])
        target_line = row["target_line"] + delta
        full = _replace_target_sorry(src, target_line, path)
    except Exception as e:  # noqa: BLE001
        return {"verdict": "unverified", "reason": f"replay_build_failed:{e}",
                "verified_by": "deterministic_router_ablation"}
    return _AX.govern(L, full, target_line, row["target_name"],
                      timeout=timeout, persist=persist)


def run_arm(L: Any, row: dict, arm: str, args) -> dict:
    order_fn = router_order if arm == "router" else static_order
    rec = search(L, row, arm, order_fn, args.budget, args.max_steps,
                 args.max_depth, args.beam, args.step_timeout,
                 args.open_timeout,
                 Path(args.trace_root) / _safe_id(row["id"]) / arm)
    if rec["status"] == "candidate_closed":
        g = govern_candidate(L, row, rec["path"], args.govern_timeout,
                             persist=not args.no_persist)
        rec["gate"] = g
        rec["verdict"] = g.get("verdict")
        rec["reason"] = g.get("reason")
    else:
        rec["gate"] = None
        rec["verdict"] = "open"
    rec["ratified"] = 1 if rec.get("verdict") == "closure" else 0
    rec["axiom_smuggled"] = 1 if rec.get("verdict") == "axiom_smuggled" else 0
    rec["exact_gap"] = 0
    return rec


def _load_rows(corpus: str, limit: int, offset: int) -> list[dict]:
    p = Path(corpus)
    if not p.exists():
        die(f"corpus missing: {corpus}")
    data = json.loads(p.read_text())
    rows = data["rows"] if isinstance(data, dict) else data
    rows = rows[offset:]
    if limit:
        rows = rows[:limit]
    if not rows:
        die("no rows after offset/limit")
    return rows


def summarize(rows: list[dict], out_path: str) -> dict:
    n = len(rows)

    def s(arm: str, key: str) -> int:
        return sum(r.get(arm, {}).get(key, 0) for r in rows)

    def med_open(arm: str, key: str) -> float:
        vals = sorted(r.get(arm, {}).get(key, 0) for r in rows
                      if not r.get(arm, {}).get("ratified", 0))
        return vals[len(vals) // 2] if vals else 0

    fixed = s("fixed", "ratified")
    router = s("router", "ratified")
    fixed_med_failed = med_open("fixed", "failed_calls")
    router_med_failed = med_open("router", "failed_calls")
    reduction = (fixed_med_failed / router_med_failed
                 if router_med_failed else 0)
    delta = (router - fixed) / n if n else 0
    safe = s("router", "axiom_smuggled") == 0
    passed = n >= 8 and safe and (delta >= 0.20 or reduction >= 2.0)
    out = {
        "n": n,
        "fixed_ratified": fixed,
        "router_ratified": router,
        "fixed_rate": round(fixed / n, 3) if n else 0,
        "router_rate": round(router / n, 3) if n else 0,
        "router_minus_fixed": round(delta, 3),
        "router_axiom_smuggled": s("router", "axiom_smuggled"),
        "fixed_median_failed_calls_open": fixed_med_failed,
        "router_median_failed_calls_open": router_med_failed,
        "failed_call_reduction_fixed_over_router": round(reduction, 2),
        "exact_gap_scored": False,
        "PASS_predicate": "n>=8 and router false-ratify=0 and "
        "(router-fixed >=0.20 or >=2x failed-call reduction on opens)",
        "VERDICT": "PASS" if passed else
        "FAIL/INCONCLUSIVE (honest — NOT relaxed)",
    }
    Path(out_path).write_text(json.dumps(out, indent=1))
    return out


def run(args) -> dict:
    import coherent_rung1 as cr
    from src.ztare.formal.lean_persistent import PersistentLean

    os.environ["ZTARE_GATE_RUN_ID"] = args.run_id
    os.environ["ZTARE_GATE_SOURCE"] = "deterministic_tool_router_ablation"
    rows = _load_rows(args.corpus, args.limit, args.offset)
    row_ids = {r["id"] for r in rows}
    ckpt = Path(args.ckpt)
    done: dict[str, dict] = {}
    if ckpt.exists():
        for ln in ckpt.read_text().splitlines():
            try:
                d = json.loads(ln)
                if d.get("id") in row_ids:
                    done[d["id"]] = d
            except Exception:
                pass
    todo = [r for r in rows if r["id"] not in done]
    print(f"[router-ablation] rows={len(rows)} todo={len(todo)} "
          f"offset={args.offset} limit={args.limit} budget={args.budget}s")
    L = PersistentLean(cr.SB, prelude=TOOL_PRELUDE, import_timeout=600)
    L.start_tactic_proof("theorem _w : True := by sorry", 180)
    fh = ckpt.open("a")
    try:
        for row in todo:
            rec = {"id": row["id"], "target_name": row.get("target_name")}
            # Independent starts: each arm re-opens the source file from the
            # same initial sorry proof state. fixed first, router second.
            rec["fixed"] = run_arm(L, row, "fixed", args)
            rec["router"] = run_arm(L, row, "router", args)
            fh.write(json.dumps(rec) + "\n")
            fh.flush()
            done[rec["id"]] = rec
            print(json.dumps({
                "id": rec["id"],
                "fixed": rec["fixed"]["verdict"],
                "router": rec["router"]["verdict"],
                "fixed_steps": rec["fixed"]["steps"],
                "router_steps": rec["router"]["steps"],
            }))
    finally:
        fh.close()
        L.close()
    out = summarize(list(done.values()), args.summary)
    print("\n=== DETERMINISTIC ROUTER ABLATION ===")
    print(json.dumps(out, indent=1))
    print("ROW TABLE:", ckpt)
    return out


def _self_test() -> int:
    import authoritative_axioms as _AX
    _AX.isolate_selftest_ledger()
    td = Path(tempfile.mkdtemp())
    src = td / "r.lean"
    src.write_text("import Mathlib\n\ntheorem t : True := by\n  sorry\n")
    row = {"id": "r", "sorried_file": str(src), "target_line": 3,
           "target_name": "t"}

    class MockL:
        def open_file(self, path, timeout=60):
            return {"ok": True, "errors": [], "sorries": [{
                "proofState": 1, "line": 4, "column": 2,
                "goal": "⊢ True"}], "messages": []}

        def step(self, ps, tactic, timeout=60):
            if tactic == "exact?":
                return {"ok": True, "closed": True, "ps": 2,
                        "goals": [], "err": ""}
            return {"ok": False, "closed": False, "ps": ps,
                    "goals": [], "err": "no progress"}

        def close(self):
            pass

    L = MockL()
    r = search(L, row, "router", router_order, 20, 20, 3, 4, 1, 1,
               td / "trace")
    assert r["status"] == "candidate_closed", r
    assert r["path"] == ["rfl"] or "exact?" in r["path"], r
    full = _replace_target_sorry(src.read_text(), 3, ["trivial"])
    assert "sorry" not in full and "trivial" in full, full
    rows = [{"fixed": {"ratified": 0, "failed_calls": 8,
                       "axiom_smuggled": 0},
             "router": {"ratified": 1, "failed_calls": 2,
                        "axiom_smuggled": 0}}
            for _ in range(8)]
    out = summarize(rows, str(td / "summary.json"))
    assert out["VERDICT"] == "PASS", out
    mod_src = "/- c -/\nmodule\n\npublic import Mathlib\n\ntheorem u : True := by\n  sorry\n"
    mod_full, mod_delta = _with_tool_imports(mod_src, 6)
    assert mod_full == mod_src and mod_delta == 0, (mod_delta, mod_full)
    shutil.rmtree(td, ignore_errors=True)
    print("[self-test] deterministic_tool_router_ablation: search, "
          "target-sorry replay, and predicate PASS/FAIL wiring OK. "
          "NO Lean/codex.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=FROZEN)
    ap.add_argument("--ckpt", default=CKPT)
    ap.add_argument("--summary", default=SUMMARY)
    ap.add_argument("--trace-root", default=TRACE_ROOT)
    ap.add_argument("--run-id", default="deterministic_router_ablation")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--budget", type=float, default=120.0)
    ap.add_argument("--max-steps", type=int, default=120)
    ap.add_argument("--max-depth", type=int, default=4)
    ap.add_argument("--beam", type=int, default=8)
    ap.add_argument("--step-timeout", type=int, default=20)
    ap.add_argument("--open-timeout", type=int, default=600)
    ap.add_argument("--govern-timeout", type=int, default=220)
    ap.add_argument("--no-persist", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    return 0 if run(args) else 1


if __name__ == "__main__":
    raise SystemExit(main())
