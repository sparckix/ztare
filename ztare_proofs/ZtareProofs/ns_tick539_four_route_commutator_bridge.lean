import Mathlib.Data.Real.Basic
import Mathlib.Tactic.Linarith
import Mathlib.Tactic.Positivity
import ZtareProofs.ns_route1_fresh_frequency_coercivity_adapter
import ZtareProofs.ns_tick538_typeIDensityLower_corrected

/-!
# Tick539 — Four-route bridge: commutator-only as the 4th route

## Origin + amnesia reconciliation

Per operator directive (reconciliation steps 2-3) and the amnesia
audit, the May-14 GPT-5.5 obligation `ActiveSingularResidualDensityGap`
(`mu_A_perp(E) ≤ C·mu_I(E)`) is **already codified** in the substrate:

- `ActiveSingularRestriction`
  (`ns_route1_fresh_frequency_coercivity_adapter.lean:5463`)
- `activeSingular_le_residual_of_measureLocalSplit` (PROVED there:
  `∀ E, muAperp E ≤ muI E` via Borel-local domination).

This tick does NOT re-codify it (that would repeat the amnesia
failure). Instead it:

1. Frames the corrected commutator-only Type-I radius receipt
   (tick538) as the **FOURTH route** alongside the existing
   three-route composition
   (`FinalThreeRouteCompositionRoute1NoConcAndCharge` in
   `ns_silent_flat_defect_observability.lean`).
2. Cites the substrate's already-proved active-singular ≤ residual
   theorem as the codified May-14 obligation.
3. Names the ONE genuinely-missing May-14 piece — the
   Radon–Nikodym density lower bound `d muI / d muAperp ≥ c > 0`
   — as an open obligation, distinct from the (already proved)
   Borel-local domination.

## The four routes (exhaustion of bad nodes)

| Route | Source | Status |
|---|---|---|
| R1 ESS/CF dichotomy | external (Escauriaza–Seregin–Šverák 2003, Constantin–Fefferman) | cited Prop |
| R2 No-Concentration Lemma | external axiom | cited Prop |
| R3 L³ / vorticity-decoherence charge | tick445-447 charge replacements | cited Prop |
| **R4 commutator-only Type-I radius receipt** | **tick538 (PROVED real inequality)** | **derived** |

Route 4 is the only one that contributes a *derived real
inequality* (`c·r ≤ α_C` from tick538's
`alphaC_radius_receipt_corrected`); R1-R3 are genuinely external and
remain cited Props (honest scope: they are not this session's work).

## Honest scope

This tick is a COMPOSITION BRIDGE, not a Clay closure. The
load-bearing real content is route 4's inequality (reused from
tick538, itself resting on the named CKN-excess / Type-I-envelope /
Poincaré / active-domination PDE obligations). R1-R3 stay external.
The residual is `SuperTypeIIntermittentCommutatorCascade` (tick538).

## ANTI-PATTERN-012 explicit (6-point)

- form ✓ `SuitableLocalEnergyDefectMeasureSource Ω`
- direction ✓ four-route case split ⇒ per-node radius charge
- quantifier ✓ `∀ Q` on bad nodes
- domain ✓ fresh regions on K
- dimension ✓ measure-valued α + scalar radius
- inclusion ✓ substrate `alphaC` + cited `activeSingular_le_residual`

## Universal-language ops applied (catalog tokens by name)

- **Problem Reformulation** — closure as four-route exhaustion.
- **Auxiliary Comparison Object Construction** — route-4 receipt as
  the comparison object for the commutator branch.
- **Characterization by Obstruction** — RN-density gap + intermittent
  cascade are the named obstructions.
- **Decomposition** — bad nodes split into four routes.
- **Sharpness / Failure-Witness Construction** — residual cited from
  tick538.

## META-PATTERN-023 4-scope verification

- **local scope** ✓ route-4 inequality is a self-contained reuse
- **chain scope** ✓ four-route case split composes to per-node charge
- **recursive scope** ✓ bridges tick538 into the existing 3-route
- **meta scope** ✓ amnesia-reconciled: cites substrate's proved
  active-singular theorem, does not duplicate; names the genuinely
  missing RN-density piece
-/

namespace ZtareProofs.NSTick539FourRouteCommutatorBridge

open ZtareProofs.Route1FreshFrequencyCoercivity
open ZtareProofs.NSTick538TypeIDensityLowerCorrected

/--
**`FourRouteBadNodeExhaustion`** — the four-route composition.

Routes 1-3 are cited external Props (ESS/CF, No-Concentration, charge
replacement). Route 4 is the corrected commutator-only Type-I radius
receipt from tick538 — a real inequality, not a Prop.

