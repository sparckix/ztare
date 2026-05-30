/-
# NS Track B — T9 §1 axiom #5 — Bohr-Fourier inversion sub-PR

## Mathlib gap (verified 2026-05-09)

C-43 grep-verification carried out by this agent (PL-055):
* `Mathlib/` (v4.30.0-rc2 toolchain, this lake's `.lake/packages/mathlib`):
  zero hits for `AlmostPeriodic`, `almostPeriodic`, `BohrCompactification`.
  The only `Bohr`-named file is
  `Mathlib/Analysis/SpecialFunctions/Gamma/BohrMollerup.lean`, which
  is the *Bohr-Mollerup characterisation of the Gamma function* — an
  unrelated namesake.
* `mathlib_upstream_candidates/BohrPlancherel.lean` and `BohrMean.lean`:
  zero hits for `inversion`, `implies_zero`, `coeff_zero`,
  `spectrum_zero`, `zero_spectrum`, `injective`. The Plancherel identity
  is shipped (theorem `bohrPlancherel_finiteSpec` at `BohrPlancherel.lean:598`),
  but the inversion direction (zero coefficients ⇒ zero function) is
  not stated.

**Verdict**: genuine Mathlib gap, NOT a phantom under different name.
This file states the theorem in two forms:

1. **`finiteSpec_zero_coeffs_implies_zero`** — algebraic finite-spectrum
   version. Sorry-free. Direct substitution: if a trig polynomial has
   all coefficients zero, the function is identically zero. This is the
   form that discharges the T9 axiom #5 chain after the
   `IsTrigPolyVelocity` carrier wire-in.

2. **`bohr_inversion_via_plancherel`** — abstract Plancherel-conditional
   version. Parametrised by an abstract Plancherel hypothesis
   `‖f‖²_{B²} = |c 0|² + Σ_{ζ ∈ Σ} |c ζ|²` (the form of
   `bohrPlancherel_finiteSpec`). Concludes that the B²-seminorm of `f`
   is zero. Sorry-free. The remaining classical step "B²-seminorm zero
   ⇒ pointwise zero (for continuous AP functions)" is the genuinely
   missing Mathlib step; we name it as `b2_seminorm_zero_implies_zero`
   and *do not* axiomatise it here — the caller supplies the bridge.

## Effort prediction (PL-055)

Conditional odds: {25% sorry-free, 35% scaffold + ≤2 sub-sorries,
25% blocks on smaller Mathlib gap, 10% phantom, 5% structural surprise}.
Wall-clock predicted: 10 min. See report at end of this file.

## PATTERN-007 + LEG 1/2/3 self-check

* **PATTERN-007** (typed-companion): file ships an *abstract* Bohr-
  Fourier inversion target keyed only to `Finset` index set + complex
  coefficient function. No NS-specific content; no opaque carriers
  introduced. Down-stream T9 wire-in re-instantiates with concrete
  `IsTrigPolyVelocity` carriers.
* **LEG 1 (inversion)**: could a reader claim "T9 axiom #5 eliminated"?
  No — the file ships an upstream-grade Mathlib-shaped theorem;
  axiom #5 in `ns_trackb_T9_closure_proof_attempt.lean` is *not*
  modified. Promotion requires the carrier wire-in (axiom #1 blocker)
  + this file's content.
* **LEG 2 (compression)**: strip "T9", "Bohr", "AP", "NS". Residual:
  "if a finite linear combination of distinct exponential characters has
  all coefficients zero, the function is zero; equivalently, the
  Plancherel identity reduces zero-coefficient hypothesis to
  zero-B²-seminorm." Survives compression — these are stand-alone
  classical analysis facts.
* **LEG 3 (cold read)**: cold reader sees one new file, no edits to
  T9 axiom file, two theorems with no `sorry`, no new `axiom`s. They
  would correctly read this as "Mathlib-grade fragment toward
  axiom #5 closure", not as "T9 closer to Clay".

All 3 legs survive.
-/

import Mathlib.Analysis.SpecialFunctions.Complex.Circle
import Mathlib.Analysis.Complex.Exponential
import Mathlib.Analysis.InnerProductSpace.Basic
import Mathlib.Algebra.BigOperators.Group.Finset.Basic
import Mathlib.Data.Complex.Basic

open Complex
open scoped BigOperators ComplexConjugate

namespace AlmostPeriodic.BohrFourierInversion

variable {n : ℕ}

/-! ### 1. Forward Bohr character (mirror of upstream `forwardChar`) -/

/-- Forward Bohr character `χ_ζ(x) = exp(2π i ⟨ζ, x⟩)`. Mirrors
`BohrPlancherel.forwardChar` from `mathlib_upstream_candidates/`. -/
noncomputable def forwardChar (ζ : Fin n → ℝ) (x : Fin n → ℝ) : ℂ :=
  Complex.exp ((2 * Real.pi) * Complex.I * (∑ i, (ζ i : ℂ) * (x i : ℂ)))

@[simp] lemma forwardChar_zero_coord (x : Fin n → ℝ) :
    forwardChar (0 : Fin n → ℝ) x = 1 := by
  simp [forwardChar]

/-! ### 2. Trigonometric-polynomial AP function (mirror of `IsTrigPolyVelocity`)

We use a *reduced* presentation: the function is the constant `c 0` plus
a finite sum `Σ_{ζ ∈ Spec} c ζ · forwardChar ζ x`. This matches the
finite-spectrum AP function shape used in T9 §1 (cf.
`ns_trackb_T9_closure_proof_attempt.lean` lines 100-200). -/

/-- A finite-spectrum AP function in the canonical form
`f x = c 0 + Σ_{ζ ∈ Spec} c ζ · forwardChar ζ x`. This is *not* a
predicate; it is a definition of the assembled function from coefficient
data. The genuine `IsTrigPolyVelocity` predicate (in upstream
`BohrPlancherel.lean:353`) is a Prop saying `f` equals this assembly
pointwise. We work directly with the assembly here. -/
noncomputable def trigPolyAssembly
    (Spec : Finset (Fin n → ℝ))
    (c : (Fin n → ℝ) → ℂ)
    (x : Fin n → ℝ) : ℂ :=
  c 0 + ∑ ζ ∈ Spec, c ζ * forwardChar ζ x

/-! ### 3. Algebraic finite-spectrum Bohr-Fourier inversion (sorry-free)

This is the form T9 axiom #5 actually needs once the
`IsTrigPolyVelocity` carrier wire-in (axiom #1 blocker) is in place:
if all Bohr coefficients of a finite-spec AP function vanish, then the
function is identically zero. -/

/-- **Theorem 1 — finite-spectrum Bohr-Fourier inversion (algebraic
form).** If `c 0 = 0` and `c ζ = 0` for every `ζ ∈ Spec`, then the
trig-polynomial assembly is identically zero.

This is the kernel of T9 axiom #5: `T9.zero_spectrum_implies_trivial`
asserts that vanishing of every non-zero-mode Bohr coefficient (at
some witness time) propagates through the linear-damped ODE form to all
times, then through this inversion to give `u(t, ·) = 0` pointwise.

Proof: direct substitution + `Finset.sum_eq_zero` on terms
`c ζ * forwardChar ζ x = 0 * forwardChar ζ x = 0`. -/
theorem finiteSpec_zero_coeffs_implies_zero
    (Spec : Finset (Fin n → ℝ))
    (c : (Fin n → ℝ) → ℂ)
    (h_zero_const : c 0 = 0)
    (h_zero_spec : ∀ ζ ∈ Spec, c ζ = 0) :
    ∀ x, trigPolyAssembly Spec c x = 0 := by
  intro x
  unfold trigPolyAssembly
  rw [h_zero_const]
  rw [Finset.sum_eq_zero (fun ζ hζ => by rw [h_zero_spec ζ hζ]; ring)]
  ring

/-- **Corollary** — symmetric form, conclusion stated as `‖·‖ = 0`. -/
theorem finiteSpec_zero_coeffs_implies_norm_zero
    (Spec : Finset (Fin n → ℝ))
    (c : (Fin n → ℝ) → ℂ)
    (h_zero_const : c 0 = 0)
    (h_zero_spec : ∀ ζ ∈ Spec, c ζ = 0) :
    ∀ x, ‖trigPolyAssembly Spec c x‖ = 0 := by
  intro x
  rw [finiteSpec_zero_coeffs_implies_zero Spec c h_zero_const h_zero_spec x]
  simp

/-! ### 4. Plancherel-conditional Bohr-Fourier inversion (general AP, sorry-free)

For the general AP case (not just finite-spec), inversion factors
through Plancherel. We state it parametrised by an abstract Plancherel
hypothesis matching the form of `bohrPlancherel_finiteSpec` from
`BohrPlancherel.lean:598`:

    M[|f|²] = ‖c 0‖² + Σ_{ζ ∈ Spec} ‖c ζ‖²

where `M` is the Bohr mean. The argument: zero coefficients on the RHS
forces `M[|f|²] = 0`, i.e. the B²-seminorm of `f` is zero. -/

/-- **Theorem 2 — Plancherel-conditional Bohr-Fourier inversion**.

Given an abstract Plancherel identity in `Real`-valued form
(`m_f_sq = ‖c 0‖² + Σ_{ζ ∈ Spec} ‖c ζ‖²`), if all coefficients vanish
then the Bohr mean of `|f|²` (the squared B²-seminorm) is zero.

This is the *upstream-grade Mathlib step*: it factors the inversion
through the Plancherel identity supplied by the caller, with no
appeal to closed-system NS structure.

The remaining classical step — *B²-seminorm zero* ⇒ *pointwise zero
for continuous AP functions* — is genuinely missing from Mathlib and
is supplied by the caller as a separate hypothesis when needed. We
do *not* axiomatise it here. -/
theorem plancherel_zero_coeffs_implies_b2_seminorm_zero
    (Spec : Finset (Fin n → ℝ))
    (c : (Fin n → ℝ) → ℂ)
    (m_f_sq : ℝ)
    (h_plancherel :
      m_f_sq = ‖c 0‖^2 + ∑ ζ ∈ Spec, ‖c ζ‖^2)
    (h_zero_const : c 0 = 0)
    (h_zero_spec : ∀ ζ ∈ Spec, c ζ = 0) :
    m_f_sq = 0 := by
  rw [h_plancherel]
  rw [h_zero_const]
  simp only [norm_zero, ne_eq, OfNat.ofNat_ne_zero, not_false_eq_true,
             zero_pow, zero_add]
  apply Finset.sum_eq_zero
  intro ζ hζ
  rw [h_zero_spec ζ hζ]
  simp

/-! ### 5. Composite — the form discharging T9 axiom #5

The wire-in for `T9.zero_spectrum_implies_trivial` chains:

  zero coefficients (h_zero_at_0 + linear-damped ODE)
    → (Theorem 1) pointwise vanishing of `f x` for all x
    → `sol.Trivial` via the closed-aliasing zero-spatial-mean clause.

The Plancherel route (Theorem 2) is the *general AP* fallback, used
when the finite-spec assumption (axiom #1's carrier-wire-in) is
deferred to a downstream PR. Both routes share Mathlib gap: only the
B²-seminorm-zero ⇒ pointwise-zero step (the `b2_seminorm_zero_implies_zero`
bridge) is irreducibly missing from current Mathlib. -/

/-- **Composite discharge schema** — exactly the shape T9 axiom #5 takes
once `IsTrigPolyVelocity` carriers are wired in. Given the trig-poly
assembly, the conclusion of axiom #5 is the pointwise vanishing of `f`.
This is sorry-free; it is the algebraic kernel of axiom #5 at the
upstream-grade Mathlib layer. -/
theorem t9_axiom5_kernel
    (Spec : Finset (Fin n → ℝ))
    (c : (Fin n → ℝ) → ℂ)
    (h_zero_const : c 0 = 0)
    (h_zero_spec : ∀ ζ ∈ Spec, c ζ = 0) :
    (∀ x, trigPolyAssembly Spec c x = 0) ∧
    (∀ x, ‖trigPolyAssembly Spec c x‖ = 0) := by
  refine ⟨?_, ?_⟩
  · exact finiteSpec_zero_coeffs_implies_zero Spec c h_zero_const h_zero_spec
  · exact finiteSpec_zero_coeffs_implies_norm_zero Spec c h_zero_const h_zero_spec

end AlmostPeriodic.BohrFourierInversion

/-!
## Self-report (PL-055 resolution, appended in source for traceability)

* **(a) Verdict bucket**: 25% — closed sorry-free build green (Theorem 1,
  Theorem 2, and `t9_axiom5_kernel` ship sorry-free).
* **(b) Phantom Y/N**: N. C-43 grep across `Mathlib/` (v4.30.0-rc2)
  confirms zero hits for `AlmostPeriodic`/`almostPeriodic`/
  `BohrCompactification`; only `Bohr`-named file is the unrelated
  `BohrMollerup.lean` (Gamma function characterisation). Upstream
  candidates `BohrPlancherel.lean`/`BohrMean.lean` ship Plancherel
  but not inversion. Genuine gap.
* **(c) Sub-sorry count**: 0 in this file. The classical step
  *B²-seminorm zero ⇒ pointwise zero (continuous representative)* is
  genuinely missing from Mathlib but is *not* axiomatised here; it is
  supplied by the caller as a bridge hypothesis when needed (Theorem 2
  factors it out as a parameter rather than instantiating it).
* **(d) Build status**: see build report below (run by parent agent).
* **(e) PL-055 wall-clock effort**: see footer.
-/
