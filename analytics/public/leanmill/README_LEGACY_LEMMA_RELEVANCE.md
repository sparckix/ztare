# LeanMill Project Folder

This folder holds the public LeanMill / lemma-relevance artifacts for GP-225. It mixes long-running research history, current factory state, and model/data files. The current operating entry points are the vNext seam, the vNext spec, the research log, the dashboard data, and the repair-family specs.

Canonical GP-225 documents:

- Seam: `research_areas/seams/engine/lean/GP-225_leanmill_vnext_station_factory_seam.md`
- Spec: `research_areas/specs/active/engine/lean/GP-225_leanmill_vnext_station_factory_spec.md`

## Current Navigation

| File or directory | Purpose |
|---|---|
| `research_log.md` | Chronological LeanMill research log. Use this for what changed, what was learned, and current scientific boundaries. |
| `LEANMILL_HANDOVER_2026-05-21.md` | Handover note from the prior LeanMill continuation point. |
| `LEANMILL_VNEXT_PULL_FORWARD_COVERAGE_2026-05-21.md` | Human-readable coverage matrix for the vNext pull-forwards and 24x7 worker blueprint. |
| `COGNITIVE_FIRM_MILL_COMPANY_GAP_ANALYSIS_2026-05-21.md` | Gap analysis for hosting LeanMill-like companies in the Cognitive Firm kernel via generic `OperatingUnit` and `WorkItem` primitives. |
| `factory_dashboard.html` | Local dashboard shell for factory state. |
| `FACTORY_DASHBOARD_README.md` | Dashboard-specific notes and refresh expectations. |
| `refresh_factory_dashboard.sh` | Dashboard refresh helper. |
| `factory_dashboard_data/` | Current machine-readable control-plane state: station contract, queue, events, source inventory, lifecycle, coverage gate, and safe 24x7 status. |
| `repair_families/` | Versioned YAML repair-family specs. These are the data-backed replacement for row-specific Python memory. |
| `LEANSEARCH_MCB_REMAINING_*` | Current MCB remaining source/queue/static/row-context packets used by source qualification and residual-family planning. |
| `LEANSEARCH_SOURCE_CANDIDATE_PACKET.*` | Source candidate packet from the broader LeanSearch source lane. |
| `PATH_C_*` | Legacy Residual Compiler queue/score artifacts. New docs should say `Residual Compiler`; legacy filenames remain for compatibility. |
| `REAL_PROVER_PRACTICE_PACKET.*` | Practice/prover packet, not clean proof credit by itself. |
| `LATEST_META_SOLVER_CONSUMPTION_MANIFEST.*` | Latest meta-solver consumption manifest for the surrounding GP-225 apparatus. |
| `leanmill_llm_critic.py` | Older LLM critic/proposal support. Current vNext proposal boundary is in `scripts/public/control/leanmill_llm_proposal_*`. |
| `mathlib_pairs.jsonl` | Large lemma-pair corpus. Treat as data, not an operating log. |
| `train.jsonl`, `test.jsonl`, `lemma_vocab.json`, `target_vocab.json` | GNN/ranker training and vocabulary artifacts. |
| `ranker_checkpoint*.pt`, `minilm_*.npy`, `minilm_*.meta.json` | Model and embedding checkpoints. |
| `v*.json`, `v*.md`, `v*.jsonl` | Historical experiment artifacts. Read only the specific version referenced by the log or seam. |

## Current vNext Control Files

Inside `factory_dashboard_data/`:

