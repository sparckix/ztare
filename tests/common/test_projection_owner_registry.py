from __future__ import annotations

from pathlib import Path

from ztare.common.projection_owner_registry import (
    PROJECTION_OWNERS,
    VISIBLE_WORKBENCH_SOURCE_REFS,
    projection_blast_radius,
    projection_owner,
    validate_projection_owner_registry,
)


def test_projection_owner_registry_resolves_core_contracts() -> None:
    ids = {owner.concept_id for owner in PROJECTION_OWNERS}

    assert "science_output_policy" in ids
    assert "boundary_cegar_automaton" in ids
    assert "strategy_card_decision_membrane" in ids
    assert "leaf_workbench_contract" in ids
    assert "agentic_briefing_pack" in ids
    assert "control_receipt_read_model" in ids
    assert "visible_workbench_source_membrane" in ids


def test_projection_blast_radius_names_dependent_surfaces() -> None:
    radius = projection_blast_radius("boundary_cegar_automaton")

    assert "src/ztare/common/sealed_boundary_cegar.py" in radius
    assert "src/ztare/worldmodel/retry_surface.py" in radius
    assert "tests/common/test_sealed_boundary_cegar.py" in radius
    assert "docs/concepts/arc_agi_3_system.md" in radius


def test_projection_owner_registry_paths_and_symbols_exist() -> None:
    root = Path(__file__).resolve().parents[2]

    assert validate_projection_owner_registry(repo_root=root) == []


def test_strategy_card_membrane_points_to_single_write_owner() -> None:
    owner = projection_owner("strategy_card_decision_membrane")

    assert owner is not None
    assert owner.owner_module == "ztare.research_director.strategy_decision_policy"
    assert "submit_strategy_card_batch" in owner.owner_symbols


def test_worldmodel_prompt_surfaces_cover_high_risk_renderers() -> None:
    radius = set(projection_blast_radius("worldmodel_prompt_surfaces"))

    assert "src/ztare/common/briefing_pack.py" in radius
    assert "src/ztare/worldmodel/retry_surface.py" in radius
    assert "src/ztare/validator/worldmodel_typed_payload.py" in radius
    assert "src/ztare/orchestrator/submission_path_helpers.py" in radius
    assert "src/ztare/orchestrator/briefing_providers/strategy_experiments.py" in radius
    assert "src/ztare/orchestrator/briefing_providers/leaf_workbench.py" in radius


def test_visible_workbench_source_refs_are_curated_execution_membrane() -> None:
    root = Path(__file__).resolve().parents[2]
    refs = set(VISIBLE_WORKBENCH_SOURCE_REFS)

    assert len(VISIBLE_WORKBENCH_SOURCE_REFS) <= 45
    assert "src/ztare/common/visible_workbench_cli.py" in refs
    assert "src/ztare/common/visible_workbench_actions.py" in refs
    assert "src/ztare/common/projection_owner_registry.py" in refs
    assert "src/ztare/common/equivariance.py" in refs
    assert "src/ztare/common/observation_chart.py" in refs
    assert "src/ztare/worldmodel/transition_identity.py" in refs
    assert "src/ztare/worldmodel/evidence_consolidation.py" in refs
    assert "src/ztare/worldmodel/gates.py" in refs
    assert "src/ztare/worldmodel/spec_abduction.py" in refs
    assert "tests/test_dispatch_model.py" not in refs
    assert all((root / ref).exists() for ref in refs)


def test_control_receipt_read_model_blast_radius_names_policy_callers() -> None:
    radius = set(projection_blast_radius("control_receipt_read_model"))

    assert "src/ztare/common/control_state_machine.py" in radius
    assert "src/ztare/common/leaf_workbench_executor.py" in radius
    assert "src/ztare/validator/core/candidate_preflight.py" in radius
    assert "src/ztare/validator/core/repair_preflight.py" in radius
    assert "src/ztare/validator/autoresearch_loop.py" in radius
