# Warrant-filtration profile — warrant promotion is monotone (acyclic case)

A formalization companion to the warrant-filtration gradual argumentation semantics (paper:
`papers/warrant-filtration/draft.md`). The headline property — which no prior gradual argumentation semantics
could even state, because none emits a stratified strength PROFILE — is that promoting a support edge to a more
checkable warrant never lexicographically lowers the thesis profile, and promoting an attack edge never raises
it. This target proves that property for the ACYCLIC-support case: a finite DAG, where each node's strength is a
well-founded recursion with no fixed-point limit, which is exactly the case the paper's sketch covers. The
cyclic case (a continuous QEM fixed point) is deliberately out of scope and left as future work.

## Domain
formalization-nonmath

## Theory file
warrant_filtration.lean

This is a NEW theory — no prior banked vocabulary to reuse; define it. The objects, in plain terms:

- A finite bipolar argument graph: finitely many nodes, each either an EVIDENCE node or a CLAIM node, with one
  distinguished claim called the THESIS. Each directed edge is either a SUPPORT edge or an ATTACK edge and
  carries a WARRANT rank in `{0,1,2,3}` (encode as `Fin 4` or `ℕ`), where a HIGHER rank means MORE checkable.
  The support edges form a DAG (are acyclic); evidence nodes are its sources.
- The squashing function `h(x) = max(0,x)² / (1 + max(0,x)²)` on the reals.
- The per-stratum STRENGTH at a threshold `t ∈ {0,1,2,3}`: keep only edges with warrant rank ≥ `t`; an evidence
  node has strength `1`; a claim node `a` has strength `h(E_a)` with energy `E_a = (sum of kept supporters'
  strengths) − (sum of kept attackers' strengths)`. Because the support edges are acyclic this is a well-founded
  recursion (a topological fold), not an iterated fixed point.
- The PROFILE of the thesis: the 4-tuple of its strength at the four nested thresholds. The LEXICOGRAPHIC order
  on profiles, most-checkable component first.

## Theorem (target)
For any node `X`: promoting a support edge **incident on `X`** (an edge whose head is `X`) to a strictly higher
warrant rank yields a profile of `X` that is lexicographically ≥ the original; promoting an attack edge incident
on `X` yields a profile of `X` lexicographically ≤ the original. The thesis is the special case. This is a LOCAL
property — the effect of promoting an edge on a node it is *not* incident on is not sign-determined (bipolar
argumentation is globally non-monotone via rebuttal chains: promoting a deep attack can raise a distant target),
and that global case is explicitly OUT OF SCOPE. Do not attempt to prove a pointwise-over-all-nodes version; it
is false.

## Idea
(Advisory planner steer — a tractability hint, not a mandate; the kernel still gates.) Three ingredients compose
the result. First, `h` is monotone nondecreasing on `ℝ` and nonnegative — the only analytic step, available from
Mathlib (`x ↦ x²/(1+x²)` is monotone on the nonnegatives). Second — the LOCAL monotonicity principle — per
stratum a node `X`'s strength is monotone nondecreasing in the kept support edges **incident on `X`** and
antitone in the kept attack edges incident on `X`, immediate from the first fact (`X`'s energy rises when a
supporter is added, falls when an attacker is added). This is local to `X`; do NOT prove a pointwise-over-all-
nodes version — it is false for bipolar graphs (a supporter added to an attacker lowers the attacker's target).
Third, componentwise `≤` implies lexicographic `≤` — a short order lemma. The theorem follows because raising the
rank of an edge incident on `X` keeps that edge at strictly more thresholds and drops it at none: at each
newly-keeping stratum `X`'s strength moves weakly in the edge's direction (monotone for a support edge, antitone
for an attack edge) and is unchanged at every other stratum, so `X`'s profile is componentwise and hence
lexicographically ordered as claimed. Keep the graph finite and decidable; the only real-analysis is `h`'s
monotonicity, everything else is finite and order-theoretic.
