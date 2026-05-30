# GP-167 — Multi-Agent Interface Form Factor

> **Seam metadata** · `seam_id:` GP-167 · `track:` mission · `status:` active - Orbit chosen; backend/channel hardening in progress · `last_updated:` 2026-05-17


**Status:** active — Orbit chosen; backend/channel hardening in progress
**Parent:** GP-128 (persistent manager agent), GP-166 (self-enacted compliance)
**Cross-refs:** GP-129 (biological org design), Paper 4 (The Cognitive Firm)

## Eigenquestion

What is the right UI form factor for a system where multiple humans and multiple AI agents collaborate with typed roles, mandates, and governance primitives?

## Panel (7 seats, 2026-04-26)

### Don Norman (cognitive science)
Exception-based dashboard with forced-function gates. Humans are terrible at monitoring (vigilance decays in 20 min). Role-centric view ("what does each agent need from me?"), not task-centric Kanban. **Failure: alarm fatigue** — if damage signals aren't triaged by severity, humans mute the system within a week.

### Bret Victor (interactive computing)
Spatial canvas (Figma/Miro), not chat. Each agent is a persistent tile showing mandate, current task, pending gates. Relationships as edges. Directly manipulable — drag to reassign, click to approve. **Failure: ghost town** — spatial canvases need active curation or degrade into junk drawers.

### Stewart Brand (pace layering)
Three-pane layout: slow (governance config, weekly), working (tasks, hourly), fast (damage signals, seconds). Don't mix cadences in one feed. **Failure: layer bleed** — if mandate changes are as easy as task approvals, you get accidental constitutional amendments.

### Robin Dunbar (social psychology)
Humans track ~5 entities' intentions simultaneously. With 10 agents, need squad clustering (2-3 groups with squad-level summary). Trust ledger showing cumulative accuracy per agent. **Failure: diffusion of responsibility** — everyone assumes someone else is watching.

### Edward Tufte (information design)
Small multiples. Sparkline + mandate indicator + pending-gate count per agent. Ten fit in one row. Tufte table lens for approval queue. Data-ink ratio > 0.8. **Failure: dashboard of dashboards** — adding panels until you've recreated a cockpit.

### Jaron Lanier (tech criticism)
Telegram is a Skinner box for governance. Approval must require context-loading friction — see reasoning + mandate + history BEFORE approve button is enabled. **Failure: frictionless abdication** — too-easy approval automates the human out while keeping them nominally in charge.

### Aza Raskin (attention/humane tech)
Attention budgeting: N interrupts per day, chosen by severity. Interface shows its own attention cost ("14 min on governance today"). Penalty for false escalation in trust ledger. **Failure: attention arms race** — agents inflate severity to get faster responses.

## Synthesis (Munger)

**Inversion:** Slack channel per agent + chat approval + phone notifications for every gate = alarm fatigue + diffusion of responsibility + reflexive approval within 2 weeks.

**Lollapalooza:** Lanier friction + Raskin attention budget + Dunbar squad clustering → **batch-gate review sessions**. Aggregate pending gates into a structured 10-min review block, grouped by squad, sorted by severity, with mandatory context loading.

**Ignored:** Migration path. The file layer (`org/`) must persist as system of record. Interface is a PROJECTION, not a replacement.

## Ranked Recommendations

| Rank | Form Factor | When | Tradeoff |
|------|------------|------|----------|
| 1 | **Spatial canvas web app + file backend** | Target (v2) | High build cost; needs curation |
| 2 | **Structured CLI + TUI dashboard** | Now (v1) | Low cost; caps at ~1 operator |
| 3 | **Telegram with gated friction** | Now (phase 1) | Fast; Skinner box risk even with friction |
| 4 | **Streamlit** | Retire | No spatial reasoning, principal dislikes it |

**Architecture invariant:** `org/` files are the system of record. Any interface is a projection. Git history is the audit trail. The interface can be replaced without losing governance state.

## Next Action

1. Ship Telegram (phase 1) — already built, just needs creds
2. Build TUI dashboard (v1) — `rich`-based terminal dashboard with sparklines + `fzf` gate approval
3. Design spatial canvas (v2) — web app, Figma-like tiles, three-pane pace-layer layout, batch-gate review

## Debate Log

### Turn 1 (Panel, 2026-04-26)
7-seat panel. Key convergence: batch-gate review > interrupt-driven approval. Key divergence: Victor wants spatial canvas (high build cost), Norman wants exception-only (minimal interface). Brand's pace-layering resolves the tension: different interface complexity for different cadences.

