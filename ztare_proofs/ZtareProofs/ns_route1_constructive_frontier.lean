import Mathlib.Tactic
import ZtareProofs.ns_global_tail_coercivity_bridge
import ZtareProofs.ns_commutator_tower_defect_budget
import ZtareProofs.ns_commutator_tower_contraction_bridge
import ZtareProofs.ns_commutator_tower_irreducible_estimate
import ZtareProofs.ns_frequency_sensitive_commutator_collapse
import ZtareProofs.ns_pressure_hessian_l2_bridge
import ZtareProofs.ns_no_invisible_critical_profile

namespace ZtareProofs

/-!
`ns_route1_constructive_frontier` packages the exact live route-1 obligations
after the proof-search obstruction mining and local proof compression.

This file is the route-1 counterpart to `ns_route5_constructive_frontier`:

1. global tail coercivity antecedent,
2. pressure-side defect budget,
3. transport-to-tower contraction bridge,
4. frequency-sensitive collapse check.
-/

/--
Unified route-1 frontier target.
-/
def route1ConstructiveFrontierTarget
    (δ penalty K tailDecay margin residualTransition
      stretch pressureL2 vorticitySq radialGrade Λ0 C0 decayProfile
      transportDefect localQuadratic advectedPressure commutatorResidual
      budget currentStep nextStep ratio carrier amplitude ε lam : Real) : Prop :=
  ns_global_tail_coercivity_bridge
      δ penalty K tailDecay margin residualTransition ∧
    route1ExactNextTarget
      stretch pressureL2 vorticitySq radialGrade Λ0 C0 decayProfile
      transportDefect localQuadratic advectedPressure commutatorResidual
      budget currentStep nextStep ratio ∧
    ¬ route5PrecedenceAfterFrequencyCollapse δ lam amplitude ε

/--
Strict-margin variant of the route-1 constructive frontier.

The global tail bridge keeps its original `margin`; the route-1 scalar
subcriticality duty is exposed separately as `budgetMargin`.
-/
def route1StrictMarginConstructiveFrontierTarget
    (δ penalty K tailDecay margin residualTransition
      stretch pressureL2 vorticitySq radialGrade Λ0 C0 decayProfile
      transportDefect localQuadratic advectedPressure commutatorResidual
      budget currentStep nextStep ratio budgetMargin carrier amplitude ε lam : Real) : Prop :=
  ns_global_tail_coercivity_bridge
      δ penalty K tailDecay margin residualTransition ∧
    route1StrictMarginNextTarget
      stretch pressureL2 vorticitySq radialGrade Λ0 C0 decayProfile
      transportDefect localQuadratic advectedPressure commutatorResidual
      budget currentStep nextStep ratio budgetMargin ∧
    ¬ route5PrecedenceAfterFrequencyCollapse δ lam amplitude ε

/--
The strict-margin frontier pays the existing route-1 constructive frontier.
-/
theorem route1ConstructiveFrontierTarget_of_strictMarginFrontier
    {δ penalty K tailDecay margin residualTransition
      stretch pressureL2 vorticitySq radialGrade Λ0 C0 decayProfile
      transportDefect localQuadratic advectedPressure commutatorResidual
      budget currentStep nextStep ratio budgetMargin carrier amplitude ε lam : Real}
    (h :
      route1StrictMarginConstructiveFrontierTarget
        δ penalty K tailDecay margin residualTransition
        stretch pressureL2 vorticitySq radialGrade Λ0 C0 decayProfile
        transportDefect localQuadratic advectedPressure commutatorResidual
        budget currentStep nextStep ratio budgetMargin carrier amplitude ε lam) :
    route1ConstructiveFrontierTarget
      δ penalty K tailDecay margin residualTransition
      stretch pressureL2 vorticitySq radialGrade Λ0 C0 decayProfile
      transportDefect localQuadratic advectedPressure commutatorResidual
      budget currentStep nextStep ratio carrier amplitude ε lam := by
  rcases h with ⟨htail, hroute1, hnoCollapse⟩
  exact ⟨htail, route1ExactNextTarget_of_route1StrictMarginNextTarget hroute1,
    hnoCollapse⟩

/--
Projection theorem: the packaged route-1 frontier really contains the exact
pressure-transport budget and contraction hinge.
-/
theorem route1_frontier_contains_exact_next_target
    {δ penalty K tailDecay margin residualTransition
      stretch pressureL2 vorticitySq radialGrade Λ0 C0 decayProfile
      transportDefect localQuadratic advectedPressure commutatorResidual
      budget currentStep nextStep ratio carrier amplitude ε lam : Real}
    (h :
      route1ConstructiveFrontierTarget δ penalty K tailDecay margin
        residualTransition stretch pressureL2 vorticitySq radialGrade Λ0 C0
        decayProfile transportDefect localQuadratic advectedPressure
        commutatorResidual budget currentStep nextStep ratio carrier amplitude ε
        lam) :
    route1ExactNextTarget
      stretch pressureL2 vorticitySq radialGrade Λ0 C0 decayProfile
      transportDefect localQuadratic advectedPressure commutatorResidual
      budget currentStep nextStep ratio := by
  exact h.2.1

/--
Projection theorem: route 1 remains primary only while the frequency-sensitive
collapse regime is not paid.
-/
theorem route1_frontier_requires_no_frequency_collapse
    {δ penalty K tailDecay margin residualTransition
      stretch pressureL2 vorticitySq radialGrade Λ0 C0 decayProfile
      transportDefect localQuadratic advectedPressure commutatorResidual
      budget currentStep nextStep ratio carrier amplitude ε lam : Real}
    (h :
      route1ConstructiveFrontierTarget δ penalty K tailDecay margin
        residualTransition stretch pressureL2 vorticitySq radialGrade Λ0 C0
        decayProfile transportDefect localQuadratic advectedPressure
        commutatorResidual budget currentStep nextStep ratio carrier amplitude ε
        lam) :
    ¬ route5PrecedenceAfterFrequencyCollapse δ lam amplitude ε := by
  exact h.2.2

/-!
## GPT-5.5 route-1 tail-visibility consumption

The 2026-05-13 GPT-5.5 response sharpened the route-1 bottleneck: the useful
replacement for the strict source-budget oracle is a non-tautological critical
tail visibility object. The algebra below deliberately contains no PDE content;
the PDE content is isolated in `criticalTailVisible` and `channelLoss`.
-/

/--
Route-1 critical tail visibility package.

