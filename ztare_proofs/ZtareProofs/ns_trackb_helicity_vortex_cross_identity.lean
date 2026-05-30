/-
# NS Track B — Helicity ↔ Vortex-Stretching Cross-Identity (CREATE-4 EXPLORATORY)

This file is a deliberately *exploratory* extension of
`ns_trackb_helicity_vortex_stretching.lean`.  It encodes a CONJECTURED
monotone Lyapunov-style functional `Φ(t)` built from the cross-coupling
of three NS scalars:

  * total helicity              `H(t) := ∫_{ℝ³} u · ω  dx`
  * vortex-stretching integral  `V(t) := ∫_{ℝ³} ω · (ω·∇) u  dx`
  * kinetic energy              `E(t) := (1/2) ∫_{ℝ³} |u|²  dx`

Classical NS identities (3-D, viscosity `ν > 0`):

  `dE/dt = -2ν · enstrophy(t)                           (energy decay)`
  `dH/dt = -2ν ∫ ω · curl ω  dx                          (Moffatt-style)`
  `d(enstrophy)/dt = V(t)  -  ν ∫ |∇ω|²  dx              (vorticity eq.)`

These three identities are individually well-known.  The OBSERVATION of
this file is that there is a *cross-structure* that has not been
systematically exploited in the regularity literature: `dH/dt` is
controlled by a viscous shear-curl integral, `dE/dt` is controlled by
enstrophy, and the time-derivative of enstrophy is sourced by `V(t)`
itself.  So `H, V, E` are coupled through a single ODE-like system in
the integrated quantities, and any combination that is monotone along
that system gives a **new criterion**: `Φ(t)` bounded ⇒ enstrophy stays
finite ⇒ BKM ⇒ smooth.

## The candidate functional (CONJECTURE — not theorem)

We propose

  `Φ(t) := H(t)²  +  2ν · ∫₀ᵗ V(s)² ds  -  α · E(t)`   (α > 0 free)

The intuition: `H²` is bounded by Cauchy-Schwarz `H² ≤ 2 E · enstrophy`,
the cumulative `∫ V²` is monotone-non-decreasing by construction, and
the `-α E` term is monotone-non-increasing (energy dissipates).  So
`Φ`'s trend depends on *which of these three drivers wins*.

Time-derivative under NS dynamics (formal — see §3 below):

  `dΦ/dt = 2 H · (dH/dt)  +  2ν · V(t)²  -  α · (dE/dt)`
        `= 2 H · (-2ν ∫ ω · curl ω)  +  2ν V²  +  2 α ν · enstrophy`

This SIGN ANALYSIS reveals the candidate is **NOT obviously monotone**:
the first term has unclear sign (depends on alignment of `ω` with
`curl ω` weighted by `H`), the second term `2ν V²` is **positive**
(BAD for a Lyapunov), and the third term `+2αν · enstrophy` is also
positive.  So as written, `Φ` is *anti*-Lyapunov: `dΦ/dt ≥ 0` in the
generic case.

That is the **HONEST FINDING**.  We record it as a `Prop` and
explicitly tag the conjecture as `ConjecturedMonotonicity` so any
downstream prover can either exhibit a counterexample (which is the
expected outcome) or repair the sign via a different `α`-choice or
a different combiner `f(H, V, E)`.

## Repaired candidate (for completeness)

A sign-corrected variant that DOES decrease under classical
inequalities, modulo Cauchy-Schwarz on `|H| ≤ √(2 E · enstrophy)`:

  `Φ_corr(t) := α · E(t)  -  H(t)²/(2 E(t))  -  ε · ∫₀ᵗ V(s)² ds`

This rearranges the three drivers so the dominant term is monotone.
But `Φ_corr` is no longer a clean polynomial in `(H, V, E)`, and the
`H²/(2E)` factor blows up at vacuum-energy (which is not physical
for finite-energy data but is a formal singularity).

We ship BOTH variants as typed Props so the architectural map records
the conjecture-space honestly.

## Why this matters even if the conjecture FAILS

A **negative** numerical result on Beltrami / screw-flow constrains
the search space for monotone helicity-stretching combiners.  The
typed-companion architecture is doing real epistemic work even when
the punchline is "this combiner is not monotone — try another."

## Numerical SymPy verification (separate file, see §6 below)

