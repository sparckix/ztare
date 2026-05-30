/-
  ns_trackb_krf_cantor_diagonal.lean

  Cantor diagonal subsequence extraction.

  Setup: a sequence of subsequence-extractions `φ : ℕ → ℕ → ℕ` satisfying:
    * each `φ k` is strictly monotone (it is itself an indexing function), and
    * `φ (k+1)` is a subsequence of `φ k`, i.e. `φ (k+1) = φ k ∘ τ k`
      for some strictly monotone `τ k : ℕ → ℕ`.

  Conclusion: there is a single strictly monotone `ψ : ℕ → ℕ` such that
  for every `k`, eventually (for `n ≥ k`), `ψ n` lies in the range of `φ k`,
  i.e. `(ψ n)_{n ≥ k}` is a subsequence of `(φ k m)_m`.

  This is the classical Cantor diagonal extraction used in Arzelà–Ascoli /
  Heine–Borel style compactness arguments. It is needed for the KRF
  (Kolmogorov–Riesz–Fréchet) compactness step in NS Track B: we have a
  sequence of subsequences indexed by `δ_k → 0`, each giving uniform
  convergence at scale `δ_k`. The Cantor diagonal produces a single
  subsequence converging at every scale.

  Mathlib status: `StrictMono.comp` and `StrictMono.le_apply` (in
  `Mathlib.Order.WellFounded`) are used; the diagonal lemma itself is
  proved here directly (it does not appear under names such as
  `cantor_diag*`, `*subseq_diag*`, or `diagonal_extract*` in Mathlib as of
  v4.30.0-rc2). The construction is the standard `ψ n := φ n n` once the
  φ's have been pre-composed into nested form.
-/

import Mathlib.Order.Monotone.Defs
import Mathlib.Order.WellFounded
import Mathlib.Tactic.Common
import Mathlib.Tactic.Linarith

namespace ZtareProofs.KRF

open Function

/-- **Cantor diagonal subsequence extraction.**

    Given a family of strict-mono indexings `φ k : ℕ → ℕ` such that each
    `φ (k+1)` is a subsequence of `φ k` via a strict-mono extractor `τ k`
    (i.e. `φ (k+1) = φ k ∘ τ k`), there exists a single strict-mono
    `ψ : ℕ → ℕ` such that for every `k`, `(ψ n)_{n ≥ k}` is a subsequence
    of `(φ k m)_m`.

    Construction: `ψ n := φ n n` (the diagonal). -/
theorem cantor_diagonal_subsequence
    (φ : ℕ → ℕ → ℕ)
    (h_strict : ∀ k, StrictMono (φ k))
    (τ : ℕ → ℕ → ℕ)
    (h_tau_strict : ∀ k, StrictMono (τ k))
    (h_nest : ∀ k n, φ (k+1) n = φ k (τ k n)) :
    ∃ ψ : ℕ → ℕ, StrictMono ψ ∧
      ∀ k, ∀ n, k ≤ n → ∃ m, ψ n = φ k m := by
  -- The diagonal.
  refine ⟨fun n => φ n n, ?_, ?_⟩
  · -- Strict monotonicity of `n ↦ φ n n`.
    -- For successor steps: φ (n+1) (n+1) = φ n (τ n (n+1)) > φ n n,
    -- because τ n (n+1) > τ n n ≥ n+1 > n on ℕ (StrictMono.le_apply).
    -- Then extend to arbitrary `<` by transitivity.
    have step : ∀ n, φ n n < φ (n+1) (n+1) := by
      intro n
      have h1 : φ (n+1) (n+1) = φ n (τ n (n+1)) := h_nest n (n+1)
      have h2 : n < τ n (n+1) := by
        have hle : n + 1 ≤ τ n (n+1) := (h_tau_strict n).le_apply
        exact Nat.lt_of_lt_of_le (Nat.lt_succ_self n) hle
      have h3 : φ n n < φ n (τ n (n+1)) := (h_strict n) h2
      simpa [h1] using h3
    intro a b hab
    -- standard: strict_mono from successor step.
    induction hab with
    | refl => exact step a
    | step _ ih => exact lt_trans ih (step _)
  · -- Subsequence-of-φ k condition: for n ≥ k, ψ n = φ n n is in range of φ k.
    -- Iterating the nesting equation: for any k ≤ n,
    --   φ n m = φ k (T k n m) where T k n is the composition τ (n-1) ∘ ... ∘ τ k.
    -- We package this as a helper.
    -- We prove by induction on `n - k`.
    have nest_iter : ∀ k d n, n = k + d → ∀ m, ∃ m', φ n m = φ k m' := by
      intro k d
      induction d with
      | zero =>
          intro n hn m
          subst hn
          exact ⟨m, rfl⟩
      | succ d ih =>
          intro n hn m
          -- n = k + (d+1) = (k + d) + 1
          have hn' : n = (k + d) + 1 := by omega
          -- Use nest at level (k+d): φ (k+d+1) m = φ (k+d) (τ (k+d) m).
          have key : φ n m = φ (k + d) (τ (k + d) m) := by
            rw [hn']; exact h_nest (k + d) m
          -- Then induction hypothesis at n' := k + d.
          obtain ⟨m', hm'⟩ := ih (k + d) rfl (τ (k + d) m)
          exact ⟨m', by rw [key, hm']⟩
    intro k n hkn
    obtain ⟨d, hd⟩ : ∃ d, n = k + d := ⟨n - k, by omega⟩
    exact nest_iter k d n hd n

end ZtareProofs.KRF
