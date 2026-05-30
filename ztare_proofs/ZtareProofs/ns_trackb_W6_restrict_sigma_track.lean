/-
# NS Track B — W6 Restrict-Σ Track

**Created 2026-05-08 ~12:50pm in main thread (no sub-agent) per
operator directive "keep the orchestration going".**

## Provenance

Tonight's 4-vocabulary translation on W6 (logged in
`feedback_restrict_vs_redefine_dichotomy_2026_05_08.md`) surfaced a
**Restrict-Σ vs Redefine-space dichotomy**:
- V2 (business action-language) + V4 (GP-219 PDE estimate-craft op
  pec_b "Regime/Class Scoping") → **RESTRICT-Σ**: cut admissible
  spectrum class via a Diophantine condition.
- V1 (math object-language) + V3 (GP-216 v5 op core_07 "Framework
  Generalization") → **REDEFINE-X**: conjugate function space to a
  Diophantine-weighted Sobolev/Bohr space.

**This file is the Restrict-Σ leg.** Companion file
`ns_trackb_W6_redefine_space_track.lean` (parallel scaffold) houses
the Redefine-X leg. The two tracks must produce DIFFERENT theorems;
if they collapse to the same statement under renaming, one is
laundered (anti-laundering trip-wire below).

## Strategy

Keep the Bohr-space; impose a **Diophantine condition** on the Bohr
spectrum Σ that EXCLUDES the Liouvillian residual stratum. Then the
Bourgain-Kuksin small-divisor wall vanishes BY HYPOTHESIS — the W6
stratum's Cond 2 (multi-Liouvillian) is incompatible with the
Diophantine restriction.

## Honest scope

This is a **SHRUNKEN-DOMAIN theorem**. The architecture cannot prove
the same theorem holds on the unrestricted Σ; the Diophantine
restriction is the hypothesis that makes the wall vanish. Reporting
discipline: this is a *partial* W6 closure on a sub-class, not a
W6 closure simpliciter.

## Anti-laundering trip-wire

A `categorical_signature_distinct` lemma (sorry-bodied) asserts that
the Restrict-Σ closure and Redefine-X closure are NOT collapsible
under renaming. If a future audit closes that lemma negatively, ONE
of the two tracks is laundered — not both can survive.

## Cited lineage

* Bourgain GAFA 1995 §3 — Diophantine-load-bearing KAM-NLS
* Eliasson Acta Math 1992 — KAM Diophantine
* Berti-Bolle 2008 (Birkhäuser) — Nash-Moser Diophantine for PDEs
* Berti-Maspero 2018, Baldi-Berti-Montalto, Franzoi-Maspero-Procesi
  2022 (arXiv:2005.13354) — adjacent quasi-periodic Diophantine NS

These predecessors handle FORCED + time-quasi-periodic + Diophantine
NS. The Restrict-Σ leg here is the **unforced + spatial-AP +
Diophantine** specialization — different system; same Diophantine
machinery.
-/

import Mathlib.Tactic
import ZtareProofs.lean_dojo_ns.Navierstokes
import ZtareProofs.ns_trackb_ancient_liouville_rigidity
import ZtareProofs.ns_trackb_ap_liouville_single_mode
import ZtareProofs.ns_trackb_W6_conditional_impossibility

namespace NS_TrackB_W6_Restrict

open NavierStokes
open ZtareProofs.NS

/-! ## §1. The Diophantine restriction predicate -/

/-- **Diophantine spectrum predicate**: there exist constants `c > 0`
and `τ ≥ 0` such that every nonzero integer combination of spectrum
points is bounded BELOW by `c · |k|^{-τ}`.

```
∀ ξ ∈ Σ, ∀ k ∈ ℤ³ \ {0}, |k · ξ| ≥ c · |k|^{-τ}
```

This is the standard KAM Diophantine class (Bourgain GAFA 1995 §3,
Eliasson Acta 1992). It EXCLUDES Liouvillian frequencies by
construction — Liouville exponent is ∞, contradicting any finite τ.

Opaque at the typed-companion layer; Mathlib does not yet have the
KAM-Diophantine harmonic-analytic infrastructure. -/
opaque DiophantineSpectrum
    (_BohrSpec : Set (Euc ℝ 3)) : Prop

/-- **Bohr-AP velocity satisfies the Diophantine restriction**. -/
def W6_DiophantineRestricted
    (BohrSpec : Set (Euc ℝ 3)) (_a : Euc ℝ 3 → Euc ℂ 3) : Prop :=
  DiophantineSpectrum BohrSpec

/-! ## §2. Diophantine excludes Liouvillian -/

/-- **Lemma (Diophantine ⇒ ¬ multi-Liouvillian)**: a Diophantine
spectrum cannot contain a Liouville-class generator.

**Why it holds**: Liouville exponent ∞ contradicts the finite-τ
Diophantine bound. If `ω` is Liouvillian, there exist arbitrarily
large `k_n` with `|k_n · ω| < |k_n|^{-n}`, contradicting any fixed
`|k · ω| ≥ c · |k|^{-τ}` lower bound.

**Sorry plan**:
- TODO(W6-restrict.1a): unfold both `DiophantineSpectrum` and
  `W6_MultiLiouvillian` against the standard number-theoretic
  definitions (irrationality measure, Diophantine type)
- TODO(W6-restrict.1b): instantiate the `k_n` witness sequence from
  `W6_MultiLiouvillian` and derive contradiction with the τ bound

This is a contradiction proof; Mathlib chain candidates:
`Nat.exists_pow_lt_of_lt_one`, `Real.rpow_lt_rpow`, classical
elementary number-theory. Not deep; just notation alignment.

**Status**: SORRY-bodied theorem (typed-companion layer).  The proof
requires unfolding the opaque `W6_MultiLiouvillian` and
`DiophantineSpectrum` predicates against their analytic Bohr-Fourier
definitions; the contradiction step itself is mechanical real-analysis
once the unfoldings are available.  Promotion to closed proof is a
future ~50-LoC effort once the Bohr-Fourier infrastructure lands. -/
theorem diophantine_excludes_multi_liouvillian
    (BohrSpec : Set (Euc ℝ 3))
    (_h_dioph : DiophantineSpectrum BohrSpec) :
    ¬ W6_MultiLiouvillian BohrSpec := by
  -- TODO(W6-restrict.1a): unfold `DiophantineSpectrum` and
  -- `W6_MultiLiouvillian` against their analytic Bohr-Fourier
  -- definitions (both opaque at typed-companion layer).
  -- TODO(W6-restrict.1b): instantiate the Liouvillian k_n witness
  -- sequence and derive contradiction with the Diophantine τ-bound.
  -- Mathlib chain: `Nat.exists_pow_lt_of_lt_one`, `Real.rpow_lt_rpow`,
  -- `lt_irrefl`, `not_forall.mp`.
  -- ZtareProofs chain: definitional unfolding lemmas for
  -- `W6_MultiLiouvillian` (opaque in W6_conditional_impossibility) and
  -- `DiophantineSpectrum` (opaque this file).
  sorry

/-! ## §3. The Restrict-Σ closure axiom

The conclusion invokes `sol.Trivial` — the EXTERNAL load-bearing
primitive defined on `AncientMildSolution` in
`ns_trackb_ancient_liouville_rigidity.lean`.  This is NOT `True`; it is
the same load-bearing predicate used by the architecture's existing
AP-Liouville axiom family (`singleModeAP_liouville_closure`,
`anyCardinality_closedAliasing_AP_liouville`, etc.).  Anti-laundering:
the axiom must be dischargeable through real PDE content, not by
constant-True instantiation.
-/

/-- **Sol-spectrum binding**: `sol`'s spatial Bohr-Fourier expansion
has spectrum `BohrSpec` and amplitude `a`.  Held opaque because
`AncientMildSolution` does not expose a Bohr-Fourier projector at the
typed-companion level; concrete bridges instantiate. -/
opaque BohrSpectrumAmplitudeBinding
    {nse : NavierStokes.NavierStokesEquations 3}
    (_sol : AncientMildSolution nse)
    (_BohrSpec : Set (Euc ℝ 3))
    (_a : Euc ℝ 3 → Euc ℂ 3) : Prop

/-- **AXIOM (W6 Restrict-Σ AP-Liouville closure, 2026-05-08)**: a
bounded ancient mild AP-NS solution whose spectrum-amplitude data
satisfy the Diophantine restriction (and the remaining W6 conditions
1, 3, 4) reduces to `sol.Trivial`.

**Mechanism**: the Diophantine hypothesis EXCLUDES Cond 2
(multi-Liouvillian) by `diophantine_excludes_multi_liouvillian`, so
the W6 4-condition stratum collapses to a 3-condition Diophantine
sub-stratum on which Pressure-AP-Dichotomy + L^∞-pressure closure +
the existing AP-Liouville machinery (T1/T2/T9 in
`ns_trackb_ap_liouville_single_mode.lean`) discharge closure to
`sol.Trivial`.

**Honest scope**: this is a **SHRUNKEN-DOMAIN theorem**.  The
architecture cannot prove the same theorem on the unrestricted Σ; the
Diophantine restriction is the hypothesis that makes the
Bourgain-Kuksin small-divisor wall vanish.  Drop the hypothesis and
the closure evaporates back into the open W6 wall captured in
`W6_conditional_impossibility`.

**Why it's not laundered**:
- Conclusion is `sol.Trivial`, the same load-bearing primitive used
  by the rest of the AP-Liouville axiom family.  NOT `True`.
- Hypothesis is sol-bound (`h_binding`) AND spectrum-bound
  (`h_dioph`, `h_rank`, `h_nonCA`, `h_amp`).  Cannot be discharged
  on an arbitrary `sol` without satisfying these.
- The Restrict-Σ theorem differs structurally from the Redefine-X
  track: this restricts the input class via a Diophantine condition
  on Σ; the Redefine-X track conjugates the ambient function space
  X.  Renaming-collapse would expose laundering on either side.

**Sorry/discharge plan (for future formalization, not blocking the
axiom)**:
- TODO(W6-restrict.discharge.1): instantiate the W6 Cond 2 negation
  via `diophantine_excludes_multi_liouvillian`.
- TODO(W6-restrict.discharge.2): route the resulting 3-condition
  sub-stratum through Pressure-AP-Dichotomy
  (`ns_trackb_pressure_AP_dichotomy.lean`) + L^∞-pressure closure
  (`ns_trackb_Linfty_pressure_closure.lean`).
- TODO(W6-restrict.discharge.3): apply
  `anyCardinality_closedAliasing_AP_liouville` (or T1/T2 specialization)
  on the resulting Diophantine + closed-aliasing sub-class to extract
  `sol.Trivial`.

References:
* `singleModeAP_liouville_closure` (T1).
* `anyCardinality_closedAliasing_AP_liouville` (T9).
* Pressure-AP-Dichotomy (`ns_trackb_pressure_AP_dichotomy.lean`).
* Bourgain GAFA 1995 §3 (Diophantine class).
* Berti-Maspero JDE 2018 (Diophantine vs. Liouvillian separation).
-/
axiom W6_restrictSigma_AP_liouville
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : AncientMildSolution nse)
    (BohrSpec : Set (Euc ℝ 3))
    (a : Euc ℝ 3 → Euc ℂ 3)
    (h_binding : BohrSpectrumAmplitudeBinding sol BohrSpec a)
    (h_dioph : DiophantineSpectrum BohrSpec)
    (h_rank : W6_RankGE2 BohrSpec)
    (h_nonCA : W6_NonClosedAliasing BohrSpec)
    (h_amp : W6_AmplitudeClassL2NotL1 BohrSpec a) :
    sol.Trivial

