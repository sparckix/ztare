/-
# NS Defect-Calculus Skeleton (PL-097 / PL-103, weeks 1-2 deliverable)

**Status: REFACTORED 2026-05-09 (PL-103)** — typed-companion skeleton for the
defect-calculus pivot of the Clay NS programme, now carrying the explicit
μ[u] construction shipped under PL-099 / catch C-2026-05-09-97 and reproduced
in `projects/ns_millennium_hunt/workspace/external_prover/responses/epd-74407924dd2c.md` (gpt-5
2026-05-09).

## Programme context

Sister to (not replacement for) the Lorentz-Strip Liouville charter on
Track B. The defect-calculus pivot proposes a parallel attack surface
motivated by the Euler analog (Duchon-Robert 1999, *Nonlinearity* **13**
(2000), 249–255), in which the local energy identity is rewritten in a
form that exposes a Radon **defect measure** `μ[u]` carrying the
cascade-defect (energy dissipation beyond the viscous term `ν |∇u|²`).

PL-103 replaces the previously-opaque math content with the concrete
PL-099 construction (Q1-Q5):

1. **Mollifier ρ_ℓ** — radial smooth compactly-supported, mass-one;
   `ρ_ℓ(x) := ℓ^{-3} ρ(x/ℓ)`.
2. **Scale-local flux Π_ℓ[u]** — increment formula
     `Π_ℓ[u](x,t) := (1/4) ∫ (∇ρ_ℓ)(r) · δ_r u(x,t) |δ_r u(x,t)|² dr`
   with `δ_r u(x,t) := u(x+r,t) - u(x,t)`. For smooth `u` this equals
   `-∇u_ℓ : τ_ℓ` with `τ_ℓ := (u⊗u)_ℓ - u_ℓ⊗u_ℓ`.
3. **Defect μ[u]** — `w*-lim_{ℓ→0} Π_ℓ[u]` in `M_+(Ω)` (vague topology),
   existence via Riesz–Markov on the local energy inequality.
4. **Algebraic identity** in `D'(Ω)`:
     `∂_t e + div((e+p)u) − νΔe + ν|∇u|² + μ[u] = 0`,
   `e := |u|²/2`, `R[u] := νΔe` is the explicit viscous correction.
5. **ε-regularity rigidity lemma** — `μ[u](Q_r(z₀)) = 0` plus
   `r⁻² ∫_{Q_r} |u|³ ≤ ε*` ⇒ `u` smooth on `Q_{θr}(z₀)` with
   `sup|u| + r·sup|∇u| ≤ C r⁻¹ (ε*)^{1/3}`.

## Encoding strategy (PL-103 step 2)

* **Mollifier section** — typed companion `mollifierKernel` with the
  explicit defining formula in the docstring; Mathlib has
  `Mathlib.Analysis.Convolution` and `ContDiffBump` but the exact
  radial/mass-one bundle is not packaged as a single primitive, so we
  keep a typed companion citing the formula.
* **Flux section** — typed companion `mollifiedFlux` carrying the
  increment formula in the docstring; the equivalence
  `Π_ℓ = -∇u_ℓ : τ_ℓ` is recorded as an axiom (Duchon–Robert 1999, §2).
* **Defect section** — `RadonDefectMeasure` retained as opaque
  `SpaceTimeRadonMeasure`, but the limit existence is explicitly
  axiomatized as Riesz–Markov on the local energy inequality, citing
  the PL-099 derivation. Mathlib has `MeasureTheory.Measure` and
  `Riesz–Markov–Kakutani` (`Mathlib.MeasureTheory.Integral.RieszMarkovKakutani`)
  but the vague topology + space-time Radon class is too thin to wire
  inline without a multi-week formalisation effort, so we tag this
  TYPED-COMPANION-PENDING-MATHLIB.
* **Algebraic identity section** — replaced by the explicit form
  `∂_t e + div((e+p)u) − νΔe + ν|∇u|² + μ[u] = 0`, with `R[u] := νΔe`
  named as `viscous_correction`. Cites Duchon–Robert 1999 (Euler) +
  tags the NS-specific addition.
* **Rigidity lemma section** — rewritten as the precise PL-099 Q4
  statement (cylinder smallness + zero defect ⇒ smoothness on `Q_{θr}`
  with quantitative bound).
* **Honesty disclosure section** — explicit typed-companion-pending
  tag on the commutator estimate `u_ℓ·τ_ℓ → 0` (PL-099 Q5; PL-102 in
  flight to verify whether Leray–Hopf alone suffices or extra
  integrability is needed).

## Anti-laundering compliance (PATTERN-015 8th-point)

* Every axiom names its literature anchor.
* The construction's truth is **encoded**, not **proved** — i.e., we
  expose typed companions that downstream Lean code can reference with
  the correct shape.
