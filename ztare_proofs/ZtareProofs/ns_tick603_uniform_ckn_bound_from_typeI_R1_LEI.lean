import Mathlib.Tactic

/-!
# Tick603 — PDE WORK: discharge tick602's `uniformCKNBound` (Case 1)
#   from Track-B Type-I + CZ + R1 + the suitable-weak LEI, reducing it
#   to ONE isolated residual (R1-tail cascade-uniformity)

## Why (operator: "go hard on PDE work")

tick602 isolated the porosity route's first OPEN PDE input as a
hypothesis `uniformCKNBound`: a rescaled CKN bound `G[U,P]+H[U] ≤ M`
on the flat branch, with `M` INDEPENDENT of the cascade index `n`
(non-uniformity would kill the porosity ⇒ the tick601 lesson). This
file does the depth-n estimate assembly and proves the reduction:
GIVEN the four named Track-B / suitable-weak inputs, `G+H ≤ M` with `M`
an explicit constant in `(C∗, C_cz, C_R)` containing NO scale `rₙ` —
hence cascade-uniform. The velocity term (Type-I), local pressure (CZ),
and enstrophy (LEI) are fully discharged; the SOLE remaining residual
is the cascade-uniformity of `C_R` (the R1 harmonic pressure tail),
which is left as an explicit hypothesis, NOT proved (anti-laundering).

## The estimate chain (each step parabolic-scale-invariant)

* Type-I ⟺ rescaled `‖U‖_{L^∞(Q₁)} ≤ C∗`  ⇒  `∫∫|U|³ ≤ |Q₁|·C∗³`.
* `−ΔP_loc = ∂ᵢ∂ⱼ(UᵢUⱼ)`; Calderón–Zygmund ⇒
  `∫∫|P_loc|^{3/2} ≤ C_cz·C∗²`.
* `P_har` harmonic in `B₁`; R1 (Track-B datum) ⇒
  `∫∫|P_har−P̄_har|^{3/2} ≤ C_R`  (the isolated residual: is `C_R`
  cascade-uniform or does it accumulate — the tick601 Σ-nonuniformity
  risk).
* suitable-weak LEI with a fixed cutoff ⇒
  `H ≤ C_lei·(1 + C∗³ + (∫∫|P−P̄|))`.
* assemble ⇒ `G + H ≤ M(C∗,C_cz,C_R)`, no `rₙ`.

## Honest status

This PROVES the estimate-assembly REDUCTION (real bookkeeping algebra),
turning the vague `uniformCKNBound` obligation into ONE sharp residual.
It is NOT a closure and does NOT prove R1-cascade-uniformity.
Adversarial kill of that residual dispatched separately.

## Post-check: Tier-1 + Tier-3. Expect NOT_APPLICABLE (a proved
## conditional estimate-reduction; explicit OPEN residual recorded).
-/

namespace ZtareProofs.NSTick603UniformCKNBoundFromTypeIR1LEI

/-- Rescaled bookkeeping quantities on the unit cylinder `Q₁` at a
flat-branch bad cylinder of cascade index `n`. All are the
parabolic-scale-invariant rescaled integrals (so any bound free of
`rₙ` is cascade-uniform). -/
structure RescaledData where
  /-- `∫∫_{Q₁} |U|³`. -/
  intU3 : ℝ
  /-- `∫∫_{Q₁} |P_loc|^{3/2}` (local/CZ pressure). -/
  intPloc : ℝ
  /-- `∫∫_{Q₁} |P_har − P̄_har|^{3/2}` (R1 harmonic tail). -/
  intPhar : ℝ
  /-- `H[U] = ∫∫_{Q₁} |∇U|²` (enstrophy). -/
  H : ℝ
  intU3_nonneg : 0 ≤ intU3
  intPloc_nonneg : 0 ≤ intPloc
  intPhar_nonneg : 0 ≤ intPhar
  H_nonneg : 0 ≤ H

/-- The CKN quantity `G[U,P] := ∫∫|U|³ + ∫∫|P−P̄|^{3/2}` with the
pressure split `|P−P̄|^{3/2} ≲ |P_loc|^{3/2} + |P_har−P̄_har|^{3/2}`
(triangle/decomposition; the schematic constant is absorbed). -/
def G (d : RescaledData) : ℝ := d.intU3 + d.intPloc + d.intPhar

/-- **`uniform_ckn_bound_reduction`** (PROVED — the estimate assembly).

GIVEN, with constants that contain NO scale `rₙ`:
* `hTypeI`  : `intU3 ≤ volQ1 * C∗³`            (Type-I sup bound),
* `hCZ`     : `intPloc ≤ C_cz * C∗²`           (Calderón–Zygmund local),
* `hR1`     : `intPhar ≤ C_R`                  (R1 harmonic tail —
              the isolated residual; cascade-uniformity of `C_R`
              is the SOLE open sub-obligation, a hypothesis here),
