import Mathlib.Tactic

/-!
# Tick582 — C7 viscous-alignment-surplus is bounded by a FIXED
#   constant via the EXISTING `cf_geometric_depletion_l2`
#   (anti-amnesia: composed with prior work, not re-derived)

## Manifest decision (HARD RULE)

Target node: **C7** (viscous alignment surplus). Anti-amnesia: the
O(1) manifest + agentic "grep mechanism, check before build" rule
caught that `ns_trackb_biot_savart_kernel.lean` ALREADY formalizes
the Constantin–Fefferman 1993 Prop 2.1 geometric depletion
(`cf_geometric_depletion_l2`: `‖∇u‖_{L²} ≤ (C₂+C₃·L_ξ)‖ω‖_{L²}`,
LINEAR in the direction-Lipschitz constant). `overlap_detected`
was *False* — only the agentic rule caught it. This tick does NOT
re-derive depletion; it COMPOSES C7 with that existing result.

## target_kind (v36, honest)

target_kind: formalized_reduction (genuine algebraic lemma; NO
closure-forward — the tick581 Tier-3-FAIL lesson). NOT closure,
NOT Clay. Tier-3-clean pattern (real inequality lemma like the
tick573 engine / tick578-580 negatives), no `… ⇒ route1_closes`.

## The genuine content (depth-n, composes C7 + existing depletion)

The C7 surplus per unit enstrophy is `A := ξ·Sξ − ν|∇ξ|²`. The
EXISTING `cf_geometric_depletion_l2` makes the stretching `ξ·Sξ`
controlled **linearly** by `L := L_ξ ≈ |∇ξ|`:
`ξ·Sξ ≲ C₂ + C₃·L` (per unit enstrophy; the linear—not
quadratic—`L_ξ` dependence is exactly the CF 1993 load-bearing
point, already noted in that file). The viscous depletion term is
**quadratic**: `ν·L²`. Hence

  `A(L) ≤ (C₂ + C₃·L) − ν·L²`.

A downward parabola in `L`: its maximum over all `L ≥ 0` is the
FIXED constant `S_max = C₂ + C₃²/(4ν)`, independent of `L`. So the
surplus cannot grow with the direction gradient — the quadratic
viscous term always eventually dominates the linear depleted
stretching.

**Consequence (prose, manifest-recorded, NOT Lean-forwarded):**
the C7 budget `Σ (A)_+ |ω|²` is `≤ S_max · Σ ∫_{fresh}|ω|²` — a
**fresh local-enstrophy budget**, i.e. the pre-existing
scale-freshness / bounded-overlap atom (perennial-atom memory,
tick551–553 terminus, linked to C5). So C7 is a genuine
*reformulation* but NOT an independent escape: via the existing
CF-depletion it routes back into the freshness core. (Recorded in
ns_residual_manifest.md; no closure claim.)

## ANTI-PATTERN-012 (6-point)

- form ✓ scalar downward-parabola `A(L) ≤ (C₂+C₃L) − νL²`
- direction ✓ linear-up minus quadratic-down ⇒ fixed max `S_max`
- quantifier ✓ ∀ L ≥ 0
- domain ✓ per-unit-enstrophy surplus, direction-Lipschitz `L`
- dimension ✓ scalar L / C₂ / C₃ / ν
- inclusion ✓ uses EXISTING cf_geometric_depletion_l2 (cited, not
  re-derived); genuine algebraic lemma; NO closure-forward

## Post-check: Tier-1 + Tier-3 + cold Opus steelman (ANTI-PATTERN-014).
-/

namespace ZtareProofs.NSTick582C7SurplusBoundedViaExistingCFDepletion

/-! ## (1) Surplus is a downward parabola in the direction gradient (PROVED) -/

/--
**`surplus_le_linear_minus_quadratic`** (PROVED, definitional bound).

