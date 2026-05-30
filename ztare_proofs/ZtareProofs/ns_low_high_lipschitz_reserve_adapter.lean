import Mathlib.Tactic
import ZtareProofs.ns_low_high_kinematic_dichotomy
import ZtareProofs.ns_low_frequency_lipschitz_control_bridge
import ZtareProofs.ns_phase_latency_control_receipt

/-!
# Low-high LP/Bony receipt to Lipschitz reserve adapter

Phase 5GP/5GB made the low-high catalyst branch concrete:

* finite low-high hostile searches find no PSD-reserve breaker;
* the Lean low-high witness requires an LP/Bony estimate
  `leakage <= C_lh * lowFrequencyLipschitzCost * highShellEnergy`;
* the Clay bridge still fails if the low-frequency Lipschitz cost is merely
  assumed controlled.

This file connects those two sides.  It does not prove the PDE estimate.  It
proves the bookkeeping implication: if the LP/Bony leakage cost is exactly one
of the costs priced by the low-frequency Lipschitz reserve ledger, then a
no-survivor block prices the low-high interaction.
-/

namespace ZtareProofs.NS

/-- Reality-check version of the low-high LP/Bony estimate.

Instead of directly assuming
`leakage <= C_lh * lowFrequencyLipschitzCost * highShellEnergy`, this object
separates the PDE estimate into two pieces closer to the usual analytic form:

* a linearized low-high operator norm times high-shell energy controls leakage;
* that operator norm is bounded by a fixed LP/Bony constant times the
  low-frequency Lipschitz cost.

This still does not prove the PDE estimate in Lean, but it prevents the receipt
from being a pure accounting declaration.  The next real analysis step is to
instantiate `operator_bound_by_low_lip` from the fixed Bony decomposition and
Sobolev/Besov embedding. -/
structure LowHighBonyOperatorEstimateRealityCheck
    (L : LowHighKinematicDichotomyLedger) where
  lift : ContinuumLowHighDeformationLift L
  lpBonyConstant : Real
  lowFrequencyLipschitzCost : Real
  highShellEnergy : Real
  operatorNorm : Real
  lp_bony_constant_declared_before_payoff : Prop
  lipschitz_cost_declared_before_payoff : Prop
  high_shell_energy_declared_before_payoff : Prop
  operator_norm_declared_before_payoff : Prop
  lp_bony_constant_nonnegative : 0 ≤ lpBonyConstant
  high_shell_energy_nonnegative : 0 ≤ highShellEnergy
  deformation_eq_lipschitz_energy :
    lift.deformationEnergy = lowFrequencyLipschitzCost * highShellEnergy
  leakage_le_operator_energy :
    L.leakageGain ≤ operatorNorm * highShellEnergy
  operator_bound_by_low_lip :
    operatorNorm ≤ lpBonyConstant * lowFrequencyLipschitzCost
  low_nonconstant : lift.low_field_nonconstant
  transfers_shell : lift.shell_transfer

/-- Fixed topology data for the low-high LP/Bony operator estimate.

This is not a theorem by itself.  It records the anti-tautology discipline
needed before a PDE estimate can be used: projectors, shell gaps, norm,
finite-core treatment, and Leray/Fourier multiplier compatibility are fixed
before payoff is scored. -/
structure FixedLowHighLPBonyTopology where
  lp_projectors_declared_before_payoff : Prop
  output_delta_projector_declared : Prop
  leray_fourier_multiplier_declared : Prop
  h1_or_lambda_norm_declared : Prop
  shell_support_gap_declared : Prop
  finite_low_shell_core_declared : Prop
  constants_declared_before_payoff : Prop

/-- Local PDE receipt for the low-high operator estimate under a fixed
LP/Bony topology.

The fields mirror the actual analytic proof plan:

* Leray/periodic pairing handles the `L2` skew transport and stretch term;
* the projected `H1` transport term is paid by an explicit commutator receipt,
  not by pretending the full `Lambda Delta_j P` expression is exactly skew;
* the stretch derivative-loss terms are paid separately;
* low-frequency separation pays the Bernstein/support-gap estimate.

Once these subreceipts are supplied, this object converts into
`LowHighBonyOperatorEstimateRealityCheck`, and the existing reserve-link
machinery takes over. -/
structure FixedTopologyLowHighOperatorReceipt
    (L : LowHighKinematicDichotomyLedger) where
  topology : FixedLowHighLPBonyTopology
  lift : ContinuumLowHighDeformationLift L
  lpBonyConstant : Real
  lowFrequencyLipschitzCost : Real
  highShellEnergy : Real
  operatorNorm : Real
  lp_bony_constant_nonnegative : 0 ≤ lpBonyConstant
  high_shell_energy_nonnegative : 0 ≤ highShellEnergy
  deformation_eq_lipschitz_energy :
    lift.deformationEnergy = lowFrequencyLipschitzCost * highShellEnergy
  leray_l2_pairing_receipt : Prop
  projected_transport_commutator_receipt : Prop
  h1_commutator_receipt : Prop
  stretching_h_grad_l_receipt : Prop
  low_frequency_separation_receipt : Prop
  leakage_le_operator_energy :
    L.leakageGain ≤ operatorNorm * highShellEnergy
  operator_bound_by_low_lip :
    operatorNorm ≤ lpBonyConstant * lowFrequencyLipschitzCost
  low_nonconstant : lift.low_field_nonconstant
  transfers_shell : lift.shell_transfer

/-- Explicit projected-transport commutator receipt.

This separates the part a hostile referee will inspect most closely.  The
transport term is not allowed to disappear by claiming the full
`Lambda Delta_j P` expression is skew.  The main skew cancellation must occur
only after commuting the fixed Fourier multiplier, and the remaining
commutator is charged by `||grad L||_infty * ||Lambda H||_2^2` with constants
fixed before payoff is scored. -/
structure FixedTopologyTransportCommutatorReceipt where
  topology : FixedLowHighLPBonyTopology
  commutatorConstant : Real
  lowFrequencyLipschitzCost : Real
  highShellEnergy : Real
  transportPairingMagnitude : Real
  commutator_constant_nonnegative : 0 ≤ commutatorConstant
  high_shell_energy_nonnegative : 0 ≤ highShellEnergy
  multiplier_self_adjoint_declared : Prop
  leray_commutes_with_fixed_multipliers : Prop
  low_field_divergence_free : Prop
  main_skew_term_cancelled_after_commuting : Prop
  commutator_remainder_declared_before_payoff : Prop
  no_full_operator_skew_shortcut : Prop
  transport_pairing_bound :
    transportPairingMagnitude ≤
      commutatorConstant *
        (lowFrequencyLipschitzCost * highShellEnergy)

/-- The hostile-referee falsifier for the transport subreceipt: same fixed
topology, same declared costs, but a transport pairing larger than the
commutator price. -/
structure TransportCommutatorGapFalsifier
    (R : FixedTopologyTransportCommutatorReceipt) where
  same_fixed_topology : Prop
  same_declared_costs : Prop
  transport_exceeds_commutator_price :
    R.commutatorConstant *
      (R.lowFrequencyLipschitzCost * R.highShellEnergy) <
        R.transportPairingMagnitude

/-- A valid projected-transport commutator receipt rules out the corresponding
same-topology transport-gap falsifier. -/
theorem no_transport_commutator_gap_under_fixed_receipt
    (R : FixedTopologyTransportCommutatorReceipt)
    (F : TransportCommutatorGapFalsifier R) :
    False :=
  not_lt_of_ge R.transport_pairing_bound
    F.transport_exceeds_commutator_price

/-- Strengthened low-high operator receipt that exposes the projected transport
commutator as an actual subreceipt instead of a bare proposition.

This still does not prove the continuum PDE estimate.  It records the correct
proof shape: the local operator receipt is admissible only after the fixed
transport commutator and the stretch/separation receipts are independently
declared. -/
structure FixedTopologyLowHighOperatorReceiptWithCommutator
    (L : LowHighKinematicDichotomyLedger) where
  base : FixedTopologyLowHighOperatorReceipt L
  transportCommutator :
    FixedTopologyTransportCommutatorReceipt
  commutator_uses_same_topology :
    transportCommutator.topology = base.topology
  commutator_uses_same_lipschitz_cost :
    transportCommutator.lowFrequencyLipschitzCost =
      base.lowFrequencyLipschitzCost
  commutator_uses_same_high_shell_energy :
    transportCommutator.highShellEnergy = base.highShellEnergy
  base_commutator_prop_paid_by_subreceipt :
    base.projected_transport_commutator_receipt

/-- Forget the explicit commutator subreceipt after it has been paid. -/
def fixed_topology_receipt_of_commutator_strengthening
    (L : LowHighKinematicDichotomyLedger)
    (R : FixedTopologyLowHighOperatorReceiptWithCommutator L) :
    FixedTopologyLowHighOperatorReceipt L :=
  R.base

/-- Finite-core receipt for the low shells below the asymptotic LP/Bony
support gap.

The high-shell proof may use Bernstein constants uniform for `j >= j0`.
The finitely many shells below `j0` must not be smuggled into that asymptotic
claim.  They need a separately declared constant and a separately declared
reserve route before payoff is scored. -/
structure FixedLowShellCoreReceipt where
  cutoffShell : ℕ
  finiteCoreConstant : Real
  finite_core_declared_before_payoff : Prop
  finite_core_constant_nonnegative : 0 ≤ finiteCoreConstant
  finite_low_shell_operator_bound : Prop
  finite_low_shell_reserve_route : Prop
  no_asymptotic_constant_used_for_low_core : Prop

/-- Full fixed-topology receipt for the local low-high operator estimate.

This packages the high-shell LP/Bony receipt together with the finite-core
receipt demanded by a hostile referee.  The theorem-facing no-arbitrage handoff
still uses the high-shell receipt; the finite-core receipt records that the
low-shell exceptions have been handled by a predeclared finite reserve route,
not by silently changing constants after the payoff is observed. -/
structure FullFixedTopologyLowHighOperatorReceipt
    (L : LowHighKinematicDichotomyLedger) where
  highShellReceipt : FixedTopologyLowHighOperatorReceipt L
  lowShellCoreReceipt : FixedLowShellCoreReceipt

/-- Convert the fixed-topology local PDE receipt into the operator reality
check used by the global reserve adapter.

This is the precise handoff requested by the narrowed ZTARE substrate:
topology and analytic subreceipts first, ledger pricing second. -/
def operator_reality_check_of_fixed_topology_receipt
    (L : LowHighKinematicDichotomyLedger)
    (R : FixedTopologyLowHighOperatorReceipt L) :
    LowHighBonyOperatorEstimateRealityCheck L where
  lift := R.lift
  lpBonyConstant := R.lpBonyConstant
  lowFrequencyLipschitzCost := R.lowFrequencyLipschitzCost
  highShellEnergy := R.highShellEnergy
  operatorNorm := R.operatorNorm
  lp_bony_constant_declared_before_payoff :=
    R.topology.constants_declared_before_payoff
  lipschitz_cost_declared_before_payoff :=
    R.topology.lp_projectors_declared_before_payoff
  high_shell_energy_declared_before_payoff :=
    R.topology.h1_or_lambda_norm_declared
  operator_norm_declared_before_payoff :=
    R.topology.output_delta_projector_declared
  lp_bony_constant_nonnegative := R.lp_bony_constant_nonnegative
  high_shell_energy_nonnegative := R.high_shell_energy_nonnegative
  deformation_eq_lipschitz_energy := R.deformation_eq_lipschitz_energy
  leakage_le_operator_energy := R.leakage_le_operator_energy
  operator_bound_by_low_lip := R.operator_bound_by_low_lip
  low_nonconstant := R.low_nonconstant
  transfers_shell := R.transfers_shell

/-- LP/Bony low-high estimate before reserve absorption has been paid.

This is deliberately weaker than `LowHighLPBonyEstimateReceipt`: it contains
the leakage estimate and the fixed scalar factors, but not the final reserve
absorption inequality.  The latter must come from the global Lipschitz reserve
ledger below, otherwise the proof would silently assume the continuation
criterion. -/
structure LowHighLPBonyUnpaidEstimateReceipt
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
  low_nonconstant : lift.low_field_nonconstant
  transfers_shell : lift.shell_transfer

/-- Geometry-only low-high data for the flat-torus LP/Bony estimate.

This deliberately does not contain reserve absorption and does not identify a
low-field deformation energy with the interaction cost.  It records the
standard PDE vocabulary needed for the local estimate: low Lipschitz norm,
high shell `H1` energy, fixed dyadic gap, Leray/LP commutation, and the fact
that the scalar leakage variable is the positive energy-growth pairing being
estimated. -/
structure LowHighFlatTorusGeometryReceipt
    (L : LowHighKinematicDichotomyLedger) where
  topology : FixedLowHighLPBonyTopology
  lowFrequencyLipschitzCost : Real
  highShellEnergy : Real
  low_lipschitz_cost_nonnegative : 0 ≤ lowFrequencyLipschitzCost
  high_shell_energy_nonnegative : 0 ≤ highShellEnergy
  flat_periodic_torus_declared : Prop
  smooth_divergence_free_low_field : Prop
  high_field_lp_localized : Prop
  low_lip_is_grad_low_linf : Prop
  high_energy_is_lambda_shell_l2_sq : Prop
  fixed_low_high_gap : Prop
  leray_commutes_with_lp_lambda_derivatives : Prop
  leakage_gain_is_positive_energy_pairing : Prop
  no_raw_h1_operator_norm_claim : Prop

/-- Fixed-topology energy-budget form of the low-high LP/Bony estimate.

This is closer to the actual PDE proof than the one-line leakage bound:

* the projected transport term is controlled by the commutator receipt;
* the derivative falling on the low field in the stretch term is paid by the
  same low-frequency Lipschitz factor;
* the remaining support-gap/remainder term is paid by the declared separation
  constant.

The hard continuum proof still has to instantiate the three analytic bounds
from the flat-torus LP/Bony decomposition.  This record only prevents the
global bridge from treating the product estimate as an unanalyzed black box. -/
structure FixedTopologyLowHighEnergyBudgetReceipt
    (L : LowHighKinematicDichotomyLedger) where
  topology : FixedLowHighLPBonyTopology
  geometry : LowHighFlatTorusGeometryReceipt L
  transportCommutator : FixedTopologyTransportCommutatorReceipt
  lpBonyConstant : Real
  lowFrequencyLipschitzCost : Real
  highShellEnergy : Real
  stretchConstant : Real
  separationConstant : Real
  stretchPairingMagnitude : Real
  separationPairingMagnitude : Real
  lp_bony_constant_declared_before_payoff : Prop
  lipschitz_cost_declared_before_payoff : Prop
  high_shell_energy_declared_before_payoff : Prop
  stretch_receipt_declared_before_payoff : Prop
  separation_receipt_declared_before_payoff : Prop
  geometry_uses_same_topology :
    geometry.topology = topology
  geometry_uses_same_lipschitz_cost :
    geometry.lowFrequencyLipschitzCost = lowFrequencyLipschitzCost
  geometry_uses_same_high_shell_energy :
    geometry.highShellEnergy = highShellEnergy
  transport_uses_same_topology :
    transportCommutator.topology = topology
  transport_uses_same_lipschitz_cost :
    transportCommutator.lowFrequencyLipschitzCost =
      lowFrequencyLipschitzCost
  transport_uses_same_high_shell_energy :
    transportCommutator.highShellEnergy = highShellEnergy
  lp_bony_constant_nonnegative : 0 ≤ lpBonyConstant
  low_lipschitz_cost_nonnegative : 0 ≤ lowFrequencyLipschitzCost
  high_shell_energy_nonnegative : 0 ≤ highShellEnergy
  leakage_decomposes_into_standard_terms :
    L.leakageGain ≤
      transportCommutator.transportPairingMagnitude +
        stretchPairingMagnitude + separationPairingMagnitude
  stretch_bound :
    stretchPairingMagnitude ≤
      stretchConstant * (lowFrequencyLipschitzCost * highShellEnergy)
  separation_bound :
    separationPairingMagnitude ≤
      separationConstant * (lowFrequencyLipschitzCost * highShellEnergy)
  component_constants_le_lp_bony_constant :
    transportCommutator.commutatorConstant +
        stretchConstant + separationConstant ≤ lpBonyConstant

/-- The fixed-topology energy-budget receipt implies the advertised one-line
low-high LP/Bony leakage estimate. -/
theorem fixed_topology_energy_budget_leakage_bound
    (L : LowHighKinematicDichotomyLedger)
    (R : FixedTopologyLowHighEnergyBudgetReceipt L) :
    L.leakageGain ≤
      R.lpBonyConstant *
        (R.lowFrequencyLipschitzCost * R.highShellEnergy) := by
  let A := R.lowFrequencyLipschitzCost * R.highShellEnergy
  have hA : 0 ≤ A := by
    exact mul_nonneg R.low_lipschitz_cost_nonnegative
      R.high_shell_energy_nonnegative
  have htransport :
      R.transportCommutator.transportPairingMagnitude ≤
        R.transportCommutator.commutatorConstant * A := by
    have h :=
      R.transportCommutator.transport_pairing_bound
    rw [R.transport_uses_same_lipschitz_cost,
      R.transport_uses_same_high_shell_energy] at h
    exact h
  have hstretch :
      R.stretchPairingMagnitude ≤ R.stretchConstant * A := by
    exact R.stretch_bound
  have hseparation :
      R.separationPairingMagnitude ≤ R.separationConstant * A := by
    exact R.separation_bound
  have hsum :
      R.transportCommutator.transportPairingMagnitude +
          R.stretchPairingMagnitude + R.separationPairingMagnitude ≤
        (R.transportCommutator.commutatorConstant +
            R.stretchConstant + R.separationConstant) * A := by
    have hsum0 :
        R.transportCommutator.transportPairingMagnitude +
            R.stretchPairingMagnitude + R.separationPairingMagnitude ≤
          R.transportCommutator.commutatorConstant * A +
            R.stretchConstant * A + R.separationConstant * A :=
      add_le_add (add_le_add htransport hstretch) hseparation
    have hring :
        R.transportCommutator.commutatorConstant * A +
            R.stretchConstant * A + R.separationConstant * A =
          (R.transportCommutator.commutatorConstant +
              R.stretchConstant + R.separationConstant) * A := by
      ring
    simpa [hring] using hsum0
  have hcomponents :
      (R.transportCommutator.commutatorConstant +
          R.stretchConstant + R.separationConstant) * A ≤
        R.lpBonyConstant * A :=
    mul_le_mul_of_nonneg_right
      R.component_constants_le_lp_bony_constant hA
  exact R.leakage_decomposes_into_standard_terms.trans
    (hsum.trans hcomponents)

/-- The cost exposed by the geometry-only low-high energy budget.

This is the cost that must be embedded into the predeclared global
low-frequency Lipschitz ledger. -/
def lowHighFlatTorusEnergyBudgetCost
    {L : LowHighKinematicDichotomyLedger}
    (R : FixedTopologyLowHighEnergyBudgetReceipt L) : Real :=
  R.lpBonyConstant *
    (R.lowFrequencyLipschitzCost * R.highShellEnergy)

/-- The geometry-only energy-budget cost is nonnegative under the stated PDE
sign conditions. -/
theorem lowHighFlatTorusEnergyBudgetCost_nonnegative
    {L : LowHighKinematicDichotomyLedger}
    (R : FixedTopologyLowHighEnergyBudgetReceipt L) :
    0 ≤ lowHighFlatTorusEnergyBudgetCost R := by
  unfold lowHighFlatTorusEnergyBudgetCost
  exact mul_nonneg R.lp_bony_constant_nonnegative
    (mul_nonneg R.low_lipschitz_cost_nonnegative
      R.high_shell_energy_nonnegative)

/-- Same-ledger reserve link for the geometry-only low-high PDE estimate.

This is the non-tautological handoff: the local PDE estimate may only be used
globally after its exact cost is embedded into a fixed Lipschitz-reserve entry,
and that entry is identified with the same low-high ledger reserve loss. -/
structure LowHighEnergyBudgetReserveLink
    (L : LowHighKinematicDichotomyLedger)
    (R : FixedTopologyLowHighEnergyBudgetReceipt L)
    (G : LowFrequencyLipschitzLedger)
    (n : ℕ) where
  cost_eq_lipschitz_entry :
    G.lipschitzCost n = lowHighFlatTorusEnergyBudgetCost R
  reserve_eq_low_high_reserve :
    L.reserveLoss = G.reservePrice n
  cost_identity_declared_before_payoff : Prop
  reserve_identity_declared_before_payoff : Prop
  same_fixed_lp_bony_topology : Prop
  same_positive_energy_pairing_observable : Prop

/-- Hostile falsifier for a geometry-only energy-budget reserve link whose
pre-payoff source declarations are not actually paid. -/
inductive LowHighEnergyBudgetReserveLinkAntiTautologyFalsifier
    {L : LowHighKinematicDichotomyLedger}
    {R : FixedTopologyLowHighEnergyBudgetReceipt L}
    {G : LowFrequencyLipschitzLedger}
    {n : ℕ}
    (link : LowHighEnergyBudgetReserveLink L R G n) : Prop
  | cost_identity_not_declared :
      ¬ link.cost_identity_declared_before_payoff →
        LowHighEnergyBudgetReserveLinkAntiTautologyFalsifier link
  | reserve_identity_not_declared :
      ¬ link.reserve_identity_declared_before_payoff →
        LowHighEnergyBudgetReserveLinkAntiTautologyFalsifier link
  | topology_mismatch :
      ¬ link.same_fixed_lp_bony_topology →
        LowHighEnergyBudgetReserveLinkAntiTautologyFalsifier link
  | positive_energy_pairing_mismatch :
      ¬ link.same_positive_energy_pairing_observable →
        LowHighEnergyBudgetReserveLinkAntiTautologyFalsifier link

/-- Paid anti-tautology receipt for the geometry-only energy-budget reserve
link.

