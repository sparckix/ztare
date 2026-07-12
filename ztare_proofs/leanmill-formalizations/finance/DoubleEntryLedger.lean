/-
LeanMill campaign provenance — balanced_journal_conservation_zero_endpoint_and_separate_sharpness
The theorem(s) below are the VERBATIM machine-checked closure. This header is GENERATED from run
telemetry (run_tag=notes_double_entry_ledger_controlplane_final_0708b) by promote_campaign_artifact.py — not hand-authored.

  outcome     : closed · faithful · axioms propext, Classical.choice, Quot.sound
  domain      : formalization-nonmath
  time        : wall 802.39s launch→close = formalize 566.03s (theory+statement+firewall) + prove 236.36s (proof search) · prove p50 0s p95 472.72s
  compute     : cost-to-closure 62.91s mean · 117.61s total
  yield       : 2/3 attempts closed (1 failed)
  phases      : 130.6s native · 116.6s leaf.dispatch · 45.9s formalize · 4s govern.mnc · 0s pool · 0s consolidate
  reuse       : 0 rung(s) banked this run · 5 reused from prior bank
  moves       : native_hammer×2 · claude_warm×1
  milestone   : campaign family 'notes_double_entry_ledger_controlplane_final_0708b' — 1 run(s) · REAL elapsed (launch→last) 832.8s (~14 min) = formalize 360.1s + prove/other · active-solve 117.6s · 2 closures [launch→last is the honest wall]
     - notes_double_entry_ledger_controlplane_final_0708b: 2/3 closed · elapsed 832.79s (~13.9 min)
-/
import Mathlib

-- Natural-language specification (blueprint): blueprints/double_entry_ledger_blueprint.md
-- Read the blueprint to check the faithfulness boundary — the guarantee stops where the English intent is argued, not proved.

universe u

abbrev Ledger (Account : Type u) : Type u :=
  Account → Int

/-- One signed amount posted to one account. -/

structure Leg (Account : Type u) where
  account : Account
  amount : Int

/-- One journal entry, represented by its finite list of legs. -/

abbrev Entry (Account : Type u) : Type u :=
  List (Leg Account)

/-- A finite sequence of journal entries. -/

abbrev Journal (Account : Type u) : Type u :=
  List (Entry Account)

/-- The signed sum of all leg amounts in an entry. -/

def entrySum {Account : Type u} (entry : Entry Account) : Int :=
  (entry.map fun leg ↦ leg.amount).sum

/-- An entry is balanced when its signed leg amounts sum to zero. -/

def BalancedEntry {Account : Type u} (entry : Entry Account) : Prop :=
  entrySum entry = 0

/-- Apply one leg to a ledger by adding the leg amount at exactly its target account. -/

def applyLeg {Account : Type u} [DecidableEq Account]
    (ledger : Ledger Account) (leg : Leg Account) : Ledger Account :=
  Function.update ledger leg.account (ledger leg.account + leg.amount)

/-- Apply all legs of one entry in submitted order. -/

def applyEntry {Account : Type u} [DecidableEq Account]
    (ledger : Ledger Account) (entry : Entry Account) : Ledger Account :=
  entry.foldl applyLeg ledger

/-- Post a finite journal by applying each entry in submitted order. -/

def postJournal {Account : Type u} [DecidableEq Account]
    (ledger : Ledger Account) (journal : Journal Account) : Ledger Account :=
  journal.foldl applyEntry ledger

/-- Sum all balances over the finite account universe. -/

def totalBalance {Account : Type u} [Fintype Account] (ledger : Ledger Account) : Int :=
  Finset.univ.sum ledger

/-- Applying one leg changes the total balance by exactly that leg's signed amount. -/
theorem applyLeg_total {Account : Type u} [Fintype Account] [DecidableEq Account]
    (ledger : Ledger Account) (leg : Leg Account) :
    totalBalance (applyLeg ledger leg) = totalBalance ledger + leg.amount := by
  unfold totalBalance applyLeg
  rw [Finset.sum_update_of_mem (Finset.mem_univ leg.account)]
  rw [Finset.sdiff_singleton_eq_erase]
  rw [← Finset.add_sum_erase Finset.univ ledger (Finset.mem_univ leg.account)]
  abel

