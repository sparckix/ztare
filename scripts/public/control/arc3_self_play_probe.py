#!/usr/bin/env python3
"""ARC-AGI-3 self-play probe under an already-closed worldmodel.

This spends live environment actions but no governed mutator tokens. It answers
one question: given a candidate transition model that already passed replay and
holdout, can the generic planner/coverage loop turn that model into sealed
task progress?
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))

from ztare.substrates.arc_agi3 import ArcAgi3Adapter, list_games  # noqa: E402
from ztare.worldmodel.gates import as_predictor  # noqa: E402
from ztare.worldmodel.grid_dsl import grid_to_lists  # noqa: E402
from ztare.worldmodel.planner import pursue_goal  # noqa: E402


def _load_play_loop_module():
    path = REPO / "scripts" / "public" / "control" / "arc3_play_loop.py"
    spec = importlib.util.spec_from_file_location("arc3_play_loop_helpers", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not import arc3_play_loop helpers")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_candidate(path: Path, project: Path, helper):
    ns: dict = {"__name__": "candidate"}
    exec(compile(path.read_text(), str(path), "exec"), ns)
    model, _progress, _goal = helper._model_from_namespace(project, ns)
    if model is None:
        raise RuntimeError("candidate exposes no supported worldmodel carrier")
    return model


def _diff_count(a, b) -> int:
    return sum(1 for ra, rb in zip(a, b) for ca, cb in zip(ra, rb) if ca != cb)


def _write_quarantined_diagnostic_trace(path: Path, model, transitions) -> dict:
    """Preserve a probe witness without admitting it to the evidence bank.

    This path is deliberately caller-selected and is never written beneath the
    project's episode directory.  It exists for apparatus inspection after an
    out-of-loop probe; governed evidence acquisition remains the sole writer of
    synthesis input.
    """
    predict = as_predictor(model)
    rows = []
    first_divergence = None
    for index, transition in enumerate(transitions):
        predicted = predict(transition.s, transition.a, transition.t)
        mismatches = []
        if predicted is None:
            prediction_status = "undefined"
        else:
            prediction_status = "matched" if predicted == transition.s_next else "diverged"
            mismatches = [
                {
                    "row": y,
                    "col": x,
                    "before": transition.s[y][x],
                    "predicted": predicted[y][x],
                    "observed": transition.s_next[y][x],
                }
                for y in range(len(transition.s_next))
                for x in range(len(transition.s_next[y]))
                if predicted[y][x] != transition.s_next[y][x]
            ]
        if prediction_status != "matched" and first_divergence is None:
            first_divergence = index
        rows.append({
            "schema": "ztare-out-of-loop-transition-diagnostic-v1",
            "authority": "quarantined_diagnostic_only",
            "admissible_to_synthesis": False,
            "index": index,
            "t": transition.t,
            "action": transition.a,
            "state": grid_to_lists(transition.s),
            "predicted": None if predicted is None else grid_to_lists(predicted),
            "observed": grid_to_lists(transition.s_next),
            "prediction_status": prediction_status,
            "mismatches": mismatches,
            "transition_identity": (
                transition.identity.to_dict() if transition.identity is not None else None
            ),
        })
    payload = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")
    return {
        "path": str(path),
        "sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        "rows": len(rows),
        "first_divergence_index": first_divergence,
        "authority": "quarantined_diagnostic_only",
        "admissible_to_synthesis": False,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", required=True)
    ap.add_argument("--project", default=None)
    ap.add_argument("--candidate-path", required=True)
    ap.add_argument("--max-steps", type=int, default=250)
    ap.add_argument("--plan-depth", type=int, default=10)
    ap.add_argument("--max-replans", type=int, default=12)
    ap.add_argument("--seed-path", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument(
        "--diagnostic-trace-out",
        default=None,
        help=(
            "optional caller-selected JSONL witness; quarantined from synthesis "
            "and intended only for out-of-loop apparatus inspection"
        ),
    )
    args = ap.parse_args(argv)

    game_id = next((g for g in list_games() if g.startswith(args.game)), None)
    if game_id is None:
        raise SystemExit(f"game {args.game} not found")
    project = Path(args.project) if args.project else REPO / "projects" / f"arc3_{args.game}_gov"
    helper = _load_play_loop_module()
    model = _load_candidate(Path(args.candidate_path), project, helper)

    adapter = ArcAgi3Adapter(game_id)
    start = adapter.reset()
    seed_receipt = None
    if args.seed_path:
        from ztare.worldmodel.level_boundary_seed import load_seed

        seed, sequence, _raw_seed, seed_sha256 = load_seed(args.seed_path)
        for action in sequence:
            adapter.step(action)
        start = adapter.state
        seed_receipt = {
            "seed_sha256": seed_sha256,
            "target_lifecycle": seed.get("target_level"),
            "interventions_executed": len(sequence),
            "observed_progress_after": int(getattr(adapter, "levels_completed", 0) or 0),
        }
    before = int(getattr(adapter, "levels_completed", 0) or 0)
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.goal_abduction import authoritative_goal_edge_predicate

    goal_edge, goal_edge_witnesses = authoritative_goal_edge_predicate(
        EpisodeLog.read_jsonl(project / "raw" / "episodes" / "episode_001.jsonl"),
        source_epoch=before,
    )
    pr = pursue_goal(
        adapter,
        model,
        goal_edge_fn=goal_edge,
        resource_colors=helper._resource_colors(project),
        invariants=helper._invariants(project),
        abstract_fn=helper._abstract_fn(project),
        coverage_fn=helper._coverage_fn(project),
        visited_store=set(),
        max_steps=args.max_steps,
        plan_depth=args.plan_depth,
        max_replans=args.max_replans,
        receipts_dir=project / "workspace",
    )
    after = int(getattr(adapter, "levels_completed", 0) or 0)
    terminal = adapter.state
    witness = (pr.divergence or {}).get("terminal_witness") if pr.divergence else None
    diagnostic_trace = None
    if args.diagnostic_trace_out:
        diagnostic_trace = _write_quarantined_diagnostic_trace(
            Path(args.diagnostic_trace_out), model, pr.observed_transitions
        )
    receipt = {
        "schema": "ztare-arc3-self-play-probe-v1",
        "game": game_id,
        "project": project.name,
        "candidate_path": str(args.candidate_path),
        "seed_receipt": seed_receipt,
        "goal_edge_witnesses": goal_edge_witnesses,
        "status": pr.status,
        "steps_executed": pr.steps_executed,
        "levels_before": before,
        "levels_after": after,
        "levels_gained": max(after - before, pr.levels_gained),
        "saturated": bool(pr.saturated),
        "terminal_verifier_model_mismatch": (
            pr.status == "goal_reached" and pr.divergence is not None
        ),
        "terminal_witness_sha": witness.get("sha256") if isinstance(witness, dict) else None,
        "terminal_witness": witness if isinstance(witness, dict) else None,
        "diagnostic_trace": diagnostic_trace,
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