`S` is the source budget, split into resolved and unresolved tail parts.
The strict scalar margin follows only if the unresolved tail is visible through
an independently defined channel sum. Defining `visibility` as `rho * X - S`
would violate the intended use of this structure.
-/
structure Route1CriticalTailVisibility where
  rho : Real
  X : Real
  S : Real
  X_res : Real
  X_tail : Real
  S_res : Real
  S_tail : Real
  visibility : Real
  deltaRes : Real
  kappa : Real
  nu : Real
  epsTail : Real
  tailError : Real
  X_nonneg : 0 ≤ X
  X_res_nonneg : 0 ≤ X_res
  X_tail_nonneg : 0 ≤ X_tail
  X_split : X = X_res + X_tail
  S_split : S = S_res + S_tail
  resolvedStrict : S_res ≤ (rho - deltaRes) * X_res
  channelLoss : S_tail ≤ rho * X_tail - kappa * visibility + tailError
  tailErrorSmall : tailError ≤ epsTail * X
  criticalTailVisible : nu * X_tail ≤ visibility
  deltaRes_pos : 0 < deltaRes
  kappa_pos : 0 < kappa
  nu_pos : 0 < nu

/--
Scalar constructor: a critical tail visibility package pays a strict route-1
source-budget subratio.

All proof-facing PDE difficulty is upstream of this theorem, in the visibility
and channel-loss fields.
-/
theorem exists_strict_source_subratio_of_Route1CriticalTailVisibility
    (h : Route1CriticalTailVisibility)
    (h_eps :
      h.epsTail ≤ (1 / 2 : Real) * min h.deltaRes (h.kappa * h.nu)) :
    ∃ rho' : Real, rho' < h.rho ∧ h.S ≤ rho' * h.X := by
  let m : Real := min h.deltaRes (h.kappa * h.nu)
  let gap : Real := (1 / 2 : Real) * m
  have hknu_pos : 0 < h.kappa * h.nu := mul_pos h.kappa_pos h.nu_pos
  have hm_pos : 0 < m := by
    dsimp [m]
    exact lt_min h.deltaRes_pos hknu_pos
  have hgap_pos : 0 < gap := by
    dsimp [gap]
    nlinarith
  refine ⟨h.rho - gap, ?_, ?_⟩
  · nlinarith
  · have hvis_loss : h.kappa * (h.nu * h.X_tail) ≤ h.kappa * h.visibility := by
      exact mul_le_mul_of_nonneg_left h.criticalTailVisible (le_of_lt h.kappa_pos)
    have htail :
        h.S_tail ≤ (h.rho - h.kappa * h.nu) * h.X_tail + h.epsTail * h.X := by
      nlinarith [h.channelLoss, h.tailErrorSmall, hvis_loss]
    have hm_delta : m ≤ h.deltaRes := by
      dsimp [m]
      exact min_le_left h.deltaRes (h.kappa * h.nu)
    have hm_knu : m ≤ h.kappa * h.nu := by
      dsimp [m]
      exact min_le_right h.deltaRes (h.kappa * h.nu)
    have hres_loss : m * h.X_res ≤ h.deltaRes * h.X_res :=
      mul_le_mul_of_nonneg_right hm_delta h.X_res_nonneg
    have htail_loss : m * h.X_tail ≤ (h.kappa * h.nu) * h.X_tail :=
      mul_le_mul_of_nonneg_right hm_knu h.X_tail_nonneg
    have h_eps_gap : h.epsTail ≤ gap := by
      dsimp [gap, m] at h_eps ⊢
      exact h_eps
    have herror_gap : h.epsTail * h.X ≤ gap * h.X :=
      mul_le_mul_of_nonneg_right h_eps_gap h.X_nonneg
    have hres_bound : h.S_res ≤ (h.rho - m) * h.X_res := by
      nlinarith [h.resolvedStrict, hres_loss]
    have htail_bound :
        h.S_tail ≤ (h.rho - m) * h.X_tail + gap * h.X := by
      nlinarith [htail, htail_loss, herror_gap]
    have hgap_m : m = 2 * gap := by
      dsimp [gap]
      ring
    have hsum_bound :
        h.S ≤ (h.rho - m) * (h.X_res + h.X_tail) + gap * h.X := by
      nlinarith [h.S_split, hres_bound, htail_bound]
    have hrearrange :
        (h.rho - m) * (h.X_res + h.X_tail) + gap * h.X =
          (h.rho - gap) * h.X := by
      rw [← h.X_split, hgap_m]
      ring
    simpa [hrearrange] using hsum_bound

/-- The independently named route-1 visibility channels. -/
def route1ChannelVisibilitySum (V_T V_Q V_P V_C : Real) : Real :=
  V_T + V_Q + V_P + V_C

/--
Five-channel route-1 visibility sum.

`V_Aperp` is the active singular source channel: the part of the unresolved
active carrier that is not dominated by transport, pressure/quadratic,
commutator, or profile-residual visibility.  It is named separately so that a
singular tangent defect cannot be silently folded into the no-invisible
residual.
-/
def route1FiveChannelVisibilitySum
    (V_T V_Q V_P V_C V_Aperp : Real) : Real :=
  V_T + V_Q + V_P + V_C + V_Aperp

/--
Producer form for route-1 critical tail visibility.

Unlike `Route1CriticalTailVisibility`, this structure does not carry a scalar
`visibility` field.  The visibility used by the scalar constructor must be the
sum of separately named transport, quadratic, pressure, and commutator channels.
This prevents the strict source-budget conclusion from being hidden inside a
single opaque scalar.
-/
structure Route1ChannelVisibilityProducer where
  rho : Real
  X : Real
  S : Real
  X_res : Real
  X_tail : Real
  S_res : Real
  S_tail : Real
  V_T : Real
  V_Q : Real
  V_P : Real
  V_C : Real
  deltaRes : Real
  kappa : Real
  nu : Real
  epsTail : Real
  tailError : Real
  X_nonneg : 0 ≤ X
  X_res_nonneg : 0 ≤ X_res
  X_tail_nonneg : 0 ≤ X_tail
  V_T_nonneg : 0 ≤ V_T
  V_Q_nonneg : 0 ≤ V_Q
  V_P_nonneg : 0 ≤ V_P
  V_C_nonneg : 0 ≤ V_C
  X_split : X = X_res + X_tail
  S_split : S = S_res + S_tail
  resolvedStrict : S_res ≤ (rho - deltaRes) * X_res
  channelLossFromChannelSum :
    S_tail ≤
      rho * X_tail -
        kappa * route1ChannelVisibilitySum V_T V_Q V_P V_C +
          tailError
  tailErrorSmall : tailError ≤ epsTail * X
  criticalTailVisibleFromChannelSum :
    nu * X_tail ≤ route1ChannelVisibilitySum V_T V_Q V_P V_C
  deltaRes_pos : 0 < deltaRes
  kappa_pos : 0 < kappa
  nu_pos : 0 < nu

