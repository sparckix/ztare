import Mathlib.Tactic
import ZtareProofs.ns_gain_tax_tether_scalar

namespace ZtareProofs.NS

noncomputable section

/-!
Track B obligation skeleton for the gain/tax tether.

This file deliberately does not prove Navier-Stokes regularity and is not
imported by the umbrella build. It names the exact proof burden exposed by the
Phase 5E audits:

* bounded Fourier and named packet classes are evidence, not global closure;
* the global theorem needs a Leray-projected vector/tensor statement, not only
  scalar bookkeeping;
* the survival burden is threshold-defect convexity:
  either `gamma ≤ 2/3`, or the exact quartic defect is already at least one
  at the amplitude `sqrt((2/3)/gamma)`;
* pressure-aware matrix intertwiners must be charged by the declared observable
  ledger or excluded by an independent admissibility theorem.
* the strongest route is dual/state-pricing: construct a positive certificate
  that prices the exact quartic ledger for every admissible Leray state. A
  degree-only `q > p` scaling story is not enough, because the quartic survival
  root can leave a nonzero limiting constant and the cross term can move the
  threshold.
* after the finite-support certificates, the remaining wall is not another
  local packet search. It is a concentration-compactness / limit-passage
  theorem: the declared state-price kernel must survive vanishing, dichotomy,
  concentration, null-profile, and cross-profile recombination without changing
  the observable class after the limit.

The only positive theorem below is a projection theorem: if the Track B
analytic obligation is supplied, then a global full-ledger survivor cannot beat
the sharp target. The analytic obligation itself remains open.
-/

/-- Scope of the ledger object. Only `globalAdmissibleField` is allowed to
carry Track B/global-Leray-convexity status. -/
inductive LedgerScope where
  | finiteClass
  | boundedFourierSlab
  | namedPacketClass
  | dyadicLadder
  | globalAdmissibleField
deriving DecidableEq, Repr

/-- Minimal scalar view of a full-ledger block after Leray projection and
normalization `||M(V)||^2 = 1`. -/
structure FullLedgerBlock where
  scope : LedgerScope
  gamma : Real
  cross : Real
  selfTax : Real
  survivalProfit : Real

/-- The sharp wall from the one-background/full-ledger audits. -/
def sharpTarget : Real := (2 : Real) / 3

/-- Which signed observable/certificate class is being used. `perBlockOracle`
is useful as a hostile numerical upper bound, but it is not an admissible
predeclared PDE certificate. -/
inductive ObservableKind where
  | scalar
  | coordinateDiagonal
  | matrixBlock
  | perBlockOracle
deriving DecidableEq, Repr

/-- Declared signed observable/certificate metadata. These flags are not a
proof of admissibility; they name the obligations a Track B theorem must pay. -/
structure SignedObservable where
  kind : ObservableKind
  predeclared : Prop
  independentNormalized : Prop
  psdBallastCharged : Prop
  dampingCharged : Prop
  crossTermCharged : Prop

/-- Matrix intertwiners are admissible only when charged by the full ledger.
Scalar/diagonal observables may have smaller obligations, but a global theorem
cannot silently ignore the matrix-block branch. -/
def MatrixIntertwinerCharged (C : SignedObservable) : Prop :=
  C.kind = ObservableKind.matrixBlock →
    C.psdBallastCharged ∧ C.dampingCharged ∧
      C.independentNormalized ∧ C.crossTermCharged

/-- Declared observable class for Track B. -/
def IsAdmissibleObservable (C : SignedObservable) : Prop :=
  C.kind ≠ ObservableKind.perBlockOracle ∧
    C.predeclared ∧
      MatrixIntertwinerCharged C

/-- Strong global observable receipt.

`IsAdmissibleObservable` is the legacy minimal interface: it blocks
per-block-oracle observables and forces the full charge package only when the
observable is a matrix block.  A global Track B closure should normally use
this stronger predicate, which requires the normalization, damping, and
cross-term charges for every signed observable class, while retaining PSD
ballast as an extra matrix-block burden.

This is an anti-tautology adapter: the signed observable cannot be chosen or
renormalized after seeing the profitable direction. -/
def GlobalSignedObservableFullyCharged (C : SignedObservable) : Prop :=
  C.kind ≠ ObservableKind.perBlockOracle ∧
    C.predeclared ∧
      C.independentNormalized ∧
        C.dampingCharged ∧
          C.crossTermCharged ∧
            (C.kind = ObservableKind.matrixBlock → C.psdBallastCharged)

/-- A fully charged global signed observable satisfies the legacy
admissibility interface. -/
theorem admissible_observable_of_fully_charged
    {C : SignedObservable}
    (h : GlobalSignedObservableFullyCharged C) :
    IsAdmissibleObservable C := by
  rcases h with ⟨hnotOracle, hpre, hnorm, hdamping, hcross, hpsd⟩
  refine ⟨hnotOracle, hpre, ?_⟩
  intro hmatrix
  exact ⟨hpsd hmatrix, hdamping, hnorm, hcross⟩

/-- Matrix-kind admissibility is already the fully charged global observable
interface.

This is the source-facing positive direction of the matrix-observable guard:
the legacy admissibility predicate is weaker in general, but it is equivalent
to full charging once the observable is explicitly a matrix block. -/
theorem fully_charged_observable_of_admissible_matrix
    {C : SignedObservable}
    (hkind : C.kind = ObservableKind.matrixBlock)
    (hC : IsAdmissibleObservable C) :
    GlobalSignedObservableFullyCharged C := by
  rcases hC with ⟨hnotOracle, hpre, hmatrixGate⟩
  rcases hmatrixGate hkind with ⟨hpsd, hdamping, hnorm, hcross⟩
  exact
    ⟨hnotOracle, hpre, hnorm, hdamping, hcross,
      fun _hmatrix => hpsd⟩

/-- Exact falsifier shape for a signed observable that passes only by omitting
generic charges.  This is not a matrix-specific loophole; it blocks scalar or
diagonal observables that were predeclared but not independently normalized,
damped, and cross-term charged before payoff scoring. -/
structure UnderchargedSignedObservable where
  observable : SignedObservable
  non_oracle : observable.kind ≠ ObservableKind.perBlockOracle
  predeclared : observable.predeclared
  missing_generic_charge :
    ¬ (observable.independentNormalized ∧
        observable.dampingCharged ∧
          observable.crossTermCharged)

/-- An undercharged signed observable cannot be promoted to the strong global
observable class. -/
theorem no_fully_charged_observable_of_undercharged
    (F : UnderchargedSignedObservable) :
    ¬ GlobalSignedObservableFullyCharged F.observable := by
  intro h
  rcases h with ⟨_, _, hnorm, hdamping, hcross, _⟩
  exact F.missing_generic_charge ⟨hnorm, hdamping, hcross⟩

/-- The block is in the global admissible-field class, not merely a bounded
or named Fourier class. -/
def IsGlobalTrackBBlock (B : FullLedgerBlock) : Prop :=
  B.scope = LedgerScope.globalAdmissibleField

/-- Exact quartic defect polynomial after normalizing `||M(V)||^2 = 1`. -/
def survivalDefect (B : FullLedgerBlock) (t : Real) : Real :=
  t ^ 2 + 2 * B.cross * t ^ 3 + B.selfTax * t ^ 4

/-- Scalar Phase 5EL gain/tax tether lifted into the Track B block language.

This is only an algebraic adapter.  It says that once the PDE/vector ledger has
proved the cross-aware self-tax allowance at the threshold amplitude, the
existing scalar polynomial lemma supplies the right branch of
`ThresholdDefectConvexity`.  It does not prove the Leray/Sobolev allowance. -/
theorem threshold_defect_convexity_of_scalar_tether_allowance
    (B : FullLedgerBlock)
    (hgamma : sharpTarget < B.gamma)
    (hx :
      0 < Real.sqrt (sharpTarget / B.gamma))
    (hself :
      (1 - (Real.sqrt (sharpTarget / B.gamma)) ^ (2 : Nat) -
            2 * B.cross *
              (Real.sqrt (sharpTarget / B.gamma)) ^ (3 : Nat)) /
          (Real.sqrt (sharpTarget / B.gamma)) ^ (4 : Nat) ≤ B.selfTax) :
    B.gamma ≤ sharpTarget ∨
      (sharpTarget < B.gamma ∧
        1 ≤ survivalDefect B (Real.sqrt (sharpTarget / B.gamma))) := by
  refine Or.inr ⟨hgamma, ?_⟩
  simpa [survivalDefect] using
    ZtareProofs.defect_ge_one_of_self_tax_ge_cross_aware_allowance
      (x := Real.sqrt (sharpTarget / B.gamma))
      (b := B.cross)
      (c := B.selfTax)
      hx
      hself

/-- The Phase 5ES threshold-defect alternative. -/
def ThresholdDefectConvexity (B : FullLedgerBlock) : Prop :=
  B.gamma ≤ sharpTarget ∨
    (sharpTarget < B.gamma ∧
      1 ≤ survivalDefect B (Real.sqrt (sharpTarget / B.gamma)))

/-- No full-ledger survivor above the sharp target. -/
def FullLedgerNoSurvivor (B : FullLedgerBlock) : Prop :=
  B.survivalProfit ≤ sharpTarget

/-- Projection from threshold-defect convexity to the actual survival-profit
cap.

This is deliberately stronger and more structured than a naked function
`ThresholdDefectConvexity B -> FullLedgerNoSurvivor B`: the below-wall branch
and the above-wall/root-defect branch must each cap the same survival-profit
observable that the candidate is trying to promote. -/
structure QuarticSurvivalProjectionReceipt (B : FullLedgerBlock) where
  survival_observable_fixed_before_defect_scoring : Prop
  root_defect_ledger_same_as_survival_observable : Prop
  survival_observable_fixed_before_defect_scoring_proved :
    survival_observable_fixed_before_defect_scoring
  root_defect_ledger_same_as_survival_observable_proved :
    root_defect_ledger_same_as_survival_observable
  below_wall_profit_cap :
    B.gamma ≤ sharpTarget → B.survivalProfit ≤ sharpTarget
  above_wall_defect_profit_cap :
    sharpTarget < B.gamma →
      1 ≤ survivalDefect B (Real.sqrt (sharpTarget / B.gamma)) →
        B.survivalProfit ≤ sharpTarget

/-- Which fixed-ledger guard failed for the quartic survival projection. -/
inductive QuarticSurvivalProjectionGuardBranch where
  | survivalObservable
  | sameLedger
deriving DecidableEq, Repr

/-- Falsifier for a survival projection that does not use the same
predeclared survivor observable and root-defect ledger. -/
structure QuarticSurvivalProjectionGuardFalsifier
    (B : FullLedgerBlock)
    (R : QuarticSurvivalProjectionReceipt B) where
  branch : QuarticSurvivalProjectionGuardBranch
  missing :
    match branch with
    | QuarticSurvivalProjectionGuardBranch.survivalObservable =>
        ¬ R.survival_observable_fixed_before_defect_scoring
    | QuarticSurvivalProjectionGuardBranch.sameLedger =>
        ¬ R.root_defect_ledger_same_as_survival_observable

/-- A valid quartic survival projection receipt excludes guard failures. -/
theorem no_quartic_survival_projection_guard_falsifier
    (B : FullLedgerBlock)
    (R : QuarticSurvivalProjectionReceipt B)
    (F : QuarticSurvivalProjectionGuardFalsifier B R) :
    False := by
  rcases F with ⟨branch, hmissing⟩
  cases branch with
  | survivalObservable =>
      exact hmissing R.survival_observable_fixed_before_defect_scoring_proved
  | sameLedger =>
      exact hmissing R.root_defect_ledger_same_as_survival_observable_proved

/-- Which cap branch failed for the quartic survival projection. -/
inductive QuarticSurvivalProjectionCapBranch where
  | belowWall
  | aboveWallDefect
deriving DecidableEq, Repr

/-- Falsifier for a survival projection whose branch cap does not actually
bound the promoted survival-profit observable. -/
structure QuarticSurvivalProjectionCapFalsifier
    (B : FullLedgerBlock)
    (R : QuarticSurvivalProjectionReceipt B) where
  branch : QuarticSurvivalProjectionCapBranch
  cap_failure :
    match branch with
    | QuarticSurvivalProjectionCapBranch.belowWall =>
        ∃ _hbelow : B.gamma ≤ sharpTarget,
          sharpTarget < B.survivalProfit
    | QuarticSurvivalProjectionCapBranch.aboveWallDefect =>
        ∃ _hgt : sharpTarget < B.gamma,
          ∃ _hdefect :
            1 ≤ survivalDefect B (Real.sqrt (sharpTarget / B.gamma)),
              sharpTarget < B.survivalProfit

/-- A valid quartic survival projection receipt excludes branch-cap failures.
-/
theorem no_quartic_survival_projection_cap_falsifier
    (B : FullLedgerBlock)
    (R : QuarticSurvivalProjectionReceipt B)
    (F : QuarticSurvivalProjectionCapFalsifier B R) :
    False := by
  rcases F with ⟨branch, hfailure⟩
  cases branch with
  | belowWall =>
      rcases hfailure with ⟨hbelow, hsurvivor⟩
      exact not_lt_of_ge (R.below_wall_profit_cap hbelow) hsurvivor
  | aboveWallDefect =>
      rcases hfailure with ⟨hgt, hdefect, hsurvivor⟩
      exact not_lt_of_ge
        (R.above_wall_defect_profit_cap hgt hdefect)
        hsurvivor

