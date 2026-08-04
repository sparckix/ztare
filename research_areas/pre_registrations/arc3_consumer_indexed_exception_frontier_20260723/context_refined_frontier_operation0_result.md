# Context-refined frontier operation-0 result

Date: 2026-07-26

Status: target reached; two-transition decomposition falsified

The no-worker probe selected the registered 130-node action system, source,
operation, flags, and 44-action route. It executed two 22-action legs:

1. `[0] * 20 + [2, 0]` ended in an exact known environment-context
   transition. The observed successor was retained, finite histories reset,
   and the controller replanned without an exclusion.
2. `[0] * 20 + [2, 0]` reached source `2fb837ceaed2…` and executed the
   registered operation 0. The adapter did not type the repaint, so the
   evidence-side classifier recorded an inferred environment boundary.

The prediction of two context transitions followed by a one-action third leg
was false. The registered target nevertheless executed within the exact
budget, with no worker-selected action and no no-good on the known transition.
One row was admitted at index 43. The sealed slice is
`eval_20260727T001613804937Z.jsonl`, SHA-256
`822f26b11da99760b3c940f6599bd2c81deec3c32b927c70402fccaebcd815a7`.

Recompilation retained 130 nodes, four contexts, five context transitions, and
zero ambiguity. The new edge increased typed boundaries from five to six and
relations from 139 to 140. All six imported options remain partially
supported. The next boundary-relevant intervention is operation 3 at the same
source through route `[0] * 20 + [2, 0] + [0] * 20 + [2, 3]`.

The adapter reported zero levels gained and two completed levels.

