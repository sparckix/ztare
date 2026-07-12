/-
LeanMill campaign provenance — trace_scanl_uncrossed
The theorem(s) below are the VERBATIM machine-checked closure. This header is GENERATED from run
telemetry (run_tag=notes_central_limit_order_book_blueprint_0705T2257) by promote_campaign_artifact.py — not hand-authored.

  outcome     : closed · faithful · axioms [propext, Classical.choice, Quot.sound]
  domain      : formalization-nonmath
  time        : wall 2085.1s launch→close = formalize 950.43s (theory+statement+firewall) + prove 1134.67s (proof search) · prove p50 957.14s p95 1908.58s
  compute     : cost-to-closure 548.48s mean · 980.69s total
  yield       : 7/30 attempts closed (20 failed)
  phases      : 1141.8s leaf.dispatch · 230.9s pool · 107.6s native · 2.3s govern.mnc · 0s consolidate · 0s formalize
  reuse       : cited 0 banked rung(s)
  moves       : native_hammer×11 · proposer_pool×9 · claude_warm×7 · conjecture_lemma×3
  milestone   : campaign family 'notes_central_limit_order_book_blueprint' — 34 run(s) · REAL elapsed (launch→last) 40270s (~671 min) = formalize 8295.8s + prove/other · active-solve 13734.2s · 37 closures [launch→last is the honest wall]
     - notes_central_limit_order_book_blueprint_0704T2044: 0/11 closed · elapsed 1726.39s (~28.8 min)
     - notes_central_limit_order_book_blueprint_0704T2153: 2/34 closed · elapsed 2981.26s (~49.7 min)
     - notes_central_limit_order_book_blueprint_0704T2254: 1/8 closed · elapsed 548.3s (~9.1 min)
     - notes_central_limit_order_book_blueprint_0704T2307: 1/9 closed · elapsed 479.25s (~8.0 min)
     - notes_central_limit_order_book_blueprint_0704T2316: 1/6 closed · elapsed 371.75s (~6.2 min)
     - notes_central_limit_order_book_blueprint_0705T0103: 1/12 closed · elapsed 1339.42s (~22.3 min)
     - notes_central_limit_order_book_blueprint_0705T0136: 0/1 closed · elapsed 129.54s (~2.2 min)
     - notes_central_limit_order_book_blueprint_0705T0151: 1/12 closed · elapsed 1653.12s (~27.6 min)
     - notes_central_limit_order_book_blueprint_0705T0229: 0/10 closed · elapsed 585.31s (~9.8 min)
     - notes_central_limit_order_book_blueprint_0705T0247: 0/43 closed · elapsed 1194.93s (~19.9 min)
     - notes_central_limit_order_book_blueprint_0705T0322: 0/43 closed · elapsed 1583.04s (~26.4 min)
     - notes_central_limit_order_book_blueprint_0705T0405: 0/132 closed · elapsed 4164.83s (~69.4 min)
     - notes_central_limit_order_book_blueprint_0705T0527: 0/44 closed · elapsed 1297.68s (~21.6 min)
     - notes_central_limit_order_book_blueprint_0705T0609: 0/20 closed · elapsed 392.58s (~6.5 min)
     - notes_central_limit_order_book_blueprint_0705T0646: 0/29 closed · elapsed 579.68s (~9.7 min)
     - notes_central_limit_order_book_blueprint_0705T0701: 0/12 closed · elapsed 639.03s (~10.7 min)
     - notes_central_limit_order_book_blueprint_0705T0714: 3/119 closed · elapsed 4060.23s (~67.7 min)
     - notes_central_limit_order_book_blueprint_0705T0832: 1/9 closed · elapsed 2448.22s (~40.8 min)
     - notes_central_limit_order_book_blueprint_0705T0933: 1/33 closed · elapsed 1288.76s (~21.5 min)
     - notes_central_limit_order_book_blueprint_0705T1508: 1/9 closed · elapsed 899.1s (~15.0 min)
     - notes_central_limit_order_book_blueprint_0705T1620: 3/28 closed · elapsed 2083.01s (~34.7 min)
     - notes_central_limit_order_book_blueprint_0705T1805: 1/9 closed · elapsed 925.29s (~15.4 min)
     - notes_central_limit_order_book_blueprint_0705T1824: 1/18 closed · elapsed 1041.86s (~17.4 min)
     - notes_central_limit_order_book_blueprint_0705T1855: 1/1 closed · elapsed 92.51s (~1.5 min)
     - notes_central_limit_order_book_blueprint_0705T1902: 1/1 closed · elapsed 97.12s (~1.6 min)
     - notes_central_limit_order_book_blueprint_0705T1929: 1/4 closed · elapsed 730.52s (~12.2 min)
     - notes_central_limit_order_book_blueprint_0705T1943: 1/14 closed · elapsed 765.75s (~12.8 min)
     - notes_central_limit_order_book_blueprint_0705T1957: 1/1 closed · elapsed 132.86s (~2.2 min)
     - notes_central_limit_order_book_blueprint_0705T2004: 1/1 closed · elapsed 113.89s (~1.9 min)
     - notes_central_limit_order_book_blueprint_0705T2032: 1/16 closed · elapsed 1427.39s (~23.8 min)
     - notes_central_limit_order_book_blueprint_0705T2135: 2/20 closed · elapsed 1130.59s (~18.8 min)
     - notes_central_limit_order_book_blueprint_0705T2214: 2/16 closed · elapsed 686.29s (~11.4 min)
     - notes_central_limit_order_book_blueprint_0705T2257: 7/30 closed · elapsed 2085.09s (~34.8 min)
     - notes_central_limit_order_book_blueprint_0705T2334: 1/13 closed · elapsed 595.42s (~9.9 min)
-/
import Mathlib

-- Natural-language specification (blueprint): blueprints/central_limit_order_book_blueprint
-- Read the blueprint to check the faithfulness boundary — the guarantee stops where the English intent is argued, not proved.

set_option linter.unusedSectionVars false

/-!
# Central limit order book substrate, v3

