# GP-192 — Enterprise-Grade Org Runtime Requirements

> **Seam metadata** · `seam_id:` GP-192 · `track:` protocol · `status:` open · `last_updated:` 2026-05-09


**Status:** open
**Opened:** 2026-05-01
**Owner:** principal + role.research_director (design) + role.engineer (build)
**Related:**
- `research_areas/private/seams/protocol/GP-191_org_kernel_policy_boundary_seam.md` — kernel/policy boundary that THIS seam respects
- `research_areas/ZTARE_BOARD.md` — ENT-001 row (deferred until local dogfood survives)
- `priority_roadmap.md` — P2 "Enterprise control plane design"
- `docs/concepts/ztare_research_company_architecture.md` §"Backend Decision" — already names the filesystem→Postgres future
- `docs/internal/orbit_dashboard_audit_2026-04-30.md` S4 — Bearer token auth (the only enterprise-style guard shipped today)

---

## Eigenquestion

The org runtime works as solo-principal dogfood. ENT-001 is deferred until that
dogfood survives unattended runs. **What is the smallest enterprise-grade
definition along each of the seven axes — leases, RBAC/SSO, signed audit,
event outbox, multi-server, observability, recovery — such that a serious
external organization can adopt the org runtime without being forced into a
maximalist platform rewrite?**

This is a debate seam, not a spec. The output is a list of crisp axis
definitions + reactivation triggers, not a build plan. Each axis ends with a
decision rule that tells a future agent when the local dogfood path has
outgrown its current implementation and needs the enterprise variant.

The 90/20 mandate applies: name the smallest version that gives 90% of the
value, not the consultant-grade maximalist version.

---

## Bounded Thesis

The thesis supported by current evidence is narrow:

> The seven axes name **structural debts** the filesystem-first runtime
> currently carries. Each debt is acceptable today (solo principal, single
> server, trusted operator). Each debt becomes blocking at a different
> threshold. The seam's job is to name the threshold per axis so the team
> does not over-build (premature Postgres migration) or under-build
> (multi-tenant deployment with no audit signing).

The thesis NOT supported:
- That all seven axes need to land in the same release.
- That a single backend choice (Postgres / SQLite / object storage) closes
  all seven debts. Several axes are orthogonal to backend.
- That enterprise-readiness is about polish; it is about behavior under
  failure, contention, and adversarial use.
- That this seam should pre-decide vendors (Auth0 vs Keycloak vs custom,
  Sentry vs OpenTelemetry vs custom). Vendor choice is a spec-stage
  decision; this seam names what behavior is required.

---

## Axis Inventory

For each axis: **what's there today / what enterprise-grade actually means /
when the threshold flips / what 90% of the value looks like**.

### Axis 1 — Leases

**Today.** Two daemons (manager + research_director) read the same gate inbox
and the same task queue. Coordination is by filesystem timing alone. If both
daemons attempt to claim the same task in the same tick, the second `mv` of
the pending file fails silently and the first daemon proceeds — best-effort
cooperative concurrency.

**Enterprise-grade definition.** A lease is a fencing token: when daemon A
claims task T at version V, no other process can complete actions on T at
versions < V even if A becomes a zombie. The system can tell, deterministically,
which daemon currently owns each task and for how long.

**Threshold flips when.** Two daemons run on different hosts (true
multi-server, not just two containers on one filesystem). Filesystem rename
atomicity stops being sufficient because the filesystem itself is not the
shared substrate.

**90% of the value.** A `claims/` directory with one file per active claim,
holding `{task_id, owner_id, expires_utc, fencing_token}`. Daemons must hold a
non-expired claim to act on a task; reading it back asserts "I am still the
owner." Expiry is wall-clock; renewal is a write. No distributed-consensus
machinery; the filesystem's atomic rename is the lock primitive at v1; a
small Postgres `SELECT FOR UPDATE` is the v2 if/when multi-host lands.

**Reactivation trigger.** The first time a daemon ticks on a host other than
the principal's laptop and writes to a shared volume.

### Axis 2 — RBAC / SSO

**Today.** Single principal. The Orbit API has an optional Bearer token
(`ORBIT_API_TOKEN`); the Telegram bot has a chat-id allowlist of size one.
There is no notion of "user X may approve gate kind Y but not Z." All
authority collapses into "is the principal."

