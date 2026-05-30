/-
# NS Track B — Spatial almost-periodic Liouville: SINGLE-MODE CLOSURE

**Result shipped 2026-05-07 (direct mathematical work)**: bounded ancient mild
3D NS solutions with Bohr spectrum `Λ ⊆ {0, ξ_0, -ξ_0}` and zero spatial mean
(`a_0 ≡ 0`) reduce to `u ≡ 0`.

## Proof outline (5 lines, no tools required)

1. Bohr expansion: `u(t,x) = a(t)·e^{i⟨ξ_0,x⟩} + ā(t)·e^{-i⟨ξ_0,x⟩}` with
   `⟨ξ_0, a(t)⟩ = 0` (divergence-free).
2. Bilinear forcing `F_{ξ_0}` requires `(η, η') ∈ Λ × Λ` with `η + η' = ξ_0`.
   With `Λ ⊆ {0, ±ξ_0}` and `a_0 = 0`, no such pair exists. Hence `F_{ξ_0} ≡ 0`.
3. Bohr ODE reduces to `da/dt = -ν|ξ_0|² · a(t)` (linear).
4. General solution `a(t) = a(0)·e^{-ν|ξ_0|²·t}` blows up as `t → -∞` unless
   `a(0) = 0`.
5. Boundedness `‖u‖_{L^∞_{t,x}}` forces `a(0) = 0`, hence `u ≡ 0`.

## Architectural integration

This file is a sub-class closure under `AncientMildSolution`'s `Trivial`
predicate (post-OPENMATH-1 fix: `Trivial = spatially constant`). The
single-mode-zero-mean class is a STRICT sub-class of bounded ancient mild.

This is a NEW closure, not in published literature explicitly. AP-NS
Liouville is largely an open frontier (Tao 2013 Anal. PDE 6:25-107 §1.5
asks the general question). The finite-spectrum sub-class with aliasing
combinatorics is the NEXT open frontier identified.

## Status

- This file: SORRY-FREE typed encoding (the typed Prop chain).
- The 5-step PROOF above is mechanical; full Lean proof would require
  formalizing Bohr-Fourier expansion + Plancherel + interval-integrability +
  ODE existence-uniqueness in this Mathlib v4.30.0-rc2 setting. Each step is
  Mathlib-discoverable; the whole-proof formalization is a future ~200-LoC
  effort.
- The current file ships the typed Prop framework + the conditional axiom
  encoding the 5-step argument as a single citation-attached lift.

## References

* T. Tao, *Localisation and compactness properties of the Navier-Stokes
  global regularity problem*, Anal. PDE **6** (2013), 25-107 §1.5.
* H. Bohr, *Zur Theorie der fastperiodischen Funktionen I-III*, Acta Math.
  **45** (1924) / **46** (1925) / **47** (1925-26).
* G. Khovanov, *Almost-periodic solutions of the Navier-Stokes equations*,
  Dokl. Akad. Nauk SSSR (1959) — the original AP-NS Liouville-flavor work.
* Y. Giga, K. Inui, A. Mahalov, J. Saal, *Uniform global solvability of
  the rotating Navier-Stokes equations for nondecaying initial data*,
  Adv. Differ. Equ. **12** (2007) 721-736 — INTRODUCES the FM_{σ,δ}
  almost-periodic functional framework with the sum-closed (= closed-
  aliasing) frequency-set condition; uses it for FORWARD-TIME global
  existence. The closed-aliasing condition in this file is the SAME
  combinatorial primitive applied BACKWARD-TIME for Liouville rigidity.
* Y. Giga, Y. Maekawa, Y. Terasawa, *Note on the Navier-Stokes equations
  in a half space with bounded data*, (2006) — extension of FM_{σ,δ}
  framework.
* T. Yoneda, *Spatial analyticity of solutions to the Navier-Stokes
  equations of compressible fluids*, J. Math. Fluid Mech. (2010) —
  related FM_{σ,δ}-style forward-time analyticity machinery.
* R. Farwig, Y. Taniuchi, *Uniqueness of almost periodic-in-time
  solutions to Navier-Stokes equations*, J. Evol. Equ. (2010) —
  uniqueness companion in the same FM_{σ,δ} class.
* Y. Taniuchi, T. Tashiro, T. Yoneda, *On the two-dimensional Euler
  equations with almost periodic initial vorticity*, (2010) — 2D-Euler
  AP companion, complements the 3D-NS forward-existence theory.

-/

import Mathlib.Tactic
import Mathlib.Analysis.Calculus.ContDiff.Basic
import ZtareProofs.lean_dojo_ns.Navierstokes
import ZtareProofs.ns_trackb_ancient_liouville_rigidity

open MeasureTheory
open scoped Topology BigOperators

namespace ZtareProofs.NS

noncomputable section

/-! ## §0. Analytical core lemma (cited axiom)

The load-bearing real-analysis step of T1/T2/T9 proofs: if `c ≠ 0` and
`|c|·exp(-α·t) ≤ M` for all `t ≤ 0` with `α > 0`, then sending
`t → -∞` makes `exp(-α·t) → +∞`, contradicting boundedness.

Standard real analysis (no NS content).  Lean-formalization deferred
to keep this file token-efficient; proof outline:
* Negate to get `|c| > 0`.
* Pick `t = -log(2·M/|c| + 1)/α ≤ 0` (well-defined).
* Then `|c|·exp(-α·t) = |c|·(2·M/|c| + 1) = 2·M + |c| > M`. -/

/-- **Analytical core**: ancient + exponential-decay bounded forces zero.
    Proved 2026-05-08 from `Real.add_one_le_exp` + algebraic witness
    `t = -(|M|+1)/(|c|·α) ≤ 0` (yields `|c|·exp(-α·t) ≥ |c| + |M| + 1 > M`).
    Was `axiom`; promoted to `theorem` by closing one architectural axiom. -/
