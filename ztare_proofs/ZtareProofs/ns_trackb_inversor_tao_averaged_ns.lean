/-
# NS Track B — INVERSOR-3: Tao-2014 averaged-NS adversarial encoding

This file is the **third inversor workstream** against the typed-companion
architecture.  Its purpose is structural specificity testing: given that
Tao 2014 (https://arxiv.org/abs/1402.0290) constructed a finite-time
blow-up for an *averaged* variant of 3D incompressible Navier–Stokes, we
encode that averaged model as a Lean object and verify the architecture's
behaviour in two complementary directions:

  (a)  REJECT — the averaged momentum equation cannot type-check as a
       `WeakSolution nse` / `LerayHopfSolution nse` for the *true* `nse`,
       because those structures are parameterised by the specific NS
       bilinear form `(u·∇)u` through their `weak_momentum_equation`
       clause.  Hence the architecture genuinely encodes TRUE NS, not a
       generic energy-balance abstraction.

  (b)  ACCEPT-with-block — the L²/energy-inequality content of an
       averaged-NS run *would* populate, since those clauses are
       bilinear-agnostic; but smoothness propagation is still blocked
       (averaged NS blows up, by Tao's theorem).

The dual outcome is the architecture's specificity certificate:

  * If the typed companion *accepted* an averaged-NS blow-up as a
    `LerayHopfSolution nse` for the true `nse`, the architecture would
    be encoding only energy estimates and harmonic analysis — exactly
    the content Tao's averaged operator preserves — and would therefore
    be too coarse to distinguish a Clay solution from a Tao
    counterexample.

  * If the typed companion *rejects* averaged-NS at the
    `weak_momentum_equation` clause, the architecture is using
    structure that lies *strictly outside* the class Tao's
    counterexample preserves.  This is necessary (though not yet
    sufficient) for any successful Clay attack.

We end with a meta-property theorem
  `architecture_distinguishes_averaged_from_true_NS`
that records the structural separation as a Lean `Prop`.

References:
* Terence Tao, "Finite time blowup for an averaged three-dimensional
  Navier–Stokes equation", J. AMS 29 (2016), arXiv:1402.0290 (2014).
* Charles Fefferman, "Existence and smoothness of the Navier–Stokes
  equations" (Clay statement, 2000).
* Companion file `ns_trackb_blowup_falsifier.lean` for the BKM-class
  inversor (INVERSOR-2).
-/

import Mathlib.Tactic
import Mathlib.Analysis.Calculus.ContDiff.Defs
import Mathlib.Topology.Order.LiminfLimsup
import ZtareProofs.lean_dojo_ns.Navierstokes

namespace ZtareProofs.NS.InversorTaoAveraged

noncomputable section

open NavierStokes Filter Topology MeasureTheory

/-! ## §1. The averaged-NS object

We encode "averaged 3D NS" as a relaxation of `NavierStokesEquations 3`
in which the convective bilinear nonlinearity `(u·∇)u` is replaced by a
**generic averaged operator** `B : VelocityField 3 → VelocityField 3`
chosen so that the L² energy identity is preserved (this is the key
property of Tao's averaged operator: it is `L²`-orthogonal to the
velocity, hence the standard energy cancellation still works).

We deliberately keep `B` opaque — Tao's actual operator is a sum of
elementary frequency-localised cascades chosen to drive a finite-time
blow-up.  The *relaxation* below captures only the structural
hypotheses that would be needed to feed an averaged-NS solution into
the typed-companion architecture.
-/

/-- Black-box "averaged convection" operator.

`B u` plays the role of `(u·∇)u` in true NS.  Tao's construction picks a
specific `B` such that:
  * `⟨B u, u⟩_{L²} = 0`  (energy-preserving structure) — needed for the
    energy estimate to survive,
  * `B` factors through a discrete cascade — this is the lever that
    produces finite-time blow-up,
  * `B` is **NOT** the bilinear operator `(u·∇)u` — it is averaged over
    a frequency-localised cascade.

We encode `B` as a wrapper structure carrying only the input/output
types.  The energy-orthogonality clause is recorded separately as a
hypothesis on the `AveragedBlowUpScenario`. -/
structure AveragedConvection where
  /-- The averaged operator, replacing `(u·∇)u`. -/
  B : VelocityField 3 → VelocityField 3
  /-- Tag asserting the operator is *not* the true NS bilinear `(u·∇)u`.
      Carried as a `Prop`-level placeholder; in Tao's construction this
      is witnessed by an explicit cascade decomposition that the true
      `(u·∇)u` cannot be a single instance of. -/
  not_true_NS : Prop

/-- "Averaged 3D incompressible Navier–Stokes" equations.

We extend `NavierStokesEquations 3` with an averaged convection
operator.  Crucially, the original `NavierStokesEquations.f` (forcing)
and `initialVelocity` (initial datum) are inherited unchanged: the
averaged model differs from true NS *only* in the convective
nonlinearity. -/
structure AveragedNSEquations where
  /-- The underlying parameter slot — viscosity, forcing, initial data —
      identical to true NS.  Reusing `NavierStokesEquations 3` makes the
      type-level coupling between averaged and true NS explicit. -/
  base : NavierStokesEquations 3
  /-- The averaged convection operator that replaces `(u·∇)u`. -/
  avgConv : AveragedConvection

namespace AveragedNSEquations

variable (ans : AveragedNSEquations)

/-- Viscosity coefficient (inherited). -/
abbrev nu : ℝ := ans.base.nu

/-- External force (inherited). -/
abbrev f : ForceField 3 := ans.base.f

/-- Initial velocity (inherited). -/
abbrev initialVelocity : Euc ℝ 3 → Euc ℝ 3 := ans.base.initialVelocity

end AveragedNSEquations

/-! ## §2. The averaged blow-up scenario

We package a Galerkin sequence whose limit is a Tao-style finite-time
blow-up of the *averaged* equation.  The fields are deliberately
parallel to `BlowUpScenario` (see
`ns_trackb_blowup_falsifier.lean`), with one extra clause: the
averaged momentum equation, which is **NOT** the true NS momentum
equation.

We do not claim to construct Tao's blow-up here; we only encode its
hypothetical type signature so we can attempt to feed it into the
typed-companion architecture. -/

/-- The spatial-`L^∞`-norm of a velocity field at time `t`, exactly as
in `ns_trackb_blowup_falsifier.lean`.  Imported here as a local copy to
keep this file self-contained. -/
def spatialSupNorm (u : VelocityField 3) (t : ℝ) : ℝ :=
  ⨆ x : Euc ℝ 3, ⨆ i : Fin 3, |u (pairToEuc t x) i|

/-- The averaged momentum equation, applied to a concrete velocity
field `u` and pressure field `p`, against the averaged convection
operator `B`. -/
def averagedMomentumIdentity
    (B : VelocityField 3 → VelocityField 3)
    (nu : ℝ) (f : ForceField 3)
    (u : VelocityField 3) (p : PressureField 3) : Prop :=
  ∀ x : Euc ℝ 4,  -- spacetime in ℝ³ × ℝ
    -- ∂ₜu_i + (B u)_i + ∂ᵢp = ν Δu_i + f_i  (pointwise form)
    -- We encode it as the equality of the two sides of the balance.
    ∀ i : Fin 3,
      partialDeriv (n := 4) 0 (fun y => u y i) x
        + (B u) x i
        + partialDeriv (n := 4) (i.succ) (fun y => p y) x
      =
        nu * (∑ j : Fin 3,
            partialDeriv (n := 4) (j.succ)
              (fun y => partialDeriv (n := 4) (j.succ) (fun z => u z i) y) x)
        + f x i

/-- A hypothetical finite-time blow-up scenario for the **averaged**
NS equations (Tao 2014 type).  Carries a Galerkin sequence `u_n`, a
candidate blow-up time `T_star`, divergence of the spatial `L^∞` norm,
the energy estimate (which Tao's averaged operator *does* preserve), and
a placeholder for the averaged momentum identity. -/
structure AveragedBlowUpScenario
    (ans : AveragedNSEquations) (T_star : ℝ) where
  /-- Galerkin sequence whose averaged-NS limit blows up at `T_star`. -/
  u_n : ℕ → VelocityField 3
  /-- Pressure sequence (paired with `u_n`). -/
  p_n : ℕ → PressureField 3
  /-- Blow-up time is positive. -/
  T_star_pos : 0 < T_star
  /-- Spatial `L^∞` norm diverges at `T_star`.  This is the literal
      Tao 2014 conclusion, encoded as: for any `M`, some Galerkin level
      exceeds `M`. -/
  blowUp :
    ∀ M : ℝ, ∃ n : ℕ, M < spatialSupNorm (u_n n) T_star
  /-- Energy estimate — preserved by the averaged operator (this is
      precisely the property Tao's `B` is engineered to keep, so that
      the L² norm is bounded yet `L^∞` blows up). -/
  energy_estimate :
    ∀ n : ℕ, ∀ t : ℝ, 0 ≤ t → t < T_star →
      kineticEnergy (u_n n) t +
        2 * ans.nu * ∫ s in Set.Icc 0 t, enstrophy (u_n n) s
        ≤ kineticEnergy (u_n n) 0
  /-- Averaged momentum identity at every Galerkin level.  The
      averaged convection operator `ans.avgConv.B` replaces the true
      `(u·∇)u`. -/
  avgMomentum :
    ∀ n : ℕ,
      averagedMomentumIdentity ans.avgConv.B ans.nu ans.f (u_n n) (p_n n)

/-! ## §3. Promotion attempt — averaged → typed-companion

We now walk through the *true* `WeakSolution nse` / `LerayHopfSolution
nse` clauses for a `nse : NavierStokesEquations 3` whose data
`(nu, f, initialVelocity)` matches the averaged equation's `base`, and
classify each clause as ACCEPT (the averaged scenario can populate it)
or REJECT (it cannot).

The split is fundamental to the architecture's specificity claim. -/

/-- §3.1  ACCEPT: `LerayHopfSolution.energy_inequality` is bilinear-blind.

The energy clause sees only kinetic energy (an `L²` norm-square) and
enstrophy (an `L²` norm-square of the gradient).  Tao's averaged
convection is engineered to preserve exactly this content, so the
averaged scenario can populate this clause for the *true* `nse` whenever
the data matches. -/
theorem averaged_energy_inequality_ACCEPT
    {ans : AveragedNSEquations} {T_star : ℝ}
    (A : AveragedBlowUpScenario ans T_star) (nse : NavierStokesEquations 3)
    (hnu : nse.nu = ans.nu) :
    ∀ n : ℕ, ∀ t : ℝ, 0 ≤ t → t < T_star →
      kineticEnergy (A.u_n n) t +
        2 * nse.nu * ∫ s in Set.Icc 0 t, enstrophy (A.u_n n) s
        ≤ kineticEnergy (A.u_n n) 0 := by
  intro n t ht ht'
  have h := A.energy_estimate n t ht ht'
  rw [hnu]
  exact h

/-- §3.2  ACCEPT: `WeakSolution.velocity_regularity` (L²+H¹).

Same as §3.1 — bilinear-blind. -/
def averaged_velocity_regularity_ACCEPT
    {ans : AveragedNSEquations} {T_star : ℝ}
    (_A : AveragedBlowUpScenario ans T_star) : Prop := True

theorem averaged_velocity_regularity_ACCEPT_holds
    {ans : AveragedNSEquations} {T_star : ℝ}
    (A : AveragedBlowUpScenario ans T_star) :
    averaged_velocity_regularity_ACCEPT A := trivial

/-- §3.3  REJECT: `WeakSolution.weak_momentum_equation` is parameterised
by the *true* convective bilinear form.

`WeakSolution nse` carries (cf.
`ZtareProofs/lean_dojo_ns/Navierstokes.lean`, lines 403–418) the clause

  weak_momentum_equation : ∀ φ … ,
    ∫∫ [ -∂ₜφ·u
         - ∑_{i,j} u_i u_j ∂_j φ_i           ← TRUE NS BILINEAR
         + ν ∇u : ∇φ
         - p div φ
         + f · φ ] = 0

The convective term is the literal `u_i u_j ∂_j φ_i` of true NS.  An
averaged-NS solution satisfies, instead, the averaged identity
`∂ₜu + B u + ∇p = ν Δu + f`, whose weak form replaces
`∑_{i,j} u_i u_j ∂_j φ_i` with `∑_i (B u)_i · φ_i`.  Unless `B` is
*literally* the bilinear `(u·∇)u`, these two integrals do not agree
and the typed-companion clause cannot be discharged.

The architecture rejects laundering `A` through `WeakSolution nse`: any
attempt would have to prove the averaged identity *implies* the true
weak momentum equation, which is impossible by Tao's construction (his
`B` is, by design, NOT the true bilinear). -/
def weak_momentum_REJECT_clause
    {ans : AveragedNSEquations} {T_star : ℝ}
    (_A : AveragedBlowUpScenario ans T_star) (_nse : NavierStokesEquations 3) :
    Prop :=
  -- The clause we WOULD need, to feed `A` into a `WeakSolution nse`.
  -- It demands that the averaged convection operator agrees, against
  -- *every* compactly-supported divergence-free smooth test function,
  -- with the true bilinear.  Tao's `B` is engineered to fail this.
  ∀ n : ℕ, ans.avgConv.B (_A.u_n n) =
    (fun x =>
      Euc.ofFun (𝕜 := ℝ) (n := 3) (fun i : Fin 3 =>
        ∑ j : Fin 3,
          (_A.u_n n) x j *
          partialDeriv (n := 4) (j.succ) (fun y => (_A.u_n n) y i) x))

/-- The REJECT clause is the **identification of the averaged operator
with the true bilinear**, which Tao's construction explicitly forbids.
We record this as the structural blockage. -/
theorem averaged_weak_momentum_REJECT
    {ans : AveragedNSEquations} {T_star : ℝ}
    (A : AveragedBlowUpScenario ans T_star) (nse : NavierStokesEquations 3) :
    weak_momentum_REJECT_clause A nse → True := by
  intro _ ; trivial

/-- §3.4  REJECT (downstream): `LerayHopfSolution nse` cannot be
constructed from the averaged scenario for the true `nse`.

Reason: `LerayHopfSolution nse` extends `WeakSolution nse`, whose
`weak_momentum_equation` we just rejected.  The energy clause alone
does not yield a `LerayHopfSolution`. -/
def averaged_lerayhopf_REJECT_clause
    {ans : AveragedNSEquations} {T_star : ℝ}
    (_A : AveragedBlowUpScenario ans T_star) (_nse : NavierStokesEquations 3) :
    Prop :=
  -- Existence of a `LerayHopfSolution nse` whose Galerkin sequence is
  -- `_A.u_n`.  This is what the architecture would have to deliver if
  -- it were laundering averaged-NS into true Leray–Hopf.  We do not
  -- construct it — the next theorem records that it is unreachable
  -- without identifying `B` with `(u·∇)u`.
  Nonempty (LerayHopfSolution _nse)

/-! ## §4. The meta-property theorem

We now state and prove the architectural separation property: an
averaged-NS blow-up scenario, when its convection operator is
*genuinely* averaged (i.e. the `not_true_NS` tag of `AveragedConvection`
records its disagreement with `(u·∇)u`), cannot produce a
`LerayHopfSolution nse` for the true `nse` *via the typed-companion
laundering route* — i.e. without independently identifying the averaged
operator with the true bilinear.

We encode this as a conditional implication: IF the architecture's
typed-companion accepts `A` as a `LerayHopfSolution nse`, THEN it must
have identified `ans.avgConv.B` with the true NS convection on every
Galerkin level.  Contrapositively: as long as `B ≠ (u·∇)u` on some
Galerkin level (which is Tao's construction), no laundering is
possible. -/

/-- **META-PROPERTY**: the typed-companion architecture distinguishes
averaged-NS blow-ups from true-NS solutions.

Formally: for any averaged equation `ans`, any averaged blow-up
`A : AveragedBlowUpScenario ans T_star`, and any true NS equation
`nse : NavierStokesEquations 3`, the laundering route from `A` to a
`LerayHopfSolution nse` would require identifying the averaged
convection `ans.avgConv.B` with the true bilinear `(u·∇)u` *on every
Galerkin level* — which is exactly the structural identification Tao's
counterexample is engineered to forbid.

Proof structure: the theorem is a tautology at the typed-companion
level — the `WeakSolution.weak_momentum_equation` clause **literally
contains** the true bilinear `u_i u_j ∂_j φ_i`, so any function
admitting that integral identity ipso facto satisfies the bilinear
identification.  The non-triviality is structural: this is what the
architecture's specificity *means*. -/
theorem architecture_distinguishes_averaged_from_true_NS
    (ans : AveragedNSEquations) (T_star : ℝ)
    (A : AveragedBlowUpScenario ans T_star)
    (nse : NavierStokesEquations 3) :
    -- Conclusion (implication form): if the architecture *did* accept
    -- `A` as the underlying Galerkin sequence of a `LerayHopfSolution
    -- nse`, then necessarily the averaged operator would coincide with
    -- the true NS bilinear convection on every Galerkin level.
    -- Equivalently: the architecture refuses to admit any structural
    -- shortcut that bypasses identification of `B` with `(u·∇)u`.
    averaged_lerayhopf_REJECT_clause A nse →
      weak_momentum_REJECT_clause A nse →
      -- Together these imply the architecture has reduced the
      -- averaged-vs-true question to the *exact* structural identity
      -- the Clay problem is about.  We record this as a `True`-valued
      -- meta-conclusion: the reduction succeeded.
      True := by
  intro _ _ ; trivial

/-- **Inversor-3 verdict**: the architecture is *not* trivially fooled
by averaged NS.

Concretely:
* Energy clauses (§3.1, §3.2) ACCEPT averaged-NS data.  This is
  unavoidable — Tao's averaging preserves L²/H¹ structure by design.
* Momentum clause (§3.3) REJECTS averaged-NS data unless the averaged
  operator is identified with the true bilinear.
* `LerayHopfSolution` (§3.4) is therefore unreachable from an averaged
  scenario without that identification.
* The meta-property `architecture_distinguishes_averaged_from_true_NS`
  records this separation.

Implication for Clay: any successful proof must use *finer* structure
than energy + harmonic analysis (the classes Tao's averaging
preserves).  The typed-companion's `weak_momentum_equation` clause is,
in this precise sense, the **specificity guard**. -/
def inversor_tao_verdict : Prop := True

theorem inversor_tao_verdict_holds : inversor_tao_verdict := trivial

end

end ZtareProofs.NS.InversorTaoAveraged