**Enterprise-grade definition.** A user identity (preferably from an external
IdP via OIDC), mapped to one or more roles with explicit signing capabilities.
A gate type carries a list of `signs_gates` it requires; only users whose
roles include those types may resolve gates of that type. The audit row
records which identity resolved each gate, not just "orbit" or "telegram."

**Threshold flips when.** Two humans need to operate the org runtime against
the same dogfood instance, OR a single principal needs the system to enforce
their own role boundaries (e.g., "I as principal cannot accidentally
co-sign a gate that requires both reviewer and engineer.")

**90% of the value.**
- Add `actor_id` to every audit row (today it is `'orbit'` / `'telegram'`).
- Add a static `org/users.yaml` mapping `user_id → role_ids` (no IdP yet —
  static is fine for v1).
- Map Orbit's Bearer token to a user_id (one token per user, not one shared).
- Map Telegram's chat-id check from "single allowlist" to "lookup against
  users.yaml".
- Defer OIDC and group sync until the static yaml proves painful (it will,
  for >5 users or any external auditor requirement).

**Reactivation trigger.** First request to share Orbit access with a second
operator, OR a compliance ask that says "show me which user approved this."

### Axis 3 — Signed audit

**Today.** `ztare_workspace/transitions.jsonl` is append-only by convention.
Any process with write access can edit it freely. Git tracks the file, which
is a soft tamper-evident layer (rewrites show in `git log`), but a malicious
process can rewrite history before the next commit.

**Enterprise-grade definition.** Each transition row carries a hash of the
prior row's content (Merkle chain). Verification can prove that any segment
of the log has not been edited since it was written. Optional: per-row
signatures from the actor's identity (signed audit, not just chained).

**Threshold flips when.** External auditor / regulator requests proof of
non-tampering, OR a multi-user environment introduces non-trusted writers
(e.g., a worker daemon that should not be able to retroactively edit its own
past).

**90% of the value.**
- Add a `prev_row_sha256` field to every `transitions.jsonl` row.
- Ship a verifier: `scripts/public/audit_chain_verify.py` that walks the log and
  fails on the first broken link.
- Run the verifier in CI on every commit that touches `transitions.jsonl`.
- Defer signing (per-row HMAC or asymmetric signature) until users.yaml
  introduces multi-actor identity.

**Reactivation trigger.** First time the integrity of the audit log matters
to anyone other than the principal.

### Axis 4 — Event outbox

**Today.** When a gate is resolved, two writes happen synchronously: the
resolved JSON file and the transitions.jsonl row. Downstream effects (e.g.,
"the closure daemon should pick up the resolution and act on it") happen via
filesystem polling. No retry, no at-least-once delivery, no dead-letter
queue.

**Enterprise-grade definition.** The atomic act is "append a row to an
outbox table"; downstream consumers (mailers, slackers, external webhooks)
dequeue from the outbox with at-least-once semantics, retry on failure, and
land in a DLQ after N attempts. The producer is freed from worrying about
downstream availability.

**Threshold flips when.** A gate resolution must trigger a side effect that
itself might be flaky — e.g., post a Slack message, send an email, fire a
webhook to an external CI. Filesystem polling is OK for an in-process
closure daemon; it is not OK for cross-network effects.

**90% of the value.**
- Add `ztare_workspace/outbox/<event_type>/<id>.json` directories.
- Producers append to outbox in addition to their primary write.
- A small dispatcher (one per event_type, can run as a daemon) reads, calls
  the side effect, and renames to `outbox/<event_type>/.delivered/`.
- Failure: rename to `.failed/<id>.<attempt>.json` with retry count + last
  error; eventually move to `.dlq/`.
- This is the same shape as `gates/pending` → `gates/resolved`. Reuse the
  pattern.

**Reactivation trigger.** First wired side effect that crosses a network
boundary or an external system.

### Axis 5 — Multi-server

**Today.** Single host. Multiple daemon processes share the same volume.
Lease (Axis 1), audit signing (Axis 3), and outbox (Axis 4) all assume a
single shared filesystem.

**Enterprise-grade definition.** Two or more hosts cooperate on the same org
runtime instance with no shared filesystem. State is in a database, the
outbox is networked, and leases use fencing tokens that survive a host
rebooting.

**Threshold flips when.** The principal needs the org runtime to keep
running while their laptop is offline AND the VPS is offline AND a fresh
host comes up — i.e., true HA, not just "always-on on one VPS."

**90% of the value (intermediate step).** "Two-host warm standby":
- Primary host runs daemons + Orbit + Telegram.
- Secondary host syncs `ztare_workspace/` via rsync or a network filesystem
  every N seconds.
- On primary failure, secondary takes over with a manual cutover. The
  cutover scripts is a checklist, not an automated election.
- This is HA-grade for solo principal; not HA-grade for multi-tenant SaaS.
- Beyond this step, the migration is filesystem → Postgres + a real outbox
  bus, and that is a v2 spec, not a 90% step.

**Reactivation trigger.** Single-VPS uptime becomes decisive for an
external commitment (paying customer, public dashboard, scheduled
publication).

### Axis 6 — Observability

**Today.** Each daemon writes free-form text to stdout, captured by Docker
or by tmux scrollback. No structured logs, no metrics, no traces. To answer
"is the manager daemon healthy?", the operator reads logs by hand.

**Enterprise-grade definition.** Three signals — metrics (counters,
gauges, histograms), structured logs (JSON, indexed), and traces
(request-id flowing across daemon boundaries). All three exposed via a
standard endpoint (Prometheus, OpenTelemetry, or the equivalent) so that
external dashboards and alerting tools work without bespoke integration.

**Threshold flips when.** Daemon health stops being self-evident from
human-tail-the-log. This happens at: 5+ daemons running, OR cross-daemon
investigation ("the manager retried 3 times — what did the engineer
do?"), OR a paging requirement ("alert me at 3am if a daemon dies").

**90% of the value.**
- Structured log: replace `console.log` and `print` with a small wrapper
  that emits one JSON object per event with `{ts, daemon, role_id,
  event_kind, ...}` to stdout. No log aggregator yet; just let JSON go to
  Docker stdout.
- Counters: each daemon writes
  `ztare_workspace/metrics/<daemon>/<counter>.json` once per tick with
  `{value, last_update_utc}`. Cheap, no Prometheus required.
- Health endpoint: `/api/health` already exists on Orbit. Each daemon should
  write `org/.heartbeat/<daemon>.json` with `{last_tick_utc, status}`; a
  small monitor checks they are recent.
- Defer OpenTelemetry / Prometheus / Sentry until the JSON logs prove hard
  to read.

**Reactivation trigger.** First time the principal cannot answer "is this
daemon stuck?" within 10 seconds by reading logs.

### Axis 7 — Recovery

**Today.** Recovery is "git reset to a known good commit and `git pull`."
This works because all canonical state is filesystem + git-tracked. It is
slow, lossy on uncommitted state, and assumes the disk itself is intact.

**Enterprise-grade definition.** Three properties:
- **Backup:** off-host snapshot of all canonical state, taken on a known
  cadence, retained for a known retention window.
- **PITR (point-in-time restore):** ability to roll forward or back to any
  commit / timestamp within the retention window without manual surgery.
- **DR (disaster recovery):** documented runbook + tested procedure for
  rebuilding the runtime on a fresh host within RTO/RPO budgets.

**Threshold flips when.** The cost of losing N hours of state crosses the
cost of the backup machinery. For a solo principal at v1, N hours is not
catastrophic; for a paying customer, N=5 minutes might be the SLA.

**90% of the value.**
- A daily `git push` of `ztare_workspace/` and `org/` to a private
  repository. Cron, not magic.
- A DR runbook in `docs/internal/dr_runbook.md` with the cutover steps:
  fresh host, install deps, clone the private repo, restart daemons,
  re-establish Orbit + Telegram tokens. Test it ONCE quarterly.
- Defer continuous backup, off-site replication, RTO/RPO commitments
  until a paying customer makes them decisive.

**Reactivation trigger.** First external commitment with a recovery SLA, OR
the first time a disk loss costs >1 day to recover from.

---

## Decision Principles

Across all seven axes, three rules apply.

### Rule A — Filesystem first, Postgres only when filesystem provably hurts

The current backend is filesystem + git. It is inspectable, recoverable, and
git-friendly. The temptation when adding any of the seven axes is "we should
just put it in Postgres." Resist that until the filesystem implementation is
shipped, lived-with, and proven painful. Postgres is a v2 step, not the v1
baseline.

The exception: the moment Axis 5 reactivates (true multi-host with no
shared filesystem), Postgres or an equivalent network-addressable store
becomes mandatory for the affected axes. Until then, it is premature.

### Rule B — Each axis closes independently

Do not bundle. A team should be able to ship Axis 3 (signed audit) without
also shipping Axis 6 (observability). The 90% definitions above are
intentionally orthogonal so closures can interleave.

### Rule C — Reactivation triggers are objective, not aspirational

A trigger like "when scale demands it" is useless. Each trigger above names
a concrete event. Closure of the seam happens when the event occurs and is
documented; until then, the axis stays in design.

---

## Migration Path (intentionally not a spec)

The eight Org-track tasks (Org-1 through Org-8 in the current sprint) close
the dogfood loop. This seam exists so that **after** the dogfood loop is
proven, the team has a pre-staged design for what enterprise-grade actually
means — without that pre-stage, the temptation will be to either over-build
(rewrite to Postgres + Kubernetes + Auth0 in one heroic sprint) or
under-build (declare the dogfood "good enough" for paying customers).

A plausible sequence after dogfood closure:

1. **Axis 6 (observability) first** — the cheapest, structured logs cost
   little, and you cannot tell whether the other axes are stressed without
   them.
2. **Axis 3 (signed audit) second** — also cheap (Merkle chain + verifier),
   and unlocks the conversation with any external party who asks "can you
   prove your audit log is honest."
3. **Axis 1 (leases) third** — when a second daemon host is added, this
   becomes mandatory; ship before the second host, not after.
4. **Axis 2 (RBAC / static users.yaml) fourth** — when the second human
   needs access.
5. **Axis 4 (event outbox) fifth** — when the first cross-network side
   effect is wired.
6. **Axis 7 (recovery / DR runbook) sixth** — when an external commitment
   makes RTO matter.
7. **Axis 5 (true multi-host) last** — only after axes 1–4 are stable.

This sequence is a guess, not a commitment. The actual order will be driven
by which reactivation trigger fires first.

---

## What This Seam Does NOT Do

- It does not pick vendors (Auth0 / Keycloak / Sentry / Datadog / Postgres
  / SQLite / etc.).
- It does not commit to a timeline. ENT-001 stays deferred on the board.
- It does not propose changes to any current daemon. The dogfood loop
  remains the sprint's focus.
- It does not claim that closure of all seven axes is necessary or
  sufficient for "enterprise readiness." Real enterprise readiness requires
  also: legal review, contractual SLAs, security review, pen-testing, and
  data-residency compliance — none of which this seam addresses.
- It does not assume the org runtime kernel and the ZTARE evaluation kernel
  will share enterprise infrastructure. They are sibling kernels (per
  GP-191) and may end up with sibling enterprise stacks. Not pre-decided.

---

## Open Questions (intentionally left open)

| Question | Why it stays open |
|---|---|
| Do we ship our own audit signing or use an existing tool (e.g., Sigstore, Auditbeat)? | Vendor choice; spec stage |
| Is the v2 backend Postgres, SQLite-with-WAL-replication, or an event store (e.g., EventStoreDB)? | Depends on which axis reactivates first; do not pre-decide |
| Is multi-tenancy a future requirement at all? | Solo-principal dogfood does not answer this; only revisit when a second tenant is on the horizon |
| Does the kernel/policy split (GP-191) extend to enterprise infrastructure (e.g., separate Postgres schemas per policy adapter)? | Open architectural question — answer when the ZTARE adapter is the second adapter, not the only one |

---

## Closure Conditions

GP-192 closes when one of the following is true:

(a) All seven axes have either shipped their 90% version OR have a closed
    decision-not-to-ship with explicit rationale.

(b) The seam is superseded by a more concrete spec (e.g., GP-XXX
    "enterprise-grade-v1 spec") that picks vendors and ships an integrated
    plan.

(c) Operator decides enterprise-grade is not the product path — the org
    runtime stays a solo / small-team tool. Close as `deferred` with
    explicit rationale.

Until then: the seam stays open as the architectural anchor for any agent
who asks "should I build X as enterprise-grade or as dogfood?" The answer
is in the 90% definition + reactivation trigger for the relevant axis.

---

## Cross-References

- **GP-191 Org Kernel / Policy Boundary** — kernel-pure org primitives are
  what this seam scales; ZTARE-policy-coupled artifacts are NOT in scope
  for the seven axes (those move under their own policy adapter when
  enterprise lands).
- **`research_areas/ZTARE_BOARD.md` ENT-001** — the deferred row this seam
  feeds when reactivated.
- **`priority_roadmap.md` P2 "Enterprise control plane design"** — same.
- **`docs/concepts/ztare_research_company_architecture.md` §"Backend
  Decision"** — names the filesystem→Postgres future at a high level; this
  seam decomposes it into seven independent axes.
