/-
LeanMill campaign provenance — median_voter_theorem
The theorem(s) below are the VERBATIM machine-checked closure. This header is GENERATED from run
telemetry (run_tag=notes_median_voter_blueprint_0702T1818) by promote_campaign_artifact.py — not hand-authored.

  outcome     : closed · faithful · axioms propext, Quot.sound
  domain      : formalization-nonmath
  time        : wall 465.22s launch→close = formalize 371.44s (theory+statement+firewall) + prove 93.78s (proof search) · prove p50 93.78s p95 93.78s
  compute     : cost-to-closure 62.93s mean · 62.93s total
  yield       : 1/3 attempts closed (1 failed)
  phases      : 136.4s leaf.dispatch · 64.1s formalize · 26.7s pool · 11.4s native · 0.1s govern.mnc · 0s consolidate
  reuse       : 0 rung(s) banked this run · 0 reused from prior bank
  moves       : proposer_pool×1 · native_hammer×1 · claude_warm×1
  milestone   : campaign family 'notes_median_voter_blueprint' — 2 run(s) · REAL elapsed (launch→last) 5183.9s (~86 min) = formalize 2244.8s + prove/other · active-solve 721s · 9 closures [launch→last is the honest wall]
     - notes_median_voter_blueprint_0702T1532: 8/20 closed · elapsed 4713.31s (~78.6 min)
     - notes_median_voter_blueprint_0702T1818: 1/3 closed · elapsed 470.54s (~7.8 min)
-/
import Mathlib

-- Natural-language specification (blueprint): blueprints/median_voter_blueprint.md
-- Read the blueprint to check the faithfulness boundary — the guarantee stops where the English intent is argued, not proved.

variable {V : Type*} [Fintype V] {A : Type*} [LinearOrder A] {B : Type*} [LinearOrder B]

def Prefers (u : A → B) (x y : A) : Prop :=
  u y < u x

def SinglePeaked (peak : A) (u : A → B) : Prop :=
  StrictMonoOn u (Set.Iic peak) ∧ StrictAntiOn u (Set.Ici peak)

def supporters (u : V → A → B) (x y : A) : Finset V :=
  Finset.univ.filter fun i => u i y < u i x

def Beats (u : V → A → B) (x y : A) : Prop :=
  Fintype.card V < 2 * (supporters u x y).card

def IsMedian [LinearOrder A] (peaks : V → A) (m : A) : Prop :=
  Fintype.card V ≤ 2 * (Finset.univ.filter fun i => peaks i ≤ m).card ∧
  Fintype.card V ≤ 2 * (Finset.univ.filter fun i => m ≤ peaks i).card

def CondorcetWinner (u : V → A → B) (m : A) : Prop :=
  ∀ y : A, y ≠ m → Beats u m y

theorem mem_supporters {u : V → A → B} {x y : A} {i : V} :
    i ∈ supporters u x y ↔ Prefers (u i) x y := by
  simp [supporters, Prefers]

theorem prefers_of_peak_le_of_lt {peak : A} {u : A → B}
    (h : SinglePeaked peak u) {m y : A} (hpm : peak ≤ m) (hmy : m < y) :
    Prefers u m y :=
  h.2 (Set.mem_Ici.mpr hpm) (Set.mem_Ici.mpr (hpm.trans (le_of_lt hmy))) hmy

theorem prefers_of_le_peak_of_lt {peak : A} {u : A → B}
    (h : SinglePeaked peak u) {m y : A} (hmp : m ≤ peak) (hym : y < m) :
    Prefers u m y :=
  h.1 (Set.mem_Iic.mpr ((le_of_lt hym).trans hmp)) (Set.mem_Iic.mpr hmp) hym

theorem lt_two_mul_of_odd_of_le {n k : ℕ} (hodd : Odd n)
    (h : n ≤ 2 * k) : n < 2 * k := by
  rcases hodd with ⟨j, rfl⟩
  omega

theorem lt_two_mul_card_of_subset {s t : Finset V}
    (hsub : s ⊆ t) (h : Fintype.card V < 2 * s.card) :
    Fintype.card V < 2 * t.card := by
  have := Finset.card_le_card hsub
  omega

theorem beats_of_isMedian_of_lt {peaks : V → A} {u : V → A → B} {m : A}
    (hodd : Odd (Fintype.card V))
    (hsp : ∀ i : V, SinglePeaked (peaks i) (u i))
    (hmed : IsMedian peaks m) {y : A} (hmy : m < y) :
    Beats u m y := by
  have hsub : (Finset.univ.filter fun i => peaks i ≤ m) ⊆ supporters u m y := by
    intro i hi
    rw [Finset.mem_filter] at hi
    exact mem_supporters.mpr (prefers_of_peak_le_of_lt (hsp i) hi.2 hmy)
  exact lt_two_mul_card_of_subset hsub
    (lt_two_mul_of_odd_of_le hodd hmed.1)

theorem beats_of_isMedian_of_gt {peaks : V → A} {u : V → A → B} {m : A}
    (hodd : Odd (Fintype.card V))
    (hsp : ∀ i : V, SinglePeaked (peaks i) (u i))
    (hmed : IsMedian peaks m) {y : A} (hym : y < m) :
    Beats u m y := by
  have hsub : (Finset.univ.filter fun i => m ≤ peaks i) ⊆ supporters u m y := by
    intro i hi
    rw [Finset.mem_filter] at hi
    exact mem_supporters.mpr (prefers_of_le_peak_of_lt (hsp i) hi.2 hym)
  exact lt_two_mul_card_of_subset hsub
    (lt_two_mul_of_odd_of_le hodd hmed.2)

theorem median_voter_theorem : ∀ {peaks : V → A} {u : V → A → B} {m : A}
    (hodd : Odd (Fintype.card V))
    (hsp : ∀ i : V, SinglePeaked (peaks i) (u i))
    (hmed : IsMedian peaks m), ∀ y : A, y ≠ m → Beats u m y := by
  intro peaks u m hodd hsp hmed y hy
  rcases lt_or_gt_of_ne hy with hym | hmy
  · exact beats_of_isMedian_of_gt hodd hsp hmed hym
  · exact beats_of_isMedian_of_lt hodd hsp hmed hmy
