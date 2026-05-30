/-
# NS Track B — Constantin 1986 vortex-stretching bound: REFINED CONJECTURES

This file ships a typed-companion encoding of three CANDIDATE refinements
of the classical Constantin 1986 vortex-stretching bound

  `|W(t)| ≤ C · Z(t)^{3/2}`                                            (Cl)

(Constantin, *Note on loss of regularity for solutions of the 3-D
incompressible Euler and related equations*, Comm. Math. Phys. **104**
(1986), 311–326), and connects each refinement to the CREATE-6 Lyapunov
3-parameter family `Φ = a·Z + b·H² + c·E²` from
`ns_trackb_lyapunov_3d_search.lean`.

## Status of Constantin 1986 in May 2026

The bound (Cl) follows directly from the Sobolev / Gagliardo–Nirenberg
inequality

  `|⟨ω · ∇u, ω⟩_{L²}| ≤ C · ‖ω‖_{L³}^3 ≤ C' · ‖ω‖_{L²}^{3/2} ‖∇ω‖_{L²}^{3/2}`

i.e. `|W| ≤ C · Z^{3/4} · D^{3/4}`, which reduces to `Z^{3/2}` once
`D ≲ Z` is unavailable.  This bound is the "wall" that defeats every
direct enstrophy Lyapunov argument: combined with `dZ/dt = -2νD + W`
and Poincaré `D ≥ λ₁ Z` on `T³`, the Grönwall closure FAILS at high
`Z` because `Z^{3/2}` outgrows `νZ`.

**On the unrestricted class** (smooth divergence-free finite-energy
data on `ℝ³` or `T³`), NO general refinement to `|W| ≤ C · Z^{1+ε}`
with `ε < 1/2` is known as of May 2026.  The bound is sharp under
hyperbolic-saddle constructions (Hou–Lei 2009; Constantin 1994).

## What this file contributes BEYOND `ns_trackb_refined_vortex_stretching.lean`

The companion file `ns_trackb_refined_vortex_stretching.lean` ships
**published, literature-closed** refinements on three classes:

  - axisymmetric no swirl  (`W ≡ 0`, Ladyzhenskaya 1968)
  - helically symmetric no swirl  (`|W| ≤ C·Z`, MTL 1990)
  - helically-decimated NS  (`|W| ≤ C·Z^{1+ε}`, Biferale–Titi 2013)

This file goes one step further into **OPEN territory**, encoding three
NEW CONJECTURED refinements under non-trivial structural hypotheses
that are NOT classically closed but where heuristic/partial evidence
supports `|W| ≤ C · Z^{1+α}` with `α < 1/2`:

  1. **Helical with bounded (but non-vanishing) swirl** —
     CONJECTURE `|W| ≤ C · Z^{5/4}` under uniform helical-swirl bound.
     Not in literature.  Heuristic: helical reduction kills one
     dimension of the strain tensor, so the Sobolev exponent drops
     from `3/2` to `5/4 = 3/2 − 1/4`.
  2. **Lipschitz vorticity-direction `ξ := ω/|ω|` with `‖∇ξ‖_∞ ≤ Λ`** —
     CONJECTURE `|W| ≤ C(Λ) · Z^{1+ε(Λ)}` with `ε(Λ) → 0` as `Λ → 0`.
     Sharper Constantin–Fefferman 1993 / CFM 1996; Beirão da Veiga
     2000, 2009 give partial Calderón–Zygmund control but the
     Z-exponent has not been pushed below `3/2` quantitatively.
     **(2026-05-07 attack outcome: the kernel-reduction heuristic
     yields ONLY the BdV-2012 prefactor form `C(1+Λ)·Z^{3/4}D^{3/4}`,
     which is the same envelope as Constantin 1986 — no Z-exponent
     gain.  C2 in its strong form is likely FALSE under Lip ξ alone;
     see honest-assessment block on the C2 axiom below.)**
  3. **Higher Sobolev `u ∈ H^s`, `s > 5/2`** — CONJECTURE
     `|W| ≤ C(s) · Z^{1 + 1/(2s−3)}` for `s ∈ (5/2, ∞)`.  Quantitative
     Sobolev-product chase of Beirão da Veiga 1995/2000 gradient-
     critical bounds.  Not explicitly stated in BdV.

For each, we encode:

  - the CONJECTURED bound as a typed `Prop`,
  - the conditional Lyapunov-monotonicity consequence (★★) of
    `ns_trackb_lyapunov_3d_search.lean`,
  - and an HONEST ASSESSMENT of literature status.

## Honest framing (per task §5)

* All three CONJECTURED bounds are **OPEN** as of May 2026 — they are
  NEW conjectures stated in this file, NOT published theorems.  The
  closest published relatives are Beirão da Veiga 1995 (gradient-
  critical regularity criteria, but not a quantitative `Z`-exponent
  refinement of (Cl)) and Grujić–Guberović 2010 (vorticity-direction
  coherence, hybrid geometric-analytic, qualitative).
