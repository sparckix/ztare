"""Visible-replay nogood learning for the spec-abduction proposer.

Covers the three hard invariants: the contamination firewall (a holdout clause
is REFUSED by the consult path), env-gated default-off inertness, cross-run
pruning of a matching candidate, and winner-preservation (a clause never prunes
a spec that gates clean)."""
import os

import pytest

from ztare.common.conflict_ledger import ConflictClause
from ztare.worldmodel import spec_nogood as sng
from ztare.worldmodel.grid_dsl import grid_from_lists


class _Tr:
    def __init__(self, s, a, s_next, t):
        self.s = grid_from_lists(s)
        self.a = a
        self.s_next = grid_from_lists(s_next)
        self.t = t


def _recolor_frag(mapping):
    """A tiny lowered step: apply a color->color recolor. Stands in for a lowered
    candidate spec so the tests need no catalog machinery."""
    m = {int(k): int(v) for k, v in mapping.items()}

    def step(s, a, t):
        return tuple(tuple(m.get(c, c) for c in row) for row in s)
    return step


def test_visible_clause_prunes_matching_candidate(tmp_path):
    led = sng.SpecNogoodLedger(tmp_path)
    rules = [{"op": "recolor_map", "mapping": {"1": 9}}]
    # candidate predicts all-9 but truth keeps the 1 -> visible mismatch
    tr = _Tr([[1, 1]], 0, [[1, 1]], t=3)
    pred = _recolor_frag({"1": 9})(tr.s, 0, 3)
    led.record_visible(rules, tr, pred)

    clause = led.blocks(sng.behavior_signature(rules))
    assert clause is not None
    assert clause.provenance["evidence"] == "visible"
    # the SAME candidate provably reproduces the recorded wrong prediction -> prune
    assert sng.reproduces(clause, _recolor_frag({"1": 9})) is True


def test_nonzero_action_prune_fires(tmp_path):
    """F4 regression: prune must fire for a transition witnessed under a non-zero
    real action (a != 0). Before the fix, record_visible stored a=tr.a (e.g. 2)
    but reproduces() replayed frag(s, 2, t); the frag was lowered under action
    key "0" so frag(s, 2, t) returned identity → never matched the recorded
    wrong output → prune was inert for all non-zero actions.

    After the fix, record_visible normalizes to a=0. reproduces() replays
    frag(s, 0, t) which DOES emit the wrong grid → prune fires correctly."""
    led = sng.SpecNogoodLedger(tmp_path)
    rules = [{"op": "recolor_map", "mapping": {"5": 8}}]
    # The real transition happened under action a=2 (non-zero real action)
    tr = _Tr([[5, 5]], 2, [[5, 5]], t=7)
    wrong_pred = _recolor_frag({"5": 8})(tr.s, 0, 7)   # [[8,8]] — wrong (frag contract: action 0)
    led.record_visible(rules, tr, wrong_pred)

    clause = led.blocks(sng.behavior_signature(rules))
    assert clause is not None
    # Action is normalized to 0 in provenance — the pre-fix bug stored a=2 here
    assert clause.provenance["a"] == 0, (
        f"expected action-normalized a=0 in provenance, got {clause.provenance['a']}"
    )
    # reproduces() must fire: same candidate replayed under action 0 emits [[8,8]]
    assert sng.reproduces(clause, _recolor_frag({"5": 8})) is True, (
        "prune did not fire for a non-zero real action (F4 regression)"
    )
    # winner invariant still holds: a clean candidate is not pruned
    assert sng.reproduces(clause, lambda s, a, t: s) is False


