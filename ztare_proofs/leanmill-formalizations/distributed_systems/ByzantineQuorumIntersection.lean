/-
LeanMill campaign provenance — byzantine_threshold_quorum_safe_available_iff_and_tight_witness
The theorem(s) below are the VERBATIM machine-checked closure. This header is GENERATED from run
telemetry (run_tag=notes_bft_quorum_intersection_blueprint_0701T0602) by promote_campaign_artifact.py — not hand-authored.

  outcome     : closed · faithful · axioms propext, Classical.choice, Quot.sound
  domain      : formalization-nonmath
  time        : wall 804.16s launch→close = formalize 596.88s (theory+statement+firewall) + prove 207.28s (proof search) · prove p50 207.28s p95 207.28s
  compute     : cost-to-closure 174.31s mean · 174.31s total
  yield       : 1/3 attempts closed (1 failed)
  phases      : 606s leaf.dispatch · 188.4s pool · 94.8s formalize · 24.9s native · 1.8s govern.mnc
  reuse       : cited 0 banked rung(s)
  moves       : proposer_pool×1 · native_hammer×1 · claude_warm×1
  milestone   : campaign family 'notes_bft_quorum_intersection_blueprint_0701T0602' — 1 run(s) · REAL elapsed (launch→last) 824.5s (~14 min) = formalize 617.2s + prove/other · active-solve 174.3s · 1 closures [launch→last is the honest wall]
     - notes_bft_quorum_intersection_blueprint_0701T0602: 1/3 closed · elapsed 824.45s (~13.7 min)
-/
import Mathlib

-- Natural-language specification (blueprint): blueprints/bft_quorum_intersection_blueprint.md
-- Read the blueprint to check the faithfulness boundary — the guarantee stops where the English intent is argued, not proved.

/-!
# Byzantine threshold quorum substrate

This file is intentionally foundational: it defines the threshold quorum
vocabulary over `Fin n`, pins each definition to elementary `Finset`/`Nat`
primitives, and proves the counting bridge from the numeric threshold
condition to the actual set-level common-correct-node fact.

Definition trial notes.

* Faults: a bundled adversary structure was rejected for now because the
  campaign quantifies over all fault sets; the workable selected shape is the
  predicate `FaultAdmissible n f F := F.card ≤ f`.
* Quorums: a bundled quorum subtype would make every theorem carry coercions.
  The selected shape is the predicate `ThresholdQuorum n q Q := q ≤ Q.card`,
  with `ThresholdQuorumSystem` as the corresponding `Set` family.
* Safety and availability: selected as direct predicates over all
  `Q₁ Q₂ F`, so the universal quantifiers are part of the definition rather
  than compatibility hypotheses.
-/

namespace ByzantineQuorumIntersection

open Finset

/-- Nodes are finite indices. -/
abbrev Nodes (n : ℕ) := Fin n

/-- A quorum/fault set over `n` nodes. -/
abbrev NodeSet (n : ℕ) := Finset (Nodes n)

/-- An at-most-`f` faulty set. -/
def FaultAdmissible (n f : ℕ) (F : NodeSet n) : Prop :=
  F.card ≤ f

/-- A node is correct with respect to a concrete faulty set. -/
def CorrectNode {n : ℕ} (F : NodeSet n) (x : Nodes n) : Prop :=
  x ∉ F

/-- A concrete quorum for threshold `q`. -/
def ThresholdQuorum (n q : ℕ) (Q : NodeSet n) : Prop :=
  q ≤ Q.card

/-- The size-`q` threshold quorum family. -/
def ThresholdQuorumSystem (n q : ℕ) : Set (NodeSet n) :=
  {Q | ThresholdQuorum n q Q}

/--
Set-level threshold safety: every two threshold quorums share a node outside
every admissible faulty set.
-/
def ThresholdSafe (n f q : ℕ) : Prop :=
  ∀ Q₁ Q₂ : NodeSet n,
    ThresholdQuorum n q Q₁ →
    ThresholdQuorum n q Q₂ →
    ∀ F : NodeSet n,
      FaultAdmissible n f F →
      ((Q₁ ∩ Q₂) \ F).Nonempty

/--
Set-level availability: after removing any admissible faulty set, some
threshold quorum remains disjoint from it.
-/
def ThresholdAvailable (n f q : ℕ) : Prop :=
  ∀ F : NodeSet n,
    FaultAdmissible n f F →
    ∃ Q : NodeSet n, ThresholdQuorum n q Q ∧ Disjoint Q F

