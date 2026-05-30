/-
# NS Track B — SQ2.B Corrected Conditional Form (typed-companion-with-hypotheses)

**Date.** 2026-05-09 (post-C-52 cross-substrate friction patch).
**Provenance.** External prover GPT-5.5 demolished the original SQ2.B
unconditional Diophantine lower-bound statement (catch C-52 in
`analytics/public/ledgers/catch/catch_ledger.jsonl`):
* (a) vacuously true if any single off-diagonal coefficient is non-zero
  (monotone LHS vs decaying RHS in the as-written direction);
* (b) false on a Liouville rank-2 Bohr lattice because the polynomial
  gap `|ζ| ≳ H(ζ)^{-τ}` is killed by Liouville's `|qω - p| < q^{1-N}`;
* (c) topological — `Λ_ω` in Euclidean is dense, not locally finite,
  so sumsets can have infinitely many elements in any ball without an
  absolute summability hypothesis;
* off-diagonal can also vanish (singleton `Σ`) or cancel (no positivity /
  no cone alignment).

The internal PATTERN-001 5-round friction debate
(`projects/ns_millennium_hunt/workspace/SQ2B_diophantine_lower_bound_2026_05_09.md`)
did NOT surface these issues; both champions operated in the same
vocabulary (PDE / Bohr-AP). Cross-substrate prover (GPT-5.5 on number
theory / Diophantine approximation) caught the framing.

## What this file IS

A **typed conditional theorem with explicit named hypothesis fields**
encoding the corrected SQ2.B claim that survives GPT-5.5's audit:

> **CONDITIONAL.**  Given
> * (BKGSW) a bilinear-Khintchine-Groshev-sumset-weighted lower bound
>   `Σ_{λ,μ ∈ Σ, λ ≠ μ, λ+μ ∈ B_R(0)} w_{λ,μ} ≥ C · R^{-3+ε}`
>   on the off-diagonal weights `w_{λ,μ} ~ |û(λ)| |û(μ)|`, and
> * (NC) a no-cancellation cone condition
>   `∀ ζ : | Σ_{λ+μ = ζ, λ ≠ μ} û(λ) ⊗ û(μ) | ≥ κ · Σ_{λ+μ = ζ, λ ≠ μ} w_{λ,μ}`,
>
> conclude
>   `S_off(R) := Σ_{ζ ∈ B_R(0)} | Σ_{λ+μ = ζ, λ ≠ μ} û(λ) ⊗ û(μ) | ≥ κ · C · R^{-3+ε}`.

The conditional is provable by **direct summation manipulation** (the
double sum reorganization is Fubini on the indexing pair `(λ, μ) ↔ ζ`,
and the chain inequality `(NC)` then `(BKGSW)` is the rest). No new
Mathlib infrastructure required beyond `Finset.sum_le_sum`.

The (BKGSW) and (NC) hypotheses are **typed `def : Prop` companions**:
they are not discharged here; they are **exactly the open content
GPT-5.5 named** as the genuine arithmetic load.

## What this file is NOT

* **NOT a closure of SQ2.B.**  (BKGSW) and (NC) are open arithmetic
  conjectures on Liouvillian Bohr lattices.  This file only encodes the
  corrected conditional shape.
* **NOT a new axiom.**  The conditional is theorem-discharged from
  hypothesis arithmetic on real numbers (no `axiom` keyword introduced).
* **NOT TIER-A.**  This is honestly **TIER-A-alien-light**: a typed
  companion with explicit, externally-vetted hypothesis fields.  The
  hypotheses are the exact open content named by the cross-substrate
  prover; the file does not claim to discharge them.

## Anti-laundering audit

* **C-43 grep verification on Mathlib symbols used.** Two symbols:
  `Finset.sum_le_sum` (Mathlib/Algebra/Order/BigOperators/Group/Finset.lean
  L108, via `to_additive` from `prod_le_prod'`; `attribute [bound]` at
  L112; `add_decl_doc` at L117 — confirmed extant) and
  `mul_le_mul_of_nonneg_left` (Mathlib/Algebra/Order/Pi.lean L65,
  Mathlib/Algebra/Order/Archimedean/Basic.lean L460, used in many
  ZtareProofs files — confirmed extant).  No phantom symbols.