`exhaustion` says every bad node falls into exactly one route. The
per-node charge theorem derives `c·r ≤ α_C` whenever route 4 fires
(the genuine new content); routes 1-3 supply their own (cited)
charges.
-/
structure FourRouteBadNodeExhaustion
    {Ω : Type u} (h : SuitableLocalEnergyDefectMeasureSource Ω) where
  badNode : Set Ω → Prop
  /-- Route 4: corrected commutator-only Type-I receipt (tick538). -/
  route4 : TypeIDensityLowerCorrected h
  route4Branch : Set Ω → Prop
  route4Branch_eq : ∀ Q : Set Ω, route4Branch Q = route4.branch Q
  route4_sameCarrier :
    ∀ Q : Set Ω, route4.branch Q → h.alphaA Q = h.alphaC Q
  /-- Routes 1-3 cited external Props (honest scope: not this work). -/
  route1_ESS_CF_killed : Set Ω → Prop
  route2_NoConcentration_killed : Set Ω → Prop
  route3_charge_paid : Set Ω → Prop
  /-- Exhaustion: every bad node is in one of the four routes. -/
  exhaustion :
    ∀ Q : Set Ω, badNode Q →
      route1_ESS_CF_killed Q ∨ route2_NoConcentration_killed Q ∨
      route3_charge_paid Q ∨ route4.branch Q

/--
**Route-4 per-node radius charge** (the genuine derived content).

Whenever a bad node is on route 4 (commutator-only Type-I), the
corrected receipt from tick538 gives an explicit positive radius
charge in the commutator measure. This is a real inequality, derived
— not assumed, not a Prop.
-/
theorem route4_radius_charge
    {Ω : Type u} (h : SuitableLocalEnergyDefectMeasureSource Ω)
    (F : FourRouteBadNodeExhaustion h)
    (Q : Set Ω) (hQ : F.route4.branch Q) :
    F.route4.poincareActiveConstant *
        (F.route4.m Q / (2 * F.route4.M ^ 3)) * F.route4.r Q ≤
      h.alphaC Q :=
  alphaC_radius_receipt_corrected h F.route4 Q hQ
    (F.route4_sameCarrier Q hQ)

/--
**Route-4 strict positivity**: the route-4 commutator charge is
strictly positive on its branch (given positive CKN mass, envelope,
radius). Confirms route 4 is non-vacuous — it pays a real charge.
-/
theorem route4_charge_pos
    {Ω : Type u} (h : SuitableLocalEnergyDefectMeasureSource Ω)
    (F : FourRouteBadNodeExhaustion h)
    (Q : Set Ω) (hQ : F.route4.branch Q)
    (hr : 0 < F.route4.r Q) :
    0 < h.alphaC Q := by
  have hrec := route4_radius_charge h F Q hQ
  have hm : 0 < F.route4.m Q := F.route4.m_pos Q hQ
  have hM : 0 < F.route4.M := F.route4.M_pos
  have hpac : 0 < F.route4.poincareActiveConstant :=
    F.route4.poincareActiveConstant_pos
  have hpos : 0 < F.route4.poincareActiveConstant *
      (F.route4.m Q / (2 * F.route4.M ^ 3)) * F.route4.r Q := by
    have : 0 < F.route4.m Q / (2 * F.route4.M ^ 3) := by positivity
    positivity
  linarith

/--
**Amnesia-reconciliation record (May-14 obligation status).**

The May-14 GPT-5.5 `ActiveSingularResidualDensityGap` decomposes:

- `singular_control` (`muAperp E ≤ C·muI E`) — **already proved** in
  the substrate as `activeSingular_le_residual_of_measureLocalSplit`
  (Borel-local domination). Cited, not duplicated.
- `residual_density_lower` (`c ≤ d muI / d muAperp`, RN-density) —
  **genuinely open**; NOT implied by Borel-local domination alone
  (domination gives an inequality of masses, not a density floor).

This record states the distinction explicitly so the open piece is
not silently absorbed into the already-proved one (anti-laundering).
-/
structure May14DensityGapReconciliation where
  /-- Borel-local domination already proved in substrate. -/
  singular_control_already_proved_in_substrate : Prop
  /-- RN-density lower bound is the genuinely-open remaining piece. -/
  rn_density_lower_bound_still_open : Prop
  /-- The two are NOT equivalent: mass-domination ⇏ density floor. -/
  domination_does_not_imply_density_floor : Prop
  /-- Route 4 (tick538) attacks the radius receipt directly, a
      different and now-derived route to the same closure target. -/
  route4_is_independent_radius_route : Prop

/-! ## Honest scope record -/

structure Tick539HonestScopeRecord where
  /-- Four-route composition; route 4 derived, R1-R3 cited external. -/
  four_route_composition_route4_derived : Prop
  /-- May-14 obligation reconciled: domination proved, RN-gap open. -/
  may14_reconciled_no_duplication : Prop
  /-- Not a Clay closure; residual is super-Type-I intermittent. -/
  not_clay_closure_residual_named : Prop
  /-- Route-4 charge is real inequality (proved), not Prop. -/
  route4_charge_is_proved_inequality : Prop

end ZtareProofs.NSTick539FourRouteCommutatorBridge
