---
description: "Code primitives for separating agent roles, authority, and work routing in the ZTARE org runtime."
---
# Organizational Primitives

> **Up:** [Documentation map](../README.md)

**Status:** public companion to `docs/concepts/architecture.md`
**Paper parent:** *Cognitive Firm*, M-form governance for recursive AI
**Code parent:** `src/ztare/signals/`, `src/ztare/sessions/`, `src/ztare/validator/mform_alignment_audit.py`, `src/ztare/orchestrator/operator_replay_audit.py`, `src/ztare/orchestrator/research_taste.py`, `src/ztare/orchestration/agent_channels.py`, `src/ztare/orchestration/execution_routing.py`, `src/ztare/orchestration/action_intelligence.py`, `src/ztare/cli_org.py`, `scripts/public/control/closure_daemon.py`, `scripts/public/control/agent_daemon.py`
**Philosophical parent:** Chandler (1962), Matzinger (2002), Margulis (1967), Kauffman (1993), Doerr (2018), Hölldobler & Wilson (1990)
**Last revised:** 2026-05-20 (aligned ZTARE tenant overlay with the generic cognitive-firm kernel and added the action-intelligence boundary)

> **How this relates to the sibling org docs.** This doc owns the code primitives
> for role separation: signals, sessions, alignment audits, and routing. The
> reference architecture for a persistent research org is
> [ztare_research_company_architecture.md](ztare_research_company_architecture.md);
> the runnable org tree is [org/README.md](../../org/README.md). This doc
> explains the primitive layer those two build on.

---

## The Relationship to Cognitive Firm

*Cognitive Firm* argues that recursive AI systems require the same structural separation that Chandler documented in human firms: strategic oversight in a general office, operational execution in autonomous divisions, with a deterministic governance layer between them. When the division that generates output also evaluates it, you get specification gaming, metric inflation, and fabricated compliance, regardless of substrate.

This document describes the code primitives that make that separation executable.
They are to *Cognitive Firm* what the
[constrained validation loop](cognitive_gym.md) is to *Epistemic Verification*:
the code-level instantiation of a theoretical claim.

