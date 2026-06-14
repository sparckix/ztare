---
description: "How to stand up a new org instance from the substrate-agnostic kernel."
---
# Forking the Org Kernel

> **Up:** [Documentation map](../README.md)

*Last updated: 2026-05-02, RD-1.12 release.*

This guide walks through standing up a new org instance ("instantiation")
on top of the public kernel published in this repository. It is written
for someone who wants to run their own research org, *not* a clone of
the ZTARE Research Org, but a fresh org with their own roles, projects,
mandates, and principal.

---

## 1. The kernel/instantiation split

The repository contains **two layers**:

1. **Kernel (public, MIT-licensed)**, the substrate-agnostic machinery
   that any org can reuse:
   - `src/ztare/role_extensions/`, RD-1.12 frontier-state, policy, executor
   - `src/ztare/supervisor/`, spend tracker, agent-utilization tracker
   - `schemas/`, `role.v1.schema.json` and friends
   - `scripts/public/control/agent_daemon.py`, the cron-style tick runner
   - `orbit/`, the dashboard frontend + git-sync backend
   - `AGENTS.md`, operating mode, autonomy directive, schema rules

2. **Instantiation (typically private)**, the principal's specific org:
   - `org/roles/<role_id>.yaml`, concrete role definitions
   - `org/mandates/*.md`, concrete role mandates
   - `org/objectives/`, `org/key_results/`, `org/tasks/`, the OKR tree
   - `projects/<slug>/`, actual research projects
   - `papers/`, `rubrics/`, domain-specific outputs
   - `ztare_workspace/`, runtime state

When you fork this repo, you get the kernel. The principal's instantiation
of ZTARE Research Co lives in a **separate private overlay repo** that
symlinks tenant-specific role/mandate/preference files into the
conventional `org/...` paths at runtime. A fresh fork without an overlay
runs in **kernel-only mode**, no `research_director.yaml`, no ZTARE-
specific mandates, exactly the [GP-191](../../research_areas/seams/engine/GP-191_typed_cold_shot_portfolio_seam.md) Stage 3 verification target.

> **The contract:** changes to kernel files (anything under `src/ztare/`,
> `schemas/`, `scripts/public/`, `orbit/src/server/`, or `AGENTS.md`) are upstream
> contributions. Tenant-specific instantiation lives in your own
> `<your-org>-tenant-overlay` private repo under `tenants/<your-id>/`,
> symlinked in via your tenant's `setup_tenant.sh` script.

### Tenant overlay pattern ([GP-191](../../research_areas/seams/engine/GP-191_typed_cold_shot_portfolio_seam.md) Stage 2)

```
~/ztare/                                    ← public kernel (this repo)
  org/                                      ← substrate-agnostic primitives
    roles/{principal,manager,engineer,reviewer}.yaml   ← generic
    mandates/templates/*                                ← generic templates
    preferences/templates/principal.yaml               ← schema
    bootstrap_manifest.yaml                            ← schema
  tenants/                                   ← tenant slot (README.md tracked; subdirs gitignored)

~/<your-org>-tenant-overlay/                ← YOUR private overlay repo
  tenants/<your-id>/
    roles/research_director.yaml            ← your tenant-specific roles
    preferences/principal.yaml              ← your values
    mandates/*.md                           ← your real mandate bodies
  scripts/public/setup_tenant.sh                   ← symlinks the above into public tree
  scripts/public/teardown_tenant.sh                ← removes symlinks (returns to kernel-only)
```

The reference implementation is the public Cognitive Firm kernel at
`github.com/sparckix/cognitive-firm`. Mirror its shape for your own org.

## 2. Pre-flight: validate the kernel works

```bash
git clone <this-repo> my-org
cd my-org
python scripts/public/control/forked_org_smoke.py
```

You should see four green checkmarks ending with `smoke PASSED`. If any
check fails, the kernel itself is broken and you should not proceed, 
file an issue or fix it before going further.

## 3. Wipe the principal's instantiation

These directories contain the previous principal's content. Empty (or
delete) them on your fork:

```bash
# OKR tree, keep .gitkeep but remove content
rm -rf org/objectives/* org/key_results/* org/tasks/active/* \
       org/tasks/done/* org/tasks/pending/*

# Domain projects + papers
rm -rf projects/*/  papers/*/

# Runtime state (will be regenerated)
rm -rf ztare_workspace/frontier_state/* \
       ztare_workspace/agent_utilization/* \
       ztare_workspace/transitions.jsonl

# Role definitions, you'll author your own in step 4
rm -rf org/roles/*.yaml org/mandates/*.md
```

The `.gitkeep` files in each subdirectory should remain so the directory
structure is preserved.

## 4. Author your roles

The minimum viable org has three roles. All role yamls validate against
`schemas/role.v1.schema.json` (kernel-pinned).

### 4a. Principal (the human owner)

```yaml
# org/roles/principal.yaml
schema_version: 1
role_id: principal
role_class: authority
description: >
  Human owner of this org instance. Approves directives, signs off on
  major architectural changes, and holds the ultimate veto on any agent
  action. All escalations terminate here.
authorized_paths: ["**/*"]
forbidden_paths: []
delegates_to: ["role.research_director", "role.manager"]
escalates_to: []
budget:
  daily_cap_usd: null
  session_cap_usd: null
  single_action_cap_usd: null
  warn_threshold_frac: null
  absolute_ceiling_usd: null
mandate_path: null
```