| File | Purpose |
|---|---|
| `station_action_contract.json` | Current station contracts and next WorkItems. |
| `repair_family_registry.json` | Stable local repair-family registry read model. It is refreshed from scratch discovery roots but is the deterministic dashboard/spec/gate registry path. |
| `station_scheduler_plan.json` | Scheduler projection from station contracts to WorkItems. |
| `learning_work_seed_plan.json` | Concrete WorkItem seed plan generated from station state: guarded proof probes, proposal jobs, and subscription-agent tasks. |
| `queued_learning_work/` | Derived probe packets with explicit credit boundaries and negative controls. |
| `leanmill_work_queue.sqlite` | Local SQLite WorkItem queue. |
| `leanmill_events.jsonl` | Append-only event ledger for the local mill control plane. |
| `leanmill_factory_policy.json` | Folder-local operating policy: live profile knobs, lane floors, model/agent budgets, proof timeouts, source-scout floors, and worker runtime-version thresholds. Operational numbers belong here rather than scattered launch commands. |
| `leanmill_24x7_status.json` | Last safe 24x7 control-plane run receipt. |
| `leanmill_watchdog_status.json` | Local watchdog receipt: daemon liveness, restarts, queue/open-queue state, current factory verdict, and gate results. |
| `leanmill_shutdown_status.json` | Last local factory shutdown receipt. |
| `station_health_dashboard.json` | Station backlog, terminal throughput, p95 terminal time, and blockers. |
| `leanmill_observability.json`, `leanmill_observability.md` | Central diagnosis surface for queue health, event counts, LLM spend/fallbacks, source-query rejects, source-binding failures, and current bottleneck classes. |
| `leanmill_factory_intelligence.json`, `leanmill_factory_intelligence.md` | Action-intelligence ETL over the queue/events/observability receipts: per-station and per-kind lead/cycle times, SLA breaches, learning-unit flow, conversion diagnostics, family-promotion blockers, ops-vs-learning exit separation, loss accounting, and ranked next actions. This is the compact factory-brain surface to inspect before opening scattered receipts. |
| `heldout_independence_scout.json`, `heldout_independence_scout.md` | Deterministic scout for candidate-family heldout rows. It nominates rows that satisfy independence prechecks and can enqueue bounded GM reviews; it does not create validation credit. |
| `heldout_promotion_worker.json`, `heldout_promotion_worker.md` | Worker receipt for scout-to-template/probe/receipt promotion. It can enqueue heldout template work, enqueue heldout family-spec probes, and emit heldout receipts only after probe/governance evidence exists. |
| `evaluation_harness_contract.json` | Four-arm public-tool attribution benchmark contract: public static tools, governed static tools, governed adaptive execution, and governed adaptive residual curriculum. The contract records whether the family/row inventory gates are ready for a full benchmark. |
| `evaluation_harness_prep.json`, `evaluation_harness_prep.md` | Benchmark prep packet: selected rows, tier counts, four-arm contract, readiness gate, and next family-promotion blocker. |
| `dead_letter_triage_status.json` | Last bounded dead-letter triage receipt; records retryable proposal-validation requeues and non-retryable holds. |
| `recover_rejected_source_bindings_status.json` | Last deterministic recovery receipt for source-binding artifacts rejected by the ingester; recovers only from receipt allowlists and emits guarded canary probes or typed rejections. |
| `vnext_coverage_gate.json` | Machine coverage receipt for the pull-forwards and 24x7 blueprint. |
| `family_spec_gate.json` | Family-spec schema validation receipt. |
| `regression_gate.json` | Fast regression gate for curated/spec repair packets. |
| `residual_lifecycle.json` | Residual lifecycle state materialization. |
| `source_quality_feedback.json` | Source-bound conversion and loss-pressure feedback by repair family; allocation signal only. |
| `source_family_allocator.json` | Source/family allocation scoring, including source-quality throttles. |
| `source_inventory.json`, `source_inventory.md` | Source artifact inventory and eligibility counts. |
| `residual_family_source_plan.*` | Residual-family source leads. |
| `residual_family_canary_packets.json` | Work-in-progress canary packet candidates; no value credit by itself. |
| `source_search_runs/` | Per-source-request LeanSearch retrieval and static-filter receipts. These are source inventory only. |
| `source_search_integrations/` | Receipts that bind successful source-search runs into source-to-canary agent tasks, with explicit credit boundaries and negative-control requirements. |
| `source_binding_ingestion_status.json` | Latest receipt from converting completed source-to-canary agent artifacts into guarded probe WorkItems. |
| `agent_output_ingestion_status.json` | Latest receipt from converting completed subscription-agent outputs into typed proposal/source-search/post-probe follow-up WorkItems. It scans evidence-bearing rows first so stale terminal rows cannot hide fresh agent outputs. |

## Runtime Boundary

LeanMill uses two separate model surfaces:

