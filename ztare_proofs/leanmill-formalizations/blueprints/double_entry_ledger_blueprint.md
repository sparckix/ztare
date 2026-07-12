# Double-entry ledger -- balanced journals preserve the accounting total

> Provenance note: the final campaign run
> `notes_double_entry_ledger_controlplane_final_0708b` recorded launch blueprint SHA-256
> `2a9086ad27b9501406a1d12e9fc2a9000826210ccc42ec669b88c7f17ce76a6a` in
> `ztare_proofs/.solver_scratch/notes_double_entry_ledger_controlplane_final_0708b/run_manifest.json`.
> This repository copy includes LeanMill's post-run generated decomposition/proven-rungs writeback and is therefore
> not byte-identical to that launch input.

Opens the core accounting semantics lane. A ledger is not a single balance; it is a state machine over accounts
updated by multi-leg journal entries. The central invariant is conservation: an admissible journal entry has signed
legs whose amounts sum to zero, so applying any finite sequence of admissible entries cannot create value from one
side alone. This is the accounting-equation spine behind balance-sheet covenants, capital calculations, and
restricted-payment tests.

Assumption-accounting note: the result depends on (1) signed amounts, so a debit/credit pair can cancel; (2) an
entry-level balance guard, `sum legs.amount = 0`; (3) applying an entry by adding each leg amount to exactly its
target account; and (4) a finite account universe when taking the total across all accounts. Surface where each is
used. Do not collapse the journal to a two-leg example: multi-leg entries and finite sequences are the point. Do
not hide conservation inside a definition of admissibility that directly states the target.

## Domain
formalization-nonmath

## Theory file
double_entry_ledger_theory.lean

## Vocabulary (build these as definitions -- do not prove them)
- **Account**: an abstract finite account carrier.
- **Leg**: one signed amount posted to one account.
- **Entry**: a finite list of legs, representing one journal entry.
- **Ledger**: a balance function from accounts to signed amounts.
- **entrySum**: the signed sum of the amounts in an entry's legs.
- **BalancedEntry**: an entry whose signed leg sum is zero.
- **applyLeg / applyEntry / postJournal**: apply one leg to a ledger; apply all legs of one entry; apply a finite
  journal sequence in order by a left fold.
- **totalBalance**: the sum of all account balances over the finite account universe.

## Anchors (prove these -- they pin each definition's meaning)
- Applying one leg changes the total balance by exactly that leg's signed amount.
- Applying one entry changes the total balance by exactly `entrySum` of that entry.
- An empty entry is balanced and changes no account total.

## Target
Consider a finite account universe with signed balances. Starting from any ledger, after any finite sequence of
journal entries such that every entry is balanced, the total balance is unchanged. In particular, if the opening
ledger has total balance zero, the posted ledger also has total balance zero. This proves that balanced multi-leg
journals cannot create single-sided value across any admissible journal sequence.

Also surface sharpness: dropping the balanced-entry condition admits a one-leg journal that changes the total
balance. This witness should be separate from the main theorem so it cannot be used to weaken the invariant.

<!-- ## Lemmas below: auto-compounded from the planner's OWN decomposition (route_and_solve, #97). Reseed by editing ## Target / ## Idea above; this section is regenerated each run. -->
## Lemmas
- theorem balanced_journal_conservation_zero_endpoint_and_separate_sharpness_conj1 : ∀ {Account : Type u} [Fintype Account] [DecidableEq Account], ∀ (ledger : Ledger Account) {journal : Journal Account}, (∀ entry ∈ journal, BalancedEntry entry) → totalBalance (postJournal ledger journal) = totalBalance ledger ∧ (totalBalance ledger = 0 → totalBalance (postJournal ledger journal) = 0) := by sorry
- theorem balanced_journal_conservation_zero_endpoint_and_separate_sharpness_conj2 : ∀ {Account : Type u} [Fintype Account] [DecidableEq Account], ∀ (ledger : Ledger Account) (account : Account) {amount : ℤ}, amount ≠ 0 → ¬BalancedEntry [{ account := account, amount := amount }] ∧ totalBalance (applyEntry ledger [{ account := account, amount := amount }]) ≠ totalBalance ledger := by sorry

## Idea
Model ledger balances as `Account -> Int` with `[Fintype Account] [DecidableEq Account]`. A leg updates one account
with `Function.update`; total balance is `Finset.univ.sum ledger`. The one-leg total lemma is a finite-sum update
calculation. The entry lemma is induction over the list of legs, accumulating the signed sum. The journal theorem is
then a `List.foldl` induction over entries with the per-entry preservation lemma. Keep the theorem over an arbitrary
finite account type; do not fix a hard-coded chart of accounts.

<!-- proven-rungs:auto -->
## Proven rungs (kernel-closed, auto — citable)
- ✅ balanced_journal_conservation_zero_endpoint_and_separate_sharpness_conj2 [sha:719e1a95eacc35ba] abbrev Ledger (Account : Type u) : Type u (ztare_proofs/.solver_scratch/notes_double_entry_ledger_controlplane_final_0708b/closures/balanced_journal_conservation_zero_endpoint_and_separate_sharpness_conj2.lean)
- ✅ balanced_journal_conservation_zero_endpoint_and_separate_sharpness [sha:713d950f70672c2f] theorem balanced_journal_conservation_zero_endpoint_and_separate_sharpness : ∀ {Account : Type u} [Fintype Account] [DecidableEq Account], (∀ (ledger : Ledger Account) {journal : Journal Account}, (∀ entry ∈ journal, BalancedEntry entry) → totalBalance (postJournal ledger journal) = totalBalance led (ztare_proofs/.solver_scratch/notes_double_entry_ledger_controlplane_final_0708b/closures/balanced_journal_conservation_zero_endpoint_and_separate_sharpness.lean)
<!-- /proven-rungs:auto -->