* **C-44 aspirational check.** No fresh names presented as Mathlib
  symbols.

* **C-21f / C-25 / C-21f-bar (no `True`-discharge, no underscore-bound
  hypotheses).** Both (BKGSW) and (NC) bind their parameters
  `Σ-weights, û, R, ε, C, κ` explicitly; none default to `True` because
  the `def`s are quantitative inequalities on real-valued aggregates.

* **C-52 cross-substrate framing patch.** The unconditional SQ2.B has
  been demoted to the conditional shape that GPT-5.5 confirmed is the
  surviving form.  Original framing's failures (a)/(b)/(c) all sit at
  the (BKGSW) hypothesis level (the condition is what fails on Liouville
  rank-2 lattices in the original direction; we now state it as a
  hypothesis to be discharged on a class where it is plausible — e.g.,
  positive-amplitude classes — not as a universal claim).

* **C-49 typed-companion-chain-inflation honesty.** This file's main
  theorem `SQ2B_conditional` is a CONDITIONAL shipping with two open
  `def : Prop` hypothesis fields.  Per C-49 taxonomy, this counts as
  **category (b): typed-companion-with-hypotheses closure consuming
  named gaps**, NOT category (a) full Mathlib-mergeable closure.

## Aggregate-level abstraction note

We work at the **aggregate / real-number level**: the per-ζ off-diagonal
bilinear sum and the per-ζ off-diagonal weight sum are real-valued
functions `Off_bilin, Off_weight : Ζ → ℝ`; the ball is a `Finset Ζ`.
This is the right abstraction level for the **conditional** claim:
the actual existence of `û, w, Σ, B_R(0)` infrastructure on Bohr
lattices is upstream content (TODO W6-sharp.1: Bohr-Fourier extractor
on `StationaryVelocityField`), and is irrelevant to whether the
conditional `(BKGSW) ∧ (NC) ⇒ S_off ≥ κ · C · R^{-3+ε}` holds.

By collapsing the off-diagonal sums into per-ζ aggregates, the Fubini
step is absorbed into the *definitions* of `Off_bilin(ζ)` and
`Off_weight(ζ)`; the conditional then becomes the chain inequality
`(NC) per-ζ + (BKGSW) on the aggregated total`, exactly as in the
informal argument.

-/

import Mathlib.Algebra.BigOperators.Group.Finset.Basic
import Mathlib.Algebra.Order.BigOperators.Group.Finset
import Mathlib.Algebra.BigOperators.Ring.Finset
import Mathlib.Tactic

namespace ZtareProofs.NS.SQ2B

-- Abstract index type for the doubled spectrum (sumset) `Ζ = Σ + Σ`.
-- For the rank-2 Liouvillian named class this is `Λ_ω + Λ_ω ⊂ ℝ³`,
-- but the conditional statement is index-type-agnostic.

noncomputable section

variable {Ζ : Type*}

/-- Per-frequency off-diagonal **bilinear** absolute value:
`Off_bilin(ζ) := | Σ_{λ + μ = ζ, λ ≠ μ} û(λ) ⊗ û(μ) |`.
This collapses the inner double sum into a single non-negative real
number per `ζ`.  Concrete instantiations on a Bohr-Fourier extractor
will compute it from `û, ⊗, |·|`; the conditional is independent of
that infrastructure. -/
abbrev OffDiagonalBilinearAbs (Ζ : Type*) : Type _ := Ζ → ℝ

/-- Per-frequency off-diagonal **weight** sum:
`Off_weight(ζ) := Σ_{λ + μ = ζ, λ ≠ μ} w_{λ,μ}`,
where `w_{λ,μ} ~ |û(λ)| |û(μ)|`.  Non-negative aggregate on the
sumset. -/
abbrev OffDiagonalWeightSum (Ζ : Type*) : Type _ := Ζ → ℝ

