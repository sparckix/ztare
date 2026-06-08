#!/usr/bin/env python3
"""ns_governance_gate.py — v36 NS governance integration.

Forces every live NS attempt through the v35 forward-evidence target_kind
schema and BLOCKS the laundering equivalences the GP-225 line repeatedly
committed:

  consequence exposure   != proof progress
  scalar wrapper         != analytic theorem
  gap isolation          != closure
  route reduction        != closure of the original

This is INTEGRATION GLUE, not new detectors. It reuses:
  - the v35 forward-evidence enum + ledger (single source of target_kind)
  - the v33 anti-laundering organs via lean_proof_gate._run_v33_anti_laundering
    (vacuity / gold-name / single-exact / indirect-leakage / currency)
  - validate_forward_evidence for the emitted row

NS attempt vocabulary -> the strict 6-enum:
  prove_source_obligation     -> proof_closure
  expose_consequence          -> consequence_exposure
  route_downstream_subgoal    -> route_reduction
  isolate_missing_atom        -> gap_isolation
  falsify_bad_bridge          -> falsifier
  apparatus/governance audit  -> apparatus_audit

Rule: ONLY ns_kind=prove_source_obligation may emit target_kind=
proof_closure, and ONLY if the Lean evidence compiles sorry/axiom-clean
AND no v33 organ confirms a false-closure sub-mode. Anything else is
recorded as its honest non-closure kind. A claim that says
closed/Clay/solved with a non-proof_closure kind is BLOCKED (mush).

Usage:
  ns_governance_gate.py --claim "..." --ns-kind expose_consequence \
      --evidence path/to/artifact [--lean ztare_proofs/.../X.lean] \
      [--emit]            # append the forward-evidence row (pending_ratification)
"""
from __future__ import annotations

import argparse
import datetime
import importlib.util
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
FE_LEDGER = REPO / "analytics/public/ledgers/forward_evidence/forward_evidence_ledger.jsonl"
LPG = REPO / "src/ztare/gates/lean_proof_gate.py"

NS_KIND_MAP = {
    "prove_source_obligation": "proof_closure",
    "expose_consequence": "consequence_exposure",
    "route_downstream_subgoal": "route_reduction",
    "isolate_missing_atom": "gap_isolation",
    "falsify_bad_bridge": "falsifier",
    "apparatus_audit": "apparatus_audit",
}
MUSH_RE = re.compile(r"\b(clos(e|ed|ure)|clay|solv(e|ed)|q\.?e\.?d)\b", re.I)


def _run_v33(lean_path: Path) -> dict:
    """Reuse the existing v33 spine — never reimplement organs here."""
    spec = importlib.util.spec_from_file_location("lpg_v36", LPG)
    m = importlib.util.module_from_spec(spec)
    sys.modules["lpg_v36"] = m
    spec.loader.exec_module(m)  # type: ignore[attr-defined]
    src = lean_path.read_text(errors="replace")
    return m.run_anti_laundering_kernel(
        src, lean_path, REPO / "ztare_workspace" / "proofs", deep_verify=False)


def adjudicate(claim: str, ns_kind: str, evidence: str,
               lean: str | None) -> dict:
    blocks: list[str] = []
    if ns_kind not in NS_KIND_MAP:
        return {"verdict": "REJECT",
                "reason": f"ns_kind '{ns_kind}' not in {sorted(NS_KIND_MAP)}"}
    target_kind = NS_KIND_MAP[ns_kind]

    # Mush block: closure language requires proof_closure.
    if target_kind != "proof_closure" and MUSH_RE.search(claim or ""):
        blocks.append(
            f"claim uses closure/Clay/solved language but ns_kind='{ns_kind}' "
            f"-> target_kind='{target_kind}' is NOT a closure. Restate the "
            f"claim as {target_kind} (consequence/gap/route), or change kind.")

    result = "inconclusive"
    if target_kind == "proof_closure":
        if not lean:
            blocks.append("proof_closure requires a Lean evidence file "
                          "(--lean); none given.")
        else:
            lp = REPO / lean
            if not lp.exists():
                blocks.append(f"Lean evidence path missing: {lean}")
            else:
                v33 = _run_v33(lp)
                if not v33.get("passed", False):
                    blocks.append(
                        "v33 anti-laundering confirms a false-closure "
                        f"sub-mode {v33.get('flags')} -> this is NOT a "
                        "proof_closure (downgrade to route_reduction / "
                        "gap_isolation and restate honestly).")
                else:
                    result = "achieved"
    else:
        # honest non-closure results
        result = {"consequence_exposure": "achieved",
                  "route_reduction": "achieved",
                  "gap_isolation": "achieved",
                  "falsifier": "achieved",
                  "apparatus_audit": "achieved"}.get(target_kind, "partial")

    if not (REPO / evidence).exists():
        blocks.append(f"evidence_pointer path missing: {evidence}")

    return {"verdict": "BLOCK" if blocks else "PASS",
            "target_kind": target_kind, "result": result,
            "blocks": blocks}


def emit_row(claim, target_kind, evidence, lean, result) -> str:
    rows = [json.loads(l) for l in FE_LEDGER.read_text().splitlines() if l.strip()] \
        if FE_LEDGER.exists() else []
    today = datetime.date.today().isoformat()
    n = sum(1 for r in rows if r.get("row_id", "").startswith(f"FE-{today}")) + 1
    rid = f"FE-{today}-{n:02d}"
    row = {
        "row_id": rid, "claim": claim, "target_kind": target_kind,
        "source_artifact": lean or evidence,
        "attempt_trace": lean or "none", "result": result,
        "evidence_pointer": evidence,
        "anti_pattern_audit": ("v33 organs run via ns_governance_gate; "
                               "no false-closure sub-mode confirmed"
                               if target_kind == "proof_closure"
                               else "clean (non-closure kind; no closure claimed)"),
        "author_agent": "claude:ns_governance_gate_session",
        "ratifier_identity": "pending", "status": "pending_ratification",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    with FE_LEDGER.open("a") as f:
        f.write(json.dumps(row) + "\n")
    return rid


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--claim", required=True)
    ap.add_argument("--ns-kind", required=True)
    ap.add_argument("--evidence", required=True)
    ap.add_argument("--lean")
    ap.add_argument("--emit", action="store_true")
    a = ap.parse_args()
    r = adjudicate(a.claim, a.ns_kind, a.evidence, a.lean)
    print(json.dumps(r, indent=2))
    if r["verdict"] != "PASS":
        print("  -> NOT emitted (fix the blocks; do not relaunder)")
        return 1
    if a.emit:
        rid = emit_row(a.claim, r["target_kind"], a.evidence, a.lean, r["result"])
        print(f"  -> emitted forward-evidence row {rid} "
              f"(status=pending_ratification — needs independent ratifier)")
    else:
        print("  -> PASS (dry-run; pass --emit to append the forward-evidence row)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
