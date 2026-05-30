import Mathlib.Tactic
import ZtareProofs.ns_clay_closure_bridge
import ZtareProofs.ns_low_high_lipschitz_reserve_adapter
import ZtareProofs.ns_low_high_profile_lipschitz_composition
import ZtareProofs.ns_profile_lipschitz_clay_bridge

/-!
# Phase-latency to Clay closure bridge

This file is a small composition receipt.  The existing
`PhaseLatencyControlGramianReceipt` supplies the fixed-topology parabolic
phase-reach law, and
`no_phase_latency_control_gramian_escape_under_lipschitz_reserve` already
shows that an unbounded harmonic schedule cannot embed in a bounded
low-frequency Lipschitz no-survivor reserve.

The Clay-facing handoff below is deliberately conditional: the no-escape
falsifier can supply the existing Track B critical-control interface only
through the already declared low-frequency Lipschitz certificate, and global
regularity still requires an explicit continuation criterion.
-/

namespace ZtareProofs.NS

universe u

noncomputable section

/-- Fixed phase-latency capacity source before no-survivor pricing is imported.

This is the source object that phase-capacity and flat-torus clock arguments may
use pre-closure: it carries the generated Lipschitz ledger, the fixed Gramian
receipt, and the embedding of the control budget into the Lipschitz ledger, but
it carries no `FullLedgerNoSurvivor` consequence. -/
structure PhaseLatencyLipschitzCapacitySource where
  ledger : LowFrequencyLipschitzLedger
  phase : PhaseLatencyControlGramianReceipt
  phase_control_embeds_in_lipschitz_ledger :
    forall n : Nat, phase.controlBudget n <= ledger.lipschitzCost n

/-- Fixed phase-latency receipt embedded in a bounded no-survivor Lipschitz
reserve.

The only new data is the embedding of the Gramian control budget into the
predeclared low-frequency Lipschitz ledger.  All pricing, no-survivor, and
critical-control content is supplied by existing interfaces. -/
structure PhaseLatencyLipschitzReserveBridge where
  ledger : LowFrequencyLipschitzLedger
  certificate : LowFrequencyLipschitzAuditedControlCertificate ledger
  phase : PhaseLatencyControlGramianReceipt
  no_survivor :
    forall n : Nat, FullLedgerNoSurvivor (ledger.block n)
  phase_control_embeds_in_lipschitz_ledger :
    forall n : Nat, phase.controlBudget n <= ledger.lipschitzCost n

/-- Forget the post-no-survivor fields of a phase-latency reserve bridge. -/
def PhaseLatencyLipschitzReserveBridge.toPhaseLatencyCapacitySource
    (B : PhaseLatencyLipschitzReserveBridge) :
    PhaseLatencyLipschitzCapacitySource where
  ledger := B.ledger
  phase := B.phase
  phase_control_embeds_in_lipschitz_ledger :=
    B.phase_control_embeds_in_lipschitz_ledger

/-- The harmonic/dyadic escape claim ruled out by the reserve bridge.

For every fixed budget `C`, some shell demands more phase-latency control than
`C` can buy through the fixed parabolic Gramian capacity. -/
def HarmonicDyadicPhaseLatencyEscape
    (B : PhaseLatencyLipschitzReserveBridge) : Prop :=
  forall C : Real, exists j : Nat,
    (C * B.phase.gramianConstant) * B.phase.harmonicIndex j <
      B.phase.angleConstant * B.phase.kNorm j

/-- Bounded no-survivor low-frequency Lipschitz reserve rules out the
harmonic/dyadic phase-latency escape. -/
theorem no_harmonic_dyadic_phase_latency_escape_under_lipschitz_reserve
    (B : PhaseLatencyLipschitzReserveBridge) :
    Not (HarmonicDyadicPhaseLatencyEscape B) := by
  intro hescape
  exact
    no_phase_latency_control_gramian_escape_under_audited_lipschitz_reserve
      B.ledger
      B.certificate
      B.phase
      B.no_survivor
      B.phase_control_embeds_in_lipschitz_ledger
      hescape

/-- The same bounded reserve supplies the existing Track B critical-control
interface.  This is not a continuation theorem. -/
theorem critical_control_of_phase_latency_lipschitz_reserve
    (B : PhaseLatencyLipschitzReserveBridge) :
    B.ledger.U.criticalControl := by
  exact
    critical_control_of_audited_low_frequency_lipschitz_certificate
      B.ledger
      B.certificate
      B.no_survivor

/-- Critical-control Clay handoff: global regularity follows only after the
standard continuation criterion is supplied. -/
theorem global_regular_of_phase_latency_lipschitz_reserve_with_continuation
    (B : PhaseLatencyLipschitzReserveBridge)
    (K : NSContinuationCriterion)
    (hsmooth : B.ledger.U.smoothOnLocalInterval)
    (henergy : B.ledger.U.finiteEnergyInequality) :
    B.ledger.U.globalRegular := by
  exact
    K.continues
      B.ledger.U
      hsmooth
      henergy
      (critical_control_of_phase_latency_lipschitz_reserve B)

