# ZTARE Research Company Architecture

**Status:** north-star reference architecture for a 24×7 virtual research org.
**Last revised:** 2026-05-01 00:03:00

---

## Product Test

The validation test is simple:

```text
Can a principal define preferences, objectives, mandates, and budget once,
then let persistent AI roles work 24x7 on current problems while the principal
intervenes only at key decision points?
```

If not, the governance kernel is not ready for external organizations.

---

## Easy Boot Surface, Hard Control Plane

Simple agent frameworks optimize for:

```text
install -> connect model -> connect tools -> chat/trigger -> agent acts
```

ZTARE should preserve that surface:

```text
write task -> start role daemon -> approve/skip or run unattended -> inspect artifacts
```

The difference is the control plane. A research company cannot treat chat as
state. It needs mandates, claims, gates, budgets, damage signals, and experiment
closure.

The goal is not to imitate consumer automation. The goal is to productize a
new organizational primitive: **self-governing research execution under
falsification discipline**. The easy surface matters because adoption matters,
but the core asset is the governance kernel: a role-bound system that decides
what can act, when evidence licenses promotion, when a claim must be blocked,
and when the principal must intervene.

There are two easy surfaces, not one:

| Surface | Command | Use case |
|---|---|---|
| Operator console | `scripts/operator_console.sh claude` | Principal-operated interactive Claude/Codex session. No daemon, no work discovery, no validator loop. |
| Role daemon | `docker compose --profile daemons up research-director-daemon` | Persistent role-bound background work with gates, claims, transition logs, and closure. |

This split is intentional. The product should not force a principal to boot the
whole governance machine just to talk to a Claude Code instance. Direct
collaboration remains a first-class Mode A path; the governance layer starts
when work needs persistence, delegation, or unattended execution.

---

## Backend Decision

Do not conflate backend, audit, and interface.

| Layer | Role |
|---|---|
| `org/` | Canonical organizational state: roles, mandates, preferences, tasks, objectives, key results, sessions, directives, controls, damage signals. |
| `ztare_workspace/gates/` | Canonical executive inbox: pending and resolved decisions. |
| `ztare_workspace/transitions.jsonl` | Append-only event log for state transitions. |
| `projects/` + `research_areas/` | Research artifacts, experiment ledgers, substrate workspaces, evidence. |
| Git | Audit, versioning, rollback, sync. Not the low-latency coordination backend. |
| Orbit | Primary governance UI projection over the backend. |
| Telegram / phone channel | Push/digest/ack channel, not the system of record. |

The backend is filesystem-first at solo/small-team scale because it is
inspectable, git-friendly, and easy to recover. At enterprise scale, the same
schema should sit behind an **Org Runtime Control Plane**: a Postgres-backed
API with leases, RBAC/SSO, idempotent gate resolution, signed audit records,
retention policy, and an event outbox.

---

## Multi-Server Shape

For many servers or divisions:

```text
tenant/
  org/
    roles/
    mandates/
    preferences/
    objectives/
    key_results/
    tasks/
    sessions/
    signals/
    directives/
    controls/
  ztare_workspace/
    gates/
      pending/
      resolved/
    transitions.jsonl
  projects/
  research_areas/
```

Runtime services:

- **Control plane API:** validates writes, resolves gates, emits events.
- **Transactional store:** Postgres for current state, leases, and gate
  resolution idempotency.
- **Event stream/outbox:** durable append-only `org.transition.*` events,
  optionally mirrored to Kafka/NATS/JetStream for real-time consumers.
- **Role daemon(s):** one process per role or role pool.
- **Worker runners:** constrained execution containers/worktrees.
- **Orbit:** browser UI for governance and executive inbox.
- **Push channel:** Telegram/Slack/email/Teams digest and urgent ack.
- **Git mirror:** commits state snapshots and artifacts for audit/rollback.

Each division gets its own namespace. Cross-division work happens through
explicit directives or gates, not shared mutable files.

---

## Authority Path

The enterprise-safe path is:

```text
task/objective/directive
-> pre-dispatch authorization gate
-> proposal gate if principal approval is required
-> resolved gate or unattended in-mandate pass
-> atomic task claim
-> constrained execution
-> append-only transition events
-> result/blocked closure
-> ledger/update or damage signal
```

Any implementation that bypasses this path is a prototype shortcut.

The invariant is:

```text
one executive inbox
one transition log
many projections
```

Orbit is the rich projection. Telegram is the constrained pager. CLI is the
low-friction path. Daemons are workers. None owns independent state.

---

## Bootstrap Contract

