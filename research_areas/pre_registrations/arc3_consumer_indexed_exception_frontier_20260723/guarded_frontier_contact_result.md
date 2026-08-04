# H-ARC3-GUARDED-FRONTIER-CONTACT-20260727-49 Result

## Verdict

Refuted by route-selection drift.

The seed and carrier execution identities matched the preregistration, and the
probe completed a governed 13-action transaction. The adapter reported zero
levels gained and kept the task open. The archived slice is
`raw/episodes/eval_slices/eval_20260727T154419281388Z.jsonl`.

## Discriminator

The planning receipt contains two different plans:

- `observed_partial_action_frontier.actions` is the expected route
  `(0,0,0,0,0,0,0,0,2,1,1,3,1)`.
- `boundary_reachability_frontier.actions` is a 66-action route beginning with
  twenty `0` operations.

The selector gave the second plan authority. With budget 13, the executed trace
was thirteen `0` operations. Execution therefore agreed with the active plan;
the preregistered continuation experiment never reached the adapter.

## Consequence

The run supplies no verdict about operation `1` at source `8f9dcb28…` and no
Level 3 completion claim. It isolates an apparatus boundary: the old
boundary-relevance score can override a separately compiled and preregistered
continuation experiment without comparing their expected information yield or
execution cost.
