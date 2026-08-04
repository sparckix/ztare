from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from ztare.common.wake_sleep_credit_router import MemoryScope


def _load():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts/public/control/arc3_pairwise_memory_content_probe.py"
    )
    spec = importlib.util.spec_from_file_location(
        "arc3_pairwise_memory_content_probe_under_test",
        path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _paths() -> tuple[Path, Path]:
    base = (
        Path(__file__).resolve().parents[1]
        / "research_areas/pre_registrations"
        / "arc3_consumer_indexed_exception_frontier_20260723"
    )
    return (
        base / "h86_level_boundary_microsleep_result.json",
        base / "h88_pairwise_memory_content_spec.json",
    )


def test_condition_spec_selects_disjoint_source_supported_memories() -> None:
    module = _load()
    source_path, spec_path = _paths()
    _meta, left, right, _turns = module._load_source(
        source_path,
        spec_path,
    )

    left_ids = {row["memory_id"] for row in left["memories"]}
    right_ids = {row["memory_id"] for row in right["memories"]}
    assert left_ids == {
        "goal_requires_glyph_match_v1",
        "floor_marker_edits_state_glyph_v1",
    }
    assert left_ids.isdisjoint(right_ids)


def test_condition_presentations_have_exact_equal_canonical_bytes() -> None:
    module = _load()
    source_path, spec_path = _paths()
    meta, left, right, turns = module._load_source(
        source_path,
        spec_path,
    )
    source = json.loads(source_path.read_text(encoding="utf-8"))
    source_scope = source["sleep_cycles"][0]["selected_digest"]["scope"]
    scope = MemoryScope(
        task_sha256=source_scope["task_sha256"],
        controller_sha256=source_scope["controller_sha256"],
        context_sha256="restored-observation",
        choice_set_sha256=source_scope["choice_set_sha256"],
        action_vocabulary_sha256=(
            source_scope["action_vocabulary_sha256"]
        ),
    )
    left_provenance = module._condition_provenance(
        source_meta=meta,
        condition=left,
        turns=turns,
    )
    right_provenance = module._condition_provenance(
        source_meta=meta,
        condition=right,
        turns=turns,
    )
    left_base = module._condition_bundle_base(
        condition=left,
        provenance=left_provenance,
        scope=scope,
        source_meta=meta,
    )
    right_base = module._condition_bundle_base(
        condition=right,
        provenance=right_provenance,
        scope=scope,
        source_meta=meta,
    )
    left_digest, right_digest, expected = (
        module._equalize_rendered_bytes(left_base, right_base)
    )

    assert (
        len(module._canonical_json(left_digest).encode("utf-8"))
        == expected
    )
    assert (
        len(module._canonical_json(right_digest).encode("utf-8"))
        == expected
    )
    assert left_digest["condition_id"] != right_digest["condition_id"]


def test_pair_orders_can_freeze_reverse_order_replication() -> None:
    module = _load()

    assert module._pair_orders(
        3,
        "ignored-by-frozen-order",
        order_mode="right-first",
    ) == [
        ["right", "left"],
        ["right", "left"],
        ["right", "left"],
    ]


def test_prior_outcome_credit_changes_heldout_selector_assignment() -> None:
    module = _load()
    source_path, spec_path = _paths()
    base = spec_path.parent
    credit_result_path = (
        base / "h89_pairwise_memory_content_reverse/result.json"
    )
    credit_result = json.loads(
        credit_result_path.read_text(encoding="utf-8")
    )
    scope_row = credit_result["pairs"][0]["stratum"]["scope"]
    scope = MemoryScope(
        task_sha256=scope_row["task_sha256"],
        controller_sha256=scope_row["controller_sha256"],
        context_sha256=scope_row["context_sha256"],
        choice_set_sha256=scope_row["choice_set_sha256"],
        action_vocabulary_sha256=scope_row[
            "action_vocabulary_sha256"
        ],
    )
    meta, left, right, turns = module._load_source(
        source_path,
        spec_path,
    )
    left_provenance = module._condition_provenance(
        source_meta=meta,
        condition=left,
        turns=turns,
    )
    right_provenance = module._condition_provenance(
        source_meta=meta,
        condition=right,
        turns=turns,
    )
    left_digest, right_digest, rendered_bytes = (
        module._equalize_rendered_bytes(
            module._condition_bundle_base(
                condition=left,
                provenance=left_provenance,
                scope=scope,
                source_meta=meta,
            ),
            module._condition_bundle_base(
                condition=right,
                provenance=right_provenance,
                scope=scope,
                source_meta=meta,
            ),
        )
    )
    left_proposal = module._proposal(
        condition=left,
        digest=left_digest,
        provenance=left_provenance,
        scope=scope,
        budget=20,
        rendered_bytes=rendered_bytes,
    )
    right_proposal = module._proposal(
        condition=right,
        digest=right_digest,
        provenance=right_provenance,
        scope=scope,
        budget=20,
        rendered_bytes=rendered_bytes,
    )

    learned, producer_prior, receipt = module._selector_assignments(
        credit_result_path=credit_result_path,
        condition_rows=(
            (left, left_digest, left_proposal),
            (right, right_digest, right_proposal),
        ),
        scope=scope,
        rendered_bytes=rendered_bytes,
    )

    assert learned[0]["condition_id"] == "causal_mechanics"
    assert (
        producer_prior[0]["condition_id"]
        == "redundant_true_memory"
    )
    assert receipt["left_role"] == "outcome_trained_selector"
    assert receipt["right_role"] == "producer_prior_selector"
    assert module._pair_orders(
        4,
        "ignored-by-frozen-order",
        order_mode="alternating",
    ) == [
        ["left", "right"],
        ["right", "left"],
        ["left", "right"],
        ["right", "left"],
    ]