The link records source metadata; this receipt is the object downstream proofs
should require when they want those metadata propositions to be load-bearing. -/
structure LowHighEnergyBudgetReserveLinkAntiTautologyReceipt
    {L : LowHighKinematicDichotomyLedger}
    {R : FixedTopologyLowHighEnergyBudgetReceipt L}
    {G : LowFrequencyLipschitzLedger}
    {n : ℕ}
    (link : LowHighEnergyBudgetReserveLink L R G n) where
  cost_identity_paid : link.cost_identity_declared_before_payoff
  reserve_identity_paid : link.reserve_identity_declared_before_payoff
  same_topology_paid : link.same_fixed_lp_bony_topology
  same_positive_energy_pairing_observable_paid :
    link.same_positive_energy_pairing_observable

/-- A geometry-only energy-budget reserve link with a paid anti-tautology
receipt excludes every named source-metadata failure. -/
theorem no_low_high_energy_budget_reserve_link_of_anti_tautology_falsifier
    (L : LowHighKinematicDichotomyLedger)
    (R : FixedTopologyLowHighEnergyBudgetReceipt L)
    (G : LowFrequencyLipschitzLedger)
    (n : ℕ)
    (link : LowHighEnergyBudgetReserveLink L R G n)
    (receipt : LowHighEnergyBudgetReserveLinkAntiTautologyReceipt link)
    (F : LowHighEnergyBudgetReserveLinkAntiTautologyFalsifier link) :
    False := by
  cases F with
  | cost_identity_not_declared hbad =>
      exact hbad receipt.cost_identity_paid
  | reserve_identity_not_declared hbad =>
      exact hbad receipt.reserve_identity_paid
  | topology_mismatch hbad =>
      exact hbad receipt.same_topology_paid
  | positive_energy_pairing_mismatch hbad =>
      exact hbad receipt.same_positive_energy_pairing_observable_paid

/-- A no-survivor reserve entry prices the geometry-only low-high energy budget
without using the paid `ContinuumLowHighDeformationLift`. -/
theorem low_high_energy_budget_leakage_le_reserve_of_link
    (L : LowHighKinematicDichotomyLedger)
    (R : FixedTopologyLowHighEnergyBudgetReceipt L)
    (G : LowFrequencyLipschitzLedger)
    (C : LowFrequencyLipschitzControlCertificate G)
    (n : ℕ)
    (link : LowHighEnergyBudgetReserveLink L R G n)
    (hnosurvivor : FullLedgerNoSurvivor (G.block n)) :
    L.leakageGain ≤ L.reserveLoss := by
  have hleak :
      L.leakageGain ≤ lowHighFlatTorusEnergyBudgetCost R :=
    fixed_topology_energy_budget_leakage_bound L R
  have hpriced :
      G.lipschitzCost n ≤ G.reservePrice n :=
    C.no_survivor_prices_lipschitz n hnosurvivor
  have hcost :
      lowHighFlatTorusEnergyBudgetCost R ≤ G.reservePrice n := by
    rw [← link.cost_eq_lipschitz_entry]
    exact hpriced
  have hcharge :
      L.leakageGain ≤ G.reservePrice n :=
    hleak.trans hcost
  rw [link.reserve_eq_low_high_reserve]
  exact hcharge

/-- The geometry-only low-high energy-budget reserve route supplies the two
reserve fields required by `FlatTorusKillingModePDEAdapter`, provided the
obligation object exposes the typed interpretation of those fields.

The non-tautological content is the reserve-chain inequality: the low-high
leakage is first bounded by the fixed energy budget, then by the predeclared
global Lipschitz reserve entry, and finally by the same low-high ledger reserve
loss.  The only remaining bridge is semantic: the flat-torus obligation fields
are opaque `Prop`s, so a caller must identify them with the same typed ledger
inequalities rather than passing them as bare assumptions. -/
theorem flat_torus_reserve_fields_of_energy_budget_reserve_link
    (O : FlatTorusLowHighKinematicPDEObligation)
    (L : LowHighKinematicDichotomyLedger)
    (R : FixedTopologyLowHighEnergyBudgetReceipt L)
    (G : LowFrequencyLipschitzLedger)
    (C : LowFrequencyLipschitzControlCertificate G)
    (n : ℕ)
    (link : LowHighEnergyBudgetReserveLink L R G n)
    (hnosurvivor : FullLedgerNoSurvivor (G.block n))
    (positive_deformation_field_of_reserve_charge :
      L.leakageGain ≤ L.reserveLoss →
        O.positive_deformation_charged_by_reserve_loss)
    (trackb_price_field_of_ledger_price_charge :
      L.reserveLoss ≤ L.interaction.price →
        O.reserve_loss_charged_in_trackb_price) :
    O.positive_deformation_charged_by_reserve_loss ∧
      O.reserve_loss_charged_in_trackb_price := by
  have hreserve :
      L.leakageGain ≤ L.reserveLoss :=
    low_high_energy_budget_leakage_le_reserve_of_link
      L R G C n link hnosurvivor
  exact
    ⟨positive_deformation_field_of_reserve_charge hreserve,
      trackb_price_field_of_ledger_price_charge
        L.price_charges_reserve_loss⟩

/-- Audited-certificate form of the geometry-only flat-torus reserve field
handoff. -/
theorem flat_torus_reserve_fields_of_audited_energy_budget_reserve_link
    (O : FlatTorusLowHighKinematicPDEObligation)
    (L : LowHighKinematicDichotomyLedger)
    (R : FixedTopologyLowHighEnergyBudgetReceipt L)
    (G : LowFrequencyLipschitzLedger)
    (C : LowFrequencyLipschitzAuditedControlCertificate G)
    (n : ℕ)
    (link : LowHighEnergyBudgetReserveLink L R G n)
    (hnosurvivor : FullLedgerNoSurvivor (G.block n))
    (positive_deformation_field_of_reserve_charge :
      L.leakageGain ≤ L.reserveLoss →
        O.positive_deformation_charged_by_reserve_loss)
    (trackb_price_field_of_ledger_price_charge :
      L.reserveLoss ≤ L.interaction.price →
        O.reserve_loss_charged_in_trackb_price) :
    O.positive_deformation_charged_by_reserve_loss ∧
      O.reserve_loss_charged_in_trackb_price :=
  flat_torus_reserve_fields_of_energy_budget_reserve_link
    O L R G C.toControlCertificate n link hnosurvivor
    positive_deformation_field_of_reserve_charge
    trackb_price_field_of_ledger_price_charge

/-- Constructor-level flat-torus adapter from the geometry-only reserve route.

This packages the Killing-mode provenance and the low-high reserve chain into
the exact object GP216 now expects.  It still requires explicit semantic
handoffs from the opaque flat-torus obligation fields to the typed ledger
facts, so the theorem does not pretend that the remaining PDE identifications
are definitional. -/
def flat_torus_killing_pde_adapter_of_energy_budget_reserve_link
    (O : FlatTorusLowHighKinematicPDEObligation)
    (K : FlatTorusKillingModeConclusion)
    (L : LowHighKinematicDichotomyLedger)
    (R : FixedTopologyLowHighEnergyBudgetReceipt L)
    (G : LowFrequencyLipschitzLedger)
    (Cert : LowFrequencyLipschitzControlCertificate G)
    (n : ℕ)
    (link : LowHighEnergyBudgetReserveLink L R G n)
    (hnosurvivor : FullLedgerNoSurvivor (G.block n))
    (provenance : FlatTorusKillingModeProvenance K)
    (deformation_cost_declared_before_payoff :
      O.deformation_cost_declared_before_payoff)
    (zero_strain_fourier_rigidity_handoff :
      K.nonzero_modes_zero_amplitude →
        O.zero_strain_nonzero_fourier_modes_vanish)
    (zero_mode_killing_lift_handoff :
      K.only_zero_mode_can_remain →
        O.zero_deformation_implies_killing_low_field)
    (constant_translation_classification_handoff :
      K.constant_translation_branch →
        O.flat_torus_killing_fields_are_constant_translations)
    (constant_translation_shell_handoff :
      K.constant_translation_branch →
        O.constant_translation_preserves_lp_shells)
    (shell_obstruction_positive_deformation_handoff :
      K.shell_transfer_requires_nonzero_strain →
        O.nonconstant_shell_transfer_forces_positive_deformation)
    (positive_deformation_field_of_reserve_charge :
      L.leakageGain ≤ L.reserveLoss →
        O.positive_deformation_charged_by_reserve_loss)
    (trackb_price_field_of_ledger_price_charge :
      L.reserveLoss ≤ L.interaction.price →
        O.reserve_loss_charged_in_trackb_price) :
    FlatTorusKillingModePDEAdapter O K := by
  have hreserve :=
    flat_torus_reserve_fields_of_energy_budget_reserve_link
      O L R G Cert n link hnosurvivor
      positive_deformation_field_of_reserve_charge
      trackb_price_field_of_ledger_price_charge
  exact
    { provenance := provenance
      deformation_cost_declared_before_payoff :=
        deformation_cost_declared_before_payoff
      zero_strain_fourier_rigidity_handoff :=
        zero_strain_fourier_rigidity_handoff
      zero_mode_killing_lift_handoff :=
        zero_mode_killing_lift_handoff
      constant_translation_classification_handoff :=
        constant_translation_classification_handoff
      constant_translation_shell_handoff :=
        constant_translation_shell_handoff
      shell_obstruction_positive_deformation_handoff :=
        shell_obstruction_positive_deformation_handoff
      positive_deformation_charged_by_reserve_loss := hreserve.1
      reserve_loss_charged_in_trackb_price := hreserve.2 }

/-- Audited-certificate constructor-level flat-torus adapter from the
geometry-only reserve route. -/
def flat_torus_killing_pde_adapter_of_audited_energy_budget_reserve_link
    (O : FlatTorusLowHighKinematicPDEObligation)
    (K : FlatTorusKillingModeConclusion)
    (L : LowHighKinematicDichotomyLedger)
    (R : FixedTopologyLowHighEnergyBudgetReceipt L)
    (G : LowFrequencyLipschitzLedger)
    (Cert : LowFrequencyLipschitzAuditedControlCertificate G)
    (n : ℕ)
    (link : LowHighEnergyBudgetReserveLink L R G n)
    (hnosurvivor : FullLedgerNoSurvivor (G.block n))
    (provenance : FlatTorusKillingModeProvenance K)
    (deformation_cost_declared_before_payoff :
      O.deformation_cost_declared_before_payoff)
    (zero_strain_fourier_rigidity_handoff :
      K.nonzero_modes_zero_amplitude →
        O.zero_strain_nonzero_fourier_modes_vanish)
    (zero_mode_killing_lift_handoff :
      K.only_zero_mode_can_remain →
        O.zero_deformation_implies_killing_low_field)
    (constant_translation_classification_handoff :
      K.constant_translation_branch →
        O.flat_torus_killing_fields_are_constant_translations)
    (constant_translation_shell_handoff :
      K.constant_translation_branch →
        O.constant_translation_preserves_lp_shells)
    (shell_obstruction_positive_deformation_handoff :
      K.shell_transfer_requires_nonzero_strain →
        O.nonconstant_shell_transfer_forces_positive_deformation)
    (positive_deformation_field_of_reserve_charge :
      L.leakageGain ≤ L.reserveLoss →
        O.positive_deformation_charged_by_reserve_loss)
    (trackb_price_field_of_ledger_price_charge :
      L.reserveLoss ≤ L.interaction.price →
        O.reserve_loss_charged_in_trackb_price) :
    FlatTorusKillingModePDEAdapter O K :=
  flat_torus_killing_pde_adapter_of_energy_budget_reserve_link
    O K L R G Cert.toControlCertificate n link hnosurvivor provenance
    deformation_cost_declared_before_payoff
    zero_strain_fourier_rigidity_handoff
    zero_mode_killing_lift_handoff
    constant_translation_classification_handoff
    constant_translation_shell_handoff
    shell_obstruction_positive_deformation_handoff
    positive_deformation_field_of_reserve_charge
    trackb_price_field_of_ledger_price_charge

/-- Geometry-only LP/Bony energy budget plus a same-ledger Lipschitz reserve
link prices the low-high interaction. -/
theorem low_high_no_arbitrage_of_energy_budget_reserve_link
    (L : LowHighKinematicDichotomyLedger)
    (R : FixedTopologyLowHighEnergyBudgetReceipt L)
    (G : LowFrequencyLipschitzLedger)
    (C : LowFrequencyLipschitzControlCertificate G)
    (n : ℕ)
    (link : LowHighEnergyBudgetReserveLink L R G n)
    (hnosurvivor : FullLedgerNoSurvivor (G.block n)) :
    InteractionNoArbitrage L.interaction := by
  unfold InteractionNoArbitrage
  have hreserve :
      L.leakageGain ≤ L.reserveLoss :=
    low_high_energy_budget_leakage_le_reserve_of_link
      L R G C n link hnosurvivor
  exact L.payoff_le_leakage_gain.trans
    (hreserve.trans L.price_charges_reserve_loss)

/-- Lift-free hostile falsifier for the geometry-only reserve route. -/
structure LowHighEnergyBudgetReserveShortfallFalsifier
    (L : LowHighKinematicDichotomyLedger) where
  positive_leakage : 0 < L.leakageGain
  reserve_shortfall : L.reserveLoss < L.leakageGain

/-- A priced geometry-only energy budget rules out a same-ledger reserve
shortfall without invoking a continuum deformation lift. -/
theorem no_low_high_energy_budget_reserve_shortfall_of_link
    (L : LowHighKinematicDichotomyLedger)
    (R : FixedTopologyLowHighEnergyBudgetReceipt L)
    (G : LowFrequencyLipschitzLedger)
    (C : LowFrequencyLipschitzControlCertificate G)
    (n : ℕ)
    (link : LowHighEnergyBudgetReserveLink L R G n)
    (hnosurvivor : FullLedgerNoSurvivor (G.block n))
    (F : LowHighEnergyBudgetReserveShortfallFalsifier L) :
    False := by
  have hreserve :
      L.leakageGain ≤ L.reserveLoss :=
    low_high_energy_budget_leakage_le_reserve_of_link
      L R G C n link hnosurvivor
  exact not_lt_of_ge hreserve F.reserve_shortfall

/-- Convert an operator-norm reality check into the unpaid LP/Bony receipt.

This is the smallest non-tautological handoff for Boss Fight 2: a future PDE
proof should produce the operator-norm estimate, not the already-multiplied
ledger inequality. -/
def unpaid_lp_bony_receipt_of_operator_reality_check
    (L : LowHighKinematicDichotomyLedger)
    (R : LowHighBonyOperatorEstimateRealityCheck L) :
    LowHighLPBonyUnpaidEstimateReceipt L where
  lift := R.lift
  lpBonyConstant := R.lpBonyConstant
  lowFrequencyLipschitzCost := R.lowFrequencyLipschitzCost
  highShellEnergy := R.highShellEnergy
  lp_bony_constant_declared_before_payoff :=
    R.lp_bony_constant_declared_before_payoff
  lipschitz_cost_declared_before_payoff :=
    R.lipschitz_cost_declared_before_payoff
  high_shell_energy_declared_before_payoff :=
    R.high_shell_energy_declared_before_payoff
  lp_bony_constant_nonnegative := R.lp_bony_constant_nonnegative
  high_shell_energy_nonnegative := R.high_shell_energy_nonnegative
  deformation_eq_lipschitz_energy := R.deformation_eq_lipschitz_energy
  leakage_bound := by
    have hoperator :
        R.operatorNorm * R.highShellEnergy ≤
          (R.lpBonyConstant * R.lowFrequencyLipschitzCost) *
            R.highShellEnergy :=
      mul_le_mul_of_nonneg_right
        R.operator_bound_by_low_lip
        R.high_shell_energy_nonnegative
    calc
      L.leakageGain ≤ R.operatorNorm * R.highShellEnergy :=
        R.leakage_le_operator_energy
      _ ≤ (R.lpBonyConstant * R.lowFrequencyLipschitzCost) *
            R.highShellEnergy := hoperator
      _ = R.lpBonyConstant *
            (R.lowFrequencyLipschitzCost * R.highShellEnergy) := by
        ring
  low_nonconstant := R.low_nonconstant
  transfers_shell := R.transfers_shell

/-- Forget reserve absorption from a paid LP/Bony receipt to expose the unpaid
local PDE estimate expected by the global Lipschitz-reserve adapter. -/
def unpaid_lp_bony_receipt_of_paid_lp_bony_estimate_receipt
    (L : LowHighKinematicDichotomyLedger)
    (R : LowHighLPBonyEstimateReceipt L) :
    LowHighLPBonyUnpaidEstimateReceipt L where
  lift := R.lift
  lpBonyConstant := R.lpBonyConstant
  lowFrequencyLipschitzCost := R.lowFrequencyLipschitzCost
  highShellEnergy := R.highShellEnergy
  lp_bony_constant_declared_before_payoff :=
    R.lp_bony_constant_declared_before_payoff
  lipschitz_cost_declared_before_payoff :=
    R.lipschitz_cost_declared_before_payoff
  high_shell_energy_declared_before_payoff :=
    R.high_shell_energy_declared_before_payoff
  lp_bony_constant_nonnegative := R.lp_bony_constant_nonnegative
  high_shell_energy_nonnegative := R.high_shell_energy_nonnegative
  deformation_eq_lipschitz_energy := R.deformation_eq_lipschitz_energy
  leakage_bound := R.leakage_bound
  low_nonconstant := R.low_nonconstant
  transfers_shell := R.transfers_shell

/-- The declared LP/Bony cost whose price must come from the global reserve
ledger. -/
def lowHighLPBonyCost
    {L : LowHighKinematicDichotomyLedger}
    (R : LowHighLPBonyUnpaidEstimateReceipt L) : Real :=
  R.lpBonyConstant * (R.lowFrequencyLipschitzCost * R.highShellEnergy)

/-- The unpaid LP/Bony cost is nonnegative on an active nonconstant shell
transfer.  This uses the geometry-deformation field, not a post-hoc price
identity. -/
theorem lowHighLPBonyCost_nonnegative
    {L : LowHighKinematicDichotomyLedger}
    (R : LowHighLPBonyUnpaidEstimateReceipt L) :
    0 ≤ lowHighLPBonyCost R := by
  unfold lowHighLPBonyCost
  have hdef :
      0 < R.lift.deformationEnergy :=
    R.lift.positive_deformation_of_nonconstant_shell_transfer
      R.low_nonconstant R.transfers_shell
  rw [R.deformation_eq_lipschitz_energy] at hdef
  exact mul_nonneg R.lp_bony_constant_nonnegative (le_of_lt hdef)

/-- Link between one low-high LP/Bony receipt and one entry of the global
low-frequency Lipschitz reserve ledger.

The link is anti-tautological only if the cost and reserve identities are fixed
before payoff is scored.  Lean records that as propositions; the future PDE
proof must instantiate them from a declared LP/Bony decomposition. -/
structure LowHighLipschitzReserveLink
    (L : LowHighKinematicDichotomyLedger)
    (R : LowHighLPBonyUnpaidEstimateReceipt L)
    (G : LowFrequencyLipschitzLedger)
    (n : ℕ) where
  cost_eq_lipschitz_entry :
    G.lipschitzCost n = lowHighLPBonyCost R
  reserve_eq_low_high_reserve :
    L.reserveLoss = G.reservePrice n
  cost_identity_declared_before_payoff : Prop
  reserve_identity_declared_before_payoff : Prop
  same_lp_bony_topology : Prop

/-- Hostile falsifier for a low-high reserve link whose pre-payoff declarations
are not actually present. -/
inductive LowHighReserveLinkAntiTautologyFalsifier
    {L : LowHighKinematicDichotomyLedger}
    {R : LowHighLPBonyUnpaidEstimateReceipt L}
    {G : LowFrequencyLipschitzLedger}
    {n : ℕ}
    (link : LowHighLipschitzReserveLink L R G n) : Prop
  | cost_identity_not_declared :
      ¬ link.cost_identity_declared_before_payoff →
        LowHighReserveLinkAntiTautologyFalsifier link
  | reserve_identity_not_declared :
      ¬ link.reserve_identity_declared_before_payoff →
        LowHighReserveLinkAntiTautologyFalsifier link
  | topology_mismatch :
      ¬ link.same_lp_bony_topology →
        LowHighReserveLinkAntiTautologyFalsifier link

/-- Proof receipt that the reserve-link anti-tautology declarations have
actually been paid.  The link fields themselves are metadata propositions; this
separate object prevents Lean from treating named metadata as proof. -/
structure LowHighReserveLinkAntiTautologyReceipt
    {L : LowHighKinematicDichotomyLedger}
    {R : LowHighLPBonyUnpaidEstimateReceipt L}
    {G : LowFrequencyLipschitzLedger}
    {n : ℕ}
    (link : LowHighLipschitzReserveLink L R G n) where
  cost_identity_paid : link.cost_identity_declared_before_payoff
  reserve_identity_paid : link.reserve_identity_declared_before_payoff
  same_topology_paid : link.same_lp_bony_topology

/-- A reserve link with a paid anti-tautology receipt cannot coexist with a
falsifier negating one of the paid declarations. -/
theorem no_low_high_lipschitz_reserve_link_of_anti_tautology_falsifier
    (L : LowHighKinematicDichotomyLedger)
    (R : LowHighLPBonyUnpaidEstimateReceipt L)
    (G : LowFrequencyLipschitzLedger)
    (n : ℕ)
    (link : LowHighLipschitzReserveLink L R G n)
    (receipt : LowHighReserveLinkAntiTautologyReceipt link)
    (F : LowHighReserveLinkAntiTautologyFalsifier link) :
    False := by
  cases F with
  | cost_identity_not_declared hbad =>
      exact hbad receipt.cost_identity_paid
  | reserve_identity_not_declared hbad =>
      exact hbad receipt.reserve_identity_paid
  | topology_mismatch hbad =>
      exact hbad receipt.same_topology_paid

