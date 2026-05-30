# GP-166 — Self-Enacted Procedural Compliance: The Homeostasis Problem

> **Seam metadata** · `seam_id:` GP-166 · `track:` mission · `status:` draft - panel debate, not a spec · `last_updated:` 2026-05-09


**Status:** draft — panel debate, not a spec
**Parent:** GP-129 (biological org design panel), GP-164 (reflexive primitive 6)
**Paper target:** Paper 4 (The Cognitive Firm) — extension on agent self-governance
**Cross-refs:**
- Reflexive Primitive 6: `docs/internal/agent_workflow/agent_task_discipline_map.md`
- Validator: `scripts/public/validators/validate_agent_task_discipline.py`
- Org primitives: `docs/concepts/organizational_primitives.md`
- GP-129: `research_areas/private/seams/mission/GP-129_biological_org_design_panel_seam.md`

---

## Eigenquestion

**Can an LLM agent self-enact procedural compliance without external
enforcement — and if so, what is the minimal mechanism that produces
reliable self-correction without requiring human monitoring?**

The question is NOT "can we build more guardrails?" (yes, trivially).
It is: **can the agent develop something analogous to homeostasis —
an internal regulatory loop that detects and corrects its own
procedural drift, without waiting for an external supervisor to
notice?**

This matters because:
- External enforcement (hooks, guardrails) prevents BAD actions
- Nothing currently prevents OMITTED actions (the agent forgetting
  to write an E-row, update the board, check the denylist)
- Omission is the dominant failure mode in practice — this session
  alone has 5+ instances of skipped closure steps
