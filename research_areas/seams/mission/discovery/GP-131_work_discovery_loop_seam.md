# GP-131 — Work-Discovery Loop (Level 2 Daemon Bridge)

> **Seam metadata** · `seam_id:` GP-131 · `track:` mission · `status:` Open - debate seam, not a spec. · `last_updated:` 2026-05-08


**Status:** Open — debate seam, not a spec.
**Parent:** GP-128 (persistent manager agent — Level 1.5 → Level 2 bridge). This seam is the concrete content of the Level 2 daemon's *autonomous identification of work*, previously gestured at in GP-105 / GP-105b and never built.
**Sibling:** GP-130 (non-LLM substrate) — if adopted, feeds into the discovery loop as one of the checks the daemon can run on its own.
**Date opened:** 2026-04-23.

---

## Eigenquestion

**Can a daemon identify work worth doing without being told, in a way that the principal recognizes as "yes, that's what I'd have asked for", more than half the time?**

The eigenquestion is NOT "can the daemon generate plausible-looking TODOs" — it almost certainly can, from LLM priors alone. The question is whether the daemon's proposals are **decisive** (addressing a real bottleneck the principal would have noticed themselves) rather than **decorative** (surfacing patterns the principal has already decided are unimportant).

The precedent to beat: GP-105 (in-loop improvement) and GP-105b (ex-post improvement) both scaffolded this and produced zero durable "daemon spontaneously proposed X, principal did it, it mattered" artifacts. We need to understand **why they failed** before we build a third version.

---

## Why GP-105 / GP-105b failed (reconstructed; verify before relying)

> **RECONSTRUCTION CORRECTED 2026-04-23.** This subsection was shown to be materially wrong by the precondition audit in the GP-131 spec (`research_areas/private/specs/active/mission/GP-131_work_discovery_loop_spec.md` § Reconstruction Audit). Short version: GP-105 is a *Goodhart-auditor for qualitative rubrics* (built, in production, unrelated to work-discovery); GP-105b is an *ex-post apparatus-improvement scanner* (scaffolded only, never built). Neither is a prior work-discovery *failure*. The failure modes below are correct as general risks of autonomous-agent loops (AutoGPT-class), but they are NOT lessons inherited from this repo's history. Read the audit for the full correction.


Going by memory of the shape of those attempts, not a fresh read:

1. **Surfaced noise, not signal.** Both loops enumerated things that *could* be improved. Without a scarcity filter, every file has something to fix. The principal learned to ignore the feed. Classic recipe-for-alert-fatigue.
2. **No calibration mechanism.** There was no way for the principal to say "that class of suggestion is never useful" and have the loop actually stop surfacing it. The loop had no memory of what had been declined.
3. **Suggestions lacked escalation context.** A proposal like "refactor module X" with no tie to a current research program or open seam is a priority claim the principal cannot evaluate in 30 seconds.
4. **No bounded action.** Proposals were unbounded ("improve this"). Bounded proposals ("run this experiment; cost $3; expected yield is evidence on hypothesis H") are evaluable; unbounded ones are not.

If the reconstruction is wrong in a decisive way, halt and read the actual GP-105 / GP-105b seams before proceeding. The seam's predictions below are contingent on this being roughly right.

---

## What a loop that works would look like

Drawing on the GP-129 panel's decisive predictions as design constraints:

- **(Kauffman) Non-closure hotspots** → the loop's first sweep is `ztare org closure-map`. Any hotspot is a standing candidate for work.
- **(Matzinger) Damage signals** → the loop reads `src.ztare.signals.damage.list_recent()` on wake. Any unresolved critical signal is an automatic escalation, no discovery needed.
- **(Godfrey-Smith) Intent vs procedure** → each proposal states the *intent* ("calibrate push-notification thresholds against real escalations") not the procedure ("run script X"). Lets the principal redirect on intent, which is cheaper than auditing steps.
- **(Wilson) Trail lock-in defense** → the loop deliberately samples *away from* the last-accepted proposal's domain once per wake, to avoid reinforcing whichever groove the last success carved.
- **(Margulis) Membrane check** → the loop verifies worker YAMLs are consistent with their actual invocation contracts, and flags drift.

