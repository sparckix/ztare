# GP-225 LeanMill vNext Station Factory Seam

> **Seam metadata** · `seam_id:` GP-225 · `track:` engine · `status:` Active · `last_updated:` 2026-05-25

## Status

Active, opened 2026-05-21 16:48:16 EST

## ID

GP-225

## Eigenquestion

What is the smallest operational boundary that turns LeanMill from an interactive proof-search script into a replayable station factory whose every station emits a typed learning-unit exit?

## Problem Statement

LeanMill now has real governed canary closures, matched negative controls, a growing repair-family registry, source qualification inventory, and a fair static-vs-adaptive experiment contract. The failure mode has shifted from "can Lean run?" to "can the mill industrialize residual-to-family-to-governed-outcome without turning into hand-coded row exceptions?"

The current risk is conflating architecture, implementation contract, scientific ledger, and station debate in one artifact. A seam should record the decision boundary and unresolved questions. The operational blueprint belongs in the companion spec.

## Scope

This seam covers the architectural decision to promote LeanMill into a station-based factory with typed learning-unit exits, durable work items, event ledger, deterministic gates, bounded LLM proposal workers, subscription-agent repair workers, and governance-only ratification.

This seam does not define the operational file contracts, worker interfaces, promotion thresholds, or launch checklist. Those belong in the companion spec:

`research_areas/specs/active/engine/lean/GP-225_leanmill_vnext_station_factory_spec.md`

## Recommendation

Adopt the station-factory architecture and keep the deterministic control plane as the authority: queue work items, emit append-only events, validate repair-family specs before execution, run bounded Proof Execution, ratify only through Governance Gate, and promote repair families only through registry evidence with controls. Move scientific knowledge out of Python conditionals and into versioned repair-family specs. Treat API LLMs as bounded proposal generators and subscription CLI agents as scoped stateful repair workers, never as ratifiers.

## Option Analysis

### Option A — Keep LeanMill As Research Scripts

Fastest to keep extending, but row-specific conditionals and manual memory become the system of record. Rejected because it cannot scale the unit of learning or support fair Evaluation Harness comparisons.

### Option B — Jump Directly To Distributed Workflow Infrastructure

Temporal, Redis Streams, or Celery would eventually fit durable multi-step workflows. Rejected as the immediate move because schemas are still changing and the mill needs replayable behavior before broker operations.

### Option C — File-Backed Factory With Clear Upgrade Path

Use SQLite WorkItems, JSONL events, versioned repair-family specs, deterministic gates, bounded workers, and dashboards now; migrate to a generic kernel queue or distributed broker once the contracts stabilize. Recommended.

## Open Questions

- ~~When should the local LeanMill WorkItem queue be replaced by a shared Cognitive Firm `OperatingUnit` / WorkItem primitive?~~ **Resolved 2026-05-21 (Turn 3):** the shared kernel primitive now exists. The replacement trigger is contract stability, not a date — migrate a LeanMill station once its work kinds and exits stop changing.
- What evidence should mechanically certify heldout independence for `validated_family` promotion?
- What source/family allocation policy should replace the current conservative scheduler once conversion-rate data is large enough?
- What is the minimum inventory threshold for launching the fair static-vs-adaptive Evaluation Harness without measuring weak inventory instead of adaptive orchestration?

## Debate Log

### Turn 1 — Principal (2026-05-21 16:48:16 EST) — Correct seam/spec separation

The principal corrected the artifact boundary: LeanMill has both a seam format and a spec format, and a seam is not a spec. The operational LeanMill vNext contract should be distributed accordingly.

### Turn 2 — Codex (2026-05-21 16:48:16 EST) — Split accepted

The previous `GP-225_leanmill_vnext_station_factory_seam.md` mixed the decision boundary with the implementation blueprint. I split the artifact: this seam now records the eigenquestion, problem, recommendation, options, and open questions; the concrete 24x7 worker, queue, gate, registry, and launch contract lives in `research_areas/specs/active/engine/lean/GP-225_leanmill_vnext_station_factory_spec.md`.

### Turn 3 — Claude (2026-05-21) — Shared kernel OperatingUnit/WorkItem primitive shipped

Open Question 1 is resolved. The LeanMill mill-company gap analysis
(`analytics/public/leanmill/_archive/COGNITIVE_FIRM_MILL_COMPANY_GAP_ANALYSIS_2026-05-21.md`)
showed cognitive-firm had the outer governance shell but no generic production
middle layer. That layer is now built in the public kernel:

- `OperatingUnit` — typed contract for one production lane (LeanMill's
  "station" is a tenant name for an `OperatingUnit`): allowed work kinds,
  worker roles, bounded exits, SLA, operator/governance triggers.
- `WorkItem` — durable queue row with lease-fenced claims (monotonic
  `claim_token`), idempotent enqueue, retry, dead-letter, and a required
  bounded exit drawn from the unit's `allowed_exits`.
- Every transition emits a canonical `KernelEvent`; an operating-unit
  dashboard read model projects backlog/claimed/p95/throughput/blockers.
- Kept generic: no Lean/proof semantics in the kernel. Protocol doc:
  `cognitive-firm/docs/protocols/work-items.md`.

Decision boundary this sets for LeanMill: the local SQLite WorkItem queue
(Option C) was the correct bootstrap, but the *replacement trigger* is now
contract stability rather than a scheduled date. Migrate a LeanMill station to
the kernel `OperatingUnit`/`WorkItem` API once that station's work kinds and
exit set have stopped changing; keep Lean execution, repair-family specs, and
proof-value ratification in the LeanMill tenant overlay. Stations whose
schemas are still moving stay on the local queue until they settle. The
companion spec's worker/queue/gate contract still holds; only the durable
substrate under it changes at migration time.

One deliberate divergence from the gap analysis: it asked for bespoke
filesystem *and* SQLite WorkItem adapters. The kernel instead ships one
JSONL-native primitive and reuses the existing transactional state-backend
seam for T2 fencing, because forking a second SQLite store inside the kernel
would contradict its single-mutation-seam design. LeanMill keeps its own
SQLite queue locally until it migrates onto that shared seam.

### Turn 4 — Codex (2026-05-21) — Station intent now seeds concrete work

Open Question 3 is partially advanced. The local station scheduler exposed the
right next station, but it still emitted generic station WorkItems that required
operator-filled artifact paths. `leanmill_learning_work_seeder.py` now converts
current station artifacts into concrete bounded WorkItems: guarded
repair-canary probes, API LLM proposal jobs, and subscription-agent sibling /
heldout tasks. The seeder preserves the seam boundary by setting explicit
credit flags and by naming Governance Gate as the only proof-credit authority.

Decision boundary: seeding concrete work is now part of the local LeanMill
factory, not a human operator duty. Scientific value remains outside the
seeder: Proof Execution, proposal gates, agent receipts, and Governance Gate
determine the typed exit.

### Turn 5 — Codex (2026-05-21) — Source scouting gets a no-laundering bridge

Open Question 3 is further advanced for sourcing. The local factory now treats
source retrieval as inventory, not proof value: theorem-shaped source-search
runs flow through a source-search integration receipt, then a scoped
source-to-canary binding agent task, then `leanmill_source_binding_ingester.py`.
Only the ingester can turn a completed binding artifact into a guarded
`repair_canary_probe`, and every positive source route must carry a matched
negative control before Proof Execution can spend a Lean slot on it.