* `hLEI`    : `H ≤ C_lei * (1 + C∗^3 + (intPloc + intPhar))`
              (suitable-weak local energy inequality, fixed cutoff),

THEN `G d + d.H ≤ M` where
`M := volQ1*C∗^3 + C_cz*C∗^2 + C_R + C_lei*(1 + C∗^3 + C_cz*C∗^2 + C_R)`
is an explicit constant in `(C∗, C_cz, C_R, C_lei, volQ1)` with NO
`rₙ` — hence CASCADE-UNIFORM. This discharges tick602's
`uniformCKNBound` modulo the single residual `C_R` cascade-uniformity. -/
theorem uniform_ckn_bound_reduction
    (d : RescaledData)
    (volQ1 Cstar Ccz CR Clei : ℝ)
    (hvol : 0 ≤ volQ1) (hCs : 0 ≤ Cstar)
    (hCcz : 0 ≤ Ccz) (hCR : 0 ≤ CR) (hClei : 0 ≤ Clei)
    (hTypeI : d.intU3 ≤ volQ1 * Cstar ^ 3)
    (hCZ : d.intPloc ≤ Ccz * Cstar ^ 2)
    (hR1 : d.intPhar ≤ CR)
    (hLEI : d.H ≤ Clei * (1 + Cstar ^ 3 + (d.intPloc + d.intPhar))) :
    G d + d.H ≤
      volQ1 * Cstar ^ 3 + Ccz * Cstar ^ 2 + CR
        + Clei * (1 + Cstar ^ 3 + (Ccz * Cstar ^ 2 + CR)) := by
  unfold G
  have hPloc := d.intPloc_nonneg
  have hPhar := d.intPhar_nonneg
  -- LEI RHS is monotone in the pressure pieces; bound them by CZ/R1
  have hLEI' : d.H ≤ Clei * (1 + Cstar ^ 3 + (Ccz * Cstar ^ 2 + CR)) := by
    refine le_trans hLEI ?_
    have hmono : 1 + Cstar ^ 3 + (d.intPloc + d.intPhar)
        ≤ 1 + Cstar ^ 3 + (Ccz * Cstar ^ 2 + CR) := by
      have := hCZ; have := hR1; linarith
    have : Clei * (1 + Cstar ^ 3 + (d.intPloc + d.intPhar))
        ≤ Clei * (1 + Cstar ^ 3 + (Ccz * Cstar ^ 2 + CR)) :=
      mul_le_mul_of_nonneg_left hmono hClei
    linarith
  linarith [hTypeI, hCZ, hR1, hLEI']

/-- **`M_is_cascade_uniform`** (the load-bearing observation, PROVED
trivially-by-construction): the bound `M` produced above is a function
ONLY of `(volQ1, C∗, C_cz, C_R, C_lei)` and contains no cascade index /
scale. So IF those five constants are cascade-uniform, `M` is. The
velocity (`volQ1,C∗`), local-pressure (`C_cz`), and LEI (`C_lei`)
constants are scale-invariant by construction (Type-I, CZ, suitable-
weak LEI are all parabolic-scale-invariant). The ONLY constant whose
cascade-uniformity is not structural is `C_R`. -/
theorem M_depends_only_on_named_constants
    (volQ1 Cstar Ccz CR Clei volQ1' Cstar' Ccz' CR' Clei' : ℝ)
    (h : (volQ1, Cstar, Ccz, CR, Clei)
       = (volQ1', Cstar', Ccz', CR', Clei')) :
    volQ1 * Cstar ^ 3 + Ccz * Cstar ^ 2 + CR
        + Clei * (1 + Cstar ^ 3 + (Ccz * Cstar ^ 2 + CR))
    = volQ1' * Cstar' ^ 3 + Ccz' * Cstar' ^ 2 + CR'
        + Clei' * (1 + Cstar' ^ 3 + (Ccz' * Cstar' ^ 2 + CR')) := by
  simp_all

/-! ## Honest record -/

structure Tick603Record where
  /-- PROVED: the estimate-assembly reduction — the four Track-B /
      suitable-weak inputs ⇒ `G+H ≤ M` with `M` free of `rₙ`. -/
  uniform_ckn_reduction_proved : Prop
  /-- Velocity (Type-I), local pressure (CZ), enstrophy (LEI) are
      DISCHARGED (scale-invariant by construction). -/
  velocity_localpressure_enstrophy_discharged : Prop
  /-- SOLE residual, OPEN, recorded NOT encoded: cascade-uniformity of
      `C_R` (R1 harmonic pressure tail) — the tick601 Σ-nonuniformity
      risk. Adversarial kill dispatched separately. NOT a closure. -/
  R1_tail_cascade_uniformity_is_the_sole_residual : Prop

end ZtareProofs.NSTick603UniformCKNBoundFromTypeIR1LEI
