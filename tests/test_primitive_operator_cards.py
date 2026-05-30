from pathlib import Path
import importlib.util

from src.ztare.research_director.primitive_operator_cards import (
    render_operator_cards,
    route_operator_cards,
    write_operator_cards,
)


def test_routes_proxy_evidence_to_evidence_carrier_card() -> None:
    cards = route_operator_cards(
        context=(
            "The claim update depends on proxy measurement and indirect evidence. "
            "We need a receipt before treating the readout as validation."
        )
    )
    assert cards
    assert cards[0].card_id == "OP-ECR-01"
    assert "claim update" in cards[0].matched_terms
    assert "4-row table" in " ".join(cards[0].required_output)


def test_routes_analogy_to_cross_frame_transfer_card() -> None:
    cards = route_operator_cards(
        context=(
            "Use reasoning by analogy: translate a state pricing representation "
            "into the target frame and audit invariant preservation."
        )
    )
    assert cards
    assert cards[0].card_id == "OP-XFT-01"
    assert "analogy" in cards[0].matched_terms


def test_routes_surplus_lift_projection_certificate_card() -> None:
    cards = route_operator_cards(
        context=(
            "Lift to a high-dimensional lattice, use entropy surplus over "
            "quotient loss, then project back with injective multiplicity."
        )
    )
    assert cards
    assert cards[0].card_id == "OP-SLP-01"
    assert "surplus" in cards[0].matched_terms
    assert "project" in cards[0].matched_terms
    assert "target-size" in " ".join(cards[0].required_output)


def test_no_context_returns_no_cards() -> None:
    assert route_operator_cards(context="plain status update with no research bottleneck") == []


def test_render_and_write_are_standalone(tmp_path: Path) -> None:
    out = tmp_path / "cards.json"
    cards = write_operator_cards(
        out,
        context="local pieces need global compatibility and interface checks",
    )
    text = render_operator_cards(cards)
    assert out.exists()
    assert "OP-LGA-01" in text
    assert "operator_card_surface_ok = True" in text
    assert "nearest-confuser disambiguators" in text


def test_render_names_action_constraint_fields_not_schema_as_cause() -> None:
    cards = route_operator_cards(
        context="scope boundary claim update needs answer object and success criterion",
    )
    text = render_operator_cards(cards)
    assert "action-constraint fields:" in text
    assert "typed schema fields:" not in text


def test_tie_order_is_deterministic_by_card_id() -> None:
    cards = route_operator_cards(context="scope boundary")
    assert [card.card_id for card in cards[:2]] == ["OP-CBM-01", "OP-BCG-01"]


def test_branch_interface_claim_boundary_disambiguators_are_present() -> None:
    cards = route_operator_cards(
        context=(
            "Multiple criteria and regimes are required before an aggregate claim, "
            "but local pieces also need an interface handoff."
        ),
        top_n=3,
    )
    by_id = {card.card_id: card for card in cards}
    assert "OP-BCG-01" in by_id
    assert "OP-LGA-01" in by_id
    assert any("Prefer interface over branch" in item for item in by_id["OP-BCG-01"].disambiguators)
    assert any("Prefer branch over interface" in item for item in by_id["OP-LGA-01"].disambiguators)


def test_top_one_suppresses_secondary_card() -> None:
    cards = route_operator_cards(context="scope boundary", top_n=1)
    text = render_operator_cards(cards)
    assert len(cards) == 1
    assert "secondary breaker candidate" not in text


def test_router_ignores_generic_task_boilerplate_claim_update() -> None:
    cards = route_operator_cards(
        context=(
            "Multiple criteria and regimes determine the decision. "
            "Produce the single next audit artifact and falsifier before a larger claim update. "
            "Do not output family names, taxonomy labels, protocol names, or op ids."
        )
    )
    assert cards
    assert cards[0].card_id == "OP-BCG-01"


def test_routes_question_replacement_to_claim_boundary_family() -> None:
    cards = route_operator_cards(
        context=(
            "The proposal replaces the old question with a new question about "
            "dominance certificates and impossibility witnesses as the usable answer object."
        )
    )
    assert cards
    assert cards[0].card_id == "OP-CBM-01"
    assert any("question_game_reframing" in item for item in cards[0].fine_handles)
    assert any("claim_boundary_split" in item for item in cards[0].fine_handles)
    assert "answer_object" in " ".join(cards[0].required_output)
    assert "success_criterion" in " ".join(cards[0].required_output)


def test_routes_encoding_representatives_to_cross_frame_family() -> None:
    cards = route_operator_cards(
        context=(
            "The same policy has multiple encodings; the audit treats each encoding "
            "as a representative and checks which obligations are preserved."
        )
    )
    assert cards
    assert cards[0].card_id == "OP-XFT-01"
    assert any("structural_semantics_quotient" in item for item in cards[0].fine_handles)
    assert any("source_target_transfer" in item for item in cards[0].fine_handles)
    text = " ".join(cards[0].required_output + cards[0].fine_handles)
    assert "equivalence-class" in text
    assert "disagreement witness" in text


def test_routes_v88_topology_restriction_to_branch_coverage() -> None:
    cards = route_operator_cards(
        context="The paper restricts the data to non-self crossings and excluded regimes need coverage."
    )
    assert cards
    assert cards[0].card_id == "OP-BCG-01"


def test_routes_v88_invariant_relation_failure_to_claim_boundary() -> None:
    cards = route_operator_cards(
        context=(
            "Some directions of inequality can fail when a coefficient vanishes; "
            "later results treat localized nonlinearities and half-line cases separately."
        )
    )
    assert cards
    assert cards[0].card_id == "OP-CBM-01"


def test_cli_match_and_no_match_exit_codes(tmp_path: Path, capsys) -> None:
    script = Path("scripts/public/control/primitive_operator_cards.py").resolve()
    spec = importlib.util.spec_from_file_location("primitive_operator_cards_cli", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    out = tmp_path / "cards.json"
    rc = module.main([
        "--context",
        "proxy measurement requires a receipt before a claim update",
        "--out",
        str(out),
    ])
    captured = capsys.readouterr()
    assert rc == 0
    assert "OP-ECR-01" in captured.out
    assert out.exists()

    rc = module.main(["--context", "plain status update", "--out", str(tmp_path / "none.json")])
    assert rc == 1


def test_cli_context_file(tmp_path: Path, capsys) -> None:
    script = Path("scripts/public/control/primitive_operator_cards.py").resolve()
    spec = importlib.util.spec_from_file_location("primitive_operator_cards_cli_file", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    context = tmp_path / "context.txt"
    context.write_text("local pieces require interface compatibility before a global claim", encoding="utf-8")
    rc = module.main([
        "--context-file",
        str(context),
        "--out",
        str(tmp_path / "cards.json"),
        "--top",
        "1",
    ])
    captured = capsys.readouterr()
    assert rc == 0
    assert "OP-LGA-01" in captured.out
    assert "secondary breaker candidate" not in captured.out

def test_render_surfaces_action_target_source_guard() -> None:
    cards = route_operator_cards(context="proxy measurement requires a receipt before a claim update")
    text = render_operator_cards(cards)
    assert "action-target guard" in text
    assert "infer the action target from source facts" in text

