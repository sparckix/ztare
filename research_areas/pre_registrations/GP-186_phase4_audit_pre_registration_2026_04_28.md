# Pre-Registration — GP-186 Phase 4 Audit

**Status**: Closed pre-registration. Audit executed on `2026-04-29 02:19:50Z` and closed on `2026-04-29 02:29:50Z`. Original protocol preserved below.  
**Date**: 2026-04-28  
**Protocol**: NS post-Phase-3 resolution-convergence audit

## Closure

Outcome: the audit rejected the original one-winner reading. Both the primary
survivor and the pre-registered control survive refinement.

Closed results:

- `full_chiral_torus_knot_A1.0_beta0.5_chi0.3`
  - slopes: `1.021 -> 1.2543 -> 1.3734`
  - verdict: `survives`
- `full_chirped_cyclic_shear_A1.0_chi0.5_lambda_z2.0`
  - slopes: `0.9353 -> 1.1768 -> 1.2736`
  - verdict: `survives`

Source artifacts:

- `projects/ns_millennium_hunt/workspace/phase4_audit_results.jsonl`
- `projects/ns_millennium_hunt/workspace/phase4_audit_summary.json`
- `projects/ns_millennium_hunt/workspace/phase4_analysis_20260429.md`

---

## 1. Run being adjudicated

Phase 3 closed on a rented H100 with:

- source artifact: `projects/ns_millennium_hunt/workspace/phase3_results_h100_20260429.jsonl`
- total rows: `53`
- only flagged Phase 4 candidate:
  - `full_chiral_torus_knot_A1.0_beta0.5_chi0.3`
  - `late_window_slope = 1.021`
  - `growth_ratio = 16.248`
  - `energy_dissipation_pct = 1.116`
  - `div_max_ever ≈ 2.99e-15`

Phase 3 also produced one broad near-miss control family:

- strongest control:
  - `full_chirped_cyclic_shear_A1.0_chi0.5_lambda_z2.0`
  - `late_window_slope = 0.9353`

---

## 2. Eigenquestion

Is the live NS signal after Phase 3 a **narrow topological spike** or a
**broad anisotropic shear plateau**?

Operationally:

1. Does the knot survivor remain elevated or strengthen under refinement?
2. Does the broad chirped-shear control lift into the same regime under refinement?
3. Or do both collapse as fixed-resolution artifacts?

---

## 3. Audit set

### Primary survivor

- `full_chiral_torus_knot_A1.0_beta0.5_chi0.3`

### Control near-miss

- `full_chirped_cyclic_shear_A1.0_chi0.5_lambda_z2.0`

Rationale: the primary is the only true flagged survivor; the control is the
highest-slope member of the broad plateau family and is the cleanest test of
whether the Phase 3 threshold merely undercalled a real mechanism.

---

## 4. Audit protocol

For each candidate:

- re-run at resolutions `N = 128, 192, 256`
- tighten `dt` with resolution (`dt_scaled = dt_base * 128 / N`)
- keep `nu = 1e-4`
- record:
  - late-window log slope
  - BKM proxy integral `∫ omega_max dt`
  - peak-omega time
  - energy dissipation %
  - divergence max

Use `projects/ns_millennium_hunt/workspace/phase4_audit.py`.

---

## 5. Pre-registered outcomes

### Outcome A — survivor sharpens

The knot candidate keeps elevated late-window slope at the two highest
resolutions, BKM proxy does not collapse, divergence stays controlled, and the
control family remains materially lower.

Interpretation:

- topological concentration is the live mechanism
- advance knot family to Phase 5 routing first

### Outcome B — plateau lifts

The control family rises into the same regime under refinement or remains
comparable while the knot weakens.

Interpretation:

- anisotropic shear-sheet amplification may be the real live branch
- broad-family mechanism outranks isolated spike

### Outcome C — both collapse

Highest-resolution slopes fall materially and/or BKM proxy collapses for both.

Interpretation:

- Phase 3 produced an informative numerical artifact screen, not a durable
  survivor
- return to Phase 3b / ansatz redesign rather than routing to experts

### Outcome D — mixed / inconclusive

Signal persists but not cleanly enough to distinguish A/B/C.

Interpretation:

- one more resolution or dt-tightening pass is justified
- no mechanism claim yet

---

## 6. Success / failure contract

The audit is **not** a proof contract. It is an admissibility contract.

Minimum admissibility for “survives” language:

- divergence remains near machine precision
- the two highest-resolution slopes remain elevated (`>= 0.5`)
- relative drift between the two highest-resolution slopes is not extreme
- BKM proxy on the highest two resolutions does not collapse

If those conditions are not met, the candidate is not promotable to strong
Phase 5 language.

---

## 7. Anti-pattern lock

- Do **not** call the Phase 3 winner a blowup candidate unless the audit says
  the highest-resolution signal remains elevated.
- Do **not** drop the chirped-shear control merely because it is below the
  Phase 3 threshold; the broad-versus-spike split is the whole reason this
  audit exists.
- Do **not** weaken or rewrite the criteria after seeing the audit outputs.