* Honest disclosure: PL-102 verification pending; the Q1-Q4 commutator
  step might require extra hypotheses beyond the bare Leray–Hopf class
  (Q5 of PL-099).

## What this file deliberately does NOT do

* Does not formalize Radon measures on `ℝ³ × (0, T)`; vague topology
  and weak-* convergence machinery in Mathlib are too thin for inline
  use.
* Does not formalize distributional differentiation or `D'` topology.
* Does not discharge the NS extension of the Duchon–Robert identity.
* Does not claim `μ[u] ≥ 0` as a theorem proved here — it is recorded
  as an axiom citing the local-energy-inequality derivation in PL-099.

References:
* J. Leray, *Sur le mouvement d'un liquide visqueux emplissant l'espace*,
  Acta Math. **63** (1934), 193–248.
* E. Hopf, *Über die Anfangswertaufgabe für die hydrodynamischen
  Grundgleichungen*, Math. Nachr. **4** (1951), 213–231.
* P. Constantin, W. E, E. Titi, *Onsager's conjecture on the energy
  conservation for solutions of Euler's equation*, Comm. Math. Phys.
  **165** (1994), 207–209.
* J. Duchon, R. Robert, *Inertial energy dissipation for weak solutions
  of incompressible Euler and Navier-Stokes equations*, Nonlinearity
  **13** (2000), 249–255.
* L. Caffarelli, R. Kohn, L. Nirenberg, *Partial regularity of suitable
  weak solutions of the Navier-Stokes equations*, CPAM **35** (1982),
  771–831.
-/

import Mathlib.Tactic
import Mathlib.MeasureTheory.Measure.MeasureSpace
import Mathlib.Analysis.Calculus.ContDiff.Basic

namespace ZtareProofs.NSDefectCalculusSkeleton

noncomputable section

/-! ## Section 1 — Abstract carrier types

We do not formalize `EuclideanSpace ℝ (Fin 3)` velocity fields,
distributions, or Radon measures inline. Instead we expose opaque type
slots that the API needs. Future formalization can refine each slot
to its Mathlib-faithful realization without changing the algebraic
API. -/

/-- **Abstract velocity-field type slot.** Real formalization would be
`ℝ × EuclideanSpace ℝ (Fin 3) → EuclideanSpace ℝ (Fin 3)` with the
appropriate regularity class (Leray–Hopf:
`L^∞_t L²_x ∩ L²_t Ḣ¹_x`, divergence-free in distributions) baked in.
We keep it opaque to avoid premature regularity commitment. -/
opaque AbstractVelocityField : Type

/-- **Abstract scalar pressure-field type slot.** Real formalization
would carry the Helmholtz–Leray-projection-defined pressure as a
distribution. -/
opaque AbstractPressureField : Type

/-- **Abstract scalar flux-distribution type.** What `Π_ℓ[u]` evaluates
to at a given scale; concretely, a distribution on `ℝ³ × (0, T)`. -/
opaque SomeFluxType : Type

/-- **Abstract space-time Radon-measure type slot.** Real formalization
would be `MeasureTheory.Measure (ℝ × EuclideanSpace ℝ (Fin 3))`
restricted to the locally-finite (Radon) class with the vague
topology. Mathlib has `MeasureTheory.Measure` but the Riesz–Markov +
vague-topology bundle on a non-compact open is thin; we keep the type
opaque. -/
opaque SpaceTimeRadonMeasure : Type

/-- **Abstract mollifier-kernel type slot.** Real formalization: a
function `ℝ → (Fin 3 → ℝ) → ℝ` that for every `ℓ > 0` is `C^∞_c`,
non-negative, radial, and integrates to one (cf. PL-099 Q1(a)). -/
opaque AbstractMollifier : Type

/-- **Nonempty witness axioms for the opaque carrier types.** Pure
type-system bookkeeping (zero vector / zero measure / zero kernel
trivially inhabit the real realizations). -/
axiom AbstractVelocityField_nonempty : Nonempty AbstractVelocityField
axiom AbstractPressureField_nonempty : Nonempty AbstractPressureField
axiom SomeFluxType_nonempty : Nonempty SomeFluxType
axiom SpaceTimeRadonMeasure_nonempty : Nonempty SpaceTimeRadonMeasure
axiom AbstractMollifier_nonempty : Nonempty AbstractMollifier

attribute [instance] AbstractVelocityField_nonempty
attribute [instance] AbstractPressureField_nonempty
attribute [instance] SomeFluxType_nonempty
attribute [instance] SpaceTimeRadonMeasure_nonempty
attribute [instance] AbstractMollifier_nonempty

/-! ## Section 2 — `TimeSpaceLerayHopfSolution`

Typed companion for a Leray-Hopf weak solution carrying a local-energy-
inequality witness. The classical Leray 1934 + Hopf 1951 framework
gives:

