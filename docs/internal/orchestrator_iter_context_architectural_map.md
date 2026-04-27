---
id: GP-157
status: active
summary: GP-101 self-model for src/ztare/orchestrator/iter_context.py (Phase 4a IterContext)
---

# orchestrator/iter_context.py — architectural map

GP-157 v5.0 Phase 4a self-model. Format follows GP-101 token-optimized
spec — line-range regions + function index + exit list, parseable by
`scripts/validate_autoresearch_arch_map.py`.

## Purpose

`IterContext` is the per-iteration state snapshot that the autoresearch
loop's main per-iter block will eventually flow through (Phase 4a-step-2),
and that the Cage v5.0 dispatcher will use as the canonical arg-marshaller
for gate run callbacks (Phase 3c).

Frozen dataclass. No setters. Mutation is via `replace()`-returning helpers.

## Region map

region: imports  lines: 22-26  entry: from __future__ import annotations
region: dataclass  lines: 28-93  entry: @dataclass(frozen=True)
region: helpers  lines: 80-94  entry: def with_iteration

## Function/method index

func: with_iteration  sig: (iteration_index: int) -> IterContext
func: cage_engagement_log_path  sig: (self) -> Path
func: __post_init__  sig: (self) -> None

## Exit list (validation failures + raises)

exit: iteration_index_negative  line: ~91  cause: ValueError when iteration_index < 0
exit: run_id_negative  line: ~93  cause: ValueError when run_id < 0
exit: workspace_dir_not_path  line: ~95  cause: TypeError when workspace_dir is not a pathlib.Path

## Drift policy

This file is registered in `scripts/validate_autoresearch_arch_map.py`
MAP_REGISTRY as label `iter_context`. Edit-then-update discipline:
when you change `iter_context.py`, run `make arch-validate` and fix
any drift before commit.

## Phase progression

- Phase 4a step 1 (this commit): dataclass + tests + arch map.
- Phase 4a step 2 (separate commit): autoresearch_loop populates this
  at top of each iteration; Cage observe-mode block consumes it.
- Phase 3c: Cage gate run callbacks accept IterContext as canonical arg.
- Phase 4b/4c: orchestrator/{telemetry, state}.py extracted, both consume
  IterContext.