/-- A raw missing source guard is exactly a quartic projection guard
falsifier.

This keeps the "fixed survival observable" and "same root-defect ledger"
guards load-bearing instead of allowing a closure attempt to mention them only
as inert receipt fields. -/
theorem nonempty_quartic_survival_projection_guard_falsifier_of_missing_source_guard
    (B : FullLedgerBlock)
    (R : QuarticSurvivalProjectionReceipt B)
    (hmissing :
      ¬ R.survival_observable_fixed_before_defect_scoring ∨
        ¬ R.root_defect_ledger_same_as_survival_observable) :
    Nonempty (QuarticSurvivalProjectionGuardFalsifier B R) := by
  rcases hmissing with hsurvival | hledger
  · exact
      ⟨⟨QuarticSurvivalProjectionGuardBranch.survivalObservable,
        hsurvival⟩⟩
  · exact
      ⟨⟨QuarticSurvivalProjectionGuardBranch.sameLedger,
        hledger⟩⟩

/-- If threshold defect holds but a survivor beats the target, the failure is
localized to one of the quartic projection cap branches. -/
theorem nonempty_quartic_survival_projection_cap_falsifier_of_threshold_defect_and_survivor
    (B : FullLedgerBlock)
    (R : QuarticSurvivalProjectionReceipt B)
    (h : ThresholdDefectConvexity B)
    (hsurvivor : sharpTarget < B.survivalProfit) :
    Nonempty (QuarticSurvivalProjectionCapFalsifier B R) := by
  rcases h with hbelow | habove
  · exact
      ⟨⟨QuarticSurvivalProjectionCapBranch.belowWall,
        ⟨hbelow, hsurvivor⟩⟩⟩
  · exact
      ⟨⟨QuarticSurvivalProjectionCapBranch.aboveWallDefect,
        ⟨habove.1, habove.2, hsurvivor⟩⟩⟩

/-- A structured quartic survival projection receipt supplies the familiar
no-survivor conclusion from threshold-defect convexity. -/
theorem full_ledger_no_survivor_of_quartic_survival_projection
    (B : FullLedgerBlock)
    (R : QuarticSurvivalProjectionReceipt B)
    (h : ThresholdDefectConvexity B) :
    FullLedgerNoSurvivor B := by
  unfold FullLedgerNoSurvivor
  rcases h with hbelow | habove
  · exact R.below_wall_profit_cap hbelow
  · exact R.above_wall_defect_profit_cap habove.1 habove.2

/-- Adapter for older proof-spine lemmas that still accept a quartic
no-survivor kernel.  New closure-facing structures should carry
`QuarticSurvivalProjectionReceipt` only for the block being promoted; this
adapter prevents duplication while older lower-level route lemmas remain
reusable.  On the full unconstrained `FullLedgerBlock` type the family premise
is intentionally too strong; see
`no_unrestricted_quartic_survival_projection_family`. -/
theorem quartic_no_survivor_kernel_of_survival_projection
    (R : ∀ B : FullLedgerBlock, QuarticSurvivalProjectionReceipt B) :
    ∀ B : FullLedgerBlock,
      ThresholdDefectConvexity B → FullLedgerNoSurvivor B := by
  intro B h
  exact full_ledger_no_survivor_of_quartic_survival_projection B (R B) h

/-- Amplitude-level survival projection receipt.

This is the scalar mechanism behind the quartic survival projection: the
candidate survivor has a predeclared amplitude square, its payoff is bounded by
`gamma * ampSq`, and the above-wall/root-defect branch forces that amplitude
under the Track B threshold `sharpTarget / gamma`.  The below-wall branch uses
the normalized unit-amplitude cap. -/
structure QuarticSurvivalAmplitudeProjectionReceipt
    (B : FullLedgerBlock) where
  survival_observable_fixed_before_defect_scoring : Prop
  root_defect_ledger_same_as_survival_observable : Prop
  survival_observable_fixed_before_defect_scoring_proved :
    survival_observable_fixed_before_defect_scoring
  root_defect_ledger_same_as_survival_observable_proved :
    root_defect_ledger_same_as_survival_observable
  ampSq : Real
  gamma_nonnegative : 0 ≤ B.gamma
  amp_sq_nonnegative : 0 ≤ ampSq
  amp_sq_le_one :
    ampSq ≤ 1
  survival_profit_le_gain_at_amp :
    B.survivalProfit ≤ B.gamma * ampSq
  above_wall_amp_sq_le_threshold :
    sharpTarget < B.gamma →
      1 ≤ survivalDefect B (Real.sqrt (sharpTarget / B.gamma)) →
        ampSq ≤ sharpTarget / B.gamma

/-- Source receipt for the scalar amplitude projection at the Track B
threshold root.

This is a narrower input than `QuarticSurvivalAmplitudeProjectionReceipt`:
the above-wall field is paid by proving the amplitude square is below the
actual threshold-root square
`(sqrt (sharpTarget / gamma))^2`.  Lean then converts that root statement into
`ampSq <= sharpTarget / gamma`.  The survival-profit gain cap and the fixed
observable/root-ledger guards remain explicit source facts; no no-survivor
conclusion is assumed. -/
structure QuarticSurvivalThresholdRootAmplitudeSource
    (B : FullLedgerBlock) where
  survival_observable_fixed_before_defect_scoring : Prop
  root_defect_ledger_same_as_survival_observable : Prop
  survival_observable_fixed_before_defect_scoring_paid :
    survival_observable_fixed_before_defect_scoring
  root_defect_ledger_same_as_survival_observable_paid :
    root_defect_ledger_same_as_survival_observable
  ampSq : Real
  gamma_nonnegative : 0 ≤ B.gamma
  amp_sq_nonnegative : 0 ≤ ampSq
  amp_sq_le_one :
    ampSq ≤ 1
  survival_profit_le_gain_at_amp :
    B.survivalProfit ≤ B.gamma * ampSq
  amp_sq_le_threshold_root :
    sharpTarget < B.gamma →
      ampSq ≤ (Real.sqrt (sharpTarget / B.gamma)) ^ (2 : Nat)

/-- A threshold-root amplitude source supplies the above-wall amplitude
threshold field required by `QuarticSurvivalAmplitudeProjectionReceipt`. -/
theorem threshold_root_source_above_wall_amp_sq_le_threshold
    (B : FullLedgerBlock)
    (S : QuarticSurvivalThresholdRootAmplitudeSource B)
    (hgt : sharpTarget < B.gamma) :
    S.ampSq ≤ sharpTarget / B.gamma := by
  have htarget_pos : 0 < sharpTarget := by
    norm_num [sharpTarget]
  have hgamma_pos : 0 < B.gamma := lt_trans htarget_pos hgt
  have hratio_nonnegative : 0 ≤ sharpTarget / B.gamma :=
    le_of_lt (div_pos htarget_pos hgamma_pos)
  have hroot_sq :
      (Real.sqrt (sharpTarget / B.gamma)) ^ (2 : Nat) =
        sharpTarget / B.gamma := by
    simpa using Real.sq_sqrt hratio_nonnegative
  exact (S.amp_sq_le_threshold_root hgt).trans (le_of_eq hroot_sq)

/-- Track B specialization of the scalar gain-action cap.

If the declared amplitude already has gain action below the sharp wall, Lean
converts that cap into the exact threshold-root square bound used by
`QuarticSurvivalThresholdRootAmplitudeSource`. -/
theorem amp_sq_le_threshold_root_of_gain_action_cap
    (B : FullLedgerBlock)
    {ampSq : Real}
    (hgt : sharpTarget < B.gamma)
    (hcap : B.gamma * ampSq ≤ sharpTarget) :
    ampSq ≤ (Real.sqrt (sharpTarget / B.gamma)) ^ (2 : Nat) := by
  have htarget_pos : 0 < sharpTarget := by
    norm_num [sharpTarget]
  exact
    ZtareProofs.amp_sq_le_sqrt_sq_of_gain_times_amp_sq_le_target
      (gamma := B.gamma)
      (target := sharpTarget)
      (ampSq := ampSq)
      (lt_trans htarget_pos hgt)
      (le_of_lt htarget_pos)
      hcap

/-- Construct the compact amplitude projection receipt from the threshold-root
source receipt.

This is the scalar gap reducer for generated Lipschitz ledgers: once a PDE
or SOS/self-tax branch proves the fixed amplitude gain cap and the
threshold-root amplitude bound for its block, the exact target receipt follows
without adding an opaque projection assumption. -/
def quartic_survival_amplitude_projection_of_threshold_root_source
    (B : FullLedgerBlock)
    (S : QuarticSurvivalThresholdRootAmplitudeSource B) :
    QuarticSurvivalAmplitudeProjectionReceipt B where
  survival_observable_fixed_before_defect_scoring :=
    S.survival_observable_fixed_before_defect_scoring
  root_defect_ledger_same_as_survival_observable :=
    S.root_defect_ledger_same_as_survival_observable
  survival_observable_fixed_before_defect_scoring_proved :=
    S.survival_observable_fixed_before_defect_scoring_paid
  root_defect_ledger_same_as_survival_observable_proved :=
    S.root_defect_ledger_same_as_survival_observable_paid
  ampSq := S.ampSq
  gamma_nonnegative := S.gamma_nonnegative
  amp_sq_nonnegative := S.amp_sq_nonnegative
  amp_sq_le_one := S.amp_sq_le_one
  survival_profit_le_gain_at_amp := S.survival_profit_le_gain_at_amp
  above_wall_amp_sq_le_threshold := by
    intro hgt _hdefect
    exact threshold_root_source_above_wall_amp_sq_le_threshold B S hgt

/-- A threshold-root amplitude source already supplies the generated
gain-at-amplitude cap.

Below the wall this is `ampSq <= 1`; above the wall it is the exact
threshold-root square bound converted through `sqrt(target / gamma)^2`. -/
theorem gain_at_amp_le_target_of_quartic_survival_threshold_root_source
    (B : FullLedgerBlock)
    (S : QuarticSurvivalThresholdRootAmplitudeSource B) :
    B.gamma * S.ampSq ≤ sharpTarget := by
  rcases le_or_gt B.gamma sharpTarget with hbelow | hgt
  · have hgain_le_gamma : B.gamma * S.ampSq ≤ B.gamma :=
      mul_le_of_le_one_right S.gamma_nonnegative S.amp_sq_le_one
    exact hgain_le_gamma.trans hbelow
  · have hamp : S.ampSq ≤ sharpTarget / B.gamma :=
      threshold_root_source_above_wall_amp_sq_le_threshold B S hgt
    have htarget_pos : 0 < sharpTarget := by
      norm_num [sharpTarget]
    have hgamma_pos : 0 < B.gamma := lt_trans htarget_pos hgt
    exact
      ZtareProofs.gain_times_amp_sq_le_target_of_amp_sq_le
        (gamma := B.gamma)
        (target := sharpTarget)
        (ampSq := S.ampSq)
        hgamma_pos
        hamp

/-- Two-index family adapter for generated ledgers.

Downstream profile/Lipschitz code can instantiate `block` with
`fun U n => ((lipschitz_bridge.ledger_of_evolution U).block n)`.  The adapter
keeps this lower module independent of the Lipschitz bridge types while still
presenting the exact `forall U n, QuarticSurvivalAmplitudeProjectionReceipt`
shape that endpoint tooling searches for. -/
def quartic_survival_amplitude_projection_family2_of_threshold_root_sources
    {α : Type*}
    (block : α → ℕ → FullLedgerBlock)
    (S : ∀ U n,
      QuarticSurvivalThresholdRootAmplitudeSource (block U n)) :
    ∀ U n, QuarticSurvivalAmplitudeProjectionReceipt (block U n) := by
  intro U n
  exact
    quartic_survival_amplitude_projection_of_threshold_root_source
      (block U n)
      (S U n)

/-- Source object for the amplitude-level survival projection.

This is the source-facing version future PDE work should instantiate: the
amplitude square must belong to a fully charged signed observable, and the
same observable/defect ledger guards must be paid before the scalar amplitude
inequalities are used.  It is still not a Navier-Stokes estimate; the two
numeric amplitude inequalities remain explicit fields. -/
structure QuarticSurvivalAmplitudeObservableSource
    (B : FullLedgerBlock) where
  observable : SignedObservable
  observable_fully_charged :
    GlobalSignedObservableFullyCharged observable
  survival_observable_fixed_before_defect_scoring : Prop
  survival_observable_fixed_before_defect_scoring_paid :
    survival_observable_fixed_before_defect_scoring
  root_defect_ledger_same_as_survival_observable : Prop
  root_defect_ledger_same_as_survival_observable_paid :
    root_defect_ledger_same_as_survival_observable
  amplitude_observable_matches_survival_profit : Prop
  amplitude_observable_matches_survival_profit_paid :
    amplitude_observable_matches_survival_profit
  ampSq : Real
  gamma_nonnegative : 0 ≤ B.gamma
  amp_sq_nonnegative : 0 ≤ ampSq
  amp_sq_le_one :
    ampSq ≤ 1
  survival_profit_le_gain_at_amp :
    B.survivalProfit ≤ B.gamma * ampSq
  above_wall_amp_sq_le_threshold :
    sharpTarget < B.gamma →
      1 ≤ survivalDefect B (Real.sqrt (sharpTarget / B.gamma)) →
        ampSq ≤ sharpTarget / B.gamma

