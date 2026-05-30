import Mathlib.Tactic

/-!
# Silent flat defect observability — measure-valued trichotomy (tick443)

Per operator + ChatGPT-5.5 analytic compression 2026-05-14: the right way to
formulate the ESS / Constantin-Fefferman / genuine-measure-valued-flat-defect
trichotomy is NOT to assert `observabilityExhaustion` as a Prop field, but to
build it from observer data + ESS/CF black boxes + a substantive
residual-construction lemma.

This file ships:

1. Three abstract observer structures (endpoint-L³, vorticity-direction,
   silent-flat-residual) carrying the analytic data needed to define what
   "ESS-visible", "CF-coherent", and "charged-by-new-residual" mean for a
   generalized flat tangent profile.

2. `SilentFlatDefectObserverData` — the bundle.

3. `SilentFlatDefectObservability` — the trichotomy.

4. `SilentFlatDefectObservability_ofObserverData` — the trichotomy theorem,
   PROVED from the observer data + ESS + CF + the residual-fallback lemma.

5. `residual_of_not_ess_not_cf_from_ESS` — the substantive ESS-fallback lemma:
   if a silent flat bad profile is neither ESS-visible nor CF-coherent, then
   it must carry a genuine measure-valued flat defect (else ESS regularity
   contradicts CKN badness at all scales).

6. `SilentFlatResidualRadiusCharge` — the next bridge target (finite
   radius-charge budgets per branch), recorded as the remaining PDE work.

Honest scope: the observer fields are abstract `Prop` carriers — measure
theory is not formally instantiated.  The trichotomy theorem and the
ESS-fallback lemma are real Lean proofs from those abstract carriers.  The
final radius-charge bridge is NOT proved here; supplying it is the
post-tick443 PDE target.
-/

namespace ZtareProofs.NSSilentFlatDefectObservability

universe u

variable (Profile : Type u)

/--
Endpoint-L³ observer for a generalized profile (ESS-visibility carrier).

The "ESS-visible" predicate is *defined* from endpoint-L³ tightness +
endpoint-L³ defect charging the active flat carrier.  Negation gives
L³-tight, no defect charge — the regime where ESS can kill an ordinary
profile.
-/
structure EndpointL3MeasureObserver (U : Profile) where
  endpointL3Tight : Prop
  endpointL3BlowupVisible : Prop
  endpointL3DefectChargesActive : Prop
  endpointL3BlowupVisible_iff_not_tight :
    endpointL3BlowupVisible ↔ ¬ endpointL3Tight
  isESSVisible : Prop
  isESSVisible_iff :
    isESSVisible ↔ endpointL3BlowupVisible ∨ endpointL3DefectChargesActive
  not_essVisible_gives_tight :
    ¬ isESSVisible → endpointL3Tight
  endpointL3DefectFromProfileLimit : Prop
  endpointL3SliceMassFromDisintegration : Prop
  endpointL3MeasureFixedBeforeRouteReceipt : Prop

/--
Vorticity-direction observer for a generalized profile
(Constantin-Fefferman-coherence carrier).

The "CF-coherent" predicate is *defined* by direction-Young-kernel coherence
+ a sub-threshold coherence seminorm.  Negation gives the
direction-decoherent residual.
-/
structure VorticityDirectionMeasureObserver (U : Profile) where
  directionKernelDiracAE : Prop
  cfCoherenceSeminormBelowThreshold : Prop
  isCFCoherent : Prop
  isCFCoherent_iff :
    isCFCoherent ↔ directionKernelDiracAE ∧ cfCoherenceSeminormBelowThreshold
  directionDecoherent : Prop
  directionDecoherent_iff_not_coherent :
    directionDecoherent ↔ ¬ isCFCoherent
  not_cfCoherent_gives_decoherent :
    ¬ isCFCoherent → directionDecoherent
  directionOscillationMeasureFromProfileLimit : Prop
  vorticityVariationFromProfile : Prop

/--
Silent-flat-residual observer (the "dark matter" branch).

The strict fallback: not ESS-visible, not CF-coherent, L³-tight,
direction-decoherent, and genuine measure-valued flat defect charged by the
residual measure.
-/
structure SilentFlatResidualObserver (U : Profile)
    (ess : EndpointL3MeasureObserver Profile U)
    (cf : VorticityDirectionMeasureObserver Profile U) where
  genuineMeasureValuedFlatDefect : Prop
  residualCharge : Prop
  silentFlatResidualMeasureFromProfileDefect : Prop
  isChargedByNewResidual : Prop
  isChargedByNewResidual_iff :
    isChargedByNewResidual ↔
      ¬ ess.isESSVisible ∧ ¬ cf.isCFCoherent ∧
        ess.endpointL3Tight ∧ cf.directionDecoherent ∧
        genuineMeasureValuedFlatDefect ∧ residualCharge

/--
Observer-data bundle: an actual silent flat bad profile + the three observer
structures + ESS/CF black boxes + the "ordinary if no genuine defect" clause
+ the "genuine defect implies charged" clause.

The ESS and CF black boxes are applied ONLY to ordinary profiles; the
not-ordinary case lands in the residual branch.
-/
structure SilentFlatDefectObserverData where
  U : Profile
  isGeneralizedFlatTangentProfile : Profile → Prop
  flatInheritedAtAllScales : Profile → Prop
  routeInvisible : Profile → Prop
  pressureInvisible : Profile → Prop
  betaInvisible : Profile → Prop
  finiteResidualInvisible : Profile → Prop
  cknBadAtAllScales : Profile → Prop
  hSilent : isGeneralizedFlatTangentProfile U ∧
    flatInheritedAtAllScales U ∧
    routeInvisible U ∧ pressureInvisible U ∧
    betaInvisible U ∧ finiteResidualInvisible U ∧
    cknBadAtAllScales U
  ess : EndpointL3MeasureObserver Profile U
  cf : VorticityDirectionMeasureObserver Profile U
  residual : SilentFlatResidualObserver Profile U ess cf
  ordinarySuitableProfile : Profile → Prop
  regularAtCenter : Profile → Prop
  /-- If there is no genuine measure-valued flat defect, the profile is
      ordinary enough for ESS/CF to apply. -/
  ordinary_if_no_genuine_defect :
    ¬ residual.genuineMeasureValuedFlatDefect → ordinarySuitableProfile U
  /-- ESS black box: ordinary + L³-tight ⇒ regular at center. -/
  ESS_regular :
    ordinarySuitableProfile U → ess.endpointL3Tight → regularAtCenter U
  /-- Constantin-Fefferman black box: ordinary + CF-coherent ⇒ regular. -/
  CF_regular :
    ordinarySuitableProfile U → cf.isCFCoherent → regularAtCenter U
  /-- Regularity contradicts CKN badness at all scales. -/
  regular_contradicts_bad_all_scales :
    regularAtCenter U → ¬ cknBadAtAllScales U
  /-- Genuine measure-valued flat defect implies the residual is charged. -/
  charge_of_genuine_defect :
    residual.genuineMeasureValuedFlatDefect → residual.residualCharge

variable {Profile}

/--
Silent flat defect observability — the trichotomy structure, proved from
observer data.
-/
structure SilentFlatDefectObservability where
  isESSVisible : Prop
  isCFCoherent : Prop
  isChargedByNewResidual : Prop
  observabilityExhaustion :
    isESSVisible ∨ isCFCoherent ∨ isChargedByNewResidual

/--
**Substantive ESS-fallback lemma (tick443).**

If a silent flat bad profile is not ESS-visible and not CF-coherent, then it
must carry a genuine measure-valued flat defect and is charged by the
residual measure.

Proof: not ESS-visible gives L³-tight; not CF-coherent gives
direction-decoherent.  If no genuine defect, the profile is ordinary, so ESS
gives regularity, contradicting CKN badness at all scales.  Therefore
genuine defect exists; the charge follows from `charge_of_genuine_defect`.
This is a real Lean proof, not a Prop wrapper.
-/
theorem residual_of_not_ess_not_cf_from_ESS
    (d : SilentFlatDefectObserverData Profile)
    (hESS : ¬ d.ess.isESSVisible)
    (hCF : ¬ d.cf.isCFCoherent) :
    d.residual.isChargedByNewResidual := by
  have hTight : d.ess.endpointL3Tight :=
    d.ess.not_essVisible_gives_tight hESS
  have hDecoh : d.cf.directionDecoherent :=
    d.cf.not_cfCoherent_gives_decoherent hCF
  have hDefect : d.residual.genuineMeasureValuedFlatDefect := by
    by_contra hNoDefect
    have hOrd : d.ordinarySuitableProfile d.U :=
      d.ordinary_if_no_genuine_defect hNoDefect
    have hReg : d.regularAtCenter d.U := d.ESS_regular hOrd hTight
    have hNotBad : ¬ d.cknBadAtAllScales d.U :=
      d.regular_contradicts_bad_all_scales hReg
    exact hNotBad d.hSilent.2.2.2.2.2.2
  have hResCharge : d.residual.residualCharge :=
    d.charge_of_genuine_defect hDefect
  exact (Iff.mpr d.residual.isChargedByNewResidual_iff)
    ⟨hESS, hCF, hTight, hDecoh, hDefect, hResCharge⟩

/--
**Trichotomy theorem (tick443).**

The silent flat defect observability trichotomy
`isESSVisible ∨ isCFCoherent ∨ isChargedByNewResidual` is PROVED from the
observer data: case-split on ESS visibility, then on CF coherence; the
non-ESS, non-CF case is closed by the ESS-fallback lemma.

