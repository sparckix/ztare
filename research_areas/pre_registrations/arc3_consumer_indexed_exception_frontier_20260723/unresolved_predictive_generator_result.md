# Unresolved predictive generator result

Date: 2026-07-26

Parent hypothesis:
`unresolved_predictive_generator_hypothesis.md`

## Transaction

The no-worker acquisition transaction satisfied its control contract:

- policy: `predictive_quotient_frontier`;
- consumer action: `execute_witnessed_predictive_route`;
- route: `[1]`;
- source class:
  `f4e11f34a1e054b66c79fd3073aa8da2c55b1f9eb86a11ca1b1f3c2688c9f60b`;
- boundary non-commuting relations: `0`;
- steps: `1`;
- level increment: `0`;
- raw-bank rows admitted: `0`.

The ordered lineage was archived at
`projects/arc3_ls20_gov/raw/episodes/eval_slices/eval_20260726T170817107981Z.jsonl`
with SHA-256
`4a6e3ed91aa4eff0fc8f07f4b4ad17a212f154533cffa4398316f9dc4da1ff6b`.

## Recompilation

The new operation-effect witness has effect SHA-256
`73e94a8d04356cc52fd15866c5871c7a8e759c81a3d76e37fedc5131ee7153f4`.

The quotient changed as follows:

- history fibers: `81 -> 82`;
- predictive classes: `74 -> 75`;
- option count: `6 -> 0`;
- section: pass;
- transport: pass;
- boundary relations: unchanged at `5`;
- boundary non-commuting relations: unchanged at `0`.

The former two-member initiation class split into singleton classes:

- `408a494c2a69bb635558f85b286a4772c8b42352277dd1137871eafda0d8c8ef`
  maps to
  `3c391f0de1f2457d1fba8dd97409fb8eecf98ad99a8adc094d2e1a09d4487fd4`;
- `60f76128a94478ca291a8dce74f192c5151a72c42e7e7495d29d7fee86086e33`
  maps to
  `5cc4f4a8c9b7b7b855df0ed441b3df01bae8e99d301a3384dd5a0f2d50d9645b`.

The current compiler treats `unknown` as an operation outcome. Therefore an
observed relation on one member and missing support on the other is sufficient
to split behavioral state identity and remove every option requiring repeated
initiation support.

Evidence:
`unresolved_predictive_generator_audit_result.json`.

## Interpretation limit

The class increase does not yet establish a new controllability mechanism.
It may be caused entirely by asymmetric evidence coverage. The next offline
test must distinguish a shared observed contradiction from a support-only
split before another intervention is authorized.

