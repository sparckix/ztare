"""Deterministic gates for transition-program candidates (GP-250 P0').

Two gates, both fail-closed, both reading only the episode log:

- replay consistency: the candidate must reproduce every observed transition
  exactly. A single mismatch, or any fail-closed (None) evaluation, kills it.
- rollout depth: on a held-out episode the candidate never fit on, the gate
  measures how many consecutive steps it predicts before the first mismatch.
  Depth-at-threshold is the primary generalization metric (panel record,
  2026-07-02): it is the farther-tail discipline with time as the tail axis,
  and it maps onto ARC-AGI-3's action-efficiency scoring.

P1 wiring note: these become registry gates under a new
`substrate.meta['class'] == "interactive_environment"` so the kernel gate
dispatcher routes them; P0' calls them directly from the harness.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

from ztare.worldmodel.episode_log import EpisodeLog
from ztare.worldmodel.transition_identity import (
    authoritative_boundary,
    authoritative_dynamics,
)
from ztare.worldmodel.grid_dsl import Program, evaluate


_EVALUATOR_IMPLEMENTATION_REFS = (
    "common/equivariance.py",
    "common/observation_chart.py",
    "common/patch_base_identity.py",
    "common/sandboxed_python.py",
    "common/worldmodel_carrier_purity.py",
    "worldmodel/carrier_loader.py",
    "worldmodel/episode_log.py",
    "worldmodel/evidence_consolidation.py",
    "worldmodel/gates.py",
    "worldmodel/grammar_extension.py",
    "worldmodel/grid_dsl.py",
    "worldmodel/patch_base_carrier.py",
    "worldmodel/spec_catalog.py",
    "worldmodel/transition_identity.py",
)


def _build_evaluator_implementation_identity() -> dict[str, object]:
    """Capture the transition evaluator loaded by this process.

    The gate owns the equality relation for replay judgments.  Carrier
    lowering, chart identity, boundary classification, and prediction are one
    implementation footprint; caches may add consumer-specific code but may
    not replace or privately reconstruct this set.
    """

    package_root = Path(__file__).resolve().parents[1]
    module_hashes = {
        ref: hashlib.sha256((package_root / ref).read_bytes()).hexdigest()
        for ref in _EVALUATOR_IMPLEMENTATION_REFS
    }
    payload: dict[str, object] = {
        "schema": "ztare-transition-evaluator-implementation-v1",
        "module_hashes": module_hashes,
    }
    payload["sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return payload


_EVALUATOR_IMPLEMENTATION_IDENTITY = _build_evaluator_implementation_identity()


def evaluator_implementation_identity() -> dict[str, object]:
    """Content identity shared by every transition-verdict cache.

    The identity is captured once during module import.  Re-reading source
    files for each judgment can relabel code that is already resident in the
    process after an on-disk edit.  Science/debug phase isolation is the owner
    of code changes; within one process this value is immutable.
    """

    return {
        "schema": _EVALUATOR_IMPLEMENTATION_IDENTITY["schema"],
        "module_hashes": dict(
            _EVALUATOR_IMPLEMENTATION_IDENTITY["module_hashes"]  # type: ignore[arg-type]
        ),
        "sha256": _EVALUATOR_IMPLEMENTATION_IDENTITY["sha256"],
    }


@dataclass(frozen=True)
class GateResult:
    ok: bool
    detail: str


@dataclass(frozen=True)
class ReplayDiagnostics:
    checked_rows: int
    exact_rows: int
    wrong_rows: int
    wrong_cell_count: int
    first_mismatch: str
    first_mismatch_signature: dict | None = None
    mismatch_classes: list[dict] | None = None
    # The full residual, not one point of it: candidates that fix SOME of the
    # wrong rows are invisible under first-mismatch-only reporting (observed
    # 2026-07-11: two candidates both at 13550 exact, identical receipts,
    # leaf could not tell which predicate guesses moved anything).
    residual_table: list[dict] | None = None

    def as_dict(self) -> dict:
        payload = {
            "checked_rows": self.checked_rows,
            "exact_rows": self.exact_rows,
            "wrong_rows": self.wrong_rows,
            "wrong_cell_count": self.wrong_cell_count,
            "first_mismatch": self.first_mismatch,
        }
        if self.first_mismatch_signature:
            payload["first_mismatch_signature"] = self.first_mismatch_signature
        if self.mismatch_classes:
            payload["mismatch_classes"] = self.mismatch_classes
        if self.residual_table:
            payload["residual_table"] = self.residual_table
        return payload


def as_predictor(candidate):
    """Uniform prediction interface over BOTH candidate carriers: a grid_dsl
    Program AST, or a direct python callable (step(grid, action, t) — the
    mutator's native output on real environments; (grid, action) also
    accepted). Fail-closed: any exception or wrong shape predicts None."""
    if callable(candidate):
        def _predict(s, a, t):
            try:
                try:
                    out = candidate(s, a, t)
                except TypeError:
                    out = candidate(s, a)
            except Exception:
                return None
            out = _canonical_grid_prediction(out)
            if out is None:
                return None
            return out
        return _predict
    return lambda s, a, t: evaluate(candidate, s, a, t)


def _canonical_grid_prediction(out):
    if not isinstance(out, (tuple, list)) or not out:
        return None
    rows = []
    for row in out:
        if not isinstance(row, (tuple, list)):
            return None
        rows.append(tuple(row))
    return tuple(rows)


def _counterexample_cells(predicted, real, limit: int = 6) -> str:
    """The falsifying cells, Compiler-Bounce style: feedback that carries the
    counterexample beats verdict-only feedback (measured on the synthetic
    ceiling runs; the governed loop lacked this channel for world models —
    mutators re-derived hypotheses a 2-cell diff would have answered)."""
    if predicted is None:
        return "prediction was None (fail-closed)"
    cells = [(y, x, predicted[y][x], real[y][x])
             for y in range(len(real)) for x in range(len(real[0]))
             if predicted[y][x] != real[y][x]]
    shown = "; ".join(
        f"(row={y},col={x}) predicted {p} real {r}" for y, x, p, r in cells[:limit]
    )
    more = f" ...+{len(cells) - limit} more" if len(cells) > limit else ""
    return f"{len(cells)} cells wrong: {shown}{more}"


def _wrong_cell_count(predicted, real) -> int:
    if predicted is None:
        return sum(len(row) for row in real)
    try:
        if len(predicted) != len(real):
            return sum(len(row) for row in real)
        total = 0
        for prow, rrow in zip(predicted, real):
            if len(prow) != len(rrow):
                return sum(len(row) for row in real)
            total += sum(1 for p, r in zip(prow, rrow) if p != r)
        return total
    except Exception:  # noqa: BLE001 — diagnostics must never crash the gate
        return sum(len(row) for row in real)


def _bbox(cells: list[tuple[int, int]]) -> list[int] | None:
    if not cells:
        return None
    ys = [y for y, _x in cells]
    xs = [x for _y, x in cells]
    return [min(ys), min(xs), max(ys), max(xs)]


def _translation_hint(src: list[tuple[int, int]], dst: list[tuple[int, int]]) -> list[int] | None:
    if not src or len(src) != len(dst):
        return None
    src_sorted = sorted(src)
    dst_sorted = sorted(dst)
    dy = dst_sorted[0][0] - src_sorted[0][0]
    dx = dst_sorted[0][1] - src_sorted[0][1]
    shifted = sorted((y + dy, x + dx) for y, x in src_sorted)
    if shifted == dst_sorted:
        return [dy, dx]
    return None


def _mismatch_signature(predicted, real) -> dict | None:
    """Compact first-counterexample shape without softening the gate.

    The exact gate already says which cells are wrong. This signature compresses
    the same counterexample into substrate-neutral structure: color-pair
    histogram, mismatch bounding box, and whether predicted-only cells translate
    to real-only cells for each color. It is a teacher signal, never an arbiter.
    """
    if predicted is None:
        return {"kind": "prediction_none"}
    try:
        cells = [
            (y, x, predicted[y][x], real[y][x])
            for y in range(len(real)) for x in range(len(real[0]))
            if predicted[y][x] != real[y][x]
        ]
    except Exception:  # noqa: BLE001
        return None
    if not cells:
        return None
    pair_counts: Counter = Counter((p, r) for _y, _x, p, r in cells)
    colors = sorted({p for _y, _x, p, _r in cells} | {r for _y, _x, _p, r in cells})
    hints = []
    for color in colors:
        predicted_only = [(y, x) for y, x, p, r in cells if p == color and r != color]
        actual_only = [(y, x) for y, x, p, r in cells if r == color and p != color]
        delta = _translation_hint(predicted_only, actual_only)
        if delta is None:
            continue
        hints.append({
            "color": color,
            "count": len(predicted_only),
            "actual_minus_predicted": delta,
            "predicted_bbox": _bbox(predicted_only),
            "actual_bbox": _bbox(actual_only),
        })
    return {
        "mismatch_cells": len(cells),
        "bbox": _bbox([(y, x) for y, x, _p, _r in cells]),
        "pair_counts": [
            {"predicted": p, "real": r, "count": n}
            for (p, r), n in sorted(pair_counts.items())
        ],
        "color_displacement_hints": hints[:8],
    }


def _divergent_cells(predicted, real, limit: int = 8) -> list[dict]:
    if predicted is None:
        return [{
            "row": None,
            "col": None,
            "predicted": None,
            "actual": real[0][0] if real and real[0] else None,
        }]
    cells: list[dict] = []
    try:
        for y in range(len(real)):
            for x in range(len(real[0])):
                if predicted[y][x] == real[y][x]:
                    continue
                cells.append({
                    "row": y,
                    "col": x,
                    "predicted": predicted[y][x],
                    "actual": real[y][x],
                })
                if len(cells) >= limit:
                    return cells
    except Exception:  # noqa: BLE001
        return []
    return cells


def _propagated_rollout(program: Program, holdout: EpisodeLog):
    """Yield one segment-aware propagated prediction, stopping at divergence."""
    predict = as_predictor(program)
    current = None
    prev_t = None
    for i, tr in enumerate(holdout):
        if prev_t is not None and tr.t <= prev_t:
            current = None
        prev_t = tr.t
        state = tr.s if current is None else current
        predicted = predict(state, tr.a, tr.t)
        yield i, tr, predicted
        if predicted is None or predicted != tr.s_next:
            return
        current = predicted


def _holdout_witness(program: Program, holdout: EpisodeLog) -> dict | None:
    """First failing row under the gate's segment-aware rollout."""
    for i, tr, predicted in _propagated_rollout(program, holdout):
        if predicted is None or predicted != tr.s_next:
            return {
                "step_index": i,
                "t": tr.t,
                "action": tr.a,
                "entry_context_note": (
                    "fail-closed (prediction None)" if predicted is None else
                    f"first rollout divergence at holdout row {i} (t={tr.t})"),
                "divergent_cells": _divergent_cells(predicted, tr.s_next),
            }
    return None


