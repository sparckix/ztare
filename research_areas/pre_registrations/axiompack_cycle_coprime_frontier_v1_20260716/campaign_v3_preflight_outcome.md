# Campaign v3 provider-free preflight outcome

Closed on 2026-07-16 before navigation or provider dispatch.

## Frozen input

- campaign: `campaign_v3.md`
- typed blueprint: `campaign_v3.typed_blueprint.json`
- initial exact strata: carrier sizes 2–6
- size-6 per-stratum deadline: 5,400,000 ms
- canonical-model cap: 1,146

## Outcome

The provider-free preflight exited nonzero after the size-6 solver reached its
deadline. The terminal adapter message was:

```text
exact SMT census did not exhaust stratum sort_sizes:S0=6: unknown: canceled
```

The process used one CPU continuously for about 90 minutes, remained within
memory capacity, and dispatched zero provider calls. Because the solver did not
return final UNSAT, v3 has no complete size-6 universe and authorizes no bounded
or unrestricted mathematical inference.

## Apparatus findings

1. A full size-6 isomorphism-class census is too expensive for this admission
   route under the frozen deadline.
2. The CLI discarded the incomplete enumeration receipt and partial class
   count when the adapter raised its terminal error.
3. The VPS campaign wrapper would have repeated a complete exact census before
   the campaign inlet performed the same provider-free construction.

The generic repairs preserve typed incomplete-census artifacts and remove the
duplicate wrapper census. The scientific redesign for v4 keeps exact sizes 2–5
as the discovery chart and makes size 6 a targeted held-out boundary, alongside
sizes 7–9.
