# GP-225 LeanMill vNext Station Factory Spec

## Status

Active - opened 2026-05-21, compacted 2026-05-26.

## Canonical References

- Seam/decision boundary:
  `research_areas/seams/engine/lean/GP-225_leanmill_vnext_station_factory_seam.md`
- Current architecture, process flow, lanes, topology, handoffs, and operating
  picture:
  `docs/concepts/leanmill_architecture.md`
- Live operating policy:
  `analytics/public/leanmill/dashboard_data/leanmill_factory_policy.json`
- Kernel surface:
  `src/ztare/leanmill/`

This spec is intentionally short. It owns durable LeanMill invariants and
credit boundaries. It does not duplicate the current topology, worker counts,
tmux session layout, or process-flow diagrams; those belong in the architecture
document and policy artifact above.

## Scope

This spec governs the LeanMill vNext operational contract:

- typed learning-unit exits;
- durable WorkItem queue and append-only event ledger;
- repair-family specs and target-aware family gates;
- bounded deterministic, API LLM, subscription-agent, and Lean probe workers;
- live policy ownership and no-sprawl rules;
- watchdog-supervised runtime discipline;
- governance-only proof-value credit;
- evaluation-harness claim boundaries.

Out of scope:

- current worker counts or lane ordering details;
- tmux session names beyond the watchdog/runner/worker role contract;
- claiming broad theorem-proving novelty from current canary closures;
- replacing Governance Gate with LLM, subscription-agent, or supervisor judgment;
- choosing a future distributed broker before local contracts stabilize.

## Decision

LeanMill is a station factory. Its unit of progress is a typed learning-unit
exit, not model activity, raw row count, or transcript volume. Proof value is
credited only after Lean execution plus governance receipts satisfy the
matched-control and C-discriminating boundaries.

The current local distributed substrate is:

- SQLite `work_items` queue for durable WorkItems, leases, retries, and claim
  filters;
- SQLite `artifact_refs` registry for mutable artifact role, path, sha,
  schema, producer, run id, and node ownership;
- JSONL event ledger for append-only station events and artifact references;
- watchdog-supervised tmux daemons for lane subscribers;
- policy-owned release rates, priorities, budgets, backpressure, and Andon
  containment.

This is the node-local file-backed broker/queue version of the factory. In live
operation the VPS queue DB is the authority and laptop-local DBs are
simulations or pulled projections. Do not use multi-writer SQLite over file
sync between Mac and VPS; if replication is needed, replicate append-only
events and snapshots from the authority node. Migration to a shared kernel
WorkItem substrate, Redis Streams, Celery, Temporal, or another broker is an
infrastructure promotion after station contracts stop changing.

## Durable Invariants

- Governance Gate is the only proof-credit authority.
- Workers must emit typed exits or typed blockers. Narrative-only progress is
  not a terminal learning-unit exit.
- Agents and LLMs are bounded proposal/repair/source workers. They cannot
  validate their own proof value, promote families, update scoreboards, or
  award source/clean-solver/repair credit.
- Generation should be agentic where agents are stronger: source discovery,
  semantic source-to-target binding, family-birth distinction, repair-template
  search, and adversarial duplicate/laundering review. Verification remains
  deterministic: target faithfulness, existing-Mathlib target disqualification,
  source allowlists, active-corpus authority, static no-signal, matched
  negative controls, Lean execution, governance, and strict C read models.
- Agentic generation spend must be gated by deterministic consumability
  preflights when the lane has known empty-input failure modes. Demand pressure
  may request attention; it may not spend a template or family-birth lane unless
  the no-enqueue preview shows concrete jobs or clusters under policy.
- Terminal agentic generation outputs must satisfy the policy-owned handoff
  contract. A completed agent row must either carry a downstream deterministic
  activation/integration/governance work receipt or a typed blocked/skipped
  receipt visible to factory intelligence. Missing handoff receipts are
  leakage, not successful generation. The durable queue boundary must apply a
  fail-closed default: when an accepted terminal agentic family-spec patch lacks
  the policy-required handoff receipt at `update_status`, the queue stamps a
  typed blocked/skipped handoff receipt. This creates no credit and enqueues no
  work; it prevents station-local omissions from hiding as terminal success.
- C-supply growth substeps follow the same rule inside the controller: stale
  template/family pressure can be recorded, but agent enqueue happens only after
  preview proves consumable inventory.
