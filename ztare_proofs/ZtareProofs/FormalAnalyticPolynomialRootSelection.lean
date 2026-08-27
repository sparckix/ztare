import Mathlib.Analysis.Meromorphic.Order
import Mathlib.Data.Finset.Max
import Mathlib.Tactic
import ZtareProofs.FormalAnalyticPolynomialRootNormalization

/-!
# Selecting the highest nonzero analytic coefficient germ

A polynomial family may have a fixed degree bound without retaining that
degree at the puncture.  From one coefficient germ that is not identically
zero, this file selects the highest active coefficient in the finite family.
All higher coefficients then vanish on a common pointed neighborhood.  The
selected analytic coefficient has finite nonnegative order and supplies the
leading-order datum required by analytic polynomial-root normalization.
-/

namespace FormalAnalyticPolynomialRootSelection

open Filter Finset Polynomial
open scoped Topology
open FormalAnalyticPolynomialRootNormalization

/-- A degree-bounded analytic polynomial root with one coefficient germ known
not to vanish identically.  No active degree or coefficient order is carried. -/
structure DegreeBoundedAnalyticRootCarrier where
  center : ℂ
  degreeBound : ℕ
  polynomialFamily : ℂ → ℂ[X]
  branch : ℂ → ℂ
  coefficient_analytic : ∀ i : ℕ, i ≤ degreeBound →
    AnalyticAt ℂ (fun t ↦ (polynomialFamily t).coeff i) center
  eventually_degree_le : ∀ᶠ t in 𝓝[≠] center,
    (polynomialFamily t).natDegree ≤ degreeBound
  branch_differentiable : ∀ᶠ t in 𝓝[≠] center,
    DifferentiableAt ℂ branch t
  root_identity : ∀ᶠ t in 𝓝[≠] center,
    (polynomialFamily t).IsRoot (branch t)
  some_coefficient_active : ∃ i : ℕ, i ≤ degreeBound ∧
    ¬(fun t ↦ (polynomialFamily t).coeff i) =ᶠ[𝓝[≠] center]
      (fun _ ↦ 0)

