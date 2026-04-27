---
id: GP-157
status: active
summary: GP-101 self-model for src/ztare/orchestrator/state.py (Phase 4c state-flow primitives)
---

# orchestrator/state.py — architectural map

GP-157 v5.0 Phase 4c self-model. Per-run Cage state construction extracted
from autoresearch_loop.py inline `_v5_*` block. Mode resolution + factory
failure handling are now testable in isolation (13 unit tests).

## Purpose

Build the resolved CageRuntime for a run from rubric_data. Three
modes: "off" / "observe" / "authoritative". Factory injection lets
this module remain free of gate-registry imports at module load.

## Region map

region: imports  lines: 19-22  entry: from __future__ import annotations
region: cage_runtime  lines: 25-46  entry: @dataclass(frozen=True)
region: resolve_cage_mode  lines: 49-60  entry: def resolve_cage_mode
region: build_cage_runtime  lines: 63-174  entry: def build_cage_runtime
region: cage_init_banner  lines: 177-194  entry: def cage_init_banner

## Function/method index

func: resolve_cage_mode  sig: (rubric_data: Mapping[str, Any]) -> str
func: build_cage_runtime  sig: (rubric_data, *, cage_factory, cage_available) -> CageRuntime
func: cage_init_banner  sig: (runtime: CageRuntime) -> Optional[str]

## Exit list

(No raises — build_cage_runtime catches factory failures and returns
an inactive CageRuntime so a Cage init failure cannot abort a run.)

## Drift policy

This file is registered in `scripts/validate_autoresearch_arch_map.py`
MAP_REGISTRY as label `state`. Run `make arch-validate` after edits.

## Migration notes

Phase 4c step 1 (this commit): Cage construction extracted.
Phase 4c step 2 (future commits): score history + stagnation tracking,
rubric-evolution state, usage-bucket snapshots — pull these from
autoresearch_loop into matching CageRuntime-style frozen dataclasses
as opportunity arises.