/-- Numeric side condition sufficient for threshold safety. -/
def ThresholdSafeBound (n f q : ℕ) : Prop :=
  n + f + 1 ≤ 2 * q

/-- Numeric side condition expressing that a correct quorum fits. -/
def ThresholdAvailableBound (n f q : ℕ) : Prop :=
  q + f ≤ n

/-- Numeric simultaneous safe-and-available region. -/
def ThresholdSafeAndAvailableBound (n f q : ℕ) : Prop :=
  ThresholdSafeBound n f q ∧ ThresholdAvailableBound n f q

theorem anchor_FaultAdmissible_iff_card_le
    {n f : ℕ} (F : NodeSet n) :
    FaultAdmissible n f F ↔ F.card ≤ f :=
  Iff.rfl

theorem anchor_CorrectNode_iff_not_mem
    {n : ℕ} (F : NodeSet n) (x : Nodes n) :
    CorrectNode F x ↔ x ∉ F :=
  Iff.rfl

theorem anchor_ThresholdQuorum_iff_card_ge
    {n q : ℕ} (Q : NodeSet n) :
    ThresholdQuorum n q Q ↔ q ≤ Q.card :=
  Iff.rfl

theorem anchor_ThresholdQuorumSystem_mem_iff
    {n q : ℕ} (Q : NodeSet n) :
    Q ∈ ThresholdQuorumSystem n q ↔ ThresholdQuorum n q Q :=
  Iff.rfl

theorem anchor_ThresholdSafe_iff_common_correct_node
    {n f q : ℕ} :
    ThresholdSafe n f q ↔
      ∀ Q₁ Q₂ : NodeSet n,
        q ≤ Q₁.card →
        q ≤ Q₂.card →
        ∀ F : NodeSet n,
          F.card ≤ f →
          ((Q₁ ∩ Q₂) \ F).Nonempty :=
  Iff.rfl

theorem anchor_ThresholdAvailable_iff_disjoint_quorum
    {n f q : ℕ} :
    ThresholdAvailable n f q ↔
      ∀ F : NodeSet n,
        F.card ≤ f →
        ∃ Q : NodeSet n, q ≤ Q.card ∧ Disjoint Q F :=
  Iff.rfl

theorem anchor_ThresholdSafeBound_iff_nat
    {n f q : ℕ} :
    ThresholdSafeBound n f q ↔ n + f + 1 ≤ 2 * q :=
  Iff.rfl

theorem anchor_ThresholdAvailableBound_iff_nat
    {n f q : ℕ} :
    ThresholdAvailableBound n f q ↔ q + f ≤ n :=
  Iff.rfl

theorem witness_FaultAdmissible_empty
    (n f : ℕ) :
    FaultAdmissible n f (∅ : NodeSet n) := by
  simp [FaultAdmissible]

theorem witness_ThresholdQuorumSystem_nonvacuous_of_le_nodes
    {n q : ℕ} (hq : q ≤ n) :
    (ThresholdQuorumSystem n q).Nonempty := by
  refine ⟨Finset.univ, ?_⟩
  simp [ThresholdQuorumSystem, ThresholdQuorum, hq]

theorem thresholdQuorum_univ_iff
    {n q : ℕ} :
    ThresholdQuorum n q (Finset.univ : NodeSet n) ↔ q ≤ n := by
  simp [ThresholdQuorum]

theorem thresholdQuorum_empty_iff
    {n q : ℕ} :
    ThresholdQuorum n q (∅ : NodeSet n) ↔ q = 0 := by
  simp [ThresholdQuorum]

theorem card_sdiff_pos_of_card_lt
    {α : Type*} [DecidableEq α] {A B : Finset α}
    (h : B.card < A.card) :
    0 < (A \ B).card := by
  have hInterLe : (A ∩ B).card ≤ B.card := by
    exact Finset.card_le_card (by intro x hx; exact (Finset.mem_inter.mp hx).2)
  have hInterLt : (A ∩ B).card < A.card := lt_of_le_of_lt hInterLe h
  have hsplit := Finset.card_sdiff_add_card_inter A B
  omega

theorem sdiff_nonempty_of_card_lt
    {α : Type*} [DecidableEq α] {A B : Finset α}
    (h : B.card < A.card) :
    (A \ B).Nonempty := by
  exact Finset.card_pos.mp (card_sdiff_pos_of_card_lt h)