/-- Applying one entry changes the total balance by exactly `entrySum`. -/
theorem applyEntry_total {Account : Type u} [Fintype Account] [DecidableEq Account]
    (ledger : Ledger Account) (entry : Entry Account) :
    totalBalance (applyEntry ledger entry) = totalBalance ledger + entrySum entry := by
  induction entry generalizing ledger with
  | nil =>
      simp [applyEntry, entrySum]
  | cons leg rest ih =>
      change totalBalance (applyEntry (applyLeg ledger leg) rest) =
        totalBalance ledger + entrySum (leg :: rest)
      rw [ih (applyLeg ledger leg), applyLeg_total]
      simp [entrySum]
      abel

/-- A balanced entry preserves the account-universe total. -/
theorem balanced_entry_preserves_total {Account : Type u} [Fintype Account] [DecidableEq Account]
    (ledger : Ledger Account) {entry : Entry Account} (hentry : BalancedEntry entry) :
    totalBalance (applyEntry ledger entry) = totalBalance ledger := by
  change entrySum entry = 0 at hentry
  rw [applyEntry_total, hentry, add_zero]

/-- A finite journal of balanced entries preserves the account-universe total. -/
theorem balanced_journal_preserves_total {Account : Type u} [Fintype Account]
    [DecidableEq Account] (ledger : Ledger Account) {journal : Journal Account}
    (hjournal : ∀ entry ∈ journal, BalancedEntry entry) :
    totalBalance (postJournal ledger journal) = totalBalance ledger := by
  induction journal generalizing ledger with
  | nil =>
      simp [postJournal]
  | cons entry rest ih =>
      have hentry : BalancedEntry entry := hjournal entry (by simp)
      have hrest : ∀ entry' ∈ rest, BalancedEntry entry' := by
        intro entry' hmem
        exact hjournal entry' (by simp [hmem])
      change totalBalance (postJournal (applyEntry ledger entry) rest) = totalBalance ledger
      rw [ih (applyEntry ledger entry) hrest]
      exact balanced_entry_preserves_total ledger hentry

theorem balanced_journal_conservation_zero_endpoint_and_separate_sharpness : ∀ {Account : Type u} [Fintype Account] [DecidableEq Account], (∀ (ledger : Ledger Account) {journal : Journal Account},
      (∀ entry ∈ journal, BalancedEntry entry) →
        totalBalance (postJournal ledger journal) = totalBalance ledger ∧
          (totalBalance ledger = 0 →
            totalBalance (postJournal ledger journal) = 0)) ∧
      (∀ (ledger : Ledger Account) (account : Account) {amount : Int},
        amount ≠ 0 →
          ¬ BalancedEntry ([{ account := account, amount := amount }] : Entry Account) ∧
            totalBalance
                (applyEntry ledger ([{ account := account, amount := amount }] : Entry Account)) ≠
              totalBalance ledger) := by
  intro Account _ _
  constructor
  · intro ledger journal hjournal
    constructor
    · exact balanced_journal_preserves_total ledger hjournal
    · intro hledger
      rw [balanced_journal_preserves_total ledger hjournal, hledger]
  · intro ledger account amount hamount
    constructor
    · intro hbalanced
      simp [BalancedEntry, entrySum] at hbalanced
      exact hamount hbalanced
    · intro hsame
      have htotal :=
        applyEntry_total ledger ([{ account := account, amount := amount }] : Entry Account)
      simp [entrySum] at htotal
      have hcancel : totalBalance ledger + amount = totalBalance ledger := by
        exact htotal.symm.trans hsame
      have hzero : amount = 0 := by
        omega
      exact hamount hzero
