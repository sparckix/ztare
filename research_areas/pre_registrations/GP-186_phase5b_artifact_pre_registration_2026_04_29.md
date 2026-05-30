# Pre-Registration — GP-186 Phase 5b Harder Anti-Artifact Audit

**Status**: Active pre-registration. Do not rewrite after the audit runs.  
**Date**: 2026-04-29  
**Protocol**: NS post-Phase-5a hostile falsification

---

## 1. Run being adjudicated

Phase 5a closed with both Phase 4 survivors still admissible under the first
hostile pass:

- `full_chiral_torus_knot_A1.0_beta0.5_chi0.3`
  - verdict: `survives_phase5a_initial`
- `full_chirped_cyclic_shear_A1.0_chi0.5_lambda_z2.0`
  - verdict: `survives_phase5a_initial`

Source artifact:

- `projects/ns_millennium_hunt/workspace/phase5a_artifact_summary.json`

---

## 2. Eigenquestion

Do the surviving families remain qualitatively stable under a harder anti-artifact
pass, or do they collapse once the grid, timestep, and viscosity stress are
made more severe?

Operationally:

1. Does a stricter dealias mask at `0.70` or `0.55` materially reduce the signal?
2. Does a tighter timestep ladder at `dt/2` or `dt/4` materially reduce the signal?
3. Does a larger viscosity ladder (`nu/4`, `nu/2`, `2nu`) shift the peak timing
   or slope enough to make the family artifact-risky?

---

## 3. Audit set

- `full_chiral_torus_knot_A1.0_beta0.5_chi0.3`
- `full_chirped_cyclic_shear_A1.0_chi0.5_lambda_z2.0`

Both are mandatory.

---

## 4. Audit protocol

At the highest completed Phase 5a resolution for each candidate (`N=256`),
run:

1. `baseline`
   - same `dt`, same `nu`, standard 2/3 dealiasing
2. `strict_dealias_070`
   - same `dt`, same `nu`, stricter effective cutoff
3. `strict_dealias_055`
   - same `dt`, same `nu`, even stricter effective cutoff
4. `tight_dt_050`
   - same `nu`, same dealiasing, `dt/2`
5. `tight_dt_025`
   - same `nu`, same dealiasing, `dt/4`
6. `nu_quarter`
   - same `dt`, same dealiasing, `nu/4`
7. `nu_half`
   - same `dt`, same dealiasing, `nu/2`
8. `nu_double`
   - same `dt`, same dealiasing, `2nu`

Recorded diagnostics:

- late-window log slope
- BKM proxy integral
- divergence max
- peak-vorticity time
- shell-binned kinetic-energy spectra
- final and late-window spectral tail metrics

Use `projects/ns_millennium_hunt/workspace/phase5b_artifact_audit.py`.

---

## 5. Interpretation rule

This is still not a proof contract. It is an artifact-admissibility contract.

Minimum admissibility for “survives Phase 5b initial” language:

- divergence remains near machine precision
- stricter dealiasing does not materially collapse the slope
- tighter timestep ladder does not materially collapse the slope
- larger viscosity changes do not materially shift peak timing

If those conditions fail, the family is downgraded to artifact-risk status.