/-- Existing Track B critical closure, exposed here to make the continuation
dependency explicit at the phase-latency handoff boundary. -/
theorem global_regular_of_existing_trackB_critical_closure_if_supplied
    (O : TrackBClayClosureObligation)
    (u0 : SmoothNSInitialData)
    (hsmooth : (O.evolution_of_initial_data u0).smoothOnLocalInterval)
    (henergy : (O.evolution_of_initial_data u0).finiteEnergyInequality) :
    (O.evolution_of_initial_data u0).globalRegular := by
  exact global_regular_of_trackB_clay_closure O u0 hsmooth henergy

/-- Existing Track B H1/enstrophy closure, likewise requiring its specialized
continuation criterion rather than deriving it from phase-latency pricing. -/
theorem global_regular_of_existing_trackB_enstrophy_closure_if_supplied
    (O : TrackBSelfTaxEnstrophyClayClosureObligation)
    (u0 : SmoothNSInitialData)
    (hsmooth : (O.evolution_of_initial_data u0).smoothOnLocalInterval)
    (henergy : (O.evolution_of_initial_data u0).finiteEnergyInequality) :
    (O.evolution_of_initial_data u0).globalRegular := by
  exact
    global_regular_of_trackB_self_tax_enstrophy_clay_closure
      O
      u0
      hsmooth
      henergy

/-- Source-first phase-latency reserve for a generated Track B
profile/Lipschitz ledger.

The source object carries only the genuinely new phase receipt and its
embedding into the generated low-frequency Lipschitz ledger.  The audited
Lipschitz certificate and no-survivor family are derived by the projection
below from the existing profile/Lipschitz closure receipts, so a final GP216
receipt cannot swap in a detached reserve bridge with the same scalar ledger
but unrelated provenance. -/
structure PhaseLatencyProfileLipschitzReserveSource
    (O : TrackBProfileLipschitzControlObligation)
    (u0 : SmoothNSInitialData) where
  phase : PhaseLatencyControlGramianReceipt
  phase_control_embeds_in_generated_lipschitz_ledger :
    forall n : Nat,
      phase.controlBudget n <=
        (trackBGeneratedLowFrequencyLipschitzLedger O u0).lipschitzCost n

/-- Build a profile/Lipschitz phase-reserve source from a concrete Fourier
latency symbol receipt on the generated Lipschitz ledger.

This is the source-preserving bridge from the Fourier latency falsifier lane
to the control-Gramian phase lane: the Fourier receipt pays the generated
Lipschitz embedding, while the caller must identify the phase `controlBudget`
with the same required low-Lipschitz cost. -/
def phase_latency_profile_lipschitz_reserve_source_of_concrete_fourier_symbol
    (O : TrackBProfileLipschitzControlObligation)
    (u0 : SmoothNSInitialData)
    (phase : PhaseLatencyControlGramianReceipt)
    (S :
      ConcreteFourierLatencySymbolReceipt
        (trackBGeneratedLowFrequencyLipschitzLedger O u0))
    (control_budget_matches_required_lipschitz :
      ∀ n : ℕ, phase.controlBudget n = S.requiredLowLipschitz n) :
    PhaseLatencyProfileLipschitzReserveSource O u0 where
  phase := phase
  phase_control_embeds_in_generated_lipschitz_ledger := by
    intro n
    rw [control_budget_matches_required_lipschitz n]
    exact S.required_lipschitz_embeds_in_lipschitz_ledger n

/-- Projection from the source-first profile/Lipschitz phase receipt to the
legacy reserve bridge.

This is the only way GP216 should obtain a phase-latency Lipschitz reserve:
the ledger, audited certificate, and no-survivor family are all the generated
profile/Lipschitz ones by construction. -/
def PhaseLatencyProfileLipschitzReserveSource.toPhaseLatencyLipschitzReserveBridge
    {O : TrackBProfileLipschitzControlObligation}
    {u0 : SmoothNSInitialData}
    (S : PhaseLatencyProfileLipschitzReserveSource O u0) :
    PhaseLatencyLipschitzReserveBridge where
  ledger := trackBGeneratedLowFrequencyLipschitzLedger O u0
  certificate := trackBGeneratedLowFrequencyLipschitzAuditedCertificate O u0
  phase := S.phase
  no_survivor :=
    generated_lipschitz_blocks_no_survivor_of_trackB_profile_closure O u0
  phase_control_embeds_in_lipschitz_ledger :=
    S.phase_control_embeds_in_generated_lipschitz_ledger

/-- Projection from the source-first profile/Lipschitz phase receipt to the
pre-no-survivor capacity source.

