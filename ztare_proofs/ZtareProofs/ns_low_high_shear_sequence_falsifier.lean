import Mathlib.Tactic
import ZtareProofs.ns_profile_lipschitz_clay_bridge
import ZtareProofs.ns_low_high_lipschitz_reserve_adapter

/-!
# Low-high smooth shear sequence falsifier

This file records the exact continuum fork for the low-high shear catalyst.

It does **not** prove the PDE estimate that closes Navier-Stokes.  Instead it
turns the smooth shear market-impact story into a formal either/or:

* if the fixed LP/Bony topology embeds the shear market-impact costs into the
  global low-frequency Lipschitz reserve ledger, unbounded N^4 execution costs
  contradict a finite critical budget;
* otherwise the missing embedding is the explicit continuum falsifier for the
  Track B closure.

The formulas are intentionally fixed before payoff scoring.  The canonical
model is the smooth divergence-free low shear

`L_N(y) = A_N sin(y) e_x`

paired with high-shell packets at shell `N`, with break-even low energy on the
`N^4` scale for fixed low frequency.  Lean keeps the analytic facts as fields:
future PDE work must instantiate them from a real torus/LP construction.
-/

namespace ZtareProofs.NS

/-- Declared N^4 market-impact lower law for an infinite shear family.

`coeff * shellIndex n^4` is the predeclared lower bound for the reserve cost of
rearming shell `shellIndex n`.  The unboundedness field is the exact continuum
burden: in a real proof it must follow from the shell choice and coefficient,
not from observing a profitable route after the fact. -/
structure N4MarketImpactLowerLaw
    (marketImpactCost : ℕ → Real) where
  coeff : Real
  shellIndex : ℕ → Real
  coeff_positive : 0 < coeff
  n4_lower_bound :
    ∀ n : ℕ,
      coeff * (shellIndex n) ^ (4 : Nat) ≤ marketImpactCost n
  n4_lower_bound_unbounded :
    ∀ B : Real, ∃ n : ℕ,
      B < coeff * (shellIndex n) ^ (4 : Nat)

/-- An N^4 lower law makes the market-impact entries pointwise unbounded. -/
theorem market_impact_pointwise_unbounded_of_n4_lower_law
    (marketImpactCost : ℕ → Real)
    (R : N4MarketImpactLowerLaw marketImpactCost) :
    ∀ B : Real, ∃ n : ℕ, B < marketImpactCost n := by
  intro B
  obtain ⟨n, hn⟩ := R.n4_lower_bound_unbounded B
  exact ⟨n, lt_of_lt_of_le hn (R.n4_lower_bound n)⟩

/-- Fixed smooth shear family for the low-high continuum falsifier.

The formula fields are propositions because this module is a verifier
interface, not a construction of torus function spaces.  They force the future
proof/counterexample to declare the actual smooth divergence-free shear family,
LP shell localization, market-impact cost, and embedding into the global
reserve ledger before using any payoff. -/
structure SmoothShearMarketImpactSequence
    (O : TrackBProfileLipschitzControlObligation)
    (u0 : SmoothNSInitialData)
    (marketImpactCost : ℕ → Real) where
  topology : FixedLPBonyTopology
  lowShearFormula : ℕ → Prop
  highShellPacketFormula : ℕ → Prop
  fixed_flat_torus_lp_bony_topology : Prop
  low_shear_is_smooth_periodic_divergence_free :
    ∀ n : ℕ, lowShearFormula n
  high_packet_is_smooth_divergence_free_lp_localized :
    ∀ n : ℕ, highShellPacketFormula n
  formulas_declared_before_payoff : Prop
  market_impact_cost_declared_before_payoff : Prop
  market_impact_cost_nonnegative :
    ∀ n : ℕ, 0 ≤ marketImpactCost n
  market_impact_embeds_in_global_lipschitz_ledger :
    ∀ n : ℕ,
      marketImpactCost n ≤
        (O.lipschitz_bridge.ledger_of_evolution
          (O.evolution_of_initial_data u0)).lipschitzCost n

/-- A smooth shear sequence with pointwise-unbounded embedded market-impact
costs triggers the top-level closure falsifier. -/
theorem no_profile_lipschitz_closure_of_smooth_shear_market_impact_sequence
    (O : TrackBProfileLipschitzControlObligation)
    (u0 : SmoothNSInitialData)
    (marketImpactCost : ℕ → Real)
    (S : SmoothShearMarketImpactSequence O u0 marketImpactCost)
    (hunbounded :
      ∀ B : Real, ∃ n : ℕ, B < marketImpactCost n) :
    False := by
  let U := O.evolution_of_initial_data u0
  let L := O.lipschitz_bridge.ledger_of_evolution U
  have hprefix_unbounded :
      ∀ B : Real, ∃ N : ℕ, B < nsPrefixSum marketImpactCost N :=
    ns_prefix_sum_unbounded_of_pointwise_unbounded_nonnegative
      marketImpactCost
      S.market_impact_cost_nonnegative
      hunbounded
  obtain ⟨N, hover⟩ := hprefix_unbounded L.criticalBudget
  have hbudget :
      nsPrefixSum marketImpactCost N ≤ L.criticalBudget :=
    generated_market_impact_prefix_le_budget_of_profile_lipschitz_closure
      O u0 marketImpactCost
      S.market_impact_embeds_in_global_lipschitz_ledger
      N
  exact not_lt_of_ge hbudget hover

/-- N^4 version of the smooth shear falsifier.

This is the formalized version of the market-impact fork: fixed-frequency
smooth shear rearming with an embedded N^4 lower law cannot be reconciled with
the composed profile + Lipschitz closure and a finite critical budget.  A
future PDE proof must therefore show that actual Navier-Stokes topology either
prevents such an embedded sequence or prices it before it can form an infinite
rearming cascade. -/
theorem no_profile_lipschitz_closure_of_smooth_shear_n4_market_impact_sequence
    (O : TrackBProfileLipschitzControlObligation)
    (u0 : SmoothNSInitialData)
    (marketImpactCost : ℕ → Real)
    (S : SmoothShearMarketImpactSequence O u0 marketImpactCost)
    (R : N4MarketImpactLowerLaw marketImpactCost) :
    False :=
  no_profile_lipschitz_closure_of_smooth_shear_market_impact_sequence
    O u0 marketImpactCost S
    (market_impact_pointwise_unbounded_of_n4_lower_law
      marketImpactCost R)

/-- Exact remaining continuum obligation for the low-high shear branch.

The branch is closed only if one can instantiate the fixed topology, the smooth
shear/high-packet sequence, and the reserve embedding in a way that avoids the
N^4 unbounded-prefix contradiction. -/
structure LowHighShearContinuumPDEObligation where
  fixed_flat_torus_profile_topology : Prop
  fixed_bony_lp_decomposition : Prop
  smooth_divergence_free_shear_formula_declared : Prop
  high_shell_packets_declared : Prop
  market_impact_cost_embeds_in_global_lipschitz_ledger : Prop
  n4_market_impact_lower_law_proved_or_falsified : Prop
  unbounded_prefix_falsifier_resolved : Prop
  no_posthoc_reserve_or_observable_choice : Prop

end ZtareProofs.NS
