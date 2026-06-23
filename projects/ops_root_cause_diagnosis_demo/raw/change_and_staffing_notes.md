---
source_type: source_evidence
---
# Synthetic Change And Staffing Notes

This source records candidate alternative explanations for the synthetic
operations diagnosis pilot.

## Staffing

| date | planned_staffed_hours | actual_staffed_hours | note |
|---|---:|---:|---|
| 2026-06-07 | 74 | 74 | weekend baseline |
| 2026-06-08 | 75 | 75 | no absence |
| 2026-06-09 | 74 | 74 | no absence |
| 2026-06-10 | 75 | 75 | no absence |
| 2026-06-11 | 75 | 75 | no absence |
| 2026-06-12 | 76 | 76 | overtime added after first backlog alert |
| 2026-06-13 | 74 | 74 | normal Saturday staffing |
| 2026-06-14 | 73 | 73 | normal Sunday staffing |
| 2026-06-15 | 75 | 75 | no absence |

The staffed-hour series does not show a staffing drop during the backlog peak.

## Product And Infrastructure Changes

| change_id | timestamp_utc | system | change | rollback_status |
|---|---:|---|---|---|
| CHG-141 | 2026-06-10T16:00:00Z | pricing-page | copy update for annual-plan offer | not rolled back |
| CHG-142 | 2026-06-11T22:30:00Z | billing-export | invoice export batching flag enabled for us-east | rolled back 2026-06-14T00:10:00Z |
| CHG-143 | 2026-06-12T17:10:00Z | support-console | read-timeout increased from 5s to 15s for billing-status lookups | retained |

`CHG-142` is the only listed change immediately preceding the backlog spike and
touches the system named in the highest-severity incident.

## Caveats

- This source does not include customer chat transcripts.
- This source does not include revenue impact or user-level error logs.
- This source cannot distinguish delayed invoice export from a downstream
  support-console cache defect without additional logs.
