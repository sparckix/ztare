import Mathlib.Tactic
import ZtareProofs.ns_low_high_catalyst_charging_obligation
import ZtareProofs.ns_flat_torus_killing_mode

/-!
# Low-high kinematic dichotomy

This file sharpens the low-high catalyst branch.  The dangerous story is an
"orthogonal catalyst": the low-frequency field transports or rotates the
high-frequency packet without deformation, yet somehow transfers energy to a
higher shell without paying the reserve/self-tax ledger.

On the flat torus the intended PDE theorem is stronger than the heuristic:
a smooth periodic zero-strain low field is a Killing field, hence a constant
translation, and constant translations preserve Fourier shells.  This Lean file
does not prove that analytic theorem.  It records the exact non-tautological
adapter:

* if deformation is zero, leakage gain is non-positive;
* if deformation is positive, leakage gain is charged by reserve loss;
* reserve loss is included in the interaction price.

Under those fixed hypotheses, the low-high interaction is no-arbitrage.
-/

namespace ZtareProofs.NS

/-- Abstract kinematic ledger for the low-high rotator/stretcher dichotomy.

`deformationCost = 0` is the rotator branch.  `0 < deformationCost` is the
stretcher branch.  The concrete PDE theorem must define this cost from the
fixed low-frequency strain / commutator geometry, not from observed payoff. -/
structure LowHighKinematicDichotomyLedger where
  interaction : LPInteractionLedger
  deformationCost : Real
  leakageGain : Real
  reserveLoss : Real
  is_low_high : interaction.interactionClass = LPParaproductClass.lowHigh
  payoff_le_leakage_gain : interaction.payoff ≤ leakageGain
  price_charges_reserve_loss : reserveLoss ≤ interaction.price

/-- Certificate for the rotator/stretcher split. -/
structure LowHighKinematicDichotomyCertificate
    (L : LowHighKinematicDichotomyLedger) where
  deformation_nonnegative : 0 ≤ L.deformationCost
  price_nonnegative : 0 ≤ L.interaction.price
  rotator_no_shell_transfer :
    L.deformationCost = 0 → L.leakageGain ≤ 0
  stretcher_charged_by_reserve :
    0 < L.deformationCost → L.leakageGain ≤ L.reserveLoss

/-- Positive leakage is impossible in the rotator branch.  This is the precise
contrapositive form of "a shell-jump catalyst must deform." -/
theorem positive_low_high_leakage_forces_deformation
    (L : LowHighKinematicDichotomyLedger)
    (h : LowHighKinematicDichotomyCertificate L)
    (hleak : 0 < L.leakageGain) :
    0 < L.deformationCost := by
  rcases lt_or_eq_of_le h.deformation_nonnegative with hpos | hzero
  · exact hpos
  · have hno : L.leakageGain ≤ 0 := h.rotator_no_shell_transfer hzero.symm
    linarith

/-- The kinematic dichotomy prices a declared low-high interaction. -/
theorem low_high_no_arbitrage_of_kinematic_dichotomy
    (L : LowHighKinematicDichotomyLedger)
    (h : LowHighKinematicDichotomyCertificate L) :
    InteractionNoArbitrage L.interaction := by
  unfold InteractionNoArbitrage
  rcases lt_or_eq_of_le h.deformation_nonnegative with hpos | hzero
  · exact L.payoff_le_leakage_gain.trans
      ((h.stretcher_charged_by_reserve hpos).trans
        L.price_charges_reserve_loss)
  · have hleak : L.leakageGain ≤ 0 := h.rotator_no_shell_transfer hzero.symm
    exact L.payoff_le_leakage_gain.trans (hleak.trans h.price_nonnegative)

/-- Finite Fourier receipt for the low-high shell-transfer branch.

This is the finite-support analytic brick, not the final PDE theorem.  The
deformation cost is fixed from the symmetric-gradient energy of the low mode
before payoff is scored.  The remaining PDE lift is to show that this
finite-mode reserve estimate is stable under the LP/Besov topology used in the
full paraproduct bridge. -/
structure FiniteFourierLowHighDeformationReceipt
    (L : LowHighKinematicDichotomyLedger) where
  wave : Fin 3 → Real
  amplitude : Fin 3 → Real
  nonzero_wave : ∃ i : Fin 3, wave i ≠ 0
  active_amplitude : amplitude ≠ 0
  deformation_eq_mode_energy :
    L.deformationCost = symmetricGradientModeEnergy wave amplitude

/-- A finite low-high shell-transfer witness has strictly positive deformation
cost once the cost is the declared symmetric-gradient mode energy. -/
theorem finite_low_high_receipt_forces_positive_deformation
    (L : LowHighKinematicDichotomyLedger)
    (R : FiniteFourierLowHighDeformationReceipt L) :
    0 < L.deformationCost := by
  rw [R.deformation_eq_mode_energy]
  exact positive_symmetricGradientModeEnergy_of_nonzero_amplitude
    R.wave R.amplitude R.nonzero_wave R.active_amplitude

/-- Finite-mode pricing adapter: if the positive finite deformation energy is
charged by the reserve loss, then the declared low-high interaction is priced.

This theorem avoids the rotator branch entirely.  It is the concrete finite
version of "shell transfer forces deformation, deformation pays reserve." -/
theorem finite_low_high_no_arbitrage_of_deformation_receipt
    (L : LowHighKinematicDichotomyLedger)
    (R : FiniteFourierLowHighDeformationReceipt L)
    (hleak_charged :
      0 < L.deformationCost → L.leakageGain ≤ L.reserveLoss) :
    InteractionNoArbitrage L.interaction := by
  unfold InteractionNoArbitrage
  have hdef : 0 < L.deformationCost :=
    finite_low_high_receipt_forces_positive_deformation L R
  exact L.payoff_le_leakage_gain.trans
    ((hleak_charged hdef).trans L.price_charges_reserve_loss)

/-- Finite-packet version of the low-high shell-transfer receipt.