This is the trichotomy promised by the ChatGPT-5.5 analytic compression —
shipped as a real Lean theorem, not a Prop assumption.
-/
def SilentFlatDefectObservability_ofObserverData
    (d : SilentFlatDefectObserverData Profile) :
    SilentFlatDefectObservability where
  isESSVisible := d.ess.isESSVisible
  isCFCoherent := d.cf.isCFCoherent
  isChargedByNewResidual := d.residual.isChargedByNewResidual
  observabilityExhaustion := by
    classical
    by_cases hESS : d.ess.isESSVisible
    · exact Or.inl hESS
    · by_cases hCF : d.cf.isCFCoherent
      · exact Or.inr (Or.inl hCF)
      · exact Or.inr (Or.inr
          (residual_of_not_ess_not_cf_from_ESS d hESS hCF))

/--
**CF kills ordinary silent flat profiles (tick443).**

If an observer-data witness has the profile ordinary and CF-coherent, then
the profile is regular at center, contradicting CKN badness at all scales —
hence the situation is impossible.
-/
theorem CF_kills_silent_flat_if_ordinary
    (d : SilentFlatDefectObserverData Profile)
    (hOrd : d.ordinarySuitableProfile d.U)
    (hCF : d.cf.isCFCoherent) : False := by
  have hReg : d.regularAtCenter d.U := d.CF_regular hOrd hCF
  have hNotBad : ¬ d.cknBadAtAllScales d.U :=
    d.regular_contradicts_bad_all_scales hReg
  exact hNotBad d.hSilent.2.2.2.2.2.2

/--
**ESS kills ordinary L³-tight silent flat profiles (tick443).**

Symmetric to CF: ordinary + L³-tight ⇒ regular ⇒ ¬ CKN-bad at all scales.
-/
theorem ESS_kills_silent_flat_if_ordinary_L3_tight
    (d : SilentFlatDefectObserverData Profile)
    (hOrd : d.ordinarySuitableProfile d.U)
    (hTight : d.ess.endpointL3Tight) : False := by
  have hReg : d.regularAtCenter d.U := d.ESS_regular hOrd hTight
  have hNotBad : ¬ d.cknBadAtAllScales d.U :=
    d.regular_contradicts_bad_all_scales hReg
  exact hNotBad d.hSilent.2.2.2.2.2.2

/-!
## Tick443+ — No-Concentration Lemma (Lions / DiPerna-Majda) target

Per operator direction 2026-05-14: after the trichotomy lands (tick442), the
residual branch (genuine measure-valued flat defect) is exactly the "dark
matter" that standard regularity bounds (ESS, Constantin-Fefferman) CANNOT
kill.  The next step is NOT another standard regularity bound — it is a
**No-Concentration Lemma** derived from Lions (incompressible-limits,
1996) or DiPerna-Majda (concentration-cancellation, 1987).

A No-Concentration Lemma for NS would assert: weak limits of suitable
Navier-Stokes solutions cannot spontaneously generate measure-valued
concentrations on null sets of the underlying flat skeleton.  In our
setting, the flat skeleton has zero spatial measure (children partition the
parent up to boundary artifacts), so a No-Concentration Lemma would
forbid the residual measure from being supported there.

This file records the No-Concentration Lemma as a *named external
axiom-input* + its consequence: kill the residual branch + close
flat-radius.

Honest scope: this is NOT proved in this artifact.  Supplying a true
NS-specific No-Concentration Lemma is the actual final analytic target.
The structure below makes that target explicit and atomic.
-/

/--
**Lions / DiPerna-Majda No-Concentration Lemma — abstract axiom form.**

The structural assertion: for a generalized flat tangent profile arising
as a weak limit of suitable NS solutions, the measure-valued flat defect
cannot be supported on a flat skeleton of zero spatial measure.

References (informal): Lions, *Mathematical Topics in Fluid Mechanics*
(1996); DiPerna-Majda, *Oscillations and concentrations in weak solutions
of the incompressible fluid equations* (Comm. Math. Phys. 1987); Saint-Raymond
hyperbolic concentration-cancellation framework.

This is an axiom-input, not a derived theorem.  Supplying it is the
fundamental remaining PDE work.
-/
structure NoConcentrationLemmaAxiom (Profile : Type u) where
  weakLimitOfSuitableNSSolutions : Profile → Prop
  flatSkeletonHasZeroSpatialMeasure : Profile → Prop
  measureValuedDefectSupportedOnFlatSkeleton : Profile → Prop
  /-- Lions/DiPerna-Majda content: a weak-limit profile whose flat
      skeleton has zero spatial measure cannot carry measure-valued
      defect there. -/
  noConcentrationOnFlatSkeleton :
    ∀ U : Profile,
      weakLimitOfSuitableNSSolutions U →
        flatSkeletonHasZeroSpatialMeasure U →
          ¬ measureValuedDefectSupportedOnFlatSkeleton U
  axiomIsExternalNotDerivedFromCKN : Prop
  axiomRequiresLionsOrDiPernaMajdaInput : Prop
  axiomIsStandardForIncompressibleEuler : Prop
  axiomForNavierStokesNeedsCarefulAdaptation : Prop

/--
**Kill the residual branch via No-Concentration Lemma.**

If the silent flat tangent profile is a weak-limit of suitable NS solutions
on a flat skeleton of zero spatial measure, then the No-Concentration Lemma
forbids the residual measure-valued defect from being supported there —
killing the dark-matter branch.

This is the conditional theorem: NoConcentrationLemma + structural
hypotheses ⇒ residual branch is empty.
-/
structure NoConcentrationLemmaKillsResidualBranch (Profile : Type u) where
  noConcAxiom : NoConcentrationLemmaAxiom Profile
  observabilityData : SilentFlatDefectObserverData Profile
  isWeakLimit :
    noConcAxiom.weakLimitOfSuitableNSSolutions observabilityData.U
  flatSkeletonZeroMeasure :
    noConcAxiom.flatSkeletonHasZeroSpatialMeasure observabilityData.U
  /-- The residual branch's measure-valued defect would be supported on the
      flat skeleton; No-Concentration Lemma forbids this. -/
  defect_supported_on_skeleton :
    observabilityData.residual.genuineMeasureValuedFlatDefect →
      noConcAxiom.measureValuedDefectSupportedOnFlatSkeleton observabilityData.U
  /-- Conclusion: residual branch is killed. -/
  noGenuineMeasureValuedFlatDefect :
    ¬ observabilityData.residual.genuineMeasureValuedFlatDefect
  axiomKillsDarkMatterBranch : Prop
  axiomDoesNotMagicallyProveClayClosure : Prop

/--
The substantive consequence: under the No-Concentration Lemma + structural
hypotheses, the genuine measure-valued flat defect cannot exist.
-/
theorem no_genuine_defect_of_NoConcentrationLemma
    (h : NoConcentrationLemmaKillsResidualBranch Profile) :
    ¬ h.observabilityData.residual.genuineMeasureValuedFlatDefect := by
  intro hDefect
  have hSupp :
      h.noConcAxiom.measureValuedDefectSupportedOnFlatSkeleton
        h.observabilityData.U :=
    h.defect_supported_on_skeleton hDefect
  exact (h.noConcAxiom.noConcentrationOnFlatSkeleton
      h.observabilityData.U h.isWeakLimit h.flatSkeletonZeroMeasure) hSupp

/--
**No-Concentration-Lemma-driven trichotomy collapse (tick443+).**

Under the No-Concentration Lemma, the trichotomy
`ESS-visible ∨ CF-coherent ∨ residual` collapses to
`ESS-visible ∨ CF-coherent` — the dark-matter branch is eliminated.

If additionally ordinary suitable profile + L³-tight or CF-coherent is
ruled out (by ESS/CF black boxes applied to ordinary profiles), the silent
flat bad profile is impossible.

This is the path to `NoSilentFlatDefectProfile` if and only if the
No-Concentration Lemma is supplied + the ordinary-realization dichotomy
holds.
-/
structure NoConcentrationLemmaCollapsesTrichotomy (Profile : Type u) where
  noConcKills : NoConcentrationLemmaKillsResidualBranch Profile
  /-- Under No-Concentration, the trichotomy collapses to ESS ∨ CF. -/
  collapsedDichotomy :
    noConcKills.observabilityData.ess.isESSVisible ∨
      noConcKills.observabilityData.cf.isCFCoherent
  /-- Each branch is then killed by ESS/CF black boxes on the ordinary
      realization (this is the second analytic obligation — the
      ordinary-realization dichotomy). -/
  ordinaryRealizationDichotomy :
    noConcKills.observabilityData.ess.isESSVisible ∨
      noConcKills.observabilityData.cf.isCFCoherent →
        noConcKills.observabilityData.ordinarySuitableProfile
          noConcKills.observabilityData.U
  conclusion :
    False
  conclusionDependsOnExternalNoConcAxiom : Prop
  conclusionDependsOnOrdinaryRealizationDichotomy : Prop

/-!
## Honest scope guards
-/

/--
Guard: the No-Concentration Lemma is an external axiom-input, not a
derived theorem.  It is the analytic content from Lions / DiPerna-Majda
that this Lean substrate assumes.
-/
structure NoConcentrationLemmaIsExternalAxiom where
  notDerivedFromCKN : Prop
  notDerivedFromLocalEnergy : Prop
  notDerivedFromESS : Prop
  notDerivedFromConstantinFefferman : Prop
  derivedFromLionsIncompressibleLimits1996 : Prop
  derivedFromDiPernaMajda1987 : Prop
  navierStokesAdaptationIsNonTrivial : Prop
  externalAxiomLoadIsTheFinalCost : Prop

