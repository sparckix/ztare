# Operational Diagnosis Demo Charter

## Task

Test whether ZTARE can take a small operations dataset, state an explicit
root-cause claim, preserve counter-hypotheses, and route the claim into the
in-loop validator without pretending that synthetic local data is a customer
deployment.

## Bounded Claim

In the synthetic fixture, the best-supported explanation for the Week 23
billing-support backlog spike is the `us-east` billing-export failure between
2026-06-11 and 2026-06-14. Staffing shortage, seasonality, and the pricing-page
copy change are weaker explanations on the available evidence. Support-console
cache misses are a real symptom channel, but on this fixture they follow the
export failures and do not independently explain the spike.

## Non-Claims

- Not a real customer incident.
- Not proof of general organizational diagnosis.
- Not a replacement for cognitive-firm workflow management.
- Not a complete root-cause automation product.

## Next Falsifier

Reject or demote the claim if export-worker logs show healthy exports during
the spike, or if support-console cache misses precede the export failures and
explain the missing billing status without export failure.
