import Mathlib.Topology.Connected.Basic
import Mathlib.Topology.Order.IntermediateValue
import Mathlib.Tactic
import ZtareProofs.FormalControlledPolynomialOverlapUniqueness
import ZtareProofs.FormalControlledPolynomialUniformRestart

/-!
# Canonical maximal controlled-polynomial trajectories

For a continuous globally bounded complex driver and a complex polynomial,
the union of all compatible local trajectories through one initial state is
an open preconnected maximal solution domain.  Complete overlap uniqueness
makes the pointwise union curve independent of every representative choice.

This construction uses no supplied maximal solution, chain upper bound, Zorn
witness, global state bound, or compatibility callback.
-/

namespace FormalControlledPolynomialMaximalTrajectory

open Filter Polynomial Set
open scoped NNReal Topology

open FormalControlledPolynomialOverlapUniqueness
open FormalControlledPolynomialUniformRestart

/-- One candidate trajectory through the fixed anchor and state. -/
structure ControlledPolynomialTrajectoryCandidate
    (p : ℂ[X]) (carrier : ControlledPolynomialDriverCarrier)
    (anchor : ℝ) (state : ℂ) where
  domain : Set ℝ
  curve : ℝ → ℂ
  domain_open : IsOpen domain
  domain_preconnected : IsPreconnected domain
  anchor_mem : anchor ∈ domain
  initial : curve anchor = state
  ode : ∀ t ∈ domain,
    HasDerivAt curve (carrier.driver t * p.eval (curve t)) t

/-- The union of the domains of all compatible candidates. -/
def maximalDomain
    (p : ℂ[X]) (carrier : ControlledPolynomialDriverCarrier)
    (anchor : ℝ) (state : ℂ) : Set ℝ :=
  ⋃ candidate : ControlledPolynomialTrajectoryCandidate
      p carrier anchor state,
    candidate.domain

/-- Every candidate domain is contained in the union domain. -/
theorem candidate_domain_subset_maximalDomain
    (p : ℂ[X]) (carrier : ControlledPolynomialDriverCarrier)
    (anchor : ℝ) (state : ℂ)
    (candidate : ControlledPolynomialTrajectoryCandidate
      p carrier anchor state) :
    candidate.domain ⊆ maximalDomain p carrier anchor state := by
  exact subset_iUnion (fun current : ControlledPolynomialTrajectoryCandidate
    p carrier anchor state ↦ current.domain) candidate

/-- The union domain is open. -/
theorem maximalDomain_isOpen
    (p : ℂ[X]) (carrier : ControlledPolynomialDriverCarrier)
    (anchor : ℝ) (state : ℂ) :
    IsOpen (maximalDomain p carrier anchor state) := by
  exact isOpen_iUnion fun candidate ↦ candidate.domain_open

/-- The union domain is preconnected because every candidate contains the
same anchor. -/
theorem maximalDomain_isPreconnected
    (p : ℂ[X]) (carrier : ControlledPolynomialDriverCarrier)
    (anchor : ℝ) (state : ℂ) :
    IsPreconnected (maximalDomain p carrier anchor state) := by
  apply isPreconnected_iUnion
  · refine ⟨anchor, ?_⟩
    simp only [mem_iInter]
    intro candidate
    exact candidate.anchor_mem
  · intro candidate
    exact candidate.domain_preconnected

/-- Two candidates agree throughout their common domain. -/
theorem candidate_eqOn_candidate
    (p : ℂ[X]) (carrier : ControlledPolynomialDriverCarrier)
    (anchor : ℝ) (state : ℂ)
    (first second : ControlledPolynomialTrajectoryCandidate
      p carrier anchor state) :
    EqOn first.curve second.curve (first.domain ∩ second.domain) := by
  apply eqOn_of_same_controlled_polynomial_ode p carrier.driverBound
    carrier.driver_bound
  · exact (first.domain_preconnected.ordConnected.inter
      second.domain_preconnected.ordConnected).isPreconnected
  · exact ⟨first.anchor_mem, second.anchor_mem⟩
  · intro t ht
    exact first.ode t ht.1
  · intro t ht
    exact second.ode t ht.2
  · rw [first.initial, second.initial]