### Turn 2 (Enterprise Panel Resubmission, 2026-04-26)

8-seat panel: Chandler, Horowitz, Vogels, Kim Scott, Gene Kim, Whittaker, James C. Scott, Christensen.

**Key convergences the first panel missed:**

1. **liable_human field on every mandate** (Horowitz) — no mandate without a named individual. SOC-2 story, GDPR story, board story. GPG-signed commits for legally defensible audit trail.

2. **Two-tier mandate enforcement** (Vogels) — Tier 1: agent-local pre-action check (<10ms, synchronous). Tier 2: 5% stochastic audit (asynchronous). Eventual consistency for governance. Never centralize.

3. **Forced-ranking replaces binary approval** (Kim Scott) — "which of these 5 is best/worst?" not "approve/reject." Humans are dramatically better at comparative judgment. >90% approval rate auto-escalates to skip-level review.

4. **Mandates are deployments** (Gene Kim) — PR-based, `make mandate-lint`, `make mandate-test` against last 100 actions, 10% canary rollout, `git revert` rollback.

5. **Sanctioned opacity zones** (James C. Scott) — `scratch/` directories excluded from governance. Creative metis preservation. Track scratch-to-promoted ratio (floor 15%).

6. **Data minimization by design** (Whittaker) — 90-day retention, team-level aggregation, architecturally forbid human-ranking dashboards. Governance ≠ surveillance.

7. **Start with 3-person teams, not Fortune 500** (Christensen) — minimum viable governance = one mandates/ dir + GitHub Issues as damage signals + branch protection as session claims. Scales to 500 by adding directories, not layers.

**Lollapalooza (compound failure):** Legibility trap (Scott) × approval theater (Kim Scott) = agents produce mandate-shaped outputs that humans rubber-stamp. Every metric green, nothing useful happening. Defense: forced-ranking + scratch-to-promoted ratio.

**Migration path:** Phase 0 (file primitives, 1-3 teams) → Phase 1 (multi-division, make mandate-lint) → Phase 2 (spatial canvas on TLDraw+Yjs+git) → Phase 3 (enterprise: GPG, SSO, retention).

**Form factor:** TLDraw spatial canvas backed by git-synced org/ directory. ~3K lines TypeScript. CLI as co-equal projection. Telegram demoted to read-only pager.

**Pricing:** Open-core. MIT for file formats + CLI + single-division. Commercial $500/division/month for multi-division canvas + audit. Enterprise $50-200K/year. Per-division pricing, not per-seat.

### Turn 3 (Comprehensive Panel — 12 experts + alien AI, 2026-04-26)

12-seat panel: Mintzberg, Eisenhardt, Shannon, Suchman, Milner, Lamport, Nardi, Dourish, Fowler, Hohpe, Alien 2031, Alien 2040.

**The death spiral (lollapalooza):** Silence-as-consent + context bankruptcy + mandate fossilization create a reinforcing collapse. Humans engage less → agents self-authorize more → mandates drift → output becomes irrelevant → humans engage even less. All three are already latent in this design.

**Three things that must change:**

1. **Silence-as-consent must become explicit** (Suchman) — every non-response needs timeout classification: "approved by inaction (logged)" vs "did not see (re-escalate)." Build attention-aware governance.

2. **Context must survive session boundaries** (Dourish) — epistemic residue (what was tried, what failed, what was learned) must be a structured persistent artifact. Not just git diffs. The Groundhog Day failure: new sessions re-explore dead ends because the search map is not persisted.

3. **Human preference model must become a first-class object** (Alien 2040) — versioned, correctable, machine-readable. The agent should know what you want without you saying it every time. This is the missing half of bidirectional legibility: agent is legible to human (dashboard), but human is NOT legible to agent (agent infers intent from sparse signals).

**Three things that will persist:**
1. File-based system of record under version control
2. Damage signals as organizational pain receptors
3. Session claims / membrane exclusion

**On git:** Yes for audit, no for coordination. Keep as append-only event store. Add: message-routing layer for real-time A↔A, Lamport timestamps for causal ordering, structured intent metadata per commit.

