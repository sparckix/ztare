import Mathlib.Tactic
import ZtareProofs.ns_cycle_resupply_threshold
import ZtareProofs.ns_low_frequency_lipschitz_control_bridge
import ZtareProofs.ns_low_high_lipschitz_reserve_adapter

open scoped BigOperators

/-!
# Event-level recurrence price bridge

This file isolates the dynamic recurrence-price accounting obligation at event
granularity.  The load-bearing point is multiplicity: if one shell returns many
times, the reciprocal-weight side must be budgeted over events, not merely over
shell labels.

No PDE estimate is claimed here.  The analytic proof still has to construct the
event weights `a_e`, prove the raw-plus-recurrence lower envelope, and supply
the finite Cauchy/duality inequality from the fixed recurrence geometry.
-/

namespace ZtareProofs.NS

noncomputable section

/-- Multiplicity-aware event recurrence ledger.

`eventWeight e` is the event weight `a_e`.  `rawPrice e + recurrencePrice e`
is the lower-envelope price that must dominate the weighted square gain for
that event.  `reciprocalBudget` is explicitly over events:
`sum_e 1 / a_e`, including repeated returns in the same shell. -/
structure EventRecurrencePriceLedger where
  eventGain : ℕ → Real
  eventWeight : ℕ → Real
  rawPrice : ℕ → Real
  recurrencePrice : ℕ → Real
  priceBudget : Real
  reciprocalBudget : Real

def eventGainPrefix
    (L : EventRecurrencePriceLedger) (N : ℕ) : Real :=
  nsPrefixSum L.eventGain N

def eventWeightedGainPricePrefix
    (L : EventRecurrencePriceLedger) (N : ℕ) : Real :=
  nsPrefixSum
    (fun e : ℕ => L.eventWeight e * (L.eventGain e) ^ (2 : Nat))
    N

def eventRawRecurrencePricePrefix
    (L : EventRecurrencePriceLedger) (N : ℕ) : Real :=
  nsPrefixSum
    (fun e : ℕ => L.rawPrice e + L.recurrencePrice e)
    N

def eventReciprocalWeightPrefix
    (L : EventRecurrencePriceLedger) (N : ℕ) : Real :=
  nsPrefixSum (fun e : ℕ => 1 / L.eventWeight e) N

/-- Event-recursion wrapper around the scalar same-ledger no-resupply theorem.

This imports the Phase 5EC scalar fact into the recurrence bridge without
claiming a Navier-Stokes estimate: if every event is charged against the same
nonnegative ledger weight with the same local cap, summing or resupplying
events cannot improve that cap.  Any claimed recurrence closure must therefore
pay for an independent amplifier, memory, or multiplicity-adjusted reserve. -/
theorem event_same_ledger_resupply_accumulation_le
    {ι : Type*} [Fintype ι]
    {S : Real} {weight response : ι → Real}
    (hpoint : ∀ i, response i ≤ S * weight i) :
    (∑ i, response i) ≤ S * (∑ i, weight i) :=
  ZtareProofs.same_ledger_accumulation_le hpoint

/-- Adaptive event-recursion wrapper around the scalar no-resupply theorem.

History-dependent event multipliers do not create a free recurrence amplifier
when they still multiply the same blockwise profit and defect ledger. -/
theorem event_adaptive_same_ledger_resupply_accumulation_le
    {ι : Type*} [Fintype ι]
    {S : Real} {adapt defect profit : ι → Real}
    (hadapt : ∀ i, 0 ≤ adapt i)
    (hpoint : ∀ i, profit i ≤ S * defect i) :
    (∑ i, adapt i * profit i) ≤
      S * (∑ i, adapt i * defect i) :=
  ZtareProofs.adaptive_same_ledger_accumulation_le hadapt hpoint

/-- Reuse the finite dual-norm bridge from
`ns_low_frequency_lipschitz_control_bridge`. -/
def EventRecurrencePriceLedger.toDualNormLedger
    (L : EventRecurrencePriceLedger) :
    EdgeGainDualNormLedger where
  gain := L.eventGain
  weightedPrice :=
    fun e : ℕ => L.eventWeight e * (L.eventGain e) ^ (2 : Nat)
  inverseWeight := fun e : ℕ => 1 / L.eventWeight e
  priceBudget := L.priceBudget
  dualBudget := L.reciprocalBudget

/-- Finite Cauchy/duality field at event granularity.

This is deliberately a field, not a theorem here: the PDE-side construction
must prove this inequality for the chosen event weights. -/
structure EventFiniteCauchyDualityField
    (L : EventRecurrencePriceLedger) where
  finite_cauchy_duality :
    ∀ N : ℕ,
      (eventGainPrefix L N) ^ (2 : Nat) ≤
        eventWeightedGainPricePrefix L N *
          eventReciprocalWeightPrefix L N

/-- Everything in the event recurrence-price bridge except the reciprocal
budget over events.

This is useful because the most common false proof supplies a shell-level
budget and then silently treats it as an event-level budget.  The missing
field must be supplied by an explicit multiplicity lift. -/
structure EventDynamicRecurrencePricePrecertificate
    (L : EventRecurrencePriceLedger) where
  event_weight_positive : ∀ e : ℕ, 0 < L.eventWeight e
  event_prices_declared_before_payoff : Prop
  event_prices_declared_before_payoff_paid :
    event_prices_declared_before_payoff
  event_prices_not_backfit_from_realized_gain_or_payoff : Prop
  event_prices_not_backfit_from_realized_gain_or_payoff_paid :
    event_prices_not_backfit_from_realized_gain_or_payoff
  price_budget_nonnegative : 0 ≤ L.priceBudget
  raw_recurrence_lower_envelope :
    ∀ e : ℕ,
      L.eventWeight e * (L.eventGain e) ^ (2 : Nat) ≤
        L.rawPrice e + L.recurrencePrice e
  raw_recurrence_prefix_le_budget :
    ∀ N : ℕ, eventRawRecurrencePricePrefix L N ≤ L.priceBudget
  duality : EventFiniteCauchyDualityField L

/-- Event-to-Duhamel/Bernstein lower-envelope receipt.

This is the exact typed interface for turning a low-high Duhamel/Bernstein
reserve estimate into the event recurrence lower envelope.  The fields are
the real PDE identifications: the event gain must be charged through the same
Duhamel kernel, and the resulting time-integrated reserve must be booked in
the event raw-plus-recurrence price. -/
structure EventDuhamelBernsteinLowerEnvelopeReceipt
    (L : EventRecurrencePriceLedger) where
  duhamel : ℕ → LowHighDuhamelBernsteinReceipt
  kernel_positive :
    ∀ e : ℕ,
      0 <
        (duhamel e).bernsteinConstant ^ 2 *
          (duhamel e).lowBandwidth ^ 3
  event_weight_kernel_bound :
    ∀ e : ℕ,
      ((duhamel e).bernsteinConstant ^ 2 *
          (duhamel e).lowBandwidth ^ 3) *
          (L.eventWeight e * (L.eventGain e) ^ (2 : Nat)) ≤
        2 * (duhamel e).dampingRate *
          (duhamel e).requiredGain ^ (2 : Nat)
  duhamel_reserve_charged_by_event_price :
    ∀ e : ℕ,
      (duhamel e).timeIntegratedReserve ≤
        L.rawPrice e + L.recurrencePrice e

/-- Duhamel/Bernstein event identification yields the raw recurrence lower
envelope required by the event pre-certificate.

This theorem deliberately does not construct the receipt above.  Constructing
it is the PDE work: same-event identification, kernel comparison, and
same-ledger reserve charging. -/
theorem raw_recurrence_lower_envelope_of_event_duhamel_bernstein
    (L : EventRecurrencePriceLedger)
    (R : EventDuhamelBernsteinLowerEnvelopeReceipt L) :
    ∀ e : ℕ,
      L.eventWeight e * (L.eventGain e) ^ (2 : Nat) ≤
        L.rawPrice e + L.recurrencePrice e := by
  intro e
  let D := R.duhamel e
  let kernel := D.bernsteinConstant ^ 2 * D.lowBandwidth ^ 3
  have hkernel : 0 < kernel := by
    simpa [D, kernel] using R.kernel_positive e
  have hweighted :
      kernel * (L.eventWeight e * (L.eventGain e) ^ (2 : Nat)) ≤
        2 * D.dampingRate * D.requiredGain ^ (2 : Nat) := by
    simpa [D, kernel] using R.event_weight_kernel_bound e
  have hduhamel :
      2 * D.dampingRate * D.requiredGain ^ (2 : Nat) ≤
        kernel * D.timeIntegratedReserve := by
    simpa [D, kernel] using
      low_high_duhamel_bernstein_integrated_reserve_bound D
  have hcharged :
      D.timeIntegratedReserve ≤ L.rawPrice e + L.recurrencePrice e := by
    simpa [D] using R.duhamel_reserve_charged_by_event_price e
  have hkernel_bound :
      kernel * (L.eventWeight e * (L.eventGain e) ^ (2 : Nat)) ≤
        kernel * D.timeIntegratedReserve :=
    hweighted.trans hduhamel
  have hprice_le_reserve :
      L.eventWeight e * (L.eventGain e) ^ (2 : Nat) ≤
        D.timeIntegratedReserve :=
    le_of_mul_le_mul_left hkernel_bound hkernel
  exact hprice_le_reserve.trans hcharged

/-- Branch-wise falsifier for the Duhamel/Bernstein event lower-envelope
receipt.

