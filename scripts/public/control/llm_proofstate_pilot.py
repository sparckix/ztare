#!/usr/bin/env python3
"""llm_proofstate_pilot.py — base-rate-gated paired pilot (cold-spec).

Tests the ONE question, minimally and cleanly: does an LLM searching
over LIVE Lean proof states beat the SAME LLM generating a whole proof
blind, at equal wall-clock — on leak-tight multi-step Mathlib goals.

Design (per cold review epd-db0a29d142bb), confound-controlled:
  * SAME model both arms (gpt-4.1 via the canonical LLMRuntime).
  * SAME leak-tight context: each row is the target's real source file
    with its proof replaced by `sorry` (true module context, target
    NOT registered) — built by build_module_context_benchmark.py.
  * STATEFUL arm: open the sorried file → real proofState; beam search
    where the LLM proposes k next-tactics CONDITIONED ON THE LIVE GOAL;
    each candidate elaborated by the warm REPL.
  * BLIND arm: SAME model, given ONLY the initial theorem/goal text
    (no proof state, NO compiler/repair feedback — else it is a third
    arm); returns one whole `by` block; substituted for the `sorry`
    and compiled ONCE in the real file context. Pass = clean compile.
  * Kernel is the trust boundary (ban sorry/admit/new imports; final
    elaboration by Lean). Serial + checkpointed + ONE warm REPL +
    light API calls → safe for the local machine (the crash was
    parallel heavy Lean; this is not that).

Base-rate gate (30-theorem pilot, cold-spec): proceed to N=100 only if
union-solve ∈ [20%,80%] and discordance ≥ 4; NOT "both arms nonzero"
(stateful>0, blind=0 is a large effect, not a floor).
"""
from __future__ import annotations

import argparse
import hashlib
import heapq
import json
import re
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
from src.ztare.formal.lean_persistent import PersistentLean  # noqa: E402
from src.ztare.common.llm_runtime import (  # noqa: E402
    LLMRuntime, resolve_model_id)

BANNED = ("sorry", "admit", "stop", "native_decide", "import ", "axiom ")
SYS_TACTIC = (
    "You are a Lean 4 / Mathlib proof expert. You will be given the "
    "CURRENT proof state (hypotheses + goal). Propose the {k} most "
    "promising DISTINCT next tactics. Output ONLY a JSON array of "
    "tactic strings, most-promising first. No prose. Each item is one "
    "Lean 4 tactic (may use <;>, [], etc.). No `sorry`/`admit`.")
SYS_WHOLE = (
    "You are a Lean 4 / Mathlib proof expert. Given a theorem's "
    "hypotheses and goal, output ONE complete tactic proof body that "
    "would replace `by` — i.e. a sequence of Lean 4 tactics. Output "
    "ONLY the tactic block, no `by`, no theorem header, no prose, no "
    "code fences. No `sorry`/`admit`/new imports.")


def _gh(goals): return hashlib.sha1(
    "␞".join(g.strip() for g in goals).encode()).hexdigest()


def _llm(rt, model_id, prompt, max_tokens=900, timeout=90):
    r = rt.call_text(prompt, model_id=model_id, max_tokens=max_tokens,
                      timeout_seconds=timeout, retries=2,
                      request_label="pilot")
    return getattr(r, "text", str(r)) or ""


def _parse_tactics(txt, k):
    m = re.search(r"\[.*\]", txt, re.S)
    if m:
        try:
            arr = json.loads(m.group(0))
            out = [str(t).strip() for t in arr if str(t).strip()]
            return [t for t in out
                    if not any(b in t for b in BANNED)][:k]
        except Exception:
            pass
    # fallback: one tactic per line
    out = [ln.strip(" -*`") for ln in txt.splitlines() if ln.strip()]
    return [t for t in out if not any(b in t for b in BANNED)][:k]


