# Review — leaf workbench / retry surface / carrier contracts

Cluster: `leaf_workbench.py` (+3,355 uncommitted), `retry_surface.py` (+637), `patch_base_carrier.py` (+368), `patch_carrier_contract.py`, `common/leaf_workbench_contract.py`, `leaf_workbench_executor.py`, `visible_workbench_actions.py`, `visible_workbench_cli.py`, `briefing_pack.py`.
Scope: ~7,480 diff lines across 10 files (13,937 LOC total in target modules), traced end-to-end into `pre_judge_gate.py`, `patch_base_identity.py`, `artifact_refs.py`, `evidence_quotients.py`.

## Enforcement questions — resolved

- **Capability-scope IS enforced at both doors.** Parent executor: `leaf_workbench_executor.py:386` (`active_workbench_task_scope_error` in `leaf_workbench_action_request_retry_message`), the single door every auto-selected morphism routes through (`_execute_boundary_morphism_once` → same function). CLI: `visible_workbench_cli.py` `_probe_json`, `_route_action`, `_run_action` all call `_active_task_scope_error`. No bypass path found.
- **The "cache keyed on incomplete identity" defect is RESOLVED.** Gate cache key (`pre_judge_gate.py:264`) now binds `evidence_epoch_sha256` + `candidate_dependencies` (full PATCH_BASE closure bytes) + rubric + evaluator identity; old mtime fingerprint gone (`_episode_mtime_fingerprint` now a content alias, line 208). New receipt-family cache (`_task_bound_kernel_receipt`) re-verifies consumed artifact bytes via `_input_artifact_bindings_are_current` + `handler_implementation_sha256` before reuse. `verify_patch_base_digest` unchanged and sound; legacy-prefix matching confined to nested ancestors. No digest bypass introduced.

## Correctness findings

**F1 — Dead authority-bridge entries.** `visible_workbench_cli.py:31` `_AUTHORITY_DERIVED_ACTIONS` lists 5 caps, but `inspect_worldmodel_counterexample_context`, `mine_worldmodel_separating_features`, `mine_worldmodel_lowerable_selectors` were removed from `local_cli_actions` this diff (`leaf_workbench.py:492`). `_run_action` raises "not registered for visible local execution" at `visible_workbench_cli.py:1061` before the authority branch can fire → the `_derived_action_evidence_refs` branch for `inspect_worldmodel_counterexample_context` (`visible_workbench_cli.py:1174`) is unreachable. Delete the 3 stale entries.

**F2 — Holdout census reachable through the contrast bridge (trust-boundary dependency).** `contrast_worldmodel_episodes` (`leaf_workbench.py:784`) defaults `episode_ref_b="holdout"`; `episode_contrast` (`evidence_quotients.py:121`) returns the holdout's color census, census delta, differing-row indices, shape. The authority bridge is the only path to real holdout bytes — gated solely on the manifest marking episode_002 `visible_status=="visible"` OR `status=="withheld"/reason=="too_large"` (`_manifest_visible_evidence_refs`, `visible_workbench_cli.py:542`). A manifest mislabeling the holdout "too_large" hands the leaf a bounded but real visible-vs-holdout diff. Medium severity (no raw cells), but exposure is decided by a single mutable manifest field, not a hard holdout gate.

**F3 — Point-fix treadmill on `dynamics_assumption`, strict-mode reversal on the error path.** `patch_base_carrier.py:209` `_validate_patch_base_contract` re-reads `rubrics/<project>.json` inline to recover `dynamics_assumption` — the comment admits this is the "third site of this contract drift after the loader and the transfer probe." The `except Exception: dynamics_assumption = None` fallback reverts to the strict contract, which the same comment says "wrongly rejects" a lawful_time champion. A transient rubric read failure makes a valid compiled PATCH_BASE carrier fail to load — re-introducing, on the error path, exactly the bug being patched. Root cause: `dynamics_assumption` resolved three times from raw JSON instead of threaded once from a resolved config.

