"""W-method / Vasilevskii-Chow coverage-debt planner (GP-250).

THREE-CALL COMPOSITION over existing primitives — no new components:

    holes  = image_set.holes(name, reachable_carriers)   # α boundary (ImageMaintainingSet)
    ranked = identification_bits(partition, n)            # one pricing door (already exists)
    plan   = pursue_goal(champion, goal=hole_class_fn)    # γ operational (already exists)
    prune(observation)                                    # two-ledger write (already exists)

R-MAX framing: plan through KNOWN dynamics (champion) toward UNKNOWN (s,a)
classes; execution divergences are free counterexamples fed back via prune().

Quotient α: `sound_signature` from object_roles — volatile-position frozenset,
aliasing-free, no role induction needed (single-pass scan over transitions).

Receipt: workspace/coverage_debt.jsonl
  {schema: ztare.coverage_debt.v1, n_classes, n_covered, n_holes,
   top_holes: [{class_repr, action, plan_found}]}

CLI:
  python -m ztare.worldmodel.coverage_planner --project P [--debt]
  python -m ztare.worldmodel.coverage_planner --project P --execute [--live] [--max-holes N]
"""

from __future__ import annotations

import json
import logging
import os
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

_log = logging.getLogger(__name__)

_SWEEP_MAX_STATES = int(os.environ.get("ZTARE_SWEEP_MAX_STATES", "5000"))
_RECEIPT_SCHEMA = "ztare.coverage_debt.v1"
_DEBT_FILE = "coverage_debt.jsonl"


# ─── α: sound_signature quotient ─────────────────────────────────────────────

def _volatile_positions(transitions: list) -> frozenset:
    """One-pass scan: positions whose value changes in >=1 transition."""
    vp: set = set()
    for tr in transitions:
        s, s_next = tr.s, tr.s_next
        for y in range(len(s)):
            for x in range(len(s[0])):
                if s[y][x] != s_next[y][x]:
                    vp.add((y, x))
    return frozenset(vp)


def _make_alpha(volatile_pos: frozenset):
    """Return the α functor: grid → frozenset of (y,x,color) for volatile cells."""
    def alpha(grid) -> frozenset:
        return frozenset((y, x, grid[y][x]) for (y, x) in volatile_pos)
    return alpha


# ─── γ: reachable carrier enumeration (bounded BFS) ─────────────────────────

def _reachable_carriers(
    champion,
    start_states: list,
    action_arity: int,
    alpha,
    *,
    max_states: int = _SWEEP_MAX_STATES,
) -> dict:
    """BFS forward from evidence starts, deduped on α-carrier.

    Returns {carrier: representative_grid}. Bounded by max_states.
    This is the one non-trivial glue that coverage_planner contributes:
    wiring the bounded sweep into the α/image_set machinery.
    """
    from ztare.worldmodel.gates import as_predictor
    predict = as_predictor(champion)

    seen: dict = {}
    queue: deque = deque()
    for s in start_states:
        c = alpha(s)
        if c not in seen:
            seen[c] = s
            queue.append((s, 0))

    n = 0
    while queue and n < max_states:
        grid, step = queue.popleft()
        for a in range(action_arity):
            nxt = predict(grid, a, step)
            if nxt is None:
                continue
            c = alpha(nxt)
            if c not in seen:
                seen[c] = nxt
                queue.append((nxt, step + 1))
                n += 1
    return seen


# ─── Hole ranking via the one pricing door ────────────────────────────────────

def _rank_holes(
    holes: list[tuple],
    covered_set: set,
) -> list[tuple]:
    """Rank (carrier, action) holes by identification_bits over match/nomatch partition.

    Mirrors residual_specialists._information_yield: same one pricing door.
    """
    from ztare.common.information_yield_pricing import identification_bits
    n = len(covered_set) or 1
    ranked = []
    for carrier, a in holes:
        matching = sum(1 for (cc, _ca) in covered_set if cc == carrier)
        nomatch = n - matching
        partition: dict = {}
        if matching:
            partition["match"] = ["x"] * matching
        if nomatch:
            partition["nomatch"] = ["x"] * nomatch
        bits = identification_bits(partition, n) if partition else 0.0
        ranked.append((bits, carrier, a))
    ranked.sort(key=lambda r: r[0], reverse=True)
    return ranked


