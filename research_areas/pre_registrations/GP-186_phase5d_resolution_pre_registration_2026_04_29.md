# Pre-Registration — GP-186 Phase 5d Resolution/Core-Coherence Audit

**Status**: Active pre-registration. Do not rewrite after the audit runs.  
**Date**: 2026-04-29  
**Protocol**: NS post-Phase-5c higher-resolution discrimination

---

## 1. Run being adjudicated

Phase 5c closed with both survivor families passing the first localization
test:

- `full_chiral_torus_knot_A1.0_beta0.5_chi0.3`
  - verdict: `supports_localized_core`
  - `r99 / r99_init = 0.1307`
- `full_chirped_cyclic_shear_A1.0_chi0.5_lambda_z2.0`
  - verdict: `supports_localized_core`
  - `r99 / r99_init = 0.1510`

The problem is that the `99%` superlevel-core metric appears to be saturating
at the `N=256` grid floor, reducing its power to discriminate the two
mechanisms.

Source artifact:

- `projects/ns_millennium_hunt/workspace/phase5c_localization_summary.json`

---

## 2. Eigenquestion

When the localization audit is repeated at higher resolution with a tighter
threshold and connected-component coherence metrics, does the knot branch
remain the cleaner collapsing-core mechanism than the shear control?

Operationally:

1. Does the knot branch preserve core contraction at `N=384` and `N=512`?
2. Does the harsh-dealias control preserve the same qualitative localization?
3. Is the high-threshold core dominated by one or a few connected components,
   rather than fragmenting into a grid-floor superlevel cloud?
4. Does the shear control look weaker or more fragmented under the same test?

---

## 3. Audit set

Primary mandatory object:

- `full_chiral_torus_knot_A1.0_beta0.5_chi0.3`

Control object:

- `full_chirped_cyclic_shear_A1.0_chi0.5_lambda_z2.0`

Variants:

1. `baseline`
2. `strict_dealias_055`

Resolutions:

1. `N=384`
2. `N=512`

Run the control only if budget allows after the knot primary completes.

---

## 4. Metrics

Thresholds:

- `95%`
- `99%`
- `99.5%`

Per threshold record:

- total superlevel-core volume
- equal-volume effective radius
- largest connected-component volume
- largest connected-component radius
- largest-component share of the total core
- connected-component count

The central discriminator is no longer just “does a superlevel set
contract?” It is:

> does a coherent connected core survive resolution increase, or does the
> apparent collapse dissolve into grid-scale fragmentation?

---

## 5. Interpretation rule

### Outcome A — coherent localized knot

Interpretation:

- the knot branch remains the primary mechanism
- the current numerical story strengthens from “localized survivor” to
  “higher-resolution coherent localized core”

### Outcome B — localized but fragmented

Interpretation:

- the core still contracts, but the geometry is not yet clean enough to
  support stronger singularity language

### Outcome C — control parity

Interpretation:

- if the shear control looks equally coherent at higher resolution, the repo
  should not overstate knot-specificity yet

### Outcome D — collapse of the localization metric

Interpretation:

- if the higher-resolution rerun loses contraction or coherence, the `N=256`
  localization result was too close to the grid floor to carry the claim

---

## 6. Execution path

Use:

- `projects/ns_millennium_hunt/workspace/phase5d_resolution_audit.py`

Expected outputs:

- `phase5d_resolution_results.jsonl`
- `phase5d_resolution_summary.json`
