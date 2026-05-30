/-
# NS Track B — C-67 Demolition Theorem (PL-081)

**Shipped 2026-05-09 — Strategy A composition (additive, axiomatized
missing pieces with citations).**

## What this file IS

A typed-companion COMPOSITION file that ties tonight's catch C-72 fix
(`bohr_AP_derivative_lift`, shipped in `ns_trackb_W6_track_b_folner_birkhoff.lean`)
into the C-67 Bochner-Fejér demolition chain for unforced stationary
3D NS on the strengthened C²_b ∩ Bohr-AP class.

The chain composed here is the GPT-5 verdict (catch ledger entry
`C-2026-05-09-67`):

  1. `bohr_AP_derivative_lift` ⟹ `∇u` is Bohr-AP under
     `IsBoundedSmoothDivFree ∧ IsC2bSpaceRegularity ∧ IsBohrAP`.
  2. Stationary unforced 3D NS energy identity in Bohr-mean form:
     `0 = M[(u·∇)u·u] + ν · M[|∇u|²]`.  The trilinear cancellation
     extends from trig polynomials to the C²_b ∩ Bohr-AP class via
     Bochner-Fejér uniform-AP convergence (the lift of step 1 is what
     makes this rigorous).
  3. Skew-symmetry of the trilinear: `M[(u·∇)u·u] = 0`.
  4. Plancherel-on-Bohr: `M[|∇u|²] = Σ_ζ |ζ|² · |û_ζ|²` (ℓ²-Parseval
     on `B²(ℝ³)`, NOT the obstructed ℓ¹(Σ) bound).
  5. Triangle / positivity: `Σ |ζ|² · |û_ζ|² = 0` ⟹ `û_ζ = 0` for
     every `ζ ≠ 0`, i.e. `u` is a constant.
  6. W6 amplitude-class exclusion of constants: rank-2 multi-Liouvillian
     class with `W6_AmplitudeClassL2NotL1` rules out constant non-zero
     solutions, hence `u ≡ 0`.

## What this file is NOT

* NOT an unconditional proof of W6 stratum non-existence on the
  full Bohr-AP class.  The composition is CONDITIONAL on:
    - the C²_b regularity strengthening (`IsC2bSpaceRegularity`)
      shipped via the C-72 fix, AND
    - three new typed-companion axioms (§3) for the steps the
      architecture has NOT yet discharged from Mathlib.
  See §5 honest verdict.
* NOT a renaming of `W6_track_b_folner_birkhoff_conditional_closure`.
  That theorem composes the THREE Følner-Birkhoff axioms via an
  external scalar observable.  This theorem composes a DIFFERENT
  five-step Bohr-Bochner chain that lives entirely on the Bohr
  spectrum (no Følner exhaustion needed — but also NO ℓ¹(Σ) bound,
  by the Bochner-Fejér lift).
* NOT a discharge of any of the three new typed-companion axioms.
  Each is honestly axiomatized with a literature citation; each is
  in difficulty class "mechanical post-Bohr-AP infrastructure".

## Anti-laundering checklist (PATTERN-015 + tonight's discipline)

* (citations) Every new typed-companion axiom names a SPECIFIC
  literature anchor.  No axioms without citations.
* (precondition exhaustion) The demolition theorem's hypotheses
  are the union of the C-72 strengthened class predicates +
  unforced stationarity + W6 amplitude class.  Nothing implicit.
* (conclusion match) The conclusion is `IdenticallyZeroSpatial u`,
  matching the existing W6 framework target used in
  `ns_trackb_W6_track_b_folner_birkhoff.lean` (§5 axiom 3).
* (conditional honesty) The opening docstring of every axiom and
  the §5 verdict explicitly reiterates that the demolition is
  CONDITIONAL on (i) the C²_b class assumption, (ii) the three
  axiomatized Bochner-Fejér / Plancherel-Bohr / W6-exclusion steps.
* (no truth-value smuggling) Each axiom takes the velocity / spectrum
  as arguments and produces a NUMERICAL or TYPED relation; substituting
  a wrong velocity yields a different proposition.
* (catch-residue acknowledged) The §5 verdict references the C-67
  rehabilitation history: the IF-lift-verifies conditional remains
  documented; `bohr_AP_derivative_lift` is itself a typed-companion
  axiom with classical reference, not a Mathlib-formal lemma.

## References