- The default generation runtime for high-context LeanMill work is a
  subscription-agent lane, warm when policy enables reuse. API LLM calls are for
  bounded scoring/calibration/review packets with compact JSON outputs. The
  execution-mode criteria are policy-owned so the factory can change intensity
  without adding launch-argument sprawl.
- Heavy Lean execution requires an explicit authorized probe lane and the
  shared resource policy. Cache hits accelerate replay but do not create new
  proof value.
- Repair-family specs are scientific memory. Python row exceptions and
  ad hoc target-specific templates are compatibility debt, not the preferred
  contract.
- Every executable family needs positive canary evidence and matched negative
  controls before it can produce credit-ready evidence.
- Target/gold theorem self-reference is quarantined by the family-spec gate
  when row context is available.
- Source scouting, source review, source search, source-search integration,
  source materialization, family birth, YAML repair, and static mining are
  inventory or routing work. They do not create proof credit.
- Family-spec positive repair must preserve the family lifecycle status. A
  patch that downgrades a `candidate_family` or stronger family to `seed_only`
  is a failed repair receipt unless it exits through an explicit
  `operator_required` or `retired` terminal reason; otherwise a successful
  seed probe can be stranded before non-laundered sibling sourcing.
- Source-search integration receipts may route family-tagged allowed target rows
  into C-supply demand corpora. They are not C credit, and existing Mathlib
  theorem names must be treated as source authority rather than unsolved facts.
- A row sourced from an existing Mathlib declaration snapshot is explicitly
  disqualified from strict C credit unless a separate non-Mathlib target
  authority exists. Materialized `sorry` snapshots are executable probes, not
  unsolved theorem claims.
- Source-derived probes must pass through source-binding, active-corpus
  authority, matched negative controls, Lean execution, and governance before
  they can count as value evidence.
- Static/public-tool success is calibration/control evidence. Strict Path C
  credit requires probe-verified C-discriminating evidence plus public/static
  no-signal where owed by the slice-prep contract.
- C-supply count is deduped by row, not by receipt or replay count.
- Breadth requirements are diagnostic and routing boundaries. Twenty rows from
  one family or one source aperture remain breadth debt.
- Twenty strict rows is the minimum readiness floor, not the stop condition.
  The live policy growth goal is 120+ strict C rows. When
  `continue_after_minimum_floor=true`, growth controllers use the policy growth
  goal and policy-owned clean C-slice sizing to keep broad source/family
  conversion moving.
- Strict C yield is decomposed, not inferred from raw closures. The policy-owned
  read model separates source-inventory rate per hour, population
  Elo/frontier quality, source-to-target binding quality, static no-signal
  survival, probe conversion, governance integrity, and diversity retention.
  The decomposition may route work by bottleneck and next lever; it does not
  create proof credit, benchmark lift, governance pass, or C credit-ready
  status.
- Predictive modeling and PCA over LeanMill yield features require a
  policy-owned minimum resolved-attempt count. Until that threshold is met, the
  factory should emit feature vectors and bottleneck diagnostics only, not a
  fitted model.
- Family-birth enqueue count is policy-owned. A cycle may enqueue several
  distinct birth candidates when they cover distinct families or mechanisms.
- Priority never creates proof value.

## Policy Ownership And Argument Sprawl

Routine operating choices belong in versioned artifacts before they become
long-lived CLI arguments:

- factory policy profile;
- station contract;
- allocator output;
- repair-family spec;
- typed WorkItem payload;
- Andon containment payload.

Permanent CLI flags are allowed for:

- artifact/path overrides;
- explicit authorization gates;
- test, simulation, or emergency overrides.

Live runtime numbers, worker counts, lane budgets, priority values, cooldowns,
claim scan limits, source floors, probe budgets, family-birth enqueue counts,
clean C-slice sizing, growth goals, yield-decomposition thresholds, predictive
model/PCA sample floors, Elo/frontier multipliers, and Andon thresholds belong in
`leanmill_factory_policy.json`. Parser defaults are compatibility fallbacks.

Priority semantics are policy-owned: higher integer priority wins. Workers
claim by priority descending and age ascending after lane filters apply. The
policy must also state the rationale for priority ordering so routing conflicts
are inspectable.

