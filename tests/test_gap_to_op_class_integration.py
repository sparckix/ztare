from ztare.validator.utilities.gap_to_op_class_integration import (
    enrich_pivot_instruction_with_op_class,
    infer_gap_type_from_judge_verdict,
)


def test_profile_lsc_gap_maps_to_local_to_global() -> None:
    verdict = {
        "text": (
            "Finite certificates exist, but profile decomposition and "
            "lower-semicontinuity through the limit passage remain unresolved."
        )
    }

    assert infer_gap_type_from_judge_verdict(verdict) == "patches_dont_glue_globally"


def test_profile_lsc_enrichment_mentions_core_04() -> None:
    verdict = {
        "critique": (
            "The candidate has local estimates but no global Sobolev profile "
            "decomposition or lower semicontinuity theorem."
        )
    }

    enriched = enrich_pivot_instruction_with_op_class("BASE", [], judge_verdict=verdict)

    assert "Local-to-Global" in enriched
    assert "core_04" in enriched


def test_hidden_source_l2_maps_to_observable_topology() -> None:
    verdict = {
        "critique": (
            "Hidden source-L2 pricing is invalid; the theorem must use a fixed "
            "all-output observable topology before payoff scoring."
        )
    }

    assert infer_gap_type_from_judge_verdict(verdict) == "wrong_observable_topology"


def test_shell_only_recurrence_maps_to_multiplicity_charge() -> None:
    verdict = {
        "text": (
            "Shell-only recurrence is insufficient because the reciprocal budget "
            "does not charge event multiplicity."
        )
    }

    assert infer_gap_type_from_judge_verdict(verdict) == "multiplicity_not_charged"
