"""Decidability router — transport-to-decidability under one kernel trichotomy (2026-06-16).

THE THESIS (the novel, obvious-in-retrospect core). An untrusted claim's validity/faithfulness is an *opinion*
problem only if you stay in one theory. Rice's theorem makes full semantic equivalence of *arbitrary* specs
undecidable — so an LLM judge can only ever opine. But restricted to a decidable THEORY (Presburger/LIA,
real-closed fields, polynomial ideals over ℚ, finite domains, EUF, bitvectors) it is *fully decidable with a
certificate*. So: route each obligation to the theory where it becomes decidable, and every attempt resolves to
a CHECKABLE ARTIFACT — `CERTIFIED` (decided affirmatively: equivalent / ∀-valid / ideal-member, with a
kernel-/solver-checkable basis), `REFUTED` (decided negatively with a concrete, re-verifiable counterexample),
or honestly `OUT_OF_FRAGMENT` (no procedure in the portfolio decides it — the Rice residue, declared, never a
silent guess). Undecidability is the frontier we push outward and *measure*, not a wall.

NOVEL, HONEST METRIC — the **decidable-fraction lift**: on a mixed corpus, what fraction does a *single* best
decision theory resolve to an artifact, vs the *portfolio* router? The lift is the portfolio's added coverage —
the quantitative version of "the agent's job is to find the theory where the claim is decidable." (A skeptic's
"routing to the right tool obviously decides more" is exactly the point: the contribution is the unified
trichotomy + router + governed certificate, which the LLM-judge approach lacks.)

NO FRANKENSTEIN: this is a thin router over the EXISTING decision procedures — `certify_policy_faithfulness`
(z3 LIA/EUF policy equivalence), `nlsat_decide` (z3 RCF/NIA ∀-decision), `groebner_certificate` (polynomial
ideal membership → `linear_combination`). It adds the typed trichotomy + the coverage metric; it does NOT
reimplement any procedure. Cross-theory *transport of a single obligation* (reformulate an OUT_OF_FRAGMENT claim
into a decidable theory) is the next depth — the math transport edges (witness 12/12, Gröbner/SOS deg-≥3) are
the already-measured instances; this router unifies them under one verdict type.

  python -m ztare.leanmill.solver.decidability_router --selftest
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ztare.leanmill.solver.certified_faithfulness import (
    Verdict, certify_policy_faithfulness, certify_policy_refinement)


@dataclass
class Obligation:
    """A typed claim to decide. `kind` selects the decision theory; `payload` is kind-specific."""
    label: str
    kind: str            # "policy_equiv" | "arith_forall" | "poly_identity"
    payload: dict
    note: str = ""


@dataclass
class Decision:
    verdict: Verdict
    theory: "Optional[str]"      # the decision theory that resolved it (None ⇒ OUT_OF_FRAGMENT)
    detail: str
    witness: "Optional[dict]" = None
    certificate: str = ""

    @property
    def decided(self) -> bool:
        return self.verdict in (Verdict.CERTIFIED_EQUIVALENT, Verdict.REFUTED)


# kind → the theory label it routes to (for the coverage/lift accounting)
_KIND_THEORY = {"policy_equiv": "policy_lia_euf", "policy_refine": "policy_lia_euf",
                "arith_forall": "rcf_nia_nlsat", "poly_identity": "poly_ideal_groebner"}


def route(ob: Obligation) -> Decision:
    """Route one obligation to its decision theory and return the trichotomy verdict (an artifact, never an
    opinion). FAIL-CLOSED: any procedure error / unknown ⇒ OUT_OF_FRAGMENT, never a silent decided verdict."""
    k = ob.kind
    if k in ("policy_equiv", "policy_refine"):
        p = ob.payload
        fn = certify_policy_faithfulness if k == "policy_equiv" else certify_policy_refinement
        cert = fn(p["intent"], p["candidate"], p["domain"])
        return Decision(cert.verdict, _KIND_THEORY[k] if cert.verdict is not Verdict.OUT_OF_FRAGMENT else None,
                        cert.detail, cert.witness, cert.certificate)
    if k == "arith_forall":
        try:
            from ztare.common.nlsat_oracle import nlsat_decide
            r = nlsat_decide(ob.payload["goal"], timeout_ms=int(ob.payload.get("timeout_ms", 8000)))
        except Exception as e:  # noqa: BLE001
            return Decision(Verdict.OUT_OF_FRAGMENT, None, f"nlsat error (fail-closed): {e!r}"[:140])
        if r is None:
            return Decision(Verdict.OUT_OF_FRAGMENT, None, "nlsat: unknown / outside the RCF/NIA fragment")
        if r.get("valid"):
            return Decision(Verdict.CERTIFIED_EQUIVALENT, _KIND_THEORY[k],
                            "nlsat: ¬φ UNSAT — the goal is valid on the whole domain (RCF decision)",
                            certificate="z3 nlsat: ¬goal is UNSAT over the real/int closure")
        return Decision(Verdict.REFUTED, _KIND_THEORY[k], "nlsat: concrete counterexample (false as written)",
                        witness=r.get("counterexample"))
    if k == "poly_identity":
        try:
            from ztare.common.groebner_cert import groebner_certificate
            cert = groebner_certificate(ob.payload["hyps"], ob.payload["goal"])
        except Exception as e:  # noqa: BLE001
            return Decision(Verdict.OUT_OF_FRAGMENT, None, f"groebner error (fail-closed): {e!r}"[:140])
        if cert:
            return Decision(Verdict.CERTIFIED_EQUIVALENT, _KIND_THEORY[k],
                            "groebner: goal ∈ ideal⟨hyps⟩ — exact cofactor certificate",
                            certificate=cert.get("linear_combination", "linear_combination <cofactors>"))
        return Decision(Verdict.OUT_OF_FRAGMENT, None,
                        "groebner: no raw-ideal-membership cert (conservative — may need the full basis lift)")
    return Decision(Verdict.OUT_OF_FRAGMENT, None, f"no decision theory wired for kind={k!r}")


def decidable_fraction_lift(corpus: "list[Obligation]") -> dict:
    """The headline metric. For each obligation, route it (portfolio) and also record which single theory could
    have decided it. Compares the PORTFOLIO's decided-fraction to the SINGLE best theory's — the lift is the
    portfolio's added coverage. Every verdict is an artifact; the OUT_OF_FRAGMENT residue is reported honestly."""
    rows, by_theory_decided, portfolio_decided = [], {}, 0
    for ob in corpus:
        d = route(ob)
        rows.append({"label": ob.label, "kind": ob.kind, "verdict": d.verdict.value,
                     "theory": d.theory, "decided": d.decided,
                     "artifact": (d.certificate or d.witness)})
        if d.decided:
            portfolio_decided += 1
            by_theory_decided[d.theory] = by_theory_decided.get(d.theory, 0) + 1
    n = len(corpus)
    single_best = max(by_theory_decided.values()) if by_theory_decided else 0
    single_best_theory = (max(by_theory_decided, key=by_theory_decided.get) if by_theory_decided else None)
    return {
        "n": n,
        "portfolio_decided": portfolio_decided,
        "portfolio_fraction": round(portfolio_decided / n, 4) if n else 0.0,
        "single_best_theory": single_best_theory,
        "single_best_decided": single_best,
        "single_best_fraction": round(single_best / n, 4) if n else 0.0,
        "decidable_fraction_lift": portfolio_decided - single_best,
        "out_of_fragment": n - portfolio_decided,
        "by_theory_decided": by_theory_decided,
        "rows": rows,
        "note": ("decided = CERTIFIED or REFUTED, each a checkable artifact (solver cert / re-verifiable "
                 "counterexample). lift = portfolio added coverage over the single best decision theory on a "
                 "mixed corpus. OUT_OF_FRAGMENT is the honest Rice residue, not a guess."),
    }