### Turn 6 — Codex (2026-05-22) — Proof Execution now has priority lanes

The 24x7 queue was saturating workers but mixing closure-oriented family-spec
probes with source-shape and source-bound probes. That inflated utilization
while delaying the highest-value learning-unit exits.

`leanmill_work_queue.py` now exposes lane-aware claim matching, and
`leanmill_probe_worker.py` accepts `--probe-lane` and
`--exclude-probe-lane`. The running local pattern is one daemon pinned to
`probe_lane=family_spec` and one general daemon excluding that lane. The
claim filter runs before lease acquisition, so a general worker does not hide
a closure-lane WorkItem from the specialized worker.

`leanmill_learning_work_seeder.py` also emits versioned repair-family YAML
templates as first-class `family_spec` probe jobs with generated corpus and
static-filter artifacts. This repaired the earlier adapter failure where
template packets referenced stale static filters or corpus rows missing
legacy `sorried_file` fields.

`leanmill_backlog_replenisher.py` now measures total probe backlog plus
lane-specific backlog. The closure lane has its own floor via
`--family-spec-probe-floor`; source-shape probes have a separate floor via
`--source-shape-probe-floor`. This keeps source/scout activity from satisfying
the proof-value lane's capacity target.

Decision boundary: priority lanes are now part of local LeanMill operations.
They improve work mix and handoff; proof value still requires the same
scoreboard, matched-control, and Governance Gate receipts.

Decision boundary: source scouting may scale through LLMs, subscription agents,
and LeanSearch, but source inventory cannot bypass the probe contract or
Governance Gate. Generic agent transcript ingestion excludes source-binding
tasks; source-binding artifacts have their own deterministic bridge into probe
work.

The API proposal worker now has a read-only Codex CLI fallback for API-denied or
API-error cases. That fallback stays in the proposal lane: it inherits the
original allowed proposal types and credit boundary, and its output must pass
the same proposal/schema/source-query gates before downstream work is created.

Observability is now centralized through `leanmill_observability.py`. The event
ledger remains append-only evidence; the observability report is the operating
diagnosis layer that turns queue/events/artifacts into bottleneck classes such
as low-quality source queries, source-binding rejection, dead letters, and
drained-but-lossy cycles. It also reads the latest 24x7 runner receipt so a
station command crash is surfaced as `runner_command_failure` in the same
diagnosis surface.

Dead-letter recovery is narrow and budgeted. `leanmill_dead_letter_triage.py`
may requeue retryable operational proposal-validation items after API/fallback
conditions change, and may requeue subscription-agent tasks that died before
emitting an output artifact. It cannot relabel scientific failures,
source-binding invalidity, probe failures, or Governance Gate outcomes.

Source-request proposal validation now requires a concrete query payload and
binding target: 3-8 `source_query` entries plus 1-12 `target_row_ids`. This
prevents agent transcripts that merely name a family or a desire for siblings
from becoming source-search work without a searchable theorem/source shape and
an explicit row-bound target.

The source-search integration receipt now exposes `allowed_binding_target_rows`.
Source-to-canary binding may only target those rows; query comments, arbitrary
corpus rows, and stale seed rows are not acceptable target-row authority.
`leanmill_source_binding_ingester.py` now enforces the receipt target-row set
before any source-bound probe can be enqueued.

The source-search integration receipt now carries an `active_corpora` list, not
only the legacy 40-row corpus. The current refill corpus is part of the default
resolver so source-bound work against later MCB rows can be validated without
loosening the target-row rule.

Probe execution now reflects scoreboard counts into the WorkItem payload. This
keeps the queue/event health surface aligned with the detailed scoreboard
artifact while preserving the scoreboard as the inspectable evidence file.

### Turn 8 — Codex (2026-05-22) — Source-bound probes preserve corpus authority and preflight direct actions

The first overnight source-bound probes separated two causes of zero closure:
some probes were scientifically weak direct source actions, while some refill
rows were invalidly executed against the stale primary corpus. The local bridge
now fixes both edges. `leanmill_source_binding_ingester.py` writes a
`leanmill-source-binding-probe-corpus-v1` artifact from the receipt's
`active_corpora` and points the probe WorkItem at that corpus, so target rows
from the refill corpus are no longer lost at Proof Execution.

The same bridge now marks positive source-bound tests with `backend=repl_step`,
`score_candidates=true`, and `require_positive_source_action=true`. This forces
a target-state preflight over `exact`, `simpa using`, and `apply` before a
source theorem can consume the direct source-action path. If the source theorem
does not interact positively with the current goal, the exit is a typed
residual/template-step candidate, not a failed broad `apply_easy` closure
attempt.

Decision boundary: source inventory may still produce useful internal lemmas,
but only a positive target-state interaction is eligible for the direct
source-action probe lane. Everything else must be compiled by the Residual
Compiler into a repair template, exact gap, falsifier, hold, or retirement.

### Turn 9 — Codex (2026-05-22) — Source-query contracts replace brittle copied gates

The morning 24x7 run exposed a resilience gap in the sourcing lane. Agent/LLM
source requests often mixed useful Lean declaration/theorem-shape queries with
weak process text. The old gate dropped the whole request if any query failed,
which stranded recoverable work and helped explain why the factory was busy
without producing new governed outcomes.

`leanmill_source_query_contract.py` is now the shared boundary. It normalizes
legacy strings and typed query objects into `leanmill-source-query-contract-v1`
records, accepts declaration references / theorem-shape / structured semantic
search requests, rejects process/control language, and emits inspectable query
quality telemetry. The LLM proposal worker, agent-output ingester,
source-search worker, source-search integrator, and recovery pass all use this
single contract instead of duplicated local heuristics. Typed query objects are
preserved through LLM/agent/recovery handoff and are normalized to LeanSearch
query strings only at the retrieval boundary.

Recovery is mechanized. `leanmill_recover_pruned_source_requests.py` replays
saved proposal artifacts from query-gate rejection events, prunes rejected query
lines, and re-enqueues only proposals with at least three accepted typed queries
and concrete target rows. The 24x7 runner executes this over a bounded recent
window by default. This is recovery of source inventory only; proof value still
requires source-binding, bounded probe execution, matched negative controls,
and Governance Gate ratification.

### Turn 10 — Codex (2026-05-22) — Action intelligence ETL added for factory speed

The next monitoring gap was not another worker. It was that an operator or
agent had to inspect many files to answer basic factory questions: which
subprocess is slow, where source work is being lost, whether lead/cycle time is
breaching station expectations, and what the next concrete action should be.

`leanmill_factory_intelligence.py` now adapts the Cognitive Firm
`OperatingUnit` dashboard and `ActionImpactRecordView` ideas into a LeanMill
read model over the existing SQLite WorkItem queue, JSONL event ledger,
station-health receipt, and observability receipt. It writes
`leanmill_factory_intelligence.json` and `.md` with per-station/per-kind lead
time, active cycle time, wait-before-start, p95 SLA breach, learning-unit flow,
conversion diagnostics, source-search integration holds, source-binding loss
classes, compact action-impact records, and ranked next actions. Conversion
diagnostics bucket loss by subscription-agent transcript to typed proposal,
source-query contract gate, source-binding receipt/corpus mismatch,
source-bound probe outcome, and runner command failure. The 24x7 runner
refreshes this surface every cycle.