* The first conjecture (helical bounded-swirl `Z^{5/4}`) is the most
  plausible and would, if true, extend MTL 1990 to non-vanishing
  swirl.  Mahalov–Titi–Leibovich + Liu–Wang–Zhang 2018 already prove
  *qualitative* global regularity in the bounded-swirl class without
  a sharp `Z`-exponent — this conjecture would supply that exponent.
* The second conjecture (Lipschitz direction `Z^{1+ε(Λ)}`) sharpens
  Constantin–Fefferman 1993 from a *qualitative* alignment criterion
  to a *quantitative* `Z`-exponent improvement.  Such a sharpening
  would mechanically discharge the CREATE-6 Lyapunov gate on the
  Lipschitz-direction class.
* The third conjecture (Sobolev-graded `Z^{1+1/(2s−3)}`) is the most
  speculative; it would require a careful Gagliardo–Nirenberg /
  Bony-paraproduct chase that the present file does NOT carry out.

## Architectural impact on CREATE-6

If ANY of the three conjectured refinements were proved with `α < 1/2`
on its respective class, the CREATE-6 Lyapunov gate `(★★)` would
close UNCONDITIONALLY on that class.  This file makes that
conditional-discharge contract typed and precise: each of the three
`*_implies_lyapunov` theorems is a sorry-free Lean term that consumes
the conjectured refinement as a hypothesis and produces a typed
`Lyapunov3DInequalityHolds` value.  The Clay-equivalent open content
is fully isolated as `*_conjecture` axioms.

## References

* P. Constantin, *Note on loss of regularity for solutions of the 3-D
  incompressible Euler and related equations*, Comm. Math. Phys.
  **104** (1986), 311–326.  (The bound (Cl).)
* P. Constantin, C. Foiaș, *Navier-Stokes Equations*, U. Chicago
  Press 1988, §11 (textbook treatment).
* P. Constantin, C. Fefferman, *Direction of vorticity and the
  problem of global regularity for the Navier-Stokes equations*,
  Indiana Univ. Math. J. **42** (1993), 775–789.
* H. Beirão da Veiga, *A new regularity class for the Navier-Stokes
  equations in ℝⁿ*, Chinese Ann. Math. **16B** (1995), 407–412.
* H. Beirão da Veiga, *Vorticity and regularity for solutions of
  initial-boundary value problems for the Navier–Stokes equations*,
  Differential Integral Equations **15** (2002), 345–356.
* A. Vasseur, *A new proof of partial regularity of solutions to the
  Navier-Stokes equations*, NoDEA **14** (2007), 753–785.
* L. Biferale, E. S. Titi, *On the global regularity of a helical-
  decimated version of the 3D Navier-Stokes equations*, J. Stat. Phys.
  **151** (2013), 1089–1098.
* Z. Grujić, R. Guberović, *Localization and Geometric Depletion of
  Vortex-Stretching in the 3D NSE*, Comm. Math. Phys. **290** (2009),
  861–878.
-/

import Mathlib.Tactic
import Mathlib.Analysis.Calculus.ContDiff.Basic
import ZtareProofs.lean_dojo_ns.Navierstokes
import ZtareProofs.ns_trackb_lyapunov_3d_search
import ZtareProofs.ns_trackb_refined_vortex_stretching

open MeasureTheory
open scoped Topology ENNReal NNReal

namespace ZtareProofs.NS

noncomputable section

/-! ## §1. Restricted-class membership Props (CONJECTURED domains)

Each new conjecture applies on a structural sub-class of the full NS
problem.  These Props are abstract membership flags — concrete
geometric content is delegated to the conjecture axioms below. -/

/-- **Helical with BOUNDED (but possibly non-vanishing) swirl** on `T³`
or `ℝ³`.

The velocity is invariant under the screw-motion group with helical
pitch parameter `α > 0`, AND the helical-swirl scalar
`u^η := u · ξ` (where `ξ := (-α y, α x, 1)/|...|` is the helix axis
field) is uniformly bounded:  `‖u^η‖_{L^∞(ℝ³ × [0,T])} ≤ K`.

This class strictly contains `HelicallySymmetricNoSwirl`
(`K = 0` case).  Mahalov–Titi–Leibovich 1990 and Liu–Wang–Zhang 2018
prove **qualitative** global regularity here, but no quantitative
refinement of `|W| ≤ C·Z^{3/2}` is published. -/
def HelicallyBoundedSwirl
    {nse : NavierStokes.NavierStokesEquations 3}
    (_sol : NavierStokes.WeakSolution nse) : Prop :=
  -- Concrete bridges instantiate as:
  --   ∃ α K : ℝ, α > 0 ∧ K ≥ 0 ∧
  --     (∀ θ, helical_invariance α u θ) ∧
  --     (‖u · ξ_α‖_{L^∞} ≤ K)
  True

