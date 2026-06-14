"""Parallel mutator worker primitives for the autoresearch blitz path.

Pull-forward of GP-060 Parallel Champion Synthesis design + Gemini Pro
master-worker MCTS framing (2026-04-25). This module owns only the
small worker/task/result primitives and deterministic combiner. The live
autoresearch wire-in is `orchestrator.blitz_dispatch`, which decides when
K-way mutation should run and records tournament provenance.

Cost shape:
  - K-way parallelism is N× mutator per tournament. It remains opt-in at
    the rubric layer (`parallel_mutator_k=K`) and is normally triggered by
    stagnation, force-iters, or an explicit force flag.
  - The deterministic combiner here does not call judges or gates. The
    caller supplies scoring policy and is responsible for downstream R1,
    fit, gate, and judge validation of the selected candidate.

Selective deployment guidance (operator-honest):
  - Substrates where local-minimum trapping is the binding constraint
    (multi-basin search, multiple plausible families) — likely strong
    gain. GP-149 mining showed gp140 Chebyshev pivot was found late by
    stochastic luck; engineered divergence would catch it iter 1-2.
  - Substrates with structural quality issues (gp154 Class K, gp159
    wrong cage_meta) — gain near zero. Parallelization does not unfuck
    non-commensurable y or wrong contracts.

Operational path:
  1. `autoresearch_loop` calls `dispatch_mutator_blitz`.
  2. `dispatch_mutator_blitz` builds `MutatorTask` objects with
     persona-seeded variants of `mutate_thesis`.
  3. This module runs them concurrently and returns stable worker-id
     ordered results.
  4. The dispatch layer scores/tournaments the candidates and adopts the
     selected text as the iteration candidate, after which normal R1/gate
     validation continues.
"""

from __future__ import annotations

import concurrent.futures
from dataclasses import dataclass, field
from typing import Any, Callable, Optional


# Workers seed their mutators with different epistemic priors. Personas
# are intentionally distinct to engineer divergence (not stylistic
# variants of the same persona). MCTS framing: each persona explores a
# different branch of the hypothesis tree.
DEFAULT_PARALLEL_PERSONAS: tuple[str, ...] = (
    "newton_discovery",        # power-law / continuous-crossover prior
    "munger_inversion",        # inversion / category-switch prior
    "engineer_pragmatist",     # piecewise / hard-boundary prior
)


@dataclass(frozen=True)
class MutatorTask:
    """One parallel-worker invocation spec.

    Per Hickey: snapshot of inputs, no hidden state. The worker_id is
    included so combiners can produce reproducible logs even when
    completion order varies.
    """
    worker_id: int
    persona: str
    prompt_seed_extras: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MutatorResult:
    """One worker's output, scored by the apparatus.

    `score` is the full-pipeline judge score (0-100) when the result
    has been evaluated; None when only the candidate is available
    (caller will score afterwards).
    """
    worker_id: int
    persona: str
    thesis_text: str
    test_model_text: str
    score: Optional[float] = None
    extras: dict[str, Any] = field(default_factory=dict)


def run_parallel_mutators(
    tasks: list[MutatorTask],
    mutator_fn: Callable[[MutatorTask], MutatorResult],
    *,
    max_workers: Optional[int] = None,
) -> list[MutatorResult]:
    """Run K mutator tasks in parallel; return results in worker_id order.

    `mutator_fn` is the per-task adapter — the autoresearch_loop's
    mutate_thesis equivalent, parameterized by MutatorTask. Caller
    bears responsibility for ensuring mutator_fn is thread-safe (the
    LLM clients today are; if that changes, this routine should switch
    to ProcessPoolExecutor).

    Failures in individual workers are caught: a failed worker
    contributes a result with thesis_text="" and extras={"__error__": ...}
    so combiners can decide whether to skip or retry.
    """
    if not tasks:
        return []
    if max_workers is None:
        max_workers = max(1, len(tasks))
    results: list[MutatorResult] = []
    by_id: dict[int, MutatorResult] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(mutator_fn, t): t for t in tasks}
        for fut in concurrent.futures.as_completed(futures):
            t = futures[fut]
            try:
                result = fut.result()
            except Exception as exc:  # noqa: BLE001
                result = MutatorResult(
                    worker_id=t.worker_id,
                    persona=t.persona,
                    thesis_text="",
                    test_model_text="",
                    score=None,
                    extras={"__error__": f"{type(exc).__name__}: {exc}"},
                )
            by_id[t.worker_id] = result
    for t in tasks:
        results.append(by_id[t.worker_id])
    return results


def pick_best_candidate(
    results: list[MutatorResult],
    scoring_fn: Optional[Callable[[MutatorResult], float]] = None,
) -> Optional[MutatorResult]:
    """Combiner — select the candidate to adopt as the iter's output.

    Selection rule (deterministic):
      - Drop results whose thesis_text is empty (worker failed).
      - If `scoring_fn` provided, score candidates and pick max.
      - Else if `result.score` already set, pick max.
      - Else fall back to first non-empty result (deterministic worker_id order).

    Returns None when no viable candidate exists.
    """
    viable = [r for r in results if r.thesis_text]
    if not viable:
        return None

    if scoring_fn is not None:
        scored = [(scoring_fn(r), r) for r in viable]
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return scored[0][1]

    pre_scored = [r for r in viable if r.score is not None]
    if pre_scored:
        return max(pre_scored, key=lambda r: r.score or float("-inf"))

    return min(viable, key=lambda r: r.worker_id)


def build_default_tasks(k: int = 3) -> list[MutatorTask]:
    """Convenience: K tasks seeded with DEFAULT_PARALLEL_PERSONAS.

    K > len(DEFAULT_PARALLEL_PERSONAS) wraps; K <= 0 returns []. Per
    operator guidance: K=3 is the recommended default
    when wiring lands; K=5 offers diminishing returns at 1.6× the
    cost.
    """
    if k <= 0:
        return []
    pool = DEFAULT_PARALLEL_PERSONAS
    return [
        MutatorTask(worker_id=i, persona=pool[i % len(pool)])
        for i in range(k)
    ]
