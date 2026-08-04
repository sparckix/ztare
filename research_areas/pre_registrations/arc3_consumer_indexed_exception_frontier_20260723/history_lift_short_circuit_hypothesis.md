# History-lift selector short-circuit

Date: 2026-07-26

## Eigenquestion

Can the history-lift selector stop after the shortest zero-boundary-ambiguity
suffix without changing the selected action system?

## Ordering argument

The selector first minimizes boundary-contaminated non-commutation, whose
lower bound is zero. Among candidates attaining that minimum it orders by
suffix length before remaining non-commutation, fiber count, and history
family.

Once one family reaches zero at length `L`:

- larger lengths in that family cannot win;
- the other family needs evaluation only through length `L`;
- if it also reaches zero, its larger lengths cannot win.

## Discriminating test

Implement the dominance short-circuit while retaining an exhaustive-candidate
mode. On the same evidence inputs, require both modes to select identical:

- history family and suffix length;
- action-system SHA-256;
- boundary non-commutation count;
- section and relation receipts.

Also require a fixture where the second family wins at the same or shorter
length to remain selectable.

## Predictions

The current live evidence will evaluate four candidates—action lengths zero
and one, operation-effect lengths zero and one—instead of 66, while selecting
action suffix length one with the same action-system hash as exhaustive mode.

## Kill conditions

Any selected identity changes, the short circuit assumes zero before
observing it, a potentially shorter second-family candidate is skipped, or
candidate pruning changes a scientific receipt beyond explicit search
diagnostics.

