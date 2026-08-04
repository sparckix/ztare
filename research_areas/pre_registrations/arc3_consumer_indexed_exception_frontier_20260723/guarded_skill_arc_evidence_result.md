# Guarded skill compilation on sealed ARC evidence

Date: 2026-07-27

Status: count criterion refuted; ordered-skill carrier confirmed

The audit consumed the same active epoch, carrier, origin seed, sealed-slice
ledger, and history lift as the existing partial-action audit. It made no
environment call.

Measured library:

- sealed trace segments: `27`
- primitive operations: `768`
- encoded tokens: `264`
- dictionary tokens: `16`
- total description length: `280`
- description-length gain: `488`
- exact reconstruction: `true`
- retained guarded programs: `4`
- current predictive-quotient options: `0`
- order-invariant receipt: `true`

The retained primitive words were:

1. `(0, 0, 0)`
2. `(0, 0, 0, 2, 1, 1)`
3. `(2, 1)`
4. `(0, 0, 0, 0, 0)`

All four had admitted initiation keys supported by at least two distinct sealed
traces. They also recorded typed `observed_degeneration`, `epoch_boundary`, or
`reset_boundary` side exits at the earliest matching operation. The compiler
forms successful occurrences only inside ordinary trace windows, and exact
reconstruction retained every boundary operation as a primitive token.

The preregistered count comparison failed because the baseline was zero:
`4 < 0` is false. The result identifies a prior harness failure rather than a
skill absence. Bounded graph-path discovery requires repeated members in one
predictive quotient class; the refined carrier has 121 classes over 130 source
fibers and therefore reports no options. Ordered trace compilation recognizes
repeated guarded morphisms across those refined classes and preserves their
failure boundaries.

Evidence:

- `guarded_skill_arc_evidence_audit_result.json`
- focused common/worldmodel verification: `30 passed`
