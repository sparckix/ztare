import Mathlib.Analysis.Normed.Group.Bounded
import Mathlib.Topology.Order.OrderClosed
import Mathlib.Tactic

/-!
# Uniform restart and the finite-endpoint escape alternative

This file isolates the maximal-continuation argument from any particular ODE.
A solution category is represented by a restriction-stable predicate on
curves and time domains.  Solutions are unique on open preconnected overlaps,
and every bounded state ball has one restart time that works uniformly for all
late initial points in that ball.

Under those hypotheses, a trajectory either extends through its finite right
endpoint or its norm tends to infinity there.  Agreement between a restart
and the original trajectory is derived from uniqueness; it is not restart
data.
-/

namespace FormalUniformRestartEndpointEscape

open Filter Set
open scoped Topology

/-- Abstract well-posed trajectory data near a finite right endpoint. -/
structure UniformRestartEndpointCarrier
    (E : Type*) [SeminormedAddCommGroup E] where
  left : ℝ
  endpoint : ℝ
  trajectory : ℝ → E
  solutionOn : (ℝ → E) → Set ℝ → Prop
  left_lt_endpoint : left < endpoint
  solution_mono : ∀ {curve : ℝ → E} {smaller larger : Set ℝ},
    smaller ⊆ larger → solutionOn curve larger → solutionOn curve smaller
  solution_unique : ∀ {first second : ℝ → E} {domain : Set ℝ}
      {anchor : ℝ},
    IsOpen domain →
    IsPreconnected domain →
    anchor ∈ domain →
    solutionOn first domain →
    solutionOn second domain →
    first anchor = second anchor →
    EqOn first second domain
  trajectory_solution : solutionOn trajectory (Ioo left endpoint)
  uniform_restart : ∀ radius : ℝ, 0 ≤ radius →
    ∃ epsilon : ℝ, 0 < epsilon ∧
      ∀ restartTime ∈ Ioo left endpoint,
        ‖trajectory restartTime‖ ≤ radius →
        ∃ restarted : ℝ → E,
          restarted restartTime = trajectory restartTime ∧
          solutionOn restarted
            (Ioo (restartTime - epsilon) (restartTime + epsilon))

/-- A continuation through the endpoint, including exact one-sided overlap
with the selected incoming trajectory. -/
def FiniteEndpointExtensionOutcome
    {E : Type*} [SeminormedAddCommGroup E]
    (carrier : UniformRestartEndpointCarrier E) : Prop :=
  ∃ extension : ℝ → E, ∃ lower upper : ℝ,
    lower < carrier.endpoint ∧
    carrier.endpoint < upper ∧
    carrier.trajectory =ᶠ[𝓝[<] carrier.endpoint] extension ∧
    carrier.solutionOn extension (Ioo lower upper)

/-- Exact endpoint alternative supplied by uniform restart and uniqueness. -/
def UniformRestartEndpointOutcome
    {E : Type*} [SeminormedAddCommGroup E]
    (carrier : UniformRestartEndpointCarrier E) : Prop :=
  Tendsto (fun t ↦ ‖carrier.trajectory t‖)
      (𝓝[<] carrier.endpoint) atTop ∨
    FiniteEndpointExtensionOutcome carrier

