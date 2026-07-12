/-
LeanMill campaign provenance — ef1_attainable_relaxation_via_roundRobin
The theorem(s) below are the VERBATIM machine-checked closure. This header is GENERATED from run
telemetry (run_tag=notes_ef1_indivisible_allocation_blueprint_0704T0618) by promote_campaign_artifact.py — not hand-authored.

  outcome     : closed · faithful · axioms propext, Classical.choice, Quot.sound
  domain      : formalization-nonmath
  time        : wall 3573.12s launch→close = formalize 1418.96s (theory+statement+firewall) + prove 2154.16s (proof search) · prove p50 2753.23s p95 3614.54s
  compute     : cost-to-closure 1294.26s mean · 2468.36s total
  yield       : 8/15 attempts closed (7 failed)
  phases      : 2169.2s leaf.dispatch · 216.9s pool · 115s formalize · 39.9s native · 9.4s govern.mnc · 0s consolidate
  reuse       : 1 rung(s) banked this run · 0 reused from prior bank
  moves       : native_hammer×8 · claude_warm×5 · proposer_pool×2
  milestone   : campaign family 'notes_ef1_indivisible_allocation_blueprint' — 2 run(s) · REAL elapsed (launch→last) 4442s (~74 min) = formalize 466.8s + prove/other · active-solve 2484.5s · 9 closures [launch→last is the honest wall]
     - notes_ef1_indivisible_allocation_blueprint_0704T0601: 1/3 closed · elapsed 685.57s (~11.4 min)
     - notes_ef1_indivisible_allocation_blueprint_0704T0618: 8/15 closed · elapsed 3756.44s (~62.6 min)
-/
import Mathlib

-- Natural-language specification (blueprint): blueprints/ef1_indivisible_allocation_blueprint.md
-- Read the blueprint to check the faithfulness boundary — the guarantee stops where the English intent is argued, not proved.

namespace FormalizeProbe

structure Valuation (Item K : Type*) [Zero K] [LE K] where
  value : Item → K
  nonneg : ∀ g : Item, 0 ≤ value g

section OrderedField

variable {Agent Item K : Type*}
variable [Field K] [LinearOrder K] [IsStrictOrderedRing K]

def bundleValue (v : Valuation Item K) (bundle : Finset Item) : K :=
  Finset.sum bundle fun g => v.value g

/-- Anchor (overlap-agreement): bundle value is exactly Mathlib `Finset.sum`. -/

structure Allocation (Agent Item : Type*) where
  owner : Item → Agent

/-- Anchor (characterization): allocation equality is equality of owner functions. -/

def bundle [DecidableEq Agent]
    (goods : Finset Item) (allocation : Allocation Agent Item) (i : Agent) : Finset Item :=
  goods.filter fun g => allocation.owner g = i

/-- Anchor (characterization): membership in a bundle means good membership plus matching owner. -/

def Envies [DecidableEq Agent]
    (profile : Agent → Valuation Item K) (goods : Finset Item)
    (allocation : Allocation Agent Item) (i j : Agent) : Prop :=
  bundleValue (profile i) (bundle goods allocation i) <
    bundleValue (profile i) (bundle goods allocation j)

/-- Anchor (characterization): envy is the strict bundle-value comparison. -/

def EnvyFree [DecidableEq Agent]
    (profile : Agent → Valuation Item K) (goods : Finset Item)
    (allocation : Allocation Agent Item) : Prop :=
  ∀ i j : Agent, ¬ Envies profile goods allocation i j

/-- Anchor (characterization): envy-freeness is no strict envy for every ordered pair. -/

def DoesNotEnvyUpToOneGood [DecidableEq Agent] [DecidableEq Item]
    (profile : Agent → Valuation Item K) (goods : Finset Item)
    (allocation : Allocation Agent Item) (i j : Agent) : Prop :=
  (bundle goods allocation j).Nonempty →
    ∃ g ∈ bundle goods allocation j,
      bundleValue (profile i) (bundle goods allocation i) ≥
        bundleValue (profile i) ((bundle goods allocation j).erase g)

/-- Anchor (characterization): pairwise EF1 is the standard removal implication. -/

def EnvyFreeUpToOneGood [DecidableEq Agent] [DecidableEq Item]
    (profile : Agent → Valuation Item K) (goods : Finset Item)
    (allocation : Allocation Agent Item) : Prop :=
  ∀ i j : Agent, DoesNotEnvyUpToOneGood profile goods allocation i j

/-- Anchor (characterization): EF1 is exactly universal pairwise EF1. -/

def SequentiallyDominates (v : Valuation Item K) (iPicks jPicks : List Item) : Prop :=
  iPicks.Nodup ∧ jPicks.Nodup ∧
    ∀ n (hj : n + 1 < jPicks.length),
      ∃ hi : n < iPicks.length,
        v.value (jPicks.get ⟨n + 1, hj⟩) ≤ v.value (iPicks.get ⟨n, hi⟩)

/-- Anchor (characterization): sequential dominance is nodup plus shifted pointwise comparison. -/

def pickedItems [DecidableEq Item] (picks : List (Agent × Item)) : Finset Item :=
  (picks.map Prod.snd).toFinset

/-- Anchor (overlap-agreement): picked items are the `toFinset` of second coordinates. -/

def remainingItems [DecidableEq Item]
    (goods : Finset Item) (picks : List (Agent × Item)) (n : Nat) : Finset Item :=
  goods \ ((picks.take n).map Prod.snd).toFinset

/-- Anchor (characterization): remaining items are goods not yet picked before index `n`. -/

def CoveredAgentOrder (order : List Agent) : Prop :=
  order.Nodup ∧ ∀ i : Agent, i ∈ order

/-- Anchor (characterization): covered orders are nodup lists containing every agent. -/

def PickLogRoundRobin [DecidableEq Item]
    (profile : Agent → Valuation Item K) (goods : Finset Item)
    (order : List Agent) (picks : List (Agent × Item)) : Prop :=
  ∃ hlen : 0 < order.length,
    CoveredAgentOrder order ∧
      (picks.map Prod.snd).Nodup ∧
        pickedItems (Item := Item) picks = goods ∧
          ∀ n (hn : n < picks.length),
            let pick := picks.get ⟨n, hn⟩
            pick.1 = order.get ⟨n % order.length, Nat.mod_lt n hlen⟩ ∧
              pick.2 ∈ remainingItems goods picks n ∧
                ∀ g ∈ remainingItems goods picks n,
                  (profile pick.1).value g ≤ (profile pick.1).value pick.2

