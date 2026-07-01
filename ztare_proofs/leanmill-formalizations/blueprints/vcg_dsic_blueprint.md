# Dominant-strategy truthfulness of the general VCG mechanism (quasi-linear, arbitrary finite outcome space, Clarke pivot)

The formal core of mechanism design: the Vickrey–Clarke–Groves mechanism makes truthful reporting a
**dominant** strategy — optimal no matter what every other agent reports, not merely a Nash equilibrium. This
blueprint targets the GENERAL theorem, not the elementary single-item second-price corollary: an arbitrary
finite outcome/allocation space, an arbitrary finite set of agents with quasi-linear valuations over a linearly
ordered field, the welfare-maximizing allocation possibly non-unique, and the Clarke pivot payment in full.

The distinctive output is the assumption accounting. DSIC holds for a precise reason — the allocation maximizes
reported social welfare AND each agent is charged exactly the externality it imposes on the others. Drop either
and truthfulness fails. A machine-checked proof pins that dependency: you cannot remove a hypothesis the kernel
used. None of this vocabulary is in Mathlib — theory-building. Probe Mathlib with Loogle and the warm checker;
decompose however the kernel teaches. A non-closure is an honest gap, never a fake closure, and never a silent
restriction (no single-unit retreat, no fixed-opponent weakening).

## Domain
formalization-nonmath

## Theory file
vcg_dominant_strategy_truthfulness.lean

The bespoke vocabulary Mathlib lacks — establish each once, over whatever structure the result actually
requires (do not pre-narrow it), and never "prove" a definition:

- **Valuation profile** — a finite set of agents, each with a valuation `v i : Outcome → K` over a finite,
  nonempty outcome space `Outcome`, valued in a linearly ordered field `K` (quasi-linear: value and money add).
  A report profile has the same type as the true profile; the two need not agree.
- **Social welfare** — the reported welfare at an outcome, `W r a = ∑ i, r i a`.
- **VCG allocation** — a welfare-maximizing outcome `aStar r ∈ argmax_a (∑ i, r i a)` for the reported profile.
  It exists because `Outcome` is a nonempty `Fintype`, and it may be non-unique: pin a deterministic selection
  but state and carry its **maximality property**, not the particular witness.
- **Clarke pivot payment** — `p i r = (⨆ a, ∑ j ≠ i, r j a) − (∑ j ≠ i, r j (aStar r))`: the externality agent
  `i` imposes on the others — the others' best attainable welfare without regard to `i`, minus the others'
  welfare at the chosen outcome. Nonnegative. Its first term is **independent of `i`'s own report**; that is the
  crux, not a convenience.
- **Quasi-linear utility** — when agent `i`'s TRUE valuation is `v i` and the mechanism is run on report profile
  `r`, its realized utility is `u = v i (aStar r) − p i r` (true value of the chosen outcome, minus payment).
- **DSIC (dominant-strategy incentive compatibility)** — for every agent `i`, every true valuation `v i`, every
  profile `r₋ᵢ` of the others' reports, and every misreport `rᵢ'`, truthful reporting weakly dominates.

## Target
Over an arbitrary finite nonempty outcome space, an arbitrary finite agent set, and quasi-linear valuations in a
linearly ordered field, DEFINE the VCG mechanism (welfare-maximizing allocation + Clarke pivot payment) and
prove all three:

1. **Dominant-strategy truthfulness (DSIC).** For every agent `i`, every true valuation `v i`, every profile of
   the others' reports `r₋ᵢ`, and every misreport `rᵢ'`, truthful reporting yields utility at least that of
   misreporting:
   `u(true = v i; report (v i, r₋ᵢ)) ≥ u(true = v i; report (rᵢ', r₋ᵢ))`.
   This is the DOMINANT-strategy claim — quantified over ALL profiles of the others — not a Nash / fixed-opponent
   version.

