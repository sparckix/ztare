# GP-231 — MCP-bridged third-party app integration

> **Seam metadata** · `seam_id:` GP-231 · `track:` mission · `status:` Open. Substrate evaluation pending alongside GP-230. Priorit · `last_updated:` 2026-05-08


**Status:** open
**Created:** 2026-05-07
**Owner:** principal + research_director
**Related:** GP-230 (absorption from 2026 governance wave), cognitive-firm OS/Config/App split

## Eigenquestion

The current cognitive-firm system of record is filesystem + git history. That choice is right for the kernel-development phase: every action is inspectable as a text file, replayable from git, and survives any tooling-layer crash because the truth is on disk. But for enterprise adoption, two structural needs emerge that the filesystem-only model does not address:

1. **Read-side integration with existing enterprise data** — ERPs (SAP, Oracle, NetSuite), CRMs (Salesforce, HubSpot), ticketing (Jira, Linear, ServiceNow), comms (Slack, Teams), calendars, document stores. A cognitive-firm running inside an enterprise needs to consume these as authoritative sources, not duplicate them on local disk.
2. **Write-side integration with the same systems** — when a role's task closes, the closure may need to land as a Salesforce activity record, a Jira transition, a Slack message in a specific channel. The org's transition log is one substrate; the enterprise's records of truth are another.

The eigenquestion: **what is the cleanest boundary at which cognitive-firm bridges to third-party enterprise systems without losing the OS/Config/App separation?**

## The candidate answer: MCP at the App layer

MCP (Model Context Protocol) is the obvious candidate primitive. It is already designed for the read/write/tool-call pattern, has reference servers for the major enterprise systems, and runs in the right architectural slot: not at the OS layer (which must remain deterministic and substrate-agnostic), not at the Config layer (which holds typed contracts), but at the App layer where agents do their work.

The proposed boundary:

- **OS layer (unchanged):** filesystem + git history remain the system-of-record for governance state — roles, mandates, gates, transitions, signals. This is the kernel and stays decisive.
- **Config layer (light extension):** `mandate.authorized_mcp_servers` becomes a typed field listing which MCP servers a role is allowed to invoke. Same shape as `authorized_paths` but for tool capabilities. Approved at mandate-edit time, not per-call.
- **App layer (new bridge):** the agent runtime gains an MCP client. Each tool call through MCP records a transition in the OS layer with the server name + tool name + redacted payload, so the audit trail still answers "what did this role do?" even when the doing happened inside a third-party system.
- **Sync direction:** read-mostly from external systems (the kernel pulls context, the agent reasons over it, the kernel records what was pulled). Writes are gated like any other authorized-paths-style action: principal approval at mandate-edit time + audit-log entry at write-time.

## Why this is not just "wrap MCP and ship"

Three sub-questions need substrate-evaluation before a single PR lands:

### S1. Where does the truth live for hybrid state?
If a Jira ticket transitions from "In Progress" to "Done" via the kernel, and somebody also transitions the same ticket via the Jira UI, which is the truth? Two viable answers:
- **External-authoritative:** the third-party system is the truth; kernel transitions log "we attempted X" and reconcile against the external system on next read.
- **Kernel-authoritative-mirror:** kernel transitions are the truth, the bridge actively mirrors the kernel state into the external system, divergence is a damage signal.

Different enterprises will want different answers. The substrate run should evaluate which default is least surprising and what mandate field controls the override.

### S2. Where does authentication live?
MCP servers need auth. Three options:
- Per-role credential store inside `org/`. Convenient but ties auth to the kernel filesystem (the very brittleness we are trying to avoid).
- Per-tenant credential store at the OS layer (vault-style). Cleaner separation but requires the OS layer to grow a secret-management primitive.
- Delegate to the enterprise's existing IdP (OIDC / SAML) and assume MCP servers federate. Cleanest at scale, hardest to bootstrap.

Substrate question: which option's threat model and operational shape fits the M-Form invariant best?

### S3. What about latency + failure modes?
Filesystem reads are microseconds; MCP calls to a remote ERP are seconds-to-minutes. The agent daemon's tick loop assumes work-discovery is fast. If a role's `discover_all` takes 30 seconds because it has to query Salesforce, the whole loop slows. Two-tier discovery (fast: local files; slow: scheduled MCP polls) may be the right shape.

## Why this is brittleness-driven, not feature-creep

The user's framing matters: we are not adding ERP/CRM connectors because some adopter asked. We are addressing a structural fragility — filesystem-as-truth assumes the kernel owns all the data the org reasons over, and a real enterprise org reasons over data that lives in systems older than the cognitive-firm install. The connector is the bridge that lets the kernel remain governance-of-record while the data-of-record stays where the enterprise already keeps it.

This is the same separation that makes the Linux kernel filesystem-based without forcing every application's truth onto disk: applications mount whatever they want and the kernel governs the access pattern.

## Proposed shape

- New mandate field: `authorized_mcp_servers: [list]` per role.
- New role-extension subdirectory: `src/cognitive_firm/role_extensions/mcp_bridge/` with one Python module per supported server class (read-only by default).
- New transition type: `mcp_call` recording server name, tool, redacted payload, success/failure, latency.
- New damage-signal class: `external_system_divergence` for S1's reconciliation case.
- Two-tier discovery API at the daemon level: `discover_local()` (fast, every tick) and `discover_external(role)` (slow, scheduled via separate cadence per `mandate.mcp_poll_interval_minutes`).

## Closure criteria

- S1 / S2 / S3 each have a written verdict with a substrate-run hash backing the choice.
- One MCP server class shipped end-to-end (proposed: read-only Linear, since it already has a reference MCP server and the parent project already uses Linear-shaped tracking).
- Audit trail demonstrably answers "what did role X do across kernel + external systems?" by joining `transitions.jsonl` with `mcp_call` entries.
- Failure-mode story: external system unreachable → role-tick continues, damage signal raised, principal sees it in Orbit.

