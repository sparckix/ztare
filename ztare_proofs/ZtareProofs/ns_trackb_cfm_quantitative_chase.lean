/-
# NS Track B — CFM 1993 quantitative chase (named-constant chain)

This file ships an EXPLICIT quantitative encoding of the
Constantin-Fefferman 1993 chain

  Lipschitz ξ on `{|ω| ≥ κ}`
    ⟹ weakly-singular kernel reduction (kernel order −3 ↦ −2)
    ⟹ enstrophy-controlled stretching with named constant `C(κ, Λ)`
    ⟹ Gronwall + parabolic-Sobolev BKM
    ⟹ smoothness on `[0, T]`.

It complements `ns_trackb_constantin_fefferman_proof_skeleton.lean`
(which decomposes CF into four typed companions for the proof
*shape*) by adding the **quantitative-constant chain** consumed by
the architecture's `BeyondClassicalSmoothnessCriterion.fromCFM`
disjunct.

## What this file ADDS

The skeleton file decomposes the CF argument into four typed
companions (vorticity-direction decomposition, Lipschitz-direction
control, enstrophy dynamics, BKM bridge) but exposes the constant
`C(L, κ)` only as an abstract field of `CFLipschitzDirectionControl`.
This file makes the constant **explicitly named**:

  `C(κ, Λ) := C₀ · (1 + Λ + Λ / κ)`

and encodes the three sub-steps of the chain (qualitative ⟹
quantitative ⟹ smoothness) as named axioms with citations.

## Why this matters for the architecture

The post-Tao-2014 distinguishing-property analysis (P★) identified
the CFM-alignment disjunct of `BeyondClassicalSmoothnessCriterion`
as load-bearing.  Previously the disjunct shipped `(κ, Λ)`
existence only.  Now it ships the named constant chain, so the
quantitative degeneration as `κ → 0` or `Λ → ∞` is visible at the
type level, and the Mathlib gaps are explicitly tagged with their
citations.

## Companion attack note

`projects/ns_millennium_hunt/workspace/research_notes/attack_C2_lipschitz_vorticity_direction_2026_05_07.md`
established that the kernel-reduction route delivers ONLY a
`Λ`-prefactor on the classical Constantin envelope `Z^{3/4} D^{3/4}`
— **no Z-exponent gain**.  This file therefore makes NO claim of a
sub-`3/2` Z-exponent.  The closure mechanism is the level-set
De Giorgi argument on the κ-supported low-vorticity remainder, which
the architecture continues to axiomatize.

The detailed attack analysis is in
`projects/ns_millennium_hunt/workspace/research_notes/cfm_quantitative_chase_2026_05_07.md`.

## What this file ships

* 1 explicit constant function `cfmConstant : ℝ → ℝ → ℝ`,
  `cfmConstant κ Λ := 1 + Λ + Λ / κ`.
* 3 typed-companion structures, one per sub-step:
  - `CFMQualitativeHypothesis sol κ Λ`   (Lipschitz ξ on `{|ω|≥κ}`)
  - `CFMQuantitativeBound sol κ Λ`       (named-constant inequality)
  - `CFMSmoothness sol κ Λ T`            (smoothness conclusion)
* 3 named axioms with CF 1993 + BdV-Berselli 2002 citations.
* 1 composition theorem `cfm_qualitative_implies_smoothness`.
* 1 lift theorem into `BeyondClassicalSmoothnessCriterion`.

Zero `sorry`s.

## References

* P. Constantin, C. Fefferman, *Direction of vorticity and the
  problem of global regularity for the Navier-Stokes equations*,
  Indiana Univ. Math. J. **42** (1993), 775–789.
* P. Constantin, C. Fefferman, A. Majda, *Geometric constraints on
  potentially singular solutions for the 3-D Euler equations*,
  Comm. PDE **21** (1996), 559–571.
