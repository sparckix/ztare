# PR2 Bohr/AP Dedup Note

Date: 2026-06-09

This note records the current dedup pass for the old Bohr/AP support cluster.
It is intentionally narrower than the May 2026 PR-readiness notes.

## Sources Checked

- `ZtareProofs/PR_A1_BohrCoeffExpNe_Discharge.lean`
- `ZtareProofs/PR_A1_BohrCoeffExpNe_Cascade.lean`
- `ZtareProofs/PR_A1_CubeAvgModSqLeLinftySq.lean`
- `ZtareProofs/PR_A1_T9_Lemma_4_2.lean`
- `ZtareProofs/PR_A1_T9_Lemma_4_3.lean`
- Current Mathlib checkout at `/private/tmp/mathlib4-pr-check`

## Local Compile Result

The four direct A1/T9 files compiled locally in `ztare_proofs`:

- `PR_A1_BohrCoeffExpNe_Discharge.lean`
- `PR_A1_CubeAvgModSqLeLinftySq.lean`
- `PR_A1_T9_Lemma_4_2.lean`
- `PR_A1_T9_Lemma_4_3.lean`

Warnings remain in the cube-average and T9 4.3 files for unused variables.
Those files should not be copied upstream without statement cleanup.

## Dedup Result

These are not clean upstream gaps:

- `cube_integral_prod_factor`: current Mathlib already has `volume_pi`,
  `Measure.restrict_pi_pi`, and `MeasureTheory.integral_fin_nat_prod_eq_prod`.
  The local theorem is a valid composition, not a missing theorem by itself.
- `integral_Icc_exp_mul`: current Mathlib has
  `integral_exp_mul_complex` in
  `Mathlib.Analysis.SpecialFunctions.Integrals.Basic`. An `Icc` wrapper may be
  convenient, but it is too small to justify a PR alone.
- Cube-volume support: current Mathlib has `Real.volume_Icc_pi` and
  `Real.volume_Icc_pi_toReal`.

The plausible reusable residue is the pair of oscillatory bounds extracted in
`PR2_OscillatoryIntegralBounds.lean`.

## PR2 Candidate

Draft file:

- `PR2_OscillatoryIntegralBounds.lean`

Candidate statements:

- exposed:
  `norm_integral_exp_mul_I_le_length`
- exposed:
  `norm_integral_exp_mul_I_le_two_div`
- private proof helper:
  `norm_exp_mul_I_sub_exp_mul_I_div_le`

Current status:

- Clean upstream branch prepared, committed, and pushed to the fork:
  https://github.com/sparckix/mathlib4/tree/oscillatory-integral-bounds
  (`08222cd`, `oscillatory-integral-bounds`). Local checkout:
  `/private/tmp/mathlib4-upstream-master`.
- Inserted into
  `Mathlib/Analysis/SpecialFunctions/Integrals/Basic.lean` after
  `integral_exp_mul_complex`.
- Passed on 2026-06-09:
  `lake env lean Mathlib/Analysis/SpecialFunctions/Integrals/Basic.lean`,
  `lake exe lint-style Mathlib.Analysis.SpecialFunctions.Integrals.Basic`, and
  `lake build Mathlib.Analysis.SpecialFunctions.Integrals.Basic`.

Submission posture:

- Technically PR-ready. Better sequencing is to wait for first feedback on PR
  #40416 before opening a second Mathlib PR.
- Keep the theorem names neutral and avoid Bohr/AP/NS terminology in the PR.
