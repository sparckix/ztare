import Mathlib.Analysis.Polynomial.CauchyBound
import Mathlib.Analysis.Complex.RemovableSingularity
import Mathlib.Tactic
import ZtareProofs.FormalAnalyticPuncturedExtension

/-!
# Punctured analytic roots of monic analytic polynomial families

A single-valued punctured-holomorphic root of an eventually monic fixed-degree
polynomial family with analytic coefficient germs is locally bounded.  The
proof obtains a uniform Cauchy root bound from the finite coefficient family,
then invokes Riemann removability.
-/

namespace FormalAnalyticMonicPolynomialRoot

open Filter Finset Polynomial Set
open scoped NNReal Topology
open FormalAnalyticPuncturedExtension

/-- Raw data for a punctured root of an analytic monic polynomial family.
Boundedness and extension are deliberately absent. -/
structure AnalyticMonicRootCarrier where
  center : ℂ
  degree : ℕ
  polynomialFamily : ℂ → ℂ[X]
  branch : ℂ → ℂ
  coefficient_analytic : ∀ i : ℕ, i < degree →
    AnalyticAt ℂ (fun t ↦ (polynomialFamily t).coeff i) center
  eventually_monic : ∀ᶠ t in 𝓝[≠] center, (polynomialFamily t).Monic
  eventually_degree : ∀ᶠ t in 𝓝[≠] center,
    (polynomialFamily t).natDegree = degree
  branch_differentiable : ∀ᶠ t in 𝓝[≠] center,
    DifferentiableAt ℂ branch t
  root_identity : ∀ᶠ t in 𝓝[≠] center,
    (polynomialFamily t).IsRoot (branch t)

/-- The specialized Cauchy bounds of an analytic fixed-degree monic family
are uniformly bounded near the puncture. -/
theorem AnalyticMonicRootCarrier.cauchyBound_isBoundedUnder
    (carrier : AnalyticMonicRootCarrier) :
    IsBoundedUnder (· ≤ ·) (𝓝[≠] carrier.center)
      fun t ↦ (carrier.polynomialFamily t).cauchyBound := by
  let coefficientNorm : ℕ → ℂ → ℝ≥0 := fun i t ↦
    ‖(carrier.polynomialFamily t).coeff i‖₊
  have hcoefficient : ∀ i ∈ range carrier.degree,
      IsBoundedUnder (· ≤ ·) (𝓝[≠] carrier.center)
        (coefficientNorm i) := by
    intro i _hi
    have htendsto : Tendsto (coefficientNorm i) (𝓝 carrier.center)
        (𝓝 (coefficientNorm i carrier.center)) := by
      exact (continuous_nnnorm.tendsto _).comp
        (carrier.coefficient_analytic i (mem_range.mp _hi)).continuousAt
    exact htendsto.isBoundedUnder_le.mono nhdsWithin_le_nhds
  have hsup : IsBoundedUnder (· ≤ ·) (𝓝[≠] carrier.center)
      (fun t ↦ sup (range carrier.degree)
        (fun i ↦ coefficientNorm i t)) :=
    isBoundedUnder_le_finset_sup hcoefficient
  have hone : IsBoundedUnder (· ≤ ·) (𝓝[≠] carrier.center)
      (fun _ : ℂ ↦ (1 : ℝ≥0)) :=
    tendsto_const_nhds.isBoundedUnder_le
  have hsum : IsBoundedUnder (· ≤ ·) (𝓝[≠] carrier.center)
      ((fun t ↦ sup (range carrier.degree)
        (fun i ↦ coefficientNorm i t)) + fun _ ↦ 1) :=
    isBoundedUnder_le_add hsup hone
  obtain ⟨bound, hbound⟩ := hsum
  refine ⟨bound, ?_⟩
  simp only [eventually_map, Pi.add_apply] at hbound ⊢
  filter_upwards [hbound, carrier.eventually_monic,
      carrier.eventually_degree] with t ht hmonic hdegree
  simpa [Polynomial.cauchyBound, hdegree, hmonic.leadingCoeff,
    coefficientNorm] using ht

/-- Every carried root is uniformly bounded in norm on the punctured germ. -/
theorem AnalyticMonicRootCarrier.branch_norm_isBoundedUnder
    (carrier : AnalyticMonicRootCarrier) :
    IsBoundedUnder (· ≤ ·) (𝓝[≠] carrier.center)
      fun t ↦ ‖carrier.branch t‖ := by
  obtain ⟨bound, hbound⟩ := carrier.cauchyBound_isBoundedUnder
  refine ⟨(bound : ℝ), ?_⟩
  simp only [eventually_map] at hbound ⊢
  filter_upwards [hbound, carrier.eventually_monic,
      carrier.root_identity] with t hboundT hmonic hroot
  have hrootBound := hroot.norm_lt_cauchyBound hmonic.ne_zero
  exact le_trans (by exact_mod_cast hrootBound.le) (by exact_mod_cast hboundT)

/-- The bounded monic root has a finite analytic extension at the puncture. -/
theorem AnalyticMonicRootCarrier.hasFiniteAnalyticExtension
    (carrier : AnalyticMonicRootCarrier) :
    HasFiniteAnalyticExtension carrier.branch carrier.center := by
  have hnorm := carrier.branch_norm_isBoundedUnder
  obtain ⟨bound, hbound⟩ := hnorm
  have hrelative : IsBoundedUnder (· ≤ ·) (𝓝[≠] carrier.center)
      (fun t ↦ ‖carrier.branch t - carrier.branch carrier.center‖) := by
    refine ⟨bound + ‖carrier.branch carrier.center‖, ?_⟩
    simp only [eventually_map] at hbound ⊢
    filter_upwards [hbound] with t ht
    exact (norm_sub_le _ _).trans (add_le_add ht le_rfl)
  exact hasFiniteAnalyticExtension_of_bounded
    carrier.branch_differentiable hrelative

/-- Aggregated local algebraic-root boundedness certificate. -/
theorem analytic_monic_root_terminal_certificate :
    ∀ carrier : AnalyticMonicRootCarrier,
      IsBoundedUnder (· ≤ ·) (𝓝[≠] carrier.center)
          (fun t ↦ ‖carrier.branch t‖) ∧
        HasFiniteAnalyticExtension carrier.branch carrier.center := by
  intro carrier
  exact ⟨carrier.branch_norm_isBoundedUnder,
    carrier.hasFiniteAnalyticExtension⟩

end FormalAnalyticMonicPolynomialRoot