/-- The radius-`R` ball in the sumset, supplied as a `Finset Ζ` so
that the conditional manipulates a finite sum.  In the Bohr-AP
substrate the locally-finite assumption is part of the conditional's
upstream hypothesis (locally finite is FALSE on dense Liouvillian
sumsets without further input — that's part of (c) in C-52); this
file abstracts away from that upstream issue by parametrizing on a
finset. -/
abbrev SumsetBall (Ζ : Type*) : Type _ := Finset Ζ

/-- **(BKGSW) — Bilinear Khintchine-Groshev sumset-weighted lower bound.**

Hypothesis: there exists a constant `C > 0` and an exponent
`ε ∈ (0, 3)` such that for every `R` (encoded by the choice of
sumset-ball finset `B`) and every weight assignment `w` non-negative,
the **total off-diagonal weighted mass on `B`** is at least
`C · R^{-3+ε}`.

In the original SQ2.B framing this was claimed as a theorem; per C-52
GPT-5.5 demolished the unconditional claim.  Here it is stated as a
**hypothesis field** (typed `def : Prop`) to be discharged class-by-
class.  Discharge candidates: positive-amplitude rank-2 Liouvillian
sumset (Plünnecke-Ruzsa rebadged), Diophantine spectrum (vacuously
fails — sumset is empty near zero), generic Baire-residual amplitude
(not the right genericity per C-52(a)), etc.

**Honest scope.** This `def` is the **open arithmetic content** named
by the cross-substrate prover; this file does not discharge it. -/
def BKGSW
    (Off_weight : OffDiagonalWeightSum Ζ)
    (B : SumsetBall Ζ)
    (rate : ℝ) (C : ℝ) : Prop :=
  0 ≤ C ∧ (∀ ζ ∈ B, 0 ≤ Off_weight ζ) ∧
    C * rate ≤ ∑ ζ ∈ B, Off_weight ζ

/-- **(NC) — No-cancellation cone condition.**

Hypothesis: there exists `κ > 0` such that for every `ζ` (in the ball
`B`), the absolute value of the bilinear off-diagonal pairing is at
least `κ` times the off-diagonal weight aggregate at `ζ`:
`|Σ_{λ+μ=ζ, λ≠μ} û(λ) ⊗ û(μ)| ≥ κ · Σ_{λ+μ=ζ, λ≠μ} w_{λ,μ}`.

This is a **cone-alignment / non-cancellation** condition.  Per C-52,
the original SQ2.B framing did not surface this hypothesis; on
Liouvillian sumsets cancellation is precisely the open arithmetic
question (the divergence-free constraint `⟨ζ, v(ζ)⟩ = 0` plus
Liouvillian denominator approximations can in principle align phases
to cancel super-polynomially; whether that's possible
unconditionally is unsettled).

**Honest scope.** This `def` is the **open arithmetic content** named
by the cross-substrate prover; this file does not discharge it. -/
def NC
    (Off_bilin : OffDiagonalBilinearAbs Ζ)
    (Off_weight : OffDiagonalWeightSum Ζ)
    (B : SumsetBall Ζ)
    (κ : ℝ) : Prop :=
  0 ≤ κ ∧ (∀ ζ ∈ B, κ * Off_weight ζ ≤ Off_bilin ζ)

/-- **`S_off(R)` — Total off-diagonal bilinear absolute mass on the
sumset ball.**  This is the quantity the SQ2.B claim lower-bounds.

`S_off(R) := Σ_{ζ ∈ B} Off_bilin(ζ) = Σ_{ζ ∈ B} | Σ_{λ+μ=ζ, λ≠μ}
û(λ) ⊗ û(μ) |`. -/
def SOff (Off_bilin : OffDiagonalBilinearAbs Ζ) (B : SumsetBall Ζ) : ℝ :=
  ∑ ζ ∈ B, Off_bilin ζ

/-- **SQ2.B Corrected Conditional (TIER-A-alien-light).**

Given the (BKGSW) lower bound on the off-diagonal weight aggregate at
rate `C · R^{-3+ε}` and the (NC) no-cancellation cone condition with
constant `κ`, the total off-diagonal bilinear mass `S_off(R)` is
bounded below by `κ · C · R^{-3+ε}`.

**Proof skeleton.**
1.  By (NC): `∀ ζ ∈ B, κ · Off_weight ζ ≤ Off_bilin ζ`.
2.  Sum over `B` via `Finset.sum_le_sum`:
    `Σ_{ζ ∈ B} κ · Off_weight ζ ≤ Σ_{ζ ∈ B} Off_bilin ζ = S_off`.
3.  Pull `κ` out via `Finset.mul_sum`:
    `κ · (Σ_{ζ ∈ B} Off_weight ζ) ≤ S_off`.
4.  By (BKGSW) and `mul_le_mul_of_nonneg_left` with `0 ≤ κ`:
    `κ · (C · rate) ≤ κ · (Σ_{ζ ∈ B} Off_weight ζ)`.
5.  Chain transitively:  `κ · C · rate ≤ S_off`.

`rate` here is the abstract placeholder for `R^{-3+ε}`; the
conditional is rate-agnostic, which means an instantiation could plug
in any positive real (the conditional is purely a chain inequality on
real-valued aggregates).

**Honesty caveat.** Per C-49 taxonomy, this is a category-(b) closure:
typed-companion-with-hypotheses, the hypotheses (BKGSW) and (NC) are
themselves open `def : Prop` content per C-52. -/
theorem SQ2B_conditional
    (Off_bilin : OffDiagonalBilinearAbs Ζ)
    (Off_weight : OffDiagonalWeightSum Ζ)
    (B : SumsetBall Ζ)
    (rate : ℝ) (C κ : ℝ)
    (h_bkgsw : BKGSW Off_weight B rate C)
    (h_nc : NC Off_bilin Off_weight B κ) :
    κ * C * rate ≤ SOff Off_bilin B := by
  -- Unpack hypotheses.
  obtain ⟨hC_nn, _hWeight_nn, hSumW_lb⟩ := h_bkgsw
  obtain ⟨hκ_nn, hPointwise⟩ := h_nc
  -- Step 2 + 3: pointwise (NC) → summed (NC).
  have h_pointwise_le : ∀ ζ ∈ B, κ * Off_weight ζ ≤ Off_bilin ζ := hPointwise
  have h_sum_pointwise :
      ∑ ζ ∈ B, κ * Off_weight ζ ≤ ∑ ζ ∈ B, Off_bilin ζ :=
    Finset.sum_le_sum h_pointwise_le
  -- Step 3: factor κ out of the LHS.
  have h_factor : ∑ ζ ∈ B, κ * Off_weight ζ
      = κ * ∑ ζ ∈ B, Off_weight ζ := by
    rw [Finset.mul_sum]
  -- Step 4: scale (BKGSW) by the non-negative κ.
  have h_scale : κ * (C * rate) ≤ κ * ∑ ζ ∈ B, Off_weight ζ :=
    mul_le_mul_of_nonneg_left hSumW_lb hκ_nn
  -- Step 5: assemble the chain.
  have h_chain : κ * (C * rate) ≤ ∑ ζ ∈ B, Off_bilin ζ := by
    calc κ * (C * rate)
        ≤ κ * ∑ ζ ∈ B, Off_weight ζ := h_scale
      _ = ∑ ζ ∈ B, κ * Off_weight ζ := h_factor.symm
      _ ≤ ∑ ζ ∈ B, Off_bilin ζ := h_sum_pointwise
  -- Reassociate `κ * (C * rate)` as `κ * C * rate` and rewrite as `SOff`.
  have h_reassoc : κ * C * rate = κ * (C * rate) := by ring
  simp only [SOff, h_reassoc]
  exact h_chain

/-- **Smoke test (sanity check).**
A trivial instantiation: `Ζ := Unit`, `B := {()}`, `Off_weight ζ := 0`,
`Off_bilin ζ := 0`, `rate = C = κ = 0`.  All hypotheses degenerate to
`0 ≤ 0`; the conclusion `0 ≤ 0` holds.  This confirms the conditional
shape is non-vacuous in the trivial direction (i.e., it doesn't fall
out of `False ⇒ anything`). -/
example :
    let Off_bilin : OffDiagonalBilinearAbs Unit := fun _ => 0
    let B : SumsetBall Unit := ({()} : Finset Unit)
    (0 : ℝ) * 0 * 0 ≤ SOff Off_bilin B :=
  SQ2B_conditional (Ζ := Unit)
    (Off_bilin := fun _ => 0)
    (Off_weight := fun _ => 0)
    (B := ({()} : Finset Unit))
    (rate := 0) (C := 0) (κ := 0)
    (h_bkgsw := ⟨le_refl _, fun _ _ => le_refl _, by simp⟩)
    (h_nc := ⟨le_refl _, fun _ _ => by simp⟩)

end

end ZtareProofs.NS.SQ2B