/-- Generic source binding for a typed payload.

The `source_eq_target` field is the payload identity.  The declaration proof is
kept separate so future PDE receipts can distinguish "this was the same object"
from "this object was fixed before it was used". -/
structure DeclaredSourceBinding (α : Type*) (target : α) where
  source : α
  source_eq_target : source = target
  declared_before_use : Prop
  declared_before_use_paid : declared_before_use

/-- Source binding with an additional no-posthoc-selection guard. -/
structure NonPosthocSourceBinding (α : Type*) (target : α)
    extends DeclaredSourceBinding α target where
  no_posthoc_selection : Prop
  no_posthoc_selection_paid : no_posthoc_selection

/-- Generic hostile branches for a typed declared source binding. -/
inductive DeclaredSourceBindingFalsifier
    {α : Type*} {target : α}
    (S : DeclaredSourceBinding α target) : Prop where
  | sourceMismatch :
      S.source ≠ target →
        DeclaredSourceBindingFalsifier S
  | notDeclaredBeforeUse :
      ¬ S.declared_before_use →
        DeclaredSourceBindingFalsifier S

/-- A typed source binding excludes source mismatch and missing-declaration
branches. -/
theorem no_declared_source_binding_falsifier
    {α : Type*} {target : α}
    (S : DeclaredSourceBinding α target)
    (F : DeclaredSourceBindingFalsifier S) :
    False := by
  cases F with
  | sourceMismatch h =>
      exact h S.source_eq_target
  | notDeclaredBeforeUse h =>
      exact h S.declared_before_use_paid

/-- Generic hostile branches for a no-posthoc typed source binding. -/
inductive NonPosthocSourceBindingFalsifier
    {α : Type*} {target : α}
    (S : NonPosthocSourceBinding α target) : Prop where
  | sourceMismatch :
      S.source ≠ target →
        NonPosthocSourceBindingFalsifier S
  | notDeclaredBeforeUse :
      ¬ S.declared_before_use →
        NonPosthocSourceBindingFalsifier S
  | posthocSelection :
      ¬ S.no_posthoc_selection →
        NonPosthocSourceBindingFalsifier S

/-- A no-posthoc typed source binding excludes mismatch, missing declaration,
and posthoc-selection branches. -/
theorem no_nonposthoc_source_binding_falsifier
    {α : Type*} {target : α}
    (S : NonPosthocSourceBinding α target)
    (F : NonPosthocSourceBindingFalsifier S) :
    False := by
  cases F with
  | sourceMismatch h =>
      exact h S.source_eq_target
  | notDeclaredBeforeUse h =>
      exact h S.declared_before_use_paid
  | posthocSelection h =>
      exact h S.no_posthoc_selection_paid

/-- Typed payload tying an observable to its scalar amplitude. -/
structure ObservableScalarPayload (Observable Scalar : Type*) where
  observable : Observable
  scalar : Scalar

/-- Typed payload tying a ledger block to its observable channel. -/
structure BlockObservablePayload (Block Observable : Type*) where
  block : Block
  observable : Observable

/-- Typed payload tying a block, observable, and scalar amplitude together. -/
structure BlockObservableScalarPayload (Block Observable Scalar : Type*) where
  block : Block
  observable : Observable
  scalar : Scalar

/-- Structured receipt that the signed observable and amplitude square are
actually the source of the block's survival-profit channel.

This is a typed receipt tied to `(B, C, ampSq)`, with downstream source fields
carrying `Nonempty` of this receipt instead of an uninterpreted free metadata
flag.  It still does not prove the scalar amplitude inequalities; those remain
fields of `QuarticSurvivalAmplitudeProjectionReceipt`. -/
structure QuarticSurvivalAmplitudeObservableMatchReceipt
    (B : FullLedgerBlock) (C : SignedObservable) (ampSq : Real) where
  observable_predeclared_before_payoff :
    C.predeclared
  observable_not_per_block_oracle :
    C.kind ≠ ObservableKind.perBlockOracle
  amplitude_square_declared_by_observable : Prop
  amplitude_square_declared_by_observable_paid :
    amplitude_square_declared_by_observable
  survival_profit_channel_declared_before_payoff : Prop
  survival_profit_channel_declared_before_payoff_paid :
    survival_profit_channel_declared_before_payoff
  same_block_survival_profit_channel : Prop
  same_block_survival_profit_channel_paid :
    same_block_survival_profit_channel
  same_observable_amplitude_square : Prop
  same_observable_amplitude_square_paid :
    same_observable_amplitude_square
  gain_bound_uses_same_observable : Prop
  gain_bound_uses_same_observable_paid :
    gain_bound_uses_same_observable

/-- Hostile failure modes for the structured survival-profit observable match. -/
inductive QuarticSurvivalAmplitudeObservableMatchFalsifier
    {B : FullLedgerBlock} {C : SignedObservable} {ampSq : Real}
    (M : QuarticSurvivalAmplitudeObservableMatchReceipt B C ampSq) : Prop where
  | notPredeclared :
      ¬ C.predeclared →
        QuarticSurvivalAmplitudeObservableMatchFalsifier M
  | perBlockOracle :
      C.kind = ObservableKind.perBlockOracle →
        QuarticSurvivalAmplitudeObservableMatchFalsifier M
  | amplitudeSquareNotDeclaredByObservable :
      ¬ M.amplitude_square_declared_by_observable →
        QuarticSurvivalAmplitudeObservableMatchFalsifier M
  | survivalProfitChannelNotPredeclared :
      ¬ M.survival_profit_channel_declared_before_payoff →
        QuarticSurvivalAmplitudeObservableMatchFalsifier M
  | wrongSurvivalProfitChannel :
      ¬ M.same_block_survival_profit_channel →
        QuarticSurvivalAmplitudeObservableMatchFalsifier M
  | wrongAmplitudeSquare :
      ¬ M.same_observable_amplitude_square →
        QuarticSurvivalAmplitudeObservableMatchFalsifier M
  | detachedGainBound :
      ¬ M.gain_bound_uses_same_observable →
        QuarticSurvivalAmplitudeObservableMatchFalsifier M

/-- A structured observable/source match excludes the named fake-match
branches. -/
theorem no_quartic_survival_amplitude_observable_match_falsifier
    {B : FullLedgerBlock} {C : SignedObservable} {ampSq : Real}
    (M : QuarticSurvivalAmplitudeObservableMatchReceipt B C ampSq)
    (F : QuarticSurvivalAmplitudeObservableMatchFalsifier M) :
    False := by
  cases F with
  | notPredeclared h =>
      exact h M.observable_predeclared_before_payoff
  | perBlockOracle h =>
      exact M.observable_not_per_block_oracle h
  | amplitudeSquareNotDeclaredByObservable h =>
      exact h M.amplitude_square_declared_by_observable_paid
  | survivalProfitChannelNotPredeclared h =>
      exact h M.survival_profit_channel_declared_before_payoff_paid
  | wrongSurvivalProfitChannel h =>
      exact h M.same_block_survival_profit_channel_paid
  | wrongAmplitudeSquare h =>
      exact h M.same_observable_amplitude_square_paid
  | detachedGainBound h =>
      exact h M.gain_bound_uses_same_observable_paid

/-- Build the survival-amplitude observable/source match from a fully charged
observable plus explicit same-source provenance facts.

This is not an analytic estimate and it does not invent the provenance Props:
the caller still has to pay the amplitude-square, survival-profit-channel, and
gain-bound same-source facts. The fully charged observable supplies only the
predeclaration and non-oracle obligations. -/
def quartic_survival_amplitude_observable_match_receipt_of_fully_charged
    {B : FullLedgerBlock} {C : SignedObservable} {ampSq : Real}
    (hC : GlobalSignedObservableFullyCharged C)
    (amplitude_square_declared_by_observable : Prop)
    (amplitude_square_declared_by_observable_paid :
      amplitude_square_declared_by_observable)
    (survival_profit_channel_declared_before_payoff : Prop)
    (survival_profit_channel_declared_before_payoff_paid :
      survival_profit_channel_declared_before_payoff)
    (same_block_survival_profit_channel : Prop)
    (same_block_survival_profit_channel_paid :
      same_block_survival_profit_channel)
    (same_observable_amplitude_square : Prop)
    (same_observable_amplitude_square_paid :
      same_observable_amplitude_square)
    (gain_bound_uses_same_observable : Prop)
    (gain_bound_uses_same_observable_paid :
      gain_bound_uses_same_observable) :
    QuarticSurvivalAmplitudeObservableMatchReceipt B C ampSq := by
  rcases hC with ⟨hnotOracle, hpre, _, _, _, _⟩
  exact
    { observable_predeclared_before_payoff := hpre
      observable_not_per_block_oracle := hnotOracle
      amplitude_square_declared_by_observable :=
        amplitude_square_declared_by_observable
      amplitude_square_declared_by_observable_paid :=
        amplitude_square_declared_by_observable_paid
      survival_profit_channel_declared_before_payoff :=
        survival_profit_channel_declared_before_payoff
      survival_profit_channel_declared_before_payoff_paid :=
        survival_profit_channel_declared_before_payoff_paid
      same_block_survival_profit_channel :=
        same_block_survival_profit_channel
      same_block_survival_profit_channel_paid :=
        same_block_survival_profit_channel_paid
      same_observable_amplitude_square := same_observable_amplitude_square
      same_observable_amplitude_square_paid :=
        same_observable_amplitude_square_paid
      gain_bound_uses_same_observable := gain_bound_uses_same_observable
      gain_bound_uses_same_observable_paid :=
        gain_bound_uses_same_observable_paid }

/-- Build the survival-amplitude observable/source match from typed source
bindings.

This adapter is stricter than the legacy Prop-pair constructor: the same-source
guards are the equality fields of typed payload bindings, not arbitrary
standalone propositions.  The declaration/no-posthoc content still has to come
from the upstream PDE source object. -/
def quartic_survival_amplitude_observable_match_receipt_of_source_bindings
    {B : FullLedgerBlock} {C : SignedObservable} {ampSq : Real}
    (hC : GlobalSignedObservableFullyCharged C)
    (amplitude_square_source :
      DeclaredSourceBinding
        (ObservableScalarPayload SignedObservable Real)
        { observable := C, scalar := ampSq })
    (survival_profit_channel_source :
      DeclaredSourceBinding
        (BlockObservablePayload FullLedgerBlock SignedObservable)
        { block := B, observable := C })
    (gain_bound_source :
      DeclaredSourceBinding
        (BlockObservableScalarPayload FullLedgerBlock SignedObservable Real)
        { block := B, observable := C, scalar := ampSq }) :
    QuarticSurvivalAmplitudeObservableMatchReceipt B C ampSq :=
  quartic_survival_amplitude_observable_match_receipt_of_fully_charged
    hC
    amplitude_square_source.declared_before_use
    amplitude_square_source.declared_before_use_paid
    survival_profit_channel_source.declared_before_use
    survival_profit_channel_source.declared_before_use_paid
    (survival_profit_channel_source.source =
      { block := B, observable := C })
    survival_profit_channel_source.source_eq_target
    (amplitude_square_source.source =
      { observable := C, scalar := ampSq })
    amplitude_square_source.source_eq_target
    (gain_bound_source.source =
      { block := B, observable := C, scalar := ampSq })
    gain_bound_source.source_eq_target

/-- Structured receipt that the threshold-root defect ledger is the same
predeclared observable channel as the survival amplitude.

This is deliberately not an estimate.  It is the source/provenance half of the
threshold-root amplitude source: future SOS, root-coercivity, or self-tax
receipts still have to supply the numerical root amplitude inequality, but the
root ledger itself cannot be selected after payoff scoring. -/
structure QuarticSurvivalRootDefectLedgerMatchReceipt
    (B : FullLedgerBlock) (C : SignedObservable) (ampSq : Real) where
  observable_predeclared_before_defect_scoring :
    C.predeclared
  observable_not_per_block_oracle :
    C.kind ≠ ObservableKind.perBlockOracle
  root_defect_block_declared_before_scoring : Prop
  root_defect_block_declared_before_scoring_paid :
    root_defect_block_declared_before_scoring
  root_defect_uses_same_block : Prop
  root_defect_uses_same_block_paid :
    root_defect_uses_same_block
  root_defect_uses_same_observable : Prop
  root_defect_uses_same_observable_paid :
    root_defect_uses_same_observable
  threshold_root_amplitude_declared_before_scoring : Prop
  threshold_root_amplitude_declared_before_scoring_paid :
    threshold_root_amplitude_declared_before_scoring
  threshold_root_uses_same_amplitude_square : Prop
  threshold_root_uses_same_amplitude_square_paid :
    threshold_root_uses_same_amplitude_square
  no_posthoc_root_or_ledger_selection : Prop
  no_posthoc_root_or_ledger_selection_paid :
    no_posthoc_root_or_ledger_selection

