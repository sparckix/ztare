import Mathlib.Analysis.Analytic.Polynomial
import Mathlib.Tactic
import ZtareProofs.FormalAnalyticAlgebraicBranchBoundary

/-!
# Assembly of a separated analytic algebraic branch

A punctured analytic branch satisfying

`visible(t) * p(branch(t)) = scalar * q(branch(t))`

already determines the degree-bounded analytic polynomial-root carrier used
by the local boundary trichotomy.  In particular, activity of one polynomial
coefficient is a conclusion.  The scalar-zero case is retained.
-/

namespace FormalSeparatedAnalyticBranchAssembly

open Filter Polynomial
open scoped Topology

open FormalAnalyticAlgebraicBranchBoundary
open FormalAnalyticPolynomialRootSelection

/-- Raw selected-branch data for a separated relation.  It contains no
polynomial-root normalization, active coefficient, meromorphicity, hidden
order, or boundary class. -/
structure RawSeparatedAnalyticBranchCarrier (p q : ℂ[X]) where
  center : ℂ
  visibleOrder : ℕ
  visible : ℂ → ℂ
  branch : ℂ → ℂ
  scalar : ℂ
  p_nonzero : p ≠ 0
  q_nonzero : q ≠ 0
  visibleOrder_positive : 0 < visibleOrder
  visible_analytic : AnalyticAt ℂ visible center
  visible_order :
    meromorphicOrderAt visible center =
      ((visibleOrder : ℤ) : WithTop ℤ)
  branch_differentiable : ∀ᶠ t in 𝓝[≠] center,
    DifferentiableAt ℂ branch t
  relation :
    (fun t ↦ visible t * p.eval (branch t)) =ᶠ[𝓝[≠] center]
      (fun t ↦ scalar * q.eval (branch t))

/-- The exact separated polynomial family owned by the raw relation. -/
noncomputable def RawSeparatedAnalyticBranchCarrier.polynomialFamily
    {p q : ℂ[X]} (carrier : RawSeparatedAnalyticBranchCarrier p q) :
    ℂ → ℂ[X] := fun t ↦
  C (carrier.visible t) * p - C carrier.scalar * q

/-- A uniform degree bound for the separated polynomial family. -/
def RawSeparatedAnalyticBranchCarrier.degreeBound
    {p q : ℂ[X]} (_carrier : RawSeparatedAnalyticBranchCarrier p q) : ℕ :=
  max p.natDegree q.natDegree

theorem RawSeparatedAnalyticBranchCarrier.visible_eventually_ne_zero
    {p q : ℂ[X]} (carrier : RawSeparatedAnalyticBranchCarrier p q) :
    ∀ᶠ t in 𝓝[≠] carrier.center, carrier.visible t ≠ 0 := by
  apply (meromorphicOrderAt_ne_top_iff_eventually_ne_zero
    carrier.visible_analytic.meromorphicAt).mp
  rw [carrier.visible_order]
  exact WithTop.coe_ne_top

theorem RawSeparatedAnalyticBranchCarrier.visible_tendsto_zero
    {p q : ℂ[X]} (carrier : RawSeparatedAnalyticBranchCarrier p q) :
    Tendsto carrier.visible (𝓝[≠] carrier.center) (𝓝 0) := by
  apply tendsto_zero_of_meromorphicOrderAt_pos
  rw [carrier.visible_order]
  exact_mod_cast carrier.visibleOrder_positive

theorem RawSeparatedAnalyticBranchCarrier.visible_center_eq_zero
    {p q : ℂ[X]} (carrier : RawSeparatedAnalyticBranchCarrier p q) :
    carrier.visible carrier.center = 0 := by
  have hcenter : Tendsto carrier.visible (𝓝[≠] carrier.center)
      (𝓝 (carrier.visible carrier.center)) :=
    carrier.visible_analytic.continuousAt.mono_left nhdsWithin_le_nhds
  exact tendsto_nhds_unique hcenter carrier.visible_tendsto_zero

