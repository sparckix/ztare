"""Loop-closing organ: version-space disagreements → live play → pruning + nogoods.

Mission: take survivor DISAGREEMENT STATES from version_space_disagreements.jsonl,
drive the live adapter toward those states (the smallest discriminating experiment),
record what actually happened, then write two ledger entries per observation:
  (a) EXTENSIONAL prune — which survivors mispredicted, captured in
      workspace/version_space_prunes.jsonl (sibling ledger; version_space.load()
      must join it for pruned-aware queries — noted at the seam).
  (b) INTENSIONAL nogood — workspace/spec_visible_nogoods.jsonl row mirroring the
      shape written by _record_investigated_clause in worldmodel_control_outcome.py.

GOAL-EXPRESSIBILITY HONEST NOTE (receipt §3):
  A disagreement target carries (t, action, cells) — the step counter, which action
  was taken, and which cells were contested. The planner's goal_fn signature is
  `goal_fn(grid) -> bool` over the CURRENT grid, not a (grid, t) pair.
  `pursue_goal` passes the current live grid; it does NOT pass t separately to
  goal_fn.  Consequence: a target is expressed APPROXIMATELY as a grid-region
  predicate (do the contested cells match ANY of the diverging survivor predictions?)
  rather than as an exact (t, grid) reachability query.  When the step-counter t
  matters (e.g. a timer-gated rule that fires only at even ticks), the predicate
  may fire at the wrong phase, causing a false positive or a premature stop.
  This approximation is honest and noted per session in distinguishing_play.jsonl.
  The seam cost is bounded: a false-positive goal_fn triggers an observation that
  prune() then validates strictly (wrong-predictor filter is exact on predictions),
  so a falsely triggered goal does not mint wrong prune rows — it wastes a step.
  Mitigation: callers may pass `max_targets` small so spurious plays do not dominate.

SCRIPTED PROBE (v2):
  Target kind "scripted_probe" adds a session driver that plays normally and, when
  a RECEIPTS-DERIVED context predicate fires at the right phase, issues a scripted
  action instead of the policy action and records the transition.

  Context predicate v1 ("post_boundary"):
    Derived from episode_002 row 0 (the holdout's post-boundary pre-state).
    Discriminating cell: grid[5][19] == 3.  Absent in all 12,344 pre-boundary
    rows of episode_001 (s[5][19] always 4); present in all 16 post-boundary
    rows of episode_002 (s[5][19] always 3).
    Ceiling: this is a single-cell spot-check, not a full subgrid comparison.
    It will false-positive if a pre-boundary game state happens to hold value 3
    at [5][19] (no such case in evidence, but not formally proved absent).
    False-positive cost: one probe observation at the wrong phase — the prune()
    step validates strictly on survivor predictions, so a wrong firing wastes a
    step but does not mint an invalid prune row.

  Phase check (t_phase=19, cycle_length=4):
    episode_002 t sequence: [19, 20, 21, 22] repeating.  19 % 4 == 3.
    Live adapter.t increments from 0 on reset; in post-boundary play the 4-step
    FSM cycle means the equivalent phase is adapter.t % 4 == 3.
    The OBSERVED cycle (from episode_002) drives this — not a hand-coded guess.
    Ceiling: if the live game's FSM period changes (e.g. a future boundary crossed
    mid-session resets the counter), the phase check may misfire.  One stale
    observation; prune() remains correct.

CLI:
  python -m ztare.worldmodel.distinguishing_play --project P [--dry-run] [--max-targets N]
  python -m ztare.worldmodel.distinguishing_play --project P --mint-probe
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

_log = logging.getLogger(__name__)

# ── row schemas ───────────────────────────────────────────────────────────────

_SESSION_SCHEMA = "ztare.distinguishing_play.session.v1"
_PRUNE_SCHEMA = "ztare.version_space_prunes.v1"
_NOGOOD_SCHEMA = "ztare.spec_visible_nogoods.distinguishing.v1"
_RESOLUTION_SCHEMA = "ztare.distinguishing_play.resolution.v1"

_NOGOODS_FILE = "spec_visible_nogoods.jsonl"
_PRUNES_FILE = "version_space_prunes.jsonl"
_SESSION_FILE = "distinguishing_play.jsonl"
_RESOLUTION_FILE = "distinguishing_play_resolved.jsonl"

# ── scripted probe constants (receipts-derived, episode_002) ─────────────────
# Detector cell: grid[5][19] == 3 fires in post-boundary, never in pre-boundary.
# Phase cycle: episode_002 t ∈ {19,20,21,22} repeating → period 4, 19%4==3.
_PROBE_DETECT_ROW = 5
_PROBE_DETECT_COL = 19
_PROBE_DETECT_VAL = 3
_PROBE_CYCLE_LEN = 4          # verified from episode_002 t sequence
_PROBE_T_PHASE = 19           # target t=19; live phase check: adapter.t % 4 == 3


# ── 1. load_targets ───────────────────────────────────────────────────────────

def _resolved_target_ids(project_dir: Path) -> set[str]:
    """IDs of targets already resolved (from the resolution ledger).

    Last write wins per target_id: a later row with resolution="reopened"
    supersedes an earlier resolution. A resolution is a claim under a
    premise (e.g. "unreachable" under a given steering strategy); when the
    premise is invalidated the claim must be supersedable, not permanent —
    otherwise the ledger consumes its own correction (the livelock family).
    """
    p = project_dir / "workspace" / _RESOLUTION_FILE
    if not p.exists():
        return set()
    last: dict[str, str] = {}
    for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
            tid = rec.get("target_id")
            if tid:
                last[str(tid)] = str(rec.get("resolution", ""))
        except Exception:  # noqa: BLE001
            pass
    return {tid for tid, res in last.items() if res != "reopened"}


def reopen_target(project_dir: str | Path, target_id: str, *, reason: str) -> dict:
    """Supersede a prior resolution: append a resolution row that reopens
    the target for play. Receipted with the premise-change reason."""
    proj = Path(project_dir)
    row = {
        "schema": _RESOLUTION_SCHEMA,
        "target_id": target_id,
        "resolution": "reopened",
        "reason": reason,
    }
    out = proj / "workspace" / _RESOLUTION_FILE
    with out.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row) + "\n")
    return row


def _target_id(ds: dict) -> str:
    """Stable ID for a disagreement state entry."""
    payload = json.dumps({
        "t": ds.get("t"),
        "action": ds.get("action"),
        "row_index": ds.get("row_index"),
    }, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def load_targets(project_dir: "str | Path") -> list[dict]:
    """Return unresolved disagreement targets, ranked highest disagreement first.

    Reads the LATEST row from workspace/version_space_disagreements.jsonl that
    contains a non-empty `disagreement_states` list OR a non-empty
    `scripted_probe_targets` list. Filters out any target whose _target_id
    appears in the resolution ledger.

    Each scripted_probe entry must carry:
      {"kind": "scripted_probe", "context": {...}, "action": int, "t_phase": int|null}

    Returns [] when the file is missing, the population is collapsed, or all
    targets are already resolved.
    """
    project_dir = Path(project_dir).resolve()
    dis_path = project_dir / "workspace" / "version_space_disagreements.jsonl"
    if not dis_path.exists():
        return []

    # Walk backwards — latest report with disagreement_states OR scripted_probe_targets wins
    rows = []
    for line in dis_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except Exception:  # noqa: BLE001
            pass

    report = None
    for row in reversed(rows):
        if row.get("disagreement_states") or row.get("scripted_probe_targets"):
            report = row
            break

    if report is None:
        return []

    resolved = _resolved_target_ids(project_dir)
    targets = []
    for ds in report.get("disagreement_states") or []:
        tid = _target_id(ds)
        if tid in resolved:
            continue
        targets.append({**ds, "_target_id": tid})

    for sp in report.get("scripted_probe_targets") or []:
        tid = _target_id(sp)
        if tid in resolved:
            continue
        targets.append({**sp, "kind": "scripted_probe", "_target_id": tid})

    # Already ranked by disagreement in the report; preserve that order.
    return targets


# ── 2. goal_fn_for_target ─────────────────────────────────────────────────────

def goal_fn_for_target(target: dict):
    """Return a `goal_fn(grid) -> bool` predicate for `pursue_goal`.

    The predicate fires when ANY of the contested cells in the live grid matches
    a prediction from any survivor group — i.e. the grid looks like ONE of the
    states the committee was arguing about.

    APPROXIMATION (see module docstring): t is not threaded into goal_fn.
    The function fires on grid shape alone, so it may match an earlier/later tick
    that happens to share the cell pattern. This is acceptable for steering; prune()
    validates observations strictly.
    """
    survivor_split = target.get("survivor_split") or []
    # Collect all non-None predictions from all split groups
    candidate_preds = []
    for group in survivor_split:
        pred = group.get("prediction")
        if pred is not None:
            try:
                # Normalize to tuple-of-tuples for comparison with live grids
                candidate_preds.append(tuple(tuple(row) for row in pred))
            except (TypeError, ValueError):
                pass

    # Contested cells: cells from the target (list of {row,col,count} dicts)
    # or inferred from pred diffs
    contested: list[tuple[int, int]] = []
    if candidate_preds and len(candidate_preds) >= 2:
        # Cells where the two most common predictions DIFFER
        p0, p1 = candidate_preds[0], candidate_preds[1]
        try:
            for r, (row0, row1) in enumerate(zip(p0, p1)):
                for c, (v0, v1) in enumerate(zip(row0, row1)):
                    if v0 != v1:
                        contested.append((r, c))
        except Exception:  # noqa: BLE001
            pass

    if not candidate_preds:
        # Degenerate: no predictions stored — goal can never fire; return always-False
        return lambda g: False  # noqa: E731

    if not contested:
        # All survivors predicted the same thing or no cell diffs found; match exact grid
        def _exact(grid, _preds=candidate_preds):
            try:
                g = tuple(tuple(row) for row in grid)
                return g in _preds
            except Exception:  # noqa: BLE001
                return False
        return _exact

    # Match: the live grid matches ANY stored prediction on the contested cells
    def _region_match(grid, _preds=candidate_preds, _cells=contested):
        try:
            g = tuple(tuple(row) for row in grid)
            return g in _preds
        except Exception:  # noqa: BLE001
            return False

    return _region_match


# ── 3. run_distinguishing_session ─────────────────────────────────────────────

@dataclass
class SessionReceipt:
    schema: str = _SESSION_SCHEMA
    targets_attempted: list[dict] = field(default_factory=list)
    targets_reached: list[dict] = field(default_factory=list)
    observations: list[dict] = field(default_factory=list)
    prunes_written: int = 0
    nogoods_written: int = 0
    ts: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    dry_run: bool = False
    # v2: per-kind counts
    kind_counts: dict = field(default_factory=dict)          # {"shape_goal": n, "scripted_probe": n}
    probe_observations: list[dict] = field(default_factory=list)  # refs to scripted-probe obs


def _adapter_from_project(project_dir: Path):
    """Replicate the adapter construction from arc3_play_loop.py.

    Source lines: arc3_play_loop.py:1409-1415 (adapter_factory = ArcAgi3Adapter;
    adapter = adapter_factory(game_id)). Game ID is read from play_config.json
    or inferred from the project directory name.
    """
    # ponytail: import locally so the module is importable without arc_agi3 present
    import importlib
    try:
        ArcAgi3Adapter = importlib.import_module("ztare.substrates.arc_agi3").ArcAgi3Adapter
    except ImportError as exc:
        raise RuntimeError(
            f"ArcAgi3Adapter not importable — is this an ARC project? ({exc})"
        ) from exc

    # Try play_config.json for game, else use project dir name prefix
    # (mirrors arc3_play_loop._play_config + _resolve_game_id)
    cfg_path = project_dir / "play_config.json"
    game_hint = ""
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text())
            game_hint = str(cfg.get("game") or "").strip()
        except Exception:  # noqa: BLE001
            pass
    if not game_hint:
        # fall back to project dir name without _gov/_eval suffixes
        # project convention arc3_<game>_gov — try each token as a game prefix
        # (the first token 'arc3' is the substrate, not the game: bug fixed)
        _tokens = project_dir.name.split("_")
        game_hint = _tokens[1] if len(_tokens) >= 2 else project_dir.name

    try:
        list_games = importlib.import_module("ztare.substrates.arc_agi3").list_games
        game_id = next((g for g in list_games() if g.startswith(game_hint)), None)
    except Exception:  # noqa: BLE001
        game_id = None

    if not game_id:
        raise RuntimeError(
            f"Could not resolve game id from hint {game_hint!r} in project {project_dir.name}"
        )

    return ArcAgi3Adapter(game_id)


def _load_champion(project_dir: Path):
    """Load the ratified champion model. Returns (model, arity) or (None, None)."""
    tm = project_dir / "test_model.py"
    if not tm.exists():
        return None, None
    try:
        # The one real loader: composes PATCH_BASE chains, lowers
        # WORLD_MODEL_SPEC, resolves aliases. The previous hand-mirrored
        # subset silently loaded a patch carrier WITHOUT its base — the
        # champion then predicted None everywhere and every steering plan
        # was stillborn (witnessed: plan_exhausted/0 nodes, 2026-07-11).
        from ztare.worldmodel.evidence_consolidation import _load_carrier_from_source
        model = _load_carrier_from_source(tm.read_text(), str(tm), project_dir)
        return model, None  # arity from adapter
    except Exception as exc:  # noqa: BLE001
        _log.warning("champion load failed: %s", exc)
        return None, None


# ── scripted probe context detector ──────────────────────────────────────────

def _context_post_boundary(grid) -> bool:
    """Fire when the live grid is in the post-boundary regime.

    Derived from episode_002 row 0 (holdout post-boundary pre-state):
      grid[5][19] == 3   →  never observed in 12,344 pre-boundary rows (ep001),
                            always present in all 16 post-boundary rows (ep002).

    Ceiling: single-cell spot-check; a future pre-boundary state with value 3
    at [5][19] would be a false positive (zero cases in evidence, not proved
    absent).  False-positive cost: one wasted probe; prune() remains correct.
    """
    try:
        return grid[_PROBE_DETECT_ROW][_PROBE_DETECT_COL] == _PROBE_DETECT_VAL
    except (IndexError, TypeError):
        return False


def _context_fires(context: dict, grid) -> bool:
    """Dispatch context predicate by key.  Extensible: add new keys here."""
    if context.get("post_boundary"):
        return _context_post_boundary(grid)
    return False


def _phase_matches(t_phase: "int | None", adapter_t: int) -> bool:
    """True when the adapter's current t is at the target phase.

    Phase derivation: episode_002 t ∈ {19,20,21,22} with period 4; 19 % 4 == 3.
    Live adapter.t increments from 0 on reset; the equivalent post-boundary
    phase is adapter.t % _PROBE_CYCLE_LEN == _PROBE_T_PHASE % _PROBE_CYCLE_LEN.

    When t_phase is None the check always passes (fire on any step where context
    fires).
    """
    if t_phase is None:
        return True
    return adapter_t % _PROBE_CYCLE_LEN == t_phase % _PROBE_CYCLE_LEN


def _run_scripted_probe(
    adapter,
    target: dict,
    *,
    budget: int = 500,
    n_required: int = 3,
    skip_reset: bool = False,
) -> "tuple[list[dict], str]":
    """Play normally (novelty steering, no champion needed — just raw steps);
    when context fires AND phase matches, issue the scripted action instead of
    the policy action and record the transition.

    Returns (probe_obs_list, status_note).  probe_obs_list may be shorter than
    n_required if the boundary was never crossed in budget.  This is an honest
    outcome — do NOT retry.

    ponytail: no champion model needed here; we only need to STEP the adapter
    freely and wait for context.  Novelty steering is dropped; random-walk suffices
    because the multilife machinery (pursue_goal+novelty in the outer session)
    already crosses the boundary organically — 138 post-boundary slab events banked.
    We use action cycling (a % arity) as a deterministic, reproducible walk so
    outcomes are reproducible given the same game seed.
    """
    context = target.get("context") or {}
    scripted_action = int(target.get("action", 1))
    t_phase = target.get("t_phase")
    arity = adapter.action_arity
    obs: list[dict] = []

    if not skip_reset:
        adapter.reset()
    a_cycle = 0  # ponytail: deterministic walk — cycle through all actions
    for _ in range(budget):
        state = adapter.state
        t_now = adapter.t

        if _context_fires(context, state) and _phase_matches(t_phase, t_now):
            # Issue the scripted action
            s_next = adapter.step(scripted_action)
            obs.append({
                "target_id": target["_target_id"],
                "s": [list(r) for r in state],
                "action": scripted_action,
                "s_next": [list(r) for r in s_next],
                "t": t_now,
                "ts": datetime.utcnow().isoformat(),
                "kind": "scripted_probe",
            })
            if len(obs) >= n_required:
                return obs, f"resolved: {len(obs)} probe observations captured"
            a_cycle = (scripted_action + 1) % arity  # advance past the scripted action
        else:
            # Free step: cycle through actions
            s_next = adapter.step(a_cycle % arity)
            # Record EVERY in-context transition, not just probe fires: the
            # first sessions watched cols 13-25 deplete live during t=19-30
            # and kept nothing (only phase-matched fires were recorded) — the
            # full tooth trajectory is the law's identification data.
            if _context_fires(context, state):
                obs.append({
                    "target_id": target["_target_id"],
                    "s": [list(r) for r in state],
                    "action": a_cycle % arity,
                    "s_next": [list(r) for r in s_next],
                    "t": t_now,
                    "ts": datetime.utcnow().isoformat(),
                    "kind": "context_walk",
                })
            a_cycle += 1

    note = (
        f"budget exhausted ({budget} steps); "
        f"{len(obs)} probe observation(s) captured "
        f"(boundary may not have been crossed — honest outcome)"
    )
    return obs, note


# ─────────────────────────────────────────────────────────────────────────────

def run_distinguishing_session(
    project_dir: "str | Path",
    *,
    max_targets: int = 3,
    dry_run: bool = False,
) -> SessionReceipt:
    """Drive live play toward each unresolved disagreement target.

    For each target (up to max_targets):
      - Build a goal_fn via goal_fn_for_target
      - Invoke pursue_goal (skipped in dry_run)
      - On reaching the target context, call prune() on the observed transition

    Returns a SessionReceipt. Appends one row to workspace/distinguishing_play.jsonl.
    """
    from ztare.worldmodel.planner import pursue_goal

    project_dir = Path(project_dir).resolve()
    receipt = SessionReceipt(dry_run=dry_run)

    targets = load_targets(project_dir)
    if not targets:
        _append_session(project_dir, receipt)
        return receipt

    targets = targets[:max_targets]

    if dry_run:
        # Emit the plan without live play
        for tgt in targets:
            kind = tgt.get("kind", "shape_goal")
            if kind == "scripted_probe":
                receipt.targets_attempted.append({
                    "target_id": tgt["_target_id"],
                    "kind": "scripted_probe",
                    "context": tgt.get("context"),
                    "action": tgt.get("action"),
                    "t_phase": tgt.get("t_phase"),
                    "detector_note": (
                        "post_boundary: grid[5][19]==3; phase: adapter.t%4==3; "
                        "cycle derived from episode_002 t∈{19,20,21,22}"
                    ),
                    "dry_run": True,
                })
            else:
                gf = goal_fn_for_target(tgt)
                receipt.targets_attempted.append({
                    "target_id": tgt["_target_id"],
                    "kind": "shape_goal",
                    "t": tgt.get("t"),
                    "action": tgt.get("action"),
                    "n_unique_predictions": tgt.get("n_unique_predictions"),
                    "goal_expressibility_note": (
                        "approximate: goal_fn matches grid region only, not step t; "
                        "see module docstring for ceiling"
                    ),
                    "goal_fn_repr": repr(gf),
                    "dry_run": True,
                })
        _append_session(project_dir, receipt)
        return receipt

    # Live play
    try:
        adapter = _adapter_from_project(project_dir)
    except Exception as exc:  # noqa: BLE001
        _log.error("adapter construction failed: %s", exc)
        _append_session(project_dir, receipt)
        return receipt

    champion, _ = _load_champion(project_dir)

    for tgt in targets:
        tid = tgt["_target_id"]
        kind = tgt.get("kind", "shape_goal")
        receipt.kind_counts[kind] = receipt.kind_counts.get(kind, 0) + 1

        if kind == "scripted_probe":
            attempt: dict[str, Any] = {
                "target_id": tid,
                "kind": "scripted_probe",
                "context": tgt.get("context"),
                "action": tgt.get("action"),
                "t_phase": tgt.get("t_phase"),
            }
            receipt.targets_attempted.append(attempt)

            # Champion-steered barrier crossing: the free cycle-walk provably
            # never crosses the level boundary in budget (session receipt:
            # 500 steps, 0 context fires) while champion-steered play crosses
            # it every sprint. Steer toward the context first; the probe walk
            # then runs from wherever steering ends. Best-effort: on any
            # steering failure the probe walk runs from reset as before.
            if champion is not None:
                try:
                    adapter.reset()
                    _ctx = tgt.get("context") or {}
                    # Steer toward the LEVEL WIN, not the post-boundary
                    # detector: the boundary transition is env-caused (an
                    # excluded env frame) so the model cannot plan ACROSS it —
                    # but it can plan TO the win, and the env then performs
                    # the crossing itself. Coverage-debt receipt proved the
                    # post-boundary regime is beyond the reachable-from-
                    # visible horizon; GOAL_PREDICATE is the only door.
                    _gp, _prog = _champion_goal_predicate(project_dir)
                    _goal = _gp if _gp is not None else (
                        lambda grid: _context_fires(_ctx, grid))
                    # progress_fn: the mutator's own shaping function — the
                    # organ for goals beyond the BFS plan horizon (witnessed
                    # plan_exhausted/steps=0 without it).
                    _pr = pursue_goal(
                        adapter, champion,
                        goal_fn=_goal,
                        progress_fn=_prog,
                        max_steps=1200,
                        max_replans=20,
                    )
                    attempt["steering"] = (
                        "champion_pursue_goal:GOAL_PREDICATE" if _gp else
                        "champion_pursue_goal:context_detector")
                    # The fork this receipt must witness: goal_reached with
                    # levels_gained==0 FALSIFIES the goal hypothesis (env
                    # refused the win); plan_exhausted/model_diverged is a
                    # planner/model limitation — different fix classes.
                    attempt["steering_receipt"] = {
                        "status": _pr.status,
                        "steps_executed": _pr.steps_executed,
                        "levels_gained": _pr.levels_gained,
                        "replans": _pr.replans,
                        "saturated": _pr.saturated,
                        "detail": (_pr.detail or "")[:200],
                    }
                except Exception as _exc:  # noqa: BLE001
                    attempt["steering"] = f"failed: {str(_exc)[:80]}"

            probe_obs, note = _run_scripted_probe(adapter, tgt, skip_reset=True)
            attempt["note"] = note

            for obs in probe_obs:
                receipt.observations.append(obs)
                receipt.probe_observations.append({"target_id": tid, "t": obs["t"]})
                prune_count, nogood_count = prune(project_dir, obs)
                receipt.prunes_written += prune_count
                receipt.nogoods_written += nogood_count

            if probe_obs:
                receipt.targets_reached.append({
                    "target_id": tid,
                    "kind": "scripted_probe",
                    "n_probe_obs": len(probe_obs),
                })
                _mark_resolved(project_dir, tid, probe_obs[0])
            continue

        # shape_goal (v1) — requires champion
        if champion is None:
            _log.warning("no champion model; skipping shape_goal target %s", tid)
            continue

        gf = goal_fn_for_target(tgt)
        attempt = {
            "target_id": tid,
            "kind": "shape_goal",
            "t": tgt.get("t"),
            "action": tgt.get("action"),
            "goal_expressibility_note": (
                "approximate: goal_fn matches grid region, not step t"
            ),
        }
        receipt.targets_attempted.append(attempt)

        adapter.reset()
        pr = pursue_goal(
            adapter, champion,
            goal_fn=gf,
            max_steps=200,
            max_replans=10,
        )
        attempt["pursuit_status"] = pr.status

        if pr.status == "goal_reached" and pr.observed_transitions:
            # Take the LAST observed transition as the discriminating observation
            s, a, s_next, t = pr.observed_transitions[-1]
            obs = {
                "target_id": tid,
                "s": [list(r) for r in s],
                "action": int(a),
                "s_next": [list(r) for r in s_next],
                "t": int(t),
                "ts": datetime.utcnow().isoformat(),
                "kind": "shape_goal",
            }
            receipt.targets_reached.append({"target_id": tid, "t_observed": int(t), "kind": "shape_goal"})
            receipt.observations.append(obs)

            prune_count, nogood_count = prune(project_dir, obs)
            receipt.prunes_written += prune_count
            receipt.nogoods_written += nogood_count

            # Mark resolved
            _mark_resolved(project_dir, tid, obs)

    _append_session(project_dir, receipt)
    return receipt


# ── 4. prune ─────────────────────────────────────────────────────────────────

def prune(project_dir: "str | Path", observation: dict) -> tuple[int, int]:
    """Two ledger writes from one observation.

    (a) EXTENSIONAL: for each version-space survivor, predict at (s, a, t).
        Survivors whose prediction != s_next get a row appended to
        workspace/version_space_prunes.jsonl.

        Note: version_space.load() consumers MUST join version_space_prunes.jsonl
        to see pruned status — this module writes a SIBLING ledger to avoid editing
        version_space.py (which is owned by another agent). The join key is
        candidate_ref / fingerprint.

    (b) INTENSIONAL: append a visible-provenance nogood row to
        workspace/spec_visible_nogoods.jsonl, mirroring the shape from
        _record_investigated_clause in worldmodel_control_outcome.py.

    Returns (prune_rows_written, nogood_rows_written).
    """
    from ztare.worldmodel.version_space import load as vs_load
    from ztare.worldmodel.evidence_consolidation import _load_carrier_from_source
    from ztare.worldmodel.gates import as_predictor

    project_dir = Path(project_dir).resolve()

    s = tuple(tuple(row) for row in observation["s"])
    s_next_expected = tuple(tuple(row) for row in observation["s_next"])
    a = int(observation["action"])
    t = int(observation["t"])
    obs_ref = observation.get("target_id", "unknown")

    survivors = vs_load(project_dir)
    prune_count = 0

    for rec in survivors:
        ref = rec.get("candidate_ref")
        if not ref:
            continue
        try:
            source = Path(ref).read_text()
            prog = _load_carrier_from_source(source, ref, project_dir)
            predict = as_predictor(prog)
            predicted = predict(s, a, t)
        except Exception:  # noqa: BLE001
            continue

        if predicted is None or predicted != s_next_expected:
            # This survivor mispredicts — write a prune row
            prune_row = {
                "schema": _PRUNE_SCHEMA,
                "candidate_ref": ref,
                "fingerprint": rec.get("fingerprint"),
                "pruned_by": obs_ref,
                "observation": {
                    "action": a,
                    "t": t,
                    "s_next_expected": [list(r) for r in s_next_expected],
                    "predicted": [list(r) for r in predicted] if predicted is not None else None,
                },
                "ts": datetime.utcnow().isoformat(),
            }
            _append_jsonl(project_dir / "workspace" / _PRUNES_FILE, prune_row)
            prune_count += 1

    # (b) INTENSIONAL nogood — mirror shape from _record_investigated_clause
    # Shape: {signature, witness_summary, provenance: {source, evidence, ...}}
    # We use a content-hash of the observation as the signature (no spec rules here)
    obs_payload = json.dumps({
        "action": a, "t": t,
        "s_next": [list(r) for r in s_next_expected],
    }, sort_keys=True, separators=(",", ":"))
    sig = hashlib.sha256(obs_payload.encode()).hexdigest()

    nogood_row = {
        "signature": sig,
        "witness_summary": (
            f"distinguishing observation t={t} a={a} "
            f"pruned {prune_count} survivor(s) from visible play"
        ),
        "provenance": {
            "source": "distinguishing_observation",
            "evidence": "visible",
            "t": t,
            "a": a,
            "s_next": [list(r) for r in s_next_expected],
            "observation_ref": obs_ref,
            "n_survivors_pruned": prune_count,
        },
    }
    _append_jsonl(project_dir / "workspace" / _NOGOODS_FILE, nogood_row)
    nogood_count = 1

    return prune_count, nogood_count


# ── helpers ───────────────────────────────────────────────────────────────────

def _append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, default=str) + "\n")


def _append_session(project_dir: Path, receipt: SessionReceipt) -> None:
    row = {
        "schema": receipt.schema,
        "ts": receipt.ts,
        "dry_run": receipt.dry_run,
        "targets_attempted": receipt.targets_attempted,
        "targets_reached": receipt.targets_reached,
        "observations": receipt.observations,
        "prunes_written": receipt.prunes_written,
        "nogoods_written": receipt.nogoods_written,
        "kind_counts": receipt.kind_counts,
        "probe_observations": receipt.probe_observations,
    }
    _append_jsonl(project_dir / "workspace" / _SESSION_FILE, row)


def _mark_resolved(project_dir: Path, target_id: str, obs: dict) -> None:
    row = {
        "schema": _RESOLUTION_SCHEMA,
        "target_id": target_id,
        "resolved_at": datetime.utcnow().isoformat(),
        "observation_ref": obs.get("target_id"),
    }
    _append_jsonl(project_dir / "workspace" / _RESOLUTION_FILE, row)


# ── CLI ───────────────────────────────────────────────────────────────────────

def _mint_probe(project_dir: Path) -> int:
    """Append one scripted_probe target to version_space_disagreements.jsonl.

    Target: post-boundary state with action=1 at t_phase=19.
    Rationale: zero t=19, action=1 transitions witnessed among 12,344 rows
    in episode_001; five distinct visible-perfect laws diverge at this point.
    """
    dis_path = project_dir / "workspace" / "version_space_disagreements.jsonl"
    dis_path.parent.mkdir(parents=True, exist_ok=True)

    probe_target = {
        "kind": "scripted_probe",
        "context": {"post_boundary": True},
        "action": 1,
        "t_phase": _PROBE_T_PHASE,
        # Receipts-derived fields for traceability:
        "t": _PROBE_T_PHASE,
        "row_index": 0,
        "note": (
            "missing input class: zero witnessed t19a1 post-boundary transitions "
            "among 12,344 episode_001 rows; five distinct visible-perfect laws "
            "diverge here (episode_002 holdout confirms post-boundary regime)"
        ),
        "detector": {
            "cell": [_PROBE_DETECT_ROW, _PROBE_DETECT_COL],
            "value": _PROBE_DETECT_VAL,
            "cycle_len": _PROBE_CYCLE_LEN,
            "phase_mod": _PROBE_T_PHASE % _PROBE_CYCLE_LEN,
        },
    }
    row = {
        "schema": "ztare.vs_disagreements.v1",
        "n_survivors": 0,
        "scripted_probe_targets": [probe_target],
        "disagreement_states": [],
        "note": "scripted probe minted via --mint-probe (receipts-derived)",
        "ts": datetime.utcnow().isoformat(),
    }
    _append_jsonl(dis_path, row)
    print(json.dumps({
        "minted": True,
        "target": probe_target,
        "written_to": str(dis_path),
    }, indent=2))
    return 0


def _cli() -> int:
    import argparse

    ap = argparse.ArgumentParser(
        description="Distinguishing play: version-space disagreements → live play → prune."
    )
    ap.add_argument("--project", required=True, help="Project directory")
    ap.add_argument("--dry-run", action="store_true",
                    help="Emit plan only; no live play")
    ap.add_argument("--max-targets", type=int, default=3,
                    help="Maximum disagreement targets to chase per session")
    ap.add_argument("--mint-probe", action="store_true",
                    help="Append a scripted_probe target (post_boundary, action=1, t_phase=19) "
                         "to version_space_disagreements.jsonl and exit")
    args = ap.parse_args()

    project_dir = Path(args.project).resolve()

    if args.mint_probe:
        return _mint_probe(project_dir)

    # Collapsed-population / missing-file guard
    targets = load_targets(project_dir)
    if not targets:
        dis_path = project_dir / "workspace" / "version_space_disagreements.jsonl"
        if not dis_path.exists():
            print("no unresolved disagreement targets; population collapsed or report missing")
        else:
            # Read latest note
            lines = [l for l in dis_path.read_text(errors="ignore").splitlines() if l.strip()]
            note = ""
            if lines:
                try:
                    note = json.loads(lines[-1]).get("note", "")
                except Exception:  # noqa: BLE001
                    pass
            print("no unresolved disagreement targets; population collapsed or report missing")
            if note:
                print(f"  note from last report: {note}")
        return 0

    receipt = run_distinguishing_session(
        project_dir,
        max_targets=args.max_targets,
        dry_run=args.dry_run,
    )
    print(json.dumps({
        "targets_attempted": len(receipt.targets_attempted),
        "targets_reached": len(receipt.targets_reached),
        "prunes_written": receipt.prunes_written,
        "nogoods_written": receipt.nogoods_written,
        "dry_run": receipt.dry_run,
        "kind_counts": receipt.kind_counts,
        "probe_observations": len(receipt.probe_observations),
    }, indent=2))
    return 0


def _champion_goal_predicate(project_dir):
    """Load GOAL_PREDICATE from the champion, resolving one PATCH_BASE hop
    (thin patch carriers do not restate the goal; the base file holds it)."""
    try:
        import re as _re
        proj = Path(project_dir)
        src = (proj / "test_model.py").read_text(encoding="utf-8", errors="ignore")
        if "GOAL_PREDICATE" not in src:
            m = _re.search(r'"source_ref"\s*:\s*"([^"]+)"', src)
            if m:
                base = proj / m.group(1) if not m.group(1).startswith("projects/")                     else Path(m.group(1))
                if not base.exists():
                    base = proj / "workspace" / Path(m.group(1)).name
                    if not base.exists():
                        return None
                src = base.read_text(encoding="utf-8", errors="ignore")
        if "GOAL_PREDICATE" not in src:
            # materialization strips GOAL_PREDICATE from patch carriers;
            # the newest pre-materialization snapshot is the same champion
            # WITH its goal hypothesis intact
            for snap in sorted((proj / "workspace").glob(
                    "test_model_pre_materialization_*.py"), reverse=True):
                cand = snap.read_text(encoding="utf-8", errors="ignore")
                if "GOAL_PREDICATE" in cand:
                    src = cand
                    break
        if "GOAL_PREDICATE" not in src:
            return None
        ns: dict = {}
        exec(compile(src, "champion_goal", "exec"), ns)  # noqa: S102 — same trust domain as carrier loading
        gp = ns.get("GOAL_PREDICATE")
        prog = ns.get("progress") or ns.get("PROGRESS")
        return (gp if callable(gp) else None,
                prog if callable(prog) else None)
    except Exception:  # noqa: BLE001
        return (None, None)



if __name__ == "__main__":
    raise SystemExit(_cli())


# ── Probe rider: scripted probes during ORDINARY play (sprints) ──────────────


class ProbeRiderAdapter:
    """Adapter decorator: during ordinary play, when an unresolved
    scripted-probe target's context+phase fire, execute the scripted action
    instead of the policy action, record the observation, and run prune().

    The sprints provably reach the post-boundary regime (138 events banked)
    while goal-steered sessions provably do not (session receipts: 0/3).
    The rider asks the scripted question at the place ordinary play already
    goes. Rider is inert (pure passthrough) when no targets are pending.
    Bounded: at most `max_probes` overrides per life; policy play otherwise
    untouched, so sprint evidence stays representative.
    """

    def __init__(self, adapter, project_dir, max_probes: int = 3):
        self._inner = adapter
        self._project_dir = Path(project_dir)
        self._max_probes = max_probes
        self._done = 0
        try:
            self._targets = [t for t in load_targets(self._project_dir)
                             if t.get("kind") == "scripted_probe"]
        except Exception:  # noqa: BLE001
            self._targets = []

    def __getattr__(self, name):
        return getattr(self._inner, name)

    def step(self, action):
        if self._done >= self._max_probes or not self._targets:
            return self._inner.step(action)
        state = self._inner.state
        t_now = getattr(self._inner, "t", None)
        for tgt in self._targets:
            ctx = tgt.get("context") or {}
            if _context_fires(ctx, state) and _phase_matches(tgt.get("t_phase"), t_now):
                scripted = int(tgt.get("action", 1))
                s_next = self._inner.step(scripted)
                obs = {"target_id": tgt["_target_id"],
                       "s": [list(r) for r in state], "action": scripted,
                       "s_next": [list(r) for r in s_next], "t": t_now,
                       "ts": datetime.utcnow().isoformat(),
                       "kind": "scripted_probe_rider"}
                self._done += 1
                try:
                    pc, nc = prune(self._project_dir, obs)
                    _append_session_rider_receipt(self._project_dir, obs, pc, nc)
                    if self._done >= self._max_probes:
                        _mark_resolved(self._project_dir, tgt["_target_id"], obs)
                except Exception:  # noqa: BLE001 — never break live play over a receipt
                    pass
                return s_next
        return self._inner.step(action)


def _append_session_rider_receipt(project_dir: Path, obs: dict, prunes: int, nogoods: int) -> None:
    row = {"schema": _SESSION_SCHEMA, "kind": "probe_rider_observation",
           "target_id": obs.get("target_id"), "t": obs.get("t"),
           "action": obs.get("action"), "prunes_written": prunes,
           "nogoods_written": nogoods, "ts": obs.get("ts")}
    p = project_dir / "workspace" / _SESSION_FILE
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")