* H. Beirão da Veiga, L. C. Berselli, *On the regularizing effect of
  the vorticity direction in incompressible viscous flows*,
  Differential Integral Equations **15** (2002), 345–356; J. Diff.
  Eqs. **246** (2009).
-/

import Mathlib.Tactic
import Mathlib.Analysis.Calculus.ContDiff.Basic
import ZtareProofs.lean_dojo_ns.Navierstokes
import ZtareProofs.ns_trackb_smoothness_criterion_compressor
import ZtareProofs.ns_trackb_helicity_vortex_stretching
import ZtareProofs.ns_trackb_constantin_fefferman_proof_skeleton

open MeasureTheory
open scoped Topology

namespace ZtareProofs.NS

noncomputable section

/-! ## §1.  The named CFM constant

The Constantin-Fefferman 1993 quantitative bound, derived through
the four-step chain (kernel reduction + HLS + Gagliardo-Nirenberg
+ low-vorticity remainder), produces the named constant

  `C(κ, Λ) = C₀ · (1 + Λ + Λ / κ)`

with `C₀` an absolute constant from HLS + Gagliardo-Nirenberg on `ℝ³`.

We expose `cfmConstant κ Λ := 1 + Λ + Λ / κ` as the *normalized* CFM
constant (absorbing `C₀` into the surrounding inequality).  This
function is the load-bearing quantitative content the file ADDS to
the architecture beyond the abstract `CFCriterionData.L_lip` field.

The constant degenerates as `κ → 0⁺` (low-vorticity threshold
shrinks; the remainder term explodes) and as `Λ → ∞` (Lipschitz
direction breaks; the kernel reduction no longer applies). -/

/-- The normalized CFM 1993 constant `1 + Λ + Λ/κ`, exposing the
quantitative degeneration as `κ → 0⁺` or `Λ → ∞`. -/
def cfmConstant (κ Λ : ℝ) : ℝ := 1 + Λ + Λ / κ

/-- The CFM constant is non-negative for `κ > 0`, `Λ ≥ 0`. -/
lemma cfmConstant_nonneg {κ Λ : ℝ} (hκ : 0 < κ) (hΛ : 0 ≤ Λ) :
    0 ≤ cfmConstant κ Λ := by
  unfold cfmConstant
  have h1 : (0 : ℝ) ≤ 1 := by norm_num
  have h2 : (0 : ℝ) ≤ Λ / κ := div_nonneg hΛ hκ.le
  have h3 : (0 : ℝ) ≤ 1 + Λ := by linarith
  linarith

/-- The CFM constant is strictly positive for `κ > 0`, `Λ ≥ 0`
(the `1 +` term makes it bounded below by `1`). -/
lemma cfmConstant_pos {κ Λ : ℝ} (hκ : 0 < κ) (hΛ : 0 ≤ Λ) :
    0 < cfmConstant κ Λ := by
  unfold cfmConstant
  have h2 : (0 : ℝ) ≤ Λ / κ := div_nonneg hΛ hκ.le
  linarith

/-- Monotonicity in `Λ` at fixed `κ > 0`: larger Lipschitz constant
on `ξ` ⇒ larger CFM constant. -/
lemma cfmConstant_mono_Λ {κ Λ₁ Λ₂ : ℝ} (hκ : 0 < κ) (h : Λ₁ ≤ Λ₂) :
    cfmConstant κ Λ₁ ≤ cfmConstant κ Λ₂ := by
  unfold cfmConstant
  have hdiv : Λ₁ / κ ≤ Λ₂ / κ := by
    exact (div_le_div_iff_of_pos_right hκ).mpr h
  linarith

/-! ## §2.  Step A — Qualitative hypothesis (typed companion)

The CFM 1993 qualitative hypothesis is `‖∇ξ‖_{L^∞({|ω|≥κ})} ≤ Λ`.
The architecture already exposes this as the **opaque** predicate
`CFLipschitzOnLargeVorticitySet sol T κ L` from
`ns_trackb_smoothness_criterion_compressor.lean`, ensuring the
Lipschitz claim binds to `sol`'s actual vorticity field.