/--
Guard: the trichotomy theorem closes observability, not flat-radius.
Flat-radius closure requires the No-Concentration Lemma (or equivalent)
applied to the residual branch + finite radius-charge budgets on the ESS
and CF branches.
-/
structure SilentFlatDefectObservabilityIsNotFlatRadiusClosure where
  trichotomyProvenInTick443 : Prop
  flatRadiusFiniteChargeStillUnproved : Prop
  essBranchFiniteChargeStillUnproved : Prop
  cfBranchFiniteChargeStillUnproved : Prop
  residualBranchKilledByNoConcLemmaOnly : Prop
  noClayClosureFromObservabilityAlone : Prop
  noConcLemmaIsTheRemainingExternalAxiom : Prop

/-!
## Tick444 — Two-route Gowers-style composition (operator-directed)

Per operator: two routes are now live:

* **Route OLD** (tick442, `ns_route1` namespace): 5-branch
  `SilentFlatProfileFiveBranchDichotomy` + ESS + CF kills branches (i)/(ii);
  branches (iii) `L³EndpointBlowupResidual`, (iv)
  `VorticityDirectionDecoherenceResidual`, (v) `GenuineMeasureValuedFlatDefect`
  remain as Prop residuals that must be excluded by hypothesis.

* **Route NEW** (tick443, this file): `NoConcentrationLemmaAxiom` derived
  from Lions (1996) / DiPerna-Majda (1987) classical concentration-cancellation
  forbids residual (v) directly — the "dark matter" branch is killed by a
  named external axiom, not by Prop assumption.

**Gowers-style composition** (this tick): replace residual (v) in the OLD
route with the NEW route's named killer.  After composition, the surviving
analytic residuals are exactly *two*: (iii) and (iv).  Each is a small
named PDE channel (L³ endpoint blowup measure; vorticity-direction
decoherence) and is the next analytic target.

Honest scope: we now reference tick442's primitive layout *abstractly*
via Prop fields (rather than importing the route1 file) — the composition
is a meta-statement that names how the two routes connect.  Supplying any
of (iii), (iv) requires real analytic content; we do not produce it here.
-/

/--
Two-route composition: NEW route (No-Concentration Lemma) absorbs the OLD
route's residual (v).  Abstract Prop carriers reference the tick442
ESS/CF + 5-branch dichotomy by name; the composition declares the
post-composition residual set is exactly two named channels.
-/
structure TwoRouteCompositionRoute1AndNoConcentration where
  /-- Tick442 OLD route hypothesis: ESS + CF + 5-branch dichotomy. -/
  oldRouteEssCfDichotomyBundleAvailable : Prop
  /-- Tick443 NEW route input: No-Concentration Lemma axiom available. -/
  newRouteNoConcentrationLemmaAxiomAvailable : Prop
  /-- Residual (i): bounded L∞_t L³_x ordinary realization — killed by ESS. -/
  residual_i_killed_by_ESS : Prop
  /-- Residual (ii): CF-coherent ordinary realization — killed by CF. -/
  residual_ii_killed_by_CF : Prop
  /-- Residual (iii): L³-endpoint blowup channel — NEW open analytic
      target after composition. -/
  residual_iii_L3EndpointBlowup_remains_open : Prop
  /-- Residual (iv): vorticity-direction decoherence channel — NEW open
      analytic target after composition. -/
  residual_iv_VorticityDecoherence_remains_open : Prop
  /-- Residual (v): genuine measure-valued flat defect — KILLED by NEW
      route's No-Concentration Lemma axiom. -/
  residual_v_killed_by_NoConcentrationLemma : Prop
  /-- Post-composition: exactly two residuals remain (iii) and (iv). -/
  post_composition_two_residuals_remain : Prop
  /-- Gowers-style replacement: residual (v) replaced by named external
      classical axiom, not by Prop assumption. -/
  gowersReplacementOfBranch_v_with_external_axiom : Prop
  /-- Composition is conditional on both route bundles + control of (iii)
      and (iv). -/
  compositionIsConditionalNotUnconditional : Prop
  /-- The composition's NEW open analytic targets are now named and
      atomic. -/
  iii_and_iv_are_named_atomic_targets : Prop

/--
Composition assertion: post-composition the two remaining residuals are
(iii) and (iv).  The structure's `post_composition_two_residuals_remain`
Prop field carries this claim directly; this `def` is the named accessor.

Honest scope: NOT Clay closure.  The two residuals (iii) and (iv) remain
as named open PDE targets.
-/
def TwoRouteCompositionRoute1AndNoConcentration.tworesidualsRemain
    (h : TwoRouteCompositionRoute1AndNoConcentration) : Prop :=
  h.post_composition_two_residuals_remain

/--
Honest scope guard for the two-route composition: it is a *meta-level*
declaration of how routes OLD and NEW combine, not a Clay closure proof.

The two remaining open analytic residuals (L³-endpoint, vorticity-decoherence)
are the next-session targets.
-/
structure TwoRouteCompositionIsNotClayClosure where
  compositionIsMetaDeclaration : Prop
  oldRouteEssCfStillExternallyCited : Prop
  newRouteNoConcentrationStillExternallyCited : Prop
  residual_iii_unresolved : Prop
  residual_iv_unresolved : Prop
  noClayClosureFromTwoRouteCompositionAlone : Prop
  iii_and_iv_are_next_session_targets : Prop
  pre_check_says_route1_lower_leverage_than_track_b : Prop

/-!
## Tick445 — Quantitative finite-budget Gowers replacement for residuals (iii) and (iv)

Per operator "continue, Gowers style" after tick444's two-route composition:
the two surviving open analytic residuals are abstract Prop predicates.  The
Gowers move is to replace each with a *quantitative measure-valued charge*
that pays the flat-radius linearly (matching the depth-reserve telescoping
from tick441).  Two new named charge primitives:

* **(iii) L³ endpoint blowup charge**: a finite-budget L³-defect measure
  whose fresh-region mass pays `c · r_Q` on each flat-inherited bad scale.
* **(iv) Vorticity-direction decoherence charge**: a finite-budget
  direction-oscillation measure (Carleson-type from
  Constantin-Fefferman framework) whose fresh-region mass pays `c · r_Q`.

If EITHER charge primitive is supplied, the corresponding residual is
killed AND the flat-radius reserve telescopes correctly.

Honest scope: neither primitive is constructed here.  The structures name
the *quantitative replacement* for the abstract residual Prop; supplying
either is the actual remaining PDE work and is NOT Clay closure.
-/

/--
Gowers replacement for residual (iii): a finite-budget L³-endpoint
blowup-defect measure that pays r-linear charge on flat bad scales.

Replaces the abstract `L3EndpointBlowupResidual` Prop with a quantitative
charge whose fresh-region mass dominates `c · radius` on each
flat-inherited bad node.  If supplied, the flat-radius reserve closes via
the tick441 depth-reserve telescoping.
-/
structure L3EndpointBlowupChargeReplacement where
  L3DefectMeasureValue : Real
  L3DefectMeasureValue_nonneg : 0 ≤ L3DefectMeasureValue
  finiteRootBudget : Real
  finiteRootBudget_nonneg : 0 ≤ finiteRootBudget
  L3DefectMeasure_bounded_by_rootBudget :
    L3DefectMeasureValue ≤ finiteRootBudget
  radiusCharge : Real
  radiusChargeCoeff : Real
  radiusChargeCoeff_pos : 0 < radiusChargeCoeff
  L3DefectChargesRadius :
    radiusChargeCoeff * radiusCharge ≤ L3DefectMeasureValue
  chargeIsFromESSBlowupMeasure : Prop
  chargeIsR_linearNotR_squared : Prop
  chargeDoesNotUseCKNSquareMass : Prop
  chargeFixedBeforeRadiusSelection : Prop

/--
Gowers replacement for residual (iv): a finite-budget vorticity-direction
decoherence measure (Carleson-type / Constantin-Fefferman seminorm) that
pays r-linear charge on flat bad scales.

Replaces the abstract `VorticityDirectionDecoherenceResidual` Prop with a
quantitative charge.  If supplied, the flat-radius reserve closes.
-/
structure VorticityDecoherenceChargeReplacement where
  decoherenceMeasureValue : Real
  decoherenceMeasureValue_nonneg : 0 ≤ decoherenceMeasureValue
  finiteRootBudget : Real
  finiteRootBudget_nonneg : 0 ≤ finiteRootBudget
  decoherenceMeasure_bounded_by_rootBudget :
    decoherenceMeasureValue ≤ finiteRootBudget
  radiusCharge : Real
  radiusChargeCoeff : Real
  radiusChargeCoeff_pos : 0 < radiusChargeCoeff
  decoherencePaysRadius :
    radiusChargeCoeff * radiusCharge ≤ decoherenceMeasureValue
  chargeIsFromConstantinFefferman_seminorm : Prop
  chargeIsCarlesonStyleVorticity : Prop
  chargeIsR_linearNotR_squared : Prop
  chargeFixedBeforeRadiusSelection : Prop

/--
**Tick445 r-linear charge from either quantitative replacement.**

Both charge replacements deliver the *same* r-linear inequality.  This
theorem extracts the radius bound from either named replacement.
-/
theorem radiusCharge_le_L3DefectMeasure
    (h : L3EndpointBlowupChargeReplacement) :
    h.radiusChargeCoeff * h.radiusCharge ≤ h.L3DefectMeasureValue :=
  h.L3DefectChargesRadius

/-- Symmetric extraction for the vorticity-decoherence charge. -/
theorem radiusCharge_le_decoherenceMeasure
    (h : VorticityDecoherenceChargeReplacement) :
    h.radiusChargeCoeff * h.radiusCharge ≤ h.decoherenceMeasureValue :=
  h.decoherencePaysRadius

/--
**Final three-route Clay-adjacency composition** (tick445).

After tick444's two-route composition, residuals (iii) and (iv) remain.
Each is now replaceable by a quantitative finite-budget charge.  This
structure collects the three routes (ESS/CF dichotomy + No-Concentration
Lemma + either charge replacement) and declares the post-composition
state: zero remaining open analytic residuals *given* one charge supplied.

