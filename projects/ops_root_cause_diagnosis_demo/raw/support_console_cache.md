---
source_type: source_evidence
---
# Synthetic Support-Console Cache Metrics

This source tests whether support-console cache behavior independently explains
the missing billing status.

## Cache Miss And Lookup Rows

| timestamp_utc | service | cache_miss_rate | billing_status_lookup_p95_ms | export_batch_lag_minutes | note |
|---|---|---:|---:|---:|---|
| 2026-06-11T20:00:00Z | support-console | 0.07 | 180 | 12 | pre-change baseline |
| 2026-06-12T02:00:00Z | support-console | 0.11 | 240 | 59 | export retries active |
| 2026-06-12T10:00:00Z | support-console | 0.34 | 1410 | 393 | export batch b-7104 failed |
| 2026-06-12T18:00:00Z | support-console | 0.39 | 1680 | 517 | export batch b-7105 failed |
| 2026-06-13T10:00:00Z | support-console | 0.42 | 1740 | 603 | export batch b-7106 failed |
| 2026-06-14T02:00:00Z | support-console | 0.18 | 520 | 72 | rollback completed, export ok |
| 2026-06-15T10:00:00Z | support-console | 0.08 | 210 | 15 | near baseline |

## Diagnostic Notes

- Cache miss rate rises after export lag rises; it does not precede the export
  failures in this fixture.
- The support-console change `CHG-143` increased timeout tolerance but was
  retained after recovery, so it is weaker as a root-cause explanation than
  the rolled-back export batching flag.
- This source supports support-console cache behavior as a symptom or amplifier,
  not as the independent root cause.