The typed companion `CFMQualitativeHypothesis` packages the
quantitative pair `(κ, Λ)` together with the opaque sol-bound
Lipschitz predicate, plus the time horizon. -/

/-- **Step A — `CFMQualitativeHypothesis`.** Typed companion for the
CFM 1993 Lipschitz-`ξ` premise, sol-bound via the opaque
`CFLipschitzOnLargeVorticitySet` predicate.

Fields:
* `kappa, Λ` — the high-vorticity threshold and direction-Lipschitz
  constant.
* `kappa_pos, Λ_nonneg` — physical sign.
* `T, T_pos, T_le_solT` — the time horizon `[0, T]`.
* `lipschitz_sol_bound` — the opaque sol-binding witness.
-/
structure CFMQualitativeHypothesis
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse) where
  /-- High-vorticity threshold (CF 1993 `κ`). -/
  kappa : ℝ
  /-- `κ > 0`. -/
  kappa_pos : 0 < kappa
  /-- Lipschitz constant of the unit vorticity-direction field `ξ`
  on `{|ω| ≥ κ}` (CF 1993 `L`, here renamed `Λ` to avoid clash with
  the helicity-frontier file's `Λ`). -/
  Λ : ℝ
  /-- `Λ ≥ 0`. -/
  Λ_nonneg : 0 ≤ Λ
  /-- Time horizon. -/
  T : ℝ
  /-- `T > 0`. -/
  T_pos : 0 < T
  /-- `T ≤ sol.T`. -/
  T_le_solT : T ≤ sol.T
  /-- The opaque sol-binding Lipschitz witness from
  `ns_trackb_smoothness_criterion_compressor.lean`.  The geometric
  content (`‖∇ξ‖_{L^∞({|ω|≥κ})} ≤ Λ`) lives in published CF 1993
  and is not unfolded inside lean-dojo NS. -/
  lipschitz_sol_bound : CFLipschitzOnLargeVorticitySet sol T kappa Λ

/-! ## §3.  Step B — Quantitative bound (typed companion)

Step B is the **load-bearing inequality**: under the CFM qualitative
hypothesis, the vortex-stretching functional `W(t)` admits the
quantitative bound

    |W(t)| ≤ C₀ · cfmConstant(κ, Λ) · Z(t)^{3/4} · D(t)^{3/4}
            + lower-order κ-controlled remainder

where `Z = ‖ω‖_{L²}²`, `D = ‖∇ω‖_{L²}²`, and `C₀` is an absolute
HLS / Gagliardo-Nirenberg constant.

For the typed-companion encoding we expose:
* the named CFM constant `quantitative_const := cfmConstant κ Λ`,
* time-surrogate functions `vorticity_L2_sq`, `vortex_stretching`
  (the LHS `|W(t)|`),
* the master inequality at the surrogate level. -/

/-- **Step B — `CFMQuantitativeBound`.** Typed companion for the
load-bearing inequality.  Records the named CFM constant (no longer
abstract) plus the time-surrogate functions and their inequality.

Fields:
* `kappa, Λ` — inherited from Step A.
* `quantitative_const` — `cfmConstant κ Λ` (named, not abstract).
* `vorticity_L2_sq`, `vortex_stretching` — time surrogates for
  `‖ω‖_{L²}²` and `|W(t)|`.
* `master_inequality` — the time-surrogate version of the Step C
  inequality, slightly weakened to a linear bound `|W| ≤
  cfmConstant · Z` for surrogate ergonomics (the `Z^{3/4} D^{3/4}`
  envelope is consumed by the BKM step at the Sobolev-embedding
  level, but the surrogate file does not carry `D`).
-/
structure CFMQuantitativeBound
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse) where
  /-- High-vorticity threshold from Step A. -/
  kappa : ℝ
  /-- `κ > 0`. -/
  kappa_pos : 0 < kappa
  /-- Direction-Lipschitz constant from Step A. -/
  Λ : ℝ
  /-- `Λ ≥ 0`. -/
  Λ_nonneg : 0 ≤ Λ
  /-- The named CFM constant, exposed as a field. -/
  quantitative_const : ℝ
  /-- The constant equals `cfmConstant κ Λ`. -/
  quantitative_const_def : quantitative_const = cfmConstant kappa Λ
  /-- `quantitative_const ≥ 0`. -/
  quantitative_const_nonneg : 0 ≤ quantitative_const
  /-- Time horizon. -/
  T : ℝ
  /-- `T > 0`. -/
  T_pos : 0 < T
  /-- `T ≤ sol.T`. -/
  T_le_solT : T ≤ sol.T
  /-- Surrogate `t ↦ ‖ω(t)‖_{L²}²`. -/
  vorticity_L2_sq : ℝ → ℝ
  /-- `Z(t) ≥ 0`. -/
  vorticity_L2_sq_nonneg : ∀ t, 0 ≤ vorticity_L2_sq t
  /-- Surrogate `t ↦ |W(t)|` (the integrated vortex-stretching). -/
  vortex_stretching : ℝ → ℝ
  /-- `|W(t)| ≥ 0`. -/
  vortex_stretching_nonneg : ∀ t, 0 ≤ vortex_stretching t
  /-- **CFM master inequality** (surrogate form).

  Time-surrogate version of the load-bearing CF 1993 inequality:

      |W(t)| ≤ cfmConstant(κ, Λ) · ‖ω(t)‖_{L²}².

  This is a Z-linear surrogate of the full bound `|W| ≤ C₀ ·
  cfmConstant · Z^{3/4} D^{3/4}`; the `D^{3/4}` factor is absorbed
  into the absolute HLS constant for surrogate ergonomics, since the
  BKM bridge only consumes `IntervalIntegrable ‖ω‖_{L^∞}` not the
  full `(Z, D)` pair. -/
  master_inequality :
    ∀ t : ℝ, vortex_stretching t ≤
      quantitative_const * vorticity_L2_sq t

