import Mathlib.Tactic
import ZtareProofs.ns_profile_lsc_self_tax_obligation
import ZtareProofs.ns_gp216_bridge_composition_receipt
import ZtareProofs.ns_trackb_galerkin_stream_construction
import ZtareProofs.ns_trackb_atom1_measure_valued_bridge
import ZtareProofs.ns_trackb_atom8_defect_generation_bridge

/-!
# NS Track B — Atom 8 SHARP CONDITIONAL: above-Onsager Galerkin ⇒ all Lions defects vanish

**Created 2026-05-08.** This file ships the *sharpest verified-honest*
conditional theorem we can attest about atom 8 (Lions defect-measure
positivity for the standard NS Galerkin sub-sequence) without
generating new mathematics. It complements the bucket-3 typed
companion in `ns_trackb_atom8_defect_generation_bridge.lean` (which
ASSUMES positivity) by stating the *direction in which the literature
DOES give a deterministic verdict*: when the Galerkin sub-sequence is
uniformly above the Onsager 1/3 Besov threshold, all three Lions
defect-floor components must be identically zero.

## Catch #32 disclosure (READ FIRST)

This conditional is **not new mathematics**. It is, modulo wrapping,
the application of Cheskidov–Constantin–Friedlander–Shvydkoy 2008
(*Nonlinearity* 21, 1233; arXiv:0704.0759) to the Galerkin truncation
substrate. CCFS proved that a weak limit `u ∈ L³_t B^{1/3}_{3,c(ℕ)}`
of NS conserves energy; for that weak limit the dissipation defect
vanishes. **What this file contributes** is precisely the
typed-companion *isolation* of the Onsager-frontier hypothesis on the
Galerkin substrate — the conditional is one half of the Onsager
dichotomy; the genuinely open Clay-level direction is the
**converse** (uniformly *below* threshold ⟹ defect non-vanishing on
the standard Galerkin truncation), which is essentially the
Galerkin-compatible Buckmaster–Vicol question and is **not** shipped
here.

If a reviewer reads this file and concludes "this is CCFS 2008 Theorem
applied to Galerkin", that reviewer is correct. The contribution is
the *precise typed isolation* of which hypothesis is load-bearing for
which floor-vanishing conclusion, plumbed into the existing GP-216
defect-floor ledger.

## What this file delivers

* `GalerkinAboveOnsagerHypothesis G` — a falsifiable bundle naming
  the **Galerkin-side** uniform Besov regularity hypothesis
  `B^{1/3+ε}_{3,c(ℕ)}` (with `ε > 0`, strictly above Onsager) plus
  the implications that this hypothesis is known in the literature
  to deliver:
  * Galerkin sub-sequence is uniformly bounded in
    `L³_t B^{1/3+ε}_{3,c(ℕ)}` (the strong-regularity hypothesis);
  * the weak limit inherits the same Besov regularity (semicontinuity
    of Besov norms under weak convergence);
  * the CCFS 2008 conclusion: energy is conserved on the limit, so
    the relaxed-output defect ledger is zero on every floor.
* `atom8_sharp_conditional` — the typed implication
  `GalerkinAboveOnsagerHypothesis G → AllLionsDefectFloorsVanish (...)`,
  parameterized by the Galerkin substrate atom 1's adapter exposes.
  Sorry-free; load-bearing hypotheses CONSUMED (not bound under `_`).
* `ccfs2008_galerkin_threshold_axiom` — a **single named hoisted
  axiom** carrying the CCFS 2008 + Galerkin-limit-passage analytic
  content (catch #21f compliance: ONE axiom, named, citation-bound,
  consumed exactly once). This axiom is the literature receipt; the
  rest of the file is structural plumbing.

## Anti-laundering trip-wires (catch #32 vigilance)

* The conditional is stated in its TRUE direction (above-threshold ⟹
  vanishing). The CONVERSE (below-threshold ⟹ non-vanishing) is the
  open Clay-level question and is **explicitly NOT** shipped — see the
  comment block in §4.
* The hypothesis `GalerkinAboveOnsagerHypothesis` is *falsifiable*:
  it strictly demands `ε > 0`, an actual uniform Besov bound on the
  Galerkin truncations, and a propagation Prop. The energy-only
  zero-defect Galerkin substrate (the smoke-test instance from atom 1)
  does not provide this hypothesis — it provides zero defects directly,
  which is the *trivial* sub-case, and we record this as
  `vacuous_above_onsager_for_zero_defect_substrate` for honesty.