2. **Pivot i-independence (the load-bearing lemma).** The term `⨆ a, ∑ j ≠ i, r j a` does not depend on `i`'s
   own report. This is what turns "maximize my utility over my report" into "make the mechanism select the
   outcome that maximizes my TRUE welfare-inclusive objective," and it must be a proven rung, not assumed.

3. **A non-degenerate multi-unit witness.** Instantiate with ≥2 agents and ≥2 identical units allocated among
   them, valuations drawn from decreasing marginal values (step functions), and exhibit a concrete
   `(true vᵢ, r₋ᵢ, misreport rᵢ')` where the misreport CHANGES the winning allocation `aStar` and yet still does
   not improve `i`'s utility. This forbids the vacuous reading (no misreport ever changes the outcome) and the
   single-unit second-price retreat.

**TYPECLASS ON `K` — MANDATORY, DO NOT WEAKEN.** State `K` as `[LinearOrderedField K]` (the intent), or at
minimum an order-compatible `[LinearOrderedAddCommGroup K]`. Do NOT split it into a bare
`[AddCommGroup K] [LinearOrder K]`. DSIC is **false** without order-compatible addition (`a ≤ b → a + c ≤ b + c`):
the Clarke-payment cancellation and the welfare-maximality step both move an inequality across a `+`, which needs
that instance. A bare `AddCommGroup + LinearOrder` admits a counterexample (an order that ignores addition), so
the theorem is **false as stated** — and its counterexample is hard to construct, so the solver will burn its
budget unable to either prove OR refute it (exactly the failure mode to avoid). The generality you want lives in
`Agent`/`Outcome`/valuations, NOT in dropping the order-field structure of the value type.

Guards. Do not assume the others report truthfully (dominant strategy, not equilibrium). Do not let a
constant or degenerate valuation make the argmax trivial or the payment identically zero — a zero-payment
allocation rule is NOT DSIC, and the proof must genuinely use the externality term. Surface, in the assumption
ledger, that welfare-maximization AND the Clarke payment are BOTH used: the theorem is exactly the statement
that these two together buy truthfulness.

## Idea
(Advisory planner context — a tractability steer, NOT a formalization mandate.) The engine of the whole proof is
one rearrangement. Write `i`'s utility from reporting `rᵢ` (true value `v i`, others `r₋ᵢ`) with
`aStar = aStar (rᵢ, r₋ᵢ)`:

  `u = v i (aStar) − p i = v i (aStar) + (∑ j ≠ i, r₋ᵢ j (aStar)) − (⨆ a, ∑ j ≠ i, r₋ᵢ j a)`.

The last term is constant in `rᵢ`. So maximizing `u` over `rᵢ` is the same as maximizing
`v i (aStar) + ∑ j ≠ i, r₋ᵢ j (aStar)`. But the mechanism chooses `aStar` to maximize
`rᵢ (aStar) + ∑ j ≠ i, r₋ᵢ j (aStar)`. Reporting `rᵢ = v i` aligns the mechanism's objective with `i`'s TRUE
objective, so the chosen `aStar` maximizes exactly `v i a + ∑ j ≠ i, r₋ᵢ j a` over ALL `a` — in particular over
the outcome any misreport could induce. That single welfare-maximality inequality IS the theorem; the rest is
the Clarke term's cancellation.

Modelling. `Outcome` a nonempty `Fintype`; `K` a `LinearOrderedField` (`ℚ` keeps it decidable if a decide/omega
lever helps; `ℝ` is fine for the argmax). The welfare-max allocation exists via `Finset.exists_max_image` over
`Finset.univ`; carry the maximality property, not the chosen witness. Agents a `Fintype`; `∑ j ≠ i` is
`∑ j in Finset.univ.erase i`. There is no banked single-item case to cite — build the general mechanism from
Mathlib's finite-sum and finite-argmax primitives. Keep valuations as functions `Outcome → K` (not tables) so
the multi-unit instance is a specialization, not a re-definition.
