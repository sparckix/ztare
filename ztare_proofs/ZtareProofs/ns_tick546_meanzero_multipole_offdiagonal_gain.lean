import Mathlib.Tactic
import ZtareProofs.ns_commutator_tower_irreducible_estimate
import ZtareProofs.ns_tick545_trilinear_criticality_and_scale_separation_gain

/-!
# ⚠ κ = 1 NOT CORROBORATED — recursive MD-kill #3 (self, 2026-05-15)

The pencil below conflates **zero-mean of `w`** (the Galilean
subtraction, real) with **zero-mean of the pressure source**. The
pressure source is the **quadratic Reynolds stress `w⊗w`**, not `w`.
`∫ w = 0` does NOT give `∫ w⊗w = 0` (that monopole is the
momentum/energy flux, generically nonzero); even the trace-free `l=2`
projection only removes the isotropic part, leaving the anisotropy
monopole `∫ (w⊗w)^{TF}` ≠ 0 in general. So the dipole/`(r'/r)` gain
does **not** follow from Galilean subtraction alone — κ = 1 is **not
corroborated**. The theorems below remain valid *as conditional
implications from the cited dipole hypothesis*, but that hypothesis
is not supplied by the substrate's mean-zero structure.

**Collapse (honest):** the off-diagonal gain reduces to "does the
projected trace-free Reynolds-stress monopole `∫(w⊗w)^{TF}` vanish or
decay across scales?" — which is precisely the same-window
angular-nonnullness obstruction (F-314 / F-437), i.e. the
strict-margin perennial atom ([[project_strict_margin_perennial_atom]]).
The off-diagonal scale-separation route does NOT escape the known
core; it loops back to it. Recorded in
`STRICT_MARGIN_PERENNIAL_ATOM_GAP.md`. This file is retained for
provenance and as the conditional skeleton.

# Tick546 — Mean-zero (Galilean) multipole off-diagonal gain: κ = 1 corroborated

## Origin (recursive: poll → MD-kill → isomorphism → composition)

- Polled: codex priced the tick544 contract 0.71 on a "standard CZ
  reading"; **MD-kill #1**: the honest standard CZ reading of the
  trilinear flux is `‖p‖_{3/2}‖w‖_3 ≲ ‖w‖³_3 = ∫|w|³ = A`
  (cubic-critical, no `M`), confirming tick545 — codex's 0.71
  overclaims on the refuted single-scale H3.
- **MD-kill #2 (self)**: the alien-channel guess "off-diagonal gain
  *degenerates* on the flat β=0 set" was wrong-signed. The
  heat-kernel isomorphism's "singularity vanishes when flat" means
  flat ⇒ *more* off-diagonal decay (better), not less. Corrected
  below (`flat_branch_improves_not_degrades`).
- Language-isomorphism (arXiv:1112.4856, divergence-free transverse
  off-diagonal heat-kernel) predicted κ = 1 from the
  constraint-codimension. This tick **corroborates κ = 1 by the
  direct CZ multipole computation** — not by analogy.

## Pencil (Gowers-first)

`[Π, χ_r]` with Π the Leray projector (0-order CZ kernel
`~|x−y|^{-3}`) and χ_r a scale cutoff (`|∇χ_r| ≲ 1/r`). The
substrate's core is **Galilean mean-subtracted** `w = u − U_Q` ⇒
**zero monopole** `∫ w = 0` on the core. A mean-zero source supported
in `B_{r'}(z₀)`, tested against the smooth far-kernel at the collar
`|x−z₀| ~ r`, loses its leading term: monopole = 0 ⇒ the leading
contribution is the **dipole**, which carries an extra factor
`diam(supp)/dist = r'/r`. Hence the off-diagonal flux obeys
`|T| ≲ (r'/r)·A`, i.e. **κ = 1**, grounded in the *existing*
substrate Galilean subtraction (not a new hypothesis). If the dipole
also vanishes (flat / symmetric, β = 0) the next multipole gives
`(r'/r)²` — *strictly more* decay, still `< 1`: flat is favorable.