/-- Hostile failure modes for the threshold-root ledger provenance receipt. -/
inductive QuarticSurvivalRootDefectLedgerMatchFalsifier
    {B : FullLedgerBlock} {C : SignedObservable} {ampSq : Real}
    (M : QuarticSurvivalRootDefectLedgerMatchReceipt B C ampSq) : Prop where
  | notPredeclared :
      ¬ C.predeclared →
        QuarticSurvivalRootDefectLedgerMatchFalsifier M
  | perBlockOracle :
      C.kind = ObservableKind.perBlockOracle →
        QuarticSurvivalRootDefectLedgerMatchFalsifier M
  | rootBlockNotPredeclared :
      ¬ M.root_defect_block_declared_before_scoring →
        QuarticSurvivalRootDefectLedgerMatchFalsifier M
  | wrongRootBlock :
      ¬ M.root_defect_uses_same_block →
        QuarticSurvivalRootDefectLedgerMatchFalsifier M
  | wrongRootObservable :
      ¬ M.root_defect_uses_same_observable →
        QuarticSurvivalRootDefectLedgerMatchFalsifier M
  | thresholdRootAmplitudePosthoc :
      ¬ M.threshold_root_amplitude_declared_before_scoring →
        QuarticSurvivalRootDefectLedgerMatchFalsifier M
  | wrongThresholdRootAmplitudeSquare :
      ¬ M.threshold_root_uses_same_amplitude_square →
        QuarticSurvivalRootDefectLedgerMatchFalsifier M
  | posthocRootOrLedgerSelection :
      ¬ M.no_posthoc_root_or_ledger_selection →
        QuarticSurvivalRootDefectLedgerMatchFalsifier M

/-- A structured threshold-root ledger match excludes the named fake-match
branches. -/
theorem no_quartic_survival_root_defect_ledger_match_falsifier
    {B : FullLedgerBlock} {C : SignedObservable} {ampSq : Real}
    (M : QuarticSurvivalRootDefectLedgerMatchReceipt B C ampSq)
    (F : QuarticSurvivalRootDefectLedgerMatchFalsifier M) :
    False := by
  cases F with
  | notPredeclared h =>
      exact h M.observable_predeclared_before_defect_scoring
  | perBlockOracle h =>
      exact M.observable_not_per_block_oracle h
  | rootBlockNotPredeclared h =>
      exact h M.root_defect_block_declared_before_scoring_paid
  | wrongRootBlock h =>
      exact h M.root_defect_uses_same_block_paid
  | wrongRootObservable h =>
      exact h M.root_defect_uses_same_observable_paid
  | thresholdRootAmplitudePosthoc h =>
      exact h M.threshold_root_amplitude_declared_before_scoring_paid
  | wrongThresholdRootAmplitudeSquare h =>
      exact h M.threshold_root_uses_same_amplitude_square_paid
  | posthocRootOrLedgerSelection h =>
      exact h M.no_posthoc_root_or_ledger_selection_paid

/-- Build the threshold-root defect-ledger match from a fully charged observable
plus explicit same-source root/provenance facts.

This exposes the remaining source debt honestly: fully charged observables pay
predeclaration/non-oracle, while the root-defect block, observable, threshold
amplitude, and no-posthoc facts remain caller-supplied provenance. -/
def quartic_survival_root_defect_ledger_match_receipt_of_fully_charged
    {B : FullLedgerBlock} {C : SignedObservable} {ampSq : Real}
    (hC : GlobalSignedObservableFullyCharged C)
    (root_defect_block_declared_before_scoring : Prop)
    (root_defect_block_declared_before_scoring_paid :
      root_defect_block_declared_before_scoring)
    (root_defect_uses_same_block : Prop)
    (root_defect_uses_same_block_paid : root_defect_uses_same_block)
    (root_defect_uses_same_observable : Prop)
    (root_defect_uses_same_observable_paid :
      root_defect_uses_same_observable)
    (threshold_root_amplitude_declared_before_scoring : Prop)
    (threshold_root_amplitude_declared_before_scoring_paid :
      threshold_root_amplitude_declared_before_scoring)
    (threshold_root_uses_same_amplitude_square : Prop)
    (threshold_root_uses_same_amplitude_square_paid :
      threshold_root_uses_same_amplitude_square)
    (no_posthoc_root_or_ledger_selection : Prop)
    (no_posthoc_root_or_ledger_selection_paid :
      no_posthoc_root_or_ledger_selection) :
    QuarticSurvivalRootDefectLedgerMatchReceipt B C ampSq := by
  rcases hC with ⟨hnotOracle, hpre, _, _, _, _⟩
  exact
    { observable_predeclared_before_defect_scoring := hpre
      observable_not_per_block_oracle := hnotOracle
      root_defect_block_declared_before_scoring :=
        root_defect_block_declared_before_scoring
      root_defect_block_declared_before_scoring_paid :=
        root_defect_block_declared_before_scoring_paid
      root_defect_uses_same_block := root_defect_uses_same_block
      root_defect_uses_same_block_paid := root_defect_uses_same_block_paid
      root_defect_uses_same_observable := root_defect_uses_same_observable
      root_defect_uses_same_observable_paid :=
        root_defect_uses_same_observable_paid
      threshold_root_amplitude_declared_before_scoring :=
        threshold_root_amplitude_declared_before_scoring
      threshold_root_amplitude_declared_before_scoring_paid :=
        threshold_root_amplitude_declared_before_scoring_paid
      threshold_root_uses_same_amplitude_square :=
        threshold_root_uses_same_amplitude_square
      threshold_root_uses_same_amplitude_square_paid :=
        threshold_root_uses_same_amplitude_square_paid
      no_posthoc_root_or_ledger_selection :=
        no_posthoc_root_or_ledger_selection
      no_posthoc_root_or_ledger_selection_paid :=
        no_posthoc_root_or_ledger_selection_paid }

/-- Build the threshold-root defect-ledger match from typed source bindings.

The block/observable and block/observable/scalar equality claims come from
source payload identities.  The final no-posthoc guard requires both the root
ledger and threshold-root amplitude source to have been selected independently
of the payoff/root scoring. -/
def quartic_survival_root_defect_ledger_match_receipt_of_source_bindings
    {B : FullLedgerBlock} {C : SignedObservable} {ampSq : Real}
    (hC : GlobalSignedObservableFullyCharged C)
    (root_defect_source :
      NonPosthocSourceBinding
        (BlockObservablePayload FullLedgerBlock SignedObservable)
        { block := B, observable := C })
    (threshold_root_amplitude_source :
      NonPosthocSourceBinding
        (BlockObservableScalarPayload FullLedgerBlock SignedObservable Real)
        { block := B, observable := C, scalar := ampSq }) :
    QuarticSurvivalRootDefectLedgerMatchReceipt B C ampSq :=
  quartic_survival_root_defect_ledger_match_receipt_of_fully_charged
    hC
    root_defect_source.declared_before_use
    root_defect_source.declared_before_use_paid
    (root_defect_source.source = { block := B, observable := C })
    root_defect_source.source_eq_target
    (root_defect_source.source = { block := B, observable := C })
    root_defect_source.source_eq_target
    threshold_root_amplitude_source.declared_before_use
    threshold_root_amplitude_source.declared_before_use_paid
    (threshold_root_amplitude_source.source =
      { block := B, observable := C, scalar := ampSq })
    threshold_root_amplitude_source.source_eq_target
    (root_defect_source.no_posthoc_selection ∧
      threshold_root_amplitude_source.no_posthoc_selection)
    ⟨root_defect_source.no_posthoc_selection_paid,
      threshold_root_amplitude_source.no_posthoc_selection_paid⟩

/-- Stronger source receipt for the scalar threshold-root amplitude adapter.

Compared with `QuarticSurvivalThresholdRootAmplitudeSource`, this source has no
free provenance Props for the fixed survivor observable or root-defect ledger:
they are paid by the structured observable-match and root-ledger-match receipts.
The numerical facts remain explicit, especially the root amplitude bound. -/
structure QuarticSurvivalThresholdRootObservableSource
    (B : FullLedgerBlock) where
  observable : SignedObservable
  observable_fully_charged :
    GlobalSignedObservableFullyCharged observable
  ampSq : Real
  observable_match :
    QuarticSurvivalAmplitudeObservableMatchReceipt B observable ampSq
  root_ledger_match :
    QuarticSurvivalRootDefectLedgerMatchReceipt B observable ampSq
  gamma_nonnegative : 0 ≤ B.gamma
  amp_sq_nonnegative : 0 ≤ ampSq
  amp_sq_le_one :
    ampSq ≤ 1
  survival_profit_le_gain_at_amp :
    B.survivalProfit ≤ B.gamma * ampSq
  amp_sq_le_threshold_root :
    sharpTarget < B.gamma →
      ampSq ≤ (Real.sqrt (sharpTarget / B.gamma)) ^ (2 : Nat)

/-- A threshold-root observable source instantiates the narrower scalar
threshold-root source without inventing any guard proof. -/
def quartic_survival_threshold_root_source_of_observable_source
    (B : FullLedgerBlock)
    (S : QuarticSurvivalThresholdRootObservableSource B) :
    QuarticSurvivalThresholdRootAmplitudeSource B where
  survival_observable_fixed_before_defect_scoring :=
    Nonempty
      (QuarticSurvivalAmplitudeObservableMatchReceipt
        B S.observable S.ampSq)
  root_defect_ledger_same_as_survival_observable :=
    Nonempty
      (QuarticSurvivalRootDefectLedgerMatchReceipt
        B S.observable S.ampSq)
  survival_observable_fixed_before_defect_scoring_paid :=
    ⟨S.observable_match⟩
  root_defect_ledger_same_as_survival_observable_paid :=
    ⟨S.root_ledger_match⟩
  ampSq := S.ampSq
  gamma_nonnegative := S.gamma_nonnegative
  amp_sq_nonnegative := S.amp_sq_nonnegative
  amp_sq_le_one := S.amp_sq_le_one
  survival_profit_le_gain_at_amp := S.survival_profit_le_gain_at_amp
  amp_sq_le_threshold_root := S.amp_sq_le_threshold_root

/-- Strong-source adapter directly to the compact amplitude projection. -/
def quartic_survival_amplitude_projection_of_threshold_root_observable_source
    (B : FullLedgerBlock)
    (S : QuarticSurvivalThresholdRootObservableSource B) :
    QuarticSurvivalAmplitudeProjectionReceipt B :=
  quartic_survival_amplitude_projection_of_threshold_root_source
    B
    (quartic_survival_threshold_root_source_of_observable_source B S)

/-- The strong threshold-root source also supplies the source-facing observable
receipt; the above-wall amplitude threshold is routed through the exact root
square conversion. -/
def quartic_survival_amplitude_observable_source_of_threshold_root_observable_source
    (B : FullLedgerBlock)
    (S : QuarticSurvivalThresholdRootObservableSource B) :
    QuarticSurvivalAmplitudeObservableSource B where
  observable := S.observable
  observable_fully_charged := S.observable_fully_charged
  survival_observable_fixed_before_defect_scoring :=
    Nonempty
      (QuarticSurvivalAmplitudeObservableMatchReceipt
        B S.observable S.ampSq)
  survival_observable_fixed_before_defect_scoring_paid :=
    ⟨S.observable_match⟩
  root_defect_ledger_same_as_survival_observable :=
    Nonempty
      (QuarticSurvivalRootDefectLedgerMatchReceipt
        B S.observable S.ampSq)
  root_defect_ledger_same_as_survival_observable_paid :=
    ⟨S.root_ledger_match⟩
  amplitude_observable_matches_survival_profit :=
    Nonempty
      (QuarticSurvivalAmplitudeObservableMatchReceipt
        B S.observable S.ampSq)
  amplitude_observable_matches_survival_profit_paid :=
    ⟨S.observable_match⟩
  ampSq := S.ampSq
  gamma_nonnegative := S.gamma_nonnegative
  amp_sq_nonnegative := S.amp_sq_nonnegative
  amp_sq_le_one := S.amp_sq_le_one
  survival_profit_le_gain_at_amp := S.survival_profit_le_gain_at_amp
  above_wall_amp_sq_le_threshold := by
    intro hgt _hdefect
    exact
      threshold_root_source_above_wall_amp_sq_le_threshold
        B
        (quartic_survival_threshold_root_source_of_observable_source B S)
        hgt

/-- A fully charged observable amplitude source instantiates the compact
amplitude projection receipt. -/
def quartic_survival_amplitude_projection_of_observable_source
    (B : FullLedgerBlock)
    (S : QuarticSurvivalAmplitudeObservableSource B) :
    QuarticSurvivalAmplitudeProjectionReceipt B where
  survival_observable_fixed_before_defect_scoring :=
    S.survival_observable_fixed_before_defect_scoring
  root_defect_ledger_same_as_survival_observable :=
    S.root_defect_ledger_same_as_survival_observable
  survival_observable_fixed_before_defect_scoring_proved :=
    S.survival_observable_fixed_before_defect_scoring_paid
  root_defect_ledger_same_as_survival_observable_proved :=
    S.root_defect_ledger_same_as_survival_observable_paid
  ampSq := S.ampSq
  gamma_nonnegative := S.gamma_nonnegative
  amp_sq_nonnegative := S.amp_sq_nonnegative
  amp_sq_le_one := S.amp_sq_le_one
  survival_profit_le_gain_at_amp := S.survival_profit_le_gain_at_amp
  above_wall_amp_sq_le_threshold := S.above_wall_amp_sq_le_threshold

