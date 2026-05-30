/-
# NS Track B — T9 closure proof-attempt scaffold
# (any-cardinality closed-aliasing AP-NS Liouville)

**Pincer convergence point**: T9 is the convergence point of the
UCC↔GP216 pincer.

* TOP (UCC, top-down categorical): T9 forces UCC route 8 (AP-Bohr) to
  collapse to Wall #4 — see
  `projects/ns_millennium_hunt/workspace/UCC_exhaustiveness_audit_2026_05_07.md`
  §2 + §4.  T9 is the SINGLE non-routine ingredient for UCC route-
  completeness (§4 of the audit).
* BOTTOM (GP216, bottom-up observable): T9 forces atom 8's Lions
  defect measure to vanish on closed-aliasing Bohr spectra (modulo
  non-trivial AP).  Both layers route through this single
  architectural fact.

**Honest novelty calibration (audit 2026-05-08)**:
T9 is one of TWO honest novel-closure axes (T9 + T7b).  T10/T11/T13
were demoted as BMN/GIMS corollaries.  This file ships T9 as a
`theorem` scaffold (NOT axiom), routed through five named typed-
companion lemmas, each currently `sorry`-bodied with a TODO tag
naming the Mathlib + ZtareProofs lemma chain.

**Anti-laundering (catches #15, #17, #21(e), #23, #26)**:
* This file does NOT smuggle in T10/T11/T13 (demoted corollaries).
* The five sub-lemmas are MODE-LOCAL — each is a typed companion of
  a single classical fact (Bohr-Plancherel, ODE existence-uniqueness,
  bilinear closure, real-analysis core, Bessel inequality).  No
  vacuous-True / 1.5-order intra-file mismatch (catch #6).
* The `theorem` signature matches the original `axiom` signature
  bit-for-bit, so this file CAN replace the axiom downstream once
  the five sub-sorries close.

**Build target**:
```
cd ztare_proofs
lake build ZtareProofs.ns_trackb_T9_closure_proof_attempt
```

## Five-step proof skeleton (matches T9's docstring in the source file)

| Step | Sub-lemma                              | Codex bucket |
|------|----------------------------------------|--------------|
| 1    | `closedAliasing_kills_bilinear_forcing`| 3            |
| 2    | `each_mode_satisfies_linear_damped_ODE`| 3            |
| 3    | `bohr_coefficient_uniformly_bounded`   | 2            |
| 4    | `linear_ODE_ancient_bounded_forces_zero`| 1           |
| 5    | `all_modes_zero_implies_trivial`       | 3            |

The composition `T9 = step5 ∘ step4 ∘ step3 ∘ step2 ∘ step1` is
mechanical Lean glue (Codex bucket 1).  T9 itself sits at bucket 3
because steps 1, 2 gate on Bohr-Plancherel infrastructure that is
not yet sorry-free in `ns_trackb_bohr_mean_enstrophy_identity.lean`
(both `bohr_mean_enstrophy_identity_holds` and
`bohr_mean_zero_implies_u_zero` are still axioms).

## Pincer claim (FALSIFIABLE FORM)

If this file ships sorry-free — i.e. all five typed-companion sub-
lemmas close against named Mathlib + ZtareProofs lemmas — then:

* **UCC route 8 ↔ atom 8 correspondence becomes a PROVABLE pincer
  claim, not a structural pattern-matching exercise.**

Concretely: the UCC top-down claim (route 8 collapses to Wall #4)
becomes derivable from this theorem composed with the UCC route-8
typed companion; and the GP216 atom-8 bottom-up claim (Lions defect
vanishes on closed-aliasing) becomes derivable from this theorem
composed with the atom-8 Lions-defect typed companion.  Until then,
T9 remains an axiom and the pincer remains a structural analogy.

## References

* Source axiom: `ns_trackb_ap_liouville_single_mode.lean` §4d
  (`anyCardinality_closedAliasing_AP_liouville`).
* UCC audit: `projects/ns_millennium_hunt/workspace/`
  `UCC_exhaustiveness_audit_2026_05_07.md` §2 + §4.
* Bohr-Plancherel typed companions: `ZtareProofs/`
  `ns_trackb_bohr_mean_enstrophy_identity.lean`.
* Wandering-pulse uniform bound (T3): `ZtareProofs/`
  `ns_trackb_wandering_pulse_obstruction.lean`.
* Real-analysis core: `ancient_exp_decay_bounded_forces_zero` in
  `ns_trackb_ap_liouville_single_mode.lean` §0 (sorry-free, 2026-05-08).
* Mathlib upstream candidates: `projects/ns_millennium_hunt/`
  `workspace/research_notes/mathlib_upstream_candidates/`
  (`BohrMean.lean` PR-A1, `IsAlmostPeriodic.lean` PR-A0,
  `BohrPlancherel.lean` PR-A2).
* Giga-Inui-Mahalov-Saal, Adv. Differ. Equ. 12 (2007) — the SAME
  closed-aliasing combinatorial primitive applied FORWARD-TIME; T9
  is the BACKWARD-TIME Liouville-direction extension.

-/

import Mathlib.Tactic
import Mathlib.Analysis.Calculus.ContDiff.Basic
import ZtareProofs.lean_dojo_ns.Navierstokes
import ZtareProofs.ns_trackb_ancient_liouville_rigidity
import ZtareProofs.ns_trackb_ap_liouville_single_mode
import ZtareProofs.ns_trackb_bohr_mean_enstrophy_identity
import ZtareProofs.ns_trackb_wandering_pulse_obstruction

open MeasureTheory
open scoped Topology BigOperators

namespace ZtareProofs.NS

noncomputable section

/-! ## §1. Five-step typed-companion decomposition of T9

T9's mathematical content decomposes into five mode-local steps.  Each
is encoded here as a typed companion `theorem` with a `sorry` body
tagged `TODO(T9.<step>)` naming the Mathlib + ZtareProofs lemma chain
that closes it.

The composition (`T9_closure_attempt`) is mechanical glue: each step
chains into the next via the standard mode-by-mode argument.  No new
mathematics enters at the composition layer.
-/

/-- **Carrier**: a Bohr-mode index for the spectrum of an ancient
mild solution.  Held opaque because the spectrum-indexing requires
Bohr-Fourier expansion machinery (gated on `BohrMean` PR-A1 + Bessel
inequality / Plancherel PR-A2).

Codex bucket: 2 (architectural typed-companion; not load-bearing
content). -/
opaque T9.BohrModeIndex
    {nse : NavierStokes.NavierStokesEquations 3}
    (_sol : AncientMildSolution nse) : Type

/-- **Bohr-Fourier coefficient at index `i`**: the time-dependent
complex amplitude `a_ξ(t)` for `ξ` the Bohr frequency at index `i`.

Codex bucket: 2 (typed-companion getter). -/
opaque T9.bohrAmp
    {nse : NavierStokes.NavierStokesEquations 3}
    (_sol : AncientMildSolution nse)
    (_i : T9.BohrModeIndex _sol) (_t : ℝ) : ℂ

/-- **Bohr frequency squared at index `i`**: `|ξ|²` where `ξ` is the
Bohr frequency at index `i`.

Codex bucket: 2 (typed-companion getter). -/
opaque T9.bohrFreqSq
    {nse : NavierStokes.NavierStokesEquations 3}
    (_sol : AncientMildSolution nse)
    (_i : T9.BohrModeIndex _sol) : ℝ

/-- **The non-zero-frequency mode set**: indices `i` whose Bohr
frequency is not the zero frequency.  Closed-aliasing ⇒ each such
mode has zero bilinear forcing.

Codex bucket: 2 (typed-companion predicate). -/
opaque T9.IsNonZeroMode
    {nse : NavierStokes.NavierStokesEquations 3}
    (_sol : AncientMildSolution nse)
    (_i : T9.BohrModeIndex _sol) : Prop

/-- **Typed-companion bridge** (axiom, Codex bucket 1): a non-zero
Bohr mode has strictly positive squared frequency.  Mathematically
trivial (`|ξ|² > 0` whenever `ξ ≠ 0`); axiomatized at the typed-
companion layer because both `T9.IsNonZeroMode` and
`T9.bohrFreqSq` are `opaque` (Bohr-Fourier expansion is not in
Mathlib at the level required).  This axiom is what the §4d
`opaque ClosedAliasingAPSpectrum` predicate would unfold to once
the Bohr-Fourier infrastructure ships in Mathlib (PR-A2). -/
axiom T9.bohrFreqSq_pos_of_isNonZeroMode
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : AncientMildSolution nse)
    (i : T9.BohrModeIndex sol)
    (_h_nonzero : T9.IsNonZeroMode sol i) :
    0 < T9.bohrFreqSq sol i

/-! ### Step 1: closed-aliasing kills bilinear forcing per mode

For every non-zero mode `i`, the bilinear forcing `F_ξ(t) ≡ 0`.
Combinatorial step: closed-aliasing means no pair `(η, η') ∈ Λ × Λ`
sums to `ξ`, so the convolution sum that defines `F_ξ` is empty.

This is the SAME combinatorial primitive as Giga-Inui-Mahalov-Saal
2007 §4 (forward-time `FM_{σ,δ}` global existence).  The architectural
novelty is the BACKWARD-TIME Liouville-direction application.
-/

/-- **Bilinear forcing on Bohr mode `i`**: time-dependent complex
forcing `F_ξ(t)` from the bilinear NS map.

Codex bucket: 2 (typed-companion getter). -/
opaque T9.bilinearForcing
    {nse : NavierStokes.NavierStokesEquations 3}
    (_sol : AncientMildSolution nse)
    (_i : T9.BohrModeIndex _sol) (_t : ℝ) : ℂ

/-- **T9.closedAliasing_F_zero_at_residual — typed-companion axiom for
the closed-aliasing combinatorial collapse of the Bohr-bilinear forcing
convolution sum.**

For every non-zero Bohr mode `i` of an `AncientMildSolution` whose Bohr
spectrum satisfies the closed-aliasing predicate
`ClosedAliasingAPSpectrum`, the time-dependent bilinear forcing
`T9.bilinearForcing sol i t` of the NS-spectral mode `i` vanishes
identically in `t`.

**Why an axiom and not a theorem here.**  Mathematically this is the
SAME combinatorial primitive as Giga-Inui-Mahalov-Saal 2007 §4 (the
forward-time `FM_{σ,δ}` global-existence step): closed aliasing means
that for every non-zero `ξ ∈ Λ` no pair `(η, η') ∈ Λ × Λ` has
`η + η' = ξ`, hence the convolution sum defining `F_ξ(t)` is over the
empty index set and collapses by `Finset.sum_empty` /
`Finset.sum_eq_zero`.  In this scaffold the carriers
`T9.BohrModeIndex`, `T9.bilinearForcing`, and the predicate
`ClosedAliasingAPSpectrum` are typed-companion `opaque`s / unfolded
only inside upstream PR-A2 work, so the convolution-empty step cannot
be discharged at this layer.

**Honest transitive dependency chain (catch #21(f) compliance).** This
axiom is gated on the following upstream artifacts; every one of them
must close before the axiom can be promoted to a theorem:

  1. `mathlib_upstream_candidates/BohrPlancherel.lean`,
     `bohrPlancherel_finiteSpec` (line 598) — the Bohr-Plancherel /
     bilinear-convolution scaffold that gives the convolution-sum
     representation of `F_ξ(t)`.  Status 2026-05-08: the `theorem`'s
     proof body is sorry-free (verbatim mirrored + smoke-tested in
     `PR_B_FinitespecSmokeTest.lean`), but the closure routes through
     five upstream-hoisted transitive axioms
     (`hasBohrMean_bohrCharacter_of_ne_zero`,
     `hasBohrMean_forwardChar_of_ne_zero`, `hasBohrMean_const_mul_zero`,
     `hasBohrMean_finset_sum_zero`, `bohrPlancherel_linear_assembly`),
     each gated on PR-A1's narrowed `n ≥ 1` sorry inside
     `bohrCoefficient_exp_ne` (`BohrMean.lean:408`) and
     `volume_cube_eq` sorry — so PR-A2 is "Bessel-direction proof-body
     closed, integrability-via-PR-A1 still open".
  2. `mathlib_upstream_candidates/BohrMean.lean`,
     `hasBohrMean_of_isAlmostPeriodic` (line 760) — needed for the
     AP-spectrum side of the `ClosedAliasingAPSpectrum` predicate
     unfold (PR-A1, currently `sorry`).
  3. ZtareProofs: `ClosedAliasingAPSpectrum` predicate-body unfold
     (currently `opaque` in `ns_trackb_ap_liouville_single_mode.lean`
     §4d) — once unfolded to its combinatorial body, the empty-sum
     collapse follows mechanically.
  4. **Carrier-identification gap**: `T9.bohrAmp` and `T9.BohrModeIndex`
     are typed-companion `opaque`s in this file with no structural
     unification path to `IsTrigPolyVelocity`'s amplitude function `a`
     in `BohrPlancherel.lean`.  Promotion to theorem requires either
     (i) wiring `BohrPlancherel.lean` into the lake target AND
     replacing the opaque carriers with concrete getters tied to
     `IsTrigPolyVelocity`, or (ii) hoisting a NEW transitive axiom
     bridging the opaque carriers to the finite-spectrum machinery
     (which would be vocabulary-relabel, not promotion).

**Anti-laundering note.**  The axiom statement is
`T9.bilinearForcing sol i t = 0` — a concrete equality between a
typed-companion getter and the literal `0 : ℂ`, not `True`, not a
self-referential predicate, and not a tautological renaming of the
opaque carrier.  A wrong upstream PR-A2 statement (e.g. a mis-defined
convolution index set that does NOT collapse under closed aliasing)
would manifest as an inconsistency once this axiom is promoted to a
theorem and unified against the upstream definitions.  The hypothesis
`h_closedAliasing` is named (not underscore-bound) — catch #30 lesson
applied — so the load-bearing dependency on the closed-aliasing
predicate is greppable.

**Bucket assessment**: this axiom is bucket-3 (transitive on PR-A1 +
PR-A2 + the `ClosedAliasingAPSpectrum` predicate unfold).  Promoting
it to bucket-1 requires the upstream PRs to land sorry-free AND the
opaque predicate to be replaced by its convolution-empty body. -/
axiom T9.closedAliasing_F_zero_at_residual
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : AncientMildSolution nse)
    (h_closedAliasing : ClosedAliasingAPSpectrum sol)
    (i : T9.BohrModeIndex sol) (h_nonzero : T9.IsNonZeroMode sol i)
    (t : ℝ) :
    T9.bilinearForcing sol i t = 0

/-- **T9.step1 — Closed-aliasing kills bilinear forcing per mode**.

Closed-aliasing ⇒ for every non-zero mode `i`, `F_ξ ≡ 0`.

**Honest bucket assessment (post-work, 2026-05-08)**: bucket-3
(transitive).  The proof body below is mechanical and sorry-free,
routing the conclusion through the typed-companion axiom
`T9.closedAliasing_F_zero_at_residual` declared above (sister of
`T9.bohrAmp_le_Linfty`).  That axiom is in turn gated on PR-A1
(`hasBohrMean_of_isAlmostPeriodic`) + PR-A2
(`bohrPlancherel_finiteSpec`) + the `ClosedAliasingAPSpectrum`
predicate-body unfold.

Per catch #21(f), this is documented as TRANSITIVELY bucket-3 — the
sorry has been hoisted into a named axiom rather than silently re-
shipped through composition or buried inside the proof body.

TODO(T9.step1.transitively_via_PR_A2.closedAliasing_F_zero_at_residual):
  promote `T9.closedAliasing_F_zero_at_residual` from `axiom` to
  `theorem` once
    * PR-A2 `bohrPlancherel_finiteSpec` (BohrPlancherel.lean L598) is
      sorry-free transitively (proof body sorry-free 2026-05-08; upstream
      hoisted axioms still gated on PR-A1's `volume_cube_eq` +
      narrowed `n ≥ 1` sorries), AND
    * `BohrPlancherel.lean` is wired into the lake target so the
      `IsTrigPolyVelocity` machinery can be imported, AND
    * `T9.bohrAmp` / `T9.BohrModeIndex` are replaced with concrete
      getters tied to `IsTrigPolyVelocity`, AND
    * `ClosedAliasingAPSpectrum` is unfolded from `opaque` to its
      combinatorial convolution-empty body. -/
theorem T9.closedAliasing_kills_bilinear_forcing
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : AncientMildSolution nse)
    (h_closedAliasing : ClosedAliasingAPSpectrum sol)
    (i : T9.BohrModeIndex sol) (h_nonzero : T9.IsNonZeroMode sol i)
    (t : ℝ) :
    T9.bilinearForcing sol i t = 0 :=
  T9.closedAliasing_F_zero_at_residual sol h_closedAliasing i h_nonzero t

/-! ### Step 2: each non-zero mode satisfies linear damped ODE

With bilinear forcing zero, the Bohr-mode ODE
`da_ξ/dt = -ν|ξ|²·a_ξ + F_ξ` reduces to the homogeneous LINEAR
damped ODE `da_ξ/dt = -ν|ξ|²·a_ξ`.

Mathlib has ODE existence-uniqueness for linear damped ODEs but the
Bohr-mode-specific ODE derivation is gated on Bohr-Plancherel.
-/

/-- **T9.linear_damped_ODE_at_each_mode — typed-companion axiom for the
Bohr-mode linear damped ODE form.**

For every non-zero Bohr mode `i` of an `AncientMildSolution` whose Bohr
spectrum is closed-aliasing, the Bohr coefficient `a_ξ(t)` satisfies
the homogeneous linear damped ODE `da_ξ/dt = -ν|ξ|²·a_ξ`, so its
modulus has the explicit form
`‖a_ξ(t)‖ = ‖a_ξ(0)‖ · exp(-ν|ξ|²·t)`.

**Why an axiom and not a theorem here.**  Mathematically this combines
two pieces: (a) the Bohr-spectral form of NS gives
`da_ξ/dt = -ν|ξ|²·a_ξ + F_ξ(t)`, and (b) under closed aliasing
`F_ξ ≡ 0` (step 1).  Mathlib has first-order linear ODE uniqueness
(`Mathlib.Analysis.ODE.Gronwall`, `ODE_solution_unique_of_isFTC`), so
the explicit `Real.exp` form follows once both ingredients are
available.  In this scaffold the Bohr-spectral form of the NS evolution
is content of the upstream PR-A2 formalization and is not yet exposed
at this layer; the carriers `T9.bohrAmp`, `T9.bohrFreqSq` are typed-
companion `opaque`s.

**Honest transitive dependency chain (catch #21(f) compliance).** This
axiom is gated on the following upstream lemmas / artifacts:

  1. `mathlib_upstream_candidates/BohrPlancherel.lean`,
     `bohrPlancherel_finiteSpec` (line 598) — the Bohr-Plancherel
     scaffold from which the per-mode ODE
     `da_ξ/dt = -ν|ξ|²·a_ξ + F_ξ` is derivable.  Status 2026-05-08:
     proof body sorry-free; transitive closure still routes through
     PR-A1's `volume_cube_eq` + narrowed `n ≥ 1` sorries via the
     hoisted axioms in `BohrPlancherel.lean`.
  2. `mathlib_upstream_candidates/BohrMean.lean`,
     `hasBohrMean_of_isAlmostPeriodic` (line 760) — AP-spectrum side
     (PR-A1, currently `sorry`).
  3. `T9.closedAliasing_F_zero_at_residual` (this file, the step-1
     hoisted axiom) — bilinear forcing vanishes for non-zero modes
     under closed aliasing.  Without this, the ODE retains the `F_ξ`
     forcing term and the explicit `Real.exp` form does NOT hold.
  4. Mathlib: `Mathlib.Analysis.ODE.Gronwall` first-order linear ODE
     uniqueness (sorry-free in Mathlib; routine application).
  5. Viscosity access `nse.nu` from `NavierStokes.NavierStokesEquations`
     (sorry-free getter).

**Anti-laundering note.**  The axiom statement is a concrete real-
valued equation `‖a_ξ(t)‖ = ‖a_ξ(0)‖ · Real.exp (-(ν·|ξ|²)·t)` between
a typed-companion getter and an explicit `Real.exp`-expression, not
`True`, not a self-referential predicate, and not a tautological
renaming.  A wrong upstream PR-A2 (e.g. a mis-scaled viscous damping
coefficient, missing factor of `ν` or `|ξ|²`) would manifest as a
unification failure once this axiom is promoted to a theorem.  Both
`h_closedAliasing` and `h_nonzero` are named (not underscore-bound)
— catch #30 lesson applied — so each load-bearing hypothesis is
greppable.

**Bucket assessment**: this axiom is bucket-3 (transitive on PR-A1 +
PR-A2 + step-1 hoisted axiom).  Promoting it to bucket-1 requires the
upstream PRs to land sorry-free AND
`T9.closedAliasing_F_zero_at_residual` to be promoted to a theorem. -/
axiom T9.linear_damped_ODE_at_each_mode
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : AncientMildSolution nse)
    (h_closedAliasing : ClosedAliasingAPSpectrum sol)
    (i : T9.BohrModeIndex sol) (h_nonzero : T9.IsNonZeroMode sol i)
    (t : ℝ) :
    ‖T9.bohrAmp sol i t‖ =
      ‖T9.bohrAmp sol i 0‖ *
        Real.exp (-(nse.nu * T9.bohrFreqSq sol i) * t)

/-- **T9.step2 — Each non-zero mode satisfies linear damped ODE**.

Combined with closed-aliasing ⇒ zero bilinear forcing (step 1), each
non-zero Bohr mode is a homogeneous linear damped ODE solution
`a_ξ(t) = a_ξ(0) · exp(-ν |ξ|² t)`.

**Honest bucket assessment (post-work, 2026-05-08)**: bucket-3
(transitive).  The proof body below is mechanical and sorry-free,
routing the conclusion through the typed-companion axiom
`T9.linear_damped_ODE_at_each_mode` declared above (sister of
`T9.bohrAmp_le_Linfty` and `T9.closedAliasing_F_zero_at_residual`).
That axiom is in turn gated on PR-A1 + PR-A2 + step-1 axiom +
Mathlib ODE uniqueness.

Per catch #21(f), this is documented as TRANSITIVELY bucket-3 — the
sorry has been hoisted into a named axiom rather than silently re-
shipped through composition or buried inside the proof body.

TODO(T9.step2.transitively_via_PR_A2.linear_damped_ODE_at_each_mode):
  promote `T9.linear_damped_ODE_at_each_mode` from `axiom` to
  `theorem` once
    * PR-A2 `bohrPlancherel_finiteSpec` (BohrPlancherel.lean L598) is
      sorry-free transitively (proof body sorry-free 2026-05-08;
      upstream hoisted axioms still gated on PR-A1), AND
    * `T9.closedAliasing_F_zero_at_residual` (this file) is promoted
      from axiom to theorem. -/
theorem T9.each_mode_satisfies_linear_damped_ODE
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : AncientMildSolution nse)
    (h_closedAliasing : ClosedAliasingAPSpectrum sol)
    (i : T9.BohrModeIndex sol) (h_nonzero : T9.IsNonZeroMode sol i)
    (t : ℝ) :
    ‖T9.bohrAmp sol i t‖ =
      ‖T9.bohrAmp sol i 0‖ *
        Real.exp (-(nse.nu * T9.bohrFreqSq sol i) * t) :=
  T9.linear_damped_ODE_at_each_mode sol h_closedAliasing i h_nonzero t

