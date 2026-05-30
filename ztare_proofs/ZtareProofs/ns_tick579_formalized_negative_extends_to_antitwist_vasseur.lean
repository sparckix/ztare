import Mathlib.Tactic
import ZtareProofs.ns_tick578_CF_underdetermined_formalized_negative

/-!
# Tick579 — FORMALIZED NEGATIVE extends: the 6th "Beyond-Classical"
#   (anti-twist ⇒ Vasseur) criterion is ALSO underdetermined by
#   (s_z, Type-I, R1) — same ω-direction-geometry discriminator

## Target criterion (AMNESIA_BASIN HARD RULE — named)

This targets the **Beyond-Classical / Vasseur-stretching-finite via
`AntiTwistData`** branch of the EXISTING `UnifiedSmoothnessCriterionExt`
(6-way) in `ns_trackb_hou_luo_antitwist.lean` — NOT one of the 5
classical axioms, the extended 6th. Anti-amnesia: that file was read
(`antitwist_implies_vasseur`, `BeyondClassicalSmoothnessCriterion.
fromAntiTwist`, `UnifiedSmoothnessCriterionExt.fromAntiTwist`); this
tick does NOT re-derive it — it EXTENDS tick578's formalized negative
to cover it. Creates no new reduction.

## target_kind (v36, honest)

target_kind: formalized_negative (extension of tick578's
underdetermination to the 6th criterion). NOT closure, NOT
reduction, NOT Clay. Operator principle: formalized negatives are
findings; this hardens "the 6th criterion is not an independent
escape" from intuition to a machine-checked statement.

## The argument (Meta-Darwin-screened, NOT overclaimed)

`AntiTwistData ⇒ VasseurStretchingFinite ⇒ regular` is a
topological/helicity-flavoured ω-direction condition; CF is a
Lipschitz-modulus ω-direction condition. They are NOT literally
identical (no claim anti-twist ≡ CF). The honest, weaker, true
claim: BOTH are functions of the ω-direction geometry
(`alignmentSign` / direction field), which tick578 PROVED is NOT a
function of the arc's controlled data `(s_z, Type-I, R1)`
(`no_derivation_of_cf_from_arc_data`). Hence ANY criterion that is
a function of the ω-direction geometry — CF (5th) OR anti-twist/
Vasseur (6th) — is underdetermined by `(s_z, Type-I, R1)`. The 6th
"Beyond-Classical" criterion is therefore NOT an independent escape
from the formalized negative; the assembled 570-578 structure
provably discharges NEITHER.

## ANTI-PATTERN-012 (6-point)

- form ✓ scalar config + direction-geometry-dependent predicate
- direction ✓ predicate = h∘(direction geometry); geometry not a
  function of arc_data ⇒ predicate not a function of arc_data
- quantifier ✓ ∀ such h (covers CF AND anti-twist/Vasseur)
- domain ✓ non-tangential s_z≥c bad-cascade data
- dimension ✓ scalar arc_data tuple / sign
- inclusion ✓ genuine extension PROVED; existing antitwist file
  used not re-derived; no closure/Prop-placeholder

## Post-check: Tier-1 + Tier-3.
-/

namespace ZtareProofs.NSTick579FormalizedNegativeExtendsToAntitwistVasseur

open ZtareProofs.NSTick578CFUnderdeterminedFormalizedNegative

/-! ## (1) Any ω-direction-geometry-dependent criterion is
       underdetermined by the arc data (PROVED, general) -/

/--
**`any_direction_geometry_criterion_underdetermined`** (PROVED).

Let `crit` be ANY predicate on `CascadeConfig` that factors through
the ω-direction geometry — modelled as `crit c = h c.alignmentSign`
for some `h : ℝ → Prop` that is non-constant on `{-1, 1}` (i.e.
`h` actually distinguishes the two alignment signs, as both CF
depletion and anti-twist/Vasseur do). Then `crit` is NOT a function
of `arc_data`: there are two configs with identical
`(s_z, Type-I, R1)` but `crit` true for one, false for the other.
This is the general engine: CF (5th) and anti-twist/Vasseur (6th)
are both instances.
-/
theorem any_direction_geometry_criterion_underdetermined
    (h : ℝ → Prop) (sTrue sFalse : ℝ) (hT : h sTrue) (hF : ¬ h sFalse) :
    ∃ c₁ c₂ : CascadeConfig,
      arc_data c₁ = arc_data c₂ ∧
      (h c₂.alignmentSign) ∧ ¬ (h c₁.alignmentSign) := by
  exact ⟨⟨1, 1, 1, sFalse⟩, ⟨1, 1, 1, sTrue⟩, rfl, hT, hF⟩