**Key new concepts:**
- **Liaison role artifact** (Mintzberg) — YAML declaring which roles must synchronize before acting
- **Mandate staleness trigger** (Eisenhardt) — auto-escalate when damage signals accumulate faster than mandate cycle
- **Intent vector** (Shannon) — structured field per commit declaring what was intended, not just what changed
- **Return-to-work summary** (Nardi) — on-demand 30-second briefing: what happened, what needs me, what is blocked
- **Scoped agent-to-agent channels** (Milner) — typed channel with declared lifetime, visible in audit log
- **Saga coordinator** (Fowler) — define transaction boundaries across agents with compensating actions
- **Content-based damage signal routing** (Hohpe) — route to the agent whose mandate covers the domain
- **Role dissolution preparation** (Alien 2031) — build so roles can split/merge/reassign dynamically
- **Bidirectional legibility** (Alien 2040) — human preference model as versioned artifact alongside agent mandates

### Turn 4 (Novel Form Factor Panel — 6 unconventional thinkers, 2026-04-27)

6-seat panel: Bret Victor, Hiroshi Ishii (MIT Tangible Media), Aza Raskin, Andy Matuschak, Alien AI 2035, a 10-year-old child.

**THE ANSWER: Orbit.**

A governance interface where you don't manage agents — you set gravity. They orbit. You intervene only when something escapes.

**Five components:**

1. **Zoomable spatial canvas** (Victor) — agents as living glyphs with expressive faces (Child). Zoom out: constellation of dots, color = health. Zoom in: unfolds into state, pending decisions, trajectory. Same on phone (pinch) and laptop (scroll).

2. **Silent by default** (Alien 2035) — canvas is calm. Surfaces nothing unless a boundary is crossed or a decision is required. Humans govern by BOUNDARY (invariants), not by INSTRUCTION (directives). The interface shows boundary violations and pending contracts, not activity.

3. **Digest, not feed** (Raskin) — 3x daily, one screen, decisions as swipeable binary cards sorted by consequence. Target: 12 minutes. Time-on-interface visible. Depth requires explicit expansion. Anti-Skinner-box: actively resists engagement.

4. **Spaced-repetition governance** (Matuschak) — approvals resurface days later: "You approved X. Here's what happened. Still correct?" Audit trail + judgment quality mechanism. Sorted by epistemic urgency, not chronology.

5. **Ambient physical companion** (Ishii) — small device, one indicator per agent, color + pulse = state. Glance-readable from across the room. Tap → opens agent's card on phone. Interrupt channel (physical) vs deliberation channel (screen).

**Data flow:** Agents emit structured state events into append-only log. Orbit reads the log, computes canvas layout, generates digest cards, schedules repetition follow-ups, drives ambient device. Human decisions write back into same log. Fully auditable. No chat — governance events only.

**Technology:** Event log (SQLite or NATS JetStream on VPS). Canvas (WebGL, responsive web app). Digest compiler (server-side cron). Ambient device (ESP32 + RGB LED + BLE). Spaced-repetition (Leitner algorithm on decision log).

**The child's insight is decisive:** "I'd want each robot to have a face. Happy means doing good. Confused means needs help. Scared means something wrong. Tap the face, one sentence, yes or no." This IS the UX specification. Everything else is engineering to make it scale.

### Turn 5 (Dogfood backend audit — 2026-04-30 15:50:00)

North-star question: can this repo run as a 24x7 ZTARE research company, where
the principal intervenes only at key decision points, while Manager / Research
Director / workers operate continuously inside mandates?

Clarification: the settled architecture is **not** "git as the live backend."
The live backend is the canonical filesystem/event-log state:

- `org/` for roles, mandates, preferences, tasks, objectives, KRs, sessions,
  controls, directives, and damage signals.
- `ztare_workspace/gates/pending/` as the single executive inbox.
- `ztare_workspace/gates/resolved/` for resolved decisions.
- `ztare_workspace/transitions.jsonl` as the append-only state-transition log.
- git as audit/versioning/rollback/sync, not the low-latency coordination
  primitive.

Orbit and Telegram are projections over that backend. They must not invent
parallel inboxes.

Panel findings from re-audit:

1. Orbit had an inbox-looking UI, but resolution was console-only and the
   backend wrote to `org/gates/resolved/` instead of the canonical
   `ztare_workspace/gates/resolved/`.
2. The daemon had direct Telegram approval/control paths, which risked a
   split-brain approval channel.
3. The agreed GP-167 "silent by default" property was not yet enforced:
   pending gates did not make orbs visibly need human intervention.
4. The daemon could discover and execute but had not yet been strict enough
   about unattended authorization, task lifecycle closure, and audit duration.

