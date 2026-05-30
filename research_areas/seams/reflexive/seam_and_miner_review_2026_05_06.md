# Seam + Miner Review — 2026-05-06 PM

> **Seam metadata** · `seam_id:` seam_and_miner_review_2026_05_06 · `track:` reflexive · `status:` closed · `last_updated:` 2026-05-09


**Status:** closed *(inferred 2026-05-08 — needs operator review)*

Comprehensive review of (a) lingering seams, (b) candidate new seams
for self-recursive improvement via telemetry, (c) miner-script
inventory + ROI dispersion. Non-NS scope per operator request.

---

## Part 1 — Lingering open seams

17 seams marked "open" today. Rough alive/stale audit (mtime + code
trace + recent F-row mention):

| Seam | mtime | Code trace? | F-rows? | Honest verdict |
|---|---|---|---|---|
| **GP-055** meta_judge_parse_robustness | 2026-04-14 | none | 0 | **Stale — likely shipped piecemeal under different name** (the `parse_llm_json_with_retry` in `common/utils.py` covers this turf). Promote to `shipped` or close with rationale. |
| GP-109 residual_periodicity_detector | 2026-04-22 | partial | 0 | Stale-pending. No live reference. |
| GP-113 diagnosis_feedback_loop | 2026-04-21 | partial | 0 | Stale-pending. |
| GP-111 proactive_closure | 2026-04-21 | none | 0 | **Stale — likely subsumed** by AGENTS.md §5b "Proactive closure" rule. Promote or close. |
| GP-115 residual_driven_grammar_expansion | 2026-04-22 | partial | 0 | Stale-pending. Probably subsumed by GP-087 tail-correction primitives shipped today. |
| GP-112 margin_of_safety_gate | 2026-04-22 | partial | 0 | Stale-pending. |
| GP-116 compression_as_architecture_discovery | 2026-04-22 | partial | 0 | Stale-pending. |
| GP-060 parallel_champion_synthesis | 2026-04-14 | partial | 0 | Stale. K-divergent-workers-plus-combiner. May be subsumed by GP-174 parallel_mutator (shipped). |
| GP-056 axiomatic_patching | 2026-04-14 | none | 0 | Stale — no code trace. |
| GP-057 ratio_finiteness_gate | 2026-04-14 | none | 0 | Stale — no code trace. |
| GP-062 trajectory_thrash_detection | 2026-04-15 | yes | 0 | **Alive — code in `composition/trajectory_thrash_detector.py`**. Should promote to `shipped`. |
| GP-061 constraint_accumulation_as_output | 2026-04-15 | yes | 2 | **Alive** — Component A structural extractor shipped + flowing into derived_constraints ledger. Promote to `shipped`. |
| GP-058 bug_bounty_factory_integration | 2026-04-14 | none | 0 | Stale-aspirational. |
| GP-114 neural_scaling_spectral_dynamics | 2026-04-21 | none | 0 | Stale-aspirational. May be subsumed by paper 6 work. |
| GP-081 lean_formal_bridge | 2026-04-22 | partial | 0 | Stale-pending. NS Track B closure attempt is the canonical instance now; GP-081's framing predates the typed_endpoint_pack architecture. |
| GP-189 ns_continuation_criterion | 2026-04-29 | none | 2 | **Alive proposal** — F-rows reference it; no code yet. NS-specific so out of scope here. |
| GP-224 ns_closure_swarm_decision | 2026-05-06 | yes | 2 | **Alive** — codified the queue-vs-no-queue debate; scaffold shipped today (`scripts/public/lean/typed_endpoint_queue.py`). |

**Concrete cleanup actions (operator-time, ~1h):**
1. Promote to `shipped` (with one-line rationale): GP-061, GP-062, GP-055, GP-111
2. Close as `subsumed_by_X`: GP-115 (subsumed by GP-087 tail correction), GP-060 (subsumed by GP-174 parallel_mutator), GP-114 (subsumed by paper 6)
3. Close as `abandoned_no_signal`: GP-056, GP-057, GP-058 — 3+ weeks no activity, no code trace, no F-row reference
4. Leave open with explicit "next observation" gate: GP-109, GP-112, GP-113, GP-116, GP-081
5. Active (no action): GP-189, GP-224

This is the GP-221 (seam health audit) workflow run manually. Shipping
the audit script is itself the meta-leverage — see Part 2.

---

## Part 2 — New seams (self-recursive via telemetry)

Ranked by leverage, scoped non-NS, all telemetry-driven:

### #1 — Implement GP-221 seam health audit (was scoped today, deferred)

**Why:** the manual audit above took me 30 minutes for 17 seams. The
corpus has 179 total. Doing this as a manual periodic review will
not happen. Mechanizing it produces the report I just wrote
automatically + lets operator review the deltas.

**What to ship:**
- `scripts/public/audits/seam_health_audit.py` — walk
  `research_areas/private/seams/`, for each seam frontmatter-extract
  status, mtime; grep `EXPERIMENT_TRACK_RECORD.md` for the seam id;
  ripgrep `src/` and `scripts/public/` for related symbols; bigram-Jaccard
  pairs against seams >30 days old (re-seam detector)