The read model now separates operational refresh exits from typed learning-unit
exits and surfaces family-promotion blockers from the repair registry. A
governance refresh, source inventory refresh, residual-source-plan refresh, or
canary-spec validation is operational motion, not proof value. A
validated-family path remains blocked until the registry sees a passing
heldout-independence receipt; same-source-file sibling evidence may strengthen a
candidate family but must not be upgraded into validated-family credit.

Decision boundary: the action-intelligence layer is a projection, not a new
authority. It may say that source-binding conversion is the bottleneck, but it
does not create proof credit, override Governance Gate, or relabel scientific
failures as operational failures.

### Turn 6 — Codex (2026-05-21) — Credit boundaries override action defaults

The first live source-bound probes exposed a no-laundering edge case: the
packet and event ledger carried `source_credit_eligible=false`, while the
row-level action-smoke result inherited its old default for direct source
actions. The local probe drain now reapplies the test packet's credit boundary
onto each row result, including cache hits.

Decision boundary: source-bound probe execution may reuse action-smoke
mechanics, but credit class comes from the WorkItem/packet contract and
Governance Gate, not from the low-level tactic family default.

### Turn 7 — Codex (2026-05-21) — Warm scout outputs can skip API review only when typed

The sourcing lane now has a cheaper fast path. If a subscription-agent source
scout emits parseable `source_request` JSON with concrete LeanSearch queries
and concrete target rows, `leanmill_agent_output_ingester.py` enqueues
source-search work directly. If the transcript is ambiguous, it still goes
through bounded API-LLM review.

Decision boundary: warm agents may accelerate sourcing, but the no-laundering
line stays intact because direct scout outputs become source inventory only;
source-search quality gates, source-binding, probe packets, and Governance Gate
remain downstream authorities.

### Turn 11 — Codex (2026-05-22) — Infra freeze gate defines stop-bugfixing boundary

The 24x7 run exposed a meta-failure: adapter fixes can become the operator's
main loop, displacing proof-science throughput. The control plane now has an
explicit freeze boundary in `leanmill_infra_freeze_gate.py`.

The gate checks recent queue state for infra-class blockers: terminal proof
probes without typed or inferable learning-unit exits, unexpected
negative-control passes, subscription-agent launches without transcript/artifact
receipts, source-binding tasks that cannot be ingested, running probes that sit
past the grace window without a scoreboard artifact, and core-lane dead letters.
It treats old generic `probe_finished` labels as acceptable only when scoreboard
counters imply a typed exit such as `tested_no_positive_signal`.

The source-binding and generic agent-output ingesters were also hardened to
accept direct `artifact_paths`, not only transcript `output_path` references.
This removes a brittle path-dependent loss mode where a worker could produce a
structured JSON artifact but the next station ignored it.

Decision boundary: when the freeze gate passes, LeanMill enters science mode by
default. Operator/agent effort goes to family-spec probes, sibling/heldout
evidence, exact-gap/falsifier extraction, and Governance Gate outcomes.
Infrastructure work reopens only for a fresh freeze-gate failure, a vNext
coverage-gate failure, or explicit operator override.

### Turn 12 — Codex (2026-05-22) — Agent value claims require probe/governance receipts

An adversarial subscription-agent review found a no-laundering bug: the
source-binding lane still allowed agent-authored `exact_gap_candidate` and
`valid_falsifier` decisions to terminalize as no-probe exits. That collapses
the intended split between proposal agents and proof-value authorities.

The binding contract is now stricter. Source-binding artifacts may terminalize
only as `operator_required` or `retired` without a probe. If a scout or
subscription agent declares `exact_gap_candidate`, `valid_falsifier`, or a
closure-like value exit, the artifact is rejected unless a separate
Proof Execution/Governance Gate receipt backs it. The freeze gate now checks
for agent-declared value exits without governance evidence.

Proof Execution also no longer leases probe work unless the worker was launched
with `--allow-heavy-lean`; no-heavy probe workers can inspect but cannot claim
and terminalize proof work. Probe scoreboards are resolved per payload/root and
read only when fresh for the current attempt, which prevents stale shared
scoreboard files from becoming false evidence.

The restart path now reclaims same-worker abandoned leases. `leanmill_work_queue`
has a `reclaim-worker` primitive, and the probe/subscription-agent daemon loops
call it at startup. A supervised daemon restart therefore requeues its own
nonterminal in-flight row immediately and decrements the abandoned claim attempt,
instead of leaving work in `running` until the lease expires.

Decision boundary: agents and API LLMs may propose, bind, repair, or request
operator intervention. They do not produce value exits. Value exits require the
probe/governance path and matched-control evidence.

### Turn 13 — Codex (2026-05-22) — Recovery becomes a control-plane duty

The source-binding bottleneck exposed a second operational failure mode: when a
source-search receipt was good but an agent-authored binding copied a stale row
or invalid candidate, the work became a rejected terminal artifact and depended
on operator memory to rescue. That does not scale.

The recovery boundary is now mechanized. The common source-to-canary binding
path defaults to a deterministic compiler from the source-search integration
receipt: only receipt-listed `allowed_binding_target_rows` and
`top_source_candidates` may be used, and the output is a guarded `canary_spec`
with no source/clean-solver credit. The old agent binding mode remains
available for ambiguous cases, but it is no longer the default copy path.

Rejected source-binding artifacts are also recoverable. The integrator can scan
`rejected_binding_artifact` rows, reload the original receipt, and emit a fresh
deterministic binding work item when the receipt still has allowed rows and
source candidates. The 24x7 runner invokes this recovery before the
source-binding ingester, so recovered work can become probe work in the same
cycle.

Decision boundary: recovery may rescue inventory and produce guarded probes or
typed rejections. It cannot award proof value, promote a family, or convert an
agent declaration into a closure/gap/falsifier without the probe/governance
path.

Follow-up hardening: recovery now refuses to recover recovered rows
recursively, and allocator no-spend signals are enforced in the seeder, API LLM
worker, and subscription-agent worker. If the family allocator says
`do_not_spend_until_new_evidence`, stale queued work retires without a model
call or CLI-agent launch. This prevents held/superseded families from consuming
the warm worker fleet just because they were already queued before the allocator
state changed.

Turn 14: Source-bound loss became allocator pressure. `leanmill_source_quality_feedback.py`
projects source-bound probe/search/proposal losses by repair family and feeds
`leanmill_source_family_allocator.py`. Families with repeated source attempts
and no governed value now receive `repair_source_strategy_before_more_binding`.
The seeder retires stale source-request/sibling work for those families and
emits bounded source-strategy repair or decomposition work instead. This is a
control-plane throttle only: it can redirect sourcing effort, but it cannot
produce proof credit or promote a family without Proof Execution and Governance
Gate evidence.

Turn 15: Source-strategy repair is now followed by lane hold when it still does
not convert. If a repaired source strategy is followed by source-bound probes
with zero governed value, the allocator emits
`hold_source_binding_until_new_target_evidence`. The seeder retires stale
source-search/source-binding/sibling work for those held families but leaves
family-spec proof probes eligible. The warm-agent worker also lints non-proof
tasks and fails structured outputs that declare proof-value exits, so sourcing
cannot smuggle exact-gap/falsifier/closure vocabulary into the event stream.

Turn 16: GM/operator work became queue-visible. `gm_operator_task` is now a
first-class WorkItem kind seeded from allocator actions and claimable by the
in-thread GM/operator. The lane exists to compare supervisor execution against
API LLM and subscription-agent work under the same queue/event discipline. It
can emit source-strategy review, hold review, sibling/heldout review, retire
decision, or operator-required receipts, all with `credit_type=none` and
Governance Gate as the only proof-credit authority.