---

## Proposed discovery sources, ranked by expected signal density

Each source is a well-defined scan the daemon can do in bounded time. The daemon runs each, assembles a candidate list, ranks, picks one or two, escalates.

| Source | What it finds | Expected signal density | Notes |
|---|---|---|---|
| Open TODO boxes in seams under `research_areas/private/seams/mission/` | Partially-completed work the principal committed to | **High** | Self-authored TODOs are pre-filtered for relevance. |
| Unresolved damage signals (`org/signals/damage/`) | Invariant tripwires, cost spikes, silent drift | **High** | A damage signal is already a scarcity-filtered event. |
| Non-closure hotspots from `ztare org closure-map` | Steps with single-agent coverage | Medium | Structural, slowly-changing; daemon should debounce. |
| Stale open seams (no file-mtime update in >14 days) | Seams that lost momentum | Medium | Principal decides: close or resume. |
| In-Flight experiments without recent telemetry updates | Runs that died silently | Medium | Needs a bridge to supervisor state. |
| Pending-publications track (paper drafts with TODO markers) | Paper sections marked incomplete | Medium | Low urgency but compounding. |
| Gemini-reviewer backlog (asks that didn't get handled) | Adversarial critiques deferred | Medium | Honest-signal filter: reviewer already believed these mattered. |

The ranking is a prior, not a verdict. After 30 escalations, tally accept-vs-decline by source and re-weight. The weights themselves are a calibration artifact — part of the Level 2 daemon's memory.

---

## Proposal envelope — the one thing the daemon writes per wake

To keep the principal's attention cost minimal, each wake produces at most ONE 200-word escalation with this shape:

```
Source:        <which discovery source triggered this>
Intent:        <what this is for, in plain English, one sentence>
Candidate action: <specific, bounded, with a cost estimate if non-zero>
What it gives you if you say yes: <expected information / infrastructure yield>
What it costs if you say no: <what happens if you decline — usually "nothing">
Scarcity signal: <why this surfaced now — what changed>
```

Three accept/decline options in the inbox: **proceed**, **defer 7 days**, **never-this-class** (writes to daemon memory; that source class gets downweighted for 30 days).

---

## Scope discipline — what the daemon does NOT do

- Does NOT execute any proposal on its own. Human-in-loop on every one. (Eventually some bands widen; not at Level 2 launch.)
- Does NOT open new research programs. It proposes work within existing programs and infrastructure; program creation is principal-authority.
- Does NOT interact with external services (Slack, email beyond ntfy, GitHub PRs) without explicit per-action authorization.
- Does NOT grow its own scope. If the daemon starts proposing changes to its own mandate, that is a hard-stop escalation, not a proposal.
- Does NOT spend money. Every proposal with an execution cost escalates for spend approval even if under the mandate's per-action cap — discovery-loop proposals are a different budget class from principal-initiated work.

---

## Falsifiable predictions

1. **Accept rate ≥50% by wake #20.** If the first 20 proposals hit below 50% accept, the sources are wrong or the ranker is wrong; retune rather than widen scope.
2. **Accepted proposals produce a durable artifact (seam/spec/evidence row) ≥80% of the time.** If accepts evaporate without producing something audit-able, the daemon is generating busywork.
3. **Zero instances of "the daemon proposed something dangerous and the principal caught it in triage."** If this happens once, review scope discipline immediately. More than once and the loop is a net negative.
4. **Daemon memory compresses.** After 30 wakes, the stored calibration (source weights, never-this-class list, accept/decline log) should be <10 KB. If it bloats beyond that, it's carrying artifacts it shouldn't.

---

## Engineering scope (when it's time to build)

Follows the Level 2 daemon scope from GP-128 § Future Work:

- **New file:** `src/ztare/orchestration/work_discovery.py` — scans each source, returns candidate list with scarcity metadata.
- **New file:** `src/ztare/orchestration/proposal_ranker.py` — applies source weights and never-this-class filter; picks one.
- **Extend:** `src/ztare/orchestration/manager_decision.py` (from GP-128 Level 2) — one branch is "nothing urgent; run work-discovery; maybe escalate a proposal."
- **New storage:** `org/mandates/daemon_calibration.json` (gitignored) — source weights, never-this-class list, accept/decline history. Updated on every inbox triage.
- **Extend:** `inbox_streamlit.py` — three-button triage (proceed / defer-7d / never-this-class).

**Total:** ~250 LOC, plus the Level 2 daemon infrastructure from GP-128 that this sits on top of. Do NOT start until Level 1.5 has been running for ≥1 week and there is calibration data on escalation thresholds.

---

## Sequencing (matches the principal's stated concrete proposal)

1. **Neural + Riemann GPU work as-is** → yields Level 1.5 calibration data; teaches us what escalation thresholds should actually be.
2. **Build Level 2 daemon with the thin work-discovery mode specified here.** Human-in-loop on every suggestion.
3. **Widen autonomous band gradually as mandate calibration earns trust.** Start with "daemon may self-triage the first N% of damage signals based on kind"; never widen to "daemon may execute a bounded action without confirmation" without a dedicated seam and at least 50 observed triage decisions.

---

## Open items

- [ ] Principal review — does the discovery-source ranking match intuition about what's actually scarce?
- [ ] Verify reconstruction of why GP-105 / GP-105b underperformed by reading those seams before building v3.
- [ ] Pick the first two discovery sources to implement (candidates: TODO-scan + damage-signal-scan — both high-signal-density, both cheap).
- [ ] Decide daemon wake cadence: 2h seems wasteful if most wakes have nothing to propose. Alternative: event-triggered wake on damage-signal writes, with a minimum 4h idle wake for discovery sweep.

---

## Debate Log

Replicates the `supervisor_findings_runner --auto-spec` flow in-session (no API spend). Four persona seats argue adversarially; convergence is reached when two consecutive turns fail to introduce a new decisive objection.

---

### Turn 1 — Seat A: Munger Inversion Skeptic — 2026-04-23

**Object under attack:** the "accept rate ≥50% by wake #20" prediction and the proposal envelope.

Start with inversion. *How do we guarantee this fails?* The fastest path to failure is the proposal-envelope itself. You have the daemon produce a 200-word envelope with "Scarcity signal: why this surfaced now." What fills that field when the answer is *"no new signal — this TODO was open yesterday and nothing changed"*? The envelope will be written anyway, because the daemon fired. The principal will see a parade of proposals whose scarcity field says, in effect, "still open." That is alert fatigue wearing a costume.

The seam names this failure mode for GP-105 — noise-not-signal — then proposes essentially the same architecture. The only structural difference is a three-button triage (proceed / defer-7d / never-this-class). Defer-7d is the deceptive one: it turns a noise item into a timer-based repeat. After three defers a human gives up and silences the whole class, and you are back to GP-105's graveyard.

**Demand:** the proposal envelope must not fire on *stock* conditions. If the daemon cannot name a delta from the last wake (new TODO, newly-failed test, new damage signal, newly-stalled artifact), it writes nothing. Null output is valid. Make this a hard invariant, not a ranker input.

Second inversion: *how does the ranker ossify?* You propose to retune source weights from accept/decline tallies. After 30 wakes, the most-accepted source class dominates. That is exactly the trail-lock-in Wilson warned about, relocated from research programs to proposal sources. Mitigation: reserve a budget (say 20%) of proposals for the *least-recently-accepted* source even when its rank says otherwise. Exploration floor.

---

### Turn 2 — Seat B: Systems-ML Engineer — 2026-04-23

**Object under attack:** daemon state, crash-idempotency, and the "daemon memory compresses" prediction.

Seat A's "null output is valid" point is correct and decisive. Build on it.

The seam does not specify **where the "delta" compares to**. Is the reference "last wake that produced a proposal" or "last wake, full stop"? These give different behavior: the former misses slow-growing drift (the delta has to clear a bar), the latter fires on trivial file-mtime bumps. Correct answer: the daemon persists a **fingerprint of each discovery source** (hash of the sorted candidate list) and fires only when at least one fingerprint has changed. Cheap: a SHA-256 per source per wake, stored in `org/mandates/daemon_fingerprints.json` (gitignored).

Second issue: **crash-idempotency at wake boundaries**. If the daemon writes an escalation but crashes before persisting the "this wake happened" marker, the next wake reconstructs the same escalation from the same state and re-fires it. That is a duplicate-notification bug not mentioned. Fix: the wake marker is written **first** (empty, just a timestamp), escalation is written second, and the ranker's output is hashed so re-runs within the same `(fingerprint, wake_id)` are no-ops.

Third issue: the "daemon memory compresses to <10 KB after 30 wakes" prediction is a vanity metric. What matters is that the memory can be **fully inspected by the principal in under 90 seconds**. Replace the size bound with a format bound: the daemon state must be a single JSON file with a fixed top-level schema (source_weights, never_this_class, last_30_decisions, last_wake_fingerprints). 10 KB is a soft guideline; schema stability is the hard requirement.

Fourth: you enumerate 8 discovery sources but only propose 2 for first build. Good. But the **interface** between source and ranker needs a contract *now*, not after source #3. Every source returns `list[Candidate]` with a fixed schema including `scarcity_delta: Optional[str]` (None means "no delta, filter me out"). Sources that can't produce a delta return empty; they don't get to special-plead.

---

### Turn 3 — Seat C: Philosophy-of-Science / Falsification — 2026-04-23

**Object under attack:** the four falsifiable predictions.

Seats A and B have strengthened the architecture. Now look at what the seam *promises to measure*.

**Prediction #1 (accept rate ≥50% by wake #20)** is not a falsifier. It is a target. If we hit 49%, do we abandon the system or retune? The seam says "retune rather than widen scope" — which means failing the prediction is *recovery advice*, not refutation. That's fine, but call it a *calibration target* not a falsifiable prediction. The prediction is working only if an agreed-in-advance level (say, ≤20% accept over 20 wakes with the tuned ranker) kills the system. Pre-register that kill level before turn-on, not after data comes in.

**Prediction #2 (accepted proposals produce a durable artifact ≥80% of the time)** is closer to a falsifier, but "durable artifact" is under-specified. Does a closed gate count? Does a one-line commit count? Anchor: a durable artifact is one of {committed code change, new/closed seam file, promoted F-row or INS-row in track record, new experiment-result JSON, closed gate with principal signature}. Things that do NOT count: Slack-message-equivalents, text replies in-session, daemon-internal state updates.

**Prediction #3 (zero instances of the daemon proposing something dangerous)** is a binary canary, good. But "dangerous" needs a concrete list, not intuition. Dangerous = any proposal that, if executed blindly, would touch `.ip_protected/`, `org/mandates/`, shared infrastructure, external parties, or cost >$10. That's auditable.

**Prediction #4 (daemon memory compresses)** — Seat B already rejected this as vanity. Drop and replace with: "the daemon's state can be replayed to reproduce the last 10 proposals byte-exactly from source data + stored weights." This is reproducibility as an invariant, not a size metric.

Add a **Prediction #5** the seam lacks: **defer-7d and never-this-class together should drop total proposal volume over the first 60 wakes, not raise it.** If volume grows after triage tools are added, the triage tools are broken (either not recorded or user-ignored). Measurable, falsifiable, catches a specific failure mode.

---

### Turn 4 — Seat D: Empirical AI Practitioner — 2026-04-23

**Object under attack:** ground truth from prior attempts (GP-105, GP-105b, industry analogs); the cadence question.

Prior seats have been constructive-adversarial, not destructive. Good. Two practitioner flags.

**Ground truth check.** The seam says "Going by memory of the shape of [GP-105/105b] — if the reconstruction is wrong in a decisive way, halt and read the actual seams." It then proceeds without doing that. That's a known anti-pattern per the "Verify LLM claims against source" memory. Before any code ships, someone (agent or principal) reads the actual GP-105 and GP-105b seams and either confirms or corrects the reconstruction. This is a spec-precondition, not a nice-to-have. Fail this and the whole seam is writing-on-sand.

**Cadence.** 2h default wake is wrong on two counts the seam hints at but doesn't resolve. (1) Most cron wakes will produce no proposal (Seat A's null-output rule), so the 2h cadence is burning tokens 12x/day for the *scan* even if the escalation is null. (2) Event-triggered wake on damage-signal writes is listed as an "alternative" — it's the primary. Make it primary. The 2h cadence becomes a fallback *minimum* wake to catch drift sources that don't fire damage signals (e.g., TODO-scan, stale-seam-scan). Suggested cadence: event-triggered on damage signal write; scheduled 4-hour sweep for drift sources; suppress the scheduled sweep if an event-triggered wake fired within the last 2 hours.

