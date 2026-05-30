import Mathlib.Tactic
import ZtareProofs.ns_littlewood_paley_paraproduct_bridge

/-!
# High-high self-tax charging obligation

The high-high paraproduct branch is the "cascade payoff survives while
self-tax cancels" attacker.  The finite audits showed that mixed-only gain can
look profitable, but exact full-ledger scoring with high-high self-tax collapses
the route.

This file does not prove the PDE theorem.  It proves the adapter from the
existing Track B exact quartic/no-survivor statement to a priced high-high
paraproduct interaction.
-/

namespace ZtareProofs.NS

/-- A high-high interaction represented by a Track B full-ledger block.

The interaction payoff is the block survival profit and the interaction price
is the sharp `2/3` wall.  The equalities must be declared before scoring the
route. -/
structure HighHighSelfTaxBridge where
  interaction : LPInteractionLedger
  block : FullLedgerBlock
  is_high_high : interaction.interactionClass = LPParaproductClass.highHigh
  payoff_eq_survival_profit : interaction.payoff = block.survivalProfit
  price_eq_sharp_target : interaction.price = sharpTarget
  threshold_defect : ThresholdDefectConvexity block

/-- Exact quartic no-survivor pricing charges a declared high-high interaction. -/
theorem high_high_interaction_no_arbitrage_of_quartic_no_survivor
    (quartic_no_survivor :
      ∀ B : FullLedgerBlock, ThresholdDefectConvexity B → FullLedgerNoSurvivor B)
    (H : HighHighSelfTaxBridge) :
    InteractionNoArbitrage H.interaction := by
  have hno : FullLedgerNoSurvivor H.block :=
    quartic_no_survivor H.block H.threshold_defect
  unfold InteractionNoArbitrage
  unfold FullLedgerNoSurvivor at hno
  rw [H.payoff_eq_survival_profit, H.price_eq_sharp_target]
  exact hno

/-- Projection-typed high-high charging theorem.

Closure-facing payloads should prefer this form so the survival payoff remains
tied to the same root-defect ledger used to exclude the route. -/
theorem high_high_interaction_no_arbitrage_of_survival_projection
    (H : HighHighSelfTaxBridge)
    (hprojection : QuarticSurvivalProjectionReceipt H.block) :
    InteractionNoArbitrage H.interaction := by
  have hno : FullLedgerNoSurvivor H.block :=
    full_ledger_no_survivor_of_quartic_survival_projection H.block
      hprojection
      H.threshold_defect
  unfold InteractionNoArbitrage
  unfold FullLedgerNoSurvivor at hno
  rw [H.payoff_eq_survival_profit, H.price_eq_sharp_target]
  exact hno

/-- Positive branch payload for high-high self-tax charging. -/
structure ClosedHighHighSelfTaxPositive where
  Class : LPInteractionLedger → Prop
  bridge_of_class :
    ∀ T : LPInteractionLedger,
      Class T →
        ∃ H : HighHighSelfTaxBridge, H.interaction = T
  quartic_survival_projection :
    ∀ H : HighHighSelfTaxBridge,
      Class H.interaction →
        QuarticSurvivalProjectionReceipt H.block

/-- Negative branch payload: a declared high-high interaction above its price. -/
structure ClosedHighHighSelfTaxNegative where
  interaction : LPInteractionLedger
  is_high_high : interaction.interactionClass = LPParaproductClass.highHigh
  arbitrage : interaction.price < interaction.payoff

/-- Scalar falsifier gate for the self-tax-free high-high attacker.

