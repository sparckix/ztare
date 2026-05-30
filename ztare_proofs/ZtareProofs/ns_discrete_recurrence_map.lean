import Mathlib.Tactic
import ZtareProofs.ns_recurrence_hysteresis

namespace ZtareProofs

/-!
`ns_discrete_recurrence_map` names the exact theorem object left by the current
NS branch once the local escape mechanism is accepted but the recurrence
question remains open.

The core object is no longer a single danger-state visit. It is a thresholded
cycle map:

* enter the danger tube below some `ε_in`,
* exit above some `ε_out`,
* complete a full reset / return cycle,
* compare the outgoing peak intensity to the incoming one.

The theorems below do not prove Navier-Stokes satisfies any premise. They
formalize the minimal dynamical-map statements needed for either:

* anti-blowup by contractive recurrence, or
* oscillatory / Zeno-style recurrence remaining live.
-/

/--
Abstract recurrence map for cycle-to-cycle peak enstrophy transfer.

`Φ E` is the peak enstrophy after one full danger+reset cycle starting from
peak enstrophy `E`.
-/
def CycleMap := Real → Real

/--
Danger / reset thresholds for a full cycle.

`epsIn` is the entry threshold for the danger tube and `epsOut` is the exit
threshold used to certify that a genuine reset occurred before re-entry.
-/
structure CycleThresholds where
  epsIn : Real
  epsOut : Real
  hsep : epsIn < epsOut

/--
Abstract cycle witness.

This is intentionally skeletal: a "cycle" here means a contiguous excursion
that starts on danger entry, exits the danger tube, and later returns. The
numerical branch is no longer resolving this object directly at high fidelity,
so the formal stack isolates only the load-bearing scalars.
-/
structure CycleWitness where
  entryPeak : Real
  exitPeak : Real
  returnPeak : Real
  dangerBudget : Real
  resetBudget : Real
  cycleTime : Real
  hEntryNonneg : 0 ≤ entryPeak
  hExitNonneg : 0 ≤ exitPeak
  hReturnNonneg : 0 ≤ returnPeak
  hTimeNonneg : 0 ≤ cycleTime

/--
Net cycle budget relative to the incoming peak enstrophy.

This is the discrete object the current NS branch has reached: the numerical
program no longer resolves the recurrence reliably, so the theorem target is
the sign and asymptotic behavior of `Φ E - E`.
-/
def cycleProfit (Φ : CycleMap) (E : Real) : Real :=
  Φ E - E

/--
Abstract danger-phase gain.

`G E` is the positive carry harvested while the cycle remains inside the danger
tube.
-/
def cycleGain := Real → Real

/--
Abstract reset / exhaust loss.

`L E` is the tax paid during ejection, reset, and re-arming after the cycle
leaves the danger tube.
-/
def cycleLoss := Real → Real

/--
Canonical gain/loss realization of the recurrence map:

  Φ(E) = E + G(E) - L(E).
-/
def recurrenceFromGainLoss (G L : Real → Real) : CycleMap :=
  fun E => E + G E - L E

/--
Cycle multiplier relative to the incoming peak enstrophy.

This is the multiplicative version of `cycleProfit`. It is only meaningful when
`E > 0`.
-/
noncomputable def cycleMultiplier (Φ : CycleMap) (E : Real) : Real :=
  Φ E / E

/--
Profit of an observed / abstract cycle witness from its budget decomposition.
-/
def witnessProfit (C : CycleWitness) : Real :=
  C.dangerBudget + C.resetBudget

/--
Multiplicity form of the witness map.
-/
noncomputable def witnessMultiplier (C : CycleWitness) : Real :=
  C.returnPeak / C.entryPeak

/--
Contractive above threshold: beyond some critical intensity `E*`, every full
cycle reduces peak enstrophy.
-/
def contractiveAbove (Φ : CycleMap) (EStar : Real) : Prop :=
  ∀ ⦃E : Real⦄, EStar ≤ E → Φ E < E

/--
Non-expanding above threshold: beyond `E*`, cycles do not increase peak
enstrophy.
-/
def nonexpandingAbove (Φ : CycleMap) (EStar : Real) : Prop :=
  ∀ ⦃E : Real⦄, EStar ≤ E → Φ E ≤ E