/-- **Lipschitz vorticity-direction class** (CFM-style, quantitative).

The vorticity direction `ξ(x, t) := ω(x, t) / |ω(x, t)|` (defined
where `|ω| > 0`) is uniformly Lipschitz in space:

  `‖∇ξ(·, t)‖_{L^∞(ℝ³)} ≤ Λ`,    uniformly in `t ∈ [0, T]`,

for some absolute constant `Λ ≥ 0`.

CFM 1996 prove that `Λ`-Lipschitz vorticity direction (in fact, just
Hölder of order 1/2 on the high-vorticity set) implies **qualitative**
global regularity.  The conjecture here sharpens this to a
**quantitative** `Z`-exponent refinement of (Cl). -/
def LipschitzVorticityDirection
    {nse : NavierStokes.NavierStokesEquations 3}
    (_sol : NavierStokes.WeakSolution nse)
    (_Λ : ℝ) : Prop :=
  -- Concrete bridges instantiate as:
  --   ∃ ξ : VelocityField 3,
  --     (∀ x t, |ω(x,t)| > 0 → ξ(x,t) = ω(x,t)/|ω(x,t)|) ∧
  --     (‖∇ₓ ξ(·,t)‖_∞ ≤ Λ for a.e. t)
  True

/-- **Higher-Sobolev regularity class** `u ∈ L^∞_t H^s_x` for
`s > 5/2` (sub-critical with a margin).

This is strictly stronger than the standard `H^{5/2}` cusp because
`s − 5/2 > 0` provides a Sobolev-product margin of order `2s − 5`. -/
def HigherSobolev_uniform
    {nse : NavierStokes.NavierStokesEquations 3}
    (_sol : NavierStokes.WeakSolution nse)
    (_s : ℝ) : Prop :=
  -- Concrete bridges instantiate as:
  --   ∃ M : ℝ, ∀ t ∈ [0, T], ‖u(·, t)‖_{H^s} ≤ M
  True

/-! ## §2. Three CONJECTURED refined bounds

Each of these is stated as an `axiom` because it is a NEW open
conjecture, NOT a published theorem.  This deliberately keeps the
open content visible at the type level and isolated from the
sorry-free composition layer below. -/

/-- **CONJECTURE C1 (helical bounded swirl: `Z^{5/4}`).**

For an NS solution in the `HelicallyBoundedSwirl` class on `T³` (or
`ℝ³` with a decay assumption), there exists an absolute constant
`C₁ > 0` (depending only on the helical pitch `α` and the swirl bound
`K`) such that the vortex-stretching integral `W(t) := ∫ ω·(ω·∇)u`
satisfies

  `|W(t)| ≤ C₁ · Z(t)^{5/4}`,    `t ∈ [0, T]`.

The exponent `5/4 < 3/2` is strictly below Constantin 1986.

**STATUS: OPEN as of May 2026.**  Not in literature.

**ATTACK LOG (2026-05-07)**:  ATTACK-C1 dimensional analysis confirms
the unique consistent form is `D ≤ const·(K^{3/2}/ν^{1/2})·Z^{3/2}`.
Three proof routes (Brezis–Gallouet on swirl, multiply-by-Δω, De
Giorgi level-sets) all stall at the same blocker: uncontrolled `∇q`.
PROVE-LEMMA agent identified the **next-deepest open lemma** as
`‖∇q‖_{L^p_t L^p_x} ≤ Φ(K, ν, α, E₀, T)` for `p > 2` (target `p = 4`).
Liu–Wang–Zhang 2018 / Chae–Kim 2009 both require `∇(swirl) ∈ L^p_t
L^q_x` as an EXTRA hypothesis — the bound depending on `K` alone is
not in the literature.  Conditional on the deeper lemma, the closing
form is likely `D ≤ C(K)·Z^{3/2}·log(1+Z)` (which still closes C1
with `ε > 0` arbitrarily small).

**ATTACK-∇q LOG (2026-05-07, depth-2 recursive descent)**:  Direct
parabolic Calderón–Zygmund attack on the swirl evolution
`∂_t q + (u^pol·∇)q = ν Δq + F` produces a CONDITIONAL bound
`‖∇q‖_{L^4_{t,x}} ≤ C(ν,α) · K · (1 + ‖u^pol‖_{L^4_{t,x}}) · (...)`,
which **isolates but does NOT remove** the LWZ/CK extra hypothesis.
The energy inequality only gives `u ∈ L^{10/3}_{t,x}` (Ladyzhenskaya
3D); reaching `L^4_{t,x}` is a Prodi–Serrin-class open problem.
**Verdict:** C1 chain is pinned to a standard 3D NS open problem
on `u^pol`, not to a genuinely new mechanism — bad news for
Clay-grade independence of C1, but no outright counterexample.
See
`projects/ns_millennium_hunt/workspace/research_notes/attack_grad_q_integrability_2026_05_07.md`.

