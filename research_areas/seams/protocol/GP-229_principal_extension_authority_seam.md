# GP-229 — Principal-Extension Authority + Bootstrap Asymmetry

> **Seam metadata** · `seam_id:` GP-229 · `track:` protocol · `status:` active - opened 2026-05-07 · `last_updated:` 2026-05-09


**Status:** active — opened 2026-05-07
**Owner:** principal
**Parents:** GP-128 (persistent-agent daemon), GP-167 (multi-agent interface), GP-191 (org kernel/policy boundary)
**Related:** GP-228 (substrate-portfolio + SRO role)

## Eigenquestion

The ZTARE Research Co org-runtime enforces role mandates on daemon-spawned agents (per GP-128). But local interactive sessions — Claude Code, Codex CLI, the principal at the keyboard — operate without that enforcement. The same agent (Claude / Codex) acting in those two contexts is governed differently, and one context literally builds the governance system the other context enforces. **Is this asymmetry a bug or a feature, and how do we name it deliberately so it doesn't drift into accidental shadow-work?**

## The asymmetry, named explicitly

There are TWO modes of agent operation in this system:

### Mode 1 — Principal-extension (interactive)

When the principal directly invokes an agent (you typing in your terminal, talking to Claude Code or Codex), the agent operates as a **principal-extension**. It inherits the principal's authority, which per `org/roles/principal.yaml` is the root authority — broader than any sub-role.

Concretely:
- The agent CAN write to any path the principal could write to (effectively all of `src/`, `org/`, `tenants/`, `research_areas/`, etc., subject to AGENTS.md universal constraints)
- The agent is NOT bound by sub-role `forbidden_paths` (it's not acting AS a sub-role)
- The agent IS bound by:
  - AGENTS.md §0–§5b decisive rules (no `--no-verify`, no destructive-without-confirm, no API key exfiltration, etc.)
  - Repo-wide invariants (MIT license, gitignore boundaries, etc.)
  - The principal's explicit directives in this session

### Mode 2 — Daemon-spawned role-bound (autonomous)

When `agent_daemon.py --role <role_id>` dispatches a task to claude/codex CLI, the spawned agent operates **as that role**. It's bound by:
- The role's `authorized_paths` and `forbidden_paths` typed contracts
- The role's mandate body (the .md file)
- The role's budget caps + agent-utilization caps
- The gate flow: actions go through `ztare_workspace/gates/pending/` for approval before execution

Mode 2 is the production pattern. Mode 1 is the development / governance-bootstrap pattern.

## Why both must exist

The bootstrap paradox: you cannot have a perfectly governed system from day 1, because someone has to write the mandates, the role yamls, the kernel code that enforces them. That work itself can't be governed by the system being built.

This is the same reason A kernel maintainer does not submit patches through the same CI pipeline they review them through. The maintainer's authority is broader than the contributor's authority, by design.

For ZTARE Research Co specifically: the interactive Claude/Codex sessions write seams, draft mandates, refactor `src/`, and bootstrap new tenants. The VPS daemon enforces the resulting mandates on autonomous work. Both lanes coexist.

## What's incompatible (the audit gap)

| Property | Mode 1 (principal-extension) | Mode 2 (role-bound) |
|---|---|---|
| Forbidden-paths enforcement | ✗ none | ✓ strict |
| Authorized-paths enforcement | ✗ none | ✓ strict |
| Budget cap enforcement | ✗ none | ✓ strict |
| `org/sessions/<role_id>/` writes | ✗ none | ✓ every tick |
| `transitions.jsonl` writes | ✗ none | ✓ on action |
| Telegram approval gate | ✗ none | ✓ default |
| Damage-signal scan | ✗ none | ✓ pre-tick |

The first three are correct asymmetries (principal authority IS broader). The last four are the **audit gap**: principal-extension work doesn't leave the structured trail that daemon work does.

## Closure: minimum discipline to close the audit gap

The fix is light-weight — make the asymmetry deliberate rather than accidental.

### Discipline 1 — Session-end log entry

When a principal-extension session does substantive work (writes to `src/`, `org/`, `tenants/`, or `research_areas/`), at session-end the agent appends a one-line summary to `org/sessions/principal/<date>/transcript.md`:

```
2026-05-07T13:00Z | claude | wrote tenants/ztare/roles/self_recursive_orchestrator.yaml + mandate; pushed to ztare-research-co; rsynced 2 files to VPS
```

This is **manual discipline for v0**. Automation deferred until drift becomes a problem.

### Discipline 2 — Daemon-spawned vs interactive disambiguation

When an agent (Claude / Codex) is unsure which mode it's in, the heuristic:
- Was this prompt initiated by the principal directly typing? → Mode 1 (principal-extension)
- Was this prompt injected by `agent_daemon.py` with role context? → Mode 2 (role-bound)

If unclear, default to the more restrictive interpretation (Mode 2).

### Discipline 3 — AGENTS.md clarification

A new section in AGENTS.md (§5c or similar) names this distinction so any agent reading it on cold-start knows which mode applies.

## Strange-loop implications (per GP-228)

The user's stated goal for the SRO PoC is to test in-loop AND out-of-loop self-recursive improvement. For that to be a real strange loop:
- The IN-loop test: a substrate iter proposes an architectural change (via `propose_substrate_architecture_change` mechanism in v3 charter). The SRO daemon surfaces it. Principal-extension OR daemon-with-elevated-mandate executes it.
- The OUT-of-loop test: the SRO daemon, between substrate runs, identifies a meta-level pattern (rotation needed, charter patch ready) and proposes/executes it.

The original SRO mandate I authored (Task #183) blocked `src/` writes entirely. **That defeats the in-loop test** — substrates can propose src/ changes via v3 mechanisms, but no role can execute them autonomously, so the loop doesn't close.

Adjustment per principal direction (GP-229 + Task #190): SRO mandate gets a **review-gated src/ path**. Direct writes still forbidden, but src/ changes via a typed proposal that passes:
1. Cross-family LLM review (claude reviews codex-authored diff, vice versa)
2. Budget-cap check
3. Transition log entry
... can be applied autonomously. The principal can `STOP` from Telegram at any point.

The strange-loop closes when the SRO can act on its own substrate's `propose_substrate_architecture_change` outputs without principal intervention — but only when the proposal passes the review-gate.

## Closure conditions

GP-229 closes when:

(a) AGENTS.md is updated with §5c (or similar) naming Mode 1 / Mode 2

(b) The SRO mandate is updated to reflect the review-gated src/ path (Task #190)

(c) Discipline 1 (session-end log) has been observed in at least 5 principal-extension sessions, OR a tooling automation makes it unnecessary

(d) The first daemon-spawned strange-loop iter completes (substrate proposes src/ change → cross-family review approves → SRO applies → next iter incorporates)

## Cross-references

- `org/roles/principal.yaml` — root-authority role
- `org/roles/self_recursive_orchestrator.yaml` (in tenant overlay) — the role this seam reshapes
- `tenants/ztare/mandates/self_recursive_orchestrator_mandate.md` — mandate to be updated
- `research_areas/private/seams/reflexive/GP-228_substrate_portfolio_v05_v3_seam.md` — strange-loop architecture
- `research_areas/private/seams/protocol/GP-191_org_kernel_policy_boundary_seam.md` — kernel/policy boundary
- `scripts/public/control/agent_daemon.py` — Mode 2 dispatcher
- AGENTS.md §5c (TBD) — Mode 1 / Mode 2 rules