/-- Upgrade a scalar amplitude projection to the source-facing observable
receipt when the observable provenance is paid separately.

This is a migration adapter, not a new estimate: the old scalar projection
supplies only the amplitude inequalities, while the caller must provide a
fully charged signed observable and a paid same-observable/matching guard
before the source object exists. -/
def quartic_survival_amplitude_observable_source_of_projection_and_fully_charged_observable
    (B : FullLedgerBlock)
    (R : QuarticSurvivalAmplitudeProjectionReceipt B)
    (C : SignedObservable)
    (hC : GlobalSignedObservableFullyCharged C)
    (amplitude_observable_matches_survival_profit : Prop)
    (amplitude_observable_matches_survival_profit_paid :
      amplitude_observable_matches_survival_profit) :
    QuarticSurvivalAmplitudeObservableSource B where
  observable := C
  observable_fully_charged := hC
  survival_observable_fixed_before_defect_scoring :=
    R.survival_observable_fixed_before_defect_scoring
  survival_observable_fixed_before_defect_scoring_paid :=
    R.survival_observable_fixed_before_defect_scoring_proved
  root_defect_ledger_same_as_survival_observable :=
    R.root_defect_ledger_same_as_survival_observable
  root_defect_ledger_same_as_survival_observable_paid :=
    R.root_defect_ledger_same_as_survival_observable_proved
  amplitude_observable_matches_survival_profit :=
    amplitude_observable_matches_survival_profit
  amplitude_observable_matches_survival_profit_paid :=
    amplitude_observable_matches_survival_profit_paid
  ampSq := R.ampSq
  gamma_nonnegative := R.gamma_nonnegative
  amp_sq_nonnegative := R.amp_sq_nonnegative
  amp_sq_le_one := R.amp_sq_le_one
  survival_profit_le_gain_at_amp := R.survival_profit_le_gain_at_amp
  above_wall_amp_sq_le_threshold := R.above_wall_amp_sq_le_threshold

/-- Upgrade a scalar amplitude projection to the source-facing observable
receipt using a structured survival-profit match receipt.

This is the preferred adapter for generated Track B blocks: the match between
the observable, amplitude square, and survival-profit channel is a typed
receipt over `(B, C, R.ampSq)`, not an arbitrary free `Prop`. -/
def quartic_survival_amplitude_observable_source_of_projection_and_match_receipt
    (B : FullLedgerBlock)
    (R : QuarticSurvivalAmplitudeProjectionReceipt B)
    (C : SignedObservable)
    (hC : GlobalSignedObservableFullyCharged C)
    (M :
      QuarticSurvivalAmplitudeObservableMatchReceipt
        B
        C
        R.ampSq) :
    QuarticSurvivalAmplitudeObservableSource B :=
  quartic_survival_amplitude_observable_source_of_projection_and_fully_charged_observable
    B
    R
    C
    hC
    (Nonempty (QuarticSurvivalAmplitudeObservableMatchReceipt B C R.ampSq))
    ⟨M⟩

/-- A survival-amplitude observable source cannot be using an undercharged
observable, provided the falsifier names the same observable. -/
theorem no_undercharged_signed_observable_of_quartic_survival_amplitude_source
    (B : FullLedgerBlock)
    (S : QuarticSurvivalAmplitudeObservableSource B)
    (F : UnderchargedSignedObservable)
    (hsame : F.observable = S.observable) :
    False := by
  have hfully : GlobalSignedObservableFullyCharged F.observable := by
    simpa [hsame] using S.observable_fully_charged
  exact
    no_fully_charged_observable_of_undercharged F
      hfully

/-- Named ways an amplitude-level survival projection receipt can fail.

This is sharper than the projection-level falsifier: it points to the actual
amplitude/gain facts needed to construct `QuarticSurvivalProjectionReceipt`
for one linked block. -/
inductive QuarticSurvivalAmplitudeProjectionFalsifier
    (B : FullLedgerBlock)
    (R : QuarticSurvivalAmplitudeProjectionReceipt B) : Type where
  | survivalObservable :
      ¬ R.survival_observable_fixed_before_defect_scoring →
        QuarticSurvivalAmplitudeProjectionFalsifier B R
  | sameLedger :
      ¬ R.root_defect_ledger_same_as_survival_observable →
        QuarticSurvivalAmplitudeProjectionFalsifier B R
  | gammaNegative :
      ¬ 0 ≤ B.gamma →
        QuarticSurvivalAmplitudeProjectionFalsifier B R
  | ampSqNegative :
      ¬ 0 ≤ R.ampSq →
        QuarticSurvivalAmplitudeProjectionFalsifier B R
  | ampSqAboveOne :
      1 < R.ampSq →
        QuarticSurvivalAmplitudeProjectionFalsifier B R
  | survivalProfitAboveGainAtAmp :
      B.gamma * R.ampSq < B.survivalProfit →
        QuarticSurvivalAmplitudeProjectionFalsifier B R
  | aboveWallAmpThresholdFailure :
      (hgt : sharpTarget < B.gamma) →
      (hdefect : 1 ≤ survivalDefect B
        (Real.sqrt (sharpTarget / B.gamma))) →
      sharpTarget / B.gamma < R.ampSq →
        QuarticSurvivalAmplitudeProjectionFalsifier B R

/-- An amplitude-level survival projection receipt excludes each named
amplitude/gain failure branch. -/
theorem no_quartic_survival_amplitude_projection_falsifier
    (B : FullLedgerBlock)
    (R : QuarticSurvivalAmplitudeProjectionReceipt B)
    (F : QuarticSurvivalAmplitudeProjectionFalsifier B R) :
    False := by
  cases F with
  | survivalObservable h =>
      exact h R.survival_observable_fixed_before_defect_scoring_proved
  | sameLedger h =>
      exact h R.root_defect_ledger_same_as_survival_observable_proved
  | gammaNegative h =>
      exact h R.gamma_nonnegative
  | ampSqNegative h =>
      exact h R.amp_sq_nonnegative
  | ampSqAboveOne h =>
      exact not_lt_of_ge R.amp_sq_le_one h
  | survivalProfitAboveGainAtAmp h =>
      exact not_lt_of_ge R.survival_profit_le_gain_at_amp h
  | aboveWallAmpThresholdFailure hgt hdefect h =>
      exact not_lt_of_ge
        (R.above_wall_amp_sq_le_threshold hgt hdefect)
        h

/-- Named ways a fully charged observable amplitude source can fail.

This sits one layer above `QuarticSurvivalAmplitudeProjectionFalsifier`: it
catches undercharged signed observables and mismatched survival channels
before the scalar amplitude receipt is projected. -/
inductive QuarticSurvivalAmplitudeObservableSourceFalsifier
    (B : FullLedgerBlock)
    (S : QuarticSurvivalAmplitudeObservableSource B) : Type where
  | survivalObservable :
      ¬ S.survival_observable_fixed_before_defect_scoring →
        QuarticSurvivalAmplitudeObservableSourceFalsifier B S
  | sameLedger :
      ¬ S.root_defect_ledger_same_as_survival_observable →
        QuarticSurvivalAmplitudeObservableSourceFalsifier B S
  | amplitudeObservableMismatch :
      ¬ S.amplitude_observable_matches_survival_profit →
        QuarticSurvivalAmplitudeObservableSourceFalsifier B S
  | underchargedObservable :
      (F : UnderchargedSignedObservable) →
      F.observable = S.observable →
        QuarticSurvivalAmplitudeObservableSourceFalsifier B S
  | amplitudeProjectionFailure :
      QuarticSurvivalAmplitudeProjectionFalsifier B
        (quartic_survival_amplitude_projection_of_observable_source B S) →
        QuarticSurvivalAmplitudeObservableSourceFalsifier B S

/-- A valid observable amplitude source excludes each source and scalar
amplitude failure branch. -/
theorem no_quartic_survival_amplitude_observable_source_falsifier
    (B : FullLedgerBlock)
    (S : QuarticSurvivalAmplitudeObservableSource B)
    (F : QuarticSurvivalAmplitudeObservableSourceFalsifier B S) :
    False := by
  cases F with
  | survivalObservable h =>
      exact h S.survival_observable_fixed_before_defect_scoring_paid
  | sameLedger h =>
      exact h S.root_defect_ledger_same_as_survival_observable_paid
  | amplitudeObservableMismatch h =>
      exact h S.amplitude_observable_matches_survival_profit_paid
  | underchargedObservable F hsame =>
      exact
        no_undercharged_signed_observable_of_quartic_survival_amplitude_source
          B S F hsame
  | amplitudeProjectionFailure h =>
      exact
        no_quartic_survival_amplitude_projection_falsifier
          B
          (quartic_survival_amplitude_projection_of_observable_source B S)
          h

/-- The amplitude-level receipt instantiates the structured survival
projection receipt. -/
def quartic_survival_projection_of_amplitude_receipt
    (B : FullLedgerBlock)
    (R : QuarticSurvivalAmplitudeProjectionReceipt B) :
    QuarticSurvivalProjectionReceipt B where
  survival_observable_fixed_before_defect_scoring :=
    R.survival_observable_fixed_before_defect_scoring
  root_defect_ledger_same_as_survival_observable :=
    R.root_defect_ledger_same_as_survival_observable
  survival_observable_fixed_before_defect_scoring_proved :=
    R.survival_observable_fixed_before_defect_scoring_proved
  root_defect_ledger_same_as_survival_observable_proved :=
    R.root_defect_ledger_same_as_survival_observable_proved
  below_wall_profit_cap := by
    intro hbelow
    have hgain_le_gamma : B.gamma * R.ampSq ≤ B.gamma := by
      exact mul_le_of_le_one_right R.gamma_nonnegative R.amp_sq_le_one
    exact R.survival_profit_le_gain_at_amp.trans
      (hgain_le_gamma.trans hbelow)
  above_wall_defect_profit_cap := by
    intro hgt hdefect
    have htarget_pos : 0 < sharpTarget := by
      norm_num [sharpTarget]
    have hgamma : 0 < B.gamma := lt_trans htarget_pos hgt
    have hamp : R.ampSq ≤ sharpTarget / B.gamma :=
      R.above_wall_amp_sq_le_threshold hgt hdefect
    exact R.survival_profit_le_gain_at_amp.trans
      (ZtareProofs.gain_times_amp_sq_le_target_of_amp_sq_le
        (gamma := B.gamma)
        (target := sharpTarget)
        (ampSq := R.ampSq)
        hgamma
        hamp)

/-- Family adapter from amplitude-level receipts to quartic survival
projection receipts.

This is the preferred target for new closure attempts: prove the predeclared
amplitude inequality, then obtain the projection interface mechanically. -/
def quartic_survival_projection_family_of_amplitude_receipts
    (R : ∀ B : FullLedgerBlock,
      QuarticSurvivalAmplitudeProjectionReceipt B) :
    ∀ B : FullLedgerBlock, QuarticSurvivalProjectionReceipt B :=
  fun B => quartic_survival_projection_of_amplitude_receipt B (R B)

/-- Amplitude projection plus an independent threshold-defect source gives the
direct gain-at-amplitude cap.

This is the non-circular form of the new generated Lipschitz numeric target:
below the wall it follows from `ampSq <= 1`; above the wall it follows from
the same threshold-defect source consumed by the quartic projection. -/
theorem gain_at_amp_le_target_of_quartic_survival_amplitude_projection
    (B : FullLedgerBlock)
    (R : QuarticSurvivalAmplitudeProjectionReceipt B)
    (hdefect : ThresholdDefectConvexity B) :
    B.gamma * R.ampSq ≤ sharpTarget := by
  rcases hdefect with hbelow | habove
  · have hgain_le_gamma : B.gamma * R.ampSq ≤ B.gamma :=
      mul_le_of_le_one_right R.gamma_nonnegative R.amp_sq_le_one
    exact hgain_le_gamma.trans hbelow
  · rcases habove with ⟨hgt, hroot_defect⟩
    have hamp : R.ampSq ≤ sharpTarget / B.gamma :=
      R.above_wall_amp_sq_le_threshold hgt hroot_defect
    have htarget_pos : 0 < sharpTarget := by
      norm_num [sharpTarget]
    have hgamma_pos : 0 < B.gamma := lt_trans htarget_pos hgt
    exact
      ZtareProofs.gain_times_amp_sq_le_target_of_amp_sq_le
        (gamma := B.gamma)
        (target := sharpTarget)
        (ampSq := R.ampSq)
        hgamma_pos
        hamp

/-- Amplitude-level survival projection supplies no-survivor from
threshold-defect convexity without a black-box projection assumption. -/
theorem full_ledger_no_survivor_of_quartic_survival_amplitude_projection
    (B : FullLedgerBlock)
    (R : QuarticSurvivalAmplitudeProjectionReceipt B)
    (h : ThresholdDefectConvexity B) :
    FullLedgerNoSurvivor B :=
  full_ledger_no_survivor_of_quartic_survival_projection B
    (quartic_survival_projection_of_amplitude_receipt B R)
    h

