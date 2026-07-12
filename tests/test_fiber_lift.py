"""Planted oracle tests for fiber_lift.py.

Level-2 (ls20) structure encoded as a test fixture from goal_hunt_v2 evidence:
  start  = (40, 29)
  KEY    = (45, 49): rotation +1 per hit (repeatable)
  cross2 = (50, 39): timer reset to 84, one-time
  cross1 = (15, 14): timer reset to 84, one-time
  FREEZE = (35, 14): no fiber effect; win position
  timer  = 84 initial, -4/action
  win    = pos == FREEZE, rotation == 3 (after 3 KEY hits)

Evidence reference: goal_hunt_v2_evidence.jsonl (hypothesis rot3_cross1_cross2_freeze)
  - 45-step empirical route; verified live in L2 (levels_completed 1→2)
  - planner should find plan of length ≤ 45 (BFS finds shortest)
"""

import json
from pathlib import Path

import pytest

# Load the real L2 grid from evidence once (session-scoped equivalent via module-level)
_EV_PATH = Path(
    "/Users/daalami/figs_activist_loop/projects/arc3_ls20_gov/workspace/goal_hunt_v2_evidence.jsonl"
)


def _load_l2_grid():
    for line in _EV_PATH.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if "s" in row and "action" in row:
            return row["s"]
    raise RuntimeError("No transition row in goal_hunt_v2_evidence.jsonl")


_GRID = _load_l2_grid()

# ── Fixture effect table (from evidence; mirrors what extract_fiber_effects emits) ──
# ponytail: hardcoded fixture matches the banked evidence exactly, no I/O in test.
_EFFECT_TABLE = {
    "45_49_sig01": {
        "anchor_pos": [45, 49],
        "fiber_effect": {"type": "rotation_increment", "delta_rot": 1},
        "one_time": False,
        "evidence_row_refs": [
            {"source": str(_EV_PATH), "row_idx": 1,
             "note": "hypothesis rot3_cross1_cross2_freeze: KEY at (45,49), rot 0→1→2→3"}
        ],
    },
    "50_39_sig11": {
        "anchor_pos": [50, 39],
        "fiber_effect": {"type": "timer_reset", "reset_value": 84},
        "one_time": True,
        "evidence_row_refs": [
            {"source": str(_EV_PATH), "row_idx": 2,
             "note": "cross2: timer reset on first entry, display rotation preserved"}
        ],
    },
    "15_14_sig11": {
        "anchor_pos": [15, 14],
        "fiber_effect": {"type": "timer_reset", "reset_value": 84},
        "one_time": True,
        "evidence_row_refs": [
            {"source": str(_EV_PATH), "row_idx": 2,
             "note": "cross1: timer reset on first entry, display rotation preserved"}
        ],
    },
    # FREEZE at (35,14) has no fiber effect; not in table so planner treats it as floor
}


def _win_pred(pos, rot, timer, used):
    """Win iff at FREEZE position with rotation 3 (after 3 KEY hits)."""
    return pos == (35, 14) and rot == 3


def _win_pred_no_key(pos, rot, timer, used):
    """Negative test: rotation must be 3 but no KEY in effect table."""
    return rot == 3  # unreachable without KEY effect


# ── Tests ────────────────────────────────────────────────────────────────────

def test_oracle_positive_finds_plan():
    """Planner finds a valid win plan; length must be ≤ 45 (empirical route)."""
    from ztare.worldmodel.fiber_lift import plan_lifted

    start = ((40, 29), (0, 84, frozenset()))
    plan = plan_lifted(
        start, _EFFECT_TABLE, _win_pred,
        grid=_GRID, max_steps=60,
    )
    assert plan is not None, "planner must find a plan"
    assert len(plan) <= 45, f"plan length {len(plan)} exceeds empirical 45-step route"