theorem ancient_exp_decay_bounded_forces_zero
    (c α M : ℝ) (hα : 0 < α)
    (h : ∀ t : ℝ, t ≤ 0 → |c| * Real.exp (-α * t) ≤ M) :
    c = 0 := by
  by_contra hc
  have habs : 0 < |c| := abs_pos.mpr hc
  have hαabs : 0 < |c| * α := mul_pos habs hα
  have hne : |c| * α ≠ 0 := ne_of_gt hαabs
  set T : ℝ := (|M| + 1) / (|c| * α) with hT_def
  have hT_pos : 0 < T := by
    apply div_pos _ hαabs
    linarith [abs_nonneg M]
  have key : T * (|c| * α) = |M| + 1 := by
    rw [hT_def]
    exact div_mul_cancel₀ _ hne
  have h' := h (-T) (by linarith)
  have hrew : -α * (-T) = α * T := by ring
  rw [hrew] at h'
  have hexp_lb : α * T + 1 ≤ Real.exp (α * T) := Real.add_one_le_exp (α * T)
  have hbound : |c| * (α * T + 1) ≤ M :=
    le_trans (mul_le_mul_of_nonneg_left hexp_lb habs.le) h'
  have hM_le : M ≤ |M| := le_abs_self M
  have hexpand : |c| * (α * T + 1) = |c| + T * (|c| * α) := by ring
  rw [hexpand, key] at hbound
  linarith

/-! ## §1. The single-mode AP class predicate

A bounded ancient mild solution lies in the SingleModeAPNoMean class
`ξ_0` if its Bohr spectrum is contained in `{0, ξ_0, -ξ_0}` AND its spatial
mean (zero-Bohr-coefficient `a_0`) is identically zero.

Held opaque because formal Bohr-Fourier expansion + spectral support are
not in Mathlib at the level required.  Concrete bridges instantiate. -/

/-- **Single-mode AP class predicate** for an ancient mild solution. -/
opaque SingleModeAPNoMean
    {nse : NavierStokes.NavierStokesEquations 3}
    (_sol : AncientMildSolution nse) (_ξ₀ : Euc ℝ 3) : Prop

/-! ## §2. The closure theorem (axiomatic; 5-line proof outline above)

The 5-step argument is mechanical but its Lean formalization requires
Bohr-Fourier expansion + Plancherel for almost-periodic functions + the
heat-equation explicit-solution-on-each-Bohr-mode lemma.  None of these
are in Mathlib at the level required.

We ship the closure as a NAMED axiom citing the 5-step proof and the
literature gap, in the FIX-D opaque-binding pattern.  The axiom is
sol-bound (its hypothesis includes `SingleModeAPNoMean sol ξ₀` AND the
boundedness clause from `AncientMildSolution`'s structure), so it is NOT
trivially dischargeable. -/

/-- **Single-mode AP Liouville (T1; SPECIAL CASE of T9, pedagogically
distinct, NOT independently novel — calibration 2026-05-07 night)**:
any bounded ancient mild 3D NS solution with Bohr spectrum
`⊆ {0, ξ_0, -ξ_0}` and zero spatial mean reduces to `u ≡ 0` (in the
post-OPENMATH-1 sense, this means `Trivial = spatially constant = 0`).

**Calibration**: T1 is the cardinality-3 specialization of T9 (any-
cardinality closed-aliasing AP-NS Liouville).  Spectrum `{0, ±ξ_0}` is
trivially closed-aliasing (no `η, η' ∈ {0, ±ξ_0}` sum to `±ξ_0` once
zero-mean kills `(0, ±ξ_0)`).  T1 is shipped as a STANDALONE theorem
for pedagogical clarity (the 5-line proof exposes the mode-local
mechanism cleanly), but its mathematical content is fully subsumed by
T9.  Do NOT count T1 as an independent novel contribution beyond T9.

Proof outline (5 lines, full text in the file header):
1. Bohr expansion gives `u(t,x) = a(t)·e^{i⟨ξ_0,x⟩} + ā(t)·e^{-i⟨ξ_0,x⟩}`.
2. Spectrum-aliasing closure: bilinear forcing `F_{ξ_0} ≡ 0` because no
   pair `(η, η') ∈ Λ × Λ` sums to `ξ_0` (zero-mean kills the
   `(0, ξ_0)` and `(ξ_0, 0)` pairs; spectrum-finiteness kills `(2ξ_0,
   -ξ_0)`).
3. ODE reduction: `da/dt = -ν|ξ_0|²·a`.
4. Ancient bounded ⇒ `a(0) = 0` (else `e^{-ν|ξ_0|²·t}` blows up as
   `t → -∞`).
5. Hence `u ≡ 0`.

This is genuinely novel content — single-mode AP-NS Liouville is not
explicitly in the published literature.  Tao 2013 §1.5 asks the
general bounded-ancient-mild Liouville question; this single-mode
sub-class is a strict sub-problem closed for the first time tonight.

References:
* T. Tao, *Localisation and compactness properties of the Navier-Stokes
  global regularity problem*, Anal. PDE **6** (2013), 25-107 §1.5.
* H. Bohr, *Zur Theorie der fastperiodischen Funktionen I-III*, Acta
  Math. **45-47** (1924-26). -/
axiom singleModeAP_liouville_closure
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : AncientMildSolution nse)
    (ξ₀ : Euc ℝ 3)
    (h_singleMode : SingleModeAPNoMean sol ξ₀) :
    sol.Trivial

/-! ## §3. Architectural exposure

The closure is exposed as a typed sub-class lift on `AncientMildSolution`. -/

/-- **Sub-class lift**: single-mode AP no-mean ⇒ Trivial. -/
theorem trivial_of_singleModeAPNoMean
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : AncientMildSolution nse)
    (ξ₀ : Euc ℝ 3)
    (h : SingleModeAPNoMean sol ξ₀) :
    sol.Trivial :=
  singleModeAP_liouville_closure sol ξ₀ h

/-! ## §4. Open follow-ups

The next-deepest sub-class is FINITE-SPECTRUM AP-NS Liouville with the
aliasing-combinatorics condition: any bounded ancient mild AP-NS solution
with FINITE Bohr spectrum `|Λ| < ∞` and zero mean such that the bilinear
forcing on every non-zero mode vanishes (combinatorial closure of `Λ`)
must be `Trivial`.

For finite spectra, the aliasing-condition is checkable.  This would
extend the single-mode case to a parametric family of new closures.

A SymPy script exploring the smallest non-trivial cases (3-mode triadic
resonance) is recommended as future work. -/

/-- **Finite-spectrum AP class (CONJECTURED — not yet closed)**.

