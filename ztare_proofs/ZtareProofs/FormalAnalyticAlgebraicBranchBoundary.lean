import Mathlib.Tactic
import ZtareProofs.FormalAnalyticPolynomialRootSelection
import ZtareProofs.FormalMeromorphicInfinityChart
import ZtareProofs.FormalSeparatedPolynomialBranchValuation

/-!
# Boundary trichotomy for a selected analytic algebraic branch

A single-valued punctured analytic root of a degree-bounded analytic
polynomial family is meromorphic.  For a separated polynomial family this
gives an exhaustive local alternative: a constant finite equilibrium, a
nonconstant finite branch of positive integral order, or a pole of negative
integral order with an analytic reciprocal chart.
-/

namespace FormalAnalyticAlgebraicBranchBoundary

open Filter Polynomial
open scoped Topology

open FormalAnalyticPuncturedExtension
open FormalAnalyticPolynomialRootSelection
open FormalMeromorphicInfinityChart
open FormalSeparatedPolynomialBranchValuation

/-- A selected analytic algebraic root whose polynomial family is the exact
separated relation. Hidden meromorphicity and hidden boundary order are not
stored. -/
structure SeparatedAnalyticRootCarrier (p q : ℂ[X]) where
  visibleOrder : ℕ
  visible : ℂ → ℂ
  scalar : ℂ
  rootCarrier : DegreeBoundedAnalyticRootCarrier
  p_nonzero : p ≠ 0
  q_nonzero : q ≠ 0
  visibleOrder_positive : 0 < visibleOrder
  visible_analytic : AnalyticAt ℂ visible rootCarrier.center
  visible_order :
    meromorphicOrderAt visible rootCarrier.center =
      ((visibleOrder : ℤ) : WithTop ℤ)
  polynomialFamily_eq : rootCarrier.polynomialFamily = fun t ↦
    C (visible t) * p - C scalar * q

/-- The selected algebraic-root identity is the separated relation itself. -/
theorem SeparatedAnalyticRootCarrier.relation
    {p q : ℂ[X]} (carrier : SeparatedAnalyticRootCarrier p q) :
    (fun t ↦ carrier.visible t * p.eval (carrier.rootCarrier.branch t)) =ᶠ[
        𝓝[≠] carrier.rootCarrier.center]
      (fun t ↦ carrier.scalar * q.eval (carrier.rootCarrier.branch t)) := by
  filter_upwards [carrier.rootCarrier.root_identity] with t ht
  rw [Polynomial.IsRoot.def, carrier.polynomialFamily_eq] at ht
  have ht' :
      carrier.visible t * p.eval (carrier.rootCarrier.branch t) -
          carrier.scalar * q.eval (carrier.rootCarrier.branch t) = 0 := by
    simpa only [eval_sub, eval_mul, eval_C] using ht
  exact sub_eq_zero.mp ht'

/-- Exact local outcome for a separated analytic algebraic branch. -/
def BoundaryOutcome {p q : ℂ[X]}
    (carrier : SeparatedAnalyticRootCarrier p q) : Prop :=
  (∃ beta : ℂ,
      carrier.rootCarrier.branch =ᶠ[𝓝[≠] carrier.rootCarrier.center]
        (fun _ ↦ beta) ∧
      (p.IsRoot beta ∨ q.IsRoot beta)) ∨
  (∃ finite : FiniteSeparatedRelationCarrier p q,
      carrier.rootCarrier.branch =ᶠ[𝓝[≠] carrier.rootCarrier.center]
        (fun t ↦ finite.boundaryCenter + finite.displacement t) ∧
      finite.scalar ≠ 0 ∧
      finite.visibleOrder = finite.branchOrder *
        (q.rootMultiplicity finite.boundaryCenter -
          p.rootMultiplicity finite.boundaryCenter) ∧
      p.rootMultiplicity finite.boundaryCenter <
        q.rootMultiplicity finite.boundaryCenter ∧
      q.IsRoot finite.boundaryCenter) ∨
  (∃ pole : PoleSeparatedRelationCarrier p q,
      pole.hidden = carrier.rootCarrier.branch ∧
      pole.scalar ≠ 0 ∧
      pole.visibleOrder = pole.poleOrder *
        (pole.pDegree - pole.qDegree) ∧
      pole.qDegree < pole.pDegree)

