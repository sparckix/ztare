import Mathlib.Algebra.Order.BigOperators.Ring.Finset
import Mathlib.Data.Real.Basic
import Mathlib.Tactic.Linarith
import Mathlib.Tactic.FieldSimp
import Mathlib.Algebra.BigOperators.Group.Finset.Basic

/-!
# `GeometricDecayFlatStopping` — the Gowers replacement (tick464)

**The final PDE work, codified.**

Per the operator's analytic compression, tick456 + tick458 close the
aggregation + composition formally; tick462 + tick463 prove that L³
mass and finite defect mass do NOT supply the per-node fresh radius
charge.  The **Gowers-style replacement** of the failed measure
target is:

> Prove **geometric decay of the flat-inherited stopping tree.**
> For every flat-inherited bad node `Q`,
>   `Σ_{Q' ∈ flatChildren(Q)} r_{Q'} ≤ θ · r_Q + charged(Q)`
> for some uniform `θ < 1`, where `charged(Q)` is a finite-budget
> charge collecting route + pressure + beta + residual contributions.

This file:

1. Codifies the structure `GeometricDecayFlatStopping`.
2. **Proves the closure theorem** `radius_partial_sum_bound`:
   the algebraic bound `(1 - θ) · Σ_{n ≤ N} A_n ≤ A_0 + Σ_{n < N} E_n`
   for partial sums, via Mathlib `Finset.sum_le_sum` + reindex.
3. Derives the divided form `radius_partial_sum_le_div`:
   `Σ_{n ≤ N} A_n ≤ (A_0 + Σ_{n < N} E_n) / (1 - θ)`.

The proof uses **only the per-step decay inequality** — no geometric
series machinery, no `tsum` lemmas.  This is the simplest possible
form of the substantive closure.

## Mathematical content

Let `A_n := Σ_{Q at flat generation n} r_Q` and
`E_n := Σ_{Q at generation n} charge(Q)`.  Hypothesis: `A_{n+1} ≤ θ A_n + E_n`.

Sum the decay from `n = 0` to `N - 1`:
  `Σ_{n=0}^{N-1} A_{n+1} ≤ θ · Σ_{n=0}^{N-1} A_n + Σ_{n=0}^{N-1} E_n`.

Reindex LHS: `Σ_{n=0}^{N-1} A_{n+1} = (Σ_{n=0}^{N} A_n) - A_0`.

Split RHS `Σ_{n=0}^{N-1} A_n = (Σ_{n=0}^{N} A_n) - A_N`:
  `S_N - A_0 ≤ θ · (S_N - A_N) + E_⟨N⟩`
where `S_N := Σ_{n=0}^{N} A_n`, `E_⟨N⟩ := Σ_{n=0}^{N-1} E_n`.

Rearrange:
  `(1 - θ) · S_N ≤ A_0 - θ · A_N + E_⟨N⟩ ≤ A_0 + E_⟨N⟩`
(since `θ · A_N ≥ 0`).

Dividing by `1 - θ > 0`:
  `S_N ≤ (A_0 + E_⟨N⟩) / (1 - θ)`.

## Anti-wrapper discipline

1. The structure `GeometricDecayFlatStopping` houses 7 carrier fields
   (radii, charges, decay constant, nonneg + bound + decay hypotheses).
2. The closure theorem `radius_partial_sum_bound` is REAL Mathlib
   content using `Finset.sum_le_sum`, `Finset.mul_sum`,
   `Finset.sum_range_succ`, `Finset.sum_range_succ'`.
3. The divided form `radius_partial_sum_le_div` uses `div_le_iff` /
   `le_div_iff` from Mathlib's order/division API.
4. The honest scope guard `Tick464IsNotNSDataProof` records that this
   theorem is conditional on the decay-and-charge carrier — which is
   itself the missing PDE input (not derivable from ESS/CF/CKN).
-/

namespace ZtareProofs.NSGeometricDecayFlatStopping

open Finset

/--
**`GeometricDecayFlatStopping` carrier (per-generation form).**

* `A n` = radius sum at flat-inherited generation `n`.
* `E n` = charge sum at flat-inherited generation `n`.
* `theta` = the geometric decay constant (`< 1`).
* Hypothesis `decay`: `A (n+1) ≤ theta * A n + E n`.