Patch direction taken in this session:

- Orbit gate resolution now targets canonical `ztare_workspace/gates/*` paths
  and appends `gate.resolved` to `ztare_workspace/transitions.jsonl`.
- Orbit watches both `org/` and `ztare_workspace/gates/pending/`.
- Pending gates now affect Orbit status and orb `needsHuman` state.
- Daemon unattended mode is explicit (`--unattended` / `ZTARE_UNATTENDED=1`),
  not the accidental fallback when Telegram is missing.
- Daemon filters Telegram commands to authorized messages only.
- Daemon claims and closes principal tasks when executing them, records real
  duration, and refuses principal tasks with `autonomous_scope_ok=false`.

Remaining dogfood blockers before 24x7 unattended production:

- full pre-dispatch `TaskAuthorizationGate` against role scope, budget, and
  referenced paths
- constrained execution sandbox/worktree matching the role's allowed paths
- atomic task claim / stale-claim recovery / session close discipline
- authentication on Orbit mutation endpoints before exposing outside localhost
- one approval path: task proposal -> gate -> resolved gate -> execution

### Turn 6 (Alien/org-design/product panel — 2026-04-30 15:58:00)

Prompt correction: do not anchor on OpenClaw as the target. OpenClaw is a
simplicity baseline (`agent + tools + task trigger`), not the product category
ZTARE is trying to occupy.

Panel composition requested: Alien organization designer 2040, Alien
distributed-systems engineer 2040, AI agent representative, Chandler, Ostrom,
Stafford Beer, Herbert Simon, Gene Kim, Lamport, enterprise CISO.

Synthesis:

1. ZTARE's unique primitive is not "agents doing tasks." It is an executable
   governance kernel for a research organization: principal intent + role
   mandate + authorization + executive gate + constrained execution + evidence
   ledger + closure discipline + audit trail.
2. The local dogfood backend may remain filesystem/event-log, but enterprise
   deployments require an Org Runtime Control Plane: Postgres for current state
   and leases, durable event outbox, RBAC/SSO, signed decisions, retention, and
   filesystem/git exporters.
3. Git remains audit/versioning/rollback/reproducibility. It must not be used
   for task locking, queueing, live authorization, or multi-server coordination.
4. The invariant is: **one executive inbox, one transition log, many
   projections**. Orbit is rich projection; Telegram is pager; CLI is simple
   projection; daemons/workers are actors.
5. The AI-agent-representative critique is decisive: agents need explicit
   refusal channels, ambiguity escalation, bounded work sessions, and protection
   from impossible/conflicting instructions. "Agent rights" here means protocol
   integrity, not moral personhood.

Human interaction contract:

- The principal should not run Python commands as the product interface.
- Commands are bootstrap/devops/debug surfaces only.
- Daily interaction should be natural-language governance cards:
  "Here is the decision. Here is why it matters. Here are trade-offs. Here is
  the recommended option. Approve / Skip / Ask more / Stop."
- Approval cards must include: requesting role, task/claim, why now, expected
  cost/time/risk, touched files/systems, approve consequence, skip consequence,
  reversibility, and expected evidence/artifact.

Implementation changes made during this turn:

- Added `docs/concepts/ztare_research_company_architecture.md` as the durable
  north-star doc.
- Made `org/preferences/principal.yaml` the generic preference profile and
  removed `daniel_alami` references from org/runtime docs.
- Added `docs/guides/org_runtime_quickstart.md` and Research Director task
  template.
- Patched `scripts/public/control/agent_daemon.py` for explicit unattended mode, authorized
  Telegram messages only, principal-task claim/closure, real duration logging,
  and refusal of `autonomous_scope_ok=false`.
- Patched `src/ztare/orchestration/goals_inbox.py` and
  `scripts/public/control/org_role_preflight.py` to avoid hard PyYAML dependence in product
  smoke paths.
- Patched Orbit (`orbit/src/server/git-sync.ts`, `orbit/src/App.tsx`) so gate
  resolution targets canonical `ztare_workspace/gates/*`, appends transition
  events, watches canonical gate paths, indicates pending decisions, and binds
  localhost by default with optional `ORBIT_API_TOKEN`.
- Added local primitives:
  `src/ztare/orchestration/transition_log.py` and
  `src/ztare/orchestration/task_authorization.py`.

Verification performed:

