import Mathlib.Algebra.Polynomial.Coeff
import Mathlib.Algebra.Polynomial.Degree.Operations
import Mathlib.Tactic
import ZtareProofs.FormalTangentSubstitutionInjectivity

/-!
# Common-equilibrium saturation for the coupled Julia relation

Regard the coupled relation as a polynomial in a visible variable `F`, with
coefficients that are polynomials in the hidden variable `Y`.  When the outer
generator has no linear term, its visible coefficients at degrees one and
`natDegree q` separate the two hidden generators.  Consequently a constant
visible divisor is exactly a common divisor of those generators.

The statement applies to arbitrary powers of a factor, so repeated common
equilibria are retained.  The imported tangent-substitution kernel then
shows that a nonzero common factor remains nonzero on every invertible
tangent germ and can be canceled there.
-/

namespace FormalCoupledJuliaCommonEquilibriumSaturation

open Polynomial
open FormalTangentSubstitutionInjectivity

variable {K : Type*} [Field K]

/-- The normalized coupled relation
`p(Y) visibleOuter(F) - F hiddenOuter(Y)` in `K[Y][F]`.  The visible and
hidden outer polynomials are separate because hidden gcd saturation changes
only the latter.  Nonzero scalar multipliers may be removed over a field
before applying the theorem below. -/
noncomputable def coupledRelation
    (inner visibleOuter hiddenOuter : K[X]) : K[X][X] :=
  C inner * visibleOuter.map (C : K →+* K[X]) - C hiddenOuter * X

/-- The visible degree-one coefficient isolates the hidden outer generator
when the outer vector field has no linear term. -/
theorem coeff_one_coupledRelation
    (inner visibleOuter hiddenOuter : K[X])
    (hlinear : visibleOuter.coeff 1 = 0) :
    (coupledRelation inner visibleOuter hiddenOuter).coeff 1 =
      -hiddenOuter := by
  simp [coupledRelation, hlinear]

/-- At every visible degree other than one, the coupled relation has only
the lifted outer coefficient times the hidden inner generator. -/
theorem coeff_coupledRelation_of_ne_one
    (inner visibleOuter hiddenOuter : K[X])
    (degree : ℕ) (hdegree : degree ≠ 1) :
    (coupledRelation inner visibleOuter hiddenOuter).coeff degree =
      C (visibleOuter.coeff degree) * inner := by
  have hx : (X : K[X][X]).coeff degree = 0 := by
    rw [Polynomial.coeff_X]
    simp [Ne.symm hdegree]
  simp only [coupledRelation, coeff_sub, coeff_C_mul, coeff_map,
    hx]
  ring

/-- A visible-constant divisor of the coupled relation is exactly a common
divisor of its two hidden generators. -/
theorem C_dvd_coupledRelation_iff
    (inner visibleOuter hiddenOuter factor : K[X])
    (hlinear : visibleOuter.coeff 1 = 0)
    (hdegree : 2 ≤ visibleOuter.natDegree) :
    C factor ∣ coupledRelation inner visibleOuter hiddenOuter ↔
      factor ∣ inner ∧ factor ∣ hiddenOuter := by
  constructor
  · intro hdivides
    have hcoefficients :=
      (Polynomial.C_dvd_iff_dvd_coeff factor
        (coupledRelation inner visibleOuter hiddenOuter)).mp hdivides
    have houterRaw := hcoefficients 1
    rw [coeff_one_coupledRelation inner visibleOuter hiddenOuter hlinear]
      at houterRaw
    have houter : factor ∣ hiddenOuter := by
      simpa using houterRaw
    have hnatDegreeNeOne : visibleOuter.natDegree ≠ 1 := by omega
    have hinnerRaw := hcoefficients visibleOuter.natDegree
    rw [coeff_coupledRelation_of_ne_one inner visibleOuter hiddenOuter
      visibleOuter.natDegree hnatDegreeNeOne] at hinnerRaw
    have hvisibleNonzero : visibleOuter ≠ 0 := by
      intro hzero
      simp [hzero] at hdegree
    have hleadingCoeff : visibleOuter.leadingCoeff ≠ 0 :=
      visibleOuter.leadingCoeff_ne_zero.mpr hvisibleNonzero
    rcases hinnerRaw with ⟨quotient, hquotient⟩
    have hinner : factor ∣ inner := by
      refine ⟨C (visibleOuter.coeff visibleOuter.natDegree)⁻¹ *
        quotient, ?_⟩
      calc
        inner = C (visibleOuter.coeff visibleOuter.natDegree)⁻¹ *
            (C (visibleOuter.coeff visibleOuter.natDegree) * inner) := by
              symm
              rw [← mul_assoc, ← C_mul]
              simp [hleadingCoeff]
        _ = C (visibleOuter.coeff visibleOuter.natDegree)⁻¹ *
            (factor * quotient) := by rw [hquotient]
        _ = factor *
            (C (visibleOuter.coeff visibleOuter.natDegree)⁻¹ *
              quotient) := by ring
    exact ⟨hinner, houter⟩
  · rintro ⟨hinner, houter⟩
    have hinnerC : C factor ∣ C inner := by
      exact map_dvd C hinner
    have houterC : C factor ∣ C hiddenOuter := by
      exact map_dvd C houter
    exact dvd_sub
      (dvd_mul_of_dvd_left hinnerC
        (visibleOuter.map (C : K →+* K[X])))
      (dvd_mul_of_dvd_left houterC X)

