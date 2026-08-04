# Joint-test strength result

Date: 2026-07-26

Parent hypothesis: `joint_test_strength_hypothesis.md`

## Result

The support frontier now ranks joint predictive evidence before exceptional
effect value and route cost. Zero-joint-test analogies cannot produce an
action plan.

From the current Level 3 origin the highest-ranked reachable support gap is:

- route:
  `[0, 0, 0, 0, 0, 0, 0, 0, 2, 1, 1, 2, 1, 1, 1, 1]`;
- queried operation: `1`;
- route depth: `16`;
- jointly witnessed compatible operation: `2`;
- tested peer:
  `4ab929993a22db595db68125a854b6e5c70ac5791623119cbddea473b29225c5`;
- untested consumer:
  `f4ff1fe339a8284f53c7d5b88a26a38670eefd59cb0a31cbee548a3ca8446edf`;
- exceptional score: `13.5`;
- peer effect alternatives:
  `ee1be1a5b78ee8ae017d7fe55bc383fe12f90785c056bf32205cbfdd0e00c9d1`,
  `fbcf77d1bc466bfda4f51eb144616f8dae987e8343c1a5de9fae1655d07cc8a4`.

The peer’s queried relation has two witnessed effects. Thus the experiment
does not copy a deterministic answer. It asks which context-conditioned
effect, if either, transports to a source that already agrees on another
operation.

Evidence: `joint_test_strength_audit_result.json`.

## Consumer consequence

The planner now places a supported compatibility gap after a certified local
orbit discriminator and before a coverage-only quotient frontier. Its policy
is `predictive_compatibility_support`; its consumer action is
`execute_predictive_support_discriminator`.

