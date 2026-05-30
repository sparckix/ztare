import Mathlib.Tactic
import Mathlib.Topology.Order.LiminfLimsup
import Mathlib.Order.Filter.Basic
import Mathlib.Topology.Algebra.Order.LiminfLimsup

/-!
# Bridge: typed-companion → `WeakSolution.weak_incompressible`

This file builds the bridge from a typed-companion record carrying
per-Galerkin-truncation divergence-free data + weak L² convergence to
the lean-dojo `weak_incompressible` clause shape:

```
weak_incompressible :
  ∀ t ∈ Set.Icc 0 T, ∀ ψ : Euc ℝ n → ℝ,
  ContDiff ℝ ⊤ ψ →
  (∃ K : Set (Euc ℝ n), IsCompact K ∧ ∀ x ∉ K, ψ x = 0) →
  ∫ x : Euc ℝ n, (∑ i : Fin n, partialDeriv i (λ y => u (pairToEuc t y) i) x * ψ x) = 0
```

(see `Problems/NavierStokes/Navierstokes.lean` lines 411-415).

## Bridge interpretation

For each Galerkin truncation `u_n`, the divergence-free property is
preserved by the Leray projection construction (`P_n` projects onto the
divergence-free subspace). For each test function `ψ`:

  ∫ ⟨u_n, ∇ψ⟩ dx = 0   for every n.

For the weak L² limit `u_∞`, weak convergence of `u_n ⇀ u_∞` against
`∇ψ` (which is itself an L² test field for compactly-supported smooth ψ)
yields:

  ∫ ⟨u_n, ∇ψ⟩ → ∫ ⟨u_∞, ∇ψ⟩.

Combined with the per-n vanishing, uniqueness of limits in ℝ gives
`∫ ⟨u_∞, ∇ψ⟩ = 0`.

This is the standard PDE bookkeeping for passing to the limit in the
weak incompressibility clause.

## Architecture

We work at the level of an abstract `VelocityFieldInterface` proxy
(matching `ns_trackb_lean_dojo_energy_bridge.lean`) extended with a
test-function pairing field `divergenceTest`. The bridge collapses the
PDE content to two structural hypotheses:

1. Per-n vanishing of the divergence-test pairing.
2. Weak convergence of the divergence-test pairing.

The substantive PDE work lives outside this bridge: somebody else must
verify (a) Leray-projection divergence-free preservation at each n, and
(b) weak L² convergence of the Galerkin sequence. Once those are
supplied, this bridge produces the clause shape mechanically.
-/

namespace ZtareProofs.NS

noncomputable section

universe u

/-! ## Extended velocity-field interface

We extend the proxy `VelocityFieldInterface` from
`ns_trackb_lean_dojo_energy_bridge.lean` (we redefine here as a
self-contained record for compile isolation; instances align via the
nominally-equivalent fields if both files are imported together). -/

/-- Self-contained proxy carrying just the test-function pairing needed
for `weak_incompressible`.

`divergenceTest ψ t` proxies for `∫ x, (∑ i, ∂ᵢ uᵢ(t,x) * ψ x)` —
i.e. the integral that the lean-dojo clause asserts equals zero. We
treat `ψ` as represented by a scalar parameter (its identity / index)
to keep the proxy first-order; in a fully typed instantiation, `ψ`
would carry its function-shape and compact-support data. -/
structure VelocityFieldDivInterface (n : ℕ) where
  /-- The divergence-test pairing: for time `t` and test-function index
  encoded as an `ℝ`, returns the integrated pairing. -/
  divergenceTest : (ℝ → ℝ) → ℝ → ℝ

/-! ## Typed-companion data: per-n divergence-free + weak convergence -/

/-- Typed companion carrying the two PDE inputs required to discharge
`weak_incompressible` at the limit:

1. `per_n_divergence_free`: for every Galerkin truncation `u_n`, every
   admissible time `t`, every test function `ψ`, the divergence-test
   pairing vanishes.
2. `weak_convergence`: the divergence-test pairings at the truncations
   converge to the limit's pairing.

The third field, `time_in_interval`, is simply the time-restriction
hypothesis; it's stored as a Prop input so the bridge consumer can
discharge it with their per-clause `t ∈ Set.Icc 0 T` hypothesis. -/
structure WeakIncompressibilityData (n : ℕ) where
  galerkinSeq : ℕ → VelocityFieldDivInterface n
  uInf : VelocityFieldDivInterface n
  /-- Per-n divergence-free property, preserved by Leray projection. -/
  per_n_divergence_free :
    ∀ (k : ℕ) (ψ : ℝ → ℝ) (t : ℝ),
      (galerkinSeq k).divergenceTest ψ t = 0
  /-- Weak L² convergence of the divergence-test pairings.
  Concretely: for fixed `(ψ, t)`, the sequence
  `n ↦ ∫ ⟨u_n(t,·), ∇ψ⟩` converges in ℝ to `∫ ⟨u_∞(t,·), ∇ψ⟩`. -/
  weak_convergence :
    ∀ (ψ : ℝ → ℝ) (t : ℝ),
      Filter.Tendsto
        (fun k => (galerkinSeq k).divergenceTest ψ t)
        Filter.atTop
        (nhds (uInf.divergenceTest ψ t))

