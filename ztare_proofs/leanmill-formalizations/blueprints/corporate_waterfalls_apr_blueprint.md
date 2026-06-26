# Absolute Priority Rule in a liquidation waterfall (priority order · no junior leapfrog)

The formal core of distressed-debt restructuring: when a firm's assets are distributed in default or
liquidation, value flows to creditors in PRIORITY order — a more-junior claim is satisfied only after every
claim senior to it has been paid in full. Credit agreements encode this "waterfall" as a natural-language
state machine; a kernel-checked proof guarantees that under NO available-value scenario can a junior claim
leapfrog a senior one. This blueprint targets the GENERAL invariant: a priority order over creditor tranches
(a single seniority chain is the special case; incomparable, pari-passu tranches are allowed), claims and
distributions as nonnegative quantities, with no simplifying restriction pre-imposed. None of this vocabulary
is in Mathlib — theory-building. Probe Mathlib with Loogle and the warm checker; decompose however the kernel
teaches. A non-closure is an honest gap, never a fake closure, and never a silent restriction.

## Domain
formalization-nonmath

## Theory file
absolute_priority_waterfall.lean

The bespoke vocabulary Mathlib lacks — establish each once, over whatever order/number structure the result
actually requires (do not pre-narrow it), and never "prove" a definition:
- **Creditor tranches with claims** — a collection of creditor tranches, each carrying a nonnegative claim
  amount (the face value owed to that tranche).
- **Priority order** — an order on tranches recording seniority ("is paid before"); allow it to be partial
  (incomparable / pari-passu tranches), with a total seniority chain as the special case.
- **Distribution (the waterfall)** — given a nonnegative pool of asset value available at liquidation, the
  amount distributed to each tranche: nonnegative, never exceeding that tranche's claim, and totalling at most
  the available pool (feasibility / value conservation).
- **Absolute Priority Rule (APR)** — the property that a tranche receives a strictly positive distribution only
  when every tranche senior to it has been paid its claim in full.

## Idea
(Advisory planner context — a tractability steer, NOT a formalization mandate.) The faithful AND tractable
structure for pari-passu is a RANKED seniority: each tranche carries a seniority rank, "strictly senior" means a
lower rank, and equal-rank tranches are pari-passu. This is a total preorder / ranked levels — strictly MORE
general than a strict `LinearOrder` chain, which forbids ties. Model the rank concretely (e.g. `rank : ι → ℕ`, or
a `LinearOrder` on a separate level/quotient type) so that two DISTINCT tranches can share a rank; do NOT put a
`[LinearOrder]` on the tranche index ι itself, because that makes pari-passu impossible. Within a rank level, when
the residual pool cannot cover the level's total claim, the tranches share it PRO-RATA by claim size (each gets
`claims i / level_total · residual`), capped at its own claim; when the residual covers the level, each is paid in
full. Feasibility then follows level by level (each level distributes at most its residual; residuals telescope
down the ranks). The strict-total-order closed form `WaterfallDistribution` (min-cap by the strictly-senior
residual) is the already-banked special case — CITE it; this run ADDS the pari-passu/pro-rata generalization, it
does not redo it.

## Target
The strict-total-order special case is ALREADY PROVEN AND BANKED (`waterfallDistribution_feasible_of_linearOrder`,
`waterfallDistribution_absolutePriority_of_linearOrder`, `waterfallDistribution_conclusion` — cite these, do not
re-derive them). THIS run's deliverable is the GENERAL case that admits PARI-PASSU (equal-seniority) tranches that
share pro-rata. Over a ranked seniority (equal-rank ties allowed — the tranche index ι must NOT carry
`[LinearOrder]`, since that forbids ties; model seniority by a rank so equal-rank pari-passu is representable),
define the pari-passu pro-rata distribution waterfall and prove BOTH:
1. **Feasibility** — every tranche's distribution is nonnegative and at most its claim, and the total amount
   distributed does not exceed the available value — for the general ranked order, with pari-passu tranches
   sharing the residual pro-rata by claim size.
2. **Absolute priority** — whenever a tranche receives a strictly positive distribution, every STRICTLY-senior
   tranche (lower rank) is paid its claim in full. (Pari-passu equals do not block one another; only strict
   seniors do.)

The theorem MUST apply to a genuine pari-passu instance — at least two equal-rank tranches whose claims jointly
exceed the residual, splitting it pro-rata — so it MUST NOT silently retreat to a strict total order. Do not
assume the available value suffices to reach any particular tranche, and do not let a zero-value (empty)
liquidation make the priority statement vacuously true.