Each constructor is an endpoint failure of the source receipt: either the
charged kernel is not positive, the event gain is not below the Duhamel
reserve price, or the time-integrated reserve was never booked into the event
raw-plus-recurrence ledger. -/
inductive EventDuhamelBernsteinLowerEnvelopeFalsifier
    (L : EventRecurrencePriceLedger)
    (R : EventDuhamelBernsteinLowerEnvelopeReceipt L) : Type where
  | kernelNonpositive (e : ℕ) :
      ¬ 0 <
        (R.duhamel e).bernsteinConstant ^ 2 *
          (R.duhamel e).lowBandwidth ^ 3 →
      EventDuhamelBernsteinLowerEnvelopeFalsifier L R
  | eventGainUnderpriced (e : ℕ) :
      2 * (R.duhamel e).dampingRate *
          (R.duhamel e).requiredGain ^ (2 : Nat) <
        ((R.duhamel e).bernsteinConstant ^ 2 *
          (R.duhamel e).lowBandwidth ^ 3) *
          (L.eventWeight e * (L.eventGain e) ^ (2 : Nat)) →
      EventDuhamelBernsteinLowerEnvelopeFalsifier L R
  | reserveNotChargedByEventPrice (e : ℕ) :
      L.rawPrice e + L.recurrencePrice e <
        (R.duhamel e).timeIntegratedReserve →
      EventDuhamelBernsteinLowerEnvelopeFalsifier L R

/-- A declared Duhamel/Bernstein lower-envelope receipt excludes the endpoint
failure branches above. -/
theorem no_event_duhamel_bernstein_lower_envelope_falsifier
    (L : EventRecurrencePriceLedger)
    (R : EventDuhamelBernsteinLowerEnvelopeReceipt L)
    (F : EventDuhamelBernsteinLowerEnvelopeFalsifier L R) :
    False := by
  cases F with
  | kernelNonpositive e hkernel =>
      exact hkernel (R.kernel_positive e)
  | eventGainUnderpriced e hbad =>
      exact not_lt_of_ge (R.event_weight_kernel_bound e) hbad
  | reserveNotChargedByEventPrice e hbad =>
      exact not_lt_of_ge (R.duhamel_reserve_charged_by_event_price e) hbad

/-- Source form of the event recurrence pre-certificate whose lower envelope
is derived from a Duhamel/Bernstein receipt instead of carried as a detached
pointwise inequality. -/
structure EventDynamicRecurrencePricePrecertificateSource
    (L : EventRecurrencePriceLedger) where
  event_weight_positive : ∀ e : ℕ, 0 < L.eventWeight e
  event_prices_declared_before_payoff : Prop
  event_prices_declared_before_payoff_paid :
    event_prices_declared_before_payoff
  event_prices_not_backfit_from_realized_gain_or_payoff : Prop
  event_prices_not_backfit_from_realized_gain_or_payoff_paid :
    event_prices_not_backfit_from_realized_gain_or_payoff
  price_budget_nonnegative : 0 ≤ L.priceBudget
  duhamel_lower_envelope :
    EventDuhamelBernsteinLowerEnvelopeReceipt L
  raw_recurrence_prefix_le_budget :
    ∀ N : ℕ, eventRawRecurrencePricePrefix L N ≤ L.priceBudget
  duality : EventFiniteCauchyDualityField L

/-- A Duhamel/Bernstein source pre-certificate instantiates the event
pre-certificate, deriving the lower-envelope field rather than accepting it as
a raw assumption. -/
def event_precertificate_of_duhamel_bernstein_source
    (L : EventRecurrencePriceLedger)
    (S : EventDynamicRecurrencePricePrecertificateSource L) :
    EventDynamicRecurrencePricePrecertificate L where
  event_weight_positive := S.event_weight_positive
  event_prices_declared_before_payoff :=
    S.event_prices_declared_before_payoff
  event_prices_declared_before_payoff_paid :=
    S.event_prices_declared_before_payoff_paid
  event_prices_not_backfit_from_realized_gain_or_payoff :=
    S.event_prices_not_backfit_from_realized_gain_or_payoff
  event_prices_not_backfit_from_realized_gain_or_payoff_paid :=
    S.event_prices_not_backfit_from_realized_gain_or_payoff_paid
  price_budget_nonnegative := S.price_budget_nonnegative
  raw_recurrence_lower_envelope :=
    raw_recurrence_lower_envelope_of_event_duhamel_bernstein
      L S.duhamel_lower_envelope
  raw_recurrence_prefix_le_budget :=
    S.raw_recurrence_prefix_le_budget
  duality := S.duality

/-- Explicit event-multiplicity reciprocal lift.

`event_reciprocal_prefix_le_budget` is the non-tautological field: it is over
actual events, including repeated returns inside one shell.  A shell-label
budget does not populate this field unless the multiplicity lift is proved. -/
structure EventMultiplicityAdjustedReciprocalLift
    (L : EventRecurrencePriceLedger) where
  eventReciprocalBudget : Real
  budget_nonnegative : 0 ≤ eventReciprocalBudget
  event_reciprocal_prefix_le_budget :
    ∀ N : ℕ, eventReciprocalWeightPrefix L N ≤ eventReciprocalBudget
  fixed_event_sections_before_payoff : Prop
  multiplicity_charged_before_payoff : Prop

/-- Section-level effective-multiplicity reciprocal prefix.

This is the intermediate budget actually supplied by an incidence argument:
first lift event reciprocal mass into a shell-section effective-multiplicity
prefix, then bound that prefix by the declared event reciprocal budget. -/
def sectionEffectiveMultiplicityReciprocalPrefix
    (shellWeight effectiveMultiplicity : ℕ → Real) (N : ℕ) : Real :=
  nsPrefixSum (fun j : ℕ => effectiveMultiplicity j / shellWeight j) N

/-- Fixed event-section incidence receipt.

This is one layer more concrete than `EventMultiplicityAdjustedReciprocalLift`.
It records that recurrence events were assigned to shell sections and
preparation windows before payoff, that window/resource overlap was measured,
and that the reciprocal event budget was charged using the effective
multiplicity, not just shell labels or raw event counts.

No incidence estimate is proved here.  A PDE construction must first lift the
event reciprocal prefix into the effective-multiplicity section prefix, then
bound that section prefix by the declared event budget. -/
structure EventSectionIncidenceReceipt
    (L : EventRecurrencePriceLedger) where
  shellOfEvent : ℕ → ℕ
  shellWeight : ℕ → Real
  rawEventMultiplicity : ℕ → Real
  overlapTax : ℕ → Real
  effectiveMultiplicity : ℕ → Real
  eventReciprocalBudget : Real
  shell_weight_positive : ∀ j : ℕ, 0 < shellWeight j
  raw_event_multiplicity_nonnegative :
    ∀ j : ℕ, 0 ≤ rawEventMultiplicity j
  overlap_tax_ge_one : ∀ j : ℕ, 1 ≤ overlapTax j
  effective_multiplicity_eq :
    ∀ j : ℕ,
      effectiveMultiplicity j =
        rawEventMultiplicity j * overlapTax j
  event_weight_inherits_shell_weight :
    ∀ e : ℕ, L.eventWeight e = shellWeight (shellOfEvent e)
  event_reciprocal_budget_nonnegative : 0 ≤ eventReciprocalBudget
  fixed_event_sections_before_payoff : Prop
  preparation_windows_declared_before_payoff : Prop
  resource_overlap_measured_before_payoff : Prop
  overlap_tax_charged_before_payoff : Prop
  no_shell_only_budget_shortcut : Prop
  event_reciprocal_prefix_le_effective_multiplicity_prefix :
    ∀ N : ℕ,
      eventReciprocalWeightPrefix L N ≤
        sectionEffectiveMultiplicityReciprocalPrefix
          shellWeight
          effectiveMultiplicity
          N
  effective_multiplicity_prefix_le_event_reciprocal_budget :
    ∀ N : ℕ,
      sectionEffectiveMultiplicityReciprocalPrefix
          shellWeight
          effectiveMultiplicity
          N ≤
        eventReciprocalBudget

/-- Backward-compatible event-budget conclusion, derived through the
effective-multiplicity prefix rather than stored as a detachable field. -/
theorem EventSectionIncidenceReceipt.event_reciprocal_prefix_le_effective_budget
    {L : EventRecurrencePriceLedger}
    (R : EventSectionIncidenceReceipt L) :
    ∀ N : ℕ, eventReciprocalWeightPrefix L N ≤ R.eventReciprocalBudget := by
  intro N
  exact
    (R.event_reciprocal_prefix_le_effective_multiplicity_prefix N).trans
      (R.effective_multiplicity_prefix_le_event_reciprocal_budget N)

/-- Deterministic lower-envelope geometry probe receipt.

This records the Phase 5JE accounting split: raw/unit/count-only recurrence
prices underprice the overlap-adjusted target, while a valid geometry must
provide the full effective-multiplicity critical weight (or a dyadic analogue)
with event clocks and all-output embedding fixed before payoff.  It is a
probe receipt, not a PDE estimate. -/
structure EventLowerEnvelopeGeometryProbeReceipt where
  scenariosChecked : ℕ
  validGeometrySequenceClosers : ℕ
  underpricedTargetCases : ℕ
  invalidGuardClosers : ℕ
  valid_geometry_sequence_closer_exists :
    0 < validGeometrySequenceClosers
  underpriced_target_cases_exist :
    0 < underpricedTargetCases
  invalid_guard_closers_exist :
    0 < invalidGuardClosers
  raw_duhamel_unit_and_count_only_underprice_target : Prop
  raw_duhamel_unit_and_count_only_underprice_target_paid :
    raw_duhamel_unit_and_count_only_underprice_target
  overlap_adjusted_log_or_dyadic_geometry_is_sequence_sufficient : Prop
  overlap_adjusted_log_or_dyadic_geometry_is_sequence_sufficient_paid :
    overlap_adjusted_log_or_dyadic_geometry_is_sequence_sufficient
  posthoc_event_clocks_and_unembedded_prices_invalid : Prop
  posthoc_event_clocks_and_unembedded_prices_invalid_paid :
    posthoc_event_clocks_and_unembedded_prices_invalid
  no_pde_estimate_claimed_from_exponent_probe : Prop
  no_pde_estimate_claimed_from_exponent_probe_paid :
    no_pde_estimate_claimed_from_exponent_probe