Turn 17: The validated-family blocker became a finite work lane. The current
registry has candidate families but zero heldout receipt events, so the factory
was repeatedly circling source-binding instead of creating independent heldout
attempts. `leanmill_heldout_independence_scout.py` now reads the registry,
family specs, and active corpora, nominates rows that pass heldout independence
prechecks, and enqueues bounded GM heldout-review tasks. It cannot issue
heldout receipts, promote families, or claim proof value.

Turn 18: LeanMill now has an Andon cord and a policy-profile boundary. The
failure was not that factory intelligence lacked warnings; the scheduler could
continue feeding upstream source/scout work after the intelligence layer had
shown source-bound zero value and verified-exit starvation. `leanmill_andon_cord.py`
is the stop-the-line control: it reads the same factory-intelligence and queue
state, emits `leanmill_andon_cord.json`, and records containment policy rather
than another advisory paragraph.

The 24x7 runner consumes that policy. When the cord is active, it pauses new
external scout seeding, resets proof-probe cooldowns, auto-drains no-credit GM
review work, and keeps family-spec/heldout proof-value probes preferred. The
watchdog refreshes the cord every cycle after factory intelligence refresh.

This turn also sets a no-sprawl boundary. Normal live launch now uses
`leanmill_factory_policy.json` profile `supervised_24x7`; the watchdog starts
the runner with the profile instead of a long list of flags. New operating
choices should go into policy artifacts, station contracts, allocator outputs,
family specs, or Andon containment before adding another permanent runner flag.

Live supervised subscription workers are Codex-only. Claude remains available
for explicit adversarial review, not as an always-on source/repair worker.

Decision boundary: scale readiness is MECE across queue health, worker
conversion, governance safety, and proof-value conversion. If source-bound
probes have reached Proof Execution but yield zero governed value, source
binding is a secondary repair lane. The top action should move to heldout
construction, family confirmation, exact-gap/falsifier extraction, or another
proof-value conversion blocker.

Turn 18: The heldout path produced its first validated family. The scout-to-work
bridge is now `leanmill_heldout_promotion_worker.py`: scout nomination becomes
either bounded template work, a `heldout_family_spec` probe, or a
`leanmill-heldout-receipt-v1` candidate only after governed positive evidence
plus matched negative-control failure. `ennreal_tsum_condensation_planner`
became `validated_family` through the heldout receipt for
`MCB_003_le_tsum_schlomilch`; the stable local registry path is now
`analytics/public/leanmill/dashboard_data/repair_family_registry.json`.
Scratch `/tmp` roots are discovery inputs, not the default registry contract.

Turn 19: The Evaluation Harness is prepared but gated. The benchmark contract is
now the four-arm attribution comparison: public static tools, governed static
tools, governed adaptive execution, and governed adaptive residual curriculum.
`leanmill_benchmark_prep.py` freezes the row tiers, contract path, readiness
gate, and next blocker. Current prep has enough target-context-ready rows and
one validated family, but only four candidate-or-better families; full
benchmark launch remains gated until the family inventory reaches five
candidate-or-better families.

Turn 20: Terminal zero-score probes now force a next bounded exit. The
premortem failure was straightforward: the mill could remain safe while
accumulating `tested_no_positive_signal` probes, leaving the next repair,
exact-gap, falsifier, or retirement decision to operator memory. That is not a
scalable learning-unit factory.

`leanmill_post_probe_triage.py` now scans terminal proof-probe WorkItems,
reads their scoreboard-backed exit, marks the original probe as triaged, and
enqueues one follow-up. A `family_spec` no-signal probe becomes a bounded Codex
repair/exact-gap/retire task that must preserve matched negative controls.
Other no-signal probes become exact-gap/falsifier/decomposition proposal work
instead of another source-binding loop. An unexpected negative-control pass
becomes a Governance Gate safety task.

Turn 21: Source leads outside the active corpus are now treated as corpus
expansion inputs before proof binding. The source-search integrator no longer
lets stale seed row IDs or inactive `/tmp` row IDs become probe targets merely
because an agent copied them into a binding. It authorizes only rows present in
the active corpus set, plus deterministic unique MCB theorem-suffix aliases,
and records unresolved rows as `unresolved_binding_target_rows`.

The runner now refreshes a generated active corpus,
`mcb_expand100_active_corpus.json`, from existing expand100 Lean target files
through `leanmill_corpus_expansion_from_files.py`. This gives sourcing agents a
clean route for new target evidence: request corpus expansion or resolve a
unique alias, then source-bind against active rows under the same matched
negative-control probe contract. The first generated corpus contains 132 rows.

Turn 22: Two conversion blockers are now explicit seam decisions. First,
source-bound probes with repeated zero governed value are a hard spend gate,
not an allocator hint. The source-quality feedback layer can escalate straight
to `hold_source_binding_until_new_target_evidence` after repeated no-value
source-bound attempts, while leaving family-spec and heldout proof lanes
eligible.

Second, a missing local target file is an operational corpus/materialization
gap, not a mathematical exact gap. Several post-probe agent artifacts were
diagnosing rows whose `sorried_file` pointed at a mathlib module path such as
`Mathlib/Analysis/PSeries.lean`; Proof Execution never reached a real target
state. The seeder now prefers executable rows and resolves stale MCB row IDs by
unique theorem-suffix alias when an executable active row exists. If no readable
target file can be found, the row is unresolved and the probe is not enqueued.

Decision boundary: post-probe triage creates work only. It does not create
proof value, update registries, promote families, or bypass Governance Gate.

Turn 21: Recovery of operational proposal failures is now a factory duty, not a
manual SQLite repair. RCA on the low-conversion loop showed two distinct
causes: source/family scientific conversion remained weak, and a control-plane
adapter caused terminal proposal/decomposition failures when model output
contained earlier diagnostic JSON or when artifact names exceeded filesystem
limits. `leanmill_llm_proposal_worker.py` now persists raw API output before
parsing, scans every JSON-object/list candidate in a response, and falls back
to the Codex CLI proposal lane only after API output is unparseable.

`leanmill_retryable_failure_recovery.py` requeues only terminal operational
proposal/decomposition failures after such adapter fixes. It records requeue
count and reason in the WorkItem payload and event ledger. It does not requeue
proposal rejections, no-signal probes, source-binding invalidity, or Governance
Gate outcomes.

AST/goal-feature extraction remains a future routing upgrade. The current
authority boundary stays typed proposal/source-query contracts plus Lean replay
and Governance Gate; AST features can improve source matching and family
selection but cannot create proof value or replace controls.

Turn 23: Claude adversarial review exposed an accounting and backpressure
failure in the 24x7 loop. The dashboard was mixing proposal/source artifacts
with learning-unit exits, and the source-bound hold policy counted only
completed source probes. That allowed scout/proposal bursts to queue many
source-binding probes before the zero-conversion hold took effect.

`leanmill_factory_intelligence.py` now delaunders the read model: governed
closures/gaps/falsifiers live in `proof_value_exit_counts`; expected no-signal
probe outcomes and retire/hold decisions are learning exits; proposal
validation, agent notes, source-search integration, and source-binding
compilation are intermediate flow. This makes queue motion visible without
letting it masquerade as proof value.