/-- A no-survivor block prices the linked low-high LP/Bony cost by the global
reserve entry. -/
theorem low_high_lipschitz_reserve_link_cost_le_reserve
    (L : LowHighKinematicDichotomyLedger)
    (R : LowHighLPBonyUnpaidEstimateReceipt L)
    (G : LowFrequencyLipschitzLedger)
    (C : LowFrequencyLipschitzControlCertificate G)
    (n : ℕ)
    (link : LowHighLipschitzReserveLink L R G n)
    (hnosurvivor : FullLedgerNoSurvivor (G.block n)) :
    lowHighLPBonyCost R ≤ G.reservePrice n := by
  have hpriced :
      G.lipschitzCost n ≤ G.reservePrice n :=
    C.no_survivor_prices_lipschitz n hnosurvivor
  rw [← link.cost_eq_lipschitz_entry]
  exact hpriced

/-- Linked LP/Bony leakage is charged by the same low-high ledger reserve. -/
theorem low_high_leakage_le_reserve_of_lipschitz_reserve_link
    (L : LowHighKinematicDichotomyLedger)
    (R : LowHighLPBonyUnpaidEstimateReceipt L)
    (G : LowFrequencyLipschitzLedger)
    (C : LowFrequencyLipschitzControlCertificate G)
    (n : ℕ)
    (link : LowHighLipschitzReserveLink L R G n)
    (hnosurvivor : FullLedgerNoSurvivor (G.block n)) :
    L.leakageGain ≤ L.reserveLoss := by
  have hleak :
      L.leakageGain ≤ lowHighLPBonyCost R := by
    unfold lowHighLPBonyCost
    exact R.leakage_bound
  have hcost :
      lowHighLPBonyCost R ≤ G.reservePrice n :=
    low_high_lipschitz_reserve_link_cost_le_reserve
      L R G C n link hnosurvivor
  have hcharge :
      L.leakageGain ≤ G.reservePrice n :=
    hleak.trans hcost
  rw [link.reserve_eq_low_high_reserve]
  exact hcharge

/-- The lift-bearing LP/Bony reserve route supplies the two reserve fields
required by `FlatTorusKillingModePDEAdapter`, once those opaque obligation
fields are tied to the typed ledger facts it proves.

Compared with the geometry-only route, this version also derives positive
declared deformation from the carried continuum lift's nonconstant shell
transfer receipt. -/
theorem flat_torus_reserve_fields_of_lipschitz_reserve_link
    (O : FlatTorusLowHighKinematicPDEObligation)
    (L : LowHighKinematicDichotomyLedger)
    (R : LowHighLPBonyUnpaidEstimateReceipt L)
    (G : LowFrequencyLipschitzLedger)
    (C : LowFrequencyLipschitzControlCertificate G)
    (n : ℕ)
    (link : LowHighLipschitzReserveLink L R G n)
    (hnosurvivor : FullLedgerNoSurvivor (G.block n))
    (positive_deformation_field_of_positive_reserve_charge :
      0 < L.deformationCost →
        L.leakageGain ≤ L.reserveLoss →
          O.positive_deformation_charged_by_reserve_loss)
    (trackb_price_field_of_ledger_price_charge :
      L.reserveLoss ≤ L.interaction.price →
        O.reserve_loss_charged_in_trackb_price) :
    O.positive_deformation_charged_by_reserve_loss ∧
      O.reserve_loss_charged_in_trackb_price := by
  have hpositive :
      0 < L.deformationCost :=
    continuum_low_high_shell_transfer_forces_positive_deformation
      L R.lift R.low_nonconstant R.transfers_shell
  have hreserve :
      L.leakageGain ≤ L.reserveLoss :=
    low_high_leakage_le_reserve_of_lipschitz_reserve_link
      L R G C n link hnosurvivor
  exact
    ⟨positive_deformation_field_of_positive_reserve_charge
        hpositive hreserve,
      trackb_price_field_of_ledger_price_charge
        L.price_charges_reserve_loss⟩

/-- Audited-certificate form of the lift-bearing flat-torus reserve field
handoff. -/
theorem flat_torus_reserve_fields_of_audited_lipschitz_reserve_link
    (O : FlatTorusLowHighKinematicPDEObligation)
    (L : LowHighKinematicDichotomyLedger)
    (R : LowHighLPBonyUnpaidEstimateReceipt L)
    (G : LowFrequencyLipschitzLedger)
    (C : LowFrequencyLipschitzAuditedControlCertificate G)
    (n : ℕ)
    (link : LowHighLipschitzReserveLink L R G n)
    (hnosurvivor : FullLedgerNoSurvivor (G.block n))
    (positive_deformation_field_of_positive_reserve_charge :
      0 < L.deformationCost →
        L.leakageGain ≤ L.reserveLoss →
          O.positive_deformation_charged_by_reserve_loss)
    (trackb_price_field_of_ledger_price_charge :
      L.reserveLoss ≤ L.interaction.price →
        O.reserve_loss_charged_in_trackb_price) :
    O.positive_deformation_charged_by_reserve_loss ∧
      O.reserve_loss_charged_in_trackb_price :=
  flat_torus_reserve_fields_of_lipschitz_reserve_link
    O L R G C.toControlCertificate n link hnosurvivor
    positive_deformation_field_of_positive_reserve_charge
    trackb_price_field_of_ledger_price_charge

/-- Constructor-level flat-torus adapter from the lift-bearing Lipschitz
reserve route.

Compared with the geometry-only constructor, this version uses the continuum
low-high lift to pay the positive-deformation side condition that the opaque
flat-torus reserve field may require. -/
def flat_torus_killing_pde_adapter_of_lipschitz_reserve_link
    (O : FlatTorusLowHighKinematicPDEObligation)
    (K : FlatTorusKillingModeConclusion)
    (L : LowHighKinematicDichotomyLedger)
    (R : LowHighLPBonyUnpaidEstimateReceipt L)
    (G : LowFrequencyLipschitzLedger)
    (Cert : LowFrequencyLipschitzControlCertificate G)
    (n : ℕ)
    (link : LowHighLipschitzReserveLink L R G n)
    (hnosurvivor : FullLedgerNoSurvivor (G.block n))
    (provenance : FlatTorusKillingModeProvenance K)
    (deformation_cost_declared_before_payoff :
      O.deformation_cost_declared_before_payoff)
    (zero_strain_fourier_rigidity_handoff :
      K.nonzero_modes_zero_amplitude →
        O.zero_strain_nonzero_fourier_modes_vanish)
    (zero_mode_killing_lift_handoff :
      K.only_zero_mode_can_remain →
        O.zero_deformation_implies_killing_low_field)
    (constant_translation_classification_handoff :
      K.constant_translation_branch →
        O.flat_torus_killing_fields_are_constant_translations)
    (constant_translation_shell_handoff :
      K.constant_translation_branch →
        O.constant_translation_preserves_lp_shells)
    (shell_obstruction_positive_deformation_handoff :
      K.shell_transfer_requires_nonzero_strain →
        O.nonconstant_shell_transfer_forces_positive_deformation)
    (positive_deformation_field_of_positive_reserve_charge :
      0 < L.deformationCost →
        L.leakageGain ≤ L.reserveLoss →
          O.positive_deformation_charged_by_reserve_loss)
    (trackb_price_field_of_ledger_price_charge :
      L.reserveLoss ≤ L.interaction.price →
        O.reserve_loss_charged_in_trackb_price) :
    FlatTorusKillingModePDEAdapter O K := by
  have hreserve :=
    flat_torus_reserve_fields_of_lipschitz_reserve_link
      O L R G Cert n link hnosurvivor
      positive_deformation_field_of_positive_reserve_charge
      trackb_price_field_of_ledger_price_charge
  exact
    { provenance := provenance
      deformation_cost_declared_before_payoff :=
        deformation_cost_declared_before_payoff
      zero_strain_fourier_rigidity_handoff :=
        zero_strain_fourier_rigidity_handoff
      zero_mode_killing_lift_handoff :=
        zero_mode_killing_lift_handoff
      constant_translation_classification_handoff :=
        constant_translation_classification_handoff
      constant_translation_shell_handoff :=
        constant_translation_shell_handoff
      shell_obstruction_positive_deformation_handoff :=
        shell_obstruction_positive_deformation_handoff
      positive_deformation_charged_by_reserve_loss := hreserve.1
      reserve_loss_charged_in_trackb_price := hreserve.2 }

/-- Audited-certificate constructor-level flat-torus adapter from the
lift-bearing Lipschitz reserve route. -/
def flat_torus_killing_pde_adapter_of_audited_lipschitz_reserve_link
    (O : FlatTorusLowHighKinematicPDEObligation)
    (K : FlatTorusKillingModeConclusion)
    (L : LowHighKinematicDichotomyLedger)
    (R : LowHighLPBonyUnpaidEstimateReceipt L)
    (G : LowFrequencyLipschitzLedger)
    (Cert : LowFrequencyLipschitzAuditedControlCertificate G)
    (n : ℕ)
    (link : LowHighLipschitzReserveLink L R G n)
    (hnosurvivor : FullLedgerNoSurvivor (G.block n))
    (provenance : FlatTorusKillingModeProvenance K)
    (deformation_cost_declared_before_payoff :
      O.deformation_cost_declared_before_payoff)
    (zero_strain_fourier_rigidity_handoff :
      K.nonzero_modes_zero_amplitude →
        O.zero_strain_nonzero_fourier_modes_vanish)
    (zero_mode_killing_lift_handoff :
      K.only_zero_mode_can_remain →
        O.zero_deformation_implies_killing_low_field)
    (constant_translation_classification_handoff :
      K.constant_translation_branch →
        O.flat_torus_killing_fields_are_constant_translations)
    (constant_translation_shell_handoff :
      K.constant_translation_branch →
        O.constant_translation_preserves_lp_shells)
    (shell_obstruction_positive_deformation_handoff :
      K.shell_transfer_requires_nonzero_strain →
        O.nonconstant_shell_transfer_forces_positive_deformation)
    (positive_deformation_field_of_positive_reserve_charge :
      0 < L.deformationCost →
        L.leakageGain ≤ L.reserveLoss →
          O.positive_deformation_charged_by_reserve_loss)
    (trackb_price_field_of_ledger_price_charge :
      L.reserveLoss ≤ L.interaction.price →
        O.reserve_loss_charged_in_trackb_price) :
    FlatTorusKillingModePDEAdapter O K :=
  flat_torus_killing_pde_adapter_of_lipschitz_reserve_link
    O K L R G Cert.toControlCertificate n link hnosurvivor provenance
    deformation_cost_declared_before_payoff
    zero_strain_fourier_rigidity_handoff
    zero_mode_killing_lift_handoff
    constant_translation_classification_handoff
    constant_translation_shell_handoff
    shell_obstruction_positive_deformation_handoff
    positive_deformation_field_of_positive_reserve_charge
    trackb_price_field_of_ledger_price_charge

/-- Concrete flat-torus PDE obligation induced by the lift-bearing LP/Bony
reserve source.

This is a source-provenance bridge, not a new PDE estimate.  It fixes the
opaque flat-torus duty fields to the exact Killing-mode and low-high reserve
facts produced by the source receipts.  Downstream code can still consume the
abstract `FlatTorusLowHighKinematicPDEObligation`, but this constructor avoids
supplying an arbitrary obligation object plus arbitrary semantic handoff
functions when the lift-bearing reserve route is the source. -/
def flat_torus_low_high_pde_obligation_of_lipschitz_reserve_source
    (K : FlatTorusKillingModeConclusion)
    (L : LowHighKinematicDichotomyLedger)
    (R : LowHighLPBonyUnpaidEstimateReceipt L) :
    FlatTorusLowHighKinematicPDEObligation where
  deformation_cost_declared_before_payoff :=
    R.lp_bony_constant_declared_before_payoff ∧
      R.lipschitz_cost_declared_before_payoff ∧
        R.high_shell_energy_declared_before_payoff
  zero_strain_nonzero_fourier_modes_vanish :=
    K.nonzero_modes_zero_amplitude
  zero_deformation_implies_killing_low_field :=
    K.only_zero_mode_can_remain
  flat_torus_killing_fields_are_constant_translations :=
    K.constant_translation_branch
  constant_translation_preserves_lp_shells :=
    K.constant_translation_branch
  nonconstant_shell_transfer_forces_positive_deformation :=
    K.shell_transfer_requires_nonzero_strain ∧
      0 < L.deformationCost
  positive_deformation_charged_by_reserve_loss :=
    0 < L.deformationCost ∧
      L.leakageGain ≤ L.reserveLoss
  reserve_loss_charged_in_trackb_price :=
    L.reserveLoss ≤ L.interaction.price

/-- Adapter from the lift-bearing LP/Bony reserve source to the concrete
flat-torus obligation generated by
`flat_torus_low_high_pde_obligation_of_lipschitz_reserve_source`.

The same source facts pay both the Killing-mode branch and the reserve/price
branch: positive deformation comes from the carried continuum low-high lift,
reserve charging comes from the linked Lipschitz reserve entry, and Track B
price charging is the ledger's own reserve-loss price field. -/
def flat_torus_killing_pde_adapter_of_typed_lipschitz_reserve_source
    (K : FlatTorusKillingModeConclusion)
    (L : LowHighKinematicDichotomyLedger)
    (R : LowHighLPBonyUnpaidEstimateReceipt L)
    (G : LowFrequencyLipschitzLedger)
    (Cert : LowFrequencyLipschitzControlCertificate G)
    (n : ℕ)
    (link : LowHighLipschitzReserveLink L R G n)
    (hnosurvivor : FullLedgerNoSurvivor (G.block n))
    (provenance : FlatTorusKillingModeProvenance K)
    (lp_bony_constant_declared_before_payoff_paid :
      R.lp_bony_constant_declared_before_payoff)
    (lipschitz_cost_declared_before_payoff_paid :
      R.lipschitz_cost_declared_before_payoff)
    (high_shell_energy_declared_before_payoff_paid :
      R.high_shell_energy_declared_before_payoff) :
    FlatTorusKillingModePDEAdapter
      (flat_torus_low_high_pde_obligation_of_lipschitz_reserve_source
        K L R)
      K := by
  have hpositive :
      0 < L.deformationCost :=
    continuum_low_high_shell_transfer_forces_positive_deformation
      L R.lift R.low_nonconstant R.transfers_shell
  have hreserve :
      L.leakageGain ≤ L.reserveLoss :=
    low_high_leakage_le_reserve_of_lipschitz_reserve_link
      L R G Cert n link hnosurvivor
  exact
    { provenance := provenance
      deformation_cost_declared_before_payoff :=
        ⟨lp_bony_constant_declared_before_payoff_paid,
          lipschitz_cost_declared_before_payoff_paid,
          high_shell_energy_declared_before_payoff_paid⟩
      zero_strain_fourier_rigidity_handoff := fun h => h
      zero_mode_killing_lift_handoff := fun h => h
      constant_translation_classification_handoff := fun h => h
      constant_translation_shell_handoff := fun h => h
      shell_obstruction_positive_deformation_handoff :=
        fun h => ⟨h, hpositive⟩
      positive_deformation_charged_by_reserve_loss :=
        ⟨hpositive, hreserve⟩
      reserve_loss_charged_in_trackb_price :=
        L.price_charges_reserve_loss }

/-- Audited-certificate form of the typed flat-torus lift-bearing source
adapter. -/
def flat_torus_killing_pde_adapter_of_typed_audited_lipschitz_reserve_source
    (K : FlatTorusKillingModeConclusion)
    (L : LowHighKinematicDichotomyLedger)
    (R : LowHighLPBonyUnpaidEstimateReceipt L)
    (G : LowFrequencyLipschitzLedger)
    (Cert : LowFrequencyLipschitzAuditedControlCertificate G)
    (n : ℕ)
    (link : LowHighLipschitzReserveLink L R G n)
    (hnosurvivor : FullLedgerNoSurvivor (G.block n))
    (provenance : FlatTorusKillingModeProvenance K)
    (lp_bony_constant_declared_before_payoff_paid :
      R.lp_bony_constant_declared_before_payoff)
    (lipschitz_cost_declared_before_payoff_paid :
      R.lipschitz_cost_declared_before_payoff)
    (high_shell_energy_declared_before_payoff_paid :
      R.high_shell_energy_declared_before_payoff) :
    FlatTorusKillingModePDEAdapter
      (flat_torus_low_high_pde_obligation_of_lipschitz_reserve_source
        K L R)
      K :=
  flat_torus_killing_pde_adapter_of_typed_lipschitz_reserve_source
    K L R G Cert.toControlCertificate n link hnosurvivor provenance
    lp_bony_constant_declared_before_payoff_paid
    lipschitz_cost_declared_before_payoff_paid
    high_shell_energy_declared_before_payoff_paid

/-- Source-first form of the typed flat-torus adapter: the Fourier/Killing
source supplies both the conclusion and its provenance, so callers cannot pass
an unrelated `FlatTorusKillingModeConclusion` beside an unrelated provenance
receipt. -/
def flat_torus_killing_pde_adapter_of_smooth_fourier_source_and_typed_lipschitz_reserve_source
    (S : FlatTorusSmoothKillingFourierSource)
    (L : LowHighKinematicDichotomyLedger)
    (R : LowHighLPBonyUnpaidEstimateReceipt L)
    (G : LowFrequencyLipschitzLedger)
    (Cert : LowFrequencyLipschitzControlCertificate G)
    (n : ℕ)
    (link : LowHighLipschitzReserveLink L R G n)
    (hnosurvivor : FullLedgerNoSurvivor (G.block n))
    (lp_bony_constant_declared_before_payoff_paid :
      R.lp_bony_constant_declared_before_payoff)
    (lipschitz_cost_declared_before_payoff_paid :
      R.lipschitz_cost_declared_before_payoff)
    (high_shell_energy_declared_before_payoff_paid :
      R.high_shell_energy_declared_before_payoff) :
    FlatTorusKillingModePDEAdapter
      (flat_torus_low_high_pde_obligation_of_lipschitz_reserve_source
        S.toConclusion L R)
      S.toConclusion :=
  flat_torus_killing_pde_adapter_of_typed_lipschitz_reserve_source
    S.toConclusion L R G Cert n link hnosurvivor S.toProvenance
    lp_bony_constant_declared_before_payoff_paid
    lipschitz_cost_declared_before_payoff_paid
    high_shell_energy_declared_before_payoff_paid

/-- Audited-certificate form of the source-first flat-torus adapter. -/
def flat_torus_killing_pde_adapter_of_smooth_fourier_source_and_typed_audited_lipschitz_reserve
    (S : FlatTorusSmoothKillingFourierSource)
    (L : LowHighKinematicDichotomyLedger)
    (R : LowHighLPBonyUnpaidEstimateReceipt L)
    (G : LowFrequencyLipschitzLedger)
    (Cert : LowFrequencyLipschitzAuditedControlCertificate G)
    (n : ℕ)
    (link : LowHighLipschitzReserveLink L R G n)
    (hnosurvivor : FullLedgerNoSurvivor (G.block n))
    (lp_bony_constant_declared_before_payoff_paid :
      R.lp_bony_constant_declared_before_payoff)
    (lipschitz_cost_declared_before_payoff_paid :
      R.lipschitz_cost_declared_before_payoff)
    (high_shell_energy_declared_before_payoff_paid :
      R.high_shell_energy_declared_before_payoff) :
    FlatTorusKillingModePDEAdapter
      (flat_torus_low_high_pde_obligation_of_lipschitz_reserve_source
        S.toConclusion L R)
      S.toConclusion :=
  flat_torus_killing_pde_adapter_of_smooth_fourier_source_and_typed_lipschitz_reserve_source
    S L R G Cert.toControlCertificate n link hnosurvivor
    lp_bony_constant_declared_before_payoff_paid
    lipschitz_cost_declared_before_payoff_paid
    high_shell_energy_declared_before_payoff_paid

/-- Direct satisfaction receipt for the concrete flat-torus PDE obligation
generated by a typed Lipschitz-reserve source. -/
def flat_torus_low_high_pde_satisfied_of_typed_lipschitz_reserve_source
    (K : FlatTorusKillingModeConclusion)
    (L : LowHighKinematicDichotomyLedger)
    (R : LowHighLPBonyUnpaidEstimateReceipt L)
    (G : LowFrequencyLipschitzLedger)
    (Cert : LowFrequencyLipschitzControlCertificate G)
    (n : ℕ)
    (link : LowHighLipschitzReserveLink L R G n)
    (hnosurvivor : FullLedgerNoSurvivor (G.block n))
    (provenance : FlatTorusKillingModeProvenance K)
    (lp_bony_constant_declared_before_payoff_paid :
      R.lp_bony_constant_declared_before_payoff)
    (lipschitz_cost_declared_before_payoff_paid :
      R.lipschitz_cost_declared_before_payoff)
    (high_shell_energy_declared_before_payoff_paid :
      R.high_shell_energy_declared_before_payoff) :
    FlatTorusLowHighKinematicPDEObligationSatisfied
      (flat_torus_low_high_pde_obligation_of_lipschitz_reserve_source
        K L R) :=
  flat_torus_low_high_pde_satisfied_of_killing_mode_adapter
    (flat_torus_low_high_pde_obligation_of_lipschitz_reserve_source
      K L R)
    K
    (flat_torus_killing_pde_adapter_of_typed_lipschitz_reserve_source
      K L R G Cert n link hnosurvivor provenance
      lp_bony_constant_declared_before_payoff_paid
      lipschitz_cost_declared_before_payoff_paid
      high_shell_energy_declared_before_payoff_paid)