theorem card_inter_gt_faults_of_threshold
    {n f q : ℕ}
    (hsafe : ThresholdSafeBound n f q)
    {Q₁ Q₂ : NodeSet n}
    (hQ₁ : ThresholdQuorum n q Q₁)
    (hQ₂ : ThresholdQuorum n q Q₂)
    {F : NodeSet n}
    (hF : FaultAdmissible n f F) :
    F.card < (Q₁ ∩ Q₂).card := by
  change n + f + 1 ≤ 2 * q at hsafe
  change q ≤ Q₁.card at hQ₁
  change q ≤ Q₂.card at hQ₂
  change F.card ≤ f at hF
  have hUnionLe : (Q₁ ∪ Q₂).card ≤ n := by
    simpa using (Finset.card_le_univ (Q₁ ∪ Q₂))
  have hInterUnion :=
    Finset.card_inter_add_card_union Q₁ Q₂
  have hCardLe : Q₁.card + Q₂.card ≤ (Q₁ ∩ Q₂).card + n := by
    calc
      Q₁.card + Q₂.card = (Q₁ ∩ Q₂).card + (Q₁ ∪ Q₂).card := by
        exact hInterUnion.symm
      _ ≤ (Q₁ ∩ Q₂).card + n := by
        exact Nat.add_le_add_left hUnionLe _
  have hTwoQ : 2 * q ≤ Q₁.card + Q₂.card := by
    omega
  have hFaultPlus : F.card + 1 ≤ (Q₁ ∩ Q₂).card := by
    omega
  omega

/--
The load-bearing set-level safety lemma.  The proof goes through the
intersection cardinality forced by `card_inter_add_card_union`, then uses the
cardinality split for set difference to produce an actual node outside `F`.
-/
theorem thresholdSafe_of_safeBound
    {n f q : ℕ}
    (hsafe : ThresholdSafeBound n f q) :
    ThresholdSafe n f q := by
  intro Q₁ Q₂ hQ₁ hQ₂ F hF
  exact sdiff_nonempty_of_card_lt
    (card_inter_gt_faults_of_threshold hsafe hQ₁ hQ₂ hF)

theorem thresholdAvailable_of_availableBound
    {n f q : ℕ}
    (hfit : ThresholdAvailableBound n f q) :
    ThresholdAvailable n f q := by
  intro F hF
  refine ⟨Finset.univ \ F, ?_, ?_⟩
  · have hcard : (Finset.univ \ F).card = n - F.card := by
      rw [Finset.card_sdiff]
      simp
    rw [ThresholdQuorum, hcard]
    apply Nat.le_sub_of_add_le
    change q + f ≤ n at hfit
    change F.card ≤ f at hF
    omega
  · simpa [disjoint_comm] using
      (Finset.disjoint_sdiff (s := F) (t := (Finset.univ : NodeSet n)))

theorem exists_thresholdSafeBound_and_availableBound_iff
    (n f : ℕ) :
    (∃ q : ℕ, ThresholdSafeAndAvailableBound n f q) ↔
      3 * f + 1 ≤ n := by
  constructor
  · rintro ⟨q, hsafe, havail⟩
    dsimp [ThresholdSafeAndAvailableBound,
      ThresholdSafeBound, ThresholdAvailableBound] at hsafe havail
    omega
  · intro h
    refine ⟨n - f, ?_, ?_⟩
    · dsimp [ThresholdSafeAndAvailableBound, ThresholdSafeBound]
      omega
    · dsimp [ThresholdAvailableBound]
      omega

theorem exists_safe_set_and_available_bound_of_three_f_plus_one_le
    {n f : ℕ} (h : 3 * f + 1 ≤ n) :
    ∃ q : ℕ, ThresholdSafe n f q ∧ ThresholdAvailableBound n f q := by
  rcases (exists_thresholdSafeBound_and_availableBound_iff n f).2 h with
    ⟨q, hsafe, havail⟩
  exact ⟨q, thresholdSafe_of_safeBound hsafe, havail⟩

theorem no_safe_available_bound_at_three_f
    {f : ℕ} (hf : 1 ≤ f) :
    ¬ ∃ q : ℕ, ThresholdSafeAndAvailableBound (3 * f) f q := by
  intro h
  have hbound :=
    (exists_thresholdSafeBound_and_availableBound_iff (3 * f) f).1 h
  have hfpos : 0 < f := Nat.lt_of_lt_of_le Nat.zero_lt_one hf
  have hnot : ¬ 3 * f + 1 ≤ 3 * f := by omega
  exact hnot hbound

