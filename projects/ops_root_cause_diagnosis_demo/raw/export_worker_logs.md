---
source_type: source_evidence
---
# Synthetic Export-Worker Logs

This source supplies the local verifier that the initial pilot named as the
decisive next falsifier. It is synthetic data for the public demo.

## Export Summary

| timestamp_utc | worker | batch_id | status | invoice_rows | error_code | duration_seconds |
|---|---|---|---|---:|---|---:|
| 2026-06-11T22:35:10Z | billing-export-us-east-2 | b-7102 | ok | 18342 | none | 318 |
| 2026-06-11T23:47:52Z | billing-export-us-east-2 | b-7103 | retry | 18401 | duplicate_payment_warning | 900 |
| 2026-06-12T00:03:05Z | billing-export-us-east-2 | b-7103 | failed | 18401 | duplicate_payment_warning | 900 |
| 2026-06-12T08:57:31Z | billing-export-us-east-2 | b-7104 | failed | 19312 | downstream_console_index_missing | 900 |
| 2026-06-12T15:42:18Z | billing-export-us-east-1 | b-7105 | failed | 19876 | downstream_console_index_missing | 900 |
| 2026-06-13T06:25:49Z | billing-export-us-east-2 | b-7106 | failed | 20110 | downstream_console_index_missing | 900 |
| 2026-06-13T17:55:33Z | billing-export-us-east-1 | b-7107 | retry | 19744 | downstream_console_index_missing | 900 |
| 2026-06-14T00:22:16Z | billing-export-us-east-2 | b-7108 | ok | 20203 | none | 344 |
| 2026-06-14T06:41:04Z | billing-export-us-east-1 | b-7109 | ok | 19988 | none | 352 |
| 2026-06-15T02:02:22Z | billing-export-us-east-2 | b-7110 | ok | 18755 | none | 327 |

## Interpretation Boundary

- The first failed/retry rows begin after `CHG-142` enabled the batching flag.
- Failed rows continue until shortly after the rollback timestamp in
  `change_and_staffing_notes.md`.
- The logs support export failure during the spike; they do not by themselves
  prove why the export worker failed.
- A healthy-log falsifier would require all rows from 2026-06-12 to
  2026-06-14 to be `ok`. This source does not satisfy that falsifier.
