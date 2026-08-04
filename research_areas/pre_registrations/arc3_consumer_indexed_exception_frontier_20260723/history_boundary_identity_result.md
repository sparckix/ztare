# History-trajectory boundary identity result

Date: 2026-07-26

Status: confirmed

The history compiler had a split lifecycle path. Ordinary transition lowering
called `transition_boundary_kind`, while sealed trajectory lowering consulted
only supplemental boundary indices. The operation-1 row at
`eval_20260724T231804834496Z.jsonl#65` therefore entered the mechanism relation
as a normal factor effect despite carrying adapter identity
`epoch_boundary / terminal_state:GAME_OVER`.

The compiler now detects adapter boundaries on both paths, retains their
specific kind, and resets action and operation/effect histories. A fixture with
no supplemental boundary index confirms that an epoch boundary has no successor
target and retains its original evidence reference.

Recompilation moved the row from effect `ee1be1a5…` to boundary effect
`12a59233…`. The operation-1 collision is now correctly reported as one
boundary-contaminated relation at every action and operation/effect suffix
through length 32. Non-boundary witnesses retained their relation ownership.

This fixes transition lifecycle identity. It does not supply the context that
separates the safe and terminal presentations.