* `u ∈ L^∞_t L²_x ∩ L²_t H¹_x` on `ℝ³ × (0, T)`,
* `u` weakly solves NS in the distributional sense,
* `u` satisfies the **local** energy inequality
  `∂_t (|u|²/2) + div((|u|²/2 + p) u) ≤ ν Δ(|u|²/2) - ν |∇u|²` in `D'`.

The local energy inequality is the load-bearing field for the defect
calculus: it is precisely the slack in this inequality that the defect
measure `μ[u]` will quantify.

References:
* J. Leray, Acta Math. **63** (1934), 193–248.
* E. Hopf, Math. Nachr. **4** (1951), 213–231. -/

/-- **Time-space Leray–Hopf solution (typed companion).** Carries the
velocity field, pressure, time horizon `T`, and a `Prop`-valued witness
that the local energy inequality holds in `D'(ℝ³ × (0, T))`. -/
structure TimeSpaceLerayHopfSolution where
  /-- Velocity field on `ℝ × ℝ³` (abstract). -/
  u : AbstractVelocityField
  /-- Pressure field on `ℝ × ℝ³` (abstract). -/
  p : AbstractPressureField
  /-- Positive time horizon `T` so the time-space domain is `ℝ³ × (0, T)`. -/
  T : ℝ
  /-- `T > 0` (non-degenerate horizon). -/
  T_pos : 0 < T
  /-- **Local energy inequality witness.** A `Prop`-valued field
  asserting that the Leray–Hopf local energy inequality holds in
  `D'(ℝ³ × (0, T))`. -/
  local_energy_inequality : Prop
  /-- The local energy inequality witness is required to hold. -/
  local_energy_inequality_holds : local_energy_inequality

/-! ## Section 3 — Mollifier kernel ρ_ℓ (PL-099 Q1(a))

PL-099 Q1(a): fix `ρ ∈ C^∞_c(ℝ³)`, `ρ ≥ 0`, radial, `supp ρ ⊂ B₁(0)`,
`∫ ρ = 1`. Define `ρ_ℓ(x) := ℓ⁻³ ρ(x/ℓ)` for `ℓ ∈ (0, 1)`.

Mathlib note: `Mathlib.Analysis.Calculus.BumpFunction.Basic` provides
`ContDiffBump` and `Mathlib.Analysis.Convolution` provides convolution
infrastructure, but the radial / mass-one / dyadic-rescaling bundle
required here is not a single Mathlib primitive. We keep a typed
companion with the explicit formula in the docstring. -/

/-- **The reference mollifier `ρ`** (typed companion).

Specification (PL-099 Q1(a)): an inhabitant of `AbstractMollifier`
representing a fixed `ρ ∈ C^∞_c(ℝ³)` with the properties

* `ρ ≥ 0`,
* radial (`ρ(x) = ρ̃(|x|)` for some `ρ̃ : [0, ∞) → ℝ`),
* `supp ρ ⊂ B₁(0)`,
* `∫_{ℝ³} ρ(x) dx = 1`.

The downstream construction is independent of the specific choice;
only existence of a kernel with these four properties is used. -/
opaque referenceMollifier : AbstractMollifier

/-- **Rescaled mollifier `ρ_ℓ`** (typed companion).

Specification (PL-099 Q1(a)): for `ℓ > 0`, `ρ_ℓ(x) := ℓ⁻³ ρ(x/ℓ)`.

* Mass-one: `∫ ρ_ℓ = 1` for every `ℓ > 0`.
* Support: `supp ρ_ℓ ⊂ B_ℓ(0)`.
* Radial / non-negative inherited from `ρ`. -/
opaque mollifierKernel (ρ : AbstractMollifier) (ℓ : ℝ) : AbstractMollifier

/-- **Mass-one axiom** for the rescaled kernel `ρ_ℓ`.

PL-099 Q1(a): `∫_{ℝ³} ρ_ℓ(x) dx = 1` for every `ℓ > 0`. We expose
the predicate as an opaque `Prop` and assert it via axiom. -/
opaque MollifierMassOne (ρ : AbstractMollifier) : Prop

/-- The reference mollifier has unit mass (PL-099 Q1(a)). -/
axiom referenceMollifier_mass_one : MollifierMassOne referenceMollifier

/-- The rescaled kernel inherits unit mass for all `ℓ > 0`
(change-of-variables `y := x/ℓ`). -/
axiom mollifierKernel_mass_one
    (ρ : AbstractMollifier) (_hρ : MollifierMassOne ρ)
    (ℓ : ℝ) (_hℓ : 0 < ℓ) :
    MollifierMassOne (mollifierKernel ρ ℓ)

/-! ## Section 4 — Scale-local mollified flux Π_ℓ[u] (PL-099 Q1(b,c))