/-- Lower concrete quorum at the tight point: nodes `< 2f+1`. -/
def tightLowerQuorum (f : ℕ) : NodeSet (3 * f + 1) :=
  Finset.univ.filter (fun x : Fin (3 * f + 1) => (x : ℕ) < 2 * f + 1)

/-- Upper concrete quorum at the tight point: nodes `≥ f`. -/
def tightUpperQuorum (f : ℕ) : NodeSet (3 * f + 1) :=
  Finset.univ.filter (fun x : Fin (3 * f + 1) => f ≤ (x : ℕ))

theorem anchor_tightLowerQuorum_mem_iff
    {f : ℕ} (x : Fin (3 * f + 1)) :
    x ∈ tightLowerQuorum f ↔ (x : ℕ) < 2 * f + 1 := by
  simp [tightLowerQuorum]

theorem anchor_tightUpperQuorum_mem_iff
    {f : ℕ} (x : Fin (3 * f + 1)) :
    x ∈ tightUpperQuorum f ↔ f ≤ (x : ℕ) := by
  simp [tightUpperQuorum]

theorem tightLowerQuorum_card
    (f : ℕ) :
    (tightLowerQuorum f).card = 2 * f + 1 := by
  have hcard :
      (Finset.univ : Finset (Fin (2 * f + 1))).card =
        (tightLowerQuorum f).card := by
    refine Finset.card_bij
      (fun i _hi =>
        (⟨(i : ℕ), by
          have hiLt := i.isLt
          omega⟩ : Fin (3 * f + 1)))
      ?hmem ?hinj ?hsurj
    · intro i _hi
      simp [tightLowerQuorum]
      exact Nat.le_of_lt_succ i.isLt
    · intro a _ha b _hb hab
      apply Fin.ext
      simpa using congrArg (fun x : Fin (3 * f + 1) => (x : ℕ)) hab
    · intro b hb
      have hbLt : (b : ℕ) < 2 * f + 1 := by
        simpa [tightLowerQuorum] using hb
      refine ⟨⟨(b : ℕ), hbLt⟩, by simp, ?_⟩
      apply Fin.ext
      simp
  simpa using hcard.symm

theorem tightUpperQuorum_card
    (f : ℕ) :
    (tightUpperQuorum f).card = 2 * f + 1 := by
  have hcard :
      (Finset.univ : Finset (Fin (2 * f + 1))).card =
        (tightUpperQuorum f).card := by
    refine Finset.card_bij
      (fun i _hi =>
        (⟨f + (i : ℕ), by
          have hiLt := i.isLt
          omega⟩ : Fin (3 * f + 1)))
      ?hmem ?hinj ?hsurj
    · intro i _hi
      simp [tightUpperQuorum]
    · intro a _ha b _hb hab
      apply Fin.ext
      have hval :=
        congrArg (fun x : Fin (3 * f + 1) => (x : ℕ)) hab
      simp at hval
      omega
    · intro b hb
      have hbGe : f ≤ (b : ℕ) := by
        simpa [tightUpperQuorum] using hb
      have hbLt := b.isLt
      refine ⟨⟨(b : ℕ) - f, by omega⟩, by simp, ?_⟩
      apply Fin.ext
      simp
      omega
  simpa using hcard.symm

theorem tightLowerQuorum_ne_univ
    {f : ℕ} (hf : 1 ≤ f) :
    tightLowerQuorum f ≠ (Finset.univ : NodeSet (3 * f + 1)) := by
  intro h
  let x : Fin (3 * f + 1) :=
    ⟨3 * f, by omega⟩
  have hxUniv : x ∈ (Finset.univ : NodeSet (3 * f + 1)) := by simp
  have hxLower : x ∈ tightLowerQuorum f := by simp [h]
  have hxlt := (anchor_tightLowerQuorum_mem_iff (f := f) x).1 hxLower
  have hxval : (x : ℕ) = 3 * f := rfl
  omega

theorem tightUpperQuorum_ne_univ
    {f : ℕ} (hf : 1 ≤ f) :
    tightUpperQuorum f ≠ (Finset.univ : NodeSet (3 * f + 1)) := by
  intro h
  let x : Fin (3 * f + 1) :=
    ⟨0, by omega⟩
  have hxUniv : x ∈ (Finset.univ : NodeSet (3 * f + 1)) := by simp
  have hxUpper : x ∈ tightUpperQuorum f := by simp [h]
  have hxge := (anchor_tightUpperQuorum_mem_iff (f := f) x).1 hxUpper
  have hxval : (x : ℕ) = 0 := rfl
  omega

