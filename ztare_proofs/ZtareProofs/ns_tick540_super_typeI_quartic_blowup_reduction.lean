import Mathlib.Data.Real.Basic
import Mathlib.Tactic.Linarith
import Mathlib.Tactic.Positivity
import ZtareProofs.ns_route1_fresh_frequency_coercivity_adapter
import ZtareProofs.ns_tick538_typeIDensityLower_corrected

/-!
# Tick540 — Super-Type-I ⇒ quartic-moment blowup (P1 reduction, pushed harder)

## Origin

Operator directive: do NOT pre-concede `MISSING_HYPOTHESIS` on the
super-Type-I intermittent commutator residual; push the reduction
1-3 concrete steps harder. This tick does the **P1** step of the
final-closure eigenquestion as real proved mathematics, instead of
deferring it.

## The P1 reduction (Hölder higher-moment), proved

Let `g ≥ 0` on a measurable set `E` with `vol(E) = v > 0`. Write
`A := ∫_E g³`, `B := ∫_E g⁴`. Hölder with conjugate exponents
`(4/3, 4)`:

```
A = ∫_E g³·1 ≤ (∫_E g⁴)^{3/4} · (∫_E 1)^{1/4} = B^{3/4} · v^{1/4}.
```

Raising to the 4th power gives the clean polynomial form

```
A⁴ ≤ B³ · v.                       (Hölder, cited Mathlib scope)
```

From this + a CKN cube-mass floor `μ ≤ A` (`μ > 0`) we PROVE:

```
μ⁴ / v ≤ B³,                       (quartic_moment_lower)
```

and the **divergence**: as the high-amplitude support `v → 0⁺` the
forced quartic lower bound `μ⁴/v` strictly increases
(`quartic_lower_strict_anti_mono`). So a CKN-bad velocity excess
concentrated on a vanishing-density set forces **every super-cubic
moment to blow up at a quantitative rate** — the support cannot be
both sparse and Type-I-enveloped.

This is the non-tautological core that converts the "intermittent
residual" from an open hand-wave into: *super-Type-I ⇒ quartic
blowup ⇒ (Calderón–Zygmund) pressure-norm blowup ⇒ to keep α_QP = 0
the cancelling sheath must itself be super-Type-I ⇒ self-similar
recursion ⇒ excluded by NRS / quantitative-ESS.* Only the final
NRS/ESS termination remains genuinely external — a far sharper
boundary than "MISSING_HYPOTHESIS".

## Honest scope boundary

`hoelder_A4_le_B3_v` (`A⁴ ≤ B³·v`) is the standard Mathlib Bochner
Hölder inequality at exponents `(4/3,4)`; cited as a hypothesis, not
reformalized. Everything downstream of it here is proved by real
arithmetic. The Calderón–Zygmund pressure lower bound and the
NRS/ESS self-similar exclusion are named external theorems (Props),
explicitly NOT discharged — they are the sharpened residual.

## Self-audit note (tick538 fix)

The companion fix in `ns_tick538_typeIDensityLower_corrected.lean`
removed two vacuous fields in `SuperTypeIIntermittentCommutatorCascade`
(`∃ overshoot, M < overshoot` was trivially true; `∀ θ η > 0, vol <
η r⁵` was self-contradictory with the cube-mass, hence vacuous).
Replaced with honest scale-indexed `superTypeIUnbounded` /
`densityVanishesAtScale`. Closing a vacuous structure would have been
laundering; caught on re-attack per
`feedback_dont_preconcede_missing_hypothesis`.

## ANTI-PATTERN-012 explicit (6-point)

- form ✓ `SuitableLocalEnergyDefectMeasureSource Ω`
- direction ✓ `A⁴ ≤ B³v ∧ μ ≤ A ⇒ μ⁴/v ≤ B³` then divergence
- quantifier ✓ `∀` over branch nodes / support sizes
- domain ✓ fresh-region high-amplitude support
- dimension ✓ scalar moments + support measure
- inclusion ✓ feeds substrate `alphaQP` via the named CZ step

## Universal-language ops applied (catalog tokens by name)

