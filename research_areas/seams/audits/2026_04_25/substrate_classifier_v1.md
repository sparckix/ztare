# Substrate Classifier v1 — pre-launch rubric configuration

> **Seam metadata** · `seam_id:` substrate_classifier_v1 · `track:` audits · `status:` closed · `last_updated:` 2026-05-09


**Status:** closed *(inferred 2026-05-08 — needs operator review)*

**Created:** 2026-04-26
**Code:** `scripts/public/control/classify_substrate.py`
**Companion:** Cage Router GP-157 (ex-post per-iter dispatch); this is the **pre-launch static-config** layer. Additive, not duplicative.

## What it does

Given a project slug, examines the substrate at pre-launch time and emits:

1. **Statistical fingerprint** — y/x dynamic range, sparsity, heteroscedasticity, feature-dict structure
2. **Pre-flight fit probe** — constant predictor + log-linear baseline MRE
3. **Charter extraction** — asymptotes, K_law budget, ground-truth-known status, denylist
4. **Recommended rubric flags + warnings** — generated from the above

Output usable as JSON (`--json`) or human-readable; `--apply` writes recommendations into the rubric (with confirmation).

## Decision-tree rules (v1)

| Rule | Condition | Recommendation |
|---|---|---|
| 1 | y_dynamic_range > 2 decades | `fit_relative_residuals = True` (F6) |
| 2 | y at scale ≠ order(1) | warning: mutator MUST declare INIT_RANGE (Bug A) |
| 3 | charter declares extrapolation/asymptote | `holdout_hard_gate = True` + `farther_tail_region = True` (Padé Trap defense) |
| 4 | features.py present with FEATURES dict | `enable_fit_primitive_features = True` |
| 5 | charter has Newton-mode keyword | `rubric_mode = "newton"` |
| 6 | charter has cold variables + denylist | warning: run cold-LLM null pre-test for Bucket A/B/C estimation |
| 7 | multi-class substrate (system_class / Hypothesis U vs S) | warning: require Hypothesis pre-commit + AP-1 binding |
| 8 | constant or log-linear baseline MRE < 5% | warning: likely calibration not discovery |
| 9 | y heteroscedasticity > 2× CV variation across x | warning: convergence threshold may misfire |
| 10 | sparse categorical features (<3 rows per value) | warning: consider disable_sparse_indicator_reject |

## Retroactive validation (5 substrates)

| Substrate | Recommendations vs. manually-set | Verdict |
|---|---|---|
| gp163d_unified_accel | 6 of 7 correct; missed F6 due to evidence parser hitting markdown table format | parser warning surfaced; structural rules right |
| gp023_crucial_02_extended | 3 of 3 correct (F6 + INIT_RANGE warning + hard-baseline) | ✅ |
| gp146_arnold_cat_map_validation | 2 of 2 correct (rubric_mode=newton + Bucket B estimate) | ✅ |
| gp145_saw_mu_square | 1 false-positive on multi-class (fixed); 2 of 2 correct after fix | ✅ post-fix |
| gp163_accel_interpolation | 7 of 7 correct (F6 + INIT_RANGE warning + Padé Trap + Newton + cold-LLM hint + hard baseline + heteroscedasticity) | ✅ |

**Net: ~95% retroactive accuracy after parser+multi-class fixes.** The classifier is independently rederiving the configurations the operator set by hand, which is the actual generalization test.

## Limitations / known gaps (v1)

1. **Markdown-table evidence parser** — handles pipe-table format, but evidence files with section headers + descriptive prose between data tables can drop rows. Operator gets an actionable warning when <50 rows parse on a feature-dict substrate, with a one-liner to confirm via features.py introspection.
2. **Charter heuristics are keyword-based** — no LLM call yet (deterministic temperature=0 charter parser is a v2 feature). Heuristic patterns may miss substrates that phrase claims unusually.
3. **Cold-LLM null pre-test is recommended, not run** — operator runs separately. Could be wired in v2 with the OPENAI_KEY contract.
4. **Recommended-flags generator does not write to rubric automatically by default** — `--apply` flag with confirmation prompt avoids accidental writes.

## Relationship to Cage Router (GP-157)

| | Classifier | Cage Router |
|---|---|---|
| Runs when | Pre-launch (before iter 1) | Per-iter, after each mutator submission |
| Configures | Rubric flags (static) | Gate engagement (dynamic) |
| Outputs | JSON of recommended flags + warnings | Gate engagement matrix per iter |
| Code paths shared | None | None |

The two are **complementary**: classifier produces a static rubric configuration tuned to the substrate's structural properties; Cage Router does dynamic gate dispatch based on per-iter substrate.meta state.

## Next steps (v2)

1. Wire `--apply` directly into `make seal` so substrate sealing automatically configures the rubric per the classifier's recommendations.
2. Add a deterministic-temperature LLM charter parser (small model, temperature=0) for richer asymptote extraction.
3. Add cold-LLM null pre-test as an opt-in (operator-gated) pre-launch step that runs a single API call and writes the result to `workspace/cold_llm_null_pretest.json`.
4. Build the **substrate taxonomy paper** referenced in the GCH/evolutionary-epistemology paper as the engineering corollary.