A role daemon is not safe merely because Docker starts. A correct boot must
prove the runtime can see the instruction stack:

| Layer | File | Function |
|---|---|---|
| Repo constitution | `AGENTS.md` | Rules every agent must obey: closure discipline, artifact visibility, inversion reflexes, experiment recording, CLI discipline. |
| Role contract | `org/roles/<role>.yaml` | Identity, path scope, budget, delegation, escalation, mandate path. |
| Role mandate | `org/mandates/<role>_mandate.md` | Operating authority and current standing context. |
| Principal preference model | `org/preferences/principal.yaml` | Taste and attention routing. |
| Task/objective state | `org/tasks/`, `org/objectives/`, `org/key_results/` | Work queue and closure pressure. |

The daemon prompt explicitly tells the spawned agent to read `AGENTS.md`,
the role YAML, the role mandate, and the principal preferences before acting.
`scripts/org_role_preflight.py` checks these documents before boot. This is
necessary because some agent hosts auto-load `AGENTS.md` when opened in a repo,
but a Dockerized subprocess may not. The product cannot rely on host-specific
autodiscovery for constitutional instructions.

---

## Persistent Agents vs Transient Invocations

ZTARE should distinguish two different computational objects:

| Object | Meaning | Authority | Durable state |
|---|---|---|---|
| Persistent role office | Codex, Claude Code, or another long-lived role-bearing agent acting as Manager, Research Director, Reviewer, Engineer, etc. | Can own tasks, claim leases, refuse scope, open gates, send handoffs, and write ledgers within mandate. | `org/roles/`, `org/mandates/`, `org/sessions/`, `org/channels/`, transitions, artifacts. |
| Transient model invocation | A one-off LLM call inside ZTARE, cold-shot, judge, mutator, or script-generated critique. | No standing authority. It is evidence, proposal, mutation, or review output consumed by a role office. | Captured only as an artifact with provenance, model, prompt, inputs, and output. |

This is an agentic primitive: **office, not model call, is the accountable
unit**. A role office may use many fungible LLM invocations. Those invocations
should not be treated as members of the organization unless they receive a
role, mandate, session, and communication address.

The practical reason is auditability. A cold-shot can suggest a decisive test;
it cannot authorize itself to run the test. A persistent Research Director can
accept, reject, or route that suggestion because the role office has a mandate,
budget cap, refusal channel, and transition log.

---

## Agent-To-Agent Communication

Current literature and protocol landscape:

- **MCP** is best understood as `agent/host -> tools/context/resources`.
  It standardizes JSON-RPC access to tools, prompts, resources, capability
  negotiation, and human-visible tool invocation controls. It is not by itself
  an org-level A2A coordination layer.
- **A2A** is closer to `agent -> agent`: agent cards, tasks, messages,
  artifacts, task status, streaming, push notifications, authentication, and
  task cancellation.
- **ACP/BeeAI** is also an agent-to-agent interoperability direction.
- **FIPA ACL** is the older conceptual ancestor: messages carry a communicative
  act/performative, sender, receiver, content, conversation context, ontology,
  and reply controls.

ZTARE should reuse the shape, not blindly import a full protocol. The local
primitive is a typed durable envelope:

```text
from_role -> to_role
kind: inform | request | proposal | handoff | clarification | refusal | status
subject/body
thread_id / causality_id
references / artifacts
expects_response
status: open | acknowledged | closed
```

Local implementation:

- `org/channels/<role>/inbox/*.json` is the persistent role inbox.
- `org/channels/<role>/sent/*.json` is the sender mirror.
- `src/ztare/orchestration/agent_channels.py` writes and reads typed
  messages.
- `scripts/agent_channel.py` is a dev/debug CLI projection.
- `src/ztare/orchestration/work_discovery.py` surfaces open role messages as
  daemon candidates.
- Every send/status mutation appends `agent.message.*` to
  `ztare_workspace/transitions.jsonl`.

Current inbox status:

- Gate inbox: `ztare_workspace/gates/pending/` is the executive decision
  inbox. Orbit and Telegram are projections over it.
- Agent inbox: `org/channels/<role>/inbox/` is the persistent role-office
  message inbox. It creates obligations, not execution authority.
- Task inbox: `org/tasks/pending/` contains assignable work. Work becomes
  executable only after authorization/gate/claim.

Do not collapse these into one chat feed. They have different semantics:
executive decision, role-to-role obligation, and work item.

Enterprise direction:

- Add A2A/ACP adapters at the control-plane boundary, not inside every agent.
- Expose role offices as A2A agent cards only after their mandates, budgets,
  and allowed actions are compiled into enforceable policy.
