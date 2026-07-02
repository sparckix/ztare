/-
LeanMill campaign provenance — constantProductAMM_temporal_invariant_and_no_roundTrip_profit
The theorem(s) below are the VERBATIM machine-checked closure. This header is GENERATED from run
telemetry (run_tag=amm_cpmm_v2) by promote_campaign_artifact.py — not hand-authored.

  outcome     : closed · faithful · axioms propext, Classical.choice, Quot.sound
  domain      : DeFi market-microstructure — constant-product AMM temporal + no-arbitrage invariants
  time        : wall 18457.1s launch→close = formalize 8923.27s (theory+statement+firewall) + prove 9533.86s (proof search) · prove p50 10150.1s p95 17480.1s
  compute     : cost-to-closure 5615.67s mean · 11452.4s total
  yield       : 40/104 attempts closed (58 failed)
  phases      : 5990.5s leaf.dispatch · 1748.8s pool · 623.6s formalize · 254.1s govern.mnc · 137.3s native
  reuse       : cited 0 banked rung(s)
  moves       : native_hammer×43 · claude_warm×36 · proposer_pool×24 · conjecture_lemma×1
  milestone   : campaign family 'amm_cpmm' — 4 run(s) · REAL elapsed (launch→last) 31362.9s (~523 min) = formalize 2290.3s + prove/other · active-solve 18444.6s · 64 closures [launch→last is the honest wall]
     - amm_cpmm_v2: 40/104 closed · elapsed 18574.3s (~309.6 min)
     - amm_cpmm_v3: 15/37 closed · elapsed 6207.89s (~103.5 min)
     - amm_cpmm_v4: 9/28 closed · elapsed 5421.65s (~90.4 min)
     - amm_cpmm_v5: 0/1 closed · elapsed 1159.06s (~19.3 min)
-/
import Mathlib

/-!
# Constant-product AMM substrate

Definition trial notes for this dispatch:

* Pool candidate A: use a raw pair `NNReal × NNReal`. Rejected because named
  reserves make theorem statements and anchors clearer.
* Pool candidate B: bundle named `reserveX` and `reserveY` fields. Selected:
  model-case well-formedness and product anchors are immediate.
* Fee candidate A: pass `gamma : NNReal` with side hypotheses everywhere.
  Rejected because every invariant repeats the fee bounds.
* Fee candidate B: bundle the fee value with `0 < gamma` and `gamma ≤ 1`.
  Selected: the bounds are projections and the feeless model case proves.
* Swap candidate A: define output first and subtract it from reserves. Rejected
  for the transition because `NNReal` subtraction is truncated.
* Swap candidate B: use the closed forms
  `x' = x + dx`, `y' = x*y/(x + gamma*dx)` and the symmetric formula.
  Selected: no reserve subtraction is needed in the state transition.
* Temporal candidate A: only assert final product monotonicity. Rejected as too
  weak for the liveness target.
* Temporal candidate B: combine final product monotonicity with a recursive
  "every visited state is well-formed" predicate. Selected: it is inductive over
  `List Trade` and rules out vacuous zero-pool interpretations.
-/


/-- Two-token reserve state for a constant-product AMM. -/
structure ConstantProductPool where
  reserveX : NNReal
  reserveY : NNReal

/-- A pool is live exactly when both reserves are strictly positive. -/
def PoolWellFormed (p : ConstantProductPool) : Prop :=
  0 < p.reserveX ∧ 0 < p.reserveY

/-- The constant-product quantity `k = x*y`. -/
def poolProduct (p : ConstantProductPool) : NNReal :=
  p.reserveX * p.reserveY

/-- Fee factor: the fraction of input that trades against the curve. -/
structure FeeFactor where
  gamma : NNReal
  gamma_pos : 0 < gamma
  gamma_le_one : gamma ≤ 1

/-- A real fee, excluding the feeless boundary. -/
def FeeIsReal (fee : FeeFactor) : Prop :=
  fee.gamma < 1

/-- Swap direction. -/
inductive TradeDirection where
  | xToY
  | yToX
deriving DecidableEq, Repr

/-- A trade is a direction together with a nonnegative input amount. -/
structure Trade where
  direction : TradeDirection
  amount : NNReal

/-- Closed-form X-for-Y swap with input fee. -/
noncomputable def swapXToY (gamma : NNReal) (p : ConstantProductPool) (dx : NNReal) :
    ConstantProductPool where
  reserveX := p.reserveX + dx
  reserveY := p.reserveX * p.reserveY / (p.reserveX + gamma * dx)

/-- Closed-form Y-for-X swap with input fee. -/
noncomputable def swapYToX (gamma : NNReal) (p : ConstantProductPool) (dy : NNReal) :
    ConstantProductPool where
  reserveX := p.reserveX * p.reserveY / (p.reserveY + gamma * dy)
  reserveY := p.reserveY + dy

/-- Apply one trade in either direction. -/
noncomputable def applyTrade (gamma : NNReal) (p : ConstantProductPool) (trade : Trade) :
    ConstantProductPool :=
  match trade.direction with
  | TradeDirection.xToY => swapXToY gamma p trade.amount
  | TradeDirection.yToX => swapYToX gamma p trade.amount

/-- Execute a finite adversarial sequence of trades. -/
noncomputable def executeTrades (gamma : NNReal) (p : ConstantProductPool)
    (trades : List Trade) : ConstantProductPool :=
  trades.foldl (fun state trade => applyTrade gamma state trade) p

/-- Every visited state, including the initial and final states, is live. -/
noncomputable def TradesKeepWellFormed (gamma : NNReal) (p : ConstantProductPool) :
    List Trade → Prop
  | [] => PoolWellFormed p
  | trade :: trades =>
      PoolWellFormed p ∧ TradesKeepWellFormed gamma (applyTrade gamma p trade) trades

/-- Sequence-level invariant: the pool stays live throughout and product does
not decrease from the initial state to the final state. -/
noncomputable def TemporalInvariant (gamma : NNReal) (p : ConstantProductPool)
    (trades : List Trade) : Prop :=
  TradesKeepWellFormed gamma p trades ∧
    poolProduct p ≤ poolProduct (executeTrades gamma p trades)

/-- Product monotonicity between two pool states. -/
def ProductNondecreasing (p q : ConstantProductPool) : Prop :=
  poolProduct p ≤ poolProduct q

/-- Strict product growth between two pool states. -/
def ProductStrictlyIncreases (p q : ConstantProductPool) : Prop :=
  poolProduct p < poolProduct q

/-- Per-trade invariant predicate for one concrete input trade. -/
noncomputable def SingleTradeInvariant (fee : FeeFactor)
    (p : ConstantProductPool) (trade : Trade) : Prop :=
  PoolWellFormed p →
    PoolWellFormed (applyTrade fee.gamma p trade) ∧
      ProductNondecreasing p (applyTrade fee.gamma p trade)

/-- Strict per-trade invariant predicate under a real fee and positive input. -/
noncomputable def StrictSingleTradeInvariant (fee : FeeFactor)
    (p : ConstantProductPool) (trade : Trade) : Prop :=
  PoolWellFormed p → FeeIsReal fee → 0 < trade.amount →
    ProductStrictlyIncreases p (applyTrade fee.gamma p trade)

/-- Sequence invariant predicate parameterized by the bundled fee. -/
noncomputable def TradeSequenceInvariant (fee : FeeFactor)
    (p : ConstantProductPool) (trades : List Trade) : Prop :=
  PoolWellFormed p → TemporalInvariant fee.gamma p trades

/-- Output of an X-for-Y swap, measured as the decrease in Y reserve. -/
noncomputable def amountOutXToY (gamma : NNReal) (p : ConstantProductPool) (dx : NNReal) :
    NNReal :=
  p.reserveY - (swapXToY gamma p dx).reserveY

/-- Output of a Y-for-X swap, measured as the decrease in X reserve. -/
noncomputable def amountOutYToX (gamma : NNReal) (p : ConstantProductPool) (dy : NNReal) :
    NNReal :=
  p.reserveX - (swapYToX gamma p dy).reserveX

/-- X-denominated return from swapping X to Y and then immediately Y to X. -/
noncomputable def roundTripXReturn (gamma : NNReal) (p : ConstantProductPool) (dx : NNReal) :
    NNReal :=
  amountOutYToX gamma (swapXToY gamma p dx) (amountOutXToY gamma p dx)

