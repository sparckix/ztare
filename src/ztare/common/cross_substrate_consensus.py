"""Cross-substrate CONSENSUS — agreement across independent substrates is trust; disagreement is a
faithfulness-bug detector.

The legs (SymPy/z3/cvc5/Isabelle → Lean) all transport INTO the Lean kernel as the sole arbiter. This adds the
missing peer layer: take the verdicts ≥2 INDEPENDENT substrates produced on the SAME natural-language claim
(each via its own NL→formal translation) and reconcile them:

  • CORROBORATED          — every distinct substrate that ran RATIFIED ⇒ a trust-lift. The independence axis is
                            the SUBSTRATE (different logic + different translation), not the model family — so it
                            catches a faithful-looking-but-mistranslated Lean statement that an independent z3
                            rendering would refuse, which a same-substrate cross-vote cannot.
  • FAITHFULNESS_CONFLICT — ≥1 substrate ratified AND ≥1 refused the SAME claim ⇒ exactly one of the NL→formal
                            translations is UNFAITHFUL. A translation bug localized with NO human. This is the
                            piece the literature does not have: cross-SUBSTRATE disagreement as a faithfulness
                            signal (hammers/portfolios import one substrate's result and re-check in a kernel;
                            none treat substrate disagreement as a verdict).
  • INSUFFICIENT          — <2 distinct substrates ⇒ FAIL-CLOSED (never a silent trust-lift from one engine).
  • UNANIMOUS_REJECT      — every substrate refused.

PURE RECONCILIATION — like `claim_audit`, this re-decides NOTHING; it consumes already-produced `CheckResult`s
via the strict `is_ok` rule and adds NO soundness surface. It cannot make a wrong claim look right — a conflict
is advisory-loud (it flags + surfaces the diagnostics), it never fabricates agreement. Substrate-neutral, in
`common/` next to `governed_verification` + `claim_audit`; NO Lean/z3/Isabelle import.

HONEST SCOPE: the detector only fires where ≥2 substrates can BOTH faithfully express the claim — the decidable
/ arithmetic-policy overlap (LIA, finite enums, threshold rules), i.e. the non-math wedge. For open higher math
(Finset/∑/nonlinear) the SMT/Isabelle translations bail out, so there is no second substrate to disagree with
and the signal degrades to the existing single-substrate cross-vote. It is NOT a general open-math oracle.

  python -m ztare.common.cross_substrate_consensus --selftest
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any

from ztare.common.governed_verification import CheckResult, is_ok


@dataclass
class SubstrateVerdict:
    """One substrate's ALREADY-COMPUTED verdict on the claim, plus a digest of the artifact IT checked.

    `substrate` is the independence key ("lean", "smt_z3", "smt_cvc5", "isabelle") — two verdicts with the same
    key are NOT independent (don't both count). `translation_digest` (sha256 of the formal artifact this
    substrate verified — Lean source / SMT formula / Isabelle theory) records WHICH rendering produced the
    verdict, so a conflict is auditable: the renderings differ by construction (that's why disagreement
    localizes a translation bug), and the digests let a human inspect exactly which two diverged."""
    substrate: str
    result: CheckResult
    translation_digest: str = ""


@dataclass
class ConsensusVerdict:
    claim_nl: str
    status: str                                   # corroborated | faithfulness_conflict | insufficient | unanimous_reject
    agree_ok: "list[str]" = field(default_factory=list)        # substrates that ratified
    agree_reject: "list[str]" = field(default_factory=list)    # substrates that refused
    conflict: "list[dict]" = field(default_factory=list)       # disagreeing (ok, reject) substrate pairs + diagnostics
    n_substrates: int = 0
    reason: str = ""

    @property
    def trust_lift(self) -> bool:
        return self.status == "corroborated"

    @property
    def faithfulness_bug(self) -> bool:
        return self.status == "faithfulness_conflict"

    def to_dict(self) -> "dict[str, Any]":
        return asdict(self)


def cross_substrate_consensus(claim_nl: str, verdicts: "list[SubstrateVerdict]", *,
                              min_substrates: int = 2) -> ConsensusVerdict:
    """Reconcile the verdicts ≥`min_substrates` DISTINCT substrates produced on the SAME claim. FAIL-CLOSED:
    fewer than `min_substrates` distinct substrates ⇒ `insufficient` (a single engine is never a consensus).
    Re-decides nothing; `is_ok` strict-pass means a `None`/string/non-True verdict counts as NOT-ratified
    (never coerced into agreement)."""
    # collapse to one verdict per distinct substrate (a substrate that disagrees with ITSELF — ran twice with
    # different outcomes — is itself a conflict; surface it rather than silently picking one).
    per_sub: "dict[str, list[SubstrateVerdict]]" = {}
    for v in verdicts:
        per_sub.setdefault(v.substrate, []).append(v)
    distinct = list(per_sub)
    if len(distinct) < min_substrates:
        return ConsensusVerdict(claim_nl, "insufficient", n_substrates=len(distinct),
                                reason=f"only {len(distinct)} distinct substrate(s); need ≥{min_substrates} for consensus")

    oks: "list[str]" = []
    rejects: "list[str]" = []
    intra_conflict: "list[dict]" = []
    for sub, vs in per_sub.items():
        sub_ok = [v for v in vs if is_ok(v.result)]
        sub_no = [v for v in vs if not is_ok(v.result)]
        if sub_ok and sub_no:                     # the SAME substrate both ratified and refused → unstable
            intra_conflict.append({"a": sub, "b": sub, "kind": "intra-substrate",
                                   "diagnostics": [sub_ok[0].result.diagnostics, sub_no[0].result.diagnostics]})
            rejects.append(sub)                   # treat an unstable substrate conservatively as not-ratified
        elif sub_ok:
            oks.append(sub)
        else:
            rejects.append(sub)

    oks.sort(); rejects.sort()
    if oks and rejects:
        conflict = intra_conflict + [
            {"a": a, "b": b, "kind": "cross-substrate", "a_ratified": True, "b_ratified": False,
             "diagnostics": [_diag(per_sub, a), _diag(per_sub, b)]}
            for a in oks for b in rejects if a != b]
        return ConsensusVerdict(claim_nl, "faithfulness_conflict", oks, rejects, conflict,
                                n_substrates=len(distinct),
                                reason="substrates disagree on the same claim → exactly one NL→formal "
                                       "translation is unfaithful (a translation bug, localized)")
    if oks:
        return ConsensusVerdict(claim_nl, "corroborated", oks, [], list(intra_conflict),
                                n_substrates=len(distinct),
                                reason=f"corroborated by {len(distinct)} independent substrates ({', '.join(oks)})")
    return ConsensusVerdict(claim_nl, "unanimous_reject", [], rejects, list(intra_conflict),
                            n_substrates=len(distinct), reason="every substrate refused the claim")


def _diag(per_sub: "dict[str, list[SubstrateVerdict]]", sub: str) -> str:
    return (per_sub.get(sub, [{}]) and per_sub[sub][0].result.diagnostics) or ""


def _selftest() -> int:
    fails = []

    def ok(n, c):
        print(f"  [{'PASS' if c else 'FAIL'}] {n}")
        if not c:
            fails.append(n)

    def V(sub, ok_, diag=""):
        return SubstrateVerdict(sub, CheckResult(ok_, diag, sub), translation_digest=f"sha256:{sub}")

    # corroboration: two DISTINCT substrates both ratify
    c = cross_substrate_consensus("CET1≥450", [V("lean", True), V("smt_z3", True)])
    ok("two distinct substrates ratify ⇒ corroborated + trust_lift",
       c.status == "corroborated" and c.trust_lift and c.n_substrates == 2)

    # faithfulness conflict: lean says ok, z3 refuses the SAME claim ⇒ translation bug
    c2 = cross_substrate_consensus("CET1≥450", [V("lean", True, "compiles"), V("smt_z3", False, "z3: sat at cet1Bp=449")])
    ok("disagreement ⇒ faithfulness_conflict + faithfulness_bug",
       c2.status == "faithfulness_conflict" and c2.faithfulness_bug)
    ok("conflict surfaces the disagreeing pair + diagnostics",
       any(d.get("kind") == "cross-substrate" and "z3: sat" in " ".join(d.get("diagnostics", [])) for d in c2.conflict))

    # fail-closed: one substrate is NOT a consensus (even if it ratifies)
    c3 = cross_substrate_consensus("x", [V("lean", True), V("lean", True)])  # same substrate twice
    ok("single distinct substrate ⇒ insufficient (fail-closed, no silent trust)", c3.status == "insufficient")

    # strict is_ok: a non-True verdict counts as NOT ratified (no coercion)
    bad = SubstrateVerdict("smt_z3", CheckResult(False, "unknown", "smt_z3"))
    c4 = cross_substrate_consensus("x", [V("lean", True), bad])
    ok("z3 'unknown'/not-ok vs lean-ok ⇒ conflict (strict is_ok, not coerced to agree)",
       c4.status == "faithfulness_conflict")

    # unanimous reject
    c5 = cross_substrate_consensus("false claim", [V("lean", False), V("smt_z3", False)])
    ok("all refuse ⇒ unanimous_reject", c5.status == "unanimous_reject")

    # intra-substrate instability surfaced (same substrate ratifies AND refuses)
    c6 = cross_substrate_consensus("x", [V("lean", True), V("lean", False), V("smt_z3", True)])
    ok("unstable substrate (ratifies+refuses) treated conservatively + surfaced",
       any(d.get("kind") == "intra-substrate" for d in c6.conflict) and "lean" in c6.agree_reject)

    # three substrates corroborate (the full triangle)
    c7 = cross_substrate_consensus("x", [V("lean", True), V("smt_z3", True), V("isabelle", True)])
    ok("lean+z3+isabelle all ratify ⇒ corroborated by 3", c7.status == "corroborated" and c7.n_substrates == 3)

    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    import sys
    raise SystemExit(_selftest() if "--selftest" in sys.argv else (print(__doc__) or 0))
