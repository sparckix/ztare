# Median Voter Theorem (Black 1948) — a Condorcet winner under single-peaked preferences

Opens a new domain for the library: **social choice / political economy**. Black's median voter theorem is the
foundational result of positive political theory — with an odd electorate and single-peaked preferences over a
linearly ordered policy space, the median voter's ideal point beats every alternative in pairwise majority vote
(it is a Condorcet winner). It is the reason "the candidate moves to the center" is a theorem and not a slogan.

The result is a clean showcase of the library's thesis — the *assumptions are the whole argument*: drop
single-peakedness and a Condorcet winner may fail to exist (Condorcet's paradox); make the electorate even and
ties break the majority. Both hypotheses are load-bearing and the assumption accounting should surface exactly
that.

Assumption-accounting note: the conclusion depends on (1) **single-peaked** preferences — each voter's ranking
strictly decreases as alternatives move away from that voter's peak in the order; (2) an **odd** number of voters,
so a strict majority `> n/2` exists on each side of the median; (3) a **linear order** on the finite alternative
set, which is what "single-peaked" and "median" are defined against. Surface where each is used. A non-closure is
an honest gap, never a fake closure. Probe Mathlib (Loogle + the warm checker) for `Finset` cardinality and
`LinearOrder`/`Finset.median`-style API; build only the small social-choice scaffold the statement genuinely needs.

## Domain
formalization-nonmath

## Theory file
median_voter_theory.lean

## Target
Consider a finite set of alternatives carrying a linear order (a one-dimensional policy space) and an odd number
of voters. Each voter has a **peak** alternative and **single-peaked** preferences with respect to the order:
moving strictly away from the peak — in either direction along the order — strictly worsens the alternative for
that voter (equivalently, of any two alternatives on the same side of the peak, the one nearer the peak is
strictly preferred, so the peak is most-preferred). Say a voter **prefers** `x` to `y`
when `x` is ranked strictly above `y`, and that alternative `x` **beats** `y` by majority when strictly more than
half the voters prefer `x` to `y`. Let `m` be a **median** of the voters' peaks — an alternative such that at
least half the peaks are `≤ m` and at least half are `≥ m`. Then `m` is a **Condorcet winner**: for every
alternative `y ≠ m`, `m` beats `y` by majority.

## Idea
The argument is a counting argument on the two sides of the median, using single-peakedness once per side. Take
any `y > m` (the case `y < m` is symmetric under the order-reversal). Every voter whose peak is `≤ m` prefers `m`
to `y`: their peak lies on the `m` side of `y`, so by single-peakedness `m` — being strictly nearer the peak than
`y` — is strictly preferred. Because `m` is a median and the electorate is odd, strictly more than half the voters
have peak `≤ m`, so a strict majority prefers `m` to `y`; hence `y` does not beat `m`, and `m` beats `y`. The two
directions together give: for all `y ≠ m`, `m` beats `y`. Keep the built definitions faithful — single-peakedness
must be the genuine "strictly worse as you move away from the peak" condition (not a shell that trivializes the
count), the peak genuinely most-preferred, and "median" the real order-statistic on the multiset of peaks. The
oddness enters exactly at "strictly more than half"; state and use it, do not assume a tie-break. Decompose as the
kernel teaches (the two-sided symmetry and the per-side single-peaked step are natural rungs); a gap on the median
counting step is a legitimate, informative outcome.

<!-- proven-rungs:auto -->
## Proven rungs (kernel-closed, auto — citable)
- ✅ iso_lemma3 [sha:22b85cfe95c3ac9b] theorem iso_lemma3 : ∀ [LinearOrder A] (peaks : V → A) (m : A) (hmem : m ∈ (Finset.univ.image peaks).filter fun a => Fintype.card V ≤ 2 * (Finset.univ.filter fun i => peaks i ≤ a).card) (hmin : ∀ a ∈ (Finset.univ.image peaks).filter fun a => Fintype.card V ≤ 2 * (Finset.univ.filter fun i => peaks i  (ztare_proofs/.solver_scratch/closures/iso_lemma3.lean)
- ✅ iso_lemma1 [sha:46360d50a9111ada] theorem iso_lemma1 : ∀ [LinearOrder A] [Nonempty V] (peaks : V → A), ((Finset.univ.image peaks).filter fun a => Fintype.card V ≤ 2 * (Finset.univ.filter fun i => peaks i ≤ a).card).Nonempty (ztare_proofs/.solver_scratch/closures/iso_lemma1.lean)
- ✅ iso_lemma2 [sha:55e9c8ea4130e468] theorem iso_lemma2 : ∀ [LinearOrder A] (peaks : V → A) (m : A), (Finset.univ.filter fun i => peaks i < m).card + (Finset.univ.filter fun i => m ≤ peaks i).card = Fintype.card V (ztare_proofs/.solver_scratch/closures/iso_lemma2.lean)
- ✅ isMedian_peak_middle_voter [sha:7ebaf4ec18029b80] theorem isMedian_peak_middle_voter : ∀ [LinearOrder A] [Nonempty V] (hodd : Odd (Fintype.card V)) (peaks : V → A), ∃ i : V, IsMedian peaks (peaks i) (ztare_proofs/.solver_scratch/closures/isMedian_peak_middle_voter.lean)
- ✅ median_voter_theorem [sha:d738d8b253118478] theorem median_voter_theorem : ∀ {peaks : V → A} {u : V → A → B} {m : A} (hodd : Odd (Fintype.card V)) (hsp : ∀ i : V, SinglePeaked (peaks i) (u i)) (hmed : IsMedian peaks m), ∀ y : A, y ≠ m → Beats u m y (ztare_proofs/.solver_scratch/closures/median_voter_theorem.lean)
<!-- /proven-rungs:auto -->