/-- Y-denominated return from swapping Y to X and then immediately X to Y. -/
noncomputable def roundTripYReturn (gamma : NNReal) (p : ConstantProductPool) (dy : NNReal) :
    NNReal :=
  amountOutXToY gamma (swapYToX gamma p dy) (amountOutYToX gamma p dy)

/-- Anchor: well-formedness is exactly strict positivity of both reserves in
Mathlib's order on `NNReal`. -/
theorem anchor_PoolWellFormed_iff (p : ConstantProductPool) :
    PoolWellFormed p ↔ 0 < p.reserveX ∧ 0 < p.reserveY := by
  rfl

/-- Anchor: the pool product is Mathlib multiplication of the two reserves. -/
theorem anchor_poolProduct_eq_mul (p : ConstantProductPool) :
    poolProduct p = p.reserveX * p.reserveY := by
  rfl

/-- Anchor: a bundled fee factor is a positive `NNReal` value bounded above by
one. -/
theorem anchor_FeeFactor_bounds (fee : FeeFactor) :
    0 < fee.gamma ∧ fee.gamma ≤ 1 := by
  exact ⟨fee.gamma_pos, fee.gamma_le_one⟩

/-- Anchor: a real fee is exactly `gamma < 1`. -/
theorem anchor_FeeIsReal_iff (fee : FeeFactor) :
    FeeIsReal fee ↔ fee.gamma < 1 := by
  rfl

/-- Anchor: an X-to-Y trade carries its direction and input amount as fields. -/
theorem anchor_Trade_xToY (amount : NNReal) :
    (Trade.mk TradeDirection.xToY amount).direction = TradeDirection.xToY ∧
      (Trade.mk TradeDirection.xToY amount).amount = amount := by
  exact ⟨rfl, rfl⟩

/-- Anchor: a Y-to-X trade carries its direction and input amount as fields. -/
theorem anchor_Trade_yToX (amount : NNReal) :
    (Trade.mk TradeDirection.yToX amount).direction = TradeDirection.yToX ∧
      (Trade.mk TradeDirection.yToX amount).amount = amount := by
  exact ⟨rfl, rfl⟩

/-- Anchor: the X reserve after an X-to-Y swap is old X plus input. -/
theorem anchor_swapXToY_reserveX (gamma : NNReal) (p : ConstantProductPool)
    (dx : NNReal) :
    (swapXToY gamma p dx).reserveX = p.reserveX + dx := by
  rfl

/-- Anchor: the Y reserve after an X-to-Y swap is the closed-form curve value. -/
theorem anchor_swapXToY_reserveY (gamma : NNReal) (p : ConstantProductPool)
    (dx : NNReal) :
    (swapXToY gamma p dx).reserveY =
      p.reserveX * p.reserveY / (p.reserveX + gamma * dx) := by
  rfl

/-- Anchor: the X reserve after a Y-to-X swap is the symmetric closed-form
curve value. -/
theorem anchor_swapYToX_reserveX (gamma : NNReal) (p : ConstantProductPool)
    (dy : NNReal) :
    (swapYToX gamma p dy).reserveX =
      p.reserveX * p.reserveY / (p.reserveY + gamma * dy) := by
  rfl

/-- Anchor: the Y reserve after a Y-to-X swap is old Y plus input. -/
theorem anchor_swapYToX_reserveY (gamma : NNReal) (p : ConstantProductPool)
    (dy : NNReal) :
    (swapYToX gamma p dy).reserveY = p.reserveY + dy := by
  rfl

/-- Anchor: applying an X-to-Y trade selects the X-to-Y swap formula. -/
theorem anchor_applyTrade_xToY (gamma : NNReal) (p : ConstantProductPool)
    (dx : NNReal) :
    applyTrade gamma p ⟨TradeDirection.xToY, dx⟩ = swapXToY gamma p dx := by
  rfl

/-- Anchor: applying a Y-to-X trade selects the Y-to-X swap formula. -/
theorem anchor_applyTrade_yToX (gamma : NNReal) (p : ConstantProductPool)
    (dy : NNReal) :
    applyTrade gamma p ⟨TradeDirection.yToX, dy⟩ = swapYToX gamma p dy := by
  rfl

/-- Anchor: executing no trades leaves the pool unchanged. -/
theorem anchor_executeTrades_nil (gamma : NNReal) (p : ConstantProductPool) :
    executeTrades gamma p [] = p := by
  rfl

/-- Anchor: executing a nonempty list first applies the head trade. -/
theorem anchor_executeTrades_cons (gamma : NNReal) (p : ConstantProductPool)
    (trade : Trade) (trades : List Trade) :
    executeTrades gamma p (trade :: trades) =
      executeTrades gamma (applyTrade gamma p trade) trades := by
  rfl

/-- Anchor: no-trade path well-formedness is just well-formedness of the
initial pool. -/
theorem anchor_TradesKeepWellFormed_nil (gamma : NNReal)
    (p : ConstantProductPool) :
    TradesKeepWellFormed gamma p [] ↔ PoolWellFormed p := by
  rfl

/-- Anchor: path well-formedness over a nonempty list checks the current state
and then recurses. -/
theorem anchor_TradesKeepWellFormed_cons (gamma : NNReal)
    (p : ConstantProductPool) (trade : Trade) (trades : List Trade) :
    TradesKeepWellFormed gamma p (trade :: trades) ↔
      PoolWellFormed p ∧
        TradesKeepWellFormed gamma (applyTrade gamma p trade) trades := by
  rfl

/-- Anchor: the temporal invariant is path liveness plus nondecreasing
initial-to-final product. -/
theorem anchor_TemporalInvariant_iff (gamma : NNReal)
    (p : ConstantProductPool) (trades : List Trade) :
    TemporalInvariant gamma p trades ↔
      TradesKeepWellFormed gamma p trades ∧
        poolProduct p ≤ poolProduct (executeTrades gamma p trades) := by
  rfl

/-- Anchor: product nondecrease is the Mathlib order relation on products. -/
theorem anchor_ProductNondecreasing_iff (p q : ConstantProductPool) :
    ProductNondecreasing p q ↔ poolProduct p ≤ poolProduct q := by
  rfl

/-- Anchor: strict product growth is the Mathlib strict order relation on
products. -/
theorem anchor_ProductStrictlyIncreases_iff (p q : ConstantProductPool) :
    ProductStrictlyIncreases p q ↔ poolProduct p < poolProduct q := by
  rfl

/-- Anchor: the single-trade invariant is well-formedness preservation plus
product nondecrease for the selected transition. -/
theorem anchor_SingleTradeInvariant_iff (fee : FeeFactor)
    (p : ConstantProductPool) (trade : Trade) :
    SingleTradeInvariant fee p trade ↔
      (PoolWellFormed p →
        PoolWellFormed (applyTrade fee.gamma p trade) ∧
          ProductNondecreasing p (applyTrade fee.gamma p trade)) := by
  rfl

/-- Anchor: the strict single-trade invariant is strict product growth under a
real fee and positive input. -/
theorem anchor_StrictSingleTradeInvariant_iff (fee : FeeFactor)
    (p : ConstantProductPool) (trade : Trade) :
    StrictSingleTradeInvariant fee p trade ↔
      (PoolWellFormed p → FeeIsReal fee → 0 < trade.amount →
        ProductStrictlyIncreases p (applyTrade fee.gamma p trade)) := by
  rfl

/-- Anchor: the fee-bundled sequence invariant is the temporal invariant under
a well-formed initial pool. -/
theorem anchor_TradeSequenceInvariant_iff (fee : FeeFactor)
    (p : ConstantProductPool) (trades : List Trade) :
    TradeSequenceInvariant fee p trades ↔
      (PoolWellFormed p → TemporalInvariant fee.gamma p trades) := by
  rfl

/-- Anchor: X-to-Y output is the truncated reserve decrease in Y. -/
theorem anchor_amountOutXToY_eq_tsub (gamma : NNReal)
    (p : ConstantProductPool) (dx : NNReal) :
    amountOutXToY gamma p dx =
      p.reserveY - (swapXToY gamma p dx).reserveY := by
  rfl

/-- Anchor: Y-to-X output is the truncated reserve decrease in X. -/
theorem anchor_amountOutYToX_eq_tsub (gamma : NNReal)
    (p : ConstantProductPool) (dy : NNReal) :
    amountOutYToX gamma p dy =
      p.reserveX - (swapYToX gamma p dy).reserveX := by
  rfl