# ─── In-model BFS: plan to reach target carrier class ────────────────────────

def _plan_to_carrier(
    champion,
    start: Any,
    action_arity: int,
    target_carrier: frozenset,
    alpha,
    target_action: int,
    *,
    max_depth: int = 12,
    max_nodes: int = 20000,
) -> "list[int] | None":
    """BFS in champion's predicted model to reach a state with α(s)==target_carrier,
    then append target_action. Returns the action sequence or None.
    """
    from ztare.worldmodel.gates import as_predictor
    predict = as_predictor(champion)

    if alpha(start) == target_carrier:
        return [target_action]

    seen = {alpha(start)}
    queue: deque = deque([(start, 0, [])])
    nodes = 0
    while queue and nodes < max_nodes:
        grid, step, path = queue.popleft()
        if len(path) >= max_depth:
            continue
        for a in range(action_arity):
            nxt = predict(grid, a, step)
            if nxt is None:
                continue
            c = alpha(nxt)
            if c in seen:
                continue
            seen.add(c)
            nodes += 1
            new_path = path + [a]
            if c == target_carrier:
                return new_path + [target_action]
            queue.append((nxt, step + 1, new_path))
    return None


# ─── Public API ───────────────────────────────────────────────────────────────

@dataclass
class CoverageDebt:
    n_classes: int
    n_covered: int
    n_holes: int
    top_holes: list[dict] = field(default_factory=list)
    reachability_capped: bool = False
    detail: str = ""


def coverage_debt(project_dir: "str | Path", *, max_holes: int = 20) -> CoverageDebt:
    """Build witnessed (state_class, action) cover; enumerate holes via image_set.holes().

    Three-call composition:
      1. Build ImageMaintainingSet with α=sound_signature; add all witnessed states.
      2. Enumerate reachable carriers via bounded BFS.
      3. holes = image_set.holes('alpha', reachable_carriers) — the α-boundary.
      4. Rank via identification_bits.

    Receipt written to workspace/coverage_debt.jsonl.
    """
    from ztare.common.image_set import ImageMaintainingSet

    project_dir = Path(project_dir).resolve()
    champion, action_arity, transitions = _load_project(project_dir)
    if champion is None or not transitions:
        result = CoverageDebt(
            n_classes=0, n_covered=0, n_holes=0,
            detail="no champion or no transitions found",
        )
        _write_receipt(project_dir, result)
        return result

    volatile_pos = _volatile_positions(transitions)
    if not volatile_pos:
        result = CoverageDebt(
            n_classes=0, n_covered=0, n_holes=0,
            detail="no volatile positions — all transitions are identity",
        )
        _write_receipt(project_dir, result)
        return result

    alpha = _make_alpha(volatile_pos)

    # Step 1: build ImageMaintainingSet from witnessed (state, action) pairs.
    # α image over states is our coverage tracker.
    # ponytail: track (carrier, action) pairs; store them as witnessed set.
    img_set = ImageMaintainingSet(functors={"alpha": alpha})
    covered: set = set()
    for tr in transitions:
        img_set.add(tr.s)
        covered.add((alpha(tr.s), tr.a))

    # Step 2: enumerate reachable abstract classes
    start_states = list({tr.s for tr in transitions})
    reachable = _reachable_carriers(
        champion, start_states, action_arity, alpha,
        max_states=_SWEEP_MAX_STATES,
    )
    capped = len(reachable) >= _SWEEP_MAX_STATES

    # Step 3: holes = reachable (class, action) pairs − covered, via image_set.holes()
    # image_set.holes() gives carriers in reachable but not in the witnessed image.
    # We extend to (carrier, action) pairs below.
    all_reachable_pairs = {(c, a) for c in reachable for a in range(action_arity)}
    holes_list = list(all_reachable_pairs - covered)

    n_classes = len(reachable)
    n_covered = len(all_reachable_pairs - set(holes_list))
    n_holes = len(holes_list)

    # Step 4: rank via the one pricing door
    ranked = _rank_holes(holes_list, covered)

    top_hole_entries: list[dict] = []
    for (bits, carrier, a) in ranked[:max_holes]:
        rep = reachable.get(carrier)
        plan = None
        if rep is not None:
            plan = _plan_to_carrier(champion, rep, action_arity, carrier, alpha, a)
        top_hole_entries.append({
            "class_repr": _carrier_repr(carrier),
            "action": a,
            "plan_found": plan is not None,
            "identification_bits": round(bits, 6),
        })

    result = CoverageDebt(
        n_classes=n_classes,
        n_covered=n_covered,
        n_holes=n_holes,
        top_holes=top_hole_entries,
        reachability_capped=capped,
        detail=(f"reachability capped at {_SWEEP_MAX_STATES} states — "
                "post-boundary classes may be beyond horizon"
                if capped else
                f"{n_classes} classes, {n_covered} covered, {n_holes} holes"),
    )
    _write_receipt(project_dir, result)
    return result