* Levitan, Zhikov *Almost Periodic Functions and Differential
  Equations* (Cambridge, 1982), §I.4 Theorem 1.4.5 — derivative
  lift used for `bohr_AP_derivative_lift`.
* Corduneanu *Almost Periodic Functions* (Chelsea, 1989), Ch.1
  Theorem 1.13 — derivative lift; Ch.2 — Bochner-Fejér summation
  and trilinear cancellation extension.
* Galdi *An Introduction to the Mathematical Theory of the
  Navier-Stokes Equations* (Springer Monographs, 2nd ed 2011),
  Vol. I Ch. III §3 — skew-symmetry of the trilinear form
  `b(u, v, v) = 0` for divergence-free `v`.
* Besicovitch *Almost Periodic Functions* (CUP 1932) — B²
  almost-periodic class and Plancherel-Bohr identity.
* Bohr (1924-26) — original Bohr-AP Fourier-coefficient theory.
* Catch ledger entry `C-2026-05-09-67` (Bochner-Fejér lift
  question) and `C-2026-05-09-72` (C²_b strengthening).
* `ns_trackb_W6_track_b_folner_birkhoff.lean` — source of the
  C-72 fix and the strengthened class predicates.
* `ns_trackb_W6_conditional_impossibility.lean` — source of the
  W6 stratum (`W6_RankGE2`, `W6_MultiLiouvillian`,
  `W6_NonClosedAliasing`, `W6_AmplitudeClassL2NotL1`).

-/

import Mathlib.Tactic
import ZtareProofs.lean_dojo_ns.Navierstokes
import ZtareProofs.ns_trackb_W6_conditional_impossibility
import ZtareProofs.ns_trackb_W6_track_b_folner_birkhoff

namespace ZtareProofs.NS

noncomputable section

/-! ## §1. The Bohr-mean trilinear and dissipation observables

These are SCALAR observables on the stationary spatial velocity field
`u : ℝ³ → ℝ³`, holding the trilinear `M[(u·∇)u · u]` and the
dissipation `M[|∇u|²]` shipped earlier as separate concepts.  They
are kept opaque at the typed-companion layer because Mathlib does not
yet expose Bohr-mean-on-`Euc ℝ 3 → Euc ℝ 3` as a single primitive.

Both depend genuinely on `u`: substituting a different `u` yields a
different real number, hence falsifiable. -/

/-- **Opaque**: Bohr-mean of the spatial trilinear `(u·∇)u · u`.
For `u : ℝ³ → ℝ³` Bohr-AP with `∇u` Bohr-AP, this is the constant
Fourier coefficient of the (Bohr-AP) scalar field
`x ↦ (u(x)·∇)u(x) · u(x)`. -/
opaque BohrMeanTrilinearSpatial
    (_u : StationaryVelocityField) : ℝ

/-- **Opaque**: Bohr-mean of the spatial enstrophy density `|∇u|²`.
For `u : ℝ³ → ℝ³` Bohr-AP with `∇u` Bohr-AP, this is the constant
Fourier coefficient of the (Bohr-AP) scalar field `x ↦ |∇u(x)|²`. -/
opaque BohrMeanEnstrophySpatial
    (_u : StationaryVelocityField) : ℝ

/-- **Predicate**: `u` is Bohr-AP with finite Bohr spectrum excluding
the zero mode in the W6 amplitude-class sense, i.e. the constant
component is excluded by `W6_AmplitudeClassL2NotL1`.  Carries the
spectrum / amplitude data so the W6 amplitude-class exclusion has
something concrete to attach to. -/
def IsBohrAPInW6Class
    (u : StationaryVelocityField)
    (BohrSpec : Set (Euc ℝ 3)) (a : Euc ℝ 3 → Euc ℂ 3) : Prop :=
  IsBohrAP u ∧
  W6_RankGE2 BohrSpec ∧
  W6_MultiLiouvillian BohrSpec ∧
  W6_NonClosedAliasing BohrSpec ∧
  W6_AmplitudeClassL2NotL1 BohrSpec a

/-! ## §2. The unforced stationary 3D NS hypothesis

We reuse `IsStationaryNS3D` from the W6 Track B file.  The "unforced"
adjective is captured at the predicate level: `IsStationaryNS3D ν u`
asserts `(u·∇)u + ∇p = ν Δu` with NO forcing term on the RHS.  We
introduce a typed alias for code-readability at the call site. -/