At a threshold amplitude `0 < x` with `x^2 < 1`, a branch with zero self-tax
and nonpositive cross term cannot make the normalized defect reach one.  Thus a
high-high "self-tax cancels" route must still pay for a favorable positive
cross term; zero self-tax alone is not a survivor geometry. -/
theorem self_tax_free_nonpositive_cross_cannot_reach_threshold
    {x cross : Real}
    (hx : 0 < x)
    (hx2 : x ^ (2 : Nat) < 1)
    (hcross : cross ≤ 0) :
    ¬ 1 ≤ x ^ (2 : Nat) + 2 * cross * x ^ (3 : Nat) := by
  intro hdefect
  have hx3_nonneg : 0 ≤ x ^ (3 : Nat) := pow_nonneg (le_of_lt hx) 3
  have hcross_term_nonpos : 2 * cross * x ^ (3 : Nat) ≤ 0 := by
    nlinarith [hcross, hx3_nonneg]
  nlinarith

/-- Root-level version of the high-high falsifier gate.

For an above-wall block, the threshold amplitude has `x^2 < 1`.  Therefore, if
the high-high self-tax is zero, reaching the threshold defect forces the cross
term to be strictly positive.  This is the exact algebraic burden a
self-tax-cancellation attacker must now pay. -/
theorem self_tax_free_above_wall_threshold_requires_positive_cross
    (B : FullLedgerBlock)
    (hgamma : 0 < B.gamma)
    (hgt : sharpTarget < B.gamma)
    (hself : B.selfTax = 0)
    (hdefect :
      1 ≤ survivalDefect B (Real.sqrt (sharpTarget / B.gamma))) :
    0 < B.cross := by
  by_contra hnot
  have hcross : B.cross ≤ 0 := le_of_not_gt hnot
  let x : Real := Real.sqrt (sharpTarget / B.gamma)
  have htarget_pos : 0 < sharpTarget := by
    norm_num [sharpTarget]
  have hratio_pos : 0 < sharpTarget / B.gamma :=
    div_pos htarget_pos hgamma
  have hx : 0 < x := by
    dsimp [x]
    exact Real.sqrt_pos.2 hratio_pos
  have hratio_lt_one : sharpTarget / B.gamma < 1 := by
    exact (div_lt_one hgamma).2 hgt
  have hx_sq :
      x ^ (2 : Nat) = sharpTarget / B.gamma := by
    dsimp [x]
    exact Real.sq_sqrt (le_of_lt hratio_pos)
  have hx2 : x ^ (2 : Nat) < 1 := by
    rw [hx_sq]
    exact hratio_lt_one
  have hdefect_x :
      1 ≤ x ^ (2 : Nat) + 2 * B.cross * x ^ (3 : Nat) := by
    have hraw :
        1 ≤ x ^ (2 : Nat) + 2 * B.cross * x ^ (3 : Nat) +
          B.selfTax * x ^ (4 : Nat) := by
      simpa [x, survivalDefect] using hdefect
    rw [hself] at hraw
    simpa using hraw
  exact self_tax_free_nonpositive_cross_cannot_reach_threshold
    hx hx2 hcross hdefect_x

/-- Cauchy semantics of the normalized same-ledger block: if
`cross = <M,S>` and `selfTax = ||S||^2` with `||M||^2 = 1`, then
`cross^2 <= selfTax`.  Under that semantic bound, exact zero self-tax forces
zero cross. -/
theorem cross_zero_of_self_tax_zero_and_cauchy
    (B : FullLedgerBlock)
    (hcauchy : B.cross ^ (2 : Nat) ≤ B.selfTax)
    (hself : B.selfTax = 0) :
    B.cross = 0 := by
  have hsq_nonneg : 0 ≤ B.cross ^ (2 : Nat) := sq_nonneg B.cross
  have hsq_zero : B.cross ^ (2 : Nat) = 0 := by
    nlinarith
  nlinarith

/-- Anti-tautology guard: Cauchy/same-ledger semantics alone do not prove the
interacting root-coercivity branch.  This scalar ledger saturates
`cross^2 <= selfTax`, has positive self-tax and above-wall mixed gain, but its
defect at the threshold root is zero.  A real PDE proof must therefore supply
the stronger cross-aware allowance / PSD receipt, not merely Cauchy. -/
noncomputable def cauchySaturatingBadLedger : FullLedgerBlock where
  scope := LedgerScope.globalAdmissibleField
  gamma := (8 : Real) / 3
  cross := -2
  selfTax := 4
  survivalProfit := 1

