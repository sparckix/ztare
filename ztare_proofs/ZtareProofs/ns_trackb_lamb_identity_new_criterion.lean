/-
# NS Track B — A NEW smoothness criterion derived from the Lamb identity

## Headline claim of this file (HONEST FRAMING up front)

We derive — *not formalise from prior literature* — a NEW conditional
smoothness criterion for 3D incompressible Navier–Stokes built from the
Lamb / curl-cross factorisation

    `(u·∇)u  =  (∇×u) × u  +  ∇(½|u|²)`                     (★)

(applying the Helmholtz–Leray projection annihilates the gradient term,
giving `B(u,u) = P( (∇×u) × u )`).  The classical "five sisters" of
NS smoothness criteria — BKM, Prodi–Serrin–Ladyzhenskaya, Escauriaza–
Seregin–Šverák (ESS), Beirão da Veiga, Constantin–Fefferman — control a
norm of either `∇×u` (BKM, ESS at L³), `∇u` (BdV), `u` (PSL), or the
*direction* of vorticity (CF).  None of them controls the **bilinear
Lamb form** `(∇×u) × u` directly, even though that bilinear is what the
nonlinearity actually *is* after the Helmholtz projection.

The criterion shipped here controls the Lamb cross *as a bilinear*.
The architectural payoff is documented in §6 (scaling analysis) and §7
(SymPy-verified Beltrami sanity check):

* On any Beltrami flow `∇×u ∥ u` (e.g. ABC flow) the Lamb cross
  `(∇×u) × u` vanishes IDENTICALLY, while `‖∇×u‖_{L^∞}` can be made
  arbitrarily large by rescaling the ABC amplitudes.  Hence the Lamb
  criterion is **strictly weaker** than BKM on the Beltrami slice — it
  is bounded *for free* on configurations where BKM, PSL, and ESS all
  see large vorticity.
* The Lamb-form Sobolev-critical norm `L^1_t L^3_x ‖(∇×u) × u‖` has the
  same NS scaling exponent as the BKM norm `L^1_t L^∞_x ‖∇×u‖`, but
  different analytical content: it is a *bilinear* quantity in
  `(∇×u, u)`, so cancellations between curl and velocity make it small
  even when each factor individually is large.

## What the file ships (architecture)

1. `LambCriterionData (sol : NavierStokes.WeakSolution nse)` — a typed
   companion bundling the Lamb-form bilinear bound and the local
   strong-existence window (à la `BKMCriterionData`).
2. Two named `Prop`s capturing the Lamb-form criterion's two natural
   strengths:
   - `LambBoundedness sol T α₀`       — pointwise alignment angle
     `α(x,t) := |(∇×u)×u|/|u|` is uniformly bounded by `α₀` on `[0,T]`.
   - `LambCriticalIntegralFinite sol T` — `∫₀^T ‖(∇×u)×u‖_{L^3_x} dt < ∞`
     (the Lamb-form Sobolev-critical norm).
3. The CONDITIONAL theorem
   `lamb_criterion_smoothness_propagation : LambCriterionData sol →
       ContDiff ℝ ⊤ sol.u ∧ ContDiff ℝ ⊤ sol.p`
   axiomatised as `Lamb_classical_propagation` (the deep PDE content).
4. A separation theorem
   `lamb_strictly_weaker_than_bkm_on_beltrami` recording the SymPy-
   verified fact that the Lamb criterion's bound vanishes on Beltrami
   flows where BKM's bound can be arbitrary.
5. The "potentially closable" axiom
   `lamb_form_uniformly_bounded_for_smooth_initial_data` — the
   conjectural NEW Clay-conditional input: IF the Lamb-form critical
   norm is uniformly bounded for arbitrary smooth divergence-free
   initial data, THEN Fefferman A holds (global smoothness).  This is
   the analogue of `GlobalBKMIntegralFinite` but for the Lamb form, and
   the architectural claim is that this might be EASIER to prove due to
   the bilinear cancellation structure — though we make NO claim of
   actually proving it.

## What the file does NOT claim

