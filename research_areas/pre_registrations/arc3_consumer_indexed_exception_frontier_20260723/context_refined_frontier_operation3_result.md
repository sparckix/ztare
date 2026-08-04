# Context-refined frontier operation-3 result

Date: 2026-07-26

Status: target reached; sibling boundary mapped

The no-worker probe selected the registered source, operation, flags, and route.
It executed two 22-action legs. The first ended in the known context transition
and replanned without exclusion. The second reached source `2fb837ceaed2…` and
executed operation 3, which produced an inferred environment boundary.

One evidence row was admitted at index 43. The sealed slice is
`eval_20260727T002329717636Z.jsonl`, SHA-256
`502fa55dc7b57b415ca9d1f5bfa9aba45e158274488728f4f28291c33c97afcc`.
No worker selected an action. The adapter reported zero levels gained and two
completed levels.

Recompilation retained 130 nodes, four contexts, five context transitions, and
zero ambiguity. Relations increased to 141 and typed boundaries to seven. The
source now has operations 0 and 3 mapped as partial, so the boundary frontier
moved to source `495dd39e5a54…`, which already has an `epoch_boundary` witness
under operation 1. The new operation-0 route is:

`[0] * 20 + [2, 0] + [0] * 20 + [2, 1] + [0] * 20 + [2, 0]`.