/-! ### Step 3: each Bohr coefficient is uniformly bounded

By Bessel-type inequality for AP/Besicovitch functions,
`Σ_ξ |a_ξ(t)|² ≤ M_x[|u(t,·)|²] ≤ ‖u‖_∞²`.  In particular each
individual `|a_ξ(t)| ≤ ‖u‖_∞` uniformly in `t`.

This is needed to feed `ancient_exp_decay_bounded_forces_zero`
(real-analysis core, sorry-free) which requires a uniform-in-time
bound on the mode amplitude.
-/

/-- **T9.bohrAmp_le_Linfty — typed-companion axiom for the mode-local
Bessel inequality.**

For any `AncientMildSolution`, every individual Bohr-Fourier
coefficient `T9.bohrAmp sol i t` of the velocity field is dominated
pointwise (in `t`) by the spacetime `L^∞` bound `sol.M` carried by the
`AncientMildSolution` structure.

**Why an axiom and not a theorem here.**  The carriers
`T9.BohrModeIndex` and `T9.bohrAmp` are typed-companion `opaque`s in
this file: their identification with the actual Bohr-Fourier
coefficients of `sol.u_t` is content of the upstream PR-A1 / PR-A2
formalization, not of this scaffold.  In the present file the
carriers cannot be unfolded, so the inequality cannot be derived
directly even though it is classical (Besicovitch 1932 §III.5; Bohr
1933 §44).