This is the projection GP216 phase-capacity code should use while proving the
closure corridor: it does not import generated no-survivor from the Track B
profile/Lipschitz endpoint. -/
def PhaseLatencyProfileLipschitzReserveSource.toPhaseLatencyCapacitySource
    {O : TrackBProfileLipschitzControlObligation}
    {u0 : SmoothNSInitialData}
    (S : PhaseLatencyProfileLipschitzReserveSource O u0) :
    PhaseLatencyLipschitzCapacitySource where
  ledger := trackBGeneratedLowFrequencyLipschitzLedger O u0
  phase := S.phase
  phase_control_embeds_in_lipschitz_ledger :=
    S.phase_control_embeds_in_generated_lipschitz_ledger

/-- Falsifier surface for a profile/Lipschitz phase-reserve source.

The two named failures are the source-level ways a generated phase bridge can
be fake: its derived bridge is not actually on the generated ledger, or its
phase-control entries do not embed in that generated ledger. -/
inductive PhaseLatencyProfileLipschitzReserveSourceFalsifier
    {O : TrackBProfileLipschitzControlObligation}
    {u0 : SmoothNSInitialData}
    (S : PhaseLatencyProfileLipschitzReserveSource O u0) : Type where
  | generatedLedgerMismatch :
      S.toPhaseLatencyLipschitzReserveBridge.ledger ≠
        trackBGeneratedLowFrequencyLipschitzLedger O u0 →
        PhaseLatencyProfileLipschitzReserveSourceFalsifier S
  | phaseControlEmbeddingFailure
      (n : Nat) :
      ¬ S.phase.controlBudget n <=
        (trackBGeneratedLowFrequencyLipschitzLedger O u0).lipschitzCost n →
        PhaseLatencyProfileLipschitzReserveSourceFalsifier S

/-- A profile/Lipschitz phase-reserve source excludes generated-ledger and
phase-control embedding failures by construction. -/
theorem no_phase_latency_profile_lipschitz_reserve_source_falsifier
    {O : TrackBProfileLipschitzControlObligation}
    {u0 : SmoothNSInitialData}
    (S : PhaseLatencyProfileLipschitzReserveSource O u0)
    (F : PhaseLatencyProfileLipschitzReserveSourceFalsifier S) :
    False := by
  cases F with
  | generatedLedgerMismatch hbad =>
      exact hbad rfl
  | phaseControlEmbeddingFailure n hbad =>
      exact hbad
        (S.phase_control_embeds_in_generated_lipschitz_ledger n)

/-- Phase-latency escape attempt inside the full profile + Lipschitz closure.

The phase-control budget must embed in the generated evolution's fixed
low-frequency Lipschitz ledger before the harmonic/dyadic escape is scored. -/
structure PhaseLatencyProfileLipschitzEscapeAttempt
    (O : TrackBProfileLipschitzControlObligation)
    (u0 : SmoothNSInitialData) where
  phase : PhaseLatencyControlGramianReceipt
  phase_control_embeds_in_generated_lipschitz_ledger :
    forall n : Nat,
      phase.controlBudget n <=
        (O.lipschitz_bridge.ledger_of_evolution
          (O.evolution_of_initial_data u0)).lipschitzCost n
  harmonic_dyadic_escape :
    forall C : Real, exists j : Nat,
      (C * phase.gramianConstant) * phase.harmonicIndex j <
        phase.angleConstant * phase.kNorm j

/-- Source-level no-escape theorem for a profile/Lipschitz phase-reserve
source.

This names the canonical route from the source-first generated profile
reserve object to the legacy bounded-reserve theorem. Downstream proofs should
use this theorem instead of reconstructing a detached
`PhaseLatencyLipschitzReserveBridge` locally. -/
theorem no_harmonic_dyadic_phase_latency_escape_of_profile_lipschitz_reserve_source
    {O : TrackBProfileLipschitzControlObligation}
    {u0 : SmoothNSInitialData}
    (S : PhaseLatencyProfileLipschitzReserveSource O u0) :
    ¬ HarmonicDyadicPhaseLatencyEscape
      S.toPhaseLatencyLipschitzReserveBridge :=
  no_harmonic_dyadic_phase_latency_escape_under_lipschitz_reserve
    S.toPhaseLatencyLipschitzReserveBridge

/-- The full profile + Lipschitz closure rules out the harmonic/dyadic
phase-latency escape once the phase-control budget embeds in the generated
Lipschitz ledger.

This is the top-level falsifier form of Phase 5JO: profile pricing supplies
no-survivor blocks, the Lipschitz bridge supplies the reserve ledger, and the
phase-latency receipt forbids unbounded harmonic preparation under a finite
macroscopic budget. -/
theorem no_phase_latency_escape_of_profile_lipschitz_closure
    (O : TrackBProfileLipschitzControlObligation)
    (u0 : SmoothNSInitialData)
    (A : PhaseLatencyProfileLipschitzEscapeAttempt O u0) :
    False := by
  let S : PhaseLatencyProfileLipschitzReserveSource O u0 :=
    { phase := A.phase
      phase_control_embeds_in_generated_lipschitz_ledger :=
        A.phase_control_embeds_in_generated_lipschitz_ledger }
  have hescape :
      HarmonicDyadicPhaseLatencyEscape
        S.toPhaseLatencyLipschitzReserveBridge := by
    simpa [S,
      PhaseLatencyProfileLipschitzReserveSource.toPhaseLatencyLipschitzReserveBridge]
      using A.harmonic_dyadic_escape
  exact
    no_harmonic_dyadic_phase_latency_escape_of_profile_lipschitz_reserve_source
      S hescape