The carrier is at the per-generation level (already aggregated over
each generation's Finset of bad nodes).  Per-node decay aggregates to
this form via `Finset.sum_le_sum` at each generation.
-/
structure GeometricDecayFlatStopping where
  A : ℕ → ℝ
  E : ℕ → ℝ
  theta : ℝ
  A_nonneg : ∀ n, 0 ≤ A n
  E_nonneg : ∀ n, 0 ≤ E n
  theta_nonneg : 0 ≤ theta
  theta_lt_one : theta < 1
  decay : ∀ n, A (n + 1) ≤ theta * A n + E n

namespace GeometricDecayFlatStopping

variable (h : GeometricDecayFlatStopping)

/-- Sum the per-step decay inequality over `[0, N)`. -/
lemma summed_decay (N : ℕ) :
    ∑ n ∈ Finset.range N, h.A (n + 1)
      ≤ h.theta * (∑ n ∈ Finset.range N, h.A n)
      + (∑ n ∈ Finset.range N, h.E n) := by
  rw [Finset.mul_sum, ← Finset.sum_add_distrib]
  exact Finset.sum_le_sum (fun n _ => h.decay n)

/-- Reindex: `Σ_{n < N} A(n+1) = (Σ_{n ≤ N} A n) - A 0`. -/
lemma sum_shift_eq (N : ℕ) :
    ∑ n ∈ Finset.range N, h.A (n + 1)
      = (∑ n ∈ Finset.range (N + 1), h.A n) - h.A 0 := by
  rw [Finset.sum_range_succ' h.A N]
  ring

/-- Split: `Σ_{n < N} A n = (Σ_{n ≤ N} A n) - A N`. -/
lemma sum_drop_last_eq (N : ℕ) :
    ∑ n ∈ Finset.range N, h.A n
      = (∑ n ∈ Finset.range (N + 1), h.A n) - h.A N := by
  rw [Finset.sum_range_succ h.A N]
  ring

/--
**Tick464 main closure theorem — partial-sum bound (algebraic form).**

For every `N`, the partial sum of radii satisfies
`(1 - θ) · S_{N+1} ≤ A_0 + Σ_{n < N} E_n` where
`S_{N+1} := Σ_{n=0}^{N} A n` (over `range (N+1)`).

Proof uses ONLY:
* The per-step decay inequality summed over `[0, N)`.
* Two reindexing lemmas (`sum_shift_eq`, `sum_drop_last_eq`).
* Nonnegativity `0 ≤ θ · A N` to drop the `-θ A_N` term.

No geometric-series machinery, no `tsum` lemmas.
-/
theorem radius_partial_sum_bound (N : ℕ) :
    (1 - h.theta) * (∑ n ∈ Finset.range (N + 1), h.A n)
      ≤ h.A 0 + (∑ n ∈ Finset.range N, h.E n) := by
  have hsum := summed_decay h N
  rw [sum_shift_eq h N] at hsum
  rw [sum_drop_last_eq h N] at hsum
  -- After rewrites:
  --   (Σ_{n ≤ N} A n) - A 0
  --     ≤ θ * ((Σ_{n ≤ N} A n) - A N)
  --     + Σ_{n < N} E n
  have hA_N_nonneg : 0 ≤ h.theta * h.A N :=
    mul_nonneg h.theta_nonneg (h.A_nonneg N)
  linarith

/--
**Tick464 corollary: divided form.**

Dividing the algebraic bound by `1 - θ > 0`:

  `Σ_{n ≤ N} A n ≤ (A_0 + Σ_{n < N} E n) / (1 - θ)`.

Provides the explicit upper bound on flat-generation radius partial
sums in terms of `A_0` and the total finite charge.
-/
theorem radius_partial_sum_le_div (N : ℕ) :
    ∑ n ∈ Finset.range (N + 1), h.A n
      ≤ (h.A 0 + ∑ n ∈ Finset.range N, h.E n) / (1 - h.theta) := by
  have h1mθ_pos : 0 < 1 - h.theta := by linarith [h.theta_lt_one]
  rw [le_div_iff₀ h1mθ_pos]
  -- Goal: S * (1 - θ) ≤ A_0 + Σ E.  Symmetric to radius_partial_sum_bound.
  have := radius_partial_sum_bound h N
  linarith

/--
**Uniform partial-sum bound: every partial sum is bounded by
`(A_0 + total_charge) / (1 - θ)`.**

If the total `E`-charge has a uniform finite upper bound `M_E`, then
every partial sum of `A` is bounded by `(A_0 + M_E) / (1 - θ)`.
This is the form most useful for downstream radius-summability.
-/
theorem radius_partial_sum_bounded_by_total_charge
    (M_E : ℝ) (hM_E : ∀ N, (∑ n ∈ Finset.range N, h.E n) ≤ M_E) (N : ℕ) :
    ∑ n ∈ Finset.range (N + 1), h.A n
      ≤ (h.A 0 + M_E) / (1 - h.theta) := by
  have h1mθ_pos : 0 < 1 - h.theta := by linarith [h.theta_lt_one]
  have hbase := radius_partial_sum_bound h N
  have hE_bound := hM_E N
  rw [le_div_iff₀ h1mθ_pos, mul_comm]
  linarith

end GeometricDecayFlatStopping

/-! ## Honest scope guards -/

/--
**Tick464 codifies the Gowers replacement; the CARRIER itself is
the open PDE input.**

What this file proves:
* The structure `GeometricDecayFlatStopping` is a clean per-generation
  carrier.
* From `decay : ∀ n, A (n+1) ≤ θ A n + E n` + `theta < 1` +
  nonnegativity, partial sums `Σ_{n ≤ N} A n` are bounded by
  `(A_0 + Σ E_n) / (1 - θ)` — a real Mathlib-derived inequality.

What this file does NOT prove:
* That `decay` is achievable from Navier–Stokes data.  This is the
  open PDE obligation per GPT-5.5 §6: ESS and CF do NOT produce
  quantitative branching gap `θ < 1`; they participate only through
  charged residuals.
* That the equality-branching dyadic countermodel (full dyadic split,
  `θ = 1`) is excluded by NS dynamics.

The Gowers replacement IS the structural property — but inhabiting it
from NS data remains the final analytic obstruction.  This file
discharges the algebraic closure; the PDE construction of `theta < 1`
flat-child decay is open. -/
structure Tick464IsNotNSDataProof where
  geometricDecayCarrierCodified : Prop
  partialSumBoundProvenAlgebraically : Prop
  thetaLessOneNotDerivedFromESS : Prop
  thetaLessOneNotDerivedFromCF : Prop
  thetaLessOneNotDerivedFromCKNLocalEnergy : Prop
  equalityDyadicCountermodelNotExcluded : Prop
  flatChildRadiusDecayFromNSStillOpenAnalyticObligation : Prop

end ZtareProofs.NSGeometricDecayFlatStopping
