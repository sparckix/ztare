---
id: GP-157
status: active
summary: GP-101 self-model for src/ztare/orchestrator/parallel_mutator.py (Phase 4e skeleton, NOT YET WIRED)
---

# orchestrator/parallel_mutator.py — architectural map

GP-157 v5.0 Phase 4e self-model. Pull-forward of GP-060 Parallel Champion
Synthesis design + Gemini Pro master-worker MCTS framing. Shipped as
ADDITIVE skeleton: data shapes locked, autoresearch_loop NOT modified.

## Region map

region: imports  lines: 39-43  entry: from __future__ import annotations
region: default_personas  lines: 46-55  entry: DEFAULT_PARALLEL_PERSONAS
region: mutator_task  lines: 58-67  entry: @dataclass(frozen=True)
region: mutator_result  lines: 69-83  entry: class MutatorResult
region: run_parallel_mutators  lines: 86-130  entry: def run_parallel_mutators
region: pick_best_candidate  lines: 133-160  entry: def pick_best_candidate
region: build_default_tasks  lines: 163-180  entry: def build_default_tasks

## Function/method index

func: run_parallel_mutators  sig: (tasks, mutator_fn, *, max_workers=None) -> list[MutatorResult]
func: pick_best_candidate  sig: (results, scoring_fn=None) -> Optional[MutatorResult]
func: build_default_tasks  sig: (k: int = 3) -> list[MutatorTask]

## Exit list

(No raises — per-task exceptions caught in run_parallel_mutators and
recorded as MutatorResult.extras["__error__"]. pick_best_candidate
returns None when no viable candidates rather than raising.)

## Wiring status

NOT WIRED. autoresearch_loop does not invoke parallel_mutator in this
commit. Future commit: read `parallel_mutator_k` from rubric, build
tasks, run, pick winner, adopt.

## Drift policy

Registered in MAP_REGISTRY as label `parallel_mutator`. Run
`make arch-validate` after edits.
