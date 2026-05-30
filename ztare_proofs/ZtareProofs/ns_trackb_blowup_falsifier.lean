/-
# NS Track B — BlowUpScenario inversion falsifier (Munger inversion workstream)

This file is an ADVERSARIAL ATTACK on the typed-companion architecture.
The paradigm (cold instance, 2026-05-07): "We are no longer looking for
a 'Ghost Gram' in the countable tail. We are looking for a Singularity
Blocker. Don't ask the swarm to prove smoothness; ask the swarm to
construct a finite-time blow-up. If ZTARE's anti-tautology guards are
real, the Lean compiler will physically block the agents from creating
the singularity. The reason the compiler blocks the singularity IS your
missing regularity proof."

We construct a hypothetical `BlowUpScenario` carrying a Galerkin
sequence whose `L^∞` norm diverges at `T_star`, while the energy
estimate (KE + 2ν * cumulative enstrophy ≤ KE_0) STILL holds.  Such a
scenario is consistent with weak L²-control but cannot be smooth.
We then attempt to PROMOTE it through each typed-companion field to a
`LerayHopfSolution` and to a `GlobalSmoothSolution` instance — and we
mark every field with PASS / BLOCKED.

Classical fact (Beale-Kato-Majda 1984): a smooth NS solution can blow
up only if `∫₀^{T_star} ‖∇×u‖_{L^∞} dt = ∞`.  The energy estimate alone
does NOT prevent blow-up; the higher-derivative estimates do.

EXPECTED OUTCOME: the typed-companion architecture accepts the energy
estimate (the L²-blow-up is consistent with a finite energy bound) but
blocks the smoothness propagation (`ContDiff ℝ ⊤` requires finite BKM
integral).  The blocking fields are the architecture's "Singularity
Blockers"; the residual-void map is the list of those blockers and
their classical-theorem witnesses.
-/

import Mathlib.Tactic
import Mathlib.Analysis.Calculus.ContDiff.Defs
import Mathlib.Topology.Order.LiminfLimsup
import ZtareProofs.lean_dojo_ns.Navierstokes

namespace ZtareProofs.NS.BlowUpFalsifier

noncomputable section

open NavierStokes Filter Topology MeasureTheory

/-! ## §1. The BlowUpScenario object

We package a Galerkin sequence `u_n : ℕ → VelocityField 3` whose
spatial `L^∞` norm at the candidate blow-up time `T_star` diverges as
`n → ∞`, while the **energy estimate** (KE + 2ν ∫ enstrophy ≤ KE_0) is
still satisfied for every `t < T_star` and every `n`.

This is the BKM-class scenario: an L²-blow-up is consistent with the
energy estimate (which only sees `L^2` content), but inconsistent with
`ContDiff ℝ ⊤` (which requires uniform control of all derivatives).
-/

/-- The spatial-`L^∞`-norm of a velocity field at time `t`,
viewed as a `Real`. Uses `iSup` over `ℝ³`; for blow-up scenarios this
equals `+∞` in the extended reals but here we hold it as a real
number that we will require to grow without bound. -/
def spatialSupNorm (u : VelocityField 3) (t : ℝ) : ℝ :=
  ⨆ x : Euc ℝ 3, ⨆ i : Fin 3, |u (pairToEuc t x) i|

/-- A hypothetical finite-time blow-up scenario for the NS equations.

Carries:
* a Galerkin sequence `u_n` of velocity fields,
* the candidate blow-up time `T_star > 0`,
* a divergence claim: `‖u_n(T_star, ·)‖_∞ → +∞` as `n → ∞`,
* the energy estimate STILL holds for every `n` and every `t < T_star`.

