/-
# NS Track B — Tao 2019 log^k chain (typed companion, conjectural family)

This file ships the **iterated-log primitive family** `iterLog k` and
the formal *statement* of the conjecture that pushing Tao 2019's
triple-log L³ lower bound to higher `k` would sharpen the bound. The
content here is **primitives + named conjectures**; there are no PDE
theorems and no claim that `k > 3` is achievable in 3D.

## Why this file exists

PR-1c (`mathlib_pr_drafts/PR_1c_iterated_log.lean`) shipped a clipped
`triLog` (= `iterLog 3` here). The natural follow-on question is:

> Does the `log^k` chain — `quartLog`, `quintLog`, ..., `iterLog k` —
> give a strictly sharper lower bound on `‖u(t)‖_{L³}` near a
> hypothetical Navier-Stokes singularity, and does the limit
> `k → ∞` close the Beale-Kato-Majda time-integral criterion?

The companion analysis note
`projects/ns_millennium_hunt/workspace/research_notes/tao_2019_log_k_chain_2026_05_07.md`
documents the literature scan and the **negative result**:

* In 3D, Tao's own technical decomposition (Bourgain pigeonhole +
  backward-uniqueness Carleman + scale stacking → 3 exponentials)
  makes triple-log structural; published 2024-2026 follow-ups
  (Barker, Prange, Wang) extend the geometry but **do not increase
  `k`** in 3D.
* The `quartLog` appearance in the literature is a `d ≥ 4`
  phenomenon, not a 3D refinement.
* Even granting a hypothetical `log^k` improvement for arbitrary `k`,
  the limit `k → ∞` weakens the bound (every finite argument
  eventually falls below the iterated-threshold tower), so the
  iterated-log chain DOES NOT close BKM. It converges to the trivial
  lower bound `‖u(t)‖_{L³} ≥ 0`.

So the verdict is **LOG^K-CONVERGES-TO-LIMIT, NO-BKM-CLOSURE**.

We still ship the primitive because:

1. Future swarm iterations revisiting "can we sharpen `k`?" can
   short-circuit on the named conjecture below.
2. `iterLog k` parameterized by `k : ℕ` does not exist in Mathlib;
   it is a useful abstraction for slow-growth analysis beyond
   Navier-Stokes.

This file is **sorry-free**. The negative-result theorems are
expressed as `Prop`-level conjectures, not proved as theorems.

## Provenance

- T. Tao, *Quantitative bounds for critically bounded solutions to
  the Navier-Stokes equations*, Proc. Symp. Pure Math. **100** (2019),
  149-193; arXiv:1908.04958.
- T. Barker, C. Prange, *Quantitative regularity for the Navier-Stokes
  equations via spatial concentration*, Comm. Math. Phys. (2021);
  follow-ups through 2024-2025 retain triple-log in 3D.
- High-dimension d ≥ 4 → quadruple-log (J. Math. Fluid Mech., 2022).
-/

import Mathlib.Analysis.SpecialFunctions.Log.Basic

set_option linter.unusedSectionVars false

namespace NSTrackB

open Real

/-! ## §1.  Threshold tower `expTower k = exp^k 1` -/

/-- The exponential tower `exp^k 1`: `expTower 0 = 1`,
`expTower (k+1) = exp (expTower k)`. This is the threshold above
which the genuine `k`-fold iterated logarithm is non-negative. -/
noncomputable def expTower : ℕ → ℝ
  | 0     => 1
  | (k+1) => Real.exp (expTower k)

@[simp] lemma expTower_zero : expTower 0 = 1 := rfl

@[simp] lemma expTower_succ (k : ℕ) :
    expTower (k+1) = Real.exp (expTower k) := rfl

lemma expTower_pos : ∀ k, 0 < expTower k
  | 0     => by simp [expTower]
  | (k+1) => by
      simp only [expTower_succ]
      exact Real.exp_pos _

lemma one_le_expTower : ∀ k, 1 ≤ expTower k
  | 0     => by simp [expTower]
  | (k+1) => by
      simp only [expTower_succ]
      have h : 0 ≤ expTower k := le_of_lt (expTower_pos k)
      exact Real.one_le_exp h

/-! ## §2.  Threshold-clipped iterated log `iterLog' k` -/

/-- Iterate `Real.log` exactly `k` times on `x`. Helper for the
upper-branch definition of `iterLog'`. -/
noncomputable def logIter : ℕ → ℝ → ℝ
  | 0,     x => x
  | (k+1), x => Real.log (logIter k x)

@[simp] lemma logIter_zero (x : ℝ) : logIter 0 x = x := rfl

@[simp] lemma logIter_succ (k : ℕ) (x : ℝ) :
    logIter (k+1) x = Real.log (logIter k x) := rfl