theorem tightLowerQuorum_ne_tightUpperQuorum
    {f : ℕ} (hf : 1 ≤ f) :
    tightLowerQuorum f ≠ tightUpperQuorum f := by
  intro h
  let x : Fin (3 * f + 1) :=
    ⟨0, by omega⟩
  have hxLower : x ∈ tightLowerQuorum f := by
    rw [anchor_tightLowerQuorum_mem_iff]
    have hxval : (x : ℕ) = 0 := rfl
    omega
  have hxUpper : x ∈ tightUpperQuorum f := by simpa [h] using hxLower
  have hxge := (anchor_tightUpperQuorum_mem_iff (f := f) x).1 hxUpper
  have hxval : (x : ℕ) = 0 := rfl
  omega

theorem tightQuorum_intersection_survives_faults
    {f : ℕ} (_hf : 1 ≤ f)
    (F : NodeSet (3 * f + 1))
    (hF : FaultAdmissible (3 * f + 1) f F) :
    (((tightLowerQuorum f) ∩ (tightUpperQuorum f)) \ F).Nonempty := by
  have hsafe : ThresholdSafeBound (3 * f + 1) f (2 * f + 1) := by
    dsimp [ThresholdSafeBound]
    omega
  exact thresholdSafe_of_safeBound hsafe
    (Q₁ := tightLowerQuorum f)
    (Q₂ := tightUpperQuorum f)
    (by rw [ThresholdQuorum, tightLowerQuorum_card])
    (by rw [ThresholdQuorum, tightUpperQuorum_card])
    F hF

theorem tightPoint_available
    (f : ℕ) :
    ThresholdAvailable (3 * f + 1) f (2 * f + 1) := by
  apply thresholdAvailable_of_availableBound
  dsimp [ThresholdAvailableBound]
  omega

/--
Bundled non-degenerate tight-point witness.  The concrete quorums are distinct,
proper threshold quorums, and their intersection contains a correct node for
every admissible faulty set.
-/
theorem tightPoint_nonDegenerate_witness
    {f : ℕ} (hf : 1 ≤ f) :
    ∃ Q₁ Q₂ : NodeSet (3 * f + 1),
      Q₁.card = 2 * f + 1 ∧
      Q₂.card = 2 * f + 1 ∧
      Q₁ ≠ Q₂ ∧
      Q₁ ≠ (Finset.univ : NodeSet (3 * f + 1)) ∧
      Q₂ ≠ (Finset.univ : NodeSet (3 * f + 1)) ∧
      (∀ F : NodeSet (3 * f + 1),
        FaultAdmissible (3 * f + 1) f F →
        ((Q₁ ∩ Q₂) \ F).Nonempty) ∧
      ThresholdAvailable (3 * f + 1) f (2 * f + 1) := by
  refine ⟨tightLowerQuorum f, tightUpperQuorum f,
    tightLowerQuorum_card f, tightUpperQuorum_card f,
    tightLowerQuorum_ne_tightUpperQuorum hf,
    tightLowerQuorum_ne_univ hf,
    tightUpperQuorum_ne_univ hf, ?_, tightPoint_available f⟩
  exact tightQuorum_intersection_survives_faults hf

end ByzantineQuorumIntersection

namespace ByzantineQuorumIntersection

/-!
Append-only consolidation: boundary fault blocks for the set-level impossibility
at `n = 3f`.  These are not replacement definitions; they are concrete
sanity witnesses used to rule out a vacuous safe/available reading at the
boundary.
-/

/-- The first `f` nodes inside `Fin (3f)`. -/
def boundaryLowFaults (f : ℕ) : NodeSet (3 * f) :=
  Finset.univ.filter (fun x : Fin (3 * f) => (x : ℕ) < f)

/-- The middle `f` nodes inside `Fin (3f)`. -/
def boundaryMidFaults (f : ℕ) : NodeSet (3 * f) :=
  Finset.univ.filter (fun x : Fin (3 * f) => f ≤ (x : ℕ) ∧ (x : ℕ) < 2 * f)

/-- The last `f` nodes inside `Fin (3f)`. -/
def boundaryHighFaults (f : ℕ) : NodeSet (3 * f) :=
  Finset.univ.filter (fun x : Fin (3 * f) => 2 * f ≤ (x : ℕ))