This is the LP-prefix shape: a finite family of nonzero Fourier modes, one
active amplitude, and deformation cost fixed as the total symmetric-gradient
energy of the low-frequency payload. -/
structure FiniteFourierLowHighPacketDeformationReceipt
    (L : LowHighKinematicDichotomyLedger) where
  mode : Type
  mode_fintype : Fintype mode
  wave : mode → Fin 3 → Real
  amplitude : mode → Fin 3 → Real
  nonzero_wave : ∀ m : mode, ∃ i : Fin 3, wave m i ≠ 0
  activeMode : mode
  activeAmplitude : amplitude activeMode ≠ 0
  deformation_eq_packet_energy :
    L.deformationCost =
      @finiteSymmetricGradientEnergy mode mode_fintype wave amplitude

attribute [instance] FiniteFourierLowHighPacketDeformationReceipt.mode_fintype

/-- A finite low-high packet receipt forces strictly positive deformation cost.
This is stronger than the rotator slogan: zero deformation energy itself rules
out an active nonzero Fourier payload. -/
theorem finite_packet_low_high_receipt_forces_positive_deformation
    (L : LowHighKinematicDichotomyLedger)
    (R : FiniteFourierLowHighPacketDeformationReceipt L) :
    0 < L.deformationCost := by
  rw [R.deformation_eq_packet_energy]
  exact positive_finiteSymmetricGradientEnergy_of_active_mode
    R.wave R.amplitude R.nonzero_wave R.activeMode R.activeAmplitude

/-- Finite-packet pricing adapter: once the finite deformation energy is
charged by the reserve loss, the declared low-high LP-prefix interaction is
priced. -/
theorem finite_packet_low_high_no_arbitrage_of_deformation_receipt
    (L : LowHighKinematicDichotomyLedger)
    (R : FiniteFourierLowHighPacketDeformationReceipt L)
    (hleak_charged :
      0 < L.deformationCost → L.leakageGain ≤ L.reserveLoss) :
    InteractionNoArbitrage L.interaction := by
  unfold InteractionNoArbitrage
  have hdef : 0 < L.deformationCost :=
    finite_packet_low_high_receipt_forces_positive_deformation L R
  exact L.payoff_le_leakage_gain.trans
    ((hleak_charged hdef).trans L.price_charges_reserve_loss)

/-- Zero-energy finite packets cannot carry an active shell-transfer amplitude.
This is the clean finite falsifier kill for the "orthogonal catalyst" loophole:
if the declared deformation energy is zero, every active nonzero Fourier
amplitude vanishes. -/
theorem finite_packet_zero_deformation_kills_active_amplitude
    {ι : Type} [Fintype ι]
    (wave amplitude : ι → Fin 3 → Real)
    (nonzero_wave : ∀ m : ι, ∃ i : Fin 3, wave m i ≠ 0)
    (henergy : finiteSymmetricGradientEnergy wave amplitude = 0)
    (m : ι) :
    amplitude m = 0 :=
  amplitudes_zero_of_finiteSymmetricGradientEnergy_zero
    wave amplitude nonzero_wave henergy m

/-- Fixed LP/Bony topology metadata for the continuum low-high lift.

These fields are intentionally `Prop`s: Lean is not choosing the PDE topology.
The topology, shell projectors, reserve price, and observable class must be
declared before payoff is scored.  Otherwise the low-high "proof" is only a
post-hoc accounting fit. -/
structure FixedLPBonyTopology where
  flat_torus_domain : Prop
  smooth_periodic_state_space : Prop
  lp_shell_projectors_predeclared : Prop
  bony_low_high_split_predeclared : Prop
  reserve_price_predeclared : Prop
  trackb_observable_class_predeclared : Prop

/-- Continuum lift of the finite deformation receipt.

This is the exact PDE estimate obligation for Boss Fight 2.  The hard analysis
is not hidden: one must prove that, in the fixed LP/Bony topology, positive
low-frequency deformation controls leakage gain and is itself charged by the
Track B reserve/self-tax ledger. -/
structure ContinuumLowHighDeformationLift
    (L : LowHighKinematicDichotomyLedger) where
  topology : FixedLPBonyTopology
  field : Type
  lowField : field
  highField : field
  deformationEnergy : Real
  trackBReserveLoss : Real
  low_field_smooth_periodic : Prop
  high_field_lp_localized : Prop
  low_field_nonconstant : Prop
  shell_transfer : Prop
  deformation_eq_ledger :
    L.deformationCost = deformationEnergy
  reserve_eq_ledger :
    L.reserveLoss = trackBReserveLoss
  positive_deformation_of_nonconstant_shell_transfer :
    low_field_nonconstant → shell_transfer → 0 < deformationEnergy
  leakage_gain_charged_by_deformation :
    L.leakageGain ≤ deformationEnergy
  deformation_energy_charged_by_trackb_reserve :
    deformationEnergy ≤ trackBReserveLoss

/-- The continuum LP/Bony deformation lift supplies the reserve-charge side of
the low-high branch.  This is still conditional on the real PDE estimate, but
it is no longer a naming exercise: the estimate must route leakage through
deformation energy and then into the Track B reserve price. -/
theorem continuum_low_high_no_arbitrage_of_deformation_lift
    (L : LowHighKinematicDichotomyLedger)
    (H : ContinuumLowHighDeformationLift L)
    (hlow : H.low_field_nonconstant)
    (htransfer : H.shell_transfer) :
    InteractionNoArbitrage L.interaction := by
  unfold InteractionNoArbitrage
  have _hpositive : 0 < H.deformationEnergy :=
    H.positive_deformation_of_nonconstant_shell_transfer hlow htransfer
  have hreserve : L.leakageGain ≤ L.reserveLoss := by
    rw [H.reserve_eq_ledger]
    exact H.leakage_gain_charged_by_deformation.trans
      H.deformation_energy_charged_by_trackb_reserve
  exact L.payoff_le_leakage_gain.trans
    (hreserve.trans L.price_charges_reserve_loss)