/-- Anti-tautology witness: threshold-defect convexity alone cannot imply the
survival-profit cap while `survivalProfit` is an independent field.

This blocks the common overclaim "we proved the defect, therefore the survivor
is gone" unless a quartic survival projection receipt ties the survival
observable to that same ledger. -/
noncomputable def thresholdDefectButSurvivalProfitUnlinkedLedger :
    FullLedgerBlock where
  scope := LedgerScope.globalAdmissibleField
  gamma := sharpTarget
  cross := 0
  selfTax := 0
  survivalProfit := 1

theorem threshold_defect_but_survival_profit_unlinked_has_threshold_defect :
    ThresholdDefectConvexity thresholdDefectButSurvivalProfitUnlinkedLedger :=
  Or.inl le_rfl

theorem threshold_defect_but_survival_profit_unlinked_not_no_survivor :
    ¬ FullLedgerNoSurvivor thresholdDefectButSurvivalProfitUnlinkedLedger := by
  unfold FullLedgerNoSurvivor thresholdDefectButSurvivalProfitUnlinkedLedger
  norm_num [sharpTarget]

theorem threshold_defect_convexity_not_sufficient_without_survival_projection :
    ∃ B : FullLedgerBlock,
      ThresholdDefectConvexity B ∧ ¬ FullLedgerNoSurvivor B := by
  exact
    ⟨thresholdDefectButSurvivalProfitUnlinkedLedger,
      threshold_defect_but_survival_profit_unlinked_has_threshold_defect,
      threshold_defect_but_survival_profit_unlinked_not_no_survivor⟩

/-- The unlinked counterexample also rejects any claimed quartic survival
projection receipt for that ledger. -/
theorem no_quartic_survival_projection_for_unlinked_counterexample :
    ¬ Nonempty
      (QuarticSurvivalProjectionReceipt
        thresholdDefectButSurvivalProfitUnlinkedLedger) := by
  intro hR
  rcases hR with ⟨R⟩
  exact threshold_defect_but_survival_profit_unlinked_not_no_survivor
    (full_ledger_no_survivor_of_quartic_survival_projection
      thresholdDefectButSurvivalProfitUnlinkedLedger
      R
      threshold_defect_but_survival_profit_unlinked_has_threshold_defect)

/-- There is no unrestricted survival-projection family on all raw
`FullLedgerBlock`s.

This is the key anti-vacuity guard: closure-facing theorems must carry a
projection receipt for the specific linked block/observable they promote, not
an impossible global family over every record with an independent
`survivalProfit` field. -/
theorem no_unrestricted_quartic_survival_projection_family :
    ¬ Nonempty
      (∀ B : FullLedgerBlock, QuarticSurvivalProjectionReceipt B) := by
  intro hR
  rcases hR with ⟨R⟩
  exact no_quartic_survival_projection_for_unlinked_counterexample
    ⟨R thresholdDefectButSurvivalProfitUnlinkedLedger⟩

/-- The stronger amplitude-level projection receipt is likewise impossible
for the unlinked counterexample. -/
theorem no_quartic_survival_amplitude_projection_for_unlinked_counterexample :
    ¬ Nonempty
      (QuarticSurvivalAmplitudeProjectionReceipt
        thresholdDefectButSurvivalProfitUnlinkedLedger) := by
  intro hR
  rcases hR with ⟨R⟩
  exact threshold_defect_but_survival_profit_unlinked_not_no_survivor
    (full_ledger_no_survivor_of_quartic_survival_amplitude_projection
      thresholdDefectButSurvivalProfitUnlinkedLedger
      R
      threshold_defect_but_survival_profit_unlinked_has_threshold_defect)

/-- The stronger observable-source receipt is also impossible for the unlinked
counterexample.

This blocks a subtler vacuity: a closure cannot replace the linked
survival-projection burden by an unrestricted charged-observable source family.
The observable source still projects to the same amplitude receipt and therefore
must remain tied to the specific block/observable provenance. -/
theorem no_quartic_survival_amplitude_observable_source_for_unlinked_counterexample :
    ¬ Nonempty
      (QuarticSurvivalAmplitudeObservableSource
        thresholdDefectButSurvivalProfitUnlinkedLedger) := by
  intro hS
  rcases hS with ⟨S⟩
  exact no_quartic_survival_amplitude_projection_for_unlinked_counterexample
    ⟨quartic_survival_amplitude_projection_of_observable_source
      thresholdDefectButSurvivalProfitUnlinkedLedger
      S⟩

/-- There is no unrestricted survival-amplitude observable-source family on
all raw `FullLedgerBlock`s.

This is the source-facing version of
`no_unrestricted_quartic_survival_projection_family`: closure code must provide
the source receipt for the particular generated block, not a global oracle over
every independent ledger record. -/
theorem no_unrestricted_quartic_survival_amplitude_observable_source_family :
    ¬ Nonempty
      (∀ B : FullLedgerBlock, QuarticSurvivalAmplitudeObservableSource B) := by
  intro hS
  rcases hS with ⟨S⟩
  exact
    no_quartic_survival_amplitude_observable_source_for_unlinked_counterexample
      ⟨S thresholdDefectButSurvivalProfitUnlinkedLedger⟩

/-- A dual state-pricing certificate for the exact Track B ledger.

This is the no-arbitrage form of the remaining analytic burden: every
admissible Leray state is priced by a positive certificate before it can be
used as a blowup trade. The certificate must control the exact quartic defect,
not merely compare polynomial degrees. -/
structure DualStatePriceKernel where
  positive : Prop
  prices_exact_quartic :
    ∀ B : FullLedgerBlock,
      IsGlobalTrackBBlock B → ThresholdDefectConvexity B
  not_degree_only : Prop

/-- Direct vorticity-production dual price receipt.

This is the PDE-shaped version of the state-pricing target suggested by the
profile concentration scaling: positive stretching production should be priced
by the geometric mean of a viscous enstrophy channel and a Leray-projected
convective self-tax channel.

The analytic theorem is the product estimate
`production^2 <= viscousEnstrophyPrice * leraySelfTaxPrice`; the Lean result
below is only the AM-GM no-arbitrage handoff once that estimate has been paid. -/
structure VorticityDualPriceReceipt where
  production : Real
  viscousEnstrophyPrice : Real
  leraySelfTaxPrice : Real
  declaredPrice : Real
  production_nonnegative : 0 ≤ production
  viscous_price_nonnegative : 0 ≤ viscousEnstrophyPrice
  self_tax_price_nonnegative : 0 ≤ leraySelfTaxPrice
  declared_price_eq_average :
    declaredPrice =
      (viscousEnstrophyPrice + leraySelfTaxPrice) / 2
  production_sq_le_price_product :
    production ^ 2 ≤ viscousEnstrophyPrice * leraySelfTaxPrice

lemma vorticity_production_le_dual_average
    {production viscousPrice selfTaxPrice : Real}
    (hvisc_nonneg : 0 ≤ viscousPrice)
    (hself_nonneg : 0 ≤ selfTaxPrice)
    (hprod : production ^ 2 ≤ viscousPrice * selfTaxPrice) :
    production ≤ (viscousPrice + selfTaxPrice) / 2 := by
  nlinarith [sq_nonneg (viscousPrice - selfTaxPrice),
    sq_nonneg (2 * production - (viscousPrice + selfTaxPrice)),
    hvisc_nonneg, hself_nonneg, hprod]

/-- AM-GM handoff for the direct vorticity dual price receipt. -/
theorem production_priced_by_vorticity_dual_receipt
    (R : VorticityDualPriceReceipt) :
    R.production ≤ R.declaredPrice := by
  rw [R.declared_price_eq_average]
  exact vorticity_production_le_dual_average
    R.viscous_price_nonnegative
    R.self_tax_price_nonnegative
    R.production_sq_le_price_product

/-- PDE identity receipt behind the vorticity dual price.

For a smooth periodic divergence-free field, enstrophy production is the
pairing of the Leray-projected nonlinear term with `Delta u`; Cauchy-Schwarz
then gives the product estimate.  Lean records the receipt abstractly here;
the analytic/formal PDE proof must instantiate `production_sq_le_cauchy_product`
from the periodic integration-by-parts identity and Cauchy. -/
structure VorticityProductionCauchyReceipt where
  production : Real
  viscousEnstrophyPrice : Real
  leraySelfTaxPrice : Real
  production_nonnegative : 0 ≤ production
  viscous_price_nonnegative : 0 ≤ viscousEnstrophyPrice
  self_tax_price_nonnegative : 0 ≤ leraySelfTaxPrice
  periodic_divergence_free_identity_declared : Prop
  leray_pressure_orthogonality_declared : Prop
  production_sq_le_cauchy_product :
    production ^ 2 ≤ viscousEnstrophyPrice * leraySelfTaxPrice

/-- Convert the PDE Cauchy receipt into the AM-GM dual price receipt. -/
def vorticity_dual_price_receipt_of_cauchy
    (R : VorticityProductionCauchyReceipt) :
    VorticityDualPriceReceipt where
  production := R.production
  viscousEnstrophyPrice := R.viscousEnstrophyPrice
  leraySelfTaxPrice := R.leraySelfTaxPrice
  declaredPrice := (R.viscousEnstrophyPrice + R.leraySelfTaxPrice) / 2
  production_nonnegative := R.production_nonnegative
  viscous_price_nonnegative := R.viscous_price_nonnegative
  self_tax_price_nonnegative := R.self_tax_price_nonnegative
  declared_price_eq_average := rfl
  production_sq_le_price_product := R.production_sq_le_cauchy_product

/-- Cauchy identity plus AM-GM prices positive enstrophy production. -/
theorem production_priced_by_vorticity_cauchy_receipt
    (R : VorticityProductionCauchyReceipt) :
    R.production ≤
      (R.viscousEnstrophyPrice + R.leraySelfTaxPrice) / 2 :=
  production_priced_by_vorticity_dual_receipt
    (vorticity_dual_price_receipt_of_cauchy R)

/-- Null self-tax routes cannot carry positive enstrophy production under the
vorticity Cauchy receipt.  This is the formal version of the Beltrami/null
branch guardrail: zero projected nonlinear self-tax means zero priced
stretching production. -/
theorem production_eq_zero_of_zero_leray_self_tax
    (R : VorticityProductionCauchyReceipt)
    (hzero : R.leraySelfTaxPrice = 0) :
    R.production = 0 := by
  have hsq_nonneg : 0 ≤ R.production ^ 2 := sq_nonneg R.production
  have hsq_le_zero : R.production ^ 2 ≤ 0 := by
    simpa [hzero] using R.production_sq_le_cauchy_product
  have hsq_zero : R.production ^ 2 = 0 := by
    linarith
  exact sq_eq_zero_iff.mp hsq_zero

/-- Sharp scalar absorption of the dual-price product estimate.

If `production^2 <= viscousPrice * selfTaxPrice`, then after paying viscosity
`nu * viscousPrice`, the maximal remaining enstrophy growth is bounded by
`selfTaxPrice / (4 * nu)`.  This is the scalar form of optimizing the Young
split over the viscous channel. -/
theorem production_minus_viscosity_le_self_tax_over_four_nu
    {production viscousPrice selfTaxPrice nu : Real}
    (hnu : 0 < nu)
    (hprod_nonneg : 0 ≤ production)
    (hvisc_nonneg : 0 ≤ viscousPrice)
    (hself_nonneg : 0 ≤ selfTaxPrice)
    (hprod_sq : production ^ 2 ≤ viscousPrice * selfTaxPrice) :
    production - nu * viscousPrice ≤ selfTaxPrice / (4 * nu) := by
  have hnu_nonneg : 0 ≤ nu := le_of_lt hnu
  have hleft_nonneg : 0 ≤ 4 * nu * production := by
    nlinarith
  have hright_nonneg : 0 ≤ 4 * nu ^ 2 * viscousPrice + selfTaxPrice := by
    nlinarith [sq_nonneg nu]
  have hsquare :
      (4 * nu * production) ^ 2 ≤
        (4 * nu ^ 2 * viscousPrice + selfTaxPrice) ^ 2 := by
    nlinarith [sq_nonneg (4 * nu ^ 2 * viscousPrice - selfTaxPrice),
      sq_nonneg nu, hprod_sq]
  have habs :
      |4 * nu * production| ≤
        |4 * nu ^ 2 * viscousPrice + selfTaxPrice| := by
    exact (sq_le_sq.mp hsquare)
  rw [abs_of_nonneg hleft_nonneg, abs_of_nonneg hright_nonneg] at habs
  have hscaled : 4 * nu * (production - nu * viscousPrice) ≤ selfTaxPrice := by
    nlinarith
  have hden_pos : 0 < 4 * nu := by
    nlinarith
  rw [le_div_iff₀ hden_pos]
  nlinarith

/-- Time-integrated absorption receipt for the vorticity dual price.