/-- The highest active coefficient and its finite analytic order construct
the normalization carrier required by the scaled-monic kernel. -/
theorem DegreeBoundedAnalyticRootCarrier.exists_normalizationCarrier
    (carrier : DegreeBoundedAnalyticRootCarrier) :
    ∃ normalized : AnalyticPolynomialRootCarrier,
      normalized.center = carrier.center ∧
      normalized.polynomialFamily = carrier.polynomialFamily ∧
      normalized.branch = carrier.branch := by
  classical
  let activeIndices : Finset ℕ :=
    (range (carrier.degreeBound + 1)).filter fun i ↦
      ¬(fun t ↦ (carrier.polynomialFamily t).coeff i) =ᶠ[𝓝[≠] carrier.center]
        (fun _ ↦ 0)
  have hactiveNonempty : activeIndices.Nonempty := by
    obtain ⟨i, hiBound, hiActive⟩ := carrier.some_coefficient_active
    refine ⟨i, mem_filter.mpr ⟨mem_range.mpr ?_, hiActive⟩⟩
    omega
  let activeDegree := activeIndices.max' hactiveNonempty
  have hactiveDegreeMem : activeDegree ∈ activeIndices :=
    max'_mem activeIndices hactiveNonempty
  have hactiveDegreeData := mem_filter.mp hactiveDegreeMem
  have hactiveDegreeBound : activeDegree ≤ carrier.degreeBound := by
    exact Nat.lt_succ_iff.mp (mem_range.mp hactiveDegreeData.1)
  have hactiveDegree :
      ¬(fun t ↦ (carrier.polynomialFamily t).coeff activeDegree) =ᶠ[
          𝓝[≠] carrier.center] (fun _ ↦ 0) :=
    hactiveDegreeData.2
  have hhigherInactive : ∀ i : ℕ, activeDegree < i →
      i ≤ carrier.degreeBound →
      (fun t ↦ (carrier.polynomialFamily t).coeff i) =ᶠ[
        𝓝[≠] carrier.center] (fun _ ↦ 0) := by
    intro i hiDegree hiBound
    by_cases hiActive :
        (fun t ↦ (carrier.polynomialFamily t).coeff i) =ᶠ[
          𝓝[≠] carrier.center] (fun _ ↦ 0)
    · exact hiActive
    · have hiMem : i ∈ activeIndices := by
        exact mem_filter.mpr ⟨mem_range.mpr (by omega), hiActive⟩
      have hiLe : i ≤ activeDegree :=
        le_max' activeIndices i hiMem
      omega
  have hhigherFinite : ∀ᶠ t in 𝓝[≠] carrier.center,
      ∀ i ∈ Finset.Ioc activeDegree carrier.degreeBound,
        (carrier.polynomialFamily t).coeff i = 0 := by
    apply (Finset.Ioc activeDegree carrier.degreeBound).eventually_all.mpr
    intro i hi
    obtain ⟨hiDegree, hiBound⟩ := Finset.mem_Ioc.mp hi
    exact hhigherInactive i hiDegree hiBound
  have hdegreeSelected : ∀ᶠ t in 𝓝[≠] carrier.center,
      (carrier.polynomialFamily t).natDegree ≤ activeDegree := by
    filter_upwards [carrier.eventually_degree_le, hhigherFinite] with
        t htBound htHigher
    apply natDegree_le_iff_coeff_eq_zero.mpr
    intro i hi
    by_cases hiBound : i ≤ carrier.degreeBound
    · exact htHigher i (Finset.mem_Ioc.mpr ⟨hi, hiBound⟩)
    · exact coeff_eq_zero_of_natDegree_lt (by omega)
  have hactiveDegreePositive : 0 < activeDegree := by
    by_contra hnot
    have hzero : activeDegree = 0 := by omega
    apply hactiveDegree
    filter_upwards [hdegreeSelected, carrier.root_identity] with
        t htDegree htRoot
    have hpConstant : carrier.polynomialFamily t =
        C ((carrier.polynomialFamily t).coeff 0) :=
      eq_C_of_natDegree_le_zero (by simpa [hzero] using htDegree)
    rw [hzero]
    rw [hpConstant] at htRoot
    simpa [Polynomial.IsRoot.def] using htRoot
  have hleadingAnalytic :=
    carrier.coefficient_analytic activeDegree hactiveDegreeBound
  have hleadingFinite :
      meromorphicOrderAt
          (fun t ↦ (carrier.polynomialFamily t).coeff activeDegree)
          carrier.center ≠ ⊤ := by
    intro htop
    apply hactiveDegree
    exact meromorphicOrderAt_eq_top_iff.mp htop
  let orderInt : ℤ :=
    (meromorphicOrderAt
      (fun t ↦ (carrier.polynomialFamily t).coeff activeDegree)
      carrier.center).untop₀
  have horderInt :
      meromorphicOrderAt
          (fun t ↦ (carrier.polynomialFamily t).coeff activeDegree)
          carrier.center = (orderInt : WithTop ℤ) := by
    exact (WithTop.coe_untop₀_of_ne_top hleadingFinite).symm
  have horderIntNonnegative : 0 ≤ orderInt := by
    have hnonnegative := hleadingAnalytic.meromorphicOrderAt_nonneg
    rw [horderInt] at hnonnegative
    exact_mod_cast hnonnegative
  let leadingOrder : ℕ := orderInt.toNat
  have hleadingOrder :
      meromorphicOrderAt
          (fun t ↦ (carrier.polynomialFamily t).coeff activeDegree)
          carrier.center =
        (((leadingOrder : ℕ) : ℤ) : WithTop ℤ) := by
    rw [horderInt]
    congr 1
    exact (Int.toNat_of_nonneg horderIntNonnegative).symm
  let normalized : AnalyticPolynomialRootCarrier :=
    { center := carrier.center
      degree := activeDegree
      degree_pos := hactiveDegreePositive
      leadingOrder := leadingOrder
      polynomialFamily := carrier.polynomialFamily
      branch := carrier.branch
      coefficient_analytic := fun i hi ↦
        carrier.coefficient_analytic i (hi.trans hactiveDegreeBound)
      eventually_degree_le := hdegreeSelected
      leading_order := hleadingOrder
      branch_differentiable := carrier.branch_differentiable
      root_identity := carrier.root_identity }
  exact ⟨normalized, rfl, rfl, rfl⟩

/-- A degree-bounded analytic polynomial root with one active coefficient is
meromorphic at the puncture. -/
theorem DegreeBoundedAnalyticRootCarrier.branch_meromorphicAt
    (carrier : DegreeBoundedAnalyticRootCarrier) :
    MeromorphicAt carrier.branch carrier.center := by
  obtain ⟨normalized, hcenter, _hfamily, hbranch⟩ :=
    carrier.exists_normalizationCarrier
  rw [← hbranch, ← hcenter]
  exact normalized.branch_meromorphicAt

/-- Aggregated finite coefficient-selection surface. -/
theorem analytic_polynomial_root_selection_terminal_certificate :
    ∀ carrier : DegreeBoundedAnalyticRootCarrier,
      MeromorphicAt carrier.branch carrier.center := by
  intro carrier
  exact carrier.branch_meromorphicAt

end FormalAnalyticPolynomialRootSelection
