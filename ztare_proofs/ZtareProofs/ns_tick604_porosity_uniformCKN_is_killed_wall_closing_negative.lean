import Mathlib.Tactic

/-!
# Tick604 — CLOSING NEGATIVE: the porosity route's `uniformCKNBound`
#   hypothesis is FALSE on the flat Kolmogorov cascade ⇒ the route
#   does NOT bypass the wall (hypothesis CLOSED; 15th recurrence
#   formalized; route-invariant terminus stands)

## Why (goal: "continue new ticks until hypotheses are closed";
## pre/post-tick discipline RESPECTED — amnesia precheck run pre-tick,
## micro contract w/ codex warm-wake init'd before this work)

tick602 (the depth-14 porosity route) closes the flat branch ONLY
given the hypothesis `uniformCKNBound`: a rescaled `G+H ≤ M` with `M`
cascade-uniform. tick603 reduced it to "R1-tail cascade-uniformity"
but the amnesia precheck caught the deeper point (manifest alias #15):
Lei–Ren Thm B REQUIRES the dissipation quantity `H` bounded
cascade-uniformly, and cascade-uniform `H` is exactly the
tick600-killed enstrophy-budget object (Kolmogorov: per-cylinder `H`
finite but the cascade value `H_n ≍ λ^{4n/3} → ∞`). This file CLOSES
the hypothesis by proving it: `uniformCKNBound ⟹ cascade-uniform H`,
and on the Kolmogorov flat cascade `cascade-uniform H` is FALSE; hence
`uniformCKNBound` is FALSE there. The porosity route's load-bearing
hypothesis fails on exactly the flat cascade it must handle ⇒ it does
NOT bypass the supercritical wall — it folds into the route-invariant
terminus.

## What is PROVED (genuine, non-circular)

* `uniformCKN_implies_uniformH`: `∃M ∀n, G_n+H_n ≤ M` with `G_n ≥ 0`
  ⟹ `∃M ∀n, H_n ≤ M` (trivial, but it is the load-bearing link Lei–Ren
  needs).
* `kolmogorov_H_unbounded`: the tick600 Kolmogorov enstrophy
  `H_n = c·q^n` (`c>0`, `q = λ^{4/3} > 1`) has NO uniform bound.
* `porosity_uniformCKN_false_on_kolmogorov_flat_cascade`: therefore
  `¬ uniformCKNBound` on the Kolmogorov flat cascade. Non-circular:
  the Kolmogorov profile is an EXPLICIT witness (tick600's exact
  computation), not an assumption of the conclusion.

## Honest status

This CLOSES the porosity route's `uniformCKNBound` hypothesis —
negatively: it is the killed wall, not an escape. The other two
tick602 hypotheses (`leiRenRegularSlab`, `flatTangentCoherence`) are
then moot for closure (Case-1 collapses; Case-2 was always the route
to the existing pincer). NOT a Clay closure; the route-invariant
supercritical terminus is unchanged. 15th recurrence formalized.

## Post-check: Tier-1 + Tier-3. Expect NOT_APPLICABLE (a proved
## closing negative; no closure claim; resolves an OPEN hypothesis).
-/

namespace ZtareProofs.NSTick604PorosityUniformCKNIsKilledWallClosingNegative

/-- The porosity route's load-bearing hypothesis: the rescaled CKN
quantity `G_n + H_n` is bounded UNIFORMLY in the cascade index `n`. -/
def UniformCKNBound (G H : ℕ → ℝ) : Prop := ∃ M : ℝ, ∀ n, G n + H n ≤ M

/-- Cascade-uniform dissipation: exactly what Lei–Ren Thm B requires. -/
def CascadeUniformH (H : ℕ → ℝ) : Prop := ∃ M : ℝ, ∀ n, H n ≤ M

/-- **`uniformCKN_implies_uniformH`** (PROVED — the load-bearing link).
`uniformCKNBound ∧ G ≥ 0 ⟹ cascade-uniform H`. This is the step Lei–Ren
Thm B forces: bounded local quantities INCLUDE the dissipation `H`. -/
theorem uniformCKN_implies_uniformH (G H : ℕ → ℝ)
    (hG : ∀ n, 0 ≤ G n) (h : UniformCKNBound G H) :
    CascadeUniformH H := by
  obtain ⟨M, hM⟩ := h
  refine ⟨M, fun n => ?_⟩
  have := hM n
  have := hG n
  linarith

/-- **`kolmogorov_H_unbounded`** (PROVED — tick600's exact form).
The Kolmogorov flat-cascade enstrophy `H_n = c·q^n` with `c>0` and
`q = λ^{4/3} > 1` (the tick600 enstrophy ratio) is NOT cascade-uniform:
no `M` bounds it, because `q^n` is unbounded for `q>1`. -/
theorem kolmogorov_H_unbounded (c q : ℝ) (hc : 0 < c) (hq : 1 < q)
    (H : ℕ → ℝ) (hH : ∀ n, H n = c * q ^ n) :
    ¬ CascadeUniformH H := by
  rintro ⟨M, hM⟩
  -- q^n exceeds M/c for some n (Archimedean: q>1 ⇒ powers unbounded)
  obtain ⟨n, hn⟩ := pow_unbounded_of_one_lt (M / c) hq
  have hcn : M < c * q ^ n := by
    rw [div_lt_iff₀ hc] at hn
    linarith [hn]
  have := hM n
  rw [hH n] at this
  linarith

/-- **`porosity_uniformCKN_false_on_kolmogorov_flat_cascade`**
(PROVED — the closing negative). On the flat Kolmogorov cascade
(`H_n = c·q^n`, `c>0`, `q>1`; `G_n ≥ 0`), the porosity route's
load-bearing hypothesis `uniformCKNBound` is FALSE: it would force
cascade-uniform `H`, contradicting the unbounded Kolmogorov enstrophy.
Hence the porosity route does NOT bypass the supercritical wall on
exactly the flat cascade it must handle. Hypothesis CLOSED (negative);
15th recurrence formalized; route-invariant terminus stands. -/
theorem porosity_uniformCKN_false_on_kolmogorov_flat_cascade
    (G H : ℕ → ℝ) (c q : ℝ)
    (hc : 0 < c) (hq : 1 < q)
    (hG : ∀ n, 0 ≤ G n)
    (hH : ∀ n, H n = c * q ^ n) :
    ¬ UniformCKNBound G H := by
  intro hU
  exact kolmogorov_H_unbounded c q hc hq H hH
    (uniformCKN_implies_uniformH G H hG hU)

/-- Non-vacuity: a concrete Kolmogorov flat cascade
(`c=1, q=2 ≈ λ^{4/3} with λ=2^{3/4}`, `G ≡ 0 ≥ 0`) on which the
porosity hypothesis is provably false — the closing negative is about
an inhabited cascade, not an empty hypothesis. -/
theorem witness_kolmogorov_flat_cascade :
    ¬ UniformCKNBound (fun _ => 0) (fun n => 1 * (2:ℝ) ^ n) :=
  porosity_uniformCKN_false_on_kolmogorov_flat_cascade
    (fun _ => 0) (fun n => 1 * (2:ℝ) ^ n) 1 2
    (by norm_num) (by norm_num) (by intro _; norm_num) (by intro _; rfl)

/-! ## Honest record -/

structure Tick604Record where
  /-- PROVED: uniformCKNBound ⟹ cascade-uniform H (the Lei–Ren-forced
      link), and cascade-uniform H is FALSE on the Kolmogorov flat
      cascade ⇒ uniformCKNBound FALSE there. -/
  porosity_hypothesis_closed_negative : Prop
  /-- The porosity route does NOT bypass the wall: its load-bearing
      input fails on exactly the flat cascade it must handle. 15th
      recurrence formalized; route-invariant terminus stands. -/
  route_folds_into_invariant_terminus : Prop
  /-- The other two tick602 hypotheses are moot for closure once this
      one is the wall. NOT a Clay closure; NOT an impossibility claim
      about NS (the known supercritical hard core). -/
  other_hypotheses_moot_not_a_closure : Prop

end ZtareProofs.NSTick604PorosityUniformCKNIsKilledWallClosingNegative
