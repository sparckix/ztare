---
id: GP-157
status: active
summary: GP-101 self-model for src/ztare/orchestrator/telemetry.py (Phase 4b telemetry primitives)
---

# orchestrator/telemetry.py — architectural map

GP-157 v5.0 Phase 4b self-model. Extracted from autoresearch_loop.py
inline Cage engagement JSONL block. Karpathy "extract what's already
a primitive": JSONL append, engagement record build, console summary.

## Purpose

Single seam for per-iteration telemetry emission. The autoresearch_loop
main loop calls `emit_cage_engagement(ctx, utc=..., engagement_matrix=...)`
which builds a typed `CageEngagementRecord`, JSONL-appends it to
`ctx.cage_engagement_log_path()`, and returns the record. Console
summary printed via `format_cage_observe_summary(record)`.

Schema parity: the JSONL line shape exactly matches the pre-Phase-4b
inline emission, so existing log readers do not need to change.

## Region map

region: imports  lines: 17-23  entry: from __future__ import annotations
region: cage_engagement_record  lines: 26-55  entry: @dataclass(frozen=True)
region: append_jsonl  lines: 58-67  entry: def append_jsonl
region: emit_cage_engagement  lines: 70-99  entry: def emit_cage_engagement
region: format_cage_observe_summary  lines: 102-114  entry: def format_cage_observe_summary

## Function/method index

func: append_jsonl  sig: (path: Path, line: str) -> None
func: emit_cage_engagement  sig: (ctx: IterContext, *, utc: str, engagement_matrix: Any) -> CageEngagementRecord
func: format_cage_observe_summary  sig: (record: CageEngagementRecord) -> str
func: to_jsonl_line  sig: (self) -> str

## Exit list

(No raises — telemetry emission is best-effort. Caller wraps in
try/except. Path errors (e.g. permission denied) bubble naturally;
observed-mode dispatch swallows them with `🦴 v5 Cage observe-mode
dispatch error (non-fatal)`.)

## Drift policy

This file is registered in `scripts/validate_autoresearch_arch_map.py`
MAP_REGISTRY as label `telemetry`. Run `make arch-validate` after
edits.