- Expose MCP servers for tools/resources used by roles, but keep authorization
  and communication state in the org runtime.
- Treat transient LLM calls as artifacts, not A2A agents, unless explicitly
  promoted into a role office.

---

## Principal Role

The principal should not babysit execution. The principal owns:

- preferences and research taste
- objectives and budget caps
- role/mandate approval
- public claims
- branch closure
- exceptional gate decisions

The principal should not have to:

- poll processes
- decide routine task ordering
- remember stale hypotheses
- manually close every experiment
- interpret raw subprocess logs

---

## Accountability Model

Accountability cannot be collapsed to one layer.

| Layer | Accountable object | What it can own | What it cannot own |
|---|---|---|---|
| Legal / fiduciary accountability | Human principal or deploying organization | Public claims, budgets, external commitments, risk acceptance, release decisions. | Cannot be delegated to a model or daemon in any meaningful enterprise sense. |
| Governance accountability | Role office | Whether it followed mandate, authorization gates, claim protocol, escalation rules, evidence closure, and refusal duties. | Cannot absorb legal blame for the human or organization. |
| Causal accountability | Transition log + artifacts | What happened, who/what triggered it, which gate/claim/message licensed it, what evidence was produced. | Cannot decide values by itself. |
| Model-call attribution | Transient invocation artifact | Prompt, model, inputs, output, score, critique, mutation, or cold-shot proposal. | No standing authority, no ownership of decisions. |

Munger inversion: if humans keep all accountability but agents act without
traceable obligations, the system becomes ungovernable. If agents are assigned
ultimate accountability, the system becomes legal and moral theater. The only
honest split is **ultimate accountability remains human/organizational;
operational accountability is pushed down to role offices; causal
accountability is made mechanically auditable**.

Operational consequence:

- Every role action needs an actor, role, mandate version, authorization
  decision, causality id, touched artifacts, and closure outcome.
- Every agent-to-agent message creates typed obligation, not execution
  authority.
- Every transient LLM call is recorded as evidence/proposal, not as a decision
  maker.
- Human approval cards must state what accountability the principal is
  accepting: cost, risk, external claim, irreversible mutation, or publication.

Enterprise rule:

```text
No accountability without authority.
No authority without mandate.
No mandate without audit.
No audit without durable artifacts.
```

This is why the product cannot be just "autonomous agents in a chat." The
company-grade object is the accountability graph: mandate -> authorization ->
message/gate/claim -> execution -> evidence -> closure.

## Human Interaction Contract

The human-facing product should be natural text, not command execution.
Shell commands are bootstrap/devops surfaces. The principal's daily interface
should be:

```text
Here is the decision.
Here is why it matters.
Here are the trade-offs.
Here is the recommended option.
Approve / Skip / Ask for more / Stop.
```

Approval cards must surface enough context to avoid rubber-stamping:

- what role wants to act
- what task or claim is involved
- why now
- expected cost / time / risk
- files or systems that may be touched
- what happens if approved
- what happens if skipped
- whether this is reversible
- what evidence/artifact will be produced

The principal should answer in natural language where possible. Orbit should
render this as cards. Telegram/phone should render the same decision in a
compact form. CLI/Python commands remain implementation and debugging tools,
not the intended governance experience.

---

## What Is Productized Now

- Generic principal preference file: `org/preferences/principal.yaml`.
- First-run setup check: `scripts/org_first_run_setup.py` validates role
  preflight, inboxes, A2A cards, and daemon dry-run without executing work.
- Role daemon can run as Manager or Research Director.
- Docker Compose profiles exist for role daemons.
- Research Director can be preflighted without mutation.
- Task discovery filters by assigned role.
- Unattended execution is explicit, not accidental.
- Principal tasks are claimed/closed by the daemon during execution.
- Orbit reads org state and gates.
- Orbit can resolve gates into canonical `ztare_workspace/gates/resolved/`.
- Orbit appends gate resolutions to `ztare_workspace/transitions.jsonl`.
- Persistent-agent channel: `org/channels/` plus
  `src/ztare/orchestration/agent_channels.py`.
- Work discovery now surfaces open role-channel messages as candidates.
- Channel sends are checked against a conservative local role-link policy:
  manager coordination, manager/principal escalation, or declared
  delegation/escalation links.
- Orbit renders open agent-channel inbox messages alongside gates.
- Unattended daemon execution is blocked for non-principal-task candidates;
  channel/damage/TODO candidates must be converted to a task or approved via
  gate before execution.
- Accountability is layered: human/org ultimate accountability, role-office
  operational accountability, transition-log causal accountability, model-call
  artifact attribution.

