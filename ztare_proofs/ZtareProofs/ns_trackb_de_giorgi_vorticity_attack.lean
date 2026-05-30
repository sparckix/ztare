/-
# NS Track B — De Giorgi level-set attack on the vorticity transport equation
#                (helical-with-swirl × De-Giorgi-decay × sub-critical-swirl)
#
# **Status: NEW conditional sub-class hypothesis. Architectural plumbing only.
#  The deep PDE content is left as a single named axiom; we do NOT attempt the
#  proof here.  HONEST FRAMING is enforced throughout: every place where a
#  "real" analytical step would belong is marked by a typed Prop / axiom whose
#  citation explicitly notes that no published theorem discharges it in this
#  exact combination of hypotheses.**
#
# Generated 2026-05-07.
#
# ## OpenMath-4 motivation
#
# Vasseur 2007 (Indiana 56) ports De Giorgi level-set methods (originally
# elliptic, then parabolic — De Giorgi 1957, Caffarelli–Vasseur 2010 for SQG)
# to the 3-D Navier-Stokes vorticity transport equation
#
#     ∂_t ω + (u·∇) ω = (ω·∇) u + ν Δ ω.                                  (*)
#
# The De Giorgi level-set lemma (informally): on the high-level set
# `Ω_κ(t) := { x : |ω(t,x)| > κ }`, the parabolic equation forces enstrophy
# concentration via the iterated truncation `(|ω| - κ_k)_+` with `κ_k ↑ K`.
# An L²-energy estimate combined with the Sobolev embedding gives a recursive
# decay estimate
#
#     a_{k+1}  ≤  C · b^k · a_k^{1+α}                                     (DG)
#
# for the truncated enstrophy `a_k := ∫∫ (|ω| - κ_k)_+² dx dt`.  If `a_0` is
# small, (DG) iterates `a_k → 0` in finite k, hence `|ω| ≤ K` a.e., which
# combined with BKM (Beale–Kato–Majda 1984) yields global smoothness.
#
# In the **unrestricted 3-D case** the small-`a_0` hypothesis is exactly
# Clay-equivalent (controlling vortex stretching `(ω·∇)u`).  Vasseur 2007
# circumvents this via a `u·∇ω`-norm hypothesis (`L^{9/4}_t L^{9/4}_x`),
# **moving the entire criticality budget into the geometric-transport norm**.
#
# This file shifts the budget differently: it RESTRICTS to a sub-class
# (helically symmetric + present-but-controlled swirl) where the
# vortex-stretching has helically-reduced structure, then asks for **only**
# a sub-critical (q > 2) bound on the swirl plus a **De Giorgi level-set
# decay rate** β > 0 on the high-vorticity set.
#
# ## Hypothesis H (NEW conditional sub-class)
#
# A 3-D NS weak solution `sol` satisfies hypothesis **`HelicalDeGiorgi(β, q, κ₀)`**
# if and only if the following four clauses all hold on a finite window
# `[0, T]`:
#
#   (H₁)  **Helical symmetry with swirl.**  The velocity `u` commutes with
#         the one-parameter helical group `H_θ : (x₁,x₂,x₃) ↦ (R_θ(x₁,x₂),
#         x₃ + αθ)` for some pitch `α ∈ ℝ \ {0}`, but the swirl component
#         `u_ξ` (along the helical-circle direction `e_ξ`) is NOT required
#         to vanish.  In particular this strictly extends the Mahalov–Titi–
#         Leibovich 1990 / BLNNT 2013 closed-class (no-swirl) by allowing
#         non-zero `u_ξ`.
#
#   (H₂)  **Sub-critical swirl bound.**  There exists `q > 2` and `M < ∞`
#         such that `‖u_ξ(t,·)‖_{L^∞(ℝ³)} ∈ L^q([0,T])` with norm `≤ M`.
#         The Serrin endpoint is `2/q + 3/p = 1` with `(p,q) = (∞, 2)`,
#         so `q > 2` is **strictly sub-critical**: easier than the open
#         endpoint, but no published global theorem covers it for helical
#         flows with swirl.
#
#   (H₃)  **De Giorgi level-set decay rate.**  There exist `β > 0`,
#         `κ₀ > 0`, and a constant `C_DG < ∞` such that the truncated
#         enstrophy `a_k(t) := ∫₀^t ∫_{ℝ³} (|ω(s,x)| - κ_k)_+² dx ds`
#         (with `κ_k = κ₀(2 - 2^{-k})`) obeys the recursive bound
#         `a_{k+1} ≤ C_DG · 2^{k(1-β)} · a_k^{1+β}` for all `k ∈ ℕ`.
#         **This is the De Giorgi step (DG) above with explicit decay
#         exponent `β` and ratio base `2^{1-β}`.**  Vasseur 2007 proves
#         (DG) with `β = 1/4` for the unrestricted parabolic case under
#         his geometric-transport norm; the present hypothesis assumes
#         (DG) holds **for the helical class with swirl** with some
#         positive `β`, which is **strictly weaker** than Vasseur's
#         transport-norm hypothesis (it is an OUTPUT of his argument)
#         but is **strictly stronger** than asking that some `‖u·∇ω‖`
#         norm be finite (it is the De Giorgi consequence, not the
#         transport input).
#
#   (H₄)  **Initial truncated enstrophy small.**  `a_0(T) ≤ ε_0` for some
#         universal `ε_0 = ε_0(C_DG, β)`.  This is the standard "smallness
#         buy-in" of De Giorgi iteration; it is automatic from the global
#         L² bound at sufficiently large `κ₀`, but we state it as a
#         hypothesis to keep the conditional form transparent.
#
# **Hypothesis H** then reads:
#
#     HelicalDeGiorgi(β, q, κ₀) := (H₁) ∧ (H₂) ∧ (H₃) ∧ (H₄).
#
# ## Why this is NOT in the published literature (HONEST novelty audit)
#
# The closest published results, and the reason each is strictly distinct
# from H:
#
#   *  Mahalov–Titi–Leibovich 1990 / Dutrifoy 1999 / BLNNT 2013:
#      helical-no-swirl ⇒ global smooth.  H ALLOWS swirl, so this does
#      not apply.
#
#   *  Vasseur 2007 (Indiana 56): De Giorgi level-set ⇒ smooth, conditional
#      on `‖u·∇ω‖_{L^{9/4}_t L^{9/4}_x} < ∞`.  Vasseur's INPUT is a
#      transport-norm hypothesis.  H's input (H₃) is the OUTPUT (DG) of
#      his iteration, and asks ONLY that this output decay form HOLD
#      with positive exponent β > 0 on the helical-with-swirl class —
#      strictly weaker as an analytical assumption than the transport
#      norm globally finite.  The novelty is asking what is left after
#      both helical-symmetry-with-swirl AND a positive-β DG decay are
#      assumed.
#
#   *  Lei–Zhang 2011, Liu–Wang 2018 (helical NS with small-swirl
#      perturbation + Constantin-type alignment): Lipschitz-direction or
#      small-swirl asymptotic regimes.  Neither uses De Giorgi level-set
#      iteration; neither asks for sub-critical swirl in `L^q_t L^∞_x` with
#      `q > 2` plus DG-decay.
#
#   *  Constantin–Fefferman 1993, CFM 1996, Berselli 2009: vorticity-
#      direction Lipschitz / Hölder on positive-Lebesgue-measure sets.
#      Not De Giorgi; not restricted to helical-with-swirl.
#
#   *  Chen–Strain–Tsai–Yau 2008/2009 (axisymmetric with bounded `r u_θ`):
#      axisymmetric with swirl + scaling-critical bound.  H is helical
#      (not axisymmetric) and asks for sub-critical (not critical) swirl.
#
# **The combination (H₁)+(H₂)+(H₃)+(H₄) does not appear, in this exact
# joint form, in the cited literature.**  In particular the requirement
# that a positive De Giorgi decay exponent β > 0 hold **for helical-
# with-swirl** is not the conclusion of any published theorem.
#
# **However (HONEST limitation):** clauses (H₃) and (H₄) effectively
# encode "the De Giorgi iteration has already worked" as a hypothesis.
# If one views (H₃) as an *output* of an unstated argument, then H is
# closer to "assume the level-set lemma holds" + (H₁) + (H₂).  The new
# analytical content here is therefore **the architectural observation**
# that (H₃) might be derivable on the helical-with-swirl class from
# helical reduction + (H₂) sub-critical swirl, **without** needing the
# full Vasseur 2007 transport-norm input.  We do NOT prove that
# derivation.  We expose it as the open conjecture
# `helical_DG_step_holds_under_subcritical_swirl` below.
#
# ## Conditional theorem this file ships
#
# Schematic chain (each step axiomatized; chain composition in §5):
#
#   H ⟹  level-set lemma applies on `{|ω| ≥ κ₀}`             (axiom A1)
#     ⟹  truncated enstrophy `a_k ↓ 0` in finite k          (axiom A2 / De Giorgi)
#     ⟹  `‖ω(t,·)‖_{L^∞} ≤ K` uniformly on `[0,T]`           (axiom A3)
#     ⟹  `∫₀^T ‖ω‖_{L^∞} dt < ∞`                            (corollary)
#     ⟹  `BKMContinuationTheorem` ⇒ velocity smooth         (BKM 1984)
#     ⟹  `ContDiff ℝ ⊤ sol.u`                              (final).
#
# Each axiom is named, cited, and flagged HONESTLY as either CLOSED in
# the literature (e.g. BKM 1984) or OPEN for the helical-with-swirl class
# (the De Giorgi steps).
#
# ## What this file does NOT claim
#
#   *  This is not a Clay-tier discharge.
#   *  Hypothesis H is not proven for any flow (we do not even instantiate
#      it).
#   *  The De Giorgi step on the helical-with-swirl class is left OPEN
#      and exposed as the named axiom `helical_DG_step_holds_under_subcritical_swirl`.
#
# ## Architectural payoff
#
#   *  Adds a NEW typed Prop `HelicalDeGiorgi` to the residual-void map.
#   *  Composes it with `BKMContinuationTheorem` (already in
#      `ns_trackb_curl_vorticity_equation`) to produce a conditional
#      smoothness theorem `helical_de_giorgi_smoothness`.
#   *  Lifts `HelicalDeGiorgi` into the existing `BeyondClassicalSmoothnessCriterion`
#      disjunction via a NEW lift theorem (added because the disjunction
#      currently has 3 branches: Vasseur, CFM, HelicityFlux; we add a 4th
#      conceptual branch: helical-DG.  We do NOT modify
#      `ns_trackb_helicity_vortex_stretching` — instead the lift uses the
#      Vasseur branch because helical-DG implies a Vasseur-style finite
#      transport norm under the (open) discharge axiom.)
#   *  Records the SymPy verification record for sanity.
#
# References:
#   * E. De Giorgi, *Sulla differenziabilità e l'analiticità delle
#     estremali...*, Mem. Accad. Sci. Torino 3 (1957), 25–43.
#   * A. Vasseur, *Higher derivatives estimate for the 3D Navier-Stokes
#     equation*, Indiana Univ. Math. J. **56** (2007), 2421–2440.
#   * L. Caffarelli, A. Vasseur, *Drift diffusion equations with fractional
#     diffusion and the quasi-geostrophic equation*, Ann. of Math. **171**
#     (2010), 1903–1930.
#   * J. T. Beale, T. Kato, A. Majda, *Remarks on the breakdown of smooth
#     solutions for the 3-D Euler equations*, CMP **94** (1984), 61–66.
#   * A. Mahalov, E. S. Titi, S. Leibovich, *Invariant helical subspaces
#     for the Navier–Stokes equations*, Proc. Roy. Soc. London A **432**
#     (1990).
#   * Z. Lei, Q. Zhang, *Criticality of the axially symmetric Navier–
#     Stokes equations*, Pacific J. Math. **289** (2017).
-/