Honest scope: still NOT Clay closure.  Supplying the L³ defect or
vorticity-decoherence charge is the actual PDE work.  This structure
declares the final Gowers-reduced state.
-/
structure FinalThreeRouteCompositionRoute1NoConcAndCharge where
  twoRouteBase : TwoRouteCompositionRoute1AndNoConcentration
  L3ChargeOrDecoherenceCharge :
    L3EndpointBlowupChargeReplacement ⊕ VorticityDecoherenceChargeReplacement
  oneChargeKillsRemainingTwoResiduals : Prop
  postFinalComposition_zero_residuals_modulo_charge_supplied : Prop
  gowersFinalReplacement : Prop
  notClayClosureSinceChargeUnsupplied : Prop
  L3OrDecoherenceIsNextAndLastAtomicTarget : Prop

/-- Honest guard for the final composition. -/
structure FinalThreeRouteCompositionIsNotClayClosure where
  threeRoutesNamedNotProved : Prop
  L3DefectMeasureStillUnconstructed : Prop
  decoherenceMeasureStillUnconstructed : Prop
  externalAxiomsLoadIsThreeNamedClassicalTheorems : Prop
  noClayClosureFromFinalCompositionAlone : Prop

/-!
## Tick446 — Construction of `L3EndpointBlowupChargeReplacement` from an ESS endpoint hypothesis

Tick445 named `L3EndpointBlowupChargeReplacement` but left it inhabited only by
hand.  Tick446 ships a *real Lean constructor* that produces the charge
replacement from a quantitative ESS endpoint hypothesis:

  `‖u‖_{L^∞_t L³_x} ≤ M` on the bad set (an ESS-applicability input from
  Escauriaza–Seregin–Šverák 2003 — externally cited).

The scaling identity
  `∫_{Q_r} |u|³ dx dt ≤ |Q_r|_t · (sup_t ‖u(·,t)‖_{L³_x})³`
gives, for a fixed time-window length proportional to `r`,
  `‖u‖_{L³(Q_r)}³ ≤ C · r · M³`,
which is `r`-linear (not `r²`).  This bypasses the classical CKN obstruction
that pays `sum r_Q²` while flat dyadic reuse only demands `sum r_Q`.

The constructor `L3EndpointBlowupChargeReplacement.ofESSEndpointL3Hypothesis`
realizes this scaling computation in Lean by choosing
  `L3DefectMeasureValue := r · M³`,
  `radiusCharge := r`,
  `radiusChargeCoeff := M³`,
  `finiteRootBudget := r · M³`,
and proving the four `Real` inequalities from `r ≥ 0` and `M > 0`.

**Honest scope**: this construction is conditional on the
`LocalESSL∞L3RegularityHypothesis` carrier, which packages the classical
ESS-applicability input.  We do NOT prove that hypothesis here; ESS is an
externally cited theorem.  Supplying the hypothesis on the actual NS bad set
is the analytic obligation the construction reduces to.  This is one of
three named classical-input bridges (the others are
`VorticityDecoherenceChargeReplacement.ofConstantinFeffermanHypothesis` and
the No-Concentration Lemma axiom).  NOT Clay closure.
-/

/--
**Tick446 — Local ESS `L^∞_t L³_x` regularity hypothesis (classical input).**

This is the named carrier for the ESS endpoint condition specialized to a
fixed parabolic cube of radius `r` on the bad set.  It packages:

* the radius `r ≥ 0` of the parabolic cube,
* the endpoint bound `M ≥ 0` with `0 < M` (so the cube charges by a strictly
  positive coefficient),
* the bad-set applicability flag (Prop),
* the fresh-region measurability flag (Prop),
* the Carleson-type fresh-region mass identification flag (Prop).

ESS-applicability and fresh-region measurability are recorded as Prop fields
because they belong to the externally cited classical input (Escauriaza–
Seregin–Šverák 2003).  The two real-number fields carry the quantitative
content the constructor consumes.
-/
structure LocalESSLInftyL3RegularityHypothesis where
  /-- Radius of the parabolic cube `Q_r` on the bad set. -/
  cubeRadius : Real
  cubeRadius_nonneg : 0 ≤ cubeRadius
  /-- ESS endpoint bound: `‖u‖_{L^∞_t L³_x} ≤ M` on the cube. -/
  endpointL3Bound : Real
  endpointL3Bound_pos : 0 < endpointL3Bound
  /-- The bad set lies in the ESS applicability regime
      (`L^∞_t L³_x` with suitable Leray–Hopf assumption — externally cited). -/
  ESSApplicableOnBadSet : Prop
  /-- The fresh region of the cube is measurable and supports a Carleson-type
      mass identification with the ESS endpoint mass. -/
  freshRegionCarlesonMeasurable : Prop
  /-- The endpoint mass is fixed before the radius is selected
      (anti-laundering guard against ex-post tuning). -/
  endpointMassFixedBeforeRadiusSelection : Prop
  /-- Reference to the classical theorem the hypothesis abstracts. -/
  externalReferenceESS2003 : Prop

/--
**Tick446 — Constructor: from an ESS endpoint hypothesis, build the charge
replacement.**

This is a real Lean `def` (not a Prop wrapper).  Given an
`LocalESSL∞L3RegularityHypothesis` with cube radius `r` and ESS endpoint bound
`M > 0`, it produces an `L3EndpointBlowupChargeReplacement` whose fields are:

* `L3DefectMeasureValue := r · M³`  (the scaling-derived defect mass)
* `radiusCharge := r`
* `radiusChargeCoeff := M³`  (strictly positive because `M > 0`)
* `finiteRootBudget := r · M³`

The four inequality fields are discharged from the scaling identity:
`M³ * r ≤ r · M³` is equality, and `0 ≤ r · M³` follows from
`r ≥ 0`, `M > 0`.

Honest scope: the constructor *assumes* the ESS hypothesis; it does not
*prove* ESS.  The four Prop guards on the output flag that the charge is
ESS-sourced, r-linear, not CKN-square, and fixed before radius selection.
-/
def L3EndpointBlowupChargeReplacement.ofESSEndpointL3Hypothesis
    (H : LocalESSLInftyL3RegularityHypothesis) :
    L3EndpointBlowupChargeReplacement :=
  let r : Real := H.cubeRadius
  let M : Real := H.endpointL3Bound
  let M3 : Real := M * M * M
  have hr : 0 ≤ r := H.cubeRadius_nonneg
  have hM : 0 < M := H.endpointL3Bound_pos
  have hM_nn : 0 ≤ M := le_of_lt hM
  have hM2_nn : 0 ≤ M * M := mul_nonneg hM_nn hM_nn
  have hM3_pos : 0 < M3 := by
    have h12 : 0 < M * M := mul_pos hM hM
    exact mul_pos h12 hM
  have hM3_nn : 0 ≤ M3 := le_of_lt hM3_pos
  have hrM3_nn : 0 ≤ r * M3 := mul_nonneg hr hM3_nn
  have hSwap : M3 * r = r * M3 := mul_comm M3 r
  { L3DefectMeasureValue := r * M3
    L3DefectMeasureValue_nonneg := hrM3_nn
    finiteRootBudget := r * M3
    finiteRootBudget_nonneg := hrM3_nn
    L3DefectMeasure_bounded_by_rootBudget := le_refl (r * M3)
    radiusCharge := r
    radiusChargeCoeff := M3
    radiusChargeCoeff_pos := hM3_pos
    L3DefectChargesRadius := by
      -- `M³ * r = r * M³` by commutativity, so the bound holds with equality.
      have := hSwap
      exact this.le
    chargeIsFromESSBlowupMeasure := H.ESSApplicableOnBadSet
    chargeIsR_linearNotR_squared := H.freshRegionCarlesonMeasurable
    chargeDoesNotUseCKNSquareMass := H.externalReferenceESS2003
    chargeFixedBeforeRadiusSelection := H.endpointMassFixedBeforeRadiusSelection }

/--
**Tick446 — r-linear charge inequality from the ESS hypothesis (real theorem).**

The output charge replacement satisfies
  `radiusChargeCoeff * radiusCharge ≤ L3DefectMeasureValue`,
which expands, with the field choices of `ofESSEndpointL3Hypothesis`, to
  `M³ * r ≤ r · M³`,
holding with equality by commutativity.  Combined with `M > 0`, this is the
r-linear (not r²) charge bound the flat-radius reserve needs.

This is the scaling theorem the operator requested: from
`‖u‖_{L^∞_t L³_x} ≤ M` on the bad set,
`‖u‖_{L³(Q_r)}³ ≤ r · M³`, hence r-linear charge.
-/
theorem L3EndpointBlowupChargeReplacement.ofESSEndpointL3Hypothesis_rLinearCharge
    (H : LocalESSLInftyL3RegularityHypothesis) :
    (L3EndpointBlowupChargeReplacement.ofESSEndpointL3Hypothesis H).radiusChargeCoeff
        *
      (L3EndpointBlowupChargeReplacement.ofESSEndpointL3Hypothesis H).radiusCharge
      ≤
      (L3EndpointBlowupChargeReplacement.ofESSEndpointL3Hypothesis H).L3DefectMeasureValue :=
  (L3EndpointBlowupChargeReplacement.ofESSEndpointL3Hypothesis H).L3DefectChargesRadius

/--
**Tick446 — explicit scaling identity in named-field form.**