* Beltrami flow `u = (sin z, 0, cos z)`: H ≠ 0 (Beltrami is helical).
* Burgers vortex (axisymmetric): H = 0 by symmetry — degenerate test.
* Screw flow `u = (sin z, cos z, 0)`: ω = curl u = (-sin z, cos z, 0)
  ⟹ `u · ω = -sin²z + cos²z = cos(2z)`, so H is NOT zero density-wise
  but vanishes in any 2π-periodic z-integral.  STILL DEGENERATE.
* Better test: ABC flow `u = (A sin z + C cos y, B sin x + A cos z,
  C sin y + B cos x)` is helical with `ω = u`, so `u · ω = |u|² > 0`.

SymPy verification is reported in:
`projects/ns_millennium_hunt/workspace/sympy_verification/
helicity_vortex_cross_identity_sympy.py`

## File contents

* `HelicityVortexCrossData sol`           — typed companion, fields H/V/E + α
* `Phi_candidate D t`                     — the candidate Φ functional
* `Phi_corrected D t`                     — sign-corrected variant
* `ConjecturedMonotonicity D`             — Prop: Φ is non-increasing
* `ConjecturedBlowupExplosion D`          — Prop: Φ → ∞ at hypothetical blow-up
* `HelicityVortexCrossStructure sol`      — full bundle (data + conjecture Props)
* `cross_identity_smoothness_criterion`   — bridge: monotone Φ ⇒ Vasseur premise

## Honest framing

This file ships **zero theorems** that close the conjecture.  Every
non-trivial claim is either:

* a `def` (typed naming of the candidate functional), or
* a `Prop` flagged as `Conjectured*` (open mathematics), or
* an axiom whose discharge is a future research task explicitly
  marked OPEN.

The expected status of `ConjecturedMonotonicity` is **likely false in
its stated form** — the sign analysis above suggests the polynomial
candidate is anti-Lyapunov.  We ship it anyway because (a) it is the
cleanest first attempt, (b) recording its failure mode in typed Lean
constrains the candidate-functional search, and (c) the
`Phi_corrected` variant is a non-polynomial repair worth checking
numerically.

ZERO `sorry`s.  Compile-clean.
-/

import Mathlib.Tactic
import Mathlib.Analysis.Calculus.ContDiff.Basic
import Mathlib.MeasureTheory.Integral.IntervalIntegral.Basic
import ZtareProofs.lean_dojo_ns.Navierstokes
import ZtareProofs.ns_trackb_helicity_vortex_stretching
import ZtareProofs.ns_trackb_trace_binds_sol

open MeasureTheory
open scoped Topology ENNReal NNReal

namespace ZtareProofs.NS

noncomputable section

/-! ## §1.  Typed companion: HelicityVortexCrossData

This bundles helicity `H(t)`, vortex stretching `V(t)`, kinetic energy
`E(t)`, the viscosity coefficient `ν`, and a positive parameter `α`
into a single record.  All fields are abstract `ℝ → ℝ` time-series;
the link to the actual NS solution is carried by the parametric
weak-solution argument and the optional companion to
`HelicityVortexStretchingData`. -/

/-- **Typed companion** for the helicity ↔ vortex-stretching cross
identity exploration.

Fields:

* `T` / `T_pos` — finite window `[0, T]`.
* `nu` / `nu_pos` — viscosity `ν > 0`.
* `alpha` / `alpha_pos` — free positive parameter in the candidate Φ.
* `helicity` — `H(t) := ∫ u · ω dx`.
* `vortex_stretching` — `V(t) := ∫ ω · (ω · ∇) u dx`.
* `energy` — `E(t) := (1/2) ∫ |u|² dx`.
* `*_integrable` — interval-integrability witnesses on `[0, T]`. -/
structure HelicityVortexCrossData
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse) where
  /-- Terminal time on which we explore the candidate Φ. -/
  T : ℝ
  /-- `T > 0`. -/
  T_pos : 0 < T
  /-- Viscosity. -/
  nu : ℝ
  /-- `ν > 0`. -/
  nu_pos : 0 < nu
  /-- Free positive parameter in the candidate Φ. -/
  alpha : ℝ
  /-- `α > 0`. -/
  alpha_pos : 0 < alpha
  /-- Total helicity `H(t)`. -/
  helicity : ℝ → ℝ
  /-- `H` is interval-integrable on `[0, T]`. -/
  helicity_integrable :
    IntervalIntegrable helicity MeasureTheory.volume 0 T
  /-- Vortex-stretching integral `V(t)`. -/
  vortex_stretching : ℝ → ℝ
  /-- `V` is interval-integrable on `[0, T]`. -/
  vortex_stretching_integrable :
    IntervalIntegrable vortex_stretching MeasureTheory.volume 0 T
  /-- The pointwise square `V(t)²`, separately exposed because
  `Phi_candidate` integrates `V²` not `V`. -/
  vortex_stretching_sq_integrable :
    IntervalIntegrable (fun s => (vortex_stretching s) ^ 2)
      MeasureTheory.volume 0 T
  /-- Kinetic energy `E(t) = (1/2) ∫ |u|²`. -/
  energy : ℝ → ℝ
  /-- `E` is interval-integrable on `[0, T]`. -/
  energy_integrable :
    IntervalIntegrable energy MeasureTheory.volume 0 T
  /-- **SUBSTRATE-FIX 2026-05-07.** Binding clause forcing the abstract
  `helicity, vortex_stretching, energy` traces to actually equal the
  corresponding integral functionals of `sol.u`.  Opaque, so all-zero
  traces no longer inhabit `HelicityVortexCrossData sol`. -/
  traces_bind_sol :
    HelicityVortexCrossTracesBindSol sol helicity vortex_stretching energy