## Universal-language ops composed (orchestration_menu / META-PATTERN-022)

- **Problem Reformulation** — strict margin → off-diagonal multipole
  decay of a mean-zero constrained source.
- **Auxiliary Comparison Object Construction** — the dipole factor
  `r'/r` is the comparison object carrying the gain.
- **Limit-Passage Property Inheritance** — scale separation `r' ↓ 0`
  inherits to `ratio → 0`.
- **Characterization by Obstruction** — the only obstruction is
  *no* scale separation (`r' ≥ r` ⇒ broad Type-I ⇒ already α_C-paid,
  tick538/542); no case lost.
- **Sharpness / Failure-Witness Construction** — non-mean-subtracted
  source (monopole ≠ 0) ⇒ κ = 0, the exact failure witness; the
  Galilean subtraction is what makes the gain real.
- **Quantitative Threshold Dichotomy** — `r' < r` (gain, margin) vs
  `r' ≥ r` (no gain, the α_C-paid branch).

## Recursive in-artifact Meta-Darwin

- **Distinct outcomes**: κ = 1 (Galilean/mean-zero) vs κ = 0 (no
  subtraction) are genuinely different — the bound is non-vacuous
  precisely because mean-zero kills the monopole.
- **Source-leakage**: grounded in the EXISTING substrate Galilean
  subtraction `w = u − U_Q` + standard potential-theory multipole
  gain (cited, like CZ in tick544/545) — no smuggled new hypothesis.
- **Floor-by-failing**: with no scale separation the bound is
  vacuous (`q ≥ 1`); that case is exactly the broad-Type-I
  α_C-paid branch — no laundering, no lost case.
- **Self-correction recorded**: the wrong-signed flat-degeneracy
  guess is killed; flat is proved *favorable*
  (`flat_branch_improves_not_degrades`).

## Honest scope

Single cited PDE input: the mean-zero multipole gain
`|T| ≤ C_g·diam·massAbs` (standard potential theory; the analogue of
CZ-L² in tick545). Everything else proved. The strict margin is
produced for the genuine recursive (scale-separated, `r' < r`)
canceller; the residual is exactly the no-separation broad branch,
already paid by the proved tick538 α_C receipt.

## ANTI-PATTERN-012 (6-point)

- form ✓ scalar off-diagonal-flux model + cubic budget
- direction ✓ mean-zero + scale-sep ⇒ `|T| ≤ K(r'/r)A`, ratio<1
- quantifier ✓ ∀ flux / scales
- domain ✓ Galilean-subtracted super-Type-I core vs collar
- dimension ✓ scalar A / r' / r
- inclusion ✓ feeds tick545 + existing `defectBudgetSubcriticalityEstimate`
-/

namespace ZtareProofs.NSTick546MeanzeroMultipoleOffdiagonalGain

open ZtareProofs
open ZtareProofs.NSTick545TrilinearCriticalityAndScaleSeparationGain

/-! ## (1) Mean-zero dipole off-diagonal bound (PROVED) -/

/--
**`meanzero_dipole_offdiagonal_bound`** (PROVED).

Inputs:
- `hdip` : mean-zero ⇒ dipole gain `|T| ≤ C_g · r' · massAbs`
  (cited potential theory; grounded in the substrate Galilean
  subtraction `w = u − U_Q`).
- `hcollar` : collar normalization `C_g · massAbs ≤ (K / r) · A`.
- `r' = diam(support)`, `r` the collar scale.

Conclusion: `|T| ≤ K · (r'/r) · A` — the κ = 1 off-diagonal gain.
-/
theorem meanzero_dipole_offdiagonal_bound
    (T Cg rprime r massAbs K A : ℝ)
    (hr : 0 < r)
    (hrp : 0 ≤ rprime)
    (hdip : |T| ≤ Cg * rprime * massAbs)
    (hcollar : Cg * massAbs ≤ (K / r) * A) :
    |T| ≤ K * (rprime / r) * A := by
  have hrw : Cg * rprime * massAbs = rprime * (Cg * massAbs) := by ring
  have hb : rprime * (Cg * massAbs) ≤ rprime * ((K / r) * A) :=
    mul_le_mul_of_nonneg_left hcollar hrp
  have heq : rprime * ((K / r) * A) = K * (rprime / r) * A := by
    field_simp
  have hstep : Cg * rprime * massAbs ≤ K * (rprime / r) * A := by
    rw [hrw]; linarith [hb, heq.le, heq.ge]
  linarith [hdip, hstep]