def test_oracle_plan_valid_fiber_trace():
    """Walk the returned plan and verify fiber invariants at each step."""
    from ztare.worldmodel.fiber_lift import plan_lifted, _build_move_graph, _TIMER_COST

    start_pos = (40, 29)
    start_rot, start_timer, start_used = 0, 84, frozenset()

    plan = plan_lifted(
        (start_pos, (start_rot, start_timer, start_used)),
        _EFFECT_TABLE, _win_pred,
        grid=_GRID, max_steps=60,
    )
    assert plan is not None

    adj = _build_move_graph(_GRID)
    pos = start_pos
    rot, timer, used = start_rot, start_timer, start_used
    pos_map = {(e["anchor_pos"][0], e["anchor_pos"][1]): e
               for e in _EFFECT_TABLE.values()}

    for step, action in enumerate(plan):
        # Find next position
        npos = None
        for a, np_ in adj.get(pos, []):
            if a == action:
                npos = np_
                break
        assert npos is not None, f"step {step}: action {action} not valid from {pos}"

        timer -= _TIMER_COST
        assert timer > 0, f"step {step}: timer exhausted at {timer}"

        if npos in pos_map:
            entry = pos_map[npos]
            eff = entry["fiber_effect"]
            is_one_time = entry.get("one_time", False)
            obj_key = npos
            if not is_one_time or obj_key not in used:
                if eff.get("type") == "rotation_increment":
                    rot = (rot + eff.get("delta_rot", 1)) % 4
                elif eff.get("type") == "timer_reset":
                    timer = eff.get("reset_value", 84)
                if is_one_time:
                    used = frozenset(used | {obj_key})

        pos = npos

    assert _win_pred(pos, rot, timer, used), \
        f"plan terminates at ({pos}, rot={rot}, timer={timer}) — not a win state"


def test_oracle_negative_no_key_returns_none():
    """Without KEY in effect table, rotation 3 is unreachable → must return None."""
    from ztare.worldmodel.fiber_lift import plan_lifted

    empty_table: dict = {}  # no KEY, no CROSS resets
    start = ((40, 29), (0, 84, frozenset()))
    plan = plan_lifted(
        start, empty_table, _win_pred,
        grid=_GRID, max_steps=50,
    )
    assert plan is None, "planner must return None when goal (rot==3) is unreachable"


def test_extract_fiber_effects_from_evidence():
    """extract_fiber_effects identifies KEY and CROSS objects from real evidence rows."""
    from ztare.worldmodel.fiber_lift import extract_fiber_effects

    ep_path = (
        Path("/Users/daalami/figs_activist_loop/projects/arc3_ls20_gov"
             "/workspace/goal_hunt_v2_evidence.jsonl")
    )
    if not ep_path.exists():
        pytest.skip("goal_hunt_v2_evidence.jsonl not present")

    table = extract_fiber_effects([ep_path], grid=_GRID)
    assert table, "table must be non-empty"

    # At least one rotation-increment object found
    rot_objs = [v for v in table.values()
                if v["fiber_effect"].get("type") == "rotation_increment"]
    assert rot_objs, "must find at least one KEY-type (rotation) object"

    # At least one timer-reset object found
    reset_objs = [v for v in table.values()
                  if v["fiber_effect"].get("type") == "timer_reset"]
    assert reset_objs, "must find at least one CROSS-type (timer-reset) object"

    # Evidence refs present (verdicts owe witnesses)
    for obj_id, entry in table.items():
        assert entry["evidence_row_refs"], \
            f"object {obj_id} has no evidence row refs"


def test_extract_from_episode_001():
    """extract_fiber_effects on L1 episode_001 finds the L1 KEY object."""
    from ztare.worldmodel.fiber_lift import extract_fiber_effects

    ep_path = (
        Path("/Users/daalami/figs_activist_loop/projects/arc3_ls20_gov"
             "/raw/episodes/episode_001.jsonl")
    )
    if not ep_path.exists():
        pytest.skip("episode_001.jsonl not present")

    # Use first row's grid as reference
    rows = [json.loads(l) for l in ep_path.read_text().splitlines() if l.strip()]
    ref_grid = next(r["s"] for r in rows if "s" in r)

    table = extract_fiber_effects([ep_path], grid=ref_grid)
    # L1 KEY at (30,19) has {0,1} signature
    key_objs = [v for v in table.values()
                if v["fiber_effect"].get("type") == "rotation_increment"]
    assert key_objs, "L1 KEY at (30,19) must appear as a rotation-increment object"
    row_counts = [v["evidence_row_count"] for v in key_objs]
    assert any(c > 10 for c in row_counts), \
        f"L1 KEY should appear in many rows; got {row_counts}"


if __name__ == "__main__":
    # Self-check without pytest
    test_extract_fiber_effects_from_evidence()
    print("extract test PASS")
    test_oracle_positive_finds_plan()
    print("oracle positive PASS")
    test_oracle_plan_valid_fiber_trace()
    print("fiber trace PASS")
    test_oracle_negative_no_key_returns_none()
    print("oracle negative PASS")
    test_extract_from_episode_001()
    print("episode_001 extract PASS")
    print("all self-checks passed")