/-- Source-first direct satisfaction receipt for the concrete flat-torus PDE
obligation generated by a typed Lipschitz-reserve source. -/
def flat_torus_low_high_pde_satisfied_of_smooth_fourier_source_and_typed_lipschitz_reserve_source
    (S : FlatTorusSmoothKillingFourierSource)
    (L : LowHighKinematicDichotomyLedger)
    (R : LowHighLPBonyUnpaidEstimateReceipt L)
    (G : LowFrequencyLipschitzLedger)
    (Cert : LowFrequencyLipschitzControlCertificate G)
    (n : ℕ)
    (link : LowHighLipschitzReserveLink L R G n)
    (hnosurvivor : FullLedgerNoSurvivor (G.block n))
    (lp_bony_constant_declared_before_payoff_paid :
      R.lp_bony_constant_declared_before_payoff)
    (lipschitz_cost_declared_before_payoff_paid :
      R.lipschitz_cost_declared_before_payoff)
    (high_shell_energy_declared_before_payoff_paid :
      R.high_shell_energy_declared_before_payoff) :
    FlatTorusLowHighKinematicPDEObligationSatisfied
      (flat_torus_low_high_pde_obligation_of_lipschitz_reserve_source
        S.toConclusion L R) :=
  flat_torus_low_high_pde_satisfied_of_killing_mode_adapter
    (flat_torus_low_high_pde_obligation_of_lipschitz_reserve_source
      S.toConclusion L R)
    S.toConclusion
    (flat_torus_killing_pde_adapter_of_smooth_fourier_source_and_typed_lipschitz_reserve_source
      S L R G Cert n link hnosurvivor
      lp_bony_constant_declared_before_payoff_paid
      lipschitz_cost_declared_before_payoff_paid
      high_shell_energy_declared_before_payoff_paid)

/-- Audited-certificate form of the direct flat-torus PDE satisfaction receipt
generated by a typed Lipschitz-reserve source. -/
def flat_torus_low_high_pde_satisfied_of_typed_audited_lipschitz_reserve_source
    (K : FlatTorusKillingModeConclusion)
    (L : LowHighKinematicDichotomyLedger)
    (R : LowHighLPBonyUnpaidEstimateReceipt L)
    (G : LowFrequencyLipschitzLedger)
    (Cert : LowFrequencyLipschitzAuditedControlCertificate G)
    (n : ℕ)
    (link : LowHighLipschitzReserveLink L R G n)
    (hnosurvivor : FullLedgerNoSurvivor (G.block n))
    (provenance : FlatTorusKillingModeProvenance K)
    (lp_bony_constant_declared_before_payoff_paid :
      R.lp_bony_constant_declared_before_payoff)
    (lipschitz_cost_declared_before_payoff_paid :
      R.lipschitz_cost_declared_before_payoff)
    (high_shell_energy_declared_before_payoff_paid :
      R.high_shell_energy_declared_before_payoff) :
    FlatTorusLowHighKinematicPDEObligationSatisfied
      (flat_torus_low_high_pde_obligation_of_lipschitz_reserve_source
        K L R) :=
  flat_torus_low_high_pde_satisfied_of_killing_mode_adapter
    (flat_torus_low_high_pde_obligation_of_lipschitz_reserve_source
      K L R)
    K
    (flat_torus_killing_pde_adapter_of_typed_audited_lipschitz_reserve_source
      K L R G Cert n link hnosurvivor provenance
      lp_bony_constant_declared_before_payoff_paid
      lipschitz_cost_declared_before_payoff_paid
      high_shell_energy_declared_before_payoff_paid)

/-- Audited-certificate form of the source-first direct flat-torus PDE
satisfaction receipt. -/
def flat_torus_low_high_pde_satisfied_of_smooth_fourier_source_and_typed_audited_lipschitz_reserve
    (S : FlatTorusSmoothKillingFourierSource)
    (L : LowHighKinematicDichotomyLedger)
    (R : LowHighLPBonyUnpaidEstimateReceipt L)
    (G : LowFrequencyLipschitzLedger)
    (Cert : LowFrequencyLipschitzAuditedControlCertificate G)
    (n : ℕ)
    (link : LowHighLipschitzReserveLink L R G n)
    (hnosurvivor : FullLedgerNoSurvivor (G.block n))
    (lp_bony_constant_declared_before_payoff_paid :
      R.lp_bony_constant_declared_before_payoff)
    (lipschitz_cost_declared_before_payoff_paid :
      R.lipschitz_cost_declared_before_payoff)
    (high_shell_energy_declared_before_payoff_paid :
      R.high_shell_energy_declared_before_payoff) :
    FlatTorusLowHighKinematicPDEObligationSatisfied
      (flat_torus_low_high_pde_obligation_of_lipschitz_reserve_source
        S.toConclusion L R) :=
  flat_torus_low_high_pde_satisfied_of_smooth_fourier_source_and_typed_lipschitz_reserve_source
    S L R G Cert.toControlCertificate n link hnosurvivor
    lp_bony_constant_declared_before_payoff_paid
    lipschitz_cost_declared_before_payoff_paid
    high_shell_energy_declared_before_payoff_paid

/-- If a no-survivor block prices the linked Lipschitz entry, then the unpaid
LP/Bony low-high receipt becomes a priced interaction.

This is the exact bridge from the finite low-high witness to the continuation
side: the low-high branch is not closed by a local estimate alone; the estimate
must land in a global reserve ledger that no-survivor blocks actually price. -/
theorem low_high_no_arbitrage_of_lipschitz_reserve_link
    (L : LowHighKinematicDichotomyLedger)
    (R : LowHighLPBonyUnpaidEstimateReceipt L)
    (G : LowFrequencyLipschitzLedger)
    (C : LowFrequencyLipschitzControlCertificate G)
    (n : ℕ)
    (link : LowHighLipschitzReserveLink L R G n)
    (hnosurvivor : FullLedgerNoSurvivor (G.block n)) :
    InteractionNoArbitrage L.interaction := by
  unfold InteractionNoArbitrage
  have hreserve :
      L.leakageGain ≤ L.reserveLoss :=
    low_high_leakage_le_reserve_of_lipschitz_reserve_link
      L R G C n link hnosurvivor
  exact L.payoff_le_leakage_gain.trans
    (hreserve.trans L.price_charges_reserve_loss)

/-- A linked LP/Bony receipt priced by the global Lipschitz reserve ledger
cannot coexist with a same-ledger low-high reserve shortfall.

This is the direct falsifier form of the smooth low-high shear branch: if the
local leakage estimate is valid, the cost is linked to a predeclared global
Lipschitz entry, and that entry is priced by a no-survivor block, then a
reserve underprice for the same interaction is impossible. -/
theorem no_low_high_lipschitz_reserve_link_with_bilinear_falsifier
    (L : LowHighKinematicDichotomyLedger)
    (R : LowHighLPBonyUnpaidEstimateReceipt L)
    (G : LowFrequencyLipschitzLedger)
    (C : LowFrequencyLipschitzControlCertificate G)
    (n : ℕ)
    (link : LowHighLipschitzReserveLink L R G n)
    (hnosurvivor : FullLedgerNoSurvivor (G.block n))
    (F : LowHighBilinearChargeFalsifier L) :
    False := by
  have hreserve :
      L.leakageGain ≤ L.reserveLoss :=
    low_high_leakage_le_reserve_of_lipschitz_reserve_link
      L R G C n link hnosurvivor
  exact not_lt_of_ge hreserve F.reserve_shortfall

/-- Shell-family closure for the low-high operator estimate.

The one-shell receipt above is not enough for a global Track B bridge.  A
candidate regularity argument must provide a fixed shell-indexed family of
low-high ledgers and unpaid LP/Bony receipts, together with a predeclared map
into the global low-frequency Lipschitz reserve ledger.  This structure records
that handoff without allowing the reserve entries to be selected after the
profitable shells have been observed. -/
structure LowHighShellReserveClosure
    (G : LowFrequencyLipschitzLedger) where
  shellLedger : ℕ → LowHighKinematicDichotomyLedger
  shellReceipt :
    ∀ j : ℕ, LowHighLPBonyUnpaidEstimateReceipt (shellLedger j)
  reserveIndex : ℕ → ℕ
  shellCost : ℕ → Real
  shell_cost_eq_receipt_cost :
    ∀ j : ℕ, shellCost j = lowHighLPBonyCost (shellReceipt j)
  shell_cost_declared_before_payoff : Prop
  reserve_index_declared_before_payoff : Prop
  same_fixed_lp_bony_topology_all_shells : Prop
  fixed_shell_gap_all_shells : Prop
  finite_low_shell_core_paid : Prop
  no_posthoc_shell_selection : Prop
  cost_embeds_in_lipschitz_entry :
    ∀ j : ℕ, shellCost j ≤ G.lipschitzCost (reserveIndex j)
  shell_reserve_is_same_ledger :
    ∀ j : ℕ, (shellLedger j).reserveLoss = G.reservePrice (reserveIndex j)
  prefix_cost_embeds_in_lipschitz_prefix :
    ∀ N : ℕ, nsPrefixSum shellCost N ≤ lipschitzPrefixCost G N

/-- Every declared low-high shell cost in a fixed shell-family closure is
nonnegative. -/
theorem low_high_shell_cost_nonnegative_of_reserve_closure
    (G : LowFrequencyLipschitzLedger)
    (S : LowHighShellReserveClosure G)
    (j : ℕ) :
    0 ≤ S.shellCost j := by
  rw [S.shell_cost_eq_receipt_cost j]
  exact lowHighLPBonyCost_nonnegative (S.shellReceipt j)

/-- The predeclared shell-family closure pays every local low-high receipt
pointwise once the linked global Lipschitz entries are priced by no-survivor
blocks.

This is the immediate formal upgrade demanded by the latest low-high operator
run: local operator control is not promoted to global closure until every shell
has a fixed reserve index and that indexed reserve is priced independently. -/
theorem low_high_shell_no_arbitrage_of_reserve_closure
    (G : LowFrequencyLipschitzLedger)
    (C : LowFrequencyLipschitzControlCertificate G)
    (S : LowHighShellReserveClosure G)
    (hnosurvivor : ∀ n : ℕ, FullLedgerNoSurvivor (G.block n))
    (j : ℕ) :
    InteractionNoArbitrage (S.shellLedger j).interaction := by
  unfold InteractionNoArbitrage
  have hpriced :
      G.lipschitzCost (S.reserveIndex j) ≤
        G.reservePrice (S.reserveIndex j) :=
    C.no_survivor_prices_lipschitz
      (S.reserveIndex j)
      (hnosurvivor (S.reserveIndex j))
  have hcost :
      lowHighLPBonyCost (S.shellReceipt j) ≤
        G.reservePrice (S.reserveIndex j) := by
    rw [← S.shell_cost_eq_receipt_cost j]
    exact (S.cost_embeds_in_lipschitz_entry j).trans hpriced
  have hreserve :
      (S.shellLedger j).leakageGain ≤ (S.shellLedger j).reserveLoss := by
    have hleak :
        (S.shellLedger j).leakageGain ≤ lowHighLPBonyCost (S.shellReceipt j) := by
      unfold lowHighLPBonyCost
      exact (S.shellReceipt j).leakage_bound
    have hcharge :
        (S.shellLedger j).leakageGain ≤
          G.reservePrice (S.reserveIndex j) :=
      hleak.trans hcost
    rw [S.shell_reserve_is_same_ledger j]
    exact hcharge
  exact (S.shellLedger j).payoff_le_leakage_gain.trans
    (hreserve.trans (S.shellLedger j).price_charges_reserve_loss)

/-- A predeclared low-high shell-family closure rules out a same-shell
underpriced bilinear falsifier at every shell. -/
theorem no_low_high_shell_reserve_closure_with_bilinear_falsifier
    (G : LowFrequencyLipschitzLedger)
    (C : LowFrequencyLipschitzControlCertificate G)
    (S : LowHighShellReserveClosure G)
    (hnosurvivor : ∀ n : ℕ, FullLedgerNoSurvivor (G.block n))
    (j : ℕ)
    (F : LowHighBilinearChargeFalsifier (S.shellLedger j)) :
    False := by
  have hpriced :
      G.lipschitzCost (S.reserveIndex j) ≤
        G.reservePrice (S.reserveIndex j) :=
    C.no_survivor_prices_lipschitz
      (S.reserveIndex j)
      (hnosurvivor (S.reserveIndex j))
  have hcost :
      lowHighLPBonyCost (S.shellReceipt j) ≤
        G.reservePrice (S.reserveIndex j) := by
    rw [← S.shell_cost_eq_receipt_cost j]
    exact (S.cost_embeds_in_lipschitz_entry j).trans hpriced
  have hreserve :
      (S.shellLedger j).leakageGain ≤ (S.shellLedger j).reserveLoss := by
    have hleak :
        (S.shellLedger j).leakageGain ≤ lowHighLPBonyCost (S.shellReceipt j) := by
      unfold lowHighLPBonyCost
      exact (S.shellReceipt j).leakage_bound
    have hcharge :
        (S.shellLedger j).leakageGain ≤
          G.reservePrice (S.reserveIndex j) :=
      hleak.trans hcost
    rw [S.shell_reserve_is_same_ledger j]
    exact hcharge
  exact not_lt_of_ge hreserve F.reserve_shortfall

/-- Finite-prefix version of the shell-family reserve closure.

If a shell-indexed market-impact stream is pointwise embedded into the same
global Lipschitz ledger, any overbudget prefix is a direct falsifier.  This
keeps the limit-passage burden explicit: the remaining PDE proof must control
prefixes of the declared shell costs, not merely prove a local shell estimate. -/
theorem no_overbudget_low_high_shell_prefix_of_reserve_closure
    (G : LowFrequencyLipschitzLedger)
    (C : LowFrequencyLipschitzControlCertificate G)
    (S : LowHighShellReserveClosure G)
    (hnosurvivor : ∀ n : ℕ, FullLedgerNoSurvivor (G.block n))
    (N : ℕ)
    (hover : G.criticalBudget < nsPrefixSum S.shellCost N) :
    False := by
  have hlip_over : G.criticalBudget < lipschitzPrefixCost G N :=
    lt_of_lt_of_le hover (S.prefix_cost_embeds_in_lipschitz_prefix N)
  exact no_overbudget_lipschitz_prefix_under_no_survivor
    G C hnosurvivor N hlip_over

/-- A finite overbudget prefix is the concrete falsifier for a proposed
low-high shell-family reserve closure.

This packages the hostile-search target without allowing the analytic topology
to move after payoff is observed: the shell closure `S` is fixed first, then a
single prefix that exceeds the declared critical budget breaks it. -/
structure LowHighShellPrefixReserveFalsifier
    (G : LowFrequencyLipschitzLedger)
    (_S : LowHighShellReserveClosure G) where
  prefixLength : ℕ
  prefix_exceeds_declared_budget :
    G.criticalBudget < nsPrefixSum _S.shellCost prefixLength

/-- A proposed low-high shell-family reserve closure cannot coexist with its
own finite overbudget prefix falsifier. -/
theorem no_low_high_shell_reserve_closure_with_prefix_falsifier
    (G : LowFrequencyLipschitzLedger)
    (C : LowFrequencyLipschitzControlCertificate G)
    (S : LowHighShellReserveClosure G)
    (hnosurvivor : ∀ n : ℕ, FullLedgerNoSurvivor (G.block n))
    (F : LowHighShellPrefixReserveFalsifier G S) :
    False :=
  no_overbudget_low_high_shell_prefix_of_reserve_closure
    G C S hnosurvivor F.prefixLength F.prefix_exceeds_declared_budget

/-- Unbounded low-high shell prefixes are impossible under the fixed reserve
closure and no-survivor pricing.

This is the limit-passage version of the previous theorem and the exact local
form of the Clay-facing uncertainty: either the analytic PDE proof supplies
uniform prefix control, or a smooth dyadic sequence with unbounded prefixes is a
direct falsifier of the closure. -/
theorem no_unbounded_low_high_shell_prefix_of_reserve_closure
    (G : LowFrequencyLipschitzLedger)
    (C : LowFrequencyLipschitzControlCertificate G)
    (S : LowHighShellReserveClosure G)
    (hnosurvivor : ∀ n : ℕ, FullLedgerNoSurvivor (G.block n))
    (hunbounded :
      ∀ B : Real, ∃ N : ℕ, B < nsPrefixSum S.shellCost N) :
    False := by
  obtain ⟨N, hover⟩ := hunbounded G.criticalBudget
  exact no_overbudget_low_high_shell_prefix_of_reserve_closure
    G C S hnosurvivor N hover

/-- Pointwise-unbounded low-high shell costs force an overbudget prefix under
the same fixed shell-family reserve closure. -/
theorem no_pointwise_unbounded_low_high_shell_cost_of_reserve_closure
    (G : LowFrequencyLipschitzLedger)
    (C : LowFrequencyLipschitzControlCertificate G)
    (S : LowHighShellReserveClosure G)
    (hnosurvivor : ∀ n : ℕ, FullLedgerNoSurvivor (G.block n))
    (hunbounded :
      ∀ B : Real, ∃ j : ℕ, B < S.shellCost j) :
    False := by
  have hnonnegative :
      ∀ j : ℕ, 0 ≤ S.shellCost j :=
    low_high_shell_cost_nonnegative_of_reserve_closure G S
  have hprefix_unbounded :
      ∀ B : Real, ∃ N : ℕ, B < nsPrefixSum S.shellCost N :=
    ns_prefix_sum_unbounded_of_pointwise_unbounded_nonnegative
      S.shellCost hnonnegative hunbounded
  exact no_unbounded_low_high_shell_prefix_of_reserve_closure
    G C S hnosurvivor hprefix_unbounded

/-- Shell-family closure for the geometry-only low-high energy budget. -/
structure LowHighEnergyBudgetShellReserveClosure
    (G : LowFrequencyLipschitzLedger) where
  shellLedger : ℕ → LowHighKinematicDichotomyLedger
  shellReceipt :
    ∀ j : ℕ, FixedTopologyLowHighEnergyBudgetReceipt (shellLedger j)
  reserveIndex : ℕ → ℕ
  shellReserveLink :
    ∀ j : ℕ,
      LowHighEnergyBudgetReserveLink
        (shellLedger j) (shellReceipt j) G (reserveIndex j)
  shellBudgetCost : ℕ → Real
  shell_budget_cost_eq_receipt_cost :
    ∀ j : ℕ,
      shellBudgetCost j =
        lowHighFlatTorusEnergyBudgetCost (shellReceipt j)
  shell_budget_cost_declared_before_payoff : Prop
  reserve_index_declared_before_payoff : Prop
  same_fixed_lp_bony_topology_all_shells : Prop
  fixed_shell_gap_all_shells : Prop
  finite_low_shell_core_paid : Prop
  no_posthoc_shell_selection : Prop
  cost_embeds_in_lipschitz_entry :
    ∀ j : ℕ, shellBudgetCost j ≤ G.lipschitzCost (reserveIndex j)
  prefix_cost_embeds_in_lipschitz_prefix :
    ∀ N : ℕ, nsPrefixSum shellBudgetCost N ≤ lipschitzPrefixCost G N

/-- The pointwise shell-budget embedding into the Lipschitz ledger is forced
by the per-shell reserve link plus the declared shell-budget cost identity. -/
theorem low_high_energy_budget_shell_budget_cost_eq_linked_lipschitz_entry
    (G : LowFrequencyLipschitzLedger)
    (S : LowHighEnergyBudgetShellReserveClosure G)
    (j : ℕ) :
    S.shellBudgetCost j = G.lipschitzCost (S.reserveIndex j) := by
  rw [S.shell_budget_cost_eq_receipt_cost j]
  exact (S.shellReserveLink j).cost_eq_lipschitz_entry.symm

/-- Inequality form of the linked shell-budget identity. -/
theorem low_high_energy_budget_shell_budget_cost_le_linked_lipschitz_entry
    (G : LowFrequencyLipschitzLedger)
    (S : LowHighEnergyBudgetShellReserveClosure G)
    (j : ℕ) :
    S.shellBudgetCost j ≤ G.lipschitzCost (S.reserveIndex j) :=
  le_of_eq
    (low_high_energy_budget_shell_budget_cost_eq_linked_lipschitz_entry
      G S j)

/-- Every declared geometry-only shell budget cost is nonnegative. -/
theorem low_high_energy_budget_shell_cost_nonnegative_of_reserve_closure
    (G : LowFrequencyLipschitzLedger)
    (S : LowHighEnergyBudgetShellReserveClosure G)
    (j : ℕ) :
    0 ≤ S.shellBudgetCost j := by
  rw [S.shell_budget_cost_eq_receipt_cost j]
  exact lowHighFlatTorusEnergyBudgetCost_nonnegative (S.shellReceipt j)

/-- The geometry-only shell-family closure exposes the underlying leakage
estimate before it is absorbed into the global Lipschitz reserve.

This is the local PDE-interface edge: the fixed LP/Bony energy-budget receipt
controls the shell leakage by the declared shell budget cost itself, so later
reserve-prefix arguments do not hide the low-high estimate inside a no-arbitrage
conclusion. -/
theorem low_high_energy_budget_shell_leakage_le_declared_cost
    (G : LowFrequencyLipschitzLedger)
    (S : LowHighEnergyBudgetShellReserveClosure G)
    (j : ℕ) :
    (S.shellLedger j).leakageGain ≤ S.shellBudgetCost j := by
  rw [S.shell_budget_cost_eq_receipt_cost j]
  exact fixed_topology_energy_budget_leakage_bound
    (S.shellLedger j) (S.shellReceipt j)

/-- The geometry-only shell-family closure prices every local low-high shell. -/
theorem low_high_energy_budget_shell_no_arbitrage_of_reserve_closure
    (G : LowFrequencyLipschitzLedger)
    (C : LowFrequencyLipschitzControlCertificate G)
    (S : LowHighEnergyBudgetShellReserveClosure G)
    (hnosurvivor : ∀ n : ℕ, FullLedgerNoSurvivor (G.block n))
    (j : ℕ) :
    InteractionNoArbitrage (S.shellLedger j).interaction :=
  low_high_no_arbitrage_of_energy_budget_reserve_link
    (S.shellLedger j) (S.shellReceipt j) G C (S.reserveIndex j)
    (S.shellReserveLink j) (hnosurvivor (S.reserveIndex j))

