# H99 persistent temporal judgment result

Date: 2026-08-05

Hypothesis:
`H-GPSA-PERSISTENT-TEMPORAL-JUDGMENT-20260805-99`

Verdict: supported on the pre-registered controller-neutral offline surface

Machine result:
`h99_persistent_temporal_judgment_result.json`

SHA-256:
`1ddb53abecbf6a5aaf7609a957e4bd8b1ad89fbc998a85b6472e5c2725bab8d4`

## Result

All twelve frozen checks passed.

- A legacy `ztare-continual-skill-memory-v1` payload migrated to v2 while its
  immediate open/open pair retained zero preference for both options.
- Four finite eligibility chains and their hashes survived save/load.
- Six exact variant/measure yield calibrations were rederived from the restored
  chains. Every calibration denied task-credit authority.
- A modified persisted calibration was rejected because it no longer matched
  the chain evidence.
- Two matched terminal contrasts reconstructed `+1` for `advance` and `-1` for
  `detour`, although both options had immediate preference zero.
- Baseline protocol selection chose `detour`; the restored distal judgment
  reranked the same priced candidates to `advance`.
- Primitive and control costs were unchanged.
- Changing the continuation controller or complete choice set returned zero
  distal value for both options.
- Opposed nonzero immediate and distal judgments returned
  `credit_conflict` with neutral preference for both options.

Focused verification:

`28 passed in 0.25s`

The focused set covered temporal credit, continual memory, guarded protocol
pricing, and mechanism protocol selection.

## Interpretation

The missing architectural object identified after H98 now has durable state:
episodic decision chains persist, prediction error remains a separate derived
receipt, and matched external terminal outcomes can affect the existing
selector after restart. The migration test also shows that old open/open
decision rows are not silently reinterpreted as delayed evidence.

The next missing object is the online chain builder. The ARC play loop still
records each decision window independently at a leg boundary; it does not yet
bind successive windows into a finite eligibility chain with a stable
continuation-policy identity, observed information-yield measure, matched-arm
identity, and terminal adjudication.

## Claim boundary

This result establishes controller-neutral offline persistence and synthetic
selector integration. It does not establish ARC score gain, automatic chain
collection from play, H97 support, cross-task value transport, or live
improvement.
