#!/usr/bin/env python3
"""AlphaProof-shaped proof search — best-of-N × beam × compiler-feedback iteration.

The fair one-shot matrix showed providers land ONE goal short on leak-clean APN rows
(0/7) and crude single-shot refinement degrades. The paper closes these with a real
SEARCH harness, not one shot. This is that harness:

  round 0:  best-of-N — sample N diverse proof attempts (varied strategy hints,
            optionally across providers); compile + score each by the proof-state
            gradient (closed > fewer-goals-left > progress). Keep the top-B beam.
  round k:  for each beam node, feed back its EXACT unsolved-goal state + working
            proof, sample N refinements/continuations; compile + score; the beam is
            the top-B of (old ∪ new) — MONOTONE (never keeps a worse node than it had,
            which is why a crude blind-regenerate loop degraded and this does not).
  stop:     a kernel-clean + matched-negative-control ratified closure, or budget.

The proof-state gradient (`proof_state_signal`) is the value function; the residual
extractor (`extract_unsolved_goals`) carries the feedback. Closures are credit-gated by
the canonical `_validate_against_contract` (kernel + MNC). Context is the SELF-CONTAINED
materialized goal (leak-clean — no `_build_solver_context` prelude). Run on the VPS.

Usage: proof_search.py --slice <materialized.jsonl> [--rows P2,..] --providers claude_opus
   [--n 6] [--beam 3] [--rounds 3] [--timeout 400] --out-db <db> [--dry-run]
"""
from __future__ import annotations
import argparse, json, sqlite3, sys, time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(REPO / "src"))

from ztare.leanmill.solver.proof_state import proof_state_signal, extract_unsolved_goals  # noqa: E402
import provider_registry as reg  # noqa: E402

# Diverse strategy hints → genuine sample diversity (a single fixed prompt gives N
# near-identical proofs). Each sample i uses STRATEGIES[i % len].
STRATEGIES = [
    "Prove it directly; unfold the definitions and close with simp/aesop/omega/decide as appropriate.",
    "Use induction where a natural recursion/structure exists; close base and step.",
    "Introduce auxiliary facts as `have` steps first, then assemble them into the goal.",
    "Split with rcases/obtain/by_cases into subcases and close each branch separately.",
    "Construct the required witness(es) explicitly, then discharge the remaining side-conditions.",
    "Reduce the goal to a known Mathlib lemma; find the lemma whose conclusion matches and apply it.",
]


def _conn(db: Path) -> sqlite3.Connection:
    con = sqlite3.connect(str(db))
    con.execute("""CREATE TABLE IF NOT EXISTS search (
        row_id TEXT, closed INTEGER, mnc INTEGER, rounds_used INTEGER, samples_used INTEGER,
        best_goals_remaining INTEGER, best_progress REAL, proof_text TEXT, attempt_at TEXT)""")
    return con


def _strip(text: str) -> str:
    t = (text or "").strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t
        if t.endswith("```"):
            t = t[:-3]
        t = t.strip()
    return t[3:].lstrip() if t.startswith("by ") or t == "by" else t


def _gen(provider, goal, prior, residual, strategy, timeout_s) -> str:
    if prior is None:
        prompt = (f"Prove this Lean theorem. Strategy hint: {strategy}\n"
                  f"Reply with ONLY the proof body after `by` (no `theorem`/`by`):\n{goal}")
    else:
        prompt = (f"Lean theorem:\n{goal}\n\nYour proof body so far (after `by`):\n{prior}\n\n"
                  f"The compiler leaves these goals UNSOLVED:\n{residual}\n\n"
                  f"Strategy hint: {strategy}\nProduce a CORRECTED, COMPLETE proof body that closes "
                  f"ALL goals (keep the working prefix). Reply with ONLY the proof body.")
    try:
        return _strip(reg.invoke(provider, goal_text=prompt, timeout_s=timeout_s).get("proof_text", ""))
    except Exception:
        return ""


