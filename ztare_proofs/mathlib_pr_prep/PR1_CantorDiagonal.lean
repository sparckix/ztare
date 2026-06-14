/-
Copyright (c) 2026 Mathlib Contributors. All rights reserved.
Released under Apache 2.0 license as described in the file LICENSE.
Authors: Daniel Alami
-/
import Mathlib.Order.Monotone.Basic

/-!
# Diagonal subsequences

This file proves a diagonal extraction lemma for a nested family of strictly
monotone index maps on `ℕ`.

If every `φ (k + 1)` is a subsequence of `φ k`, the diagonal sequence
`fun n => φ n n` is strictly monotone and every tail of it is a subsequence of
the corresponding `φ k`.
-/

namespace Nat

/-- A diagonal extraction lemma for nested subsequences of `ℕ`.

Given a family of strict-mono index maps `φ k : ℕ → ℕ`, where each
`φ (k + 1)` factors through `φ k` by a strict-mono map `τ k`, there is a
strict-mono sequence `ψ` such that for every `k`, the tail `fun n => ψ (n + k)`
factors through `φ k` by a strict-mono map.

The witness is the diagonal sequence `fun n => φ n n`. -/
theorem exists_strictMono_diagonal_subsequence
    (φ : ℕ → ℕ → ℕ)
    (hφ : ∀ k, StrictMono (φ k))
    (τ : ℕ → ℕ → ℕ)
    (hτ : ∀ k, StrictMono (τ k))
    (h_nest : ∀ k n, φ (k + 1) n = φ k (τ k n)) :
    ∃ ψ : ℕ → ℕ, StrictMono ψ ∧
      ∀ k, ∃ σ : ℕ → ℕ, StrictMono σ ∧ ∀ n, ψ (n + k) = φ k (σ n) := by
  have strictMono_id_le : ∀ {f : ℕ → ℕ}, StrictMono f → ∀ n, n ≤ f n := by
    intro f hf n
    induction n with
    | zero => exact Nat.zero_le _
    | succ n ih =>
        exact Nat.succ_le_of_lt (lt_of_le_of_lt ih (hf (Nat.lt_succ_self n)))
  have step : ∀ n, φ n n < φ (n + 1) (n + 1) := by
    intro n
    have h1 : φ (n + 1) (n + 1) = φ n (τ n (n + 1)) := h_nest n (n + 1)
    have h2 : n < τ n (n + 1) := by
      have hle : n + 1 ≤ τ n (n + 1) := strictMono_id_le (hτ n) (n + 1)
      exact Nat.lt_of_lt_of_le (Nat.lt_succ_self n) hle
    exact h1 ▸ (hφ n h2)
  have hψ : StrictMono (fun n => φ n n) := strictMono_nat_of_lt_succ step
  refine ⟨fun n => φ n n, hψ, ?_⟩
  · have nest_iter : ∀ k d n, n = k + d → ∀ m, ∃ m', φ n m = φ k m' := by
      intro k d
      induction d with
      | zero =>
          intro n hn m
          subst hn
          exact ⟨m, rfl⟩
      | succ d ih =>
          intro n hn m
          have hn' : n = (k + d) + 1 := by
            rw [hn, Nat.add_succ]
          have key : φ n m = φ (k + d) (τ (k + d) m) := by
            rw [hn']
            exact h_nest (k + d) m
          obtain ⟨m', hm'⟩ := ih (k + d) rfl (τ (k + d) m)
          exact ⟨m', by rw [key, hm']⟩
    intro k
    have h_mem : ∀ n, ∃ m, φ (n + k) (n + k) = φ k m := by
      intro n
      exact nest_iter k n (n + k) (Nat.add_comm n k) (n + k)
    let σ : ℕ → ℕ := fun n => Classical.choose (h_mem n)
    refine ⟨σ, ?_, ?_⟩
    · intro a b hab
      have hσa : φ (a + k) (a + k) = φ k (σ a) := Classical.choose_spec (h_mem a)
      have hσb : φ (b + k) (b + k) = φ k (σ b) := Classical.choose_spec (h_mem b)
      have hψ_lt : φ (a + k) (a + k) < φ (b + k) (b + k) :=
        hψ (Nat.add_lt_add_right hab k)
      by_contra hle
      have hba : σ b ≤ σ a := Nat.le_of_not_lt hle
      have hφ_le : φ k (σ b) ≤ φ k (σ a) := (hφ k).monotone hba
      rw [← hσa, ← hσb] at hφ_le
      exact (not_le_of_gt hψ_lt) hφ_le
    · intro n
      exact Classical.choose_spec (h_mem n)

end Nat