This is the exact handoff after the identity
`Production = <P((u.grad)u), Delta u>`: a Young/Cauchy split can absorb a
declared fraction of the viscous enstrophy channel, but whatever remains is a
time integral of the Leray self-tax channel.  Thus the Clay-level burden is not
the instantaneous production identity; it is the profile/topology theorem that
controls or prices `selfTaxIntegral` without changing the observable class. -/
structure VorticityDualPriceTimeAbsorptionReceipt where
  initialEnstrophy : Real
  finalEnstrophy : Real
  viscosity : Real
  viscousIntegral : Real
  selfTaxIntegral : Real
  productionIntegral : Real
  absorbCoeff : Real
  selfTaxCoeff : Real
  viscous_integral_nonnegative : 0 ≤ viscousIntegral
  self_tax_coeff_nonnegative : 0 ≤ selfTaxCoeff
  absorb_coeff_le_viscosity : absorbCoeff ≤ viscosity
  enstrophy_balance_upper :
    finalEnstrophy ≤
      initialEnstrophy - viscosity * viscousIntegral + productionIntegral
  production_integral_priced :
    productionIntegral ≤
      absorbCoeff * viscousIntegral + selfTaxCoeff * selfTaxIntegral

/-- Once the viscous portion is absorbed, enstrophy is controlled exactly by
the unclosed Leray self-tax integral. -/
theorem enstrophy_controlled_by_self_tax_integral
    (R : VorticityDualPriceTimeAbsorptionReceipt) :
    R.finalEnstrophy ≤ R.initialEnstrophy + R.selfTaxCoeff * R.selfTaxIntegral := by
  have hmul :
      R.absorbCoeff * R.viscousIntegral ≤ R.viscosity * R.viscousIntegral := by
    exact mul_le_mul_of_nonneg_right
      R.absorb_coeff_le_viscosity
      R.viscous_integral_nonnegative
  nlinarith [R.enstrophy_balance_upper, R.production_integral_priced, hmul]

/-- A self-tax budget turns the time-integrated dual-price receipt into a
finite enstrophy bound. This is still conditional; the budget is the remaining
profile/limit-passage theorem, not an assumption that can be inserted after
payoff scoring. -/
theorem enstrophy_bound_of_self_tax_budget
    (R : VorticityDualPriceTimeAbsorptionReceipt)
    {budget : Real}
    (hbudget : R.selfTaxCoeff * R.selfTaxIntegral ≤ budget) :
    R.finalEnstrophy ≤ R.initialEnstrophy + budget := by
  have hcontrol := enstrophy_controlled_by_self_tax_integral R
  linarith

/-- Exact scalar receipt for two-profile self-tax gluing.

For projected nonlinearities `A=P((u.grad)u)`, `B=P((v.grad)v)`, and
`C=P((u.grad)v+(v.grad)u)`, the static algebra is
`||A+B+C||^2 = ||A||^2 + ||B||^2 + ||C||^2
  + 2<A,B> + 2<A,C> + 2<B,C>`.

The positive parts of the three coherence terms are therefore an exact
one-sided cover for the undercharge. The continuum PDE burden is to prove that
this positive coherence is charged by a fixed profile topology before payoff
scoring; the scalar receipt only prevents hiding the missing term. -/
structure SelfTaxTwoProfileCoherenceDecomposition where
  branchA : Real
  branchB : Real
  cross : Real
  coherenceAB : Real
  coherenceAC : Real
  coherenceBC : Real
  total : Real
  positiveCoherenceBudget : Real
  exact_decomposition :
    total =
      branchA + branchB + cross +
        coherenceAB + coherenceAC + coherenceBC
  positive_coherence_budget_eq :
    positiveCoherenceBudget =
      max coherenceAB 0 + max coherenceAC 0 + max coherenceBC 0
  coherenceAB_le_branch_pair : coherenceAB ≤ branchA + branchB
  coherenceAC_le_branch_cross : coherenceAC ≤ branchA + cross
  coherenceBC_le_branch_cross : coherenceBC ≤ branchB + cross

/-- Branch, cross, and positive-coherence budgets cover the two-profile
self-tax exactly in the scalar receipt. -/
theorem two_profile_self_tax_le_positive_coherence_budget
    (D : SelfTaxTwoProfileCoherenceDecomposition) :
    D.total ≤
      D.branchA + D.branchB + D.cross + D.positiveCoherenceBudget := by
  have hAB : D.coherenceAB ≤ max D.coherenceAB 0 := le_max_left _ _
  have hAC : D.coherenceAC ≤ max D.coherenceAC 0 := le_max_left _ _
  have hBC : D.coherenceBC ≤ max D.coherenceBC 0 := le_max_left _ _
  rw [D.exact_decomposition, D.positive_coherence_budget_eq]
  nlinarith

/-- Blunter but topology-friendly two-profile receipt: Cauchy/Young charges all
coherence terms by a universal factor of the branch-plus-cross component sum.

This is not sharp enough to settle the threshold ledger by itself, but it
rules out a binary-gluing ghost where coherence is completely unpriced. -/
theorem two_profile_self_tax_le_three_component_sum
    (D : SelfTaxTwoProfileCoherenceDecomposition) :
    D.total ≤ 3 * (D.branchA + D.branchB + D.cross) := by
  rw [D.exact_decomposition]
  nlinarith [D.coherenceAB_le_branch_pair,
    D.coherenceAC_le_branch_cross,
    D.coherenceBC_le_branch_cross]

/-- Output-side Gram coherence receipt for finite profile gluing.

`componentNormSum` is the sum of the squared norms of all declared projected
output atoms: self terms and cross terms.  `signedCoherence` is the total
signed Gram pair contribution between those atoms.  The correct all-output
ledger charges `positiveCoherence`, not just component norms. -/
structure AllOutputGramCoherenceGluingReceipt where
  totalSelfTax : Real
  componentNormSum : Real
  signedCoherence : Real
  positiveCoherence : Real
  declaredFullPrice : Real
  exact_gram_decomposition :
    totalSelfTax = componentNormSum + signedCoherence
  signed_coherence_le_positive :
    signedCoherence ≤ positiveCoherence
  declared_full_price_eq :
    declaredFullPrice = componentNormSum + positiveCoherence

/-- Finite all-output Gram coherence charges profile gluing.

This is the algebra behind Phase 5JF: finite profile gluing is not the hard
part once every output atom is declared and positive Gram coherence is charged.
The hard part remains continuum lower-semicontinuity of this fixed ledger. -/
theorem total_self_tax_le_declared_all_output_gram_price
    (G : AllOutputGramCoherenceGluingReceipt) :
    G.totalSelfTax ≤ G.declaredFullPrice := by
  rw [G.exact_gram_decomposition, G.declared_full_price_eq]
  nlinarith [G.signed_coherence_le_positive]

/-- If component norms alone undercharge the total self-tax, the omitted
positive coherence cannot be set to zero in a valid all-output Gram receipt. -/
theorem positive_coherence_required_of_component_undercharge
    (G : AllOutputGramCoherenceGluingReceipt)
    (hunder : G.componentNormSum < G.totalSelfTax) :
    0 < G.positiveCoherence := by
  rw [G.exact_gram_decomposition] at hunder
  have hpos : 0 < G.signedCoherence := by
    linarith
  exact lt_of_lt_of_le hpos G.signed_coherence_le_positive

/-- Local-to-global assembly receipt for the Leray self-tax integral.

This is the `core_04` object exposed by the op-class mapper: local/profile
branch prices do not prove anything until a gluing receipt shows that their
sum, plus declared cross-defect price, really charges the global time integral
under the same topology and observable class. -/
structure SelfTaxIntegralLocalToGlobalReceipt where
  selfTaxIntegral : Real
  branchBudgetSum : Real
  crossDefectBudget : Real
  coherenceBudget : Real
  totalBudget : Real
  self_tax_integral_nonnegative : 0 ≤ selfTaxIntegral
  branch_budget_nonnegative : 0 ≤ branchBudgetSum
  cross_defect_budget_nonnegative : 0 ≤ crossDefectBudget
  coherence_budget_nonnegative : 0 ≤ coherenceBudget
  fixed_topology_predeclared : Prop
  fixed_topology_predeclared_paid :
    fixed_topology_predeclared
  observable_class_predeclared : Prop
  observable_class_predeclared_paid :
    observable_class_predeclared
  branch_prices_declared_before_payoff : Prop
  branch_prices_declared_before_payoff_paid :
    branch_prices_declared_before_payoff
  cross_defects_charged_before_gluing : Prop
  cross_defects_charged_before_gluing_paid :
    cross_defects_charged_before_gluing
  coherence_terms_charged_before_gluing : Prop
  coherence_terms_charged_before_gluing_paid :
    coherence_terms_charged_before_gluing
  self_tax_charged_by_branch_and_cross :
    selfTaxIntegral ≤ branchBudgetSum + crossDefectBudget + coherenceBudget
  total_budget_eq :
    totalBudget = branchBudgetSum + crossDefectBudget + coherenceBudget

/-- Falsifiers for a local-to-global self-tax receipt whose numeric budget is
present but whose topology/source declarations were not actually paid. -/
inductive SelfTaxIntegralLocalToGlobalSourceFalsifier
    (G : SelfTaxIntegralLocalToGlobalReceipt) : Prop where
  | missing_fixed_topology :
      ¬ G.fixed_topology_predeclared →
        SelfTaxIntegralLocalToGlobalSourceFalsifier G
  | missing_observable_class :
      ¬ G.observable_class_predeclared →
        SelfTaxIntegralLocalToGlobalSourceFalsifier G
  | branch_prices_posthoc :
      ¬ G.branch_prices_declared_before_payoff →
        SelfTaxIntegralLocalToGlobalSourceFalsifier G
  | cross_defects_not_charged_before_gluing :
      ¬ G.cross_defects_charged_before_gluing →
        SelfTaxIntegralLocalToGlobalSourceFalsifier G
  | coherence_terms_not_charged_before_gluing :
      ¬ G.coherence_terms_charged_before_gluing →
        SelfTaxIntegralLocalToGlobalSourceFalsifier G

/-- A local-to-global self-tax receipt excludes missing-source guard failures.

This does not prove the analytic gluing estimate; it only keeps the receipt's
predeclared topology and charged-cross/coherence guards load-bearing. -/
theorem no_self_tax_integral_local_to_global_source_falsifier
    (G : SelfTaxIntegralLocalToGlobalReceipt)
    (F : SelfTaxIntegralLocalToGlobalSourceFalsifier G) :
    False := by
  cases F with
  | missing_fixed_topology h =>
      exact h G.fixed_topology_predeclared_paid
  | missing_observable_class h =>
      exact h G.observable_class_predeclared_paid
  | branch_prices_posthoc h =>
      exact h G.branch_prices_declared_before_payoff_paid
  | cross_defects_not_charged_before_gluing h =>
      exact h G.cross_defects_charged_before_gluing_paid
  | coherence_terms_not_charged_before_gluing h =>
      exact h G.coherence_terms_charged_before_gluing_paid

/-- The local-to-global receipt yields a total self-tax integral budget. -/
theorem self_tax_integral_le_total_budget_of_local_to_global
    (G : SelfTaxIntegralLocalToGlobalReceipt) :
    G.selfTaxIntegral ≤ G.totalBudget := by
  rw [G.total_budget_eq]
  exact G.self_tax_charged_by_branch_and_cross

/-- Coherence is not optional when branch plus cross budgets undercharge the
global self-tax integral.  This is the formal version of the Phase 5IG warning:
setting the coherence/inner-product budget to zero is falsified by any profile
pair with positive undercharge. -/
theorem no_zero_coherence_local_to_global_receipt_of_undercharge
    (G : SelfTaxIntegralLocalToGlobalReceipt)
    (hzero : G.coherenceBudget = 0)
    (hunder : G.branchBudgetSum + G.crossDefectBudget < G.selfTaxIntegral) :
    False := by
  have hcharge := G.self_tax_charged_by_branch_and_cross
  nlinarith

/-- Compose the time-absorption receipt with the local-to-global self-tax
gluing receipt.  This is still conditional: the gluing receipt is the real PDE
profile theorem. -/
theorem enstrophy_bound_of_local_to_global_self_tax_budget
    (R : VorticityDualPriceTimeAbsorptionReceipt)
    (G : SelfTaxIntegralLocalToGlobalReceipt)
    (hmatch : R.selfTaxIntegral = G.selfTaxIntegral) :
    R.finalEnstrophy ≤
      R.initialEnstrophy + R.selfTaxCoeff * G.totalBudget := by
  have htax : R.selfTaxIntegral ≤ G.totalBudget := by
    rw [hmatch]
    exact self_tax_integral_le_total_budget_of_local_to_global G
  have hbudget :
      R.selfTaxCoeff * R.selfTaxIntegral ≤
        R.selfTaxCoeff * G.totalBudget := by
    exact mul_le_mul_of_nonneg_left htax R.self_tax_coeff_nonnegative
  exact enstrophy_bound_of_self_tax_budget R hbudget

/-- The unresolved analytic Track B obligation.

`threshold_defect_from_leray` is the new PDE/harmonic-analysis content: the
flat-torus Leray vector ledger must force threshold-defect convexity on the
global admissible field class, with null directions, cross terms, charged
observables, and scope handled honestly.

`quartic_survival_projection` connects that vector statement to the already
isolated scalar survival ledger only at the promoted block.  It is therefore
not a field of this global convexity object: an unrestricted family over every
raw `FullLedgerBlock` is impossible by
`no_unrestricted_quartic_survival_projection_family`.
-/
structure TrackBLerayConvexityObligation where
  dual_kernel : DualStatePriceKernel
  threshold_defect_from_leray :
    ∀ (B : FullLedgerBlock) (C : SignedObservable),
      IsGlobalTrackBBlock B →
        IsAdmissibleObservable C →
          ThresholdDefectConvexity B

