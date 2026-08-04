# History-trajectory boundary identity

Date: 2026-07-26

Parent hypothesis: `persistent_predictive_context_hypothesis.md`

## Eigenquestion

Does the history-state compiler preserve an environment-adapter transition
boundary when the same row enters through sealed trajectory evidence rather
than the ordinary transition-bank path?

## Hypothesis

`build_fiber_action_system` already routes adapter-typed epoch and reset
transitions to partiality, but `select_fiber_history_action_system` checks only
the trajectory's supplemental boundary-index set. Consequently an
adapter-typed terminal row absent from that supplemental set is admitted as an
ordinary factor effect.

Routing both sources through `transition_boundary_kind`, while preserving the
adapter's boundary kind, will reclassify the surviving operation-1 collision
as law-versus-terminal partiality. It will not alter law rows, concrete
observations, histories, or evidence references.

## Discriminating test

Add one adapter-typed epoch boundary to a trajectory with no supplemental
boundary index and require the history compiler to emit no successor target,
retain the adapter boundary kind, and reset both predictive histories. Recompile
the latest sealed evidence and compare row ownership and non-boundary relations.

## Success criteria

The terminal row is owned by a boundary effect with its original kind and
reference; it is absent from ordinary effect classes; the collision is reported
as boundary-contaminated until a predictive context separates it; and all
non-boundary relation witnesses remain unchanged.

## Kill conditions

The terminal row remains a law effect; its boundary kind is rewritten as a
control exclusion; a law row changes identity; histories fail to reset; or
evidence references migrate between relations.

## Claim boundary

This repairs transition lifecycle identity. It neither supplies the missing
context coordinate nor changes the external level counter.
