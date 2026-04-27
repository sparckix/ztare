# `org/` — AI-Native M-Form Primitives

**Seam:** GP-128 (Persistent Manager Agent / AI-Native M-Form)
**Opened:** 2026-04-23

This top-level folder houses the structural primitives for the AI-native
organization: **roles** (persistent identity + authority), **mandates**
(authorization scope per role), **delegation graph** (who-reports-to-whom),
and **sessions** (per-role audit windows).

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
│   ├── claude_manager.yaml    # Claude-as-manager
│   ├── codex_engineer.yaml    # Codex-as-implementer
│   └── gemini_reviewer.yaml   # Gemini-as-peer-reviewer
├── delegation.yaml            # public: cross-role edges + signing authority
├── mandates/                  # GITIGNORED: per-role authorization docs
│   └── claude_manager_mandate.md
└── sessions/                  # GITIGNORED: per-role audit windows
    └── <role_id>/<timestamp>/
        ├── transcript.md
        ├── actions.jsonl
        └── spend.json
```

## The three primitives

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

Defined in `org/mandates/<role_id>_mandate.md`. Gitignored because
mandates contain personal and IP-sensitive context (research program
state, patent portfolio, principal context). The mandate expands the
role YAML with:
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

## Relationship to GP-070 (goal orchestration)

GP-070 tracks **work** (goals, stages, gates, closure). `org/` tracks
**structure** (roles, mandates, delegation). These are ORTHOGONAL:

- A GP-070 goal has an `owner_role` pointing into `org/roles/`
- Gate signing authority per gate type is looked up via
  `org/delegation.yaml`
- A session happens whenever a role acts, regardless of which goals
  it touches

## CLI

```
ztare role list                     # list all roles
ztare role inspect <role_id>        # show role + mandate + recent sessions
ztare role delegate <role> <task>   # create a session, attach work
ztare session list <role_id>        # list this role's sessions
```

## Paper 4 connection

This folder is the practical instantiation of the AI-native M-form
architecture proposed in paper 4 (§ Persistence Asymmetry and Role-Substrate
Decoupling). Key paper claims grounded here:
1. Roles are persistent contracts; substrates are interchangeable bodies
2. Workers are ephemeral; managers are backed by persistent or session
   substrates — the ROLE is always persistent
3. Organizational leverage concentrates in role definition, not worker selection