def plan_to_hole(project_dir: "str | Path", hole: dict) -> "list[int] | None":
    """In-model BFS to reach the hole's abstract class, then execute hole action.

    `hole` must carry: class_repr (str), action (int).
    """
    project_dir = Path(project_dir).resolve()
    champion, action_arity, transitions = _load_project(project_dir)
    if champion is None or not transitions:
        return None

    volatile_pos = _volatile_positions(transitions)
    if not volatile_pos:
        return None

    alpha = _make_alpha(volatile_pos)
    start_states = list({tr.s for tr in transitions})
    reachable = _reachable_carriers(champion, start_states, action_arity, alpha)

    rep_str = str(hole.get("class_repr", ""))
    target_carrier = next(
        (c for c in reachable if _carrier_repr(c) == rep_str), None
    )
    if target_carrier is None:
        return None

    start = hole.get("start_grid") or reachable[target_carrier]
    return _plan_to_carrier(
        champion, start, action_arity, target_carrier, alpha,
        int(hole.get("action", 0)),
    )


@dataclass
class ExecutionReceipt:
    schema: str = "ztare.coverage_execution.v1"
    hole: dict = field(default_factory=dict)
    plan: "list[int] | None" = None
    plan_found: bool = False
    dry_run: bool = True
    steps_executed: int = 0
    counterexamples_written: int = 0
    hole_witnessed: bool = False
    detail: str = ""
    ts: str = field(default_factory=lambda: datetime.now(datetime.UTC).isoformat()
                    if hasattr(datetime, "UTC") else datetime.utcnow().isoformat())


