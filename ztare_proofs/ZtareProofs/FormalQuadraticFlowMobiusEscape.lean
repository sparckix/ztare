import Mathlib.Analysis.Calculus.Deriv.Basic
import Mathlib.Tactic
import ZtareProofs.FormalComplexMonodromyFiniteRootEscape

/-!
# Quadratic-flow Möbius escape

The time-one map of `a*x^2 d/dx` is the Möbius map
`x / (1 - a*x)` and its inverse is `x / (1 + a*x)`.  Two elementary
selection facts are useful for polynomial-flow factorizations:

* the inverse Möbius map is regular over at least one of the two distinct
  critical centers `-2` and `6`;
* an injective non-torsion scalar monodromy orbit contains a value away from
  the unique pole of every fixed inverse Möbius map.

This file owns those substrate-neutral algebraic and local-calculus facts.
It does not construct a critical Puiseux germ or assert a two-flow
factorization.
-/

namespace FormalQuadraticFlowMobiusEscape

open Complex Polynomial
open FormalComplexIrrationalResidueMonodromy
open FormalComplexMonodromyFiniteRootEscape

/-- The time-one map of the quadratic vector field `a*x^2 d/dx`. -/
noncomputable def quadraticFlow (a x : ℂ) : ℂ :=
  x / (1 - a * x)

/-- The inverse time-one map of the quadratic vector field. -/
noncomputable def inverseQuadraticFlow (a x : ℂ) : ℂ :=
  x / (1 + a * x)

/-- The denominator at the regular preimage is the reciprocal of the center
denominator. -/
theorem inverseQuadraticFlow_preimage_denominator
    (a center : ℂ) (hregular : 1 - a * center ≠ 0) :
    1 + a * (center / (1 - a * center)) =
      (1 - a * center)⁻¹ := by
  field_simp
  ring

/-- The explicit inverse sends the regular preimage of `center` back to the
center. -/
theorem inverseQuadraticFlow_preimage
    (a center : ℂ) (hregular : 1 - a * center ≠ 0) :
    inverseQuadraticFlow a (center / (1 - a * center)) = center := by
  rw [inverseQuadraticFlow,
    inverseQuadraticFlow_preimage_denominator a center hregular]
  have hdenominator : 1 - center * a ≠ 0 := by
    simpa [mul_comm] using hregular
  field_simp [hdenominator]

/-- The inverse Möbius map is locally biholomorphic at every regular point. -/
theorem inverseQuadraticFlow_hasDerivAt
    (a x : ℂ) (hregular : 1 + a * x ≠ 0) :
    HasDerivAt (inverseQuadraticFlow a) ((1 + a * x)⁻¹ ^ 2) x := by
  have hnumerator : HasDerivAt (fun z : ℂ => z) 1 x := hasDerivAt_id x
  have hdenominator : HasDerivAt (fun z : ℂ => 1 + a * z) a x := by
    convert (hasDerivAt_const x (1 : ℂ)).add
      ((hasDerivAt_const x a).mul (hasDerivAt_id x)) using 1 <;> ring
  have hquotient := hnumerator.div hdenominator hregular
  convert hquotient using 1 <;> field_simp <;> ring

/-- The two critical centers cannot both be poles of one inverse quadratic
flow. -/
theorem one_of_two_critical_centers_regular (a : ℂ) :
    1 - a * (-2) ≠ 0 ∨ 1 - a * 6 ≠ 0 := by
  by_contra h
  push_neg at h
  have hfour : (4 : ℂ) = 0 := by
    linear_combination 3 * h.1 + h.2
  norm_num at hfour

/-- A non-torsion scalar orbit avoids the unique pole of every fixed inverse
quadratic flow. -/
theorem exists_monodromy_iterate_inverseQuadraticFlow_regular
    (residue base b : ℂ)
    (hirrational : IrrationalResidue residue)
    (hbase : base ≠ 0) :
    ∃ order : ℕ,
      1 + b * (residueMonodromy residue ^ order * base) ≠ 0 := by
  let polePolynomial : ℂ[X] := C 1 + C b * X
  have hpole : polePolynomial ≠ 0 := by
    intro hzero
    have hconstant := congrArg (fun p : ℂ[X] => p.coeff 0) hzero
    simp [polePolynomial] at hconstant
  obtain ⟨order, hescape⟩ :=
    exists_monodromy_iterate_polynomial_ne_zero
      residue base hirrational hbase polePolynomial hpole
  refine ⟨order, ?_⟩
  simpa [polePolynomial] using hescape

/-- Aggregated quadratic-flow escape surface. -/
theorem quadratic_flow_mobius_escape_terminal_certificate :
    (∀ a : ℂ, 1 - a * (-2) ≠ 0 ∨ 1 - a * 6 ≠ 0) ∧
    (∀ (residue base b : ℂ),
      IrrationalResidue residue → base ≠ 0 →
        ∃ order : ℕ,
          1 + b * (residueMonodromy residue ^ order * base) ≠ 0) := by
  constructor
  · exact one_of_two_critical_centers_regular
  · intro residue base b hirrational hbase
    exact exists_monodromy_iterate_inverseQuadraticFlow_regular
      residue base b hirrational hbase

end FormalQuadraticFlowMobiusEscape