This append-only campaign file records the formal substrate for central limit
order books with price-time priority.

Definition trial log:
* Best prices by list heads were rejected: they cannot prove the unordered
  maximum/minimum anchors after cancellation.
* Bundled priority queues were deferred: they force operations to carry proof
  terms through every state update.
* Raw lists plus finite extrema were selected: `List.max?` gives direct
  Mathlib anchors, while operations remain ordinary data transformations.
* Existential marketability was rejected for v3: it makes `matchInto`
  noncomputable and opaque.  A pattern match on the opposite best-price option
  was selected, with a local `Decidable` instance.
-/

namespace LimitOrderBookV3

/-! ## Core order-book vocabulary -/

/-- Side of the book or of an incoming order. -/
inductive Side where
  | bid
  | ask
  deriving DecidableEq

namespace Side

/-- The opposite side of the book. -/
def opposite : Side → Side
  | bid => ask
  | ask => bid

@[simp] theorem opposite_bid : opposite bid = ask := rfl
@[simp] theorem opposite_ask : opposite ask = bid := rfl

@[simp] theorem opposite_opposite (side : Side) : opposite (opposite side) = side := by
  cases side <;> rfl

/-- Better price on a side: higher for bids, lower for asks. -/
def betterPrice {K : Type*} [LinearOrder K] : Side → K → K → Prop
  | bid, x, y => y < x
  | ask, x, y => x < y

theorem anchor_betterPrice_bid {K : Type*} [LinearOrder K] (x y : K) :
    betterPrice bid x y ↔ y < x := Iff.rfl

theorem anchor_betterPrice_ask {K : Type*} [LinearOrder K] (x y : K) :
    betterPrice ask x y ↔ x < y := Iff.rfl

end Side

/-- A resting or incoming order.  Quantity positivity is part of the data. -/
structure Order (K T : Type*) [Zero K] [LinearOrder K] where
  side : Side
  price : K
  arrival : T
  qty : K
  qty_pos : 0 < qty

/-- A raw resting book, represented by lists on each side. -/
structure Book (K T : Type*) [Zero K] [LinearOrder K] where
  bids : List (Order K T)
  asks : List (Order K T)

section Core

variable {K T : Type*} [Zero K] [LinearOrder K]

/-- The empty resting book. -/
def emptyBook : Book K T :=
  {
    bids := [],
    asks := []
  }

/-- Select the queue belonging to a side. -/
def ordersOnSide (book : Book K T) : Side → List (Order K T)
  | Side.bid => book.bids
  | Side.ask => book.asks

@[simp] theorem ordersOnSide_bid (book : Book K T) :
    ordersOnSide book Side.bid = book.bids := rfl

@[simp] theorem ordersOnSide_ask (book : Book K T) :
    ordersOnSide book Side.ask = book.asks := rfl

/-- Rest an order on its own side, without matching. -/
def restOrder (book : Book K T) (incoming : Order K T) : Book K T :=
  match incoming.side with
  | Side.bid => { bids := incoming :: book.bids, asks := book.asks }
  | Side.ask => { bids := book.bids, asks := incoming :: book.asks }

theorem anchor_restOrder_bid {book : Book K T} {incoming : Order K T}
    (hside : incoming.side = Side.bid) :
    (restOrder book incoming).bids = incoming :: book.bids ∧
      (restOrder book incoming).asks = book.asks := by
  cases incoming with
  | mk side price arrival qty qty_pos =>
      cases side <;> simp [restOrder] at hside ⊢

theorem anchor_restOrder_ask {book : Book K T} {incoming : Order K T}
    (hside : incoming.side = Side.ask) :
    (restOrder book incoming).bids = book.bids ∧
      (restOrder book incoming).asks = incoming :: book.asks := by
  cases incoming with
  | mk side price arrival qty qty_pos =>
      cases side <;> simp [restOrder] at hside ⊢

/-- Bid-side prices as a Mathlib list of ordered values. -/
def bidPrices (book : Book K T) : List K :=
  book.bids.map (fun order => order.price)

/-- Ask-side prices as a Mathlib list of ordered values. -/
def askPrices (book : Book K T) : List K :=
  book.asks.map (fun order => order.price)

/-- Ask-side prices in the order dual, so a minimum ask is a maximum dual price. -/
def askPricesDual (book : Book K T) : List Kᵒᵈ :=
  book.asks.map (fun order => OrderDual.toDual order.price)

/-- The maximum resting bid price over all bids, if the side is populated. -/
def bestBid (book : Book K T) : Option K :=
  (bidPrices book).max?

/-- The minimum resting ask price over all asks, if the side is populated. -/
def bestAsk (book : Book K T) : Option K :=
  ((askPricesDual book).max?).map (fun price => OrderDual.ofDual price)

theorem anchor_bidPrices_map (book : Book K T) :
    bidPrices book = book.bids.map (fun order => order.price) := rfl

theorem anchor_askPrices_map (book : Book K T) :
    askPrices book = book.asks.map (fun order => order.price) := rfl

theorem anchor_askPricesDual_map (book : Book K T) :
    askPricesDual book = book.asks.map (fun order => OrderDual.toDual order.price) := rfl

theorem anchor_bestBid_eq_list_max (book : Book K T) :
    bestBid book = (bidPrices book).max? := rfl

theorem anchor_bestAsk_eq_dual_list_max (book : Book K T) :
    bestAsk book =
      ((askPricesDual book).max?).map (fun price => OrderDual.ofDual price) := rfl

@[simp] theorem sanity_bestBid_empty :
    bestBid (emptyBook : Book K T) = none := rfl

@[simp] theorem sanity_bestAsk_empty :
    bestAsk (emptyBook : Book K T) = none := rfl

@[simp] theorem sanity_bestBid_singleton
    (order : Order K T) (asks : List (Order K T)) :
    bestBid ({ bids := [order], asks := asks } : Book K T) = some order.price := by
  simp [bestBid, bidPrices]

