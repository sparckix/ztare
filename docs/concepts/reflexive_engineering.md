---
description: "How ZTARE turns repeated failures in its own loop into durable checks, routes, and records."
---
# Reflexive Engineering Primitives

> **Up:** [Documentation map](../README.md)

**Status:** public companion to [architecture.md](architecture.md).

**Companion docs:** [reflexive_audit_workflow.md](../guides/reflexive_audit_workflow.md)
for the discovery workflow, and
[agentic_engineering_patterns.md](agentic_engineering_patterns.md) for portable
LLM-pipeline hardening patterns.

**Core rule:** when the same failure repeats, make the next run inherit a
check, route, record, queue entry, or budget constraint. Do not rely on a human
or an agent remembering what went wrong.

Agentic engineering patterns are general LLM-pipeline practices: replay tests,
contract checks, canonicalization, and provenance. Reflexive primitives are the
inward-facing layer: ZTARE applies those practices to its own research loop,
routing, memory, and attention allocation.

---

## The Reader Decision

Use this page when you see the same failure twice and need to decide whether it
deserves machinery. The decision is not "is this failure interesting?" It is:

```text
Will a future run behave differently because this failure was recorded?
```

If the answer is no, the work is a note, dashboard row, or planning item. If the
answer is yes, the failure may be ready for a reflexive primitive: a check,
route, record, queue entry, budget constraint, or forecast contract that a
future run must consume.

## Small Case

A model repeatedly skips source-readiness checks before trying to launch a run.
A weak response is to write a reminder. A reflexive response is to add an
artifact that future launches read:

1. the trace records the missing source surface;
2. the launcher blocks before model spend;
3. the next command points to the recovery step;
4. a later audit can see whether the blocker was consumed.

That is a reflexive primitive only if the blocker changes later behavior. The
primitive is not the prose explanation. It is the consumed artifact plus the
changed route.

## Evidence Boundary

This page does not prove that the system is improving in general. It describes
which repeated failures are allowed to become durable machinery. Evidence for a
particular primitive must point to the consumed artifact, the command or gate
that reads it, and the later behavior change.

## Start Here

Read this as a maintenance manual for the research loop. It helps you decide
whether a recurring failure has become a durable repair, or whether it is still
only a note.

A reflexive primitive is a repair ZTARE applies to its own loop after a
recurring failure.

A candidate primitive belongs here only when all four conditions hold:

1. A concrete infrastructure failure occurred.
2. The failure can recur during normal agent or research-director work.
3. The repair changes a future run through a check, route, record, queue, gate,
   or budget decision.
4. The repair can be tested or audited from an artifact, not only remembered.

If the mechanism is useful for any LLM pipeline, document it first in
[agentic_engineering_patterns.md](agentic_engineering_patterns.md). It belongs
here when ZTARE uses the mechanism on its own routing, memory, trace, forecast,
or allocation policy.

## How To Read This Doc

Use this page after something repeats. The order is:

1. Identify the repeated failure in [When To Use Which Primitive](#when-to-use-which-primitive).
2. Check [Status And Owners](#status-and-owners) before treating the primitive
   as implemented.
3. Check [Primitive Audit Matrix](#primitive-audit-matrix) for the selecting
   signal, required artifact, owner, and known confuser.
4. Find the owned artifact: architecture map, trace, route preflight, primitive
   miss, action receipt, queue row, or forecast contract.
5. Ask whether the next run changes because of that artifact.

If the answer to step 4 is no, the work is a note or a dashboard. It is not a
reflexive primitive yet.

## Promotion Criteria

A reflexive primitive can be promoted only when it passes all five checks.

| Check | Question |
|---|---|
| Recurrence | Did the same failure happen more than once, or can it recur naturally? |
| Loop target | Is the failure in routing, memory, trace, forecast, attention, or closure rather than only in the external project surface? |
| Consumed artifact | Is there a file, row, receipt, gate, queue entry, or command that future runs consume? |
| Behavior change | Would a future run route, block, score, or prepare differently because of it? |
| Audit path | Can a reviewer inspect the artifact without reading a chat transcript? |

This bar is deliberately stricter than "useful idea." Many useful ideas belong
in the roadmap, a project note, or the agentic pattern catalog instead.

## When To Use Which Primitive

| Current failure | Use | Add this first |
|---|---|---|
| Agent edits a large pipeline from partial context and breaks ordering | [Token-Optimized Self-Modeling](#primitive-1-token-optimized-self-modeling) | validated architecture map |
| Agent proposes without knowing which gate will reject it | [Preflight Environment Model](#primitive-2-preflight-environment-model-inception) | machine-readable gate or phase model |
| Static reviewer lenses miss a new failure family | [Hybrid Persona Router](#primitive-3-hybrid-persona-router-cache-route-generate-promote) | routed reviewer lens plus promotion rule |
| A grammar ceiling exposes a structured residual | [Residual-to-Primitive Discovery](#primitive-4-residual-to-primitive-discovery) | residual-to-primitive proposal and leak check |
| Goals repeatedly fail because the process is ambiguous | [Process Lifecycle Repair](#primitive-5-process-lifecycle-repair) | transition-log audit and process-vs-project-surface discriminator |
| Agent skips known task steps | [Procedural Self-Audit](#primitive-6-procedural-self-audit) | task type, required checklist, post-check receipt |
| Maintainer correction stays trapped in chat | [Maintainer Correction Replay](#primitive-7-maintainer-correction-replay) | next-discriminator queue or missing-record finding |
| Several valid next moves compete for attention | [Research Taste Router](#primitive-8-research-taste-router) | scored opportunity card with explicit preference axes |
| Proposed actions need priced disagreement before execution | [Reflexive Forecast Market](#primitive-9-reflexive-forecast-market) | sealed contract, independent forecasts, resolver, score closure |

## Status And Owners

These primitives are not all equally mature. The table names the current owner
and the gap a maintainer should respect.

| Primitive | Current status | Main owner / check | Current gap |
|---|---|---|---|
| [Token-Optimized Self-Modeling](#primitive-1-token-optimized-self-modeling) | live / shared | [architecture index](../../src/ztare/architecture_index/graph.yaml), [`primitive_tick_surface.py`](../../src/ztare/research_director/primitive_tick_surface.py), arch-map validators | same mechanism as [Agentic Pattern 9](agentic_engineering_patterns.md#pattern-9-token-optimized-self-modeling); keep one owner story |
| [Preflight Environment Model](#primitive-2-preflight-environment-model-inception) | partial | [`rd_tick_brief.py`](../../scripts/public/control/rd_tick_brief.py), project route preflights, `ztare autoresearch trace` | live only where the tool emits blockers and next commands |
| [Hybrid Persona Router](#primitive-3-hybrid-persona-router-cache-route-generate-promote) | partial | persona routing and reviewer surfaces | needs a clearer public owner/test before strong claims |
| [Residual-to-Primitive Discovery](#primitive-4-residual-to-primitive-discovery) | partial | [`primitive_amnesia.py`](../../src/ztare/research_director/primitive_amnesia.py), miss queues, [`pattern_action_contract.py`](../../src/ztare/research_director/pattern_action_contract.py) | residual must become a candidate primitive or typed action receipt, not a new label |
| [Process Lifecycle Repair](#primitive-5-process-lifecycle-repair) | partial | membrane state, action intelligence, orchestration shadow logs | separate process-lifecycle repair from project progress |
| [Procedural Self-Audit](#primitive-6-procedural-self-audit) | live / advanced | project preflights, [`post_tick_check.py`](../../scripts/public/control/post_tick_check.py), RD close clients | public docs should present the reusable checklist/receipt shape, not tick ceremony |
| [Maintainer Correction Replay](#primitive-7-maintainer-correction-replay) | partial | [correction replay audit](../../src/ztare/orchestrator/operator_replay_audit.py), [`discriminator_queue.py`](../../src/ztare/orchestrator/discriminator_queue.py) | captures recurring discriminator shapes, not the final taste call |
| [Research Taste Router](#primitive-8-research-taste-router) | candidate / partial | preference profile and [`research_taste.py`](../../src/ztare/orchestrator/research_taste.py) opportunity cards | keep public claims modest until decision-use rows exist |
| [Reflexive Forecast Market](#primitive-9-reflexive-forecast-market) | live | [`forecast/pool.py`](../../scripts/public/control/forecast/pool.py), [`prediction_contract.py`](../../src/ztare/forecasting/prediction_contract.py), forecast capability audit | separate scoring, decision influence, and authority |

## Primitive Audit Matrix

This table is the promotion surface for reflexive primitives. A row is not a
primitive just because it sounds useful; it must identify the repeated failure,
the signal that selects it, the artifact a future run consumes, and the nearby
false pattern it must not collapse into.

| Primitive | Failure class | Selecting signal | Required artifact or check | Known confuser | Status |
|---|---|---|---|---|---|
| 1. Self-modeling | Repo cannot tell agents what invariants matter | Repeated context-window or cross-file mistakes | Architecture/self-model row plus drift validator | Human-readable architecture essay | live / duplicate |
| 2. Environment model | Agent acts before it knows launch state | Edit/run depends on hidden state or active gate mode | Preflight environment model with task, gates, surfaces, blockers | Generic instruction reminder | partial |
| 3. Reviewer router | Wrong reviewer or persona handles the task | Task has a distinct lens or reviewer-domain need | Persona route row with domain, rationale, and fallback | Committee prompt without route evidence | partial |
| 4. Residual-to-primitive | Repeated residual remains a note | Miss queue, catch category, or graph/action edge repeats | Residual signature, nearest primitive/confuser, promotion or refusal row | Naming a primitive by assertion | partial |
| 5. Lifecycle repair | Process repair is confused with project progress | Lifecycle gate, action row, or shadow policy changes operation | Transition log, action-impact row, stop rule, later outcome | Dashboard metric treated as authority | partial |
| 6. Procedural self-audit | Run closes without required checklist/receipt | Task type has mandatory pre/post/close checks | Task checklist, receipt, blocker or pass row | Prose "done" note | live, advanced |
| 7. Maintainer correction replay | Insight exists only in chat/maintainer memory | Next discriminator cannot be reconstructed from artifacts | Replay audit row and next-discriminator queue item | Meeting note or scratch TODO | partial |
| 8. Research taste router | Attention allocation is opaque or overfit to preference | Two valid moves compete for scarce effort | Opportunity card with axis scores, penalties, route label | Truth score or priority label | candidate / partial |
| 9. Forecast market | System acts without priced risk or learns nothing from a miss | Branch/action choice has uncertainty and cost | Forecast contract, independent forecasts, resolution, score, decision-use row | Local score-only prediction row | live |

---

## Primitive Runtime Contract

| Primitive | Target | Artifact a future run consumes | What changes |
|-----------|--------|-------------------------------|--------------|
| Token-Optimized Self-Modeling | Agent context use | architecture map, primitive surface, graph edge | The agent reads the relevant regions and invariants before editing. |
| Preflight Environment Model | Agent environment model | gate/phase model, trace blockers, next command | The agent sees rejection conditions before proposing a change. |
| Hybrid Persona Router | Review expertise | routed reviewer lens and promotion rule | A review request uses an existing lens or creates a temporary one with an expiry path. |
| Residual-to-Primitive Discovery | Primitive catalogue and action contracts | residual signature, nearest primitive/confuser, promotion/refusal row | A repeated residual becomes a candidate primitive, typed receipt, or explicit refusal. |
| Process Lifecycle Repair | Goal lifecycle | transition log, action-impact row, stop rule, later outcome | Process debt is separated from project difficulty before the target changes. |
| Procedural Self-Audit | Agent task discipline | task checklist, receipt, blocker/pass row | Completion requires task-specific proof that required steps happened. |
| Maintainer Correction Replay | Human-agent discovery loop | replay audit row, next-discriminator queue item | Repeated maintainer corrections become next-test queues or missing-record findings. |
| Research Taste Router | Attention allocation | opportunity card with axis scores and penalties | Competing next moves get scored before scarce effort is spent. |
| Reflexive Forecast Market | Research actions | sealed forecast contract, aggregate, decision-use row, score | Proposed actions get priced disagreement and scored outcomes. |

---

## Primitive 1: Token-Optimized Self-Modeling

**Failure signal:** an agent edits from a local slice of the repository and
misses a cross-file invariant, ordering rule, or already-built primitive.

**Owned artifact:** a compact architecture/self-model surface: region index,
dependency edges, invariant rows, and edit-intent lookups.

**Next-run effect:** before editing, the agent sees which regions and
constraints matter. The system can surface existing primitives instead of
letting the agent rebuild them from memory.

**Boundary:** this is not a prose architecture overview. It must be structured
enough for retrieval, validation, and drift checks.

**Current owner and status:** Live, but shared with
[Agentic Pattern 9](agentic_engineering_patterns.md#pattern-9-token-optimized-self-modeling).
The concrete owners are the [architecture index](../../src/ztare/architecture_index/graph.yaml)
and
[`primitive_tick_surface.py`](../../src/ztare/research_director/primitive_tick_surface.py).
In this doc, keep the reflexive claim narrow: ZTARE uses a compact model of its
own codebase and primitive graph to reduce partial-context edits.

---

## Primitive 2: Preflight Environment Model (Inception)

**Failure signal:** an agent proposes a change before it knows the active
gates, launch state, expected inputs, or rejection conditions.

**Owned artifact:** a small machine-readable environment model: task, phase,
required surfaces, blockers, next command, and the gate or validator that will
read each output.

**Next-run effect:** the agent sees the rejection conditions before it spends a
model call or edits the wrong surface. A blocked path emits the recovery command
instead of becoming a failed run.

**Boundary:** this is only live where a tool emits concrete blockers and next
commands. A general instruction like "check the environment first" is not an
environment model.

**Current owner and status:** Partial. ZTARE has several environment models:
[`rd_tick_brief.py`](../../scripts/public/control/rd_tick_brief.py) for
research-director ticks, public project route preflights for autoresearch
entry, and `ztare autoresearch trace` for the project trace chain. The
primitive is live where those tools emit explicit blockers and next commands.
It should not be described as one universal environment model.

---

## Primitive 3: Hybrid Persona Router (Cache-Route-Generate-Promote)

**Failure signal:** a review request needs a specific adversarial lens, but the
system either sends every task to the same reviewer style or invents a new lens
without checking whether one already exists.

**Owned artifact:** a routed reviewer-lens row: selected lens, source signal,
fallback path, promotion rule, and expiry or demotion condition for temporary
lenses.

**Next-run effect:** known failure families reuse stable lenses; unknown ones
can be explored without silently becoming permanent policy.

**Promotion rule:** A temporary lens is exploration. A promoted lens is a
versioned artifact with tests, examples, or a repeatable routing rule.

**Boundary:** a routed lens is not a verdict. It changes who or what reviews
the work; the claim still needs evidence, gates, and normal authority.

---

## Primitive 4: Residual-to-Primitive Discovery

**Failure signal:** the same residual, gap, catch category, or graph edge
survives repeated attempts even after existing tools are surfaced.

**Owned artifact:** a residual-to-primitive proposal: failed surface, nearest
existing primitive, nearest confuser, rejected alternative, owed artifact, and a
promote/defer/refuse decision.

**Next-run effect:** the system either creates a narrow primitive/card/receipt
schema/test, or records why the residual should not become reusable machinery.
Future agents can query that decision instead of renaming the same gap.

**Observability constraint:** A missing primitive can be discovered only if the
next run can see the residual. A note such as "the route still feels wrong" is
not enough. The residual must point to an artifact, gate miss, repeated
rediscovery, or failed receipt field.

**Known limitation:** This does not guarantee that the missing primitive exists.
Many residuals mean the current branch is dead, under-specified, or outside the
current system boundary. The primitive proposal has to survive the
nearest-confuser check and earn promotion through tests or repeated use.

**Instantiation checklist:**
- A gate, trace, graph, workbench, or project memory records the residual.
- [`primitive_amnesia.py`](../../src/ztare/research_director/primitive_amnesia.py)
  finds the nearest existing capability or returns a miss.
- [`pattern_action_contract.py`](../../src/ztare/research_director/pattern_action_contract.py)
  lowers the residual into required fields when an action is owed.
- The proposal names the nearest confuser and why the existing primitive is not
  enough.
- Promotion creates a narrow primitive, card, receipt schema, or test; refusal
  records why the residual is not a reusable primitive.

**Current owner and status:** Partial, with two live sub-surfaces. Capability
amnesia uses
[`primitive_amnesia.py`](../../src/ztare/research_director/primitive_amnesia.py)
and its miss queue to turn repeated rediscovery into primitive/catalog debt.
Action contracts use
[`pattern_action_contract.py`](../../src/ztare/research_director/pattern_action_contract.py)
to lower a residual edge into a required artifact and nearest-confuser check.
The older symbolic-regression example should be kept as one instance, not the
definition of the primitive.

---

## Primitive 5: Process Lifecycle Repair

**Status:** conceptual, not yet implemented

**Failure signal:** goals repeatedly fail at the same process stage, and the
team reacts by changing the research target instead of checking the lifecycle.

**Owned artifact:** a transition-log audit with the failed phase, required
field, stale gate, ambiguous stage, or missing lifecycle invariant. If a repair
is proposed, it needs a stop rule and a later outcome.

**Next-run effect:** process debt is separated from project difficulty before
the system changes target, retires work, or opens a new route.

**Discriminator:** would a clearer process contract have changed the outcome?
If yes, repair the lifecycle. If no, the failure belongs to the project surface
or research branch.

**Current boundary:** This remains partial. Treat it as a diagnostic shape for
process repair, not as proof that the lifecycle is generally solved.

---

## What These Have In Common

These entries are not general best practices. They are repairs to ZTARE's own
research machinery.

1. They apply an existing ZTARE principle to ZTARE's own machinery: routing,
   memory, state, attention, or closure.
2. They came from a specific failure, not from a naming exercise.
3. They are testable against the failure that motivated them.
4. They change a future run through an artifact the next agent or command can
   consume.

Examples: the architecture map prevents partial-context edits; the environment
model shows gates before an agent proposes; residual-to-primitive discovery
either creates a primitive/card/receipt proposal with a test, or records a
refusal.

### Recognizing when a new primitive is needed

A new reflexive primitive is indicated when:

- known recovery mechanisms fail in the same way across repeated attempts;
- the failure traces to an infrastructure constraint rather than only to the
  project surface;
- applying an existing ZTARE principle inward would change a later run.

The signature is zero-variance stagnation rather than ordinary search: the
loop keeps hitting one structural constraint instead of exploring different
failure modes.

For the periodic discovery mechanism that detects this signature automatically, see `docs/guides/reflexive_audit_workflow.md`.

### Current candidate boundary

Autoresearch workbench routing is intentionally treated as an implementation of
the agentic Pattern 16 contract compiler, not as a new reflexive primitive yet.
It is inward-facing infrastructure: the route code decides when the in-loop
workbench should be used instead of manual RD/agent work, and records the route
as an action-impact row. That is valuable, but the REP bar is higher. Promotion
would require evidence across more than one context that the route receipt
changes behavior: fewer unexplained out-of-loop bypasses, more prepared
workbench surfaces, or better reuse of failed-branch constraints. Until then it
belongs in OP-AWR/action-intelligence machinery rather than in the primitive
catalogue.

---

## Primitive 6: Procedural Self-Audit

**Failure signal:** an agent completes a task while skipping required steps:
closure rows, project validation, paper sync, route preflight, or repo-specific
checks.

**Owned artifact:** a typed task checklist plus pre/post receipt. The task type
selects required steps; the validator reports blockers before the agent can
claim completion.

**Next-run effect:** completion means the required checks have run or the
blocker is explicit. The agent no longer relies on memory for task discipline.

**Instantiation:**
- Task discipline map: local task-discipline rules compiled from `AGENTS.md`
- Validator: `scripts/public/validators/validate_agent_task_discipline.py {pre,post,show,audit}`
- Session log: `workspace/agent_session_log.jsonl` (gitignored, per-session)
- Six task types: experiment_run, substrate_build, paper_edit, seam_update, recording, infrastructure
- Each type has typed pre-checks and post-checks derived from AGENTS.md

**The test:** Run `python scripts/public/validators/validate_agent_task_discipline.py post experiment_run` after any experiment. If post-checks are incomplete, the agent fixes them before responding. The validator is the deterministic gate; AGENTS.md is the specification.

**Known limitation:** The session log is manually maintained by the agent. A
dishonest agent can skip logging. The validator catches honest mistakes; it
does not catch adversarial evasion without independent audit.

**Current owner and status:** Live at several levels, with different authority.
`validate_agent_task_discipline.py` is the generic agent checklist surface.
`post_tick_check.py`, `posttick_runner.py`, and the RD close clients carry the
higher-authority tick close discipline. Public project routing uses source
preflight, source-index, evidence-output binding, and launch preflight before
run readiness. The doc should present the reusable shape first: task type,
required checklist, receipt, and blocker.

---

## Primitive 7: Maintainer Correction Replay

**Failure signal:** the maintainer and agent discover a better discriminator, but
the insight remains in chat or scratch notes.

**Owned artifact:** a replay audit row and, when the next test is
reconstructable, a `next_discriminator_queue.jsonl` item.

**Next-run effect:** a future agent can recover the next decisive test from
files alone, without reading a chat transcript.

**Instantiation:**
- Replay reader:
  [correction replay audit](../../src/ztare/orchestrator/operator_replay_audit.py)
- Queue contract:
  [discriminator queue](../../src/ztare/orchestrator/discriminator_queue.py)
- Primary artifact: `projects/<slug>/workspace/next_discriminator_queue.jsonl`
- Typical recovered moves: empty-box background gate, large-box boundary gate, tensor-rotation gate, background-debt ladder, dynamic-admissibility gate

**The discriminator:** Could a cold agent open the repo tomorrow and
reconstruct the next decisive test without reading chat? If not, the record has
not mechanized the maintainer's move. Improve artifact closure or add a replay
template.

**Known limitation:** This is template-based. It captures recurring
discriminator shapes, not the final judgment of which scientific question
matters most.

---

## Primitive 8: Research Taste Router

**Failure signal:** several next moves are valid, but the reason for choosing
one over another is opaque, personality-driven, or reconstructed after the
fact.

**Owned artifact:** an opportunity card with explicit axes: scientific value,
architecture fit, governance value, risk, public-claim exposure, and current
reviewer preference.

**Next-run effect:** scarce attention is allocated against stated preferences.
The router can say `pursue_now`, `queue`, or `defer`, and the human can override
with a visible reason.

**Instantiation:**
- Profile: `org/preferences/principal.yaml`
- Scorer: `src/ztare/orchestrator/research_taste.py`
- Output: ranked opportunity cards with axis scores, penalties, and route labels (`pursue_now`, `queue`, `defer`)

**The discriminator:** If two candidate next moves are both scientifically
valid, the router should explain why one better matches the stated preferences.
If it cannot, the choice remains manual and should be labeled that way.

**Known limitation:** Taste routing allocates attention. It does not promote a
claim or grant auto-dispatch authority. A high taste score only says the
candidate is worth scarce attention.

---

## Primitive 9: Reflexive Forecast Market

**Failure signal:** ZTARE is about to spend effort on a consequential branch,
but the risk, expected value, and failure modes are not priced before action.

**Owned artifact:** a sealed forecast contract, independent forecasts, an
aggregate, a decision-use row when behavior changes, and a scored resolution.

**Next-run effect:** forecasts become calibrated decision records rather than
advisory prose. A forecast can route away from a weak branch, tighten an
artifact constraint, name a failure mode the executor must guard, or escalate to
a different-family judge.

Pattern 12 is the portable agentic implementation. This primitive is the inward
use of that mechanism on ZTARE's own research allocation and tick-level action
choices.

**Required records:**

- sealed forecast contract;
- independent forecasts with authorship and timing;
- aggregate before the outcome is known;
- decision-use row if the forecast changed behavior;
- resolution and score;
- follow-up when the miss exposes a repeated failure mode.

**Current surfaces:**
- Agentic implementation pattern:
  [Pattern 12, Sealed Forecast Pool for Execution Control](agentic_engineering_patterns.md#pattern-12-sealed-forecast-pool-for-execution-control)
- Forecast-pool design record:
  [decision-market seam](../../research_areas/seams/protocol/GP-230_forecast_pool_decision_market_seam.md)
  and
  [decision-market spec](../../research_areas/specs/active/protocol/GP-230_forecast_pool_decision_market_spec.md)
- Calibration evidence record:
  [forecaster-skill calibration seam](../../research_areas/seams/apparatus/instrumentation/GP-245_forecaster_skill_calibration_seam.md),
  with the per-finding evidence ledger in
  `projects/llm_forecasting_calibration_program/forecaster_skill_calibration_v1/workspace/research_log.md`
- Generated reflexive read model:
  `analytics/public/forecast_pool/market_state/reflexive_insights.json`
- Generated hygiene queue:
  `analytics/public/forecast_pool/market_state/maintenance_plan.json`
- Audit/validator: `scripts/public/analytics_shared/audit_forecast_pool_externalities.py`
  and `scripts/public/control/forecast/pool.py externalities`

**Authority boundary:** A sealed forecast-pool row can influence research
allocation only through the forecast-pool lifecycle and decision-use record.
Local in-loop prediction rows, scratch forecasts, and prediction-ledger mirrors
are score/read-model surfaces until they prove authority, timing, and resolution
through
[`prediction_contract.py`](../../src/ztare/forecasting/prediction_contract.py).

**The discriminator:** Did the forecast change behavior before the result was
known? Valid changes include routing away from a weak branch, tightening an
artifact constraint, naming a failure mode the executor explicitly guards, or
escalating to a different-family judge. If forecasts only produce after-the-fact
Brier scores, they are calibration data, not reflexive control.

**Operational falsifier:** The primitive fails in practice if recurring audits
show that forecasts are not scored, resolved contracts leave stale transport
messages, forecast wakes do not produce aggregates or explicit no-update
statuses, macro/meso decisions omit causal forecast-use fields, ZTARE's own
forecasters can see each other's prior outputs (silently breaking the
independence Schoenegger-style aggregation depends on), or scored history stops
improving branch/effort routing across contexts.

**Known limitation:** This is a sealed, properly-scored decision market with
agentic transport. It is deliberately not a live LMSR/AMM or continuous price
tape; the market is used to precondition and calibrate research decisions, not
to create a tradable public asset.

---

## Closure: Internal Vs External Pressure

One reflexive-mining run produced a useful correction: **coordination
closure** (when to stop searching, what to fund next, when to abandon a
branch) needs external resource pressure. A later pass over-extended that into
"closure of any kind requires external pressure" and the checker rejected it.
The distinction matters.

**Internal closure (works without exogenous pressure):**

Technical-validation closures are checks whose stopping condition is internal to
the artifact. They do not need a budget, deadline, or principal to terminate.

- `validate_substrate_meta`, schema validation
- `validate_rubric.py`, rubric pre-flight
- Deterministic cage gates, including the legacy numbered gate family, where
  the public name should describe the failure class rather than expose only
  labels such as `R10` or `R11`
- Lean cages, formal-proof termination
- R1 mutation_suite_guard, Python-importability guarantee
- Type-checks, lint, signature checks
- Cryptographic primitives (when present)

**Exogenous closure (needs principal / budget / deadline / mortality):**

Coordination closures, choices among epistemically-valid
alternatives. They cannot terminate from internal coherence alone
because no internal property distinguishes the "correct" answer.

- Choosing which Objective to fund next
- Deciding whether a paper is ready to publish
- Allocating principal attention across competing seams
- Deciding when a research direction is exhausted
- Promotion of a thesis from "passes gates" to "is a paper claim"

**Why this distinction matters operationally:**

Conflating the two creates two opposite mistakes. If "all closure needs
exogenous pressure," even schema validation becomes a management decision. If
"all closure can be internal," the system can deliberate forever over choices
that require taste, budget, or priority. The practical rule is: technical
validation closes internally; coordination closure requires an external
constraint. Schema validators do not ask the principal for permission; OKR
closure does.

---

## Home And Boundaries

- **Epistemic verification stays in the treatise.** This page records
  engineering primitives. It can show that the decomposition is useful, but it
  should not make broad claims about the world.
- **Run-time checklists stay in operational guides.** This page is about
  design-time repairs to the system: checks, routes, records, queues, gates,
  and budget decisions added because a failure recurred.
- **This page owns the self-improvement layer.** It sits beside
  [architecture.md](architecture.md), which explains the system, and the
  validator workflow, which explains how model proposals are separated from
  checks.