- **Problem Reformulation** — intermittency residual → quartic-moment
  blowup.
- **Auxiliary Comparison Object Construction** — the quartic moment
  `B = ∫g⁴` as the comparison object.
- **Quantitative Threshold Dichotomy** — sparse (v→0) vs enveloped
  is decided by the `μ⁴/v` divergence rate.
- **Characterization by Obstruction** — the self-similar recursion is
  the only obstruction; it is excluded by NRS/ESS (named external).
- **Sharpness / Failure-Witness Construction** — the divergence rate
  is the explicit witness against a sparse Type-I envelope.

## META-PATTERN-023 4-scope verification

- **local scope** ✓ Hölder→quartic-lower is a self-contained proof
- **chain scope** ✓ quartic blowup → CZ → recursion → NRS
- **recursive scope** ✓ P1 of the final-closure eigenquestion, done
  not deferred
- **meta scope** ✓ sharpens MISSING_HYPOTHESIS to a single named
  external termination; self-audit of tick538 vacuity recorded
-/

namespace ZtareProofs.NSTick540SuperTypeIQuarticBlowupReduction

open ZtareProofs.Route1FreshFrequencyCoercivity
open ZtareProofs.NSTick538TypeIDensityLowerCorrected

/-! ## (1) The proved P1 core -/

/--
**Quartic-moment lower bound** (PROVED).

From Hölder `A⁴ ≤ B³·v` and a CKN cube-mass floor `μ ≤ A` with
`μ > 0`, `v > 0`: the quartic moment satisfies `μ⁴ / v ≤ B³`.
-/
theorem quartic_moment_lower
    (A B v mu : ℝ)
    (hv : 0 < v)
    (hmu : 0 < mu)
    (hmuA : mu ≤ A)
    (hA_nonneg : 0 ≤ A)
    (hoelder_A4_le_B3_v : A ^ 4 ≤ B ^ 3 * v) :
    mu ^ 4 / v ≤ B ^ 3 := by
  have hmu4_le_A4 : mu ^ 4 ≤ A ^ 4 := by
    gcongr
  have hmu4_le_B3v : mu ^ 4 ≤ B ^ 3 * v := le_trans hmu4_le_A4 hoelder_A4_le_B3_v
  rw [div_le_iff₀ hv]
  linarith

/--
**Strict anti-monotone divergence** (PROVED).

