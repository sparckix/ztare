# Relation-lineage ownership result

Date: 2026-07-26

Parent hypothesis: `relation_lineage_ownership_hypothesis.md`

## Result

The common partial-action compiler now retains relation-owned evidence
references separately from effect-class support references. Boundary
reachability consumes the relation-owned map.

The adversarial two-source fixture passed: both sources retained the shared
effect class and aggregate effect support, while each edge cited only its own
row.

Recompiling the sealed Level 3 evidence preserved:

- 86 nodes and 91 relations;
- 83 support identities;
- 7 boundaries, 83 deterministic edges, and 1 ambiguous edge;
- 114 reachable frontier pairs and 30 boundary-relevant pairs;
- the same length-14 next frontier at source `c1ad28…`, operation `1`.

The op3 lineage is now exact:

- source `4ab929…` cites only
  `eval_20260726T205139058694Z.jsonl#21`;
- source `c1ad28…` cites only
  `eval_20260725T185747154114Z.jsonl#13`.

Evidence: `relation_lineage_ownership_audit_result.json`.

## Consequence

The third-source op3 transaction did reach its registered source. The apparent
cross-source attribution was a receipt-provenance defect, not a transported
path counterexample. Future counterexample refinement must distinguish
relation lineage from globally shared effect support.
