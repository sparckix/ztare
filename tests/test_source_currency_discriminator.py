from src.ztare.research_director.source_currency_discriminator import (
    classify_forecast_source_currency,
    classify_source_currency,
)


def test_classifies_convergence_currency_bridge_before_generic_contract() -> None:
    result = classify_source_currency(
        "KRF row20 source contract for diagonal convergence in measure",
        "consumer needs TendstoInMeasure for the diagonal limit",
    )

    assert result["source_currency_class"] == "convergence_currency_bridge"
    assert "tendstoinmeasure" in result["matched_terms"]
    assert any(
        "target convergence mode receipt" in receipt
        for receipt in result["required_receipts"]
    )
    assert result["also_matched"]


def test_classifies_integrability_membership_confuser() -> None:
    result = classify_source_currency(
        "strengthen data contract with IntegrableOn norm squared source field",
        "indicator MemLp consumer",
    )

    assert result["source_currency_class"] == "integrability_membership"
    assert any(
        "bounded Bochner integral inequality implies IntegrableOn" in confuser
        for confuser in result["nearest_confusers"]
    )


def test_pairwise_elpnorm_cauchy_prioritizes_norm_currency() -> None:
    result = classify_source_currency(
        "selected diagonal restricted Lp Cauchy source from pairwise eLpNorm Cauchy",
        "consumer needs a CauchySeq in the restricted Lp metric",
    )

    assert result["source_currency_class"] == "norm_currency_bridge"
    assert "elpnorm" in result["matched_terms"]
    assert "cauchy" in result["matched_terms"]
    assert any(
        match["source_currency_class"] == "integrability_membership"
        for match in result["also_matched"]
    )


def test_restricted_elpnorm_source_prioritizes_norm_currency() -> None:
    result = classify_source_currency(
        "target_currency restricted_eLpNorm_source_contract_repair",
        "source field: eLpNorm approximation for a restricted selected family",
    )

    assert result["source_currency_class"] == "norm_currency_bridge"
    assert "elpnorm" in result["matched_terms"]
    assert any(
        match["source_currency_class"] == "integrability_membership"
        for match in result["also_matched"]
    )


def test_unknown_profile_returns_minimal_receipts() -> None:
    result = classify_source_currency("unrelated finite combinatorial selector")

    assert result["source_currency_class"] == "unknown"
    assert result["confidence"] == "low"
    assert "state the downstream consumer" in result["required_receipts"]


def test_coefficient_tensor_projection_prioritizes_triad_receipts() -> None:
    result = classify_source_currency(
        "Fourier triad Lamb vector tensor projection with owner-preimage no-rebilling",
        "consumer needs same-carrier phase coherence penalty after Leray projection",
    )

    assert result["source_currency_class"] == "coefficient_tensor_projection"
    assert "fourier triad" in result["matched_terms"]
    assert any(
        "projected coefficient-level penalty" in check
        for check in [result["downstream_consumer_check"]]
    )
    assert any(
        "scalar shell coherence price" in confuser
        for confuser in result["nearest_confusers"]
    )


def test_lamb_helicity_labels_alone_do_not_become_coefficient_tensor() -> None:
    result = classify_source_currency(
        "Clebsch alpha beta phi helicity topology labels for Lamb vector geometry",
        "no amplitude energy source budget and no numerical payment receipt",
    )

    assert result["source_currency_class"] != "coefficient_tensor_projection"
    assert result["source_currency_class"] == "unknown"


def test_owner_preimage_budget_is_distinct_from_triad_tensor() -> None:
    result = classify_source_currency(
        "Microlocal wavepacket owner-preimage Carleson budget",
        "selected-prefix no-rebilling same-carrier source output binding",
    )

    assert result["source_currency_class"] == "owner_preimage_budget"
    assert any("owner map fixed before payoff" in receipt for receipt in result["required_receipts"])


def test_scalar_shell_price_is_own_class() -> None:
    result = classify_source_currency(
        "scalar shell Littlewood-Paley shell crossPrice coherencePrice stream",
        "consumer wants selected-event payment from shell coherence",
    )

    assert result["source_currency_class"] == "scalar_shell_price"
    assert any("shell-to-selected-event transport" in receipt for receipt in result["required_receipts"])


def test_forecast_source_currency_prefers_computed_relation_when_requested() -> None:
    result = classify_forecast_source_currency(
        resolve_date="2025-07-01",
        model_cutoff_date="2025-10-01",
        stored_post_training_cutoff=1,
        prefer_computed_cutoff=True,
    )

    assert result["cutoff_relation"] == "pre_cutoff"
    assert result["stored_cutoff_relation"] == "post_cutoff"
    assert result["computed_cutoff_relation"] == "pre_cutoff"
    assert result["cutoff_relation_conflict"] is True
    assert result["provenance"] == "computed_from_panel_cutoff_date_over_stored_flag"