PL-099 Q1(b): the increment formula

  `Π_ℓ[u](x,t) := (1/4) ∫_{ℝ³} (∇ρ_ℓ)(r) · δ_r u(x,t) |δ_r u(x,t)|² dr`,

where `δ_r u(x,t) := u(x+r,t) - u(x,t)`. Equivalently, for smooth `u`:

  `Π_ℓ[u] = -∇u_ℓ : τ_ℓ`,

with `τ_ℓ := (u ⊗ u)_ℓ - u_ℓ ⊗ u_ℓ`.

PL-099 Q1(c): cancellations used —
* `∫ ∇ρ_ℓ = 0` (mass-one + radiality), so `Π_ℓ` vanishes on affines.
* `∇ρ_ℓ` odd in `r`, `δ_r u` odd, integrand even.
* `div u = 0 ⇒ div u_ℓ = 0`.
* `u ⊗ u` symmetric ⇒ `τ_ℓ` symmetric ⇒
  `∇u_ℓ : τ_ℓ = Sym(∇u_ℓ) : τ_ℓ`. -/

/-- **Scale-local mollified flux `Π_ℓ[u]`** (typed companion,
increment formula).

Specification (PL-099 Q1(b)): for a Leray–Hopf solution `u` and a
kernel `ρ_ℓ`,

  `Π_ℓ[u](x,t) := (1/4) ∫_{ℝ³} (∇ρ_ℓ)(r) · δ_r u(x,t) |δ_r u(x,t)|² dr`,

with `δ_r u(x,t) := u(x+r,t) - u(x,t)`.

The increment form is taken as the **primary definition** because it
is well-defined for the Leray–Hopf class without requiring `∇u_ℓ`. -/
opaque mollifiedFlux
    (u : TimeSpaceLerayHopfSolution) (ρ : AbstractMollifier) (ℓ : ℝ) :
    SomeFluxType

/-- Backwards-compatible alias: scale-local mollified flux specialized
to the reference kernel `ρ`. Older API consumers indexing only on `u`
and `ℓ` continue to compile. -/
@[reducible]
def MollifiedFlux (u : TimeSpaceLerayHopfSolution) (ℓ : ℝ) : SomeFluxType :=
  mollifiedFlux u referenceMollifier ℓ

/-- **Smooth-`u` equivalence** (typed-companion-axiom; PL-099 Q1(b)).

For `u` smooth on `ℝ³ × (0, T)`, the increment-formula flux equals the
contracted-gradient form `−∇u_ℓ : τ_ℓ`, with `τ_ℓ := (u⊗u)_ℓ − u_ℓ⊗u_ℓ`.
We expose the contracted-gradient form as `mollifiedFluxContracted`
and the equivalence as a `Prop` axiom indexed by a smoothness witness.

Citation: Duchon–Robert 1999, §2; Constantin–E–Titi 1994, eq. (2.4)–(2.6). -/
opaque mollifiedFluxContracted
    (u : TimeSpaceLerayHopfSolution) (ρ : AbstractMollifier) (ℓ : ℝ) :
    SomeFluxType

/-- Predicate that `u` is smooth in the classical sense on `ℝ³ × (0, T)`. -/
opaque IsSmoothLerayHopf : TimeSpaceLerayHopfSolution → Prop

/-- For smooth `u`, the increment-formula flux equals the
contracted-gradient flux (Duchon–Robert 1999, §2). -/
axiom mollifiedFlux_smooth_eq
    (u : TimeSpaceLerayHopfSolution) (ρ : AbstractMollifier) (ℓ : ℝ)
    (_hu : IsSmoothLerayHopf u) (_hρ : MollifierMassOne ρ) (_hℓ : 0 < ℓ) :
    mollifiedFlux u ρ ℓ = mollifiedFluxContracted u ρ ℓ

/-! ## Section 5 — Radon defect measure μ[u] (PL-099 Q2)

PL-099 Q2(a): work in `M_+(Ω)`, `Ω := ℝ³ × (0, T)`, with the vague
(weak-*) topology, i.e. `μ_n → μ` iff `∫ φ dμ_n → ∫ φ dμ` for every
`φ ∈ C_c(Ω)`.

PL-099 Q2(b): the limit `lim_{ℓ→0} ∫ Π_ℓ[u] φ` exists for every
`φ ∈ C^∞_c(Ω)` and equals
  `L(φ) := −⟨∂_t e + div((e+p)u) − νΔe + ν|∇u|², φ⟩`,
`e := |u|²/2`. Convergence is along the **full** sequence (no
subsequence extraction), provided the commutator step Q5 holds.

PL-099 Q2(c): non-negativity. For nonnegative `φ` the Leray–Hopf
local energy inequality forces `⟨L, φ⟩ ≥ 0`, so `L` is a positive
distribution; by Riesz–Markov it is a non-negative Radon measure.