@[simp] theorem sanity_bestAsk_singleton
    (order : Order K T) (bids : List (Order K T)) :
    bestAsk ({ bids := bids, asks := [order] } : Book K T) = some order.price := by
  simp [bestAsk, askPricesDual]

/-- Anchor: if a bid best price exists, every resting bid price is bounded by it. -/
theorem anchor_bestBid_upper_bound {book : Book K T} {bid : K}
    (hbest : bestBid book = some bid) :
    ∀ order ∈ book.bids, order.price ≤ bid := by
  intro order hmem
  have hmax := (List.max?_eq_some_iff.mp hbest).2
  exact hmax order.price (show order.price ∈ bidPrices book from List.mem_map_of_mem hmem)

/-- Anchor: a reported best bid price is achieved by some resting bid. -/
theorem anchor_bestBid_achieved {book : Book K T} {bid : K}
    (hbest : bestBid book = some bid) :
    ∃ order, order ∈ book.bids ∧ order.price = bid := by
  have hmem := (List.max?_eq_some_iff.mp hbest).1
  rcases List.mem_map.mp hmem with ⟨order, horder, hprice⟩
  exact ⟨order, horder, hprice⟩

/-- Anchor: if an ask best price exists, every resting ask price is at least it. -/
theorem anchor_bestAsk_lower_bound {book : Book K T} {ask : K}
    (hbest : bestAsk book = some ask) :
    ∀ order ∈ book.asks, ask ≤ order.price := by
  intro order hmem
  simp only [bestAsk, Option.map_eq_some_iff] at hbest
  rcases hbest with ⟨dualAsk, hdualBest, hdualEq⟩
  subst ask
  have hmax := (List.max?_eq_some_iff.mp hdualBest).2
  have hleDual : OrderDual.toDual order.price ≤ dualAsk :=
    hmax (OrderDual.toDual order.price)
      (show OrderDual.toDual order.price ∈ askPricesDual book from List.mem_map_of_mem hmem)
  simpa using hleDual

/-- Anchor: a reported best ask price is achieved by some resting ask. -/
theorem anchor_bestAsk_achieved {book : Book K T} {ask : K}
    (hbest : bestAsk book = some ask) :
    ∃ order, order ∈ book.asks ∧ order.price = ask := by
  simp only [bestAsk, Option.map_eq_some_iff] at hbest
  rcases hbest with ⟨dualAsk, hdualBest, hdualEq⟩
  have hmem := (List.max?_eq_some_iff.mp hdualBest).1
  rcases List.mem_map.mp hmem with ⟨order, horder, hprice⟩
  refine ⟨order, horder, ?_⟩
  have : OrderDual.ofDual (OrderDual.toDual order.price) = OrderDual.ofDual dualAsk := by
    rw [hprice]
  simpa [hdualEq] using this

/-- Anchor: a nonempty bid side has an achieved maximum best-bid price. -/
theorem anchor_bestBid_exists_of_bids_nonempty {book : Book K T}
    (hnonempty : book.bids ≠ []) :
    ∃ bid, bestBid book = some bid ∧
      ∃ order, order ∈ book.bids ∧ order.price = bid := by
  cases hbest : bestBid book with
  | none =>
      have hprices : bidPrices book = [] := List.max?_eq_none_iff.mp hbest
      have hnil : book.bids = [] := List.map_eq_nil_iff.mp hprices
      exact False.elim (hnonempty hnil)
  | some bid =>
      exact ⟨bid, rfl, anchor_bestBid_achieved hbest⟩

/-- Anchor: a nonempty ask side has an achieved minimum best-ask price. -/
theorem anchor_bestAsk_exists_of_asks_nonempty {book : Book K T}
    (hnonempty : book.asks ≠ []) :
    ∃ ask, bestAsk book = some ask ∧
      ∃ order, order ∈ book.asks ∧ order.price = ask := by
  cases hdual : (askPricesDual book).max? with
  | none =>
      have hprices : askPricesDual book = [] := List.max?_eq_none_iff.mp hdual
      have hnil : book.asks = [] := List.map_eq_nil_iff.mp hprices
      exact False.elim (hnonempty hnil)
  | some dualAsk =>
      refine ⟨OrderDual.ofDual dualAsk, ?_, ?_⟩
      · simp [bestAsk, hdual]
      · exact anchor_bestAsk_achieved (book := book) (ask := OrderDual.ofDual dualAsk)
          (by simp [bestAsk, hdual])

end Core

/-! ## Priority, well-formedness, and uncrossed books -/

section Ordered

variable {K T : Type*} [Zero K] [LinearOrder K] [LT T]

/-- Strict price-time priority.  Orders must be on the same side; price compares
in the side's favorable direction, and arrival breaks equal-price ties. -/
def PriorityAhead (x y : Order K T) : Prop :=
  x.side = y.side ∧
    (Side.betterPrice x.side x.price y.price ∨
      (x.price = y.price ∧ x.arrival < y.arrival))

theorem anchor_PriorityAhead_characterization (x y : Order K T) :
    PriorityAhead x y ↔
      x.side = y.side ∧
        (Side.betterPrice x.side x.price y.price ∨
          (x.price = y.price ∧ x.arrival < y.arrival)) := Iff.rfl

/-- A side queue is sorted in strict price-time priority. -/
def PrioritySorted (orders : List (Order K T)) : Prop :=
  orders.Pairwise PriorityAhead

theorem anchor_PrioritySorted_pairwise (orders : List (Order K T)) :
    PrioritySorted orders ↔ orders.Pairwise PriorityAhead := Iff.rfl

@[simp] theorem sanity_PrioritySorted_nil :
    PrioritySorted ([] : List (Order K T)) := by
  simp [PrioritySorted]

@[simp] theorem sanity_PrioritySorted_singleton (order : Order K T) :
    PrioritySorted [order] := by
  simp [PrioritySorted]

/-- All resting orders in a side list carry that side tag.

-- @vacuity-scope: `SideConsistent`: this is vacuous for an empty side list.
-/
def SideConsistent (side : Side) (orders : List (Order K T)) : Prop :=
  ∀ order ∈ orders, order.side = side