theorem anchor_boundaryLowFaults_mem_iff
    {f : ℕ} (x : Fin (3 * f)) :
    x ∈ boundaryLowFaults f ↔ (x : ℕ) < f := by
  simp [boundaryLowFaults]

theorem anchor_boundaryMidFaults_mem_iff
    {f : ℕ} (x : Fin (3 * f)) :
    x ∈ boundaryMidFaults f ↔ f ≤ (x : ℕ) ∧ (x : ℕ) < 2 * f := by
  simp [boundaryMidFaults]

theorem anchor_boundaryHighFaults_mem_iff
    {f : ℕ} (x : Fin (3 * f)) :
    x ∈ boundaryHighFaults f ↔ 2 * f ≤ (x : ℕ) := by
  simp [boundaryHighFaults]

theorem boundaryLowFaults_card
    (f : ℕ) :
    (boundaryLowFaults f).card = f := by
  have hcard :
      (Finset.univ : Finset (Fin f)).card = (boundaryLowFaults f).card := by
    refine Finset.card_bij
      (fun i _hi =>
        (⟨(i : ℕ), by
          have hiLt := i.isLt
          omega⟩ : Fin (3 * f)))
      ?hmem ?hinj ?hsurj
    · intro i _hi
      rw [anchor_boundaryLowFaults_mem_iff]
      exact i.isLt
    · intro a _ha b _hb hab
      apply Fin.ext
      simpa using congrArg (fun x : Fin (3 * f) => (x : ℕ)) hab
    · intro b hb
      have hbLt : (b : ℕ) < f :=
        (anchor_boundaryLowFaults_mem_iff (f := f) b).1 hb
      refine ⟨⟨(b : ℕ), hbLt⟩, by simp, ?_⟩
      apply Fin.ext
      simp
  simpa using hcard.symm

theorem boundaryMidFaults_card
    (f : ℕ) :
    (boundaryMidFaults f).card = f := by
  have hcard :
      (Finset.univ : Finset (Fin f)).card = (boundaryMidFaults f).card := by
    refine Finset.card_bij
      (fun i _hi =>
        (⟨f + (i : ℕ), by
          have hiLt := i.isLt
          omega⟩ : Fin (3 * f)))
      ?hmem ?hinj ?hsurj
    · intro i _hi
      rw [anchor_boundaryMidFaults_mem_iff]
      change f ≤ f + (i : ℕ) ∧ f + (i : ℕ) < 2 * f
      have hiLt := i.isLt
      omega
    · intro a _ha b _hb hab
      apply Fin.ext
      have hval :=
        congrArg (fun x : Fin (3 * f) => (x : ℕ)) hab
      simp at hval
      omega
    · intro b hb
      have hbMid :=
        (anchor_boundaryMidFaults_mem_iff (f := f) b).1 hb
      refine ⟨⟨(b : ℕ) - f, by omega⟩, by simp, ?_⟩
      apply Fin.ext
      simp
      omega
  simpa using hcard.symm

theorem boundaryHighFaults_card
    (f : ℕ) :
    (boundaryHighFaults f).card = f := by
  have hcard :
      (Finset.univ : Finset (Fin f)).card = (boundaryHighFaults f).card := by
    refine Finset.card_bij
      (fun i _hi =>
        (⟨2 * f + (i : ℕ), by
          have hiLt := i.isLt
          omega⟩ : Fin (3 * f)))
      ?hmem ?hinj ?hsurj
    · intro i _hi
      rw [anchor_boundaryHighFaults_mem_iff]
      change 2 * f ≤ 2 * f + (i : ℕ)
      omega
    · intro a _ha b _hb hab
      apply Fin.ext
      have hval :=
        congrArg (fun x : Fin (3 * f) => (x : ℕ)) hab
      simp at hval
      omega
    · intro b hb
      have hbHigh :=
        (anchor_boundaryHighFaults_mem_iff (f := f) b).1 hb
      have hbLt := b.isLt
      refine ⟨⟨(b : ℕ) - 2 * f, by omega⟩, by simp, ?_⟩
      apply Fin.ext
      simp
      omega
  simpa using hcard.symm

theorem witness_boundaryFaultBlocks_admissible
    (f : ℕ) :
    FaultAdmissible (3 * f) f (boundaryLowFaults f) ∧
      FaultAdmissible (3 * f) f (boundaryMidFaults f) ∧
      FaultAdmissible (3 * f) f (boundaryHighFaults f) := by
  simp [FaultAdmissible, boundaryLowFaults_card,
    boundaryMidFaults_card, boundaryHighFaults_card]

