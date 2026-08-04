from __future__ import annotations

import importlib.util
from pathlib import Path

from ztare.common.wake_sleep_credit_router import MemoryScope


def _load():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts/public/control/arc3_paired_recall_probe.py"
    )
    spec = importlib.util.spec_from_file_location(
        "arc3_paired_recall_probe_under_test",
        path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_source_provenance_is_separate_from_consumption_scope() -> None:
    module = _load()
    source_path = (
        Path(__file__).resolve().parents[1]
        / "research_areas/pre_registrations"
        / "arc3_consumer_indexed_exception_frontier_20260723"
        / "h86_level_boundary_microsleep_result.json"
    )
    source, selected = module._source_bundle(source_path)
    source_scope = source["source_scope"]
    scope = MemoryScope(
        task_sha256=source_scope["task_sha256"],
        controller_sha256=source_scope["controller_sha256"],
        context_sha256="restored-initial-observation",
        choice_set_sha256=source_scope["choice_set_sha256"],
        action_vocabulary_sha256=(
            source_scope["action_vocabulary_sha256"]
        ),
    )

    candidate, digest, transport = module._candidate_and_digest(
        source_receipt=source,
        selected_source_digest=selected,
        scope=scope,
        primitive_action_cost=20.0,
        predicted_decision_delta=0.2,
    )

    assert (
        candidate.acquisition_provenance.observation_sha256
        != candidate.scope.context_sha256
    )
    assert digest["consumption_scope_sha256"] == scope.sha256
    assert (
        digest["acquisition_provenance"]["sha256"]
        == candidate.acquisition_provenance.sha256
    )
    assert transport["preserved_fields"] == [
        "task_sha256",
        "controller_sha256",
        "choice_set_sha256",
        "action_vocabulary_sha256",
    ]


def test_seeded_arm_order_and_metrics_are_deterministic() -> None:
    module = _load()
    assert module._pair_orders(3, "sealed-seed") == (
        module._pair_orders(3, "sealed-seed")
    )
    metrics = module._outcome_metrics({
        "budget": 4,
        "first_level_action": 3,
        "turns": [
            {"successor_observation_sha256": "a"},
            {"successor_observation_sha256": "b"},
            {"successor_observation_sha256": "b"},
            {"successor_observation_sha256": "c"},
        ],
    })
    assert metrics["task_score"] == 1.0
    assert metrics["efficiency_score"] == 0.5
    assert metrics["information_yield"] == 0.75
