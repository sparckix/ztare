# Review — meta/governance layer

Cluster: `engine_router.py`, `strategy_battery.py`, `strategy_gate_actions.py`, `machinery_contradictions.py`, `stale_surface_audit.py`, `arc3_run_observability.py`, `search_control_repair.py`, `experiment_executor.py`, `evidence_probe.py`, `evidence_quotients.py`, `evidence_digest.py`, `refuted_experiments.py`, `residual_specialists.py`, `residual_repair.py`, `orchestrator/trace_auditor.py`, `common/k_line.py`, `machinery_adoption.py`, `adapter_width.py`.
Scope: 18 files = 11,554 LOC + callers (`arc3_play_loop.py`, `pre_judge_gate.py`, `leaf_workbench_executor.py`, `operator_proposal_contract.py`, briefing providers) + live receipts in `projects/arc3_ls20_gov/workspace/`.

## 1. Correctness

### Engine router (`src/ztare/worldmodel/engine_router.py`)
- **Escape latch ignores supersession — real bug.** `engine_router.py:310-321` (`_unreachable_targets`) returns True on any *historical* `resolution=="unreachable"` row (deliberately permanent, "run-11 lesson"). But `distinguishing_play.py:95-118` (`_resolved_target_ids`) implements last-write-wins where `"reopened"` supersedes. The live ledger has 4 unreachable targets, **all later reopened** — `escape_unreachable` is True right now over zero actually-unreachable targets. Consequence: branch 0 (`engine_router.py:614-632`) fires hypothesis-class escape whenever population collapses + stagnation≥3 even though targets are playable; `_signature_from_state` (line 431) stamps `regime_position="boundary"` into every k-line signature forever. Two organs disagree on the semantics of the same ledger; the router side is wrong.
- Router receipts otherwise recomputed fresh each call (no stale-latest reads); the uncommitted diff (n_fingerprints→n_distinct_hypotheses; `_last_enumeration_futile` rewritten to `generated_count>0 and admitted==0`) is correct.
- ~150 LOC of prior/counterfactual handling in `route()`/`decide()` (lines 582-597, 687-728, 872-893) is dead code — see k-line.

### K-line prior (`src/ztare/common/k_line.py`, 1,100 LOC) — provably can never influence a route
Three independent, each-sufficient blocks:
- `authority=="causal_bound"` requires `causal_authority=="matched_ablation"` + `ablation_pair_ref` (`k_line.py:1026-1044`); **no writer anywhere sets those fields**.
- `k_line.py:1008-1021` drops all `transfer_status=retrospective_candidate` rows; all 9 fix_class rows in live `k_lines.jsonl` are retrospective, and `record_success` (the only prospective stamper) has no production caller → `routing_prior` returns None on every call. `router_prior_receipts.jsonl` does not exist — the prior has never been non-None.
- Even bypassing both: `engine_router.py:445-446` hardcodes 2 of 6 signature axes to `"unknown"` (never match, `k_line.py:993`), and remaining axes use disjoint vocabularies (`visible/holdout` vs stored `observed/heldout/testimony`; `diverse/collapsed-*` vs `objective_*`) → max 2 of the required 4 matches. Match is impossible.
- Bonus bugs: backfill dedup key on missing timestamp re-appends rows every scan (`k_line.py:601-627`); backfill stamps *current* signature/config on all historical rows, so `_attribution_for_rows` gets zero contrast forever (`k_line.py:585-596, 730-731`).

### Trace auditor (`src/ztare/orchestrator/trace_auditor.py`, 2,093 LOC, 21 checks)
- **Nothing consumes its findings.** `run_audit` ignores `emit`; `emitted` hardcoded `[]` (lines 2048-2052); `_emit_rider` (1513) has zero production callers. Play loop (arc3_play_loop.py:3598-3614) prints counts and stores two string lists in the report JSON; no branch reads them. Write-only telemetry.
- **Recurrence false positive:** `check_recurrence` (1423-1441) sets `fixed[cid]=True` the first time a check is ok, so a first-ever anomaly after any healthy audit is tagged `recurrence=True` and `fire_conjecture_rung` (1342-1420) burns an LLM call + ledger row on a failure that never "came back". Conjecture ledger's only reader is a briefing provider (`forced_reframe.py:443`).
- **Cross-project pollution:** `check_loop_phase_death` (940-948) globs `projects/*/workspace/*.log` — a week-old failed log in a sibling project flags this project on every audit, no acknowledgment state to clear.
- **Dead-letter detector false pos/neg by construction:** "≥2 modules mention the filename ⇒ read" proxy (516-544) misses 2-writer files, flags single-module writer+readers; `check_file_seam_coverage` (1089-1161) only sees `"workspace/…"` string literals, so ledgers addressed via filename constants are invisible. `tests/test_no_dead_letter_receipts.py` freezes ~12 dead letters as `_KNOWN_DEBT`.
- `check_gate_achievability` (1694-1697) uses `gates.py` mtime as freshness — the uncommitted tree invalidates every achievability receipt, refiring the anomaly until an oracle rerun.
- Live report: 1 "active" anomaly (`phase_cost_regression` — a dominant-phase>50% rule any play loop trips) + 8 standing catalog advisories. Alarm fatigue, no actuator.