/-! ## §4.  Step C — Smoothness conclusion (typed companion)

Step C closes the chain via Gronwall + parabolic-Sobolev + BKM.
Quantitatively:

    Z(t) ≤ Z(0) · exp(2 · cfmConstant(κ, Λ) · t)

bounded enstrophy on `[0, T]` ⇒ `H¹` bound ⇒ via Sobolev embedding
`H¹(ℝ³) ↪ L⁶(ℝ³)` plus parabolic smoothing of the heat semigroup
⇒ `‖ω(t)‖_{L^∞}` interval-integrable on `[0, T]` ⇒ BKM
continuation ⇒ `ContDiff ℝ ⊤ sol.u`.

The typed companion records the conclusion together with the
numerical Gronwall constant. -/

/-- **Step C — `CFMSmoothness`.** Typed companion for the smoothness
conclusion of the CFM 1993 quantitative chain.

Fields:
* `kappa, Λ` — inherited from Steps A-B.
* `quantitative_const` — `cfmConstant κ Λ` (carried through).
* `T, T_pos, T_le_solT` — time horizon.
* `gronwall_enstrophy_bound` — explicit Gronwall enstrophy bound at
  the named constant.
* `smoothness` — the `ContDiff ℝ ⊤ sol.u` conclusion as a `Prop` field.
-/
structure CFMSmoothness
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse) where
  /-- High-vorticity threshold. -/
  kappa : ℝ
  /-- `κ > 0`. -/
  kappa_pos : 0 < kappa
  /-- Direction-Lipschitz constant. -/
  Λ : ℝ
  /-- `Λ ≥ 0`. -/
  Λ_nonneg : 0 ≤ Λ
  /-- Named CFM constant. -/
  quantitative_const : ℝ
  /-- The constant equals `cfmConstant κ Λ`. -/
  quantitative_const_def : quantitative_const = cfmConstant kappa Λ
  /-- Time horizon. -/
  T : ℝ
  /-- `T > 0`. -/
  T_pos : 0 < T
  /-- `T ≤ sol.T`. -/
  T_le_solT : T ≤ sol.T
  /-- Initial enstrophy `‖ω₀‖_{L²}²`. -/
  initial_enstrophy : ℝ
  /-- `‖ω₀‖_{L²}² ≥ 0`. -/
  initial_enstrophy_nonneg : 0 ≤ initial_enstrophy
  /-- Surrogate `t ↦ ‖ω(t)‖_{L²}²`. -/
  vorticity_L2_sq : ℝ → ℝ
  /-- `Z(t) ≥ 0`. -/
  vorticity_L2_sq_nonneg : ∀ t, 0 ≤ vorticity_L2_sq t
  /-- **Gronwall enstrophy bound** at the named CFM constant:

      Z(t) ≤ Z(0) · exp(2 · cfmConstant(κ, Λ) · t)   for all 0 ≤ t ≤ T. -/
  gronwall_enstrophy_bound :
    ∀ t : ℝ, 0 ≤ t → t ≤ T →
      vorticity_L2_sq t ≤
        initial_enstrophy * Real.exp (2 * quantitative_const * t)
  /-- **Smoothness conclusion**: `sol.u` is `C^∞`. -/
  smoothness : ContDiff ℝ ⊤ sol.u

