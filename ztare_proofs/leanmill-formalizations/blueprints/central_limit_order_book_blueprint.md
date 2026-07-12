# Central limit order book — the resting book never crosses, and matching respects price-time priority

Opens the **market-microstructure** frontier, and the discrete result a reviewer would demand: the AMM is a
continuous algebraic invariant (`x·y = k`), but the traditional exchanges — Nasdaq, CME, Treasury markets — run on
a discrete **central limit order book** with price-time priority. This is the library's first result over a
discrete order-book data structure subject to adversarial state mutation, not a real-number inequality. The claim
is a safety invariant over reachable book states: across any stream of limit-order injections, market orders, and
cancellations, the resting book never crosses itself — the best bid is strictly below the best ask — and a
marketable order executes against resting orders in strict price-then-time priority. Proving the safety of a
queueing structure under adversarial mutation is the discrete counterpart of the AMM invariant.

Assumption-accounting note: the results depend on (1) a **book as two priority-ordered sides** — resting bids
ordered by (price descending, arrival ascending) and resting asks by (price ascending, arrival ascending), each
order carrying a price, an arrival index, and a positive quantity; (2) the **matching rule** — an incoming order is
filled against the opposite side while it is marketable (its price crosses the best resting price), and only the
unfilled remainder rests; (3) an **uncrossed opening book** — best bid strictly below best ask, or an empty side.
Surface where each is used. Keep prices and quantities over an ordered field and the arrival index over a linear
order; do **not** fix a decidable finite instance, and do not restrict to a single operation or a two-order book —
the arbitrary-stream quantification is the point. A non-closure is an honest gap. Probe the banked DeFi/AMM
`List.foldl` invariant pattern for the reachable-state induction.

## Domain
formalization-nonmath

## Theory file
limit_order_book_v3.lean

## Vocabulary (build these as definitions — do not prove them)
- **Order**: a side (bid or ask), a price, an arrival index (time priority), and a positive quantity.
- **PriorityAhead**: on the same side, order `x` has priority over `y` when `x` has the better price, or an equal
  price and an earlier arrival — the price-time priority order.
- **Book**: the resting bids and the resting asks.
- **bestBid / bestAsk**: the best resting prices — `bestBid` is the **maximum** price over ALL resting bids and
  `bestAsk` is the **minimum** price over ALL resting asks (a max/min over the entire side, order-independent —
  NOT the first element of a list). Absent on an empty side. The "best price" is intrinsic to the set of resting
  orders, so it does not depend on how the book happens to be stored.
- **Uncrossed**: `bestBid < bestAsk` whenever both sides are populated (an empty side is vacuously uncrossed).
- **Marketable**: an incoming order crosses the opposite side's best price — a buy is marketable iff the opposite
  side HAS a best ask and it is `≤` the buy's price; a sell iff there is a best bid `≥` the sell's price. Formalize
  it as a **DECIDABLE, computable test on the opposite best-price OPTION** (e.g. the best-ask option is *some* price
  that is `≤` the incoming price) — a `Bool`/`Decidable Prop` that REDUCES, **never** an opaque `∃`-existential
  (which forces a `noncomputable`/`Classical` definition that will not unfold in proofs).
- **matchInto**: a **plain computable `def`** (never `noncomputable`, never `by classical`): if the incoming order
  is marketable its marketable part executes against the opposite side and only the non-marketable remainder rests;
  if it is not marketable it simply rests. Define it by a **direct `if` on the decidable `Marketable`** so it
  unfolds definitionally (`simp [matchInto]` / `if_pos` reduce it). **cancel**: remove a resting order; a book
  **operation** is a limit injection, a market order, or a cancellation.
- **postOps**: apply a finite sequence of operations to a book in order (a left fold).

## Anchors (prove these — they PIN each def's meaning; a representation-dependent def cannot prove them)
- **bestBid is the maximum resting bid price**: every resting bid's price is `≤ bestBid`, and when the bid side is
  non-empty `bestBid` equals the price of some resting bid (it is *achieved*). A first-element/`head` definition
  cannot prove this on an unordered book — the anchor forces the order-independent maximum.
- **bestAsk is the minimum resting ask price**: symmetric — every resting ask's price is `≥ bestAsk`, and `bestAsk`
  is the price of some resting ask when the ask side is non-empty.

## Target
Consider a central limit order book — priority-ordered resting bids and asks — evolved by a matching engine that
injects limit orders (filling any marketable part first), executes market orders, and processes cancellations.
Starting from an uncrossed book, after **any** finite sequence of these operations, in any interleaving, the
resting book stays uncrossed at every state it passes through: whenever both sides are populated, the best bid is
strictly below the best ask, so the book never crosses itself.

## Idea
The reachable-state safety invariant follows the banked DeFi admissible-sequence and AMM `executeTrades` shape — a
fold over the operation stream from an uncrossed opening book. Keep prices, quantities, and the arrival index as
parameters over ordered carriers; do not fix a decidable instance or collapse the operation stream to a single
step.
