import Mathlib.Tactic
import ZtareProofs.ns_discrete_recurrence_map
import ZtareProofs.ns_interior_renormalization_obligation

namespace ZtareProofs

/-!
Phase 5CG changed the proof-facing object again.

The old branch no longer supports a strong self-similar profile claim on the
available patches. The sharper candidate is:

* radial/coarse concentration can persist;
* spectral exhaust can continue;
* angular/vector organization can scramble;
* coherent stretching may therefore be depleted before a danger cycle
  consolidates.

This file is a theorem cage, not an NS proof. It connects the new empirical
language to the existing recurrence-map spine.
-/

/-- A coarse transition summary for one interior-renormalized local patch. -/
structure CoherentStretchSample where
  time : Real
  shellCentroid : Real
  radialDrift : Real
  angularAnisotropy : Real
  vectorAnisotropy : Real
  coherentStretch : Real

/-- A finite sampled sequence of coherent-stretch summaries. -/
def CoherentStretchSeq := Nat → CoherentStretchSample

/-- The high-k exhaust proxy keeps moving outward across a transition. -/
def spectralExhaustContinues
    (S : CoherentStretchSeq) (i j : Nat) (σ : Real) : Prop :=
  σ ≤ (S j).shellCentroid - (S i).shellCentroid

/-- Angular and vector anisotropy both drop by declared margins. -/
def angularVectorScrambling
    (S : CoherentStretchSeq) (i j : Nat) (α β : Real) : Prop :=
  (S j).angularAnisotropy ≤ (S i).angularAnisotropy - α ∧
    (S j).vectorAnisotropy ≤ (S i).vectorAnisotropy - β

/-- Coarse radial shape remains controlled while directional organization scrambles. -/
def radialConcentrationWithScramble
    (S : CoherentStretchSeq) (i j : Nat) (κ α β σ : Real) : Prop :=
  (S j).radialDrift ≤ κ ∧
    spectralExhaustContinues S i j σ ∧
    angularVectorScrambling S i j α β

/--
Coherent-stretch depletion premise.

This is the theorem-shaped bridge missing after Phase 5CG: convert observed
angular/vector scrambling into an upper bound on the coherent stretching
available to the next danger cycle.
-/
def coherentStretchDepleted
    (S : CoherentStretchSeq) (_i j : Nat) (cap : Real) : Prop :=
  (S j).coherentStretch ≤ cap

/--
Candidate Phase 5CG proxy suggested by the r64 backtest:
discount coherent stretch by the active exhaust scale.
-/
noncomputable def exhaustDiscountedCoherentStretch
    (s : CoherentStretchSample) : Real :=
  s.coherentStretch / max s.shellCentroid 1

/--
Exhaust-discounted depletion is weaker than raw coherent-stretch depletion and
matches the surviving empirical proxy candidate from the full r64 replay.
-/
def exhaustDiscountedDepleted
    (S : CoherentStretchSeq) (_i j : Nat) (cap : Real) : Prop :=
  exhaustDiscountedCoherentStretch (S j) ≤ cap

/--
The depletion horizon is just the recurrence exhaust horizon expressed in the
new mechanism language: after coherent stretching is depleted, reset/exhaust
loss strictly dominates danger gain.
-/
def coherentStretchDepletionHorizon
    (G L : cycleGain) (EStar : Real) : Prop :=
  exhaustHorizon G L EStar

/--
If the coherent-stretch depletion horizon is proved from the PDE estimates,
the danger-cycle recurrence is contractive above threshold.
-/
theorem contractive_of_coherentStretchDepletionHorizon
    {G L : cycleGain} {EStar : Real}
    (h : coherentStretchDepletionHorizon G L EStar) :
    contractiveAbove (recurrenceFromGainLoss G L) EStar := by
  exact contractive_of_exhaustHorizon h

/--
Phase 5CG recurrence/exhaust target.

This names the next discriminator directly: once coherent-stretch depletion is
available, the remaining proof obligation is to show that the gain/loss cycle
map is contractive above a threshold.
-/
def phase5cgRecurrenceExhaustTarget
    (G L : cycleGain) (EStar : Real) : Prop :=
  contractiveAbove (recurrenceFromGainLoss G L) EStar

/--
If the coherent-stretch depletion horizon is established, the Phase 5CG
recurrence/exhaust target is the contractive-above-threshold statement itself.
-/
theorem phase5cg_recurrence_target_of_depletion_horizon
    {G L : cycleGain} {EStar : Real}
    (h : coherentStretchDepletionHorizon G L EStar) :
    phase5cgRecurrenceExhaustTarget G L EStar := by
  exact contractive_of_coherentStretchDepletionHorizon h

