---
source_type: source_evidence
---
# Synthetic Incident Log

This is a synthetic operations dataset for a public ZTARE starter pilot. It is
not customer data and does not describe a real organization.

## Incident Rows

| incident_id | opened_at_utc | closed_at_utc | service | region | severity | observation |
|---|---:|---:|---|---|---:|---|
| INC-2306-08-A | 2026-06-08T09:20:00Z | 2026-06-08T10:05:00Z | helpdesk-router | us-east | 3 | short queue delay after a scheduled analytics export |
| INC-2306-11-B | 2026-06-11T23:50:00Z | 2026-06-12T03:20:00Z | billing-export | us-east | 2 | nightly invoice export retried 7 times and emitted duplicate-payment warning codes |
| INC-2306-12-C | 2026-06-12T09:05:00Z | 2026-06-13T18:40:00Z | billing-export | us-east | 1 | invoice export worker stalled; customer invoices were visible in app but missing from downstream support console |
| INC-2306-13-D | 2026-06-13T13:10:00Z | 2026-06-14T01:30:00Z | support-console | us-east | 2 | agents reported "billing status unavailable" on 41% of sampled tickets |
| INC-2306-15-E | 2026-06-15T08:40:00Z | 2026-06-15T09:15:00Z | helpdesk-router | us-east | 3 | queue rules hotfixed after backlog normalized |

## Operational Notes

- The backlog spike began after `INC-2306-11-B` and peaked during `INC-2306-12-C`.
- The support-console incident followed the billing-export failure and reported a billing-status-specific symptom.
- No region other than `us-east` is represented in this pilot fixture.
- The fixture is intentionally small, so any broad organizational diagnosis must stay out of scope.

## Non-Claims

- This source does not prove a causal root cause in a real organization.
- This source does not claim staffing, training, or seasonality are irrelevant in general.
- This source does not claim the full operations workflow is ready for deployment.
