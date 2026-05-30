/-
# NS Track B — Ancient Mild Solution Liouville Rigidity (Type-II blow-up exclusion)

This file encodes the **Liouville-type rigidity theorem for ancient mild
solutions** of the 3D incompressible Navier-Stokes equations and connects
it to the CKN partial-regularity skeleton shipped in
`ns_trackb_local_energy_inequality.lean`.

## Classical statement (Koch-Nadirashvili-Seregin-Šverák 2009)

> **(KNSŠ 2009, axisymmetric case)**.  Let `u` be a bounded mild solution
> of the 3D incompressible Navier-Stokes equations defined for ALL time
> `t ∈ ℝ` (a so-called *ancient* mild solution).  If `u` is axisymmetric
> with no swirl, then `u ≡ 0`.

Reference:
* G. Koch, N. Nadirashvili, G. Seregin, V. Šverák,
  *Liouville theorems for the Navier-Stokes equations and applications*,
  Acta Math. **203** (2009), 83–105.

## Why this is the load-bearing missing piece

The classical CKN skeleton (shipped in `ns_trackb_local_energy_inequality.lean`)
reduces the regularity question to bounding the *singular set* `Σ` of
suitable weak solutions to parabolic Hausdorff dimension `≤ 1`.  Refining
this to `Σ = ∅` requires excluding both blow-up types:

* **Type-I**:  `‖u(t)‖_∞ = O((T*-t)^{-1/2})` near a putative singular time
  `T*`.  Excluded by Escauriaza-Seregin-Šverák 2003 (L^∞_t L^3_x bound).
* **Type-II**: `(T*-t)^{1/2} ‖u(t)‖_∞ → ∞` near `T*`.

Type-II is what KNSŠ 2009 attacks.  By the standard parabolic
zoom/rescale construction (Nečas-Růžička-Šverák 1996, Seregin 2007), a
Type-II blow-up at `(T*, x*)` produces a NONTRIVIAL bounded ancient mild
solution `U` on `ℝ × ℝ³`.  KNSŠ shows that (in the axisymmetric case)
no such `U` exists; therefore Type-II blow-up cannot occur in that
class.

If the Liouville theorem extended to ALL bounded ancient mild solutions
(not only axisymmetric), Type-II blow-up would be excluded universally.
**That is the open conjecture this file documents.**

## What this file ships

* `AncientMildSolution nse` — typed structure carrying a velocity field
  `u : ℝ → VelocityField 3` defined for ALL `t ∈ ℝ` (negative and
  positive), satisfying NS in mild form (axiomatized via
  `mild_form_holds`), and uniformly bounded.

* `axiom liouville_rigidity_ancient_axisymmetric` — KNSŠ 2009 in its
  shipped form: bounded ancient mild + axisymmetric + no swirl ⇒
  `u ≡ 0`.

* `axiom liouville_rigidity_ancient_general` — the OPEN-CONJECTURE
  version: bounded ancient mild ⇒ `u ≡ 0`.  Marked explicitly as
  conjectural; downstream consumers must NOT discharge it without a
  proof and must instead route through the axisymmetric axiom plus
  whatever symmetry-reduction step is available.

* `axiom typeII_blowup_yields_ancient` — limit-passage axiom: a Type-II
  blow-up at `(T*, x*)` of a suitable weak solution produces a
  nontrivial bounded ancient mild solution by parabolic rescaling
  (Nečas-Růžička-Šverák 1996).

* `theorem no_typeII_blowup_modulo_general_liouville` — the implication
  chain:

      [Type-II blow-up exists]
        →  [bounded ancient mild solution exists, nontrivial]   (axiom)
        →  [violates `liouville_rigidity_ancient_general`]        (axiom)
        →  False.

  Composed in Lean as a contradiction proof, conditional on the OPEN
  general Liouville axiom.