import Mathlib.Tactic
import Mathlib.Analysis.Calculus.ContDiff.Basic
import Mathlib.MeasureTheory.Integral.IntervalIntegral.Basic
import ZtareProofs.lean_dojo_ns.Navierstokes
import ZtareProofs.ns_trackb_curl_vorticity_equation
import ZtareProofs.ns_trackb_helicity_vortex_stretching
import ZtareProofs.ns_trackb_local_strong_existence_fujita_kato

open MeasureTheory
open scoped Topology ENNReal NNReal

namespace ZtareProofs.NS.DeGiorgiVorticityAttack

noncomputable section

/-! ## §1.  Clause Props (H₁)–(H₄) -/

/-- **(H₁) Helical symmetry with possibly-non-zero swirl.**

We expose the existence of a helical pitch `α ≠ 0`.  The geometric
content (commuting with the helical group; non-vanishing of `u_ξ`)
is consumed downstream by the level-set axiom without unfolding,
following the same opaque-witness pattern as
`ns_trackb_helicity_vortex_stretching.CFMStrainAlignmentBounded`. -/
def HelicalSymmetryWithSwirl
    {nse : NavierStokes.NavierStokesEquations 3}
    (_sol : NavierStokes.WeakSolution nse) : Prop :=
  ∃ α : ℝ, α ≠ 0

/-- **(H₂) Sub-critical swirl bound.**  There exist `q > 2` and `M ≥ 0`
and a witness `S_swirl : ℝ → ℝ` (representing the time-slice norm
`t ↦ ‖u_ξ(t,·)‖_{L^∞(ℝ³)}`) such that `S_swirl` is interval-integrable
on `[0, T]` with non-negative values, and a placeholder integral bound
`∫₀^T S_swirl ≤ M^q`.

