# Labeled-successor refinement result

H74 produced the predicted deeper distinguishing suffix.

- The generic one-step right-congruence refinement passed its fixture.
- 250 focused tests passed.
- The Level 3 run retained H71, the current carrier and seed, all four
  operations, depth 180, and the 20,000-state ceiling.
- H72's source block was separated.
- Search returned `projection_noncommuting` after 537 generated / 462 expanded
  states at depth 21.
- The new merged source class has controlled base `(5,29)`. Applying operation
  `3` yields successor depth-one classes distinguished by the subsequent
  operation `0`; the exposed distinguishing word is `(3,0)`.
- The task-relation truth vector did not change.

This is a behavioral depth result: one labeled future is insufficient, while
two are directly demanded by the counterexample. No environment contact
occurred.