theorem cauchy_saturating_bad_ledger_above_wall :
    sharpTarget < cauchySaturatingBadLedger.gamma := by
  norm_num [cauchySaturatingBadLedger, sharpTarget]

theorem cauchy_saturating_bad_ledger_positive_self_tax :
    0 < cauchySaturatingBadLedger.selfTax := by
  norm_num [cauchySaturatingBadLedger]

theorem cauchy_saturating_bad_ledger_obeys_cauchy :
    cauchySaturatingBadLedger.cross ^ (2 : Nat) ≤
      cauchySaturatingBadLedger.selfTax := by
  norm_num [cauchySaturatingBadLedger]

theorem cauchy_saturating_bad_ledger_root_is_half :
    Real.sqrt (sharpTarget / cauchySaturatingBadLedger.gamma) =
      (1 : Real) / 2 := by
  have hratio :
      sharpTarget / cauchySaturatingBadLedger.gamma =
        ((1 : Real) / 2) ^ (2 : Nat) := by
    norm_num [cauchySaturatingBadLedger, sharpTarget]
  rw [hratio]
  rw [Real.sqrt_sq_eq_abs]
  norm_num

theorem cauchy_saturating_bad_ledger_root_defect_zero :
    survivalDefect cauchySaturatingBadLedger
        (Real.sqrt (sharpTarget / cauchySaturatingBadLedger.gamma)) =
      0 := by
  rw [cauchy_saturating_bad_ledger_root_is_half]
  norm_num [survivalDefect, cauchySaturatingBadLedger]

/-- Concrete quartic-bound witness for the high-high branch.

This is the GP-215 "Quartic Bound Witness" shape: a specific ledger tuple that
turns a proposed inequality into ground arithmetic.  Here the witness is
negative: it proves Cauchy semantics plus positive self-tax do **not** suffice
for Track B root coercivity. -/
structure HighHighQuarticBoundWitness where
  block : FullLedgerBlock
  above_wall : sharpTarget < block.gamma
  positive_self_tax : 0 < block.selfTax
  cauchy_semantics : block.cross ^ (2 : Nat) ≤ block.selfTax
  threshold_root_defect_below_one :
    survivalDefect block (Real.sqrt (sharpTarget / block.gamma)) < 1

/-- The Cauchy-saturating bad ledger is a closed arithmetic witness that the
high-high theorem needs a stronger PSD/cross-aware receipt than Cauchy. -/
noncomputable def cauchySaturatingBadQuarticBoundWitness :
    HighHighQuarticBoundWitness where
  block := cauchySaturatingBadLedger
  above_wall := cauchy_saturating_bad_ledger_above_wall
  positive_self_tax := cauchy_saturating_bad_ledger_positive_self_tax
  cauchy_semantics := cauchy_saturating_bad_ledger_obeys_cauchy
  threshold_root_defect_below_one := by
    rw [cauchy_saturating_bad_ledger_root_defect_zero]
    norm_num

/-- Cauchy semantics alone cannot imply Track B threshold-defect convexity. -/
theorem cauchy_semantics_not_sufficient_for_threshold_defect :
    ∃ B : FullLedgerBlock,
      sharpTarget < B.gamma ∧
        0 < B.selfTax ∧
          B.cross ^ (2 : Nat) ≤ B.selfTax ∧
            ¬ ThresholdDefectConvexity B := by
  refine ⟨cauchySaturatingBadLedger, ?_⟩
  refine ⟨cauchy_saturating_bad_ledger_above_wall,
    cauchy_saturating_bad_ledger_positive_self_tax,
    cauchy_saturating_bad_ledger_obeys_cauchy, ?_⟩
  intro h
  rcases h with hbelow | habove
  · exact not_lt_of_ge hbelow cauchy_saturating_bad_ledger_above_wall
  · rcases habove with ⟨_hgt, hdefect⟩
    rw [cauchy_saturating_bad_ledger_root_defect_zero] at hdefect
    norm_num at hdefect