/-- Anchor (characterization): `PickLogRoundRobin` is the covered trace condition. -/

def PickLogMatchesAllocation
    (allocation : Allocation Agent Item) (picks : List (Agent × Item)) : Prop :=
  ∀ n (hn : n < picks.length),
    allocation.owner (picks.get ⟨n, hn⟩).2 = (picks.get ⟨n, hn⟩).1

def RoundRobin [DecidableEq Item]
    (profile : Agent → Valuation Item K) (goods : Finset Item)
    (order : List Agent) (allocation : Allocation Agent Item) : Prop :=
  ∃ picks : List (Agent × Item),
    PickLogRoundRobin profile goods order picks ∧
      PickLogMatchesAllocation allocation picks

private theorem owner_eq_of_mem_of_snd_nodup
    {picks : List (Agent × Item)}
    (hnodup : (picks.map Prod.snd).Nodup)
    {a b : Agent} {g : Item}
    (ha : (a, g) ∈ picks) (hb : (b, g) ∈ picks) :
    a = b := by
  have hp : (a, g) = (b, g) :=
    List.inj_on_of_nodup_map hnodup ha hb rfl
  exact congrArg Prod.fst hp

private theorem suffix_remaining_cons_erase [DecidableEq Item]
    (s : Finset Item) (x : Item) (a : Agent) (tail : List (Agent × Item)) (n : Nat) :
    s \ ((((a, x) :: tail).take (n + 1)).map Prod.snd).toFinset =
      (s.erase x) \ ((tail.take n).map Prod.snd).toFinset := by
  ext y
  by_cases hyx : y = x
  · subst hyx
    simp
  · simp [Finset.mem_sdiff, Finset.mem_erase, hyx]

private theorem exists_greedy_roundRobin_suffix [DecidableEq Agent] [DecidableEq Item]
    (profile : Agent → Valuation Item K) (order : List Agent)
    (hlen : 0 < order.length) :
    ∀ s : Finset Item, ∀ t : Nat,
      ∃ picks : List (Agent × Item),
        (picks.map Prod.snd).Nodup ∧
          pickedItems (Item := Item) picks = s ∧
            ∀ n (hn : n < picks.length),
              let pick := picks.get ⟨n, hn⟩
              pick.1 = order.get ⟨(t + n) % order.length, Nat.mod_lt _ hlen⟩ ∧
                pick.2 ∈ s \ ((picks.take n).map Prod.snd).toFinset ∧
                  ∀ g ∈ s \ ((picks.take n).map Prod.snd).toFinset,
                    (profile pick.1).value g ≤ (profile pick.1).value pick.2 := by
  classical
  let P : Nat → Prop := fun m =>
    ∀ s : Finset Item, s.card = m → ∀ t : Nat,
      ∃ picks : List (Agent × Item),
        (picks.map Prod.snd).Nodup ∧
          pickedItems (Item := Item) picks = s ∧
            ∀ n (hn : n < picks.length),
              let pick := picks.get ⟨n, hn⟩
              pick.1 = order.get ⟨(t + n) % order.length, Nat.mod_lt _ hlen⟩ ∧
                pick.2 ∈ s \ ((picks.take n).map Prod.snd).toFinset ∧
                  ∀ g ∈ s \ ((picks.take n).map Prod.snd).toFinset,
                    (profile pick.1).value g ≤ (profile pick.1).value pick.2
  have hP : ∀ m, P m := by
    intro m
    induction m using Nat.strong_induction_on with
    | h m ih =>
        intro s hcard t
        by_cases hs : s.Nonempty
        · let currentAgent :=
            order.get ⟨t % order.length, Nat.mod_lt t hlen⟩
          obtain ⟨x, hxmem, hxmax⟩ :=
            Finset.exists_max_image s (fun g => (profile currentAgent).value g) hs
          have hlt : (s.erase x).card < m := by
            rw [← hcard]
            exact Finset.card_erase_lt_of_mem hxmem
          obtain ⟨tail, htail_nodup, htail_picked, htail_trace⟩ :=
            ih (s.erase x).card hlt (s.erase x) rfl (t + 1)
          refine ⟨(currentAgent, x) :: tail, ?_, ?_, ?_⟩
          · have hx_not_tail : x ∉ tail.map Prod.snd := by
              intro hx_tail
              have hx_pick : x ∈ pickedItems (Item := Item) tail := by
                simpa [pickedItems] using hx_tail
              rw [htail_picked] at hx_pick
              exact (Finset.notMem_erase x s) hx_pick
            simpa [hx_not_tail, htail_nodup]
          · calc
              pickedItems (Item := Item) ((currentAgent, x) :: tail)
                  = insert x (pickedItems (Item := Item) tail) := by
                    simp [pickedItems]
              _ = insert x (s.erase x) := by
                    rw [htail_picked]
              _ = s := Finset.insert_erase hxmem
          · intro n hn
            cases n with
            | zero =>
                have hagent :
                    currentAgent =
                      order.get ⟨(t + 0) % order.length, Nat.mod_lt _ hlen⟩ := by
                  simp [currentAgent]
                refine ⟨hagent, ?_, ?_⟩
                · simpa [currentAgent, Finset.mem_sdiff] using hxmem
                · intro g hg
                  have hgmem : g ∈ s := by
                    exact (Finset.mem_sdiff.mp hg).1
                  simpa [currentAgent] using hxmax g hgmem
            | succ n =>
                have hn_tail : n < tail.length := by
                  simpa using Nat.succ_lt_succ_iff.mp hn
                have htrace := htail_trace n hn_tail
                have hrem :
                    s \ (((((currentAgent, x) :: tail).take (n + 1)).map Prod.snd).toFinset) =
                      (s.erase x) \ ((tail.take n).map Prod.snd).toFinset :=
                  suffix_remaining_cons_erase s x currentAgent tail n
                refine ⟨?_, ?_, ?_⟩
                · have hidx : (t + (n + 1)) % order.length =
                      (t + 1 + n) % order.length := by
                    have hsum : t + (n + 1) = t + 1 + n := by omega
                    exact congrArg (fun q => q % order.length) hsum
                  simpa [currentAgent, hidx] using htrace.1
                · rw [hrem]
                  exact htrace.2.1
                · intro g hg
                  have hg' : g ∈ (s.erase x) \ ((tail.take n).map Prod.snd).toFinset := by
                    rw [← hrem]
                    exact hg
                  simpa [currentAgent, Nat.add_assoc, Nat.add_comm, Nat.add_left_comm] using
                    htrace.2.2 g hg'
        · have hs_empty : s = ∅ := Finset.not_nonempty_iff_eq_empty.mp hs
          refine ⟨[], ?_, ?_, ?_⟩
          · simp
          · simp [pickedItems, hs_empty]
          · intro n hn
            simp at hn
  intro s t
  exact hP s.card s rfl t

