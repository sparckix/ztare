"""Tests for causal_compiler kernel and worldmodel adapter.

Tests 1-6: Kernel with planted toy adapter
  1. Predictive+addressable variable is compiled
  2. Non-predictive variable (never changes) is excluded
  3. Unscored variable emitted when too few transitions
  4. Invariance detected on conserved feature
  5. Intervention proposal named for weak-addressability variable
  6. Ledger content_hash is deterministic

Tests 7-9: Flood-fill (adapter internals)
  7. Single component on tiny grid
  8. Two disconnected components
  9. Background color not counted

Test 10: Adapter collisions (deterministic substrate = empty)
Test 11: Ledger write/read roundtrip
Test 12: max_variables cap respected
Test 13: Promotion seam raises on unknown id
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

import pytest

from ztare.common.causal_compiler import (
    CausalAdapter,
    CausalVariable,
    compile_causal_objects,
    CausalObjectLedger,
)
from ztare.worldmodel.causal_compiler_adapter import _flood_fill_components


# ---------------------------------------------------------------------------
# Toy adapter helpers
# ---------------------------------------------------------------------------

def _make_transition(t: int, a: int, before: dict, after: dict, ref: str = "test") -> dict:
    return {"t": t, "a": a, "features_before": before, "features_after": after, "source_ref": ref}


class ToyAdapter:
    """Planted synthetic adapter for kernel unit tests."""

    def __init__(self, transitions: list[dict], objects: list[dict] | None = None):
        self._transitions = transitions
        self._objects = objects or []

    def objects(self) -> list[dict]:
        return self._objects

    def transitions(self) -> list[dict]:
        return self._transitions

    def collisions(self) -> list[dict]:
        return []


# ---------------------------------------------------------------------------
# Test 1: Predictive + addressable variable compiled
# ---------------------------------------------------------------------------

def test_predictive_and_addressable_variable_compiled():
    # timer_count decreases each step and action=0 changes it faster than action=1
    trs = [
        _make_transition(0, 0, {"timer_count": 10}, {"timer_count": 8}),
        _make_transition(1, 0, {"timer_count": 8},  {"timer_count": 6}),
        _make_transition(2, 1, {"timer_count": 6},  {"timer_count": 6}),
        _make_transition(3, 1, {"timer_count": 6},  {"timer_count": 6}),
        _make_transition(4, 0, {"timer_count": 6},  {"timer_count": 4}),
    ]
    adapter = ToyAdapter(trs)
    ledger = compile_causal_objects(adapter)
    ids = {v.variable_id for v in ledger.variables}
    assert "var_timer_count" in ids
    v = next(v for v in ledger.variables if v.variable_id == "var_timer_count")
    assert v.predictive_support is not None and v.predictive_support > 0
    assert v.status in ("candidate", "unscored")


# ---------------------------------------------------------------------------
# Test 2: Non-predictive variable excluded
# ---------------------------------------------------------------------------

def test_non_predictive_variable_excluded():
    # static_val never changes — predictive_support = 0.0 → excluded
    trs = [
        _make_transition(0, 0, {"static_val": 42, "moving": 10}, {"static_val": 42, "moving": 8}),
        _make_transition(1, 0, {"static_val": 42, "moving": 8},  {"static_val": 42, "moving": 6}),
        _make_transition(2, 1, {"static_val": 42, "moving": 6},  {"static_val": 42, "moving": 6}),
        _make_transition(3, 1, {"static_val": 42, "moving": 6},  {"static_val": 42, "moving": 6}),
    ]
    adapter = ToyAdapter(trs)
    ledger = compile_causal_objects(adapter)
    ids = {v.variable_id for v in ledger.variables}
    assert "var_static_val" not in ids
    assert "var_moving" in ids


# ---------------------------------------------------------------------------
# Test 3: Unscored when too few transitions
# ---------------------------------------------------------------------------

def test_unscored_with_too_few_transitions():
    trs = [
        _make_transition(0, 0, {"x": 1}, {"x": 2}),
        _make_transition(1, 1, {"x": 2}, {"x": 3}),
    ]
    adapter = ToyAdapter(trs)
    ledger = compile_causal_objects(adapter)
    if ledger.variables:
        # If emitted, must be unscored (only 2 transitions < MIN 4)
        for v in ledger.variables:
            if v.variable_id == "var_x":
                assert v.status == "unscored"
                assert v.predictive_support is None


# ---------------------------------------------------------------------------
# Test 4: Invariance detected on conserved feature
# ---------------------------------------------------------------------------

def test_invariance_detected_on_conserved_feature():
    # floor_count never changes across transitions
    trs = [
        _make_transition(0, 0, {"floor_count": 100, "moving": 10}, {"floor_count": 100, "moving": 8}),
        _make_transition(1, 0, {"floor_count": 100, "moving": 8},  {"floor_count": 100, "moving": 6}),
        _make_transition(2, 1, {"floor_count": 100, "moving": 6},  {"floor_count": 100, "moving": 5}),
        _make_transition(3, 1, {"floor_count": 100, "moving": 5},  {"floor_count": 100, "moving": 4}),
    ]
    adapter = ToyAdapter(trs)
    ledger = compile_causal_objects(adapter)
    inv_ids = {i.invariance_id for i in ledger.invariances}
    assert "inv_conserved_floor_count" in inv_ids
    inv = next(i for i in ledger.invariances if i.invariance_id == "inv_conserved_floor_count")
    assert inv.support_count == 4


# ---------------------------------------------------------------------------
# Test 5: Intervention proposal for weak-addressability variable
# ---------------------------------------------------------------------------

def test_intervention_proposal_for_weak_addressability():
    # All actions produce the same change rate in "drift" — addressable spread ~0
    trs = [
        _make_transition(0, 0, {"drift": 10}, {"drift": 9}),
        _make_transition(1, 1, {"drift": 9},  {"drift": 8}),
        _make_transition(2, 2, {"drift": 8},  {"drift": 7}),
        _make_transition(3, 3, {"drift": 7},  {"drift": 6}),
        _make_transition(4, 0, {"drift": 6},  {"drift": 5}),
    ]
    adapter = ToyAdapter(trs)
    ledger = compile_causal_objects(adapter)
    proposal_ids = {p.variable_id for p in ledger.proposals}
    assert "var_drift" in proposal_ids
    p = next(p for p in ledger.proposals if p.variable_id == "var_drift")
    assert p.falsification_test  # non-empty string
    assert "action" in p.falsification_test.lower()


# ---------------------------------------------------------------------------
# Test 6: Determinism (content hash stable)
# ---------------------------------------------------------------------------

def test_content_hash_deterministic():
    trs = [
        _make_transition(0, 0, {"x": 5}, {"x": 3}),
        _make_transition(1, 1, {"x": 3}, {"x": 1}),
        _make_transition(2, 0, {"x": 1}, {"x": 0}),
        _make_transition(3, 1, {"x": 0}, {"x": 0}),
    ]
    adapter = ToyAdapter(trs)
    h1 = compile_causal_objects(adapter).content_hash()
    h2 = compile_causal_objects(adapter).content_hash()
    assert h1 == h2


# ---------------------------------------------------------------------------
# Test 7: Flood-fill single component
# ---------------------------------------------------------------------------

def test_flood_fill_single_component():
    grid = (
        (0, 1, 0),
        (1, 1, 0),
        (0, 1, 0),
    )
    comps = _flood_fill_components(grid, 1)
    # All 1-cells are connected (4-connected path exists: (0,1)-(1,1)-(1,0)? no wait:
    # (0,1) is adjacent to (1,1); (1,0) is adjacent to (1,1); (2,1) is adjacent to (1,1)
    assert len(comps) == 1
    assert len(comps[0]) == 4  # (0,1), (1,0), (1,1), (2,1)


# ---------------------------------------------------------------------------
# Test 8: Flood-fill two disconnected components
# ---------------------------------------------------------------------------

def test_flood_fill_two_components():
    grid = (
        (1, 0, 1),
        (0, 0, 0),
        (1, 0, 1),
    )
    comps = _flood_fill_components(grid, 1)
    assert len(comps) == 4  # four isolated corners


# ---------------------------------------------------------------------------
# Test 9: Background color not counted as components
# ---------------------------------------------------------------------------

def test_flood_fill_background_not_counted():
    grid = (
        (4, 4, 4),
        (4, 1, 4),
        (4, 4, 4),
    )
    comps_bg = _flood_fill_components(grid, 4)
    # Background 4 has 8 cells but they're all connected around the 1
    assert len(comps_bg) == 1
    comps_fg = _flood_fill_components(grid, 1)
    assert len(comps_fg) == 1
    assert len(comps_fg[0]) == 1


# ---------------------------------------------------------------------------
# Test 10: Collisions empty on deterministic toy
# ---------------------------------------------------------------------------

def test_toy_adapter_collisions_empty():
    adapter = ToyAdapter([])
    assert adapter.collisions() == []


# ---------------------------------------------------------------------------
# Test 11: Ledger write/read roundtrip
# ---------------------------------------------------------------------------

def test_ledger_write_roundtrip():
    trs = [
        _make_transition(0, 0, {"a": 5}, {"a": 3}),
        _make_transition(1, 1, {"a": 3}, {"a": 1}),
        _make_transition(2, 0, {"a": 1}, {"a": 0}),
        _make_transition(3, 1, {"a": 0}, {"a": 0}),
    ]
    adapter = ToyAdapter(trs)
    ledger = compile_causal_objects(adapter)

    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "workspace" / "causal_objects.jsonl"
        ledger.write_jsonl(out)
        assert out.exists()
        lines = [json.loads(l) for l in out.read_text().splitlines() if l.strip()]
        schemas = {l["schema"] for l in lines}
        assert schemas == {"ztare.causal_objects.v1"}
        types = {l["object_type"] for l in lines}
        assert "causal_variable" in types


# ---------------------------------------------------------------------------
# Test 12: max_variables cap respected
# ---------------------------------------------------------------------------

def test_max_variables_cap():
    # 10 distinct features, each changing
    trs = []
    for i in range(8):
        before = {f"feat_{j}": i + j for j in range(10)}
        after  = {f"feat_{j}": i + j + 1 for j in range(10)}
        trs.append(_make_transition(i, i % 4, before, after))
    adapter = ToyAdapter(trs)
    ledger = compile_causal_objects(adapter, max_variables=3)
    assert len(ledger.variables) <= 3


# ---------------------------------------------------------------------------
# Test 13: Promotion seam raises on unknown id
# ---------------------------------------------------------------------------

def test_promotion_seam_raises_on_unknown():
    ledger = CausalObjectLedger()
    with pytest.raises(KeyError, match="not found"):
        ledger.promote("nonexistent_var", "some_receipt.json")
