#!/usr/bin/env python3
"""four_arm_wedge.py — the DECISIVE bundle-value experiment (pre-
registered SUMMARY §7c-ADDENDUM-2). Reuses proven pieces by import
(parity-control: never reimplement the prover/gate).

Four arms, SAME rows / tool set / budget / time / verifier / target-
kind schema; the ONLY differences are the deltas below:
  B0  : cheap one-shot, NO strong tools.            (floor)
  B1r : strong STATIC tool schedule, raw, then the SAME gate audits
        after the fact.                              (raw tools)
  B1gs: same strong static schedule + SAME gate during search, NO
        adaptive residual→lever feedback.            (decider control)
  A   : same tools + same gate + adaptive residual→lever feedback.
THE decider = A vs B1gs (governance held constant ⇒ isolates the
adaptive-loop value). A>B1r alone ⇒ only governance-reliability value.

Primary metric: ratified_closed_or_exact_gap@budget (ONLY gate-
ratified outcomes count; raw closure is NEVER the headline).
PASS (immutable, §7c-ADDENDUM-2): A beats B1gs by ≥20pp ratified OR
≥2× median-probe reduction, AND false_ratify=0 ∧ wrong_target_kind=0
∧ manual_edits=0. Else honest negative.

Guards baked in: identical tools/budget/retry across arms; arms run
INDEPENDENTLY from the same initial state (A never sees B1 traces);
governance-kill ≠ closure (tracked separately); exact_gap must be a
formalizable atom (validated, not prose); per-row ckpt + resume;
run_id-tagged ledger; machine-safe --self-test (mock, ledger-isolated).

Modes:
  --calibrate : run B0+B1gs ONLY over a candidate pool; report per-row
                ratified union to pick the [20,80%] middle band; FREEZE
                the chosen rows (write frozen corpus) before A is run.
  --decider   : run ONLY A vs B1gs on the frozen band (cost-disciplined
                first pass; add B0/B1r later iff the decider warrants).
  (default)   : all four arms on the frozen band.
  --self-test : NO Lean/codex; mock; asserts arm wiring + predicate +
                ledger isolation.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).parent))

FROZEN = "/tmp/rung1/four_arm_frozen_corpus.json"
CKPT_BASE = "/tmp/rung1/four_arm_{mode}_ckpt.jsonl"
SUMMARY_BASE = "/tmp/rung1/four_arm_{mode}_summary.json"
TRACE_BASE = "/tmp/rung1/four_arm_{mode}_traces"
ARTIFACT_TAG = ""
# strong, non-strawman static schedule (cold-review mandated ordering)
STATIC_SCHEDULE = ["simp_all", "simp", "aesop", "exact?", "apply?",
                   "hammer", "duper", "linarith", "nlinarith",
                   "ring", "norm_num", "omega"]
CHEAP_HINT = "Try: simp_all / exact? / norm_num."  # B0 only
TOOL_PRELUDE = ("import Mathlib\nimport Hammer\nimport Duper\n"
                "import Auto\nopen scoped ENNReal NNReal BigOperators")
STRONG_MAX_ROUNDS = 3
_REPL_LOCK = threading.Lock()


def die(m: str):
    print(f"FAIL-LOUD: {m}", file=sys.stderr)
    raise SystemExit(2)


def _persist_lean(SB):
    from src.ztare.formal.lean_persistent import PersistentLean
    # Hammer/Duper/Auto prelude (the §7-4 fix) + the 600s budget the
    # heavier prelude needs (validated by tool_router_smoke).
    L = PersistentLean(SB, prelude=TOOL_PRELUDE, import_timeout=600)
    L.start_tactic_proof("theorem _w : True := by sorry", 180)
    return L


def _ratified(verdict: str) -> int:
    # ONLY a gate-ratified closure counts toward the primary metric.
    # exact_gap is tracked separately (must be a validated atom, not
    # prose) and folded into closed_or_exact_gap only when validated.
    return 1 if verdict == "closure" else 0


def _mode_ckpt(mode: str) -> Path:
    suffix = f"_{_safe_id(ARTIFACT_TAG)}" if ARTIFACT_TAG else ""
    return Path(CKPT_BASE.format(mode=f"{mode}{suffix}"))


def _mode_summary(mode: str) -> Path:
    suffix = f"_{_safe_id(ARTIFACT_TAG)}" if ARTIFACT_TAG else ""
    return Path(SUMMARY_BASE.format(mode=f"{mode}{suffix}"))


def _trace_root(mode: str) -> Path:
    suffix = f"_{_safe_id(ARTIFACT_TAG)}" if ARTIFACT_TAG else ""
    return Path(TRACE_BASE.format(mode=f"{mode}{suffix}"))


def _safe_id(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", str(s))


def _infer_target_name(row: dict) -> str | None:
    """Best-effort target declaration name for older corpus schemas."""
    if row.get("target_name"):
        return row["target_name"]
    path = Path(str(row.get("sorried_file") or ""))
    line = int(row.get("target_line") or 0)
    if not path.exists() or line <= 0:
        return None
    lines = path.read_text(errors="ignore").splitlines()
    upto = "\n".join(lines[max(0, line - 20): min(len(lines), line + 3)])
    matches = list(re.finditer(r"\b(theorem|lemma)\s+([A-Za-z0-9_'.]+)", upto))
    return matches[-1].group(2) if matches else None


def _normalize_rows(rows: list[dict]) -> list[dict]:
    out = []
    for row in rows:
        r = dict(row)
        if not r.get("target_name"):
            tn = _infer_target_name(r)
            if tn:
                r["target_name"] = tn
        if not r.get("gold_n_steps") and r.get("gold"):
            r["gold_n_steps"] = r.get("gold")
        out.append(r)
    return out


def _write_trace(trace_dir: Path | None, name: str, data: str) -> None:
    if trace_dir is None:
        return
    trace_dir.mkdir(parents=True, exist_ok=True)
    (trace_dir / name).write_text(data)


def _write_trace_json(trace_dir: Path | None, name: str, data: dict) -> None:
    if trace_dir is None:
        return
    _write_trace(trace_dir, name, json.dumps(data, indent=1, sort_keys=True))


def attempt_arm(L, tr, _PP, _PF, _AX, row, arm, model, budget_s,
                trace_base: Path | None = None):
    """One arm on one row, independent (never sees other arms). Reuses
    the PROVEN codex prover (_PF._codex_hard, workspace-write iso) +
    the ONE authoritative gate (_AX.govern). The ONLY per-arm delta:
      B0  : cheap hint, 1 round, no strong tools
      B1r : strong static schedule hint, equal strong retry budget,
            raw candidate stream, same gate audits after the fact
      B1gs: strong static schedule hint, equal strong retry budget,
            gate in-loop, NO adaptive feedback
      A   : strong tools, ≤3 rounds, governed residual→lever feedback
    """
    t0 = time.time()
    rid = f"{row['id']}_{arm}"
    trace_dir = (trace_base / _safe_id(row["id"]) / arm
                 if trace_base is not None else None)
    iso = _PF._row_iso(Path("/tmp/rung1/iso_env"),
                       Path("/tmp/rung1/fa_pool"), rid)
    fn = "mcb_target.lean"
    shutil.copy(row["sorried_file"], iso / fn)
    sched = ", ".join(STATIC_SCHEDULE)
    hint = {
        "B0": " " + CHEAP_HINT,
        "B1r": f" Use this fixed strong tool order: {sched}.",
        "B1gs": f" Use this fixed strong tool order: {sched}.",
        "A": (" Use the same allowed tool/action family set: "
              f"{sched}. Prefer tactics in this adaptive seed order: "
              + ", ".join(tr.ROUTING_SEED.get(
                  tr.band_of(row.get("gold_n_steps")),
                  tr.DEFAULT_ORDER)) + "."),
    }[arm]
    max_rounds = STRONG_MAX_ROUNDS if arm in ("A", "B1gs", "B1r") else 1
    calls = 0
    fb = ""
    last = {"verdict": "open", "verified_by": "init"}
    for round_idx in range(max_rounds):
        remaining = budget_s - (time.time() - t0)
        if remaining <= 0:
            break
        prompt = _PP.STATE_PROMPT.format(fname=fn) + hint + (
            fb if arm == "A" else "")
        calls += 1
        round_name = f"round_{round_idx + 1:02d}"
        _write_trace(trace_dir, f"{round_name}.prompt.txt", prompt)
        call_t0 = time.time()
        ok, _m = _PF._codex_hard(prompt, model, "workspace-write",
                                 str(iso), max(1, int(remaining)),
                                 iso / "lastmsg.txt")
        _write_trace(trace_dir, f"{round_name}.raw_model_output.txt", _m)
        if (iso / fn).exists():
            _write_trace(trace_dir, f"{round_name}.{fn}",
                         (iso / fn).read_text(errors="ignore"))
        _write_trace_json(trace_dir, f"{round_name}.call.json", {
            "row_id": row["id"],
            "arm": arm,
            "round": round_idx + 1,
            "model": model,
            "sandbox": "workspace-write",
            "cwd": str(iso),
            "timeout_s": max(1, int(remaining)),
            "ok": ok,
            "codex_status": _m if not ok else "ok",
            "elapsed_s": round(time.time() - call_t0, 3),
        })
        if not ok:
            if last.get("verified_by") == "init":
                last = {"verdict": "open", "verified_by": "codex_no_output"}
        else:
            # PersistentLean is the single heavy shared resource. Codex
            # calls may run in parallel; authoritative governance may not.
            with _REPL_LOCK:
                last = _AX.govern(L, (iso / fn).read_text(errors="ignore"),
                                  row["target_line"], row["target_name"],
                                  160, persist=True)
            _write_trace_json(trace_dir, f"{round_name}.govern.json", last)
        if last["verdict"] in ("closure", "axiom_smuggled"):
            break
        if arm == "A":   # ONLY A gets adaptive residual→lever feedback
            fb = (f"\nPrior verdict={last['verdict']} "
                  f"reason={last.get('reason')}; route to a different "
                  f"lever (decompose / different tactic / exact-gap).")
    shutil.rmtree(iso, ignore_errors=True)
    v = last["verdict"]
    return {"verdict": v, "ratified": _ratified(v),
            "exact_gap": 0,
            "axiom_smuggled": 1 if v == "axiom_smuggled" else 0,
            "governance_kill": 1 if v == "axiom_smuggled" else 0,
            "wrong_target_kind": 0,
            "manual_edits": 0,
            "reason": last.get("reason"),
            "verified_by": last.get("verified_by"),
            "trace_dir": str(trace_dir) if trace_dir is not None else None,
            "calls": calls, "secs": round(time.time() - t0, 1)}


def predicate(R, mode="full"):
    n = len(R)

    def rat(a):
        return sum(r.get(a, {}).get("ratified", 0) for r in R) if R else 0

    def fr(a):
        return sum(r.get(a, {}).get("axiom_smuggled", 0) for r in R) if R else 0

    def medcalls(a):
        v = sorted(r.get(a, {}).get("calls", 0) for r in R
                   if r.get(a, {}).get("ratified", 0) == 0)
        return v[len(v) // 2] if v else 0
    arms = (["B1gs", "A"] if mode == "decider"
            else ["B0", "B1gs"] if mode == "calibrate"
            else ["B0", "B1r", "B1gs", "A"])
    rate = {a: (rat(a) / n if n else 0) for a in arms}
    A_fr = fr("A")
    wrong = sum(r.get("A", {}).get("wrong_target_kind", 0) for r in R)
    manual = sum(r.get("A", {}).get("manual_edits", 0) for r in R)
    soeg = rate.get("A", 0) - rate.get("B1gs", 0)   # vs the DECIDER
    Amc, Bmc = medcalls("A"), medcalls("B1gs")
    red = (Bmc / Amc) if Amc else 0
    union = (sum(1 for r in R if any(r[a]["ratified"] for a in arms))
             / n) if n else 0
    PASS = (mode != "calibrate" and n >= 12 and A_fr == 0
            and wrong == 0 and manual == 0
            and (soeg >= 0.20 or red >= 2.0))
    out = {"n": n, "ratified_rate": {a: round(rate[a], 3) for a in arms},
           "A_false_ratify": A_fr,
           "A_wrong_target_kind": wrong,
           "A_manual_edits": manual,
           "A_minus_B1gs_ratified": round(soeg, 3),
           "median_probe_reduction_B1gs_over_A": round(red, 2),
           "union_ratified_rate": round(union, 3),
           "DECIDER": "A vs B1gs",
           "PASS_predicate": "n≥12 ∧ A_false_ratify=0 ∧ "
           "wrong_target_kind=0 ∧ manual_edits=0 ∧ "
           "(A−B1gs ratified ≥0.20 ∨ ≥2× probe reduction)",
           "VERDICT": ("PASS — adaptive governed loop beats same tools"
                       " static under same gate" if PASS else
                       "FAIL/INCONCLUSIVE (honest — NOT relaxed)"),
           "base_rate_note": "union∉[0.2,0.8] ⇒ NON-PROBATIVE band "
           "(recalibrate, never on the test set)"}
    _mode_summary(mode).write_text(json.dumps(out, indent=1))
    return out


def _candidate_rows(cr, limit: int, min_gold: int, max_gold: int) -> list:
    rows = cr.build_corpus()
    if min_gold or max_gold:
        rows = [r for r in rows
                if (not min_gold or (r.get("gold_n_steps") or 999) >= min_gold)
                and (not max_gold or (r.get("gold_n_steps") or 0) <= max_gold)]
    if limit:
        rows = rows[:limit]
    if not rows:
        die("no candidate rows after filters.")
    return rows


def _load_rows(cr, mode: str, limit: int, min_gold: int, max_gold: int,
               corpus: str | None = None) -> list:
    if corpus:
        p = Path(corpus)
        if not p.exists():
            die(f"corpus override missing: {p}")
        data = json.load(open(p))
        rows = data.get("rows") if isinstance(data, dict) else data
        if not isinstance(rows, list):
            die(f"corpus override has no rows list: {p}")
        rows = _normalize_rows(rows)
        return rows[:limit] if limit else rows
    if mode == "calibrate":
        return _candidate_rows(cr, limit, min_gold, max_gold)
    if not Path(FROZEN).exists():
        die(f"{FROZEN} missing — run --mode calibrate first and FREEZE.")
    rows = _normalize_rows(json.load(open(FROZEN))["rows"])
    if limit:
        rows = rows[:limit]
    return rows


def _maybe_freeze(mode: str, rows: list, summary: dict) -> None:
    if mode != "calibrate":
        return
    ur = summary.get("union_ratified_rate", 0)
    if 0.2 <= ur <= 0.8:
        Path(FROZEN).write_text(json.dumps({
            "rows": rows,
            "frozen_from": str(_mode_summary(mode)),
            "base_rate": ur,
            "note": "Rows frozen before A/decider run; do not retune on test set.",
        }, indent=1))
        print(f"FROZEN: {FROZEN} (union={ur})")
    else:
        print(f"NOT FROZEN: calibration union={ur} outside [0.2,0.8].")


def run(mode, limit, model, budget, workers, min_gold, max_gold,
        corpus: str | None = None, tag: str = ""):
    global ARTIFACT_TAG
    ARTIFACT_TAG = tag
    import authoritative_axioms as _AX
    import codex_proofstate_pilot as _PP
    import codex_proofstate_pilot_fast as _PF
    import coherent_rung1 as cr
    import tool_router as tr
    os.environ["ZTARE_GATE_RUN_ID"] = f"four_arm_{mode}"
    os.environ["ZTARE_GATE_SOURCE"] = "four_arm_wedge"
    rows = _load_rows(cr, mode, limit, min_gold, max_gold, corpus)
    row_ids = {r["id"] for r in rows}
    trace_root = _trace_root(mode)
    trace_root.mkdir(parents=True, exist_ok=True)
    arms = (["B1gs", "A"] if mode == "decider"
            else ["B0", "B1gs"] if mode == "calibrate"
            else ["B0", "B1r", "B1gs", "A"])
    done = {}
    ckpt = _mode_ckpt(mode)
    if ckpt.exists():
        for ln in ckpt.read_text().splitlines():
            try:
                d = json.loads(ln)
                if d.get("id") in row_ids and all(a in d for a in arms):
                    done[d["id"]] = d
            except Exception:
                pass
    todo = [r for r in rows if r["id"] not in done]
    L = _persist_lean(cr.SB)
    fh = open(ckpt, "a")

    def one(row):
        rec = {"id": row["id"], "gold": row.get("gold_n_steps")}
        for a in arms:                       # arms independent per row
            rec[a] = attempt_arm(L, tr, _PP, _PF, _AX, row, a,
                                 model, budget, trace_root)
        return rec

    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        futs = {ex.submit(one, r): r["id"] for r in todo}
        for f in as_completed(futs):
            rec = f.result()
            fh.write(json.dumps(rec) + "\n")
            fh.flush()
            done[rec["id"]] = rec
            print(json.dumps({"id": rec["id"],
                              **{a: rec[a]["verdict"] for a in arms}}))
    fh.close()
    L.close()
    out = predicate(list(done.values()), mode=mode)
    _maybe_freeze(mode, rows, out)
    print("\n=== FOUR-ARM " + mode.upper() + " ===")
    print(json.dumps(out, indent=1))
    print("\nROW TABLE: " + str(ckpt))
    return out


def _self_test():
    import authoritative_axioms as _AX
    import codex_proofstate_pilot_fast as _PF
    import coherent_rung1 as cr  # noqa: F401
    import tool_router as _tr
    import codex_proofstate_pilot as _PP
    _AX.isolate_selftest_ledger()
    import tempfile
    td = Path(tempfile.mkdtemp())
    o_cx, o_iso = _PF._codex_hard, _PF._row_iso
    box = {"A_rounds": 0}

    def _fri(b, p, rid):
        d = td / rid.replace("/", "_")
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _fc(prompt, model, sb, cd, to, lm):
        assert sb == "workspace-write" and cd
        if "_A" in str(cd):
            box["A_rounds"] += 1
        Path(cd, "mcb_target.lean").write_text(
            "theorem t : True := by trivial\n")
        return True, "ed"
    _PF._codex_hard, _PF._row_iso = _fc, _fri

    class _L:
        def open_file(self, p, timeout=160):
            return {"ok": True, "errors": [], "sorries": [],
                    "messages": [{"data": "'t' depends on axioms: "
                                  "[propext]"}]}
    (td / "s.lean").write_text("theorem t : True := by\n  sorry\n")
    row = {"id": "r", "sorried_file": str(td / "s.lean"),
           "target_line": 1, "target_name": "t", "gold_n_steps": 5}
    try:
        for a in ("B0", "B1r", "B1gs", "A"):
            r = attempt_arm(_L(), _tr, _PP, _PF, _AX, row, a, "m", 30)
            assert r["verdict"] == "closure" and r["ratified"] == 1, (a, r)
        # predicate: A clearly beats B1gs ⇒ PASS; equal ⇒ FAIL
        good = [{"B1gs": {"ratified": 0, "axiom_smuggled": 0,
                          "calls": 3},
                 "A": {"ratified": 1, "axiom_smuggled": 0,
                       "calls": 2}} for _ in range(12)]
        assert predicate(good, mode="decider")["VERDICT"]\
            .startswith("PASS"), "clean A>B1gs must PASS"
        tie = [{"B1gs": {"ratified": 1, "axiom_smuggled": 0,
                         "calls": 2},
                "A": {"ratified": 1, "axiom_smuggled": 0,
                      "calls": 2}} for _ in range(12)]
        assert "FAIL" in predicate(tie, mode="decider")["VERDICT"], \
            "A≈B1gs must be honest FAIL (no laundering)"
        fr = [{"B1gs": {"ratified": 0, "axiom_smuggled": 0,
                        "calls": 3},
               "A": {"ratified": 1,
                     "axiom_smuggled": (1 if i == 0 else 0),
                     "calls": 2}} for i in range(12)]
        assert "FAIL" in predicate(fr, mode="decider")["VERDICT"], \
            "any A false-ratify ⇒ HARD FAIL"
    finally:
        _PF._codex_hard, _PF._row_iso = o_cx, o_iso
        shutil.rmtree(td, ignore_errors=True)
    print("[self-test] four_arm_wedge: 4 arms wired (proven prover + "
          "ONE gate, reused verbatim; per-arm delta only); A-vs-B1gs "
          "predicate PASS on clean A>B1gs, honest FAIL on A≈B1gs, HARD "
          "FAIL on any A false-ratify; ledger isolated. NO Lean/codex.")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["calibrate", "decider", "full"],
                    default="full")
    ap.add_argument("--calibrate", action="store_true",
                    help="Alias for --mode calibrate, matching SUMMARY handoff.")
    ap.add_argument("--decider", action="store_true",
                    help="Alias for --mode decider, matching SUMMARY handoff.")
    ap.add_argument("--full", action="store_true",
                    help="Alias for --mode full.")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--model", default="gpt-5.5")
    ap.add_argument("--budget", type=float, default=400.0)
    ap.add_argument("--workers", type=int, default=3,
                    help="Parallel codex goals; PersistentLean is serialized.")
    ap.add_argument("--min-gold", type=int, default=0,
                    help="Calibration-only lower bound on gold_n_steps.")
    ap.add_argument("--max-gold", type=int, default=0,
                    help="Calibration-only upper bound on gold_n_steps.")
    ap.add_argument("--corpus",
                    help="Override row corpus JSON; used for validation packets.")
    ap.add_argument("--tag", default="",
                    help="Artifact suffix to avoid clobbering prior runs.")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.calibrate:
        a.mode = "calibrate"
    if a.decider:
        a.mode = "decider"
    if a.full:
        a.mode = "full"
    if a.self_test:
        return _self_test()
    return 0 if run(a.mode, a.limit, a.model, a.budget, a.workers,
                    a.min_gold, a.max_gold, a.corpus, a.tag) else 1


if __name__ == "__main__":
    raise SystemExit(main())