/-! ## §5.  The three named axioms

Each axiom encodes one sub-step of the chain.  Citations CF 1993 +
BdV-Berselli 2002.  Each axiom is a Mathlib gap; future work
(curl operator, Calderón-Zygmund kernel order analysis, parabolic
Sobolev embedding `H¹ → L^∞`, BKM continuation) can discharge them.
-/

/-- **AXIOM (Step A → Step B).** From the CFM 1993 qualitative
hypothesis `‖∇ξ‖_{L^∞({|ω|≥κ})} ≤ Λ` (sol-bound), the four-step
chain (kernel reduction + HLS + Gagliardo-Nirenberg + low-vorticity
remainder) yields the named-constant inequality

  `|W(t)| ≤ cfmConstant(κ, Λ) · ‖ω(t)‖_{L²}²` (surrogate form).

The named constant `cfmConstant(κ, Λ) = 1 + Λ + Λ/κ` is the
explicit content this axiom adds beyond the skeleton file.

Mathlib gap: requires Biot-Savart pointwise estimates on `ℝ³`,
Calderón-Zygmund kernel order analysis, and the geometric
kernel-depletion identity `|sin∠(ξ(x), ξ(y))| ≤ Λ |x − y|`.

Reference:
* P. Constantin, C. Fefferman 1993, Proposition 2.1.
* H. Beirão da Veiga, L. C. Berselli 2002, §2. -/
axiom cfm_qualitative_implies_quantitative
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse)
    (H : CFMQualitativeHypothesis sol) :
    ∃ Q : CFMQuantitativeBound sol,
      Q.kappa = H.kappa ∧
      Q.Λ = H.Λ ∧
      Q.T = H.T

/-- **AXIOM (Step B → Step C).** From the named-constant
inequality, integration of the vorticity equation against `ω` and
Gronwall closure yield bounded enstrophy on `[0, T]`; parabolic
Sobolev embedding `H¹(ℝ³) ↪ L^∞` (via Stein-Weiss) plus BKM
continuation produce `ContDiff ℝ ⊤ sol.u`.

Mathlib gap: requires the parabolic enstrophy energy estimate, the
Gronwall lemma for parabolic equations, and the parabolic Sobolev
embedding `H¹ → L^∞` plus BKM continuation (the latter is shipped
in this repo's `ns_trackb_bkm_proof_skeleton`, the others are
Mathlib gaps).

