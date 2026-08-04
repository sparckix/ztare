"""Planted-synthetic acceptance for the pattern_write operator family.

Machinery Rules discipline: a new catalog operator enters only through a
planted synthetic where ONLY the new family explains the transitions, plus
non-regression checks. The planted law is the RESTORATION class: a mover
translates under actions, and when a resource strip is exhausted the strip
rewrites to its remembered full pattern (a mid-life refill — no reset, no
mover crossing, so region_event cannot express the trigger and translate /
recolor cannot express the write).
"""
from __future__ import annotations

import json

from ztare.worldmodel.episode_log import EpisodeLog
from ztare.worldmodel.spec_abduction import _abduce_pattern_write, abduce_spec
from ztare.worldmodel.spec_catalog import lower_spec, validate_spec

H = W = 12
BAR_ROW = 10
BAR_COLS = list(range(2, 8))          # 6-cell resource strip
FULL, EMPTY = 7, 1
MOVER, FLOOR = 5, 0


def _mk_grid(mover_x: int, bar_fill: int):
    g = [[FLOOR] * W for _ in range(H)]
    g[2][mover_x] = MOVER
    for k, x in enumerate(BAR_COLS):
        g[BAR_ROW][x] = FULL if k < bar_fill else EMPTY
    return g


def _sealed_step(g, a):
    """Generating law (sealed): mover moves +/-1 col; each move burns one bar
    cell; when the bar hits empty the strip refills to FULL (mid-life)."""
    mover_x = next(x for x in range(W) if g[2][x] == MOVER)
    fill = sum(1 for x in BAR_COLS if g[BAR_ROW][x] == FULL)
    nx = min(W - 1, mover_x + 1) if a == 1 else max(0, mover_x - 1)
    new_fill = fill - 1
    if new_fill <= 0:
        new_fill = len(BAR_COLS)      # the restoration law
    return _mk_grid(nx, new_fill)


def _episode(tmp_path):
    rows = []
    g = _mk_grid(3, len(BAR_COLS))
    t = 0
    import itertools
    for a in itertools.islice(itertools.cycle([1, 1, 0, 1]), 40):
        nxt = _sealed_step(g, a)
        rows.append({"t": t, "s": g, "a": a, "s_next": nxt})
        g, t = nxt, t + 1
    p = tmp_path / "planted_pattern_write.jsonl"
    with p.open("w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    return EpisodeLog.read_jsonl(p)


def test_miner_proposes_pattern_write_on_refill_diff():
    g0 = _mk_grid(3, 1)                       # one bar cell left
    g1 = _sealed_step(g0, 1)                  # burn -> refill fires
    diff = [(y, x, g0[y][x], g1[y][x])
            for y in range(H) for x in range(W) if g0[y][x] != g1[y][x]]
    props = _abduce_pattern_write(g0, g1, diff)
    bar_props = [p for p in props if p["rect"][0] == BAR_ROW]
    assert bar_props, f"no bar-region pattern_write proposed; got {props}"
    rule = bar_props[0]
    assert validate_spec({"actions": {"0": [rule]}, "always": []}) is None


def test_pattern_write_lowering_executes_and_guards_compose():
    rule = {
        "op": "pattern_write",
        "rect": [BAR_ROW, BAR_COLS[0], BAR_ROW, BAR_COLS[-1]],
        "pattern": [FULL] * len(BAR_COLS),
        "when_count": [FULL, None, 0],        # fires only when no FULL cells
    }
    frag, err = lower_spec({"actions": {"0": [rule]}, "always": []})
    assert not err and frag is not None
    empty = _mk_grid(3, 0)
    full = _mk_grid(3, len(BAR_COLS))
    out = frag(empty, 0, 0)
    assert [out[BAR_ROW][x] for x in BAR_COLS] == [FULL] * len(BAR_COLS)
    # guard vetoes on a non-exhausted bar: rule is a no-op
    out2 = frag(full, 0, 0)
    assert [list(r) for r in out2] == full


def test_abduce_recovers_planted_restoration_law(tmp_path):
    log = _episode(tmp_path)
    ab = abduce_spec(log, 2)
    fn = getattr(ab, "step_fn", None)
    assert fn is not None, f"no step_fn from abduction: {ab}"
    exact = sum(
        1 for tr in log
        if (p := fn([list(r) for r in tr.s], tr.a, tr.t)) is not None
        and [list(r) for r in p] == [list(r) for r in tr.s_next]
    )
    n = len(list(log))
    # the acceptance bar: the refill rows are the discriminator — without
    # pattern_write the best expressible spec misses every refill event
    refills = sum(
        1 for tr in log
        if sum(1 for x in BAR_COLS if tr.s_next[BAR_ROW][x] == FULL)
        > sum(1 for x in BAR_COLS if tr.s[BAR_ROW][x] == FULL)
    )
    assert refills >= 3, "planted episode must witness several refills"
    assert exact == n, (
        f"planted restoration law not recovered: {exact}/{n} exact "
        f"(refill witnesses: {refills})"
    )