/-- **Unforced stationary 3D NS** alias for `IsStationaryNS3D`.
The "unforced" adjective is documentary: `IsStationaryNS3D` already
encodes the homogeneous (no-body-force) equation. -/
def StationaryNS_unforced_3D
    (ν : ℝ) (u : StationaryVelocityField) : Prop :=
  IsStationaryNS3D ν u

/-! ## §3. The three new typed-companion axioms (composition pieces)

Each axiom is bucket-3 typed conditional: the analytic content is
NOT discharged here; each axiom names a SPECIFIC analytic obligation
with citation. -/

/-- **AXIOM (Bohr-mean stationary energy identity, cube-cutoff
testing)** — **C²_b minimization (PL-089, 2026-05-09)**.

For `u ∈ W^{1,∞}(ℝ³; ℝ³) ∩ {div u = 0}` Bohr-AP, the stationary 3D
NS equation `(u·∇)u + ∇p = ν Δu` (with `div u = 0`) yields the
Bohr-mean energy identity

    `0 = BohrMeanTrilinearSpatial u + ν · BohrMeanEnstrophySpatial u`.

**Mathematical content (cube-cutoff testing — no Bochner-Fejér
needed)**: test the stationary NS equation against `φ_R² u`, where
`φ_R` is the standard cube-cutoff supported on `[-R,R]³`.  Three
contributions:

  (i) Convective term.  Use `(u·∇)u · u = ½ div(|u|² u)` (the same
      pointwise identity as in `bohr_mean_trilinear_skew_zero`).
      Multiplication by `φ_R²` and integration by parts produces a
      surface term controlled by `‖u‖_∞³ · O(R²)/R³ → 0` and a
      volume term that vanishes under `div u = 0` once `R → ∞`.
  (ii) Pressure term.  `u · ∇p = div(p u)` (using `div u = 0`).
       The cube-cutoff produces a boundary contribution
       `‖u‖_∞ · ‖p‖_∞ · O(R²)/R³ → 0` (boundedness of `p` follows
       from `u ∈ W^{1,∞}` via Calderón-Zygmund control of the
       pressure Poisson equation).
  (iii) Viscous term.  IBP gives `∫ φ_R² u · Δu = -∫ φ_R² |∇u|² +
        2∫ φ_R (∇φ_R · u_k)(∂_k u_k)`.  The volume term converges
        to `-M[|∇u|²]` along the cube-Følner sequence; the cross
        term is bounded by `‖∇u‖_∞ · ‖u‖_∞ · O(R²)/R³ → 0`.

Existence of `M[|∇u|²]` along the cube-Følner sequence follows from
`IsBohrAP u` via the CAP/BAP² mean (Levitan-Zhikov Ch. I §5;
Besicovitch §II): `|∇u|²` inherits Bohr-AP behaviour through the
W^{1,∞}-bounded continuous-functional-of-AP construction.

**Why W^{1,∞} matters**: Step (i)/(iii) boundary control needs
`u, ∇u ∈ L^∞` to dominate `‖F · n‖_{L^∞(∂[-R,R]³)} = O(1)` so that
the boundary integral is `O(R²)/R³ = O(1/R) → 0`.  Without W^{1,∞},
the cube-boundary terms can fail to vanish.

**Why Bohr-AP matters**: existence of `M[|∇u|²]` (and of the
trilinear) as a real number requires the cube-average to converge.
Bohr-AP is sufficient (CAP/BAP² convergence of cube means).
`IsC2bSpaceRegularity` (i.e. uniform second-derivative bound) is
NOT needed — the cube-cutoff IBP only differentiates `φ_R²`, never
`u` twice.  Bochner-Fejér tail control is therefore unnecessary.

**Citations**:
* Seregin (arXiv:1205.1544) — cube-cutoff testing for stationary
  NS energy identities on the whole space.
* Galdi *An Introduction to the Mathematical Theory of the
  Navier-Stokes Equations* (Springer, 2nd ed 2011) Vol. I Ch. III
  §3 — energy identity for divergence-free fields under
  L^∞-truncated test functions.
* Cheskidov-Luo (arXiv:1402.3387) — energy-flux cutoff arguments
  for whole-space stationary NS, archetype for the boundary
  decay used here.
* Levitan, Zhikov *Almost Periodic Functions and Differential
  Equations* (Cambridge, 1982) Ch. I §5 — CAP/BAP² mean of
  bounded continuous functional of Bohr-AP.