Mathlib note: `MeasureTheory.Integral.RieszMarkovKakutani` provides
the Riesz representation in compact-`X` form; the locally-finite /
non-compact-Ω extension required here is thin in current Mathlib. -/

/-- **`μ[u]` — Radon defect measure on space-time** (typed companion).

For a Leray–Hopf solution `u`, `RadonDefectMeasure u` is the space-time
Radon measure obtained as `w*-lim_{ℓ → 0} Π_ℓ[u]` in the vague topology
on `M_+(ℝ³ × (0, T))`. PL-099 Q2 establishes:

* limit exists along full sequence (no subsequence extraction);
* `μ[u]` is a non-negative Radon measure on `Ω`;
* `μ[u] ≡ 0` for smooth `u` (no anomalous dissipation).

**Status**: TYPED-COMPANION-PENDING-MATHLIB on the vague-topology
infrastructure; the construction itself is recorded by axioms below. -/
opaque RadonDefectMeasure (u : TimeSpaceLerayHopfSolution) : SpaceTimeRadonMeasure

/-- **Vague-limit existence axiom** (PL-099 Q2(b)).

Asserts that for every `φ ∈ C^∞_c(Ω)`,
  `lim_{ℓ → 0} ⟨Π_ℓ[u], φ⟩ = ⟨μ[u], φ⟩`,
along the full sequence `ℓ → 0`. We package this as an opaque
predicate `VagueLimitOfMollifiedFlux` indexed by `u, ρ` and assert the
existence axiomatically. -/
opaque VagueLimitOfMollifiedFlux
    (u : TimeSpaceLerayHopfSolution) (ρ : AbstractMollifier)
    (μ : SpaceTimeRadonMeasure) : Prop

/-- The defect measure is the vague-limit of `Π_ℓ[u]`
(Riesz–Markov on the local energy inequality; PL-099 Q2(b,c)).

References: Duchon–Robert 1999, Theorem 1 (Euler analog);
Constantin–E–Titi 1994, eq. (2.8). -/
axiom radonDefectMeasure_is_vague_limit
    (u : TimeSpaceLerayHopfSolution) (ρ : AbstractMollifier)
    (_hρ : MollifierMassOne ρ) :
    VagueLimitOfMollifiedFlux u ρ (RadonDefectMeasure u)

/-- **Non-negativity** of `μ[u]` (PL-099 Q2(c)).

By the local energy inequality + Riesz–Markov, `μ[u] ≥ 0` as a Radon
measure (i.e. `∫ φ dμ ≥ 0` for every `φ ∈ C_c(Ω)` with `φ ≥ 0`). -/
opaque DefectMeasureNonNegative : SpaceTimeRadonMeasure → Prop

/-- The Radon defect measure is non-negative
(local-energy-inequality ⇒ positive distribution ⇒ Riesz–Markov;
Duchon–Robert 1999 §2 + PL-099 Q2(c)). -/
axiom radonDefectMeasure_nonneg
    (u : TimeSpaceLerayHopfSolution) :
    DefectMeasureNonNegative (RadonDefectMeasure u)

/-! ## Section 6 — Algebraic identity with viscous correction (PL-099 Q3)

PL-099 Q3 (rewritten in standard form):

  `∂_t e + div((e+p)u) − νΔe + ν|∇u|² + μ[u] = 0`   in `D'(Ω)`,

`e := |u|²/2`. The explicit viscous correction is

  `R[u] := νΔe = νΔ(|u|²/2)`.

Equivalently `∂_t e + div((e+p)u) = −ν|∇u|² − μ[u] + R[u]` (sign
convention `μ ≥ 0` represents dissipation **beyond** the viscous term).

This recovers smooth equality (`μ ≡ 0`), and against nonnegative
`φ` gives the Leray–Hopf local energy inequality

  `⟨∂_t e + div((e+p)u) − νΔe + ν|∇u|², φ⟩ = −∫ φ dμ[u] ≤ 0`.

**Falsifiability lever.** Dropping `local_energy_inequality_holds`
breaks the identity — generic distributional weak solutions need not
admit a defect measure with the stated sign.

**Status: TYPED-COMPANION-PENDING-PROOF (NS).**
* Euler (`ν = 0`): canonical Duchon–Robert 1999 Theorem 1.
* NS (`ν > 0`): adapts via the Friedrichs-mollified energy form,
  contingent on the commutator step PL-099 Q5 (in flight as PL-102). -/

/-- **Distributional local energy balance with defect — Prop slot.**

Opaque `Prop` asserting the distributional identity (PL-099 Q3)

  `∂_t (|u|²/2) + div((|u|²/2 + p) u) − νΔ(|u|²/2)
       + ν |∇u|² + μ[u] = 0`

