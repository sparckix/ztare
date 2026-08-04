# Terminal affordance-relation transport result

Date: 2026-07-26

Status: full hypothesis refuted; destination-footprint invariant confirmed

All terminal operation maps were supported and untied. Both positive sources
had one controlled origin. The inferred attempted origins are `(10,34)` for
the epoch-0 completion and `(40,14)` for the held-out epoch-1 completion.

The palette-partitioned, dihedral-canonical 5×5 attempted-destination
footprint has the same SHA-256 on both completions:
`5f332d7e3f1cf374998f1da7bc323ebe6cee405acb23268c60992eb8f7760bec`.
None of five epoch-1 `GAME_OVER` edges shares it; all five instead share
`d76ebf5d…`. This is the first prior-level transport in this lane that passes a
positive holdout and terminal-failure discriminator.

The preregistered product with `finite_configuration` fails. More sharply, the
epoch-0 completion configuration is shared by all five epoch-1 failures, while
the epoch-1 completion has a different configuration. Configuration therefore
cannot be copied across levels. The larger shell also differs between positive
epochs, so global surroundings are implementation coordinates rather than the
transported object.

The result separates two layers:

- universal candidate: the attempted-destination footprint relation;
- level-local residual: which configuration and route can realize that
  relation without a non-discharge boundary.

The footprint remains advisory. It must now be lowered onto the active
partial-action frontier, with already observed Level 3 boundaries used as
counterexamples before any live intervention.

Evidence: `terminal_affordance_relation_audit_result.json`.