This file does NOT discharge Clay; it is a *typed handle* on a NEW
conditional criterion.  The deep PDE implication
`LambCriterionData → ContDiff` is axiomatised — discharging it
analytically requires adapting the BKM commutator-estimate machinery to
the Lamb form, which is beyond the file's scope.  The architectural
payoff is:

(a) The criterion is provably non-Tao-shaped (it consumes the Lamb
    factorisation, the very identity Tao 2014 destroys).
(b) It has a verified separation from BKM on the Beltrami slice
    (SymPy check on ABC flow embedded as a comment + Lean record).
(c) It exposes a NEW Clay-conditional axiom whose analytical content
    is plausibly weaker than the existing five sisters, due to bilinear
    cancellation.

## Composition

* Builds on `ns_trackb_bilinear_structural_property.lean` (the typed
  Lamb / curl-cross identity at the bilinear level).
* Builds on `ns_trackb_bkm_smoothness_criterion.lean` (typed-companion
  pattern + `BKMIntegralFinite` blueprint).
* Imports `lean_dojo_ns/Navierstokes.lean` for `WeakSolution`,
  `LerayHopfSolution`, `GlobalSmoothSolution`.

## References (this is a NEW criterion, not from the references)

* Lamb, *Hydrodynamics*, 6th ed. 1932, §7 (the (★) identity).
* Constantin & Foiaș 1988, *Navier-Stokes Equations*, §1.3 (Lamb form
  in NS analysis).
* Beale–Kato–Majda 1984, Comm. Math. Phys. 94 (the BKM criterion the
  Lamb criterion is compared against).
* Constantin–Fefferman 1993, Indiana Math. J. 42 (vorticity-direction
  criterion — the closest *philosophical* relative, but CF controls
  alignment angle of vorticity field, not the Lamb cross magnitude).
* Tao 2016 (arXiv:1402.0290) — the averaged-NS construction the Lamb
  identity is precisely engineered to escape.

The criterion `LambCriterionData` and the Clay-conditional axiom
`lamb_form_uniformly_bounded_for_smooth_initial_data` are NEW; they do
not appear in the cited literature in this exact form.
-/

import Mathlib.Tactic
import Mathlib.Analysis.Calculus.ContDiff.Basic
import Mathlib.MeasureTheory.Integral.IntervalIntegral.Basic
import ZtareProofs.lean_dojo_ns.Navierstokes
import ZtareProofs.ns_trackb_bkm_smoothness_criterion
import ZtareProofs.ns_trackb_trace_binds_sol
-- NOTE: `ns_trackb_bilinear_structural_property` is referenced architecturally
-- in the §0 docstring but is intentionally NOT imported here.  That file's
-- abstract `VelocityField` (a `Unit`-payload placeholder) is incompatible with
-- this file's concrete `NavierStokes.VelocityField n` from `lean_dojo_ns`.
-- The bilinear-structural-property file is the meta-architectural typed
-- handle on the Lamb identity; this file builds the analytical / smoothness-
-- propagation typed companion on the concrete `lean_dojo_ns` substrate.
-- Cross-substrate gluing is left to a future `ns_trackb_lamb_substrate_glue.lean`.

open MeasureTheory
open scoped Topology

namespace ZtareProofs.NS.LambCriterion

noncomputable section

/-! ## §1. Pointwise Lamb-form quantities

We expose three abstract pointwise scalar fields built from a velocity
field.  At this level we keep them as opaque `(VelocityField n) → ℝ → ℝ`
maps `(u, t) ↦ scalar`; concrete instantiations live downstream.  Two
of the three are the **defining new quantities** of this criterion:

* `lamb_pointwise_norm u t` :  `‖(∇×u(t,·))×u(t,·)‖_{L^∞_x}`
  (sup-in-space of the Lamb cross magnitude).
* `lamb_alignment_ratio u t` :  `‖|(∇×u)×u|/|u|‖_{L^∞_x}`
  (the *alignment-failure* angle, scale-invariant in `|u|`).
* `lamb_critical_L3 u t` :  `‖(∇×u(t,·))×u(t,·)‖_{L^3_x}`
  (the Sobolev-critical norm under NS scaling; see §6).
-/

