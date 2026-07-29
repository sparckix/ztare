import Mathlib.LinearAlgebra.Dimension.Free
import Mathlib.LinearAlgebra.FiniteDimensional.Basic

/-!
Field-degree obstruction used by the unbounded formal-source-lift argument.

The scientific artifact supplies the geometric bridge: a uniformly bounded
spatial degree would turn the coefficientwise formal lift into a dominant
polynomial map over `k((s))`, producing the displayed intermediate function
field.  This file checks the invariant terminal step: a degree-four extension
cannot factor through a degree-three extension.
-/

namespace AxiomPackJacobianUnboundedLift

theorem degree_four_cannot_factor_through_degree_three
    (K L M : Type*) [Field K] [Field L] [Field M]
    [Algebra K L] [Algebra L M] [Algebra K M] [IsScalarTower K L M]
    [FiniteDimensional K L] [FiniteDimensional L M] [FiniteDimensional K M]
    (hKL : Module.finrank K L = 3) :
    Module.finrank K M ≠ 4 := by
  intro hKM
  have htower := Module.finrank_mul_finrank K L M
  rw [hKL, hKM] at htower
  omega

/-- Terminal numerical tower certificate, stated as the divisibility
contradiction used for the public `3 -> 4` generic-degree jump. -/
theorem unbounded_source_lift_degree_certificate
    (m : ℕ) (hdegree : 4 = 3 * m) : False := by
  omega

end AxiomPackJacobianUnboundedLift