/-- Wall-saturating resonant ledger.

Phase 5GL found finite resonant-overlap pair rows with normalized
`cross = -2`, `selfTax = 4`, and `gamma = 2/3`.  This is the physical analogue
of the Cauchy-saturating anti-alignment branch, but it sits exactly on the
Track B wall instead of above it. -/
noncomputable def cauchySaturatingWallLedger : FullLedgerBlock where
  scope := LedgerScope.globalAdmissibleField
  gamma := sharpTarget
  cross := -2
  selfTax := 4
  survivalProfit := sharpTarget

theorem cauchy_saturating_wall_ledger_at_wall :
    cauchySaturatingWallLedger.gamma = sharpTarget := by
  rfl

theorem cauchy_saturating_wall_ledger_not_above_wall :
    ¬ sharpTarget < cauchySaturatingWallLedger.gamma := by
  rw [cauchy_saturating_wall_ledger_at_wall]
  exact not_lt.mpr le_rfl

/-- The wall-saturating ledger is strictly below the above-wall bad ledger in
the gain coordinate.

This is the typed form of the constraint-graph transitivity candidate:
`cauchySaturatingWallLedger.gamma = sharpTarget <
cauchySaturatingBadLedger.gamma`.  It keeps the resonant-wall boundary witness
separate from the genuinely above-wall Cauchy-saturating obstruction. -/
theorem cauchy_saturating_wall_gamma_lt_bad_gamma :
    cauchySaturatingWallLedger.gamma <
      cauchySaturatingBadLedger.gamma := by
  rw [cauchy_saturating_wall_ledger_at_wall]
  exact cauchy_saturating_bad_ledger_above_wall

theorem cauchy_saturating_wall_ledger_obeys_cauchy :
    cauchySaturatingWallLedger.cross ^ (2 : Nat) ≤
      cauchySaturatingWallLedger.selfTax := by
  norm_num [cauchySaturatingWallLedger]

theorem cauchy_saturating_wall_ledger_root_is_one :
    Real.sqrt (sharpTarget / cauchySaturatingWallLedger.gamma) =
      (1 : Real) := by
  have hratio :
      sharpTarget / cauchySaturatingWallLedger.gamma = (1 : Real) := by
    norm_num [cauchySaturatingWallLedger, sharpTarget]
  rw [hratio]
  norm_num

theorem cauchy_saturating_wall_ledger_root_defect_one :
    survivalDefect cauchySaturatingWallLedger
        (Real.sqrt (sharpTarget / cauchySaturatingWallLedger.gamma)) =
      1 := by
  rw [cauchy_saturating_wall_ledger_root_is_one]
  norm_num [survivalDefect, cauchySaturatingWallLedger]

/-- Same-ledger consequence: an above-wall threshold-root defect cannot be
reached by a self-tax-free high-high block once the cross term obeys the
Hilbert/Cauchy ledger semantics.  Equivalently, any above-wall threshold-root
high-high route must have strictly positive self-tax. -/
theorem above_wall_threshold_requires_positive_self_tax_of_cauchy
    (B : FullLedgerBlock)
    (hgamma : 0 < B.gamma)
    (hgt : sharpTarget < B.gamma)
    (hself_nonneg : 0 ≤ B.selfTax)
    (hcauchy : B.cross ^ (2 : Nat) ≤ B.selfTax)
    (hdefect :
      1 ≤ survivalDefect B (Real.sqrt (sharpTarget / B.gamma))) :
    0 < B.selfTax := by
  by_contra hnot
  have hself : B.selfTax = 0 := le_antisymm (le_of_not_gt hnot) hself_nonneg
  have hcross_pos : 0 < B.cross :=
    self_tax_free_above_wall_threshold_requires_positive_cross
      B hgamma hgt hself hdefect
  have hcross_zero : B.cross = 0 :=
    cross_zero_of_self_tax_zero_and_cauchy B hcauchy hself
  linarith