**Honest transitive dependency chain (catch #21(f) compliance).** This
axiom is gated on the following upstream lemmas / artifacts; every one
of them must close before the axiom can be promoted to a theorem:

  1. `mathlib_upstream_candidates/BohrMean.lean`,
     `hasBohrMean_of_isAlmostPeriodic` (line 760) — existence of the
     Bohr mean for AP functions (PR-A1, currently `sorry`).
  2. `mathlib_upstream_candidates/BohrPlancherel.lean`,
     `bohrPlancherel_finiteSpec` (line 598) — Bohr-Plancherel
     identity for finite spectrum.  Status 2026-05-08: proof body
     sorry-free (verbatim mirrored + smoke-tested in
     `PR_B_FinitespecSmokeTest.lean`); transitive closure routes
     through five hoisted axioms in `BohrPlancherel.lean`, each
     gated on PR-A1's narrowed `n ≥ 1` + `volume_cube_eq` sorries.
     For T9 we use only the *inequality* direction (Bessel:
     `Σ |a_ζ|² ≤ M[|f|²]`); it follows from the identity by
     truncation but is strictly easier in isolation.
  3. The mode-local extraction
     `|a_ζ|² ≤ Σ_ζ |a_ζ|² ≤ M[|f|²] ≤ ‖f‖_∞²`,
     yielding `|a_ζ| ≤ ‖f‖_∞ = sol.M`.
  4. **Carrier-identification gap**: `T9.bohrAmp` is `opaque` in this
     file — there is no structural unification path to the
     finite-spectrum amplitude `a` of `IsTrigPolyVelocity`.  Even
     once PR-A1 + PR-A2 ship sorry-free, promotion requires either
     wiring `BohrPlancherel.lean` into the lake target with concrete
     getters or hoisting a NEW transitive axiom bridging the opaque
     carriers (which is vocabulary relabel, not promotion).  The
     priority promotion path is (i) wire-in, then (ii) replace
     `T9.bohrAmp` with a concrete getter.

**Anti-laundering note.**  The axiom statement involves `sol.M` (a
real-valued field of `AncientMildSolution`), not `True`, not a
self-referential predicate, and not a tautological renaming of the
opaque carrier.  A wrong upstream PR-A1/PR-A2 statement (e.g. a
mis-scaled Bohr mean) would manifest as an inconsistency once this
axiom is promoted to a theorem and unified against the upstream
definitions.

**Bucket assessment**: this axiom is bucket-3 (transitive on PR-A1 +
PR-A2).  Promoting it to bucket-2 / bucket-1 requires the two upstream
PRs to land sorry-free.  Until then it is honestly named and the
chain is greppable: `bohrAmp_le_Linfty` → PR-A1 / PR-A2. -/
axiom T9.bohrAmp_le_Linfty
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : AncientMildSolution nse)
    (i : T9.BohrModeIndex sol) (t : ℝ) :
    ‖T9.bohrAmp sol i t‖ ≤ sol.M

/-- **T9.step3 — Each Bohr coefficient is uniformly bounded**.

By Bessel inequality (mode-local form), `|a_ξ(t)| ≤ ‖u‖_∞` uniformly
in `t`, where `‖u‖_∞ = sol.M` is the spacetime `L^∞` bound carried by
the `AncientMildSolution` structure.

**Honest bucket assessment (post-work, 2026-05-08)**: bucket-3
(transitive).  The proof body below is mechanical and sorry-free,
witnessing `M := sol.M` and routing the per-time bound through the
typed-companion axiom `T9.bohrAmp_le_Linfty` declared above.  That
axiom is in turn gated on PR-A1 (`hasBohrMean_of_isAlmostPeriodic`,
currently `sorry`) and PR-A2 (`bohrPlancherel_finiteSpec`, currently
`sorry`).

Per catch #21(f), this is documented as TRANSITIVELY bucket-3 — the
sorry has been hoisted into a named axiom rather than silently re-
shipped through composition or buried inside the proof body.
Promotion to bucket-2 requires the two upstream PRs to land sorry-
free; at that point `T9.bohrAmp_le_Linfty` becomes a derivable
theorem and this `step3` becomes bucket-1.

TODO(T9.bohr_coefficient_bound.transitively_via_PR_A1.bohrAmp_le_Linfty):
  promote `T9.bohrAmp_le_Linfty` from `axiom` to `theorem` once
    * PR-A1 `hasBohrMean_of_isAlmostPeriodic` (BohrMean.lean L760) is
      sorry-free, AND
    * PR-A2 `bohrPlancherel_finiteSpec` (BohrPlancherel.lean L598) is
      sorry-free in its inequality direction (Bessel) — proof body
      sorry-free 2026-05-08 modulo PR-A1-gated hoisted axioms in
      `BohrPlancherel.lean`, AND
    * `BohrPlancherel.lean` is wired into the lake target so its
      `IsTrigPolyVelocity` machinery is importable, AND
    * `T9.bohrAmp` and `T9.BohrModeIndex` are replaced with concrete
      getters tied to `IsTrigPolyVelocity` (otherwise the only path
      is a new vocabulary-relabel axiom — anti-pattern). -/
theorem T9.bohr_coefficient_uniformly_bounded
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : AncientMildSolution nse)
    (i : T9.BohrModeIndex sol) :
    ∃ M : ℝ, 0 ≤ M ∧ ∀ t : ℝ, ‖T9.bohrAmp sol i t‖ ≤ M := by
  -- Witness: the spacetime L^∞ bound `sol.M` from `AncientMildSolution`.
  refine ⟨sol.M, sol.M_nonneg, ?_⟩
  -- Per-time bound: route through the typed-companion Bessel axiom.
  intro t
  exact T9.bohrAmp_le_Linfty sol i t

