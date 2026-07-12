"""Planted regression tests for six silent-verdict defects (raise-or-receipt:
an error or absence must never be coerced into a pass)."""


def test_pursue_treats_none_prediction_as_divergence():
    """A fail-closed None prediction during live pursuit is a divergence event,
    not silent agreement — pursuit must not play blind under an erroring champion."""
    from ztare.worldmodel.grid_dsl import grid_from_lists
    from ztare.worldmodel.planner import pursue_goal

    class Adapter:
        action_arity = 2
        levels_completed = 0
        def __init__(self):
            self._s = grid_from_lists([[1, 0, 0, 0]])
            self._t = 0
        @property
        def t(self): return self._t
        @property
        def state(self): return self._s
        def step(self, a):
            self._t += 1
            return self._s

    # champion answers each (state, action, t) exactly once (enough for the
    # planner's search), then errors fail-closed to None — so the FIRST
    # execution-time predict, a repeat of a planning call, returns None.
    seen: set = set()
    def champ(s, a, t):
        key = (s, a, t)
        if key in seen:
            return None
        seen.add(key)
        return (s[0][1:] + s[0][:1],)   # rotate: a valid, novel prediction

    r = pursue_goal(Adapter(), champ, max_steps=5)
    assert r.status == "model_diverged", r
    assert r.divergence is not None
    assert r.divergence["terminal_witness"]["kind"] == "prediction_none"


def test_house_verdict_rejects_phantom_baseline():
    """If the ab_result carries a spec that cannot be loaded, the house arbiter
    must refuse to adjudicate — a phantom baseline makes every row base-wrong,
    auto-accepting any candidate."""
    from types import SimpleNamespace
    from ztare.worldmodel import grammar_reflex as gr
    from ztare.worldmodel.episode_log import EpisodeLog

    log = EpisodeLog()
    log.append(((0,),), 0, ((1,),), t=0)
    log.append(((1,),), 0, ((2,),), t=1)
    ab = SimpleNamespace(
        spec={"actions": {"0": [{"op": "no_such_operator"}]}, "always": []},
        step_fn=None, replay_ok=False)
    candidate = {"actions": {"0": [{"op": "recolor_map", "mapping": {"0": 1, "1": 2}}]},
                 "always": []}
    verdict = gr._spec_patch_house_verdict(log, ab, candidate)
    assert verdict["accepted"] is False, verdict
    assert verdict["reason"].startswith("baseline_unloadable:"), verdict


def test_lowered_step_raising_rule_predicts_none(monkeypatch):
    """A rule that raises at apply time must predict NOTHING (None), not
    "no change" — returning the input grid earned replay credit on no-op rows."""
    from ztare.worldmodel import spec_catalog as SC

    def _boom(*_a, **_k):
        raise RuntimeError("planted rule failure")

    grid = ((1, 0), (0, 0))
    # action-rule path
    step, err = SC.lower_spec(
        {"actions": {"0": [{"op": "recolor_map", "mapping": {"1": 2}}]}, "always": []})
    assert step is not None, err
    monkeypatch.setitem(SC._APPLY, "recolor_map", _boom)
    assert step(grid, 0) is None
    # always-rule path
    step2, err2 = SC.lower_spec(
        {"actions": {"0": [{"op": "identity"}]},
         "always": [{"op": "recolor_map", "mapping": {"1": 2}}]})
    assert step2 is not None, err2
    assert step2(grid, 0) is None


def test_execution_receipt_records_kill_condition_check():
    """A "survived" disposition is appealable: the receipt records the
    kill-condition text and whether the substring check matched."""
    from ztare.worldmodel.experiment_executor import _execution_receipt

    card = {"failure_family_sha": "abc", "kind": "probe",
            "kill_condition": "boundary crossed"}
    hit = _execution_receipt(card, {"summary": "the boundary crossed at t=3"}, "killed")
    miss = _execution_receipt(card, {"summary": "nothing observed"}, "survived")
    assert hit["kill_condition"] == "boundary crossed"
    assert hit["kill_condition_matched"] is True
    assert miss["kill_condition_matched"] is False
    # empty kill condition never counts as matched
    blank = _execution_receipt({"kill_condition": ""}, {"summary": ""}, "survived")
    assert blank["kill_condition_matched"] is False