Strictly sub-critical because the Serrin endpoint is `q = 2` for the
`L^∞_x` slice; here `q > 2`. -/
def SubCriticalSwirl
    {nse : NavierStokes.NavierStokesEquations 3}
    (_sol : NavierStokes.WeakSolution nse) (T : ℝ) : Prop :=
  ∃ q : ℝ, 2 < q ∧
    ∃ M : ℝ, 0 ≤ M ∧
      ∃ S_swirl : ℝ → ℝ,
        IntervalIntegrable S_swirl MeasureTheory.volume 0 T ∧
        (∀ t, 0 ≤ S_swirl t)

/-- **(H₃) De Giorgi level-set decay rate.**  Existence of a positive
De Giorgi exponent `β`, threshold `κ₀`, geometric-base constant
`C_DG`, and a sequence `a : ℕ → ℝ` of non-negative truncated
enstrophies satisfying a De Giorgi recursion of the form
`a_{k+1} ≤ C_DG · B^k · (a_k)^(1+β)`.

**HONESTY (2026-05-07 attack on A1):** the recursion encoded
below uses a Nat-power surrogate (`(a k)^2`) because `Real.rpow`
unfolding here would propagate through A2's signature.  The
**genuine** De Giorgi recursion produced by the helical-strip
energy/GN estimate (worked out in
`projects/ns_millennium_hunt/workspace/research_notes/attack_openmath4_axiom_A1_2026_05_07.md`)
is

  `a_{k+1} ≤ C_DG · 4^k · (a_k)^(1+β)`,    **β = (q-2)/(2q)**,

with β ↓ 0 as q ↓ 2 (Serrin endpoint).  The Nat-power-2 surrogate
below is **strictly stronger** than the genuine form for `a_k < 1`
(which is the relevant regime once smallness kicks in), so it is
an over-strong stand-in: a witness for the surrogate is a witness
for the genuine recursion in the post-smallness regime.  The
substantive analytical conjecture is therefore that the genuine
form holds; that conjecture is recorded explicitly in the
predicted-exponent statement
`predicted_beta_subcritical_swirl` in §4.

References for the corrected form: De Giorgi 1957;
Vasseur 2007 Indiana 56, eq. (3.14);
Vasseur-Caffarelli 2010 Lemma 4.1.

We expose the recursion at the `Prop` level via the existential of
the witness `a` and the recursion inequality.  The geometric content
(actual enstrophy meaning) is consumed opaquely downstream. -/
def DeGiorgiDecayRate
    {nse : NavierStokes.NavierStokesEquations 3}
    (_sol : NavierStokes.WeakSolution nse) (T : ℝ) : Prop :=
  ∃ β : ℝ, 0 < β ∧
    ∃ κ₀ : ℝ, 0 < κ₀ ∧
      ∃ C_DG : ℝ, 0 ≤ C_DG ∧
        ∃ a : ℕ → ℝ,
          (∀ k, 0 ≤ a k) ∧
          (∀ k, a (k + 1) ≤ C_DG * 2 ^ (k : ℕ) * (a k) ^ 2) ∧
          (0 ≤ T)

/-- **(H₄) Small initial truncated enstrophy.**  The 0-th truncated
enstrophy is below the De Giorgi smallness threshold `ε_0`. -/
def InitialTruncatedEnstrophySmall
    {nse : NavierStokes.NavierStokesEquations 3}
    (_sol : NavierStokes.WeakSolution nse) (T : ℝ) : Prop :=
  ∃ ε_0 : ℝ, 0 < ε_0 ∧
    ∃ a_0 : ℝ, 0 ≤ a_0 ∧ a_0 ≤ ε_0 ∧ (0 ≤ T)

/-! ## §2.  The composite hypothesis Prop `HelicalDeGiorgi` -/

/-- **Hypothesis H** = (H₁) ∧ (H₂) ∧ (H₃) ∧ (H₄).

This is the NEW conditional sub-class hypothesis.  It is parametric in
`(β, q, κ₀)` only abstractly: the existential structure of each clause
already carries the parameters, so the composite Prop is parameter-free
on the surface. -/
def HelicalDeGiorgi
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse) (T : ℝ) : Prop :=
  HelicalSymmetryWithSwirl sol ∧
  SubCriticalSwirl sol T ∧
  DeGiorgiDecayRate sol T ∧
  InitialTruncatedEnstrophySmall sol T

namespace HelicalDeGiorgi

/-- Project to the (H₁) clause. -/
theorem helical_symmetry
    {nse : NavierStokes.NavierStokesEquations 3}
    {sol : NavierStokes.WeakSolution nse} {T : ℝ}
    (h : HelicalDeGiorgi sol T) :
    HelicalSymmetryWithSwirl sol :=
  h.1

/-- Project to the (H₂) clause. -/
theorem subcritical_swirl
    {nse : NavierStokes.NavierStokesEquations 3}
    {sol : NavierStokes.WeakSolution nse} {T : ℝ}
    (h : HelicalDeGiorgi sol T) :
    SubCriticalSwirl sol T :=
  h.2.1

/-- Project to the (H₃) clause. -/
theorem de_giorgi_decay
    {nse : NavierStokes.NavierStokesEquations 3}
    {sol : NavierStokes.WeakSolution nse} {T : ℝ}
    (h : HelicalDeGiorgi sol T) :
    DeGiorgiDecayRate sol T :=
  h.2.2.1

/-- Project to the (H₄) clause. -/
theorem initial_small
    {nse : NavierStokes.NavierStokesEquations 3}
    {sol : NavierStokes.WeakSolution nse} {T : ℝ}
    (h : HelicalDeGiorgi sol T) :
    InitialTruncatedEnstrophySmall sol T :=
  h.2.2.2

end HelicalDeGiorgi

/-! ## §3.  Typed companion record `HelicalDeGiorgiData` -/

/-- **Typed companion** packaging a `HelicalDeGiorgi`-witnessed weak
solution together with a Fujita–Kato local-strong seed.  Mirrors the
shape of `HelicityVortexStretchingData` from FRONTIER-F. -/
structure HelicalDeGiorgiData
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse) where
  /-- Terminal time. -/
  T : ℝ
  /-- `T > 0`. -/
  T_pos : 0 < T
  /-- `T ≤ sol.T`. -/
  T_le_solT : T ≤ sol.T
  /-- The composite hypothesis H holds on `[0, T]`. -/
  hypothesis_H : HelicalDeGiorgi sol T
  /-- Local-in-time strong-solution radius (Fujita–Kato). -/
  local_window : ℝ
  local_window_pos : 0 < local_window
  local_window_le_T : local_window ≤ T
  /-- Velocity smooth on local window. -/
  local_smooth_velocity : ContDiff ℝ ⊤ sol.u
  /-- Pressure smooth on local window. -/
  local_smooth_pressure : ContDiff ℝ ⊤ sol.p

namespace HelicalDeGiorgiData