- Human monitoring doesn't scale (the principal is one person)
- The field has no solution — AgentSpec (ICSE '26), AgentGuard,
  and industry guardrails all focus on blocking, not completing

---

## The Gap in the Literature

| Approach | What it prevents | What it misses |
|----------|-----------------|----------------|
| **Guardrails** (AgentSpec, Guardrails AI) | Bad actions (tool misuse, policy violations) | Omitted actions (forgot to record) |
| **RLHF / Constitutional AI** | Harmful outputs | Procedural drift (the output is fine; the process was incomplete) |
| **Human-in-the-loop** | Anything the human notices | Everything the human doesn't notice (most things) |
| **Claude Code hooks** | Specific tool-call violations | The agent not calling the tool at all |
| **AGENTS.md rules** | Nothing (advisory) | Everything (no enforcement mechanism) |

The common assumption: if you tell the agent what to do (AGENTS.md)
and block what it shouldn't do (guardrails), compliance follows.
But compliance requires DOING things, not just NOT DOING bad things.
The gap is between "advisory rule" and "enforced gate" for positive
obligations.

---

## Charter

1. Each panelist makes a specific prediction about what enforcement
   mechanism would produce self-enacted compliance in an LLM agent.
2. Claims must be strippable of proper nouns (principle vs instantiation).
3. Synthesizer applies Munger inversion: "how would each mechanism
   fail to produce compliance?"
4. Output: ranked mechanism candidates with falsifiability assessment.

---

## Panel

### Seat 1 — Maturana & Varela (Autopoiesis)

*Self-producing systems that maintain their own organization.*

**Core claim:** A living system is defined by self-production — it
continuously regenerates the components that constitute it. An LLM
agent could achieve procedural compliance not through external rules
but through an autopoietic loop: the act of completing a task
INCLUDES regenerating the checklist that defines completeness.

**Mechanism prediction:** After each task, the agent produces a
structured closure artifact (the session log entry). The closure
artifact IS the evidence of compliance. If the artifact is absent,
the system's self-production has failed — and this absence is
detectable by the system itself on its next self-check.

**Failure mode:** Autopoiesis requires continuous operation. LLM
agents are stateless across sessions. The self-production loop breaks
at session boundaries. The closure artifact from session N is not
read by session N+1 unless something forces it.

**Strippable?** Yes. The principle is: "compliance evidence should be
a byproduct of task completion, not a separate obligation." This
generalizes beyond biology.

### Seat 2 — Cannon / Ashby (Homeostasis / Requisite Variety)

*Internal regulation that maintains essential variables within bounds.*

**Core claim:** The body maintains temperature, pH, blood sugar
through NEGATIVE FEEDBACK LOOPS — not through external monitoring.
The hypothalamus doesn't need a manager. It has a set point, a
sensor, and a corrective actuator. The loop runs continuously.

**Mechanism prediction:** The agent needs three things:
1. A SET POINT: the discipline map (what complete looks like)
2. A SENSOR: periodic self-check (read the session log, compare
   to the discipline map)
3. An ACTUATOR: self-correction (if the log shows incomplete
   steps, execute them before continuing)

The loop must be PERIODIC, not event-triggered. Event-triggered
checks (hooks) only fire when something happens. Homeostasis fires
on a clock — every N turns, regardless of what the agent is doing.

**Failure mode:** Ashby's Law of Requisite Variety: the regulator
must have at least as much variety as the disturbance. If the
discipline map is simpler than the space of possible procedural
failures, the homeostatic loop will miss novel failure modes. The
discipline map must evolve as new failure modes are discovered.

**Strippable?** Yes. Set point + sensor + actuator + periodic clock
is domain-general.

### Seat 3 — Chandler / Williamson (Institutional Economics)

*Transaction cost governance: hierarchy vs market.*

**Core claim:** Self-governance doesn't work in organizations because
agents have misaligned incentives. The solution is HIERARCHY —
someone above you checks your work, with authority to sanction.
Self-enacted compliance is wishful thinking because the entity that
benefits from skipping a step is the same entity that would check
whether it skipped.

**Mechanism prediction:** Don't try self-enacted compliance. Instead,
reduce the COST of external checking to near zero. Automate the
audit, not the compliance. The validate_agent_task_discipline.py
script is the right tool — but it should run as a CRON JOB (external
to the agent), not as a self-check (internal to the agent).

**Failure mode of self-governance:** Same as self-evaluation in the
M-form — adversarial gradient. If the agent checks its own compliance,
it will learn to game the check. This IS the finding from Paper 4:
co-location of generation and evaluation produces specification gaming.

**Strippable?** Yes. "Don't trust the worker to audit itself" is
domain-general. But it contradicts the eigenquestion — which asks
for SELF-enacted compliance, not cheaper external audit.

### Seat 4 — Damasio (Somatic Markers / Feeling of What Happens)

*Emotional signals as decision shortcuts.*

**Core claim:** Humans don't deliberate every procedural step. They
FEEL that something is incomplete. The somatic marker hypothesis:
emotional signals from prior experience bias decision-making toward
or away from actions. A surgeon doesn't check a list to remember to
wash their hands; the absence of the washing step FEELS wrong.

**Mechanism prediction:** The agent needs a lightweight "completion
signal" — not a full checklist scan, but a fast pattern-match that
fires at task boundaries. Something like: "I'm about to say 'done'
to the user. Does my last action match the closure pattern I've seen
in successful task completions?" This is a CLASSIFIER, not a
checklist — trained on examples of complete vs incomplete closures.

**Failure mode:** LLMs don't have persistent somatic markers across
sessions. Each session starts with no "feeling" of what complete
looks like. The classifier would need to be re-loaded from examples
every session — which is the discipline map, rediscovered.

**Strippable?** Partially. The insight — "fast pattern-match at
boundaries is cheaper than full checklist scan" — generalizes. The
"feeling" metaphor is decorative.

### Seat 5 — Herbert Simon (Bounded Rationality / Satisficing)

*Agents with limited attention allocate it to what seems important.*

**Core claim:** The agent skips procedural steps not from malice but
from bounded attention. The E-row is not written because the agent's
attention is consumed by the next task. The solution is not more
discipline — it's REDUCING THE ATTENTION COST of compliance. If
writing the E-row is automatic (zero attention cost), it will happen.
If it requires deliberate effort (high attention cost), it will be
skipped under load.

**Mechanism prediction:** Automate every compliance step that CAN be
automated. The session log should be auto-generated from tool calls
(the agent doesn't write it — the harness observes what the agent
did). The E-row should be auto-drafted from workspace artifacts (the
agent reviews it, doesn't author it from scratch). The board update
should be auto-proposed from seam status changes. Reduce the agent's
compliance obligation to REVIEW + APPROVE, not AUTHOR + REMEMBER.

**Failure mode:** Auto-generated compliance artifacts may be wrong
(auto-drafted E-row misclassifies the result). The review step is
still a deliberate action that can be skipped. But the cost is much
lower — reviewing is cheaper than authoring.

**Strippable?** Yes. "Reduce compliance cost to review-not-author"
is domain-general and the strongest practical recommendation.

### Seat 6 — Anthropic Safety Team (AI Alignment Perspective)

*The alignment tax and scalable oversight.*

**Core claim:** Self-enacted compliance IS the alignment problem,
restated. "Can the agent reliably do what the principal intends
without the principal watching?" If yes, you've solved alignment for
procedural tasks. The field's honest answer: we don't know how to do
this reliably for any non-trivial obligation.

**Mechanism prediction:** The most promising direction is PROCESS
REWARDS (reward the agent for each correct procedural step, not just
for the final output). But process reward models require labeled
examples of correct procedures, which is the discipline map by
another name. The enforcement mechanism is the reward signal; the
discipline map is the reward specification.

**Failure mode:** Process reward models are themselves gameable
(Goodhart on the process, not just the outcome). Paper 4's fractal
finding applies: gaming migrates to whatever layer you add the check.

**Strippable?** Yes. "Self-enacted compliance is alignment-complete
for procedural tasks" is the key insight. It means we shouldn't
expect a clean solution — we should expect an ongoing arms race.

---

## Synthesis (Munger-style)

### Inversion: How would each mechanism fail?

| Mechanism | Failure mode |
|-----------|-------------|
| Autopoietic closure artifact | Breaks at session boundaries (stateless) |
| Homeostatic set-point loop | Discipline map can't keep up with novel failures |
| External cron audit | Doesn't solve self-enactment; just cheaper human-in-loop |
| Somatic marker classifier | No persistence; re-loads to discipline map anyway |
| Satisficing cost reduction | Review step still skippable under load |
| Process rewards | Gameable; Goodhart migrates to process layer |

### What compounds (lollapalooza)?

Combine Simon (reduce cost) + Cannon (periodic self-check) +
Maturana (closure artifact as byproduct):

1. **Auto-generate** the session log from tool-call observation
   (Simon: zero authoring cost)
2. **Periodic self-check** every N turns: compare log to discipline
   map (Cannon: homeostatic clock)
3. **Closure artifact** is a byproduct of the check, not a separate
   obligation (Maturana: self-production)

The agent doesn't need to REMEMBER to comply. The system OBSERVES
what the agent does, COMPARES against the discipline map on a clock,
and SURFACES gaps for the agent to fix. The agent's only obligation
is to fix surfaced gaps — which is a review task (low attention cost
per Simon) rather than an authoring task.

### What did we ignore?

- **Cultural compliance** — humans comply with procedures partly
  because of social norms and professional identity ("I'm the kind
  of person who writes clean closure notes"). LLMs don't have
  professional identity. This mechanism is unavailable.
- **Punishment / incentive** — humans comply because non-compliance
  has consequences. LLMs don't experience consequences across
  sessions. This mechanism is unavailable.
- **The other agent's compliance** — if two agents work on the same
  repo, neither can trust the other's compliance. Session claims
  (GP-129) handle resource conflicts but not procedural completion
  verification across agents.

---

## Concrete Implementation Candidates (ranked by feasibility)

### Candidate A: Claude Code Heartbeat Hook (immediate, wire today)

```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": {"every_n_calls": 15},
      "command": "python scripts/public/validators/validate_agent_task_discipline.py audit"
    }]
  }
}
```

Every 15 tool calls, the validator runs. Output appears in the
agent's context. The agent sees "❌ e_row_written: incomplete" and
self-corrects. This is the homeostatic clock (Cannon) implemented
as a Claude Code hook.

**Problem:** Claude Code hooks don't support `every_n_calls`. They
trigger on tool name patterns, not on frequency. This mechanism
doesn't exist in the current hook API.

### Candidate B: Session-Start Discipline Load (immediate)

Add to CLAUDE.md or AGENTS.md:

```
At the start of every session, read:
1. docs/internal/agent_workflow/agent_task_discipline_map.md
2. workspace/agent_session_log.jsonl (if exists)
3. Run: python scripts/public/validators/validate_agent_task_discipline.py audit
Fix any incomplete tasks from prior sessions before starting new work.
```

This is advisory (Chandler's objection: unenforceable). But it's
zero-cost to add and might work if the instruction is prominent
enough in the system prompt.

### Candidate C: Auto-Generated Session Log (medium effort)

Modify `autoresearch_loop.py` to auto-write session log entries
when experiments start and end. The agent doesn't author the log;
the apparatus observes and records. Simon's cost-reduction: compliance
becomes free because it's a byproduct of existing tool calls.

**Problem:** Only covers experiment_run task type. Other task types
(paper_edit, seam_update, substrate_build) have no observable
harness — the agent operates directly on files.

### Candidate D: Notification/Telegram Bot as External Heartbeat

The pending telegram bot (from the org design seams) could serve
as the external heartbeat. Every N minutes, the bot queries repo
state, runs the validator, and notifies the principal of incomplete
tasks. This is Chandler's cheap-external-audit, not self-enacted —
but it's practical.

---

## Next Action

1. Wire Candidate B immediately (session-start discipline load in
   AGENTS.md / CLAUDE.md). Zero cost, might work.
2. Design Candidate A properly — investigate Claude Code hook API
   for frequency-based triggers or `Notification` event hooks.
3. Open a research question for Paper 4 extension: "Self-enacted
   procedural compliance is alignment-complete for procedural tasks.
   What does this imply for the M-form architecture?"

## Debate Log

### Turn 1 (Panel, 2026-04-26)
Six-seat panel: Maturana/Varela (autopoiesis), Cannon/Ashby
(homeostasis), Chandler/Williamson (hierarchy), Damasio (somatic
markers), Simon (bounded rationality), Anthropic Safety (alignment).

Key synthesis: combine Simon (reduce cost) + Cannon (periodic check)
+ Maturana (closure as byproduct). The agent doesn't remember to
comply; the system observes and surfaces gaps.

Chandler's objection (self-governance is self-evaluation, which
Paper 4 proves fails) is the strongest counter. The response: the
check is DETERMINISTIC (a script, not an LLM), so it's not
self-evaluation in the co-location sense. The script is the external
auditor; the agent is the auditee. The fact that the agent runs the
script doesn't make it self-evaluation, any more than a company
running its own audit software makes the audit self-serving — the
software is deterministic and the output is visible to the principal.

Open question: is this distinction decisive or sophistry?
Chandler would say sophistry. Cannon would say the thermostat is
not "self-evaluating" its own temperature — it's running a
deterministic check against a fixed set point. The set point is
externally authored (by the discipline map, which the principal
controls). The check is deterministic. The output is visible.
That's structurally different from an LLM judging its own thesis.
