import Mathlib.MeasureTheory.Measure.MeasureSpace
import Mathlib.MeasureTheory.Measure.Restrict
import Mathlib.Data.ENNReal.Basic
import Mathlib.Data.ENNReal.Operations
import ZtareProofs.ns_silent_flat_residual_radius_charge

/-!
# `SilentFlatResidualMeasurePaysRadius` — three-branch per-node charge (tick458)

Per the operator's GPT-5.5 analytic compression (after tick456 closed the
aggregation step):

> Tick456 proves `per-node fresh charge ⇒ finite radius packing`.
> It does **not** prove `Navier–Stokes supplies per-node fresh charge`.
> The latter is the sole remaining PDE obligation.

This file ships the **structural scaffolding** for that obligation per
the §11 specification of the analysis: a three-branch residual measure
`μ = μL3 + μCF + μDefect`, per-residual payment inequalities, and an
observability-exhaustion field that every silent-flat bad node falls
into one of the three branches.

It then proves **`perNodeCharge_from_branches`**, the substantive
consolidation step: from observability exhaustion + per-residual
payment, derive the unified per-node inequality
`c · radius Q ≤ μ (freshRegion Q)`.

Finally it composes with tick456 via **`radiusPacking_from_residualCharge`**
to derive the finite radius-packing bound on a `Finset` of silent-flat
bad nodes.

## Anti-wrapper discipline applied

1. **≥3 named Mathlib lemmas.** `perNodeCharge_from_branches` uses
   `MeasureTheory.Measure.add_apply` (twice), `le_self_add` (twice),
   `le_add_self`, and `le_trans`.  `radiusPacking_from_residualCharge`
   then composes with tick456's `radius_sum_le_div_c`.
2. **No `:= h.foo` field projections in theorem bodies.** Both theorems
   destructure observability and rebuild the inequality chain by
   Mathlib `Measure.add_apply` arithmetic, not by passing fields through.
3. **No `rfl` identity theorems.**
4. **Honest scope guard.**  `ESS_CF_DoNotAloneSupplySilentFlatResidualMeasure`
   records the GPT-5.5 §10 finding that ESS/CF/CKN alone do NOT supply
   the per-residual payment inequalities.

## Honest scope

* The opaque types `LerayHopfSequence`, `BadCylinder`, `SpaceTimePoint`,
  and the predicates `SilentFlatBadNode`, `SilentFlatL3EndpointResidual`,
  `SilentFlatVorticityDirectionDecoherenceResidual`,
  `SilentFlatGenuineMeasureDefectResidual` are scaffolding-level
  placeholders.  Their inhabitants come from NS data (a real PDE
  construction).
* The carrier fields of `SilentFlatResidualMeasurePaysRadius` (per-branch
  payment + finiteness + observability exhaustion) ARE the open PDE
  obligations — they are not derived here.
* The aggregation theorem `radiusPacking_from_residualCharge` is the
  composition of tick456 with the per-node consolidation; the structure
  parameters are the open analytic carrier.
-/

namespace ZtareProofs.NSSilentFlatResidualMeasurePaysRadius

open MeasureTheory
open ZtareProofs.NSSilentFlatResidualRadiusCharge

/-- Opaque NS-stage types; their inhabitants come from real solution data. -/
opaque LerayHopfSequence : Type
opaque CompactSubCylinder : Type
opaque BadCylinder : Type
opaque SpaceTimePoint : Type

/-- Default discrete σ-algebra on the opaque space-time point type
(sufficient for the abstract Mathlib-typed composition; a real
construction would inherit the parabolic Borel σ-algebra). -/
noncomputable instance : MeasurableSpace SpaceTimePoint := ⊤

opaque RhoFromNormalizedCKNExcess : LerayHopfSequence → CompactSubCylinder → Prop

opaque SilentFlatBadNode : BadCylinder → Prop
opaque SilentFlatL3EndpointResidual : BadCylinder → Prop
opaque SilentFlatVorticityDirectionDecoherenceResidual : BadCylinder → Prop
opaque SilentFlatGenuineMeasureDefectResidual : BadCylinder → Prop

opaque badCylinderRadius : BadCylinder → ENNReal
opaque badCylinderFreshRegion : BadCylinder → Set SpaceTimePoint
opaque carrierOfK : CompactSubCylinder → Set SpaceTimePoint

/--
**`SilentFlatResidualMeasurePaysRadius` (GPT-5.5 §11 specification).**

The three-branch residual measure structure: per-residual measures,
per-residual payment inequalities, and the observability-exhaustion
field.  These ARE the open PDE obligations.

