# `org/` — AI-Native M-Form Primitives

**Seam:** GP-128 (Persistent Manager Agent / AI-Native M-Form)
**Opened:** 2026-04-23

This top-level folder houses the structural primitives for an AI-native
organization: **roles** (persistent identity + authority), **mandates**
(authorization scope per role), **delegation graph** (who-reports-to-whom),
**tasks** (work packets), **execution routes** (how work should be handled),
and **sessions** (per-role audit windows).

`org/` is domain-general. A travel agency, fintech startup, or scientific
research lab should be able to reuse this skeleton. ZTARE-specific language
belongs in role mandates, task bodies, project folders, or backend adapters,
not in the core org primitive.

Kernel rule: `org/` owns mechanisms, not policy. Roles, mandates, claims,
routes, budgets, inboxes, and transitions are the stable kernel surface.
Domain policy is loaded through roles, mandates, preferences, tasks, and
backend adapters. If a generic primitive needs to say "science", "substrate",
or "ZTARE" to make sense, it is probably not generic enough.

## Why this is a top-level folder (not under `research_areas/` or `supervisor/`)

Per `AGENTS.md` §4:
- `research_areas/` = prose humans read/write (research notes, seams, specs)
- `supervisor/` = JSON the supervisor reads/writes (program registry, manifest)

Org structure is neither. Roles are **configuration of the organization**,
distinct from both the research corpus and the execution machinery. Placing
them at the root makes the org primitives discoverable without burying them
in content-addressed folders.

## Layout

```
org/
├── README.md                  # this file
├── roles/                     # public: persistent role definitions
│   ├── principal.yaml         # root authority (the human)
│   ├── manager.yaml           # operational manager
│   ├── research_director.yaml # external-validity / frontier direction
│   ├── engineer.yaml          # production-code engineer
│   └── reviewer.yaml          # independent reviewer
├── delegation.yaml            # public: cross-role edges + signing authority
├── mandates/                  # templates public; real mandates gitignored
│   ├── README.md
│   ├── templates/
│   ├── manager_mandate.md             # local/private
│   └── research_director_mandate.md   # local/private
├── tasks/                     # work packets + execution-route frontmatter
└── sessions/                  # GITIGNORED: per-role audit windows
    └── <role_id>/<timestamp>/
        ├── transcript.md
        ├── actions.jsonl
        └── spend.json
```

## The primitives

### 1. Role (persistent contract)

Defined in `org/roles/<role_id>.yaml`. A role specifies:
- Identity (role_id, display_name, description)
- Classification (manager / worker / reviewer / specialist)
- Substrates it can inhabit (Claude conversational, Claude daemon, Codex CLI, Gemini API, human)
- Authorized / forbidden filesystem paths
- Delegation outgoing edges (who this role may invoke)
- Escalation outgoing edges (who this role escalates to)
- Budget caps (daily / session / single-action)
- SLA expectations and failure mode
- Reference to the mandate document that expands the authorization

A role persists indefinitely. The BODY (substrate) may come and go — a
Claude session starts and ends, a daemon restarts — but the role
definition is the contract that constrains all of them.

### 2. Mandate (authorization)

Defined locally in `org/mandates/<role_id>_mandate.md`. Real mandates are
gitignored because they contain personal and IP-sensitive context (research
program state, patent portfolio, principal context). Public templates live in
`org/mandates/templates/`. The mandate expands the role YAML with:
- Scope of autonomous action (what the role does without asking)
- Scope of inbox escalation (what needs principal review at leisure)
- Scope of push escalation (what needs immediate principal attention)
- Absolute forbidden actions (what requires explicit written approval)
- Standing context (current research programs, preferences, relationships)

### 3. Session (execution window)

Defined in `org/sessions/<role_id>/<timestamp>/`. Gitignored because
sessions are personal activity logs. Each session contains:
- `transcript.md` — summary of what happened in this window
- `actions.jsonl` — append-only log of significant actions
- `spend.json` — cost telemetry for this session (matches spend_tracker schema)

Sessions enable (a) per-role daily/weekly spend rollups, (b) audit trail
for what a role actually did, (c) cross-session state handoff.

### 4. Task + Execution Route (generic work decomposition)

Defined in `org/tasks/{pending,active,done}/<task_id>.md`. A task says what
the organization wants done. The execution route says how it should be done:

- `route_only` — decide the route and create the next task.
- `direct_work` — a role-bearing agent can do the work directly.
- `expert_review` — use a bounded expert/adversarial review packet.
- `scripted_run` — run a script or external compute job with telemetry.
- `artifact_build` — build a reusable artifact/contract/workflow.
- `experiment_loop` — run a repeatable candidate-search loop after preflight.
- `docs_records` — update documentation, ledgers, manuals, or public/private mirrors.

These route names are intentionally generic. In this repo, `experiment_loop`
often means the ZTARE loop and `artifact_build` may mean a scientific substrate.
In another company, `experiment_loop` could mean a pricing A/B loop and
`artifact_build` could mean a supplier onboarding workflow. The org layer
should not know the domain; adapters and mandates bind the generic route to a
local backend.

### 5. Filesystem State Backend (current dogfood implementation)

The org runtime is currently filesystem-backed. That is a design choice for
inspectability and dogfood velocity, not a claim that every enterprise
deployment should use a shared folder forever.