- Output: `analytics/public/queries/audits/seam_health_report.json`
- KR: `kr_seam_health_periodic` with P30D recurrence (lighter cadence
  than primitive ROI; corpus changes slowly)

**Cost:** ~3-4 hours implementation. Pure stdlib + grep. No LLM.

### #2 — Implement GP-220 reflexive primitive ROI scorecard

**Why:** the same staleness problem applies to primitives. R10-R16
backports shipped in April; we don't measure their engagement_rate /
hit_rate / score_lift. Without the ROI scorecard, primitive over-build
is unchecked. Ranks #2 because GP-220 is more invasive (touches
per-iter telemetry surfaces) than GP-221.

**What to ship:** see `GP-220_reflexive_primitive_roi_telemetry_seam.md`
shipped today.

**Cost:** ~6-8 hours.

### #3 — NEW: Cross-Substrate Cap-Kind Distribution Miner

**Why:** GP-183 phase A5 emits `cap_kind_iter_NNN.json` per iter (gaming
/ physics_violation / generalization_gap / holdout_miss /
numerical_failure). We have ~262 F-rows worth of iters with cap_kind
classifications. **No miner aggregates them.** Cross-substrate
distribution would reveal:
- Which substrate classes hit which cap kinds most often
- Whether new gates (R10-R16 etc.) shifted the distribution
- Recurring cap-kinds across diverse substrates → primitive candidates

**What to ship:** `scripts/public/mining/mine_cap_kind_distribution.py` —
walk all `projects/*/workspace/cap_kind_iter_*.json`, aggregate by
(substrate_class, cap_kind) tuple, output a contingency matrix +
top recurring (substrate-class, cap-kind) clusters.

**Cost:** ~2 hours. Pure CPU. Produces `analytics/public/queries/classification/cap_kind_distribution.json`.

**Compounds with:** the failure_cluster_analyzer, GP-220 ROI scorecard.

### #4 — NEW: Production-Hit@K Telemetry Integration into reflexive_audit

**Why:** today's v2 production hit@10 falsifier is a one-shot script.
Its verdict (DATA_SHIFT_DOMINATES / PURSUE_V4 / SHIP_V2) is not
integrated into any audit. The reflexive_audit's `gather_telemetry`
should consume it as a "ranker ROI" signal alongside CANNOT-PATCH events.

**What to ship:** add `production_hit_at_k_summary` field to
`AuditReport`; reflexive_audit reads
`analytics/public/leanmill/results/v*_production_hit_at_k.json`. Includes
the verdict + the test-vs-production delta.

**Cost:** ~1 hour. Surfaces ranker ROI alongside primitive ROI.

### #5 — NEW: Miner ROI Dispersion Telemetry

**Why:** we have 15+ miner scripts. No tracking of which ones produce
actionable output vs decorative summaries. The miner-corpus needs the
same ROI discipline applied to per-iter primitives (GP-220).

**What to ship:** `scripts/public/mining/mine_miner_roi.py` — for each miner
in `scripts/public/mining/` and standalone miners, compute:
- `last_run_utc` (mtime of canonical output file)
- `run_frequency_per_28d` (count of mtime updates over last 28 days)
- `output_size_bytes` (does it produce non-trivial output?)
- `downstream_references` (grep for the output filename in `org/`,
  `research_areas/`, `papers/`)
- Verdict: alive / dormant / dead

**Cost:** ~2 hours. Closes the meta-loop (miners audit miners).

### #6 — NEW: Mathlib Reconnaissance Periodic Refresh

**Why:** today I ran the mathlib reconnaissance for NS-relevant
shapes. The output (`ns_mathlib_reconnaissance_summary.json`) is a
one-shot snapshot. Mathlib evolves (new lemmas land monthly); the
reconnaissance should refresh on a cadence. **NS-targeted today;
generalize to other substrate domains later.**

**What to ship:** add `kr_mathlib_reconnaissance_refresh` with P30D
recurrence; the existing `scripts/public/lean/mathlib_lemma_scout.py --build` is
the work; the KR closes the staleness gap.

**Cost:** ~30 minutes (just author the KR + small wrapper). Note: this
is one specific instance of "ZTARE's external-data corpus needs
periodic refresh"; if more such corpuses appear, generalize.

### #7 — NEW: Cross-Miner Triangulation View

**Why:** failure_cluster_analyzer + cannot_patch_harvester +
endpoint_type_compression_audit + mine_climb_triggers each look at
ONE signal axis. **No script joins them.** A unified per-target view
would show: "this Lean obligation has cluster X (9 failures), Y
compression candidates, was preceded by Z climb triggers." That's
where compounding insight surfaces.

**What to ship:** `scripts/public/mining/triangulate_per_target.py` — joins
the 4 miner outputs by target name, produces a per-target dossier.

**Cost:** ~2-3 hours. Compounds value of all 4 individual miners.

---

## Part 3 — Miner Script Inventory + ROI Dispersion