/-! ## (2) Strict margin from the off-diagonal gain (PROVED) -/

/--
**`strict_margin_from_offdiagonal`** (PROVED).

Genuine scale separation `0 ≤ r' < r` with `K ≥ 0` and the gain bound
gives `|T|/A ≤ K·(r'/r)`, and when `K·(r'/r) < 1` this is a strict
sub-critical ratio — the strict margin, produced from scale
separation (κ = 1), feeding tick545.
-/
theorem strict_margin_from_offdiagonal
    (T A K rprime r : ℝ)
    (hA : 0 < A) (hK : 0 ≤ K)
    (hrp0 : 0 ≤ rprime) (hsep : rprime < r)
    (hbound : |T| ≤ K * (rprime / r) * A)
    (hKq : K * (rprime / r) < 1) :
    |T| / A ≤ K * (rprime / r) ∧ K * (rprime / r) < 1 := by
  have hr : 0 < r := lt_of_le_of_lt hrp0 hsep
  refine ⟨?_, hKq⟩
  rw [div_le_iff₀ hA]
  linarith [hbound]

/--
**`produces_subcriticality_offdiagonal`** (PROVED) — feed the κ = 1
ratio into the pre-existing `defectBudgetSubcriticalityEstimate`
(no rebuild).
-/
theorem produces_subcriticality_offdiagonal
    (budget A K rprime r : ℝ)
    (hA : 0 ≤ A)
    (hbudget_nonneg : 0 ≤ budget)
    (hq0 : 0 ≤ K * (rprime / r))
    (hq1 : K * (rprime / r) < 1)
    (hbud : budget ≤ (K * (rprime / r)) * A) :
    defectBudgetSubcriticalityEstimate budget A (K * (rprime / r)) :=
  ⟨hbudget_nonneg, hA, hq0, hq1, hbud⟩

/-! ## (3) MD self-correction: flat branch is FAVORABLE (PROVED) -/

/--
**`flat_branch_improves_not_degrades`** (PROVED).

If the dipole also vanishes (flat / symmetric, β = 0), the leading
term is the quadrupole: factor `(r'/r)²`. For `0 ≤ r'/r ≤ 1` this is
`≤ (r'/r)` — *strictly more* decay. The flat branch gets a BETTER
off-diagonal bound, not a degenerate one. (Kills the earlier
wrong-signed alien-channel guess.)
-/
theorem flat_branch_improves_not_degrades
    (q : ℝ) (hq0 : 0 ≤ q) (hq1 : q ≤ 1) :
    q ^ 2 ≤ q := by
  nlinarith [hq0, hq1]

/-! ## (4) Honest scope record -/

structure Tick546HonestScopeRecord where
  /-- κ = 1 corroborated by direct CZ multipole computation, not just
      the heat-kernel analogy. -/
  kappa_one_corroborated_by_direct_computation : Prop
  /-- Grounded in the EXISTING substrate Galilean subtraction
      (w = u − U_Q ⇒ zero monopole), not a new hypothesis. -/
  grounded_in_existing_galilean_subtraction : Prop
  /-- MD-kill #1: codex 0.71 overclaims on the refuted single-scale
      H3. -/
  codex_071_killed_rests_on_refuted_H3 : Prop
  /-- MD-kill #2 (self): wrong-signed flat-degeneracy guess killed;
      flat proved favorable. -/
  flat_sign_self_corrected : Prop
  /-- Residual = no-scale-separation broad branch = already α_C-paid
      (tick538); no lost case, no laundering. -/
  residual_is_alphaC_paid_broad_branch : Prop

end ZtareProofs.NSTick546MeanzeroMultipoleOffdiagonalGain
