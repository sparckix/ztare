#!/usr/bin/env python3
"""Step 1a (cold-review): generate a VERIFIED per-row probe matrix using
ONLY the verified primitives (batch_probe + governance) — no brittle
live orchestration. ONE batched compile per row amortizes import; each
in-grid 'closed' is governance-adjudicated. Persisted ONCE, then
offline_policy_replay.py runs any number of cost-accounted policies over
it for free (zero further Lean).

Schema (per cold-review): one record per (row,candidate,action):
 {row_id,candidate_id,action_id,candidate_source_rank,text_score,
  lean_result(closed|exact_gap|no_progress|failed),
  governance_verdict(genuine|single_lemma|axiom_smuggled|unverified|na),
  axioms_clean,target_kind,cost_counted:true}
"""
from __future__ import annotations
import argparse, importlib.util, json, re
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "r1", str(Path(__file__).with_name("rung1_kernel_grounded_rerank.py")))
R1 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(R1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--sandbox", default=R1.DEFAULT_SB)
    ap.add_argument("--out", required=True)
    ap.add_argument("--batch-timeout", type=int, default=900)
    a = ap.parse_args()
    sb = Path(a.sandbox).expanduser().resolve()
    rows = json.load(open(a.corpus))["rows"]
    c_acts = [x for x in R1.ACTIONS if "{C}" in x]
    noc = [x for x in R1.ACTIONS if "{C}" not in x]

    out = {"sandbox": str(sb), "actions": R1.ACTIONS, "rows": {}}
    for row in rows:
        rid = row["id"]
        nm = row.get("intended_closer") or ""
        novel = (row.get("bucket") not in ("pin_delta", "escape_route")
                 or R1.closer_absent_at_pin(sb, nm))
        if not novel:
            out["rows"][rid] = {"skipped": "closer not #check-absent at pin"}
            continue
        stmt = row["statement"]
        pool = list(row.get("candidate_pool", []))
        text_rank = {c: i for i, c in enumerate(
            R1.source_text_bm25(stmt, pool))}
        clean = re.sub(r"[^A-Za-z0-9_]", "", rid) or "R"
        items, meta, k = [], {}, 0
        for c in pool:
            for act in c_acts:
                pid = f"{clean}p{k}"; k += 1
                items.append((pid, R1._named(stmt, pid)
                              + " := by " + act.replace("{C}", c)))
                meta[pid] = (c, act)
        for act in noc:
            pid = f"{clean}p{k}"; k += 1
            items.append((pid, R1._named(stmt, pid) + " := by " + act))
            meta[pid] = (None, act)
        oc = R1.batch_probe(sb, items, timeout=a.batch_timeout)
        recs = []
        for pid, (c, act) in meta.items():
            res = oc.get(pid, "fail")
            lean_result = {"closed": "closed", "progress": "exact_gap",
                           "fail": "failed"}.get(res, "failed")
            gv, axc, tk = "na", None, None
            if res == "closed":
                tac = act.replace("{C}", c) if c else act
                full = R1._named(stmt, f"{clean}g") + " := by " + tac
                g = R1.governance(sb, stmt, full, 60)
                gv = {"closure": "genuine"}.get(g, g)
                axc = (g != "axiom_smuggled")
                tk = ("proof_closure" if g == "closure"
                      else "single_lemma" if g == "single_lemma"
                      else "invalid")
            recs.append({
                "row_id": rid, "candidate_id": c, "action_id": act,
                "candidate_source_rank": (text_rank.get(c)
                                          if c is not None else None),
                "lean_result": lean_result, "governance_verdict": gv,
                "axioms_clean": axc, "target_kind": tk,
                "cost_counted": True})
        out["rows"][rid] = {
            "statement": stmt, "pool": pool, "bucket": row.get("bucket"),
            "intended_closer": nm, "probes": recs,
            "n_closed_genuine": sum(
                1 for r in recs if r["governance_verdict"] == "genuine"),
            "n_closed_any": sum(
                1 for r in recs if r["lean_result"] == "closed"),
            "n_exact_gap": sum(
                1 for r in recs if r["lean_result"] == "exact_gap")}
    Path(a.out).write_text(json.dumps(out, indent=1, ensure_ascii=False))
    summ = {rid: {kk: v.get(kk) for kk in
                  ("n_closed_genuine", "n_closed_any", "n_exact_gap")}
            if "probes" in v else v
            for rid, v in out["rows"].items()}
    print(json.dumps({"out": a.out, "rows": len(out["rows"]),
                       "per_row": summ}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