# A seed mixed corpus (policy + nonlinear-arith + polynomial), incl. GENUINELY out-of-fragment rows so the
# residue is real and the metric is not gamed. Ground truth in comments; the router must agree.
SEED_CORPUS = [
    # --- policy equivalence (LIA/EUF) ---
    Obligation("policy_reorder_equiv", "policy_equiv",
               {"intent": "Or(And(age >= 18, bal >= 1000), vip == 1)",
                "candidate": "Or(vip == 1, And(bal >= 1000, age >= 18))",
                "domain": {"age": "int", "bal": "int", "vip": "int"}}, "faithful reorder ⇒ CERTIFIED"),
    Obligation("policy_vip_widen_launder", "policy_equiv",
               {"intent": "Or(And(age >= 18, bal >= 1000), vip == 1)",
                "candidate": "Or(And(age >= 18, bal >= 1000), vip >= 1)",
                "domain": {"age": "int", "bal": "int", "vip": "int"}}, "widen ⇒ REFUTED w/ witness"),
    # --- nonlinear real / integer arithmetic (RCF/NIA) ---
    Obligation("rcf_amgm_true", "arith_forall",
               {"goal": "∀ (x y : ℝ), x^2 + y^2 >= 2*x*y"}, "AM-GM ⇒ CERTIFIED (valid)"),
    Obligation("rcf_false_ineq", "arith_forall",
               {"goal": "∀ (x : ℝ), x^2 >= x + 1"}, "false at x=0.5 ⇒ REFUTED w/ counterexample"),
    Obligation("nia_unknown", "arith_forall",
               {"goal": "∀ (a b c n : ℤ), n >= 3 -> a^n + b^n != c^n"}, "Fermat — z3 NIA unknown ⇒ OUT"),
    # --- polynomial ideal membership (Gröbner) ---
    Obligation("poly_cubic_sum", "poly_identity",
               {"hyps": ["a + b + c = 0"], "goal": "a^3 + b^3 + c^3 = 3*a*b*c"}, "ideal member ⇒ CERTIFIED"),
    Obligation("poly_not_member", "poly_identity",
               {"hyps": ["a + b = 1"], "goal": "a^2 + b^2 = 1"}, "NOT in ideal ⇒ OUT (conservative)"),
]