/-- Exact cross-aware allowance used by the saved-artifact root-margin miner.

If a positive threshold amplitude has already paid
`(1 - x^2 - 2 * cross * x^3) / x^4`, then the full quartic defect is at least
one.  This is the algebraic receipt behind the Phase 5GI root-margin audit. -/
theorem threshold_defect_of_cross_aware_tax_allowance
    (B : FullLedgerBlock)
    {x : Real}
    (hx4 : 0 < x ^ (4 : Nat))
    (hallow :
      (1 - x ^ (2 : Nat) - 2 * B.cross * x ^ (3 : Nat)) /
          x ^ (4 : Nat) ≤ B.selfTax) :
    1 ≤ survivalDefect B x := by
  have hx4_ne : x ^ (4 : Nat) ≠ 0 := ne_of_gt hx4
  have hmul :
      ((1 - x ^ (2 : Nat) - 2 * B.cross * x ^ (3 : Nat)) /
            x ^ (4 : Nat)) *
          x ^ (4 : Nat) ≤
        B.selfTax * x ^ (4 : Nat) :=
    mul_le_mul_of_nonneg_right hallow (le_of_lt hx4)
  have hcancel :
      ((1 - x ^ (2 : Nat) - 2 * B.cross * x ^ (3 : Nat)) /
            x ^ (4 : Nat)) *
          x ^ (4 : Nat) =
        1 - x ^ (2 : Nat) - 2 * B.cross * x ^ (3 : Nat) := by
    exact div_mul_cancel₀ _ hx4_ne
  rw [hcancel] at hmul
  unfold survivalDefect
  nlinarith

/-- Root-level version of the Phase 5GI receipt: for an above-wall block, paying
the exact cross-aware allowance at the Track B threshold root implies
threshold-defect convexity. -/
theorem threshold_defect_convexity_of_cross_aware_root_allowance
    (B : FullLedgerBlock)
    (hgamma : 0 < B.gamma)
    (hgt : sharpTarget < B.gamma)
    (hallow :
      let x : Real := Real.sqrt (sharpTarget / B.gamma)
      (1 - x ^ (2 : Nat) - 2 * B.cross * x ^ (3 : Nat)) /
          x ^ (4 : Nat) ≤ B.selfTax) :
    ThresholdDefectConvexity B := by
  refine Or.inr ⟨hgt, ?_⟩
  let x : Real := Real.sqrt (sharpTarget / B.gamma)
  have htarget_pos : 0 < sharpTarget := by
    norm_num [sharpTarget]
  have hratio_pos : 0 < sharpTarget / B.gamma :=
    div_pos htarget_pos hgamma
  have hx : 0 < x := by
    dsimp [x]
    exact Real.sqrt_pos.2 hratio_pos
  have hx4 : 0 < x ^ (4 : Nat) := pow_pos hx 4
  exact threshold_defect_of_cross_aware_tax_allowance B hx4 hallow

/-- Nonresonant specialization of the cross-aware receipt.

When the mixed/self support partition has already forced the cross term to
zero, the above-wall branch only has to pay the exact root self-tax floor
`(1 - x^2) / x^4`.  This is not a PDE estimate by itself; it is the algebraic
adapter that lets a fixed topology estimate enter the Track B quartic ledger. -/
theorem threshold_defect_convexity_of_cross_zero_root_floor
    (B : FullLedgerBlock)
    (hgamma : 0 < B.gamma)
    (hgt : sharpTarget < B.gamma)
    (hcross : B.cross = 0)
    (hfloor :
      let x : Real := Real.sqrt (sharpTarget / B.gamma)
      (1 - x ^ (2 : Nat)) / x ^ (4 : Nat) ≤ B.selfTax) :
    ThresholdDefectConvexity B := by
  exact threshold_defect_convexity_of_cross_aware_root_allowance
    B hgamma hgt (by
      dsimp
      rw [hcross]
      simpa using hfloor)