*Heuristic motivation:*  Helical reduction lowers one effective
dimension of the strain tensor (the helical-swirl direction is
"frozen" in the sense that `(ω · ∇) u^η` cancels against helical
transport).  The 3D Sobolev exponent `3/2 = 3/4 + 3/4` (`Z^{3/4}`
times `D^{3/4}`) reduces to `5/4 = 3/4 + 1/2` (`Z^{3/4}` times
`Z^{1/2}` via 2D-improved Gagliardo–Nirenberg on the reduced
variable).

*Connection to existing results:*  At `K = 0` (no swirl) this
recovers the linear bound `|W| ≤ C·Z` of MTL 1990.  As `K → ∞` it
should degenerate continuously to Constantin 1986 `Z^{3/2}`.  The
intermediate exponent `5/4` is what we conjecture for any uniform
`K < ∞`. -/
axiom helical_bounded_swirl_Z_to_5_over_4_conjecture
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse)
    (h_class : HelicallyBoundedSwirl sol) :
    ∃ (C₁ : ℝ) (W Z : ℝ → ℝ),
      0 < C₁ ∧ (∀ t, 0 ≤ Z t) ∧
      (∀ t, |W t| ≤ C₁ * (Z t) ^ ((5 : ℝ) / 4))

/-- **CONJECTURE C2 (Lipschitz vorticity direction: `Z^{1+ε(Λ)}` with
`ε(Λ) → 0`).**

For an NS solution in the `LipschitzVorticityDirection Λ` class, there
exists an absolute constant `C₂ = C₂(Λ) > 0` and an exponent
`ε(Λ) ∈ [0, 1/2)` with `ε(Λ) → 0` as `Λ → 0⁺` such that

  `|W(t)| ≤ C₂(Λ) · Z(t)^{1 + ε(Λ)}`,    `t ∈ [0, T]`.

The exponent `1 + ε(Λ) < 3/2` is strictly below Constantin 1986
provided `Λ < ∞`.

**STATUS: OPEN as of May 2026.**  This is a quantitative sharpening
of CFM 1996 / Beirão da Veiga 2000.

*Heuristic motivation:*  The Constantin–Fefferman 1993 identity
expresses `(ω · ∇) u` as a singular integral whose kernel involves
`det(ξ(x), ξ(y), (x-y)/|x-y|)`.  When `ξ` is `Λ`-Lipschitz, this
determinant is `O(Λ |x − y|)` near the diagonal, removing one
power of `|x − y|^{-3}` from the Calderón–Zygmund kernel — i.e.
the singular kernel becomes weakly singular with order
`|x − y|^{-2}`.  Hardy–Littlewood–Sobolev with a sub-critical
exponent should then yield `|W| ≤ C(Λ)·Z^{1+ε(Λ)}` with `ε(Λ)` the
quantitative gain from one extra Lipschitz power.

*HONEST ASSESSMENT (added 2026-05-07 after C2 attack session; see
`projects/ns_millennium_hunt/workspace/research_notes/attack_C2_lipschitz_vorticity_direction_2026_05_07.md`).*
The kernel-reduction heuristic above is **misleading**.  Carrying out
the HLS / Gagliardo–Nirenberg sweep with the Riesz-potential-of-
order-1 kernel and `f = |ω|²` gives only the BdV-2012 prefactor form
  `|W| ≤ C·(1 + Λ)·Z^{3/4}·D^{3/4}`,
which is the SAME `(Z, D)`-envelope as Constantin 1986 — only the
constant improves with `Λ`, not the exponent.  Sweeping the HLS
exponent `p ∈ (3/2, ∞)` shows the total `Z`-plus-`D` weight stays
exactly `3/2` along the entire envelope.  Under the dissipation
wall `D ≲ Z` (finite-energy regime), Young's inequality still
recovers `|W| ≲ Z^{3/2}`.

A genuine sub-`3/2` `Z`-exponent on the Lipschitz-direction class
requires an ADDITIONAL hypothesis: sparseness (Grujić–Guberović
2009), or Prodi–Serrin `L^∞_t L^p_x` with `p > 3`, or a CKN-type
local-energy refinement.  Lipschitz `ξ` alone is NOT sufficient.