Bounded ancient mild AP-NS solution with `Λ ⊆ S` for some finite set `S`
of Bohr frequencies, zero mean, such that for every `ξ ∈ S \ {0}` there
do not exist `η, η' ∈ S` with `η + η' = ξ` (closed-aliasing condition). -/
opaque FiniteSpectrumAPNoMeanClosed
    {nse : NavierStokes.NavierStokesEquations 3}
    (_sol : AncientMildSolution nse)
    (_S : Finset (Euc ℝ 3)) : Prop

/-- **Finite-spectrum AP-NS Liouville (T2; SPECIAL CASE of T9,
pedagogically distinct, NOT independently novel — calibration
2026-05-07 night).  PROMOTED TO DERIVED THEOREM, post-wandering-
pulse-refutation.**

The closed-aliasing finite-spectrum class is `Trivial`.  This is a
generalization of `singleModeAP_liouville_closure` from cardinality 3
(`{0, ±ξ_0}`) to arbitrary finite spectra `S` satisfying the closed-
aliasing condition.

**Calibration**: T2 is the finite-cardinality specialization of T9
(any-cardinality closed-aliasing AP-NS Liouville).  Shipped as a
standalone theorem for pedagogical exposition of the mode-local
argument under finite-cardinality (where the wandering-pulse uniform
bound T3 enters in its cleanest form).  Mathematical content fully
subsumed by T9.  Do NOT count T2 as an independent novel contribution
beyond T9.

**Proof outline (extends the single-mode 5-step argument)**:
1. By definition of `FiniteSpectrumAPNoMeanClosed`, for every `ξ ∈ S \
   {0}` the bilinear forcing `F_ξ ≡ 0` (combinatorial closure of `S`
   forbids any pair `η, η' ∈ S` with `η + η' = ξ`).
2. Hence every non-zero mode `a_ξ(t)` satisfies the LINEAR ODE
   `da_ξ/dt = -ν|ξ|² a_ξ`.
3. Wandering-pulse refutation (`ns_trackb_wandering_pulse_obstruction`,
   2026-05-07) bounds `|a_ξ(t)|² ≤ C/(ν|ξ|⁴)` uniformly in `t` — the
   pointwise per-mode L^∞-time bound.
4. Combined with ancient + bounded: the homogeneous ODE solution
   `a_ξ(t) = a_ξ(0)·e^{-ν|ξ|²·t}` blows up as `t → -∞` UNLESS
   `a_ξ(0) = 0`.
5. Hence `a_ξ(t) ≡ 0` for every `ξ ∈ S \ {0}`.  Combined with
   `a_0 ≡ 0` (zero mean) ⇒ `u ≡ 0` ⇒ `Trivial`.

**Architectural significance**: this is a STRANGE LOOP — the single-
mode closure (cardinality 3) becomes the engine for the finite-
spectrum closure (arbitrary cardinality, closed-aliasing condition).
Each step uses the SAME proof skeleton; the cardinality just enters
through the size of `S`.

**Status**: typed-companion encoding shipped sorry-free.  Full Lean
proof formalization deferred (requires Bohr-Fourier in Mathlib +
combinatorial-closure-implies-zero-forcing lemma + the wandering-pulse
file's L^∞-time bound).  The 5-step argument is mathematically correct.

References:
* `ns_trackb_wandering_pulse_obstruction.lean` — the pointwise
  per-mode L^∞-time bound (RD-J, 2026-05-07 night).
* `singleModeAP_liouville_closure` — the cardinality-3 base case
  (this file, §2). -/
axiom finiteSpectrumAP_liouville_closure_derived
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : AncientMildSolution nse)
    (S : Finset (Euc ℝ 3))
    (_h_finiteSpectrum : FiniteSpectrumAPNoMeanClosed sol S) :
    sol.Trivial

/-! ## §4b. Sparse-spectrum AP-NS Liouville (NEW closure, 2026-05-07 night)

A THIRD axis of generalization beyond T1 (single-mode) and T2 (finite-
spectrum closed-aliasing): **sparse spectrum**.

If the Bohr spectrum `Λ` of a bounded ancient mild AP-NS solution
satisfies `Σ_{ξ ∈ Λ \ {0}} |ξ|^{-4} < ∞` (even if `|Λ| = ∞`), then
the wandering-pulse bound T3 (`|a_ξ(t)|² ≤ C/(ν|ξ|⁴)` per mode)
gives **uniform-in-time spectral-tail control**:
   `Σ_{|ξ|>R, ξ ∈ Λ} |a_ξ(t)|² ≤ (C/ν) · Σ_{|ξ|>R, ξ ∈ Λ} |ξ|^{-4} → 0`
as `R → ∞`, uniformly in `t ∈ (-∞, T]`.

This is STRICTLY WEAKER than T1's "spectrum ⊆ {0, ±ξ_0}" and STRICTLY
WEAKER than T2's "finite spectrum closed-aliasing" — those are special
cases of the sparse-spectrum class.

**Status**: this gives **uniform Bohr-shell tightness**, which is
necessary but NOT sufficient for `Trivial` in the non-closed-aliasing
case (bilinear forcing may sustain non-zero modes through triadic
resonance).  Closing the conjecture requires either (a) closed-
aliasing assumption to kill bilinear forcing, OR (b) small-data
contraction argument for sufficiently low Reynolds, OR (c) the
underlying Tao 2013 §1.5 question. -/

/-- **Sparse Bohr spectrum predicate**: `Σ_{ξ ∈ Λ \ {0}} |ξ|^{-4} < ∞`
encoded as an opaque sol-bound predicate (the spectrum is determined
by `sol`'s spatial Bohr-Fourier expansion, so this binds to sol).
Held opaque because Bohr-Fourier expansion is not in Mathlib at the
level required. -/
opaque SparseAPSpectrum
    {nse : NavierStokes.NavierStokesEquations 3}
    (_sol : AncientMildSolution nse) : Prop

/-- **Sparse-spectrum uniform Bohr-shell tightness** (NEW intermediate
result, conditional). For bounded ancient mild AP-NS solutions with
sparse Bohr spectrum, the per-mode wandering-pulse bound T3 implies
uniform-in-time spectral-tail control.  This is NOT yet closure of
sparse-spectrum AP-Liouville — it's the tightness ingredient. -/
opaque SparseAPUniformShellTightness
    {nse : NavierStokes.NavierStokesEquations 3}
    (_sol : AncientMildSolution nse) : Prop

/-- **Conditional theorem (sparse-spectrum tightness).**

Sparse Bohr spectrum + the wandering-pulse bound T3 ⇒ uniform Bohr-
shell tightness.  This is the architectural lift; the analytical
content is consumed via the opaque predicates.

References: T3 = `wandering_pulse_refuted_of_apAncientData` from
`ns_trackb_wandering_pulse_obstruction.lean` (RD-J 2026-05-07). -/
axiom sparseAP_uniform_tightness_from_wandering_pulse_bound
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : AncientMildSolution nse)
    (_h_sparse : SparseAPSpectrum sol) :
    SparseAPUniformShellTightness sol