/-- Applying the divisor theorem to a power retains the exact common-factor
multiplicity rather than replacing the gcd by its squarefree support. -/
theorem C_pow_dvd_coupledRelation_iff
    (inner visibleOuter hiddenOuter factor : K[X]) (multiplicity : ℕ)
    (hlinear : visibleOuter.coeff 1 = 0)
    (hdegree : 2 ≤ visibleOuter.natDegree) :
    C (factor ^ multiplicity) ∣
        coupledRelation inner visibleOuter hiddenOuter ↔
      factor ^ multiplicity ∣ inner ∧
        factor ^ multiplicity ∣ hiddenOuter := by
  exact C_dvd_coupledRelation_iff inner visibleOuter hiddenOuter
    (factor ^ multiplicity) hlinear hdegree

/-- Once the two hidden generators have been divided by their complete gcd,
every remaining visible-constant divisor of the coupled relation is a unit. -/
theorem isUnit_of_C_dvd_coupledRelation_of_isCoprime
    (inner visibleOuter hiddenOuter factor : K[X])
    (hlinear : visibleOuter.coeff 1 = 0)
    (hdegree : 2 ≤ visibleOuter.natDegree)
    (hcoprime : IsCoprime inner hiddenOuter)
    (hdivides : C factor ∣
      coupledRelation inner visibleOuter hiddenOuter) :
    IsUnit factor := by
  have hcommon :=
    (C_dvd_coupledRelation_iff inner visibleOuter hiddenOuter factor
      hlinear hdegree).mp hdivides
  exact hcoprime.isUnit_of_dvd' hcommon.1 hcommon.2

/-- A nonzero common-equilibrium factor remains nonzero on a selected
invertible tangent germ, including when its substituted value has positive
order and is not a unit. -/
theorem common_factor_aeval_ne_zero_on_tangent_germ
    (endpoint : PowerSeries K)
    (hconstant : endpoint.constantCoeff = 0)
    [Invertible (endpoint.coeff 1)]
    (factor : K[X]) (hfactor : factor ≠ 0) :
    Polynomial.aeval endpoint factor ≠ 0 := by
  exact polynomial_aeval_ne_zero_of_invertible_linear
    endpoint hconstant factor hfactor

/-- An `F`-independent divisor is simultaneously identified as a common
generator factor and made cancellable on every selected tangent germ. -/
theorem C_divisor_common_and_cancellable_on_tangent_germ
    (inner visibleOuter hiddenOuter factor : K[X])
    (hlinear : visibleOuter.coeff 1 = 0)
    (hdegree : 2 ≤ visibleOuter.natDegree)
    (endpoint : PowerSeries K)
    (hconstant : endpoint.constantCoeff = 0)
    [Invertible (endpoint.coeff 1)]
    (hfactor : factor ≠ 0)
    (hdivides : C factor ∣
      coupledRelation inner visibleOuter hiddenOuter) :
    (factor ∣ inner ∧ factor ∣ hiddenOuter) ∧
      ∀ (left right : K[X]),
        Polynomial.aeval endpoint (factor * left) =
            Polynomial.aeval endpoint (factor * right) →
          Polynomial.aeval endpoint left =
            Polynomial.aeval endpoint right := by
  refine ⟨(C_dvd_coupledRelation_iff inner visibleOuter hiddenOuter factor
      hlinear hdegree).mp hdivides, ?_⟩
  intro left right hidentity
  exact cancel_polynomial_factor_on_tangent_germ
    endpoint hconstant factor left right hfactor hidentity

/-- The algebraic saturation theorem and tangent nonvanishing theorem in one
consumer-facing certificate. -/
theorem coupled_julia_common_equilibrium_saturation_terminal_certificate :
    ∀ (inner visibleOuter hiddenOuter factor : K[X]),
      visibleOuter.coeff 1 = 0 →
      2 ≤ visibleOuter.natDegree →
      (C factor ∣ coupledRelation inner visibleOuter hiddenOuter ↔
        factor ∣ inner ∧ factor ∣ hiddenOuter) ∧
      (∀ (multiplicity : ℕ),
        C (factor ^ multiplicity) ∣
            coupledRelation inner visibleOuter hiddenOuter ↔
          factor ^ multiplicity ∣ inner ∧
            factor ^ multiplicity ∣ hiddenOuter) := by
  intro inner visibleOuter hiddenOuter factor hlinear hdegree
  exact ⟨C_dvd_coupledRelation_iff inner visibleOuter hiddenOuter factor
      hlinear hdegree,
    fun multiplicity ↦ C_pow_dvd_coupledRelation_iff
      inner visibleOuter hiddenOuter factor multiplicity hlinear hdegree⟩

end FormalCoupledJuliaCommonEquilibriumSaturation
