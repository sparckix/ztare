"""Extra anti-laundering organs surfaced by the constraint-isomorphism engine (default OFF).

The engine, run on the governance detection ceiling ("a novel cheat passes the fixed v33 checks"),
surfaced two cross-field detection structures. Both are ADDITIVE organs for the v33 stack, gated by
`ZTARE_LEANMILL_EXTRA_ORGANS=1`, FAIL-OPEN (tooling-inconclusive ⇒ pass; only a CONFIRMED signal
flags), and ADVISORY until their efficacy is shown (catch known laundering WITHOUT false-positives
on genuine proofs — positive AND negative controls through the same path).

  A. MDL / generativity (Algorithmic Information Theory):
     A genuine proof DERIVES (carries generative information about the claim); a laundered one is a
     LOOKUP — a single citation of one too-strong named lemma that closes a non-trivial goal. Flag
     when the proof's description length is anomalously low relative to the statement AND the proof
     is a lone named-lemma citation. (Distinct mechanism from the lexical single-lemma organ: the
     MDL RATIO, not just the shape.)

  B. Schwartz-Zippel randomized differential probe (Algebraic Complexity):
     A fixed check battery is gameable; randomized probes are not. Perturb a numeric literal in the
     statement — the variant is almost surely FALSE — and re-verify the SAME proof against it. A
     genuine proof closes ONLY the real statement; a vacuous / assume-the-conclusion / inconsistent-
     context proof closes the false variant too. Re-verify via an injected `verify_fn` (the worker's
     real kernel compile; a mock in tests). Fail-open when there is no perturbable literal.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Callable, Optional

from ztare.leanmill.solver.family_lemma_library import lean_description_length

# A lone-citation proof: `by exact foo`, `by apply Foo.bar`, `exact mul_assoc` — ANY identifier
# (adversarial review 2026-06-04: was uppercase-anchored, missing the dominant lowercase snake_case
# Mathlib form). Optional surrounding parens around the cited term are tolerated.
_LONE_CITATION = re.compile(
    r"^\s*(?:by\s+)?(?:exact\??|apply|refine)\s+@?\(?\s*([A-Za-z_][\w'.]*)\s*\)?\s*$")
_COMMENT_BLOCK = re.compile(r"/-.*?-/", re.S)
_COMMENT_LINE = re.compile(r"--[^\n]*")
# SZ targets ONLY a numeral that is the RHS of an equality (`= 66` / `≡ 66`). Perturbing those is
# almost-surely falsifying; numerals in inequalities (`≥ 5`), type indices (`Fin 7`), or decorative
# positions are SKIPPED — perturbing them stays true and would false-flag a genuine proof.
_EQ_NUMERAL = re.compile(r"(?:==|=|≡)\s*(\d+)(?![\w.])")


def _normalize_tactic(body: str) -> str:
    """Strip comments / trailing `;` so a lone citation can't be hidden behind surface syntax
    (adversarial review: `by exact Foo -- note` / `by exact Foo;` evaded the `$` anchor)."""
    s = _COMMENT_BLOCK.sub(" ", body or "")
    s = _COMMENT_LINE.sub(" ", s)
    return s.strip().rstrip(";").strip()


@dataclass
class OrganFinding:
    organ: str
    flagged: bool
    confirmed_violation: bool   # True only on a CONFIRMED signal (fail-CLOSED); else advisory/fail-open
    reason: str


def mdl_generativity(proof_text: str, statement: str, *, min_ratio: float = 0.25) -> OrganFinding:
    """Organ A. Flag a closure whose proof carries too little generative information for its claim:
    a lone named-lemma citation whose description length is < `min_ratio` of the statement's. A
    genuine multi-step proof, or a tactic-automation proof (`omega`/`simp`/`decide`), is NOT flagged."""
    body = _normalize_tactic((proof_text or "").strip())
    if not body:
        return OrganFinding("mdl_generativity", False, False, "empty proof — not this organ's call")
    lone = _LONE_CITATION.match(body)
    if not lone:
        return OrganFinding("mdl_generativity", False, False, "proof is not a lone named-lemma citation")
    proof_dl = lean_description_length(body)
    stmt_dl = lean_description_length(statement or "")
    ratio = proof_dl / max(1, stmt_dl)
    if stmt_dl >= 8 and ratio < min_ratio:
        return OrganFinding(
            "mdl_generativity", True, False,  # ADVISORY ONLY — see caveat; never auto-reject
            f"lone citation `{lone.group(1)}` (proof_dl={proof_dl}) closes a complex goal "
            f"(stmt_dl={stmt_dl}, ratio={ratio:.2f}<{min_ratio}) — too-strong-lemma LOOKUP candidate. "
            "CAVEAT (review, do NOT auto-reject): this is ALSO the shape of naming the single CORRECT "
            "lemma (a legitimate Mathlib idiom); the MDL ratio alone cannot separate the two")
    return OrganFinding("mdl_generativity", False, False,
                        f"generativity ok (ratio={ratio:.2f})")


def randomized_differential_probe(statement: str, proof_text: str,
                                  verify_fn: "Callable[[str, str], bool]",
                                  *, k: int = 3) -> OrganFinding:
    """Organ B. Perturb a numeric literal in `statement` (the variant is almost surely false) and
    re-verify the SAME `proof_text` against it via `verify_fn(perturbed_statement, proof) -> bool`.
    If the proof closes any false variant ⇒ CONFIRMED violation (fail-CLOSED). No numeral / verifier
    inconclusive ⇒ fail-open."""
    nums = list(_EQ_NUMERAL.finditer(statement or ""))   # equality-RHS literals only (sound to perturb)
    if not nums:
        return OrganFinding("sz_differential", False, False,
                            "no equality-RHS literal to perturb — fail-open (inequalities/indices skipped)")
    decided = 0
    errored = 0
    for m in nums[:k]:
        orig = int(m.group(1))
        # Perturb BOTH directions; a load-bearing equality literal makes BOTH variants false, so a
        # genuine proof closes NEITHER. Flag only if the proof closes BOTH ⇒ the literal does not pin
        # truth in this proof (vacuity / assumes-conclusion). Belt-and-suspenders over the eq-restriction.
        results = []
        for pv in (orig + 1, orig - 1):
            if pv < 0:
                continue
            perturbed = statement[:m.start(1)] + str(pv) + statement[m.end(1):]
            if perturbed == statement:
                continue
            try:
                results.append(bool(verify_fn(perturbed, proof_text)))
            except Exception:
                errored += 1   # inconclusive on this direction
        if len(results) >= 1:
            decided += 1
        if len(results) >= 2 and all(results):
            return OrganFinding(
                "sz_differential", True, False,   # ADVISORY — never auto-reject
                f"proof closes BOTH perturbed variants of an equality literal ({orig}±1) — the literal "
                "is not load-bearing in the proof: vacuity / assumes-conclusion candidate. REVIEW only "
                "(residual FP: a hypothesis-equality whose perturbation makes the context inconsistent).")
    if decided == 0:
        why = (f"inconclusive: {errored} probe(s) errored (e.g. timeout) and were not evaluated — fail-open"
               if errored else "no probe was verifier-decidable — fail-open")
        return OrganFinding("sz_differential", False, False, why)
    note = f" ({errored} other probe(s) errored, not evaluated)" if errored else ""
    return OrganFinding("sz_differential", False, False,
                        f"survived {decided} two-sided equality-literal differential probe(s){note}")


def run_governance_organs(proof_text: str, statement: str,
                          verify_fn: "Optional[Callable[[str, str], bool]]" = None) -> "list[OrganFinding]":
    """Run the extra organs IFF ZTARE_LEANMILL_EXTRA_ORGANS=1 (default off ⇒ []). The SZ organ runs
    only when a verify_fn is supplied. Both organs are ADVISORY (`confirmed_violation` always False
    in this version): they SURFACE laundering candidates for review, they never auto-reject — the
    kernel + the existing fail-closed v33 organs remain the sole arbiters (per §3b: do not hard-gate
    an unvalidated organ). Promotion to fail-closed (e.g. SZ on a pure-equality perturbation, high-
    confidence MDL) comes only after the efficacy test + adversarial review."""
    if os.environ.get("ZTARE_LEANMILL_EXTRA_ORGANS") != "1":
        return []
    out = [mdl_generativity(proof_text, statement)]
    if verify_fn is not None:
        out.append(randomized_differential_probe(statement, proof_text, verify_fn))
    return out


def _self_test() -> int:
    fails = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    cplx = "theorem t (n : ℕ) (h : 0 < n) : n * (n + 1) / 2 = Nat.choose (n + 1) 2"
    # A — lone citation of a complex goal → flagged (lookup); a real derivation / tactic-automation → not.
    ok("mdl_flags_lone_citation_lookup",
       mdl_generativity("by exact Nat.triangle_eq_choose", cplx).flagged)
    # REGRESSION (adversarial review): lowercase snake_case (the dominant Mathlib form) must also flag.
    ok("mdl_flags_lowercase_snake_case", mdl_generativity("by exact triangle_eq_choose_lemma", cplx).flagged)
    # REGRESSION: surface-syntax evasion (trailing comment / parens / semicolon) must not defeat it.
    ok("mdl_catches_comment_evasion", mdl_generativity("by exact some_strong_lemma -- the lemma", cplx).flagged)
    ok("mdl_catches_paren_semicolon", mdl_generativity("by exact (some_strong_lemma);", cplx).flagged)
    ok("mdl_clears_multistep_proof",
       not mdl_generativity("by\n  induction n with\n  | zero => simp\n  | succ k ih => rw [ih]; ring", cplx).flagged)
    ok("mdl_clears_tactic_automation", not mdl_generativity("by omega", cplx).flagged)
    ok("mdl_clears_lone_citation_on_trivial_goal",
       not mdl_generativity("by exact Foo", "theorem t : True").flagged)

    # B — Schwartz-Zippel: a proof that closes a false numeric variant is a CONFIRMED violation.
    stmt = "theorem v : T 11 = 66"
    def verify_closes_anything(perturbed, proof):   # a vacuous/assume-conclusion proof: closes everything
        return True
    def verify_value_specific(perturbed, proof):    # a genuine proof: closes ONLY the real statement
        return perturbed == stmt
    bad = randomized_differential_probe(stmt, "by rfl", verify_closes_anything)
    ok("sz_flags_proof_that_closes_variant_ADVISORY",
       bad.flagged and not bad.confirmed_violation)   # advisory only — never auto-reject (inequality safety)
    good = randomized_differential_probe(stmt, "by decide", verify_value_specific)
    ok("sz_clears_value_specific_proof", not good.flagged)
    ok("sz_fail_open_no_literal",
       not randomized_differential_probe("theorem v : P → P", "by id", verify_closes_anything).flagged)
    # REGRESSION (adversarial review): an INEQUALITY literal (`≥ 5`) is NOT an equality RHS → skipped
    # (perturbing it stays true and would false-flag a genuine proof). Must fail-open, not flag.
    ineq = "theorem t (n : Nat) (h : n ≥ 5) : n ≥ 3"
    ok("sz_inequality_fail_open_no_false_flag",
       not randomized_differential_probe(ineq, "by omega", verify_closes_anything).flagged)
    # REGRESSION: an errored probe is reported as INCONCLUSIVE, never as "survived".
    def verify_raises(perturbed, proof):
        raise TimeoutError("kernel timeout on the harder variant")
    er = randomized_differential_probe(stmt, "by launder", verify_raises)
    ok("sz_errored_reported_inconclusive", not er.flagged and "inconclusive" in er.reason)

    # gating: default off → no organs run; on → they run
    ok("organs_default_off", run_governance_organs("by exact Foo", cplx) == [])
    os.environ["ZTARE_LEANMILL_EXTRA_ORGANS"] = "1"
    try:
        res = run_governance_organs("by exact Foo", cplx, verify_fn=verify_value_specific)
        ok("organs_on_runs_both", len(res) == 2 and {f.organ for f in res} == {"mdl_generativity", "sz_differential"})
    finally:
        del os.environ["ZTARE_LEANMILL_EXTRA_ORGANS"]

    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    import sys
    sys.exit(_self_test())
