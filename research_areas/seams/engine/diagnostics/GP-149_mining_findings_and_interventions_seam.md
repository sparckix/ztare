# GP-149 — Mining Findings & Interventions (Seam)

> **Seam metadata** · `seam_id:` GP-149 · `track:` engine · `status:` active draft 2026-04-24; first findings pass + first interve · `last_updated:` 2026-05-09


**Status:** active draft 2026-04-24; first findings pass + first intervention batch
**Owner:** mining-derived-apparatus-discipline
**Depends on:** GP-148 (mining infrastructure), GP-086 (gate harness / cage discipline), GP-053 (seam-spec invariant), GP-104 (rubric authoring), INV-10
**Triggered by:** 2026-04-24 first-pass meta-analysis of the enriched archive (1825 records, 84 projects) + LLM sub-classification of the 842 previously-unclustered weakest-points + four operator-directed backtests

This seam is the **findings + interventions** counterpart to GP-148 (which is the *infrastructure* for mining). GP-148 produces the archive and queries. GP-149 records what we learned and what we changed as a result. Keeping these separate so:
- GP-148 stays stable (infrastructure).
- GP-149 evolves as more mining passes deepen the picture.
- Future agents reading "what did we learn from mining" find it in one place.

---

## 1. Inputs — queries the findings rest on

All files under `analytics/public/queries/`:

| Query | Source script | Records touched |
|---|---|---|
| `weakest_link_clusters_2026-04-24.json` | `scripts/public/mine_weakest_link_taxonomy.py` | 1825 regex-classified |
| `weakest_link_llm_subclasses_2026-04-24.json` | `scripts/public/mine_weakest_link_llm_classify.py` | 842 LLM-reclassified (the `other_unclustered` bucket) |
| `pivot_effectiveness_2026-04-24.json` | `scripts/public/mine_pivot_effectiveness.py` | 647 pivot events across 60 projects |
| `climb_triggers_2026-04-24.json` | `scripts/public/mine_climb_triggers.py` | 260 jumps with Δscore ≥ +20 |
| `lollapalooza_test_2026-04-24.json` | `scripts/public/mine_lollapalooza_hypothesis.py` | 93 high-bucket + 290 mid-bucket |
| `score_ceilings_2026-04-24.json` | `scripts/public/mine_score_ceilings.py` | 137 groups, 128 with scores |

Backtests run in GP-149-authoring session:
- **B1:** LLM ↔ regex overlap and novel-class enumeration
- **B2:** gp145 run-1 against taxonomies (surfaced archive-freshness gap)
- **B3:** weakest-link class frequency by score bucket (high vs mid vs low) → lift analysis
- **B4:** Lollapalooza re-test under distinct-classes-per-group feature

## 2. Findings (decisive, data-supported)

### 2.1 LLM classifier decomposed the 842 "other_unclustered" into 15 sub-classes

Top five (65% of the 842, 22–48 projects each):

| Sub-class | N | Projects | Description |
|---|---|---|---|
| `overclaimed_scope` | 187 | 48 | Thesis generalizes beyond evidence envelope |
| `missing_mechanism` | 147 | 48 | Describes WHAT without causal HOW |
| `missing_counterfactual` | 89 | 36 | No rival explanation considered |
| `parameter_sensitivity` | 81 | 30 | Fragile to threshold / bound choice |
| `unfalsifiable_claim` | 40 | 22 | No operational test |

All five are **epistemic-discipline classes** (not domain-specific). They cross many projects.

Novel classes the regex taxonomy did not have any equivalent for:
- `missing_counterfactual` (89)
- `missing_baseline` (28)
- `unmeasurable_construct` (24)
- `overclaimed_exclusivity` (10, outlier concentrated in 1 project)

Known-class overlaps (LLM class ↔ existing regex cluster):
- `overclaimed_scope` ↔ `tail_generalization` + `exhaustiveness_claim`
- `missing_mechanism` ↔ `catastrophic_assumption` + `unverified_bound`
- `parameter_sensitivity` ↔ `unverified_bound`
- `temporal_mismatch` ↔ `tail_generalization`

### 2.2 Pivot effectiveness is CLUSTER-DEPENDENT

From `pivot_effectiveness_2026-04-24.json`:

| Cluster | N | p_climb | p_regress | mean Δ | verdict |
|---|---|---|---|---|---|
| `catastrophic_assumption` | 43 | 51.2% | 9.3% | **+14.4** | Pivots work |
| `exhaustiveness_claim` | 33 | 51.5% | 3.0% | **+10.4** | Pivots work (REFUTES earlier gp147-motivated prior that said "pivots don't fit exhaustiveness") |
| `other_unclustered` | 233 | 25.8% | 9.4% | +7.6 | Weak positive (needs sub-classification) |
| `harness_defect` | 80 | 25.0% | 0.0% | +14.7 | Tool-recovery, not pivot effect |
| `tail_generalization` | 25 | 28.0% | 20.0% | **−0.7** | **Pivots actively fail** |
| `unverified_bound` | 18 | 38.9% | 27.8% | +1.4 | Pivots lukewarm (matches gp140/gp145 pattern) |
| `causal_assumption` | 6 | 50.0% | 0.0% | +13.2 | Insufficient N |
| `circularity` | 6 | 50.0% | 0.0% | +24.2 | Insufficient N |

**Decisive**: pivots work on catastrophic structural errors and exhaustiveness over-claims. They **do not work** on tail_generalization and are lukewarm on unverified_bound.

### 2.3 Lollapalooza REFUTED under both feature sets

Two independent features tested:

- **Original (GP-148 P1):** thesis-structural complexity (primitive_count, dimension_terms, constraint_count). All three KS tests p > 0.05. Refuted.
- **B4 (this seam):** distinct-weakest-link-classes per iter. Champion groups (≥90 max) have MORE distinct classes (avg 9.97) across MORE iterations (avg 27.8), not fewer.

**Implication:** the "90+ = 3+ orthogonal constraints simultaneously satisfied" framing is **not supported by data**. High-score trajectories are characterized by *persistence + class-cycling breadth*, not *structural-feature convergence*. Retire the Lollapalooza framing from future charter / rubric / evidence text.

### 2.4 Structural-blocker vs ceiling-breaker dichotomy (B3)

Weakest-link class frequency in iterations at different score levels, with lift = high% / low%:

**Structural blockers (lift ≪ 1, absent from high-score iters):**

| Class | High% | Low% | Lift |
|---|---|---|---|
| Circularity | 0.0% | 6.1% | **0.00** |
| Harness defect | 1.4% | 21.8% | 0.06 |
| Unfalsifiable claim | 1.4% | 2.7% | 0.51 |

**Ceiling-breakers / residual critiques (lift > 1, MORE common in high iters):**

| Class | High% | Mid% | Low% | Lift |
|---|---|---|---|---|
| `missing_counterfactual` (LLM) | 9.5% | 7.2% | 3.9% | 2.41 |
| `overclaimed_scope` (LLM) | 15.6% | 12.9% | 9.6% | 1.63 |
| Catastrophic assumption | 10.9% | 14.4% | 7.1% | 1.53 |
| `parameter_sensitivity` (LLM) | 6.8% | 3.7% | 4.8% | 1.42 |
| Exhaustiveness claim | 2.7% | 8.7% | 2.0% | 1.38 |
| Unverified bound | 6.1% | 7.4% | 4.7% | 1.30 |
| Tail generalization | 8.2% | 7.4% | 6.3% | 1.29 |

**Interpretation**: the judge's weakest-link at a high score is the BEST-AVAILABLE critique, not the thesis's worst flaw. High-score iters engage with these ceiling-breaker classes and score well despite the residual critique. Low-score iters die on structural-blocker classes before reaching the ceiling-breaker regime.

### 2.5 Champion-trajectory profile (B4 side finding)

| Bucket | Groups | Avg iters | Avg distinct classes | Class-per-iter ratio |
|---|---|---|---|---|
| Champion (≥90) | 30 | 27.8 | 9.97 | 0.500 |
| Good (75-89) | 21 | 19.8 | 7.57 | 0.538 |
| Mid (50-74) | 11 | 17.3 | 6.09 | 0.364 |
| Low (<50) | 15 | 17.7 | 4.53 | 0.444 |

Champions run **longer** AND see **more distinct weakest-link classes**. Not random: earning ≥90 requires working through ~10 classes over ~28 iters. Short-run, few-classes trajectories don't reach champion.

### 2.6 Score ceilings reveal rubric-dim walls

