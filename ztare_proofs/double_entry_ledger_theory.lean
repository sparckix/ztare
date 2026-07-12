import Mathlib

/-!
# Double-entry ledger theory

Definition trial summary:

* A `Finsupp Account Int` ledger gives sparse storage, but the campaign invariant is
  over a finite account universe, including zero-balance accounts.
* A `Multiset` entry quotients away leg order, but posting is naturally stated as a
  fold over submitted journal legs and the blueprint asks for finite sequences.
* The selected substrate uses `Account → Int` ledgers and `List` entries/journals.
  Its model-case anchors reduce directly to Mathlib's `Function.update`,
  `List.foldl`, `List.sum`, and `Finset.univ.sum`.

No definition below universally quantifies over membership in a constructed set, so
the vacuity guard for empty sets is not triggered here.
-/

namespace DoubleEntryLedger

universe u

/-- A ledger is a signed balance for each account in the account universe. -/
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

theorem anchor_Ledger_eq_function {Account : Type u} (ledger : Ledger Account) :
    ledger = (ledger : Account → Int) :=
  rfl

@[simp]
theorem anchor_Leg_mk_account {Account : Type u} (account : Account) (amount : Int) :
    (Leg.mk account amount).account = account :=
  rfl

@[simp]
theorem anchor_Leg_mk_amount {Account : Type u} (account : Account) (amount : Int) :
    (Leg.mk account amount).amount = amount :=
  rfl

theorem anchor_Entry_eq_list {Account : Type u} (entry : Entry Account) :
    entry = (entry : List (Leg Account)) :=
  rfl

theorem anchor_Journal_eq_list {Account : Type u} (journal : Journal Account) :
    journal = (journal : List (Entry Account)) :=
  rfl

theorem anchor_entrySum_eq_list_sum {Account : Type u} (entry : Entry Account) :
    entrySum entry = (entry.map fun leg ↦ leg.amount).sum :=
  rfl

theorem anchor_BalancedEntry_iff_entrySum_zero {Account : Type u} (entry : Entry Account) :
    BalancedEntry entry ↔ entrySum entry = 0 :=
  Iff.rfl

theorem anchor_applyLeg_eq_function_update {Account : Type u} [DecidableEq Account]
    (ledger : Ledger Account) (leg : Leg Account) :
    applyLeg ledger leg =
      Function.update ledger leg.account (ledger leg.account + leg.amount) :=
  rfl

theorem anchor_applyEntry_eq_list_foldl {Account : Type u} [DecidableEq Account]
    (ledger : Ledger Account) (entry : Entry Account) :
    applyEntry ledger entry = entry.foldl applyLeg ledger :=
  rfl

theorem anchor_postJournal_eq_list_foldl {Account : Type u} [DecidableEq Account]
    (ledger : Ledger Account) (journal : Journal Account) :
    postJournal ledger journal = journal.foldl applyEntry ledger :=
  rfl

theorem anchor_totalBalance_eq_univ_sum {Account : Type u} [Fintype Account]
    (ledger : Ledger Account) :
    totalBalance ledger = Finset.univ.sum ledger :=
  rfl

/-- Applying one leg changes the total balance by exactly that leg's signed amount. -/

theorem applyLeg_total {Account : Type u} [Fintype Account] [DecidableEq Account]
    (ledger : Ledger Account) (leg : Leg Account) :
    totalBalance (applyLeg ledger leg) = totalBalance ledger + leg.amount := by
  unfold totalBalance applyLeg
  rw [Finset.sum_update_of_mem (Finset.mem_univ leg.account)]
  rw [Finset.sdiff_singleton_eq_erase]
  rw [← Finset.add_sum_erase Finset.univ ledger (Finset.mem_univ leg.account)]
  abel

theorem anchor_applyLeg_total {Account : Type u} [Fintype Account] [DecidableEq Account]
    (ledger : Ledger Account) (leg : Leg Account) :
    totalBalance (applyLeg ledger leg) = totalBalance ledger + leg.amount :=
  applyLeg_total ledger leg

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

theorem anchor_applyEntry_total {Account : Type u} [Fintype Account] [DecidableEq Account]
    (ledger : Ledger Account) (entry : Entry Account) :
    totalBalance (applyEntry ledger entry) = totalBalance ledger + entrySum entry :=
  applyEntry_total ledger entry

/-- The empty entry is balanced. -/

theorem empty_entry_balanced {Account : Type u} :
    BalancedEntry ([] : Entry Account) := by
  simp [BalancedEntry, entrySum]

/-- The empty entry changes no account total. -/

theorem empty_entry_preserves_total {Account : Type u} [Fintype Account] [DecidableEq Account]
    (ledger : Ledger Account) :
    totalBalance (applyEntry ledger ([] : Entry Account)) = totalBalance ledger := by
  simp [applyEntry]

theorem anchor_empty_entry_balanced {Account : Type u} :
    BalancedEntry ([] : Entry Account) :=
  empty_entry_balanced

theorem anchor_empty_entry_preserves_total {Account : Type u}
    [Fintype Account] [DecidableEq Account] (ledger : Ledger Account) :
    totalBalance (applyEntry ledger ([] : Entry Account)) = totalBalance ledger :=
  empty_entry_preserves_total ledger

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

/-- Zero-total opening ledgers remain zero-total after any balanced finite journal. -/

theorem zero_total_postJournal_of_balanced {Account : Type u} [Fintype Account]
    [DecidableEq Account] (ledger : Ledger Account) {journal : Journal Account}
    (hledger : totalBalance ledger = 0)
    (hjournal : ∀ entry ∈ journal, BalancedEntry entry) :
    totalBalance (postJournal ledger journal) = 0 := by
  rw [balanced_journal_preserves_total ledger hjournal, hledger]

/--
Dropping the balanced-entry guard admits a one-leg nonzero journal that changes the
total. This witness is intentionally separate from the preservation theorem.
-/

theorem single_leg_unbalanced_changes_total {Account : Type u} [Fintype Account]
    [DecidableEq Account] (ledger : Ledger Account) (account : Account)
    {amount : Int} (hamount : amount ≠ 0) :
    ¬ BalancedEntry ([{ account := account, amount := amount }] : Entry Account) ∧
      totalBalance
          (applyEntry ledger ([{ account := account, amount := amount }] : Entry Account)) ≠
        totalBalance ledger := by
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

section  -- [family-lemma-library] banked rungs (re-open env namespaces + section variables)
open DoubleEntryLedger

-- [family-lemma-library] banked: balanced_journal_conservation_zero_endpoint_and_separate_sharpness_conj2__5cb10a89
theorem balanced_journal_conservation_zero_endpoint_and_separate_sharpness_conj2__5cb10a89 : ∀ {Account : Type u} [Fintype Account] [DecidableEq Account], ∀ (ledger : Ledger Account) (account : Account) {amount : ℤ},
    amount ≠ 0 →
      ¬BalancedEntry [{ account := account, amount := amount }] ∧
        totalBalance (applyEntry ledger [{ account := account, amount := amount }]) ≠ totalBalance ledger := by
  (repeat' apply And.intro) <;> (first | assumption | exact?)

end

section  -- [family-lemma-library] banked rungs (re-open env namespaces + section variables)
open DoubleEntryLedger

-- [family-lemma-library] banked: balanced_journal_conservation_zero_endpoint_and_separate_sharpness__0019fad4
theorem balanced_journal_conservation_zero_endpoint_and_separate_sharpness__0019fad4 : ∀ {Account : Type u} [Fintype Account] [DecidableEq Account], (∀ (ledger : Ledger Account) {journal : Journal Account},
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

end