/-- The geometry-only shell-family closure rules out a same-shell reserve
shortfall without a deformation lift. -/
theorem no_low_high_energy_budget_shell_reserve_closure_with_shortfall_falsifier
    (G : LowFrequencyLipschitzLedger)
    (C : LowFrequencyLipschitzControlCertificate G)
    (S : LowHighEnergyBudgetShellReserveClosure G)
    (hnosurvivor : ∀ n : ℕ, FullLedgerNoSurvivor (G.block n))
    (j : ℕ)
    (F : LowHighEnergyBudgetReserveShortfallFalsifier (S.shellLedger j)) :
    False :=
  no_low_high_energy_budget_reserve_shortfall_of_link
    (S.shellLedger j) (S.shellReceipt j) G C (S.reserveIndex j)
    (S.shellReserveLink j) (hnosurvivor (S.reserveIndex j)) F

/-- Finite-prefix version of the geometry-only shell-family reserve closure. -/
theorem no_overbudget_low_high_energy_budget_shell_prefix_of_reserve_closure
    (G : LowFrequencyLipschitzLedger)
    (C : LowFrequencyLipschitzControlCertificate G)
    (S : LowHighEnergyBudgetShellReserveClosure G)
    (hnosurvivor : ∀ n : ℕ, FullLedgerNoSurvivor (G.block n))
    (N : ℕ)
    (hover : G.criticalBudget < nsPrefixSum S.shellBudgetCost N) :
    False := by
  have hlip_over : G.criticalBudget < lipschitzPrefixCost G N :=
    lt_of_lt_of_le hover (S.prefix_cost_embeds_in_lipschitz_prefix N)
  exact no_overbudget_lipschitz_prefix_under_no_survivor
    G C hnosurvivor N hlip_over

/-- Audited-certificate version of the geometry-only shell prefix overbudget
falsifier. -/
theorem no_overbudget_low_high_energy_budget_shell_prefix_of_audited_reserve_closure
    (G : LowFrequencyLipschitzLedger)
    (C : LowFrequencyLipschitzAuditedControlCertificate G)
    (S : LowHighEnergyBudgetShellReserveClosure G)
    (hnosurvivor : ∀ n : ℕ, FullLedgerNoSurvivor (G.block n))
    (N : ℕ)
    (hover : G.criticalBudget < nsPrefixSum S.shellBudgetCost N) :
    False := by
  have hlip_over : G.criticalBudget < lipschitzPrefixCost G N :=
    lt_of_lt_of_le hover (S.prefix_cost_embeds_in_lipschitz_prefix N)
  exact no_overbudget_lipschitz_prefix_under_audited_no_survivor
    G C hnosurvivor N hlip_over

/-- Finite-prefix falsifier for the geometry-only shell-family closure. -/
structure LowHighEnergyBudgetShellPrefixReserveFalsifier
    (G : LowFrequencyLipschitzLedger)
    (_S : LowHighEnergyBudgetShellReserveClosure G) where
  prefixLength : ℕ
  prefix_exceeds_declared_budget :
    G.criticalBudget < nsPrefixSum _S.shellBudgetCost prefixLength

/-- A geometry-only shell-family closure cannot coexist with its own finite
overbudget prefix falsifier. -/
theorem no_low_high_energy_budget_shell_reserve_closure_with_prefix_falsifier
    (G : LowFrequencyLipschitzLedger)
    (C : LowFrequencyLipschitzControlCertificate G)
    (S : LowHighEnergyBudgetShellReserveClosure G)
    (hnosurvivor : ∀ n : ℕ, FullLedgerNoSurvivor (G.block n))
    (F : LowHighEnergyBudgetShellPrefixReserveFalsifier G S) :
    False :=
  no_overbudget_low_high_energy_budget_shell_prefix_of_reserve_closure
    G C S hnosurvivor F.prefixLength F.prefix_exceeds_declared_budget

/-- Audited-certificate version of the finite-prefix shell reserve falsifier.
-/
theorem no_low_high_energy_budget_shell_reserve_closure_with_audited_prefix_falsifier
    (G : LowFrequencyLipschitzLedger)
    (C : LowFrequencyLipschitzAuditedControlCertificate G)
    (S : LowHighEnergyBudgetShellReserveClosure G)
    (hnosurvivor : ∀ n : ℕ, FullLedgerNoSurvivor (G.block n))
    (F : LowHighEnergyBudgetShellPrefixReserveFalsifier G S) :
    False :=
  no_overbudget_low_high_energy_budget_shell_prefix_of_audited_reserve_closure
    G C S hnosurvivor F.prefixLength F.prefix_exceeds_declared_budget

/-- Unbounded geometry-only low-high shell prefixes are impossible under the
fixed reserve closure and no-survivor pricing. -/
theorem no_unbounded_low_high_energy_budget_shell_prefix_of_reserve_closure
    (G : LowFrequencyLipschitzLedger)
    (C : LowFrequencyLipschitzControlCertificate G)
    (S : LowHighEnergyBudgetShellReserveClosure G)
    (hnosurvivor : ∀ n : ℕ, FullLedgerNoSurvivor (G.block n))
    (hunbounded :
      ∀ B : Real, ∃ N : ℕ, B < nsPrefixSum S.shellBudgetCost N) :
    False := by
  obtain ⟨N, hover⟩ := hunbounded G.criticalBudget
  exact no_overbudget_low_high_energy_budget_shell_prefix_of_reserve_closure
    G C S hnosurvivor N hover

/-- Audited-certificate version of the unbounded shell-prefix falsifier. -/
theorem no_unbounded_low_high_energy_budget_shell_prefix_of_audited_reserve_closure
    (G : LowFrequencyLipschitzLedger)
    (C : LowFrequencyLipschitzAuditedControlCertificate G)
    (S : LowHighEnergyBudgetShellReserveClosure G)
    (hnosurvivor : ∀ n : ℕ, FullLedgerNoSurvivor (G.block n))
    (hunbounded :
      ∀ B : Real, ∃ N : ℕ, B < nsPrefixSum S.shellBudgetCost N) :
    False := by
  obtain ⟨N, hover⟩ := hunbounded G.criticalBudget
  exact no_overbudget_low_high_energy_budget_shell_prefix_of_audited_reserve_closure
    G C S hnosurvivor N hover

/-- Pointwise-unbounded geometry-only shell costs force an overbudget prefix. -/
theorem no_pointwise_unbounded_low_high_energy_budget_shell_cost_of_reserve_closure
    (G : LowFrequencyLipschitzLedger)
    (C : LowFrequencyLipschitzControlCertificate G)
    (S : LowHighEnergyBudgetShellReserveClosure G)
    (hnosurvivor : ∀ n : ℕ, FullLedgerNoSurvivor (G.block n))
    (hunbounded :
      ∀ B : Real, ∃ j : ℕ, B < S.shellBudgetCost j) :
    False := by
  have hnonnegative :
      ∀ j : ℕ, 0 ≤ S.shellBudgetCost j :=
    low_high_energy_budget_shell_cost_nonnegative_of_reserve_closure G S
  have hprefix_unbounded :
      ∀ B : Real, ∃ N : ℕ, B < nsPrefixSum S.shellBudgetCost N :=
    ns_prefix_sum_unbounded_of_pointwise_unbounded_nonnegative
      S.shellBudgetCost hnonnegative hunbounded
  exact no_unbounded_low_high_energy_budget_shell_prefix_of_reserve_closure
    G C S hnosurvivor hprefix_unbounded

/-- Audited-certificate version of the pointwise-unbounded shell-cost
falsifier. -/
theorem no_pointwise_unbounded_low_high_energy_budget_shell_cost_of_audited_reserve_closure
    (G : LowFrequencyLipschitzLedger)
    (C : LowFrequencyLipschitzAuditedControlCertificate G)
    (S : LowHighEnergyBudgetShellReserveClosure G)
    (hnosurvivor : ∀ n : ℕ, FullLedgerNoSurvivor (G.block n))
    (hunbounded :
      ∀ B : Real, ∃ j : ℕ, B < S.shellBudgetCost j) :
    False := by
  have hnonnegative :
      ∀ j : ℕ, 0 ≤ S.shellBudgetCost j :=
    low_high_energy_budget_shell_cost_nonnegative_of_reserve_closure G S
  have hprefix_unbounded :
      ∀ B : Real, ∃ N : ℕ, B < nsPrefixSum S.shellBudgetCost N :=
    ns_prefix_sum_unbounded_of_pointwise_unbounded_nonnegative
      S.shellBudgetCost hnonnegative hunbounded
  exact no_unbounded_low_high_energy_budget_shell_prefix_of_audited_reserve_closure
    G C S hnosurvivor hprefix_unbounded

/-- Algebraic market-impact law for a low-high catalyst.

This is the analytic compression behind the smooth-shear audits.  If a
low-high operator with constant `operatorConstant` must match viscous loss
`ν * N^2`, then the required low Lipschitz strength is at least
`ν * N^2 / operatorConstant`.  When the declared reserve is the quadratic
low-H1/enstrophy cost `lowLipschitz^2 / 2`, the reserve pays an `N^4` lower
bound.

The theorem is only algebraic; the PDE work is proving the operator estimate
and embedding this reserve into the fixed LP/Bony profile topology. -/
structure LowHighMarketImpactScalingReceipt where
  viscosity : Real
  shellN : Real
  operatorConstant : Real
  lowLipschitzCost : Real
  lowH1ReserveCost : Real
  viscosity_nonnegative : 0 ≤ viscosity
  shellN_nonnegative : 0 ≤ shellN
  operator_constant_nonnegative : 0 ≤ operatorConstant
  low_lipschitz_nonnegative : 0 ≤ lowLipschitzCost
  low_h1_reserve_eq_quadratic :
    lowH1ReserveCost = lowLipschitzCost ^ 2 / 2
  rearming_requires_viscous_match :
    viscosity * shellN ^ 2 ≤ operatorConstant * lowLipschitzCost

/-- Market-impact lower bound in multiplication form.

This avoids division and is the form most convenient for later Lean adapters:
the low-H1 reserve must be large enough that
`ν^2 N^4 <= 2 C_lh^2 reserve`. -/
theorem low_high_market_impact_n4_lower_bound
    (R : LowHighMarketImpactScalingReceipt) :
    R.viscosity ^ 2 * R.shellN ^ 4 ≤
      2 * R.operatorConstant ^ 2 * R.lowH1ReserveCost := by
  have hleft_nonneg :
      0 ≤ R.viscosity * R.shellN ^ 2 := by
    exact mul_nonneg R.viscosity_nonnegative (sq_nonneg R.shellN)
  have hright_nonneg :
      0 ≤ R.operatorConstant * R.lowLipschitzCost := by
    exact mul_nonneg R.operator_constant_nonnegative
      R.low_lipschitz_nonnegative
  have hsquare_mul :
      (R.viscosity * R.shellN ^ 2) *
          (R.viscosity * R.shellN ^ 2) ≤
        (R.operatorConstant * R.lowLipschitzCost) *
          (R.operatorConstant * R.lowLipschitzCost) := by
    exact (mul_self_le_mul_self_iff hleft_nonneg hright_nonneg).mp
      R.rearming_requires_viscous_match
  rw [R.low_h1_reserve_eq_quadratic]
  nlinarith

/-- Bernstein-corrected market-impact receipt.

The sinusoidal shear witness gives an `N^4` reserve law because its low
Lipschitz norm is globally distributed.  A hostile smooth low-frequency field
can concentrate its Lipschitz norm up to the Bernstein factor of its low
bandwidth `K`.  This is the defensible continuum form:

* matching high-shell viscosity still requires
  `ν * N^2 <= C_lh * lowLipschitz`;
* fixed LP/Bony topology supplies the Bernstein-side lower-price statement
  `lowLipschitz^2 <= C_B^2 * K^3 * lowH1Reserve`.

Therefore any such catalyst pays at least an `N^4 / K^3` low-H1 reserve price.
Under a fixed low-high separation `K <= θ N`, this remains an unbounded
market-impact prefix obligation. -/
structure LowHighBernsteinMarketImpactReceipt where
  viscosity : Real
  shellN : Real
  operatorConstant : Real
  bernsteinConstant : Real
  lowBandwidth : Real
  lowLipschitzCost : Real
  lowH1ReserveCost : Real
  viscosity_nonnegative : 0 ≤ viscosity
  operator_constant_nonnegative : 0 ≤ operatorConstant
  low_bandwidth_nonnegative : 0 ≤ lowBandwidth
  low_lipschitz_nonnegative : 0 ≤ lowLipschitzCost
  low_h1_reserve_nonnegative : 0 ≤ lowH1ReserveCost
  rearming_requires_viscous_match :
    viscosity * shellN ^ 2 ≤ operatorConstant * lowLipschitzCost
  bernstein_lipschitz_price :
    lowLipschitzCost ^ 2 ≤
      bernsteinConstant ^ 2 * lowBandwidth ^ 3 * lowH1ReserveCost

/-- Bernstein-corrected low-high market-impact lower bound.

This is the safer global theorem surface than the pure `N^4` shear law:
`ν^2 N^4 <= C_lh^2 C_B^2 K^3 reserve`. -/
theorem low_high_bernstein_market_impact_lower_bound
    (R : LowHighBernsteinMarketImpactReceipt) :
    R.viscosity ^ 2 * R.shellN ^ 4 ≤
      R.operatorConstant ^ 2 * R.bernsteinConstant ^ 2 *
        R.lowBandwidth ^ 3 * R.lowH1ReserveCost := by
  have hleft_nonneg :
      0 ≤ R.viscosity * R.shellN ^ 2 := by
    exact mul_nonneg R.viscosity_nonnegative (sq_nonneg R.shellN)
  have hright_nonneg :
      0 ≤ R.operatorConstant * R.lowLipschitzCost := by
    exact mul_nonneg R.operator_constant_nonnegative
      R.low_lipschitz_nonnegative
  have hsquare_mul :
      (R.viscosity * R.shellN ^ 2) *
          (R.viscosity * R.shellN ^ 2) ≤
        (R.operatorConstant * R.lowLipschitzCost) *
          (R.operatorConstant * R.lowLipschitzCost) := by
    exact (mul_self_le_mul_self_iff hleft_nonneg hright_nonneg).mp
      R.rearming_requires_viscous_match
  nlinarith [R.bernstein_lipschitz_price]

/-- Low-high separated form of the Bernstein market-impact law.

If the low bandwidth obeys the fixed LP/Bony separation
`K <= theta * N`, the same receipt yields the explicit separated bound with
`theta^3 * N^3` in place of `K^3`.  This is the theorem surface for the
infinite-cascade prefix argument: the worst admissible low-high concentration
still leaves a price growing linearly in `N` when the constants are fixed. -/
theorem low_high_bernstein_market_impact_separated_bound
    (R : LowHighBernsteinMarketImpactReceipt)
    (theta : Real)
    (hband : R.lowBandwidth ≤ theta * R.shellN) :
    R.viscosity ^ 2 * R.shellN ^ 4 ≤
      R.operatorConstant ^ 2 * R.bernsteinConstant ^ 2 *
        (theta * R.shellN) ^ 3 * R.lowH1ReserveCost := by
  have hmain :
      R.viscosity ^ 2 * R.shellN ^ 4 ≤
        R.operatorConstant ^ 2 * R.bernsteinConstant ^ 2 *
          R.lowBandwidth ^ 3 * R.lowH1ReserveCost :=
    low_high_bernstein_market_impact_lower_bound R
  have hband3 :
      R.lowBandwidth ^ 3 ≤ (theta * R.shellN) ^ 3 := by
    exact pow_le_pow_left₀ R.low_bandwidth_nonnegative hband 3
  have hconstant_nonnegative :
      0 ≤ R.operatorConstant ^ 2 * R.bernsteinConstant ^ 2 :=
    mul_nonneg (sq_nonneg R.operatorConstant)
      (sq_nonneg R.bernsteinConstant)
  have hconstant_mul :
      R.operatorConstant ^ 2 * R.bernsteinConstant ^ 2 *
          R.lowBandwidth ^ 3 ≤
        R.operatorConstant ^ 2 * R.bernsteinConstant ^ 2 *
          (theta * R.shellN) ^ 3 :=
    mul_le_mul_of_nonneg_left hband3 hconstant_nonnegative
  have hmul :
      R.operatorConstant ^ 2 * R.bernsteinConstant ^ 2 *
          R.lowBandwidth ^ 3 * R.lowH1ReserveCost ≤
        R.operatorConstant ^ 2 * R.bernsteinConstant ^ 2 *
          (theta * R.shellN) ^ 3 * R.lowH1ReserveCost :=
    mul_le_mul_of_nonneg_right hconstant_mul R.low_h1_reserve_nonnegative
  exact hmain.trans hmul

/-- Setup-latency / execution-cost receipt for a shell-transfer catalyst.

This is the algebraic core of the dynamic latency framing.  A genuine
shell-transfer event must accumulate a fixed geometric alignment action before
payoff (`minAlignmentAction <= catalystRate * setupLatency`).  If the high
shell is to survive viscosity during that setup window
(`ν N^2 setupLatency <= survivalBudget`), the catalyst rate must grow like
`N^2`.  Charging the catalyst rate quadratically gives an `N^4` market-impact
lower bound.

The PDE theorem still has to prove the alignment-action lower bound from the
fixed LP/Bony geometry and embed the catalyst reserve in the Track B ledger.
This receipt prevents a proof from silently taking zero setup latency. -/
structure LowHighSetupLatencyExecutionReceipt where
  viscosity : Real
  shellN : Real
  minAlignmentAction : Real
  setupLatency : Real
  catalystRate : Real
  survivalBudget : Real
  catalystReserve : Real
  viscosity_nonnegative : 0 ≤ viscosity
  min_alignment_action_nonnegative : 0 ≤ minAlignmentAction
  setup_latency_nonnegative : 0 ≤ setupLatency
  catalyst_rate_nonnegative : 0 ≤ catalystRate
  survival_budget_nonnegative : 0 ≤ survivalBudget
  catalyst_reserve_eq_quadratic :
    catalystReserve = catalystRate ^ 2 / 2
  alignment_requires_setup_action :
    minAlignmentAction ≤ catalystRate * setupLatency
  high_shell_survival_budget :
    viscosity * shellN ^ 2 * setupLatency ≤ survivalBudget

/-- Survival plus nonzero alignment action forces a large catalyst rate.

Multiplication form: `ν * action * N^2 <= survivalBudget * catalystRate`.
This is the exact execution-cost analogue of "latency is not free." -/
theorem setup_latency_forces_catalyst_rate
    (R : LowHighSetupLatencyExecutionReceipt) :
    R.viscosity * R.minAlignmentAction * R.shellN ^ 2 ≤
      R.survivalBudget * R.catalystRate := by
  have hnuN_nonnegative : 0 ≤ R.viscosity * R.shellN ^ 2 :=
    mul_nonneg R.viscosity_nonnegative (sq_nonneg R.shellN)
  have halign_scaled :
      (R.viscosity * R.shellN ^ 2) * R.minAlignmentAction ≤
        (R.viscosity * R.shellN ^ 2) *
          (R.catalystRate * R.setupLatency) :=
    mul_le_mul_of_nonneg_left
      R.alignment_requires_setup_action
      hnuN_nonnegative
  have hsurvival_scaled :
      R.catalystRate *
          (R.viscosity * R.shellN ^ 2 * R.setupLatency) ≤
        R.catalystRate * R.survivalBudget :=
    mul_le_mul_of_nonneg_left
      R.high_shell_survival_budget
      R.catalyst_rate_nonnegative
  nlinarith

/-- Setup-latency market-impact lower bound.

If the shell survives while accumulating the required alignment action, the
quadratic catalyst reserve must pay
`ν^2 * action^2 * N^4 <= 2 * survivalBudget^2 * reserve`. -/
theorem setup_latency_market_impact_n4_lower_bound
    (R : LowHighSetupLatencyExecutionReceipt) :
    R.viscosity ^ 2 * R.minAlignmentAction ^ 2 * R.shellN ^ 4 ≤
      2 * R.survivalBudget ^ 2 * R.catalystReserve := by
  have hrate :
      R.viscosity * R.minAlignmentAction * R.shellN ^ 2 ≤
        R.survivalBudget * R.catalystRate :=
    setup_latency_forces_catalyst_rate R
  have hleft_nonnegative :
      0 ≤ R.viscosity * R.minAlignmentAction * R.shellN ^ 2 := by
    exact mul_nonneg
      (mul_nonneg R.viscosity_nonnegative
        R.min_alignment_action_nonnegative)
      (sq_nonneg R.shellN)
  have hright_nonnegative :
      0 ≤ R.survivalBudget * R.catalystRate :=
    mul_nonneg R.survival_budget_nonnegative
      R.catalyst_rate_nonnegative
  have hsquare :
      (R.viscosity * R.minAlignmentAction * R.shellN ^ 2) *
          (R.viscosity * R.minAlignmentAction * R.shellN ^ 2) ≤
        (R.survivalBudget * R.catalystRate) *
          (R.survivalBudget * R.catalystRate) := by
    exact (mul_self_le_mul_self_iff hleft_nonnegative hright_nonnegative).mp
      hrate
  rw [R.catalyst_reserve_eq_quadratic]
  nlinarith

/-- Control-Gramian phase-alignment receipt.

This is the integrated-control correction to the pointwise setup-rate receipt
above.  A finite-time controller can spread rate through the setup window; the
right lower bound is therefore `phaseGap^2 / setupLatency`, not merely a
pointwise rate squared.  If the controllability Gramian for the declared
low-high phase coordinate is at most `gramianConstant * setupLatency`, then
survival through the parabolic window forces the integrated control price

`ν * N^2 * phaseGap^2 <= C * survivalBudget * controlEnergy`.

