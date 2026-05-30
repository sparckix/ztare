import Mathlib.Tactic
import ZtareProofs.ns_eigenvalue_repulsion_or_collapse

namespace ZtareProofs

/-!
`ns_mollified_frame_subdyadic_bridge` records the constructive escape hatch
revealed by iter 2 on the route-5 substrate.

The sharpened question is no longer just:

* can a moving-frame route avoid exact eigenvalue-gap blowup?

but:

* if a spectral-gap mollifier reduces the defect from `2^q` to `2^(2q/3)`,
  is that now genuinely summable, or only a cheaper but still divergent
  cascade?
-/

/-- Dyadic frequency index. -/
abbrev DyadicScale := Real

/-- Scalar defect size after mollifying the moving frame. -/
abbrev MollifiedFrameDefect := Real

/-- Residual exponent in the frequency growth of the defect. -/
abbrev DefectExponent := Real

/--
Constructive route-5 bridge candidate: a mollified moving frame beats the flat
`2^q` defect and leaves only a sub-dyadic `2^(γ q)` growth with `γ < 1`.
-/
def mollifiedFrameSubdyadicTarget
    (γ : Real) (flatExponent : Real) : Prop :=
  0 ≤ γ ∧ γ < flatExponent

/--
Global regularity still requires more than mere sub-dyadic improvement: the
remaining exponent must be summable or offset by a second coercive mechanism.
-/
def subdyadicStillNeedsSummability
    (γ : Real) : Prop :=
  0 < γ

/--
The exact iter-2 hinge: a mollified frame can lower route-5 proof cost, but it
has not closed the branch until the remaining exponent is paid.
-/
def route5MollifiedEscapeHinge
    (γ flatExponent : Real) : Prop :=
  mollifiedFrameSubdyadicTarget γ flatExponent ∧
    subdyadicStillNeedsSummability γ

/--
If `γ = 2/3`, then the route has genuinely improved on the flat exponent `1`
but still carries a positive residual burden.
-/
theorem two_thirds_is_subdyadic_but_not_closed :
    route5MollifiedEscapeHinge (2 / 3 : Real) 1 := by
  constructor
  · constructor
    · norm_num
    · norm_num
  · unfold subdyadicStillNeedsSummability
    norm_num

end ZtareProofs