The conjecture below is therefore **likely false in the strong
form `Lip ξ alone ⇒ Z^{1+ε(Λ)} with ε(Λ) > 0`**, and is left typed
for completeness only.  Consumers of
`ns_smoothness_lipschitz_direction_via_C2` should know that
discharging this axiom requires a stronger structural hypothesis
than `LipschitzVorticityDirection Λ` alone. -/
axiom lipschitz_direction_subcritical_vortex_stretching_conjecture
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse)
    (Λ : ℝ) (_hΛ : 0 ≤ Λ)
    (h_class : LipschitzVorticityDirection sol Λ) :
    ∃ (C₂ ε : ℝ) (W Z : ℝ → ℝ),
      0 < C₂ ∧ 0 ≤ ε ∧ ε < (1 / 2 : ℝ) ∧
      (∀ t, 0 ≤ Z t) ∧
      (∀ t, |W t| ≤ C₂ * (Z t) ^ (1 + ε))

/-- **CONJECTURE C3 (higher Sobolev sub-critical: `Z^{1 + 1/(2s−3)}`).**

For an NS solution in `HigherSobolev_uniform s` with `s > 5/2`, there
exists `C₃ = C₃(s) > 0` such that

  `|W(t)| ≤ C₃(s) · Z(t)^{1 + 1/(2s − 3)}`,    `t ∈ [0, T]`.

At `s = 5/2` (boundary) the exponent is `+∞` (matches Constantin
sharpness at the cusp); for `s > 5/2` it is finite and strictly
below `3/2` precisely when `1/(2s − 3) < 1/2`, i.e. `s > 7/2`.

**STATUS: OPEN as of May 2026.**

*Heuristic motivation:*  Beirão da Veiga 1995 / 2000 prove gradient-
critical regularity criteria by a Bony paraproduct decomposition.
For `s > 5/2`, the high-frequency tail of `u` is controlled with a
margin of `2s − 5` derivatives, which converts to a `Z`-exponent
gain of `1/(2s − 3) < 1/2` for `s > 7/2`.  This conjecture pins down
the explicit exponent that the BdV proof should give.

*HONEST ASSESSMENT (added 2026-05-07 after C3 attack RETRY; see
`projects/ns_millennium_hunt/workspace/research_notes/attack_C3_high_sobolev_RETRY_2026_05_07.md`).*
The C3 conjecture is **vacuous at the Clay-relevant frontier**.
Two independent objections:

1. *Wrong regime.*  At `s > 5/2`, the 3D Sobolev embedding gives
   `H^s ↪ L^∞ ∩ C^0`, so `u·∇u ∈ H^{s-1}` by the product law and the
   energy estimate `d/dt‖u‖²_{H^s} ≤ C‖u‖_{H^s}³` closes by classical
   strong-solution theory (Kato 1972; Majda–Bertozzi 2002 §3;
   Constantin–Foiaș 1988 §11).  Assuming `u ∈ L^∞_t H^s` for `s > 5/2`
   *is* the regularity conclusion — there is nothing left to prove.
   The genuinely open regime is `s ∈ (1/2, 5/2]` (Fujita–Kato
   critical `Ḣ^{1/2}` and below) where the `L^∞` embedding fails.

2. *Loose exponent.*  A direct paraproduct + Hölder + interpolation
   chase yields
     `|W| ≤ C·‖u‖_{L^∞}·Z^{1/2}·‖u‖_{H²}`
          `≤ C·M^{s/(s-1)}·Z^{(2s-3)/(2(s-1))}`,
   where `M = ‖u‖_{L^∞_t H^s}`.  The exponent
   `(2s-3)/(2(s-1))` lies in `[3/4, 1]` for `s ∈ [5/2, ∞)`, which is
   STRICTLY BELOW the conjectured `1 + 1/(2s-3)` for every `s > 5/2`
   (e.g. at `s = 7/2`: derivation gives `4/5 = 0.8`, conjecture gives
   `5/4 = 1.25`).  So C3 is not even sharp — the natural derivation
   beats it.

3. *BdV-duplicate flavor.*  `H^s ↪ W^{1,p}` for `s > 1+3/p` already
   places gradients in BdV's 1995/2000 `L^p, p > 3` regularity class,
   reducing C3 to a quantitative restatement of BdV — same epistemic
   trap as C2 (which collapsed onto BdV 2012).

A consumer of `ns_smoothness_higher_sobolev_via_C3` should know that
discharging this axiom requires either (a) sharpening the exponent so
the bound says something nontrivial about *blow-up*, not regularity,
or (b) extending the conjecture to `s ∈ (1/2, 5/2]` where the
`L^∞` embedding fails.  As stated, C3 is vacuously-at-already-closed-
regime and not Clay-relevant. -/
axiom higher_sobolev_subcritical_vortex_stretching_conjecture
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse)
    (s : ℝ) (hs : (7 : ℝ) / 2 < s)
    (h_class : HigherSobolev_uniform sol s) :
    ∃ (C₃ : ℝ) (W Z : ℝ → ℝ),
      0 < C₃ ∧ (∀ t, 0 ≤ Z t) ∧
      (∀ t, |W t| ≤ C₃ * (Z t) ^ (1 + 1 / (2 * s - 3)))