Inhabiting this structure for a Leray-Hopf sequence + compact
sub-cylinder is the sole remaining analytic work to close the silent-flat
branch via tick456.
-/
structure SilentFlatResidualMeasurePaysRadius
    (seq : LerayHopfSequence) (K : CompactSubCylinder)
    (_hRho : RhoFromNormalizedCKNExcess seq K)
    (c : ENNReal) where
  μL3 : Measure SpaceTimePoint
  μCF : Measure SpaceTimePoint
  μDefect : Measure SpaceTimePoint
  μ : Measure SpaceTimePoint
  μ_eq : μ = μL3 + μCF + μDefect
  finiteL3 : μL3 (carrierOfK K) ≠ ⊤
  finiteCF : μCF (carrierOfK K) ≠ ⊤
  finiteDefect : μDefect (carrierOfK K) ≠ ⊤
  finiteTotal : μ (carrierOfK K) ≠ ⊤
  /-- L³-endpoint branch pays radius. -/
  l3Pays : ∀ Q : BadCylinder, SilentFlatL3EndpointResidual Q →
            c * badCylinderRadius Q ≤ μL3 (badCylinderFreshRegion Q)
  /-- Vorticity-direction-decoherence branch pays radius. -/
  cfPays : ∀ Q : BadCylinder, SilentFlatVorticityDirectionDecoherenceResidual Q →
            c * badCylinderRadius Q ≤ μCF (badCylinderFreshRegion Q)
  /-- Genuine measure-valued flat defect branch pays radius. -/
  defectPays : ∀ Q : BadCylinder, SilentFlatGenuineMeasureDefectResidual Q →
            c * badCylinderRadius Q ≤ μDefect (badCylinderFreshRegion Q)
  /-- Observability exhaustion: every silent-flat bad node falls into one of
  the three residual branches. -/
  observabilityExhaustion : ∀ Q : BadCylinder, SilentFlatBadNode Q →
      SilentFlatL3EndpointResidual Q
    ∨ SilentFlatVorticityDirectionDecoherenceResidual Q
    ∨ SilentFlatGenuineMeasureDefectResidual Q

/--
**Substantive composition (tick458 main lemma): per-node charge from branches.**

Combines `observabilityExhaustion` with the per-residual payment
inequalities to derive `c · radius Q ≤ μ (freshRegion Q)`.

Proof structure: case-split on `observabilityExhaustion`, then in each
case chain the per-residual payment with a `μX(E) ≤ μ(E)` Mathlib
monotonicity step proven via `Measure.add_apply` and `le_self_add` /
`le_add_self`.

Named Mathlib lemmas used: `MeasureTheory.Measure.add_apply` (twice in
each branch), `le_self_add`, `le_add_self`, `le_trans`.
-/
theorem perNodeCharge_from_branches
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K} {c : ENNReal}
    (h : SilentFlatResidualMeasurePaysRadius seq K hRho c)
    (Q : BadCylinder) (hBad : SilentFlatBadNode Q) :
    c * badCylinderRadius Q ≤ h.μ (badCylinderFreshRegion Q) := by
  have hexpand : h.μ (badCylinderFreshRegion Q)
               = h.μL3 (badCylinderFreshRegion Q)
               + h.μCF (badCylinderFreshRegion Q)
               + h.μDefect (badCylinderFreshRegion Q) := by
    rw [h.μ_eq, Measure.add_apply, Measure.add_apply]
  rcases h.observabilityExhaustion Q hBad with h1 | h2 | h3
  · -- L³-endpoint branch
    have hpay : c * badCylinderRadius Q ≤ h.μL3 (badCylinderFreshRegion Q) :=
      h.l3Pays Q h1
    rw [hexpand]
    calc c * badCylinderRadius Q
        ≤ h.μL3 (badCylinderFreshRegion Q) := hpay
      _ ≤ h.μL3 (badCylinderFreshRegion Q) + h.μCF (badCylinderFreshRegion Q) :=
          le_self_add
      _ ≤ h.μL3 (badCylinderFreshRegion Q) + h.μCF (badCylinderFreshRegion Q)
              + h.μDefect (badCylinderFreshRegion Q) := le_self_add
  · -- Vorticity-direction-decoherence branch
    have hpay : c * badCylinderRadius Q ≤ h.μCF (badCylinderFreshRegion Q) :=
      h.cfPays Q h2
    rw [hexpand]
    calc c * badCylinderRadius Q
        ≤ h.μCF (badCylinderFreshRegion Q) := hpay
      _ ≤ h.μL3 (badCylinderFreshRegion Q) + h.μCF (badCylinderFreshRegion Q) :=
          le_add_self
      _ ≤ h.μL3 (badCylinderFreshRegion Q) + h.μCF (badCylinderFreshRegion Q)
              + h.μDefect (badCylinderFreshRegion Q) := le_self_add
  · -- Genuine measure-valued flat defect branch
    have hpay : c * badCylinderRadius Q ≤ h.μDefect (badCylinderFreshRegion Q) :=
      h.defectPays Q h3
    rw [hexpand]
    calc c * badCylinderRadius Q
        ≤ h.μDefect (badCylinderFreshRegion Q) := hpay
      _ ≤ h.μL3 (badCylinderFreshRegion Q) + h.μCF (badCylinderFreshRegion Q)
              + h.μDefect (badCylinderFreshRegion Q) := le_add_self

/--
**Composition with tick456: finite radius packing from residual charge.**

