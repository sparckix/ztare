# Pre-Registration — GP-186 Phase 5a Anti-Artifact Audit

**Status**: Active pre-registration. Do not rewrite after the audit runs.  
**Date**: 2026-04-28  
**Protocol**: NS post-Phase-4 hostile artifact falsification

---

## 1. Run being adjudicated

Phase 4 closed on `2026-04-29 02:29:50Z` with two refinement survivors:

- `full_chiral_torus_knot_A1.0_beta0.5_chi0.3`
  - slopes: `1.021 -> 1.2543 -> 1.3734`
  - verdict: `survives`
- `full_chirped_cyclic_shear_A1.0_chi0.5_lambda_z2.0`
  - slopes: `0.9353 -> 1.1768 -> 1.2736`
  - verdict: `survives`

Source artifact:

- `projects/ns_millennium_hunt/workspace/phase4_audit_summary.json`

---

## 2. Eigenquestion

Are the Phase 4 survivors measuring ansatz-specific concentration physics, or
are they converging onto the shared failure modes of the numerical apparatus?

Operationally:

1. Does a stricter effective spectral cutoff materially reduce the signal?
2. Does a tighter timestep materially reduce the signal?
3. Does halving viscosity shift the peak event so much that the survivor looks
   transient rather than structural?

---

## 3. Audit set

- `full_chiral_torus_knot_A1.0_beta0.5_chi0.3`
- `full_chirped_cyclic_shear_A1.0_chi0.5_lambda_z2.0`

Both are mandatory. Do not drop the chirped-shear branch now that it survived
Phase 4.

---

## 4. Audit protocol

At the highest completed Phase 4 resolution for each candidate (`N=256` in the
current audit close), run:

1. `baseline`
   - same `dt`, same `nu`, standard 2/3 dealiasing
2. `strict_dealias`
   - same `dt`, same `nu`, stricter effective cutoff via scaled dealias mask
3. `tight_dt`
   - same `nu`, same dealiasing, globally tighter `dt`
4. `half_nu`
   - same `dt`, same dealiasing, `nu/2`

Recorded diagnostics:

- late-window log slope of `omega_max`
- BKM proxy integral
- divergence max
- peak-vorticity time
- shell-binned kinetic-energy spectra across logged times
- final and late-window spectral hook metrics

Use `projects/ns_millennium_hunt/workspace/phase5a_artifact_audit.py`.

---

## 5. Important limitation

The current solver stack still uses fixed `dt`; it does not yet implement the
adaptive CFL stepping promised in the original charter. Therefore the timestep
test in this Phase 5a prereg is a **global dt ladder**, not a late-window
adaptive cap. Interpret it accordingly.

---

## 6. Pre-registered outcomes

### Outcome A — artifact-robust

The stricter dealias and tighter-dt variants remain qualitatively aligned with
baseline, and `nu/2` does not shift peak timing wildly.

Interpretation:

- the family survives the first hostile anti-artifact pass
- stronger mechanism language becomes admissible

### Outcome B — spectral-blocking risk

The stricter dealias cutoff causes a material slope drop and/or removes a
tail-hook signature.

Interpretation:

- the apparent survivor is at serious risk of being truncation-driven
- do not escalate mechanism claims yet

### Outcome C — timestep sensitivity

The tighter-dt run materially reduces the late-window slope.

Interpretation:

- the survivor may reflect numerical integration stress rather than a stable
  concentration process

### Outcome D — viscosity fragility

Halving `nu` shifts the peak event strongly or destabilizes the timing pattern.

Interpretation:

- the family may be a viscosity-sensitive transient, not a robust singular
  mechanism

---

## 7. Success / failure contract

This stage is still not a proof contract. It is an anti-artifact admissibility
contract.

Minimum admissibility for “survives Phase 5a initial” language:

- divergence remains near machine precision
- strict dealias does not materially collapse the slope
- tighter `dt` does not materially collapse the slope
- `nu/2` does not shift peak timing by a large fraction of the run window

If these conditions fail, the survivor is downgraded to artifact-risk status.