/-- Quadratic anti-alignment receipt.

The scalar bad ledger shows that Cauchy is too weak because `cross` can be
almost perfectly anti-aligned with self-tax.  A useful PDE receipt must instead
combine a lower bound on that anti-alignment with enough scaled self-tax `y`.
This theorem is the exact algebraic adapter: if the scaled self-tax and cross
terms dominate the quadratic burden `1 - x^2`, then the threshold defect is
paid. -/
theorem threshold_defect_of_quadratic_anti_alignment_receipt
    (B : FullLedgerBlock)
    {x rho y : Real}
    (hquad : 1 - x ^ (2 : Nat) ≤ y ^ (2 : Nat) - 2 * rho * x * y)
    (hself : y ^ (2 : Nat) ≤ B.selfTax * x ^ (4 : Nat))
    (hcross : -rho * x * y ≤ B.cross * x ^ (3 : Nat)) :
    1 ≤ survivalDefect B x := by
  unfold survivalDefect
  nlinarith

/-- Root-level anti-alignment receipt for the positive self-tax branch.

This is the proof-facing shape suggested by Phase 5GJ: exclude strong
mixed/self anti-alignment and prove a scaled self-tax floor at the Track B root.
Those two PDE estimates imply threshold-defect convexity without choosing any
quantity after observing the payoff. -/
theorem threshold_defect_convexity_of_quadratic_anti_alignment_receipt
    (B : FullLedgerBlock)
    (hgt : sharpTarget < B.gamma)
    {rho y : Real}
    (hquad :
      let x : Real := Real.sqrt (sharpTarget / B.gamma)
      1 - x ^ (2 : Nat) ≤ y ^ (2 : Nat) - 2 * rho * x * y)
    (hself :
      let x : Real := Real.sqrt (sharpTarget / B.gamma)
      y ^ (2 : Nat) ≤ B.selfTax * x ^ (4 : Nat))
    (hcross :
      let x : Real := Real.sqrt (sharpTarget / B.gamma)
      (-rho * x * y) ≤ B.cross * x ^ (3 : Nat)) :
    ThresholdDefectConvexity B := by
  refine Or.inr ⟨hgt, ?_⟩
  let x : Real := Real.sqrt (sharpTarget / B.gamma)
  exact threshold_defect_of_quadratic_anti_alignment_receipt
    B hquad hself hcross

/-- Remaining PDE/receipt obligation for high-high self-tax charging.

This does not prove the LP/Bony/Leray estimate.  It names the duties required
before the algebraic high-high threshold-defect adapters may be used globally:
fixed high-high topology, same-output Leray ledger, self-tax positivity/null
route cap, a real cross-aware/SOS receipt, and profile-limit stability. -/
structure HighHighSelfTaxPDEObligation where
  fixed_high_high_lp_bony_topology : Prop
  same_leray_output_ledger_declared_before_payoff : Prop
  self_tax_nonnegative_for_global_high_high_blocks : Prop
  null_self_tax_above_wall_cap_proved : Prop
  cross_aware_root_allowance_or_sos_receipt_proved : Prop
  cauchy_saturating_bad_ledger_falsifier_addressed : Prop
  cauchy_saturating_bad_ledger_falsifier_surface :
    survivalDefect cauchySaturatingBadLedger
      (Real.sqrt (sharpTarget / cauchySaturatingBadLedger.gamma)) < 1
  resonant_wall_case_not_promoted_above_wall : Prop
  resonant_wall_case_boundary_surface :
    ¬ sharpTarget < cauchySaturatingWallLedger.gamma
  smooth_profile_limit_preserves_high_high_receipt : Prop
  no_posthoc_phase_shell_or_observable_choice : Prop

/-- Satisfaction predicate for the high-high self-tax PDE obligation.

