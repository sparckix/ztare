---
source_type: source_evidence
---
# Synthetic Cache Isolation Check

This source is synthetic local fixture evidence for the public operations
diagnosis demo. It tests whether support-console cache misses can stay high
while billing exports are healthy.

## Isolation Rows

| timestamp_utc | export_batch_id | export_status | export_duration_seconds | export_batch_lag_minutes | cache_miss_rate | billing_status_lookup_p95_ms | chg_143_retained | interpretation |
|---|---|---|---:|---:|---:|---:|---|---|
| 2026-06-14T02:30:00Z | b-7108 | ok | 344 | 28 | 0.09 | 260 | true | rollback complete; cache near threshold but below independent-defect line |
| 2026-06-14T06:50:00Z | b-7109 | ok | 352 | 18 | 0.08 | 230 | true | healthy export; cache low |
| 2026-06-15T02:15:00Z | b-7110 | ok | 327 | 15 | 0.07 | 205 | true | healthy export; cache baseline restored |
| 2026-06-15T10:00:00Z | none | no_export_due | 0 | 12 | 0.08 | 210 | true | support-console timeout change retained; no independent cache spike |

## Local Verifier

The fixture contains no isolation row where `cache_miss_rate > 0.10` while
`export_duration_seconds < 400` and `export_batch_lag_minutes < 30`.

That local verifier weakens the independent-cache-defect hypothesis for this
synthetic dataset. It does not prove that cache defects are impossible in a real
operations environment.

## Boundary

- The rows are local synthetic evidence, not customer telemetry.
- The rows support cache behavior as a symptom or amplifier after export lag,
  not as an independently sufficient root cause in this fixture.
- A future row showing high cache misses during healthy exports would reopen the
  cache-defect hypothesis.