/-- The continuum LP/Bony deformation lift directly charges leakage by the
ledger reserve.  This is the load-bearing pricing output of the lift; the
nonconstant shell-transfer assumptions are only needed for positivity, not for
the reserve-chain inequality itself. -/
theorem continuum_low_high_deformation_lift_charges_ledger_reserve
    (L : LowHighKinematicDichotomyLedger)
    (H : ContinuumLowHighDeformationLift L) :
    L.leakageGain ≤ L.reserveLoss := by
  have hcharge :
      L.leakageGain ≤ H.trackBReserveLoss :=
    H.leakage_gain_charged_by_deformation.trans
      H.deformation_energy_charged_by_trackb_reserve
  rw [← H.reserve_eq_ledger] at hcharge
  exact hcharge

/-- Positive continuum shell transfer must leave the zero-deformation branch
once the fixed LP/Bony lift is supplied. -/
theorem continuum_low_high_shell_transfer_forces_positive_deformation
    (L : LowHighKinematicDichotomyLedger)
    (H : ContinuumLowHighDeformationLift L)
    (hlow : H.low_field_nonconstant)
    (htransfer : H.shell_transfer) :
    0 < L.deformationCost := by
  rw [H.deformation_eq_ledger]
  exact H.positive_deformation_of_nonconstant_shell_transfer hlow htransfer

/-- Positive continuum shell transfer forces a positive declared Track B
reserve loss once the deformation energy is charged by the reserve. -/
theorem continuum_low_high_shell_transfer_forces_positive_trackB_reserve
    (L : LowHighKinematicDichotomyLedger)
    (H : ContinuumLowHighDeformationLift L)
    (hlow : H.low_field_nonconstant)
    (htransfer : H.shell_transfer) :
    0 < H.trackBReserveLoss := by
  have hdef : 0 < H.deformationEnergy :=
    H.positive_deformation_of_nonconstant_shell_transfer hlow htransfer
  exact lt_of_lt_of_le hdef H.deformation_energy_charged_by_trackb_reserve

/-- Positive continuum shell transfer forces positive reserve loss in the
ledger itself. -/
theorem continuum_low_high_shell_transfer_forces_positive_ledger_reserve
    (L : LowHighKinematicDichotomyLedger)
    (H : ContinuumLowHighDeformationLift L)
    (hlow : H.low_field_nonconstant)
    (htransfer : H.shell_transfer) :
    0 < L.reserveLoss := by
  have hreserve :
      0 < H.trackBReserveLoss :=
    continuum_low_high_shell_transfer_forces_positive_trackB_reserve
      L H hlow htransfer
  rw [H.reserve_eq_ledger]
  exact hreserve

/-- Anti-tautology guard for the topology lift: a claimed continuum lift is not
admissible if the topology, reserve price, or observable class is chosen after
payoff scoring. -/
structure ContinuumLowHighLiftAntiTautology where
  topology_fixed_before_payoff : Prop
  shell_projectors_fixed_before_payoff : Prop
  reserve_price_fixed_before_payoff : Prop
  observable_class_fixed_before_payoff : Prop
  deformation_energy_defined_from_geometry : Prop
  leakage_gain_not_used_to_define_deformation : Prop
  no_posthoc_shell_partition : Prop

/-- The low-high Bilinear Charge Witness suggested by the meta-arc inversion.

It packages the actual continuum-lift theorem target in one place.  A real PDE
instantiation must supply:

* the fixed LP/Bony topology and anti-tautology receipts;
* a nonconstant smooth low field causing shell transfer;
* the bilinear estimate routing leakage through deformation energy;
* the Track B reserve/self-tax estimate charging that deformation energy.

The witness is still conditional on those analytic estimates, but it is the
smallest non-tautological object that would close the low-high branch. -/
structure LowHighBilinearChargeWitness
    (L : LowHighKinematicDichotomyLedger) where
  lift : ContinuumLowHighDeformationLift L
  anti_tautology : ContinuumLowHighLiftAntiTautology
  topology_admissible :
    lift.topology.flat_torus_domain ∧
      lift.topology.smooth_periodic_state_space ∧
        lift.topology.lp_shell_projectors_predeclared ∧
          lift.topology.bony_low_high_split_predeclared ∧
            lift.topology.reserve_price_predeclared ∧
              lift.topology.trackb_observable_class_predeclared
  anti_tautology_paid :
    anti_tautology.topology_fixed_before_payoff ∧
      anti_tautology.shell_projectors_fixed_before_payoff ∧
        anti_tautology.reserve_price_fixed_before_payoff ∧
          anti_tautology.observable_class_fixed_before_payoff ∧
            anti_tautology.deformation_energy_defined_from_geometry ∧
              anti_tautology.leakage_gain_not_used_to_define_deformation ∧
                anti_tautology.no_posthoc_shell_partition
  low_nonconstant : lift.low_field_nonconstant
  transfers_shell : lift.shell_transfer

/-- A paid Bilinear Charge Witness prices the declared low-high interaction. -/
theorem low_high_no_arbitrage_of_bilinear_charge_witness
    (L : LowHighKinematicDichotomyLedger)
    (W : LowHighBilinearChargeWitness L) :
    InteractionNoArbitrage L.interaction :=
  continuum_low_high_no_arbitrage_of_deformation_lift
    L W.lift W.low_nonconstant W.transfers_shell

