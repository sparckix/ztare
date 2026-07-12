/-
LeanMill campaign provenance — no_history_enables_round_trip_arbitrage
The theorem(s) below are the VERBATIM machine-checked closure. This header is GENERATED from run
telemetry (run_tag=amm_nocyclic_v6) by promote_campaign_artifact.py — not hand-authored.

  outcome     : closed · faithful · axioms propext, Classical.choice, Quot.sound
  domain      : DeFi market-microstructure — no round-trip arbitrage at ANY reachable AMM state (flash-loan / sandwich / cyclic path); compounds the banked constant-product theory
  time        : wall 486.25s launch→close = formalize 237.97s (theory+statement+firewall) + prove 248.28s (proof search) · prove p50 248.28s p95 248.28s
  compute     : cost-to-closure 236.71s mean · 236.71s total
  yield       : 1/5 attempts closed (3 failed)
  phases      : 381.3s leaf.dispatch · 83.2s pool · 58.5s formalize · 14.5s native · 0.2s govern.mnc
  reuse       : cited 0 banked rung(s)
  moves       : native_hammer×3 · proposer_pool×1 · claude_warm×1
  milestone   : campaign family 'amm_nocyclic' — 5 run(s) · REAL elapsed (launch→last) 6436.1s (~107 min) = formalize 1711.1s + prove/other · active-solve 1979.6s · 19 closures [launch→last is the honest wall]
     - amm_nocyclic_v2: 1/17 closed · elapsed 1321.7s (~22.0 min)
     - amm_nocyclic_v3: 5/36 closed · elapsed 1947.52s (~32.5 min)
     - amm_nocyclic_v4: 6/12 closed · elapsed 1596.52s (~26.6 min)
     - amm_nocyclic_v5: 6/6 closed · elapsed 1077.55s (~18.0 min)
     - amm_nocyclic_v6: 1/5 closed · elapsed 492.78s (~8.2 min)
-/
import Mathlib

-- Natural-language specification (blueprint): blueprints/amm_no_cyclic_arbitrage_blueprint.md
-- Read the blueprint to check the faithfulness boundary — the guarantee stops where the English intent is argued, not proved.

structure ConstantProductPool where
  reserveX : NNReal
  reserveY : NNReal

def PoolWellFormed (p : ConstantProductPool) : Prop :=
  0 < p.reserveX ∧ 0 < p.reserveY

def poolProduct (p : ConstantProductPool) : NNReal :=
  p.reserveX * p.reserveY

structure FeeFactor where
  gamma : NNReal
  gamma_pos : 0 < gamma
  gamma_le_one : gamma ≤ 1

def FeeIsReal (fee : FeeFactor) : Prop :=
  fee.gamma < 1

inductive TradeDirection where
  | xToY
  | yToX
deriving DecidableEq, Repr

structure Trade where
  direction : TradeDirection
  amount : NNReal

noncomputable def swapXToY (gamma : NNReal) (p : ConstantProductPool) (dx : NNReal) :
    ConstantProductPool where
  reserveX := p.reserveX + dx
  reserveY := p.reserveX * p.reserveY / (p.reserveX + gamma * dx)

noncomputable def swapYToX (gamma : NNReal) (p : ConstantProductPool) (dy : NNReal) :
    ConstantProductPool where
  reserveX := p.reserveX * p.reserveY / (p.reserveY + gamma * dy)
  reserveY := p.reserveY + dy

noncomputable def applyTrade (gamma : NNReal) (p : ConstantProductPool) (trade : Trade) :
    ConstantProductPool :=
  match trade.direction with
  | TradeDirection.xToY => swapXToY gamma p trade.amount
  | TradeDirection.yToX => swapYToX gamma p trade.amount

noncomputable def executeTrades (gamma : NNReal) (p : ConstantProductPool)
    (trades : List Trade) : ConstantProductPool :=
  trades.foldl (fun state trade => applyTrade gamma state trade) p

noncomputable def TradesKeepWellFormed (gamma : NNReal) (p : ConstantProductPool) :
    List Trade → Prop
  | [] => PoolWellFormed p
  | trade :: trades =>
      PoolWellFormed p ∧ TradesKeepWellFormed gamma (applyTrade gamma p trade) trades