/-- Choose a candidate through each time in the union domain, using a fixed
seed candidate outside that domain. -/
noncomputable def chosenCandidate
    (p : ℂ[X]) (carrier : ControlledPolynomialDriverCarrier)
    (anchor : ℝ) (state : ℂ)
    (seed : ControlledPolynomialTrajectoryCandidate p carrier anchor state)
    (t : ℝ) : ControlledPolynomialTrajectoryCandidate
      p carrier anchor state := by
  classical
  exact if ht : t ∈ maximalDomain p carrier anchor state then
      Classical.choose (show ∃ candidate :
          ControlledPolynomialTrajectoryCandidate p carrier anchor state,
          t ∈ candidate.domain by
        simpa only [maximalDomain, mem_iUnion] using ht)
    else seed

/-- The chosen candidate contains its time whenever the time belongs to the
union domain. -/
theorem chosenCandidate_mem
    (p : ℂ[X]) (carrier : ControlledPolynomialDriverCarrier)
    (anchor : ℝ) (state : ℂ)
    (seed : ControlledPolynomialTrajectoryCandidate p carrier anchor state)
    {t : ℝ} (ht : t ∈ maximalDomain p carrier anchor state) :
    t ∈ (chosenCandidate p carrier anchor state seed t).domain := by
  classical
  simp only [chosenCandidate, dif_pos ht]
  exact Classical.choose_spec (show ∃ candidate :
      ControlledPolynomialTrajectoryCandidate p carrier anchor state,
      t ∈ candidate.domain by
    simpa only [maximalDomain, mem_iUnion] using ht)

/-- The pointwise union curve, made choice-independent below. -/
noncomputable def maximalCurve
    (p : ℂ[X]) (carrier : ControlledPolynomialDriverCarrier)
    (anchor : ℝ) (state : ℂ)
    (seed : ControlledPolynomialTrajectoryCandidate p carrier anchor state) :
    ℝ → ℂ := fun t ↦
  (chosenCandidate p carrier anchor state seed t).curve t

/-- Every candidate agrees with the pointwise union curve on its domain. -/
theorem candidate_eqOn_maximalCurve
    (p : ℂ[X]) (carrier : ControlledPolynomialDriverCarrier)
    (anchor : ℝ) (state : ℂ)
    (seed candidate : ControlledPolynomialTrajectoryCandidate
      p carrier anchor state) :
    EqOn candidate.curve
      (maximalCurve p carrier anchor state seed) candidate.domain := by
  intro t ht
  have htmax : t ∈ maximalDomain p carrier anchor state :=
    candidate_domain_subset_maximalDomain p carrier anchor state candidate ht
  have htchosen : t ∈
      (chosenCandidate p carrier anchor state seed t).domain :=
    chosenCandidate_mem p carrier anchor state seed htmax
  have hagree := candidate_eqOn_candidate p carrier anchor state candidate
    (chosenCandidate p carrier anchor state seed t) ⟨ht, htchosen⟩
  simpa only [maximalCurve] using hagree

/-- The pointwise union curve satisfies the ODE at every time in the union
domain; the derivative is transported from a locally selected candidate. -/
theorem maximalCurve_ode
    (p : ℂ[X]) (carrier : ControlledPolynomialDriverCarrier)
    (anchor : ℝ) (state : ℂ)
    (seed : ControlledPolynomialTrajectoryCandidate p carrier anchor state) :
    ∀ t ∈ maximalDomain p carrier anchor state,
      HasDerivAt (maximalCurve p carrier anchor state seed)
        (carrier.driver t *
          p.eval (maximalCurve p carrier anchor state seed t)) t := by
  intro t ht
  obtain ⟨candidate, htcandidate⟩ : ∃ candidate :
      ControlledPolynomialTrajectoryCandidate p carrier anchor state,
      t ∈ candidate.domain := by
    simpa only [maximalDomain, mem_iUnion] using ht
  have hagree := candidate_eqOn_maximalCurve p carrier anchor state seed
    candidate
  have heventually : candidate.curve =ᶠ[𝓝 t]
      maximalCurve p carrier anchor state seed :=
    eventuallyEq_of_mem (candidate.domain_open.mem_nhds htcandidate) hagree
  have hderivative := (candidate.ode t htcandidate).congr_of_eventuallyEq
    heventually.symm
  exact hderivative.congr_deriv (by rw [hagree htcandidate])