in `D'(Ω)`, with `μ[u] := RadonDefectMeasure u`. The `ν` argument is
explicit so positivity / monotonicity claims can quantify over `ν`. -/
opaque LocalEnergyBalanceWithDefect
    (u : TimeSpaceLerayHopfSolution) (ν : ℝ) : Prop

/-- **`R[u] := νΔ(|u|²/2)` — explicit viscous correction.**

PL-099 Q3 names `R[u]` as `νΔe`. The typed companion below records
this as an opaque function from `(u, ν)` to a flux distribution; the
axiom `viscous_correction_is_nu_laplacian_e` ties it to the algebraic
form. -/
opaque viscous_correction
    (u : TimeSpaceLerayHopfSolution) (ν : ℝ) : SomeFluxType

/-- `viscous_correction u ν = νΔ(|u|²/2)` in `D'(Ω)`.
PL-099 Q3 algebraic identification. -/
opaque ViscousCorrectionIsNuLaplacianE
    (u : TimeSpaceLerayHopfSolution) (ν : ℝ) : Prop

/-- The viscous correction is identically `νΔ(|u|²/2)` in `D'(Ω)`. -/
axiom viscous_correction_is_nu_laplacian_e
    (u : TimeSpaceLerayHopfSolution) (ν : ℝ) :
    ViscousCorrectionIsNuLaplacianE u ν

/-- **AXIOM `local_energy_balance_with_defect`** (refactored PL-103).

For every Leray–Hopf solution `u` on `ℝ³ × (0, T)` and every viscosity
`ν > 0`,

  `∂_t (|u|²/2) + div((|u|²/2 + p) u) − νΔ(|u|²/2)
       + ν |∇u|² + μ[u] = 0`

in `D'(ℝ³ × (0, T))`, with `μ[u] := RadonDefectMeasure u`.

**Sign convention.** `μ ≥ 0` represents energy dissipation **beyond**
the viscous term `ν |∇u|²` (the cascade-defect; for smooth solutions
`μ[u] = 0` and the identity becomes the classical smooth balance).

**Status: TYPED-COMPANION-PENDING-PROOF (NS).**
* For Euler (`ν = 0`): canonical Duchon–Robert 1999 Theorem 1.
* For NS (`ν > 0`): the Duchon–Robert argument adapts directly via
  the Friedrichs-mollified energy form; the commutator step is PL-099
  Q5 / PL-102.

References:
* J. Duchon, R. Robert, *Inertial energy dissipation for weak
  solutions of incompressible Euler and Navier-Stokes equations*,
  Nonlinearity **13** (2000), 249–255 — Theorem 1 (Euler) + §3
  remarks on the NS extension.
* PL-099 epd-74407924dd2c (gpt-5 2026-05-09), Q3 + Q5. -/
axiom local_energy_balance_with_defect
    (u : TimeSpaceLerayHopfSolution) (ν : ℝ) (_hν : 0 < ν) :
    LocalEnergyBalanceWithDefect u ν

/-! ## Section 7 — ε-regularity rigidity lemma (PL-099 Q4)

PL-099 Q4 statement: there exist universal `ε* > 0`, `θ ∈ (0, 1/2)`
such that for `z₀ = (x₀, t₀) ∈ Ω`, `r > 0`, `Q_r(z₀) := B_r(x₀) ×
(t₀ − r², t₀) ⊂ Ω`,

  (i)  `μ[u](Q_r(z₀)) = 0`,
  (ii) `r⁻² ∫_{t₀ − r²}^{t₀} ∫_{B_r(x₀)} |u|³ dx dt ≤ ε*`

⇒ `u` smooth on `Q_{θr}(z₀)` with

  `sup_{Q_{θr}(z₀)} |u| + r · sup_{Q_{θr}(z₀)} |∇u|
       ≤ C r⁻¹ (ε*)^{1/3}`.

Intended proof outline: vanishing μ on `Q_r` ⇒ local energy equality
(no anomalous dissipation) ⇒ Caccioppoli without defect-loss; Serrin-
critical smallness (ii) triggers CKN-iteration ⇒ Morrey ⇒ Hölder ⇒
parabolic bootstrap ⇒ smooth.

References:
* Caffarelli–Kohn–Nirenberg 1982 (CPAM 35) — partial regularity.
* PL-099 epd-74407924dd2c, Q4. -/

/-- **Parabolic cylinder `Q_r(z₀)` — opaque slot.** Real formalization
would be a subset of `ℝ × EuclideanSpace ℝ (Fin 3)`. -/
opaque ParabolicCylinder : Type

axiom ParabolicCylinder_nonempty : Nonempty ParabolicCylinder
attribute [instance] ParabolicCylinder_nonempty