private def agentItems [DecidableEq Agent] (a : Agent) (picks : List (Agent × Item)) :
    List Item :=
  (picks.filter fun p => p.1 = a).map Prod.snd

private theorem agentItems_nodup [DecidableEq Agent]
    {picks : List (Agent × Item)} {a : Agent}
    (hnodup : (picks.map Prod.snd).Nodup) :
    (agentItems a picks).Nodup := by
  exact hnodup.sublist
    ((List.filter_sublist (p := fun p : Agent × Item => decide (p.1 = a))
      (l := picks)).map Prod.snd)

private theorem agentItems_toFinset_eq_bundle [DecidableEq Agent] [DecidableEq Item]
    {profile : Agent → Valuation Item K} {goods : Finset Item}
    {order : List Agent} {allocation : Allocation Agent Item}
    {picks : List (Agent × Item)}
    (hlog : PickLogRoundRobin profile goods order picks)
    (hmatch : PickLogMatchesAllocation allocation picks)
    (a : Agent) :
    (agentItems a picks).toFinset = bundle goods allocation a := by
  rcases hlog with ⟨_hlen, _hcovered, _hnodup, hpicked, _htrace⟩
  ext x
  constructor
  · intro hx
    simp only [agentItems, List.mem_toFinset, List.mem_map, List.mem_filter] at hx
    rcases hx with ⟨p, ⟨hp_mem, hp_agent⟩, hp_item⟩
    have hx_goods : x ∈ goods := by
      rw [← hpicked]
      simp only [pickedItems, List.mem_toFinset, List.mem_map]
      exact ⟨p, hp_mem, hp_item⟩
    rcases List.exists_mem_iff_get.mp ⟨p, hp_mem, rfl⟩ with ⟨idx, _hidx⟩
    have howner_p : allocation.owner p.2 = p.1 := by
      subst p
      exact hmatch idx idx.isLt
    have hp_agent_eq : p.1 = a := of_decide_eq_true hp_agent
    have hx_owner : allocation.owner x = a := by
      calc
        allocation.owner x = allocation.owner p.2 := by rw [hp_item]
        _ = p.1 := howner_p
        _ = a := hp_agent_eq
    simpa [bundle] using And.intro hx_goods hx_owner
  · intro hx
    have hx_bundle : x ∈ goods ∧ allocation.owner x = a := by
      simpa [bundle] using hx
    have hx_picked : x ∈ pickedItems (Item := Item) picks := by
      rw [hpicked]
      exact hx_bundle.1
    have hx_map : x ∈ (picks.map Prod.snd).toFinset := by
      simpa [pickedItems] using hx_picked
    simp only [List.mem_toFinset, List.mem_map] at hx_map
    rcases hx_map with ⟨p, hp_mem, hp_item⟩
    rcases List.exists_mem_iff_get.mp ⟨p, hp_mem, rfl⟩ with ⟨idx, _hidx⟩
    have howner_p : allocation.owner p.2 = p.1 := by
      subst p
      exact hmatch idx idx.isLt
    have hp_agent : p.1 = a := by
      calc
        p.1 = allocation.owner p.2 := howner_p.symm
        _ = allocation.owner x := by rw [hp_item]
        _ = a := hx_bundle.2
    simp only [agentItems, List.mem_toFinset, List.mem_map, List.mem_filter]
    exact ⟨p, ⟨hp_mem, by simpa [hp_agent]⟩, hp_item⟩

private theorem length_pos_of_toFinset_nonempty [DecidableEq Item] {s : Finset Item}
    {l : List Item} (h : l.toFinset = s) (hs : s.Nonempty) :
    0 < l.length := by
  rw [← h] at hs
  cases l with
  | nil => simpa using hs
  | cons _ _ => simp

private theorem first_mem_of_toFinset_eq [DecidableEq Item] {s : Finset Item} {l : List Item}
    (h : l.toFinset = s) (hlen : 0 < l.length) :
    l.get ⟨0, hlen⟩ ∈ s := by
  rw [← h]
  simpa using List.get_mem l ⟨0, hlen⟩

private theorem erase_first_toFinset_eq_tail_toFinset [DecidableEq Item] {l : List Item}
    (hnd : l.Nodup) (hlen : 0 < l.length) :
    l.toFinset.erase (l.get ⟨0, hlen⟩) = l.tail.toFinset := by
  cases l with
  | nil =>
      simp at hlen
  | cons a t =>
      simp at hnd
      ext x
      simp [hnd.1]

private theorem list_sum_nonneg_of_value_nonneg
    (v : Valuation Item K) (l : List Item) :
    0 ≤ (l.map fun g => v.value g).sum := by
  induction l with
  | nil => simp
  | cons g gs ih =>
      simpa using add_nonneg (v.nonneg g) ih