/--
Explicit bridge witness for the Phase 5CG recurrence target.

This packages the live object cleanly: the sequence-level mechanism is
observed first, the recurrence horizon is the theorem obligation, and the
contractive target is what remains to be proved.
-/
structure Phase5CGRecurrenceBridge where
  G : cycleGain
  L : cycleLoss
  EStar : Real
  depletion : coherentStretchDepletionHorizon G L EStar

/-- The bridge target is the contractive recurrence bound itself. -/
def phase5cgRecurrenceBridgeTarget (B : Phase5CGRecurrenceBridge) : Prop :=
  phase5cgRecurrenceExhaustTarget B.G B.L B.EStar

/-- Any paid bridge witness immediately discharges the target shape. -/
theorem phase5cg_recurrence_bridge_target_of_witness
    (B : Phase5CGRecurrenceBridge) :
    phase5cgRecurrenceBridgeTarget B := by
  exact phase5cg_recurrence_target_of_depletion_horizon B.depletion

/-!
Observed-signal packaging for the Phase 5CG branch.

This is the direct "what did the replay show?" object: a radial/coarse
concentration transition with angular/vector scrambling, together with the
abstract recurrence witness that is supposed to absorb it.
-/
structure Phase5CGSignalBridge where
  S : CoherentStretchSeq
  R : InteriorRenormSeq
  i : Nat
  j : Nat
  n0 : Nat
  n1 : Nat
  κ : Real
  α : Real
  β : Real
  σ : Real
  cap : Real
  δ : Real
  ε : Real
  η : Real
  ρ : Real
  bridge : Phase5CGRecurrenceBridge
  signal : radialConcentrationWithScramble S i j κ α β σ
  depletion : coherentStretchDepleted S i j cap
  interior : phase5cgInteriorRenormDichotomy R n0 n1 δ ε η ρ

/--
The next proof obligation in signal form:

if the observed Phase 5CG signal can be compressed into a coherent-stretch
depletion witness, then the recurrence bridge target is the right theorem
shape.
-/
def phase5cgSignalToBridgeTarget
    (X : Phase5CGSignalBridge) : Prop :=
  phase5cgRecurrenceBridgeTarget X.bridge

/-- Any packaged signal witness yields the next bridge target statement. -/
theorem phase5cg_signal_to_bridge_target_of_witness
    (X : Phase5CGSignalBridge) :
    phase5cgSignalToBridgeTarget X := by
  exact phase5cg_recurrence_bridge_target_of_witness X.bridge

/--
Phase 5CG left one exact observable gap:

the audits measure shell-centroid advance, radial compactness, angular
anisotropy drop, and vector-orientation drop, but they do not yet prove that
those proxies upper-bound the coherent stretching available to the next cycle.
-/
def scramblingProxyControlsCoherentStretch
    (S : CoherentStretchSeq) (i j : Nat) (α β cap : Real) : Prop :=
  angularVectorScrambling S i j α β → coherentStretchDepleted S i j cap

/--
If the measured scrambling proxies are proved to control coherent stretch,
then any radial/scramble witness upgrades to a depletion witness.
-/
theorem coherent_stretch_depleted_of_scrambling_proxy
    {S : CoherentStretchSeq} {i j : Nat} {α β cap : Real}
    (hproxy : scramblingProxyControlsCoherentStretch S i j α β cap)
    (hscramble : angularVectorScrambling S i j α β) :
    coherentStretchDepleted S i j cap := by
  exact hproxy hscramble

/--
This is the real unpaid bridge after the r64 replay.

Once the measured angular/vector scrambling proxies are shown to control
coherent stretch, the empirical Phase 5CG signal can feed the depletion bridge.
-/
def phase5cgMeasuredProxyGap
    (X : Phase5CGSignalBridge) : Prop :=
  scramblingProxyControlsCoherentStretch X.S X.i X.j X.α X.β X.cap

/--
Closing the measured-proxy gap is sufficient to upgrade the Phase 5CG signal
to an explicit coherent-stretch depletion witness at the observed transition.
-/
theorem signal_bridge_of_measured_proxy_gap
    (X : Phase5CGSignalBridge)
    (hproxy : phase5cgMeasuredProxyGap X) :
    coherentStretchDepleted X.S X.i X.j X.cap := by
  have hscramble : angularVectorScrambling X.S X.i X.j X.α X.β := by
    exact X.signal.2.2
  exact coherent_stretch_depleted_of_scrambling_proxy hproxy hscramble