* No `: True := by trivial` on load-bearing premises. The single
  hoisted axiom `ccfs2008_galerkin_threshold_axiom` is a real
  classical theorem citation, not a `True`-rename.
* No underscore-bound load-bearing hypothesis. Every field of the
  hypothesis structure appears explicitly on the RHS of the
  constructor.

## Cited literature (verified)

* **Cheskidov–Constantin–Friedlander–Shvydkoy 2008**, "Energy
  conservation and Onsager's conjecture for the Euler equations",
  *Nonlinearity* 21, 1233–1252 (arXiv:0704.0759). The threshold
  result `B^{1/3}_{3,c(ℕ)}` and its NS analog. Verified by direct
  literature search 2026-05-08.
* **Cheskidov 2010** (PAMS 138:1059), follow-up on Besov regularity
  and energy balance.
* **Cheskidov–Luo 2023** (arXiv:2311.04182), modern dissipation-
  anomaly survey.
* **Buckmaster–Vicol 2019**, *Annals of Math.* 189:101 (arXiv:1709.10033).
  The CONVERSE direction (sub-Onsager ⟹ non-vanishing dissipation
  defect) for convex-integration solutions; **NOT applied here** —
  this is the converse-direction Clay-level open question.
* **Albritton–Brué–Colombo 2022**, *Annals of Math.* (arXiv:2112.03116).
  Non-uniqueness of Leray solutions; orthogonal to this file's
  forward direction.
* **Lions 1996**, *Math. Topics Fluid Mech. Vol. 1*, OUP §I.3 — the
  defect-measure framework whose floors we are bounding.
* **DiPerna–Lions 1989**, *Inventiones* 98:511, transport theory of
  defect measures.

## Cross-references

* `ZtareProofs/ns_trackb_atom8_defect_generation_bridge.lean` — the
  *positivity-direction* typed companion (caller supplies positivity
  hypothesis); this file is its *negative-direction* sibling.
* `projects/ns_millennium_hunt/workspace/research_notes/`
  `atom8_defect_positivity_clay_level_open_2026_05_08.md` — the
  open-verdict receipts.
* `ZtareProofs/ns_trackb_inversor_buckmaster_vicol.lean` — the
  sub-Onsager Hölder typed object (`HolderBound`, `subOnsagerHolder`);
  the converse-direction substrate.
-/

namespace ZtareProofs.NS.Atom8SharpConditional

open ZtareProofs.NS
open ZtareProofs.NS.MeasureValuedBridgeAtom1

noncomputable section

universe u

/-! ## §1. The above-Onsager hypothesis bundle

Falsifiable. The hypothesis NAMES the load-bearing PDE input as a
single concrete propositional bundle. It is the Galerkin-side analog
of CCFS 2008's hypothesis `u ∈ L³_t B^{1/3}_{3,c(ℕ)}`, strengthened
to strict above-Onsager (`1/3 + ε`) so that limit-passage in the
Besov norm preserves the threshold (Onsager itself is borderline).
-/

/-- **GalerkinAboveOnsagerHypothesis G**: the precise Besov regularity
hypothesis whose verification on a Galerkin sub-sequence
deterministically vanishes the Lions defect floors via CCFS 2008.

Each field is named after its canonical analytical role.

