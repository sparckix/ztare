"""Prompt-evolution SUBSTRATE (#124 deferred-leg pulled forward, alien lens) — the missing half of the
prompt-evolution loop. The EVALUATOR already exists (`sequential_ab.SequentialABGate`, anytime-valid /
peeking-safe); what was missing is the LEDGER that lets a prompt change be adjudicated: stamp every
dispatch with the FINGERPRINT of the prompt-template version that produced it, plus (goal_sha, closed),
so when a template changes the new fingerprint's outcomes can be A/B'd against the old — paired by
goal_sha — through the existing gate.

WHY substrate-not-loop (the no-frankenstein / no-dormancy line): automating prompt MUTATION on zero data
is the overfit trap the deferral named. Generation (proposing a better prompt) stays the agent/operator's
creative act — the correct Goldilocks boundary (agency upstream). This module is pure TELEMETRY +
adjudication: it auto-accrues on every dispatch (so it is never dormant), reuses the one sound A/B gate
(no parallel statistics), and only ever RECOMMENDS a promotion (`evaluate`), never flips a prompt itself.

  python -m ztare.leanmill.solver.prompt_evolution --selftest
  python -m ztare.leanmill.solver.prompt_evolution report <slot>
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
LEDGER = REPO / "analytics" / "public" / "queries" / "prompt_evolution.jsonl"   # append-only telemetry


def prompt_fingerprint(template_text: str) -> str:
    """Stable 12-hex fingerprint of a prompt TEMPLATE (the version-bearing skeleton, NOT the filled-in
    goal). Whitespace-normalized so a reflow doesn't churn the id; placeholder names are part of the
    skeleton and DO count (changing them is a real prompt change)."""
    norm = " ".join((template_text or "").split())
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()[:12]


def record_dispatch(slot: str, template_text: str, goal_sha: str, closed: bool,
                    *, run_tag: str = "", ts: str = "", ledger: "Path | None" = None) -> str:
    """Append one (slot, fingerprint, goal_sha, closed) row. Returns the fingerprint. Best-effort:
    `ZTARE_LEANMILL_PROMPT_EVO=0` disables; any IO error is swallowed (telemetry never breaks a solve)."""
    if os.environ.get("ZTARE_LEANMILL_PROMPT_EVO", "1") == "0":
        return ""
    fp = prompt_fingerprint(template_text)
    try:
        led = Path(ledger) if ledger else LEDGER
        led.parent.mkdir(parents=True, exist_ok=True)
        with led.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"slot": slot, "fp": fp, "goal_sha": goal_sha,
                                "closed": 1 if closed else 0, "run_tag": run_tag, "ts": ts}) + "\n")
    except OSError:
        pass
    return fp


def _rows(ledger: "Path | None" = None) -> "list[dict]":
    try:
        led = Path(ledger) if ledger else LEDGER
        return [json.loads(l) for l in led.read_text(encoding="utf-8").splitlines() if l.strip()]
    except OSError:
        return []


def fingerprints(slot: str, ledger: "Path | None" = None) -> "list[dict]":
    """Per-fingerprint summary for a slot, newest-first by last-seen: {fp, n, closed, last_ts}."""
    agg: "dict[str, dict]" = {}
    for r in _rows(ledger):
        if r.get("slot") != slot:
            continue
        a = agg.setdefault(r["fp"], {"fp": r["fp"], "n": 0, "closed": 0, "last_ts": ""})
        a["n"] += 1
        a["closed"] += int(r.get("closed") or 0)
        if str(r.get("ts") or "") > a["last_ts"]:
            a["last_ts"] = str(r.get("ts") or "")
    return sorted(agg.values(), key=lambda d: d["last_ts"], reverse=True)


def evaluate(slot: str, fp_a: str, fp_b: str, *, alpha: float = 0.05,
             ledger: "Path | None" = None) -> dict:
    """Adjudicate template fp_a vs fp_b on the SAME goals (paired by goal_sha) through the anytime-valid
    gate. A=baseline (current), B=candidate (new). Returns the gate verdict + per-arm rates + the
    paired-N; a goal counts only if BOTH fingerprints attempted it (the pairing the gate requires)."""
    from ztare.leanmill.sequential_ab import ab_gate
    by_goal: "dict[str, dict]" = {}
    for r in _rows(ledger):
        if r.get("slot") != slot or r.get("fp") not in (fp_a, fp_b):
            continue
        g = by_goal.setdefault(r["goal_sha"], {})
        # best (max) outcome per (goal, fp) — a goal that ever closed under a template counts as a win
        g[r["fp"]] = max(g.get(r["fp"], 0), int(r.get("closed") or 0))
    a_out, b_out = [], []
    for g in by_goal.values():
        if fp_a in g and fp_b in g:
            a_out.append(g[fp_a]); b_out.append(g[fp_b])
    if not a_out:
        return {"verdict": "not_yet", "paired_n": 0, "note": "no goals attempted under BOTH fingerprints yet"}
    res = ab_gate(a_out, b_out, alpha=alpha)
    rec = ("promote candidate (B)" if res["verdict"] == "B>A"
           else "keep baseline (A)" if res["verdict"] == "A>B"
           else "keep running — not enough paired evidence")
    return {**res, "paired_n": len(a_out), "fp_a": fp_a, "fp_b": fp_b, "recommendation": rec}


def _selftest() -> int:
    import tempfile
    fails: "list[str]" = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    led = Path(tempfile.mkdtemp(prefix="pe_")) / "pe.jsonl"
    tmpl_a = "Prove the goal.\nGOAL: {goal}"
    tmpl_b = "Prove the goal. Search Mathlib for the lemma first.\nGOAL: {goal}"
    fa, fb = prompt_fingerprint(tmpl_a), prompt_fingerprint(tmpl_b)
    ok("fingerprint stable under whitespace reflow",
       prompt_fingerprint(tmpl_a) == prompt_fingerprint("Prove the   goal.\n\nGOAL: {goal}"))
    ok("fingerprint changes when the template changes", fa != fb)
    # B closes more on the SAME 20 goals (paired); A closes ~half
    for i in range(20):
        gs = f"goal{i:02d}"
        record_dispatch("warm_leaf", tmpl_a, gs, closed=(i % 2 == 0), run_tag="t", ts=f"t{i:02d}", ledger=led)
        record_dispatch("warm_leaf", tmpl_b, gs, closed=(i % 5 != 0), run_tag="t", ts=f"t{i:02d}", ledger=led)
    fps = fingerprints("warm_leaf", ledger=led)
    ok("fingerprints summarized per template", len(fps) == 2 and all(f["n"] == 20 for f in fps))
    ev = evaluate("warm_leaf", fa, fb, ledger=led)
    ok("paired evaluation runs through the anytime-valid gate", ev["paired_n"] == 20 and "verdict" in ev)
    ok("B's higher close-rate is reflected", ev["b_rate"] > ev["a_rate"])
    # an unpaired comparison (B never attempted these goals) ⇒ not_yet, no false flip
    for i in range(5):
        record_dispatch("planner", tmpl_a, f"p{i}", closed=True, ledger=led)
    ok("no pairing ⇒ not_yet (peeking-safe, no false promotion)",
       evaluate("planner", fa, fb, ledger=led)["paired_n"] == 0)
    _sv = os.environ.get("ZTARE_LEANMILL_PROMPT_EVO")
    try:
        os.environ["ZTARE_LEANMILL_PROMPT_EVO"] = "0"
        ok("kill-switch: =0 records nothing", record_dispatch("x", tmpl_a, "g", True, ledger=led) == "")
    finally:
        os.environ.pop("ZTARE_LEANMILL_PROMPT_EVO", None) if _sv is None else os.environ.__setitem__("ZTARE_LEANMILL_PROMPT_EVO", _sv)
    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


def _report(slot: str) -> int:
    fps = fingerprints(slot)
    if not fps:
        print(f"prompt_evolution: no dispatches recorded for slot '{slot}'")
        return 0
    print(f"prompt_evolution — slot '{slot}' ({len(fps)} template fingerprint(s)):")
    for f in fps:
        rate = f["closed"] / max(1, f["n"])
        print(f"  {f['fp']}  n={f['n']:4d}  closed={f['closed']:4d}  rate={rate:.3f}  last={f['last_ts']}")
    if len(fps) >= 2:
        ev = evaluate(slot, fps[1]["fp"], fps[0]["fp"])   # baseline=older, candidate=newest
        print(f"  → newest vs prior: {ev.get('recommendation', ev)} "
              f"(paired_n={ev.get('paired_n')}, verdict={ev.get('verdict')})")
    return 0


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 3 and sys.argv[1] == "report":
        raise SystemExit(_report(sys.argv[2]))
    raise SystemExit(_selftest())
