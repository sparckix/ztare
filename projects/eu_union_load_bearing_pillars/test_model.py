# test_model.py
# Operational state-ontology checks for the load-bearing pillars project.

# Imported axioms / inherited facts - Reflecting the governance mode distinction
# These axioms support the classification of current EU state into fragile_but_intact (Mode FI)
axiom_legal_primacy_contested = True # Evidences Mode FI for legal pillar, per "EU-law primacy is a real Court of Justice doctrine but is not a freestanding treaty article and faces contested enforcement in member-state constitutional courts."
axiom_emu_lacks_sizeable_federal_budget = True # Evidences Mode FI for fiscal pillar, per "EMU lacks a sizeable federal budget by official Commission characterization"
axiom_article_48_unanimity = True # Structural constraint for shifting from Mode FI to Mode DE via treaty change, per "Article 48 TEU requires unanimity for treaty revision"
axiom_discretionary_crisis_instruments = True # Direct evidence of Mode FI governance under stress, per "The EFSF, ESM, OMT, and RRF were all crisis-driven discretionary or treaty-adjacent instruments rather than standing automatic fiscal mechanisms"
axiom_survival_not_equilibrium = True # Supports the distinction between intactness and durable equilibrium, per "Repeated EU crisis survival should not automatically be treated as proof of durable equilibrium"

# External Grounding Data (Immutable Constants from evidence.txt)
# Fiscal Scale Benchmarks (S002)
IMF_FISCAL_CONTRIBUTION_BASELINE_GDP_PERCENT = 0.35 # IMF baseline for meaningful macroeconomic stabilization
IMF_FISCAL_PEAK_TRANSFERS_BASELINE_GDP_PERCENT = 1.1 # IMF baseline for peak transfer capability
IMF_FISCAL_TOO_SMALL_THRESHOLD_GDP_PERCENT = 0.1 # IMF explicit threshold for 'too small' contribution
EURO_AREA_SHOCK_SMOOTHING_PERCENT = 0.20 # Share of idiosyncratic shocks smoothed across euro-area countries (S002)
US_SHOCK_SMOOTHING_PERCENT = 0.75 # Share of idiosyncratic shocks smoothed across US states (S002)

# Legal Scope Benchmarks (S004, S005)
US_CONSTITUTION_SUPREMACY_CLAUSE_EXPLICIT_ENTRENCHMENT = True # Article VI provides explicit, founding-level legal supremacy (S004)
EU_PRIMACY_TREATY_PROVISION_RECOMMENDED = True # European Parliament recommends explicit treaty provision due to challenges (S005)


def classify_union_state(
    *,
    major_member_exit: bool,
    sustained_multistate_breakdown: bool,
    requires_discretionary_emergency_bargaining: bool, # Mode FI indicator: preservation relies on ad hoc political bargaining
    preservation_relies_on_temporary_or_treaty_adjacent_fixes: bool, # Mode FI indicator: preservation uses non-standing tools
    standing_material_fiscal_stabilizer_exists: bool, # Presence indicates Mode DE for fiscal, absence indicates Mode FI for fiscal
    legal_enforcement_is_recurrently_contested: bool, # Indicates Mode FI for legal, absence indicates Mode DE for legal
    # New parameters to incorporate external grounding for Mode DE definitions
    fiscal_capacity_meets_external_benchmark: bool, # True if fiscal capacity meets IMF baselines for scale/shock smoothing
    legal_supremacy_meets_external_benchmark: bool, # True if legal supremacy is explicitly entrenched and less contested than EU's current state (e.g., US Article VI)
) -> str:
    """
    Classifies the union state based on operational definitions, directly implementing the
    `stress_response_governance_mode` discriminator, now leveraging external benchmarks.
    """
    if major_member_exit or sustained_multistate_breakdown:
        return "material_union_failure"

    # Durable Equilibrium (Mode DE) requires the *absence* of Mode FI indicators
    # AND the *presence* of key standing pillars (fiscal and legal),
    # AND that these pillars meet the externally grounded benchmarks.
    if (
        not requires_discretionary_emergency_bargaining
        and not preservation_relies_on_temporary_or_treaty_adjacent_fixes
        and standing_material_fiscal_stabilizer_exists
        and not legal_enforcement_is_recurrently_contested
        and fiscal_capacity_meets_external_benchmark # New condition for DE
        and legal_supremacy_meets_external_benchmark # New condition for DE
    ):
        return "durable_equilibrium"

    # If not failure and not durable equilibrium, it must be fragile_but_intact (Mode FI).
    # This captures scenarios where any Mode FI indicator is true OR a key standing pillar is absent OR
    # the standing pillars, if they exist, do not meet external benchmarks.
    return "fragile_but_intact"


