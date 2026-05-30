import Mathlib.Tactic
import ZtareProofs.ns_gp216_limit_lsc_obligation
import ZtareProofs.ns_matrix_block_sos_bossfight

/-!
# Galerkin PSD action source for continuum LP lower semicontinuity

This file isolates the fixed-action version of the finite PSD route.  A finite
PSD audit becomes useful for the continuum LP/profile limit only after it is
promoted to one fixed Galerkin action family: fixed topology, fixed operators,
fixed coordinates, and an explicit action identity at every prefix.  The
liminf lower bound and prefix-price domination still remain analytic source
obligations.
-/

namespace ZtareProofs.NS

noncomputable section

universe u

/-- A fixed Galerkin PSD action family for one continuum LP prefix stream.

The dimensions may vary with the prefix index, but the topology, coordinates,
operators, and action identity must be fixed before payoff scoring.  This is a
source object: it records the data needed to build a kinematic-action LSC
source, while leaving the actual liminf and price-domination estimates explicit
for the PDE proof. -/
structure GalerkinPSDActionFamily
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ) where
  dimension : ℕ → ℕ
  operator : ∀ N : ℕ, FinitePSDOperator (dimension N)
  coordinates : ∀ N : ℕ, Fin (dimension N) → ℝ
  action : ℕ → ℝ
  fixed_galerkin_topology : Prop
  fixed_galerkin_topology_paid :
    fixed_galerkin_topology
  operators_declared_before_payoff : Prop
  operators_declared_before_payoff_paid :
    operators_declared_before_payoff
  coordinates_declared_before_payoff : Prop
  coordinates_declared_before_payoff_paid :
    coordinates_declared_before_payoff
  action_declared_before_payoff : Prop
  action_declared_before_payoff_paid :
    action_declared_before_payoff
  no_posthoc_operator_or_coordinate_substitution : Prop
  no_posthoc_operator_or_coordinate_substitution_paid :
    no_posthoc_operator_or_coordinate_substitution
  exact_action_identity :
    ∀ N : ℕ,
      action N =
        finiteOperatorQuadratic
          (operator N).carrier
          (coordinates N)

/-- Every prefix action in a fixed Galerkin PSD action family is nonnegative. -/
theorem galerkin_psd_action_nonnegative
    {τ : ContinuumLPProfileTopology.{u}}
    {S : ContinuumLPPrefixPriceStream τ}
    (G : GalerkinPSDActionFamily S)
    (N : ℕ) :
    0 ≤ G.action N := by
  rw [G.exact_action_identity N]
  exact (G.operator N).quadratic_nonnegative (G.coordinates N)

/-- Hostile falsifier surface for a claimed fixed Galerkin PSD action family. -/
inductive GalerkinPSDActionFamilyFalsifier
    {τ : ContinuumLPProfileTopology.{u}}
    {S : ContinuumLPPrefixPriceStream τ}
    (G : GalerkinPSDActionFamily S) : Prop where
  | topology_not_fixed :
      ¬ G.fixed_galerkin_topology →
        GalerkinPSDActionFamilyFalsifier G
  | operators_posthoc :
      ¬ G.operators_declared_before_payoff →
        GalerkinPSDActionFamilyFalsifier G
  | coordinates_posthoc :
      ¬ G.coordinates_declared_before_payoff →
        GalerkinPSDActionFamilyFalsifier G
  | action_posthoc :
      ¬ G.action_declared_before_payoff →
        GalerkinPSDActionFamilyFalsifier G
  | operator_or_coordinate_substituted :
      ¬ G.no_posthoc_operator_or_coordinate_substitution →
        GalerkinPSDActionFamilyFalsifier G
  | action_identity_break
      (N : ℕ) :
      G.action N ≠
          finiteOperatorQuadratic
            (G.operator N).carrier
            (G.coordinates N) →
        GalerkinPSDActionFamilyFalsifier G

/-- A paid fixed Galerkin PSD action family excludes its guard failures. -/
theorem no_galerkin_psd_action_family_falsifier
    {τ : ContinuumLPProfileTopology.{u}}
    {S : ContinuumLPPrefixPriceStream τ}
    (G : GalerkinPSDActionFamily S)
    (F : GalerkinPSDActionFamilyFalsifier G) :
    False := by
  cases F with
  | topology_not_fixed hbad =>
      exact hbad G.fixed_galerkin_topology_paid
  | operators_posthoc hbad =>
      exact hbad G.operators_declared_before_payoff_paid
  | coordinates_posthoc hbad =>
      exact hbad G.coordinates_declared_before_payoff_paid
  | action_posthoc hbad =>
      exact hbad G.action_declared_before_payoff_paid
  | operator_or_coordinate_substituted hbad =>
      exact hbad G.no_posthoc_operator_or_coordinate_substitution_paid
  | action_identity_break N hbad =>
      exact hbad (G.exact_action_identity N)