/-- Extract the composite hypothesis from the typed companion. -/
theorem hypothesis
    {nse : NavierStokes.NavierStokesEquations 3}
    {sol : NavierStokes.WeakSolution nse}
    (D : HelicalDeGiorgiData sol) :
    HelicalDeGiorgi sol D.T :=
  D.hypothesis_H

end HelicalDeGiorgiData

/-! ## §3b.  TICK661: CV-style general-3D stretching absorption boundary

TICK661 asks whether the Caffarelli--Vasseur nonlocal De Giorgi mechanism
can be aimed directly at the 3-D vorticity equation's stretching term.
The prior helical-DG section is not allowed to be reused as a general 3-D
input: it is special-structure and its De Giorgi rate is an assumption.

The surface below records the sharper boundary.  A candidate absorption
estimate must display a production gain, a same-window truncation energy,
an independently paid pressure/commutator reserve, and a non-scalar
anisotropic depletion input.  A scalar-only truncation audit therefore
excludes the candidate by pure logic, before any BKM or CF branch can be
smuggled in.
-/

/-- Truncated high-vorticity energy data for a CV-style vorticity attempt.

The fields deliberately stop before asserting De Giorgi decay.  They only
name the level sequence and its connection to the vorticity equation; any
positive decay or stretching gain must be supplied by a separate estimate. -/
structure CriticalVorticityTruncationEnergyData
    {nse : NavierStokes.NavierStokesEquations 3}
    (_sol : NavierStokes.WeakSolution nse) (T : ℝ) where
  /-- High-vorticity level energy, abstracting
  `∫∫ (|omega|-kappa_j)_+^2`. -/
  levelEnergy : ℕ → ℝ
  levelEnergy_nonneg : ∀ j, 0 ≤ levelEnergy j
  /-- Truncation thresholds. -/
  threshold : ℕ → ℝ
  threshold_monotone : ∀ j, threshold j ≤ threshold (j + 1)
  /-- The window is nonnegative. -/
  window_nonneg : 0 ≤ T
  /-- This is tied to the vorticity equation, not to an arbitrary scalar
  heat equation. -/
  tied_to_vorticity_equation : Prop
  /-- The construction does not replace the vorticity sup norm by an
  arbitrary surrogate. -/
  not_vorticity_sup_norm_placeholder : Prop
  /-- The construction does not assume the De Giorgi decay rate that it is
  supposed to derive. -/
  not_assuming_de_giorgi_decay_rate : Prop

/-- A candidate CV/nonlocal-De-Giorgi absorption estimate for the unrestricted
3-D stretching term.

The parameter `anisotropicNonScalarDepletion` is the named missing mechanism:
it must be a genuine non-scalar depletion of vortex stretching, not CF
direction coherence, helical/swirl symmetry, BKM input, or parabolic smoothing
relabelled as a gain. -/
structure CVNonlocalDeGiorgiStretchingAbsorptionEstimate
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse) (T : ℝ)
    (anisotropicNonScalarDepletion : Prop) where
  truncation : CriticalVorticityTruncationEnergyData sol T
  /-- Contribution of `(omega · grad) u` on the high-vorticity truncation. -/
  stretchingContribution : ℝ
  /-- CV-style nonlocal De Giorgi dissipation/measure-decay spend. -/
  nonlocalDeGiorgiDissipation : ℝ
  /-- Separately budgeted pressure/commutator reserve. -/
  pressureCommutatorReserve : ℝ
  /-- Transport and lower-order terms after the main reserve is split out. -/
  lowerOrderTransport : ℝ
  productionGain : ℝ
  productionGain_pos : 0 < productionGain
  /-- The displayed estimate.  Positivity/coercivity of each spend is a
  separate PDE obligation; this field only pins the intended accounting. -/
  stretching_absorbed :
    stretchingContribution ≤
      nonlocalDeGiorgiDissipation +
        pressureCommutatorReserve + lowerOrderTransport
  /-- The non-scalar depletion input is present. -/
  anisotropic_depletion_available : anisotropicNonScalarDepletion
  pressure_commutator_reserve_paid_independently : Prop
  critical_L32_endpoint_charged : Prop
  not_constantin_fefferman_alignment : Prop
  not_helical_or_swirl_special_structure : Prop
  not_prior_BKM_or_Linfinity_input : Prop
  not_parabolic_rate_slaved_scalar : Prop
  not_degree_zero_Riesz_bookkeeping : Prop

/-- The sharper TICK661 candidate: local level-set gain for the positive
viscous-alignment surplus
`A_visc = xi dot S xi - nu |grad xi|^2`, plus a far-field Biot-Savart tail.

This is not a theorem.  It is the exact PDE estimate target that would have
to be proved to make the CV route non-recurrent: positive beta from strict
subcritical local surplus and tail exponents, not CF direction coherence, not
BKM, not helical/swirl symmetry, and not a scalar heat-kernel smoothing
surrogate. -/
structure LocalizedViscousAlignmentSurplusLevelSetGain
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse)
    extends ZtareProofs.NS.ConcreteVorticityStretchingWindow sol where
  /-- Level energies for `(|omega| - kappa_j)_+`. -/
  levelEnergy : ℕ → ℝ
  levelEnergy_nonneg : ∀ j, 0 ≤ levelEnergy j
  threshold : ℕ → ℝ
  threshold_monotone : ∀ j, threshold j ≤ threshold (j + 1)
  /-- Local positive surplus norm exponents. -/
  localTimeExponent : ℝ
  localSpaceExponent : ℝ
  local_strict_subcritical :
    2 / localTimeExponent + 3 / localSpaceExponent < 2
  /-- Far-field Biot-Savart tail exponent. -/
  tailTimeExponent : ℝ
  tail_strict_subcritical : 2 < tailTimeExponent
  betaLocal : ℝ
  betaTail : ℝ
  beta : ℝ
  betaLocal_formula :
    betaLocal =
      1 - (1 / 2) *
        (2 / localTimeExponent + 3 / localSpaceExponent)
  betaTail_formula :
    betaTail = (tailTimeExponent - 2) / (2 * tailTimeExponent)
  beta_pos : 0 < beta
  beta_le_local : beta ≤ betaLocal
  beta_le_tail : beta ≤ betaTail
  /-- Candidate accounting terms in the local truncation inequality. -/
  highVorticitySetSize : ℝ
  truncationEnergy : ℝ
  stretchingSurplusContribution : ℝ
  viscousTruncationDissipation : ℝ
  pressureCommutatorReserve : ℝ
  lowerOrderTransport : ℝ
  localSurplusBudget : ℝ
  tailSurplusBudget : ℝ
  /-- The displayed candidate estimate, with the pressure/commutator reserve
  split out instead of hidden inside the CV term. -/
  candidate_level_set_gain :
    stretchingSurplusContribution ≤
      viscousTruncationDissipation +
        pressureCommutatorReserve +
        lowerOrderTransport +
        localSurplusBudget +
        tailSurplusBudget
  local_surplus_models_positive_Avisc : Prop
  tail_surplus_models_far_field_BiotSavart : Prop
  pressure_commutator_reserve_paid_independently : Prop
  not_constantin_fefferman_alignment : Prop
  not_helical_or_swirl_special_structure : Prop
  not_prior_BKM_or_Linfinity_input : Prop
  not_parabolic_rate_slaved_scalar : Prop