For the Phase 5JO edge `phaseGap ~= 1/j`, this is the exact `N^2 / j^2`
catalyst-price lane exposed by the finite Fourier panel. -/
structure PhaseAlignmentControlGramianReceipt where
  viscosity : Real
  shellN : Real
  phaseGap : Real
  setupLatency : Real
  controlEnergy : Real
  survivalBudget : Real
  gramianConstant : Real
  controllabilityGramian : Real
  viscosity_nonnegative : 0 ≤ viscosity
  setup_latency_nonnegative : 0 ≤ setupLatency
  control_energy_nonnegative : 0 ≤ controlEnergy
  survival_budget_nonnegative : 0 ≤ survivalBudget
  gramian_constant_nonnegative : 0 ≤ gramianConstant
  controllability_gramian_nonnegative : 0 ≤ controllabilityGramian
  gramian_upper_bound :
    controllabilityGramian ≤ gramianConstant * setupLatency
  phase_requires_control_energy :
    phaseGap ^ 2 ≤ controllabilityGramian * controlEnergy
  high_shell_survival_budget :
    viscosity * shellN ^ 2 * setupLatency ≤ survivalBudget

/-- Integrated phase-alignment control price.

This is the control-theory version of the low-high execution-cost bridge.  It
does not prove the NSE phase coordinate has this Gramian; it states the exact
receipt a PDE proof must instantiate before using the latency analogy. -/
theorem phase_alignment_control_energy_lower_bound
    (R : PhaseAlignmentControlGramianReceipt) :
    R.viscosity * R.shellN ^ 2 * R.phaseGap ^ 2 ≤
      R.gramianConstant * R.survivalBudget * R.controlEnergy := by
  have hgram_control :
      R.controllabilityGramian * R.controlEnergy ≤
        (R.gramianConstant * R.setupLatency) * R.controlEnergy :=
    mul_le_mul_of_nonneg_right
      R.gramian_upper_bound
      R.control_energy_nonnegative
  have hphase_control :
      R.phaseGap ^ 2 ≤
        (R.gramianConstant * R.setupLatency) * R.controlEnergy :=
    R.phase_requires_control_energy.trans hgram_control
  have hnuN_nonnegative :
      0 ≤ R.viscosity * R.shellN ^ 2 :=
    mul_nonneg R.viscosity_nonnegative (sq_nonneg R.shellN)
  have hscaled :
      (R.viscosity * R.shellN ^ 2) * R.phaseGap ^ 2 ≤
        (R.viscosity * R.shellN ^ 2) *
          ((R.gramianConstant * R.setupLatency) * R.controlEnergy) :=
    mul_le_mul_of_nonneg_left hphase_control hnuN_nonnegative
  have hsurvival_scaled :
      (R.gramianConstant * R.controlEnergy) *
          (R.viscosity * R.shellN ^ 2 * R.setupLatency) ≤
        (R.gramianConstant * R.controlEnergy) * R.survivalBudget :=
    mul_le_mul_of_nonneg_left
      R.high_shell_survival_budget
      (mul_nonneg R.gramian_constant_nonnegative
        R.control_energy_nonnegative)
  nlinarith

/-- Sequence-level consequence of the integrated phase-alignment Gramian
receipt.

If the required viscous phase-alignment burden eventually exceeds every fixed
multiple of the available control-energy coefficient, then the control-energy
entries themselves are pointwise unbounded.  This is the control-energy
analogue of the pointwise phase-latency `|k_j|/j` lower-bound handoff. -/
theorem phase_alignment_control_energy_pointwise_unbounded_of_requirement
    (R : ℕ → PhaseAlignmentControlGramianReceipt)
    (hunbounded_requirement :
      ∀ B : Real, ∃ n : ℕ,
        (R n).gramianConstant * (R n).survivalBudget * B <
          (R n).viscosity * (R n).shellN ^ 2 * (R n).phaseGap ^ 2) :
    ∀ B : Real, ∃ n : ℕ, B < (R n).controlEnergy := by
  intro B
  obtain ⟨n, hn⟩ := hunbounded_requirement B
  refine ⟨n, ?_⟩
  by_contra hnot
  have hcontrol_le : (R n).controlEnergy ≤ B := le_of_not_gt hnot
  have hlower :
      (R n).viscosity * (R n).shellN ^ 2 * (R n).phaseGap ^ 2 ≤
        (R n).gramianConstant * (R n).survivalBudget *
          (R n).controlEnergy :=
    phase_alignment_control_energy_lower_bound (R n)
  have hcoef_nonnegative :
      0 ≤ (R n).gramianConstant * (R n).survivalBudget :=
    mul_nonneg (R n).gramian_constant_nonnegative
      (R n).survival_budget_nonnegative
  have hupper :
      (R n).gramianConstant * (R n).survivalBudget *
          (R n).controlEnergy ≤
        (R n).gramianConstant * (R n).survivalBudget * B :=
    mul_le_mul_of_nonneg_left hcontrol_le hcoef_nonnegative
  linarith

/-- Integrated phase-alignment control energy cannot escape the fixed
low-frequency Lipschitz reserve.

This is the sequence-level bridge from the control-theory Gramian receipt back
to the Track B no-survivor ledger: once each phase-alignment control-energy
entry is embedded in the declared Lipschitz cost, an unbounded integrated
phase-alignment requirement forces an overbudget finite prefix. -/
theorem no_phase_alignment_control_energy_escape_under_lipschitz_reserve
    (G : LowFrequencyLipschitzLedger)
    (C : LowFrequencyLipschitzControlCertificate G)
    (R : ℕ → PhaseAlignmentControlGramianReceipt)
    (hnosurvivor : ∀ n : ℕ, FullLedgerNoSurvivor (G.block n))
    (hcontrol_embeds_in_lipschitz_ledger :
      ∀ n : ℕ, (R n).controlEnergy ≤ G.lipschitzCost n)
    (hunbounded_requirement :
      ∀ B : Real, ∃ n : ℕ,
        (R n).gramianConstant * (R n).survivalBudget * B <
          (R n).viscosity * (R n).shellN ^ 2 * (R n).phaseGap ^ 2) :
    False := by
  have hcontrol_unbounded :
      ∀ B : Real, ∃ n : ℕ, B < (R n).controlEnergy :=
    phase_alignment_control_energy_pointwise_unbounded_of_requirement
      R hunbounded_requirement
  exact no_pointwise_unbounded_market_impact_under_no_survivor
    G C hnosurvivor
    (fun n => (R n).controlEnergy)
    (fun n => (R n).control_energy_nonnegative)
    hcontrol_embeds_in_lipschitz_ledger
    hcontrol_unbounded

/-- Audited-certificate version of the integrated phase-alignment escape
falsifier. -/
theorem no_phase_alignment_control_energy_escape_under_audited_lipschitz_reserve
    (G : LowFrequencyLipschitzLedger)
    (C : LowFrequencyLipschitzAuditedControlCertificate G)
    (R : ℕ → PhaseAlignmentControlGramianReceipt)
    (hnosurvivor : ∀ n : ℕ, FullLedgerNoSurvivor (G.block n))
    (hcontrol_embeds_in_lipschitz_ledger :
      ∀ n : ℕ, (R n).controlEnergy ≤ G.lipschitzCost n)
    (hunbounded_requirement :
      ∀ B : Real, ∃ n : ℕ,
        (R n).gramianConstant * (R n).survivalBudget * B <
          (R n).viscosity * (R n).shellN ^ 2 * (R n).phaseGap ^ 2) :
    False := by
  have hcontrol_unbounded :
      ∀ B : Real, ∃ n : ℕ, B < (R n).controlEnergy :=
    phase_alignment_control_energy_pointwise_unbounded_of_requirement
      R hunbounded_requirement
  exact no_pointwise_unbounded_market_impact_under_audited_no_survivor
    G C hnosurvivor
    (fun n => (R n).controlEnergy)
    (fun n => (R n).control_energy_nonnegative)
    hcontrol_embeds_in_lipschitz_ledger
    hcontrol_unbounded

/-- Prefix-level setup-latency market-impact closure.

This is the countable-cascade adapter for `LowHighSetupLatencyExecutionReceipt`.
The PDE estimate must instantiate `setupImpactCost` from the fixed LP/Bony
phase-alignment geometry.  Once those nonnegative setup costs embed into the
global low-frequency Lipschitz reserve ledger, unbounded setup costs cannot
coexist with no-survivor pricing and a finite critical budget. -/
structure LowHighSetupLatencyPrefixClosure
    (G : LowFrequencyLipschitzLedger) where
  setupImpactCost : ℕ → Real
  setup_impact_nonnegative :
    ∀ n : ℕ, 0 ≤ setupImpactCost n
  setup_impact_embeds_in_lipschitz_ledger :
    ∀ n : ℕ, setupImpactCost n ≤ G.lipschitzCost n
  fixed_lp_bony_phase_topology_declared_before_payoff : Prop
  phase_angle_comparable_to_gain_declared_before_payoff : Prop
  parabolic_window_survival_price_declared_before_payoff : Prop

/-- A fixed setup-latency prefix closure rules out any unbounded setup impact
prefix under the same no-survivor Lipschitz-reserve assumptions. -/
theorem no_unbounded_setup_latency_market_impact_under_no_survivor
    (G : LowFrequencyLipschitzLedger)
    (C : LowFrequencyLipschitzControlCertificate G)
    (S : LowHighSetupLatencyPrefixClosure G)
    (hnosurvivor : ∀ n : ℕ, FullLedgerNoSurvivor (G.block n))
    (hunbounded :
      ∀ B : Real, ∃ n : ℕ, B < S.setupImpactCost n) :
    False :=
  no_pointwise_unbounded_market_impact_under_no_survivor
    G C hnosurvivor S.setupImpactCost
    S.setup_impact_nonnegative
    S.setup_impact_embeds_in_lipschitz_ledger
    hunbounded

/-- Concrete Fourier latency symbol receipt.

For the low-high Fourier block `p = k + q`,
`P_p((a_q · ∇)b_k)`, the deterministic panel observed the sharp scaling
`requiredLowLipschitz ≳ |k| / j` for a phase angle comparable to `1/j` on the
parabolic window `|k|^-2`.  This structure records the proof-facing algebraic
interface: if the PDE supplies a lower bound by `a * shellOverIndex`, then the
existing Lipschitz-reserve closure forbids such a path whenever
`shellOverIndex` is unbounded. -/
structure ConcreteFourierLatencySymbolReceipt
    (G : LowFrequencyLipschitzLedger) where
  shellOverIndex : ℕ → Real
  requiredLowLipschitz : ℕ → Real
  symbolConstant : Real
  symbol_constant_positive : 0 < symbolConstant
  required_lipschitz_nonnegative :
    ∀ n : ℕ, 0 ≤ requiredLowLipschitz n
  fixed_modes_topology_and_leray_outputs_declared : Prop
  low_high_leray_symbol_bound_declared : Prop
  phase_angle_comparable_to_gain_declared : Prop
  required_lipschitz_lower_bound :
    ∀ n : ℕ,
      symbolConstant * shellOverIndex n ≤ requiredLowLipschitz n
  required_lipschitz_embeds_in_lipschitz_ledger :
    ∀ n : ℕ, requiredLowLipschitz n ≤ G.lipschitzCost n

/-- The concrete Fourier latency symbol law closes under the existing
Lipschitz reserve if `|k_j|/j` is unbounded.

This is the formal version of the Phase 5JO read: bounded low-Lipschitz
capacity cannot deliver `theta_j ≃ 1/j` on dyadic high shells; allowing
`L_j ≃ |k_j|/j` must be charged in the same Lipschitz/all-output ledger. -/
theorem no_unbounded_concrete_fourier_latency_symbol_under_no_survivor
    (G : LowFrequencyLipschitzLedger)
    (C : LowFrequencyLipschitzControlCertificate G)
    (S : ConcreteFourierLatencySymbolReceipt G)
    (hnosurvivor : ∀ n : ℕ, FullLedgerNoSurvivor (G.block n))
    (hshell_over_index_unbounded :
      ∀ B : Real, ∃ n : ℕ, B < S.shellOverIndex n) :
    False := by
  have hrequired_unbounded :
      ∀ B : Real, ∃ n : ℕ, B < S.requiredLowLipschitz n :=
    pointwise_unbounded_of_positive_linear_lower_bound
      S.symbolConstant
      S.shellOverIndex
      S.requiredLowLipschitz
      S.symbol_constant_positive
      S.required_lipschitz_lower_bound
      hshell_over_index_unbounded
  exact no_pointwise_unbounded_market_impact_under_no_survivor
    G C hnosurvivor S.requiredLowLipschitz
    S.required_lipschitz_nonnegative
    S.required_lipschitz_embeds_in_lipschitz_ledger
    hrequired_unbounded

/-- Audited-certificate version of the concrete Fourier latency symbol
falsifier. -/
theorem no_unbounded_concrete_fourier_latency_symbol_under_audited_no_survivor
    (G : LowFrequencyLipschitzLedger)
    (C : LowFrequencyLipschitzAuditedControlCertificate G)
    (S : ConcreteFourierLatencySymbolReceipt G)
    (hnosurvivor : ∀ n : ℕ, FullLedgerNoSurvivor (G.block n))
    (hshell_over_index_unbounded :
      ∀ B : Real, ∃ n : ℕ, B < S.shellOverIndex n) :
    False :=
  no_linear_shell_market_impact_under_audited_no_survivor
    G C hnosurvivor
    S.shellOverIndex
    S.requiredLowLipschitz
    S.symbolConstant
    S.symbol_constant_positive
    S.required_lipschitz_nonnegative
    S.required_lipschitz_lower_bound
    S.required_lipschitz_embeds_in_lipschitz_ledger
    hshell_over_index_unbounded

/-- The parabolic phase-latency control receipt forces pointwise-unbounded
macroscopic control whenever the required shell schedule outgrows every fixed
budget.

This converts the finite-shell `Omega(|k_j|/j)` obstruction into the exact
pointwise-unbounded shape consumed by the low-frequency Lipschitz reserve
bridge. -/
theorem phase_latency_control_budget_pointwise_unbounded_of_requirement
    (R : PhaseLatencyControlGramianReceipt)
    (hunbounded_requirement :
      ∀ B : Real, ∃ j : ℕ,
        (B * R.gramianConstant) * R.harmonicIndex j <
          R.angleConstant * R.kNorm j) :
    ∀ B : Real, ∃ j : ℕ, B < R.controlBudget j := by
  intro B
  by_contra hno
  push Not at hno
  exact
    no_uniform_control_budget_for_unbounded_phase_latency_schedule
      R hno hunbounded_requirement

/-- Phase-latency control budget embedded in the fixed Lipschitz reserve cannot
be unbounded under no-survivor pricing.

This is the load-bearing handoff from the control-Gramian analogy back into the
existing Track B continuation bridge.  It still requires the PDE proof to
identify `controlBudget` with a declared low-frequency Lipschitz/BKM reserve
entry before payoff scoring. -/
theorem no_phase_latency_control_gramian_escape_under_lipschitz_reserve
    (G : LowFrequencyLipschitzLedger)
    (C : LowFrequencyLipschitzControlCertificate G)
    (R : PhaseLatencyControlGramianReceipt)
    (hnosurvivor : ∀ n : ℕ, FullLedgerNoSurvivor (G.block n))
    (hcontrol_embeds_in_lipschitz_ledger :
      ∀ n : ℕ, R.controlBudget n ≤ G.lipschitzCost n)
    (hunbounded_requirement :
      ∀ B : Real, ∃ j : ℕ,
        (B * R.gramianConstant) * R.harmonicIndex j <
          R.angleConstant * R.kNorm j) :
    False := by
  have hcontrol_unbounded :
      ∀ B : Real, ∃ n : ℕ, B < R.controlBudget n :=
    phase_latency_control_budget_pointwise_unbounded_of_requirement
      R hunbounded_requirement
  exact no_pointwise_unbounded_market_impact_under_no_survivor
    G C hnosurvivor R.controlBudget
    R.budget_nonnegative
    hcontrol_embeds_in_lipschitz_ledger
    hcontrol_unbounded

/-- Audited-certificate version of the phase-latency control-Gramian escape
falsifier. -/
theorem no_phase_latency_control_gramian_escape_under_audited_lipschitz_reserve
    (G : LowFrequencyLipschitzLedger)
    (C : LowFrequencyLipschitzAuditedControlCertificate G)
    (R : PhaseLatencyControlGramianReceipt)
    (hnosurvivor : ∀ n : ℕ, FullLedgerNoSurvivor (G.block n))
    (hcontrol_embeds_in_lipschitz_ledger :
      ∀ n : ℕ, R.controlBudget n ≤ G.lipschitzCost n)
    (hunbounded_requirement :
      ∀ B : Real, ∃ j : ℕ,
        (B * R.gramianConstant) * R.harmonicIndex j <
          R.angleConstant * R.kNorm j) :
    False := by
  have hcontrol_unbounded :
      ∀ B : Real, ∃ n : ℕ, B < R.controlBudget n :=
    phase_latency_control_budget_pointwise_unbounded_of_requirement
      R hunbounded_requirement
  exact no_pointwise_unbounded_market_impact_under_audited_no_survivor
    G C hnosurvivor R.controlBudget
    R.budget_nonnegative
    hcontrol_embeds_in_lipschitz_ledger
    hcontrol_unbounded

/-- Time-integrated Duhamel/Bernstein low-high receipt.

This is the correction to the pointwise market-impact proof.  A high-shell
branch is not charged by a pointwise low-Lipschitz spike alone; the Duhamel
kernel allows time concentration.  The Cauchy-Schwarz/Bernstein estimate has
the abstract form

`requiredGain^2 <= (C_B^2 * K^3 / (2 * dampingRate)) * timeIntegratedReserve`.

Thus the actual integrated reserve lower bound is proportional to
`dampingRate / K^3`, not the pointwise `N^4 / K^3` cost.  This is the precise
place where the low-high branch must pay a resupply/memory theorem rather than
only a pointwise Bernstein estimate. -/
structure LowHighDuhamelBernsteinReceipt where
  requiredGain : Real
  dampingRate : Real
  bernsteinConstant : Real
  lowBandwidth : Real
  timeIntegratedReserve : Real
  damping_rate_positive : 0 < dampingRate
  low_bandwidth_nonnegative : 0 ≤ lowBandwidth
  time_integrated_reserve_nonnegative : 0 ≤ timeIntegratedReserve
  duhamel_bernstein_cauchy_bound :
    requiredGain ^ 2 ≤
      (bernsteinConstant ^ 2 * lowBandwidth ^ 3 /
          (2 * dampingRate)) * timeIntegratedReserve

/-- Duhamel/Bernstein integrated reserve lower bound.

Multiplication form: `2 λ requiredGain^2 <= C_B^2 K^3 reserveIntegral`. -/
theorem low_high_duhamel_bernstein_integrated_reserve_bound
    (R : LowHighDuhamelBernsteinReceipt) :
    2 * R.dampingRate * R.requiredGain ^ 2 ≤
      R.bernsteinConstant ^ 2 * R.lowBandwidth ^ 3 *
        R.timeIntegratedReserve := by
  have hpos : 0 < 2 * R.dampingRate := by
    nlinarith [R.damping_rate_positive]
  have hmul :=
    mul_le_mul_of_nonneg_left
      R.duhamel_bernstein_cauchy_bound
      (le_of_lt hpos)
  have hcancel :
      (2 * R.dampingRate) *
          ((R.bernsteinConstant ^ 2 * R.lowBandwidth ^ 3 /
              (2 * R.dampingRate)) * R.timeIntegratedReserve) =
        R.bernsteinConstant ^ 2 * R.lowBandwidth ^ 3 *
          R.timeIntegratedReserve := by
    have hdamp : R.dampingRate ≠ 0 := ne_of_gt R.damping_rate_positive
    field_simp [ne_of_gt hpos, hdamp]
  nlinarith

/-- Viscous-shell specialization guard for the Duhamel/Bernstein receipt.

The Duhamel receipt itself only names an abstract damping rate and low
bandwidth.  To use it as the flat-torus/NS viscous shell clock, a PDE
instantiation must additionally identify that damping rate with
`nu * shellN^2` and fix the low-high separation `K <= theta * shellN`.  This
adapter makes those source identifications load-bearing without pretending to
prove them. -/
structure LowHighDuhamelViscousShellGuard
    (R : LowHighDuhamelBernsteinReceipt) where
  viscosity : Real
  shellN : Real
  theta : Real
  damping_rate_eq_viscous_shell :
    R.dampingRate = viscosity * shellN ^ 2
  low_bandwidth_le_theta_shell :
    R.lowBandwidth ≤ theta * shellN

/-- Duhamel/Bernstein reserve bound after the PDE has identified the abstract
damping rate with the viscous shell rate and fixed the low-high bandwidth
separation.

This is the proof-facing form of the `nu -- shell` graph edge: it is valid
only through the explicit guard above, not as an unconditional relation between
viscosity and shell index. -/
theorem low_high_duhamel_bernstein_viscous_shell_bound
    (R : LowHighDuhamelBernsteinReceipt)
    (G : LowHighDuhamelViscousShellGuard R) :
    2 * G.viscosity * G.shellN ^ 2 * R.requiredGain ^ 2 ≤
      R.bernsteinConstant ^ 2 * (G.theta * G.shellN) ^ 3 *
        R.timeIntegratedReserve := by
  have hmain :
      2 * R.dampingRate * R.requiredGain ^ 2 ≤
        R.bernsteinConstant ^ 2 * R.lowBandwidth ^ 3 *
          R.timeIntegratedReserve :=
    low_high_duhamel_bernstein_integrated_reserve_bound R
  have hband3 :
      R.lowBandwidth ^ 3 ≤ (G.theta * G.shellN) ^ 3 := by
    exact pow_le_pow_left₀
      R.low_bandwidth_nonnegative
      G.low_bandwidth_le_theta_shell
      3
  have hconstant_nonnegative :
      0 ≤ R.bernsteinConstant ^ 2 :=
    sq_nonneg R.bernsteinConstant
  have hband_scaled :
      R.bernsteinConstant ^ 2 * R.lowBandwidth ^ 3 ≤
        R.bernsteinConstant ^ 2 * (G.theta * G.shellN) ^ 3 :=
    mul_le_mul_of_nonneg_left hband3 hconstant_nonnegative
  have hreserve_scaled :
      R.bernsteinConstant ^ 2 * R.lowBandwidth ^ 3 *
          R.timeIntegratedReserve ≤
        R.bernsteinConstant ^ 2 * (G.theta * G.shellN) ^ 3 *
          R.timeIntegratedReserve :=
    mul_le_mul_of_nonneg_right
      hband_scaled
      R.time_integrated_reserve_nonnegative
  have hcombined :
      2 * R.dampingRate * R.requiredGain ^ 2 ≤
        R.bernsteinConstant ^ 2 * (G.theta * G.shellN) ^ 3 *
          R.timeIntegratedReserve :=
    hmain.trans hreserve_scaled
  simpa [G.damping_rate_eq_viscous_shell, mul_assoc, mul_left_comm,
    mul_comm] using hcombined

