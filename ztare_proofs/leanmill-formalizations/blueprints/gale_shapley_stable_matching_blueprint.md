# Stable matching — deferred acceptance produces a matching with no blocking pair, across any complete proposal run

Opens the **market design / two-sided matching** frontier — the mechanism that clears the medical-residency match
(NRMP), public-school choice, and kidney exchange, and the one whose "intent" is contested in court and in policy
(the NRMP faced antitrust litigation over exactly what the match guarantees). The iconic result is Gale–Shapley:
run the deferred-acceptance procedure — each unengaged agent proposes down its preference list, each receiver keeps
its best proposer so far and rejects the rest — and the outcome is **stable**: no man and woman both strictly
prefer each other to the partner the match assigned them. Stability is the property the field means by "the match
is fair to participants," and it is what makes a centralized clearinghouse hold together against side deals. This is
the library's first result over an **iterative allocation process whose invariant is a monotone tentative
assignment** — the deferred-acceptance reachable-state induction, a discrete counterpart of the CLOB matching
engine, over preference orders rather than prices.

Assumption-accounting note: the results depend on (1) **strict preferences** — each man strictly ranks the women
and each woman strictly ranks the men, so "most preferred remaining" and "prefers m to my partner" are
unambiguous (no ties); (2) the **deferred-acceptance rule** — a woman holding a man releases him only for a man she
strictly prefers, and a man proposes to women in strict decreasing order of his preference and never re-proposes to
one who rejected him; (3) a **complete (quiescent) run** — the proposal schedule runs until no unengaged man has any
un-proposed woman left. Assumption (3) is the load-bearing admissibility hypothesis, and dropping it is exactly how
a blocking pair survives (a man who never got to propose to a woman he prefers). Surface where each is used. Keep
the two sides as arbitrary finite carriers and each agent's preference as a decidable strict linear order over the
opposite side; do **not** fix a decidable finite instance, and do not restrict to a single proposal step or a
two-agent market — the quantification over an arbitrary complete run is the point. A non-closure is an honest gap.
Probe the banked DeFi/AMM/CLOB `List.foldl` reachable-state invariant pattern for the deferred-acceptance induction.

## Domain
formalization-nonmath

## Theory file
gale_shapley_stable_matching_theory.lean

## Property class
SAFETY. The Target is an invariant of the terminal reachable state — the quiescent matching admits no blocking
pair — proved by induction over the proposal schedule (the DeFi/AMM/CLOB `List.foldl` shape). The **LIVENESS** dual
is deliberately **not** proven: that a quiescent state is always reached (deferred acceptance terminates, so a
complete stable matching always exists). Existence-via-termination is the frontier the library has not yet closed;
this target assumes a run reaches quiescence and characterizes what that terminal state guarantees.

## Vocabulary (build these as definitions — do not prove them)
- **Man / Woman**: the two finite sides of the market (the proposing side and the receiving side).
- **prefM / prefW**: `prefM m x y` means man `m` strictly prefers woman `x` to woman `y`; `prefW w a b` means woman
  `w` strictly prefers man `a` to man `b`. Each is a **strict linear order over the opposite side** — irreflexive,
  transitive, and total on distinct agents (any two distinct alternatives are comparable) — and **decidable**, so
  the choice tests below `REDUCE` rather than sitting behind an opaque `∃`.
- **chooseBetterForW**: given a woman `w` and two men, the man `w` prefers — a **plain computable `def`** by a
  direct `if` on the decidable `prefW` (so `simp [chooseBetterForW]` / `if_pos` reduce it). It returns one of the
  two men, never a third.
- **Matching**: an assignment `held : Woman → Option Man` (the man a woman currently holds, or none) in which no man
  is held by two women — the deferred-acceptance process maintains this injectivity, since a man proposes only while
  unheld. **partnerOfMan**: the woman holding a given man, or none (well-defined by that injectivity).
- **freeMan**: a man no woman currently holds.
- **BlockingPair**: a man `m` and woman `w` such that `m` strictly prefers `w` to `partnerOfMan m` (or `m` is a
  freeMan) **and** `w` strictly prefers `m` to `held w` (or `w` holds no one) — both would defect from the match to
  pair with each other. Formalize it as a **decidable** predicate on the two `Option` partners (a `Bool`/`Decidable
  Prop` that reduces), never an opaque existential.
- **Stable**: a matching with **no** blocking pair.
- **ProposalState**: the deferred-acceptance state — the current `held : Woman → Option Man` together with, for each
  man, `rem : Man → List Woman`, the women he has **not yet** proposed to, in his strict preference order.
- **openingState**: every woman holds no one (`held w = none`) and every man's `rem` is his full preference-ordered
  list of women.