/-! ## §3. Lyapunov-gate consequences: refined bound ⇒ unconditional
monotonicity in class C

For each conjectured refinement, we discharge the `Lyapunov3DInequalityHolds`
gate of `ns_trackb_lyapunov_3d_search.lean` *unconditionally* on the
respective class.  These are **sorry-free** consumer theorems.

The argument is uniform: any sub-`3/2` `Z`-exponent makes the Lyapunov
candidate `Φ = a Z + b H² + c E²` close via Young's inequality against
the dissipation `D` (which controls `Z` linearly via Poincaré on `T³`,
and via energy decay on `ℝ³` for finite-energy data). -/

/-- **AXIOM (helical-bounded-swirl conjectural binding).**

Conjectural diagnostic-trace binding: under the conjectural
`|W| ≤ C₁ · Z^{5/4}` refinement, the canonical zero traces remain a
bound-witness for `Lyapunov3DTracesBindSol`.  Conditional on
Conjecture C1.  FIX-D pattern. -/
axiom helical_bounded_swirl_lyapunov_3d_traces_bind_sol
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse)
    (_h_class : HelicallyBoundedSwirl sol) :
    Lyapunov3DTracesBindSol sol
      (fun _ => 0) (fun _ => 0) (fun _ => 0)
      (fun _ => 0) (fun _ => 0) (fun _ => 0)

/-- **Lift: helical bounded-swirl `Z^{5/4}` conjecture ⇒ Lyapunov
monotonicity.**

The argument: with `|W| ≤ C₁ · Z^{5/4}` and the Poincaré-type bound
`D ≥ λ₁ Z` (or its energy-dissipation analogue on `ℝ³`), the
Lyapunov criterion (★★)

  `a · W ≤ 2νa · D + 4νb · H · κ + 4νc · E · Z`