private theorem list_sum_le_of_get
    (v : Valuation Item K) :
    ∀ {xs ys : List Item},
      ys.length ≤ xs.length →
      (∀ n (hy : n < ys.length) (hx : n < xs.length),
        v.value (ys.get ⟨n, hy⟩) ≤ v.value (xs.get ⟨n, hx⟩)) →
      (ys.map fun g => v.value g).sum ≤ (xs.map fun g => v.value g).sum
  | [], [], _, _ => by simp
  | [], _ :: _, hlen, _ => by simp at hlen
  | x :: xs, [], _, _ => by
      simpa using list_sum_nonneg_of_value_nonneg v (x :: xs)
  | x :: xs, y :: ys, hlen, hle => by
      have hhead : v.value y ≤ v.value x := by
        simpa using hle 0 (by simp) (by simp)
      have htail :
          (ys.map fun g => v.value g).sum ≤
            (xs.map fun g => v.value g).sum := by
        refine list_sum_le_of_get v (Nat.succ_le_succ_iff.mp hlen) ?_
        intro n hy hx
        have hy' : n + 1 < (y :: ys).length := by
          simpa [Nat.succ_eq_add_one] using Nat.succ_lt_succ hy
        have hx' : n + 1 < (x :: xs).length := by
          simpa [Nat.succ_eq_add_one] using Nat.succ_lt_succ hx
        simpa using hle (n + 1) hy' hx'
      simpa using add_le_add hhead htail

private theorem bundleValue_tail_toFinset_le [DecidableEq Item]
    (v : Valuation Item K) {iPicks jPicks : List Item}
    (hdom : SequentiallyDominates v iPicks jPicks) :
    bundleValue v jPicks.tail.toFinset ≤ bundleValue v iPicks.toFinset := by
  have htail_len : jPicks.tail.length ≤ iPicks.length := by
    by_contra hnot
    have hlt : iPicks.length < jPicks.tail.length := Nat.lt_of_not_ge hnot
    have hj : iPicks.length + 1 < jPicks.length := by
      simp only [List.length_tail] at hlt
      omega
    rcases hdom.2.2 iPicks.length hj with ⟨hi, _⟩
    exact (Nat.lt_irrefl iPicks.length hi).elim
  have hpoint :
      ∀ n (hj : n < jPicks.tail.length) (hi : n < iPicks.length),
        v.value (jPicks.tail.get ⟨n, hj⟩) ≤
          v.value (iPicks.get ⟨n, hi⟩) := by
    intro n hj hi
    have hj' : n + 1 < jPicks.length := by
      simp only [List.length_tail] at hj
      omega
    rcases hdom.2.2 n hj' with ⟨_, hle⟩
    simpa [List.get_tail] using hle
  have hlist :
      (jPicks.tail.map fun g => v.value g).sum ≤
        (iPicks.map fun g => v.value g).sum :=
    list_sum_le_of_get v htail_len hpoint
  have hjnd : jPicks.tail.Nodup := hdom.2.1.tail
  calc
    bundleValue v jPicks.tail.toFinset
        = (jPicks.tail.map fun g => v.value g).sum := by
          simpa [bundleValue] using
            (List.sum_toFinset (fun g => v.value g) hjnd)
    _ ≤ (iPicks.map fun g => v.value g).sum := hlist
    _ = bundleValue v iPicks.toFinset := by
          simpa [bundleValue] using
            (List.sum_toFinset (fun g => v.value g) hdom.1).symm

private theorem sequentiallyDominates_pair_EF1_core [DecidableEq Agent] [DecidableEq Item]
    {profile : Agent → Valuation Item K} {goods : Finset Item}
    {allocation : Allocation Agent Item} {i j : Agent}
    {iPicks jPicks : List Item}
    (hdom : SequentiallyDominates (profile i) iPicks jPicks)
    (hiPicks : iPicks.toFinset = bundle goods allocation i)
    (hjPicks : jPicks.toFinset = bundle goods allocation j) :
    DoesNotEnvyUpToOneGood profile goods allocation i j := by
  intro hnonempty
  have hlen : 0 < jPicks.length :=
    length_pos_of_toFinset_nonempty hjPicks hnonempty
  let g := jPicks.get ⟨0, hlen⟩
  refine ⟨g, ?_, ?_⟩
  · exact first_mem_of_toFinset_eq hjPicks hlen
  · have htail_le :
        bundleValue (profile i) jPicks.tail.toFinset ≤
          bundleValue (profile i) iPicks.toFinset :=
      bundleValue_tail_toFinset_le (profile i) hdom
    have herase :
        jPicks.toFinset.erase g = jPicks.tail.toFinset := by
      simpa [g] using erase_first_toFinset_eq_tail_toFinset hdom.2.1 hlen
    rw [← hiPicks, ← hjPicks]
    rw [herase]
    exact htail_le

private theorem findIdxNth_lt_of_lt_countPBefore {α : Type*} {xs : List α}
    {p : α → Bool} {n t : Nat}
    (h : n < xs.countPBefore p t) :
    xs.findIdxNth p n < t := by
  have hncount : n < xs.countP p :=
    lt_of_lt_of_le h (List.countPBefore_le_countP (xs := xs) (p := p))
  by_contra hnot
  have ht_le : t ≤ xs.findIdxNth p n := Nat.le_of_not_gt hnot
  have hmono :
      xs.countPBefore p t ≤ xs.countPBefore p (xs.findIdxNth p n) :=
    List.countPBefore_mono (xs := xs) (p := p) ht_le
  have hcount :
      xs.countPBefore p (xs.findIdxNth p n) = n :=
    List.countPBefore_findIdxNth_of_lt_countP (xs := xs) (p := p) hncount
  omega

private theorem agent_at_iff_mod [DecidableEq Agent] [DecidableEq Item]
    {profile : Agent → Valuation Item K} {goods : Finset Item}
    {order : List Agent} {picks : List (Agent × Item)}
    (hlen : 0 < order.length) (hcovered : CoveredAgentOrder order)
    (htrace :
      ∀ n (hn : n < picks.length),
        let pick := picks.get ⟨n, hn⟩
        pick.1 = order.get ⟨n % order.length, Nat.mod_lt n hlen⟩ ∧
          pick.2 ∈ remainingItems goods picks n ∧
            ∀ g ∈ remainingItems goods picks n,
              (profile pick.1).value g ≤ (profile pick.1).value pick.2)
    (a : Agent) {t : Nat} (ht : t < picks.length) :
    (picks.get ⟨t, ht⟩).1 = a ↔ t % order.length = order.idxOf a := by
  have ha_mem : a ∈ order := hcovered.2 a
  have hidx_lt : order.idxOf a < order.length := List.idxOf_lt_length_iff.mpr ha_mem
  have hagent :
      (picks.get ⟨t, ht⟩).1 =
        order.get ⟨t % order.length, Nat.mod_lt t hlen⟩ := (htrace t ht).1
  constructor
  · intro hp
    have hget :
        order.get ⟨t % order.length, Nat.mod_lt t hlen⟩ = a := by
      calc
        order.get ⟨t % order.length, Nat.mod_lt t hlen⟩ =
            (picks.get ⟨t, ht⟩).1 := hagent.symm
        _ = a := hp
    have hidx_get :
        order.idxOf (order.get ⟨t % order.length, Nat.mod_lt t hlen⟩) =
          t % order.length :=
      hcovered.1.idxOf_getElem (t % order.length) (Nat.mod_lt t hlen)
    have hidx_a : order.idxOf a = t % order.length := by
      rw [← hget]
      exact hidx_get
    exact hidx_a.symm
  · intro hmod
    calc
      (picks.get ⟨t, ht⟩).1 =
          order.get ⟨t % order.length, Nat.mod_lt t hlen⟩ := hagent
      _ = order.get ⟨order.idxOf a, hidx_lt⟩ := by
          congr
      _ = a := List.getElem_idxOf hidx_lt

