import Mathlib.Data.Real.Basic

/-!
# Dynamic admissibility pivot for near-stealth pressure cancellation

Phase 5AS demoted the static pressure-footprint route: a large finite local
incompressible jet family can nearly cancel the moving-axis projected pressure
moment while preserving a strong torque.  This file records the replacement
theorem cage.

The load-bearing object is no longer the static implication

`active torque -> projected pressure footprint`.

It is the dynamic implication

`near stealth + NS vector field transverse to stealth manifold -> not
admissible for a reset dwell`.

This is intentionally abstract.  The PDE obligation is to prove the
transversality lower bound for actual Navier-Stokes reset trajectories.
-/

namespace ZtareProofs.NS

structure DynamicStealthState where
  residual : ℝ
  residualDot : ℝ
  residualSecondDot : ℝ := 0
  dwellTime : ℝ
  exposureTime : ℝ
  torque : ℝ

def positiveTorque (s : DynamicStealthState) : Prop :=
  0 < s.torque

def exposureTimeDef (s : DynamicStealthState) : Prop :=
  0 < |s.residualDot| ∧ s.exposureTime = |s.residual| / |s.residualDot|

def dynamicallyRepelled (s : DynamicStealthState) : Prop :=
  exposureTimeDef s ∧ 0 < s.exposureTime ∧ s.exposureTime < s.dwellTime

def resetStealthAdmissible (s : DynamicStealthState) : Prop :=
  positiveTorque s ∧ s.dwellTime ≤ s.exposureTime

def materialDerivativeLowerBound (s : DynamicStealthState) (c : ℝ) : Prop :=
  0 < c ∧ c ≤ |s.residualDot|

def secondMaterialDerivativeLowerBound (s : DynamicStealthState) (c₂ : ℝ) : Prop :=
  0 < c₂ ∧ c₂ ≤ |s.residualSecondDot|

theorem dynamically_repelled_not_reset_stealth_admissible
    (s : DynamicStealthState)
    (hrepel : dynamicallyRepelled s) :
    ¬ resetStealthAdmissible s := by
  intro hadm
  exact not_le_of_gt hrepel.2.2 hadm.2

theorem dynamic_pivot_closes_static_near_stealth
    (s : DynamicStealthState)
    (hexposure : exposureTimeDef s)
    (hpos : 0 < s.exposureTime)
    (hshort : s.exposureTime < s.dwellTime) :
    ¬ resetStealthAdmissible s := by
  exact dynamically_repelled_not_reset_stealth_admissible
    s ⟨hexposure, hpos, hshort⟩

theorem material_derivative_bound_closes_if_residual_budget_short
    (s : DynamicStealthState) (c : ℝ)
    (hbound : materialDerivativeLowerBound s c)
    (hexposure : exposureTimeDef s)
    (hrespos : 0 < |s.residual|)
    (hshort : |s.residual| / c < s.dwellTime) :
    ¬ resetStealthAdmissible s := by
  have hdotpos : 0 < |s.residualDot| := lt_of_lt_of_le hbound.1 hbound.2
  have hres_nonneg : 0 ≤ |s.residual| := abs_nonneg s.residual
  have hcpos : 0 < c := hbound.1
  have hle : |s.residual| / |s.residualDot| ≤ |s.residual| / c := by
    exact div_le_div_of_nonneg_left hres_nonneg hcpos hbound.2
  have hshort' : s.exposureTime < s.dwellTime := by
    rw [hexposure.2]
    exact lt_of_le_of_lt hle hshort
  have hexppos : 0 < s.exposureTime := by
    rw [hexposure.2]
    exact div_pos hrespos hdotpos
  exact dynamically_repelled_not_reset_stealth_admissible
    s ⟨hexposure, hexppos, hshort'⟩

/-!
Phase 5AV found sampled full-jet states with both `residual ≈ 0` and
`residualDot ≈ 0`.  Therefore the first-material-derivative lower-bound route
cannot be assumed.  The next admissible proof target is second-order (or a
separate trajectory-admissibility constraint).
-/

def quadraticExposureTimeBound (s : DynamicStealthState) (c₂ : ℝ) (eps : ℝ) : Prop :=
  0 < eps ∧ secondMaterialDerivativeLowerBound s c₂ ∧
    s.exposureTime ≤ eps

theorem second_order_dynamic_pivot_closes_if_exposure_short
    (s : DynamicStealthState) (c₂ eps : ℝ)
    (hquad : quadraticExposureTimeBound s c₂ eps)
    (hshort : eps < s.dwellTime) :
    ¬ resetStealthAdmissible s := by
  intro hadm
  have heps_lt_exposure : eps < s.exposureTime :=
    lt_of_lt_of_le hshort hadm.2
  have heps_lt_eps : eps < eps :=
    lt_of_lt_of_le heps_lt_exposure hquad.2.2
  exact (lt_irrefl eps) heps_lt_eps

end ZtareProofs.NS
