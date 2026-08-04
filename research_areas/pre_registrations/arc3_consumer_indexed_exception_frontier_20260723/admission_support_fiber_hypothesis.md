# Admission-support fiber hypothesis

Date: 2026-07-26

Parent result: `boundary_source_operation1_result.md`

## Eigenquestion

Can a coarser evidence-admission support fiber remove history-induced
duplicate acquisition targets without altering the history-sensitive control
relation?

## Discriminating test

Recompile the current boundary-reachability system with:

- full history-lifted identity for graph nodes and edges;
- exact rendered-source digest as admission-support identity;
- operation support aggregated only within equal admission identities;
- no edge, effect, or successor aggregation.

Require the just-executed operation-`1` query at source
`943c3bdc3d7736f8e4ac3d5b0ef3ebf642c27e845ac8f672270524de8812369e`
to disappear from the acquisition frontier because it has exact prior
support. Require operation `0`'s newly admitted edge to remain present and
require all section/transport checks to pass.

## Predictions

- support-identity count is smaller than history control-node count;
- the operation-`1` false gap disappears;
- relation and deterministic-edge counts remain unchanged;
- the next boundary-relevant target differs from the redundant query;
- no target edge appears at a history node that lacked a witnessed edge.

## Kill conditions

Any edge or successor is borrowed, relation counts change merely from support
aggregation, the duplicate operation remains a frontier target, operation
`0` disappears, or common code imports substrate vocabulary.