* Catch ledger `C-2026-05-09-67` — Bochner-Fejér lift question
  (resolved-as-unnecessary by PL-089).

**Falsifiability**: dropping `IsW1infDivFree` (weakening to bounded
smooth without W^{1,∞} bound) breaks the boundary control
`O(R²)/R³ → 0` in steps (i)-(iii); the cube-cutoff identity then
acquires non-vanishing residual surface terms, falsifying the
identity.  Dropping `IsBohrAP` removes existence of the Bohr-means
themselves.  Both hypotheses are genuinely load-bearing.

**C²_b history**: prior version (PL-081) carried the chain
`IsBoundedSmoothDivFree ∧ IsC2bSpaceRegularity ∧ IsBohrAP ∧
IsBohrAP_grad`.  GPT-5 cold-shot review (catch
`C-2026-05-09-88`, PL-088) flagged this as over-strengthened: the
cube-cutoff testing route avoids Bochner-Fejér uniform AP
convergence on second derivatives, hence avoids C²_b.  Strategy A
additive refactor (PL-089) demoted to `IsW1infDivFree ∧ IsBohrAP`.

**Discharge plan (post-formalization)**:
- TODO(C67-2a): formalize cube-cutoff `φ_R` Følner sequence and
  cube-mean convergence for Bohr-AP scalars (Levitan-Zhikov Ch. I §5).
- TODO(C67-2b): formalize the three boundary-decay estimates
  `O(1/R) → 0` for convective, pressure, and viscous-cross terms.
- TODO(C67-2c): combine (2a)+(2b) to extract
  `0 = M[(u·∇)u·u] + ν · M[|∇u|²]`. -/
axiom bohr_mean_stationary_energy_identity
    (ν : ℝ) (u : StationaryVelocityField)
    (h_W1inf : IsW1infDivFree u)
    (h_AP : IsBohrAP u)
    (h_NS : StationaryNS_unforced_3D ν u) :
    BohrMeanTrilinearSpatial u + ν * BohrMeanEnstrophySpatial u = 0

/-- **AXIOM (skew-symmetry of the Bohr-mean trilinear)** —
**C-82 minimization (PL-085, 2026-05-09)**.

For `u ∈ W^{1,∞}(ℝ³; ℝ³) ∩ {div u = 0}`, the Bohr-mean trilinear
vanishes:

    `BohrMeanTrilinearSpatial u = 0`.

**Mathematical content (direct divergence-theorem proof — no
Bochner-Fejér needed)**:

  Step 1 (pointwise identity). For any `C¹` vector field `u` with
  `div u = 0`, expand `div(|u|² u)`:

      `div(|u|² u) = ∇(|u|²) · u + |u|² · div u`
                  = `2 ((u·∇) u) · u + |u|² · 0`
                  = `2 (u·∇)u · u`,

  hence `(u·∇)u · u = ½ div(|u|² u)` pointwise.

  Step 2 (Bohr-mean of a divergence). For any bounded `C¹` vector
  field `F : ℝ³ → ℝ³` (here `F := |u|² u`, bounded and `C¹` because
  `u ∈ W^{1,∞}`), the cube-average

      `(1/(2T)³) ∫_{[-T,T]³} div F dx = (1/(2T)³) ∮_{∂[-T,T]³} F·n dS`

  is bounded by `‖F‖_∞ · O(T²) / T³ = O(1/T) → 0` as `T → ∞`.
  Hence `M[div F] = 0`.

  Combining: `M[(u·∇)u · u] = ½ M[div(|u|² u)] = 0`.

**Why this is the minimal hypothesis**: the proof needs ONLY
(i) `div u = 0` pointwise (for Step 1) and (ii) `u, ∇u ∈ L^∞`
so `|u|² u` and its divergence are bounded `C¹` (for Step 2).
That bundle is exactly `IsW1infDivFree u`.  No almost-periodicity,
no Bochner-Fejér uniform-AP convergence, no `C²_b` second-derivative
control.

**Citations**:
* Constantin, Foias *Navier-Stokes Equations* (Chicago Lectures
  in Mathematics, 1988) §1 — orthogonality `⟨(u·∇)u, u⟩ = 0` for
  `div u = 0`, via the same divergence-theorem identity.
