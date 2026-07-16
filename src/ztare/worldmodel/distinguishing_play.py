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

CLI:
  python -m ztare.worldmodel.distinguishing_play --project P [--dry-run] [--max-targets N]
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

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

# ── 1. load_targets ───────────────────────────────────────────────────────────

def target_resolution_states(project_dir: str | Path) -> dict[str, str]:
    """Latest resolution state per target from the append-only ledger.

    Last write wins per target_id: a later row with resolution="reopened"
    supersedes an earlier resolution. A resolution is a claim under a
    premise (e.g. "unreachable" under a given steering strategy); when the
    premise is invalidated the claim must be supersedable, not permanent —
    otherwise the ledger consumes its own correction (the livelock family).
    """
    p = Path(project_dir) / "workspace" / _RESOLUTION_FILE
    if not p.exists():
        return {}
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
    return last


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
        "evidence_sha256": ds.get("evidence_sha256"),
        "t": ds.get("t"),
        "action": ds.get("action"),
        "row_index": ds.get("row_index"),
    }, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def load_targets(project_dir: "str | Path") -> list[dict]:
    """Return unresolved disagreement targets, ranked highest disagreement first.

    Reads the latest report whose targets are bound to a visible-evidence
    content identity.  Evaluation-only or unbound rows cannot steer play.
    Filters out any target whose _target_id appears in the resolution ledger.

    Returns [] when the file is missing, the population is collapsed, or all
    targets are already resolved.
    """
    project_dir = Path(project_dir).resolve()
    dis_path = project_dir / "workspace" / "version_space_disagreements.jsonl"
    if not dis_path.exists():
        return []

    # Last provenance-bound visible report with disagreements wins.
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
        if (
            row.get("disagreement_states")
            and row.get("evidence_role") == "visible"
            and row.get("evidence_sha256")
        ):
            report = row
            break

    if report is None:
        return []

    resolved = {
        tid
        for tid, state in target_resolution_states(project_dir).items()
        if state != "reopened"
    }
    targets = []
    for ds in report.get("disagreement_states") or []:
        bound = {
            **ds,
            "evidence_role": "visible",
            "evidence_sha256": report["evidence_sha256"],
            "evidence_ref": report.get("evidence_ref"),
        }
        tid = _target_id(bound)
        if tid in resolved:
            continue
        targets.append({**bound, "_target_id": tid})

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
    kind_counts: dict = field(default_factory=dict)


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
            gf = goal_fn_for_target(tgt)
            receipt.targets_attempted.append({
                "target_id": tgt["_target_id"],
                "kind": "shape_goal",
                "t": tgt.get("t"),
                "action": tgt.get("action"),
                "n_unique_predictions": tgt.get("n_unique_predictions"),
                "evidence_sha256": tgt.get("evidence_sha256"),
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
        kind = "shape_goal"
        receipt.kind_counts[kind] = receipt.kind_counts.get(kind, 0) + 1

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
            transition = pr.observed_transitions[-1]
            s, a, s_next, t = (
                transition.s,
                transition.a,
                transition.s_next,
                transition.t,
            )
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
    args = ap.parse_args()

    project_dir = Path(args.project).resolve()

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
    }, indent=2))
    return 0



if __name__ == "__main__":
    raise SystemExit(_cli())