- Subscription agents: Codex CLI and Claude Code through `src/ztare/common/subscription_agent_runtime.py`. These use the operator's CLI subscription auth, not API keys.
- API LLMs: bounded proposal calls through `src/ztare/common/llm_runtime.py`. These are proposal-only and must pass schema gates before any Lean probe.
- API dollar caps apply only to API LLM calls. Subscription Codex/Claude workers are constrained by task leases, wall time, iteration count, and allowed paths, not USD caps.
- Codex CLI fallback for proposal calls: `leanmill_llm_proposal_worker.py --allow-codex-cli-fallback` can use subscription-backed Codex in read-only mode when the API call is denied or errors. The fallback is still a proposal generator only; its JSON goes through the same proposal gate and typed source-query contract.
- Warm subscription-agent operation: `scripts/public/control/leanmill/agent_repair_worker.py --daemon --allow-agent-launch` keeps subscription-agent workers alive, reuses CLI session state when supported, and writes per-task transcripts/artifacts. The task contract still controls station, allowed paths, budget, expected exit, and negative-control requirements. In live ops, general warm workers should be launched with explicit `--claim-kind agent_repair_task --claim-kind subscription_agent_task --claim-kind agent_task --claim-kind agent_repair`; source-only workers claim `source_scout_task`. This keeps public-source scouting from occupying general repair/heldout agent capacity.
- Subscription-agent usage accounting: each launched Codex/Claude task records a `leanmill-subscription-agent-usage-estimate-v2` receipt with worker id, task kind, station, family, expected exit, agent id, warm-session reuse, prompt/output character counts, estimated tokens, runtime, model label, wall time, `subscription_mode=true`, and `cost_usd=0`. `leanmill_factory_intelligence.py` aggregates completed usage plus currently open warm-agent work by kind/worker/station, including source scouters, so subscription token burn can be judged against downstream exits.
- GM/operator lane: `scripts/public/control/leanmill/gm_operator_lane.py` creates and claims `gm_operator_task` WorkItems for the in-thread supervisor. This is for bounded source-strategy, hold/retire, sibling/heldout, and operator-needed decisions. GM outputs are receipts with `credit_type=none`; they can be compared against API LLM and subscription-agent outputs by downstream conversion, but they cannot ratify proof value.
- Warm Proof Execution operation: `scripts/public/control/leanmill/probe_worker.py --daemon --allow-heavy-lean --warm-repl-inline` claims bounded proof-probe WorkItems, uses the shared heavy-Lean slot lock, reuses `PersistentLean` inside bounded packets, and writes scoreboard/event artifacts. `leansearch_repair_canary_drain.py` also has a deterministic result cache at `/tmp/rung1/leanmill_canary_result_cache` for identical canary replays.
- Local watchdog: `scripts/public/control/leanmill/watchdog.py --daemon --interval-s 300` keeps the tmux-based local mill supervised. It restarts missing bounded daemon sessions, refreshes factory intelligence, runs the infra freeze gate, and writes `leanmill_watchdog_status.json`. It has no proof-credit authority and does not edit scientific scoreboards.
- Worker runtime-version discipline: every worker claim/heartbeat records a `leanmill-runtime-version-receipt-v1` into the queue database. The receipt includes process start time, pid, git head, tracked-change count/hash, restart-required watched-source hash, dynamic watched-data hash, watched-source max mtime, and stale/runtime-mismatch detection. The watched file sets and thresholds live in `leanmill_factory_policy.json` under `runtime_version`; intelligence root-cause thresholds live under `intelligence`; observability bottleneck windows live under `observability`. Watchdog, observability, and factory intelligence surface stale or mismatched runtime-source workers as high-priority operational defects. Dynamic repair-family YAML and seam/spec doc changes are tracked as data-version drift, not automatic process-staleness.
- Local shutdown: `scripts/public/control/leanmill/shutdown.py --reason <reason>` writes `leanmill_shutdown_requested.json`, stops LeanMill tmux sessions, and writes `leanmill_shutdown_status.json`. The watchdog honors the shutdown marker and will not restart workers until the marker is cleared, for example with `leanmill_watchdog.py --clear-shutdown-marker`.
- Priority proof lanes: run a closure-focused daemon with `--probe-lane family_spec` and a general/source-shape daemon with `--exclude-probe-lane family_spec`. Queue claiming is lane-aware, so source scouting and source-bound probes cannot occupy the versioned repair-family closure lane. The current closure lane is the family-spec lane generated by `leanmill_learning_work_seeder.py --max-family-spec-probe-families`.
- Backlog floors are lane-aware: `leanmill_backlog_replenisher.py --family-spec-probe-floor ... --source-shape-probe-floor ...` keeps a source-heavy queue from hiding an empty closure lane. Duplicate proof replay remains blocked by deterministic probe signatures; the replenisher widens the policy-owned candidate pool (`overgenerate_factor`) to find different proof packets instead of weakening cooldowns.
- Proof-probe cooldowns are signature-scoped. Proposal and agent lanes may use family-level terminal cooldowns, but `repair_canary_probe` seeding is blocked by open/recent `probe_signature`, not by broad same-family terminal history. This lets distinct templates or heldout rows from the same family run without replaying identical packets.
- Family-spec probes are row-sharded. A repair family is memory, not the executable learning-unit identity; `leanmill_learning_work_seeder.py` emits separate `(family, row)` proof packets with their own signatures and matched controls. This prevents many templates from collapsing into one repeat family packet while still blocking identical packet replay.
- Learning-work seeding: `scripts/public/control/leanmill/learning_work_seeder.py --enqueue` turns current station artifacts into concrete queue jobs. Probe packets generated by the seeder set `source_credit_eligible=false`, `clean_solver_credit_eligible=false`, `worker_can_self_ratify=false`, and `proof_credit_authority=governance_gate`.
- Source scouting loop: `leanmill_llm_proposal_worker.py` and `leanmill_agent_repair_worker.py` can propose typed source-query contracts (`declaration_ref`, `theorem_shape`, or `semantic_search`); `leanmill_agent_output_ingester.py` sends valid scout JSON straight to source-search work and uses API-LLM review only for ambiguous transcripts; `leanmill_source_search_worker.py` runs retrieval/static qualification; `leanmill_source_search_integrator.py` converts successful runs into bounded source-to-canary binding tasks; `leanmill_source_binding_ingester.py` turns completed binding artifacts into guarded probe WorkItems. Target rows must be in the active corpus, and the binding plus ingestion path is required before source-search inventory can become probe work. Source/scout/subscription-agent lanes cannot declare `ratified_closure`, `exact_gap_candidate`, or `valid_falsifier` as value exits; those require Proof Execution plus Governance Gate receipts.
- Family-spec patch ingestion: `expected_exit=family_spec_patch` subscription-agent outputs bypass API-LLM/source-request review. A deterministic patch receipt with changed, parseable target-family YAML is recorded as `family_spec_patch_accepted`; terminal hold/retire receipts remain no-credit exits; failed or missing receipts become typed blockers. The changed YAML then re-enters the normal Family Spec Gate and family-spec proof-probe seeding path.
- Public-source scouting loop: `leanmill_external_source_scout_seeder.py` seeds subscription-backed Codex/Claude `source_scout_task` WorkItems for public Lean/mathlib source scouting. These tasks may use external lookup if the CLI runtime supports it, but their only useful output is typed `source_request` JSON with 5-8 declaration/theorem-shape queries and concrete target rows. The ingester and source-query gate still decide whether anything becomes a `source_search_task`. The 24x7 runner keeps this lane at a bounded queue floor through `--external-source-scout-floor`; it tops up scouts only when open external-scout work falls below the floor.