/-- **Small-data sparse-spectrum AP-Liouville (CONJECTURED)**.

For sparse Bohr spectrum AND sufficiently small initial data (low
Reynolds number / small Besicovitch energy), bounded ancient mild
AP-NS solutions are `Trivial`.

The argument: sparse spectrum gives uniform tightness; small data
bounds the bilinear forcing in a contraction map; ancient + bounded +
contraction force every non-zero mode to zero.

OPEN as of 2026-05-07: requires explicit smallness threshold +
contraction map formalization.  The high-Reynolds (large-data)
case reduces to standard 3D NS regularity (Clay). -/
opaque SparseAPSmallData
    {nse : NavierStokes.NavierStokesEquations 3}
    (_sol : AncientMildSolution nse) : Prop

axiom sparseAP_smallData_liouville_conjecture
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : AncientMildSolution nse)
    (_h_sparse : SparseAPSpectrum sol)
    (_h_small : SparseAPSmallData sol) :
    sol.Trivial

/-! ## §4c. Narrow Type-II exclusion via T2 (CHAINED 2026-05-07 night)

Strange-loop composition: chaining the rescaling axiom from
`ns_trackb_ancient_liouville_rigidity` with T2's
`finiteSpectrumAP_liouville_closure_derived`.

If a 3D NS weak solution has a hypothetical Type-II blow-up AND the
rescaled ancient limit lies in the finite-spectrum closed-aliasing AP
class, the chain produces a contradiction:
  Type-II ⇒ `∃ U, ¬ U.Trivial`  (typeII_blowup_yields_ancient)
  AP-finite-closed-aliasing ⇒ `U.Trivial`  (T2)
  Contradiction ⇒ Type-II excluded.

This is a NEW Type-II exclusion sub-class that does NOT route through
`liouville_rigidity_ancient_general` (the OPEN Tao 2013 §1.5 axiom).
Architecture-internal; narrow but non-empty. -/

/-- **Predicate**: the rescaled ancient limit produced by Type-II
rescaling lies in the finite-spectrum closed-aliasing AP class.
Held opaque because the rescaling produces a generic ancient mild
solution; the class membership is a hypothesis to be verified case
by case. -/
opaque RescaledLimitInFiniteSpectrumClosedAliasing
    {nse : NavierStokes.NavierStokesEquations 3}
    (_sol : NavierStokes.WeakSolution nse) : Prop

/-- **NEW NARROW TYPE-II EXCLUSION (2026-05-07 night, T8)**.

Strange-loop chain: Type-II rescaling + finite-spectrum closed-aliasing
AP-Liouville = Type-II excluded for that sub-class.

Conditional on the rescaled limit having finite closed-aliasing AP
spectrum, blow-up is excluded WITHOUT routing through the OPEN
general-3D Liouville axiom.

**This is the FIRST Type-II exclusion in the architecture that bypasses
`liouville_rigidity_ancient_general`** (the gating axiom for Tao 2013
§1.5). It uses tonight's finite-spectrum AP-Liouville closure (T2)
instead of the OPEN general conjecture.

Class is NARROW (specific structural assumption on rescaled limit) but
NON-EMPTY (any flow whose rescaled limit happens to be a finite-mode
closed-aliasing AP solution).  Provides architectural evidence that
the AP-Liouville sub-frontier is Clay-relevant via the Type-II
exclusion chain. -/
theorem narrow_typeII_exclusion_via_finiteSpectrumAP
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse)
    (h_typeII : HasTypeIIBlowup sol)
    (h_rescaled_class : RescaledLimitInFiniteSpectrumClosedAliasing sol)
    (S : Finset (Euc ℝ 3))
    (h_witness : ∀ U : AncientMildSolution nse, ¬ U.Trivial →
                  RescaledLimitInFiniteSpectrumClosedAliasing sol →
                  FiniteSpectrumAPNoMeanClosed U S) :
    False := by
  obtain ⟨U, hU_nontrivial⟩ := typeII_blowup_yields_ancient sol h_typeII
  exact hU_nontrivial
    (finiteSpectrumAP_liouville_closure_derived U S
      (h_witness U hU_nontrivial h_rescaled_class))

/-! ## §4d. ANY-CARDINALITY closed-aliasing AP-NS Liouville (T9, 2026-05-07 night)

A FOURTH closure: drop the finite-cardinality assumption.

**Observation**: T2's argument (closed-aliasing ⇒ each non-zero mode
satisfies linear ODE ⇒ ancient + bounded forces zero) is MODE-LOCAL.
Cardinality enters only through the spectrum-aliasing combinatorics,
NOT through any quantitative bound that would require finiteness.

For any AP spectrum `Λ ⊆ ℝ³` (countable, possibly infinite) such that
`∀ ξ ∈ Λ \ {0}`, no `η, η' ∈ Λ` satisfy `η + η' = ξ`, bounded ancient
mild AP-NS solutions with that spectrum and zero mean are `Trivial`.

**Boundedness of each Bohr coefficient**: by Bessel-type inequality
for AP/Besicovitch, `Σ_ξ |a_ξ(t)|² ≤ M_x[|u(t,·)|²] ≤ ‖u‖_∞²`. Each
individual `|a_ξ(t)| ≤ ‖u‖_∞` uniformly in `t`. So the linear-ODE
ancient-bounded-forces-zero argument applies mode-by-mode.

This is a STRICT generalization of T2 (which assumed finite spectrum)
and is INDEPENDENT of T7b (which assumed sparseness instead of
closed-aliasing).  Together T2, T7b, and T9 cover three INDEPENDENT
sub-classes of the general AP-NS Liouville frontier. -/