/-- Paid form of the deterministic lower-envelope geometry probe.

This is not a PDE estimate; it only exposes which finite-panel lower-envelope
guards were actually paid before a source bundle may use the probe to
discharge a higher-level event-duty field. -/
def EventLowerEnvelopeGeometryProbeReceipt.Paid
    (R : EventLowerEnvelopeGeometryProbeReceipt) : Prop :=
  0 < R.validGeometrySequenceClosers ∧
    0 < R.underpricedTargetCases ∧
      0 < R.invalidGuardClosers ∧
        R.raw_duhamel_unit_and_count_only_underprice_target ∧
          R.overlap_adjusted_log_or_dyadic_geometry_is_sequence_sufficient ∧
            R.posthoc_event_clocks_and_unembedded_prices_invalid ∧
              R.no_pde_estimate_claimed_from_exponent_probe

theorem EventLowerEnvelopeGeometryProbeReceipt.paid
    (R : EventLowerEnvelopeGeometryProbeReceipt) :
    R.Paid :=
  ⟨R.valid_geometry_sequence_closer_exists,
    R.underpriced_target_cases_exist,
    R.invalid_guard_closers_exist,
    R.raw_duhamel_unit_and_count_only_underprice_target_paid,
    R.overlap_adjusted_log_or_dyadic_geometry_is_sequence_sufficient_paid,
    R.posthoc_event_clocks_and_unembedded_prices_invalid_paid,
    R.no_pde_estimate_claimed_from_exponent_probe_paid⟩

/-- Smooth fixed-event-clock lower-envelope falsifier receipt.

This records the Phase 5JH obstruction: a finite-prefix smooth LP/Bony clock
with raw edge geometry at or below the square-root boundary does not provide
the event weight required by the overlap-adjusted recurrence threshold.  A
valid closure must therefore add a strict super-sqrt gain theorem or an
independent predeclared recurrence reserve embedded in the same all-output
stream. -/
structure EventLowerEnvelopeSmoothFalsifierReceipt where
  scenariosChecked : ℕ
  rawFixedClockFailures : ℕ
  conditionalPredeclaredClosers : ℕ
  invalidPosthocOrUnembeddedClosers : ℕ
  blockFalsifierCases : ℕ
  raw_fixed_clock_failures_exist : 0 < rawFixedClockFailures
  conditional_predeclared_closers_exist :
    0 < conditionalPredeclaredClosers
  invalid_posthoc_or_unembedded_closers_exist :
    0 < invalidPosthocOrUnembeddedClosers
  fixed_smooth_lp_edge_clock_declared_before_payoff : Prop
  fixed_smooth_lp_edge_clock_declared_before_payoff_paid :
    fixed_smooth_lp_edge_clock_declared_before_payoff
  raw_lp_bony_beta_le_half_underprices_overlap_adjusted_threshold : Prop
  raw_lp_bony_beta_le_half_underprices_overlap_adjusted_threshold_paid :
    raw_lp_bony_beta_le_half_underprices_overlap_adjusted_threshold
  sqrt_boundary_leaves_divergent_event_reciprocal_budget : Prop
  sqrt_boundary_leaves_divergent_event_reciprocal_budget_paid :
    sqrt_boundary_leaves_divergent_event_reciprocal_budget
  closure_requires_super_sqrt_gain_or_predeclared_log_reserve : Prop
  closure_requires_super_sqrt_gain_or_predeclared_log_reserve_paid :
    closure_requires_super_sqrt_gain_or_predeclared_log_reserve
  posthoc_clocks_and_unembedded_prices_invalid : Prop
  posthoc_clocks_and_unembedded_prices_invalid_paid :
    posthoc_clocks_and_unembedded_prices_invalid
  no_pde_closure_claimed_from_smooth_prefix_panel : Prop
  no_pde_closure_claimed_from_smooth_prefix_panel_paid :
    no_pde_closure_claimed_from_smooth_prefix_panel

/-- Paid form of the smooth fixed-event-clock lower-envelope falsifier panel.
-/
def EventLowerEnvelopeSmoothFalsifierReceipt.Paid
    (R : EventLowerEnvelopeSmoothFalsifierReceipt) : Prop :=
  0 < R.rawFixedClockFailures ∧
    0 < R.conditionalPredeclaredClosers ∧
      0 < R.invalidPosthocOrUnembeddedClosers ∧
        R.fixed_smooth_lp_edge_clock_declared_before_payoff ∧
          R.raw_lp_bony_beta_le_half_underprices_overlap_adjusted_threshold ∧
            R.sqrt_boundary_leaves_divergent_event_reciprocal_budget ∧
              R.closure_requires_super_sqrt_gain_or_predeclared_log_reserve ∧
                R.posthoc_clocks_and_unembedded_prices_invalid ∧
                  R.no_pde_closure_claimed_from_smooth_prefix_panel

theorem EventLowerEnvelopeSmoothFalsifierReceipt.paid
    (R : EventLowerEnvelopeSmoothFalsifierReceipt) :
    R.Paid :=
  ⟨R.raw_fixed_clock_failures_exist,
    R.conditional_predeclared_closers_exist,
    R.invalid_posthoc_or_unembedded_closers_exist,
    R.fixed_smooth_lp_edge_clock_declared_before_payoff_paid,
    R.raw_lp_bony_beta_le_half_underprices_overlap_adjusted_threshold_paid,
    R.sqrt_boundary_leaves_divergent_event_reciprocal_budget_paid,
    R.closure_requires_super_sqrt_gain_or_predeclared_log_reserve_paid,
    R.posthoc_clocks_and_unembedded_prices_invalid_paid,
    R.no_pde_closure_claimed_from_smooth_prefix_panel_paid⟩

/-- Fractional log-gain adversary receipt.

This records the hostile construction-side audit: the target
`g_j = 1 / (j log(j)^ρ)` can diverge only for `ρ ≤ 1`, while a recurrence-safe
single all-output reserve of the Phase 5JD/5JH kind makes the realized
gain-price finite only beyond the divergent range.  A genuine blowup
blueprint must therefore decouple the recurrence reserve from realized
all-output gain price by a predeclared PDE mechanism, not by instant
prepositioning or posthoc clocks. -/
structure FractionalLogGainAdversaryReceipt where
  scenarioCount : ℕ
  validUnderAntiTautologyGuards : ℕ
  invalidControls : ℕ
  harmonicValidFailures : ℕ
  recurrencePaidPriceDiverges : ℕ
  recurrenceUnderpriced : ℕ
  smoothNSEAdmissibleBlueprints : ℕ
  no_smooth_nse_admissible_blueprints_found :
    smoothNSEAdmissibleBlueprints = 0
  invalid_controls_use_instant_prepositioning_posthoc_or_infinite_profile : Prop
  invalid_controls_use_instant_prepositioning_posthoc_or_infinite_profile_paid :
    invalid_controls_use_instant_prepositioning_posthoc_or_infinite_profile
  raw_fixed_clock_attempts_underprice_recurrence : Prop
  raw_fixed_clock_attempts_underprice_recurrence_paid :
    raw_fixed_clock_attempts_underprice_recurrence
  recurrence_safe_reserve_makes_harmonic_gain_price_diverge : Prop
  recurrence_safe_reserve_makes_harmonic_gain_price_diverge_paid :
    recurrence_safe_reserve_makes_harmonic_gain_price_diverge
  price_finite_fractional_log_gain_has_summable_gain_tail : Prop
  price_finite_fractional_log_gain_has_summable_gain_tail_paid :
    price_finite_fractional_log_gain_has_summable_gain_tail
  valid_blowup_needs_predeclared_decoupling_mechanism : Prop
  valid_blowup_needs_predeclared_decoupling_mechanism_paid :
    valid_blowup_needs_predeclared_decoupling_mechanism
  no_nse_counterexample_claimed_from_construction_panel : Prop
  no_nse_counterexample_claimed_from_construction_panel_paid :
    no_nse_counterexample_claimed_from_construction_panel

/-- Paid form of the fractional log-gain adversary panel. -/
def FractionalLogGainAdversaryReceipt.Paid
    (R : FractionalLogGainAdversaryReceipt) : Prop :=
  R.smoothNSEAdmissibleBlueprints = 0 ∧
    R.invalid_controls_use_instant_prepositioning_posthoc_or_infinite_profile ∧
      R.raw_fixed_clock_attempts_underprice_recurrence ∧
        R.recurrence_safe_reserve_makes_harmonic_gain_price_diverge ∧
          R.price_finite_fractional_log_gain_has_summable_gain_tail ∧
            R.valid_blowup_needs_predeclared_decoupling_mechanism ∧
              R.no_nse_counterexample_claimed_from_construction_panel

theorem FractionalLogGainAdversaryReceipt.paid
    (R : FractionalLogGainAdversaryReceipt) :
    R.Paid :=
  ⟨R.no_smooth_nse_admissible_blueprints_found,
    R.invalid_controls_use_instant_prepositioning_posthoc_or_infinite_profile_paid,
    R.raw_fixed_clock_attempts_underprice_recurrence_paid,
    R.recurrence_safe_reserve_makes_harmonic_gain_price_diverge_paid,
    R.price_finite_fractional_log_gain_has_summable_gain_tail_paid,
    R.valid_blowup_needs_predeclared_decoupling_mechanism_paid,
    R.no_nse_counterexample_claimed_from_construction_panel_paid⟩

/-- Reserve/gain decoupling search receipt.