/-! ## Core lemma: weak limit preserves zero

The mathematical core. Given a sequence of reals, all equal to zero,
that converges to a limit `L`, conclude `L = 0`. This is the standard
"limit of zeros is zero" argument via uniqueness of limits in a
Hausdorff space. -/

/-- If `a_n → L` and every `a_n = 0`, then `L = 0`.

Proof: `a_n = 0` makes the sequence the constant zero sequence, which
converges to `0`. Uniqueness of limits in ℝ (Hausdorff) gives `L = 0`. -/
lemma limit_of_zero_sequence_is_zero
    {a : ℕ → ℝ} {L : ℝ}
    (h_zero : ∀ k, a k = 0)
    (h_tendsto : Filter.Tendsto a Filter.atTop (nhds L)) :
    L = 0 := by
  -- Replace `a` with the constant zero function via `h_zero`.
  have h_eq : a = (fun _ : ℕ => (0 : ℝ)) := by
    funext k
    exact h_zero k
  rw [h_eq] at h_tendsto
  -- Now `Tendsto (fun _ => 0) atTop (𝓝 L)` and the constant sequence's
  -- canonical limit is `0`. Use uniqueness of limits.
  have h_const : Filter.Tendsto (fun _ : ℕ => (0 : ℝ)) Filter.atTop (nhds 0) :=
    tendsto_const_nhds
  -- Uniqueness of limits: in a Hausdorff space, a sequence has at most
  -- one limit. ℝ is T2 (Hausdorff), so the limits coincide.
  exact (tendsto_nhds_unique h_const h_tendsto).symm

/-! ## Bridge corollary: produce the lean-dojo-shape clause for `u_∞`

Given a `WeakIncompressibilityData` record, produce, for any test
function `ψ` and admissible time `t`, the vanishing of the limit's
divergence-test pairing. -/

/-- The bridge corollary, in a form parallel to the lean-dojo clause.
The lean-dojo clause asserts an integral over `Euc ℝ n` equals zero;
here, the proxy `divergenceTest ψ t` plays that role. -/
theorem weakIncompressibility_from_typed_companion
    {n : ℕ}
    (D : WeakIncompressibilityData n)
    (ψ : ℝ → ℝ) (t : ℝ) :
    D.uInf.divergenceTest ψ t = 0 := by
  -- Step 1: each truncation's pairing vanishes.
  have h_each_zero :
      ∀ k, (D.galerkinSeq k).divergenceTest ψ t = 0 :=
    fun k => D.per_n_divergence_free k ψ t
  -- Step 2: the weak-convergence hypothesis gives the sequence's limit.
  have h_tendsto :
      Filter.Tendsto
        (fun k => (D.galerkinSeq k).divergenceTest ψ t)
        Filter.atTop
        (nhds (D.uInf.divergenceTest ψ t)) :=
    D.weak_convergence ψ t
  -- Step 3: apply the core "limit of zeros is zero" lemma.
  exact limit_of_zero_sequence_is_zero h_each_zero h_tendsto

/-! ## Lean-dojo-shape adapter

The lean-dojo clause additionally has the universally-quantified
prologue `∀ t ∈ Set.Icc 0 T, ∀ ψ, ContDiff ℝ ⊤ ψ → ⟨compact-support⟩ → …`.
At the proxy level we don't model `ContDiff` or compact-support data
(both are independent regularity inputs), but we record a quantified
version for downstream callers who need to feed the clause into the
lean-dojo `WeakSolution` constructor. -/

/-- Lean-dojo-shape clause for the limit solution `u_∞`: for every
admissible time `t` and every test-function index `ψ`, the
divergence-test pairing vanishes.

When this proxy is composed with a concrete realization (i.e. the
`Euc ℝ n → ℝ` and `partialDeriv` integral are wired in), this
universally-quantified statement directly fits the lean-dojo clause
shape after dropping the regularity hypotheses (which are independent
inputs to the bridge consumer). -/
theorem weakIncompressibility_clause_for_uInf
    {n : ℕ}
    (D : WeakIncompressibilityData n)
    (T : ℝ) :
    ∀ t ∈ Set.Icc (0 : ℝ) T, ∀ ψ : ℝ → ℝ,
      D.uInf.divergenceTest ψ t = 0 := by
  intro t _ht ψ
  exact weakIncompressibility_from_typed_companion D ψ t

/-! ## Composition note

This bridge composes with the energy-inequality bridge in
`ns_trackb_lean_dojo_energy_bridge.lean` and the initial-condition /
weak-momentum bridges (analogous typed-companion patterns) to give a
mechanical reduction of the full `WeakSolution` constructor:

- `velocity_regularity` ← Sobolev-bound typed companion (separate).
- `weak_momentum_equation` ← weak-form-passage typed companion
  (separate; structurally identical to this bridge but for the full
  momentum quintuple integral).
- `weak_incompressible` ← THIS bridge.
- `weak_initial_condition` ← initial-condition matching typed companion.

In each case the typed companion isolates the load-bearing PDE input
(weak convergence, LSC, or compactness) so the lean-dojo clause shape
is produced mechanically. -/

end

end ZtareProofs.NS