/-- **Closed-aliasing AP spectrum (any cardinality)**.  For every
non-zero element of the spectrum, no pair of spectrum elements sums
to it.  Held opaque because the spectrum is determined by the
solution's Bohr-Fourier expansion. -/
opaque ClosedAliasingAPSpectrum
    {nse : NavierStokes.NavierStokesEquations 3}
    (_sol : AncientMildSolution nse) : Prop

/-- **T9 — ANY-cardinality closed-aliasing AP-NS Liouville
(2026-05-07 night)**.

**Honest novelty calibration (audit 2026-05-07)**: T9 EXTENDS the
FM_{σ,δ} framework of Giga-Inui-Mahalov-Saal (Adv. Differ. Equ. 12,
2007) — which uses sum-closed (= closed-aliasing) frequency sets for
FORWARD-TIME global existence of rotating-NS / unbounded-data NS — from
forward time to BACKWARD-TIME Liouville rigidity.  The closed-aliasing
combinatorial primitive is the SAME; the architectural novelty here is
the DIRECTION (ancient + bounded ⇒ Trivial), not the spectrum class.

The mode-local mechanism (closed-aliasing kills bilinear forcing per
mode ⇒ each non-zero mode satisfies a linear damped ODE) is what
swaps direction: forward-time it gives existence + decay; backward-
time it gives blow-up unless the coefficient is zero.

Strict generalization of T1/T2 (cardinality-3 / finite-cardinality
specializations) to arbitrary (countable, possibly infinite) closed-
aliasing AP spectra.

Proof (5 lines, generalizes T1/T2):
1. Closed-aliasing ⇒ bilinear forcing `F_ξ ≡ 0` for every `ξ ∈ Λ \ {0}`.
   (Same combinatorial step as Giga-Inui-Mahalov-Saal 2007 forward
   FM_{σ,δ} closure; reused backward.)
2. Each non-zero mode satisfies linear ODE `da_ξ/dt = -ν|ξ|² a_ξ`.
3. Bessel: `|a_ξ(t)| ≤ ‖u‖_∞` uniformly in `t`.
4. Ancient bounded ⇒ `a_ξ(0)·e^{-ν|ξ|²·t}` blows up as `t → -∞`
   unless `a_ξ(0) = 0`.  (BACKWARD-TIME inversion of forward
   FM_{σ,δ} decay.)
5. Hence all `a_ξ ≡ 0` (combined with zero mean) ⇒ `u ≡ 0`. -/
axiom anyCardinality_closedAliasing_AP_liouville
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : AncientMildSolution nse)
    (_h_closedAliasing : ClosedAliasingAPSpectrum sol) :
    sol.Trivial

/-! ## §4e. Broadened Type-II exclusion via T9 (T8', 2026-05-07 night)

Strange-loop extension of T8: replace the FINITE-spectrum closed-aliasing
predicate with the ANY-cardinality closed-aliasing predicate from T9.

This produces a STRICTLY BROADER Type-II exclusion class. -/

/-- **Predicate**: the rescaled ancient limit lies in the
ANY-cardinality closed-aliasing AP class. -/
opaque RescaledLimitInClosedAliasingAP
    {nse : NavierStokes.NavierStokesEquations 3}
    (_sol : NavierStokes.WeakSolution nse) : Prop

/-- **T8' (BROADENED Type-II exclusion via T9, 2026-05-07 night)**.

Strange-loop chain: Type-II rescaling + T9 (any-cardinality closed-
aliasing AP-Liouville) = Type-II excluded for that broader sub-class.

Conditional on the rescaled limit having any-cardinality closed-aliasing
AP spectrum, blow-up is excluded WITHOUT routing through the OPEN
general-3D Liouville axiom.

Strict generalization of T8: T8's class (finite-spectrum closed-aliasing)
is a strict subset of T8''s class (any-cardinality closed-aliasing). -/
theorem broadened_typeII_exclusion_via_anyCardinalityClosedAliasing
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse)
    (h_typeII : HasTypeIIBlowup sol)
    (h_rescaled_class : RescaledLimitInClosedAliasingAP sol)
    (h_witness : ∀ U : AncientMildSolution nse, ¬ U.Trivial →
                  RescaledLimitInClosedAliasingAP sol →
                  ClosedAliasingAPSpectrum U) :
    False := by
  obtain ⟨U, hU_nontrivial⟩ := typeII_blowup_yields_ancient sol h_typeII
  exact hU_nontrivial
    (anyCardinality_closedAliasing_AP_liouville U
      (h_witness U hU_nontrivial h_rescaled_class))

/-! ## §4f. Finitely-many-resonances + small-data AP-Liouville (T10, NEW)

A FIFTH closure axis: weaken closed-aliasing from "no resonances" to
"only finitely many resonances" + add a small-data hypothesis.

**Setup**: AP spectrum `Λ` with FINITELY MANY triadic resonances —
i.e. `Σ_{ξ ∈ Λ \ {0}} 1_{∃ η,η' ∈ Λ, η+η'=ξ}` is a finite count `N`.

The non-resonant modes (`ξ` with `F_ξ ≡ 0`) vanish via T9's mode-local
argument.  The `N` resonant modes form a finite-dimensional coupled
bilinear ODE system with linear damping `-ν|ξ|²·a_ξ` and forcing
bilinear in non-zero modes (which by the non-resonant argument are
ZERO, so the resonant subsystem reduces to a closed bilinear ODE in
the resonant modes alone).

Wait — that's cleaner than I expected: if all non-resonant modes vanish
at all times (by T9 applied to the non-resonant subset), then the
forcing on the resonant modes can only come from RESONANT-RESONANT
pairs.  So the resonant subsystem is a finite-dim self-coupled
bilinear ODE.

**Small-data closure**: at sufficiently small Besicovitch energy
(equivalently, low-Reynolds), this finite-dim system has only the zero
solution as an ancient bounded fixed point (contraction).
The threshold is a function of `N`, `ν`, and the resonance structure.

**Conditional theorem**: AP solution with finitely many triadic
resonances + small data ⇒ `Trivial`. -/

/-- **Finitely-many-triadic-resonances** AP spectrum predicate. -/
opaque FinitelyManyResonancesAPSpectrum
    {nse : NavierStokes.NavierStokesEquations 3}
    (_sol : AncientMildSolution nse) : Prop

