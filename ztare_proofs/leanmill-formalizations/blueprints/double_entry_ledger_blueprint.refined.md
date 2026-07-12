# Consider a finite account universe with signed balances. Starting from any ledger, after a — apparatus-refined
<!-- 5/5 lemmas formalized+closed; shelf=5; target closed -->

## Target
Consider a finite account universe with signed balances. Starting from any ledger, after any finite sequence of journal entries such that every entry is balanced, the total balance is unchanged. In particular, if the opening ledger has total balance zero, the posted ledger also has total balance zero. This proves that balanced multi-leg journals cannot create single-sided value across any admissible journal sequence. Also surface sharpness: dropping the balanced-entry condition admits a one-leg journal that changes the total balance. This witness should be separate from the main theorem so it cannot be used to weaken the invariant.

## Proven this run (✅ kernel-closed — citable):
- ✅
- ✅
- ✅
- ✅
- ✅

## Proven shelf (cite these):
- theorem applyLeg_total {Account : Type u} [Fintype Account] [DecidableEq Account] (ledger : Ledger Account) (leg : Leg Account) : totalBalance (applyLeg ledger leg) = totalBalance ledger + leg.amount
- theorem applyEntry_total {Account : Type u} [Fintype Account] [DecidableEq Account] (ledger : Ledger Account) (entry : Entry Account) : totalBalance (applyEntry ledger entry) = totalBalance ledger + entrySum entry
- theorem balanced_entry_preserves_total {Account : Type u} [Fintype Account] [DecidableEq Account] (ledger : Ledger Account) {entry : Entry Account} (hentry : BalancedEntry entry) : totalBalance (applyEntry ledger entry) = totalBalance ledger
- theorem balanced_journal_preserves_total {Account : Type u} [Fintype Account] [DecidableEq Account] (ledger : Ledger Account) {journal : Journal Account} (hjournal : ∀ entry ∈ journal, BalancedEntry entry) : totalBalance (postJournal ledger journal) = totalBalance ledger
- theorem single_leg_unbalanced_changes_total {Account : Type u} [Fintype Account] [DecidableEq Account] (ledger : Ledger Account) (account : Account) {amount : Int} (hamount : amount ≠ 0) : ¬ BalancedEntry ([{ account := account, amount := amount }] : Entry Account) ∧ totalBalance (applyEntry ledger ([{ account := account, amount := amount }] : Entry Account)) ≠ totalBalance ledger

## Kernel-closed sub-lemmas this run (deep rungs — citable):
- ✅ balanced_journal_conservation_zero_endpoint_and_separate_sharpness_conj2 [sha:719e1a95eacc35ba] abbrev Ledger (Account : Type u) : Type u (ztare_proofs/.solver_scratch/notes_double_entry_ledger_controlplane_final_0708b/closures/balanced_journal_conservation_zero_endpoint_and_separate_sharpness_conj2.lean)
- ✅ balanced_journal_conservation_zero_endpoint_and_separate_sharpness [sha:713d950f70672c2f] theorem balanced_journal_conservation_zero_endpoint_and_separate_sharpness : ∀ {Account : Type u} [Fintype Account] [DecidableEq Account], (∀ (ledger : Ledger Account) {journal : Journal Account}, (∀ entry ∈ journal, BalancedEntry entry) → totalBalance (postJournal ledger journal) = totalBalance led (ztare_proofs/.solver_scratch/notes_double_entry_ledger_controlplane_final_0708b/closures/balanced_journal_conservation_zero_endpoint_and_separate_sharpness.lean)
