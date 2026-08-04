# Guarded skill compiler result

Date: 2026-07-27

Status: confirmed on the bounded generic discriminator

The new common compiler consumes only ordered opaque transition identities. On
the preregistered fixture it produced:

- bounded deterministic-path options: `3`
- retained guarded programs: `1`
- primitive trace tokens: `11`
- encoded tokens: `7`
- dictionary tokens: `3`
- total description length: `10`
- description-length gain: `1`
- exact reconstruction: `true`
- successful program occurrences: `2` on independent traces
- effect/termination variants: `1`
- typed side exits: `1`

The retained word was `('a', 'b', 'c')`. The side exit occurred on attempted
operation `'c'` at zero-based step `2`, after matched prefix `('a', 'b')`.

Execution decisions were:

- two clean witnessed initiation keys: `compiled / witnessed_guard`
- the boundary-conflicted initiation key: `primitive_fallback / guard_conflict`
- an unseen initiation key: `primitive_fallback / guard_unwitnessed`

Reversing input trace order produced an identical receipt. An overlapping
single-trace `('a', 'a')` case produced no program and zero gain, preventing
overlap from manufacturing compression.

Focused verification:

```text
21 passed
```

This establishes lossless selection, guard separation, and fallback on the
bounded common fixture. The next test lowers the existing sealed ARC
trajectories through the same contract.