/-- Anchor: the X round trip feeds the first leg's Y output into the reverse
Y-to-X swap. -/
theorem anchor_roundTripXReturn_eq (gamma : NNReal)
    (p : ConstantProductPool) (dx : NNReal) :
    roundTripXReturn gamma p dx =
      amountOutYToX gamma (swapXToY gamma p dx) (amountOutXToY gamma p dx) := by
  rfl

/-- Anchor: the Y round trip feeds the first leg's X output into the reverse
X-to-Y swap. -/
theorem anchor_roundTripYReturn_eq (gamma : NNReal)
    (p : ConstantProductPool) (dy : NNReal) :
    roundTripYReturn gamma p dy =
      amountOutXToY gamma (swapYToX gamma p dy) (amountOutYToX gamma p dy) := by
  rfl

/-- Witness: the unit pool is a nonvacuous well-formed state. -/
theorem witness_PoolWellFormed_unit :
    PoolWellFormed ⟨1, 1⟩ := by
  norm_num [PoolWellFormed]

/-- Witness: the feeless boundary `gamma = 1` is an admissible fee factor. -/
def feelessFee : FeeFactor where
  gamma := 1
  gamma_pos := by norm_num
  gamma_le_one := by rfl

/-- Sanity: the feeless fee's value is exactly one. -/
theorem witness_feelessFee_gamma :
    feelessFee.gamma = 1 := by
  rfl

/-- Witness: the empty trade sequence has the temporal invariant for every
well-formed initial pool. -/
theorem witness_TemporalInvariant_nil (gamma : NNReal)
    (p : ConstantProductPool) (hp : PoolWellFormed p) :
    TemporalInvariant gamma p [] := by
  constructor
  · exact hp
  · rfl

/-- Witness: the empty trade sequence satisfies the fee-bundled sequence
invariant for every admissible fee. -/
theorem witness_TradeSequenceInvariant_nil (fee : FeeFactor)
    (p : ConstantProductPool) :
    TradeSequenceInvariant fee p [] := by
  intro hp
  exact witness_TemporalInvariant_nil fee.gamma p hp

/-- Solver work item: one X-to-Y swap preserves strict positivity of reserves. -/















theorem swapXToY_wellFormed : ∀ (fee : FeeFactor) (p : ConstantProductPool) (dx : NNReal)
    (hp : PoolWellFormed p), PoolWellFormed (swapXToY fee.gamma p dx) := by
  intro fee p dx hp
  rcases hp with ⟨hx, hy⟩
  constructor
  · change 0 < p.reserveX + dx
    exact lt_of_lt_of_le hx (le_add_of_nonneg_right (zero_le dx))
  · change 0 < p.reserveX * p.reserveY / (p.reserveX + fee.gamma * dx)
    exact div_pos (mul_pos hx hy)
      (lt_of_lt_of_le hx (le_add_of_nonneg_right (zero_le (fee.gamma * dx))))



-- [family-lemma-library] banked: swapYToX_wellFormed
theorem swapYToX_wellFormed : ∀ (fee : FeeFactor) (p : ConstantProductPool) (dy : NNReal)
    (hp : PoolWellFormed p), PoolWellFormed (swapYToX fee.gamma p dy) := by
  intro fee p dy hp
  rcases hp with ⟨hx, hy⟩
  constructor
  · change 0 < p.reserveX * p.reserveY / (p.reserveY + fee.gamma * dy)
    exact div_pos (mul_pos hx hy)
      (lt_of_lt_of_le hy (le_add_of_nonneg_right (zero_le (fee.gamma * dy))))
  · change 0 < p.reserveY + dy
    exact lt_of_lt_of_le hy (le_add_of_nonneg_right (zero_le dy))