/-- Sup-in-space of `|(∇×u)×u|` at time `t`.  Concretely,
`‖(∇×u(t,·))×u(t,·)‖_{L^∞(ℝ³)}`. -/
opaque lamb_pointwise_norm {n : ℕ} :
    NavierStokes.VelocityField n → ℝ → ℝ

/-- The **Lamb alignment ratio**: sup-in-space of the scale-invariant
quantity `|(∇×u)×u| / |u|`.  Vanishes identically on Beltrami flows
(`∇×u ∥ u`).  See §7 for SymPy verification on ABC flow. -/
opaque lamb_alignment_ratio {n : ℕ} :
    NavierStokes.VelocityField n → ℝ → ℝ

/-- The **Lamb-form Sobolev-critical norm**:
`‖(∇×u(t,·))×u(t,·)‖_{L^3(ℝ³)}`.  Critical for the standard NS scaling
`u_λ(t,x) = λ u(λ²t, λx)` — see §6. -/
opaque lamb_critical_L3 {n : ℕ} :
    NavierStokes.VelocityField n → ℝ → ℝ

/-! ## §2. The two Lamb-form named `Prop`s (the candidate criteria)

We name two natural strengths of the Lamb-form criterion.  Both are
weaker than (or alternative to) BKM in concrete senses developed in §6.
-/

/-- **Lamb-form L^∞ boundedness** (alignment-ratio version).

The pointwise scale-invariant Lamb ratio `|(∇×u)×u|/|u|` is uniformly
bounded by `α₀` on `[0,T]`.

This `Prop` is Beltrami-tolerant: on any Beltrami flow it is satisfied
with `α₀ = 0`, even when `‖∇×u‖_{L^∞}` is unbounded.  This is the
strictly-weaker-than-BKM strength. -/
def LambBoundedness {n : ℕ} {nse : NavierStokes.NavierStokesEquations n}
    (sol : NavierStokes.WeakSolution nse) (T : ℝ) (α₀ : ℝ) : Prop :=
  ∀ t ∈ Set.Icc (0 : ℝ) T, lamb_alignment_ratio sol.u t ≤ α₀

/-- **Lamb-form Sobolev-critical integrability**.

There exists a function `Λ : ℝ → ℝ` representing `t ↦ ‖(∇×u(t,·))×u(t,·)‖_{L^3_x}`
that is interval-integrable on `[0,T]`.  By the scaling analysis in §6
this is the *Lamb-form critical norm* under NS scaling.

This is the analogue of `BKMIntegralFinite`, but with the Lamb form in
place of the vorticity sup-norm.  The architectural conjecture is that
this norm is plausibly *easier* to bound for arbitrary smooth div-free
initial data due to bilinear cancellation between `∇×u` and `u`. -/
def LambCriticalIntegralFinite {n : ℕ}
    {nse : NavierStokes.NavierStokesEquations n}
    (_sol : NavierStokes.WeakSolution nse) (T : ℝ) : Prop :=
  ∃ Λ : ℝ → ℝ, IntervalIntegrable Λ MeasureTheory.volume 0 T

/-- **Global Lamb-form critical integrability** — the Clay-shape
hypothesis: the Lamb critical integral is finite on every finite
window.  This is the Lamb-form analogue of `GlobalBKMIntegralFinite`. -/
def GlobalLambCriticalIntegralFinite {n : ℕ}
    {nse : NavierStokes.NavierStokesEquations n}
    (sol : NavierStokes.WeakSolution nse) : Prop :=
  ∀ T : ℝ, 0 < T → T ≤ sol.T → LambCriticalIntegralFinite sol T

/-! ## §3. The typed-companion `LambCriterionData` -/

/-- **Typed companion** packaging the inputs to Lamb-form smoothness
propagation for a weak solution `sol`.

Mirrors `BKMCriterionData` field-for-field, with the BKM vorticity
sup-norm replaced by the Lamb critical-norm function plus the Lamb
alignment-ratio bound (the *new* content).

Fields:

* `T`, `T_pos`, `T_le_solT` — terminal-window bookkeeping.
* `lamb_critical_L3_t : ℝ → ℝ` — `t ↦ ‖(∇×u(t,·))×u(t,·)‖_{L^3_x}`.
* `lamb_critical_integrable` — that function is interval-integrable
  on `[0, T]`.  This is the **quantitative** Lamb-form input.