noncomputable def amountOutXToY (gamma : NNReal) (p : ConstantProductPool) (dx : NNReal) :
    NNReal :=
  p.reserveY - (swapXToY gamma p dx).reserveY

noncomputable def amountOutYToX (gamma : NNReal) (p : ConstantProductPool) (dy : NNReal) :
    NNReal :=
  p.reserveX - (swapYToX gamma p dy).reserveX

noncomputable def roundTripXReturn (gamma : NNReal) (p : ConstantProductPool) (dx : NNReal) :
    NNReal :=
  amountOutYToX gamma (swapXToY gamma p dx) (amountOutXToY gamma p dx)

noncomputable def roundTripYReturn (gamma : NNReal) (p : ConstantProductPool) (dy : NNReal) :
    NNReal :=
  amountOutXToY gamma (swapYToX gamma p dy) (amountOutYToX gamma p dy)

noncomputable def reachablePool (fee : FeeFactor) (p : ConstantProductPool)
    (trades : List Trade) : ConstantProductPool :=
  executeTrades fee.gamma p trades

noncomputable def roundTripReturn (gamma : NNReal) (p : ConstantProductPool)
    (direction : TradeDirection) (amount : NNReal) : NNReal :=
  match direction with
  | TradeDirection.xToY => roundTripXReturn gamma p amount
  | TradeDirection.yToX => roundTripYReturn gamma p amount

noncomputable def reachableRoundTripReturn (fee : FeeFactor)
    (p : ConstantProductPool) (trades : List Trade)
    (direction : TradeDirection) (amount : NNReal) : NNReal :=
  roundTripReturn fee.gamma (reachablePool fee p trades) direction amount

theorem applyTrade_keep_wellFormed (gamma : NNReal) (p : ConstantProductPool)
    (trade : Trade) (hp : PoolWellFormed p) :
    PoolWellFormed (applyTrade gamma p trade) := by
  rcases hp with ⟨hx, hy⟩
  rcases trade with ⟨direction, amount⟩
  cases direction
  · constructor
    · change 0 < p.reserveX + amount
      exact lt_of_lt_of_le hx (le_add_of_nonneg_right (zero_le amount))
    · change 0 < p.reserveX * p.reserveY / (p.reserveX + gamma * amount)
      exact div_pos (mul_pos hx hy)
        (lt_of_lt_of_le hx (le_add_of_nonneg_right (zero_le (gamma * amount))))
  · constructor
    · change 0 < p.reserveX * p.reserveY / (p.reserveY + gamma * amount)
      exact div_pos (mul_pos hx hy)
        (lt_of_lt_of_le hy (le_add_of_nonneg_right (zero_le (gamma * amount))))
    · change 0 < p.reserveY + amount
      exact lt_of_lt_of_le hy (le_add_of_nonneg_right (zero_le amount))

theorem executeTrades_keep_wellFormed (gamma : NNReal) :
    ∀ (p : ConstantProductPool) (trades : List Trade),
      PoolWellFormed p → TradesKeepWellFormed gamma p trades := by
  intro p trades
  induction trades generalizing p with
  | nil =>
      intro hp
      exact hp
  | cons trade trades ih =>
      intro hp
      constructor
      · exact hp
      · exact ih (applyTrade gamma p trade) (applyTrade_keep_wellFormed gamma p trade hp)

theorem executeTrades_final_wellFormed (gamma : NNReal) :
    ∀ (p : ConstantProductPool) (trades : List Trade),
      PoolWellFormed p → PoolWellFormed (executeTrades gamma p trades) := by
  intro p trades
  induction trades generalizing p with
  | nil =>
      intro hp
      simpa [executeTrades] using hp
  | cons trade trades ih =>
      intro hp
      simpa [executeTrades, List.foldl_cons] using
        ih (applyTrade gamma p trade) (applyTrade_keep_wellFormed gamma p trade hp)

theorem reachablePool_wellFormed (fee : FeeFactor) (p : ConstantProductPool)
    (trades : List Trade) (hp : PoolWellFormed p) :
    PoolWellFormed (reachablePool fee p trades) := by
  simpa [reachablePool] using executeTrades_final_wellFormed fee.gamma p trades hp

