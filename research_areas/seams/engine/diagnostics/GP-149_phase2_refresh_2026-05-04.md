# GP-149 Phase 2 — Mining Refresh (2026-05-04)

> **Seam metadata** · `seam_id:` GP-149 · `track:` engine · `status:` delta report. Companion to `GP-149_mining_findings_and_inter · `last_updated:` 2026-05-09


**Status:** delta report. Companion to `GP-149_mining_findings_and_interventions_seam.md`.
**Triggered by:** GP-212 Phase B requirement + 2026-05-04 operator ratification.
**Source archive:** `analytics/public/ledgers/trajectory/trajectory_archive_enriched.jsonl` (refreshed today).

---

## 1. Corpus growth

| Metric | April 24 | May 4 | Δ |
|---|---:|---:|---:|
| Records | 1,825 | 2,608 | +783 (+43%) |
| Projects | 84 | 128 | +44 |
| Unclustered (regex) | 842 | 1,258 | +416 |
| LLM-classified categories | 15 (top-5: 65%) | 340 (top-10: 53%) | +325 (much longer tail) |

The corpus growth is real and concentrated in three substrate families: NS Phase 5* work, gp210 consciousness theory + companion gp211 Lean proofs, and Falsify backend telemetry (the latter not in the project archive but mentioned for completeness).

---

## 2. LLM weakest-point classification — distribution shift

Gemini Flash-Lite re-classified the 1,258 unclustered records. Distribution shift vs April 24:

### 2.1 Top 10 (May 4)

| Rank | Class | N (May) | Projects (May) | N (Apr) | Apr rank |
|---:|---|---:|---:|---:|---:|
| 1 | unfalsifiable_claim | 163 | 53 | 40 | 5 |
| 2 | missing_mechanism | 137 | 40 | 147 | 2 |
| 3 | overclaimed_scope | 99 | 30 | 187 | 1 |
| 4 | unmeasurable_construct | 69 | 24 | (24, novel class) | — |
| 5 | unsupported_assumption | 57 | 15 | (novel) | — |
| 6 | parameter_sensitivity | 37 | 20 | 81 | 4 |
| 7 | missing_counterfactual | 32 | 9 | 89 | 3 |
| 8 | missing_data | 25 | 15 | (novel) | — |
| 9 | definition_ambiguity | 23 | 10 | (28, novel) | — |
| 10 | unverified_assumption | 20 | 2 | (novel) | — |

### 2.2 Decisive shifts

- **`unfalsifiable_claim` rank 5 → rank 1** (+307% absolute count). Drivers: NS Phase 5 conjecture work where the gain/tax tether is asserted before formal proof; gp210 consciousness sufficiency claims before the formal-impossibility framing landed; gp211 Lean proof attempts before compile gates rejected them.

- **`overclaimed_scope` rank 1 → rank 3** (-47% absolute count). Drivers: GP-149 I-1 (anti-pattern catalog injection) shipped 2026-04-24; the pattern is now caught earlier in the loop. The drop is consistent with the I-1 intervention working as intended.

- **`missing_counterfactual` rank 3 → rank 7** (-64%). Drivers: fewer empirical-discovery substrates in new corpus relative to formal-proof and structural-conjecture substrates.

### 2.3 New top-10 entries (no April equivalent)

`unmeasurable_construct`, `unsupported_assumption`, `missing_data`, `unverified_assumption`. These four together account for 171 records across 56 project-occurrences. They cluster around formal-conjecture-without-evidence patterns common in the NS / consciousness / Lean work.

### 2.4 Cross-LLM stability — NOT yet re-tested

GP-151's super-class three-way agreement test ran 2026-04-24 against gpt-4.1-mini / claude-haiku-4.5 / gemini-3.1-flash-lite. The May 4 LLM classifier ran with gemini-2.5-flash-lite only. Cross-LLM consistency for the new top-10 has NOT yet been tested. **Per GP-151 PATH_C_ONLY discipline, the May classifier output should be treated as observability-only until a fresh cross-provider audit lands.**

---

## 3. Pivot effectiveness — per-cluster (refreshed)

813 pivot events across 93 projects. 542 analyzable (others truncated by window or missing pre-score).

| Cluster | N events | p(climb) | Verdict |
|---|---:|---:|---|
| circularity | (high) | 0.69 | Pivots strongly work |
| catastrophic_assumption | (high) | 0.62 | Pivots work (was 0.51 April) |
| causal_assumption | (mod) | 0.60 | Pivots work |
| exhaustiveness_claim | (mod) | 0.39 | Lukewarm (was 0.52 April — REGRESSED) |
| unverified_bound | (mod) | 0.36 | Lukewarm |
| no_thesis_proposed | (mod) | 0.33 | Lukewarm |
| other_unclustered | (high) | 0.32 | Weak |
| tail_generalization | (mod) | 0.28 | Pivots barely work (was -0.7 mean Δ April) |
| harness_defect | (mod) | 0.22 | Tool recovery, not pivot effect |

**Decisive shift:** `exhaustiveness_claim` p_climb dropped from 0.52 → 0.39. This was the GP-149 finding that "pivots work on exhaustiveness over-claims." The May data is more equivocal. Either the April finding was sample-noise, or the substrate-mix shift (more formal-proof, fewer empirical-discovery) reweighted the effect.

**Stable finding:** `tail_generalization` is still the central blindspot. It went from -0.7 mean Δ to 0.28 p_climb. Both metrics consistent with "pivots barely work for this class."

---

## 4. Lollapalooza re-test — VERDICT FLIPPED

**April 24:** Lollapalooza REFUTED. KS test on 4 features (primitive_count, dimension_term_count, active_constraint_count, gate_engagement) all p > 0.05.

**May 4:** Lollapalooza SUPPORTED. KS on the same features, with `active_constraint_count` significant at p = 2.7e-5.

| Feature | April p | May p | Direction |
|---|---:|---:|---|
| primitive_count | 0.95 | 0.95 | Still null |
| dimension_term_count | 0.05 | 0.054 | Marginal |
| active_constraint_count | (was null) | 2.7e-5 *** | NEW SIGNAL |

**Read.** Champion iterations (≥90) now show 8.87 mean active_constraint_count vs 7.37 for mid-bucket (70–89). One additional active constraint per champion iteration. The signal is real and consistent with the GP-149 §3.2 finding that *persistence beats cleverness for ≥90* — champions traverse more constraint-tagged territory.

**Implication for GP-212.** Active-constraint-count is a candidate signal for the substrate-recommender's "this charter has the right shape for ≥90 trajectory" inference. Worth piping into the BRIDGE-1 spec.

---

## 5. Score ceilings — NEW walls observed

| Wall constraint | Wall freq | High freq | Ratio | Source |
|---|---:|---:|---:|---|
| `rubric_dim.implementation_cash-out` | 0.050 | 0.000 | 50× | (project-specific) |
| `rubric_dim.law-packet_ambition` | 0.050 | 0.000 | 50× | (discovery substrate) |
| `rubric_dim.literature_resolution_value` | 0.050 | 0.000 | 50× | (paper-promotion substrate) |
| `rubric_dim.nonclaim_and_resource_safety` | 0.050 | 0.000 | 50× | (governance substrate) |
| `rubric_dim.nullspace_branch` | 0.050 | 0.000 | 50× | **NS Phase 5** |
| `rubric_dim.observable_class_and_matrix_intertwiners` | 0.050 | 0.000 | 50× | **NS Phase 5 — INS-081 family** |

The two NS-related walls (`nullspace_branch` and `observable_class_and_matrix_intertwiners`) are direct empirical confirmation of the operator's substantive Track B work. The mining is now classifying NS-substrate failure modes that were not in the April taxonomy.

---

## 6. Champion trajectory transitions

Top transitions for champion-promoted iterations:

| Transition | N |
|---|---:|
| `other_unclustered → other_unclustered` | 160 |
| `harness_defect → harness_defect` | 34 |
| `other_unclustered → catastrophic_assumption` | 30 |
| `harness_defect → other_unclustered` | (mid) |

**Read.** Champion paths spend a lot of time in unclassified territory before resolving. The `other_unclustered → catastrophic_assumption` transition (30 events) is interesting — it suggests champions often surface a decisive assumption *after* a stretch of unclassifiable critique. Mining the unclustered records sub-class distribution (§2 above) gives a sharper view: many of those would now be classified as `unfalsifiable_claim`, `missing_mechanism`, or `unmeasurable_construct`.

---

## 7. What this changes for GP-212 + GP-213

### GP-212 (gate-package recommender)

- **Phase B (mining hit-rate population) is now feasible.** The May 4 classifier output gives per-class N for the top-10 categories. Several have N ≥ 20 (the seam §7 threshold). Specifically: `unfalsifiable_claim` (53 projects), `missing_mechanism` (40), `overclaimed_scope` (30), `unmeasurable_construct` (24).
- **Cross-LLM check is the bottleneck for Phase C.** Before deploying the recommender's classifier body, a fresh cross-provider audit must run on the May 4 categories.
- **The taxonomy file `docs/concepts/problem_class_taxonomy.md` should be updated with current N counts** in the next refresh.

### GP-213 (operator-role mechanization)

- **BRIDGE-1 (substrate recommender) is feasible** but should wait for cross-LLM audit completion.
- **Active-constraint-count is a candidate input** for the substrate recommender (per §4 above).
- **The `unfalsifiable_claim` cluster is the largest target for kernel intervention.** A potential I-4 intervention: when the runtime classifier detects this class, force a "what would falsify this?" prompt addition to the next mutator turn. Adds to the GP-149 intervention catalog.

---

## 8. Open work

- [ ] Run cross-provider classifier agreement on the May 4 LLM classifier output (gpt-4.1-mini vs claude-haiku-4.5 vs gemini-2.5-flash-lite). Required before any Phase C deployment.
- [ ] Populate per-class hit rates in `docs/concepts/problem_class_taxonomy.md` using the May 4 LLM classifier sub-classes mapped onto the 6 problem classes.
- [ ] Update `weakest_link_classifier.py` (regex runtime) with patterns for `unfalsifiable_claim` (largest new class).
- [ ] Add I-4 candidate intervention proposal to GP-149 intervention catalog: "force falsifiability check when unfalsifiable_claim detected at runtime."
- [ ] Update `EXPERIMENT_TRACK_RECORD.md` with E-row for this refresh + F-row for the decisive shifts (Lollapalooza FLIP, exhaustiveness_claim p_climb regression, NS-class new walls).

---

## 9. Pattern-bank-as-kernel-input (I-5 candidate, surfaced 2026-05-04 via Mini-ZTARE)

While building Mini-ZTARE-2.0 v0.1, a new corpus artifact emerged: a *pattern bank* generated by `scripts/public/mining/build_mini_ztare_pattern_bank.ts`. The bank groups the May 4 LLM classifier's 1,258 classified records by class, samples representative exemplars (redacted), and emits one structured markdown entry per class with N counts, mechanism, exemplar critiques, and a generic killer-question. Output landed at `mini-ztare/corpus/pattern_bank/` (15 entries above N≥10 threshold).

The bank is mining-derived, exemplar-rich, and refreshable on every mining run. This is structurally distinct from `docs/concepts/anti_pattern_catalog.md`, which is hand-curated and abstract. The two are complementary, not redundant:

| Layer | Anti-pattern catalog (existing GP-149 I-1) | Pattern bank (this candidate I-5) |
|---|---|---|
| Source | Operator-curated, manually-written | Auto-generated from LLM classifier on debate logs |
| Granularity | Abstract families (9 canonical) | 15+ classes with mining N counts |
| Content | Pattern name + mechanism + boardroom translation | Pattern name + mechanism + 5 redacted real exemplars + N + project count |
| Refresh cadence | Operator-driven, manual | Auto-refreshable when mining re-runs |
| Use today | `inject_antipattern_catalog: hardkill/ceilingbreaker/both` | None (kernel doesn't ingest yet) |

**The candidate intervention I-5** is a new rubric flag like `inject_pattern_bank_for_class: <class_name>` (or `inject_pattern_bank: filtered_to_substrate_class | full | off`). When set, the autoresearch loop appends pattern-bank exemplars relevant to the substrate's class to the mutator's grounding payload — alongside the abstract catalog — giving the mutator concrete failures to avoid rather than only abstract guards.

**Cross-LLM constraint applies.** Because the pattern bank's class labels come from the LLM classifier, GP-151's PATH_C_ONLY discipline applies to *automated routing on those labels*. The bank itself is safe to inject (same data, exemplar-shaped). But auto-selecting *which class* to inject must pass the cross-provider audit before going live. Until then, manual operator selection of a class.

**Where this lands.** I-5 is a candidate intervention for the GP-149 catalog, not a new seam. The pattern bank itself is operator-private (the script lives in `scripts/public/mining/build_mini_ztare_pattern_bank.ts`, output is gitignored in Mini-ZTARE). The committed Mini-ZTARE corpus uses the bank only via embeddings.json (vectors + redacted text), not raw classifier output.

**Implementation sketch (pre-spec):**
1. Read `analytics/public/queries/pattern_bank_redacted/*.md` (operator-private generation step, parallel to mini-ztare's gitignored copy).
2. New rubric flag `inject_pattern_bank: "off" | "manual" | "auto_by_substrate_class"`. `auto_by_substrate_class` is gated on cross-provider audit ≥75% three-way (per GP-151 super-class threshold).
3. Autoresearch loop reads the flag, optionally appends class-filtered bank entries to grounding payload.
4. Operator-override log captures when operator sets the flag manually vs. accepts auto.

**Why this matters for GP-213.** BRIDGE-1 (substrate-recommender) can recommend the right pattern-bank class to inject as part of its gate package. The bank becomes a kernel-side asset GP-212 + GP-213 both reference. This is also one of the "obvious bridges hiding in plain sight" GP-213 names: structured exemplar grounding from the corpus you already have.

**What changed by surfacing this:** the kernel's existing failure-mode injection (I-1) is *abstract*. The pattern bank adds *exemplar-grounded* injection. Operator instinct that "we already inject failure modes in autoresearch" is correct for the abstract layer; the bank adds a concrete layer the kernel doesn't currently use.

Status: surfaced as a candidate, not yet specced. Promote to a formal I-5 spec when GP-212 Phase B ships and per-class hit rates exist.

---

*Refresh report v0 written 2026-05-04 in auto mode. Companion to GP-149 seam. Refresh again after cross-provider audit lands.*

---

## 10. Cross-provider classifier audit — RESULT (2026-05-04, post-run)

The audit landed. **It fails the GP-151 PATH_C_ONLY cross-LLM gate.**

**Setup**
- Sample: 100 random records from `analytics/public/queries/weakest_link_llm_classify_2026-05-04_v3.json`
- Providers: `openai/gpt-4.1-mini`, `anthropic/claude-haiku-4.5`, `google/gemini-2.5-flash-lite`
- Output: `analytics/public/queries/classification/cross_provider_classifier_agreement_2026-05-04.json`

**Headline numbers**
- Three-way agreement rate: **42 %** (verdict band: `FAILS_cross_llm_validation` < 0.60)
- Pairwise Cohen's κ:
  - GPT-4.1-mini ↔ Claude-Haiku-4.5: 0.566 (moderate)
  - GPT-4.1-mini ↔ Gemini-2.5-flash-lite: 0.567 (moderate)
  - Claude-Haiku-4.5 ↔ Gemini-2.5-flash-lite: 0.481 (moderate-low)

**Per-class stability (subset, sorted by `n_at_least_one`)**

| Class | n at least one | three-way agree | stability |
|---|---:|---:|---:|
| `unsupported_assumption` | 32 | 12 | **0.375** |
| `missing_counterfactual` | 17 | 0 | **0.0** |
| `parameter_sensitivity` | 16 | 4 | 0.250 |
| `overclaimed_scope` | 15 | 5 | 0.333 |
| `overclaimed_exclusivity` | 15 | 4 | 0.267 |
| `non_identifiability` | 14 | 4 | 0.286 |
| `missing_mechanism` | 13 | 3 | 0.231 |
| `catastrophic_fit_failure` | 13 | 7 | **0.538** ← strongest signal |
| `temporal_mismatch` | 6 | 2 | 0.333 |
| `missing_baseline` | 5 | 0 | 0.0 |
| `unfalsifiable_claim` | 5 | 0 | 0.0 |

(`unfalsifiable_claim` shows up far less than the §7 finding suggested because that count was *ANY-classifier*, not *all-three-agree*. The previous "53 projects" figure was inflated by classifier-specific over-firing.)

**Implications**

1. **GP-212 Phase C (auto-routing of gate packages by predicted class) is blocked.** The classifier signal does not pass cross-LLM validation. Phase B (manual operator selection from a populated taxonomy) remains feasible.

2. **GP-213 BRIDGE-1 (substrate-recommender) cannot use class predictions for routing.** It can still recommend substrates from operator-supplied class labels, but auto-detection from debate logs is unsafe.

3. **I-5 (pattern-bank-as-kernel-input) — the `auto_by_substrate_class` mode is dead.** The `manual` mode (operator selects class, kernel injects exemplars) survives unchanged. The bank itself is intact; only auto-routing on classifier labels fails.

4. **`catastrophic_fit_failure` is the only reliable class.** Stability 0.538 is the highest in the audit. This is the only class where automated routing might survive a higher bar; even at 0.538 it is below GP-151's 0.60 threshold but is the most defensible single-class auto-route candidate.

5. **`missing_counterfactual`, `missing_baseline`, `unfalsifiable_claim` have stability 0.0.** These three classes are essentially classifier hallucinations from the operator's perspective: each provider fires on different records. Manual operator review remains the only valid use.

**What this changes about the pattern bank**

The pattern bank is *still safe* to use as exemplar grounding. The 15 entries are real redacted critiques from real debate logs; the corpus integrity is unaffected. What fails is *automated dispatch by predicted class*. The mini-ztare retrieval (cosine similarity over query embedding → top-k exhibits) is unaffected — it does not use the classifier labels for routing, only for grouping during bank construction.

**Updated I-5 status**

- I-5 `manual` mode: green-light. Operator-supplied class label, kernel injects bank entries.
- I-5 `auto_by_substrate_class` mode: red-light pending cross-LLM stability ≥ 0.60 on the routed class. Only `catastrophic_fit_failure` is plausibly close.
- I-5 `single_class_only_auto: catastrophic_fit_failure` mode: amber. Worth a small experiment (does injecting `catastrophic_fit_failure` exemplars at runtime actually move the apparent failure rate of that class?). If yes, it is the first auto-routed kernel intervention from mining; if no, the whole auto-routing branch is buried for v0.

**Action items**
- [ ] Promote I-5 to its own seam (`GP-214_pattern_bank_kernel_injection_seam.md`) with manual mode green-lit, auto modes gated.
- [ ] Update `docs/concepts/problem_class_taxonomy.md` to include the cross-LLM stability column alongside N counts. Stability < 0.60 means the class is *operator-only* for now.
- [ ] BRIDGE-1 + BRIDGE-2 specs scope to operator-supplied class labels in v0; auto-detection deferred.
- [ ] Add F-row to `EXPERIMENT_TRACK_RECORD.md`: "May 4 cross-LLM audit failed at 42 % three-way; auto-routing on classifier labels deferred; manual-mode I-5 remains green."

This is a **decisive finding**, not a setback. It tells us where the corpus signal is real (manual review by class) and where it is not (auto-classification with confidence). The kernel architecture survives; the boundary between operator-mediated and machine-mediated routing just moved.