/-- Hostile anti-tautology falsifier for a claimed continuum low-high lift.
Each case negates one pre-payoff declaration required by the witness. -/
inductive ContinuumLowHighLiftAntiTautologyFalsifier
    (A : ContinuumLowHighLiftAntiTautology) : Prop
  | topology_not_fixed :
      ¬ A.topology_fixed_before_payoff →
        ContinuumLowHighLiftAntiTautologyFalsifier A
  | shell_projectors_not_fixed :
      ¬ A.shell_projectors_fixed_before_payoff →
        ContinuumLowHighLiftAntiTautologyFalsifier A
  | reserve_price_not_fixed :
      ¬ A.reserve_price_fixed_before_payoff →
        ContinuumLowHighLiftAntiTautologyFalsifier A
  | observable_class_not_fixed :
      ¬ A.observable_class_fixed_before_payoff →
        ContinuumLowHighLiftAntiTautologyFalsifier A
  | deformation_not_geometric :
      ¬ A.deformation_energy_defined_from_geometry →
        ContinuumLowHighLiftAntiTautologyFalsifier A
  | leakage_used_to_define_deformation :
      ¬ A.leakage_gain_not_used_to_define_deformation →
        ContinuumLowHighLiftAntiTautologyFalsifier A
  | posthoc_shell_partition :
      ¬ A.no_posthoc_shell_partition →
        ContinuumLowHighLiftAntiTautologyFalsifier A

/-- A Bilinear Charge Witness cannot pass the anti-tautology guard if any
pre-payoff declaration fails. -/
theorem no_low_high_bilinear_charge_witness_of_anti_tautology_falsifier
    (L : LowHighKinematicDichotomyLedger)
    (W : LowHighBilinearChargeWitness L)
    (F :
      ContinuumLowHighLiftAntiTautologyFalsifier W.anti_tautology) :
    False := by
  rcases W.anti_tautology_paid with
    ⟨htop, hshell, hreserve, hobs, hgeom, hnotleak, hnoposthoc⟩
  cases F with
  | topology_not_fixed hbad => exact hbad htop
  | shell_projectors_not_fixed hbad => exact hbad hshell
  | reserve_price_not_fixed hbad => exact hbad hreserve
  | observable_class_not_fixed hbad => exact hbad hobs
  | deformation_not_geometric hbad => exact hbad hgeom
  | leakage_used_to_define_deformation hbad => exact hbad hnotleak
  | posthoc_shell_partition hbad => exact hbad hnoposthoc

/-- Exact hostile falsifier shape for the topology lift.

This is what would break Boss Fight 2: a fixed-topology smooth low-high shell
transfer where the bilinear leakage gain is positive but the declared Track B
reserve does not charge it. -/
structure LowHighBilinearChargeFalsifier
    (L : LowHighKinematicDichotomyLedger) where
  lift : ContinuumLowHighDeformationLift L
  low_nonconstant : lift.low_field_nonconstant
  transfers_shell : lift.shell_transfer
  positive_leakage : 0 < L.leakageGain
  reserve_shortfall : L.reserveLoss < L.leakageGain

/-- A genuine Bilinear Charge Witness and a same-ledger falsifier cannot coexist
for the same low-high ledger. -/
theorem no_low_high_bilinear_falsifier_with_charge_witness
    (L : LowHighKinematicDichotomyLedger)
    (W : LowHighBilinearChargeWitness L)
    (F : LowHighBilinearChargeFalsifier L) :
    False := by
  have hreserve : L.leakageGain ≤ L.reserveLoss :=
    continuum_low_high_deformation_lift_charges_ledger_reserve L W.lift
  exact not_lt_of_ge hreserve F.reserve_shortfall

/-- A continuum deformation lift by itself rules out the same-ledger reserve
shortfall falsifier.  The nonconstant/transfer fields remain the PDE activity
receipt, but the pricing contradiction is the reserve-chain inequality. -/
theorem no_low_high_bilinear_falsifier_with_deformation_lift
    (L : LowHighKinematicDichotomyLedger)
    (H : ContinuumLowHighDeformationLift L)
    (F : LowHighBilinearChargeFalsifier L) :
    False := by
  have hreserve : L.leakageGain ≤ L.reserveLoss :=
    continuum_low_high_deformation_lift_charges_ledger_reserve L H
  exact not_lt_of_ge hreserve F.reserve_shortfall

/-- Constant-bearing form of the Bilinear Charge Witness.

This is closer to the actual PDE estimate GP-215 generated: the low-high
paraproduct leakage must be bounded by an explicit LP/Besov constant times the
deformation energy, and the reserve price must absorb that constant-weighted
energy.  The constant is part of the witness and must be fixed before payoff
scoring. -/
structure LowHighBilinearConstantWitness
    (L : LowHighKinematicDichotomyLedger) where
  lift : ContinuumLowHighDeformationLift L
  catalystConstant : Real
  catalyst_constant_declared_before_payoff : Prop
  catalyst_constant_nonnegative : 0 ≤ catalystConstant
  low_nonconstant : lift.low_field_nonconstant
  transfers_shell : lift.shell_transfer
  bilinear_bound :
    L.leakageGain ≤ catalystConstant * lift.deformationEnergy
  reserve_absorbs_constant_weighted_deformation :
    catalystConstant * lift.deformationEnergy ≤ lift.trackBReserveLoss

/-- A constant-bearing low-high paraproduct witness prices the interaction. -/
theorem low_high_no_arbitrage_of_bilinear_constant_witness
    (L : LowHighKinematicDichotomyLedger)
    (W : LowHighBilinearConstantWitness L) :
    InteractionNoArbitrage L.interaction := by
  unfold InteractionNoArbitrage
  have _hpositive : 0 < W.lift.deformationEnergy :=
    W.lift.positive_deformation_of_nonconstant_shell_transfer
      W.low_nonconstant W.transfers_shell
  have hreserve : L.leakageGain ≤ L.reserveLoss := by
    have hcharge :
        L.leakageGain ≤ W.lift.trackBReserveLoss :=
      W.bilinear_bound.trans
        W.reserve_absorbs_constant_weighted_deformation
    rw [← W.lift.reserve_eq_ledger] at hcharge
    exact hcharge
  exact L.payoff_le_leakage_gain.trans
    (hreserve.trans L.price_charges_reserve_loss)