This records the follow-up attack on the only mechanism left open by the
fractional log-gain adversary: try to route recurrence reserve through one
fixed all-output channel while realizing harmonic gain through another.  Under
fixed atoms/topology and nonnegative positive-Gram pricing, the tested valid
mechanisms either keep coherent harmonic gain and pay divergent realized price,
or make price finite by losing the fixed coherent harmonic output section. -/
structure ReserveGainDecouplingSearchReceipt where
  mechanismCount : ℕ
  validUnderAntiTautologyGuards : ℕ
  invalidNegativeControls : ℕ
  validDecouplersFound : ℕ
  validRecurrenceSafePriceDivergent : ℕ
  validNoFixedOutputHarmonicGain : ℕ
  no_valid_decouplers_found : validDecouplersFound = 0
  fixed_positive_gram_guards_enforced : Prop
  fixed_positive_gram_guards_enforced_paid :
    fixed_positive_gram_guards_enforced
  coherent_harmonic_mechanisms_have_divergent_realized_price : Prop
  coherent_harmonic_mechanisms_have_divergent_realized_price_paid :
    coherent_harmonic_mechanisms_have_divergent_realized_price
  finite_price_mechanisms_lose_fixed_output_harmonic_gain : Prop
  finite_price_mechanisms_lose_fixed_output_harmonic_gain_paid :
    finite_price_mechanisms_lose_fixed_output_harmonic_gain
  invalid_controls_break_clock_topology_expectation_or_smooth_tail_guard : Prop
  invalid_controls_break_clock_topology_expectation_or_smooth_tail_guard_paid :
    invalid_controls_break_clock_topology_expectation_or_smooth_tail_guard
  no_nse_counterexample_claimed_from_decoupling_panel : Prop
  no_nse_counterexample_claimed_from_decoupling_panel_paid :
    no_nse_counterexample_claimed_from_decoupling_panel

/-- Matrix/intertwiner reserve-gain decoupling audit receipt.

This is the finite-dimensional matrix analogue of
`ReserveGainDecouplingSearchReceipt`.  It records that apparent decouplers
arise only by breaking the fixed all-output positive-Gram ledger: the gain lane
is not coupled to the recurrence receipt, PSD pushforward ballast is omitted,
signed cancellation is credited, or the output subspace moves.  Valid
intertwiner controls restore harmonic all-output positive-Gram price
divergence. -/
structure MatrixReserveGainDecouplingAuditReceipt where
  scenarioCount : ℕ
  apparentInvalidDecouplers : ℕ
  validRecurrencePaidPriceDivergentControls : ℕ
  candidateValidDecouplers : ℕ
  no_candidate_valid_decouplers_found : candidateValidDecouplers = 0
  fixed_all_output_positive_gram_ledger_enforced : Prop
  fixed_all_output_positive_gram_ledger_enforced_paid :
    fixed_all_output_positive_gram_ledger_enforced
  psd_pushforward_ballast_included : Prop
  psd_pushforward_ballast_included_paid :
    psd_pushforward_ballast_included
  no_signed_cancellation_credit : Prop
  no_signed_cancellation_credit_paid :
    no_signed_cancellation_credit
  no_moving_output_subspace : Prop
  no_moving_output_subspace_paid :
    no_moving_output_subspace
  valid_intertwiners_restore_harmonic_price_divergence : Prop
  valid_intertwiners_restore_harmonic_price_divergence_paid :
    valid_intertwiners_restore_harmonic_price_divergence
  no_nse_counterexample_claimed_from_matrix_panel : Prop
  no_nse_counterexample_claimed_from_matrix_panel_paid :
    no_nse_counterexample_claimed_from_matrix_panel

/-- Setup-latency / geometric execution-cost audit receipt.

This records the dynamic execution-cost inversion: if the next shell requires
geometric phase alignment, then either setup latency is bounded below and
viscosity erases the high shell, or setup is accelerated to `N_j^2` scale and
the catalyst/all-output reserve diverges.  Invalid controls are the usual
anti-tautology breaks: zero latency, unpriced high-frequency catalyst,
prealigned infinite tails, or expectation-only alignment. -/
structure SetupLatencyExecutionCostReceipt where
  scenarioCount : ℕ
  antiTautologyValidCount : ℕ
  invalidControls : ℕ
  viscousSurvivalKillsHarmonicGain : ℕ
  harmonicSurvivesOnlyWithDivergentPrice : ℕ
  validSmoothBlowupBlueprints : ℕ
  no_valid_smooth_blowup_blueprints_found :
    validSmoothBlowupBlueprints = 0
  setup_latency_declared_before_payoff : Prop
  setup_latency_declared_before_payoff_paid :
    setup_latency_declared_before_payoff
  catalyst_rate_bound_declared_before_payoff : Prop
  catalyst_rate_bound_declared_before_payoff_paid :
    catalyst_rate_bound_declared_before_payoff
  bounded_or_polynomial_setup_latency_erases_harmonic_gain : Prop
  bounded_or_polynomial_setup_latency_erases_harmonic_gain_paid :
    bounded_or_polynomial_setup_latency_erases_harmonic_gain
  n_squared_scale_catalyst_survival_requires_divergent_price : Prop
  n_squared_scale_catalyst_survival_requires_divergent_price_paid :
    n_squared_scale_catalyst_survival_requires_divergent_price
  zero_latency_unpriced_catalyst_prealigned_tail_and_expectation_only_invalid : Prop
  zero_latency_unpriced_catalyst_prealigned_tail_and_expectation_only_invalid_paid :
    zero_latency_unpriced_catalyst_prealigned_tail_and_expectation_only_invalid
  no_nse_counterexample_claimed_from_setup_latency_panel : Prop
  no_nse_counterexample_claimed_from_setup_latency_panel_paid :
    no_nse_counterexample_claimed_from_setup_latency_panel

/-- Dynamic setup-latency counterexample-search receipt.

This records the next inversion after setup-latency accounting: try to build a
fixed periodic smooth dyadic shell-transfer schedule with parabolic setup
windows, divergent harmonic delivered gain, finite setup/action price, finite
recurrence budget, and finite all-output positive-Gram price.  The modeled
valid schedules either are erased by viscosity, pay divergent setup action, or
keep setup finite only while the all-output positive-Gram price diverges.
Apparent wins break fixed clocks/topology, recurrence reserve, positive-Gram
pricing, signed-credit, or finite-prefix smoothness guards. -/
structure DynamicLatencyCounterexampleSearchReceipt where
  scenarioCount : ℕ
  validGuardCount : ℕ
  invalidGuardCount : ℕ
  candidateValidCounterexamples : ℕ
  validSetupPriceDiverges : ℕ
  validAllOutputPositiveGramPriceDiverges : ℕ
  validViscousLatencyRegularized : ℕ
  no_candidate_valid_counterexamples_found :
    candidateValidCounterexamples = 0
  fixed_periodic_topology_and_clocks_declared : Prop
  fixed_periodic_topology_and_clocks_declared_paid :
    fixed_periodic_topology_and_clocks_declared
  parabolic_window_fast_setup_either_pays_action_or_all_output_price : Prop
  parabolic_window_fast_setup_either_pays_action_or_all_output_price_paid :
    parabolic_window_fast_setup_either_pays_action_or_all_output_price
  invalid_controls_break_recurrence_output_clock_signed_or_tail_guards : Prop
  invalid_controls_break_recurrence_output_clock_signed_or_tail_guards_paid :
    invalid_controls_break_recurrence_output_clock_signed_or_tail_guards
  no_nse_counterexample_claimed_from_dynamic_latency_panel : Prop
  no_nse_counterexample_claimed_from_dynamic_latency_panel_paid :
    no_nse_counterexample_claimed_from_dynamic_latency_panel

/-- Smooth fixed-topology phase-latency PDE obligation falsifier receipt.

This records the proof-facing version of the setup-latency branch.  It asks for
a smooth periodic LP/Bony shell-transfer sequence with fixed topology and fixed
positive-Gram ledger, phase angle comparable to harmonic gain, parabolic
windows, divergent delivered gain, and bounded catalyst/commutator/all-output
prices.  The local panel found no such schedule; valid fast schedules pay a
divergent catalyst or commutator/all-output price, while apparent finite-price
wins break anti-tautology guards. -/
structure SmoothLatencyPDEObligationFalsifierReceipt where
  scenarioCount : ℕ
  candidateSmoothFixedTopologyEscapes : ℕ
  invalidNegativeControls : ℕ
  fastValidPriceDivergentControls : ℕ
  no_candidate_smooth_fixed_topology_escapes_found :
    candidateSmoothFixedTopologyEscapes = 0
  fixed_lp_bony_topology_declared_before_payoff : Prop
  fixed_lp_bony_topology_declared_before_payoff_paid :
    fixed_lp_bony_topology_declared_before_payoff
  phase_angle_comparable_to_harmonic_gain_guard : Prop
  phase_angle_comparable_to_harmonic_gain_guard_paid :
    phase_angle_comparable_to_harmonic_gain_guard
  parabolic_window_survival_requires_catalyst_or_commutator_price : Prop
  parabolic_window_survival_requires_catalyst_or_commutator_price_paid :
    parabolic_window_survival_requires_catalyst_or_commutator_price
  moving_topology_posthoc_clock_hidden_catalyst_expectation_and_coupon_invalid : Prop
  moving_topology_posthoc_clock_hidden_catalyst_expectation_and_coupon_invalid_paid :
    moving_topology_posthoc_clock_hidden_catalyst_expectation_and_coupon_invalid
  remaining_pde_theorem_or_finite_prefix_falsifier_declared : Prop
  remaining_pde_theorem_or_finite_prefix_falsifier_declared_paid :
    remaining_pde_theorem_or_finite_prefix_falsifier_declared
  no_nse_counterexample_claimed_from_smooth_latency_panel : Prop
  no_nse_counterexample_claimed_from_smooth_latency_panel_paid :
    no_nse_counterexample_claimed_from_smooth_latency_panel

/-- Concrete Fourier latency falsifier receipt.