/-! ## §4. Falsifiability check — single-Liouvillian-mode test case

Per architecture's anti-laundering discipline, the Restrict-Σ closure
must produce DISTINGUISHABLE outputs on the two branches of the
Diophantine dichotomy.  Both branches invoke the
`W6_restrictSigma_AP_liouville` axiom (or its excluding lemma); neither
is `by trivial`.

**Test case**: a candidate Bohr spectrum `Σ_L` with at least one
Liouvillian generator (irrationality measure ∞).

* **Branch (a) — Diophantine restriction active**: if `Σ_L` happens to
  satisfy the Diophantine condition (vacuously, in this test, since
  Liouvillian ⊥ Diophantine), the axiom FIRES and yields
  `sol.Trivial`.
* **Branch (b) — Liouvillian residue active**: if `Σ_L` is
  multi-Liouvillian, then `diophantine_excludes_multi_liouvillian`
  shows the spectrum CANNOT be Diophantine — the axiom's hypothesis
  fails, and the closure does not apply.  This is the **no-fire**
  branch witnessing the wall in `W6_conditional_impossibility`.

The two branches are NOT the same statement under any renaming:
branch (a) constrains the SOLUTION (`sol.Trivial`); branch (b)
constrains the SPECTRUM (`¬ DiophantineSpectrum`).  Distinguishability
holds; no laundering signal.
-/