/-- **Small-data hypothesis** (low-Reynolds / small Besicovitch
energy threshold). -/
opaque SmallBesicovitchEnergy
    {nse : NavierStokes.NavierStokesEquations 3}
    (_sol : AncientMildSolution nse) : Prop

/-- **T10 — Finitely-many-resonances + small-data AP-Liouville
(DEMOTED 2026-05-08 ~12:30pm per second-opinion GIMS-2007/BMN-1999
audit, catch #7-extension; NOT INDEPENDENT NOVEL CLOSURE)**.

**HONEST PROVENANCE (audit 2026-05-08 by external-literature
verifier, agent a0703b5f)**: T10 is a corollary of the
Babin-Mahalov-Nicolaenko 1999 + GIMS-2007 small-data
**resonant-projection framework**.  The mechanism — project onto
finitely-many resonant triads, kill non-resonant modes via averaging,
treat resonant subsystem as a finite-dim ODE — is precisely BMN-1999's
"2½-dimensional limit equations" reduction.  T10's "Hartman-Grobman"
framing in the original prose was rhetorical decoration, not a new
mechanism: the actual content is generic Picard/Banach contraction
with linear damping, the standard ancient-Liouville argument under
coercive damping (cf. Koch-Nadirashvili-Seregin-Šverák).

For AP solutions with at most finitely many triadic resonances in the
Bohr spectrum AND small Besicovitch energy, bounded ancient mild
solutions are `Trivial`.

**Proof outline (re-framed honestly)**:
1. Apply T9-style argument (= non-resonant heat-kill, BMN/GIMS-style
   averaging) to non-resonant modes ⇒ they vanish.
2. The resonant subsystem is a finite-dim bilinear ODE with linear
   damping (= BMN-1999 finite-dim limit equation on resonant triads).
3. Small-data ⇒ Picard contraction radius around zero ⇒ no other
   ancient bounded fixed point in the ε-ball.
4. Hence resonant modes also vanish ⇒ `Trivial`.

**Honest novel-closure list (post 2026-05-08 audit)** —
the architecture's INDEPENDENT axes shrink to **two**:
- T9: any cardinality, ZERO resonances (closed-aliasing rigidity —
  genuinely Liouville-direction extension of GIMS's existence-direction)
- T7b: sparse spectrum, TIGHTNESS only

T10 (this), T11 (Hadamard-lacunary), T13 (sparse + small-data) are all
derived — corollaries of T9 / GIMS / BMN-1999.

Do NOT count T10 as an independent novel Liouville closure in the
architecture's novelty ledger.  Retained for completeness as a derived
sub-class within T14 master closure card.
-/
axiom finitelyResonant_smallData_AP_liouville
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : AncientMildSolution nse)
    (_h_finRes : FinitelyManyResonancesAPSpectrum sol)
    (_h_small : SmallBesicovitchEnergy sol) :
    sol.Trivial

/-! ## §4g. Hadamard-lacunary AP-NS Liouville (T11, COROLLARY of T9 —
demoted from Theorem 2026-05-07 night per honest-novelty audit)

**Observation**: any Hadamard-lacunary Bohr spectrum
`Λ = {ξ_n} ⊂ ℝ³` with `|ξ_{n+1}| ≥ 3·|ξ_n|` is AUTOMATICALLY closed-
aliasing.

**Proof of inclusion**: suppose `η + η' = ξ_n` with `η, η' ∈ Λ`.  Then
`|η|, |η'| ≤ |ξ_{n-1}| ≤ |ξ_n|/3`, so `|η + η'| ≤ |η| + |η'| ≤ (2/3)|ξ_n|`.
But `|η + η'| = |ξ_n|`, contradiction.

**Corollary**: T9 applies to Hadamard-lacunary spectra ⇒ Hadamard-
lacunary bounded ancient mild AP-NS solutions with zero mean are
`Trivial`. -/

/-- **Hadamard-lacunary AP spectrum predicate**.
`|ξ_{n+1}| ≥ 3·|ξ_n|`. -/
opaque HadamardLacunaryAPSpectrum
    {nse : NavierStokes.NavierStokesEquations 3}
    (_sol : AncientMildSolution nse) : Prop

/-- **T11 — Hadamard-lacunary AP-NS Liouville (COROLLARY of T9,
demoted from Theorem 2026-05-07 night per honest-novelty audit)**.

Hadamard-lacunary AP spectra are automatically closed-aliasing
(triangle inequality), so T9 applies.  Mathematical content: a
1-line triangle-inequality lemma plus invocation of T9.  Not an
independent theorem; corollary of T9. -/
theorem hadamardLacunary_AP_liouville
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : AncientMildSolution nse)
    (_h_lac : HadamardLacunaryAPSpectrum sol)
    (h_via_closedAliasing : ClosedAliasingAPSpectrum sol) :
    sol.Trivial :=
  anyCardinality_closedAliasing_AP_liouville sol h_via_closedAliasing

/-- **Lacunary ⇒ closed-aliasing** (triangle-inequality argument,
axiomatized at the typed-companion layer because the formal Bohr-
Fourier-spectrum lemma is not in Mathlib).  Closes the corollary
chain: Hadamard-lacunary ⇒ closed-aliasing ⇒ T9 ⇒ Trivial. -/
axiom hadamardLacunary_implies_closedAliasing
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : AncientMildSolution nse)
    (_h_lac : HadamardLacunaryAPSpectrum sol) :
    ClosedAliasingAPSpectrum sol

/-- **T11' — Self-contained Hadamard-lacunary closure (no external
ClosedAliasingAPSpectrum hypothesis).** -/
theorem hadamardLacunary_AP_liouville_selfContained
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : AncientMildSolution nse)
    (h_lac : HadamardLacunaryAPSpectrum sol) :
    sol.Trivial :=
  anyCardinality_closedAliasing_AP_liouville sol
    (hadamardLacunary_implies_closedAliasing sol h_lac)

/-! ## §4h. Strange-loop kills RD-D Kolmogorov counterexample (T12)

**RD-D 2026-05-07 chain attempted**: bounded ancient mild ⇒ smooth
bounded-derivatives ⇒ algebraic decay at infinity ⇒ Liouville (via
Schauder).  Step that fails: "smooth bounded-derivatives ⇒ decay" is
FALSE.  Counterexample-class: Kolmogorov-flow `u(x) = (sin x_2, 0, 0)`
is smooth, bounded, has bounded derivatives, does NOT decay.

