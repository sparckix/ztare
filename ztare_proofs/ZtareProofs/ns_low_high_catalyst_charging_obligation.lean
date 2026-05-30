import Mathlib.Tactic
import ZtareProofs.ns_littlewood_paley_paraproduct_bridge
import ZtareProofs.ns_continuum_tail_bound

/-!
# Low-high catalyst charging obligation

This file connects an older continuum-tail object,
`LeakageAbsorptionEstimate`, to the new Track B LP/paraproduct bridge.

It does **not** prove the PDE leakage estimate.  It proves the adapter:
if a low-high catalyst interaction is represented by an explicit leakage
budget and that leakage is absorbed by a reserve loss channel, then the
low-high paraproduct interaction is priced.

This is the first concrete paraproduct-branch target after Phase 5FT.
-/

namespace ZtareProofs.NS

/-- A low-high catalyst interaction represented by the continuum tail/leakage
budget.  The equalities are part of the anti-tautology contract: the interaction
payoff and price must be identified with the predeclared leakage ledger, not
chosen after a profitable route is observed. -/
structure LowHighCatalystLeakageBridge where
  interaction : LPInteractionLedger
  budget : ZtareProofs.CoreTailBudget
  leakage : ZtareProofs.LeakageAbsorptionEstimate
  is_low_high : interaction.interactionClass = LPParaproductClass.lowHigh
  leakage_represents : leakage.represents budget
  leakage_absorbing : leakage.absorbing
  payoff_eq_leakage_gain : interaction.payoff = budget.leakageGain
  price_eq_leakage_loss : interaction.price = budget.leakageLoss

/-- Leakage absorption prices a declared low-high catalyst interaction. -/
theorem low_high_interaction_no_arbitrage_of_leakage_absorption
    (H : LowHighCatalystLeakageBridge) :
    InteractionNoArbitrage H.interaction := by
  have hleak : ZtareProofs.lowHighLeakageControlled H.budget :=
    ZtareProofs.low_high_leakage_controlled_of_absorption
      H.budget H.leakage H.leakage_represents H.leakage_absorbing
  unfold InteractionNoArbitrage
  unfold ZtareProofs.lowHighLeakageControlled at hleak
  rw [H.payoff_eq_leakage_gain, H.price_eq_leakage_loss]
  exact hleak

/-- Branch-positive payload for low-high catalyst charging.  A future substrate
can close this branch by supplying a class of low-high interactions and a
bridge for every member of that class. -/
structure ClosedLowHighCatalystPositive where
  Class : LPInteractionLedger → Prop
  bridge_of_class :
    ∀ T : LPInteractionLedger,
      Class T →
        ∃ H : LowHighCatalystLeakageBridge, H.interaction = T

/-- Branch-negative payload: a concrete low-high interaction whose payoff
strictly exceeds price. -/
structure ClosedLowHighCatalystNegative where
  interaction : LPInteractionLedger
  is_low_high : interaction.interactionClass = LPParaproductClass.lowHigh
  arbitrage : interaction.price < interaction.payoff

/-- If a class has a leakage-absorption bridge, every member is priced. -/
theorem low_high_class_no_arbitrage_of_closed_positive
    (P : ClosedLowHighCatalystPositive)
    (T : LPInteractionLedger)
    (hT : P.Class T) :
    InteractionNoArbitrage T := by
  obtain ⟨H, hHT⟩ := P.bridge_of_class T hT
  rw [← hHT]
  exact low_high_interaction_no_arbitrage_of_leakage_absorption H

/-- Finite falsifier for an underpriced low-high catalyst reserve. -/
structure LowHighCatalystReserveShortfallFalsifier
    (H : LowHighCatalystLeakageBridge) where
  declared_catalyst_gain_exceeds_reserve :
    H.budget.leakageLoss < H.budget.leakageGain

/-- A leakage-absorption low-high bridge and a same-budget reserve shortfall
falsifier cannot coexist. -/
theorem no_low_high_catalyst_reserve_shortfall_with_leakage_absorption
    (H : LowHighCatalystLeakageBridge)
    (F : LowHighCatalystReserveShortfallFalsifier H) :
    False := by
  have hleak : ZtareProofs.lowHighLeakageControlled H.budget :=
    ZtareProofs.low_high_leakage_controlled_of_absorption
      H.budget H.leakage H.leakage_represents H.leakage_absorbing
  unfold ZtareProofs.lowHighLeakageControlled at hleak
  exact not_lt_of_ge hleak F.declared_catalyst_gain_exceeds_reserve

/-- A closed positive low-high catalyst class and a finite underpriced member
cannot coexist. -/
theorem no_low_high_negative_member_of_closed_positive
    (P : ClosedLowHighCatalystPositive)
    (N : ClosedLowHighCatalystNegative)
    (hN : P.Class N.interaction) :
    False := by
  have hnoarb : InteractionNoArbitrage N.interaction :=
    low_high_class_no_arbitrage_of_closed_positive P N.interaction hN
  unfold InteractionNoArbitrage at hnoarb
  exact not_lt_of_ge hnoarb N.arbitrage

end ZtareProofs.NS
