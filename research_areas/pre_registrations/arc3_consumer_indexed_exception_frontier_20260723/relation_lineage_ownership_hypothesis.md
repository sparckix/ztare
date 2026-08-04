# Relation-lineage ownership

Date: 2026-07-26

Parent result: `third_boundary_source_operation3_result.md`

## Eigenquestion

Can evidence lineage be owned by the witnessed source-operation relation
without changing any transition, effect, target, support, or frontier identity?

## Hypothesis

`PartialActionSystem.effect_evidence_refs` intentionally aggregates support over
an operation/effect class. It is therefore the wrong owner for a concrete
reachability edge's evidence lineage. Retaining a separate
`relation_evidence_refs[(source, operation)]` map at compilation and consuming
that map in the boundary-reachability lowering will:

- keep the current partial-action relation and action-system SHA stable except
  for the explicit receipt schema extension;
- attach the latest op3 row only to its witnessed source-operation relation;
- leave graph nodes, effects, targets, support identities, boundary counts, and
  the selected frontier unchanged;
- prevent a relation receipt from claiming a witness owned only by a peer
  relation with the same effect.

## Discriminating test

Add relation-owned evidence lineage to the common partial-action system. Use a
fixture with two sources sharing one operation/effect class but distinct
evidence references, and assert that each reachability edge retains only its
own reference. Recompile the current sealed bank and compare all scientific
graph identities and the selected frontier before and after the change.

## Success criteria

Each edge's references are a subset of the observations compiled for that exact
source-operation relation; shared effect support remains aggregated; no
successor or effect changes; and the current frontier is unchanged.

## Kill conditions

Any relation, target, effect, boundary classification, support identity, or
frontier changes; a shared effect loses its aggregate support; or a peer
relation's reference remains attached.

## Claim boundary

This repairs evidence provenance. It does not add task evidence or change the
Level 3 counter.