-- [family-lemma-library] banked: swapXToY_product_mono
theorem swapXToY_product_mono : ∀ (fee : FeeFactor) (p : ConstantProductPool) (dx : NNReal)
    (hp : PoolWellFormed p), poolProduct p ≤ poolProduct (swapXToY fee.gamma p dx) := by
  intro fee p dx hp
  rcases hp with ⟨hx, _hy⟩
  dsimp [poolProduct, swapXToY]
  let d : NNReal := p.reserveX + fee.gamma * dx
  have hd_pos : 0 < d := by
    dsimp [d]
    exact lt_of_lt_of_le hx (le_add_of_nonneg_right (zero_le (fee.gamma * dx)))
  have hd_ne : d ≠ 0 := ne_of_gt hd_pos
  have hgamma_mul : fee.gamma * dx ≤ dx := by
    simpa using (mul_le_mul_right' fee.gamma_le_one dx)
  have hd_le : d ≤ p.reserveX + dx := by
    dsimp [d]
    simpa [add_comm] using add_le_add_left hgamma_mul p.reserveX
  calc
    p.reserveX * p.reserveY = d * (p.reserveX * p.reserveY / d) := by
      exact (mul_div_cancel₀ (p.reserveX * p.reserveY) hd_ne).symm
    _ ≤ (p.reserveX + dx) * (p.reserveX * p.reserveY / d) := by
      exact mul_le_mul_right' hd_le (p.reserveX * p.reserveY / d)



-- [family-lemma-library] banked: swapYToX_product_mono
theorem swapYToX_product_mono : ∀ (fee : FeeFactor) (p : ConstantProductPool) (dy : NNReal)
    (hp : PoolWellFormed p), poolProduct p ≤ poolProduct (swapYToX fee.gamma p dy) := by
  intro fee p dy hp
  rcases hp with ⟨_hx, hy⟩
  dsimp [poolProduct, swapYToX]
  let d : NNReal := p.reserveY + fee.gamma * dy
  have hd_pos : 0 < d := by
    dsimp [d]
    exact lt_of_lt_of_le hy (le_add_of_nonneg_right (zero_le (fee.gamma * dy)))
  have hd_ne : d ≠ 0 := ne_of_gt hd_pos
  have hgamma_mul : fee.gamma * dy ≤ dy := by
    simpa using (mul_le_mul_right' fee.gamma_le_one dy)
  have hd_le : d ≤ p.reserveY + dy := by
    dsimp [d]
    simpa [add_comm] using add_le_add_left hgamma_mul p.reserveY
  calc
    p.reserveX * p.reserveY = (p.reserveX * p.reserveY / d) * d := by
      simpa [mul_comm] using (mul_div_cancel₀ (p.reserveX * p.reserveY) hd_ne).symm
    _ ≤ (p.reserveX * p.reserveY / d) * (p.reserveY + dy) := by
      exact mul_le_mul_left' hd_le (p.reserveX * p.reserveY / d)



-- [family-lemma-library] banked: swapXToY_product_strict_of_real_fee
theorem swapXToY_product_strict_of_real_fee : ∀ (fee : FeeFactor) (p : ConstantProductPool)
    (dx : NNReal) (hp : PoolWellFormed p) (hfee : FeeIsReal fee) (hdx : 0 < dx), poolProduct p < poolProduct (swapXToY fee.gamma p dx) := by
  intro fee p dx hp hfee hdx
  rcases hp with ⟨hx, hy⟩
  dsimp [poolProduct, swapXToY]
  let d : NNReal := p.reserveX + fee.gamma * dx
  have hd_pos : 0 < d := by
    dsimp [d]
    exact lt_of_lt_of_le hx (le_add_of_nonneg_right (zero_le (fee.gamma * dx)))
  have hd_ne : d ≠ 0 := ne_of_gt hd_pos
  have hgamma_mul : fee.gamma * dx < dx := by
    simpa using (mul_lt_mul_of_pos_right hfee hdx)
  have hd_lt : d < p.reserveX + dx := by
    dsimp [d]
    simpa [add_comm] using add_lt_add_left hgamma_mul p.reserveX
  have hquot_pos : 0 < p.reserveX * p.reserveY / d := by
    exact div_pos (mul_pos hx hy) hd_pos
  calc
    p.reserveX * p.reserveY = d * (p.reserveX * p.reserveY / d) := by
      exact (mul_div_cancel₀ (p.reserveX * p.reserveY) hd_ne).symm
    _ < (p.reserveX + dx) * (p.reserveX * p.reserveY / d) := by
      exact mul_lt_mul_of_pos_right hd_lt hquot_pos



-- [family-lemma-library] banked: swapYToX_product_strict_of_real_fee
theorem swapYToX_product_strict_of_real_fee : ∀ (fee : FeeFactor) (p : ConstantProductPool)
    (dy : NNReal) (hp : PoolWellFormed p) (hfee : FeeIsReal fee) (hdy : 0 < dy), poolProduct p < poolProduct (swapYToX fee.gamma p dy) := by
  intro fee p dy hp hfee hdy
  rcases hp with ⟨hx, hy⟩
  dsimp [poolProduct, swapYToX]
  let d : NNReal := p.reserveY + fee.gamma * dy
  have hd_pos : 0 < d := by
    dsimp [d]
    exact lt_of_lt_of_le hy (le_add_of_nonneg_right (zero_le (fee.gamma * dy)))
  have hd_ne : d ≠ 0 := ne_of_gt hd_pos
  have hgamma_mul : fee.gamma * dy < dy := by
    simpa using (mul_lt_mul_of_pos_right hfee hdy)
  have hd_lt : d < p.reserveY + dy := by
    dsimp [d]
    simpa [add_comm] using add_lt_add_left hgamma_mul p.reserveY
  have hquot_pos : 0 < p.reserveX * p.reserveY / d := by
    exact div_pos (mul_pos hx hy) hd_pos
  calc
    p.reserveX * p.reserveY = (p.reserveX * p.reserveY / d) * d := by
      simpa [mul_comm] using (mul_div_cancel₀ (p.reserveX * p.reserveY) hd_ne).symm
    _ < (p.reserveX * p.reserveY / d) * (p.reserveY + dy) := by
      exact mul_lt_mul_of_pos_left hd_lt hquot_pos



-- [family-lemma-library] banked: singleTradeInvariant
theorem singleTradeInvariant : ∀ (fee : FeeFactor) (p : ConstantProductPool) (trade : Trade), SingleTradeInvariant fee p trade := by
  intro fee p trade hp
  rcases trade with ⟨direction, amount⟩
  cases direction
  · constructor
    · exact swapXToY_wellFormed fee p amount hp
    · exact swapXToY_product_mono fee p amount hp
  · constructor
    · exact swapYToX_wellFormed fee p amount hp
    · exact swapYToX_product_mono fee p amount hp



-- [family-lemma-library] banked: strictSingleTradeInvariant
theorem strictSingleTradeInvariant : ∀ (fee : FeeFactor) (p : ConstantProductPool) (trade : Trade), StrictSingleTradeInvariant fee p trade := by
  intro fee p trade hp hfee hamount
  rcases trade with ⟨direction, amount⟩
  cases direction
  · exact swapXToY_product_strict_of_real_fee fee p amount hp hfee hamount
  · exact swapYToX_product_strict_of_real_fee fee p amount hp hfee hamount



-- [family-lemma-library] banked: applyTrade_keep_wellFormed
theorem applyTrade_keep_wellFormed (fee : FeeFactor) (p : ConstantProductPool)
    (trade : Trade) (hp : PoolWellFormed p) :
    PoolWellFormed (applyTrade fee.gamma p trade) := by
  rcases hp with ⟨hx, hy⟩
  rcases trade with ⟨direction, amount⟩
  cases direction
  · constructor
    · change 0 < p.reserveX + amount
      exact lt_of_lt_of_le hx (le_add_of_nonneg_right (zero_le amount))
    · change 0 < p.reserveX * p.reserveY / (p.reserveX + fee.gamma * amount)
      exact div_pos (mul_pos hx hy)
        (lt_of_lt_of_le hx (le_add_of_nonneg_right (zero_le (fee.gamma * amount))))
  · constructor
    · change 0 < p.reserveX * p.reserveY / (p.reserveY + fee.gamma * amount)
      exact div_pos (mul_pos hx hy)
        (lt_of_lt_of_le hy (le_add_of_nonneg_right (zero_le (fee.gamma * amount))))
    · change 0 < p.reserveY + amount
      exact lt_of_lt_of_le hy (le_add_of_nonneg_right (zero_le amount))

-- [family-lemma-library] banked: executeTrades_keep_wellFormed
theorem executeTrades_keep_wellFormed : ∀ (fee : FeeFactor) (p : ConstantProductPool)
    (trades : List Trade) (hp : PoolWellFormed p), TradesKeepWellFormed fee.gamma p trades := by
  intro fee p trades
  induction trades generalizing p with
  | nil =>
      intro hp
      exact hp
  | cons trade trades ih =>
      intro hp
      constructor
      · exact hp
      · exact ih (applyTrade fee.gamma p trade)
          (applyTrade_keep_wellFormed fee p trade hp)



-- [family-lemma-library] banked: swapXToY_product_mono_aux
theorem swapXToY_product_mono_aux (fee : FeeFactor) (p : ConstantProductPool)
    (dx : NNReal) (hp : PoolWellFormed p) :
    poolProduct p ≤ poolProduct (swapXToY fee.gamma p dx) := by
  rcases hp with ⟨hx, _hy⟩
  dsimp [poolProduct, swapXToY]
  let d : NNReal := p.reserveX + fee.gamma * dx
  have hd_pos : 0 < d := by
    dsimp [d]
    exact lt_of_lt_of_le hx (le_add_of_nonneg_right (zero_le (fee.gamma * dx)))
  have hd_ne : d ≠ 0 := ne_of_gt hd_pos
  have hgamma_mul : fee.gamma * dx ≤ dx := by
    simpa using (mul_le_mul_right' fee.gamma_le_one dx)
  have hd_le : d ≤ p.reserveX + dx := by
    dsimp [d]
    simpa [add_comm] using add_le_add_left hgamma_mul p.reserveX
  calc
    p.reserveX * p.reserveY = d * (p.reserveX * p.reserveY / d) := by
      exact (mul_div_cancel₀ (p.reserveX * p.reserveY) hd_ne).symm
    _ ≤ (p.reserveX + dx) * (p.reserveX * p.reserveY / d) := by
      exact mul_le_mul_right' hd_le (p.reserveX * p.reserveY / d)

-- [family-lemma-library] banked: swapYToX_product_mono_aux
theorem swapYToX_product_mono_aux (fee : FeeFactor) (p : ConstantProductPool)
    (dy : NNReal) (hp : PoolWellFormed p) :
    poolProduct p ≤ poolProduct (swapYToX fee.gamma p dy) := by
  rcases hp with ⟨_hx, hy⟩
  dsimp [poolProduct, swapYToX]
  let d : NNReal := p.reserveY + fee.gamma * dy
  have hd_pos : 0 < d := by
    dsimp [d]
    exact lt_of_lt_of_le hy (le_add_of_nonneg_right (zero_le (fee.gamma * dy)))
  have hd_ne : d ≠ 0 := ne_of_gt hd_pos
  have hgamma_mul : fee.gamma * dy ≤ dy := by
    simpa using (mul_le_mul_right' fee.gamma_le_one dy)
  have hd_le : d ≤ p.reserveY + dy := by
    dsimp [d]
    simpa [add_comm] using add_le_add_left hgamma_mul p.reserveY
  calc
    p.reserveX * p.reserveY = (p.reserveX * p.reserveY / d) * d := by
      simpa [mul_comm] using (mul_div_cancel₀ (p.reserveX * p.reserveY) hd_ne).symm
    _ ≤ (p.reserveX * p.reserveY / d) * (p.reserveY + dy) := by
      exact mul_le_mul_left' hd_le (p.reserveX * p.reserveY / d)

-- [family-lemma-library] banked: applyTrade_product_mono_aux
theorem applyTrade_product_mono_aux (fee : FeeFactor) (p : ConstantProductPool)
    (trade : Trade) (hp : PoolWellFormed p) :
    poolProduct p ≤ poolProduct (applyTrade fee.gamma p trade) := by
  rcases trade with ⟨direction, amount⟩
  cases direction
  · exact swapXToY_product_mono_aux fee p amount hp
  · exact swapYToX_product_mono_aux fee p amount hp

-- [family-lemma-library] banked: applyTrade_keep_wellFormed_aux
theorem applyTrade_keep_wellFormed_aux (fee : FeeFactor) (p : ConstantProductPool)
    (trade : Trade) (hp : PoolWellFormed p) :
    PoolWellFormed (applyTrade fee.gamma p trade) := by
  rcases hp with ⟨hx, hy⟩
  rcases trade with ⟨direction, amount⟩
  cases direction
  · constructor
    · change 0 < p.reserveX + amount
      exact lt_of_lt_of_le hx (le_add_of_nonneg_right (zero_le amount))
    · change 0 < p.reserveX * p.reserveY / (p.reserveX + fee.gamma * amount)
      exact div_pos (mul_pos hx hy)
        (lt_of_lt_of_le hx (le_add_of_nonneg_right (zero_le (fee.gamma * amount))))
  · constructor
    · change 0 < p.reserveX * p.reserveY / (p.reserveY + fee.gamma * amount)
      exact div_pos (mul_pos hx hy)
        (lt_of_lt_of_le hy (le_add_of_nonneg_right (zero_le (fee.gamma * amount))))
    · change 0 < p.reserveY + amount
      exact lt_of_lt_of_le hy (le_add_of_nonneg_right (zero_le amount))

-- [family-lemma-library] banked: executeTrades_product_mono
theorem executeTrades_product_mono : ∀ (fee : FeeFactor) (p : ConstantProductPool)
    (trades : List Trade) (hp : PoolWellFormed p), poolProduct p ≤ poolProduct (executeTrades fee.gamma p trades) := by
  intro fee p trades
  induction trades generalizing p with
  | nil =>
      intro hp
      simp [executeTrades]
  | cons trade trades ih =>
      intro hp
      have hstep : poolProduct p ≤ poolProduct (applyTrade fee.gamma p trade) :=
        applyTrade_product_mono_aux fee p trade hp
      have htail :
          poolProduct (applyTrade fee.gamma p trade) ≤
            poolProduct (executeTrades fee.gamma (applyTrade fee.gamma p trade) trades) :=
        ih (applyTrade fee.gamma p trade) (applyTrade_keep_wellFormed_aux fee p trade hp)
      exact le_trans hstep htail



-- [family-lemma-library] banked: executeTrades_keep_wellFormed_aux
theorem executeTrades_keep_wellFormed_aux : ∀ (fee : FeeFactor) (p : ConstantProductPool)
    (trades : List Trade) (hp : PoolWellFormed p), TradesKeepWellFormed fee.gamma p trades := by
  intro fee p trades
  induction trades generalizing p with
  | nil =>
      intro hp
      exact hp
  | cons trade trades ih =>
      intro hp
      constructor
      · exact hp
      · exact ih (applyTrade fee.gamma p trade)
          (applyTrade_keep_wellFormed_aux fee p trade hp)

-- [family-lemma-library] banked: executeTrades_product_mono_aux
theorem executeTrades_product_mono_aux : ∀ (fee : FeeFactor) (p : ConstantProductPool)
    (trades : List Trade) (hp : PoolWellFormed p),
    poolProduct p ≤ poolProduct (executeTrades fee.gamma p trades) := by
  intro fee p trades
  induction trades generalizing p with
  | nil =>
      intro hp
      simp [executeTrades]
  | cons trade trades ih =>
      intro hp
      have hstep : poolProduct p ≤ poolProduct (applyTrade fee.gamma p trade) :=
        applyTrade_product_mono_aux fee p trade hp
      have htail :
          poolProduct (applyTrade fee.gamma p trade) ≤
            poolProduct (executeTrades fee.gamma (applyTrade fee.gamma p trade) trades) :=
        ih (applyTrade fee.gamma p trade) (applyTrade_keep_wellFormed_aux fee p trade hp)
      exact le_trans hstep htail

-- [family-lemma-library] banked: tradeSequenceInvariant
theorem tradeSequenceInvariant : ∀ (fee : FeeFactor) (p : ConstantProductPool)
    (trades : List Trade), TradeSequenceInvariant fee p trades := by
  intro fee p trades hp
  constructor
  · exact executeTrades_keep_wellFormed_aux fee p trades hp
  · exact executeTrades_product_mono_aux fee p trades hp



-- [family-lemma-library] banked: iso_roundTripX_product_ge_initial




theorem roundTripXReturn_le_input : ∀ (fee : FeeFactor)
    (p : ConstantProductPool) (dx : NNReal) (hp : PoolWellFormed p), roundTripXReturn fee.gamma p dx ≤ dx := by
  intro fee p dx hp
  let q : ConstantProductPool :=
    swapYToX fee.gamma (swapXToY fee.gamma p dx) (amountOutXToY fee.gamma p dx)
  have h_first_wf : PoolWellFormed (swapXToY fee.gamma p dx) := by
    rcases hp with ⟨hx, hy⟩
    constructor
    · change 0 < p.reserveX + dx
      exact lt_of_lt_of_le hx (le_add_of_nonneg_right (zero_le dx))
    · change 0 < p.reserveX * p.reserveY / (p.reserveX + fee.gamma * dx)
      exact div_pos (mul_pos hx hy)
        (lt_of_lt_of_le hx (le_add_of_nonneg_right (zero_le (fee.gamma * dx))))
  have h_swapX_prod :
      poolProduct p ≤ poolProduct (swapXToY fee.gamma p dx) := by
    rcases hp with ⟨hx, _hy⟩
    dsimp [poolProduct, swapXToY]
    let d : NNReal := p.reserveX + fee.gamma * dx
    have hd_pos : 0 < d := by
      dsimp [d]
      exact lt_of_lt_of_le hx (le_add_of_nonneg_right (zero_le (fee.gamma * dx)))
    have hd_ne : d ≠ 0 := ne_of_gt hd_pos
    have hgamma_mul : fee.gamma * dx ≤ dx := by
      simpa using (mul_le_mul_right' fee.gamma_le_one dx)
    have hd_le : d ≤ p.reserveX + dx := by
      dsimp [d]
      simpa [add_comm] using add_le_add_left hgamma_mul p.reserveX
    calc
      p.reserveX * p.reserveY = d * (p.reserveX * p.reserveY / d) := by
        exact (mul_div_cancel₀ (p.reserveX * p.reserveY) hd_ne).symm
      _ ≤ (p.reserveX + dx) * (p.reserveX * p.reserveY / d) := by
        exact mul_le_mul_right' hd_le (p.reserveX * p.reserveY / d)
  have h_swapY_prod :
      poolProduct (swapXToY fee.gamma p dx) ≤ poolProduct q := by
    rcases h_first_wf with ⟨_hx, hy⟩
    dsimp [q, poolProduct, swapYToX]
    let dy : NNReal := amountOutXToY fee.gamma p dx
    let d : NNReal := (swapXToY fee.gamma p dx).reserveY + fee.gamma * dy
    have hd_pos : 0 < d := by
      dsimp [d]
      exact lt_of_lt_of_le hy (le_add_of_nonneg_right (zero_le (fee.gamma * dy)))
    have hd_ne : d ≠ 0 := ne_of_gt hd_pos
    have hgamma_mul : fee.gamma * dy ≤ dy := by
      simpa using (mul_le_mul_right' fee.gamma_le_one dy)
    have hd_le : d ≤ (swapXToY fee.gamma p dx).reserveY + dy := by
      dsimp [d]
      simpa [add_comm] using add_le_add_left hgamma_mul (swapXToY fee.gamma p dx).reserveY
    calc
      (swapXToY fee.gamma p dx).reserveX * (swapXToY fee.gamma p dx).reserveY =
          ((swapXToY fee.gamma p dx).reserveX * (swapXToY fee.gamma p dx).reserveY / d) * d := by
        simpa [mul_comm] using
          (mul_div_cancel₀
            ((swapXToY fee.gamma p dx).reserveX * (swapXToY fee.gamma p dx).reserveY)
            hd_ne).symm
      _ ≤ ((swapXToY fee.gamma p dx).reserveX * (swapXToY fee.gamma p dx).reserveY / d) *
          ((swapXToY fee.gamma p dx).reserveY + dy) := by
        exact mul_le_mul_left' hd_le
          ((swapXToY fee.gamma p dx).reserveX * (swapXToY fee.gamma p dx).reserveY / d)
  have hprod : poolProduct p ≤ poolProduct q := le_trans h_swapX_prod h_swapY_prod
  have h_first_y_le : (swapXToY fee.gamma p dx).reserveY ≤ p.reserveY := by
    dsimp [swapXToY]
    let d : NNReal := p.reserveX + fee.gamma * dx
    have hd_pos : 0 < d := by
      dsimp [d]
      exact lt_of_lt_of_le hp.1 (le_add_of_nonneg_right (zero_le (fee.gamma * dx)))
    have hd_ne : d ≠ 0 := ne_of_gt hd_pos
    have hx_le_d : p.reserveX ≤ d := by
      dsimp [d]
      exact le_add_of_nonneg_right (zero_le (fee.gamma * dx))
    calc
      p.reserveX * p.reserveY / d ≤ d * p.reserveY / d := by
        exact div_le_div_of_nonneg_right (mul_le_mul_right' hx_le_d p.reserveY) (zero_le d)
      _ = p.reserveY := by
        exact mul_div_cancel_left₀ p.reserveY hd_ne
  have hyq : q.reserveY ≤ p.reserveY := by
    dsimp [q, swapYToX, amountOutXToY]
    exact le_of_eq (by rw [add_comm, tsub_add_cancel_of_le h_first_y_le])
  have h_final_x : p.reserveX ≤ q.reserveX := by
    dsimp [poolProduct] at hprod
    have hqprod_le : q.reserveX * q.reserveY ≤ q.reserveX * p.reserveY := by
      exact mul_le_mul_left' hyq q.reserveX
    have hmain : p.reserveX * p.reserveY ≤ q.reserveX * p.reserveY :=
      le_trans hprod hqprod_le
    exact (mul_le_mul_iff_left₀ hp.2).mp hmain
  have hsum :
      (swapXToY fee.gamma p dx).reserveX ≤ dx + q.reserveX := by
    dsimp [swapXToY]
    simpa [add_comm] using add_le_add_right h_final_x dx
  dsimp [roundTripXReturn, amountOutYToX, q]
  exact tsub_le_iff_right.mpr (by
    simpa [q] using hsum)



-- [family-lemma-library] banked: iso_roundTripX_final_reserveY_le_initial




theorem roundTripXReturn_lt_input_of_real_fee : ∀ (fee : FeeFactor)
    (p : ConstantProductPool) (dx : NNReal) (hp : PoolWellFormed p)
    (hfee : FeeIsReal fee) (hdx : 0 < dx), roundTripXReturn fee.gamma p dx < dx := by
  intro fee p dx hp hfee hdx
  let q : ConstantProductPool :=
    swapYToX fee.gamma (swapXToY fee.gamma p dx) (amountOutXToY fee.gamma p dx)
  have h_first_wf : PoolWellFormed (swapXToY fee.gamma p dx) := by
    rcases hp with ⟨hx, hy⟩
    constructor
    · change 0 < p.reserveX + dx
      exact lt_of_lt_of_le hx (le_add_of_nonneg_right (zero_le dx))
    · change 0 < p.reserveX * p.reserveY / (p.reserveX + fee.gamma * dx)
      exact div_pos (mul_pos hx hy)
        (lt_of_lt_of_le hx (le_add_of_nonneg_right (zero_le (fee.gamma * dx))))
  have h_swapX_prod :
      poolProduct p < poolProduct (swapXToY fee.gamma p dx) := by
    rcases hp with ⟨hx, hy⟩
    dsimp [poolProduct, swapXToY]
    let d : NNReal := p.reserveX + fee.gamma * dx
    have hd_pos : 0 < d := by
      dsimp [d]
      exact lt_of_lt_of_le hx (le_add_of_nonneg_right (zero_le (fee.gamma * dx)))
    have hd_ne : d ≠ 0 := ne_of_gt hd_pos
    have hgamma_mul : fee.gamma * dx < dx := by
      simpa using (mul_lt_mul_of_pos_right hfee hdx)
    have hd_lt : d < p.reserveX + dx := by
      dsimp [d]
      simpa [add_comm] using add_lt_add_left hgamma_mul p.reserveX
    have hquot_pos : 0 < p.reserveX * p.reserveY / d := by
      exact div_pos (mul_pos hx hy) hd_pos
    calc
      p.reserveX * p.reserveY = d * (p.reserveX * p.reserveY / d) := by
        exact (mul_div_cancel₀ (p.reserveX * p.reserveY) hd_ne).symm
      _ < (p.reserveX + dx) * (p.reserveX * p.reserveY / d) := by
        exact mul_lt_mul_of_pos_right hd_lt hquot_pos
  have h_swapY_prod :
      poolProduct (swapXToY fee.gamma p dx) ≤ poolProduct q := by
    rcases h_first_wf with ⟨_hx, hy⟩
    dsimp [q, poolProduct, swapYToX]
    let dy : NNReal := amountOutXToY fee.gamma p dx
    let d : NNReal := (swapXToY fee.gamma p dx).reserveY + fee.gamma * dy
    have hd_pos : 0 < d := by
      dsimp [d]
      exact lt_of_lt_of_le hy (le_add_of_nonneg_right (zero_le (fee.gamma * dy)))
    have hd_ne : d ≠ 0 := ne_of_gt hd_pos
    have hgamma_mul : fee.gamma * dy ≤ dy := by
      simpa using (mul_le_mul_right' fee.gamma_le_one dy)
    have hd_le : d ≤ (swapXToY fee.gamma p dx).reserveY + dy := by
      dsimp [d]
      simpa [add_comm] using add_le_add_left hgamma_mul (swapXToY fee.gamma p dx).reserveY
    calc
      (swapXToY fee.gamma p dx).reserveX * (swapXToY fee.gamma p dx).reserveY =
          ((swapXToY fee.gamma p dx).reserveX * (swapXToY fee.gamma p dx).reserveY / d) * d := by
        simpa [mul_comm] using
          (mul_div_cancel₀
            ((swapXToY fee.gamma p dx).reserveX * (swapXToY fee.gamma p dx).reserveY)
            hd_ne).symm
      _ ≤ ((swapXToY fee.gamma p dx).reserveX * (swapXToY fee.gamma p dx).reserveY / d) *
          ((swapXToY fee.gamma p dx).reserveY + dy) := by
        exact mul_le_mul_left' hd_le
          ((swapXToY fee.gamma p dx).reserveX * (swapXToY fee.gamma p dx).reserveY / d)
  have hprod : poolProduct p < poolProduct q := lt_of_lt_of_le h_swapX_prod h_swapY_prod
  have h_first_y_le : (swapXToY fee.gamma p dx).reserveY ≤ p.reserveY := by
    dsimp [swapXToY]
    let d : NNReal := p.reserveX + fee.gamma * dx
    have hd_pos : 0 < d := by
      dsimp [d]
      exact lt_of_lt_of_le hp.1 (le_add_of_nonneg_right (zero_le (fee.gamma * dx)))
    have hd_ne : d ≠ 0 := ne_of_gt hd_pos
    have hx_le_d : p.reserveX ≤ d := by
      dsimp [d]
      exact le_add_of_nonneg_right (zero_le (fee.gamma * dx))
    calc
      p.reserveX * p.reserveY / d ≤ d * p.reserveY / d := by
        exact div_le_div_of_nonneg_right (mul_le_mul_right' hx_le_d p.reserveY) (zero_le d)
      _ = p.reserveY := by
        exact mul_div_cancel_left₀ p.reserveY hd_ne
  have hyq : q.reserveY ≤ p.reserveY := by
    dsimp [q, swapYToX, amountOutXToY]
    exact le_of_eq (by rw [add_comm, tsub_add_cancel_of_le h_first_y_le])
  have h_final_x : p.reserveX < q.reserveX := by
    by_contra hnot
    have hxq : q.reserveX ≤ p.reserveX := le_of_not_gt hnot
    have hprod_le : q.reserveX * q.reserveY ≤ p.reserveX * p.reserveY := by
      exact mul_le_mul hxq hyq (zero_le q.reserveY) (zero_le p.reserveX)
    exact (not_lt_of_ge hprod_le) (by simpa [poolProduct] using hprod)
  have hreturn : (swapXToY fee.gamma p dx).reserveX - q.reserveX < dx := by
    dsimp [swapXToY]
    calc
      p.reserveX + dx - q.reserveX =
          p.reserveX + dx - (p.reserveX + (q.reserveX - p.reserveX)) := by
        rw [add_tsub_cancel_of_le h_final_x.le]
      _ = dx - (q.reserveX - p.reserveX) := by
        rw [add_tsub_add_eq_tsub_left]
      _ < dx := tsub_lt_self hdx (tsub_pos_of_lt h_final_x)
  dsimp [roundTripXReturn, amountOutYToX, q]
  simpa [q] using hreturn



-- [family-lemma-library] banked: iso_lemma1




theorem roundTripYReturn_le_input : ∀ (fee : FeeFactor)
    (p : ConstantProductPool) (dy : NNReal) (hp : PoolWellFormed p), roundTripYReturn fee.gamma p dy ≤ dy := by
  intro fee p dy hp
  let q : ConstantProductPool :=
    swapXToY fee.gamma (swapYToX fee.gamma p dy) (amountOutYToX fee.gamma p dy)
  have h_first_wf : PoolWellFormed (swapYToX fee.gamma p dy) := by
    rcases hp with ⟨hx, hy⟩
    constructor
    · change 0 < p.reserveX * p.reserveY / (p.reserveY + fee.gamma * dy)
      exact div_pos (mul_pos hx hy)
        (lt_of_lt_of_le hy (le_add_of_nonneg_right (zero_le (fee.gamma * dy))))
    · change 0 < p.reserveY + dy
      exact lt_of_lt_of_le hy (le_add_of_nonneg_right (zero_le dy))
  have h_swapY_prod :
      poolProduct p ≤ poolProduct (swapYToX fee.gamma p dy) := by
    rcases hp with ⟨_hx, hy⟩
    dsimp [poolProduct, swapYToX]
    let d : NNReal := p.reserveY + fee.gamma * dy
    have hd_pos : 0 < d := by
      dsimp [d]
      exact lt_of_lt_of_le hy (le_add_of_nonneg_right (zero_le (fee.gamma * dy)))
    have hd_ne : d ≠ 0 := ne_of_gt hd_pos
    have hgamma_mul : fee.gamma * dy ≤ dy := by
      simpa using (mul_le_mul_right' fee.gamma_le_one dy)
    have hd_le : d ≤ p.reserveY + dy := by
      dsimp [d]
      simpa [add_comm] using add_le_add_left hgamma_mul p.reserveY
    calc
      p.reserveX * p.reserveY = (p.reserveX * p.reserveY / d) * d := by
        simpa [mul_comm] using (mul_div_cancel₀ (p.reserveX * p.reserveY) hd_ne).symm
      _ ≤ (p.reserveX * p.reserveY / d) * (p.reserveY + dy) := by
        exact mul_le_mul_left' hd_le (p.reserveX * p.reserveY / d)
  have h_swapX_prod :
      poolProduct (swapYToX fee.gamma p dy) ≤ poolProduct q := by
    rcases h_first_wf with ⟨hx, _hy⟩
    dsimp [q, poolProduct, swapXToY]
    let dx : NNReal := amountOutYToX fee.gamma p dy
    let d : NNReal := (swapYToX fee.gamma p dy).reserveX + fee.gamma * dx
    have hd_pos : 0 < d := by
      dsimp [d]
      exact lt_of_lt_of_le hx (le_add_of_nonneg_right (zero_le (fee.gamma * dx)))
    have hd_ne : d ≠ 0 := ne_of_gt hd_pos
    have hgamma_mul : fee.gamma * dx ≤ dx := by
      simpa using (mul_le_mul_right' fee.gamma_le_one dx)
    have hd_le : d ≤ (swapYToX fee.gamma p dy).reserveX + dx := by
      dsimp [d]
      simpa [add_comm] using add_le_add_left hgamma_mul (swapYToX fee.gamma p dy).reserveX
    calc
      (swapYToX fee.gamma p dy).reserveX * (swapYToX fee.gamma p dy).reserveY =
          d * ((swapYToX fee.gamma p dy).reserveX * (swapYToX fee.gamma p dy).reserveY / d) := by
        exact
          (mul_div_cancel₀
            ((swapYToX fee.gamma p dy).reserveX * (swapYToX fee.gamma p dy).reserveY)
            hd_ne).symm
      _ ≤ ((swapYToX fee.gamma p dy).reserveX + dx) *
          ((swapYToX fee.gamma p dy).reserveX * (swapYToX fee.gamma p dy).reserveY / d) := by
        exact mul_le_mul_right' hd_le
          ((swapYToX fee.gamma p dy).reserveX * (swapYToX fee.gamma p dy).reserveY / d)
  have hprod : poolProduct p ≤ poolProduct q := le_trans h_swapY_prod h_swapX_prod
  have h_first_x_le : (swapYToX fee.gamma p dy).reserveX ≤ p.reserveX := by
    change p.reserveX * p.reserveY / (p.reserveY + fee.gamma * dy) ≤ p.reserveX
    exact NNReal.div_le_of_le_mul <|
      mul_le_mul_left' (le_add_of_nonneg_right (zero_le (fee.gamma * dy))) p.reserveX
  have hxq : q.reserveX = p.reserveX := by
    dsimp [q, swapXToY, amountOutYToX]
    exact add_tsub_cancel_of_le h_first_x_le
  have h_final_y : p.reserveY ≤ q.reserveY := by
    dsimp [poolProduct] at hprod
    rw [hxq] at hprod
    exact (mul_le_mul_iff_right₀ hp.1).mp hprod
  have hsum :
      (swapYToX fee.gamma p dy).reserveY ≤ dy + q.reserveY := by
    dsimp [swapYToX]
    simpa [add_comm, add_left_comm, add_assoc] using add_le_add_left h_final_y dy
  dsimp [roundTripYReturn, amountOutXToY, q]
  exact tsub_le_iff_right.mpr (by
    simpa [q] using hsum)



-- [family-lemma-library] banked: iso_roundTripY_final_reserveX_eq_initial




theorem roundTripYReturn_lt_input_of_real_fee : ∀ (fee : FeeFactor)
    (p : ConstantProductPool) (dy : NNReal) (hp : PoolWellFormed p)
    (hfee : FeeIsReal fee) (hdy : 0 < dy), roundTripYReturn fee.gamma p dy < dy := by
  intro fee p dy hp hfee hdy
  let q : ConstantProductPool :=
    swapXToY fee.gamma (swapYToX fee.gamma p dy) (amountOutYToX fee.gamma p dy)
  have h_first_wf : PoolWellFormed (swapYToX fee.gamma p dy) := by
    rcases hp with ⟨hx, hy⟩
    constructor
    · change 0 < p.reserveX * p.reserveY / (p.reserveY + fee.gamma * dy)
      exact div_pos (mul_pos hx hy)
        (lt_of_lt_of_le hy (le_add_of_nonneg_right (zero_le (fee.gamma * dy))))
    · change 0 < p.reserveY + dy
      exact lt_of_lt_of_le hy (le_add_of_nonneg_right (zero_le dy))
  have h_swapY_prod :
      poolProduct p < poolProduct (swapYToX fee.gamma p dy) := by
    rcases hp with ⟨hx, hy⟩
    dsimp [poolProduct, swapYToX]
    let d : NNReal := p.reserveY + fee.gamma * dy
    have hd_pos : 0 < d := by
      dsimp [d]
      exact lt_of_lt_of_le hy (le_add_of_nonneg_right (zero_le (fee.gamma * dy)))
    have hd_ne : d ≠ 0 := ne_of_gt hd_pos
    have hgamma_mul : fee.gamma * dy < dy := by
      simpa using (mul_lt_mul_of_pos_right hfee hdy)
    have hd_lt : d < p.reserveY + dy := by
      dsimp [d]
      simpa [add_comm] using add_lt_add_left hgamma_mul p.reserveY
    have hquot_pos : 0 < p.reserveX * p.reserveY / d := by
      exact div_pos (mul_pos hx hy) hd_pos
    calc
      p.reserveX * p.reserveY = (p.reserveX * p.reserveY / d) * d := by
        simpa [mul_comm] using (mul_div_cancel₀ (p.reserveX * p.reserveY) hd_ne).symm
      _ < (p.reserveX * p.reserveY / d) * (p.reserveY + dy) := by
        exact mul_lt_mul_of_pos_left hd_lt hquot_pos
  have h_swapX_prod :
      poolProduct (swapYToX fee.gamma p dy) ≤ poolProduct q := by
    rcases h_first_wf with ⟨hx, _hy⟩
    dsimp [q, poolProduct, swapXToY]
    let dx : NNReal := amountOutYToX fee.gamma p dy
    let d : NNReal := (swapYToX fee.gamma p dy).reserveX + fee.gamma * dx
    have hd_pos : 0 < d := by
      dsimp [d]
      exact lt_of_lt_of_le hx (le_add_of_nonneg_right (zero_le (fee.gamma * dx)))
    have hd_ne : d ≠ 0 := ne_of_gt hd_pos
    have hgamma_mul : fee.gamma * dx ≤ dx := by
      simpa using (mul_le_mul_right' fee.gamma_le_one dx)
    have hd_le : d ≤ (swapYToX fee.gamma p dy).reserveX + dx := by
      dsimp [d]
      simpa [add_comm] using add_le_add_left hgamma_mul (swapYToX fee.gamma p dy).reserveX
    calc
      (swapYToX fee.gamma p dy).reserveX * (swapYToX fee.gamma p dy).reserveY =
          d * ((swapYToX fee.gamma p dy).reserveX *
            (swapYToX fee.gamma p dy).reserveY / d) := by
        exact
          (mul_div_cancel₀
            ((swapYToX fee.gamma p dy).reserveX * (swapYToX fee.gamma p dy).reserveY)
            hd_ne).symm
      _ ≤ ((swapYToX fee.gamma p dy).reserveX + dx) *
          ((swapYToX fee.gamma p dy).reserveX *
            (swapYToX fee.gamma p dy).reserveY / d) := by
        exact mul_le_mul_right' hd_le
          ((swapYToX fee.gamma p dy).reserveX * (swapYToX fee.gamma p dy).reserveY / d)
  have hprod : poolProduct p < poolProduct q := lt_of_lt_of_le h_swapY_prod h_swapX_prod
  have h_first_x_le : (swapYToX fee.gamma p dy).reserveX ≤ p.reserveX := by
    change p.reserveX * p.reserveY / (p.reserveY + fee.gamma * dy) ≤ p.reserveX
    exact NNReal.div_le_of_le_mul <|
      mul_le_mul_left' (le_add_of_nonneg_right (zero_le (fee.gamma * dy))) p.reserveX
  have hxq : q.reserveX = p.reserveX := by
    dsimp [q, swapXToY, amountOutYToX]
    exact add_tsub_cancel_of_le h_first_x_le
  have h_final_y : p.reserveY < q.reserveY := by
    dsimp [poolProduct] at hprod
    rw [hxq] at hprod
    exact (mul_lt_mul_iff_right₀ hp.1).mp hprod
  have hreturn : (swapYToX fee.gamma p dy).reserveY - q.reserveY < dy := by
    dsimp [swapYToX]
    calc
      p.reserveY + dy - q.reserveY =
          p.reserveY + dy - (p.reserveY + (q.reserveY - p.reserveY)) := by
        rw [add_tsub_cancel_of_le h_final_y.le]
      _ = dy - (q.reserveY - p.reserveY) := by
        rw [add_tsub_add_eq_tsub_left]
      _ < dy := tsub_lt_self hdy (tsub_pos_of_lt h_final_y)
  dsimp [roundTripYReturn, amountOutXToY, q]
  simpa [q] using hreturn



-- [family-lemma-library] banked: iso_roundTripXReturn_lt_all










theorem swapXToY_product_strict_of_real_fee_aux (fee : FeeFactor)
    (p : ConstantProductPool) (dx : NNReal) (hp : PoolWellFormed p)
    (hfee : FeeIsReal fee) (hdx : 0 < dx) :
    poolProduct p < poolProduct (swapXToY fee.gamma p dx) := by
  rcases hp with ⟨hx, hy⟩
  dsimp [poolProduct, swapXToY]
  let d : NNReal := p.reserveX + fee.gamma * dx
  have hd_pos : 0 < d := by
    dsimp [d]
    exact lt_of_lt_of_le hx (le_add_of_nonneg_right (zero_le (fee.gamma * dx)))
  have hd_ne : d ≠ 0 := ne_of_gt hd_pos
  have hgamma_mul : fee.gamma * dx < dx := by
    simpa using (mul_lt_mul_of_pos_right hfee hdx)
  have hd_lt : d < p.reserveX + dx := by
    dsimp [d]
    simpa [add_comm] using add_lt_add_left hgamma_mul p.reserveX
  have hquot_pos : 0 < p.reserveX * p.reserveY / d := by
    exact div_pos (mul_pos hx hy) hd_pos
  calc
    p.reserveX * p.reserveY = d * (p.reserveX * p.reserveY / d) := by
      exact (mul_div_cancel₀ (p.reserveX * p.reserveY) hd_ne).symm
    _ < (p.reserveX + dx) * (p.reserveX * p.reserveY / d) := by
      exact mul_lt_mul_of_pos_right hd_lt hquot_pos

-- [family-lemma-library] banked: swapYToX_product_strict_of_real_fee_aux
theorem swapYToX_product_strict_of_real_fee_aux (fee : FeeFactor)
    (p : ConstantProductPool) (dy : NNReal) (hp : PoolWellFormed p)
    (hfee : FeeIsReal fee) (hdy : 0 < dy) :
    poolProduct p < poolProduct (swapYToX fee.gamma p dy) := by
  rcases hp with ⟨hx, hy⟩
  dsimp [poolProduct, swapYToX]
  let d : NNReal := p.reserveY + fee.gamma * dy
  have hd_pos : 0 < d := by
    dsimp [d]
    exact lt_of_lt_of_le hy (le_add_of_nonneg_right (zero_le (fee.gamma * dy)))
  have hd_ne : d ≠ 0 := ne_of_gt hd_pos
  have hgamma_mul : fee.gamma * dy < dy := by
    simpa using (mul_lt_mul_of_pos_right hfee hdy)
  have hd_lt : d < p.reserveY + dy := by
    dsimp [d]
    simpa [add_comm] using add_lt_add_left hgamma_mul p.reserveY
  have hquot_pos : 0 < p.reserveX * p.reserveY / d := by
    exact div_pos (mul_pos hx hy) hd_pos
  calc
    p.reserveX * p.reserveY = (p.reserveX * p.reserveY / d) * d := by
      simpa [mul_comm] using (mul_div_cancel₀ (p.reserveX * p.reserveY) hd_ne).symm
    _ < (p.reserveX * p.reserveY / d) * (p.reserveY + dy) := by
      exact mul_lt_mul_of_pos_left hd_lt hquot_pos

-- [family-lemma-library] banked: iso_strictSingleTradeInvariant_all

theorem applyTrade_product_mono (fee : FeeFactor) (p : ConstantProductPool)
    (trade : Trade) (hp : PoolWellFormed p) :
    poolProduct p ≤ poolProduct (applyTrade fee.gamma p trade) := by
  rcases trade with ⟨direction, amount⟩
  cases direction
  · exact swapXToY_product_mono fee p amount hp
  · exact swapYToX_product_mono fee p amount hp

-- [family-lemma-library] banked: constantProductAMM_temporal_invariant_and_no_roundTrip_profit
theorem constantProductAMM_temporal_invariant_and_no_roundTrip_profit : (∀ (fee : FeeFactor) (p : ConstantProductPool) (trade : Trade),
      SingleTradeInvariant fee p trade) ∧
    (∀ (fee : FeeFactor) (p : ConstantProductPool) (trade : Trade),
      StrictSingleTradeInvariant fee p trade) ∧
    (∀ (fee : FeeFactor) (p : ConstantProductPool) (trades : List Trade),
      TradeSequenceInvariant fee p trades) ∧
    (∀ (fee : FeeFactor) (p : ConstantProductPool) (dx : NNReal),
      PoolWellFormed p → roundTripXReturn fee.gamma p dx ≤ dx) ∧
    (∀ (fee : FeeFactor) (p : ConstantProductPool) (dy : NNReal),
      PoolWellFormed p → roundTripYReturn fee.gamma p dy ≤ dy) ∧
    (∀ (fee : FeeFactor) (p : ConstantProductPool) (dx : NNReal),
      PoolWellFormed p → FeeIsReal fee → 0 < dx →
        roundTripXReturn fee.gamma p dx < dx) ∧
    (∀ (fee : FeeFactor) (p : ConstantProductPool) (dy : NNReal),
      PoolWellFormed p → FeeIsReal fee → 0 < dy →
        roundTripYReturn fee.gamma p dy < dy) := by
  exact ⟨singleTradeInvariant, strictSingleTradeInvariant, tradeSequenceInvariant,
    roundTripXReturn_le_input, roundTripYReturn_le_input,
    roundTripXReturn_lt_input_of_real_fee, roundTripYReturn_lt_input_of_real_fee⟩