This records the bounded deterministic Fourier LP/Bony panel for the phase
latency theorem.  In the tested low-high block
`p = k + q`, `P_p((a_q · ∇)b_k)`, no bounded-Lipschitz row can rotate the
high interaction by `theta_j ≃ 1/j` on the parabolic window `|k|^-2`.
The only suspicious action-only rows have summable `L_j^2 |k|^-2` but require
low catalyst amplitude/lane price growing like `|k|^2/j^2`. -/
structure ConcreteFourierLatencyFalsifierReceipt where
  rowsEvaluated : ℕ
  zeroCouplingRowsSkipped : ℕ
  boundedLipschitzCandidates : ℕ
  suspiciousActionOnlyRows : ℕ
  highShellCount : ℕ
  no_bounded_lipschitz_candidates_found :
    boundedLipschitzCandidates = 0
  fixed_modes_topology_and_output_lanes_before_payoff : Prop
  fixed_modes_topology_and_output_lanes_before_payoff_paid :
    fixed_modes_topology_and_output_lanes_before_payoff
  low_high_leray_symbol_bound_verified_rowwise : Prop
  low_high_leray_symbol_bound_verified_rowwise_paid :
    low_high_leray_symbol_bound_verified_rowwise
  action_only_rows_require_unbounded_low_catalyst_gram : Prop
  action_only_rows_require_unbounded_low_catalyst_gram_paid :
    action_only_rows_require_unbounded_low_catalyst_gram
  no_moving_posthoc_hidden_or_signed_controls : Prop
  no_moving_posthoc_hidden_or_signed_controls_paid :
    no_moving_posthoc_hidden_or_signed_controls
  remaining_pde_symbol_theorem_or_falsifier_declared : Prop
  remaining_pde_symbol_theorem_or_falsifier_declared_paid :
    remaining_pde_symbol_theorem_or_falsifier_declared
  no_nse_counterexample_claimed_from_concrete_fourier_panel : Prop
  no_nse_counterexample_claimed_from_concrete_fourier_panel_paid :
    no_nse_counterexample_claimed_from_concrete_fourier_panel

/-- Paid form of the reserve/gain decoupling search panel. -/
def ReserveGainDecouplingSearchReceipt.Paid
    (R : ReserveGainDecouplingSearchReceipt) : Prop :=
  R.validDecouplersFound = 0 ∧
    R.fixed_positive_gram_guards_enforced ∧
      R.coherent_harmonic_mechanisms_have_divergent_realized_price ∧
        R.finite_price_mechanisms_lose_fixed_output_harmonic_gain ∧
          R.invalid_controls_break_clock_topology_expectation_or_smooth_tail_guard ∧
            R.no_nse_counterexample_claimed_from_decoupling_panel

theorem ReserveGainDecouplingSearchReceipt.paid
    (R : ReserveGainDecouplingSearchReceipt) :
    R.Paid :=
  ⟨R.no_valid_decouplers_found,
    R.fixed_positive_gram_guards_enforced_paid,
    R.coherent_harmonic_mechanisms_have_divergent_realized_price_paid,
    R.finite_price_mechanisms_lose_fixed_output_harmonic_gain_paid,
    R.invalid_controls_break_clock_topology_expectation_or_smooth_tail_guard_paid,
    R.no_nse_counterexample_claimed_from_decoupling_panel_paid⟩

/-- Paid form of the matrix reserve/gain decoupling audit panel. -/
def MatrixReserveGainDecouplingAuditReceipt.Paid
    (R : MatrixReserveGainDecouplingAuditReceipt) : Prop :=
  R.candidateValidDecouplers = 0 ∧
    R.fixed_all_output_positive_gram_ledger_enforced ∧
      R.psd_pushforward_ballast_included ∧
        R.no_signed_cancellation_credit ∧
          R.no_moving_output_subspace ∧
            R.valid_intertwiners_restore_harmonic_price_divergence ∧
              R.no_nse_counterexample_claimed_from_matrix_panel

theorem MatrixReserveGainDecouplingAuditReceipt.paid
    (R : MatrixReserveGainDecouplingAuditReceipt) :
    R.Paid :=
  ⟨R.no_candidate_valid_decouplers_found,
    R.fixed_all_output_positive_gram_ledger_enforced_paid,
    R.psd_pushforward_ballast_included_paid,
    R.no_signed_cancellation_credit_paid,
    R.no_moving_output_subspace_paid,
    R.valid_intertwiners_restore_harmonic_price_divergence_paid,
    R.no_nse_counterexample_claimed_from_matrix_panel_paid⟩

/-- Paid form of the setup-latency execution-cost panel. -/
def SetupLatencyExecutionCostReceipt.Paid
    (R : SetupLatencyExecutionCostReceipt) : Prop :=
  R.validSmoothBlowupBlueprints = 0 ∧
    R.setup_latency_declared_before_payoff ∧
      R.catalyst_rate_bound_declared_before_payoff ∧
        R.bounded_or_polynomial_setup_latency_erases_harmonic_gain ∧
          R.n_squared_scale_catalyst_survival_requires_divergent_price ∧
            R.zero_latency_unpriced_catalyst_prealigned_tail_and_expectation_only_invalid ∧
              R.no_nse_counterexample_claimed_from_setup_latency_panel

theorem SetupLatencyExecutionCostReceipt.paid
    (R : SetupLatencyExecutionCostReceipt) :
    R.Paid :=
  ⟨R.no_valid_smooth_blowup_blueprints_found,
    R.setup_latency_declared_before_payoff_paid,
    R.catalyst_rate_bound_declared_before_payoff_paid,
    R.bounded_or_polynomial_setup_latency_erases_harmonic_gain_paid,
    R.n_squared_scale_catalyst_survival_requires_divergent_price_paid,
    R.zero_latency_unpriced_catalyst_prealigned_tail_and_expectation_only_invalid_paid,
    R.no_nse_counterexample_claimed_from_setup_latency_panel_paid⟩

/-- Paid form of the dynamic latency counterexample-search panel. -/
def DynamicLatencyCounterexampleSearchReceipt.Paid
    (R : DynamicLatencyCounterexampleSearchReceipt) : Prop :=
  R.candidateValidCounterexamples = 0 ∧
    R.fixed_periodic_topology_and_clocks_declared ∧
      R.parabolic_window_fast_setup_either_pays_action_or_all_output_price ∧
        R.invalid_controls_break_recurrence_output_clock_signed_or_tail_guards ∧
          R.no_nse_counterexample_claimed_from_dynamic_latency_panel

theorem DynamicLatencyCounterexampleSearchReceipt.paid
    (R : DynamicLatencyCounterexampleSearchReceipt) :
    R.Paid :=
  ⟨R.no_candidate_valid_counterexamples_found,
    R.fixed_periodic_topology_and_clocks_declared_paid,
    R.parabolic_window_fast_setup_either_pays_action_or_all_output_price_paid,
    R.invalid_controls_break_recurrence_output_clock_signed_or_tail_guards_paid,
    R.no_nse_counterexample_claimed_from_dynamic_latency_panel_paid⟩

/-- Paid form of the smooth fixed-topology latency panel. -/
def SmoothLatencyPDEObligationFalsifierReceipt.Paid
    (R : SmoothLatencyPDEObligationFalsifierReceipt) : Prop :=
  R.candidateSmoothFixedTopologyEscapes = 0 ∧
    R.fixed_lp_bony_topology_declared_before_payoff ∧
      R.phase_angle_comparable_to_harmonic_gain_guard ∧
        R.parabolic_window_survival_requires_catalyst_or_commutator_price ∧
          R.moving_topology_posthoc_clock_hidden_catalyst_expectation_and_coupon_invalid ∧
            R.remaining_pde_theorem_or_finite_prefix_falsifier_declared ∧
              R.no_nse_counterexample_claimed_from_smooth_latency_panel

theorem SmoothLatencyPDEObligationFalsifierReceipt.paid
    (R : SmoothLatencyPDEObligationFalsifierReceipt) :
    R.Paid :=
  ⟨R.no_candidate_smooth_fixed_topology_escapes_found,
    R.fixed_lp_bony_topology_declared_before_payoff_paid,
    R.phase_angle_comparable_to_harmonic_gain_guard_paid,
    R.parabolic_window_survival_requires_catalyst_or_commutator_price_paid,
    R.moving_topology_posthoc_clock_hidden_catalyst_expectation_and_coupon_invalid_paid,
    R.remaining_pde_theorem_or_finite_prefix_falsifier_declared_paid,
    R.no_nse_counterexample_claimed_from_smooth_latency_panel_paid⟩

/-- Paid form of the concrete Fourier latency falsifier panel. -/
def ConcreteFourierLatencyFalsifierReceipt.Paid
    (R : ConcreteFourierLatencyFalsifierReceipt) : Prop :=
  R.boundedLipschitzCandidates = 0 ∧
    R.fixed_modes_topology_and_output_lanes_before_payoff ∧
      R.low_high_leray_symbol_bound_verified_rowwise ∧
        R.action_only_rows_require_unbounded_low_catalyst_gram ∧
          R.no_moving_posthoc_hidden_or_signed_controls ∧
            R.remaining_pde_symbol_theorem_or_falsifier_declared ∧
              R.no_nse_counterexample_claimed_from_concrete_fourier_panel

theorem ConcreteFourierLatencyFalsifierReceipt.paid
    (R : ConcreteFourierLatencyFalsifierReceipt) :
    R.Paid :=
  ⟨R.no_bounded_lipschitz_candidates_found,
    R.fixed_modes_topology_and_output_lanes_before_payoff_paid,
    R.low_high_leray_symbol_bound_verified_rowwise_paid,
    R.action_only_rows_require_unbounded_low_catalyst_gram_paid,
    R.no_moving_posthoc_hidden_or_signed_controls_paid,
    R.remaining_pde_symbol_theorem_or_falsifier_declared_paid,
    R.no_nse_counterexample_claimed_from_concrete_fourier_panel_paid⟩

