"""Gate ACHIEVABILITY receipts for segment-structured holdouts.

The 2026-07-11 incident: episode_002 is four independent 4-step trajectories
(t=[19,20,21,22] repeating, state discontinuities at rows 4/8/12) but
rollout_depth propagated predictions across the boundaries — the hard gate's
threshold (16) was unpassable by construction for ANY law, the true one
included. Its observable was a uniformity fingerprint: every candidate ever
gated scored exactly 4 or 0.

These tests are the planted-oracle pattern: a gate without an achievability
proof is an unfalsifiable examiner.
  1. the TRUE law of a synthetic segmented world must reach depth == total
  2. a WRONG law must still fail (the fix must not weaken the gate)
  3. the real ls20 holdout structure (non-advancing t) must be reseeded
"""
from ztare.worldmodel.episode_log import EpisodeLog, Transition
from ztare.worldmodel.gates import rollout_depth, rollout_diagnostics
from ztare.worldmodel.transition_identity import TransitionIdentity


def _mk_grid(counter: int):
    # 2x3 world: cell (0,0) is a mod-5 counter, rest constant
    return ((counter % 5, 7, 7), (7, 7, 7))


def _true_law(grid, action, t):
    # true dynamics: counter increments by (action+1), everything else constant
    return ((int(grid[0][0] + action + 1) % 5, 7, 7), (7, 7, 7))


def _wrong_law(grid, action, t):
    # off-by-one physics: right shape, wrong increment
    return ((int(grid[0][0] + action + 2) % 5, 7, 7), (7, 7, 7))


def _segmented_holdout(n_segments: int = 4, seg_len: int = 4) -> EpisodeLog:
    """n independent trajectories, each restarting t at 19 and state fresh —
    mirrors the real episode_002 factorial structure."""
    log = EpisodeLog()
    for seg in range(n_segments):
        c = seg  # each segment starts from a DIFFERENT fresh state
        for k in range(seg_len):
            t = 19 + k
            a = (seg + k) % 4
            s = _mk_grid(c)
            c = (c + a + 1) % 5
            log.append(s, a, _mk_grid(c), t=t)
    return log


def test_true_law_achieves_full_depth_on_segmented_holdout():
    """ACHIEVABILITY RECEIPT: the gate must be passable by the true law."""
    hold = _segmented_holdout()
    assert rollout_depth(_true_law, hold) == len(hold)


def test_wrong_law_still_fails_within_segment():
    """The reseed must not weaken the gate: bad physics dies in segment 1."""
    hold = _segmented_holdout()
    assert rollout_depth(_wrong_law, hold) < 4


def test_partially_right_law_stops_at_first_real_error():
    """A law wrong only from segment 2's start state scores exactly seg 1."""
    def seg1_only(grid, action, t):
        if grid[0][0] == 0 or True:  # true law everywhere...
            out = _true_law(grid, action, t)
        return out

    # law that breaks specifically on segment-2 start (counter==1 at t==19)
    def breaks_on_seg2(grid, action, t):
        if grid[0][0] == 1 and t == 19:
            return _wrong_law(grid, action, t)
        return _true_law(grid, action, t)

    hold = _segmented_holdout()
    assert rollout_depth(breaks_on_seg2, hold) == 4


def test_continuous_holdout_semantics_unchanged():
    """Single-trajectory holdouts (advancing t) keep true-rollout semantics:
    propagation is NOT reseeded when t advances."""
    log = EpisodeLog()
    c = 0
    for k in range(8):
        s = _mk_grid(c)
        a = k % 4
        c = (c + a + 1) % 5
        log.append(s, a, _mk_grid(c), t=10 + k)
    assert rollout_depth(_true_law, log) == 8
    assert rollout_depth(_wrong_law, log) < 8


def test_environment_boundary_successor_cannot_change_rollout_verdict():
    """A boundary presentation is excluded and severs propagation."""
    regular = TransitionIdentity(
        kind="dynamics",
        authority="environment_adapter",
        source_epoch=2,
        target_epoch=2,
        evidence_refs=("test:dynamics",),
    )
    boundary = TransitionIdentity(
        kind="reset_boundary",
        authority="environment_adapter",
        source_epoch=2,
        target_epoch=3,
        boundary_kind="non_discharge_respawn",
        evidence_refs=("test:boundary",),
    )
    verdicts = []
    for boundary_successor in (_mk_grid(0), _mk_grid(4)):
        log = EpisodeLog([
            Transition(10, _mk_grid(0), 0, _mk_grid(1), regular),
            Transition(11, _mk_grid(1), 3, boundary_successor, boundary),
            Transition(12, _mk_grid(3), 1, _mk_grid(0), regular),
        ])
        verdicts.append(rollout_diagnostics(_true_law, log))

    assert verdicts == [
        {
            "rollout_depth": 2,
            "scored_rows": 2,
            "environment_frames_excluded": 1,
        }
    ] * 2