/--
Route-1 source accounting and channel-loss data without the critical-tail
visibility lower bound.  This is the anti-smuggling base: no theorem using this
structure can import `nu * X_tail <= V_T + V_Q + V_P + V_C` unless a separate
PDE receipt supplies it.
-/
structure Route1ChannelAccountingBase where
  rho : Real
  X : Real
  S : Real
  X_res : Real
  X_tail : Real
  S_res : Real
  S_tail : Real
  V_T : Real
  V_Q : Real
  V_P : Real
  V_C : Real
  deltaRes : Real
  kappa : Real
  nu : Real
  epsTail : Real
  tailError : Real
  X_nonneg : 0 ≤ X
  X_res_nonneg : 0 ≤ X_res
  X_tail_nonneg : 0 ≤ X_tail
  V_T_nonneg : 0 ≤ V_T
  V_Q_nonneg : 0 ≤ V_Q
  V_P_nonneg : 0 ≤ V_P
  V_C_nonneg : 0 ≤ V_C
  X_split : X = X_res + X_tail
  S_split : S = S_res + S_tail
  resolvedStrict : S_res ≤ (rho - deltaRes) * X_res
  channelLossFromChannelSum :
    S_tail ≤
      rho * X_tail -
        kappa * route1ChannelVisibilitySum V_T V_Q V_P V_C +
          tailError
  tailErrorSmall : tailError ≤ epsTail * X
  deltaRes_pos : 0 < deltaRes
  kappa_pos : 0 < kappa
  nu_pos : 0 < nu

/-- Forget the visibility lower-bound field of a full channel producer. -/
def Route1ChannelVisibilityProducer.accountingBase
    (h : Route1ChannelVisibilityProducer) : Route1ChannelAccountingBase where
  rho := h.rho
  X := h.X
  S := h.S
  X_res := h.X_res
  X_tail := h.X_tail
  S_res := h.S_res
  S_tail := h.S_tail
  V_T := h.V_T
  V_Q := h.V_Q
  V_P := h.V_P
  V_C := h.V_C
  deltaRes := h.deltaRes
  kappa := h.kappa
  nu := h.nu
  epsTail := h.epsTail
  tailError := h.tailError
  X_nonneg := h.X_nonneg
  X_res_nonneg := h.X_res_nonneg
  X_tail_nonneg := h.X_tail_nonneg
  V_T_nonneg := h.V_T_nonneg
  V_Q_nonneg := h.V_Q_nonneg
  V_P_nonneg := h.V_P_nonneg
  V_C_nonneg := h.V_C_nonneg
  X_split := h.X_split
  S_split := h.S_split
  resolvedStrict := h.resolvedStrict
  channelLossFromChannelSum := h.channelLossFromChannelSum
  tailErrorSmall := h.tailErrorSmall
  deltaRes_pos := h.deltaRes_pos
  kappa_pos := h.kappa_pos
  nu_pos := h.nu_pos

/-- Add an independently proved visibility lower bound to the accounting base. -/
def Route1ChannelAccountingBase.toProducer
    (h : Route1ChannelAccountingBase)
    (hvisible : h.nu * h.X_tail ≤ route1ChannelVisibilitySum h.V_T h.V_Q h.V_P h.V_C) :
    Route1ChannelVisibilityProducer where
  rho := h.rho
  X := h.X
  S := h.S
  X_res := h.X_res
  X_tail := h.X_tail
  S_res := h.S_res
  S_tail := h.S_tail
  V_T := h.V_T
  V_Q := h.V_Q
  V_P := h.V_P
  V_C := h.V_C
  deltaRes := h.deltaRes
  kappa := h.kappa
  nu := h.nu
  epsTail := h.epsTail
  tailError := h.tailError
  X_nonneg := h.X_nonneg
  X_res_nonneg := h.X_res_nonneg
  X_tail_nonneg := h.X_tail_nonneg
  V_T_nonneg := h.V_T_nonneg
  V_Q_nonneg := h.V_Q_nonneg
  V_P_nonneg := h.V_P_nonneg
  V_C_nonneg := h.V_C_nonneg
  X_split := h.X_split
  S_split := h.S_split
  resolvedStrict := h.resolvedStrict
  channelLossFromChannelSum := h.channelLossFromChannelSum
  tailErrorSmall := h.tailErrorSmall
  criticalTailVisibleFromChannelSum := hvisible
  deltaRes_pos := h.deltaRes_pos
  kappa_pos := h.kappa_pos
  nu_pos := h.nu_pos

/--
Constructor from independently named visibility channels to the scalar package
consumed by the route-1 algebra.
-/
def Route1CriticalTailVisibility.ofChannelProducer
    (h : Route1ChannelVisibilityProducer) : Route1CriticalTailVisibility where
  rho := h.rho
  X := h.X
  S := h.S
  X_res := h.X_res
  X_tail := h.X_tail
  S_res := h.S_res
  S_tail := h.S_tail
  visibility := route1ChannelVisibilitySum h.V_T h.V_Q h.V_P h.V_C
  deltaRes := h.deltaRes
  kappa := h.kappa
  nu := h.nu
  epsTail := h.epsTail
  tailError := h.tailError
  X_nonneg := h.X_nonneg
  X_res_nonneg := h.X_res_nonneg
  X_tail_nonneg := h.X_tail_nonneg
  X_split := h.X_split
  S_split := h.S_split
  resolvedStrict := h.resolvedStrict
  channelLoss := h.channelLossFromChannelSum
  tailErrorSmall := h.tailErrorSmall
  criticalTailVisible := h.criticalTailVisibleFromChannelSum
  deltaRes_pos := h.deltaRes_pos
  kappa_pos := h.kappa_pos
  nu_pos := h.nu_pos

/--
Projection theorem for the channel producer: all four channel receipts stay
visible, and the tail-visibility lower bound is explicitly over their sum.
-/
theorem route1_channel_visibility_producer_projects
    (h : Route1ChannelVisibilityProducer) :
    0 ≤ h.V_T ∧ 0 ≤ h.V_Q ∧ 0 ≤ h.V_P ∧ 0 ≤ h.V_C ∧
      h.nu * h.X_tail ≤
        route1ChannelVisibilitySum h.V_T h.V_Q h.V_P h.V_C := by
  exact ⟨h.V_T_nonneg, h.V_Q_nonneg, h.V_P_nonneg, h.V_C_nonneg,
    h.criticalTailVisibleFromChannelSum⟩

/--
Strict source subratio from a channel producer.  This is still algebra only;
the producer fields are the PDE obligations.
-/
theorem exists_strict_source_subratio_of_Route1ChannelVisibilityProducer
    (h : Route1ChannelVisibilityProducer)
    (h_eps :
      h.epsTail ≤ (1 / 2 : Real) * min h.deltaRes (h.kappa * h.nu)) :
    ∃ rho' : Real, rho' < h.rho ∧ h.S ≤ rho' * h.X :=
  exists_strict_source_subratio_of_Route1CriticalTailVisibility
    (Route1CriticalTailVisibility.ofChannelProducer h) h_eps