/-- Integrated phase-alignment escape attempt inside the full profile +
Lipschitz closure.

This is the control-energy counterpart of
`PhaseLatencyProfileLipschitzEscapeAttempt`: every phase-alignment energy entry
must embed in the generated low-frequency Lipschitz ledger before a claimed
unbounded integrated Gramian schedule is scored. -/
structure PhaseAlignmentProfileLipschitzEscapeAttempt
    (O : TrackBProfileLipschitzControlObligation)
    (u0 : SmoothNSInitialData) where
  phase : ℕ → PhaseAlignmentControlGramianReceipt
  control_energy_embeds_in_generated_lipschitz_ledger :
    forall n : Nat,
      (phase n).controlEnergy <=
        (O.lipschitz_bridge.ledger_of_evolution
          (O.evolution_of_initial_data u0)).lipschitzCost n
  integrated_phase_alignment_escape :
    forall B : Real, exists n : Nat,
      (phase n).gramianConstant * (phase n).survivalBudget * B <
        (phase n).viscosity * (phase n).shellN ^ 2 *
          (phase n).phaseGap ^ 2

/-- The full profile + Lipschitz closure also rules out the integrated
phase-alignment control-energy escape once the control energy is embedded in
the generated Lipschitz ledger.

This is the top-level bridge for the control-theory framing: finite-time
Gramian control does not bypass the Track B reserve ledger if its energy
entries are charged in the same generated low-frequency Lipschitz market. -/
theorem no_phase_alignment_control_energy_escape_of_profile_lipschitz_closure
    (O : TrackBProfileLipschitzControlObligation)
    (u0 : SmoothNSInitialData)
    (A : PhaseAlignmentProfileLipschitzEscapeAttempt O u0) :
    False := by
  let U := O.evolution_of_initial_data u0
  let L := O.lipschitz_bridge.ledger_of_evolution U
  have hnosurvivor :
      forall n : Nat, FullLedgerNoSurvivor (L.block n) := by
    intro n
    simpa [trackBGeneratedLowFrequencyLipschitzLedger, U, L] using
      generated_lipschitz_block_no_survivor_of_trackB_profile_closure
        O u0 n
  exact
    no_phase_alignment_control_energy_escape_under_audited_lipschitz_reserve
      L
      (O.lipschitz_bridge.audited_certificate_of_evolution U)
      A.phase
      hnosurvivor
      A.control_energy_embeds_in_generated_lipschitz_ledger
      A.integrated_phase_alignment_escape

/-- Source-level phase/low-high action cap for generated Lipschitz blocks.

This is the non-circular boundary between the phase-alignment / LP-Bony lane
and the generated amplitude lane.  The phase receipt may motivate the action
functional, but the caller must still pay the actual sandwich inequalities:

* the action is the generated gain-at-amplitude `gamma * ampSq`;
* survival profit is below that predeclared action;
* the action is below `sharpTarget`;
* the action cap was not obtained by first assuming `FullLedgerNoSurvivor`.

Without the `action_le_target` field this object cannot construct a generated
action source, which keeps phase-latency from silently reusing the no-survivor
fact that the generated action source itself proves. -/
structure PhaseLowHighGeneratedActionCapReceipt
    (lipschitz_bridge : LowFrequencyLipschitzBridge) where
  phase :
    NSEvolution → ℕ → PhaseAlignmentControlGramianReceipt
  ampSq : NSEvolution → ℕ → Real
  action : NSEvolution → ℕ → Real
  observable_of_generated_block :
    ∀ (_U : NSEvolution) (_n : ℕ), SignedObservable
  observable_fully_charged :
    ∀ (U : NSEvolution) (n : ℕ),
      GlobalSignedObservableFullyCharged
        (observable_of_generated_block U n)
  action_channel_declared_before_payoff :
    ∀ (_U : NSEvolution) (_n : ℕ), Prop
  action_channel_declared_before_payoff_paid :
    ∀ (U : NSEvolution) (n : ℕ),
      action_channel_declared_before_payoff U n
  phase_action_cap_not_derived_from_no_survivor :
    ∀ (_U : NSEvolution) (_n : ℕ), Prop
  phase_action_cap_not_derived_from_no_survivor_paid :
    ∀ (U : NSEvolution) (n : ℕ),
      phase_action_cap_not_derived_from_no_survivor U n
  gamma_nonnegative :
    ∀ (U : NSEvolution) (n : ℕ),
      0 ≤ ((lipschitz_bridge.ledger_of_evolution U).block n).gamma
  amp_sq_nonnegative :
    ∀ (U : NSEvolution) (n : ℕ), 0 ≤ ampSq U n
  amp_sq_le_one :
    ∀ (U : NSEvolution) (n : ℕ), ampSq U n ≤ 1
  action_eq_gain_at_amp :
    ∀ (U : NSEvolution) (n : ℕ),
      action U n =
        ((lipschitz_bridge.ledger_of_evolution U).block n).gamma *
          ampSq U n
  survival_profit_le_action :
    ∀ (U : NSEvolution) (n : ℕ),
      ((lipschitz_bridge.ledger_of_evolution U).block n).survivalProfit ≤
        action U n
  action_le_target :
    ∀ (U : NSEvolution) (n : ℕ), action U n ≤ sharpTarget

