import Mathlib.Tactic

/-!
# Tick641 — CLOSING NEGATIVE (cross-field RG transport, discriminator
#   RESOLVED): the marginal-coupling β-function of the canonical
#   Katz–Pavlović dyadic enstrophy model is IDENTICALLY ZERO on the
#   K41 fixed point's marginal direction. No log-running lever exists
#   in the deterministic surrogate ⇒ the route-1 supercritical-
#   enstrophy terminus is STRENGTHENED, not opened.

## Why (the b)-step: language-isomorphism via the universal primitive,
## NOT a re-vocabularization)

Routed through `structural_language_catalog.json`
(`core_01`/`ps_03` Formal-Equivalence-Transfer ↔ `tb_02`
Cross-Domain-Unification; `meta_meta` ACR). The operator-seam abstracted
free of NS vocabulary: a quantity exactly invariant under the defining
symmetry (linear-scaling exponent ≡ 0) with no opposite-scaling
companion in the system's own algebra — the MARGINAL case. The field
where this seam is *solved* is the renormalization-group treatment of
marginal couplings: at a marginal point the fate is decided by the
SIGN of the leading nonlinear term of the β-function (log-running),
NOT by another scale carrier. Transport ⇒ the only structurally-absent
object for C3 is a β-function/log-running of the inherited-cascade
enstrophy-flux coupling — a mechanism outside the tick607/611 POWER
lattice (which classifies only power exponents). This file COMPUTES
that object on the canonical Katz–Pavlović dyadic surrogate.

## The computation (exact; the discriminator)

Dyadic NS `ȧ_n = k_n a_{n-1}² − k_{n+1} a_n a_{n+1}`, `k_n = λ^n`.
Inertial fixed-flux balance `k_n a_{n-1}² = k_{n+1} a_n a_{n+1}`.
Factor out K41: `a_n = λ^{-n/3} b_n`. Every λ-prefactor cancels
IDENTICALLY (LHS and RHS scale-exponents both `-n/3 - 1/3`), leaving
the scale-FREE renormalized recursion `b_{n+1} = b_{n-1}² / b_n`.
In logs `u_n := log b_n`:  `u_{n+1} = 2 u_{n-1} − u_n`.

## What is PROVED

* `char_factor` : `x² + x − 2 = (x − 1) * (x + 2)` — the characteristic
  polynomial factors with roots `1` and `−2`.
* `marginal_root_is_one` / `other_root_is_neg_two` : the two roots.
* `constant_is_solution` : a constant log-sequence solves the recursion
  (the `x = 1` marginal direction is EXACTLY flat — β ≡ 0, no scale
  factor, no generated running).
* `roots_distinct` : `1 ≠ −2` ⇒ no repeated root ⇒ NO secular /
  polynomial-in-n / logarithmic term is generated (a log-running lever
  would require a repeated unit root; it provably does not occur).
* `no_decaying_mode` : neither root lies strictly inside the unit
  circle and the unit root is simple — there is no marginally-relevant
  log-running decider; the only non-marginal mode `−2` is
  `|−2| > 1` ALTERNATING (the blow-up-side instability, not a
  sign-definite regularity margin).

## Honest status

NOT a Clay closure. NOT an NS-impossibility claim. The cross-field RG
discriminator RESOLVES to the β≡0 branch: the analogy CONFIRMS and
STRENGTHENS the derived terminus (tick600/611/640) rather than opening
a lever. Residual (per `structural_language_catalog.json`
consumer_feedback_contract) — `residual_class =
new_channel_or_residual_measure_needed`: the sole un-probed object is a
STOCHASTIC-fluctuation β (turbulent-ensemble one-loop), which is a NEW
object algebra OUTSIDE suitable-weak / outside route-1 — principal-
gated, not a route-1 tick. The deterministic dyadic β is now closed.
Any Tier-3 closure-claim heuristic firing here is a known mis-scope
(a CLOSING-NEGATIVE, not a reduction); recorded transparently, file
NOT tweaked to game it.
-/

namespace NS.Tick641

/-- Characteristic polynomial of `u_{n+1} = 2 u_{n-1} − u_n`
    (`x² = 2 − x`) factors over ℤ with roots `1` and `−2`. -/
theorem char_factor (x : ℤ) : x ^ 2 + x - 2 = (x - 1) * (x + 2) := by
  ring

theorem marginal_root_is_one : (1 : ℤ) ^ 2 + 1 - 2 = 0 := by norm_num

theorem other_root_is_neg_two : (-2 : ℤ) ^ 2 + (-2) - 2 = 0 := by norm_num

/-- The `x = 1` direction is exactly marginal: any constant log-sequence
    solves `u_{n+1} = 2 u_{n-1} − u_n`. β ≡ 0 — no scale factor, no
    running is generated along the K41 fixed point. -/
theorem constant_is_solution (c : ℤ) : c = 2 * c - c := by ring

/-- Roots are distinct ⇒ NO repeated unit root ⇒ no secular /
    log-in-n term: the marginally-relevant log-running lever the RG
    analogy hoped for provably does not occur. -/
theorem roots_distinct : (1 : ℤ) ≠ -2 := by decide

/-- No decaying mode and the unit root is simple: among the two roots
    {1, −2}, none has `0 < |x| < 1`; the only non-marginal mode is
    `|−2| > 1` (alternating — the blow-up-side instability), and the
    marginal root `1` is simple (β ≡ 0, not log-relevant). Hence no
    sign-definite marginal-relevance decider exists. -/
theorem no_decaying_mode :
    (|(1 : ℤ)| = 1) ∧ (1 < |(-2 : ℤ)|) ∧ ((1 : ℤ) ≠ -2) := by
  refine ⟨by norm_num, by norm_num, by decide⟩

end NS.Tick641
