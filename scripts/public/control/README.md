# scripts/public/control/

> **Up:** [scripts/](../../README.md) · **Subdir:** [substrate_management/](substrate_management/README.md) · **Siblings:** [lean/](../lean/README.md) · [mining/](../mining/README.md) · [validators/](../validators/README.md)

The control plane and the largest scripts tree: agent dispatch,
org-runtime CLIs, discipline linters, the tick lifecycle, forecast-pool
control, and the GP-225 / Route-C / gp235 experiment pipelines. Treat
anything named `route_c`, `rung`, `pin_delta`, `gap_ledger`, `v32`,
`v33`, or `gp235` as active research tooling, not dead code; several
files are recent in-flight work and must not be archived on a name-grep
miss.

## Agent and org runtime

| Script | What it does |
|---|---|
| `agent_daemon.py` | GP-128 Level-2 persistent autonomous agent: the sleepless tick loop, runs on a VPS or locally. |
| `agent_channel.py` | Small CLI for the local persistent-agent channel (devops/debug surface, not the product UI). |
| `closure_daemon.py` | GP-168 exogenous-pressure enforcer: stateless poller over the OKR tree. |
| `external_run_monitor.py` | Project-agnostic watchdog for external GPU/API runs (watches a PID file + result file). |
| `poll_telegram.py` | Optional tenant Telegram inbound poller; public runtime does not require it. |
| `telegram_setup.py` | Optional tenant Telegram setup wizard; filesystem gates are the public default. |
| `org_first_run_setup.py` | Low-friction first-run check for the ZTARE org runtime. |
| `org_inbox_status.py` | Summarize the three local inboxes without mutating state. |
| `org_role_preflight.py` | Non-mutating preflight that a role daemon can boot against the durable contracts. |
| `org_runtime_smoke.py` | One-command smoke test of the local org runtime (verifies, does not execute work). |
| `runtime_smoke_test.py` | Runnable end-to-end exercise of the five org-runtime elements. |
| `forked_org_smoke.py` | Fresh-fork smoke test of the org kernel (RD-1.12 detection in a tempdir). |
| `check_org_independence.py` | CI lint: `org/` source must not import ZTARE-specific modules. |
| `export_a2a_agent_cards.py` | Export local A2A-style agent cards for the persistent role offices. |

## Tick lifecycle and close-out gates

| Script | What it does |
|---|---|
| `post_tick_check.py` | The RD close-out gate (post-tick counterpart of `rd_tick_brief`); referenced by AGENTS.md. |
| `tick_close.py` | Fail-closed interactive tick-close wrapper for the artisanal (non-daemon) path. |
| `tier_scoreboard.py` | Tier-tagged, never-merged scoreboard + gate eval (thin composition, allowed under the freeze). |
| `rd_tick_brief.py` | Kernel-tick pre-tick surfacing for Research Director discipline. |
| `rd_tick_gnn_precheck.py` | Frozen-artifact GNN advisory precheck: keep the lemma-ranker lane visible at ticks. |
| `primitive_tick_surface.py` | Render the RD tick-start primitive-discoverability surface. |
| `prediction_logging_discriminator.py` | CLI for PATTERN-012 prediction-ledger logging decisions. |
| `assert_codex_bet.py` | Back-compatible forcing guard for the kernel ordering rule "never resolve a micro contract before an independent forecaster warm-wake is consumed". |

## Discipline linters and pre-flight

| Script | What it does |
|---|---|
| `closure_claim_discipline_linter.py` | Tier-1 deterministic discipline linter for closure-claim artifacts. |
| `closure_claim_discipline_linter_tier2.py` | Tier-2 LLM semantic check (companion to the deterministic Tier-1). |
| `closure_claim_discipline_linter_tier3.py` | Tier-3 multi-LLM cross-validation of the same artifact. |
| `predispatch_check.py` | Mechanical pre-dispatch discipline gate (operator catch 2026-05-09). |
| `proof_source_integrity_lint.py` | Advisory proof-source integrity lint for a bundle `proofs.json` (apparatus risks R1-R4). |
| `scientific_amnesia_precheck.py` | Generic scientific-amnesia history-overlap precheck (run before any new tick). |
| `formalization_sequence_classifier.py` | Run the formalization-sequencing precheck. |
| `preflight_charter_patches.py` | GP-226 charter-patch pre-iter-1 confirmation hook (a `make loop` prerequisite). |
| `charter_commit.py` | GP-226: apply an advisory-mode charter-critic patch candidate. |
| `restore_baseline_test_model.py` | Restore a project's `test_model.py` to an iter-0 placeholder (detects substrate type). |
| `safe_lean_runner.py` | Operator-mandated resource-limited Lean test runner (use instead of ad-hoc parallel bash). |