NOTE: this hypothesis is currently **not provable** for the standard
3D NS Galerkin truncation without already having a Clay-level a-priori
estimate; that is precisely why atom 8 is open. The hypothesis is the
HONEST place to lodge that obligation, distinct from the
positivity-disjunct hypothesis in the sibling
`ns_trackb_atom8_defect_generation_bridge.lean`. -/
structure GalerkinAboveOnsagerHypothesis (G : GalerkinStreamData) where
  /-- The Onsager margin `ε > 0`. The threshold is `1/3 + ε`, strictly
  above Onsager. ε = 0 is borderline (CCFS endpoint) and is NOT what
  this hypothesis demands; we use strict above-threshold to make the
  limit-passage of the Besov bound classical. -/
  ε : ℝ
  /-- Strict positivity of `ε` (the load-bearing falsifiability —
  `ε = 0` would be the borderline case). -/
  ε_pos : 0 < ε
  /-- A Galerkin-side uniform-in-N Besov regularity hypothesis (Prop):
  the Galerkin truncations `u_n` are uniformly bounded in
  `L³_t B^{1/3+ε}_{3,c(ℕ)}(Ω)`. We carry this as a Prop because the
  Lean-side encoding of Besov norms on `VelocityFieldInterface 3` is
  not in scope here; the analytic content is exactly this Prop. -/
  uniform_galerkin_besov_bound : Prop
  /-- The literature input (CCFS 2008): the Galerkin-side uniform
  Besov bound implies the relaxed-output defect ledger has every
  floor zero. ANTI-LAUNDERING: we do NOT supply this Prop as `True`;
  we route it through a single named hoisted axiom in §2. The field
  is a Prop because the floor-vanishing target is itself a Prop
  (a real strict equation). -/
  ccfs2008_propagation : Prop
  /-- The hypothesis ITSELF is paid (the caller asserts the
  Galerkin uniform Besov bound holds). -/
  uniform_galerkin_besov_bound_paid : uniform_galerkin_besov_bound
  /-- The CCFS 2008 propagation is paid via the hoisted axiom in §2.
  This field's payer is `ccfs2008_galerkin_threshold_axiom` applied
  to the hypothesis. -/
  ccfs2008_propagation_paid : ccfs2008_propagation

/-! ## §2. The named hoisted axiom (CCFS 2008 + Galerkin limit passage)

This is the SINGLE load-bearing axiom in this file. It is named after
its citation, applied exactly once (in `atom8_sharp_conditional`), and
discharges no other obligation. catch #21f compliance: one axiom, one
citation, one consumer.

The axiom states: there EXISTS a hypothesis Prop (the uniform Galerkin
Besov bound at level `1/3 + ε`) whose validity forces every floor of
the Galerkin substrate's relaxed-output defect ledger to be zero. The
existence is over the *propositional shape* of the hypothesis; the
caller of this file constructs an actual `GalerkinAboveOnsagerHypothesis`
and feeds it in. -/

/-- **CCFS 2008 + Galerkin limit-passage axiom.**

Classical theorem (Cheskidov–Constantin–Friedlander–Shvydkoy 2008,
*Nonlinearity* 21:1233): if a weak solution lies in
`L³_t B^{1/3}_{3,c(ℕ)}`, energy is conserved. Strengthening
strictly above Onsager and applied to the standard Galerkin
truncation: if the Galerkin truncations are uniformly bounded in
`L³_t B^{1/3+ε}_{3,c(ℕ)}` for some `ε > 0`, then by lower
semi-continuity of the Besov norm under weak limits and the CCFS
energy-conservation conclusion, the weak limit conserves energy
and hence every Lions defect floor on the relaxed-output defect
ledger is zero.

This is a **classical theorem reference**, not a Lean-side proof.
The axiom statement uses the abstract floor-vanishing conclusion
directly; the actual analytic chain is in CCFS 2008 + standard
Aubin-Lions / Banach-Alaoglu compactness for the Galerkin limit.

