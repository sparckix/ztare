import Mathlib.Analysis.Meromorphic.Order
import Mathlib.Tactic
import ZtareProofs.FormalPolynomialRootScaling
import ZtareProofs.FormalScaledMonicMeromorphicRoot

/-!
# Meromorphic normalization of an analytic polynomial root

A punctured-holomorphic branch need not satisfy a monic polynomial relation
before the puncture is reached: the leading coefficient can vanish there.
Its finite vanishing order supplies the exact coordinate-power scaling that
turns the relation into a monic analytic family.  The resulting bounded root
extends analytically, so the original branch is meromorphic.
-/

namespace FormalAnalyticPolynomialRootNormalization

open Filter Polynomial
open scoped Topology
open FormalPolynomialRootScaling
open FormalAnalyticMonicPolynomialRoot
open FormalScaledMonicMeromorphicRoot

/-- Raw local data for a root of a degree-bounded analytic polynomial family.
No bound, extension, monic normalization, or meromorphicity is included. -/
structure AnalyticPolynomialRootCarrier where
  center : ℂ
  degree : ℕ
  degree_pos : 0 < degree
  leadingOrder : ℕ
  polynomialFamily : ℂ → ℂ[X]
  branch : ℂ → ℂ
  coefficient_analytic : ∀ i : ℕ, i ≤ degree →
    AnalyticAt ℂ (fun t ↦ (polynomialFamily t).coeff i) center
  eventually_degree_le : ∀ᶠ t in 𝓝[≠] center,
    (polynomialFamily t).natDegree ≤ degree
  leading_order :
    meromorphicOrderAt (fun t ↦ (polynomialFamily t).coeff degree) center =
      (((leadingOrder : ℕ) : ℤ) : WithTop ℤ)
  branch_differentiable : ∀ᶠ t in 𝓝[≠] center,
    DifferentiableAt ℂ branch t
  root_identity : ∀ᶠ t in 𝓝[≠] center,
    (polynomialFamily t).IsRoot (branch t)

/-- The finite leading-coefficient order constructs an explicit scaled monic
root carrier. -/
theorem AnalyticPolynomialRootCarrier.exists_scaledMonicRootCarrier
    (carrier : AnalyticPolynomialRootCarrier) :
    ∃ scaled : ScaledMonicRootCarrier,
      scaled.branch = carrier.branch ∧
      scaled.scaleOrder = carrier.leadingOrder ∧
      scaled.rootCarrier.center = carrier.center := by
  have hleadingAnalytic := carrier.coefficient_analytic carrier.degree le_rfl
  obtain ⟨unit, hunitAnalytic, hunitNonzero, hleadingNormal⟩ :=
    (meromorphicOrderAt_eq_int_iff hleadingAnalytic.meromorphicAt).1
      carrier.leading_order
  simp only [zpow_natCast, smul_eq_mul] at hleadingNormal
  let normalizedFamily : ℂ → ℂ[X] := fun t ↦
    scaledMonicPolynomial (carrier.polynomialFamily t) carrier.degree
      carrier.leadingOrder (t - carrier.center) (unit t)
  let scaledBranch : ℂ → ℂ := fun t ↦
    (t - carrier.center) ^ carrier.leadingOrder * carrier.branch t
  have hcoefficient : ∀ i : ℕ, i < carrier.degree →
      AnalyticAt ℂ (fun t ↦ (normalizedFamily t).coeff i) carrier.center := by
    intro i hi
    have hcoordinate : AnalyticAt ℂ
        (fun t : ℂ ↦ (t - carrier.center) ^
          (carrier.leadingOrder * (carrier.degree - i - 1)))
        carrier.center := by
      fun_prop
    have hraw := carrier.coefficient_analytic i hi.le
    have hquotient : AnalyticAt ℂ
        (fun t ↦ (carrier.polynomialFamily t).coeff i / unit t)
        carrier.center :=
      hraw.div hunitAnalytic hunitNonzero
    have hnormalized := hcoordinate.mul hquotient
    simpa only [normalizedFamily,
      coeff_scaledMonicPolynomial_of_lt _ _ _ _ _ hi,
      Pi.mul_apply, Pi.div_apply, mul_div_assoc] using hnormalized
  have hmonic : ∀ᶠ t in 𝓝[≠] carrier.center,
      (normalizedFamily t).Monic := by
    filter_upwards [] with t
    exact scaledMonicPolynomial_monic _ _ _ _ _
  have hdegree : ∀ᶠ t in 𝓝[≠] carrier.center,
      (normalizedFamily t).natDegree = carrier.degree := by
    filter_upwards [] with t
    exact scaledMonicPolynomial_natDegree _ _ _ _ _
  have hscaledDifferentiable : ∀ᶠ t in 𝓝[≠] carrier.center,
      DifferentiableAt ℂ scaledBranch t := by
    filter_upwards [carrier.branch_differentiable] with t ht
    dsimp [scaledBranch]
    fun_prop
  have hunitEventually : ∀ᶠ t in 𝓝 carrier.center, unit t ≠ 0 :=
    hunitAnalytic.continuousAt.eventually_ne hunitNonzero
  have hroot : ∀ᶠ t in 𝓝[≠] carrier.center,
      (normalizedFamily t).IsRoot (scaledBranch t) := by
    filter_upwards [carrier.eventually_degree_le, carrier.root_identity,
        hleadingNormal,
        eventually_nhdsWithin_of_eventually_nhds hunitEventually] with
        t htDegree htRoot htLeading htUnit
    exact scaledMonicPolynomial_isRoot
      (carrier.polynomialFamily t) carrier.degree carrier.leadingOrder
      (t - carrier.center) (unit t) (carrier.branch t)
      carrier.degree_pos htDegree htUnit htLeading htRoot
  let rootCarrier : AnalyticMonicRootCarrier :=
    { center := carrier.center
      degree := carrier.degree
      polynomialFamily := normalizedFamily
      branch := scaledBranch
      coefficient_analytic := hcoefficient
      eventually_monic := hmonic
      eventually_degree := hdegree
      branch_differentiable := hscaledDifferentiable
      root_identity := hroot }
  let scaled : ScaledMonicRootCarrier :=
    { branch := carrier.branch
      scaleOrder := carrier.leadingOrder
      rootCarrier := rootCarrier
      scaled_identity := by rfl }
  exact ⟨scaled, rfl, rfl, rfl⟩

/-- Every carried punctured analytic algebraic branch is meromorphic once one
finite leading-coefficient order has been identified. -/
theorem AnalyticPolynomialRootCarrier.branch_meromorphicAt
    (carrier : AnalyticPolynomialRootCarrier) :
    MeromorphicAt carrier.branch carrier.center := by
  obtain ⟨scaled, hbranch, _hscale, hcenter⟩ :=
    carrier.exists_scaledMonicRootCarrier
  rw [← hbranch, ← hcenter]
  exact scaled.branch_meromorphicAt

/-- Aggregated analytic polynomial-root normalization surface. -/
theorem analytic_polynomial_root_normalization_terminal_certificate :
    ∀ carrier : AnalyticPolynomialRootCarrier,
      MeromorphicAt carrier.branch carrier.center := by
  intro carrier
  exact carrier.branch_meromorphicAt

end FormalAnalyticPolynomialRootNormalization