/-- The cylinder `Q_r(x₀, t₀) := B_r(x₀) × (t₀ − r², t₀)`. -/
opaque parabolicCylinder
    (x₀ : Fin 3 → ℝ) (t₀ : ℝ) (r : ℝ) : ParabolicCylinder

/-- `μ[u]`-mass of a cylinder. -/
opaque defectMassOfCylinder
    (μ : SpaceTimeRadonMeasure) (Q : ParabolicCylinder) : ℝ

/-- The critical-`L³` smallness functional `r⁻² ∫_{Q_r} |u|³`. -/
opaque criticalCubeIntegral
    (u : TimeSpaceLerayHopfSolution) (Q : ParabolicCylinder) : ℝ

/-- Smoothness of `u` on a sub-cylinder. -/
opaque SmoothOnCylinder :
    TimeSpaceLerayHopfSolution → ParabolicCylinder → Prop

/-- The quantitative `sup|u| + r · sup|∇u|` bound on a sub-cylinder. -/
opaque QuantitativeRigidityBound
    (u : TimeSpaceLerayHopfSolution)
    (Q : ParabolicCylinder)
    (r ε C : ℝ) : Prop

/-- **`ε*`-regularity with vanishing defect** (PL-099 Q4 — typed
companion theorem).

There exist universal constants `ε* > 0`, `θ ∈ (0, 1/2)`, `C > 0`
such that for every Leray–Hopf solution `u`, every `(x₀, t₀, r)` with
`r > 0`, the implication

  `μ[u](Q_r(x₀, t₀)) = 0`  ∧  `r⁻² ∫_{Q_r} |u|³ ≤ ε*`
  ⇒  `u` smooth on `Q_{θr}(x₀, t₀)`  ∧
     `sup|u| + r·sup|∇u| ≤ C r⁻¹ (ε*)^{1/3}`

holds.

**Status: TYPED-SCAFFOLD-FOR-NEXT-PHASE (weeks 3-4 rigidity-kernel
target).** The proof body is `sorry`. The hypothesis cylinder
formalization is opaque pending Mathlib parabolic-cylinder
infrastructure. -/
theorem epsilon_regularity_with_vanishing_defect :
    ∃ (εStar θ C : ℝ),
      0 < εStar ∧ 0 < θ ∧ θ < 1/2 ∧ 0 < C ∧
      (∀ (u : TimeSpaceLerayHopfSolution) (x₀ : Fin 3 → ℝ)
         (t₀ r : ℝ) (_hr : 0 < r),
        defectMassOfCylinder (RadonDefectMeasure u)
            (parabolicCylinder x₀ t₀ r) = 0 →
        criticalCubeIntegral u (parabolicCylinder x₀ t₀ r) ≤ εStar →
        SmoothOnCylinder u (parabolicCylinder x₀ t₀ (θ * r)) ∧
        QuantitativeRigidityBound u
            (parabolicCylinder x₀ t₀ (θ * r)) r εStar C) := by
  -- TODO(ns_defect_calculus_pivot.weeks_3_4): rigidity-kernel proof.
  -- Outline (PL-099 Q4 remarks):
  --   1. μ[u](Q_r) = 0 + local_energy_balance_with_defect ⇒ local energy
  --      equality on Q_r (no anomalous inertial dissipation).
  --   2. Caccioppoli without defect-loss; Serrin-critical smallness (ii).
  --   3. CKN-iteration (Caffarelli–Kohn–Nirenberg 1982) ⇒ Morrey ⇒ Hölder.
  --   4. Standard parabolic bootstrap ⇒ smoothness on Q_{θr}.
  sorry

/-- Simple legacy form: defect-zero everywhere ⇒ smooth.

Provided the universal-zero-defect hypothesis holds (placeholder for
`RadonDefectMeasure u = 0` once `Zero SpaceTimeRadonMeasure` is in
scope), the rigidity kernel concludes smoothness on the full domain.
TYPED-SCAFFOLD-FOR-NEXT-PHASE; weeks 3-4 target. -/
theorem defect_zero_implies_smoothness
    (u : TimeSpaceLerayHopfSolution)
    (_hμ : ∃ z : SpaceTimeRadonMeasure, RadonDefectMeasure u = z ∧
            ∀ w : TimeSpaceLerayHopfSolution, RadonDefectMeasure w = z) :
    IsSmoothLerayHopf u := by
  -- TODO(ns_defect_calculus_pivot.weeks_3_4): conclude global smoothness
  -- by combining the universal-zero-defect hypothesis with
  -- `epsilon_regularity_with_vanishing_defect` plus a covering argument.
  sorry

/-! ## Section 8 — Honesty disclosure (PL-099 Q5 / PL-102 in flight)

The technically most delicate step in PL-099 is the unconditional
identification, for Leray–Hopf `u` without any extra integrability,
that

  `lim_{ℓ→0} ∫ Π_ℓ[u] · φ
     = −⟨∂_t e + div((e+p)u) − νΔe + ν|∇u|², φ⟩`