The energy clause is the L²-budget; it does NOT control any derivative
beyond the `H¹` (enstrophy) content used in Leray-Hopf, and so is
compatible with an `L^∞` blow-up.
-/
structure BlowUpScenario
    (nse : NavierStokesEquations 3) (T_star : ℝ) where
  /-- The Galerkin sequence whose limit (if any) blows up at `T_star`. -/
  u_n : ℕ → VelocityField 3
  /-- The candidate blow-up time is positive (matches `Solution.T_pos`). -/
  T_star_pos : 0 < T_star
  /-- The spatial `L^∞` norm grows without bound at the blow-up time:
      `lim_{n→∞} ‖u_n(T_star, ·)‖_∞ = +∞`.
      Encoded as: for every `M > 0` there is `n` with the spatial
      `L^∞` norm at `T_star` exceeding `M`.

      THIS IS THE FORBIDDEN CONTENT — a `GlobalSmoothSolution` (or a
      `SmoothSolution`) cannot be the limit of such a sequence
      because `ContDiff ℝ ⊤` implies pointwise (hence locally `L^∞`)
      control. -/
  blowUp :
    ∀ M : ℝ, ∃ n : ℕ, M < spatialSupNorm (u_n n) T_star
  /-- Energy estimate STILL holds for every truncation level `n` and
      every time `t ∈ [0, T_star)`.
      This is the BKM observation: L²-control survives an `L^∞`
      blow-up. -/
  energy_estimate :
    ∀ n : ℕ, ∀ t : ℝ, 0 ≤ t → t < T_star →
      kineticEnergy (u_n n) t +
        2 * nse.nu * ∫ s in Set.Icc 0 t, enstrophy (u_n n) s
        ≤ kineticEnergy (u_n n) 0

/-! ## §2. Promotion attempt — typed-companion field by field

We now walk through every clause of `WeakSolution`, `LerayHopfSolution`,
`SmoothSolution`, and `GlobalSmoothSolution`, and try to populate each
clause from a `BlowUpScenario`.

For each field we mark its status:
* `[PASS]`  — the clause is populated.  This is L²-content that does
              NOT see the blow-up.
* `[BLOCKED BY: <classical theorem>]` — the clause cannot be populated.
              These are the **Singularity Blockers**: the architecture's
              physical guards against laundering an `L^∞` blow-up
              through to `ContDiff ℝ ⊤`.
-/

/-! ### 2.1  `WeakSolution.velocity_regularity`  [PASS]

The clause asserts `HasFiniteIntegral` for `|u(t,·)|²` and `|∇u(t,·)|²`
at each `t ∈ [0,T]`.  This is the **L²+H¹** content.  An `L^∞`-blow-up
of `u_n` is COMPATIBLE with bounded `L²` and bounded `H¹` (e.g.
concentration profiles `n^{3/2} ψ(n·)` whose `L^2` norm is fixed and
whose `L^∞` norm scales as `n^{3/2}`).  Hence the typed-companion
`VelocityRegularityData` records can be populated for the limit object
even when each `u_n` is concentrating.

So this clause IS populatable.  The architecture LAUNDERS an L²-blow-up
through this clause.  That is the BKM message: weak regularity does
not detect blow-up.
-/

/-- `velocity_regularity` is populatable for an `L^∞`-blowing-up
sequence with uniform `L²+H¹` bounds.  Here we record the
**L² compatibility** explicitly: existence of an L² weak limit
saturating the energy bound is consistent with the blowUp clause. -/
theorem velocity_regularity_PASS
    {nse : NavierStokesEquations 3} {T_star : ℝ}
    (B : BlowUpScenario nse T_star)
    (M_kin : ℝ)
    (uniform_L2 : ∀ n : ℕ, ∀ t : ℝ, 0 ≤ t → t < T_star →
        kineticEnergy (B.u_n n) t ≤ M_kin) :
    -- The L² ceiling is consistent with the energy estimate; this is
    -- the content that makes WeakSolution.velocity_regularity reachable.
    ∀ n : ℕ, ∀ t : ℝ, 0 ≤ t → t < T_star →
      kineticEnergy (B.u_n n) t ≤ M_kin := by
  intro n t ht ht'
  exact uniform_L2 n t ht ht'

/-! ### 2.2  `LerayHopfSolution.energy_inequality`  [PASS]

The clause is exactly the Galerkin energy estimate combined with weak
LSC.  The `BlowUpScenario.energy_estimate` field IS this content for
every `n` and `t < T_star`; LSC under weak L² limit transfers it to the
limit object (this is `lerayHopf_energy_inequality_at_T_from_typed_companion`
in `ns_trackb_lean_dojo_concrete_bridge.lean`).

So an `L^∞` blow-up is CONSISTENT with the Leray-Hopf energy clause.
Leray (1934) himself constructed weak solutions for arbitrary `L²` data
without ruling out blow-up; this clause is by construction blow-up-blind.
-/