/-- Uniform restart on bounded state balls turns every failure of norm escape
into a continuation through the endpoint. -/
theorem UniformRestartEndpointCarrier.uniformRestartEndpointOutcome
    {E : Type*} [SeminormedAddCommGroup E]
    (carrier : UniformRestartEndpointCarrier E) :
    UniformRestartEndpointOutcome carrier := by
  by_cases hescape : Tendsto (fun t ↦ ‖carrier.trajectory t‖)
      (𝓝[<] carrier.endpoint) atTop
  · exact Or.inl hescape
  · right
    have hthreshold : ∃ threshold : ℝ,
        ¬ ∀ᶠ t in 𝓝[<] carrier.endpoint,
          threshold ≤ ‖carrier.trajectory t‖ := by
      by_contra hall
      push Not at hall
      exact hescape (tendsto_atTop.2 hall)
    obtain ⟨threshold, hthreshold⟩ := hthreshold
    let radius : ℝ := max threshold 0
    have hradius : 0 ≤ radius := le_max_right _ _
    obtain ⟨epsilon, hepsilon, hrestart⟩ :=
      carrier.uniform_restart radius hradius
    have hnotEventuallyLarge :
        ¬ ∀ᶠ t in 𝓝[<] carrier.endpoint,
          radius < ‖carrier.trajectory t‖ := by
      intro hlarge
      apply hthreshold
      filter_upwards [hlarge] with t ht
      exact (le_max_left threshold 0).trans ht.le
    have hfrequentBounded : ∃ᶠ t in 𝓝[<] carrier.endpoint,
        ‖carrier.trajectory t‖ ≤ radius := by
      simpa only [not_lt] using
        (not_eventually.mp hnotEventuallyLarge)
    let nearLower : ℝ :=
      max carrier.left (carrier.endpoint - epsilon / 2)
    have hnearLower : nearLower < carrier.endpoint := by
      apply max_lt carrier.left_lt_endpoint
      linarith
    have hnear : ∀ᶠ t in 𝓝[<] carrier.endpoint,
        t ∈ Ioo nearLower carrier.endpoint :=
      Ioo_mem_nhdsLT hnearLower
    obtain ⟨restartTime, hbounded, hrestartTimeNear⟩ :=
      (hfrequentBounded.and_eventually hnear).exists
    have hrestartTime : restartTime ∈ Ioo carrier.left carrier.endpoint := by
      exact ⟨(le_max_left carrier.left
        (carrier.endpoint - epsilon / 2)).trans_lt
          hrestartTimeNear.1, hrestartTimeNear.2⟩
    obtain ⟨restarted, hrestartedAt, hrestartedSolution⟩ :=
      hrestart restartTime hrestartTime hbounded
    let overlapLower : ℝ :=
      max carrier.left (restartTime - epsilon)
    have hoverlapLowerRestart : overlapLower < restartTime := by
      apply max_lt hrestartTime.1
      linarith
    have hendpointUpper : carrier.endpoint < restartTime + epsilon := by
      have htimeLower :
          carrier.endpoint - epsilon / 2 < restartTime :=
        (le_max_right carrier.left
          (carrier.endpoint - epsilon / 2)).trans_lt
            hrestartTimeNear.1
      linarith
    have hoverlapLowerEndpoint : overlapLower < carrier.endpoint :=
      hoverlapLowerRestart.trans hrestartTime.2
    let overlap : Set ℝ := Ioo overlapLower carrier.endpoint
    have hoverlapTrajectory : overlap ⊆ Ioo carrier.left carrier.endpoint := by
      intro t ht
      exact ⟨(le_max_left carrier.left
        (restartTime - epsilon)).trans_lt ht.1, ht.2⟩
    have hoverlapRestarted :
        overlap ⊆ Ioo (restartTime - epsilon) (restartTime + epsilon) := by
      intro t ht
      exact ⟨(le_max_right carrier.left
        (restartTime - epsilon)).trans_lt ht.1,
        ht.2.trans hendpointUpper⟩
    have htrajectoryOnOverlap : carrier.solutionOn carrier.trajectory overlap :=
      carrier.solution_mono hoverlapTrajectory carrier.trajectory_solution
    have hrestartedOnOverlap : carrier.solutionOn restarted overlap :=
      carrier.solution_mono hoverlapRestarted hrestartedSolution
    have hrestartTimeOverlap : restartTime ∈ overlap :=
      ⟨hoverlapLowerRestart, hrestartTime.2⟩
    have hagreeOnOverlap : EqOn carrier.trajectory restarted overlap :=
      carrier.solution_unique isOpen_Ioo
        (convex_Ioo overlapLower carrier.endpoint).isPreconnected
        hrestartTimeOverlap htrajectoryOnOverlap hrestartedOnOverlap
        hrestartedAt.symm
    have hagreeEndpoint :
        carrier.trajectory =ᶠ[𝓝[<] carrier.endpoint] restarted :=
      eventuallyEq_of_mem (Ioo_mem_nhdsLT hoverlapLowerEndpoint)
        hagreeOnOverlap
    exact ⟨restarted, restartTime - epsilon, restartTime + epsilon,
      (sub_lt_self restartTime hepsilon).trans hrestartTime.2,
      hendpointUpper, hagreeEndpoint, hrestartedSolution⟩

/-- A maximal trajectory, expressed as the absence of any continuation of the
declared solution category, must escape every bounded state ball. -/
theorem UniformRestartEndpointCarrier.normEscape_of_noFiniteEndpointExtension
    {E : Type*} [SeminormedAddCommGroup E]
    (carrier : UniformRestartEndpointCarrier E)
    (hmaximal : ¬ FiniteEndpointExtensionOutcome carrier) :
    Tendsto (fun t ↦ ‖carrier.trajectory t‖)
      (𝓝[<] carrier.endpoint) atTop := by
  rcases carrier.uniformRestartEndpointOutcome with hescape | hextension
  · exact hescape
  · exact False.elim (hmaximal hextension)

/-- Aggregated uniform-restart endpoint terminal. -/
theorem uniform_restart_endpoint_escape_terminal_certificate :
    ∀ {E : Type*} [SeminormedAddCommGroup E]
      (carrier : UniformRestartEndpointCarrier E),
      UniformRestartEndpointOutcome carrier ∧
      (¬ FiniteEndpointExtensionOutcome carrier →
        Tendsto (fun t ↦ ‖carrier.trajectory t‖)
          (𝓝[<] carrier.endpoint) atTop) := by
  intro E _ carrier
  exact ⟨carrier.uniformRestartEndpointOutcome,
    carrier.normEscape_of_noFiniteEndpointExtension⟩

end FormalUniformRestartEndpointEscape
