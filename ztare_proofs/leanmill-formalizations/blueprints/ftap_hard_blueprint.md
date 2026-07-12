# Finite FTAP — HARD direction (no arbitrage ⇒ a strictly positive state-price vector exists)

The companion to the easy direction we proved — the real-content half. Finance's cornerstone: in a finite
one-period market, ABSENCE of arbitrage FORCES the existence of a strictly positive state-price (risk-neutral)
vector that prices every asset (Harrison–Pliska). Where the easy direction was an elementary sum rearrangement,
this is a separating-hyperplane / Farkas–Stiemke argument — no-arbitrage says the cone of attainable
(−cost, payoff) vectors meets the nonnegative orthant only at the origin, and separation produces the strictly
positive pricing functional.

Assumption-accounting note: the conclusion must deliver STRICT positivity of every state price (q s > 0), which
is exactly what NO-arbitrage (not merely no-sure-loss) buys; finiteness of states and assets is what makes the
attainable cone closed and the separating functional finite. Surface where finiteness and the (strict)
no-arbitrage hypothesis are each used. A non-closure is an honest gap, never a fake closure.

## Domain
formalization-nonmath

## Theory file
ftap_hard_theory.lean

No bespoke definition is required — the market data are plain functions over `Fin`/`Finset` and ℝ (payoffs D,
prices p, holdings θ, state prices q), and the separation machinery is Mathlib's. (If the apparatus finds it
needs a finite Farkas/Stiemke separation lemma that Mathlib lacks, it should build and govern that as part of its
own decomposition — probe with Loogle and the warm checker first.)

## Target
Consider a one-period market with finitely many states and finitely many assets, asset payoffs D(i, s) in state s
and prices p(i), all real. Suppose the market admits no arbitrage: there is no portfolio θ(i) whose cost
Σ_i θ(i)·p(i) is ≤ 0, whose payoff Σ_i θ(i)·D(i, s) is ≥ 0 in every state s, and is > 0 in at least one state.
Then there exists a state-price vector q with q(s) > 0 for every state s such that every asset is priced by it:
p(i) = Σ_s q(s)·D(i, s) for all assets i.

## Idea
Form the linear map sending a portfolio θ to its (−cost, state-payoff) vector. No-arbitrage says the image cone
meets the closed nonnegative orthant only at the origin; a finite separating-hyperplane / Farkas argument
(Stiemke is the sharp, strict form) yields a STRICTLY positive functional vanishing on the image. Its
state-coordinates, normalized by the cost-coordinate, are q(s) > 0, and "vanishing on the image" is exactly the
pricing identity p = Dᵀq. Strict positivity is forced coordinate-by-coordinate by the no-arbitrage hypothesis (a
zero coordinate would permit an arbitrage concentrated in that state). This is genuinely harder than the easy
direction (convex analysis, not summation) — an honest gap on the separation step is a legitimate, informative
outcome. Keep any built definition faithful (the market data are the literal payoff/price arrays, never a shell
that trivializes existence).
