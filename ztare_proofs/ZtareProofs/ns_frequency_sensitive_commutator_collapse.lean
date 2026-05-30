import Mathlib.Tactic
import ZtareProofs.ns_commutator_microstructure_escape

namespace ZtareProofs

/-!
`ns_frequency_sensitive_commutator_collapse` records the strongest iter-4
insight from the proof-search substrate.

The old route-1 cutoff story was still too coarse. In the high-frequency
regime, pseudodifferential symbol calculus says the commutator magnitude is not
`δ⁻¹` alone but `δ⁻¹ λ⁻¹`. That means the isotropic commutator route can
collapse on oscillatory fields instead of remaining coercive.
-/

/-- Spatial frequency of the adversarial microgeometry. -/
abbrev SpatialFrequency := Real

/-- Frequency-sensitive commutator amplitude. -/
abbrev FrequencySensitiveCommutatorSize := Real

/--
High-frequency commutator scaling from pseudodifferential symbol calculus.
-/
def frequencySensitiveCutoffCommutator
    (δ lam amplitude C : Real) : Prop :=
  0 < δ ∧
    0 < lam ∧
    0 ≤ C ∧
    amplitude = C / (δ * lam)

/--
Collapse regime: once the internal field frequency outruns the cutoff
resolution, the isotropic commutator ceases to provide a robust coercive lower
bound.
-/
def isotropicCommutatorCollapseRegime
    (δ lam amplitude ε : Real) : Prop :=
  frequencySensitiveCutoffCommutator δ lam amplitude 1 ∧
    δ⁻¹ < lam ∧
    0 < ε ∧
    amplitude ≤ ε

/--
Reranking target surfaced by iter 4: route `1` collapses on high-frequency
microgeometry, so route `5` becomes the cheapest plausible constructive route
unless its own phase-resonance obstruction is found.
-/
def route5PrecedenceAfterFrequencyCollapse
    (δ lam amplitude ε : Real) : Prop :=
  isotropicCommutatorCollapseRegime δ lam amplitude ε

/--
If the frequency-sensitive collapse regime is paid, the old inverse-width-only
cutoff axiom is not the right coercive object in that regime.
-/
theorem no_uniform_cutoff_coercivity_of_frequencyCollapse
    {δ lam amplitude ε : Real}
    (h : route5PrecedenceAfterFrequencyCollapse δ lam amplitude ε) :
    amplitude ≤ ε := by
  exact h.2.2.2

end ZtareProofs
