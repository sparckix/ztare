"""GP-216 v1.20 — option B integration shim for gap_to_op_class injection.

Integrates `gap_to_op_class.lookup_with_fallback()` into the autoresearch_loop's
existing stagnation-pivot machinery. This is the option-B (stagnation-only)
integration point; option A (every-iteration) requires a separate hook
in mutator-prompt construction.

USAGE in autoresearch_loop.py:

    from src.ztare.validator.utilities.gap_to_op_class_integration import (
        enrich_pivot_instruction_with_op_class,
    )

    # Where the existing pivot_state is resolved:
    pivot_state = resolve_stagnation_pivot_state(...)

    # NEW: enrich the instruction text with v5 op-class suggestion
    if pivot_state.profile is not None:
        enriched_instruction = enrich_pivot_instruction_with_op_class(
            base_instruction=pivot_state.profile.instruction,
            iteration_history=iteration_history,
            judge_verdict=last_judge_verdict,  # if available; None falls through
            rubric_data=rubric_data,
        )
        # ... use enriched_instruction in mutator prompt construction

The shim is a one-line change at the call site. It is opt-in because GP-216's
paper result is primarily a Director/workbench vocabulary. If
`rubric_data["enable_v5_op_class_injection"]` is not true, the shim returns
base_instruction unchanged. The old `disable_v5_op_class_injection` escape
hatch is still honored.
"""
from __future__ import annotations

from typing import Any, Optional

from .gap_to_op_class import (
    GAP_TO_OP_CLASS,
    OpClassSuggestion,
    lookup_with_fallback,
    render_directive,
)


def infer_gap_type_from_judge_verdict(judge_verdict: Optional[dict[str, Any]]) -> str:
    """Map judge verdict patterns to canonical gap-type strings.

    Heuristic-only: looks at common verdict-text patterns and verdict-tag fields.
    Returns 'stagnation_unknown_gap_type' if no clear gap is detectable.

    Mapping logic (priority order):
      1. Check `judge_verdict["failure_family"]` if structured tag exists
      2. Check `judge_verdict["text"]` for keyword patterns
      3. Fall back to generic stagnation
    """
    if not judge_verdict:
        return "stagnation_unknown_gap_type"

    # Structured failure-family tag (most reliable)
    family = judge_verdict.get("failure_family", "").lower()
    if family:
        family_to_gap = {
            "ood_brittle": "thesis_fits_in_distribution_only",
            "tail_unresolved": "thesis_fits_in_distribution_only",
            "ad_hoc_constants": "ad_hoc_constants_without_derivation",
            "fitted_constants": "ad_hoc_constants_without_derivation",
            "monolithic": "argument_is_monolithic",
            "no_decomposition": "argument_is_monolithic",
            "gluing_missing": "patches_dont_glue_globally",
            "local_only": "patches_dont_glue_globally",
            "narrow_claim": "claim_too_narrow",
            "scope_too_narrow": "claim_too_narrow",
            "no_redundancy_collapse": "no_canonical_representative",
            "stuck_in_domain": "no_cross_domain_bridge",
            "wrong_observable_topology": "wrong_observable_topology",
            "hidden_coordinate_price": "wrong_observable_topology",
            "multiplicity_not_charged": "multiplicity_not_charged",
            "event_budget_missing": "multiplicity_not_charged",
            "tautological_price": "tautological_price_definition",
            "self_referential_price": "tautological_price_definition",
        }
        if family in family_to_gap:
            return family_to_gap[family]

    # Text keyword patterns (lower-reliability fallback)
    text = (judge_verdict.get("text", "") + " " + judge_verdict.get("critique", "")).lower()
    keyword_to_gap = [
        ("in-distribution", "thesis_fits_in_distribution_only"),
        ("out-of-distribution", "thesis_fits_in_distribution_only"),
        ("far-tail", "thesis_fits_in_distribution_only"),
        ("ad-hoc", "ad_hoc_constants_without_derivation"),
        ("fitted constant", "ad_hoc_constants_without_derivation"),
        ("derivation missing", "ad_hoc_constants_without_derivation"),
        ("monolithic", "argument_is_monolithic"),
        ("decompose", "argument_is_monolithic"),
        ("local but not global", "patches_dont_glue_globally"),
        ("gluing", "patches_dont_glue_globally"),
        ("profile decomposition", "patches_dont_glue_globally"),
        ("lower-semicontinuity", "patches_dont_glue_globally"),
        ("lower semicontinuity", "patches_dont_glue_globally"),
        ("limit passage", "patches_dont_glue_globally"),
        ("limit-passage", "patches_dont_glue_globally"),
        ("finite certificates", "patches_dont_glue_globally"),
        ("global sobolev", "patches_dont_glue_globally"),
        ("hidden source", "wrong_observable_topology"),
        ("source-l2", "wrong_observable_topology"),
        ("source l2", "wrong_observable_topology"),
        ("wrong topology", "wrong_observable_topology"),
        ("observable topology", "wrong_observable_topology"),
        ("all-output", "wrong_observable_topology"),
        ("shell-only", "multiplicity_not_charged"),
        ("event-level", "multiplicity_not_charged"),
        ("event multiplicity", "multiplicity_not_charged"),
        ("reciprocal budget", "multiplicity_not_charged"),
        ("multiplicity", "multiplicity_not_charged"),
        ("tautology", "tautological_price_definition"),
        ("self-referential", "tautological_price_definition"),
        ("after payoff", "tautological_price_definition"),
        ("before payoff", "tautological_price_definition"),
        ("narrow scope", "claim_too_narrow"),
        ("too specific", "claim_too_narrow"),
        ("redundant", "no_canonical_representative"),
        ("equivalent", "no_canonical_representative"),
    ]
    for kw, gap in keyword_to_gap:
        if kw in text:
            return gap

    return "stagnation_unknown_gap_type"