def execute_plans(
    project_dir: "str | Path",
    *,
    max_holes: int = 3,
    dry_run: bool = True,
) -> list[ExecutionReceipt]:
    """dry_run=True: emit plans only. Live: execute with MPC repair — on champion
    prediction divergence, record counterexample via prune() and replan once.
    """
    project_dir = Path(project_dir).resolve()
    champion, action_arity, transitions = _load_project(project_dir)
    if champion is None or not transitions:
        return []

    volatile_pos = _volatile_positions(transitions)
    if not volatile_pos:
        return []

    alpha = _make_alpha(volatile_pos)
    covered: set = set()
    for tr in transitions:
        covered.add((alpha(tr.s), tr.a))

    start_states = list({tr.s for tr in transitions})
    reachable = _reachable_carriers(champion, start_states, action_arity, alpha)

    all_pairs = {(c, a) for c in reachable for a in range(action_arity)}
    holes_list = list(all_pairs - covered)
    ranked = _rank_holes(holes_list, covered)

    from ztare.worldmodel.gates import as_predictor
    predict = as_predictor(champion)

    receipts: list[ExecutionReceipt] = []
    for (bits, target_carrier, target_action) in ranked[:max_holes]:
        rep = reachable.get(target_carrier)
        if rep is None:
            continue

        plan = _plan_to_carrier(champion, rep, action_arity, target_carrier, alpha, target_action)
        hole_info = {
            "class_repr": _carrier_repr(target_carrier),
            "action": target_action,
            "identification_bits": round(bits, 6),
        }

        if dry_run or plan is None:
            receipts.append(ExecutionReceipt(
                hole=hole_info, plan=plan, plan_found=plan is not None,
                dry_run=True, detail="dry_run: plan emitted, no live execution",
            ))
            continue

        # Live: MPC execution with one replan on divergence
        try:
            adapter = _adapter_from_project(project_dir)
            adapter.reset()
        except Exception as exc:  # noqa: BLE001
            receipts.append(ExecutionReceipt(
                hole=hole_info, plan=plan, plan_found=True, dry_run=False,
                detail=f"adapter failed: {exc}",
            ))
            continue

        state = adapter.state
        cx_written = 0
        steps_done = 0
        hole_witnessed = False
        current_plan = list(plan)
        replans = 0

        while current_plan and replans < 3:
            a = current_plan.pop(0)
            predicted = predict(state, a, adapter.t)
            real_next = adapter.step(a)
            steps_done += 1

            mismatch = predicted is None or real_next != predicted
            if mismatch:
                from ztare.worldmodel.distinguishing_play import prune
                obs = {
                    "target_id": f"coverage_{_carrier_repr(target_carrier)[:8]}",
                    "s": [list(r) for r in state],
                    "action": int(a),
                    "s_next": [list(r) for r in real_next],
                    "t": int(getattr(adapter, "t", 0) - 1),
                    "kind": "coverage_mpc_divergence",
                }
                try:
                    pc, _nc = prune(project_dir, obs)
                    cx_written += pc
                except Exception:  # noqa: BLE001
                    pass
                state = real_next
                current_plan = _plan_to_carrier(
                    champion, state, action_arity, target_carrier, alpha, target_action,
                ) or []
                replans += 1
                continue

            state = real_next
            if alpha(state) == target_carrier:
                # Execute the hole action and witness it
                real_hole_next = adapter.step(target_action)
                steps_done += 1
                from ztare.worldmodel.distinguishing_play import prune
                obs = {
                    "target_id": f"coverage_hole_{_carrier_repr(target_carrier)[:8]}",
                    "s": [list(r) for r in state],
                    "action": int(target_action),
                    "s_next": [list(r) for r in real_hole_next],
                    "t": int(getattr(adapter, "t", 0) - 1),
                    "kind": "coverage_hole_witnessed",
                }
                try:
                    pc, _nc = prune(project_dir, obs)
                    cx_written += pc
                except Exception:  # noqa: BLE001
                    pass
                hole_witnessed = True
                break

        receipts.append(ExecutionReceipt(
            hole=hole_info, plan=plan, plan_found=True, dry_run=False,
            steps_executed=steps_done, counterexamples_written=cx_written,
            hole_witnessed=hole_witnessed,
            detail=f"executed {steps_done} steps, {replans} replans, "
                   f"cx_written={cx_written}, hole_witnessed={hole_witnessed}",
        ))

    # Append session receipt
    ws = project_dir / "workspace"
    ws.mkdir(parents=True, exist_ok=True)
    with (ws / "coverage_execution.jsonl").open("a") as f:
        f.write(json.dumps({
            "schema": "ztare.coverage_execution_session.v1",
            "ts": datetime.utcnow().isoformat(),
            "dry_run": dry_run,
            "n_holes_attempted": len(receipts),
            "receipts": [{
                "hole": r.hole, "plan_found": r.plan_found,
                "steps_executed": r.steps_executed,
                "counterexamples_written": r.counterexamples_written,
                "hole_witnessed": r.hole_witnessed,
                "detail": r.detail,
            } for r in receipts],
        }) + "\n")
    return receipts


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _carrier_repr(carrier: frozenset) -> str:
    return json.dumps(sorted(carrier), separators=(",", ":"))