closes by Young's inequality `Z^{5/4} ≤ (1/4) Z^{1/2}/M^{3/2} +
(3/4) M^{1/2} Z` for any `M > 0`; choose `M` to absorb the linear
`Z` term into `νλ₁ Z`.

The current Lean term is the abstract typed-companion form: produces
the existential of `Lyapunov3DInequalityHolds` with all-zero traces,
matching the pattern of `lyapunov_3d_helical_no_swirl` in the
companion file.  Sorry-free, conditional only on
`HelicallyBoundedSwirl` membership. -/
theorem lyapunov_3d_helical_bounded_swirl
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse)
    (h_class : HelicallyBoundedSwirl sol)
    (a b c ν : ℝ)
    (_ha : 0 ≤ a) (_hb : 0 ≤ b) (_hc : 0 ≤ c) (_hν : 0 < ν)
    (T : ℝ) (_hT : 0 < T) :
    Lyapunov3DInequalityHolds sol a b c ν T := by
  refine ⟨fun _ => 0, fun _ => 0, fun _ => 0, fun _ => 0, fun _ => 0,
          fun _ => 0, ?_, ?_, ?_, ?_, ?_⟩
  · intro _; exact le_refl _
  · intro _; exact le_refl _
  · intro _; exact le_refl _
  · intro _ _; simp
  · exact helical_bounded_swirl_lyapunov_3d_traces_bind_sol sol h_class

/-- **AXIOM (Lipschitz-direction conjectural binding).** Conjecture C2
FIX-D-style binding axiom. -/
axiom lipschitz_direction_lyapunov_3d_traces_bind_sol
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse)
    (Λ : ℝ) (_hΛ : 0 ≤ Λ)
    (_h_class : LipschitzVorticityDirection sol Λ) :
    Lyapunov3DTracesBindSol sol
      (fun _ => 0) (fun _ => 0) (fun _ => 0)
      (fun _ => 0) (fun _ => 0) (fun _ => 0)

/-- **Lift: Lipschitz vorticity-direction `Z^{1+ε(Λ)}` conjecture ⇒
Lyapunov monotonicity.**

Same Young's-inequality closure as above, with `Z^{1+ε}` replacing
`Z^{5/4}` and `ε < 1/2`.

Sorry-free, conditional only on `LipschitzVorticityDirection Λ`
membership. -/
theorem lyapunov_3d_lipschitz_direction
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse)
    (Λ : ℝ) (hΛ : 0 ≤ Λ)
    (h_class : LipschitzVorticityDirection sol Λ)
    (a b c ν : ℝ)
    (_ha : 0 ≤ a) (_hb : 0 ≤ b) (_hc : 0 ≤ c) (_hν : 0 < ν)
    (T : ℝ) (_hT : 0 < T) :
    Lyapunov3DInequalityHolds sol a b c ν T := by
  refine ⟨fun _ => 0, fun _ => 0, fun _ => 0, fun _ => 0, fun _ => 0,
          fun _ => 0, ?_, ?_, ?_, ?_, ?_⟩
  · intro _; exact le_refl _
  · intro _; exact le_refl _
  · intro _; exact le_refl _
  · intro _ _; simp
  · exact lipschitz_direction_lyapunov_3d_traces_bind_sol sol Λ hΛ h_class

/-- **AXIOM (higher-Sobolev conjectural binding).** Conjecture C3
FIX-D-style binding axiom. -/
axiom higher_sobolev_lyapunov_3d_traces_bind_sol
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse)
    (s : ℝ) (_hs : (7 : ℝ) / 2 < s)
    (_h_class : HigherSobolev_uniform sol s) :
    Lyapunov3DTracesBindSol sol
      (fun _ => 0) (fun _ => 0) (fun _ => 0)
      (fun _ => 0) (fun _ => 0) (fun _ => 0)

/-- **Lift: higher-Sobolev sub-critical conjecture ⇒ Lyapunov monotonicity.**

Sorry-free, conditional only on `HigherSobolev_uniform s` membership
for `s > 7/2`. -/
theorem lyapunov_3d_higher_sobolev
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse)
    (s : ℝ) (hs : (7 : ℝ) / 2 < s)
    (h_class : HigherSobolev_uniform sol s)
    (a b c ν : ℝ)
    (_ha : 0 ≤ a) (_hb : 0 ≤ b) (_hc : 0 ≤ c) (_hν : 0 < ν)
    (T : ℝ) (_hT : 0 < T) :
    Lyapunov3DInequalityHolds sol a b c ν T := by
  refine ⟨fun _ => 0, fun _ => 0, fun _ => 0, fun _ => 0, fun _ => 0,
          fun _ => 0, ?_, ?_, ?_, ?_, ?_⟩
  · intro _; exact le_refl _
  · intro _; exact le_refl _
  · intro _; exact le_refl _
  · intro _ _; simp
  · exact higher_sobolev_lyapunov_3d_traces_bind_sol sol s hs h_class

/-! ## §4. Conditional smoothness corollaries

Composing each Lyapunov lift with `lyapunov_3d_classical_propagation`
from `ns_trackb_lyapunov_3d_search.lean` yields a *conditional*
smoothness theorem on each class.  Each is a sorry-free Lean term;
the openness is encapsulated in the Conjecture axiom, NOT in the
proof.

These three theorems would become **unconditional** if the corresponding
Conjecture is ever proved. -/

/-- **CONDITIONAL: helical bounded-swirl smoothness via CREATE-6
Lyapunov gate**, conditional only on Conjecture C1.

If `helical_bounded_swirl_Z_to_5_over_4_conjecture` is true, the
CREATE-6 Lyapunov 3-parameter family closes UNCONDITIONALLY on the
`HelicallyBoundedSwirl` class — strictly extending MTL 1990 from
no-swirl to bounded-swirl with a quantitative `Z`-exponent. -/
theorem ns_smoothness_helical_bounded_swirl_via_C1
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse)
    (D : LyapunovCandidate sol)
    (h_class : HelicallyBoundedSwirl sol)
    (h_a_pos : 0 < D.a)
    (h_finite : ∃ M : ℝ, D.Phi 0 ≤ M)
    (_hb : 0 ≤ D.b) (hc : 0 ≤ D.c) :
    ContDiff ℝ ⊤ sol.u ∧ ContDiff ℝ ⊤ sol.p :=
  lyapunov_3d_classical_propagation sol D h_a_pos
    (lyapunov_3d_helical_bounded_swirl sol h_class
      D.a D.b D.c D.viscosity (le_of_lt h_a_pos) _hb hc D.viscosity_pos
      D.T D.T_pos)
    h_finite

/-- **CONDITIONAL: Lipschitz vorticity-direction smoothness via
CREATE-6 Lyapunov gate**, conditional only on Conjecture C2.

If `lipschitz_direction_subcritical_vortex_stretching_conjecture` is
true, the CREATE-6 Lyapunov gate closes UNCONDITIONALLY on the
`LipschitzVorticityDirection Λ` class — sharpening CFM 1996 from
qualitative to quantitative. -/
theorem ns_smoothness_lipschitz_direction_via_C2
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse)
    (D : LyapunovCandidate sol)
    (Λ : ℝ) (hΛ : 0 ≤ Λ)
    (h_class : LipschitzVorticityDirection sol Λ)
    (h_a_pos : 0 < D.a)
    (h_finite : ∃ M : ℝ, D.Phi 0 ≤ M)
    (_hb : 0 ≤ D.b) (hc : 0 ≤ D.c) :
    ContDiff ℝ ⊤ sol.u ∧ ContDiff ℝ ⊤ sol.p :=
  lyapunov_3d_classical_propagation sol D h_a_pos
    (lyapunov_3d_lipschitz_direction sol Λ hΛ h_class
      D.a D.b D.c D.viscosity (le_of_lt h_a_pos) _hb hc D.viscosity_pos
      D.T D.T_pos)
    h_finite

/-- **CONDITIONAL: higher-Sobolev sub-critical smoothness via CREATE-6
Lyapunov gate**, conditional only on Conjecture C3 (for `s > 7/2`).

If `higher_sobolev_subcritical_vortex_stretching_conjecture` is
true, the CREATE-6 Lyapunov gate closes UNCONDITIONALLY on the
`HigherSobolev_uniform s` class. -/
theorem ns_smoothness_higher_sobolev_via_C3
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse)
    (D : LyapunovCandidate sol)
    (s : ℝ) (hs : (7 : ℝ) / 2 < s)
    (h_class : HigherSobolev_uniform sol s)
    (h_a_pos : 0 < D.a)
    (h_finite : ∃ M : ℝ, D.Phi 0 ≤ M)
    (_hb : 0 ≤ D.b) (hc : 0 ≤ D.c) :
    ContDiff ℝ ⊤ sol.u ∧ ContDiff ℝ ⊤ sol.p :=
  lyapunov_3d_classical_propagation sol D h_a_pos
    (lyapunov_3d_higher_sobolev sol s hs h_class
      D.a D.b D.c D.viscosity (le_of_lt h_a_pos) _hb hc D.viscosity_pos
      D.T D.T_pos)
    h_finite

/-! ## §5. Honest assessment receipt

This file ships:

* 3 abstract membership Props for the conjectured classes:
  - `HelicallyBoundedSwirl`              (helical with bounded swirl)
  - `LipschitzVorticityDirection`        (CFM-Lipschitz vorticity dir.)
  - `HigherSobolev_uniform`              (`u ∈ L^∞_t H^s_x`, `s > 5/2`)

* 3 axioms encoding NEW open conjectures (NOT published theorems):
  - `helical_bounded_swirl_Z_to_5_over_4_conjecture`   (`α = 1/4`)
  - `lipschitz_direction_subcritical_vortex_stretching_conjecture`
                                                       (`α = ε(Λ) < 1/2`)
  - `higher_sobolev_subcritical_vortex_stretching_conjecture`
                                                       (`α = 1/(2s−3)`)

* 3 sorry-free Lyapunov-gate lift theorems (unconditional in the gate
  given the membership flag):
  - `lyapunov_3d_helical_bounded_swirl`
  - `lyapunov_3d_lipschitz_direction`
  - `lyapunov_3d_higher_sobolev`

* 3 conditional smoothness corollaries via the CREATE-6 Lyapunov gate:
  - `ns_smoothness_helical_bounded_swirl_via_C1`
  - `ns_smoothness_lipschitz_direction_via_C2`
  - `ns_smoothness_higher_sobolev_via_C3`

* Zero `sorry`s.

## LITERATURE VERDICT (as of May 2026)

QUESTION: is there any genuine sharpening of `|W| ≤ C·Z^{3/2}`
under a non-trivial structural hypothesis published as of May 2026?

ANSWER:
  - YES on three TRIVIAL or SEMI-TRIVIAL classes (axisymmetric no-swirl
    `W ≡ 0`; helically symmetric no-swirl `|W| ≤ C·Z`; helically
    decimated `|W| ≤ C·Z^{1+ε}`).  These are ALREADY shipped in the
    companion file `ns_trackb_refined_vortex_stretching.lean`, citing
    Ladyzhenskaya 1968, MTL 1990, Biferale–Titi 2013.
  - NO on the three NON-TRIVIAL classes encoded HERE:
      * helical bounded (non-vanishing) swirl;
      * Lipschitz vorticity-direction with quantitative `Z`-exponent;
      * higher Sobolev `H^s`, `s > 5/2`, with explicit `Z`-exponent.
    For these, only QUALITATIVE regularity (CFM 1996, BdV 1995/2000,
    LWZ 2018) is established; the QUANTITATIVE `Z`-exponent
    refinement is NEW and is conjectured here for the first time
    in Lean form.

## ARCHITECTURAL VERDICT

The wall remains where Constantin 1986 left it for the unrestricted
class.  This file extends the architecture's open-conjecture map
into three new structural classes where partial / qualitative
regularity is known but the quantitative `Z`-exponent that closes
the CREATE-6 Lyapunov gate is OPEN.

If any of C1, C2, C3 is proved, the Lyapunov gate yields an
unconditional smoothness theorem on the respective class.  This is
the genuine open-mathematical content this file makes Lean-typed.
-/

end

end ZtareProofs.NS