/-- Scale-covariant low-high quotient kernel source.

This is a narrow source object for the finite low-high PSD pattern surfaced by
the Phase 5FA/5FB audits.  It does not assert that Navier-Stokes supplies such
a quotient.  It records the stronger hypothesis that all shell-indexed
low-high rows are pullbacks of one fixed finite price kernel, with the
rescaling law and finite replay anchor declared before payoff.  If this source
is paid, it compiles into the ordinary `GalerkinPSDActionFamily` socket below.
-/
structure ScaleCovariantLowHighStatePriceQuotientSource
    {τ : ContinuumLPProfileTopology.{u}}
    (_S : ContinuumLPPrefixPriceStream τ) where
  quotientDimension : ℕ
  quotientOperator : FinitePSDOperator quotientDimension
  quotientCoordinates : ℕ → Fin quotientDimension → ℝ
  quotientAction : ℕ → ℝ
  fixed_low_high_quotient_topology : Prop
  fixed_low_high_quotient_topology_paid :
    fixed_low_high_quotient_topology
  shell_rescaling_law_declared_before_payoff : Prop
  shell_rescaling_law_declared_before_payoff_paid :
    shell_rescaling_law_declared_before_payoff
  quotient_operator_declared_before_payoff : Prop
  quotient_operator_declared_before_payoff_paid :
    quotient_operator_declared_before_payoff
  quotient_coordinates_declared_before_payoff : Prop
  quotient_coordinates_declared_before_payoff_paid :
    quotient_coordinates_declared_before_payoff
  quotient_action_declared_before_payoff : Prop
  quotient_action_declared_before_payoff_paid :
    quotient_action_declared_before_payoff
  no_posthoc_shell_or_coordinate_substitution : Prop
  no_posthoc_shell_or_coordinate_substitution_paid :
    no_posthoc_shell_or_coordinate_substitution
  scale_covariance_to_original_low_high_kernel : Prop
  scale_covariance_to_original_low_high_kernel_paid :
    scale_covariance_to_original_low_high_kernel
  finite_replay_anchored_to_source_rows : Prop
  finite_replay_anchored_to_source_rows_paid :
    finite_replay_anchored_to_source_rows
  exact_quotient_action_identity :
    ∀ N : ℕ,
      quotientAction N =
        finiteOperatorQuadratic
          quotientOperator.carrier
          (quotientCoordinates N)

/-- A paid scale-covariant quotient source has nonnegative quotient action. -/
theorem scale_covariant_low_high_quotient_action_nonnegative
    {τ : ContinuumLPProfileTopology.{u}}
    {S : ContinuumLPPrefixPriceStream τ}
    (Q : ScaleCovariantLowHighStatePriceQuotientSource S)
    (N : ℕ) :
    0 ≤ Q.quotientAction N := by
  rw [Q.exact_quotient_action_identity N]
  exact Q.quotientOperator.quadratic_nonnegative (Q.quotientCoordinates N)

/-- Hostile falsifier surface for the quotient-kernel compression. -/
inductive ScaleCovariantLowHighStatePriceQuotientFalsifier
    {τ : ContinuumLPProfileTopology.{u}}
    {S : ContinuumLPPrefixPriceStream τ}
    (Q : ScaleCovariantLowHighStatePriceQuotientSource S) : Prop where
  | quotient_topology_not_fixed :
      ¬ Q.fixed_low_high_quotient_topology →
        ScaleCovariantLowHighStatePriceQuotientFalsifier Q
  | shell_rescaling_posthoc :
      ¬ Q.shell_rescaling_law_declared_before_payoff →
        ScaleCovariantLowHighStatePriceQuotientFalsifier Q
  | quotient_operator_posthoc :
      ¬ Q.quotient_operator_declared_before_payoff →
        ScaleCovariantLowHighStatePriceQuotientFalsifier Q
  | quotient_coordinates_posthoc :
      ¬ Q.quotient_coordinates_declared_before_payoff →
        ScaleCovariantLowHighStatePriceQuotientFalsifier Q
  | quotient_action_posthoc :
      ¬ Q.quotient_action_declared_before_payoff →
        ScaleCovariantLowHighStatePriceQuotientFalsifier Q
  | shell_or_coordinate_substituted :
      ¬ Q.no_posthoc_shell_or_coordinate_substitution →
        ScaleCovariantLowHighStatePriceQuotientFalsifier Q
  | scale_covariance_break :
      ¬ Q.scale_covariance_to_original_low_high_kernel →
        ScaleCovariantLowHighStatePriceQuotientFalsifier Q
  | finite_replay_unanchored :
      ¬ Q.finite_replay_anchored_to_source_rows →
        ScaleCovariantLowHighStatePriceQuotientFalsifier Q
  | quotient_action_identity_break
      (N : ℕ) :
      Q.quotientAction N ≠
          finiteOperatorQuadratic
            Q.quotientOperator.carrier
            (Q.quotientCoordinates N) →
        ScaleCovariantLowHighStatePriceQuotientFalsifier Q