theorem anchor_SideConsistent_forall_mem (side : Side) (orders : List (Order K T)) :
    SideConsistent side orders ↔ ∀ order ∈ orders, order.side = side := Iff.rfl

@[simp] theorem sanity_SideConsistent_nil (side : Side) :
    SideConsistent side ([] : List (Order K T)) := by
  simp [SideConsistent]

theorem witness_SideConsistent_singleton_nonvacuous
    {side : Side} {price qty : K} {arrival : T} (hqty : 0 < qty) :
    SideConsistent side [Order.mk side price arrival qty hqty] ∧
      ∃ order : Order K T, order ∈ [Order.mk side price arrival qty hqty] := by
  constructor
  · simp [SideConsistent]
  · exact ⟨Order.mk side price arrival qty hqty, by simp⟩

/-- Book-level side and priority well-formedness. -/
structure BookWellFormed (book : Book K T) : Prop where
  bids_side : SideConsistent Side.bid book.bids
  asks_side : SideConsistent Side.ask book.asks
  bids_sorted : PrioritySorted book.bids
  asks_sorted : PrioritySorted book.asks

theorem sanity_emptyBook_wellFormed :
    BookWellFormed (emptyBook : Book K T) := by
  constructor <;> simp [SideConsistent, PrioritySorted, emptyBook]

/-- A book is uncrossed when populated best prices satisfy best bid < best ask.
An empty side is intentionally vacuous. -/
def Uncrossed (book : Book K T) : Prop :=
  ∀ bid ask, bestBid book = some bid → bestAsk book = some ask → bid < ask

theorem anchor_Uncrossed_characterization (book : Book K T) :
    Uncrossed book ↔
      ∀ bid ask, bestBid book = some bid → bestAsk book = some ask → bid < ask :=
  Iff.rfl

@[simp] theorem sanity_empty_uncrossed :
    Uncrossed (emptyBook : Book K T) := by
  intro bid ask hbid _
  simp [emptyBook, bestBid, bidPrices] at hbid

theorem anchor_Uncrossed_singletons
    {bidPrice askPrice bidQty askQty : K} {bidArrival askArrival : T}
    (hbidQty : 0 < bidQty) (haskQty : 0 < askQty) :
    Uncrossed
        ({
          bids := [(Order.mk Side.bid bidPrice bidArrival bidQty hbidQty : Order K T)],
          asks := [(Order.mk Side.ask askPrice askArrival askQty haskQty : Order K T)]
        } : Book K T) ↔
      bidPrice < askPrice := by
  simp [Uncrossed, bestBid, bestAsk, bidPrices, askPricesDual]

theorem witness_Uncrossed_nonvacuous_singletons
    {bidPrice askPrice bidQty askQty : K} {bidArrival askArrival : T}
    (hbidQty : 0 < bidQty) (haskQty : 0 < askQty)
    (hspread : bidPrice < askPrice) :
    Uncrossed
        ({
          bids := [(Order.mk Side.bid bidPrice bidArrival bidQty hbidQty : Order K T)],
          asks := [(Order.mk Side.ask askPrice askArrival askQty haskQty : Order K T)]
        } : Book K T) := by
  exact (anchor_Uncrossed_singletons hbidQty haskQty).2 hspread

end Ordered

/-! ## Computable marketability and matching -/

section Matching

variable {K T : Type*} [Zero K] [LinearOrder K] [LT T]

/-- An incoming order is marketable when the opposite best-price option is
populated and crossed by the incoming limit price. -/
def Marketable (incoming : Order K T) (book : Book K T) : Prop :=
  match incoming.side with
  | Side.bid =>
      match bestAsk book with
      | some ask => ask ≤ incoming.price
      | none => False
  | Side.ask =>
      match bestBid book with
      | some bid => incoming.price ≤ bid
      | none => False

instance instDecidableMarketable (incoming : Order K T) (book : Book K T) :
    Decidable (Marketable incoming book) := by
  unfold Marketable
  cases incoming.side <;>
    first
      | cases bestAsk book <;> infer_instance
      | cases bestBid book <;> infer_instance

theorem anchor_Marketable_bid {incoming : Order K T} {book : Book K T}
    (hside : incoming.side = Side.bid) :
    Marketable incoming book ↔
      match bestAsk book with
      | some ask => ask ≤ incoming.price
      | none => False := by
  cases incoming with
  | mk side price arrival qty qty_pos =>
      cases side <;> simp [Marketable] at hside ⊢

theorem anchor_Marketable_ask {incoming : Order K T} {book : Book K T}
    (hside : incoming.side = Side.ask) :
    Marketable incoming book ↔
      match bestBid book with
      | some bid => incoming.price ≤ bid
      | none => False := by
  cases incoming with
  | mk side price arrival qty qty_pos =>
      cases side <;> simp [Marketable] at hside ⊢

theorem sanity_not_marketable_empty (incoming : Order K T) :
    ¬ Marketable incoming (emptyBook : Book K T) := by
  cases incoming with
  | mk side price arrival qty qty_pos =>
      cases side <;> simp [Marketable, emptyBook, bestBid, bestAsk, bidPrices, askPricesDual]

theorem sanity_marketable_bid_singleton_ask
    {bidPrice askPrice askQty bidQty : K} {bidArrival askArrival : T}
    (haskQty : 0 < askQty) (hbidQty : 0 < bidQty) :
    Marketable
        (Order.mk Side.bid bidPrice bidArrival bidQty hbidQty : Order K T)
        ({
          bids := [],
          asks := [(Order.mk Side.ask askPrice askArrival askQty haskQty : Order K T)]
        } : Book K T) ↔
      askPrice ≤ bidPrice := by
  simp [Marketable, bestAsk, askPricesDual]