## Forecast pool and calibration

| Script | What it does |
|---|---|
| `forecast_pool.py` | The sealed forecast-pool primitive for macro/meso/micro routing. |
| `p0_calibration.py` | Emit the one stable GP-236 calibration block (composes existing forecast-pool outputs). |
| `pattern_026_calibration_audit.py` | Tertiary calibration test for PATTERN-026 (primitive-before-architecture gate). |

## GP-225 / LeanMill Harnesses

| Script | What it does |
|---|---|
| `bundle_run.py` | The single runnable entrypoint for the bundled Proof Execution plus Governance Gate Lean-closure harness. |
| `bundle_verify.py` | The reusable Proof Execution verifier, productized from the disposable per-corpus `/tmp/run_*` scripts. |
| `gp225_audit.py` | The productized Governance Gate harness interface. |
| `leanmill_24x7_runner.py` | Safe LeanMill station runner: refreshes deterministic state, seeds queue work, drains bounded workers, and writes the 24x7 status receipt. |
| `leanmill_work_queue.py` | SQLite WorkItem queue plus append-only event ledger used by the LeanMill station workers. |
| `leanmill_observability.py` | Central LeanMill observability report over queue status, event tail, source-search quality, source-binding rejections, LLM spend/fallbacks, and bottleneck classes. |
| `leanmill_operator_contracts.py` | Compact checked operator-contract helpers for LeanMill worker lanes; C-supply template backfill uses this to carry source-cue checks, action-program order, and terminal-attempt rules into warm agents. |
| `leanmill_learning_feedback_contract.py` | Compatibility shim for canonical learning-feedback contracts under `src/ztare/leanmill/contracts/learning_feedback.py`; normalizes learning exits, malformed negative-control detection, and bounded non-credit feedback entries. |
| `leanmill_dead_letter_triage.py` | Bounded operational triage for retryable dead-lettered WorkItems; currently requeues only proposal-validation items with explicit retry budget. |
| `leanmill_retryable_failure_recovery.py` | Requeues failed proposal/decomposition WorkItems after recoverable control-plane defects such as parser or artifact-path failures are fixed. |
| `leanmill_learning_work_seeder.py` | Turns station/source/registry state into bounded WorkItems with credit boundaries and negative-control expectations. |
| `leanmill_corpus_expansion_from_files.py` | Deterministically turns existing Lean target files into active corpus rows so inactive row leads can be resolved before any source-bound probe. |
| `leanmill_source_search_worker.py` | Executes theorem-shaped source-search tasks and static qualification; emits source inventory only. |
| `leanmill_source_search_integrator.py` | Converts successful source-search inventory into bounded source-to-canary binding tasks for agent/LLM follow-up. |
| `leanmill_source_binding_ingester.py` | Converts completed source-to-canary binding artifacts into guarded probe WorkItems with matched negative controls. |
| `leanmill_agent_repair_worker.py` | Subscription-backed Codex/Claude worker for scoped stateful repair, sibling, heldout, and source-binding tasks. |
| `leanmill_llm_proposal_worker.py` | API-backed proposal worker for bounded JSON source, repair-template, decomposition, exact-gap, and falsifier proposals. Optional Codex CLI fallback is read-only and still passes the same schema/source-query gates. |
| `leanmill_agent_output_ingester.py` | Converts completed subscription-agent outputs into direct source-search work when they emit valid source-request JSON, otherwise into bounded API-LLM review jobs. |
| `leanmill_probe_worker.py` | Queue wrapper for bounded heavy-Lean proof probes; requires explicit heavy-Lean authorization. |
| `leanmill_post_probe_triage.py` | Converts terminal proof probes into the next bounded repair, exact-gap/decomposition, hold, retirement, or safety task; zero-score probes now carry typed no-positive learning contracts plus anti-template replay signatures, including ex-post backfill for previously triaged no-signal probes. |
| `leanmill_governance_worker.py` | Governance worker for ratification/rejection/exact-gap/falsifier control receipts. |
| `leanmill_andon_cord.py` | Applies bounded containment decisions from factory health signals; pauses or redirects work without granting proof credit. |
| `leanmill_backlog_replenisher.py` | Refills proof-value probe and repair queues from current registry/source state under cooldown and retry limits. |
| `leanmill_benchmark_prep.py` | Builds preregistered benchmark packets and checks contract/readiness metadata before harness execution. |
| `leanmill_benchmark_slice_analyzer.py` | Produces paired-row, family-eligible, family-invoked, and attempt-quality breakdowns for benchmark interpretation. |
| `leanmill_c_discriminating_slice_prep.py` | Gated selector for C-discriminating rows: static-tool no-positive signal, matching family templates, negative controls, and executable target evidence. |
| `leanmill_c_slice_freezer.py` | Freezes a C-discriminating slice after predeclared qualification so benchmark rows cannot drift after seeing C results. |
| `leanmill_c_supply_batch.py` | Static-only miner over family corpora/source-demand rows; qualifies potential C-supply without running Path C. |
| `leanmill_c_supply_demand_corpus_builder.py` | Builds demand-specific corpora for families that need more static-fail sibling rows. |
| `leanmill_c_supply_expost_cleaner.py` | Ex-post hygiene pass that compacts duplicate C-supply checkpoints and makes static-result conflicts explicit. |
| `leanmill_c_supply_template_backfill.py` | Bounded template-conversion planner for strict static-fail C-supply rows; enforces row top-family agreement before enqueue. |
| `leanmill_c_supply_upstream_rater.py` | Observe/advisory upstream routing forecaster for C-supply family corpora; GPT-5.4-mini predictions are calibration artifacts for spend routing, not proof credit. |
| `leanmill_c_supply_growth_controller.py` | Closed-loop C-supply growth controller: template backfill, governed static controls, family-spec probes, and strict slice re-scoring without granting proof credit. |
| `leanmill_c_static_sweep_backfill.py` | Completes missing governed-static control-arm records for C-slice candidates before any benchmark credit; heavy Lean requires explicit authorization. |
| `leanmill_canary_validator_worker.py` | Validates canary packets and template substance before downstream probe/governance work consumes them. |
| `leanmill_de_experiment_contract.py` | Pre-registration contract helper for discriminating LeanMill experiments. |
| `leanmill_enqueue_ns_lemma.py` | Validates and enqueues a bounded NS-corpus work item through the existing LeanMill queue and agent-repair contract. |
| `leanmill_evaluation_harness_runner.py` | Runs pre-registered LeanMill benchmark arms with checkpoint/resume and governance/readiness enforcement. |
| `leanmill_external_source_scout_seeder.py` | Seeds external source-scout work for source-starved families under policy floors and runtime routing. |
| `leanmill_external_source_search_recovery.py` | Recovers source-search work that was blocked by transient external-source failures. |
| `leanmill_factory_config.py` | Compatibility shim for the canonical LeanMill policy module under `src/ztare/leanmill/policy.py`. |
| `leanmill_factory_intelligence.py` | Converts queue, event, scoreboard, source, and C-supply state into actionable bottleneck recommendations. |
| `leanmill_family_birth_miner.py` | Dormant ex-post miner for missed multi-row repair-family candidates; default is plan-only/no enqueue/no proof credit. |
| `leanmill_family_spec_gate.py` | Validates repair-family YAML structure, template evidence, and control expectations before use. |
| `leanmill_family_specs.py` | Shared parser/index helpers for repair-family specs and template inventories. |
| `leanmill_gm_operator_lane.py` | Bounded no-credit operator/GM review lane for heldout and source decisions that should not block queues silently. |
| `leanmill_governance_sentinel_suite.py` | Sentinel tests for governance behavior, including negative controls and false-positive guardrails. |
| `leanmill_handoff_integrity_gate.py` | Checks queue/artifact handoff points for stale, missing, or malformed cross-worker state. |
| `leanmill_heldout_independence_scout.py` | Finds heldout sibling rows for repair-family validation without using final benchmark rows as design feedback. |
| `leanmill_heldout_promotion_worker.py` | Promotes repair families only after heldout evidence and negative-control receipts satisfy policy. |
| `leanmill_heldout_receipt_gate.py` | Defense-in-depth receipt checker for heldout evidence attached to family promotion. |
| `leanmill_infra_freeze_gate.py` | Fails fast on recent infrastructure defect classes before restart/benchmark credit. |
| `leanmill_llm_critic.py` | Structured critic over LeanMill artifacts using the versioned critic axes file. |
| `leanmill_llm_proposal_gate.py` | Schema/source-query gate for API or fallback LLM proposals before they enter bounded work lanes. |
| `leanmill_paths.py` | Compatibility shim for canonical LeanMill paths under `src/ztare/leanmill/paths.py`. |
| `leanmill_population_elo.py` | Experimental population/Elo-style ranking helper for APN-lite-style sketch/proposal comparison. |
| `leanmill_recover_pruned_source_requests.py` | Reopens source requests pruned by older policy when current policy says they are recoverable. |
| `leanmill_registry_converger.py` | Reconciles registry/materialized state so family status, templates, and receipts agree. |
| `leanmill_registry_worker.py` | Queue worker for repair-registry refresh/convergence tasks. |
| `leanmill_regression_gate.py` | Regression guard over LeanMill control-plane invariants and representative self-tests. |
| `leanmill_residual_lifecycle.py` | Classifies residuals from probe/governance/source lanes into next repair, retirement, or family-candidate states. |
| `leanmill_restart_gate.py` | Restart preflight: requires explicit shutdown-marker clearing and enough candidate diversity before scaled restart. |
| `leanmill_runtime_router.py` | Policy and heartbeat-aware subscription runtime router; supports Codex-only or balanced routing without per-task ad hoc choices. |
| `leanmill_shutdown.py` | Graceful LeanMill stop path: writes shutdown marker, reclaims leases, and cleans orphan REPL processes under policy. |
| `leanmill_source_family_allocator.py` | Allocates source candidates to repair families while preserving credit boundaries and avoiding duplicate work. |
| `leanmill_source_inventory.py` | Source-candidate inventory builder/query helper; inventory has no proof credit until canary/governance lanes consume it. |
| `leanmill_source_plan_worker.py` | Refreshes residual-to-source search plans from registry and source inventory state. |
| `leanmill_source_quality_feedback.py` | Scores source-search/source-binding outcomes and feeds policy-level supply quality recommendations. |
| `leanmill_source_query_contract.py` | Compatibility shim for canonical source-query contracts under `src/ztare/leanmill/contracts/source_query.py`. |
| `leanmill_source_worker.py` | Legacy/source-specific worker surface kept for compatibility with older LeanMill work items. |
| `leanmill_static_failure_miner.py` | Static-tool sweep/miner that identifies rows public tools fail, before Path C is allowed into the evaluation loop. |
| `leanmill_station_action_contract.py` | Action-contract primitive for station self-correction: maps intelligence recommendations to bounded runner actions. |
| `leanmill_station_health_dashboard.py` | Station-level health dashboard over worker heartbeats, version drift, queue health, and learning-unit flow. |
| `leanmill_station_scheduler.py` | Schedules station refresh/probe/source/governance work from policy and current queue state. |
| `leanmill_vnext_coverage_gate.py` | Coverage/self-test gate for LeanMill vNext control-plane surfaces. |
| `leanmill_watchdog.py` | Tmux watchdog for local/VPS LeanMill daemons; restarts bounded sessions, refreshes intelligence, and honors shutdown markers. |
| `gp230_solve.py` | GP-230 / Route-C solver harness CLI (Day-7 operator deliverable). |
| `route_c_archetype_runner.py` | GP-230 Layer-4 archetype-catalog 5-mode ablation harness over Carleson sandbox rows. |
| `route_c_layer_2c_dispatch.py` | Route-C Layer-2c LLM dispatch with semantic masking (GP-235-aligned wiring). |
| `analyze_ablation_results.py` | Report on a `route_c_archetype_runner` JSON trace (per-mode closure breakdown). |
| `rung1_kernel_grounded_rerank.py` | Rung-1 kernel-grounded candidate-action rerank: the cheapest falsifier of the Path-A thesis (no training, no GNN). |
| `build_pin_delta_corpus.py` | Corrected pin-delta OOD corpus builder (bucketed `rung1_corpus.json`). |
| `exact_gap_ledger.py` | The exact-gap / falsifier ledger: every non-closure row must resolve to a concrete next lever. |
| `escape_route_run.py` | The paid discriminating run (PL-156): the wired Route-C Layer-2c generator. |
| `escape_route_screen.py` | Deterministic v4.29.0 rigor gate for the escape-route ablation. |
| `known_possible_run.py` | Solver-0 corpus fix (PL-367): adds known-possible rows to the genuinely-open corpus. |
| `solver0_gate.py` | The minimal solver-0 measurement (GPT-5.5 reframe), not a new benchmark seed. |
| `residual_to_lever.py` | The verification-to-solving bridge: implements the consumer-feedback contract. |
| `surgical_swarm_panel.py` | Bounded multi-job typed-endpoint swarm panel (thin layer over `batched_candidate_generator`). |
| `dispatch_external_prover.py` | PATTERN-014 independent-CAS-verification deployer over the OpenAI API (the cold cross-provider pass). |
| `archetype_classifier.py` | Predict the L4 Lean tactic archetype + L2 op + L3 flags from the archetype catalog. |
| `test_archetype_classifier_accuracy.py` | Measure `archetype_classifier.py` precision on the v3 ground-truth catalog. |
| `proof_route_fingerprint.py` | Surface proof-route fingerprint extractor (GP-235 §4 primitive validation step 1). |
| `proof_route_fingerprint_v2.py` | Augmented fingerprint with signature features (surface-only could not pass §4.2). |
| `proof_route_fingerprint_v3_kernel.py` | v3 fingerprint with kernel features from v28B artifacts (anti-amnesia reuse). |