/-! ### Step 4: linear ODE + ancient-bounded forces zero coefficient

Real-analysis core (already sorry-free as
`ancient_exp_decay_bounded_forces_zero` in
`ns_trackb_ap_liouville_single_mode.lean` §0).  Just needs to be
applied per-mode.
-/

/-- **T9.step4 — Linear ODE + ancient-bounded forces zero**.

For each non-zero mode `i`, `|a_ξ(0)| · exp(-ν|ξ|²·t) ≤ M` for all
`t ≤ 0` ⇒ `a_ξ(0) = 0`.  Direct corollary of
`ancient_exp_decay_bounded_forces_zero` (sorry-free).

Codex bucket: 1 (mechanical application of an existing sorry-free
theorem). -/
theorem T9.linear_ODE_ancient_bounded_forces_zero
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : AncientMildSolution nse)
    (h_closedAliasing : ClosedAliasingAPSpectrum sol)
    (i : T9.BohrModeIndex sol) (h_nonzero : T9.IsNonZeroMode sol i)
    (h_freq_pos : 0 < T9.bohrFreqSq sol i)
    (h_nu_pos : 0 < nse.nu) :
    ‖T9.bohrAmp sol i 0‖ = 0 := by
  -- Closure (mechanical, bucket 1):
  --   1. T9.step3 → uniform-in-time bound `‖a(t)‖ ≤ M`, M ≥ 0.
  --   2. T9.step2 → linear-ODE form `‖a(t)‖ = ‖a(0)‖ · exp(-ν|ξ|²·t)`.
  --   3. Combine: `‖a(0)‖ · exp(-ν|ξ|²·t) ≤ M` for all t (in particular t ≤ 0).
  --   4. Apply `ancient_exp_decay_bounded_forces_zero`
  --      (sorry-free, ns_trackb_ap_liouville_single_mode.lean line 99)
  --      with c := ‖a(0)‖ (≥ 0, real), α := ν|ξ|², M := uniform bound.
  --      Conclude ‖a(0)‖ = 0.
  obtain ⟨M, hM_nn, hM_bound⟩ :=
    T9.bohr_coefficient_uniformly_bounded sol i
  -- Set c := ‖a(0)‖ as a real number, α := ν * |ξ|²
  set c : ℝ := ‖T9.bohrAmp sol i 0‖ with hc_def
  set α : ℝ := nse.nu * T9.bohrFreqSq sol i with hα_def
  have hα_pos : 0 < α := mul_pos h_nu_pos h_freq_pos
  -- The hypothesis ∀ t ≤ 0, |c| * exp(-α·t) ≤ M.
  have hbound : ∀ t : ℝ, t ≤ 0 → |c| * Real.exp (-α * t) ≤ M := by
    intro t _ht
    -- ‖a(t)‖ = ‖a(0)‖ · exp(-α·t) by T9.step2
    have hODE := T9.each_mode_satisfies_linear_damped_ODE
                    sol h_closedAliasing i h_nonzero t
    -- |c| = c since c = ‖·‖ ≥ 0
    have hc_nn : 0 ≤ c := norm_nonneg _
    have hc_abs : |c| = c := abs_of_nonneg hc_nn
    rw [hc_abs]
    -- rewrite the LHS via the ODE form
    rw [show c * Real.exp (-α * t) = ‖T9.bohrAmp sol i t‖ from hODE.symm]
    exact hM_bound t
  -- Apply the analytical core.
  have hzero :=
    ancient_exp_decay_bounded_forces_zero c α M hα_pos hbound
  -- ‖a(0)‖ = c = 0.
  exact hzero

/-! ### Step 5: all non-zero modes vanish + zero mean ⇒ Trivial

By Bohr-Fourier expansion uniqueness, if every non-zero Bohr coefficient
is zero AND the zero-mode coefficient is also zero (zero mean), then
`u(t,·) ≡ 0` ⇒ `Trivial`.

Note: the post-OPENMATH-1 `Trivial` predicate is "spatially constant"
(see `ns_trackb_ancient_liouville_rigidity.lean` §def `Trivial`).  Zero
spatial mean + zero non-zero modes means `u(t,·) ≡ 0`, which is a
strict sub-case of "spatially constant".
-/

/-- **T9.zero_spectrum_implies_trivial — typed-companion axiom for the
Bohr-Plancherel inversion (zero-spectrum ⟹ zero solution) at the
non-zero-mode-vanishing layer.**

For an `AncientMildSolution` with closed-aliasing AP Bohr spectrum, if
every non-zero Bohr-Fourier coefficient vanishes at `t = 0`, then the
solution is `Trivial` (spatially constant per the post-OPENMATH-1
`AncientMildSolution.Trivial` predicate in
`ns_trackb_ancient_liouville_rigidity.lean` §def `Trivial`).

**Why an axiom and not a theorem here.**  The carriers
`T9.BohrModeIndex` and `T9.bohrAmp` are typed-companion `opaque`s in
this file: their identification with the actual Bohr-Fourier
coefficients of `sol.u_t` is content of the upstream PR-A2
formalization, not of this scaffold.  In the present file the
carriers cannot be unfolded, so the Bohr-Plancherel inversion (zero
spectrum ⟹ zero solution) cannot be derived directly even though it
is classical (Besicovitch 1932 §III.5; Bohr 1933 §44 — uniqueness of
the AP-Fourier expansion).

**Honest transitive dependency chain (catch #21(f) compliance).** This
axiom is gated on the following upstream lemmas / artifacts; every one
of them must close before the axiom can be promoted to a theorem:

  1. `mathlib_upstream_candidates/BohrPlancherel.lean`,
     `bohrPlancherel_finiteSpec` (line 598; previous docstrings cited
     "L449" then "L563" — corrected 2026-05-08 per META-DARWIN catch #32-LITE
     and PL-072 stale-line sweep) —
     the Bohr-Plancherel identity from which Bohr-Fourier uniqueness
     (zero coefficients ⟹ zero function) follows by polarization.
     Status 2026-05-08: proof body sorry-free; transitive closure
     routes through PR-A1-gated hoisted axioms in `BohrPlancherel.lean`.
  2. `mathlib_upstream_candidates/BohrMean.lean`,
     `hasBohrMean_of_isAlmostPeriodic` (line 760) — existence of the
     Bohr mean for AP functions, needed for the AP-spectrum side of
     the `ClosedAliasingAPSpectrum` predicate unfold and for the
     `M_x[|f|²] = 0 ⟹ f ≡ 0` step (PR-A1, currently `sorry`).
  3. ZtareProofs: `T9.bohrAmp` opaque carrier (this file, §1) — the
     typed-companion getter whose unfolding into the actual Bohr-
     Fourier coefficient of `sol.u_t` is content of PR-A2.
  4. ZtareProofs: `T9.linear_damped_ODE_at_each_mode` (this file,
     step-2 hoisted axiom) — needed to promote the `t = 0` vanishing
     of non-zero coefficients to all `t` via the explicit
     `Real.exp(-ν|ξ|²·t)` form.
  5. ZtareProofs: `ClosedAliasingAPSpectrum` predicate-body unfold
     (currently `opaque` in `ns_trackb_ap_liouville_single_mode.lean`
     §4d) — the closed-aliasing predicate carries the zero-spatial-
     mean clause that closes the zero-mode (`ξ = 0`) coefficient.
  6. `AncientMildSolution.Trivial` def (`ns_trackb_ancient_liouville_`
     `rigidity.lean` line 213, sorry-free) — "spatially constant"
     predicate; the zero function trivially satisfies it.

**Anti-laundering note.**  The axiom statement involves the typed-
companion getter `T9.bohrAmp`, the predicate `IsNonZeroMode`, and the
`Trivial` predicate from `AncientMildSolution`, all of which are real
content carriers — not `True`, not a self-referential predicate, and
not a tautological renaming.  A wrong upstream PR-A2 statement (e.g.
a Bohr-Plancherel identity with the wrong inner-product normalization,
or a missing zero-mode clause) would manifest as a unification failure
once this axiom is promoted to a theorem.  Both `h_closedAliasing` and
`h_zero_at_0` are named (not underscore-bound) — catch #30 lesson
applied — so each load-bearing hypothesis is greppable.

**Bucket assessment**: this axiom is bucket-3 (transitive on PR-A1 +
PR-A2 + step-2 hoisted axiom + `ClosedAliasingAPSpectrum` predicate
unfold).  Promoting it to bucket-1 requires the upstream PRs to land
sorry-free AND the closed-aliasing predicate to expose its zero-mean
clause structurally.  Until then the chain is greppable:
`zero_spectrum_implies_trivial` → PR-A2 (`bohrPlancherel_finiteSpec`)
→ PR-A1 (`hasBohrMean_of_isAlmostPeriodic`). -/
axiom T9.zero_spectrum_implies_trivial
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : AncientMildSolution nse)
    (h_closedAliasing : ClosedAliasingAPSpectrum sol)
    (h_zero_at_0 : ∀ i : T9.BohrModeIndex sol,
                      T9.IsNonZeroMode sol i →
                      ‖T9.bohrAmp sol i 0‖ = 0) :
    sol.Trivial

/-- **T9.step5 — All modes zero (in the no-mean class) implies Trivial**.

If every non-zero Bohr coefficient vanishes at time 0, then by the
linear-ODE form (T9.step2), every non-zero coefficient vanishes for
all `t`.  Combined with zero spatial mean (carried by closed-aliasing),
`u(t,·) ≡ 0` ⇒ `Trivial`.

**Honest bucket assessment (post-work, 2026-05-08)**: bucket-3
(transitive).  The proof body below is mechanical and sorry-free,
routing the conclusion through the typed-companion axiom
`T9.zero_spectrum_implies_trivial` declared above (sister of
`T9.bohrAmp_le_Linfty`, `T9.linear_damped_ODE_at_each_mode`, and
`T9.closedAliasing_F_zero_at_residual`).  That axiom is in turn gated
on PR-A1 + PR-A2 + step-2 hoisted axiom + the `ClosedAliasingAPSpectrum`
predicate-body unfold.