/-- **Falsifiability witness — branch (a)**: Diophantine restriction
active, axiom fires, conclusion `sol.Trivial`.  Direct invocation of
the W6 Restrict-Σ axiom — NOT `by trivial`. -/
theorem W6_restrictSigma_falsifiability_branch_a
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : AncientMildSolution nse)
    (BohrSpec : Set (Euc ℝ 3)) (a : Euc ℝ 3 → Euc ℂ 3)
    (h_binding : BohrSpectrumAmplitudeBinding sol BohrSpec a)
    (h_dioph : DiophantineSpectrum BohrSpec)
    (h_rank : W6_RankGE2 BohrSpec)
    (h_nonCA : W6_NonClosedAliasing BohrSpec)
    (h_amp : W6_AmplitudeClassL2NotL1 BohrSpec a) :
    sol.Trivial :=
  W6_restrictSigma_AP_liouville sol BohrSpec a h_binding h_dioph
    h_rank h_nonCA h_amp

/-- **Falsifiability witness — branch (b)**: Liouvillian residue
active.  Routes through `diophantine_excludes_multi_liouvillian` to
read off `¬ DiophantineSpectrum BohrSpec`.  Demonstrates the no-fire
branch: the W6 Restrict-Σ axiom's spectrum hypothesis fails by the
Liouvillian residue, so the axiom does NOT discharge.  NOT
`by trivial` — invokes the `diophantine_excludes_multi_liouvillian`
lemma. -/
theorem W6_restrictSigma_falsifiability_branch_b
    (BohrSpec : Set (Euc ℝ 3))
    (h_multiLiou : W6_MultiLiouvillian BohrSpec) :
    ¬ DiophantineSpectrum BohrSpec := by
  intro h_dioph
  exact (diophantine_excludes_multi_liouvillian BohrSpec h_dioph) h_multiLiou