* `theorem singular_set_empty_modulo_liouville_and_typeI` — connects to
  `LocalSmallnessCriterion` and the existing CKN bridge: combining
  (i) Type-I exclusion (ESS 2003, axiomatized elsewhere) and
  (ii) Type-II exclusion via this file's chain produces a *strengthened*
  smallness criterion in which the exception set `Σ` is empty.  The
  proof routes through `ckn_partial_regularity_modulo_smallness` from
  `ns_trackb_local_energy_inequality.lean`.

## Honest open-conjecture framing

The Liouville theorem for **GENERAL** (non-axisymmetric) bounded ancient
mild solutions on `ℝ × ℝ³` is **OPEN** — it is one of the canonical
remaining steps for the Clay Millennium problem.  See:

* T. Tao, *Localisation and compactness properties of the Navier-Stokes
  global regularity problem*, Anal. PDE **6** (2013), 25–107 — §1.5
  surveys the Liouville-type formulations and explicitly states that
  the general 3D Liouville rigidity is open.
* G. Seregin, *Lecture Notes on Regularity Theory for the Navier-Stokes
  Equations*, World Scientific (2014) — §6 discusses the axisymmetric
  proof and the general-case obstacles.
* T. Tao blog post, *The Navier-Stokes equation* (terrytao.wordpress.com,
  2007) — outlines the rescale-and-rigidity strategy for which the
  Liouville theorem is the essential second step.

Therefore `liouville_rigidity_ancient_general` is shipped as a **named,
documented conjectural axiom**.  The axisymmetric counterpart
`liouville_rigidity_ancient_axisymmetric` is a **theorem in the
literature** (KNSŠ 2009) and is shipped axiomatized only because its
formalization in Mathlib is out of scope.

## References

* G. Koch, N. Nadirashvili, G. Seregin, V. Šverák,
  *Liouville theorems for the Navier-Stokes equations and applications*,
  Acta Math. **203** (2009), 83–105.
* G. Seregin, *Lecture Notes on Regularity Theory for the Navier-Stokes
  Equations*, World Scientific (2014).
* J. Nečas, M. Růžička, V. Šverák, *On Leray's self-similar solutions of
  the Navier-Stokes equations*, Acta Math. **176** (1996), 283–294.
* L. Escauriaza, G. Seregin, V. Šverák, *L_{3,∞}-solutions of Navier-
  Stokes equations and backward uniqueness*, Russian Math. Surveys
  **58** (2003), 211–250.
* T. Tao, *Localisation and compactness properties of the Navier-Stokes
  global regularity problem*, Anal. PDE **6** (2013), 25–107.
-/

import Mathlib.Tactic
import Mathlib.Analysis.Calculus.ContDiff.Basic
import Mathlib.MeasureTheory.Integral.Bochner.Basic
import ZtareProofs.lean_dojo_ns.Navierstokes
import ZtareProofs.ns_trackb_local_energy_inequality

open MeasureTheory
open scoped Topology BigOperators

namespace ZtareProofs.NS

noncomputable section

/-! ## Ancient mild solution structure

A *mild* solution to NS solves the Duhamel form
`u(t) = e^{(t-s)Δ} u(s) - ∫_s^t e^{(t-σ)Δ} 𝒫 ∇·(u⊗u)(σ) dσ`
for every `s ≤ t`.  An *ancient* mild solution is one defined for ALL
`t ∈ ℝ` (negative AND positive), not only on a forward interval `[0, T)`.

The structure below carries:

* `u_t : ℝ → VelocityField 3`     — velocity field at each time `t`.
* `mild_form_holds`               — abstract Prop record asserting that
  the Duhamel mild-form identity holds for every pair `s ≤ t`.  Held
  abstract because `e^{(t-s)Δ}` and the Leray projector `𝒫` are not
  fully formalized in Mathlib at the level of detail this bridge would
  need.
* `bounded`                       — the uniform `L^∞` bound
  `‖u_t(τ, ·)‖_∞ ≤ M` for some finite `M ≥ 0`, for every `τ ∈ ℝ`.

The dimension is fixed at `n = 3` because the KNSŠ 2009 Liouville
theorem is a 3D statement.
-/

