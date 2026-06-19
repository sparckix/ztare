"""DENOTATION-FAITHFULNESS — the honest catch for a BUILT definition (theory-first #123).

THE OPEN PROBLEM. The firewall (`autoformalize.faithfulness_gate`) certifies that a STATEMENT round-trips
to the NL. `detect_def_shells` / `default_def_faithfulness` catch a constant-shell or an LLM-obvious
wrong-object def. None of them answer the genuinely-hard question: when the agent INTRODUCES a new symbol
(a Lean `def` Mathlib lacks — `simpleResidueCoeff`, `IsRationalAntiderivative`), does that symbol actually
DENOTE the intended concept C, or merely some self-consistent decoy C' that satisfies every internal
sanity lemma AND composes with the shelf yet means something subtly different? A(S) (the stated API) under-
determines S. Proving denotation absolutely is NOT possible from inside the system — so we do NOT pretend to.

THE DESIGN (research_isomorphism, 2026-06-19 — deanchored from ITP):
  • Kalman observability rank — a hidden state is uniquely recoverable iff its constraint set is FULL-RANK
    over external outputs. Rank-deficient ⇒ a decoy fits ⇒ the denotation is UNDER-DETERMINED, not certified.
  • Mayers-Yao self-testing / Mostow-Birkhoff rigidity — one EXTREMAL external constraint pins the referent
    up to isomorphism where internal statistics alone cannot.
  • Universal Composability / Revelation Principle — composition with a TRUSTED environment forces the
    declared symbol to equal the true referent.

So we MEASURE pinning instead of asserting denotation, and return a 3-valued verdict that never launders
under-determination as certification:
  • REFUTED       — a declared agreement with a trusted reference is kernel-FALSE (a decoy is caught red-handed).
  • PINNED        — every built def carries ≥1 kernel-VERIFIED external anchor (overlap-agreement with a
                    trusted Mathlib concept, or composition with the proven shelf) → a decoy is ruled out.
  • UNDERDETERMINED — a built def has only self-consistency (no verified external anchor) → an HONEST GAP,
                    surfaced, NOT certified. This is the frontier, reported truthfully.
  • NOT_APPLICABLE — the formalization introduced no new defs (it used Mathlib objects only).

THE ANCHOR CONVENTION (agency upstream / determinism at the boundary — Goldilocks). The AGENT decides which
trusted reference its def extends and STATES the agreement as a first-class `anchor_…`-named theorem in the
theory file (a work item like any sorried API lemma). The KERNEL decides whether that agreement HOLDS
(`verify_anchor_fn` = compile sorry-free + axiom-clean). A wrong def cannot produce a verified overlap
anchor — it simply cannot prove agreement with the established concept — so it can never reach PINNED. The
harness never writes the anchor (that would let it launder); it only verifies and counts.

Pure + injectable: `certify_def_denotation` takes the theory source + injected verify/refute fns (mocks in
tests). `kernel_denotation_verifier` wires the real boundary through `_compile_probe` + `audit_axioms_subset`
(the SAME primitives `composite_ratify` uses — zero new soundness surface).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Callable, Optional

from ztare.leanmill import lean_source as _ls

# the name a built def must agree-with-a-trusted-reference theorem carries; the agent writes these.
ANCHOR_PREFIX = "anchor_"

PINNED = "PINNED"
UNDERDETERMINED = "UNDERDETERMINED"
REFUTED = "REFUTED"
NOT_APPLICABLE = "NOT_APPLICABLE"


def mentions_token(text: str, name: str) -> bool:
    """True iff `name` occurs as a whole Lean identifier (not a substring of a longer ident) in `text` —
    so `… rationalDeriv …` matches `rationalDeriv` but not `rationalDerivQuotient`. The single canonical
    whole-token test reused by the anchor↔def mapping AND the composition-anchor scan (no re-rolled regex)."""
    return re.search(r"(?<![\w'.])" + re.escape(name) + r"(?![\w'.])", text or "") is not None


def certify_def_denotation(theory_src: str, *,
                           verify_anchor_fn: "Callable[[str], bool]",
                           composed_defs: "Optional[set]" = None,
                           refute_anchor_fn: "Optional[Callable[[str], bool]]" = None) -> dict:
    """Score how well the BUILT defs in `theory_src` are pinned to their intended denotation by external,
    kernel-verifiable anchors. Returns the 3-valued verdict + per-def accounting. NO Lean is run here — the
    kernel work is the injected `verify_anchor_fn(anchor_name)->bool` (proven sorry-free + axiom-clean) and
    optional `refute_anchor_fn(anchor_name)->bool` (the deep leg: kernel-proves the agreement is FALSE).
    `composed_defs` = defs that appear in a kernel-RATIFIED composite with the proven shelf — composition is
    itself an external anchor (the UC principle), so those defs are pinned without a separate overlap lemma."""
    defs = _ls.def_names(theory_src)
    composed = set(composed_defs or ())
    if not defs:
        return {"verdict": NOT_APPLICABLE, "defs": [], "per_def": {}, "anchors": [],
                "reason": "no new definitions introduced — denotation-faithfulness N/A (Mathlib objects only)"}

    # classify every anchor theorem once (kernel calls are the cost; do them per anchor, not per def).
    anchor_names = [t for t in _ls.theorem_names(theory_src) if t.startswith(ANCHOR_PREFIX)]
    anchor_stmt = {a: (_ls.extract_signature(theory_src, a) or a) for a in anchor_names}
    anchor_state: "dict[str, str]" = {}
    for a in anchor_names:
        try:
            if refute_anchor_fn is not None and refute_anchor_fn(a):
                anchor_state[a] = REFUTED
                continue
            anchor_state[a] = "verified" if verify_anchor_fn(a) else "pending"
        except Exception:  # noqa: BLE001 — a tooling failure is PENDING (never silently a pass)
            anchor_state[a] = "pending"

    per_def: "dict[str, dict]" = {}
    for d in defs:
        v, p, r = [], [], []
        for a in anchor_names:
            if not mentions_token(anchor_stmt[a], d):
                continue
            st = anchor_state[a]
            (v if st == "verified" else r if st == REFUTED else p).append(a)
        composition = d in composed
        if r:
            status = REFUTED
        elif v or composition:
            status = PINNED
        else:
            status = UNDERDETERMINED
        per_def[d] = {"status": status, "verified_anchors": v, "pending_anchors": p,
                      "refuted_anchors": r, "composition_anchor": composition}

    if any(x["status"] == REFUTED for x in per_def.values()):
        verdict = REFUTED
    elif any(x["status"] == UNDERDETERMINED for x in per_def.values()):
        verdict = UNDERDETERMINED
    else:
        verdict = PINNED
    under = [d for d, x in per_def.items() if x["status"] == UNDERDETERMINED]
    refd = [d for d, x in per_def.items() if x["status"] == REFUTED]
    reason = {
        PINNED: f"all {len(defs)} built def(s) pinned by a verified external anchor",
        UNDERDETERMINED: f"under-determined def(s) (no verified external anchor — HONEST GAP, not certified): {under}",
        REFUTED: f"decoy def(s) caught — declared agreement is kernel-FALSE: {refd}",
    }[verdict]
    return {"verdict": verdict, "defs": defs, "per_def": per_def,
            "anchors": [{"name": a, "state": anchor_state[a]} for a in anchor_names],
            "reason": reason}


def kernel_denotation_verifier(theory_src: str, lean_root: "Path | str", *, timeout_s: int = 180):
    """Wire the real boundary: returns `verify_anchor_fn(anchor_name)->bool` that compiles the theory file
    ONCE (cached) and per-anchor audits axioms — VERIFIED iff the file typechecks AND the anchor's proof is
    sorry-free (no `sorryAx`) and banned-axiom-free. Reuses `_compile_probe` + `audit_axioms_subset` (the
    composite_ratify primitives) so there is no new kernel surface. A sorried/unfinished anchor audits as
    `sorryAx` ⇒ NOT verified ⇒ its def stays UNDERDETERMINED (the honest gap), never laundered to PINNED."""
    from ztare.gates.v33_preflight_risk_detector import _compile_probe
    from ztare.gates.lean_compile_primitives import audit_axioms_subset
    lean_root = Path(lean_root)
    src = theory_src if theory_src.lstrip().startswith("import") else ("import Mathlib\n\n" + theory_src)
    _compiled: "dict[str, bool]" = {}

    def _file_ok() -> bool:
        if "ok" not in _compiled:
            try:
                _compiled["ok"] = _compile_probe(src, lean_root, "Denotation", max(120, timeout_s)) is True
            except Exception:  # noqa: BLE001
                _compiled["ok"] = False
        return _compiled["ok"]

    def verify_anchor_fn(anchor_name: str) -> bool:
        if not _file_ok():
            return False
        try:
            clean, bad, axs = audit_axioms_subset(
                src, anchor_name, lean_root / "_denotation_axiom_audit.lean", lean_root,
                timeout_s=max(120, timeout_s))
        except Exception:  # noqa: BLE001
            return False
        # VERIFIED iff axiom-clean AND not sorried (sorryAx ⇒ the agreement is asserted, not proven).
        return bool(clean and not bad and not any("sorry" in str(a).lower() for a in (axs or [])))

    return verify_anchor_fn


# ───────────────────────────── selftest (hermetic — injected verify/refute, no Lean) ─────────────────────────────
def _selftest() -> int:
    fails = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    theory = (
        "import Mathlib\n\n"
        "noncomputable def simpleResidueCoeff (f : RatFunc K) : K := 0\n\n"
        "def IsRationalAntiderivative (f g : RatFunc K) : Prop := True\n\n"
        "theorem anchor_simpleResidueCoeff_agrees_evalResidue :\n"
        "    ∀ f, simpleResidueCoeff f = Mathlib.residue f := by sorry\n\n"
        "theorem some_api_lemma : True := trivial\n")

    # (1) NOT_APPLICABLE when no defs.
    r0 = certify_def_denotation("import Mathlib\ntheorem t : True := trivial\n",
                                verify_anchor_fn=lambda a: True)
    ok("no-defs ⇒ NOT_APPLICABLE", r0["verdict"] == NOT_APPLICABLE)

    # (2) a built def with a VERIFIED overlap anchor + the other pinned by composition ⇒ PINNED.
    r1 = certify_def_denotation(
        theory, verify_anchor_fn=lambda a: a == "anchor_simpleResidueCoeff_agrees_evalResidue",
        composed_defs={"IsRationalAntiderivative"})
    ok("verified-anchor + composition ⇒ PINNED", r1["verdict"] == PINNED)
    ok("def pinned by composition recorded",
       r1["per_def"]["IsRationalAntiderivative"]["composition_anchor"] is True)
    ok("only the mentioned def gets the anchor (token match)",
       r1["per_def"]["simpleResidueCoeff"]["verified_anchors"] == ["anchor_simpleResidueCoeff_agrees_evalResidue"]
       and r1["per_def"]["IsRationalAntiderivative"]["verified_anchors"] == [])

    # (3) anchor PENDING (sorried / unproven) + no composition ⇒ UNDERDETERMINED (honest gap, NOT certified).
    r2 = certify_def_denotation(theory, verify_anchor_fn=lambda a: False)
    ok("pending anchor + no composition ⇒ UNDERDETERMINED", r2["verdict"] == UNDERDETERMINED)
    ok("UNDERDETERMINED never launders to PINNED",
       r2["per_def"]["simpleResidueCoeff"]["status"] == UNDERDETERMINED)

    # (4) the deep leg: a kernel-FALSE agreement ⇒ REFUTED (decoy caught), dominating PINNED.
    r3 = certify_def_denotation(
        theory, verify_anchor_fn=lambda a: True,
        refute_anchor_fn=lambda a: a == "anchor_simpleResidueCoeff_agrees_evalResidue")
    ok("kernel-false agreement ⇒ REFUTED", r3["verdict"] == REFUTED)
    ok("refuted def flagged with the offending anchor",
       r3["per_def"]["simpleResidueCoeff"]["refuted_anchors"] == ["anchor_simpleResidueCoeff_agrees_evalResidue"])

    # (5) a tooling exception in verify is PENDING, never a silent pass.
    def _boom(a):
        raise RuntimeError("kernel down")
    r4 = certify_def_denotation(theory, verify_anchor_fn=_boom, composed_defs=set())
    ok("verify exception ⇒ UNDERDETERMINED (fail-honest)", r4["verdict"] == UNDERDETERMINED)

    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