`leanmill_source_quality_feedback.py` now counts queued/running source-binding
probes as source spend. Once a family has pending or completed source-bound
spend above the no-value threshold, `hold_source_binding_until_new_target_evidence`
can fire before the probes consume more Lean slots. `leanmill_learning_work_seeder.py`
now retires open source-binding probes and source/proposal-validation work for
held families while leaving family-spec, heldout, and other proof lanes
eligible. In the first repair pass, this retired 82 open source-bound tasks and
then 49 queued source/proposal-review tasks, narrowing the open queue back to
proof/heldout work.

Claude adversarial review then found the remaining defect: claim-time
retirement still allowed enqueue-time source/scout fan-out, so the mill could
spend cycles creating work it would later retire. The next repair moved the
hold upstream. Clean repeated source-bound no-signal now trips hard hold even
when the loss score is low; `leanmill_agent_output_ingester.py` blocks direct
source-search and source-review enqueue for held families; `leanmill_source_search_worker.py`
retires stale held-family source-search at claim time; and the seeder skips
held-family source expansion. After this repair, open work narrowed to proof
probes plus routine refresh rows instead of source/proposal backlog.

Decision boundary: source/scout scale is useful only when it converts into
active target evidence or proof-value probes. When source-bound conversion is
zero, scale pressure moves to family-spec probes, heldout construction,
post-probe repair, exact-gap/falsifier extraction, and tested retirements.

Turn 24: Argument sprawl became an operational defect, not a style complaint.
The restart after Turn 23 exposed two compounding failures: patched code was
not enough while warm daemons still carried old output contracts, and probe
packet command timeouts were being set by whichever wrapper launched the drain.
That made multi-test canaries vulnerable to premature wrapper timeout even
though the per-test Lean wall cap was reasonable.

The fix moved normal tuning into the folder-local factory policy. Added
`leanmill_factory_config.py` and wired `leanmill_24x7_runner.py`,
`leanmill_backlog_replenisher.py`, and `leanmill_learning_work_seeder.py` to
consume `leanmill_factory_policy.json` profile sections. The live
`supervised_24x7` profile now owns packet-level probe command timeout,
probe-timeout overhead, queue floors, scout limits, and cooldowns. The seeder
writes `command_timeout_s` into every proof-probe WorkItem so the timeout
travels with the canary packet instead of hiding in a launch command.

The source-hold contract also moved from prompt preference to executable lint.
For `expected_exit=sibling_or_heldout_target_evidence`, subscription-agent
output may not use `proposal_type=source_request`; it must emit decomposition,
hold, retire, target evidence, or a downstream probe contract. This prevents
held source families from re-entering the source lane through a weak warm-agent
prompt. External source scouts remain the only source-request lane, and only
when the allocator permits source spend.

Verification: policy JSON parses, affected scripts compile, seeder/replenisher/
agent-worker/runner self-tests pass, and the vNext coverage gate remains
`47/47` at `100%`.

Turn 25: Low-burn mode exposed a lane-naming ambiguity. The operator wanted
reduced consumption while keeping learning exits alive. The live process shape
had already moved to `supervised_24x7_low_burn`, but old high-burn tmux
sessions remained beside it, and the profile still let the general
`probe_floor` seed source-shape probes. That made the mill spend Lean slots on
source-shape inventory when the intended low-burn lane was family-spec proof
probing.

The live launch surface was normalized to one low-burn runner, one watchdog,
one paid LLM proposal worker capped at `$10`, one warm Codex repair agent, one
Codex source scout, the local source-search worker, and the two dedicated proof
probe daemons. The low-burn profile now sets `learning_max_probe_families=0`
and `probe_floor=0`, while preserving `learning_max_family_spec_probe_families=1`
and `family_spec_probe_floor=1`. Two stale queued source-shape probes were
retired with `exit_kind=low_burn_source_shape_retired`; the already-running
probe was allowed to terminate normally so its lease can close through the
worker path.

Current operating rule: low-burn means no automatic source-shape proof probes.
It keeps proof-family validation, post-probe triage, bounded proposals, and
bounded warm-agent repair alive. Source scouting continues at a reduced floor,
but source-shape Lean spend must be deliberately re-enabled through policy.

Turn 26: Full-speed monitoring exposed an accounting and proposal-contract
gap. The factory was replaying the same family-spec probe signature and the
read model was counting raw Governance Gate replay rows as recent proof-value
progress. That is valid regression evidence, but not fresh learning-unit
progress. `leanmill_factory_intelligence.py` now emits raw and `unique_*`
counts, and the live verdict uses `unique_proof_value_exit_counts` keyed by
probe signature. The seeder already skips recent terminal signatures; the
dashboard now follows the same no-inflation rule.

The same watch cycle showed subscription-agent transcripts with useful target
evidence being rejected because the API proposal summarizer sometimes omitted
the required `hypothesis` field. `leanmill_llm_proposal_worker.py` now performs
deterministic schema repair for missing non-credit fields from existing typed
evidence (`blocked_edge`, target rows, formal/gap fields, and
`next_probe_contract`) before the proposal gate. It does not widen proposal
types, change credit boundaries, or create proof value. Verification:
`leanmill_llm_proposal_worker.py --self-test` passes and the vNext coverage
gate remains `47/47` at `100%`.

Follow-up: the duplicate replay came from Andon containment zeroing
probe-signature cooldowns while source-bound lanes were under containment.
That was too broad. `leanmill_andon_cord.py` no longer requests signature
cooldown reset, and `leanmill_24x7_runner.py` treats probe-signature cooldowns
as invariant even during Andon containment. Andon may redirect toward
family-spec/heldout work, but it may not make repeated probe signatures look
like fresh learning work.

Turn 27: The next scale bottleneck was validated target-evidence inventory.
Subscription agents were producing decomposition proposals, the API proposal
gate was validating them, and then the row stopped because only source_request
proposals had an automatic downstream bridge. `leanmill_llm_proposal_worker.py`
now enqueues a no-credit `agent_repair_task` with
`expected_exit=family_spec_patch` when a validated decomposition proposal has
`next_probe_contract` or candidate artifacts. The patch task may compile the
proposal into a versioned repair-family spec update or return a typed hold /
operator-required edge; it cannot create proof value. This keeps target
evidence moving toward family-spec probes instead of accumulating as inert
proposal validation.

Turn 28: The family-spec patch bridge needed a deterministic receipt. During
the watch loop, patch-task transcripts claimed YAML updates, but transcript
claims alone were not a sufficient acceptance condition. The subscription-agent
worker now snapshots the intended `repair_families/{family}.yaml` hash before
launch and requires either a changed target-family YAML that parses with the
same family id, or terminal JSON with `exit_kind=operator_required` or
`exit_kind=retired`. Patching a different family file, returning prose with no
target-file change, or exiting 0 without terminal JSON is a failed WorkItem.
This makes `family_spec_patch` an evidence-bearing transition from validated
proposal to probeable family spec, not a transcript-status shortcut.

Turn 29: The overnight full-speed run exposed a resource-allocation defect.
The factory stayed alive and completed thousands of WorkItems, but most volume
went through source scouting/search/proposal loops while recent probes produced
mostly no-signal exits and only thin proof-value evidence. The `supervised_24x7`
policy was therefore shifted to value-sprint allocation: generic/source-shape
probe floors are zero, the family-spec probe floor is four, family-spec probe
seeding is raised, and external source-scout floor/enqueue capacity is reduced
from broad 24-task scouting to a bounded four-task background lane. This policy
keeps sourcing alive as evidence supply, but the primary live pressure is now
family-spec probes and target-evidence promotion.

