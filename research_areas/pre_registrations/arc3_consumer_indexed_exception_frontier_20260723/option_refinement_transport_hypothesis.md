# Option transport across predictive refinement

Date: 2026-07-26

Parent result: `component_reservoir_audit_result.json`

## Eigenquestion

Can an option program retain its identity and evidence lineage when one prior
initiation state refines into several predictive-context children?

## Hypothesis

An option's initiation digest names a node in the prior control graph. A
predictive refinement supplies a parent morphism from each refined node back to
that prior node. Reindexing option initiation through the inverse image of this
morphism will preserve the option's operation and lineage identity while
allowing its current images to become stable, context-gated, partially
supported, or unsupported according to witnessed child edges.

Direct lookup by the refined node digest incorrectly reports every option as
absent. Parent transport should remove that artifact without borrowing an
operation between siblings.

## Discriminating test

Compile a fixture in which one parent initiation has two refined children. Give
both children complete but context-distinct option images and require a
context-gated result with unchanged option identity. Remove one child's edge and
require partial support rather than edge borrowing. Reindex the six current ARC
options and require that no option fails solely because its prior initiation
digest is absent after refinement.

## Success criteria

Every current child is resolved only through an explicit parent lineage; option
and evidence identities remain stable; variants name current child and terminal
nodes; missing child edges stay missing; and the live six-option bank is no
longer uniformly unsupported by `initiation_source_absent`.

## Kill conditions

A child resolves without an explicit parent; a sibling edge is borrowed; option
identity changes; failed children disappear from the receipt; or the live
options remain absent after a valid parent morphism is supplied.

## Claim boundary

This transports previously learned action chunks across state refinement. It
does not validate their unobserved images or change the external level counter.
