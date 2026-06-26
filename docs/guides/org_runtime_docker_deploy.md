---
description: "Running the AI-org runtime on a VPS/clean machine via Docker."
---
# Org Runtime Docker Deploy

> Up: [Documentation map](../README.md)

This guide is for running the AI-org runtime on a VPS or clean machine. It is
not specific to scientific work. The same `org/` skeleton can run a research
lab, travel agency, fintech team, or internal enterprise workflow. ZTARE is the
default backend in this repo. It is not a requirement of the org primitive.

---

## Mental Model

```text
repo checkout + private org config
-> Docker image with Python + agent CLI
-> role daemon
-> tasks / gates / sessions / transition logs on the mounted filesystem
```

The daemon does not own truth. It reads tasks, applies role/mandate limits,
asks for approval when required, executes through an agent CLI, and records
what happened.

---

## Build the image

From the repo root:

```bash
docker build -t ztare-org-runtime:local .
```

Or through Compose:

```bash
docker compose build research-director-daemon
```

The default `Dockerfile` installs:

- Python dependencies from `requirements.txt`
- `git`, `make`, `nodejs`, `npm`
- Claude Code CLI via `npm install -g @anthropic-ai/claude-code`

If you want Codex or another runtime instead, extend the image or install that
CLI on the host and run the daemon outside Docker.

---

## Prepare the VPS

On a clean Ubuntu VPS:

```bash
sudo apt-get update
sudo apt-get install -y git docker.io docker-compose-plugin
sudo usermod -aG docker "$USER"
newgrp docker
```

Clone the repo:

```bash
git clone <repo-url> ztare
cd ztare
```

Build:

```bash
docker compose build research-director-daemon
```

---

## Bring private org state

The public repo is not enough. Tasks and mandates are filesystem state. The VPS
daemon can only see what exists in its checkout.

Minimum private state to sync from your local machine:

```text
org/mandates/
org/preferences/
org/tasks/
org/channels/
ztare_workspace/gates/
```

Simple one-off sync from local:

```bash
rsync -az \
  org/mandates org/preferences org/tasks org/channels ztare_workspace/gates \
  <user>@<vps-ip>:~/ztare/
```

After the run, sync results back:

```bash
rsync -az \
  <user>@<vps-ip>:~/ztare/org/tasks/ \
  <user>@<vps-ip>:~/ztare/org/sessions/ \
  <user>@<vps-ip>:~/ztare/ztare_workspace/ \
  ./_vps_pull/
```

For production, replace ad hoc `rsync` with one of:

- a private encrypted config repo;
- a mounted secrets/config volume;
- an API-backed task store;
- a database/event-log backend.

The current single-team backend is files.

---

## Configure environment

Create `.env` on the VPS. Do not commit it.

```bash
cp .env.example .env
$EDITOR .env
```

At minimum:

```text
ANTHROPIC_API_KEY=...
ZTARE_AGENT_CLI=claude
ZTARE_AGENT_ADAPTER=claude_print
ZTARE_MEMBER_ID=research-director-vps01
ZTARE_UNATTENDED=
```

Leave `ZTARE_UNATTENDED` empty for approval-gated operation. Set it only after
a successful supervised single-team run on the same machine.

The default `docker-compose.yml` intentionally does not reference secret
provider keys, so `docker compose config` is safe to run in public logs. For
live daemon runs, pass the private file explicitly:

```bash
docker compose --env-file .env --profile daemons up research-director-daemon
```

---

## Preflight

Run the same checks Docker would run before live work:

```bash
docker compose --env-file .env --profile daemons run --rm research-director-daemon \
  python scripts/public/control/org_first_run_setup.py \
    --member-id research-director-vps01 \
    --agent-cli claude \
    --agent-adapter claude_print
```

Dry-run one daemon tick:

```bash
docker compose --env-file .env --profile daemons run --rm research-director-daemon \
  python scripts/public/control/agent_daemon.py \
    --role research_director \
    --member-id research-director-vps01 \
    --agent-cli claude \
    --agent-adapter claude_print \
    --tick-once \
    --dry-run
```

Expected result: the daemon lists candidate work and stops before mutation.

---

## Run the research director

Approval-gated:

```bash
docker compose --env-file .env --profile daemons up research-director-daemon
```

One-shot live tick:

```bash
docker compose --env-file .env --profile daemons run --rm research-director-daemon \
  python scripts/public/control/agent_daemon.py \
    --role research_director \
    --member-id research-director-vps01 \
    --agent-cli claude \
    --agent-adapter claude_print \
    --tick-once
```

Unattended:

```bash
ZTARE_UNATTENDED=1 docker compose --env-file .env --profile daemons up research-director-daemon
```

Unattended mode still obeys role mandates, task claims, budget gates, route
contracts, and closure discipline. It only skips the approval wait when the
task is already in autonomous scope.

---

## How tasks move

1. Put a task in `org/tasks/pending/<task_id>.md`.
2. Daemon discovers it.
3. Daemon proposes or executes depending on mandate + unattended mode.
4. Daemon claims it into `org/tasks/active/`.
5. Spawned role agent receives an `EXECUTION ROUTE CONTRACT`.
6. Agent writes the required first artifact.
7. Agent executes or creates a handoff task.
8. Daemon closes to `org/tasks/done/` or appends `## Blocked`.

For generic org routing, see `org/tasks/README.md`.

---

## Common failure modes

- No task appears: the task was never synced to the VPS checkout.
- Daemon runs but no work executes: gate approval is pending, or
  `ZTARE_UNATTENDED` is empty.
- Agent CLI missing: the image contains Claude by default; other CLIs must
  be installed separately.
- Auth failure: the container has API keys but the CLI may still require
  its own auth/session.
- Results not visible locally: sync `org/tasks/`, `org/sessions/`, and
  `ztare_workspace/` back from the VPS.

---

## Kernel boundary

The Docker image runs the org kernel. It should not encode company policy.

Generic kernel:

- roles
- mandates
- tasks
- execution routes
- claims
- gates
- sessions
- transition logs

Policy/adapters:

- ZTARE research backend
- travel-agency workflow backend
- fintech risk-control backend
- enterprise approval/SOO/RBAC backend

Keep that boundary clean. If the Docker path only works for ZTARE science
tasks, the org runtime has overfit.