/-- Falsifiers for the phase/low-high generated action-cap receipt.

The last two constructors are the important anti-tautology checks: a receipt
that does not pay the target action cap, or that derives it only after assuming
generated no-survivor, is not a valid source for the generated amplitude lane. -/
inductive PhaseLowHighGeneratedActionCapReceiptFalsifier
    {lipschitz_bridge : LowFrequencyLipschitzBridge}
    (R : PhaseLowHighGeneratedActionCapReceipt lipschitz_bridge) :
    Type where
  | actionChannelPosthoc
      (U : NSEvolution) (n : ℕ) :
      ¬ R.action_channel_declared_before_payoff U n →
        PhaseLowHighGeneratedActionCapReceiptFalsifier R
  | amplitudeNegative
      (U : NSEvolution) (n : ℕ) :
      ¬ 0 ≤ R.ampSq U n →
        PhaseLowHighGeneratedActionCapReceiptFalsifier R
  | amplitudeAboveOne
      (U : NSEvolution) (n : ℕ) :
      ¬ R.ampSq U n ≤ 1 →
        PhaseLowHighGeneratedActionCapReceiptFalsifier R
  | actionGainMismatch
      (U : NSEvolution) (n : ℕ) :
      R.action U n ≠
        ((lipschitz_bridge.ledger_of_evolution U).block n).gamma *
          R.ampSq U n →
        PhaseLowHighGeneratedActionCapReceiptFalsifier R
  | survivalActionMismatch
      (U : NSEvolution) (n : ℕ) :
      ¬ ((lipschitz_bridge.ledger_of_evolution U).block n).survivalProfit ≤
          R.action U n →
        PhaseLowHighGeneratedActionCapReceiptFalsifier R
  | actionTargetFailure
      (U : NSEvolution) (n : ℕ) :
      ¬ R.action U n ≤ sharpTarget →
        PhaseLowHighGeneratedActionCapReceiptFalsifier R
  | noSurvivorBackflow
      (U : NSEvolution) (n : ℕ) :
      ¬ R.phase_action_cap_not_derived_from_no_survivor U n →
        PhaseLowHighGeneratedActionCapReceiptFalsifier R

theorem no_phase_low_high_generated_action_cap_receipt_falsifier
    {lipschitz_bridge : LowFrequencyLipschitzBridge}
    (R : PhaseLowHighGeneratedActionCapReceipt lipschitz_bridge) :
    PhaseLowHighGeneratedActionCapReceiptFalsifier R → False := by
  intro F
  cases F with
  | actionChannelPosthoc U n hbad =>
      exact hbad (R.action_channel_declared_before_payoff_paid U n)
  | amplitudeNegative U n hbad =>
      exact hbad (R.amp_sq_nonnegative U n)
  | amplitudeAboveOne U n hbad =>
      exact hbad (R.amp_sq_le_one U n)
  | actionGainMismatch U n hbad =>
      exact hbad (R.action_eq_gain_at_amp U n)
  | survivalActionMismatch U n hbad =>
      exact hbad (R.survival_profit_le_action U n)
  | actionTargetFailure U n hbad =>
      exact hbad (R.action_le_target U n)
  | noSurvivorBackflow U n hbad =>
      exact hbad (R.phase_action_cap_not_derived_from_no_survivor_paid U n)

/-- A paid phase/low-high action-cap receipt is a generated action-sandwich
source.

This constructor is intentionally one-way.  It exposes phase/low-high action
data to the existing generated amplitude interface only after the receipt pays
the target action cap directly, before no-survivor pricing is available. -/
def generated_lipschitz_action_sandwich_dual_source_of_phase_low_high_action_cap
    {lipschitz_bridge : LowFrequencyLipschitzBridge}
    (R : PhaseLowHighGeneratedActionCapReceipt lipschitz_bridge) :
    GeneratedLipschitzActionSandwichDualSource lipschitz_bridge where
  ampSq := R.ampSq
  action := R.action
  observable_of_generated_block := R.observable_of_generated_block
  observable_fully_charged := R.observable_fully_charged
  action_channel_declared_before_payoff :=
    R.action_channel_declared_before_payoff
  action_channel_declared_before_payoff_paid :=
    R.action_channel_declared_before_payoff_paid
  gamma_nonnegative := R.gamma_nonnegative
  amp_sq_nonnegative := R.amp_sq_nonnegative
  amp_sq_le_one := R.amp_sq_le_one
  action_eq_gain_at_amp := R.action_eq_gain_at_amp
  survival_profit_le_action := R.survival_profit_le_action
  action_le_target := R.action_le_target

