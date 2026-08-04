# H-GPSA-GUARDED-PROTOCOL-PRICING-20260727-51 Result

## Verdict

Confirmed.

Twenty-two focused common and worldmodel tests passed. The sealed ARC audit was
read-only and invariant to protocol, committee, and learned-library order.

## Measured protocols

| Protocol | Compatible mechanisms | Response cells | Primitive actions | Control tokens | Weighted yield | Yield density |
|---|---:|---:|---:|---:|---:|---:|
| observed continuation | 18 | 8 | 13 | 3 | 1.36102343 | 0.08506396 |
| boundary reachability | 3 | 3 | 66 | 16 | 1.83333333 | 0.02235772 |

The selector chose `observed_continuation`, the exact word
`(0,0,0,0,0,0,0,0,2,1,1,3,1)`. Its preparation ends at source
`8f9dcb28…`; probe `1` remains separate. Compiled skills reduced only the
control coordinate: the primitive execution cost stayed 13.

Typed boundary responses remained response cells. No missing response was
invented, no undefined preparation edge was crossed, and no environment action
occurred.

## Consequence

The common response-partition selector can replace the planner's unpriced
boundary-first precedence. A separate hypothesis must verify that integration
offline before another environment transaction.
