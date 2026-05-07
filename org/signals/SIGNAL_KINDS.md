# `org/signals/` — kind catalog

This file is the **single source of truth** for damage-signal `kind` strings.
The schema field itself is free-form (`DamageSignal.kind: str` in
`src/ztare/signals/damage.py:46`), but conventions are tracked here so
emitters and consumers don't drift.

A kind may appear in this catalog with status `reserved` — meaning the
name is reserved for future use but no emitter or consumer is wired in
yet. Reserving a name is cheap; it prevents two future implementations
from picking the same string for different concepts. Building a
mechanism without sufficient empirical signal is *not* cheap — see
`feedback_ztare_on_ztare_postmortem.md` for the canonical lesson.

## Catalog

| `kind` | Status | Emitter (current or planned) | Consumer | Severity convention |
|---|---|---|---|---|
| `cost_spike` | active | spend tracker | manager | warn |
| `contradiction` | active | various | manager / principal | warn–critical |
| `handoff_conflict` | active | session boundary | manager | warn |
| `output_regression` | active | gate telemetry | manager | warn |
| `integrity` | active | various | principal | critical |
| `mandate_drift` | active | `signals/autoemit.py` | manager | warn |
| `mandate_drift_unverifiable` | active | `signals/autoemit.py` | manager | warn |
| `mandate_missing` | active | `signals/autoemit.py` | manager | critical |
| `goals_not_inspected` | active | `signals/autoemit.py` | manager | warn |
| `session_id_forgery` | active | `signals/autoemit.py` | principal | critical |
| `dag_stagnation` | active | `autoresearch_loop` (GP-134 DAG steering, 5+ iters stuck on same weakest node) | mutator briefing | info |
| `evidence_changed_mid_run` | active | `autoresearch_loop` (GP-182, fires when `evidence_reload_per_iter: true` AND content SHA differs from prior iter) | audit/replay only | info |
| `noether_gaming_streak` | active | `autoresearch_loop` (fires after 3+ consecutive iters where mutator declared LAGRANGIAN but produced zero non-degenerate Noether invariants) | mutator briefing / manager | warn |
| **`conversation_stagnation`** | **reserved** | (future watcher; not built) | (future epistemic-auditor mandate) | info |

## `conversation_stagnation` — reservation rationale (2026-04-28)

The GP-180/GP-181 pivot (paper 7 §11.11) surfaced a class of failure mode
the apparatus has no current mechanism for: the **operator-LLM
conversation gets stuck in a local minimum** when iteration on apparatus
mechanics produces incrementally better machinery while the implicit
loss function ("minimize MRE on g_obs") remains unquestioned.

The mutator-layer analog is mechanized — `REFRAME` / `ANALOGY` / Erdős
cold-LLM seed fire on stagnation predicates. The operator-conversation-
layer analog is not. The instinct to mechanize it immediately was
*itself* a frame-anchoring move (see *Three Legs of ZTARE*, Leg 1
sub-pattern, "Inversion is fractal across layers").

The right discipline:

1. **Reserve the signal kind now.** This file is that reservation. Any
   future emitter that detects "5+ turns on the same project, no commit
   / no rubric edit / no score movement, all turns iterating on
   apparatus mechanics" should use `kind: conversation_stagnation`.

2. **Do not build the emitter or consumer until the pattern recurs.**
   The minimum bar is two more independent sessions exhibiting the
   pattern. Two more observations protect against a single-data-point
   threshold-calibration mistake (the `feedback_ztare_on_ztare_postmortem`
   sycophancy lesson).

3. **When/if the emitter is built**, it should fire ONE directive into
   `org/directives/` containing a single reframe prompt — *"name the
   implicit loss function this conversation is optimizing, and what
   would change it"* — and immediately self-suppress for the rest of
   the session. Routinizing the reframe move dilutes its force; one
   prompt per session is the cap.

4. **The consumer mandate** belongs on a future `epistemic_auditor`
   role (or as a new clause in `manager_mandate.md`) — not on
   `research_director`, which operates at a different cadence and
   scope.

## Editing rules

- Adding a new kind: append a row, set `status: reserved` initially,
  and write a one-paragraph rationale in this file. Promote to `active`
  only when an emitter and consumer both ship.
- Renaming a kind: forbidden once `status: active`. Add a new kind and
  deprecate the old one over a 30-day window.
- Removing a kind: only if `status: reserved` and rationale no longer
  applies. Document the removal in commit message + git blame.