Turn 30: The proof-backend lane was still wasting opportunity because
family-spec probe selection used allocator/source scores too strongly and
dropped an entire family when any row in that family was missing from active
corpora. The seeder now scores family-spec probes from registry evidence first:
validated/candidate status, useful governed outcomes, heldout success, clean
negative controls, exact gaps, and valid falsifiers dominate source allocator
yield. It also emits partial family packets over executable selected rows while
recording `missing_row_ids`, instead of skipping a strong family because one
sibling row has no readable target file. This reopened high-evidence families
such as ENNReal and convolution for proof-backend work without weakening the
Governance Gate or duplicate-signature guard.

Turn 31: The post-probe agent lane exposed a mini-step failure mode. A
subscription agent can produce a well-formed next artifact, but if ingestion
only records that artifact, the factory has created a note rather than a
learning-unit exit. `leanmill_agent_output_ingester.py` now treats
`leanmill-post-probe-next-artifact-v1` as a compiler input: `repaired_canary`
artifacts enqueue scoped `agent_repaired` proof probes, while true
`exact_gap_candidate` / `valid_falsifier` artifacts enqueue Governance WorkItems
with candidate files. Transcript parsing preserves the stdout JSON block even
when CLI stderr fills the transcript tail, so typed `decision` fields win over
filename/token coincidences. The Governance candidate gate now rejects vague
gap/falsifier artifacts that lack a formal/gap statement or blocked edge plus
evidence.

The same turn fixed row-scope and corpus hydration for repaired canaries.
Post-probe repaired-canary artifacts may narrow replay to declared `row_id` or
`target_row_ids`; the ingester filters the packet and corpus together before
hydrating executable rows from configured corpora. Missing unrelated siblings no
longer block a concrete repaired row, while genuinely unavailable rows remain
typed blockers. This keeps agent repair outputs moving into bounded proof probes
without letting stale source-binding corpora or missing local target files become
fake exact gaps.

Turn 32: The next watch cycle exposed a different proof-lane starvation mode.
The family-spec floor requested several proof probes, but the replenisher asked
the seeder for too narrow a top-ranked candidate set. The enqueue gate then
correctly rejected many candidates as open or recent duplicate signatures, so
the queue showed low proof concurrency even though duplicate replay protection
was doing its job.

Decision boundary: do not tune around this by weakening proof cooldowns.
Duplicate probe signatures are not new learning-unit exits. The fix widens the
policy-owned candidate pool through
`backlog_replenisher.overgenerate_factor` and records a replenisher receipt
with `unmet_after_replenish`, seed skip counts, duplicate blockers, and a
`starvation_reason`. If the widened pool still cannot produce distinct proof
packets, the correct next action is heldout/template diversification or tested
hold/retirement, not replaying the same packet for utilization optics.

Turn 33: The following watch cycle found a conversion bug at the
subscription-agent/template boundary. Completed `family_spec_patch` tasks had
deterministic patch receipts showing target-family YAML changed and parsed, but
the generic agent-output ingester still treated those transcripts as ambiguous
agent prose and enqueued `agent_output_review` API-LLM jobs. Those reviews
converted several patch tasks into `source_request`, which pushed the mill back
into low-yield source-bound probing instead of replaying the changed
family-spec templates.

Decision boundary: family-spec patch evidence is not source-scout evidence.
A changed, parseable target-family YAML receipt is accepted only as no-credit
family-spec inventory, then it must pass the normal Family Spec Gate and
Proof Execution/Governance path before any proof value exists. Terminal
operator-required/retired patch receipts remain no-credit typed exits, and
failed or missing patch receipts become typed blockers. The ingester now
bypasses API-LLM source-review for `expected_exit=family_spec_patch` and
retires any stale review WorkItem for that patch. This fixes throughput without
laundering: closures still require family-spec proof probes plus Governance
Gate receipts, while template edits merely create new replayable inventory.

Turn 34: The proof-lane cooldown model was refactored after the same starvation
pattern recurred. The previous seeder treated a repair family as the proof
learning-unit identity, so many versioned templates collapsed into one family
packet and then into one recent `probe_signature`. That protected against fake
replay, but it also prevented distinct row/template checks from reaching Proof
Execution.

Decision boundary: a repair family is memory; the executable learning unit is
a canonical proof-probe shard. The seeder now centralizes admission in one
skip-decision function: proposal and subscription-agent generation remain
family/replenish spend-scoped, while `repair_canary_probe` admission is
signature-scoped. Family-spec probes are emitted as row-sharded packets with
their own `probe_signature`, selected row, and matched controls. This preserves
the anti-laundering invariant that identical packet replay is blocked, but
allows distinct rows under the same family to run and produce separate
learning-unit exits.

The same turn added subscription-agent usage receipts. Codex/Claude CLI tasks
now record prompt/output character counts, estimated tokens, runtime/model
label, wall time, `subscription_mode=true`, `api_llm_call=false`, and
`cost_usd=0`. Factory intelligence aggregates those estimates so subscription
token burn can be compared against downstream typed exits instead of being
invisible.

Turn 35: Warm-agent telemetry was extended to the scouter and repair lanes as
a single accounting surface. The first usage receipt made completed
subscription-agent launches visible, but active warm agents and source-scout
tasks were still hard to inspect while they were running. That made it too
easy to misread subscription token burn as either zero or unbounded.

Decision boundary: subscription agents are station workers, not opaque chat
sessions. The worker now stamps usage receipts with WorkItem id, worker id,
task kind, station, family, expected exit, agent id, session reuse, runtime,
wall time, and estimated prompt/output/total tokens. Factory intelligence
also reports currently open warm-agent work by kind, worker, and station, plus
newly-created terminal rows that lack a usage receipt. Low-count proposal
rejections remain visible as non-blocking signals and become root-cause
recommendations only through policy-owned thresholds. This does not give agents
any proof-credit authority; it makes their capacity and output quality
auditable against downstream learning-unit exits without letting a small
proposal-quality blip hide a proof-lane bottleneck.

Turn 36: Benchmark readiness exposed a registry-status interpretation bug.
The registry now distinguishes true `validated_family` from
`validated_family_requires_true_holdout_check`. The latter is not validated
credit, but it is candidate-or-better inventory with sibling evidence. The
four-arm Evaluation Harness readiness gate was undercounting that inventory by
only accepting literal `candidate_family` plus `validated_family`, which made
the benchmark appear blocked despite one validated family and several
sibling-rich heldout-pending families.

Decision boundary: heldout-pending candidate inventory may support the
Evaluation Harness gate, but it may not be reported as validated-family
evidence. The contract now counts `candidate_family`, `validated_family`, and
`validated_family_requires_true_holdout_check` toward candidate-or-better
inventory, while only `validated_family` counts toward the validated-family
requirement. This follows the benchmark preregistration without weakening the
heldout receipt standard.

Turn 37: An engineering-discipline pass landed on 2026-05-23 to close gaps the
architecture review flagged as scaling-brittleness signs. Five strands.

