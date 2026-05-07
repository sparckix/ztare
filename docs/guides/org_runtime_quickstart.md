# Org Runtime Quickstart

**Audience:** operators or enterprise engineers who want persistent AI roles,
not just one-off chat sessions.

**Status:** productization path for the *Cognitive Firm* organizational primitives.
The scientific engine is MIT-licensed; the governance kernel is BSL/commercial.
See `README.md` §License and
`docs/concepts/ztare_research_company_architecture.md` for the 24×7 unattended
architecture.

---

## RD-1.12 Live Co-Drive (default operating mode, 2026-05-02)

Live co-drive is **standard operating mode** for the Research Director.
The daemon runs the full detection → policy → execution chain on every
tick — there is no opt-in flag.

The chain:

1. **Detection** (`src/ztare/role_extensions/frontier_runner.py`) watches
   per-project artifacts (`eval_history.jsonl`, `latest_eval_results.json`,
   `debate_log_iter_*.md`, `verified_axioms.json`) and emits typed events:
   `obstruction_detected`, `verified_axiom_emitted`, `champion_promoted`,
   `gate_repeated_cold_shot`, `stagnation_detected`.

2. **Policy** (`src/ztare/role_extensions/iter_action_policy.py`) reads
   `iter_action_policy.yaml`, matches events against rules, and queues
   actions onto `frontier_state.<slug>.json::pending_actions` (idempotent
   via cooldown windows). Default rules are kernel-shipped; per-instance
   overrides go to `org/policies/iter_action.yaml`.

3. **Execution** (`src/ztare/role_extensions/iter_action_executor.py`)
   pops queued actions and runs them through three safety rails:
   - **USD spend gate** via `src/ztare/supervisor/spend_tracker.py`
   - **Agent-CLI utilization gate** via `agent_utilization_tracker.py`
   - **Damage signal emit** to `org/signals/damage/` on any failure

Action handlers cover: `fork_substrate`, `create_lean_cage`,
`demote_route_in_packet`, `mutate_evidence`, `mutate_charter`,
`queue_cold_shot`, `update_champion_meaning`, `escalate_to_principal`.

Visualize live state in Orbit by clicking 🧭 **Frontier** in the top bar
(reads `/api/frontier_state`).

### Agent-CLI utilization caps (capacity dimension, ≠ USD spend)

Each role yaml may carry an `agent_utilization` block (schema v1.2):

```yaml
agent_utilization:
  daily_cap_seconds: 7200            # max wall-clock per UTC day
  daily_cap_output_tokens: 500000    # max tokens emitted
  daily_cap_turn_count: 200          # max agent steps
  session_cap_seconds: 1800          # any single session
  absolute_ceiling_seconds: 14400    # never-exceed (runaway-loop breaker)
  warn_threshold_frac: 0.80          # push warning at 80% of any cap
```

Tracked daily totals live at `ztare_workspace/agent_utilization/<date>.json`.
Warn-threshold trips emit a Telegram push **and** a damage signal at
`org/signals/damage/` (idempotent — one alert per role/cli/dim/UTC-day).

**Warn-threshold jitter (gp168 v3 run-2 finding F2, 2026-05-02).** The
effective warn-threshold is jittered by ±10% per `(role, agent_cli,
UTC-date)` so agents cannot game by staying just below a static
threshold. With `warn_threshold_frac: 0.80`, the apparatus actually
warns at a uniform-random fraction in `[0.70, 0.80]` each day, seeded
by `(role_id, agent_cli, date)` so reproducible within a day but
unpredictable across days. Set `agent_utilization_jitter_window: 0.0`
in the rubric to disable for deterministic operation.

**Override events (gp168 v3 run-2 finding F1, 2026-05-02).** When the
principal extends a cap, postpones a closure, delays an approval,
skips an audit, or raises the absolute ceiling, the event is recorded
to `ztare_workspace/agent_utilization/overrides/<date>.jsonl` AND
appended to `transitions.jsonl` as `event: override_event` AND pushed
to Telegram (friction-of-being-watched defense). Every principal-side
subversion of the exogenous-pressure clock is now a first-class audit
artifact rather than a silent action. API:
`record_override_event(kind, role_id, actor, old_value, new_value,
target, reason)` from `src.ztare.supervisor.agent_utilization_tracker`.

Configure caps from Orbit by clicking ⚙ **Settings** in the top bar.

### Agent-CLI rotation (optional — gp168 v3 run-2 finding F3, 2026-05-02)

A role yaml may carry an `agent_rotation` block to rotate the role's
primary member across multiple CLIs (Claude / Codex / Gemini) on a
fixed cadence. Single-CLI-specific gaming patterns surface as
cross-CLI inconsistency in role outputs.