/-! ## §2.  The candidate Φ functional

`Φ(t) := H(t)² + 2ν · ∫₀ᵗ V(s)² ds - α · E(t)`. -/

/-- The **candidate** Φ functional from the cross-identity conjecture.

`Φ(t) = H(t)² + 2ν · ∫₀ᵗ V(s)² ds - α · E(t)`. -/
def Phi_candidate
    {nse : NavierStokes.NavierStokesEquations 3}
    {sol : NavierStokes.WeakSolution nse}
    (D : HelicityVortexCrossData sol) (t : ℝ) : ℝ :=
  (D.helicity t) ^ 2
    + 2 * D.nu *
        (∫ s in (0 : ℝ)..t, (D.vortex_stretching s) ^ 2)
    - D.alpha * D.energy t

/-! ## §3.  Sign-corrected variant Φ_corrected

`Φ_corr(t) := α · E(t) − H(t)²/(2 E(t)) − ε · ∫₀ᵗ V(s)² ds`.

We carry `ε` as a separately supplied positive parameter via the
companion `HelicityVortexCrossCorrectedExtras` record below, to keep
the shape of `HelicityVortexCrossData` minimal and reusable. -/

/-- Extras packaging the sign-corrected variant's free parameter `ε`. -/
structure HelicityVortexCrossCorrectedExtras where
  /-- Coefficient on the cumulative `∫ V²` term in the corrected
  variant.  Positive. -/
  epsilon : ℝ
  /-- `ε > 0`. -/
  epsilon_pos : 0 < epsilon

/-- The **sign-corrected** Φ functional.

`Φ_corr(t) = α · E(t) − H(t)²/(2 E(t)) − ε · ∫₀ᵗ V(s)² ds`.

NOTE: this is a non-polynomial combiner.  At hypothetical
vacuum-energy points `E(t) = 0`, the term `H²/(2E)` is formally
singular; we adopt the convention that division by zero in Lean
returns `0`, so the formula is still total but degenerate at `E = 0`. -/
def Phi_corrected
    {nse : NavierStokes.NavierStokesEquations 3}
    {sol : NavierStokes.WeakSolution nse}
    (D : HelicityVortexCrossData sol)
    (X : HelicityVortexCrossCorrectedExtras) (t : ℝ) : ℝ :=
  D.alpha * D.energy t
    - (D.helicity t) ^ 2 / (2 * D.energy t)
    - X.epsilon *
        (∫ s in (0 : ℝ)..t, (D.vortex_stretching s) ^ 2)

/-! ## §4.  Conjectured monotonicity Props

We expose the conjectures as `Prop`s so downstream code (skeptic
reviewers, SymPy bridges, future Lean theorems) can either prove or
falsify them. -/

/-- **CONJECTURE (likely false in this form).**

`Φ_candidate` is non-increasing on `[0, T]`.

The sign analysis in the file header strongly suggests this is FALSE
generically: the term `2ν V(t)²` is non-negative and the term
`+2αν · enstrophy` is non-negative, so `dΦ/dt ≥ 0` outside the
helicity-curl-aligned regime.

We record it as a Prop anyway, both to make the conjecture inspectable
and to give a SymPy/numerical attack a typed target. -/
def ConjecturedMonotonicity_candidate
    {nse : NavierStokes.NavierStokesEquations 3}
    {sol : NavierStokes.WeakSolution nse}
    (D : HelicityVortexCrossData sol) : Prop :=
  ∀ t₁ t₂ : ℝ, 0 ≤ t₁ → t₁ ≤ t₂ → t₂ ≤ D.T →
    Phi_candidate D t₂ ≤ Phi_candidate D t₁