**F4 — Scope-close check fails open (forcing risk).** `active_workbench_task_capability_scope` (`leaf_workbench_executor.py:198-213`) wraps `task_identity_status_fn` in blanket `except Exception: pass` and keeps the task active. That function is the lifecycle-close signal; any raise inside `worldmodel_workbench_task_identity_status` leaves a promoted/consumed task still forcing evidence actions on the leaf. Not unsound (gates still real), but burns turns on a stale task — the "forcing = authority collapse" failure mode. Fail closed (or log) on the close check.

No bugs found in receipt-family resumption, the route-production admission door (`_admit_task_bound_route_production` requires task-id match + in-scope cap + existing parent receipt), or the digest chain.

## What the 3,355 new lines actually are

- **~1,750 (52%) genuinely new diagnostic capability**, dominated by two mega-functions: `_catalog_residual_event_candidates` (536 lines, line 4943) and `_mine_task_operation_domain_selector` (477 lines, line 2716), plus `_observed_behavioral_fiber`, `_observed_commuting_catalog_transports`, `_patch_base_chain_effects`, `_active_frontier_observation_triple`. New science (observation triples, operation identities, behavioral fibers, chain effects).
- **~900 (27%) defensive scaffolding / identity plumbing**: `worldmodel_workbench_task_identity_status`, `_task_bound_upstream_receipts`, payload normalization, epoch/sha guards.
- **~700 (21%) prompt/record surfacing**: `_render_active_task_first_fire_fragment`, first-fire record projection, compaction helpers.

**Verdict: leaf_workbench.py is doing the kernel's job.** The ~1,000 lines in the two mega-functions are grid-level spec-abduction orchestration (connected-component completion, state-machine compression, boundary-recurrence evidence) kept in the adapter. Per the repo's own "adapter = routing/surfacing, kernel does the science" invariant, this belongs in a worldmodel analysis module. Very little of the growth is compensation for defects elsewhere (F3 is the main such case).

## Prompt / briefing surface

- Good: `format_worldmodel_retry_skeleton` fully removed the `mine_worldmodel_separating_features` branch and its duplicated `current_requests_feature_miner` block; scope-narrowed manifest filters routes to the active task.
- Duplicated policy: the "failed morphism / exhausted selector refutes only that family, don't escalate to LOWERABILITY_BLOCKED" message appears with near-identical wording in `science_output_policy.py:121`, `leaf_workbench_executor.py` (WORKBENCH_OBSERVATION_YIELD_EXHAUSTED), and `retry_surface.py` `carrier_guidance_section`. One source of truth needed.
- Stale removal done right: `strategy_gate_command_wrapper` doc block deleted from `briefing_pack.py` alongside `_PARENT_KERNEL_ROUTES` removal.

## Dead code / unwired handlers

- `mine_worldmodel_separating_features` semi-orphaned: still registered handler + stateless action + "available on request" record row (`leaf_workbench.py:1696`), but removed from `local_cli_actions` and every auto-selection path. Receipts ledger confirms cold (31 historical, all pre-change; `inspect_worldmodel_counterexample_context` at 62 is the live replacement). Keep handler; drop from `_AUTHORITY_DERIVED_ACTIONS`.
- `inspect_worldmodel_patch_base` (1 receipt) has no matching handler in the registry — legacy.

## Top 3 structural remediations

1. **Move the two mega-functions out of the adapter** into `worldmodel/residual_event_analysis.py` next to `spec_abduction` (with helpers `_observed_behavioral_fiber`, `_observed_commuting_catalog_transports`, `_patch_base_chain_effects`, `_catalog_operation_fibers`); leaf_workbench calls one entrypoint. Cuts ~1,300 lines from the adapter, restores the kernel/adapter boundary.
2. **Resolve `dynamics_assumption` once and thread it** (delete two of the three read sites; kill the inline rubric re-read + strict fallback in `_validate_patch_base_contract`).
3. **Delete the 3 dead `_AUTHORITY_DERIVED_ACTIONS` entries and add a hard holdout-non-bridgeable guard**: the bridge refuses any ref canonicalizing to the holdout episode regardless of manifest size marking.
