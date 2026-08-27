# Delta review — ARC worldmodel, 2026-07-17 (two days after the full review)

## P0 status — all 8 FIXED (with tests)

| # | Finding | Status | Evidence |
|---|---|---|---|
| 1 | Holdout-derived probe constants (distinguishing_play) | FIXED | Module rewritten — zero hardcoded/episode_002 constants; `load_targets` (:108) admits only `evidence_role=="visible"` rows with bound `evidence_sha256`; resolution ledger with supersedable `reopened` rows (:60-100) |
| 2 | `within_epoch_view` last-row inference | FIXED | episode_log.py:422-452 — explicit `source_epoch` arg; `None` = full bank; unobserved epoch = EMPTY (never falls back); play-loop callers pass adapter-derived epoch (`_adapter_epoch`, :1302) |
| 3 | candidate_pool bypassing carrier_loader | FIXED | candidate_pool.py:41-48 routes through `lower_carrier_namespace` — PATCH_BASE/PROGRAM restored to committee |
| 4 | StateInterner interned/visited conflation | FIXED | frontier_codec.py:68-166 — separate arena vs `_visited`, `mark_visited`/`visited_matrix`, legacy migration; `_ensure_interners_synced` deleted repo-wide |
| 5 | MANIFEST fail-closed + holdout bridge | FIXED | evidence_consolidation.py:116 raises on unreadable manifest; visible_workbench_cli.py:1120-1125 raises on any holdout-role contrast; deny-by-default outside the allowed set |
| 6 | Router reopened-latch | FIXED | engine_router.py:266-274 imports `distinguishing_play.target_resolution_states` (last-write-wins) — the prescribed reuse |
| 7 | Lean invariant epoch binding | FIXED | lean_bridge.py:40-134 — `current_invariant_binding` verifies `spec_sha256` + `evidence_epoch_sha256`; consumer wired at 3 planner call sites |
| 8 | Global `EXTENSIONS.clear()` | FIXED | carrier_loader.py:296-313 — per-program registry via `bind_extensions`; no `.clear()` anywhere |

Regression tests landed: test_frontier_codec.py, test_planner_refactor.py, test_carrier_loader_identity.py, test_object_roles.py, +465 lines in test_worldmodel_p0.py.

## What else changed

- **Commit d81dfe866 (07-16) executed most of the P2 deletion pass**: k_line.py (−1,082), causal_compiler.py (−462), adapter_width.py (−286), machinery_adoption.py (−107), 3 dead scripts; trace_auditor cut ~1,900 lines. New organs: observation_chart, schema_routes, equivariance, factored_search, task_discharge (clean typed contract), level_boundary_seed (verified boundary-seed replay — closes the "level-2 evidence was actually level-1" class; latest replay verified).
- Uncommitted through 07-17 17:14: +3,361/−815 (arc3_play_loop +859, leaf_workbench +768, planner +494, compiled_fiber_planning +393, goal_abduction +349).
- **Weakness receipts: 151/day → 16/day** (emission dedup now aggregates `occurrence_count`/`first_seen`/`last_seen` — P1 #11 partially done; no human queue for capability-less classes yet).

## Still open / new findings

1. **No new level.** Play report: epoch 2, `levels_completed: 2`, `no_level_in_budget`; factored search exhausting 5,000 states (cap already widened 250→5000); `pursuit.plan` consumes ~99% of live-play leg time (73.0s of 73.3s).
2. **The grammar loop is STILL OFF** (P3 #15 — the review's headline lever): 106 proposals / 0 promotions; `operator_vocabulary_size` dropped 2→1. See file 09: level 3's blocking mechanic is precisely a grammar-ceiling case.
3. p0_metrics still `observer_only`, 0 consumers. tu93 untouched since 07-09.
4. New (minor): `candidate_pool.surviving_committee` (uncommitted :74-96) returns `[]` when fewer than 2 current-exact members remain — a lone current-exact survivor silently discarded; committee depends on candidate_memory freshness with no receipt.
5. `causal_compiler.py` was deleted, but P3 #17 named it the only candidate organ for the `variables` width rung — no successor exists; the adapter-width ladder currently has no candidate.
6. Stale comment: lean_bridge.py:485 claims the `_invariants` consumer "does not exist yet" — it exists at 3 call sites.
7. `_adapter_epoch` falls back `current_epoch → levels_completed → last_transition_identity.target_epoch` — adapter-authoritative, acceptable, but the `levels_completed` proxy is an ARC-shaped assumption in the loop script.

**Net:** the fix marathon worked — all P0s closed, ~4k LOC of inert code deleted, receipt churn down 10x. The apparatus is materially healthier than at the 07-15 review. The remaining stall is not the fixed bugs: see 09 for the level-3 diagnosis.