/-- The complete maximal-trajectory output. -/
def ControlledPolynomialMaximalTrajectoryOutcome
    (p : ℂ[X]) (carrier : ControlledPolynomialDriverCarrier)
    (anchor : ℝ) (state : ℂ) : Prop :=
  ∃ domain : Set ℝ, ∃ trajectory : ℝ → ℂ,
    IsOpen domain ∧
    IsPreconnected domain ∧
    anchor ∈ domain ∧
    trajectory anchor = state ∧
    (∀ t ∈ domain,
      HasDerivAt trajectory
        (carrier.driver t * p.eval (trajectory t)) t) ∧
    ∀ candidate : ControlledPolynomialTrajectoryCandidate
        p carrier anchor state,
      candidate.domain ⊆ domain ∧
        EqOn candidate.curve trajectory candidate.domain

/-- Uniform restart supplies a seed, and the union of all compatible germs
constructs the canonical maximal controlled-polynomial trajectory. -/
theorem controlledPolynomialDriver_maximalTrajectoryOutcome
    (p : ℂ[X]) (carrier : ControlledPolynomialDriverCarrier)
    (anchor : ℝ) (state : ℂ) :
    ControlledPolynomialMaximalTrajectoryOutcome
      p carrier anchor state := by
  obtain ⟨epsilon, hepsilon, hrestart⟩ :=
    carrier.uniformRestartOutcome p ‖state‖₊
  obtain ⟨solution, hsolutionInitial, hsolutionODE⟩ :=
    hrestart anchor state le_rfl
  let seed : ControlledPolynomialTrajectoryCandidate
      p carrier anchor state :=
    { domain := Ioo (anchor - epsilon) (anchor + epsilon)
      curve := solution
      domain_open := isOpen_Ioo
      domain_preconnected :=
        (convex_Ioo (anchor - epsilon) (anchor + epsilon)).isPreconnected
      anchor_mem := by constructor <;> linarith
      initial := hsolutionInitial
      ode := hsolutionODE }
  refine ⟨maximalDomain p carrier anchor state,
    maximalCurve p carrier anchor state seed,
    maximalDomain_isOpen p carrier anchor state,
    maximalDomain_isPreconnected p carrier anchor state,
    candidate_domain_subset_maximalDomain
      p carrier anchor state seed seed.anchor_mem,
    ?_, maximalCurve_ode p carrier anchor state seed, ?_⟩
  · have hagree := candidate_eqOn_maximalCurve
      p carrier anchor state seed seed seed.anchor_mem
    exact hagree.symm.trans seed.initial
  · intro candidate
    exact ⟨candidate_domain_subset_maximalDomain
      p carrier anchor state candidate,
      candidate_eqOn_maximalCurve p carrier anchor state seed candidate⟩

/-- Aggregated canonical maximal-trajectory terminal. -/
theorem controlled_polynomial_maximal_trajectory_terminal_certificate :
    ∀ (p : ℂ[X]) (carrier : ControlledPolynomialDriverCarrier)
      (anchor : ℝ) (state : ℂ),
      ControlledPolynomialMaximalTrajectoryOutcome
        p carrier anchor state := by
  intro p carrier anchor state
  exact controlledPolynomialDriver_maximalTrajectoryOutcome
    p carrier anchor state

end FormalControlledPolynomialMaximalTrajectory