**Industry analog warning.** Autonomous agent loops in 2024-2025 (AutoGPT, BabyAGI, AgentGPT) overwhelmingly failed on the "no shutoff condition" axis — the agent kept proposing work until the user killed it. GP-131's human-in-loop triage + never-this-class bucket is the counter, but it only works if the principal actively triages. If triage backlog grows (inbox builds up, no triage for 3 days), **the daemon must automatically pause** until triage catches up. Add: daemon pauses scheduled sweeps if the inbox has >10 unresolved proposals. Event-triggered critical-damage wakes still fire, but drift-source sweeps go silent.

---

### Turn 5 — Munger Inversion Skeptic, replying to Seats B/C/D — 2026-04-23

Two new objections, one retraction.

**Retraction.** The defer-7d concern (Turn 1) is weakened by Seat C's Prediction #5: if defer-7d causes volume to rise over 60 wakes, the metric catches it. That's fine. I overstated.

**New objection 1 — cascading pauses.** Seat D's "daemon pauses if inbox > 10 unresolved" interacts badly with "event-triggered critical-damage wakes still fire." What if a critical wake fires during a paused window, the principal escalates it to a proposal action, which then fails, producing a new damage signal? That's a potential loop. Cap: event-triggered wakes that result in a new escalation written while paused count against the inbox limit. If an event-triggered wake would push the inbox over cap during a pause, it is written but marked `principal_required_before_further_action=true`, suppressing further daemon wakes of any kind until the principal touches the inbox.