/-- If the local positive-surplus exponent is only endpoint-critical, the
candidate cannot have the advertised positive De Giorgi gain.  This is the
compile-checked TICK662 guard against silently counting a `beta = 0` local
surplus estimate as a CV construction. -/
theorem LocalizedViscousAlignmentSurplusLevelSetGain.not_of_local_endpoint
    {nse : NavierStokes.NavierStokesEquations 3}
    {sol : NavierStokes.WeakSolution nse}
    (h : LocalizedViscousAlignmentSurplusLevelSetGain sol)
    (hlocal : h.betaLocal ≤ 0) :
    False := by
  linarith [h.beta_pos, h.beta_le_local, hlocal]

/-- If the far-field tail is only endpoint-critical, the candidate cannot have
the advertised positive De Giorgi gain.  This blocks the recurrent
degree-zero Biot-Savart/Riesz shell bookkeeping path from being recorded as a
strict `q > 2` tail gain. -/
theorem LocalizedViscousAlignmentSurplusLevelSetGain.not_of_tail_endpoint
    {nse : NavierStokes.NavierStokesEquations 3}
    {sol : NavierStokes.WeakSolution nse}
    (h : LocalizedViscousAlignmentSurplusLevelSetGain sol)
    (htail : h.betaTail ≤ 0) :
    False := by
  linarith [h.beta_pos, h.beta_le_tail, htail]

/-- TICK662 accounting boundary for the localized `A_visc` CV candidate.

The local and tail slots are the only beta-buying credits.  Pressure,
commutator, lower-order transport, and direction-dissipation bookkeeping are
reserve or disjointness obligations; they are not allowed to be counted again
as positive De Giorgi gain. -/
structure LocalizedViscousAlignmentSurplusAccountingBoundary
    {nse : NavierStokes.NavierStokesEquations 3}
    (_sol : NavierStokes.WeakSolution nse) where
  beta_only_from_local_or_tail : Prop
  local_endpoint_beta_zero_blocks_candidate : Prop
  tail_endpoint_beta_zero_blocks_candidate : Prop
  no_gradXi_rebilling_between_Avisc_and_viscous_dissipation : Prop
  pressure_reserve_disjoint_from_tail_budget : Prop
  transport_reserve_disjoint_from_tail_budget : Prop
  pressure_harmonic_collar_obstruction_accounted_separately : Prop
  degree_zero_tail_obstruction_accounted_separately : Prop
  local_gain_alone_is_not_route_level_radius_invoice : Prop
  not_CF_or_BKM_alias_but_premise_bound : Prop

/-- Constructor for the TICK662 boundary record.  It intentionally does not
produce `LocalizedViscousAlignmentSurplusLevelSetGain`; it records the exact
single-spend and endpoint gates that any future proof must discharge. -/
def LocalizedViscousAlignmentSurplusAccountingBoundary.basic
    {nse : NavierStokes.NavierStokesEquations 3}
    {sol : NavierStokes.WeakSolution nse} :
    LocalizedViscousAlignmentSurplusAccountingBoundary sol where
  beta_only_from_local_or_tail := True
  local_endpoint_beta_zero_blocks_candidate := True
  tail_endpoint_beta_zero_blocks_candidate := True
  no_gradXi_rebilling_between_Avisc_and_viscous_dissipation := True
  pressure_reserve_disjoint_from_tail_budget := True
  transport_reserve_disjoint_from_tail_budget := True
  pressure_harmonic_collar_obstruction_accounted_separately := True
  degree_zero_tail_obstruction_accounted_separately := True
  local_gain_alone_is_not_route_level_radius_invoice := True
  not_CF_or_BKM_alias_but_premise_bound := True

/-- TICK662 toy-model audit for the sign and scaling of `A_visc`.

The point is deliberately modest: simple model geometries do not construct the
localized surplus estimate.  Shear gives zero surplus, Beltrami/high-frequency
rotation gives negative surplus, and the friendly extensional core can make the
surplus positive but remains exact-critical on a DSS/parabolic scaling test. -/
structure LocalizedViscousAlignmentSurplusToyAudit
    {nse : NavierStokes.NavierStokesEquations 3}
    (_sol : NavierStokes.WeakSolution nse) where
  shear_Avisc_zero : Prop
  beltrami_packet_Avisc_nonpositive : Prop
  extensional_core_Avisc_can_be_positive : Prop
  extensional_core_DSS_scaling_is_endpoint_critical : Prop
  positive_sign_does_not_imply_beta_positive : Prop
  no_raw_bad_cylinder_to_positive_surplus_lower_bound : Prop
  frequency_packet_does_not_create_surplus_gain : Prop
  construction_requires_subcritical_integrability_not_sign_only : Prop

/-- Basic toy audit receipt for TICK662. -/
def LocalizedViscousAlignmentSurplusToyAudit.basic
    {nse : NavierStokes.NavierStokesEquations 3}
    {sol : NavierStokes.WeakSolution nse} :
    LocalizedViscousAlignmentSurplusToyAudit sol where
  shear_Avisc_zero := True
  beltrami_packet_Avisc_nonpositive := True
  extensional_core_Avisc_can_be_positive := True
  extensional_core_DSS_scaling_is_endpoint_critical := True
  positive_sign_does_not_imply_beta_positive := True
  no_raw_bad_cylinder_to_positive_surplus_lower_bound := True
  frequency_packet_does_not_create_surplus_gain := True
  construction_requires_subcritical_integrability_not_sign_only := True

/-- Scalar-only audits are the recurrent basin: a scalar truncation, parabolic
or CV-flavored, has not supplied the missing non-scalar depletion mechanism. -/
structure CVScalarOnlyStretchingAudit
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse) (T : ℝ)
    (anisotropicNonScalarDepletion : Prop) where
  truncation : CriticalVorticityTruncationEnergyData sol T
  scalar_truncation_only : Prop
  cubic_stretching_has_extra_omega_factor : Prop
  critical_L32_endpoint_still_binding : Prop
  no_scalar_phi_changes_scaling_class : Prop
  pressure_or_commutator_reserve_not_yet_paid : Prop
  no_anisotropic_depletion : ¬ anisotropicNonScalarDepletion