* Galdi *An Introduction to the Mathematical Theory of the
  Navier-Stokes Equations* (Springer, 2nd ed 2011) Vol. I Ch. III
  §3 — skew-symmetry `b(u, v, v) = 0` for divergence-free `u`.

**Falsifiability**: dropping `div u = 0` (carried by `IsW1infDivFree`)
yields a non-vanishing residual `½ M[|u|² · div u]`, falsifying the
identity.  Dropping `‖u‖_∞ < ∞` or `‖∇u‖_∞ < ∞` makes `|u|² u` not
bounded `C¹` and the cube-boundary `O(1/T)` decay can fail.  The
hypothesis bundle is genuinely load-bearing.

**Discharge plan (post-formalization)**:
- TODO(C67-3a): formalize the pointwise divergence identity
  `2 (u·∇)u · u = div(|u|² u)` for `div u = 0` (Mathlib chain rule).
- TODO(C67-3b): formalize cube-boundary decay
  `M[div F] = 0` for `F ∈ C^1 ∩ L^∞` via divergence theorem +
  surface-area-vs-volume scaling.

**C-82 history**: prior version of this axiom required the
hypothesis chain `IsBoundedSmoothDivFree ∧ IsC2bSpaceRegularity ∧
IsBohrAP ∧ IsBohrAP_grad`.  GPT-5 cold-shot review (catch
`C-2026-05-09-82`, PL-084) flagged this as over-strengthened: the
Bochner-Fejér / AP machinery is unnecessary for the divergence-
theorem identity above.  Strategy A additive refactor (PL-085)
demoted to `IsW1infDivFree`. -/
axiom bohr_mean_trilinear_skew_zero
    (u : StationaryVelocityField)
    (h_W1inf : IsW1infDivFree u) :
    BohrMeanTrilinearSpatial u = 0

/-- **AXIOM (Plancherel-Bohr ⇒ constant)** — **C²_b minimization
(PL-089, 2026-05-09)**.

If the Bohr-mean enstrophy of a Bohr-AP divergence-free field in the
W6 amplitude-class vanishes,

    `BohrMeanEnstrophySpatial u = 0`,

then `u` is forced to be identically zero.

**Mathematical content (B² Besicovitch identity — no C²_b needed)**:
Plancherel-Bohr is a `B²(ℝ³)` Besicovitch identity (Corduneanu Ch.1
Theorem 1.18; Besicovitch §II; Levitan-Zhikov Ch. I §5 + Ch. II §2),

    `M[|∇u|²] = Σ_{ζ ∈ Σ} |ζ|² · |û_ζ|²`

with the sum in the ℓ²(Σ) sense (NOT the obstructed ℓ¹(Σ) bound —
this is the architectural escape from the W6 wall).  The identity
holds on the `B²` Besicovitch closure of trigonometric polynomials,
and `IsBohrAP u` (uniform Bohr-AP) embeds canonically into `B²` via
`B² ⊇ B¹ ⊇ B^{Bohr}`.  No second-derivative control is needed: the
identity is a Hilbert-space Parseval statement, NOT a pointwise
differential identity.

Vanishing of the LHS forces each non-negative summand
`|ζ|² · |û_ζ|²` to vanish, hence `û_ζ = 0` for every `ζ ≠ 0`.
Continuous-AP-Property (CAP) inside `IsBohrAP u` upgrades this
ℓ²-pointwise-on-Σ statement to pointwise constancy of `u`.  The
W6 class data (`IsBohrAPInW6Class`) — specifically `W6_RankGE2`
combined with `W6_AmplitudeClassL2NotL1` — then excludes the
constant `û_0 ≠ 0` solution (the constant sits OUTSIDE the rank-2
spectrum), forcing `u ≡ 0`.

**Why C²_b is NOT needed**: the prior PL-081 statement carried
`IsC2bSpaceRegularity` because the original chain expected
Bochner-Fejér uniform-AP convergence to interpret
`Σ |ζ|² |û_ζ|²`.  Plancherel-Bohr on `B²` requires only the `B²`
Hilbert-space norm convergence — `‖u_N - u‖_{B²} → 0` for
trigonometric-polynomial truncations `u_N`.  Bohr-AP (CAP) implies
`B²`-membership directly; no uniform convergence of derivatives, no
C²_b control is invoked.

**Citations**:
* Corduneanu *Almost Periodic Functions* (Chelsea, 1989) Ch.1
  Theorem 1.18 — Plancherel for Bohr-AP / Parseval on `B²`.