def test_holdout_clause_refused_by_consult(tmp_path):
    """FIREWALL: a holdout-provenance clause must never reach hypothesis
    formation — visible_clauses filters it out AND reproduces()/assert_visible
    raises if ever handed one."""
    led = sng.SpecNogoodLedger(tmp_path)
    # write a holdout clause directly (simulating a mis-tagged row)
    led.path.parent.mkdir(parents=True, exist_ok=True)
    import json
    led.path.write_text(json.dumps({
        "signature": "hh",
        "witness_summary": "holdout witness",
        "provenance": {"evidence": "holdout", "s": [[1]], "a": 0, "t": 0,
                       "predicted_next": [[9]]},
    }) + "\n")

    # filtered out of the consult path entirely
    assert "hh" not in led.visible_clauses()
    assert led.blocks("hh") is None

    holdout_clause = ConflictClause(signature="hh",
                                    provenance={"evidence": "holdout"})
    with pytest.raises(ValueError):
        sng.assert_visible(holdout_clause)
    with pytest.raises(ValueError):
        sng.reproduces(holdout_clause, _recolor_frag({"1": 9}))


def test_winner_is_never_pruned(tmp_path):
    """A clause records the WRONG successor a rejected candidate produced. A
    DIFFERENT candidate that would gate clean (predicts the truth on the witness)
    cannot reproduce that wrong grid, so it is never pruned."""
    led = sng.SpecNogoodLedger(tmp_path)
    rules = [{"op": "recolor_map", "mapping": {"1": 9}}]
    tr = _Tr([[1, 1]], 0, [[1, 1]], t=0)
    wrong = _recolor_frag({"1": 9})(tr.s, 0, 0)     # [[9,9]] — wrong
    led.record_visible(rules, tr, wrong)
    clause = led.blocks(sng.behavior_signature(rules))

    # the identity frag reproduces the TRUTH [[1,1]], not the wrong [[9,9]]
    assert sng.reproduces(clause, lambda s, a, t: s) is False


def test_flag_off_is_inert(tmp_path, monkeypatch):
    monkeypatch.setenv("ZTARE_SPEC_NOGOOD", "0")  # default is now "1"; test explicit-off
    assert sng.enabled() is False
    # with the flag off, abduce_spec must not touch the ledger at all
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.spec_abduction import abduce_spec

    log = EpisodeLog()
    for t in range(4):
        log.append(((1, 0),), 0, ((0, 1),), t=t)     # a simple recolor-ish log
    abduce_spec(log, 1, nogood_project=str(tmp_path))
    assert not (tmp_path / "workspace" / "spec_visible_nogoods.jsonl").exists()


def test_end_to_end_feed_then_prune(tmp_path, monkeypatch):
    """Cross-run: run 1 records visible nogoods (flag on), run 2 consults them and
    the nogood_pruned counter fires. Uses a log with a decoy candidate the search
    tries and rejects on a visible replay counterexample."""
    monkeypatch.setenv("ZTARE_SPEC_NOGOOD", "1")
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.spec_abduction import abduce_spec

    # Arity 2 so the recolor candidates stay in the PER-ACTION option lists (not
    # folded into 'always'). Under action 0, two frames disagree on what 1
    # recolors to (2 vs 3), so a candidate recolor {1:2} is proposed from the
    # first frame yet FAILS replay on the second — a visible counterexample the
    # per-action search rejects. Action 1 is a distinct clean recolor 5->6.
    log = EpisodeLog()
    frames = [
        (0, [[1, 1]], [[2, 2]]),
        (0, [[1, 1]], [[3, 3]]),
        (1, [[5, 5]], [[6, 6]]),
    ]
    for t, (a, s, sn) in enumerate(frames):
        log.append(tuple(tuple(r) for r in s), a, tuple(tuple(r) for r in sn), t=t)

    r1 = abduce_spec(log, 2, nogood_project=str(tmp_path))
    ng = tmp_path / "workspace" / "spec_visible_nogoods.jsonl"
    assert ng.exists(), "run 1 should record at least one visible nogood"
    rows = [l for l in ng.read_text().splitlines() if l.strip()]
    assert rows, "expected recorded visible nogood rows"
    import json
    assert all(json.loads(l)["provenance"]["evidence"] == "visible" for l in rows)

    r2 = abduce_spec(log, 2, nogood_project=str(tmp_path))
    assert r2.galois_stats.get("nogood_pruned", 0) >= 1, r2.galois_stats
    # winner invariance: same identified spec both runs
    assert r1.replay_ok == r2.replay_ok
    assert r1.spec == r2.spec


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-q"]))
