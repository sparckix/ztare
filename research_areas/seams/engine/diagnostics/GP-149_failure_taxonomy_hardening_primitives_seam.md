# GP-149: Failure Taxonomy Hardening Primitives

> **Seam metadata** · `seam_id:` GP-149 · `track:` engine · `status:` OPEN - debate required before implementation · `last_updated:` 2026-05-09


**Status:** OPEN — debate required before implementation  
**Opened:** 2026-04-24  
**Trigger:** GP-148 Stage 2+3 mining results (1,825 iterations, 84 projects, 21 failure families)  
**Depends on:** GP-148 (void mining pipeline), GP-133 R4 (Newton-mode)  
**Owner:** principal  

---

## 1. Situation

GP-148 Stage 2 (deterministic keyword clustering) + Stage 3 (LLM classification of the 842-record unclustered bucket) produced a 21-family failure taxonomy across the full ZTARE corpus. Three findings drive this seam:

1. **Three failure families have zero apparatus coverage and high frequency** (overclaimed_scope=187, missing_counterfactual=89, tail_generalization=116). The engine has no gate, primitive, or pivot that addresses these.

2. **Pivots actively fail on tail_generalization** (mean delta = -0.7, only 28% climb rate). Yet when anything else fixes a tail_generalization weakness, the score jump is the biggest in the corpus (median +43.4, Ticket E). This is the highest-leverage blind spot.

3. **Newton-mode Generative Yield already addresses missing_mechanism** (147 hits). This validates the GP-133 R4 design — the dimension was correctly identified as a gap before the data confirmed it.

---

## 2. Combined Failure Taxonomy (reference)

Source: `analytics/public/queries/classification/weakest_link_clusters_2026-04-24.json` (Stage 2) + `analytics/public/queries/classification/weakest_link_llm_subclasses_2026-04-24.json` (Stage 3).

| Family | N | Projects | Source | Apparatus coverage |
|---|---|---|---|---|
| harness_defect | 262 | 32 | keyword | Existing (infrastructure bugs, shrinks as fixed) |
| **overclaimed_scope** | **187** | **48** | **llm** | **NONE** |
| catastrophic_assumption | 157 | 44 | keyword | Pivots work (51% climb, +14.4) |
| **missing_mechanism** | **147** | **48** | **llm** | **Newton-mode Generative Yield (shipped GP-133 R4)** |
| **tail_generalization** | **116** | **23** | **keyword** | **NONE — pivots FAIL here (-0.7 delta)** |
| null_weakest_point | 110 | — | keyword | Data quality issue (empty field) |
| unverified_bound | 94 | 35 | keyword | Pivots mixed (39% climb, 28% regress) |
| **missing_counterfactual** | **89** | **36** | **llm** | **NONE** |
| **parameter_sensitivity** | **81** | **30** | **llm** | **Partial (prediction-stability in compress_champion)** |
| circularity | 72 | — | keyword | Existing (climb from 0, harness recovery) |
| exhaustiveness_claim | 62 | — | keyword | Pivots work (52% climb, +10.4) — my prior refuted |
| unfalsifiable_claim | 40 | 22 | llm | None (lower priority, N=40) |
| causal_assumption | 39 | — | keyword | Partial (catastrophic_assumption overlap) |
| missing_baseline | 28 | 17 | llm | None |
| unmeasurable_construct | 24 | 14 | llm | None |
| temporal_mismatch | 23 | 14 | llm | None |
| no_thesis_proposed | 20 | — | keyword | N/A (mutator failure) |
| generalization_overclaim | 19 | — | keyword | Partial (farther-tail gate) |
| definition_ambiguity | 16 | 10 | llm | None |
| model_class_restriction | 14 | — | keyword | Grammar ceiling (known) |
| overclaimed_exclusivity | 10 | 1 | llm | None (single-project) |

**Bold** = candidates for new primitives.

---

## 3. Three Candidate Hardening Primitives

### Candidate A: Scope-Claim Auditor

**Target family:** `overclaimed_scope` (187 hits, 48 projects — largest LLM-classified cluster)

**What it is:** A post-judge gate that detects when the thesis claims generality beyond the evidence range. Compares the claimed scope of the thesis (e.g., "for all n > 10", "holds universally") against the actual evidence coverage (visible range, holdout range).

**Implementation sketch:**
- Parse thesis.md for scope-claiming language (regex: "for all", "universally", "in general", "for any", "always holds")
- Compare against evidence.txt range boundaries
- Flag when claimed scope exceeds 10x the evidence range without farther-tail support
- Gate output: `scope_overclaim_ratio = claimed_range / evidence_range`
- Fire when ratio > 10 and no farther-tail gate passes

**Where it lives:** `src/ztare/gates/scope_claim_auditor.py`, called from `global_gates.py`