GP216 should carry this predicate exactly like the event-recurrence and
low-high reserve predicates: it makes the high-high duties load-bearing
without pretending this file proves the PDE estimate. -/
def HighHighSelfTaxPDEObligationSatisfied
    (O : HighHighSelfTaxPDEObligation) : Prop :=
  O.fixed_high_high_lp_bony_topology ∧
    O.same_leray_output_ledger_declared_before_payoff ∧
      O.self_tax_nonnegative_for_global_high_high_blocks ∧
        O.null_self_tax_above_wall_cap_proved ∧
          O.cross_aware_root_allowance_or_sos_receipt_proved ∧
            O.cauchy_saturating_bad_ledger_falsifier_addressed ∧
              survivalDefect cauchySaturatingBadLedger
                  (Real.sqrt (sharpTarget / cauchySaturatingBadLedger.gamma)) < 1 ∧
                O.resonant_wall_case_not_promoted_above_wall ∧
                  ¬ sharpTarget < cauchySaturatingWallLedger.gamma ∧
                    O.smooth_profile_limit_preserves_high_high_receipt ∧
                      O.no_posthoc_phase_shell_or_observable_choice

/-- Closed arithmetic receipt for the Cauchy-saturating above-wall witness
surface carried by `HighHighSelfTaxPDEObligation`.

This theorem keeps the field load-bearing without asking future PDE
instantiations to re-prove the scalar arithmetic. -/
theorem cauchy_saturating_bad_ledger_falsifier_surface_paid :
    survivalDefect cauchySaturatingBadLedger
        (Real.sqrt (sharpTarget / cauchySaturatingBadLedger.gamma)) < 1 := by
  rw [cauchy_saturating_bad_ledger_root_defect_zero]
  norm_num

/-- Closed arithmetic receipt for the resonant wall boundary surface carried
by `HighHighSelfTaxPDEObligation`. -/
theorem resonant_wall_case_boundary_surface_paid :
    ¬ sharpTarget < cauchySaturatingWallLedger.gamma :=
  cauchy_saturating_wall_ledger_not_above_wall

/-- Partial high-high PDE satisfaction constructor that fills the two closed
arithmetic witness surfaces from proved scalar lemmas.

The remaining arguments are the genuine PDE/LP/Bony duties; this constructor
only prevents the already-closed arithmetic boundary checks from appearing as
open analytic work. -/
theorem high_high_self_tax_pde_obligation_satisfied_of_pde_duties
    (O : HighHighSelfTaxPDEObligation)
    (hfixed : O.fixed_high_high_lp_bony_topology)
    (hsame : O.same_leray_output_ledger_declared_before_payoff)
    (hnonneg : O.self_tax_nonnegative_for_global_high_high_blocks)
    (hnull : O.null_self_tax_above_wall_cap_proved)
    (hcross : O.cross_aware_root_allowance_or_sos_receipt_proved)
    (hbad : O.cauchy_saturating_bad_ledger_falsifier_addressed)
    (hwall : O.resonant_wall_case_not_promoted_above_wall)
    (hlimit : O.smooth_profile_limit_preserves_high_high_receipt)
    (hposthoc : O.no_posthoc_phase_shell_or_observable_choice) :
    HighHighSelfTaxPDEObligationSatisfied O :=
  ⟨hfixed, hsame, hnonneg, hnull, hcross, hbad,
    O.cauchy_saturating_bad_ledger_falsifier_surface,
    hwall, O.resonant_wall_case_boundary_surface, hlimit, hposthoc⟩

/-- Named ways the high-high self-tax PDE obligation can fail.