## gp235 §4 series and v3x corpus / leakage gates

| Script | What it does |
|---|---|
| `gp235_section_4_1_intra_cluster.py` | §4.1 intra-cluster distance test on the 30-pair train set. |
| `gp235_section_4_2_inter_cluster.py` | §4.2 inter-cluster distance test on the 50-pair structurally-distinct test set. |
| `gp235_section_4_5_weight_grid_search.py` | §4.5 ablation-dominance prep: grid search over the fingerprint axis weights. |
| `gp235_section_4_v2_full.py` | §4 with the v2 fingerprint + v2 train set. |
| `gp235_section_4_v33.py` | §4 with the pre-registered relaxed threshold + joint tune. |
| `gp235_section_4_v33_kfold.py` | 5-fold CV for honest §4 generalization (single-split tune-to-held was fragile). |
| `gp235_section_4_v34_kernel_kfold.py` | v34: adds a kernel-embedding axis + 5-fold CV (v28B node2vec). |
| `gp235_section_4_v35_kernel_full_data.py` | v35: kernel + proof-body-snippet fallback (anti-amnesia: test set carries the snippet). |
| `v31_gap_report_generator.py` | Layer-5 gap reports on open Lean sorries (Path-C deliverable). |
| `v32_corpus_real_content_retest.py` | Fair re-test of the deterministic L2 classifier on real content. |
| `v32_import_curated_rows.py` | Anti-amnesia: import pre-vetted rows from the v2.1+ harness instead of inventing new ones. |
| `v32_llm_l2_classifier.py` | GPT-5.5 as L2 classifier (the deterministic keyword L2 genuinely fails 0/18). |
| `v32_meta_pattern_miner.py` | The meta-solver substrate test: does the 3-catalog meta-pattern substrate have signal. |
| `v32_rich_corpus_l2_test.py` | Corrected substrate test on rich multi-step proofs (elementary one-liners gave degenerate labels). |
| `v32_rich_corpus_miner.py` | Run the meta-pattern miner on the corrected rich corpus. |
| `v32_route_c_replay_batch.py` | Strict replay of curated proven-Mathlib rows through Route C. |
| `v33_corpus_vacuity_relabel.py` | Leakage-independent re-labeling of the NS corpus via the validated vacuity organ. |
| `v33_currency_mismatch_gate.py` | Fifth forward gate: catches the NS scalar-wrapper currency-mismatch class. |
| `v33_indirect_leakage_gate.py` | Fourth forward gate: leakage-independent simp/fun_prop indirect-leakage organ. |
| `v33_leakage_safe_miner.py` | Tick-2 variance gate + Tick-3 leakage-safe miner over the re-audited corpus. |
| `v33_paraphrase_gate.py` | Second forward gate: gold-name-verbatim / paraphrase organ. |
| `v33_preflight_risk_detector.py` | The governance harness's missing organ: catches tick541/carleman vacuity before, not after. |
| `v33_single_lemma_exact_gate.py` | Third forward gate: leakage-independent single-lemma-exact organ (the v26/v27 subsumption class). |
| `gp233_adversary_yield_decomp.py` | GP-233 scientific-yield decomposition of the non-gamed adversary-corpus run. |
| `ns_governance_gate.py` | v36 NS governance integration: forces every live NS attempt through the v35 forward-evidence schema. |