/-- A constant-bearing Bilinear Charge Witness and a same-ledger reserve
shortfall falsifier cannot coexist. -/
theorem no_low_high_bilinear_falsifier_with_constant_witness
    (L : LowHighKinematicDichotomyLedger)
    (W : LowHighBilinearConstantWitness L)
    (F : LowHighBilinearChargeFalsifier L) :
    False := by
  have hreserve : L.leakageGain ≤ L.reserveLoss := by
    have hcharge :
        L.leakageGain ≤ W.lift.trackBReserveLoss :=
      W.bilinear_bound.trans
        W.reserve_absorbs_constant_weighted_deformation
    rw [← W.lift.reserve_eq_ledger] at hcharge
    exact hcharge
  exact not_lt_of_ge hreserve F.reserve_shortfall

/-- Concrete LP/Bony estimate receipt for the low-high catalyst branch.

This is the analytic shape behind the constant witness.  The standard
low-high paraproduct estimate has the form

`leakage <= C_lh * low-frequency-Lipschitz-cost * high-shell-energy`.

The non-tautological continuation burden is the absorption line: that same
quantity must be charged by the predeclared Track B reserve price, typically
through a viscosity/frequency reserve or a separately proved state-pricing
budget.  The fields below are deliberately scalar receipts: future PDE work
must instantiate them from a fixed LP/Bony topology before payoff is scored. -/
structure LowHighLPBonyEstimateReceipt
    (L : LowHighKinematicDichotomyLedger) where
  lift : ContinuumLowHighDeformationLift L
  lpBonyConstant : Real
  lowFrequencyLipschitzCost : Real
  highShellEnergy : Real
  lp_bony_constant_declared_before_payoff : Prop
  lipschitz_cost_declared_before_payoff : Prop
  high_shell_energy_declared_before_payoff : Prop
  lp_bony_constant_nonnegative : 0 ≤ lpBonyConstant
  high_shell_energy_nonnegative : 0 ≤ highShellEnergy
  deformation_eq_lipschitz_energy :
    lift.deformationEnergy = lowFrequencyLipschitzCost * highShellEnergy
  leakage_bound :
    L.leakageGain ≤
      lpBonyConstant * (lowFrequencyLipschitzCost * highShellEnergy)
  reserve_absorbs_lipschitz_energy :
    lpBonyConstant * (lowFrequencyLipschitzCost * highShellEnergy) ≤
      lift.trackBReserveLoss
  low_nonconstant : lift.low_field_nonconstant
  transfers_shell : lift.shell_transfer

/-- The concrete LP/Bony receipt induces the constant-bearing witness. -/
def constant_witness_of_lp_bony_estimate_receipt
    (L : LowHighKinematicDichotomyLedger)
    (R : LowHighLPBonyEstimateReceipt L) :
    LowHighBilinearConstantWitness L where
  lift := R.lift
  catalystConstant := R.lpBonyConstant
  catalyst_constant_declared_before_payoff :=
    R.lp_bony_constant_declared_before_payoff
  catalyst_constant_nonnegative := R.lp_bony_constant_nonnegative
  low_nonconstant := R.low_nonconstant
  transfers_shell := R.transfers_shell
  bilinear_bound := by
    rw [R.deformation_eq_lipschitz_energy]
    exact R.leakage_bound
  reserve_absorbs_constant_weighted_deformation := by
    rw [R.deformation_eq_lipschitz_energy]
    exact R.reserve_absorbs_lipschitz_energy

/-- A concrete LP/Bony estimate receipt directly prices the low-high
interaction.

This is the PDE-facing target form: prove the fixed-topology paraproduct bound
and the Track B reserve absorption line, and the interaction is priced without
introducing any additional observable or shell partition. -/
theorem low_high_no_arbitrage_of_lp_bony_estimate_receipt
    (L : LowHighKinematicDichotomyLedger)
    (R : LowHighLPBonyEstimateReceipt L) :
    InteractionNoArbitrage L.interaction :=
  low_high_no_arbitrage_of_bilinear_constant_witness L
    (constant_witness_of_lp_bony_estimate_receipt L R)

/-- A concrete LP/Bony receipt charges leakage by the same ledger reserve. -/
theorem low_high_lp_bony_receipt_charges_ledger_reserve
    (L : LowHighKinematicDichotomyLedger)
    (R : LowHighLPBonyEstimateReceipt L) :
    L.leakageGain ≤ L.reserveLoss := by
  have hcharge :
      L.leakageGain ≤ R.lift.trackBReserveLoss :=
    R.leakage_bound.trans R.reserve_absorbs_lipschitz_energy
  rw [← R.lift.reserve_eq_ledger] at hcharge
  exact hcharge

/-- The same LP/Bony estimate receipt also forces positive deformation cost for
the active nonconstant shell transfer it declares. -/
theorem low_high_positive_deformation_of_lp_bony_estimate_receipt
    (L : LowHighKinematicDichotomyLedger)
    (R : LowHighLPBonyEstimateReceipt L) :
    0 < L.deformationCost :=
  continuum_low_high_shell_transfer_forces_positive_deformation
    L R.lift R.low_nonconstant R.transfers_shell

/-- A concrete LP/Bony estimate receipt also forces positive Track B reserve
loss for its declared active low-high shell transfer. -/
theorem low_high_positive_reserve_of_lp_bony_estimate_receipt
    (L : LowHighKinematicDichotomyLedger)
    (R : LowHighLPBonyEstimateReceipt L) :
    0 < L.reserveLoss :=
  continuum_low_high_shell_transfer_forces_positive_ledger_reserve
    L R.lift R.low_nonconstant R.transfers_shell

/-- Active LP/Bony shell transfer forces positive Lipschitz-times-high-shell
energy, since that product is the declared deformation energy. -/
theorem low_high_lp_bony_receipt_forces_positive_lipschitz_energy
    (L : LowHighKinematicDichotomyLedger)
    (R : LowHighLPBonyEstimateReceipt L) :
    0 < R.lowFrequencyLipschitzCost * R.highShellEnergy := by
  have hdef :
      0 < R.lift.deformationEnergy :=
    R.lift.positive_deformation_of_nonconstant_shell_transfer
      R.low_nonconstant R.transfers_shell
  rw [R.deformation_eq_lipschitz_energy] at hdef
  exact hdef