- `python3 -m py_compile scripts/public/control/agent_daemon.py src/ztare/orchestration/goals_inbox.py scripts/public/control/org_role_preflight.py`
- `python3 scripts/public/control/agent_daemon.py --role research_director --tick-once --dry-run`
- `cd orbit && npm run build`

### Turn 7 (Enterprise-grade belief contract — 2026-04-30 16:05:00)

Do not call this enterprise-grade merely because the local dogfood loop works.
To honestly claim "enterprise-grade ZTARE research company," we would need to
believe all of the following, with evidence:

1. **Single authority path holds under concurrency.** Every action flows through
   task/directive -> authorization -> gate if required -> lease/claim ->
   execution -> event log -> closure. No side channel (Telegram, Orbit, CLI,
   daemon prompt, direct file edit) can approve or execute outside that path.

2. **Authorization is structural, not prompt-based.** Role mandates are compiled
   into enforceable path, budget, secret, network, and tool constraints. The
   agent cannot write outside scope even if it tries.

3. **Claims are transactional leases.** Multiple servers/daemons cannot double
   execute the same task. Claims have idempotency keys, heartbeats, stale
   recovery, and compensating actions.

4. **The event log is canonical and complete.** Daemon, Orbit, Telegram,
   closure daemon, workers, and supervisors all emit the same transition schema
   with actor, role, surface, causality id, authorization decision, prior/new
   version, and artifact pointers.

5. **Human approvals are informed but low-friction.** Approval cards surface the
   right context/trade-offs without turning the principal into a sysadmin. The
   product interaction is natural language and decision cards, not Python
   commands.

6. **Silent-by-default survives real use.** The interface interrupts only for
   boundary crossings or consequential decisions. It does not become a feed that
   trains the principal into reflexive approval.

7. **Agent refusal and ambiguity escalation are first-class.** Agents can
   refuse impossible/conflicting mandates, ask for scope clarification, and
   record why work was blocked. This is protocol integrity, not moral rhetoric.

8. **Enterprise controls exist before external deployment.** SSO/RBAC, safe
   bind defaults, signed decisions, secret isolation, retention policy, audit
   export, tenant/division namespace, and least-privilege service identities are
   implemented and tested.

9. **Git is not overloaded.** Git is audit/versioning/rollback. It is not the
   live queue, lease manager, or authorization coordinator in multi-server
   deployments.

10. **Failure modes are rehearsed.** We have simulations for daemon crash
    mid-task, duplicate daemon startup, stale claim, unauthorized Telegram
    message, Orbit auth failure, gate timeout, malformed task, budget overflow,
    and agent attempting forbidden writes.

Current status after today's patches: suitable for **local dogfood with
operator supervision**, not yet enterprise-grade. The code is moving toward the
belief contract but does not yet satisfy items 2, 3, 4, 8, or 10 at enterprise
strength.

### Turn 8 (Persistent-agent ontology + protocol panel — 2026-04-30 16:06:47)

Prompt: distinguish persistent agents like Codex / Claude Code from transient
LLM calls inside ZTARE, cold-shot, judge, mutator, and script generation. Decide
whether communication should be MCP, another protocol, or a new primitive.

Panel:

1. **Distributed-systems engineer:** Do not use chat history as the bus. Use a
   typed envelope with idempotency, status, causality, sender/receiver, and
   artifact pointers.
2. **MCP maintainer perspective:** MCP is a tool/context/resource protocol. It
   is useful for exposing the org runtime to LLM hosts, but it is not the whole
   A2A coordination layer.
3. **A2A/ACP interoperability perspective:** Reuse agent cards / tasks /
   messages / artifacts / status ideas, but do not import the full remote-agent
   protocol before the local governance semantics are correct.
4. **FIPA/ACL perspective:** The old performative idea remains decisive:
   every message needs a communicative act (`inform`, `request`, `proposal`,
   `handoff`, `clarification`, `refusal`, `status`) so the receiver knows what
   kind of obligation it creates.
5. **AI agent representative:** Persistent role offices need refusal,
   ambiguity, and handoff channels. Transient model calls should not inherit
   authority merely because their prose sounds agentic.
6. **Enterprise CISO:** No side-channel authority. Agent-to-agent messages can
   request or hand off work, but execution must still route through
   authorization, gates if required, claims, runner constraints, and transition
   logs.

Decision:

- Treat **persistent role offices** as accountable organizational actors:
  mandate, role, session, budget, claim rights, refusal rights, address, and
  audit trail.