/-- Exponent ledger for the Duhamel/Bernstein low-high edge.

If `K = N^alpha` and the independently declared required gain scales like
`N^beta`, the integrated reserve lower-bound exponent is
`2 + 2 beta - 3 alpha`.  This object keeps the dynamic exponent burden
separate from the pointwise market-impact receipt. -/
structure LowHighDuhamelExponentReceipt where
  alpha : Real
  beta : Real
  reserveExponent : Real
  exponent_eq : reserveExponent = 2 + 2 * beta - 3 * alpha

/-- Nonnegative reserve exponent threshold.

On dyadic shells, nonnegative exponent is the algebraic condition that prevents
the Duhamel/Bernstein edge receipt from becoming a summable tail. -/
theorem low_high_duhamel_reserve_exponent_nonnegative_of_gain_threshold
    (R : LowHighDuhamelExponentReceipt)
    (hbeta : (3 * R.alpha - 2) / 2 ≤ R.beta) :
    0 ≤ R.reserveExponent := by
  rw [R.exponent_eq]
  nlinarith

/-- Edge form `alpha = 1`: the missing dynamic price is exactly a half-power
gain/return-time/resupply factor. -/
theorem low_high_edge_duhamel_reserve_exponent_nonnegative_of_sqrt_gain
    (R : LowHighDuhamelExponentReceipt)
    (hedge : R.alpha = 1)
    (hbeta : (1 / 2 : Real) ≤ R.beta) :
    0 ≤ R.reserveExponent := by
  apply low_high_duhamel_reserve_exponent_nonnegative_of_gain_threshold R
  rw [hedge]
  norm_num
  exact hbeta

/-- Unit-gain edge events expose the summable-tail risk: the formal exponent is
`-1`, so this branch needs an additional recurrence price before it can close
an infinite cascade. -/
theorem low_high_edge_unit_gain_duhamel_reserve_exponent_eq_neg_one
    (R : LowHighDuhamelExponentReceipt)
    (hedge : R.alpha = 1)
    (hunit : R.beta = 0) :
    R.reserveExponent = -1 := by
  rw [R.exponent_eq, hedge, hunit]
  norm_num

/-- Recurrence-price exponent layered on top of the Duhamel/Bernstein edge
receipt.

For unit-gain LP-edge events the base exponent is `-1`; therefore any closure
that does not raise `beta` to `1/2` must provide an independent price exponent
of at least `1` from return time, resupply, profile prepositioning, or dynamic
admissibility. -/
structure LowHighDuhamelRecurrencePriceReceipt where
  base : LowHighDuhamelExponentReceipt
  recurrencePriceExponent : Real
  totalReserveExponent : Real
  total_exponent_eq :
    totalReserveExponent =
      base.reserveExponent + recurrencePriceExponent

/-- Unit-gain edge closure through an independent recurrence price.

This is the exact algebraic target left by the Duhamel correction: once the
base edge tail is `N^-1`, an additional `N^1` price makes the dyadic reserve
exponent nonnegative again. -/
theorem low_high_edge_unit_gain_total_exponent_nonnegative_of_recurrence_price
    (R : LowHighDuhamelRecurrencePriceReceipt)
    (hedge : R.base.alpha = 1)
    (hunit : R.base.beta = 0)
    (hrec : 1 ≤ R.recurrencePriceExponent) :
    0 ≤ R.totalReserveExponent := by
  have hbase :
      R.base.reserveExponent = -1 :=
    low_high_edge_unit_gain_duhamel_reserve_exponent_eq_neg_one
      R.base hedge hunit
  rw [R.total_exponent_eq, hbase]
  linarith

/-- Strict recurrence-price version needed for arbitrary fractional divergent
edge-gain schedules.

Nonnegative exponent is enough to block unit dyadic jumps, but Phase 5HN/5HO
show that a flat exponent does not control every divergent fractional gain
schedule.  The recurrence/admissibility theorem needed for the global bridge
must raise the raw `-1` LP-edge exponent to a strictly positive exponent. -/
theorem low_high_edge_unit_gain_total_exponent_positive_of_strict_recurrence_price
    (R : LowHighDuhamelRecurrencePriceReceipt)
    (hedge : R.base.alpha = 1)
    (hunit : R.base.beta = 0)
    (hrec : 1 < R.recurrencePriceExponent) :
    0 < R.totalReserveExponent := by
  have hbase :
      R.base.reserveExponent = -1 :=
    low_high_edge_unit_gain_duhamel_reserve_exponent_eq_neg_one
      R.base hedge hunit
  rw [R.total_exponent_eq, hbase]
  linarith

/-- Conversely, any positive total exponent on the raw unit LP-edge route pays
more than one full dyadic power of independent recurrence price. -/
theorem recurrence_price_gt_one_of_low_high_edge_unit_gain_total_positive
    (R : LowHighDuhamelRecurrencePriceReceipt)
    (hedge : R.base.alpha = 1)
    (hunit : R.base.beta = 0)
    (hpos : 0 < R.totalReserveExponent) :
    1 < R.recurrencePriceExponent := by
  have hbase :
      R.base.reserveExponent = -1 :=
    low_high_edge_unit_gain_duhamel_reserve_exponent_eq_neg_one
      R.base hedge hunit
  rw [R.total_exponent_eq, hbase] at hpos
  linarith

/-- Sobolev-order translation of the low-high edge price.

At the LP edge, the Duhamel/Bernstein price supplied by an `H^s` low-frequency
reserve has exponent `p = 2s - 3`.  This records Phase 5HP in the proof spine:
energy/H1 gives `p = -1`, the critical `H^(3/2)` line gives only `p = 0`,
and arbitrary fractional edge-gain schedules need `p > 0`. -/
structure LowHighSobolevEdgePriceReceipt where
  sobolevOrder : Real
  edgePriceExponent : Real
  exponent_eq : edgePriceExponent = 2 * sobolevOrder - 3

/-- A Sobolev reserve strictly above the `3/2` line supplies positive edge
sequence price. -/
theorem edge_price_positive_of_sobolev_supercritical
    (R : LowHighSobolevEdgePriceReceipt)
    (h : (3 : Real) / 2 < R.sobolevOrder) :
    0 < R.edgePriceExponent := by
  rw [R.exponent_eq]
  nlinarith

/-- If the Sobolev reserve is at or below `3/2`, this route cannot supply a
positive edge price exponent. -/
theorem edge_price_nonpositive_of_sobolev_not_supercritical
    (R : LowHighSobolevEdgePriceReceipt)
    (h : R.sobolevOrder ≤ (3 : Real) / 2) :
    R.edgePriceExponent ≤ 0 := by
  rw [R.exponent_eq]
  nlinarith

/-- Positive edge price through the Sobolev route is exactly a supercritical
Sobolev-order claim.  This prevents laundering the missing recurrence price
into endpoint `H^(3/2)` language. -/
theorem sobolev_supercritical_of_positive_edge_price
    (R : LowHighSobolevEdgePriceReceipt)
    (h : 0 < R.edgePriceExponent) :
    (3 : Real) / 2 < R.sobolevOrder := by
  rw [R.exponent_eq] at h
  nlinarith

/-- A reusable closure object for the low-high branch at the Lipschitz-reserve
layer.  This is a stronger target than a local finite packet no-go: every
declared low-high interaction must provide an unpaid LP/Bony estimate, link it
to the global Lipschitz reserve ledger, and use a no-survivor block to pay that
entry. -/
structure LowHighLipschitzReserveBranchCertificate where
  Class : LPInteractionLedger → Prop
  globalLedger : LowFrequencyLipschitzLedger
  globalCertificate :
    LowFrequencyLipschitzControlCertificate globalLedger
  low_high_bridge :
    ∀ T : LPInteractionLedger,
      Class T →
        ∃ (L : LowHighKinematicDichotomyLedger)
          (R : LowHighLPBonyUnpaidEstimateReceipt L)
          (n : ℕ),
          ∃ _link : LowHighLipschitzReserveLink L R globalLedger n,
            L.interaction = T ∧
              FullLedgerNoSurvivor (globalLedger.block n)

/-- A branch certificate prices every low-high member in the declared class. -/
theorem low_high_class_no_arbitrage_of_lipschitz_reserve_branch
    (P : LowHighLipschitzReserveBranchCertificate)
    (T : LPInteractionLedger)
    (hT : P.Class T) :
    InteractionNoArbitrage T := by
  obtain ⟨L, R, n, hlink, hLT, hnosurvivor⟩ := P.low_high_bridge T hT
  rw [← hLT]
  exact low_high_no_arbitrage_of_lipschitz_reserve_link
    L R P.globalLedger P.globalCertificate n hlink hnosurvivor

/-- Operator-norm reality check plus a global reserve link prices the low-high
interaction.

This is the proof-facing version of the low-high PDE estimate.  The analytic
work is isolated in `LowHighBonyOperatorEstimateRealityCheck`; after that,
the existing global Lipschitz reserve ledger pays the interaction. -/
theorem low_high_no_arbitrage_of_operator_reality_check_reserve_link
    (L : LowHighKinematicDichotomyLedger)
    (R : LowHighBonyOperatorEstimateRealityCheck L)
    (G : LowFrequencyLipschitzLedger)
    (C : LowFrequencyLipschitzControlCertificate G)
    (n : ℕ)
    (link :
      LowHighLipschitzReserveLink L
        (unpaid_lp_bony_receipt_of_operator_reality_check L R) G n)
    (hnosurvivor : FullLedgerNoSurvivor (G.block n)) :
    InteractionNoArbitrage L.interaction :=
  low_high_no_arbitrage_of_lipschitz_reserve_link
    L
    (unpaid_lp_bony_receipt_of_operator_reality_check L R)
    G C n link hnosurvivor

/-- Operator-norm reality check, global reserve link, and no-survivor pricing
cannot coexist with a same-ledger low-high reserve shortfall. -/
theorem no_low_high_operator_reality_check_with_bilinear_falsifier
    (L : LowHighKinematicDichotomyLedger)
    (R : LowHighBonyOperatorEstimateRealityCheck L)
    (G : LowFrequencyLipschitzLedger)
    (C : LowFrequencyLipschitzControlCertificate G)
    (n : ℕ)
    (link :
      LowHighLipschitzReserveLink L
        (unpaid_lp_bony_receipt_of_operator_reality_check L R) G n)
    (hnosurvivor : FullLedgerNoSurvivor (G.block n))
    (F : LowHighBilinearChargeFalsifier L) :
    False :=
  no_low_high_lipschitz_reserve_link_with_bilinear_falsifier
    L
    (unpaid_lp_bony_receipt_of_operator_reality_check L R)
    G C n link hnosurvivor F

/-- Fixed-topology local operator receipt plus a global reserve link prices the
low-high interaction.

This is the narrow theorem surface now exposed to ZTARE: it may work on the
fixed LP/Bony topology receipt without touching the broader Track B theorem. -/
theorem low_high_no_arbitrage_of_fixed_topology_operator_receipt
    (L : LowHighKinematicDichotomyLedger)
    (R : FixedTopologyLowHighOperatorReceipt L)
    (G : LowFrequencyLipschitzLedger)
    (C : LowFrequencyLipschitzControlCertificate G)
    (n : ℕ)
    (link :
      LowHighLipschitzReserveLink L
        (unpaid_lp_bony_receipt_of_operator_reality_check L
          (operator_reality_check_of_fixed_topology_receipt L R)) G n)
    (hnosurvivor : FullLedgerNoSurvivor (G.block n)) :
    InteractionNoArbitrage L.interaction :=
  low_high_no_arbitrage_of_operator_reality_check_reserve_link
    L (operator_reality_check_of_fixed_topology_receipt L R)
    G C n link hnosurvivor

/-- Explicit-commutator version of the fixed-topology low-high no-arbitrage
handoff.

The result is algebraically the same as
`low_high_no_arbitrage_of_fixed_topology_operator_receipt`; the additional
value is proof hygiene.  A future PDE proof can no longer satisfy the surface
by silently treating the projected `H1` transport as exactly skew. -/
theorem low_high_no_arbitrage_of_fixed_topology_commutator_receipt
    (L : LowHighKinematicDichotomyLedger)
    (R : FixedTopologyLowHighOperatorReceiptWithCommutator L)
    (G : LowFrequencyLipschitzLedger)
    (C : LowFrequencyLipschitzControlCertificate G)
    (n : ℕ)
    (link :
      LowHighLipschitzReserveLink L
        (unpaid_lp_bony_receipt_of_operator_reality_check L
          (operator_reality_check_of_fixed_topology_receipt L R.base)) G n)
    (hnosurvivor : FullLedgerNoSurvivor (G.block n)) :
    InteractionNoArbitrage L.interaction :=
  low_high_no_arbitrage_of_fixed_topology_operator_receipt
    L R.base G C n link hnosurvivor

/-- The fixed-topology local receipt, if linked to a priced global reserve
entry, cannot coexist with a same-ledger low-high shortfall falsifier. -/
theorem no_low_high_fixed_topology_operator_receipt_with_bilinear_falsifier
    (L : LowHighKinematicDichotomyLedger)
    (R : FixedTopologyLowHighOperatorReceipt L)
    (G : LowFrequencyLipschitzLedger)
    (C : LowFrequencyLipschitzControlCertificate G)
    (n : ℕ)
    (link :
      LowHighLipschitzReserveLink L
        (unpaid_lp_bony_receipt_of_operator_reality_check L
          (operator_reality_check_of_fixed_topology_receipt L R)) G n)
    (hnosurvivor : FullLedgerNoSurvivor (G.block n))
    (F : LowHighBilinearChargeFalsifier L) :
    False :=
  no_low_high_operator_reality_check_with_bilinear_falsifier
    L (operator_reality_check_of_fixed_topology_receipt L R)
    G C n link hnosurvivor F

/-- Full fixed-topology receipt, including the finite low-shell core, prices the
low-high interaction once the high-shell receipt is linked to a priced global
reserve entry. -/
theorem low_high_no_arbitrage_of_full_fixed_topology_operator_receipt
    (L : LowHighKinematicDichotomyLedger)
    (R : FullFixedTopologyLowHighOperatorReceipt L)
    (G : LowFrequencyLipschitzLedger)
    (C : LowFrequencyLipschitzControlCertificate G)
    (n : ℕ)
    (link :
      LowHighLipschitzReserveLink L
        (unpaid_lp_bony_receipt_of_operator_reality_check L
          (operator_reality_check_of_fixed_topology_receipt L
            R.highShellReceipt)) G n)
    (hnosurvivor : FullLedgerNoSurvivor (G.block n)) :
    InteractionNoArbitrage L.interaction :=
  low_high_no_arbitrage_of_fixed_topology_operator_receipt
    L R.highShellReceipt G C n link hnosurvivor

/-- Full fixed-topology receipt, including the finite low-shell core, cannot
coexist with a same-ledger low-high reserve shortfall once its high-shell
receipt is linked to a priced global reserve entry. -/
theorem no_low_high_full_fixed_topology_operator_receipt_with_bilinear_falsifier
    (L : LowHighKinematicDichotomyLedger)
    (R : FullFixedTopologyLowHighOperatorReceipt L)
    (G : LowFrequencyLipschitzLedger)
    (C : LowFrequencyLipschitzControlCertificate G)
    (n : ℕ)
    (link :
      LowHighLipschitzReserveLink L
        (unpaid_lp_bony_receipt_of_operator_reality_check L
          (operator_reality_check_of_fixed_topology_receipt L
            R.highShellReceipt)) G n)
    (hnosurvivor : FullLedgerNoSurvivor (G.block n))
    (F : LowHighBilinearChargeFalsifier L) :
    False :=
  no_low_high_fixed_topology_operator_receipt_with_bilinear_falsifier
    L R.highShellReceipt G C n link hnosurvivor F

/-- Hostile smooth-shear lesson: a low-high interaction can defeat a naive
local self-tax reserve if the low catalyst has zero local self-tax but realizes
positive leakage/payoff.

This is not a counterexample to the global Lipschitz-reserve adapter above.
It is the reason that adapter is necessary: the reserve must charge the
low-frequency Lipschitz cost itself, not only the low mode's local
self-advection. -/
structure LowHighNaiveReserveDecoupler where
  interaction : LPInteractionLedger
  leakageGain : Real
  localSelfTaxReserve : Real
  is_low_high : interaction.interactionClass = LPParaproductClass.lowHigh
  leakage_realized_as_payoff : leakageGain ≤ interaction.payoff
  price_eq_local_self_tax_reserve :
    interaction.price = localSelfTaxReserve
  zero_local_self_tax_reserve : localSelfTaxReserve = 0
  positive_leakage : 0 < leakageGain

/-- A naive reserve that only charges local self-tax cannot price a genuine
low-high decoupler. -/
theorem not_no_arbitrage_of_naive_reserve_decoupler
    (D : LowHighNaiveReserveDecoupler) :
    ¬ InteractionNoArbitrage D.interaction := by
  intro h
  unfold InteractionNoArbitrage at h
  have hpaypos : 0 < D.interaction.payoff :=
    lt_of_lt_of_le D.positive_leakage D.leakage_realized_as_payoff
  have hprice0 : D.interaction.price = 0 := by
    rw [D.price_eq_local_self_tax_reserve, D.zero_local_self_tax_reserve]
  rw [hprice0] at h
  linarith

/-- Routing certificate for the shear-catalyst branch after the decoupler audit.

The audit shows local H1/Lipschitz leakage can be positive while local
self-advection tax is zero.  A proof must therefore route such a catalyst in
one of two ways:

* `energy_skew_nonrearming`: the interaction has no positive survival payoff in
  the declared Track B observable, so it is harmless for the no-arbitrage
  ledger even though it may create transient gradient growth;
* `reserve_link`: the exact H1/Lipschitz cost is embedded into the global
  low-frequency Lipschitz reserve ledger and priced there.

This prevents the false proof target "local shear growth cannot exist." -/
inductive LowHighShearCatalystRoute
    (L : LowHighKinematicDichotomyLedger)
    (R : LowHighLPBonyUnpaidEstimateReceipt L)
    (G : LowFrequencyLipschitzLedger)
    (C : LowFrequencyLipschitzControlCertificate G)
    (n : ℕ) : Prop where
  | energySkewNonrearming :
      L.interaction.payoff ≤ L.interaction.price →
        LowHighShearCatalystRoute L R G C n
  | reservePriced :
      LowHighLipschitzReserveLink L R G n →
        FullLedgerNoSurvivor (G.block n) →
          LowHighShearCatalystRoute L R G C n

/-- The shear-catalyst branch is priced if either the declared survival payoff
is already non-positive/energy-skew, or the exact Lipschitz cost is routed into
the global reserve ledger. -/
theorem low_high_no_arbitrage_of_shear_catalyst_routing
    (L : LowHighKinematicDichotomyLedger)
    (R : LowHighLPBonyUnpaidEstimateReceipt L)
    (G : LowFrequencyLipschitzLedger)
    (C : LowFrequencyLipschitzControlCertificate G)
    (n : ℕ)
    (S : LowHighShearCatalystRoute L R G C n) :
    InteractionNoArbitrage L.interaction := by
  cases S with
  | energySkewNonrearming h =>
      exact h
  | reservePriced link hnosurvivor =>
      exact low_high_no_arbitrage_of_lipschitz_reserve_link
        L R G C n link hnosurvivor

/-- If a smooth shear catalyst has positive survival payoff while the local
self-tax price is zero, then the "energy-skew/non-rearming" route is not
available.  Any valid shear-catalyst route must expose a reserve link and a
no-survivor price for that reserve entry.

This is the formal read of the Phase 5GT audit: transport-only low advection is
`L2`-skew, but the full low-high linearized shear can rearm `L2/H1`, so the
branch cannot be closed by calling the shear harmless unless the declared
survival observable itself has no positive payoff. -/
theorem shear_rearming_route_forces_reserve_priced
    (L : LowHighKinematicDichotomyLedger)
    (R : LowHighLPBonyUnpaidEstimateReceipt L)
    (G : LowFrequencyLipschitzLedger)
    (C : LowFrequencyLipschitzControlCertificate G)
    (n : ℕ)
    (S : LowHighShearCatalystRoute L R G C n)
    (hpositive_payoff : 0 < L.interaction.payoff)
    (hlocal_price_zero : L.interaction.price = 0) :
    ∃ _ : LowHighLipschitzReserveLink L R G n,
      FullLedgerNoSurvivor (G.block n) := by
  cases S with
  | energySkewNonrearming hskew =>
      rw [hlocal_price_zero] at hskew
      linarith
  | reservePriced link hnosurvivor =>
      exact ⟨link, hnosurvivor⟩

/-- Algebraic market-impact receipt for a low-high shear catalyst.

If the measured linearized shear growth `growthConstant * (amp * kLow)` beats
the viscous shell rate `nu * shell^2`, then the low-mode energy
`lowEnergy = amp^2 / 2` must pay the cross-multiplied price below.

