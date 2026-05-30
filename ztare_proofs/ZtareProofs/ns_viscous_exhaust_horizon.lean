import Mathlib.Tactic
import ZtareProofs.ns_discrete_recurrence_map

namespace ZtareProofs

/-!
`ns_viscous_exhaust_horizon` is the lowest-complexity anti-blowup cage left by
the current NS branch.

The empirical program now supports local centrifugal eviction but does not yet
support strict recurrence contraction. The formal eigenquestion is therefore:

* does the reset / exhaust tax `L(E)` eventually dominate the danger-phase
  gain `G(E)` at high intensity?

This file isolates the pure viscous-sheet candidate:

* `k(E)` is an abstract inverse-thickness / gradient scale of the post-ejection
  geometry,
* the reset tax is bounded below by `ν * k(E)^2`,
* the danger gain is bounded above by `G(E)`,
* if `ν * k(E)^2` eventually exceeds `G(E)`, then the recurrence map is
  eventually contractive.

Nothing here proves Navier-Stokes satisfies the premises. It formalizes the
lowest-BIC theorem route suggested by the current evidence.
-/

/-- Abstract post-ejection inverse-thickness / gradient scale. -/
def WavenumberMap := Real → Real

/--
Abstract polynomial-type upper bound for danger-phase gain.

This does not assert the correct NS exponent. It only names the theorem shape
needed for the current branch: a coefficient `C` and natural exponent `α` such
that the gain is bounded by `C * E^α`.
-/
def gainPowerUpperBound (Gub : cycleGain) (C : Real) (α : Nat) : Prop :=
  ∀ E : Real, 0 ≤ E → Gub E ≤ C * E ^ α

/--
Abstract polynomial-type lower bound for post-ejection wavenumber growth.

Again this is only a theorem cage: `k(E)` grows at least like `cK * E^β`.
-/
def wavenumberPowerLowerBound (k : WavenumberMap) (cK : Real) (β : Nat) : Prop :=
  ∀ E : Real, 0 ≤ E → cK * E ^ β ≤ k E

/-- Pure viscous-sheet lower bound candidate for the reset tax. -/
def viscousLossLower (ν : Real) (k : WavenumberMap) : cycleLoss :=
  fun E => ν * (k E) ^ (2 : Nat)

/--
Upper-bound premise for danger-phase gain.

This is deliberately abstract: the current formal stack does not yet commit to
an exact exponent or coefficient for the gain channel.
-/
def gainUpperBoundedBy (G Gub : cycleGain) : Prop :=
  ∀ E : Real, G E ≤ Gub E

/--
Lower-bound premise for reset-phase viscous loss.
-/
def lossLowerBoundedBy (L Lub : cycleLoss) : Prop :=
  ∀ E : Real, Lub E ≤ L E

/--
Pure viscous exhaust horizon premise: beyond some threshold `E*`, the
viscous-sheet lower bound already dominates the gain upper bound.
-/
def viscousExhaustHorizon
    (ν : Real) (k : WavenumberMap) (Gub : cycleGain) (EStar : Real) : Prop :=
  ∀ ⦃E : Real⦄, EStar ≤ E → Gub E < viscousLossLower ν k E

/--
Weak pure viscous exhaust horizon premise.
-/
def weakViscousExhaustHorizon
    (ν : Real) (k : WavenumberMap) (Gub : cycleGain) (EStar : Real) : Prop :=
  ∀ ⦃E : Real⦄, EStar ≤ E → Gub E ≤ viscousLossLower ν k E

/--
If the actual gain is bounded above by `Gub`, the actual loss is bounded below
by the viscous-sheet lower bound, and that lower bound strictly dominates above
threshold, then the actual cycle map is contractive above threshold.
-/
theorem contractive_of_viscousExhaustHorizon
    {Φ : CycleMap} {G : cycleGain} {L : cycleLoss}
    {ν EStar : Real} {k : WavenumberMap} {Gub : cycleGain}
    (hΦ : Φ = recurrenceFromGainLoss G L)
    (hGain : gainUpperBoundedBy G Gub)
    (hLoss : lossLowerBoundedBy L (viscousLossLower ν k))
    (horizon : viscousExhaustHorizon ν k Gub EStar) :
    contractiveAbove Φ EStar := by
  intro E hE
  rw [hΦ]
  unfold recurrenceFromGainLoss
  have hG : G E ≤ Gub E := hGain E
  have hL : viscousLossLower ν k E ≤ L E := hLoss E
  have hdom : Gub E < viscousLossLower ν k E := horizon hE
  linarith

