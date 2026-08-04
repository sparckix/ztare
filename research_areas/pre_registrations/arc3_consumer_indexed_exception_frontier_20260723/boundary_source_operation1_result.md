# Boundary-source operation-1 result

Date: 2026-07-26

Parent hypothesis: `boundary_source_operation1_hypothesis.md`

## Transaction

The no-worker probe matched the registered policy, consumer action, source,
operation, budget, and route. It executed all 12 actions and sealed
`raw/episodes/eval_slices/eval_20260726T180758839355Z.jsonl` with SHA-256
`a7d6abd11452280884a6f20592cf41c9ec6fe19f4f9a9db43af73592ec6a1145`.
The task counter did not change.

Operation `1` stayed in-lifecycle with factor effect:

`controlled_base translate (5,0); ordered feasibility -1; ordered budget -1`

and effect SHA-256
`fec1d30f7e61dad70d5f14cacee530bc07bade8f838a1b271eadb839ea338781`.
It supplies the opposite directional basis from operation `0`.

## Admission counterexample

`evidence_grown_by` was zero. The persistent bank already contains four
rows with the exact same rendered source and operation `1`; all four also
have the same successor. Their bank indices are `14807`, `14892`, `15601`,
and `15667`.

The history-lifted control graph therefore surfaced a false acquisition gap.
History is needed for transition consequences elsewhere, but it is not part
of the evidence store's admission-support identity for this exact
source/action.

## Apparatus consequence

Control node and admission support must be separate projections. Nodes that
share an exact rendered source may share the fact that an operation was
already admitted, while retaining distinct history-indexed edges and
successors. No outcome may be copied between them.

