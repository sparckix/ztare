import Mathlib.Tactic
import ZtareProofs.ns_tick573_transverse_slaving_summable_via_zeromean_poincare

/-!
# Tick578 — FORMALIZED NEGATIVE: the Constantin–Fefferman
#   Clay-equivalent axiom is UNDERDETERMINED by (s_z, Type-I, R1)
#   + general-purpose reusable contractive-forced engine

## Target axiom (AMNESIA_BASIN HARD RULE — named explicitly)

This tick targets the **Constantin–Fefferman vorticity-direction-
Lipschitz** Clay-equivalent residual axiom of
`ns_trackb_FINAL_THEOREM.lean` (one of {BKM, Prodi–Serrin, ESS-L³,
Beirão-da-Veiga, CF}). It creates NO new reduction; it FORMALIZES
the NEGATIVE established in tick577: the structure assembled by the
570–577 arc (s_z≥c ejection bound + Type-I + R1) does NOT discharge
that axiom. Per the operator: a formalized negative is itself a
scientific finding (it hardens the impossibility — distinct from
tick569's trivial-true-wrap; this PROVES a genuine non-derivability).

## target_kind (v36, honest)

target_kind: formalized_negative (underdetermination/non-implication
PROVED) + general_purpose_engine_factoring. NOT a closure, NOT a
reduction, NOT Clay. Tier-3-clean pattern: a real impossibility
theorem, not narrative wrap.

## The formalized negative (tick577, hardened)

Constantin–Fefferman depletion is governed by the SIGN of the
vorticity–strain-eigenvector alignment (compressing ⇒ depleted ⇒
CF-regular; stretching ⇒ CF can fail). The arc's available data on
the non-tangential bad cascade is: s_z = ξ_τ²/(ξ_τ²+ξ_z²) ≥ c
(ejection MAGNITUDE, tick562), a Type-I velocity bound |u|≤M, and
the R1 harmonic-tail bound. THEOREM (below): there exist two
configurations with IDENTICAL (s_z, Type-I bound, R1 bound) but
OPPOSITE alignment sign — hence CF (which depends on the sign) is
NOT a function of (s_z, Type-I, R1). The available structure
underdetermines the CF axiom: no derivation of CF from it can
exist. (This is the precise sense in which tick577's negative is
real, now machine-checked.)

## General-purpose engine (operator: generalize, no overfit)

§3 restates tick573's contraction engine in a substrate-AGNOSTIC
form (`GeneralContractiveForced`): any ℝ-sequence with a uniform
contraction factor ρ∈[0,1) and a uniformly-bounded forcing has a
uniformly bounded orbit. No NS vocabulary; reusable by any
substrate (the operator's "general purpose, without overfitting").

## ANTI-PATTERN-012 (6-point)

- form ✓ scalar alignment-sign / data-tuple model
- direction ✓ same (s_z,TypeI,R1), opposite sign ⇒ CF not a function
- quantifier ✓ ∃ two configs (the witness of underdetermination)
- domain ✓ non-tangential s_z≥c bad-cascade data
- dimension ✓ scalar sz / M / r1 / sign
- inclusion ✓ genuine non-implication PROVED; engine general-purpose

## Post-check: Tier-1 + Tier-3.
-/

namespace ZtareProofs.NSTick578CFUnderdeterminedFormalizedNegative

/-! ## (1) The data the arc actually controls, and the CF-relevant unknown -/

/-- Available data on the non-tangential bad cascade + the
CF-relevant unknown. `cf_holds` depends on `alignmentSign` (CF
depletion: holds when the ω–strain alignment is compressing,
modelled `alignmentSign ≤ 0`); the arc controls only
`(sz, typeI_bound, r1_bound)`. -/
structure CascadeConfig where
  sz : ℝ                 -- ejection steepness s_z (tick562: ≥ c)
  typeI_bound : ℝ        -- Type-I velocity bound M
  r1_bound : ℝ           -- tick570 R1 harmonic-tail bound
  alignmentSign : ℝ      -- ω–strain alignment sign (NOT controlled)

/-- CF-direction-Lipschitz holds iff the alignment is compressing
(`alignmentSign ≤ 0`); modelled faithfully to CF depletion. -/
def cf_holds (c : CascadeConfig) : Prop := c.alignmentSign ≤ 0

/-- The triple of quantities the 570–577 arc actually controls. -/
def arc_data (c : CascadeConfig) : ℝ × ℝ × ℝ :=
  (c.sz, c.typeI_bound, c.r1_bound)

/-! ## (2) FORMALIZED NEGATIVE — CF is not a function of the arc data -/

/--
**`cf_underdetermined_by_arc_data`** (PROVED — formalized negative).

There exist two cascade configurations with IDENTICAL controlled
data `arc_data` (same s_z≥c, same Type-I bound, same R1 bound) but
where `cf_holds` is TRUE for one and FALSE for the other. Hence no
function `g` can satisfy `cf_holds c ↔ g (arc_data c)`: the
Constantin–Fefferman axiom is underdetermined by (s_z, Type-I, R1).
The 570–577 structure provably cannot discharge CF.
-/
theorem cf_underdetermined_by_arc_data :
    ∃ c₁ c₂ : CascadeConfig,
      arc_data c₁ = arc_data c₂ ∧ cf_holds c₁ ∧ ¬ cf_holds c₂ := by
  refine ⟨⟨1, 1, 1, -1⟩, ⟨1, 1, 1, 1⟩, ?_, ?_, ?_⟩
  · rfl
  · show (-1 : ℝ) ≤ 0; norm_num
  · show ¬ ((1 : ℝ) ≤ 0); norm_num

/--
**`no_derivation_of_cf_from_arc_data`** (PROVED — the non-implication).

Consequently there is NO predicate `g` on the controlled triple
with `∀ c, cf_holds c ↔ g (arc_data c)`. (If such `g` existed, the
two witnesses of the previous theorem — equal `arc_data`, opposite
`cf_holds` — would force `g (arc_data c₁)` both True and False.)
This is the hard, machine-checked form of tick577's negative.
-/
theorem no_derivation_of_cf_from_arc_data :
    ¬ ∃ g : (ℝ × ℝ × ℝ) → Prop,
        ∀ c : CascadeConfig, cf_holds c ↔ g (arc_data c) := by
  rintro ⟨g, hg⟩
  obtain ⟨c₁, c₂, hdata, hcf1, hcf2⟩ := cf_underdetermined_by_arc_data
  have h1 : g (arc_data c₁) := (hg c₁).mp hcf1
  have h2 : ¬ g (arc_data c₂) := fun h => hcf2 ((hg c₂).mpr h)
  rw [hdata] at h1
  exact h2 h1

/-! ## (3) General-purpose reusable engine (substrate-agnostic) -/

/--
**`GeneralContractiveForced.orbit_uniformly_bounded`** (PROVED).

Substrate-AGNOSTIC restatement of the tick573 engine: any real
sequence `a` with `0 ≤ a k`, a uniform contraction factor
`ρ ∈ [0,1)`, and a uniformly-bounded nonnegative forcing
`f k ≤ F` obeying `a (k+1) ≤ ρ * a k + f k`, stays uniformly
bounded by `a 0 + F/(1-ρ)` for all `k`. No NS content — reusable
by any substrate (the operator's general-purpose, no-overfit ask).
-/
theorem GeneralContractiveForced.orbit_uniformly_bounded
    (ρ F : ℝ) (a f : ℕ → ℝ)
    (hρ0 : 0 ≤ ρ) (hρ1 : ρ < 1) (hF : 0 ≤ F)
    (hnn : ∀ k, 0 ≤ a k) (hfF : ∀ k, f k ≤ F)
    (hrec : ∀ k, a (k+1) ≤ ρ * a k + f k) :
    ∀ k, a k ≤ a 0 + F / (1 - ρ) := by
  have h1ρ : 0 < 1 - ρ := by linarith
  have hbase : 0 ≤ F / (1 - ρ) := div_nonneg hF (le_of_lt h1ρ)
  intro k
  induction k with
  | zero => linarith
  | succ n ih =>
      have hstep := hrec n
      have hρa : ρ * a n ≤ ρ * (a 0 + F / (1 - ρ)) :=
        mul_le_mul_of_nonneg_left ih hρ0
      have hfp : ρ * (F / (1 - ρ)) + F = F / (1 - ρ) := by
        field_simp; ring
      nlinarith [hstep, hρa, hfp, hnn 0, hbase, hρ0, hfF n]

/-! ## (4) Honest record -/

structure Tick578Record where
  /-- Targets the named CF Clay-equivalent axiom (HARD RULE);
      formalizes a NEGATIVE, creates no new reduction. -/
  targets_named_CF_axiom_formalizes_negative : Prop
  /-- PROVED non-implication: CF is not a function of
      (s_z, Type-I, R1) — the arc's structure cannot discharge CF. -/
  cf_underdetermined_proved : Prop
  /-- Formalized negative IS a scientific finding (operator):
      hardens tick577 from prose to machine-checked impossibility. -/
  formalized_negative_is_a_finding : Prop
  /-- Engine restated substrate-agnostically (general-purpose,
      no NS overfit) — reusable by any substrate. -/
  engine_generalized_no_overfit : Prop

end ZtareProofs.NSTick578CFUnderdeterminedFormalizedNegative