The active state surfaces are:

- `org/tasks/` — assignable work and task closure.
- `org/channels/` — role-to-role messages.
- `org/sessions/` — session/audit windows and claims.
- `org/signals/` — damage signals.
- `ztare_workspace/gates/` — principal/executive decisions.
- `ztare_workspace/transitions.jsonl` — append-only transition trail.

Any daemon only sees the filesystem mounted into its process. If a task exists
on your laptop but the daemon is running on a VPS, the VPS will not see it
until you sync, mount, or otherwise replicate that state.

Deployment choices:

- **Local dogfood:** run daemon on the same checkout where tasks are written.
- **Single VPS:** copy/sync the repo plus private org state to the VPS, run
  daemons there, then sync results back.
- **Shared volume:** mount the same persistent volume into all daemon
  containers.
- **Enterprise backend:** replace the filesystem adapter with Postgres/object
  storage/event outbox while preserving the same logical primitives.

The kernel primitive is not "markdown files." The primitive is durable,
inspectable, claimable work state. Markdown files are the current adapter.

## Relationship to GP-070 (goal orchestration)

GP-070 tracks **work** (goals, stages, gates, closure). `org/` tracks
**structure** (roles, mandates, delegation). These are ORTHOGONAL:

- A GP-070 goal has an `owner_role` pointing into `org/roles/`
- Gate signing authority per gate type is looked up via
  `org/delegation.yaml`
- A session happens whenever a role acts, regardless of which goals
  it touches

## Research Director vs. ZTARE

The Research Director is not the ZTARE inner loop. The split is:

- **ZTARE / manager loop:** mutates candidates, scores candidates, runs gates,
  writes telemetry, and closes experiments.
- **Research Director:** reads durable artifacts, reconstructs the next
  hostile discriminator, ranks candidate next moves against
  `org/preferences/principal.yaml`, writes `next_discriminator_queue.jsonl`
  or directives, enforces checkpoint/telemetry discipline for external
  GPU/API runs, and escalates overclaim/instrument-risk signals.
- **Principal:** owns taste, budget, public-claim approval, and final branch
  closure.

The operating philosophy is:

```text
operator <-> agent discovers a useful move
-> artifacts record it
-> Research Director replays/ranks it
-> ZTARE or an engineer mechanizes the stable subroutine
```

Exploration may be manual. Durable learning should not remain manual.

## CLI

```
ztare role list                     # list all roles
ztare role inspect <role_id>        # show role + mandate + recent sessions
ztare role delegate <role> <task>   # create a session, attach work
ztare session list <role_id>        # list this role's sessions
```

## Docker / daemon boot path

For a fuller productized walkthrough, including task templates and
preference-based routing, see `docs/guides/org_runtime_quickstart.md`.

Before a daemon acts, the boot contract is:

1. `AGENTS.md` — repo-wide constitution loaded by every agent.
2. `org/roles/<role>.yaml` — role scope, budget, path constraints.
3. `org/mandates/<role>_mandate.md` — role-specific authority.
4. `org/preferences/<member>.yaml` — private preference/taste model.

`scripts/org_first_run_setup.py --init-private --skip-smoke` copies public
templates into missing local private mandate/preference files.
`scripts/org_role_preflight.py` checks these exist. `scripts/agent_daemon.py`
also tells the spawned runtime to read them. This matters in Docker because
not every agent host auto-discovers `AGENTS.md` the way Codex/Claude do in an
interactive repo session.

Dry-run the Research Director against the current preferences:

```bash
python scripts/org_role_preflight.py --role research_director
python scripts/agent_daemon.py --role research_director --tick-once --dry-run
docker compose --profile daemons run --rm research-director-daemon python scripts/org_role_preflight.py --role research_director
docker compose --profile daemons run --rm research-director-daemon python scripts/agent_daemon.py --role research_director --tick-once --dry-run
```

Run it continuously:

```bash
docker compose --profile daemons up research-director-daemon
```

The Docker service is only a process wrapper. It does not grant authority. The
role YAML, private mandate, private preference file, task assignment, and
principal approvals remain the authority surfaces. Full execution also requires
the configured agent runtime inside the container or a host daemon with the
agent CLI already authenticated.

Runtime identity is configurable. Example:

```bash
ZTARE_MEMBER_ID=codex ZTARE_AGENT_CLI=codex ZTARE_AGENT_ADAPTER=codex_exec docker compose --profile daemons up research-director-daemon
```

`ZTARE_MEMBER_ID` is the member/runtime written to sessions. `ZTARE_AGENT_CLI`
is the executable the daemon uses for task execution. `ZTARE_AGENT_ADAPTER`
selects the noninteractive runtime adapter. Supported adapters today are
`claude_print` and `codex_exec`; `auto` infers from the executable name.

## Paper 4 connection

This folder is the practical instantiation of the AI-native M-form
architecture proposed in paper 4 (§ Persistence Asymmetry and Role-Substrate
Decoupling). Key paper claims grounded here:
1. Roles are persistent contracts; substrates are interchangeable bodies
2. Workers are ephemeral; managers are backed by persistent or session
   substrates — the ROLE is always persistent
3. Organizational leverage concentrates in role definition, not worker selection