/--
Set-level boundary impossibility.  Availability against the low and high
fault blocks yields two quorums avoiding opposite thirds of the node set.  Their
intersection is forced into the middle fault block, contradicting set-level
safety for that admissible adversary.
-/
theorem no_thresholdSafe_and_thresholdAvailable_at_three_f
    {f : ℕ} (hf : 1 ≤ f) :
    ¬ ∃ q : ℕ, ThresholdSafe (3 * f) f q ∧ ThresholdAvailable (3 * f) f q := by
  have _hfpos : 0 < f := Nat.lt_of_lt_of_le Nat.zero_lt_one hf
  intro h
  rcases h with ⟨q, hsafe, havail⟩
  have hBlocks := witness_boundaryFaultBlocks_admissible f
  rcases hBlocks with ⟨hLowAdm, hMidAdm, hHighAdm⟩
  rcases havail (boundaryLowFaults f) hLowAdm with ⟨Q₁, hQ₁, hQ₁Disj⟩
  rcases havail (boundaryHighFaults f) hHighAdm with ⟨Q₂, hQ₂, hQ₂Disj⟩
  have hCommon :=
    hsafe Q₁ Q₂ hQ₁ hQ₂ (boundaryMidFaults f) hMidAdm
  rcases hCommon with ⟨x, hx⟩
  have hxInter : x ∈ Q₁ ∩ Q₂ := (Finset.mem_sdiff.mp hx).1
  have hxNotMid : x ∉ boundaryMidFaults f := (Finset.mem_sdiff.mp hx).2
  have hxQ₁ : x ∈ Q₁ := (Finset.mem_inter.mp hxInter).1
  have hxQ₂ : x ∈ Q₂ := (Finset.mem_inter.mp hxInter).2
  have hxNotLow : x ∉ boundaryLowFaults f :=
    (Finset.disjoint_left.mp hQ₁Disj) hxQ₁
  have hxNotHigh : x ∉ boundaryHighFaults f :=
    (Finset.disjoint_left.mp hQ₂Disj) hxQ₂
  have hxGeF : f ≤ (x : ℕ) := by
    by_contra hxltNot
    have hxlt : (x : ℕ) < f := by omega
    exact hxNotLow ((anchor_boundaryLowFaults_mem_iff (f := f) x).2 hxlt)
  have hxLt2F : (x : ℕ) < 2 * f := by
    by_contra hxltNot
    have hxge : 2 * f ≤ (x : ℕ) := by omega
    exact hxNotHigh ((anchor_boundaryHighFaults_mem_iff (f := f) x).2 hxge)
  exact hxNotMid
    ((anchor_boundaryMidFaults_mem_iff (f := f) x).2 ⟨hxGeF, hxLt2F⟩)

end ByzantineQuorumIntersection

section  -- [family-lemma-library] banked rungs (re-open env namespaces for short-name refs)
open ByzantineQuorumIntersection