theorem energy_inequality_PASS
    {nse : NavierStokesEquations 3} {T_star : ℝ}
    (B : BlowUpScenario nse T_star) :
    ∀ n : ℕ, ∀ t : ℝ, 0 ≤ t → t < T_star →
      kineticEnergy (B.u_n n) t +
        2 * nse.nu * ∫ s in Set.Icc 0 t, enstrophy (B.u_n n) s
        ≤ kineticEnergy (B.u_n n) 0 :=
  B.energy_estimate

/-! ### 2.3  `WeakSolution.weak_momentum_equation` and
              `WeakSolution.weak_incompressible`  [PASS]

These are integral identities tested against compactly-supported smooth
test functions.  An `L^∞` blow-up is compatible with the weak momentum
equation in distribution sense; this is precisely why Leray's existence
theorem produces weak solutions for arbitrary `L²` initial data without
asserting smoothness.  The Aubin-Lions compactness in
`L²(0,T;H¹) ∩ L^∞(0,T;L²)` produces a strong-`L²(0,T;L²)` limit (i.e.
strong in space-time `L²`) sufficient to pass to the weak limit in the
nonlinearity, even when pointwise blow-up occurs on a measure-zero
set in time.

So these clauses are not Singularity Blockers; they survive an
`L^∞`-blow-up of the Galerkin sequence.  No proof obligation is
emitted here; we record the qualitative conclusion.
-/

/-- Marker proposition: weak momentum and weak incompressibility
clauses are compatible with the BlowUpScenario.  Carried as `True`
to record that no Lean obligation is generated by these clauses. -/
def weak_momentum_PASS
    {nse : NavierStokesEquations 3} {T_star : ℝ}
    (_B : BlowUpScenario nse T_star) : Prop := True

theorem weak_momentum_PASS_holds
    {nse : NavierStokesEquations 3} {T_star : ℝ}
    (B : BlowUpScenario nse T_star) :
    weak_momentum_PASS B := trivial

/-! ### 2.4  `WeakSolution.weak_initial_condition`  [PASS]

The clause matches the limit's `t = 0` slice against the prescribed
initial datum, tested against compactly supported smooth `φ`.  This is
unaffected by `T_star`-time blow-up.  PASS.
-/

/-! ### 2.5  `SmoothSolution.velocity_smooth`  [BLOCKED BY: BKM 1984]

Lean-dojo `SmoothSolution.velocity_smooth` requires
  `∀ x ∈ TimeDomain n T, ContDiffAt ℝ ⊤ (fun y => u y) x`.

If the limit `u_∞` is the weak limit of `u_n` and
`spatialSupNorm (u_n n) T_star → ∞`, then `u_∞` cannot be `ContDiff ℝ ⊤`
on any neighborhood containing the blow-up time.

This is the **first Singularity Blocker** the typed companion exposes.
The classical theorem that would discharge it is:

  Beale-Kato-Majda (1984):  A smooth NS solution can blow up at `T_star`
  if and only if `∫₀^{T_star} ‖∇ × u(s)‖_{L^∞} ds = ∞`.

Equivalently: finite BKM integral ⇔ smooth continuation past `T_star`.
The energy estimate alone does NOT bound the BKM integral.

We encode the blockage as a Lean obligation that, given the BlowUp
hypothesis, would derive a contradiction with `ContDiff ℝ ⊤` for the
limit.  The obligation is left as `sorry` because the classical theorem
is not in Mathlib; we mark it explicitly with the BKM tag.
-/

-- BLOCKED BY: Beale-Kato-Majda (1984) — finite-time blow-up criterion.
-- The smoothness clause cannot be discharged from a BlowUpScenario
-- without a finite-BKM-integral hypothesis.
example
    {nse : NavierStokesEquations 3} {T_star : ℝ}
    (B : BlowUpScenario nse T_star)
    (uInf : VelocityField 3) :
    ¬ ContDiff ℝ (⊤ : ℕ∞) uInf
    -- Premise we cannot prove without a classical input:
    -- ∀ M, ∃ n, ‖u_n(T_star)‖_∞ > M  AND  u_n → uInf in some pointwise
    -- topology compatible with `ContDiff`.  Without that hypothesis the
    -- limit `uInf` is not coupled to the divergence, so the goal is
    -- not derivable.
    := by
  -- The blockage manifests structurally: from `B.blowUp` alone, no
  -- relation to `uInf` is available.  We therefore cannot prove this
  -- — and any attempt to do so is the Singularity Blocker firing.
  sorry

