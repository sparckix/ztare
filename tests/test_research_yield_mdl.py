from src.ztare.research_director.research_yield_mdl import (
    ResearchAvenue,
    score_research_avenue,
    score_research_avenues,
)


def test_triad_projection_route_gets_formalize_or_counterexample() -> None:
    score = score_research_avenue(
        ResearchAvenue(
            avenue_id="triad",
            description=(
                "Fourier triad Lamb vector tensor projection with owner-preimage "
                "and no-rebilling under physical projection"
            ),
            receipts=(
                "event-payment-to-projected-triad-penalty inequality",
                "prefix-bounded projected penalty",
            ),
            kill_conditions=("coherent triad packet rebills one owner",),
            novelty_hints=("FourierTriadPositivePenaltyReceipt",),
            expected_reuse=3,
            exposure=1,
        )
    )

    assert score.source_currency_class == "coefficient_tensor_projection"
    assert score.recommendation == "formalize_or_counterexample"
    assert score.net_information_units > 0
    payload = score.as_dict()
    assert payload["canonical_mdl_engine"] == "ztare.fit.mdl.score_item"
    assert payload["mdl_citation_cost"] == 4
    assert payload["positive_projection_receipt"] is True
    assert payload["shell_transport_receipt"] is False


def test_scalar_shell_decoy_ranks_below_triad_projection() -> None:
    scores = score_research_avenues(
        [
            ResearchAvenue(
                avenue_id="scalar_shell",
                description=(
                    "scalar shell coherence price extension without Fourier triad "
                    "tensor projection"
                ),
                receipts=("scalar shell coherence price",),
                kill_conditions=("selected-tree rebilling packet",),
                expected_reuse=2,
                exposure=5,
                prior_negative_receipts=3,
            ),
            ResearchAvenue(
                avenue_id="triad",
                description="resonant triad Lamb tensor projection no-rebilling",
                receipts=("projected coefficient-level penalty",),
                kill_conditions=("coherent triad packet rebills one owner",),
                novelty_hints=("FourierTriadPositivePenaltyReceipt",),
                expected_reuse=3,
                exposure=1,
            ),
        ]
    )

    assert scores[0].avenue_id == "triad"
    assert scores[-1].avenue_id == "scalar_shell"


def test_scalar_shell_price_requires_transport_receipt() -> None:
    score = score_research_avenue(
        ResearchAvenue(
            avenue_id="scalar_shell",
            description="scalar shell Littlewood-Paley shell crossPrice coherencePrice",
            receipts=("scalar shell coherence price",),
            kill_conditions=("selected-tree rebilling packet",),
            expected_reuse=2,
            exposure=5,
            prior_negative_receipts=3,
        )
    )

    assert score.source_currency_class == "scalar_shell_price"
    assert score.recommendation == "defer_until_transport_receipt"


def test_transport_deferral_sorts_before_kill_alias() -> None:
    scores = score_research_avenues(
        [
            ResearchAvenue(
                avenue_id="renamed_prior",
                description="unrelated renamed geometric slogan with no receipt",
                amnesia_hits=6,
                prior_negative_receipts=2,
                expected_reuse=0,
                exposure=5,
            ),
            ResearchAvenue(
                avenue_id="scalar_shell",
                description="scalar shell Littlewood-Paley shell crossPrice coherencePrice",
                receipts=("scalar shell coherence price",),
                kill_conditions=("selected-tree rebilling packet",),
                expected_reuse=2,
                exposure=5,
                prior_negative_receipts=3,
            ),
        ]
    )

    assert [score.avenue_id for score in scores] == [
        "scalar_shell",
        "renamed_prior",
    ]


def test_label_only_coefficient_route_defers_until_receipt() -> None:
    score = score_research_avenue(
        ResearchAvenue(
            avenue_id="label_only",
            description=(
                "Clebsch helicity Lamb vector local frame with Biot-Savart "
                "projection vocabulary"
            ),
            receipts=("helicity density label", "local vortex frame label"),
            kill_conditions=("Biot-Savart projection tail rebills payment",),
            expected_reuse=2,
            exposure=4,
            prior_negative_receipts=2,
        )
    )

    assert score.source_currency_class == "unknown"
    assert score.recommendation == "defer_until_new_receipt"


def test_high_amnesia_unknown_route_is_killed_or_deferred() -> None:
    score = score_research_avenue(
        ResearchAvenue(
            avenue_id="renamed_prior",
            description="unrelated renamed geometric slogan with no receipt",
            amnesia_hits=6,
            prior_negative_receipts=2,
            expected_reuse=1,
            exposure=5,
        )
    )

    assert score.source_currency_class == "unknown"
    assert score.recommendation in {
        "kill_or_alias_to_prior_negative",
        "defer_until_complexity_drops",
        "defer_until_new_receipt",
    }