def _selftest() -> int:
    fails: "list[str]" = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    by = {ob.label: route(ob) for ob in SEED_CORPUS}
    ok("policy reorder ⇒ CERTIFIED via policy_lia_euf",
       by["policy_reorder_equiv"].verdict is Verdict.CERTIFIED_EQUIVALENT
       and by["policy_reorder_equiv"].theory == "policy_lia_euf")
    ok("policy widen ⇒ REFUTED w/ witness",
       by["policy_vip_widen_launder"].verdict is Verdict.REFUTED and by["policy_vip_widen_launder"].witness)
    ok("RCF AM-GM ⇒ CERTIFIED via rcf_nia_nlsat",
       by["rcf_amgm_true"].verdict is Verdict.CERTIFIED_EQUIVALENT and by["rcf_amgm_true"].theory == "rcf_nia_nlsat")
    ok("RCF false inequality ⇒ REFUTED w/ counterexample",
       by["rcf_false_ineq"].verdict is Verdict.REFUTED and by["rcf_false_ineq"].witness is not None)
    ok("NIA Fermat ⇒ OUT_OF_FRAGMENT (honest residue)",
       by["nia_unknown"].verdict is Verdict.OUT_OF_FRAGMENT and by["nia_unknown"].theory is None)
    ok("poly cubic-sum ⇒ CERTIFIED via poly_ideal_groebner",
       by["poly_cubic_sum"].verdict is Verdict.CERTIFIED_EQUIVALENT and by["poly_cubic_sum"].theory == "poly_ideal_groebner")
    ok("poly non-member ⇒ OUT (conservative, never a false REFUTED)",
       by["poly_not_member"].verdict is Verdict.OUT_OF_FRAGMENT)

    # IAM/cloud refinement routing (the policy-permissiveness over-grant question, as a faithfulness verdict)
    iam_dom = {"is_admin": "int", "mfa": "int", "resource_prod": "int"}
    safe = route(Obligation("iam_safe", "policy_refine", {
        "intent": "Or(is_admin == 1, And(mfa == 1, resource_prod == 0))",
        "candidate": "And(is_admin == 1, mfa == 1)", "domain": iam_dom}))  # stricter ⇒ no over-grant
    esc = route(Obligation("iam_escalation", "policy_refine", {
        "intent": "Or(is_admin == 1, And(mfa == 1, resource_prod == 0))",
        "candidate": "Or(is_admin == 1, mfa == 1)", "domain": iam_dom}))   # drops resource guard ⇒ over-grants prod
    ok("IAM stricter candidate ⇒ CERTIFIED (no over-grant)", safe.verdict is Verdict.CERTIFIED_EQUIVALENT)
    ok("IAM over-grant ⇒ REFUTED w/ escalation witness (intent denies, candidate allows)",
       esc.verdict is Verdict.REFUTED and (esc.witness or {}).get("intent_decides") is False
       and (esc.witness or {}).get("request", {}).get("resource_prod") == 1)

    m = decidable_fraction_lift(SEED_CORPUS)
    # 5 decided (2 policy + 2 arith + 1 poly), 2 OUT (Fermat, poly non-member); single best theory decides 2.
    ok("portfolio decides 5/7", (m["portfolio_decided"], m["n"]) == (5, 7))
    ok("single best theory decides only 2/7", m["single_best_decided"] == 2)
    ok("decidable-fraction lift = +3 (portfolio over single best)", m["decidable_fraction_lift"] == 3)
    ok("2 honest OUT_OF_FRAGMENT residue", m["out_of_fragment"] == 2)
    print(f"\n  decidable-fraction: portfolio {m['portfolio_decided']}/{m['n']} "
          f"({m['portfolio_fraction']*100:.0f}%) vs single-best {m['single_best_decided']}/{m['n']} "
          f"({m['single_best_fraction']*100:.0f}%) → LIFT +{m['decidable_fraction_lift']}; "
          f"OUT_OF_FRAGMENT {m['out_of_fragment']} (honest residue)")
    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        raise SystemExit(_selftest())
    import json
    print(json.dumps(decidable_fraction_lift(SEED_CORPUS), indent=2, default=str))