/-- A paid quotient-kernel source excludes every named guard failure. -/
theorem no_scale_covariant_low_high_quotient_falsifier
    {τ : ContinuumLPProfileTopology.{u}}
    {S : ContinuumLPPrefixPriceStream τ}
    (Q : ScaleCovariantLowHighStatePriceQuotientSource S)
    (F : ScaleCovariantLowHighStatePriceQuotientFalsifier Q) :
    False := by
  cases F with
  | quotient_topology_not_fixed hbad =>
      exact hbad Q.fixed_low_high_quotient_topology_paid
  | shell_rescaling_posthoc hbad =>
      exact hbad Q.shell_rescaling_law_declared_before_payoff_paid
  | quotient_operator_posthoc hbad =>
      exact hbad Q.quotient_operator_declared_before_payoff_paid
  | quotient_coordinates_posthoc hbad =>
      exact hbad Q.quotient_coordinates_declared_before_payoff_paid
  | quotient_action_posthoc hbad =>
      exact hbad Q.quotient_action_declared_before_payoff_paid
  | shell_or_coordinate_substituted hbad =>
      exact hbad Q.no_posthoc_shell_or_coordinate_substitution_paid
  | scale_covariance_break hbad =>
      exact hbad Q.scale_covariance_to_original_low_high_kernel_paid
  | finite_replay_unanchored hbad =>
      exact hbad Q.finite_replay_anchored_to_source_rows_paid
  | quotient_action_identity_break N hbad =>
      exact hbad (Q.exact_quotient_action_identity N)

/-- A paid scale-covariant quotient kernel is a fixed Galerkin PSD action
family with constant quotient dimension and operator.

The quotient source is not a shortcut around the continuum estimates.  It only
packages the finite-kernel identity and anti-posthoc guards into the same
source socket used by the kinematic-action LSC constructor. -/
def galerkin_psd_action_family_of_scale_covariant_low_high_quotient_source
    {τ : ContinuumLPProfileTopology.{u}}
    {S : ContinuumLPPrefixPriceStream τ}
    (Q : ScaleCovariantLowHighStatePriceQuotientSource S) :
    GalerkinPSDActionFamily S where
  dimension := fun _ => Q.quotientDimension
  operator := fun _ => Q.quotientOperator
  coordinates := Q.quotientCoordinates
  action := Q.quotientAction
  fixed_galerkin_topology :=
    Q.fixed_low_high_quotient_topology ∧
      Q.shell_rescaling_law_declared_before_payoff ∧
        Q.scale_covariance_to_original_low_high_kernel ∧
          Q.finite_replay_anchored_to_source_rows
  fixed_galerkin_topology_paid :=
    ⟨Q.fixed_low_high_quotient_topology_paid,
      Q.shell_rescaling_law_declared_before_payoff_paid,
      Q.scale_covariance_to_original_low_high_kernel_paid,
      Q.finite_replay_anchored_to_source_rows_paid⟩
  operators_declared_before_payoff :=
    Q.quotient_operator_declared_before_payoff
  operators_declared_before_payoff_paid :=
    Q.quotient_operator_declared_before_payoff_paid
  coordinates_declared_before_payoff :=
    Q.quotient_coordinates_declared_before_payoff
  coordinates_declared_before_payoff_paid :=
    Q.quotient_coordinates_declared_before_payoff_paid
  action_declared_before_payoff :=
    Q.quotient_action_declared_before_payoff
  action_declared_before_payoff_paid :=
    Q.quotient_action_declared_before_payoff_paid
  no_posthoc_operator_or_coordinate_substitution :=
    Q.no_posthoc_shell_or_coordinate_substitution
  no_posthoc_operator_or_coordinate_substitution_paid :=
    Q.no_posthoc_shell_or_coordinate_substitution_paid
  exact_action_identity := Q.exact_quotient_action_identity