### Weakness-receipt loop (483 rows) — half-closed, non-converging
- Emitters: every pre-judge gate block appends (`pre_judge_gate.py:1757-1770`) plus `repair_preflight.py:512-521` — **no emission dedup**. 483 rows cover 151 distinct `task_id`s; top task re-reported 34×.
- Consumers: only `latest_harness_weakness.json` (single most-recent receipt) is decision-bearing — scopes leaf workbench capabilities and first-fire tracking (`leaf_workbench_executor.py:1169-1248`, `leaf_workbench.py:1301, 1393-1402`, `retry_surface.py:183`). The 483-row ledger is consumed only as the **last 4 rows** rendered as briefing bullets (`tried_failed_digest.py:61, 126-133`). Bulk acknowledged dead in `_KNOWN_DEBT`.
- The repair leg does execute (62 `counterexample_context` receipts, 1,477 visible-CLI receipts) — not fully open-loop. But 230 `unquotiented_counterexample_chart_missing` re-emissions over 8 days = treadmill; nothing tracks "route taken N times, class count not decreasing". Classes with empty `recommended_capability_id` (`unclassifiable`=73, `failing_gate_without_witness`=7, `plateau`=5) have **no automated executor** — 85 receipts re-emitted forever, human-only.

### Other organs (verified)
- `experiment_executor.py:321` genuine re-emission loop: `open_cards` didn't treat `rejected_unlowerable/killed/observed/survived` as terminal → 261 execution rows over 23 distinct card shas (top families 13× each). Uncommitted fix (`active_strategy_cards`) is the correct root-cause fix at the shared chokepoint; same migration correctly applied in strategy_battery/strategy_gate_actions.
- `strategy_battery.py:578-604` reads `latest_level_transfer_probe.json` with no currentness check — the exact stale-latest class `stale_surface_receipt_is_current` was built to prevent — stale probe keeps re-seeding repair cards for an already-fixed transfer. Also `stale_surface_audit.py:39-57` fingerprint omits `gate_harness.py`'s own sha; `:277` applies card rejections even when the gate crashed.
- `machinery_contradictions.py`: dedup by `failure_family_sha` against ALL rows including dispositioned (`operator_proposal_contract.py:138-151`) → a once-rejected contradiction family can never be re-carded — over-suppression, mirror image of weakness-receipt under-suppression. All detectors wrapped in bare `except: pass` (`:466-493`) — a detector can go permanently dark silently.
- `search_control_repair.py` uncommitted fix correct and load-bearing: terminal close now requires a bound `task_discharge_receipt` keyed on its sha instead of the spoofable witness sha (closes a close-laundering hole).

## 2. Governance overhead

- Object-level science ≈ **31,500 LOC**; governance/audit/receipt plumbing ≈ **17,300 LOC** → **0.55 lines of governance per line of science (~35% of surface)**. Play loop is 3,628 lines, ~half governance glue.
- **Audits that have demonstrably changed a decision** (receipts on disk): engine_router (17 routing decisions incl. one open-world escape); `latest_harness_weakness.json` → leaf capability scoping (1,477 capability receipts); refuted_experiments → `rejected_refuted` re-proposal blocks; residual_repair / stale_surface_audit(apply) / search_control_repair → strategy card dispositions (78-row ledger: 45 rejected, 15 rejected_unlowerable, 3 accepted); residual_specialists → challenger portfolio membership, width allocation.
- **Write-only telemetry (no consumer has ever branched):** trace_auditor (2,093), k_line prior lane (1,100), arc3_run_observability (671 — output frozen at Jul 9 while loop ran to Jul 15), adapter_width (274), machinery_adoption (107), `engine_routing.jsonl` itself, weakness-ledger bulk, conjecture_rung_ledger, strategy_battery dossier text, ~12 `_KNOWN_DEBT` files. ≈ **4,300 LOC provably inert** plus dead-ledger tail — and a meta-layer whose main occupation is auditing the other governance organs' dead outputs.

