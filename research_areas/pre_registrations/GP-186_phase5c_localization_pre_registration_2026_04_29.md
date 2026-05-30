# Pre-Registration — GP-186 Phase 5c Localization Audit

**Status**: Active pre-registration. Do not rewrite after the audit runs.  
**Date**: 2026-04-29  
**Protocol**: NS post-Phase-5b localization discrimination

---

## 1. Run being adjudicated

Phase 5b closed with both survivor families still admissible under the harder
anti-artifact pass, but with a sharper internal split:

- `full_chiral_torus_knot_A1.0_beta0.5_chi0.3`
  - verdict: `survives_phase5b_initial`
  - strongest surviving branch under the harshest dealias ladder
- `full_chirped_cyclic_shear_A1.0_chi0.5_lambda_z2.0`
  - verdict: `survives_phase5b_initial`
  - still live, but more cutoff-fragile at `dealias=0.55`

Source artifact:

- `projects/ns_millennium_hunt/workspace/phase5b_artifact_summary.json`

---

## 2. Eigenquestion

Are the surviving late-time growth signatures accompanied by a shrinking,
localized high-vorticity core, or are they better described as broad
sheet-like amplification patterns?

Operationally:

1. Does the highest-threshold `|omega|` core contract from the initial state
   to the peak event?
2. Does that contraction survive the harshest dealias setting that still
   preserves the family?
3. Does the knot branch look more localized than the shear branch under the
   same localization metric?

---

## 3. Audit set

Mandatory families:

- `full_chiral_torus_knot_A1.0_beta0.5_chi0.3`
- `full_chirped_cyclic_shear_A1.0_chi0.5_lambda_z2.0`

Mandatory variants:

1. `baseline`
2. `strict_dealias_055`

This keeps the Phase 5c package small and targeted. The spectral differentiation
question was already pushed hard in Phase 5b. Phase 5c adds the missing spatial
localization layer.

---

## 4. Localization metric

For each logged time, compute the superlevel-core sets

- `|omega| >= 0.90 * |omega|_max`
- `|omega| >= 0.95 * |omega|_max`
- `|omega| >= 0.99 * |omega|_max`

Recorded per threshold:

- cell-count-based volume
- occupancy fraction
- effective radius of the equal-volume sphere

Also record:

- peak-vorticity grid location and physical coordinates
- late-window path length of the peak point

This is the cheapest admissible localization instrument in the current solver
stack. Do not infer vortex-tube curvature from these runs yet.

---

## 5. Interpretation rule

This stage is still not a proof contract. It is a localization-admissibility
contract.

Minimum language for `supports_localized_core`:

- the `99%` superlevel core contracts from initial state to peak
- that contraction persists under `strict_dealias_055`
- the resulting signal is cleaner for the knot branch than for the shear branch

Possible outcomes:

### Outcome A — localized knot, weaker shear

Interpretation:

- the knot becomes the primary mechanism branch
- the shear branch is downgraded to a broader but less singular-looking control

### Outcome B — both localized

Interpretation:

- the search has found two genuinely live localized concentration mechanisms
- the next move is mechanism extraction, not more search

### Outcome C — neither localizes cleanly

Interpretation:

- the current survivors are strong growth objects but not yet singularity-like
  collapse objects
- downgrade mechanism language accordingly

---

## 6. Execution path

Use:

- `projects/ns_millennium_hunt/workspace/phase5c_localization_audit.py`
- `projects/ns_millennium_hunt/workspace/plot_phase5c_outputs.py`

Expected outputs:

- `phase5c_localization_results.jsonl`
- `phase5c_localization_summary.json`
- `phase5c_four_panel_comparison.svg`
- `phase5c_knot_localization.svg`