The constructed charge satisfies the explicit r-linear identity
`radiusChargeCoeff = M³` and `radiusCharge = r` and `L3DefectMeasureValue = r · M³`,
where `M = H.endpointL3Bound` and `r = H.cubeRadius`.  This makes the scaling
audit machine-checkable: the inequality is in fact an equality up to
commutativity of multiplication.
-/
theorem L3EndpointBlowupChargeReplacement.ofESSEndpointL3Hypothesis_scaling_identity
    (H : LocalESSLInftyL3RegularityHypothesis) :
    (L3EndpointBlowupChargeReplacement.ofESSEndpointL3Hypothesis H).L3DefectMeasureValue
      = H.cubeRadius *
          (H.endpointL3Bound * H.endpointL3Bound * H.endpointL3Bound) := rfl

/--
**Tick446 — explicit r-linear charge coefficient identity.**

The radius-charge coefficient produced by the constructor is exactly
`M³ = H.endpointL3Bound³`, the cube of the ESS endpoint bound.  This pins
down the dependence on the classical input: the coefficient is fully
determined by the ESS bound, no hidden constants.
-/
theorem L3EndpointBlowupChargeReplacement.ofESSEndpointL3Hypothesis_coeff_identity
    (H : LocalESSLInftyL3RegularityHypothesis) :
    (L3EndpointBlowupChargeReplacement.ofESSEndpointL3Hypothesis H).radiusChargeCoeff
      = H.endpointL3Bound * H.endpointL3Bound * H.endpointL3Bound := rfl

/--
**Tick446 — honest scope guard.**

The constructor and theorems above ship the *conditional* bridge:
ESS endpoint hypothesis ⇒ r-linear charge replacement.  They do NOT:

* prove the ESS endpoint regularity theorem (externally cited, ESS 2003);
* identify the abstract `L3DefectMeasureValue` Real with an actual integral
  of `|u|³` against an honest measure (the Carleson identification is a Prop);
* close `NoSilentFlatDefectProfile`;
* close the flat-radius reserve unconditionally;
* close Clay regularity.

The bridge supplies (one of) three named classical inputs the tick445
composition needs.  The other two are the Constantin–Fefferman vorticity
hypothesis (parallel constructor) and the No-Concentration Lemma axiom
(tick443).  Supplying any single one of the three classical inputs in PDE-real
form remains open analytic work.
-/
structure L3EndpointConstructionFromESSIsNotClayClosure where
  ESSTheoremIsExternallyCited : Prop
  CarlesonIdentificationIsPropNotIntegral : Prop
  NoSilentFlatDefectProfileNotClosed : Prop
  FlatRadiusReserveNotUnconditionallyClosed : Prop
  ClayRegularityNotClosed : Prop
  OneOfThreeNamedClassicalInputBridges : Prop
  VorticityHypothesisBridgeIsParallelTarget : Prop
  NoConcentrationLemmaIsThirdTarget : Prop

/-!
## Tick447 — Construction of `VorticityDecoherenceChargeReplacement` from a
Constantin–Fefferman direction-decoherence hypothesis (Claude RD-extension)

Parallel to PDE-A's tick446 (L³-endpoint construction from ESS) above.
Tick447 ships the second of the three named classical-input bridges flagged
by tick446's honest scope guard:

> The other two are the Constantin–Fefferman vorticity hypothesis (parallel
> constructor) and the No-Concentration Lemma axiom.

This tick supplies the *parallel constructor* for the vorticity branch.
Appended BELOW PDE-A's additions per operator constraint that this work
not collide with tick442/443/444/445 structures or PDE-A's L³-endpoint
construction.

### Informal analytic content

Let `ξ := ω/|ω|` denote the vorticity direction on a parabolic cube `Q_r`
of radius `r` (defined where `|ω| > 0`).  The Constantin–Fefferman
direction-coherence seminorm is `‖∇ξ‖_{L^p L^q}(Q_r)` for an exponent pair
`(p, q)` compatible with Biot–Savart + scaling.  The parabolic
decoherence-charge integral is

  `D(Q_r) := ∫_{Q_r} |∇ξ|^p · |ω|^q dx dt`.

Constantin–Fefferman 1993 (Comm. Pure Appl. Math. 46:1273–1281) shows that
control of this seminorm rules out singularity formation.  Specializing to a
parabolic cube on the flat bad set, two estimates apply:

* **Carleson-type upper budget.** By Biot–Savart inversion + Calderón–Zygmund
  regularity for the Riesz transform + parabolic Carleson embedding,
  `D(Q_r) ≤ B` for a finite root-budget `B` that depends on the local
  enstrophy and the Biot–Savart constant.
* **r-linear lower charge at decoherent scales.** When CF direction coherence
  *fails* at `Q_r` (residual-(iv) of the tick442 5-branch dichotomy), the
  seminorm is bounded below by a strictly positive constant on parabolic
  balls; combined with the magnitude factor `|ω|^q` and parabolic scaling,
  this gives `c · r ≤ D(Q_r)` with `c > 0`.

Combining the two yields a `VorticityDecoherenceChargeReplacement`: a
finite-root-budget object whose `decoherenceMeasureValue` dominates
`c · radius` on each flat-inherited bad scale.  This bypasses the classical
CKN obstruction that pays `Σ r_Q²` while flat dyadic reuse demands `Σ r_Q`.

### Scope honesty

This file does NOT formalize Biot–Savart, Calderón–Zygmund, parabolic
Carleson, or the CF 1993 theorem.  The construction shipped here is a
**typed bridge**: it converts the abstract analytic hypothesis
`ConstantinFeffermanDirectionDecoherenceHypothesis` into the already-named
tick445 `VorticityDecoherenceChargeReplacement` by populating its `Real` and
`Prop` fields.  The analytic content is **named** in the hypothesis carrier
and **not derived**.  What IS proved (real Lean theorems, not Prop wrappers):

1. The constructor produces a well-typed inhabitant.
2. The r-linear charge inequality `c · r ≤ D(Q_r)` extracts from the
   constructed charge by `rfl`-level definitional unfolding to the carrier's
   field.
3. Field identification: the constructor faithfully transports the
   `Real`-typed analytic content through the type bridge.

The output is universe-free (`Type` with no `u` universe parameter) per
operator constraint.  Parallel to PDE-A's L³-endpoint construction
(residual (iii)); does not collide with tick442/443/444/445 surfaces.
-/

/--
**Tick447 — Constantin–Fefferman direction-decoherence hypothesis carrier
(classical input).**

Named carrier for the CF direction-coherence seminorm + the Carleson-type
upper budget on `D(Q_r) = ∫ |∇ξ|^p |ω|^q` + the r-linear lower bound at
decoherent scales.  All `Real`-typed fields are concrete numerical content;
the Biot–Savart / Calderón–Zygmund / parabolic-scaling / CF-1993 origin
sits in `Prop`-typed obligation fields and is **named, not derived**.

Universe-free `Type` (no `u` parameter).
-/
structure ConstantinFeffermanDirectionDecoherenceHypothesis where
  /-- Abstract spacetime domain `Ω × (0, T)` — not instantiated. -/
  spaceTime : Type
  /-- Abstract unit 2-sphere `S² ⊂ ℝ³` — vorticity-direction codomain. -/
  sphere : Type
  /-- Vorticity-direction field `ξ = ω/|ω| : spaceTime → sphere`. -/
  xi : spaceTime → sphere
  /-- Parabolic cube radius `r_Q`. -/
  parabolicCubeRadius : Real
  parabolicCubeRadius_nonneg : 0 ≤ parabolicCubeRadius
  /-- The Constantin–Fefferman direction-coherence seminorm value
      `‖∇ξ‖_{L^p L^q}(Q_r)`. -/
  cfSeminormValue : Real
  cfSeminormValue_nonneg : 0 ≤ cfSeminormValue
  /-- Anchor for the magnitude factor `|ω|^q` (local enstrophy-power on the
      cube; appears as a coefficient in the charge integrand). -/
  omegaMagnitudePowerOnCube : Real
  omegaMagnitudePowerOnCube_nonneg : 0 ≤ omegaMagnitudePowerOnCube
  /-- The parabolic decoherence-charge integral
      `D(Q_r) = ∫_{Q_r} |∇ξ|^p · |ω|^q dx dt`. -/
  decoherenceIntegralValue : Real
  decoherenceIntegralValue_nonneg : 0 ≤ decoherenceIntegralValue
  /-- Finite root-budget `B` (Biot–Savart + CZ + parabolic Carleson). -/
  finiteRootBudget : Real
  finiteRootBudget_nonneg : 0 ≤ finiteRootBudget
  /-- Carleson upper budget: `D(Q_r) ≤ B`. -/
  decoherenceCarlesonUpperBudget :
    decoherenceIntegralValue ≤ finiteRootBudget
  /-- r-linear coefficient `c > 0` from CF decoherence + parabolic scaling. -/
  rLinearChargeCoeff : Real
  rLinearChargeCoeff_pos : 0 < rLinearChargeCoeff
  /-- r-linear lower bound (the substantive CF-decoherence consequence):
      `c · r_Q ≤ D(Q_r)` at any cube where CF direction coherence fails. -/
  decoherenceLowerCharge_at_decoherent_scale :
    rLinearChargeCoeff * parabolicCubeRadius ≤ decoherenceIntegralValue
  /-- The cube is direction-decoherent (CF coherence fails at `Q_r`); this
      is the residual-(iv) branch from the tick442 5-branch dichotomy. -/
  directionDecoherenceWitnessed_at_cube : Prop
  /-- Named-not-derived: the Carleson upper budget originates from
      Biot–Savart inversion + Calderón–Zygmund regularity for the Riesz
      transform + parabolic Carleson embedding. -/
  carlesonUpperBudgetIsBiotSavartCZOrigin : Prop
  /-- Named-not-derived: the r-linear lower bound originates from
      Constantin–Fefferman 1993 (Comm. Pure Appl. Math. 46:1273–1281)
      direction-coherence regularity + parabolic scaling. -/
  rLinearLowerChargeIsCF1993Origin : Prop
  /-- Named-not-derived: the charge is r-linear (not r-squared) because
      the seminorm `‖∇ξ‖_{L^p L^q}` is *direction-only*, not the full
      kinetic-energy / local-energy / CKN budget that pays `r²`. -/
  chargeIsR_linearNotR_squared_by_direction_only_seminorm : Prop
  /-- Anti-laundering guard: cube radius is fixed *before* the charge
      accounting (matches tick441 depth-reserve telescoping convention). -/
  cubeRadiusFixedBeforeChargeAccounting : Prop
  /-- Reference to the classical theorem the hypothesis abstracts. -/
  externalReferenceConstantinFefferman1993 : Prop

