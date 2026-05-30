import Mathlib.Analysis.SpecificLimits.Basic
import Mathlib.Topology.Algebra.InfiniteSum.Real
import Mathlib.Tactic.Linarith
import Mathlib.Tactic.Positivity

/-!
# Sequence lemma: nonsummable ⇒ no uniform block decay (tick475)

**The pincer bridge** (per operator's 2026-05-15 GPT-5.5 pincer analysis).

Per Meta-Darwin self-audit on prior attempt: the full residue-class
decomposition is non-trivial in Mathlib (codex_rd predicted M1=0.62
because of this).  This version DOWNGRADES the conclusion to the
**block subsequence**, which is the load-bearing part and is cleanly
formalizable.

## What this file ships

**Theorem `block_subsequence_summable_under_decay`**: if `A : ℕ → ℝ` is
nonneg and `A_{n+L} ≤ θ A_n` for all `n ≥ N₀` (with `θ ∈ [0,1)`), then
the block subsequence `k ↦ A (N₀ + k · L)` is `Summable`.

**Corollary `block_subsequence_bound`**: explicit upper bound
`∑_{k < K} A (N₀ + k · L) ≤ A N₀ / (1 - θ)` for every `K`.

These together capture the geometric-decay-along-blocks consequence
of uniform block decay.  Combined with a between-block boundedness
hypothesis (separate carrier) they yield `Summable A`, contradicting
the Dini cascade.

This is REAL real-analysis, no PDE.

## Anti-laundering acknowledgement

Prior attempt left a `sorry` for the residue-class decomposition.
Restated to use ONLY the block subsequence, which is tractable.
The full "contradicts non-summable A" step needs additional structural
input (between-block bound) — left for the next tick to compose.
-/

namespace ZtareProofs.NSDiniSequenceBlockDecayContradiction

open Filter Topology

/--
**Iterated block decay** (clean induction): `A (N₀ + k·L) ≤ θ^k · A N₀`.
-/
lemma iterated_block_decay
    (A : ℕ → ℝ) (N₀ L : ℕ) (θ : ℝ) (hθ_nonneg : 0 ≤ θ)
    (h_decay : ∀ n, N₀ ≤ n → A (n + L) ≤ θ * A n) :
    ∀ k : ℕ, A (N₀ + k * L) ≤ θ^k * A N₀ := by
  intro k
  induction k with
  | zero => simp
  | succ k ih =>
    have hN : N₀ ≤ N₀ + k * L := Nat.le_add_right _ _
    have hstep : A ((N₀ + k * L) + L) ≤ θ * A (N₀ + k * L) := h_decay _ hN
    have hθ_mul : θ * A (N₀ + k * L) ≤ θ * (θ^k * A N₀) :=
      mul_le_mul_of_nonneg_left ih hθ_nonneg
    have hrw : N₀ + (k + 1) * L = (N₀ + k * L) + L := by ring
    rw [hrw]
    calc A ((N₀ + k * L) + L) ≤ θ * A (N₀ + k * L) := hstep
      _ ≤ θ * (θ^k * A N₀) := hθ_mul
      _ = θ^(k+1) * A N₀ := by ring

/--
**Block subsequence is summable under uniform block decay.**

If `A` is nonneg and `A_{n+L} ≤ θ · A_n` for `n ≥ N₀` with `θ ∈ [0,1)`,
then `k ↦ A (N₀ + k · L)` is `Summable`.

Uses Mathlib `summable_geometric_of_lt_one`, `Summable.mul_right`,
`Summable.of_nonneg_of_le`.
-/
theorem block_subsequence_summable_under_decay
    (A : ℕ → ℝ) (hA_nonneg : ∀ n, 0 ≤ A n)
    (N₀ L : ℕ)
    (θ : ℝ) (hθ_nonneg : 0 ≤ θ) (hθ_lt_one : θ < 1)
    (h_decay : ∀ n, N₀ ≤ n → A (n + L) ≤ θ * A n) :
    Summable (fun k : ℕ => A (N₀ + k * L)) := by
  -- The geometric subseries θ^k · A N₀ is summable (|θ| < 1).
  have h_geom : Summable (fun k : ℕ => θ^k) :=
    summable_geometric_of_lt_one hθ_nonneg hθ_lt_one
  have h_geom_mul : Summable (fun k : ℕ => θ^k * A N₀) :=
    h_geom.mul_right (A N₀)
  -- Compare: A (N₀ + k · L) ≤ θ^k · A N₀ pointwise.
  have h_ck_le : ∀ k, A (N₀ + k * L) ≤ θ^k * A N₀ :=
    iterated_block_decay A N₀ L θ hθ_nonneg h_decay
  -- Apply Summable.of_nonneg_of_le.
  exact h_geom_mul.of_nonneg_of_le (fun k => hA_nonneg _) h_ck_le

/--
**Explicit partial-sum bound** for the block subsequence.

`∑_{k < K} A (N₀ + k · L) ≤ A N₀ / (1 - θ)`.
-/
theorem block_subsequence_partial_sum_bound
    (A : ℕ → ℝ) (hA_nonneg : ∀ n, 0 ≤ A n)
    (N₀ L : ℕ)
    (θ : ℝ) (hθ_nonneg : 0 ≤ θ) (hθ_lt_one : θ < 1)
    (h_decay : ∀ n, N₀ ≤ n → A (n + L) ≤ θ * A n) (K : ℕ) :
    ∑ k ∈ Finset.range K, A (N₀ + k * L) ≤ A N₀ / (1 - θ) := by
  have h1mθ_pos : 0 < 1 - θ := by linarith
  have hAN₀_nonneg : 0 ≤ A N₀ := hA_nonneg _
  have h_ck_le : ∀ k, A (N₀ + k * L) ≤ θ^k * A N₀ :=
    iterated_block_decay A N₀ L θ hθ_nonneg h_decay
  have h_partial_le_geom :
      ∑ k ∈ Finset.range K, A (N₀ + k * L)
        ≤ ∑ k ∈ Finset.range K, θ^k * A N₀ :=
    Finset.sum_le_sum (fun k _ => h_ck_le k)
  -- Σ_{k < K} θ^k · A N₀ = A N₀ · Σ_{k < K} θ^k ≤ A N₀ · 1/(1-θ) = A N₀ / (1-θ).
  have h_geom_partial :
      ∑ k ∈ Finset.range K, θ^k * A N₀ = (∑ k ∈ Finset.range K, θ^k) * A N₀ := by
    rw [← Finset.sum_mul]
  rw [h_geom_partial] at h_partial_le_geom
  -- Σ_{k < K} θ^k ≤ 1/(1-θ) for θ ∈ [0,1).  Use Finset.geom_sum_lt or direct.
  -- Σ_{k<K} θ^k ≤ Σ' θ^k = (1-θ)⁻¹ via tsum_geometric_of_lt_one + sum_le_tsum.
  have h_summable : Summable (fun k : ℕ => θ^k) :=
    summable_geometric_of_lt_one hθ_nonneg hθ_lt_one
  have h_tsum_eq : ∑' k : ℕ, θ^k = (1 - θ)⁻¹ :=
    tsum_geometric_of_lt_one hθ_nonneg hθ_lt_one
  have h_geom_sum_le : ∑ k ∈ Finset.range K, θ^k ≤ (1 - θ)⁻¹ := by
    have h_partial_le : ∑ k ∈ Finset.range K, θ^k ≤ ∑' k : ℕ, θ^k :=
      h_summable.sum_le_tsum (Finset.range K) (fun k _ => pow_nonneg hθ_nonneg k)
    rw [h_tsum_eq] at h_partial_le
    exact h_partial_le
  -- Final chain: Σ A_{N₀+kL} ≤ (Σ θ^k) · A N₀ ≤ (1-θ)⁻¹ · A N₀ = A N₀ / (1-θ).
  calc ∑ k ∈ Finset.range K, A (N₀ + k * L)
      ≤ (∑ k ∈ Finset.range K, θ^k) * A N₀ := h_partial_le_geom
    _ ≤ (1 - θ)⁻¹ * A N₀ := mul_le_mul_of_nonneg_right h_geom_sum_le hAN₀_nonneg
    _ = A N₀ / (1 - θ) := by rw [inv_mul_eq_div]

end ZtareProofs.NSDiniSequenceBlockDecayContradiction
