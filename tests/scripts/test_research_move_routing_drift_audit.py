from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts/public/control/research_move_routing_drift_audit.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("research_move_routing_drift_audit", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_valid_primitive_amnesia(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "PRIMITIVE_MODULES = [",
                "    'src/ztare/common/graph_carrier.py',",
                "    'src/ztare/workspace/source_freshness.py',",
                "]",
                "WHEN_TO_USE = {",
                "    'artifact_source_freshness': 'source freshness',",
                "    'canonical_graph_kind_specs': 'graph registry',",
                "    'raw_relative_path': 'raw path normalization',",
                "    'validate_graph_carrier': 'graph receipt',",
                "}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _write_operator_cards(path: Path, card_ids: list[str]) -> None:
    lines = [
        "def OperatorCard(**kwargs):",
        "    return kwargs",
        "CARDS = (",
    ]
    for card_id in card_ids:
        lines.append(f"    OperatorCard(card_id='{card_id}'),")
    lines.append(")")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_current_repo_routing_drift_audit_passes() -> None:
    audit_mod = _load_module()
    result = audit_mod.audit()
    assert result.ok, result.findings


def test_rejects_new_pattern_contract_route_list(tmp_path: Path) -> None:
    audit_mod = _load_module()
    pattern_contract = tmp_path / "pattern_action_contract.py"
    pattern_contract.write_text(
        "\n".join(
            [
                "HARD_RESIDUAL_TOKENS = ('lean',)",
                "GRAPH_CARRIER_PHRASES = ('context graph', 'probability dag')",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    rd_tick_brief = tmp_path / "rd_tick_brief.py"
    rd_tick_brief.write_text(
        "def surface():\n    return route_operator_cards_semantic(context='graph')\n",
        encoding="utf-8",
    )
    primitive_amnesia = tmp_path / "primitive_amnesia.py"
    _write_valid_primitive_amnesia(primitive_amnesia)

    result = audit_mod.audit(
        pattern_action_contract=pattern_contract,
        rd_tick_brief=rd_tick_brief,
        primitive_amnesia=primitive_amnesia,
    )

    assert not result.ok
    assert any("GRAPH_CARRIER_PHRASES" in finding for finding in result.findings)


def test_rejects_reintroduced_claim_boundary_phrase_list(tmp_path: Path) -> None:
    audit_mod = _load_module()
    pattern_contract = tmp_path / "pattern_action_contract.py"
    pattern_contract.write_text(
        "\n".join(
            [
                "HARD_RESIDUAL_TOKENS = ('lean',)",
                "CLAIM_BOUNDARY_PHRASES = ('overclaim', 'narrow claim')",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    rd_tick_brief = tmp_path / "rd_tick_brief.py"
    rd_tick_brief.write_text(
        "def surface():\n    return route_operator_cards_semantic(context='graph')\n",
        encoding="utf-8",
    )
    primitive_amnesia = tmp_path / "primitive_amnesia.py"
    _write_valid_primitive_amnesia(primitive_amnesia)

    result = audit_mod.audit(
        pattern_action_contract=pattern_contract,
        rd_tick_brief=rd_tick_brief,
        primitive_amnesia=primitive_amnesia,
    )

    assert not result.ok
    assert any("CLAIM_BOUNDARY_PHRASES" in finding for finding in result.findings)


def test_rejects_reintroduced_surplus_lift_token_list(tmp_path: Path) -> None:
    audit_mod = _load_module()
    pattern_contract = tmp_path / "pattern_action_contract.py"
    pattern_contract.write_text(
        "\n".join(
            [
                "HARD_RESIDUAL_TOKENS = ('lean',)",
                "SURPLUS_LIFT_TOKENS = ('surplus', 'lift')",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    rd_tick_brief = tmp_path / "rd_tick_brief.py"
    rd_tick_brief.write_text(
        "def surface():\n    return route_operator_cards_semantic(context='graph')\n",
        encoding="utf-8",
    )
    primitive_amnesia = tmp_path / "primitive_amnesia.py"
    _write_valid_primitive_amnesia(primitive_amnesia)

    result = audit_mod.audit(
        pattern_action_contract=pattern_contract,
        rd_tick_brief=rd_tick_brief,
        primitive_amnesia=primitive_amnesia,
    )

    assert not result.ok
    assert any("SURPLUS_LIFT_TOKENS" in finding for finding in result.findings)


def test_rejects_reintroduced_analogy_token_list(tmp_path: Path) -> None:
    audit_mod = _load_module()
    pattern_contract = tmp_path / "pattern_action_contract.py"
    pattern_contract.write_text(
        "\n".join(
            [
                "HARD_RESIDUAL_TOKENS = ('lean',)",
                "ANALOGY_TOKENS = ('analogy', 'transfer')",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    rd_tick_brief = tmp_path / "rd_tick_brief.py"
    rd_tick_brief.write_text(
        "def surface():\n    return route_operator_cards_semantic(context='graph')\n",
        encoding="utf-8",
    )
    primitive_amnesia = tmp_path / "primitive_amnesia.py"
    _write_valid_primitive_amnesia(primitive_amnesia)

    result = audit_mod.audit(
        pattern_action_contract=pattern_contract,
        rd_tick_brief=rd_tick_brief,
        primitive_amnesia=primitive_amnesia,
    )

    assert not result.ok
    assert any("ANALOGY_TOKENS" in finding for finding in result.findings)


def test_rejects_reintroduced_portable_estimate_phrase_list(tmp_path: Path) -> None:
    audit_mod = _load_module()
    pattern_contract = tmp_path / "pattern_action_contract.py"
    pattern_contract.write_text(
        "\n".join(
            [
                "HARD_RESIDUAL_TOKENS = ('lean',)",
                "PORTABLE_ESTIMATE_RECEIPT_PHRASES = ('pec_a', 'auxiliary object')",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    rd_tick_brief = tmp_path / "rd_tick_brief.py"
    rd_tick_brief.write_text(
        "def surface():\n    return route_operator_cards_semantic(context='graph')\n",
        encoding="utf-8",
    )
    primitive_amnesia = tmp_path / "primitive_amnesia.py"
    _write_valid_primitive_amnesia(primitive_amnesia)

    result = audit_mod.audit(
        pattern_action_contract=pattern_contract,
        rd_tick_brief=rd_tick_brief,
        primitive_amnesia=primitive_amnesia,
    )

    assert not result.ok
    assert any("PORTABLE_ESTIMATE_RECEIPT_PHRASES" in finding for finding in result.findings)


def test_rejects_reintroduced_meta_language_phrase_list(tmp_path: Path) -> None:
    audit_mod = _load_module()
    pattern_contract = tmp_path / "pattern_action_contract.py"
    pattern_contract.write_text(
        "\n".join(
            [
                "HARD_RESIDUAL_TOKENS = ('lean',)",
                "META_LANGUAGE_PHRASES = ('mm_02', 'causal edge')",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    rd_tick_brief = tmp_path / "rd_tick_brief.py"
    rd_tick_brief.write_text(
        "def surface():\n    return route_operator_cards_semantic(context='graph')\n",
        encoding="utf-8",
    )
    primitive_amnesia = tmp_path / "primitive_amnesia.py"
    _write_valid_primitive_amnesia(primitive_amnesia)

    result = audit_mod.audit(
        pattern_action_contract=pattern_contract,
        rd_tick_brief=rd_tick_brief,
        primitive_amnesia=primitive_amnesia,
    )

    assert not result.ok
    assert any("META_LANGUAGE_PHRASES" in finding for finding in result.findings)


def test_rejects_any_legacy_pattern_contract_route_list(tmp_path: Path) -> None:
    audit_mod = _load_module()
    pattern_contract = tmp_path / "pattern_action_contract.py"
    pattern_contract.write_text(
        "\n".join(
            [
                "HARD_RESIDUAL_TOKENS = (",
                "    'research_depth_required',",
                "    'recursive_research_required',",
                "    'pde',",
                "    'lean',",
                "    'formal',",
                "    'theorem',",
                "    'lemma',",
                "    'estimate',",
                "    'new brittle keyword',",
                ")",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    rd_tick_brief = tmp_path / "rd_tick_brief.py"
    rd_tick_brief.write_text(
        "def surface():\n    return route_operator_cards_semantic(context='graph')\n",
        encoding="utf-8",
    )
    primitive_amnesia = tmp_path / "primitive_amnesia.py"
    _write_valid_primitive_amnesia(primitive_amnesia)

    result = audit_mod.audit(
        pattern_action_contract=pattern_contract,
        rd_tick_brief=rd_tick_brief,
        primitive_amnesia=primitive_amnesia,
    )

    assert not result.ok
    assert any("owns top-level route lists" in finding for finding in result.findings)


def test_rejects_pattern_contract_matched_terms_branch(tmp_path: Path) -> None:
    audit_mod = _load_module()
    pattern_contract = tmp_path / "pattern_action_contract.py"
    pattern_contract.write_text(
        "\n".join(
            [
                "def surface(card):",
                "    if 'graph' in card.matched_terms:",
                "        return 'graph_diagnostic'",
                "    return 'general'",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    rd_tick_brief = tmp_path / "rd_tick_brief.py"
    rd_tick_brief.write_text(
        "def surface():\n    return route_operator_cards_semantic(context='graph')\n",
        encoding="utf-8",
    )
    primitive_amnesia = tmp_path / "primitive_amnesia.py"
    _write_valid_primitive_amnesia(primitive_amnesia)

    result = audit_mod.audit(
        pattern_action_contract=pattern_contract,
        rd_tick_brief=rd_tick_brief,
        primitive_amnesia=primitive_amnesia,
    )

    assert not result.ok
    assert any("matched_terms" in finding for finding in result.findings)


def test_rejects_missing_required_operator_card(tmp_path: Path) -> None:
    audit_mod = _load_module()
    pattern_contract = tmp_path / "pattern_action_contract.py"
    pattern_contract.write_text("# no local route lists\n", encoding="utf-8")
    rd_tick_brief = tmp_path / "rd_tick_brief.py"
    rd_tick_brief.write_text(
        "def surface():\n    return route_operator_cards_semantic(context='graph')\n",
        encoding="utf-8",
    )
    primitive_amnesia = tmp_path / "primitive_amnesia.py"
    _write_valid_primitive_amnesia(primitive_amnesia)
    primitive_operator_cards = tmp_path / "primitive_operator_cards.py"
    _write_operator_cards(primitive_operator_cards, ["OP-HRD-01"])

    result = audit_mod.audit(
        pattern_action_contract=pattern_contract,
        rd_tick_brief=rd_tick_brief,
        primitive_amnesia=primitive_amnesia,
        primitive_operator_cards=primitive_operator_cards,
    )

    assert not result.ok
    assert any("OP-PDE-01" in finding for finding in result.findings)


def test_rejects_direct_rd_brief_lexical_card_router(tmp_path: Path) -> None:
    audit_mod = _load_module()
    pattern_contract = tmp_path / "pattern_action_contract.py"
    pattern_contract.write_text("HARD_RESIDUAL_TOKENS = ('lean',)\n", encoding="utf-8")
    rd_tick_brief = tmp_path / "rd_tick_brief.py"
    rd_tick_brief.write_text(
        "def surface():\n    return route_operator_cards(context='graph')\n",
        encoding="utf-8",
    )
    primitive_amnesia = tmp_path / "primitive_amnesia.py"
    _write_valid_primitive_amnesia(primitive_amnesia)

    result = audit_mod.audit(
        pattern_action_contract=pattern_contract,
        rd_tick_brief=rd_tick_brief,
        primitive_amnesia=primitive_amnesia,
    )

    assert not result.ok
    assert any("route_operator_cards directly" in finding for finding in result.findings)


def test_rejects_missing_graph_primitive_catalog_declaration(tmp_path: Path) -> None:
    audit_mod = _load_module()
    pattern_contract = tmp_path / "pattern_action_contract.py"
    pattern_contract.write_text("HARD_RESIDUAL_TOKENS = ('lean',)\n", encoding="utf-8")
    rd_tick_brief = tmp_path / "rd_tick_brief.py"
    rd_tick_brief.write_text(
        "def surface():\n    return route_operator_cards_semantic(context='graph')\n",
        encoding="utf-8",
    )
    primitive_amnesia = tmp_path / "primitive_amnesia.py"
    primitive_amnesia.write_text(
        "PRIMITIVE_MODULES = []\nWHEN_TO_USE = {}\n",
        encoding="utf-8",
    )

    result = audit_mod.audit(
        pattern_action_contract=pattern_contract,
        rd_tick_brief=rd_tick_brief,
        primitive_amnesia=primitive_amnesia,
    )

    assert not result.ok
    assert any("PRIMITIVE_MODULES" in finding for finding in result.findings)
    assert any("WHEN_TO_USE" in finding for finding in result.findings)


def test_rejects_missing_source_freshness_primitive_declaration(tmp_path: Path) -> None:
    audit_mod = _load_module()
    pattern_contract = tmp_path / "pattern_action_contract.py"
    pattern_contract.write_text("HARD_RESIDUAL_TOKENS = ('lean',)\n", encoding="utf-8")
    rd_tick_brief = tmp_path / "rd_tick_brief.py"
    rd_tick_brief.write_text(
        "def surface():\n    return route_operator_cards_semantic(context='graph')\n",
        encoding="utf-8",
    )
    primitive_amnesia = tmp_path / "primitive_amnesia.py"
    primitive_amnesia.write_text(
        "\n".join(
            [
                "PRIMITIVE_MODULES = [",
                "    'src/ztare/common/graph_carrier.py',",
                "]",
                "WHEN_TO_USE = {",
                "    'canonical_graph_kind_specs': 'graph registry',",
                "    'validate_graph_carrier': 'graph receipt',",
                "}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = audit_mod.audit(
        pattern_action_contract=pattern_contract,
        rd_tick_brief=rd_tick_brief,
        primitive_amnesia=primitive_amnesia,
    )

    assert not result.ok
    assert any("source_freshness.py" in finding for finding in result.findings)
    assert any("artifact_source_freshness" in finding for finding in result.findings)
    assert any("raw_relative_path" in finding for finding in result.findings)