/--
Refined proxy gap after the r64 backtest.

This is weaker and more faithful to the data: the surviving candidate is not a
raw anisotropy proxy, but an anisotropy proxy discounted by spectral exhaust.
-/
def phase5cgExhaustDiscountedProxyGap
    (S : CoherentStretchSeq) (i j : Nat) (α β cap : Real) : Prop :=
  angularVectorScrambling S i j α β → exhaustDiscountedDepleted S i j cap

/--
Analytic legitimacy of the shell-centroid discount.

This is the next theorem-shaped obligation after the proxy backtest: justify
why shell-centroid growth measures the active exhaust scale strongly enough
that dividing by it represents a genuine reduction in effective coherent
stretch reserve, rather than an empirical fit.
-/
def shellCentroidDiscountLegitimate
    (S : CoherentStretchSeq) (i j : Nat) (μ : Real) : Prop :=
  spectralExhaustContinues S i j μ →
    exhaustDiscountedCoherentStretch (S j) ≤ (S j).coherentStretch

/--
If the shell-centroid discount is analytically legitimate and the
exhaust-discounted proxy gap is paid, then the surviving empirical candidate
does produce a discounted depletion witness.
-/
theorem exhaust_discounted_depleted_of_legitimate_discount
    {S : CoherentStretchSeq} {i j : Nat} {α β cap μ : Real}
    (_hlegit : shellCentroidDiscountLegitimate S i j μ)
    (hproxy : phase5cgExhaustDiscountedProxyGap S i j α β cap)
    (hscramble : angularVectorScrambling S i j α β) :
    exhaustDiscountedDepleted S i j cap := by
  exact hproxy hscramble

/--
This is the precise next bridge target for the NS branch:

1. justify the shell-centroid discount analytically;
2. show the discounted scrambling proxy controls effective coherent stretch;
3. route that discounted depletion into the recurrence/exhaust target.
-/
def phase5cgDiscountedBridgeTarget
    (S : CoherentStretchSeq) (i j : Nat) (α β cap μ : Real) : Prop :=
  shellCentroidDiscountLegitimate S i j μ ∧
    phase5cgExhaustDiscountedProxyGap S i j α β cap

/--
Phase 5CG branch split for the old spike:

* radial concentration plus scrambling,
* coherent-stretch depletion,
* or the earlier interior-renormalization dichotomy.
-/
def phase5cgCoherentStretchDichotomy
    (S : CoherentStretchSeq) (R : InteriorRenormSeq)
    (i j n0 n1 : Nat) (κ α β σ cap δ ε η ρ : Real) : Prop :=
  radialConcentrationWithScramble S i j κ α β σ ∨
    coherentStretchDepleted S i j cap ∨
    phase5cgInteriorRenormDichotomy R n0 n1 δ ε η ρ

theorem phase5cg_dichotomy_of_radial_scramble
    {S : CoherentStretchSeq} {R : InteriorRenormSeq}
    {i j n0 n1 : Nat} {κ α β σ cap δ ε η ρ : Real}
    (h : radialConcentrationWithScramble S i j κ α β σ) :
    phase5cgCoherentStretchDichotomy S R i j n0 n1 κ α β σ cap δ ε η ρ := by
  exact Or.inl h

theorem phase5cg_dichotomy_of_coherent_depletion
    {S : CoherentStretchSeq} {R : InteriorRenormSeq}
    {i j n0 n1 : Nat} {κ α β σ cap δ ε η ρ : Real}
    (h : coherentStretchDepleted S i j cap) :
    phase5cgCoherentStretchDichotomy S R i j n0 n1 κ α β σ cap δ ε η ρ := by
  exact Or.inr (Or.inl h)

theorem phase5cg_dichotomy_of_interior_renorm
    {S : CoherentStretchSeq} {R : InteriorRenormSeq}
    {i j n0 n1 : Nat} {κ α β σ cap δ ε η ρ : Real}
    (h : phase5cgInteriorRenormDichotomy R n0 n1 δ ε η ρ) :
    phase5cgCoherentStretchDichotomy S R i j n0 n1 κ α β σ cap δ ε η ρ := by
  exact Or.inr (Or.inr h)

end ZtareProofs