def _signature_key(signature: dict | None) -> str:
    return json_dumps_stable(signature or {"kind": "unknown"})


def json_dumps_stable(payload) -> str:
    import json
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


ENV_FRAME_CAP = 0.05     # >5% env frames = systematic mismatch, refuse to excuse
_ENV_FRAME_CACHE: "dict[str, frozenset[int]]" = {}
# Tracks how many candidate frames were suppressed when the cap tripped (keyed
# by the same cache key). Consumed by replay_consistency_gate to surface the
# cap trip in the gate detail — docstring says exclusions are never silent.
_ENV_FRAME_CAP_TRIPS: "dict[str, int]" = {}


def _color_counts(grid) -> Counter:
    c: Counter = Counter()
    for row in grid:
        c.update(row)
    return c


def env_frame_indices(log: EpisodeLog) -> "set[int]":
    """Transitions OUTSIDE the game's dynamics — not physics, so no law can or
    should explain them (kernel fix, 2026-07-03: the complete law scored
    120/122 and failed the gate on these). Adapter-authored transition identity
    is authoritative.  Legacy rows without identity use the structural fallback
    below; grid-difference magnitude never decides the row category.

    A positively evidenced authoritative ``dynamics`` row is protected from
    legacy inference even when it resembles a reset.  A bare dynamics label is
    not positive evidence: older collectors emitted it merely because their
    public API exposed no boundary signal, while omitting automatic respawns.
    An authoritative boundary row is excluded even when no observation
    heuristic recognizes it.  Candidate-authored/untrusted labels receive no
    authority.

    Legacy fallback:

      (a) environment no-ops: s == s_next (the env swallowed the step; a real
          blocked move differs — it must be PREDICTED as unchanged by a guard,
          and those frames replay fine under identity prediction, so only
          model-expected-change no-ops ever reach the mismatch path);
      (b) within-transition resets: an EPISODE-BOUNDARY discontinuity captured
          inside the step (level restart). The horizon resource — the color
          whose bar DECREMENTS across most transitions (a genuine timer ticks
          down nearly every step) — only ever GROWS on a reset. A transition
          that (i) sits at an episode boundary (its successor row's t fails to
          advance, or it is the final row) AND (ii) strictly grows that resource
          is a refill: an episode boundary, not a transition law. The resource
          color and the boundaries are read from the log — no game constants.

    A recording gap (a new play cycle reset the env BETWEEN two rows) also shows
    a non-advancing t, but its own transition is normal physics: the resource
    decrements there, so the refill test correctly keeps it (this is why t alone
    over-excludes and the refill is the real discriminator).

    CAPPED: if more than ENV_FRAME_CAP of the log qualifies, return empty —
    a log drowning in "env frames" is a broken harness, not excusable noise.
    Excluded frames are always REPORTED in gate detail, never silent."""
    rows = list(log)
    if not rows:
        return set()
    # Exact content identity. EpisodeLog memoizes this digest and invalidates it
    # on append, avoiding both GC-id aliasing and sampled-cell collisions.
    key = log.content_hash()
    cached = _ENV_FRAME_CACHE.get(key)
    if cached is not None:
        return set(cached)
    explicit_boundary = {
        i for i, tr in enumerate(rows) if authoritative_boundary(tr.identity)
    }
    protected_dynamics = {
        i for i, tr in enumerate(rows) if authoritative_dynamics(tr.identity)
    }
    inferred: set[int] = set()
    # (a) environment no-ops — ONLY when the row also carries a t-anomaly
    # (non-advancing t). A 0-diff frame with normal t advance is a BLOCKED
    # MOVE: real physics the law must PREDICT via a refusal guard (when_dest),
    # never excuse (2026-07-03 night: blanket excusal let live play diverge
    # at depth 1 forever while abduction felt no pressure to learn refusal).
    for i, tr in enumerate(rows):
        if i in protected_dynamics or i in explicit_boundary:
            continue
        if tr.s == tr.s_next:
            t_anomalous = (i + 1 < len(rows) and rows[i + 1].t <= tr.t)
            if t_anomalous:
                inferred.add(i)
    # Compute the observation projection once. Recomputing Counters in each
    # inference branch multiplies full-bank verifier cost without adding
    # evidence.
    state_counts = [_color_counts(tr.s) for tr in rows]
    next_counts = [_color_counts(tr.s_next) for tr in rows]

    # identify the depleting horizon resource and where it grows
    down: Counter = Counter()
    grew: "dict[int, set[int]]" = {}
    for i, (cs, cn) in enumerate(zip(state_counts, next_counts)):
        for c in cs.keys() | cn.keys():
            delta = cn[c] - cs[c]
            if delta < 0:
                down[c] += 1
            elif delta > 0:
                grew.setdefault(c, set()).add(i)
    resource = None
    if down:
        cand, n_down = down.most_common(1)[0]
        if n_down > len(rows) / 2:        # a continuous bar, not an occasional marker
            resource = cand
    # (b) within-transition resets: a refill of the horizon resource. At an
    # episode boundary ANY strict growth qualifies; away from a boundary only a
    # RESET-SCALE refill (>= half the bar's max observed size) does — merged
    # probe logs carry advancing t across real resets (2026-07-03 miss), while
    # a lawful small pickup mechanic must stay physics.
    if resource is not None:
        res_max = max(counts.get(resource, 0) for counts in state_counts)
        for i, tr in enumerate(rows):
            if i in protected_dynamics or i in explicit_boundary:
                continue
            if i not in grew.get(resource, ()):
                continue
            at_boundary = (i + 1 == len(rows)) or (rows[i + 1].t <= tr.t)
            delta = next_counts[i].get(resource, 0) - state_counts[i].get(resource, 0)
            if at_boundary or delta >= max(1, res_max // 2):
                inferred.add(i)
    # (c) a SECONDARY per-episode counter: a colour that strictly depletes within
    # transitions (down>0) but NEVER regrows in one — it refills only across
    # recording gaps, so no transition shows it grow — and is not the primary
    # resource. When such a bar ticks DOWN at an episode boundary it is a level-end
    # decrement, not physics: the same class as (b) for the primary resource, one
    # observation of which the gate would otherwise demand a memorized rule for
    # (ls20: a secondary lives-bar consumed only at boundaries; 15/16 ticks already
    # fall on (b)-excluded refills, the 16th on a recording-gap boundary). Evidence-
    # derived, no game constants; NARROW — a non-boundary tick stays physics, so a
    # genuine mid-episode consume is still learnable from those frames.
    secondary = {c for c, n in down.items() if n > 0 and c not in grew and c != resource}
    if secondary:
        for i, tr in enumerate(rows):
            if i in protected_dynamics or i in explicit_boundary:
                continue
            # ONLY a STRICT t-reset boundary (t jumps DOWN to a new episode), not a
            # non-advancing gap or a constant-t log — else every frame of a single
            # t=0 episode would qualify and a real mid-episode consume be excused.
            if i + 1 >= len(rows) or rows[i + 1].t >= tr.t:
                continue
            cs, cn = state_counts[i], next_counts[i]
            if any(cn.get(c, 0) < cs.get(c, 0) for c in secondary):
                inferred.add(i)
    if len(inferred) > max(1, int(len(rows) * ENV_FRAME_CAP)) + 1:
        # Cap tripped: too many "env frames" → broken harness, not excusable
        # noise. Record how many were suppressed so replay_consistency_gate can
        # surface it in the detail string (docstring: exclusions are NEVER
        # silent — F3a fix, 2026-07-09).
        _ENV_FRAME_CAP_TRIPS[key] = len(inferred)
        inferred = set()
    else:
        _ENV_FRAME_CAP_TRIPS.pop(key, None)
    if len(_ENV_FRAME_CACHE) > 64:
        _ENV_FRAME_CACHE.clear()
        _ENV_FRAME_CAP_TRIPS.clear()
    idx = explicit_boundary | inferred
    _ENV_FRAME_CACHE[key] = frozenset(idx)
    return idx


def _env_frame_note(log: EpisodeLog, env: "set[int]") -> str:
    """Render exclusion authority instead of laundering every row as reset.

    Adapter-attested boundaries and contextual boundary inferences have
    different epistemic identities even though neither is scored as a
    within-epoch law row.
    """
    if not env:
        return ""
    rows = list(log)
    explicit = sum(
        1
        for index in env
        if 0 <= index < len(rows) and authoritative_boundary(rows[index].identity)
    )
    inferred = len(env) - explicit
    return (
        f" ({len(env)} environment frames excluded: "
        f"adapter_attested={explicit}, evidence_inferred={inferred})"
    )


def replay_consistency_gate(program: Program, log: EpisodeLog) -> GateResult:
    predict = as_predictor(program)
    env = env_frame_indices(log)
    # Check whether the cap tripped for this log (F3a: cap trips are never
    # silent — surface them in the gate detail).
    rows = list(log)
    _cap_key = log.content_hash() if rows else None
    cap_suppressed = _ENV_FRAME_CAP_TRIPS.get(_cap_key, 0) if _cap_key else 0
    for i, tr in enumerate(log):
        if i in env:
            continue
        predicted = predict(tr.s, tr.a, tr.t)
        if predicted is None:
            return GateResult(False, f"fail-closed evaluation at t={tr.t}")
        if predicted != tr.s_next:
            return GateResult(False,
                              f"replay mismatch at t={tr.t} action={tr.a}: "
                              + _counterexample_cells(predicted, tr.s_next))
    note = _env_frame_note(log, env)
    if cap_suppressed:
        note += f"; env-frame cap tripped: {cap_suppressed} candidate frames suppressed"
    return GateResult(True, f"replay consistent over {len(log) - len(env)} transitions" + note)


def replay_diagnostics(program: Program, log: EpisodeLog) -> ReplayDiagnostics:
    """Teacher-forced replay diagnostics for learning from hard-gate failures.

    This does not soften replay_consistency_gate. The gate remains binary; the
    diagnostic receipt preserves partial structure so the next mutator can build
    from the best failed candidate instead of treating all gate misses as equal.
    """
    predict = as_predictor(program)
    env = env_frame_indices(log)
    checked = exact = wrong_rows = wrong_cells = 0
    first = ""
    first_sig = None
    residual: list[dict] = []
    _RESIDUAL_CAP = 48  # ponytail: bank holds 48 post-boundary rows; cap matches
    class_counts: Counter = Counter()
    class_examples: dict[str, dict] = {}
    for i, tr in enumerate(log):
        if i in env:
            continue
        checked += 1
        predicted = predict(tr.s, tr.a, tr.t)
        if predicted is None:
            wrong_rows += 1
            wrong_cells += _wrong_cell_count(None, tr.s_next)
            sig = {"kind": "prediction_none"}
            key = _signature_key(sig)
            class_counts[key] += 1
            class_examples.setdefault(
                key, {"signature": sig, "first_row": i, "t": tr.t, "action": tr.a}
            )
            if not first:
                first = f"fail-closed evaluation at t={tr.t}"
            continue
        if predicted == tr.s_next:
            exact += 1
            continue
        wrong_rows += 1
        wrong_cells += _wrong_cell_count(predicted, tr.s_next)
        if len(residual) < _RESIDUAL_CAP:
            residual.append({
                "t": tr.t, "action": tr.a,
                "cells": _counterexample_cells(predicted, tr.s_next),
            })
        sig = _mismatch_signature(predicted, tr.s_next)
        key = _signature_key(sig)
        class_counts[key] += 1
        class_examples.setdefault(
            key, {"signature": sig or {}, "first_row": i, "t": tr.t, "action": tr.a}
        )
        if not first:
            first = (
                f"replay mismatch at t={tr.t} action={tr.a}: "
                + _counterexample_cells(predicted, tr.s_next)
            )
            first_sig = sig
    mismatch_classes = []
    for key, n in class_counts.most_common(12):
        row = dict(class_examples.get(key) or {})
        row["count"] = n
        mismatch_classes.append(row)
    return ReplayDiagnostics(
        checked_rows=checked,
        exact_rows=exact,
        wrong_rows=wrong_rows,
        wrong_cell_count=wrong_cells,
        first_mismatch=first,
        first_mismatch_signature=first_sig,
        mismatch_classes=mismatch_classes,
        residual_table=residual or None,
    )


def replay_gate_and_diagnostics(
    program: Program,
    log: EpisodeLog,
) -> tuple[GateResult, ReplayDiagnostics]:
    """Return the exact replay verdict and witness from one carrier scan.

    The diagnostics are a sufficient statistic for the binary verdict:
    ``wrong_rows == 0`` exactly when every checked prediction equals its
    successor. Consumers that need both outputs should not evaluate the same
    carrier twice over one evidence identity.
    """

    diagnostics = replay_diagnostics(program, log)
    env = env_frame_indices(log)
    if diagnostics.wrong_rows:
        detail = diagnostics.first_mismatch or (
            f"replay mismatch on {diagnostics.wrong_rows} transitions"
        )
        return GateResult(False, detail), diagnostics
    note = _env_frame_note(log, env)
    cap_suppressed = _ENV_FRAME_CAP_TRIPS.get(log.content_hash(), 0) if len(log) else 0
    if cap_suppressed:
        note += f"; env-frame cap tripped: {cap_suppressed} candidate frames suppressed"
    return (
        GateResult(
            True,
            f"replay consistent over {diagnostics.checked_rows} transitions" + note,
        ),
        diagnostics,
    )


def rollout_depth(program: Program, holdout: EpisodeLog) -> int:
    """Consecutive correctly-predicted steps on a held-out episode, from its
    start, propagating the candidate's own predictions (a true rollout, not
    per-step teacher forcing)."""
    depth = 0
    for _index, tr, predicted in _propagated_rollout(program, holdout):
        if predicted is None or predicted != tr.s_next:
            break
        depth += 1
    return depth


def rollout_diagnostics(program: Program, holdout: EpisodeLog) -> dict:
    depth = rollout_depth(program, holdout)
    payload = {"rollout_depth": depth}
    if depth < len(holdout):
        witness = _holdout_witness(program, holdout)
        if witness is not None:
            payload["holdout_witness"] = witness
    return payload


def rollout_depth_gate(program: Program, holdout: EpisodeLog, min_depth: int) -> GateResult:
    d = rollout_depth(program, holdout)
    ok = d >= min_depth
    return GateResult(ok, f"rollout depth {d} (required {min_depth}) over {len(holdout)} held-out steps")


def determinism_check(log: EpisodeLog, phase_mod: int = 6) -> GateResult:
    """Detect NON-determinism in the evidence itself: the same (state, action,
    t % phase_mod) mapping to different successors. Everything downstream
    (abduction, gates, sweeps) assumes deterministic dynamics; on a stochastic
    game the stack would churn with no diagnosis. This names the boundary as a
    structural receipt instead (env frames excluded first — resets are not
    nondeterminism)."""
    env = env_frame_indices(log)
    seen: dict = {}
    for i, tr in enumerate(log):
        if i in env:
            continue
        k = (tr.s, tr.a, tr.t % phase_mod)
        if k in seen and seen[k][0] != tr.s_next:
            return GateResult(False,
                f"NON-DETERMINISTIC: rows {seen[k][1]} and {i} share (state, action, "
                f"phase) but differ in outcome — dynamics are stochastic or carry "
                f"hidden state; deterministic identification is out of scope here")
        seen.setdefault(k, (tr.s_next, i))
    return GateResult(True, f"deterministic over {len(seen)} distinct (s, a, phase) keys")