/-- Strong-observable version of the unresolved analytic Track B obligation.

This is the preferred GP216-facing surface after the signed-observable audit:
the theorem may still be open, but any future closure must feed the Leray
convexity statement with a fully charged observable, not merely the legacy
matrix-only admissibility adapter. -/
structure TrackBLerayConvexityFullyChargedObligation where
  dual_kernel : DualStatePriceKernel
  threshold_defect_from_leray :
    ∀ (B : FullLedgerBlock) (C : SignedObservable),
      IsGlobalTrackBBlock B →
        GlobalSignedObservableFullyCharged C →
          ThresholdDefectConvexity B

/-- Concentration-compactness branches that a global pricing theorem must
handle. These are proof-burden labels, not a decomposition theorem. -/
inductive ProfileLimitBranch where
  | compactProfile
  | vanishing
  | dichotomy
  | concentration
  | nullProfile
  | crossProfileRecombination
deriving DecidableEq, Repr

/-- The post-Phase-5F limit-passage obligation.

Finite PSD and lifted quartic certificates price fixed supports. A global
Track B theorem also needs a topology and a profile calculus showing that no
near-arbitrage sequence can change the rules at infinity. The fields below
name that obligation in a way that prevents the common tautology: the state
space, observable class, and topology must be fixed before the limiting
sequence is scored. -/
structure PricingKernelLimitPassageObligation where
  state_space_predeclared : Prop
  observable_class_predeclared : Prop
  limit_topology_predeclared : Prop
  fixed_observable_closed_at_limit : Prop
  profile_decomposition_available : Prop
  vanishing_has_no_payoff : Prop
  dichotomy_is_subadditive_for_price : Prop
  concentration_charged_by_price : Prop
  null_profiles_capped : Prop
  cross_profile_cancellation_charged : Prop
  threshold_defect_survives_limit :
    ∀ (B : FullLedgerBlock) (C : SignedObservable),
      IsGlobalTrackBBlock B →
        IsAdmissibleObservable C →
          ThresholdDefectConvexity B

/-- Cycle-free endpoint view for Leray self-tax/profile limit streams.

The downstream `LeraySelfTaxProfilePriceStream` lives in a module that imports
this Track B spine, so this file cannot mention it directly without creating an
import cycle.  This endpoint records exactly the source/provenance fields the
downstream stream exposes, plus the aggregate payoff/limit price edge that a
limit-passage receipt must pay. -/
structure TrackBSelfTaxLimitEndpoint where
  payoffLimit : Real
  limitPrice : Real
  profileTopologyDeclaredBeforePayoff : Prop
  profileStreamDeclaredBeforePayoff : Prop
  prefixComponentPricesDeclaredBeforePayoff : Prop
  limitComponentPricesDeclaredBeforePayoff : Prop
  noPosthocPayoffDependentStreamChoice : Prop

/-- Limit-passage receipt for the self-tax endpoint.

This is not a PDE closure: `limit_no_arbitrage` and the downstream
threshold-coordinate handoff still have to be supplied by the analytic
self-tax/profile stream.  The point of the receipt is to make the source and
provenance guards theorem-level inputs rather than decorative fields. -/
structure TrackBSelfTaxEndpointLimitPassageReceipt
    (E : TrackBSelfTaxLimitEndpoint) where
  profile_topology_declared_before_payoff :
    E.profileTopologyDeclaredBeforePayoff
  profile_stream_declared_before_payoff :
    E.profileStreamDeclaredBeforePayoff
  prefix_component_prices_declared_before_payoff :
    E.prefixComponentPricesDeclaredBeforePayoff
  limit_component_prices_declared_before_payoff :
    E.limitComponentPricesDeclaredBeforePayoff
  no_posthoc_payoff_dependent_stream_choice :
    E.noPosthocPayoffDependentStreamChoice
  limit_no_arbitrage :
    E.payoffLimit ≤ E.limitPrice

/-- Source-ready predicate consumed by endpoint handoffs. -/
def TrackBSelfTaxEndpointSourceReady
    (E : TrackBSelfTaxLimitEndpoint) : Prop :=
  E.profileTopologyDeclaredBeforePayoff ∧
    E.profileStreamDeclaredBeforePayoff ∧
      E.prefixComponentPricesDeclaredBeforePayoff ∧
        E.limitComponentPricesDeclaredBeforePayoff ∧
          E.noPosthocPayoffDependentStreamChoice

/-- A paid endpoint limit-passage receipt exposes all source/provenance guards
as a single theorem-level edge. -/
theorem trackb_self_tax_endpoint_source_ready_of_limit_passage
    (E : TrackBSelfTaxLimitEndpoint)
    (R : TrackBSelfTaxEndpointLimitPassageReceipt E) :
    TrackBSelfTaxEndpointSourceReady E := by
  exact
    ⟨R.profile_topology_declared_before_payoff,
      R.profile_stream_declared_before_payoff,
      R.prefix_component_prices_declared_before_payoff,
      R.limit_component_prices_declared_before_payoff,
      R.no_posthoc_payoff_dependent_stream_choice⟩

/-- Which provenance guard failed for a self-tax endpoint. -/
inductive TrackBSelfTaxEndpointGuardBranch where
  | topology
  | stream
  | prefixPrices
  | limitPrices
  | payoffDependentChoice
deriving DecidableEq, Repr

/-- Branch-wise falsifier for the known endpoint escape: the payoff is priced
only after moving the topology, stream, component prices, or stream choice. -/
structure TrackBSelfTaxEndpointGuardFalsifier
    (E : TrackBSelfTaxLimitEndpoint) where
  branch : TrackBSelfTaxEndpointGuardBranch
  missing :
    match branch with
    | TrackBSelfTaxEndpointGuardBranch.topology =>
        ¬ E.profileTopologyDeclaredBeforePayoff
    | TrackBSelfTaxEndpointGuardBranch.stream =>
        ¬ E.profileStreamDeclaredBeforePayoff
    | TrackBSelfTaxEndpointGuardBranch.prefixPrices =>
        ¬ E.prefixComponentPricesDeclaredBeforePayoff
    | TrackBSelfTaxEndpointGuardBranch.limitPrices =>
        ¬ E.limitComponentPricesDeclaredBeforePayoff
    | TrackBSelfTaxEndpointGuardBranch.payoffDependentChoice =>
        ¬ E.noPosthocPayoffDependentStreamChoice

/-- A paid endpoint limit-passage receipt excludes each source/provenance guard
falsifier. -/
theorem no_trackb_self_tax_endpoint_guard_falsifier_of_limit_passage
    (E : TrackBSelfTaxLimitEndpoint)
    (R : TrackBSelfTaxEndpointLimitPassageReceipt E)
    (F : TrackBSelfTaxEndpointGuardFalsifier E) :
    False := by
  rcases F with ⟨branch, hmissing⟩
  cases branch with
  | topology =>
      exact hmissing R.profile_topology_declared_before_payoff
  | stream =>
      exact hmissing R.profile_stream_declared_before_payoff
  | prefixPrices =>
      exact hmissing R.prefix_component_prices_declared_before_payoff
  | limitPrices =>
      exact hmissing R.limit_component_prices_declared_before_payoff
  | payoffDependentChoice =>
      exact hmissing R.no_posthoc_payoff_dependent_stream_choice

/-- Endpoint adapter into the open Track B threshold-defect handoff.

The final argument is intentionally explicit: the endpoint receipt only proves
limit no-arbitrage for the declared stream.  A downstream
`LeraySelfTaxProfilePriceStream` still has to identify that price with the same
threshold-root ledger for the branch block. -/
theorem threshold_defect_of_trackb_self_tax_endpoint_limit_passage
    (E : TrackBSelfTaxLimitEndpoint)
    (R : TrackBSelfTaxEndpointLimitPassageReceipt E)
    (B : FullLedgerBlock)
    (threshold_defect_of_endpoint_no_arbitrage :
      TrackBSelfTaxEndpointSourceReady E →
        E.payoffLimit ≤ E.limitPrice →
          ThresholdDefectConvexity B) :
    ThresholdDefectConvexity B :=
  threshold_defect_of_endpoint_no_arbitrage
    (trackb_self_tax_endpoint_source_ready_of_limit_passage E R)
    R.limit_no_arbitrage

/-- Projection-typed no-survivor adapter for the self-tax endpoint.  It keeps
the quartic survival projection and the self-tax limit-passage receipt as
separate obligations, so no PDE closure is smuggled in by the endpoint. -/
theorem no_global_survivor_of_trackb_self_tax_endpoint_limit_passage
    (E : TrackBSelfTaxLimitEndpoint)
    (R : TrackBSelfTaxEndpointLimitPassageReceipt E)
    (B : FullLedgerBlock)
    (hprojection : QuarticSurvivalProjectionReceipt B)
    (threshold_defect_of_endpoint_no_arbitrage :
      TrackBSelfTaxEndpointSourceReady E →
        E.payoffLimit ≤ E.limitPrice →
          ThresholdDefectConvexity B) :
    FullLedgerNoSurvivor B :=
  full_ledger_no_survivor_of_quartic_survival_projection B
    hprojection
    (threshold_defect_of_trackb_self_tax_endpoint_limit_passage
      E R B threshold_defect_of_endpoint_no_arbitrage)

/-- Limit-passage projection theorem: if the finite state-price kernel has a
valid global limit-passage theorem, then the same no-survivor conclusion follows
for global Track B blocks. -/
theorem no_global_survivor_of_limit_passage
    (hlim : PricingKernelLimitPassageObligation)
    (B : FullLedgerBlock)
    (hprojection : QuarticSurvivalProjectionReceipt B)
    (C : SignedObservable)
    (hglobal : IsGlobalTrackBBlock B)
    (hC : IsAdmissibleObservable C) :
    FullLedgerNoSurvivor B := by
  exact full_ledger_no_survivor_of_quartic_survival_projection B
    hprojection
    (hlim.threshold_defect_survives_limit B C hglobal hC)

/-- Scope anti-narrowing: a finite or named-class block is not a global Track B
block by relabeling. -/
theorem not_global_trackB_of_scope_ne_global
    {B : FullLedgerBlock}
    (hscope : B.scope ≠ LedgerScope.globalAdmissibleField) :
    ¬ IsGlobalTrackBBlock B := by
  exact hscope

/-- The per-block oracle is a hostile numerical upper bound, not an admissible
Track B observable. -/
theorem perBlockOracle_not_admissible
    {C : SignedObservable}
    (hkind : C.kind = ObservableKind.perBlockOracle) :
    ¬ IsAdmissibleObservable C := by
  intro h
  exact h.1 hkind

/-- Scalar observable that passes the legacy matrix-only admissibility gate
without paying the generic normalization/damping/cross-term charges.

This is an anti-tautology witness: legacy admissibility is not enough for the
GP216-facing fully charged observable interface. -/
def legacyAdmissibleButNotFullyChargedScalarObservable : SignedObservable where
  kind := ObservableKind.scalar
  predeclared := True
  independentNormalized := False
  psdBallastCharged := False
  dampingCharged := False
  crossTermCharged := False

/-- Legacy admissibility does not imply full observable charging.

The scalar case makes the matrix-block implication vacuous, so a closure that
requires `GlobalSignedObservableFullyCharged` cannot substitute the older
`IsAdmissibleObservable` receipt. -/
theorem legacy_admissible_observable_does_not_imply_fully_charged :
    ∃ C : SignedObservable,
      IsAdmissibleObservable C ∧
        ¬ GlobalSignedObservableFullyCharged C := by
  refine ⟨legacyAdmissibleButNotFullyChargedScalarObservable, ?_, ?_⟩
  · refine ⟨?_, trivial, ?_⟩
    · intro hkind
      cases hkind
    · intro hmatrix
      cases hmatrix
  · intro hcharged
    exact hcharged.2.2.1

/-- Projection theorem: once the real Track B analytic obligation is paid,
global full-ledger survivors above `2/3` are excluded. -/
theorem no_global_survivor_of_trackB_obligation
    (h : TrackBLerayConvexityObligation)
    (B : FullLedgerBlock)
    (hprojection : QuarticSurvivalProjectionReceipt B)
    (C : SignedObservable)
    (hglobal : IsGlobalTrackBBlock B)
    (hC : IsAdmissibleObservable C) :
    FullLedgerNoSurvivor B := by
  exact full_ledger_no_survivor_of_quartic_survival_projection B
    hprojection
    (h.threshold_defect_from_leray B C hglobal hC)

/-- Projection theorem for the strong-observable Track B obligation. -/
theorem no_global_survivor_of_trackB_fully_charged_obligation
    (h : TrackBLerayConvexityFullyChargedObligation)
    (B : FullLedgerBlock)
    (hprojection : QuarticSurvivalProjectionReceipt B)
    (C : SignedObservable)
    (hglobal : IsGlobalTrackBBlock B)
    (hC : GlobalSignedObservableFullyCharged C) :
    FullLedgerNoSurvivor B :=
  full_ledger_no_survivor_of_quartic_survival_projection B
    hprojection
    (h.threshold_defect_from_leray B C hglobal hC)

end

end ZtareProofs.NS
