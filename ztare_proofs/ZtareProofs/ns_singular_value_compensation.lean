import Mathlib.Tactic
import ZtareProofs.ns_kinematic_compensation

namespace ZtareProofs

/-!
`ns_singular_value_compensation` is the de-anchored form of the compensation
bridge.

Instead of speaking about tubes and sheets, it speaks about the singular values
of a local incompressible deformation.  If the deformation preserves volume and
one axis expands, the transverse singular spectrum must pay for it.
-/

/--
Local incompressible singular-value split:
`axial * trans1 * trans2 = 1`.
-/
def volumePreservingSingularValues (axial trans1 trans2 : Real) : Prop :=
  axial * trans1 * trans2 = 1

/--
If a volume-preserving deformation expands axially and both transverse singular
values were at least `q`, then `axial * q^2 <= 1`.

Contrapositive reading: if `axial * q^2 > 1`, at least one transverse singular
value must be below `q`.
-/
theorem transverse_singular_value_pressure
    {axial trans1 trans2 q : Real}
    (hvol : volumePreservingSingularValues axial trans1 trans2)
    (haxial_nonneg : 0 ≤ axial)
    (hq_nonneg : 0 ≤ q)
    (h1 : q ≤ trans1)
    (h2 : q ≤ trans2) :
    axial * q ^ (2 : Nat) ≤ 1 := by
  unfold volumePreservingSingularValues at hvol
  have hqprod : q * q ≤ trans1 * trans2 := by
    exact mul_le_mul h1 h2 hq_nonneg (le_trans hq_nonneg h1)
  have hmain : axial * (q * q) ≤ axial * (trans1 * trans2) := by
    exact mul_le_mul_of_nonneg_left hqprod haxial_nonneg
  have hrewrite : axial * (trans1 * trans2) = 1 := by
    linarith
  have hpow : q ^ (2 : Nat) = q * q := by ring
  rw [hpow]
  exact le_trans hmain (by simp [hrewrite])

/--
Forced transverse collapse, stated without choosing a square root.

If `axial * q^2 > 1`, the two transverse singular values cannot both be at
least `q`.
-/
theorem exists_transverse_singular_below_threshold
    {axial trans1 trans2 q : Real}
    (hvol : volumePreservingSingularValues axial trans1 trans2)
    (haxial_nonneg : 0 ≤ axial)
    (hq_nonneg : 0 ≤ q)
    (hthreshold : 1 < axial * q ^ (2 : Nat)) :
    trans1 < q ∨ trans2 < q := by
  by_contra hnone
  have h1 : q ≤ trans1 := le_of_not_gt (fun h => hnone (Or.inl h))
  have h2 : q ≤ trans2 := le_of_not_gt (fun h => hnone (Or.inr h))
  have hle : axial * q ^ (2 : Nat) ≤ 1 :=
    transverse_singular_value_pressure hvol haxial_nonneg hq_nonneg h1 h2
  linarith

/--
Singular-value compensation target:
centrifugal escape must supply a growing axial singular value. Once that is
available, incompressibility forces transverse contraction below any threshold
`q` whose squared scale violates the volume budget.
-/
theorem singular_value_compensation_target_shape
    {axial trans1 trans2 q : Real}
    (hvol : volumePreservingSingularValues axial trans1 trans2)
    (haxial_nonneg : 0 ≤ axial)
    (hq_nonneg : 0 ≤ q)
    (hthreshold : 1 < axial * q ^ (2 : Nat)) :
    trans1 < q ∨ trans2 < q := by
  exact exists_transverse_singular_below_threshold hvol haxial_nonneg hq_nonneg hthreshold

end ZtareProofs