Proof value still requires Lean execution and Governance Gate ratification. Repair-canary credit, source credit, and clean-solver credit are separate.

## Current Repair-Family Specs

The active spec layer currently has nine migrated families and 32 positive-or-control templates:

- `asymptotics_bigo_eq_mul_planner.yaml`
- `complex_limit_causeq_planner.yaml`
- `cusp_function_qparam_periodic_planner.yaml`
- `ennreal_tsum_condensation_planner.yaml`
- `interval_alignment_planner.yaml`
- `qparam_tendsto_norm_exp_planner.yaml`
- `spectral_rayleigh_spectrum_planner.yaml`
- `spectral_rayleigh_extremum_planner.yaml`
- `spectral_rayleigh_singular_values_planner.yaml`

Run `scripts/public/control/leanmill/family_spec_gate.py` for schema/credit/control validation. The heavier regression check is governed Lean replay through `leansearch_repair_canary_drain.py`.

Validated-family promotion requires a passing `scripts/public/control/leanmill/heldout_receipt_gate.py` receipt. Candidate-family evidence alone is not enough. `scripts/public/control/leanmill/heldout_independence_scout.py` is the upstream eligibility scout; it can nominate independent heldout candidates and queue GM review tasks, but it cannot issue heldout receipts or promote a family. `scripts/public/control/leanmill/heldout_promotion_worker.py` is the executable bridge from scout nomination to template/probe/receipt work.