- **complete preferences**: at the opening state every man's list `rem` lists **every** woman — no woman is missing
  from any man's ranking. This is what makes quiescence mean "has proposed to everyone": a quiescent man has
  exhausted his `rem`, so under complete preferences he has genuinely proposed to every woman; WITHOUT it he may
  have exhausted only a **partial** list and still strictly prefer a woman he never reached, and that pair blocks.
  It is a hypothesis of the stability Target and of the quiescent-stability lemma — kept **separate** from the
  proposal-soundness invariants, since the load-bearing non-quiescence witness deliberately does not assume it.
- **proposalStep**: a **plain computable `def`** advancing one proposal — given a freeMan `m` whose `rem m` is
  nonempty, `m` proposes to its head `w`; `w` becomes `chooseBetterForW w` applied to her current holder and `m`
  (keeping the better, rejecting the other); `rem m` drops its head. A step that names an ineligible man is the
  identity. Define it by a **direct `if`** on the decidable freeMan/`rem` tests so it unfolds definitionally.
- **postProposals**: apply a finite proposal **schedule** (a `List Man`, the order in which men are activated to
  make their next proposal) to a state in order — a left fold of `proposalStep`.
- **reachable**: a state equal to `postProposals sched openingState` for some finite schedule `sched`.
- **Quiescent**: a state in which **no** freeMan has a nonempty `rem` — every man is either held by a woman or has
  exhausted his preference list. The completeness hypothesis of the Target.

## Anchors (prove these — they PIN each def's meaning; a representation-dependent def cannot prove them)
- **chooseBetterForW returns the woman's genuine preference-maximum of the two**: for any woman `w` and men `a`, `b`,
  `chooseBetterForW w a b` is one of `a`, `b`, and `w` weakly prefers it to both. A positional / first-argument
  choice cannot prove this — the anchor forces the preference-driven selection, the analog of `bestBid` being the
  max rather than a list head.
- **prefW / prefM are strict linear orders — comparability and no ties**: for distinct men `a`, `b`, exactly one of
  `prefW w a b` and `prefW w b a` holds (symmetrically for `prefM`). This forces the total, tie-free preference
  relation the "most preferred remaining" pointer and the blocking test rely on, over a merely partial or
  positional ranking.

## Target
Consider man-proposing deferred acceptance over two finite sides with strict **and complete** preferences — every
man's opening list ranks **every** woman: starting from the empty
matching, unengaged men propose to women in strict order of preference, and each woman tentatively holds the best
proposer she has seen and rejects the rest, a held man being displaced only by one she strictly prefers. After
**any** finite proposal schedule that runs to quiescence — no unengaged man has an un-proposed woman left — the
resulting matching is **stable**: there is no blocking pair, i.e. no man and woman who each strictly prefer the
other to the partner the match assigned them. So the outcome of a complete deferred-acceptance run is immune to
pairwise defection. Surface that quiescence is load-bearing: an incomplete run can leave an unengaged man who
strictly prefers a woman he never reached, and that pair blocks — so stability is a property of the **completed**
run, not of an arbitrary partial one. (The dual guarantee that a quiescent state is always reached — termination
and hence existence of a stable matching — is the liveness result this target does not cover.)

## Idea
Everything runs over `reachable` states obtained by `List.foldl proposalStep` from `openingState` — the same
reachable-state shape as the banked DeFi admissible-sequence and CLOB matching-engine invariants, so mirror them:
induct on the schedule, and at each `proposalStep` the woman it touches either keeps her holder or replaces it by
`chooseBetterForW`, which the anchor pins to be weakly better — the woman-improvement invariant is that monotonicity
carried along the fold. The rejected-dominated lemma is the same invariant read at a rejection: `chooseBetterForW`
kept a man she prefers to the rejected one, and monotonicity carries it forward. The initial-segment lemma is
structural: `rem m` starts as `m`'s full preference-ordered list and `proposalStep` drops only its head, so the
proposed set is exactly the complement prefix. Stability at quiescence combines them: if `m` strictly prefers `w` to
his partner then by the initial-segment lemma `m` proposed to `w`, and — since he is not held by her — she rejected
him, so by the rejected-dominated lemma she holds a man she strictly prefers to `m`; hence `w` does not prefer `m`
to her partner and `(m, w)` is no blocking pair. The load-bearing witness is a small explicit market (a couple of
men and women) run one step short of quiescence, exhibiting a surviving blocking pair. Probe Mathlib's `List.foldl`
and `List` prefix lemmas and the order/decidability machinery; keep the two sides as finite parameters and the
preferences as decidable strict linear orders, and do not fix a decidable carrier or collapse the schedule to a
single step. This is a frontier target — the quiescent-stability capstone is a real lift; the woman-improvement
invariant, the rejected-dominated lemma, and the load-bearing witness are the reachable-state-invariant spine the
engine already nails if the capstone resists.