---

## Remaining Enterprise Blockers

- Full `TaskAuthorizationGate`: current implementation covers scope flags,
  budget cap, referenced paths, forbidden paths, and unattended eligibility,
  but still lacks tool/network/secret constraints and declared touched-file
  manifests.
- Constrained execution: role-specific worktree/container with allowed mounts.
- More runtime adapters beyond the shipped `claude_print` and `codex_exec`
  noninteractive paths.
- Stale-claim recovery / heartbeats / idempotency keys for multi-server leases.
- Authenticated Orbit mutation endpoints and safe bind address.
- Single approval path hardening: atomic pending-to-resolved transition with
  idempotency and gate-id validation across Orbit and Telegram.
- Event-log unification: daemon, Orbit, Telegram, closure daemon, channels,
  and workers should emit the same event schema.
- Postgres-backed control-plane service for multi-server / multi-division
  deployments; filesystem remains a materialized projection.
- A2A/ACP adapters for external agent interop at the control-plane boundary.
- MCP server exposing org-runtime resources/tools to agent hosts without making
  MCP the authority layer.
- Digest cards sorted by consequence, not feeds sorted by recency.
- Multi-tenant namespace and retention policy.

---

## Implementation Ledger

### 2026-04-30 15:58:00

Changes made during the productization session:

- Added this document as the durable north-star architecture.
- Added `docs/guides/org_runtime_quickstart.md`.
- Genericized the principal preference surface to
  `org/preferences/principal.yaml`.
- Added `org/members/principal.yaml`.
- Added `org/tasks/templates/research_director_candidate_review.md`.
- Patched the role daemon for explicit unattended mode, authorized Telegram
  control filtering, task claim/closure, real duration logging, and refusal of
  principal tasks with `autonomous_scope_ok=false`.
- Patched the task inbox and role preflight to work in bare Python without
  mandatory PyYAML.
- Patched Orbit to resolve gates through canonical
  `ztare_workspace/gates/{pending,resolved}/`, append transitions, watch the
  gate inbox, surface pending decisions, and bind localhost by default.
- Added `src/ztare/orchestration/transition_log.py`.
- Added `src/ztare/orchestration/task_authorization.py`.
- Updated GP-167 with Turns 5 and 6 so the debate record matches the code.

Verification:

- Python compile check passed for touched daemon/task/preflight files.
- Research Director dry-run discovers candidates successfully.
- Orbit production build passes.

### 2026-04-30 16:06:47

Changes made after the persistent-agent ontology review:

- Added the persistent role office vs transient invocation distinction.
- Added local typed agent-to-agent channel implementation:
  `src/ztare/orchestration/agent_channels.py`.
- Added `scripts/agent_channel.py` for development/debug use.
- Patched work discovery to surface open `org/channels/<role>/inbox/`
  messages as candidates for the owning role daemon.
- Registered the external-protocol stance: MCP for tools/context, A2A/ACP for
  interoperability adapters, local org-runtime envelope as canonical state.

### 2026-04-30 16:11:28

Changes made after the accountability panel:

- Added the accountability model: ultimate human/organizational
  accountability, operational role-office accountability, causal
  transition-log accountability, and transient-invocation attribution.
- Clarified that agent-to-agent messages create typed obligations, not
  execution authority.
- Added the enterprise rule: no accountability without authority; no authority
  without mandate; no mandate without audit; no audit without durable artifacts.

### 2026-04-30 17:45:59

Changes made after independent review:

- Added channel-policy enforcement to `agent_channels.py`; unlinked roles can
  no longer message each other by default.
- Patched work discovery so critical damage signals outrank agent-channel
  obligations.
- Patched daemon authorization flow so approval-required candidates open/queue
  gates instead of being terminally refused.
- Blocked unattended execution for non-principal-task candidates.
- Added daemon closure handling for agent-channel candidates so executed
  messages are closed/acknowledged.
- Added Orbit state and UI rendering for open agent-channel messages.
- Added `tests/test_agent_channels.py`; patched `tests/test_goals_inbox.py` so
  claim-conflict tests do not pollute the live damage inbox.

Verification:

- `python3 -m py_compile src/ztare/orchestration/agent_channels.py src/ztare/orchestration/work_discovery.py src/ztare/orchestration/task_authorization.py scripts/agent_daemon.py scripts/agent_channel.py`
- `venv/bin/pytest tests/test_agent_channels.py tests/test_work_discovery.py tests/test_goals_inbox.py` (`18 passed`)
- `cd orbit && npm run build`
- `python3 scripts/agent_daemon.py --role research_director --tick-once --dry-run`

