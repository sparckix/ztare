#!/usr/bin/env python3
"""GP-250 ceiling-extension run: the mutator earns a grammar extension, live.

For each deliberately-inexpressible sealed environment (e03 gravity, e09
rotation), this: builds a witnessing episode log, confirms `grammar_ceiling`,
prompts the model (raw grids only — sealed rule), sandbox-compiles the
proposal, and keeps it only if the re-synthesized champion passes replay +
full-depth held-out rollout. Up to three Compiler-Bounce retries with the
failure injected. Post-hoc (harness-side, after promotion): behavioral
equivalence against the sealed law — a promoted-but-wrong extension is a
false ratification and fails the run.

Spends model tokens (one small call per attempt). Usage:
    python scripts/public/control/worldmodel_ceiling_run.py [--model deepseek]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))

from ztare.common.llm_runtime import LLMRuntime, resolve_model_id  # noqa: E402
from ztare.substrates.arc_synthetic import ENVIRONMENTS, scripted_random_actions  # noqa: E402
from ztare.worldmodel.episode_log import EpisodeLog  # noqa: E402
from ztare.worldmodel.grammar_extension import (  # noqa: E402
    attempt_extension, render_ceiling_prompt, rollback_if_rejected,
)
from ztare.worldmodel.grid_dsl import EXTENSIONS, evaluate  # noqa: E402
from ztare.worldmodel.synthesis import synthesize  # noqa: E402

CEILING_ENVS = ("e03_gravity", "e09_rotation")
OUT_DIR = REPO / "workspace" / "worldmodel_ceiling"


def _log_from(env, actions) -> EpisodeLog:
    log = EpisodeLog()
    for s, a, s_next in env.rollout(actions):
        log.append(s, a, s_next)
    return log


def _reset_witnessing_log(env, per_episode: int, seed: int) -> EpisodeLog:
    """Multi-episode witnessing for absorbing worlds: one short episode per
    action, each OPENING with that action on the pristine initial state, then
    a random tail. Discovered necessary by the e03 matched control: gravity
    settles the world on the first probe, so single-episode round-robin never
    witnesses the other actions on unsettled matter, and an over-generalized
    champion survives replay only to die (correctly) at the rollout gate."""
    log = EpisodeLog()
    for opening in range(env.action_arity):
        actions = [opening] + scripted_random_actions(env, per_episode - 1,
                                                      seed + opening)
        for t, (s, a, s_next) in enumerate(env.rollout(actions)):
            log.append(s, a, s_next, t=t)  # env restarts its step per episode
    return log


def _counterexample(env, log, fn) -> str:
    """One concrete before/expected/got for the Compiler Bounce."""
    for tr in log:
        if tr.s == tr.s_next:
            continue
        try:
            got = fn(tr.s)
        except Exception as exc:
            got = f"<raised {exc}>"
        if got != tr.s_next:
            def r(g):
                return "; ".join(" ".join(str(c) for c in row) for row in g) if isinstance(g, tuple) else str(g)
            return (f"counterexample — input: [{r(tr.s)}] expected: [{r(tr.s_next)}] "
                    f"your function returned: [{r(got)}]")
    return ""


def _equivalent_to_sealed(program, env, log, holdout) -> bool:
    for source in (log, holdout):
        for tr in source:
            for a in range(env.action_arity):
                if evaluate(program, tr.s, a, tr.t) != env.transition(tr.s, a, tr.t):
                    return False
    return True


def run_env(env, runtime, model_id: str) -> dict:
    log = _reset_witnessing_log(env, per_episode=20, seed=11)
    holdout = _log_from(env, scripted_random_actions(env, 40, seed=23))

    base = synthesize(log, env.action_arity)
    if base.status != "grammar_ceiling":
        return {"env": env.env_id, "verdict": "skipped",
                "detail": f"expected grammar_ceiling, got {base.status}"}

    prompt = render_ceiling_prompt(log, env.action_arity)
    project_dir = OUT_DIR / env.env_id
    last = None
    for attempt in range(1, 4):
        print(f"  [{env.env_id}] attempt {attempt}: calling {model_id} ...", flush=True)
        response = runtime.call_text(prompt, model_id=model_id, max_tokens=1200,
                                     timeout_seconds=240,
                                     request_label=f"gp250-ceiling-{env.env_id}")
        receipt = attempt_extension(project_dir, log, holdout, env.action_arity,
                                    response.text, model_id=model_id,
                                    prompt=prompt, env_hint=env.env_id)
        last = receipt
        print(f"  [{env.env_id}] proposal `{receipt.name}` -> {receipt.verdict}: "
              f"{receipt.detail[:100]}", flush=True)
        if receipt.verdict == "promoted":
            champion = synthesize(log, env.action_arity).champion
            if _equivalent_to_sealed(champion, env, log, holdout):
                return {"env": env.env_id, "verdict": "promoted_and_equivalent",
                        "extension": receipt.name, "champion": str(champion),
                        "attempts": attempt}
            rollback_if_rejected(receipt)  # no-op (promoted), so unregister hard:
            from ztare.worldmodel.grid_dsl import unregister_extension
            unregister_extension(receipt.name)
            return {"env": env.env_id, "verdict": "FALSE_RATIFICATION",
                    "extension": receipt.name, "attempts": attempt,
                    "detail": "gates passed but champion is not equivalent to the sealed law"}
        rollback_if_rejected(receipt)
        # Compiler Bounce: re-prompt with the failure AND a concrete counterexample
        from ztare.worldmodel.grammar_extension import compile_extension
        fn, _e = compile_extension(receipt.python) if receipt.python.startswith("def") else (None, "")
        counter = _counterexample(env, log, fn) if fn else ""
        prompt = prompt + (f"\n\nYour previous proposal `{receipt.name}` was rejected: "
                           f"{receipt.detail}. {counter} "
                           f"Propose a corrected primitive; same JSON contract.")
    return {"env": env.env_id, "verdict": "unresolved_after_retries",
            "extension": (last.name if last else ""), "attempts": 3,
            "detail": (last.detail if last else "")}


def main() -> int:
    model_arg = sys.argv[sys.argv.index("--model") + 1] if "--model" in sys.argv else "deepseek"
    model_id = resolve_model_id(model_arg)
    runtime = LLMRuntime()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    results = []
    for env in ENVIRONMENTS:
        if env.env_id not in CEILING_ENVS:
            continue
        EXTENSIONS.clear()  # each environment earns its own extension from scratch
        results.append(run_env(env, runtime, model_id))

    report = {"schema": "ztare-worldmodel-ceiling-run-v1", "model": model_id,
              "results": results,
              "ok": all(r["verdict"] == "promoted_and_equivalent" for r in results)}
    (OUT_DIR / "ceiling_run_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