This is the formal core of the Phase 5GU scaling audit: the catalyst exists,
but rearming arbitrarily high shells requires a diverging low-frequency energy
budget unless the "low" frequency grows with the target shell. -/
theorem shear_market_impact_energy_cross_bound
    {amp kLow shell nu growthConstant lowEnergy : Real}
    (henergy : 2 * lowEnergy = amp ^ 2)
    (hbeat :
      nu * shell ^ 2 ≤ growthConstant * (amp * kLow))
    (hvisc_nonnegative : 0 ≤ nu * shell ^ 2)
    (hgrowth_nonnegative :
      0 ≤ growthConstant * (amp * kLow)) :
    (nu * shell ^ 2) ^ 2 ≤
      2 * (growthConstant ^ 2 * kLow ^ 2) * lowEnergy := by
  let a := nu * shell ^ 2
  let b := growthConstant * (amp * kLow)
  have hdiff : 0 ≤ b - a := by
    exact sub_nonneg.mpr hbeat
  have hsum : 0 ≤ b + a := by
    exact add_nonneg hgrowth_nonnegative hvisc_nonnegative
  have hprod : 0 ≤ (b - a) * (b + a) :=
    mul_nonneg hdiff hsum
  have hsq : a ^ 2 ≤ b ^ 2 := by
    nlinarith
  dsimp [a, b] at hsq
  have hgrowth_sq :
      (growthConstant * (amp * kLow)) ^ 2 =
        2 * (growthConstant ^ 2 * kLow ^ 2) * lowEnergy := by
    calc
      (growthConstant * (amp * kLow)) ^ 2 =
          (growthConstant ^ 2 * kLow ^ 2) * amp ^ 2 := by
        ring
      _ = (growthConstant ^ 2 * kLow ^ 2) * (2 * lowEnergy) := by
        rw [← henergy]
      _ = 2 * (growthConstant ^ 2 * kLow ^ 2) * lowEnergy := by
        ring
  rw [hgrowth_sq] at hsq
  exact hsq

/-- Contrapositive market-impact cutoff.

Given a finite low-frequency energy budget, a shear catalyst cannot beat
viscosity at shell `shell` once the market-impact lower bound exceeds that
budget.  This is the algebraic "infinity is not free" version of the low-high
shear audit. -/
theorem no_shear_break_even_above_energy_budget
    {amp kLow shell nu growthConstant lowEnergy budget : Real}
    (henergy : 2 * lowEnergy = amp ^ 2)
    (hbudget : lowEnergy ≤ budget)
    (hvisc_nonnegative : 0 ≤ nu * shell ^ 2)
    (hgrowth_nonnegative :
      0 ≤ growthConstant * (amp * kLow))
    (hcutoff :
      2 * (growthConstant ^ 2 * kLow ^ 2) * budget <
        (nu * shell ^ 2) ^ 2) :
    ¬ nu * shell ^ 2 ≤ growthConstant * (amp * kLow) := by
  intro hbeat
  have hcross :
      (nu * shell ^ 2) ^ 2 ≤
        2 * (growthConstant ^ 2 * kLow ^ 2) * lowEnergy :=
    shear_market_impact_energy_cross_bound
      henergy hbeat hvisc_nonnegative hgrowth_nonnegative
  have hcoef : 0 ≤ 2 * (growthConstant ^ 2 * kLow ^ 2) := by
    nlinarith [sq_nonneg growthConstant, sq_nonneg kLow]
  have hbudget' :
      2 * (growthConstant ^ 2 * kLow ^ 2) * lowEnergy ≤
        2 * (growthConstant ^ 2 * kLow ^ 2) * budget :=
    mul_le_mul_of_nonneg_left hbudget hcoef
  exact not_lt_of_ge (hcross.trans hbudget') hcutoff

/-- Remaining PDE obligation for the low-high branch after the reserve adapter.

The finite searches support this shape locally, but the unpaid mathematical
work is the fixed-topology theorem that constructs this branch certificate for
actual Navier-Stokes LP/Bony low-high blocks. -/
structure LowHighLipschitzReservePDEObligation where
  fixed_lp_bony_topology : Prop
  unpaid_lp_bony_estimate_for_low_high_blocks : Prop
  one_shell_energy_form_not_raw_operator_norm : Prop
  transport_stretch_separation_budget_declared : Prop
  leakage_positive_part_or_abs_pairing_declared : Prop
  lipschitz_cost_embeds_in_global_reserve_ledger : Prop
  no_survivor_prices_each_lipschitz_entry : Prop
  reserve_identity_fixed_before_payoff : Prop
  does_not_use_paid_deformation_lift_as_local_estimate : Prop
  smooth_limit_preserves_cost_and_reserve : Prop
  no_posthoc_shell_or_observable_choice : Prop

/-- Satisfaction predicate for the low-high Lipschitz reserve PDE obligation.

This is the continuum low-high analogue of the event-recurrence obligation
satisfaction predicate.  The record names the topology and reserve duties; this
predicate makes all of them load-bearing before a global bridge may use the
shell-family reserve closure. -/
def LowHighLipschitzReservePDEObligationSatisfied
    (O : LowHighLipschitzReservePDEObligation) : Prop :=
  O.fixed_lp_bony_topology ∧
    O.unpaid_lp_bony_estimate_for_low_high_blocks ∧
      O.one_shell_energy_form_not_raw_operator_norm ∧
        O.transport_stretch_separation_budget_declared ∧
          O.leakage_positive_part_or_abs_pairing_declared ∧
            O.lipschitz_cost_embeds_in_global_reserve_ledger ∧
              O.no_survivor_prices_each_lipschitz_entry ∧
                O.reserve_identity_fixed_before_payoff ∧
                  O.does_not_use_paid_deformation_lift_as_local_estimate ∧
                    O.smooth_limit_preserves_cost_and_reserve ∧
                      O.no_posthoc_shell_or_observable_choice

/-- Pre-no-survivor portion of the low-high Lipschitz reserve PDE obligation.

These are exactly the duties that a concrete shell-reserve closure can pay
without first importing `FullLedgerNoSurvivor` for the target Lipschitz ledger.
The no-survivor-priced leakage/no-arbitrage fields remain outside this
predicate, so source-first bridges can audit which part of the low-high PDE
work has actually been paid before the endpoint consequence is available. -/
def LowHighLipschitzReservePDEPreNoSurvivorSatisfied
    (O : LowHighLipschitzReservePDEObligation) : Prop :=
  O.fixed_lp_bony_topology ∧
    O.unpaid_lp_bony_estimate_for_low_high_blocks ∧
      O.one_shell_energy_form_not_raw_operator_norm ∧
        O.transport_stretch_separation_budget_declared ∧
          O.lipschitz_cost_embeds_in_global_reserve_ledger ∧
            O.reserve_identity_fixed_before_payoff ∧
              O.does_not_use_paid_deformation_lift_as_local_estimate ∧
                O.smooth_limit_preserves_cost_and_reserve ∧
                  O.no_posthoc_shell_or_observable_choice

/-- Semantic handoff from a concrete energy-budget shell closure to the
abstract low-high PDE checklist.

The fields are deliberately directional: the shell closure supplies the fixed
LP/Bony topology, energy-budget receipts, same-ledger reserve links, and
no-posthoc shell discipline; the handoff explains how those concrete facts pay
the named PDE-obligation fields.  This avoids treating the PDE satisfaction
receipt as a detachable black box next to the shell-reserve closure. -/
structure LowHighEnergyBudgetShellReservePDEHandoff
    (O : LowHighLipschitzReservePDEObligation)
    (G : LowFrequencyLipschitzLedger)
    (S : LowHighEnergyBudgetShellReserveClosure G) where
  same_fixed_shell_topology_paid :
    S.same_fixed_lp_bony_topology_all_shells
  fixed_shell_gap_paid :
    S.fixed_shell_gap_all_shells
  finite_low_shell_core_paid :
    S.finite_low_shell_core_paid
  fixed_lp_bony_topology_of_same_fixed_shell_topology :
    S.same_fixed_lp_bony_topology_all_shells →
      O.fixed_lp_bony_topology
  unpaid_lp_bony_estimate_of_shell_receipts :
    (∀ j : ℕ, (S.shellLedger j).leakageGain ≤ S.shellBudgetCost j) →
      O.unpaid_lp_bony_estimate_for_low_high_blocks
  one_shell_energy_form_of_energy_budget_receipts :
    S.fixed_shell_gap_all_shells →
      S.finite_low_shell_core_paid →
        (∀ j : ℕ, 0 ≤ S.shellBudgetCost j) →
          O.one_shell_energy_form_not_raw_operator_norm
  transport_stretch_separation_budget_declared :
    O.transport_stretch_separation_budget_declared
  leakage_pairing_of_shell_no_arbitrage :
    (∀ j : ℕ, InteractionNoArbitrage (S.shellLedger j).interaction) →
      O.leakage_positive_part_or_abs_pairing_declared
  lipschitz_cost_embeds_of_shell_closure :
    (∀ j : ℕ, S.shellBudgetCost j ≤ G.lipschitzCost (S.reserveIndex j)) →
      O.lipschitz_cost_embeds_in_global_reserve_ledger
  no_survivor_prices_each_lipschitz_entry_of_generated_blocks :
    (∀ n : ℕ, FullLedgerNoSurvivor (G.block n)) →
      O.no_survivor_prices_each_lipschitz_entry
  reserve_identity_of_shell_links :
    (∀ j : ℕ,
      LowHighEnergyBudgetReserveLink
        (S.shellLedger j) (S.shellReceipt j) G (S.reserveIndex j)) →
        O.reserve_identity_fixed_before_payoff
  no_deformation_lift_of_energy_budget_receipts :
    (∀ j : ℕ, FixedTopologyLowHighEnergyBudgetReceipt (S.shellLedger j)) →
      O.does_not_use_paid_deformation_lift_as_local_estimate
  smooth_limit_preserves_cost_and_reserve :
    O.smooth_limit_preserves_cost_and_reserve
  no_posthoc_shell_selection_paid :
    S.no_posthoc_shell_selection
  no_posthoc_shell_choice_of_closure :
    S.no_posthoc_shell_selection →
      O.no_posthoc_shell_or_observable_choice

/-- Named ways the semantic handoff from generated shell-reserve closure to the
abstract low-high PDE checklist can lack its paid source data.

This is a provenance guard for the handoff object itself.  It does not add a
new PDE assumption; it exposes the fields already carried by
`LowHighEnergyBudgetShellReservePDEHandoff` as falsifier branches for final
bridge audits. -/
inductive LowHighEnergyBudgetShellReservePDEHandoffFalsifier
    {O : LowHighLipschitzReservePDEObligation}
    {G : LowFrequencyLipschitzLedger}
    {S : LowHighEnergyBudgetShellReserveClosure G}
    (H : LowHighEnergyBudgetShellReservePDEHandoff O G S) : Type where
  | sameFixedShellTopologyUnpaid :
      ¬ S.same_fixed_lp_bony_topology_all_shells →
        LowHighEnergyBudgetShellReservePDEHandoffFalsifier H
  | fixedShellGapUnpaid :
      ¬ S.fixed_shell_gap_all_shells →
        LowHighEnergyBudgetShellReservePDEHandoffFalsifier H
  | finiteLowShellCoreUnpaid :
      ¬ S.finite_low_shell_core_paid →
        LowHighEnergyBudgetShellReservePDEHandoffFalsifier H
  | transportStretchBudgetUndeclared :
      ¬ O.transport_stretch_separation_budget_declared →
        LowHighEnergyBudgetShellReservePDEHandoffFalsifier H
  | smoothLimitCostReserveUnpaid :
      ¬ O.smooth_limit_preserves_cost_and_reserve →
        LowHighEnergyBudgetShellReservePDEHandoffFalsifier H
  | posthocShellSelectionUnpaid :
      ¬ S.no_posthoc_shell_selection →
        LowHighEnergyBudgetShellReservePDEHandoffFalsifier H

/-- A concrete low-high energy-budget PDE handoff excludes missing-source
provenance falsifiers for the fields it already carries. -/
theorem no_low_high_energy_budget_shell_reserve_pde_handoff_falsifier
    {O : LowHighLipschitzReservePDEObligation}
    {G : LowFrequencyLipschitzLedger}
    {S : LowHighEnergyBudgetShellReserveClosure G}
    (H : LowHighEnergyBudgetShellReservePDEHandoff O G S)
    (F : LowHighEnergyBudgetShellReservePDEHandoffFalsifier H) :
    False := by
  cases F with
  | sameFixedShellTopologyUnpaid h =>
      exact h H.same_fixed_shell_topology_paid
  | fixedShellGapUnpaid h =>
      exact h H.fixed_shell_gap_paid
  | finiteLowShellCoreUnpaid h =>
      exact h H.finite_low_shell_core_paid
  | transportStretchBudgetUndeclared h =>
      exact h H.transport_stretch_separation_budget_declared
  | smoothLimitCostReserveUnpaid h =>
      exact h H.smooth_limit_preserves_cost_and_reserve
  | posthocShellSelectionUnpaid h =>
      exact h H.no_posthoc_shell_selection_paid

/-- A concrete energy-budget shell closure pays the pre-no-survivor portion of
the abstract low-high PDE checklist.

This theorem is intentionally weaker than
`low_high_lipschitz_reserve_pde_obligation_satisfied_of_energy_budget_shell_closure`:
it does not consume `FullLedgerNoSurvivor`, and therefore does not claim the
no-survivor-priced leakage/no-arbitrage fields. -/
theorem low_high_lipschitz_reserve_pde_pre_no_survivor_satisfied_of_energy_budget_shell_closure
    (O : LowHighLipschitzReservePDEObligation)
    (G : LowFrequencyLipschitzLedger)
    (S : LowHighEnergyBudgetShellReserveClosure G)
    (H : LowHighEnergyBudgetShellReservePDEHandoff O G S) :
    LowHighLipschitzReservePDEPreNoSurvivorSatisfied O := by
  exact
    ⟨H.fixed_lp_bony_topology_of_same_fixed_shell_topology
        H.same_fixed_shell_topology_paid,
      H.unpaid_lp_bony_estimate_of_shell_receipts
        (low_high_energy_budget_shell_leakage_le_declared_cost G S),
      H.one_shell_energy_form_of_energy_budget_receipts
        H.fixed_shell_gap_paid
        H.finite_low_shell_core_paid
        (low_high_energy_budget_shell_cost_nonnegative_of_reserve_closure G S),
      H.transport_stretch_separation_budget_declared,
      H.lipschitz_cost_embeds_of_shell_closure
        (low_high_energy_budget_shell_budget_cost_le_linked_lipschitz_entry
          G S),
      H.reserve_identity_of_shell_links S.shellReserveLink,
      H.no_deformation_lift_of_energy_budget_receipts S.shellReceipt,
      H.smooth_limit_preserves_cost_and_reserve,
      H.no_posthoc_shell_choice_of_closure
        H.no_posthoc_shell_selection_paid⟩

/-- A concrete energy-budget shell closure pays the abstract low-high PDE
checklist once the closure is tied to the same generated Lipschitz ledger and
the generated blocks are known no-survivor.

This theorem is intentionally general-purpose: it does not mention GP216 or
any final bridge receipt. -/
theorem low_high_lipschitz_reserve_pde_obligation_satisfied_of_energy_budget_shell_closure
    (O : LowHighLipschitzReservePDEObligation)
    (G : LowFrequencyLipschitzLedger)
    (C : LowFrequencyLipschitzControlCertificate G)
    (S : LowHighEnergyBudgetShellReserveClosure G)
    (hnosurvivor : ∀ n : ℕ, FullLedgerNoSurvivor (G.block n))
    (H : LowHighEnergyBudgetShellReservePDEHandoff O G S) :
    LowHighLipschitzReservePDEObligationSatisfied O := by
  exact
    ⟨H.fixed_lp_bony_topology_of_same_fixed_shell_topology
        H.same_fixed_shell_topology_paid,
      H.unpaid_lp_bony_estimate_of_shell_receipts
        (low_high_energy_budget_shell_leakage_le_declared_cost G S),
      H.one_shell_energy_form_of_energy_budget_receipts
        H.fixed_shell_gap_paid
        H.finite_low_shell_core_paid
        (low_high_energy_budget_shell_cost_nonnegative_of_reserve_closure G S),
      H.transport_stretch_separation_budget_declared,
      H.leakage_pairing_of_shell_no_arbitrage
        (low_high_energy_budget_shell_no_arbitrage_of_reserve_closure
          G C S hnosurvivor),
      H.lipschitz_cost_embeds_of_shell_closure
        (low_high_energy_budget_shell_budget_cost_le_linked_lipschitz_entry
          G S),
      H.no_survivor_prices_each_lipschitz_entry_of_generated_blocks
        hnosurvivor,
      H.reserve_identity_of_shell_links S.shellReserveLink,
      H.no_deformation_lift_of_energy_budget_receipts S.shellReceipt,
      H.smooth_limit_preserves_cost_and_reserve,
      H.no_posthoc_shell_choice_of_closure
        H.no_posthoc_shell_selection_paid⟩

/-- Audited-certificate form of the low-high Lipschitz reserve PDE discharge.

This is the preferred endpoint-facing route: the proof still uses the same
energy-budget shell closure, but the control certificate is projected from a
declared continuation source rather than supplied as a detachable legacy
interface. -/
theorem low_high_lipschitz_reserve_pde_obligation_satisfied_of_audited_energy_budget_shell_closure
    (O : LowHighLipschitzReservePDEObligation)
    (G : LowFrequencyLipschitzLedger)
    (C : LowFrequencyLipschitzAuditedControlCertificate G)
    (S : LowHighEnergyBudgetShellReserveClosure G)
    (hnosurvivor : ∀ n : ℕ, FullLedgerNoSurvivor (G.block n))
    (H : LowHighEnergyBudgetShellReservePDEHandoff O G S) :
    LowHighLipschitzReservePDEObligationSatisfied O :=
  low_high_lipschitz_reserve_pde_obligation_satisfied_of_energy_budget_shell_closure
    O G C.toControlCertificate S hnosurvivor H

/-- The shell-reserve PDE handoff directly pays the smooth-limit duty.

This is a projection helper only: it keeps downstream bridge code from
destructuring the full PDE-satisfaction tuple when it only needs the named
smooth-limit source. -/
theorem smooth_limit_preserves_cost_and_reserve_of_energy_budget_shell_pde_handoff
    {O : LowHighLipschitzReservePDEObligation}
    {G : LowFrequencyLipschitzLedger}
    {S : LowHighEnergyBudgetShellReserveClosure G}
    (H : LowHighEnergyBudgetShellReservePDEHandoff O G S) :
    O.smooth_limit_preserves_cost_and_reserve :=
  H.smooth_limit_preserves_cost_and_reserve

/-- Named ways the low-high Lipschitz reserve PDE obligation can fail.

This keeps the final GP216 bridge from treating a black-box
`¬ LowHighLipschitzReservePDEObligationSatisfied` as an opaque rejection:
each branch corresponds to one analytic duty in the obligation record. -/
inductive LowHighLipschitzReservePDEObligationFalsifier
    (O : LowHighLipschitzReservePDEObligation) : Type where
  | topologyNotFixed :
      ¬ O.fixed_lp_bony_topology →
        LowHighLipschitzReservePDEObligationFalsifier O
  | lpBonyEstimateMissing :
      ¬ O.unpaid_lp_bony_estimate_for_low_high_blocks →
        LowHighLipschitzReservePDEObligationFalsifier O
  | rawOperatorNormUsed :
      ¬ O.one_shell_energy_form_not_raw_operator_norm →
        LowHighLipschitzReservePDEObligationFalsifier O
  | stretchBudgetUndeclared :
      ¬ O.transport_stretch_separation_budget_declared →
        LowHighLipschitzReservePDEObligationFalsifier O
  | leakagePairingUndeclared :
      ¬ O.leakage_positive_part_or_abs_pairing_declared →
        LowHighLipschitzReservePDEObligationFalsifier O
  | lipschitzCostNotEmbedded :
      ¬ O.lipschitz_cost_embeds_in_global_reserve_ledger →
        LowHighLipschitzReservePDEObligationFalsifier O
  | noSurvivorMissesEntry :
      ¬ O.no_survivor_prices_each_lipschitz_entry →
        LowHighLipschitzReservePDEObligationFalsifier O
  | reserveIdentityPosthoc :
      ¬ O.reserve_identity_fixed_before_payoff →
        LowHighLipschitzReservePDEObligationFalsifier O
  | deformationLiftUsedAsLocalEstimate :
      ¬ O.does_not_use_paid_deformation_lift_as_local_estimate →
        LowHighLipschitzReservePDEObligationFalsifier O
  | smoothLimitNotPreserved :
      ¬ O.smooth_limit_preserves_cost_and_reserve →
        LowHighLipschitzReservePDEObligationFalsifier O
  | posthocShellOrObservableChoice :
      ¬ O.no_posthoc_shell_or_observable_choice →
        LowHighLipschitzReservePDEObligationFalsifier O

/-- A satisfied low-high reserve PDE obligation excludes each named failure
branch. -/
theorem no_low_high_lipschitz_reserve_pde_obligation_falsifier
    (O : LowHighLipschitzReservePDEObligation)
    (hO : LowHighLipschitzReservePDEObligationSatisfied O)
    (F : LowHighLipschitzReservePDEObligationFalsifier O) :
    False := by
  rcases hO with
    ⟨htopology, hlp, henergy, hstretch, hpairing, hembed,
      hentry, hreserve, hdeformation, hlimit, hposthoc⟩
  cases F with
  | topologyNotFixed h => exact h htopology
  | lpBonyEstimateMissing h => exact h hlp
  | rawOperatorNormUsed h => exact h henergy
  | stretchBudgetUndeclared h => exact h hstretch
  | leakagePairingUndeclared h => exact h hpairing
  | lipschitzCostNotEmbedded h => exact h hembed
  | noSurvivorMissesEntry h => exact h hentry
  | reserveIdentityPosthoc h => exact h hreserve
  | deformationLiftUsedAsLocalEstimate h => exact h hdeformation
  | smoothLimitNotPreserved h => exact h hlimit
  | posthocShellOrObservableChoice h => exact h hposthoc

end ZtareProofs.NS