/-- Compact gain-action projection of a paid phase/low-high action cap.

This is the endpoint-tooling friendly form of
`generated_lipschitz_action_sandwich_dual_source_of_phase_low_high_action_cap`.
It still pays the same source receipt; no no-survivor fact is imported. -/
def generated_lipschitz_gain_action_dual_source_of_phase_low_high_action_cap
    {lipschitz_bridge : LowFrequencyLipschitzBridge}
    (R : PhaseLowHighGeneratedActionCapReceipt lipschitz_bridge) :
    GeneratedLipschitzGainActionDualSource lipschitz_bridge :=
  generated_lipschitz_gain_action_dual_source_of_action_sandwich
    lipschitz_bridge
    (generated_lipschitz_action_sandwich_dual_source_of_phase_low_high_action_cap
      R)

/-- A paid phase/low-high action cap excludes survivor profit for the same
generated Lipschitz block.

This theorem is not an input to the source receipt; it is the consequence that
justifies routing the receipt into the existing Track B no-survivor lane. -/
theorem no_survivor_of_phase_low_high_generated_action_cap
    {lipschitz_bridge : LowFrequencyLipschitzBridge}
    (R : PhaseLowHighGeneratedActionCapReceipt lipschitz_bridge)
    (U : NSEvolution) (n : ℕ) :
    FullLedgerNoSurvivor
      ((lipschitz_bridge.ledger_of_evolution U).block n) :=
  no_survivor_of_generated_lipschitz_action_sandwich_source
    (generated_lipschitz_action_sandwich_dual_source_of_phase_low_high_action_cap
      R)
    U
    n

/-- A unit-amplitude phase/low-high action cap gives the normalized generated
unit-amplitude source.

This is the source-level bridge from the phase-latency lane into the shortest
Track B amplitude route.  It does not prove the phase cap; it only says that
once a non-posthoc phase receipt has paid `action = gamma * 1 <= sharpTarget`,
the normalized source can use the same predeclared action channel as
`survivalProfit <= gamma`. -/
def generated_lipschitz_unit_amplitude_source_of_phase_low_high_unit_action_cap
    {lipschitz_bridge : LowFrequencyLipschitzBridge}
    (R : PhaseLowHighGeneratedActionCapReceipt lipschitz_bridge)
    (amp_sq_eq_one :
      ∀ (U : NSEvolution) (n : ℕ), R.ampSq U n = (1 : Real)) :
    GeneratedLipschitzUnitAmplitudeGainCapSource lipschitz_bridge where
  observable_of_generated_block := R.observable_of_generated_block
  observable_fully_charged := R.observable_fully_charged
  gamma_nonnegative := R.gamma_nonnegative
  survival_profit_le_gamma := by
    intro U n
    have hsurv := R.survival_profit_le_action U n
    have haction := R.action_eq_gain_at_amp U n
    rw [haction, amp_sq_eq_one U n, mul_one] at hsurv
    exact hsurv
  gamma_le_target := by
    intro U n
    have hcap := R.action_le_target U n
    have haction := R.action_eq_gain_at_amp U n
    rw [haction, amp_sq_eq_one U n, mul_one] at hcap
    exact hcap

/-- Provenance-bearing unit-amplitude source from a unit phase/low-high action
cap plus typed same-source bindings.

The phase receipt supplies the scalar inequalities; the binding arguments
still have to prove that the observable/root ledger used by the generated block
is the same predeclared unit observable. -/
def generated_lipschitz_unit_amplitude_observable_source_of_phase_low_high_unit_action_cap
    {lipschitz_bridge : LowFrequencyLipschitzBridge}
    (R : PhaseLowHighGeneratedActionCapReceipt lipschitz_bridge)
    (amp_sq_eq_one :
      ∀ (U : NSEvolution) (n : ℕ), R.ampSq U n = (1 : Real))
    (amplitude_square_source :
      ∀ (U : NSEvolution) (n : ℕ),
        DeclaredSourceBinding
          (ObservableScalarPayload SignedObservable Real)
          { observable := R.observable_of_generated_block U n,
            scalar := (1 : Real) })
    (survival_profit_channel_source :
      ∀ (U : NSEvolution) (n : ℕ),
        DeclaredSourceBinding
          (BlockObservablePayload FullLedgerBlock SignedObservable)
          { block := ((lipschitz_bridge.ledger_of_evolution U).block n),
            observable := R.observable_of_generated_block U n })
    (gain_bound_source :
      ∀ (U : NSEvolution) (n : ℕ),
        DeclaredSourceBinding
          (BlockObservableScalarPayload FullLedgerBlock SignedObservable Real)
          { block := ((lipschitz_bridge.ledger_of_evolution U).block n),
            observable := R.observable_of_generated_block U n,
            scalar := (1 : Real) })
    (root_defect_source :
      ∀ (U : NSEvolution) (n : ℕ),
        NonPosthocSourceBinding
          (BlockObservablePayload FullLedgerBlock SignedObservable)
          { block := ((lipschitz_bridge.ledger_of_evolution U).block n),
            observable := R.observable_of_generated_block U n })
    (threshold_root_amplitude_source :
      ∀ (U : NSEvolution) (n : ℕ),
        NonPosthocSourceBinding
          (BlockObservableScalarPayload FullLedgerBlock SignedObservable Real)
          { block := ((lipschitz_bridge.ledger_of_evolution U).block n),
            observable := R.observable_of_generated_block U n,
            scalar := (1 : Real) }) :
    GeneratedLipschitzUnitAmplitudeObservableSource lipschitz_bridge :=
  generated_lipschitz_unit_amplitude_observable_source_of_source_bindings
    (generated_lipschitz_unit_amplitude_source_of_phase_low_high_unit_action_cap
      R
      amp_sq_eq_one)
    amplitude_square_source
    survival_profit_channel_source
    gain_bound_source
    root_defect_source
    threshold_root_amplitude_source