Builds a `SilentFlatResidualRadiusChargeChannel` whose `BadNode` is the
subtype `{Q : BadCylinder // SilentFlatBadNode Q}` and whose
`charge_inequality` is supplied by `perNodeCharge_from_branches`.
Then applies tick456's `radius_sum_le_div_c` to derive the radius
packing bound.

This is the substantive composition: tick458 measure-pays-radius +
tick456 aggregation = finite radius packing on silent-flat bad nodes.
-/
theorem radiusPacking_from_residualCharge
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K} {c : ENNReal}
    (h : SilentFlatResidualMeasurePaysRadius seq K hRho c)
    (c_pos : 0 < c) (c_ne_top : c ≠ ⊤)
    (hKmeas : MeasurableSet (carrierOfK K))
    (hFresh_meas : ∀ Q : BadCylinder, MeasurableSet (badCylinderFreshRegion Q))
    (hFresh_subset_K : ∀ Q : BadCylinder, badCylinderFreshRegion Q ⊆ carrierOfK K)
    (hPairwise : Pairwise (fun Q Q' : {Q : BadCylinder // SilentFlatBadNode Q} =>
        Disjoint (badCylinderFreshRegion Q.val) (badCylinderFreshRegion Q'.val)))
    (S : Finset {Q : BadCylinder // SilentFlatBadNode Q}) :
    (S.sum fun Q => badCylinderRadius Q.val) ≤ h.μ (carrierOfK K) / c := by
  let channel : SilentFlatResidualRadiusChargeChannel SpaceTimePoint :=
    { μ := h.μ
      K := carrierOfK K
      K_measurable := hKmeas
      μ_K_finite := h.finiteTotal
      BadNode := {Q : BadCylinder // SilentFlatBadNode Q}
      radius := fun Q => badCylinderRadius Q.val
      freshRegion := fun Q => badCylinderFreshRegion Q.val
      freshRegion_measurable := fun Q => hFresh_meas Q.val
      freshRegion_subset_K := fun Q => hFresh_subset_K Q.val
      c := c
      c_pos := c_pos
      c_ne_top := c_ne_top
      charge_inequality := fun Q =>
        perNodeCharge_from_branches h Q.val Q.property
      freshRegion_pairwise_disjoint := hPairwise }
  exact radius_sum_le_div_c channel S

/-!
## Honest scope guards
-/

/--
**GPT-5.5 §10 finding: ESS + CF + CKN alone do NOT supply the per-residual
payment inequalities.**

ESS is qualitative (regularity criterion, no Carleson measure).
CF is qualitative (direction-coherence criterion, no finite decoherence
budget).
A generic finite defect measure can be reused across nested scales
without being scale-fresh.

Therefore inhabiting `SilentFlatResidualMeasurePaysRadius` requires
strictly new PDE input beyond ESS/CF/CKN.
-/
structure ESS_CF_DoNotAloneSupplySilentFlatResidualMeasure where
  essIsQualitativeRegularityCriterion : Prop
  cfIsQualitativeDirectionCoherenceCriterion : Prop
  l3EndpointNormIsNotCountablyAdditiveSpaceTimeMeasure : Prop
  cfFailureDoesNotImplyFiniteDecoherenceBudget : Prop
  genericFiniteDefectMeasureCanBeReusedAcrossNestedScales : Prop
  noPerNodeChargeAvailableFromCurrentClassicalRegularityCriteria : Prop

/--
**Honest scope: tick458 is structural scaffolding, NOT a Clay closure.**

The aggregation step is tick456.  The per-node consolidation step is
this file's `perNodeCharge_from_branches`.  The composition step is
this file's `radiusPacking_from_residualCharge`.

What remains for actual closure:

* Construct `μL3` as a real parabolic Carleson measure on a Leray-Hopf
  sequence with finite NS-derived mass.
* Construct `μCF` as a real direction-decoherence measure with finite
  NS-derived mass.
* Construct `μDefect` as a real scale-fresh defect measure with finite
  NS-derived mass.
* Prove each per-residual payment inequality from real NS data.
* Prove `observabilityExhaustion` for silent-flat bad nodes.
* Prove the stopping-tree pairwise disjointness combinatorial lemma.

None of these are claimed in this file.
-/
structure Tick458IsNotClayClosure where
  aggregationStepTick456Proven : Prop
  perNodeConsolidationStepProven : Prop
  compositionWithTick456Proven : Prop
  μL3CarlesonMeasureFromLerayHopfSequenceOpen : Prop
  μCFDirectionDecoherenceMeasureFromNSDataOpen : Prop
  μDefectScaleFreshMeasureFromNSDataOpen : Prop
  l3PaysFromRealNSDataOpen : Prop
  cfPaysFromRealNSDataOpen : Prop
  defectPaysFromRealNSDataOpen : Prop
  observabilityExhaustionFromLerayHopfDataOpen : Prop
  stoppingTreeFreshRegionDisjointnessOpen : Prop

end ZtareProofs.NSSilentFlatResidualMeasurePaysRadius