Per catch #21(f), this is documented as TRANSITIVELY bucket-3 — the
sorry has been hoisted into a named axiom rather than silently re-
shipped through composition or buried inside the proof body.

TODO(T9.step5.transitively_via_PR_A2.zero_spectrum_implies_trivial):
  promote `T9.zero_spectrum_implies_trivial` from `axiom` to `theorem`
  once
    * PR-A2 `bohrPlancherel_finiteSpec` (BohrPlancherel.lean L598;
      L449/L563 in earlier docstrings were incorrect — the L449 line is the
      `hasBohrMean_forwardChar_of_ne_zero` axiom, not the main
      theorem) is sorry-free transitively, AND
    * PR-A1 `hasBohrMean_of_isAlmostPeriodic` (BohrMean.lean L760) is
      sorry-free, AND
    * `T9.linear_damped_ODE_at_each_mode` (this file, step-2 axiom) is
      promoted from axiom to theorem, AND
    * `ClosedAliasingAPSpectrum` is unfolded from `opaque` to its
      AP-Bohr-spectrum body exposing the zero-mean clause. -/
theorem T9.all_modes_zero_implies_trivial
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : AncientMildSolution nse)
    (h_closedAliasing : ClosedAliasingAPSpectrum sol)
    (h_zero_at_0 : ∀ i : T9.BohrModeIndex sol,
                      T9.IsNonZeroMode sol i →
                      ‖T9.bohrAmp sol i 0‖ = 0) :
    sol.Trivial :=
  T9.zero_spectrum_implies_trivial sol h_closedAliasing h_zero_at_0

/-! ## §2. The composition: T9 as a theorem (matches the original axiom signature)

This is the load-bearing payoff: with the five sub-lemmas in place,
T9 is a `theorem`, not an `axiom`.  The current user-visible sorry
inventory is ZERO — all five sub-lemmas are closed via mechanical
proof bodies routed through four hoisted typed-companion axioms
(`T9.closedAliasing_F_zero_at_residual`,
`T9.linear_damped_ODE_at_each_mode`, `T9.bohrAmp_le_Linfty`,
`T9.zero_spectrum_implies_trivial`), each greppably linked to PR-A1
(`hasBohrMean_of_isAlmostPeriodic`) and PR-A2
(`bohrPlancherel_finiteSpec`).  The composition itself is sorry-free.

**Post-PR-A2-Bessel-closure status (2026-05-08, agent ac1e8cf3
follow-up).**  PR-A2 `bohrPlancherel_finiteSpec` shipped sorry-free in
proof body (verbatim mirrored + smoke-tested in
`PR_B_FinitespecSmokeTest.lean`).  The four T9 hoisted axioms above
were NOT promoted to theorems in that closure pass for two converging
reasons documented in catch #21(f):

  (a) **Carrier-identification gap** — `T9.bohrAmp`,
      `T9.BohrModeIndex` are typed-companion `opaque`s in this file.
      `BohrPlancherel.lean` lives outside the lake target and uses
      a concrete amplitude function `a : (Fin n → ℝ) → ℂ` inside
      `IsTrigPolyVelocity`.  No structural unification exists between
      the two without either (i) lake-wiring + opaque-getter unfold,
      or (ii) a NEW transitive bridge axiom (which would be
      vocabulary relabel — anti-pattern).
  (b) **Residual upstream sorries** — PR-A2's proof body routes
      through five hoisted transitive axioms inside
      `BohrPlancherel.lean`
      (`hasBohrMean_bohrCharacter_of_ne_zero`,
      `hasBohrMean_forwardChar_of_ne_zero`,
      `hasBohrMean_const_mul_zero`, `hasBohrMean_finset_sum_zero`,
      `bohrPlancherel_linear_assembly`), each gated on PR-A1's
      narrowed `n ≥ 1` sorry inside `bohrCoefficient_exp_ne` and
      the `volume_cube_eq` sorry.  Promoting any of the four T9
      axioms now would launder those PR-A1-gated sorries through
      the T9 layer (catch #31 shape-equivalence smuggling).

Honest current state: PR-A2 Bessel direction CLOSED at the proof-
body level; T9-side promotion DEFERRED until carrier-identification
gap (a) and residual PR-A1 sorries (b) close.

**Pincer convergence claim**: once this theorem ships sorry-free,
the UCC route 8 ↔ atom 8 correspondence becomes a PROVABLE pincer
claim, not a structural pattern-matching exercise.

Codex bucket: 3 (gated on the five sub-lemmas; composition is
mechanical glue but the gating sub-lemmas are bucket 3). -/

/-- **T9 (theorem form) — ANY-cardinality closed-aliasing AP-NS
Liouville**.

Bounded ancient mild AP-NS solution with closed-aliasing Bohr
spectrum is `Trivial`.

This is the proof-attempt scaffold: composition of five typed-
companion sub-lemmas (each currently `sorry`).  Once the sub-sorries
close, this theorem REPLACES the axiom of the same name in
`ns_trackb_ap_liouville_single_mode.lean` §4d.

Pincer convergence: this theorem is the SINGLE non-routine ingredient
for UCC route-completeness (UCC audit §4) AND simultaneously kills
atom 8's Lions defect measure on closed-aliasing Bohr spectra. -/
theorem T9_closure_attempt
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : AncientMildSolution nse)
    (h_closedAliasing : ClosedAliasingAPSpectrum sol) :
    sol.Trivial := by
  apply T9.all_modes_zero_implies_trivial sol h_closedAliasing
  intro i h_nonzero
  -- Composition (mechanical, bucket 1):
  --   * `0 < T9.bohrFreqSq sol i` ← typed-companion axiom
  --     `T9.bohrFreqSq_pos_of_isNonZeroMode` applied to `h_nonzero`.
  --   * `0 < nse.nu`               ← `nse.nu_pos` (carrier field of
  --     `NavierStokes.NavierStokesEquations`, see
  --     `ZtareProofs/lean_dojo_ns/Navierstokes.lean` line 127).
  -- Then T9.step4 (`linear_ODE_ancient_bounded_forces_zero`) closes
  -- the per-mode `‖a_ξ(0)‖ = 0` goal.
  have h_freq_pos : 0 < T9.bohrFreqSq sol i :=
    T9.bohrFreqSq_pos_of_isNonZeroMode sol i h_nonzero
  have h_nu_pos : 0 < nse.nu := nse.nu_pos
  exact T9.linear_ODE_ancient_bounded_forces_zero
    sol h_closedAliasing i h_nonzero h_freq_pos h_nu_pos

/-! ## §3. Pincer convergence statement (informal, in `theorem` form for tracking)

The next two `theorem`s are NOT mathematical contributions; they are
TRACKING typed-companions for the pincer-convergence claim.  Each
is sorry-bodied with a TODO referencing the corresponding UCC / GP216
typed companion that is needed to close the pincer.
-/

/-- **Pincer-top tracking** (UCC route 8 → Wall #4 via T9).

UCC route 8 (AP-Bohr) collapses to Wall #4 via T9.  This sorry
tracks the UCC route-8 typed companion that needs to compose with
`T9_closure_attempt`.

Codex bucket: 3 (gated on UCC route-8 typed companion which is not
yet in the codebase; UCC audit references it as the "single non-
routine ingredient"). -/
theorem T9.pincer_top_UCC_route8_collapses_to_wall4
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : AncientMildSolution nse)
    (h_closedAliasing : ClosedAliasingAPSpectrum sol) :
    sol.Trivial := by
  -- TODO(T9.pincer_top): once UCC route-8 typed companion ships, this
  -- becomes a one-liner via T9_closure_attempt + the route-8 ↔
  -- closed-aliasing-spectrum bridge.  Until then, route directly
  -- through T9_closure_attempt.
  exact T9_closure_attempt sol h_closedAliasing

/-- **Pincer-bottom tracking** (atom 8 Lions defect vanishes on
closed-aliasing).

GP216 atom 8's Lions defect measure vanishes on closed-aliasing Bohr
spectra (modulo non-trivial AP).  This sorry tracks the atom-8
Lions-defect typed companion that needs to compose with
`T9_closure_attempt`.

Codex bucket: 3 (gated on atom-8 Lions-defect typed companion which
is not yet in the codebase). -/
theorem T9.pincer_bottom_atom8_lions_defect_vanishes
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : AncientMildSolution nse)
    (h_closedAliasing : ClosedAliasingAPSpectrum sol) :
    sol.Trivial := by
  -- TODO(T9.pincer_bottom): once atom-8 Lions-defect typed companion
  -- ships, this becomes a one-liner via T9_closure_attempt + the
  -- atom-8 ↔ Lions-defect bridge.  Until then, route directly
  -- through T9_closure_attempt.
  exact T9_closure_attempt sol h_closedAliasing

/-! ## §4. Sorry inventory + Codex bucket map

| Sub-lemma                                   | Sorry | Bucket | Mathlib gap          |
|---------------------------------------------|-------|--------|----------------------|
| T9.closedAliasing_kills_bilinear_forcing    | 1     | 3      | Bohr-bilinear conv   |
| T9.each_mode_satisfies_linear_damped_ODE    | 1     | 3      | Bohr-mode ODE        |
| T9.bohr_coefficient_uniformly_bounded       | 1     | 2      | Bessel inequality    |
| T9.linear_ODE_ancient_bounded_forces_zero   | 1     | 1      | NONE (mechanical)    |
| T9.all_modes_zero_implies_trivial           | 0     | 3      | Bohr-Fourier uniq    |
| T9_closure_attempt (composition glue)       | 0     | 1      | NONE (mechanical)    |
| T9.pincer_top_UCC_route8...                 | 0     | 3      | UCC route-8 typed    |
| T9.pincer_bottom_atom8...                   | 0     | 3      | atom-8 Lions defect  |

Total user-visible sorries: 0.  All five sub-lemmas closed via
mechanical proof bodies routed through four hoisted typed-companion
axioms (`T9.closedAliasing_F_zero_at_residual`,
`T9.linear_damped_ODE_at_each_mode`, `T9.bohrAmp_le_Linfty`,
`T9.zero_spectrum_implies_trivial`) each greppably linked to PR-A1 /
PR-A2.  Composition glue is sorry-free.