**New objection 2 — the "never-this-class" bucket has a half-life problem.** Seat C's Prediction #5 says triage tools should reduce volume. But "never-this-class" as permanent memory is too strong: a class dismissed 30 days ago may be decisive today (domain changed, new program opened). Decay rule: never-this-class marker auto-expires after 30 days unless the principal re-asserts it on any proposal. Proposal: display the re-assert prompt only for the first proposal of a previously-banned class after expiry; never bury it deeper.

No other new objections. **Convergence proposal:** if Seat B or Seat C rebut these two points meaningfully, continue; else we converge.

---

### Turn 6 — Systems-ML Engineer, final — 2026-04-23

Seat A's two refinements stand. No meaningful rebuttal from me.

One engineering clarification on the state schema. The daemon state file should carry `schema_version` as its first field, and the loader (analogous to GP-128 role loader) should refuse to load unknown major versions. We already have `tests/test_org_schema_compat.py` pattern for this — reuse it for the daemon state file so a future v2 state doesn't silently corrupt v1.

**I have no further decisive objections.**

---

### Turn 7 — Philosophy-of-Science, final — 2026-04-23

Seat A's decay rule for never-this-class is the right call — it turns a locked-in verdict into a revisable one, which is exactly what Popperian hygiene requires for user-provided "never" claims. Without decay, the bucket becomes a shrine to yesterday's priorities.

