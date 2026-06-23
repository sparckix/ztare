---
source_type: source_evidence
---
# Synthetic CHG-142 Design Note

This source is synthetic local fixture evidence for the public operations
diagnosis demo. It describes the mechanism that was missing from the initial
pilot packet.

## Change Summary

`CHG-142` enabled the `invoice_export_batching_v2` flag for the `us-east`
billing-export workers at `2026-06-11T22:30:00Z`.

The flag changed the export worker in three ways:

| area | previous behavior | CHG-142 behavior |
|---|---|---|
| invoice grouping | export one customer-account shard at a time | merge adjacent customer-account shards into one batch when the invoice-row count is between 18,000 and 21,000 |
| downstream index write | commit support-console billing-status index after each shard | defer the downstream index write until the merged batch finalizes |
| duplicate warning check | run duplicate-payment warning check after the index commit | run duplicate-payment warning check before the deferred index commit |

## Failure Path

The exported invoice rows were durable in the billing application, but the
support-console billing-status index waited on the deferred index commit. When
the merged batch exceeded 18,000 invoice rows, the duplicate-warning branch and
the downstream-index branch both attempted to hold the `billing_status_index`
lease.

The lease conflict produced this sequence:

1. The export worker wrote the invoice rows.
2. The duplicate-payment warning branch attempted to check for duplicate rows
   before the downstream index commit completed.
3. The downstream-index branch waited for the same lease.
4. The worker retried until the 900-second job timeout.
5. Early retries emitted `duplicate_payment_warning`; later attempts emitted
   `downstream_console_index_missing` because the support-console index had not
   been committed.

## Rollback Effect

Rolling back `CHG-142` restored per-shard export commits and moved the
duplicate-payment warning check after each shard-level index commit. Batches
`b-7108`, `b-7109`, and `b-7110` then completed below 400 seconds with no
error code.

## Boundary

- This note supports a common mechanism for `duplicate_payment_warning` and
  `downstream_console_index_missing` in this fixture.
- It does not claim the same mechanism applies outside the synthetic
  operations dataset.
- It does not remove the need to verify cache behavior during healthy export
  windows.
