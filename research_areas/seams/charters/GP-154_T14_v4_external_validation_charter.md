# T14 — v4 Conversion-Transform External Validation Charter

> **Seam metadata** · `seam_id:` GP-154 · `track:` charters · `status:` ACTIVE - Phase A in progress, Phase B deferred · `last_updated:` 2026-05-09


**Parent seam:** `GP-154_class_K_diagnostic_and_panel_review.md`
**Status:** ACTIVE — Phase A in progress, Phase B deferred
**Created:** 2026-04-25 night

---

## Origin

Panel verdict (2026-04-25 night, parent seam Turn 13) on the v4 charter:

> *Attacks 4.1, 4.2, 7.1 (FATAL leakage objections): the diagnostic priors
> encoded in the v4 charter were derived from the SAME 110-row dataset that
> v4's holdout draws from. The holdout was unsealed during the offline
> diagnostic. Any "ZTARE autonomously discovered the conversion transform"
> CONFIRMATORY claim is methodologically void.*

Panel's required remedy: external sealed holdout from post-2026-04-25
publications. T14 is the work item that produces that holdout.

Plus today's `gp154i_convention_pair_overlap.py` (Turn 17) result: best
in-pool convention-pair transform = 0.41 mean CV MRE for kaplan_separable
→ loss_curve_power. Below 1.6 unified-law wall (4× tighter), but above
v4 charter threshold of 0.25. **Conclusion: v4 has signal worth chasing,
needs external data to validate.**

---

## Target

Validate (or refute) the v4 conversion-transform claim:

> *Given α observed under source convention `s`, predict the α that would
> have been measured under target convention `t` for the same (N, D, C)
> regime. The transform `T(α, s, t, N, D, C) → α_target` should achieve
> HOLDOUT MRE < 0.25 on independent data.*

---

## Two-Phase Structure

### Phase A — Literature Scrape (tonight, ~1 hour)

**Scope:** weakened external validation. Papers from 2025-Q4 / 2026-Q1
that are NOT in the existing 110-row dataset. Use their PUBLISHED α
values directly (no curve refits).

**Method:**
1. WebSearch for "neural scaling law 2025 2026" — identify 4-8 candidates.
2. Per candidate, extract from the abstract / table:
   - Published α (with sign, if relevant)
   - fit_convention (chinchilla_joint / kaplan_separable / loss_curve_power / etc.)
   - log_N range
   - log_D range (if reported)
   - modality + study_id + regime_hint
3. Append to `evidence_external_phase_a.txt` with provenance comments
   linking each row to its arxiv URL.
4. Train T (best from gp154i) on the 94-row pool.
5. Apply T to predict α_target on the new external rows.
6. Compute HOLDOUT MRE, std, and per-row residuals.

**Phase A success criteria:**
- HOLDOUT MRE < 0.25 → strong signal, justifies Phase B.
- 0.25 ≤ MRE < 0.5 → suggestive, justifies Phase B with caution.
- MRE ≥ 0.5 → v4 dies cheaply; do not invest in Phase B.

**Phase A leakage caveats (do not hide):**
- These papers are pre-2026-04-25 cutoff. The agent who built gp154 (me)
  may have implicitly known of them. NOT panel-strict.
- This phase is a methodology rehearsal + preliminary signal check, not
  a publishable validation.

### Phase B — Real T14 (~1 week, deferred)

Triggered only if Phase A passes the suggestive threshold.

**Scope:** panel-strict external holdout.

**Method:**
1. Identify 4 papers that publish raw `(N, D, L)` curve data (tables,
   appendices, supplementary CSVs — figures alone insufficient).
2. Refit each curve under chinchilla_joint AND kaplan_separable (and any
   other relevant pair). Get paired α's per study.
3. Train T on 94 rows + Phase A external rows. Apply to Phase B paired α's.
4. Validate. Compute HOLDOUT MRE on the strict-paired set.

**Phase B success criterion:**
- MRE < 0.25 on the strict external paired set → v4 confirmatory claim
  achieves Nature MI tier.
- Anything else → bounded null on v4 conversion-transform target.

---

## Anti-patterns

- **Cherry-picking conventions to fit the data after seeing it.** The
  pair to validate is fixed at the start of Phase A: `kaplan_separable
  → loss_curve_power` (best from gp154i). Any other pair tested in
  Phase A is descriptive/exploratory and labeled as such.
- **Treating Phase A as a validation claim.** Phase A is a feasibility
  test. Only Phase B yields a confirmatory claim per the panel.
- **Fabricating α values from prior knowledge.** Every Phase A row must
  have a verifiable arxiv URL + page number citation. If the paper
  doesn't report α numerically, skip — don't impute.

---

## Deliverables

- `scripts/public/gp154j_external_holdout_scrape.py` — Phase A pipeline.
- `evidence_external_phase_a.txt` — extracted rows with citations.
- `research_areas/private/seams/GP-154_T14_v4_external_validation_charter.md`
  — this file, status updated post-Phase-A.
- Decision gate at end of Phase A: invest Phase B or sunset v4.

---

## Status log

- **2026-04-25 night:** Charter drafted. Phase A in progress.
