"""GP-216 v1.20 — gap_type → next_op_class lookup for core-engine soft-generative use.

When the autoresearch loop's judge identifies a gap (via failure-family tag,
verdict, or critique) that maps to a recognizable structural shortfall, this
module returns the v5 op-class most-likely to repair it. The op-class is then
injected into the next mutator iteration's prompt as an advisory directive
(option B: stagnation-only, OR option A: every-iteration).

This is the load-bearing core-engine integration of paper 5b's v5 universal
vocabulary. NOT for ClearJudgment / mini-ztare (those are separate parallel
work owned by other agents).

Mandate reference: research_director_mandate.md §v1.20 standing duty 4.

Discipline:
  - Advisory only; the mutator MAY follow the directive or ignore it
  - The lookup is NOT a gate; the autoresearch loop's existing gates remain
  - No new control flow; the suggestion enriches existing prompts only
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class OpClassSuggestion:
    """A suggested next op-class for repairing a specific gap-type."""

    gap_type: str             # canonical gap-type identifier
    op_class: str             # v5 op_id (e.g., "core_07")
    op_name: str              # human-readable op name
    suggestion_text: str      # text to inject into mutator prompt
    rationale: str            # why this op-class is suggested for this gap


# Canonical gap_type → v5 op-class mapping
# Keyed on gap_type strings the judge / verdict pipeline emits. Mapping
# derived from GP-216 vocabulary v5 mechanisms.
GAP_TO_OP_CLASS: dict[str, OpClassSuggestion] = {
    # Brittleness / over-specialized to in-distribution data
    "thesis_fits_in_distribution_only": OpClassSuggestion(
        gap_type="thesis_fits_in_distribution_only",
        op_class="broad_05",
        op_name="Extremal Method",
        suggestion_text=(
            "The current thesis fits in-distribution data but fails on extremes. Consider the "
            "Extremal Method (broad_05): identify the load-bearing extremal configuration that, if "
            "handled, forces structural rigidity on the rest. Find the minimal counterexample or "
            "maximal configuration where the current thesis breaks; rebuild from that anchor."
        ),
        rationale="Tail / OOD failure indicates extremal-case rigidity has not been established",
    ),
    "claim_too_narrow": OpClassSuggestion(
        gap_type="claim_too_narrow",
        op_class="core_02",
        op_name="Generalization & Abstraction",
        suggestion_text=(
            "The current thesis claim is too narrow to absorb the observed structure. Consider "
            "Generalization & Abstraction (core_02): broaden the definitions to encompass more "
            "phenomena. Identify which constraint is doing artificial work; relax it to a more "
            "general categorical / structural setting."
        ),
        rationale="Narrow claim suggests definition restriction is artificial; generalize",
    ),
    # Constants / parameters without grounding
    "ad_hoc_constants_without_derivation": OpClassSuggestion(
        gap_type="ad_hoc_constants_without_derivation",
        op_class="core_06",
        op_name="Cross-Domain Translation",
        suggestion_text=(
            "Constants are empirically fitted without mechanistic grounding. Consider Cross-Domain "
            "Translation (core_06): map the estimate to a formal framework whose constants are "
            "already controlled (e.g., Sobolev embedding, Hardy-Littlewood inequality, scaling-law "
            "theorem), verify its preconditions, and derive the constants rather than stipulating "
            "them."
        ),
        rationale="Ad-hoc constants are signal that an external framework should provide them",
    ),
    # Structural fragility / monolithic argument
    "argument_is_monolithic": OpClassSuggestion(
        gap_type="argument_is_monolithic",
        op_class="core_03",
        op_name="Decomposition & Recomposition",
        suggestion_text=(
            "The argument is monolithic and brittle to local failures. Consider Decomposition & "
            "Recomposition (core_03): partition the object into well-understood components, prove "
            "the property locally on each component, then assemble. The decomposition itself "
            "becomes the proof's structural backbone."
        ),
        rationale="Monolithic = no decomposition has been imposed; impose canonical decomposition",
    ),
    "patches_dont_glue_globally": OpClassSuggestion(
        gap_type="patches_dont_glue_globally",
        op_class="core_04",
        op_name="Local-to-Global Assembly",
        suggestion_text=(
            "Local proofs exist but don't compose into a global argument. Consider Local-to-Global "
            "Assembly (core_04): identify the gluing data — the consistency or compatibility "
            "conditions that must hold across patches — and prove these explicitly. Without "
            "explicit gluing, local proofs are necessary but not sufficient."
        ),
        rationale="Patch-level proofs without gluing data is an incomplete local-to-global pattern",
    ),
    "wrong_observable_topology": OpClassSuggestion(
        gap_type="wrong_observable_topology",
        op_class="core_02",
        op_name="Generalization & Abstraction",
        suggestion_text=(
            "The current proof prices or observes the wrong object. Consider Generalization & "
            "Abstraction (core_02): replace the hidden/internal coordinate ledger with the "
            "externally load-bearing observable class before scoring payoff. Define the topology, "
            "atoms, and observable prices independently of the successful candidate, then rerun the "
            "claim inside that fixed broader observable space."
        ),
        rationale="Hidden-coordinate pricing is a topology error; broaden to the true observable class",
    ),
    "multiplicity_not_charged": OpClassSuggestion(
        gap_type="multiplicity_not_charged",
        op_class="core_04",
        op_name="Local-to-Global Assembly",
        suggestion_text=(
            "The local certificate does not charge multiplicity in the global assembly. Consider "
            "Local-to-Global Assembly (core_04): lift the bound from labels/classes to actual "
            "events or occurrences, prove the multiplicity map, and budget the reciprocal or dual "
            "quantity over the assembled event stream rather than over representatives."
        ),
        rationale="A class-level budget that ignores event multiplicity cannot glue globally",
    ),
    "tautological_price_definition": OpClassSuggestion(
        gap_type="tautological_price_definition",
        op_class="core_05",
        op_name="Canonical Form & Invariance",
        suggestion_text=(
            "The proof risks defining the price from the payoff it is supposed to bound. Consider "
            "Canonical Form & Invariance (core_05): fix the decomposition, topology, observables, "
            "and price kernel before observing the candidate. Then prove invariance of the receipt "
            "under equivalent representations, so the argument cannot change coordinates after "
            "seeing the profitable direction."
        ),
        rationale="Anti-tautology failures require predeclared canonical observables and prices",
    ),
    # Cross-domain / reformulation gaps
    "no_cross_domain_bridge": OpClassSuggestion(
        gap_type="no_cross_domain_bridge",
        op_class="core_01",
        op_name="Problem Reformulation & Reduction",
        suggestion_text=(
            "The current formulation is intractable in its native domain. Consider Problem "
            "Reformulation & Reduction (core_01): translate the problem to an equivalent form in a "
            "different formal system where more powerful tools are available (e.g., topology → "
            "algebra; analytic → algebraic; integer → polynomial). Identify the structural "
            "correspondence that would let theorems transport across the bridge."
        ),
        rationale="Stuck-in-domain = candidate cross-domain reformulation",
    ),
    # Iteration / refinement issues
    "stagnation_with_potential_function": OpClassSuggestion(
        gap_type="stagnation_with_potential_function",
        op_class="broad_01",
        op_name="Iterative Refinement",
        suggestion_text=(
            "Iteration has stagnated; the declared potential function is not strictly improving. "
            "Either the potential function is wrong (replace with a different scalar invariant), or "
            "the iteration step is broken (revisit the refinement procedure). Standard fixes: "
            "switch potential function from energy to entropy; or add a regularization that "
            "guarantees monotonicity."
        ),
        rationale="Stagnation under monotone potential = wrong potential or wrong iteration step",
    ),
    # Self-reference / canonical-form gaps
    "no_canonical_representative": OpClassSuggestion(
        gap_type="no_canonical_representative",
        op_class="core_05",
        op_name="Canonical Form & Invariance",
        suggestion_text=(
            "Equivalent objects are being treated as distinct, inflating the search. Consider "
            "Canonical Form & Invariance: identify a stable representative within each equivalence "
            "class (Jordan form / minimal model / normal form / fundamental domain) and reduce "
            "analysis to representatives only."
        ),
        rationale="Redundant equivalent objects = canonical-form lookup not yet applied",
    ),
    # Default fallback
    "stagnation_unknown_gap_type": OpClassSuggestion(
        gap_type="stagnation_unknown_gap_type",
        op_class="multi",
        op_name="multi-op suggestion",
        suggestion_text=(
            "Stagnation detected; gap-type not classified. Consider in priority order: "
            "(1) Generalization & Abstraction (core_02) — is the claim too narrow? "
            "(2) Decomposition & Recomposition (core_03) — is the argument monolithic? "
            "(3) Problem Reformulation & Reduction (core_01) — is there a cross-domain bridge? "
            "(4) Extremal Method (broad_05) — is the load-bearing extremal case unhandled?"
        ),
        rationale="Generic stagnation fallback when judge gap-type is unclassified",
    ),
}


def lookup(gap_type: str) -> Optional[OpClassSuggestion]:
    """Look up the suggested next op-class for a given gap-type.

    Returns None if gap_type is not in the canonical lookup. Caller should fall
    back to the generic `stagnation_unknown_gap_type` suggestion in that case.
    """
    return GAP_TO_OP_CLASS.get(gap_type)


def lookup_with_fallback(gap_type: str) -> OpClassSuggestion:
    """Like lookup() but always returns a suggestion; falls back to generic on miss."""
    sug = lookup(gap_type)
    return sug if sug is not None else GAP_TO_OP_CLASS["stagnation_unknown_gap_type"]


def render_directive(suggestion: OpClassSuggestion) -> str:
    """Render an op-class suggestion as a mutator-prompt advisory directive.

    Output format aligns with the existing `StagnationSpecialCaseHintGate.directive`
    style so the autoresearch_loop can append it to mutator prompts uniformly.
    """
    return (
        f"\n\n=== NEXT-OP CLASS SUGGESTION (advisory; gap_type={suggestion.gap_type}) ===\n"
        f"Suggested op-class: **{suggestion.op_name}** ({suggestion.op_class})\n"
        f"\n"
        f"{suggestion.suggestion_text}\n"
        f"\n"
        f"Rationale: {suggestion.rationale}\n"
        f"\n"
        f"This is advisory: the mutator MAY follow this op-class or ignore it. The "
        f"suggestion derives from GP-216 universal vocabulary v5 (see `src/ztare/research_director/"
        f"universal_research_ops.py` for the full vocabulary). If you ignore the suggestion, "
        f"explain in your iteration's notes why a different op-class was chosen.\n"
    )


__all__ = [
    "OpClassSuggestion",
    "GAP_TO_OP_CLASS",
    "lookup",
    "lookup_with_fallback",
    "render_directive",
]


if __name__ == "__main__":
    # Self-test
    test_gaps = [
        "thesis_fits_in_distribution_only",
        "ad_hoc_constants_without_derivation",
        "argument_is_monolithic",
        "stagnation_unknown_gap_type",
        "completely_unknown_gap_type",
    ]
    print("=== gap_to_op_class self-test ===\n")
    for gap in test_gaps:
        sug = lookup_with_fallback(gap)
        print(f"  {gap}")
        print(f"    → {sug.op_class} ({sug.op_name})")
        print(f"    rationale: {sug.rationale}")
        print()
    print("Sample directive render:")
    print(render_directive(GAP_TO_OP_CLASS["argument_is_monolithic"])[:400])