/-- Active LP/Bony shell transfer cannot be paid with zero high-shell energy. -/
theorem low_high_lp_bony_receipt_forces_positive_high_shell_energy
    (L : LowHighKinematicDichotomyLedger)
    (R : LowHighLPBonyEstimateReceipt L) :
    0 < R.highShellEnergy := by
  have hprod :
      0 < R.lowFrequencyLipschitzCost * R.highShellEnergy :=
    low_high_lp_bony_receipt_forces_positive_lipschitz_energy L R
  rcases lt_or_eq_of_le R.high_shell_energy_nonnegative with hpos | hzero
  · exact hpos
  · rw [hzero.symm, mul_zero] at hprod
    linarith

/-- Active LP/Bony shell transfer cannot be paid with zero or negative
low-frequency Lipschitz cost. -/
theorem low_high_lp_bony_receipt_forces_positive_low_frequency_lipschitz_cost
    (L : LowHighKinematicDichotomyLedger)
    (R : LowHighLPBonyEstimateReceipt L) :
    0 < R.lowFrequencyLipschitzCost := by
  have hprod :
      0 < R.lowFrequencyLipschitzCost * R.highShellEnergy :=
    low_high_lp_bony_receipt_forces_positive_lipschitz_energy L R
  have hhigh :
      0 < R.highShellEnergy :=
      low_high_lp_bony_receipt_forces_positive_high_shell_energy L R
  by_contra hnot
  push Not at hnot
  have hprod_nonpos :
      R.lowFrequencyLipschitzCost * R.highShellEnergy ≤ 0 :=
    mul_nonpos_of_nonpos_of_nonneg hnot (le_of_lt hhigh)
  linarith

/-- A concrete LP/Bony estimate receipt and the same-ledger reserve shortfall
falsifier cannot coexist. -/
theorem no_low_high_bilinear_falsifier_with_lp_bony_receipt
    (L : LowHighKinematicDichotomyLedger)
    (R : LowHighLPBonyEstimateReceipt L)
    (F : LowHighBilinearChargeFalsifier L) :
    False := by
  have hreserve : L.leakageGain ≤ L.reserveLoss :=
    low_high_lp_bony_receipt_charges_ledger_reserve L R
  exact not_lt_of_ge hreserve F.reserve_shortfall

/-- A viscosity/frequency absorption split is enough to pay the LP/Bony reserve
line, provided the high-shell energy is nonnegative.

This is where the low-high branch meets the continuation problem: if the
low-frequency Lipschitz cost is not controlled relative to the shell frequency
reserve, the argument has only restated a continuation criterion. -/
theorem reserve_absorbs_lp_bony_energy_of_frequency_split
    {C Llow Ehigh Vreserve TrackBReserve : Real}
    (hE : 0 ≤ Ehigh)
    (hfreq : C * Llow ≤ Vreserve)
    (hreserve : Vreserve * Ehigh ≤ TrackBReserve) :
    C * (Llow * Ehigh) ≤ TrackBReserve := by
  have hmul : (C * Llow) * Ehigh ≤ Vreserve * Ehigh :=
    mul_le_mul_of_nonneg_right hfreq hE
  have hassoc : C * (Llow * Ehigh) = (C * Llow) * Ehigh := by
    ring
  rw [hassoc]
  exact hmul.trans hreserve

/-- The constant-bearing witness induces the simpler Bilinear Charge Witness
whenever the constant-weighted estimate is compressed into the deformation and
reserve inequalities.  This is a one-way adapter used when an analytic PDE
proof supplies the sharper constant form. -/
def bilinear_charge_witness_of_constant_witness
    (L : LowHighKinematicDichotomyLedger)
    (W : LowHighBilinearConstantWitness L)
    (hcompressed_leakage :
      L.leakageGain ≤ W.lift.deformationEnergy)
    (hcompressed_reserve :
      W.lift.deformationEnergy ≤ W.lift.trackBReserveLoss)
    (A : ContinuumLowHighLiftAntiTautology)
    (htop :
      W.lift.topology.flat_torus_domain ∧
        W.lift.topology.smooth_periodic_state_space ∧
          W.lift.topology.lp_shell_projectors_predeclared ∧
            W.lift.topology.bony_low_high_split_predeclared ∧
              W.lift.topology.reserve_price_predeclared ∧
                W.lift.topology.trackb_observable_class_predeclared)
    (hA :
      A.topology_fixed_before_payoff ∧
        A.shell_projectors_fixed_before_payoff ∧
          A.reserve_price_fixed_before_payoff ∧
            A.observable_class_fixed_before_payoff ∧
              A.deformation_energy_defined_from_geometry ∧
                A.leakage_gain_not_used_to_define_deformation ∧
                  A.no_posthoc_shell_partition) :
    LowHighBilinearChargeWitness L where
  lift :=
    { W.lift with
      leakage_gain_charged_by_deformation := hcompressed_leakage
      deformation_energy_charged_by_trackb_reserve := hcompressed_reserve }
  anti_tautology := A
  topology_admissible := htop
  anti_tautology_paid := hA
  low_nonconstant := W.low_nonconstant
  transfers_shell := W.transfers_shell

/-- Positive branch payload: the low-high class admits a fixed kinematic
dichotomy ledger. -/
structure ClosedLowHighKinematicPositive where
  Class : LPInteractionLedger → Prop
  ledger_of_class :
    ∀ T : LPInteractionLedger,
      Class T →
        ∃ L : LowHighKinematicDichotomyLedger,
          L.interaction = T ∧ LowHighKinematicDichotomyCertificate L

