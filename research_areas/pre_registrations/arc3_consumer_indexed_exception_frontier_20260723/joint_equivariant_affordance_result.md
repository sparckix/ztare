# Joint-equivariant affordance result

Date: 2026-07-26  
Hypothesis: `H-ARC3-JOINT-EQUIVARIANT-AFFORDANCE-20260726-30`  
Result artifact: `joint_equivariant_affordance_audit_result.json`

## Verdict

Confirmed.

One shared D4 action on the raw destination footprint and square
finite-configuration matrix produced joint code `c1968343…`. The code matched
the held-out epoch-1 completion and none of the five epoch-1 `GAME_OVER`
edges. Every terminal input had a supported operation displacement, one
controlled-object origin, and a square configuration.

The active epoch contains four distinct configuration orientations. Pairing
each with the fixed H29 target footprint gave:

| Descriptor | Active matches |
|---|---:|
| shared joint orbit | 1 |
| footprint only | 4 |
| configuration only | 4 |
| independently canonicalized product | 4 |

The unique joint preimage has configuration digest `4dd96788…`, appears in 36
admitted active states, and carries direct bank lineage. The already observed
non-discharging target edge has configuration `293fb91a…` and does not match
the joint code.

## Mechanism

The four active configurations are rotations/reflections of one equality
pattern. Canonicalizing footprint and configuration separately collapses all
four orientations and discards the relation between them. Applying the same
group element to both preserves that relative orientation and separates the
single compatible configuration:

```text
4dd96788…
001100
001100
001111
001111
000000
000000
```

The selected representation is therefore an oriented affordance relation, not
an isolated target property or an isolated configuration property.

## Claim boundary

The result certifies the cross-epoch joint code and an evidence-backed active
configuration preimage. It does not show that a selected-configuration state
can reach the target relation, that a proposed route is safe, or that Level 3
is complete.