private theorem SeparatedAnalyticRootCarrier.visible_eventually_ne_zero
    {p q : ℂ[X]} (carrier : SeparatedAnalyticRootCarrier p q) :
    ∀ᶠ t in 𝓝[≠] carrier.rootCarrier.center, carrier.visible t ≠ 0 := by
  apply (meromorphicOrderAt_ne_top_iff_eventually_ne_zero
    carrier.visible_analytic.meromorphicAt).mp
  rw [carrier.visible_order]
  exact WithTop.coe_ne_top

private theorem SeparatedAnalyticRootCarrier.visible_tendsto_zero
    {p q : ℂ[X]} (carrier : SeparatedAnalyticRootCarrier p q) :
    Tendsto carrier.visible (𝓝[≠] carrier.rootCarrier.center) (𝓝 0) := by
  apply tendsto_zero_of_meromorphicOrderAt_pos
  rw [carrier.visible_order]
  exact_mod_cast carrier.visibleOrder_positive

private theorem SeparatedAnalyticRootCarrier.constant_boundary_equilibrium
    {p q : ℂ[X]} (carrier : SeparatedAnalyticRootCarrier p q)
    (beta : ℂ)
    (hconstant : carrier.rootCarrier.branch =ᶠ[
      𝓝[≠] carrier.rootCarrier.center] fun _ ↦ beta) :
    p.IsRoot beta ∨ q.IsRoot beta := by
  have hrelation :
      (fun t ↦ carrier.visible t * p.eval beta) =ᶠ[
          𝓝[≠] carrier.rootCarrier.center]
        (fun _ ↦ carrier.scalar * q.eval beta) := by
    filter_upwards [carrier.relation, hconstant] with t ht hbranch
    simpa [hbranch] using ht
  by_cases hscalar : carrier.scalar = 0
  · left
    have heventually : ∀ᶠ t in 𝓝[≠] carrier.rootCarrier.center,
        carrier.visible t ≠ 0 ∧
          carrier.visible t * p.eval beta =
            carrier.scalar * q.eval beta :=
      carrier.visible_eventually_ne_zero.and hrelation
    obtain ⟨t, htVisible, htRelation⟩ := heventually.exists
    rw [hscalar, zero_mul] at htRelation
    rw [Polynomial.IsRoot.def]
    exact (mul_eq_zero.mp htRelation).resolve_left htVisible
  · right
    have hleft : Tendsto (fun t ↦ carrier.visible t * p.eval beta)
        (𝓝[≠] carrier.rootCarrier.center) (𝓝 0) := by
      simpa using carrier.visible_tendsto_zero.mul_const (p.eval beta)
    have hrightZero : Tendsto
        (fun _ : ℂ ↦ carrier.scalar * q.eval beta)
        (𝓝[≠] carrier.rootCarrier.center) (𝓝 0) :=
      Tendsto.congr' hrelation hleft
    have hright : Tendsto
        (fun _ : ℂ ↦ carrier.scalar * q.eval beta)
        (𝓝[≠] carrier.rootCarrier.center)
        (𝓝 (carrier.scalar * q.eval beta)) := tendsto_const_nhds
    have hproduct : carrier.scalar * q.eval beta = 0 :=
      tendsto_nhds_unique hright hrightZero
    rw [Polynomial.IsRoot.def]
    exact (mul_eq_zero.mp hproduct).resolve_left hscalar