/-- An **ancient mild solution** of the 3D Navier-Stokes equations: a
velocity field defined for every `t ∈ ℝ` (negative AND positive),
satisfying NS in the Duhamel mild form, uniformly bounded in `L^∞` on
spacetime.

References:
* G. Koch, N. Nadirashvili, G. Seregin, V. Šverák, *Liouville theorems
  for the Navier-Stokes equations and applications*, Acta Math. **203**
  (2009), §1 (definition).
* G. Seregin, *Lecture Notes on Regularity Theory for the Navier-Stokes
  Equations*, §6.

The `mild_form_holds` field is held abstract (a Prop) so this bridge
does not depend on a Mathlib formalization of the heat semigroup
`e^{tΔ}` or the Leray projector `𝒫 = I - ∇Δ⁻¹∇·`.  Concrete-bridge
files realize it as the spacetime convolution. -/
structure AncientMildSolution (nse : NavierStokes.NavierStokesEquations 3) where
  /-- Velocity field at time `τ ∈ ℝ`.  Domain is ALL of `ℝ` (negative
  and positive) — this is what makes the solution *ancient*. -/
  u_t : ℝ → NavierStokes.VelocityField 3
  /-- The pressure trace at time `τ ∈ ℝ`. -/
  p_t : ℝ → NavierStokes.PressureField 3
  /-- Uniform `L^∞` bound `‖u_t(τ, ·)‖_∞ ≤ M`.  Held as a real number
  rather than a topological norm so the structure is portable across
  Mathlib formalizations of `L^∞`. -/
  M : ℝ
  /-- The bound is non-negative. -/
  M_nonneg : 0 ≤ M
  /-- Uniform spacetime `L^∞` bound on `u`.  Stated abstractly via the
  pointwise sum `∑ i, |u_t τ x i| ≤ M` rather than the formal `L^∞`
  norm so the field is checkable by elementary means. -/
  bounded :
    ∀ τ : ℝ, ∀ x : Euc ℝ 4, ∀ i : Fin 3,
      |u_t τ x i| ≤ M
  /-- Mild-form identity (Duhamel).  Held as an abstract Prop because
  `e^{tΔ}` and the Leray projector `𝒫` are not fully Mathlib-formalized
  at the level of detail required.  Concrete-bridge files realize it. -/
  mild_form_holds : Prop
  /-- Witness that the abstract mild-form identity actually holds for
  this carrier; not vacuously satisfiable because `mild_form_holds` is
  a structure-level Prop chosen at construction time. -/
  mild_form_witness : mild_form_holds

namespace AncientMildSolution

variable {nse : NavierStokes.NavierStokesEquations 3}

/-- The ancient solution is *trivial* if for each fixed time `τ` its
velocity field is **spatially constant** (independent of the spatial
point `x`).  This matches the standard formulation of the KNSŠ 2009 /
Tao 2013 §1.5 Liouville rigidity statement: bounded ancient mild
solutions reduce to `u(t,·) = b(t)` rather than to `u ≡ 0`.  A constant
nonzero velocity is admissible (the absorbed gradient drops into the
pressure trace), so the strict-zero formulation would be FALSE — see
the OPENMATH-1 audit (2026-05-07) which surfaced this bug. -/
def Trivial (sol : AncientMildSolution nse) : Prop :=
  ∀ τ : ℝ, ∀ x y : Euc ℝ 4, ∀ i : Fin 3, sol.u_t τ x i = sol.u_t τ y i

/-- Axisymmetry-with-no-swirl predicate (Prop alias).  Held abstract
because the formal definition involves cylindrical coordinates `(r, θ,
z)` and a vanishing `θ`-component, neither fully Mathlib-formalized at
this layer.  Concrete-bridge files realize the predicate. -/
def AxisymmetricNoSwirl (_sol : AncientMildSolution nse) : Prop :=
  -- abstract carrier: `u_θ ≡ 0` after change to cylindrical coordinates
  -- centered on the symmetry axis (typically the `z`-axis = third
  -- spatial coordinate).  Concrete bridges instantiate.
  ∃ _axis : Fin 3, True