The strict C row count in policy is a minimum floor, not a ceiling. Hitting 20
rows must not stop sourcing or conversion while the 120+ strict C growth goal,
family-breadth debt, or source-breadth debt remains. Additional rows count only
through the same strict C-discriminating probe, static no-signal where owed,
matched-control, and governed receipts.

## Runtime Supervision

The live deployment path is watchdog-supervised:

- `leanmill_watchdog.py` owns tmux launch/restart of the control runner and
  lane daemons.
- `leanmill_24x7_runner.py` is the control-plane runner in live profiles:
  refresh, ingestion, replenishment, read models, Andon/self-correction, and
  status heartbeats.
- `leanmill_c_supply_conversion_prioritizer.py` is a policy-owned feedback
  controller from the C-supply read model back into queued work priority. It
  can favor uncredited and underrepresented families while strict C row or
  breadth targets are short, but it must not update freshness timestamps or
  grant proof, benchmark, or C credit.
- `leanmill_agentic_portfolio_controller.py` is the policy-owned bridge from
  factory intelligence into bounded generation spend. It may dispatch existing
  source-request, source-to-target binding, template-family, family birth, and
  proof-proposal lanes immediately after the governance sentinel from the last
  read model and again after refreshed intelligence, but all outputs remain
  inventory/contracts until deterministic static/probe/governance and strict C
  read-model receipts accept them.
- `leanmill_c_supply_growth_controller.py` is controlled by the live policy
  profile. Its `allow_heavy_lean` gate is a policy value, and the 24x7 runner
  propagates the active gate into the child controller so governed static,
  source-growth, and probe stages are not silently skipped. The same profile
  owns the clean C-slice size, 120+ strict C growth goal, and per-cycle
  family-birth enqueue budget.
- Source-growth corpus ordering is policy-owned. The advisory upstream rater
  may order spend, but `operations.c_supply_source_growth_routing` must be able
  to promote a bounded number of recent ratified seed families ahead of older
  demand families so newborn families get at least one non-laundered sibling
  source-mining pass. This promotion is routing only; source-family matching,
  static no-signal, probes, governance, and the strict C read model still decide
  credit.
- The C-supply growth controller publishes a running receipt before and after
  long stations, including `current_stage`, `latest_selection`,
  `best_selection`, `latest_metrics`, `best_metrics`, effective target, and
  partial round data. Factory intelligence consumes the running latest/best
  selection while status is `running`, instead of using an older
  `final_selection`.
- If the active policy profile sets `resume_previous_running_state=true`, a
  restarted C-supply growth controller must seed from the prior running
  receipt's latest/best selection and checkpoint when those artifacts are
  still fresh and present. This preserves partial governed-static/probe
  conversion state across restart; it is routing-state recovery only and
  cannot grant strict C, benchmark, governance, or proof credit.
- `leanmill_external_source_scout_release_daemon.py` is the dedicated upstream
  source producer. It maintains the policy source-scout floor while the longer
  24x7/C-supply control cycle is busy; it emits only `source_scout_task`
  inventory work and still respects the Andon scout pause. The live full and
  overnight profiles keep a bounded target-bound scout buffer and skip families
  already queued/running so upstream work favors breadth rather than duplicate
  family saturation. The release seeder must use the same policy-backed
  recent-ratified-seed promotion as C-supply source routing before applying
  `max_families`; when the policy enables it, recent zero-source-spend families
  outrank recent families already tried/open. The seeder must derive target
  hints from family specs so newborn families are not excluded by stale
  hand-authored hint maps. Source-bound zero-value pauses direct binding/probes,
  not source scouting by itself.
- Live policy profiles set `runner_drain_lanes=false`; dedicated daemons drain
  source, repair, source-binding, family-spec, and non-family probe lanes.
- A manually launched bare runner is a simulation/debug shape unless policy
  explicitly enables runner lane draining.
- `leanmill_shutdown.py` and `leanmill_restart.sh` are the paired stop/start
  surfaces for tmux deployment.

Workers must emit runtime-version heartbeats. A live worker that started before
the watched LeanMill source/policy/spec surface changed is stale until restarted
or explicitly contained by the watchdog. Terminated historical heartbeats are
observability evidence, not active blockers.

All live code dependencies for watchdog, runner, and lane daemons must be in
`deploy/vps_sync_files.txt`. Introducing a local helper without adding it to the
sync manifest is a distributed-systems fault, because the VPS can pass an
already-loaded cycle and then fail the next import after restart or child
process launch.