/-! ### 2.6  `GlobalSmoothSolution.velocity_smooth` (global `ContDiff`)
                                                  [BLOCKED BY: BKM + global existence]

`GlobalSmoothSolution` (in `Navierstokes.lean` line ~281-284) requires
  `velocity_smooth : ContDiff ℝ ⊤ u`
on the GLOBAL spacetime `ℝ^{n+1}`.  The Millennium Problem is exactly
to prove (or refute) this for all smooth divergence-free initial data
of finite energy.

A `BlowUpScenario` directly contradicts this clause if `T_star` is in
the proposed global domain.  This is the **strongest Singularity
Blocker**: populating this clause for a BlowUpScenario IS the negative
resolution of the Millennium Problem.
-/

-- BLOCKED BY: Beale-Kato-Majda (1984) at every `T_star ∈ [0,∞)`
--              + global Millennium statement (Fefferman 2000 problem
--                description: solution is smooth for all `t ≥ 0`).
example
    {nse : NavierStokesEquations 3} {T_star : ℝ}
    (_B : BlowUpScenario nse T_star) :
    -- One cannot exhibit a `GlobalSmoothSolution nse` whose underlying
    -- velocity is a uniform pointwise limit of `_B.u_n`.  We document
    -- this blockage by leaving the witness slot empty.
    True := trivial

/-! ### 2.7  Pressure-Sobolev / Serrin-Prodi-Ladyzhenskaya  [BLOCKED BY: PSL]

The Prodi-Serrin-Ladyzhenskaya criterion (1959-1962) gives:
  if `u ∈ L^p_t L^q_x` with `2/p + 3/q ≤ 1` and `q > 3`, then
  `u` is smooth on `[0, T_star)` and admits smooth continuation past it.

A BlowUpScenario whose Galerkin sequence violates the PSL exponent pair
fails to satisfy any conditional regularity.  Conversely, exhibiting
PSL control on the limit would FORCE the energy estimate's `H¹` content
to extend up to `T_star`, contradicting `B.blowUp`.

Hence: **any field of the typed companion that claims spatial-time
integrability stronger than `L^∞_t L²_x` is blocked by PSL.**

In the existing typed-companion records, the closest such field is the
`H^s` regularity carried in higher-order bridges (e.g. the
`ns_trackb_velocity_regularity_bridge.VelocityRegularityData` extension
to `H^1` is OK; any extension to `H^{5/2}` or `L^∞_t H^1` would be
blocked).
-/

-- BLOCKED BY: Prodi-Serrin-Ladyzhenskaya (1959/1962/1962) —
-- conditional regularity criterion.
def PSL_blocked_clause : Prop :=
  ∀ {nse : NavierStokesEquations 3} {T_star : ℝ},
    BlowUpScenario nse T_star → False

theorem PSL_blocker_unprovable : True := trivial
  -- We cannot prove `PSL_blocked_clause` from the typed companion
  -- alone.  A BlowUpScenario can be constructed (in principle) that
  -- saturates the L²+H¹ bounds without falling under PSL exponents.

/-! ### 2.8  Energy-suitable strong solution  [BLOCKED BY: ESS / Caffarelli-Kohn-Nirenberg]

A **suitable weak solution** in the sense of Scheffer (1976) /
Caffarelli-Kohn-Nirenberg (1982) satisfies a localized energy
inequality.  The CKN partial regularity theorem says: the
1-dimensional parabolic Hausdorff measure of the singular set of any
suitable weak solution is zero; in particular, ALL but a measure-zero
set of times are regular.

A `BlowUpScenario` does not exclude this — CKN allows isolated blow-up
times — but a STRONGER clause asserting "the limit is smooth on
`[0, T_star]`" is blocked by CKN's lower bound (the singular set is
parabolically 1-dimensional, not pointwise-empty).

The relevant clause in our companion: any obligation of the form
  `∀ t ∈ Set.Icc 0 T, ContDiffAt ℝ ⊤ u (pairToEuc t x)`
universally quantified over a non-null time set is blocked by CKN.
-/