/--
Five-channel producer for the active-singular branch.

This is still algebra only.  The PDE obligations are the channel-loss estimate
against the five-channel sum and the lower bound saying the active tail is
visible through the five named channels.  In particular, `V_Aperp` must be
constructed independently as an active singular/defect channel; it may not be
defined from budget slack.
-/
structure Route1FiveChannelVisibilityProducer where
  rho : Real
  X : Real
  S : Real
  X_res : Real
  X_tail : Real
  S_res : Real
  S_tail : Real
  V_T : Real
  V_Q : Real
  V_P : Real
  V_C : Real
  V_Aperp : Real
  deltaRes : Real
  kappa : Real
  nu : Real
  epsTail : Real
  tailError : Real
  X_nonneg : 0 ≤ X
  X_res_nonneg : 0 ≤ X_res
  X_tail_nonneg : 0 ≤ X_tail
  V_T_nonneg : 0 ≤ V_T
  V_Q_nonneg : 0 ≤ V_Q
  V_P_nonneg : 0 ≤ V_P
  V_C_nonneg : 0 ≤ V_C
  V_Aperp_nonneg : 0 ≤ V_Aperp
  X_split : X = X_res + X_tail
  S_split : S = S_res + S_tail
  resolvedStrict : S_res ≤ (rho - deltaRes) * X_res
  channelLossFromFiveChannelSum :
    S_tail ≤
      rho * X_tail -
        kappa *
          route1FiveChannelVisibilitySum V_T V_Q V_P V_C V_Aperp +
          tailError
  tailErrorSmall : tailError ≤ epsTail * X
  criticalTailVisibleFromFiveChannelSum :
    nu * X_tail ≤
      route1FiveChannelVisibilitySum V_T V_Q V_P V_C V_Aperp
  deltaRes_pos : 0 < deltaRes
  kappa_pos : 0 < kappa
  nu_pos : 0 < nu
  activeSingularChannelIndependent : Prop
  activeSingularChannelNotBudgetSlack : Prop

/--
Collapse a five-channel producer to the existing four-channel algebra by
aggregating the active singular channel into the final scalar slot.  The source
surface still records `V_Aperp` independently; this function is only the
algebraic adapter.
-/
def Route1FiveChannelVisibilityProducer.toFourChannelProducer
    (h : Route1FiveChannelVisibilityProducer) :
    Route1ChannelVisibilityProducer where
  rho := h.rho
  X := h.X
  S := h.S
  X_res := h.X_res
  X_tail := h.X_tail
  S_res := h.S_res
  S_tail := h.S_tail
  V_T := h.V_T
  V_Q := h.V_Q
  V_P := h.V_P
  V_C := h.V_C + h.V_Aperp
  deltaRes := h.deltaRes
  kappa := h.kappa
  nu := h.nu
  epsTail := h.epsTail
  tailError := h.tailError
  X_nonneg := h.X_nonneg
  X_res_nonneg := h.X_res_nonneg
  X_tail_nonneg := h.X_tail_nonneg
  V_T_nonneg := h.V_T_nonneg
  V_Q_nonneg := h.V_Q_nonneg
  V_P_nonneg := h.V_P_nonneg
  V_C_nonneg := add_nonneg h.V_C_nonneg h.V_Aperp_nonneg
  X_split := h.X_split
  S_split := h.S_split
  resolvedStrict := h.resolvedStrict
  channelLossFromChannelSum := by
    simpa [route1ChannelVisibilitySum, route1FiveChannelVisibilitySum,
      add_assoc, add_left_comm, add_comm] using
      h.channelLossFromFiveChannelSum
  tailErrorSmall := h.tailErrorSmall
  criticalTailVisibleFromChannelSum := by
    simpa [route1ChannelVisibilitySum, route1FiveChannelVisibilitySum,
      add_assoc, add_left_comm, add_comm] using
      h.criticalTailVisibleFromFiveChannelSum
  deltaRes_pos := h.deltaRes_pos
  kappa_pos := h.kappa_pos
  nu_pos := h.nu_pos

/--
Strict route-1 source subratio from five independently named channels,
including the active singular channel `V_Aperp`.
-/
theorem exists_strict_source_subratio_of_Route1FiveChannelVisibilityProducer
    (h : Route1FiveChannelVisibilityProducer)
    (h_eps :
      h.epsTail ≤ (1 / 2 : Real) * min h.deltaRes (h.kappa * h.nu)) :
    ∃ rho' : Real, rho' < h.rho ∧ h.S ≤ rho' * h.X :=
  exists_strict_source_subratio_of_Route1ChannelVisibilityProducer
    h.toFourChannelProducer h_eps

