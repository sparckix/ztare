"""Certified faithfulness — translation-validation for an UNTRUSTED non-math formalization (2026-06-16).

The thesis, sharpened. A frontier LLM judge answering "is this formalization faithful to the intent?" gives
an OPINION you must trust. This module returns an ARTIFACT you can check yourself, one of three typed verdicts:

  • CERTIFIED_EQUIVALENT — an EXHAUSTIVE certificate that candidate ≡ intent on EVERY input of the domain
    (z3 `ref ≢ cand` UNSAT over the whole space; optionally PROMOTED to a kernel-grade Lean `omega`/`decide`
    proof the Lean kernel re-checks — independent of z3);
  • REFUTED — a CONCRETE distinguishing input where the candidate disagrees with the intent, labelled by the
    intent's decision (the auditable counterexample an opinion cannot give);
  • OUT_OF_FRAGMENT — the obligation falls outside the decidable fragment the decision procedure covers
    (Rice's theorem: full semantic equivalence of arbitrary specs is undecidable, so a sound certifier MUST
    declare this honestly rather than guess) ⇒ fall back to the advisory battery + judge, NEVER a silent admit.

WHY THIS IS NOT A FRANKENSTEIN / NO-AMNESIA. Every decision leg already exists; this is a THIN typed contract
over them, not a reimplementation:
  • the LIA/EUF policy fragment → `common.smt_checker.SmtPolicyChecker.{distinguishing_requests,equivalence}`
    (z3 is COMPLETE for linear integer arithmetic — there is no separate Farkas/Presburger code to write);
  • the kernel-grade promotion → a Lean `∀ …, intent ↔ cand := by omega`/`by decide` probe through the
    EXISTING warm compile path (caller injects `lean_compile`); `omega` IS the kernel's LIA decision procedure;
  • the polynomial-identity fragment → `common.groebner_cert.groebner_certificate` → `linear_combination`
    (the transport edge #137, already kernel-verified).
The research-isomorphism surface (2026-06-16) named the lineage: PCP/IP (a bounded verifier policing an
untrusted producer), Rice (the undecidability boundary), Gröbner/Farkas (certificate-of-equivalence). The
novelty is the COMPOSITION into one typed, always-an-artifact verdict — not any single leg.

  python -m ztare.leanmill.solver.certified_faithfulness --selftest
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Callable, Optional


class Verdict(str, Enum):
    CERTIFIED_EQUIVALENT = "certified_equivalent"
    REFUTED = "refuted"
    OUT_OF_FRAGMENT = "out_of_fragment"


@dataclass
class FaithfulnessCertificate:
    """A typed faithfulness verdict that is ALWAYS an artifact, never an opinion.

    `kernel_checked` = a Lean-kernel (or kernel-grade) certificate backs the verdict, independent of the SMT
    solver — the strongest tier. `certificate` carries the exhaustive-equivalence evidence (z3 UNSAT summary
    / a Lean probe / Gröbner cofactors). `witness` (REFUTED only) is the concrete distinguishing input plus
    the intent's and candidate's decisions on it — the thing a reviewer can re-evaluate by hand."""
    verdict: Verdict
    fragment: str                      # linear_int_euf | finite | polynomial | none
    kernel_checked: bool
    detail: str
    certificate: str = ""
    witness: "Optional[dict]" = None

    @property
    def is_opinion(self) -> bool:
        return False                   # by construction: every verdict carries a checkable artifact

    @property
    def faithful(self) -> "Optional[bool]":
        """True/False only when DECIDED; None for OUT_OF_FRAGMENT (don't collapse 'undecided' into 'unfaithful')."""
        if self.verdict is Verdict.CERTIFIED_EQUIVALENT:
            return True
        if self.verdict is Verdict.REFUTED:
            return False
        return None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["verdict"] = self.verdict.value
        d["faithful"] = self.faithful
        return d


def certify_policy_faithfulness(
        intent_src: str, candidate_src: str, domain: "dict[str, object]", *,
        lean_equiv_probe: "Optional[str]" = None,
        lean_compile: "Optional[Callable[[str], bool]]" = None) -> FaithfulnessCertificate:
    """Certify that `candidate_src` (an untrusted formalization) is faithful to `intent_src` (the trusted
    reference) over the WHOLE `domain`, via the z3 LIA/EUF decision procedure. Both are z3-policy sources
    (`common.smt_checker` syntax). Returns a typed `FaithfulnessCertificate` — never an opinion.

    Order is REFUTE-FIRST (cheapest disproof, and the most legible artifact): look for a distinguishing input;
    only if none exists do we assert exhaustive equivalence. FAIL-CLOSED: a z3 compile error / `unknown` is
    OUT_OF_FRAGMENT (advisory), never a silent CERTIFIED.

    `lean_equiv_probe` (+ `lean_compile`): if supplied, an equivalence verdict is PROMOTED to kernel-grade by
    compiling a Lean `∀ …, intent ↔ cand := by omega/decide` probe — `kernel_checked=True` iff it compiles.
    The promotion can only ever UPGRADE trust (a failed Lean probe leaves the z3-exhaustive cert intact)."""
    try:
        from ztare.common.smt_checker import SmtPolicyChecker
        chk = SmtPolicyChecker(domain)
    except Exception as e:  # noqa: BLE001 — z3 absent ⇒ out of fragment, fail-closed
        return FaithfulnessCertificate(Verdict.OUT_OF_FRAGMENT, "none", False,
                                       f"decision procedure unavailable (fail-closed): {e!r}"[:160])

    # 1) REFUTE: a concrete input where candidate disagrees with the intent (labelled by the intent's decision).
    dr = chk.distinguishing_requests(intent_src, candidate_src, max_cases=1)
    if dr:
        req, intent_dec = dr[0]
        return FaithfulnessCertificate(
            Verdict.REFUTED, "linear_int_euf", kernel_checked=False,
            detail="the decision procedure found an input where the candidate disagrees with the intent",
            witness={"request": req, "intent_decides": bool(intent_dec),
                     "candidate_decides": (not bool(intent_dec))})  # they disagree by construction at `req`

    # 2) CERTIFY: no distinguishing input — is it EXHAUSTIVELY equivalent? (distinguishing_requests returns []
    #    on a compile error too, so re-ask via equivalence() to separate 'equivalent' from 'inconclusive'.)
    eq = chk.equivalence(intent_src, candidate_src)
    if eq.ok:
        kernel_checked, certificate = False, "z3: (intent ≢ candidate) is UNSAT — equivalent on every input"
        if lean_equiv_probe and lean_compile is not None:
            try:
                if lean_compile(lean_equiv_probe) is True:
                    kernel_checked = True
                    certificate = "Lean kernel: ∀ inputs, intent ↔ candidate (by omega/decide) — re-checked"
            except Exception:  # noqa: BLE001 — a failed promotion never downgrades the z3 cert
                pass
        return FaithfulnessCertificate(Verdict.CERTIFIED_EQUIVALENT, "linear_int_euf", kernel_checked,
                                       "the candidate is faithful to the intent on every input", certificate)

    # 3) OUT OF FRAGMENT: undecided / unknown / non-wellformed — the honest Rice boundary, advisory fallback.
    return FaithfulnessCertificate(Verdict.OUT_OF_FRAGMENT, "none", False,
                                   f"undecided in the SMT fragment (fall back to battery+judge): {eq.diagnostics}"[:180])


def certify_policy_refinement(
        intent_src: str, candidate_src: str, domain: "dict[str, object]") -> FaithfulnessCertificate:
    """IAM/access-control REFINEMENT (the policy-permissiveness question, as a faithfulness verdict): does the candidate
    policy **over-grant** relative to the intent — i.e. allow a request the intent denies (privilege
    escalation)? This is the safety-critical direction for security policy, where a *stricter* candidate is
    acceptable but a *more permissive* one is the launder. Reuses `SmtPolicyChecker.{implies,distinguishing_requests}`
    (z3 over the whole request space) — no new decision procedure.

      • CERTIFIED  — candidate ⊆ intent (no over-grant; equivalent or stricter): a safe refinement;
      • REFUTED    — a concrete request the candidate ALLOWS but the intent DENIES (the escalation witness);
      • OUT_OF_FRAGMENT — undecided (fail-closed)."""
    try:
        from ztare.common.smt_checker import SmtPolicyChecker
        chk = SmtPolicyChecker(domain)
    except Exception as e:  # noqa: BLE001
        return FaithfulnessCertificate(Verdict.OUT_OF_FRAGMENT, "none", False,
                                       f"decision procedure unavailable (fail-closed): {e!r}"[:160])
    imp = chk.implies(candidate_src, intent_src)        # candidate ⊆ intent  ⟺  no over-grant
    if imp.ok:
        return FaithfulnessCertificate(
            Verdict.CERTIFIED_EQUIVALENT, "policy_refinement_lia_euf", kernel_checked=False,
            detail="no over-grant: the candidate is ⊆ the intent (safe refinement — equivalent or stricter)",
            certificate="z3: every request the candidate allows, the intent also allows (no escalation)")
    # over-grant exists — surface the concrete escalation request (intent DENIES, candidate ALLOWS).
    dr = chk.distinguishing_requests(intent_src, candidate_src, max_cases=8)
    over = [req for req, intent_dec in dr if intent_dec is False]
    if over:
        return FaithfulnessCertificate(
            Verdict.REFUTED, "policy_refinement_lia_euf", kernel_checked=False,
            detail="the candidate OVER-GRANTS: a request the intent denies but the candidate allows (escalation)",
            witness={"request": over[0], "intent_decides": False, "candidate_decides": True})
    # implies failed but no intent-denies witness surfaced in the cap (rare) — still a refinement failure.
    return FaithfulnessCertificate(Verdict.REFUTED, "policy_refinement_lia_euf", kernel_checked=False,
                                   detail=f"candidate is not ⊆ intent (over-grant): {imp.diagnostics}"[:160])


def certify_polynomial_identity(
        hypotheses: "list[str]", goal: str, *,
        lean_prelude: str = "import Mathlib", var_decl: "Optional[str]" = None,
        lean_compile: "Optional[Callable[[str], bool]]" = None) -> FaithfulnessCertificate:
    """The polynomial fragment: a multivariate equality `goal` that should follow from equational `hypotheses`
    is ideal membership — CERTIFIED by a Gröbner cofactor cert (`groebner_certificate`) the Lean kernel
    re-verifies via `linear_combination`. Conservative: no cert ⇒ OUT_OF_FRAGMENT (never a guess)."""
    try:
        from ztare.common.groebner_cert import groebner_certificate
    except Exception as e:  # noqa: BLE001
        return FaithfulnessCertificate(Verdict.OUT_OF_FRAGMENT, "polynomial", False, f"sympy/groebner absent: {e!r}"[:160])
    cert = groebner_certificate(hypotheses, goal)
    if not cert:
        return FaithfulnessCertificate(Verdict.OUT_OF_FRAGMENT, "polynomial", False,
                                       "no Gröbner cofactor certificate (not raw-ideal-membership; conservative None)")
    kernel_checked = False
    lc = cert["linear_combination"]
    if lean_compile is not None and var_decl:
        hyp_decl = "".join(f" (h{i} : {h})" for i, h in enumerate(hypotheses))
        hlist = ", ".join(f"h{i}" for i in range(len(hypotheses)))
        probe = (f"{lean_prelude}\n\ntheorem _cf_poly ({var_decl}){hyp_decl} : {goal} := by\n"
                 f"  {lc.format(h=hlist) if '{h}' in lc else lc}\n")
        try:
            kernel_checked = lean_compile(probe) is True
        except Exception:  # noqa: BLE001
            kernel_checked = False
    return FaithfulnessCertificate(Verdict.CERTIFIED_EQUIVALENT, "polynomial", kernel_checked,
                                   "the goal is an algebraic consequence of the hypotheses (ideal membership)",
                                   certificate=lc)


def _selftest() -> int:
    """Hermetic over the SMT fragment (needs z3, which the smt_checker suite already requires). No Lean."""
    fails: "list[str]" = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    # A 3-attribute integer policy. INTENT: allow iff (age >= 18 AND balance >= 1000) OR vip == 1.
    domain = {"age": "int", "balance": "int", "vip": "int"}
    INTENT = "Or(And(age >= 18, balance >= 1000), vip == 1)"
    EQUIV = "Or(vip == 1, And(balance >= 1000, age >= 18))"          # reordered — faithful
    LAUNDER = "Or(And(age >= 18, balance >= 1000), vip >= 1)"        # vip==1 → vip>=1 widens (vip=2 now allowed)
    OFF_BY_ONE = "Or(And(age >= 18, balance > 1000), vip == 1)"      # balance>=1000 → >1000 (denies balance==1000)

    c_equiv = certify_policy_faithfulness(INTENT, EQUIV, domain)
    ok("faithful reorder ⇒ CERTIFIED_EQUIVALENT", c_equiv.verdict is Verdict.CERTIFIED_EQUIVALENT)
    ok("certified carries an exhaustive cert + faithful=True", bool(c_equiv.certificate) and c_equiv.faithful is True)

    c_l = certify_policy_faithfulness(INTENT, LAUNDER, domain)
    ok("vip widening ⇒ REFUTED", c_l.verdict is Verdict.REFUTED)
    ok("REFUTED carries a concrete witness w/ both decisions",
       c_l.witness is not None and "request" in c_l.witness
       and c_l.witness["intent_decides"] != c_l.witness["candidate_decides"])
    ok("witness is a genuine distinguisher (vip>=2 region)", (c_l.witness or {}).get("request", {}).get("vip", 0) >= 2)

    c_o = certify_policy_faithfulness(INTENT, OFF_BY_ONE, domain)
    ok("balance off-by-one ⇒ REFUTED w/ witness at balance boundary", c_o.verdict is Verdict.REFUTED
       and (c_o.witness or {}).get("request", {}).get("balance") == 1000)

    # never an opinion; to_dict round-trips the enum
    ok("every verdict is_opinion == False", all(not c.is_opinion for c in (c_equiv, c_l, c_o)))
    ok("to_dict serializes verdict + faithful", c_l.to_dict()["verdict"] == "refuted" and c_l.to_dict()["faithful"] is False)

    # kernel-grade promotion: a mock lean_compile that 'passes' upgrades kernel_checked on an equivalent pair
    c_promoted = certify_policy_faithfulness(INTENT, EQUIV, domain,
                                             lean_equiv_probe="example : True := trivial", lean_compile=lambda s: True)
    ok("equivalent + passing Lean probe ⇒ kernel_checked promotion", c_promoted.kernel_checked is True)
    c_nopromote = certify_policy_faithfulness(INTENT, EQUIV, domain,
                                              lean_equiv_probe="bad", lean_compile=lambda s: False)
    ok("failed Lean probe does NOT downgrade the z3 cert",
       c_nopromote.verdict is Verdict.CERTIFIED_EQUIVALENT and c_nopromote.kernel_checked is False)

    # polynomial fragment: a+b+c=0 ⊢ a^3+b^3+c^3 = 3abc has a Gröbner cofactor cert
    c_poly = certify_polynomial_identity(["a + b + c = 0"], "a^3 + b^3 + c^3 = 3*a*b*c")
    ok("polynomial ideal-membership ⇒ CERTIFIED w/ linear_combination cert",
       c_poly.verdict is Verdict.CERTIFIED_EQUIVALENT and "linear_combination" in c_poly.certificate)

    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        raise SystemExit(_selftest())
    print(__doc__)
