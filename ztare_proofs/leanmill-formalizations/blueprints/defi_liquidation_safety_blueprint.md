# DeFi liquidation safety — solvency is preserved along every admissible trajectory

Extends the library's DeFi-security lane (the banked AMM path-independence result) from a single swap invariant to a
**collateralized-lending state machine**: a position with collateral and debt, evolved by the operations a lending
protocol actually exposes — deposit, borrow, repay, withdraw — each behind the protocol's own solvency guard, plus an
exogenous, adversarial price move, plus liquidation. The security claim is dynamic and contested in exactly the way a
smart-contract audit cannot settle by inspection: **no admissible sequence of user operations can drive a guarded
position into insolvency**, and when an exogenous price shock does, **liquidation moves the position back toward
health and never strands the protocol with unrecoverable debt**. This is an economic-security property over reachable
states and adversarial histories — the paper's "mechanisms markets run on" — not a static inequality, and it is a
theorem EconCSLib does not hold.

Assumption-accounting note: the results depend on (1) **nonnegativity** — collateral, debt, and every operation
amount are nonnegative; (2) the **collateral factor** `θ` (the maximum debt as a fraction of collateral value, the
loan-to-value / liquidation threshold) satisfying `0 < θ ≤ 1`; (3) each user operation being applied only when its
**solvency guard** holds (a borrow/withdraw the protocol would revert is not in the admissible trajectory) — this is
the load-bearing hypothesis, and dropping it is exactly how insolvency enters; (4) for liquidation safety, the
**bonus** `β ≥ 0` satisfying the standard safe-bonus condition `θ·(1+β) ≤ 1` (the liquidation incentive does not
exceed the inverse collateral factor). Surface where each is used. Keep the model over an ordered field of
real-valued quantities; do **not** collapse it to a fixed decidable integer instance, and do **not** narrow the price
move or the operation sequence to a single hard-coded step (the reachable-state quantification is the whole point). A
non-closure is an honest gap, never a fake closure. Probe Mathlib / the banked AMM shelf for the `List.foldl`
invariant pattern (`executeTrades`-style) rather than re-deriving it.

## Domain
formalization-nonmath

## Theory file
defi_liquidation_theory.lean

## Vocabulary (build these as definitions — do not prove them)
- **Position**: a collateral value and a debt value, both nonnegative, carried against a collateral factor `θ` with
  `0 < θ ≤ 1`.
- **Healthy / safe**: a position is healthy when its debt is within its collateral factor — `debt ≤ θ · collateral`
  (equivalently the health factor `θ · collateral / debt ≥ 1`). Below this the position is liquidatable.
- **Operations** as state transitions on a position: `deposit` adds collateral; `repay` reduces debt; `borrow` adds
  debt; `withdraw` removes collateral; each of `borrow`/`withdraw` carries the protocol **guard** that the resulting
  position is still healthy (`deposit`/`repay` need no guard). An exogenous **price move** rescales the collateral
  value by a positive factor.
- **Admissible sequence**: a finite list of operations in which every step's guard holds at the state it is applied
  to (the trajectory the protocol actually permits).
- **Liquidation**: on a liquidatable position, repay an amount of debt and seize collateral worth that amount scaled
  by the bonus factor `(1 + β)`.

## Target
Consider a collateralized-debt position — a nonnegative collateral value and a nonnegative debt value against a
collateral factor `θ` between 0 and 1 — evolved by a protocol that exposes deposit, borrow, repay, and withdraw, and
that permits a borrow or a withdraw only when the resulting position remains healthy (debt within the collateral
factor). The claim is a reachable-state solvency guarantee: starting from any healthy position, after **any** finite
admissible sequence of these operations — a flash-loan-style burst, a repay-then-reborrow, a withdraw interleaved with
deposits, in any order — the position is healthy at every state it passes through. No trajectory of guarded user
actions can reach an insolvent state; only an exogenous price move can, and it lies outside the guarded operations.
Surface that the guarantee uses nonnegativity, the collateral-factor range, and the per-step guard, and that the guard
is load-bearing: dropping it admits a borrow that reaches an unhealthy state.

## Lemmas
- Depositing collateral preserves health: a healthy position that receives additional collateral (debt unchanged)
  stays healthy.
- Repaying debt preserves health: a healthy position that reduces its debt (collateral unchanged) stays healthy.
- A guarded withdraw yields a healthy position: if the debt is still within the collateral factor of the reduced
  collateral, the post-withdraw position is healthy.
- Liquidation is loss-free on the liquidated tranche: repaying an amount and seizing collateral worth that amount
  scaled by `(1 + β)` with `β ≥ 0` seizes collateral value at least equal to the debt repaid.
- Liquidation moves toward health: under the safe-bonus condition `θ · (1 + β) ≤ 1`, a partial liquidation does not
  increase the under-collateralization gap `debt − θ · collateral` (it weakly decreases it).
- The health boundary is sharp: a position with `debt = θ · collateral` is healthy (inclusive), while `debt >
  θ · collateral` is liquidatable; a price move by a factor below 1 pushes a boundary position into the liquidatable
  region.

## Idea
The health predicate is the linear inequality `debt ≤ θ · collateral`; keep it that way (no division, so no
positivity-of-debt side condition and the boundary stays exact). Each per-operation lemma is one `linarith`/`nlinarith`
step: deposit and repay weaken the right/left side; the borrow and withdraw guards are *definitionally* the post-state
health predicate, so those lemmas are near-immediate. The reachable-state target is a `List.foldl` invariant over the
admissible sequence — induct on the operation list, discharge each step with the matching per-op lemma; this is the
same shape as the banked AMM `executeTrades_keep_wellFormed` invariant, so cite/mirror it rather than re-deriving.
Liquidation loss-free is `(1+β) ≥ 1`; liquidation-toward-health is the gap computation `gap' = gap − r·(1 − θ(1+β))`
with `1 − θ(1+β) ≥ 0` from the safe-bonus condition — one `nlinarith`. Keep `θ` and `β` as parameters (the theorems
are general in them); the guard is the whole argument — state and use it, do not silently assume all operations are
health-preserving, and do not fix a single price factor or a length-one operation list.
