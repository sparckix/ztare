# Predictive identity versus acquisition support result

Date: 2026-07-26

Parent hypothesis:
`predictive_support_identity_hypothesis.md`

## Result

The support-only prediction passed.

The support-aware compiler evaluated `82` source fibers by greatest-fixed-point
compatibility:

- refinement rounds: `15`;
- distinct compatible pairs: `2383`;
- refuted pairs: `938`;
- asymmetric source-operation support gaps: `3477`.

For the exact two members split by the total quotient:

- left:
  `408a494c2a69bb635558f85b286a4772c8b42352277dd1137871eafda0d8c8ef`;
- right:
  `60f76128a94478ca291a8dce74f192c5151a72c42e7e7495d29d7fee86086e33`;
- compatible: `true`;
- refutation: none;
- support gaps: exactly one;
- missing test: operation `1`;
- witnessed effect:
  `73e94a8d04356cc52fd15866c5871c7a8e759c81a3d76e37fedc5131ee7153f4`.

The prior `74 -> 75` partition change therefore encoded evidence coverage as
behavioral state identity. It did not establish a new controllability
mechanism.

Evidence:
`predictive_support_identity_audit_result.json`.

## Kernel consequence

`src/ztare/common/predictive_quotient.py` now contains a separate predictive
compatibility object:

- jointly witnessed disjoint effects refute compatibility;
- refuted successors propagate backward to predecessors;
- an untested operation supplies no behavioral result;
- asymmetric coverage becomes a consumer-indexed support gap;
- concrete source witnesses remain available;
- lifecycle boundaries remain in the compared effect relation.

## Remaining discriminator

Compatibility under partial evidence is permissive. The current corpus has
`2383` unrefuted source pairs and `3477` support gaps. A consumer must rank a
gap by the amount of shared predictive testing that supports its analogy;
absence of contradiction alone is insufficient steering evidence.