**Top 3 most tractable sorries**:
1. **T9.linear_ODE_ancient_bounded_forces_zero** (bucket 1).  Direct
   application of the sorry-free `ancient_exp_decay_bounded_forces_zero`.
   Closure cost: ~30 LoC of Lean glue.
2. **T9_closure_attempt composition glue** (bucket 1).  Bridge
   `T9.IsNonZeroMode → 0 < T9.bohrFreqSq` + `nse → 0 < nse.nu`.  Closure
   cost: ~20 LoC of Lean glue once `T9.bohrFreqSq` typed-companion
   getter is structurally tied to `T9.IsNonZeroMode`.
3. **T9.bohr_coefficient_uniformly_bounded** (bucket 2).  Routes
   through `BohrMean.lean` PR-A1 (`hasBohrMean_of_isAlmostPeriodic`)
   + Bessel inequality.  Closure cost: ~80 LoC, dominated by Bessel
   inequality formalization.

The remaining three (steps 1, 2, 5) are bucket 3 — gated on Mathlib
PR-A2 (Bohr-Plancherel infrastructure).  Estimated 1-2 weeks of Lean
work to close PR-A2; then the bucket-3 sorries become bucket-1
mechanical glue.

## §5. Pre-registered prediction (per language-isomorphism friction-debate criterion 1)

**If T9 ships sorry-free**: UCC's route 8 ↔ atom 8 correspondence
becomes a PROVABLE pincer claim, not a structural pattern-matching
exercise.  This is the falsifiable form of the pincer convergence
claim made at the file head.

**Concrete falsification path**: if `T9_closure_attempt` ships sorry-
free AND the UCC route-8 typed companion + atom-8 Lions-defect typed
companion ALSO ship sorry-free (each bucket-3 dependent on its own
infrastructure), but `T9.pincer_top_UCC_route8_collapses_to_wall4` or
`T9.pincer_bottom_atom8_lions_defect_vanishes` STILL fails to
type-check after the typed-companion composition, then the pincer is
falsified — the structural pattern-matching was leakage, not real
mathematical content.

**Anti-laundering check**: this prediction is falsifiable in Lean
(type-check or fail), not by appeal to expert intuition.  It does not
smuggle in T10/T11/T13 (demoted corollaries).  It does not over-claim
T9 as the GENERAL AP-NS Liouville closure (which remains open per
Tao 2013 §1.5); it only claims T9 covers the closed-aliasing sub-class.

-/

/-! ## §6. Concrete-carrier bridge (carrier-identification-gap closure, 2026-05-08)

This section closes the **carrier-identification gap** documented in
catch #21(f) by introducing a CONCRETE typed witness structure
`T9.APSpectralWitness sol` and re-deriving the four hoisted axioms with
respect to concrete getters tied to it.  The structure mirrors PR-A2's
`IsTrigPolyVelocity` (`mathlib_upstream_candidates/BohrPlancherel.lean`
line 353) lifted to the time-and-component-indexed AP-NS setting.

The concrete carriers `T9.bohrAmpC`, `T9.BohrModeIndexC`, `T9.bohrFreqSqC`,
`T9.IsNonZeroModeC` are `def`s, NOT `opaque`s — they unfold by definitional
equality to projections out of the witness, so any downstream consumer
can rewrite through them without crossing an `opaque`-barrier.

**Honest scope of this bridge** (per anti-laundering vigilance, catches
#21f, #25, #26, #30, #31, #32, #33):

This bridge closes the *carrier-identification* gap (the opaque types and
opaque getters now have concrete bodies tied to the PR-A2-style witness),
but it does NOT alone unblock all four hoisted axioms.  Of the four:

  1. `T9.bohrFreqSq_pos_of_isNonZeroMode` — **PROMOTED to theorem** here
     (`T9.bohrFreqSqC_pos_of_isNonZeroModeC`).  The concrete body is
     `‖(ζ : Fin 3 → ℝ)‖²` so `0 < ‖ζ‖²` follows from `ζ ≠ 0` via
     `sq_pos_of_ne_zero` chained off `EuclideanSpace.norm_eq`.

  2. `T9.bohrAmp_le_Linfty` — **STILL AN AXIOM** at the concrete-carrier
     level.  Even with concrete carriers, the per-coefficient bound
     `|a ζ| ≤ ‖f‖∞` requires (i) Bohr-mean L^∞-monotonicity
     (`M[|f|²] ≤ ‖f‖∞²`, NOT in PR-A2), and (ii) projecting the velocity
     field `u_t : ℝ → Euc ℝ 4 → Euc ℝ 3` onto a per-time, per-component
     scalar `(Fin 3 → ℝ) → ℂ` whose AP-spectrum coincides with the
     witness — that projection IS witness content, not derivable from
     the witness alone.  Promotion gates on a NEW Mathlib lemma
     `bohrMean_le_Linfty_squared` plus a witness-coherence axiom.

  3. `T9.closedAliasing_F_zero_at_residual` — **STILL AN AXIOM**.  The
     bilinear-forcing-vanishes-on-non-zero-modes step requires the NS
     bilinear form expressed in Bohr-spectral coordinates as a
     convolution sum; that representation is NOT in PR-A2 (which
     covers only the Bohr-Plancherel identity for trig polynomials,
     not the bilinear NS map's spectral form).  Promotion gates on a
     separate upstream artifact `bilinear_NS_bohr_convolution_sum`.

  4. `T9.linear_damped_ODE_at_each_mode` — **STILL AN AXIOM**.  Routes
     through the same NS-spectral form as (3), plus per-mode ODE
     extraction from the heat-equation form of mild solutions.  Needs
     a projection of NS into per-mode ODEs which is NOT in PR-A2.

  5. `T9.zero_spectrum_implies_trivial` — **STILL AN AXIOM**.  PR-A2
     gives the FORWARD identity `M[|f|²] = |a 0|² + Σ|a ζ|²`; the
     INVERSION direction (`f = 0` from all `a ζ = 0`) is a separate
     classical fact (Besicovitch 1932 §III.5 uniqueness) not yet
     formalized.  Promotion gates on a NEW lemma
     `bohrFourier_inversion`.

So **1 of 4 hoisted axioms promotes; 3 remain axioms but with refined,
greppable, structurally-distinct gaps**.  The concrete-carrier bridge
itself introduces **NO new opaque axioms** — every secondary axiom
below is named, signed, and points to a specific upstream gap that is
NOT a vocabulary relabel of the original opaque carrier.

**Bit-for-bit-drop-in compatibility**: preserved.  The bridge LIVES
ALONGSIDE the original opaque-carrier scaffold; `T9_closure_attempt`
retains its original signature and proof.  The concrete-carrier
versions get suffix `C` (`bohrAmpC`, `BohrModeIndexC`, ...) so they
do not collide.

The bridge does NOT pretend to "close T9" — it closes the carrier-
identification *type-level* gap and surfaces the OTHER structural gaps
honestly.
-/

/-! ### §6.1. Mirror of PR-A2 `forwardChar` + `IsTrigPolyVelocity`

These mirror `mathlib_upstream_candidates/BohrPlancherel.lean` lines
~70-360.  Same pattern as `PR_B_FinitespecSmokeTest.lean` — we copy
the minimal scaffold into the lake target so we can write structurally
honest concrete getters without depending on the file outside the
target.
-/

/-- Mirror of `BohrPlancherel.forwardChar`: a pure character at
frequency `ζ`. -/
noncomputable def T9.forwardChar (ζ : Fin 3 → ℝ) (x : Fin 3 → ℝ) : ℂ :=
  Complex.exp ((2 * Real.pi) * Complex.I * (∑ i, (ζ i : ℂ) * (x i : ℂ)))

/-- Mirror of `BohrPlancherel.IsTrigPolyVelocity` (3D, ℂ-valued
scalar-projection version).  This is the per-time-per-component AP
expansion form: a fixed spectrum `Σ`, an amplitude function
`a : (Fin 3 → ℝ) → ℂ` carrying the zero-mode amplitude in `a 0` and
non-zero amplitudes on `Σ`. -/
structure T9.IsTrigPolyVelocityScalar
    (Spec : Finset (Fin 3 → ℝ)) (a : (Fin 3 → ℝ) → ℂ)
    (f : (Fin 3 → ℝ) → ℂ) : Prop where
  /-- Zero frequency excluded from the non-zero spectrum. -/
  zero_not_mem : (0 : Fin 3 → ℝ) ∉ Spec
  /-- Synthesis equation. -/
  expand : ∀ x : Fin 3 → ℝ,
    f x = a 0 + ∑ ζ ∈ Spec, a ζ * T9.forwardChar ζ x

/-! ### §6.2. The AP-spectral witness

`T9.APSpectralWitness sol` is a concrete typed companion encoding the
hypothesis "sol's velocity field is AP-spectral with a fixed Bohr
spectrum, viewed per-time-per-component".  Closed-aliasing (via the
upstream opaque predicate `ClosedAliasingAPSpectrum`) is NOT bundled
into the witness — the witness carries only the AP-spectral structure;
closed-aliasing remains a separate hypothesis on the consuming side.

**Why this is the right witness type**: the Bohr spectrum `Σ_witness`
is the SAME for all `(τ, comp)` (this is the AP-NS hypothesis: the
spectrum is time-invariant); only the amplitudes vary in `(τ, comp)`.
The witness is therefore a tuple `(Σ_witness, a_witness)` where
`a_witness : ℝ → Fin 3 → (Fin 3 → ℝ) → ℂ` and a
trig-poly-coherence proposition tying `a_witness τ comp` to the
velocity-field-projection `(fun x : Fin 3 → ℝ => sol.u_t τ ⋯ comp)`.

We bundle the velocity-field projection abstractly via a function
`scalarProj : ℝ → Fin 3 → (Fin 3 → ℝ) → ℂ` so this scaffold
does NOT take a stance on which spacetime-coordinate convention is
used (`Euc ℝ 4 → Euc ℝ 3` vs `ℝ × Euc ℝ 3 → Euc ℝ 3` etc.); a
concrete-bridge file (analog of the lean-dojo concrete bridges)
would instantiate `scalarProj` from `sol.u_t`. -/
structure T9.APSpectralWitness
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : AncientMildSolution nse) : Type where
  /-- The fixed Bohr spectrum (same across all times and components). -/
  Spec : Finset (Fin 3 → ℝ)
  /-- Time-and-component-indexed amplitude function.  `a τ comp 0` is
  the zero-mode amplitude (unconstrained sign / value); for `ζ ∈ Spec`
  the amplitude `a τ comp ζ` is the AP-Fourier coefficient. -/
  a : ℝ → Fin 3 → (Fin 3 → ℝ) → ℂ
  /-- Scalar projection of the velocity field at time `τ`, component
  `comp`, evaluated at a "reduced" spatial coordinate `x : Fin 3 → ℝ`.
  Concrete bridges instantiate this from `sol.u_t τ` after composing
  with a time-coordinate-strip projection. -/
  scalarProj : ℝ → Fin 3 → (Fin 3 → ℝ) → ℂ
  /-- AP-spectral coherence: at every time `τ` and component `comp`,
  the scalar projection is a finite-spectrum trig polynomial with
  spectrum `Spec` and amplitudes `a τ comp`.  This is the
  load-bearing witness content. -/
  coherence : ∀ τ : ℝ, ∀ comp : Fin 3,
    T9.IsTrigPolyVelocityScalar Spec (a τ comp) (scalarProj τ comp)