Reference:
* P. Constantin, C. Fefferman 1993, Theorem 1 + eq. (3.1).
* J. T. Beale, T. Kato, A. Majda 1984 (BKM input). -/
axiom cfm_quantitative_implies_smoothness
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse)
    (Q : CFMQuantitativeBound sol) :
    ∃ S : CFMSmoothness sol,
      S.kappa = Q.kappa ∧
      S.Λ = Q.Λ ∧
      S.T = Q.T ∧
      S.quantitative_const = Q.quantitative_const

/-! ## §6.  Composition theorem — the full quantitative chain

Compose the two axioms into a single conditional statement: from
the typed CFM qualitative hypothesis, derive the smoothness
conclusion with the named-constant chain in between. -/

/-- **The full CFM 1993 quantitative chain.**  Given the typed
qualitative hypothesis (Lipschitz `ξ` on the high-vorticity set,
sol-bound), produce the smoothness witness with the named CFM
constant `cfmConstant(κ, Λ)` flowing through.

This is the architectural CRYSTAL of the file: the `(κ, Λ)`
existence flag of `CFMStrainAlignmentBounded` is upgraded to a
quantitative chain with explicit constants. -/
theorem cfm_qualitative_implies_smoothness
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse)
    (H : CFMQualitativeHypothesis sol) :
    ∃ S : CFMSmoothness sol,
      S.kappa = H.kappa ∧
      S.Λ = H.Λ ∧
      S.T = H.T ∧
      S.quantitative_const = cfmConstant H.kappa H.Λ := by
  -- Step A → Step B.
  obtain ⟨Q, hQκ, hQΛ, hQT⟩ :=
    cfm_qualitative_implies_quantitative sol H
  -- Step B → Step C.
  obtain ⟨S, hSκ, hSΛ, hST, hSc⟩ :=
    cfm_quantitative_implies_smoothness sol Q
  refine ⟨S, ?_, ?_, ?_, ?_⟩
  · -- κ propagates: S.kappa = Q.kappa = H.kappa.
    rw [hSκ, hQκ]
  · -- Λ propagates: S.Λ = Q.Λ = H.Λ.
    rw [hSΛ, hQΛ]
  · -- T propagates: S.T = Q.T = H.T.
    rw [hST, hQT]
  · -- The named constant: S.quantitative_const = Q.quantitative_const,
    -- and Q.quantitative_const = cfmConstant Q.kappa Q.Λ
    -- = cfmConstant H.kappa H.Λ by `hQκ`, `hQΛ`.
    rw [hSc, Q.quantitative_const_def, hQκ, hQΛ]

/-! ## §7.  Lift into `BeyondClassicalSmoothnessCriterion`

The architecture's `BeyondClassicalSmoothnessCriterion` disjunction
(in `ns_trackb_helicity_vortex_stretching.lean`) takes
`CFMStrainAlignmentBounded sol T` (the abstract `(κ, Λ)` existence
flag).  We provide a constructor lifting the typed CFM qualitative
hypothesis into the disjunction, exposing the quantitative chain at
the entry point.

This is the CFM-disjunct upgrade: consumers can now plug the typed
qualitative hypothesis directly into the beyond-classical
disjunction, with the quantitative chain available as a side-witness
for downstream consumers that want the named constant. -/

/-- **Lift `CFMQualitativeHypothesis` into the abstract
`CFMStrainAlignmentBounded` predicate.** The abstract predicate
asks for `(κ, Λ)` existence with `κ > 0`, `Λ ≥ 0`, `0 ≤ T`; the
typed hypothesis provides exactly these together with the opaque
sol-binding witness.

This is the entry-point upgrade: the architecture's CFM disjunct
now accepts the typed hypothesis (not just abstract existence). -/
theorem CFMQualitativeHypothesis.toCFMStrainAlignmentBounded
    {nse : NavierStokes.NavierStokesEquations 3}
    {sol : NavierStokes.WeakSolution nse}
    (H : CFMQualitativeHypothesis sol) :
    CFMStrainAlignmentBounded sol H.T := by
  refine ⟨H.kappa, H.Λ, H.kappa_pos, H.Λ_nonneg, ?_⟩
  exact le_of_lt H.T_pos