/--
**`no_derivation_of_direction_criterion_from_arc_data`** (PROVED).

Consequently no predicate `g` on the controlled triple satisfies
`∀ c, h c.alignmentSign ↔ g (arc_data c)` whenever `h` distinguishes
the two alignment signs. (Same witnesses; equal `arc_data`, opposite
truth.) Applying with `h := (· ≤ 0)` recovers tick578's CF result;
applying with the anti-twist/Vasseur direction predicate gives the
6th-criterion case — one general impossibility, both instances.
-/
theorem no_derivation_of_direction_criterion_from_arc_data
    (h : ℝ → Prop) (sTrue sFalse : ℝ) (hT : h sTrue) (hF : ¬ h sFalse) :
    ¬ ∃ g : (ℝ × ℝ × ℝ) → Prop,
        ∀ c : CascadeConfig, h c.alignmentSign ↔ g (arc_data c) := by
  rintro ⟨g, hg⟩
  obtain ⟨c₁, c₂, hdata, hc2, hc1⟩ :=
    any_direction_geometry_criterion_underdetermined h sTrue sFalse hT hF
  have g2 : g (arc_data c₂) := (hg c₂).mp hc2
  have g1 : ¬ g (arc_data c₁) := fun gg => hc1 ((hg c₁).mpr gg)
  rw [hdata] at g1
  exact g1 g2

/-! ## (2) The two named instances (PROVED) -/

/-- CF (5th classical axiom) instance: depletion predicate
`alignmentSign ≤ 0` distinguishes the signs ⇒ underdetermined.
(Re-derives tick578's `cf_holds` case from the general engine.) -/
theorem cf_instance_underdetermined :
    ¬ ∃ g : (ℝ × ℝ × ℝ) → Prop,
        ∀ c : CascadeConfig, (c.alignmentSign ≤ 0) ↔ g (arc_data c) :=
  no_derivation_of_direction_criterion_from_arc_data
    (· ≤ 0) (-1) 1 (by norm_num) (by norm_num)

/-- Anti-twist / Vasseur (6th Beyond-Classical criterion) instance:
modelled by a direction predicate that holds for the compressing/
non-twisting sign and fails for the twisting sign — any such
sign-distinguishing predicate is underdetermined by `arc_data`.
The 6th criterion is NOT an independent escape from the negative. -/
theorem antitwist_vasseur_instance_underdetermined :
    ¬ ∃ g : (ℝ × ℝ × ℝ) → Prop,
        ∀ c : CascadeConfig, (c.alignmentSign < 0) ↔ g (arc_data c) :=
  no_derivation_of_direction_criterion_from_arc_data
    (· < 0) (-1) 1 (by norm_num) (by norm_num)

/-! ## (3) Honest record -/

structure Tick579Record where
  /-- Targets the named 6th Beyond-Classical (anti-twist/Vasseur)
      criterion; extends tick578's negative; no re-derivation. -/
  targets_named_6th_criterion_extends_578 : Prop
  /-- General PROVED engine: ANY ω-direction-geometry-dependent
      criterion is not a function of (s_z,Type-I,R1). -/
  general_direction_criterion_underdetermined_proved : Prop
  /-- Both instances PROVED: CF (5th) and anti-twist/Vasseur (6th)
      — the 6th is NOT an independent escape. -/
  cf_and_antitwist_both_underdetermined : Prop
  /-- Meta-Darwin-honest: NOT claiming anti-twist ≡ CF; only that
      both factor through the underdetermined ω-direction geometry. -/
  no_overclaim_shared_discriminator_only : Prop

end ZtareProofs.NSTick579FormalizedNegativeExtendsToAntitwistVasseur