## Index / catalog / query helpers

| Script | What it does |
|---|---|
| `build_gp_index.py` | GP-XXX index builder (Linus MAINTAINERS-style auto-generated index). |
| `query_graph.py` | GP-216d/f Director graph-query helper: traversal queries over the knowledge graph (replaces grep). |
| `render_architecture_index.py` | Render `architecture_index.jsonl` into the discoverability meta-graph `INDEX.md`. |
| `render_structural_language_catalog.py` | Render the RD structural-language registries into a human-readable catalog. |
| `export_structural_language_catalog.py` | Export GP-216/GP-219 structural language as machine-readable JSON. |
| `classify_substrate.py` | Pre-launch substrate fingerprint + recommended-flags generator (built after gp163d). |
| `catch_graph_edge_advisory.py` | Conservative leakage-free advisory deriving the `surfaced_catch` graph edge from the catch ledger. |
| `remediate_catch_ledger.py` | Integrity-preserving remediation of the catch ledger (SOX §1220: never null a concurring agent). |
| `register_external_gpu_run.py` | Register an external GPU/API run in the kernel run registry (shared with [utilities/gpu/](../utilities/gpu/README.md)). |
| `probe_matrix.py` | Cold-review Step 1a: generate a verified per-row probe matrix using only verified primitives (no brittle live orchestration). |
| `offline_policy_replay.py` | Cold-review Step 1b: pure-Python zero-Lean rerunnable-for-free cost-accounted policy replay over a verified probe matrix. |