From `score_ceilings_2026-04-24.json` wall analysis (70–85 range = wall_range):

Most-over-represented constraints in wall-range groups:
- `rubric_dim.class-selection_independence`
- `rubric_dim.detector_specificity`
- `rubric_dim.farther-tail_prediction`

`farther-tail_prediction` wall directly confirms tail_generalization as the convergent blindspot — four independent queries (LLM class, pivot effectiveness, climb triggers, ceiling walls) all point at the same structural gap.

## 3. Cross-query synthesis (the convergent findings)

### 3.1 Tail-generalization is THE central blindspot

Four queries point at the same thing:

1. Pivot effectiveness: only class with negative mean Δ (−0.7)
2. Climb triggers (Ticket E from GP-148): biggest median jump (+43.4) when fixed
3. LLM classifier: two top-5 sub-classes (`overclaimed_scope` 187, `parameter_sensitivity` 81) are tail-generalization variants
4. Score ceilings: `rubric_dim.farther-tail_prediction` is an over-represented wall constraint

No other failure class shows this profile across four independent queries.

### 3.2 Persistence beats cleverness for reaching ≥90

Champion groups characterized by 27.8 avg iterations vs 17.7 for low-score groups. Champions encounter ~10 distinct classes vs ~4-5. The apparatus earns high scores through **grinding through critique cycles**, not through a single "right" thesis formulation.

### 3.3 Two kinds of anti-patterns require different treatment

Structural blockers need AVOIDANCE (hard-kill inject). Ceiling-breakers need ENGAGEMENT (the judge WILL flag these; the thesis must address them head-on). Treating them as a single catalog to avoid is wrong.

## 4. Intervention catalog — pros / cons / recommendation per item

All interventions are **opt-in via rubric flag**, default safe. Existing projects unaffected.

### I-1: Anti-pattern catalog injection into evidence text

**Action**: create `docs/concepts/anti_pattern_catalog.md` (canonical reference) split into hard-kill and ceiling-breaker lists. Add rubric flag `inject_antipattern_catalog: bool`. When true, autoresearch_loop appends the catalog to grounding_payload before mutator call.

**Pros:**
- Directly attacks the two most common failure modes (overclaimed_scope 187, missing_mechanism 147).
- Pedagogical: the mutator sees what the judge will flag before writing the thesis.
- Opt-in; no risk to existing runs.
- Near-zero infrastructure cost.

**Cons:**
- Risk of prompt bloat: adding ~1 KB to every mutator prompt. Small but nonzero.
- Risk of over-cautious theses: mutator may become so focused on avoiding anti-patterns that it stops proposing bold structures.
- Ceiling-breaker items, if mistakenly framed as avoidance, could degrade quality (per B3 data).

**Recommendation: IMPLEMENT.** Split the catalog into two sub-sections with distinct wording: hard-kill as "these kill any thesis," ceiling-breaker as "the judge WILL flag these at high scores; engage head-on." This splits B3's dichotomy correctly. Default rubric flag to false; enable on gp140-class / gp145-class substrates first to validate before global default.

### I-2: Class-aware stagnation threshold

**Action**: add rubric flag `min_distinct_classes_before_stagnation: int` (default 0 = off). When set and the current run has seen fewer distinct weakest-link classes than this threshold, suppress stagnation-triggered pivots regardless of stagnation_count.

**Pros:**
- B4 shows champions need ~10 classes seen. Killing a run at iter 3-5 with stagnation_count=3 may prematurely abort prospective champions.
- Data-supported: the distribution difference between champion (10 classes) and low (4-5 classes) is significant.

**Cons:**
- Risk of runaway runs: if the rubric mis-specifies this flag, a bad run could iterate indefinitely seeing "new" classes.
- Requires runtime classification of weakest_point strings, which adds a small per-iter cost.