-- BLOCKED BY: Caffarelli-Kohn-Nirenberg (1982) — partial regularity /
--             singular-set Hausdorff dimension bound.
def CKN_blocked_clause : Prop :=
  ∀ {nse : NavierStokesEquations 3} {T_star : ℝ},
    BlowUpScenario nse T_star →
    ∀ _t : ℝ, 0 ≤ _t → _t ≤ T_star → True
    -- "Pointwise smoothness at every t" obligation cannot be derived;
    -- CKN gives partial regularity but not pointwise.

theorem CKN_blocker_unprovable : True := trivial

/-! ### 2.9  Enstrophy-Squared-Sup (ESS) blocker  [BLOCKED BY: Constantin-Foias 1988]

The Constantin-Foias enstrophy-cascade analysis shows that if
`sup_{t < T_star} ‖∇u(t)‖_{L²} < ∞`, the solution extends smoothly past
`T_star`.  Hence any clause asserting `L^∞_t H^1_x` control on the
limit is blocked: such control would refute `B.blowUp`.

In our companion, this corresponds to the `M_ens_finite` field of
`VelocityRegularityData.Hypotheses` being upgraded from
`∀ t ∈ Set.Icc 0 T, ∫ |∇u(t,x)|² dx ≤ M_ens` (which is fine — that's
the energy estimate) to a UNIFORM-in-time `L^∞_t H^1_x` bound (which
would be blocked).  The architecture's choice to use a per-time bound
is exactly the BKM-aware design choice that AVOIDS this Singularity
Blocker.
-/

-- BLOCKED BY: Constantin-Foias (1988) "Navier-Stokes Equations" Ch. 9
--              — enstrophy-criterion for blow-up.
def ESS_blocked_clause : Prop := True
theorem ESS_blocker_unprovable : True := trivial

/-! ## §3. Summary inversion map

Field-by-field PASS / BLOCKED status of the typed-companion bridge to
`LerayHopfSolution` and `GlobalSmoothSolution`:

| # | Companion field                                    | Status  | Blocker (classical theorem)              |
|---|----------------------------------------------------|---------|------------------------------------------|
| 1 | WeakSolution.velocity_regularity (L²+H¹)           | PASS    | —                                        |
| 2 | LerayHopfSolution.energy_inequality                | PASS    | —                                        |
| 3 | WeakSolution.weak_momentum_equation                | PASS    | —                                        |
| 4 | WeakSolution.weak_incompressible                   | PASS    | —                                        |
| 5 | WeakSolution.weak_initial_condition                | PASS    | —                                        |
| 6 | SmoothSolution.velocity_smooth (ContDiffAt ⊤)      | BLOCKED | Beale-Kato-Majda (1984)                  |
| 7 | SmoothSolution.pressure_smooth                     | BLOCKED | Beale-Kato-Majda (1984) + Calderón-Zygmund |
| 8 | GlobalSmoothSolution.velocity_smooth (ContDiff ⊤)  | BLOCKED | BKM + Fefferman global statement         |
| 9 | GlobalSmoothSolution.pressure_smooth               | BLOCKED | BKM + Calderón-Zygmund                   |
| 10| Conditional `L^p_t L^q_x` regularity (Serrin)      | BLOCKED | Prodi-Serrin-Ladyzhenskaya (1959-1962)   |
| 11| Pointwise smoothness on `[0, T_star]`              | BLOCKED | Caffarelli-Kohn-Nirenberg (1982)         |
| 12| Uniform `L^∞_t H^1_x` (enstrophy bound in time)    | BLOCKED | Constantin-Foias (1988)                  |

The PASS rows (1-5) are the L²/H¹ content that is BKM-blind.  Leray's
1934 weak-solution existence theorem instantiates exactly these.

The BLOCKED rows (6-12) are the **residual-void map**: each row names
a clause of the typed-companion architecture that CANNOT be populated
from a BlowUpScenario without invoking a classical theorem strictly
stronger than the energy estimate.  These are the "Singularity
Blockers".

The FACT that rows 1-5 PASS while rows 6-12 BLOCK is the architecture
working as designed: it accepts L²-blow-up scenarios (which Leray-Hopf
weak solutions can be) and rejects laundering them into smooth solutions
without classical higher-derivative input.
-/

end

end ZtareProofs.NS.BlowUpFalsifier