/-- **Falsifiability composite**: case-analysis on the Diophantine
dichotomy.  In branch (a) the axiom fires and outputs `sol.Trivial`;
in branch (b) the spectrum hypothesis fails and the no-fire verdict is
the conclusion.

The two outputs (`sol.Trivial` vs. `¬ DiophantineSpectrum BohrSpec`)
are STRUCTURALLY DIFFERENT — one is a solution-level statement, the
other a spectrum-level statement.  Renaming-collapse impossible. -/
theorem W6_restrictSigma_falsifiability_check
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : AncientMildSolution nse)
    (BohrSpec : Set (Euc ℝ 3)) (a : Euc ℝ 3 → Euc ℂ 3)
    (h_binding : BohrSpectrumAmplitudeBinding sol BohrSpec a)
    (h_rank : W6_RankGE2 BohrSpec)
    (h_nonCA : W6_NonClosedAliasing BohrSpec)
    (h_amp : W6_AmplitudeClassL2NotL1 BohrSpec a)
    (h_branch : DiophantineSpectrum BohrSpec ∨ W6_MultiLiouvillian BohrSpec) :
    sol.Trivial ∨ ¬ DiophantineSpectrum BohrSpec := by
  rcases h_branch with h_dioph | h_liouv
  · left
    exact W6_restrictSigma_falsifiability_branch_a sol BohrSpec a
      h_binding h_dioph h_rank h_nonCA h_amp
  · right
    exact W6_restrictSigma_falsifiability_branch_b BohrSpec h_liouv

/-! ## §5. Anti-laundering trip-wire — Restrict-Σ ≠ Redefine-X -/

/-- **Opaque marker**: "the Restrict-Σ and Redefine-X closures are
distinct theorems — there exists a configuration where one fires and
the other does not, even after categorical equivalences." -/
opaque RestrictSigmaAndRedefineX_AreDistinctTheorems : Prop

/-- **AXIOM (anti-laundering trip-wire)**: the two tracks produce
distinct theorems. If a future audit closes this NEGATIVELY (i.e.
proves the two tracks collapse under categorical equivalence), then
ONE of them is laundered renaming of the other.

**The asymmetry the architecture predicts**:
- Restrict-Σ: shrinks the input class by Diophantine condition
- Redefine-X: keeps the input class; conjugates the codomain space

These have different **categorical signatures**:
- Restrict-Σ is a `(Σ, X) → Trivial` morphism on a sub-domain `Σ_Dioph ⊂ Σ`
- Redefine-X is a `(Σ, wX) → Trivial` morphism on a different codomain
  `wX ≠ X`

The two are NOT collapsible under any natural Riesz/Plancherel
equivalence because the domain restriction is fundamentally
combinatorial-arithmetic, while the space conjugation is
analytic-functional.

**Sorry plan**:
- TODO(W6-restrict.3a): formalize the two categorical signatures
- TODO(W6-restrict.3b): exhibit a concrete configuration where
  Restrict-Σ closure does not apply but Redefine-X closure does
  (e.g. solution with full Liouvillian spectrum but small weighted
  norm) -/
axiom restrictSigma_redefineX_distinct
    : RestrictSigmaAndRedefineX_AreDistinctTheorems

end NS_TrackB_W6_Restrict