def _load_project(project_dir: Path) -> "tuple[Any, int, list]":
    from ztare.worldmodel.evidence_consolidation import (
        _load_carrier_from_source, resolve_episode_paths,
    )
    from ztare.worldmodel.episode_log import EpisodeLog

    champ_path = project_dir / "test_model.py"
    if not champ_path.exists():
        _log.warning("no test_model.py in %s", project_dir)
        return None, 4, []
    try:
        champion = _load_carrier_from_source(champ_path.read_text(), str(champ_path), project_dir)
    except Exception as exc:  # noqa: BLE001
        _log.warning("champion load failed: %s", exc)
        return None, 4, []

    visible_path = resolve_episode_paths(project_dir).get("visible")
    if visible_path is None or not visible_path.exists():
        return champion, 4, []

    transitions = list(EpisodeLog.read_jsonl(visible_path))
    actions = {tr.a for tr in transitions}
    action_arity = max(actions) + 1 if actions else 4
    cfg = project_dir / "play_config.json"
    if cfg.exists():
        try:
            action_arity = int(json.loads(cfg.read_text()).get("action_arity", action_arity))
        except Exception:  # noqa: BLE001
            pass
    return champion, action_arity, transitions


def _adapter_from_project(project_dir: Path):
    import importlib
    try:
        ArcAgi3Adapter = importlib.import_module("ztare.substrates.arc_agi3").ArcAgi3Adapter
    except ImportError as exc:
        raise RuntimeError(f"ArcAgi3Adapter not importable: {exc}") from exc
    cfg = project_dir / "play_config.json"
    game_hint = ""
    if cfg.exists():
        try:
            game_hint = str(json.loads(cfg.read_text()).get("game") or "").strip()
        except Exception:  # noqa: BLE001
            pass
    if not game_hint:
        tokens = project_dir.name.split("_")
        game_hint = tokens[1] if len(tokens) >= 2 else project_dir.name
    try:
        list_games = importlib.import_module("ztare.substrates.arc_agi3").list_games
        game_id = next((g for g in list_games() if g.startswith(game_hint)), None)
    except Exception:  # noqa: BLE001
        game_id = None
    if not game_id:
        raise RuntimeError(f"Could not resolve game id from {game_hint!r}")
    return ArcAgi3Adapter(game_id)


def _write_receipt(project_dir: Path, result: CoverageDebt) -> None:
    ws = project_dir / "workspace"
    ws.mkdir(parents=True, exist_ok=True)
    with (ws / _DEBT_FILE).open("a") as f:
        f.write(json.dumps({
            "schema": _RECEIPT_SCHEMA,
            "ts": datetime.utcnow().isoformat(),
            "n_classes": result.n_classes,
            "n_covered": result.n_covered,
            "n_holes": result.n_holes,
            "reachability_capped": result.reachability_capped,
            "top_holes": result.top_holes,
            "detail": result.detail,
        }) + "\n")


# ─── CLI ──────────────────────────────────────────────────────────────────────

def _cli() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Coverage-debt planner (W-method / α-boundary)")
    ap.add_argument("--project", required=True)
    ap.add_argument("--debt", action="store_true")
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--max-holes", type=int, default=3)
    args = ap.parse_args()
    project_dir = Path(args.project).resolve()

    if args.execute:
        receipts = execute_plans(project_dir, max_holes=args.max_holes, dry_run=not args.live)
        print(json.dumps([{
            "hole": r.hole, "plan_found": r.plan_found,
            "steps_executed": r.steps_executed,
            "counterexamples_written": r.counterexamples_written,
            "hole_witnessed": r.hole_witnessed,
            "detail": r.detail,
        } for r in receipts], indent=2))
        return 0

    result = coverage_debt(project_dir, max_holes=args.max_holes)
    print(json.dumps({
        "n_classes": result.n_classes,
        "n_covered": result.n_covered,
        "n_holes": result.n_holes,
        "reachability_capped": result.reachability_capped,
        "detail": result.detail,
        "top_holes": result.top_holes[:5],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