/--
Uniformly expanding with multiplier `M`: each cycle amplifies peak enstrophy by
at least `M`.
-/
def expandingBy (Φ : CycleMap) (M : Real) : Prop :=
  ∀ ⦃E : Real⦄, 0 ≤ E → M * E ≤ Φ E

/--
Strict positive-carry recurrence above threshold: beyond `E*`, each full cycle
increases peak enstrophy by at least a fixed additive margin `δ`.
-/
def profitableAbove (Φ : CycleMap) (EStar δ : Real) : Prop :=
  ∀ ⦃E : Real⦄, EStar ≤ E → E + δ ≤ Φ E

/--
Geometrically shrinking cycle durations.

This is the abstract time-side premise needed by any Zeno-style recurrence
story. It is kept separate from expansion so the theorem burden cannot smuggle
finite-time recurrence in for free.
-/
def durationsShrinkBy (τ : Nat → Real) (ρ : Real) : Prop :=
  0 ≤ ρ ∧ ρ < 1 ∧ ∀ n : Nat, 0 ≤ τ n ∧ τ (n + 1) ≤ ρ * τ n

/--
If the recurrence map is contractive above threshold, then its cycle profit is
strictly negative there.
-/
theorem cycle_profit_negative_of_contractiveAbove
    {Φ : CycleMap} {EStar E : Real}
    (hcontract : contractiveAbove Φ EStar)
    (hE : EStar ≤ E) :
    cycleProfit Φ E < 0 := by
  unfold cycleProfit
  have hlt : Φ E < E := hcontract hE
  linarith

/--
If the recurrence map is non-expanding above threshold, then its cycle profit
is non-positive there.
-/
theorem cycle_profit_nonpos_of_nonexpandingAbove
    {Φ : CycleMap} {EStar E : Real}
    (hnonexp : nonexpandingAbove Φ EStar)
    (hE : EStar ≤ E) :
    cycleProfit Φ E ≤ 0 := by
  unfold cycleProfit
  have hle : Φ E ≤ E := hnonexp hE
  linarith

/--
If the recurrence map is profitable above threshold, then its cycle profit is
uniformly bounded below by `δ`.
-/
theorem cycle_profit_lower_bound_of_profitableAbove
    {Φ : CycleMap} {EStar δ E : Real}
    (hprofit : profitableAbove Φ EStar δ)
    (hE : EStar ≤ E) :
    δ ≤ cycleProfit Φ E := by
  unfold cycleProfit
  have hle : E + δ ≤ Φ E := hprofit hE
  linarith

/--
If the recurrence map expands by a multiplier `M > 1`, then every nonnegative
cycle profit is strictly positive.
-/
theorem cycle_profit_positive_of_expandingBy
    {Φ : CycleMap} {M E : Real}
    (hexp : expandingBy Φ M)
    (hM : 1 < M)
    (hE : 0 < E) :
    0 < cycleProfit Φ E := by
  unfold cycleProfit
  have hmap : M * E ≤ Φ E := hexp (le_of_lt hE)
  have hstrict : E < M * E := by
    nlinarith
  linarith

