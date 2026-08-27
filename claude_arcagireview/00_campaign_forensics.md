# ARC-AGI apparatus review — campaign forensics (evidence lane)

Reviewer: Claude (conductor lane). Date: 2026-07-15/16.
Scope: repo-level scale metrics, live workspace receipts, phase timings, adapter width, tu93 status.
All numbers measured directly from the working tree and `projects/arc3_ls20_gov/workspace/` — not from docs.

## Apparatus scale

| Layer | LOC |
|---|---|
| src/ztare/worldmodel | 39,799 |
| src/ztare/common | 33,715 |
| src/ztare/orchestrator | 35,999 |
| src/ztare/validator | 36,993 |
| src/ztare/research_director | 34,445 |
| **Total (5 layers)** | **~181k** |

- 4-day fix window (uncommitted working tree): **~50k insertions / 9.1k deletions across 358 files**.
- worldmodel share: +7,048 / −1,524 across 32 files; `leaf_workbench.py` alone **+3,355 lines**.
- 23 new untracked src files, incl. 5 new common contracts (`equivariance.py`, `factored_search.py`, `observation_chart.py`, `schema_routes.py`, `task_discharge.py`).
- Test coverage: only ~7 worldmodel/ARC test files (`test_worldmodel_p0.py`, `test_worldmodel_p0_metrics.py`, `test_worldmodel_patch_base_carrier.py`, `test_factored_search.py`, `test_arc_lean_feedback.py`, …) against ~40k lines of worldmodel + new common contracts.

## Harness-weakness receipt stream (the iatrogenics instrument)

`harness_weakness_receipts.jsonl`: **483 rows, 1.7 MB**, still firing hours before this review.

By class:

| weakness_class | count |
|---|---|
| unquotiented_counterexample_chart_missing | 230 |
| local_receipt_overgeneralized | 96 |
| unclassifiable_carrier_or_gate_failure | 73 |
| quotient_context_missing | 29 |
| visible_counterexample_trace_unfactored | 26 |
| failing_gate_without_witness | 7 |
| candidate_quality_failure | 6 |
| registered_capability_delivery_failure | 5 |
| plateau_without_information_gain | 5 |
| declared_gate_obligation_open | 4 |
| boundary_evidence_missing | 2 |

By day: 07-08: 138 · 07-09: 7 · 07-10: 3 · 07-11: 8 · 07-12: 15 · 07-13: 115 · 07-14: 36 · **07-15: 151** · 07-16: 10.

**327 of 483 receipts landed during the 4-day fix window.** The instrument is still screaming after the fixes.

## Time economics (phase_timings.jsonl)

| phase | count | total hours |
|---|---|---|
| governed_loop | 57 | 12.59 |
| sprint.multilife | 2 | 2.98 |
| live_play | 56 | 1.20 |
| sprint | 21 | 1.07 |
| pursuit.plan | 186 | 1.01 |
| sprint.identification | 24 | 0.93 |
| reseal | 52 | 0.82 |
| system1_candidate_gate | 52 | 0.72 |
| agent_dispatch | 87 | 0.50 |

≈ **10:1 machinery-to-environment ratio** (12.6h governed_loop vs 1.2h live_play).

## Science outcomes (real but narrow)

- ls20: carrier `dcea1a97…` exact on **14,707/14,707** law-scored rows (383 env frames excluded), **16/16** withheld rollout. Two adapter-attested task discharges (level completions). Current play report: `no_level_in_budget`.
- Two consecutive in-loop operation acquisitions without a conductor-authored law (`b5abed8c…`, `83e6ea51…`) — the transaction has first-fired.
- tu93 (transfer game): completed level 1 in 18 steps, `goal_reached` — but with `terminal_verifier_model_mismatch: true` and `reward_model_mismatch: true` (won while the transition model was still wrong).

## Generality by the repo's own metrics

- **Adapter width: 7/7** — zero human-supplied givens graduated. One field (`variables`) has status `abduced_candidate` (causal_compiler v1) but no validator and no downstream consumer.
- p0_metrics: `observer_only`, `decision_consumer_count: 0`; catalog_growth_velocity / operator_reusability_index / hypothesis-split **not_computable** (no denominators / no paired epochs).
- Kernel pressure (cumulative): **r1_failures: 718**, tool_action_requests: 430, pre_judge_failures: 0.
- Compression: catalog_proposals **106 → catalog_promotions 0**; operator_vocabulary_size **2**.
- `closure_boundaries.status: not_terminal_closed`, `autonomous_completion_proven: false` (`missing_explicit_unassisted_terminal_provenance`).

## Other campaign evidence

- `AGENT_CORRECTIONS.md` (2026-07-11): `win_attempt_evidence.jsonl` — **2,843 rows all level-1** while intended as level-2 evidence; root cause `adapter.reset()` restarting at level 1. Another instance of the apparatus corrupting its own evidence.
- Seam doc (GP-250) records the recurring pattern from day one: sealing shipped unsealed (worker read holdout via 8 tool calls); judge read-only flag dead code; `EpisodeLog.append` mis-stamped `t` from episode 2 onward (made step-dependent laws unrecoverable from their own evidence); exec split-namespace zeroed an entire sealed run; holdout gate unpassable-by-construction for a week (every candidate scored exactly 4 or 0); feedback chain with three dead links (computed-but-never-persisted, stale-passed-as-current, dropped-at-render); workbench cache stale-singleton (identity omitted consumed evidence bytes).