## Related

- Substrate freeze/reset before cross-family runs: [substrate_management/](substrate_management/README.md)
- The discipline these gates enforce: [epistemic principles](../../../docs/concepts/epistemic_principles.md), [anti-pattern catalog](../../../docs/concepts/anti_pattern_catalog.md)
- Org runtime concepts: [organizational primitives](../../../docs/concepts/organizational_primitives.md)

## Forecasting / calibration DB tooling (added 2026-05-29)

Wired into `ztare forecast <verb>` (see `src/ztare/cli.py:140`).

| Script | Verb | What it does |
|---|---|---|
| `forecast_ingest_smoke_jsonl.py` | `ztare forecast ingest-smoke` | Ingest the 5 forecast-smoke JSONL ledgers (novel_bias_smokes_n30, novel_bias_smokes_n42_diversified, freq_inheritance_smoke_n15, freq_inheritance_DI_panel_smoke_n15, pilot_v28timedecay) into `pilot_calls` with the standard schema. Use `--dry-run` then `--commit`. |
| `forecast_compute_elo_by_corpus.py` | `ztare forecast elo-refresh` | Recompute per-(family, corpus_class) Elo from head-to-head per-contract Brier and populate the `family_elo_by_corpus_class` table. K=16, init=1500, takes best (lowest) Brier per (family, contract) when a family fired the same contract across multiple pilots. |
| `forecast_brier_elo_report.py` | `ztare forecast brier-elo` | Print the roll-up table from `v_family_brier_by_corpus_class` JOINed with `family_elo_by_corpus_class`. `--by-subsource` adds the Polymarket / Manifold / Metaculus / FRED / yfinance drill-down via `v_family_brier_by_subsource`. `--corpus-class internal|external|all` filters. |
| `leanmill/llm_critic.py` | (relocated) | LLM critic for leanmill (was at `analytics/public/gnn/lemma_relevance/leanmill_llm_critic.py` pre-restructure; this is a script and now lives in `scripts/public/control/leanmill/`). |