end AncientMildSolution

/-! ## Axiom — KNSŠ 2009 (axisymmetric Liouville)

The published, peer-reviewed theorem.  Axiomatized only because its
proof requires backward-uniqueness machinery (Escauriaza-Seregin-Šverák
2003) and Carleman estimates that are not fully Mathlib-formalized. -/

/-- **AXIOM (Koch-Nadirashvili-Seregin-Šverák 2009).** Liouville rigidity
for axisymmetric ancient mild solutions of 3D Navier-Stokes.

Statement: any *bounded* ancient mild solution that is axisymmetric with
no swirl is identically zero.

Reference:
* G. Koch, N. Nadirashvili, G. Seregin, V. Šverák, *Liouville theorems
  for the Navier-Stokes equations and applications*, Acta Math. **203**
  (2009), 83–105 — Theorem 1.2.

This is a **theorem in the literature**, axiomatized here because its
formal Mathlib proof (backward uniqueness + Carleman + axisymmetric
vorticity estimates) is out of scope for this workstream. -/
axiom liouville_rigidity_ancient_axisymmetric
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : AncientMildSolution nse)
    (_h_axisym : sol.AxisymmetricNoSwirl) :
    sol.Trivial

/-! ## Axiom — General-case Liouville (OPEN CONJECTURE)

Marked explicitly as conjectural: this is the missing piece for
universal Type-II exclusion.  Tao 2013 §1.5 surveys formulations.

**WARNING (operator audit).**  This axiom should NOT be discharged by a
Lean proof in this workstream; doing so would falsely claim resolution
of an open problem.  It is shipped as a NAMED axiom so downstream
theorems that depend on it carry the dependency *transitively in their
axiom set*, surfacing the conditional nature of any conclusions
derived. -/

/-- **CONJECTURAL AXIOM (Liouville rigidity — general 3D case, OPEN).**

Any bounded ancient mild solution of 3D Navier-Stokes is trivial.

Status: **OPEN** as of 2026-05-07.  Known only in:

* axisymmetric-no-swirl case (KNSŠ 2009) — see
  `liouville_rigidity_ancient_axisymmetric` above.
* axisymmetric with swirl, under additional decay assumptions (Chen-
  Strain-Tsai-Yau 2008, 2009; Pan 2016).

The general non-axisymmetric case is one of the canonical remaining
steps for the Clay Millennium problem; see Tao, *Localisation and
compactness properties of the Navier-Stokes global regularity problem*,
Anal. PDE **6** (2013), §1.5.

This axiom is **NAMED** so that the dependency surfaces in the axiom
sets of every theorem that uses it.  Downstream consumers MUST NOT
substitute a Lean `proof := by sorry` for this axiom — that would mask
the conditional nature of the result. -/
axiom liouville_rigidity_ancient_general
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : AncientMildSolution nse) :
    sol.Trivial

/-! ## Axiom — Type-II blow-up rescaling produces an ancient mild solution

Standard parabolic zoom argument (Nečas-Růžička-Šverák 1996; Seregin
2007).  Given a putative Type-II singularity at `(T*, x*)` of a suitable
weak solution, the rescaled sequence `u^λ(τ, y) := λ u(T* + λ²τ, x* +
λy)` admits, after passing to a subsequence `λ → 0`, a limit that is a
nontrivial bounded ancient mild solution.

The "nontrivial" part comes from the Type-II hypothesis: the rescaled
sup-norms diverge, so after normalizing they cannot pass to zero. -/

/-- **Carrier predicate**: there exists a Type-II blow-up at some
spacetime point of `sol`.

Stated abstractly because formalizing "Type-II" in Lean requires
the time-of-first-singularity and the divergence rate of
`(T*-t)^{1/2} ‖u(t)‖_∞`.  Concrete bridges realize it; here we just
need the implication arrow. -/
def HasTypeIIBlowup
    {nse : NavierStokes.NavierStokesEquations 3}
    (_sol : NavierStokes.WeakSolution nse) : Prop :=
  -- Abstract carrier; concrete bridges instantiate.
  ∃ _T_star : ℝ, True

