import Mathlib.Tactic
import ZtareProofs.ns_subdyadic_summability_barrier

namespace ZtareProofs

/-!
`ns_intrinsic_frame_mollification_universality` records the strongest useful
claim from constructive iter 3.

The claim is not merely that one particular mollified frame bottoms out at
`2^(2q/3)`, but that any *intrinsic* frame built from local or mollified
physical tensor fields pays the same geometry-vs-advection tradeoff unless it
leaves the intrinsic category entirely.
-/

/-- Abstract marker for routes built from intrinsic physical tensor fields. -/
def intrinsicFrameRoute (isIntrinsic : Prop) : Prop := isIntrinsic

/--
Universal tradeoff target: every intrinsic mollified frame inherits a positive
residual exponent and therefore still faces the same summability barrier.
-/
def intrinsicMollificationUniversalityTarget
    (isIntrinsic : Prop) (γ : Real) : Prop :=
  intrinsicFrameRoute isIntrinsic ∧ 0 < γ

/--
If an intrinsic route has a positive residual exponent, it is still downstream
of the route-5 summability barrier.
-/
theorem intrinsic_positive_exponent_hits_same_barrier
    {isIntrinsic : Prop} {γ : Real}
    (h : intrinsicMollificationUniversalityTarget isIntrinsic γ) :
    intrinsicFrameRoute isIntrinsic ∧ ¬ residualExponentSummable γ := by
  rcases h with ⟨hintrinsic, hγ⟩
  constructor
  · exact hintrinsic
  · exact positive_subdyadic_not_summable hγ

/--
So an intrinsic category proposal only escapes iter-3 if it proves a
non-positive residual exponent or leaves the intrinsic-frame universality
class.
-/
def intrinsicRouteEscapesUniversality
    (isIntrinsic : Prop) (γ : Real) : Prop :=
  residualExponentSummable γ ∨ ¬ intrinsicFrameRoute isIntrinsic

end ZtareProofs