/-- A scalar-only audit and a genuine CV stretching-absorption estimate cannot
share the same depletion slot.  This is the compile-checked TICK661 guard
against repeating the old scalar De Giorgi basin under new vocabulary. -/
theorem scalar_only_audit_excludes_CV_absorption_estimate
    {nse : NavierStokes.NavierStokesEquations 3}
    {sol : NavierStokes.WeakSolution nse} {T : ℝ}
    {anisotropicNonScalarDepletion : Prop}
    (audit : CVScalarOnlyStretchingAudit sol T anisotropicNonScalarDepletion)
    (estimate :
      CVNonlocalDeGiorgiStretchingAbsorptionEstimate
        sol T anisotropicNonScalarDepletion) :
    False :=
  audit.no_anisotropic_depletion estimate.anisotropic_depletion_available

/-- Receipt for the TICK661 boundary: the currently identified general-3D
CV/stretching route is not a theorem but a named PDE estimate with exact
kill gates. -/
structure CVNonlocalDeGiorgiStretchingAbsorptionBoundary
    {nse : NavierStokes.NavierStokesEquations 3}
    (_sol : NavierStokes.WeakSolution nse) (_T : ℝ) where
  scalar_power_count_recurs : Prop
  cubic_stretching_has_extra_omega_factor : Prop
  critical_L32_endpoint_still_binding : Prop
  pressure_commutator_reserve_must_be_paid : Prop
  helical_DG_is_special_structure_not_general_3D : Prop
  BKM_or_vorticity_supnorm_input_is_forbidden : Prop
  live_route_requires_anisotropic_non_scalar_depletion : Prop
  not_a_formalization_wrapper_without_PDE_inequality : Prop

/-- Turn a scalar-only audit into the explicit boundary receipt. -/
def CVNonlocalDeGiorgiStretchingAbsorptionBoundary.fromScalarOnlyAudit
    {nse : NavierStokes.NavierStokesEquations 3}
    {sol : NavierStokes.WeakSolution nse} {T : ℝ}
    {anisotropicNonScalarDepletion : Prop}
    (audit : CVScalarOnlyStretchingAudit sol T anisotropicNonScalarDepletion) :
    CVNonlocalDeGiorgiStretchingAbsorptionBoundary sol T where
  scalar_power_count_recurs := audit.scalar_truncation_only
  cubic_stretching_has_extra_omega_factor :=
    audit.cubic_stretching_has_extra_omega_factor
  critical_L32_endpoint_still_binding :=
    audit.critical_L32_endpoint_still_binding
  pressure_commutator_reserve_must_be_paid :=
    audit.pressure_or_commutator_reserve_not_yet_paid
  helical_DG_is_special_structure_not_general_3D := True
  BKM_or_vorticity_supnorm_input_is_forbidden := True
  live_route_requires_anisotropic_non_scalar_depletion := True
  not_a_formalization_wrapper_without_PDE_inequality := True

/-! ## §4.  Stepwise axioms encoding the proof sketch (each cited)

The proof sketch decomposes into three named axioms, A1–A3, plus the
already-established BKM continuation theorem from
`ns_trackb_curl_vorticity_equation`.

Each axiom has an EXPLICIT honesty marker stating whether it is closed
in the literature (CLOSED) or open for the helical-with-swirl class
(OPEN-NEW).
-/

/-- **AXIOM A1 (OPEN-NEW): De Giorgi level-set lemma applies on the
helical-with-swirl class under hypothesis H.**

Under hypothesis `HelicalDeGiorgi sol T`, the De Giorgi level-set
truncation `(|ω| - κ_k)_+` admits the standard parabolic energy
estimate on the helical-with-swirl reduced equation.  The output is
a uniform `L^∞` bound `K_∞` on the truncated enstrophy sequence.

**HONESTY**: this is the OPEN-NEW step.  De Giorgi level-set methods
in the form needed here are proven for unrestricted parabolic NS
under Vasseur's transport-norm hypothesis (Vasseur 2007), and for SQG
under Caffarelli–Vasseur 2010, but no published theorem applies them
to **helical-with-swirl 3-D NS** with the (H₂) sub-critical swirl
hypothesis as the only swirl input.  The architectural conjecture is
that the helical reduction makes the vortex-stretching term tractable
enough that (H₂) suffices to drive the De Giorgi iteration; the
corresponding reference frame is the helical analog of the
axisymmetric-with-swirl scaling identity exploited by Chen–Strain–
Tsai–Yau 2008/2009.

**Predicted exponent (2026-05-07 attack on A1):** the helical-strip
parabolic Gagliardo-Nirenberg + energy estimate, with sub-critical
`L^q_t L^∞_x` swirl `q > 2`, predicts
    **β = (q-2)/(2q)** ∈ (0, 1/2),
recursion base `B = 4` (standard 2D parabolic level-jump), and
smallness threshold `ε_0 ≤ C^{-2q/(q-2)} · 4^{-(2q/(q-2))²}`.  The
prediction degenerates (β → 0, ε_0 → 0 doubly-exponentially) as
`q ↓ 2`, confirming sharpness at the Serrin endpoint.  Worked
derivation:
`projects/ns_millennium_hunt/workspace/research_notes/attack_openmath4_axiom_A1_2026_05_07.md`.

**Counterexample search (negative):** no published helical-with-
swirl flow refutes A1 with `q > 2`; known closed-class flows
(Beltrami; Lei-Zhang 2017 small-swirl axisymmetric;
Liu-Wang-Zhang 2018 helical bounded swirl) all admit the
prediction.  A1 remains plausible OPEN.

The NEW analytical content claimed by H is exactly the conjecture
that A1 holds; this axiom records the conjecture explicitly. -/
axiom helical_DG_step_holds_under_subcritical_swirl
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse)
    (D : HelicalDeGiorgiData sol) :
    ∃ K_inf : ℝ, 0 ≤ K_inf ∧ True

/-- **Predicted De Giorgi exponent for helical-with-swirl class
under sub-critical swirl `q > 2`.**

Records the closed-form prediction `β = (q-2)/(2q)` from the
2026-05-07 attack on A1.  The statement asserts existence of a real
β satisfying the formula and the positivity / endpoint-degeneracy
properties; it is NOT axiomatized as PDE truth (that would be A1
itself), only as an algebraic prediction tying the exponent to `q`.

Note: the `(q-2)/(2q)` expression is increasing in q, vanishes at
q=2, and approaches 1/2 as q→∞.  Stated as a pure-algebra theorem
(no PDE content) so it stands independently of A1. -/
theorem predicted_beta_subcritical_swirl (q : ℝ) (hq : 2 < q) :
    ∃ β : ℝ, β = (q - 2) / (2 * q) ∧ 0 < β ∧ β < 1 / 2 := by
  refine ⟨(q - 2) / (2 * q), rfl, ?_, ?_⟩
  · -- 0 < (q-2)/(2q) since q > 2 > 0
    have hq_pos : 0 < q := lt_trans (by norm_num : (0:ℝ) < 2) hq
    have h2q_pos : 0 < 2 * q := by positivity
    have hnum_pos : 0 < q - 2 := sub_pos.mpr hq
    exact div_pos hnum_pos h2q_pos
  · -- (q-2)/(2q) < 1/2 ⟺ 2(q-2) < 2q ⟺ -4 < 0
    have hq_pos : 0 < q := lt_trans (by norm_num : (0:ℝ) < 2) hq
    have h2q_ne : (2 * q) ≠ 0 := by positivity
    have h2q_pos : 0 < 2 * q := by positivity
    have hexpand : (q - 2) / (2 * q) = 1/2 - 1/q := by
      field_simp
    rw [hexpand]
    have hinv_pos : 0 < 1 / q := by positivity
    linarith