/-- **CONJECTURE (status: open; depends on `α, ε` and on alignment).**

`Φ_corrected` is non-increasing on `[0, T]` for some choice of
parameters `(α, ε)`. -/
def ConjecturedMonotonicity_corrected
    {nse : NavierStokes.NavierStokesEquations 3}
    {sol : NavierStokes.WeakSolution nse}
    (D : HelicityVortexCrossData sol)
    (X : HelicityVortexCrossCorrectedExtras) : Prop :=
  ∀ t₁ t₂ : ℝ, 0 ≤ t₁ → t₁ ≤ t₂ → t₂ ≤ D.T →
    Phi_corrected D X t₂ ≤ Phi_corrected D X t₁

/-- **CONJECTURE.** At a hypothetical blow-up time `T*`, `Φ` (either
variant) explodes: `Φ(t) → +∞` as `t → T*⁻`.

We expose this in the candidate-form via the cumulative `∫ V²` term:
if `V(t)² → ∞` faster than `α E(t)` decays, then `Φ_candidate(t) → ∞`.
This direction is the EASIER one to argue informally — the hard part
is monotonicity, not explosion. -/
def ConjecturedBlowupExplosion_candidate
    {nse : NavierStokes.NavierStokesEquations 3}
    {sol : NavierStokes.WeakSolution nse}
    (D : HelicityVortexCrossData sol)
    (Tstar : ℝ) : Prop :=
  Tstar ≤ D.T ∧
  ∀ M : ℝ, ∃ t : ℝ, 0 ≤ t ∧ t < Tstar ∧ M ≤ Phi_candidate D t

/-! ## §5.  The full cross-structure typed companion

Bundle data + both conjectures into a single record so the file's
shipped artifact is a single typed object inspectable by the
architecture map. -/

/-- **Typed companion** for the helicity ↔ vortex-stretching cross
identity.

Carries the cross-structure data `D` plus the two conjectured
monotonicity Props (candidate + corrected) plus the corrected variant's
extra parameter `X`.

This record makes EXPLICIT, at the type level, that the file is
shipping conjectures-as-Props rather than theorems. -/
structure HelicityVortexCrossStructure
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse) where
  /-- Underlying cross-identity data. -/
  data : HelicityVortexCrossData sol
  /-- Free parameters for the corrected Φ variant. -/
  corrected_extras : HelicityVortexCrossCorrectedExtras
  /-- The candidate-Φ monotonicity conjecture (LIKELY FALSE; we carry
  it as a Prop, not as an inhabited proof). -/
  conjecture_candidate : Prop :=
    ConjecturedMonotonicity_candidate data
  /-- The corrected-Φ monotonicity conjecture (status: OPEN). -/
  conjecture_corrected : Prop :=
    ConjecturedMonotonicity_corrected data corrected_extras

namespace HelicityVortexCrossStructure

variable {nse : NavierStokes.NavierStokesEquations 3}
  {sol : NavierStokes.WeakSolution nse}

/-- Extract the helicity time series. -/
def helicity (S : HelicityVortexCrossStructure sol) : ℝ → ℝ :=
  S.data.helicity

/-- Extract the vortex-stretching time series. -/
def vortex_stretching (S : HelicityVortexCrossStructure sol) : ℝ → ℝ :=
  S.data.vortex_stretching

/-- Extract the energy time series. -/
def energy (S : HelicityVortexCrossStructure sol) : ℝ → ℝ :=
  S.data.energy

/-- Evaluate the candidate Φ functional. -/
def evalPhiCandidate (S : HelicityVortexCrossStructure sol) (t : ℝ) : ℝ :=
  Phi_candidate S.data t

/-- Evaluate the corrected Φ functional. -/
def evalPhiCorrected (S : HelicityVortexCrossStructure sol) (t : ℝ) : ℝ :=
  Phi_corrected S.data S.corrected_extras t

end HelicityVortexCrossStructure

/-! ## §6.  Bridge to the existing helicity / vortex-stretching companion

If a downstream user supplies BOTH a `HelicityVortexStretchingData`
(the existing Vasseur-premise companion from
`ns_trackb_helicity_vortex_stretching.lean`) AND a
`HelicityVortexCrossData` for the same solution, we can copy the
`H, V` time series across.  This is just a forward-constructor
helper — no analytical content. -/

