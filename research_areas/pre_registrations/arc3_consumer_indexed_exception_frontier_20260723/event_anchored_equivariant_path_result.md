# Event-anchored equivariant path result

Date: 2026-07-26

Status: refuted

The epoch-0 completion has two primitive direction runs before the
finite-configuration event and three after it. The held-out epoch-1 completion
has seven before and twelve after. None of the five non-discharge terminal
sections contains the anchor, so both tested languages rank the completion
above every failure.

The direction-run language aligns five of six template tokens but skips the
anchor. Its score is `5/13`; the reversed template scores `6/13`, and
independent per-step rotation also scores `6/13`. It therefore fails the global
equivariance and order tests.

The relative-turn language aligns all four template tokens, including the
anchor. Its score is `4/11`, but its three motion tokens are the same
orthogonal-turn invariant. Reversing the word produces the same score. The
apparent match is a repeated right-angle motif rather than a directed action
mechanism.

Motor-path imitation is therefore rejected. The shared configuration event
remains a phase marker, but the next object should be the action-conditioned
relation among controlled object, configuration, and attempted destination at
the terminal edge. This relation can express an affordance natively while
leaving trajectory length and route geometry as implementation coordinates.

Evidence: `event_anchored_equivariant_path_audit_result.json`.