private theorem exists_positive_order_of_nonconstant_extension
    {branch extension : ℂ → ℂ} {center : ℂ}
    (hbranch : branch =ᶠ[𝓝[≠] center] extension)
    (hanalytic : AnalyticAt ℂ extension center)
    (hnonconstant :
      ¬branch =ᶠ[𝓝[≠] center] fun _ ↦ extension center) :
    ∃ order : ℕ,
      0 < order ∧
      meromorphicOrderAt (fun t ↦ extension t - extension center) center =
        ((order : ℤ) : WithTop ℤ) := by
  let displacement : ℂ → ℂ := fun t ↦ extension t - extension center
  have hdisplacementAnalytic : AnalyticAt ℂ displacement center := by
    dsimp [displacement]
    fun_prop
  have hdisplacementZero : displacement center = 0 := by
    simp [displacement]
  have hdisplacementNotEventuallyZero :
      ¬displacement =ᶠ[𝓝[≠] center] fun _ ↦ 0 := by
    intro hzero
    apply hnonconstant
    filter_upwards [hbranch, hzero] with t ht htzero
    rw [ht]
    dsimp [displacement] at htzero
    exact sub_eq_zero.mp htzero
  have hfinite : meromorphicOrderAt displacement center ≠ ⊤ := by
    intro htop
    apply hdisplacementNotEventuallyZero
    exact meromorphicOrderAt_eq_top_iff.mp htop
  have htendsto : Tendsto displacement (𝓝[≠] center) (𝓝 0) := by
    have hcontinuous := hdisplacementAnalytic.continuousAt
    change Tendsto displacement (𝓝 center)
      (𝓝 (displacement center)) at hcontinuous
    simpa only [hdisplacementZero] using
      hcontinuous.mono_left nhdsWithin_le_nhds
  have hpositive : 0 < meromorphicOrderAt displacement center :=
    (tendsto_zero_iff_meromorphicOrderAt_pos
      hdisplacementAnalytic.meromorphicAt).mp htendsto
  let orderInt : ℤ := (meromorphicOrderAt displacement center).untop₀
  have horderInt : meromorphicOrderAt displacement center =
      (orderInt : WithTop ℤ) :=
    (WithTop.coe_untop₀_of_ne_top hfinite).symm
  have horderIntPositive : 0 < orderInt := by
    rw [horderInt] at hpositive
    exact_mod_cast hpositive
  let order : ℕ := orderInt.toNat
  have horderPositive : 0 < order := by
    have hcast : ((orderInt.toNat : ℕ) : ℤ) = orderInt :=
      Int.toNat_of_nonneg horderIntPositive.le
    have hcastPositive : (0 : ℤ) < (orderInt.toNat : ℕ) := by
      rwa [hcast]
    exact_mod_cast hcastPositive
  have horder : meromorphicOrderAt displacement center =
      ((order : ℤ) : WithTop ℤ) := by
    rw [horderInt]
    congr 1
    exact (Int.toNat_of_nonneg horderIntPositive.le).symm
  exact ⟨order, horderPositive, horder⟩

private theorem exists_pole_order
    {branch : ℂ → ℂ} {center : ℂ}
    (hnegative : meromorphicOrderAt branch center < 0) :
    ∃ poleOrder : ℕ,
      0 < poleOrder ∧
      meromorphicOrderAt branch center =
        ((-(poleOrder : ℤ) : ℤ) : WithTop ℤ) := by
  have hfinite : meromorphicOrderAt branch center ≠ ⊤ :=
    ne_top_of_lt hnegative
  let orderInt : ℤ := (meromorphicOrderAt branch center).untop₀
  have horderInt : meromorphicOrderAt branch center =
      (orderInt : WithTop ℤ) :=
    (WithTop.coe_untop₀_of_ne_top hfinite).symm
  have horderIntNegative : orderInt < 0 := by
    rw [horderInt] at hnegative
    exact_mod_cast hnegative
  let poleOrder : ℕ := orderInt.natAbs
  have hpolePositive : 0 < poleOrder :=
    Int.natAbs_pos.mpr (ne_of_lt horderIntNegative)
  have horderPole : meromorphicOrderAt branch center =
      ((-(poleOrder : ℤ) : ℤ) : WithTop ℤ) := by
    rw [horderInt]
    congr 1
    dsimp [poleOrder]
    rw [Int.ofNat_natAbs_of_nonpos horderIntNegative.le]
    simp
  exact ⟨poleOrder, hpolePositive, horderPole⟩