### 2026-04-30 17:57:47

Changes made after validating the runtime identity boundary:

- `scripts/agent_daemon.py` now accepts `--member-id` and `--agent-cli`, with
  `ZTARE_MEMBER_ID` / `ZTARE_AGENT_CLI` environment defaults.
- `scripts/org_role_preflight.py` now checks the configured agent CLI instead
  of hardcoding `claude`.
- Docker daemon services pass the configured member/runtime through to the
  daemon.

Verification:

- `python3 -m py_compile scripts/org_role_preflight.py scripts/agent_daemon.py`
- `python3 scripts/org_role_preflight.py --role research_director --agent-cli claude --json`
- `python3 scripts/agent_daemon.py --role research_director --member-id codex --agent-cli claude --tick-once --dry-run`

### 2026-04-30 18:03:00

Changes made after bootstrap review:

- Added `AGENTS.md` to `scripts/org_role_preflight.py` as a required boot
  document.
- Added `docs/guides/org_runtime_quickstart.md` and the Research Director task
  template to preflight checks.
- Patched `scripts/agent_daemon.py` so spawned agents are explicitly instructed
  to read `AGENTS.md`, role YAML, mandate, quickstart, and principal
  preferences before acting.
- Added noninteractive runtime adapter selection: `claude_print` for
  `claude --print -p`, `codex_exec` for `codex exec --cd <repo> --sandbox
  workspace-write --ask-for-approval never`, and `auto` inference from the
  executable name.
- Added `scripts/org_runtime_smoke.py` as the one-command product smoke:
  preflight plus daemon dry-run, no work execution.
- Documented the instruction hierarchy: `AGENTS.md` is the repo constitution;
  role YAML is the durable contract; mandate is role-specific operating
  authority; stricter constraint wins on conflict.
- Fixed the agent-channel closure path so daemon-executed channel candidates
  close or acknowledge the underlying message instead of hitting an out-of-scope
  `role_id`.
- Hardened gate resolution: Telegram/daemon path now validates gate IDs,
  writes resolved gates atomically, preserves pending-gate contents in the
  resolved artifact, and marks pending gates handled. Orbit now validates gate
  IDs and treats already-resolved gates idempotently.
- Added local A2A-style agent-card projection:
  `scripts/export_a2a_agent_cards.py` writes role-office cards to
  `ztare_workspace/a2a/agent_cards/` without making A2A the authority layer.
- Added `scripts/org_inbox_status.py` to make the three inboxes explicit:
  executive gates, assignable tasks, and role-to-role obligations.
- Hardened minimal-environment role parsing so Docker/no-PyYAML exports keep
  block-scalar descriptions and null mandate fields sane.

Verification:

- `python3 -m py_compile src/ztare/orchestration/a2a_projection.py scripts/export_a2a_agent_cards.py scripts/org_inbox_status.py scripts/org_runtime_smoke.py scripts/agent_daemon.py scripts/org_role_preflight.py`
- `venv/bin/pytest tests/test_a2a_projection.py tests/test_agent_channels.py tests/test_work_discovery.py tests/test_goals_inbox.py` (`22 passed`)
- `npm --prefix orbit run build`
- `python3 scripts/agent_daemon.py --role research_director --member-id codex --agent-cli codex --agent-adapter codex_exec --tick-once --dry-run`
- `python3 scripts/org_runtime_smoke.py --role research_director --member-id codex --agent-cli codex --agent-adapter codex_exec`
- `python3 scripts/export_a2a_agent_cards.py`
- `python3 scripts/org_inbox_status.py`

### 2026-04-30 19:28:09

Changes made after GPU-run and early org-runtime failures:

- Added RD-1.5 GPU checkpoint/telemetry mandate: external GPU/API runs must
  declare run root, launch packet, checkpoint cadence, telemetry bundle, hard
  gates, download manifest, and closure artifacts.
- Patched the gp163d GPU runner to send remote-side ntfy start and
  interrupted notifications, and to terminate child solves on ordinary
  stop/hangup signals.
- Added `scripts/external_run_monitor.py` as the reusable remote-side watchdog
  for PID/result/progress/log monitoring.
- Added `scripts/org_first_run_setup.py` as the low-friction first-run boot
  check for the research-company runtime.
- Documented that missing external-run telemetry is instrument debt, not an
  acceptable shortcut.

Verification:

- `python3 -m py_compile projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/run_gpu_domain_validation.py`
- `python3 -m py_compile scripts/org_first_run_setup.py scripts/external_run_monitor.py`