Runner-spawned and controller-spawned long commands must use process-group
timeouts. A timed-out static/probe child must not keep writing checkpoint rows
after the controller has moved to the next station, because that produces
split-brain evidence that the current read model did not actually consume.
Shutdown/restart must also clean LeanMill long-running process groups under
policy key `shutdown_cleanup_process_groups`; tmux stop alone is insufficient
when a controller or static/source child has been reparented to PID 1.

C-supply source-growth resume must preserve stage-local evidence, not only the
last published dashboard `latest_*` pointers. If a recent
`round_*.source_candidates.static_checkpoint.jsonl` has records, the controller
may resume it under the policy max-age together with the paired
`round_*.source_static_candidates.selection.json` row context. The checkpoint
and selection are routing state only; strict C credit still requires downstream
slice, template, probe, and governance receipts.

Source-static family matching is a policy-owned conversion gate, not a raw
lexical best-match heuristic. `src/ztare/leanmill/contracts/source_family_match.py`
is the shared contract for growth-controller candidate selection, slice-prep
top-family routing, and template-backfill candidate filtering. Policy
`operations.source_static_family_match_policy` requires distinctive-hit,
confidence, negative-control, and family-status eligibility before a
source-mined static failure may spend downstream C-template/probe budget.
Seed-only lexical matches are allowed to create diagnostics, source demand, or
family-birth pressure, but they must not directly become C-template backfill
jobs. This prevents source breadth from being laundered into false row-family
edges.

The same conversion-eligible status boundary applies to family-birth token
suppression. A seed-only family is not strong enough to erase candidate birth
tokens. `leanmill_family_birth_miner.py` may suppress tokens from
candidate-family-or-stronger existing families, but it must keep seed-only
overlap visible as birth pressure and emit cluster diagnostics when pressure
rows fail to form clusters.

## Queue And Event Contract

The WorkItem queue owns:

- status transitions: queued, claimed/running, done, failed, retired/dead
  letter;
- leases and retry budgets;
- claim tokens and worker ids;
- priority and age ordering after lane filters;
- payloads with station, work kind, expected exit, credit flags, and artifact
  references.
- queue-boundary application of shared contract defaults, including agentic
  handoff fail-closed receipts for accepted terminal generation rows.

The artifact registry owns mutable dashboard artifact identity:

- role: canonical, self-correction, or diagnostic;
- path and sha256 at the authority node;
- schema, producer, run id, node id, and update time;
- conflict visibility for read models when a noncanonical artifact shares a
  canonical path or a registered sha no longer matches the file.

Corrective runs may produce artifacts, but they must not become canonical
factory state by filename collision. Self-correction C-supply runs must use
isolated output paths or fail before writing shared dashboard outputs.

The event ledger owns:

- append-only worker outputs;
- artifact paths and hashes;
- station receipts and blocker classes;
- audit history for read-model reconstruction.

Lane specialization is implemented by queue claim filters, not by trust in
human naming. Source-scout workers claim source-scout work; source-review
workers claim source-review proposals; source-binding probe workers claim only
`probe_lane=source_binding`; family-spec probe workers claim the family-spec
probe lane.

Agentic generation budgets are policy-owned. `operations.agentic_execution_budget_policy`
declares the minimum API LLM token/timeout budget and the minimum subscription-agent
wall-clock/iteration budget for source discovery, source binding, family birth,
C-supply agent work, and upstream routing review. Factory intelligence reports
these budgets in `execution_mode_read_model.declared_budgets`; under-budgeted
complex lanes produce `execution_budget_underprovisioned`. This is an operating
guard against shallow/truncated generation, not a credit rule.

## Learning-Unit Exits

Allowed terminal or consequential exits include:

- qualified source;
- canary ready;
- rejected with reason;
- closure candidate;
- ratified closure;
- exact gap;
- valid falsifier;
- residual-family update;
- reusable repair family;
- tested hold;
- retired;
- operator required.

Intermediate flow such as proposal validation, source-search integration,
agent notes, scout transcripts, source-binding compilation, and dashboard
refresh must be reported separately from proof-value exits.

## Repair-Family Contract

Repair-family knowledge lives in versioned YAML specs under:

`analytics/public/leanmill/repair_families/`

Executable families must include:

- family id and version;
- status and residual match;
- explicit credit eligibility flags;
- positive template(s);
- matched negative control(s);
- bounded backend/action surface;
- target-safe row context behavior;
- evidence path for candidate or validated status when claimed.