This is the high-high analogue of the event-recurrence and low-high reserve
falsifier surfaces: a final bridge should not consume a black-box failure of
`HighHighSelfTaxPDEObligationSatisfied` without identifying which analytic duty
was missing. -/
inductive HighHighSelfTaxPDEObligationFalsifier
    (O : HighHighSelfTaxPDEObligation) : Type where
  | topologyNotFixed :
      ¬ O.fixed_high_high_lp_bony_topology →
        HighHighSelfTaxPDEObligationFalsifier O
  | ledgerNotSameOutput :
      ¬ O.same_leray_output_ledger_declared_before_payoff →
        HighHighSelfTaxPDEObligationFalsifier O
  | selfTaxNonnegativeMissing :
      ¬ O.self_tax_nonnegative_for_global_high_high_blocks →
        HighHighSelfTaxPDEObligationFalsifier O
  | nullSelfTaxCapMissing :
      ¬ O.null_self_tax_above_wall_cap_proved →
        HighHighSelfTaxPDEObligationFalsifier O
  | crossAwareOrSOSReceiptMissing :
      ¬ O.cross_aware_root_allowance_or_sos_receipt_proved →
        HighHighSelfTaxPDEObligationFalsifier O
  | cauchySaturatingSurfaceUnaddressed :
      ¬ O.cauchy_saturating_bad_ledger_falsifier_addressed →
        HighHighSelfTaxPDEObligationFalsifier O
  | cauchySaturatingSurfaceNotBelowThreshold :
      ¬ survivalDefect cauchySaturatingBadLedger
          (Real.sqrt (sharpTarget / cauchySaturatingBadLedger.gamma)) < 1 →
        HighHighSelfTaxPDEObligationFalsifier O
  | wallCasePromotedAboveWall :
      ¬ O.resonant_wall_case_not_promoted_above_wall →
        HighHighSelfTaxPDEObligationFalsifier O
  | wallBoundaryNotRespected :
      ¬ ¬ sharpTarget < cauchySaturatingWallLedger.gamma →
        HighHighSelfTaxPDEObligationFalsifier O
  | smoothProfileLimitMissing :
      ¬ O.smooth_profile_limit_preserves_high_high_receipt →
        HighHighSelfTaxPDEObligationFalsifier O
  | posthocPhaseShellOrObservableChoice :
      ¬ O.no_posthoc_phase_shell_or_observable_choice →
        HighHighSelfTaxPDEObligationFalsifier O

/-- A satisfied high-high self-tax PDE obligation excludes each named failure
branch. -/
theorem no_high_high_self_tax_pde_obligation_falsifier
    (O : HighHighSelfTaxPDEObligation)
    (hO : HighHighSelfTaxPDEObligationSatisfied O)
    (F : HighHighSelfTaxPDEObligationFalsifier O) :
    False := by
  rcases hO with
    ⟨htopology, hledger, hnonneg, hnull, hsos, hbad,
      hbad_surface, hwall, hwall_surface, hlimit, hposthoc⟩
  cases F with
  | topologyNotFixed h => exact h htopology
  | ledgerNotSameOutput h => exact h hledger
  | selfTaxNonnegativeMissing h => exact h hnonneg
  | nullSelfTaxCapMissing h => exact h hnull
  | crossAwareOrSOSReceiptMissing h => exact h hsos
  | cauchySaturatingSurfaceUnaddressed h => exact h hbad
  | cauchySaturatingSurfaceNotBelowThreshold h => exact h hbad_surface
  | wallCasePromotedAboveWall h => exact h hwall
  | wallBoundaryNotRespected h => exact h hwall_surface
  | smoothProfileLimitMissing h => exact h hlimit
  | posthocPhaseShellOrObservableChoice h => exact h hposthoc

/-- If every class member has a quartic high-high bridge, the class is priced. -/
theorem high_high_class_no_arbitrage_of_closed_positive
    (P : ClosedHighHighSelfTaxPositive)
    (T : LPInteractionLedger)
    (hT : P.Class T) :
    InteractionNoArbitrage T := by
  obtain ⟨H, hHT⟩ := P.bridge_of_class T hT
  have hclass : P.Class H.interaction := by
    rw [hHT]
    exact hT
  rw [← hHT]
  exact high_high_interaction_no_arbitrage_of_survival_projection
    H (P.quartic_survival_projection H hclass)

end ZtareProofs.NS