def enrich_pivot_instruction_with_op_class(
    base_instruction: str,
    iteration_history: list[dict],
    judge_verdict: Optional[dict[str, Any]] = None,
    rubric_data: Optional[dict[str, Any]] = None,
) -> str:
    """Append v5 op-class suggestion to the existing pivot instruction.

    If `rubric_data["enable_v5_op_class_injection"]` is not True, returns
    base_instruction unchanged. The old `disable_v5_op_class_injection` flag
    also returns the base instruction unchanged.

    Otherwise: infers gap_type from latest judge verdict, looks up op-class
    suggestion, appends rendered directive to base_instruction.
    """
    rubric_data = rubric_data or {}
    if rubric_data.get("disable_v5_op_class_injection"):
        return base_instruction
    if not rubric_data.get("enable_v5_op_class_injection"):
        return base_instruction

    # Infer gap from latest judge verdict (or from iteration_history's last entry)
    if judge_verdict is None and iteration_history:
        last = iteration_history[-1]
        judge_verdict = last.get("judge_verdict", last.get("verdict"))

    gap_type = infer_gap_type_from_judge_verdict(judge_verdict)
    suggestion = lookup_with_fallback(gap_type)
    directive = render_directive(suggestion)
    return base_instruction + directive


__all__ = [
    "infer_gap_type_from_judge_verdict",
    "enrich_pivot_instruction_with_op_class",
]


if __name__ == "__main__":
    # Self-test
    base = "## STANDARD PIVOT INSTRUCTION\nApply the heuristic modules..."

    # Case 1: ad-hoc constants
    verdict_1 = {"failure_family": "ad_hoc_constants", "text": "Constants are fitted empirically."}
    enriched_1 = enrich_pivot_instruction_with_op_class(
        base,
        [],
        judge_verdict=verdict_1,
        rubric_data={"enable_v5_op_class_injection": True},
    )
    print("CASE 1 (ad-hoc constants):")
    print(enriched_1[-400:])
    print()

    # Case 2: brittle on tail
    verdict_2 = {"failure_family": "tail_unresolved", "text": "Thesis fails on far-tail residual."}
    enriched_2 = enrich_pivot_instruction_with_op_class(
        base,
        [],
        judge_verdict=verdict_2,
        rubric_data={"enable_v5_op_class_injection": True},
    )
    print("CASE 2 (tail unresolved):")
    print(enriched_2[-400:])
    print()

    # Case 3: disabled via rubric
    enriched_3 = enrich_pivot_instruction_with_op_class(
        base, [], judge_verdict=verdict_1, rubric_data={"disable_v5_op_class_injection": True}
    )
    print("CASE 3 (disabled):")
    print(f"  Returns base unchanged: {enriched_3 == base}")

    enriched_4 = enrich_pivot_instruction_with_op_class(base, [], judge_verdict=verdict_1)
    print("CASE 4 (default no-op):")
    print(f"  Returns base unchanged: {enriched_4 == base}")