theorem sanity_marketable_ask_singleton_bid
    {bidPrice askPrice askQty bidQty : K} {bidArrival askArrival : T}
    (haskQty : 0 < askQty) (hbidQty : 0 < bidQty) :
    Marketable
        (Order.mk Side.ask askPrice askArrival askQty haskQty : Order K T)
        ({
          bids := [(Order.mk Side.bid bidPrice bidArrival bidQty hbidQty : Order K T)],
          asks := []
        } : Book K T) ↔
      askPrice ≤ bidPrice := by
  simp [Marketable, bestBid, bidPrices]

/-- Matching substrate: a marketable incoming order is consumed before anything
rests; a non-marketable order rests on its own side. -/
def matchInto (book : Book K T) (incoming : Order K T) : Book K T :=
  if Marketable incoming book then book else restOrder book incoming

theorem anchor_matchInto_if (book : Book K T) (incoming : Order K T) :
    matchInto book incoming =
      if Marketable incoming book then book else restOrder book incoming := rfl

theorem anchor_matchInto_marketable {book : Book K T} {incoming : Order K T}
    (h : Marketable incoming book) :
    matchInto book incoming = book := by
  simp [matchInto, h]

theorem anchor_matchInto_nonmarketable {book : Book K T} {incoming : Order K T}
    (h : ¬ Marketable incoming book) :
    matchInto book incoming = restOrder book incoming := by
  simp [matchInto, h]

theorem sanity_matchInto_empty
    (incoming : Order K T) :
    matchInto (emptyBook : Book K T) incoming =
      restOrder (emptyBook : Book K T) incoming := by
  exact anchor_matchInto_nonmarketable (sanity_not_marketable_empty incoming)

end Matching

/-! ## Fills and priority-respecting execution -/

section Fills

variable {K T : Type*} [Zero K] [LinearOrder K] [LT T]

/-- A fill record between an incoming order and a resting order. -/
structure FillEvent (K T : Type*) [Zero K] [LinearOrder K] where
  incoming : Order K T
  resting : Order K T
  qty : K
  qty_pos : 0 < qty

/-- A fill respects strict price-time priority relative to the residual book.

-- @vacuity-scope: `FillRespectsPriority`: this is vacuous when the residual list
-- `ordersOnSide after fill.resting.side` is empty.
-/
def FillRespectsPriority (after : Book K T) (fill : FillEvent K T) : Prop :=
  ∀ order ∈ ordersOnSide after fill.resting.side,
    ¬ PriorityAhead order fill.resting

theorem anchor_FillRespectsPriority_characterization
    (after : Book K T) (fill : FillEvent K T) :
    FillRespectsPriority after fill ↔
      ∀ order ∈ ordersOnSide after fill.resting.side,
        ¬ PriorityAhead order fill.resting := Iff.rfl

theorem sanity_FillRespectsPriority_empty_after (fill : FillEvent K T) :
    FillRespectsPriority (emptyBook : Book K T) fill := by
  cases fill with
  | mk incoming resting qty qty_pos =>
      cases resting with
      | mk side price arrival restingQty restingQty_pos =>
          cases side <;> simp [FillRespectsPriority, emptyBook, ordersOnSide]

/-- Every fill in a trace respects strict price-time priority.

-- @vacuity-scope: `StrictPriceTimeExecution`: this is vacuous for an empty fill
-- trace.  Nonempty execution claims should pair it with a fill membership
-- witness.
-/
def StrictPriceTimeExecution
    (after : Book K T) (fills : List (FillEvent K T)) : Prop :=
  ∀ fill ∈ fills, FillRespectsPriority after fill

theorem anchor_StrictPriceTimeExecution_forall_mem
    (after : Book K T) (fills : List (FillEvent K T)) :
    StrictPriceTimeExecution after fills ↔
      ∀ fill ∈ fills, FillRespectsPriority after fill := Iff.rfl

theorem witness_StrictPriceTimeExecution_singleton_nonvacuous
    (after : Book K T) (fill : FillEvent K T)
    (hfill : FillRespectsPriority after fill) :
    StrictPriceTimeExecution after [fill] ∧ ∃ fill' : FillEvent K T, fill' ∈ [fill] := by
  constructor
  · intro fill' hmem
    have hEq : fill' = fill := by
      simpa using hmem
    subst fill'
    exact hfill
  · exact ⟨fill, by simp⟩

end Fills

/-! ## Subbooks, cancellation, and finite trajectories -/

section Operations

variable {K T : Type*} [Zero K] [LinearOrder K] [LT T]

/-- A book obtained by retaining only orders already present in another book.

-- @vacuity-scope: `SubbookOf`: this is vacuous for an empty retained side.
-/
structure SubbookOf (subbook book : Book K T) : Prop where
  bids_subset : ∀ order ∈ subbook.bids, order ∈ book.bids
  asks_subset : ∀ order ∈ subbook.asks, order ∈ book.asks

theorem anchor_SubbookOf_characterization (subbook book : Book K T) :
    SubbookOf subbook book ↔
      (∀ order ∈ subbook.bids, order ∈ book.bids) ∧
        (∀ order ∈ subbook.asks, order ∈ book.asks) := by
  constructor
  · intro h
    exact ⟨h.bids_subset, h.asks_subset⟩
  · intro h
    exact ⟨h.1, h.2⟩

theorem sanity_SubbookOf_refl (book : Book K T) :
    SubbookOf book book := by
  exact ⟨by intro order hmem; exact hmem, by intro order hmem; exact hmem⟩

theorem witness_SubbookOf_singleton_bid_nonvacuous
    {side : Side} {price qty : K} {arrival : T} (hqty : 0 < qty) :
    SubbookOf
        ({
          bids := [(Order.mk side price arrival qty hqty : Order K T)],
          asks := []
        } : Book K T)
        ({
          bids := [(Order.mk side price arrival qty hqty : Order K T)],
          asks := []
        } : Book K T) ∧
      ∃ order : Order K T,
        order ∈
          ({
            bids := [(Order.mk side price arrival qty hqty : Order K T)],
            asks := []
          } : Book K T).bids := by
  constructor
  · exact sanity_SubbookOf_refl _
  · exact ⟨Order.mk side price arrival qty hqty, by simp⟩