/--
If the recurrence map expands by multiplier `M > 1`, then its cycle multiplier
is bounded below by `M`.
-/
theorem cycle_multiplier_lower_bound_of_expandingBy
    {Φ : CycleMap} {M E : Real}
    (hexp : expandingBy Φ M)
    (hE : 0 < E) :
    M ≤ cycleMultiplier Φ E := by
  unfold cycleMultiplier
  have hmap : M * E ≤ Φ E := hexp (le_of_lt hE)
  have hdiv : M * E / E ≤ Φ E / E := by
    exact div_le_div_of_nonneg_right hmap (le_of_lt hE)
  have hleft : M * E / E = M := by
    field_simp [hE.ne']
  simpa [hleft] using hdiv

/--
If an abstract witness returns below its entry peak, then its multiplier is
strictly contractive.
-/
theorem witness_multiplier_lt_one_of_return_lt_entry
    {C : CycleWitness}
    (hEntryPos : 0 < C.entryPeak)
    (hret : C.returnPeak < C.entryPeak) :
    witnessMultiplier C < 1 := by
  unfold witnessMultiplier
  exact (div_lt_one hEntryPos).2 hret

/--
If an abstract witness returns above its entry peak, then its multiplier is
strictly expanding.
-/
theorem witness_multiplier_gt_one_of_return_gt_entry
    {C : CycleWitness}
    (hEntryPos : 0 < C.entryPeak)
    (hret : C.entryPeak < C.returnPeak) :
    1 < witnessMultiplier C := by
  unfold witnessMultiplier
  exact (one_lt_div hEntryPos).2 hret

/--
Budget decomposition for a cycle witness.
-/
theorem witness_profit_decomp
    {C : CycleWitness} :
    witnessProfit C = C.dangerBudget + C.resetBudget := by
  rfl

/--
The recurrence map generated by explicit gain/loss channels has cycle profit
equal to `G(E) - L(E)`.
-/
theorem cycle_profit_of_gain_loss
    {G L : Real → Real} {E : Real} :
    cycleProfit (recurrenceFromGainLoss G L) E = G E - L E := by
  unfold cycleProfit recurrenceFromGainLoss
  ring

/--
Exhaust-horizon premise: beyond some critical intensity `E*`, the reset tax
strictly dominates the danger-phase gain.
-/
def exhaustHorizon (G L : Real → Real) (EStar : Real) : Prop :=
  ∀ ⦃E : Real⦄, EStar ≤ E → G E < L E

/--
Weak exhaust horizon: above `E*`, the reset tax is at least as large as the
danger-phase gain.
-/
def weakExhaustHorizon (G L : Real → Real) (EStar : Real) : Prop :=
  ∀ ⦃E : Real⦄, EStar ≤ E → G E ≤ L E

/--
If the reset tax strictly exceeds the gain above threshold, then the induced
recurrence map is contractive above that threshold.
-/
theorem contractive_of_exhaustHorizon
    {G L : Real → Real} {EStar : Real}
    (hexhaust : exhaustHorizon G L EStar) :
    contractiveAbove (recurrenceFromGainLoss G L) EStar := by
  intro E hE
  unfold recurrenceFromGainLoss
  have hgl : G E < L E := hexhaust hE
  linarith

/--
If the reset tax weakly dominates the gain above threshold, then the induced
recurrence map is non-expanding above that threshold.
-/
theorem nonexpanding_of_weakExhaustHorizon
    {G L : Real → Real} {EStar : Real}
    (hexhaust : weakExhaustHorizon G L EStar) :
    nonexpandingAbove (recurrenceFromGainLoss G L) EStar := by
  intro E hE
  unfold recurrenceFromGainLoss
  have hgl : G E ≤ L E := hexhaust hE
  linarith

/--
The exact regularity target shape for the current NS branch:
to turn local centrifugal eviction into an anti-blowup theorem, it would be
enough to prove that the discrete recurrence map becomes non-expanding above a
critical threshold.
-/
theorem regularity_target_shape
    {Φ : CycleMap} {EStar : Real}
    (h : nonexpandingAbove Φ EStar) :
    nonexpandingAbove Φ EStar := by
  exact h

/--
Stronger regularity target shape:
eventual strict contraction of the recurrence map.
-/
theorem strict_regularity_target_shape
    {Φ : CycleMap} {EStar : Real}
    (h : contractiveAbove Φ EStar) :
    contractiveAbove Φ EStar := by
  exact h

/--
The exact oscillatory-blowup target shape:
to keep the ratchet alive, one would need both an expanding recurrence map and
an independent finite-total-time mechanism for the cycle durations.

This theorem does not prove that such a mechanism exists; it just names the
second theorem obligation explicitly so the branch cannot smuggle recurrence in
for free.
-/
theorem zeno_blowup_target_shape
    {Φ : CycleMap} {M : Real}
    (h : expandingBy Φ M) :
    expandingBy Φ M := by
  exact h

/--
Additive positive-carry version of the recurrence target.
-/
theorem profitable_recurrence_target_shape
    {Φ : CycleMap} {EStar δ : Real}
    (h : profitableAbove Φ EStar δ) :
    profitableAbove Φ EStar δ := by
  exact h

/--
Time-side target shape for any Zeno-style recurrence claim.
-/
theorem zeno_time_target_shape
    {τ : Nat → Real} {ρ : Real}
    (h : durationsShrinkBy τ ρ) :
    durationsShrinkBy τ ρ := by
  exact h

end ZtareProofs