def forecast_tilt_by_2035(*, material_failure_event_occurs: bool) -> str:
    """
    Provides a directional forecast tilt for 2035, event-driven.
    This bridge explains why the current pattern of discretionary preservation
    either is or is not enough to keep the union formally intact.
    """
    if material_failure_event_occurs:
        return "forecast_weakened_due_to_failure"
    # If no material failure event, the current pattern of discretionary preservation
    # (Mode FI) is assessed as sufficient to maintain formal intactness,
    # leading to the "fragile_but_intact_more_likely_than_failure" tilt.
    return "fragile_but_intact_more_likely_than_failure"


def test_current_eu_classifies_as_fragile_but_intact():
    """
    Tests that the current EU state, based on axioms, observable markers,
    and comparison to external benchmarks, classifies as fragile_but_intact.
    This directly reflects the current `stress_response_governance_mode` being Mode FI.
    """
    current_eu_state = classify_union_state(
        major_member_exit=False,
        sustained_multistate_breakdown=False,
        requires_discretionary_emergency_bargaining=axiom_discretionary_crisis_instruments,
        preservation_relies_on_temporary_or_treaty_adjacent_fixes=axiom_discretionary_crisis_instruments,
        # Axioms confirm absence of Mode DE fiscal pillar's characteristics AND external benchmarks are not met
        standing_material_fiscal_stabilizer_exists=not axiom_emu_lacks_sizeable_federal_budget, # Currently, no sizeable budget exists
        fiscal_capacity_meets_external_benchmark=False, # EU's current shock smoothing (0.20) < US (0.75), and lacks IMF baseline contributions
        # Axioms confirm absence of Mode DE legal pillar's characteristics AND external benchmarks are not met
        legal_enforcement_is_recurrently_contested=axiom_legal_primacy_contested,
        legal_supremacy_meets_external_benchmark=False, # EU primacy is jurisprudential & contested, unlike US explicit entrenchment
    )
    assert current_eu_state == "fragile_but_intact"

    # PROXY 1: Legal supremacy is doctrinal but contested (vs. explicit treaty entrenchment)
    # Asserts that EU's contested primacy does not meet the explicit entrenchment benchmark
    assert axiom_legal_primacy_contested is True
    assert US_CONSTITUTION_SUPREMACY_CLAUSE_EXPLICIT_ENTRENCHMENT is True # External benchmark exists

    # PROXY 2: Crisis preservation remains discretionary (vs. standing automatic mechanisms)
    assert axiom_discretionary_crisis_instruments is True
    # Euro Area shock smoothing is significantly less than US benchmark
    assert EURO_AREA_SHOCK_SMOOTHING_PERCENT < US_SHOCK_SMOOTHING_PERCENT
    assert US_SHOCK_SMOOTHING_PERCENT == 0.75
    assert EURO_AREA_SHOCK_SMOOTHING_PERCENT == 0.20

    # PROXY 3: No standing federal stabilizer of material size (vs. IMF baseline)
    assert axiom_emu_lacks_sizeable_federal_budget is True
    # Implicitly, the lack of a sizeable budget means it doesn't meet IMF baseline
    # We assert that the IMF baseline is greater than the 'too small' threshold, setting the bar.
    assert IMF_FISCAL_CONTRIBUTION_BASELINE_GDP_PERCENT > IMF_FISCAL_TOO_SMALL_THRESHOLD_GDP_PERCENT
    assert IMF_FISCAL_CONTRIBUTION_BASELINE_GDP_PERCENT == 0.35 # IMF baseline for comparison
    assert IMF_FISCAL_PEAK_TRANSFERS_BASELINE_GDP_PERCENT == 1.1 # IMF peak transfers for comparison