Ranked by perceived alive/value:

### Alive + decisive (run regularly, output consumed)

1. **`failure_cluster_analyzer.py`** — clusters typed_endpoint_failure_log
   events. Run today: surfaced TrackBProfileLipschitz* family + 3
   cluster patterns. Output `analytics/public/queries/audits/failure_clusters.md`.
   Active reference in mandate.
2. **`mathlib_lemma_scout.py`** — index + query mathlib by shape. Run
   today for NS reconnaissance. Output
   `analytics/public/queries/lean/mathlib_lemma_index.json`.
3. **`reflexive_audit.py`** (`src/ztare/composition/`) — GP-102 cron-style
   audit. Run today after 3-week staleness. Output
   `research_areas/private/seams/reflexive/reflexive_audit_report.json`.
4. **`endpoint_type_compression_audit.py`** — GP-223 Layer 3.
   Shipped + run today; 1 candidate surfaced.
5. **`v2_production_hit10_falsifier.py`** — apparatus_level2_review
   claim_v3_gnn_predicts_real instantiation. Shipped + run today.

### Alive but rarely consumed

6. **`mine_climb_triggers.py`** — when did substrates climb past
   plateaus? Useful but no recurring consumer.
7. **`mine_pivot_effectiveness.py`** — does the pivot logic actually
   help? Output exists but not flowing into reflexive_audit.
8. **`mine_score_ceilings.py`** — qualitative-ceiling diagnosis. Output
   referenced in some F-rows but not periodically.
9. **`mine_judge_stratified.py`** — judge calibration by substrate
   class. Run once or twice per quarter.
10. **`mine_lollapalooza_hypothesis.py`** — multi-cause score
    breakthroughs. The reflexive_audit (today) reported lollapalooza
    refuted; this miner's role decayed.
11. **`mine_trajectories.py`** — score trajectories per substrate.
    Useful for postmortem but not periodic.
12. **`audit_gate_coverage.py` / `audit_gate_effectiveness.py` /
    `audit_gate_engagement.py`** — three gate-audit miners. Closely
    aligned with GP-220 scope; should consolidate.
13. **`audit_judge_drift.py`** — judge calibration check. Periodic
    duty candidate.

### One-shot / specialty

14. **`extract_effective_rank.py`** / **`extract_layer_transitions.py`** —
    paper 6 (neural scaling) specific.
15. **`extract_mathlib_graph.py`** — one-shot mathlib graph build.
16. **`gflownet_data_extract.py`** — GFlowNet experiment specific.
17. **`mine_champion_trajectory_sequence.py`** — one specific analysis.
18. **`mine_cross_provider_classifier_agreement.py`** — Mutator/judge
    cross-family agreement check.
19. **`cannot_patch_harvester.py`** — feeds the
    typed_endpoint_failure_log. Production-grade now but a sister to
    failure_cluster_analyzer.
20. **`typed_endpoint_agent_panel_harvest.py`** — Codex's reusable
    closed-loop artifact (per today's update).

### Today's additions

21. **`mine_ztare_pairs_for_training.py`** — extracts (target, used_lemmas)
    from ZTARE Lean spine. 880 pairs persisted.
22. **`endpoint_type_compression_audit.py`** — GP-223 Layer 3.
23. **`v2_production_hit10_falsifier.py`** — see above.

### What's missing (not yet built)

- Miner ROI scorecard (proposed seam #5 above)
- Cross-miner triangulation (proposed seam #7 above)
- Cap-kind distribution (proposed seam #3 above)
- Seam health (proposed seam #1 above; GP-221 deferred)
- Reflexive primitive ROI (proposed seam #2 above; GP-220 deferred)

---

## Recommendation: ship-order if any

**If 1 day available:** ship #3 (cap-kind distribution miner — 2h, pure
CPU, immediate operator-time signal) + #4 (production-hit@k integration
into reflexive_audit — 1h, closes a known telemetry gap).

**If 1 week available:** add #1 (seam health audit) + #2 (GP-220 ROI
scorecard implementation). Together they close the meta-loop:
seams audit themselves, primitives audit themselves, miners audit
themselves.

**If just spot-cleanup:** Part 1's seam status updates (15-min text-only
edits to promote/close stale seams). Lowest leverage but highest
hygiene.

---

## Honest closing

**The pattern across seams + primitives + miners:** all three
catalogs accumulate without a retirement discipline. The seam corpus
has 179 files; 17 marked open of which most are stale-pending. The
primitive catalog has 8 entries; no ROI metric. The miner corpus
has 20+ scripts; no ROI metric.

**The reflexive move:** apply the closure-pressure discipline ZTARE
uses for substrates (GP-168) to the apparatus's own catalogs.
exogenous resource pressure (operator time, audit cadence) is what
forces the prune. Without it, "is this still useful?" stays unanswered
and the corpus accretes.

**Today's KR system + closure_daemon are the right substrate** — author
the audit KRs (#1, #2, #5 above), let the daemon enforce cadence, and
the catalogs self-prune over time.