- Treat **transient LLM invocations** as artifacts: judge output, mutation,
  cold-shot, critique, or script proposal. They have provenance but no standing
  authority.
- Implement a local typed persistent-agent channel now. Add MCP/A2A/ACP
  adapters later at the control-plane boundary.

Implementation shipped:

- Added `src/ztare/orchestration/agent_channels.py`.
- Added `scripts/public/control/agent_channel.py` as a dev/debug projection.
- Added `org/channels/<role>/inbox/*.json` and `sent/*.json` as the local
  durable channel layout.
- Patched `src/ztare/orchestration/work_discovery.py` so open channel messages
  become role-daemon candidates.
- Added `agent.message.sent`, `agent.message.acknowledged`, and
  `agent.message.closed` events to the canonical transition log.
- Updated `docs/concepts/ztare_research_company_architecture.md`.
- Updated `docs/concepts/organizational_primitives.md` with new primitive #8:
  Persistent-Agent Channel.

Enterprise-grade condition added to Turn 7:

- We would need to believe that persistent-agent messages cannot authorize
  execution by themselves; they only create typed obligations. Execution remains
  impossible without the authority path:
  `authorization -> gate if needed -> lease/claim -> constrained runner ->
  transition log -> closure`.

Status:

- Local primitive implemented.
- Not yet enterprise-grade because it lacks RBAC-backed channel permissions,
  A2A/ACP adapters, retention policy, and Orbit rendering of channel inboxes.

### Turn 10 (Docker bootstrap / AGENTS.md contract — 2026-04-30 18:03:00)

Prompt: how do we make sure new Docker agents load correctly and read what
they need to do? What role does `AGENTS.md` play relative to role YAML,
mandates, A2A channels, and inboxes?

Decision:

- `AGENTS.md` is the repo-wide agent constitution. It is not a task queue and
  not a role mandate. It governs every agent that opens the repo: closure
  discipline, public/private split, experiment-recording rules,
  inversion/reflexive-discovery rules, CLI discipline, and collaboration
  norms.
- `org/roles/<role>.yaml` is the durable role contract: identity, budget,
  path scope, delegation, escalation, and mandate path.
- `org/mandates/<role>_mandate.md` is role-specific authority and standing
  context.
- `org/preferences/principal.yaml` is the principal preference/taste model.
- If these conflict, the stricter constraint wins and the agent escalates.

Implementation:

- `scripts/public/control/org_role_preflight.py` now checks `AGENTS.md`, the org-runtime
  quickstart, and the Research Director task template in addition to role,
  mandate, preferences, dependencies, and configured agent runtime.
- `scripts/public/control/agent_daemon.py` now explicitly tells spawned agents to read
  `AGENTS.md`, role YAML, mandate, quickstart, and preferences before acting.
- The daemon now records runtime identity via `--member-id` /
  `ZTARE_MEMBER_ID` and execution runtime via `--agent-cli` /
  `ZTARE_AGENT_CLI`, instead of hardcoding `member_id=claude`.
- `scripts/public/control/org_runtime_smoke.py` gives the Docker/product path a single local
  smoke command: preflight plus daemon dry-run, no mutation.
- `docs/guides/org_runtime_quickstart.md`, `org/README.md`, and
  `docs/concepts/ztare_research_company_architecture.md` now document the
  bootstrap contract.
- The A2A closure path was regression-tested: daemon-completed
  `agent-channel` candidates now close the underlying message.
- Gate resolution was tightened: validated gate IDs, idempotent
  already-resolved handling, atomic resolved writes, and pending-gate
  `.handled` marking.

Inbox semantics clarified:

- `ztare_workspace/gates/pending/` is the executive decision inbox.
- `org/channels/<role>/inbox/` is the role-to-role obligation inbox.
- `org/tasks/pending/` is the assignable work inbox.
- None of these should collapse into chat. They have different authority
  semantics.

Remaining productization debt:

- more runtime adapters beyond the shipped `claude_print` and `codex_exec`
  noninteractive paths;
- constrained runner/worktree with role-specific mounts;
- stronger gate idempotency across multi-process/multi-server deployments;
- A2A/ACP adapters at the control-plane boundary;
- MCP server exposing org-runtime resources/tools without making MCP the
  authority layer.

Verification:

- `python3 scripts/public/control/org_role_preflight.py --role manager --agent-cli claude --json`
- `python3 scripts/public/control/org_role_preflight.py --role research_director --agent-cli claude --json`
- `python3 scripts/public/control/agent_daemon.py --role research_director --member-id codex --agent-cli codex --agent-adapter codex_exec --tick-once --dry-run`
- `python3 scripts/public/control/org_runtime_smoke.py --role research_director --member-id codex --agent-cli codex --agent-adapter codex_exec`
- `venv/bin/pytest tests/test_a2a_projection.py tests/test_agent_channels.py tests/test_work_discovery.py tests/test_goals_inbox.py` (`22 passed`)
- `npm --prefix orbit run build`

### Turn 9 (Accountability philosophy panel — 2026-04-30 16:11:28)

Prompt: can accountability be pushed to agents, or does it always remain at
the human level? What is the correct accountability architecture for a
role-based AI research organization?

Panel:

1. **Kantian/deontic philosopher:** Moral responsibility requires agency,
   reasons, and standing in a community of obligation. Current agents can be
   assigned duties inside a protocol, but ultimate moral accountability cannot
   be offloaded to them.
2. **Legal philosopher:** Enterprise accountability stays with the deploying
   human/entity. A model cannot hold fiduciary duties, sign enforceable risk
   acceptance, or absorb liability.
3. **Cybernetician:** Accountability is control-loop structure. If an agent has
   no authority, blaming it is theater. If it has authority but no audit, the
   system is ungovernable.
4. **Operations executive:** Push operational accountability downward:
   role offices should be accountable for mandate compliance, closure
   discipline, escalation, and evidence hygiene.
5. **AI agent representative:** Protocol accountability matters. Agents need
   refusal, ambiguity, handoff, and impossible-instruction channels; otherwise
   "accountability" becomes a way to punish outputs from contradictory inputs.
6. **Munger synthesis:** Invert both bad answers. If all accountability remains
   with the human while agents act invisibly, the system becomes a black box.
   If accountability is pushed fully to agents, it becomes legal/moral theater.
   The workable split is layered accountability.

Synthesis:

- **Ultimate accountability** remains with the human principal or deploying
  organization: budgets, public claims, external commitments, release
  decisions, publication risk, and value judgments.
- **Operational accountability** is pushed to persistent role offices: did the
  role follow its mandate, authorization gate, claim/lease protocol, escalation
  rules, refusal duties, and closure discipline?
- **Causal accountability** belongs to the transition log and artifacts: what
  happened, what licensed it, what files/systems were touched, what evidence
  resulted, and what changed afterward?
- **Model-call attribution** belongs to transient invocations: prompt, model,
  inputs, output, score, critique, mutation. It is provenance, not authority.

Rule:

```text
No accountability without authority.
No authority without mandate.
No mandate without audit.
No audit without durable artifacts.
```

Implementation implication:

- Approval cards must say what accountability the principal is accepting.
- Persistent-agent messages create typed obligations, not execution authority.
- Role-daemon execution records need actor, role, mandate version,
  authorization decision, causality id, touched artifacts, and closure outcome.
- Transient LLM calls must be stored as evidence/proposals, never as hidden
  decision makers.

Patch:

- Updated `docs/concepts/ztare_research_company_architecture.md` with the
  layered accountability model.

### Turn 10 (A2A projection and product smoke hardening — 2026-04-30 18:17:03)

Prompt: make the virtual-org runtime openclaw-like/easy while preserving the
local authority model; clarify how Codex/Claude-style persistent agents differ
from transient LLM workers; do not let A2A/MCP become the authority layer.

Decision:

- Keep the repo-local org runtime canonical. A2A/ACP cards are projections for
  discoverability and future interoperability, not a second source of truth.
- Persistent agents are role-office occupants: they bind to `AGENTS.md`, role
  YAML, mandate, preferences, inbox, claims, transition log, and closure rules.
- Transient LLM calls remain fungible workers/oracles: useful for mutation,
  review, cold shots, and scripts, but they do not own authority unless wrapped
  by a role office.
- MCP remains a tool/context surface. It can expose resources and commands, but
  it must not bypass gates, claims, or role mandates.

Implementation:

- Added `src/ztare/orchestration/a2a_projection.py` and
  `scripts/public/control/export_a2a_agent_cards.py` to export local role YAMLs as
  A2A-style agent cards under `ztare_workspace/a2a/agent_cards/`.
- Added `scripts/public/control/org_inbox_status.py` to show the three distinct inboxes:
  executive gates, assignable tasks, and role-to-role obligations.