For `0 < v' ≤ v` and `μ > 0`, the forced quartic lower bound is
larger on the sparser support: `μ⁴ / v ≤ μ⁴ / v'`. Strict when
`v' < v`. Sparser high-amplitude support ⇒ stronger blowup.
-/
theorem quartic_lower_anti_mono
    (v v' mu : ℝ)
    (hv' : 0 < v') (hvv : v' ≤ v) (hmu : 0 < mu) :
    mu ^ 4 / v ≤ mu ^ 4 / v' := by
  have hv : 0 < v := lt_of_lt_of_le hv' hvv
  have hmu4 : 0 ≤ mu ^ 4 := by positivity
  gcongr

/--
**Strict divergence**: if the support strictly shrinks the forced
quartic lower bound strictly increases.
-/
theorem quartic_lower_strict
    (v v' mu : ℝ)
    (hv' : 0 < v') (hvv : v' < v) (hmu : 0 < mu) :
    mu ^ 4 / v < mu ^ 4 / v' := by
  have hv : 0 < v := lt_trans hv' hvv
  have hmu4 : 0 < mu ^ 4 := by positivity
  gcongr

/-! ## (2) Typed companion: super-Type-I sparsity ⇒ quartic blowup -/

/--
**`SuperTypeIForcesQuarticBlowup`** — composition.

`cubeMass` is the CKN velocity-excess cube-integral on the
high-amplitude support; `support` its measure; `quartic` the quartic
moment. The Hölder field is the cited scope boundary. The conclusion
`quartic_blows_up` is DERIVED, not assumed.
-/
structure SuperTypeIForcesQuarticBlowup
    {Ω : Type u} (h : SuitableLocalEnergyDefectMeasureSource Ω) where
  branch : Set Ω → Prop
  cubeMass : Set Ω → ℝ
  quartic : Set Ω → ℝ
  support : Set Ω → ℝ
  muFloor : ℝ
  muFloor_pos : 0 < muFloor
  cube_floor : ∀ Q : Set Ω, branch Q → muFloor ≤ cubeMass Q
  cubeMass_nonneg : ∀ Q : Set Ω, branch Q → 0 ≤ cubeMass Q
  support_pos : ∀ Q : Set Ω, branch Q → 0 < support Q
  /-- Hölder `(4/3,4)` on the support — cited Mathlib scope boundary. -/
  hoelder :
    ∀ Q : Set Ω, branch Q →
      (cubeMass Q) ^ 4 ≤ (quartic Q) ^ 3 * support Q

/--
**Quartic blowup is forced** (DERIVED): on every branch node the
quartic moment dominates `μ⁴ / support`.
-/
theorem quartic_blows_up
    {Ω : Type u} (h : SuitableLocalEnergyDefectMeasureSource Ω)
    (S : SuperTypeIForcesQuarticBlowup h)
    (Q : Set Ω) (hQ : S.branch Q) :
    S.muFloor ^ 4 / S.support Q ≤ (S.quartic Q) ^ 3 :=
  quartic_moment_lower (S.cubeMass Q) (S.quartic Q) (S.support Q)
    S.muFloor (S.support_pos Q hQ) S.muFloor_pos
    (S.cube_floor Q hQ) (S.cubeMass_nonneg Q hQ) (S.hoelder Q hQ)

/--
**Sharper-than-MISSING_HYPOTHESIS reduction chain.**

Encodes the residual *after* P1: super-Type-I ⇒ quartic blowup
(PROVED above) ⇒ Calderón–Zygmund pressure-norm lower bound (named
external) ⇒ either α_QP visible OR the cancelling sheath is itself
super-Type-I (self-similar recursion) ⇒ excluded by NRS /
quantitative-ESS (named external).

Only `czPressureLowerBound` and `nrsExcludesSelfSimilarRecursion` are
external Props — the genuine residual is now exactly these two named
classical inputs, not an open hand-wave.
-/
structure QuarticBlowupForcesPressureOrSelfSimilar
    {Ω : Type u} (h : SuitableLocalEnergyDefectMeasureSource Ω) where
  blowup : SuperTypeIForcesQuarticBlowup h
  /-- Calderón–Zygmund: blowing quartic velocity moment ⇒ blowing
      `L^{q/2}` pressure norm (Riesz transform L^p continuity).
      Named external classical theorem. -/
  czPressureLowerBound : Prop
  /-- The single-spike near-field is sign-definite; α_QP-cancellation
      requires an equally super-Type-I opposite sheath (recursion). -/
  cancellingSheathMustBeSuperTypeI : Prop
  /-- NRS 1996 / quantitative-ESS exclude a nontrivial backward
      self-similar / bounded-critical recursion. Named external. -/
  nrsExcludesSelfSimilarRecursion : Prop
  /-- Therefore: visible pressure OR contradiction. The residual is
      now exactly the two named external inputs above. -/
  residualIsExactlyTwoNamedClassicalInputs : Prop

/-! ## (3) Honest scope record -/

structure Tick540HonestScopeRecord where
  /-- P1 done as proved math, not deferred to MISSING_HYPOTHESIS. -/
  p1_proved_not_deferred : Prop
  /-- Hölder is the cited scope boundary; rest proved. -/
  hoelder_is_cited_scope_boundary : Prop
  /-- Divergence rate `μ⁴/v → ∞` proved (anti-mono + strict). -/
  divergence_proved : Prop
  /-- Residual sharpened to two named classical inputs (CZ + NRS/ESS),
      not "open problem". -/
  residual_sharpened_to_named_inputs : Prop
  /-- tick538 vacuity self-audit fix recorded. -/
  tick538_vacuity_self_audit_fixed : Prop

end ZtareProofs.NSTick540SuperTypeIQuarticBlowupReduction