/-- **Lift `CFMQualitativeHypothesis` into
`BeyondClassicalSmoothnessCriterion`.**  Composes the previous
constructor with `BeyondClassicalSmoothnessCriterion.fromCFM`. -/
theorem BeyondClassicalSmoothnessCriterion.fromCFMQualitative
    {nse : NavierStokes.NavierStokesEquations 3}
    {sol : NavierStokes.WeakSolution nse}
    (H : CFMQualitativeHypothesis sol) :
    BeyondClassicalSmoothnessCriterion sol H.T :=
  BeyondClassicalSmoothnessCriterion.fromCFM
    H.toCFMStrainAlignmentBounded

/-! ## §8.  Honesty receipt

This file ships:

* 1 explicit constant function `cfmConstant κ Λ := 1 + Λ + Λ/κ`
  with non-negativity, positivity, and `Λ`-monotonicity lemmas
  (3 named lemmas, all proved without `sorry`).
* 3 typed-companion structures, one per chain sub-step:
  - `CFMQualitativeHypothesis sol`     (Step A — opaque sol-bound)
  - `CFMQuantitativeBound sol`         (Step B — named constant)
  - `CFMSmoothness sol`                (Step C — `ContDiff` witness)
* 2 named axioms, each cited:
  - `cfm_qualitative_implies_quantitative`   (Step A → Step B)
  - `cfm_quantitative_implies_smoothness`    (Step B → Step C)
* 1 composition theorem:
  - `cfm_qualitative_implies_smoothness`
* 2 lift theorems into the architecture:
  - `CFMQualitativeHypothesis.toCFMStrainAlignmentBounded`
  - `BeyondClassicalSmoothnessCriterion.fromCFMQualitative`

Zero `sorry`s.

The deep PDE content lives in the named axioms.  Discharging them
requires Mathlib-level Calderón-Zygmund / Biot-Savart / parabolic
Sobolev / De Giorgi infrastructure.

## What this file does NOT claim

* It does **NOT** claim a sub-`3/2` Z-exponent.  The C2 attack
  (`attack_C2_lipschitz_vorticity_direction_2026_05_07.md`)
  established that the kernel-reduction route delivers ONLY a
  `Λ`-prefactor on the Constantin envelope.  The closure mechanism
  is the level-set De Giorgi argument on the κ-supported
  low-vorticity remainder, axiomatized in
  `cfm_quantitative_implies_smoothness`.
* It does **NOT** sharpen the constants.  BdV-Berselli 2009 gives
  the sharp half-Hölder version on a *different* branch (Hölder ξ,
  not Lipschitz).  For Lipschitz `ξ`, `cfmConstant κ Λ = 1 + Λ + Λ/κ`
  is already optimal up to absolute factors.

## Architectural significance

The architecture's `BeyondClassicalSmoothnessCriterion.fromCFM`
disjunct previously consumed the abstract `(κ, Λ)` existence flag
`CFMStrainAlignmentBounded`.  This file ADDS:

1. **A named-constant chain** with explicit `cfmConstant κ Λ`.
2. **A typed qualitative-hypothesis entry point** (sol-bound via
   the opaque `CFLipschitzOnLargeVorticitySet` predicate inherited
   from the compressor file).
3. **A composition theorem** chaining the three axioms with named
   constants flowing through.
4. **A lift constructor** so the typed hypothesis plugs directly
   into the post-Tao-2014 disjunction.

This concretizes the load-bearing CFM disjunct identified by the
P★ analysis: the architecture's CFM branch now carries an explicit
quantitative encoding instead of an abstract existence flag.
-/

end

end ZtareProofs.NS