The generic version of these primitives is being factored into
[cognitive-firm](https://github.com/sparckix/cognitive-firm). In this repo,
`org/` is the ZTARE tenant overlay: it proves the primitives against a live
research organization, but the public abstractions should remain usable by
other domains.

| Paper | Theory | Code instantiation | Doc |
|-------|--------|-------------------|-----|
| Epistemic Verification | Ten operations decompose judgment | Constrained validation loop: semantic router, residual diagnostics, deterministic sidecar, contamination gate, operator-agent replay | `docs/concepts/cognitive_gym.md` |
| Cognitive Firm | M-form separation bounds gaming | **This document**: damage signals, session claims, M-form audit, closure map, closure pressure, OKR tree, research direction | You are here |

---

## The Nine Organizational Primitives

Originally four (damage signals, session claims, M-form alignment audit, closure
map). The 2026-04-27 [GP-168](../../research_areas/seams/mission/org/GP-168_org_design_unfalsifiability_seam.md) addendum added two more, closure pressure and the
OKR tree, to operationalize the finding that *bicameral architectures provide
consistency but not closure; closure requires exogenous resource pressure*. The
2026-04-30 added Research Direction: a role-bound external-validity and
attention-routing layer that converts fast operator-agent frontier work into
typed discriminators without pretending taste is evidence. The same session
added Persistent-Agent Channel: a role-office communication primitive that
separates durable agents from transient model invocations. The 2026-05-01
session added Work Routing: a domain-general task decomposition primitive that
keeps the org skeleton reusable outside ZTARE. The nine
primitives now compose the firm's current operational schema.

### 1. Damage Signals (Matzinger Danger Model)

**Biological analog:** The immune system does not ask "is this self or non-self?" It asks "is this dangerous?" Matzinger's danger model (2002) separates identity (who are you?) from damage (are you hurting the host?).

**The M-form problem it solves:** Identity-based authorization (`src/ztare/roles/authorization.py`) answers "is this actor allowed here?" It does NOT answer "is this action damaging the host?" An authorized agent can damage the system legally, specification gaming is precisely this failure mode.

**How it works:**
- Any code can `emit()` a damage signal with a kind (e.g., `cost_spike`, `quality_regression`, `handoff_conflict`, `evidence_contradiction`)
- Signals are plain JSON files under `org/signals/damage/`, one per emission
- The supervisor calls `list_recent()` before making a decision
- No enforcement is baked in, the point is to create the write surface so future invariant tripwires have somewhere to land
- Signals are best-effort (never raise on filesystem issues)

**Code:** `src/ztare/signals/damage.py`

**Any-LLM applicability:** Any multi-agent system where authorized actions can
still be harmful. The damage channel is a typed "something went wrong" surface.
It does not need to decide who caused the damage before making the damage
visible.

---

### 2. Session Claims (Membrane Exclusion)

**Biological analog:** Endosymbiosis (Margulis 1967). When two organisms could both metabolize the same resource, membrane exclusion determines who gets it. The excluded organism defers, not dies.

**The M-form problem it solves:** When two sessions (a Claude conversational session AND a headless cron manager, or two parallel agents) could both act on the same task, uncoordinated writes produce race conditions and corrupt state. Identity doesn't solve this, both sessions may be authorized. The problem is simultaneous access to a shared resource.

**How it works:**
- Claiming a task writes a JSON file under `org/sessions/_claims/<task_id>.json` with owner (session_id), task_id, and expiry
- Any other session that tries to claim the same task while the first claim is live must defer
- Deferred sessions SHOULD emit a damage signal of kind `handoff_conflict`
- Claims are gitignored (runtime coordination, not shipped state)

**Code:** `src/ztare/sessions/claims.py`

**Companion:** `src/ztare/sessions/enforce.py`, `ensure_session()` (idempotent session open) and `require_no_conflict()` (raises on multi-session collision)

**Any-LLM applicability:** Any workflow where multiple agents or sessions operate on shared files. GitHub, CI/CD, multi-agent chat, anywhere two writers can collide on the same artifact.

---

### 3. M-Form Alignment Audit (Immune Self/Non-Self)

**Biological analog:** The adaptive immune system audits cells for foreign peptides displayed on MHC molecules. The audit is stochastic (not every cell is checked), cross-reactive (the checker has never seen this specific pathogen before), and lethal (flagged cells are killed, not warned).

**The M-form problem it solves:** The mutator optimizes the rubric's scoring surface. If the rubric is a narrow proxy of the charter's intent, the mutator will satisfy the rubric while violating the charter, the recurring Goodhart pattern documented in *Cognitive Firm* §5.4. The rubric is the evaluator; the charter is the intent. The gap between them is where gaming lives.

**How it works:**
- Fires stochastically when a qualitative run scores high: `p = 0.15 + 0.65 * sigmoid(score - 85)`
- A "General Office" LLM call audits the champion thesis against the charter while BLINDED to the rubric
- Cross-family model separation: general_office_model ≠ judge_model ≠ mutator_model
- If the General Office finds charter-spirit misalignment, it appends a new rubric dimension at 15% weight
- Max 2 audits per run; late-run high scores (iter > 10) are skipped

**Code:** `src/ztare/validator/mform_alignment_audit.py`

**Integration:** Before main loop: `_mform_audits_this_run = 0`. Start of each iter: `apply_mform_pending()`. After scoring: `maybe_fire_mform_audit()`.

**Any-LLM applicability:** Any LLM evaluation pipeline where the scoring rubric could diverge from the actual intent. The pattern: randomly audit high-scoring outputs against the original specification using a model that has never seen the scoring rubric. If the audit finds misalignment, tighten the rubric. This is the LLM equivalent of internal audit.

---

### 4. Closure Map (Kauffman Autocatalytic Sets)

**Biological analog:** Kauffman's (1993) autocatalytic sets: a collection of molecules is "closed" if every molecule needed for the set's reproduction is produced by some member of the set. An organism that needs vitamin C but cannot synthesize it is not closed on that axis, it depends on external supply.

**The M-form problem it solves:** A research cycle (evidence → hypothesis → experiment → finding → paper) has steps. If only one agent can perform a step, that step is a single point of failure. If NO agent can perform a step, the cycle is broken. The closure map identifies these gaps.

**How it works:**
- Enumerates the research cycle steps
- For each step, lists which agents/roles are qualified
- Flags steps with only one qualified agent (fragile) or zero (broken)
- Reports as a CLI output for operator inspection

**Code:** `python -m src.ztare.cli_org closure-map`

**Any-LLM applicability:** Any multi-agent workflow with a defined process. Map the process steps, list who can do each, flag the bottlenecks. This is organizational design 101 applied to agent workflows.

---

### 5. Closure Pressure ([GP-168](../../research_areas/seams/mission/org/GP-168_org_design_unfalsifiability_seam.md), Pheromone Decay + Mycelial Pruning)

**Biological analog:** Ant pheromone trails evaporate; a foraging route that is
not reinforced disappears within minutes to hours, regardless of how
"important" the colony's deliberation about it was. Mycelial networks
redistribute carbon and nitrogen across the network based on local demand
signals; nodes that stop producing are pruned by withdrawal of resource flow,
not by a budget cap firing. Both are *exogenous* closure mechanisms, the
environment decides, not the organism.

**The M-form problem it solves:** GP-168 (the unfalsifiability theorem) showed
that bicameral architectures, even sophisticated ones with multiple
non-colluding paths, provide internal consistency but cannot close on their
own. Without an exogenous resource constraint, deliberation accumulates
indefinitely; the human becomes the bottleneck because no other force can
declare "this thread is done." Time and budget are the cheapest exogenous
constraints available.

**How it works:**
- Every Task, Key Result, and Objective carries closure-pressure fields in
  its frontmatter (`closure_deadline`, `auto_resolution`, `budget_cap_usd`,
  `budget_spent_usd`, `budget_exhaust_action`, `review_overdue_threshold_days`)
- A stateless daemon (`scripts/public/control/closure_daemon.py`) polls the work-item tree on
  a configurable interval (default 30s)
- When a pressure threshold fires (deadline passed, budget exhausted,
  measurement overdue), the daemon writes a gate to the single executive
  inbox at `ztare_workspace/gates/pending/` with options + an
  `auto_resolution_on_default` rule that fires after N days of principal
  silence
- The [GP-070](../../research_areas/seams/apparatus/supervisor/GP-070_meta_supervisor_goal_orchestrator_seam.md) orchestrator owns mutations; the daemon only schedules requests
  via gates and appends `gate.opened` events to `ztare_workspace/transitions.jsonl`
  (single write-ahead log)
- The principal resolves gates via Orbit (full state) or a configured
  notification provider (compact push channel). The provider owns no state;
  acknowledgements route back to `ztare_workspace/gates/resolved/` with audit
  entries.

**Theatre-detection signal:** Daemon computes a per-Objective *honesty score*
at closure: `(world-measured KRs with non-null last_measured_utc in the
closure window) / (total world-measured KRs)`. If <0.5 across two consecutive
Objective closures, daemon posts: *"OKR honesty score declining. The system
may have collapsed into empty process."* This is the kill signal for the case where
the work-item tree keeps closing Objectives whose KRs were never measured.

**Code:** `scripts/public/control/closure_daemon.py`, gates at `ztare_workspace/gates/pending/`,
write-ahead log at `ztare_workspace/transitions.jsonl`

**Any-LLM applicability:** Any system where deliberation can run indefinitely
without an exogenous deadline. Multi-agent debate, RLHF labeling pipelines,
peer-review queues. Add a per-item time and budget clock, write the
auto-resolution rule alongside, and run a stateless poller. The principle is:
internal consensus is sufficient when present, but cannot be the only mechanism
for termination, an external force (clock or money) must always exist to
break ties the deliberation cannot.

---

### 6. OKR Tree (Multi-Level Objective Hierarchy with World-Measured KRs)

**Biological analog:** Ant colonies have nested objectives: colony-level
("survive winter"), sub-level ("maintain pheromone trails"), bottom-level
("forage from this tree"). The structure spans roughly 10⁵ in timescale
ratio between top and bottom, about one decade per tier across four-to-five
tiers. The relevant property is *extrinsic* measurement: trails that don't
lead to food evaporate; carbon-starved hyphae prune themselves; the
environment measures, not the colony. A unit that measures only its own
success has no external feedback and drifts.

**The M-form problem it solves:** The pre-2026-04-27 work-item primitive
(`org/goals/`) was task-shaped, no Objective layer above (the "why" was
implicit, in the principal's head) and no measurable Key Results alongside
(success was undefined; agents wrote a `## Result` section but nothing in the
world told us if the goal mattered). Without these layers, the org optimizes
for what it can see (tasks closed) rather than what it wanted (outcomes
moved). This is Goodhart's Law at the work-item layer.

**How it works:**
- **Top tier, Objectives** at `org/objectives/<obj_id>.md`. Markdown body is
  canonical; small YAML frontmatter is machine-maintainable. Carries
  `horizon: target_date | open` (durable Objectives outlive quarters at solo
  scale), `closure_deadline`, `auto_resolution: archive_with_postmortem`.
- **Mid tier, Key Results** at `org/key_results/<kr_id>.md`. First-class
  files (not YAML arrays), gives clean git diffs, reassignability,
  KR-level audit trail. Required fields: `measurement` (concrete),
  `measurement_source: daemon | principal` (prefer daemon, solo-scale
  KRs that need principal-driven measurement rot fast),
  `measurement_locus: self | world` (at least one `world` per Objective),
  `kr_type: output | outcome | health_metric` (forces output-vs-outcome
  discipline). Continuous `score: float` set at parent closure; pass/fail
  binaries collapse into self-flattering grades.
- **Bottom tier, Tasks** at `org/tasks/{pending,active,done}/<task_id>.md`
  (renamed from `org/goals/` on 2026-04-27). Carries closure-pressure fields
  (see primitive #5) plus optional `objective_id` and `kr_id` foreign keys
  linking upward.
- Daemon enforces the world-measurement invariant: an Objective with only
  self-measured KRs is rejected at creation (no external feedback).

**Why three tiers, not two or four:** the principal's timescale ratio between
top intent (multi-year, *"produce a body of work that matters"*) and atomic
task (minutes-to-hours) is ~10⁴, which gives one decade per tier across
three tiers. Two would be too coarse, four too ceremonial.

**Code:** `org/objectives/`, `org/key_results/`, `org/tasks/`,
`scripts/public/control/closure_daemon.py`, `orbit/src/components/ObjectiveTreePane.tsx`
(renders the tree with pressure indicators per level)

**Any-LLM applicability:** Any organization or research apparatus that needs
to express *what it's trying to do and how it will know if it worked*. The
controlling piece is `measurement_locus: world`, the requirement that every
Objective have at least one externally-verifiable measurement. Without it,
self-grading drifts toward self-flattery. The
three-tier structure is well-calibrated to organizations whose top-intent
horizon is 10³-10⁴ × their atomic-task duration; very flat orgs (one human +
one agent, hour-scale work, no multi-year intents) can collapse to two tiers.

---

### 7. Research Direction (External-Validity General Office + Taste Router)

**Organizational analog:** Chandler's general office allocates capital and
reviews divisions from outside the operating unit. A research director does
the same for discovery work: it does not write every thesis, score every
candidate, or mutate every substrate. It asks whether the claim is externally
defensible, whether the decisive test is already available from artifacts, and
which hostile discriminator should run before scarce GPU/API/operator
attention is spent.

**The M-form problem it solves:** ZTARE's inner loop is deliberately heavy:
mutator, judge, gates, telemetry, and closure. The recent gp163d and NS
frontier tracks showed a second legitimate loop:

```text
operator <-> coding agent -> narrow script/GPU discriminator -> result
-> ledger/status artifact -> mechanized replay queue
```

That loop is faster than a full ZTARE iteration for instrument repair and
frontier falsification. The risk is that the useful move remains trapped in
chat. Research Direction is the primitive that turns repeatable pieces of that
operator-agent loop into durable machinery.

**How it works:**
- Durable role contract: `org/roles/research_director.yaml`.
- Authoritative mandate: `org/mandates/research_director_mandate.md`.
- Principal preference surface: `org/preferences/principal.yaml`
  (`research_taste` axes).
- Replay compiler: `operator_replay_audit.py` reads durable artifacts and
  writes typed next-test proposals to
  `projects/<slug>/workspace/next_discriminator_queue.jsonl`.
- Taste router: `research_taste.py` ranks next moves by outstanding-problem
  resolution, prize/money potential, architecture fit, and self-recursive
  governance value, with penalties for public-claim risk and infrastructure
  fragility.
- Script productization path: `frontier_script_scaffold.py` and
  `frontier_script_scaffold_runner.py` create bounded script proposals and
  smoke-test contracts before execution.
- Promotion guard: `promotion_guard.py` prevents finding/paper-grade
  promotion while high-severity discriminator debt remains open.

**Boundary with ZTARE:** ZTARE asks: *can this candidate survive the substrate
and cage?* Research Direction asks: *what would make this success
uninterpretable, what is the cheapest hostile test, and is this the right
place to spend attention?* The Director may queue discriminators and write
directives. It does not silently modify substrates, run the inner loop by
default, or promote its own conclusions.

**Runtime / Docker path:** The role can be run manually by an agent reading
the role and mandate files, or as a role daemon:

```bash
python scripts/public/control/agent_daemon.py --role research_director --tick-once --dry-run
docker compose --env-file .env --profile daemons run --rm research-director-daemon python scripts/public/control/agent_daemon.py --role research_director --tick-once --dry-run
docker compose --env-file .env --profile daemons up research-director-daemon
```

For the current end-to-end boot path, task template, and preference-ranking
commands, use `docs/guides/org_runtime_quickstart.md`.

The Docker service is a process wrapper, not a new authority surface. It
mounts the repo, opens a `role.research_director` session, filters discovered
work to tasks assigned to `role.research_director`, and prompts the configured
agent runtime with the Director role, mandate, and principal preferences.

**Current limitation:** The role runtime is productized enough for dry-run and
role-scoped daemon operation. Full autonomous execution still depends on the
configured agent CLI/API being available inside the runtime environment. If
the container lacks the chosen agent executable, use dry-run mode or run the
daemon on the host where the agent is authenticated.

**Any-LLM applicability:** Any frontier research organization where a fast
human-agent loop outruns the formal apparatus. Keep the Director as chooser /
sequencer / compressor; compile repeated primitives into ZTARE; leave
under-specified abductive choices at the Director/principal boundary until
their discriminator contract is clear.

---

### 8. Persistent-Agent Channel (Role Office vs Transient Invocation)

**Organizational analog:** An organization distinguishes offices from
contractors. The CFO can sign, escalate, refuse, and keep records because the
CFO is an office. A one-off consultant memo can influence the CFO, but it does
not become the CFO. In ZTARE terms, Codex / Claude Code / a daemonized
Research Director are persistent role offices when they act under a mandate;
cold-shot LLM calls, judges, mutators, and script-generated critiques are
transient invocations.

**The M-form problem it solves:** Without this split, two bad things happen at
once. Disposable model calls start to look like agents with authority, while
real persistent agents lack a clean way to communicate except through chat
history or ad hoc files. The result is a false ontology: transient calls are
over-personified and durable offices are under-protocolized.

**How it works:**
- `org/channels/<role>/inbox/*.json` is a durable inbox for persistent role
  offices.
- `org/channels/<role>/sent/*.json` mirrors sent messages.
- `src/ztare/orchestration/agent_channels.py` defines the typed envelope:
  `kind`, `from_role`, `to_role`, `subject`, `body`, `thread_id`,
  `causality_id`, `references`, `artifacts`, `expects_response`, `status`.
- `scripts/public/control/agent_channel.py` is the dev/debug CLI projection.
- `src/ztare/orchestration/work_discovery.py` surfaces open channel messages
  as role-daemon candidates.
- Every message/status mutation appends `agent.message.*` to
  `ztare_workspace/transitions.jsonl`.
- `scripts/public/control/org_first_run_setup.py` verifies that role offices, inboxes, A2A
  agent cards, and the daemon dry-run path are reachable before live work.

**Protocol stance:** MCP is the right shape for exposing tools/resources to an
LLM host. A2A/ACP are the right inspiration for cross-agent task/message/
artifact interoperability. ZTARE's local primitive is smaller and stricter:
role-office communication is canonical only when it is mandate-bound,
auditable, and connected to claims/gates/transitions. External protocol
adapters should wrap this primitive rather than replace it.

**Boundary:** This channel does not authorize execution. A message can request
work, hand off context, or ask for clarification. Execution still flows through
authorization gates, proposal gates when required, task claims, constrained
runners, and closure ledgers.

**Any-LLM applicability:** Any system mixing long-running agents and one-off
LLM calls needs this distinction. Treat durable offices as accountable actors;
treat model invocations as artifacts unless explicitly promoted into an
office with a role, mandate, budget, session, and address.

---

### 9. Work Routing (Generic Task Decomposition)

**Organizational analog:** A capable chief of staff does not treat every
request as the same kind of work. Some requests need a memo, some need an
expert review, some need an operating procedure, some need a data run, and
some need a repeatable business process. The first decision is the work mode,
not the answer.

**The M-form problem it solves:** A domain-specific company can accidentally
turn its local vocabulary into organizational law. In this repo, that failure
mode is "everything becomes a ZTARE run" or "everything becomes a science
substrate." In a travel agency it would be "everything becomes an itinerary";
in fintech it might be "everything becomes a risk model." The org primitive
must stay general while allowing domain-specific adapters.

**How it works:**
- Tasks carry an optional `execution_route` in frontmatter.
- If missing, `src/ztare/orchestration/execution_routing.py` infers a route
  conservatively from task body + frontmatter.
- Supported generic routes are:
  `route_only`, `direct_work`, `expert_review`, `scripted_run`,
  `artifact_build`, `experiment_loop`, and `docs_records`.
- Domain-specific names are aliases only. For this repo, `ztare_loop` maps to
  `experiment_loop`, `substrate_build` maps to `artifact_build`, and
  `cold_shot` maps to `expert_review`.
- `scripts/public/control/agent_daemon.py` injects an `EXECUTION ROUTE CONTRACT` into the
  spawned agent prompt. The agent must write the required first artifact
  before acting and must not silently switch modes.

**Boundary:** Work Routing does not authorize work. It classifies the mode.
Authorization still comes from role YAML, mandate, task scope, budget,
proposal gates, and session claims.

**Any-org applicability:** A generic organization can replace the backend
adapter without changing the primitive. `experiment_loop` might mean ZTARE in
a research lab, A/B testing in a startup, reconciliation testing in fintech,
or supplier-quality audits in operations. The route remains the same; the
backend changes.

**Kernel boundary:** Work Routing is mechanism, not policy. The kernel may
know that a task is `artifact_build`; it should not need to know whether the
artifact is a ZTARE substrate, a travel itinerary template, a fintech risk
control, or an enterprise onboarding checklist. Domain words belong in
adapters and mandates, not in the generic route enum.

---

## The Relationship Between the Two Instantiation Docs

```
Epistemic Verification               Cognitive Firm
         │                                     │
         ▼                                     ▼
Constrained Validation Loop          Organizational Primitives (9)
(in-loop proposal discipline)            (governance of the agents)
         │                                     │
    ┌────┴────┐                       ┌────────┼────────┐
    │         │                       │        │        │
Semantic   Deterministic            Damage  Session   M-Form
 Router    Sidecar                 Signals  Claims   Audit
              │                        │        │        │
    │         │                     Closure  Closure   OKR
Residual   Contam-                   Map    Pressure  Tree
Diagnostics ination                             │
           Gate
                                           Research
                                           Direction
                                               │
                                          Persistent
                                            Agent
                                           Channel
                                               │
                                             Work
                                            Routing
```

The constrained validation loop answers: **how does a single LLM operate within the verification pipeline?** It uses typed inputs, deterministic checks, residual diagnostics, and gates.

The organizational primitives answer: **how do multiple agents coordinate without dissolving the governance layer?** (Through damage signals, membrane exclusion, stochastic audits, closure analysis, exogenous clocks, world-measured objectives, role-bound research direction, persistent-agent channels, and generic work routing.)

Both are operational instantiations of theoretical claims. Both are domain-general. Both ship as runnable code in this repo.

### Adjacent reflexive allocation layer

Forecast markets and action intelligence are deliberately adjacent to the
organizational primitives, not replacements for them. The org primitives
answer who may act, how work is routed, where claims/gates live, and how
coordination is audited. The reflexive allocation layer asks whether a proposed
action was predicted, chosen, executed, observed, and learned from. In ZTARE
that layer is implemented through the forecast pool, prediction ledger,
[GP-243](../../research_areas/seams/protocol/GP-243_action_intelligence_loop_seam.md) action-impact records, and [GP-244](../../research_areas/seams/apparatus/instrumentation/GP-244_research_operations_intelligence_cockpit_seam.md) research-operations intelligence
surface.

This boundary matters. A market price or action-impact score can route
attention, ask for another independent agent, split a contract, defer a branch,
or kill a weak line. It does not grant authority by itself. Authority still
comes from roles, mandates, claims, gates, and budgets.

---

## Where This Does NOT Belong

- **Not Cognitive Firm itself.** *Cognitive Firm* is the theory; this doc is the implementation. A sentence here should not be cited as "*Cognitive Firm* says X", it should be cited as "the implementation of *Cognitive Firm*'s M-form in this repo does X."
- **Not the reflexive engineering doc.** The reflexive primitives (`docs/concepts/reflexive_engineering.md`) are about the engine improving its OWN infrastructure. The organizational primitives are about agents coordinating with EACH OTHER. Different problem, different solution, same philosophical roots.
- **Not AGENTS.md.** AGENTS.md is the standing rules; this doc explains WHY those rules exist and WHAT code enforces them.

---

*Created: 2026-04-26. Update whenever a new organizational primitive ships or *Cognitive Firm* adds a theoretical claim that needs an implementation companion. Last revised 2026-05-20: clarified the cognitive-firm kernel boundary, kept `org/` as the ZTARE tenant overlay, and separated authority primitives from the adjacent forecast/action-intelligence allocation layer.*