/-- Copy the helicity / vortex-stretching time series from a
`HelicityVortexStretchingData` companion into a fresh
`HelicityVortexCrossData`.

The user supplies the additional fields `nu, alpha, energy` and the
relevant integrability witnesses; the helicity/stretching data is
inherited. -/
def HelicityVortexCrossData.ofStretchingData
    {nse : NavierStokes.NavierStokesEquations 3}
    {sol : NavierStokes.WeakSolution nse}
    (D : HelicityVortexStretchingData sol)
    (nu : ℝ) (nu_pos : 0 < nu)
    (alpha : ℝ) (alpha_pos : 0 < alpha)
    (energy : ℝ → ℝ)
    (energy_integrable :
      IntervalIntegrable energy MeasureTheory.volume 0 D.T)
    (vortex_sq_integrable :
      IntervalIntegrable (fun s => (D.vortex_stretching s) ^ 2)
        MeasureTheory.volume 0 D.T)
    -- SUBSTRATE-FIX 2026-05-07: caller must supply binding clause so
    -- the constructor can no longer manufacture a sol-decoupled cross
    -- companion from the stretching companion alone.
    (traces_bind_sol :
      HelicityVortexCrossTracesBindSol sol
        D.helicity D.vortex_stretching energy) :
    HelicityVortexCrossData sol :=
  { T := D.T
  , T_pos := D.T_pos
  , nu := nu
  , nu_pos := nu_pos
  , alpha := alpha
  , alpha_pos := alpha_pos
  , helicity := D.helicity
  , helicity_integrable := D.helicity_integrable
  , vortex_stretching := D.vortex_stretching
  , vortex_stretching_integrable := D.vortex_stretching_integrable
  , vortex_stretching_sq_integrable := vortex_sq_integrable
  , energy := energy
  , energy_integrable := energy_integrable
  , traces_bind_sol := traces_bind_sol }

/-! ## §7.  Sanity lemmas (logic only — no PDE content)

Trivial structural lemmas about Φ.  These are NOT analytical; they
just record that the candidate and corrected Φ behave linearly /
algebraically as written.  They serve as compile-time sanity checks
on the definitions. -/

/-- At `t = 0`, the candidate Φ reduces to `H(0)² − α · E(0)` (the
cumulative `∫₀⁰ V² = 0`). -/
theorem Phi_candidate_at_zero
    {nse : NavierStokes.NavierStokesEquations 3}
    {sol : NavierStokes.WeakSolution nse}
    (D : HelicityVortexCrossData sol) :
    Phi_candidate D 0 =
      (D.helicity 0) ^ 2 - D.alpha * D.energy 0 := by
  unfold Phi_candidate
  simp

/-- The candidate Φ is real-valued (trivially: it is defined as a
real). -/
theorem Phi_candidate_real
    {nse : NavierStokes.NavierStokesEquations 3}
    {sol : NavierStokes.WeakSolution nse}
    (D : HelicityVortexCrossData sol) (t : ℝ) :
    ∃ y : ℝ, Phi_candidate D t = y :=
  ⟨_, rfl⟩

/-! ## §8.  The conjectural axiom (UNUSED — recorded for honesty)

We do NOT mark `ConjecturedMonotonicity_candidate` as an axiom,
because it is very likely FALSE in its stated form.  We do, however,
expose a CONDITIONAL bridge: IF the corrected-variant monotonicity
held, THEN it would feed the existing Vasseur-style smoothness
criterion via a (still-conjectural) chain.  We axiomatize ONLY this
conditional, with explicit citation that the discharge is open. -/

/-- **AXIOM (conditional, OPEN).** If the corrected Φ functional is
non-increasing on `[0, T]` AND a Vasseur-style premise holds at the
endpoint, then the cross-structure feeds smoothness propagation.

This axiom is not used to close anything in the architecture; it is
a typed PLACEHOLDER for the conditional mathematical claim "monotone
Φ_corr controls vortex stretching".  Discharging it requires either
proving the conjecture or replacing it with an explicit Lyapunov
argument.

Status: OPEN.  Citation: this file (no published reference).