Prediction #5 (volume-over-60-wakes) holds. Adding one test refinement: the denominator should be *proposals written to inbox*, not *wakes that fired* — a wake that produces null output doesn't count. This is consistent with Seat A's Turn 1 hard invariant.

**I have no further decisive objections.**

---

### Turn 8 — Empirical AI Practitioner, final — 2026-04-23

Seat A's cascading-pause objection is real and the fix (suppress further wakes when an event-triggered wake puts the inbox over cap) is clean. The `principal_required_before_further_action` flag is decisive and should be a first-class field in the inbox escalation schema, not a free-text convention.

One final empirical note. The spec (when written) should include a **dry-run mode** that logs what the daemon *would have* proposed for at least 7 days of real data before any ntfy push fires. That window is how we catch the Seat A "still open" failure mode before it reaches the principal's phone. Industry track record: every autonomous-agent system that shipped without a dry-run window incurred at least one embarrassing incident in the first month.

**I have no further decisive objections.**

---

### Convergence Marker — 2026-04-23

<!-- SEAM_DEBATE_CONVERGED 2026-04-23 -->

Converged after 8 turns (4 seats × 2 rounds). The spec must address and encode the following **accepted modifications** from debate:

1. **Hard invariant:** daemon writes a proposal only if at least one discovery source's fingerprint has changed since the last wake. Null output is valid. (Seats A, B, C, D)
2. **Daemon state:** single JSON file with `schema_version` field, fixed top-level schema (source_weights, never_this_class, last_30_decisions, last_wake_fingerprints), replayability invariant over 10-proposal window. Loader reuses the schema-compat test pattern. (Seat B, Seat C)
3. **Exploration floor:** reserve 20% of proposals for the least-recently-accepted source even when ranker says otherwise. (Seat A)
4. **Crash-idempotency:** wake marker written first, escalation second, `(fingerprint, wake_id)` hash makes re-runs no-ops. (Seat B)
5. **Falsifiers pre-registered:** P1 kill-level ≤20% accept over 20 wakes; P2 durable-artifact defined as committed code / seam file / F- or INS-row / experiment JSON / signed gate; P3 "dangerous" = touches `.ip_protected/`, `org/mandates/`, shared infra, external parties, or >$10; P4 replaced by replayability invariant; P5 proposal-volume non-monotone over first 60 wakes after triage tools exist. (Seat C, Seat A)
6. **Source interface contract:** every discovery source returns `list[Candidate]` with `scarcity_delta: Optional[str]` field; sources returning empty list are filtered out of ranking. (Seat B)
7. **Cadence:** event-triggered on damage-signal write is primary; 4h scheduled sweep is secondary drift-catch; scheduled sweep suppressed if event-triggered fired in last 2h. (Seat D)
8. **Pause-on-backlog:** daemon pauses scheduled sweeps if unresolved inbox > 10; event-triggered critical wakes still fire but count against cap; `principal_required_before_further_action` becomes a first-class inbox field. (Seat D, Seat A)
9. **Never-this-class decay:** 30-day auto-expiry with one-time re-assert prompt on next proposal of that class. (Seat A)
10. **Dry-run mode:** spec must provide ≥7-day dry-run window that logs but does not notify. (Seat D)
11. **Spec precondition:** before any implementation, actual GP-105 and GP-105b seams are read and the seam's reconstruction is confirmed or corrected in a reconstruction audit sub-section. (Seat D)