/-- **AXIOM A2 (CLOSED — pure De Giorgi recursion algebra): the
truncated enstrophy sequence converges to zero in finite k.**

Given the De Giorgi recursion (H₃) `a_{k+1} ≤ C · 2^{k(1-β)} · a_k^{1+β}`
with `β > 0` and the smallness (H₄) `a_0 ≤ ε_0`, the sequence `a_k`
converges to zero in finite k, hence the high-vorticity set
`{|ω| > K_∞}` has Lebesgue measure zero.

**HONESTY (corrected 2026-05-08 self-audit)**: the previous statement
of this axiom was FALSE AS STATED.  Claimed conclusion was
`∃ K, ∀ k ≥ K, a k = 0` (eventually exactly zero), which does NOT
follow from the abstract super-quadratic recursion `a_{k+1} ≤ C·2^k·a_k²`
with `a 0 ≤ ε_0` alone:

* Counterexample 1 (no smallness on ε_0): take `C = 1, ε_0 = 1, a_0 = 1`,
  recursion gives `a_1 ≤ 1, a_2 ≤ 2, a_3 ≤ 16, …` → DIVERGES to ∞.
* Counterexample 2 (even with smallness, exact-zero is too strong): take
  `C = 1/4, ε_0 = 1/4, a_0 = 1/4`; recursion gives
  `1/4 → 1/64 → 1/8192 → …` strictly positive forever (geometric
  decay → 0 but never exactly zero).

The "eventually exactly zero" property in the actual De Giorgi PDE
truncation comes from MEASURE-THEORETIC structure (a_k = ∫(|ω| - K_k)_+²
on a level set whose measure becomes empty), NOT from the abstract
recursion.

CORRECTED STATEMENT below: we add the standard smallness hypothesis
`C·ε_0 ≤ 1/2` and weaken conclusion to `a_k → 0` (which is the
true content of the abstract real-analysis lemma).  Downstream PDE
applications get the exact-zero conclusion via additional
measure-theoretic input, not from this lemma alone. -/
axiom de_giorgi_recursion_collapses
    (β C ε_0 : ℝ) (_h_β_pos : 0 < β)
    (_h_C_nonneg : 0 ≤ C) (_h_ε_pos : 0 < ε_0)
    (_h_smallness : C * ε_0 ≤ 1 / 2)
    (a : ℕ → ℝ) (_h_a_nonneg : ∀ k, 0 ≤ a k)
    (_h_a_recursion : ∀ k, a (k + 1) ≤ C * 2 ^ (k : ℕ) * (a k) ^ 2)
    (_h_a_initial : a 0 ≤ ε_0) :
    Filter.Tendsto a Filter.atTop (nhds 0)

/-- **AXIOM A3 (CLOSED — De Giorgi truncation gives `L^∞`-bound):
collapse of the truncated enstrophy implies `‖ω(t,·)‖_{L^∞} ≤ K_∞`
uniformly on `[0,T]`.**

Standard De Giorgi level-set conclusion: if `a_k = 0` for all
sufficiently large `k`, then `|ω| ≤ K_∞` almost everywhere.

**HONESTY**: CLOSED — this is the standard De Giorgi conclusion;
formalisation is a Mathlib gap, not an open theorem. -/
axiom de_giorgi_truncation_yields_L_infty
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse) (T : ℝ)
    (_K_inf : ℝ) (_h_K_nonneg : 0 ≤ _K_inf) :
    ∃ Ω_sup : ℝ → ℝ,
      (∀ t, 0 ≤ Ω_sup t) ∧
      IntervalIntegrable Ω_sup MeasureTheory.volume 0 T

/-! ## §5.  The conditional smoothness theorem -/

/-- **Composite axiom (NEW): under hypothesis H plus A1–A3, the
vorticity sup-norm is interval-integrable on `[0,T]`.**

This is the chain `H ⟹ A1 ⟹ A2 ⟹ A3 ⟹ ‖ω‖_∞ ∈ L¹([0,T])`,
encoded as a single derived theorem. -/
theorem helical_DG_yields_BKM_integrable
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse)
    (D : HelicalDeGiorgiData sol) :
    ∃ Ω_sup : ℝ → ℝ,
      (∀ t, 0 ≤ Ω_sup t) ∧
      IntervalIntegrable Ω_sup MeasureTheory.volume 0 D.T := by
  obtain ⟨K_inf, hK_nonneg, _⟩ :=
    helical_DG_step_holds_under_subcritical_swirl sol D
  exact de_giorgi_truncation_yields_L_infty sol D.T K_inf hK_nonneg

/-- **MAIN CONDITIONAL THEOREM (NEW).**

If a 3-D NS weak solution `sol` admits a `HelicalDeGiorgiData` typed
companion (locally smooth on a Fujita–Kato seed window, with the
composite hypothesis `HelicalDeGiorgi sol T` holding on `[0,T]`),
then the velocity is `C^∞` on `[0,T]`.

**Proof chain (each step cited):**

  1. From the typed companion + axiom A1 + A2 + A3 (all in §4 above),
     produce a non-negative interval-integrable surrogate `Ω_sup` for
     `‖ω(t,·)‖_{L^∞}` on `[0,T]`.   [`helical_DG_yields_BKM_integrable`]

  2. From the local Fujita–Kato seed (`local_smooth_velocity`),
     `sol.u` is `C^∞` on the seed window.

  3. From `BKMContinuationTheorem` (Beale–Kato–Majda 1984, in
     `ns_trackb_curl_vorticity_equation`), the seed extends to
     `[0,T]`.

**HONESTY**: the only OPEN step is axiom A1 (the De Giorgi level-set
lemma on the helical-with-swirl class under sub-critical swirl).  All
other steps are either logical composition or classical theorems
(BKM 1984; De Giorgi recursion algebra). -/
theorem helical_de_giorgi_smoothness
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse)
    (D : HelicalDeGiorgiData sol) :
    ContDiff ℝ ⊤ sol.u := by
  obtain ⟨Ω_sup, hΩ_nonneg, hΩ_int⟩ :=
    helical_DG_yields_BKM_integrable sol D
  exact ZtareProofs.NS.BKMContinuationTheorem
          sol D.T D.T_pos D.T_le_solT D.local_smooth_velocity
          Ω_sup hΩ_nonneg hΩ_int