/-- Time-bandwidth guard for posthoc phase snaps.

This is the uncertainty-principle import in the same anti-tautology language as
the latency panels.  It does not prove a Fourier uncertainty theorem.  It
records the exact receipt needed to reject "instant phase snap while staying in
the same dyadic LP shell" arguments: if the snap is localized in a short time
window, then either the declared bandwidth cap is large enough or a remainder /
off-shell bandwidth price must be charged. -/
structure TimeBandwidthPhaseSnapReceipt where
  timeWindow : Real
  declaredBandwidthCap : Real
  remainderBandwidthPrice : Real
  uncertaintyConstant : Real
  time_window_nonnegative : 0 ≤ timeWindow
  declared_bandwidth_cap_nonnegative : 0 ≤ declaredBandwidthCap
  remainder_bandwidth_price_nonnegative : 0 ≤ remainderBandwidthPrice
  uncertainty_constant_positive : 0 < uncertaintyConstant
  time_bandwidth_lower_bound :
    uncertaintyConstant ≤
      timeWindow * (declaredBandwidthCap + remainderBandwidthPrice)
  fixed_lp_shell_declared_before_snap : Prop
  remainder_or_cross_price_declared_before_payoff : Prop
  no_posthoc_phase_snap_without_bandwidth_price : Prop

/-- Quantitative remainder bandwidth price forced by the uncertainty guard. -/
theorem phase_snap_remainder_bandwidth_lower_bound
    (R : TimeBandwidthPhaseSnapReceipt) :
    R.uncertaintyConstant -
        R.timeWindow * R.declaredBandwidthCap ≤
      R.timeWindow * R.remainderBandwidthPrice := by
  have htb := R.time_bandwidth_lower_bound
  have hdist :
      R.timeWindow *
          (R.declaredBandwidthCap + R.remainderBandwidthPrice) =
        R.timeWindow * R.declaredBandwidthCap +
          R.timeWindow * R.remainderBandwidthPrice := by
    ring
  rw [hdist] at htb
  linarith

/-- Fixed-bandwidth zero-remainder phase snaps are impossible when the proposed
time window is shorter than the declared time-bandwidth product allows. -/
theorem no_zero_remainder_posthoc_phase_snap
    (R : TimeBandwidthPhaseSnapReceipt)
    (hfixed_bandwidth_too_small :
      R.timeWindow * R.declaredBandwidthCap < R.uncertaintyConstant)
    (hzero_remainder : R.remainderBandwidthPrice = 0) :
    False := by
  have hrem :
      R.uncertaintyConstant -
          R.timeWindow * R.declaredBandwidthCap ≤
        R.timeWindow * R.remainderBandwidthPrice :=
    phase_snap_remainder_bandwidth_lower_bound R
  rw [hzero_remainder] at hrem
  nlinarith

/-- A fixed event-section incidence receipt supplies the multiplicity-adjusted
reciprocal lift required by the event bridge. -/
def multiplicity_lift_of_event_section_incidence
    (L : EventRecurrencePriceLedger)
    (R : EventSectionIncidenceReceipt L) :
    EventMultiplicityAdjustedReciprocalLift L where
  eventReciprocalBudget := R.eventReciprocalBudget
  budget_nonnegative := R.event_reciprocal_budget_nonnegative
  event_reciprocal_prefix_le_budget :=
    R.event_reciprocal_prefix_le_effective_budget
  fixed_event_sections_before_payoff :=
    R.fixed_event_sections_before_payoff
  multiplicity_charged_before_payoff :=
    R.overlap_tax_charged_before_payoff

/-- Dynamic recurrence-price certificate at event granularity.

The reciprocal budget is over events.  A shell-level budget does not satisfy
`event_reciprocal_prefix_le_budget` unless it is separately lifted through the
event multiplicity map. -/
structure EventDynamicRecurrencePriceCertificate
    (L : EventRecurrencePriceLedger) where
  event_weight_positive : ∀ e : ℕ, 0 < L.eventWeight e
  price_budget_nonnegative : 0 ≤ L.priceBudget
  reciprocal_budget_nonnegative : 0 ≤ L.reciprocalBudget
  raw_recurrence_lower_envelope :
    ∀ e : ℕ,
      L.eventWeight e * (L.eventGain e) ^ (2 : Nat) ≤
        L.rawPrice e + L.recurrencePrice e
  raw_recurrence_prefix_le_budget :
    ∀ N : ℕ, eventRawRecurrencePricePrefix L N ≤ L.priceBudget
  event_reciprocal_prefix_le_budget :
    ∀ N : ℕ, eventReciprocalWeightPrefix L N ≤ L.reciprocalBudget
  duality : EventFiniteCauchyDualityField L

/-- Promote a pre-certificate to the full event bridge only after an explicit
event-multiplicity reciprocal lift is supplied. -/
def event_price_bridge_of_precertificate_and_multiplicity_lift
    (L : EventRecurrencePriceLedger)
    (P : EventDynamicRecurrencePricePrecertificate L)
    (R : EventMultiplicityAdjustedReciprocalLift L)
    (hbudget : L.reciprocalBudget = R.eventReciprocalBudget) :
    EventDynamicRecurrencePriceCertificate L where
  event_weight_positive := P.event_weight_positive
  price_budget_nonnegative := P.price_budget_nonnegative
  reciprocal_budget_nonnegative := by
    rw [hbudget]
    exact R.budget_nonnegative
  raw_recurrence_lower_envelope := P.raw_recurrence_lower_envelope
  raw_recurrence_prefix_le_budget := P.raw_recurrence_prefix_le_budget
  event_reciprocal_prefix_le_budget := by
    intro N
    rw [hbudget]
    exact R.event_reciprocal_prefix_le_budget N
  duality := P.duality

/-- Full event recurrence-price certificate from the Duhamel/Bernstein source
and an explicit event-multiplicity reciprocal lift.

This is the closure-facing constructor: the pointwise lower envelope is
derived from the Duhamel/Bernstein receipt, while the reciprocal budget is paid
over events rather than shell labels. -/
def event_price_bridge_of_duhamel_source_and_multiplicity_lift
    (L : EventRecurrencePriceLedger)
    (P : EventDynamicRecurrencePricePrecertificateSource L)
    (R : EventMultiplicityAdjustedReciprocalLift L)
    (hbudget : L.reciprocalBudget = R.eventReciprocalBudget) :
    EventDynamicRecurrencePriceCertificate L :=
  event_price_bridge_of_precertificate_and_multiplicity_lift
    L
    (event_precertificate_of_duhamel_bernstein_source L P)
    R
    hbudget

/-- Full event recurrence-price certificate from the Duhamel/Bernstein source
and a fixed event-section incidence receipt.

This is the sharpest source path currently available in the formal spine: the
event lower envelope, event sections, overlap/effective multiplicity, and
reciprocal event budget all remain attached until the final certificate. -/
def event_price_bridge_of_duhamel_source_and_section_incidence
    (L : EventRecurrencePriceLedger)
    (P : EventDynamicRecurrencePricePrecertificateSource L)
    (R : EventSectionIncidenceReceipt L)
    (hbudget : L.reciprocalBudget = R.eventReciprocalBudget) :
    EventDynamicRecurrencePriceCertificate L :=
  event_price_bridge_of_duhamel_source_and_multiplicity_lift
    L
    P
    (multiplicity_lift_of_event_section_incidence L R)
    hbudget

/-- The event certificate directly bounds the weighted-square event price prefix
by the declared finite price budget. -/
theorem event_weighted_gain_price_prefix_le_budget
    (L : EventRecurrencePriceLedger)
    (C : EventDynamicRecurrencePriceCertificate L)
    (N : ℕ) :
    eventWeightedGainPricePrefix L N ≤ L.priceBudget := by
  have hprefix :
      eventWeightedGainPricePrefix L N ≤
        eventRawRecurrencePricePrefix L N :=
    ns_prefix_sum_le_of_pointwise
      (fun e : ℕ => L.eventWeight e * (L.eventGain e) ^ (2 : Nat))
      (fun e : ℕ => L.rawPrice e + L.recurrencePrice e)
      C.raw_recurrence_lower_envelope
      N
  exact hprefix.trans (C.raw_recurrence_prefix_le_budget N)

/-- The event certificate directly bounds the reciprocal event-weight prefix by
the declared reciprocal budget. -/
theorem event_reciprocal_weight_prefix_le_budget
    (L : EventRecurrencePriceLedger)
    (C : EventDynamicRecurrencePriceCertificate L)
    (N : ℕ) :
    eventReciprocalWeightPrefix L N ≤ L.reciprocalBudget :=
  C.event_reciprocal_prefix_le_budget N

def edge_gain_dual_norm_certificate_of_event_price_bridge
    (L : EventRecurrencePriceLedger)
    (C : EventDynamicRecurrencePriceCertificate L) :
    EdgeGainDualNormPrefixCertificate L.toDualNormLedger where
  weighted_price_nonnegative := by
    intro e
    exact mul_nonneg
      (le_of_lt (C.event_weight_positive e))
      (sq_nonneg (L.eventGain e))
  inverse_weight_nonnegative := by
    intro e
    exact div_nonneg zero_le_one (le_of_lt (C.event_weight_positive e))
  price_budget_nonnegative := C.price_budget_nonnegative
  dual_budget_nonnegative := C.reciprocal_budget_nonnegative
  price_prefix_le_budget := by
    intro N
    exact event_weighted_gain_price_prefix_le_budget L C N
  inverse_prefix_le_budget :=
    event_reciprocal_weight_prefix_le_budget L C
  weighted_cauchy_prefix := by
    intro N
    simpa [eventGainPrefix, eventWeightedGainPricePrefix,
      eventReciprocalWeightPrefix, EventRecurrencePriceLedger.toDualNormLedger,
      edgeGainPrefix, edgePricePrefix, edgeInverseWeightPrefix]
      using C.duality.finite_cauchy_duality N