/-- Every selected separated analytic algebraic branch has a constructed
constant, finite-positive-order, or pole-negative-order boundary carrier. -/
theorem SeparatedAnalyticRootCarrier.boundaryOutcome
    {p q : ℂ[X]} (carrier : SeparatedAnalyticRootCarrier p q) :
    BoundaryOutcome carrier := by
  have hmeromorphic : MeromorphicAt carrier.rootCarrier.branch
      carrier.rootCarrier.center := carrier.rootCarrier.branch_meromorphicAt
  by_cases hfinite : HasFiniteAnalyticExtension carrier.rootCarrier.branch
      carrier.rootCarrier.center
  · obtain ⟨extension, hbranchExtension, hextensionAnalytic⟩ := hfinite
    by_cases hconstant : carrier.rootCarrier.branch =ᶠ[
        𝓝[≠] carrier.rootCarrier.center] fun _ ↦
          extension carrier.rootCarrier.center
    · left
      exact ⟨extension carrier.rootCarrier.center, hconstant,
        carrier.constant_boundary_equilibrium
          (extension carrier.rootCarrier.center) hconstant⟩
    · right
      left
      obtain ⟨branchOrder, hbranchOrderPositive, hbranchOrder⟩ :=
        exists_positive_order_of_nonconstant_extension hbranchExtension
          hextensionAnalytic hconstant
      let displacement : ℂ → ℂ := fun t ↦
        extension t - extension carrier.rootCarrier.center
      have hdisplacementAnalytic : AnalyticAt ℂ displacement
          carrier.rootCarrier.center := by
        dsimp [displacement]
        fun_prop
      have hdisplacementZero :
          displacement carrier.rootCarrier.center = 0 := by
        simp [displacement]
      have hrelation :
          (fun t ↦ carrier.visible t * p.eval
            (extension carrier.rootCarrier.center + displacement t)) =ᶠ[
              𝓝[≠] carrier.rootCarrier.center]
            (fun t ↦ carrier.scalar * q.eval
              (extension carrier.rootCarrier.center + displacement t)) := by
        filter_upwards [carrier.relation, hbranchExtension]
          with t ht hbranch
        simpa [displacement, hbranch] using ht
      let finite : FiniteSeparatedRelationCarrier p q :=
        { parameterCenter := carrier.rootCarrier.center
          boundaryCenter := extension carrier.rootCarrier.center
          visibleOrder := carrier.visibleOrder
          branchOrder := branchOrder
          visible := carrier.visible
          displacement := displacement
          scalar := carrier.scalar
          p_nonzero := carrier.p_nonzero
          q_nonzero := carrier.q_nonzero
          visibleOrder_positive := carrier.visibleOrder_positive
          branchOrder_positive := hbranchOrderPositive
          visible_analytic := carrier.visible_analytic
          visible_order := carrier.visible_order
          displacement_analytic := hdisplacementAnalytic
          displacement_zero := hdisplacementZero
          displacement_order := by simpa [displacement] using hbranchOrder
          relation := hrelation }
      have hoverlap : carrier.rootCarrier.branch =ᶠ[
          𝓝[≠] carrier.rootCarrier.center]
          (fun t ↦ finite.boundaryCenter + finite.displacement t) := by
        filter_upwards [hbranchExtension] with t ht
        simp [finite, displacement, ht]
      obtain ⟨hscalar, hbalance, hstrict, hroot⟩ :=
        finite.natural_balance_and_boundary_root
      exact ⟨finite, hoverlap, hscalar, hbalance, hstrict, hroot⟩
  · right
    right
    obtain ⟨hnegative, _hcobounded, hreciprocalChart⟩ :=
      meromorphic_infinity_chart_terminal_certificate
        carrier.rootCarrier.branch carrier.rootCarrier.center
        hmeromorphic hfinite
    obtain ⟨poleOrder, hpoleOrderPositive, hpoleOrder⟩ :=
      exists_pole_order hnegative
    obtain ⟨reciprocal, hreciprocal, hreciprocalAnalytic,
        hreciprocalZero⟩ := hreciprocalChart
    let pole : PoleSeparatedRelationCarrier p q :=
      { parameterCenter := carrier.rootCarrier.center
        visibleOrder := carrier.visibleOrder
        poleOrder := poleOrder
        pDegree := p.natDegree
        qDegree := q.natDegree
        visible := carrier.visible
        hidden := carrier.rootCarrier.branch
        reciprocal := reciprocal
        scalar := carrier.scalar
        p_nonzero := carrier.p_nonzero
        q_nonzero := carrier.q_nonzero
        visibleOrder_positive := carrier.visibleOrder_positive
        poleOrder_positive := hpoleOrderPositive
        p_degree := rfl
        q_degree := rfl
        visible_analytic := carrier.visible_analytic
        visible_order := carrier.visible_order
        hidden_meromorphic := hmeromorphic
        hidden_order := hpoleOrder
        reciprocal_analytic := hreciprocalAnalytic
        reciprocal_zero := hreciprocalZero
        reciprocal_eq_inverse := hreciprocal.symm
        relation := carrier.relation }
    obtain ⟨hscalar, hbalance, hstrict⟩ :=
      pole.natural_balance_and_degree_drop
    exact ⟨pole, rfl, hscalar, hbalance, hstrict⟩

/-- Aggregated boundary-classification terminal. -/
theorem analytic_algebraic_branch_boundary_terminal_certificate :
    ∀ (p q : ℂ[X]) (carrier : SeparatedAnalyticRootCarrier p q),
      BoundaryOutcome carrier := by
  intro p q carrier
  exact carrier.boundaryOutcome

end FormalAnalyticAlgebraicBranchBoundary