/-- Negative branch payload: a shell-transfer rotator, i.e. the exact hostile
falsifier the operator described. -/
structure ClosedLowHighKinematicNegative where
  ledger : LowHighKinematicDichotomyLedger
  certificate_without_rotator :
    0 ≤ ledger.deformationCost ∧ 0 ≤ ledger.interaction.price ∧
      (0 < ledger.deformationCost → ledger.leakageGain ≤ ledger.reserveLoss)
  zero_deformation : ledger.deformationCost = 0
  positive_leakage : 0 < ledger.leakageGain

/-- If every low-high class member has a fixed kinematic dichotomy certificate,
then the class is priced. -/
theorem low_high_class_no_arbitrage_of_kinematic_positive
    (P : ClosedLowHighKinematicPositive)
    (T : LPInteractionLedger)
    (hT : P.Class T) :
    InteractionNoArbitrage T := by
  obtain ⟨L, hLT, hcert⟩ := P.ledger_of_class T hT
  rw [← hLT]
  exact low_high_no_arbitrage_of_kinematic_dichotomy L hcert

/-- Analytic obligations for the flat-torus version of the dichotomy.

The strongest possible closure would prove these from the declared LP/Bony
decomposition and standard torus geometry, not from fitted finite packets. -/
structure FlatTorusLowHighKinematicPDEObligation where
  deformation_cost_declared_before_payoff : Prop
  zero_strain_nonzero_fourier_modes_vanish : Prop
  zero_deformation_implies_killing_low_field : Prop
  flat_torus_killing_fields_are_constant_translations : Prop
  constant_translation_preserves_lp_shells : Prop
  nonconstant_shell_transfer_forces_positive_deformation : Prop
  positive_deformation_charged_by_reserve_loss : Prop
  reserve_loss_charged_in_trackb_price : Prop

/-- Paid receipt for the flat-torus low-high kinematic PDE obligation.

The obligation object names the PDE duties.  This companion structure carries
proofs that those duties are paid.  Keeping the two layers separate prevents a
bare declaration surface from being mistaken for an analytic closure. -/
structure FlatTorusLowHighKinematicPDEObligationSatisfied
    (O : FlatTorusLowHighKinematicPDEObligation) where
  deformation_cost_declared_before_payoff :
    O.deformation_cost_declared_before_payoff
  zero_strain_nonzero_fourier_modes_vanish :
    O.zero_strain_nonzero_fourier_modes_vanish
  zero_deformation_implies_killing_low_field :
    O.zero_deformation_implies_killing_low_field
  flat_torus_killing_fields_are_constant_translations :
    O.flat_torus_killing_fields_are_constant_translations
  constant_translation_preserves_lp_shells :
    O.constant_translation_preserves_lp_shells
  nonconstant_shell_transfer_forces_positive_deformation :
    O.nonconstant_shell_transfer_forces_positive_deformation
  positive_deformation_charged_by_reserve_loss :
    O.positive_deformation_charged_by_reserve_loss
  reserve_loss_charged_in_trackb_price :
    O.reserve_loss_charged_in_trackb_price

/-- Adapter from the flat-torus Killing-mode receipt into the low-high PDE
obligation surface.

The Killing provenance is load-bearing here: the theorem below derives the
zero-mode, constant-translation, and shell-obstruction facts from
`FlatTorusKillingModeProvenance`, then uses only predeclared handoff arrows to
pay the corresponding PDE obligation fields.  The reserve/price fields remain
separate because the finite Fourier/Killing receipt does not contain those
Track B estimates. -/
structure FlatTorusKillingModePDEAdapter
    (O : FlatTorusLowHighKinematicPDEObligation)
    (C : FlatTorusKillingModeConclusion) where
  provenance : FlatTorusKillingModeProvenance C
  deformation_cost_declared_before_payoff :
    O.deformation_cost_declared_before_payoff
  zero_strain_fourier_rigidity_handoff :
    C.nonzero_modes_zero_amplitude →
      O.zero_strain_nonzero_fourier_modes_vanish
  zero_mode_killing_lift_handoff :
    C.only_zero_mode_can_remain →
      O.zero_deformation_implies_killing_low_field
  constant_translation_classification_handoff :
    C.constant_translation_branch →
      O.flat_torus_killing_fields_are_constant_translations
  constant_translation_shell_handoff :
    C.constant_translation_branch →
      O.constant_translation_preserves_lp_shells
  shell_obstruction_positive_deformation_handoff :
    C.shell_transfer_requires_nonzero_strain →
      O.nonconstant_shell_transfer_forces_positive_deformation
  positive_deformation_charged_by_reserve_loss :
    O.positive_deformation_charged_by_reserve_loss
  reserve_loss_charged_in_trackb_price :
    O.reserve_loss_charged_in_trackb_price

/-- The flat-torus Killing-mode adapter constructs the full PDE-obligation
satisfaction receipt without treating the obligation fields as bare slogans. -/
theorem flat_torus_low_high_pde_satisfied_of_killing_mode_adapter
    (O : FlatTorusLowHighKinematicPDEObligation)
    (C : FlatTorusKillingModeConclusion)
    (A : FlatTorusKillingModePDEAdapter O C) :
    FlatTorusLowHighKinematicPDEObligationSatisfied O := by
  have hnonzero : C.nonzero_modes_zero_amplitude :=
    A.provenance.nonzero_modes_zero_amplitude
  have honly : C.only_zero_mode_can_remain :=
    A.provenance.only_zero_mode_of_nonzero_modes_zero hnonzero
  have hconstant : C.constant_translation_branch :=
    A.provenance.constant_translation_of_only_zero_mode honly
  have hshell : C.shell_transfer_requires_nonzero_strain :=
    A.provenance.shell_transfer_obstruction_of_constant_translation hconstant
  exact
    { deformation_cost_declared_before_payoff :=
        A.deformation_cost_declared_before_payoff
      zero_strain_nonzero_fourier_modes_vanish :=
        A.zero_strain_fourier_rigidity_handoff hnonzero
      zero_deformation_implies_killing_low_field :=
        A.zero_mode_killing_lift_handoff honly
      flat_torus_killing_fields_are_constant_translations :=
        A.constant_translation_classification_handoff hconstant
      constant_translation_preserves_lp_shells :=
        A.constant_translation_shell_handoff hconstant
      nonconstant_shell_transfer_forces_positive_deformation :=
        A.shell_obstruction_positive_deformation_handoff hshell
      positive_deformation_charged_by_reserve_loss :=
        A.positive_deformation_charged_by_reserve_loss
      reserve_loss_charged_in_trackb_price :=
        A.reserve_loss_charged_in_trackb_price }