/-- Auto-coupled Track B endpoint from a unit phase/low-high action cap.

This exposes the intended one-corridor route for the finite phase-latency
source: profile bundle and Lipschitz bridge first; then a non-posthoc unit
action cap with same-source observable bindings. -/
def trackB_control_auto_of_phase_low_high_unit_action_cap
    (evolution_of_initial_data : SmoothNSInitialData → NSEvolution)
    (profile_bundle : TrackBProfileDecompositionBridgeBundle)
    {lipschitz_bridge : LowFrequencyLipschitzBridge}
    (R : PhaseLowHighGeneratedActionCapReceipt lipschitz_bridge)
    (amp_sq_eq_one :
      ∀ (U : NSEvolution) (n : ℕ), R.ampSq U n = (1 : Real))
    (amplitude_square_source :
      ∀ (U : NSEvolution) (n : ℕ),
        DeclaredSourceBinding
          (ObservableScalarPayload SignedObservable Real)
          { observable := R.observable_of_generated_block U n,
            scalar := (1 : Real) })
    (survival_profit_channel_source :
      ∀ (U : NSEvolution) (n : ℕ),
        DeclaredSourceBinding
          (BlockObservablePayload FullLedgerBlock SignedObservable)
          { block := ((lipschitz_bridge.ledger_of_evolution U).block n),
            observable := R.observable_of_generated_block U n })
    (gain_bound_source :
      ∀ (U : NSEvolution) (n : ℕ),
        DeclaredSourceBinding
          (BlockObservableScalarPayload FullLedgerBlock SignedObservable Real)
          { block := ((lipschitz_bridge.ledger_of_evolution U).block n),
            observable := R.observable_of_generated_block U n,
            scalar := (1 : Real) })
    (root_defect_source :
      ∀ (U : NSEvolution) (n : ℕ),
        NonPosthocSourceBinding
          (BlockObservablePayload FullLedgerBlock SignedObservable)
          { block := ((lipschitz_bridge.ledger_of_evolution U).block n),
            observable := R.observable_of_generated_block U n })
    (threshold_root_amplitude_source :
      ∀ (U : NSEvolution) (n : ℕ),
        NonPosthocSourceBinding
          (BlockObservableScalarPayload FullLedgerBlock SignedObservable Real)
          { block := ((lipschitz_bridge.ledger_of_evolution U).block n),
            observable := R.observable_of_generated_block U n,
            scalar := (1 : Real) }) :
    TrackBProfileLipschitzControlObligation :=
  trackB_control_auto_of_unit_amplitude_observable_source
    evolution_of_initial_data
    profile_bundle
    lipschitz_bridge
    (generated_lipschitz_unit_amplitude_observable_source_of_phase_low_high_unit_action_cap
      R
      amp_sq_eq_one
      amplitude_square_source
      survival_profit_channel_source
      gain_bound_source
      root_defect_source
      threshold_root_amplitude_source)

/-- Build the phase/low-high action-cap receipt from an already paid compact
generated gain-action source.