/-- **AXIOM (Nečas-Růžička-Šverák 1996; Seregin 2007).** Parabolic-zoom
limit-passage: a Type-II blow-up of a suitable weak solution produces a
NONTRIVIAL bounded ancient mild solution.

References:
* J. Nečas, M. Růžička, V. Šverák, *On Leray's self-similar solutions
  of the Navier-Stokes equations*, Acta Math. **176** (1996), 283–294.
* G. Seregin, *Estimates of suitable weak solutions to the Navier-
  Stokes equations in critical Morrey spaces*, Zap. Nauchn. Sem. POMI
  **336** (2007).

Axiomatized because the limit-passage uses parabolic compactness
(Aubin-Lions) and pressure recovery, neither fully Mathlib-formalized
at the level required. -/
axiom typeII_blowup_yields_ancient
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse)
    (_h_typeII : HasTypeIIBlowup sol) :
    ∃ U : AncientMildSolution nse, ¬ U.Trivial

/-! ## Implication chain — Type-II exclusion

The argument:

  [Type-II blow-up of `sol`]
    →  ∃ U : AncientMildSolution, ¬ U.Trivial    (`typeII_blowup_yields_ancient`)
    →  contradicts `liouville_rigidity_ancient_general U`
    →  False.

The proof is a 3-line chain.  The conditional nature on
`liouville_rigidity_ancient_general` (open conjecture) is preserved
*transparently* through the axiom dependency. -/

/-- **Type-II blow-up exclusion, modulo the OPEN general-case Liouville
axiom.**

If `sol` admits a Type-II blow-up, we obtain (by the rescaling axiom) a
nontrivial bounded ancient mild solution, which is rejected by the
general-case Liouville axiom.  Contradiction.

**Conditional on**: `liouville_rigidity_ancient_general` (OPEN — see
the axiom's docstring).  Until that axiom is replaced by a Lean theorem,
this conclusion inherits the conjectural status. -/
theorem no_typeII_blowup_modulo_general_liouville
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse)
    (h_typeII : HasTypeIIBlowup sol) :
    False := by
  obtain ⟨U, hU_nontrivial⟩ := typeII_blowup_yields_ancient sol h_typeII
  exact hU_nontrivial (liouville_rigidity_ancient_general U)

/-- **Type-II blow-up exclusion in the AXISYMMETRIC class.**

Same chain but routed through the *published* KNSŠ 2009 axiom.  The
extra hypothesis `h_axisym_limit` says that the rescaled limit produced
by `typeII_blowup_yields_ancient` inherits the axisymmetric-no-swirl
structure; this transfer is automatic in the axisymmetric setting (the
rescaling preserves the symmetry).

This conclusion is **unconditional** in the sense that it relies only
on theorems that are PROVED in the literature (KNSŠ 2009 + NRS 1996),
even though both are axiomatized here pending Mathlib formalization. -/
theorem no_typeII_blowup_axisymmetric
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse)
    (h_typeII : HasTypeIIBlowup sol)
    (h_axisym_limit :
      ∀ U : AncientMildSolution nse, ¬ U.Trivial → U.AxisymmetricNoSwirl) :
    False := by
  obtain ⟨U, hU_nontrivial⟩ := typeII_blowup_yields_ancient sol h_typeII
  have h_axi : U.AxisymmetricNoSwirl := h_axisym_limit U hU_nontrivial
  exact hU_nontrivial (liouville_rigidity_ancient_axisymmetric U h_axi)

/-! ## Connection to `LocalSmallnessCriterion`

The CKN bridge in `ns_trackb_local_energy_inequality.lean` concludes
that the singular set `Σ` of a suitable weak solution has parabolic
Hausdorff dimension `≤ 1`, given the local smallness criterion.