theorem RawSeparatedAnalyticBranchCarrier.polynomialFamily_coefficient_analytic
    {p q : ℂ[X]} (carrier : RawSeparatedAnalyticBranchCarrier p q)
    (i : ℕ) :
    AnalyticAt ℂ (fun t ↦ (carrier.polynomialFamily t).coeff i)
      carrier.center := by
  have hleft : AnalyticAt ℂ
      (fun t ↦ carrier.visible t * p.coeff i) carrier.center :=
    carrier.visible_analytic.mul analyticAt_const
  have hright : AnalyticAt ℂ
      (fun _t ↦ carrier.scalar * q.coeff i) carrier.center :=
    analyticAt_const
  simpa only [RawSeparatedAnalyticBranchCarrier.polynomialFamily,
    coeff_sub, coeff_C_mul, Pi.sub_apply] using hleft.sub hright

theorem RawSeparatedAnalyticBranchCarrier.polynomialFamily_degree_le
    {p q : ℂ[X]} (carrier : RawSeparatedAnalyticBranchCarrier p q)
    (t : ℂ) :
    (carrier.polynomialFamily t).natDegree ≤ carrier.degreeBound := by
  calc
    (carrier.polynomialFamily t).natDegree ≤
        max (natDegree (C (carrier.visible t) * p))
          (natDegree (C carrier.scalar * q)) := by
      exact natDegree_sub_le _ _
    _ ≤ max p.natDegree q.natDegree :=
      max_le_max (natDegree_C_mul_le _ p) (natDegree_C_mul_le _ q)
    _ = carrier.degreeBound := rfl

theorem RawSeparatedAnalyticBranchCarrier.polynomialFamily_root
    {p q : ℂ[X]} (carrier : RawSeparatedAnalyticBranchCarrier p q) :
    ∀ᶠ t in 𝓝[≠] carrier.center,
      (carrier.polynomialFamily t).IsRoot (carrier.branch t) := by
  filter_upwards [carrier.relation] with t ht
  rw [Polynomial.IsRoot.def]
  simp only [RawSeparatedAnalyticBranchCarrier.polynomialFamily,
    eval_sub, eval_mul, eval_C]
  exact sub_eq_zero.mpr ht