def stateful(L, rt, mid, row, k, beam, max_depth, budget):
    t_open = time.time()
    of = L.open_file(row["sorried_file"], timeout=600)
    if not of["ok"]:
        return {"status": "open_failed", "solved": False,
                "open_s": round(time.time() - t_open, 1)}
    tl = row["target_line"]
    tgt = next((s for s in of["sorries"]
                if s["line"] and abs(s["line"] - tl) <= 3), None)
    if not tgt or tgt["proofState"] is None:
        return {"status": "open_failed", "solved": False,
                "open_s": round(time.time() - t_open, 1)}
    open_s = round(time.time() - t_open, 1)
    t0 = time.time()
    ps0, g0 = tgt["proofState"], tgt["goal"]
    seen = {_gh([g0])}
    fr = [(1, 0, 0, ps0, [g0], [])]
    tie = calls = 0
    while fr and (time.time() - t0) < budget:
        _, depth, _, ps, goals, path = heapq.heappop(fr)
        if depth >= max_depth:
            continue
        prompt = (f"{SYS_TACTIC.format(k=k)}\n\n## Proof state\n"
                  f"{goals[0]}\n\n## Tactics so far\n{path}")
        calls += 1
        cands = _parse_tactics(_llm(rt, mid, prompt), k)
        for tac in cands:
            if (time.time() - t0) >= budget:
                break
            r = L.step(ps, tac, timeout=20)
            if not r["ok"]:
                continue
            if r["closed"]:
                return {"status": "solved", "solved": True,
                        "path": path + [tac], "calls": calls,
                        "open_s": open_s,
                        "search_s": round(time.time() - t0, 1)}
            h = _gh(r["goals"])
            if h in seen:
                continue
            seen.add(h)
            tie += 1
            heapq.heappush(fr, (len(r["goals"]), depth + 1, tie,
                                r["ps"], r["goals"], path + [tac]))
            if len(fr) > beam * 4:
                fr = heapq.nsmallest(beam, fr)
                heapq.heapify(fr)
    return {"status": "exhausted", "solved": False, "calls": calls,
            "open_s": open_s, "search_s": round(time.time() - t0, 1)}