This is the compatibility bridge between the measure-valued/self-tax route and
the phase/low-high route.  It is not phase-native: the caller supplies the
phase data and an explicit no-survivor-backflow guard, while the gain-action
source pays the actual cap `gamma * ampSq <= sharpTarget`. -/
def phase_low_high_generated_action_cap_of_gain_action_dual_source
    {lipschitz_bridge : LowFrequencyLipschitzBridge}
    (phase :
      NSEvolution → ℕ → PhaseAlignmentControlGramianReceipt)
    (S : GeneratedLipschitzGainActionDualSource lipschitz_bridge)
    (action_channel_declared_before_payoff :
      ∀ (_U : NSEvolution) (_n : ℕ), Prop)
    (action_channel_declared_before_payoff_paid :
      ∀ (U : NSEvolution) (n : ℕ),
        action_channel_declared_before_payoff U n)
    (phase_action_cap_not_derived_from_no_survivor :
      ∀ (_U : NSEvolution) (_n : ℕ), Prop)
    (phase_action_cap_not_derived_from_no_survivor_paid :
      ∀ (U : NSEvolution) (n : ℕ),
        phase_action_cap_not_derived_from_no_survivor U n) :
    PhaseLowHighGeneratedActionCapReceipt lipschitz_bridge where
  phase := phase
  ampSq := S.ampSq
  action := fun U n =>
    ((lipschitz_bridge.ledger_of_evolution U).block n).gamma *
      S.ampSq U n
  observable_of_generated_block := S.observable_of_generated_block
  observable_fully_charged := S.observable_fully_charged
  action_channel_declared_before_payoff :=
    action_channel_declared_before_payoff
  action_channel_declared_before_payoff_paid :=
    action_channel_declared_before_payoff_paid
  phase_action_cap_not_derived_from_no_survivor :=
    phase_action_cap_not_derived_from_no_survivor
  phase_action_cap_not_derived_from_no_survivor_paid :=
    phase_action_cap_not_derived_from_no_survivor_paid
  gamma_nonnegative := S.gamma_nonnegative
  amp_sq_nonnegative := S.amp_sq_nonnegative
  amp_sq_le_one := S.amp_sq_le_one
  action_eq_gain_at_amp := by
    intro _U _n
    rfl
  survival_profit_le_action := S.survival_profit_le_gain_at_amp
  action_le_target := S.dual_gain_action_cap

/-- Noncircular Young/defect self-tax plus generated matrix parts can pay the
phase action-cap receipt once the phase data and anti-backflow guard are named.

The cap itself comes from the noncircular self-tax gain-action theorem carried
by `generated_gain_action_dual_source_of_noncircular_mv_matrix_parts`; this
constructor only aligns it with a phase action channel. -/
def phase_low_high_generated_action_cap_of_noncircular_mv_matrix_parts
    {lipschitz_bridge : LowFrequencyLipschitzBridge}
    (phase :
      NSEvolution → ℕ → PhaseAlignmentControlGramianReceipt)
    (self_tax_source :
      LeraySelfTaxNoncircularMeasureValuedProfilePriceStreamFamilySource)
    (P : GeneratedMatrixBlockAmplitudeSourceParts lipschitz_bridge)
    (action_channel_declared_before_payoff :
      ∀ (_U : NSEvolution) (_n : ℕ), Prop)
    (action_channel_declared_before_payoff_paid :
      ∀ (U : NSEvolution) (n : ℕ),
        action_channel_declared_before_payoff U n)
    (phase_action_cap_not_derived_from_no_survivor :
      ∀ (_U : NSEvolution) (_n : ℕ), Prop)
    (phase_action_cap_not_derived_from_no_survivor_paid :
      ∀ (U : NSEvolution) (n : ℕ),
        phase_action_cap_not_derived_from_no_survivor U n) :
    PhaseLowHighGeneratedActionCapReceipt lipschitz_bridge :=
  phase_low_high_generated_action_cap_of_gain_action_dual_source
    phase
    (generated_gain_action_dual_source_of_noncircular_mv_matrix_parts
      self_tax_source
      P)
    action_channel_declared_before_payoff
    action_channel_declared_before_payoff_paid
    phase_action_cap_not_derived_from_no_survivor
    phase_action_cap_not_derived_from_no_survivor_paid

/-- Continuum all-output LP/Bony self-tax plus generated matrix parts gives the
same phase action-cap compatibility bridge. -/
def phase_low_high_generated_action_cap_of_continuum_all_output_matrix_parts
    {τ : ContinuumLPProfileTopology.{u}}
    {lipschitz_bridge : LowFrequencyLipschitzBridge}
    (phase :
      NSEvolution → ℕ → PhaseAlignmentControlGramianReceipt)
    (self_tax_source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ)
    (P : GeneratedMatrixBlockAmplitudeSourceParts lipschitz_bridge)
    (action_channel_declared_before_payoff :
      ∀ (_U : NSEvolution) (_n : ℕ), Prop)
    (action_channel_declared_before_payoff_paid :
      ∀ (U : NSEvolution) (n : ℕ),
        action_channel_declared_before_payoff U n)
    (phase_action_cap_not_derived_from_no_survivor :
      ∀ (_U : NSEvolution) (_n : ℕ), Prop)
    (phase_action_cap_not_derived_from_no_survivor_paid :
      ∀ (U : NSEvolution) (n : ℕ),
        phase_action_cap_not_derived_from_no_survivor U n) :
    PhaseLowHighGeneratedActionCapReceipt lipschitz_bridge :=
  phase_low_high_generated_action_cap_of_gain_action_dual_source
    phase
    (generated_gain_action_dual_source_of_continuum_all_output_matrix_parts
      self_tax_source
      P)
    action_channel_declared_before_payoff
    action_channel_declared_before_payoff_paid
    phase_action_cap_not_derived_from_no_survivor
    phase_action_cap_not_derived_from_no_survivor_paid

end

end ZtareProofs.NS