**Pros:**
- Addresses the single largest unserved failure family (187/1825 = 10.2%)
- Deterministic — regex + range comparison, no LLM call
- Low blast radius — it's a flag, not a score override (operator decides threshold)
- Cross-substrate: works for both quantitative (range comparison) and qualitative (scope language detection)

**Cons:**
- Regex for scope-claiming language will have false positives ("for all" in a mathematical context may be legitimate)
- Thesis authors may learn to avoid flagged language without actually narrowing scope (Goodhart risk)
- May overlap with existing `generalization_overclaim` keyword cluster (19 records) — could merge

**Risk:** Low. It's a detection gate, not a score mutator. Worst case: false positive flags that operators ignore.

**Recommendation:** BUILD. Highest N, lowest risk, deterministic. Ship as informational gate first (flag, don't score). Promote to score-affecting after 1 run cycle confirms low false-positive rate.

---

### Candidate B: Counterfactual-Rival Injector

**Target family:** `missing_counterfactual` (89 hits, 36 projects)

**What it is:** A mutator-prompt injection that forces the thesis to name and evaluate at least one rival explanation. Goes beyond the current `_rival_stress_test()` in compress_champion (which only tests parametric rivals for quantitative substrates) to cover qualitative theses.

**Implementation sketch:**
- In autoresearch_loop.py mutator prompt: append a RIVAL REQUIREMENT section
- "Name at least one structurally different rival mechanism that could produce the same observations. For each rival, specify what evidence would distinguish it from your thesis."
- Post-judge: check if the thesis contains a RIVAL HYPOTHESIS section with at least one named rival
- Gate: `has_rival_named = bool(re.search(r'RIVAL HYPOTHESIS.*\n.*\S', thesis_text))`
- If missing: cap score at 50 (same pattern as H-JUDGE-01 harness defect cap)

**Where it lives:** Mutator prompt addition in autoresearch_loop.py (RIVAL REQUIREMENT block), gate check in `global_gates.py`

**Pros:**
- Addresses a real epistemic gap (89 hits, 36 projects)
- Already partially implemented — the thesis template has RIVAL HYPOTHESIS as mandatory section
- Forces the mutator to think adversarially, which is the core ZTARE design philosophy

**Cons:**
- The mutator already has RIVAL HYPOTHESIS in the template. The 89 hits suggest the judge is not PENALIZING when the rival is weak or absent — this might be a judge-calibration issue, not a prompt issue
- Capping at 50 is harsh. Could cause score regression on runs that currently score 60-70 without explicit rivals
- Qualitative theses may have legitimate "no rival" states (unique mechanism with no known alternative)

**Risk:** Medium. Score cap could cause regression. The 89 hits might be judge-scoring noise rather than genuine missing rivals.

**Recommendation:** INVESTIGATE FIRST. Before building, sample 10 records from the `missing_counterfactual` cluster and check manually: is the thesis actually missing a rival, or is the judge critique a false positive? If ≥7/10 are genuine, build. If <5/10, this is a judge-calibration issue and the fix is judge-model selection, not a new gate.

---

### Candidate C: Tail-Extension Primitive

**Target family:** `tail_generalization` (116 hits, 23 projects — pivots FAIL, biggest genuine climbs)

**What it is:** An active intervention (not a gate) that extends evidence into the farther-tail region when the thesis passes visible gates but fails farther-tail. Unlike pivots (which change the topology), this changes the DATA by computing or fetching additional evidence at larger n/x.

**Implementation sketch:**
- Trigger: when `farther_tail_gate` fails AND visible gates pass AND stagnation ≥ 2
- Action: call `generate_extended_evidence(project, current_range, extension_factor=2.0)`
  - For sieve-based substrates (Lucky, abundant density): compute the sieve to 2x current farther-tail range
  - For GT-based substrates: call GT module to generate evidence at extended range
  - For qualitative substrates: N/A (skip)
- Write extended evidence to `evidence_farther_tail_extended.txt`
- Update gate harness to include extended range
- Log the extension event to `loop_events.jsonl`

**Where it lives:** New module `src/ztare/evidence/tail_extension.py`, called from the stagnation handler in autoresearch_loop.py

**Pros:**
- Addresses the highest-leverage blind spot (pivots fail here, biggest climbs when fixed)
- Ticket E data: tail_generalization fixes produce median +43.4 score jumps — if automation captures even 20% of these, it's 10+ score points per run
- Does NOT change the thesis or the grammar — changes the evidence, which is the correct lever for "works in-window, fails out-of-window"
- Clean separation of concerns: evidence extension is substrate-dependent, gate checking is substrate-independent

**Cons:**
- Substrate-dependent: requires a computation module per substrate type. Sieve substrates are straightforward. Qualitative substrates have no computable tail extension.
- Computes may be expensive: extending Lucky numbers from 50K to 100K takes ~30s. Extending to 1M takes ~5min. Budget cap needed.
- Changes the evidence surface mid-run — could interact with stagnation detection (new evidence → new scores → stagnation counter resets → infinite loops)
- Contamination risk: if the mutator sees extended evidence, it might overfit to the tail rather than finding the correct structural form

**Risk:** Medium-high. The interaction with stagnation detection and the contamination risk need careful design. The evidence extension must be SEALED (not visible to the mutator) or used only for gate checking.

**Recommendation:** DESIGN FIRST. Open a spec (GP-072 style) before implementing. Key design questions:
1. Is the extended evidence visible to the mutator or sealed?
2. Does the stagnation counter reset on evidence extension?
3. What's the compute budget cap per extension?
4. How does this interact with the existing farther-tail region definition in the rubric?

If sealed (mutator doesn't see it, only the gate does), the contamination risk drops to zero and this becomes a pure gate-strengthening move. That's the recommended path.

---

## 4. Priority Ranking

| Rank | Candidate | Effort | Risk | Expected impact | Recommendation |
|---|---|---|---|---|---|
| 1 | **A: Scope-Claim Auditor** | Low (regex + range check) | Low (informational gate) | 187 records addressed | **BUILD NOW** |
| 2 | **C: Tail-Extension Primitive** | High (substrate-dependent, design needed) | Medium-high | 116 records, biggest climbs | **SPEC FIRST** |
| 3 | **B: Counterfactual-Rival Injector** | Medium (prompt + gate) | Medium | 89 records, may be judge noise | **INVESTIGATE FIRST** |

---

## 5. Already Covered (no new primitive needed)

- `missing_mechanism` (147) → Newton-mode Generative Yield (GP-133 R4) — already shipped
- `parameter_sensitivity` (81) → prediction-stability check in compress_champion — already shipped
- `catastrophic_assumption` (157) → pivots work (51% climb)
- `exhaustiveness_claim` (62) → pivots work (52% climb)
- `harness_defect` (262) → infrastructure bugs, shrinks as fixed

---

## 6. Data Quality Issues (from GP-148 Stage 2)

1. **Scores > 100 exist** (max 115) — early rubrics didn't cap. Treat as anomalies or clamp.
2. **thesis_primitive_names populated for ~1% of records** — limits Lollapalooza test. Fix: enrich from historical theses.
3. **active_constraints reflects CURRENT rubric state**, not historical — wall-constraint analysis is approximate. Fix: hash-lock rubric at extraction time.
4. **46% → 77% classified after LLM pass** — 197 records (23%) still unclassified. Acceptable noise floor for Stage 3.

---

## 7. Lollapalooza Hypothesis Status

**REFUTED on current features** (all three KS tests p > 0.05). High-scoring iterations are not structurally distinguishable from mid-scoring on primitive_count, dimension_term_count, or active_constraint_count.

**Caveat:** thesis_primitive_names is too sparse to trust feature (a). Before declaring Lollapalooza dead, enrich primitive_names by parsing historical thesis.md files, then retest.

**Hedged verdict:** Not supported. Not conclusively refuted due to feature sparsity. Park until feature enrichment is done.

---

## 8. Anti-Overfitting Discipline

Per GP-148 seam §2.3:
- All patterns reported here have N ≥ 10 (sufficient confidence threshold)
- All patterns span ≥ 10 projects (cross-project replication)
- No changes to `src/ztare/` heuristics proposed without operator signoff
- The three candidate primitives are PROPOSED, not committed
- Candidate B explicitly recommends INVESTIGATION before implementation

---

## 9. Decision Required

- [ ] Approve Candidate A (Scope-Claim Auditor) for immediate implementation
- [ ] Approve Candidate C spec (Tail-Extension Primitive) for GP-072 design phase
- [ ] Approve Candidate B investigation (10-record manual sample of missing_counterfactual)
- [ ] Defer all — current apparatus coverage is sufficient
- [ ] Other direction

---

## 10. Artifacts

| Artifact | Path |
|---|---|
| Stage 2 keyword clusters | `analytics/public/queries/classification/weakest_link_clusters_2026-04-24.json` |
| Stage 3 LLM sub-clusters | `analytics/public/queries/classification/weakest_link_llm_subclasses_2026-04-24.json` |
| Pivot effectiveness | `analytics/public/queries/trajectory/pivot_effectiveness_2026-04-24.json` |
| Lollapalooza test | `analytics/public/queries/classification/lollapalooza_test_2026-04-24.json` |
| Score ceilings | `analytics/public/queries/trajectory/score_ceilings_2026-04-24.json` |
| Climb triggers | `analytics/public/queries/trajectory/climb_triggers_2026-04-24.json` |
| Stage 1 extractor | `scripts/public/mine_trajectories.py` |
| Stage 1.5 enrichment | `scripts/public/mine_trajectories_enrich.py` |
| Stage 3 LLM classifier | `scripts/public/mine_weakest_link_llm_classify.py` |
| GP-148 parent seam | `research_areas/private/seams/engine/GP-148_void_mining_seam.md` |