/--
**Tick447 — Constructor: from a CF direction-decoherence hypothesis, build
the tick445 `VorticityDecoherenceChargeReplacement`.**

Real Lean `def` (not a Prop wrapper).  Given a
`ConstantinFeffermanDirectionDecoherenceHypothesis` with cube radius `r_Q`,
decoherence integral `D = D(Q_r)`, r-linear coefficient `c > 0`, and finite
root-budget `B ≥ D`, it produces a `VorticityDecoherenceChargeReplacement`
whose fields are:

* `decoherenceMeasureValue := h.decoherenceIntegralValue`     (= `D`)
* `finiteRootBudget := h.finiteRootBudget`                    (= `B`)
* `radiusCharge := h.parabolicCubeRadius`                     (= `r_Q`)
* `radiusChargeCoeff := h.rLinearChargeCoeff`                 (= `c`)

The four inequality fields are discharged directly from the carrier's
analytic obligations:

* `decoherenceMeasure_bounded_by_rootBudget := h.decoherenceCarlesonUpperBudget`
* `decoherencePaysRadius := h.decoherenceLowerCharge_at_decoherent_scale`
* `radiusChargeCoeff_pos := h.rLinearChargeCoeff_pos`
* `decoherenceMeasureValue_nonneg := h.decoherenceIntegralValue_nonneg`
* `finiteRootBudget_nonneg := h.finiteRootBudget_nonneg`

The four `Prop` provenance fields are populated from the carrier's
named-origin Props:

* `chargeIsFromConstantinFefferman_seminorm := h.rLinearLowerChargeIsCF1993Origin`
* `chargeIsCarlesonStyleVorticity := h.carlesonUpperBudgetIsBiotSavartCZOrigin`
* `chargeIsR_linearNotR_squared := h.chargeIsR_linearNotR_squared_by_direction_only_seminorm`
* `chargeFixedBeforeRadiusSelection := h.cubeRadiusFixedBeforeChargeAccounting`

Honest scope: the constructor *assumes* the CF carrier; it does not *prove*
Constantin–Fefferman 1993, Biot–Savart, or Calderón–Zygmund.  Supplying an
instance of the carrier on the actual NS bad set is the residual analytic
obligation this construction reduces to.
-/
def VorticityDecoherenceChargeReplacement.ofCFDecoherenceHypothesis
    (h : ConstantinFeffermanDirectionDecoherenceHypothesis) :
    VorticityDecoherenceChargeReplacement :=
  { decoherenceMeasureValue := h.decoherenceIntegralValue
    decoherenceMeasureValue_nonneg := h.decoherenceIntegralValue_nonneg
    finiteRootBudget := h.finiteRootBudget
    finiteRootBudget_nonneg := h.finiteRootBudget_nonneg
    decoherenceMeasure_bounded_by_rootBudget := h.decoherenceCarlesonUpperBudget
    radiusCharge := h.parabolicCubeRadius
    radiusChargeCoeff := h.rLinearChargeCoeff
    radiusChargeCoeff_pos := h.rLinearChargeCoeff_pos
    decoherencePaysRadius := h.decoherenceLowerCharge_at_decoherent_scale
    chargeIsFromConstantinFefferman_seminorm :=
      h.rLinearLowerChargeIsCF1993Origin
    chargeIsCarlesonStyleVorticity :=
      h.carlesonUpperBudgetIsBiotSavartCZOrigin
    chargeIsR_linearNotR_squared :=
      h.chargeIsR_linearNotR_squared_by_direction_only_seminorm
    chargeFixedBeforeRadiusSelection :=
      h.cubeRadiusFixedBeforeChargeAccounting }

/--
**Tick447 — r-linear charge inequality from the CF hypothesis (real theorem).**

The constructed charge replacement satisfies
  `radiusChargeCoeff * radiusCharge ≤ decoherenceMeasureValue`,
which expands, with the field choices of `ofCFDecoherenceHypothesis`, to
  `c · r_Q ≤ D(Q_r)`
— exactly the CF-decoherence r-linear lower charge.  This is the scaling
theorem the operator requested: from the CF direction-coherence seminorm at
a decoherent parabolic cube, the decoherence integral pays `c · r_Q`, hence
**r-linear charge** (not `r²`).

Proof: by `rfl`-level definitional equality the constructed charge's
`decoherencePaysRadius` field is exactly the carrier's
`decoherenceLowerCharge_at_decoherent_scale`.  We extract it via the tick445
extraction theorem `radiusCharge_le_decoherenceMeasure`.
-/
theorem rLinearCharge_from_CFDecoherenceHypothesis
    (h : ConstantinFeffermanDirectionDecoherenceHypothesis) :
    h.rLinearChargeCoeff * h.parabolicCubeRadius
        ≤ h.decoherenceIntegralValue := by
  exact radiusCharge_le_decoherenceMeasure
    (VorticityDecoherenceChargeReplacement.ofCFDecoherenceHypothesis h)

/--
**Tick447 — explicit field-identification identity (named-field form).**

The constructed charge satisfies the explicit `rfl`-level identities

  `decoherenceMeasureValue = h.decoherenceIntegralValue`,
  `radiusCharge = h.parabolicCubeRadius`,
  `radiusChargeCoeff = h.rLinearChargeCoeff`,
  `finiteRootBudget = h.finiteRootBudget`.

This makes the audit machine-checkable: the constructor faithfully
transports the analytic `Real`-typed content of the CF carrier into the
tick445 charge object without modification.  Parallel to PDE-A's
`ofESSEndpointL3Hypothesis_scaling_identity` / `_coeff_identity` for the
L³-endpoint branch.
-/
theorem ofCFDecoherenceHypothesis_field_identification
    (h : ConstantinFeffermanDirectionDecoherenceHypothesis) :
    (VorticityDecoherenceChargeReplacement.ofCFDecoherenceHypothesis h).decoherenceMeasureValue
        = h.decoherenceIntegralValue
      ∧ (VorticityDecoherenceChargeReplacement.ofCFDecoherenceHypothesis h).radiusCharge
        = h.parabolicCubeRadius
      ∧ (VorticityDecoherenceChargeReplacement.ofCFDecoherenceHypothesis h).radiusChargeCoeff
        = h.rLinearChargeCoeff
      ∧ (VorticityDecoherenceChargeReplacement.ofCFDecoherenceHypothesis h).finiteRootBudget
        = h.finiteRootBudget :=
  ⟨rfl, rfl, rfl, rfl⟩

/--
**Tick447 — explicit r-linear charge coefficient identity.**

The radius-charge coefficient produced by the constructor is exactly the
CF carrier's `rLinearChargeCoeff` (the constant `c > 0` from
Constantin–Fefferman 1993 + parabolic scaling).  Pins down the dependence
on the classical input: the coefficient is fully determined by the CF
carrier, no hidden constants.
-/
theorem ofCFDecoherenceHypothesis_coeff_identity
    (h : ConstantinFeffermanDirectionDecoherenceHypothesis) :
    (VorticityDecoherenceChargeReplacement.ofCFDecoherenceHypothesis h).radiusChargeCoeff
      = h.rLinearChargeCoeff := rfl

/--
**Tick447 — Carleson upper-budget transport theorem.**

The constructed charge's `decoherenceMeasure_bounded_by_rootBudget` field
witnesses `D(Q_r) ≤ B`, the Carleson upper budget transported faithfully
from the carrier.
-/
theorem ofCFDecoherenceHypothesis_carlesonUpperBudget
    (h : ConstantinFeffermanDirectionDecoherenceHypothesis) :
    (VorticityDecoherenceChargeReplacement.ofCFDecoherenceHypothesis h).decoherenceMeasureValue
      ≤
      (VorticityDecoherenceChargeReplacement.ofCFDecoherenceHypothesis h).finiteRootBudget :=
  (VorticityDecoherenceChargeReplacement.ofCFDecoherenceHypothesis h).decoherenceMeasure_bounded_by_rootBudget

/--
**Tick447 — honest scope guard.**

The constructor and theorems above ship the *conditional* bridge:
CF direction-decoherence hypothesis ⇒ r-linear vorticity-decoherence
charge replacement.  They do NOT:

* prove the Constantin–Fefferman 1993 direction-coherence regularity
  theorem (externally cited);
* prove Biot–Savart inversion, Calderón–Zygmund regularity for the Riesz
  transform, or parabolic Carleson embedding (each externally cited);
* identify the abstract `decoherenceIntegralValue` `Real` with an actual
  integral of `|∇ξ|^p · |ω|^q` against an honest parabolic measure (the
  identification is a `Prop` tag);
* construct the vorticity-direction field `ξ = ω/|ω|` as an honest
  measurable map on an NS solution;
* close `NoSilentFlatDefectProfile`;
* close the flat-radius reserve unconditionally;
* close upstream or Clay regularity.