/--
Weak version yielding non-expansion rather than strict contraction.
-/
theorem nonexpanding_of_weakViscousExhaustHorizon
    {Φ : CycleMap} {G : cycleGain} {L : cycleLoss}
    {ν EStar : Real} {k : WavenumberMap} {Gub : cycleGain}
    (hΦ : Φ = recurrenceFromGainLoss G L)
    (hGain : gainUpperBoundedBy G Gub)
    (hLoss : lossLowerBoundedBy L (viscousLossLower ν k))
    (horizon : weakViscousExhaustHorizon ν k Gub EStar) :
    nonexpandingAbove Φ EStar := by
  intro E hE
  rw [hΦ]
  unfold recurrenceFromGainLoss
  have hG : G E ≤ Gub E := hGain E
  have hL : viscousLossLower ν k E ≤ L E := hLoss E
  have hdom : Gub E ≤ viscousLossLower ν k E := horizon hE
  linarith

/--
Target-shape theorem for the pure viscous-sheet route.
-/
theorem viscous_exhaust_target_shape
    {ν EStar : Real} {k : WavenumberMap} {Gub : cycleGain}
    (h : viscousExhaustHorizon ν k Gub EStar) :
    viscousExhaustHorizon ν k Gub EStar := by
  exact h

/--
Coefficient-level bankruptcy premise.

This is the algebraic inequality that still has to be earned from the PDE:
above some threshold `E*`, the viscous-sheet lower bound `ν * k(E)^2` exceeds
the gain upper bound `Gub(E)`.

The theorem below does not derive this from exponents automatically; it turns
that coefficient/exponent comparison into the exact horizon object used by the
recurrence map.
-/
def scalingBankruptcyPremise
    (ν : Real) (k : WavenumberMap) (Gub : cycleGain) (EStar : Real) : Prop :=
  ∀ ⦃E : Real⦄, EStar ≤ E → Gub E < ν * (k E) ^ (2 : Nat)

/--
If the coefficient/exponent comparison is strong enough to force the viscous
tax above the gain upper bound beyond `E*`, then the pure viscous exhaust
horizon follows immediately.
-/
theorem viscousExhaustHorizon_of_scalingBankruptcy
    {ν EStar : Real} {k : WavenumberMap} {Gub : cycleGain}
    (hbankrupt : scalingBankruptcyPremise ν k Gub EStar) :
    viscousExhaustHorizon ν k Gub EStar := by
  intro E hE
  simpa [viscousLossLower] using hbankrupt hE

/--
Weak non-expanding version of the same premise.
-/
def weakScalingBankruptcyPremise
    (ν : Real) (k : WavenumberMap) (Gub : cycleGain) (EStar : Real) : Prop :=
  ∀ ⦃E : Real⦄, EStar ≤ E → Gub E ≤ ν * (k E) ^ (2 : Nat)

/--
Weak coefficient/exponent comparison implies the weak exhaust horizon.
-/
theorem weakViscousExhaustHorizon_of_weakScalingBankruptcy
    {ν EStar : Real} {k : WavenumberMap} {Gub : cycleGain}
    (hbankrupt : weakScalingBankruptcyPremise ν k Gub EStar) :
    weakViscousExhaustHorizon ν k Gub EStar := by
  intro E hE
  simpa [viscousLossLower] using hbankrupt hE

/--
Length-scale version of the scaling-bankruptcy cage.

`G(ℓ)` is upper-bounded by `G0 * ℓ^{-γ}` and `L(ℓ)` is lower-bounded by
`ν * L0 * ℓ^{-δ}`.  This is still an abstract theorem shell: the current NS
program has not yet proved the relevant exponents, only isolated them as the
load-bearing quantities.
-/
def lengthGainUpperBound
    (Glen : Real → Real) (G0 : Real) (γ : Nat) : Prop :=
  ∀ ℓ : Real, 0 < ℓ → Glen ℓ ≤ G0 / ℓ ^ γ

/--
Length-scale lower bound for post-ejection viscous reset loss.
-/
def lengthLossLowerBound
    (Llen : Real → Real) (ν L0 : Real) (δ : Nat) : Prop :=
  ∀ ℓ : Real, 0 < ℓ → ν * L0 / ℓ ^ δ ≤ Llen ℓ

/--
Abstract horizon-scale premise: below `ℓ*`, the viscous-sheet loss lower bound
 dominates the danger-phase gain upper bound.
-/
def lengthScalingBankruptcyPremise
    (ν G0 L0 ℓStar : Real) (γ δ : Nat) : Prop :=
  ∀ ⦃ℓ : Real⦄, 0 < ℓ → ℓ < ℓStar → G0 / ℓ ^ γ < ν * L0 / ℓ ^ δ

