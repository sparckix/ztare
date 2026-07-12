#!/usr/bin/env python3
"""ARC-AGI-3 self-play probe under an already-closed worldmodel.

This spends live environment actions but no governed mutator tokens. It answers
one question: given a candidate transition model that already passed replay and
holdout, can the generic planner/coverage loop turn that model into sealed
reward progress?
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))

from ztare.substrates.arc_agi3 import ArcAgi3Adapter, list_games  # noqa: E402
from ztare.worldmodel.gates import as_predictor  # noqa: E402
from ztare.worldmodel.planner import pursue_goal  # noqa: E402


def _load_play_loop_module():
    path = REPO / "scripts" / "public" / "control" / "arc3_play_loop.py"
    spec = importlib.util.spec_from_file_location("arc3_play_loop_helpers", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not import arc3_play_loop helpers")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_candidate(path: Path):
    ns: dict = {"__name__": "candidate"}
    exec(compile(path.read_text(), str(path), "exec"), ns)
    spec = ns.get("WORLD_MODEL_SPEC")
    if spec is not None:
        from ztare.worldmodel.spec_catalog import lower_spec

        model, err = lower_spec(spec)
        if model is None:
            raise RuntimeError(f"WORLD_MODEL_SPEC failed to lower: {err}")
        return model
    for alias in ("step", "f", "model", "I_model"):
        fn = ns.get(alias)
        if callable(fn):
            return fn
    raw = ns.get("PROGRAM")
    if raw is not None:
        def _to(node):
            return tuple(_to(x) for x in node) if isinstance(node, list) else node
        return _to(raw)
    raise RuntimeError("candidate exposes no supported worldmodel carrier")


def _diff_count(a, b) -> int:
    return sum(1 for ra, rb in zip(a, b) for ca, cb in zip(ra, rb) if ca != cb)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", required=True)
    ap.add_argument("--project", default=None)
    ap.add_argument("--candidate-path", required=True)
    ap.add_argument("--max-steps", type=int, default=250)
    ap.add_argument("--plan-depth", type=int, default=10)
    ap.add_argument("--max-replans", type=int, default=12)
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    game_id = next((g for g in list_games() if g.startswith(args.game)), None)
    if game_id is None:
        raise SystemExit(f"game {args.game} not found")
    project = Path(args.project) if args.project else REPO / "projects" / f"arc3_{args.game}_gov"
    model = _load_candidate(Path(args.candidate_path))
    predict = as_predictor(model)

    helper = _load_play_loop_module()
    adapter = ArcAgi3Adapter(game_id)
    start = adapter.reset()
    before = int(getattr(adapter, "levels_completed", 0) or 0)
    pr = pursue_goal(
        adapter,
        model,
        resource_colors=helper._resource_colors(project),
        invariants=helper._invariants(project),
        abstract_fn=helper._abstract_fn(project),
        coverage_fn=helper._coverage_fn(project),
        visited_store=set(),
        max_steps=args.max_steps,
        plan_depth=args.plan_depth,
        max_replans=args.max_replans,
    )
    after = int(getattr(adapter, "levels_completed", 0) or 0)
    terminal = adapter.state
    witness = (pr.divergence or {}).get("terminal_witness") if pr.divergence else None
    receipt = {
        "schema": "ztare-arc3-self-play-probe-v1",
        "game": game_id,
        "project": project.name,
        "candidate_path": str(args.candidate_path),
        "status": pr.status,
        "steps_executed": pr.steps_executed,
        "levels_before": before,
        "levels_after": after,
        "levels_gained": max(after - before, pr.levels_gained),
        "saturated": bool(pr.saturated),
        "terminal_verifier_model_mismatch": pr.status == "goal_reached" and pr.divergence is not None,
        "reward_model_mismatch": pr.status == "goal_reached" and pr.divergence is not None,
        "terminal_witness_sha": witness.get("sha256") if isinstance(witness, dict) else None,
        "replans": pr.replans,
        "trace": pr.trace,
        "observed_transitions": len(pr.observed_transitions),
        "terminal_diff_from_start": _diff_count(start, terminal),
        "detail": pr.detail,
        "divergence": None
        if pr.divergence is None
        else {
            "action": pr.divergence.get("action"),
            "step": pr.divergence.get("step"),
        },
        "authority": "sealed environment levels_completed is the terminal verifier; model only steers",
    }
    text = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text)
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
