# H89 reverse-order memory-content result

H89 supports order robustness for H88's local content comparison. It also
contains one negative-transfer pair, which prevents treating causal recall as
uniformly beneficial across stochastic controllers at the same observation.

## Result

All three pairs executed redundant true memory before causal mechanics. Every
arm restored the H88 initial observation, received one 3,849-byte injection,
spent 20 charged actions, and retained distinct controller, runtime, and
trajectory identities.

| Pair | Redundant Level 1 | Causal Level 1 | Causal task delta | Causal composite delta |
|---|---:|---:|---:|---:|
| 1 | action 16 | action 13 | 0 | +0.03 |
| 2 | miss | action 20 | +1 | +0.81 |
| 3 | action 13 | action 20 | 0 | -0.07 |

Causal mechanics scored `3/3` versus `2/3`, won two of three paired scores,
and averaged `+0.2567` compared with the preregistered `+0.15`. Learned top-1
allocation remained the causal revision. Together, H88 and H89 contain three
pairs in each order: causal mechanics completed `6/6`, redundant true memory
completed `4/6`, and the six-pair mean causal-minus-redundant effect was
`+0.2833`.

Pair 3 is the important boundary case. Its redundant arm visited the marker
early and completed at action 13. Its causal arm treated the state as already
matched, tested direct terminal entry, and completed only at action 20. The
same intervention therefore has positive average value and negative marginal
value in one controller trajectory whose exact initial observation is
identical to the others.

## Evidence

- machine result: `h89_pairwise_memory_content_reverse/result.json`
  (`2093a1c1a12b7bc3362ef4e66f684f38fab8e545635b62f5f7d3ef6a06479fcc`)
- frozen manifest: `h89_pairwise_memory_content_reverse/manifest.json`
- arm receipts: `h89_pairwise_memory_content_reverse/arms/`
- incremental turn checkpoints:
  `h89_pairwise_memory_content_reverse/turns/`
- symmetric matched settlements:
  `h89_pairwise_memory_content_reverse/settlements/`