```yaml
agent_rotation:
  enabled: true
  rotation_period_days: 7              # weekly rotation
  members: [member.claude, member.codex, member.gemini]
  strategy: round_robin                # round_robin | random | stratified
  fallback_member: member.claude       # used if rotated CLI is unavailable
```

Resolved by `src.ztare.supervisor.agent_rotation.resolve_with_fallback`
at daemon tick time. Members whose CLI is unavailable on the host
(`shutil.which()` probe) are skipped automatically.

### Anti-debrief autonomy directive

`AGENTS.md §4z` ("Maximal autonomy — keep pushing; don't debrief between
sub-tasks") instructs every agent to keep working until one of four
real stop conditions: information gap, budget trip, damage signal, or
forbidden path. The daemon enforces the same contract by adding
`--permission-mode acceptEdits` (Claude) and `--ask-for-approval never`
(Codex) on every spawn, plus a post-tick verification check that emits
a damage signal if the agent returned success but produced no audit/state
advance.

---

## What This Is

The org runtime turns a repository into a small AI-native firm:

```text
principal preferences + mandates
-> task/objective tree
-> role daemon
-> proposal or execution
-> session log, damage signal, closure gate, experiment ledger
```

The important distinction is:

- **ZTARE** executes formal research loops: mutator, judge, gates, telemetry,
  workspace artifacts, closure.
- **Research Director** chooses and sequences frontier work: it reads artifacts,
  ranks next moves against the principal's preferences, proposes hostile
  discriminators, and blocks promotion when the evidence is not licensed.
- **Manager** runs operational work: cleanup, workflow execution, closure, and
  standard task processing.

This is not another chat wrapper. The durable state is in files under `org/`,
`ztare_workspace/`, `projects/`, and `research_areas/`.

## State Backend: Where The Org Lives

The current org runtime is filesystem-backed. That means the daemon only sees
tasks, gates, mandates, sessions, and channels that exist in the checkout or
volume mounted into the daemon process.

For local use, this is simple: write a task under `org/tasks/pending/`, run the
daemon from the same repo, and the task is visible.

For a VPS or Docker deployment, you must choose a state strategy:

- **Same checkout:** clone the repo on the VPS and create tasks there.
- **Sync:** `rsync` private org state (`org/mandates`, `org/preferences`,
  `org/tasks`, `org/channels`, `ztare_workspace/gates`) to the VPS before the
  daemon runs, then sync results back.
- **Mounted volume:** mount the same persistent volume into all daemon
  containers.
- **Service backend:** replace the file adapter with a database/API/event log
  while preserving the same task/gate/session abstractions.

Do not assume a daemon running on a VPS can see a task created only on your
laptop. Filesystem state is local unless you replicate it.

If you want a direct principal-operated Claude/Codex terminal session instead
of the autonomous org runtime, use
[`docs/guides/operator_console.md`](operator_console.md). That path starts no
daemon and runs no work-discovery loop.

---

## The Minimal Local Check

Run the productized first-run check before starting any daemon:

```bash
python scripts/org_first_run_setup.py --init-private --skip-smoke
python scripts/org_first_run_setup.py --member-id codex --agent-cli codex --agent-adapter codex_exec
```

The first command creates missing local private bootstrap files from public
templates: `org/mandates/manager_mandate.md`,
`org/mandates/research_director_mandate.md`, and
`org/preferences/principal.yaml`. These files are gitignored; edit them for
your local principal and role authority before unattended execution.

The second command validates the instruction stack, role preflights, A2A
agent-card export, inbox state, and a dry-run Research Director daemon tick
without executing work.

The lower-level checks are:

```bash
python scripts/org_role_preflight.py --role research_director
python scripts/org_role_preflight.py --role manager
python scripts/org_runtime_smoke.py --role research_director --member-id codex --agent-cli codex --agent-adapter codex_exec
```

What this checks:

- `AGENTS.md` exists as the repo-wide agent constitution
- role YAML exists in `org/roles/`
- local private mandate exists in `org/mandates/`
- principal preference profile exists in `org/preferences/principal.yaml`
- org-runtime quickstart and Research Director task template exist
- Research Director dependencies exist
- local A2A-style role cards can be exported
- the three inboxes can be summarized
- the configured agent runtime is available, if required

If you want preflight to fail when the configured agent runtime is missing:

```bash
python scripts/org_role_preflight.py --role research_director --require-agent --agent-cli claude
```

---

## Run With Docker

On macOS, install Docker Desktop first:

```bash
brew install --cask docker
open -a Docker
docker version
```

Validate the Research Director service without executing work:

```bash
docker compose --profile daemons run --rm research-director-daemon \
  python scripts/org_role_preflight.py --role research_director
```

Run one discovery tick without executing work:

```bash
docker compose --profile daemons run --rm research-director-daemon \
  python scripts/agent_daemon.py --role research_director --tick-once --dry-run
```

Run continuously:

```bash
docker compose --profile daemons up research-director-daemon
```

Run the operational manager instead:

```bash
docker compose --profile daemons up manager-daemon
```

The container is a process wrapper. Full execution requires the chosen agent
runtime and credentials inside the container, or running the daemon on a host
where that runtime is already authenticated. If the image does not contain
`claude` or `codex`, run the local smoke command first and treat Docker as a
deployment wrapper until the runtime image is extended.

Runtime identity is configurable:

```bash
ZTARE_MEMBER_ID=codex ZTARE_AGENT_CLI=claude \
docker compose --profile daemons up research-director-daemon
```

`ZTARE_MEMBER_ID` is the accountable runtime/member recorded in sessions.
`ZTARE_AGENT_CLI` is the executable used for task execution.
`ZTARE_AGENT_ADAPTER=auto` chooses the adapter from the executable name:

- `claude_print`: `claude --print -p <prompt>`
- `codex_exec`: `codex exec --cd <repo> --sandbox workspace-write --ask-for-approval never <prompt>`

Codex example:

```bash
ZTARE_MEMBER_ID=codex ZTARE_AGENT_CLI=codex ZTARE_AGENT_ADAPTER=codex_exec \
python scripts/agent_daemon.py --role research_director --tick-once --dry-run
```

## Bootstrap Contract: What The Agent Reads

Every Docker/daemon role run has three layers of instruction:

1. `AGENTS.md` — repo-wide constitution. It covers closure discipline,
   public/private artifact rules, experiment recording, CLI discipline,
   inversion reflexes, and the operating philosophy.
2. `org/roles/<role>.yaml` — durable role contract. It defines identity,
   allowed/forbidden paths, budget, delegation, escalation, and mandate path.
3. `org/mandates/<role>_mandate.md` — role-specific operating authority. It
   defines what the role may do, what it must escalate, and current standing
   context.

The daemon prompts the spawned agent to read all three, and preflight checks
that the required files exist. `AGENTS.md` is not a task queue and not a role
mandate; it is the higher-level repo constitution. If it conflicts with a role
mandate, the agent must obey the stricter constraint and escalate the conflict.

The bootstrap proof is:

```bash
python scripts/org_role_preflight.py --role research_director --agent-cli claude --json
python scripts/agent_daemon.py --role research_director --member-id codex --agent-cli codex --agent-adapter codex_exec --tick-once --dry-run
```

The first command proves the documents/runtime are reachable. The second proves
the role can open a session, read durable state, discover work, and stop before
mutation.

By default, a daemon with Telegram configured asks for approval before
executing, and a daemon without Telegram refuses to execute. For an explicit
24×7 unattended run where in-scope tasks execute without approval, set:

```bash
ZTARE_UNATTENDED=1 docker compose --profile daemons up research-director-daemon
```

Use this only after `org/roles/<role>.yaml`, `org/mandates/<role>_mandate.md`,
and `org/preferences/principal.yaml` are correct. Unattended mode still routes
only role-assigned work and still uses task claims, damage signals, and closure
artifacts.

---

## Give The Director Work

Create a task under `org/tasks/pending/` using the Research Director template:

```bash
cp org/tasks/templates/research_director_candidate_review.md \
  org/tasks/pending/research_director_candidate_review.md
```

Edit the frontmatter:

```yaml
assigned_to: role.research_director
autonomous_scope_ok: true
```

Then run a dry tick:

```bash
python scripts/agent_daemon.py --role research_director --tick-once --dry-run
```

For real execution, remove `--dry-run`. If Telegram is configured, the daemon
proposes the task and waits for approval. If Telegram is not configured, the
daemon refuses to execute unless `--unattended` is explicitly passed, so use
`--dry-run` until you are sure the mandate is correct.

The intended human interaction is natural language through Orbit/Telegram,
not Python commands. Commands are the bootstrap/debug surface. The daily
experience should be: a role proposes a decision card, explains trade-offs and
artifacts, and the principal replies approve/skip/ask/stop.

---

## Where Human-Agent Communication Lives

The product surface is split deliberately:

- **Orbit** is the primary console. It reads `org/` and `ztare_workspace/`,
  shows roles, active sessions, task pressure, damage signals, pending gates,
  and agent-channel messages, then writes gate resolutions back to the
  filesystem backend.
- **Telegram** is the mobile approval and notification rail. It watches the
  same executive inbox, pushes compact decision cards, accepts fixed approval
  verbs, and records the resolution in `ztare_workspace/gates/resolved/`.
- **A2A channels** under `org/channels/` are role-to-role communication. They
  are durable handoff envelopes for agents, not a substitute for human approval.
- **CLI commands** are setup and debugging tools. They are not the desired
  everyday interface.

The current gap is free-form natural-language routing. Today, Orbit and
Telegram can resolve structured gates; they do not yet parse arbitrary human
messages into typed directives/tasks/gates. That parser should sit in front of
the same backend, not create a second chat-owned source of truth.

See the standalone concept page:

```text
docs/demos/research_company_landing.html
```

---

## Route Research Areas By Principal Preference

Preferences live here:

```text
org/preferences/principal.yaml
```

The current research-taste axes are:

- `outstanding_problem_resolution`
- `prize_or_money_potential`
- `architecture_fit`
- `self_recursive_governance`

Candidate next moves are ranked from JSONL queues:

```bash
python -m src.ztare.orchestrator.research_taste \
  --queue projects/<project>/workspace/next_discriminator_queue.jsonl \
  --out projects/<project>/workspace/research_taste_ranking.json
```

For frontier projects, build or refresh the queue from durable artifacts:

```bash
python -m src.ztare.orchestrator.operator_replay_audit \
  --project <project_slug> \
  research_areas/EXPERIMENT_TRACK_RECORD.md \
  research_areas/private/insights_ledger.md
```

Then run the taste ranker on the generated queue. A high taste score routes
attention; it does not license a scientific claim or dispatch a GPU run by
itself.

## External GPU/API Run Discipline

Research Director work often leaves the local repo for a GPU box or paid API
provider. Those runs must be launched as resumable instruments, not as opaque
terminal sessions.

Before launch, create or emit a run packet with:

- run root, host, batch label, exact command, and artifact download target;
- expected device residency and warmup window;
- checkpoint cadence and checkpoint file pattern;
- telemetry files to preserve: preflight JSON, process/GPU probes, raw logs,
  residual diagnostics, summaries, and partial artifacts;
- hard admissibility gates, kill conditions, and notification channel.

During the run, poll the declared run root and verify command lines, device
residency, log freshness, and checkpoint progression. If an independent batch
fails a hard gate, stop the remaining configurations, download partial
artifacts, and close the experiment.

At closure, download the full declared artifact set or explicitly list what is
missing. A cold agent should be able to reconstruct the run from the closure
bundle without reading chat history.

Reusable watchdog:

```bash
python scripts/external_run_monitor.py \
  --run-name "my GPU batch" \
  --pid-file /path/to/run.pid \
  --result-file /path/to/result.json \
  --progress-file /path/to/progress.json \
  --log-file /path/to/raw.log \
  --monitor-log /path/to/monitor.log \
  --topic "$ZTARE_NTFY_TOPIC"
```

The watchdog sends remote-side start, completion, interrupted, and
stopped-without-result notices. Project-specific runners may embed the same
logic directly, but they should still write a terminal result marker JSON.

---

## Enterprise Shape

The easy boot surface is:

```text
write task -> start daemon -> approve/skip -> inspect artifacts
```

The backend model is deliberately not "chat as state" and not "git as a
database":

- **Canonical live state:** files under `org/` and `ztare_workspace/`.
- **Executive inbox:** `ztare_workspace/gates/pending/`, resolved into
  `ztare_workspace/gates/resolved/`.
- **Append-only audit:** `ztare_workspace/transitions.jsonl` plus git history.
- **Interface projections:** Orbit and Telegram read/write through the backend
  paths above; they do not own independent state.
- **Git's role:** versioning, audit, rollback, and sync. It is not the
  low-latency coordination primitive.

The enterprise value is the governance layer:

- role contracts and mandates are versioned files
- session claims prevent multiple agents from writing the same resource
- damage signals surface harmful-but-authorized actions
- closure clocks prevent infinite deliberation
- preferences are explicit and auditable
- Research Director separates taste/routing from proof/validation
- ZTARE keeps formal experiment execution behind gates and ledgers

Near-term gaps before this is turnkey enterprise software:

- packaged agent runtime inside the Docker image
- first-run setup command for credentials and notification channels
- multi-tenant role namespace
- SSO/GPG signing/retention controls
- stronger pre-dispatch authorization gates and constrained execution
- production auth on Orbit mutation endpoints