- Hardened the no-PyYAML fallback parser so minimal/Docker environments export
  real block-scalar descriptions and sane null mandate fields.
- Added `tests/test_a2a_projection.py` to pin the local projection contract.

Verification:

- `python3 -m py_compile src/ztare/orchestration/a2a_projection.py scripts/public/control/export_a2a_agent_cards.py scripts/public/control/org_inbox_status.py scripts/public/control/org_runtime_smoke.py scripts/public/control/agent_daemon.py scripts/public/control/org_role_preflight.py`
- `venv/bin/pytest tests/test_a2a_projection.py tests/test_agent_channels.py tests/test_work_discovery.py tests/test_goals_inbox.py` (`22 passed`)
- `python3 scripts/public/control/org_runtime_smoke.py --role research_director --member-id codex --agent-cli codex --agent-adapter codex_exec`
- `python3 scripts/public/control/export_a2a_agent_cards.py`
- `python3 scripts/public/control/org_inbox_status.py`
- `npm --prefix orbit run build`

## 2026-05-17 — Unified inbound-message channel + NL routing (folded here, NOT a new seam)

**Built:** `src/ztare/messaging/inbound.py` — one abstract `MessageInbox`
over a `MessageSource` ABC: `InteractiveSource` (watched local inbox
dir — the tmux / "type to it" path + the headless poll-an-inbox
hybrid; fully live + tested), `TelegramSource`, `OrbitSource` (JSONL
spool consumers; dedupe by stable id; time-ordered; never raise into
the agent loop; INPUT-ONLY — enforcement is the GP-241 membrane's job).
Realizes the GP-241 thesis: once input is uniform and enforcement is
the membrane, headless / tmux / conversational are the SAME to the
agent.

**Spool contract the backends must implement (remaining wiring):**
`orbit/src/server/telegram-bot.ts` + the orbit server must write each
received free-text message as one JSON line `{ts, sender, text}` to
`$ZTARE_INBOUND_ROOT/telegram/nl_spool.jsonl` resp.
`.../orbit/nl_spool.jsonl`. Today the TS bot only routes
STOP/PAUSE/STATUS — the NL spool write is a contained side-effect-free
append (does NOT change the existing control path). Until then
InteractiveSource is end-to-end; telegram/orbit degrade-empty.

**NL routing requirement (operator 2026-05-17) + PREREQUISITE GAP:**
route an NL message to the *relevant* agent when >1 is active. HONEST
FINDING: there is no active-agent registry to route against —
prerequisite design item, not a quick wire. Minimal model: an
`active_agents` view (owner-id + role + last-heartbeat + current-tick)
the bot reads; routing = explicit `@owner:` prefix → that inbox; else
exactly-one-active → it; else bot asks which (no silent mis-delivery).
TS bot is live VPS infra ⇒ focused reviewed pass, NOT a tail cram.
Tracked here; do NOT spin a new seam.

### Turn 11 (human work is not just decision gating — 2026-05-19)

Prompt: check whether the kernel handles humans doing actual work alongside
agents, not only approving gates; keep ZTARE seams/specs as provenance while
the shared kernel carries stable public primitives.

Decision:

- Keep A2A as the role-to-role obligation channel. A2A messages create typed
  obligations; they do not become execution authority.
- Keep H2A as the human interaction channel. H2A includes decision gates, but
  also bounded human work sessions for access, taste, judgment, relationship
  work, external actions, and non-digitized work.
- Link the two by `obligation_id`: the A2A obligation says which role is
  waiting; the H2A human-work session says what human-side work is carrying
  the missing piece; `agent_followup_required` says whether a role office must
  consume the result before closing the obligation.
- Do not add a new "interaction ledger" primitive yet. The shared kernel's
  human-work `interaction_events` field already captures structured events
  without pretending private/offline work is fully observable. The required
  improvement was queryability by obligation/follow-up/surface.

Implementation in `cognitive-firm`:

- Extended `cognitive_firm.orchestration.human_work.list_human_work_sessions`
  and its CLI with filters for `obligation_id`, `agent_followup_required`, and
  `interaction_surface`.
- Added a regression test that creates an A2A request, records a linked
  human-work session, and queries it through the new filters.
- Updated public `docs/protocols/h2a.md` and `docs/protocols/a2a.md` to state
  the bridge.

Verification:

- `PYTHONPATH=src ./.venv/bin/python -m pytest tests/test_human_work.py tests/test_obligation_lifecycle.py`