## Status

Open. Substrate evaluation pending alongside GP-230. Prioritize S1 (truth-location semantics) before S2 (auth) and S3 (latency), since S1 is the architectural decision and S2/S3 are implementation choices that follow from it.

---

## 2026-05-07 Panel verdict + revised architecture

Three adversarial panels reviewed this seam (enterprise-security architect at regulated FinSvcs, principal distributed-systems engineer, M-Form invariant auditor). They independently converged on the same finding: **the original three-options framing of S1 is wrong**, and the architecture that survives all three threat models is the **transactional outbox** pattern grounded in the M-Form's existing `transitions.jsonl` + git history.

### What the original seam got wrong

1. **S1 is a category error (M-Form auditor).** The kernel's job under M-Form is to govern *action*, not to mirror *state*. Asking "is the kernel or the third-party system the source of truth for state?" presumes state-mirroring is a kernel responsibility. It is not. The kernel records `role X attempted action W under mandate M at time T`; the world's state is whatever the world's state is. Divergence is the steady state, not a damage signal.
2. **All three implementations had dual-write hazards (distributed-systems skeptic).** External-authoritative loses writes under partition (transition logged but RPC lost or vice versa). Kernel-authoritative-mirror inherits a replication problem with no 2PC. Per-mandate-field choice multiplies the failure surface. None of the three is shippable.
3. **Config-layer treats MCP servers as path-globs (enterprise architect).** `authorized_mcp_servers: [list of names]` is an outbound trust delegation, not a reference. A server name is a moving target across vendor releases.

### The architecture all three panels endorse

**Single source of truth: `transitions.jsonl` is the outbox.** The kernel writes one row per attempted action — that row IS the durable, ordered, append-only commitment. Any external dispatch is downstream:

- **OS layer (unchanged):** filesystem + git history + `transitions.jsonl`. Continues to be deterministic and substrate-agnostic.
- **Config layer (extended):** mandate now carries **capability tokens**, not server names. Each token is principal-signed and includes `(server_digest, tool_manifest_hash, declared_egress, response_projection_id)`. The projection ID names a deterministic function `mcp_response → transition_class` so ambiguous returns are rejected, not LLM-interpreted (closes the T2 break).
- **App layer (new primitive):** an **outbox-relay** process reads pending `mcp_call` rows from `transitions.jsonl`, computes a deterministic idempotency key from the transition hash, issues the call to the MCP server, marks the row dispatched. Idempotent retries on transient failure. Crash-safe by construction. Audit-replayable.
- **Polling (revised):** removed from OS. The App-layer daemon polls; results arrive at the OS layer as ordinary `external_observation` transitions, indistinguishable from filesystem events.

### Sub-question resolutions

- **S1 dissolved.** Not a real architectural choice; the kernel governs action, not state. Divergence audits compare *attempted-action log* to *world state on read*; mismatch is a fact about reality, not a kernel failure mode.
- **S2 — IdP federation is correct (M-Form auditor + enterprise architect agree).** Mandate authorizes `role R may invoke server S under federated identity I`; IdP resolves `I → short-lived credential` per call. Refresh tokens never live in `org/`. Mandate edits revoke immediately and cannot be replayed. T1 (principal-independence) is preserved because the principal still signs the capability-token mandate; IdP cannot edit mandates.
- **S3 — two-tier discovery moves entirely to App-layer.** OS layer sees only the resulting transition.

### Supply-chain primitives the seam under-specified

The enterprise architect's decisive question — *what prevents a malicious MCP-server update from executing?* — requires:

1. **Server digest pin** at the Config layer (not a name; an immutable image digest + signed tool manifest hash).
2. **Revocation feed** the daemon checks each tick; quarantines any pinned server whose digest is on the feed.
3. **Declared-egress allowlist** enforced at the network layer (firewall / iptables egress rules), not the agent layer.
4. **Data-residency tag** on each `mcp_call` transition for cross-tenant audit.

### Damage-signal classes (final)

- `mcp_call_dispatched_but_unverified` — relay issued the call, server did not return a confirmation within the timeout; surfaces with the deterministic idempotency key for replay analysis.
- `mcp_response_unprojectable` — server returned a response that the deterministic projection function could not classify; rejected, transition marked failed, principal review.
- `mcp_server_revoked` — pinned digest appeared on the revocation feed; quarantine active.
- `external_observation_diverged` — attempted-action log says role X moved Jira ticket #N, current Jira read says it did not move. Informational, not a kernel failure.

### Phase-gated implementation order

1. **Phase 1 (this PR):** Outbox-relay primitive in cognitive-firm App layer. Single read-only MCP server class as proof (Linear, since it has a reference MCP server and minimal supply-chain surface). No write semantics yet.
2. **Phase 2:** Capability-token mandate field + deterministic projection function registry. First write-capable server class (still scoped: read + create-only, no edit/delete).
3. **Phase 3:** Supply-chain primitives (digest pinning, revocation feed, declared-egress).
4. **Phase 4:** IdP federation for S2.

Phases 2–4 are speculative until a concrete adopter's threat model justifies the work. Phase 1 ships now because the outbox-relay is independently decisive for cognitive-firm's own audit guarantees, with or without enterprise demand.

### Closure criteria (revised)

Each phase closes with: a primitive shipped behind a feature flag, a smoke test that exercises the primitive end-to-end against a real MCP server, an audit-trail demonstration showing the `transitions.jsonl` row pre-dates the external dispatch in every successful case, and a damage-signal demonstration showing the right signal fires under each named failure mode.