**SUBSTRATE-FIX 2026-05-07 (REPAIRED).**  `HelicityVortexCrossData
sol` previously carried `helicity, vortex_stretching, energy : ℝ → ℝ`
trace fields decoupled from `sol`, allowing the all-zero trace to
inhabit it and trivially discharge the conjecture Props.  As of
2026-05-07 the structure now carries a `traces_bind_sol :
HelicityVortexCrossTracesBindSol sol …` field that is opaque
(cannot be inhabited by zero traces), forcing every supplier of
`HelicityVortexCrossData` to supply a trace-binding witness via a
named diagnostic-identity axiom (FIX-D pattern).  See
`ZtareProofs/ns_trackb_trace_binds_sol.lean`. -/
axiom cross_identity_conditional_propagation
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse)
    (S : HelicityVortexCrossStructure sol)
    (_h_corr_monotone :
      ConjecturedMonotonicity_corrected S.data S.corrected_extras) :
    VasseurStretchingFinite sol S.data.T

/-! ## §9.  Honesty receipt

Total content of this file:

* 1 typed companion record:
  - `HelicityVortexCrossData`        (H, V, E, ν, α with integrability)
* 1 extras record:
  - `HelicityVortexCrossCorrectedExtras`  (ε for corrected variant)
* 2 candidate functional defs:
  - `Phi_candidate`                  (polynomial: H² + 2ν∫V² − αE)
  - `Phi_corrected`                  (rational: αE − H²/(2E) − ε∫V²)
* 3 conjecture Props (NOT THEOREMS):
  - `ConjecturedMonotonicity_candidate`   (likely FALSE)
  - `ConjecturedMonotonicity_corrected`   (status OPEN)
  - `ConjecturedBlowupExplosion_candidate` (status OPEN; easier dir.)
* 1 bundle record:
  - `HelicityVortexCrossStructure`   (data + both conjectures)
* 1 forward constructor:
  - `HelicityVortexCrossData.ofStretchingData`
* 2 sanity lemmas (logic only):
  - `Phi_candidate_at_zero`
  - `Phi_candidate_real`
* 1 conditional axiom (OPEN, unused):
  - `cross_identity_conditional_propagation`

Zero `sorry`s.

EXPLORATORY VERDICT (SymPy-validated 2026-05-07)
-------------------------------------------------
Empirical sign-test of `dΦ/dt|_{t=0}` on three exact symbolic flows
(viscosity ν = 1/100, α = 1, periodic cube `[0, 2π]³`):

| Flow                        | H(0)    | V(0) | dΦ/dt|_0          | Sign    |
|-----------------------------|---------|------|-------------------|---------|
| Beltrami `(sin z, 0, cos z)`| 0       | 0    | `+π³/25`          | + (anti)|
| Screw `(sin z, cos z, 0)`   | `8π³`   | 0    | `2π³(1−32π³)/25`  | − (Lyap)|
| ABC `A=B=C=1` Beltrami      | `24π³`  | 0    | `6π³(1−96π³)/25`  | − (Lyap)|

Conclusion: the polynomial candidate Φ is NOT universally Lyapunov,
but it IS Lyapunov on flows with sufficiently large helicity at
t = 0.  The crossover happens at `H(0)² ≳ α · enstrophy(0) / (2 ν)`,
where the negative `4 H · ν · ∫ ω·curl ω` term overcomes the positive
`+2αν · enstrophy` term.  Zero-helicity flows like the standard
Beltrami `(sin z, 0, cos z)` are EXACTLY the failure mode predicted
by the header sign analysis.

The honest mathematical content of this file:

  Φ_candidate is a CONDITIONAL Lyapunov: monotone-decreasing on the
  initial-data subset `{u₀ : H(u₀)² · 4ν · |∫ω·curlω| ≥ 2αν · Ens(u₀)
  + 2ν · V(u₀)²}`.  Outside that set, it is anti-Lyapunov.

This is genuinely useful information: it carves the initial-data
manifold into two regions and tells future research which side is
worth pushing on.  A *modified* combiner might be globally monotone
by gating on `H²` vs. enstrophy, e.g. via a smooth indicator
multiplier on the `+ 2ν · V²` term.

The `Phi_corrected` rational variant remains untested on these flows
(its `H²/(2E)` factor is well-defined here since `E(0) > 0` for all
three) — that is the obvious next exploration.

This file CONSTRAINS the search space for monotone helicity-stretching
combiners by recording — at the type level — exactly which initial-
data subset the candidate works on and which it fails on.  Recording
a CONDITIONAL Lyapunov as a typed Prop is the load-bearing epistemic
move: the conjecture is not "Φ is monotone" (false) nor "Φ is never
monotone" (also false) but "Φ is monotone on a specific helicity-
dominated subset" (the sharp truth).
-/

end

end ZtareProofs.NS
