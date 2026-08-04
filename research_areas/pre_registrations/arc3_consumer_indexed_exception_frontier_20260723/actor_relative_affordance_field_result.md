# Actor-relative affordance field result

Date: 2026-07-26  
Hypothesis ID: `H-ARC3-ACTOR-RELATIVE-AFFORDANCE-FIELD-20260726-39`  
Verdict: refuted

All four operation maps were admitted and the actor-relative field separated
the H38 witness. Search nevertheless stopped after 128 generated / 94 expanded
states at another same-time (`78 == 78`) simulation counterexample.

At controlled base `(25,34)`, every immediate destination footprint matched.
The concrete states differed only by a structured eight-cell ring at rows
16–18 / columns 35–37. Operation 0 moved both actors to `(20,34)`; from there,
the differing object entered the next operation-0 footprint, so the successor
affordance fields diverged.

This is the boundary failure of a finite local crop: transition closure
requires the next shell, and repeating that move merely grows the crop. The
appropriate coordinate is the mutable world configuration—persistent,
consumed, or spawned object identities and locations—separate from the
controlled actor, static world, and UI. A larger hand-chosen radius is
disallowed.

Evidence:

- `actor_relative_affordance_field_audit_result.json`
- `actor_relative_affordance_field_audit.py`