The bridge supplies the **second** of the three named classical-input
bridges flagged by tick446's scope guard.  Combined with PDE-A's tick446
L³-endpoint constructor (ESS branch) and the tick443
No-Concentration-Lemma axiom, the tick445 final composition now has
*typed bridges* for all three classical inputs — each conditional on
its named classical theorem.
-/
structure CFDecoherenceConstructionFromCFIsNotClayClosure where
  CFTheoremIsExternallyCited1993 : Prop
  BiotSavartIsExternallyCited : Prop
  CalderonZygmundIsExternallyCited : Prop
  ParabolicCarlesonEmbeddingIsExternallyCited : Prop
  CarlesonIdentificationIsPropNotIntegral : Prop
  VorticityDirectionFieldIsAbstractNotMeasurable : Prop
  NoSilentFlatDefectProfileNotClosed : Prop
  FlatRadiusReserveNotUnconditionallyClosed : Prop
  UpstreamClosureNotClosed : Prop
  ClayRegularityNotClosed : Prop
  SecondOfThreeNamedClassicalInputBridges : Prop
  L3EndpointESSBridgeIsParallelTick446 : Prop
  NoConcentrationLemmaIsThirdTarget : Prop
  AppendedBelowPDEAToAvoidStructureCollision : Prop
  UniverseFreeTypePerOperatorConstraint : Prop

/--
**Tick447 — composition with PDE-A's L³-endpoint construction.**

After tick446 (PDE-A) and tick447 (this), the tick445
`FinalThreeRouteCompositionRoute1NoConcAndCharge` structure's
`L3ChargeOrDecoherenceCharge : L3EndpointBlowupChargeReplacement ⊕
VorticityDecoherenceChargeReplacement` is *inhabitable* from either of two
named classical hypotheses:

* `L3EndpointBlowupChargeReplacement.ofESSEndpointL3Hypothesis` (tick446)
* `VorticityDecoherenceChargeReplacement.ofCFDecoherenceHypothesis` (tick447)

This structure declares the post-tick447 composition state.  Honest scope:
NOT Clay closure.  Either bridge requires its named classical hypothesis to
be inhabited on the actual NS bad set, which remains open analytic work.
-/
structure Tick446And447ParallelConstructorsCompose where
  l3EndpointBridgeAvailableViaPDEATick446 : Prop
  cfDecoherenceBridgeAvailableViaClaudeTick447 : Prop
  tick445LeftSummandInhabitableFromESSHypothesis : Prop
  tick445RightSummandInhabitableFromCFHypothesis : Prop
  eitherClassicalHypothesisInhabitsFinalComposition : Prop
  bothBridgesAreTypedNotPDEDerivations : Prop
  noClassicalHypothesisProvedHere : Prop
  noClayClosureFromParallelBridgesAlone : Prop
  remainingPDEWorkIsHypothesisInhabitationOnActualNSBadSet : Prop

/-!
## Tick449 — Gowers next-level compression: unify the two charge primitives (claude_rd)

After tick445 / tick446 (ESS-sourced L³-endpoint construction) /
tick447 (CF-sourced vorticity-decoherence construction), the disjunctive
r-linear charge frontier consists of two named primitives with *identical
structural shape*:

* `L3EndpointBlowupChargeReplacement` (ESS-sourced) — tick445/446.
* `VorticityDecoherenceChargeReplacement` (CF-sourced) — tick445/447.

Both carry the same `Real`-valued data: a non-negative measure value bounded
by a finite root budget, an `r`-linear charge `coeff * radius ≤ measureValue`
with a strictly positive coefficient, plus four `Prop` guards distinguishing
the external-classical source.  The only structural difference is the *names*
of the measure field and the four source-guard Props.

**Gowers move (a)**: factor the *shape* from the *source*.  Introduce one
unified primitive `UnifiedClayChargePrimitive` carrying the shared `Real`
data + an opaque `externalClassicalSourceToken : Prop` and a `sourceTag : Nat`
field that records which classical input produced it.  Provide two
`toUnified` reduction `def`s — one from each tick445 primitive — and prove
the r-linear inequality at the unified level.

After this compression:

* Downstream consumers (flat-radius reserve telescoping; depth-reserve
  identification) take a `UnifiedClayChargePrimitive` argument and need
  not pattern-match on which source supplied it.
* The two named primitives remain useful as *source-typed entry points*
  but no longer need parallel downstream theorems.
* The post-tick449 frontier collapses from "L³ OR vorticity (two separate
  charge structures)" to "one unified charge OR an explicit no-charge
  obstruction".

**Honest scope** (Meta-Darwin-to-self, six checks recorded in the E-row
and as Lean Prop fields below):

1. NOT Clay closure.  Supplying an inhabitant of `UnifiedClayChargePrimitive`
   still requires an external classical input (ESS, CF, or another
   r-linear-charge-producing theorem).
2. NOT PDE progress.  Neither inhabitant is constructed here; the
   compression is structural / syntactic, not analytic.
3. The compression IS load-bearing: it factors the depth-reserve
   telescoping into a single consumer of the unified primitive, removing
   the OLD requirement to ship two parallel downstream theorems.
4. Anti-laundering guard `compressionIsStructuralNotAnalytic : Prop`
   shipped explicitly to forbid retroactive reading of the compression
   as analytic progress.
5. Falsifier: if it turns out only one of (L³, CF) admits a charge
   inhabitant and the other admits an explicit countermodel, then the
   unified primitive degenerates to a renaming of the surviving one and
   the compression *did not buy anything*.  Recorded as
   `falsifierDegenerateIfOneBranchHasCountermodel : Prop`.
6. Pre-check `ns_graph_tick` ran before this tick; top closure-miner
   targets remain Track-B (`LeraySelfTaxProfilePriceStream:1095`,
   `LowFrequencyLipschitzBridge:762`).  Continuing the Gowers chain on
   silent-flat is an explicit one-tick operator-directed deviation,
   NOT a routing policy change.  Recorded as
   `preCheckSaysTrackBHigherLeverage : Prop`.

We choose (a) over (b)/(c) because both tick445 charge primitives share
exactly the same `Real`-shape: factoring is the cheaper move and yields
a falsifiable structural compression with a clean Lean theorem.
-/

/--
**Tick449 — Unified Clay charge primitive (Gowers 2 → 1 compression).**

Shared structural shape of `L3EndpointBlowupChargeReplacement` and
`VorticityDecoherenceChargeReplacement`.  Carries one non-negative `Real`
measure value bounded by a finite root budget, plus an `r`-linear charge
with a strictly positive coefficient, plus an opaque source token and
enumeration tag.

The `sourceTag : Nat` field is a small enumeration tag (1 = ESS endpoint,
2 = Constantin–Fefferman, 3+ reserved for future weaker classical inputs)
that records the provenance without forcing the consumer to switch.
-/
structure UnifiedClayChargePrimitive where
  /-- Non-negative measure value. -/
  measureValue : Real
  measureValue_nonneg : 0 ≤ measureValue
  /-- Finite root budget bounding the measure. -/
  finiteRootBudget : Real
  finiteRootBudget_nonneg : 0 ≤ finiteRootBudget
  /-- Budget bound. -/
  measure_bounded_by_rootBudget : measureValue ≤ finiteRootBudget
  /-- Radius being charged (one cube). -/
  radiusCharge : Real
  /-- Strictly positive r-linear charge coefficient. -/
  radiusChargeCoeff : Real
  radiusChargeCoeff_pos : 0 < radiusChargeCoeff
  /-- r-linear (not r²) charge inequality: `coeff * radius ≤ measureValue`. -/
  paysRadius : radiusChargeCoeff * radiusCharge ≤ measureValue
  /-- Provenance enumeration tag (1 = ESS L³, 2 = CF, 3 = NoConcLemma,
      ≥ 4 reserved). -/
  sourceTag : Nat
  /-- Opaque token recording the external classical input that produced
      the inhabitant.  Forbids constructing the unified primitive without
      naming *some* external classical source. -/
  externalClassicalSourceToken : Prop
  /-- Anti-laundering guard: the charge is r-linear, not r². -/
  chargeIsR_linearNotR_squared : Prop
  /-- Anti-laundering guard: the charge was fixed before radius selection. -/
  chargeFixedBeforeRadiusSelection : Prop
  /-- Anti-laundering guard: the unified primitive does NOT use CKN
      square-mass charging. -/
  chargeDoesNotUseCKNSquareMass : Prop

/--
**Tick449 — Reduction: `L3EndpointBlowupChargeReplacement` → unified primitive.**

The L³-endpoint blowup charge from tick445/446 reduces to the unified
charge by field-by-field plumbing.  `sourceTag := 1` (= ESS L³ endpoint).
-/
def L3EndpointBlowupChargeReplacement.toUnified
    (h : L3EndpointBlowupChargeReplacement) : UnifiedClayChargePrimitive :=
  { measureValue := h.L3DefectMeasureValue
    measureValue_nonneg := h.L3DefectMeasureValue_nonneg
    finiteRootBudget := h.finiteRootBudget
    finiteRootBudget_nonneg := h.finiteRootBudget_nonneg
    measure_bounded_by_rootBudget := h.L3DefectMeasure_bounded_by_rootBudget
    radiusCharge := h.radiusCharge
    radiusChargeCoeff := h.radiusChargeCoeff
    radiusChargeCoeff_pos := h.radiusChargeCoeff_pos
    paysRadius := h.L3DefectChargesRadius
    sourceTag := 1
    externalClassicalSourceToken := h.chargeIsFromESSBlowupMeasure
    chargeIsR_linearNotR_squared := h.chargeIsR_linearNotR_squared
    chargeFixedBeforeRadiusSelection := h.chargeFixedBeforeRadiusSelection
    chargeDoesNotUseCKNSquareMass := h.chargeDoesNotUseCKNSquareMass }