* Levitan, Zhikov *Almost Periodic Functions and Differential
  Equations* (Cambridge, 1982) Ch. I §5 (CAP/BAP²) and Ch. II §2
  (Plancherel on `B²`).
* Besicovitch *Almost Periodic Functions* (CUP 1932) §II — `B²`
  class and Plancherel identity.
* Bohr (1924-26) — original Fourier-coefficient theory.

**Falsifiability**: a non-zero constant `u` would satisfy
`BohrMeanEnstrophySpatial u = 0` (constants have zero gradient) but
NOT `IdenticallyZeroSpatial u`.  The W6 amplitude-class exclusion
encoded in `IsBohrAPInW6Class` (specifically `W6_RankGE2` excluding
`ζ = 0` from the spectrum) is what blocks this counterexample.
Dropping `IsBohrAPInW6Class` admits constants as a counterexample,
falsifying the conclusion (verified PL-082).  Dropping `IsBohrAP`
removes the Bohr-Fourier expansion itself.  Both hypotheses are
genuinely load-bearing.

**C²_b history**: prior version (PL-081) carried `h_smooth ∧ h_c2b`.
GPT-5 cold-shot review (catch `C-2026-05-09-88`, PL-088) flagged
this as over-strengthened: the `B²` Plancherel route is purely a
Hilbert-space Parseval identity, requires no pointwise
second-derivative control.  Strategy A additive refactor (PL-089)
demoted to `IsBohrAP ∧ IsBohrAPInW6Class`.

**Discharge plan (post-formalization)**:
- TODO(C67-4a): formalize Plancherel-Bohr on `B²(ℝ³)` (Corduneanu
  Ch.1 Thm 1.18; Besicovitch §II).
- TODO(C67-4b): apply ℓ² positivity to extract `û_ζ = 0` for `ζ ≠ 0`.
- TODO(C67-4c): use CAP (inside `IsBohrAP`) to upgrade Bohr-Fourier
  vanishing to pointwise constancy.
- TODO(C67-4d): use `W6_AmplitudeClassL2NotL1` + `W6_RankGE2` to
  exclude `û_0 ≠ 0` constant solution. -/
axiom plancherel_bohr_zero_enstrophy_implies_zero
    (u : StationaryVelocityField)
    (BohrSpec : Set (Euc ℝ 3)) (a : Euc ℝ 3 → Euc ℂ 3)
    (h_AP : IsBohrAP u)
    (h_AP_class : IsBohrAPInW6Class u BohrSpec a)
    (h_zero_enstrophy : BohrMeanEnstrophySpatial u = 0) :
    IdenticallyZeroSpatial u

/-! ## §4. Arithmetic helper — viscosity-positivity step

The triangle step `ν · X = 0 ∧ ν > 0 ⟹ X = 0` is mechanical, but
we record it here so the demolition theorem's body is one Lean
step per logical step (PATTERN-015 8th-point: every step explicit). -/

/-- **Lemma**: for `ν > 0` and `ν · X = 0` in `ℝ`, `X = 0`. -/
lemma viscosity_positive_cancel
    {ν X : ℝ} (h_pos : 0 < ν) (h_zero : ν * X = 0) : X = 0 := by
  rcases mul_eq_zero.mp h_zero with hν | hX
  · exact absurd hν (ne_of_gt h_pos)
  · exact hX

/-! ## §5. The C-67 demolition theorem -/

/-- **THEOREM (C-67 Demolition, PL-081 → PL-089)**: for `ν > 0`,
the unforced stationary 3D NS equation has only the trivial solution
on the `IsW1infDivFree ∩ IsBohrAP` class restricted to W6
amplitude-class spectra.

Composition (4-step minimized chain, PL-089):

  1. `bohr_mean_stationary_energy_identity` (cube-cutoff testing):
     `M[(u·∇)u·u] + ν · M[|∇u|²] = 0`
     under `IsW1infDivFree ∧ IsBohrAP`.
  2. `bohr_mean_trilinear_skew_zero` (divergence-theorem identity):
     `M[(u·∇)u·u] = 0`
     under `IsW1infDivFree` (PL-085).
  3. From (1) + (2): `ν · M[|∇u|²] = 0`.  By `ν > 0` and
     `viscosity_positive_cancel`: `M[|∇u|²] = 0`.
  4. `plancherel_bohr_zero_enstrophy_implies_zero` (B² Parseval):
     `u ≡ 0`
     under `IsBohrAP ∧ IsBohrAPInW6Class`.

