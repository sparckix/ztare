from ztare.pde.applicability_cards import (
    applicability_card_retrieval,
    render_applicability_cards,
)


def test_applicability_card_retrieval_ranks_query_and_runs_applicability() -> None:
    theorem_db = {
        "annular_riesz_payment": {
            "requires": {
                "annular_bandlimit": True,
                "riesz_l1": True,
                "same_carrier": True,
            },
            "concludes": {"trace_payment": True},
            "does_not_accept": ["raw_cz"],
        },
        "energy_localization": {
            "requires": {"cutoff_energy": True},
            "concludes": {"energy_bound": True},
            "does_not_accept": [],
        },
    }

    cards = applicability_card_retrieval(
        theorem_db,
        query="annular Riesz L1 payment",
        available={"annular_bandlimit": True, "raw_cz": True},
        source_profile="toy",
        top_k=2,
    )

    assert cards[0]["schema"] == "pde-applicability-card-v1"
    assert cards[0]["theorem_id"] == "annular_riesz_payment"
    assert cards[0]["source_profile"] == "toy"
    assert cards[0]["applicability"]["verdict"] == "NO_MATCH"
    assert cards[0]["applicability"]["missing_fields"] == [
        "riesz_l1",
        "same_carrier",
    ]
    assert cards[0]["applicability"]["rejected_substitutes"] == ["raw_cz"]


def test_render_applicability_cards_is_compact() -> None:
    cards = applicability_card_retrieval(
        {
            "toy": {
                "requires": {"field": True},
                "concludes": {},
                "does_not_accept": [],
            }
        },
        query="toy field",
        top_k=1,
    )

    rendered = render_applicability_cards(cards)
    assert "toy" in rendered
    assert "verdict" in rendered
