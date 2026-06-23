---
source_type: source_evidence
---
# Synthetic Ticket Samples

This source gives concrete examples of what customers and support agents saw.
The rows are synthetic and intentionally small.

| ticket_id | opened_at_utc | queue | primary_tag | customer_text | agent_note |
|---|---:|---|---|---|---|
| T-8841 | 2026-06-12T09:40:00Z | billing | invoice_missing | "The invoice shows in the app but support says there is no billing status." | console billing lookup empty |
| T-8849 | 2026-06-12T11:12:00Z | billing | duplicate_payment_warning | "I got a duplicate payment warning after last night's invoice run." | linked to duplicate-payment warning code |
| T-8873 | 2026-06-12T15:27:00Z | billing | invoice_export_delay | "My invoice did not reach the support portal." | export batch b-7105 missing downstream index |
| T-8904 | 2026-06-13T09:19:00Z | billing | billing_status_unavailable | "The billing page loads but the support team cannot verify it." | cache miss observed after export lag |
| T-8916 | 2026-06-13T16:44:00Z | billing | invoice_export_delay | "Invoice status has been stuck since Friday." | export lag > 10 hours |
| T-8977 | 2026-06-14T08:13:00Z | billing | recovery_confirmation | "Support can see the billing status again." | export batch b-7109 ok |
| T-9002 | 2026-06-15T12:02:00Z | billing | account_question | "Can I change my plan?" | ordinary account question, no export symptom |

## Boundary

- The samples support billing-export and billing-status symptoms during the
  spike.
- The samples do not show pricing-page confusion or sales-copy tags before
  billing tags.
- The samples are not a full customer-impact dataset.