def search(row, providers, n, beam_w, rounds, timeout_s, lean_root, con) -> dict:
    from solver_lane_worker import (_verify_compile, _validate_against_contract,  # noqa: E402
                                     _build_solver_action_contract)
    rid = row.get("row_id", "anon"); tgt = row.get("target_theorem_name") or ""
    goal = (row.get("goal") or "").strip()
    samples_used = 0

    def evaluate(body):
        nonlocal samples_used
        samples_used += 1
        if not body:
            return None
        ok, tail = _verify_compile(rid, goal, body, lean_root, timeout_s)
        sig = proof_state_signal(0 if ok else 1, tail)
        return {"body": body, "ok": ok, "tail": tail,
                "goals": sig["goals_remaining"], "progress": sig["progress"]}

    def ratify(body, tail):
        contract = _build_solver_action_contract(row, lean_root)
        v = _validate_against_contract(contract=contract, proof_text=body, enriched_goal=goal,
                target_name=tgt, lean_root=lean_root, timeout_s=timeout_s,
                kernel_compile_ok=True, kernel_compile_tail=tail)
        return bool(v["credit_ready_at_solver_layer"]), v["receipts"]["matched_negative_control_receipt"]["passed"]

    def key(c):                                  # higher = better: closed, fewer goals, more progress
        return (1 if c["ok"] else 0, -(c["goals"] if c["goals"] is not None else 99), c["progress"])

    # round 0 — best-of-N fresh
    cands = []
    for i in range(n):
        c = evaluate(_gen(providers[i % len(providers)], goal, None, None, STRATEGIES[i % len(STRATEGIES)], timeout_s))
        if c is None:
            continue
        if c["ok"]:
            ok2, mnc = ratify(c["body"], c["tail"])
            print(f"  [{rid[:20]}] round0 sample{i}: COMPILED — ratified={ok2}", flush=True)
            if ok2:
                return _record(con, rid, True, mnc, 0, samples_used, 0, 1.0, c["body"])
        cands.append(c)
    beam = sorted(cands, key=key, reverse=True)[:beam_w]
    best = beam[0] if beam else None
    print(f"  [{rid[:20]}] round0: beam goals={[b['goals'] for b in beam]}", flush=True)

    # rounds 1..K — feedback refinement, monotone beam
    for r in range(1, rounds + 1):
        newc = []
        for node in beam:
            residual = "\n---\n".join(extract_unsolved_goals(node["tail"])) or "(no explicit goal text)"
            for i in range(n):
                c = evaluate(_gen(providers[i % len(providers)], goal, node["body"], residual,
                                  STRATEGIES[i % len(STRATEGIES)], timeout_s))
                if c is None:
                    continue
                if c["ok"]:
                    ok2, mnc = ratify(c["body"], c["tail"])
                    print(f"  [{rid[:20]}] round{r}: COMPILED — ratified={ok2}", flush=True)
                    if ok2:
                        return _record(con, rid, True, mnc, r, samples_used, 0, 1.0, c["body"])
                newc.append(c)
        beam = sorted(beam + newc, key=key, reverse=True)[:beam_w]   # monotone: never worse
        best = beam[0] if beam else best
        print(f"  [{rid[:20]}] round{r}: beam goals={[b['goals'] for b in beam]} samples={samples_used}", flush=True)

    return _record(con, rid, False, None, rounds, samples_used,
                   best["goals"] if best else None, best["progress"] if best else 0.0,
                   best["body"] if best else "")


def _record(con, rid, closed, mnc, rounds_used, samples, goals, prog, body) -> dict:
    con.execute("INSERT INTO search VALUES (?,?,?,?,?,?,?,?,?)",
                (rid, 1 if closed else 0, (1 if mnc else 0) if mnc is not None else None,
                 rounds_used, samples, goals, prog, (body or "")[:4000],
                 datetime.now(timezone.utc).isoformat()))
    con.commit()
    return {"row_id": rid, "closed": closed, "goals": goals, "samples": samples}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slice", required=True)
    ap.add_argument("--rows", default="")
    ap.add_argument("--providers", default="claude_opus")
    ap.add_argument("--n", type=int, default=6, help="best-of-N samples per node")
    ap.add_argument("--beam", type=int, default=3)
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--timeout", type=int, default=400)
    ap.add_argument("--out-db", default=str(REPO / "analytics/public/leanmill/proof_search.db"))
    ap.add_argument("--lean-root", default=str(REPO / "ztare_proofs"))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    rows = [json.loads(l) for l in Path(a.slice).read_text().splitlines() if l.strip()]
    rows = [r for r in rows if (r.get("goal") or "").strip()]
    if a.rows:
        keep = set(x.strip() for x in a.rows.split(",") if x.strip())
        rows = [r for r in rows if r.get("target_theorem_name") in keep or any(k in r.get("row_id","") for k in keep)]
    provs = [p.strip() for p in a.providers.split(",") if p.strip()]
    budget = a.n * (1 + a.beam * a.rounds)
    print(f"[search] {len(rows)} rows × providers={provs} × N={a.n} beam={a.beam} rounds={a.rounds} "
          f"(≤{budget} samples/row)")
    if a.dry_run:
        for r in rows: print(f"  {r.get('row_id')} goal_len={len(r.get('goal',''))}")
        return 0
    con = _conn(Path(a.out_db)); wins = 0
    for r in rows:
        t0 = time.time()
        res = search(r, provs, a.n, a.beam, a.rounds, a.timeout, Path(a.lean_root), con)
        if res["closed"]: wins += 1
        print(f"[search] {res['row_id'][:24]} closed={res['closed']} goals={res['goals']} "
              f"samples={res['samples']} ({round(time.time()-t0)}s)", flush=True)
    print(f"\n[search] CLOSURES: {wins}/{len(rows)} "
          f"{'<-- search closes what one-shot could not' if wins else '(no closure under this budget)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