Given the depleted-stretching bound `xiSxi ≤ C₂ + C₃·L` (from the
EXISTING `cf_geometric_depletion_l2`, linear in `L = L_ξ ≈ |∇ξ|`)
and the viscous term `ν·L²`, the surplus `A := xiSxi − ν·L²`
satisfies `A ≤ (C₂ + C₃·L) − ν·L²`.
-/
theorem surplus_le_linear_minus_quadratic
    (xiSxi C2 C3 ν L : ℝ)
    (hdep : xiSxi ≤ C2 + C3 * L) :
    xiSxi - ν * L^2 ≤ (C2 + C3 * L) - ν * L^2 := by
  linarith [hdep]

/--
**`surplus_bounded_by_fixed_Smax`** (PROVED — the genuine content).

For `ν > 0`, the downward parabola `(C₂ + C₃·L) − ν·L²` is bounded
above for ALL `L` by the FIXED constant `S_max = C₂ + C₃²/(4ν)`,
independent of `L`. Hence the C7 surplus cannot grow with the
vorticity-direction gradient: viscous depletion (quadratic) always
caps the depleted stretching (linear). Proof: complete the square,
`(C₂+C₃L) − νL² = S_max − ν(L − C₃/(2ν))² ≤ S_max`.
-/
theorem surplus_bounded_by_fixed_Smax
    (C2 C3 ν L : ℝ) (hν : 0 < ν) :
    (C2 + C3 * L) - ν * L^2 ≤ C2 + C3^2 / (4 * ν) := by
  have hsq : 0 ≤ ν * (L - C3 / (2 * ν))^2 :=
    mul_nonneg (le_of_lt hν) (sq_nonneg _)
  have hkey : (C2 + C3 * L) - ν * L^2
      = (C2 + C3^2 / (4 * ν)) - ν * (L - C3 / (2 * ν))^2 := by
    field_simp
    ring
  rw [hkey]; linarith [hsq]

/--
**`surplus_uniformly_capped`** (PROVED — composition).

Combining: for `ν>0`, ANY surplus value `A = xiSxi − νL²` whose
stretching obeys the existing linear depletion `xiSxi ≤ C₂+C₃L`
satisfies `A ≤ S_max := C₂ + C₃²/(4ν)`, a constant independent of
the direction gradient `L`. This is why C7 reduces to a fresh
*enstrophy* budget (prose/manifest), not an independent escape.
-/
theorem surplus_uniformly_capped
    (xiSxi C2 C3 ν L : ℝ) (hν : 0 < ν)
    (hdep : xiSxi ≤ C2 + C3 * L) :
    xiSxi - ν * L^2 ≤ C2 + C3^2 / (4 * ν) :=
  le_trans (surplus_le_linear_minus_quadratic xiSxi C2 C3 ν L hdep)
           (surplus_bounded_by_fixed_Smax C2 C3 ν L hν)

/-! ## (2) Honest record -/

structure Tick582Record where
  /-- Anti-amnesia: composed C7 with the EXISTING
      cf_geometric_depletion_l2 (overlap_detected was False; agentic
      grep-mechanism rule caught it), did not re-derive. -/
  composed_existing_cf_depletion_not_rederived : Prop
  /-- PROVED: linear depleted stretching − quadratic viscous term
      ⇒ surplus ≤ fixed S_max = C₂+C₃²/(4ν), independent of |∇ξ|. -/
  surplus_capped_by_fixed_constant_proved : Prop
  /-- Consequence (prose/manifest, NOT Lean-forwarded): C7 budget
      ⟺ fresh enstrophy budget = pre-existing freshness atom; C7 is
      a reformulation, NOT an independent escape. -/
  C7_reduces_to_freshness_atom_not_escape : Prop
  /-- Tier-3-clean pattern: genuine algebraic lemma, NO
      conditional-forward-to-closure (tick581 lesson applied). -/
  no_closure_forward_clean_lemma : Prop

end ZtareProofs.NSTick582C7SurplusBoundedViaExistingCFDepletion