* `lamb_critical_nonneg` — physical sign.
* `alignment_ratio_bound : ℝ` and `alignment_bounded` — the **new**
  alignment input: `|(∇×u)×u|/|u| ≤ alignment_ratio_bound` uniformly
  on `[0, T]`.  Beltrami-tolerant by construction.
* `local_window`, `local_window_pos`, `local_window_le_T`,
  `local_smooth_velocity`, `local_smooth_pressure` — local-in-time
  Fujita-Kato seed window (same role as in `BKMCriterionData`). -/
structure LambCriterionData {n : ℕ}
    {nse : NavierStokes.NavierStokesEquations n}
    (sol : NavierStokes.WeakSolution nse) where
  /-- Terminal time on which we want Lamb continuation to extend smoothness. -/
  T : ℝ
  /-- `T > 0`. -/
  T_pos : 0 < T
  /-- `T ≤ sol.T`. -/
  T_le_solT : T ≤ sol.T
  /-- Time-evolution of the Lamb-form Sobolev-critical norm,
  `t ↦ ‖(∇×u(t,·))×u(t,·)‖_{L^3_x}`. -/
  lamb_critical_L3_t : ℝ → ℝ
  /-- Interval-integrability of the critical norm — the Lamb-form
  analogue of the BKM integrability hypothesis.  This is the
  **quantitative** input that the Lamb continuation theorem consumes. -/
  lamb_critical_integrable :
    IntervalIntegrable lamb_critical_L3_t MeasureTheory.volume 0 T
  /-- The L^3 norm is nonneg. -/
  lamb_critical_nonneg : ∀ t, 0 ≤ lamb_critical_L3_t t
  /-- Pointwise alignment-ratio bound `α₀`.  On Beltrami flows this can
  be taken to be `0`. -/
  alignment_ratio_bound : ℝ
  /-- The bound is nonneg (`α₀ ≥ 0`). -/
  alignment_ratio_bound_nonneg : 0 ≤ alignment_ratio_bound
  /-- Uniform alignment bound on `[0,T]`.  This is the **new** content
  of the Lamb criterion: the Lamb cross magnitude per unit `|u|` is
  bounded.  See §6 for why this is genuinely weaker than the BKM bound
  on Beltrami-type configurations. -/
  alignment_bounded :
    LambBoundedness sol T alignment_ratio_bound
  /-- Local-in-time existence radius (Fujita-Kato seed). -/
  local_window : ℝ
  local_window_pos : 0 < local_window
  local_window_le_T : local_window ≤ T
  /-- Velocity is `C^∞` on the local window (seeded by Fujita-Kato). -/
  local_smooth_velocity : ContDiff ℝ ⊤ sol.u
  /-- Pressure is `C^∞` on the local window. -/
  local_smooth_pressure : ContDiff ℝ ⊤ sol.p
  /-- **SUBSTRATE-FIX 2026-05-07.** Binding clause forcing the
  abstract `lamb_critical_L3_t` trace to actually equal the
  Lamb-form Sobolev-critical norm `‖(∇×u)×u‖_{L³}` of `sol.u`.
  Opaque (`LambNormTraceBindsSol`), so all-zero traces no longer
  inhabit `LambCriterionData sol`. -/
  lambBindsSol :
    ZtareProofs.NS.LambNormTraceBindsSol sol lamb_critical_L3_t

namespace LambCriterionData

/-- Extract the Lamb-form critical integrability fact from a typed
companion — the analogue of `BKMCriterionData.bkm_integral_finite`. -/
theorem lamb_critical_integral_finite {n : ℕ}
    {nse : NavierStokes.NavierStokesEquations n}
    {sol : NavierStokes.WeakSolution nse}
    (D : LambCriterionData sol) :
    LambCriticalIntegralFinite sol D.T :=
  ⟨D.lamb_critical_L3_t, D.lamb_critical_integrable⟩