theorem roundTripXReturn_le_input (fee : FeeFactor)
    (p : ConstantProductPool) (dx : NNReal) (hp : PoolWellFormed p) :
    roundTripXReturn fee.gamma p dx ≤ dx := by
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

theorem roundTripXReturn_lt_input_of_real_fee (fee : FeeFactor)
    (p : ConstantProductPool) (dx : NNReal) (hp : PoolWellFormed p)
    (hfee : FeeIsReal fee) (hdx : 0 < dx) :
    roundTripXReturn fee.gamma p dx < dx := by
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

theorem roundTripYReturn_le_input (fee : FeeFactor)
    (p : ConstantProductPool) (dy : NNReal) (hp : PoolWellFormed p) :
    roundTripYReturn fee.gamma p dy ≤ dy := by
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

theorem roundTripYReturn_lt_input_of_real_fee (fee : FeeFactor)
    (p : ConstantProductPool) (dy : NNReal) (hp : PoolWellFormed p)
    (hfee : FeeIsReal fee) (hdy : 0 < dy) :
    roundTripYReturn fee.gamma p dy < dy := by
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

theorem no_history_enables_round_trip_arbitrage : (∀ (fee : FeeFactor) (p : ConstantProductPool) (trades : List Trade),
      PoolWellFormed p →
        TradesKeepWellFormed fee.gamma p trades ∧
        (∀ direction amount,
          reachableRoundTripReturn fee p trades direction amount ≤ amount) ∧
        (FeeIsReal fee →
          ∀ direction amount, 0 < amount →
            reachableRoundTripReturn fee p trades direction amount < amount)) ∧
    (∃ (fee : FeeFactor) (p : ConstantProductPool) (trades : List Trade)
        (amount : NNReal),
      PoolWellFormed p ∧ FeeIsReal fee ∧ 0 < amount ∧
        reachableRoundTripReturn fee p trades TradeDirection.xToY amount < amount ∧
        reachableRoundTripReturn fee p trades TradeDirection.yToX amount < amount) := by
  constructor
  · intro fee p trades hp
    have hreach : PoolWellFormed (reachablePool fee p trades) :=
      reachablePool_wellFormed fee p trades hp
    constructor
    · exact executeTrades_keep_wellFormed fee.gamma p trades hp
    · constructor
      · intro direction amount
        cases direction
        · simpa [reachableRoundTripReturn, roundTripReturn] using
            roundTripXReturn_le_input fee (reachablePool fee p trades) amount hreach
        · simpa [reachableRoundTripReturn, roundTripReturn] using
            roundTripYReturn_le_input fee (reachablePool fee p trades) amount hreach
      · intro hfee direction amount hamount
        cases direction
        · simpa [reachableRoundTripReturn, roundTripReturn] using
            roundTripXReturn_lt_input_of_real_fee fee (reachablePool fee p trades) amount
              hreach hfee hamount
        · simpa [reachableRoundTripReturn, roundTripReturn] using
            roundTripYReturn_lt_input_of_real_fee fee (reachablePool fee p trades) amount
              hreach hfee hamount
  · let fee : FeeFactor := ⟨(1 / 2 : NNReal), by norm_num, by norm_num⟩
    let p : ConstantProductPool := ⟨1, 1⟩
    refine ⟨fee, p, [], 1, ?_, ?_, ?_, ?_, ?_⟩
    · norm_num [PoolWellFormed, p]
    · norm_num [FeeIsReal, fee]
    · norm_num
    · have hp : PoolWellFormed p := by norm_num [PoolWellFormed, p]
      have hfee : FeeIsReal fee := by norm_num [FeeIsReal, fee]
      have hpos : 0 < (1 : NNReal) := by norm_num
      simpa [reachableRoundTripReturn, reachablePool, executeTrades, roundTripReturn] using
        roundTripXReturn_lt_input_of_real_fee fee p 1 hp hfee hpos
    · have hp : PoolWellFormed p := by norm_num [PoolWellFormed, p]
      have hfee : FeeIsReal fee := by norm_num [FeeIsReal, fee]
      have hpos : 0 < (1 : NNReal) := by norm_num
      simpa [reachableRoundTripReturn, reachablePool, executeTrades, roundTripReturn] using
        roundTripYReturn_lt_input_of_real_fee fee p 1 hp hfee hpos

#print axioms no_history_enables_round_trip_arbitrage