def blind(L, rt, mid, row):
    """SAME model, ONLY the goal text, ONE whole-proof attempt, NO
    state/repair. Verified by substituting the block for the `sorry`
    in the real leak-tight file and compiling once."""
    t0 = time.time()
    src = Path(row["sorried_file"]).read_text(encoding="utf-8",
                                              errors="ignore")
    prompt = (f"{SYS_WHOLE}\n\n## Theorem (goal in real context)\n"
              f"{row.get('goal','')}\n")
    block = _llm(rt, mid, prompt, max_tokens=1200).strip()
    block = re.sub(r"^```\w*|```$", "", block, flags=re.M).strip()
    if not block or any(b in block for b in BANNED):
        return {"status": "blind_bad_output", "solved": False,
                "secs": round(time.time() - t0, 1)}
    # replace the injected `:= by\n  sorry` with the candidate block
    new = re.sub(r":=\s*by\s*\n\s*sorry",
                 ":= by\n  " + block.replace("\n", "\n  "),
                 src, count=1)
    tf = Path(row["sorried_file"] + ".blind.lean")
    tf.write_text(new, encoding="utf-8")
    of = L.open_file(str(tf), timeout=600)
    tf.unlink(missing_ok=True)
    if not of["ok"]:
        return {"status": "blind_compile_err", "solved": False,
                "secs": round(time.time() - t0, 1)}
    tl = row["target_line"]
    # solved iff NO error on/after target line AND no leftover sorry
    bad = [m for m in of.get("errors", [])]
    leftover = [s for s in of["sorries"]
                if s["line"] and abs(s["line"] - tl) <= 3]
    solved = (not bad) and (not leftover)
    return {"status": "solved" if solved else "blind_fail",
            "solved": solved, "secs": round(time.time() - t0, 1)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sandbox", required=True)
    ap.add_argument("--corpus", default="/tmp/rung1/mcb_corpus_v2.json")
    ap.add_argument("--n", type=int, default=30)
    # FRONTIER model REQUIRED — proving is generation+search where
    # model strength dominates. gpt-4.1 is the JUDGE model (bounded
    # grading) and was shown weak at SOLVING here; using it would
    # re-floor the pilot (predictable null = the recurring wrong-
    # instrument trap). Default = claude-opus (what produced genuine
    # proofs in this project); SAME model drives both arms so the
    # state-vs-blind comparison stays controlled.
    ap.add_argument("--model", default="claude-opus")
    ap.add_argument("--k", type=int, default=6)
    ap.add_argument("--beam", type=int, default=8)
    ap.add_argument("--max-depth", type=int, default=12)
    ap.add_argument("--budget", type=float, default=60.0)
    ap.add_argument("--ckpt", default="/tmp/rung1/pilot_ckpt.jsonl")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    rows = json.load(open(a.corpus))["rows"]
    # stratify by gold_n_steps so the pilot is graded, not all-hard
    rows.sort(key=lambda r: r.get("gold_n_steps", 99))
    if len(rows) > a.n:
        step = len(rows) / a.n
        rows = [rows[int(i * step)] for i in range(a.n)]
    if a.limit:
        rows = rows[: a.limit]

    done = {}
    ck = Path(a.ckpt)
    if ck.exists():
        for ln in ck.read_text().splitlines():
            try:
                d = json.loads(ln)
                done[d["id"]] = d
            except Exception:
                pass
    sb = Path(a.sandbox).expanduser().resolve()
    L = PersistentLean(sb)
    rt = LLMRuntime()
    mid = resolve_model_id(a.model)
    L.start_tactic_proof("theorem _w : True := by sorry", 180)

    fh = ck.open("a")
    for row in rows:
        rid = row["id"]
        if rid in done:
            continue
        s = stateful(L, rt, mid, row, a.k, a.beam, a.max_depth, a.budget)
        b = blind(L, rt, mid, row)
        rec = {"id": rid, "gold_steps": row.get("gold_n_steps"),
               "stateful_solved": s["solved"], "stateful": s,
               "blind_solved": b["solved"], "blind": b}
        fh.write(json.dumps(rec) + "\n")
        fh.flush()
        done[rid] = rec
        print(json.dumps({"id": rid, "gs": row.get("gold_n_steps"),
                          "S": s["solved"], "B": b["solved"],
                          "s_status": s["status"],
                          "b_status": b["status"]}))
    fh.close()
    L.close()

    R = list(done.values())
    n = len(R)
    S = sum(1 for r in R if r["stateful_solved"])
    B = sum(1 for r in R if r["blind_solved"])
    U = sum(1 for r in R if r["stateful_solved"] or r["blind_solved"])
    n10 = sum(1 for r in R if r["stateful_solved"]
              and not r["blind_solved"])
    n01 = sum(1 for r in R if r["blind_solved"]
              and not r["stateful_solved"])
    disc = n10 + n01
    ur = U / n if n else 0
    gate = (0.20 <= ur <= 0.80) and disc >= 4
    summary = {"n": n, "stateful_solved": S, "blind_solved": B,
               "union": U, "union_rate": round(ur, 3),
               "discordant": disc, "n10_S_only": n10,
               "n01_B_only": n01,
               "base_rate_gate": "PASS" if gate else "FAIL",
               "interpretation": (
                   "proceed to N=100 paired test" if gate else
                   ("both-zero/saturated or too-few discordant — "
                    "fix design before scaling (NOT a proof-state "
                    "verdict)"))}
    print("\n" + json.dumps(summary, indent=1))
    Path("/tmp/rung1/pilot_summary.json").write_text(
        json.dumps({"summary": summary, "rows": R}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