## 3. The 106 proposals / 0 promotions funnel

Proposals die at a handoff with no receiver:
1. `arc3_play_loop.py:1084-1089` calls `attempt_grammar_extension(project, log, ab, budget=0, implementation_owner="governed_carrier")`.
2. `grammar_reflex.py:425-440`: with `governed_carrier` it returns immediately after writing cards, emitting `ztare-grammar-reflex-handoff-v1` — a schema string that appears **nowhere else in the repo. Zero consumers.** Loop breaks to the governed checkpoint (= the human).
3. The implement leg that CAN accept cards (`grammar_reflex.py:444-508`, sealed leaf + house gates) is doubly disabled: `budget=0` and the owner short-circuit. The 22 rejected rows are fossils of when it ran — proof the gates work and the leg is now off.
4. Structural bridge fallback env-gated off by default (`grammar_reflex.py:84-85`).
5. Path B promotion (`grammar_extension._write_promotion_contract`) reachable only from side scripts run manually. `grammar_extension_promotion_contracts.jsonl` does not exist → `p0_metrics.catalog_promotions` structurally 0.
6. Default-loop card-disposition writers can only **reject** (`residual_repair.py:127,361,384`).

**Verdict: build→register→wire→first-fire is not executable end-to-end by the system.** Every acceptance path requires the human conductor. 84 cards sit open; their only systemic effect is a briefing paragraph.

## 4. Dead / unwired organs (callers verified)

| Organ | Evidence |
|---|---|
| `common/machinery_adoption.py` (107) | callers only in tests — as docs admit |
| `common/adapter_width.py` (274) | zero non-CLI callers; JSON read back only by its own `--report` |
| `worldmodel/arc3_run_observability.py` (671) | no callers; output stale 6 days |
| k_line routing-prior lane (~400/1,100) + router prior code (~150) | unreachable (three independent permanent blocks); `record_success` no production caller |
| `trace_auditor._emit_rider` (1513) | no production caller; `emit` flag no-op |
| `machinery_contradictions.tested_but_undispositioned` (:233) | no non-test caller |
| grammar-reflex handoff receipt | zero consumers of `ztare-grammar-reflex-handoff-v1` |
| `experiment_executor.execute_experiments` | CLI-only; never invoked by the loop |
| ~12 write-only workspace ledgers | frozen as `_KNOWN_DEBT` |

## Judgment: net-positive or drag?

**Split verdict, currently trending drag.** The inner governance ring earns its keep — pre-judge gates, refuted-experiment blocks, strategy card lifecycle, the router (hybrid mode), stale-surface currentness are decision-bearing, and the receipts enabled real RCAs (261-row executor loop, run-10/11 livelock, close-laundering). The uncommitted fixes are uniformly correct root-cause repairs.

But the outer ring is self-inflicted: ~4,300 LOC that provably cannot change any behavior (a 2,093-line auditor nothing listens to, an 1,100-line prior that can't match, three organs with no callers), a 483-row weakness ledger re-describing ~150 defects because emission has no dedup and three classes have no executor, and governance-auditing-governance. Most damning: the one autonomy lever this layer exists to provide — grammar promotion without the conductor — is switched off at its single call site, so 106 proposals converted at 0% while the meta-layer produced thousands of receipts about itself.

## Top 3 remediations

1. **Close the promotion funnel or stop pretending it's automated.** Give the grammar-reflex handoff a consumer: raise `budget>=1` and drop the `governed_carrier` short-circuit at `arc3_play_loop.py:1084-1089` (implement leg + gates exist and demonstrably reject junk), or wire the governed worker to write `accepted` dispositions + promotion contracts. One end-to-end promotion validates 2,000+ LOC of card machinery currently converting at 0%.
2. **Delete or wire the inert 4,300 LOC.** Remove k_line's routing-prior lane, adapter_width, arc3_run_observability, machinery_adoption, `_emit_rider` (or build their missing halves — matched-ablation producer + aligned signature vocabulary is a project, not a patch). Shrink trace_auditor to the checks anyone has acted on; make `active_apparatus` anomalies gate something (even just refusing a closure claim while `schema_route_ledger` reports halt_required).
3. **Fix the two receipt-semantics splits.** (a) `engine_router._unreachable_targets` must honor last-write-wins/`reopened` — reuse `distinguishing_play._resolved_target_ids` (engine_router.py:310-321); today escape latches on 4 targets all reopened. (b) Dedup weakness emission on `task_id`+evidence epoch (append a count, not a row); route empty-capability classes (`unclassifiable`, `failing_gate_without_witness`) to an explicit human queue instead of infinite re-emission.