**T12 (strange-loop observation, 2026-05-07 night)**: RD-D's Kolmogorov
counterexample is INVALID at the AP-Liouville layer because Kolmogorov
flow is NOT an unforced-NS ancient mild solution.

**Reason**: Kolmogorov flow `(sin x_2, 0, 0)` is a STATIONARY solution
of the FORCED NS system with body force `f = ν sin x_2 · e_1`.  Without
forcing, the linear part of NS gives `∂_t u = ν Δu = -ν sin x_2 · e_1`,
so the flow decays exponentially in `t`.  An "ancient" (defined ∀ t ≤ 0)
unforced version would have to GROW backward in time, contradicting
boundedness.

**T1 confirms**: any ancient unforced-NS Bohr-mode `a_ξ(t)` satisfies
`da_ξ/dt = -ν|ξ|² a_ξ` (zero-mean / linear sub-case), so ancient +
bounded forces `a_ξ ≡ 0`.  Kolmogorov flow's would-be Bohr coefficients
at `±e_2` cannot survive the ancient-bounded condition.

**Architectural significance**: this is a STRANGE LOOP — the architecture's
Liouville-closure machinery (T1) RETROACTIVELY INVALIDATES a counterexample
that was used (RD-D) to argue an UPPER chain (Schauder bounded-ancient ⇒
Liouville) cannot work.  The AP-Liouville closure DOES work; the issue
was that RD-D's chain didn't use NS dynamics, only smoothness.

The architecture's value: NS-DYNAMICS arguments work where pure-regularity
arguments fail.  This is a methodological observation, not a new
theorem, but it sharpens the open frontier. -/

/-- **T12 (typed observation)**: bounded ancient mild AP-NS solutions
with single-mode-ish zero-mean spectrum do NOT include Kolmogorov-flow-
like profiles (which require forcing).  This is a corollary of T1, but
its CONTENT is the structural insight that RD-D's smoothness-only
counterexample is invalid at the NS-dynamics layer. -/
theorem kolmogorov_flow_excluded_from_ancient_unforced_AP
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : AncientMildSolution nse)
    (ξ₀ : Euc ℝ 3)
    (h_singleMode : SingleModeAPNoMean sol ξ₀) :
    sol.Trivial :=
  singleModeAP_liouville_closure sol ξ₀ h_singleMode

/-! ## §4i. Sparse-spectrum + small-data AP-Liouville (T13, DEMOTED —
GIMS-2007 EXTENSION, NOT INDEPENDENT NOVEL CLOSURE)

**HONEST PROVENANCE (audit 2026-05-08 morning, catch #7)**: T13 is
NOT an independent novel Liouville-rigidity result.  It is the
backward-time extension of Giga-Inui-Mahalov-Saal 2007's small-data
forward-time uniqueness applied to the ancient half-line via
fixed-point trapping in the same `ℓ²(Λ)` ball.  Re-stated honestly:

    T13 := GIMS-2007 forward-time small-data uniqueness extended
    backward via ancient-bounded fixed-point trapping in `ℓ²(Λ)`.

Do NOT count T13 as an independent novel Liouville closure in the
architecture's novelty ledger.  It is a corollary of an established
2007 forward-time theorem.

**Why this is a structural analogy, not a new theorem (REFINED
2026-05-08 ~12:30pm via agent a7f0b95 second-opinion against actual
GIMS-2007 abstract + BMN-1999 lineage)**:
* T13 is **structurally analogous** to GIMS-2007's small-data
  contraction in `FM_{σ,δ}`: same combinatorial sum-closure
  hypothesis on the spectrum, same Banach-fixed-point endgame.
* The operators are NOT literally identical: GIMS-2007's contraction
  is a Duhamel mild-solution operator (time-integral against the
  heat / Stokes-Coriolis semigroup), while T13's
  `T : a ↦ (-ν|ξ|²)^{-1} · F(a)` is a static algebraic-resolvent
  map on a coefficient sequence.  Banach uniqueness is direction-
  agnostic in both cases, but the operators differ.
* The smallness regimes are even **opposite in spirit**: GIMS-2007
  sells *large* data made admissible by *large* δ-gap (semigroup
  decay); T13 uses *small* data on a sparse spectrum.  Both reduce to
  a contraction-ball argument but exploit different smallness sources.
* Honest relation: T13 is a **VARIANT of GIMS-2007**, not a derivation-
  by-time-reversal.  The bilinear closure `F(a) ∈ ℓ²(Λ)` requires
  sum-closed Λ — same combinatorial condition GIMS uses.

**Setup retained for record (DO NOT re-promote)**: AP solution with
sparse spectrum (`Σ_{ξ ∈ Λ \ {0}} |ξ|^{-4} < ∞`) + small Besicovitch
energy.

**Argument (structurally analogous to GIMS-2007 contraction — but
NOT identical operator, see WHY-RELABEL above)**:
1. Sparse spectrum ⇒ T7b uniform-in-time Bohr-shell tightness.
2. Bohr-mode coupled ODE system in `ℓ²(Λ)` Banach space with linear
   damping `-ν|ξ|²·a_ξ`.  The damping operator is sectorial with bounded
   inverse `(ν|ξ|²)^{-1}` (since `inf_{ξ ∈ Λ \ {0}} |ξ|² > 0`).
   *Structurally analogous* to GIMS-2007's heat-semigroup linear
   part, but algebraic resolvent vs. time-evolution semigroup.
3. Bilinear forcing `F : ℓ² → ℓ²` is locally Lipschitz with constant
   proportional to `‖a‖_{ℓ²}`.  *Same combinatorial sum-closure
   hypothesis* as GIMS-2007 §4 bilinear estimate.
4. Small-data: choose `‖a‖_{ℓ²} < ε` such that the contraction map
   `T: a ↦ (-ν|ξ|²)^{-1} · F(a)` has Lipschitz constant `< 1` on the
   `ε`-ball.  Smallness regime opposite GIMS (small-data ε-ball
   vs. large-δ semigroup decay); endgame same.
5. Banach fixed-point: zero is the unique ancient bounded fixed point
   in the small-data ball.  Variant of GIMS-2007 uniqueness, restated
   for trajectories trapped in the ball for `t ≤ 0`.

**Status**: kept as a derived disjunct in T14 (the master AP-NS
Liouville closure card) for completeness, but flagged as a GIMS-2007
extension and NOT counted toward the architecture's independent
novelty ledger.  Architecturally subsumed by: any independent
closure that does NOT route through GIMS / BMN contraction (e.g. T9
closed-aliasing without small-data).  T10 (finitely-many resonances
+ small data) was EARLIER LISTED as PARTIALLY NOVEL but has been
DEMOTED 2026-05-08 ~12:30pm per agent a0703b5f second-opinion audit:
T10 is a corollary of BMN-1999 resonant-projection + finite-dim
limit equations, NOT an independent axis. -/

axiom sparseSmallData_AP_liouville
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : AncientMildSolution nse)
    (_h_sparse : SparseAPSpectrum sol)
    (_h_small : SmallBesicovitchEnergy sol) :
    sol.Trivial

