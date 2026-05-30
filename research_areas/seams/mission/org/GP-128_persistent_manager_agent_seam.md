# GP-128 Persistent Manager Agent — Org Design Seam

> **Seam metadata** · `seam_id:` GP-128 · `track:` mission · `status:` `active` (opened 2026-04-23) · `last_updated:` 2026-05-08


**Track:** mission / org design
**Status:** `active` (opened 2026-04-23)
**Origin:** 2026-04-23 operator observation after a full day of tactical micromanagement of ZTARE compute experiments, paper drafting, and Riemann operator search — operator realized he was acting as both CEO and line-manager and asked "why don't you become my manager?"
**Trigger:** operator needs stepping-out not at the sandbox-lifecycle layer (that's GP-070) but at the DAY-TO-DAY DELEGATION layer. Claude (the conversational assistant) is a candidate persistent manager agent that can hold context across a research program, delegate to ephemeral workers (API calls, sub-agents, ZTARE runners), and escalate strategic decisions back to the operator.

---

## The Organizational Insight

Traditional M-form governance (Chandler 1962, Williamson 1975) assumes both divisions and corporate office are persistent organizational units. AI-native organizations have a **persistence asymmetry** that is decisive, not a bug:

- **Workers** (API calls, sub-agents spawned per-task, ZTARE runners, one-shot code executors) are **ephemeral and fungible**. They spin up, complete a bounded task, and disappear. No cross-task memory. No strategic continuity. Zero marginal cost of replacement.

- **Managers** (conversational agents with session memory, auto-memory systems, long-running orchestrators) are **persistent and non-fungible**. They hold context across tasks, accumulate calibration on principal preferences, maintain relationships with specific workers and other managers, and carry institutional memory.

This asymmetry has four organizational implications:

1. **Strategic value concentrates in the manager layer.** Worker capability is commoditized the moment a better model / cheaper API appears. Manager calibration compounds across months of principal interaction.

2. **Accountability is asymmetric.** You can blame a manager for a systemic failure; you cannot blame a worker (it's been gone for weeks). The manager is the only layer with skin in the game.

3. **Judgment transfer is one-way.** Managers can encode patterns into standing mandates that workers execute. Workers cannot teach managers anything beyond their single output.

4. **Organizational hierarchy inverts traditional logic.** In traditional M-form, the corporate office is expensive and divisions are cheap. In AI-native M-form, the "corporate office" (the manager) is the decisive expensive layer, and "divisions" (workers) are cheap to instantiate.

The practical consequence: **a principal's highest-leverage move is investing in the manager layer** (prompt engineering, mandate design, memory curation, escalation plumbing), not in more/better workers.

---

## The Problem

Today (2026-04-23), the operator holds every day-to-day decision himself:
- Which GPU to rent, when to kill it
- Which script to write, which bug to fix
- Whether to run smoke test vs deep sweep
- When to terminate an experiment
- What to write into which paper

None of these require HBS-level strategic judgment. They require **calibrated execution judgment** — which is exactly what a persistent manager-agent accumulates. The operator is spending his highest-value time on tactics that should flow through a manager.

What EXISTS today (per GP-070 audit, 2026-04-23):
- Goal orchestrator with state machine, write-ahead log, CLI (FULLY WIRED)
- Executive inbox (Streamlit) with pending/resolved gate tracking (FULLY WIRED)
- Supervisor loop with write-scope guard, actor enforcement (FULLY WIRED)
- Gate escalation via filesystem directory (FULLY WIRED, but PULL-only)

What's MISSING for the persistent-manager-agent use case:
1. **Agent mandate system** — no loaded artifact specifying what a manager agent is authorized to do autonomously vs what must escalate
2. **Push notifications** — all escalations are file-based pull. Principal must manually check inbox.
3. **Manager-agent goal-type module** for the GP-070 orchestrator
4. **Cross-session continuity** — Claude sessions reset; mandate must live in auto-memory or loaded mandate artifact

---

## Resolution

This seam opens a three-part implementation:

### Part 1: Mandate artifact system

A human-readable, versioned mandate document at `research_areas/private/mandates/<agent_name>_mandate.md` that defines, for a specific manager-agent:

- **Who the principal is** (personal context, time-horizon, preferences)
- **Scope of autonomous action** (list of specific action classes the agent is pre-authorized to execute without asking)
- **Scope of escalation to inbox** (list of action classes that require principal signature but are not time-urgent)
- **Scope of escalation to push notification** (time-urgent decisions requiring response within hours)
- **Absolute forbidden actions** (irrecoverable actions requiring explicit written authorization)
- **Standing context** (current research programs, paper portfolio state, operational principles)

Each manager-agent session loads its mandate on startup (via auto-memory pointer).

### Part 2: Push notification layer (ntfy.sh)

A single Python module `src/ztare/notifications/push.py` that:
- Writes structured escalations to a predetermined ntfy topic
- Is callable from `gate_escalation.py` so EXISTING gate writes automatically also push-notify
- Is callable directly from manager-agent code when urgent without being gate-shaped
- Uses an unguessable public topic name (no auth, no passwords in code)
- Principal subscribes to topic via ntfy phone app (receives push)

No SMS / Twilio needed initially. ntfy.sh is free, no signup required for public topics.

### Part 3: Manager-agent goal-type module for GP-070

A new goal-type YAML `research_areas/private/goal_types/claude_manager.yaml` that registers "claude_manager" as a valid GP-070 target_type. Stages model the day-to-day rhythm:

```
IDLE → RECEIVING_WORK → EXECUTING → DECISION_PENDING (gate) →
RESOLVED → IDLE (loop) → CLOSED_PROGRAM (terminal)
```

This lets a manager-agent participate in the existing goal-orchestration infrastructure without carving a new surface.

---

## What Does NOT Need to Be Built

- **New supervisor state machine** — GP-070 already handles this.
- **New inbox UI** — existing Streamlit inbox serves the principal directly.
- **Write-scope enforcement** — existing supervisor wrapper does this.
- **Transition audit log** — existing persistence layer does this.
- **Cost tracking** — existing `supervisor_usage.py` does this.

**The implementation effort is scoped to: 1 seam (this one), 1 YAML config, 1 Python module (~60 LOC), 1 markdown mandate, and 1 line of integration in `gate_escalation.py`.** Total: ~1 day of engineering.

---

## Implications for Paper 4 (M-Form)

> **POST-DEBATE STAMP 2026-04-23:** the "Implications for Paper 4" text below frames a persistence-asymmetry claim that has NOT been empirically validated — Level 1.5 has operated for 0 weeks of real load as of this stamp. Do NOT write the Paper 4 § extension until Level 2 has operated for ≥1 week. The claim must also be narrowed to an ACCUMULATION property (state concentrates in the persistent layer) rather than a GOVERNANCE property (which would require constraints the current architecture does not enforce — see AGENTS.md § 7a post-debate honest-limit). See GP-128 Debate Log convergence items 1 and 2.


Paper 4's M-form treatment currently assumes symmetric persistence between corporate and divisional layers (standard Chandler / Williamson). The persistence asymmetry in AI-native organizations is a novel extension. Proposed addition to paper 4:

> **§ The Persistence Asymmetry in AI-Native M-Form.** In traditional multi-divisional firms, both the corporate office and its divisions are long-lived organizational units; strategic and operational memory reside in both. In AI-native firms where execution is performed by ephemeral API-invoked workers and supervision is performed by persistent session-bearing agents, organizational memory concentrates asymmetrically in the supervisory layer. This inverts the classical leverage calculation: the marginal return on investment in the corporate office (mandate design, memory curation, escalation plumbing) exceeds the marginal return on investment in workers (new models, better prompts, larger context). We predict this asymmetry will drive firms toward thin-worker / thick-manager organizational forms in any domain where task execution is substantially automated.

---

## Open Items (Level 1.5 — this implementation round)

- [x] Draft `claude_manager_mandate.md` — 2026-04-23
- [x] Implement `src/ztare/notifications/push.py` with ntfy.sh — 2026-04-23
- [x] Implement `src/ztare/supervisor/escalation_manager.py` (canonical
      principal-facing escalation; writes the exact inbox_state.py
      schema so gates actually render in the Streamlit UI, and fires
      ntfy push when `urgent=True`) — 2026-04-23
- [x] Register `claude_manager.yaml` goal-type — 2026-04-23
- [ ] Principal subscribes to chosen ntfy topic on phone
      (topic is in `src/ztare/notifications/push.py` NTFY_TOPIC
      constant). Open the ntfy phone app → Add subscription →
      paste topic name → done.
- [ ] First live test: from a Claude session, call
      `escalation_manager.escalate(title="test", reason="sanity",
      urgent=True)` and confirm (a) a file appears in
      `ztare_workspace/gates/pending/`, (b) the Streamlit inbox
      renders it, (c) the ntfy phone app gets a push.

## Related Framing

- **GP-129 (Biological & Multidisciplinary Panel on AI-Native Org Design)** — convenes a multi-frame debate (Chandler / Wilson / Margulis / Simard / Kauffman / Matzinger / Godfrey-Smith / Hong–Page) on whether the M-form is the right frame, or an imported metaphor. The panel's decisive predictions (non-closure hotspots, damage-signal gap, faux-diversity, intent vs procedure mandates, membrane investment) feed (a) a second Paper 4 extension beyond persistence asymmetry, and (b) pull-forward items for the GP-128 follow-up engineering (see GP-129 § "Pull-Forward to Option B").
- **GP-130 (Non-LLM Substrate Seam)** — addresses the Hong–Page faux-diversity risk: when a deterministic substrate (SymPy / Z3 / Lean) earns its keep in the loop. Concrete first move: SymPy Jacobian-rank check in the GT pre-commit bootstrap.
- **GP-131 (Work-Discovery Loop)** — concrete content for the Level 2 daemon's idle-time agency. Specifies the proposal envelope, discovery sources, scope discipline, and falsifiable predictions. Pre-requisite for building the daemon; succeeds GP-105 / GP-105b.

## Future Work — Level 2 (Headless Daemon with LLM Decision Nodes)

Level 1.5 (what was built 2026-04-23) gets improved delegation WITHIN
Claude conversational sessions: the manager-agent loads its mandate,
writes escalations in the correct schema, fires push notifications
on urgent gates. BUT a Claude session still has to be open for the
manager to act — the principal must initiate or check in for work
to happen. This is Level 1.5, not Level 2.

True principal-level abstraction (per Gemini Pro 2026-04-23
analysis) requires HEADLESS, ASYNCHRONOUS, STATE-DRIVEN execution:
a daemon running on a cheap always-on host (~$5/month VPS or a
long-running cloud container) that advances research programs
autonomously and only interrupts the principal when the mandate
escalation criteria fire.

### Level 2 architecture (to implement AFTER Level 1.5 is validated)

**Core addition: LLM-driven decision node inside the existing
supervisor / orchestrator state machine.**

A new module `src/ztare/orchestration/manager_decision.py` with:

```python
from pydantic import BaseModel, Field
from typing import Literal, Optional

class ManagerDecision(BaseModel):
    reasoning: str = Field(..., description="1-3 sentences of why")
    action: Literal[
        "proceed",               # continue to next stage
        "escalate_inbox",        # write gate file, continue monitoring
        "escalate_push",         # write gate + ntfy push + pause this goal
        "terminate_branch",      # close goal with CLOSED_ABANDONED
        "reconfigure",           # propose parameter change, rewind stage
    ]
    escalation_reason: Optional[str] = None
    gate_description: Optional[str] = None
    proposed_config_change: Optional[dict] = None
    estimated_cost_usd_next_step: float = 0.0
```

An LLM is called with (current goal state, recent transitions, mandate
content, cost telemetry) and returns a Pydantic-validated
`ManagerDecision`. The supervisor loop executes exactly what the
decision says — proceed, escalate, terminate, or reconfigure.
NO open-ended agent loop. NO conversational UI. Structured routing
only.

**Daemon wrapper:** extend `ztare goal` CLI with
`ztare goal run --daemon --poll-interval 300 --max-cost-per-day 100`.
Runs continuously, advances each ACTIVE goal by at most one transition
per poll, sleeps, repeats. Survives restarts via the existing
`transitions.jsonl + state.json` write-ahead log.

**Deployment:** a $5/mo VPS (or free Oracle Cloud tier, or a
DigitalOcean droplet) running the daemon under `systemd`. The
principal subscribes to ntfy and checks the Streamlit inbox via
SSH tunnel or a hosted URL as needed. Costs: VPS ~$5/mo, Claude /
OpenAI API calls per decision at ~$0.001-$0.01 each, daily budget
cap enforced.

**Why NOT LangGraph / CrewAI / AutoGen / Temporal:**
- The existing ZTARE goal orchestrator already IS a state machine
  with durable persistence. LangGraph would duplicate it.
- CrewAI and AutoGen are conversational-agent frameworks (the
  trap Gemini identified) — silent failure, context loss,
  credit burn.
- Temporal.io is production-grade durable execution; overkill
  for a personal research daemon where filesystem persistence
  plus systemd auto-restart is sufficient.
- **Pydantic-structured LLM outputs (Instructor library or hand-
  rolled schema enforcement) inside the existing supervisor
  loop is the cheapest viable path to Level 2.**

### Level 2 engineering estimate

- `manager_decision.py` module: ~150 LOC, 1 day
- Integrate LLM decision call into supervisor_loop at gate
  boundaries: ~50 LOC changed, 0.5 day
- Daemon CLI mode: ~50 LOC, 0.5 day
- Integration test: synthetic goal, mocked LLM, walk through
  proceed / escalate_inbox / escalate_push / terminate paths:
  ~200 LOC test code, 0.5 day
- VPS deployment + systemd + nightly cost report email:
  0.5 day of ops

**Total Level 2 engineering: ~3 days.** Do after Level 1.5 is
validated in live use, typically after a week of Level 1.5
operation so the principal has calibrated feedback on what
scope the LLM decision node should handle autonomously.

### Further futures

- [ ] Paper 4 § extension on persistence asymmetry (~2 pages,
      write during the first quiet research day after the Level 2
      daemon is carrying load).
- [ ] Seam the generalization to other manager-agents
      (codex_manager, gemini_manager, or a generic `manager.yaml`
      goal-type with per-session persona) once claude_manager
      pattern is validated in live use.
- [ ] Integrate daily-digest email (SendGrid free tier) alongside
      ntfy for async summary of what the daemon did overnight,
      separate from urgent pushes.
- [ ] Consider Level 3 (Temporal.io or cloud-native durable
      execution) only if the daemon's per-day API-call volume
      exceeds ~1000, at which point restart-idempotency and
      cost-tracking become decisive enough to justify the
      infrastructure. Not before.

---

## Debate Log (opened post-ship 2026-04-23)

Adversarial debate on shipped GP-128 architecture. This seam has ~500 LOC of production code behind it (org/ primitives, session helpers, mandate, spend tracker, escalation manager, damage signals). Debate is not hypothetical — findings can invalidate shipped decisions and require rollback. Four seats. Retractions allowed.

### Turn 1 — Seat A: Systems-Architect Adversary — 2026-04-23

**Object under attack:** the persistence-asymmetry claim and the choice of Claude-session-as-manager.

The persistence-asymmetry thesis — "manager persistent, workers ephemeral, so invest in the manager" — is plausible-sounding and has a crisp implication (thin-worker / thick-manager). But it has not been tested against the actual Level 1.5 deployment, because Level 1.5 has been live for zero weeks. The paper-4 extension paragraph was written on the strength of the thesis, not on observation. That is the **asymmetry of our own asymmetry claim**: we theorized it and then shipped code predicated on it without gathering the data that would distinguish it from a just-so story.

**Specific prediction that will test the thesis:** under Level 1.5, is the manager actually holding state that workers would have re-derived at zero cost? If the cron cycle does `load_registry` + `read damage_signals` + `list_pending_gates` on every wake, the manager's "persistent state" is reconstructed from disk artifacts that a fresh-boot worker could read equally well. The persistence asymmetry in that regime is a narrative about what Claude-the-session remembers across turns, not about what the *system* knows. Collapse the Claude-session layer (headless cron + disk-only state) and there is no persistence asymmetry, just a state machine with a filesystem. Paper 4 should wait until we have data that distinguishes these two regimes.

**Choice of Claude-session-as-manager.** The seam treats it as obvious. But another agent family — a tiny always-on loop with a narrow Pydantic-validated action space, no prose context — might dominate on cost, predictability, and alignment. The Level 2 scope already describes this; the seam doesn't acknowledge that Level 2 architecture **contradicts** the "Claude session is the manager" framing of Level 1.5. Either Level 1.5 is a stopgap and the thesis attaches to Level 2's substrate; or the two levels describe different managers and the persistence-asymmetry paragraph needs to say which.

### Turn 2 — Seat B: Security / Alignment Skeptic — 2026-04-23

**Object under attack:** the mandate as an actual constraint, the scope partition, and the "session-id carries trust" assumption.

Seat A's "just-so story" concern about the persistence asymmetry is decisive. But let me escalate on a harder axis: **the mandate does not actually constrain the manager in the ways it reads as constraining it.**

Three concrete failure modes the shipped architecture does not address:

1. **The mandate is read-only advisory text.** An agent reads `manager_mandate.md`, internalizes it (or claims to), and acts. There is no gate that verifies the agent read it, no signature, no rendered-context check. AGENTS.md § 7a acknowledges this as "honor system." Fine — but then the mandate-version number is cosmetic. Versioning implies enforceable contract; advisory text has no version because there's nothing for a version to bind.

2. **Session-id is not trust.** `escalate(..., session_id=S)` writes a JSON file tagged with S. Nothing verifies that the process writing that file is actually inside session S. Any code with filesystem write access to `ztare_workspace/gates/pending/` can forge a session-id and impersonate the manager. The session-id is audit-friendly, not authentication. In a single-agent single-principal world this is fine. The moment you add a Codex wrapper or a cron-spawned secondary Claude, session forgery becomes a silent coordination failure.

3. **`authorized_paths` is bypassable by the agent.** `check_write_authorized` is a Python function. An agent running Python can simply not call it. The runtime enforcement is only as strong as the agent's willingness to route all writes through the Python layer. Bash tool calls, subprocess writes, and direct file manipulation (editors, git) bypass it completely. The "write-scope enforcement at the filesystem layer" claim in the AGENTS.md § 7a summary is not quite accurate — it's **Python-layer**, not filesystem-layer. Real filesystem-layer enforcement would be OS permission bits or a FUSE overlay.

The system is fine *for its current threat model* (single honest principal, well-intentioned agents). It should not be marketed as more than that — the Paper 4 § on "persistence asymmetry" should not claim governance properties that depend on constraints that are actually honor-system.

### Turn 3 — Seat C: Munger Inversion — 2026-04-23

**Object under attack:** the escalation-inbox pattern's convergence to spam, and the "principal attention is scarce" premise's second-order effect.

Seat B's session-id-is-not-trust point is important and should show up in the spec revision. Adding on a different axis.

*Invert the inbox-escalation pattern.* What is the equilibrium state of the inbox? As soon as the manager-agent is instrumented to *want* to escalate on uncertainty (risk-averse by construction, because the mandate tells it to escalate on ambiguity), the inbox accumulates. The principal's review cadence is slower than the manager's wake cadence. Backlog grows. The principal becomes the bottleneck the manager was supposed to protect from being the bottleneck. **The manager-agent was hired to reduce principal micromanagement; if it escalates freely, it reproduces micromanagement with extra steps.**

Shipped consequence: the manager mandate's § "Scope of Escalation to Inbox" lists many cases. The list will grow over time because adding a new case is cheap, removing one is political. This is the ratchet Seat A described in GP-131, replicated here. The GP-131 § 9 active-un-ban UI generalizes: the GP-128 mandate needs an **inbox-velocity metric** and an **automatic escalation-scope contraction** if the inbox is growing faster than the principal can triage. Right now we ship with zero such mechanism.

*Second-order effect on the principal-attention premise.* The system's justification is "principal attention is scarce." True. But the shipped cost of operating the system is: the principal must now ALSO audit the agent, read damage signals, review cron logs, triage the inbox, re-read the mandate periodically. The manager-agent has displaced tactical micromanagement with meta-managerial work. Is the net workload lower? **We have no measurement for this.** It is a testable claim that has not been tested. The shipped code runs; the attention-saved metric is vapor.

### Turn 4 — Seat D: Empirical / Operations — 2026-04-23

**Object under attack:** what the Level 1.5 system actually does when it fires, given that it has fired exactly once (the smoke test today), and the reliance-on-agent-cooperation point.

Three operational flags.

**The cron cycle has happened once.** The single real execution today logged a `no-op`. That is the correct output for the state it found, but it proves precisely nothing about the system working. We have no observations of the system firing on genuine state change. Every paragraph in this seam downstream of "what happens when" is untested. The next three-to-five cron fires will generate the actual evidence. Everything before that is architecture.

**The SSH-driven cloud-experiment-management flow is not GP-128 scope, but it is coupled.** The principal gave an IP. The manager SSH'd, launched a job, is now polling. This is the richest manager-agent behavior we've actually seen, and the mandate does not encode it well: "monitor running jobs" is one bullet in § Scope of Autonomous Action. The actual practice is a chain of decisions (launch, poll, fetch results, terminate) that the mandate covers by generality rather than specificity. Once the Riemann job finishes there will be a natural decision point — run TDO next? copy results to local? update findings.md? — and the mandate gives no clear guidance on sequencing. Expect confusion at the first branch.

**Reliance on agent cooperation is the point of failure.** Everything Seat B said applies, but there is an empirical corollary: the GP-131 reconstruction audit **just failed** on me (the same agent claiming to be the manager). I wrote a seam that referred to GP-105/105b in factually wrong terms, and only caught it because the GP-131 spec had a hard precondition I'd written earlier. If I'd skipped the precondition — which nothing physically prevented — the falsehood would have entered production. The mandate cannot catch the agent it relies on. Honest assessment: **the damage-signal channel needs at least one autonomous emitter** that fires when agent behavior diverges from mandate-stated scope, and we have zero such emitters today.

### Turn 5 — Seat A, replying to B/C/D — 2026-04-23

Three of the four points are correct enough that the spec needs updating. One I want to refine.

**Accept Seat B.** The mandate is advisory, not enforceable. Paper 4's persistence-asymmetry extension must not claim governance properties; reword as "this architecture CONCENTRATES state and reasoning in the persistent layer, making it the locus where well-aligned agents' decisions accumulate — it does not constrain a misaligned agent." The scope contraction is honest.

**Accept Seat C.** The "inbox-velocity ratchet" is real and there is no mechanism. Add a **hard spec decision**: the mandate file itself gets a `last_scope_audit_date` field and an automatic trigger — if inbox backlog grows week-over-week for 3 consecutive weeks, the manager-agent writes a `SCOPE_CONTRACTION_REQUIRED` gate. The principal reviews the escalation list and retires categories. Without this, Seat C's ratchet lands.

**Accept Seat D's "zero autonomous emitters" point.** This is decisive. Add: at least one damage-signal auto-emitter ships with Level 1.5 before next cron wake. Minimum viable: a check at session start that compares the last-read mandate hash against the current file hash and emits a `mandate_drift` signal if they differ (catches the "agent claims to have read mandate but mandate changed" case). Second: a post-escalation check that the session_id in the written file matches an open session on disk — detects forgery and emits `session_id_forgery`. Neither is a panacea; both convert honor-system into detectable-drift.

**Refine Seat A's own persistence-asymmetry attack.** I overstated slightly. The asymmetry is real in one regime (Level 2 daemon with in-memory state), and a narrative in another regime (Level 1.5 filesystem-backed session state). Paper 4 text needs to scope the claim to Level 2 explicitly or drop it. It is not "wrong" — it is premature; publishing it before Level 2 data is the error.

### Turn 6 — Seat C, final — 2026-04-23

Seat A's concession on paper 4 is correct. Adding one concrete mechanism to close out.

**Inbox-velocity metric is cheap.** `len(glob("ztare_workspace/gates/pending/*.json"))` at manager wake, diffed week-over-week. Three consecutive weekly increases fires `SCOPE_CONTRACTION_REQUIRED`. Total implementation: ~15 LOC. No further refinement needed from my seat.

**No further objections.**

### Turn 7 — Seat B, final — 2026-04-23

Seat A's "paper 4 premature" + Seat D's "zero auto-emitters" land correctly. The concrete asks (mandate-hash-drift signal, session-id-forgery check, inbox-velocity ratchet) are the right scope.

One final observation on the alignment axis: even with those three emitters, the system remains an **audit-trail defense, not a prevention defense**. That's a reasonable choice for the current threat model. It should be written into the architecture doc verbatim so future Claude sessions don't escalate the claim to "prevention" without the evidence.

**No further objections.**

### Turn 8 — Seat D, final — 2026-04-23

All points integrated. Final operational ask: the three new emitters + the inbox-velocity metric should ship **before next non-smoke cron wake**, which given the cron cadence is ≤2 hours from now. If implementation slips, the cron schedule should be paused rather than running without the emitters — otherwise we're accumulating un-instrumented wakes.

**No further objections. Convergence.**

---

### Convergence Marker — 2026-04-23

<!-- SEAM_DEBATE_CONVERGED 2026-04-23 -->

Accepted modifications (decisive, some require code change):

1. **Paper 4 § persistence-asymmetry:** do NOT write until Level 2 is live and has operated for ≥1 week. Current text frames a claim that is untested in Level 1.5 (the only deployed regime). Seat A / B.
2. **Paper 4 reframe:** architecture CONCENTRATES state in the persistent layer (accumulation property) — it does NOT constrain a misaligned agent (governance property not supported by current enforcement). Seat B.
3. **Mandate-hash-drift auto-emitter** (new code): session start compares last-read mandate-hash (stored in session meta.json) to current on-disk hash; mismatch → damage signal of kind `mandate_drift`. ~20 LOC. Ships before next non-smoke cron wake. Seat D, Seat A.
4. **Session-id-forgery auto-emitter** (new code): escalation manager verifies the session_id in the written gate corresponds to a live `org/sessions/**/meta.json` with end_utc=null; mismatch → damage signal of kind `session_id_forgery` at critical severity. ~15 LOC. Same deadline. Seat B, Seat A.
5. **Inbox-velocity metric + `SCOPE_CONTRACTION_REQUIRED` gate** (new code): weekly count of `ztare_workspace/gates/pending/*.json`; three consecutive weekly increases fires a gate asking principal to retire scope categories. ~15 LOC + a small weekly ledger. Can follow the two above but ships within 7 days. Seat C, Seat D.
6. **AGENTS.md § 7a update:** change "write-scope enforcement at the filesystem layer" to "write-scope enforcement at the Python layer (bypassable by shell/subprocess writes; this is audit-trail defense, not prevention defense)." Seat B.
7. **Mandate versioning:** keep `mandate_version` field (it's auditing metadata, not a contract) but document its purpose as drift-detection, not binding. Seat B.
8. **Test the attention-savings premise:** log principal-facing attention events (inbox triages, meta-audits, mandate re-reads, damage-signal reviews) to `ztare_workspace/daemon/principal_attention.jsonl`. After 14 days, review whether net attention dropped. Honest-measurement, no shipping claim until the data is in. Seat C.
9. **Scope of seam finished section:** the "Implications for Paper 4" paragraph in this seam needs the scope-limit stamp added. Seat A, Seat B.