theorem RawSeparatedAnalyticBranchCarrier.some_coefficient_active
    {p q : ℂ[X]} (carrier : RawSeparatedAnalyticBranchCarrier p q) :
    ∃ i : ℕ, i ≤ carrier.degreeBound ∧
      ¬(fun t ↦ (carrier.polynomialFamily t).coeff i) =ᶠ[
        𝓝[≠] carrier.center] (fun _ ↦ 0) := by
  have hpLeading : p.coeff p.natDegree ≠ 0 := by
    rw [Polynomial.coeff_natDegree]
    exact Polynomial.leadingCoeff_ne_zero.mpr carrier.p_nonzero
  have hqLeading : q.coeff q.natDegree ≠ 0 := by
    rw [Polynomial.coeff_natDegree]
    exact Polynomial.leadingCoeff_ne_zero.mpr carrier.q_nonzero
  by_cases hscalar : carrier.scalar = 0
  · refine ⟨p.natDegree, le_max_left _ _, ?_⟩
    intro hinactive
    have hinactive' :
        (fun t ↦ carrier.visible t * p.coeff p.natDegree) =ᶠ[
          𝓝[≠] carrier.center] (fun _ ↦ 0) := by
      simpa only [RawSeparatedAnalyticBranchCarrier.polynomialFamily,
        coeff_sub, coeff_C_mul, Pi.sub_apply, hscalar, zero_mul, sub_zero]
        using hinactive
    have hfalse : ∀ᶠ _t in 𝓝[≠] carrier.center, False := by
      filter_upwards [carrier.visible_eventually_ne_zero, hinactive'] with
          t htVisible htZero
      exact (mul_ne_zero htVisible hpLeading) htZero
    exact (Filter.Eventually.exists hfalse).choose_spec
  · refine ⟨q.natDegree, le_max_right _ _, ?_⟩
    have hcoefficientCenter :
        (carrier.polynomialFamily carrier.center).coeff q.natDegree ≠ 0 := by
      simp only [RawSeparatedAnalyticBranchCarrier.polynomialFamily,
        coeff_sub, coeff_C_mul, carrier.visible_center_eq_zero, zero_mul,
        zero_sub]
      exact neg_ne_zero.mpr (mul_ne_zero hscalar hqLeading)
    have hcoefficientEventually : ∀ᶠ t in 𝓝[≠] carrier.center,
        (carrier.polynomialFamily t).coeff q.natDegree ≠ 0 :=
      ((carrier.polynomialFamily_coefficient_analytic q.natDegree).continuousAt
        |>.eventually_ne hcoefficientCenter).filter_mono nhdsWithin_le_nhds
    intro hinactive
    have hfalse : ∀ᶠ _t in 𝓝[≠] carrier.center, False := by
      filter_upwards [hcoefficientEventually, hinactive] with
          t htNonzero htZero
      exact htNonzero htZero
    exact (Filter.Eventually.exists hfalse).choose_spec

/-- The raw selected branch constructs the exact degree-bounded analytic root
carrier; coefficient activity is derived rather than supplied. -/
noncomputable def
    RawSeparatedAnalyticBranchCarrier.toDegreeBoundedAnalyticRootCarrier
    {p q : ℂ[X]} (carrier : RawSeparatedAnalyticBranchCarrier p q) :
    DegreeBoundedAnalyticRootCarrier :=
  { center := carrier.center
    degreeBound := carrier.degreeBound
    polynomialFamily := carrier.polynomialFamily
    branch := carrier.branch
    coefficient_analytic := fun i _ ↦
      carrier.polynomialFamily_coefficient_analytic i
    eventually_degree_le := by
      filter_upwards [] with t
      exact carrier.polynomialFamily_degree_le t
    branch_differentiable := carrier.branch_differentiable
    root_identity := carrier.polynomialFamily_root
    some_coefficient_active := carrier.some_coefficient_active }

/-- The raw selected branch constructs the separated analytic root carrier
consumed by the governed boundary theorem. -/
noncomputable def
    RawSeparatedAnalyticBranchCarrier.toSeparatedAnalyticRootCarrier
    {p q : ℂ[X]} (carrier : RawSeparatedAnalyticBranchCarrier p q) :
    SeparatedAnalyticRootCarrier p q :=
  { visibleOrder := carrier.visibleOrder
    visible := carrier.visible
    scalar := carrier.scalar
    rootCarrier := carrier.toDegreeBoundedAnalyticRootCarrier
    p_nonzero := carrier.p_nonzero
    q_nonzero := carrier.q_nonzero
    visibleOrder_positive := carrier.visibleOrder_positive
    visible_analytic := carrier.visible_analytic
    visible_order := carrier.visible_order
    polynomialFamily_eq := rfl }

/-- A selected punctured analytic branch of the raw separated relation already
has the exhaustive constant/finite/pole boundary outcome. -/
theorem RawSeparatedAnalyticBranchCarrier.boundaryOutcome
    {p q : ℂ[X]} (carrier : RawSeparatedAnalyticBranchCarrier p q) :
    BoundaryOutcome carrier.toSeparatedAnalyticRootCarrier := by
  exact carrier.toSeparatedAnalyticRootCarrier.boundaryOutcome

/-- Aggregated raw separated-branch assembly terminal. -/
theorem separated_analytic_branch_assembly_terminal_certificate :
    ∀ (p q : ℂ[X]) (carrier : RawSeparatedAnalyticBranchCarrier p q),
      BoundaryOutcome carrier.toSeparatedAnalyticRootCarrier := by
  intro p q carrier
  exact carrier.boundaryOutcome

end FormalSeparatedAnalyticBranchAssembly
