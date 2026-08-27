from ztare.worldmodel.evaluation import compile_evaluation_integrity_receipt


def test_evaluation_integrity_authority_changes_with_producer_and_seal_maturity() -> None:
    sources = (
        {
            "source_id": "filing-1",
            "available_at": "2024-01-02T12:00:00Z",
            "as_of": "2024-01-03T00:00:00Z",
        },
        {
            "source_id": "price-1",
            "available_at": "2024-01-03T00:00:00Z",
            "as_of": "2024-01-03T00:00:00Z",
        },
    )
    deterministic = compile_evaluation_integrity_receipt(
        temporal_design="historical_replay",
        generation_processes=("deterministic",),
        source_availability_rows=sources,
    )
    reordered = compile_evaluation_integrity_receipt(
        temporal_design="historical_replay",
        generation_processes=("deterministic",),
        source_availability_rows=reversed(sources),
    )
    llm_reconstruction = compile_evaluation_integrity_receipt(
        temporal_design="historical_replay",
        generation_processes=("subscription_llm",),
        source_availability_rows=sources,
    )
    seal = ({
        "episode_id": "episode-1",
        "sealed_at": "2024-01-03T00:00:00Z",
        "episode_start_at": "2024-01-03T00:00:00Z",
    },)
    pending = compile_evaluation_integrity_receipt(
        temporal_design="prospective_sealed",
        generation_processes=("subscription_llm",),
        seal_rows=seal,
    )
    matured = compile_evaluation_integrity_receipt(
        temporal_design="prospective_sealed",
        generation_processes=("subscription_llm",),
        seal_rows=seal,
        maturity_rows=({
            "episode_id": "episode-1",
            "episode_end_at": "2024-04-03T00:00:00Z",
            "outcome_available_at": "2024-04-04T00:00:00Z",
            "evaluated_at": "2024-04-05T00:00:00Z",
        },),
    )

    assert deterministic["evaluation_class"] == "deterministic_point_in_time_mechanical_replay"
    assert deterministic["backtest_evidence_eligible"] is True
    assert deterministic["evaluation_integrity_sha256"] == reordered["evaluation_integrity_sha256"]
    assert llm_reconstruction["evaluation_class"] == "llm_assisted_historical_reconstruction"
    assert llm_reconstruction["latent_knowledge_contaminated"] is True
    assert llm_reconstruction["alpha_evidence_eligible"] is False
    assert pending["evidence_authority"] == "prospective_pending"
    assert pending["alpha_evidence_eligible"] is False
    assert matured["evidence_authority"] == "matured_prospective_evidence"
    assert matured["authority_rank"] > deterministic["authority_rank"]
    assert matured["paper_policy_authority"] is False
    assert matured["capital_authority"] is False
    assert matured["sufficient_for_alpha_claim"] is False