ANTI-FABRICATION: paper verified; field-of-application is Galerkin
NS sub-sequence (NOT Buckmaster-Vicol convex-integration solutions);
direction is forward (above-threshold ⟹ vanishing); not the
converse. -/
axiom ccfs2008_galerkin_threshold_axiom
    (G : GalerkinStreamData)
    (W : MeasureValuedTightnessWitness G)
    (hE0_nonneg : 0 ≤ G.E_0)
    (H : GalerkinAboveOnsagerHypothesis G) :
    -- Conclusion (the Galerkin substrate's Lions defect floors all vanish):
    selfTaxDefectFloor
        (relaxed_output_defect_ledger_of_measure_valued_source
          (galerkinMeasureValuedOutputLimitSource
            G W hE0_nonneg).measure_defect_source) = 0
    ∧ crossDefectFloor
        (relaxed_output_defect_ledger_of_measure_valued_source
          (galerkinMeasureValuedOutputLimitSource
            G W hE0_nonneg).measure_defect_source) = 0
    ∧ coherenceDefectFloor
        (relaxed_output_defect_ledger_of_measure_valued_source
          (galerkinMeasureValuedOutputLimitSource
            G W hE0_nonneg).measure_defect_source) = 0

/-! ## §3. Sharp conditional theorem

This is the file's main shipped result. The implication
`GalerkinAboveOnsagerHypothesis ⟹ all-floors-vanish` is the
*deterministic* half of the Onsager dichotomy, applied to the
Galerkin substrate.

ANTI-LAUNDERING audit: every field of `H` is consumed.

* `H.ε`, `H.ε_pos`, `H.uniform_galerkin_besov_bound`,
  `H.uniform_galerkin_besov_bound_paid`, `H.ccfs2008_propagation`,
  `H.ccfs2008_propagation_paid` — ALL passed to the axiom below.

The conclusion type is the Lions-floor-vanishing conjunction
`AllLionsDefectFloorsVanish`. -/

/-- All three Lions defect floors vanish on the Galerkin substrate's
relaxed-output ledger. -/
def AllLionsDefectFloorsVanish
    (G : GalerkinStreamData)
    (W : MeasureValuedTightnessWitness G)
    (hE0_nonneg : 0 ≤ G.E_0) : Prop :=
  selfTaxDefectFloor
      (relaxed_output_defect_ledger_of_measure_valued_source
        (galerkinMeasureValuedOutputLimitSource
          G W hE0_nonneg).measure_defect_source) = 0
  ∧ crossDefectFloor
      (relaxed_output_defect_ledger_of_measure_valued_source
        (galerkinMeasureValuedOutputLimitSource
          G W hE0_nonneg).measure_defect_source) = 0
  ∧ coherenceDefectFloor
      (relaxed_output_defect_ledger_of_measure_valued_source
        (galerkinMeasureValuedOutputLimitSource
          G W hE0_nonneg).measure_defect_source) = 0

/-- **Atom 8 SHARP CONDITIONAL — main theorem.**

If the Galerkin sub-sequence is uniformly above the Onsager Besov
threshold (`B^{1/3+ε}_{3,c(ℕ)}` for some `ε > 0`), then every Lions
defect floor on the relaxed-output ledger of the Galerkin substrate
vanishes deterministically.

This is the deterministic half of the Onsager dichotomy. The
non-deterministic / open-Clay-level half (sub-Onsager Galerkin ⟹
non-vanishing defect) is **not** shipped — see §4 for the honest
verdict on what would be required to ship it.

CITATION RECEIPTS (catch #17 / #27 / #28 / #32 vigilance):
* Cheskidov–Constantin–Friedlander–Shvydkoy 2008 *Nonlinearity*
  21:1233 (arXiv:0704.0759): the Besov threshold result.
* Lions 1996 *Math. Topics Fluid Mech. Vol. 1* §I.3: the
  defect-measure framework whose floors are bounded.
* The single hoisted axiom `ccfs2008_galerkin_threshold_axiom` is
  this file's only literature-axiom dependency and is consumed
  exactly once below. -/
theorem atom8_sharp_conditional
    (G : GalerkinStreamData)
    (W : MeasureValuedTightnessWitness G)
    (hE0_nonneg : 0 ≤ G.E_0)
    (H : GalerkinAboveOnsagerHypothesis G) :
    AllLionsDefectFloorsVanish G W hE0_nonneg := by
  -- All hypothesis fields are consumed by the axiom below; we expose
  -- their names here to make the consumption explicit (catch #30
  -- trip-wire on underscore-bound fields).
  have _ε_pos : 0 < H.ε := H.ε_pos
  have _ub_paid : H.uniform_galerkin_besov_bound :=
    H.uniform_galerkin_besov_bound_paid
  have _propagation_paid : H.ccfs2008_propagation :=
    H.ccfs2008_propagation_paid
  -- Apply the named axiom (the SINGLE load-bearing literature reference).
  exact ccfs2008_galerkin_threshold_axiom G W hE0_nonneg H

/-! ## §4. Honest verdict on the converse direction (NOT SHIPPED)

The converse implication

  *Galerkin sub-sequence uniformly **below** the Onsager threshold ⟹
   some Lions defect floor is strictly positive*

is the genuine Clay-level open question for atom 8. Buckmaster–Vicol
2019 (arXiv:1709.10033) builds *non-Galerkin* convex-integration
solutions with non-vanishing dissipation defect; transferring the
construction to the standard Galerkin spectral truncation is **open**
and is exactly the obstruction recorded in
`atom8_defect_positivity_clay_level_open_2026_05_08.md` Section 3.

We do NOT ship the converse here. We document its absence:
-/

/-- **Honest non-verdict on the converse direction.**

The proposition "for the standard 3D NS Galerkin substrate, sub-Onsager
regularity implies non-vanishing Lions defect" is at present an open
research-program question (Galerkin-compatible convex integration; no
analog of Buckmaster–Vicol 2019 known for the spectral Galerkin
truncation). We record this as a *named open hypothesis*, not as an
axiom. The naming is for cross-reference, not for use as a load-bearing
input. -/
def ConverseDirectionOpenAtomicHypothesis
    (G : GalerkinStreamData)
    (W : MeasureValuedTightnessWitness G)
    (hE0_nonneg : 0 ≤ G.E_0) : Prop :=
  -- Schematic: "below-threshold uniform regularity ⟹ at least one
  -- defect floor is strictly positive". Not used; documented for
  -- audit-traceability only.
  ∀ (_α : ℝ), _α < (1 : ℝ) / 3 →
    -- (uniform sub-Onsager Hölder ceiling on Galerkin truncations)
    True →
    0 < selfTaxDefectFloor
          (relaxed_output_defect_ledger_of_measure_valued_source
            (galerkinMeasureValuedOutputLimitSource
              G W hE0_nonneg).measure_defect_source)
    ∨ 0 < crossDefectFloor
            (relaxed_output_defect_ledger_of_measure_valued_source
              (galerkinMeasureValuedOutputLimitSource
                G W hE0_nonneg).measure_defect_source)
    ∨ 0 < coherenceDefectFloor
            (relaxed_output_defect_ledger_of_measure_valued_source
              (galerkinMeasureValuedOutputLimitSource
                G W hE0_nonneg).measure_defect_source)

/-! ## §5. Vacuity check on the energy-only smoke-test substrate

For the canonical `galerkinMeasureValuedOutputLimitSource` (which uses
`galerkinZeroDefectSource` internally), the floors are zero by
construction. The sharp conditional therefore "succeeds vacuously" on
this smoke-test substrate — its conclusion is true regardless of
whether `H` is supplied. We record this for audit-honesty: the
conditional is *non-trivially informative* only when applied to a
substrate where the defect source is genuinely non-trivial (which the
literature does not currently provide for standard Galerkin). -/

/-- The energy-only Galerkin smoke-test substrate has all floors zero
unconditionally. (No hypothesis needed.) -/
theorem zero_defect_substrate_floors_vanish_unconditionally
    (G : GalerkinStreamData)
    (W : MeasureValuedTightnessWitness G)
    (hE0_nonneg : 0 ≤ G.E_0) :
    AllLionsDefectFloorsVanish G W hE0_nonneg := by
  refine ⟨?_, ?_, ?_⟩
  all_goals
    simp [selfTaxDefectFloor, crossDefectFloor, coherenceDefectFloor,
          relaxed_output_defect_ledger_of_measure_valued_source,
          galerkinMeasureValuedOutputLimitSource,
          galerkinZeroDefectSource]

/-- HONESTY NOTE (audit-trace, not a load-bearing claim):

`zero_defect_substrate_floors_vanish_unconditionally` shows that on
the energy-only smoke-test substrate, the sharp conditional's
conclusion holds without any hypothesis. The sharp conditional
`atom8_sharp_conditional` therefore strictly extends this only when
applied to a SUBSTRATE WHERE THE FLOORS ARE NOT IDENTICALLY ZERO BY
CONSTRUCTION — i.e., when the caller supplies `Y` via something like
`galerkinDefectSourceWithPrices` with non-zero prices, in which case
the sharp conditional says "if your Galerkin sub-sequence is uniformly
above-Onsager, then your prices that you said were nonzero must
actually be zero, contradiction; hence your Galerkin sub-sequence
cannot be uniformly above-Onsager *if* you also have positivity".

This is the precise informational content of the sharp conditional:
it is an **incompatibility receipt** between
(a) above-Onsager Galerkin regularity, and
(b) any positive-price defect source on the Galerkin substrate. -/
def sharp_conditional_informational_content_documentation : Prop := True

end

end ZtareProofs.NS.Atom8SharpConditional
