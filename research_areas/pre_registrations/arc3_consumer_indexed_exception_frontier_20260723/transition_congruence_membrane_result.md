# Transition-congruence membrane result

H73 passed with a bounded continuation.

- Semantic capability retrieval found no existing primitive for
  counterexample-guided transition-quotient refinement.
- Codex-only research-isomorphism dispatch `9d0c7e…` transported H72 to
  right-congruence refinement. Its discriminating prediction was a
  label-sensitive, one-step split that leaves task acceptance unchanged.
- A generic exact-observation relational fallback was added. Exact
  `(state,time)` identity declares deterministic merge compatibility, avoiding
  redundant quotient checks; task-relation evaluation remains the terminal
  condition.
- The bounded fixture passed, and 249 focused tests passed.
- The Level 3 run used the unchanged H71 relation, carrier, seed, four
  operations, depth 180, and 20,000-state ceiling.
- Result: `search_budget_exhausted`; 20,000 generated, 16,024 expanded, depth
  30, 3,977 nodes left on the frontier.
- A 30-operation continuation replayed exactly offline.
- H72's `(61,57)/(62,57)` merge did not recur; no new typed projection failure
  occurred.

Exact identity is therefore a safe fallback, but its concrete frontier is too
wide at this allocation. The next representation should refine the compact
chart by labeled successor behavior—the canonical one-step splitter supplied
by the counterexample—while keeping the task relation separate. No environment
contact occurred.