/--
Low-level weakening of an already proved channel producer.  This should not be
used as a proof-facing PDE bridge: it imports the full visibility lower bound
and then weakens it.  New PDE routes should instead consume
`Route1ChannelAccountingBase` and construct a producer from an independent
visibility receipt.
-/
def Route1ChannelVisibilityProducer.withReducedNu
    (h : Route1ChannelVisibilityProducer)
    (nu' : Real)
    (hnu'_pos : 0 < nu')
    (hnu'_le : nu' ≤ h.nu) : Route1ChannelVisibilityProducer where
  rho := h.rho
  X := h.X
  S := h.S
  X_res := h.X_res
  X_tail := h.X_tail
  S_res := h.S_res
  S_tail := h.S_tail
  V_T := h.V_T
  V_Q := h.V_Q
  V_P := h.V_P
  V_C := h.V_C
  deltaRes := h.deltaRes
  kappa := h.kappa
  nu := nu'
  epsTail := h.epsTail
  tailError := h.tailError
  X_nonneg := h.X_nonneg
  X_res_nonneg := h.X_res_nonneg
  X_tail_nonneg := h.X_tail_nonneg
  V_T_nonneg := h.V_T_nonneg
  V_Q_nonneg := h.V_Q_nonneg
  V_P_nonneg := h.V_P_nonneg
  V_C_nonneg := h.V_C_nonneg
  X_split := h.X_split
  S_split := h.S_split
  resolvedStrict := h.resolvedStrict
  channelLossFromChannelSum := h.channelLossFromChannelSum
  tailErrorSmall := h.tailErrorSmall
  criticalTailVisibleFromChannelSum := by
    have hnu_tail : nu' * h.X_tail ≤ h.nu * h.X_tail :=
      mul_le_mul_of_nonneg_right hnu'_le h.X_tail_nonneg
    exact le_trans hnu_tail h.criticalTailVisibleFromChannelSum
  deltaRes_pos := h.deltaRes_pos
  kappa_pos := h.kappa_pos
  nu_pos := hnu'_pos

/--
Route-1 integration theorem: if the pressure/transport source terms are the
source budget of a critical tail-visibility package, then the package pays the
existing strict-margin route-1 target.

This is the Lean bridge from the GPT-5.5 replacement object back into the
pre-existing route-1 frontier. It remains conditional on the non-tautological
PDE fields of `Route1CriticalTailVisibility`.
-/
theorem exists_route1StrictMarginNextTarget_of_Route1CriticalTailVisibility
    {stretch pressureL2 vorticitySq radialGrade Λ0 C0 decayProfile
      transportDefect localQuadratic advectedPressure commutatorResidual
      budget currentStep nextStep ratio : Real}
    (htransport :
      pressureL2TransportDefectObligation
        stretch pressureL2 vorticitySq radialGrade Λ0 C0 decayProfile
        transportDefect localQuadratic advectedPressure commutatorResidual)
    (hbudget :
      route1DefectBudgetTarget
        transportDefect localQuadratic advectedPressure commutatorResidual budget nextStep)
    (hvis : Route1CriticalTailVisibility)
    (hsource :
      hvis.S = transportDefect + localQuadratic + advectedPressure + commutatorResidual)
    (hX : hvis.X = currentStep)
    (hrho : hvis.rho = ratio)
    (hcurrent_pos : 0 < currentStep)
    (hr0 : 0 ≤ ratio)
    (hr1 : ratio < 1)
    (h_eps :
      hvis.epsTail ≤ (1 / 2 : Real) * min hvis.deltaRes (hvis.kappa * hvis.nu)) :
    ∃ margin : Real,
      route1StrictMarginNextTarget
        stretch pressureL2 vorticitySq radialGrade Λ0 C0 decayProfile
        transportDefect localQuadratic advectedPressure commutatorResidual
        budget currentStep nextStep ratio margin := by
  rcases exists_strict_source_subratio_of_Route1CriticalTailVisibility
      hvis h_eps with
    ⟨rho', hrho_lt, hS_le⟩
  have hstrict :
      transportDefect + localQuadratic + advectedPressure + commutatorResidual <
        ratio * currentStep := by
    have hlt : rho' * hvis.X < hvis.rho * hvis.X := by
      nlinarith [hrho_lt, hcurrent_pos, hX]
    nlinarith [hS_le, hsource, hX, hrho, hlt]
  exact
    exists_route1StrictMarginNextTarget_of_source_sum_strict_subcriticality
      htransport hbudget hr0 hr1 (le_of_lt hcurrent_pos) hstrict

/--
Endpoint accounting no-go surface: strict source-budget subratio does not
follow from endpoint source saturation while source mass can escape beyond
every fixed resolved cutoff.
-/
structure Route1NoStrictSubratioFromEndpointAccounting where
  X : Nat → Real
  T : Nat → Real
  Q : Nat → Real
  P : Nat → Real
  C : Nat → Real
  rho : Real
  resolvedVisibilityAt : Nat → Nat → Real
  X_normalized : ∀ n, X n = 1
  endpointSaturation : ∀ n, T n + Q n + P n + C n = rho * X n
  unresolvedTailEscape : ∀ J, ∃ n, J ≤ n ∧ resolvedVisibilityAt J n = 0
  noStrictRho :
    ¬ ∃ rho' : Real,
      rho' < rho ∧ ∀ n, T n + Q n + P n + C n ≤ rho' * X n

/--
Pressure-channel visibility obligation extracted from the GPT-5.5 response.
This is a theorem target, not a solved estimate.
-/
structure Route1PressureTailVisibility where
  pressureSource : Real
  rhoP : Real
  X_tail : Real
  pressureReserve : Real
  pressureError : Real
  localQuadraticVisibility : Real
  acceptableChildCharge : Real
  pressureTailMass : Real
  C0 : Real
  localPressureDecomposition : Prop
  pressureChannelLoss :
    pressureSource ≤ rhoP * X_tail - C0 * pressureReserve + pressureError
  pressureNoEscape :
    pressureTailMass ≤
      C0 * (localQuadraticVisibility + pressureReserve + acceptableChildCharge)

/--
Commutator-channel visibility obligation extracted from the GPT-5.5 response.
This is a theorem target, not a solved endpoint estimate.
-/
structure Route1CommutatorTailVisibility where
  commutatorSource : Real
  rhoC : Real
  X_tail : Real
  commutatorDefect : Real
  commutatorError : Real
  kappaC : Real
  strongCriticalTailCompactness : Prop
  commutatorChannelLoss :
    commutatorSource ≤ rhoC * X_tail - kappaC * commutatorDefect + commutatorError
  zeroDefectImpliesStrongTailCompactness :
    commutatorDefect = 0 → strongCriticalTailCompactness

/--
Bundled non-tautological PDE side of the route-1 tail-visibility bridge.

This is the PATTERN-022-style PDE bundle consumed from the current harness
state: pressure reserve/no-escape, endpoint commutator visibility/no-escape,
and no-invisible-critical-profile compactness are kept as separate legs.  The
bundle carries a channel producer rather than a scalar visibility package, so
the strict source subratio remains downstream of independently named channels.
-/
structure Route1CriticalTailVisibilityPDEBundle where
  visibilityProducer : Route1ChannelVisibilityProducer
  pressureVisibility : Route1PressureReserveNoEscapeObligation
  pressureReserveFeedsPressure :
    (route1PressureVisibilityReceipts pressureVisibility).pressureReserveReceipt ≤
      visibilityProducer.V_P
  pressureLocalQuadraticFeedsQuadratic :
    (route1PressureVisibilityReceipts pressureVisibility).localQuadraticReceipt ≤
      visibilityProducer.V_Q
  pressureChildChargeFeedsTransport :
    (route1PressureVisibilityReceipts pressureVisibility).childChargeReceipt ≤
      visibilityProducer.V_T
  transportDefect : Real
  localQuadratic : Real
  advectedPressure : Real
  commutatorResidual : Real
  budget : Real
  nextStep : Real
  endpointDefect : Real
  compactTailLoss : Real
  escapeMass : Real
  microstructureLeak : Real
  frequencyLeak : Real
  residualFloor : Real
  tailMass : Real
  tailOscillation : Real
  compactnessModulus : Real
  commutatorVisibility :
    route1CriticalTailVisibilityObligation
      transportDefect localQuadratic advectedPressure commutatorResidual
      budget nextStep
      endpointDefect compactTailLoss
      escapeMass microstructureLeak frequencyLeak residualFloor
      tailMass tailOscillation compactnessModulus
  commutatorResidualFeedsCommutator :
    commutatorResidual ≤ visibilityProducer.V_C
  noInvisibleProfile : Prop
  noInvisibleProfileProof : noInvisibleProfile

/--
Projection theorem for the bundled PDE legs.  This is a guard against
compressing the three distinct PDE obligations into a renamed scalar margin.
-/
theorem route1_critical_tail_visibility_pde_bundle_projects
    (h : Route1CriticalTailVisibilityPDEBundle) :
    (0 ≤ h.visibilityProducer.V_T ∧
        0 ≤ h.visibilityProducer.V_Q ∧
        0 ≤ h.visibilityProducer.V_P ∧
        0 ≤ h.visibilityProducer.V_C) ∧
      ∃ _pressure : Route1PressureReserveNoEscapeObligation,
      (∃ _commutator :
        route1CriticalTailVisibilityObligation
        h.transportDefect h.localQuadratic h.advectedPressure h.commutatorResidual
        h.budget h.nextStep
        h.endpointDefect h.compactTailLoss
        h.escapeMass h.microstructureLeak h.frequencyLeak h.residualFloor
        h.tailMass h.tailOscillation h.compactnessModulus,
        h.noInvisibleProfile) := by
  exact
    ⟨⟨h.visibilityProducer.V_T_nonneg, h.visibilityProducer.V_Q_nonneg,
      h.visibilityProducer.V_P_nonneg, h.visibilityProducer.V_C_nonneg⟩,
      h.pressureVisibility, h.commutatorVisibility, h.noInvisibleProfileProof⟩

/--
Pressure receipt projection from the route-1 PDE bundle.  The pressure leg is
not merely present; its three independently exposed receipts must feed named
route-1 channels.
-/
theorem route1_critical_tail_visibility_pde_bundle_pressure_feeds_channels
    (h : Route1CriticalTailVisibilityPDEBundle) :
    (route1PressureVisibilityReceipts h.pressureVisibility).pressureReserveReceipt ≤
        h.visibilityProducer.V_P ∧
      (route1PressureVisibilityReceipts h.pressureVisibility).localQuadraticReceipt ≤
        h.visibilityProducer.V_Q ∧
      (route1PressureVisibilityReceipts h.pressureVisibility).childChargeReceipt ≤
        h.visibilityProducer.V_T := by
  exact ⟨h.pressureReserveFeedsPressure,
    h.pressureLocalQuadraticFeedsQuadratic, h.pressureChildChargeFeedsTransport⟩

/--
Commutator receipt projection from the route-1 PDE bundle.  The endpoint
escape channels are charged to the independently named commutator receipt,
then to the route-1 `V_C` channel plus the compactness modulus.
-/
theorem route1_critical_tail_visibility_pde_bundle_commutator_receipt
    (h : Route1CriticalTailVisibilityPDEBundle) :
    EndpointCommutatorVisibilityReceipt
      h.endpointDefect h.commutatorResidual h.compactTailLoss
      h.escapeMass h.microstructureLeak h.frequencyLeak h.residualFloor
      h.tailMass h.tailOscillation h.compactnessModulus :=
  endpointCommutatorVisibilityReceipt_of_route1CriticalTailVisibilityObligation
    h.commutatorVisibility

/--
The named commutator route-1 channel pays the endpoint escape channels up to
the compactness modulus.  This is still a visibility/no-escape statement, not a
strict source-budget claim.
-/
theorem route1_critical_tail_visibility_pde_bundle_endpoint_escape_charged
    (h : Route1CriticalTailVisibilityPDEBundle) :
    h.escapeMass + h.microstructureLeak + h.frequencyLeak + h.residualFloor ≤
      h.visibilityProducer.V_C + h.compactnessModulus := by
  have hreceipt :=
    route1_critical_tail_visibility_pde_bundle_commutator_receipt h
  linarith [hreceipt.compactness_modulus_escape_bound,
    h.commutatorResidualFeedsCommutator]

/--
One receipt stack for the route-1 PDE bundle: pressure receipts feed their
named channels, commutator escape is charged to the commutator channel, and the
channel producer supplies the critical-tail lower bound over the full channel
sum.
-/
theorem route1_critical_tail_visibility_pde_bundle_channel_receipt_stack
    (h : Route1CriticalTailVisibilityPDEBundle) :
    (route1PressureVisibilityReceipts h.pressureVisibility).pressureReserveReceipt ≤
        h.visibilityProducer.V_P ∧
      (route1PressureVisibilityReceipts h.pressureVisibility).localQuadraticReceipt ≤
        h.visibilityProducer.V_Q ∧
      (route1PressureVisibilityReceipts h.pressureVisibility).childChargeReceipt ≤
        h.visibilityProducer.V_T ∧
      h.escapeMass + h.microstructureLeak + h.frequencyLeak + h.residualFloor ≤
        h.visibilityProducer.V_C + h.compactnessModulus ∧
      h.visibilityProducer.nu * h.visibilityProducer.X_tail ≤
        route1ChannelVisibilitySum
          h.visibilityProducer.V_T h.visibilityProducer.V_Q
          h.visibilityProducer.V_P h.visibilityProducer.V_C := by
  exact
    ⟨h.pressureReserveFeedsPressure,
      h.pressureLocalQuadraticFeedsQuadratic,
      h.pressureChildChargeFeedsTransport,
      route1_critical_tail_visibility_pde_bundle_endpoint_escape_charged h,
      h.visibilityProducer.criticalTailVisibleFromChannelSum⟩

/--
Route1 can consume the isolated no-invisible-critical-profile compactness leg
without importing the long profile-price tail.  This keeps the profile leg as a
compactness/rigidity contradiction, not as source-budget algebra.
-/
theorem route1_no_invisible_profile_contradiction_of_compactness
    (h : NS.NoInvisibleCriticalProfileCompactnessObligation)
    (hFail : h.strictNoInvisibleCriticalProfileFailure)
    (hZeroVisibility : h.zeroCriticalTailVisibility) :
    False :=
  NS.no_invisible_critical_profile_of_compactness_obligation
    h hFail hZeroVisibility

/--
If an independent pressure lower-bound producer is available and its receipts
feed the route-1 channels, then the pressure leg alone can pay the channel-sum
tail visibility lower bound for the route-1 producer scale.

This is the exact theorem the pressure no-escape counterexample says is missing
from no-escape alone.
-/
theorem route1_pressure_lower_bound_pays_channel_visibility
    (h : Route1CriticalTailVisibilityPDEBundle)
    (hp : Route1PressureVisibilityLowerBoundProducer)
    (hp_obligation : hp.obligation = h.pressureVisibility)
    (hp_tail : hp.X_tail = h.visibilityProducer.X_tail)
    (hnu : h.visibilityProducer.nu ≤ hp.nuP) :
    h.visibilityProducer.nu * h.visibilityProducer.X_tail ≤
      route1ChannelVisibilitySum
        h.visibilityProducer.V_T h.visibilityProducer.V_Q
        h.visibilityProducer.V_P h.visibilityProducer.V_C := by
  have hnuX :
      h.visibilityProducer.nu * h.visibilityProducer.X_tail ≤
        hp.nuP * h.visibilityProducer.X_tail :=
    mul_le_mul_of_nonneg_right hnu h.visibilityProducer.X_tail_nonneg
  have hpBound := hp.pressureReceiptLowerBound
  rw [hp_tail, hp_obligation] at hpBound
  have hreceipts :
      (route1PressureVisibilityReceipts h.pressureVisibility).receiptSum ≤
        h.visibilityProducer.V_T + h.visibilityProducer.V_Q +
          h.visibilityProducer.V_P := by
    dsimp [Route1PressureVisibilityReceipts.receiptSum]
    nlinarith [h.pressureReserveFeedsPressure,
      h.pressureLocalQuadraticFeedsQuadratic,
      h.pressureChildChargeFeedsTransport]
  have hsum :
      h.visibilityProducer.V_T + h.visibilityProducer.V_Q +
          h.visibilityProducer.V_P ≤
        route1ChannelVisibilitySum
          h.visibilityProducer.V_T h.visibilityProducer.V_Q
          h.visibilityProducer.V_P h.visibilityProducer.V_C := by
    dsimp [route1ChannelVisibilitySum]
    nlinarith [h.visibilityProducer.V_C_nonneg]
  exact le_trans hnuX (le_trans hpBound (le_trans hreceipts hsum))

/--
Pressure-small handoff: once pressure tail mass is too small to pay route1
visibility by itself, the remaining obligation is a lower bound from transport,
local quadratic excess, or commutator channels.  This structure names that
non-pressure PDE obligation without converting it into a scalar source-budget
claim.
-/
structure Route1PressureSmallChannelHandoff
    (h : Route1CriticalTailVisibilityPDEBundle) where
  pressureSmall : Route1PressureTailSmall
  pressure_obligation :
    Route1PressureTailSmall.obligation pressureSmall = h.pressureVisibility
  pressure_tail :
    Route1PressureTailSmall.X_tail pressureSmall = h.visibilityProducer.X_tail
  nonpressureVisible :
    h.visibilityProducer.nu * h.visibilityProducer.X_tail ≤
      h.visibilityProducer.V_T + h.visibilityProducer.V_Q +
        h.visibilityProducer.V_C

/--
If the pressure-small branch can pay visibility through transport, local
quadratic excess, or commutator channels, then it pays the full route1 channel
sum.  The pressure channel is used only through nonnegativity.
-/
theorem route1_pressure_small_handoff_pays_channel_visibility
    (h : Route1CriticalTailVisibilityPDEBundle)
    (hs : Route1PressureSmallChannelHandoff h) :
    h.visibilityProducer.nu * h.visibilityProducer.X_tail ≤
      route1ChannelVisibilitySum
        h.visibilityProducer.V_T h.visibilityProducer.V_Q
        h.visibilityProducer.V_P h.visibilityProducer.V_C := by
  have hsum :
      h.visibilityProducer.V_T + h.visibilityProducer.V_Q +
          h.visibilityProducer.V_C ≤
        route1ChannelVisibilitySum
          h.visibilityProducer.V_T h.visibilityProducer.V_Q
          h.visibilityProducer.V_P h.visibilityProducer.V_C := by
    dsimp [route1ChannelVisibilitySum]
    nlinarith [h.visibilityProducer.V_P_nonneg]
  exact le_trans hs.nonpressureVisible hsum

/--
Three-channel pigeonhole for the pressure-small handoff.  If the aggregate
non-pressure visibility pays the route1 tail scale, then transport, local
quadratic excess, or commutator visibility alone pays one third of that scale.
-/
theorem route1_three_channel_visibility_pigeonhole
    (nu X V_T V_Q V_C : Real)
    (h : nu * X ≤ V_T + V_Q + V_C) :
    (nu / 3) * X ≤ V_T ∨
      (nu / 3) * X ≤ V_Q ∨
        (nu / 3) * X ≤ V_C := by
  by_contra hnot
  push Not at hnot
  nlinarith

/--
Concrete split target unlocked by the pressure-small branch: after pressure is
too small, one non-pressure channel must be large at one-third scale.
-/
theorem route1_pressure_small_handoff_has_large_nonpressure_channel
    (h : Route1CriticalTailVisibilityPDEBundle)
    (hs : Route1PressureSmallChannelHandoff h) :
    (h.visibilityProducer.nu / 3) * h.visibilityProducer.X_tail ≤
        h.visibilityProducer.V_T ∨
      (h.visibilityProducer.nu / 3) * h.visibilityProducer.X_tail ≤
        h.visibilityProducer.V_Q ∨
      (h.visibilityProducer.nu / 3) * h.visibilityProducer.X_tail ≤
        h.visibilityProducer.V_C :=
  route1_three_channel_visibility_pigeonhole
    h.visibilityProducer.nu h.visibilityProducer.X_tail
    h.visibilityProducer.V_T h.visibilityProducer.V_Q h.visibilityProducer.V_C
    hs.nonpressureVisible

/--
Anti-smuggling input for the pressure-small local-quadratic route.

This consumes only source accounting and channel-loss data, not a full
`Route1ChannelVisibilityProducer`.  The critical-tail visibility lower bound
must be supplied by the CKN/tent-excess certificate below.
-/
structure Route1PressureSmallQuadraticReducedInput where
  accounting : Route1ChannelAccountingBase
  pressureVisibility : Route1PressureReserveNoEscapeObligation
  tentExcessCertificate : Route1LocalQuadraticTentExcessCertificate
  cert_obligation :
    tentExcessCertificate.obligation = pressureVisibility
  cert_tail :
    tentExcessCertificate.X_tail = accounting.X_tail
  tail_scale_pos : 0 < accounting.X_tail
  etaQ_pays_third :
    accounting.nu / 3 ≤ tentExcessCertificate.etaQ
  pressureLocalQuadraticFeedsQuadratic :
    (route1PressureVisibilityReceipts pressureVisibility).localQuadraticReceipt ≤
      accounting.V_Q
  quadraticChannel_no_extra_oracle :
    accounting.V_Q ≤
      (route1PressureVisibilityReceipts pressureVisibility).localQuadraticReceipt

/--
The tent-excess certificate pays the one-third local-quadratic channel from an
accounting base that has no full visibility oracle.
-/
theorem route1_pressure_small_tent_excess_input_pays_quadratic_channel
    (h : Route1PressureSmallQuadraticReducedInput) :
    (h.accounting.nu / 3) * h.accounting.X_tail ≤ h.accounting.V_Q := by
  have hreceipt :=
    route1_local_quadratic_receipt_lower_bound_of_tent_excess_certificate
      h.tentExcessCertificate
  rw [h.cert_tail, h.cert_obligation] at hreceipt
  have hthird_tail :
      (h.accounting.nu / 3) * h.accounting.X_tail ≤
        h.tentExcessCertificate.etaQ * h.accounting.X_tail :=
    mul_le_mul_of_nonneg_right h.etaQ_pays_third h.accounting.X_tail_nonneg
  exact le_trans hthird_tail
    (le_trans hreceipt h.pressureLocalQuadraticFeedsQuadratic)

/--
The same input pays the full channel sum at reduced scale `nu / 3`, using only
nonnegativity of the other named channels.
-/
theorem route1_pressure_small_tent_excess_input_pays_reduced_channel_sum
    (h : Route1PressureSmallQuadraticReducedInput) :
    (h.accounting.nu / 3) * h.accounting.X_tail ≤
      route1ChannelVisibilitySum
        h.accounting.V_T h.accounting.V_Q h.accounting.V_P h.accounting.V_C := by
  have hq :=
    route1_pressure_small_tent_excess_input_pays_quadratic_channel h
  have hsum :
      h.accounting.V_Q ≤
        route1ChannelVisibilitySum
          h.accounting.V_T h.accounting.V_Q h.accounting.V_P h.accounting.V_C := by
    dsimp [route1ChannelVisibilitySum]
    nlinarith [h.accounting.V_T_nonneg, h.accounting.V_P_nonneg,
      h.accounting.V_C_nonneg]
  exact le_trans hq hsum

/--
Clean reduced producer from the pressure-small CKN/tent-excess branch.  This is
the non-tautological route: source accounting plus a local-quadratic receipt
lower bound produces the missing visibility field at scale `nu / 3`.
-/
noncomputable def route1_pressure_small_tent_excess_reduced_producer
    (h : Route1PressureSmallQuadraticReducedInput) :
    Route1ChannelVisibilityProducer where
  rho := h.accounting.rho
  X := h.accounting.X
  S := h.accounting.S
  X_res := h.accounting.X_res
  X_tail := h.accounting.X_tail
  S_res := h.accounting.S_res
  S_tail := h.accounting.S_tail
  V_T := h.accounting.V_T
  V_Q := h.accounting.V_Q
  V_P := h.accounting.V_P
  V_C := h.accounting.V_C
  deltaRes := h.accounting.deltaRes
  kappa := h.accounting.kappa
  nu := h.accounting.nu / 3
  epsTail := h.accounting.epsTail
  tailError := h.accounting.tailError
  X_nonneg := h.accounting.X_nonneg
  X_res_nonneg := h.accounting.X_res_nonneg
  X_tail_nonneg := h.accounting.X_tail_nonneg
  V_T_nonneg := h.accounting.V_T_nonneg
  V_Q_nonneg := h.accounting.V_Q_nonneg
  V_P_nonneg := h.accounting.V_P_nonneg
  V_C_nonneg := h.accounting.V_C_nonneg
  X_split := h.accounting.X_split
  S_split := h.accounting.S_split
  resolvedStrict := h.accounting.resolvedStrict
  channelLossFromChannelSum := h.accounting.channelLossFromChannelSum
  tailErrorSmall := h.accounting.tailErrorSmall
  criticalTailVisibleFromChannelSum :=
    route1_pressure_small_tent_excess_input_pays_reduced_channel_sum h
  deltaRes_pos := h.accounting.deltaRes_pos
  kappa_pos := h.accounting.kappa_pos
  nu_pos := by nlinarith [h.accounting.nu_pos]

/--
Strict route1 source subratio from the clean pressure-small tent-excess input.
No full visibility producer is an input to this theorem.
-/
theorem exists_strict_source_subratio_of_pressure_small_tent_excess_input
    (h : Route1PressureSmallQuadraticReducedInput)
    (h_eps :
      h.accounting.epsTail ≤
        (1 / 2 : Real) *
          min h.accounting.deltaRes
            (h.accounting.kappa * (h.accounting.nu / 3))) :
    ∃ rho' : Real,
      rho' < h.accounting.rho ∧ h.accounting.S ≤ rho' * h.accounting.X :=
  exists_strict_source_subratio_of_Route1ChannelVisibilityProducer
    (route1_pressure_small_tent_excess_reduced_producer h)
    h_eps

/--
Route1 pressure branch payment: either pressure tail mass is visible and pays
through pressure receipts, or pressure is small and the non-pressure channels
pay.  This is the branch interface to attack next in PDE, not a strict-budget
oracle.
-/
inductive Route1PressureBranchChannelPayment
    (h : Route1CriticalTailVisibilityPDEBundle) where
  | pressureVisible
      (hp : Route1PressureVisibilityLowerBoundProducer)
      (hp_obligation : hp.obligation = h.pressureVisibility)
      (hp_tail : hp.X_tail = h.visibilityProducer.X_tail)
      (hnu : h.visibilityProducer.nu ≤ hp.nuP) :
      Route1PressureBranchChannelPayment h
  | pressureSmall
      (hs : Route1PressureSmallChannelHandoff h) :
      Route1PressureBranchChannelPayment h

/-- Either route1 pressure branch payment is sufficient for channel visibility. -/
theorem route1_pressure_branch_pays_channel_visibility
    (h : Route1CriticalTailVisibilityPDEBundle)
    (hb : Route1PressureBranchChannelPayment h) :
    h.visibilityProducer.nu * h.visibilityProducer.X_tail ≤
      route1ChannelVisibilitySum
        h.visibilityProducer.V_T h.visibilityProducer.V_Q
        h.visibilityProducer.V_P h.visibilityProducer.V_C := by
  cases hb with
  | pressureVisible hp hp_obligation hp_tail hnu =>
      exact route1_pressure_lower_bound_pays_channel_visibility
        h hp hp_obligation hp_tail hnu
  | pressureSmall hs =>
      exact route1_pressure_small_handoff_pays_channel_visibility h hs

/--
Bundled scalar consequence: if the three PDE legs have produced a genuine
channel-sum visibility producer with small tail error, the strict route-1
source subratio follows.  The proof intentionally consumes only the channel
producer; the projection theorem above keeps the PDE receipts auditable and
non-tautological.
-/
theorem exists_strict_source_subratio_of_Route1CriticalTailVisibilityPDEBundle
    (h : Route1CriticalTailVisibilityPDEBundle)
    (h_eps :
      h.visibilityProducer.epsTail ≤
        (1 / 2 : Real) *
          min h.visibilityProducer.deltaRes
            (h.visibilityProducer.kappa * h.visibilityProducer.nu)) :
    ∃ rho' : Real,
      rho' < h.visibilityProducer.rho ∧
        h.visibilityProducer.S ≤ rho' * h.visibilityProducer.X :=
  exists_strict_source_subratio_of_Route1ChannelVisibilityProducer
    h.visibilityProducer h_eps

end ZtareProofs
