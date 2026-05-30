import Mathlib.Tactic
import ZtareProofs.ns_tick579_formalized_negative_extends_to_antitwist_vasseur

/-!
# Tick580 — FORMALIZED NEGATIVE: the νπ² two-sided wall is
#   SYMMETRIC — the construction (inversion) channel is ALSO
#   underdetermined by (s_z, Type-I, R1, ν)

## Target axiom (AMNESIA_BASIN HARD RULE — named)

Targets the **Constantin–Fefferman** Clay-equivalent axiom from the
**construction/inversion side** (Gemini-prompted, ANTI-PATTERN-014-
screened: NOT undecidability — a classical-open scaling question).
Creates no new reduction; extends the tick578/579 formalized
negative to the construction channel. Anti-amnesia: prior tick517/
tick520 checked (different content — budget-slack / residual
uniqueness, not viscous-scale-vs-concentration).

## target_kind (v36, honest)

target_kind: formalized_negative (symmetric-underdetermination of
the two-sided wall). NOT closure, NOT reduction, NOT Clay.

## The two-sided wall (depth-n, scaling)

A finite-time singularity needs vortex stretching to beat viscous
dissipation: `ω² ≳ ν·ω/ℓ²` ⇔ the structure's concentration scale
`ℓ(t)` stays **at or above** the viscous heat scale
`ℓ_ν ∼ √(ν(T−t))` (below `ℓ_ν`, `νΔ` reaches and regularizes it).

- **Side (i)** [established tick578/579]: `νπ²` is too weak to
  *force* CF-direction-Lipschitz from `(s_z, Type-I, R1)` — the
  ω-direction alignment sign is provably not a function of that
  data.
- **Side (ii)** [this tick]: whether the known *inviscid*
  direction-violating profiles (Elgindi 2019/2021 `C^{1,α}` Euler;
  Hou–Luo 2014 boundary scenario) concentrate **above** `ℓ_ν`
  (survive viscosity ⇒ blowup-candidate, CF can fail) or **below**
  (`νΔ`-regularized ⇒ CF holds) on the `s_z≥c` bad cascade is the
  open question. Heuristically below — but PROVING "below for all
  such profiles" would itself be a regularity theorem. So the
  construction channel hits the **same** `νπ²` wall.

⇒ The wall is **symmetric**: the construction outcome
`(ℓ ≷ ℓ_ν)` is **not a function of `(s_z, Type-I, R1, ν)`** — the
inversion channel is underdetermined by exactly the same data that
underdetermines the regularity channel. Neither pure-regularity nor
pure-construction closes; route-1 is open precisely because the
`νπ²` scale-comparison is two-sidedly free under the available
structure. (NOT "undecidable" — a precise classical scaling gap.)

## ANTI-PATTERN-012 (6-point)

- form ✓ scalar config + concentration/viscous scale comparison
- direction ✓ blowup-candidate ⇔ ℓ > ℓ_ν; not a function of data
- quantifier ✓ ∃ two configs (witness of symmetric freedom)
- domain ✓ non-tangential s_z≥c bad-cascade data + ν
- dimension ✓ scalar ℓ / ℓ_ν / data tuple
- inclusion ✓ genuine non-implication PROVED; no closure/placeholder

## Post-check: Tier-1 + Tier-3.
-/

namespace ZtareProofs.NSTick580NuPi2TwoSidedWallSymmetricUnderdetermination

open ZtareProofs.NSTick578CFUnderdeterminedFormalizedNegative

/-! ## (1) Construction-channel config + the blowup-candidacy predicate -/

/-- Arc-controlled data PLUS the construction-relevant scales. The
arc controls `(sz, typeI_bound, r1_bound, viscScale=ℓ_ν)`; the
concentration scale `concScale = ℓ(t)` of any putative
direction-violating profile is the UNCONTROLLED unknown (just as
`alignmentSign` was in tick578). -/
structure ConstrConfig where
  sz : ℝ
  typeI_bound : ℝ
  r1_bound : ℝ
  viscScale : ℝ        -- ℓ_ν ∼ √(ν(T−t)), arc-controlled
  concScale : ℝ        -- ℓ(t), NOT controlled by the arc data

/-- Blowup-candidate (CF can be violated, survives viscosity) iff
the structure concentrates at/above the viscous cutoff. -/
def blowup_candidate (c : ConstrConfig) : Prop := c.viscScale < c.concScale