Family-spec patch work must produce either a validated target-family YAML
change or a typed terminal decision. Passing a family-spec gate is not proof
value; it only creates or repairs future probe supply.

## Source And Breadth Contract

Outside sourcing is mandatory upstream inventory, but it cannot bypass the
conversion gates. The source path is:

```text
source scout -> source review -> typed source request -> source search
-> source-search integration -> source binding -> source-binding probe
-> scoreboard/governance -> factory intelligence
```

Source requests must contain typed search/query structure and concrete target
row authority. Bindings must target rows authorized by the integration receipt
and active corpus. A source-bound artifact that declares closure, exact gap, or
falsifier value without a separate probe/governance receipt is rejected as an
unverified value claim.

Source-search integration receipts may also route family-tagged allowed target
rows into C-supply demand corpora. That route creates demand, not credit. It
must not relabel an existing Mathlib theorem name as an unsolved target; known
theorem names are source facts unless target resolution produces a distinct
allowed row.

Breadth is a first-class operating constraint. The read model must distinguish:

- family breadth;
- source-file/root breadth;
- source-aperture breadth;
- target-resolution debt;
- source-bound zero-value evidence;
- family/spec conversion pressure.

## Current Credit Definition

A strict C-supply row may be `credit_ready` only with probe-verified
C-discriminating evidence and all of these receipts:

- terminal governed probe receipt from the eligible C proof lane;
- target-safe family/source template;
- public and governed static arms show no positive static signal where owed by
  the slice-prep contract;
- scoreboard reports ratified closure, exact-gap candidate, or valid falsifier;
- matched negative control failed at least once;
- unexpected negative-control passes equal zero;
- invalid negative-control failures equal zero;
- the row is deduped by `row_id`.

Code that needs this boundary must use the shared classifier in
`scripts/public/control/leanmill/c_supply_credit.py`, not a local
`probe_credit_ready` shortcut.

Mechanism evidence, wiring smokes, public-lemma wrappers, target/gold
self-reference, source-search integration receipts, and static-solvable rows
must remain outside competitive moat-grade C credit.

Rows marked `c_discriminating_probe_verified_pending_static_sweep` are
near-ready inventory. They are useful for routing and progress accounting, but
the C read model must keep them separate from strict credit-ready rows until the
static arms are complete and the slice-prep status is
`c_discriminating_probe_verified`.

## Observability And GM Control

`leanmill_factory_intelligence.py`, `leanmill_observability.py`,
`leanmill_station_health_dashboard.py`, and watchdog status must let a cold
operator answer:

- what is running;
- which lanes are backlogged, idle, stale, or starved;
- where conversion is failing;
- whether source breadth and family breadth are expanding;
- which rows are strict C credit-ready and why;
- which probe-verified rows are near-ready but still static-sweep blocked;
- which evidence is only mechanism/calibration evidence;
- what next action is policy-recommended and why.

If that requires reading chat history or manually joining raw scoreboards, the
read model is incomplete.

The GM/operator lane is allowed to create bounded no-credit routing tasks and
diagnostic decisions. It is not a proof-credit authority.

## Evaluation Harness Boundary

The evaluation harness compares frozen arms under equal tool universe, budget,
and governance. It asks whether governed adaptive residual memory adds value on
top of public tools. Tiny runs and smokes can prove wiring health only.

Competitive claims require C-discriminating rows, target-safe templates,
public/static no-signal where owed, matched controls, family/source breadth,
and governed improvement under the frozen benchmark contract.

Clean C-slice sizing is policy-owned. Benchmark or factory reports may cite the
active policy size, but must not bake a fixed row count into the claim boundary.

## Change Discipline

When implementation changes affect topology, lane specialization, credit
boundaries, policy ownership, or operator process flow, update
`docs/concepts/leanmill_architecture.md`.

When implementation changes affect durable invariants in this file, update this
spec. Do not duplicate current worker counts, session topology, or flow
diagrams here.

Current implementation status must be read from VPS-generated LeanMill status
artifacts and factory intelligence, not from this spec.

## Open Questions

- Which stable station should migrate first to a shared kernel WorkItem or
  external broker substrate?
- What evidence should mechanically certify heldout independence for the next
  validated-family promotion?
- What source/family allocation policy should replace conservative routing
  once conversion-rate data is large enough?