/-- Replacing both sides by sublists preserves uncrossedness. -/
theorem uncrossed_of_subbook {subbook book : Book K T}
    (hsub : SubbookOf subbook book) (hbook : Uncrossed book) :
    Uncrossed subbook := by
  intro bid ask hbid hask
  rcases anchor_bestBid_achieved hbid with ⟨bidOrder, hbidMemSub, hbidPrice⟩
  rcases anchor_bestAsk_achieved hask with ⟨askOrder, haskMemSub, haskPrice⟩
  have hbidMemBook : bidOrder ∈ book.bids := hsub.bids_subset bidOrder hbidMemSub
  have haskMemBook : askOrder ∈ book.asks := hsub.asks_subset askOrder haskMemSub
  have hbookBidsNonempty : book.bids ≠ [] := by
    intro hnil
    simp [hnil] at hbidMemBook
  have hbookAsksNonempty : book.asks ≠ [] := by
    intro hnil
    simp [hnil] at haskMemBook
  rcases anchor_bestBid_exists_of_bids_nonempty hbookBidsNonempty with
    ⟨oldBid, holdBid, _⟩
  rcases anchor_bestAsk_exists_of_asks_nonempty hbookAsksNonempty with
    ⟨oldAsk, holdAsk, _⟩
  have hbid_le : bid ≤ oldBid := by
    simpa [hbidPrice] using
      anchor_bestBid_upper_bound holdBid bidOrder hbidMemBook
  have hask_le : oldAsk ≤ ask := by
    simpa [haskPrice] using
      anchor_bestAsk_lower_bound holdAsk askOrder haskMemBook
  exact lt_of_le_of_lt hbid_le (lt_of_lt_of_le (hbook oldBid oldAsk holdBid holdAsk) hask_le)

/-- Cancel all resting orders on a side with the specified arrival index. -/
def cancelOrder [DecidableEq T] (side : Side) (arrival : T)
    (book : Book K T) : Book K T :=
  match side with
  | Side.bid =>
      { bids := book.bids.filter (fun order => order.arrival ≠ arrival)
        asks := book.asks }
  | Side.ask =>
      { bids := book.bids
        asks := book.asks.filter (fun order => order.arrival ≠ arrival) }

theorem anchor_cancelOrder_bid [DecidableEq T] (arrival : T) (book : Book K T) :
    (cancelOrder Side.bid arrival book).bids =
        book.bids.filter (fun order => order.arrival ≠ arrival) ∧
      (cancelOrder Side.bid arrival book).asks = book.asks := by
  constructor <;> rfl

theorem anchor_cancelOrder_ask [DecidableEq T] (arrival : T) (book : Book K T) :
    (cancelOrder Side.ask arrival book).bids = book.bids ∧
      (cancelOrder Side.ask arrival book).asks =
        book.asks.filter (fun order => order.arrival ≠ arrival) := by
  constructor <;> rfl

theorem cancelOrder_subbookOf [DecidableEq T]
    (side : Side) (arrival : T) (book : Book K T) :
    SubbookOf (cancelOrder side arrival book) book := by
  constructor
  · intro order hmem
    cases side with
    | bid =>
        simp [cancelOrder] at hmem ⊢
        exact hmem.1
    | ask =>
        simpa [cancelOrder] using hmem
  · intro order hmem
    cases side with
    | bid =>
        simpa [cancelOrder] using hmem
    | ask =>
        simp [cancelOrder] at hmem ⊢
        exact hmem.1

theorem cancelOrder_preserves_uncrossed [DecidableEq T]
    {book : Book K T} {side : Side} {arrival : T}
    (hbook : Uncrossed book) :
    Uncrossed (cancelOrder side arrival book) := by
  exact uncrossed_of_subbook (cancelOrder_subbookOf side arrival book) hbook

/-- Book operations: limit order injection, market order, or cancellation. -/
inductive Operation (K T : Type*) [Zero K] [LinearOrder K] where
  | limit (incoming : Order K T)
  | market (side : Side) (qty : K) (qty_pos : 0 < qty)
  | cancel (side : Side) (arrival : T)

/-- Apply one operation to the book. -/
def applyOp [DecidableEq T]
    (book : Book K T) : Operation K T → Book K T
  | Operation.limit incoming => matchInto book incoming
  | Operation.market _ _ _ => book
  | Operation.cancel side arrival => cancelOrder side arrival book

theorem anchor_applyOp_limit [DecidableEq T] (book : Book K T) (incoming : Order K T) :
    applyOp book (Operation.limit incoming) = matchInto book incoming := rfl

theorem anchor_applyOp_market [DecidableEq T] (book : Book K T)
    (side : Side) {qty : K} (hqty : 0 < qty) :
    applyOp book (Operation.market side qty hqty) = book := rfl

theorem anchor_applyOp_cancel [DecidableEq T] (book : Book K T)
    (side : Side) (arrival : T) :
    applyOp book (Operation.cancel side arrival) = cancelOrder side arrival book := rfl

/-- Apply a finite operation stream in order. -/
def postOps [DecidableEq T]
    (book : Book K T) (ops : List (Operation K T)) : Book K T :=
  ops.foldl applyOp book

theorem anchor_postOps_eq_foldl [DecidableEq T]
    (book : Book K T) (ops : List (Operation K T)) :
    postOps book ops = ops.foldl applyOp book := rfl

@[simp] theorem sanity_postOps_nil [DecidableEq T] (book : Book K T) :
    postOps book [] = book := rfl

/-- Reachability under finite operation streams. -/
def Reachable [DecidableEq T]
    (initial target : Book K T) : Prop :=
  ∃ ops : List (Operation K T), postOps initial ops = target

theorem anchor_Reachable_exists_fold [DecidableEq T]
    (initial target : Book K T) :
    Reachable initial target ↔
      ∃ ops : List (Operation K T), ops.foldl applyOp initial = target := by
  rfl

