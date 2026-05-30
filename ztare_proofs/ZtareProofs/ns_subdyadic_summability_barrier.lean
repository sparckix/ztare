import Mathlib.Tactic
import ZtareProofs.ns_mollified_frame_subdyadic_bridge

namespace ZtareProofs

/-!
`ns_subdyadic_summability_barrier` names the exact next route-5 burden after
the iter-2 mollified-frame bridge.

The live question is no longer whether `γ = 2/3` improves on the flat route.
It does. The live question is whether a positive residual exponent can be made
summable, or whether route 5 still needs a second coercive mechanism.
-/

/-- Abstract witness that a residual exponent is summable in the needed sense. -/
def residualExponentSummable (γ : Real) : Prop :=
  γ ≤ 0

/-- Secondary coercive mechanism that can neutralize a positive residual exponent. -/
def secondaryCoerciveOffset (γ offset : Real) : Prop :=
  0 ≤ offset ∧ γ - offset ≤ 0

/--
Exact route-5 next target after the mollified-frame proposal: either the
residual exponent is summable directly, or a second coercive mechanism offsets
it down to a non-positive effective exponent.
-/
def route5SubdyadicClosureTarget (γ offset : Real) : Prop :=
  residualExponentSummable γ ∨ secondaryCoerciveOffset γ offset

/--
Positive sub-dyadic exponents do not close the route by themselves.
-/
theorem positive_subdyadic_not_summable
    {γ : Real} (hγpos : 0 < γ) :
    ¬ residualExponentSummable γ := by
  intro hsum
  unfold residualExponentSummable at hsum
  linarith

/--
But a large enough secondary offset would close the residual budget.
-/
theorem offset_can_close_positive_subdyadic
    {γ offset : Real}
    (hγpos : 0 < γ)
    (hoff : γ ≤ offset) :
    route5SubdyadicClosureTarget γ offset := by
  right
  unfold secondaryCoerciveOffset
  constructor
  · linarith
  · linarith

end ZtareProofs