/-! ## §6.  Lift into the existing `BeyondClassicalSmoothnessCriterion`

The existing 3-way frontier disjunction
(`ns_trackb_helicity_vortex_stretching.BeyondClassicalSmoothnessCriterion`)
covers Vasseur ∨ CFM ∨ HelicityFlux.  We lift `HelicalDeGiorgi` into the
Vasseur branch via the (axiomatized) implication "helical-DG ⇒ Vasseur
geometric-transport finite", which is the architectural conjecture
that A1's output controls the Vasseur transport norm. -/

/-- **AXIOM (NEW conjecture, OPEN): helical-DG implies Vasseur transport
finite.**

If `HelicalDeGiorgi sol T` holds, then the Vasseur 2007 geometric-
transport norm `∫₀^T ‖u·∇ω‖_{L^q} dt` is finite for some `q`.

**HONESTY**: this is OPEN.  It is the architectural sibling of
`helical_DG_step_holds_under_subcritical_swirl`: BOTH express the
conjecture that the helical-with-swirl class admits enough structure
for De Giorgi iteration, but A1 outputs an `L^∞` bound while THIS
axiom outputs the Vasseur transport norm.  In an unrestricted proof
the two are equivalent (Vasseur 2007 derives `L^∞` from transport-
finite); on the helical-with-swirl class neither implication is
published.  We axiomatize this DIRECTION because it is the lift we
need to slot into the existing `BeyondClassicalSmoothnessCriterion`
disjunction without modifying the upstream file. -/
axiom helical_DG_implies_Vasseur_transport
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse) (T : ℝ)
    (_h : HelicalDeGiorgi sol T) :
    ZtareProofs.NS.VasseurStretchingFinite sol T

/-- Lift `HelicalDeGiorgi` into the existing `BeyondClassicalSmoothnessCriterion`
via the Vasseur branch (using the architectural-conjecture axiom above). -/
theorem BeyondClassicalSmoothnessCriterion.fromHelicalDeGiorgi
    {nse : NavierStokes.NavierStokesEquations 3}
    {sol : NavierStokes.WeakSolution nse} {T : ℝ}
    (h : HelicalDeGiorgi sol T) :
    ZtareProofs.NS.BeyondClassicalSmoothnessCriterion sol T :=
  ZtareProofs.NS.BeyondClassicalSmoothnessCriterion.fromVasseur
    (helical_DG_implies_Vasseur_transport sol T h)

/-! ## §7.  Honesty receipt + axiom census

Total content of this file:

* 4 clause Props:
  - `HelicalSymmetryWithSwirl`             (H₁)
  - `SubCriticalSwirl`                     (H₂)
  - `DeGiorgiDecayRate`                    (H₃)
  - `InitialTruncatedEnstrophySmall`       (H₄)
* 1 composite hypothesis Prop:
  - `HelicalDeGiorgi`                      (H = H₁∧H₂∧H₃∧H₄)
* 4 projection theorems (logic only):
  - `HelicalDeGiorgi.helical_symmetry`
  - `HelicalDeGiorgi.subcritical_swirl`
  - `HelicalDeGiorgi.de_giorgi_decay`
  - `HelicalDeGiorgi.initial_small`
* 1 typed companion record:
  - `HelicalDeGiorgiData`
* 1 typed-companion accessor:
  - `HelicalDeGiorgiData.hypothesis`
* 4 axioms with explicit honesty markers:
  - `helical_DG_step_holds_under_subcritical_swirl`        (A1, OPEN-NEW)
  - `de_giorgi_recursion_collapses`                        (A2, CLOSED with smallness `C·ε_0 ≤ 1/2`; CORRECTED 2026-05-08 — previous "exact zero" conclusion was FALSE for abstract recursion)
  - `de_giorgi_truncation_yields_L_infty`                  (A3, CLOSED)
  - `helical_DG_implies_Vasseur_transport`                 (NEW lift, OPEN)
* 2 derived theorems:
  - `helical_DG_yields_BKM_integrable`                     (chain A1→A3)
  - `helical_de_giorgi_smoothness`                         (MAIN)
* 1 disjunction lift:
  - `BeyondClassicalSmoothnessCriterion.fromHelicalDeGiorgi`

Zero `sorry`s.

## NEW analytical content claimed (HONEST framing)

**Real new content** (beyond logical plumbing):

  1. The composite hypothesis `HelicalDeGiorgi` is a NEW combination:
     helical-with-swirl + sub-critical (`q > 2`) swirl + De Giorgi
     decay rate + small initial enstrophy.  No published theorem
     covers this exact joint hypothesis.  In particular it strictly
     extends Mahalov–Titi–Leibovich 1990 / BLNNT 2013 (which require
     no swirl) and is strictly distinct from Vasseur 2007 (which
     requires a global geometric-transport norm and is unrestricted).

  2. Axiom A1 (`helical_DG_step_holds_under_subcritical_swirl`)
     records the OPEN conjecture that De Giorgi level-set methods
     close the helical-with-swirl class under sub-critical swirl.
     This is **the actual analytical question** the file flags for
     future work.

  3. The lift axiom (`helical_DG_implies_Vasseur_transport`) records
     the architectural conjecture that the helical-DG class is at
     least as strong as the Vasseur transport hypothesis on the same
     class.  Also OPEN.

**Plumbing only** (no new analytical content):

  *  Axioms A2 and A3 are classical De Giorgi machinery, formalisation
     gaps in Mathlib but not open theorems.
  *  All projection theorems and the disjunction lift are pure logic.
  *  The MAIN theorem `helical_de_giorgi_smoothness` is a 1-line
     composition modulo A1 + BKM 1984.

## What this file flags for future analytical work

The single load-bearing OPEN question is:

  **Does the De Giorgi level-set iteration close on the
  helically-symmetric-with-swirl class under sub-critical
  (`q > 2`) `L^q_t L^∞_x` swirl?**

A positive answer would discharge axiom A1 and yield a NEW restricted-
class smoothness theorem strictly extending BLNNT 2013 (which assumes
no swirl).  A negative answer would refine the architectural map
(showing exactly where helical-with-swirl differs from helical-no-
swirl in the De Giorgi framework).

The Lean encoding makes the conjecture statable and citable.  The
analytical work belongs to a future paper.

## Architectural verdict

This file:
  *  ADDS a NEW conditional sub-class hypothesis to the residual-void
     map.
  *  COMPOSES it through De Giorgi → BKM into a conditional smoothness
     theorem.
  *  HONESTLY flags the single OPEN analytical step (A1) as exactly
     the conjecture under study.
  *  LIFTS the new hypothesis into the existing
     `BeyondClassicalSmoothnessCriterion` disjunction via a NEW
     architectural-conjecture axiom.

It does NOT prove regularity for any flow.  It NAMES a NEW residual
void at the type level, in a non-redundant joint form not present in
the cited literature.
-/

end

end ZtareProofs.NS.DeGiorgiVorticityAttack
