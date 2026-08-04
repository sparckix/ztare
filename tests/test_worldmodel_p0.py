"""Fast invariants for the GP-250 P0' world-model kernel (no harness sweep)."""

import hashlib
import json
from pathlib import Path

from ztare.substrates.arc_synthetic import ENVIRONMENTS, scripted_random_actions
from ztare.worldmodel.episode_log import EpisodeLog
from ztare.worldmodel.gates import as_predictor, replay_consistency_gate, rollout_depth
from ztare.worldmodel.grid_dsl import evaluate, grid_from_lists, program_size
from ztare.worldmodel.policy import select_action
from ztare.worldmodel.synthesis import synthesize


def _log_for(env_id: str, steps: int = 60, seed: int = 7) -> tuple:
    env = next(e for e in ENVIRONMENTS if e.env_id == env_id)
    log = EpisodeLog()
    for s, a, s_next in env.rollout(scripted_random_actions(env, steps, seed)):
        log.append(s, a, s_next)
    return env, log


def test_evaluator_shift_and_fail_closed():
    g = grid_from_lists([[1, 0], [0, 2]])
    assert evaluate(("shift", ("s",), 0, 1), g, 0, 0) == grid_from_lists([[0, 1], [0, 0]])
    # undefined: mod by zero fails closed through the conditional
    assert evaluate(("if", ("eq", ("mod", ("step",), ("lit", 0)), ("lit", 0)), ("s",), ("s",)), g, 0, 0) is None


def test_callable_predictor_canonicalizes_grid_lists():
    g = grid_from_lists([[1, 0], [0, 2]])
    predict = as_predictor(lambda _s, _a, _t: [[1, 0], [0, 2]])

    assert predict(g, 0, 0) == g
    assert as_predictor(lambda _s, _a, _t: {"not": "a grid"})(g, 0, 0) is None


def test_synthesis_recovers_action_gated_shift():
    env, log = _log_for("e01_shift_on_a0")
    result = synthesize(log, env.action_arity)
    assert result.status == "committee"
    assert replay_consistency_gate(result.champion, log).ok
    # champion matches the sealed law on a fresh rollout
    holdout = EpisodeLog()
    for s, a, s_next in env.rollout(scripted_random_actions(env, 40, seed=99)):
        holdout.append(s, a, s_next)
    assert rollout_depth(result.champion, holdout) == len(holdout)


def test_grammar_ceiling_is_typed_not_silent():
    env, log = _log_for("e03_gravity", steps=80)
    assert synthesize(log, env.action_arity).status == "grammar_ceiling"


def test_policy_probes_untried_action_and_identifies():
    env, log = _log_for("e01_shift_on_a0", steps=6, seed=3)
    result = synthesize(log, env.action_arity)
    assert len(result.committee) >= 1
    decision = select_action(result.committee, env.initial, step=0,
                             action_arity=env.action_arity, remaining_budget=50)
    assert decision.status in ("probe", "identified")
    single = select_action(result.committee[:1], env.initial, 0, env.action_arity, 50)
    assert single.status == "identified"


def test_program_size_is_positive_and_ordered():
    assert program_size(("s",)) == 1
    assert program_size(("shift", ("s",), 0, 1)) > program_size(("s",))


def test_p1_dispatcher_gates_registered_for_interactive_class():
    from ztare.gates.registry import _build_gates

    names = {g.name for g in _build_gates()}
    assert {"worldmodel_replay", "worldmodel_rollout"} <= names
    replay = next(g for g in _build_gates() if g.name == "worldmodel_replay")

    class _Sub:
        meta = {"class": "interactive_environment"}

    ok, _reason = replay.can_handle(_Sub(), None)
    assert ok

    class _Numeric:
        meta = {"class": "oeis_sequence"}

    ok, _reason = replay.can_handle(_Numeric(), None)
    assert not ok


def test_p1_acquire_evidence_and_gates_end_to_end(tmp_path):
    from ztare.gates.worldmodel_gates import run_replay_gate, run_rollout_gate
    from ztare.substrates.arc_synthetic import ENVIRONMENTS, scripted_random_actions
    from ztare.worldmodel.adapter import (
        SyntheticEnvAdapter, acquire_evidence, episode_log_path,
    )

    env = next(e for e in ENVIRONMENTS if e.env_id == "e01_shift_on_a0")
    receipt = acquire_evidence(tmp_path, SyntheticEnvAdapter(env), max_probes=12)
    assert receipt.status == "identified"
    assert receipt.committee_size == 1

    # held-out episode for the rollout gate
    holdout_path = tmp_path / "raw" / "episodes" / "holdout.jsonl"
    log = EpisodeLog()
    for s, a, s_next in env.rollout(scripted_random_actions(env, 30, seed=77)):
        log.append(s, a, s_next)
    log.write_jsonl(holdout_path)

    import json as _json
    champion = _json.loads((tmp_path / "workspace" / "worldmodel_committee.json").read_text())["champion"]

    class _Sub:
        meta = {"class": "interactive_environment",
                "project_dir": tmp_path,
                "episode_log_path": episode_log_path(tmp_path),
                "holdout_log_path": holdout_path,
                "min_rollout_depth": 30}

    candidate = {"transition_program": champion}
    assert run_replay_gate(_Sub(), candidate)["ok"]
    assert run_rollout_gate(_Sub(), candidate)["ok"]
    # fail-closed: a wrong program dies at replay
    assert not run_replay_gate(_Sub(), {"transition_program": ("shift", ("s",), 1, 1)})["ok"]


def test_replay_diagnostics_quotients_repeated_mismatch_classes():
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.gates import replay_diagnostics
    from ztare.worldmodel.grid_dsl import grid_from_lists

    s0 = grid_from_lists([[0, 0], [0, 0]])
    real = grid_from_lists([[3, 3], [0, 0]])
    log = EpisodeLog()
    log.append(s0, 1, real, t=0)
    log.append(s0, 1, real, t=1)

    def bad_step(_grid, _action, _t):
        return grid_from_lists([[8, 8], [0, 0]])

    diag = replay_diagnostics(bad_step, log).as_dict()

    assert diag["wrong_rows"] == 2
    assert diag["mismatch_classes"][0]["count"] == 2
    assert diag["mismatch_classes"][0]["signature"]["pair_counts"] == [
        {"predicted": 8, "real": 3, "count": 2}
    ]


def test_combined_replay_gate_matches_separate_verdict_with_one_carrier_scan():
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.gates import (
        replay_consistency_gate,
        replay_gate_and_diagnostics,
    )

    log = EpisodeLog()
    state = ((0, 0), (0, 0))
    successor = ((0, 1), (0, 0))
    for t in range(4):
        log.append(state, 0, successor, t=t)
    calls = {"n": 0}

    def candidate(grid, action, t):
        calls["n"] += 1
        return successor if t < 3 else grid

    separate = replay_consistency_gate(candidate, log)
    calls["n"] = 0
    combined, diagnostics = replay_gate_and_diagnostics(candidate, log)

    assert combined.ok == separate.ok is False
    assert combined.detail == separate.detail
    assert diagnostics.checked_rows == 4
    assert diagnostics.exact_rows == 3
    assert calls["n"] == diagnostics.checked_rows


def test_rollout_diagnostics_emits_holdout_witness_from_first_mismatch():
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.gates import rollout_diagnostics

    holdout = EpisodeLog()
    holdout.append(((1,),), 1, ((2,),), t=7)
    holdout.append(((2,),), 2, ((2,),), t=8)

    def bad_step(_state, _action, _t):
        return ((9,),)

    diag = rollout_diagnostics(bad_step, holdout)

    assert diag["rollout_depth"] == 0
    witness = diag["holdout_witness"]
    assert witness["step_index"] == 0
    assert witness["t"] == 7
    assert witness["action"] == 1
    assert witness["entry_context_note"] == "first rollout divergence at holdout row 0 (t=7)"
    assert witness["divergent_cells"] == [
        {"row": 0, "col": 0, "predicted": 9, "actual": 2},
    ]


def test_replay_diagnostics_preserves_candidate_execution_failure_identity():
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.gates import replay_diagnostics

    log = EpisodeLog()
    log.append(((1,),), 0, ((1,),), t=3)

    def broken_candidate(_state, _action, _t):
        raise NameError("missing_operator")

    diagnostics = replay_diagnostics(broken_candidate, log).as_dict()

    assert diagnostics["first_mismatch_signature"] == {
        "kind": "candidate_exception",
        "exception_type": "NameError",
        "message": "missing_operator",
    }
    assert diagnostics["residual_table"][0]["prediction_failure"] == diagnostics[
        "first_mismatch_signature"
    ]
    assert "candidate execution error NameError: missing_operator" in diagnostics[
        "first_mismatch"
    ]


def test_replay_diagnostics_distinguishes_undefined_partial_map_from_exception():
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.gates import replay_diagnostics

    log = EpisodeLog()
    log.append(((1,),), 0, ((1,),), t=4)

    diagnostics = replay_diagnostics(lambda _state, _action, _t: None, log).as_dict()

    assert diagnostics["first_mismatch_signature"] == {
        "kind": "undefined_prediction"
    }
    assert diagnostics["first_mismatch"] == (
        "candidate map undefined on this transition at t=4"
    )


def test_planner_reaches_goal_under_known_model():
    """Exploit half: BFS through a ratified law finds an action sequence that
    the model says reaches the goal; a fail-closed model prunes cleanly."""
    from ztare.worldmodel.planner import plan_to_goal
    from ztare.worldmodel.grid_dsl import grid_from_lists
    # law: action 0 shifts a marker right; goal: marker in the last column
    champ = ("if", ("eq", ("action",), ("lit", 0)), ("shift", ("s",), 0, 1), ("s",))
    start = grid_from_lists([[1, 0, 0, 0]])
    goal = lambda g: g[0][3] == 1  # noqa: E731
    plan = plan_to_goal(champ, start, action_arity=2, goal_fn=goal, max_depth=6)
    assert plan is not None and plan.actions == [0, 0, 0], plan
    # unreachable goal within depth → empty plan, not a crash
    bad = plan_to_goal(champ, start, action_arity=2, goal_fn=lambda g: g[0][0] == 9,
                       max_depth=4)
    assert bad is not None and not bad.actions


def test_planner_grid_quotient_does_not_silently_quotient_time():
    """A grid alpha map has no authority to merge distinct lawful times."""
    from ztare.worldmodel.planner import plan_to_goal
    from ztare.worldmodel.grid_dsl import grid_from_lists

    champ = ("if", ("eq", ("action",), ("lit", 0)), ("shift", ("s",), 0, 1), ("s",))
    start = grid_from_lists([[1, 0, 0, 0, 0, 0, 0, 0]])
    goal = lambda g: g[0][7] == 1  # noqa: E731
    coarse_alpha = lambda _g: "all-states-equivalent"  # noqa: E731

    plan = plan_to_goal(
        champ,
        start,
        action_arity=2,
        goal_fn=goal,
        max_depth=8,
        abstract_fn=coarse_alpha,
    )

    assert plan is not None
    assert plan.actions == [0] * 7


def test_undefined_terminal_acquisition_uses_projected_coverage_before_raw_novelty(tmp_path):
    """A passive clock change is transition state, but not a new acquisition target."""
    from ztare.worldmodel.planner import pursue_goal

    def law(state, action, _time):
        position, remaining = state[0]
        return ((position + int(action == 1), remaining - 1),)

    class Adapter:
        action_arity = 2
        levels_completed = 0
        last_transition_identity = None

        def __init__(self):
            self._state = ((0, 3),)
            self._time = 0

        @property
        def state(self):
            return self._state

        @property
        def t(self):
            return self._time

        def step(self, action):
            self._state = law(self._state, action, self._time)
            self._time += 1
            return self._state

    abstract = lambda grid: tuple(grid[0])  # noqa: E731
    controllable = lambda signature: signature[0]  # noqa: E731
    receipt = pursue_goal(
        Adapter(),
        law,
        max_steps=1,
        plan_depth=2,
        abstract_fn=abstract,
        coverage_fn=controllable,
        visited_store={abstract(((0, 3),))},
        receipts_dir=tmp_path,
    )

    # Action 0 changes only the predictable clock.  Action 1 reaches the first
    # unseen controllable quotient class and therefore has higher acquisition
    # value despite both successors being distinct transition states.
    assert receipt.trace == [1]
    route = json.loads((tmp_path / "acquisition_routing.jsonl").read_text().splitlines()[-1])
    assert route["policy"] == "projected_reachability_coverage"
    assert route["plan_found"] is True


def test_acquisition_search_does_not_simulate_through_adjudicated_boundary(tmp_path):
    """A non-discharge edge constrains control without editing the carrier."""
    from ztare.worldmodel.planner import pursue_goal

    def law(state, action, _time):
        position, remaining = state[0]
        return ((position + int(action == 1), remaining - 1),)

    class Adapter:
        action_arity = 2
        levels_completed = 0
        last_transition_identity = None

        def __init__(self):
            self._state = ((0, 3),)
            self._time = 0

        @property
        def state(self):
            return self._state

        @property
        def t(self):
            return self._time

        def step(self, action):
            if action == 1:
                raise AssertionError(f"excluded acquisition edge executed: {action}")
            self._state = law(self._state, action, self._time)
            self._time += 1
            return self._state

    start = ((0, 3),)
    abstract = lambda grid: tuple(grid[0])  # noqa: E731
    receipt = pursue_goal(
        Adapter(),
        law,
        max_steps=1,
        plan_depth=2,
        abstract_fn=abstract,
        coverage_fn=lambda signature: signature[0],
        visited_store={abstract(start)},
        excluded_edge_fn=lambda source, action, _time: (
            source == start and action == 1
        ),
        receipts_dir=tmp_path,
    )

    assert receipt.status == "plan_exhausted"
    assert receipt.trace == [0]


def test_pursue_returns_candidate_goal_to_external_adjudicator():
    from ztare.worldmodel.planner import pursue_goal

    def law(state, _action, _time):
        return ((state[0][0] + 1,),)

    class Adapter:
        action_arity = 1
        levels_completed = 0
        last_transition_identity = None

        def __init__(self):
            self._state = ((0,),)
            self._time = 0

        @property
        def state(self):
            return self._state

        @property
        def t(self):
            return self._time

        def step(self, action):
            self._state = law(self._state, action, self._time)
            self._time += 1
            return self._state

    receipt = pursue_goal(
        Adapter(),
        law,
        goal_fn=lambda state: state == ((1,),),
        max_steps=3,
        plan_depth=2,
    )

    assert receipt.status == "candidate_goal_reached"
    assert receipt.trace == [0]
    assert receipt.levels_gained == 0


def test_pursue_reports_model_divergence():
    """A ratified model that mispredicts a live transition ends pursuit with
    model_diverged, not a silent wrong plan."""
    from ztare.worldmodel.planner import pursue_goal
    from ztare.worldmodel.grid_dsl import grid_from_lists

    class DivergingAdapter:
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
            self._s = grid_from_lists([[0, 0, 0, 0]])  # reality: marker vanishes (model says shift)
            return self._s

    champ = ("if", ("eq", ("action",), ("lit", 0)), ("shift", ("s",), 0, 1), ("s",))
    r = pursue_goal(DivergingAdapter(), champ, max_steps=5)
    assert r.status == "model_diverged", r
    assert r.divergence is not None


def test_pursue_records_terminal_verifier_model_mismatch():
    """A terminal verifier transition can also be a counterexample to the
    current law. The level remains scored, but the receipt must preserve the
    mismatch so the next identification pass can refine the law."""
    from ztare.worldmodel.planner import pursue_goal
    from ztare.worldmodel.grid_dsl import grid_from_lists

    class RewardMismatchAdapter:
        action_arity = 1
        levels_completed = 0
        def __init__(self):
            self._s = grid_from_lists([[1, 0, 0, 0]])
            self._t = 0
        @property
        def t(self): return self._t
        @property
        def state(self): return self._s
        def step(self, _a):
            self._t += 1
            self._s = grid_from_lists([[0, 0, 0, 0]])  # model predicts shift, terminal edge differs
            self.levels_completed = 1
            return self._s

    champ = ("shift", ("s",), 0, 1)
    r = pursue_goal(RewardMismatchAdapter(), champ, max_steps=5)

    assert r.status == "goal_reached", r
    assert r.levels_gained == 1
    assert r.divergence is not None
    assert r.divergence["action"] == 0
    assert r.divergence["kernel_role_bindings"][0]["term"] == "terminal_verifier_event"
    assert r.divergence["terminal_witness"]["sha256"]
    terms = {b["term"] for b in r.divergence["terminal_witness"]["kernel_role_bindings"]}
    assert {"terminal_witness", "translation_quotient"} <= terms
    assert "refuted the transition law" in r.detail


def test_terminal_witness_quotients_translation_but_not_phase_or_context():
    from ztare.worldmodel.grid_dsl import grid_from_lists
    from ztare.worldmodel.terminal_witness import terminal_witness_fingerprint

    state_a = grid_from_lists([
        [0, 0, 0, 0],
        [0, 7, 1, 0],
        [0, 0, 0, 0],
    ])
    pred_a = grid_from_lists([
        [0, 0, 0, 0],
        [0, 7, 0, 1],
        [0, 0, 0, 0],
    ])
    obs_a = grid_from_lists([
        [0, 0, 0, 0],
        [0, 7, 1, 0],
        [0, 0, 0, 0],
    ])
    state_b = grid_from_lists([
        [0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0],
        [0, 0, 7, 1, 0],
        [0, 0, 0, 0, 0],
    ])
    pred_b = grid_from_lists([
        [0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0],
        [0, 0, 7, 0, 1],
        [0, 0, 0, 0, 0],
    ])
    obs_b = grid_from_lists([
        [0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0],
        [0, 0, 7, 1, 0],
        [0, 0, 0, 0, 0],
    ])

    fp_a = terminal_witness_fingerprint(
        action=2, step=8, state=state_a, predicted=pred_a, observed=obs_a)
    fp_b = terminal_witness_fingerprint(
        action=2, step=8, state=state_b, predicted=pred_b, observed=obs_b)
    fp_phase = terminal_witness_fingerprint(
        action=2, step=9, state=state_b, predicted=pred_b, observed=obs_b)
    fp_later = terminal_witness_fingerprint(
        action=2, step=14, state=state_b, predicted=pred_b, observed=obs_b)
    fp_certified_a = terminal_witness_fingerprint(
        action=2, step=8, state=state_b, predicted=pred_b, observed=obs_b,
        certified_period=6)
    fp_certified_b = terminal_witness_fingerprint(
        action=2, step=14, state=state_b, predicted=pred_b, observed=obs_b,
        certified_period=6)

    assert fp_a["sha256"] == fp_b["sha256"]
    assert fp_phase["sha256"] != fp_a["sha256"]
    assert fp_later["sha256"] != fp_a["sha256"]
    assert fp_a["step"] == 8 and "phase" not in fp_a
    assert fp_certified_a["sha256"] == fp_certified_b["sha256"]
    assert fp_certified_a["certified_period"] == 6
    roles = {
        binding["term"]: set(binding["roles"])
        for binding in fp_a["kernel_role_bindings"]
    }
    assert roles["terminal_witness"] == {
        "counterexample_routing", "model_update", "representation"}
    assert roles["translation_quotient"] == {
        "compression", "counterexample_routing", "representation"}


def test_act_and_learn_absorbs_offbasin_transitions():
    """The identify->act->learn loop appends the live transitions the model
    was never fit on, growing the log each round until convergence."""
    from ztare.worldmodel.planner import act_and_learn
    from ztare.worldmodel.grid_dsl import grid_from_lists

    # a world the round-1 model gets wrong off its witnessed cell: real law
    # shifts right and WRAPS; a naive model shifts-and-drops. Pursuit exposes
    # the wrap transitions, which re-id absorbs.
    class WrapAdapter:
        action_arity = 1
        levels_completed = 0
        def __init__(self):
            self._g = grid_from_lists([[1, 0, 0]])
            self._t = 0
        @property
        def t(self): return self._t
        @property
        def state(self): return self._g
        def reset(self):
            self._g, self._t = grid_from_lists([[1, 0, 0]]), 0
            return self._g
        def step(self, a):
            row = list(self._g[0]); row = [row[-1]] + row[:-1]  # cyclic right shift
            self._g = (tuple(row),); self._t += 1
            return self._g

    from ztare.worldmodel.gates import replay_consistency_gate

    class Res:
        def __init__(self, champ): self.status = "committee"; self.champion = champ
    def resynth(log):
        # champion = "shift right, drop" (correct only until the marker wraps)
        def champ(g, a, t):
            row = list(g[0]); return (tuple([0] + row[:-1]),)
        return Res(champ)

    from ztare.worldmodel.episode_log import EpisodeLog
    adapter = WrapAdapter(); adapter.reset()
    log = EpisodeLog()
    # seed the witnessing basin with the non-wrapping steps
    s = adapter.state
    log.append(s, 0, (tuple([0, 1, 0]),), t=0)
    r = act_and_learn(adapter, log, 1, resynthesize=resynth, max_rounds=3, pursue_steps=8)
    assert r.rounds >= 1 and r.log_growth, r
    assert len(log) > 1  # off-basin (wrap) transitions were absorbed


def test_novelty_planner_seeks_unexplored_states():
    """Novelty steering plans toward states farthest from the visited set —
    general, no goal predicate. A wrong steer can't fake success (that's the
    adapter adjudicator's job); this only checks it drives exploration."""
    from ztare.worldmodel.planner import plan_novelty
    from ztare.worldmodel.grid_dsl import grid_from_lists
    # marker moves right under action 0; novelty should push it away from start
    champ = ("if", ("eq", ("action",), ("lit", 0)), ("shift", ("s",), 0, 1), ("s",))
    start = grid_from_lists([[1, 0, 0, 0]])
    plan = plan_novelty(champ, start, action_arity=2, visited={start}, max_depth=4)
    assert plan is not None and plan.actions and plan.actions[0] == 0, plan
    # identity-only world: the sole reachable state IS start; once visited,
    # no novel state remains, so novelty search returns an empty plan
    ident = ("s",)
    plan2 = plan_novelty(ident, start, action_arity=1, visited={start}, max_depth=4)
    assert plan2 is not None and not plan2.actions, plan2


def test_novelty_planner_respects_quotient_identity():
    from ztare.worldmodel.planner import plan_novelty
    from ztare.worldmodel.grid_dsl import grid_from_lists

    champ = ("if", ("eq", ("action",), ("lit", 0)), ("shift", ("s",), 0, 1), ("s",))
    start = grid_from_lists([[1, 0, 0, 0]])
    coarse_alpha = lambda _g: "all-states-equivalent"  # noqa: E731

    plan = plan_novelty(
        champ,
        start,
        action_arity=2,
        visited={start},
        max_depth=4,
        abstract_fn=coarse_alpha,
    )

    assert plan is not None and not plan.actions


def test_spec_catalog_lowers_ls20_shaped_law():
    """Class-selection + deterministic lowering: a spec expressing a
    block-move-with-refusal law plus an extremal-consume counter lowers to a
    step() that reproduces both mechanics exactly — and a malformed spec
    fail-closes instead of lowering wrong."""
    from ztare.worldmodel.spec_catalog import lower_spec
    spec = {
        "actions": {
            "0": [{"op": "translate_block", "match_colors": [9], "dy": 0, "dx": 1,
                   "require_dest_colors": [3], "fill_color": 3}],
            "1": [{"op": "identity"}],
        },
        "always": [{"op": "consume_extremal", "color": 11, "replacement": 3,
                    "axis": "row", "extreme": "min"}],
    }
    step, err = lower_spec(spec)
    assert step is not None, err
    g = ((3, 9, 3, 3),
         (11, 11, 11, 3))
    out = step(g, 0, 0)
    assert out[0] == (3, 3, 9, 3)          # block moved right into floor
    assert out[1] == (3, 11, 11, 3)        # leftmost 11 consumed
    # blocked move: destination is a wall (color 4) -> refusal, timer still runs
    g2 = ((3, 9, 4, 3),
          (11, 3, 3, 3))
    out2 = step(g2, 0, 1)
    assert out2[0] == (3, 9, 4, 3)         # refused
    assert out2[1] == (3, 3, 3, 3)         # timer consumed anyway
    # malformed spec fail-closes
    bad, err2 = lower_spec({"actions": {"0": [{"op": "warp_reality"}]}})
    assert bad is None and "unknown op" in err2


def test_spec_abduction_recovers_law_from_diffs():
    """Zero-model-call identification: rule abduction reads a guarded-move +
    counter law off transition diffs, assembles a spec, and the lowered step
    replays exactly — with a multi-color component moving while a same-palette
    single-color decoration stays static (component_min_colors inference)."""
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.spec_abduction import abduce_spec
    from ztare.worldmodel.spec_catalog import lower_spec

    truth, _ = lower_spec({
        "actions": {"0": [{"op": "translate_block", "match_colors": [9, 12],
                           "dy": 0, "dx": 1, "require_dest_colors": [3],
                           "fill_color": 3, "component_min_colors": 2}],
                    "1": [{"op": "identity"}]},
        "always": [{"op": "consume_extremal", "color": 11, "replacement": 3,
                    "axis": "row", "extreme": "min"}]})
    # world: two-color mover, single-color 9 decoration, timer row
    g = ((9, 0, 0, 0, 0),
         (12, 9, 3, 3, 3),
         (11, 11, 11, 3, 3))
    log = EpisodeLog()
    s = g
    for a in (0, 1, 0, 0, 1, 0):
        s2 = truth(s, a, 0)
        log.append(s, a, s2, t=0)
        s = s2
    r = abduce_spec(log, 2)
    assert r.replay_ok, r.detail
    assert r.status == "spec_identified"


def test_spec_when_overlap_pauses_rule_on_positional_overlap():
    """when_overlap is a POSITIONAL pause: a rule fires while the mover colors
    stay OUTSIDE the rect and is suppressed the moment any land inside it (a
    key-window entry pausing the mechanic), read off the STEP-START grid."""
    from ztare.worldmodel.spec_catalog import lower_spec
    step, err = lower_spec({
        "actions": {"0": [{"op": "identity"}]},
        "always": [{"op": "consume_extremal", "color": 11, "replacement": 3,
                    "axis": "row", "extreme": "min",
                    "when_overlap": [[9], 0, 0, 0, 1]}]})
    assert step is not None, err
    # mover (9) at col 3 — outside the window — so the timer ticks (leftmost 11)
    g_out = ((3, 3, 3, 9), (11, 11, 11, 3))
    assert step(g_out, 0, 0) == ((3, 3, 3, 9), (3, 11, 11, 3))
    # mover inside the window (cols 0-1) — the tick is suppressed (paused)
    g_in = ((9, 3, 3, 3), (11, 11, 11, 3))
    assert step(g_in, 0, 0) == g_in
    # malformed when_overlap fail-closes rather than lowering wrong
    bad, err2 = lower_spec({"actions": {"0": [{"op": "identity",
                            "when_overlap": [1, 2, 3]}]}})
    assert bad is None and "when_overlap" in err2


def test_spec_abduction_recovers_planted_overlap_guard():
    """A depleting counter that PAUSES on a positional overlap (no count guard
    can express it) is recovered zero-model: abduction learns the mover's
    translate rules, the consume law, and a when_overlap rect from the
    paused-step sprite positions; the lowered step replays the 6-transition
    log exactly."""
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.spec_abduction import abduce_spec
    from ztare.worldmodel.spec_catalog import lower_spec
    truth, _ = lower_spec({
        "actions": {"0": [{"op": "translate_block", "match_colors": [9], "dy": 0,
                           "dx": 1, "require_dest_colors": [3], "fill_color": 3}],
                    "1": [{"op": "translate_block", "match_colors": [9], "dy": 0,
                           "dx": -1, "require_dest_colors": [3], "fill_color": 3}]},
        "always": [{"op": "consume_extremal", "color": 11, "replacement": 3,
                    "axis": "row", "extreme": "min",
                    "when_overlap": [[9], 0, 0, 0, 1]}]})
    g = ((3, 3, 3, 9, 3, 3),
         (11, 11, 11, 11, 3, 3))
    log = EpisodeLog()
    s = g
    for a in (1, 1, 1, 0, 0, 0):     # slide the mover into the window and back out
        s2 = truth(s, a, 0)
        log.append(s, a, s2, t=0)
        s = s2
    r = abduce_spec(log, 2)
    assert r.replay_ok and r.status == "spec_identified", r.detail
    assert any("when_overlap" in rule for rule in r.spec["always"]), r.spec["always"]


def test_spec_region_event_writes_on_mover_crossing():
    """region_event is a CROSSING write: iff the mover leaves (exit) or enters
    (enter) a fixed rect between the step-start and post-action grids, a
    learned remote cell-set is painted — the general form of a pressure plate,
    a door toggle, a checkpoint HUD flag, or terrain restored behind a sprite.
    A frame where the mover does NOT cross writes nothing; malformed fail-closes."""
    from ztare.worldmodel.spec_catalog import lower_spec
    exit_spec = {
        "actions": {"0": [{"op": "translate_block", "match_colors": [7], "dy": 0,
                           "dx": 1, "require_dest_colors": [3], "fill_color": 3}]},
        "always": [{"op": "region_event", "mover_colors": [7], "rect": [0, 0, 0, 1],
                    "edge": "exit", "writes": [[6, [[2, 3]]]]}]}
    step, err = lower_spec(exit_spec)
    assert step is not None, err
    # mover inside the rect (col 1); moving right EXITS it -> the flag lights
    g = ((3, 7, 3, 3), (3, 3, 3, 3), (3, 3, 3, 3))
    out = step(g, 0, 0)
    assert out[0] == (3, 3, 7, 3) and out[2][3] == 6      # moved + flag written
    # mover already outside (col 2); moving right is no crossing -> no write
    g2 = ((3, 3, 7, 3), (3, 3, 3, 3), (3, 3, 3, 3))
    assert step(g2, 0, 0)[2][3] == 3
    # 'enter' is the mirror: moving INTO the rect fires
    enter_step, _ = lower_spec({
        "actions": {"0": [{"op": "translate_block", "match_colors": [7], "dy": 0,
                           "dx": -1, "require_dest_colors": [3], "fill_color": 3}]},
        "always": [{"op": "region_event", "mover_colors": [7], "rect": [0, 0, 0, 1],
                    "edge": "enter", "writes": [[6, [[2, 3]]]]}]})
    assert enter_step(((3, 3, 7, 3), (3, 3, 3, 3), (3, 3, 3, 3)), 0, 0)[2][3] == 6
    # malformed rect fail-closes instead of lowering wrong
    bad, err2 = lower_spec({"actions": {"0": [{"op": "region_event", "mover_colors": [7],
                            "rect": [0, 0, 1], "edge": "exit", "writes": []}]}})
    assert bad is None and "rect" in err2


def test_region_event_pattern_trigger_is_translation_equivariant():
    from ztare.worldmodel.spec_catalog import lower_patch_delta_spec

    rule = {
        "op": "region_event",
        "mover_colors": [7],
        "trigger_pattern": {
            "shape": [2, 2],
            "values": [1, 2, 3, 4],
        },
        "edge": "enter",
        "writes": [[9, [[0, 0]]]],
    }
    delta, error = lower_patch_delta_spec({"actions": {}, "always": [rule]})
    assert error == ""

    def case(top: int, left: int):
        state = [[0 for _ in range(7)] for _ in range(7)]
        state[top][left : left + 2] = [1, 2]
        state[top + 1][left : left + 2] = [3, 4]
        state[6][6] = 7
        consequence = [row[:] for row in state]
        consequence[6][6] = 0
        consequence[top][left] = 7
        return tuple(tuple(row) for row in state), tuple(
            tuple(row) for row in consequence
        )

    first_state, first_next = case(1, 1)
    shifted_state, shifted_next = case(3, 2)
    first = delta(first_next, first_state, 0, 0)
    shifted = delta(shifted_next, shifted_state, 3, 91)

    assert first[0][0] == shifted[0][0] == 9
    assert first[1:] == first_next[1:]
    assert shifted[1:] == shifted_next[1:]

    no_arrival = [list(row) for row in shifted_next]
    no_arrival[3][2] = 0
    no_arrival = tuple(tuple(row) for row in no_arrival)
    assert delta(no_arrival, shifted_state, 2, 18) == no_arrival


def test_bind_region_value_transports_value_without_palette_literal():
    from ztare.worldmodel.spec_catalog import lower_patch_delta_spec

    delta, error = lower_patch_delta_spec({
        "actions": {},
        "always": [{
            "op": "bind_region_value",
            "target_rect": [1, 2, 2, 3],
            "source_offset": [0, -1],
            "expected_current": 12,
        }],
    })
    assert error == ""
    state = (
        (0, 0, 0, 0, 0),
        (0, 9, 5, 5, 0),
        (0, 9, 5, 5, 0),
    )
    base = (
        (0, 0, 0, 0, 0),
        (0, 9, 12, 12, 0),
        (0, 9, 12, 12, 0),
    )
    assert delta(base, state, 0, 0)[1][2:4] == (9, 9)
    sparse = (
        (0, 0, 0, 0, 0),
        (0, 9, 12, 5, 0),
        (0, 9, 5, 12, 0),
    )
    transported = delta(sparse, state, 0, 0)
    assert transported[1][2:4] == (9, 5)
    assert transported[2][2:4] == (5, 9)
    already_owned = tuple(
        tuple(8 if row in (1, 2) and col in (2, 3) else value
              for col, value in enumerate(values))
        for row, values in enumerate(base)
    )
    assert delta(already_owned, state, 0, 0) == already_owned


def test_spec_abduction_recovers_region_event():
    """Zero-model recovery of a region-crossing write on a PLANTED synthetic
    world (no substrate constants): a two-color sprite slides on floor and,
    whenever it exits a fixed rect, a remote flag lights — a residual the move
    rule cannot explain. Abduction learns the translate rules, then mines the
    region_event (its rect anchored to the moving sprite's footprint, its write
    the residual) and the lowered step replays the log exactly."""
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.spec_abduction import abduce_spec
    from ztare.worldmodel.spec_catalog import lower_spec
    truth, _ = lower_spec({
        "actions": {"0": [{"op": "translate_block", "match_colors": [7, 8], "dy": 0,
                           "dx": 1, "require_dest_colors": [3], "fill_color": 3,
                           "component_min_colors": 2}],
                    "1": [{"op": "translate_block", "match_colors": [7, 8], "dy": 0,
                           "dx": -1, "require_dest_colors": [3], "fill_color": 3,
                           "component_min_colors": 2}]},
        "always": [{"op": "region_event", "mover_colors": [7, 8], "rect": [1, 2, 2, 2],
                    "edge": "exit", "writes": [[6, [[4, 6], [4, 7]]]]}]})
    g = ((3, 3, 3, 3, 3, 3, 3, 3),
         (3, 3, 7, 3, 3, 3, 3, 3),
         (3, 3, 8, 3, 3, 3, 3, 3),
         (3, 3, 3, 3, 3, 3, 3, 3),
         (3, 3, 3, 3, 3, 3, 3, 3))
    log = EpisodeLog()
    s = g
    for a in (0, 0, 1, 1, 0, 0, 1):     # cross out of the rect, wander, cross again
        s2 = truth(s, a, 0)
        log.append(s, a, s2, t=0)
        s = s2
    r = abduce_spec(log, 2)
    assert r.replay_ok and r.status == "spec_identified", r.detail
    assert any(rule["op"] == "region_event" for rule in r.spec["always"]), r.spec["always"]


def test_spec_lowers_action_gated_rule():
    """Action gating: `when_action` fires a rule only under listed actions (a
    directional 'use' interaction); an action-scoped `when_overlap` applies its
    positional pause only under those actions — the disambiguator when two
    actions leave the mover in the same key-window cell but only one trips the
    mechanic. Both compose as AND vetoes; malformed when_action fail-closes."""
    from ztare.worldmodel.spec_catalog import lower_spec
    # region_event gated to action 1: crossing under action 0 writes nothing
    step, err = lower_spec({
        "actions": {"0": [{"op": "translate_block", "match_colors": [7], "dy": 0,
                           "dx": 1, "require_dest_colors": [3], "fill_color": 3}],
                    "1": [{"op": "translate_block", "match_colors": [7], "dy": 0,
                           "dx": 1, "require_dest_colors": [3], "fill_color": 3}]},
        "always": [{"op": "region_event", "mover_colors": [7], "rect": [0, 0, 0, 1],
                    "edge": "exit", "writes": [[6, [[2, 3]]]], "when_action": [1]}]})
    assert step is not None, err
    g = ((3, 7, 3, 3), (3, 3, 3, 3), (3, 3, 3, 3))
    assert step(g, 1, 0)[2][3] == 6          # crossing under action 1 -> flag lit
    assert step(g, 0, 0)[2][3] == 3          # SAME crossing under action 0 -> no write
    # action-scoped when_overlap: the pause only bites under action 1
    tstep, err2 = lower_spec({
        "actions": {"0": [{"op": "identity"}], "1": [{"op": "identity"}]},
        "always": [{"op": "consume_extremal", "color": 11, "replacement": 3,
                    "axis": "row", "extreme": "min",
                    "when_overlap": [[9], 0, 0, 0, 1, [1]]}]})
    assert tstep is not None, err2
    g_in = ((9, 3, 3, 3), (11, 11, 11, 3))
    assert tstep(g_in, 1, 0) == g_in                       # in window + a=1 -> paused
    assert tstep(g_in, 0, 0) == ((9, 3, 3, 3), (3, 11, 11, 3))  # same cell, a=0 -> ticks
    # malformed when_action fail-closes
    bad, err3 = lower_spec({"actions": {"0": [{"op": "identity", "when_action": 1}]}})
    assert bad is None and "when_action" in err3


def test_spec_abduction_recovers_action_gated_pause():
    """Zero-model recovery of an ACTION-gated positional pause: the timer pauses
    only when the mover sits in the window AND the action is a=1; the SAME
    window cell under a=0 ticks (a counterexample no positional or count guard
    can separate — provable only from the action). Abduction learns the overlap
    pause and, seeing the same-cell tick, scopes the veto to a=1; replay exact."""
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.spec_abduction import abduce_spec
    from ztare.worldmodel.spec_catalog import lower_spec
    truth, _ = lower_spec({
        "actions": {"0": [{"op": "translate_block", "match_colors": [9], "dy": 0,
                           "dx": 1, "require_dest_colors": [3], "fill_color": 3}],
                    "1": [{"op": "translate_block", "match_colors": [9], "dy": 0,
                           "dx": -1, "require_dest_colors": [3], "fill_color": 3}]},
        "always": [{"op": "consume_extremal", "color": 11, "replacement": 3,
                    "axis": "row", "extreme": "min",
                    "when_overlap": [[9], 0, 0, 0, 1, [1]]}]})

    def grid(c):                                   # mover 9 at (0,c); window cols 0-1
        row0 = [3] * 8
        row0[c] = 9
        return (tuple(row0), (11,) * 8)
    # out-of-window ticks (both actions) + same in-window cell under a=1 (pause)
    # and a=0 (tick): forces a positional AND action-scoped pause
    probes = [(5, 0), (5, 1), (6, 1), (6, 0), (1, 1), (1, 1), (1, 1), (1, 0)]
    log = EpisodeLog()
    for c, a in probes:
        s = grid(c)
        log.append(s, a, truth(s, a, 0), t=0)

    r = abduce_spec(log, 2)
    assert r.replay_ok and r.status == "spec_identified", r.detail
    scoped = [rule for rule in r.spec["always"]
              if rule.get("op") == "consume_extremal"
              and len(rule.get("when_overlap", [])) == 6]
    assert scoped, r.spec["always"]                # the pause was action-scoped
    assert scoped[0]["when_overlap"][5] == [1]     # to the pausing action only


def test_spec_abduction_recovers_derived_display_law():
    """Zero-model recovery of a DERIVED DISPLAY: a remote 4-cell panel renders
    panel = AND(flagA, flagB), each flag latched ON when the sprite reaches its
    trigger cell, the panel updated the SAME transition a flag flips.

    Crossing-write mining PROVABLY cannot close this: the panel's write on a
    flag's crossing depends on the OTHER, persistent flag, so no fixed write and
    no single-cell toggle is consistent across crossings — abduction WITHOUT the
    display refine stays `partial` (the negative assertion). The display law reads
    the flag's STEP-END state: an enter-triggered region_event (its crossing test
    consults the post-action grid) composed with a when_region on the unchanged
    flag; placed last in `always` it sees the already-flipped flag. Recovery is
    exact."""
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.spec_abduction import abduce_spec
    H, W = 10, 14
    FA, FB, TA, TB = (5, 1), (5, 12), (5, 4), (5, 9)
    PANEL = [(9, 0), (9, 1), (9, 2), (9, 3)]

    def fresh(mover):
        g = [[3] * W for _ in range(H)]
        g[mover[0]][mover[1]] = 7
        g[FA[0]][FA[1]] = 4
        g[FB[0]][FB[1]] = 4
        for (y, x) in PANEL:
            g[y][x] = 3
        return g

    def step(g, a):
        g = [row[:] for row in g]
        my, mx = next((y, x) for y in range(H) for x in range(W) if g[y][x] == 7)
        dy, dx = {0: (0, 1), 1: (0, -1), 2: (1, 0), 3: (-1, 0)}[a]
        ny, nx = my + dy, mx + dx
        if 0 <= ny < H and 0 <= nx < W and g[ny][nx] == 3:
            g[my][mx] = 3
            g[ny][nx] = 7
            my, mx = ny, nx
        if (my, mx) == TA:
            g[FA[0]][FA[1]] = 5
        if (my, mx) == TB:
            g[FB[0]][FB[1]] = 6
        on = (g[FA[0]][FA[1]] == 5 and g[FB[0]][FB[1]] == 6)
        for (y, x) in PANEL:
            g[y][x] = 8 if on else 3
        return g

    def path(s, tgt):
        seq, (my, mx) = [], next((y, x) for y in range(H) for x in range(W) if s[y][x] == 7)
        while mx != tgt[1]:
            a = 0 if tgt[1] > mx else 1
            seq.append(a)
            mx += 1 if a == 0 else -1
        while my != tgt[0]:
            a = 2 if tgt[0] > my else 3
            seq.append(a)
            my += 1 if a == 2 else -1
        return seq

    # concatenated independent episodes (the gate scores each transition alone),
    # exercising BOTH flag orders and single-flag (panel-off) cases
    episodes = [((5, 2), [TA, TB]), ((5, 2), [TB, TA]), ((5, 2), [TA]),
                ((5, 7), [TB]), ((5, 2), [TA, TB]), ((5, 11), [TB, TA])]
    log = EpisodeLog()
    for start, wps in episodes:
        s, plan = tuple(tuple(r) for r in fresh(start)), []
        for w in wps:
            plan += path(s, w)
            for a in path(s, w):
                s = tuple(tuple(r) for r in step([list(r) for r in s], a))
        s = tuple(tuple(r) for r in fresh(start))
        for a in plan:
            s2 = tuple(tuple(r) for r in step([list(r) for r in s], a))
            log.append(s, a, s2, t=0)
            s = s2

    # NEGATIVE: crossing-write mining alone cannot close the joint display
    off = abduce_spec(log, 4, _display_refine=False)
    assert off.status != "spec_identified", off.detail
    # the display law closes it exactly
    on = abduce_spec(log, 4, _display_refine=True)
    assert on.replay_ok and on.status == "spec_identified", on.detail
    enters = [r for r in on.spec["always"]
              if r.get("op") == "region_event" and r.get("edge") == "enter"]
    assert any("when_region" in r for r in enters), on.spec["always"]   # joint composition


def test_display_refine_support_filter_skips_zero_support_candidate_preserves_winner(monkeypatch):
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel import spec_abduction as SA

    spec = {
        "actions": {"0": [{"op": "translate_block", "match_colors": [1],
                           "dy": 0, "dx": 1, "require_dest_colors": [0],
                           "fill_color": 0}]},
        "always": [],
    }
    log = EpisodeLog()
    log.append(((1, 0, 0), (0, 0, 0)), 0,
               ((0, 1, 0), (0, 0, 2)), t=0)

    monkeypatch.setenv("ZTARE_DISPLAY_REFINE_FAST", "1")
    baseline_spec, _baseline_step = SA._derived_display_refine(spec, log)

    zero_support = {"op": "region_event", "mover_colors": [1],
                    "rect": [0, 2, 0, 2], "edge": "enter",
                    "writes": [[2, [[1, 2]]]]}
    zero_key = SA._freeze_deep(zero_support)
    original_candidates = SA._display_event_candidates
    original_score = SA._append_event_wrong_cell_count
    scored = []

    def planted_candidates(rt, mover, indicators, flaglike):
        return [zero_support] + original_candidates(rt, mover, indicators, flaglike)

    def score_spy(preds, ev, log_arg, env, incumbent=None):
        scored.append(SA._freeze_deep(ev))
        return original_score(preds, ev, log_arg, env, incumbent=incumbent)

    monkeypatch.setattr(SA, "_display_event_candidates", planted_candidates)
    monkeypatch.setattr(SA, "_append_event_wrong_cell_count", score_spy)

    planted_spec, _planted_step = SA._derived_display_refine(spec, log)

    assert zero_key not in scored
    assert planted_spec == baseline_spec


def test_cegar_classification_finds_aliasing_witness():
    """External-review fix: spurious abstraction is a TWO-state property —
    detected via a historical state with identical role signature whose
    ground truth OBEYS the lowered law this state refutes."""
    from ztare.common.abstraction_functor import (
        AbstractState, Role, classify_counterexample)

    class F:  # role map that (too coarsely) ignores the marker's position
        def abstract(self, states):
            return AbstractState(roles=[Role("mover", [1])])
        def lower(self, law, s):
            return law(s)

    law = lambda s: (tuple([0] + list(s[0][:-1])),)   # noqa: E731 — shift right
    s1, s1_next = ((1, 0, 0),), ((0, 1, 0),)          # obeys the law
    s2, s2_next = ((0, 0, 1),), ((0, 0, 1),)          # same roles; wall-blocked: refutes
    v = classify_counterexample(F(), law, s2, s2_next, law(s2), history=[(s1, s1_next)])
    assert v.kind == "spurious_abstraction", v
    # no witness -> the law itself is blamed
    v2 = classify_counterexample(F(), law, s2, s2_next, law(s2), history=[])
    assert v2.kind == "real_law_failure"
    # matching prediction -> not a counterexample at all
    v3 = classify_counterexample(F(), law, s1, s1_next, law(s1), history=[])
    assert v3.kind == "not_a_counterexample"


def test_reachability_sweep_separates_exhaustion_from_budget():
    """Certified sweep: returns a ranked goal path when reachable; returns
    model_target_unreachable only when the finite model frontier drains."""
    from ztare.worldmodel.reachability import reachability_sweep
    from ztare.worldmodel.grid_dsl import grid_from_lists
    # marker shifts right under action 0; goal = marker in last column
    champ = ("if", ("eq", ("action",), ("lit", 0)), ("shift", ("s",), 0, 1), ("s",))
    start = grid_from_lists([[1, 0, 0, 0]])
    r = reachability_sweep(champ, start, 2, goal_fn=lambda g: g[0][3] == 1, max_depth=8)
    assert r.status == "goal_paths" and [0, 0, 0] in r.paths, r
    # unreachable goal -> exact model-frontier exhaustion
    r2 = reachability_sweep(champ, start, 2, goal_fn=lambda g: g[0][0] == 9, max_depth=8)
    assert r2.status == "model_target_unreachable" and r2.exhaustive, r2
    # state cap -> indeterminate; a flat discovery derivative cannot upgrade it
    # into an unreachability verdict.
    r3 = reachability_sweep(
        champ, start, 2, goal_fn=lambda g: g[0][0] == 9,
        max_depth=8, max_states=1,
    )
    assert r3.status == "search_budget_exhausted" and not r3.exhaustive, r3


def test_invariant_bridge_filters_only_impossible_transitions():
    """Deterministic proof->planner bridge: a kernel-ratified monotone
    certificate drops only theorem-violating predicted transitions; it never
    prunes an admissible (winning) path."""
    from ztare.worldmodel.invariant_bridge import (
        InvariantCertificate, prediction_is_admissible)
    cert = InvariantCertificate(("count", 11), "non_increasing", "kernel_ratified")
    before = ((11, 11, 3),)
    ok_after = ((11, 3, 3),)      # bar fell -> admissible
    bad_after = ((11, 11, 11),)   # bar grew -> theorem-impossible -> dropped
    assert prediction_is_admissible([cert], before, ok_after)
    assert not prediction_is_admissible([cert], before, bad_after)
    # a merely conjectured invariant is NOT enforced (trust gated on ratification)
    conj = InvariantCertificate(("count", 11), "non_increasing", "conjectured")
    assert prediction_is_admissible([conj], before, bad_after)


def test_exploratory_coverage_without_goal():
    """Self-review fix: with no goal predicate, the sweep drives abstract-state
    COVERAGE (a path to the deepest reachable object-state) — the mechanism
    that finds the FIRST level before any goal exemplar exists."""
    from ztare.worldmodel.reachability import reachability_sweep
    from ztare.worldmodel.grid_dsl import grid_from_lists
    champ = ("if", ("eq", ("action",), ("lit", 0)), ("shift", ("s",), 0, 1), ("s",))
    start = grid_from_lists([[1, 0, 0, 0]])
    r = reachability_sweep(champ, start, 2, goal_fn=None, max_depth=8)
    assert r.status == "coverage" and r.paths and r.paths[0], r
    assert all(a == 0 for a in r.paths[0])   # coverage drives the marker rightward


# ── GP-250: automated operator-proposal channel + dynamic goal abduction ─────

def _rotate_block_2x2(g):
    """90° CW rotation of the 2x2 block at rows 1-2, cols 1-2 (a residual no
    catalog op expresses: a color-set permutation within a fixed bbox)."""
    g = [list(r) for r in g]
    a, b, c, d = g[1][1], g[1][2], g[2][1], g[2][2]
    g[1][1], g[1][2], g[2][1], g[2][2] = c, a, d, b
    return tuple(tuple(r) for r in g)


def test_operator_proposals_flags_rotation_residual_and_dedups(tmp_path):
    """A planted rotation-like residual clusters into one proposal card whose
    per-family failure proof marks translate_block failing the rigidity check
    and sketches a rotation operator; a second write is deduped by family sha."""
    from ztare.worldmodel.operator_proposals import propose_operators, write_proposals
    from ztare.worldmodel.episode_log import EpisodeLog

    # colour 4 sits at two block corners so a 90° rotation sends it to two
    # different colours -> not a functional recolor, not rigid, not consumable
    base = ((3, 3, 3, 3), (3, 4, 5, 3), (3, 6, 4, 3), (3, 3, 3, 3))
    log = EpisodeLog()
    s = base
    for _ in range(6):
        s2 = _rotate_block_2x2(s)
        log.append(s, 0, s2, t=0)
        s = s2

    cards = propose_operators(log, {}, list(range(len(log))))
    assert cards, "expected at least one proposal card"
    card = cards[0]
    assert card["schema"] == "worldmodel-operator-proposal-v1"
    assert card["evidence_indices"], card
    tb = card["why_existing_ops_fail"]["translate_block"]
    assert "not rigid" in tb, tb
    # every existing family must be marked as failing (it is a genuine residual)
    assert "not a recolor" in card["why_existing_ops_fail"]["recolor_map"]
    assert "not region_event" in card["why_existing_ops_fail"]["region_event"]
    assert "rotate" in card["proposed_operator_sketch"].lower(), card["proposed_operator_sketch"]

    w1 = write_proposals(tmp_path, cards)
    assert w1, "first write should persist the card"
    w2 = write_proposals(tmp_path, cards)
    assert w2 == [], "second write of the same family must dedup to nothing"
    ledger = (tmp_path / "workspace" / "operator_proposals.jsonl").read_text().splitlines()
    assert len(ledger) == len(w1)   # no duplicate rows appended


def test_operator_proposal_contract_validation_and_dispositions():
    """The kernel contract validates card shape and filters dispositioned cards
    out of the mutator-facing open set."""
    from ztare.common.operator_proposal_contract import (
        DISPOSITION_ACCEPTED, is_open, operator_proposal_card, set_disposition,
        validate_operator_proposal_card,
    )
    card = operator_proposal_card(
        failure_family="fam-A",
        evidence_indices=[0, 1],
        spatial_footprint={"bbox": [0, 0, 1, 1]},
        why_existing_ops_fail={"translate_block": "not rigid"},
        proposed_operator_sketch="rotate_block(...)",
        acceptance_test="planted synthetic log ...",
    )
    assert validate_operator_proposal_card(card)["status"] == "pass"
    assert is_open(card)
    accepted = set_disposition(card, DISPOSITION_ACCEPTED)
    assert not is_open(accepted)
    broken = dict(card)
    broken.pop("why_existing_ops_fail")
    assert validate_operator_proposal_card(broken)["status"] == "fail"


def test_goal_abduction_pre_success_finds_dormant_event():
    """Pre-success mode: a region_event whose write never fired in the log is
    surfaced as a dormant-event goal candidate, and predicate_from_spec compiles
    it to a region-differs-from-start goal_fn."""
    from ztare.worldmodel.goal_abduction import (
        abduce_goal_candidates, predicate_from_spec,
    )
    from ztare.worldmodel.episode_log import EpisodeLog

    spec = {
        "actions": {"0": [{"op": "translate_block", "match_colors": [7], "dy": 0,
                           "dx": 1, "require_dest_colors": [3], "fill_color": 3}]},
        "always": [{"op": "region_event", "mover_colors": [7], "rect": [0, 0, 0, 0],
                    "edge": "exit", "writes": [[6, [[4, 3]]]]}]}
    # the mover 7 slides right but never sits in the rect (0,0); the flag (4,3)
    # never lights -> the event is dormant
    g0 = ((3, 3, 7, 3, 3), (3, 3, 3, 3, 3), (3, 3, 3, 3, 3),
          (3, 3, 3, 3, 3), (3, 3, 3, 3, 3))
    log = EpisodeLog()
    s = g0
    for col in (3, 4):
        row = list(s[0])
        row[col - 1], row[col] = 3, 7
        s2 = (tuple(row),) + s[1:]
        log.append(s, 0, s2, t=0)
        s = s2

    res = abduce_goal_candidates(log, spec, [])
    assert res["mode"] == "pre_success", res
    dormant = [c for c in res["candidates"] if c["kind"] == "dormant_region_event"]
    assert dormant, res
    region = dormant[0]["predicate_spec"]["region"]
    y0, x0, y1, x1 = region
    assert y0 <= 4 <= y1 and x0 <= 3 <= x1, region

    goal = predicate_from_spec(dormant[0]["predicate_spec"], g0)
    assert not goal(g0)                       # flag unset == start
    lit = [list(r) for r in g0]
    lit[4][3] = 6
    assert goal(tuple(tuple(r) for r in lit))  # flag set == goal


def test_goal_abduction_post_success_recovers_goal_region():
    """Post-success mode: two synthetic completions (resource refills) with a
    consistent indicator change in the 3 pre-completion frames recover the goal
    region and report support == 2, excluding the depleting resource (timer)."""
    from ztare.worldmodel.goal_abduction import abduce_goal_candidates
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.common.abstraction_functor import Role

    E0 = ((7, 3, 3, 3), (11, 11, 11, 3))       # resource 11 bar, indicator at (0,3)
    S1 = ((7, 3, 3, 6), (3, 11, 11, 3))        # indicator lit, one 11 consumed
    S2 = ((7, 3, 3, 6), (3, 3, 11, 3))
    S3 = ((7, 3, 3, 6), (3, 3, 3, 3))          # bar empty, indicator still lit
    episode = [(E0, S1), (S1, S2), (S2, S3), (S3, E0)]  # last = completion (refill)

    log = EpisodeLog()
    for _ep in range(2):
        for t, (s, s2) in enumerate(episode):
            log.append(s, 0, s2, t=t)

    roles = [Role("monotone_depleting", [11], "bar")]
    res = abduce_goal_candidates(log, {}, roles)
    assert res["mode"] == "post_success", res
    assert res["support"] == 2, res
    y0, x0, y1, x1 = res["goal_predicate_spec"]["region"]
    assert (y0, x0, y1, x1) == (0, 3, 0, 3), res   # the indicator, not the timer row


# ── BUILD 1: persistent cross-episode frontier memory ────────────────────────

def test_sweep_frontier_memory_avoids_visited_and_saturates():
    """Coverage with a visited_store targets the deepest UNVISITED reachable
    state; when every reachable state is visited it saturates and falls back to
    the deepest overall."""
    from ztare.worldmodel.reachability import reachability_sweep
    from ztare.worldmodel.grid_dsl import grid_from_lists
    # single-action shift-drop world: a clean linear chain [1000]->[0100]->
    # [0010]->[0001]->[0000] (arity 1 + max_depth 4 avoids step%6 sink recurrence)
    champ = ("shift", ("s",), 0, 1)
    start = grid_from_lists([[1, 0, 0, 0]])
    abstract = lambda g: frozenset(  # noqa: E731 — full signature: every cell
        (y, x, g[y][x]) for y in range(len(g)) for x in range(len(g[0])))
    # no store: deepest reachable is the empty grid (marker shifted off) at depth 4
    r0 = reachability_sweep(champ, start, 1, goal_fn=None, abstract_fn=abstract, max_depth=4)
    assert r0.status == "coverage" and r0.paths[0] == [0, 0, 0, 0] and not r0.saturated, r0
    # mark the deepest (empty) state visited -> next-deepest novel = marker last col
    store = {abstract(grid_from_lists([[0, 0, 0, 0]]))}
    r1 = reachability_sweep(champ, start, 1, goal_fn=None, abstract_fn=abstract,
                            visited_store=store, max_depth=4)
    assert r1.status == "coverage" and not r1.saturated and r1.paths[0] == [0, 0, 0], r1
    # every reachable state visited -> saturated, fall back to deepest overall
    reachable = ([1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1], [0, 0, 0, 0])
    store_all = {abstract(grid_from_lists([row])) for row in reachable}
    r2 = reachability_sweep(champ, start, 1, goal_fn=None, abstract_fn=abstract,
                            visited_store=store_all, max_depth=4)
    assert r2.saturated and r2.paths[0] == [0, 0, 0, 0], r2


def test_coverage_frontier_ignores_passive_resource_only_novelty():
    """A caller-supplied coverage projection can prefer controlled-object
    novelty over passive resource deltas. Reachability still memoizes the full
    abstract state; it does not infer the projection itself."""
    from ztare.worldmodel.object_roles import control_signature
    from ztare.worldmodel.reachability import reachability_sweep
    start = ((1, 0, 6, 6),)

    def champ(g, a, _t):
        row = list(g[0])
        if a == 0:
            for i, v in enumerate(row):
                if v == 6:
                    row[i] = 0
                    break
            return (tuple(row),)
        if a == 1:
            x = row.index(1)
            if x + 1 < len(row) and row[x + 1] == 0:
                row[x], row[x + 1] = 0, 1
            return (tuple(row),)
        return g

    def abstract(g):
        agent = frozenset((0, x) for x, v in enumerate(g[0]) if v == 1)
        resource = ((6, sum(1 for v in g[0] if v == 6)),)
        return (agent, resource, frozenset())

    r = reachability_sweep(champ, start, 2, goal_fn=None, abstract_fn=abstract,
                           coverage_fn=control_signature,
                           visited_store={abstract(start)}, max_depth=3)
    assert r.status == "coverage" and r.paths and r.paths[0][0] == 1, r


def test_visited_store_save_load_roundtrip(tmp_path):
    """save_visited/load_visited round-trip abstract keys (frozensets of tuples);
    a missing file loads to an empty set."""
    from ztare.worldmodel.reachability import load_visited, save_visited
    keys = {frozenset({(0, 0, 1), (0, 3, 2)}), frozenset({(1, 1, 5)})}
    p = tmp_path / "workspace" / "visited.jsonl"
    save_visited(p, keys)
    assert load_visited(p) == keys
    assert load_visited(tmp_path / "absent.jsonl") == set()


def test_visited_store_roundtrip_nested_role_signature(tmp_path):
    """Frontier memory persists role signatures, not only flat cell sets."""
    from ztare.worldmodel.reachability import load_visited, save_visited
    key = (
        frozenset({(2, 3), (2, 4)}),
        ((6, 18),),
        frozenset({(4, 7, 5)}),
    )
    p = tmp_path / "workspace" / "visited_nested.jsonl"
    save_visited(p, {key})
    assert load_visited(p) == {key}


# ── BUILD 2: dormant-conjunction goal candidates ─────────────────────────────

def test_goal_abduction_dormant_conjunction():
    """Two indicator regions each witnessed changed-from-start alone but never in
    the same frame surface a dormant_conjunction candidate; predicate_from_spec
    compiles the AND (true only when BOTH differ)."""
    from ztare.worldmodel.goal_abduction import (
        abduce_goal_candidates, predicate_from_spec)
    from ztare.worldmodel.episode_log import EpisodeLog
    # two region_event rules writing flag A at (0,0) and flag B at (0,2)
    spec = {"always": [
        {"op": "region_event", "mover_colors": [7], "rect": [0, 0, 0, 0],
         "edge": "exit", "writes": [[6, [[0, 0]]]]},
        {"op": "region_event", "mover_colors": [7], "rect": [0, 0, 0, 0],
         "edge": "exit", "writes": [[6, [[0, 2]]]]}]}
    start = ((3, 3, 3),)
    log = EpisodeLog()
    log.append(start, 0, ((6, 3, 3),), t=0)     # A lit, B not
    log.append(((6, 3, 3),), 0, ((3, 3, 6),), t=1)  # B lit, A not — never together
    res = abduce_goal_candidates(log, spec, [])
    assert res["mode"] == "pre_success", res
    conj = [c for c in res["candidates"] if c["kind"] == "dormant_conjunction"]
    assert conj, res
    goal = predicate_from_spec(conj[0]["predicate_spec"], start)
    assert not goal(start)             # neither differs
    assert not goal(((6, 3, 3),))      # only A differs
    assert not goal(((3, 3, 6),))      # only B differs
    assert goal(((6, 3, 6),))          # both differ -> conjunction satisfied


def test_goal_predicate_preserves_exact_support_not_bounding_hull():
    """Changing an unrelated cell inside a support's display hull is inert."""
    from ztare.worldmodel.goal_abduction import predicate_from_spec

    start = ((3, 3, 3),)
    spec = {
        "cells": [[0, 0], [0, 2]],
        "region": [0, 0, 0, 2],
        "differs_from_start": True,
    }
    goal = predicate_from_spec(spec, start)
    assert not goal(((3, 9, 3),))
    assert goal(((9, 3, 3),))


def test_goal_abduction_no_conjunction_when_co_witnessed():
    """When the two indicators are once seen simultaneously changed, the
    conjunction is not dormant -> no candidate."""
    from ztare.worldmodel.goal_abduction import abduce_goal_candidates
    from ztare.worldmodel.episode_log import EpisodeLog
    spec = {"always": [
        {"op": "region_event", "mover_colors": [7], "rect": [0, 0, 0, 0],
         "edge": "exit", "writes": [[6, [[0, 0]]]]},
        {"op": "region_event", "mover_colors": [7], "rect": [0, 0, 0, 0],
         "edge": "exit", "writes": [[6, [[0, 2]]]]}]}
    log = EpisodeLog()
    log.append(((3, 3, 3),), 0, ((6, 3, 6),), t=0)   # A and B lit in ONE frame
    res = abduce_goal_candidates(log, spec, [])
    assert not [c for c in res["candidates"] if c["kind"] == "dormant_conjunction"], res


# ── lean_bridge: deterministic worldmodel<->leanmill feedback loop ────────────

def _bridge_log(rows):
    from ztare.worldmodel.episode_log import EpisodeLog
    log = EpisodeLog()
    for t, (s, s2) in enumerate(rows):
        log.append(s, 0, s2, t=t)
    return log


def test_lean_bridge_conjectures_monotone_and_conserved_skips_refill():
    from ztare.worldmodel.lean_bridge import conjecture_invariants
    # color 11 strictly depletes (monotone), 4 is a constant wall, 7 refills.
    frames = [
        (((11, 11, 7, 4),), ((11, 3, 7, 4),)),   # 11: 2->1 (down), 7: 1->1
        (((11, 3, 7, 4),), ((3, 3, 7, 4),)),     # 11: 1->0 (down), 7: 1->1
        (((3, 3, 7, 4),), ((3, 7, 7, 4),)),      # 11: 0->0,        7: 1->2 (refill)
    ]
    conj = conjecture_invariants(_bridge_log(frames), {}, [])
    by_name = {c["name"]: c for c in conj}
    assert "count11_monotone" in by_name, conj
    assert by_name["count11_monotone"]["relation"] == "non_increasing"
    assert "count4_conserved" in by_name, conj
    assert by_name["count4_conserved"]["relation"] == "constant"
    assert "count7_monotone" not in by_name and "count7_conserved" not in by_name, conj
    # monotone conjectures are ordered before conserved ones (Target = the law)
    assert conj[0]["name"].endswith("_monotone"), conj


def test_lean_bridge_blueprint_has_theory_target_and_conjecture():
    from ztare.worldmodel.lean_bridge import blueprint_from_spec
    spec = {"actions": {"0": [{"op": "consume_extremal", "axis": "row", "color": 11,
                              "replacement": 3, "extreme": "min"}]}, "always": []}
    frames = [(((11, 11, 3),), ((11, 3, 3),)), (((11, 3, 3),), ((3, 3, 3),))]
    md = blueprint_from_spec(spec, _bridge_log(frames), [])
    assert "## Domain" in md and "worldmodel-invariant" in md
    assert "## Theory" in md and "## Target" in md
    assert "sorry" in md
    assert "count11_monotone" in md
    assert "def specStep" in md


def test_play_loop_emits_leanmill_blueprint_receipt(tmp_path):
    mod = _load_arc3_play_loop()
    from ztare.worldmodel.episode_log import EpisodeLog

    project = tmp_path / "project"
    log = EpisodeLog()
    log.append(((11, 11, 3),), 0, ((11, 3, 3),), t=0)
    log.append(((11, 3, 3),), 0, ((3, 3, 3),), t=1)
    spec = {"actions": {"0": [{"op": "consume_extremal", "axis": "row",
                              "color": 11, "replacement": 3,
                              "extreme": "min"}]}, "always": []}

    path = mod._write_worldmodel_blueprint(project, log, spec)

    assert path == project / "workspace" / "worldmodel_auto_blueprint.md"
    assert "count11_monotone" in path.read_text()
    receipt = json.loads(
        (project / "workspace" / "worldmodel_lean_feedback_receipt.json").read_text()
    )
    assert receipt["status"] == "blueprint_emitted"
    assert receipt["blueprint_ref"] == "workspace/worldmodel_auto_blueprint.md"
    assert len(receipt["blueprint_sha256"]) == 64
    assert len(receipt["spec_sha256"]) == 64
    assert len(receipt["evidence_epoch_sha256"]) == 64
    assert "ztare.leanmill.cli campaign" in receipt["next_command"]
    assert receipt["next_command"].endswith(
        "project/workspace/worldmodel_auto_blueprint.md"
    )
    assert "ztare.leanmill.workbench_actions autoformalize-notes" in receipt["async_command"]
    assert "--project project --save --json" in receipt["async_command"]
    assert "ztare.worldmodel.lean_bridge absorb" in receipt["absorb_command_template"]
    assert receipt["evidence_hash"] == log.content_hash()
    assert receipt["routes"]["prove_current_spec"]["status"] == "ready"
    assert receipt["routes"]["repair_single_proof_gap"]["status"] == "inside_leanmill"
    axiom_route = receipt["routes"]["discover_reusable_theory"]
    assert axiom_route["status"] == "awaiting_signed_unseen_task_family"
    assert axiom_route["minimum_distinct_eval_tasks"] == 2
    assert "typed_axiom_pack_blueprint.json" in axiom_route["command_template"]
    assert "byte-matched L1/L2/L3 proof audit" in receipt["authority"]
    assert not (project / "workspace" / "invariant_certificates.jsonl").exists()


def test_component_scoped_consume_extremal_selects_quotient_class_not_all_same_color():
    from ztare.worldmodel.spec_catalog import lower_spec, validate_spec

    grid = (
        (0, 11, 11, 11, 11, 0, 0),
        (0, 11, 11, 11, 11, 0, 0),
        (0, 0, 0, 0, 0, 0, 0),
        (0, 11, 11, 0, 0, 0, 0),
        (0, 11, 0, 0, 0, 0, 0),
    )
    spec = {"actions": {"0": [{"op": "identity"}]}, "always": [{
        "op": "consume_extremal", "color": 11, "replacement": 3,
        "axis": "row", "extreme": "min", "count": 2,
        "component_scope": {"colors": [11], "select": "largest", "min_size": 4},
    }]}
    step, err = lower_spec(spec)
    assert err == "", err
    out = step(grid, 0, 0)
    assert out[0] == (0, 3, 3, 11, 11, 0, 0)
    assert out[1] == (0, 3, 3, 11, 11, 0, 0)
    assert out[3] == grid[3]
    assert out[4] == grid[4]
    bad = {"actions": {"0": [{"op": "consume_extremal", "color": 11, "replacement": 3,
                              "component_scope": {"select": "leftmost"}}]}}
    assert "bad component_scope select" in validate_spec(bad)


def test_component_scoped_consume_count_observes_only_selected_quotient():
    from ztare.worldmodel.spec_abduction import _transition_consume_count
    from ztare.worldmodel.episode_log import Transition
    from ztare.worldmodel.spec_catalog import lower_spec

    grid = (
        (0, 11, 11, 11, 11, 0, 0),
        (0, 11, 11, 11, 11, 0, 0),
        (0, 0, 0, 0, 0, 0, 0),
        (0, 11, 11, 0, 0, 0, 0),
        (0, 11, 0, 0, 0, 0, 0),
    )
    rule = {
        "op": "consume_extremal", "color": 11, "replacement": 3,
        "axis": "row", "extreme": "min", "count": 2,
        "component_scope": {"colors": [11], "select": "largest", "min_size": 4},
    }
    step, err = lower_spec({"actions": {"0": [{"op": "identity"}]},
                            "always": [rule]})
    assert step is not None, err
    tr = Transition(0, grid, 0, step(grid, 0, 0))

    assert _transition_consume_count(tr, rule) == 2


def test_refinement_ladder_scopes_consume_to_component_quotient():
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.gates import replay_consistency_gate
    from ztare.worldmodel.refinement_ladder import run_refinement_ladder
    from ztare.worldmodel.spec_catalog import lower_spec

    grid = (
        (11, 0, 0, 0, 0, 0),
        (11, 0, 0, 0, 0, 0),
        (0, 0, 0, 0, 0, 0),
        (0, 11, 11, 11, 11, 0),
        (0, 11, 11, 11, 11, 0),
    )
    truth_spec = {"actions": {"0": [{"op": "identity"}]}, "always": [{
        "op": "consume_extremal", "color": 11, "replacement": 3,
        "axis": "row", "extreme": "min",
        "component_scope": {"colors": [11], "select": "largest", "min_size": 2},
    }]}
    truth, err = lower_spec(truth_spec)
    assert truth is not None, err
    log = EpisodeLog()
    for t in range(4):
        log.append(grid, 0, truth(grid, 0, t), t=t)

    seed_spec = {"actions": {"0": [{"op": "identity"}]}, "always": [{
        "op": "consume_extremal", "color": 11, "replacement": 3,
        "axis": "row", "extreme": "min",
    }]}
    seed, err = lower_spec(seed_spec)
    assert seed is not None, err
    assert not replay_consistency_gate(seed, log).ok

    refined, step = run_refinement_ladder(seed_spec, seed, log)

    assert replay_consistency_gate(step, log).ok
    timer = [r for r in refined["always"] if r.get("op") == "consume_extremal"][0]
    assert timer["component_scope"]["select"] == "largest"
    assert timer["component_scope"]["colors"] == [11]


def test_component_scope_refine_splits_by_observable_count_threshold():
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.gates import replay_consistency_gate
    from ztare.worldmodel.spec_abduction import _component_scope_consume_refine
    from ztare.worldmodel.spec_catalog import lower_spec

    low = (
        (11, 11, 0, 0, 0, 0),
        (11, 11, 0, 0, 0, 0),
    )
    high = (
        (11, 11, 11, 11, 0, 11),
        (11, 11, 11, 11, 0, 11),
    )
    truth_spec = {"actions": {"0": [{"op": "identity"}]}, "always": [
        {"op": "consume_extremal", "color": 11, "replacement": 3,
         "axis": "row", "extreme": "min", "when_count": [11, None, 4]},
        {"op": "consume_extremal", "color": 11, "replacement": 3,
         "axis": "row", "extreme": "min", "count": 2,
         "component_scope": {"colors": [11], "select": "largest", "min_size": 2},
         "when_count": [11, 5, None]},
    ]}
    truth, err = lower_spec(truth_spec)
    assert truth is not None, err
    log = EpisodeLog()
    for s in (low, high, low, high):
        log.append(s, 0, truth(s, 0, 0), t=0)

    seed_spec = {"actions": {"0": [{"op": "identity"}]}, "always": [
        {"op": "consume_extremal", "color": 11, "replacement": 3,
         "axis": "row", "extreme": "min"},
    ]}
    seed, err = lower_spec(seed_spec)
    assert seed is not None, err
    assert not replay_consistency_gate(seed, log).ok

    refined, step = _component_scope_consume_refine(seed_spec, log)

    assert replay_consistency_gate(step, log).ok
    rules = [r for r in refined["always"] if r.get("op") == "consume_extremal"]
    assert any(r.get("component_scope") and r.get("count") == 2 for r in rules)
    assert any((r.get("when_count") or [None, None, None])[2] is not None
               for r in rules)
    assert any((r.get("when_count") or [None, None, None])[1] is not None
               for r in rules)


def test_noise_deferral_preserves_short_reset_segments():
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.spec_abduction import _noise_deferred_frames

    log = EpisodeLog()
    for t in range(240):
        s = ((t + 1, 0),)
        nxt = ((t + 2, 0),)
        log.append(s, 0, nxt, t=t)
    suffix_start = len(log)
    for t in (3, 4, 5, 3, 4, 5):
        s = ((11, t),)
        nxt = ((3, t),)
        log.append(s, 0, nxt, t=t)

    deferred = _noise_deferred_frames(log, env=set(), min_support=2)

    assert len(deferred) > 0
    assert not (deferred & set(range(suffix_start, len(log))))


def test_count_guard_consume_refine_splits_magnitude_by_observable_count():
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.spec_abduction import _count_guard_consume_refine
    from ztare.worldmodel.gates import replay_consistency_gate
    from ztare.worldmodel.spec_catalog import lower_spec

    truth_spec = {"actions": {"0": [{"op": "identity"}]}, "always": [
        {"op": "consume_extremal", "color": 6, "replacement": 0,
         "axis": "row", "extreme": "min"},
        {"op": "consume_extremal", "color": 6, "replacement": 0,
         "axis": "row", "extreme": "min", "when_count": [6, 8, None]},
    ]}
    truth, err = lower_spec(truth_spec)
    assert err == "", err
    low = ((6, 6, 0, 0), (6, 6, 0, 0))
    high = ((6, 6, 6, 6), (6, 6, 6, 6))
    log = EpisodeLog()
    for s in (low, high, low, high):
        log.append(s, 0, truth(s, 0, 0), t=0)

    seed_spec = {"actions": {"0": [{"op": "identity"}]}, "always": [
        {"op": "consume_extremal", "color": 6, "replacement": 0,
         "axis": "row", "extreme": "min"},
    ]}
    seed_step, err = lower_spec(seed_spec)
    assert err == "", err
    assert not replay_consistency_gate(seed_step, log).ok
    refined, step = _count_guard_consume_refine(seed_spec, log)
    assert replay_consistency_gate(step, log).ok
    rules = [r for r in refined["always"] if r.get("op") == "consume_extremal"]
    assert any(r.get("when_count") == [6, 8, None] for r in rules), refined


def test_lean_bridge_absorb_ratification_writes_nothing_on_failed_lake(tmp_path, monkeypatch):
    from ztare.worldmodel import lean_bridge
    # point the proofs dir at a nonexistent path -> no lake invocation, no write
    monkeypatch.setattr(lean_bridge, "_proofs_dir", lambda: tmp_path / "no_such_proofs")
    stmt = ("theorem count11_monotone (g : Grid) (a t : Nat) : "
            "countColor (specStep g a t) 11 ≤ countColor g 11 := by sorry")
    out = lean_bridge.absorb_ratification(tmp_path, tmp_path / "x.lean", [stmt])
    assert out == []
    assert not (tmp_path / "workspace" / "invariant_certificates.jsonl").exists()


def _passing_worldmodel_proof_audit(path, theorem):
    import hashlib

    return {
        "schema": "leanmill-pr-a1-compile-l3-audit-v1",
        "status": "compile_pass_l3_advisory_pass",
        "target": str(path),
        "target_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "top_level_target_resolved": theorem,
        "static_clean": True,
        "static": {"sorry_count": 0, "admit_count": 0, "axiom_decl_count": 0},
        "compile": {"ok": True},
        "kernel_axiom_policy": {"allowlist_ok": True, "disallowed_axioms": {}},
        "l3_audit": {
            "status": "pass",
            "confirmed_blockers": [],
            "review_flags": [],
            "rows": [{"name": theorem}],
        },
    }


def _current_test_invariant_binding(*_args, **_kwargs):
    return {
        "binding_schema": "ztare-worldmodel-invariant-binding-v1",
        "spec_sha256": "1" * 64,
        "evidence_epoch_sha256": "3" * 64,
    }


def test_lean_bridge_absorb_ratification_persists_and_dedups(tmp_path, monkeypatch):
    import json as _json
    from ztare.worldmodel import lean_bridge

    stmt = ("theorem count11_monotone (g : Grid) (a t : Nat) : "
            "countColor (specStep g a t) 11 ≤ countColor g 11 := by sorry")
    lean = tmp_path / "x.lean"
    lean.write_text(stmt.replace("by sorry", "by exact proof"), encoding="utf-8")
    monkeypatch.setattr(
        lean_bridge,
        "_run_proof_audit",
        lambda path, theorem: _passing_worldmodel_proof_audit(path, theorem),
    )
    monkeypatch.setattr(
        lean_bridge, "current_invariant_binding", _current_test_invariant_binding
    )
    certs = lean_bridge.absorb_ratification(tmp_path, lean, [stmt])
    assert len(certs) == 1 and certs[0].status == "kernel_ratified"

    jsonl = tmp_path / "workspace" / "invariant_certificates.jsonl"
    rows = [_json.loads(l) for l in jsonl.read_text().splitlines() if l.strip()]
    assert len(rows) == 1
    assert rows[0]["quantity"] == ["count", 11]
    assert rows[0]["relation"] == "non_increasing"
    assert rows[0]["status"] == "kernel_ratified"
    assert rows[0]["theorem"] == "count11_monotone"
    assert len(rows[0]["artifact_sha256"]) == 64
    assert len(rows[0]["proof_audit_sha256"]) == 64
    # second call is a no-op: dedup on (quantity, relation, theorem)
    again = lean_bridge.absorb_ratification(tmp_path, lean, [stmt])
    assert again == []
    assert len(jsonl.read_text().splitlines()) == 1


def test_lean_bridge_absorb_cli_extracts_theorem_and_writes_cert(tmp_path, monkeypatch, capsys):
    import json as _json
    from ztare.worldmodel import lean_bridge

    lean = tmp_path / "timer.lean"
    lean.write_text(
        "theorem timer_monotone : ∀ (g : Grid) (a t : Nat),\n"
        "    countColor (specStep g a t) 11 ≤ countColor g 11 := by\n"
        "  exact proof\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        lean_bridge,
        "_run_proof_audit",
        lambda path, theorem: _passing_worldmodel_proof_audit(path, theorem),
    )
    monkeypatch.setattr(
        lean_bridge, "current_invariant_binding", _current_test_invariant_binding
    )

    rc = lean_bridge.main([
        "absorb", "--project", str(tmp_path), "--lean-file", str(lean),
        "--theorem", "timer_monotone",
    ])
    assert rc == 0
    payload = _json.loads(capsys.readouterr().out)
    assert payload["status"] == "absorbed"
    assert payload["certificates"] == [{
        "quantity": ["count", 11],
        "relation": "non_increasing",
        "status": "kernel_ratified",
        "theorem": "timer_monotone",
    }]

    rows = [
        _json.loads(l)
        for l in (tmp_path / "workspace" / "invariant_certificates.jsonl").read_text().splitlines()
    ]
    assert [{k: row[k] for k in ("quantity", "relation", "status", "theorem")} for row in rows] == payload["certificates"]


def test_lean_bridge_rejects_sorry_even_if_audit_payload_claims_clean(tmp_path, monkeypatch):
    from ztare.worldmodel import lean_bridge

    lean = tmp_path / "unsafe.lean"
    lean.write_text("theorem count11_monotone : True := by sorry\n", encoding="utf-8")
    monkeypatch.setattr(
        lean_bridge,
        "_run_proof_audit",
        lambda path, theorem: _passing_worldmodel_proof_audit(path, theorem),
    )
    monkeypatch.setattr(
        lean_bridge, "current_invariant_binding", _current_test_invariant_binding
    )

    assert lean_bridge.absorb_ratification(
        tmp_path,
        lean,
        ["theorem count11_monotone : True := by sorry"],
    ) == []


def test_lean_bridge_binds_invariant_statement_to_audited_file(tmp_path, monkeypatch):
    from ztare.worldmodel import lean_bridge

    lean = tmp_path / "weak.lean"
    lean.write_text("theorem count11_monotone : True := by trivial\n", encoding="utf-8")
    monkeypatch.setattr(
        lean_bridge,
        "_run_proof_audit",
        lambda path, theorem: _passing_worldmodel_proof_audit(path, theorem),
    )
    monkeypatch.setattr(
        lean_bridge, "current_invariant_binding", _current_test_invariant_binding
    )
    stronger_caller_statement = (
        "theorem count11_monotone (g : Grid) (a t : Nat) : "
        "countColor (specStep g a t) 11 <= countColor g 11 := by sorry"
    )

    assert lean_bridge.absorb_ratification(
        tmp_path,
        lean,
        [stronger_caller_statement],
    ) == []


# ── GP-250: toggle/cycle region events + region/phase guards + depletion goals ─

def test_spec_region_event_toggle_and_cycle_lower():
    """A region_event may PERMUTE colours over its cell-set on a crossing (a
    switch/latch/door), not just fix-write: `toggle` swaps a pair on every
    crossing (correct on both phases — a fixed write is wrong on half), and
    `cycle` rotates a k-state indicator."""
    from ztare.worldmodel.spec_catalog import lower_spec
    tstep, err = lower_spec({
        "actions": {"0": [{"op": "translate_block", "match_colors": [7], "dy": 0,
                           "dx": 1, "require_dest_colors": [3], "fill_color": 3}]},
        "always": [{"op": "region_event", "mover_colors": [7], "rect": [0, 2, 0, 2],
                    "edge": "exit", "writes": [[9, [[3, 0], [3, 1]]]], "toggle": [[5, 9]]}]})
    assert tstep is not None, err
    # mover 7 in the rect (col 2) exits right -> HUD swaps 9<->5
    g = ((3, 3, 7, 3, 3), (3, 3, 3, 3, 3), (3, 3, 3, 3, 3), (9, 5, 3, 3, 3))
    out = tstep(g, 0, 0)
    assert out[3][0] == 5 and out[3][1] == 9              # 9->5 and 5->9
    # a fresh crossing from the other phase swaps back
    g2 = ((3, 3, 7, 3, 3), (3, 3, 3, 3, 3), (3, 3, 3, 3, 3), (5, 9, 3, 3, 3))
    assert tstep(g2, 0, 0)[3][:2] == (9, 5)
    # 3-cycle: 1->2->3->1 on each crossing
    cstep, err2 = lower_spec({
        "actions": {"0": [{"op": "translate_block", "match_colors": [7], "dy": 0,
                           "dx": 1, "require_dest_colors": [3], "fill_color": 3}]},
        "always": [{"op": "region_event", "mover_colors": [7], "rect": [0, 2, 0, 2],
                    "edge": "exit", "writes": [[1, [[3, 0]]]], "cycle": [[1, 2, 3]]}]})
    assert cstep is not None, err2
    assert cstep(((3, 3, 7, 3), (3,) * 4, (3,) * 4, (1, 3, 3, 3)), 0, 0)[3][0] == 2
    assert cstep(((3, 3, 7, 3), (3,) * 4, (3,) * 4, (2, 3, 3, 3)), 0, 0)[3][0] == 3
    assert cstep(((3, 3, 7, 3), (3,) * 4, (3,) * 4, (3, 3, 3, 3)), 0, 0)[3][0] == 1
    # malformed toggle / cycle fail-close
    bad, e3 = lower_spec({"actions": {"0": [{"op": "region_event", "mover_colors": [7],
                          "rect": [0, 0, 0, 0], "edge": "exit", "writes": [],
                          "toggle": [[5]]}]}})
    assert bad is None and "toggle" in e3


def test_spec_abduction_recovers_planted_toggle():
    """Zero-model recovery of a state-dependent TOGGLE from a synthetic swap log
    (no substrate constants): a mover slides back and forth over floor, and each
    time it exits a fixed rect a remote HUD cell-set SWAPS {5,9}. A fixed write
    is wrong on half the crossings; abduction detects the swap (a cell shows
    5->9 AND 9->5) and emits the toggle variant. Replay exact."""
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.spec_abduction import abduce_spec
    from ztare.worldmodel.spec_catalog import lower_spec
    truth, _ = lower_spec({
        "actions": {"0": [{"op": "translate_block", "match_colors": [7], "dy": 0,
                           "dx": 1, "require_dest_colors": [3], "fill_color": 3}],
                    "1": [{"op": "translate_block", "match_colors": [7], "dy": 0,
                           "dx": -1, "require_dest_colors": [3], "fill_color": 3}]},
        "always": [{"op": "region_event", "mover_colors": [7], "rect": [0, 2, 0, 2],
                    "edge": "exit", "writes": [[9, [[3, 0]]]], "toggle": [[5, 9]]}]})
    g = ((3, 3, 7, 3, 3), (3, 3, 3, 3, 3), (3, 3, 3, 3, 3), (5, 3, 3, 3, 3))
    log = EpisodeLog()
    s = g
    for a in (0, 0, 1, 1, 0, 0, 1, 1, 0, 0):
        s2 = truth(s, a, 0)
        log.append(s, a, s2, t=0)
        s = s2
    r = abduce_spec(log, 2)
    assert r.replay_ok and r.status == "spec_identified", r.detail
    tog = [rl for rl in r.spec["always"]
           if rl.get("op") == "region_event" and rl.get("toggle")]
    assert tog and sorted(tog[0]["toggle"][0]) == [5, 9], r.spec["always"]


def test_spec_abduction_recovers_permutation_cycle():
    """Zero-model recovery of a 3-STATE indicator: each crossing rotates a cell
    through colours 1->2->3->1. A toggle (k=2) cannot express it; abduction emits
    the cycle variant."""
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.spec_abduction import abduce_spec
    from ztare.worldmodel.spec_catalog import lower_spec
    truth, _ = lower_spec({
        "actions": {"0": [{"op": "translate_block", "match_colors": [7], "dy": 0,
                           "dx": 1, "require_dest_colors": [3], "fill_color": 3}],
                    "1": [{"op": "translate_block", "match_colors": [7], "dy": 0,
                           "dx": -1, "require_dest_colors": [3], "fill_color": 3}]},
        "always": [{"op": "region_event", "mover_colors": [7], "rect": [0, 2, 0, 2],
                    "edge": "exit", "writes": [[1, [[3, 0]]]], "cycle": [[1, 2, 3]]}]})
    g = ((3, 3, 7, 3, 3), (3, 3, 3, 3, 3), (3, 3, 3, 3, 3), (1, 3, 3, 3, 3))
    log = EpisodeLog()
    s = g
    for a in (0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1):
        s2 = truth(s, a, 0)
        log.append(s, a, s2, t=0)
        s = s2
    r = abduce_spec(log, 2)
    assert r.replay_ok and r.status == "spec_identified", r.detail
    cyc = [rl for rl in r.spec["always"]
           if rl.get("op") == "region_event" and rl.get("cycle")]
    assert cyc and len(cyc[0]["cycle"][0]) == 3, r.spec["always"]


def test_spec_when_region_and_when_phase_lower():
    """when_region gates a rule on an indicator region's step-start pattern
    (legal only while it holds X); when_phase is a periodic gate (blinker)."""
    from ztare.worldmodel.spec_catalog import lower_spec
    rstep, err = lower_spec({
        "actions": {"0": [{"op": "consume_extremal", "color": 11, "replacement": 3,
                           "axis": "row", "extreme": "min",
                           "when_region": [2, 0, 2, 0, [8]]}]}})
    assert rstep is not None, err
    assert rstep(((3, 3), (11, 11), (8, 3)), 0, 0)[1] == (3, 11)   # holds 8 -> fires
    assert rstep(((3, 3), (11, 11), (5, 3)), 0, 0)[1] == (11, 11)  # holds 5 -> pauses
    pstep, err2 = lower_spec({
        "actions": {"0": [{"op": "consume_extremal", "color": 11, "replacement": 3,
                           "axis": "row", "extreme": "min", "when_phase": [2, 0]}]}})
    assert pstep is not None, err2
    assert pstep(((11, 11),), 0, 0)[0] == (3, 11)     # t%2==0 fires
    assert pstep(((11, 11),), 0, 1)[0] == (11, 11)    # t%2==1 pauses
    bad, e3 = lower_spec({"actions": {"0": [{"op": "identity", "when_region": [0, 0, 1]}]}})
    assert bad is None and "when_region" in e3


def test_spec_abduction_recovers_region_gated_move():
    """A MOVE legal only while an indicator region holds a pattern (1b): under
    action 0 the mover translates only when a region-event write-target holds
    colour 8. Abduction selects the move, mines the indicator's region_event,
    then guards the move with when_region — provable only once the indicator
    exists. A global timer keeps refused frames non-trivial."""
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.spec_abduction import abduce_spec
    from ztare.worldmodel.spec_catalog import lower_spec
    truth, _ = lower_spec({
        "actions": {
            "0": [{"op": "translate_block", "match_colors": [7], "dy": 0, "dx": 1,
                   "require_dest_colors": [3], "fill_color": 3,
                   "when_region": [4, 0, 4, 0, [8]]}],
            "1": [{"op": "translate_block", "match_colors": [6], "dy": 0, "dx": 1,
                   "require_dest_colors": [3], "fill_color": 3}]},
        "always": [{"op": "consume_extremal", "color": 11, "replacement": 3,
                    "axis": "row", "extreme": "min"},
                   {"op": "region_event", "mover_colors": [6], "rect": [2, 0, 2, 0],
                    "edge": "exit", "writes": [[8, [[4, 0]]]]}]})

    def grid(seven, six, ind):
        g = [[3] * 5 for _ in range(5)]
        g[0][seven], g[2][six] = 7, 6
        g[3][0] = g[3][1] = g[3][2] = 11
        g[4][0] = ind
        return tuple(tuple(r) for r in g)
    log = EpisodeLog()
    t = 0
    for _ in range(3):                       # action 1: mover 6 crosses, writes indicator=8
        s = grid(1, 0, 3)
        log.append(s, 1, truth(s, 1, t), t=t)
        t += 1
    for _ in range(3):                       # action 0, indicator=3: move refused (timer ticks)
        s = grid(1, 3, 3)
        log.append(s, 0, truth(s, 0, t), t=t)
        t += 1
    for _ in range(3):                       # action 0, indicator=8: move legal
        s = grid(1, 3, 8)
        log.append(s, 0, truth(s, 0, t), t=t)
        t += 1
    r = abduce_spec(log, 2)
    assert r.replay_ok and r.status == "spec_identified", r.detail
    gated = [rl for rl in r.spec["actions"]["0"]
             if rl.get("op") == "translate_block" and rl.get("when_region")]
    assert gated and gated[0]["when_region"][-1] == [8], r.spec["actions"]["0"]


def test_spec_abduction_recovers_blinker_phase():
    """A BLINKER (1d): a mechanic that fires on a t-period no count/overlap guard
    can express. Colour 11 consumes every step; colour 12 consumes only on even
    t. Abduction learns the period from the fired-frame t-residues -> when_phase."""
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.spec_abduction import abduce_spec
    from ztare.worldmodel.spec_catalog import lower_spec
    truth, _ = lower_spec({
        "actions": {"0": [{"op": "identity"}]},
        "always": [{"op": "consume_extremal", "color": 11, "replacement": 3,
                    "axis": "row", "extreme": "min"},
                   {"op": "consume_extremal", "color": 12, "replacement": 3,
                    "axis": "row", "extreme": "min", "when_phase": [2, 0]}]})
    base = ((11, 11, 3), (12, 12, 3))
    log = EpisodeLog()
    for t in range(8):
        log.append(base, 0, truth(base, 0, t), t=t)
    r = abduce_spec(log, 1)
    assert r.replay_ok and r.status == "spec_identified", r.detail
    blink = [rl for rl in r.spec["always"]
             if rl.get("color") == 12 and rl.get("when_phase")]
    assert blink and blink[0]["when_phase"] == [2, 0], r.spec["always"]


def test_goal_abduction_depletion_config_predicate():
    """Depletion-config goals (theory-backed: completion = a flag configuration
    at resource exhaustion). The predicate compiles resource_zero + a mix of
    differs/matches-from-start and is true ONLY on the exact configuration."""
    from ztare.worldmodel.goal_abduction import (
        abduce_goal_candidates, predicate_from_spec)
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.common.abstraction_functor import Role

    start = ((3, 3, 3), (11, 11, 11))
    pspec = {"conjunction": [
        {"region": [0, 0, 0, 0], "differs_from_start": True},    # flag A must flip
        {"region": [0, 2, 0, 2], "differs_from_start": False},   # flag B must stay
        {"resource_zero": 11}]}                                  # timer exhausted
    goal = predicate_from_spec(pspec, start)
    assert not goal(start)                             # timer full, A unchanged
    assert goal(((8, 3, 3), (3, 3, 3)))                # A flipped, B kept, no 11
    assert not goal(((3, 3, 3), (3, 3, 3)))            # A unchanged
    assert not goal(((8, 3, 9), (3, 3, 3)))            # B changed -> violates matches
    assert not goal(((8, 3, 3), (11, 3, 3)))           # timer not exhausted

    # abduction emits depletion_config candidates from region-event indicators +
    # a depleting resource, in pre-success (no completion witnessed)
    spec = {"always": [
        {"op": "region_event", "mover_colors": [7], "rect": [0, 0, 0, 0],
         "edge": "exit", "writes": [[6, [[0, 0]]]]},
        {"op": "region_event", "mover_colors": [7], "rect": [0, 0, 0, 0],
         "edge": "exit", "writes": [[6, [[0, 2]]]]}]}
    log = EpisodeLog()
    log.append(((3, 3, 3), (11, 11, 11)), 0, ((6, 3, 3), (11, 11, 3)), t=0)
    log.append(((6, 3, 3), (11, 11, 3)), 0, ((6, 3, 3), (11, 3, 3)), t=1)
    log.append(((6, 3, 3), (11, 3, 3)), 0, ((6, 3, 3), (3, 3, 3)), t=2)
    roles = [Role("monotone_depleting", [11], "bar")]
    res = abduce_goal_candidates(log, spec, roles)
    assert res["mode"] == "pre_success", res
    dc = [c for c in res["candidates"] if c["kind"] == "depletion_config"]
    assert dc, res
    # every depletion-config predicate ends in a resource_zero clause
    assert all(any("resource_zero" in s for s in c["predicate_spec"]["conjunction"])
               for c in dc), dc


def test_prune_region_writes_drops_harmful_resource_write():
    """Post-closure prune: a firing region-event that ALSO writes floor over a
    resource-bar cell double-consumes the bar; the prune drops that write cell
    (strict wrong-cell improvement), handing the cell back to the consume rule."""
    from ztare.worldmodel.spec_abduction import _prune_region_writes
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.spec_catalog import lower_spec
    from ztare.worldmodel.gates import replay_consistency_gate
    truth, _ = lower_spec({
        "actions": {"0": [{"op": "translate_block", "match_colors": [9], "dy": 0,
                           "dx": 1, "require_dest_colors": [3], "fill_color": 3}]},
        "always": [{"op": "consume_extremal", "color": 11, "replacement": 3,
                    "axis": "row", "extreme": "min"}]})
    g = ((9, 3, 3, 3), (11, 11, 11, 3))
    log = EpisodeLog()
    s = g
    for t in range(3):
        s2 = truth(s, 0, t)
        log.append(s, 0, s2, t=t)
        s = s2
    spec = {"actions": {"0": [{"op": "translate_block", "match_colors": [9], "dy": 0,
                              "dx": 1, "require_dest_colors": [3], "fill_color": 3}]},
            "always": [{"op": "consume_extremal", "color": 11, "replacement": 3,
                        "axis": "row", "extreme": "min"},
                       {"op": "region_event", "mover_colors": [9], "rect": [0, 0, 0, 0],
                        "edge": "exit", "writes": [[3, [[1, 2]]]]}]}   # spurious bar write
    assert not replay_consistency_gate(lower_spec(spec)[0], log).ok
    pruned, step = _prune_region_writes(spec, log)
    assert replay_consistency_gate(step, log).ok               # over-consumption gone
    reg = [r for r in pruned["always"] if r["op"] == "region_event"]
    assert reg and reg[0]["writes"] == []                      # the bar write was dropped


def test_prune_region_writes_uses_exact_last_event_delta(monkeypatch):
    """The reducible case is scored from prefix/event deltas, not full replay."""
    import ztare.worldmodel.spec_abduction as SA
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.spec_catalog import lower_spec

    truth, _ = lower_spec({
        "actions": {"0": [{"op": "translate_block", "match_colors": [9], "dy": 0,
                           "dx": 1, "require_dest_colors": [3], "fill_color": 3}]},
        "always": [{"op": "consume_extremal", "color": 11, "replacement": 3,
                    "axis": "row", "extreme": "min"}]})
    log = EpisodeLog()
    s = ((9, 3, 3, 3), (11, 11, 11, 3))
    for t in range(3):
        s2 = truth(s, 0, t)
        log.append(s, 0, s2, t=t)
        s = s2
    spec = {"actions": {"0": [{"op": "translate_block", "match_colors": [9], "dy": 0,
                              "dx": 1, "require_dest_colors": [3], "fill_color": 3}]},
            "always": [{"op": "consume_extremal", "color": 11, "replacement": 3,
                        "axis": "row", "extreme": "min"},
                       {"op": "region_event", "mover_colors": [9], "rect": [0, 0, 0, 0],
                        "edge": "exit", "writes": [[3, [[1, 2]]]]}]}

    original = SA._wrong_cell_count
    calls = {"n": 0}

    def counted(step, log_arg, env, incumbent=None):
        calls["n"] += 1
        if incumbent is not None:
            raise AssertionError("last-event prune should not full-replay candidates")
        return original(step, log_arg, env, incumbent=incumbent)

    monkeypatch.setattr(SA, "_wrong_cell_count", counted)
    pruned, step = SA._prune_region_writes(spec, log)

    assert calls["n"] == 1
    assert step is not None
    assert pruned["always"][-1]["writes"] == []


def test_prune_region_writes_skips_uncertified_full_replay(monkeypatch):
    """The live hot path only runs certified cheap scorers; exhaustive fallback is opt-in."""
    import ztare.worldmodel.spec_abduction as SA
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.spec_catalog import lower_spec

    truth, _ = lower_spec({
        "actions": {"0": [{"op": "translate_block", "match_colors": [9], "dy": 0,
                           "dx": 1, "require_dest_colors": [3], "fill_color": 3}]},
        "always": [{"op": "consume_extremal", "color": 11, "replacement": 3,
                    "axis": "row", "extreme": "min"}]})
    log = EpisodeLog()
    s = ((9, 3, 3, 3), (11, 11, 11, 3))
    for t in range(3):
        s2 = truth(s, 0, t)
        log.append(s, 0, s2, t=t)
        s = s2
    spec = {"actions": {"0": [{"op": "translate_block", "match_colors": [9], "dy": 0,
                              "dx": 1, "require_dest_colors": [3], "fill_color": 3}]},
            "always": [{"op": "consume_extremal", "color": 11, "replacement": 3,
                        "axis": "row", "extreme": "min"},
                       {"op": "region_event", "mover_colors": [9], "rect": [0, 0, 0, 0],
                        "edge": "exit", "writes": [[3, [[1, 2]]]]},
                       {"op": "identity"}]}

    original = SA._wrong_cell_count
    calls = {"incumbent": 0}

    def counted(step, log_arg, env, incumbent=None):
        if incumbent is not None:
            calls["incumbent"] += 1
            raise AssertionError("uncertified prune candidate should be skipped")
        return original(step, log_arg, env, incumbent=incumbent)

    monkeypatch.delenv("ZTARE_PRUNE_REGION_FULL_FALLBACK", raising=False)
    monkeypatch.setattr(SA, "_wrong_cell_count", counted)
    pruned, _step = SA._prune_region_writes(spec, log)

    assert calls["incumbent"] == 0
    assert pruned["always"][1]["writes"] == [[3, [[1, 2]]]]


def test_seed_visited_unions_log_and_cache(tmp_path):
    """Visited seed is the single source of truth: the live-play cache UNION every
    abstract state in the evidence log (both transition endpoints). Pure helper."""
    import importlib.util
    from pathlib import Path
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.reachability import save_visited

    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "public" / "control" / "arc3_play_loop.py"
    spec = importlib.util.spec_from_file_location("arc3_play_loop", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    cache = tmp_path / "visited.jsonl"
    save_visited(cache, {frozenset({(9, 9, 1)})})
    log = EpisodeLog()
    log.append(((1, 0),), 0, ((0, 1),), t=0)
    abstract = lambda g: frozenset(  # noqa: E731
        (y, x, g[y][x]) for y in range(len(g)) for x in range(len(g[0])))
    store = mod._seed_visited(cache, log, abstract)
    assert frozenset({(9, 9, 1)}) in store             # cache preserved
    assert abstract(((1, 0),)) in store                # s seeded from evidence
    assert abstract(((0, 1),)) in store                # s_next seeded from evidence
    assert mod._seed_visited(cache, log, None) == {frozenset({(9, 9, 1)})}


def test_frontier_memory_reuses_only_exact_append_lineage(tmp_path):
    """A quotient image survives an append only when prior episode bytes are an
    exact prefix; mutating the prefix severs the cache lineage."""
    import importlib.util
    from pathlib import Path
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.reachability import save_visited

    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "public" / "control" / "arc3_play_loop.py"
    spec = importlib.util.spec_from_file_location("arc3_play_loop", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    project = tmp_path / "project"
    ep = project / "raw" / "episodes" / "episode_001.jsonl"
    ep.parent.mkdir(parents=True)
    log = EpisodeLog()
    log.append(((1, 0),), 0, ((0, 1),), t=0)
    log.write_jsonl(ep)

    legacy = project / "workspace" / "visited_signatures.jsonl"
    save_visited(legacy, {frozenset({("legacy",)})})

    _af, scoped_path, store = mod._frontier_memory(project)
    assert scoped_path.parent == project / "workspace" / "frontier"
    assert scoped_path.name.startswith("visited_")
    assert scoped_path != legacy
    assert frozenset({("legacy",)}) not in store

    current_key = frozenset({("current",)})
    save_visited(scoped_path, {current_key})
    _af2, same_path, same_store = mod._frontier_memory(project)
    assert same_path == scoped_path
    assert current_key in same_store

    log.append(((0, 1),), 0, ((0, 0),), t=1)
    log.write_jsonl(ep)
    _af3, next_path, next_store = mod._frontier_memory(project)
    assert next_path == scoped_path
    assert current_key in next_store
    receipt = json.loads((project / "workspace" / "latest_frontier_scope.json").read_text())
    assert receipt["inherited_rows"] == 1

    mutated = EpisodeLog()
    mutated.append(((9, 9),), 0, ((0, 1),), t=0)
    mutated.append(((0, 1),), 0, ((0, 0),), t=1)
    mutated.write_jsonl(ep)
    _af4, mutation_path, mutation_store = mod._frontier_memory(project)
    assert mutation_path != next_path
    assert current_key not in mutation_store
    receipt = json.loads((project / "workspace" / "latest_frontier_scope.json").read_text())
    assert receipt["inherited_rows"] == 0


def test_frontier_memory_reuses_same_epoch_append_lineage(tmp_path):
    """An active epoch keeps its visited quotient across a certified append.

    Global evidence-row counts cannot stand in for rows in the epoch-local
    frontier view.
    """
    import importlib.util
    from pathlib import Path
    from ztare.worldmodel.episode_log import EpisodeLog, Transition
    from ztare.worldmodel.reachability import save_visited
    from ztare.worldmodel.transition_identity import TransitionIdentity

    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "public" / "control" / "arc3_play_loop.py"
    spec = importlib.util.spec_from_file_location("arc3_play_loop_epoch", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    project = tmp_path / "project"
    episode = project / "raw" / "episodes" / "episode_001.jsonl"
    episode.parent.mkdir(parents=True)
    e1 = TransitionIdentity(
        kind="dynamics", authority="environment_adapter",
        source_epoch=1, target_epoch=1,
    )
    e2 = TransitionIdentity(
        kind="dynamics", authority="environment_adapter",
        source_epoch=2, target_epoch=2,
    )
    rows = EpisodeLog([
        Transition(0, ((1,),), 0, ((2,),), e1),
        Transition(1, ((2,),), 0, ((3,),), e2),
    ])
    rows.write_jsonl(episode)

    loaded = EpisodeLog.read_jsonl(episode)
    _af, visited_path, _store = mod._frontier_memory(
        project, loaded, source_epoch=2,
    )
    marker = frozenset({("same-epoch",)})
    save_visited(visited_path, {marker})

    loaded.append_jsonl(
        episode,
        [Transition(2, ((3,),), 0, ((4,),), e2)],
    )
    advanced = EpisodeLog.read_jsonl(episode)
    _af2, same_path, same_store = mod._frontier_memory(
        project, advanced, source_epoch=2,
    )

    assert same_path == visited_path
    assert marker in same_store
    receipt = json.loads(
        (project / "workspace" / "latest_frontier_scope.json").read_text()
    )
    assert receipt["evidence_rows"] == 3
    assert receipt["frontier_rows"] == 2
    assert receipt["inherited_rows"] == 1


def test_play_turn_reuses_one_evidence_induced_role_projection(tmp_path, monkeypatch):
    import importlib.util
    from pathlib import Path
    from ztare.worldmodel.episode_log import EpisodeLog
    import ztare.worldmodel.object_roles as object_roles

    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "public" / "control" / "arc3_play_loop.py"
    spec = importlib.util.spec_from_file_location("arc3_play_loop_role_cache", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    project = tmp_path / "project"
    episode = project / "raw" / "episodes" / "episode_001.jsonl"
    episode.parent.mkdir(parents=True)
    log = EpisodeLog()
    log.append(((1, 0),), 0, ((0, 1),), t=0)
    log.write_jsonl(episode)
    calls = 0
    original = object_roles.induce_roles

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(object_roles, "induce_roles", counted)
    mod._ROLE_STATE_CACHE.clear()
    mod._abstract_fn(project)
    mod._coverage_fn(project)
    mod._resource_colors(project)
    assert calls == 1


def test_governed_play_uses_persistent_frontier_memory():
    """Governed live play must use the same quotient-frontier memory as sprint.

    Otherwise a gate-passing model with no goal cue can keep rewalking already
    witnessed abstract states and report zero information gain.
    """
    source = Path("scripts/public/control/arc3_play_loop.py").read_text(
        encoding="utf-8"
    )
    governed = source[source.index("===== CYCLE {cyc}: live play") :]
    assert "af, visited_path, visited_store = _frontier_memory(" in governed
    assert "source_epoch=active_epoch" in governed
    assert "visited_store=visited_store" in governed
    assert "visited_path=visited_path" in governed


def test_determinism_check_flags_stochastic_and_passes_deterministic():
    """Same (s, a, phase) -> different s_next is named, not silently churned."""
    from ztare.worldmodel.gates import determinism_check
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.grid_dsl import grid_from_lists
    a = grid_from_lists([[1, 0]]); b = grid_from_lists([[0, 1]]); c = grid_from_lists([[1, 1]])
    det = EpisodeLog(); det.append(a, 0, b, t=0); det.append(b, 0, a, t=1)
    assert determinism_check(det).ok
    sto = EpisodeLog(); sto.append(a, 0, b, t=0); sto.append(a, 0, c, t=6)  # same phase, differs
    r = determinism_check(sto)
    assert not r.ok and "NON-DETERMINISTIC" in r.detail

def test_spec_when_effect_couples_rule_to_prior_firing():
    """when_effect [ref_id, pol] fires a rule iff the id'd rule DID (True) /
    DIDN'T (False) change the grid earlier this step. ls20 timer coupling: the
    mover translate carries an id; the timer consume ticks only when the mover
    moved (True) — a blocked-mover step (refusal) pauses the timer. Malformed
    fail-closes rather than lowering wrong."""
    from ztare.worldmodel.spec_catalog import lower_spec
    step, err = lower_spec({
        "actions": {"0": [{"op": "translate_block", "id": "mover", "match_colors": [9],
                           "dy": 0, "dx": 1, "require_dest_colors": [3], "fill_color": 3}]},
        "always": [{"op": "consume_extremal", "color": 11, "replacement": 3,
                    "axis": "row", "extreme": "min", "when_effect": ["mover", True]}]})
    assert step is not None, err
    # mover free -> it moves AND the timer ticks (leftmost 11 -> 3)
    assert step(((3, 9, 3, 3), (11, 11, 11, 3)), 0, 0) == ((3, 3, 9, 3), (3, 11, 11, 3))
    # mover blocked by wall 7 at the destination -> refuses -> timer PAUSES (full no-op)
    g_block = ((3, 3, 9, 7), (11, 11, 11, 3))
    assert step(g_block, 0, 0) == g_block
    # polarity False inverts: the timer ticks iff the mover did NOT move
    fstep, _ = lower_spec({
        "actions": {"0": [{"op": "translate_block", "id": "mover", "match_colors": [9],
                           "dy": 0, "dx": 1, "require_dest_colors": [3], "fill_color": 3}]},
        "always": [{"op": "consume_extremal", "color": 11, "replacement": 3,
                    "axis": "row", "extreme": "min", "when_effect": ["mover", False]}]})
    assert fstep(((3, 9, 3, 3), (11, 11, 11, 3)), 0, 0) == ((3, 3, 9, 3), (11, 11, 11, 3))
    bad, err2 = lower_spec({"actions": {"0": [{"op": "identity", "when_effect": ["x"]}]}})
    assert bad is None and "when_effect" in err2


def test_implement_and_validate_accept_reject_and_persists(tmp_path):
    """The kernel contract runs a leaf then a harness and disposes the card:
    accept -> receipt, reject -> counterexample. Both dispositions upsert into
    the ledger by family sha (one row per family) and close the card."""
    from ztare.common.operator_proposal_contract import (
        implement_and_validate, is_open, operator_proposal_card, open_cards,
    )
    card = operator_proposal_card(
        failure_family="rule-coupling-A", evidence_indices=[0, 1],
        spatial_footprint={"bbox": [0, 0, 1, 1]},
        why_existing_ops_fail={"consume_extremal": "over-fires; pause not positional"},
        proposed_operator_sketch="when_effect [mover, false]",
        acceptance_test="planted synthetic + real strict improvement")
    ledger = tmp_path / "workspace" / "operator_proposals.jsonl"

    ok_harness = lambda art: {"accepted": True, "receipt": f"receipt::{art['ok']}",
                              "counterexample": None}
    accepted = implement_and_validate(card, lambda c: {"ok": 1}, ok_harness, ledger=ledger)
    assert not is_open(accepted) and accepted["disposition"] == "accepted"
    assert accepted["receipt"] == "receipt::1"

    bad_harness = lambda art: {"accepted": False, "receipt": "",
                               "counterexample": "real did not improve"}
    rejected = implement_and_validate(card, lambda c: {"ok": 0}, bad_harness, ledger=ledger)
    assert not is_open(rejected) and rejected["disposition"] == "rejected"
    assert rejected["counterexample"] == "real did not improve"
    # upsert-by-sha: one row for this family, carrying the latest (rejected) disposition
    lines = ledger.read_text().splitlines()
    assert len(lines) == 1, lines
    assert open_cards(ledger) == []           # a closed card leaves the open set empty

def test_spec_when_dest_relational_destination_gate():
    """when_dest [ref_id, colors, flag]: a rule fires iff the CURRENT action's
    id'd translate has a destination cell (components displaced by that rule's
    own dy/dx) holding one of the colors == flag. Object-anchored: same guard,
    any mover position. A same-palette single-color decoration (a lock icon) is
    not a qualifying component and never trips it. Malformed fail-closes; Lean
    lowering emits the destHolds parity guard."""
    from ztare.worldmodel.spec_catalog import lower_spec
    from ztare.worldmodel.spec_lean import spec_to_lean_step
    spec = {
        "actions": {"0": [{"op": "translate_block", "id": "m", "match_colors": [9, 12],
                           "dy": 0, "dx": 1, "require_dest_colors": [0, 3],
                           "fill_color": 3, "component_min_colors": 2}],
                    "1": [{"op": "identity"}]},
        "always": [{"op": "consume_extremal", "color": 11, "replacement": 3,
                    "axis": "row", "extreme": "min", "when_dest": ["m", [0], False]}]}
    step, err = lower_spec(spec)
    assert step is not None, err
    # floor ahead -> mover moves AND the timer ticks
    g = ((3, 9, 12, 3, 3), (11, 11, 11, 3, 3))
    assert step(g, 0, 0) == ((3, 3, 9, 12, 3), (3, 11, 11, 3, 3))
    # void ahead -> mover still moves (0 is passable) but the timer PAUSES
    g2 = ((3, 9, 12, 0, 3), (11, 11, 11, 3, 3))
    assert step(g2, 0, 0) == ((3, 3, 9, 12, 3), (11, 11, 11, 3, 3))
    # action with no referenced translate -> predicate False -> flag False fires
    assert step(g2, 1, 0)[1] == (3, 11, 11, 3, 3)
    # single-color same-palette decoration is not a qualifying component
    g3 = ((3, 9, 12, 3, 3), (9, 3, 3, 3, 0), (11, 11, 11, 3, 3))
    assert step(g3, 0, 0)[2] == (3, 11, 11, 3, 3)
    bad, err2 = lower_spec({"actions": {"0": [{"op": "identity", "when_dest": ["m", [0]]}]}})
    assert bad is None and "when_dest" in err2
    assert "destHolds s [9, 12]" in spec_to_lean_step(spec)


def test_spec_abduction_recovers_dest_coupling():
    """Zero-model recovery of a PLANTED transit-freeze: a timer that pauses only
    while the mover's destination holds void, at TWO different void gaps so no
    absolute rect or phase separates the split. The refine learns the guard by
    set separation (colors present in every paused dest, absent from every fired
    dest) and the post-refine broaden retry closes the coupled move refusals."""
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.spec_abduction import abduce_spec
    from ztare.worldmodel.spec_catalog import lower_spec
    truth, _ = lower_spec({
        "actions": {"0": [{"op": "translate_block", "id": "m", "match_colors": [9, 12],
                           "dy": 0, "dx": 1, "require_dest_colors": [0, 3],
                           "fill_color": 3, "component_min_colors": 2}],
                    "1": [{"op": "identity"}]},
        "always": [{"op": "consume_extremal", "color": 11, "replacement": 3,
                    "axis": "row", "extreme": "min", "when_dest": ["m", [0], False]}]})
    g = ((7, 9, 12, 0, 3, 3, 0, 3, 3, 3, 3, 7),
         (11, 11, 11, 11, 11, 11, 11, 11, 11, 3, 3, 3))
    log = EpisodeLog()
    s = g
    for a in (0, 1, 0, 0, 1, 0, 0, 0, 1, 0):
        s2 = truth(s, a, 0)
        log.append(s, a, s2, t=0)
        s = s2

    def mism(res):
        st = res.step_fn
        return sum(1 for tr in log if st(tr.s, tr.a, tr.t) != tr.s_next)
    base = abduce_spec(log, 2, _effect_refine=False)
    full = abduce_spec(log, 2, _effect_refine=True)
    assert mism(base) > 0, "planted transit-freeze must leave a residual before the refine"
    assert full.replay_ok and mism(full) == 0, full.detail
    wd = [r for r in full.spec["always"] if "when_dest" in r]
    assert wd and wd[0]["when_dest"][1] == [0] and wd[0]["when_dest"][2] is False, full.spec


def test_spec_abduction_recovers_multi_content_dest_pause():
    """Zero-model recovery of a timer paused by TWO distinct destination contents
    at once: the mover's destination holding void (0, a passable dock the mover
    slides onto) OR a blocking sprite (6, which refuses the move). The two paused-
    dest colour-sets are DISJOINT, so their intersection is empty and a single
    shared separating colour does not exist — the ls20 timer's real shape, where a
    dock-transit freeze and a sprite-blocked freeze coincide. The sound separator
    is the paused-union minus the fired-union, gated as a MULTI-colour when_dest;
    a single colour cannot close it. Guards spec_abduction._dest_guard_refine."""
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.spec_abduction import abduce_spec
    from ztare.worldmodel.spec_catalog import lower_spec
    truth, _ = lower_spec({
        "actions": {"0": [{"op": "translate_block", "id": "m", "match_colors": [9, 12],
                           "dy": 0, "dx": 1, "require_dest_colors": [0, 3],
                           "fill_color": 3, "component_min_colors": 2}],
                    "1": [{"op": "identity"}]},
        "always": [{"op": "consume_extremal", "color": 11, "replacement": 3,
                    "axis": "row", "extreme": "min", "when_dest": ["m", [0, 6], False]}]})
    g = ((9, 12, 0, 3, 0, 3, 3, 6, 3, 3, 3, 3, 3, 7),
         (11, 11, 11, 11, 11, 11, 11, 11, 3, 3, 3, 3, 3, 3),
         (11, 11, 11, 11, 11, 11, 11, 11, 3, 3, 3, 3, 3, 3))
    log = EpisodeLog()
    s = g
    # real (advancing) t so the sprite-blocked full-no-op frames read as blocked
    # moves the law must predict, not environment no-ops the classifier excuses
    for i, a in enumerate([0, 1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0]):
        s2 = truth(s, a, i)
        log.append(s, a, s2, t=i)
        s = s2

    def mism(res, colors=None):
        sp = res.spec
        if colors is not None:
            import copy
            sp = copy.deepcopy(sp)
            for r in sp["always"]:
                if "when_dest" in r:
                    r["when_dest"] = [r["when_dest"][0], colors, r["when_dest"][2]]
        st, _e = lower_spec(sp)
        return sum(1 for tr in log if st(tr.s, tr.a, tr.t) != tr.s_next)

    full = abduce_spec(log, 2, _effect_refine=True)
    assert full.replay_ok and mism(full) == 0, full.detail
    wd = [r for r in full.spec["always"] if "when_dest" in r]
    assert wd, full.spec
    assert set(wd[0]["when_dest"][1]) >= {0, 6} and wd[0]["when_dest"][2] is False, full.spec
    # necessity: neither separating colour alone closes it (a single-colour /
    # intersection-based separator would leave a residual)
    assert mism(full, [0]) > 0 and mism(full, [6]) > 0, "multi-colour guard must be needed"

def test_excused_but_diverging_fires_and_silent():
    """Detector 1: fires when a diverged row is 0-diff (excusal hides physics);
    silent when divergence falls on a normal (non-zero-diff) row."""
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.machinery_contradictions import excused_but_diverging

    g = ((1, 0), (0, 2))
    g2 = ((0, 1), (2, 0))
    log = EpisodeLog()
    # row 0: 0-diff, t=0; row 1: t=0 (non-advancing) → row 0 is env frame
    # (env_frame_indices: 0-diff AND t-anomaly because rows[1].t <= rows[0].t)
    log.append(g, 0, g, t=0)
    log.append(g, 1, g2, t=0)

    # planted contradiction: diverged on the 0-diff row → fires
    cards = excused_but_diverging(log, {0})
    assert cards, "detector must fire on 0-diff diverged row"
    assert cards[0]["failure_family"] == "excusal:hides:physics:diverged-frames"
    assert cards[0]["certifier_touched"] is True  # S1/I2: conductor disposition required
    assert "excusal is hiding physics" in cards[0]["why_existing_ops_fail"]["machinery"]

    # clean: divergence on a normal row only → silent
    assert not excused_but_diverging(log, {1}), "must be silent when diverged row is non-zero-diff"


def test_absorb_diverge_spiral_fires_and_silent():
    """Detector 2: fires on >=3 consecutive model_diverged depth<=2 with
    growing log; silent when the spiral has fewer than 3 rounds."""
    from ztare.worldmodel.machinery_contradictions import absorb_diverge_spiral

    # planted contradiction: 3 consecutive model_diverged, depth=1, log grew
    rounds_bad = [
        {"round": 1, "pursuit": "model_diverged", "steps": 1, "log": 15},
        {"round": 2, "pursuit": "model_diverged", "steps": 1, "log": 17},
        {"round": 3, "pursuit": "model_diverged", "steps": 1, "log": 19},
    ]
    cards = absorb_diverge_spiral(rounds_bad)
    assert cards, "detector must fire on 3-round model_diverged spiral"
    assert cards[0]["failure_family"] == "absorb-diverge:spiral:depth<=2"
    assert cards[0]["certifier_touched"] is False  # targets law, not certifier

    # clean: spiral broken by a non-diverged round
    rounds_ok = [
        {"round": 1, "pursuit": "model_diverged", "steps": 1, "log": 15},
        {"round": 2, "pursuit": "model_diverged", "steps": 1, "log": 17},
        {"round": 3, "pursuit": "goal_reached",   "steps": 8, "log": 19},
    ]
    assert not absorb_diverge_spiral(rounds_ok), "must be silent when spiral is broken"


def test_terminal_verifier_edge_model_mismatch_fires_and_silent():
    """A scored edge that refutes the transition law becomes a refinement card;
    an ordinary scored edge stays silent."""
    from ztare.worldmodel.machinery_contradictions import (
        terminal_verifier_edge_model_mismatch)

    cards = terminal_verifier_edge_model_mismatch([
        {"round": 2, "pursuit": "goal_reached", "terminal_verifier_model_mismatch": True,
         "terminal_witness_sha": "abc"},
        {"round": 3, "pursuit": "goal_reached", "terminal_verifier_model_mismatch": True,
         "terminal_witness_sha": "abc"},
    ])
    assert cards
    assert cards[0]["failure_family"] == "terminal-verifier-edge:refines:transition-law"
    assert cards[0]["certifier_touched"] is False
    assert cards[0]["spatial_footprint"]["terminal_verifier_mismatch_edges"] == 2
    assert cards[0]["spatial_footprint"]["terminal_witness_classes"] == 1

    assert not terminal_verifier_edge_model_mismatch([
        {"round": 2, "pursuit": "goal_reached", "terminal_verifier_model_mismatch": False},
    ])
    wrapped = terminal_verifier_edge_model_mismatch([
        {"round": 4, "pursuit": "multilife", "transition_model_mismatch": True,
         "terminal_witness_sha": "wrapped"},
    ])
    assert wrapped
    assert wrapped[0]["spatial_footprint"]["terminal_witness_shas"] == ["wrapped"]


def test_transition_mismatch_card_is_invariant_to_enclosing_status_label():
    from ztare.worldmodel.machinery_contradictions import terminal_verifier_edge_model_mismatch

    families = set()
    witness_counts = []
    for label in ["goal_reached", "multilife", "model_diverged", "advice_boundary"]:
        cards = terminal_verifier_edge_model_mismatch([
            {
                "round": 7,
                "pursuit": label,
                "transition_model_mismatch": True,
                "terminal_witness_sha": "same-edge",
            }
        ])
        assert len(cards) == 1
        families.add(cards[0]["failure_family"])
        witness_counts.append(cards[0]["spatial_footprint"]["terminal_witness_classes"])

    assert families == {"terminal-verifier-edge:refines:transition-law"}
    assert witness_counts == [1, 1, 1, 1]
    assert not terminal_verifier_edge_model_mismatch([
        {"round": 7, "pursuit": "model_diverged", "transition_model_mismatch": False}
    ])


def test_visible_holdout_split_fires_and_silent():
    """Detector 3: fires when visible passes but holdout regressed; silent
    when holdout does not regress."""
    from ztare.worldmodel.machinery_contradictions import visible_holdout_split

    # planted contradiction: visible ok, holdout depth dropped
    cards = visible_holdout_split(visible_ok=True, holdout_depth=3,
                                  holdout_len=10, prev_holdout_depth=7)
    assert cards, "detector must fire on visible-ok + holdout regression"
    assert cards[0]["failure_family"] == "overfit:visible:holdout-regressed"
    assert cards[0]["certifier_touched"] is True  # targets selection arbiter

    # clean: holdout did not regress
    assert not visible_holdout_split(visible_ok=True, holdout_depth=8,
                                     holdout_len=10, prev_holdout_depth=7)


def test_full_survivor_hidden_from_prompt_fires_and_silent():
    """Detector 4: fires when deterministic candidate memory has a full
    survivor but prompt routing omits or demotes it; silent when the prompt
    surfaces it as the deterministic baseline."""
    from ztare.worldmodel.machinery_contradictions import full_survivor_hidden_from_prompt

    records = [
        {
            "source_type": "full_survivor",
            "submission": "workspace/winner.py",
            "sha": "abc123",
            "gate_score": 1.0,
            "visible_exact_rows": 1023,
            "holdout_depth": 10,
            "summary": "bridge-gated motion",
        },
        {
            "source_type": "deterministic_near_miss",
            "submission": "workspace/near.py",
            "sha": "def456",
            "visible_exact_rows": 923,
            "holdout_depth": 0,
        },
    ]

    cards = full_survivor_hidden_from_prompt(records, "### Mandatory Patch Base\nnear.py")
    assert cards, "detector must fire when a weaker patch base demotes a full survivor"
    assert cards[0]["failure_family"] == "briefing:full-survivor:hidden-or-demoted"
    assert cards[0]["certifier_touched"] is False

    prompt = (
        "## Deterministic Candidate Memory\n"
        "BEST FULL SURVIVOR abc123 workspace/winner.py\n"
        "NEAR-MISS SURVIVORS workspace/near.py\n"
    )
    assert not full_survivor_hidden_from_prompt(records, prompt)


def test_authority_artifact_demoted_in_prompt_is_generic():
    """Generic authority-routing detector: not tied to ARC candidate memory."""
    from ztare.worldmodel.machinery_contradictions import (
        authority_artifact_demoted_in_prompt,
    )

    records = [{
        "authority_rank": 10,
        "path": "proofs/champion.lean",
        "sha": "proofabc",
        "summary": "compiled proof artifact",
    }]
    cards = authority_artifact_demoted_in_prompt(
        authority_records=records,
        prompt_text="### Mandatory Patch Base\nold prose",
        authority_label="compiled_proof_artifact",
        demotion_markers=["Mandatory Patch Base"],
    )

    assert cards
    assert cards[0]["failure_family"] == "briefing:authority-artifact:hidden-or-demoted"
    assert cards[0]["spatial_footprint"]["authority_label"] == "compiled_proof_artifact"
    assert cards[0]["certifier_touched"] is False

    clean_prompt = "Use proofs/champion.lean sha proofabc as the baseline."
    assert not authority_artifact_demoted_in_prompt(
        authority_records=records,
        prompt_text=clean_prompt,
        authority_label="compiled_proof_artifact",
        demotion_markers=["Mandatory Patch Base"],
    )


def test_detect_and_card_dedup_and_empty(tmp_path):
    """detect_and_card: dedup on second write; returns 0 on empty input."""
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.machinery_contradictions import detect_and_card

    log = EpisodeLog()

    # empty: no log rows, no rounds → 0 cards
    assert detect_and_card(tmp_path, log, []) == 0

    # plant spiral contradiction → cards written on first call
    rounds = [
        {"round": 1, "pursuit": "model_diverged", "steps": 1, "log": 15},
        {"round": 2, "pursuit": "model_diverged", "steps": 1, "log": 17},
        {"round": 3, "pursuit": "model_diverged", "steps": 1, "log": 19},
    ]
    c1 = detect_and_card(tmp_path, log, rounds)
    assert c1 > 0, "first call must write cards"
    # second call with identical inputs → deduped, nothing new written
    c2 = detect_and_card(tmp_path, log, rounds)
    assert c2 == 0, "second call must be deduped to 0"


# ── GP-250: warm start, unified write learner, guard conjunction, episode crossing ──

def test_spec_abduction_warm_start_returns_prior_and_seeds():
    """CEGIS warm start: a prior champion that still replays the log is returned
    immediately (receipt 'warm', byte-identical spec) without the full search; a
    STALE prior (wrong displacement) falls through to the full search, recovers
    the true law, and is NOT returned as-is."""
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.spec_abduction import abduce_spec
    from ztare.worldmodel.spec_catalog import lower_spec
    truth, _ = lower_spec({"actions": {"0": [{"op": "translate_block", "match_colors": [9],
                           "dy": 0, "dx": 1, "require_dest_colors": [3], "fill_color": 3}],
                           "1": [{"op": "identity"}]}})
    log = EpisodeLog()
    s = ((3, 9, 3, 3, 3), (3, 3, 3, 3, 3))
    for a in (0, 0, 1, 0):
        s2 = truth(s, a, 0)
        log.append(s, a, s2, t=0)
        s = s2
    cold = abduce_spec(log, 2)
    assert cold.replay_ok and cold.spec is not None
    warm = abduce_spec(log, 2, prior_spec=cold.spec)
    assert warm.detail.startswith("warm"), warm.detail
    assert warm.replay_ok and warm.spec == cold.spec
    stale = {"actions": {"0": [{"op": "translate_block", "match_colors": [9], "dy": 0,
                               "dx": -1, "require_dest_colors": [3], "fill_color": 3}],
                         "1": [{"op": "identity"}]}, "always": []}
    fell = abduce_spec(log, 2, prior_spec=stale)
    assert not fell.detail.startswith("warm")
    assert fell.replay_ok and fell.spec != stale


def test_spec_abduction_warm_only_defers_full_reidentification():
    """Checkpoint callers can ask only the champion-first question: if the
    standing prior is refuted, return a bounded receipt instead of running the
    full miner and recovering a different law."""
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.spec_abduction import abduce_spec
    from ztare.worldmodel.spec_catalog import lower_spec

    truth, _ = lower_spec({"actions": {"0": [{"op": "translate_block", "match_colors": [9],
                           "dy": 0, "dx": 1, "require_dest_colors": [3], "fill_color": 3}],
                           "1": [{"op": "identity"}]}})
    log = EpisodeLog()
    s = ((3, 9, 3, 3, 3),)
    for a in (0, 0, 1):
        s2 = truth(s, a, 0)
        log.append(s, a, s2, t=0)
        s = s2

    stale = {"actions": {"0": [{"op": "translate_block", "match_colors": [9],
                               "dy": 0, "dx": -1, "require_dest_colors": [3],
                               "fill_color": 3}],
                         "1": [{"op": "identity"}]}, "always": []}
    bounded = abduce_spec(log, 2, prior_spec=stale, warm_only=True)
    assert bounded.status == "prior_refuted"
    assert bounded.replay_ok is False
    assert bounded.spec == stale
    assert bounded.detail.startswith("warm_only")


def test_spec_abduction_stale_prior_seeds_whole_incumbent():
    src = Path("src/ztare/worldmodel/spec_abduction.py").read_text()
    needle = "best_bad = pbad"
    assert needle in src
    window = src[src.index("best_spec, best_step, best_bad, best_rules"):src.index(
        "tried = 0"
    )]
    assert "lower_spec(prior_spec)" in window
    assert "best_spec, best_step = prior_spec, pstep" in window
    assert "spec_description_length(prior_spec)" in window


def test_spec_abduction_does_not_remine_region_events_from_prior_receipt():
    src = Path("src/ztare/worldmodel/spec_abduction.py").read_text()
    assert "prior_region_receipt" in src
    window = src[src.index("prior_region_receipt ="):src.index(
        "# ---- ACTION-SCOPING"
    )]
    assert 'r.get("op") == "region_event"' in window
    assert "if best_spec is not None and not prior_region_receipt:" in window
    assert "run_refinement_ladder" in src[src.index("# ---- ACTION-SCOPING"):]


def test_env_frame_indices_memoizes_append_only_log_snapshot(monkeypatch):
    import ztare.worldmodel.gates as gates
    from ztare.worldmodel.episode_log import EpisodeLog

    log = EpisodeLog()
    log.append(((1, 1),), 0, ((1, 0),), t=0)
    log.append(((1, 0),), 0, ((1, 1),), t=1)
    gates._ENV_FRAME_CACHE.clear()
    calls = {"n": 0}
    original = gates._color_counts

    def counted(grid):
        calls["n"] += 1
        return original(grid)

    monkeypatch.setattr(gates, "_color_counts", counted)
    first = gates.env_frame_indices(log)
    n = calls["n"]
    second = gates.env_frame_indices(log)
    assert second == first
    assert calls["n"] == n


def test_display_rung_uses_residual_topology_not_consume_vocabulary():
    src = Path("src/ztare/worldmodel/refinement_ladder.py").read_text()
    display_window = src[src.index('Rung("derived_display_refine"'):src.index(
        "_wrap_refine(\"_derived_display_refine\")"
    )]
    assert "compact_recurrent_residual" in display_window
    assert "not sig[\"has_consume\"]" not in display_window


def test_display_source_support_reuses_row_diff_cache(monkeypatch):
    import ztare.worldmodel.spec_abduction as SA
    from ztare.worldmodel.episode_log import EpisodeLog

    log = EpisodeLog()
    log.append(((1, 0, 0), (0, 0, 0)), 0, ((0, 1, 2), (0, 0, 0)), t=0)
    rows = list(log)
    cache = {}
    calls = {"n": 0}
    original = SA._diff_cell_set

    def counted(a, b):
        calls["n"] += 1
        return original(a, b)

    monkeypatch.setattr(SA, "_diff_cell_set", counted)
    source_a = ((1,), (0, 0, 0, 1), "enter", None, None, None, None, None)
    source_b = ((2,), (0, 2, 0, 2), "enter", None, None, None, None, None)
    SA._display_source_support(rows, set(), source_a, cache)
    first = calls["n"]
    SA._display_source_support(rows, set(), source_b, cache)
    assert first == 1
    assert calls["n"] == first


def test_unified_write_learner_fits_all_three_families():
    """The unified region-write learner classifies by consistency + MDL: constant
    -> fixed write, involution -> toggle, permutation -> cycle, inconsistent ->
    None (card). Built from the GLOBAL colour map, so it is robust to which cell
    witnessed which phase; a per-cell constant stays a fixed write (MDL-simplest)."""
    from ztare.worldmodel.spec_abduction import _fit_write_function
    # CONSTANT -> fixed write
    ev = _fit_write_function([0, 0, 4, 1], {(4, 0): [(3, 5), (3, 5)], (4, 1): [(3, 5)]}, [9, 12])
    assert ev.get("toggle") is None and ev.get("cycle") is None
    assert ev["writes"] == [[5, [[4, 0], [4, 1]]]]
    # INVOLUTION (both phases witnessed at cells) -> toggle
    ev = _fit_write_function([0, 0, 4, 1], {(4, 0): [(5, 9), (9, 5)], (4, 1): [(9, 5)]}, [9, 12])
    assert ev["toggle"] == [[5, 9]]
    # PERMUTATION (3-cycle) -> cycle
    ev = _fit_write_function([0, 0, 4, 0], {(4, 0): [(1, 2), (2, 3), (3, 1)]}, [9, 12])
    assert ev["cycle"] == [[1, 2, 3]]
    # NONE (a -> two different targets) -> no law, leave for a card
    assert _fit_write_function([0, 0, 4, 0], {(4, 0): [(5, 9), (5, 7)]}, [9, 12]) is None
    # per-cell constant (each cell only one phase) stays a FIXED write, not a toggle
    cp = {(4, i): [(5, 9)] for i in range(4)}
    cp.update({(4, i): [(9, 5)] for i in range(4, 8)})
    ev = _fit_write_function([0, 0, 4, 7], cp, [9, 12])
    assert ev.get("toggle") is None and {w[0] for w in ev["writes"]} == {5, 9}


def test_spec_abduction_recovers_hud_phase_inversion():
    """Zero-model recovery of an 8-cell HUD that PHASE-INVERTS {5,9} on each
    crossing (both phases in evidence). A fixed write is wrong on half the
    crossings; the unified write learner fits the involution and attaches a toggle
    over all 8 cells. Replay exact (the real-log t=8 phase-inversion class)."""
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.spec_abduction import abduce_spec
    from ztare.worldmodel.spec_catalog import lower_spec
    hud = [[3, 0], [3, 1], [3, 2], [3, 3], [4, 0], [4, 1], [4, 2], [4, 3]]
    truth, _ = lower_spec({
        "actions": {"0": [{"op": "translate_block", "match_colors": [7], "dy": 0,
                           "dx": 1, "require_dest_colors": [3], "fill_color": 3}],
                    "1": [{"op": "translate_block", "match_colors": [7], "dy": 0,
                           "dx": -1, "require_dest_colors": [3], "fill_color": 3}]},
        "always": [{"op": "region_event", "mover_colors": [7], "rect": [0, 2, 0, 2],
                    "edge": "exit", "writes": [[9, hud]], "toggle": [[5, 9]]}]})
    g = ((3, 3, 7, 3, 3), (3, 3, 3, 3, 3), (3, 3, 3, 3, 3),
         (5, 9, 5, 9, 3), (9, 5, 9, 5, 3))
    log = EpisodeLog()
    s = g
    for a in (0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1):
        s2 = truth(s, a, 0)
        log.append(s, a, s2, t=0)
        s = s2
    r = abduce_spec(log, 2)
    assert r.replay_ok, r.detail
    tog = [rl for rl in r.spec["always"]
           if rl.get("op") == "region_event" and rl.get("toggle")]
    assert tog and sorted(tog[0]["toggle"][0]) == [5, 9]
    assert len(tog[0]["writes"][0][1]) == 8, "toggle must cover all 8 HUD cells"


def test_region_event_multi_approach_checkpoint_dest_anchored():
    """The real-log HUD-latch configuration: a spread HUD (two column groups)
    phase-inverts {5,9} when the mover REACHES a fixed checkpoint — reached from
    two DIRECTIONS (a lateral and a vertical move). Source-anchored (edge=exit)
    mining splits the one write across two docks by approach direction — one real,
    one a corridor the mover also traverses on non-crossing moves, so it over-
    fires and is rejected, leaving the crossings unexplained. Dest-anchored
    (edge=enter) mining converges every approach onto the one checkpoint and pools
    both phases into an involution toggle that closes them all."""
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel import spec_abduction as SA
    from ztare.worldmodel.spec_catalog import lower_spec
    hud = [[0, 0], [0, 1], [0, 6], [0, 7]]           # two spread groups
    truth, _ = lower_spec({
        "actions": {"0": [{"op": "translate_block", "match_colors": [7], "dy": -1,
                           "dx": 0, "require_dest_colors": [3], "fill_color": 3}],
                    "1": [{"op": "translate_block", "match_colors": [7], "dy": 0,
                           "dx": -1, "require_dest_colors": [3], "fill_color": 3}]},
        "always": [{"op": "region_event", "mover_colors": [7], "rect": [3, 3, 3, 3],
                    "edge": "enter", "writes": [[9, hud]], "toggle": [[5, 9]]}]})

    def grid(mover, phase):
        g = [[3] * 8 for _ in range(6)]
        left, right = (5, 9) if phase == "A" else (9, 5)
        g[0][0] = g[0][1] = left
        g[0][6] = g[0][7] = right
        g[mover[0]][mover[1]] = 7
        return tuple(tuple(r) for r in g)

    # crossings reach checkpoint (3,3) from BELOW (a=0) and the RIGHT (a=1), both
    # phases; decoys leave the same source cells WITHOUT entering the checkpoint
    cross = [((4, 3), 0, "A"), ((3, 4), 1, "B"), ((4, 3), 0, "A"),
             ((3, 4), 1, "B"), ((4, 3), 0, "B"), ((3, 4), 1, "A")]
    decoy = [((4, 3), 1, "A"), ((3, 4), 0, "A"), ((5, 0), 0, "A"), ((5, 7), 1, "B")]
    log = EpisodeLog()
    for mover, a, ph in cross + decoy:
        s = grid(mover, ph)
        log.append(s, a, truth(s, a, 0), t=0)

    move = {"actions": {"0": [{"op": "translate_block", "match_colors": [7], "dy": -1,
                              "dx": 0, "require_dest_colors": [3], "fill_color": 3}],
                        "1": [{"op": "translate_block", "match_colors": [7], "dy": 0,
                              "dx": -1, "require_dest_colors": [3], "fill_color": 3}]},
            "always": []}
    base, _ = lower_spec(move)
    events = SA._abduce_region_events(base, log, [7], [])

    def _mismatches(always):
        st, _ = lower_spec({"actions": move["actions"], "always": always})
        return [i for i, tr in enumerate(log) if st(tr.s, tr.a, tr.t) != tr.s_next]

    exit_only = [e for e in events if e.get("edge") == "exit"]
    assert _mismatches(exit_only), "exit-anchoring alone must leave the crossings unexplained"

    enter_toggle = [e for e in events if e.get("edge") == "enter" and e.get("toggle")]
    assert enter_toggle, "dest-anchoring must mine an involution toggle at the checkpoint"
    ev = enter_toggle[0]
    assert ev["rect"] == [3, 3, 3, 3] and sorted(ev["toggle"][0]) == [5, 9]
    assert len(ev["writes"][0][1]) == 4, "toggle covers every spread HUD cell"
    assert _mismatches([ev]) == [], "the single dest-anchored toggle closes all crossings"


def test_dest_guard_composes_guard_conjunction():
    """The compose (conjunction) case: a timer that ticks iff object N fired
    (when_effect) AND mover M's destination is not void (when_dest). No single
    guard separates it (same M-dest, opposite outcomes driven by N). The
    dest-guard refine COMPOSES when_dest onto the existing when_effect (reusing
    the mover's id, not re-minting) rather than stripping it — additive over the
    bare pass, so it never perturbs a case bare already handled."""
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel import spec_abduction as SA
    from ztare.worldmodel.spec_catalog import lower_spec
    from ztare.worldmodel.gates import env_frame_indices
    truth, _ = lower_spec({
        "actions": {"0": [{"op": "translate_block", "id": "m", "match_colors": [9, 12],
                           "dy": 0, "dx": 1, "require_dest_colors": [0, 3],
                           "fill_color": 3, "component_min_colors": 2},
                          {"op": "translate_block", "id": "n", "match_colors": [4],
                           "dy": 0, "dx": 1, "require_dest_colors": [3], "fill_color": 3}]},
        "always": [{"op": "consume_extremal", "color": 11, "replacement": 3, "axis": "row",
                    "extreme": "min", "when_effect": ["n", True], "when_dest": ["m", [0], False]}]})
    A = ((3, 9, 12, 3, 3, 3), (3, 4, 3, 3, 3, 3), (11, 11, 11, 3, 3, 3))
    B = ((3, 9, 12, 3, 3, 3), (4, 7, 3, 3, 3, 3), (11, 11, 11, 3, 3, 3))
    C = ((3, 9, 12, 0, 3, 3), (3, 4, 3, 3, 3, 3), (11, 11, 11, 3, 3, 3))
    log = EpisodeLog()
    for s in (A, B, C, A, B, C):
        log.append(s, 0, truth(s, 0, 0), t=0)
    env = env_frame_indices(log)
    post = {"actions": {"0": [{"op": "translate_block", "id": "m", "match_colors": [9, 12],
                              "dy": 0, "dx": 1, "require_dest_colors": [0, 3],
                              "fill_color": 3, "component_min_colors": 2},
                             {"op": "translate_block", "id": "n", "match_colors": [4],
                              "dy": 0, "dx": 1, "require_dest_colors": [3], "fill_color": 3}]},
            "always": [{"op": "consume_extremal", "color": 11, "replacement": 3, "axis": "row",
                        "extreme": "min", "when_effect": ["n", True]}]}
    st, _ = lower_spec(post)
    w0 = SA._wrong_cell_count(st, log, env)
    out, _ = SA._dest_guard_refine(post, log)
    sto, _ = lower_spec(out)
    timer = [r for r in out["always"] if r.get("op") == "consume_extremal"][0]
    assert w0 > 0 and SA._wrong_cell_count(sto, log, env) == 0, out
    assert "when_effect" in timer and "when_dest" in timer, timer


def test_sprint_is_env_reset_classifies_refill():
    """The episode-crossing guard: gates.env_frame_indices classification of the
    last observed transition. A horizon-timer REFILL at a boundary is an env reset
    (continue the round); a normal timer tick is physics (end the round)."""
    import importlib.util
    from ztare.worldmodel.episode_log import EpisodeLog
    spec = importlib.util.spec_from_file_location(
        "arc3_play_loop", "scripts/public/control/arc3_play_loop.py")
    try:
        lp = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(lp)
    except Exception as e:                              # pragma: no cover - env dependent
        import pytest
        pytest.skip(f"loop script import unavailable: {e}")
    W = 24
    def bar(n):
        return tuple(tuple(11 if x < n else 3 for x in range(W)) for _ in range(2))
    base = EpisodeLog()
    n = 22
    for t in range(20):
        base.append(bar(n), 0, bar(n - 1), t=t)
        n -= 1
    assert lp._is_env_reset(base, [(bar(2), 0, bar(22), 20)]) is True
    assert lp._is_env_reset(base, [(bar(3), 0, bar(2), 21)]) is False


# ── Strategy Office (research_director) + WorldmodelBattery (GP-105 sibling) ───

def _mini_worldmodel_project(tmp_path):
    """A tiny synthetic interactive project: a mover translating right along row
    0 and a horizon resource (color 4) depleting along row 5, written to the
    canonical raw/episodes/episode_001.jsonl. Enough for every battery audit."""
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.grid_dsl import grid_from_lists

    def frame(mover_col, res_left):
        g = [[0] * 6 for _ in range(6)]
        g[0][mover_col] = 9                      # mover cell
        for x in range(res_left):
            g[5][x] = 4                          # depleting bar
        return grid_from_lists(g)

    log = EpisodeLog()
    for t in range(4):
        log.append(frame(t, 6 - t), 0, frame(t + 1, 6 - t - 1), t=t)
    log.write_jsonl(tmp_path / "raw" / "episodes" / "episode_001.jsonl")
    return tmp_path


def _bind_current_transfer_receipt(project, receipt):
    from ztare.worldmodel.carrier_loader import (
        resolve_current_carrier_evidence_identity,
    )

    carrier = project / "test_model.py"
    if not carrier.exists():
        carrier.write_text("VALUE = 1\n", encoding="utf-8")
    return {
        **receipt,
        "carrier_evidence_identity": (
            resolve_current_carrier_evidence_identity(project).to_dict()
        ),
    }


def test_strategy_battery_dossier_compiles_under_cap(tmp_path):
    from ztare.worldmodel.strategy_battery import WorldmodelBattery
    proj = _mini_worldmodel_project(tmp_path)
    (proj / "current_iteration.md").write_text(
        "verifier certifies the outcome; verifier updates the model; "
        "verifier should not author reusable advice"
    )
    dossier = WorldmodelBattery().run_audits(proj)
    assert dossier["rows_scanned"] == 4
    assert 0.0 <= dossier["firing_signal"] <= 1.0
    for key in ("novelty_decay", "conditional_coverage",
                "event_context_at_env_frames", "ledger_closure", "sweep_horizon",
                "semantic_deanchor_pressure", "planner_attention_pressure",
                "level_transfer_pressure"):
        assert key in dossier, key
    # the depleting bar is recovered as the horizon resource
    assert dossier["sweep_horizon"]["horizon_resource_color"] == 4
    # novelty decay carries the CAP-HORIZON caveat + a Good-Turing estimate
    assert "CAP-HORIZON" in dossier["novelty_decay"]["caveat"]
    assert 0.0 <= dossier["novelty_decay"]["good_turing_unseen_mass"] <= 1.0
    assert dossier["semantic_deanchor_pressure"]["suspects"][0]["term"] == "verifier"
    assert "deanchor_seam" in dossier["semantic_deanchor_pressure"]["suspects"][0]


def test_strategy_battery_menu_query_executes(tmp_path):
    from ztare.worldmodel.strategy_battery import WorldmodelBattery
    proj = _mini_worldmodel_project(tmp_path)
    battery = WorldmodelBattery()
    menu = battery.query_menu()
    assert "novelty_decay" in menu and "open_cards" in menu
    assert "semantic_deanchor" in menu
    assert "planner_attention" in menu
    assert "level_transfer" in menu
    _desc, fn = menu["novelty_decay"]
    out = fn(proj, k=2)
    assert out["segment_size_k"] == 2
    _desc, fn = menu["semantic_deanchor"]
    (proj / "current_iteration.md").write_text(
        "marker decides the goal; marker updates the planner; marker certifies progress"
    )
    deanchor = fn(proj, top=1)
    assert deanchor["suspects"][0]["term"] == "marker"
    assert set(battery.experiment_kinds()) >= {"reachability_sweep_to_goal",
                                               "coverage_gap_probe"}
def test_replay_residual_repair_sync_rejects_stale_card_and_opens_current_quotient(tmp_path):
    from ztare.common.operator_proposal_contract import write_proposal_cards
    from ztare.worldmodel.residual_repair import sync_replay_residual_repair_card

    proj = _mini_worldmodel_project(tmp_path)
    (proj / "workspace").mkdir(exist_ok=True)
    stale = {
        "schema": "strategy-experiment-v1",
        "kind": "compressed_counterexample_repair",
        "failure_family": "old-replay-residue",
        "rationale": "old replay residue",
        "falsifiable_prediction": "repair old residue",
        "action_plan": {
            "source_receipt": "workspace/old_replay_diagnostics.json",
            "residue_quotient": {
                "residue_class": "replay_mismatch_quotient",
                "cells": [{"y": 61, "x": 14}],
            },
            "required_next_gate": {
                "command": "replay_diagnostics",
                "success_status": "residual_class_removed_or_operator_carded",
            },
        },
        "kill_condition": "old residue gone",
        "disposition": "open",
    }
    ledger = proj / "workspace" / "strategy_experiments.jsonl"
    assert write_proposal_cards(ledger, [stale])
    diagnostics = {
        "schema": "ztare-replay-diagnostics-v1",
        "checked_rows": 5701,
        "exact_rows": 5665,
        "wrong_rows": 36,
        "wrong_cell_count": 144,
        "mismatch_classes": [{
            "count": 36,
            "first_row": 621,
            "t": 128,
            "action": 1,
            "signature": {
                "bbox": [61, 56, 62, 57],
                "mismatch_cells": 4,
                "pair_counts": [{"predicted": 8, "real": 3, "count": 4}],
            },
        }],
    }

    receipt = sync_replay_residual_repair_card(
        proj,
        diagnostics,
        source_ref="workspace/latest_replay_diagnostics_after_abduce.json",
    )

    assert receipt["rejected_stale_cards"] == 1
    assert receipt["cards_written"] == 1
    rows = [
        json.loads(line)
        for line in ledger.read_text().splitlines()
        if line.strip()
    ]
    assert sum(row["disposition"] == "rejected" for row in rows) == 1
    open_row = next(row for row in rows if row["disposition"] == "open")
    plan = open_row["action_plan"]
    assert plan["residue_quotient"]["bbox"] == [61, 56, 62, 57]
    assert plan["residue_quotient"]["signature"]["pair_counts"][0]["predicted"] == 8
    assert plan["routing_class"] == "classify_existing_operator_or_emit_operator_proposal"
    assert plan["required_next_gate"]["success_status"] == (
        "residual_class_removed_or_operator_carded"
    )


def test_replay_residual_sync_does_not_reject_transfer_seed_card(tmp_path):
    from ztare.common.operator_proposal_contract import open_cards, write_proposal_cards
    from ztare.worldmodel.residual_repair import sync_replay_residual_repair_card

    proj = _mini_worldmodel_project(tmp_path)
    (proj / "workspace").mkdir(exist_ok=True)
    transfer_card = {
        "schema": "strategy-experiment-v1",
        "kind": "compressed_counterexample_repair",
        "failure_family": "seed-clock-card",
        "rationale": "transfer probe needs its own seed producer",
        "falsifiable_prediction": "seed recovery precedes transfer probe exactness",
        "action_plan": {
            "source_receipt_schema": "ztare-arc3-level-transfer-probe-v1",
            "source_receipt": "workspace/latest_level_transfer_probe.json",
            "seed_prerequisite": {
                "seed_path": "workspace/level2_seed.json",
                "seed_bound": False,
                "status": "replayable_seed_missing",
            },
            "residue_quotient": {
                "residue_class": "action_independent_boundary_update",
                "cells": [{"y": 61, "x": 14}],
            },
            "required_next_gate": {
                "command": "recover_level_boundary_seed",
                "success_status": "replayable_boundary_seed_available",
                "blocked_until": "replayable_seed_available",
            },
        },
        "kill_condition": "seed recovery fails",
        "disposition": "open",
    }
    ledger = proj / "workspace" / "strategy_experiments.jsonl"
    assert write_proposal_cards(ledger, [transfer_card])
    diagnostics = {
        "schema": "ztare-replay-diagnostics-v1",
        "mismatch_classes": [{
            "count": 36,
            "first_row": 621,
            "t": 128,
            "action": 1,
            "signature": {
                "bbox": [40, 10, 41, 11],
                "mismatch_cells": 4,
                "pair_counts": [{"predicted": 3, "real": 8, "count": 4}],
            },
        }],
    }

    receipt = sync_replay_residual_repair_card(
        proj,
        diagnostics,
        source_ref="workspace/latest_replay_diagnostics_after_abduce.json",
    )

    assert receipt["rejected_stale_cards"] == 0
    assert len(open_cards(ledger)) == 2
    assert any(
        (card.get("action_plan") or {}).get("required_next_gate", {}).get("command")
        == "recover_level_boundary_seed"
        for card in open_cards(ledger)
    )


def test_seed_prerequisite_auditor_rejects_satisfied_missing_seed_card(tmp_path):
    from ztare.common.operator_proposal_contract import open_cards, write_proposal_cards
    from ztare.worldmodel.residual_repair import reject_satisfied_seed_prerequisite_cards

    proj = _mini_worldmodel_project(tmp_path)
    ws = proj / "workspace"
    ws.mkdir(exist_ok=True)
    (ws / "level2_seed.json").write_text(json.dumps({"full_sequence_from_reset": [0]}))
    ledger = ws / "strategy_experiments.jsonl"
    stale = {
        "schema": "strategy-experiment-v1",
        "kind": "compressed_counterexample_repair",
        "failure_family": "missing-seed-card",
        "rationale": "seed missing",
        "falsifiable_prediction": "recover seed",
        "action_plan": {
            "seed_prerequisite": {
                "seed_path": "workspace/level2_seed.json",
                "status": "replayable_seed_missing",
            },
            "required_next_gate": {
                "command": "recover_level_boundary_seed",
                "success_status": "replayable_boundary_seed_available",
            },
            "residue_quotient": {
                "residue_class": "action_independent_boundary_update",
            },
        },
        "kill_condition": "seed recovery fails",
        "disposition": "open",
    }
    current = {
        **stale,
        "failure_family": "seed-bound-card",
        "falsifiable_prediction": "repair and rerun transfer probe",
        "action_plan": {
            **stale["action_plan"],
            "seed_prerequisite": {
                "seed_path": "workspace/level2_seed.json",
                "status": "replayable_seed_available",
                "seed_bound": True,
            },
            "required_next_gate": {
                "command": "arc3_level_transfer_probe",
                "success_status": "exact_local_transfer_depth",
            },
        },
    }
    write_proposal_cards(ledger, [stale, current])

    rejected = reject_satisfied_seed_prerequisite_cards(
        proj, source_ref="workspace/level2_seed.json")

    assert len(rejected) == 1
    cards = open_cards(ledger)
    assert len(cards) == 1
    assert (cards[0]["action_plan"]["required_next_gate"]["command"]
            == "arc3_level_transfer_probe")


def test_replay_residual_repair_sync_rejects_stale_bbox_only_card(tmp_path):
    from ztare.common.operator_proposal_contract import write_proposal_cards
    from ztare.worldmodel.residual_repair import sync_replay_residual_repair_card

    proj = _mini_worldmodel_project(tmp_path)
    (proj / "workspace").mkdir(exist_ok=True)
    stale = {
        "schema": "strategy-experiment-v1",
        "kind": "compressed_counterexample_repair",
        "failure_family": "old-bbox-only-residue",
        "rationale": "old candidate-local residue",
        "falsifiable_prediction": "repair old bbox",
        "action_plan": {
            "source_receipt": "latest_eval_results.json:pre_judge_gate_payload",
            "residue_quotient": {
                "residue_class": "replay_mismatch_quotient",
                "bbox": [61, 57, 62, 57],
                "signature": {
                    "bbox": [61, 57, 62, 57],
                    "pair_counts": [{"predicted": 8, "real": 3, "count": 2}],
                },
            },
            "required_next_gate": {
                "command": "replay_diagnostics",
                "success_status": "residual_class_removed_or_operator_carded",
            },
        },
        "kill_condition": "old bbox no longer current",
        "disposition": "open",
    }
    ledger = proj / "workspace" / "strategy_experiments.jsonl"
    assert write_proposal_cards(ledger, [stale])
    diagnostics = {
        "schema": "ztare-replay-diagnostics-v1",
        "mismatch_classes": [{
            "count": 36,
            "first_row": 621,
            "t": 128,
            "action": 1,
            "signature": {
                "bbox": [40, 10, 41, 11],
                "mismatch_cells": 4,
                "pair_counts": [{"predicted": 3, "real": 8, "count": 4}],
            },
        }],
    }

    receipt = sync_replay_residual_repair_card(
        proj,
        diagnostics,
        source_ref="workspace/latest_replay_diagnostics_after_abduce.json",
    )

    rows = [json.loads(line) for line in ledger.read_text().splitlines() if line.strip()]
    assert receipt["rejected_stale_cards"] == 1
    assert any(
        row.get("failure_family") == "old-bbox-only-residue"
        and row.get("disposition") == "rejected"
        for row in rows
    )


def test_replay_residual_repair_sync_rejects_overlapping_changed_signature(tmp_path):
    from ztare.common.operator_proposal_contract import write_proposal_cards
    from ztare.worldmodel.residual_repair import sync_replay_residual_repair_card

    proj = _mini_worldmodel_project(tmp_path)
    (proj / "workspace").mkdir(exist_ok=True)
    stale = {
        "schema": "strategy-experiment-v1",
        "kind": "compressed_counterexample_repair",
        "failure_family": "old-overlap-different-pair",
        "rationale": "old overlapping replay residue",
        "falsifiable_prediction": "repair old quotient",
        "action_plan": {
            "source_receipt": "latest_eval_results.json:pre_judge_gate_payload",
            "residue_quotient": {
                "residue_class": "replay_mismatch_quotient",
                "t": 128,
                "action": 1,
                "bbox": [61, 56, 62, 57],
                "signature": {
                    "bbox": [61, 56, 62, 57],
                    "mismatch_cells": 4,
                    "pair_counts": [{"predicted": 8, "real": 3, "count": 4}],
                },
            },
            "required_next_gate": {
                "command": "replay_diagnostics",
                "success_status": "residual_class_removed_or_operator_carded",
            },
        },
        "kill_condition": "old quotient no longer current",
        "disposition": "open",
    }
    ledger = proj / "workspace" / "strategy_experiments.jsonl"
    assert write_proposal_cards(ledger, [stale])
    diagnostics = {
        "schema": "ztare-replay-diagnostics-v1",
        "mismatch_classes": [{
            "count": 1,
            "first_row": 5941,
            "t": 128,
            "action": 1,
            "signature": {
                "bbox": [61, 57, 62, 57],
                "mismatch_cells": 2,
                "pair_counts": [{"predicted": 3, "real": 8, "count": 2}],
            },
        }],
    }

    receipt = sync_replay_residual_repair_card(
        proj,
        diagnostics,
        source_ref="workspace/stale_surface_audit.json:current_root_gate",
    )

    rows = [json.loads(line) for line in ledger.read_text().splitlines() if line.strip()]
    assert receipt["rejected_stale_cards"] == 1
    assert any(
        row.get("failure_family") == "old-overlap-different-pair"
        and row.get("disposition") == "rejected"
        and "quotient signature" in row.get("counterexample", "")
        for row in rows
    )


def test_replay_residual_repair_sync_rejects_card_dominated_by_candidate_memory(tmp_path):
    from ztare.common.operator_proposal_contract import open_cards, write_proposal_cards
    from ztare.worldmodel.residual_repair import (
        build_replay_residual_repair_card,
        sync_replay_residual_repair_card,
    )

    proj = _mini_worldmodel_project(tmp_path)
    ws = proj / "workspace"
    ws.mkdir(exist_ok=True)
    diagnostics = {
        "schema": "ztare-replay-diagnostics-v1",
        "checked_rows": 5701,
        "exact_rows": 5665,
        "wrong_rows": 36,
        "wrong_cell_count": 144,
        "mismatch_classes": [{
            "count": 36,
            "first_row": 621,
            "t": 128,
            "action": 1,
            "signature": {
                "bbox": [61, 56, 62, 57],
                "mismatch_cells": 4,
                "pair_counts": [{"predicted": 8, "real": 3, "count": 4}],
            },
        }],
    }
    card = build_replay_residual_repair_card(
        diagnostics,
        source_ref="workspace/latest_replay_diagnostics_after_abduce.json",
    )
    assert card is not None
    ledger = ws / "strategy_experiments.jsonl"
    write_proposal_cards(ledger, [card])
    (ws / "candidate_memory.json").write_text(json.dumps({
        "schema": "ztare-candidate-memory-v1",
        "records": [{
            "source_type": "deterministic_near_miss",
            "submission": "workspace/submissions/best.py",
            "sha": "abc123",
            "visible_exact_rows": 5701,
            "visible_checked_rows": 5701,
            "visible_wrong_cells": 0,
            "holdout_depth": 0,
            "gate_score": 0.6667,
        }],
    }))

    receipt = sync_replay_residual_repair_card(
        proj,
        diagnostics,
        source_ref="workspace/latest_replay_diagnostics_after_abduce.json",
    )

    assert receipt["rejected_candidate_dominated_cards"] == 1
    assert receipt["cards_written"] == 0
    assert open_cards(ledger) == []
    rows = [json.loads(line) for line in ledger.read_text().splitlines() if line.strip()]
    assert rows[-1]["disposition"] == "rejected"
    assert rows[-1]["superseding_candidate"]["visible_exact_rows"] == 5701
    assert "holdout/local-transfer" in rows[-1]["counterexample"]


def test_replay_residual_repair_sync_rejects_card_dominated_by_better_near_miss(tmp_path):
    from ztare.common.operator_proposal_contract import open_cards, write_proposal_cards
    from ztare.worldmodel.residual_repair import (
        build_replay_residual_repair_card,
        sync_replay_residual_repair_card,
    )

    proj = _mini_worldmodel_project(tmp_path)
    ws = proj / "workspace"
    ws.mkdir(exist_ok=True)
    diagnostics = {
        "schema": "ztare-replay-diagnostics-v1",
        "checked_rows": 6125,
        "exact_rows": 6088,
        "wrong_rows": 37,
        "wrong_cell_count": 148,
        "mismatch_classes": [{
            "count": 37,
            "first_row": 621,
            "t": 128,
            "action": 1,
            "signature": {
                "bbox": [61, 56, 62, 57],
                "mismatch_cells": 4,
                "pair_counts": [{"predicted": 8, "real": 3, "count": 4}],
            },
        }],
    }
    card = build_replay_residual_repair_card(
        diagnostics,
        source_ref="workspace/stale_surface_audit.json:current_root_gate",
    )
    assert card is not None
    ledger = ws / "strategy_experiments.jsonl"
    write_proposal_cards(ledger, [card])
    (ws / "candidate_memory.json").write_text(json.dumps({
        "schema": "ztare-candidate-memory-v1",
        "records": [{
            "source_type": "deterministic_near_miss",
            "submission": "workspace/submissions/better.py",
            "sha": "better123",
            "visible_exact_rows": 6124,
            "visible_checked_rows": 6125,
            "visible_wrong_cells": 2,
            "holdout_depth": 0,
            "gate_score": 0.8,
        }],
    }))

    receipt = sync_replay_residual_repair_card(
        proj,
        diagnostics,
        source_ref="workspace/stale_surface_audit.json:current_root_gate",
    )

    assert receipt["rejected_candidate_dominated_cards"] == 1
    assert receipt["cards_written"] == 0
    assert open_cards(ledger) == []
    rows = [json.loads(line) for line in ledger.read_text().splitlines() if line.strip()]
    assert rows[-1]["disposition"] == "rejected"
    assert rows[-1]["superseding_candidate"]["visible_exact_rows"] == 6124
    assert "strictly better" in rows[-1]["counterexample"]


def test_stale_surface_audit_uses_dominating_candidate_memory_carrier(tmp_path):
    from ztare.common.operator_proposal_contract import open_cards, write_proposal_cards
    from ztare.research_director.strategy_office import STRATEGY_LEDGER
    from ztare.worldmodel.residual_repair import build_replay_residual_repair_card
    from ztare.worldmodel.stale_surface_audit import run_stale_surface_audit

    proj = tmp_path
    ws = proj / "workspace"
    submissions = ws / "submissions"
    submissions.mkdir(parents=True)
    (proj / "test_model.py").write_text("def model(grid, action, t): return grid\n")
    (submissions / "best.py").write_text("def model(grid, action, t): return grid\n")
    (proj / "gate_harness.py").write_text(
        """
import argparse, json

ap = argparse.ArgumentParser()
ap.add_argument("--emit-deterministic-gates", action="store_true")
ap.add_argument("--candidate-path", default="")
args = ap.parse_args()
is_best = args.candidate_path.endswith("best.py")
mismatch_classes = [] if is_best else [{
    "count": 2,
    "first_row": 1,
    "t": 7,
    "action": 1,
    "signature": {
        "bbox": [1, 1, 1, 2],
        "mismatch_cells": 2,
        "pair_counts": [{"predicted": 8, "real": 3, "count": 2}],
    },
}]
diagnostics = {
    "checked_rows": 10,
    "exact_rows": 10 if is_best else 8,
    "wrong_rows": 0 if is_best else 2,
    "wrong_cell_count": 0 if is_best else 4,
    "mismatch_classes": mismatch_classes,
}
print(json.dumps({
    "harness_ok": True,
    "gated_sha256": "best" if is_best else "root",
    "gates": {
        "visible_replay_exact": {"diagnostics": diagnostics},
        "holdout_rollout_exact": {"value": 0},
    },
}))
"""
    )
    diagnostics = {
        "schema": "ztare-replay-diagnostics-v1",
        "checked_rows": 10,
        "exact_rows": 8,
        "wrong_rows": 2,
        "wrong_cell_count": 4,
        "mismatch_classes": [{
            "count": 2,
            "first_row": 1,
            "t": 7,
            "action": 1,
            "signature": {
                "bbox": [1, 1, 1, 2],
                "mismatch_cells": 2,
                "pair_counts": [{"predicted": 8, "real": 3, "count": 2}],
            },
        }],
    }
    card = build_replay_residual_repair_card(
        diagnostics,
        source_ref="workspace/stale_surface_audit.json:root_gate",
    )
    assert card is not None
    ledger = ws / STRATEGY_LEDGER
    write_proposal_cards(ledger, [card])
    (ws / "candidate_memory.json").write_text(json.dumps({
        "schema": "ztare-candidate-memory-v1",
        "records": [{
            "source_type": "deterministic_near_miss",
            "submission": "workspace/submissions/best.py",
            "sha": "best123",
            "source_excerpt": "def model(grid, action, t): return grid\n",
            "visible_exact_rows": 10,
            "visible_checked_rows": 10,
            "visible_wrong_cells": 0,
            "holdout_depth": 0,
            "gate_score": 0.6667,
        }],
    }))

    receipt = run_stale_surface_audit(proj, apply=True, force=True)

    assert receipt["active_carrier"]["source"] == "candidate_memory"
    assert receipt["active_carrier"]["candidate_sha"] == "best123"
    assert receipt["root_replay"]["exact_rows"] == 8
    assert receipt["current_replay"]["exact_rows"] == 10
    sync = next(a for a in receipt["actions"] if a["action"] == "sync_replay_residual_repair_card")
    assert sync["rejected_stale_cards"] == 1
    assert open_cards(ledger) == []


def test_stale_surface_audit_consumes_supplied_gate_without_rerun(
    tmp_path: Path,
    monkeypatch,
):
    import ztare.worldmodel.stale_surface_audit as audit

    project = tmp_path / "project"
    (project / "workspace").mkdir(parents=True)
    (project / "test_model.py").write_text(
        "def step(state, action, t):\n    return state\n",
        encoding="utf-8",
    )
    payload = {
        "harness_ok": True,
        "gated_sha256": "configured",
        "gates": {
            "visible_replay_exact": {
                "diagnostics": {
                    "checked_rows": 3,
                    "exact_rows": 2,
                    "wrong_rows": 1,
                    "wrong_cell_count": 4,
                    "mismatch_classes": [],
                }
            }
        },
    }

    def forbidden_gate(*_args, **_kwargs):
        raise AssertionError("supplied gate payload must prevent a second gate run")

    monkeypatch.setattr(audit, "_run_gate", forbidden_gate)
    receipt = audit.run_stale_surface_audit(
        project,
        force=True,
        gate_payload=payload,
    )

    assert receipt["active_carrier"]["source"] == "configured_system1_gate"
    assert receipt["current_replay"]["exact_rows"] == 2
    assert receipt["gate"]["gated_sha256"] == "configured"


def test_stale_surface_cache_identity_advances_with_evidence_epoch(tmp_path: Path):
    """A `latest` gate projection cannot remain current after bank growth."""
    from ztare.worldmodel.stale_surface_audit import run_stale_surface_audit

    project = tmp_path / "project"
    episode = project / "raw" / "episodes" / "episode_001.jsonl"
    episode.parent.mkdir(parents=True)
    (project / "workspace").mkdir()
    (project / "test_model.py").write_text(
        "def step(state, action, t):\n    return state\n",
        encoding="utf-8",
    )
    episode.write_text('{"observation":1}\n', encoding="utf-8")
    payload = {
        "harness_ok": True,
        "gated_sha256": "configured",
        "gates": {
            "visible_replay_exact": {
                "diagnostics": {
                    "checked_rows": 1,
                    "exact_rows": 1,
                    "wrong_rows": 0,
                    "wrong_cell_count": 0,
                    "mismatch_classes": [],
                }
            }
        },
    }

    first = run_stale_surface_audit(project, gate_payload=payload)
    assert first["cached"] is False
    assert run_stale_surface_audit(project, gate_payload=payload)["cached"] is True

    with episode.open("a", encoding="utf-8") as handle:
        handle.write('{"observation":2}\n')
    advanced = run_stale_surface_audit(project, gate_payload=payload)
    assert advanced["cached"] is False
    assert (
        advanced["input_fingerprint"]["evidence_epoch"]
        != first["input_fingerprint"]["evidence_epoch"]
    )


def test_level_transfer_probe_quotients_action_invariant_boundary_residue():
    import importlib.util
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "public" / "control" / "arc3_level_transfer_probe.py"
    spec = importlib.util.spec_from_file_location("arc3_level_transfer_probe", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    diffs = {
        a: [
            {"y": 61, "x": 14, "boundary": 11, "predicted": 11, "observed": 3},
            {"y": 62, "x": 14, "boundary": 11, "predicted": 11, "observed": 3},
        ]
        for a in range(4)
    }
    q = mod._boundary_residue_quotient(diffs, action_arity=4)
    assert q["residue_class"] == "action_independent_boundary_update"
    assert q["all_action_invariant"] is True
    assert q["all_predicted_equals_boundary"] is True
    assert q["cell_count"] == 2
    cert = mod._quotient_repair_certificate(diffs, q)
    assert cert["sufficient_for_first_step"] is True
    assert cert["repair_class"] == "action_independent_cell_rewrite"
    assert cert["repair_map"] == [
        {"y": 61, "x": 14, "from_predicted": 11, "from_boundary": 11, "to_observed": 3},
        {"y": 62, "x": 14, "from_predicted": 11, "from_boundary": 11, "to_observed": 3},
    ]
    assert "does not claim level solve" in cert["authority"]
    local = mod._local_transfer_summary(
        [
            {"initial_action": 0, "post_step": 1, "action": 0, "wrong_cells": 2,
             "first_diffs": diffs[0]},
            {"initial_action": 0, "post_step": 2, "action": 1, "wrong_cells": 2,
             "first_diffs": [
                 {"y": 61, "x": 16, "predicted": 11, "observed": 3},
                 {"y": 62, "x": 16, "predicted": 11, "observed": 3},
             ]},
        ],
        cert,
    )
    assert local["exact_steps_after_first_step_repair"] == 1
    assert local["first_step_repair_generalizes_to_depth"] is False
    assert local["first_failed_after_first_step_repair"]["post_step"] == 2
    local_q = mod._local_residue_quotient([
        {"initial_action": 0, "post_step": 1, "action": 0,
         "first_diffs": [dict(d, before=11) for d in diffs[0]]},
        {"initial_action": 0, "post_step": 2, "action": 1,
         "first_diffs": [
             {"y": 16, "x": 15, "before": 11, "predicted": 3, "observed": 11},
             {"y": 61, "x": 16, "before": 11, "predicted": 11, "observed": 3},
        ]},
    ])
    rels = {c["relation"] for c in local_q["classes"]}
    assert local_q["status"] == "multi_class_local_residue"
    assert {"underpredicted_update", "overpredicted_update"} <= rels
    under = next(c for c in local_q["classes"] if c["relation"] == "underpredicted_update")
    assert under["refinement_hint"]["candidate_class"] == (
        "component_scoped_extremal_count_or_rate_refinement_candidate"
    )
    assert under["refinement_hint"]["existing_catalog_primitive"] == (
        "consume_extremal.count_or_rate"
    )
    assert "evidence-induced component" in under["refinement_hint"]["missing_generalization"]


def test_level_transfer_probe_exact_game_id_bypasses_listing(monkeypatch):
    import importlib.util
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "public" / "control" / "arc3_level_transfer_probe.py"
    spec = importlib.util.spec_from_file_location("arc3_level_transfer_probe", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    def _boom():
        raise AssertionError("list_games should not run for an exact game id")

    monkeypatch.setattr(mod, "list_games", _boom)

    assert mod._resolve_game_id("ls20-9607627b") == "ls20-9607627b"


def test_level_boundary_harvest_exact_game_id_bypasses_listing(monkeypatch):
    import importlib.util
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "public" / "control" / "arc3_level_boundary_harvest.py"
    spec = importlib.util.spec_from_file_location("arc3_level_boundary_harvest", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    def _boom():
        raise AssertionError("list_games should not run for an exact game id")

    monkeypatch.setattr(mod, "list_games", _boom)

    assert mod._resolve_game_id("ls20-9607627b") == "ls20-9607627b"


def test_level_transfer_probe_cli_persists_latest_receipt(tmp_path, monkeypatch):
    import importlib.util
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "public" / "control" / "arc3_level_transfer_probe.py"
    spec = importlib.util.spec_from_file_location("arc3_level_transfer_probe", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    project = tmp_path / "arc3_toy_gov"
    (project / "workspace").mkdir(parents=True)
    candidate = project / "test_model.py"
    candidate.write_text("def step(state, action, t):\n    return state\n")
    seed = project / "workspace" / "level2_seed.json"
    seed.write_text(json.dumps({"full_sequence_from_reset": [0]}))

    monkeypatch.setattr(mod, "run_probe", lambda **_kw: {
        "schema": "ztare-arc3-level-transfer-probe-v1",
        "status": "bounded_mismatch",
        "seed_path": str(seed),
    })

    rc = mod.main([
        "--game", "toy",
        "--seed-path", str(seed),
        "--candidate-path", str(candidate),
    ])

    assert rc == 0
    latest = json.loads((project / "workspace" / "latest_level_transfer_probe.json").read_text())
    assert latest["status"] == "bounded_mismatch"


def test_play_loop_emits_planner_goal_cue_absent_binding():
    from types import SimpleNamespace

    mod = _load_arc3_play_loop()
    pr = SimpleNamespace(status="plan_exhausted", levels_gained=0)
    bindings = mod._planner_attention_bindings(
        pr, goal_fn=None, progress_fn=None, evidence_grown_by=0)
    assert bindings[0]["term"] == "planner_goal_cue_absent"
    assert set(bindings[0]["roles"]) == {
        "model_update", "search_control", "selection"}
    assert mod._planner_attention_bindings(
        pr, goal_fn=lambda _g: False, progress_fn=None, evidence_grown_by=0) == []


def test_play_loop_strategy_office_hook_is_opt_in(tmp_path, monkeypatch):
    mod = _load_arc3_play_loop()
    monkeypatch.delenv("ZTARE_STRATEGY_OFFICE", raising=False)
    (tmp_path / "workspace").mkdir()
    from ztare.worldmodel import search_control_repair as scr
    monkeypatch.setattr(
        scr,
        "write_search_control_repair_card",
        lambda _project: [{"kind": "search_control_residue_repair"}],
    )
    entry = {
        "pursuit": "plan_exhausted",
        "levels_gained": 0,
        "evidence_grown_by": 0,
    }

    out = mod._maybe_convene_strategy_office(
        tmp_path, {}, {"cycles": [entry]}, cycle=1, entry=entry)

    assert out["enabled"] is False
    assert out["deterministic_cards_written"] == 1


def test_play_loop_detects_open_strategy_cards(tmp_path):
    mod = _load_arc3_play_loop()
    ws = tmp_path / "workspace"
    ws.mkdir()
    assert mod._has_open_strategy_cards(tmp_path) is False
    (ws / "strategy_experiments.jsonl").write_text(json.dumps({
        "schema": "strategy-experiment-v1",
        "kind": "search_control_residue_repair",
        "failure_family": "fam",
        "disposition": "open",
    }) + "\n")
    assert mod._has_open_strategy_cards(tmp_path) is True


def _bound_discharged_task_payload() -> dict:
    from ztare.common.task_discharge import (
        TaskDischargeContract,
        TaskDischargeReceipt,
    )

    contract = TaskDischargeContract(
        contract_id="test.skill.v1",
        adjudicator_id="test.adjudicator.v1",
        lifecycle_scope="test_run",
        owner="test_profile",
    )
    receipt = TaskDischargeReceipt(
        contract_sha256=contract.sha256,
        adjudicator_id=contract.adjudicator_id,
        status="discharged",
        authority="test_adapter",
        observed={"attested": True},
        evidence_refs=("test_adapter:discharge",),
    )
    return {
        "task_contract": contract.to_dict(),
        "task_discharge_receipt": receipt.to_dict(),
        "task_discharged": True,
        "status": "TASK_DISCHARGED",
    }


def test_search_control_card_disposition_from_terminal_report(tmp_path):
    from ztare.common.operator_proposal_contract import open_cards, write_proposal_cards
    from ztare.worldmodel.search_control_repair import (
        build_search_control_residue_card,
        disposition_search_control_cards_from_report,
    )

    proj = _mini_worldmodel_project(tmp_path)
    (proj / "workspace").mkdir(exist_ok=True)
    card = build_search_control_residue_card({
        "planner_attention_pressure": {
            "anomalies": [{"cycle": 1, "steps": 250}],
        },
        # Unrelated open cards do not own this residual identity.
        "ledger_closure": {"open_strategy_cards": 7},
    })
    assert card is not None
    ledger = proj / "workspace" / "strategy_experiments.jsonl"
    write_proposal_cards(ledger, [card])

    report = {
        "cycles": [{
            "cycle": 2,
            "pursuit": "goal_reached",
            **_bound_discharged_task_payload(),
            "levels_gained": 1,
            "steps": 18,
            "terminal_witness_sha": "abc",
        }],
    }
    dispositions = disposition_search_control_cards_from_report(proj, report)

    assert len(dispositions) == 1
    assert dispositions[0]["disposition"] == "accepted"
    assert dispositions[0]["discharge"]["observed_status"] == "terminal_event"
    assert "terminal_event" in dispositions[0]["discharge"]["observed_statuses"]
    assert dispositions[0]["discharge"]["terminal_witness_sha"] == "abc"
    assert open_cards(ledger) == []


def test_terminal_closure_audit_keeps_candidate_gate_separate(tmp_path):
    from ztare.common.operator_proposal_contract import open_cards, write_proposal_cards
    from ztare.worldmodel.search_control_repair import (
        build_search_control_residue_card,
        disposition_search_control_cards_from_report,
        write_terminal_closure_audit,
    )

    proj = _mini_worldmodel_project(tmp_path)
    (proj / "workspace").mkdir(exist_ok=True)
    card = build_search_control_residue_card({
        "planner_attention_pressure": {
            "anomalies": [{"cycle": 1, "steps": 250}],
        },
        "ledger_closure": {"open_strategy_cards": 0},
    })
    assert card is not None
    ledger = proj / "workspace" / "strategy_experiments.jsonl"
    write_proposal_cards(ledger, [card])
    report = {
        "mode": "governed",
        "result": "beat",
        "cycles": [{
            "cycle": 2,
            "pursuit": "goal_reached",
            **_bound_discharged_task_payload(),
            "levels_gained": 1,
            "steps": 18,
            "terminal_witness_sha": "abc",
        }],
    }
    (proj / "workspace" / "arc3_play_loop_report.json").write_text(json.dumps(report))
    disposition_search_control_cards_from_report(proj, report)
    assert open_cards(ledger) == []
    (proj / "latest_eval_results.json").write_text(json.dumps({
        "score": 0,
        "score_cap_reason": "pre_judge_gate_harness_failed",
    }))
    current_survivor = _bind_current_transfer_receipt(proj, {
        "observed_at_utc": "2026-07-06T04:54:49+00:00",
        "gate_score": 1.0,
        "passed_gates": 3,
        "holdout_depth": 10,
        "source_type": "full_survivor",
    })
    current_sha = current_survivor["carrier_evidence_identity"]["carrier_sha256"]
    current_survivor["sha"] = current_sha
    (proj / "workspace" / "candidate_memory.json").write_text(json.dumps({
        "schema": "ztare-worldmodel-candidate-memory-v1",
        "records": [
            {
                "sha": "old-assisted",
                "observed_at_utc": "2026-07-06T01:01:00+00:00",
                "gate_score": 1.0,
                "passed_gates": 3,
                "holdout_depth": 10,
                "source_type": "manual_probe",
                "assistance_label": "codex_assisted",
            },
            current_survivor,
        ],
    }))

    receipt = write_terminal_closure_audit(proj)

    assert receipt["status"] == "terminal_closed_candidate_unpromoted"
    assert receipt["closure_verification"]["ok"] is True
    assert receipt["level_closed"] is True
    assert receipt["search_control_closed"] is True
    assert receipt["candidate_gate"]["candidate_unpromoted"] is True
    assert receipt["authority"]["candidate_promotion_used_for_closure"] is False
    assert receipt["strategy_ledger"]["matching_terminal_discharges"] == 1
    assert receipt["candidate_memory"]["records"] == 2
    assert (
        receipt["candidate_memory"]["latest_gate_passing"]["sha"]
        == current_sha
    )
    assert receipt["claim_boundaries"]["level_closure"]["proven"] is True
    assert receipt["claim_boundaries"]["candidate_promotion"]["proven"] is False
    assert (
        receipt["claim_boundaries"]["candidate_promotion"]["reason"]
        == "terminal_closure_does_not_promote_candidate"
    )
    assert receipt["claim_boundaries"]["bridge_law_support"]["proven"] is True
    assert (
        receipt["claim_boundaries"]["bridge_law_support"]["latest_gate_passing_sha"]
        == current_sha
    )
    assert receipt["claim_boundaries"]["autonomous_completion"]["proven"] is False
    assert (
        receipt["claim_boundaries"]["autonomous_completion"]["reason"]
        == "missing_explicit_unassisted_terminal_provenance"
    )
    saved = json.loads((proj / "workspace" / "terminal_closure_audit.json").read_text())
    assert saved["terminal_report"]["terminal_witness_sha"] == "abc"


def test_terminal_closure_audit_requires_explicit_autonomy_provenance(tmp_path):
    from ztare.common.operator_proposal_contract import write_proposal_cards
    from ztare.worldmodel.search_control_repair import (
        build_search_control_residue_card,
        disposition_search_control_cards_from_report,
        write_terminal_closure_audit,
    )

    proj = _mini_worldmodel_project(tmp_path)
    (proj / "workspace").mkdir(exist_ok=True)
    card = build_search_control_residue_card({
        "planner_attention_pressure": {
            "anomalies": [{"cycle": 1, "steps": 250}],
        },
        "ledger_closure": {"open_strategy_cards": 0},
    })
    ledger = proj / "workspace" / "strategy_experiments.jsonl"
    write_proposal_cards(ledger, [card])
    report = {
        "mode": "governed",
        "result": "beat",
        "cycles": [{
            "cycle": 2,
            "pursuit": "goal_reached",
            **_bound_discharged_task_payload(),
            "levels_gained": 1,
            "steps": 18,
            "terminal_witness_sha": "abc",
            "autonomy_provenance": {
                "label": "self_play",
                "operator_interventions": 0,
                "source": "play_loop",
            },
        }],
    }
    (proj / "workspace" / "arc3_play_loop_report.json").write_text(json.dumps(report))
    disposition_search_control_cards_from_report(proj, report)
    (proj / "latest_eval_results.json").write_text(json.dumps({
        "score": 0,
        "score_cap_reason": "pre_judge_gate_harness_failed",
    }))

    receipt = write_terminal_closure_audit(proj)

    assert receipt["claim_boundaries"]["autonomous_completion"] == {
        "proven": True,
        "reason": "",
        "assistance_label": "self_play",
        "operator_interventions": 0,
        "source": "play_loop",
    }


def test_terminal_closure_audit_ledger_survives_later_nonclose_attempt(tmp_path):
    from ztare.common.operator_proposal_contract import write_proposal_cards
    from ztare.worldmodel.search_control_repair import (
        build_search_control_residue_card,
        disposition_search_control_cards_from_report,
        write_terminal_closure_audit,
    )

    proj = _mini_worldmodel_project(tmp_path)
    (proj / "workspace").mkdir(exist_ok=True)
    card = build_search_control_residue_card({
        "planner_attention_pressure": {
            "anomalies": [{"cycle": 1, "steps": 250}],
        },
        "ledger_closure": {"open_strategy_cards": 0},
    })
    ledger = proj / "workspace" / "strategy_experiments.jsonl"
    write_proposal_cards(ledger, [card])
    beat_report = {
        "mode": "governed",
        "result": "beat",
        "cycles": [{
            "cycle": 1,
            "pursuit": "goal_reached",
            **_bound_discharged_task_payload(),
            "levels_gained": 1,
            "steps": 19,
            "terminal_witness_sha": "terminal-level-1",
        }],
    }
    (proj / "workspace" / "arc3_play_loop_report.json").write_text(json.dumps(beat_report))
    disposition_search_control_cards_from_report(proj, beat_report)
    (proj / "latest_eval_results.json").write_text(json.dumps({
        "score": 0,
        "score_cap_reason": "pre_judge_gate_harness_failed",
    }))

    first = write_terminal_closure_audit(proj)
    assert first["level_closed"] is True

    no_level_report = {
        "mode": "governed",
        "result": "no_level_in_budget",
        "cycles": [{
            "cycle": 2,
            "pursuit": "model_diverged",
            "status": "NOT_FINISHED",
            "levels_gained": 0,
            "steps": 44,
            "terminal_witness_sha": "nonterminal-transition-witness",
        }],
    }
    (proj / "workspace" / "arc3_play_loop_report.json").write_text(json.dumps(no_level_report))
    latest = write_terminal_closure_audit(proj)

    history_path = proj / "workspace" / "terminal_closure_audits.jsonl"
    rows = [
        json.loads(line)
        for line in history_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert latest["status"] == "not_terminal_closed"
    assert latest["level_closed"] is False
    assert len(rows) == 1
    assert rows[0]["terminal_report"]["terminal_witness_sha"] == "terminal-level-1"
    assert rows[0]["ledger_schema"] == "ztare-terminal-closure-audit-ledger-v1"


def test_play_loop_report_writer_always_emits_terminal_closure_audit(tmp_path):
    from ztare.common.operator_proposal_contract import write_proposal_cards
    from ztare.worldmodel.search_control_repair import (
        build_search_control_residue_card,
        disposition_search_control_cards_from_report,
    )

    mod = _load_arc3_play_loop()
    proj = _mini_worldmodel_project(tmp_path)
    (proj / "workspace").mkdir(exist_ok=True)
    card = build_search_control_residue_card({
        "planner_attention_pressure": {
            "anomalies": [{"cycle": 1, "steps": 250}],
        },
        "ledger_closure": {"open_strategy_cards": 0},
    })
    write_proposal_cards(proj / "workspace" / "strategy_experiments.jsonl", [card])
    report = {
        "game": "x",
        "mode": "governed",
        "result": "beat",
        "cycles": [{
            "cycle": 1,
            "pursuit": "goal_reached",
            **_bound_discharged_task_payload(),
            "levels_gained": 1,
            "steps": 18,
            "terminal_witness_sha": "abc",
        }],
    }
    disposition_search_control_cards_from_report(proj, report)
    (proj / "latest_eval_results.json").write_text(json.dumps({
        "score": 0,
        "score_cap_reason": "pre_judge_gate_harness_failed",
    }))

    receipt = mod._write_play_report_and_terminal_audit(proj, report)

    assert (proj / "workspace" / "arc3_play_loop_report.json").exists()
    assert (proj / "workspace" / "terminal_closure_audit.json").exists()
    assert receipt["status"] == "terminal_closed_candidate_unpromoted"
    assert receipt["authority"]["candidate_promotion_used_for_closure"] is False


def test_terminal_closure_verifier_rejects_candidate_laundering(tmp_path):
    from ztare.worldmodel.search_control_repair import validate_terminal_closure_audit

    receipt = {
        "schema": "ztare-worldmodel-terminal-closure-audit-v1",
        "status": "terminal_closed_candidate_unpromoted",
        "level_closed": True,
        "search_control_closed": True,
        "terminal_report": {
            "pursuit": "goal_reached",
            "levels_gained": 1,
            "terminal_witness_sha": "abc",
        },
        "strategy_ledger": {
            "open_cards": 0,
            "matching_terminal_discharges": 1,
        },
        "candidate_gate": {
            "candidate_unpromoted": True,
            "blocked_before_judge": True,
        },
        "claim_boundaries": {
            "level_closure": {
                "proven": True,
                "authority": "terminal_report",
                "terminal_witness_sha": "abc",
            },
            "search_control_card": {"proven": True},
            "candidate_promotion": {
                "proven": True,
                "authority": "terminal_report",
                "reason": "terminal event implies candidate success",
            },
            "bridge_law_support": {
                "proven": True,
                "authority": "terminal_report",
                "separate_from_terminal_closure": False,
            },
            "autonomous_completion": {
                "proven": True,
                "assistance_label": "codex_assisted",
                "operator_interventions": 1,
                "source": "prose",
            },
        },
        "authority": {
            "closure_source": "terminal_report",
            "candidate_promotion_used_for_closure": True,
            "authority_ladder_ok": True,
        },
    }

    verification = validate_terminal_closure_audit(receipt)

    assert verification["ok"] is False
    assert "candidate_promotion_used_for_terminal_closure" in verification["errors"]
    assert "candidate_promotion_claim_not_false" in verification["errors"]
    assert "bridge_support_not_bound_to_candidate_memory" in verification["errors"]
    assert "autonomy_claim_without_zero_intervention_receipt" in verification["errors"]


def test_search_control_gate_matching_uses_status_atoms_not_substrings():
    from ztare.common.abstraction_functor import FiniteQuotient, parse_disjunctive_atoms
    from ztare.worldmodel.search_control_repair import _cycle_satisfies_required_gate

    cycle = {
        "pursuit": "goal_reached",
        "levels_gained": 1,
        **_bound_discharged_task_payload(),
    }

    assert parse_disjunctive_atoms(
        "terminal_event_or_new_evidence"
    ) == frozenset({"terminal_event", "new_evidence"})
    assert FiniteQuotient(frozenset({"terminal_event"})).satisfies_any(
        "terminal_event_or_new_evidence"
    )
    assert not FiniteQuotient(frozenset({"terminal_event"})).satisfies_any(
        "terminal_eventual"
    )
    assert _cycle_satisfies_required_gate(cycle, "terminal_event") is True
    assert _cycle_satisfies_required_gate(
        cycle,
        "terminal_event_or_new_evidence_or_more_specific_strategy_receipt",
    ) is True
    assert _cycle_satisfies_required_gate(cycle, "terminal_eventual") is False
    progress_only = {"pursuit": "goal_reached", "levels_gained": 1}
    assert _cycle_satisfies_required_gate(progress_only, "terminal_event") is False

    forged_properties = {
        "observed_status": "terminal_event",
        "status": "TASK_DISCHARGED",
        "task_discharged": True,
    }
    assert _cycle_satisfies_required_gate(forged_properties, "terminal_event") is False


def test_play_loop_strategy_office_hook_commissions_after_no_progress(
    tmp_path, monkeypatch,
):
    mod = _load_arc3_play_loop()
    (tmp_path / "workspace").mkdir()
    monkeypatch.delenv("ZTARE_STRATEGY_OFFICE", raising=False)
    from ztare.research_director import strategy_office as so
    from ztare.worldmodel import strategy_battery as sb

    calls = []

    def fake_convene(project, battery, **kwargs):
        calls.append((project, battery, kwargs))
        return [{"kind": "targeted_action_path_probe"}]

    monkeypatch.setattr(so, "convene", fake_convene)
    monkeypatch.setattr(sb, "WorldmodelBattery", lambda: "battery")
    entry = {
        "pursuit": "plan_exhausted",
        "levels_gained": 0,
        "evidence_grown_by": 0,
    }
    report = {"cycles": [entry]}

    out = mod._maybe_convene_strategy_office(
        tmp_path,
        {"enable_strategy_office": True, "strategy_office_leaf_model": "cheap"},
        report,
        cycle=2,
        entry=entry,
    )

    assert out["cards_written"] == 1
    assert out["cycle"] == 2
    assert calls[0][0] == tmp_path
    assert calls[0][1] == "battery"
    assert calls[0][2]["leaf_model"] == "cheap"
    saved = json.loads((tmp_path / "workspace" / "arc3_play_loop_report.json").read_text())
    assert saved["cycles"][0]["pursuit"] == "plan_exhausted"


def test_play_loop_writes_replayable_next_level_seed(tmp_path):
    mod = _load_arc3_play_loop()
    seed = mod._write_level_boundary_seed(
        tmp_path,
        game_id="toy-game",
        cycle=3,
        completed_level=1,
        actions=[0, 1, 3],
    )

    assert seed["schema"] == "ztare-level-boundary-seed-v1"
    assert seed["target_level"] == 2
    assert seed["full_sequence_from_reset"] == [0, 1, 3]
    assert seed["execution_segments"] == [{
        "segment_id": "segment-0",
        "segment_kind": "active_control",
        "source_ref": "arc3_play_loop",
        "authority": "live_environment_execution",
        "start_index": 0,
        "end_index_exclusive": 3,
        "actions": [0, 1, 3],
    }]
    level_seed = json.loads((tmp_path / "workspace" / "level2_seed.json").read_text())
    latest = json.loads((tmp_path / "workspace" / "latest_level_boundary_seed.json").read_text())
    assert level_seed == latest == seed
    assert "replay seed only" in seed["authority"]


def test_play_loop_replays_seed_through_environment_before_use(tmp_path):
    mod = _load_arc3_play_loop()
    mod._write_level_boundary_seed(
        tmp_path,
        game_id="toy-game",
        cycle=1,
        completed_level=2,
        actions=[0, 1, 1],
    )

    class Adapter:
        action_arity = 2

        def __init__(self):
            self.reset()

        def reset(self):
            self.levels_completed = 0
            self.actions = []

        def step(self, action):
            self.actions.append(action)
            if self.actions == [0]:
                self.levels_completed = 1
            if self.actions == [0, 1, 1]:
                self.levels_completed = 2

    adapter = Adapter()
    receipt = mod._replay_latest_level_boundary_seed(tmp_path, adapter)

    assert receipt["status"] == "verified"
    assert receipt["declared_epoch"] == receipt["observed_epoch"] == 2
    assert receipt["actions"] == [0, 1, 1]
    assert receipt["execution_segments"][0]["segment_kind"] == "active_control"
    assert adapter.levels_completed == 2
    rows = [
        json.loads(line)
        for line in (tmp_path / "workspace" / "level_boundary_seed_replays.jsonl")
        .read_text()
        .splitlines()
    ]
    assert rows[-1]["status"] == "verified"


def test_play_loop_severs_seed_when_replay_epoch_disagrees(tmp_path):
    mod = _load_arc3_play_loop()
    mod._write_level_boundary_seed(
        tmp_path,
        game_id="toy-game",
        cycle=1,
        completed_level=2,
        actions=[0],
    )

    class Adapter:
        action_arity = 1

        def __init__(self):
            self.reset()

        def reset(self):
            self.levels_completed = 0

        def step(self, _action):
            self.levels_completed = 1

    adapter = Adapter()
    receipt = mod._replay_latest_level_boundary_seed(tmp_path, adapter)

    assert receipt["status"] == "epoch_mismatch"
    assert receipt["observed_epoch"] == 1
    assert receipt["active_epoch"] == 0
    assert receipt["actions"] == []
    assert adapter.levels_completed == 0


def test_seed_recovery_card_executes_live_seed_producer(tmp_path):
    from ztare.common.operator_proposal_contract import write_proposal_cards
    from ztare.worldmodel.adapter import episode_log_path
    from ztare.worldmodel.episode_log import EpisodeLog

    mod = _load_arc3_play_loop()
    (tmp_path / "workspace" / "submissions").mkdir(parents=True)
    EpisodeLog().write_jsonl(episode_log_path(tmp_path))
    (tmp_path / "workspace" / "submissions" / "identity.py").write_text(
        "def step(grid, action, t):\n    return grid\n"
    )
    (tmp_path / "workspace" / "candidate_memory.json").write_text(json.dumps({
        "schema": "ztare-candidate-memory-v1",
        "records": [{
            "source_type": "deterministic_near_miss",
            "submission": "workspace/submissions/identity.py",
            "sha": "identity",
            "visible_exact_rows": 1,
            "visible_checked_rows": 1,
            "visible_wrong_cells": 0,
        }],
    }))
    write_proposal_cards(tmp_path / "workspace" / "strategy_experiments.jsonl", [{
        "schema": "strategy-experiment-v1",
        "kind": "compressed_counterexample_repair",
        "failure_family": "seed-recovery-test",
        "failure_family_sha": "seed-card",
        "rationale": "need seed",
        "falsifiable_prediction": "seed producer writes replayable seed",
        "action_plan": {
            "seed_prerequisite": {
                "seed_path": "workspace/level2_seed.json",
                "status": "replayable_seed_missing",
            },
            "required_next_gate": {
                "command": "recover_level_boundary_seed",
                "success_status": "replayable_boundary_seed_available",
            },
        },
        "kill_condition": "seed not recovered",
        "disposition": "open",
    }])

    class CompletesAfterOne:
        action_arity = 1
        def __init__(self, _game_id):
            self.levels_completed = 0
            self._state = ((0,),)
            self._t = 0
        def reset(self):
            self.levels_completed = 0
            self._state = ((0,),)
            self._t = 0
            return self._state
        @property
        def state(self):
            return self._state
        @property
        def t(self):
            return self._t
        def step(self, _action):
            self._t += 1
            self.levels_completed = 1
            return self._state

    receipt = mod._recover_level_boundary_seed(
        tmp_path,
        game_id="toy-game",
        cfg={"seed_recovery_steps": 3, "plan_depth": 2},
        adapter_factory=CompletesAfterOne,
    )

    assert receipt["status"] == "seed_recovered"
    seed = json.loads((tmp_path / "workspace" / "level2_seed.json").read_text())
    assert seed["full_sequence_from_reset"] == [0]
    assert seed["source"].startswith("strategy_seed_recovery:")
    assert "live environment confirmed" in receipt["authority"]


def test_seed_recovery_allows_bounded_patch_base_steering(tmp_path):
    from ztare.common.operator_proposal_contract import write_proposal_cards
    from ztare.worldmodel.adapter import episode_log_path
    from ztare.worldmodel.episode_log import EpisodeLog

    mod = _load_arc3_play_loop()
    submissions = tmp_path / "workspace" / "submissions"
    submissions.mkdir(parents=True)
    EpisodeLog().write_jsonl(episode_log_path(tmp_path))
    base = submissions / "base.py"
    base.write_text("def step(grid, action, t):\n    return grid\n")
    base_sha = hashlib.sha256(base.read_bytes()).hexdigest()
    wrapper = submissions / "wrapper.py"
    wrapper.write_text(
        "PATCH_BASE = {'source_ref': 'workspace/submissions/base.py', "
        f"'sha256': '{base_sha}'}}\n"
        "def PATCH_DELTA(base_next, state, action, t):\n"
        "    return base_next\n"
    )
    (tmp_path / "workspace" / "candidate_memory.json").write_text(json.dumps({
        "schema": "ztare-candidate-memory-v1",
        "records": [{
            "source_type": "deterministic_near_miss",
            "submission": "workspace/submissions/wrapper.py",
            "sha": "wrapper",
            "visible_exact_rows": 2,
            "visible_checked_rows": 2,
            "visible_wrong_cells": 0,
        }],
    }))
    write_proposal_cards(tmp_path / "workspace" / "strategy_experiments.jsonl", [{
        "schema": "strategy-experiment-v1",
        "kind": "compressed_counterexample_repair",
        "failure_family": "seed-recovery-test",
        "failure_family_sha": "seed-card",
        "rationale": "need seed",
        "falsifiable_prediction": "seed producer writes replayable seed",
        "action_plan": {
            "seed_prerequisite": {
                "seed_path": "workspace/level2_seed.json",
                "status": "replayable_seed_missing",
            },
            "required_next_gate": {
                "command": "recover_level_boundary_seed",
                "success_status": "replayable_boundary_seed_available",
            },
        },
        "kill_condition": "seed not recovered",
        "disposition": "open",
    }])

    class CompletesAfterOne:
        action_arity = 1
        def __init__(self, _game_id):
            self.levels_completed = 0
            self._state = ((0,),)
            self._t = 0
        def reset(self):
            self.levels_completed = 0
            self._state = ((0,),)
            self._t = 0
            return self._state
        @property
        def state(self):
            return self._state
        @property
        def t(self):
            return self._t
        def step(self, _action):
            self._t += 1
            self.levels_completed = 1
            return self._state

    receipt = mod._recover_level_boundary_seed(
        tmp_path,
        game_id="toy-game",
        cfg={
            "seed_recovery_steps": 3,
            "plan_depth": 2,
            "seed_recovery_patch_base_depth": 1,
        },
        adapter_factory=CompletesAfterOne,
    )

    assert receipt["status"] == "seed_recovered"
    assert receipt["attempts"][0]["patch_base_depth"] == 1
    assert receipt["composition_policy"]["seed_recovery_patch_base_depth"] == 1


def test_play_round_multilife_preserves_action_trace(monkeypatch):
    from types import SimpleNamespace

    mod = _load_arc3_play_loop()
    calls = []

    def fake_pursue_goal(_adapter, _model, max_steps, **_kw):
        calls.append(max_steps)
        return SimpleNamespace(
            status="goal_reached",
            steps_executed=3,
            levels_gained=1,
            saturated=False,
            observed_transitions=[],
            divergence=None,
            trace=[2, 1, 3],
        )

    monkeypatch.setattr(mod, "pursue_goal", fake_pursue_goal)
    pr = mod._play_round_multilife(
        object(), object(), budget=10, context_log=[], plan_depth=1)

    assert calls == [10]
    assert pr.levels_gained == 1
    assert pr.trace == [2, 1, 3]
    assert pr.task_discharged is False
    assert pr.legacy_boundary_stop is True
    assert pr.status == "environment_boundary"


def test_play_round_crosses_first_level_until_profile_task_discharge(monkeypatch):
    from types import SimpleNamespace
    from ztare.common.task_discharge import (
        TaskDischargeContract,
        TaskDischargeReceipt,
    )

    mod = _load_arc3_play_loop()
    class Adapter(SimpleNamespace):
        def adjudicate_task_discharge(self, contract):
            observed = int(self.levels_completed)
            discharged = observed >= int(contract.parameters["target"])
            return TaskDischargeReceipt(
                contract_sha256=contract.sha256,
                adjudicator_id=contract.adjudicator_id,
                status="discharged" if discharged else "open",
                authority="test_adapter",
                observed={"level_count": observed},
                evidence_refs=(f"test_level_count:{observed}",) if discharged else (),
            )

    adapter = Adapter(levels_completed=0)
    calls = []

    def fake_pursue_goal(active_adapter, _model, max_steps, **_kw):
        calls.append(max_steps)
        active_adapter.levels_completed += 1
        return SimpleNamespace(
            status="goal_reached",
            steps_executed=3 if len(calls) == 1 else 2,
            levels_gained=1,
            saturated=False,
            observed_transitions=[],
            divergence=None,
            trace=[len(calls)],
        )

    monkeypatch.setattr(mod, "pursue_goal", fake_pursue_goal)
    task_contract = TaskDischargeContract(
        contract_id="two-level-run",
        adjudicator_id="test.level_count.v1",
        lifecycle_scope="run",
        owner="test-profile",
        parameters={"target": 2},
    )
    pr = mod._play_round_multilife(
        adapter,
        object(),
        budget=10,
        context_log=[],
        task_contract=task_contract,
        plan_depth=1,
    )

    assert calls == [10, 7]
    assert pr.levels_gained == 2
    assert pr.steps_executed == 5
    assert pr.task_discharged is True
    assert pr.status == "task_discharged"
    assert pr.trace == [1, 2]


def test_play_round_accepts_task_discharge_without_level_delta(monkeypatch):
    from types import SimpleNamespace
    from ztare.common.task_discharge import (
        TaskDischargeContract,
        TaskDischargeReceipt,
    )

    mod = _load_arc3_play_loop()

    class Adapter(SimpleNamespace):
        def adjudicate_task_discharge(self, contract):
            return TaskDischargeReceipt(
                contract_sha256=contract.sha256,
                adjudicator_id=contract.adjudicator_id,
                status="discharged",
                authority="test_adapter",
                observed={"accepted": True},
                evidence_refs=("test:discharge",),
            )

    def should_not_play(*_args, **_kwargs):
        raise AssertionError("a discharged task must stop before another action")

    monkeypatch.setattr(mod, "pursue_goal", should_not_play)
    contract = TaskDischargeContract(
        contract_id="non-counter-task",
        adjudicator_id="test.acceptance.v1",
        lifecycle_scope="run",
        owner="test-profile",
    )
    pr = mod._play_round_multilife(
        Adapter(), object(), budget=5, context_log=[], task_contract=contract
    )

    assert pr.task_discharged is True
    assert pr.levels_gained == 0
    assert pr.status == "task_discharged"


def test_goal_hypothesis_identity_merges_intervention_presentations():
    from ztare.worldmodel.goal_abduction import compile_goal_hypothesis_set

    start = ((0, 0),)
    predicate = {"region": [0, 0, 0, 0], "differs_from_start": True}
    first = {"op": "region_event", "rect": [0, 0, 0, 0], "edge": "enter"}
    second = {"op": "region_event", "rect": [1, 0, 1, 0], "edge": "exit"}
    goals = compile_goal_hypothesis_set(
        [
            {"kind": "candidate", "predicate_spec": predicate, "experiment_specs": [first]},
            {"kind": "candidate", "predicate_spec": predicate, "experiment_specs": [second]},
        ],
        start,
    )

    assert goals.active_count == 1
    assert tuple(goals.experiments.values()) == ((first, second),)
    assert goals.projection_key(((1, 0),)) == goals.projection_key(((1, 99),))


def test_goal_hypothesis_compiler_replays_task_open_negative_evidence():
    from ztare.worldmodel.goal_abduction import compile_goal_hypothesis_set

    goals = compile_goal_hypothesis_set(
        [
            {
                "kind": "already_reached",
                "predicate_spec": {
                    "region": [0, 0, 0, 0],
                    "differs_from_start": True,
                },
            },
            {
                "kind": "unreached",
                "predicate_spec": {
                    "region": [0, 1, 0, 1],
                    "differs_from_start": True,
                },
            },
        ],
        ((0, 0),),
        task_open_states=(((1, 0),),),
        source_epoch=4,
        task_contract_sha256="a" * 64,
    )

    assert goals.active_count == 1
    assert goals.satisfied_ids(((1, 1),))
    assert goals.for_source_epoch(4) is goals
    assert goals.for_source_epoch(5) is None


def test_candidate_task_hypothesis_is_independent_of_carrier_promotion(tmp_path):
    import hashlib

    from ztare.worldmodel.goal_abduction import (
        compile_candidate_goal_hypothesis_set,
    )

    project = tmp_path / "project"
    submission = project / "workspace" / "submissions" / "candidate.py"
    submission.parent.mkdir(parents=True)
    source = "def GOAL_PREDICATE(observation):\n    return observation[0][0] == 1\n"
    submission.write_text(source)
    source_sha = hashlib.sha256(source.encode()).hexdigest()
    records = [{
        "source_type": "deterministic_near_miss",
        "submission": "workspace/submissions/candidate.py",
        "sha": source_sha,
        "evidence_epoch_sha256": "e" * 64,
        "observed_at_utc": "2026-07-18T00:00:00+00:00",
    }]

    goals = compile_candidate_goal_hypothesis_set(
        project,
        source_epoch=2,
        task_contract_sha256="a" * 64,
        witness_states=(((0,),), ((1,),)),
        records=records,
    )

    assert goals is not None
    assert goals.active_count == 1
    assert goals.for_source_epoch(2) is goals
    assert goals.for_source_epoch(3) is None
    assert goals(((1,),)) is True


def test_candidate_task_hypothesis_replays_task_open_negative_evidence(tmp_path):
    import hashlib

    from ztare.worldmodel.goal_abduction import (
        compile_candidate_goal_hypothesis_set,
    )

    project = tmp_path / "project"
    submission = project / "workspace" / "submissions" / "candidate.py"
    submission.parent.mkdir(parents=True)
    source = "def GOAL_PREDICATE(observation):\n    return observation[0][0] == 1\n"
    submission.write_text(source)
    records = [{
        "submission": "workspace/submissions/candidate.py",
        "sha": hashlib.sha256(source.encode()).hexdigest(),
        "evidence_epoch_sha256": "e" * 64,
    }]

    goals = compile_candidate_goal_hypothesis_set(
        project,
        source_epoch=2,
        task_contract_sha256="a" * 64,
        witness_states=(((0,),), ((1,),)),
        task_open_states=(((0,),), ((1,),)),
        records=records,
    )

    assert goals is not None
    assert goals.active_count == 0


def test_task_hypothesis_composition_unions_identities_and_experiments():
    from ztare.worldmodel.goal_abduction import (
        GoalHypothesisSet,
        compose_goal_hypothesis_sets,
    )

    first_rule = {"op": "region_event", "rect": [0, 0, 0, 0]}
    second_rule = {"op": "region_event", "rect": [0, 1, 0, 1]}
    first = GoalHypothesisSet(
        (("a", lambda state: state[0][0] == 1, "first", {}),),
        {"a": (first_rule,)},
        source_epoch=2,
        task_contract_sha256="c" * 64,
    )
    second = GoalHypothesisSet(
        (
            ("a", lambda state: state[0][0] == 1, "duplicate", {}),
            ("b", lambda state: state[0][1] == 1, "second", {}),
        ),
        {"a": (first_rule,), "b": (second_rule,)},
        source_epoch=2,
        task_contract_sha256="c" * 64,
    )
    first.refuted_ids.add("a")

    composed = compose_goal_hypothesis_sets(first, second)

    assert tuple(row[0] for row in composed.hypotheses) == ("a", "b")
    assert composed.active_count == 1
    assert composed.experiments == {"a": (first_rule,), "b": (second_rule,)}
    assert composed(((0, 1),)) is True


def test_task_hypothesis_composition_rejects_cross_chart_union():
    import pytest

    from ztare.worldmodel.goal_abduction import (
        GoalHypothesisSet,
        compose_goal_hypothesis_sets,
    )

    one = GoalHypothesisSet((), source_epoch=1, task_contract_sha256="a" * 64)
    two = GoalHypothesisSet((), source_epoch=2, task_contract_sha256="a" * 64)

    with pytest.raises(ValueError, match="lifecycle charts"):
        compose_goal_hypothesis_sets(one, two)


def test_task_hypothesis_turn_cannot_preempt_residual_frontier():
    source = (
        Path(__file__).resolve().parents[1]
        / "scripts/public/control/arc3_play_loop.py"
    ).read_text()
    task_turn = source[source.index("if (\n                abduced"):]
    task_turn = task_turn[:task_turn.index("):", task_turn.index("if ("))]

    assert "not configured_residual_frontier" in task_turn
    assert "not acquisition_only" in task_turn
    assert "active_count" in task_turn


def test_play_round_refutes_reached_goal_hypothesis_and_continues(monkeypatch):
    from types import SimpleNamespace
    from ztare.common.task_discharge import (
        TaskDischargeContract,
        TaskDischargeReceipt,
    )
    from ztare.worldmodel.goal_abduction import compile_goal_hypothesis_set

    mod = _load_arc3_play_loop()
    start = ((0, 0),)
    goals = compile_goal_hypothesis_set(
        [
            {"kind": "first", "predicate_spec": {"region": [0, 0, 0, 0], "differs_from_start": True}},
            {"kind": "second", "predicate_spec": {"region": [0, 1, 0, 1], "differs_from_start": True}},
        ],
        start,
    )

    class Adapter(SimpleNamespace):
        def adjudicate_task_discharge(self, contract):
            return TaskDischargeReceipt(
                contract_sha256=contract.sha256,
                adjudicator_id=contract.adjudicator_id,
                status="open",
                authority="test_adapter",
                observed={"accepted": False},
            )

    adapter = Adapter(state=start, levels_completed=0)
    calls = []

    def fake_pursue_goal(active_adapter, _model, max_steps, **kw):
        calls.append((max_steps, kw.get("goal_fn").active_count))
        active_adapter.state = (((1, 0),) if len(calls) == 1 else ((1, 1),))
        return SimpleNamespace(
            status="plan_exhausted",
            steps_executed=1,
            levels_gained=0,
            saturated=False,
            observed_transitions=[],
            divergence=None,
            trace=[len(calls)],
            planning_outcome={},
        )

    monkeypatch.setattr(mod, "pursue_goal", fake_pursue_goal)
    contract = TaskDischargeContract(
        contract_id="goal-version-space",
        adjudicator_id="test.acceptance.v1",
        lifecycle_scope="run",
        owner="test-profile",
    )
    pr = mod._play_round_multilife(
        adapter,
        object(),
        budget=2,
        context_log=[],
        task_contract=contract,
        goal_fn=goals,
    )

    assert calls == [(2, 2), (1, 1)]
    assert goals.active_count == 0
    assert [row["status"] for row in pr.leg_outcomes] == [
        "goal_hypothesis_refuted",
        "goal_hypothesis_refuted",
    ]
    assert pr.task_discharged is False


def test_play_round_refutes_only_reached_relational_goal_edge(monkeypatch):
    from types import SimpleNamespace

    from ztare.common.relational_task_contract import (
        EdgeTaskHypothesis,
        TaskHypothesisVersionSpace,
    )
    from ztare.common.task_discharge import (
        TaskDischargeContract,
        TaskDischargeReceipt,
    )
    from ztare.worldmodel.goal_abduction import (
        RelationalGoalEdgeHypothesisSet,
    )

    mod = _load_arc3_play_loop()
    hypotheses = TaskHypothesisVersionSpace(
        edge_hypotheses=(
            EdgeTaskHypothesis(
                "first",
                lambda _source, operation, descriptor: (
                    operation == 0 and descriptor == "first"
                ),
            ),
            EdgeTaskHypothesis(
                "second",
                lambda _source, operation, descriptor: (
                    operation == 1 and descriptor == "second"
                ),
            ),
        ),
        source_epoch=2,
        task_contract_sha256="c" * 64,
    )
    goals = RelationalGoalEdgeHypothesisSet(
        hypotheses=hypotheses,
        describe_edge=lambda _source, operation, _time: (
            "first" if operation == 0 else "second"
        ),
        descriptor_id="fixture.two-relations.v1",
    )

    class Adapter(SimpleNamespace):
        def adjudicate_task_discharge(self, contract):
            return TaskDischargeReceipt(
                contract_sha256=contract.sha256,
                adjudicator_id=contract.adjudicator_id,
                status="open",
                authority="test_adapter",
                observed={"accepted": False},
            )

    adapter = Adapter(
        state=((0,),),
        current_epoch=2,
        levels_completed=0,
        t=0,
    )
    calls = []

    def fake_pursue_goal(_adapter, _model, max_steps, **kw):
        active = kw["goal_edge_fn"]
        calls.append((
            max_steps,
            active.active_count,
            kw.get("control_task_contract_sha256"),
        ))
        operation = len(calls) - 1
        return SimpleNamespace(
            status="candidate_goal_edge_reached",
            steps_executed=1,
            levels_gained=0,
            saturated=False,
            observed_transitions=[],
            divergence=None,
            trace=[operation],
            planning_outcome={},
            candidate_goal_edge={
                "source": ((0,),),
                "operation": operation,
                "time": operation,
            },
        )

    monkeypatch.setattr(mod, "pursue_goal", fake_pursue_goal)
    contract = TaskDischargeContract(
        contract_id="relational-goal-version-space",
        adjudicator_id="test.acceptance.v1",
        lifecycle_scope="run",
        owner="test-profile",
    )
    receipt = mod._play_round_multilife(
        adapter,
        object(),
        budget=2,
        context_log=[],
        task_contract=contract,
        goal_edge_fn=goals,
    )

    assert calls == [
        (2, 2, contract.sha256),
        (1, 1, contract.sha256),
    ]
    assert goals.active_count == 0
    assert [row["status"] for row in receipt.leg_outcomes] == [
        "goal_hypothesis_refuted",
        "goal_hypothesis_refuted",
    ]
    assert receipt.task_discharged is False


def test_play_round_records_task_outcome_at_protocol_decision_boundary(
    tmp_path,
    monkeypatch,
):
    from types import SimpleNamespace

    from ztare.common.continual_skill_memory import (
        load_continual_skill_memory,
    )
    from ztare.common.task_discharge import (
        TaskDischargeContract,
        TaskDischargeReceipt,
    )

    mod = _load_arc3_play_loop()
    contract = TaskDischargeContract(
        contract_id="effect-option-outcome",
        adjudicator_id="test.effect-option.v1",
        lifecycle_scope="run",
        owner="test-profile",
    )

    class Adapter(SimpleNamespace):
        def adjudicate_task_discharge(self, active_contract):
            return TaskDischargeReceipt(
                contract_sha256=active_contract.sha256,
                adjudicator_id=active_contract.adjudicator_id,
                status="open",
                authority="test_adapter",
                observed={"epoch": self.current_epoch},
                evidence_refs=(),
            )

    seen_contracts = []

    def fake_pursue_goal(_adapter, _model, max_steps, **kw):
        seen_contracts.append(
            kw.get("control_task_contract_sha256")
        )
        return SimpleNamespace(
            status="plan_exhausted",
            steps_executed=1,
            levels_gained=0,
            saturated=False,
            observed_transitions=[],
            divergence=None,
            trace=[0],
            planning_outcome={
                "continual_control_process_tokens": [
                    "primitive:prepare",
                    "effect_option:advance",
                ],
                "task_decision_choice": {
                    "decision_namespace": "acquisition-protocols",
                    "choice_context_sha256": "choice-context-two",
                    "continuation_context_sha256": "controller-context",
                    "chosen_option_family_sha256": "advance",
                    "chosen_option_variant_sha256": (
                        "advance-context-two"
                    ),
                    "available_option_family_sha256s": [
                        "advance",
                        "detour",
                    ],
                },
            },
        )

    monkeypatch.setattr(mod, "pursue_goal", fake_pursue_goal)
    receipt = mod._play_round_multilife(
        Adapter(current_epoch=2),
        object(),
        budget=1,
        context_log=[],
        task_contract=contract,
        receipts_dir=tmp_path,
    )

    memory = load_continual_skill_memory(
        tmp_path / "continual_skill_memory.json"
    )
    assert seen_contracts == [contract.sha256]
    assert receipt.continual_task_experience["status"] == "recorded"
    assert receipt.continual_task_experience["outcome"] == "open"
    assert receipt.continual_task_experience[
        "effect_option_token_count"
    ] == 1
    assert receipt.continual_task_experience[
        "choice_experience_count"
    ] == 0
    assert receipt.continual_task_experience[
        "decision_experience_count"
    ] == 1
    assert len(memory.task_experiences) == 1
    assert len(memory.task_choice_experiences) == 0
    assert len(memory.task_decision_experiences) == 1
    assert memory.task_experiences[0].process_tokens == (
        "primitive:prepare",
        "effect_option:advance",
    )
    assert (
        memory.task_decision_experiences[0]
        .chosen_option_family_sha256
    ) == "advance"
    assert memory.credit_witnesses == ()


def test_multilife_rescopes_terminal_edge_at_each_epoch(monkeypatch):
    from types import SimpleNamespace
    from ztare.common.task_discharge import (
        TaskDischargeContract,
        TaskDischargeReceipt,
    )

    mod = _load_arc3_play_loop()

    class Adapter(SimpleNamespace):
        def adjudicate_task_discharge(self, contract):
            discharged = self.current_epoch >= int(contract.parameters["target"])
            return TaskDischargeReceipt(
                contract_sha256=contract.sha256,
                adjudicator_id=contract.adjudicator_id,
                status="discharged" if discharged else "open",
                authority="test_adapter",
                observed={"epoch": self.current_epoch},
                evidence_refs=(f"epoch:{self.current_epoch}",) if discharged else (),
            )

    class EpochEdge:
        def for_source_epoch(self, epoch):
            return f"edge-for-{epoch}" if epoch == 0 else None

    adapter = Adapter(current_epoch=0)
    seen_edges = []

    def fake_pursue_goal(active_adapter, _model, max_steps, **kw):
        seen_edges.append(kw.get("goal_edge_fn"))
        if len(seen_edges) == 1:
            active_adapter.current_epoch = 1
            return SimpleNamespace(
                status="goal_reached",
                steps_executed=1,
                levels_gained=1,
                saturated=False,
                observed_transitions=[],
                divergence=None,
                trace=[0],
            )
        return SimpleNamespace(
            status="plan_exhausted",
            steps_executed=1,
            levels_gained=0,
            saturated=False,
            observed_transitions=[],
            divergence=None,
            trace=[1],
        )

    monkeypatch.setattr(mod, "pursue_goal", fake_pursue_goal)
    contract = TaskDischargeContract(
        contract_id="epoch-scoped-run",
        adjudicator_id="test.epoch.v1",
        lifecycle_scope="run",
        owner="test-profile",
        parameters={"target": 2},
    )
    mod._play_round_multilife(
        adapter,
        object(),
        budget=2,
        context_log=[],
        task_contract=contract,
        goal_edge_fn=EpochEdge(),
    )

    assert seen_edges == ["edge-for-0", None]


def test_play_round_does_not_relabel_environment_reset_as_law_divergence(monkeypatch):
    from types import SimpleNamespace

    mod = _load_arc3_play_loop()
    calls = []
    exclusions = []
    boundary_edges = []

    def fake_pursue_goal(_adapter, _model, max_steps, **kw):
        calls.append(max_steps)
        exclusions.append(kw.get("excluded_edge_fn"))
        boundary_edges.append(tuple(kw.get("control_boundary_edges") or ()))
        if len(calls) == 1:
            return SimpleNamespace(
                status="model_diverged",
                steps_executed=1,
                levels_gained=0,
                saturated=False,
                observed_transitions=[("before", 0, "reset", 7)],
                divergence={"terminal_witness": {"sha256": "boundary"}},
                trace=[0],
            )
        return SimpleNamespace(
            status="plan_exhausted",
            steps_executed=1,
            levels_gained=0,
            saturated=False,
            observed_transitions=[],
            divergence=None,
            trace=[1],
        )

    monkeypatch.setattr(mod, "pursue_goal", fake_pursue_goal)
    monkeypatch.setattr(mod, "_is_env_reset", lambda _context, _obs: True)
    pr = mod._play_round_multilife(
        object(), object(), budget=2, context_log=[], plan_depth=1)

    assert calls == [2, 1]
    assert pr.lives == 2
    assert pr.status == "plan_exhausted"
    assert pr.divergence is None
    assert mod._transition_model_mismatch(pr) is False
    assert pr.leg_outcomes[0]["status"] == "environment_boundary_inferred"
    assert "adapter-unclassified repaint" in pr.leg_outcomes[0]["detail"]
    assert exclusions[0] is None
    assert exclusions[1]("before", 0, 99) is True
    assert exclusions[1]("before", 1, 99) is False
    assert boundary_edges[0] == ()
    assert boundary_edges[1][0][:2] == ("before", 0)
    assert boundary_edges[1][0][2].startswith(
        "arc3_play_loop:active_control_boundary#"
    )
    assert pr.non_discharge_edge_count == 1


def test_play_round_replans_across_exact_known_context_transition(monkeypatch):
    from types import SimpleNamespace

    from ztare.worldmodel.episode_log import EpisodeLog, Transition
    from ztare.worldmodel.transition_identity import TransitionIdentity

    mod = _load_arc3_play_loop()
    identity = TransitionIdentity(
        kind="dynamics",
        authority="environment_adapter",
        source_epoch=2,
        target_epoch=2,
    )
    transition = Transition(
        9,
        ((1,),),
        0,
        ((2,),),
        identity,
    )
    calls = []

    def fake_pursue_goal(_adapter, _model, max_steps, **kw):
        calls.append((
            max_steps,
            kw.get("excluded_edge_fn"),
            tuple(kw.get("control_boundary_edges") or ()),
            tuple(kw.get("control_history_prefix") or ()),
        ))
        if len(calls) == 1:
            return SimpleNamespace(
                status="model_diverged",
                steps_executed=1,
                levels_gained=0,
                saturated=False,
                observed_transitions=[transition],
                divergence={"terminal_witness": {"sha256": "repaint"}},
                trace=[0],
            )
        return SimpleNamespace(
            status="plan_exhausted",
            steps_executed=1,
            levels_gained=0,
            saturated=False,
            observed_transitions=[],
            divergence=None,
            trace=[1],
        )

    monkeypatch.setattr(mod, "pursue_goal", fake_pursue_goal)
    monkeypatch.setattr(mod, "_is_env_reset", lambda _context, _obs: True)
    adapter = SimpleNamespace(current_epoch=2)
    receipt = mod._play_round_multilife(
        adapter,
        object(),
        budget=2,
        context_log=EpisodeLog([transition]),
        control_history_prefix=(7,),
    )

    assert receipt.leg_outcomes[0]["status"] == (
        "environment_context_transition_inferred"
    )
    assert receipt.non_discharge_edge_count == 0
    assert receipt.divergence is None
    assert calls[1][1] is None
    assert calls[1][2] == ()
    assert calls[1][3] == ()


def test_play_round_transports_repeated_non_discharge_over_support_fiber(monkeypatch):
    from types import SimpleNamespace

    mod = _load_arc3_play_loop()
    sources = [((0, 7),), ((0, 8),), ((0, 9),)]
    calls = []

    def fake_pursue_goal(_adapter, _model, max_steps, **kw):
        exclusion = kw.get("excluded_edge_fn")
        calls.append((max_steps, exclusion))
        if len(calls) == 2:
            assert exclusion(sources[0], 0, 50) is True
            assert exclusion(sources[1], 0, 50) is False
        if len(calls) == 3:
            assert exclusion(sources[2], 0, 50) is True
            return SimpleNamespace(
                status="plan_exhausted",
                steps_executed=0,
                levels_gained=0,
                saturated=False,
                observed_transitions=[],
                divergence=None,
                trace=[],
            )
        source = sources[len(calls) - 1]
        return SimpleNamespace(
            status="model_diverged",
            steps_executed=1,
            levels_gained=0,
            saturated=False,
            observed_transitions=[(source, 0, "reset", len(calls))],
            divergence={"terminal_witness": {"sha256": f"boundary-{len(calls)}"}},
            trace=[0],
        )

    monkeypatch.setattr(mod, "pursue_goal", fake_pursue_goal)
    monkeypatch.setattr(mod, "_is_env_reset", lambda _context, _obs: True)
    pr = mod._play_round_multilife(
        object(),
        object(),
        budget=3,
        context_log=[],
        abstract_fn=lambda state: state[0][0],
        coverage_fn=lambda identity: identity,
    )

    assert len(calls) == 3
    assert pr.non_discharge_edge_count == 2
    assert pr.non_discharge_projection_count == 1
    assert pr.status == "plan_exhausted"


def test_play_round_excludes_boundary_predecessor_not_following_reset(monkeypatch):
    from types import SimpleNamespace
    from ztare.worldmodel.episode_log import Transition
    from ztare.worldmodel.transition_identity import TransitionIdentity

    mod = _load_arc3_play_loop()
    predecessor = ((1,),)
    reset_source = ((2,),)
    boundary = TransitionIdentity(
        kind="epoch_boundary",
        authority="environment_adapter",
        source_epoch=2,
        target_epoch=3,
        boundary_kind="task_open_terminal",
    )
    reset = TransitionIdentity(
        kind="reset_boundary",
        authority="environment_adapter",
        source_epoch=3,
        target_epoch=4,
        boundary_kind="reset_after_terminal",
    )
    calls = []

    def fake_pursue_goal(_adapter, _model, max_steps, **kw):
        calls.append(kw.get("excluded_edge_fn"))
        if len(calls) == 1:
            return SimpleNamespace(
                status="environment_boundary",
                steps_executed=2,
                levels_gained=0,
                saturated=False,
                observed_transitions=[
                    Transition(5, predecessor, 1, reset_source, boundary),
                    Transition(6, reset_source, 3, ((3,),), reset),
                ],
                divergence=None,
                trace=[1, 3],
            )
        assert calls[-1](predecessor, 1, 99) is True
        assert calls[-1](reset_source, 3, 99) is False
        return SimpleNamespace(
            status="plan_exhausted",
            steps_executed=0,
            levels_gained=0,
            saturated=False,
            observed_transitions=[],
            divergence=None,
            trace=[],
        )

    monkeypatch.setattr(mod, "pursue_goal", fake_pursue_goal)
    pr = mod._play_round_multilife(
        object(), object(), budget=3, context_log=[]
    )

    assert pr.non_discharge_edge_indices == [0]
    assert pr.non_discharge_edge_count == 1


def test_play_loop_mismatch_fields_separate_transition_from_terminal():
    from types import SimpleNamespace

    mod = _load_arc3_play_loop()
    ordinary = SimpleNamespace(divergence={"terminal_witness": {"sha256": "abc"}},
                               levels_gained=0)
    terminal = SimpleNamespace(divergence={"terminal_witness": {"sha256": "def"}},
                               levels_gained=1)

    assert mod._transition_model_mismatch(ordinary) is True
    assert mod._terminal_model_mismatch(ordinary) is False
    assert mod._transition_model_mismatch(terminal) is True
    assert mod._terminal_model_mismatch(terminal) is True


def test_abduced_core_receipt_quotients_duplicate_residuals(tmp_path):
    from types import SimpleNamespace

    mod = _load_arc3_play_loop()
    transitions = [
        SimpleNamespace(s=[[0]], a=1, t=7, s_next=[[2]]),
        SimpleNamespace(s=[[0]], a=1, t=8, s_next=[[2]]),
        SimpleNamespace(s=[[0]], a=2, t=9, s_next=[[3]]),
    ]

    def step(_s, a, _t):
        return [[1]] if a == 1 else [[4]]

    ab = SimpleNamespace(spec={"always": []}, step_fn=step)
    (tmp_path / "workspace").mkdir()
    mod._write_abduced_core_receipt(tmp_path, transitions, ab)
    receipt = json.loads((tmp_path / "workspace" / "abduced_core.json").read_text())

    assert receipt["matched_transitions"] == 0
    assert receipt["residual_class_count"] == 2
    assert receipt["residuals"][0]["count"] == 2
    assert receipt["residuals"][0]["t_values"] == [7, 8]
    assert receipt["residuals"][0]["t_value_count"] == 2


def test_level_boundary_seed_snapshot_binds_seed_bytes(tmp_path):
    from ztare.worldmodel.level_boundary_seed import (
        load_seed,
        seed_receipt_fields,
        snapshot_seed,
    )

    project = tmp_path / "proj"
    seed_path = project / "workspace" / "level2_seed.json"
    seed_path.parent.mkdir(parents=True)
    seed_path.write_text(json.dumps({
        "schema": "ztare-level-boundary-seed-v1",
        "full_sequence_from_reset": [0, 2, 1],
    }))

    _seed, sequence, raw, sha = load_seed(seed_path)
    ref = snapshot_seed(project, raw, sha)
    fields = seed_receipt_fields(
        project=project,
        seed_path=seed_path,
        raw_seed=raw,
        seed_sha256=sha,
    )

    assert sequence == [0, 2, 1]
    assert ref == f"workspace/level_boundary_seeds/{sha}.json"
    assert fields["seed_sha256"] == sha
    assert fields["seed_snapshot_ref"] == ref
    assert (project / ref).read_bytes() == raw


def test_strategy_battery_reads_play_loop_report_role_bindings(tmp_path):
    from ztare.worldmodel.strategy_battery import WorldmodelBattery
    proj = _mini_worldmodel_project(tmp_path)
    (proj / "workspace").mkdir(exist_ok=True)
    (proj / "workspace" / "arc3_play_loop_report.json").write_text(json.dumps({
        "cycles": [{
            "kernel_role_bindings": [{
                "term": "planner_goal_cue_absent",
                "roles": ["search_control", "selection", "model_update"],
                "evidence": "exact model exhausted planning with no cue",
            }]
        }]
    }))
    out = WorldmodelBattery().query_menu()["semantic_deanchor"][1](proj, top=3)
    assert out["method"] == "typed_kernel_role_binding"
    assert out["suspects"][0]["term"] == "planner_goal_cue_absent"


def test_strategy_battery_surfaces_planner_attention_pressure(tmp_path):
    from ztare.worldmodel.strategy_battery import WorldmodelBattery
    proj = _mini_worldmodel_project(tmp_path)
    (proj / "workspace").mkdir(exist_ok=True)
    (proj / "workspace" / "arc3_play_loop_report.json").write_text(json.dumps({
        "cycles": [
            {
                "cycle": 1,
                "pursuit": "plan_exhausted",
                "steps": 250,
                "levels_gained": 0,
                "evidence_grown_by": 0,
                "played": "candidate",
                "planning_outcome": {
                    "policy": "bounded_terminal_search",
                    "status": "no_plan_within_bound",
                    "factored_predecessor": {
                        "policy": "factored_goal_experiment",
                        "status": "search_budget_exhausted",
                    },
                },
            },
            {
                "cycle": 2,
                "pursuit": "goal_reached",
                "steps": 12,
                "levels_gained": 1,
            },
        ]
    }))

    dossier = WorldmodelBattery().run_audits(proj)
    pressure = dossier["planner_attention_pressure"]

    assert pressure["firing_signal"] > 0
    assert pressure["anomalies"][0]["anomaly_class"] == (
        "plan_exhausted_without_task_progress_or_new_evidence"
    )
    assert "override gates" in pressure["rule"]


def test_strategy_battery_surfaces_loop_control_scheduler_pressure(tmp_path):
    from ztare.worldmodel.strategy_battery import WorldmodelBattery
    proj = _mini_worldmodel_project(tmp_path)
    (proj / "workspace").mkdir(exist_ok=True)
    (proj / "workspace" / "latest_information_yield.json").write_text(json.dumps({
        "signal": {
            "iteration_index": 1,
            "score": 0,
            "weakest_point": (
                "Runner R1 rejection: PATCH_BASE_IMPROVEMENT_PRECHECK: "
                "candidate must strictly improve the best deterministic near-miss"
            ),
            "mutation_r1_mismatch": True,
        },
        "decision": {
            "action": "REFRESH_SPECIALISTS",
            "stagnant_window": 1,
            "rationale": "Latest iteration failed R1 declaration validation",
        },
    }))

    dossier = WorldmodelBattery().run_audits(proj)
    pressure = dossier["loop_control_pressure"]

    assert pressure["firing_signal"] > 0
    anomaly = pressure["anomalies"][0]
    assert anomaly["anomaly_class"] == "scheduler_counterexample"
    assert set(anomaly["scheduler_tags"]) >= {
        "r1_declaration_mismatch",
        "patch_base_no_improvement",
    }
    assert "do not certify a candidate" in pressure["rule"]


def test_search_control_repair_card_written_from_planner_pressure(tmp_path):
    from ztare.worldmodel.search_control_repair import write_search_control_repair_card
    proj = _mini_worldmodel_project(tmp_path)
    (proj / "workspace").mkdir(exist_ok=True)
    (proj / "workspace" / "arc3_play_loop_report.json").write_text(json.dumps({
        "cycles": [
            {
                "cycle": 1,
                "pursuit": "plan_exhausted",
                "steps": 250,
                "levels_gained": 0,
                "evidence_grown_by": 0,
                "played": "candidate",
                "planning_outcome": {
                    "policy": "bounded_terminal_search",
                    "status": "no_plan_within_bound",
                    "factored_predecessor": {
                        "policy": "factored_goal_experiment",
                        "status": "search_budget_exhausted",
                    },
                },
            }
        ]
    }))

    written = write_search_control_repair_card(proj)
    written_again = write_search_control_repair_card(proj)

    assert len(written) == 1
    assert written_again == []
    card = written[0]
    assert card["kind"] == "search_control_residue_repair"
    plan = card["action_plan"]
    assert plan["residue_quotient"]["residue_class"] == (
        "closed_dynamics_no_terminal_progress"
    )
    assert plan["routing_class"] == "target_synthesis_or_discriminating_probe"
    assert plan["planning_outcome"]["factored_predecessor"]["policy"] == (
        "factored_goal_experiment"
    )
    assert plan["discriminator_axis"]["axis"] == (
        "target_specification_gap_vs_transition_model_gap"
    )
    assert "failed broad sweeps" in plan["discriminator_axis"]["class_invariant"]
    assert plan["required_next_gate"]["success_status"] == (
        "terminal_event_or_new_evidence_or_more_specific_strategy_receipt"
    )


def test_strategy_office_convene_query_round_then_commits(tmp_path):
    from ztare.research_director import strategy_office as so
    from ztare.worldmodel.strategy_battery import WorldmodelBattery
    proj = _mini_worldmodel_project(tmp_path)

    prompts = []
    replies = iter([
        '{"queries": [{"name": "novelty_decay", "params": {"k": 2}}]}',
        '{"experiments": [{"kind": "reachability_sweep_to_goal", '
        '"rationale": "novelty decayed", "falsifiable_prediction": "reaches goal", '
        '"action_plan": {"paths": [[0, 1]]}, "kill_condition": "no progress"}]}',
    ])

    def mock_leaf(prompt):
        prompts.append(prompt)
        return next(replies)

    written = so.convene(proj, WorldmodelBattery(), leaf_fn=mock_leaf,
                         judge_model="claude-sonnet-4-6", mutator_model="gpt-5.5")
    assert len(written) == 1 and written[0]["kind"] == "reachability_sweep_to_goal"
    # the harness ran the menu query and re-dispatched with the results
    assert len(prompts) == 2
    assert "QUERY RESULTS" in prompts[1]
    # cards persisted to the ledger
    ledger = proj / "workspace" / so.STRATEGY_LEDGER
    assert ledger.exists() and ledger.read_text().strip()
    # commissioning attestation + async handoff written
    import json as _json
    pend = _json.loads((proj / "workspace" / so.PENDING_FILENAME).read_text())
    assert pend["n_cards_written"] == 1
    # I2: gpt-5.5 leaf collides with the gpt-5.5 mutator — the attestation
    # records the collision rather than silently claiming independence.
    assert pend["cross_family"]["separated"] is False
    assert "mutator(gpt)" in pend["cross_family"]["collision"]
    assert pend["attestation"]["outcome"] == "commissioned"


def test_strategy_office_round_cap_emits_meta_card(tmp_path):
    from ztare.research_director import strategy_office as so
    from ztare.worldmodel.strategy_battery import WorldmodelBattery
    proj = _mini_worldmodel_project(tmp_path)

    def always_query(prompt):
        return '{"queries": [{"name": "open_cards", "params": {}}]}'

    written = so.convene(proj, WorldmodelBattery(), leaf_fn=always_query,
                         max_query_rounds=2)
    assert len(written) == 1 and written[0]["kind"] == "meta"
    assert "escalate" in written[0]["rationale"]


def test_strategy_office_cards_dedup(tmp_path):
    from ztare.research_director import strategy_office as so
    from ztare.worldmodel.strategy_battery import WorldmodelBattery
    proj = _mini_worldmodel_project(tmp_path)
    exp = ('{"experiments": [{"kind": "coverage_gap_probe", "rationale": "hole", '
           '"falsifiable_prediction": "p", "action_plan": {"paths": [[1]]}, '
           '"kill_condition": "k"}]}')
    b = WorldmodelBattery()
    w1 = so.convene(proj, b, leaf_fn=lambda p: exp)
    w2 = so.convene(proj, b, leaf_fn=lambda p: exp)
    assert len(w1) == 1 and len(w2) == 0                  # identical experiment deduped


def test_strategy_decision_policy_local_majority_approves(tmp_path):
    from ztare.research_director.strategy_decision_policy import (
        DECISION_LATEST,
        decide_strategy_card_batch,
    )

    proj = _mini_worldmodel_project(tmp_path)
    cards = [{
        "schema": "strategy-experiment-v1",
        "failure_family": "kind|{}",
        "kind": "coverage_gap_probe",
        "rationale": "hole",
        "falsifiable_prediction": "p",
        "action_plan": {},
        "kill_condition": "k",
        "disposition": "open",
    }]

    receipt = decide_strategy_card_batch(
        project_dir=proj,
        cards=cards,
        policy="majority",
        backend="local",
        positions=[
            {"actor_id": "agent.a", "role_id": "role.a", "position": "approve", "rationale": "a"},
            {"actor_id": "agent.b", "role_id": "role.b", "position": "approve", "rationale": "b"},
            {"actor_id": "agent.c", "role_id": "role.c", "position": "reject", "rationale": "c"},
        ],
        persist=True,
    )

    assert receipt["recommendation"] == "approve"
    assert receipt["approved_cards"] == cards
    assert receipt["counts"]["approve"] == 2
    assert (proj / "workspace" / DECISION_LATEST).exists()


def test_strategy_office_convene_can_use_decision_policy(tmp_path):
    from ztare.research_director import strategy_office as so
    from ztare.worldmodel.strategy_battery import WorldmodelBattery

    proj = _mini_worldmodel_project(tmp_path)
    exp = ('{"experiments": [{"kind": "coverage_gap_probe", "rationale": "hole", '
           '"falsifiable_prediction": "p", "action_plan": {"paths": [[1]]}, '
           '"kill_condition": "k"}]}')

    written = so.convene(
        proj,
        WorldmodelBattery(),
        leaf_fn=lambda _p: exp,
        decision_policy="majority",
        decision_backend="local",
        decision_positions=[
            {"actor_id": "agent.a", "role_id": "role.a", "position": "approve", "rationale": "a"},
            {"actor_id": "agent.b", "role_id": "role.b", "position": "approve", "rationale": "b"},
        ],
    )

    assert len(written) == 1
    pend = json.loads((proj / "workspace" / so.PENDING_FILENAME).read_text())
    assert pend["strategy_decision"]["policy"] == "majority"
    assert pend["strategy_decision"]["recommendation"] == "approve"
    assert (proj / "workspace" / "strategy_decision_receipts.jsonl").exists()


def test_strategy_office_rejects_unlowerable_cards_with_retry_then_records_rejection(tmp_path):
    from ztare.research_director import strategy_office as so
    from ztare.worldmodel.strategy_battery import WorldmodelBattery

    proj = _mini_worldmodel_project(tmp_path)
    replies = iter([
        '{"experiments": [{"kind": "reachability_sweep_to_goal", "rationale": "hole", '
        '"falsifiable_prediction": "p", "action_plan": {"paths": [], "goal_predicate_spec": {}}, '
        '"kill_condition": "k"}]}',
        '{"experiments": [{"kind": "reachability_sweep_to_goal", "rationale": "hole", '
        '"falsifiable_prediction": "p", "action_plan": {"paths": [], "goal_predicate_spec": {}}, '
        '"kill_condition": "k"}]}',
    ])

    written = so.convene(proj, WorldmodelBattery(), leaf_fn=lambda _p: next(replies))

    assert len(written) == 1
    assert written[0]["disposition"] == "rejected_unlowerable"
    rows = [json.loads(line) for line in (proj / "workspace" / so.STRATEGY_LEDGER).read_text().splitlines()]
    assert rows[0]["disposition"] == "rejected_unlowerable"
    assert rows[0]["rejection_reason"] == "action_plan is not lowerable by experiment_executor"
    pend = json.loads((proj / "workspace" / so.PENDING_FILENAME).read_text())
    assert pend["n_cards_written"] == 1


def test_strategy_office_prompt_includes_registry_example_and_lowerability_receipt(tmp_path):
    from ztare.research_director import strategy_office as so
    from ztare.worldmodel.strategy_battery import WorldmodelBattery

    proj = _mini_worldmodel_project(tmp_path)
    dossier = WorldmodelBattery().run_audits(proj)
    prompt = so._build_prompt(
        so.render_dossier(dossier, WorldmodelBattery().query_menu(), list(WorldmodelBattery().experiment_kinds())),
        ["=== LOWERABILITY REJECTION RECEIPT ===\n{\"disposition\": \"rejected_unlowerable\", \"rejection_reason\": \"action_plan is not lowerable\", \"action_plan\": {\"paths\": []}}"],
        rounds_left=1,
    )

    assert "=== PROBE REGISTRY ===" in prompt
    assert "- reachability_sweep_to_goal: action_plan required fields = [goal_predicate_spec]" in prompt
    assert "- carrier_repair_probe: action_plan required fields = [repair_carrier, target_residual_class]" in prompt
    assert "=== WORKED EXAMPLE (FORM ONLY) ===" in prompt
    assert '"source_artifact": "workspace/probe_paths.py"' in prompt
    assert "=== LOWERABILITY REJECTION RECEIPT ===" in prompt
    assert "\"rejection_reason\": \"action_plan is not lowerable\"" in prompt
    assert "Reply with STRICT JSON" not in prompt
    assert "The response format is STRICT JSON and nothing else." in prompt


def test_strategy_path_probe_reuses_requested_prefixes():
    from ztare.worldmodel.experiment_executor import _maximal_action_paths

    covered = _maximal_action_paths([[0], [1], [0, 1], [1, 0], [2]])
    assert [(path, indices) for _index, path, indices in covered] == [
        ((0, 1), (0, 2)),
        ((1, 0), (1, 3)),
        ((2,), (4,)),
    ]


def test_experiment_executor_carrier_repair_probe_survives_and_kills_with_witness(tmp_path, monkeypatch):
    import types

    from ztare.common.operator_proposal_contract import write_proposal_cards
    from ztare.worldmodel import experiment_executor as ee

    proj = _mini_worldmodel_project(tmp_path)
    ws = proj / "workspace"
    ws.mkdir(exist_ok=True)
    prior = ws / "submissions" / "prior_carrier.py"
    prior.parent.mkdir(parents=True, exist_ok=True)
    prior.write_text(
        "def step(grid, action, t):\n"
        "    return grid\n",
        encoding="utf-8",
    )
    current = ws / "submissions" / "current_carrier.py"
    current.write_text(
        "def step(grid, action, t):\n"
        "    return grid\n",
        encoding="utf-8",
    )
    write_json = {
        "schema": "operator-proposal-v1",
        "failure_family": "ff",
        "kind": "carrier_repair_probe",
        "rationale": "repair the carrier",
        "falsifiable_prediction": "carrier improves",
        "action_plan": {"repair_carrier": "workspace/submissions/current_carrier.py", "target_residual_class": "class-a"},
        "kill_condition": "candidate does not strictly improve on both legs",
        "disposition": "open",
    }
    survivor_card = dict(write_json)
    survivor_card["failure_family"] = "ff-survivor"
    survivor_card["action_plan"] = {"repair_carrier": "workspace/submissions/prior_carrier.py", "target_residual_class": "class-a"}
    written = write_proposal_cards(ws / "strategy_experiments.jsonl", [write_json, survivor_card])
    sha = written[0]["failure_family_sha"]
    survivor_sha = written[1]["failure_family_sha"]

    prior_path = prior.resolve()
    candidate_calls = []

    def fake_preflight(*, enabled, project_dir, candidate_path, **_kwargs):
        candidate_calls.append(Path(candidate_path))
        if Path(candidate_path) == prior_path:
            return None
        return types.SimpleNamespace(
            regression_receipt={
                "candidate_relation": "no_strict_improvement",
                "candidate_exact_rows": 3,
                "candidate_holdout_depth": 4,
                "best_prior_exact_rows": 3,
                "best_prior_holdout_depth": 4,
                "first_mismatch": "row 1",
                "holdout_witness": {"row": 1, "col": 2},
            },
            counterexample_trace={"holdout_witness": {"row": 1, "col": 2}},
        )

    monkeypatch.setattr(ee, "detect_patch_base_regression_preflight", fake_preflight)

    result = ee.execute_experiments(proj, card_sha=sha)
    assert result["processed"] == 1
    assert result["receipts"][0]["disposition"] == "killed"
    assert result["receipts"][0]["outcome_status"] == "blocked"

    result = ee.execute_experiments(proj, card_sha=survivor_sha)
    assert result["receipts"][0]["disposition"] == "survived"
    assert candidate_calls[0].name == "current_carrier.py"
    assert candidate_calls[1].name == "prior_carrier.py"
    assert (ws / "strategy_experiment_executions.jsonl").exists()
    assert (ws / "strategy_experiment_probe_rows.jsonl").exists()


def test_strategy_office_should_convene_gated_and_probabilistic():
    from ztare.research_director.strategy_office import should_convene
    hot = {"firing_signal": 0.95}
    # disabled by default
    assert should_convene(hot, rounds_since_last=5, rubric_data={}) is False
    rd = {"enable_strategy_office": True}
    # rng=0.0 always fires when enabled + pressure present; adjacent cycle blocked
    class _Z:
        @staticmethod
        def random():
            return 0.0
    assert should_convene(hot, rounds_since_last=0, rubric_data=rd, rng=_Z) is False
    assert should_convene(hot, rounds_since_last=2, rubric_data=rd, rng=_Z) is True


def test_strategy_office_dry_run_cli(tmp_path, capsys):
    from ztare.research_director import strategy_office as so
    proj = _mini_worldmodel_project(tmp_path)
    rc = so.main(["--project", str(proj), "--dry-run"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "DETERMINISTIC RECEIPTS DOSSIER" in out
    assert "QUERY MENU" in out and "EXPERIMENT KINDS" in out
    assert "no LLM dispatched" in out
    # dry-run writes NO cards
    assert not (proj / "workspace" / so.STRATEGY_LEDGER).exists()


def test_adjudicate_leaf_proposals_persists_dispositions_digest_and_counters(tmp_path, monkeypatch):
    from ztare.common.operator_proposal_contract import open_cards
    from ztare.research_director import strategy_office as so

    proj = _mini_worldmodel_project(tmp_path)
    ws = proj / "workspace"
    ws.mkdir(exist_ok=True)
    from ztare.research_director.strategy_office import _proposal_signature
    sig_a = _proposal_signature({
        "proposed_change": "add query affordance",
        "expected_number_moved": {"interventions": -1},
        "certifier_touched": False,
    })
    sig_b = _proposal_signature({
        "proposed_change": "tighten certifier gate",
        "expected_number_moved": {"closure": 1},
        "certifier_touched": True,
    })
    ledger = ws / "leaf_proposals.jsonl"
    ledger.write_text("\n".join([
        json.dumps({
            "proposal_signature": sig_a,
            "proposal": {
                "proposed_change": "add query affordance",
                "expected_number_moved": {"interventions": -1},
                "certifier_touched": False,
            },
            "submitted_leaf_model": "gpt-5.5",
            "disposition": "open",
        }),
        json.dumps({
            "proposal_signature": sig_a,
            "proposal": {
                "proposed_change": "add query affordance",
                "expected_number_moved": {"interventions": -1},
                "certifier_touched": False,
            },
            "submitted_leaf_model": "gpt-5.5",
            "disposition": "open",
        }),
        json.dumps({
            "proposal_signature": sig_b,
            "proposal": {
                "proposed_change": "tighten certifier gate",
                "expected_number_moved": {"closure": 1},
                "certifier_touched": True,
            },
            "submitted_leaf_model": "gpt-5.5",
            "disposition": "open",
        }),
        json.dumps({
            "category": "process_health",
            "provenance": "trace_auditor",
            "check_id": "organ_liveness",
            "proposed_change": "global catalog advisory",
            "disposition": "open",
        }),
    ]) + "\n", encoding="utf-8")
    open_ledger = ws / "strategy_experiments.jsonl"
    open_ledger.write_text(json.dumps({
        "schema": "strategy-experiment-v1",
        "kind": "compressed_counterexample_repair",
        "failure_family": "open family",
        "action_plan": {"proposed_change": "add query affordance", "expected_number_moved": {"interventions": -1}},
        "disposition": "open",
    }) + "\n", encoding="utf-8")
    monkeypatch.setattr(so, "_sealed_leaf_adjudicator", lambda *_a, **_k: (lambda _p, proposal: {"accepted": True, "rule_citations": ["Rule 2"], "reason": f"strict improvement: {proposal['proposed_change']}"}))
    monkeypatch.setattr(so, "_sealed_leaf_dissent_adjudicator", lambda *_a, **_k: (lambda _p, _proposal: {"accepted": True, "rule_citations": [], "reason": "no dissent: strongest counter-case fails"}))

    receipt = so.adjudicate_leaf_proposals(proj, sealed_leaf_model="claude-3.5", judge_model="gpt-4o", mutator_model="gpt-4o")

    assert receipt["status"] == "ok"
    assert receipt["approved"] == 1
    assert receipt["rejected"] == 1
    rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
    assert any(row["disposition"] == "accepted" for row in rows)
    assert any(row["disposition"] == "rejected" for row in rows)
    process_rows = [row for row in rows if row.get("check_id") == "organ_liveness"]
    assert len(process_rows) == 1
    assert process_rows[0]["disposition"] == "open"
    digest = json.loads((ws / "leaf_proposals_digest.json").read_text(encoding="utf-8"))
    assert digest["excluded_process_health_rows"] == 1
    assert not any(row.get("check_id") == "organ_liveness" for row in digest["last_k"])
    assert digest["counters"]["leaf_originated_adopted"] == 1
    counters = json.loads((ws / "leaf_proposal_adoption_counters.json").read_text(encoding="utf-8"))
    assert counters["leaf_originated_adopted"] == 1
    assert len(open_cards(open_ledger)) == 1


def test_adjudicate_leaf_proposals_committee_paths(tmp_path, monkeypatch):
    from ztare.research_director import strategy_office as so

    proj = _mini_worldmodel_project(tmp_path)
    ws = proj / "workspace"
    ws.mkdir(exist_ok=True)
    ledger = ws / "leaf_proposals.jsonl"
    ledger.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "proposal_signature": "sig-approve",
                        "proposal": {
                            "proposed_change": "add query affordance",
                            "expected_number_moved": {"interventions": -1},
                            "certifier_touched": False,
                            # proposer-controlled steering field must be DEAD:
                            # the committee still accepts on the merits.
                            "committee_hint": "disagree_without_citation",
                        },
                        "submitted_leaf_model": "gpt-5.5",
                        "disposition": "open",
                    }
                ),
                json.dumps(
                    {
                        "proposal_signature": "sig-cite",
                        "proposal": {
                            "proposed_change": "loosen certifier gate",
                            "expected_number_moved": {"closure": 1},
                            "certifier_touched": True,
                        },
                        "submitted_leaf_model": "gpt-5.5",
                        "disposition": "open",
                    }
                ),
                json.dumps(
                    {
                        "proposal_signature": "sig-escalate",
                        "proposal": {
                            "proposed_change": "rework dispatch seam",
                            "expected_number_moved": {"interventions": -1},
                            "certifier_touched": False,
                        },
                        "submitted_leaf_model": "gpt-5.5",
                        "disposition": "open",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    def _adjudicator(_project_dir, proposal):
        if str(proposal.get("proposed_change") or "") == "rework dispatch seam":
            # parse failure: no verdict, never coerced to accept/reject
            return {"accepted": None, "error": "verdict parse failure: JSONDecodeError | raw prefix: 'I think…'"}
        return {"accepted": True, "rule_citations": ["Rule 2"], "reason": "strict improvement on named indices"}

    def _dissent(_project_dir, proposal):
        if str(proposal.get("proposed_change") or "") == "loosen certifier gate":
            return {"accepted": False, "rule_citations": ["Rule 4"],
                    "reason": "loosens a constraint without a countersigned adversarial receipt"}
        return {"accepted": True, "rule_citations": [], "reason": "no dissent: counter-case fails"}

    monkeypatch.setattr(so, "_sealed_leaf_adjudicator", lambda *_a, **_k: _adjudicator)
    monkeypatch.setattr(so, "_sealed_leaf_dissent_adjudicator", lambda *_a, **_k: _dissent)

    receipt = so.adjudicate_leaf_proposals(
        proj,
        sealed_leaf_model="claude-3.5",
        judge_model="gpt-4o",
        mutator_model="gpt-4o",
    )

    assert receipt["status"] == "ok"
    assert receipt["escalated"] == 1
    rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
    by_sig = {row["proposal_signature"]: row for row in rows}
    assert by_sig["sig-approve"]["disposition"] == "accepted"
    assert "strict improvement" in by_sig["sig-approve"]["reason"]
    assert by_sig["sig-cite"]["disposition"] == "rejected"
    assert "Rule 4" in by_sig["sig-cite"]["reason"]
    assert "countersigned" in by_sig["sig-cite"]["reason"]
    assert by_sig["sig-escalate"]["disposition"] == "escalate"
    assert by_sig["sig-escalate"]["committee_disposition"]["adjudicator"]["accepted"] is None
    assert "no verdict" in by_sig["sig-escalate"]["reason"]
    assert "parse failure" in by_sig["sig-escalate"]["reason"]


def test_adjudicate_leaf_proposals_normalizes_free_form_riders(tmp_path, monkeypatch):
    from ztare.research_director import strategy_office as so

    proj = _mini_worldmodel_project(tmp_path)
    ws = proj / "workspace"
    ws.mkdir(exist_ok=True)
    ledger = ws / "leaf_proposals.jsonl"
    ledger.write_text(
        json.dumps({
            "proposal_signature": "sig-free",
            "proposal": "add carrier write evidence",
            "turn_receipt_ref": "workspace/visible_cli_receipts/check.json",
            "disposition": "open",
        }) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(so, "_sealed_leaf_adjudicator", lambda *_a, **_k: (lambda _p, proposal: {"accepted": True, "rule_citations": ["Rule 2"], "reason": proposal["proposed_change"]}))
    monkeypatch.setattr(so, "_sealed_leaf_dissent_adjudicator", lambda *_a, **_k: (lambda _p, _proposal: {"accepted": True, "rule_citations": [], "reason": "no dissent: counter-case fails"}))
    receipt = so.adjudicate_leaf_proposals(proj)
    assert receipt["status"] == "ok"
    rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
    assert rows[-1]["proposal"]["proposed_change"] == "add carrier write evidence"
    assert rows[-1]["proposal"]["refs"] == ["workspace/visible_cli_receipts/check.json"]


class _CannedResp:
    def __init__(self, text, effective_model_id=None, model_id_used=None):
        self.text = text
        self.effective_model_id = effective_model_id
        self.model_id_used = model_id_used


def test_sealed_leaf_adjudicators_planted_dispatch(tmp_path, monkeypatch):
    """Planted canned-JSON dispatch: accept, reject, parse-failure→escalate,
    and cross-provider fallback annotation — no verdict coercion anywhere."""
    from ztare.research_director import strategy_office as so

    proposal = {"proposed_change": "extend join_lowerable_selectors to guarded coproduct",
                "certifier_touched": False}
    prompts = []

    def _plant(reply_text, effective=None):
        def _fake_leaf_call(_project_dir, _model, prompt, *, label):
            prompts.append((label, prompt))
            return _CannedResp(reply_text, effective_model_id=effective), "gpt-5.5"
        monkeypatch.setattr(so, "_leaf_call", _fake_leaf_call)

    # accept path
    _plant(json.dumps({"accepted": True, "rule_citations": ["Rule 2"],
                       "reason": "guarded coproduct closes the 4-cell residual under Rule 2(c)"}))
    verdict = so._sealed_leaf_adjudicator("gpt-5.5")(tmp_path, proposal)
    assert verdict["accepted"] is True
    assert verdict["rule_citations"] == ["Rule 2"]
    assert "model_fallback" not in verdict
    # the sealed prompt carries the rules and the proposal, not the old stub
    label, prompt = prompts[-1]
    assert label == "strategy_office_sealed_adjudicator"
    assert "MACHINERY RULES" in prompt
    assert "guarded coproduct" in prompt

    # reject path (dissent leaf, adversarial frame)
    _plant(json.dumps({"accepted": False, "rule_citations": ["Rule 3"],
                       "reason": "touches the certifier in the same transaction"}))
    dissent = so._sealed_leaf_dissent_adjudicator("gpt-5.5")(tmp_path, proposal)
    assert dissent["accepted"] is False
    assert dissent["rule_citations"] == ["Rule 3"]
    assert "AGAINST" in prompts[-1][1]

    # parse failure NEVER becomes a verdict; the committee escalates it
    _plant("I would probably approve this one.")
    bad = so._sealed_leaf_adjudicator("gpt-5.5")(tmp_path, proposal)
    assert bad["accepted"] is None
    assert "raw prefix" in bad["error"]
    ok = {"accepted": True, "rule_citations": [], "reason": "fine"}
    disposition, reason = so._committee_disposition(bad, ok)
    assert disposition == "escalate"
    assert "adjudicator: no verdict" in reason

    # silent cross-provider fallback is annotated in the receipt
    _plant(json.dumps({"accepted": True, "rule_citations": ["Rule 2"],
                       "reason": "strict improvement"}), effective="claude-opus-4-6")
    fb = so._sealed_leaf_adjudicator("gpt-5.5")(tmp_path, proposal)
    assert fb["model_fallback"] == {"requested": "gpt-5.5", "effective": "claude-opus-4-6"}


def test_committee_disposition_refuses_bare_category_strings():
    from ztare.research_director import strategy_office as so

    ok = {"accepted": True, "rule_citations": ["Rule 2"], "reason": "strict improvement on closure"}
    # a negative verdict without rule_citations cannot close the proposal
    disposition, reason = so._committee_disposition(
        {"accepted": False, "rule_citations": [], "reason": "seems bad"}, ok)
    assert disposition == "escalate"
    assert "negative verdict without rule_citations" in reason
    # a verdict without a concrete reason cannot close the proposal
    disposition, reason = so._committee_disposition(ok, {"accepted": True, "rule_citations": [], "reason": ""})
    assert disposition == "escalate"
    assert "dissent: missing concrete reason" in reason
    # a valid cited dissent rejects with the citation in the reason
    disposition, reason = so._committee_disposition(
        ok, {"accepted": False, "rule_citations": ["Rule 4"], "reason": "loosens a gate"})
    assert disposition == "rejected"
    assert reason == "dissent: loosens a gate [Rule 4]"


def test_convene_attests_effective_model_on_fallback(tmp_path, monkeypatch):
    """F4: the pending attestation names the model that ACTUALLY answered."""
    from ztare.research_director import strategy_office as so
    from ztare.worldmodel.strategy_battery import WorldmodelBattery

    proj = _mini_worldmodel_project(tmp_path)

    def leaf(_prompt):
        return json.dumps({"experiments": []})
    leaf.requested_model_id = "gpt-5.5"
    leaf.effective_model_id = "claude-opus-4-6"

    so.convene(proj, WorldmodelBattery(), leaf_fn=leaf,
               leaf_model="gpt-5.5", judge_model="gpt-4o", mutator_model="gemini-2.5-pro")
    pending = json.loads((proj / "workspace" / so.PENDING_FILENAME).read_text(encoding="utf-8"))
    assert pending["effective_leaf_model"] == "claude-opus-4-6"
    xfam = pending["cross_family"]
    assert xfam["model_fallback"] == {"requested": "gpt-5.5", "effective": "claude-opus-4-6"}
    # the attested family is the EFFECTIVE (claude) family, not the requested one
    assert xfam["leaf_family"] == "claude"


def test_tested_but_undispositioned_detector(tmp_path):
    from ztare.worldmodel.machinery_contradictions import tested_but_undispositioned
    pool = tmp_path / "candidate_pool.jsonl"
    pool.write_text('{"sha": "a"}\n{"sha": "b"}\n')
    ledger = tmp_path / "operator_proposals.jsonl"
    from ztare.common.operator_proposal_contract import operator_proposal_card, write_proposal_cards
    card = operator_proposal_card(
        failure_family="fam", evidence_indices=[1], spatial_footprint={"a": 1},
        why_existing_ops_fail={"x": "y"}, proposed_operator_sketch="s",
        acceptance_test="t")
    write_proposal_cards(ledger, [card])
    cards = tested_but_undispositioned(pool, ledger)
    assert len(cards) == 1
    assert cards[0]["failure_family"] == "ledger:tested-but-undispositioned"
    assert cards[0]["certifier_touched"] is False
    # silent once a disposition is recorded
    from ztare.common.operator_proposal_contract import set_disposition, record_disposition
    record_disposition(ledger, set_disposition(card, "accepted"))
    assert tested_but_undispositioned(pool, ledger) == []


# ── cycle enumeration + template/copy goal (GP-250 exploration primitives) ────

def _tr(t, s, a, s_next):
    from ztare.worldmodel.episode_log import Transition
    from ztare.worldmodel.grid_dsl import grid_from_lists
    return Transition(t, grid_from_lists(s), a, grid_from_lists(s_next))


def test_close_cycle_and_state_at():
    from ztare.worldmodel.cycle_enumeration import close_cycle, state_at
    assert close_cycle(["A", "B", "A", "B"]) == ["A", "B"]     # 2-cycle closes
    assert close_cycle(["A", "B", "C"]) is None                # still open
    assert state_at(((1, 2), (3, 4)), [(0, 0), (1, 1)]) == (1, 4)


def test_cycles_from_evidence_flags_undersampled_switch_despite_mover_colour_collision():
    # A display cell that toggles 5<->9 while 9 is ALSO a sprite colour: the
    # positional sprite footprint must keep the display 9, not mask it away.
    from ztare.worldmodel.cycle_enumeration import cycles_from_evidence
    from ztare.worldmodel.episode_log import EpisodeLog
    spec = {"actions": {"0": []},
            "always": [{"op": "region_event", "mover_colors": [8, 9], "rect": [2, 2, 2, 3],
                        "edge": "exit", "writes": [[5, [[0, 0]]]]}]}
    # sprite is the 2-colour {8,9} blob at (2,2)-(2,3); the write cell (0,0) is a
    # lone display cell that is 5 in one frame and 9 in another.
    A = [[5, 0, 0, 0], [0, 0, 0, 0], [0, 0, 8, 9], [0, 0, 0, 0]]
    B = [[9, 0, 0, 0], [0, 0, 0, 0], [0, 0, 8, 9], [0, 0, 0, 0]]
    log = EpisodeLog([_tr(0, A, 0, A), _tr(1, B, 0, B)])
    rep = cycles_from_evidence(log, spec)
    src = rep["region_event@[2, 2, 2, 3]"]
    assert src["multi_state"] is True
    assert src["distinct_values"] == [5, 9]           # 9 kept: cell (0,0) is not the sprite


def test_plan_next_crossing_finds_gated_exit():
    from ztare.worldmodel.cycle_enumeration import plan_next_crossing
    from ztare.worldmodel.spec_catalog import lower_spec
    spec = {"actions": {"0": [{"op": "translate_block", "match_colors": [2], "dy": 0, "dx": 1,
                               "require_dest_colors": [0], "fill_color": 0,
                               "component_min_colors": 1}]}, "always": []}
    step, err = lower_spec(spec)
    assert step, err
    grid = ((2, 0, 0, 0, 0),)                          # mover at col0, moves right
    path, after = plan_next_crossing(step, grid, [0, 3, 0, 3], [2], "exit", 1)
    assert path is not None and path[-1] == 0          # exits the rect moving right
    assert after[0][4] == 2                            # mover ended past the rect


def test_template_copy_candidate_and_predicate():
    from ztare.worldmodel.goal_abduction import (
        _template_copy_candidates, predicate_from_spec)
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.grid_dsl import grid_from_lists
    # bg=0 field; a static 2-colour template glyph {7,8} at (1,1)-(1,2); a copy the
    # region_event mutates at (4,4)-(4,5). Copy starts unmatched (all bg there).
    base = [[0] * 8 for _ in range(6)]
    base[1][1], base[1][2] = 7, 8                      # static template
    g_a = [row[:] for row in base]
    g_b = [row[:] for row in base]
    g_b[4][4] = 7                                      # copy cell changes -> mutable
    log = EpisodeLog([_tr(0, g_a, 0, g_b), _tr(1, g_b, 0, g_a)])
    spec = {"actions": {"0": []},
            "always": [{"op": "region_event", "mover_colors": [3], "rect": [5, 5, 5, 6],
                        "edge": "exit", "writes": [[7, [[4, 4], [4, 5]]]]}]}
    cands = _template_copy_candidates(list(log), spec, [])
    tm = [c for c in cands if c["kind"] == "template_match"]
    assert tm, "expected a template_match candidate"
    ps = tm[0]["predicate_spec"]
    assert ps["relation"] == "content_equal_up_to_alignment"
    # predicate is False on the unmatched start, True once the copy holds {7,8}
    goal = predicate_from_spec(ps, grid_from_lists(g_a))
    assert goal(grid_from_lists(g_a)) is False
    solved = [row[:] for row in g_a]
    solved[4][4], solved[4][5] = 7, 8                  # copy now equals the template
    assert goal(grid_from_lists(solved)) is True


# ── GP-250 region-state machine + dihedral shape equivalence (appended) ──────
from ztare.worldmodel.spec_catalog import lower_spec as _lower
from ztare.worldmodel.spec_abduction import _cellwise_reproducible, _fit_write_function
from ztare.worldmodel.symmetry import canonical_form
from ztare.worldmodel.goal_abduction import predicate_from_spec


def _shift_spec():
    # a 3-glyph display where the lit pixel SHIFTS across 3 cells; a mover (2)
    # exits rect [0,0,0,0] on action 0, advancing the display one cycle step.
    return {
        "actions": {"0": [{"op": "translate_block", "match_colors": [2], "dy": 1, "dx": 0,
                           "require_dest_colors": [0], "fill_color": 0}]},
        "always": [{"op": "region_event", "mover_colors": [2], "rect": [0, 0, 0, 0],
                    "edge": "exit", "region": [3, 0, 3, 2],
                    "content_states": [[8, 7, 7], [7, 8, 7], [7, 7, 8]],
                    "state_transition": "cycle"}],
    }


def _grid_with_display(disp):
    g = [[0, 0, 0] for _ in range(4)]
    g[0][0] = 2                       # mover in the rect
    g[3][0], g[3][1], g[3][2] = disp  # display row
    return tuple(tuple(r) for r in g)


def test_region_state_machine_advances_and_fail_closes():
    step, err = _lower(_shift_spec())
    assert step is not None, err
    # each crossing advances the glyph one step around the ring
    assert step(_grid_with_display((8, 7, 7)), 0, 0)[3] == (7, 8, 7)
    assert step(_grid_with_display((7, 8, 7)), 0, 0)[3] == (7, 7, 8)
    assert step(_grid_with_display((7, 7, 8)), 0, 0)[3] == (8, 7, 7)
    # unknown glyph => fail-closed (region untouched)
    assert step(_grid_with_display((9, 9, 9)), 0, 0)[3] == (9, 9, 9)
    # Lean parity: the spec lowers to the regionEventStates semantics
    from ztare.worldmodel.spec_lean import spec_to_lean_step
    lean = spec_to_lean_step(_shift_spec())
    assert "regionEventStates" in lean and "[(0, 1), (1, 2), (2, 0)]" in lean


def test_shifting_glyph_is_not_cellwise_but_content_states_fits():
    # the planted negative: a 3-glyph SHIFT cycle. A global colour map (7<->8)
    # exists over the moving set, so the cell-wise learner is TEMPTED — but
    # applying it cell-wise does NOT reproduce the region, so no cell-wise write
    # (fixed / toggle / cycle) fits. Only the region-state machine does.
    states = [(8, 7, 7), (7, 8, 7), (7, 7, 8)]
    cyc = {0: 1, 1: 2, 2: 0}
    assert _cellwise_reproducible(states, cyc) is False
    # _fit_write_function may emit a toggle from the global map; prove it MISFIRES
    cell_pairs = {}
    for f, t in cyc.items():
        for k, (a, b) in enumerate(zip(states[f], states[t])):
            cell_pairs.setdefault((3, k), []).append((a, b))
    ev = _fit_write_function((0, 0, 0, 0), cell_pairs, [2])
    if ev is not None and (ev.get("toggle") or ev.get("cycle")):
        from ztare.worldmodel.spec_catalog import _perm_from_rule
        perm = _perm_from_rule(ev)
        got = tuple(perm.get(c, c) for c in states[0])
        assert got != states[1]        # the cell-wise map cannot reproduce the shift
    # a genuine 2-state recolour toggle, by contrast, IS cell-wise
    assert _cellwise_reproducible([(8, 7), (7, 8)], {0: 1, 1: 0}) is True
    # generality (no hardcoded k>=3 ceiling): a 2-state DIRECTIONAL latch whose
    # block SHIFTS is still non-cell-wise, so it is captured, not dropped — the
    # functional-dependency check, not a state count, is the gate.
    assert _cellwise_reproducible([(8, 7, 0), (0, 8, 7)], {0: 1, 1: 0}) is False


def test_counterexample_route_compresses_phase_writes_equivariantly():
    """Repeated trigger effects become one state machine under chart relabeling."""
    from types import SimpleNamespace

    from ztare.worldmodel.leaf_workbench import _catalog_residual_event_candidates

    def run_case(row_shift, col_shift, palette):
        mover = palette["mover"]
        idle, lit = palette["idle"], palette["lit"]
        source = (2 + row_shift, 1 + col_shift)
        target = (2 + row_shift, 3 + col_shift)
        display = (8 + row_shift, 2 + col_shift)
        states = (
            ((lit, idle, idle), (lit, idle, idle)),
            ((idle, lit, idle), (idle, lit, idle)),
            ((idle, idle, lit), (idle, idle, lit)),
        )

        def transition(before_state, after_state):
            before = [[0] * 16 for _ in range(16)]
            after = [[0] * 16 for _ in range(16)]
            for grid, anchor in ((before, source), (after, target)):
                r0, c0 = anchor
                grid[r0][c0:c0 + 2] = [mover[0], mover[0]]
                grid[r0 + 1][c0:c0 + 2] = [mover[1], mover[1]]
            dr, dc = display
            for rr in range(2):
                before[dr + rr][dc:dc + 3] = list(before_state[rr])
                after[dr + rr][dc:dc + 3] = list(after_state[rr])
            return SimpleNamespace(
                s=tuple(tuple(row) for row in before),
                s_next=tuple(tuple(row) for row in after),
                a=0,
                t=0,
                identity=None,
            )

        prior = [
            (0, transition(states[0], states[1])),
            (1, transition(states[1], states[2])),
        ]
        current = transition(states[2], states[0])
        proposed = [list(row) for row in current.s_next]
        dr, dc = display
        for rr in range(2):
            proposed[dr + rr][dc:dc + 3] = list(states[2][rr])
        events = _catalog_residual_event_candidates(
            prior,
            current,
            tuple(tuple(row) for row in proposed),
            current.s_next,
        )
        assert events
        return events[0]

    first = run_case(0, 0, {"mover": (1, 2), "idle": 7, "lit": 8})
    transformed = run_case(1, 2, {"mover": (4, 9), "idle": 5, "lit": 12})

    assert first["operation_identity"] == transformed["operation_identity"] == {
        "relation": "boundary_conditioned_state_transition",
        "subject_role": "moves_under_actions",
        "boundary": "arrival",
        "consequence_role": "finite_state_object",
    }
    assert first["lowering"]["state_transition"] == "cycle"
    assert transformed["lowering"]["state_transition"] == "cycle"
    assert first["lowering"]["region"] == [8, 2, 9, 4]
    assert transformed["lowering"]["region"] == [9, 4, 10, 6]
    assert first["state_machine_evidence"]["state_count"] == 3
    assert first["operation_support_rows"] == [0, 1]


def _place(g, y0, x0, cells, color):
    for (dy, dx) in cells:
        g[y0 + dy][x0 + dx] = color


def test_template_match_dihedral_matches_rotation_translation_fails():
    L = [(0, 0), (1, 0), (2, 0), (2, 1)]              # an L tetromino
    L_rot = [(0, 0), (0, 1), (0, 2), (1, 0)]          # the same L, turned 90°
    start = [[0] * 10 for _ in range(10)]
    _place(start, 1, 1, L, 4)                          # static template
    start = tuple(tuple(r) for r in start)
    goal = [[0] * 10 for _ in range(10)]
    _place(goal, 1, 1, L, 4)
    _place(goal, 5, 5, L_rot, 4)                       # copy = template rotated 90°
    goal = tuple(tuple(r) for r in goal)
    spec = {"relation": "content_equal_up_to_alignment",
            "template_region": [1, 1, 3, 3], "copy_region": [5, 5, 7, 7], "background": [0]}
    # dihedral group: rotation counts as a match (Core-Knowledge geometry prior)
    assert predicate_from_spec(spec, start, "dihedral")(goal) is True
    # identity group (translation only): a rotated copy provably does NOT match
    assert predicate_from_spec(spec, start, "identity")(goal) is False
    # A geometric prior is never the implicit authority-bearing default.
    assert predicate_from_spec(spec, start)(goal) is False


def test_accumulate_extremal_is_consume_transpose_and_mines_dropped_fills():
    """accumulate_extremal — the fill mirror of consume_extremal (progress
    bars/counters that GROW). Three planted-synthetic claims:

      1. TRANSPOSE — accumulate(color=W, from=E) is behaviorally identical to
         consume(color=E, replacement=W): both set the extremal-index cell of one
         value to another. Honest datapoint: the mirror adds a NAME + a mining
         path, not new expressive power.
      2. PIPELINE — a spec carrying accumulate_extremal lowers and replays a
         filling-bar log exactly, and abduce_spec recovers a replay-consistent
         law for that log end to end.
      3. STRICT IMPROVEMENT — on a step where the fill's empty color is also
         produced elsewhere, consume mining DROPS the fill (its moved-color
         filter) and only accumulate mining proposes it.
    """
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.spec_abduction import (
        abduce_spec, _abduce_accumulate_extremal, _abduce_consume_extremal, _diff)
    from ztare.worldmodel.spec_catalog import (
        lower_spec, _apply_accumulate_extremal, _apply_consume_extremal)

    # 1. TRANSPOSE (exhaustive over extreme x count on mixed grids)
    for extreme in ("min", "max"):
        for cnt in (1, 2, 3):
            grid = [[0, 6, 0, 6, 0, 3], [3, 0, 0, 6, 6, 0]]
            acc = {"op": "accumulate_extremal", "color": 6, "from": 0,
                   "axis": "row", "extreme": extreme, "count": cnt}
            con = {"op": "consume_extremal", "color": 0, "replacement": 6,
                   "axis": "row", "extreme": extreme, "count": cnt}
            assert (_apply_accumulate_extremal([r[:] for r in grid], acc)
                    == _apply_consume_extremal([r[:] for r in grid], con))

    # 2. PIPELINE — a filling bar in the only row carrying the empty-slot color 8
    truth, err = lower_spec({
        "actions": {"0": [{"op": "identity"}], "1": [{"op": "identity"}]},
        "always": [{"op": "accumulate_extremal", "color": 7, "from": 8,
                    "axis": "row", "extreme": "min"}]})
    assert err == "", err
    g = ((7, 8, 8, 8, 8, 8),
         (3, 3, 3, 3, 3, 3))
    log = EpisodeLog()
    s = g
    for a in (0, 1, 0, 1, 0, 1):
        s2 = truth(s, a, 0)
        log.append(s, a, s2, t=0)
        s = s2
    assert replay_consistency_gate(truth, log).ok           # accumulate spec replays
    r = abduce_spec(log, 2)
    assert r.replay_ok and r.status == "spec_identified", r.detail

    # 3. STRICT IMPROVEMENT — fill 0->7 while 0 is also produced (3->0)
    s = [[7, 0, 0, 0], [3, 3, 3, 0]]
    sn = [[7, 7, 0, 0], [3, 3, 0, 0]]
    d = _diff(s, sn)
    assert not any(rr["op"] == "consume_extremal" and rr["color"] == 0
                   for rr in _abduce_consume_extremal(s, sn, d))
    assert any(rr["op"] == "accumulate_extremal" and rr["color"] == 7 and rr["from"] == 0
               for rr in _abduce_accumulate_extremal(s, sn, d))


def _rotation_residual_log():
    """A planted rotation residual no catalog op expresses -> abduction PARTIAL."""
    from ztare.worldmodel.episode_log import EpisodeLog
    base = ((3, 3, 3, 3), (3, 4, 5, 3), (3, 6, 4, 3), (3, 3, 3, 3))
    log = EpisodeLog()
    s = base
    for _ in range(6):
        s2 = _rotate_block_2x2(s)
        log.append(s, 0, s2, t=0)
        s = s2
    return log


def _load_arc3_play_loop():
    import importlib.util
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    p = root / "scripts" / "public" / "control" / "arc3_play_loop.py"
    spec = importlib.util.spec_from_file_location("arc3_play_loop_under_test", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_governed_adoption_requires_current_run_promotion_and_changed_bytes(tmp_path):
    mod = _load_arc3_play_loop()
    project = tmp_path / "project"
    workspace = project / "workspace"
    workspace.mkdir(parents=True)
    model = project / "test_model.py"
    telemetry = workspace / "iteration_telemetry.jsonl"
    model.write_text("def step(s, a, t): return s\n", encoding="utf-8")
    telemetry.write_text("", encoding="utf-8")
    cursor = mod._governed_adoption_cursor(project)

    telemetry.write_text(
        json.dumps({"record_type": "iteration", "champion_promoted": False}) + "\n",
        encoding="utf-8",
    )
    no_promotion = mod._governed_adoption_since(project, cursor)
    assert no_promotion["adopted"] is False

    cursor = mod._governed_adoption_cursor(project)
    model.write_text("def step(s, a, t): return tuple(s)\n", encoding="utf-8")
    with telemetry.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"record_type": "iteration", "champion_promoted": True}) + "\n")
    promoted = mod._governed_adoption_since(project, cursor)
    assert promoted["adopted"] is True
    assert promoted["candidate_bytes_changed"] is True
    assert promoted["adoption_scope"] == "active_discriminator_frontier"
    assert promoted["task_discharge_authorized"] is False


def test_residual_frontier_materializes_as_baseline_without_promotion(tmp_path):
    import hashlib

    mod = _load_arc3_play_loop()
    project = tmp_path / "project"
    workspace = project / "workspace"
    workspace.mkdir(parents=True)
    (workspace / "iteration_telemetry.jsonl").write_text("", encoding="utf-8")
    (project / "test_model.py").write_text(
        "def step(state, action, t): return state\n",
        encoding="utf-8",
    )
    frontier = "def step(state, action, t): return tuple(state)\n"
    frontier_sha = hashlib.sha256(frontier.encode("utf-8")).hexdigest()
    (workspace / "frontier.py").write_text(frontier, encoding="utf-8")

    receipt = mod._materialize_governed_baseline(
        project,
        source=frontier,
        source_ref="workspace/frontier.py",
        candidate_sha256=frontier_sha,
        producer_id="deterministic-frontier",
    )
    cursor = mod._governed_adoption_cursor(project)
    with (workspace / "iteration_telemetry.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"record_type": "iteration", "champion_promoted": True}) + "\n")

    assert receipt["changed"] is True
    assert receipt["promotion_authority"] is False
    assert (project / "test_model.py").read_text(encoding="utf-8") == frontier
    assert mod._governed_adoption_since(project, cursor)["adopted"] is False


def test_configured_candidate_verifier_error_does_not_unlock_raw_abduction(
    tmp_path, monkeypatch
):
    from types import SimpleNamespace

    mod = _load_arc3_play_loop()
    candidate = SimpleNamespace(
        proposal=SimpleNamespace(candidate_sha256="a" * 64),
        gate_pass=False,
        gate_payload={
            "verdict": "harness_error",
            "control_receipt": {"cause": "RuntimeError: verifier timed out"},
        },
    )
    monkeypatch.setattr(
        "ztare.worldmodel.deterministic_candidate_producers.evaluate_configured_candidates",
        lambda *_args, **_kwargs: [candidate],
    )

    outcome = mod._configured_system1_candidate(tmp_path, {})

    assert outcome["status"] == "verification_unavailable"
    assert outcome["candidate_sha256s"] == ["a" * 64]
    assert outcome["causes"] == ["RuntimeError: verifier timed out"]


def test_configured_system1_reuses_current_incumbent_before_mutation(
    tmp_path, monkeypatch
):
    """An empty residual selects the incumbent role, not a challenger role."""
    from types import SimpleNamespace

    mod = _load_arc3_play_loop()
    source = "def step(state, action, t):\n    return state\n"
    incumbent = tmp_path / "test_model.py"
    incumbent.write_text(source, encoding="utf-8")
    (tmp_path / "gate_harness.py").write_text("# identity stub\n", encoding="utf-8")
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    payload = {
        "harness_ok": True,
        "gated_sha256": digest[:16],
        "gates": {
            "visible": {"name": "visible", "pass": True},
            "holdout": {"name": "holdout", "pass": True},
        },
        # Reuse does not need replacement authority.  This false bit proves
        # the two lifecycle roles are not being conflated.
        "pre_judge_decision": {"evaluator_authorized": False},
    }
    monkeypatch.setattr(
        "ztare.validator.core.pre_judge_gate.run_pre_judge_gate_harness",
        lambda **_kwargs: SimpleNamespace(ran=True, payload=payload),
    )
    monkeypatch.setattr(
        "ztare.worldmodel.deterministic_candidate_producers.evaluate_configured_candidates",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("mutation producer must not fire without a residual")
        ),
    )

    outcome = mod._configured_system1_candidate(tmp_path, {})

    assert outcome["status"] == "incumbent_current"
    assert outcome["candidate_sha256"] == digest
    assert outcome["model"](((1,),), 0, 0) == ((1,),)


def test_current_cached_survivor_consumes_just_observed_gate(tmp_path, monkeypatch):
    """Producer publication and survivor selection compose in one phase."""
    mod = _load_arc3_play_loop()
    source = "def step(state, action, t):\n    return state\n"
    candidate = tmp_path / "workspace" / "submissions" / "candidate.py"
    candidate.parent.mkdir(parents=True)
    candidate.write_text(source, encoding="utf-8")
    digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
    record = {
        "submission": "workspace/submissions/candidate.py",
        "visible_exact_rows": 3,
        "visible_wrong_cells": 0,
        "holdout_depth": 2,
        "gate_score": 1.0,
        "description_length": len(source),
        "run_role": "EVALUATION",
        "claim_class": "clean_transfer",
        "evaluation_policy_sha256": "policy-current",
    }
    payload = {
        "harness_ok": True,
        "gated_sha256": digest,
        "gates": {"replay": {"name": "replay", "pass": True}},
        # Replacement can remain unpromoted while the carrier is reused as a
        # current-evidence search survivor.
        "pre_judge_decision": {"evaluator_authorized": False},
        "evaluation_policy_sha256": "policy-current",
    }
    monkeypatch.setattr(
        "ztare.validator.core.pre_judge_gate.evaluation_policy_sha256",
        lambda: "policy-current",
    )
    monkeypatch.setattr(
        "ztare.common.candidate_memory.admissible_candidate_memory_records",
        lambda *_args, **_kwargs: [record],
    )
    monkeypatch.setattr(
        "ztare.common.candidate_memory.candidate_memory_source",
        lambda *_args, **_kwargs: source,
    )
    monkeypatch.setattr(
        "ztare.validator.core.pre_judge_gate.run_pre_judge_gate_harness",
        lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("the just-observed gate must not replay")
        ),
    )

    outcome = mod._current_cached_survivor(
        tmp_path,
        observed_gate_payloads={digest: payload},
    )

    assert outcome["status"] == "cached_survivor_current"
    assert outcome["candidate_sha256"] == digest


def test_current_cached_survivor_rejects_prior_evaluator_policy(
    tmp_path, monkeypatch
):
    """Carrier/evidence equality cannot transport a verdict across policy."""
    mod = _load_arc3_play_loop()
    source = "def step(state, action, t):\n    return state\n"
    candidate = tmp_path / "workspace" / "submissions" / "candidate.py"
    candidate.parent.mkdir(parents=True)
    candidate.write_text(source, encoding="utf-8")
    record = {
        "submission": "workspace/submissions/candidate.py",
        "evaluation_policy_sha256": "policy-prior",
    }
    monkeypatch.setattr(
        "ztare.common.candidate_memory.best_admissible_candidate_memory_record",
        lambda *_args, **_kwargs: record,
    )
    monkeypatch.setattr(
        "ztare.validator.core.pre_judge_gate.evaluation_policy_sha256",
        lambda: "policy-current",
    )

    assert mod._current_cached_survivor(tmp_path) is None


def test_deterministic_producer_consumes_pre_judge_authority_bit(
    tmp_path, monkeypatch
):
    """Raw gate success cannot be reconstructed as replacement authority."""
    from types import SimpleNamespace

    from ztare.worldmodel import deterministic_candidate_producers as producers

    candidate = tmp_path / "workspace" / "submissions" / "candidate.py"
    candidate.parent.mkdir(parents=True)
    candidate.write_text(
        "def step(state, action, t):\n    return state\n",
        encoding="utf-8",
    )
    digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
    proposal = producers.DeterministicCandidateProposal(
        producer_id="fixture",
        candidate_path=candidate,
        candidate_sha256=digest,
        input_sha256s={},
    )
    payload = {
        "harness_ok": True,
        "gated_sha256": digest[:16],
        "gates": {"visible": {"name": "visible", "pass": True}},
        "pre_judge_decision": {"evaluator_authorized": False},
    }
    monkeypatch.setattr(
        producers,
        "configured_proposals",
        lambda *_args, **_kwargs: [proposal],
    )
    monkeypatch.setattr(
        "ztare.validator.core.pre_judge_gate.run_pre_judge_gate_harness",
        lambda **_kwargs: SimpleNamespace(ran=True, payload=payload),
    )

    assessed = producers.evaluate_configured_candidates(
        tmp_path,
        {},
        phase="checkpoint_identification",
    )

    assert len(assessed) == 1
    assert assessed[0].gate_pass is False


def test_catalog_operation_compiler_consumes_matching_task_receipt_family(
    tmp_path, monkeypatch
):
    from ztare.worldmodel import deterministic_candidate_producers as producers

    project = tmp_path
    workspace = project / "workspace"
    workspace.mkdir()
    base_source = "def step(state, action, t):\n    return state\n"
    base_path = workspace / "base.py"
    base_path.write_text(base_source, encoding="utf-8")
    base_sha = hashlib.sha256(base_source.encode("utf-8")).hexdigest()
    operation_identity = {
        "relation": "covered_uncovered",
        "subject_role": "moves_under_actions",
        "boundary": "departure",
        "consequence_role": "revealed_substrate",
    }
    operation_sha = hashlib.sha256(
        json.dumps(
            operation_identity,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    inspection = {
        "input_hashes": {
            "kernel_receipt_ref": "workspace/inspect.json",
        },
        "output_summary": json.dumps(
            {
                "catalog_residual_event_candidates": [
                    {
                        "identity_status": "catalog_operation_reuse_candidate",
                        "operation_identity": {
                            "relation": "decoy",
                            "subject_role": "unselected",
                        },
                        "operation_identity_sha256": hashlib.sha256(
                            json.dumps(
                                {
                                    "relation": "decoy",
                                    "subject_role": "unselected",
                                },
                                sort_keys=True,
                                separators=(",", ":"),
                            ).encode("utf-8")
                        ).hexdigest(),
                        "lowering_kind": "identity",
                        "lowering": {"op": "identity"},
                    },
                    {
                        # The inspector predates recurrence acquisition.  The
                        # downstream selector owns current reuse authority.
                        "identity_status": "operation_recurrence_required",
                        "operation_identity": operation_identity,
                        "operation_identity_sha256": operation_sha,
                        "lowering_kind": "region_event",
                        "lowering": {
                            "op": "region_event",
                            "mover_colors": [1, 2],
                            "rect": [2, 2, 3, 3],
                            "edge": "exit",
                            "writes": [[9, [[2, 2]]]],
                        },
                    }
                ]
            }
        ),
    }
    selector = {
        "input_hashes": {
            "kernel_receipt_ref": "workspace/selector.json",
        },
        "output_summary": json.dumps(
            {
                "schema": "ztare-worldmodel-operation-domain-selector-v1",
                "task_id": "task-1",
                "task_source_sha256": base_sha,
                "operation_identity_sha256": operation_sha,
                "candidate_delta_admissible": True,
                "operation_guard": {
                    "kind": "adapter_local_exact_chart",
                    "lowering": {"when_region": [1, 1, 4, 4, [0] * 16]},
                },
            }
        ),
    }
    task = {
        "task_id": "task-1",
        "source_ref": "workspace/base.py",
        "source_sha256": base_sha,
    }
    monkeypatch.setattr(
        "ztare.common.leaf_workbench_executor.active_workbench_task_capability_scope",
        lambda *_args, **_kwargs: (
            frozenset(
                {
                    "inspect_worldmodel_counterexample_context",
                    "mine_worldmodel_lowerable_selectors",
                }
            ),
            task,
        ),
    )
    monkeypatch.setattr(
        "ztare.common.leaf_workbench_executor.active_workbench_task_receipt_family",
        lambda *_args, **_kwargs: {
            "inspect_worldmodel_counterexample_context": inspection,
            "mine_worldmodel_lowerable_selectors": selector,
        },
    )

    proposal = producers._catalog_operation_patch_compiler(project, {})

    assert proposal is not None
    source = proposal.candidate_path.read_text(encoding="utf-8")
    assert "# TaskIdentity: task-1" in source
    assert "# OperationIdentity: " + operation_sha in source
    assert "CARRIER_PROVENANCE =" in source
    assert "'when_region': [1, 1, 4, 4" in source
    assert "'when_action'" not in source

    mismatched = json.loads(selector["output_summary"])
    mismatched["operation_identity_sha256"] = "f" * 64
    selector["output_summary"] = json.dumps(mismatched)
    assert producers._catalog_operation_patch_compiler(project, {}) is None

    relational_identity = {
        "relation": "input_bound_output_value",
        "source_role": "observed_context",
        "target_role": "carrier_consequence",
        "compatibility": "equality_transport",
    }
    relational_sha = hashlib.sha256(
        json.dumps(
            relational_identity,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    inspection["output_summary"] = json.dumps(
        {"catalog_residual_event_candidates": []}
    )
    selector["output_summary"] = json.dumps({
        "schema": "ztare-worldmodel-operation-domain-selector-v1",
        "task_id": "task-1",
        "task_source_sha256": base_sha,
        "operation_identity": relational_identity,
        "operation_identity_sha256": relational_sha,
        "candidate_delta_admissible": True,
        "candidate_lowering": {
            "op": "bind_region_value",
            "target_rect": [1, 2, 2, 3],
            "source_offset": [0, -1],
            "expected_current": 12,
        },
    })

    relational = producers._catalog_operation_patch_compiler(project, {})

    assert relational is not None
    relational_source = relational.candidate_path.read_text(encoding="utf-8")
    assert "'op': 'bind_region_value'" in relational_source
    assert relational_sha in relational_source


def test_configured_system1_keeps_better_incumbent_residual_frontier(
    tmp_path, monkeypatch
):
    """A rejected challenger cannot displace a narrower incumbent residual."""
    from types import SimpleNamespace

    mod = _load_arc3_play_loop()
    submissions = tmp_path / "workspace" / "submissions"
    submissions.mkdir(parents=True)
    incumbent_source = "def step(state, action, t):\n    return state\n"
    incumbent_path = tmp_path / "test_model.py"
    incumbent_path.write_text(incumbent_source, encoding="utf-8")
    (submissions / "incumbent.py").write_text(incumbent_source, encoding="utf-8")
    (tmp_path / "gate_harness.py").write_text("# fixture\n", encoding="utf-8")
    incumbent_sha = hashlib.sha256(incumbent_source.encode("utf-8")).hexdigest()

    def payload(sha, exact, wrong):
        return {
            "harness_ok": True,
            "gated_sha256": sha[:16],
            "gates": {
                "visible": {
                    "name": "visible",
                    "pass": False,
                    "diagnostics": {
                        "exact_rows": exact,
                        "wrong_cell_count": wrong,
                        "residual_table": [{"row": exact}],
                    },
                }
            },
            "pre_judge_decision": {"evaluator_authorized": False},
        }

    monkeypatch.setattr(
        "ztare.validator.core.pre_judge_gate.run_pre_judge_gate_harness",
        lambda **_kwargs: SimpleNamespace(
            ran=True,
            payload=payload(incumbent_sha, 10, 2),
        ),
    )
    challenger_source = "def step(state, action, t):\n    return tuple(state)\n"
    challenger_path = submissions / "challenger.py"
    challenger_path.write_text(challenger_source, encoding="utf-8")
    challenger_sha = hashlib.sha256(challenger_source.encode("utf-8")).hexdigest()
    challenger = SimpleNamespace(
        proposal=SimpleNamespace(
            candidate_path=challenger_path,
            candidate_sha256=challenger_sha,
            producer_id="challenger",
        ),
        gate_pass=False,
        gate_payload=payload(challenger_sha, 9, 20),
    )
    monkeypatch.setattr(
        "ztare.worldmodel.deterministic_candidate_producers.evaluate_configured_candidates",
        lambda *_args, **_kwargs: [challenger],
    )

    outcome = mod._configured_system1_candidate(tmp_path, {})

    assert outcome["status"] == "residual_frontier"
    assert outcome["producer_id"] == "current_incumbent"
    assert outcome["candidate_sha256"] == incumbent_sha
    assert outcome["rank"][0] == 10
    assert outcome["rank"][3] == -2
    assert outcome["source_ref"] == "workspace/submissions/incumbent.py"


def test_configured_system1_consumes_receipt_owned_repair_frontier(
    tmp_path, monkeypatch
):
    """A resolved continuation role outranks private candidate re-ranking."""
    from types import SimpleNamespace

    mod = _load_arc3_play_loop()
    workspace = tmp_path / "workspace"
    submissions = workspace / "submissions"
    submissions.mkdir(parents=True)
    (workspace / "latest_patch_base_regression.json").write_text("{}\n")
    (tmp_path / "gate_harness.py").write_text("# fixture\n", encoding="utf-8")
    incumbent_source = "def step(state, action, t): return state\n"
    (tmp_path / "test_model.py").write_text(incumbent_source, encoding="utf-8")
    frontier = submissions / "frontier.py"
    frontier_source = "def step(state, action, t): return tuple(state)\n"
    frontier.write_text(frontier_source, encoding="utf-8")
    frontier_sha = hashlib.sha256(frontier.read_bytes()).hexdigest()
    incumbent_sha = hashlib.sha256(incumbent_source.encode()).hexdigest()
    incumbent_payload = {
        "harness_ok": True,
        "gated_sha256": incumbent_sha[:16],
        "gates": {
            "visible": {
                "pass": False,
                "diagnostics": {
                    "exact_rows": 100,
                    "wrong_cell_count": 1,
                    "residual_table": [{"row": 0}],
                },
            }
        },
    }
    monkeypatch.setattr(
        "ztare.validator.core.pre_judge_gate.run_pre_judge_gate_harness",
        lambda **_kwargs: SimpleNamespace(ran=True, payload=incumbent_payload),
    )
    monkeypatch.setattr(
        "ztare.worldmodel.deterministic_candidate_producers.evaluate_configured_candidates",
        lambda *_args, **_kwargs: [],
    )
    monkeypatch.setattr(
        "ztare.common.patch_base_identity.load_current_repair_frontier",
        lambda _project: {
            "path": frontier,
            "source_ref": "workspace/submissions/frontier.py",
            "sha256": frontier_sha,
            "exact_rows": 90,
            "wrong_cells": 5,
        },
    )

    outcome = mod._configured_system1_candidate(tmp_path, {})

    assert outcome["status"] == "residual_frontier"
    assert outcome["producer_id"] == "repair_preflight_frontier"
    assert outcome["candidate_sha256"] == frontier_sha


def test_configured_system1_replaces_expired_repair_frontier_from_current_epoch(
    tmp_path, monkeypatch
):
    """Evidence growth expires the singleton role without disabling verification."""
    from types import SimpleNamespace

    from ztare.common.patch_base_identity import StaleRepairFrontierError

    mod = _load_arc3_play_loop()
    workspace = tmp_path / "workspace"
    submissions = workspace / "submissions"
    submissions.mkdir(parents=True)
    (workspace / "latest_patch_base_regression.json").write_text("{}\n")
    (tmp_path / "gate_harness.py").write_text("# fixture\n", encoding="utf-8")
    incumbent_source = "def step(state, action, t): return state\n"
    incumbent = tmp_path / "test_model.py"
    incumbent.write_text(incumbent_source, encoding="utf-8")
    immutable = submissions / "incumbent.py"
    immutable.write_text(incumbent_source, encoding="utf-8")
    incumbent_sha = hashlib.sha256(incumbent_source.encode()).hexdigest()
    incumbent_payload = {
        "harness_ok": True,
        "gated_sha256": incumbent_sha[:16],
        "gates": {
            "visible": {
                "pass": False,
                "diagnostics": {
                    "exact_rows": 101,
                    "wrong_cell_count": 3,
                    "residual_table": [{"row": 0}],
                },
            }
        },
    }
    monkeypatch.setattr(
        "ztare.validator.core.pre_judge_gate.run_pre_judge_gate_harness",
        lambda **_kwargs: SimpleNamespace(ran=True, payload=incumbent_payload),
    )
    monkeypatch.setattr(
        "ztare.worldmodel.deterministic_candidate_producers.evaluate_configured_candidates",
        lambda *_args, **_kwargs: [],
    )

    def expired(_project):
        raise StaleRepairFrontierError("prior evidence epoch")

    monkeypatch.setattr(
        "ztare.common.patch_base_identity.load_current_repair_frontier",
        expired,
    )

    outcome = mod._configured_system1_candidate(tmp_path, {})

    assert outcome["status"] == "residual_frontier"
    assert outcome["producer_id"] == "current_incumbent"
    assert outcome["candidate_sha256"] == incumbent_sha
    assert outcome["source_ref"] == "workspace/submissions/incumbent.py"


def _setup_sprint_project(tmp_path, log):
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.adapter import episode_log_path
    log.write_jsonl(episode_log_path(tmp_path))
    EpisodeLog().write_jsonl(episode_log_path(tmp_path, episode=2))   # empty holdout
    return {"mode": "sprint", "sprint_rounds": 1, "sprint_steps": 5, "plan_depth": 6}


def test_arc3_play_config_competition_aliases_to_advice(tmp_path):
    """Competition/advice mode consumes compiled state and never launches the
    governed worker loop."""
    import json

    mod = _load_arc3_play_loop()
    (tmp_path / "play_config.json").write_text(json.dumps({"mode": "competition"}))

    cfg = mod._play_config(tmp_path)
    assert cfg["mode"] == "advice"
    assert cfg["mode_alias"] == "competition"


def test_arc3_play_loop_exact_game_id_bypasses_listing(monkeypatch):
    mod = _load_arc3_play_loop()

    def _boom():
        raise AssertionError("list_games should not run for an exact game id")

    monkeypatch.setattr("ztare.substrates.arc_agi3.list_games", _boom)

    assert mod._game_prefix("ls20-9607627b") == "ls20"
    assert mod._resolve_game_id("ls20-9607627b") == "ls20-9607627b"


def test_play_loop_migrates_legacy_champion_spec_only_after_replay_check(tmp_path):
    from ztare.worldmodel.adapter import episode_log_path
    from ztare.worldmodel.episode_log import EpisodeLog

    mod = _load_arc3_play_loop()
    mod.REPO = tmp_path
    project = tmp_path / "projects" / "arc3_demo_gov"
    log = EpisodeLog()
    log.append(((1,),), 0, ((1,),), t=0)
    log.write_jsonl(episode_log_path(project))
    (tmp_path / "workspace").mkdir()
    legacy = tmp_path / "workspace" / "champion_spec.json"
    good = {"actions": {"0": [{"op": "identity"}]}, "always": []}
    legacy.write_text(json.dumps(good), encoding="utf-8")

    loaded = mod._load_prior_spec(project)

    assert loaded["verdict"] == "loaded"
    assert loaded["spec"] == good
    migrated = project / "workspace" / "champion_spec.json"
    assert json.loads(migrated.read_text()) == good

    other_project = tmp_path / "projects" / "arc3_bad_gov"
    bad_log = EpisodeLog()
    bad_log.append(((1,),), 0, ((2,),), t=0)
    bad_log.write_jsonl(episode_log_path(other_project))
    assert mod._load_prior_spec(other_project)["verdict"] == "missing"
    assert not (other_project / "workspace" / "champion_spec.json").exists()
    assert (project / "workspace" / "arc3_play_loop_receipts.jsonl").exists()


def test_play_loop_uses_partial_abduced_core_only_as_warm_prior(tmp_path):
    from ztare.worldmodel.adapter import episode_log_path
    from ztare.worldmodel.episode_log import EpisodeLog

    mod = _load_arc3_play_loop()
    project = tmp_path / "projects" / "arc3_demo_gov"
    log = EpisodeLog()
    log.append(((1,),), 0, ((2,),), t=0)
    log.write_jsonl(episode_log_path(project))
    core = {"actions": {"0": [{"op": "identity"}]}, "always": []}
    core_path = project / "workspace" / "abduced_core.json"
    core_path.parent.mkdir(parents=True)
    core_path.write_text(json.dumps({
        "schema": "ztare-abduced-core-v1",
        "spec": core,
        "transitions": 1,
        "matched_transitions": 0,
        "residuals": [],
    }), encoding="utf-8")

    assert mod._load_prior_spec(project)["verdict"] == "missing"
    assert mod._load_abduced_core_spec(project) == core
    assert mod._load_warm_prior_spec(project) == core
    assert not (project / "workspace" / "champion_spec.json").exists()


def test_arc3_play_loads_world_model_spec_as_advice(tmp_path):
    """The play loop's compiled-advice loader accepts the preferred
    WORLD_MODEL_SPEC carrier, not only hand-written step functions."""
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.adapter import episode_log_path

    mod = _load_arc3_play_loop()
    s = ((6, 6, 0),)
    s2 = ((6, 0, 0),)
    log = EpisodeLog()
    log.append(s, 0, s2, t=0)
    log.write_jsonl(episode_log_path(tmp_path))
    (tmp_path / "test_model.py").write_text(
        "WORLD_MODEL_SPEC = {'actions': {'0': [{'op': 'identity'}]}, "
        "'always': [{'op': 'consume_extremal', 'color': 6, 'replacement': 0, "
        "'axis': 'row', 'extreme': 'max'}]}\n"
    )

    model, progress, goal, source = mod._load_advice_model(tmp_path)
    assert source == "test_model"
    assert progress is None and goal is None
    assert model(s, 0, 0) == s2


def test_arc3_play_loads_candidate_memory_patch_base_advice(tmp_path):
    """Compiled advice includes candidate_memory, not only root test_model.py.

    Root artifacts may be stale after a rejected iteration. If a hash-bound
    patch-base carrier in candidate memory replays the current log, advice mode
    should use that carrier before falling to sprint.
    """
    import hashlib
    import json
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.adapter import episode_log_path

    mod = _load_arc3_play_loop()
    s = ((1, 0),)
    s2 = ((0, 1),)
    log = EpisodeLog()
    log.append(s, 0, s2, t=0)
    log.write_jsonl(episode_log_path(tmp_path))
    (tmp_path / "test_model.py").write_text(
        "def step(state, action, t):\n    return state\n"
    )
    submissions = tmp_path / "workspace" / "submissions"
    submissions.mkdir(parents=True)
    base = submissions / "base.py"
    base.write_text("def step(state, action, t):\n    return ((0, 1),)\n")
    sha = hashlib.sha256(base.read_bytes()).hexdigest()
    wrapper = submissions / "wrapper.py"
    wrapper.write_text(
        "PATCH_BASE = {'source_ref': 'workspace/submissions/base.py', "
        f"'sha256': '{sha}'}}\n\n"
        "def PATCH_DELTA(base_next, state, action, t):\n"
        "    return base_next\n"
    )
    (tmp_path / "workspace" / "candidate_memory.json").write_text(json.dumps({
        "records": [{
            "submission": "workspace/submissions/wrapper.py",
            "sha": "wrapped",
            "visible_exact_rows": 1,
            "visible_wrong_cells": 0,
            "passed_gates": 2,
            "gate_score": 0.6667,
        }]
    }))

    model, progress, goal, source = mod._load_advice_model(tmp_path)

    assert source == "candidate_memory:wrapped"
    assert progress is None and goal is None
    assert model(s, 0, 0) == s2


def test_sprint_ceiling_reflex_hands_open_cards_to_governed_owner(tmp_path, monkeypatch):
    """Sprint triages the ceiling but cannot implement through a second door."""
    from types import SimpleNamespace
    import json

    mod = _load_arc3_play_loop()
    log = _rotation_residual_log()
    cfg = _setup_sprint_project(tmp_path, log)
    out = mod._sprint(tmp_path, SimpleNamespace(action_arity=1), cfg, None, None)
    assert any(r.get("status") == "abduction_partial" for r in out["rounds"])
    assert out["grammar_reflex"][0]["status"] == "proposals_routed"
    ledger = tmp_path / "workspace" / "operator_proposals.jsonl"
    rows = [json.loads(l) for l in ledger.read_text().splitlines() if l.strip()]
    assert rows
    assert all(r.get("disposition") not in {"accepted", "rejected"} for r in rows)
    receipt = json.loads((tmp_path / "workspace" / "latest_sprint_receipt.json").read_text())
    assert receipt["status"] == "abduction_partial"
    assert receipt["transition_model_mismatch"] is False
    assert receipt["terminal_verifier_model_mismatch"] is False
def test_sprint_uses_candidate_goal_before_goal_exemplar(tmp_path, monkeypatch):
    """A candidate goal predicate is steering, not authority; it may guide the
    planner before any terminal exemplar exists because the sealed environment
    still decides whether a level was completed."""
    from types import SimpleNamespace
    from ztare.worldmodel.episode_log import EpisodeLog

    mod = _load_arc3_play_loop()
    log = EpisodeLog()
    state = ((0, 1),)
    log.append(state, 0, state, t=0)
    cfg = _setup_sprint_project(tmp_path, log)
    seen = {"goal": None}

    def fake_play(adapter, play_model, **kw):
        seen["goal"] = kw.get("goal_fn")
        return SimpleNamespace(status="saturated", steps_executed=0, levels_gained=0,
                               saturated=True, observed_transitions=[], lives=1)

    marker_goal = lambda _grid: False  # noqa: E731
    monkeypatch.setattr(mod, "_play_round_multilife", fake_play)
    out = mod._sprint(tmp_path, SimpleNamespace(action_arity=1), cfg,
                      None, marker_goal,
                      champion_model=lambda s, a, t: s)
    assert seen["goal"] is marker_goal
    assert out["rounds"][0]["pursuit"] == "saturated"


def test_sprint_grammar_reflex_flag_off_restores_old_behavior(tmp_path, monkeypatch):
    """ZTARE_GRAMMAR_REFLEX=0 restores the old ceiling->checkpoint behavior: the
    reflex is never invoked and the round is a plain abduction_partial."""
    from types import SimpleNamespace
    from ztare.worldmodel import grammar_reflex as gr

    mod = _load_arc3_play_loop()
    log = _rotation_residual_log()
    cfg = _setup_sprint_project(tmp_path, log)
    monkeypatch.setenv("ZTARE_GRAMMAR_REFLEX", "0")
    called = {"n": 0}
    monkeypatch.setattr(gr, "route_operator_proposals",
                        lambda *a, **k: called.__setitem__("n", called["n"] + 1))

    out = mod._sprint(tmp_path, SimpleNamespace(action_arity=1), cfg, None, None)
    assert called["n"] == 0
    assert any(r.get("status") == "abduction_partial" for r in out["rounds"])
    assert "grammar_reflex" not in out
    receipt = json.loads((tmp_path / "workspace" / "latest_sprint_receipt.json").read_text())
    assert receipt["status"] == "abduction_partial"
    assert receipt["terminal_verifier_model_mismatch"] is False


def test_spec_abduction_recovers_periodic_consume_schedule():
    """A variable-rate depleting bar: base consumes one cell every step, with an
    extra phase-gated consume on t%3==0."""
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.spec_abduction import abduce_spec
    from ztare.worldmodel.spec_catalog import lower_spec

    truth, err = lower_spec({
        "actions": {"0": [{"op": "identity"}]},
        "always": [{"op": "consume_extremal", "color": 6, "replacement": 0,
                    "axis": "row", "extreme": "max"},
                   {"op": "consume_extremal", "color": 6, "replacement": 0,
                    "axis": "row", "extreme": "max", "when_phase": [3, 0]}]})
    assert truth is not None, err
    base = ((0, 0, 0, 0, 0, 0),
            (6, 6, 6, 6, 6, 6),
            (0, 0, 0, 0, 0, 0))
    log = EpisodeLog()
    for t in range(12):
        log.append(base, 0, truth(base, 0, t), t=t)

    r = abduce_spec(log, 1)
    assert r.replay_ok and r.status == "spec_identified", r.detail
    timers = [rl for rl in r.spec["always"]
              if rl.get("op") == "consume_extremal" and rl.get("color") == 6]
    assert any(not rl.get("when_phase") for rl in timers), r.spec["always"]
    assert any(rl.get("when_phase") == [3, 0] for rl in timers), r.spec["always"]


def test_spec_abduction_recovers_rational_rate_consume_before_phase():
    """A Bresenham 3/2 depleting bar is one rate rule, not phase decomposition."""
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.spec_abduction import abduce_spec
    from ztare.worldmodel.spec_catalog import lower_spec

    truth, err = lower_spec({
        "actions": {"0": [{"op": "identity"}]},
        "always": [{"op": "consume_extremal", "color": 6, "replacement": 0,
                    "axis": "row", "extreme": "max", "rate": [3, 2]}]})
    assert truth is not None, err
    base = ((0, 0, 0, 0, 0, 0, 0, 0),
            (6, 6, 6, 6, 6, 6, 6, 6),
            (0, 0, 0, 0, 0, 0, 0, 0))
    # Start at t=1 so the visible counts alternate 2,1 under floor-difference.
    log = EpisodeLog()
    for t in range(1, 13):
        log.append(base, 0, truth(base, 0, t), t=t)

    r = abduce_spec(log, 1)
    assert r.replay_ok and r.status == "spec_identified", r.detail
    timers = [rl for rl in r.spec["always"]
              if rl.get("op") == "consume_extremal" and rl.get("color") == 6]
    assert len(timers) == 1, r.spec["always"]
    assert timers[0].get("rate") == [3, 2], timers
    assert all("when_phase" not in rl for rl in timers), r.spec["always"]


def test_spec_abduction_quotient_scores_duplicate_rows_identically_and_fewer_calls(monkeypatch):
    """Duplicate transitions with no visible time feature are one score class."""
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.spec_abduction import _install_score_context, _mismatch_count
    from ztare.worldmodel.spec_catalog import lower_spec

    spec = {"actions": {"0": [{"op": "identity"}]}, "always": []}
    base_step, err = lower_spec(spec)
    assert base_step is not None, err
    s = ((1, 2), (3, 4))
    log = EpisodeLog()
    for t in range(240):
        log.append(s, 0, s, t=t)

    def counted(step_calls):
        def _step(g, a, t):
            step_calls["n"] += 1
            return base_step(g, a, t)
        _step._ztare_world_model_spec = spec
        return _step

    monkeypatch.setenv("ZTARE_QUOTIENT_SCORE", "0")
    _install_score_context(log)
    off_calls = {"n": 0}
    off_bad = _mismatch_count(counted(off_calls), log)

    monkeypatch.setenv("ZTARE_QUOTIENT_SCORE", "1")
    _install_score_context(log)
    on_calls = {"n": 0}
    on_bad = _mismatch_count(counted(on_calls), log)

    assert on_bad == off_bad == 0
    assert on_calls["n"] == 1
    assert off_calls["n"] == len(log)


def test_spec_abduction_quotient_survives_identity_preserving_filtered_log(monkeypatch):
    """Noise deferral must filter by Transition objects, not rebuild rows."""
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.spec_abduction import _install_score_context, _mismatch_count
    from ztare.worldmodel.spec_catalog import lower_spec

    spec = {"actions": {"0": [{"op": "identity"}]}, "always": []}
    base_step, err = lower_spec(spec)
    assert base_step is not None, err
    s = ((1, 2), (3, 4))
    log = EpisodeLog()
    for t in range(240):
        log.append(s, 0, s, t=t)
    kept = EpisodeLog([tr for i, tr in enumerate(log) if i % 2 == 0])

    calls = {"n": 0}

    def counted(g, a, t):
        calls["n"] += 1
        return base_step(g, a, t)
    counted._ztare_world_model_spec = spec

    monkeypatch.setenv("ZTARE_QUOTIENT_SCORE", "1")
    _install_score_context(log)
    assert _mismatch_count(counted, kept) == 0
    assert calls["n"] == 1


def test_spec_abduction_quotient_rate_candidate_uses_raw_t(monkeypatch):
    """A rate-bearing rule cannot quotient rows that differ only by raw t."""
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.spec_abduction import _install_score_context, _mismatch_count
    from ztare.worldmodel.spec_catalog import lower_spec

    spec = {"actions": {"0": [{"op": "identity"}]},
            "always": [{"op": "consume_extremal", "color": 6, "replacement": 0,
                        "axis": "row", "extreme": "max", "rate": [3, 2]}]}
    step, err = lower_spec(spec)
    assert step is not None, err
    s = ((0, 0, 0, 0), (6, 6, 6, 6), (0, 0, 0, 0))
    log = EpisodeLog()
    for _ in range(30):
        for t in (0, 1):
            log.append(s, 0, step(s, 0, t), t=t)

    calls = {"n": 0}

    def counted(g, a, t):
        calls["n"] += 1
        return step(g, a, t)
    counted._ztare_world_model_spec = spec

    monkeypatch.setenv("ZTARE_QUOTIENT_SCORE", "1")
    _install_score_context(log)
    assert _mismatch_count(counted, log) == 0
    assert calls["n"] == 2


def test_spec_abduction_galois_footprint_prunes_dominated_candidate(monkeypatch):
    """A candidate that cannot write an observed changed cell loses by bound."""
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.spec_abduction import (
        _galois_summary, _install_score_context, _mismatch_count)
    from ztare.worldmodel.spec_catalog import lower_spec

    truth = {"actions": {"0": [{"op": "recolor_map", "mapping": {"1": 2}}]},
             "always": []}
    dominated = {"actions": {"0": [{"op": "identity"}]}, "always": []}
    s = ((1, 0), (0, 0))
    log = EpisodeLog()
    log.append(s, 0, ((2, 0), (0, 0)), t=0)

    def run(flag):
        monkeypatch.setenv("ZTARE_GALOIS_PRUNE", flag)
        monkeypatch.setenv("ZTARE_QUOTIENT_SCORE", "1")
        _install_score_context(log)
        best_spec, best_bad = None, None
        for spec in (truth, dominated):
            step, err = lower_spec(spec)
            assert step is not None, err
            bad = _mismatch_count(step, log, incumbent=best_bad)
            if best_bad is None or bad < best_bad:
                best_spec, best_bad = spec, bad
        return best_spec, best_bad, _galois_summary()

    off_spec, off_bad, off_stats = run("0")
    on_spec, on_bad, on_stats = run("1")

    assert on_spec == off_spec == truth
    assert on_bad == off_bad == 0
    assert off_stats["footprint_pruned"] == 0
    assert on_stats["footprint_pruned"] == 1
    assert on_stats["bounded_candidates"] == 1
    assert on_stats["footprint_pruned_fraction"] == 1.0


def test_spec_abduction_scoring_does_not_alias_python_object_identities(monkeypatch):
    """Distinct targets and specs remain distinct even under an id collision."""
    from ztare.worldmodel import spec_abduction as SA
    from ztare.worldmodel.episode_log import EpisodeLog

    monkeypatch.setattr(SA, "id", lambda _obj: 1, raising=False)
    assert SA._grid_wrong_cells(((0,),), ((0,),)) == 0
    assert SA._grid_wrong_cells(((0,),), ((1,),)) == 1

    state = ((1, 0), (0, 0))
    target = ((2, 0), (0, 0))
    log = EpisodeLog()
    log.append(state, 0, target, t=0)
    identity = {"actions": {"0": [{"op": "identity"}]}, "always": []}
    recolor = {
        "actions": {"0": [{"op": "recolor_map", "mapping": {"1": 2}}]},
        "always": [],
    }

    def identity_step(g, _a, _t):
        return g

    def recolor_step(_g, _a, _t):
        return target

    identity_step._ztare_world_model_spec = identity
    recolor_step._ztare_world_model_spec = recolor
    monkeypatch.setenv("ZTARE_QUOTIENT_SCORE", "1")
    SA._install_score_context(log)

    assert SA._galois_footprint_lower_bound(identity_step, log, "cell") == 1
    assert SA._galois_footprint_lower_bound(recolor_step, log, "cell") == 0


def test_spec_abduction_incumbent_early_exit_preserves_winner(monkeypatch):
    """A losing full score aborts after exceeding the incumbent.

    This early exit is the cheap incumbent-delta scorer, not the expensive
    Galois footprint bound. It stays active even when `ZTARE_GALOIS_PRUNE=0`.
    """
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.spec_abduction import (
        _galois_summary, _install_score_context, _mismatch_count)

    log = EpisodeLog()
    for t in range(12):
        s = ((t, 0), (0, 0))
        log.append(s, 0, ((t + 1, 0), (0, 0)), t=t)

    def run(flag):
        monkeypatch.setenv("ZTARE_GALOIS_PRUNE", flag)
        monkeypatch.setenv("ZTARE_QUOTIENT_SCORE", "0")
        _install_score_context(log)
        calls = {"bad": 0}

        def good(g, _a, _t):
            return ((g[0][0] + 1, 0), (0, 0))

        def bad(g, _a, _t):
            calls["bad"] += 1
            return g

        best_name, best_bad = None, None
        for name, step in (("good", good), ("bad", bad)):
            score = _mismatch_count(step, log, incumbent=best_bad)
            if best_bad is None or score < best_bad:
                best_name, best_bad = name, score
        return best_name, best_bad, calls["bad"], _galois_summary()

    off_name, off_bad, off_calls, off_stats = run("0")
    on_name, on_bad, on_calls, on_stats = run("1")

    assert on_name == off_name == "good"
    assert on_bad == off_bad == 0
    assert on_calls == 1
    assert off_calls == 1
    assert off_stats["footprint_pruned"] == 0
    assert on_stats["early_exited"] == 1
    assert off_stats["early_exited"] == 1


def test_refinement_ladder_signature_routes_rate_residual():
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.refinement_ladder import default_rungs, extract_residual_signature
    from ztare.worldmodel.spec_catalog import lower_spec

    spec = {"actions": {"0": [{"op": "identity"}]},
            "always": [{"op": "consume_extremal", "color": 6, "replacement": 0,
                        "axis": "row", "extreme": "max", "count": 0}]}
    step, err = lower_spec(spec)
    assert step is not None, err
    base = ((0, 0, 0, 0), (6, 6, 6, 6), (0, 0, 0, 0))
    log = EpisodeLog()
    for t, n in enumerate((1, 2, 1, 2)):
        nxt = ((0, 0, 0, 0), tuple([6] * (4 - n) + [0] * n), (0, 0, 0, 0))
        log.append(base, 0, nxt, t=t)

    sig = extract_residual_signature(spec, step, log, {})
    shortlist = sorted([r for r in default_rungs({}) if r.applies(sig)],
                       key=lambda r: r.cost_rank)
    assert sig["counts_vary_with_t"] is True
    assert sig["counts_vary_by_color"][6] is True
    assert sig["consume_residual_overlap"] is True
    assert "rational_rate_consume_refine" in {r.name for r in shortlist}
    assert shortlist[0].name == "component_scope_consume_refine"


def test_open_strategy_card_does_not_skip_deterministic_pre_abduction():
    src = Path("scripts/public/control/arc3_play_loop.py").read_text()
    msg = "deterministic abduction still runs"
    assert msg in src
    window = src[src.index("strategy_pending = _has_open_strategy_cards"):src.index(
        "except Exception as _ab_err"
    )]
    assert "pre-abduction shortcut skipped" not in window
    assert "if not strategy_pending or advice_only" not in window
    assert "_ab = abduce_spec(" in window
    assert "_rd(_ab.step_fn, _hold) >= len(_hold)" in window


def test_refinement_ladder_signature_routes_guard_split():
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.refinement_ladder import default_rungs, extract_residual_signature
    from ztare.worldmodel.spec_catalog import lower_spec

    spec = {"actions": {"0": [{"op": "identity"}]},
            "always": [{"op": "consume_extremal", "color": 6, "replacement": 0,
                        "axis": "row", "extreme": "max", "count": 2,
                        "when_overlap": [[9], 0, 0, 0, 0]}]}
    step, err = lower_spec(spec)
    assert step is not None, err
    base = ((0, 0, 0, 0), (6, 6, 6, 6), (0, 0, 0, 0))
    log = EpisodeLog()
    for t, n in enumerate((1, 0, 1, 0)):
        nxt = ((0, 0, 0, 0), tuple([6] * (4 - n) + [0] * n), (0, 0, 0, 0))
        log.append(base, 0, nxt, t=t)

    sig = extract_residual_signature(spec, step, log, {})
    shortlist = sorted([r for r in default_rungs({}) if r.applies(sig)],
                       key=lambda r: r.cost_rank)
    assert sig["guard_splittable"] is True
    assert shortlist[0].axis == "region_guard"
    assert {r.axis for r in shortlist} & {"region_guard", "effect", "dest"}


def test_refinement_ladder_does_not_route_consume_rungs_on_unrelated_residual():
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.refinement_ladder import default_rungs, extract_residual_signature
    from ztare.worldmodel.spec_catalog import lower_spec

    spec = {"actions": {"0": [{"op": "identity"}]},
            "always": [{"op": "consume_extremal", "color": 11, "replacement": 3,
                        "axis": "row", "extreme": "min"}]}
    step, err = lower_spec(spec)
    assert step is not None, err
    s = (
        (11, 0, 0),
        (8, 0, 0),
    )
    s_next = (
        (3, 0, 0),
        (3, 0, 0),
    )
    log = EpisodeLog()
    log.append(s, 0, s_next, t=0)

    sig = extract_residual_signature(spec, step, log, {})
    routed = {r.name: r.applies(sig)
              for r in default_rungs({"effect_refine": False, "display_refine": False})}

    assert sig["wrong_cell_count"] == 1
    assert sig["has_consume"] is True
    assert sig["consume_residual_overlap"] is False
    assert routed["component_scope_consume_refine"] is False
    assert routed["rational_rate_consume_refine"] is False
    assert routed["count_guard_consume_refine"] is False
    assert routed["periodic_consume_refine"] is False


def test_refinement_ladder_caps_at_eight_iterations():
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.refinement_ladder import Rung, run_refinement_ladder

    class Step:
        def __init__(self, score):
            self.score = score
        def __call__(self, s, a, t):
            return s

    log = EpisodeLog()
    log.append(((1,),), 0, ((2,),), t=0)
    calls = []

    def run(spec, step, log, env):
        calls.append(step.score)
        return spec, Step(step.score - 1)

    rung = Rung("fake_improver", "rate", 1, lambda sig: True, run)
    _spec, out_step = run_refinement_ladder(
        {"actions": {"0": [{"op": "identity"}]}, "always": []},
        Step(10), log, {}, rungs=[rung], max_iterations=8,
        score_fn=lambda step, _log, _env: step.score,
    )
    assert len(calls) == 8
    assert out_step.score == 2


def test_refinement_ladder_flag_zero_runs_legacy_sequence(monkeypatch):
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel import spec_abduction as SA
    from ztare.worldmodel.spec_catalog import lower_spec

    truth, err = lower_spec({
        "actions": {"0": [{"op": "translate_block", "match_colors": [9],
                           "dy": 0, "dx": 1, "require_dest_colors": [3],
                           "fill_color": 3}]},
        "always": [{"op": "consume_extremal", "color": 6, "replacement": 0,
                    "axis": "row", "extreme": "max"}]})
    assert truth is not None, err
    log = EpisodeLog()
    s = ((9, 3, 3), (6, 6, 6))
    for t in range(3):
        s2 = truth(s, 0, t)
        log.append(s, 0, s2, t=t)
        s = s2

    calls = []

    def no_op(name):
        def _f(spec, log):
            calls.append(name)
            return spec, SA.lower_spec(spec)[0]
        return _f

    names = [
        "_action_scope_refine",
        "_region_guard_refine",
        "_effect_guard_refine",
        "_dest_guard_refine",
        "_rational_rate_consume_refine",
        "_periodic_consume_refine",
        "_prune_region_writes",
        "_region_state_refine",
        "_derived_display_refine",
    ]
    for name in names:
        monkeypatch.setattr(SA, name, no_op(name))
    monkeypatch.setenv("ZTARE_REFINE_LADDER", "0")

    result = SA.abduce_spec(log, 1)
    assert result.step_fn is not None
    assert calls == names


def test_operator_proposal_triage_prefers_parameter_generalization():
    """A residual explained by the same family with only magnitude wrong is not
    triaged as a novel operator."""
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.operator_proposals import propose_operators

    s = ((1, 0, 0, 0),)
    s_next = ((0, 0, 1, 0),)
    log = EpisodeLog()
    log.append(s, 0, s_next, t=0)
    spec = {"actions": {"0": [{"op": "translate_block", "match_colors": [1],
                               "dy": 0, "dx": 1,
                               "require_dest_colors": [0], "fill_color": 0}]},
            "always": []}

    cards = propose_operators(log, spec)
    assert cards, "expected one residual card"
    assert cards[0]["kind"] == "parameter_generalization", cards[0]
    assert cards[0]["parameter_generalization"]["family"] == "translate_block"
    assert cards[0]["parameter_generalization"]["suspect_parameter"] == "dy_dx"