def test_standing_bundle_classifies_as_durable_equilibrium():
    """
    Tests a hypothetical scenario where the EU has standing, non-discretionary
    mechanisms and uncontested legal supremacy, *meeting external benchmarks*,
    classifying it as durable_equilibrium (Mode DE). This represents the target state not currently met by the EU.
    """
    standing_bundle_state = classify_union_state(
        major_member_exit=False,
        sustained_multistate_breakdown=False,
        requires_discretionary_emergency_bargaining=False,
        preservation_relies_on_temporary_or_treaty_adjacent_fixes=False,
        standing_material_fiscal_stabilizer_exists=True,
        legal_enforcement_is_recurrently_contested=False,
        fiscal_capacity_meets_external_benchmark=True, # Hypothetically meets benchmarks
        legal_supremacy_meets_external_benchmark=True, # Hypothetically meets benchmarks
    )
    assert standing_bundle_state == "durable_equilibrium"


def test_failure_boundary_dominates_intactness():
    """
    Tests that material union failure overrides other classifications,
    reflecting the operational end-state ontology.
    """
    failure_state = classify_union_state(
        major_member_exit=True, # Event of material failure
        sustained_multistate_breakdown=False,
        requires_discretionary_emergency_bargaining=False,
        preservation_relies_on_temporary_or_treaty_adjacent_fixes=False,
        standing_material_fiscal_stabilizer_exists=True,
        legal_enforcement_is_recurrently_contested=False,
        fiscal_capacity_meets_external_benchmark=True,
        legal_supremacy_meets_external_benchmark=True,
    )
    assert failure_state == "material_union_failure"


def test_survival_alone_does_not_imply_equilibrium():
    """
    Tests that survival through discretionary means (Mode FI) still means fragile_but_intact,
    consistent with the axiom "Repeated EU crisis survival should not automatically be treated as proof of durable equilibrium."
    This also reinforces that merely "standing_material_fiscal_stabilizer_exists" is not enough
    if it doesn't meet external benchmarks or if discretionary means are still primary.
    """
    survival_only_state = classify_union_state(
        major_member_exit=False,
        sustained_multistate_breakdown=False,
        requires_discretionary_emergency_bargaining=True, # Mode FI response
        preservation_relies_on_temporary_or_treaty_adjacent_fixes=True, # Mode FI response
        standing_material_fiscal_stabilizer_exists=False, # Missing a key DE pillar (axiom_emu_lacks_sizeable_federal_budget)
        legal_enforcement_is_recurrently_contested=False,
        fiscal_capacity_meets_external_benchmark=False, # Does not meet external benchmarks
        legal_supremacy_meets_external_benchmark=True, # Hypothetically meets legal, but fiscal is lacking
    )
    assert survival_only_state == "fragile_but_intact"
    assert axiom_survival_not_equilibrium is True


