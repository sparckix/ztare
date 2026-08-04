# H90 held-out outcome-trained selector result

H90 rejects the proposed compounding step. H89's settled credit state correctly
changed top-1 allocation from producer-favored redundant memory to causal
memory, but that learned choice performed worse on four fresh controllers.
Intervention selection based only on observation-level average value is
insufficient.

## Selector identity

Before any scored arm:

- H89 result hash
  `2093a1c1a12b7bc3362ef4e66f684f38fab8e545635b62f5f7d3ef6a06479fcc`
  verified;
- its embedded credit state rehydrated with exact hash and derived-field
  checks;
- the live task, controller class, observation, choice set, and action
  vocabulary matched that credit scope;
- the outcome-trained allocator selected causal revision
  `e32046fb0d67861ea9174e429768871dfbc4f500ed406e6d39ddbc37974518f3`;
- the empty-state producer-prior allocator selected redundant revision
  `8be45f02c57e800bae37a640c40534b064b04231f9471170a05f650433656985`.

The four execution orders alternated, giving each selector two first-arm and
two second-arm positions. Both presentations remained exactly 3,849 canonical
JSON UTF-8 bytes and every arm spent 20 actions.

## Result

| Pair | Order | Trained Level 1 | Prior Level 1 | Task delta | Composite delta |
|---|---|---:|---:|---:|---:|
| 1 | trained, prior | action 19 | action 14 | 0 | -0.05 |
| 2 | prior, trained | action 20 | action 20 | 0 | 0.00 |
| 3 | trained, prior | action 13 | action 13 | 0 | 0.00 |
| 4 | prior, trained | miss | action 13 | -1 | -0.88 |

The outcome-trained selector won `0/4`, completed `3/4` versus `4/4`, and
averaged `-0.2325` against the preregistered prediction `+0.20`. The result
verdict is `rejected`. Incorporating the new outcomes moved final top-1
allocation back to redundant true memory.

## Failure identity

H88/H89 estimated the average effect of memory content over stochastic
controllers that shared one observation. H90 attempted to use that value as a
policy. The exact observation does not identify the controller's active
hypothesis:

- when a controller spontaneously visited the marker first, causal recall was
  redundant and pairs tied or favored the producer-prior arm;
- when a controller treated the state as already matched, the causal bundle
  did not reliably prevent direct terminal entry;
- Pair 4 delivered the causal bundle, yet the controller tested the terminal,
  reached the marker only at action 15, and missed the fixed horizon.

The current receipt proves injection. It does not prove that the intervention
changed, confirmed, or was rejected by the controller's proposed action. The
next governing object is a proposal-conditional **decision-use transition**:

```text
unbriefed proposal
-> candidate intervention
-> inject / challenge / silence gate
-> revised proposal
-> use relation
-> charged action
-> external settlement
```

The use relation must distinguish at least:

- `already_satisfied`: the unbriefed proposal already carries the causal
  constraint, so silence may win;
- `accepted_change`: intervention changes the action or falsifiable
  prediction in the supported direction;
- `rejected`: the revised proposal explicitly declines the memory;
- `contradicted`: the proposal asserts a state incompatible with the memory
  and current observation;
- `unresolved`: no inspectable consequence connects intervention to proposal.

Outcome credit should pay the gate decision under this proposal state, not
continue attaching one unconditional value to the memory content.

## Evidence

- machine result: `h90_heldout_outcome_trained_selector/result.json`
  (`3b0d070afed8526ba84210b6e60b557aed753949247bf37c296a32beaa437f2b`)
- frozen manifest: `h90_heldout_outcome_trained_selector/manifest.json`
- arm receipts: `h90_heldout_outcome_trained_selector/arms/`
- incremental turn checkpoints:
  `h90_heldout_outcome_trained_selector/turns/`
- matched settlements:
  `h90_heldout_outcome_trained_selector/settlements/`
- focused verification after settlement: `23 passed`