theorem witness_Reachable_nonvacuous [DecidableEq T]
    (initial : Book K T) :
    ∃ target : Book K T, Reachable initial target := by
  exact ⟨initial, ⟨[], rfl⟩⟩

/-! ## Solver work items over the v3 substrate -/

section  -- [family-lemma-library] banked rungs (re-open env namespaces + section variables)
open LimitOrderBookV3
open Side
variable {K T : Type*} [Zero K] [LinearOrder K] [LT T]

-- [family-lemma-library] banked: bidPrice_le_bestBid
private lemma bidPrice_le_bestBid {K T : Type*} [Zero K] [LinearOrder K] [LT T]
    {book : Book K T} {price best : K}
    (hmem : price ∈ bidPrices book) (hbest : bestBid book = some best) :
    price ≤ best := by
  have hmax : (bidPrices book).max? = some best := by
    simpa [bestBid] using hbest
  exact (List.max?_eq_some_iff.mp hmax).2 price hmem

-- [family-lemma-library] banked: bestAsk_le_of_mem_askPricesDual
private lemma bestAsk_le_of_mem_askPricesDual {K T : Type*} [Zero K] [LinearOrder K] [LT T]
    {book : Book K T} {priceDual : Kᵒᵈ} {best : K}
    (hmem : priceDual ∈ askPricesDual book) (hbest : bestAsk book = some best) :
    best ≤ OrderDual.ofDual priceDual := by
  rcases (Option.map_eq_some_iff.mp hbest) with ⟨bestDual, hmax, hbestDual⟩
  have hleDual : priceDual ≤ bestDual :=
    (List.max?_eq_some_iff.mp hmax).2 priceDual hmem
  have hleBase : OrderDual.ofDual bestDual ≤ OrderDual.ofDual priceDual := by
    simpa [OrderDual.ofDual_le_ofDual] using hleDual
  simpa [hbestDual] using hleBase

-- [family-lemma-library] banked: iso_lemma1
theorem iso_lemma1 : ∀ {K T : Type*} [Zero K] [LinearOrder K] [LT T]
    {book : Book K T} {incoming : Order K T},
    ((incoming.side = Side.bid → ∀ ask, bestAsk book = some ask → incoming.price < ask) ∧
      (incoming.side = Side.ask → ∀ bid, bestBid book = some bid → bid < incoming.price)) →
    Uncrossed book → Uncrossed (restOrder book incoming) := by
  intro K T _ _ _ book incoming hsafe hbook bid ask hbid hask
  cases hside : incoming.side with
  | bid =>
      have hask_old : bestAsk book = some ask := by
        simpa [restOrder, hside] using hask
      have hbid_rest : (incoming.price :: bidPrices book).max? = some bid := by
        simpa [restOrder, hside, bestBid, bidPrices] using hbid
      have hbid_mem : bid ∈ incoming.price :: bidPrices book :=
        List.max?_mem hbid_rest
      rcases (List.mem_cons.mp hbid_mem) with hnew | hold
      · subst bid
        exact hsafe.1 hside ask hask_old
      · cases hbest_old : bestBid book with
        | none =>
            have hempty : bidPrices book = [] := by
              exact List.max?_eq_none_iff.mp (by simpa [bestBid] using hbest_old)
            simpa [hempty] using hold
        | some oldBid =>
            have hle : bid ≤ oldBid :=
              bidPrice_le_bestBid (book := book) hold hbest_old
            exact lt_of_le_of_lt hle (hbook oldBid ask hbest_old hask_old)
  | ask =>
      have hbid_old : bestBid book = some bid := by
        simpa [restOrder, hside] using hbid
      rcases (Option.map_eq_some_iff.mp hask) with ⟨askDual, haskDual, haskEq⟩
      have haskDual_rest :
          (OrderDual.toDual incoming.price :: askPricesDual book).max? = some askDual := by
        simpa [restOrder, hside, bestAsk, askPricesDual] using haskDual
      have hask_mem : askDual ∈ OrderDual.toDual incoming.price :: askPricesDual book :=
        List.max?_mem haskDual_rest
      rcases (List.mem_cons.mp hask_mem) with hnew | hold
      · subst askDual
        have hprice : incoming.price = ask := by
          simpa using haskEq
        simpa [hprice] using hsafe.2 hside bid hbid_old
      · cases hbest_old : bestAsk book with
        | none =>
            have hmax_none : (askPricesDual book).max? = none := by
              simpa [bestAsk] using hbest_old
            have hemptyDual : askPricesDual book = [] :=
              List.max?_eq_none_iff.mp hmax_none
            have hfalse : False := by
              simpa [hemptyDual] using hold
            exact False.elim hfalse
        | some oldAsk =>
            have hle : oldAsk ≤ OrderDual.ofDual askDual :=
              bestAsk_le_of_mem_askPricesDual (book := book) hold hbest_old
            have hlt : bid < oldAsk :=
              hbook bid oldAsk hbid_old hbest_old
            simpa [haskEq] using lt_of_lt_of_le hlt hle

end