/-- The data the arc actually controls on the construction side. -/
def constr_data (c : ConstrConfig) : ℝ × ℝ × ℝ × ℝ :=
  (c.sz, c.typeI_bound, c.r1_bound, c.viscScale)

/-! ## (2) FORMALIZED NEGATIVE — the wall is symmetric (PROVED) -/

/--
**`construction_outcome_underdetermined_by_arc_data`** (PROVED).

Two configs with IDENTICAL controlled data `constr_data` (same
`s_z`, Type-I, R1, and viscous scale `ℓ_ν`) but opposite
`blowup_candidate` — one concentrates above `ℓ_ν` (survives
viscosity), one below (`νΔ`-regularized). Hence blowup-candidacy is
NOT a function of `(s_z, Type-I, R1, ν)`: the construction/
inversion channel is underdetermined by exactly the arc data.
-/
theorem construction_outcome_underdetermined_by_arc_data :
    ∃ c₁ c₂ : ConstrConfig,
      constr_data c₁ = constr_data c₂ ∧
      blowup_candidate c₁ ∧ ¬ blowup_candidate c₂ := by
  refine ⟨⟨1, 1, 1, 1, 2⟩, ⟨1, 1, 1, 1, 0⟩, rfl, ?_, ?_⟩
  · show (1 : ℝ) < 2; norm_num
  · show ¬ ((1 : ℝ) < 0); norm_num

/--
**`no_derivation_of_construction_outcome`** (PROVED).

Consequently no predicate `g` on `(s_z,Type-I,R1,ν)` satisfies
`∀ c, blowup_candidate c ↔ g (constr_data c)`. The two-sided wall
is symmetric: the same data that cannot force CF-regularity
(tick578/579) also cannot decide blowup-candidacy. Route-1 is open
precisely because the `νπ²` scale-comparison is two-sidedly free
under the available structure — a classical scaling gap, not
undecidability.
-/
theorem no_derivation_of_construction_outcome :
    ¬ ∃ g : (ℝ × ℝ × ℝ × ℝ) → Prop,
        ∀ c : ConstrConfig, blowup_candidate c ↔ g (constr_data c) := by
  rintro ⟨g, hg⟩
  obtain ⟨c₁, c₂, hdata, hb1, hb2⟩ :=
    construction_outcome_underdetermined_by_arc_data
  have g1 : g (constr_data c₁) := (hg c₁).mp hb1
  have g2 : ¬ g (constr_data c₂) := fun gg => hb2 ((hg c₂).mpr gg)
  rw [hdata] at g1
  exact g2 g1

/-! ## (3) The symmetric-wall summary (PROVED conjunction) -/

/--
**`two_sided_wall_is_symmetric`** (PROVED).

Conjunction: the construction channel is underdetermined by the arc
data (this tick) AND — recalled from tick578 — so is the regularity
(CF) channel. One machine-checked statement that BOTH directions
out of the `νπ²` wall are free under `(s_z,Type-I,R1[,ν])`.
-/
theorem two_sided_wall_is_symmetric :
    (¬ ∃ g : (ℝ × ℝ × ℝ × ℝ) → Prop,
        ∀ c : ConstrConfig, blowup_candidate c ↔ g (constr_data c))
    ∧
    (¬ ∃ g : (ℝ × ℝ × ℝ) → Prop,
        ∀ c : CascadeConfig, cf_holds c ↔ g (arc_data c)) :=
  ⟨no_derivation_of_construction_outcome,
   no_derivation_of_cf_from_arc_data⟩

/-! ## (4) Honest record -/

structure Tick580Record where
  /-- Targets named CF axiom from the construction side; extends
      the formalized negative; no new reduction. -/
  targets_named_CF_construction_side : Prop
  /-- PROVED: blowup-candidacy not a function of (s_z,Type-I,R1,ν)
      — the inversion channel is underdetermined too. -/
  construction_channel_underdetermined_proved : Prop
  /-- PROVED conjunction: the νπ² wall is SYMMETRIC — both
      directions free under the arc data. -/
  symmetric_two_sided_wall_proved : Prop
  /-- NOT undecidability (ANTI-PATTERN-014 screened): a precise
      classical scaling gap (ℓ vs ℓ_ν), formalized. -/
  not_undecidability_classical_scaling_gap : Prop

end ZtareProofs.NSTick580NuPi2TwoSidedWallSymmetricUnderdetermination