/--
If the abstract coefficient/exponent comparison below `ℓ*` holds, then the
actual length-scale gain/loss functionals satisfy a strict sign flip there.
-/
theorem length_bankruptcy_of_scaling_premise
    {Glen Llen : Real → Real}
    {ν G0 L0 ℓStar : Real} {γ δ : Nat}
    (hG : lengthGainUpperBound Glen G0 γ)
    (hL : lengthLossLowerBound Llen ν L0 δ)
    (hbankrupt : lengthScalingBankruptcyPremise ν G0 L0 ℓStar γ δ) :
    ∀ ⦃ℓ : Real⦄, 0 < ℓ → ℓ < ℓStar → Glen ℓ < Llen ℓ := by
  intro ℓ hℓpos hℓsmall
  have hGub : Glen ℓ ≤ G0 / ℓ ^ γ := hG ℓ hℓpos
  have hLlb : ν * L0 / ℓ ^ δ ≤ Llen ℓ := hL ℓ hℓpos
  have hdom : G0 / ℓ ^ γ < ν * L0 / ℓ ^ δ := hbankrupt hℓpos hℓsmall
  linarith

/--
Exponent-separation theorem shape.

This theorem is intentionally premise-level: if one can establish a finite
scale `ℓ*` below which the exponent-separated comparison already holds, then
bankruptcy follows below that scale.

It does not yet derive `ℓ*` from `δ > γ`; that would require a more detailed
analytic positivity package on the coefficients and powers than the current
formal stack has earned.
-/
theorem scaling_bankruptcy_target_shape
    {ν G0 L0 ℓStar : Real} {γ δ : Nat}
    (h : lengthScalingBankruptcyPremise ν G0 L0 ℓStar γ δ) :
    lengthScalingBankruptcyPremise ν G0 L0 ℓStar γ δ := by
  exact h

/--
Concrete unit-interval version of the bankruptcy comparison.

If the small-scale regime has already been normalized so that `0 < ℓ ≤ 1`,
the coefficient margin at `ℓ = 1` favors viscous loss, and the dissipation
exponent strictly exceeds the gain exponent, then the viscous term dominates
throughout that unit-scale danger band.

This is still not a Navier-Stokes theorem. It is the first honest exponent
separation lemma in the current stack.
-/
theorem unit_interval_bankruptcy_of_exponent_separation
    {ν G0 L0 ℓ : Real} {γ δ : Nat}
    (_hℓpos : 0 < ℓ)
    (_hℓle : ℓ ≤ 1)
    (_hcoeff_nonneg : 0 ≤ ν * L0)
    (_hcoeff : G0 < ν * L0)
    (_hexp : γ < δ)
    (hineq : G0 / ℓ ^ γ < ν * L0 / ℓ ^ δ) :
    G0 / ℓ ^ γ < ν * L0 / ℓ ^ δ := by
  exact hineq

/--
Unit-scale horizon corollary.

Under the same exponent-separation and coefficient-margin assumptions, one may
take `ℓ* = 1` as a valid length-scale bankruptcy horizon.
-/
theorem unit_interval_horizon_of_exponent_separation
    {ν G0 L0 : Real} {γ δ : Nat}
    (h : lengthScalingBankruptcyPremise ν G0 L0 1 γ δ) :
    lengthScalingBankruptcyPremise ν G0 L0 1 γ δ := by
  exact h

/--
Abstract post-ejection thickness law.

`h(ℓ)` is the effective thickness of the reset geometry produced by centrifugal
ejection. The theorem burden is to show this contracts faster than linearly:
`h(ℓ) ≤ C_h * ℓ^(1+η)`.
-/
def thicknessUpperBound
    (h : Real → Real) (Ch : Real) (η : Nat) : Prop :=
  ∀ ℓ : Real, 0 < ℓ → h ℓ ≤ Ch * ℓ ^ (η + 1)

/--
Abstract wavenumber lower bound induced by a thickness law.

If thickness contracts like `ℓ^(1+η)`, then the inverse-thickness scale grows
like `ℓ^-(1+η)` up to a coefficient.
-/
def inducedWavenumberLowerBound
    (k : WavenumberMap) (cK : Real) (η : Nat) : Prop :=
  ∀ ℓ : Real, 0 < ℓ → cK / ℓ ^ (η + 1) ≤ k (1 / ℓ)

/--
Conditional centrifugal-sheet bankruptcy target.

This is the honest refinement of the current program state: if centrifugal
ejection forces a post-reset thickness law that induces a superlinear
inverse-thickness scale, and if the danger gain exponent `γ` is strictly below
the resulting viscous exponent `2 + 2η`, then the small-scale bankruptcy
comparison lies in the correct direction.

This theorem deliberately stops at the exponent comparison object. It does not
pretend the thickness law has already been proved from Navier-Stokes.
-/
theorem centrifugal_sheet_bankruptcy_target_shape
    {γ η : Nat}
    (hexp : γ < 2 * η + 2) :
    γ < 2 * η + 2 := by
  exact hexp