/-- Convert a fixed Galerkin PSD action family into the GP216 kinematic-action
LSC source.

The PSD family supplies the predeclared action and its operator identity.  The
three analytic estimates that actually promote finite Galerkin data to the
continuum limit are still explicit: target dominated by the action liminf,
action dominated by each prefix price, and boundedness/coboundedness side
conditions. -/
def continuum_kinematic_action_lsc_source_of_galerkin_psd_action_family
    {τ : ContinuumLPProfileTopology.{u}}
    {S : ContinuumLPPrefixPriceStream τ}
    (G : GalerkinPSDActionFamily S)
    (target_le_liminf_action :
      continuumGlobalSelfTaxTarget S ≤
        Filter.liminf G.action Filter.atTop)
    (action_le_prefix_price :
      ∀ N : ℕ, G.action N ≤ continuumLPPrefixPrice S N)
    (action_bounded :
      Filter.atTop.IsBoundedUnder (· ≥ ·) G.action)
    (prefix_cobounded :
      Filter.atTop.IsCoboundedUnder (· ≥ ·)
        (fun N : ℕ => continuumLPPrefixPrice S N))
    (prefix_bounded :
      Filter.atTop.IsBoundedUnder (· ≥ ·)
        (fun N : ℕ => continuumLPPrefixPrice S N)) :
    ContinuumLPKinematicActionLSCSource S where
  action := G.action
  action_declared_before_payoff :=
    G.action_declared_before_payoff ∧
      G.operators_declared_before_payoff ∧
        G.coordinates_declared_before_payoff ∧
          G.no_posthoc_operator_or_coordinate_substitution
  action_declared_before_payoff_paid :=
    ⟨G.action_declared_before_payoff_paid,
      G.operators_declared_before_payoff_paid,
      G.coordinates_declared_before_payoff_paid,
      G.no_posthoc_operator_or_coordinate_substitution_paid⟩
  target_le_liminf_action := target_le_liminf_action
  action_le_prefix_price := action_le_prefix_price
  action_bounded := action_bounded
  prefix_cobounded := prefix_cobounded
  prefix_bounded := prefix_bounded

/-- Build the all-output LP/Bony source through a fixed Galerkin PSD action
family.

This is just the composition of the Galerkin-action adapter with the GP216
source constructor.  It does not remove any of the other all-output source
obligations. -/
def continuum_all_output_lp_bony_source_of_galerkin_psd_action_family
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ)
    (fixed_topology : ContinuumLPUsesFixedTopology S)
    (fixed_atoms : FixedAllOutputLPBonyAtoms S)
    (prefix_charge : ∀ N : ℕ, PrefixAllOutputCoherenceCharge S N)
    (G : GalerkinPSDActionFamily S)
    (target_le_liminf_action :
      continuumGlobalSelfTaxTarget S ≤
        Filter.liminf G.action Filter.atTop)
    (action_le_prefix_price :
      ∀ N : ℕ, G.action N ≤ continuumLPPrefixPrice S N)
    (action_bounded :
      Filter.atTop.IsBoundedUnder (· ≥ ·) G.action)
    (prefix_cobounded :
      Filter.atTop.IsCoboundedUnder (· ≥ ·)
        (fun N : ℕ => continuumLPPrefixPrice S N))
    (prefix_bounded :
      Filter.atTop.IsBoundedUnder (· ≥ ·)
        (fun N : ℕ => continuumLPPrefixPrice S N))
    (liminf_price_bound : ContinuumLPLiminfPriceBound S)
    (smooth_budget_bridge : ContinuumLPSmoothBudgetBridge S)
    (stream_declared_before_payoff : Prop)
    (stream_declared_before_payoff_paid :
      stream_declared_before_payoff)
    (no_posthoc_stream_or_atom_substitution : Prop)
    (no_posthoc_stream_or_atom_substitution_paid :
      no_posthoc_stream_or_atom_substitution) :
    ContinuumAllOutputLPBonySource τ :=
  continuum_all_output_lp_bony_source_of_kinematic_action_lsc
    S
    fixed_topology
    fixed_atoms
    prefix_charge
    (continuum_kinematic_action_lsc_source_of_galerkin_psd_action_family
      G
      target_le_liminf_action
      action_le_prefix_price
      action_bounded
      prefix_cobounded
      prefix_bounded)
    liminf_price_bound
    smooth_budget_bridge
    stream_declared_before_payoff
    stream_declared_before_payoff_paid
    no_posthoc_stream_or_atom_substitution
    no_posthoc_stream_or_atom_substitution_paid

end

end ZtareProofs.NS