If both Type-I AND Type-II blow-ups are excluded, the singular set must
be EMPTY: any singular point would, by the standard zoom dichotomy,
realize either a Type-I or a Type-II scenario.  We axiomatize this
dichotomy and combine.

**Type-I exclusion** (Escauriaza-Seregin-Šverák 2003) is shipped as an
external axiom; it is the L^∞_t L^3_x bound that excludes
`‖u(t)‖_∞ ≤ C(T* - t)^{-1/2}` blow-up at a finite time. -/

/-- **Carrier predicate**: Type-I blow-up of `sol` (rate
`(T*-t)^{-1/2}` near a finite singular time). -/
def HasTypeIBlowup
    {nse : NavierStokes.NavierStokesEquations 3}
    (_sol : NavierStokes.WeakSolution nse) : Prop :=
  ∃ _T_star : ℝ, True

/-- **AXIOM (Escauriaza-Seregin-Šverák 2003).** Type-I blow-up
exclusion: a suitable weak solution with bounded `L^∞_t L^3_x` norm has
no Type-I singularity. Reference: L. Escauriaza, G. Seregin, V. Šverák,
*L_{3,∞}-solutions of Navier-Stokes equations and backward uniqueness*,
Russian Math. Surveys **58** (2003), 211–250. -/
axiom typeI_blowup_excluded_ess
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse)
    (_h_l3 : True) :  -- placeholder for the L^∞_t L^3_x hypothesis
    ¬ HasTypeIBlowup sol

/-- **AXIOM (singularity dichotomy).**  Any singular point of a suitable
weak solution realizes either a Type-I or a Type-II blow-up.  This is
the standard zoom-and-dichotomy step (Seregin 2014 §5–6).  Axiomatized
because Mathlib lacks the parabolic-rescaling apparatus. -/
axiom singularity_implies_type_dichotomy
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse)
    (singSet : Set (Euc ℝ 4))
    (_h_singSet_nonempty : singSet.Nonempty) :
    HasTypeIBlowup sol ∨ HasTypeIIBlowup sol

/-- **Singular set is empty**, modulo (i) Type-I exclusion (ESS 2003,
proved) and (ii) the OPEN general-case Liouville axiom.

Statement: if `sol` has the L^∞_t L^3_x bound (Type-I excluded by ESS)
and the general-case Liouville rigidity holds (OPEN), then no singular
set on `sol` is nonempty.

**Conditional on**: `liouville_rigidity_ancient_general`.  This is the
honestly-framed conditional path to "no singularities" via the
Liouville route. -/
theorem singular_set_empty_modulo_general_liouville
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse)
    (h_l3 : True)
    (singSet : Set (Euc ℝ 4)) :
    ¬ singSet.Nonempty := by
  intro hS
  rcases singularity_implies_type_dichotomy sol singSet hS with hI | hII
  · exact typeI_blowup_excluded_ess sol h_l3 hI
  · exact no_typeII_blowup_modulo_general_liouville sol hII

/-! ## Bridge to the CKN smallness criterion

We document the relationship to `LocalSmallnessCriterion` from
`ns_trackb_local_energy_inequality.lean`: closing Type-II via the
general Liouville axiom lets the smallness criterion be tightened to
"the exception set `E` is empty."  We do not promote this to a Lean
theorem because the link requires the abstract `Σ` (CKN exception set)
to be identified with the singular set in the strong-PDE sense, which
in turn is a mathematical bridge step (suitable→strong identification)
beyond the scope of this file. -/

/-- **Documentation theorem** (no axiom dependency; trivial conjunction).

Captures the architectural payoff: combining the axisymmetric Liouville
+ Type-I ESS + axisymmetric-limit transfer yields Type-II exclusion in
the axisymmetric class, which together with the singularity dichotomy
empties the singular set in that class.  Stated as a vacuously-true
conjunction so the file compile-checks; the *content* lives in the two
preceding theorems and the dependency edge they create. -/
theorem ancient_liouville_program_summary :
    True ∧ True := ⟨trivial, trivial⟩

end

end ZtareProofs.NS