/-- Budget product bound for every finite event-gain prefix. -/
theorem event_gain_prefix_sq_le_budget_product
    (L : EventRecurrencePriceLedger)
    (C : EventDynamicRecurrencePriceCertificate L)
    (N : ℕ) :
    (eventGainPrefix L N) ^ (2 : Nat) ≤
      L.priceBudget * L.reciprocalBudget := by
  have Cdual :
      EdgeGainDualNormPrefixCertificate L.toDualNormLedger :=
    edge_gain_dual_norm_certificate_of_event_price_bridge L C
  simpa [EventRecurrencePriceLedger.toDualNormLedger, eventGainPrefix]
    using edge_gain_prefix_sq_le_budget_product L.toDualNormLedger Cdual N

/-- Divergence of total event gain across finite prefixes. -/
def EventGainPrefixDiverges
    (L : EventRecurrencePriceLedger) : Prop :=
  ∀ B : Real, ∃ N : ℕ, B < eventGainPrefix L N

/-- A supplied block construction witnessing an event-level recurrence
falsifier.

This is the proof-facing shape of the Phase 5IX accounting result.  It does
not assert that a PDE cascade has been constructed.  It says: if a fixed event
decomposition admits finite blocks whose gains embed into event prefixes while
their charged block prices stay under a finite budget, then the event-gain
prefix diverges.  Such a block schedule is exactly the obstruction to a
claimed recurrence-price closure unless the reciprocal event budget is
summable after multiplicity. -/
structure EventBlockFalsifierSchedule
    (L : EventRecurrencePriceLedger) where
  blockGain : ℕ → Real
  blockPrice : ℕ → Real
  blockPriceBudget : Real
  block_price_prefix_le_budget :
    ∀ M : ℕ, nsPrefixSum blockPrice M ≤ blockPriceBudget
  block_gain_prefix_diverges :
    ∀ B : Real, ∃ M : ℕ, B < nsPrefixSum blockGain M
  block_gain_embeds_in_event_prefix :
    ∀ M : ℕ, ∃ N : ℕ,
      nsPrefixSum blockGain M ≤ eventGainPrefix L N

/-- A block falsifier schedule forces event-gain prefix divergence. -/
theorem event_gain_prefix_diverges_of_block_falsifier_schedule
    (L : EventRecurrencePriceLedger)
    (F : EventBlockFalsifierSchedule L) :
    EventGainPrefixDiverges L := by
  intro B
  rcases F.block_gain_prefix_diverges B with ⟨M, hM⟩
  rcases F.block_gain_embeds_in_event_prefix M with ⟨N, hN⟩
  exact ⟨N, lt_of_lt_of_le hM hN⟩

/-- Event-level recurrence pricing rules out a divergent event-gain prefix. -/
theorem no_divergent_event_gain_prefix_of_event_price_bridge
    (L : EventRecurrencePriceLedger)
    (C : EventDynamicRecurrencePriceCertificate L) :
    ¬ EventGainPrefixDiverges L := by
  intro hdiv
  have hdual :
      ¬ EdgeGainPrefixDiverges L.toDualNormLedger :=
    no_divergent_edge_gain_of_dual_norm_prefix_certificate
      L.toDualNormLedger
      (edge_gain_dual_norm_certificate_of_event_price_bridge L C)
  apply hdual
  intro B
  rcases hdiv B with ⟨N, hN⟩
  exact ⟨N, by
    simpa [EventRecurrencePriceLedger.toDualNormLedger, eventGainPrefix,
      edgeGainPrefix] using hN⟩

/-- Duhamel/Bernstein lower-envelope plus fixed event-section incidence rules
out a divergent event-gain prefix.

This is the dynamic recurrence price in its current non-tautological source
form: a closure may cite this only after supplying the Duhamel/Bernstein source
receipt and the event-multiplicity incidence receipt for the same ledger. -/
theorem no_divergent_event_gain_prefix_of_duhamel_source_and_section_incidence
    (L : EventRecurrencePriceLedger)
    (P : EventDynamicRecurrencePricePrecertificateSource L)
    (R : EventSectionIncidenceReceipt L)
    (hbudget : L.reciprocalBudget = R.eventReciprocalBudget) :
    ¬ EventGainPrefixDiverges L :=
  no_divergent_event_gain_prefix_of_event_price_bridge
    L
    (event_price_bridge_of_duhamel_source_and_section_incidence
      L P R hbudget)

/-- Duhamel/Bernstein lower-envelope plus fixed event-section incidence gives
the finite-prefix budget product bound directly. -/
theorem event_gain_prefix_sq_le_budget_product_of_duhamel_source_and_section_incidence
    (L : EventRecurrencePriceLedger)
    (P : EventDynamicRecurrencePricePrecertificateSource L)
    (R : EventSectionIncidenceReceipt L)
    (hbudget : L.reciprocalBudget = R.eventReciprocalBudget)
    (N : ℕ) :
    (eventGainPrefix L N) ^ (2 : Nat) ≤
      L.priceBudget * L.reciprocalBudget :=
  event_gain_prefix_sq_le_budget_product
    L
    (event_price_bridge_of_duhamel_source_and_section_incidence
      L P R hbudget)
    N

/-- Therefore a supplied block-falsifier schedule is incompatible with a full
event recurrence-price bridge certificate. -/
theorem no_event_price_bridge_certificate_of_block_falsifier_schedule
    (L : EventRecurrencePriceLedger)
    (F : EventBlockFalsifierSchedule L) :
    ¬ EventDynamicRecurrencePriceCertificate L := by
  intro C
  exact no_divergent_event_gain_prefix_of_event_price_bridge
    L C (event_gain_prefix_diverges_of_block_falsifier_schedule L F)

/-- Unbounded event reciprocal prefixes mean there is no uniform reciprocal
budget over events. -/
def EventReciprocalPrefixUnbounded
    (L : EventRecurrencePriceLedger) : Prop :=
  ∀ B : Real, ∃ N : ℕ, B < eventReciprocalWeightPrefix L N

theorem no_uniform_event_reciprocal_budget_of_unbounded_prefix
    (L : EventRecurrencePriceLedger)
    (hunbounded : EventReciprocalPrefixUnbounded L) :
    ¬ ∃ B : Real,
      ∀ N : ℕ, eventReciprocalWeightPrefix L N ≤ B := by
  intro hbudget
  rcases hbudget with ⟨B, hB⟩
  rcases hunbounded B with ⟨N, hN⟩
  exact not_lt_of_ge (hB N) hN

/-- Falsifier for a recurrence-price story that has price-side control and a
finite-duality expression but no event reciprocal budget strong enough to stop
an event-gain cascade. -/
structure MissingEventReciprocalBudgetFalsifier where
  ledger : EventRecurrencePriceLedger
  event_weight_positive : ∀ e : ℕ, 0 < ledger.eventWeight e
  raw_recurrence_lower_envelope :
    ∀ e : ℕ,
      ledger.eventWeight e * (ledger.eventGain e) ^ (2 : Nat) ≤
        ledger.rawPrice e + ledger.recurrencePrice e
  raw_recurrence_prefix_le_budget :
    ∀ N : ℕ, eventRawRecurrencePricePrefix ledger N ≤ ledger.priceBudget
  duality : EventFiniteCauchyDualityField ledger
  divergent_event_gain_prefix : EventGainPrefixDiverges ledger

theorem no_event_price_bridge_certificate_of_missing_reciprocal_budget
    (F : MissingEventReciprocalBudgetFalsifier) :
    ¬ EventDynamicRecurrencePriceCertificate F.ledger := by
  intro C
  exact no_divergent_event_gain_prefix_of_event_price_bridge
    F.ledger C F.divergent_event_gain_prefix

/-- Shell-level reciprocal budget.  This budgets shell labels, not event
multiplicity. -/
structure ShellLevelReciprocalBudget where
  shellOfEvent : ℕ → ℕ
  shellWeight : ℕ → Real
  shellBudget : Real
  shell_weight_positive : ∀ j : ℕ, 0 < shellWeight j
  shell_reciprocal_prefix_le_budget :
    ∀ N : ℕ,
      nsPrefixSum (fun j : ℕ => 1 / shellWeight j) N ≤ shellBudget

/-- Falsifier for the shell-only mistake: the event weights may be inherited
from shell weights, and the shell-label reciprocal budget may be finite, while
the event reciprocal prefixes are still unbounded because multiplicity was not
charged. -/
structure ShellOnlyReciprocalBudgetFalsifier
    extends MissingEventReciprocalBudgetFalsifier where
  shellBudget : ShellLevelReciprocalBudget
  event_weight_is_shell_weight :
    ∀ e : ℕ,
      ledger.eventWeight e =
        shellBudget.shellWeight (shellBudget.shellOfEvent e)
  event_reciprocal_prefix_unbounded :
    EventReciprocalPrefixUnbounded ledger

theorem shell_only_budget_does_not_supply_event_reciprocal_budget
    (F : ShellOnlyReciprocalBudgetFalsifier) :
    ¬ ∃ B : Real,
      ∀ N : ℕ, eventReciprocalWeightPrefix F.ledger N ≤ B :=
  no_uniform_event_reciprocal_budget_of_unbounded_prefix
    F.ledger F.event_reciprocal_prefix_unbounded

theorem no_event_price_bridge_certificate_of_shell_only_budget
    (F : ShellOnlyReciprocalBudgetFalsifier) :
    ¬ EventDynamicRecurrencePriceCertificate F.ledger :=
  no_event_price_bridge_certificate_of_missing_reciprocal_budget
    F.toMissingEventReciprocalBudgetFalsifier