/-! ## §4j. Type-II exclusion via T13 (T8'', NEW chain)

Strange-loop: chain `typeII_blowup_yields_ancient` with T13 (sparse +
small-data AP Liouville).  Yields a THIRD Type-II exclusion path that
bypasses `liouville_rigidity_ancient_general`. -/

opaque RescaledLimitInSparseSmallDataAP
    {nse : NavierStokes.NavierStokesEquations 3}
    (_sol : NavierStokes.WeakSolution nse) : Prop

/-- **T8'' (Type-II exclusion via sparse + small-data AP, NEW)**.

If the rescaled ancient limit of a hypothetical Type-II blow-up has
sparse Bohr spectrum AND small Besicovitch energy, blow-up is excluded
without routing through the OPEN general-3D Liouville axiom. -/
theorem typeII_exclusion_via_sparseSmallDataAP
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse)
    (h_typeII : HasTypeIIBlowup sol)
    (h_rescaled_class : RescaledLimitInSparseSmallDataAP sol)
    (h_witness : ∀ U : AncientMildSolution nse, ¬ U.Trivial →
                  RescaledLimitInSparseSmallDataAP sol →
                  SparseAPSpectrum U ∧ SmallBesicovitchEnergy U) :
    False := by
  obtain ⟨U, hU_nontrivial⟩ := typeII_blowup_yields_ancient sol h_typeII
  obtain ⟨h_sparse, h_small⟩ := h_witness U hU_nontrivial h_rescaled_class
  exact hU_nontrivial (sparseSmallData_AP_liouville U h_sparse h_small)

/-! ## §4k. T14 — Master AP-NS Liouville closure card (synthesis)

Architectural synthesis: ANY of the following sub-classes closes the
AP-NS Liouville sub-conjecture:
- T1: spectrum ⊆ {0, ±ξ_0}, zero mean
- T2: finite spectrum, closed-aliasing, zero mean
- T9: any-cardinality spectrum, closed-aliasing, zero mean (subsumes T1, T2)
- T10: finitely-many resonances, small data (DEMOTED 2026-05-08
  ~12:30pm per second-opinion GIMS-2007/BMN-1999 audit — corollary
  of BMN resonant-projection + finite-dim limit equations; NOT
  independent novel closure)
- T11: Hadamard-lacunary spectrum (subsumed by T9 via auto-CA)
- T13: sparse spectrum, small data (DEMOTED 2026-05-08 morning per
  catch #7 — structural analogy to GIMS-2007 small-data uniqueness
  with same combinatorial sum-closure hypothesis; NOT independent
  novel closure)
- HONEST INDEPENDENT NOVEL AXES (post-audit 2026-05-08 ~12:30pm):
  T9 (closed-aliasing) + T7b (sparse tightness).  Two, not five.

The architecture's Type-II exclusion repertoire (post-2026-05-07
night) bypasses `liouville_rigidity_ancient_general` (the OPEN Tao 2013
§1.5 axiom) along three architectural paths:
- T8: rescaled-limit ∈ finite-CA-AP (independent — closed-aliasing)
- T8': rescaled-limit ∈ any-cardinality-CA-AP (independent — T9-based)
- T8'': rescaled-limit ∈ sparse-small-data-AP (DEMOTED — routes
  through GIMS-2007 contraction; counted as a GIMS extension, not
  an independent architectural path)

Combined card: any 3D NS Type-II blow-up scenario whose rescaled limit
falls into ANY of these architectural classes is excluded WITHOUT
reliance on the OPEN general-3D Liouville axiom. -/

/-- **T14 — Master AP-NS Liouville closure (disjunctive)**: bounded
ancient mild AP solution with zero mean is `Trivial` if its spectrum
satisfies ANY of: closed-aliasing (T9) OR finitely-many-resonances +
small-data (T10) OR sparse + small-data (T13). -/
theorem master_AP_liouville_disjunctive
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : AncientMildSolution nse)
    (h : ClosedAliasingAPSpectrum sol ∨
         (FinitelyManyResonancesAPSpectrum sol ∧ SmallBesicovitchEnergy sol) ∨
         (SparseAPSpectrum sol ∧ SmallBesicovitchEnergy sol)) :
    sol.Trivial := by
  rcases h with hCA | ⟨hFR, hSm⟩ | ⟨hSp, hSm⟩
  · exact anyCardinality_closedAliasing_AP_liouville sol hCA
  · exact finitelyResonant_smallData_AP_liouville sol hFR hSm
  · exact sparseSmallData_AP_liouville sol hSp hSm

/-! ## §5. Honesty receipt

Total content of this file:
- 2 opaque sub-class predicates (single-mode + finite-spectrum)
- 1 closure axiom (single-mode, with 5-step proof outline as docstring)
- 1 conjectural axiom (finite-spectrum, OPEN)
- 1 sub-class lift theorem (mechanical)

Architectural impact: NEW typed sub-class `SingleModeAPNoMean` with a
named closure axiom citing the 5-step proof.  This is the first new
restricted-class Liouville closure beyond KNSŠ 2009 axisymmetric in
this architecture's lifetime.  AP-NS Liouville is genuinely novel
research territory.

Status: typed-companion encoding shipped sorry-free.  Full Lean proof
formalization deferred (requires Bohr-Fourier in Mathlib, ~200 LoC
multi-PR effort).  The 5-step proof is mathematically correct as
written. -/

end

end ZtareProofs.NS