def test_missing_fiscal_pillar_blocks_durable_equilibrium():
    """
    Tests that a missing fiscal pillar (Mode FI for fiscal, due to absence of standing mechanism
    OR failing to meet external benchmarks) leads to fragile_but_intact.
    This demonstrates the load-bearing nature of the fiscal pillar, now with external grounding.
    """
    # Scenario 1: No standing fiscal stabilizer
    fiscal_missing_no_standing_state = classify_union_state(
        major_member_exit=False,
        sustained_multistate_breakdown=False,
        requires_discretionary_emergency_bargaining=False, # Would otherwise lean to DE
        preservation_relies_on_temporary_or_treaty_adjacent_fixes=False, # Would otherwise lean to DE
        standing_material_fiscal_stabilizer_exists=False, # MISSING (e.g., axiom_emu_lacks_sizeable_federal_budget)
        legal_enforcement_is_recurrently_contested=False,
        fiscal_capacity_meets_external_benchmark=False, # By definition if no standing stabilizer
        legal_supremacy_meets_external_benchmark=True, # Present
    )
    assert fiscal_missing_no_standing_state == "fragile_but_intact"

    # Scenario 2: Standing fiscal stabilizer exists but does NOT meet external benchmarks
    fiscal_exists_but_not_material_state = classify_union_state(
        major_member_exit=False,
        sustained_multistate_breakdown=False,
        requires_discretionary_emergency_bargaining=False,
        preservation_relies_on_temporary_or_treaty_adjacent_fixes=False,
        standing_material_fiscal_stabilizer_exists=True, # EXISTS, but...
        legal_enforcement_is_recurrently_contested=False,
        fiscal_capacity_meets_external_benchmark=False, # ...it DOES NOT meet Mode DE external benchmarks
        legal_supremacy_meets_external_benchmark=True,
    )
    assert fiscal_exists_but_not_material_state == "fragile_but_intact"


def test_missing_legal_pillar_blocks_durable_equilibrium():
    """
    Tests that a contested legal pillar (Mode FI for legal, due to recurrent contestation
    OR failing to meet explicit entrenchment benchmarks) leads to fragile_but_intact.
    This demonstrates the load-bearing nature of the legal pillar, now with external grounding.
    """
    # Scenario 1: Legal enforcement is recurrently contested (axiom_legal_primacy_contested)
    legal_missing_contested_state = classify_union_state(
        major_member_exit=False,
        sustained_multistate_breakdown=False,
        requires_discretionary_emergency_bargaining=False,
        preservation_relies_on_temporary_or_treaty_adjacent_fixes=False,
        standing_material_fiscal_stabilizer_exists=True,
        legal_enforcement_is_recurrently_contested=True, # CONTESTED (e.g., axiom_legal_primacy_contested)
        fiscal_capacity_meets_external_benchmark=True,
        legal_supremacy_meets_external_benchmark=False, # By definition if recurrently contested
    )
    assert legal_missing_contested_state == "fragile_but_intact"

    # Scenario 2: Legal supremacy is NOT explicitly entrenched (even if contestation is 'low', it doesn't meet the benchmark)
    legal_not_meeting_entrenchment_benchmark_state = classify_union_state(
        major_member_exit=False,
        sustained_multistate_breakdown=False,
        requires_discretionary_emergency_bargaining=False,
        preservation_relies_on_temporary_or_treaty_adjacent_fixes=False,
        standing_material_fiscal_stabilizer_exists=True,
        legal_enforcement_is_recurrently_contested=False, # Hypothetically low contestation
        fiscal_capacity_meets_external_benchmark=True,
        legal_supremacy_meets_external_benchmark=False, # But it's not explicitly entrenched like US Article VI
    )
    assert legal_not_meeting_entrenchment_benchmark_state == "fragile_but_intact"


def test_forecast_tilt_is_event_driven():
    """
    Tests the conditional logic of the forecast tilt for 2035.
    This reflects the bridge from the observed `fragile_but_intact` state
    to the forward projection based on the absence or presence of `material_union_failure` events.
    """
    # If no material failure event occurs, the forecast is continued intactness (in fragile mode)
    assert (
        forecast_tilt_by_2035(material_failure_event_occurs=False)
        == "fragile_but_intact_more_likely_than_failure"
    )
    # If a material failure event occurs, the forecast is weakened due to failure
    assert (
        forecast_tilt_by_2035(material_failure_event_occurs=True)
        == "forecast_weakened_due_to_failure"
    )


if __name__ == "__main__":
    test_current_eu_classifies_as_fragile_but_intact()
    test_standing_bundle_classifies_as_durable_equilibrium()
    test_failure_boundary_dominates_intactness()
    test_survival_alone_does_not_imply_equilibrium()
    test_missing_fiscal_pillar_blocks_durable_equilibrium()
    test_missing_legal_pillar_blocks_durable_equilibrium()
    test_forecast_tilt_is_event_driven()