/-- Exact PDE-side obligations that remain open after the event-level bridge is
formalized.  These are assumptions a future analysis must prove, not estimates
proved in this file. -/
structure EventRecurrencePricePDEObligation where
  event_decomposition_fixed_before_payoff : Prop
  event_weights_declared_before_payoff : Prop
  preparation_windows_declared_before_payoff : Prop
  resource_overlap_measured_before_payoff : Prop
  raw_price_declared_before_payoff : Prop
  recurrence_price_declared_before_payoff : Prop
  raw_recurrence_lower_envelope_proved : Prop
  reciprocal_budget_over_events_proved : Prop
  overlap_adjusted_effective_multiplicity_proved : Prop
  finite_cauchy_duality_over_events_proved : Prop
  shell_multiplicity_lift_proved_if_using_shell_weights : Prop
  raw_lp_bony_underpricing_obstruction_addressed : Prop
  super_sqrt_gain_or_predeclared_log_reserve_proved : Prop
  fractional_log_gain_adversary_decoupling_ruled_out_or_constructed : Prop
  reserve_gain_decoupling_ruled_out_or_constructed : Prop
  matrix_reserve_gain_decoupling_ruled_out_or_constructed : Prop
  setup_latency_execution_cost_ruled_out_or_constructed : Prop
  dynamic_latency_counterexample_ruled_out_or_constructed : Prop
  smooth_latency_pde_obligation_ruled_out_or_constructed : Prop
  concrete_fourier_latency_falsifier_ruled_out_or_constructed : Prop

/-- Satisfaction predicate for the PDE-side event recurrence obligations.

The obligation record names the predeclared topology, multiplicity, latency,
and decoupling duties.  This predicate is the load-bearing version: a bridge
that imports the obligation must supply all duties before it can use the
event-level recurrence price in a global closure. -/
def EventRecurrencePricePDEObligationSatisfied
    (O : EventRecurrencePricePDEObligation) : Prop :=
  let concreteFourierLatencyFalsifierRuledOut :=
    O.concrete_fourier_latency_falsifier_ruled_out_or_constructed
  O.event_decomposition_fixed_before_payoff ∧
    O.event_weights_declared_before_payoff ∧
      O.preparation_windows_declared_before_payoff ∧
        O.resource_overlap_measured_before_payoff ∧
          O.raw_price_declared_before_payoff ∧
            O.recurrence_price_declared_before_payoff ∧
              O.raw_recurrence_lower_envelope_proved ∧
                O.reciprocal_budget_over_events_proved ∧
                  O.overlap_adjusted_effective_multiplicity_proved ∧
                    O.finite_cauchy_duality_over_events_proved ∧
                      O.shell_multiplicity_lift_proved_if_using_shell_weights ∧
                        O.raw_lp_bony_underpricing_obstruction_addressed ∧
                          O.super_sqrt_gain_or_predeclared_log_reserve_proved ∧
                            O.fractional_log_gain_adversary_decoupling_ruled_out_or_constructed ∧
                              O.reserve_gain_decoupling_ruled_out_or_constructed ∧
                                O.matrix_reserve_gain_decoupling_ruled_out_or_constructed ∧
                                  O.setup_latency_execution_cost_ruled_out_or_constructed ∧
                                    O.dynamic_latency_counterexample_ruled_out_or_constructed ∧
                                      O.smooth_latency_pde_obligation_ruled_out_or_constructed ∧
                                        concreteFourierLatencyFalsifierRuledOut

/-- Named ways the event recurrence-price PDE obligation can fail.

The surface is branch-wise on purpose: downstream bridges should not collapse
the event recurrence gap into an opaque
`¬ EventRecurrencePricePDEObligationSatisfied`.  Each constructor names the
analytic duty still missing; it does not prove or import that duty. -/
inductive EventRecurrencePricePDEObligationFalsifier
    (O : EventRecurrencePricePDEObligation) : Type where
  | eventDecompositionNotFixed :
      ¬ O.event_decomposition_fixed_before_payoff →
        EventRecurrencePricePDEObligationFalsifier O
  | eventWeightsUndeclared :
      ¬ O.event_weights_declared_before_payoff →
        EventRecurrencePricePDEObligationFalsifier O
  | preparationWindowsUndeclared :
      ¬ O.preparation_windows_declared_before_payoff →
        EventRecurrencePricePDEObligationFalsifier O
  | resourceOverlapUnmeasured :
      ¬ O.resource_overlap_measured_before_payoff →
        EventRecurrencePricePDEObligationFalsifier O
  | rawPriceUndeclared :
      ¬ O.raw_price_declared_before_payoff →
        EventRecurrencePricePDEObligationFalsifier O
  | recurrencePriceUndeclared :
      ¬ O.recurrence_price_declared_before_payoff →
        EventRecurrencePricePDEObligationFalsifier O
  | rawRecurrenceLowerEnvelopeMissing :
      ¬ O.raw_recurrence_lower_envelope_proved →
        EventRecurrencePricePDEObligationFalsifier O
  | reciprocalEventBudgetMissing :
      ¬ O.reciprocal_budget_over_events_proved →
        EventRecurrencePricePDEObligationFalsifier O
  | effectiveMultiplicityMissing :
      ¬ O.overlap_adjusted_effective_multiplicity_proved →
        EventRecurrencePricePDEObligationFalsifier O
  | finiteCauchyDualityMissing :
      ¬ O.finite_cauchy_duality_over_events_proved →
        EventRecurrencePricePDEObligationFalsifier O
  | shellMultiplicityLiftMissing :
      ¬ O.shell_multiplicity_lift_proved_if_using_shell_weights →
        EventRecurrencePricePDEObligationFalsifier O
  | rawLpBonyUnderpricingUnaddressed :
      ¬ O.raw_lp_bony_underpricing_obstruction_addressed →
        EventRecurrencePricePDEObligationFalsifier O
  | superSqrtOrLogReserveMissing :
      ¬ O.super_sqrt_gain_or_predeclared_log_reserve_proved →
        EventRecurrencePricePDEObligationFalsifier O
  | fractionalLogAdversaryUndecided :
      ¬ O.fractional_log_gain_adversary_decoupling_ruled_out_or_constructed →
        EventRecurrencePricePDEObligationFalsifier O
  | reserveGainDecouplingUndecided :
      ¬ O.reserve_gain_decoupling_ruled_out_or_constructed →
        EventRecurrencePricePDEObligationFalsifier O
  | matrixReserveGainDecouplingUndecided :
      ¬ O.matrix_reserve_gain_decoupling_ruled_out_or_constructed →
        EventRecurrencePricePDEObligationFalsifier O
  | setupLatencyExecutionCostUndecided :
      ¬ O.setup_latency_execution_cost_ruled_out_or_constructed →
        EventRecurrencePricePDEObligationFalsifier O
  | dynamicLatencyCounterexampleUndecided :
      ¬ O.dynamic_latency_counterexample_ruled_out_or_constructed →
        EventRecurrencePricePDEObligationFalsifier O
  | smoothLatencyPDEObligationUndecided :
      ¬ O.smooth_latency_pde_obligation_ruled_out_or_constructed →
        EventRecurrencePricePDEObligationFalsifier O
  | concreteFourierLatencyFalsifierUndecided :
      ¬ O.concrete_fourier_latency_falsifier_ruled_out_or_constructed →
        EventRecurrencePricePDEObligationFalsifier O

/-- A satisfied event recurrence-price PDE obligation excludes each named
failure branch. -/
theorem no_event_recurrence_price_pde_obligation_falsifier
    (O : EventRecurrencePricePDEObligation)
    (hO : EventRecurrencePricePDEObligationSatisfied O)
    (F : EventRecurrencePricePDEObligationFalsifier O) :
    False := by
  dsimp [EventRecurrencePricePDEObligationSatisfied] at hO
  rcases hO with
    ⟨hdecomposition, hweights, hpreparation, hoverlap, hrawPrice,
      hrecurrencePrice, hlowerEnvelope, hreciprocalBudget,
      heffectiveMultiplicity, hduality, hshellLift, hrawLpBony,
      hsuperSqrtOrReserve, hfractionalLog, hreserveGain, hmatrixReserveGain,
      hsetupLatency, hdynamicLatency, hsmoothLatency, hconcreteFourier⟩
  cases F with
  | eventDecompositionNotFixed h => exact h hdecomposition
  | eventWeightsUndeclared h => exact h hweights
  | preparationWindowsUndeclared h => exact h hpreparation
  | resourceOverlapUnmeasured h => exact h hoverlap
  | rawPriceUndeclared h => exact h hrawPrice
  | recurrencePriceUndeclared h => exact h hrecurrencePrice
  | rawRecurrenceLowerEnvelopeMissing h => exact h hlowerEnvelope
  | reciprocalEventBudgetMissing h => exact h hreciprocalBudget
  | effectiveMultiplicityMissing h => exact h heffectiveMultiplicity
  | finiteCauchyDualityMissing h => exact h hduality
  | shellMultiplicityLiftMissing h => exact h hshellLift
  | rawLpBonyUnderpricingUnaddressed h => exact h hrawLpBony
  | superSqrtOrLogReserveMissing h => exact h hsuperSqrtOrReserve
  | fractionalLogAdversaryUndecided h => exact h hfractionalLog
  | reserveGainDecouplingUndecided h => exact h hreserveGain
  | matrixReserveGainDecouplingUndecided h => exact h hmatrixReserveGain
  | setupLatencyExecutionCostUndecided h => exact h hsetupLatency
  | dynamicLatencyCounterexampleUndecided h => exact h hdynamicLatency
  | smoothLatencyPDEObligationUndecided h => exact h hsmoothLatency
  | concreteFourierLatencyFalsifierUndecided h => exact h hconcreteFourier

end

end ZtareProofs.NS
