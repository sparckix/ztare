"""Typed refinement ladder for spec-abduction post-passes.

This module is intentionally a wrapper layer: every rung delegates to the
existing spec_abduction refine function, and the ladder accepts only strict
wrong-cell improvements.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Callable, Literal


Axis = Literal[
    "phase", "rate", "count_guard", "component_scope", "dest", "effect",
    "region_state", "region_guard",
]


@dataclass(frozen=True)
class Rung:
    name: str
    axis: Axis
    cost_rank: int
    applies: Callable[[dict], bool]
    run: Callable[[dict, object, object, dict], tuple[dict, object]]


def _sa():
    from ztare.worldmodel import spec_abduction

    return spec_abduction


def _wrap_refine(func_name: str):
    def _run(spec, step, log, env):
        func = getattr(_sa(), func_name)
        env["_self_scored_rung"] = func_name
        return func(spec, log)

    return _run


def _selected_mover_colors(spec: dict) -> list[int]:
    return sorted({int(c) for rules in spec.get("actions", {}).values()
                   for r in rules if r.get("op") == "translate_block"
                   for c in r.get("match_colors", [])})


def _run_dest_broaden(spec, step, log, env):
    sa = _sa()
    mover = env.get("selected_mover_colors") or _selected_mover_colors(spec)
    b_actions = sa._broaden_dests(spec.get("actions", {}), log, mover)
    st, _err = sa.lower_spec({"actions": b_actions, "always": spec.get("always", [])})
    if st is None:
        return spec, step
    return {"actions": b_actions, "always": spec.get("always", [])}, st


def _wrong_cells_for(step, log, env: dict, score_fn=None) -> int:
    if score_fn is not None:
        return int(score_fn(step, log, env))
    sa = _sa()
    env_frames = env.get("env_frames")
    if env_frames is None:
        from ztare.worldmodel.gates import env_frame_indices

        env_frames = env_frame_indices(log)
        env["env_frames"] = env_frames
    return sa._wrong_cell_count(step, log, env_frames)


def _residual_rows(step, log, env_frames: set[int]) -> list[tuple[int, object, object, list]]:
    rows = []
    for i, tr in enumerate(log):
        if i in env_frames:
            continue
        pred = step(tr.s, tr.a, tr.t) if step is not None else None
        if pred is None:
            wrong = [(y, x) for y in range(len(tr.s_next)) for x in range(len(tr.s_next[0]))]
        else:
            wrong = [(y, x) for y in range(len(pred)) for x in range(len(pred[0]))
                     if pred[y][x] != tr.s_next[y][x]]
        if wrong:
            rows.append((i, tr, pred, wrong))
    return rows


def _rule_family_counts_vary(spec: dict, rows: list[tuple[int, object, object, list]]) -> dict[int, bool]:
    sa = _sa()
    by_color: dict[int, list[tuple[int, int]]] = defaultdict(list)
    rules = list(spec.get("always", []))
    for rs in spec.get("actions", {}).values():
        rules.extend(rs)
    for rule in rules:
        if rule.get("op") != "consume_extremal":
            continue
        color = int(rule["color"])
        for _i, tr, _pred, _wrong in rows:
            n = sa._transition_consume_count(tr, rule)
            if n is not None:
                by_color[color].append((int(tr.t), int(n)))
    return {c: len({n for _t, n in obs}) > 1 and len({t for t, _n in obs}) > 1
            for c, obs in by_color.items()}


def _has_magnitude_only(spec: dict, rows: list[tuple[int, object, object, list]]) -> bool:
    sa = _sa()
    for rules in [spec.get("always", [])] + list(spec.get("actions", {}).values()):
        for rule in rules:
            if rule.get("op") != "consume_extremal":
                continue
            expected = int(rule.get("count", 1))
            for _i, tr, _pred, _wrong in rows:
                n = sa._transition_consume_count(tr, rule)
                if n is not None and n != expected:
                    return True
    return False


def _has_consume_residual_overlap(
    spec: dict,
    rows: list[tuple[int, object, object, list]],
) -> bool:
    """Whether the current residual belongs to a consume rule's value family.

    Operator presence is too broad for a refinement scheduler: once a consume
    repair lands, unrelated residuals should not keep re-entering consume rungs.
    This test quotients by the cells still wrong and the source values of
    consume laws; it carries no substrate-specific vocabulary.
    """
    source_colors = set()
    for rules in [spec.get("always", [])] + list(spec.get("actions", {}).values()):
        for rule in rules:
            if rule.get("op") != "consume_extremal":
                continue
            source_colors.add(int(rule["color"]))
    if not source_colors:
        return False
    for _i, tr, pred, wrong in rows:
        for y, x in wrong:
            vals = {int(tr.s[y][x])}
            if pred is not None:
                vals.add(int(pred[y][x]))
            if vals & source_colors:
                return True
    return False


def _all_non_env_rows(log, env_frames: set[int]) -> list[tuple[int, object, object, list]]:
    return [(i, tr, None, []) for i, tr in enumerate(log) if i not in env_frames]


def _has_guard_split(spec: dict, rows: list[tuple[int, object, object, list]]) -> bool:
    sa = _sa()
    for rules in [spec.get("always", [])] + list(spec.get("actions", {}).values()):
        for rule in rules:
            if rule.get("op") == "consume_extremal":
                hits = [sa._effect_present(rule, tr) for _i, tr, _pred, _wrong in rows]
            elif rule.get("op") == "translate_block":
                hits = [sa._mover_moved(rule, tr) for _i, tr, _pred, _wrong in rows]
            else:
                frag = sa._rule_bare_frag(rule)
                hits = [sa._rule_fired_in_reality(frag, tr) for _i, tr, _pred, _wrong in rows]
            if any(hits) and not all(hits):
                return True
    return False


def _has_region_state_residual(rows: list[tuple[int, object, object, list]]) -> bool:
    if not rows:
        return False
    sa = _sa()
    cells = {(y, x) for _i, _tr, _pred, wrong in rows for (y, x) in wrong}
    if len(cells) < 4:
        return False
    y0, x0, y1, x1 = sa._bbox([list(c) for c in cells])
    if (y1 - y0 + 1) * (x1 - x0 + 1) > 400:
        return False
    rcells = [(y, x) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)]

    def content(g):
        return tuple(g[y][x] for y, x in rcells)

    state_counts = defaultdict(int)
    edges = []
    for _i, tr, _pred, _wrong in rows:
        c0, c1 = content(tr.s), content(tr.s_next)
        state_counts[c0] += 1
        state_counts[c1] += 1
        if c0 != c1:
            edges.append((c0, c1))
    states = [s for s, n in state_counts.items() if n >= 2]
    if len(states) < 2 or not edges:
        return False
    sidx = {s: i for i, s in enumerate(states)}
    m = {}
    for c0, c1 in edges:
        if c0 not in sidx or c1 not in sidx:
            continue
        f, t = sidx[c0], sidx[c1]
        if m.get(f, t) != t:
            return False
        m[f] = t
    return bool(m) and not sa._cellwise_reproducible(states, m)


def _has_compact_recurrent_residual(rows: list[tuple[int, object, object, list]]) -> bool:
    """Local alpha-map over counterexamples: the same compact wrong-cell support
    recurs. This is substrate-neutral routing for readout/latch synthesis; it
    depends on the quotient of residual supports, not operator vocabulary."""
    if not rows:
        return False
    counts = defaultdict(int)
    for _i, _tr, _pred, wrong in rows:
        cells = tuple(sorted((int(y), int(x)) for y, x in wrong))
        if len(cells) < 4:
            continue
        ys = [y for y, _x in cells]
        xs = [x for _y, x in cells]
        area = (max(ys) - min(ys) + 1) * (max(xs) - min(xs) + 1)
        if area > 400:
            continue
        counts[cells] += 1
    return any(n >= 2 for n in counts.values())


def extract_residual_signature(spec: dict, step, log, env: dict | None = None) -> dict:
    """Return compact residual features for the current champion."""
    env = dict(env or {})
    if "env_frames" not in env:
        from ztare.worldmodel.gates import env_frame_indices

        env["env_frames"] = env_frame_indices(log)
    env_frames = set(env["env_frames"])
    rows = _residual_rows(step, log, env_frames)
    all_rows = _all_non_env_rows(log, env_frames)
    varies = _rule_family_counts_vary(spec, rows)
    all_rules = list(spec.get("always", []))
    for rs in spec.get("actions", {}).values():
        all_rules.extend(rs)
    has_translate = any(r.get("op") == "translate_block" for r in all_rules)
    has_consume = any(r.get("op") == "consume_extremal" for r in all_rules)
    consume_residual_overlap = _has_consume_residual_overlap(spec, rows)
    has_region_event = any(r.get("op") == "region_event" for r in all_rules)
    has_writable_region_event = any(r.get("op") == "region_event" and "writes" in r
                                    for r in all_rules)
    has_state_region_event = any(r.get("op") == "region_event" and "content_states" in r
                                 for r in all_rules)
    has_when_overlap = any("when_overlap" in r for r in all_rules)
    return {
        "wrong_transition_count": len(rows),
        "wrong_cell_count": sum(len(wrong) for _i, _tr, _pred, wrong in rows),
        "counts_vary_with_t": any(varies.values()),
        "counts_vary_by_color": varies,
        "compact_recurrent_residual": _has_compact_recurrent_residual(rows),
        "region_consistent_cellwise_inconsistent": _has_region_state_residual(rows),
        "guard_splittable": _has_guard_split(spec, all_rows),
        "magnitude_only": _has_magnitude_only(spec, rows),
        "has_translate": has_translate,
        "has_consume": has_consume,
        "consume_residual_overlap": consume_residual_overlap,
        "has_region_event": has_region_event,
        "has_writable_region_event": has_writable_region_event,
        "has_state_region_event": has_state_region_event,
        "has_when_overlap": has_when_overlap,
    }


def default_rungs(env: dict | None = None) -> list[Rung]:
    env = env or {}
    effect_refine = bool(env.get("effect_refine", True))
    display_refine = bool(env.get("display_refine", True))
    rungs = [
        Rung("action_scope_refine", "region_guard", 10,
             lambda sig: sig["wrong_cell_count"] > 0
             and not sig["has_state_region_event"]
             and (sig["has_when_overlap"] or sig["has_writable_region_event"]),
             _wrap_refine("_action_scope_refine")),
        Rung("region_guard_refine", "region_guard", 20,
             lambda sig: sig["wrong_cell_count"] > 0 and sig["has_translate"]
             and sig["has_region_event"], _wrap_refine("_region_guard_refine")),
    ]
    if effect_refine:
        rungs.extend([
            Rung("effect_guard_refine", "effect", 30,
                 lambda sig: sig["wrong_cell_count"] > 0 and sig["guard_splittable"],
                 _wrap_refine("_effect_guard_refine")),
            Rung("dest_guard_refine", "dest", 40,
                 lambda sig: sig["wrong_cell_count"] > 0 and sig["has_translate"],
                 _wrap_refine("_dest_guard_refine")),
            Rung("dest_broaden_retry", "dest", 45,
                 lambda sig: sig["wrong_cell_count"] > 0 and sig["has_translate"],
                 _run_dest_broaden),
        ])
    rungs.extend([
        # Quotient locality comes before temporal fitting. If a consume family
        # is being measured over the wrong equivalence class, rate/phase rungs
        # see the wrong signal and spend scorer budget on the wrong question.
        Rung("component_scope_consume_refine", "component_scope", 48,
             lambda sig: sig["wrong_cell_count"] > 0 and sig["has_consume"]
             and sig["consume_residual_overlap"],
             _wrap_refine("_component_scope_consume_refine")),
        Rung("rational_rate_consume_refine", "rate", 50,
             lambda sig: sig["has_consume"]
             and sig["consume_residual_overlap"]
             and (sig["counts_vary_with_t"] or sig["magnitude_only"]),
             _wrap_refine("_rational_rate_consume_refine")),
        Rung("count_guard_consume_refine", "count_guard", 58,
             lambda sig: sig["has_consume"]
             and sig["consume_residual_overlap"]
             and (sig["counts_vary_with_t"] or sig["magnitude_only"]),
             _wrap_refine("_count_guard_consume_refine")),
        Rung("periodic_consume_refine", "phase", 60,
             lambda sig: sig["has_consume"]
             and sig["consume_residual_overlap"]
             and (sig["counts_vary_with_t"] or sig["magnitude_only"]),
             _wrap_refine("_periodic_consume_refine")),
        Rung("prune_region_writes", "region_state", 70,
             lambda sig: sig["wrong_cell_count"] > 0 and sig["has_region_event"],
             _wrap_refine("_prune_region_writes")),
    ])
    if display_refine:
        rungs.extend([
            Rung("region_state_refine", "region_state", 80,
                 lambda sig: sig["wrong_cell_count"] > 0
                 and (sig["region_consistent_cellwise_inconsistent"] or sig["has_translate"]),
                 _wrap_refine("_region_state_refine")),
            Rung("derived_display_refine", "region_state", 90,
                 lambda sig: sig["wrong_cell_count"] > 0
                 and (sig["region_consistent_cellwise_inconsistent"]
                      or (sig["has_writable_region_event"]
                          and sig["compact_recurrent_residual"])),
                 _wrap_refine("_derived_display_refine")),
        ])
    return sorted(rungs, key=lambda r: r.cost_rank)


def run_refinement_ladder(spec: dict, step, log, env: dict | None = None, *,
                          rungs: list[Rung] | None = None,
                          max_iterations: int = 8,
                          score_fn=None) -> tuple[dict, object]:
    env = dict(env or {})
    active = list(rungs) if rungs is not None else default_rungs(env)
    spec_cur, step_cur = spec, step
    for iteration in range(int(max_iterations)):
        sig = extract_residual_signature(spec_cur, step_cur, log, env)
        env["last_signature"] = sig
        env["iterations"] = iteration + 1
        if sig["wrong_cell_count"] <= 0:
            break
        before = _wrong_cells_for(step_cur, log, env, score_fn=score_fn)
        improved = False
        for rung in sorted((r for r in active if r.applies(sig)), key=lambda r: r.cost_rank):
            env.pop("_self_scored_rung", None)
            cand_spec, cand_step = rung.run(spec_cur, step_cur, log, env)
            if cand_step is None:
                continue
            self_scored = env.pop("_self_scored_rung", None)
            if self_scored and cand_spec == spec_cur:
                continue
            if self_scored:
                spec_cur, step_cur = cand_spec, cand_step
                env.setdefault("accepted_rungs", []).append(rung.name)
                improved = True
                break
            after = _wrong_cells_for(cand_step, log, env, score_fn=score_fn)
            if after < before:
                spec_cur, step_cur = cand_spec, cand_step
                env.setdefault("accepted_rungs", []).append(rung.name)
                improved = True
                break
        if not improved:
            break
    return spec_cur, step_cur