(1) Phase-A kernel residency for the LeanMill primitives that already passed
the boundary tests in `scripts/README.md`. The work queue
(`leanmill_work_queue.py`), the typed source-query contract
(`leanmill_source_query_contract.py`), the policy reader
(`leanmill_factory_config.py`), and the path constants
(`leanmill_paths.py`) now live under `src/ztare/leanmill/` as
`work_queue.py`, `contracts/source_query.py`, `policy.py`, and
`paths.py`. The original scripts keep thin re-export shims at their
former paths so existing sibling imports across ~14 workers continue to
work without modification. The kernel boundary is preserved: nothing in
`src/ztare/leanmill/` imports from `scripts/`. Every worker that imported
through the old paths was re-self-tested through the shims; all pass,
including `leanmill_24x7_runner.py --self-test`. A new package module
`src/ztare/leanmill/common.py` provides the canonical helpers
(`read_json`, `write_json_atomic` via tempfile + `os.replace`, subprocess
`run` with explicit timeout, `sqlite_open` with WAL + busy_timeout) that
the duplicated worker primitives can migrate to incrementally.

(2) Append-only event ledger durability. `append_event` in the queue
module now `fsync`s after every write. Previously a kernel panic between
the buffered write and OS flush would silently drop a record from the
audit ledger. The cost is one fsync per event; for a research apparatus
that is under-counted volume the durability is the right trade-off.

(3) Retry-budget honesty. `reclaim_worker_claims` no longer decrements
`attempts` on requeue. The worker incremented `attempts` on claim; the
row was abandoned without a terminal status; that attempt counts as spent.
Previously the refund let a worker that crashed in a tight loop bypass
`max_attempts` indefinitely. `reclaim_all_open_claims` still refunds
because that path is a deliberate factory shutdown, not a crash; the
self-test was updated to reflect the asymmetric semantics. Operators who
depended on the soft-retry-on-restart behavior should bump
`max_attempts` defaults rather than reverting this change.

