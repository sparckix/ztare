import Mathlib.Tactic
import ZtareProofs.ns_littlewood_paley_paraproduct_bridge
import ZtareProofs.ns_continuum_tail_bound

/-!
# High-low transport charging obligation

This is the companion to `ns_low_high_catalyst_charging_obligation.lean`.
The low-high branch asks whether a low-frequency catalyst stretches high modes
for free.  The high-low branch asks whether high-frequency transport against
low-frequency structure escapes the declared price.

The adapter is deliberately the same leakage-reserve shape: if the high-low
interaction is represented by a predeclared leakage gain/loss budget and the
leakage is absorbed by reserve loss, then the interaction is priced.
-/

namespace ZtareProofs.NS

/-- A high-low transport interaction represented by the continuum tail/leakage
budget. -/
structure HighLowTransportLeakageBridge where
  interaction : LPInteractionLedger
  budget : ZtareProofs.CoreTailBudget
  leakage : ZtareProofs.LeakageAbsorptionEstimate
  is_high_low : interaction.interactionClass = LPParaproductClass.highLow
  leakage_represents : leakage.represents budget
  leakage_absorbing : leakage.absorbing
  payoff_eq_leakage_gain : interaction.payoff = budget.leakageGain
  price_eq_leakage_loss : interaction.price = budget.leakageLoss

/-- Leakage absorption prices a declared high-low transport interaction. -/
theorem high_low_interaction_no_arbitrage_of_leakage_absorption
    (H : HighLowTransportLeakageBridge) :
    InteractionNoArbitrage H.interaction := by
  have hleak : ZtareProofs.lowHighLeakageControlled H.budget :=
    ZtareProofs.low_high_leakage_controlled_of_absorption
      H.budget H.leakage H.leakage_represents H.leakage_absorbing
  unfold InteractionNoArbitrage
  unfold ZtareProofs.lowHighLeakageControlled at hleak
  rw [H.payoff_eq_leakage_gain, H.price_eq_leakage_loss]
  exact hleak

/-- Finite falsifier for an underpriced high-low transport reserve.

This is the hostile shape the bridge must exclude: the same predeclared
high-low leakage budget cannot both be absorbed by reserve loss and declare
more transport gain than reserve/loss price. -/
structure HighLowTransportReserveShortfallFalsifier
    (H : HighLowTransportLeakageBridge) where
  declared_transport_gain_exceeds_reserve :
    H.budget.leakageLoss < H.budget.leakageGain

/-- A leakage-absorption high-low bridge and a same-budget reserve shortfall
falsifier cannot coexist. -/
theorem no_high_low_transport_reserve_shortfall_with_leakage_absorption
    (H : HighLowTransportLeakageBridge)
    (F : HighLowTransportReserveShortfallFalsifier H) :
    False := by
  have hleak : ZtareProofs.lowHighLeakageControlled H.budget :=
    ZtareProofs.low_high_leakage_controlled_of_absorption
      H.budget H.leakage H.leakage_represents H.leakage_absorbing
  unfold ZtareProofs.lowHighLeakageControlled at hleak
  exact not_lt_of_ge hleak F.declared_transport_gain_exceeds_reserve

/-- Positive branch payload for high-low transport charging. -/
structure ClosedHighLowTransportPositive where
  Class : LPInteractionLedger → Prop
  bridge_of_class :
    ∀ T : LPInteractionLedger,
      Class T →
        ∃ H : HighLowTransportLeakageBridge, H.interaction = T

/-- Negative branch payload: a concrete high-low interaction whose payoff
strictly exceeds price. -/
structure ClosedHighLowTransportNegative where
  interaction : LPInteractionLedger
  is_high_low : interaction.interactionClass = LPParaproductClass.highLow
  arbitrage : interaction.price < interaction.payoff

/-- If a class has a leakage-absorption bridge, every member is priced. -/
theorem high_low_class_no_arbitrage_of_closed_positive
    (P : ClosedHighLowTransportPositive)
    (T : LPInteractionLedger)
    (hT : P.Class T) :
    InteractionNoArbitrage T := by
  obtain ⟨H, hHT⟩ := P.bridge_of_class T hT
  rw [← hHT]
  exact high_low_interaction_no_arbitrage_of_leakage_absorption H

/-- A closed positive high-low class and a finite underpriced member cannot
coexist. -/
theorem no_high_low_negative_member_of_closed_positive
    (P : ClosedHighLowTransportPositive)
    (N : ClosedHighLowTransportNegative)
    (hN : P.Class N.interaction) :
    False := by
  have hnoarb : InteractionNoArbitrage N.interaction :=
    high_low_class_no_arbitrage_of_closed_positive P N.interaction hN
  unfold InteractionNoArbitrage at hnoarb
  exact not_lt_of_ge hnoarb N.arbitrage

end ZtareProofs.NS