/-- **Threshold-clipped iterated logarithm.** Returns the genuine
`k`-fold iterated log when `x > expTower k`, else `0`. By construction
this is total, non-negative, and a safe lower bound for the genuine
iterated log on its natural domain.

Special cases:
* `iterLog' 0 x = x` when `x > 1`, else `0`.
* `iterLog' 1 x` ≈ `Real.posLog x` (= `max (log x) 0`).
* `iterLog' 3 x` agrees with the `Real.triLog` of PR-1c on the
  upper branch (threshold `expTower 3 = exp (exp (exp 1))`). -/
noncomputable def iterLog' (k : ℕ) (x : ℝ) : ℝ :=
  if expTower k < x then logIter k x else 0

/-- On the lower branch, `iterLog' k` is identically zero. -/
lemma iterLog'_of_le {k : ℕ} {x : ℝ} (hx : x ≤ expTower k) :
    iterLog' k x = 0 := by
  unfold iterLog'
  exact if_neg (not_lt.mpr hx)

/-- On the upper branch, `iterLog' k` agrees with `logIter k`. -/
lemma iterLog'_of_lt {k : ℕ} {x : ℝ} (hx : expTower k < x) :
    iterLog' k x = logIter k x := by
  unfold iterLog'
  exact if_pos hx

/-- `iterLog'` is non-negative on the lower branch by definition. -/
lemma iterLog'_nonneg_lower {k : ℕ} {x : ℝ} (hx : x ≤ expTower k) :
    0 ≤ iterLog' k x := by
  rw [iterLog'_of_le hx]

/-! ## §3.  Tao 2019 typed-companion conjecture (k = 3) and chain -/

/-- **Tao 2019 (theorem in the literature; typed companion only).**
For Leray-Hopf weak solutions of 3D NS with hypothetical first
blow-up time `Tstar`, there exist `c > 0` and `t₀ < Tstar` such that
for every `t ∈ [t₀, Tstar)`,

    ‖u(t)‖_{L³} ≥ c · sqrt (iterLog' 3 (1 / (Tstar - t))).

We state the typed companion as a `Prop` keyed on the scalar inputs;
the PDE-level statement lives in
`ns_trackb_tao_2019_quantitative_carleman.lean`. -/
def TaoTripleLogLowerBound
    (c t Tstar L3norm : ℝ) : Prop :=
  c > 0 ∧ t < Tstar ∧
  L3norm ≥ c * Real.sqrt (iterLog' 3 (1 / (Tstar - t)))

/-- **CONJECTURE (open; structurally blocked in 3D).** The Tao 2019
triple-log lower bound generalizes to a `k`-fold iterated-log lower
bound for every `k ≥ 3`. -/
def TaoLogKLowerBoundConjecture (k : ℕ) : Prop :=
  k ≥ 3 →
  ∀ (c t Tstar L3norm : ℝ),
    c > 0 → t < Tstar →
    L3norm ≥ c * Real.sqrt (iterLog' k (1 / (Tstar - t)))

/-! ## §4.  Limiting bound — DOES NOT close BKM (formal statement) -/

/-- **The limiting-bound function**: pointwise `lim_{k→∞} iterLog' k x`.

For every fixed `x > 0`, the threshold tower `expTower k` eventually
exceeds `x` (since `expTower (k+1) = exp (expTower k) ≥ exp 1 · expTower k`
diverges), at which point `iterLog' k x = 0`. So the pointwise limit
is identically `0`.

This is the formal statement that the `log^k` chain DOES NOT close
BKM: as `k → ∞`, the lower bound on `‖u(t)‖_{L³}` degrades to the
trivial bound `‖u(t)‖_{L³} ≥ 0`. -/
def limitLogBound : ℝ → ℝ := fun _ => 0

/-- **Conjectural statement (not proved here).** For every `x > 0`,
`iterLog' k x` is eventually `0` as `k → ∞`. The proof requires
`expTower k → ∞`, which we do not inline. We ship the named statement
as a `Prop` for the swarm to discharge separately. -/
def iterLog'_eventually_zero (x : ℝ) : Prop :=
  ∀ᶠ k in Filter.atTop, iterLog' k x = 0

/-- **Verdict tag** (machine-readable, for the closure miner). -/
def verdict_log_k_chain : String :=
  "LOG_K_CONVERGES_TO_LIMIT — NO_BKM_CLOSURE"

/-! ## §5.  Sanity smoke-test: `iterLog' 0 = id` on the upper branch. -/

lemma iterLog'_zero_upper {x : ℝ} (hx : 1 < x) : iterLog' 0 x = x := by
  unfold iterLog' logIter
  simp [expTower, hx]

lemma iterLog'_zero_lower {x : ℝ} (hx : x ≤ 1) : iterLog' 0 x = 0 := by
  apply iterLog'_of_le
  simpa [expTower] using hx

end NSTrackB
