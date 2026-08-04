# Context-transition ownership versus task non-discharge

Date: 2026-07-26

Parent transaction: `context_crossing_frontier_operation0_hypothesis.md`

## Eigenquestion

When a same-epoch adapter-unclassified repaint is an exact previously witnessed
source-operation-successor transition, does task non-discharge make that edge a
control no-good, or does the transition remain traversable under a changed
predictive context?

## Hypothesis

Task adjudication and transition partiality have different owners. An open level
counter says only that an edge did not finish the task. It cannot erase an exact
within-epoch transition witness. If the observed repaint matches a previously
witnessed law triple `(source, operation, successor)`, the multilife controller
must classify it as a context transition, reset finite predictive histories,
retain its successor, and replan from that successor without adding a control
exclusion.

Likewise, a legacy sealed non-discharge marker cannot override an exact
law-scored triple under the same epoch and carrier. Such a marker remains task
evidence but is not transition partiality.

## Discriminating test

1. Give the multilife controller a model-divergent, same-epoch repaint whose
   exact triple already occurs in its evidence bank. Require a
   context-transition disposition, no no-good, no boundary edge, history reset,
   and replanning from the observed successor.
2. Seal the same triple once as law and once with a supplemental non-discharge
   marker. Require the search-control compiler to retain it as a trajectory
   transition and not emit an exclusion.
3. Preserve control exclusion for a non-discharge edge with no exact law
   witness and preserve adapter-typed epoch/reset boundaries.
4. Recompile the current ARC bank and require the reservoir coordinate and zero
   ambiguity to survive the latest slice.

## Success criteria

Task-open status never substitutes for partial-action identity; exact law
triples remain traversable; finite histories restart at the context transition;
unwitnessed no-goods and typed lifecycle boundaries retain their prior behavior;
and the current graph keeps four contexts with zero ambiguous edges.

## Kill conditions

A task-open edge is traversed without an exact law witness; an adapter-typed
terminal becomes traversable; the duplicate law is still excluded; histories
carry across the respawn; evidence lineage is dropped; or the current graph
loses the reservoir refinement.

## Claim boundary

This repairs control semantics around observed respawns. It does not assert that
the transition finishes Level 3.