Current promoted YAML families include `ennreal_tsum_condensation_planner`, which reached `validated_family` on 2026-05-22 after a heldout receipt passed for `MCB_003_le_tsum_schlomilch`. Sibling-rich families such as `cusp_function_qparam_periodic_planner`, `complex_limit_causeq_planner`, `convolution_argument_planner`, and related zpow/asymptotics families may appear as `validated_family_requires_true_holdout_check`; that status is candidate-or-better inventory for benchmark readiness, but it is not validated-family credit.

## Infra Freeze Gate

Use `scripts/public/control/leanmill/infra_freeze_gate.py` as the local boundary between control-plane hardening and science mode.

It fails on recent infra-class blockers: terminal probes without typed or inferable learning-unit exits, unexpected negative-control passes, launched subscription-agent tasks without transcript/artifact receipts, source/scout agents declaring value exits without governance, uningestable source-binding tasks, running probes past the grace window with no scoreboard artifact, and core-lane dead letters. Probe and subscription-agent daemons reclaim their own abandoned in-flight leases at startup, so supervised restarts do not strand work for the full lease window.

Rejected source-binding artifacts are not left as manual cleanup. The 24x7 runner invokes `leanmill_source_search_integrator.py --recover-rejected-bindings` before the binding ingester; it recompiles safe bindings from the original receipt allowlists and then lets the ingester turn them into guarded probes. Recovery rescues inventory only; proof value still requires Proof Execution and Governance Gate receipts.

Recovery and warm-worker spending are bounded by the allocator. Auto-compiled recovery rows are not recursively recovered if they fail again, and families marked `do_not_spend_until_new_evidence` in `source_family_allocator.json` are skipped by the seeder and retired by the API LLM / subscription-agent workers without a model call or CLI-agent launch.

Source-bound attempts are now fed back into allocation. `leanmill_source_quality_feedback.py` counts source-bound probes, guarded value exits, expected negative-control failures, rejected bindings, rejected source searches, and proposal/agent failures by family. If a family accumulates source attempts with no governed value, the allocator emits `repair_source_strategy_before_more_binding`; the seeder then retires stale source-request/sibling work and dispatches bounded source-strategy repair or decomposition instead of repeating broad sourcing.

If source-strategy repair itself has already run and subsequent source-bound work still produces no governed value, the allocator escalates to `hold_source_binding_until_new_target_evidence`. That holds only the source-binding lane for that family; family-spec probes and other governed proof-science lanes can continue. The seeder retires stale source-search/source-binding/sibling work for held families so the factory does not spend warm-agent or Lean capacity rechecking a known-bad source loop.

External public-source scouts are exempt from that stale source-binding retirement rule when marked `source_scout_mode=subscription_public_external`, because their job is to find new target/source evidence rather than replay the held source-binding loop.

When it passes, stop fixing adapters by default and spend cycles on proof-science lanes: family-spec probes, sibling/heldout evidence, exact gaps/falsifiers, and Governance Gate outcomes. Reopen infra work only for a new freeze-gate failure, a failed vNext coverage gate, or an explicit operator override.

Current MECE readiness boundary:

- queue health: no stuck leases, bounded dead letters, workers claim only their lane;
- worker conversion: proposals and source artifacts either enter a downstream lane or emit typed rejection/retirement;
- governance safety: no proof-value exit is accepted without Proof Execution plus Governance Gate evidence;
- proof-value conversion: closure, exact-gap, falsifier, candidate-family, or validated-family exits increase under matched controls.
