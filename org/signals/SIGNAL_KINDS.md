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
| `duty_overdue` | active | `closure_daemon.py` (KR with `recurrence` + `last_attested` past `next_due + grace_period`) | role's executive inbox (gate kind `DUTY_PERFORMED` for attestation reply) | info → warn after grace → critical after 2× recurrence |
| `endpoint_double_invoice` | reserved | (future typed_endpoint_pack pre-check OR post-hoc audit; not built) | research_director / typed_endpoint_pack mutator briefing | info — diagnostic only |
| `primitive_dead` | reserved | (future GP-220 ROI scorecard emitter; not built — needs ≥2 confirmed dead primitives across two 28-day windows before promotion to active) | product_manager (new role; future) | warn — operator-time review |

## `duty_overdue` — rationale (2026-05-06)

Roles have STANDING DUTIES with descriptive cadence labels in their
mandates ("per-substrate-close", "weekly", "per-iteration") but until
2026-05-06 there was no enforcement primitive: a role could silently
skip a duty for weeks and the only signal was post-hoc absence of
artifacts.

The closure_daemon already polls Objectives + Key Results + Tasks for
deadline-shaped pressure (`closure_deadline`, `review_overdue_threshold_days`,
`budget_cap_usd`). Recurring duties fit the same shape — a duty is just
a KR whose deadline is `last_attested + recurrence` rather than a fixed
calendar date.

Mechanism (role-agnostic, all roles):

1. Author the duty as a KR with `owner_role`, `recurrence` (ISO-8601
   duration, e.g. `P7D`), `last_attested`, `attestation_method`,
   `artifacts_required`. Files live in `org/key_results/`.
2. closure_daemon computes `next_due = last_attested + recurrence`.
3. If `now > next_due + grace_period` → emit a `duty_overdue` gate of
   kind `kr_duty_overdue` to `ztare_workspace/gates/pending/`.
4. Role attests by submitting a gate of kind `DUTY_PERFORMED`
   referencing the KR id + the artifact produced. The gate signature
   updates `last_attested` on the KR.

This fits the `conversation_stagnation` discipline IN REVERSE: that
kind is reserved because the pattern is rare and detection is fragile.
`duty_overdue` is built directly because (a) the predicate is
deterministic (timestamp arithmetic, no fuzzy detection), (b) two
concrete KRs are authored at the same time as this kind goes active
(`rd_apparatus_l2_review`, `manager_weekly_okr_walk`), satisfying the
"don't ship a single-data-point mechanism" rule, (c) the consumer (the
role's executive inbox via existing gate flow) already exists.

If `duty_overdue` empirically misfires or fails to fire, treat that as
the same kind of evidence that motivated the `conversation_stagnation`
RESERVATION: tighten or roll back rather than expand.

## `endpoint_double_invoice` — rationale (2026-05-06 PM)

Source: NS Track B Codex session. The operator-reframe pattern that
surfaced this kind: Codex was over-weighting source-provenance
hygiene (because recent failures were tautology / source-substitution
class) and treating duplicate workmap fields as fresh PDE burden.
The reframe forced a target-function check that exposed the
duplicate: `capacity_of_macroscopic_clock_sources` was
extensionally a projection of `parabolic_low_high_capacity` from
a carried `PhaseLatencyControlGramianReceipt`. The endpoint could
be discharged by projection of an existing receipt; treating it
as new doubled the work.

Generalized rule (added to RD mandate): **before treating any top
workmap field as a new PDE estimate, run endpoint-type compression
against carried source objects. If the field is extensionally a
projection of an existing receipt, close it by projection; only
then call the residue "hard PDE."**

**This kind reserves a name for the post-hoc detector** that fires
when typed_endpoint_pack OR the RD review notices an endpoint was
extensionally a projection that could have been closed without LLM
patch. Reserved-not-built per the standard
`feedback_ztare_on_ztare_postmortem` discipline: build the emitter
only after 2+ independent observations (we have 1 today; need a
second from another substrate before mechanizing).

When/if built, the emitter should fire INFO-severity to RD's
review channel + flow into typed_endpoint_pack's mutator briefing
as a "compression candidate" hint. See
`research_areas/private/seams/protocol/GP-223_endpoint_type_compression_gate_seam.md`
for the proposed gate that would prevent the issue at PRE-LLM-PATCH
time (separate from the post-hoc detector this kind would emit).

## `primitive_dead` — rationale (2026-05-06 PM)

The 2026-05-06 GP-220 reflexive primitive ROI audit produced its first
scorecard. Dead-band candidates surfaced (R8/R9/R10/R11/R12/R13/R14/R16
all engaging at <5% over 1857 eligible iters). Whether this is a
real "primitive is decorative" signal or a logging-name mismatch is
unclear at v1.0 of the audit.

This kind reserves a name for the future emitter that fires when a
primitive lands in the `dead` band of the scorecard for two
consecutive 28-day windows AND has been engagement-eligible on
≥50 iters total. Two-window minimum protects against a single-data-
point audit-classifier bug (the same discipline that gates
`conversation_stagnation`).

When/if built:
1. The emitter fires ONE damage signal per dead primitive per window
   (idempotent on primitive_id × window_start).
2. The consumer is the PM-of-ZTARE role's executive inbox (the role
   itself is a future seam — drafted 2026-05-06 PM but not formally
   instantiated).
3. The action surface is "review + retire" not "auto-disable" — same
   discipline as the GP-102 reflexive_audit's Component 4 (proposes,
   doesn't auto-promote).

Until built, the GP-220 audit's verdict bands sit in the json/md
output as advisory; operator reviews manually.

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