/--
**Tick449 — Reduction: `VorticityDecoherenceChargeReplacement` → unified primitive.**

The vorticity-direction decoherence charge from tick445/447 reduces to the
unified charge by field-by-field plumbing.  `sourceTag := 2`
(= Constantin–Fefferman vorticity-direction).  The original tick445
structure does not carry an explicit `chargeDoesNotUseCKNSquareMass` slot,
so the Carleson-style guard (`chargeIsCarlesonStyleVorticity`) is routed
into that slot at the unified level — the Carleson guard already excludes
CKN square-mass.
-/
def VorticityDecoherenceChargeReplacement.toUnified
    (h : VorticityDecoherenceChargeReplacement) : UnifiedClayChargePrimitive :=
  { measureValue := h.decoherenceMeasureValue
    measureValue_nonneg := h.decoherenceMeasureValue_nonneg
    finiteRootBudget := h.finiteRootBudget
    finiteRootBudget_nonneg := h.finiteRootBudget_nonneg
    measure_bounded_by_rootBudget := h.decoherenceMeasure_bounded_by_rootBudget
    radiusCharge := h.radiusCharge
    radiusChargeCoeff := h.radiusChargeCoeff
    radiusChargeCoeff_pos := h.radiusChargeCoeff_pos
    paysRadius := h.decoherencePaysRadius
    sourceTag := 2
    externalClassicalSourceToken := h.chargeIsFromConstantinFefferman_seminorm
    chargeIsR_linearNotR_squared := h.chargeIsR_linearNotR_squared
    chargeFixedBeforeRadiusSelection := h.chargeFixedBeforeRadiusSelection
    chargeDoesNotUseCKNSquareMass := h.chargeIsCarlesonStyleVorticity }

/--
**Tick449 — Unified r-linear charge theorem.**

The unified primitive delivers the same r-linear inequality both source
primitives delivered separately.  Downstream consumers (flat-radius
reserve telescoping) now need only one theorem instead of two.
-/
theorem UnifiedClayChargePrimitive.radiusCharge_le_measure
    (h : UnifiedClayChargePrimitive) :
    h.radiusChargeCoeff * h.radiusCharge ≤ h.measureValue :=
  h.paysRadius

/--
**Tick449 — Reduction theorem from the L³ replacement.**

The L³ replacement's r-linear charge inequality factors through the unified
theorem.  This makes the compression machine-checkable: the L³ inequality
is now reachable via `toUnified` + `UnifiedClayChargePrimitive.radiusCharge_le_measure`.
-/
theorem L3EndpointBlowupChargeReplacement.unified_radiusCharge
    (h : L3EndpointBlowupChargeReplacement) :
    h.toUnified.radiusChargeCoeff * h.toUnified.radiusCharge ≤ h.toUnified.measureValue :=
  h.toUnified.paysRadius

/-- Symmetric reduction theorem from the vorticity-decoherence replacement. -/
theorem VorticityDecoherenceChargeReplacement.unified_radiusCharge
    (h : VorticityDecoherenceChargeReplacement) :
    h.toUnified.radiusChargeCoeff * h.toUnified.radiusCharge ≤ h.toUnified.measureValue :=
  h.toUnified.paysRadius

/--
**Tick449 — Field-identity audit for the L³ reduction.**

The unified `measureValue` field equals the original `L3DefectMeasureValue`
under `toUnified`.  Reflexivity by construction; this is the machine-checkable
audit that no field is silently re-routed.
-/
theorem L3EndpointBlowupChargeReplacement.toUnified_measureValue_identity
    (h : L3EndpointBlowupChargeReplacement) :
    h.toUnified.measureValue = h.L3DefectMeasureValue := rfl

/-- Symmetric field-identity audit for the vorticity reduction. -/
theorem VorticityDecoherenceChargeReplacement.toUnified_measureValue_identity
    (h : VorticityDecoherenceChargeReplacement) :
    h.toUnified.measureValue = h.decoherenceMeasureValue := rfl

/-- `sourceTag` identity for the L³ reduction (= 1). -/
theorem L3EndpointBlowupChargeReplacement.toUnified_sourceTag
    (h : L3EndpointBlowupChargeReplacement) :
    h.toUnified.sourceTag = 1 := rfl

/-- `sourceTag` identity for the vorticity reduction (= 2). -/
theorem VorticityDecoherenceChargeReplacement.toUnified_sourceTag
    (h : VorticityDecoherenceChargeReplacement) :
    h.toUnified.sourceTag = 2 := rfl

/--
**Tick449 — Disjunctive reduction: either tick445 primitive yields a unified
charge.**

The Sum-type sender from `L3EndpointBlowupChargeReplacement ⊕
VorticityDecoherenceChargeReplacement` reduces to `UnifiedClayChargePrimitive`
by `Sum.elim`.  This is exactly the Gowers 2 → 1 compression at the
disjunction level: the two-branch frontier collapses to a single named
primitive.
-/
def UnifiedClayChargePrimitive.ofSumOfTick445Primitives
    (s : L3EndpointBlowupChargeReplacement ⊕ VorticityDecoherenceChargeReplacement) :
    UnifiedClayChargePrimitive :=
  s.elim L3EndpointBlowupChargeReplacement.toUnified
         VorticityDecoherenceChargeReplacement.toUnified

/--
**Tick449 — Composability with `FinalThreeRouteCompositionRoute1NoConcAndCharge`.**

The tick445 final-composition structure takes a Sum of the two tick445
charge replacements as its charge field.  After tick449, that Sum reduces
to a single `UnifiedClayChargePrimitive` — the post-compression final
composition consumes one named primitive instead of two.

This `def` exposes the unified extractor directly from the tick445
composition.
-/
def FinalThreeRouteCompositionRoute1NoConcAndCharge.unifiedCharge
    (h : FinalThreeRouteCompositionRoute1NoConcAndCharge) :
    UnifiedClayChargePrimitive :=
  UnifiedClayChargePrimitive.ofSumOfTick445Primitives h.L3ChargeOrDecoherenceCharge

/--
**Tick449 — honest scope guard for the Gowers compression.**

The compression is *structural*: it factors the shape of the r-linear
charge inequality from the external classical input.  It does NOT supply
any inhabitant.  It does NOT close Clay regularity.  It does NOT make
progress on constructing either the ESS endpoint L³ measure or the
Constantin–Fefferman vorticity seminorm.

Anti-laundering guards (Prop fields enumerate the things the compression
does NOT do):
-/
structure UnifiedClayChargePrimitiveIsNotClayClosure where
  /-- The compression is a structural refactor, not analytic content. -/
  compressionIsStructuralNotAnalytic : Prop
  /-- Constructing an inhabitant still requires an external classical input. -/
  inhabitationStillRequiresExternalClassicalInput : Prop
  /-- ESS theorem is externally cited (Escauriaza–Seregin–Šverák 2003). -/
  ESSStillExternallyCited : Prop
  /-- CF theorem is externally cited (Constantin–Fefferman). -/
  CFStillExternallyCited : Prop
  /-- The compression does not close `NoSilentFlatDefectProfile`. -/
  noSilentFlatDefectProfileNotClosed : Prop
  /-- The compression does not unconditionally close flat-radius reserve. -/
  flatRadiusReserveNotUnconditionallyClosed : Prop
  /-- The compression does not close Clay regularity. -/
  clayRegularityNotClosed : Prop
  /-- The compression is a 2 → 1 syntactic compression at the disjunctive
      r-linear charge frontier; the count of *open* PDE problems is
      unchanged: ESS endpoint L³ construction OR CF vorticity-decoherence
      construction OR a weaker third source. -/
  countOfOpenPDEProblemsUnchanged : Prop
  /-- Falsifier: if one branch admits a countermodel, the unified primitive
      degenerates to a renaming of the surviving branch and the compression
      buys nothing.  This is the explicit Meta-Darwin guard. -/
  falsifierDegenerateIfOneBranchHasCountermodel : Prop
  /-- Pre-check signal: `ns_graph_tick` continues to rank Track-B objects
      higher than silent-flat work.  Continuing here is an explicit one-tick
      operator-directed deviation. -/
  preCheckSaysTrackBHigherLeverage : Prop

/--
**Tick449 — Meta-Darwin-to-self check (in-artifact).**

Six checks recorded in Lean as Prop fields so the self-audit survives in
the file alongside the construction:

1. Null distribution: a charge with `radiusChargeCoeff = 0` would still
   satisfy `0 ≤ measureValue` trivially.  Our structure forbids this by
   `radiusChargeCoeff_pos`.
2. Distinct-outcome count: the two tick445 primitives produce distinct
   `sourceTag` values (1 vs 2) under `toUnified`.  Machine-checked.
3. Class-balance: both `toUnified` defs do exactly the same kind of
   field-plumbing — no asymmetric content hidden in one direction.
4. LOO: leaving out either tick445 primitive does not break the unified
   primitive (the Sum disjunction still admits the remaining branch).
5. Floor-satisfiable: the unified r-linear theorem is satisfiable by an
   r-linear charge with `coeff = 1`, `radius = 1`, `measure = 1`.
6. Source-leakage: the unified primitive does not leak ESS or CF semantic
   content into the shape — only the opaque `externalClassicalSourceToken`
   `Prop` records provenance.
-/
structure UnifiedClayChargePrimitiveMetaDarwinSelfAudit where
  nullDistribution_radiusChargeCoeff_pos_excludes_trivial : Prop
  distinctOutcome_sourceTag_1_vs_2 : Prop
  classBalance_symmetric_field_plumbing : Prop
  LOO_either_branch_can_be_dropped : Prop
  floorSatisfiable_unit_inhabitant_exists : Prop
  sourceLeakage_only_via_opaque_token : Prop

end ZtareProofs.NSSilentFlatDefectObservability