private lemma restOrder_preserves_uncrossed_of_safe
    {book : Book K T} {incoming : Order K T}
    (hsafe :
      (incoming.side = Side.bid → ∀ ask, bestAsk book = some ask → incoming.price < ask) ∧
        (incoming.side = Side.ask → ∀ bid, bestBid book = some bid → bid < incoming.price))
    (hbook : Uncrossed book) :
    Uncrossed (restOrder book incoming) := by
  intro bid ask hbid hask
  cases hside : incoming.side with
  | bid =>
      have hask_old : bestAsk book = some ask := by
        simpa [restOrder, hside] using hask
      have hbid_rest : (incoming.price :: bidPrices book).max? = some bid := by
        simpa [restOrder, hside, bestBid, bidPrices] using hbid
      have hbid_mem : bid ∈ incoming.price :: bidPrices book :=
        List.max?_mem hbid_rest
      rcases (List.mem_cons.mp hbid_mem) with hnew | hold
      · subst bid
        exact hsafe.1 hside ask hask_old
      · cases hbest_old : bestBid book with
        | none =>
            have hempty : bidPrices book = [] := by
              exact List.max?_eq_none_iff.mp (by simpa [bestBid] using hbest_old)
            simpa [hempty] using hold
        | some oldBid =>
            have hle : bid ≤ oldBid :=
              bidPrice_le_bestBid (book := book) hold hbest_old
            exact lt_of_le_of_lt hle (hbook oldBid ask hbest_old hask_old)
  | ask =>
      have hbid_old : bestBid book = some bid := by
        simpa [restOrder, hside] using hbid
      rcases (Option.map_eq_some_iff.mp hask) with ⟨askDual, haskDual, haskEq⟩
      have haskDual_rest :
          (OrderDual.toDual incoming.price :: askPricesDual book).max? = some askDual := by
        simpa [restOrder, hside, bestAsk, askPricesDual] using haskDual
      have hask_mem : askDual ∈ OrderDual.toDual incoming.price :: askPricesDual book :=
        List.max?_mem haskDual_rest
      rcases (List.mem_cons.mp hask_mem) with hnew | hold
      · subst askDual
        have hprice : incoming.price = ask := by
          simpa using haskEq
        simpa [hprice] using hsafe.2 hside bid hbid_old
      · cases hbest_old : bestAsk book with
        | none =>
            have hmax_none : (askPricesDual book).max? = none := by
              simpa [bestAsk] using hbest_old
            have hemptyDual : askPricesDual book = [] :=
              List.max?_eq_none_iff.mp hmax_none
            have hfalse : False := by
              simpa [hemptyDual] using hold
            exact False.elim hfalse
        | some oldAsk =>
            have hle : oldAsk ≤ OrderDual.ofDual askDual :=
              bestAsk_le_of_mem_askPricesDual (book := book) hold hbest_old
            have hlt : bid < oldAsk :=
              hbook bid oldAsk hbid_old hbest_old
            simpa [haskEq] using lt_of_lt_of_le hlt hle

private lemma not_marketable_safe
    {book : Book K T} {incoming : Order K T}
    (hnot : ¬ Marketable incoming book) :
    (incoming.side = Side.bid → ∀ ask, bestAsk book = some ask → incoming.price < ask) ∧
      (incoming.side = Side.ask → ∀ bid, bestBid book = some bid → bid < incoming.price) := by
  constructor
  · intro hside ask hask
    have hnot_le : ¬ ask ≤ incoming.price := by
      intro hle
      exact hnot (by simpa [Marketable, hside, hask] using hle)
    exact lt_of_not_ge hnot_le
  · intro hside bid hbid
    have hnot_le : ¬ incoming.price ≤ bid := by
      intro hle
      exact hnot (by simpa [Marketable, hside, hbid] using hle)
    exact lt_of_not_ge hnot_le

theorem restOrder_preserves_uncrossed_of_not_marketable : ∀ {book : Book K T} {incoming : Order K T}
    (hbook : Uncrossed book) (hnot : ¬ Marketable incoming book), Uncrossed (restOrder book incoming) := by
  intro book incoming hbook hnot
  exact restOrder_preserves_uncrossed_of_safe (not_marketable_safe hnot) hbook
theorem matchInto_preserves_uncrossed
    {book : Book K T} {incoming : Order K T}
    (hbook : Uncrossed book) :
    Uncrossed (matchInto book incoming) := by
  by_cases hmarket : Marketable incoming book
  · simpa [matchInto, hmarket] using hbook
  · simpa [matchInto, hmarket] using
      restOrder_preserves_uncrossed_of_not_marketable hbook hmarket

theorem applyOp_preserves_uncrossed [DecidableEq T]
    {book : Book K T} {op : Operation K T}
    (hbook : Uncrossed book) :
    Uncrossed (applyOp book op) := by
  cases op with
  | limit incoming =>
      exact matchInto_preserves_uncrossed hbook
  | market side qty hqty =>
      simpa [applyOp] using hbook
  | cancel side arrival =>
      exact cancelOrder_preserves_uncrossed hbook

theorem postOps_preserves_uncrossed [DecidableEq T]
    {book : Book K T} {ops : List (Operation K T)}
    (hbook : Uncrossed book) :
    Uncrossed (postOps book ops) := by
  unfold postOps
  induction ops generalizing book with
  | nil =>
      exact hbook
  | cons op ops ih =>
      simp only [List.foldl_cons]
      exact ih (book := applyOp book op) (applyOp_preserves_uncrossed hbook)

theorem trace_scanl_uncrossed [DecidableEq T]
    (initial : Book K T) (hinitial : Uncrossed initial)
    (ops : List (Operation K T)) :
    ∀ state ∈ List.scanl applyOp initial ops, Uncrossed state := by
  induction ops generalizing initial with
  | nil =>
      intro state hstate
      simp at hstate
      subst state
      exact hinitial
  | cons op ops ih =>
      intro state hstate
      simp [List.scanl] at hstate
      rcases hstate with hstate | hstate
      · subst state
        exact hinitial
      · exact ih (applyOp initial op) (applyOp_preserves_uncrossed hinitial) state hstate

end Operations

end LimitOrderBookV3

namespace LimitOrderBookV3

/-! ## Supplemental denotation anchors

These anchors are appended so every selected primitive `def` has an
`anchor_`-named theorem tying it to its intended Mathlib/list reduction.
-/

namespace Side

theorem anchor_opposite_bid : opposite bid = ask := rfl

theorem anchor_opposite_ask : opposite ask = bid := rfl

end Side

section SupplementalAnchors

variable {K T : Type*} [Zero K] [LinearOrder K]

theorem anchor_emptyBook_fields :
    (emptyBook : Book K T).bids = [] ∧ (emptyBook : Book K T).asks = [] := by
  constructor <;> rfl

theorem anchor_ordersOnSide_characterization (book : Book K T) (side : Side) :
    ordersOnSide book side =
      match side with
      | Side.bid => book.bids
      | Side.ask => book.asks := by
  cases side <;> rfl

end SupplementalAnchors

end LimitOrderBookV3