/-- The finite Killing-mode clock supplies the nonconstant-transfer duty
through the adapter, without routing through the full satisfied receipt.

This isolates the symmetry-breaker edge that prevents a later phase-capacity
handoff from treating the flat-torus Killing obstruction as decorative. -/
theorem flat_torus_nonconstant_transfer_of_killing_mode_adapter
    (O : FlatTorusLowHighKinematicPDEObligation)
    (C : FlatTorusKillingModeConclusion)
    (A : FlatTorusKillingModePDEAdapter O C) :
    O.nonconstant_shell_transfer_forces_positive_deformation :=
  A.shell_obstruction_positive_deformation_handoff
    (shell_transfer_requires_nonzero_strain_of_killing_mode_provenance
      C A.provenance)

/-- The phase-capacity consumer must take the whole flat-torus source package:
finite shell obstruction, positive deformation, reserve-loss charging, and
Track B price charging. -/
theorem flat_torus_phase_capacity_sources_of_killing_mode_adapter
    (O : FlatTorusLowHighKinematicPDEObligation)
    (C : FlatTorusKillingModeConclusion)
    (A : FlatTorusKillingModePDEAdapter O C) :
    C.shell_transfer_requires_nonzero_strain ∧
      O.nonconstant_shell_transfer_forces_positive_deformation ∧
        O.positive_deformation_charged_by_reserve_loss ∧
          O.reserve_loss_charged_in_trackb_price := by
  have hshell : C.shell_transfer_requires_nonzero_strain :=
    shell_transfer_requires_nonzero_strain_of_killing_mode_provenance
      C A.provenance
  exact
    ⟨hshell,
      A.shell_obstruction_positive_deformation_handoff hshell,
      A.positive_deformation_charged_by_reserve_loss,
      A.reserve_loss_charged_in_trackb_price⟩

/-- Branch-wise falsifier surface for the flat-torus low-high kinematic PDE
obligation.

This prevents the GP216 bridge from compressing the torus symmetry-breaker into
a single slogan.  A hostile branch must name exactly which PDE duty failed:
pre-payoff deformation geometry, zero-strain Fourier rigidity, Killing-field
classification, LP-shell preservation, positive deformation, or reserve/price
charging. -/
inductive FlatTorusLowHighKinematicPDEObligationFalsifier
    (O : FlatTorusLowHighKinematicPDEObligation) : Prop
  | deformation_cost_posthoc :
      ¬ O.deformation_cost_declared_before_payoff →
        FlatTorusLowHighKinematicPDEObligationFalsifier O
  | zero_strain_fourier_rigidity_missing :
      ¬ O.zero_strain_nonzero_fourier_modes_vanish →
        FlatTorusLowHighKinematicPDEObligationFalsifier O
  | zero_deformation_killing_lift_missing :
      ¬ O.zero_deformation_implies_killing_low_field →
        FlatTorusLowHighKinematicPDEObligationFalsifier O
  | killing_fields_not_classified_as_translations :
      ¬ O.flat_torus_killing_fields_are_constant_translations →
        FlatTorusLowHighKinematicPDEObligationFalsifier O
  | constant_translation_shell_preservation_missing :
      ¬ O.constant_translation_preserves_lp_shells →
        FlatTorusLowHighKinematicPDEObligationFalsifier O
  | nonconstant_transfer_positive_deformation_missing :
      ¬ O.nonconstant_shell_transfer_forces_positive_deformation →
        FlatTorusLowHighKinematicPDEObligationFalsifier O
  | positive_deformation_not_charged_by_reserve :
      ¬ O.positive_deformation_charged_by_reserve_loss →
        FlatTorusLowHighKinematicPDEObligationFalsifier O
  | reserve_loss_not_charged_in_trackb_price :
      ¬ O.reserve_loss_charged_in_trackb_price →
        FlatTorusLowHighKinematicPDEObligationFalsifier O

/-- A carried flat-torus low-high PDE obligation rules out every branch-wise
falsifier surface for that same obligation object. -/
theorem no_flat_torus_low_high_kinematic_pde_obligation_falsifier
    (O : FlatTorusLowHighKinematicPDEObligation)
    (H : FlatTorusLowHighKinematicPDEObligationSatisfied O)
    (F : FlatTorusLowHighKinematicPDEObligationFalsifier O) :
    False := by
  cases F with
  | deformation_cost_posthoc hbad =>
      exact hbad H.deformation_cost_declared_before_payoff
  | zero_strain_fourier_rigidity_missing hbad =>
      exact hbad H.zero_strain_nonzero_fourier_modes_vanish
  | zero_deformation_killing_lift_missing hbad =>
      exact hbad H.zero_deformation_implies_killing_low_field
  | killing_fields_not_classified_as_translations hbad =>
      exact hbad H.flat_torus_killing_fields_are_constant_translations
  | constant_translation_shell_preservation_missing hbad =>
      exact hbad H.constant_translation_preserves_lp_shells
  | nonconstant_transfer_positive_deformation_missing hbad =>
      exact hbad H.nonconstant_shell_transfer_forces_positive_deformation
  | positive_deformation_not_charged_by_reserve hbad =>
      exact hbad H.positive_deformation_charged_by_reserve_loss
  | reserve_loss_not_charged_in_trackb_price hbad =>
      exact hbad H.reserve_loss_charged_in_trackb_price

end ZtareProofs.NS