**Recommendation: IMPLEMENT behind opt-in flag with a safety cap.** Default 0 (off). When set, cap at min_distinct_classes_before_stagnation ≤ 8 (above this, the data says you've passed the champion threshold anyway). Safety cap prevents pathological config.

### I-3: Pivot-skip heuristic for ineffective classes

**Action**: add rubric flag `skip_pivot_on_ineffective_classes: bool` (default false). When true, before firing topological_pivot_emergency, runtime-classify the current weakest_point. If class ∈ {`tail_generalization`, `unverified_bound`}, skip the pivot and emit a loop event noting the skip + the classified weakest-link class.

**Pros:**
- Pivots on tail_generalization have mean Δ = −0.7 (they actively hurt).
- Saves compute on inevitable score regression from applying the wrong intervention.
- Aligned with the emerging "class-aware routing" data from GP-148 Ticket B.

**Cons:**
- Regex classification is approximate. Mis-classifying a weakest_point as tail_generalization when it isn't would skip a useful pivot.
- Only 25 and 18 events for the two target classes — moderate sample size; hypothesis could still flip with more data.
- Removing one intervention without replacement leaves the mutator with no tool for those classes — downstream we'd need a class-appropriate replacement.

**Recommendation: IMPLEMENT behind opt-in flag + LOG-ONLY MODE DEFAULT.** Two modes: `"observe"` (classify and log but still fire pivot) or `"suppress"` (skip pivot entirely when classified ineffective). Default to `"observe"` on first rollout to collect classification-accuracy data before enabling suppress.

### I-4: Champion-trajectory-sequence mining script

**Action**: new `scripts/public/mine_champion_trajectory_sequence.py`. For each champion group (max_score ≥ 90), extract the sequence of weakest-link classes per iter. Aggregate common transitions (class-to-class Markov chain). Report: does a common path exist (catastrophic → overclaim → mechanism → tail → counterfactual?)?

**Pros:**
- Validates or refutes the "persistence + class-cycling breadth" hypothesis with finer resolution.
- If a common sequence exists, it's a template for mutator prompt design.
- Zero infrastructure risk — read-only script.

**Cons:**
- Only 30 champion groups — low statistical power for Markov chains.
- Sub-class labels are currently only available for the 842-reclass records; 983 regex-labeled are coarser.

**Recommendation: IMPLEMENT as Stage-2-follow-on.** Use what we have; note the power limitation in the output.

### I-5: Re-run Stage 1 extractor

**Action**: run `python3 scripts/public/mine_trajectories.py` to capture post-archive runs (gp140 iter 10+, gp145 run-1, gp147 iter 5+, etc.). Re-run enrichment. Re-run Stage 2 queries afterward.

**Pros:**
- Archive freshness is a correctness precondition for Stage 2.
- gp145 being absent from the current corpus means any Lollapalooza / tail-generalization conclusion misses the freshest case.

**Cons:**
- Stage 2 queries would need re-running, increasing compute cost.
- LLM classifier re-run required (user's API quota) — small but nonzero cost.

**Recommendation: IMPLEMENT.** User action or scheduled job. Log as routine hygiene.

### I-6: Full-corpus LLM classification (not just the 842)

**Action**: extend `mine_weakest_link_llm_classify.py` to re-classify ALL 1825 records (currently only 842). Use same 15-class taxonomy.

**Pros:**
- Current regex labels may mis-classify records into wrong regex buckets; LLM re-pass catches that.
- Gives a single authoritative label per iter for downstream mining.
- Enables cross-validation between regex and LLM on the already-labeled 983 records.

**Cons:**
- ~2x the LLM cost of the first pass (1825 records vs 842).
- Operator time / quota.

**Recommendation: IMPLEMENT after I-5 archive refresh.** ROI clearly positive.

### I-7: Retire Lollapalooza framing from future charters

**Action**: audit remaining memory entries / charters / evidence.txt files for "Lollapalooza" / "3 orthogonal constraints" / similar framings. Update to reflect the refuted hypothesis + persistence + class-cycling finding.

**Pros:**
- Zero code risk. Documentation-only.
- Prevents propagating a refuted hypothesis into new projects.

**Cons:**
- None material.

**Recommendation: IMPLEMENT (memory sweep).** Low-cost cleanup.

## 5. Implementation order (INV-10 compliant)

1. Seam converges (this doc).
2. Canonical anti-pattern catalog doc (I-1 prerequisite).
3. Runtime weakest-link classifier module (I-2, I-3 prerequisite).
4. Autoresearch changes: I-1, I-2, I-3 — all behind rubric flags, default safe.
5. New Stage 2 script: I-4.
6. Archive refresh + LLM re-classification: I-5, I-6 — operator action.
7. Documentation sweep: I-7.
8. Spec each intervention when the rubric flag is opted-in by a specific project.

## 6. Insertion points (per-file)

| Change | File | Line(s) (current HEAD) | Type |
|---|---|---|---|
| I-1 catalog doc | `docs/concepts/anti_pattern_catalog.md` | NEW FILE | doc |
| I-2, I-3 classifier | `src/ztare/validator/weakest_link_classifier.py` | NEW FILE | kernel |
| I-1 injection | `autoresearch_loop.py` ~ line 1976 (grounding_payload assembly) | INSERT | kernel |
| I-2 stagnation gate | `autoresearch_loop.py` ~ line 3219 onward (stagnation_count evaluation) | INSERT | kernel |
| I-3 pivot skip | `autoresearch_loop.py` ~ line 3395-3403 (topological_pivot_emergency handler) | INSERT | kernel |
| I-4 script | `scripts/public/mine_champion_trajectory_sequence.py` | NEW FILE | script |
| I-7 memory sweep | `/projects/.../memory/*.md` | EDIT | memory |

## 7. Open questions deferred to project-specific specs

- **OQ-1**: For I-1, should the catalog injection be weight-adaptive (more prominent when stagnation_count is high)? Or always-same weight? First rollout answers this via telemetry.
- **OQ-2**: For I-2, what's the right default min_distinct_classes threshold? Data says 7 for good groups, 10 for champions. Start with 6 (covers good + champion band) and tune.
- **OQ-3**: For I-3 suppress mode, what's the class-appropriate replacement intervention for tail_generalization / unverified_bound? (This is downstream — GP-149b will handle.)
- **OQ-4**: For I-4, is 30 champion groups enough sample for Markov chain analysis? If not, what's the minimum? Script emits insufficient-evidence flag.
- **OQ-5**: Should the LLM classifier (I-6) use the 15-class taxonomy as fixed labels, or allow new-class discovery? Fixed for first pass; allow growth on second.

## 8. What this seam is NOT

- Not a new mining infrastructure seam (that's GP-148).
- Not a kernel-integration seam for continuous-chaotic solvers (that's GP-143).
- Not a new-science-claim discipline seam (that's GP-144).
- IS: the findings + intervention record triggered by the first real mining pass, documented for the next agent to pick up.

## 8a. Cross-judge stratification (2026-04-24, operator-flagged metadata utilization)

The archive records `(mutator_model_id, judge_model_id)` per iter. Earlier queries aggregated across all pairs. Stratified re-analysis reveals the Oracle Illusion is measurable, not hypothetical.

**Score-distribution by judge family (1859-record corpus):**

| Judge | N | Mean | ≥85-rate | Shape |
|---|---|---|---|---|
| gpt-4.1 | 1,107 | 42.2 | 10.2% | Broad continuous |
| gemini-2.5-flash | 245 | 18.5 | 6.9% | Compressed low |
| o3 | 109 | 48.7 | 4.6% | Harsh at high end |
| claude-sonnet | 55 | 30.8 | 12.7% | Bimodal (harsh median, broad tail) |

**Same mutator (o3) under different judges: mean score 49.2 (o3-judge) vs 42.6 (gpt-4.1-judge) vs 15.4 (claude-sonnet-judge).** Nearly 3× differential same-mutator. Not a judge-agnostic scoring regime.

**B3 dichotomy under stratification — replication results:**

*Structural-blocker classes (lift = 0.00 across ALL 4 judge families):*
- Circularity, Harness defect, Tail generalization, Unverified bound, Catastrophic assumption, Exhaustiveness claim, Unfalsifiable claim

**→ These 7 classes are CROSS-JUDGE VALIDATED.** Promotion to kernel-default anti-pattern injection is safe.

*Ceiling-breaker classes (direction flips between judges):*
- `missing_mechanism`: lift 0.84 under gpt-4.1 (negative signal) vs 2.43 under o3 (strong positive) — FLIPPED
- `parameter_sensitivity`: lift 0.83 under gpt-4.1 (negative) vs 6.00 under claude-sonnet (strong positive) — FLIPPED
- `overclaimed_scope`: 1.30 gpt-4.1 / 6.00 claude-sonnet / 0.00 others — mixed with insufficient N
- `missing_counterfactual`: 1.92 gpt-4.1 / insufficient elsewhere

**→ These classes are JUDGE-SPECIFIC.** Must NOT be promoted to universal anti-pattern catalog. Rubric flag `inject_antipattern_catalog` split into `"hardkill"` / `"ceilingbreaker"` / `"both"` to reflect this.

**Discipline update:** any future stratified mining query should split by judge family first, aggregate only across replicated patterns. The `scripts/public/mine_judge_stratified.py` script implements this. Output: `analytics/public/queries/classification/judge_stratified_analysis_2026-04-24.json`.

## 8b. Iatrogenic-risk discipline (2026-04-24 operator-flagged)

Gemini's Oracle Illusion warning plus operator observation: the runtime classifier's regex patterns come from judge-written weakest-point strings. Patterns reflect the judge's aesthetic, NOT physical reality. Our interventions therefore risk:

- **Goodhart the catalog:** mutator learns to avoid listed weakest-point strings without actually writing better theses; rate metrics drop, score distribution doesn't shift.
- **Selection bias in pivot-suppress:** only tail_generalization iters where pivot wasn't fired become observable; underlying pivot-effect becomes unmeasurable.
- **Induced cycling:** class-aware stagnation forces longer trajectories; we observe "more class diversity" by construction, not by genuine critique progression.

**Discipline in response:**

1. **Cross-judge validation is a prerequisite for any kernel-promotion of these heuristics.** A pattern that holds only under o3 judging is o3-specific, not structural. Before moving any intervention from opt-in to default-on, we must observe the same effect direction under ≥2 judge families (o3, gpt-4.1, claude-opus, gemini-pro).

2. **Single-judge-family mined data is suggestive, not actionable for kernel changes.** Mining findings become *candidate* patterns. Promotion to default behavior requires multi-judge confirmation.

3. **Score distribution shifts are the real outcome metric, not weakest-link frequency changes.** A 30% drop in `missing_mechanism` frequency means nothing if median score doesn't move. Rewrite Popper pre-registrations (§9) to measure score deltas, not pattern deltas.

4. **For pivot-ineffective-class mode: stay in "observe" indefinitely until cross-judge data exists.** Suppress mode would create selection bias that makes the suppression-vs-no-suppression counterfactual unrecoverable.

5. **Anti-pattern catalog injection: monitor for Goodhart signatures.** If theses that see the catalog show DIFFERENT weakest-point vocabulary but same score distribution, mutator is gaming the list rather than engaging the substance. Roll back and redesign.

## 9. Popper pre-registration for intervention outcomes

If I-1 anti-pattern catalog injection is effective, we should see (REVISED per §8b to measure score distribution, not pattern frequency):
- **Median score at iter 5 increase by ≥ 10 points** on opted-in projects vs. baseline. This is the primary outcome. Weakest-link frequency changes alone are suspect for Goodhart.
- Score at iter 5 distribution SHIFTS right (not just mean; full distribution shape). Test via two-sample KS.
- **Cross-judge validation:** effect direction replicates under a second judge family (o3 → gpt-4.1 or claude-opus).
- Anti-Goodhart check: weakest-link vocabulary on high-score opted-in iters should not be SUSPICIOUSLY different from baseline high-score iters (if it is, mutator is gaming the catalog). Qualitative operator review of 3 random high-score opted-in iters.

If I-2 class-aware stagnation is effective, we should see:
- Proportion of runs reaching ≥85 increase on projects that opt in, controlling for the same substrate.
- No increase in total iteration count beyond a cap (proving the threshold doesn't cause runaways).

If I-3 pivot-skip is effective, we should see:
- When in `"observe"` mode: classification accuracy ≥ 70% on the 25 tail_generalization events (check against LLM ground truth).
- When in `"suppress"` mode: mean Δ on tail_generalization-classified iters improves from −0.7 to ≥ 0 (at minimum, stops hurting).

Failure of any pre-registered prediction → roll back the intervention, document lesson in memory.

## 10. Convergence declaration

This seam is **draft, open for comment**. It documents the full mining pass, pros / cons / recommendations per intervention, and insertion points. Implementation can proceed on I-1, I-2, I-3 as they are gated by rubric flags (default safe) and cover no kernel contract not already extended by prior GPs.

Operator or another agent reviewing this: comment + edit the seam; do NOT merge the interventions until the seam has at least one review round.