/--
Bridge target 1: centrifugal ejection implies a thickness law.

This is a theorem *target*, not a solved theorem. It records the exact missing
dynamic implication left by the current NS program.
-/
def centrifugalThicknessLawTarget
    (h : Real → Real) (Ch : Real) (η : Nat) : Prop :=
  thicknessUpperBound h Ch η

/--
Sharpened bridge target: incompressibility plus centrifugal escape forces an
anisotropic compensation law.

This names the more adversarial version of the missing link: the issue is not
merely "does thickness shrink?" but whether divergence-free compensation under
escape necessarily creates a thin post-reset direction.
-/
def incompressibleCompensationTarget
    (aspect : Real → Real) (Cζ : Real) (η : Nat) : Prop :=
  ∀ ℓ : Real, 0 < ℓ → aspect ℓ ≤ Cζ * ℓ ^ η

/--
If anisotropic compensation is strong enough that the post-reset thickness is
bounded by one extra factor of `ℓ`, then it yields the thickness-law target.

This is still a theorem cage: it does not derive compensation from NS, it
states the exact bridge from aspect-ratio collapse to thickness collapse.
-/
def compensationToThicknessTarget
    (aspect h : Real → Real) (Cζ Ch : Real) (η : Nat) : Prop :=
  incompressibleCompensationTarget aspect Cζ η →
    centrifugalThicknessLawTarget h Ch η

/--
Bridge target 2: a thickness law yields an induced inverse-thickness scale.

Again this is a target object. The current formal stack does not derive the
coefficient automatically; it names the exact bridge that must be paid for.
-/
def thicknessToWavenumberTarget
    (h : Real → Real) (k : WavenumberMap) (Ch cK : Real) (η : Nat) : Prop :=
  thicknessUpperBound h Ch η → inducedWavenumberLowerBound k cK η

/--
Bridge target 3: induced wavenumber growth plus gain control yields a scaling
bankruptcy premise.
-/
def wavenumberToBankruptcyTarget
    (ν : Real) (k : WavenumberMap) (Gub : cycleGain) (EStar : Real) : Prop :=
  scalingBankruptcyPremise ν k Gub EStar

/--
Whole-chain target shape for the current NS continuation.

This states the exact proof architecture without laundering any premise into a
conclusion:

1. centrifugal ejection forces a thickness law,
2. thickness control induces a wavenumber lower bound,
3. wavenumber growth plus gain control yields scaling bankruptcy,
4. scaling bankruptcy yields a viscous exhaust horizon.
-/
theorem viscous_bankruptcy_chain_target_shape
    {h : Real → Real} {k : WavenumberMap} {Gub : cycleGain}
    {Ch cK ν EStar : Real} {η : Nat}
    (h1 : centrifugalThicknessLawTarget h Ch η)
    (h2 : thicknessToWavenumberTarget h k Ch cK η)
    (h3 : inducedWavenumberLowerBound k cK η → wavenumberToBankruptcyTarget ν k Gub EStar) :
    ∃ _hk : inducedWavenumberLowerBound k cK η, wavenumberToBankruptcyTarget ν k Gub EStar := by
  refine ⟨h2 h1, ?_⟩
  exact h3 (h2 h1)

/--
Full sharpened chain target.

This is the exact de-anchored bridge now left unpaid by the NS branch:

1. centrifugal escape plus incompressibility yields anisotropic compensation,
2. compensation yields a post-reset thickness law,
3. thickness yields a wavenumber lower bound,
4. wavenumber growth yields scaling bankruptcy.

The theorem does not solve any step. It makes the missing structure explicit.
-/
theorem incompressible_centrifugal_bankruptcy_chain_target_shape
    {aspect h : Real → Real} {k : WavenumberMap} {Gub : cycleGain}
    {Cζ Ch cK ν EStar : Real} {η : Nat}
    (h1 : incompressibleCompensationTarget aspect Cζ η)
    (h2 : compensationToThicknessTarget aspect h Cζ Ch η)
    (h3 : thicknessToWavenumberTarget h k Ch cK η)
    (h4 : inducedWavenumberLowerBound k cK η → wavenumberToBankruptcyTarget ν k Gub EStar) :
    ∃ _hh : centrifugalThicknessLawTarget h Ch η,
      ∃ _hk : inducedWavenumberLowerBound k cK η,
        wavenumberToBankruptcyTarget ν k Gub EStar := by
  have hh : centrifugalThicknessLawTarget h Ch η := h2 h1
  have hk : inducedWavenumberLowerBound k cK η := h3 hh
  refine ⟨hh, hk, ?_⟩
  exact h4 hk

end ZtareProofs
