#!/usr/bin/env python3
"""residual_to_lever.py — the verification→solving bridge.

Implements the EXISTING consumer_feedback_contract (defined in
src/ztare/research_director/structural_fingerprint.py — imported here, not
re-forked): every audited/verified outcome is converted into a typed
residual_class from the canonical allowed set, then to a next_lever and a
next_target_statement. This is the component that makes governance
constructive: a verifier says FAIL; this says FAIL because residual=X,
next lever=Y, next target=Z.

Strict two-scoreboard discipline: this is SHARED KERNEL. It never counts
as a closure. `next_target_statement` is a PROPOSED obligation, not a
proof. A CLOSED outcome routes to governance ratification (xpanel +
operator-inversion per forward_evidence_schema) and only counts after.

Consumes outputs the apparatus already emits — no new detectors:
  - route_c_layer_2c_dispatch JSON (closure_verdict + gap_report{named_candidate_lemmas})
  - v33 organ flags / lean_proof_gate v33_organ_flags
  - ns_governance_gate verdict (BLOCK/PASS + target_kind)

Usage:
  residual_to_lever.py --dispatch-json /tmp/er_*.json
  residual_to_lever.py --record record.json        # generic audited record
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

# Canonical residual classes + lever map — IMPORTED from the kernel
# (src/ztare/research_director/structural_fingerprint), single source of
# truth. No local fork (anti-drift). The kernel now owns the map
# (operator-authorized kernel improvement 2026-05-16).
from src.ztare.research_director.structural_fingerprint import (  # noqa: E402
    ALLOWED_RESIDUAL_CLASSES as ALLOWED_RESIDUAL,
    RESIDUAL_TO_LEVER as LEVER,
)


# Unambiguous APPARATUS/wrapper compile signatures. Conservative on
# purpose: a genuine math failure ("unsolved goals", "linarith failed",
# "type mismatch" in the goal) is NOT here — only harness/scope/import
# defects, so this never launders a real math gap as a harness bug.
_APPARATUS_SIG = (
    "unknownidentifier", "unknown identifier", "unknown constant",
    "unbound", "unexpected token", "unknown package", "import",
    "unknown namespace", "failed to synthesize", "unknown attribute",
)
_GENUINE_GAP_SIG = (
    "unsolved goals", "linarith failed", "nlinarith failed",
    "ring failed", "type mismatch", "omega could not",
)


def _apparatus_error(rec: dict) -> bool:
    tails = []
    for r in rec.get("rounds", []) or []:
        cr = r.get("lean_compile") or {}
        t = str(cr.get("error_tail") or cr.get("error_head") or "")
        if t:
            tails.append(t.lower())
    blob = " ".join(tails)
    if not blob:
        return False
    # genuine math failure present anywhere -> NOT apparatus (don't launder)
    if any(g in blob for g in _GENUINE_GAP_SIG):
        return False
    return any(s in blob for s in _APPARATUS_SIG)


def classify(rec: dict) -> dict:
    """Map an audited outcome to {residual_class, next_lever, ...}.
    Deterministic; never fabricates a closure."""
    cv = rec.get("closure_verdict") or rec.get("verdict")
    gap = rec.get("gap_report") or {}
    v33 = rec.get("v33_organ_flags") or rec.get("risk_flags") or []
    ns_block = rec.get("verdict") == "BLOCK" and rec.get("blocks")

    if v33 and any("vacu" in str(f) or "gold_name" in str(f)
                   or "single_lemma_exact" in str(f) or "indirect_leak" in str(f)
                   or "currency" in str(f) for f in v33):
        rc = "gate_contract_not_crisp"
        summary = (f"v33 confirmed a false-closure sub-mode {list(v33)}: the "
                   "claimed target-kind/contract is not crisp (claim is "
                   "vacuous / verbatim / single-exact / leaked / mismatched).")
        nxt = "Restate as the honest target_kind (consequence/gap/route) or retire; do NOT record as proof_closure."
    elif ns_block:
        rc = "gate_contract_not_crisp"
        summary = "ns_governance_gate BLOCK: closure language on a non-proof_closure target_kind (mush)."
        nxt = "Restate the claim at its true target_kind, then re-submit."
    elif cv == "CLOSED" or rec.get("compiled_any") is True:
        rc = "none_closed"
        summary = "Candidate compiled / closure_verdict=CLOSED — UNVERIFIED until governance ratifies."
        nxt = "Route to governance: xpanel discipline + operator_inversion for idea-truth (forward_evidence). Counts only after ratified."
    elif _apparatus_error(rec):
        rc = "apparatus_or_source_mismatch"
        summary = ("Lean compile failed on an APPARATUS/wrapper defect "
                   "(unbound identifier / unknown constant / import / "
                   "scope) — NOT a genuine math gap. The harness corrupted "
                   "the attempt; classifying this as theorem_or_pde_gap "
                   "would launder a harness bug as missing mathematics.")
        nxt = ("Fix the route_c wrapper / replay / imports (e.g. binder "
               "splice dropping bound vars), then re-run before any "
               "theorem-gap verdict.")
    elif cv == "OPEN_GAP_REPORT" or gap:
        rc = "theorem_or_pde_gap"
        cands = gap.get("named_candidate_lemmas") or []
        c0 = (cands[0] if cands else None)
        summary = (f"Genuine attempt produced no closure; exact missing "
                   f"obligation isolated: {c0 or '(unnamed)'}.")
        nxt = (f"Prove the missing lemma: {c0}" if c0
               else "Formulate + prove the missing analytic atom named in gap_report.candidate_pathways")
    elif rec.get("status", "").startswith(("result_read_error", "dispatch_timeout",
                                           "sig_extract", "harness")):
        rc = "apparatus_or_source_mismatch"
        summary = f"Harness/apparatus failure ({rec.get('status')}) — not a math result."
        nxt = "Fix replay/import/context/parser; re-run before any theorem verdict."
    else:
        rc = "vocabulary_gap"
        summary = "Outcome not classifiable by current contract without stretching a term."
        nxt = "Log vocabulary_gap; route GP-233 + seam/spec update before promoting language (extension_trigger)."

    return {
        "attempt_id": rec.get("attempt_id") or rec.get("row_id")
                       or (gap.get("target_row") or "unknown"),
        "target_kind": rec.get("target_kind"),
        "l2_op": rec.get("operation_type_chosen") or rec.get("l2_op"),
        "l1_process": rec.get("l1_process"),
        "l3_flags": list(v33),
        "verifier_result": cv or rec.get("verdict") or rec.get("status"),
        "residual_class": rc,                       # canonical set
        "residual_summary": summary,
        "did_language_change_next_action": rc in ("vocabulary_gap", "new_channel_or_residual_measure_needed"),
        "evidence_pointer": rec.get("evidence_pointer") or gap.get("target_row") or rec.get("_src"),
        "next_lever": LEVER[rc],
        "next_target_statement": nxt,
        "scoreboard_note": "SHARED KERNEL — not a closure; CLOSED routes to governance and counts only after ratification",
    }


def _rec_from_probe_row(rid: str, rr: dict) -> dict:
    """Adapter (durable, in-primitive — replaces the /tmp throwaway):
    a Rung-1 probe_matrix row's governed verdicts -> the rec schema
    classify() consumes. NEVER fabricates a closure; CLOSED routes to
    governance ratification per the two-scoreboard discipline."""
    gv = {p.get("governance_verdict") for p in rr.get("probes", [])}
    closer = rr.get("intended_closer")
    if "genuine" in gv:
        return {"row_id": rid, "closure_verdict": "CLOSED",
                "target_kind": "proof_closure"}
    if any(p.get("lean_result") == "exact_gap" for p in rr.get("probes", [])):
        return {"row_id": rid, "closure_verdict": "OPEN_GAP_REPORT",
                "gap_report": {"named_candidate_lemmas": [closer],
                               "target_row": rid}}
    if "single_lemma" in gv:
        return {"row_id": rid, "v33_organ_flags": ["single_lemma_exact"]}
    if "axiom_smuggled" in gv:
        return {"row_id": rid, "v33_organ_flags": ["currency_mismatch"]}
    # nothing genuine in-grid: honest = isolated theorem gap to compose
    # (named target), NEVER impossible (canonical set has no such class).
    return {"row_id": rid, "closure_verdict": "OPEN_GAP_REPORT",
            "gap_report": {"named_candidate_lemmas": [closer],
                           "target_row": rid}}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dispatch-json")
    ap.add_argument("--record")
    ap.add_argument("--probe-matrix",
                    help="Rung-1 probe_matrix.json: route EVERY governed "
                         "row through the canonical bridge (durable; "
                         "retires the /tmp adapter)")
    ap.add_argument("--ledger",
                    default="analytics/public/ledgers/residual_to_lever/"
                            "RUNG1_RESIDUAL_LEDGER.jsonl")
    a = ap.parse_args()

    if a.probe_matrix:
        import time
        M = json.loads(Path(a.probe_matrix).read_text())
        rows = {k: v for k, v in M["rows"].items() if "probes" in v}
        led = Path(a.ledger); led.parent.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        recs, by = [], {}
        with led.open("a") as f:
            for rid, rr in rows.items():
                o = classify({**_rec_from_probe_row(rid, rr),
                              "_src": a.probe_matrix})
                assert o["residual_class"] in ALLOWED_RESIDUAL
                row = {"row_id": rid, "tier": rr.get("tier"),
                       "residual_class": o["residual_class"],
                       "next_lever": o["next_lever"],
                       "next_target_statement": o["next_target_statement"],
                       "ts": ts}
                f.write(json.dumps(row) + "\n")
                recs.append(row)
                by[o["residual_class"]] = by.get(o["residual_class"], 0) + 1
        print(json.dumps({
            "ledger": str(led), "rows": len(recs), "by_residual_class": by,
            "every_row_has_lever": all(r["next_lever"] for r in recs),
            "no_impossible_class": "retired_impossible" not in ALLOWED_RESIDUAL,
            "levers": recs}, indent=2, ensure_ascii=False))
        return 0

    src = a.dispatch_json or a.record
    if not src:
        print("need --dispatch-json | --record | --probe-matrix",
              file=sys.stderr); return 2
    rec = json.loads(Path(src).read_text())
    rec.setdefault("_src", src)
    out = classify(rec)
    assert out["residual_class"] in ALLOWED_RESIDUAL, out["residual_class"]
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