private theorem countPBefore_agent_eq_count_mod [DecidableEq Agent] [DecidableEq Item]
    {profile : Agent → Valuation Item K} {goods : Finset Item}
    {order : List Agent} {picks : List (Agent × Item)}
    (hlen : 0 < order.length) (hcovered : CoveredAgentOrder order)
    (htrace :
      ∀ n (hn : n < picks.length),
        let pick := picks.get ⟨n, hn⟩
        pick.1 = order.get ⟨n % order.length, Nat.mod_lt n hlen⟩ ∧
          pick.2 ∈ remainingItems goods picks n ∧
            ∀ g ∈ remainingItems goods picks n,
              (profile pick.1).value g ≤ (profile pick.1).value pick.2)
    (a : Agent) :
    ∀ {t : Nat}, t ≤ picks.length →
      picks.countPBefore (fun p : Agent × Item => decide (p.1 = a)) t =
        Nat.count (fun k => k % order.length = order.idxOf a) t
  | 0, _ => by simp
  | t + 1, htlen => by
      have ht : t < picks.length := Nat.lt_of_succ_le htlen
      have iht : t ≤ picks.length := Nat.le_of_lt ht
      have ih := countPBefore_agent_eq_count_mod hlen hcovered htrace a iht
      rw [List.countPBefore_eq_countP_take]
      rw [← List.take_concat_get' picks t ht]
      simp only [List.countP_append, List.countP_singleton, Bool.decide_eq_true,
        List.countPBefore_eq_countP_take] at ih ⊢
      rw [ih, Nat.count_succ]
      have hiff := agent_at_iff_mod hlen hcovered htrace a ht
      by_cases hp : (picks[t]).1 = a
      · have hpget : (picks.get ⟨t, ht⟩).1 = a := by
          simpa using hp
        have hm : t % order.length = order.idxOf a := hiff.mp hpget
        simp [hp, hm]
      · have hm : ¬ t % order.length = order.idxOf a := by
          intro hm
          have hpget : (picks.get ⟨t, ht⟩).1 = a := hiff.mpr hm
          exact hp (by simpa using hpget)
        simp [hp, hm]

private theorem count_mod_at_current_ge [DecidableEq Agent]
    {order : List Agent} (hlen : 0 < order.length) (hcovered : CoveredAgentOrder order)
    (i j : Agent) {t : Nat}
    (hjt : t % order.length = order.idxOf j) :
    Nat.count (fun k => k % order.length = order.idxOf i) t ≥
      Nat.count (fun k => k % order.length = order.idxOf j) t := by
  have hi_mem : i ∈ order := hcovered.2 i
  have hj_mem : j ∈ order := hcovered.2 j
  have hi_lt : order.idxOf i < order.length := List.idxOf_lt_length_iff.mpr hi_mem
  have hj_lt : order.idxOf j < order.length := List.idxOf_lt_length_iff.mpr hj_mem
  have hi_mod : order.idxOf i % order.length = order.idxOf i :=
    Nat.mod_eq_of_lt hi_lt
  have hj_mod : order.idxOf j % order.length = order.idxOf j :=
    Nat.mod_eq_of_lt hj_lt
  have hci :
      Nat.count (fun k => k % order.length = order.idxOf i) t =
        t / order.length +
          if order.idxOf i < t % order.length then 1 else 0 := by
    simpa [Nat.ModEq, hi_mod] using
      (Nat.count_modEq_card (b := t) (r := order.length) hlen (order.idxOf i))
  have hcj :
      Nat.count (fun k => k % order.length = order.idxOf j) t =
        t / order.length := by
    have hbase :
        Nat.count (fun k => k ≡ order.idxOf j [MOD order.length]) t =
          t / order.length := by
      rw [Nat.count_modEq_card (b := t) (r := order.length) hlen (order.idxOf j)]
      simp [hj_mod, hjt]
    simpa [Nat.ModEq, hj_mod] using hbase
  rw [hci, hcj]
  omega

private theorem filtered_shifted_domination [DecidableEq Agent] [DecidableEq Item]
    {profile : Agent → Valuation Item K} {goods : Finset Item}
    {order : List Agent} {picks : List (Agent × Item)}
    (hlog : PickLogRoundRobin profile goods order picks)
    (i j : Agent) :
    ∀ n (hj : n + 1 < (agentItems j picks).length),
      ∃ hi : n < (agentItems i picks).length,
        (profile i).value ((agentItems j picks).get ⟨n + 1, hj⟩) ≤
          (profile i).value ((agentItems i picks).get ⟨n, hi⟩) := by
  intro n hj
  rcases hlog with ⟨hlen, hcovered, hnodup, hpicked, htrace⟩
  let Pi : Agent × Item → Bool := fun p => decide (p.1 = i)
  let Pj : Agent × Item → Bool := fun p => decide (p.1 = j)
  have hcountj : n + 1 < picks.countP Pj := by
    simpa [agentItems, Pj, List.countP_eq_length_filter] using hj
  let tj := picks.findIdxNth Pj (n + 1)
  have htj_lt : tj < picks.length := List.findIdxNth_lt_length_of_lt_countP hcountj
  have hpj : (picks.get ⟨tj, htj_lt⟩).1 = j := by
    have hpos := List.pos_findIdxNth_getElem (xs := picks) (p := Pj) (n := n + 1)
      (h := htj_lt)
    exact of_decide_eq_true (by simpa [Pj, tj] using hpos)
  have hjmod : tj % order.length = order.idxOf j :=
    (agent_at_iff_mod hlen hcovered htrace j htj_lt).mp hpj
  have hbefore_j :
      picks.countPBefore Pj tj = n + 1 :=
    List.countPBefore_findIdxNth_of_lt_countP (xs := picks) (p := Pj) hcountj
  have hbefore_i_ge :
      n + 1 ≤ picks.countPBefore Pi tj := by
    have hci :=
      countPBefore_agent_eq_count_mod hlen hcovered htrace i (Nat.le_of_lt htj_lt)
    have hcj :=
      countPBefore_agent_eq_count_mod hlen hcovered htrace j (Nat.le_of_lt htj_lt)
    have hge :=
      count_mod_at_current_ge (order := order) hlen hcovered i j hjmod
    rw [hci]
    rw [hcj] at hbefore_j
    exact hbefore_j ▸ hge
  have hi_count : n < picks.countP Pi := by
    have hle := List.countPBefore_le_countP (xs := picks) (p := Pi) (i := tj)
    omega
  let si := picks.findIdxNth Pi n
  have hsi_lt : si < picks.length := List.findIdxNth_lt_length_of_lt_countP hi_count
  have hsi_tj : si < tj := by
    exact findIdxNth_lt_of_lt_countPBefore
      (xs := picks) (p := Pi) (n := n) (t := tj) (by omega)
  have hpi : (picks.get ⟨si, hsi_lt⟩).1 = i := by
    have hpos := List.pos_findIdxNth_getElem (xs := picks) (p := Pi) (n := n)
      (h := hsi_lt)
    exact of_decide_eq_true (by simpa [Pi, si] using hpos)
  have hremain :
      (picks.get ⟨tj, htj_lt⟩).2 ∈ remainingItems goods picks si := by
    have hgoods : (picks.get ⟨tj, htj_lt⟩).2 ∈ goods := by
      rw [← hpicked]
      rw [pickedItems, List.mem_toFinset]
      exact List.mem_map.mpr ⟨picks.get ⟨tj, htj_lt⟩, List.get_mem picks ⟨tj, htj_lt⟩, rfl⟩
    have hnot_prefix :
        (picks.get ⟨tj, htj_lt⟩).2 ∉ ((picks.take si).map Prod.snd).toFinset := by
      intro hmem
      simp only [List.mem_toFinset, List.mem_map] at hmem
      rcases hmem with ⟨p, hp_mem, hp_item⟩
      rcases List.exists_mem_iff_get.mp ⟨p, hp_mem, rfl⟩ with ⟨r, hr⟩
      have hr_lt_si : (r : Nat) < si := by
        have : (r : Nat) < (picks.take si).length := r.isLt
        have hlen_take : (picks.take si).length = si := by
          simp [Nat.le_of_lt hsi_lt]
        simpa [hlen_take] using this
      have hr_global_lt : (r : Nat) < picks.length := lt_trans hr_lt_si hsi_lt
      have hget_r : picks.get ⟨r, hr_global_lt⟩ = p := by
        have htake_get :
            (picks.take si).get r = picks.get ⟨r, hr_global_lt⟩ := by
          simp [List.get_eq_getElem, hr_lt_si]
        exact htake_get.symm.trans hr.symm
      have hitem_eq :
          (picks.map Prod.snd).get ⟨r, by simpa using hr_global_lt⟩ =
            (picks.map Prod.snd).get ⟨tj, by simpa using htj_lt⟩ := by
        calc
          (picks.map Prod.snd).get ⟨r, by simpa using hr_global_lt⟩ =
              (picks.get ⟨r, hr_global_lt⟩).2 := by
            simp
          _ = p.2 := congrArg Prod.snd hget_r
          _ = (picks.get ⟨tj, htj_lt⟩).2 := hp_item
          _ = (picks.map Prod.snd).get ⟨tj, by simpa using htj_lt⟩ := by
            simp
      have hidx_eq : (r : Nat) = tj := by
        exact congrArg Fin.val ((hnodup.get_inj_iff).mp hitem_eq)
      omega
    simpa [remainingItems] using And.intro hgoods hnot_prefix
  have hbest := (htrace si hsi_lt).2.2 (picks.get ⟨tj, htj_lt⟩).2 hremain
  have hbest_i :
      (profile i).value (picks.get ⟨tj, htj_lt⟩).2 ≤
        (profile i).value (picks.get ⟨si, hsi_lt⟩).2 := by
    rw [hpi] at hbest
    exact hbest
  have hi_len : n < (agentItems i picks).length := by
    simpa [agentItems, Pi, List.countP_eq_length_filter] using hi_count
  refine ⟨hi_len, ?_⟩
  have hget_i :
      (agentItems i picks).get ⟨n, hi_len⟩ = (picks.get ⟨si, hsi_lt⟩).2 := by
    have hfilter :
        (picks.filter Pi).get ⟨n, by simpa [agentItems, Pi] using hi_len⟩ =
          picks.get ⟨si, hsi_lt⟩ := by
      have hfinds :
          (picks.findIdxs Pi).get
              ⟨n, by simpa [List.length_findIdxs, hi_count] using hi_count⟩ = si := by
        simpa [si] using
          (List.getElem_findIdxs_eq_findIdxNth (xs := picks) (p := Pi)
            (n := n) (h := by simpa [List.length_findIdxs, hi_count] using hi_count))
      have hfilter0 :=
        (List.getElem_filter_eq_getElem_getElem_findIdxs (xs := picks) (p := Pi)
          (i := n) (h := by simpa [List.countP_eq_length_filter, Pi] using hi_count))
      have hfinds' :
          (picks.findIdxs Pi)[n]'(by
            simpa [List.length_findIdxs, hi_count] using hi_count) = si := by
        simpa [List.get_eq_getElem] using hfinds
      simpa [si, hfinds'] using hfilter0
    simpa [agentItems, Pi] using congrArg Prod.snd hfilter
  have hget_j :
      (agentItems j picks).get ⟨n + 1, hj⟩ = (picks.get ⟨tj, htj_lt⟩).2 := by
    have hfilter :
        (picks.filter Pj).get ⟨n + 1, by simpa [agentItems, Pj] using hj⟩ =
          picks.get ⟨tj, htj_lt⟩ := by
      have hfinds :
          (picks.findIdxs Pj).get
              ⟨n + 1, by simpa [List.length_findIdxs, hcountj] using hcountj⟩ = tj := by
        simpa [tj] using
          (List.getElem_findIdxs_eq_findIdxNth (xs := picks) (p := Pj)
            (n := n + 1) (h := by simpa [List.length_findIdxs, hcountj] using hcountj))
      have hfilter0 :=
        (List.getElem_filter_eq_getElem_getElem_findIdxs (xs := picks) (p := Pj)
          (i := n + 1) (h := by simpa [List.countP_eq_length_filter, Pj] using hcountj))
      have hfinds' :
          (picks.findIdxs Pj)[n + 1]'(by
            simpa [List.length_findIdxs, hcountj] using hcountj) = tj := by
        simpa [List.get_eq_getElem] using hfinds
      simpa [tj, hfinds'] using hfilter0
    simpa [agentItems, Pj] using congrArg Prod.snd hfilter
  calc
    (profile i).value ((agentItems j picks).get ⟨n + 1, hj⟩) =
        (profile i).value (picks.get ⟨tj, htj_lt⟩).2 := by
      rw [hget_j]
    _ ≤ (profile i).value (picks.get ⟨si, hsi_lt⟩).2 := hbest_i
    _ = (profile i).value ((agentItems i picks).get ⟨n, hi_len⟩) := by
      rw [hget_i]

private theorem picklog_sequentiallyDominates [DecidableEq Agent] [DecidableEq Item]
    {profile : Agent → Valuation Item K} {goods : Finset Item}
    {order : List Agent} {picks : List (Agent × Item)}
    (hlog : PickLogRoundRobin profile goods order picks) (i j : Agent) :
    SequentiallyDominates (profile i) (agentItems i picks) (agentItems j picks) := by
  rcases hlog with ⟨hlen, hcovered, hnodup, hpicked, htrace⟩
  have hlog' : PickLogRoundRobin profile goods order picks :=
    ⟨hlen, hcovered, hnodup, hpicked, htrace⟩
  exact ⟨agentItems_nodup (a := i) hnodup,
    agentItems_nodup (a := j) hnodup,
    filtered_shifted_domination hlog' i j⟩

private theorem picklog_ef1 [DecidableEq Agent] [DecidableEq Item]
    {profile : Agent → Valuation Item K} {goods : Finset Item}
    {order : List Agent} {allocation : Allocation Agent Item}
    {picks : List (Agent × Item)}
    (hlog : PickLogRoundRobin profile goods order picks)
    (hmatch : PickLogMatchesAllocation allocation picks) :
    EnvyFreeUpToOneGood profile goods allocation := by
  intro i j
  exact sequentiallyDominates_pair_EF1_core
    (picklog_sequentiallyDominates hlog i j)
    (agentItems_toFinset_eq_bundle hlog hmatch i)
    (agentItems_toFinset_eq_bundle hlog hmatch j)

abbrev TwoAgent := Fin 2

abbrev OneGoodItem := Fin 1

def oneGoodSet : Finset OneGoodItem :=
  {(0 : OneGoodItem)}

def oneGoodPositiveValuation : Valuation OneGoodItem K :=
  { value := fun _ => 1
    nonneg := by intro _; norm_num }

def twoAgentOneGoodProfile : TwoAgent → Valuation OneGoodItem K :=
  fun _ => oneGoodPositiveValuation

def oneGoodToAgent0 : Allocation TwoAgent OneGoodItem :=
  { owner := fun _ => 0 }

theorem iso_lemma1_roundRobin_allocation_exists : ∀ {Agent Item : Type*} [DecidableEq Agent] [DecidableEq Item]
        {profile : Agent → Valuation Item K} {goods : Finset Item}
        {order : List Agent},
      CoveredAgentOrder order → 0 < order.length →
        ∃ allocation : Allocation Agent Item,
          RoundRobin profile goods order allocation := by
  intro Agent Item _ _ profile goods order hcovered hlen
  classical
  obtain ⟨picks, hnodup, hpicked, htrace⟩ :=
    exists_greedy_roundRobin_suffix (profile := profile) (order := order) hlen goods 0
  let defaultAgent : Agent := order.get ⟨0, hlen⟩
  let allocation : Allocation Agent Item :=
    { owner := fun g =>
        if h : ∃ a : Agent, (a, g) ∈ picks then Classical.choose h else defaultAgent }
  refine ⟨allocation, ?_⟩
  refine ⟨picks, ?_, ?_⟩
  · refine ⟨hlen, hcovered, hnodup, hpicked, ?_⟩
    intro n hn
    simpa [remainingItems, Nat.zero_add] using htrace n hn
  · intro n hn
    let pick := picks.get ⟨n, hn⟩
    have hmem : pick ∈ picks := List.get_mem picks ⟨n, hn⟩
    have hex : ∃ a : Agent, (a, pick.2) ∈ picks := ⟨pick.1, hmem⟩
    have hchoose :
        Classical.choose hex = pick.1 := by
      have hchoose_mem : (Classical.choose hex, pick.2) ∈ picks :=
        Classical.choose_spec hex
      exact owner_eq_of_mem_of_snd_nodup hnodup hchoose_mem hmem
    dsimp [allocation]
    change (if h : ∃ a : Agent, (a, pick.2) ∈ picks then Classical.choose h else defaultAgent) =
      pick.1
    rw [dif_pos hex]
    exact hchoose

theorem iso_lemma2_roundRobin_ef1 : ∀ {Agent Item : Type*} [DecidableEq Agent] [DecidableEq Item]
        {profile : Agent → Valuation Item K} {goods : Finset Item}
        {order : List Agent} {allocation : Allocation Agent Item},
      RoundRobin profile goods order allocation →
        EnvyFreeUpToOneGood profile goods allocation := by
  intro Agent Item _ _ profile goods order allocation hrr
  rcases hrr with ⟨picks, hlog, hmatch⟩
  exact picklog_ef1 hlog hmatch

theorem no_EnvyFree_two_agents_one_good (allocation : Allocation TwoAgent OneGoodItem) :
    ¬ EnvyFree (twoAgentOneGoodProfile (K := K)) oneGoodSet allocation := by
  intro hEF
  have howner : allocation.owner (0 : OneGoodItem) = 0 ∨
      allocation.owner (0 : OneGoodItem) = 1 := by
    let a := allocation.owner (0 : OneGoodItem)
    have ha : a.val = 0 ∨ a.val = 1 := by
      omega
    rcases ha with ha | ha
    · left
      exact Fin.ext ha
    · right
      exact Fin.ext ha
  rcases howner with h0 | h1
  · have henvy :
        Envies (twoAgentOneGoodProfile (K := K)) oneGoodSet allocation
          (1 : TwoAgent) (0 : TwoAgent) := by
      have hloser : bundle oneGoodSet allocation (1 : TwoAgent) = ∅ := by
        ext g
        fin_cases g
        simp [bundle, oneGoodSet, h0]
      have hwinner : bundle oneGoodSet allocation (0 : TwoAgent) = {(0 : OneGoodItem)} := by
        ext g
        fin_cases g
        simp [bundle, oneGoodSet, h0]
      simp [Envies, bundleValue, twoAgentOneGoodProfile,
        oneGoodPositiveValuation, hloser, hwinner]
    exact (hEF (1 : TwoAgent) (0 : TwoAgent)) henvy
  · have henvy :
        Envies (twoAgentOneGoodProfile (K := K)) oneGoodSet allocation
          (0 : TwoAgent) (1 : TwoAgent) := by
      have hloser : bundle oneGoodSet allocation (0 : TwoAgent) = ∅ := by
        ext g
        fin_cases g
        simp [bundle, oneGoodSet, h1]
      have hwinner : bundle oneGoodSet allocation (1 : TwoAgent) = {(0 : OneGoodItem)} := by
        ext g
        fin_cases g
        simp [bundle, oneGoodSet, h1]
      simp [Envies, bundleValue, twoAgentOneGoodProfile,
        oneGoodPositiveValuation, hloser, hwinner]
    exact (hEF (0 : TwoAgent) (1 : TwoAgent)) henvy

theorem EnvyFree_implies_EnvyFreeUpToOneGood_local :
    ∀ {Agent Item : Type*} [DecidableEq Agent] [DecidableEq Item]
        {profile : Agent → Valuation Item K} {goods : Finset Item}
        {allocation : Allocation Agent Item},
      EnvyFree profile goods allocation →
        EnvyFreeUpToOneGood profile goods allocation := by
  intro Agent Item _ _ profile goods allocation hEF i j hnonempty
  classical
  rcases hnonempty with ⟨g, hg⟩
  refine ⟨g, hg, ?_⟩
  have hnot := hEF i j
  change ¬ bundleValue (profile i) (bundle goods allocation i) <
      bundleValue (profile i) (bundle goods allocation j) at hnot
  have hfull_le_self : bundleValue (profile i) (bundle goods allocation j) ≤
      bundleValue (profile i) (bundle goods allocation i) := le_of_not_gt hnot
  have herase_le_full : bundleValue (profile i) ((bundle goods allocation j).erase g) ≤
      bundleValue (profile i) (bundle goods allocation j) := by
    unfold bundleValue
    exact Finset.sum_le_sum_of_subset_of_nonneg (Finset.erase_subset g (bundle goods allocation j))
      (by intro x _ _; exact (profile i).nonneg x)
  exact le_trans herase_le_full hfull_le_self

theorem oneGoodToAgent0_EF1 :
    EnvyFreeUpToOneGood (twoAgentOneGoodProfile (K := K)) oneGoodSet oneGoodToAgent0 := by
  intro i j hnonempty
  fin_cases j
  · refine ⟨(0 : OneGoodItem), ?_, ?_⟩
    · simp [bundle, oneGoodSet, oneGoodToAgent0]
    · fin_cases i <;>
        simp [bundleValue, bundle, oneGoodSet, oneGoodToAgent0,
          twoAgentOneGoodProfile, oneGoodPositiveValuation]
  · exfalso
    simp [bundle, oneGoodSet, oneGoodToAgent0] at hnonempty

theorem ef1_attainable_relaxation_via_roundRobin : (∀ allocation : Allocation TwoAgent OneGoodItem,
      ¬ EnvyFree (twoAgentOneGoodProfile (K := K)) oneGoodSet allocation) ∧
    (∀ {Agent Item : Type*} [DecidableEq Agent] [DecidableEq Item]
        {profile : Agent → Valuation Item K} {goods : Finset Item}
        {order : List Agent},
      CoveredAgentOrder order → 0 < order.length →
        ∃ allocation : Allocation Agent Item,
          RoundRobin profile goods order allocation ∧
            EnvyFreeUpToOneGood profile goods allocation) ∧
    (∀ {Agent Item : Type*} [DecidableEq Agent] [DecidableEq Item]
        {profile : Agent → Valuation Item K} {goods : Finset Item}
        {allocation : Allocation Agent Item},
      EnvyFree profile goods allocation →
        EnvyFreeUpToOneGood profile goods allocation) ∧
    (EnvyFreeUpToOneGood (twoAgentOneGoodProfile (K := K)) oneGoodSet oneGoodToAgent0 ∧
      ¬ EnvyFree (twoAgentOneGoodProfile (K := K)) oneGoodSet oneGoodToAgent0) := by
  refine ⟨no_EnvyFree_two_agents_one_good, ?_,
    EnvyFree_implies_EnvyFreeUpToOneGood_local, ?_⟩
  · intro Agent Item _ _ profile goods order hcovered hlen
    obtain ⟨allocation, hrr⟩ :=
      iso_lemma1_roundRobin_allocation_exists (profile := profile) (goods := goods)
        (order := order) hcovered hlen
    exact ⟨allocation, hrr, iso_lemma2_roundRobin_ef1 hrr⟩
  · exact ⟨oneGoodToAgent0_EF1,
      no_EnvyFree_two_agents_one_good (K := K) oneGoodToAgent0⟩