### 4b. Research Director (the autonomous agent)

```yaml
# org/roles/research_director.yaml
schema_version: 1
role_id: research_director
role_class: director
description: >
  Autonomous research-driving agent. Watches the iter loop on every
  active project, dispatches frontier_runner detection passes, queues
  iter_action_policy actions, and executes them via iter_action_executor
  under safety rails (USD spend cap + agent_utilization cap + damage
  signal emit).
authorized_paths:
  - "projects/**"
  - "ztare_workspace/frontier_state/**"
  - "ztare_workspace/transitions.jsonl"
  - "ztare_proofs/cages/**"
forbidden_paths:
  - "papers/**"          # papers go through escalation
  - "schemas/**"         # kernel
  - "src/ztare/**"       # kernel
delegates_to: []
escalates_to: ["role.principal"]
budget:
  daily_cap_usd: 50.0
  session_cap_usd: 10.0
  single_action_cap_usd: 5.0
  warn_threshold_frac: 0.80
  absolute_ceiling_usd: 200.0
agent_utilization:
  daily_cap_seconds: 7200
  daily_cap_output_tokens: 500000
  daily_cap_turn_count: 200
  session_cap_seconds: 1800
  absolute_ceiling_seconds: 14400
  warn_threshold_frac: 0.80
mandate_path: org/mandates/research_director_mandate.md
```

### 4c. Manager (the routing/escalation role)

A minimal manager mandate is in `org/mandates/manager_mandate.md` template.
You can defer this until you have multiple workers to coordinate.

## 5. Configure the daemon

The agent daemon at `scripts/public/control/agent_daemon.py` reads `org/roles/` and
ticks each role on a cron-like schedule. Default tick interval is 60s.

```bash
# Recommended: run under a process supervisor (systemd, launchd, tmux)
ORBIT_BACKEND_PORT=3001 python scripts/public/control/agent_daemon.py --tick-interval 60
```

The daemon is **idempotent**, if no events have happened since the last
tick, no action is taken. Safe to restart.

## 6. Wire Orbit

```bash
cd orbit
npm install
ORBIT_BACKEND_HOST=127.0.0.1 ORBIT_BACKEND_PORT=3001 npm run dev
```

Open `http://localhost:5173`. You should see your role(s) in the
constellation, an empty objective tree (until you create OKRs), and the
🧭 Frontier and ⚙ Settings buttons in the top bar.

## 7. Optional: customize the policy

The default policy at `src/ztare/role_extensions/iter_action_policy.yaml`
ships with seven rules covering common patterns (obstruction → fork,
verified-axiom → Lean cage, champion-shift → meaning update, etc.).
You can:

- **Override per-instance:** copy the yaml to `org/policies/iter_action.yaml`
  and point `IAP_POLICY_PATH=org/policies/iter_action.yaml` in the daemon
  environment. The kernel default stays untouched.
- **Hot-reload:** edit the yaml while the daemon is running; the next
  tick picks up the change (no restart required).

## 8. The public/private boundary, restated

When you push your fork:

| Path                          | Public on your fork? |
|-------------------------------|----------------------|
| `src/ztare/`                  | yes (kernel)         |
| `schemas/`                    | yes (kernel)         |
| `scripts/public/control/agent_daemon.py`     | yes (kernel)         |
| `orbit/`                      | yes (kernel)         |
| `AGENTS.md`                   | yes (operating contract for THIS deployment) |
| `org/roles/{principal,manager,engineer,reviewer}.yaml` | yes (generic primitives) |
| `org/mandates/templates/*` | yes (generic templates) |
| `org/preferences/templates/*` | yes (schema) |
| `org/bootstrap_manifest.yaml` | yes (schema) |
| `org/channels/` | yes (schema; content gitignored) |
| `tenants/README.md` | yes (documents the slot) |
| `tenants/<id>/`               | **NEVER**, your private overlay (gitignored from public) |
| `org/roles/research_director.yaml` | gitignored from public (lives in tenant overlay) |
| `org/roles/product_manager.yaml` | gitignored from public (lives in tenant overlay) |
| `org/preferences/principal.yaml` | gitignored from public (the values; schema is at templates/) |
| `org/mandates/*.md` (non-template) | gitignored from public |
| `org/{objectives,key_results,tasks,sessions,signals,directives,goals}/` | gitignored from public |
| `projects/`                   | curated showcase allowlist; rest gitignored |
| `papers/`                     | usually public for ZTARE Research Co (published work); private if you choose |
| `ztare_workspace/`            | runtime state gitignored; future [GP-192](../../research_areas/seams/protocol/GP-192_enterprise_grade_org_runtime_seam.md) Axis 7 daily-snapshot lives in your tenant overlay |

The public `.gitignore` enforces these defaults. The kernel-only-runnable
property is verified by `setup_tenant.sh` / `teardown_tenant.sh`, running
teardown should leave the public tree functional in kernel-only mode.

## 9. Where to go next

- `docs/guides/org_runtime_quickstart.md`, runtime ops cheat sheet
- `docs/guides/runtime_smoke_test.md`, how to validate after upgrades
- `AGENTS.md` §4z, autonomy directive (read this before letting an
  agent run unattended)

If you find a bug in the kernel: open an issue or PR upstream. If your
instantiation behaves badly but the kernel passes the fork-smoke test,
the bug is in your config, not the substrate.
