# H88 pairwise memory-content result

H88 supports a narrow content-attribution claim: on the same `ls20` initial
decision, the evidence-derived causal-mechanics bundle improved behavior more
than an equally presented bundle of true but redundant memories. The result
does not establish order independence, online inject-or-silence judgment,
cross-game transport, or benchmark-wide gain.

## Result

Both conditions received one decision-zero injection and exactly 20 charged
actions. Their canonical JSON presentations were each 3,849 UTF-8 bytes.
Every arm restored observation
`e55a1c1775c34a88319adea39042846b6100c4c674bbfc809b9711334430e778`
and retained distinct harness-controller, runtime-session, and trajectory
identities.

The causal condition contained:

- `goal_requires_glyph_match_v1`;
- `floor_marker_edits_state_glyph_v1`.

The redundant-true condition contained:

- `controls_cardinal_v1`;
- `walls_block_without_state_change_v1`;
- `marker_is_not_consumed_v1`.

| Pair | Execution order | Causal Level 1 | Redundant Level 1 | Task delta | Composite delta |
|---|---|---:|---:|---:|---:|
| 1 | causal, redundant | action 13 | action 19 | 0 | +0.06 |
| 2 | causal, redundant | action 15 | miss | +1 | +0.86 |
| 3 | causal, redundant | action 13 | action 14 | 0 | +0.01 |

The frozen criterion passed. Causal mechanics completed Level 1 in all three
arms, versus two of three for redundant true memory, and won the composite
decision score in all three pairs. Mean observed left-minus-right composite
effect was `+0.31`, compared with the preregistered prediction `+0.15`; squared
error between those means was `0.0256`. Mean distinct-observation information
yield delta remained `0.00`.

Outcome credit changed the learned top allocation to causal mechanics,
revision
`e32046fb0d67861ea9174e429768871dfbc4f500ed406e6d39ddbc37974518f3`,
although the source producer had rated the redundant bundle higher (`0.99`
versus `0.96`).

## Interpretation and open confound

The redundant arms often inferred the missing mechanism online. Their costly
branch was approaching the terminal before aligning the state glyph, then
using later actions to discover or repair that mismatch. Causal recall
suppressed that branch without supplying a complete action sequence. The
measured role is therefore early search control: old evidence perturbed which
hypothesis governed action, while the frontier controller still performed
navigation and correction.

All three seeded H88 shuffles placed causal mechanics first, a probability
`1/8` event under independent fair two-arm order. Distinct runtime sessions
prevent direct state carry between arms, but temporal service effects and
investigator-order effects remain possible. A frozen right-first replication
is required before treating the content ranking as order-independent.

The result advances one edge of the proposed compounding circuit:

```text
experience
-> causal consolidation
-> bounded policy intervention
-> matched external outcome
-> corrected intervention priority
```

Critical-mass behavior would additionally require the corrected priority to
improve later autonomous selection, abstention, and cross-context transport.
H88 prices two forced interventions at one prefix; it does not test those
later edges.

## Evidence

- machine result: `h88_pairwise_memory_content/result.json`
  (`9dc9e7fdce2b4479896926c09019da9c896a8ae7e0b9ad6e209cfadadc1de2d7`)
- frozen manifest: `h88_pairwise_memory_content/manifest.json`
- arm receipts: `h88_pairwise_memory_content/arms/`
- incremental turn checkpoints: `h88_pairwise_memory_content/turns/`
- symmetric matched settlements:
  `h88_pairwise_memory_content/settlements/`
- focused verification after settlement: `20 passed`