-- [family-lemma-library] banked: byzantine_threshold_quorum_safe_available_iff_and_tight_witness
theorem byzantine_threshold_quorum_safe_available_iff_and_tight_witness : ∀ (n f : ℕ) (hf : 1 ≤ f), (∀ q : ℕ,
      ThresholdSafeBound n f q →
        ThresholdSafe n f q ∧
        ∀ Q₁ Q₂ : NodeSet n,
          ThresholdQuorum n q Q₁ →
          ThresholdQuorum n q Q₂ →
          ∀ F : NodeSet n,
            FaultAdmissible n f F →
            ((Q₁ ∩ Q₂) \ F).Nonempty ∧
              ∃ x : Nodes n, x ∈ Q₁ ∩ Q₂ ∧ CorrectNode F x) ∧
      ((∃ q : ℕ, ThresholdSafeAndAvailableBound n f q) ↔
        3 * f + 1 ≤ n) ∧
      ThresholdSafeAndAvailableBound (3 * f + 1) f (2 * f + 1) ∧
      ThresholdSafe (3 * f + 1) f (2 * f + 1) ∧
      ThresholdAvailable (3 * f + 1) f (2 * f + 1) ∧
      ThresholdQuorum (3 * f + 1) (2 * f + 1) (tightLowerQuorum f) ∧
      ThresholdQuorum (3 * f + 1) (2 * f + 1) (tightUpperQuorum f) ∧
      (tightLowerQuorum f).card = 2 * f + 1 ∧
      (tightUpperQuorum f).card = 2 * f + 1 ∧
      tightLowerQuorum f ≠ tightUpperQuorum f ∧
      tightLowerQuorum f ≠ (Finset.univ : NodeSet (3 * f + 1)) ∧
      tightUpperQuorum f ≠ (Finset.univ : NodeSet (3 * f + 1)) ∧
      (∀ F : NodeSet (3 * f + 1),
        FaultAdmissible (3 * f + 1) f F →
        (((tightLowerQuorum f) ∩ (tightUpperQuorum f)) \ F).Nonempty ∧
          ∃ x : Nodes (3 * f + 1),
            x ∈ (tightLowerQuorum f) ∩ (tightUpperQuorum f) ∧ CorrectNode F x) ∧
      (boundaryLowFaults f).card = f ∧
      (boundaryMidFaults f).card = f ∧
      (boundaryHighFaults f).card = f ∧
      FaultAdmissible (3 * f) f (boundaryLowFaults f) ∧
      FaultAdmissible (3 * f) f (boundaryMidFaults f) ∧
      FaultAdmissible (3 * f) f (boundaryHighFaults f) ∧
      ¬ (∃ q : ℕ, ThresholdSafe (3 * f) f q ∧ ThresholdAvailable (3 * f) f q) ∧
      ¬ ∃ q : ℕ, ThresholdSafeAndAvailableBound (3 * f) f q := by
  intro n f hf
  refine ⟨?safeAll, ?existsIff, ?tightBound, ?tightSafe, ?tightAvail,
    ?lowerQuorum, ?upperQuorum, ?lowerCard, ?upperCard,
    ?lowerNeUpper, ?lowerNeUniv, ?upperNeUniv, ?tightCorrect,
    ?lowCard, ?midCard, ?highCard, ?lowAdm, ?midAdm, ?highAdm,
    ?noSafeAvail, ?noBound⟩
  · intro q hsafe
    refine ⟨thresholdSafe_of_safeBound hsafe, ?_⟩
    intro Q₁ Q₂ hQ₁ hQ₂ F hF
    have hnonempty :=
      thresholdSafe_of_safeBound hsafe Q₁ Q₂ hQ₁ hQ₂ F hF
    refine ⟨hnonempty, ?_⟩
    rcases hnonempty with ⟨x, hx⟩
    exact ⟨x, (Finset.mem_sdiff.mp hx).1, (Finset.mem_sdiff.mp hx).2⟩
  · exact exists_thresholdSafeBound_and_availableBound_iff n f
  · dsimp [ThresholdSafeAndAvailableBound,
      ThresholdSafeBound, ThresholdAvailableBound]
    omega
  · apply thresholdSafe_of_safeBound
    dsimp [ThresholdSafeBound]
    omega
  · apply thresholdAvailable_of_availableBound
    dsimp [ThresholdAvailableBound]
    omega
  · rw [ThresholdQuorum, tightLowerQuorum_card]
  · rw [ThresholdQuorum, tightUpperQuorum_card]
  · exact tightLowerQuorum_card f
  · exact tightUpperQuorum_card f
  · exact tightLowerQuorum_ne_tightUpperQuorum hf
  · exact tightLowerQuorum_ne_univ hf
  · exact tightUpperQuorum_ne_univ hf
  · intro F hF
    have hnonempty :=
      thresholdSafe_of_safeBound
        (n := 3 * f + 1) (f := f) (q := 2 * f + 1)
        (by dsimp [ThresholdSafeBound]; omega)
        (Q₁ := tightLowerQuorum f)
        (Q₂ := tightUpperQuorum f)
        (by rw [ThresholdQuorum, tightLowerQuorum_card])
        (by rw [ThresholdQuorum, tightUpperQuorum_card])
        F hF
    refine ⟨hnonempty, ?_⟩
    rcases hnonempty with ⟨x, hx⟩
    exact ⟨x, (Finset.mem_sdiff.mp hx).1, (Finset.mem_sdiff.mp hx).2⟩
  · exact boundaryLowFaults_card f
  · exact boundaryMidFaults_card f
  · exact boundaryHighFaults_card f
  · exact (witness_boundaryFaultBlocks_admissible f).1
  · exact (witness_boundaryFaultBlocks_admissible f).2.1
  · exact (witness_boundaryFaultBlocks_admissible f).2.2
  · exact no_thresholdSafe_and_thresholdAvailable_at_three_f hf
  · exact no_safe_available_bound_at_three_f hf

end

#print axioms byzantine_threshold_quorum_safe_available_iff_and_tight_witness