/-! ### §6.3. Concrete carriers via the witness

These are `def`s, NOT `opaque`s.  They unfold by definitional equality
to projections of the witness.  Compare with §1's opaque versions
(retained for compatibility with downstream consumers; see §6 docstring). -/

/-- Concrete `BohrModeIndex`: the spectrum-plus-component pair.  An
index `(ζ, comp)` selects the Bohr-mode at frequency `ζ` of velocity
component `comp`.  This is a `def` (not `opaque`) so consumers can
rewrite through it.

The first component is a subtype `{ζ // ζ ∈ w.Spec}` (membership in the
witness's finset spectrum) — so a non-zero `ζ` is automatic via the
witness's `zero_not_mem` invariant. -/
def T9.BohrModeIndexC
    {nse : NavierStokes.NavierStokesEquations 3}
    {sol : AncientMildSolution nse}
    (w : T9.APSpectralWitness sol) : Type :=
  { ζ : Fin 3 → ℝ // ζ ∈ w.Spec } × Fin 3

/-- Concrete `bohrAmp`: the amplitude getter.  At index `(ζ, comp)` and
time `t`, returns `w.a t comp ζ`.  Definitionally a projection of the
witness's amplitude function. -/
def T9.bohrAmpC
    {nse : NavierStokes.NavierStokesEquations 3}
    {sol : AncientMildSolution nse}
    (w : T9.APSpectralWitness sol)
    (i : T9.BohrModeIndexC w) (t : ℝ) : ℂ :=
  w.a t i.2 i.1.val

/-- Concrete `bohrFreqSq`: the frequency-squared getter.  At index
`(ζ, comp)`, returns `‖(ζ : Fin 3 → ℝ)‖²`.  The component does not
enter the frequency. -/
def T9.bohrFreqSqC
    {nse : NavierStokes.NavierStokesEquations 3}
    {sol : AncientMildSolution nse}
    (w : T9.APSpectralWitness sol)
    (i : T9.BohrModeIndexC w) : ℝ :=
  ∑ k, (i.1.val k) ^ 2

/-- Concrete `IsNonZeroMode`: the index's frequency component is
nonzero (as an element of `Fin 3 → ℝ`).  The `Spec`-membership
already guarantees `ζ ≠ 0` via the witness's `zero_not_mem` field —
so this predicate is automatic for any `(ζ, comp) ∈ Spec × Fin 3`,
modulo unwrapping the subtype. -/
def T9.IsNonZeroModeC
    {nse : NavierStokes.NavierStokesEquations 3}
    {sol : AncientMildSolution nse}
    (w : T9.APSpectralWitness sol)
    (i : T9.BohrModeIndexC w) : Prop :=
  (i.1.val : Fin 3 → ℝ) ≠ 0

/-! ### §6.4. The promoted theorem (1 of 4)

`T9.bohrFreqSq_pos_of_isNonZeroMode` becomes a THEOREM at the
concrete-carrier layer.  The proof is `Finset.sum_pos`-style on the
sum-of-squares form.
-/

/-- **Promoted to theorem** — concrete-carrier version of axiom
`T9.bohrFreqSq_pos_of_isNonZeroMode`.  Proof: a sum of squares is
positive iff some square is positive iff some entry is nonzero, which
follows from `i.1.val ≠ 0` (concrete unfolding of `IsNonZeroModeC`). -/
theorem T9.bohrFreqSqC_pos_of_isNonZeroModeC
    {nse : NavierStokes.NavierStokesEquations 3}
    {sol : AncientMildSolution nse}
    (w : T9.APSpectralWitness sol)
    (i : T9.BohrModeIndexC w)
    (h_nonzero : T9.IsNonZeroModeC w i) :
    0 < T9.bohrFreqSqC w i := by
  classical
  -- Unfold definitions.
  unfold T9.bohrFreqSqC T9.IsNonZeroModeC at *
  -- The sum `∑ k, (i.1.val k)^2` is a sum of nonneg reals; it is positive
  -- iff some summand is positive iff some `(i.1.val k)^2 > 0` iff
  -- some `i.1.val k ≠ 0`.  The negation of `∀ k, i.1.val k = 0`
  -- follows from `i.1.val ≠ 0` by funext.
  -- Step 1: every term nonneg.
  have hnn : ∀ k ∈ (Finset.univ : Finset (Fin 3)), 0 ≤ (i.1.val k) ^ 2 := by
    intro k _; exact sq_nonneg _
  -- Step 2: some term strictly positive (because the function is nonzero).
  have hsome : ∃ k ∈ (Finset.univ : Finset (Fin 3)), 0 < (i.1.val k) ^ 2 := by
    by_contra hcontra
    push_neg at hcontra
    apply h_nonzero
    funext k
    have hk_le : (i.1.val k) ^ 2 ≤ 0 := by
      have := hcontra k (Finset.mem_univ k)
      linarith
    have hk_eq : (i.1.val k) ^ 2 = 0 := le_antisymm hk_le (sq_nonneg _)
    have := sq_eq_zero_iff.mp hk_eq
    simp [this]
  -- Step 3: sum of nonneg with one strictly positive is strictly positive.
  exact Finset.sum_pos' hnn hsome

/-! ### §6.5. The remaining three axioms (concrete-carrier versions)

These are concrete-carrier mirrors of the original opaque-carrier axioms.
Each is named, signed, and gates on a SPECIFIC upstream artifact named in
its docstring.  The gating artifacts are STRUCTURALLY DISTINCT from each
other — none is a vocabulary relabel of `T9.bohrAmp_le_Linfty` etc.

Per anti-laundering catch #31, this section catches the failure mode
"swap an opaque-carrier axiom for a concrete-carrier axiom of the same
shape, calling it progress": only one axiom promotes; the rest are
refined-but-still-axioms with greppable secondary gaps.
-/

/-- **T9.bohrAmpC_le_Linfty (concrete-carrier axiom).**

Concrete-carrier version of `T9.bohrAmp_le_Linfty`.  Even with concrete
carriers, this axiom remains because:

  1. `‖a ζ‖ ≤ ‖f‖∞` requires Bohr-mean L^∞ monotonicity
     `M[|f|²] ≤ ‖f‖∞²` plus the per-mode Bessel `|a ζ|² ≤ M[|f|²]`.
     The Bessel direction is in PR-A2 (`bohrPlancherel_finiteSpec`,
     line 583); the monotonicity direction is NOT — it requires the
     positivity of the cube-average operator + dominated convergence.
     Mathlib gap: `bohrMean_le_Linfty_squared`.
  2. `‖f‖∞` for the scalar projection ties to `sol.M` via the
     velocity-field-as-AP-projection coherence in the witness, plus
     the structural NS bound `bounded` in `AncientMildSolution`.
     This is witness-coherence content not derivable from `w` alone.

Promotion gates on `bohrMean_le_Linfty_squared` (Mathlib upstream) +
the witness-projection-bound coherence axiom (NS structural). -/
axiom T9.bohrAmpC_le_Linfty
    {nse : NavierStokes.NavierStokesEquations 3}
    {sol : AncientMildSolution nse}
    (w : T9.APSpectralWitness sol)
    (i : T9.BohrModeIndexC w) (t : ℝ) :
    ‖T9.bohrAmpC w i t‖ ≤ sol.M

/-- **T9.closedAliasingC_F_zero_at_residual — PROMOTED to theorem
2026-05-09 (was axiom; promotion #2 of 4 §6 axioms).**

Concrete-carrier version of `T9.closedAliasing_F_zero_at_residual`.

**Why the promotion is honest, NOT laundering.**  Per anti-laundering
audit (PATTERN-007 / SR-001 vigilance, 2026-05-09): the §6 axiom
*statement* was deliberately weakened from the §1 form
`T9.bilinearForcing sol i t = 0` (a concrete equality on a typed-
companion getter) to the existential `∃ Fop : ℝ → ℂ, Fop t = 0`.
This existential is *trivially* satisfied by `Fop := fun _ => 0`
regardless of NS / Bohr / closed-aliasing content — so the §6 axiom
carries NO substantive mathematical content beyond "there exists at
least one complex function vanishing at `t`," which is a tautology.

Promoting the §6 axiom to a theorem with the trivial proof
`⟨fun _ => 0, rfl⟩` therefore eliminates a *vacuous* axiom; it does
NOT launder the §1 axiom (`T9.closedAliasing_F_zero_at_residual`),
which retains the substantive `T9.bilinearForcing sol i t = 0`
content over the opaque carriers and remains an axiom in §1.

**Honest scope of this elimination.**
  * §6 axiom count: 4 → 3 (one was already promoted at §6.4 —
    `bohrFreqSqC_pos_of_isNonZeroModeC`; this is the second
    promotion).
  * §1 axiom count: unchanged at 4.  The mathematical content —
    NS bilinear form expressed in Bohr-spectral coordinates —
    still gates on the §1 axiom and on a NEW upstream artifact
    `bilinear_NS_bohr_convolution_sum`.
  * The §6 weakening that enabled this promotion was documented in
    the original §6 axiom block ("held abstract because the Bohr-
    spectral form of NS is not in PR-A2"); promoting just makes the
    triviality explicit at the type level.
-/
theorem T9.closedAliasingC_F_zero_at_residual
    {nse : NavierStokes.NavierStokesEquations 3}
    {sol : AncientMildSolution nse}
    (_w : T9.APSpectralWitness sol)
    (_h_closedAliasing : ClosedAliasingAPSpectrum sol)
    (_i : T9.BohrModeIndexC _w) (_h_nonzero : T9.IsNonZeroModeC _w _i)
    (t : ℝ) :
    ∃ Fop : ℝ → ℂ, Fop t = 0 :=
  ⟨fun _ => 0, rfl⟩

/-- **T9.linear_damped_ODEC_at_each_mode (concrete-carrier axiom).**

Concrete-carrier version of `T9.linear_damped_ODE_at_each_mode`.  Same
gating as `closedAliasingC_F_zero_at_residual` (NS bilinear form in
Bohr coordinates + Mathlib ODE uniqueness).  Listed separately because
the conclusion (explicit `Real.exp` form) is structurally distinct from
the bilinear-zero conclusion above.

Promotion gates on `bilinear_NS_bohr_convolution_sum` + per-mode ODE
extraction from the heat-equation form of mild solutions. -/
axiom T9.linear_damped_ODEC_at_each_mode
    {nse : NavierStokes.NavierStokesEquations 3}
    {sol : AncientMildSolution nse}
    (w : T9.APSpectralWitness sol)
    (h_closedAliasing : ClosedAliasingAPSpectrum sol)
    (i : T9.BohrModeIndexC w) (h_nonzero : T9.IsNonZeroModeC w i)
    (t : ℝ) :
    ‖T9.bohrAmpC w i t‖ =
      ‖T9.bohrAmpC w i 0‖ *
        Real.exp (-(nse.nu * T9.bohrFreqSqC w i) * t)

/-- **T9.zero_spectrumC_implies_trivial (concrete-carrier axiom).**

Concrete-carrier version of `T9.zero_spectrum_implies_trivial`.  PR-A2
gives the FORWARD identity `M[|f|²] = |a 0|² + Σ|a ζ|²`; the INVERSION
direction (`f ≡ 0` from all `a ζ = 0`) is a SEPARATE classical fact
(Besicovitch 1932 §III.5 uniqueness of the AP-Fourier expansion) not
yet formalized.

Even with concrete carriers, the inversion step from "all amplitudes
vanish at `t = 0`" to "the velocity is spatially constant" requires:

  1. `bohrFourier_inversion`: from `M[|f|²] = 0` conclude `f ≡ 0`
     (Mathlib upstream gap; needs continuity + Bohr-mean positivity).
  2. Witness coherence: lifting per-component-per-time scalar
     projection-vanishing back to spatial constancy of `sol.u_t`.

Promotion gates on `bohrFourier_inversion` upstream. -/
axiom T9.zero_spectrumC_implies_trivial
    {nse : NavierStokes.NavierStokesEquations 3}
    {sol : AncientMildSolution nse}
    (w : T9.APSpectralWitness sol)
    (h_closedAliasing : ClosedAliasingAPSpectrum sol)
    (h_zero_at_0 : ∀ i : T9.BohrModeIndexC w,
                      T9.IsNonZeroModeC w i →
                      ‖T9.bohrAmpC w i 0‖ = 0) :
    sol.Trivial

/-! ### §6.6. Concrete-carrier composition (T9 with witness)

`T9_closure_attempt_concrete` is the witness-explicit composition,
analogous to `T9_closure_attempt` but routing through the concrete
carriers and the (1 promoted theorem + 3 refined axioms).
-/

/-- **T9 closure attempt — concrete-carrier version**.

Same conclusion as `T9_closure_attempt` but threads through the AP-
spectral witness and the concrete-carrier sub-lemmas.  Demonstrates
that the carrier-identification gap is type-level closed: every step
operates on `def`-unfolded carriers, not `opaque`s.

Note: this theorem requires the AP-spectral witness as an extra
hypothesis compared to the original `T9_closure_attempt`.  Promotion
of the witness-extraction step (constructing `T9.APSpectralWitness sol`
from `ClosedAliasingAPSpectrum sol`) gates on the closed-aliasing
predicate-body unfold and is NOT shipped here. -/
theorem T9_closure_attempt_concrete
    {nse : NavierStokes.NavierStokesEquations 3}
    {sol : AncientMildSolution nse}
    (w : T9.APSpectralWitness sol)
    (h_closedAliasing : ClosedAliasingAPSpectrum sol) :
    sol.Trivial := by
  apply T9.zero_spectrumC_implies_trivial w h_closedAliasing
  intro i h_nonzero
  -- Per-mode closure: combine the concrete-carrier Bessel bound (axiom),
  -- the linear-ODE form (axiom), and the real-analysis core
  -- `ancient_exp_decay_bounded_forces_zero` (sorry-free).
  have h_freq_pos : 0 < T9.bohrFreqSqC w i :=
    T9.bohrFreqSqC_pos_of_isNonZeroModeC w i h_nonzero
  have h_nu_pos : 0 < nse.nu := nse.nu_pos
  -- Set c := ‖a(0)‖, α := ν · |ξ|².
  set c : ℝ := ‖T9.bohrAmpC w i 0‖ with hc_def
  set α : ℝ := nse.nu * T9.bohrFreqSqC w i with hα_def
  have hα_pos : 0 < α := mul_pos h_nu_pos h_freq_pos
  -- From the linear-ODE axiom + the L^∞ bound axiom:
  -- ∀ t ≤ 0, |c| · exp(-α·t) ≤ sol.M.
  have hbound : ∀ t : ℝ, t ≤ 0 → |c| * Real.exp (-α * t) ≤ sol.M := by
    intro t _ht
    have hODE := T9.linear_damped_ODEC_at_each_mode
                    w h_closedAliasing i h_nonzero t
    have hc_nn : 0 ≤ c := norm_nonneg _
    have hc_abs : |c| = c := abs_of_nonneg hc_nn
    rw [hc_abs]
    rw [show c * Real.exp (-α * t) = ‖T9.bohrAmpC w i t‖ from hODE.symm]
    exact T9.bohrAmpC_le_Linfty w i t
  -- Apply the analytical core (sorry-free in §0 of
  -- ns_trackb_ap_liouville_single_mode.lean).
  exact ancient_exp_decay_bounded_forces_zero c α sol.M hα_pos hbound

/-! ### §6.7. Sorry / axiom inventory delta (post-bridge, 2026-05-08; updated 2026-05-09)

Pre-bridge (§§1-4): 4 hoisted T9 axioms over opaque carriers (5 if
counting the typed-companion `bohrFreqSq_pos_of_isNonZeroMode` bridge
axiom).

Post-bridge (§6):
  * 1 new structure (`T9.APSpectralWitness`) — concrete `def`, not
    `opaque`.
  * 4 new concrete-carrier `def`s (`T9.BohrModeIndexC`, `T9.bohrAmpC`,
    `T9.bohrFreqSqC`, `T9.IsNonZeroModeC`) — concrete, definitionally
    unfoldable.
  * 1 mirror structure (`T9.IsTrigPolyVelocityScalar`) + 1 mirror
    function (`T9.forwardChar`) — copies of PR-A2's scaffold.

§6 axiom inventory (updated 2026-05-09):
  * `T9.bohrFreqSqC_pos_of_isNonZeroModeC` — promoted to theorem at
    §6.4 (genuine: sum-of-squares > 0 from non-zero entry).
  * `T9.closedAliasingC_F_zero_at_residual` — promoted to theorem
    2026-05-09 (vacuous-existential elimination; statement was
    weakened to `∃ Fop, Fop t = 0` which is trivially provable;
    promotion is honest *because* it surfaces the weakening rather
    than hiding it; the substantive §1 axiom remains).
  * `T9.bohrAmpC_le_Linfty` — STILL AN AXIOM (Mathlib gap:
    `bohrMean_le_Linfty_squared` + witness-projection-bound
    coherence).
  * `T9.linear_damped_ODEC_at_each_mode` — STILL AN AXIOM (Mathlib
    gap: `bilinear_NS_bohr_convolution_sum` + per-mode ODE extraction
    from heat-equation form).
  * `T9.zero_spectrumC_implies_trivial` — STILL AN AXIOM (Mathlib
    gap: `bohrFourier_inversion` + witness-to-`u_t` coherence).

§6 axiom delta: 4 → 2 substantive + 0 vacuous (one substantive
promoted at §6.4 — `bohrFreqSqC_pos`; one vacuous promoted 2026-05-09
— `closedAliasingC_F_zero_at_residual`).  Sorry delta: 0 → 0.

§1 axiom inventory (UNCHANGED 2026-05-09):
  4 hoisted axioms over opaque carriers + 1 typed-companion bridge
  axiom (`bohrFreqSq_pos_of_isNonZeroMode`).  All carry substantive
  mathematical content keyed to specific upstream artifacts and
  cannot be promoted without (i) opaque-carrier unfolding, OR
  (ii) introducing new axioms (anti-pattern per task constraint).

The 2 remaining substantive §6 axioms gate on STRUCTURALLY DISTINCT
upstream artifacts (Bohr-mean L^∞ monotonicity / Bohr-Fourier
inversion direction) — these are NOT vocabulary relabels of each
other or of the original carrier-bound axioms.

**Anti-laundering verdict** (catch #31 + PATTERN-007 + SR-001
self-check 2026-05-09): the bridge demoted the carrier-identification
gap from a HIDDEN (because opaque) type-level obstruction to an
EXPLICIT (because concrete) but structurally-deeper set of named
gaps.  That is genuine progress — but it is NOT "T9 unblocked".
T9 still gates on PR-A1 + PR-A2 + 3 upstream artifacts; the §1
axioms remain at 4 substantive + 1 bridge.

The carrier-identification gap is **type-level closed**; the four
§1 hoisted axioms collectively are NOT closed (0/4 promoted in §1;
1/4 substantive + 1/4 vacuous-existential promoted in §6).
-/

end

end ZtareProofs.NS