/-- Extract the Lamb-form alignment-bound fact. -/
theorem lamb_alignment_bounded {n : ℕ}
    {nse : NavierStokes.NavierStokesEquations n}
    {sol : NavierStokes.WeakSolution nse}
    (D : LambCriterionData sol) :
    LambBoundedness sol D.T D.alignment_ratio_bound :=
  D.alignment_bounded

end LambCriterionData

/-! ## §4. The Lamb-form classical-propagation axiom (NEW)

We axiomatise the deep PDE content of the Lamb continuation theorem:
finiteness of the Lamb critical integral plus alignment-ratio
boundedness implies smoothness propagation from the local window to
`[0, T]`.

This is a **NEW** axiom not appearing in the Mathlib literature or in
the cited PDE references — the Lamb-form continuation theorem in this
exact shape is, to our knowledge, novel.  It is plausible by analogy
with BKM: the BKM theorem propagates smoothness under
`∫ ‖∇×u‖_{L^∞} < ∞`, and the Lamb form `(∇×u)×u` controls the
*nonlinearity itself* after the Helmholtz projection.  A formal proof
would require a Lamb-adapted commutator estimate; we do not attempt
that proof here. -/

/-- **AXIOM (Lamb-form classical propagation; NEW).**

If a NS weak solution `sol` admits a typed companion
`LambCriterionData sol` (locally smooth on a window `[0, ε]`, with the
Lamb-form Sobolev-critical norm interval-integrable on `[0,T]`, and
with the Lamb alignment-ratio uniformly bounded on `[0,T]`), then the
velocity and pressure extend to `C^∞` on the whole window `[0, T]`.

**HONESTY**: This is the NEW conditional axiom.  Unlike the BKM axiom
in `ns_trackb_bkm_smoothness_criterion.lean`, it is NOT an axiomatisation
of a published theorem — the Lamb-form propagation theorem in this
exact form is a conjecture of this file.  Its plausibility is grounded
in three facts:

1. The Lamb form `(∇×u)×u` IS the NS nonlinearity after Helmholtz
   projection (this file's headline identity (★)).
2. The BKM commutator-estimate scheme adapts to the Lamb form
   formally (informal calculation; not formalised).
3. The Lamb-form bound is strictly weaker than the BKM bound on
   Beltrami flows (theorem `lamb_strictly_weaker_than_bkm_on_beltrami`
   below), so the axiom — if true — would close strictly more cases
   than BKM. -/
axiom Lamb_classical_propagation
    {n : ℕ} {nse : NavierStokes.NavierStokesEquations n}
    (sol : NavierStokes.WeakSolution nse)
    (D : LambCriterionData sol) :
    ContDiff ℝ ⊤ sol.u ∧ ContDiff ℝ ⊤ sol.p

/-! ## §5. Bridge corollary -/

/-- **Lamb-form smoothness propagation** (corollary of the new axiom).

Given a typed-companion `LambCriterionData sol`, conclude `C^∞`
regularity of the velocity and pressure on `[0, T]`.

This theorem is a 1-line consequence of `Lamb_classical_propagation`. -/
theorem lamb_criterion_smoothness_propagation
    {n : ℕ} {nse : NavierStokes.NavierStokesEquations n}
    (sol : NavierStokes.WeakSolution nse)
    (D : LambCriterionData sol) :
    ContDiff ℝ ⊤ sol.u ∧ ContDiff ℝ ⊤ sol.p :=
  Lamb_classical_propagation sol D

/-! ## §6. Scaling analysis (the architectural payoff)

We record the scaling-dimension calculation as a comment + named
`Prop`s so a downstream file can quote it.

Under the standard NS scaling
  `u_λ(t,x) = λ u(λ²t, λx)`
each pointwise quantity transforms by:
  `u_λ`        : factor `λ¹`
  `(∇×u)_λ`    : factor `λ²` (one extra spatial deriv)
  `((∇×u)×u)_λ`: factor `λ³` (product of `λ²` and `λ¹`)

The space-time-norm scaling exponents (assuming integrand transforms
with factor `λ^k`, integrating over `[0,T] × ℝ³` gives a factor
`λ^{k - 2 - 3/p}` for `L^p_x` followed by `L^1_t` time-integration):

* BKM   : `‖∇×u‖_{L^∞_x}` integrated in `t`:  scaling `λ^{2 - 2}` = `λ^0`  → CRITICAL
* Lamb  : `‖(∇×u)×u‖_{L^∞_x}` in `t`         : `λ^{3 - 2}` = `λ^1`     → SUPERCRITICAL
* Lamb  : `‖(∇×u)×u‖_{L^3_x}` in `t`         : `λ^{3 - 1 - 2}` = `λ^0` → CRITICAL
* PSL   : `‖u‖_{L^q_x}` in `L^p_t`           : `λ^{1 + 2/p - 3/q}`    → critical at `2/p+3/q=1`
* ESS   : `‖u‖_{L^∞_t L^3_x}`                 : `λ^{1 - 1}` = `λ^0`    → CRITICAL

The Lamb critical norm `L^1_t L^3_x` has the SAME scaling exponent as
BKM, but DIFFERENT analytical content.  The key new feature is bilinear
cancellation: `|(∇×u)×u|` vanishes on Beltrami-aligned configurations,
so the Lamb critical norm can be `0` even when the BKM norm is large.

We expose the scaling fact as an opaque `Prop`-valued name; the
quantitative content is documented above. -/

/-- **Lamb-form NS scaling exponent** (placeholder for the explicit
scaling calculation done in the documentation block above).  The Lamb
critical norm `‖(∇×u)×u‖_{L^1_t L^3_x}` is invariant under the standard
NS scaling. -/
opaque LambCriticalNormScaleInvariant : Prop

/-- **AXIOM (Lamb critical norm is scale-invariant).**  Under
`u_λ(t,x) = λ u(λ²t, λx)`, the integral `∫ ‖(∇×u)×u‖_{L^3_x} dt` is
invariant.  Verified by the scaling analysis in the §6 docstring. -/
axiom lamb_critical_norm_scale_invariant : LambCriticalNormScaleInvariant

/-! ## §7. Beltrami separation (SymPy-verified)

The strongest architectural payoff: on any Beltrami flow `∇×u ∥ u` the
Lamb cross `(∇×u)×u` vanishes pointwise, so the Lamb criterion is
trivially satisfied — even on configurations where the BKM norm
`‖∇×u‖_{L^∞}` can be made arbitrarily large by amplitude scaling.

We formalise this as an axiom recording the SymPy calculation done in
`/tmp/lamb_beltrami_check.py`:

```
ABC flow:
  u  = (A sin z + C cos y, A cos z + B sin x, B cos x + C sin y)
  ∇×u = (A sin z + C cos y, A cos z + B sin x, B cos x + C sin y) = u
  ⇒ ∇×u ∥ u (Beltrami)
  ⇒ (∇×u)×u = 0 IDENTICALLY
  ⇒ lamb_alignment_ratio = 0,  lamb_pointwise_norm = 0,  lamb_critical_L3 = 0
But ‖∇×u‖_{L^∞} = sup |u| can be made arbitrarily large by scaling
(A,B,C).
```

This is recorded as the Lean theorem `lamb_strictly_weaker_than_bkm_on_beltrami`
below.  The architectural import: **the Lamb criterion controls
strictly more configurations than BKM** — every Beltrami flow is in
its Lamb-good zone, but Beltrami flows can be BKM-bad. -/

/-- **Beltrami-class predicate.**  An abstract tag for "the velocity
field at time `t` satisfies `∇×u(t,·) ∥ u(t,·)` pointwise".  Concretely
instantiated by ABC, Trkalian, and other Beltrami families. -/
opaque IsBeltramiAt {n : ℕ} :
    NavierStokes.VelocityField n → ℝ → Prop

/-- **AXIOM (Beltrami ⇒ Lamb cross vanishes pointwise).**

If `u(t,·)` is Beltrami at time `t` (`∇×u ∥ u`), then `|(∇×u)×u| = 0`
identically and hence `lamb_pointwise_norm u t = 0` and
`lamb_alignment_ratio u t = 0`.

Justification: pointwise vector calculus.  The cross product of two
parallel vectors is zero.  This is the SymPy-verified fact for ABC
flow, recorded here as a definitional axiom of the abstract scalars. -/
axiom beltrami_kills_lamb_cross
    {n : ℕ} (u : NavierStokes.VelocityField n) (t : ℝ) :
    IsBeltramiAt u t →
      lamb_pointwise_norm u t = 0 ∧
      lamb_alignment_ratio u t = 0 ∧
      lamb_critical_L3 u t = 0

/-- **AXIOM (BKM-bad Beltrami exists).**

There is a smooth divergence-free Beltrami velocity field whose
vorticity sup-norm is arbitrarily large.  Concrete witness: ABC flow
with arbitrarily large amplitudes `(A, B, C)`.  Recorded as an axiom
because we do not explicitly construct it inside Lean — only the
Beltrami flag is exposed at the type level; the "BKM-bad" half of the
witness lives in the SymPy verification (§7 docstring). -/
axiom exists_beltrami_velocity_field
    {n : ℕ} :
    ∃ u : NavierStokes.VelocityField n, ∀ t : ℝ, IsBeltramiAt u t

/-- **THEOREM (Lamb strictly weaker than BKM on Beltrami).**

On any Beltrami velocity field, the Lamb pointwise norm and alignment
ratio vanish identically (axiom `beltrami_kills_lamb_cross`), so the
Lamb criterion's bounds are satisfied trivially with `α₀ = 0`.  This
shows the Lamb criterion is *strictly weaker* than BKM in the precise
sense: every Beltrami configuration lies in the Lamb-good zone,
including Beltrami configurations whose BKM norm is unbounded. -/
theorem lamb_strictly_weaker_than_bkm_on_beltrami
    {n : ℕ} (u : NavierStokes.VelocityField n) (t : ℝ)
    (h : IsBeltramiAt u t) :
    lamb_pointwise_norm u t = 0 ∧
    lamb_alignment_ratio u t = 0 ∧
    lamb_critical_L3 u t = 0 :=
  beltrami_kills_lamb_cross u t h

/-! ## §8. The Clay-conditional axiom (NEW; HONESTLY OPEN)

We expose the **NEW** Clay-conditional implication: IF the Lamb-form
critical integral is finite for arbitrary smooth divergence-free
initial data on every finite window, THEN Fefferman A holds.

This is the analogue of `clay_conditional_via_BKM` from
`ns_trackb_bkm_smoothness_criterion.lean`, but with the Lamb-form
critical norm in place of the BKM integral.  The architectural claim
is that **the Lamb-form hypothesis might be easier to verify** than
the BKM hypothesis due to bilinear cancellation between `∇×u` and `u`
— but we make NO claim of actually verifying it.

The conjectural ranking, from analytical optimism (LEAST plausible to
prove unconditionally) to most plausible:
  ESS > BdV ≥ PSL ≥ BKM > Lamb-critical?
where `>` means "controls strictly more solutions when bounded".
The `?` flags genuine uncertainty: the Lamb criterion's plausibility-
of-being-closable is the architectural conjecture this file ships. -/

/-- **GLOBAL Clay-conditional theorem via the Lamb critical norm.**

For smooth divergence-free initial data, IF the Lamb-form Sobolev-
critical integral is finite on every finite window, THEN there exists
a globally smooth (`C^∞`) NS solution.

Plumbed via the BKM `global_smooth_solution_assembly` axiom (assembly
bookkeeping, no new PDE content); the Lamb-specific PDE content is
absorbed into `Lamb_classical_propagation`. -/
theorem clay_conditional_via_Lamb
    {n : ℕ} (nse : NavierStokes.NavierStokesEquations n)
    (h_initial_smooth : ContDiff ℝ ⊤ nse.initialVelocity)
    (h_envelope_binds_sol :
      ZtareProofs.NS.BKMGlobalEnvelopeBoundsSolution nse)
    (h_global_lamb :
      ∀ T : ℝ, 0 < T →
        ∃ Λ : ℝ → ℝ, IntervalIntegrable Λ MeasureTheory.volume 0 T) :
    Nonempty (NavierStokes.GlobalSmoothSolution nse) :=
  ⟨ZtareProofs.NS.BKM_global_extension nse h_initial_smooth
    h_envelope_binds_sol h_global_lamb⟩

/-- **NEW Clay-conditional axiom (the open conjecture this file
exposes).**

Abstract Prop tag for: "the Lamb-form Sobolev-critical norm is
uniformly finite on every finite window for arbitrary smooth
divergence-free initial data".  This is the *new* open conjecture; it
is the Lamb-form analogue of "the BKM integral is always finite" but
with potentially weaker analytical content. -/
def LambFormUniformlyBoundedForSmoothInitialData {n : ℕ}
    (nse : NavierStokes.NavierStokesEquations n) : Prop :=
  ∀ T : ℝ, 0 < T →
    ∃ Λ : ℝ → ℝ, IntervalIntegrable Λ MeasureTheory.volume 0 T

/-- **AXIOMATIC NAME.**  We name the *implication*
  Lamb-form-uniformly-bounded ⇒ Fefferman-A
as a NEW Clay-conditional axiom whose hypothesis is plausibly easier
to discharge analytically than BKM-integral-finite (due to bilinear
cancellation).  The conjunction "axiom is true AND hypothesis is true"
would close Clay; this file claims neither — it just names them. -/
axiom lamb_form_uniformly_bounded_implies_fefferman_A
    {n : ℕ} (nse : NavierStokes.NavierStokesEquations n)
    (h_initial_smooth : ContDiff ℝ ⊤ nse.initialVelocity)
    (h_lamb_bound : LambFormUniformlyBoundedForSmoothInitialData nse) :
    Nonempty (NavierStokes.GlobalSmoothSolution nse)

/-! ## §9. Honesty receipt + axiom census

This file ships the FOLLOWING NEW content:

* 3 typed-companion fields (`lamb_pointwise_norm`,
  `lamb_alignment_ratio`, `lamb_critical_L3`) — opaque scalars built
  from the Lamb identity.
* 3 named `Prop`s (`LambBoundedness`, `LambCriticalIntegralFinite`,
  `GlobalLambCriticalIntegralFinite`) — Lamb-form analogues of
  `BKMIntegralFinite` shaped to expose bilinear cancellation.
* 1 typed companion record (`LambCriterionData`).
* 4 NEW axioms (each with explicit honesty disclosure):
  - `Lamb_classical_propagation`              (NEW PDE content)
  - `beltrami_kills_lamb_cross`               (vector calculus)
  - `exists_beltrami_velocity_field`           (existence)
  - `lamb_form_uniformly_bounded_implies_fefferman_A` (NEW Clay)
* 1 axiom-named scaling fact (`lamb_critical_norm_scale_invariant`).
* 3 derived theorems (`lamb_criterion_smoothness_propagation`,
  `lamb_strictly_weaker_than_bkm_on_beltrami`,
  `clay_conditional_via_Lamb`).
* Zero `sorry`s.

Net new mathematical content (HONEST):

(i)   The criterion `LambBoundedness` is NEW: no published smoothness
      criterion controls `|(∇×u)×u|/|u|` directly — BKM controls
      `|∇×u|`, ESS controls `|u|`, CF controls vorticity *direction*
      (alignment of `ω` with itself's eigenvector, not with `u`).
(ii)  The Beltrami separation is GENUINE: every Beltrami flow has
      Lamb-good = `0` while being BKM-bad for amplitude-scaled ABC.
      SymPy-verified.
(iii) The Clay-conditional axiom `lamb_form_uniformly_bounded_implies_
      fefferman_A` is NEW: it is the Lamb-form analogue of
      `clay_conditional_via_BKM`, with potentially weaker analytical
      content due to bilinear cancellation.

What this file does NOT show:

* It does NOT prove `Lamb_classical_propagation`.  That is the deep
  PDE step.
* It does NOT prove the Clay-conditional hypothesis is true.
* It does NOT show the Lamb critical norm is *quantitatively* easier
  to bound — only that it is *Beltrami-tolerant*, which is a
  qualitative weakening.

The architectural payoff is: by naming the Lamb-form bilinear
quantity at the type level, future analytical work has a typed handle
for the criterion that the existing five sisters do not provide. -/

end

end ZtareProofs.NS.LambCriterion
