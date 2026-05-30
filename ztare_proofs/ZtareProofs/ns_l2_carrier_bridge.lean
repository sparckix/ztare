import Mathlib.Tactic
import ZtareProofs.ns_exhaust_scale_reserve_bridge
import ZtareProofs.ns_quadrupole_identity

namespace ZtareProofs

/-!
`ns_l2_carrier_bridge` rewrites the Phase 5CG gap in representation language.

The replay and proxy backtest suggest the proof object is not full-profile
compactness and not raw anisotropy collapse. The surviving candidate is a
low-order anisotropic carrier, plausibly the `l = 2` quadrupole channel,
renormalized by an active radial grade.

This file does not prove that `l = 2` is the correct carrier. It names the
exact theorem shape that would make the current branch proof-facing.
-/

/-- Effective amplitude of the first stretching-relevant anisotropic carrier. -/
abbrev L2CarrierAmplitude := Real

/-- Active radial grade or spectral scale associated to a localized patch. -/
abbrev RadialGrade := Real

/-- Coherent stretching available to the next danger cycle. -/
abbrev StretchReserve := Real

/-- Residual higher-mode anisotropic carrier after the `l = 2` channel is removed. -/
abbrev HigherModeCarrierAmplitude := Real

/-- Instantaneous deviatoric quadrupole carrier built from vorticity. -/
abbrev DeviatoricQuadrupoleCarrier := Real

/-- Renormalized `l = 2` carrier strength per active radial grade. -/
noncomputable def l2CarrierPerScale
    (a : L2CarrierAmplitude) (r : RadialGrade) : Real :=
  a / max r 1

/-- The effective stretch reserve factors through the renormalized `l = 2` carrier. -/
def coherentStretchFactorsThroughL2
    (reserve carrierPerScale C : Real) : Prop :=
  reserve ≤ C * carrierPerScale

/--
Residual higher-mode anisotropy is subcritical once measured per active radial
grade. This is the explicit "no hidden carrier in `l ≥ 4`" obligation.
-/
def higherModesSubcritical
    (higherCarrier r C cap : Real) : Prop :=
  C * (higherCarrier / max r 1) ≤ cap

/-- One-step contraction of the renormalized `l = 2` carrier. -/
def l2CarrierContracts
    (a0 a1 r0 r1 q : Real) : Prop :=
  l2CarrierPerScale a1 r1 ≤ q * l2CarrierPerScale a0 r0

/--
Exact representation-theoretic bridge target.

If the effective coherent stretch factors through the renormalized `l = 2`
carrier and that carrier contracts by a factor `q < 1`, then the reserve is
controlled by a contractive anisotropic channel rather than raw profile shape.
-/
def l2CarrierBridgeTarget
    (reserve0 reserve1 a0 a1 r0 r1 C q : Real) : Prop :=
  coherentStretchFactorsThroughL2 reserve1 (l2CarrierPerScale a1 r1) C ∧
    l2CarrierContracts a0 a1 r0 r1 q

/--
Thresholded version intended to feed the exhaust-discount bridge.
-/
def l2CarrierCapTarget
    (reserve1 a1 r1 C cap : Real) : Prop :=
  coherentStretchFactorsThroughL2 reserve1 (l2CarrierPerScale a1 r1) C ∧
    C * l2CarrierPerScale a1 r1 ≤ cap

/--
Sharper factorization target for the current branch.

This makes explicit the two unpaid obligations hidden in the current story:

1. coherent stretch really factors through the renormalized `l = 2` carrier;
2. renormalized higher-mode carriers are already subcritical, so the `l = 2`
   channel is not just a decoy while `l ≥ 4` secretly carries the reserve.

The panel review sharpened this further:
the exact algebraic part is only the instantaneous quadrupole contraction
identity; the renormalized carrier statement below is a PDE bridge target,
not a representation-theoretic identity.
-/
def l2CarrierFactorizationTarget
    (reserve1 l2 higher r C cap : Real) : Prop :=
  coherentStretchFactorsThroughL2 reserve1 (l2CarrierPerScale l2 r) C ∧
    higherModesSubcritical higher r C cap

/--
If the `l = 2` carrier cap target is paid, the reserve falls below the same
cap. This is the clean contractive carrier statement we would want before
returning to the recurrence bridge.
-/
theorem stretch_reserve_capped_of_l2CarrierCapTarget
    {reserve1 a1 r1 C cap : Real}
    (hcap : l2CarrierCapTarget reserve1 a1 r1 C cap) :
    reserve1 ≤ cap := by
  rcases hcap with ⟨hfactor, hbound⟩
  unfold coherentStretchFactorsThroughL2 at hfactor
  linarith

/--
If the sharper factorization target is paid and the `l = 2` carrier itself is
below the same cap, then the reserve is capped and the higher modes are
already harmless at that scale.
-/
theorem stretch_reserve_capped_of_l2CarrierFactorizationTarget
    {reserve1 l2 higher r C cap : Real}
    (hfactor : l2CarrierFactorizationTarget reserve1 l2 higher r C cap)
    (hl2 : C * l2CarrierPerScale l2 r ≤ cap) :
    reserve1 ≤ cap ∧ higherModesSubcritical higher r C cap := by
  rcases hfactor with ⟨hreserve, hhigher⟩
  unfold coherentStretchFactorsThroughL2 at hreserve
  constructor
  · linarith
  · exact hhigher

/--
The exact quadrupole algebra already shipped in `ns_quadrupole_identity`
is the only part of the `l = 2` route that is exact without further PDE input.
-/
theorem instantaneous_quadrupole_layer_is_exact
    {stretchDensity quadrupoleContraction quadrupoleNorm strainNorm : Real}
    (hid : strainContractionEqQuadrupoleContraction stretchDensity quadrupoleContraction)
    (hbound : |quadrupoleContraction| ≤ quadrupoleNorm * strainNorm) :
    strainContractionLeQuadrupoleNormMulStrainNorm stretchDensity quadrupoleNorm strainNorm := by
  exact strain_contraction_le_quadrupole_norm_mul_strain_norm_of_identity hid hbound

end ZtareProofs
