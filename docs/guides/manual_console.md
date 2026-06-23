---
description: "Driving the repo via the manual console without the autonomous runtime."
---
# Manual Console

> **Up:** [Documentation map](../README.md)

**Purpose:** open a direct human-run Claude/Codex terminal session in this repo
without starting the autonomous org runtime.

This is the path for work like a normal Claude Code or Codex collaboration:
the human reviewer is present, the agent can ask clarifying questions, and no
background work-discovery loop is running.

Older checkouts may still use `operator_console.sh` as a compatibility alias.
The public command name is `manual_console.sh`.

- **Human reviewer** means the accountable person supervising the
  session.
- **Agentic worker** means the tool-using Claude/Codex process that can
  inspect files, run commands, edit artifacts, and report back.

The manual console is a human-run session with an agentic worker inside
it. It is not the same as a role daemon, where the agentic worker continues
under a standing mandate without the human reviewer present.

---

## The Three Runtime Lanes

Do not collapse these:

| Lane | Command surface | What it is for |
|---|---|---|
| **Manual console** | `scripts/public/control/manual_console.sh claude` | Direct human-agent collaboration. No daemon, no automatic task discovery, no validator loop. |
| **Role daemon** | `python scripts/public/control/agent_daemon.py ...` or Docker daemon profile | Persistent role-bound work with gates, claims, transitions, and closure. |
| **ZTARE validator** | `make experiment-loop ...` | Formal adversarial validation: mutator, judge, hard gates, telemetry, synthesis. |

The manual console is Mode A. The daemon is Mode B/org-runtime work. The
validator is Mode C/domain validation.

---

## Local Claude Code

Install and authenticate Claude Code on the host once:

```bash
npm install -g @anthropic-ai/claude-code
claude
```

Then start a direct console from the repo:

```bash
scripts/public/control/manual_console.sh claude
```

The script verifies the repo context files exist and then opens `claude`
interactively. It does not run `agent_daemon.py`, does not discover work, and
does not touch the executive inbox.

---

## Local Codex

If Codex CLI is installed and authenticated:

```bash
scripts/public/control/manual_console.sh codex
```

This is equivalent to opening Codex in the repo, with an explicit banner that
the session is Mode A.

---

## Docker Claude Console

If you want the console in a container:

```bash
scripts/public/control/manual_console.sh docker-claude
```

Equivalent direct command:

```bash
docker compose --profile console run --rm operator-claude
```

The service:

- uses `deploy/Dockerfile.operator`;
- installs Claude Code inside the image;
- mounts the repo at `/app`;
- mounts `${HOME}/.claude` into `/root/.claude` so existing Claude auth can be
  reused when available;
- passes API-key environment variables through.

This is still a manual console, not a daemon. When the container exits, the
interactive session is over. Durable changes are whatever the agent wrote to
the mounted repo.

---

## When To Use This Instead Of The Org Runtime

Use the manual console when:

- the human reviewer is actively supervising;
- the work is exploratory or conversational;
- you want the agent to inspect code, draft, debug, or reason interactively;
- the task does not need autonomous scheduling, notification approval, or
  background claims.

Use the role daemon when:

- work should continue without the human reviewer present;
- decisions should be surfaced as gates;
- a role mandate and budget should constrain the run;
- the result must be closed through the org runtime.

The invariant is simple: direct collaboration stays lightweight, but any result
that changes durable research state still has to obey `AGENTS.md` closure and
recording discipline.

## Before Durable RD Work

If the manual console is about a Research Director task, an autoresearch
boundary decision, or a project-charter/eigenquestion change, run the RD brief
first:

```bash
python scripts/public/control/rd_tick_brief.py \
  --allow-no-owner \
  --autoresearch-project <project> \
  --autoresearch-rubric <rubric> \
  --workbench-task "<task description>"
```

Read §8e for the autoresearch-workbench route and §8f for pending advisory
eigenquestions. If you continue out of loop on a task that could have used the
workbench, record the route decision with
`ztare autoresearch route --record-decision-id <id>`. Use
`ztare action-intel record-agentic-route` only when you already have a saved
route JSON.
