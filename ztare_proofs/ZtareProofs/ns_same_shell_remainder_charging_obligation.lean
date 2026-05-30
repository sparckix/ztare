import Mathlib.Tactic
import ZtareProofs.ns_littlewood_paley_paraproduct_bridge
import ZtareProofs.ns_pricing_kernel_limit_passage

/-!
# Same-shell and remainder charging obligation

The low-high, high-low, and high-high paraproduct branches now have explicit
adapters.  This file isolates the remaining LP/Bony bookkeeping branch:
same-shell and remainder interactions.

The point is not to assume those terms are harmless.  The adapter below states
the exact charging route: a same-shell/remainder interaction may be priced by a
fixed profile-family or residual ledger only when its payoff is bounded by the
declared family payoff and the declared family price is itself dominated by the
interaction's price.  That prevents the tautology where remainder terms are
hidden after the profitable route is seen.
-/

namespace ZtareProofs.NS

/-- A paraproduct class is in the same-shell/remainder branch. -/
def IsSameShellRemainderClass (c : LPParaproductClass) : Prop :=
  c = LPParaproductClass.sameShell ∨ c = LPParaproductClass.remainder

/-- A same-shell/remainder interaction charged through a fixed profile-family
ledger.  The concrete PDE proof must define `family` from the LP/Bony
decomposition before scoring the interaction payoff. -/
structure SameShellRemainderProfileBridge where
  interaction : LPInteractionLedger
  family : PricingProfileFamily
  class_is_same_shell_or_remainder :
    IsSameShellRemainderClass interaction.interactionClass
  payoff_le_family_payoff :
    interaction.payoff ≤ familyPayoff family
  family_price_le_interaction_price :
    familyPrice family ≤ interaction.price

/-- Profile-family no-arbitrage prices a declared same-shell/remainder
interaction when the profile-family ledger is fixed and charged. -/
theorem same_shell_remainder_priced_of_profile_family_no_arbitrage
    (B : SameShellRemainderProfileBridge)
    (hfamily : familyPayoff B.family ≤ familyPrice B.family) :
    InteractionNoArbitrage B.interaction := by
  unfold InteractionNoArbitrage
  exact B.payoff_le_family_payoff.trans
    (hfamily.trans B.family_price_le_interaction_price)

/-- Positive branch payload: same-shell/remainder terms are priced by a fixed
profile-family certificate. -/
structure ClosedSameShellRemainderPositive where
  bridge_of_interaction :
    ∀ T : LPInteractionLedger,
      IsSameShellRemainderClass T.interactionClass →
        SameShellRemainderProfileBridge
  bridge_matches :
    ∀ (T : LPInteractionLedger)
      (hclass : IsSameShellRemainderClass T.interactionClass),
        (bridge_of_interaction T hclass).interaction = T
  family_no_arbitrage :
    ∀ (T : LPInteractionLedger)
      (hclass : IsSameShellRemainderClass T.interactionClass),
        familyPayoff (bridge_of_interaction T hclass).family ≤
          familyPrice (bridge_of_interaction T hclass).family

/-- Negative branch payload: a fixed same-shell/remainder profile family fails
to price the declared interaction. -/
structure ClosedSameShellRemainderNegative where
  bridge : SameShellRemainderProfileBridge
  family_priced : familyPayoff bridge.family ≤ familyPrice bridge.family
  payoff_escapes_price : bridge.interaction.price < bridge.interaction.payoff

/-- If every same-shell/remainder interaction has a fixed priced
profile-family bridge, then the interaction class is no-arbitrage. -/
theorem same_shell_remainder_class_no_arbitrage_of_closed_positive
    (H : ClosedSameShellRemainderPositive)
    (T : LPInteractionLedger)
    (hclass : IsSameShellRemainderClass T.interactionClass) :
    InteractionNoArbitrage T := by
  have hpriced :
      InteractionNoArbitrage (H.bridge_of_interaction T hclass).interaction :=
    same_shell_remainder_priced_of_profile_family_no_arbitrage
      (H.bridge_of_interaction T hclass)
      (H.family_no_arbitrage T hclass)
  rw [H.bridge_matches T hclass] at hpriced
  exact hpriced

/-- Pointwise residual charge witness for same-shell/remainder and cross
residual terms.

This is the GP-215 "Residual Charge Witness Construction" shape.  It charges a
declared interaction before any countable limit by giving a fixed nonnegative
selector and residual norm whose product bounds payoff and is itself charged
by the interaction price. -/
structure ResidualChargeWitness where
  interaction : LPInteractionLedger
  class_is_same_shell_or_remainder :
    IsSameShellRemainderClass interaction.interactionClass
  residualNorm : Real
  priceSelector : Real
  selector_declared_before_payoff : Prop
  residual_norm_nonnegative : 0 ≤ residualNorm
  selector_nonnegative : 0 ≤ priceSelector
  payoff_le_selector_times_norm :
    interaction.payoff ≤ priceSelector * residualNorm
  selector_times_norm_charged_by_price :
    priceSelector * residualNorm ≤ interaction.price

/-- A pointwise residual charge witness prices the declared interaction before
any profile/LP limit is taken. -/
theorem same_shell_remainder_priced_of_residual_charge_witness
    (W : ResidualChargeWitness) :
    InteractionNoArbitrage W.interaction := by
  unfold InteractionNoArbitrage
  exact W.payoff_le_selector_times_norm.trans
    W.selector_times_norm_charged_by_price

/-- The exact falsifier shape for residual charging: positive payoff survives
while the pre-limit residual selector price is short. -/
structure ResidualChargeFalsifier where
  witness_data : ResidualChargeWitness
  positive_payoff : 0 < witness_data.interaction.payoff
  price_shortfall :
    witness_data.interaction.price < witness_data.interaction.payoff

/-- A residual charge witness and a same-data residual falsifier cannot coexist. -/
theorem no_residual_falsifier_with_charge_witness
    (F : ResidualChargeFalsifier) :
    False := by
  have hpriced :
      InteractionNoArbitrage F.witness_data.interaction :=
    same_shell_remainder_priced_of_residual_charge_witness F.witness_data
  unfold InteractionNoArbitrage at hpriced
  exact not_lt_of_ge hpriced F.price_shortfall

/-- Anti-tautology checklist for the same-shell/remainder branch. -/
structure SameShellRemainderPDEObligation where
  lp_bony_remainder_split_fixed : Prop
  profile_family_declared_before_payoff : Prop
  same_shell_payoff_represented_in_family : Prop
  remainder_payoff_represented_in_family : Prop
  family_price_charged_before_limit : Prop
  no_profitable_term_hidden_as_residual : Prop

end ZtareProofs.NS
