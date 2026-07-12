#!/usr/bin/env python3
"""GP-250 P1-external: end-to-end on a real ARC-AGI-3 game.

Pipeline (kernel-first, no game-specific logic):
  1. acquire_evidence over the live adapter (reset-witnessing across actions)
  2. if grammar_ceiling: run the earned-extension loop — the mutator proposes
     ONE new primitive from raw diffs (sealed rule), sandbox-compiled, promoted
     only if the re-synthesized champion survives replay + held-out rollout
  3. once a champion is ratified: pursue_goal — plan through the model and
     execute against the live game, stopping on the sealed levels_completed
     reward (or reporting model_diverged off the witnessed basin)

Spends subscription tokens for the ceiling mutator (sealed claude by default).
Usage: python3 scripts/public/control/arc3_live_run.py [--game ls20] [--model claude]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))

from ztare.substrates.arc_agi3 import ArcAgi3Adapter  # noqa: E402
from ztare.worldmodel.adapter import (  # noqa: E402
    acquire_evidence, committee_read_model_path, episode_log_path)
from ztare.worldmodel.episode_log import EpisodeLog  # noqa: E402
from ztare.worldmodel.grid_dsl import EXTENSIONS  # noqa: E402
from ztare.worldmodel.planner import pursue_goal  # noqa: E402
from ztare.worldmodel.synthesis import synthesize  # noqa: E402


def _to_program(node):
    """JSON nested lists -> grid_dsl tuple AST (committee read model stores lists)."""
    if isinstance(node, list):
        return tuple(_to_program(x) for x in node)
    return node


def _model_id(arg: str) -> str:
    from ztare.common.llm_runtime import resolve_model_id
    try:
        return resolve_model_id(arg)
    except Exception:
        return arg


def run(game: str, model_arg: str, max_probes: int, max_ceiling_attempts: int) -> dict:
    from ztare.substrates.arc_agi3 import list_games
    games = list_games()
    match = next((g for g in games if g.startswith(game)), None)
    if match is None:
        return {"error": f"game {game} not in {games[:8]}..."}

    adapter = ArcAgi3Adapter(match)
    adapter.reset()
    project = REPO / "projects" / f"arc3_{game}_live"
    project.mkdir(parents=True, exist_ok=True)

    report: dict = {"game": match, "arity": adapter.action_arity, "phases": []}

    # Phase 1 — identify
    receipt = acquire_evidence(project, adapter, max_probes=max_probes)
    report["phases"].append({"phase": "acquire", "status": receipt.status,
                             "probes": receipt.probes_taken,
                             "committee": receipt.committee_size})

    # Phase 2 — earn grammar if the seed cannot express the world
    if receipt.status == "grammar_ceiling":
        from ztare.common.llm_runtime import LLMRuntime
        from ztare.worldmodel.grammar_extension import (
            attempt_extension, render_ceiling_prompt, rollback_if_rejected)
        model_id = _model_id(model_arg)
        runtime = LLMRuntime()
        log = EpisodeLog.read_jsonl(episode_log_path(project))
        holdout_actions = [(i % adapter.action_arity) for i in range(40)]
        holdout = EpisodeLog()
        for a in holdout_actions:
            t_now = adapter.t
            s = adapter.state
            s2 = adapter.step(a)
            holdout.append(s, a, s2, t=t_now)
        from ztare.worldmodel.synthesis import context_coverage
        base_prompt = render_ceiling_prompt(log, adapter.action_arity)
        prompt = base_prompt
        earned, retained = None, []
        for attempt in range(1, max_ceiling_attempts + 1):
            cov = context_coverage(log, adapter.action_arity)
            print(f"  [ceiling {attempt}/{max_ceiling_attempts}] {model_id} "
                  f"(coverage {cov[0]}/{cov[1]}) ...", flush=True)
            # Route through the dispatch layer: with ZTARE_AGENT_DISPATCH_MUTATOR=agent
            # this is a SEALED subscription worker (claude/codex, no API spend); without
            # the env it falls back to the API lane of whatever --model names.
            from ztare.common.dispatch_model import dispatch_call_text
            resp = dispatch_call_text(
                "mutator", prompt,
                llm_response_call=lambda p: runtime.call_text(
                    p, model_id=model_id, max_tokens=1400, timeout_seconds=300,
                    request_label=f"gp250-arc3-{game}"),
                repo=str(REPO), timeout_seconds=420)
            rc = attempt_extension(project, log, holdout, adapter.action_arity,
                                   resp.text, model_id=model_id, prompt=prompt,
                                   env_hint=game, retain_on_coverage_gain=True)
            print(f"    proposal `{rc.name}` -> {rc.verdict}: {rc.detail[:90]}", flush=True)
            if rc.verdict == "promoted":
                earned = rc.name
                break
            if rc.verdict == "retained_partial":
                retained.append(rc.name)
                prompt = base_prompt + (
                    f"\n\nPrimitives already accepted this session: {retained} — they explain "
                    f"part of the data ({rc.detail}). Propose a DIFFERENT primitive for the "
                    f"transitions still unexplained; same JSON contract.")
                continue
            rollback_if_rejected(rc)
            prompt = prompt + (f"\n\nYour proposal `{rc.name}` was rejected: {rc.detail}. "
                               f"Propose a corrected primitive; same JSON contract.")
        cov = context_coverage(log, adapter.action_arity)
        report["phases"].append({"phase": "ceiling", "earned": earned,
                                 "retained_partial": retained, "attempts": attempt,
                                 "coverage": f"{cov[0]}/{cov[1]}",
                                 "extensions": sorted(EXTENSIONS)})
        if earned or retained:
            result = synthesize(log, adapter.action_arity)
            report["phases"].append({"phase": "re_synthesize", "status": result.status})

    # Phase 3 — pursue the goal through the ratified model
    model_path = committee_read_model_path(project)
    champion = None
    if model_path.exists():
        rm = json.loads(model_path.read_text())
        if rm.get("status") == "committee":

            champion = _to_program(rm.get("champion"))
    if champion is not None:
        pursuit = pursue_goal(adapter, champion, max_steps=200)
        report["phases"].append({"phase": "pursue", "status": pursuit.status,
                                 "steps": pursuit.steps_executed,
                                 "levels_gained": pursuit.levels_gained,
                                 "detail": pursuit.detail})
    else:
        report["phases"].append({"phase": "pursue", "status": "no_ratified_model",
                                 "detail": "no singleton committee to plan through"})

    report["levels_completed"] = adapter.levels_completed
    (project / "arc3_live_report.json").write_text(json.dumps(report, indent=2))
    return report


def main() -> int:
    args = sys.argv
    game = args[args.index("--game") + 1] if "--game" in args else "ls20"
    model = args[args.index("--model") + 1] if "--model" in args else "claude"
    probes = int(args[args.index("--probes") + 1]) if "--probes" in args else 24
    ceiling = int(args[args.index("--ceiling") + 1]) if "--ceiling" in args else 4
    report = run(game, model, probes, ceiling)
    print(json.dumps(report, indent=2))
    return 0 if "error" not in report else 1


if __name__ == "__main__":
    raise SystemExit(main())