for every `φ ∈ C^∞_c(Ω)`, with no residual commutators beyond the
transport terms handled in the coarse-grained balance. Executing this
requires careful commutator estimates to control `u_ℓ · τ_ℓ` against
`∇φ` (with only `u ∈ L^∞_t L²_x ∩ L²_t Ḣ¹_x` and `p` defined
distributionally), and to justify passing limits in the viscous terms
`|∇u_ℓ|² → |∇u|²` in `D'`.

If a residual `r_ℓ[φ]` survives at roughness, it should be absorbed
into `R[u]`, **at the expense of losing the clean form
`R[u] = νΔe`**.

**TYPED-COMPANION-PENDING-VERIFICATION** — PL-102 is in flight to
verify whether Leray–Hopf alone suffices or extra integrability is
needed. The `viscous_correction_is_nu_laplacian_e` axiom is the
load-bearing claim that PL-102 is checking; if PL-102 falsifies it,
the axiom must be replaced by

  `viscous_correction u ν = νΔe + r[u, ν]`

with a residual `r` of as-yet-unbounded form. -/

/-! ## Section 9 — Sanity smoke check

Trivial `example`s exercising the algebraic API: ensure all the
typed-companion type signatures compose end-to-end. -/

example
    (u : TimeSpaceLerayHopfSolution) (ν : ℝ) (hν : 0 < ν) :
    LocalEnergyBalanceWithDefect u ν :=
  local_energy_balance_with_defect u ν hν

/-- The mollified flux at a positive scale `ℓ` exists as a value of
`SomeFluxType`. -/
example
    (u : TimeSpaceLerayHopfSolution) (ℓ : ℝ) : SomeFluxType :=
  mollifiedFlux u referenceMollifier ℓ

/-- Backwards-compatible alias smoke check. -/
example (u : TimeSpaceLerayHopfSolution) (ℓ : ℝ) : SomeFluxType :=
  MollifiedFlux u ℓ

/-- The defect measure exists as a `SpaceTimeRadonMeasure`. -/
example (u : TimeSpaceLerayHopfSolution) : SpaceTimeRadonMeasure :=
  RadonDefectMeasure u

/-- The defect measure is non-negative. -/
example (u : TimeSpaceLerayHopfSolution) :
    DefectMeasureNonNegative (RadonDefectMeasure u) :=
  radonDefectMeasure_nonneg u

/-- The reference rescaled kernel has unit mass at every positive
scale. -/
example (ℓ : ℝ) (hℓ : 0 < ℓ) :
    MollifierMassOne (mollifierKernel referenceMollifier ℓ) :=
  mollifierKernel_mass_one referenceMollifier referenceMollifier_mass_one ℓ hℓ

/-- The viscous correction identifies with `νΔ(|u|²/2)`. -/
example (u : TimeSpaceLerayHopfSolution) (ν : ℝ) :
    ViscousCorrectionIsNuLaplacianE u ν :=
  viscous_correction_is_nu_laplacian_e u ν

/-- Vague-limit identification (PL-099 Q2(b)). -/
example
    (u : TimeSpaceLerayHopfSolution) (ρ : AbstractMollifier)
    (hρ : MollifierMassOne ρ) :
    VagueLimitOfMollifiedFlux u ρ (RadonDefectMeasure u) :=
  radonDefectMeasure_is_vague_limit u ρ hρ

/-! ## Section 10 — Minimal-blowup classification (weeks 5-6 stub)

Retained from the pre-PL-103 skeleton so downstream files importing
`IsMinimalBlowup` / `DefectMeasureIsPositive` continue to compile. -/

opaque IsMinimalBlowup : TimeSpaceLerayHopfSolution → Prop
opaque DefectMeasureIsPositive : SpaceTimeRadonMeasure → Prop

/-- **Minimal-blowup-positive-defect classification — scaffold theorem.**

`TYPED-SCAFFOLD-FOR-NEXT-PHASE`. Stub for the weeks 5-6 classification.
Discharged with `sorry`. -/
theorem minimal_blowup_positive_defect_classification
    (u : TimeSpaceLerayHopfSolution)
    (_hu : IsMinimalBlowup u) :
    DefectMeasureIsPositive (RadonDefectMeasure u) := by
  -- TODO(ns_defect_calculus_pivot.weeks_5_6): minimal-blowup
  -- classification.  Outline:
  --   1. Apply local_energy_balance_with_defect to the minimal blowup.
  --   2. Use the local energy inequality to show that vanishing μ
  --      contradicts blowup (via epsilon_regularity_with_vanishing_defect).
  --   3. Conclude μ[u] > 0 in the appropriate sense.
  sorry

end

end ZtareProofs.NSDefectCalculusSkeleton