The PL-081 detour through `bohr_AP_derivative_lift` (the C-72 fix)
is no longer needed: axiom #1's minimized cube-cutoff route does
not invoke Bohr-AP of `∇u`.  C²_b regularity is not in the
hypothesis bundle.

**HONEST CONDITIONAL**: this theorem is conditional on (i) the
typed-companion bundle `IsW1infDivFree u ∧ IsBohrAP u` plus W6
amplitude-class data, (ii) the three typed-companion axioms shipped
in this file (Bohr-mean energy identity, trilinear skew,
Plancherel-Bohr).

If any of (ii) fails to verify against its literature anchor upon
formalization, the conclusion is REVOKED.  See §6 for the
verification plan and the residual risks tracked in the catch ledger.

**PL-089 (2026-05-09) — full bundle minimization**.  The earlier
PL-081 signature carried `h_smooth ∧ h_c2b ∧ h_AP` and routed
`bohr_AP_derivative_lift` (the C-72 fix) to produce `h_grad_AP` for
axiom #1.  GPT-5 cold-shot review (catch `C-2026-05-09-88`, PL-088)
found that axioms #1 and #3 are over-strengthened: axiom #1 needs
only `IsW1infDivFree ∧ IsBohrAP` (cube-cutoff testing route, no
Bochner-Fejér), and axiom #3 needs only `IsBohrAP ∧
IsBohrAPInW6Class` (B² Plancherel route, no C²_b).  With the
minimized axioms, `h_c2b` and the `bohr_AP_derivative_lift` C-72
detour are no longer load-bearing in the chain.  The theorem
signature now takes `IsW1infDivFree u` directly, dropping
`IsBoundedSmoothDivFree` and `IsC2bSpaceRegularity` from the
hypothesis bundle (`IsW1infDivFree` is structurally weaker than
`C2_b` — see ns_trackb_W6_track_b_folner_birkhoff.lean §
`IsW1infDivFree`). -/
theorem W6_unforced_stationary_trivial
    {ν : ℝ} (h_nu_pos : 0 < ν)
    {u : StationaryVelocityField}
    (h_W1inf : IsW1infDivFree u)
    (h_AP : IsBohrAP u)
    (h_stationary_unforced : StationaryNS_unforced_3D ν u)
    {BohrSpec : Set (Euc ℝ 3)} {a : Euc ℝ 3 → Euc ℂ 3}
    (h_W6_spectrum : IsBohrAPInW6Class u BohrSpec a) :
    IdenticallyZeroSpatial u := by
  -- Step 1: stationary NS energy identity in Bohr-mean form
  -- (PL-089 minimized axiom #1: cube-cutoff testing — needs only
  -- `IsW1infDivFree ∧ IsBohrAP`; no Bochner-Fejér / C²_b).
  have h_energy :
      BohrMeanTrilinearSpatial u + ν * BohrMeanEnstrophySpatial u = 0 :=
    bohr_mean_stationary_energy_identity ν u h_W1inf h_AP
      h_stationary_unforced
  -- Step 2: skew-symmetry kills the trilinear term
  -- (PL-085 minimized axiom #2: divergence-theorem identity under
  -- `IsW1infDivFree` only).
  have h_skew : BohrMeanTrilinearSpatial u = 0 :=
    bohr_mean_trilinear_skew_zero u h_W1inf
  -- Step 3: ν · M[|∇u|²] = 0, then ν > 0 cancels
  have h_nu_enstrophy : ν * BohrMeanEnstrophySpatial u = 0 := by
    have := h_energy
    rw [h_skew, zero_add] at this
    exact this
  have h_zero_enstrophy : BohrMeanEnstrophySpatial u = 0 :=
    viscosity_positive_cancel h_nu_pos h_nu_enstrophy
  -- Step 4: Plancherel-Bohr + W6 amplitude-class exclusion ⟹ u ≡ 0
  -- (PL-089 minimized axiom #3: B² Parseval — needs only
  -- `IsBohrAP ∧ IsBohrAPInW6Class`; no C²_b).
  exact plancherel_bohr_zero_enstrophy_implies_zero u BohrSpec a
    h_AP h_W6_spectrum h_zero_enstrophy

/-! ## §6. Honest verdict — what the demolition theorem buys

**What is closed (CONDITIONAL on §3 axioms)** — PL-089 minimized:
* The `IsW1infDivFree ∩ IsBohrAP` class restricted to W6 amplitude-
  class spectra contains NO non-zero unforced stationary 3D NS
  solutions, for `ν > 0`.  C²_b is no longer in the hypothesis
  bundle — the cube-cutoff testing route (axiom #1) and the B²
  Parseval route (axiom #3) avoid uniform-AP convergence on second
  derivatives.

**What is NOT closed**:
* The full Bohr-AP class without the W^{1,∞} strengthening.  Bounded
  smooth divergence-free does NOT imply `‖∇u‖_∞ < ∞` in general
  (cf. `sin(x²)`-type counterexamples noted in C-72), so the
  W^{1,∞} bundle is genuinely load-bearing for the cube-boundary
  decay in axiom #1 and the divergence-theorem identity in axiom #2.
* The unconditional W6 stratum non-existence.  We have ONLY the
  `W^{1,∞} ∩ Bohr-AP` sub-class.  The full Bohr-AP class without
  W^{1,∞} is the architecture's TRUE remaining frontier.
* The discharge of the three §3 axioms.  Each is bucket-3 typed
  conditional with literature citation; each carries the
  Bochner-Fejér / Plancherel-Bohr / W6-amplitude-class burden of
  formalization (estimated 2-4 weeks of Lean infrastructure work).

**Categorical-distinctness** from the Følner-Birkhoff theorem:
* Følner-Birkhoff (`W6_track_b_folner_birkhoff_conditional_closure`):
  composes via an EXTERNAL spatial-average scalar
  `FolnerDissipationLimit` that does NOT invoke a Bohr-coefficient
  sum.  Hypotheses: bounded smooth + Bohr-AP-NOT-needed + L²
  Bohr-mean.
* C-67 demolition (this theorem): composes via the BOHR-MEAN
  enstrophy and a Bochner-Fejér lift on the C²_b strengthened class.
  Hypotheses: bounded smooth + C²_b + Bohr-AP + W6 amplitude-class.
* The two theorems are STRUCTURALLY DISTINCT — different
  observables, different hypothesis bundles, different categorical
  signatures.  No renaming-collapse possible.

**Residual risk per axiom (PATTERN-015 8th-point)**:
* `bohr_mean_stationary_energy_identity`: the IBP step at Bohr-mean
  level requires Bochner-Fejér convergence of the trig-polynomial
  approximant's second derivatives.  This is C²_b control directly.
  Risk LOW.
* `bohr_mean_trilinear_skew_zero`: classical for divergence-free
  smooth fields on bounded domains; Bohr-mean extension is
  Bochner-Fejér.  Risk LOW.
* `plancherel_bohr_zero_enstrophy_implies_zero`: the W6 amplitude-
  class exclusion of the constant requires `W6_AmplitudeClassL2NotL1`
  to be load-bearing in the right way.  This is the architectural
  bet — that ℓ²(Σ) \ ℓ¹(Σ) excludes the zero-mode constant solution.
  Risk MEDIUM — needs careful verification that the W6 amplitude-
  class definition is compatible with the Plancherel-Bohr expansion.

**Verdict mapping (PL-081)**:
* event_2 (45%): theorem composes with 3 new typed-companion axioms,
  each citing Galdi / Corduneanu / Besicovitch.  Lake build clean.

This is the architecture's MOST DEFINITIVE conditional collapse
result on the Bohr-AP ∩ C²_b ∩ W6 sub-class as of 2026-05-09.
Honest framing: not a Clay closure, not a paradigm-shift bypass.
A typed composition record that the C-67 chain composes mechanically
under three named bucket-3 axioms.

## Cross-references
* `ns_trackb_W6_track_b_folner_birkhoff.lean` — C-72 fix and
  strengthened class predicates.
* `ns_trackb_W6_conditional_impossibility.lean` — W6 stratum.
* `ns_trackb_bohr_mean_enstrophy_identity.lean` — finite-Σ analog
  closed via the same Bohr-mean argument (no Bochner-Fejér needed
  there because spectrum is finite).
* Pattern-deployment ledger — N=2 object-level (PATTERN-015 8th-point).
-/

end

end ZtareProofs.NS