(4) Evaluation Harness pre-registration discipline encoded as code. The
runner now (a) verifies `contract_sha256` against the on-disk contract
file at startup and refuses to run on mismatch (`--skip-contract-sha-check`
is debug-only); (b) validates every arm's `route` tactic against the
contract's `tool_universe` (pre-reg hard failure #4); (c) enforces
`wall_timeout_s_per_row` from the contract budget per row, not just per
candidate (pre-reg hard failure #5); (d) supports
`--snapshot-repair-families-dir` to air-gap the `repair_families/`
directory against mid-run edits by the live 24x7 mill (pre-reg hard
failure #3); (e) captures Lean toolchain pin, `lean --version`, Mathlib
commit, and per-spec-file SHA256 in the run receipt for reproducibility;
(f) records `target_kind` on every row record and audits closure-shaped
verdicts against it (pre-reg hard failure #2). The infra-freeze gate
similarly now reads the agent-declared `governance_report` file and
verifies a matching ratification record exists with hash match, rather
than accepting the field's presence as evidence.

(5) Defense-in-depth on the heldout receipt matcher. The
`_record_matches_governance` helper now refuses to match when no proof
or artifact hash was supplied; the upstream `validate_receipt` already
required hashes for proof-value outcomes, but the matcher previously
would have returned True for a hashless receipt that bypassed validation
through any future code path.

Live finding from running these checks: the on-disk evaluation harness
contract file's SHA256 does not match the value pinned inside the file
itself. Pinned: `6fbdce…6e71a90`; actual:
`ed46ada57dba316af345aa0c9895cbd07e68f6753069a525946c112249f8617c`.
The contract was edited after pinning. Before any credited run, the
operator must reconcile: either re-pin to the current hash (accepting
the post-pin edits) or restore the file to a state matching the pinned
hash (rejecting the post-pin edits). The new SHA-check refuses a
credited run until this is resolved.

Two operational artefacts also landed. The LLM critic
(`leanmill_llm_critic.py`) moved from `analytics/public/leanmill/_legacy_lemma_relevance/`
to `scripts/public/control/`, where a read-only operator critic belongs by
layering. A scratch janitor
(`scripts/public/utilities/leanmill_scratch_janitor.py`) provides a
TTL-based purge of aged per-probe-run subdirectories under
`/tmp/rung1/`, replacing the previously implicit "never clean up" policy
that was projected to fill the host disk in ~6 months at current growth.
Default TTL is 14 days; the janitor is dry-run unless `--apply` is
passed.

Decision boundary: every change above is non-laundering and
discipline-tightening. None weakens the Governance Gate as the single
source of proof-value credit; none gives workers self-certification
authority; none bypasses the contract-pinned pre-registration. The
kernel-residency move is reversible (deleting `src/ztare/leanmill/` and
restoring the original module bodies from git rolls it back); the
`fsync`/retry-budget changes can be reverted independently; the harness
hardening defaults to strict with explicit `--skip-*` flags for debug.
Operators should not pass the skip flags during any credited run.

Open question that this turn does not answer: the contract SHA drift
must be reconciled by a human. The apparatus correctly refuses to run a
credited benchmark against a drifted contract; what it cannot do is
decide whether the post-pin edits to the contract were intended or
accidental. That call belongs to the operator who made them. A second
deferred question: the Lean toolchain pin
(`ztare_proofs/lean-toolchain` = `leanprover/lean4:v4.30.0-rc2`) is a
release candidate, not a stable. Publication of a credited benchmark
should pin to a Mathlib-compatible stable build and record both the
exact Lean binary and Mathlib commit in the run receipt; the harness
already captures these into the receipt, but the choice of stable
remains an operator-substrate decision.


### Turn 38 — Codex (2026-05-25) — Family-spec positive repair symmetry

Turn 38 corrected a post-probe handoff asymmetry that blocked C-supply conversion. Family-spec probes already had a structured YAML repair lane for invalid negative controls, but a probe with matched negative controls and zero positive compile candidates was routed to a generic `repaired_canary` diagnostic task. The spectral probe batch showed the failure clearly: 8 tests completed, 4 matched negative controls failed as expected, 0 unexpected negative-control passes, 0 compile candidates, and 0 ratified closures. Safety was working; the positive route was weak and the follow-up contract was too vague to repair the family spec.

Decision boundary: any proof-affecting family-spec template failure now routes through a checked family-spec patch contract when YAML repair is plausible, regardless of whether the failed side is negative-control safety or positive-template productivity. The new `family_spec_positive_repair` mode uses the existing operator-contract/action-card machinery, target YAML write scope, same-row candidate receipts, target self-reference checks, family-spec gate validation, quarantine/feedback retry, and Governance-Gate-only credit boundary. It does not claim new C-supply by itself; repaired rows must still reprobe and earn governed value.

This is a factory invariant, not a spectral-row patch. Generic `diagnose why templates failed` work items are no longer an acceptable handoff for family-spec no-positive probes. Already-triaged no-positive family-spec probes are backfillable into the structured positive-repair lane so old vague follow-ups do not remain stranded.


### Turn 39 — Codex (2026-05-25) — Watchdog drift restart

Turn 39 fixed a supervision gap exposed immediately after `family_spec_positive_repair` was added to policy. The queue contained structured positive-repair work and one 24x7-spawned Codex worker claimed it, but the three long-lived warm Codex tmux sessions were still running their old command line without the new `--claim-patch-mode family_spec_positive_repair` fragment. They were alive and idle, so the old watchdog classified them as healthy even though they could not claim the new C-supply repair lane.

Decision boundary: a worker daemon is not healthy merely because its tmux session exists. For bounded daemons with policy-owned command fragments, the watchdog now checks the live process command. It also consumes worker-version health and treats a stale watched-source runtime as a restartable drift condition. If required fragments are missing, or the worker heartbeat says the live process predates current watched source, and the worker owns no running queue claim, the watchdog restarts the session with the current policy command. If the worker owns a running claim, restart is deferred and recorded. This makes policy edits and code deploys operationally active without hand-killing daemons and avoids interrupting an in-flight repair.


### Turn 40 — Codex (2026-05-25) — Positive repair activation

Turn 40 closed the next handoff gap after the first `family_spec_positive_repair` task succeeded. The agent produced a checked YAML patch and the family-spec gate passed, but no new probe was enqueued for the repaired row. That would leave the mill with a valid template mutation but no governed evidence about whether it improved C-supply.

Decision boundary: a successful positive-template repair must immediately enqueue a bounded family-spec reprobe over the repaired candidate rows, using the existing learning-work seeder and Governance Gate credit boundary. The repair still earns no proof or C-ready credit by itself; only the resulting probe scoreboard can convert it into governed value, exact gap, falsifier, hold, or another typed repair.


### Turn 41 — Codex (2026-05-25) — Queue busy retry for activation handoffs

Turn 41 fixed a queue-layer throughput defect exposed by backfilling positive-repair activations under live worker load. Several activation seeders produced valid probe jobs but failed at `work_queue.enqueue` with `sqlite3.OperationalError: database is locked`. That is an infrastructure loss, not a scientific result.

Decision boundary: transient SQLite busy/locked errors during queue enqueue are retried inside the durable queue layer. Enqueue remains idempotent by `work_id`; retries cannot create duplicate proof credit, and downstream probe/governance still owns all value claims.

### Turn 42 — Codex (2026-05-25) — Positive repair activation reconciliation + NS smoke bridge

Turn 42 closed the activation gap left when a `family_spec_positive_repair` worker fails, quarantines its patch, and the target family spec is later made clean by deploy/sync or another validated edit path. The prior automation only activated reprobes on the worker-success callback. That was too brittle: current family-spec state can become clean after the callback path is gone.

Decision boundary: post-probe triage now reconciles terminal `family_spec_positive_repair` tasks against the current usable family specs. If the candidate rows now have a clean same-row positive + negative-control pair, it writes a bounded activation selection and invokes the existing `leanmill_learning_work_seeder.py` to enqueue the owed family-spec probe. This grants no proof credit; it only restores the conveyor belt from repaired template supply to governed probe evidence. The concrete recovered row on VPS is `MCB_047_adjoint_comp`, now queued as `probe:family_spec:spectral_rayleigh_spectrum_planner:MCB_047_adjoint_comp:4143dc5c5d0d357a`.

The family-spec patch prompt/lint was also tightened: C-supply template backfill and family-spec positive repair outputs must include the actual family-spec gate result, not merely a `validation_command` string. A patch that cannot show the gate result is feedback/retry material, not an accepted patch.

A separate bounded NS smoke bridge was added through `leanmill_enqueue_ns_lemma.py` and the `ns_corpus` contract. It validates the NS target declaration exists, validates the downstream agent-repair worker contract, and enqueues only a no-credit `sibling_or_heldout_target_evidence` task. The initial VPS queue item is `ns:route1StrictMarginOpenObligation:subscription_agent_task`; lane floors remain conservative until the smoke item produces useful feedback.

### Turn 43 - Controlled claims and repair-feedback evidence (2026-05-25)

Observed failure mode: bounded operator runs for a specific C-positive repair/probe could silently claim a different same-lane row, or claim nothing, because the worker predicate was applied only after the queue's priority/age scan window. This made controlled verification non-deterministic under backlog pressure. `leanmill_agent_repair_worker.py` and `leanmill_probe_worker.py` now accept exact `--claim-work-id` filters and widen the bounded scan for exact claims while preserving normal lane scans. This is an orchestration correctness fix, not proof credit.

Observed learning failure mode: the family-spec patch gate can pass while the subsequent governed probe still fails; aggregate scoreboard counts were too weak for the next repair worker to diagnose the proof route. `leanmill_post_probe_triage.py` now attaches bounded failed-candidate evidence (candidate/action family, driver path, body tail, stdout/REPL error tail) to no-positive learning contracts and recent probe feedback. This converts failed probes into actionable feedback without moving proof credit or negative-control authority into arbitrary agents.

MCB_047 validation: the prior positive template using `adjoint_inner_left` left an inner-product goal unsolved. The corrected `spectral_rayleigh_spectrum_planner` template uses the inner-right route and a direct governed reprobe on the VPS produced `ratified_closure_count=1` with `negative_control_fail_count=1` and `negative_control_unexpected_pass_count=0`.


### Turn 44 - Target-bound family-spec probes (2026-05-25)

Turn 44 fixed a target-hydration defect exposed by the Mellin positive-repair loop. A family-spec reprobe for `MCB_008_mellin_comp_rpow` initially executed against the first theorem in a multi-theorem file because stale corpus metadata named `MellinConvergent.const_smul` and the seeder could fall back to line 1. The result was a false `tested_no_positive_signal`: Lean ran, but not against the intended target theorem.

Decision boundary: family-spec probe hydration must bind a concrete theorem target before Proof Execution. Generated declaration row ids such as `MCB_008_mellin_comp_rpow` may supply a theorem suffix, but this is a typed naming contract, not generic underscore parsing. Non-generated row ids fall through to explicit metadata, goal parsing, or single-theorem fallback. Multi-theorem files without a resolved target are refused as target-resolution debt, not counted as no-signal evidence.

The seeder and probe worker now share target-aware probe signatures (`row_id`, candidate, action family, test kind, target theorem, target line, and body hash), so stale packets and corrected-target packets cannot alias. Factory intelligence now exposes a `target_resolution_read_model` and raises `family_spec_target_resolution_debt` when probes are missing target metadata or carry unresolved rows.

### Turn 45 - Mechanism vs moat evidence split (2026-05-26)

Turn 45 fixed a claim-discipline gap exposed by ZPow no-signal drains and the competitive-readiness review. The old family-spec gate could reject holes and duplicate controls, and the patch worker could reject new self-referential positives, but old YAML could still seed probes whose positive body named the target/source theorem or wrapped a known public Mathlib lemma with light glue. That made governed closures truthful as mechanism evidence while still weak as competitive evidence. The factory narrative could drift from “C generated a governed learning exit” to “LeanMill has solver lift,” which is not justified without the pre-registered arm comparison.

Decision boundary: family-spec validation is now target-context aware. `leanmill_family_spec_gate.py` loads current C-supply row contexts by default and passes target/source theorem names into `leanmill_family_specs.py`. Templates that directly reference the target or source/gold theorem are quarantined out of usable probe supply. Public-lemma wrapper positives and generic tactic-floor positives are not automatically quarantined, because they can still be useful mechanism/calibration evidence, but they are emitted under `moat_disqualification_summary` as `mechanism_evidence_only` until the frozen benchmark shows lift over public/static tools. `leanmill_learning_work_seeder.py` uses the same target-aware usable-spec filter before enqueueing family-spec probes, so this is enforced before Lean spend rather than only in a diagnostic report.

`leanmill_factory_intelligence.py` now surfaces `mechanism_vs_moat_evidence_debt` when the gate reports moat-disqualified positives. The intended operator response is to prioritize C-discriminating rows where static/public tools fail, widen non-gold family birth/generalization supply, and run the pre-registered benchmark before making competitive claims. This is a delaundering change only; Governance Gate remains the sole proof-value authority, and no closure/exact-gap/falsifier credit is granted by the new moat labels.
