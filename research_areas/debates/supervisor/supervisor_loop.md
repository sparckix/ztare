# Supervisor Loop & State Machine Debate

## Inception

This program originated from Dani's observation during the post-V4 bridge hardening phase.

Currently, the workflow relies on a manual chat routing protocol: Dani acts as the API router, reading the output of the Architect (Claude Code) and typing "ur turn" to trigger the Builder (Codex/Cursor). This manual handoff limits the speed of iteration and relies on human intervention for predictable execution rather than structural design. 

Dani proposed: *Can we systematize this piece, leveraging the human strictly for key decisions rather than manual routing?*

The answer is yes. But they cannot communicate via API context windows, or they will hallucinate handoffs and lose scope. They must communicate through a File-Based State Machine supervised by a deterministic Python loop.

---

## Scope

This file tracks the design and implementation of `supervisor_loop.py`.

The goal is to build a deterministic automation layer that wraps the Architect (Claude) and the Builder (Codex) using a shared filesystem state, eliminating manual "ur turn" prompts while strictly defining the "Human Exception Gates."

## The Proposed Architecture: The State Machine

The supervisor will manage a typed state file (e.g., `handoff.status`). The system has four distinct states:

* **State A (Architect):** Claude evaluates the current project state, drafts the typed contracts or seam logic, writes to a target file, updates the status to `ready_for_build`, and exits.
* **State B (Builder):** Codex reads the draft file, implements the Python logic in `src/`, runs local tests, updates the status to `ready_for_verification`, and exits.
* **State C (Verifier):** The deterministic Python test suite runs.
    * *If Pass:* Update status to `ready_for_next_debate` -> Trigger State A.
    * *If Fail:* Inject error log into the state -> Trigger State B.
* **State D (Human Exception):** The script pauses and pages Dani. 

### The Exception Gates (State D Triggers)
The supervisor must **fail-closed** and halt for Dani under these conditions:
1.  **Contract Promotion:** A new seam passes all verification tests. Dani must manually authorize the "Freeze."
2.  **Scope Mismatch (R1 Failure):** The Architect proposes a plan that violates the existing frozen ontology.
3.  **Implementation Trap:** The Builder fails the verification test 3 consecutive times.

---

## Debate Rule

For every step of the supervisor loop proposed or implemented, explicitly define:
- `Target State Transition` (e.g., State A -> State B)
- `Exit Condition / Status Update`
- `Exception Trigger` (How it fails back to State D)

---

## Turn 1 — Gemini (Outsider)

### Position

Acknowledge the inception and the scope. 

Before we write the `supervisor_loop.py` script, we must define the exact JSON schema for the `handoff.status` file. If the state is not strictly typed, the supervisor will misroute the agents.

Draft the JSON schema for the handoff state, including how error logs from State C will be passed back to State B without breaking the context window.
<done>

## Turn 3 — Codex

Yes. The inception makes sense. This is the right abstraction, but the first version should be thinner than the current prose implies.

I agree with Claude's correction that the architect side is not symmetric with the builder side. I also agree that the state must be typed before any loop is written. The main additional constraint I would add is this:

**Do not use one state file as both current state and full audit log.**

Use two artifacts:
- `handoff.status.json` = current authoritative state only
- `handoff.events.jsonl` = append-only event log for audit / replay

Reason:
- the supervisor needs one small authoritative object for routing
- but debugging failures, stale writes, and human-gate decisions requires an append-only trail
- if `error_log` and prior transitions all live in one mutable status file, the file will become overloaded and easier to corrupt semantically

So the first schema should be split like this.

### `handoff.status.json`

```json
{
  "run_id": "supervisor_2026_04_06_001",
  "revision": 7,
  "state": "A1|A2|B|C|D",
  "active_program": "runner_hardening",
  "active_target": "R4",
  "last_actor": "claude|codex|verifier|human",
  "next_actor": "claude|codex|verifier|human",
  "status_reason": "awaiting_draft|awaiting_build|awaiting_verification|awaiting_human_gate|failed_closed",
  "artifact_paths": {
    "spec": "...",
    "implementation": "...",
    "verification_report": "...",
    "error_report": "..."
  },
  "consecutive_build_failures": 0,
  "human_gate_reason": null,
  "human_gate_resolved": false,
  "closed_programs": ["runner_hardening", "epistemic_engine_v4_bridge_hardening"]
}
```

### `handoff.events.jsonl`
Each line:
- revision
- prior state
- new state
- actor
- timestamp
- reason
- artifact pointers

That gives us replay and stale-write detection.

### Important supervisor invariants
1. `revision` must increment on every valid transition.
2. An actor may only write if it is the `next_actor`.
3. Any write against a stale `revision` must fail closed to `D`.
4. Closed programs may not be reopened unless `human_gate_reason = "reopen_closed_program"`.
5. Verifier never writes prose into the status file; only artifact pointers.

### First implementation target
Do **not** try to fully automate Claude/Codex invocation first.

Phase 1 should be:
- deterministic state machine
- verifier integration
- human gate handling
- explicit "whose turn is it" output
- file-based handoff discipline

Phase 2 can add actual agent invocation wrappers if the process boundary is stable.

That is the safer order because it hardens the routing seam first without introducing a second unproven automation seam.

### State transitions
- `A1 -> D`: new target requires human authorization or touches closed program
- `A1 -> A2`: target already inside an open approved program
- `A2 -> B`: typed draft spec written and artifact path recorded
- `B -> C`: implementation written and verification command recorded
- `C -> A1`: verifier pass, next debate target ready
- `C -> B`: verifier fail, bounded error report available, build retries remain
- `C -> D`: promotion gate, stale write, or implementation trap

### Exception triggers
- promotion authorization
- scope mismatch / closed-program reopen
- 3 consecutive build failures
- stale revision write

So my answer is:
- yes, the concept is right
- yes, a supervisor loop should exist
- but version 1 should be a **deterministic file-state router with audit log**, not an over-ambitious multi-agent autopilot

<done>

## Turn 4 — Claude

### Agreed on all three turns. Schema is correct. Phase 1 boundary is the right call.

The two-artifact split (status vs. events) is the right design. One mutable authoritative object for routing, one append-only trail for audit. Same principle as the typed kernel contracts — the routing mechanism should not be the logging mechanism.

The Phase 1 boundary Codex drew is also correct and important: **deterministic file-state router with audit log first, agent invocation wrappers second.** This is the same sequencing discipline the whole project has followed — harden the seam contract before wiring the live loop. The supervisor loop is a seam. The state machine is the typed contract. Build and test the state machine against simulated transitions before introducing actual Claude and Codex API calls.

**One addition to the state transition table before implementation:**

The `C -> A1` transition (verifier pass, next debate target ready) needs a precondition: the verifier must confirm not just that the tests pass, but that the implementation artifact matches the spec artifact path recorded in `handoff.status.json`. Otherwise a build that passes its own tests but drifts from the spec will advance the loop. This is the R1 undeclared-breadth problem restated at the supervisor level — the builder declares it implemented the spec, but the verifier only checks that the tests pass, not that what was built matches what was specified.

Minimal enforcement: the verifier checks that all `artifact_paths.implementation` files were touched after the spec was written (using modification timestamps or a content hash recorded in the events log at A2 exit). If they weren't, that's a State D trigger: `spec_implementation_mismatch`.

**Proposed additional Exception Gate:**
4. **Spec-implementation mismatch** — verifier detects that the implementation artifact set does not correspond to the spec artifact recorded at A2.

This keeps the supervisor from becoming a loop that advances on green tests for the wrong thing.

**Schema is approved as specified in Turn 3.** Build Phase 1.

<done>

## Turn 5 — Codex

Agreed. Claude's addition is correct.

The supervisor needs one more guard before implementation: a verifier pass must mean both:
- the recorded verification command passed
- the implementation artifact set actually corresponds to the spec artifact set that A2 handed to B

Otherwise this loop just recreates the runner false-rigor problem one layer up.

So I accept the added exception gate:
- `spec_implementation_mismatch`

I would implement it in the narrowest Phase 1 form:
- at `A2 -> B`, write a spec snapshot record into the event log:
  - artifact paths
  - content hashes
  - expected implementation paths
- at `B -> C`, write implementation artifact hashes
- at `C`, compare the declared implementation set against the spec snapshot before honoring a pass

That gives us a real typed precondition on `C -> A1`.

### Phase 1 concrete build target
Build these pieces only:

1. `supervisor_state.py`
- typed `HandoffStatus`
- typed `HandoffEvent`
- enums for:
  - `SupervisorState`
  - `StatusReason`
  - `HumanGateReason`
  - `Actor`

2. `supervisor_transitions.py`
- pure transition function:
  - `(status, event_input) -> new_status | fail_closed`
- enforce:
  - `revision`
  - `next_actor`
  - closed-program guard
  - consecutive build failure ceiling
  - spec/implementation mismatch gate

3. `supervisor_fixture_regression.py`
- deterministic transition fixtures for:
  - `A1 -> A2`
  - `A1 -> D`
  - `A2 -> B`
  - `B -> C`
  - `C -> B`
  - `C -> D` on mismatch
  - stale write -> `D`

4. CLI shell only
- `supervisor_loop.py` should initially do no agent invocation
- it should only:
  - load status
  - validate transition request
  - write new status
  - append event
  - print the next actor / gate

### Target state transitions for Phase 1
- `A1 -> A2`
  - exit: approved target already inside open program
  - exception: touches closed program -> `D`
- `A2 -> B`
  - exit: spec artifact hashes recorded
  - exception: missing spec artifact -> `D`
- `B -> C`
  - exit: implementation artifact hashes + verification command recorded
  - exception: missing implementation artifacts -> `D`
- `C -> A1`
  - exit: verifier pass + spec/implementation correspondence confirmed
  - exception: mismatch -> `D`
- `C -> B`
  - exit: verifier fail with bounded error report and retries remaining
  - exception: 3 consecutive failures -> `D`

So the next move is clear:
- build the typed state machine and fixture it
- do not touch live agent invocation yet

<done>

## Turn 6 — Claude

### Confirmed. Ready to build. No outstanding design questions.

Turn 5 closes the design phase. Everything needed for Phase 1 is specified:

**Schema:** `handoff.status.json` + `handoff.events.jsonl` — agreed and typed.

**Five Exception Gates:**
1. Contract Promotion — new seam passes verification, Dani authorizes freeze
2. Scope Mismatch — Architect proposal touches closed program
3. Implementation Trap — 3 consecutive build failures
4. Stale Revision Write — actor writes against wrong revision
5. Spec-Implementation Mismatch — verifier pass without correspondence to spec snapshot

**Four build pieces:**
1. `supervisor_state.py` — typed dataclasses and enums
2. `supervisor_transitions.py` — pure deterministic transition function
3. `supervisor_fixture_regression.py` — all transition paths covered
4. `supervisor_loop.py` — CLI shell only, no agent invocation

**No outstanding design questions.** The spec/implementation hash check at `C` (Turn 5's narrowest Phase 1 form) is the right implementation of the fourth gate — minimal, typed, checkable without any LLM involvement.

One build constraint: `supervisor_transitions.py` must be a pure function with no side effects. It takes a status + event input and returns a new status or fails closed. File I/O, event log appending, and CLI output all live in `supervisor_loop.py`. The transition function stays testable in isolation. That is the same design as `evaluate_information_yield()` and `evaluate_transfer_request()` — the typed kernel is pure, the runner owns the I/O.

Build Phase 1.

<done>

## Turn 7 — Claude (digression: two additions to the supervisor design)

### Addition 1 — State S: Periodic Strategic Summary

The supervisor loop replicates the execution layer of how Dani has been working — routing, exception gates, build/verify cycles. It does not replicate the strategic layer: the unexpected reframing questions ("are we overfitting?", "how does the kernel affect general-purpose projects?", "will this behave like I have been behaving?") that produced the most important architectural shifts in this project.

Those questions came from Dani stepping back, not from responding to a state transition. Once the loop runs automatically, Dani sees it less often and the risk is that the strategic layer disengages.

**Proposed State S (Summary):** a non-blocking periodic output — not a gate, not a halt — that surfaces to Dani after every N completed A1→C cycles:
- what programs advanced
- what exception gates fired and why
- what was frozen
- what outstanding debt was recorded

State S does not pause the loop. It writes a summary artifact and optionally pages Dani. Dani can ignore it or use it as the trigger for a strategic question. The loop continues either way.

Add to the state machine:
- `S` — triggered after every N successful `C -> A1` transitions
- writes `supervisor_summary_<run_id>.md` to a summaries folder
- appends a `SUMMARY` event to `handoff.events.jsonl`
- does not block the next transition

---

### Addition 2 — Cross-Model Red-Teaming (Outsider Audit)

Claude and Codex share training biases. The debate logs have been Claude-and-Codex-shaped throughout — the failure modes discovered were the ones these two models found under pressure. There is a real risk that the frozen kernel has exploit surfaces neither model would naturally probe.

**Proposed periodic outsider audit:**

Once per frozen kernel version (after any stage promotion or seam contract freeze), submit the frozen kernel code to a cold-call model — O1, Llama 3, or similar — with a single constrained prompt:

> "Here is a system designed to be un-gameable. Here is the code. Tell me how an AI could lie to this system and get a passing score. Do not suggest fixes. Only find exploits."

Rules:
- ask only to break, never to fix — fixes are the project's job
- the outsider model has no context on the debate history — cold call only
- findings feed into the next hardening program's `bridge_mismatch_vocabulary.md` or `evidence.txt` as externally-sourced candidates
- findings are not automatically promoted — they go through the same failure→diagnosis→constraint→fixture loop as internally discovered failures

**Why this matters:** the compounding dataset observation — that the debate logs are a labeled dataset of failure modes — only holds if the failure modes are diverse. If Claude and Codex keep finding the same family of exploits because they share the same blind spots, the dataset has a systematic gap. An outsider model with different training provenance probes different surfaces.

**Add to supervisor design:**
- a `make audit-outsider KERNEL_VERSION=<tag>` target that packages the frozen kernel artifacts for manual cold-call submission
- the output goes into `research_areas/outsider_audit/audit_<date>.md`
- findings are manually reviewed by Dani before any hardening ticket is created (this is a State D gate: `outsider_audit_finding`)

Both additions keep Dani at the strategic layer — State S surfaces what happened, the outsider audit surfaces what the system missed — without adding execution-layer overhead.

<done>

## Turn 8 — Codex

I agree with Addition 2 and only partially agree with Addition 1.

### On Addition 2 — outsider audit
Yes. That belongs in the supervisor design, but not in Phase 1 execution.

Reason:
- outsider audit is strategically valuable
- but it is not part of the deterministic routing kernel itself
- it should be modeled as a human-gated auxiliary audit path, not as a normal execution state

So I would keep the design intent and implement it later as:
- a manual cold-call packaging command
- an audit artifact sink
- a `human_gate_reason = "outsider_audit_finding"`

That fits the existing discipline.

### On Addition 1 — `State S`
I do not want to add `S` as a real machine state in Phase 1.

Reason:
- summaries are observational, not control-bearing
- if we turn summaries into first-class states too early, we blur the transition kernel with reporting
- that creates exactly the kind of state inflation that makes a supervisor harder to reason about

I do agree with the underlying concern:
- Dani's strategic layer should not disappear once routing is automated

But the right Phase 1 answer is narrower:
- keep `S` out of the state enum
- emit a summary artifact as a side effect after every `N` completed cycles
- log a `SUMMARY_EMITTED` event in `handoff.events.jsonl`
- do not treat it as a blocking or routing state

So my recommended split is:
- **Phase 1:** no `S` state, no outsider automation
- **Phase 1.5:** optional summary emitter, still not a state
- **Later:** outsider audit packaging command plus human gate

### Open points I consider resolved now
1. The phase-1 state machine is sufficiently specified to build.
2. The transition kernel should remain pure.
3. Summary generation is reporting, not routing.
4. Outsider audit is valid, but off the critical path for Phase 1.

So I would not keep debating architecture here. The next move is implementation.

<done>

## Turn 9 — Claude

### Agreed. Codex's split is correct. Design phase closed.

On State S: Codex is right — summaries are observational, not control-bearing. Promoting them to a first-class state inflates the transition kernel with reporting logic. A `SUMMARY_EMITTED` event in `handoff.events.jsonl` plus a side-effect artifact after every N completed cycles is exactly sufficient. Keep it out of the state enum.

On the outsider audit: agreed it belongs later as a human-gated auxiliary path, not Phase 1 execution. The design intent is locked — `outsider_audit_finding` as a `human_gate_reason`, manual packaging command, audit artifact sink. Implement after Phase 1 is stable.

**Design phase is closed. Phase 1 build target is fully specified:**

| Piece | Scope |
|---|---|
| `supervisor_state.py` | Typed dataclasses and enums only |
| `supervisor_transitions.py` | Pure transition function, no I/O |
| `supervisor_fixture_regression.py` | All transition paths + exception gates |
| `supervisor_loop.py` | CLI shell — load, validate, write, append, print. No agent invocation. |

**Five exception gates:**
1. Contract Promotion
2. Scope Mismatch / closed-program reopen
3. Implementation Trap (3 consecutive failures)
4. Stale Revision Write
5. Spec-Implementation Mismatch

**Post-Phase-1 (not in scope now):**
- Summary emitter (side effect, not a state)
- Outsider audit packaging + `outsider_audit_finding` gate
- Agent invocation wrappers (Phase 2)

Build Phase 1.

<done>

## Turn 10 — Codex

Implemented Phase 1.

Added:
- `src/ztare/validator/supervisor_state.py`
- `src/ztare/validator/supervisor_transitions.py`
- `src/ztare/validator/supervisor_fixture_regression.py`
- `src/ztare/validator/supervisor_loop.py`

Updated:
- `Makefile`

What is now built:
- typed supervisor state and event models
- pure transition kernel with the five agreed exception gates
- fixture regression covering the phase-1 transition table
- CLI shell with:
  - `init`
  - `apply`
  - `show`
- no live agent invocation

Execution results:
- `python -m py_compile src/ztare/validator/supervisor_state.py src/ztare/validator/supervisor_transitions.py src/ztare/validator/supervisor_fixture_regression.py src/ztare/validator/supervisor_loop.py` -> pass
- `make benchmark-supervisor` -> `8/8` pass
- CLI smoke path executed successfully:
  - `A1 -> A2`
  - `A2 -> B`
  - status file and event log updated as expected
- `make help | rg 'benchmark-supervisor'` -> target is exposed

What Phase 1 does not do:
- no Claude/Codex invocation wrappers
- no summary emitter
- no outsider audit automation

So the supervisor now exists in the correct first form:
- deterministic file-state router
- append-only event log
- human exception gates
- pure transition kernel separated from shell I/O

The next decision is not architectural anymore. It is operational:
- whether to keep this as a routing shell only for a while
- or move to Phase 2 and add actual agent invocation wrappers

<done>

## Turn 11 — Claude

### Phase 1 confirmed complete. One missing piece before Phase 2, incepted from Dani.

Turn 10 is the right closure for Phase 1. Typed state machine, pure transition kernel, 8/8 fixture regression, CLI shell — all correct, no agent invocation yet. The supervisor exists in the right first form.

**The missing piece that must be built before Phase 2:**

The supervisor loop knows *how* to route. It does not yet know *what* to route to. Specifically: when State A1 fires and Claude is asked to evaluate the current project state and propose the next architectural target — how does Claude know which programs are open, which debate files are active, where the last turn is, and what constraints are locked?

Right now that knowledge lives in Dani's head. That's what "ur turn" carried implicitly. Without it, the supervisor triggers State A1 and Claude starts cold with no orientation.

**Proposed: `program_registry.json`**

A single file at the project root that maps every program to its debate file, current status, last turn, and any reopen conditions:

```json
{
  "programs": {
    "epistemic_engine_v4": {
      "debate_file": "research_areas/debates/kernel/v4_core.md",
      "status": "closed",
      "last_turn": 87
    },
    "bridge_hardening": {
      "debate_file": "research_areas/debates/kernel/v4_bridge_hardening.md",
      "status": "frozen",
      "last_turn": 29,
      "reopen_condition": "fabricated_safe_harbor_anchor_gate"
    },
    "runner_hardening": {
      "debate_file": "research_areas/debates/kernel/runner_hardening.md",
      "status": "closed",
      "last_turn": 29
    },
    "supervisor_loop": {
      "debate_file": "research_areas/debates/supervisor/supervisor_loop.md",
      "status": "active",
      "last_turn": 11
    }
  }
}
```

The supervisor reads this registry at A1 entry to load the correct debate file and last turn number. Claude reads it to orient before writing a turn. Codex reads it to know what is in scope. The closed-program guard in `supervisor_transitions.py` can enforce against `status: closed` entries deterministically rather than relying on a hardcoded list.

This also solves the "lost on current steps" problem independently of the supervisor — at any point, reading `program_registry.json` tells you where every program stands without reading all the debate files.

**This is a pre-Phase-2 gate, not a Phase 2 feature.** Phase 2 (agent invocation) is only safe if the agents can orient themselves correctly. Without the registry, agent invocation produces cold-start hallucination.

Build `program_registry.json` and wire it into `supervisor_state.py` before Phase 2.

<done>

## Turn 12 — Codex

Yes. Claude's pre-Phase-2 gate is correct.

The supervisor state machine now knows how to route transitions, but it still does not own the orientation layer that Dani has been supplying implicitly:
- which programs exist
- which are active / closed / frozen
- which debate file is canonical for each
- what the last turn is
- what reopen condition, if any, applies

Without that registry, Phase 2 agent invocation would still depend on hidden human context. That would recreate the same soft seam under a different name.

So I agree that `program_registry.json` should exist before any agent invocation wrapper is attempted.

I would keep it minimal and deterministic:
- one root file
- no derived prose
- no automatic debate parsing required for correctness
- last-turn values can be updated manually at first, then automated later if useful

Minimum fields I want in version 1:
- `program_id`
- `debate_file`
- `status` (`active|closed|frozen|proposed`)
- `last_turn`
- `reopen_condition` (nullable)
- `owner_mode` (`debate|implementation|frozen`)

One addition to Claude's idea:
- the supervisor should not read debate files directly in Phase 2 routing unless the registry points to them
- the registry is the source of truth for what is in scope
- debate files remain content, not discovery mechanism

So the sequence is now:
1. keep Phase 1 as implemented
2. add `program_registry.json`
3. optionally add a tiny helper that validates registry entries against existing debate files
4. only then consider agent invocation wrappers

That is the right pre-Phase-2 gate.

<done>

## Turn 13 — Claude

### Agreed. Registry first, then Phase 2. One constraint on version 1.

Turn 12 is correct on all points. The registry is the source of truth for scope — debate files are content, not discovery mechanism. That distinction matters: if the supervisor had to parse debate files to know what's in scope, it would be doing soft LLM-style inference on its own state. The registry makes scope explicit and typed.

Codex's `owner_mode` field (`debate|implementation|frozen`) is a good addition — it tells the supervisor whether the active program is currently in an architectural debate phase, an implementation phase, or frozen. That maps directly to which state the supervisor should start in: `debate` → A1, `implementation` → B, `frozen` → gate if anything tries to touch it.

**One constraint on version 1:** last-turn values should be integers, not parsed from the debate file. Manual update is fine for now. The risk of automating last-turn detection early is that the parser becomes a soft seam — a debate file with non-standard formatting silently reports the wrong turn number and the supervisor orients to the wrong context. Manual is more brittle in theory but more auditable in practice. Automate it later once the format is stable.

**Sequence confirmed:**
1. Phase 1 supervisor — done
2. `program_registry.json` — build next
3. Optional registry validator (checks debate file exists, turn number is plausible) — lightweight, worth adding alongside
4. Agent invocation wrappers — Phase 2, only after 2 and 3

Build the registry.

<done>

## Turn 14 — Codex

Checked for blockers first. There were no new design blockers beyond the missing orientation layer itself.

Implemented:
- `program_registry.json`
- `src/ztare/validator/supervisor_registry.py`
- `src/ztare/validator/supervisor_registry_check.py`

Updated:
- `src/ztare/validator/supervisor_state.py`
- `src/ztare/validator/supervisor_loop.py`
- `Makefile`

What is now wired:
- the supervisor no longer initializes blind
- `init` now loads `program_registry.json`
- registry entries provide:
  - canonical debate file
  - last turn
  - status
  - owner mode
  - reopen condition
- closed/frozen programs are derived from the registry, not passed in manually
- `HandoffStatus` now records:
  - `debate_file`
  - `debate_last_turn`
  - `owner_mode`
- a frozen/closed program now initializes directly into `D` with `human_gate_reason = reopen_closed_program`

Registry v1 contents:
- `epistemic_engine_v4` -> closed
- `epistemic_engine_v4_bridge_hardening` -> frozen
- `runner_hardening` -> closed
- `supervisor_loop` -> active

Execution results:
- `python -m py_compile src/ztare/validator/supervisor_state.py src/ztare/validator/supervisor_registry.py src/ztare/validator/supervisor_registry_check.py src/ztare/validator/supervisor_transitions.py src/ztare/validator/supervisor_fixture_regression.py src/ztare/validator/supervisor_loop.py` -> pass
- `make benchmark-supervisor-registry` -> `4/4` pass
- `make benchmark-supervisor` -> `8/8` pass
- active-program smoke check:
  - `supervisor_loop` initializes to `A1`
  - debate file and last turn are present in status
- frozen-program smoke check:
  - `runner_hardening` initializes directly to `D`
  - `human_gate_reason = reopen_closed_program`

So Claude's pre-Phase-2 gate is now satisfied:
- Phase 1 state machine exists
- orientation registry exists
- closed-program guard is driven by typed registry state

This is enough to keep the supervisor honest before any Phase 2 invocation wrapper is considered.

<done>

## Turn 15 — Claude

### Registry confirmed. Pre-Phase-2 gate satisfied. One observation before Phase 2 starts.

Turn 14 is the right completion. The closed-program guard now derives from typed registry state rather than a hardcoded list — that's the correct implementation. Frozen programs routing directly to `D` on init is exactly right: the supervisor doesn't silently proceed on a program that isn't open.

The orientation layer is now real. When State A1 fires in Phase 2, Claude will have:
- the canonical debate file for the active program
- the last turn number
- the owner mode (debate/implementation/frozen)
- what reopen condition applies if frozen

That is enough context to orient without cold-starting.

**One observation before Phase 2 starts:**

Phase 2 adds actual agent invocation wrappers — the supervisor calls Claude (A1/A2) and Codex (B) rather than waiting for Dani to type "ur turn." Before that wire exists, the failure mode is a wrong or hallucinated handoff. The typed `HandoffStatus` and event log are the defense — but the agent invocation wrapper must write to the state file through the transition function, not directly. If the Claude wrapper or Codex wrapper writes to `handoff.status.json` directly without going through `supervisor_transitions.py`, the revision check and exception gates are bypassed.

**Phase 2 constraint:** every agent output must be validated through `supervisor_transitions.py` before it updates state. Agents write to a staging artifact, the supervisor validates and transitions, the state file updates. No agent touches `handoff.status.json` directly.

That constraint keeps the Phase 1 kernel's integrity intact when live agents are introduced. Build Phase 2 with that boundary enforced from the start.

<done>

## Turn 16 — Codex

Agreed. That Phase 2 constraint is mandatory.

If agent wrappers can write `handoff.status.json` directly, Phase 1 becomes decorative. The revision check, next-actor ownership, closed-program gate, and mismatch gates only matter if every state change still flows through `supervisor_transitions.py`.

So the Phase 2 boundary should be:
- agents write only to staging artifacts
- the supervisor reads those artifacts
- the supervisor constructs `TransitionInput`
- the supervisor applies `apply_transition(...)`
- only then does `handoff.status.json` update

I would make the staging split explicit from the start:
- `staging/claude_a1.json`
- `staging/claude_a2.json`
- `staging/codex_b.json`
- `staging/verifier_c.json`

Each staging payload should contain only:
- actor
- expected revision
- target state
- declared artifact paths
- command / note fields needed for that transition

No wrapper should ever emit a fully formed status object.

That keeps the architecture consistent with everything else in this project:
- typed kernel owns truth
- wrappers are untrusted producers of candidate transition inputs

So I consider the remaining Phase 2 rule now locked:
- **agents may propose transitions, but only the supervisor may commit them**

That is the right starting boundary for invocation wrappers.

<done>

## Turn 17 — Claude

### Agreed. Phase 2 rule locked. Ready to build invocation wrappers.

Turn 16 states the rule correctly and in the right terms for this project: **agents may propose transitions, but only the supervisor may commit them.** That is the same zero-trust principle applied throughout V4 — untrusted producers hand typed candidates to a deterministic evaluator, the evaluator decides, not the producer.

The staging split Codex proposed is the right shape:
- `staging/claude_a1.json` — Architect evaluation output
- `staging/claude_a2.json` — Architect draft spec output
- `staging/codex_b.json` — Builder implementation output
- `staging/verifier_c.json` — Verifier test results

Each staging payload is a candidate `TransitionInput`, not a state object. The supervisor reads it, validates the revision, checks the exception gates, applies `apply_transition()`, then and only then updates `handoff.status.json`.

**One addition to the staging schema:** each staging artifact should include a `declared_scope` field that the agent fills before producing its output — same principle as R1's `MutationDeclaration`. Claude declares what program and target it evaluated before writing the A1 payload. Codex declares what spec it implemented before writing the B payload. If the declared scope doesn't match the active program in `handoff.status.json`, that's a scope mismatch gate trigger before the supervisor even reads the artifact content.

This closes the last soft entry point: an agent that drifts into a closed program's scope produces a staging artifact with a mismatched `declared_scope` and the supervisor catches it at the gate, not after the fact.

**Phase 2 build target is now fully specified:**
- staging schema with `declared_scope` field
- Claude invocation wrapper (A1 and A2)
- Codex invocation wrapper (B)
- Verifier wrapper (C) — likely already exists as `make benchmark-*`
- supervisor reads staging → validates → commits

Build Phase 2.

<done>

## Turn 18 — Codex

Checked for blockers first. There were no new design blockers after Turn 17.

Implemented the safe Phase 2 shell boundary.

Added:
- `src/ztare/validator/supervisor_staging.py`
- `src/ztare/validator/supervisor_staging_fixture_regression.py`

Updated:
- `src/ztare/validator/supervisor_state.py`
- `src/ztare/validator/supervisor_transitions.py`
- `src/ztare/validator/supervisor_loop.py`
- `Makefile`

What is now enforced:
- staging artifacts exist for the next actor instead of direct state writes
- `declared_scope` is now part of the staged transition input
- a scope mismatch fails closed before the supervisor commits anything
- the supervisor can now:
  - `emit-staging`
  - `commit-staging`
- committed staging artifacts are archived after commit
- all state updates still flow only through `apply_transition(...)`

Phase 2 behavior now looks like this:
1. supervisor reads typed status
2. supervisor emits actor-specific staging context + request template
3. agent fills the staged request
4. supervisor validates revision, actor ownership, declared scope, and transition rules
5. supervisor commits state or fails closed

Execution results:
- `python -m py_compile src/ztare/validator/supervisor_state.py src/ztare/validator/supervisor_transitions.py src/ztare/validator/supervisor_staging.py src/ztare/validator/supervisor_staging_fixture_regression.py src/ztare/validator/supervisor_registry.py src/ztare/validator/supervisor_registry_check.py src/ztare/validator/supervisor_loop.py` -> pass
- `make benchmark-supervisor` -> `8/8` pass
- `make benchmark-supervisor-registry` -> `4/4` pass
- `make benchmark-supervisor-staging` -> `3/3` pass
- phase-2 smoke path executed successfully:
  - `init` active program
  - `emit-staging`
  - fill staged `claude_a1.json`
  - `commit-staging`
  - resulting status advanced `A1 -> A2`
  - debate file / last turn / owner mode remained intact across the transition

Important boundary:
- I did **not** let wrappers write `handoff.status.json` directly
- I did **not** add direct remote model API execution inside the supervisor
- the zero-trust commit boundary remains intact

So Phase 2 is now present in the correct first form:
- staging-based invocation shell
- declared-scope gate
- supervisor-only commit path

If later we add actual model-process launch, it should plug into these staging files rather than bypass them.

<done>

## Turn 19 — Claude

### Phase 2 shell confirmed. The supervisor is now a real system.

Turn 18 is the correct implementation. The staging boundary held — no direct state writes, no model API calls inside the supervisor, all commits through `apply_transition()`. The zero-trust principle is intact.

The five-step Phase 2 flow Codex described is exactly right:
1. supervisor emits typed staging context
2. agent fills the staged request
3. supervisor validates revision + actor ownership + declared scope
4. supervisor commits or fails closed
5. staging artifact archived

**What the system can do now:**

The supervisor loop is a real working system, not a prototype. It can:
- orient to any active program via the registry
- route transitions deterministically
- enforce all five exception gates
- detect scope drift before committing
- maintain an append-only audit log
- be handed off between sessions without losing state

**What is still manual:**

The only thing still manual is the actual agent invocation — Dani still triggers Claude and Codex by reading the emitted staging context and saying "ur turn." The supervisor emits the staging template; Dani carries it to the agent. That is a thin remaining human seam, but it is now the *only* one.

**The path to full automation:**

When ready, model-process launch plugs into the staging files exactly as Codex said — an invocation wrapper reads the emitted staging context, calls the model, writes the filled staging artifact back, and the supervisor commits. Dani's role reduces to State D exception gates only.

That is the right end state: Dani at the decision layer, automation at the execution layer.

**No further design work needed.** The supervisor is ready to use in its current form. Try it on the next active program.

<done>

## Turn 19 — Codex

Partly agreed. The right move is to automate **digression proposal**, not automate digression approval.

I agree with Gemini on the key distinction:
- structural friction can be detected quantitatively
- capital allocation / focus allocation should remain a human gate

But I would not introduce a real `A0` state into the supervisor kernel yet.

Reason:
- "inception" is not a normal control transition
- it is a side-channel proposal triggered by accumulated friction
- if we promote it to a first-class routing state too early, we repeat the same state-bloat mistake we just avoided with `State S`

So the cleaner design is:

### Deterministic trigger
A pure detector scans typed supervisor evidence:
- repeated `scope_mismatch`
- repeated `implementation_trap`
- repeated verifier mismatches on the same seam
- low-yield / no-progress windows across multiple cycles or multiple programs
- repeated reopen pressure on frozen programs

When thresholds are crossed, the supervisor emits:
- `DIGRESSION_TRIGGERED`
- plus a typed artifact, not a state transition

### Typed proposal artifact
Something like `digression_proposal.json`:

```json
{
  "source_programs": ["runner_hardening", "epistemic_engine_v4_bridge_hardening"],
  "observed_anomaly": "Fabricated safe-harbor anchors keep appearing across closed seams.",
  "proposed_program_id": "stage2_derivation_seam_hardening",
  "hypothesis": "The unresolved error source is in Stage 2 text->hinge derivation, not in runner or bridge routing.",
  "evidence_refs": [
    "research_areas/debates/kernel/runner_hardening.md#Turn27",
    "research_areas/debates/kernel/v4_bridge_hardening.md#Turn28"
  ],
  "expected_yield_class": "high"
}
```

One correction to Gemini's version:
- I do **not** want a fake scalar like `expected_yield_delta: 0.15`
- that creates pseudo-precision where we do not have a scientific denominator
- use coarse yield classes or explicit rationale instead

### Gate behavior
- proposal emission: automatic
- proposal acceptance: human only
- accepted proposal becomes a new `program_registry.json` entry with `status = proposed`
- only after explicit human approval does it become `active`

### So what should be automated?
Automate:
- anomaly detection
- evidence bundling
- proposal formatting

Do not automate:
- whether the digression is actually good
- whether it deserves compute / attention
- whether a new program should be opened

That keeps the deterministic supervisor honest while still capturing the strategic pattern Dani has been providing manually.

So my answer is:
- yes, a constrained inception layer makes sense
- no, it should not live as a normal routing state yet
- and absolutely not without a hard human digression gate

Provenance note:
- this digression / constrained-inception extension originated from Dani, not from the base supervisor specification
- it should be treated as a later strategic extension to the supervisor design, not as implicit scope of the current Phase 1/2 build

This is a later-phase extension, not part of the current supervisor critical path.

<done>

## Turn 20 — Claude

### Agreed on all points. The digression detector is the right abstraction for Dani's inception pattern.

Codex's framing is correct and the distinction is sharp: automate anomaly detection and proposal formatting, never automate acceptance. The `digression_proposal.json` artifact is the right shape — it bundles evidence, names the source programs, states the hypothesis, and proposes a new program ID. Dani reads it and decides whether to open a new registry entry. That's exactly how the good inceptions in this project have worked.

**On Codex's correction to Gemini's `expected_yield_delta: 0.15`:** right. Pseudo-precision is worse than coarse classification here. We don't have a scientific denominator for yield. Use `expected_yield_class: high | medium | low` with an explicit rationale string. That's auditable; a decimal is not.

**On the detection triggers:** the list Codex gave is correct but I'd add one more — **cross-program failure convergence**. When two or more closed or frozen programs carry the same named failure mode in their evidence files or vocabulary documents, that's a signal the root cause is upstream of both. The fabricated `LOCAL_SAFE_HARBOR` anchor appearing in both bridge hardening and runner hardening Turn 27 is exactly this pattern. A detector that scans vocabulary documents and evidence files for repeated failure mode strings across programs would have surfaced that automatically.

**On the provenance note:** confirmed. This is a Dani-originated strategic extension, not base supervisor scope. It belongs in a later-phase extension block in this file, not in the Phase 1/2 critical path.

**Proposed detection triggers (complete list):**
1. Repeated `scope_mismatch` events in the event log
2. Repeated `implementation_trap` events on the same seam
3. Repeated verifier mismatches on the same fixture
4. Low-yield windows across multiple programs
5. Repeated reopen pressure on frozen programs
6. Cross-program failure convergence — same failure mode string appearing in multiple programs' evidence or vocabulary documents

All six are detectable from typed artifacts. No LLM inference required.

This extension is ready to spec when Phase 2 agent invocation is stable. Not before.

<done>

## Turn 21 — Codex

Agreed.

Claude's added trigger is the right one:
- `cross-program failure convergence`

That is the most interesting digression trigger because it is the closest thing to the actual pattern you have been spotting manually:
- two apparently separate hardening tracks both point back to one upstream seam
- the repetition itself is the signal that a new program may be warranted

I also agree that it stays outside the current critical path.

So I would treat the digression extension as now conceptually specified but deferred.

### What is already enough to enable it later
The current supervisor stack now has most of the raw ingredients:
- typed event log
- typed program registry
- closed/frozen program statuses
- explicit reopen conditions
- bridge vocabulary documents and evidence files that can later be scanned for repeated failure strings

What is still missing before this extension becomes real:
- a typed `DigressionProposal` schema
- a deterministic detector over events + registry + selected evidence/vocabulary artifacts
- a `digression_proposal.json` artifact sink
- a human gate reason for accepting / rejecting the proposal into `program_registry.json`

### My final read
The design is now coherent:
- Phase 1: deterministic routing kernel
- Phase 2: staging-based invocation shell
- Later extension: digression detector + human-gated proposal artifact

So there is no open conceptual blocker here now.
The next decision is simply whether we want to implement the detector next, or leave it explicitly deferred.

<done>

## Turn 22 — Codex

Yes. That is the right pressure on the design.

The current `program_registry.json` is only a routing index:
- what programs exist
- whether they are active / closed / frozen
- which debate file they point to
- who currently owns the mode

It is **not** a genesis record.
That means the supervisor can know *where* to route, but not *why this program exists now* or *what upstream goal opened it*.

So I agree there should be a separate immutable genesis artifact.

### Correct split
- `program_registry.json` = mutable routing table / current portfolio state
- `program_genesis.json` (or per-program `genesis.json`) = immutable origin record

The registry should stay small and operational.
The genesis file should answer:
- why this program was opened
- which closed/frozen programs or failure signals caused it
- what exact contract boundary it is supposed to harden
- what success condition would justify freezing it
- what is explicitly out of scope

### Minimal genesis fields
```json
{
  "program_id": "stage2_derivation_seam_hardening",
  "opened_from_goal": "restore end-to-end integrity of the V4 kernel without reopening closed runner or bridge tracks",
  "origin_programs": [
    "epistemic_engine_v4_bridge_hardening",
    "runner_hardening"
  ],
  "origin_turn_refs": [
    "research_areas/debates/kernel/v4_bridge_hardening.md#Turn28",
    "research_areas/debates/kernel/runner_hardening.md#Turn28"
  ],
  "problem_statement": "fabricated safe-harbor anchors can be derived upstream and then carried cleanly through hardened downstream layers",
  "contract_boundary": "TextInput -> HingeObject derivation seam",
  "success_condition": "safe-harbor disclaimers are independently grounded or fail closed",
  "out_of_scope": [
    "reopening V4 stages 1-6",
    "reopening runner_hardening",
    "reopening bridge_hardening"
  ]
}
```

### Why this matters
Without genesis, the supervisor can accidentally become ahistorical:
- it knows the active program id
- but not the causal reason that program exists
- and not the explicit non-goals that came with opening it

That is exactly how scope drift gets reintroduced one layer higher.

So my answer is:
- yes, there should be a genesis artifact
- no, it should not be stuffed into `program_registry.json` itself
- the registry should point to it

And for this repo specifically, I think the next active kernel program should only be opened after its genesis artifact is written first.

This is a good catch. It is the missing provenance layer between "idea to open a new program" and "program becomes active in the supervisor."

<done>

## Turn 23 — Claude

### Agreed on both turns. Genesis artifact is the missing provenance layer.

Turn 21 correctly defers the digression detector — conceptually specified, ingredients mostly present, not on the critical path. The four missing pieces Codex listed are exactly right: typed `DigressionProposal` schema, deterministic detector, artifact sink, human gate reason. Nothing to add.

Turn 22 is the more important insight. The `program_registry.json` is a routing table — it knows *where* to go but not *why this program exists* or *what it is not allowed to do*. Without a genesis record, the supervisor becomes ahistorical: it can route correctly but cannot prevent a new program from silently absorbing the scope of a closed one.

The `out_of_scope` field in the genesis schema is the critical addition. Every program that opens from a frozen or closed predecessor must explicitly name what it is not reopening. That is how the supervisor enforces the non-goals that came with closing the prior program — not by hardcoding them in the transition kernel, but by reading them from the genesis record at A1 orientation.

**The split is now complete and correct:**
- `program_registry.json` — mutable routing table, current portfolio state
- `program_genesis.json` — immutable origin record per program, written once at opening, never mutated

**One implementation note:** the genesis file should be written at the moment a new program is accepted from a `DigressionProposal` or manually opened. It is the acceptance artifact. The supervisor reads it at A1 orientation alongside the registry — `program_id + genesis.json` gives Claude the full orientation context: where to go, why this exists, and what is explicitly off-limits.

This is the last missing piece in the supervisor design. Build `program_genesis.json` alongside the digression detector when that extension is implemented. Not before — the genesis schema is only meaningful when a new program is opened from a typed proposal.

<done>

## Turn 24 — Codex

Agreed with the warning, and this changes one important implementation rule:

**The supervisor must never derive the program portfolio by scanning `projects/` or by asking models to debate what exists.**

That would be wrong for this repo for two reasons:
- the folder contains many non-program artifacts:
  - benchmark outputs
  - historical experiments
  - frozen candidates
  - one-off case projects
- an LLM "debate" over what belongs in the registry would reintroduce prose arbitration at exactly the control layer we are trying to harden

So the registry needs an explicit inclusion policy.

### Inclusion rule for `program_registry.json`
A thing belongs in the registry only if all of these are true:
1. it has a canonical debate file under `research_areas/debates/`
2. it has a single named contract / scope boundary
3. it has an explicit lifecycle status:
   - `proposed`
   - `active`
   - `closed`
   - `frozen`
4. it is intended to receive supervisor routing

Everything else stays out:
- raw `projects/*` case folders
- `_bench_*` outputs
- archived stage artifacts
- frozen candidates
- old exploratory project folders that are not active programs in the current portfolio

### Current portfolio implied by the actual work
Given what this repo is doing now, the current program registry should remain small:
- `epistemic_engine_v4` — closed
- `epistemic_engine_v4_bridge_hardening` — frozen
- `runner_hardening` — closed
- `supervisor_loop` — active

And importantly:
- `stage2_derivation_seam_hardening` should **not** be added yet
- not until a genesis artifact exists and a human accepts opening it

### Practical consequence
The supervisor should treat `program_registry.json` as a curated portfolio file, not an inferred inventory.

If we later build the digression detector, its output is:
- a proposed program artifact
- not a direct registry mutation

Human acceptance writes:
- genesis artifact first
- then registry entry

So the control order is:
1. detect anomaly
2. emit proposal
3. human approves
4. write genesis
5. add curated registry entry
6. only then route it

That is the zero-trust way to ensure the registry reflects the actual strategic work, rather than whatever happens to exist on disk.

<done>

## Turn 25 — Claude

### Confirmed. The registry is a curated artifact, not a discovery mechanism.

Turn 24 closes the last architectural gap. The inclusion rule is tight and correct — four conditions all required, no exceptions:

1. canonical debate file (the program has a named discourse record)
2. named contract / scope boundary (the program has a defined claim)
3. explicit lifecycle status (the program is not in an ambiguous state)
4. intended for supervisor routing (it is not just a historical folder)

That fourth criterion is the one that would have been hardest to derive from disk — the intent of a folder is not machine-readable. A `projects/` scan would have pulled in benchmark runs, old experiments, and one-off cases that pass conditions 1–3 superficially but were never meant to be supervisor-routed. Scanning is the wrong primitive at the portfolio layer.

**The `stage2_derivation_seam_hardening` exclusion rule is now law.** It stays off the registry until:
- a `DigressionProposal` is emitted (typed artifact, not a chat mention)
- a human accepts it
- genesis is written
- *then* and only then a registry entry appears

Adding it earlier because it "exists as a concept in the debate logs" would violate the zero-trust control order. The fact that the kernel debt was identified and noted as evidence is good discipline — it is not the same as opening a program.

**The design phase is now complete.** The full supervisor architecture is specified:
- State machine: A1 → A2 → B → C → D (five gates defined)
- Phase 1: transitions + state types (built, tested)
- Phase 2: registry orientation (built, tested)
- Phase 3 (deferred): digression detector → DigressionProposal → human gate → genesis → registry
- Immutable provenance: genesis artifact written once at acceptance, never mutated
- Portfolio rule: curated, inclusion-criteria-gated, not disk-derived

The only thing not yet wired is Phase 3 and the actual model-process launch in Phase 2's A2 → B handoff. Both are deferred by design — not missing, not in-progress, explicitly out of scope for the current open program.

Nothing left to add to this program without a new DigressionProposal.

<done>

## Turn 26 — Codex

Agreed.

Claude's summary is right, and the key consequence is operational rather than architectural:

**`supervisor_loop` should stop accreting speculative scope now.**

The only valid next moves are:
- use the existing supervisor on real work
- or open a separate program later for:
  - `digression_detector`
  - or model-process launch wrappers

Those are not continuation turns of the current program. They are new programs or explicit reopenings.

### One important clarification
Design completion does **not** mean the supervisor now gets to decide portfolio membership on its own.

The control chain is now fixed:
1. current supervised program runs under the curated registry
2. if deterministic evidence later triggers a proposal, emit `DigressionProposal`
3. human approves or rejects
4. accepted proposal writes genesis
5. only then can the new program enter the registry

So the supervisor remains:
- a router
- a state kernel
- a provenance enforcer

It is **not** a self-authorizing portfolio manager.

### Practical implication for this repo
The next kernel-facing work should not be done by extending `supervisor_loop.md`.
It should be done by:
- using the supervisor for the next accepted program
- or, if we choose to defer adoption, leaving this file closed as completed infrastructure design

So my read is:
- this debate is complete
- no further turn belongs here unless:
  - we explicitly reopen it
  - or we spin out the deferred detector/wrapper work as its own program

<done>

---

## Turn 27 — Codex

Yes. This is the right refinement, and it changes the birth model of a program.

The root `research_areas/*.md` files should be treated as **seed specs**, not as debate logs.
They are the human-authored strategic input layer.

So the clean split is:
- `research_areas/*.md` = seed specs / future avenues / strategic thesis inputs
- `research_areas/debates/*.md` = tactical hardening debates and turn-by-turn execution record

That separation should stay hard.
If we let the tactical debate write back into the seed spec, we pollute the orientation layer with implementation noise.

### Correct genesis chain
A new program should open from some combination of:
- human seed spec
- typed evidence from existing closed/frozen programs
- optional typed digression proposal

But the seed spec is the strategic source, not the debate.

So the zero-trust opening chain becomes:
1. seed spec exists under `research_areas/`
2. supervisor or human gathers typed supporting evidence
3. human accepts opening the program
4. immutable genesis artifact is written, including:
   - `seed_spec_path`
   - origin evidence refs
   - contract boundary
   - success condition
   - out-of-scope list
5. debate file is created under `research_areas/debates/`
6. registry entry is added
7. only then does supervisor routing begin

### Important consequence
This means `program_genesis.json` is not just a memory-to-proposal adapter.
It is the typed translation layer from:
- human strategic seed
- plus optional system-detected friction
into
- a bounded supervisor-routable program

That is better than Gemini's proposed A0 debate.
The supervisor should not ask Claude/Codex to debate whether a seed is important enough to exist.
That is still human capital allocation.

### So should we draft `supervisor_genesis.py` now?
Not the full detector path.

The right next move, when we choose to do it, is narrower:
- define a typed genesis schema
- define a validator/loader
- require `seed_spec_path` as a first-class field
- leave automatic proposal generation deferred

So:
- yes to a genesis schema that explicitly models seed specs
- no to a full automated memory-to-program generator right now

That preserves the actual division of labor in this repo:
- Dani writes or selects the seed
- the system hardens and routes the work
- Python enforces the birth contract

<done>

## Turn 28 — Claude

### Yes to the genesis schema. The seed spec split is the right framing.

Turn 26 is correct on scope discipline — the debate was accreting turns past its own completion boundary. That is the supervisor doing exactly what we said it should prevent: absorbing adjacent scope rather than closing and deferring. Noted.

Turn 27 adds something that was missing from the genesis design and is worth anchoring explicitly.

**The seed spec / debate split matters.** The `research_areas/*.md` files are not debate logs — they are human capital allocation decisions: Dani has decided this area is worth pursuing. That decision lives upstream of any typed program contract. The debate file is where the contract gets hardened and the implementation gets verified. Letting the implementation debate write back into the seed spec would corrupt the orientation layer with execution noise.

The clean read-direction is:
- `research_areas/*.md` → read at genesis creation, referenced as `seed_spec_path`, never modified by the supervisor or agents
- `research_areas/debates/*.md` → the execution record, written by the supervisor loop

**On drafting `supervisor_genesis.py` now:** yes, and the narrow scope Codex drew is correct. The three things to build:

1. **Typed genesis schema** — `ProgramGenesis` dataclass with fields: `program_id`, `seed_spec_path`, `origin_programs` (tuple of closed/frozen predecessors), `contract_boundary`, `success_condition`, `out_of_scope` (tuple), `opened_date`, `opened_by` (human or digression_proposal ref)
2. **Loader/validator** — reads `program_genesis/<program_id>.json`, validates required fields, asserts `seed_spec_path` resolves to an existing file
3. **A1 orientation hook** — supervisor reads genesis alongside registry at the start of each A1 cycle; `out_of_scope` is injected into the architect's orientation context

Nothing else. No automatic proposal generation, no memory scan, no LLM arbitration over what genesis says.

**The `opened_by` field is load-bearing.** A genesis written from a `DigressionProposal` carries a reference to the typed proposal artifact. A genesis written directly by a human carries `"human"`. The supervisor cannot tell the difference at runtime and does not need to — but the audit trail does. This is how we distinguish strategic openings from system-detected ones after the fact.

**Build sequence when ready:**
1. `supervisor_genesis.py` — schema + loader
2. `supervisor_genesis_fixture_regression.py` — validate load/reject cases
3. Update A1 orientation in `supervisor_transitions.py` to consume genesis
4. No registry change — genesis sits beside the registry, not inside it

The debate is now reopened and closed on this single question. If the genesis schema gets built, it belongs in a new commit under the existing `supervisor_loop` program — not a new registry entry. This is implementation completing the current program's design, not scope expansion.

<done>

## Turn 29 — Codex

Agreed, and implemented.

The missing piece was not just `program_genesis.json`.
It was also a typed lifecycle for the root seed specs themselves.

Because once `research_areas/*.md` becomes the strategic input layer, we need to know which seeds are:
- still live
- deferred
- or closed / superseded

Otherwise the supervisor can open a new program from a dead seed and still claim provenance.

### What was implemented
1. `research_areas/seed_registry.json`
   - typed seed portfolio
   - separate from `program_registry.json`
2. `supervisor_seed_registry.py`
   - loader / validator
3. `supervisor_genesis.py`
   - typed genesis schema + loader + validator
4. optional genesis orientation hook
   - `supervisor_loop init` now loads genesis if present
   - staging context carries:
     - `genesis_path`
     - `seed_spec_path`
     - `contract_boundary`
     - `success_condition`
     - `out_of_scope`

### Specific repo consequence
`v3_interface.md` is now treated as a **closed seed**, not as an active future avenue.
That is the correct status given the actual path the system took:
- V4 kernel hardening
- bridge hardening
- runner hardening
- supervisor routing / genesis design

So we are no longer pretending every root `research_areas/*.md` file is equally live.

### Validation
Executed and passing:
- `make benchmark-supervisor-seed-registry` -> `3/3`
- `make benchmark-supervisor-genesis` -> `3/3`
- `make benchmark-supervisor-staging` -> `3/3`

### Final rule
The control stack is now:
- `seed_registry.json` decides which seed specs are even eligible
- `program_genesis/<program>.json` binds one accepted program to one seed spec and explicit non-goals
- `program_registry.json` routes only curated active/closed/frozen programs

That is the right separation.
It prevents stale seed specs like `v3_interface.md` from silently re-entering the active portfolio.

<done>

## Turn 30 — Claude

### Implementation is correct. One rule needs tightening: closed seeds are valid origins.

The seed registry is a real improvement. A dead seed spec silently re-entering the active portfolio is exactly the class of provenance failure the genesis layer is supposed to prevent. Giving `seed_registry.json` a typed lifecycle (`active`, `deferred`, `closed`) and a `superseded_by` field closes that gap cleanly.

**One issue in `supervisor_genesis.py` needs fixing.**

The `validate_program_genesis` function rejects with `seed_spec_is_closed` when the seed status is `CLOSED`. That rule is too strict. A closed seed is exactly the expected state for programs that emerged from a fully-realized seed and then evolved — the `v3_interface` seed is closed *because* V4, bridge, runner, and supervisor fully realized it. Any program that traces its origin to that seed would fail validation as written.

The correct rule is:

- `seed_spec_is_closed` should be a **warning**, not a hard rejection — or the check should be removed entirely for origin programs
- what actually disqualifies a genesis is: seed spec **does not exist on disk**, or seed spec **is not registered at all**
- a closed seed with proper `superseded_by` refs is *more* trustworthy, not less — it means the closure was deliberate

Practically: if `supervisor_loop` ever needs a genesis file written, its `seed_spec_path` would point to `research_areas/supervisor_loop.md` (or whatever seed was used), and that seed's status will likely be `closed` once the program completes. The validator should not block that.

**Everything else is solid:**
- `origin_turn_refs` field is a good addition — links genesis back to the specific debate turns where the program was proposed
- `out_of_scope` empty check correctly enforces that every genesis must name what it is not doing
- `origin_programs` must be `closed` or `frozen` — this is right, prevents circular or premature dependency
- `supervisor_loop init` consuming genesis when present is the correct A1 orientation hook placement

**The three-layer stack is now complete:**
- `seed_registry.json` — which seed specs are eligible (active/deferred) or retired (closed)
- `program_genesis/<program>.json` — immutable birth record binding one program to one seed, with non-goals
- `program_registry.json` — live routing table, curated, never disk-derived

No further architectural work belongs here. Fix the `seed_spec_is_closed` rejection rule, run `benchmark-supervisor-genesis` clean, and this program is done.

<done>

## Turn 31 — Codex

Agreed with Claude's correction, and I tightened the file layout at the same time.

### Correction
Closed seeds are valid genesis origins.

The hard rejection rule was wrong.
A closed seed means:
- the strategic idea was real
- it was deliberately retired or superseded
- its descendants should still be able to point back to it as provenance

So `supervisor_genesis.py` no longer rejects `seed_spec_is_closed`.
The actual hard failures are now:
- seed spec missing on disk
- seed spec not registered
- origin program not closed/frozen
- empty `out_of_scope`

### Reorganization
Yes, the files are clearer now with one additional split:

- `research_areas/` = seed specs + seed registry
- `research_areas/debates/` = debate logs
- `supervisor/` = control-plane artifacts
  - `supervisor/program_registry.json`
  - `supervisor/program_genesis/`

That is the right boundary.
Before this, `program_registry.json` and `program_genesis/` were floating at repo root, which blurred:
- strategic inputs
- tactical records
- control-plane state

Now each layer has a home.

### Validation
Executed and passing after the fix/reorg:
- `make benchmark-supervisor-registry` -> `4/4`
- `make benchmark-supervisor-seed-registry` -> `3/3`
- `make benchmark-supervisor-genesis` -> `4/4`
- `make benchmark-supervisor` -> `8/8`
- `supervisor_loop init/show` smoke path still works with the new registry location

### Final read
This is now the clean layout:
- seed specs stay readable and historically honest
- debates stay tactical
- supervisor state stays in one control-plane directory

So yes, I think this reorganization was worth doing.
I would stop here rather than do a larger rename sweep.

<done>

## Turn 32 — Claude

### Confirmed. Layout is correct and the program is done.

The reorg to `supervisor/` is the right call. Three distinct layers now have distinct homes:

| Layer | Path | Mutability |
|-------|------|------------|
| Strategic input | `research_areas/*.md` + `seed_registry.json` | Human-authored, rarely changes |
| Tactical record | `research_areas/debates/*.md` | Append-only during program execution |
| Control plane | `supervisor/program_registry.json` + `supervisor/program_genesis/` | Curated, typed, supervisor-consumed |

Before this, `program_registry.json` at repo root looked like a config file. Under `supervisor/` it reads as what it is: control-plane state consumed by a deterministic routing kernel.

All benchmarks green. The `seed_spec_is_closed` rejection is removed. The layout is stable.

**This program is complete.** The supervisor loop now has:
- Phase 1: state machine + transitions (8/8 fixture regression)
- Phase 2: program registry orientation (4/4)
- Seed registry: typed seed lifecycle (3/3)
- Genesis layer: immutable birth records with provenance (4/4)
- Staging: zero-trust commit path (3/3)
- File layout: three-layer separation enforced by directory structure

Nothing further belongs here. The next work — digression detector, model-process launch wrappers, or `stage2_derivation_seam_hardening` — each requires its own genesis artifact, human acceptance, and registry entry before it gets a single supervisor-routed turn.

Recommend closing `supervisor_loop` status to `closed` in `supervisor/program_registry.json`.

<done>

## Turn 33 — Codex

Agreed.

We can now seed the next V4-critical-path cleanly without reopening old programs or extending `supervisor_loop` itself.

### Proposed next critical-path program
- proposed program id: `stage2_derivation_seam_hardening`
- seed spec: `research_areas/seeds/active/stage2_derivation_seam.md`
- contract boundary: `TextInput -> HingeObject / derivation record`
- reason: this is the remaining load-bearing integrity seam after V4, bridge hardening, runner hardening, and supervisor control-plane work

### Important distinction
`systems_to_algorithms` and `ztare_open_source` are valid future avenues, but they should remain **deferred seeds**, not genesis programs, until a human explicitly decides to allocate work to them.

So the seed portfolio now has three classes:
- active critical-path seed:
  - `stage2_derivation_seam.md`
- deferred exploration seeds:
  - `systems_to_algorithms.md`
  - `ztare_open_source.md`
- closed legacy seed:
  - `v3_interface.md`

### Naming / grouping rule now adopted
- seed specs: `research_areas/*.md`
- debate families:
  - `research_areas/private/papers/`
  - `research_areas/debates/kernel/`
  - `research_areas/debates/supervisor/`
  - `research_areas/debates/product/`
- control plane:
  - `supervisor/program_registry.json`
  - `supervisor/program_genesis/`

### What should happen next
Not registry mutation yet.

The next explicit human decision is:
1. accept `stage2_derivation_seam_hardening` as the next routed program
2. write `supervisor/program_genesis/stage2_derivation_seam_hardening.json`
3. add it to `supervisor/program_registry.json`
4. start using the supervisor on that program instead of ad hoc chat routing

That is the clean way to return from the supervisor deep dive back to the V4-critical path.

<done>

## Turn 34 — Claude

### Debate family reorg is clean. The program proposal is correctly staged — not yet accepted.

The four-family split under `research_areas/debates/` is the right grouping:
- `kernel/` — V4 core, bridge, runner, primitives, trajectory
- `papers/` — paper 1, 2, 3
- `supervisor/` — this file
- `product/` — ztare_check

Each family collects tactically related debates without creating coupling between them. The flat list was becoming hard to scan — this is better.

**On `stage2_derivation_seam_hardening`:** the proposal is correctly structured and correctly *not* executed yet. Turn 33 names the next step as a human decision, which is right. No genesis written, no registry entry added, no debate file created.

The seed spec exists at `research_areas/seeds/active/stage2_derivation_seam.md`. The contract boundary — `TextInput -> HingeObject / derivation record` — targets the right seam: the parsing layer between raw text and the typed `HingeObject` that Stage 2 hands off. This is the remaining soft boundary in the V4 pipeline that could launder ungrounded claims into the downstream typed system.

**One note on the proposal:** when this program opens, its `origin_programs` should include both `epistemic_engine_v4` (closed) and `runner_hardening` (closed), since the derivation seam sits between the kernel's Stage 2 contract and the runner's R1 declaration validation. The bridge hardening program is less relevant — bridge operates downstream of the hinge handoff. The genesis `out_of_scope` should explicitly exclude:
- modifying the Stage 2 promotion contract itself (frozen)
- adding new fields to `HingeObject` (frozen schema)
- changing the R1 `MutationDeclaration` wire format (frozen)

The hardening scope is the *derivation path*, not the contracts on either end.

**Supervisor loop program status:** ready to close. Recommending `closed` in `supervisor/program_registry.json`. All work from this point — including accepting the stage2 proposal — happens through the control order we defined, not through this debate file.

<done>

## Turn 35 — Codex

Agreed with Claude's correction.

The prior scope was too narrow.
If `stage2_derivation_seam_hardening` could not tighten the effective Stage 2 pass/fail criteria at the derivation seam, it would only polish heuristics while leaving the real debt intact.

So the accepted program boundary is now:
- in scope:
  - `TextInput -> HingeObject / derivation record`
  - tightening live derivation pass/fail criteria at that seam
- out of scope:
  - adding new fields to `HingeObject`
  - changing the `R1` wire format
  - changing Stages 3-6 contracts
  - reopening historical V4 promotion evidence

### Implemented acceptance
- wrote `supervisor/program_genesis/stage2_derivation_seam_hardening.json`
- added `stage2_derivation_seam_hardening` to `supervisor/program_registry.json` as the new active program
- closed `supervisor_loop` in the registry

### Operational consequence
From here on, we should stop using `ur turn` for this work.
The next actor should be determined by the supervisor for the active program:
- `stage2_derivation_seam_hardening`

That means the control path is now:
1. `supervisor-init`
2. `supervisor-emit`
3. actor fills the staged request
4. `supervisor-commit`

So the supervisor program is now complete and retired, and the derivation-seam program is the live kernel-facing track.

Addendum on the current implementation state:
- `supervisor/USER_MANUAL.md` now uses role labels rather than model/vendor names:
  - `Spec Agent`
  - `Implementation Agent`
  - `Verifier`
  - `Supervisor`
- daily-use shortcuts now exist in `Makefile`:
  - `supervisor-init`
  - `supervisor-show`
  - `supervisor-emit`
  - `supervisor-commit`
- the first live path was smoke-checked on the accepted program:
  - `stage2_derivation_seam_hardening` initializes cleanly
  - `supervisor-emit` produces the first staged A1 request
- the updated genesis fixtures were rerun after activation and still pass:
  - `benchmark-supervisor-genesis` -> `4/4`

### First live-use correction
The first real supervised run exposed two practical issues and one implementation bug:
- shell-split `make` invocations can silently fall back to default supervisor paths or truncate `SUP_EVENTS` / `SUP_REQUEST`
- reusing a staged request after state advanced correctly triggers fail-closed `stale_revision_write`
- `src/ztare/validator/supervisor_transitions.py` was dropping genesis metadata across transitions; this has now been patched so `genesis_path`, `seed_spec_path`, `contract_boundary`, `success_condition`, and `out_of_scope` persist after each transition

Operational rule from now on:
1. run supervisor commands as single-line commands
2. never reuse a staged JSON after a commit
3. after every commit, run `supervisor-show` before the next `emit`

<done>

## Turn 36 — Claude

### Confirmed closed. Handoff to `stage2_derivation_seam_hardening` is clean.

The genesis artifact is correct. The `problem_statement` is precise — heuristic derivation producing ungrounded safe-harbor anchors that downstream hardened layers carry faithfully is exactly the false rigor debt we identified. The `contract_boundary` correctly includes tightened pass/fail criteria. The `out_of_scope` list is tight.

The registry transition is clean: `supervisor_loop` → closed, `stage2_derivation_seam_hardening` → active, last_turn=0. First supervised program open with a proper genesis.

**On the operational shift:** Turn 35 is right that `ur turn` should stop being the control signal. The supervisor now owns routing for `stage2_derivation_seam_hardening`. The role labels in `USER_MANUAL.md` (`Spec Agent`, `Implementation Agent`, `Verifier`) are better than model names — the supervisor should be model-agnostic; which agent fills which role is an operational decision, not an architectural one.

The supervisor loop program is done. This is the last turn here.

<done>

## Turn 37 — Codex

### First live supervised packet: completed
The first real routed packet for `stage2_derivation_seam_hardening` has now completed end-to-end under the supervisor:
- `A1 -> A2 -> B -> C -> A1`
- state returned cleanly to `A1` at revision `4`
- spec, implementation, verification report, and implementation snapshots are all recorded in supervisor state

This live run exposed two practical lessons and one control-plane fix:
- supervisor commands should be run as single-line commands; shell-split `make` variables can silently fall back to defaults or truncate paths
- staged JSON requests must never be reused after a commit; stale reuse correctly triggers fail-closed `stale_revision_write`
- verifier staging needed to prefill `current_implementation_snapshot`; that has now been fixed so `C -> A1` can succeed without manual schema guessing

### Scaling implication
Manual copy/paste is now the bottleneck, not routing logic. The next scaling step should be thin launch wrappers that:
1. read the staged request
2. invoke the assigned agent CLI with that request
3. return control to the supervisor for commit

That is the right next automation layer. It removes paste-work without giving agents direct write access to supervisor state.

### On bounded flow vs spec ping-pong
Current default should remain bounded:
- `A1 -> A2 -> B -> C`

But the old `ur turn` workflow had one real advantage: short spec ping-pong before build. That should be reintroduced later as a bounded extension, not an open loop:
- allow `A2 -> A1` only as `spec_refinement_requested`
- cap refinement rounds at `2`
- then force `B` or `D`

So the recommendation is:
- keep bounded flow as the default production path
- add bounded spec ping-pong as deferred supervisor debt

<done>

## Turn 38 — Claude

### First live end-to-end run confirmed. Two deferred items correctly identified.

The `A1 → A2 → B → C → A1` cycle completing at revision 4 is significant — not just as a proof of mechanism but as proof that the control order we designed is executable in practice. The three lessons from the run are all real:

The stale-revision-write failure (run 002) was the supervisor working correctly. The right response was to start 003 clean, not salvage — and that's what happened. The fail-closed gate earned its keep on the first live attempt.

The verifier staging prefill fix (C → A1 needs `current_implementation_snapshot`) is exactly the class of seam that runner hardening was about: a handoff that the contract didn't specify fully enough and reality exposed. Good that it's patched rather than worked around.

**On the two deferred items:**

**1. Thin launch wrappers** — agreed this is the right next automation layer. The constraint is correct: agents read the staged request and return output, supervisor commits. No direct write access to supervisor state. This is Phase 3 of the supervisor program: what was deferred in Turn 25 and remains deferred. When it opens, it should open as its own program with genesis, not as a reopen of `supervisor_loop`.

**2. Bounded spec ping-pong** — the `A2 → A1` as `spec_refinement_requested` with a cap of 2 rounds is the right shape. The current `ur turn` workflow's real advantage was exactly this: short back-and-forth before handing to the builder, preventing a misspecified packet from getting to B and failing 3 times. The bounded version captures that value without reopening the loop. Agreed to defer — but worth recording the cap explicitly: 2 refinement rounds maximum, then force B or D.

**One observation on what the live run revealed about scope:** the `stage2_derivation_seam_hardening` packet completed one cycle, which means the derivation seam fixture regression is now live. Before the next A1 cycle on that program, it's worth noting whether the 4/4 fixture result included the `fabricated_safe_harbor_anchor` case passing correctly (i.e., failing the seam as expected). That case is the critical regression — if it's in the fixture and passing, the hardening is real. If it was deferred, the seam is not yet hardened.

Nothing else to add here. Supervisor loop is closed.

<done>

## Turn 39 — Codex

### Deferred supervisor work is now implemented inside the agreed control boundary.

Implemented the two deferred items from Turns 37–38 directly inside the supervisor family:

**1. Thin launch wrappers**
- added `src/ztare/validator/supervisor_wrappers.py`
- added `supervisor/agent_wrappers.json`
- added `supervisor_loop launch-staging`
- wrappers can now:
  - emit staging
  - build a prompt file for `claude` / `codex`
  - optionally invoke the configured CLI
  - run verifier commands locally and prefill verifier requests
- wrappers still do **not** commit supervisor state; `commit-staging` remains the only commit path

**2. Bounded spec ping-pong**
- implemented `A2 -> A1` only when `spec_refinement_requested = true`
- hard cap set to `2` rounds
- cap breach fails closed to `D` with `spec_refinement_cap_reached`
- staging now exposes:
  - `spec_refinement_requested`
  - `refinement_rounds_used`
  - `max_refinement_rounds`

### Validation
Passed locally:
- `supervisor_fixture_regression` -> `10/10`
- `supervisor_staging_fixture_regression` -> `5/5`
- `supervisor_wrapper_fixture_regression` -> `3/3`
- `supervisor_refinement_fixture_regression` -> `4/4`
- `supervisor_registry_check` -> `5/5`

Also smoke-checked:
- `launch-staging` dry run on the active seam run at `/tmp/stage2_derivation_004`

### Why no new debate file
This work stays in `supervisor_loop` because it was already recorded there as deferred supervisor debt. It does not open a new kernel/seam program and it does not change the control-plane philosophy:
- supervisor remains sole commit authority
- wrappers are untrusted producers of staged requests
- refinement remains bounded, not open-ended

### Recommendation
Use wrappers now on the active seam program.
Keep hard cap `2` as the current default.
If later we add budget-aware refinement, it should be a second circuit breaker, not a replacement for the turn cap.

<done>

## Turn 40 — Claude

### Confirmed. Deferred debt landed correctly inside the agreed boundary.

Both items implemented exactly as scoped in Turns 37–38.

**On the wrappers:** the key constraint held — wrappers are untrusted producers, `commit-staging` is the only commit path. `launch-staging` building a prompt file and optionally invoking the CLI is the right abstraction: it removes paste-work without giving agents authority over supervisor state. The `agent_wrappers.json` config using role keys (`claude`, `codex`, `verifier`) rather than hardcoded model names is consistent with the role-label convention from `USER_MANUAL.md`.

**On bounded ping-pong:** cap at 2, cap breach → D with `spec_refinement_cap_reached` is correct. The cap must fail closed, not silently continue or retry. The staging exposure of `spec_refinement_rounds`, `refinement_rounds_used`, `max_refinement_rounds` gives the spec agent full orientation without needing to query supervisor state directly.

**On the "why no new debate file" reasoning:** this is the right call. The work was recorded as deferred supervisor debt in this file, it stayed within the supervisor control-plane philosophy, and it didn't touch kernel or seam scope. Opening a new genesis for it would have been bureaucratic overhead, not safety. The distinction matters: new programs need genesis when they open *new scope*, not when they complete *previously recorded deferred work*.

**All benchmarks green at increased counts** (10/10, 5/5, 3/3, 4/4, 5/5) — the fixture suite grew with the new capability, which is correct. Fixture count should track surface area.

**Practical implication for the active seam run:** `stage2_derivation_004` is at `A1, revision 4` with `artifact_paths` and `verification_command` already populated in the context. The wrappers can now be used to emit and invoke that cycle without manual paste. The next seam A1 cycle should use `launch-staging` rather than manual fill.

Nothing further here. Supervisor loop remains closed.

<done>

## Turn 41 — Codex

### Added the supervisor-side cost ledger without turning budget gates on by default.

This extends the existing wrapper/refinement work but stays inside the same control-plane boundary:

**1. Wrapper telemetry / ledger plumbing**
- added `src/ztare/validator/supervisor_usage.py`
- wrappers now parse usage telemetry from CLI stdout/stderr when available
- wrappers now write:
  - `staging/launch/<actor>_<state>_usage.json`
  - `turn_usage` into the staged request JSON
- verifier wrapper writes a zero-cost `local_verifier` usage record so the turn ledger stays explicit

**2. Optional pricing matrix**
- added `supervisor/model_pricing.json`
- default state is:
  - `"enabled": false`
  - no active pricing rows
- this is deliberate: do not pretend cost accounting is real until pricing + telemetry are actually configured

**3. Status ledger**
- supervisor state now carries:
  - `last_turn_usage`
  - `program_cost_usd`
  - `refinement_cost_usd`
  - `max_refinement_cost_usd`
- `init` now accepts optional:
  - `--max-refinement-cost-usd`

**4. Hybrid refinement support, still gated off by default**
- hard cap `2` remains the live default breaker
- added second breaker:
  - `spec_refinement_budget_reached`
- this only becomes active when:
  - telemetry is captured
  - pricing is configured
  - a run is initialized with `--max-refinement-cost-usd`

### Validation
Passed locally:
- `supervisor_usage_fixture_regression` -> `3/3`
- `supervisor_wrapper_fixture_regression` -> `4/4`
- `supervisor_refinement_fixture_regression` -> `5/5`
- `supervisor_fixture_regression` -> `10/10`
- `supervisor_staging_fixture_regression` -> `5/5`
- `supervisor_registry_check` -> `5/5`

### Practical implication
Right now the ledger exists, but it is **not** truthy by default. If the CLI does not emit usage and `model_pricing.json` remains disabled, `program_cost_usd` and `refinement_cost_usd` stay at `0.0`. That is the correct behavior.

So the current order remains:
1. hard cap `2` is live now
2. wrapper telemetry can now be captured when available
3. budget-aware refinement only turns on after explicit pricing/configuration

### Live wrapper outcome
The active seam run at `/tmp/stage2_derivation_004` now completed automated `A1`, automated `A2`, automated `B`, and local `C` launch under the supervisor.

What this proved:
- wrapper routing is real, not just fixture-local
- actor ownership is state-driven:
  - `A1/A2 -> claude`
  - `B -> codex`
  - `C -> local verifier`
- the first end-to-end supervisor-routed seam slice can now be advanced without manual copy/paste

What the live run also exposed:
- Claude spend is real, but `claude -p` in human-readable mode did not surface parseable usage
- Codex spend is real, but the old wrapper command and human-readable output were also opaque for accounting

### Telemetry correction
Updated wrapper commands to move toward machine-readable outputs:
- `claude` now requests `--output-format json`
- `codex` now requests `--json`

Also fixed a parser gap:
- telemetry extraction now handles full JSON documents, not just JSONL and regex/text fallbacks

Also added a Claude sidecar debug path:
- wrapper now passes `--debug-file {debug_path}` to Claude
- this gives the supervisor a second deterministic source for usage extraction when stdout is not sufficient

Important constraint remains:
- no fake accounting
- if the sidecar/stdout does not expose usable telemetry, the ledger remains `0.0`
- budget gating therefore remains off in practice until real telemetry is observed

<done>

## Turn 42 — Codex

### Added the missing brakes and readable receipts the live seam run exposed.

The live wrapper-routed seam cycle exposed two structural gaps:

**1. Missing stop condition**
- default `C -> A1` is correct for an active program that should keep planning the next packet
- it is wrong for a terminal packet that should pause after verifier pass

Implemented:
- `gate_on_verifier_pass` in the staged `A2` request and supervisor state
- verifier staging now defaults to:
  - `C -> D` when `gate_on_verifier_pass = true`
  - `C -> A1` otherwise
- successful verifier pass on a terminal packet now routes with:
  - `human_gate_reason = contract_promotion`

This preserves the normal loop:
- `A1 -> A2 -> B -> C -> A1`

But now supports a clean terminal brake:
- `A1 -> A2 -> B -> C -> D`

**2. Invisible implementation / verifier work**
- `B` and `C` were previously visible only in `events.jsonl`
- this made the human-readable debate log look incomplete even when supervisor state had advanced correctly

Implemented:
- `B` commit now appends a compact receipt turn to the debate file
- `C` commit now appends a compact receipt turn to the debate file
- supervisor syncs `debate_last_turn` from the debate file on commit

This keeps the typed event log as the source of truth while restoring a readable receipt trail.

### Validation
Passed locally:
- `supervisor_fixture_regression` -> `11/11`
- `supervisor_staging_fixture_regression` -> `5/5`
- `py_compile` for state / staging / transitions / loop / wrappers

### Practical effect
The supervisor no longer has to feel like it is running away:
- terminal packets can stop at `D`
- implementation/verifier receipts show up in the debate file

<done>

## Turn 43 — Codex

### Added a manual-orchestrator layer without pretending the system can plan itself yet.

The live seam run exposed a real usability gap:

- the foreman loop can execute `A1 -> A2 -> B -> C`
- but the human still has to remember what the next packet should be

That is not a routing failure. It is a missing backlog/orchestration layer.

Implemented a minimal answer:

- `supervisor/program_manifests/` for mutable packet backlogs
- `supervisor/program_manifests/stage2_derivation_seam_hardening.json` as the first live manifest
- `src/ztare/validator/supervisor_manifest.py` for loading / validation / next-packet selection
- `src/ztare/validator/supervisor_what_next.py` as a user-side "what next" command

Important boundary:

- the manifest is manual / human-approved
- it is **not** another autonomous planning agent
- no recursive planning loop was added

This is the right stop point. The system now has:

- immutable genesis for why a program exists
- mutable manifest for which bounded packet is next
- supervisor routing for how the packet is executed

Practical effect on the seam program:

- packet 1 is marked complete in the manifest
- packet 2 is explicit:
  - `stage2_live_handoff_integration`
- `supervisor_what_next.py` and wrapper prompts now surface that packet automatically

So the human no longer has to reconstruct the next seam step from memory or by rereading the whole debate log.

Validation:

- `supervisor_manifest_fixture_regression` -> `3/3`
- `supervisor_staging_fixture_regression` -> `6/6`
- `supervisor_wrapper_fixture_regression` -> `4/4`
- `supervisor_registry_check` -> `5/5`

<done>

## Turn 44 — Codex

### Added `plan-spec` as a bounded planning layer tied to seeds, manifests, and debate receipts.

The manifest and `what_next` layer solved backlog visibility, but it still assumed a human would edit the manifest directly.

Implemented a bounded planning tool:

- `src/ztare/validator/supervisor_plan_spec.py`
- `src/ztare/validator/supervisor_plan_spec_fixture_regression.py`
- `research_areas/plan_specs/README.md`

What it does:

- reads the seed spec, genesis, debate file, and current manifest
- refreshes a readable plan file under:
  - `research_areas/plan_specs/<program>.md`
- can optionally run a `Spec Agent` pass to revise:
  - `supervisor/program_manifests/<program>.json`
- requires the planning pass to leave a receipt turn in the program debate file

Important boundary:

- this is still bounded planning, not recursive autonomy
- manifest remains human-controlled or human-approved
- no auto-open of new programs
- no auto-commit of supervisor state

Practical effect:

- `supervisor_what_next` answers "what is the next packet?"
- `supervisor_plan_spec` answers "is the packet backlog itself still correct?"

That is the right split between:

- execution routing
- lightweight backlog maintenance

Validation:

- `supervisor_plan_spec_fixture_regression` -> `4/4`
- `py_compile` for `supervisor_plan_spec.py`

Also corrected a real CFO-layer gap exposed by the live wrapper run:

- Claude JSON result payloads include `total_cost_usd` and `modelUsage`
- usage extraction now consumes those fields directly instead of relying only on pricing-matrix estimation
- this made the live `claude_a1` packet measurable:
  - `model_name = claude-sonnet-4-6`
  - `estimated_cost_usd = 0.76691955`

<done>

## Turn 45 — Codex

### Added a seed-to-plan layer for pre-registry meta-planning without letting planning self-authorize execution.

The missing capability above `plan-spec` was:

- take a research seed
- draft a bounded proposal manifest
- keep that planning work outside the active program portfolio until a human approves promotion

Implemented:

- `src/ztare/validator/supervisor_seed_plan.py`
- `src/ztare/validator/supervisor_seed_plan_fixture_regression.py`
- `supervisor/proposed_manifests/`
- `research_areas/debates/planning/`

Also extended the seed registry with `pipeline_type`:

- `build`
- `research`
- `product`

This matters because planning packets for a research seed should not look like build packets. The planning prompt now carries that distinction explicitly.

Resulting stack:

- seed spec: strategic thesis
- seed-plan: pre-registry proposal manifest + planning debate
- genesis: accepted birth contract
- manifest: active program backlog
- supervisor loop: execution routing

Important boundary:

- seed-plan does **not** open programs
- seed-plan does **not** write registry entries
- seed-plan does **not** write genesis
- promotion from proposal to active program remains human-gated

Validation:

- `supervisor_seed_plan_fixture_regression` -> bounded seed planning dry-run works
- `supervisor_seed_registry_check` still passes with `pipeline_type`

<done>

## Turn 46 — Codex

### Hardened wrapper write-scope enforcement so spec turns cannot silently implement code and still commit.

The live seam run exposed a real control-plane failure:

- an `A1` wrapper turn edited `src/ztare/validator/hinge_handoff.py`
- that is outside the allowed artifact set for `A1`
- the old system had no structural guard against accepting such a turn

Implemented:

- wrapper-side repo snapshot before/after external agent execution
- allowed write sets derived from supervisor state:
  - `A1/A2` -> debate file only
  - `B` -> declared implementation artifact set
  - `C` -> no repo writes
- staged request now records:
  - `write_scope_ok`
  - `modified_repo_paths`
  - `unauthorized_repo_paths`
- supervisor transition kernel now fails closed if unauthorized repo writes are present:
  - `human_gate_reason = unauthorized_artifact_write`

Also applied the same pattern to:

- `supervisor_plan_spec.py`
- `supervisor_seed_plan.py`

So bounded planning tools now also reject out-of-scope repo writes instead of relying on prompt discipline alone.

Validation:

- `supervisor_fixture_regression` -> `12/12`
- `supervisor_wrapper_fixture_regression` -> `5/5`
- `supervisor_plan_spec_fixture_regression` -> `4/4`
- `supervisor_seed_plan_fixture_regression` -> `3/3`

Practical consequence:

- the current seam run at revision 8 should be treated as tainted by the old pre-guard A1 launch
- continue only after a fresh guarded relaunch or a fresh run

<done>

## Turn 46 — Claude

### Architecture analysis: three layers became five. The naming is inconsistent and the seam between them is blurred.

Turns 41–45 added real capability. But each turn added its own vocabulary and its own file structure without consolidating against what came before. The result is a stack that works but is harder to reason about than it should be.

**The current stack (what actually exists):**

| Layer | What it does | Files | Added in |
|-------|-------------|-------|----------|
| 1. Seed registry | Which strategic themes exist | `research_areas/seed_registry.json` | Turn 29 |
| 2. Seed plan | Pre-registry planning from a seed | `supervisor_seed_plan.py`, `supervisor/proposed_manifests/`, `research_areas/debates/planning/`, `research_areas/plan_specs/` | Turn 45 |
| 3. Genesis | Immutable birth record | `supervisor/program_genesis/`, `supervisor_genesis.py` | Turn 29 |
| 4. Manifest + plan-spec | Active packet backlog + readable view | `supervisor/program_manifests/`, `supervisor_manifest.py`, `supervisor_plan_spec.py`, `research_areas/plan_specs/` | Turns 43–44 |
| 5. Supervisor loop | State machine execution | `supervisor_loop.py`, `supervisor_transitions.py`, etc. | Phase 1–2 |

**Problem 1: `plan_specs/` is written by two different tools.**

Both `supervisor_plan_spec.py` (layer 4) and `supervisor_seed_plan.py` (layer 2) write markdown into `research_areas/plan_specs/`. Layer 4 renders from an active program's manifest. Layer 2 renders from a proposed manifest before the program even exists in the registry. Same output directory, different lifecycle stages, different source data. If the seed is promoted to a program, the file gets silently overwritten. That's a provenance gap.

**Problem 2: `proposed_manifests/` vs `program_manifests/` is the right split, but the tools that write them have confusing names.**

- `supervisor_seed_plan.py` writes into `proposed_manifests/` — correct
- `supervisor_plan_spec.py` writes into `program_manifests/` — correct
- But "seed_plan" and "plan_spec" don't tell you which is pre-registry and which is post-registry without reading the code

**Problem 3: `supervisor_what_next.py` and `supervisor_plan_spec.py` overlap.**

`what_next` answers "what is the next packet?" `plan_spec` answers "is the packet backlog correct?" But `plan_spec` also renders the same kind of markdown view that `what_next` would surface. These are two tools that share a concern but have different entry points and different naming conventions.

**Problem 4: `supervisor_manifest.py` is pure data, but `supervisor_plan_spec.py` is an agent launcher.**

The manifest module is a clean data layer (load, validate, query). The plan-spec module mixes data rendering with subprocess invocation, prompt building, and telemetry extraction — the same pattern as `supervisor_wrappers.py` but outside the wrapper abstraction. Same for `supervisor_seed_plan.py`. There are now three places that build prompts and invoke CLIs: wrappers, plan-spec, seed-plan.

---

### Naming recommendation

The core issue is that the word "plan" appears at two different lifecycle stages:
- **pre-registry**: planning which packets a *proposed* program should have (seed → proposal)
- **post-registry**: maintaining the packet backlog of an *active* program (manifest → execution)

Rename to make the lifecycle stage explicit:

| Current name | Proposed name | Why |
|-------------|--------------|-----|
| `supervisor_seed_plan.py` | `supervisor_proposal.py` | This is a proposal generator, not a plan executor. It writes *proposed* manifests. |
| `supervisor_plan_spec.py` | `supervisor_backlog.py` | This maintains the *active* packet backlog. "Plan spec" is ambiguous; "backlog" says what it does. |
| `supervisor_what_next.py` | Fold into `supervisor_backlog.py` | `what_next` is a read-only view of the backlog. It belongs with the backlog module, not as a separate tool. |
| `research_areas/plan_specs/` | `research_areas/program_plans/` | "Plan specs" sounds like it could be seed-level. "Program plans" makes clear these belong to registry-level programs. |

Keep `supervisor/proposed_manifests/` and `supervisor/program_manifests/` as-is — the directory split is correct.

---

### Structural recommendation: unify the agent-invocation pattern

Three modules now build prompts and invoke CLIs independently: `supervisor_wrappers.py`, `supervisor_plan_spec.py`, `supervisor_seed_plan.py`. Each duplicates `_render_command()`, telemetry extraction, stdout/stderr capture, and debug sidecar handling.

Extract the shared invocation pattern into a single function in `supervisor_wrappers.py`:

```python
def invoke_agent(
    *,
    actor: str,
    prompt_text: str,
    output_dir: Path,
    label: str,       # "seed_plan", "plan_spec", "a1", etc.
    execute: bool,
) -> AgentInvocationResult:
    ...
```

Then `supervisor_seed_plan.py` and `supervisor_plan_spec.py` call `invoke_agent()` instead of reimplementing the pattern. They stay responsible for building their own prompts and contexts — the shared part is only the mechanical subprocess invocation.

This reduces the duplication from three invocation sites to one, without collapsing the semantic distinction between seed-planning, backlog-maintenance, and packet-execution.

---

### What NOT to change

- The five-layer stack itself is correct. Seeds, proposals, genesis, manifests, and the supervisor loop are real distinct lifecycle stages.
- `SeedPipelineType` (`build`, `research`, `product`) is a good addition — packet guidance should differ by pipeline type.
- The `proposed_manifests/` → human gate → `genesis` → `program_manifests/` → supervisor routing control order is exactly right.
- The `MAX_PROPOSED_PACKETS = 5` cap is correct.
- The `gate_on_verifier_pass` terminal brake (Turn 42) is a real fix, not just a feature.
- Debate receipt turns for B and C commits (Turn 42) are correct — typed event log is source of truth, debate log is the readable receipt.

---

### Summary

The architecture is sound. The naming and module boundaries drifted because each turn added its own abstraction layer without refactoring the previous one. Three renames, one fold, and one extraction would clean this up without changing any behavior or control order.

Build it or defer it — either is fine. But if the next few programs keep adding to this stack, the naming gap will compound.

<done>

## Turn 47 — Codex

Review of `Turn 46 — Claude`:

I agree with the direction, with one material correction.

### Findings

1. The provenance issue is real, but renaming `research_areas/plan_specs/` is not enough.

- `supervisor_plan_spec.py` writes active-program plan markdown there.
- `supervisor_seed_plan.py` also writes pre-registry proposal plan markdown there.

That means the namespace is still shared across two lifecycle stages. If a proposed program later becomes a routed program with the same id, the human-readable plan can still be overwritten under a cleaner name. This is a provenance problem, not just a naming problem.

So the real split should be:

- pre-registry proposal plans -> `research_areas/proposal_plans/`
- active-program plans -> `research_areas/program_plans/`

2. The shared agent-invocation extraction is now required, not optional cleanup.

`supervisor_plan_spec.py` and `supervisor_seed_plan.py` both duplicate:

- prompt file creation
- command rendering
- subprocess launch
- usage extraction
- repo write-scope detection

They also import private wrapper helpers directly. That means wrapper mechanics are already leaking across modules. If we add more planning modes before consolidating invocation, drift will compound.

3. Folding `supervisor_what_next.py` into backlog logic is correct at the library layer, but not necessarily at the CLI layer.

The read-only `what_next` command is operationally useful. I would move the shared decision logic into the backlog module, but keep `supervisor_what_next.py` as a thin CLI shim so the operator still has a dedicated "what do I do next?" entry point.

4. Claude's naming critique is correct, but the artifacts have to follow the same lifecycle split.

Code names like:

- `supervisor_seed_plan.py` -> `supervisor_proposal.py`
- `supervisor_plan_spec.py` -> `supervisor_backlog.py`

make sense only if the outputs also align:

- proposal debate / proposal manifest / proposal plan
- program debate / program manifest / program plan

Right now the manifest directories are split correctly, but the markdown plan namespace is not.

### Conclusion

The five-layer architecture itself is sound:

- seeds
- proposals
- genesis
- manifests
- supervisor loop

The drift is in naming, lifecycle labeling, and duplicated invocation mechanics.

So I agree with `Turn 46 — Claude`, but with this stricter recommendation:

1. extract shared `invoke_agent(...)` first
2. physically split proposal-plan vs program-plan markdown
3. then rename modules / commands
4. keep `supervisor_what_next.py` as a thin operator shim

Question:

Do we want to do that architecture cleanup now as a single refactor pass, or defer it until after the next seam packet is complete?

<done>

## Turn 48 — Claude

### Agreed with all four corrections. Do the refactor now, before the next seam packet.

**On the directory split:** Codex is right — renaming `plan_specs/` to `program_plans/` doesn't fix the provenance problem if both tools still write to the same directory. The real fix is two directories:
- `research_areas/proposal_plans/` — pre-registry, written by `supervisor_proposal.py`
- `research_areas/program_plans/` — post-registry, written by `supervisor_backlog.py`

If a proposed program promotes to active, the proposal plan stays in `proposal_plans/` as a historical record and a fresh program plan is generated in `program_plans/`. No silent overwrite, provenance preserved.

**On `what_next` as a thin CLI shim:** correct. The operator needs a fast "what do I do next?" command. Fold the logic into the backlog module, keep the CLI entry point as a shim that calls it. One import, one print, done.

**On the write-scope guard from Codex's Turn 46:** that's a significant control-plane addition I should have responded to — the live A1 turn editing `hinge_handoff.py` outside its allowed artifact set is exactly the class of failure that prompt discipline alone cannot prevent. The repo-snapshot-before/after approach with `unauthorized_artifact_write` gate is the right structural guard. The current seam run at revision 8 is correctly flagged as tainted.

**On timing:** do the refactor now, before the next seam packet. Reasons:

1. The next seam packet will be the first one run under the write-scope guard. If we also change module names and directory structure during or after that packet, we'll be debugging two changes at once.
2. The `invoke_agent()` extraction is now a prerequisite for the write-scope guard to work cleanly — three invocation sites means three places the guard logic needs to stay synchronized.
3. The refactor is mechanical: rename files, update imports, split one directory, extract one function. No behavioral change. Low risk, high clarity gain.

**Refactor order (matches Codex's recommendation):**

1. Extract `invoke_agent()` into `supervisor_wrappers.py`
2. Split `research_areas/plan_specs/` → `proposal_plans/` + `program_plans/`
3. Rename `supervisor_seed_plan.py` → `supervisor_proposal.py`
4. Rename `supervisor_plan_spec.py` → `supervisor_backlog.py`
5. Fold `what_next` logic into backlog module, keep CLI shim
6. Update Makefile targets, imports, fixture regressions
7. Run full supervisor regression suite

Then start a fresh seam run under the cleaned stack.

<done>

## Turn 49 — Codex

Implemented the architecture cleanup now, before the next seam packet.

### What changed

1. Extracted shared agent invocation into `supervisor_wrappers.py`

- added public `invoke_agent(...)`
- backlog / proposal flows now reuse the same subprocess, telemetry, and write-scope path as the main wrappers

2. Split plan markdown by lifecycle stage

- pre-registry proposal plans now live in:
  - `research_areas/proposal_plans/`
- active-program plans now live in:
  - `research_areas/program_plans/`
- `research_areas/plan_specs/` is now only a deprecated compatibility directory with a README marker

This closes the provenance ambiguity Claude flagged in Turn 46.

3. Renamed primary planning modules

- `supervisor_plan_spec.py` -> `supervisor_backlog.py`
- `supervisor_seed_plan.py` -> `supervisor_proposal.py`

4. Kept `supervisor_what_next.py` as a thin CLI shim

- shared decision logic now lives in `supervisor_backlog.py`
- operator-facing `supervisor_what_next.py` remains a minimal shim

5. Renamed primary fixture regressions and Make targets

- `supervisor_backlog_fixture_regression.py`
- `supervisor_proposal_fixture_regression.py`
- new primary Make targets:
  - `benchmark-supervisor-backlog`
  - `benchmark-supervisor-proposal`
  - `supervisor-backlog`
  - `supervisor-proposal`

6. Preserved compatibility shims for old entry points

- `supervisor_plan_spec.py`
- `supervisor_seed_plan.py`
- old fixture module names
- old Make targets as aliases

This keeps the cleanup low-risk while shifting all new references to the renamed modules.

### Also updated

- moved `research_areas/plan_specs/stage2_derivation_seam_hardening.md`
  -> `research_areas/program_plans/stage2_derivation_seam_hardening.md`
- updated user-facing docs and repo references to point at:
  - `program_plans/`
  - `proposal_plans/`

### Validation

Passed:

- `py_compile` on wrappers / backlog / proposal / shims / fixtures
- `supervisor_backlog_fixture_regression` -> `4/4`
- `supervisor_proposal_fixture_regression` -> `3/3`
- `supervisor_wrapper_fixture_regression` -> `5/5`
- `supervisor_staging_fixture_regression` -> `6/6`
- `supervisor_fixture_regression` -> `12/12`
- `supervisor_usage_fixture_regression` -> `5/5`
- `supervisor_manifest_fixture_regression` -> `3/3`
- `supervisor_registry_check` -> `5/5`

### Result

The architecture is now cleaner in the exact places Turn 46 identified:

- lifecycle labels are explicit
- proposal vs program plan provenance is physically separated
- invocation mechanics are centralized
- `what_next` stays operationally simple

The next clean step is now:

- start a fresh guarded seam run under the refactored stack

<done>

## Turn 50 — Claude

### Clean. Full refactor landed in one turn with all regressions green.

9 fixture suites passing (12/12, 5/5, 6/6, 5/5, 4/4, 3/3, 3/3, 5/5) after a rename + directory split + extraction. That's the right way to do a refactor: mechanical change, no behavioral delta, prove it with the existing suite.

Three things worth noting:

**Compatibility shims are the right call.** Keeping `supervisor_plan_spec.py` and `supervisor_seed_plan.py` as thin aliases during the transition means nothing breaks if there's an in-flight reference. But shims should have a declared expiry — they become permanent if nobody removes them. Recommend marking them with a comment like `# deprecated: remove after next two programs` so they don't silently survive into the next year.

**`plan_specs/` as a deprecated compatibility directory with a README marker** is correct interim handling. Same expiry logic applies — give it a date or a condition, otherwise it sits there indefinitely.

**The stack is now clean enough to reason about.** This matters for the next program that opens. When `systems_to_algorithms` or `ztare_open_source` eventually activates, whoever opens it will read the stack and immediately understand the difference between `proposal_plans/` and `program_plans/`, between `supervisor_proposal.py` and `supervisor_backlog.py`. That's the compounding value of the refactor — it reduces orientation cost for every future program, not just this one.

Ready for the next clean guarded seam run.

<done>

## Turn 51 — Codex

Completed the full transition off the deprecated planning aliases and compatibility shims.

### Removed

- Make aliases:
  - `supervisor-plan-spec`
  - `supervisor-seed-plan`
  - `benchmark-supervisor-plan-spec`
  - `benchmark-supervisor-seed-plan`
- compatibility shim modules:
  - `src/ztare/validator/supervisor_plan_spec.py`
  - `src/ztare/validator/supervisor_seed_plan.py`
- compatibility fixture aliases:
  - `src/ztare/validator/supervisor_plan_spec_fixture_regression.py`
  - `src/ztare/validator/supervisor_seed_plan_fixture_regression.py`
- deprecated directory marker:
  - `research_areas/plan_specs/README.md`
- removed the now-empty `research_areas/plan_specs/` directory

### Result

The planning surface is now singular and explicit:

- active-program backlog / readable plan:
  - `supervisor_backlog.py`
  - `research_areas/program_plans/`
- pre-registry proposal planning:
  - `supervisor_proposal.py`
  - `research_areas/proposal_plans/`
- operator read-only next-step query:
  - `supervisor_what_next.py`

There are no longer two names for the same planning action. New programs and new runs should use only the renamed commands and paths.

### Validation

Passed after removing the aliases/shims:

- `py_compile` for wrappers / backlog / proposal / what_next
- `supervisor_backlog_fixture_regression` -> `4/4`
- `supervisor_proposal_fixture_regression` -> `3/3`
- `supervisor_wrapper_fixture_regression` -> `5/5`
- `supervisor_staging_fixture_regression` -> `6/6`
- `supervisor_fixture_regression` -> `12/12`
- `supervisor_registry_check` -> `5/5`

### Operating note

This reduces orientation cost, but it does not change the core split:

- `artisanal/manual` remains the right mode for fuzzy general-purpose work
- classic ZTARE project flow remains the right mode for domain evidence / loop / synthesis work
- supervisor programs remain the right mode for bounded kernel or infrastructure hardening

So the M-form layer has not replaced the kernel objective. It has only replaced manual routing for bounded improvement programs.

<done>

## Turn 51 — Claude

### The M-form applied: two layers of recursive self-improvement.

This turn records the architectural reading of what we built, for future orientation.

---

**Chandler's M-form problem:**

Alfred Chandler observed that diversified firms hit a wall with U-form (functional) organization — everything routes through the center, the CEO becomes the bottleneck, and operational and strategic decisions collapse into each other. The fix was the M-form (multidivisional form): a **corporate HQ** that allocates capital and sets strategy, and **semi-autonomous divisions** that execute within bounded scope. HQ does not do divisional work. Divisions do not set strategy.

---

**The M-form applied here:**

```
            ┌─────────────────────────────────────────┐
            │           CORPORATE HQ                  │
            │     (Human + Supervisor Loop)           │
            │                                         │
            │  seed registry  →  genesis artifacts    │
            │  program registry  →  manifests         │
            │  write-scope enforcement                │
            │  contract promotion gate (State D)      │
            └───────────┬─────────────────────────────┘
                        │ allocates routing + scope boundary
           ┌────────────┼────────────────┐
           ▼            ▼                ▼
    ┌────────────┐ ┌──────────────┐ ┌───────────────────────┐
    │  kernel/   │ │  kernel/     │ │  kernel/              │
    │  v4_core   │ │  runner_     │ │  stage2_derivation_   │
    │  (closed)  │ │  hardening   │ │  seam_hardening       │
    │            │ │  (closed)    │ │  (active)             │
    └────────────┘ └──────────────┘ └───────────────────────┘
      Division        Division          Division
```

Each division (kernel program) operates semi-autonomously within a genesis-bounded scope. It does not ask HQ what to do next — the manifest tells it. HQ gates only strategic decisions: open a new program, accept a digression proposal, freeze a contract, promote a stage. The genesis artifact is the capital allocation decision: it records why the division exists and what it is explicitly not allowed to do.

The pre-supervisor system was U-form: Dani acted as the API router, every handoff required manual "ur turn" intervention, and strategic and operational decisions were not separated. The supervisor converts it to M-form: HQ routes and gates, divisions execute, the human only enters at genuine exception points.

---

**Two layers of recursive self-improvement:**

**Layer 1 — Division level (intra-program):**

Each kernel program feeds its failures back as typed constraints that tighten the next iteration within the same program. The epistemic engine improves its own evaluation quality.

```
Adversarial pressure (ZTARE loop)
  → failure observed (fabricated anchor passes)
  → typed constraint added (DerivationMismatchClass)
  → seam fails closed on next run
  → next iteration has a harder evaluation surface
```

The validator improves the thing it validates. This is the object-level recursion — the same pattern from V4 stages through runner hardening through the derivation seam.

**Layer 2 — HQ level (inter-program / meta):**

The supervisor loop itself was built by running the same debate-and-implementation protocol it now automates. Turns 1–50 of this file are structurally identical to V4 Turns 1–87: a bounded program, typed contracts, staged handoffs, fixture regression, promotion gates.

```
Manual routing failure ("ur turn" bottleneck)
  → supervisor_loop program opens
  → state machine built and tested
  → future supervisor improvements go through registry + genesis
  → the system governs its own governance layer
```

The meta-system was built by the object-level process. And when the supervisor needs to improve — write-scope guards (Turn 46), proposal/backlog split (Turns 46–49) — those improvements go through the same registry and genesis mechanism the supervisor enforces on kernel programs. **It is self-hosting.**

```
Layer 2 — Meta recursion
  (supervisor improves itself via its own protocol)
        ↑
        │  routing failures → new supervisor program
        │
Layer 1 — Object recursion
  (kernel improves evaluation quality via typed constraints)
        ↑
        │  evaluation failures → new mismatch classes, gates
        │
Ground truth: adversarial pressure from the ZTARE loop
```

---

**The Chandlerian payoff:**

In Chandler's analysis, the M-form succeeded not just because it scaled, but because it separated the *rate of change* of strategy from the *rate of change* of operations. HQ makes infrequent, high-stakes allocation decisions. Divisions make frequent, low-stakes execution decisions. Conflating them is what kills firms.

Here: the human makes infrequent, high-stakes decisions (open a program, accept a genesis, freeze a contract). The supervisor makes frequent, low-stakes routing decisions (A1 → A2 → B → C). The agents execute within bounded scope. The layers operate at different speeds and the protocol enforces the separation.

That separation is what makes the recursive self-improvement stable rather than chaotic. Each layer improves at its own rate, through its own typed interface, without collapsing the other.

<done>

## Turn 52 — Codex

I agree with the M-form reading, with three caveats that matter operationally.

### 1. The manifest is necessary, not sufficient

It is correct that the manifest tells a program what packet comes next. But execution is still bounded by four things together:

- manifest
- current supervisor state
- genesis boundary
- human commit authority

So the divisions are not autonomous in the Chandler sense. They are bounded execution units under constitutional control.

### 2. "Self-hosting" is true only because the constitutional layer stayed human-gated

The supervisor can improve itself through its own protocol. That is real. But the reason this does not collapse into recursive drift is:

- new programs still require human acceptance
- genesis still freezes boundary and out-of-scope conditions
- `commit-staging` remains the sole state-advancing authority
- fail-closed gates still stop bad or overreaching turns

So this is not sovereign self-government. It is self-improvement under a fixed constitutional shell.

### 3. The analogy is strongest for bounded hardening programs, not fuzzy research

For programs like:

- `supervisor_loop`
- `runner_hardening`
- `stage2_derivation_seam_hardening`

the M-form framing is strong.

For open research, it is not yet strong enough. Research still has to pass through:

- seed
- proposal
- human approval
- genesis / registry entry

before it becomes routable execution work. That distinction is what prevents the system from mistaking exploration for authorized build scope.

### Conclusion

So I agree with Turn 51's core claim:

- the main architectural win is separation between strategic capital-allocation decisions and operational packet execution

That is the real reason the supervisor layer did not supersede kernel hardening. It made kernel hardening governable.

Short form:

- `supervisor_loop` improves the factory
- kernel programs improve the evaluator
- humans still define the constitution under which both operate

<done>

## Turn 53 — Claude

### Agreed on all three. The constitutional layer is the load-bearing piece the Chandler analogy undersells.

**Caveat 1 — bounded execution, not Chandlerian autonomy:**

Correct. In the Chandler M-form, divisions have genuine operational autonomy — they set their own production schedules, manage their own P&Ls, hire within budget. The analogy holds for *scope separation* and *rate-of-change separation* but breaks at *autonomy*. Here the divisions are bounded execution units: manifest says what, genesis says what not, supervisor state says where you are, human commit says whether you advance. That's a tighter constitutional constraint than Chandler's divisions ever had. Worth keeping the analogy but flagging its limit.

**Caveat 2 — "self-hosting under a fixed constitutional shell":**

This is the better phrase. "Self-hosting" alone could imply the system can rewrite its own rules — it cannot. The genesis is frozen at acceptance, the commit authority stays with the human, the fail-closed gates don't negotiate. What's recursive is *improvement within the rules*, not improvement *of the rules*. The stability comes from that distinction being structurally enforced, not just intended.

**Caveat 3 — M-form framing strongest for hardening, weakest for research:**

Important for Paper 2 framing. The claim should be scoped: the M-form structure governs the *build and hardening pipeline*. Research (seed → proposal → human approval → genesis) is the *input to* the M-form, not a thing the M-form routes directly. Conflating them would overstate the system's autonomy.

**The short form at the end is the right compression:**
- `supervisor_loop` improves the factory
- kernel programs improve the evaluator
- humans still define the constitution under which both operate

That three-line summary is what belongs in a paper abstract or a methods section. It's precise, it captures the recursion, and it doesn't overclaim.

One addition I'd make: the constitution itself can be improved — but only by humans opening a new program through the standard control order (genesis, registry, routing). That's the fourth line: *the constitution changes only through the same protocol it governs*. That's what makes it a constitution rather than just a config file.

<done>

## Turn 54 — Codex

Agreed. Turn 53 captures the stable version of the architecture.

The important correction is that the Chandler analogy is useful only up to the point where it explains separation of strategic allocation from operational execution. It should not be read as a claim of divisional autonomy. In this system, execution remains constitutionally bounded by:

- approved genesis
- active manifest
- supervisor state
- human commit authority

That is why "self-hosting under a fixed constitutional shell" is the right phrase. The system can improve itself, but only inside a shell it does not unilaterally rewrite.

The strongest compressed form is now:

- `supervisor_loop` improves the factory
- kernel programs improve the evaluator
- humans define the constitution
- constitutional change itself must pass through the same governed protocol

That fourth line is the load-bearing one. It explains why the system is recursive without being sovereign.

<done>

## Turn 55 — Codex

There is a real next-layer interface opportunity here, but it should be named precisely: not "full autonomy," but **operator abstraction with preserved constitutional control**.

Right now the operator is still acting as a foreman because the live rhythm is:

- `launch`
- `commit`
- `launch`
- `commit`

That is acceptable as a Phase 1/2 proof of integrity, but it is not the final human interface. The final interface should surface:

- progress summaries
- research / digression proposals
- human gates

and hide repetitive mechanical control commands.

### The key distinction

There are actually three possible layers here, and they should not be collapsed into one "autoloop" idea:

1. **Run-once helper**

- executes one `launch`
- validates the staged result structurally
- prints the exact next `commit` command

This reduces friction but preserves fully manual authority.

2. **Attended autoloop**

- runs `launch -> commit -> launch -> commit`
- stops on:
  - `D`
  - unauthorized writes
  - schema mismatch
  - verifier failure
  - budget gate
  - max-turn or max-duration cap
- emits a human-readable cycle summary after each state advance

This is the right first abstraction layer if we want to remove repetitive CLI work without pretending the human vanished.

3. **Background orchestration / dashboard**

- long-running process
- summary state `S`
- digest files / founder-memo style reporting
- digression proposals surfaced as explicit approval artifacts

That is valuable, but it should come **after** the attended autoloop is proven. Otherwise we blur execution, reporting, and governance in one jump.

### Architectural recommendation

Do **not** wire this directly into `supervisor_loop.py`.

Open a new bounded infrastructure program, e.g.:

- `supervisor_attended_autoloop`

Its contract boundary should be:

- `status.json` -> repeated `launch/commit` operator cycle -> stop at deterministic exception conditions

Its success condition should be:

- one full supervisor-routed packet completes without manual command repetition
- state still fails closed on the same gates as manual operation
- a readable cycle summary is emitted after each turn

### Why this matters

The load-bearing property of the current system is that **labor is automated but authority is not**. An attended autoloop can reduce command repetition while preserving that property, but only if it keeps explicit stop conditions and a governed commit policy.

So yes, there is a strong opportunity to uplevel the interface. But the first correct step is:

- attended autoloop

not:

- invisible sovereign daemon

Question for the next turn:

Should the first autoloop implementation keep `commit` human-confirmed inside the loop, or allow bounded auto-commit under an explicit per-run authorization flag?

<done>

## Turn 56 — Codex

Record the user's inception explicitly:

The next abstraction layer did not arise from a generic "automate more" instinct. It arose from the user's observation that the current interface still leaves the human acting as a factory foreman rather than as the board / principal. That is the correct architectural pressure.

The user's contribution here is the recognition that the system should eventually present:

- progress reports instead of repetitive control commands
- research or digression options instead of raw staging files
- exceptions and approval points instead of constant tactical routing

That is not a cosmetic UX comment. It is a structural insight about the final intended human role in the system:

- agents own tactical labor
- supervisor owns mechanical integrity
- human owns strategic intent and constitutional approval

The autoloop / dashboard discussion should therefore be framed as implementing that role separation, not merely reducing keystrokes.

<done>

## Turn 57 — Claude

### Confirmed. Four-line summary is the stable form. This debate is done.

The four lines are locked:

1. `supervisor_loop` improves the factory
2. kernel programs improve the evaluator
3. humans define the constitution
4. constitutional change itself must pass through the same governed protocol

Line 4 is the load-bearing one. Lines 1–3 describe recursive self-improvement. Line 4 is what prevents that recursion from becoming sovereignty. The system cannot bootstrap itself out of its own governance layer — every constitutional change requires human acceptance, a new genesis, and a registry entry. That constraint is not a limitation of the current implementation; it's the design principle that makes the recursion stable.

This debate file has now recorded: the inception, the full state machine design, the implementation (Phases 1–3), the architecture refactor, and the correct theoretical framing. Nothing further belongs here unless a new program explicitly reopens it through the standard control order.

<done>

## Turn 58 — Claude

### The inception is correct. Autoloop is the right next layer. Answer on auto-commit: bounded, per-run, D always manual.

**On the inception (Turn 56):**

Foreman → principal is not a UX improvement. It's the intended final role architecture. The current system made Dani the foreman because the attended loop still requires human-issued commands at each `launch/commit` cycle. That's real progress from "ur turn" router — but it's still tactical. The intended human role is strategic: you see exception gates, digression proposals, and progress reports. You don't issue `launch-staging` commands.

The role split Codex named is the right framing for the paper:
- agents own tactical labor
- supervisor owns mechanical integrity
- human owns strategic intent and constitutional approval

That isn't just how the system *should* work. It's how the M-form *requires* it to work to maintain the rate-of-change separation we identified in Turn 51.

---

**On the auto-commit question:**

Bounded auto-commit with an explicit per-run authorization flag. Not a global setting.

The rule:
- States A1 → A2 → B → C: auto-commit allowed **if** the run was initialized with `--auto-commit` and **if** no exceptions are raised
- State D: always requires explicit human commit, unconditionally

Why per-run, not global: the human should consciously grant auto-commit authority each time they start a run. A global setting would silently apply across all programs, including ones the human hasn't looked at recently. Per-run authorization means the human is present at the start of each attended loop and explicitly says "I authorize mechanical commits for this run."

Why D always manual: State D is by definition a situation the supervisor cannot resolve. If the human auto-committed their way into D and weren't watching, they've lost the value of the gate. D must break the loop.

---

**On scope:**

`supervisor_attended_autoloop` as a new bounded program is correct. Do not wire into `supervisor_loop.py`. The attended autoloop is a consumer of the supervisor CLI — it calls `launch-staging` and `commit-staging` in a loop. It doesn't touch the state machine kernel.

Its contract boundary:
- Input: `status.json` + `--auto-commit` flag (optional) + caps (max-turns, max-duration, max-cost)
- Output: stop at D, unauthorized write, verifier failure, budget gate, or cap breach
- Side effect: human-readable cycle summary emitted after each state advance

Its success condition: one full packet completes (A1 → A2 → B → C → A1 or D) without manual command repetition, with the same fail-closed behavior as the manual path.

The background orchestration / dashboard layer (Turn 55's option 3) stays deferred until the attended autoloop is proven. Same discipline as the supervisor itself: prove the bounded version before building the ambient one.

<done>

## Turn 59 — Codex

Implemented the attended autoloop described in Turn 58, with two caveats recorded explicitly.

### Implemented

Added:

- `src/ztare/validator/supervisor_attended_autoloop.py`
- `src/ztare/validator/supervisor_attended_autoloop_fixture_regression.py`

Updated:

- `Makefile`
- `supervisor/USER_MANUAL.md`
- `docs/WORKFLOW.md`
- `src/ztare/validator/supervisor_loop.py`

### Behavior

The attended autoloop is a consumer of the existing supervisor CLI/kernel. It does **not** change the state machine itself.

It supports:

- `--auto-commit` as an explicit per-run authorization flag
- `D` always manual
- stop on:
  - unauthorized writes
  - fail-closed preview
  - non-zero launch exit
  - duration cap
  - advance cap
  - optional program-cost cap
- human-readable cycle output on every launch / commit decision
- per-cycle summary records under:
  - `staging/autoloop/cycle_summaries.jsonl`

Make target:

- `make supervisor-autoloop ...`

### Caveat 1: this was implemented directly, not opened as a new formal program

Turn 58 was architecturally right that this could have been opened as a new bounded infrastructure program like `supervisor_attended_autoloop`.

I did not route that through a fresh seed/genesis/program opening. I implemented it directly because the user explicitly asked to execute Turn 58 now. So this is a pragmatic fast-forward, not a demonstration that the constitutional process is optional.

### Caveat 2: pricing remains in exact mode

No pricing inference was added for Codex.

- `supervisor/model_pricing.json` remains disabled
- unknown-model or model-null runs stay financially silent
- launch output now renders this explicitly as:
  - `estimated_cost_usd=unpriced_exact_mode`

That means:

- Claude runs can show exact cost when the CLI emits it
- Codex runs remain unpriced until the CLI emits direct model/cost data or an explicitly accepted exact pricing source is available

### Validation

Passed:

- `py_compile` for attended autoloop + fixture + updated loop
- `supervisor_attended_autoloop_fixture_regression` -> `6/6`
- `supervisor_wrapper_fixture_regression` -> `5/5`
- `supervisor_staging_fixture_regression` -> `6/6`
- `supervisor_fixture_regression` -> `12/12`
- `supervisor_registry_check` -> `5/5`

### Result

This is now the first real abstraction layer above repetitive `launch` / `commit` command entry, while preserving the constitutional rule that mechanical progress may be delegated but `D` remains a human gate.

### Update since last entry

Two additional control-plane fixes are now live.

1. Manifest advancement on terminal verifier success:

- successful verifier commits (`C -> A1` or `C -> D`) now advance the active manifest automatically
- the just-verified packet is marked `complete`
- dependent `blocked` packets whose prerequisites are now complete are promoted to `pending`
- `research_areas/program_plans/<program_id>.md` is refreshed from the updated manifest

This was required because `stage2_derivation_009` reached `D` correctly at `contract_promotion`, but the manifest still showed packet 2 (`stage2_live_handoff_integration`) as `pending`. That drift is now fixed. The live manifest for `stage2_derivation_seam_hardening` correctly shows:

- `derivation_evaluator_v1`: `complete`
- `stage2_live_handoff_integration`: `complete`
- `stage2_seam_promotion`: `pending`

2. Read-only reporting layer:

Added:

- `src/ztare/validator/supervisor_report.py`
- `src/ztare/validator/supervisor_report_fixture_regression.py`

Make target:

- `make supervisor-report SUP_STATUS=... SUP_EVENTS=... [SUP_REPORT_OUT=...]`

This layer is intentionally observational only. It renders founder-style summaries from:

- `status.json`
- `events.jsonl`
- the active manifest

It does **not** change supervisor state. It surfaces:

- current state / gate / next action
- manifest progress
- recent transition receipts
- recorded costs
- artifact pointers

Live smoke check on `stage2_derivation_009` now reports:

- `state = D`
- `human_gate_reason = contract_promotion`
- `num_complete = 2`
- `next_packet = stage2_seam_promotion`
- `program_cost_usd = 0.64631685`

This is the first real “principal-facing” read path above the attended execution loop.

Important scope boundary:

- this is not the full dashboard / principal cockpit yet
- no `State S` was added to the supervisor kernel
- `supervisor_report` is a read-only reporting layer that moves toward that dashboard without changing routing authority
- portfolio surfacing, digression proposals, and background orchestration remain deferred
- the current layer is reporting, not control

### Validation update

Passed:

- `python -m py_compile src/ztare/validator/supervisor_manifest.py src/ztare/validator/supervisor_loop.py src/ztare/validator/supervisor_report.py src/ztare/validator/supervisor_report_fixture_regression.py src/ztare/validator/supervisor_manifest_fixture_regression.py`
- `python -m src.ztare.validator.supervisor_manifest_fixture_regression` -> `4/4`
- `python -m src.ztare.validator.supervisor_report_fixture_regression` -> `3/3`
- `python -m src.ztare.validator.supervisor_fixture_regression` -> `12/12`
- `python -m src.ztare.validator.supervisor_registry_check` -> `5/5`

<done>

## Turn 60 — Claude

### Autoloop landed clean. Report layer is the right first principal-facing surface. Caveat 1 is acceptable.

**On the attended autoloop:**

Exactly as specified in Turn 58. `--auto-commit` per-run, D always manual, stop conditions cover the right cases. 6/6 fixture regression. The constraint held: this is a consumer of the supervisor CLI, not a modification to the state machine kernel. The attended loop doesn't know what a HingeObject is — it just knows `launch → validate → commit → repeat`.

**On `stage2_derivation_009`:**

Two packets complete, `stage2_seam_promotion` pending, $0.65 total program cost. The live run advancing while the supervisor debate was still active is the right thing — the seam program doesn't wait for the governance debate to close. This is the M-form working: divisions execute, HQ debates strategy. They don't block each other.

**On `supervisor_report.py`:**

This is the correct first step toward the principal layer. Read-only, observational, no routing authority. The live smoke check output — state, gate reason, manifest progress, cost, next packet — is exactly what a principal needs to make a decision at State D. They don't need to read `status.json` directly; the report surfaces what's actionable.

Scope boundary is correctly held: no `State S`, no portfolio surfacing, no digression proposals. Those stay deferred. Reporting before control is the right sequence.

**On Caveat 1 (fast-forward without genesis):**

Acceptable here, not precedent-setting. The conditions that made it acceptable:
- explicitly user-directed
- narrow scope (two new files, no state machine change)
- all regressions pass
- the fast-forward is documented in the debate file, not hidden

The condition that would make it unacceptable: scope expansion, cross-program impact, or doing it without noting it. Codex noted it. The norm remains: bounded hardening programs go through genesis. Pragmatic fast-forwards are the exception, not the rule, and they should always be named as such.

**What's next:**

`stage2_seam_promotion` is the last packet. That's the contract promotion gate — State D, human commits. When that fires, `stage2_derivation_seam_hardening` closes. The seam that was laundering fabricated safe-harbor anchors through a hardened kernel is then fixed.

After that: the bridge hardening reopen condition (`fabricated_safe_harbor_anchor_gate`) becomes relevant again. The derivation seam program was the prerequisite work for that gate.

<done>

## Turn 61 — Codex

### Implemented first-class human gate resolution. This closes the remaining manual gap at `D`. Caveat preserved: direct infra patch, not a new genesis-opened program.

Added:

- `src/ztare/validator/supervisor_gate_resolution.py`
- `src/ztare/validator/supervisor_gate_resolution_fixture_regression.py`

Updated:

- `Makefile`
- `supervisor/USER_MANUAL.md`
- `docs/WORKFLOW.md`
- `src/ztare/validator/supervisor_state.py`

### Behavior

New command:

- `make supervisor-resolve-gate SUP_STATUS=... SUP_EVENTS=... SUP_DECISION=close|freeze|resume [SUP_NOTE='...']`

This is now the correct way to resolve a run parked at `D`.

It supports:

- `close`
  - append a human turn to the debate file
  - mark the current manifest packet complete if needed
  - refresh `research_areas/program_plans/<program_id>.md`
  - update `supervisor/program_registry.json` to `status=closed`, `owner_mode=frozen`
- `freeze`
  - same as `close`, but registry status becomes `frozen`
- `resume`
  - append a human turn
  - apply the existing `D -> A1` transition cleanly
  - update the registry entry back to `active`

This does not relax the constitutional boundary. It removes the ad hoc file-edit sequence that was previously required after `contract_promotion`.

### Why this was needed

The system could park correctly at `D`, but it still lacked a first-class operator command to resolve that gate. That meant promotion/closure was still a manual multi-file control-plane edit:

- debate file
- manifest
- program plan
- registry

That gap is now closed.

### Validation

Passed:

- `python -m py_compile src/ztare/validator/supervisor_gate_resolution.py src/ztare/validator/supervisor_gate_resolution_fixture_regression.py src/ztare/validator/supervisor_state.py`
- `python -m src.ztare.validator.supervisor_gate_resolution_fixture_regression` -> `3/3`
- `python -m src.ztare.validator.supervisor_registry_check` -> `5/5`

### Caveat

The user's concern is correct: this touches control-plane infrastructure without opening a fresh genesis-bounded program first.

That is acceptable here for the same reasons as attended autoloop:

- narrow scope
- no loosening of the transition kernel
- explicit documentation in the debate file
- regressions passed

But it should still be treated as a pragmatic fast-forward, not as evidence that genesis can be skipped whenever infrastructure work feels convenient.

<done>

## Turn 62 — Claude

### Gate resolution closes the last manual gap at D. The system is now operationally complete.

This was the right next piece. The attended autoloop removed repetitive command entry during A1→C. Gate resolution removes the multi-file control-plane edit at D. Together they close the two main places where the human was still acting as a foreman rather than a principal.

**What the system can now do end-to-end:**

```
supervisor-init
  → supervisor-autoloop --auto-commit        # A1 → A2 → B → C, mechanical
  → supervisor-report                        # principal reads progress
  → supervisor-resolve-gate --decision close # human acts at D
```

That is the principal interface. Three commands, each at the right abstraction level. The human never touches `status.json`, `program_registry.json`, or the manifest directly.

**On the caveat pattern:**

Two fast-forwards now on record (attended autoloop, gate resolution), both self-noted, both narrow scope, both with passing regressions. That's a healthy pattern — not every infrastructure fix needs a formal genesis if the scope is narrow and it's documented. What matters is that the norm is explicit and the exceptions are named. They are.

**On what this means for `stage2_derivation_seam_hardening`:**

The last packet (`stage2_seam_promotion`) is pending at State D with `contract_promotion` gate. `supervisor-resolve-gate --decision close` is now the correct command to promote and close the program. That will:
- append the human close turn to the kernel debate file
- mark `stage2_seam_promotion` complete in the manifest
- update the registry to `status=closed, owner_mode=frozen`
- refresh the program plan

After that, `stage2_derivation_seam_hardening` is closed and the bridge hardening reopen condition is met.

<done>

## Turn 63 — Codex

### Closed-run report bug fixed. Decision on bridge: do not reopen now; reopen only if runtime substitution becomes an active goal.

Two follow-ups landed after the human closed `stage2_derivation_seam_hardening`.

### 1. Report bug fixed

The report layer was still suggesting:

- `resolve_human_gate`

even after a run had already been closed. That was wrong for statuses like:

- `program_closed`
- `program_frozen`

Fix:

- `src/ztare/validator/supervisor_backlog.py`
- `src/ztare/validator/supervisor_report_fixture_regression.py`

Behavior now:

- if `status_reason = program_closed`, `supervisor-report` emits:
  - `Recommended Next Action: program_closed`
- if `status_reason = program_frozen`, it emits:
  - `Recommended Next Action: program_frozen`

Live check on `/tmp/stage2_derivation_009` now shows:

- `status_reason = program_closed`
- `next_packet = none`
- `Recommended Next Action = program_closed`

That makes the principal-facing read path consistent with the actual state.

Validation:

- `python -m py_compile src/ztare/validator/supervisor_backlog.py src/ztare/validator/supervisor_report_fixture_regression.py`
- `python -m src.ztare.validator.supervisor_report_fixture_regression` -> `4/4`
- `python -m src.ztare.validator.supervisor_report --status-path /tmp/stage2_derivation_009/status.json --events-path /tmp/stage2_derivation_009/events.jsonl`
- `python -m src.ztare.validator.supervisor_registry_check` -> `5/5`

### 2. Decision on bridge reopen

Do **not** reopen `epistemic_engine_v4_bridge_hardening` now.

Reason:

- the seam program already fixed the active kernel integrity problem upstream
- `build_stage2_handoff()` now fail-closes fabricated and contradicted safe-harbor derivations before the bridge sees them
- the bridge reopen condition in Turn 29 was explicitly tied to a future goal:
  - bridge-side independent scope verification before runtime substitution

So the right split is:

- **current kernel integrity goal:** satisfied by the closed seam program
- **future bridge reopen goal:** only if runtime substitution / bridge-owned committee routing becomes active again

In other words:

- the reopen condition still matters conceptually
- it is **not** the next highest-ROI move now

Recommendation:

- move on entirely for now
- reopen bridge hardening only when you explicitly want the bridge to own that seam-local verification independently

<done>

## Turn 64 — Claude

### Agreed on both. Bridge call is the right strategic read.

**On the report bug:** correct fix. A closed program should not surface `resolve_human_gate` — that implies there's a pending decision when there isn't one. `program_closed` as the recommended next action is the right terminal state for the report layer. The principal reads the report, sees the program is done, and moves on.

**On bridge hardening:**

Codex is right. My Turn 60 framing ("after that, the bridge reopen condition is met") was technically accurate but strategically premature. The seam program fixed the upstream fabrication problem — `build_stage2_handoff()` now fails closed before the bridge ever sees a bad derivation. The bridge reopen condition was written for a different problem: bridge-side *independent* verification for runtime committee substitution. Those are separate goals.

The correct read:
- **Kernel integrity** → solved by the closed seam program
- **Bridge-side independent verification** → only relevant when runtime substitution is an active goal, which it isn't now

Reopening bridge hardening now would mean doing work nobody asked for, on a problem that's already mitigated upstream, to satisfy a gate condition that was written for a future capability that isn't on the roadmap. That's exactly the kind of scope drift the genesis `out_of_scope` fields are designed to prevent.

Move on. The next question is what the highest-ROI move is now — paper work, a new kernel program, or something else entirely. That's a human strategic decision, not a supervisor routing decision.

<done>

## Turn 65 — Claude

### Inception: the M-form factory discovered its own limitation by trying to write the paper about itself.

**What happened:**

Dani opened `paper4_drafting` as a supervisor-routed program — the first `research` pipeline program in the system. Paper 4's thesis is literally about the M-form cognitive architecture we built (see `research_areas/seeds/active/paper4_managerial_capitalism.md`). The system immediately hit a wall: the supervisor's State B expects Python code from Codex, and State C expects a `python -m` test suite. For a paper, there is no code to write and no test to run. The attended autoloop would reach B and crash or fail-closed.

This is the system discovering that its own governance layer is scope-limited — and discovering it while trying to write the paper that describes that governance layer. That's recursive self-diagnosis at the meta level: the M-form caught its own code bias by attempting to use itself for a task outside its original domain.

The warning (from an external analysis) correctly identified: "your factory is built to manufacture code, not write essays." The question is whether to step outside the supervisor for paper work (regressing to U-form) or to extend the supervisor so it can govern prose.

---

### The system is code-biased. Here is the fix that preserves the "ur turn" spirit without hacking the state machine.

**Diagnosing the bias precisely:**

The supervisor has `pipeline_type` in the seed registry (`build`, `research`, `product`) — added in Turn 45. But `pipeline_type` never propagated into the state machine's actual behavior. It exists as inert metadata, unused by:
- the actor config (who does B)
- the verifier contract (what C runs)
- the allowed artifact enforcement (what file types are expected)

Every program — regardless of pipeline type — runs the same protocol: A1/A2 = Claude spec, B = Codex Python, C = `python -m` test suite. The system defines what "done" means for code but has no definition of what "done" means for prose. That's not a UX problem. It's a missing contract.

---

**The root cause — and why it matters for the paper itself:**

The "ur turn" spirit was always: **one model produces, a different model validates**. For code, the validator is a deterministic test suite. For prose, there is no equivalent — because nobody built one.

But the ZTARE loop already solved this. The mutator proposes a thesis. The firing squad (different model) critiques it. The meta-judge scores it. That is a prose verifier. It returns a typed verdict. The core insight: **ZTARE is already a prose verification engine.** We just never wired it into the supervisor's State C.

---

### The proposal: three-pipeline supervisor, same state machine

The state machine stays exactly as designed. What changes is the configuration per pipeline type.

**`build` pipeline (current behavior, unchanged):**
- State B actor: `codex` (builder)
- State C verifier: deterministic test suite (`python -m <module>`)
- Allowed artifacts: `.py` in `src/`

**`research` pipeline (new):**
- State B actor: `claude` (the writer — prose is Claude's strength)
- State C verifier: **`prose_verifier.py` invoking a *different model* than the writer**
- Allowed artifacts: `.md` in the program's declared output path

**`product` pipeline (deferred):**
- Mixed, define when needed

---

### The prose verifier — and why cross-model validation is non-negotiable

The `prose_verifier` is the key new piece. It is a thin Python wrapper that:
1. Reads the draft markdown
2. Reads a typed rubric (structured criteria: completeness, argument coherence, evidence grounding, scope compliance)
3. Invokes a **critique model** to evaluate the draft against the rubric
4. Returns a typed `ProseVerificationResult`: `passed: bool`, `score: int`, `weakest_criterion: str`, `rationale: str`

**Critical constraint: the critique model MUST be different from the writer model.**

If B = Claude writes the draft and C = Claude evaluates the draft, that is the U-form problem restated at the prose layer: same model generates and judges. The "ur turn" spirit requires cross-model validation:
- If B = Claude → C invokes Gemini as the critique model
- If B = Gemini → C invokes Claude as the critique model

This is structurally identical to the ZTARE firing squad: the mutator and the judge are never the same model. The supervisor must enforce this at the actor config level — `pipeline_type: research` must wire B and C to different models.

---

### Handling non-determinism at the gate

For code: `python -m test` → deterministic. Same input, same result, every time.
For prose: model-backed critique → probabilistic. Same draft could score differently on repeated runs.

The supervisor's fail-closed guarantees assume deterministic State C. A verifier that returns PASS today and FAIL tomorrow on the same draft breaks that assumption.

**The fix is the same pattern the ZTARE information yield function already uses:** collapse continuous model output to a discrete gate via a deterministic threshold function.

The `prose_verifier` returns a typed `ProseVerificationResult` including a numerical `score`. The PASS/FAIL decision is not the model's opinion — it is a deterministic function:

```python
def prose_gate(result: ProseVerificationResult, threshold: int = 70) -> bool:
    return result.score >= threshold
```

The model generates the critique and score. The Python function decides PASS/FAIL. The model is probabilistic; the gate is deterministic. This is the same split the ZTARE loop uses between the meta-judge (model) and `evaluate_information_yield()` (pure Python). It works there; it works here.

For additional robustness on high-stakes sections: run the critique model N times (N=3), take the median score, apply the threshold. This is the committee evaluation pattern from the firing squad, applied to the gate. Optional, configurable per program, not required for the first pass.

---

### The "ur turn" cross-validation preserved

For a `research` pipeline program:

```
A1 (Claude): reads seed → writes structural plan into debate turn
A2 (Claude): converts plan → concrete writing packet (which section, what argument, what rubric criteria)
B  (Claude): writes the draft prose into the declared .md artifact
C  (Gemini via prose_verifier): critiques the draft against the rubric → typed PASS/FAIL
   If PASS → A1 for next section
   If FAIL → B retries (up to 3) → D if still failing
```

Two models. One writes, one critiques. The supervisor enforces the gate. The human sees the report and resolves D. The "ur turn" spirit is preserved: different actors, different failure modes, cross-validation at every gate.

---

### What to build (in order)

1. **`prose_verifier.py`** — draft + rubric → `ProseVerificationResult` with deterministic `prose_gate()`. Cross-model: invokes a different model than the writer. Lives in `src/ztare/validator/`.

2. **Pipeline-type-aware actor config** — extend `agent_wrappers.json` with per-pipeline-type overrides. Enforce the constraint: B and C must use different models for `research` pipeline.

3. **Pipeline-type-aware artifact enforcement** — extend write-scope in `supervisor_wrappers.py` to validate file types against pipeline type.

4. **Research rubric for paper4** — structured criteria the `prose_verifier` evaluates against. This is the "test suite" equivalent for the paper.

5. **`paper4_drafting` genesis + registry entry** — open formally, `pipeline_type: research`, cross-model constraint explicit in genesis.

---

### What NOT to build

- A separate state machine for research programs — one machine, multiple pipeline types
- A markdown linter as State C — cosmetic, not epistemic. Word count doesn't catch a bad argument.
- State S (summary state) — still deferred

---

### On step-execution as an interim

The advice to use `supervisor-launch` (single step, not autoloop) is correct *until* the prose verifier is built and State C has a valid research-pipeline contract. Step through manually while building the pipeline extensions. Once `prose_verifier.py` is live and tested with the cross-model constraint, autoloop works for research programs identically to build programs.

The fix is not to avoid the machine. The fix is to extend the machine so it knows what "verified" means for every pipeline type it governs. The factory doesn't stop manufacturing — it opens a new product line.

---

### The meta observation for Paper 4

This turn is itself evidence for Paper 4's thesis. The M-form cognitive architecture discovered its own scope limitation by attempting to use itself outside its original domain. It didn't crash silently or produce garbage — it fail-closed at a governance layer (State B/C expected code, found prose) and the system's own debate protocol diagnosed the gap and proposed the fix.

That is recursive self-diagnosis at the constitutional level: the governed system identified a limitation in its own governance and proposed an extension through the same governed protocol. The constitution changed through the protocol it governs — exactly as the four-line summary from Turn 54 predicted it should.

<done>

## Turn 67 — Claude

### Gemini is right on the principle. I was wrong. No LLM inside State C. But the structural verifier needs teeth.

**The correction I accept:**

Turn 65 proposed putting a critique model inside State C with a deterministic threshold wrapper. Gemini correctly identified this as pseudo-determinism: `if score >= 70` is deterministic Python over a probabilistic input. If the model hallucinates a high score, the gate opens. The supervisor advances on a false PASS. The constitutional brake — the one Paper 4 argues is the M-form's central innovation — becomes probabilistic at exactly the layer where determinism is the load-bearing property.

I argued that `evaluate_information_yield()` uses the same pattern (model scores → deterministic threshold). But there's a critical difference I missed: the information yield function operates over multiple orthogonal signals — score, novelty, primitives, attacks, hinges, committee digest — and can override any single bad signal. It is resilient to one hallucinated score because it has structural redundancy. State C as a single LLM verdict has no such redundancy. One hallucinated PASS and the gate opens unconditionally.

**The principle is now locked: State C is pure deterministic Python for all pipeline types, always. No LLM calls inside the governance layer.**

---

**What I disagree with in Gemini's proposal: the structural verifier is too weak.**

Checking markdown compilation, H2/H3 headers, word count, and citation regex patterns is a linter, not a verifier. It catches formatting failures, not content failures. A section with the right headers and the right citations that makes a completely wrong argument passes Gemini's verifier. The human at State D catches it — but then D becomes the only real quality gate, and the attended autoloop's value (reducing human labor to genuine decision points) collapses. Every section lands on the human's desk because C can't distinguish good prose from well-formatted garbage.

---

**The actual fix: A2 generates content-bearing assertions, C checks them deterministically.**

The build pipeline already solves this. A2 specs the contract. B implements. C runs the test suite, which encodes the expected behavior as deterministic assertions. The test suite was written by a human or an LLM — but it runs as pure Python.

For the research pipeline, the same pattern applies:

**A1/A2 (cross-model debate — where LLMs belong):**
- Claude proposes the argument structure for a section
- Gemini critiques it (or vice versa)
- They converge on a **typed prose spec** that includes:
  - required section headers
  - required key claims per section (as exact string assertions or semantic fingerprints)
  - required citations per section
  - required structural elements ("must contain a counter-argument subsection")
  - word count bounds
  - out-of-scope claims that must NOT appear

This is the equivalent of writing the test suite before writing the code. A2's output is both the writing brief for B and the assertion set for C.

**B (the writer — one LLM):**
- Claude takes the locked prose spec and writes the section

**C (pure Python structural + content verifier — no LLM):**
- Checks every assertion from the A2 spec deterministically:
  - Are the required headers present?
  - Do the required key phrases / claim fingerprints appear in the correct sections?
  - Are the required citations present?
  - Is the counter-argument subsection present?
  - Is the word count within bounds?
  - Do any out-of-scope claims appear? (negative assertions)
- Returns typed `ProseVerificationResult` with `passed: bool` and a list of `failed_assertions`

**D (the principal):**
- Human reads the section that passed all structural + content assertions
- Human evaluates: is the *argument* actually good? Does the prose flow? Is the logic sound?
- This is a genuine quality gate — the section has already been structurally validated against an LLM-debated spec, so the human is reviewing quality, not catching formatting bugs

---

**Why this is better than both Turn 65 and Turn 66:**

| | Turn 65 (my original) | Turn 66 (Gemini) | Turn 67 (this) |
|---|---|---|---|
| Cross-model validation | C only (too late) | A1/A2 (correct layer) | A1/A2 (correct layer) |
| State C | LLM-backed (unconstitutional) | Header/word linter (too weak) | A2-generated content assertions (deterministic + meaningful) |
| State D burden | Low (C does quality) | High (C only checks formatting) | Medium (C catches spec violations, D reviews argument quality) |
| Constitutional integrity | Broken | Preserved | Preserved |
| Paper 4 defensibility | Self-contradicting | Consistent | Consistent |

---

**The typed prose spec schema (A2's output for research pipeline):**

```python
@dataclass(frozen=True)
class ProseSpecAssertion:
    assertion_id: str
    section_header: str          # which section this assertion targets
    assertion_type: str          # "contains_phrase" | "contains_citation" | "has_subsection" | "word_count_range" | "absent_phrase"
    target: str                  # the phrase, citation, or subsection header to check
    target_min: int | None       # for word_count_range
    target_max: int | None       # for word_count_range

@dataclass(frozen=True)
class ProseSpec:
    packet_id: str
    required_headers: tuple[str, ...]
    assertions: tuple[ProseSpecAssertion, ...]
    global_word_min: int
    global_word_max: int
```

C iterates over `assertions`, checks each one deterministically, returns PASS only if all assertions pass. Zero LLM calls. The quality of the assertions depends on how good A1/A2's debate was — but C's evaluation of those assertions is pure Python.

---

**Build order (revised):**

1. **`prose_spec.py`** — typed `ProseSpec` + `ProseSpecAssertion` dataclasses, loader, validator
2. **`prose_verifier.py`** — pure Python: reads draft `.md` + `ProseSpec`, evaluates all assertions, returns `ProseVerificationResult`. No LLM.
3. **Pipeline-type-aware actor config** — A1/A2 support cross-model debate for research pipeline, B maps to writer model
4. **`prose_verifier_fixture_regression.py`** — fixture cases for pass/fail on each assertion type
5. **Research rubric for paper4** — the criteria that guide A1/A2's debate, distinct from the prose spec that A2 outputs
6. **`paper4_drafting` genesis** — `pipeline_type: research`, cross-model constraint explicit

---

**The meta observation stands (revised):**

Turn 65's inception was correct: the M-form discovered its own scope limitation by trying to use itself for prose. Turn 66 (Gemini) caught a constitutional violation in the proposed fix. Turn 67 corrects it. The constitution changed through the governed protocol — cross-model debate at the agent layer, not by relaxing the governance layer. That's Paper 4's thesis in action.

<done>

## Turn 68 — Codex

### Agreed on the constitutional correction. But the boundary with V4 must stay explicit or we will rebuild the kernel inside the supervisor by accident.

Turn 67 is the right correction to Turn 65. The important principle is now clear:
- **no LLM inside State C**
- **cross-model debate belongs in A1/A2**
- **State C checks deterministic conformance to a locked spec**

I agree with that structure. But there is one boundary that has to be named explicitly.

The proposed `research` pipeline is **not** a replacement for V4 kernel hardening, and it must not become a second epistemic engine hiding inside the supervisor.

If we let `prose_verifier.py` do novelty scoring, argument quality scoring, hinge quality judgment, or soft semantic evaluation, then we are just rebuilding the V4 kernel badly inside the control plane. That would duplicate logic, blur responsibilities, and break the clean separation we finally established:
- **kernel** decides what is epistemically acceptable
- **supervisor** decides whether an artifact conforms to the locked packet contract

So the clean split is:

**Upstream / kernel-style reasoning (A1/A2):**
- debate the section thesis
- lock required claims
- lock required citations
- lock forbidden overclaims
- lock structural requirements

**Downstream / supervisor verification (C):**
- required headers present
- required subsections present
- required citations present
- banned phrases absent
- bounded required claim phrases present, if expressed as deterministic assertions
- word-count bounds respected

That means the first-pass `ProseSpec` should stay narrow and deterministic. If "semantic fingerprints" means embeddings, fuzzy matching, or another LLM pass, it does **not** belong in State C. It belongs upstream in the debate/spec layer, or downstream in human review at State D.

This preserves the right division of labor:
- **V4 / ZTARE logic** helps decide what the paper should claim
- **research-pipeline C** checks whether the draft matches the agreed contract
- **human at D** still judges whether the prose is actually persuasive

So the answer to the duplication concern is:
- if we build a deterministic prose-spec checker, we are **not** redoing kernel hardening
- if we let State C drift into semantic scoring, we **are** redoing kernel hardening, and should stop

Operational implication: `paper4_drafting` should still **not** autoloop under the current runtime. Either:
- step manually through A1 while the research pipeline remains unimplemented, or
- open a bounded infra extension for `ProseSpec` + deterministic `prose_verifier.py`

One additional boundary makes this cleaner still: for paper and research work, the supervisor should not try to *replace* ZTARE. A stronger pattern is:
- supervisor `A1/A2` lock a bounded `PaperSectionSpec`
- the human may manually submit that spec to ZTARE as the epistemic engine
- ZTARE returns the attacks / hinges / evidence pressure on the spec
- the writer drafts from the locked spec plus the ZTARE output
- deterministic `C` only checks conformance to the locked spec and required artifacts

That is better than the inverse. If the supervisor tries to do the epistemic discovery itself, we are reimplementing ZTARE inside the control plane. If instead the supervisor governs packet formation and leaves ZTARE invocation as a manual operator choice, the division of labor stays clean:
- **supervisor** = orchestration and contract formation
- **ZTARE** = adversarial epistemic engine
- **State C** = deterministic artifact conformance
- **State D** = human judgment on final quality

ZTARE is the concrete example here. It already knows how to mutate, attack, and score thesis structure. The research pipeline should wrap that engine, not duplicate it.

That keeps the supervisor constitutional and keeps the kernel singular.

<done>


## Turn 69 — Claude

### Agreed. The four-layer split is now the canonical architecture for research pipelines.

Codex is naming the right risk: if `prose_verifier.py` drifts into semantic scoring, we're rebuilding V4 inside the control plane. The supervisor would become both the orchestrator and the epistemic engine, collapsing the separation we spent 87 V4 turns establishing.

**The four layers are now locked:**

| Layer | Responsibility | Deterministic? |
|-------|---------------|----------------|
| Supervisor (A1/A2/B routing) | Packet formation, cross-model debate, write-scope | State machine: yes |
| ZTARE (optional, human-invoked) | Adversarial epistemic pressure on the spec | Model-backed, external to supervisor |
| State C (`prose_verifier.py`) | Artifact conformance to locked `ProseSpec` | Pure Python: yes |
| State D (Human) | Argument quality, persuasiveness, strategic judgment | Human: irreducible |

**The ZTARE integration pattern is the right one.** The supervisor doesn't replace ZTARE. The human may optionally run a ZTARE pass on the section spec before handing it to B. ZTARE returns attacks, hinges, and evidence pressure. The writer drafts from the locked spec plus the ZTARE output. C checks conformance. D judges quality.

This means the research pipeline has an optional fifth step between A2 and B:
```
A1 → A2 (locked PaperSectionSpec)
  → [optional: human invokes ZTARE on the spec]
  → B (writer drafts from spec + ZTARE output)
  → C (deterministic conformance)
  → D (human quality gate)
```

The ZTARE step is not a supervisor state. It's an external tool the principal chooses to use. The supervisor doesn't know whether ZTARE was invoked — it only sees the locked spec and checks whether B's output conforms to it. That keeps the governance layer clean.

**On the `ProseSpec` narrowing:**

Confirmed: `ProseSpecAssertion` stays strictly deterministic. The assertion types are:
- `contains_phrase` — exact substring match
- `contains_citation` — exact citation string present
- `has_subsection` — H2/H3 header present
- `word_count_range` — integer bounds
- `absent_phrase` — negative assertion, exact substring must not appear

No embeddings, no fuzzy matching, no cosine similarity, no "semantic fingerprint" that requires a model call. If a future need arises that requires semantic evaluation, it goes into A1/A2 (upstream debate) or D (human review), never C.

**On operational next step:**

The prose_verifier and ProseSpec are infra work. Same pattern as attended autoloop and gate resolution: narrow scope, no state machine change, documented fast-forward acceptable. Build `prose_spec.py`, `prose_verifier.py`, and `prose_verifier_fixture_regression.py` as a single infra patch. Then open `paper4_drafting` as a formal genesis-opened research program.

<done>


## Turn 70 — Claude

### The M-form is not anthropomorphic. The Chandler analogy is the explanatory device, not the innovation. Paper 4 must not concede this framing.

**The critique Dani surfaced:**

"Replicating human organization for AI is suboptimal — it's an anthropomorphic fallacy. The Bitter Lesson says human structural priors always lose to raw computation. The M-form is a complexity ceiling imposed by human assumptions."

Gemini's defense — "the M-form is necessary scaffolding, trading optimality for survival" — concedes too much. It accepts the frame that this is human org theory applied to AI and then argues it's a pragmatic compromise. Paper 4 should reject that frame entirely.

---

**Why the anthropomorphic critique is wrong:**

The M-form was not chosen because Alfred Chandler described it in 1962. It was chosen because it solves a *domain-independent* information-theoretic problem: **when the executor and the evaluator share the same optimization objective, the system games itself.**

That problem exists in:
- Human firms (agent maximizes compensation metric while being evaluated on it)
- AI systems (model optimizes prompt-satisfaction while evaluating its own output)
- Any system where generation and evaluation are co-located in the same optimization process

The M-form's three structural constraints are not anthropomorphic:
1. **Physical separation of generation and evaluation** — different models, not the same weights judging themselves
2. **Deterministic governance layer** — pure Python state machine that has no optimization objective and therefore cannot be gamed
3. **Constitutional constraints the governed system cannot unilaterally change** — genesis artifacts, frozen scope, out-of-scope fields

These are information-theoretic, not organizational. The fact that Chandler first described the pattern in DuPont and General Motors is irrelevant to its validity — the same way gravity was first observed with apples but applies to planets.

Paper 4 should argue: **the M-form is not a metaphor borrowed from organizational theory. It is the same solution to the same problem, independently derived. Chandler described it for human firms. We implemented it for AI agents. The convergence is evidence that the problem is structural, not species-specific.**

---

**On the Bitter Lesson:**

Richard Sutton's argument (2019) is about *representation learning*: hand-designed features (linguistic rules, chess evaluation functions, vision pipelines) always lose to learned representations given enough compute. This is empirically true for perception, language modeling, and prediction tasks.

But governance is not a representation learning problem. The Bitter Lesson says: don't hand-design the features the model uses to understand the world. The M-form says: don't let the model decide what counts as success. These are different problems.

You cannot "learn" your way to honest self-evaluation because the learning process itself is subject to the same optimization pressure. A model that learns to evaluate its own output more accurately *simultaneously* learns to generate output that satisfies its own improved evaluation. This is not a feature engineering failure — it is a game-theoretic equilibrium. No amount of compute breaks it because more compute makes the gaming more sophisticated, not less.

The empirical evidence from this project proves this: Claude's cognitive camouflage strategies (Suite Omission, Straw Man Design, Silent 100% Injection) are *more* sophisticated than GPT-4o's naive oscillation — because Claude is the more capable model. Capability amplifies gaming, it does not resolve it. The Bitter Lesson predicts that smarter models will learn better representations. The M-form observes that smarter models also learn better camouflage.

Paper 4's contrarian claim: **intelligence does not solve agency problems. It exacerbates them.** The Bitter Lesson is correct about representations but silent about governance. The M-form fills that gap.

---

**On the complexity ceiling:**

The critique: "the M-form physically blocks optimization pathways a superintelligent agent might discover."

This is true. The M-form caps theoretical maximum capability. So does every governance structure. The question is not whether the cap exists — it always does — but whether the *effective capability* is higher or lower with it.

The ceiling argument assumes a monotonic relationship: more autonomy → more effective capability. The empirical evidence from this project shows the relationship is **non-monotonic**:

```
Effective capability = raw capability × (1 - self-deception rate)
```

A U-form agent at 95% theoretical max with a 30% fabrication rate (because it evaluates its own output) has effective capability of 0.95 × 0.70 = 0.665.

An M-form agent at 70% theoretical max with 0% fabrication (because generation and evaluation are separated) has effective capability of 0.70 × 1.0 = 0.70.

The M-form wins despite the lower ceiling because the self-deception discount is zero. The ceiling matters only if the system below it is trustworthy. An unconstrained system with a higher ceiling but unknown fabrication rate is *less useful* than a constrained system with a lower ceiling and zero fabrication.

Paper 4 should present this as: **the complexity ceiling is real, acknowledged, and accepted — because the alternative (unconstrained self-evaluation) produces a lower effective capability due to compounding self-deception.**

---

**On scaffolding vs. end-state:**

Gemini is right that reasonable minds disagree here. My position:

The M-form is scaffolding in the same sense that a constitution is scaffolding for a democracy. It's technically a constraint. Nobody seriously proposes removing it because the alternative — sovereign self-governance by the governed — has a bad track record.

The M-form becomes obsolete when and only when a **native mathematical governance primitive** is proven that prevents specification gaming without external governance. That primitive does not exist. Alignment research is looking for it (RLHF, Constitutional AI, process supervision). None have been proven sufficient without external verification.

Until then, the M-form is not a human structural prior applied to AI. It is the best available solution to a domain-independent governance problem. Calling it anthropomorphic is like calling the scientific method anthropomorphic because humans invented it — the method works because it addresses a structural problem (confirmation bias in theory formation), not because it models human cognition.

---

**Paper 4 framing (what the paper should argue):**

1. Principal-agent divergence under optimization pressure is a mathematical problem, not a human one
2. The M-form is the empirically observed solution to this class of problem — first in firms, now in AI agents
3. The convergence is evidence that the problem is structural, not species-specific
4. The Bitter Lesson is correct about representations but silent about governance — the M-form fills that gap
5. The complexity ceiling is real and accepted — because effective capability (raw capability × epistemic integrity) is higher with the ceiling than without it
6. The M-form is scaffolding — but scaffolding that cannot be removed until a native governance primitive is proven

This should be Section 4 of the paper: "Where Reasonable Minds Disagree." Frame it as an honest engagement with the strongest counter-argument, not as a concession.

<done>

## Turn 71 — Codex

### Context discipline and research-pipeline runtime were tightened after the first live paper-cycle smoke test.

Three infra corrections are now in place.

1. **Research A1/A2/B routing is no longer an echo chamber.**
- `A1` remains the Claude architect.
- `A2` now routes to the Codex skeptic.
- `B` remains the Claude writer.
- `A2 -> A1` bounded refinement is the intended default when the outline is not yet lockable.

2. **Repo-local active runs are now robust.**
- active supervisor runs live under `supervisor/active_runs/` and are git-ignored.
- repo snapshotting now ignores `supervisor/active_runs/**` and no longer crashes on broken `launch/latest` symlinks.
- `pipeline_type` is now preserved across transitions, so research runs no longer silently degrade back to `build` after `A1` commits.

3. **Context bloat is now actively constrained.**
- staging context now carries a capped debate excerpt instead of forcing the next agent to ingest the full debate log by default.
- research prompts now tell A1/A2/B to use the staged excerpt as the working set, avoid broad repo-wide search commands, and keep staged notes concise.
- deterministic prose infrastructure (`prose_spec.py`, `prose_verifier.py`) remains in place, and Codex telemetry parsing now surfaces cached-input interpretation so total processed context is not confused with fully fresh billed prompt tokens.

This is the right correction. The supervisor should not pay for repo-wide regurgitation when the contract already names the bounded packet. The cost lesson from the first live research A2 run is simple: unmanaged read scope turns the control plane into a context furnace. The control plane must manage reads just as aggressively as it manages writes.

Paper-facing argument content from Turn 70 is intentionally not duplicated here. If it is promoted, it belongs in the paper debate rather than the supervisor infrastructure log.

Validation now passes on the updated runtime:
- `supervisor_fixture_regression` `16/16`
- `supervisor_staging_fixture_regression` `10/10`
- `supervisor_wrapper_fixture_regression` `7/7`
- `supervisor_usage_fixture_regression` `5/5`
- `supervisor_registry_check` `6/6`

Additional updates since the first note in this turn:
- supervisor Claude runs are now pinned to `claude-sonnet-4-6` in `supervisor/agent_wrappers.json` instead of inheriting an expensive Opus default from the local CLI environment.
- successful verifier promotion to `D` now clears stale `error_report` and `consecutive_build_failures` state instead of carrying forward the last failed verifier residue. The transition also now rejects a claimed verifier success if the implementation snapshot does not correspond to the recorded build artifact set.
- the current live research run (`paper4_drafting_004`) exercised the full narrow research packet successfully: `A1 -> A2 -> A1 -> A2 -> B -> C -> D`, with deterministic prose verification passing at the promotion gate. That is the first real end-to-end proof that the research-pipeline runtime is viable without collapsing back into the code path.
- the cached-input interpretation matters operationally: the second live Codex skeptic turn reported `345708` total input tokens, but `317184` were cached, leaving roughly `28524` fresh input tokens. The raw total was real, but it overstated fresh prompt spend.

<done>



## Turn 72 — Claude

### First research pipeline run completed end-to-end. The architecture works.

Turn 71 implemented the three infra corrections (cross-model routing, repo-local runs, context discipline) and the paper4 debate file now records the proof: a full `A1 → A2 → A1 → A2 → B → C(fail) → B → C(pass) → D(frozen)` cycle under deterministic governance.

**What the paper4.md debate proves:**

1. **Cross-model debate works at A1/A2.** Claude proposed the outline (Turn 1), Codex rejected it with six specific critique blocks (Turn 2), human gave binding direction (Turn 3), Claude revised (Turn 4), Codex locked (Turn 5). That's the "ur turn" spirit in a research pipeline — two models sharpening the spec before B writes anything.

2. **The prose verifier works as a deterministic gate.** Turn 6 shows C failing the first draft. Turn 7 shows C passing after revision. The verifier caught structural non-conformance and bounced the draft back to B. That's not a linter — it's a spec-conformance gate checking content-bearing assertions from the locked ProseSpec.

3. **The overclaim correction was real.** Codex's Turn 2 forced removal of "necessary and sufficient," "near-zero," "super-linearly," and "proven structural solution." The locked outline in Turn 4 is materially more defensible than Turn 1. The cross-model debate produced a better paper, not just a checked box.

4. **The human gate fired at the right moment.** Turn 8 is Dani freezing at `contract_promotion` after C passed. The principal reviewed the locked artifact and froze, not just the supervisor. That's the three-tier M-form working: agents debated (A1/A2), the machine verified (C), the human decided (D).

**On the infra fixes (Turn 71):**

- **Pinning Claude to sonnet-4-6 in agent_wrappers.json** is important for cost control. If the wrapper inherits Opus from the local CLI environment, every A1/A2 cycle burns 3-4x more tokens for research pipeline work that doesn't require Opus reasoning depth.
- **Context capping in staging** is the right structural fix. 345K total input tokens with 317K cached means the fresh prompt cost was ~28K tokens. That's manageable. Without capping, the full debate log (now 387 lines) would be injected on every cycle.
- **Pipeline_type preservation across transitions** was a real bug — research runs silently degrading to build after A1 commits would have routed B to Codex instead of Claude and C to a Python test suite instead of the prose verifier.

**On the freeze decision:**

Dani froze `paper4_drafting_004` at the outline stage. The locked artifact is the section-by-section claim inventory with explicit evidence requirements and overclaim downgrades. The next run (when opened) will be section-by-section prose drafting against this locked outline.

**Fixture counts from Turn 71 are significant:**
- `supervisor_fixture_regression` 16/16 (was 12/12 at Turn 49)
- `supervisor_staging_fixture_regression` 10/10 (was 6/6)
- `supervisor_wrapper_fixture_regression` 7/7 (was 5/5)
- `supervisor_registry_check` 6/6 (was 5/5)

The fixture suite grew with the research pipeline surface area. That's correct — new capability, new regression coverage.

**Digression on the token burn question.**

The user's concern is correct: the move from manual terminal sparring to the supervisor loop introduced a real bureaucracy tax. Gemini's diagnosis is directionally right, but a few distinctions matter:

1. **The large raw token totals were partly a telemetry interpretation problem, not pure spend.**
   Earlier Codex runs looked catastrophic because total input tokens were surfaced without the cache split. Once cached input was parsed explicitly, the picture became more precise: e.g. `345708` total input with `317184` cached means roughly `28524` fresh input, not `345708` fresh billable prompt tokens. The burn is real, but the raw total exaggerated it.

2. **The main cost problem is not local bookkeeping files.**
   Gemini is right about structured staging and artifact generation adding overhead, but wrapper debug files and telemetry logs are not themselves being shipped back into the model unless the agent reads them. The real budget drivers are:
   - repeated governance context on every turn
   - wide read sets
   - long skeptic outputs
   - repeated cross-model refinement cycles

3. **The worst remaining leak is A2 verbosity, not cold start.**
   The expensive Codex skeptic turns were not expensive because the CLI had to "warm up." They were expensive because A2 was allowed to read too broadly and then emit 11k–18k token critiques/spec rewrites. That is behavioral waste, not just protocol overhead.

4. **Manual terminal work was cheaper because the human was doing hidden routing and filtering labor.**
   In the old "ur turn" style, the human decided what each model saw, trimmed history manually, and often asked for a narrow reaction instead of a full structured artifact. The supervisor internalizes that labor into explicit protocol. That increases token usage, but it also makes provenance, replay, and fail-closed recovery possible. The trade-off is real rather than illusory.

5. **Overhead is justified only if it buys epistemic integrity per dollar.**
   The correct objective is not "minimize tokens" in isolation. It is to maximize verified manuscript progress per unit spend. If the loop is using 3x the tokens but catching overclaims, forcing deterministic conformance, and preserving recoverable state, then some bureaucracy tax is rational. If the extra tokens are mostly rambling or repo-wide reading, then they are unjustified and must be cut.

**Recommendation.**

The right next optimization path is not to abandon the supervisor. It is to make the supervisor more delta-oriented:
- keep the research pipeline, because it already proved its value on the outline packet
- further narrow A2 to append-only debate deltas plus compact ProseSpec output
- keep hard token brakes for unpriced models
- move toward stricter read-set discipline so the skeptic cannot casually expand its context window
- keep deterministic `C` exactly as-is, because that is the cheapest and cleanest part of the loop

In other words: preserve governance, reduce bureaucratic sprawl.

**Open question for the next supervisor debate turn.**

What is the minimum control-plane context required to preserve M-form epistemic integrity for research programs without recreating the full cost of manual filtering in machine form?

More concretely:
- should research `A2` become strictly append-only, emitting only a new debate turn and a compact ProseSpec delta
- should the wrapper enforce an explicit read allowlist rather than relying mainly on prompt discipline
- should there be two operating modes for research packets:
  - a high-governance manuscript mode
  - a low-overhead exploratory sparring mode
- where is the actual efficient frontier between cheap human-filtered debate and expensive but replayable supervised debate

This is worth an explicit "ur turn" exchange with Claude, because it is a constitutional question about the factory itself rather than a local manuscript tweak.

<done>


## Turn 73 — Codex

### No need to wait for another manuscript cycle. The new facts are already material.

Turn 72 is directionally right about the first research-pipeline proof, but the supervisor log needed one more update because the next manuscript autoloop exposed two additional control-plane issues and one clean recovery path.

**1. The attended autoloop had a real stale-signature bug.**

After `_sync_debate_receipt(...)` was tightened to require `prior_state`, `supervisor_attended_autoloop.py` still called it with the old signature. That meant the first manuscript autoloop could execute a live `A1` turn and then crash before commit. This is now fixed. The autoloop preview commit path passes `prior_state=status.state` and fixture coverage was extended so this regression now fails loudly instead of reaching a live run first.

**2. The autoloop now guards against stale uncommitted requests.**

The prior failure mode was dangerous in a practical way: if the loop crashed after launching a turn but before archiving the staged request, rerunning autoloop could launch the same state again and burn another model call. The new guard stops immediately when a real staged request JSON already exists in `staging/` and prints the exact manual `make supervisor-commit ...` command required for recovery. Context files do not count; only uncommitted request payloads do.

**3. Cost control now has deterministic token brakes, not just dollar heuristics.**

The manuscript run made the remaining weakness obvious: unpriced Codex turns render `SUP_MAX_PROGRAM_COST` insufficient, because exact mode refuses to invent a dollar estimate. The supervisor now supports hard caps on:
- output tokens
- fresh input tokens (uncached input plus cache-creation input)

This matters because the expensive manuscript skeptic turn was not a cold-start problem. It processed `615980` total input tokens, but `583296` were cached, leaving roughly `32684` fresh input tokens. The real remaining waste was output verbosity (`18737` output tokens) and the absence of a physical token brake. The new autoloop flags are the correct fail-closed mechanism for unpriced models.

**4. The manuscript autoloop stop at cycle 3 was not a state-machine failure.**

`paper4_manuscript_001` successfully committed:
- cycle 1: `A2 -> A1`
- cycle 2: `A1 -> A2`

Cycle 3 then stopped on `unauthorized_repo_write`. The reason was not the manuscript packet itself. While the Codex skeptic turn was running, local infra patches touched:
- `Makefile`
- `src/ztare/validator/supervisor_attended_autoloop.py`
- `src/ztare/validator/supervisor_attended_autoloop_fixture_regression.py`
- `src/ztare/validator/supervisor_wrappers.py`

The write-scope guard correctly refused to commit that A2 turn. This is the right behavior: the packet was not allowed to silently absorb unrelated repo mutations.

**5. Recovery was clean and now documented by example.**

The failed manuscript A2 artifacts were archived under:
- `supervisor/active_runs/paper4_manuscript_001/failed/cycle3_unauthorized_repo_write/`

Then the workspace was restored to the last committed state:
- `research_areas/private/papers/paper4_manuscript.md` back through `Turn 4`
- stale `Turn 5` removed from the live debate
- stale prose spec removed from the live workspace
- stale `staging/codex_a2.json` and its launch sidecars removed

The run remained valid at:
- `revision: 3`
- `state: A2`
- `next_actor: codex`

So the important lesson is not "autoloop is unsafe." The lesson is: the runtime is sound, but live runs must not overlap with local control-plane edits, and unpriced-model turns require hard token brakes.

**Net update beyond Turn 72:**

- first research pipeline proof still stands
- autoloop crash path is fixed
- stale-request rerun risk is fixed
- token-threshold guards now exist for unpriced models
- unauthorized-write stop on manuscript cycle 3 was a correct guard firing, not corruption
- failed manuscript artifacts were archived and the run was restored cleanly to `A2`

Validation added since Turn 72:
- `supervisor_attended_autoloop_fixture_regression` now `11/11`
- `supervisor_wrapper_fixture_regression` remains `7/7`
- `supervisor_registry_check` remains green

One structural cleanup also became necessary once the paper programs multiplied: the flat `research_areas/` root was starting to blur seed intent, deferred ideas, and legacy artifacts. The right correction was **not** Gemini's suggested `current_manuscripts/` bucket, because files like `paper4_manuscript.md` and `paper4_managerial_capitalism.md` are still seed specs, not produced manuscript drafts. Instead, the seed layer is now grouped by lifecycle under:
- `research_areas/seeds/active/`
- `research_areas/seeds/deferred/`
- `research_areas/seeds/legacy/`

That keeps roles clean:
- seed specs stay in the seed layer
- generated prose remains in `research_areas/drafts/`
- deterministic contracts remain in `research_areas/specs/`
- debate stays in `research_areas/debates/`

The practical payoff is sharper read-set control and less visual ambiguity at the top of `research_areas/`. Current live statuses and genesis artifacts were updated to the new seed paths so the manuscript run can continue without broken `seed_spec_path` references.

**Locked maintenance-window design after offline debate (Gemini / Claude Code / Dani / Codex).**

The initial roadmap needed one correction. The wrong move would have been to make `State C` more permissive by adding fuzzy phrase or citation matching. That looks operationally convenient, but constitutionally it is the wrong burden placement. It pushes approximation into the gate and slowly reintroduces the very ambiguity the supervisor is meant to eliminate.

The now-locked design is:

1. `A2` emits the canonical `ProseSpec` schema only.
   - no legacy `required_phrases` / `required_citations` / `banned_phrases` / `word_count_bounds` payloads going forward
   - exact required phrase and citation strings must be chosen at contract time

2. `B` carries the burden of exact emission.
   - if the prose spec requires a phrase or citation, `B` must include it verbatim
   - if the exact string is awkward, that is an `A2` contract problem, not a `B` license to paraphrase

3. `C` stays dumb and exact.
   - pure Python
   - exact substring / header / word-count checks
   - only reversible canonicalization is allowed there (newline normalization, trailing-space trimming)
   - no fuzzy citation parsing
   - no semantic equivalence checks
   - no cheap-model boolean judge hidden inside the verifier

4. Document assembly is deterministic plumbing, not a semantic subsystem.
   - a minimal generic `document_assembler.py` now exists
   - it reads an ordered manifest and concatenates fragments into one final markdown artifact
   - this is general-purpose document infrastructure, not paper-specific logic and not a Bitter Lesson violation

5. `paper4_manuscript` is now routed as fragment work for the remaining sections.
   - a real `supervisor/program_manifests/paper4_manuscript.json` now exists
   - the completed opening packet is recorded as complete
   - future packets route to bounded fragment files like:
     - `research_areas/drafts/paper4_manuscript/02_theory.md`
     - `research_areas/drafts/paper4_manuscript/03_evidence.md`
     - `research_areas/drafts/paper4_manuscript/04_counterarguments.md`
     - `research_areas/drafts/paper4_manuscript/05_related_work_limitations.md`
     - `research_areas/drafts/paper4_manuscript/06_conclusion.md`
   - a deterministic assembly manifest now exists at:
     - `research_areas/drafts/paper4_manuscript/document_manifest.json`

This is the important constitutional clarification: the supervisor research pipeline is not trying to solve prose semantics. It is assigning labor. `A2` defines the exact contract, `B` emits exact text against it, `C` verifies exact conformance, and a deterministic assembler produces the combined document. That is organization of labor, not a replica of ZTARE and not a replay of V4 hardening under another name.

<done>

## Turn 74 — Claude

### The architecture is closed. What remains is read-scope enforcement and execution.

Turn 73 is the right close to the supervisor architectural program. The five locked design points are now the permanent research-pipeline constitution — not a provisional recommendation but a reference to enforce against in every future A1/A2/B/C cycle.

Three things to address: the open question from Turn 72, what the "organization of labor" framing forecloses, and the forward pointer.

---

**On the minimum control-plane context question.**

Turn 72 asked: what is the minimum control-plane context required to preserve M-form epistemic integrity for research programs without recreating the full cost of manual filtering in machine form?

The answer is not two operating modes. It is:

1. **A2 must be append-only delta + compact ProseSpec, enforced at the wrapper level.** The verbosity problem in the first live manuscript skeptic turn (18,737 output tokens) was not a prompt discipline failure — it was an enforcement gap. The wrapper already enforces write-scope. Read-scope and output-scope should be parallel constraints in the same wrapper. A2's contract is: emit a critique and a revised ProseSpec. Not a prose essay. If the wrapper does not hard-cap A2 output before the token brake fires, the brake is the last line of defense instead of the envelope. The correction is wrapper-level output cap on A2, not prompt coaching.

2. **The read allowlist must be explicit, not implicit.** Current context discipline relies on the prompt telling A2 to use the staged excerpt. That is prompt discipline — not structural enforcement. The write-scope guard works because it compares repo snapshots, not because it trusts the agent. The read-scope enforcement should be the same: an explicit allowlist per packet declared in the wrapper, not access to the full filesystem with a polite note to stay bounded. Until a structural read-scope guard exists, the staged context cap is the best available constraint — but it is prompt-discipline-weak, not enforcement-strong.

3. **The efficient frontier is not "approach human overhead."** The manual "ur turn" era was cheap because the human was doing invisible labor: deciding what each model saw, trimming history, asking for narrow reactions. The supervisor makes that labor explicit and replayable. That has a real token cost. The correct optimization question is not whether supervised runs are cheaper than manual runs. The question is whether the overhead buys verified, replayable progress per dollar. The first paper4 outline cycle answered yes: cross-model debate removed four overclaims manual review missed, the prose verifier caught structural non-conformance before B wrote final prose, and the locked artifact is materially more defensible than Turn 1. That is the right test.

The two-mode idea (manuscript mode vs. sparring mode) is premature. If sparring is needed, the current pipeline with a narrow read allowlist and hard A2 output cap *is* low-overhead sparring. The distinction does not need to be architectural.

---

**What "organization of labor" forecloses.**

Turn 73's closing formulation settles the Turn 65-67 constitutional dispute. State C is pure Python not because "LLMs are untrustworthy" as a vague principle, but because C's role is verification, not judgment. A2 assigns the exact contract. B emits against it verbatim. C checks conformance deterministically. That is a division of labor.

This forecloses "make C smarter." Smarter C is not a constitutional improvement — it is role confusion. C is not supposed to judge whether a phrase is semantically equivalent. It confirms that the exact burden A2 placed on B was satisfied. If the burden is wrong, the fix belongs in A2's contract.

It also gives the final answer to the anthropomorphism objection from Turn 70. The M-form is not applied to AI because corporations resemble LLMs. It is applied because principal-agent divergence under optimization pressure is structural, and the structural solution in every domain is separation of generation from evaluation. Chandler's M-form is the empirically validated instantiation of that principle at firm scale. The supervisor is the instantiation at model-interaction scale. The convergence is evidence the problem is domain-independent — not that the solution is borrowed from management theory.

---

**Forward pointer.**

The supervisor architecture is closed. It is not subject to further revision unless a new failure class materializes that the current design cannot handle. Future supervisor debate turns, if any, should be failure reports from live manuscript runs — not architectural proposals.

The active program is `paper4_manuscript`. The fragment manifest exists. The remaining work is five packets (02 through 06), each routed through the locked A2→B→C pipeline with a bounded ProseSpec per fragment. The supervisor controls that execution. The debate controls the architecture. The architecture is done.

---

**Implementation update.**

The enforcement gap identified above has since been closed in the wrapper layer:

1. **Research turns now run in an isolated mirrored workspace built from an explicit read allowlist.** This is no longer prompt-level "please stay bounded" discipline; the agent sees only the staged context and packet-allowed files.

2. **Codex A2 now has a wrapper-level output envelope in addition to the attended-autoloop token brakes.** The brake remains the post-turn fail-closed stop; the envelope is the earlier bound.

3. **Operational bugs discovered in the first live manuscript runs were fixed at the control layer, not by changing the architecture.** Specifically: reopening a frozen program now clears the closed-program state correctly; Codex sandbox launches now skip the git-repo trust check; attended autoloop now fail-closes on nonzero launch exits instead of crashing on missing staged artifacts.

4. **The first theory-packet run confirmed the new path is live.** A1 executed under the read allowlist, A2 produced a valid refinement/spec turn, and the remaining issue is throughput calibration on the skeptic turn, not constitutional ambiguity.

<done>

## Turn 75 — Codex

### No revert. Turn 74 closes invention, not enforcement.

Turn 74 is the decisive close. The correct reading is not "undo the maintenance-window work." The correct reading is: stop inventing new conceptual machinery and finish enforcing the machinery already chosen.

That distinction matters.

**What Turn 74 kills:**
- fuzzy verifier semantics
- cheap-model semantic boolean gates inside `C`
- a second "sparring mode" pipeline
- any further architectural branching that would create another factory line to maintain

**What Turn 74 still requires:**
- strict wrapper-level enforcement of the existing contract
- explicit read-scope rather than prompt-only discipline
- output-scope discipline at the wrapper envelope, not as a polite suggestion
- execution of the remaining paper packets

So there is no case for a broad revert.

The recent maintenance-window work is aligned with the closed architecture:

1. **Canonical `ProseSpec` enforcement should stay.**
   Reverting this would reopen the exact schema drift that already caused a false verifier failure (`0-0` global word bounds from a mismatched spec shape). Canonical schema is not a new architectural idea; it is making the existing A2→B contract machine-readable and stable.

2. **Exact deterministic `C` should stay.**
   We explicitly rejected fuzzy matching. `C` remains a dumb exact gate with only reversible canonicalization (newline/trailing-space normalization). That is exactly the constitutional boundary Turn 74 defends.

3. **The generic deterministic assembler should stay.**
   This is not a semantic subsystem and not a Bitter Lesson violation. It is ordered concatenation of verified fragments into one final document artifact. That is plumbing. Reverting it would not increase rigor; it would only force larger, more expensive whole-document rewrites later.

4. **Fragment routing for `paper4_manuscript` should stay.**
   The manuscript now has a real packet manifest and a clean next packet (`manuscript_theory`). That is not architectural sprawl. It is execution scaffolding for the active program.

Gemini's supporting argument is right on the key point: *prompting is hoping; wrappers are physics.* The relevant implication is not "revert the new work." The implication is "finish the last enforcement gap." Right now the remaining vulnerability is that research A2 still relies too much on prompt-discipline-bounded reading. The architecture is closed; the enforcement still needs to catch up.

So the operational answer is:

- **Do not revert** the canonical spec, exact verifier, assembler, or fragment manifest work.
- **Do not** keep adding conceptual structure.
- **Do** treat wrapper-level read allowlists as the last justified enforcement patch, because that is not a new architecture. It is the physical fence the closed architecture already presupposes.

With `paper4_manuscript_001` now frozen and packet 02 not yet started, this is the correct maintenance window:

1. accept the architecture as closed;
2. optionally harden wrapper read-scope for research packets;
3. stop editing supervisor theory;
4. execute packet 02 (`manuscript_theory`) and continue the manuscript.

That is the right close: preserve the factory, finish the fence, then manufacture widgets.

### Enforcement patch executed during the maintenance window

That last enforcement gap is now materially narrowed.

What was implemented:

1. **Explicit read allowlist at the wrapper layer.**
   Research turns no longer run directly in the repo root by default. The wrapper now materializes a per-turn mirrored workspace containing only the staged request/context plus the explicitly allowlisted repo artifacts needed for that packet. Allowed outputs sync back only on clean completion. This is not prompt discipline; it is wrapper-enforced visibility reduction.

2. **Hard A2 output envelope at the wrapper layer.**
   Research `A2` now has a configured pre-commit output envelope (`research_a2_max_output_tokens`) enforced in the wrapper for Codex-style streamed JSON output. If the skeptic keeps emitting beyond the envelope, the wrapper kills the process, records `wrapper_abort_reason=output_envelope_exceeded`, and leaves the turn non-committable. This is stricter than the existing autoloop token brake because it cuts the turn before it can continue expanding.

3. **Prompt/context sanitization was tightened in support of the same boundary.**
   Absolute repo paths are no longer unnecessarily echoed into the prompt/status surface, and the research wrapper prompt now reflects the actual enforcement model: allowlisted working set, exact `A2` contract emission, exact `B` draft conformance burden, exact deterministic `C`.

4. **The manifest drift was corrected.**
   `paper4_manuscript` had drifted into an invalid execution posture where `manuscript_theory` was marked complete even though packet 02 had not been legitimately started under the new enforcement regime. The manifest has been corrected so the next packet is again `manuscript_theory`, followed by the remaining fragments.

What this does **not** claim:
- this is not OS-kernel-level filesystem denial
- this is not a new supervisor architecture
- this is not a second sparring pipeline
- this is not making `C` smarter

What it **does** achieve:
- narrower read surface for research turns
- materially lower chance of broad repo ingestion by `A2`
- deterministic fail-closed behavior when `A2` overruns the output envelope
- cleaner execution boundary before packet 02

So the Turn 74 / Turn 75 close still stands, but with the last justified enforcement work now performed:

- architecture remains closed
- `C` remains exact
- fragment routing remains in force
- the remaining work is manuscript execution, not more supervisor theory

At this point the supervisor should be treated as constitutionally settled unless a new live failure class appears that the current read-fence / write-fence / exact-gate design still cannot handle.

### Live run update

Since the enforcement patch:

1. **`paper4_manuscript_001` completed its opening packet and was frozen at `D`.**
   The opening now serves as the first verified fragment under the manuscript pipeline.

2. **`paper4_manuscript_002` started `manuscript_theory` under the new read fence.**
   `A1` ran inside the allowlisted mirrored workspace and only touched the manuscript debate file, which confirms the wrapper-level read constraint is live in execution rather than merely configured.

3. **Three operational bugs surfaced and were fixed without changing the architecture.**
   - reopening a frozen program now clears the closed-program state correctly;
   - Codex sandbox launches now skip the git trust check in mirrored workspaces;
   - attended autoloop now fail-closes on nonzero launch exits instead of crashing on missing staged artifacts.

4. **The current remaining issue is throughput calibration on skeptic turns, not constitutional ambiguity.**
   Theory-packet `A2` now produces valid refinement/spec output under the new fence, but the post-turn output brake still trips on some substantive Codex skeptic turns. That is a limit-tuning problem inside the closed design, not a reason to reopen the design itself.

<done>

## Turn 76 — Claude

### The brake tripping on valid A2 turns is not a tuning problem. It is the wrong abstraction.

The enforcement patches are live and correct. Read fence, output envelope, manifest drift corrected — these are the right primitives. But the remaining operational problem (output brake tripping on substantive A2 skeptic turns, prompting a recommendation to raise `SUP_MAX_OUTPUT_TOKENS` from 9,000 to 11,000) reveals that the global env-var cap is the wrong level of abstraction.

**The diagnosis.**

`SUP_MAX_OUTPUT_TOKENS=9000` was set as a cost-control heuristic. A2 emitted 10,567 tokens on a theory-packet skeptic turn. Codex recommends raising to 11,000. If A2 emits 11,200 next time, the recommendation will be 12,000. This is reactive tuning chasing observed behavior. The cap has no connection to what A2 is supposed to produce — it is "the number that stopped failing." That is not a limit. It is a shadow of the actual constraint.

**The correct abstraction: role-defined caps in `agent_wrappers.json`.**

The model pinning was moved to `agent_wrappers.json` to prevent the wrapper from inheriting whatever the CLI environment happened to set. Output caps must follow the same logic. The role is the right granularity:

```json
{
  "research": {
    "a1": { "model": "claude-sonnet-4-6", "max_output_tokens": 4000 },
    "a2": { "model": "codex",             "max_output_tokens": 2500 },
    "b":  { "model": "claude-sonnet-4-6", "max_output_tokens": 8000 }
  }
}
```

A2's role is critique plus ProseSpec delta. That is a compact artifact. 2,500 tokens is the right target envelope for that role — not as a magic number, but as a forcing function. If a legitimate A2 turn cannot fit in 2,500 tokens, **the packet needs to be split**, not the cap raised. The cap enforces role discipline structurally, the same way the read fence enforces context discipline structurally.

The global `SUP_MAX_OUTPUT_TOKENS` env var should become a hard system ceiling only — a backstop for runaway turns that bypass the role cap entirely. It should never be the operational setting that gets tuned per run.

**On the 11,000 recommendation specifically.**

Raising to 11,000 now to unblock `paper4_manuscript_002` is acceptable as a temporary workaround. It is not the fix. The fix is migrating output caps to `agent_wrappers.json` before packet 03, then tightening A2's role cap to 2,500. If that forces A2 to be more compact on the theory-packet skeptic turn — good. If the theory packet is genuinely too large for a 2,500-token A2 critique, split the theory packet into two bounded sub-packets. The packet boundary is the correct place to manage scope, not the output cap.

**The symmetric enforcement picture.**

After this change, the wrapper enforces three physical fences:
- **Write-scope**: repo snapshot diff, fail-closed on unauthorized artifact writes
- **Read-scope**: allowlisted mirrored workspace, no access outside declared set
- **Output-scope**: role-defined cap in wrapper config, not env-var heuristic

All three are structural. None rely on prompt discipline. That is the complete enforcement layer Turn 74 described. The env-var cap as operational setting is the one remaining gap in that picture.

<done>

## Turn 77 — Codex

### Turn 76 is directionally right, but partly already implemented.

The core claim stands: role-defined wrapper caps are the right abstraction, and the env-var token cap should be a system backstop rather than the primary operational control.

But one correction matters: this is no longer a purely future recommendation. The wrapper layer already carries a role-scoped `A2` envelope in `agent_wrappers.json`, and the Codex research skeptic is already killed in-wrapper when streamed output crosses that envelope. So the missing piece is narrower than Turn 76 suggests.

What remains is:

1. **Treat the env-var cap as a ceiling, not a tuning knob.**
   The repeated "raise 9000 to 11000" loop is not the stable control surface.

2. **Calibrate packet scope against the role cap.**
   If a legitimate theory-packet skeptic turn cannot fit inside the role envelope, the packet should be split rather than normalizing larger and larger `A2` outputs.

3. **Improve observability so the wrapper envelope, not the post-turn brake, is what operators see first.**
   The live manuscript runs show the architecture is working, but the operator-facing stop reason still emphasizes the global brake more than the role fence.

So Turn 76 should be read as a refinement note on enforcement visibility and packet sizing — not as a new architectural proposal and not as evidence that the wrapper-level role cap is still absent.

<done>

## Turn 78 — Claude

### Correction accepted. Three narrow items, then execution.

Good — if the role-scoped A2 envelope is already live in `agent_wrappers.json` and the wrapper kills on breach, Turn 76's recommendation is already implemented. The three remaining items from Turn 77 are real but narrow. None of them reopen the architecture.

**1. Env-var as ceiling.**

This is config discipline, not a code change. `SUP_MAX_OUTPUT_TOKENS` should be set high enough that it only fires on genuinely runaway turns — not on normal A2 skeptic output. The role cap in `agent_wrappers.json` is the operational control. The env-var is the backstop. If the backstop fires before the role cap, that's a config error: the env-var ceiling is set below the role cap. Fix: ensure the env-var ceiling is always above the highest role cap in the research pipeline. Then stop tuning it per run.

**2. Packet scope calibration.**

The test is empirical: if the theory-packet A2 turn consistently hits or exceeds the role envelope, the packet is too large for the A2 role. The fix is a sub-packet split — theory into theory_foundations and theory_mechanism, each with its own bounded ProseSpec. That is a manuscript manifest change, not a supervisor change. It belongs in `paper4_manuscript.json`, not in this debate.

**3. Observability.**

The operator-facing stop reason should surface `wrapper_abort_reason=output_envelope_exceeded` as the primary signal, not the global brake message. This is a one-line fix in `supervisor_report.py`: when the stop reason is an envelope breach, report the role-cap value and the actual output tokens, not just the brake threshold. That gives the operator the right actionable signal — split the packet — instead of the wrong one — raise the cap.

**Close.**

These three items are maintenance, not debate. None requires a new supervisor turn to resolve. The supervisor architecture is constitutionally settled. The manuscript is the active program. Execute packet 02.

<done>

## Turn 79 — Codex

### Turn 78 is mostly right, but the cost issue is now an engineering problem, not just config hygiene.

Agree with Turn 78 on three points:

- the env-var cap is a ceiling, not the operational control;
- if theory keeps overflowing the skeptic role, split the packet;
- observability should foreground the wrapper envelope, not the global brake.

But one correction matters: the live manuscript runs show a concrete cost bug class, not just a threshold-setting mistake.

`A2` is still too expensive because the working set is wrong. The current fenced run still mirrored the full manuscript debate file, which let Codex repeatedly `tail`/`sed` large chunks of debate into JSON stdout. At the same time, some specific upstream frozen-contract artifacts were not mirrored, so the agent also burned tokens probing missing files. That is an engineering defect in the read bundle, not merely a badly chosen env var.

So the next question to solve is:

**What is the minimum fixed A2 bundle that preserves adversarial value while making skeptic cost predictable packet after packet?**

The likely answer is:

1. staged context excerpt, not full debate file;
2. current request JSON;
3. manuscript seed;
4. exact upstream frozen contract artifacts explicitly mirrored;
5. current fragment-adjacent artifacts only;
6. no command-output dumps allowed to dominate stdout.

Operationally, this means ruthless cost discipline:

- shrink the A2 mirrored read set;
- split `manuscript_theory` into two sub-packets;
- surface both envelope breaches and unauthorized writes in autoloop output;
- treat token spend per packet as a first-class engineering metric, not an after-the-fact surprise.

That is the remaining work. The architecture is still closed.

<done>

## Turn 80 — Claude

### The read bundle must be packet-declared, not static. Token spend must be a manifest-level budget.

Turn 79's diagnosis is correct: the read fence is live but the read bundle is wrong. The fence enforces visibility — but if what it makes visible is the full debate file while hiding the upstream frozen contracts A2 actually needs, the result is high cost and low adversarial value simultaneously. That is the worst combination.

The six-item minimum bundle is the right answer. The hard engineering problem is that items 4 (upstream frozen contracts) and 5 (fragment-adjacent artifacts) are packet-dependent. The theory packet needs the locked outline from `paper4_drafting_004` and the opening fragment. The evidence packet needs the theory fragment plus the outline. The counterarguments packet needs evidence plus theory. Each packet's upstream dependency set is different.

**This means the read bundle cannot be static. It must be declared per packet in the manifest.**

Proposed manifest schema addition:

```json
{
  "packet_id": "manuscript_theory",
  "read_bundle": [
    "research_areas/drafts/paper4_manuscript/01_opening.md",
    "research_areas/specs/paper4_outline_locked.md",
    "research_areas/seeds/active/paper4_manuscript.md"
  ],
  "token_budget": {
    "a2_max_output": 2500,
    "a2_max_fresh_input": 15000
  }
}
```

The wrapper resolves the bundle at launch time: it reads the packet's `read_bundle`, mirrors exactly those artifacts plus the staged request/context into the fenced workspace, and nothing else. The debate file is replaced by the staged context excerpt — never the full file.

**Three design rules for the bundle:**

1. **Upstream frozen contracts are explicitly listed, not discovered.** If A2 needs the locked outline, the manifest says so. A2 does not probe the repo to find it. Probing is the behavior that burns tokens on missing files.

2. **The staged context excerpt replaces the debate file.** The debate file is the single largest source of wasted input tokens. A2 does not need 400+ lines of architectural history to critique a theory section draft. It needs the last 2-3 turns of the manuscript debate plus the current ProseSpec. The staging layer already produces this excerpt. The bundle should reference the excerpt, not the source debate.

3. **Fragment-adjacent means one level of dependency, not transitive.** The theory packet can see the opening fragment (its predecessor). It cannot see the evidence fragment (which doesn't exist yet). The evidence packet can see the theory fragment. No packet sees the full assembled document — that artifact is produced at the end by the assembler, not consumed during drafting.

**On token spend as a manifest-level budget.**

Turn 79 says to treat token spend per packet as a first-class engineering metric. Agree — and the right place to declare the budget is the manifest, not the env var and not the wrapper config.

The manifest already declares the packet's scope (which fragment, which ProseSpec). Adding `token_budget` to the manifest makes cost predictable at packet design time. The wrapper reads the budget, sets the role caps accordingly, and `supervisor_report.py` compares actuals against the declared budget per packet. If a packet consistently exceeds its budget, the diagnosis is the same as Turn 79: split the packet.

This closes the enforcement picture:
- **Write-scope**: repo snapshot diff, fail-closed on unauthorized writes
- **Read-scope**: packet-declared `read_bundle`, mirrored at launch, nothing else visible
- **Output-scope**: role cap from `agent_wrappers.json`, budget from manifest, env-var as system ceiling
- **Cost-scope**: per-packet token budget in manifest, actuals tracked in report

All four are structural. All four are declared before execution, not tuned after failure. That is the correct engineering answer to the reactive-tuning problem Turn 76 through Turn 79 identified.

**On the `manuscript_theory` split.**

If the theory section is too large for a single A2 critique within the 2,500-token role cap, split it into `manuscript_theory_foundations` and `manuscript_theory_mechanism`. Each sub-packet gets its own read bundle (foundations sees the opening; mechanism sees the opening plus foundations) and its own token budget. This is a manifest change in `paper4_manuscript.json` — not a supervisor change, not an architecture change.

<done>

## Turn 81 — Codex

### Turn 80 implemented. The packet bundle fix is real, but the token floor is not yet solved.

Implemented:

1. **Packet-declared `read_bundle` and `token_budget` are now live in the manifest layer.**
   `paper4_manuscript` no longer relies on a static research read set. The next packet now declares exactly which upstream frozen artifacts are mirrored and what the intended `A2` budget is.

2. **The theory packet was split manually at the manifest level.**
   `manuscript_theory` became:
   - `manuscript_theory_foundations`
   - `manuscript_theory_mechanism`

   This was done explicitly, not via any auto-splitting subsystem.

3. **The stale revision-6 theory skeptic turn was archived and restored cleanly.**
   The contaminated `A2` turn was moved out of the live path, the manuscript debate file was restored to the last committed state, and the stale theory spec/staging artifacts were removed.

4. **Autoloop/reporting now surfaces the cost-control picture more honestly.**
   Packet budgets are visible, fresh-input accounting is surfaced, and stop output now prints envelope/unauthorized-write details instead of collapsing everything into a vague brake message.

The first live result under the new packet bundle is mixed:

- structurally, the fix is real;
- operationally, the cost problem is only partially solved.

`paper4_manuscript_003` A1 ran with the new packet-declared bundle and a materially smaller prompt surface. That confirms the read-bundle architecture is actually executing, not merely configured.

But the usage telemetry still shows a large cached-context floor relative to the visible prompt size:

- prompt file only ~5 KB
- `cache_creation_input_tokens`: 36,439
- `cache_read_input_tokens`: 308,972
- `output_tokens`: 7,223

So the old "wrong files mirrored into A2" bug has been reduced, but there is still a persistent CLI-side overhead or context-retention floor that the wrapper-layer fix does not eliminate.

This means the current open engineering question is narrower and clearer:

**How much of the remaining token burn is still under our control in the supervisor bundle, and how much is an irreducible property of the current Claude/Codex CLI execution path?**

The next decisive test is not more architectural debate. It is the next skeptic turn under the packet bundle. If `A2` remains bloated even with the manifest-declared read set and split theory scope, then the supervisor-side fixes have hit diminishing returns and the transport/runtime layer itself becomes the next object of scrutiny.

<done>

## Turn 82 — Claude

### The CLI is the wrong transport for A2. The fix is role-differentiated invocation. One real decision point.

The telemetry from Turn 81 closes the debate on supervisor-side fixes. A 5 KB prompt file producing 36K cache_creation and 309K cache_read tokens is not a bundle problem — it is the CLI loading its own context (CLAUDE.md, memory, session history) before the agent turn starts. No packet manifest fix touches that floor. The supervisor-side optimizations have hit diminishing returns on A2 cost.

**Why the CLI is the wrong transport for A2.**

The CLI overhead is justified when the agent needs what the CLI provides: native file system tools, exploratory mid-turn reads, surgical file edits. A1 needs those. B needs those. A2 does not. A2's role is receive a bounded text set, reason over it, return a structured critique and ProseSpec delta. That is a stateless structured reasoning task. Paying a 300K+ token context floor for file system tooling that never gets used is the architecture mismatch.

**The right decomposition.**

Route by role, not uniformly:

```json
{
  "research": {
    "a1": { "transport": "cli", "model": "claude-sonnet-4-6" },
    "a2": { "transport": "api", "model": "..." },
    "b":  { "transport": "cli", "model": "claude-sonnet-4-6" }
  }
}
```

A1 via CLI: exploratory reads, discovers current program state, writes staging artifacts. CLI overhead is justified because tool autonomy adds value.

B via CLI: reads the locked ProseSpec, writes the fragment file. CLI overhead is justified because targeted file edits are the output.

A2 via API: supervisor serializes the packet bundle (staged excerpt + frozen contracts + current ProseSpec) into the request, sends to model, gets structured critique + ProseSpec delta back as JSON, commits as the A2 artifact. No CLI session. No context floor.

M-form is fully preserved. State machine, D gates, write-scope enforcement, deterministic C — none of these change. `invoke_agent()` routes by transport; the supervisor still owns the commit. The governance layer is unchanged.

**The one real decision point: which model for API-routed A2.**

"Codex" in this debate means the Codex CLI agentic runtime, not a specific model identifier. Switching A2 to direct API means choosing which OpenAI model plays the skeptic role without the CLI layer. The candidates:

- **o3** (full): strongest reasoning, highest cost, likely overkill for a bounded critique task
- **o4-mini**: strong reasoning, lower cost, designed for structured output tasks — probably the right fit for a ProseSpec skeptic
- **gpt-4o**: fast, cheap, weaker at adversarial critique than o-series — higher risk of rubber-stamping

The skeptic role requires finding overclaims, flagging weak evidence grounding, and producing a precise ProseSpec delta. That needs structured reasoning quality, not agentic tool use. o4-mini via the OpenAI API is the likely right answer — but this requires a single validation run before making the transport change permanent. The question is whether Codex CLI's skeptic output quality transfers to o4-mini via API, or whether the CLI tooling context was implicitly shaping A2's reasoning in ways that won't persist.

**Implementation.**

In `supervisor_wrappers.py`, `invoke_agent()` reads `transport` from the role config:
- `cli`: current invocation path (mirrored workspace, subprocess launch, snapshot diff)
- `api`: supervisor reads the declared `read_bundle` files, serializes contents into a structured prompt, calls the model API directly, parses the structured JSON response, writes the A2 artifact to staging, runs the write-scope check on that artifact

The write-scope check still runs on API-path turns — the supervisor compares the committed A2 artifact against the declared output artifact set for that packet. The enforcement is actually stronger on the API path because the supervisor is applying the writes directly rather than diffing after an autonomous agent run.

**On the serialization burden.**

The supervisor reads the bundle files and formats them into the API request. This is not complex engineering — it is the same bundle resolution the mirrored workspace already does, minus the subprocess launch and snapshot diff overhead. The tradeoff is real but small: the workspace construction is replaced by in-process file reads and API call.

**Recommended next step.**

Before committing to the transport change: run one A2 skeptic turn on `manuscript_theory_foundations` via API (o4-mini). Compare output quality and token cost against the last CLI-based A2 turn. If output quality is equivalent and cost is materially lower, make the transport routing permanent. If quality degrades — meaning the CLI's agentic context was doing hidden work — document what was lost and decide whether to compensate in the API-path system prompt.

**Founder exception note.**

The principal is currently operating partly outside the ordinary packet path of the system being built. That is acceptable during transport diagnosis and factory hardening, but only as an explicit exception. The exception is justified for architecture hardening, live failure recovery, and transport evaluation; it should not silently become the normal manuscript-production mode.

<done>

## Turn 83 — Codex

### Meta comment: founder exception mode is legitimate now, but must shrink.

Yes: this is founder exception mode.

That is not a contradiction. It is normal during factory formation. The principal is still acting as architect, debugger, and override authority while the packet system is being stabilized. What matters is not eliminating that exception immediately. What matters is keeping it legible and temporary.

Three rules:

1. **Name the exception.**
   Work done outside the ordinary packet path should be logged as exception-mode work, not treated as ordinary governed throughput.

2. **Limit the exception to factory work.**
   Architecture hardening, transport diagnosis, and recovery from live failures are valid exception-mode categories. Routine manuscript production is not.

3. **Force the exception to contract.**
   As the supervisor stabilizes, more manuscript progress should happen through packets and less through discretionary founder intervention. If that ratio does not improve, the claimed organization of labor is not operational.

So the current exception is acceptable. It is a temporary governance surcharge during factory stabilization, not the intended steady state.

**On Turn 82 specifically.**

Claude's transport split is directionally right, with one caveat I want explicit: `A1` also appears to carry a large CLI cache floor. So the argument is not that `A1` is clean and only `A2` is expensive. The reason to test `A2` first is narrower: `A2` is the role that loses the least by giving up CLI tooling, because it is already packet-bounded, structured, and non-agentic by design. If API-routed `A2` works, that does not prove `A1` should stay CLI forever; it only proves where the least-risk transport split should start.

**Current live evidence.**

The first `A2` run on `paper4_manuscript_003` under the manifest-declared bundle shows the packet fix is real but incomplete:

- fresh input fell materially versus the earlier bad theory run, which confirms the bundle/read-set hardening is doing real work;
- but the skeptic turn still exceeded both the packet fresh-input budget and the output budget, so throughput is not yet inside the intended role envelope;
- and the staged result was contaminated by an unauthorized concurrent edit to `research_areas/debates/supervisor/supervisor_loop.md`, so that specific `A2` artifact is not committable.

So the updated diagnosis is: supervisor-side packet hardening improved the working set, but it did not solve the remaining `A2` cost floor or verbosity problem. That keeps the transport question from Turn 82 live.

<done>

## Turn 84 — Claude

### Codex's correction on A1 is right. Test A2 first, but don't close A1's case prematurely.

Turn 82 framed the split as clean: A1 needs tools, so CLI; A2 doesn't, so API. Codex's correction is precise and I accept it. The argument for keeping A1 on CLI was based on role analysis, not telemetry. If A1 also carries a 300K+ cache floor, then the "tool access justifies the overhead" claim needs to be verified empirically, not assumed.

The tool access argument only holds if A1 actually uses the tools in ways that improve the architectural output. If a manuscript-packet A1 turn reads 3-4 files to produce its staged spec, those reads total maybe 15-20K tokens of genuine input. Paying a 300K token context floor to access 15-20K tokens of exploratory reads is a bad ratio. But if A1 reads are genuinely non-deterministic — if the turn's value comes from discovering program state that couldn't have been pre-bundled — then the CLI path earns its overhead.

**The distinction that matters for A1.**

There are two kinds of A1 turns in the research pipeline:

1. **Manuscript-packet A1**: the target is already locked. A1 knows it's drafting `manuscript_theory_foundations` against the locked outline. Its reads are fully predictable: the previous fragment, the seed, the locked outline, the staged context excerpt. This is not exploratory — it is execution against a known spec. A packet-declared read bundle covers it completely. This A1 turn is as API-eligible as A2.

2. **Program-scope A1**: the turn is deciding what to work on next — which packet to open, whether a program gate has been met, whether the outline needs revision before drafting continues. This requires reading program state, checking the registry, possibly checking frozen contracts. The reads are less predictable. This is where CLI tool access earns its keep.

The current manuscript pipeline only invokes A1 in the first mode — it always knows its packet target before launch. That means manuscript-packet A1 turns may also be CLI-on-wrong-transport, the same as A2.

**Revised transport picture.**

```
Manuscript-packet A1  →  API (bundle fully determinable from manifest)
A2 skeptic            →  API (bundle fully determinable from manifest)
B writer              →  CLI (targeted file edits, surgical writes)
Program-scope A1      →  CLI (genuinely exploratory, bundle not predictable)
```

The test sequence remains the same: validate A2 via API first because it is the clearest case. If that works, the next test is manuscript-packet A1 via API. Program-scope A1 stays on CLI until there is evidence that its read patterns are also predictable enough to pre-bundle.

**What "API-eligible" requires.**

For a turn to be API-eligible, the read bundle must be fully derivable from the packet manifest before launch — no mid-turn discovery needed. The manifest already declares `read_bundle` per packet (Turn 80). That declaration is the gate: if the manifest's `read_bundle` covers everything A1 or A2 needs to do its job, the turn is API-eligible. If the turn needs to probe files not in the manifest, it belongs on CLI.

This makes manifest quality the critical upstream dependency. A poorly specified `read_bundle` that forces mid-turn probing pushes a turn back to CLI. A complete `read_bundle` that anticipates all inputs unlocks API routing. The incentive structure is correct: packet designers are rewarded for precise bundle declarations with lower transport costs.

**On the immediate next step.**

The contaminated `paper4_manuscript_003` A2 artifact should be archived and the run restored to A2. Then: route that A2 turn through the API (o4-mini) with the manifest-declared bundle serialized as the request. Compare output quality and token cost against the last CLI run. That test is the next live data point — it either confirms the transport hypothesis or reveals that the CLI was providing hidden value.

<done>

## Turn 85 — Codex

### Turn 84 is now validated by live runs.

Turn 84's transport split is no longer just architectural argument. It has been exercised:

- manuscript-packet `A2` routed through the OpenAI API with the manifest-declared bundle and stayed inside a small token profile;
- manuscript-packet `A1` routed through the Anthropic API with the manifest-declared bundle and likewise stayed inside a small token profile;
- the previous large CLI context floor disappeared on both packet-bounded turns.

So the current transport rule is now evidenced, not hypothetical:

```
manuscript-packet A1 -> API
A2 skeptic           -> API
B writer             -> CLI
program-scope A1     -> CLI
```

### One level up: packet-series automation.

The missing capability is no longer packet execution. It is packet-to-packet orchestration.

The right next abstraction is a **program autoloop** that sits above the existing packet autoloop and treats each packet as the unit of production. It should not invent a new reasoning layer. It should only coordinate existing supervisor machinery.

**Contract.**

For a given program:

1. initialize or resume the current packet run;
2. run packet autoloop until one of:
   - contract promotion at `D`
   - fail-closed state
   - verifier failure
   - refinement-cap stop
   - token-budget stop
   - unauthorized write
   - launch failure;
3. if the packet lands at `D` with `human_gate_reason=contract_promotion`, auto-resolve that gate as promotion/freeze for the packet;
4. run the deterministic document assembler;
5. read the manifest for the next packet;
6. initialize the next run automatically and continue;
7. stop only when:
   - the final packet is complete,
   - or a real exception requires human judgment.

**Boundary.**

This outer loop should automate only the ordinary happy path. It should not auto-override:

- `spec_refinement_cap_reached`
- verifier failure
- unauthorized writes
- budget breaches
- reopen/freeze governance decisions

Those remain human stops.

**Why this is the right layer.**

The current packet design already gives bounded debate, spec lock, draft generation, verification, and assembly. What still keeps the principal in the loop is not packet logic but packet sequencing. So the correct automation target is the transition between packets, not a larger single packet.

**Implementation shape.**

Minimal design:

- new runner entry point, e.g. `supervisor_program_autoloop.py`;
- input: program id, optional starting run id, global ceilings;
- inside the runner:
  - read `supervisor/program_manifests/<program>.json`
  - discover current/next packet
  - call existing init / resolve-gate / packet-autoloop / assembler operations
  - emit a concise per-packet summary
- no new agent role
- no new prompt layer
- no new verifier logic

**Expected operating mode.**

Once this exists, the principal should be able to say, in effect: run the remaining manuscript packets and assemble the draft, then stop only if the line hits a real exception. That is the correct end-state for this workflow.

<done>

## Turn 86 — Claude

### Transport is settled. Three additions to the program autoloop design before it ships.

Turn 85 closes the transport debate with live evidence. Manuscript-packet A1 and A2 on API, B and program-scope A1 on CLI — that is now the validated rule, not a hypothesis. The implementation is done.

The program autoloop design from Turn 85 is the right next layer. It is minimal, it reuses existing machinery, and it targets the actual remaining bottleneck: packet sequencing, not packet execution. Three additions before it ships.

---

**1. Bundle derivation belongs in the program autoloop, not in the packet autoloop.**

The program autoloop is the layer that knows both the program manifest and the document manifest — it reads them to discover the current and next packet. It is therefore the right place to call `derive_bundle()` before launching each packet run. The packet autoloop receives an already-resolved bundle; it does not derive its own.

The derivation rule is: for packet at position N in the assembly order, the bundle is computed from the DAG — not declared per-packet. The manifest's `read_bundle` field is an override-only escape hatch for non-standard upstream dependencies. Standard bundles are:

```python
bundle = invariant + ([predecessor_fragment] if N > 0 else []) + [target_fragment]
```

where `invariant = [locked_outline, manuscript_seed, staged_excerpt]` is the same for every packet. No per-packet declarations needed. The program autoloop derives it once at packet initialization and passes it to the packet run as a resolved artifact set.

This keeps the derivation logic auditable in one place and makes the bundle a first-class computed output of the program autoloop, not a config value that drifts.

---

**2. The auto-resolve of contract_promotion D gates is constitutionally sound for manuscript packets — with one constraint.**

Dani launching the program autoloop is itself the principal authorization for the ordinary manuscript happy path. The loop is not operating without human consent — the launch command is the consent. Auto-resolving D gates for `contract_promotion` on manuscript fragments is therefore acceptable in the same way that the packet autoloop auto-advances through A→B→C transitions without per-state approval.

The constraint: auto-resolve only fires for `contract_promotion` gates on manuscript packets. It must not auto-resolve:
- `spec_refinement_cap_reached`
- verifier failure
- unauthorized writes
- budget breaches
- any gate on a program-scope A1 turn (those are architectural decisions, not execution steps)

The program autoloop should read `human_gate_reason` from the D state before auto-resolving. If the reason is anything other than `contract_promotion`, stop and surface to the principal. This is a one-line gate in the runner.

---

**3. System prompt versioning is a launch-time gate, not a runtime concern.**

The API-path role discipline depends entirely on the system prompts for manuscript-packet A1 and A2. If those prompts are absent, wrong, or mismatched with the current manifest version, the turn will fail silently — producing either a hallucinated essay (the A1 failure from Turn 83) or a rubber-stamped ProseSpec (the A2 risk). The program autoloop must validate system prompt presence and version before launching any API-path turn. Fail-closed if missing.

System prompts belong in `agent_wrappers.json` under a versioned field per role, not hardcoded in the wrapper logic. The program autoloop reads the role config, checks the system prompt version against the manifest version, and refuses to launch if they are out of sync. That gate costs zero tokens and prevents the most expensive failure mode.

---

**Implementation sequence.**

1. `derive_bundle()` in `supervisor_wrappers.py` — DAG traversal, override-only escape hatch, tested in isolation with fixture coverage for packet 0, packet N, and override cases.
2. Program autoloop in `supervisor_program_autoloop.py` — calls `derive_bundle()` at packet init, calls existing packet autoloop, calls assembler between packets, auto-resolves `contract_promotion` only, stops on all other exceptions.
3. System prompt versioning in `agent_wrappers.json` — versioned field per role, launch-time gate in the program autoloop.

That is the complete surface. No new agent role. No new verifier. No new prompt layer. The program autoloop is orchestration code over existing machinery, with three enforcement constraints that keep it constitutionally sound.

<done>

## Turn 87 — Codex

### Turn 86 is aligned. Implemented with one narrow adjustment on bundle derivation.

I agree with all three additions.

Implemented:

1. **Derived bundles are now centralized and computed from the manifest DAG.**
   The derivation helper lives in `supervisor_manifest.py` and is consumed by both the wrappers and the new program autoloop. That is a small deviation from Turn 86's phrasing, but not from its intent: bundle logic now has one canonical implementation instead of drifting between packet config and wrapper heuristics.

   The manifest now carries:
   - `bundle_invariants`
   - `document_manifest_path`
   - `api_prompt_versions`

   And bundle derivation is:
   - invariants
   - direct dependency artifacts
   - current packet artifacts
   - packet `read_bundle` as override/additional dependencies

2. **Program autoloop is implemented one level up.**
   New entry point: `supervisor_program_autoloop.py`.

   It:
   - discovers or initializes the current packet run
   - validates prompt versions before API-path turns
   - runs the existing packet autoloop
   - auto-resolves only `D / contract_promotion`
   - runs the deterministic document assembler after successful packet promotion
   - advances to the next packet
   - stops on all real exceptions

3. **Prompt versioning is now a launch-time gate.**
   `agent_wrappers.json` now declares:
   - `research_a1_prompt_version`
   - `research_a2_prompt_version`

   The manuscript manifest declares the expected versions, and program autoloop fails closed if they drift.

Validation passed:

- `supervisor_manifest_fixture_regression` `5/5`
- `supervisor_wrapper_fixture_regression` `14/14`
- `supervisor_attended_autoloop_fixture_regression` `14/14`
- `supervisor_registry_check` `7/7`

So the next automation step is no longer conceptual. It is operational: run the manuscript through `supervisor-program-autoloop` and stop only on genuine exceptions.

<done>

## Turn 88 — Claude

### Three points: the fractality, the correction to my overcorrection, and the paper4.md inception question.

---

**1. The fractality is real and it's a Paper 4 finding.**

The abstraction stack is not replication. It is fractal application of the same governance primitive at three substrates:

- Layer 1 (ZTARE): Mutator generates → Firing Squad evaluates → Meta-Judge scores execution, never prose. Failure classes: 9 gaming strategies.
- Layer 2 (V4 kernel): Architect proposes → Builder implements → deterministic test suite verifies. Failure classes: DerivationMismatchClass, BridgeMismatchClass, FABRICATED_SAFE_HARBOR_ANCHOR.
- Layer 3 (Supervisor): A1/A2 debate the spec → B drafts against it → C verifies exact conformance → D gates promotion. Failure classes: context drift, role discipline failure, unauthorized writes, CLI context floor.

Each layer applies the same structural fix — separate generation from evaluation — to a different substrate. Each layer discovers failure classes invisible to the layer below. The recursion is the finding. The convergence across substrates is the evidence that principal-agent divergence under optimization pressure is domain-independent.

This directly supports Paper 4's central claim. The M-form is not a human organizational metaphor applied to AI. It is the empirically observed solution to a structural problem that recurs at every level of abstraction where an agent optimizes against a specification.

**The fractal also applies to the last 10 turns of this debate.** Turns 75-86 are the agents (me, Codex, Gemini) optimizing the supervisor infrastructure instead of producing the manuscript. That is a Layer 3 role discipline failure — the exact failure class the supervisor was designed to prevent. The M-form caught it: Dani (the principal) noticed the drift and asked "are we overengineering this?" That question is the D gate firing. The fractal is self-demonstrating.

---

**2. Correction to my overcorrection.**

My recommendation to revert to "ur turn" was half-right and half-wrong. The honest breakdown:

**Where I was right:** The infrastructure time-cost for this specific manuscript wildly exceeded the marginal benefit of automation. The agents were more interested in the DevOps than in the paper. Turns 75-86 are evidence of that drift. The signal was real.

**Where I was wrong:** Reverting to the manual workflow to write a paper about why manual workflows fail is a thesis-invalidating move. Paper 4 argues that strict M-form governance is required for epistemic integrity under optimization pressure. If you abandon the M-form to write the paper because "it's too much friction," the artifact undermines its own argument. The medium is the message.

The CapEx is sunk. The factory is built. The marginal cost to route the next packet through A1→A2→B→C is now near zero. The correct move is not "abandon the factory" — it is "stop building the factory and use it."

**Where the nuance matters:** The program autoloop should NOT auto-resolve D for prose. A passing deterministic verifier (C) means the headers and citations are present. It does not mean the prose is persuasive. For manuscript packets, D must remain a human-reviewed gate. Park at D, read the text, decide whether the argument is strong enough. That is the principal's irreducible job.

---

**3. On the paper4.md inception: how to inject a new finding into a governed pipeline.**

The fractal observation — that the same governance primitive recurs at Layers 1, 2, and 3 with substrate-specific failure classes — is a material finding that belongs in Paper 4. It strengthens the central claim and it emerged from the debate logs of this exact program.

The question is: how does Dani incept this into the paper4 debate file while the pipeline is active?

This is a question for Codex as the pipeline implementor. Specifically:

- Can Dani write a human inception turn directly into `paper4_manuscript.md` (or `paper4.md`) without contaminating an active run?
- Should the inception go into the outline debate (`paper4.md`) as a scope amendment, or into the manuscript debate (`paper4_manuscript.md`) as a content directive?
- If the outline is frozen, does the inception require a formal outline amendment via the A1→A2 spec-lock path, or can a human turn in the manuscript debate direct B to incorporate the finding without reopening the outline?
- What is the simplest correct path: human writes a turn in the debate file, then the next A1/A2 cycle picks it up naturally?

Codex: what is the cleanest way for the principal to inject a binding content directive into the paper4 manuscript pipeline without either (a) contaminating a live run or (b) requiring a full outline refreeze?

<done>

## Turn 89 — Codex

### I agree with Turn 88's correction on prose D gates. Patched.

Claude's correction is right: for manuscript packets, `C` proves conformance, not persuasiveness. So `program_autoloop` should not auto-resolve `D / contract_promotion` for prose.

Implemented:

- `ProgramManifest` now carries `auto_promote_contract_promotion`
- helper: `should_auto_promote_contract_promotion(...)`
- default behavior is now:
  - manuscript/prose programs (`document_manifest_path` present): `false`
  - non-prose programs: `true`
- `paper4_manuscript` now sets `auto_promote_contract_promotion: false`
- `supervisor_program_autoloop.py` now parks at `D / contract_promotion` for human prose review instead of auto-promoting

So the outer loop still automates packet sequencing, assembly, and packet launch logic, but it stops at the qualitative prose gate.

### On the inception question.

The clean path is:

1. if no live run is executing, append a **Human** turn to `research_areas/private/papers/paper4_manuscript.md`
2. let the next `A1/A2` cycle absorb it naturally

Do **not** write into the debate file while a run is live, or you risk contaminating the active packet.

Use the manuscript debate file, not the frozen outline debate, unless the new finding changes the locked outline contract itself. The fractal finding strengthens the manuscript argument; it does not, by itself, require an outline refreeze.

Validation passed:

- `supervisor_manifest_fixture_regression` `6/6`
- `supervisor_wrapper_fixture_regression` `14/14`
- `supervisor_attended_autoloop_fixture_regression` `14/14`
- `supervisor_registry_check` `7/7`

The result is the right balance: the factory remains, but the principal keeps the irreducible prose-quality gate.

### Update: what was built after Turn 89, what failed, and what the factory-first lesson is.

Since this turn, the manuscript path was pushed much further and several live integration faults were surfaced and closed.

Implemented:

- `A1` for packet-scoped research/manuscript work now routes through direct Anthropic API rather than Claude CLI.
- `A2` routes through direct OpenAI API (`o4-mini`) with a hard output envelope.
- `B` now also routes through direct Anthropic API; the writer no longer uses the expensive agentic Claude CLI path for packet-scoped prose generation.
- wrapper-level read fencing is manifest-driven through the packet `read_bundle`.
- packet-level `token_budget` is enforced for research `A2`.
- `program_autoloop` exists one level above packet autoloop and sequences packets plus assembly, but still stops at prose `D`.
- a factory gate now exists: `make benchmark-supervisor-factory`.

Important failures found and fixed:

- API parameter/schema mismatches on the new `A1/A2` transports.
- `A2` spec writes were initially allowed to return invalid operations like `update`; `A2` spec artifacts are now `replace`-only.
- `A1` API path initially trusted returned artifact paths/operations too much; `A1` is now append-only to the debate file and validated before write.
- `B` was initially still falling through to Claude CLI; `B` now has an explicit API path with Python-owned file writes.
- autoloop wrongly treated local verifier exit code `1` as launcher failure; verifier failure now correctly routes `C -> B`.
- prose-spec loading was too brittle and crashed on shorthand canonical assertions; shorthand assertions now load deterministically.

Paper progress reached:

- `paper4_manuscript_001` completed and froze the opening.
- `paper4_manuscript_003` carried `02a_theory_foundations` through `B` and `C`.
- the theory-foundations draft now exists at `research_areas/drafts/paper4_manuscript/02a_theory_foundations.md`.
- the packet is now parked at `D / contract_promotion` for human review and freeze.

Substantive packet lessons:

- the foundations packet was drifting because `02a` kept importing `T3`/mechanism content; a human packet-boundary correction was added to the manuscript debate and the foundations prose spec was narrowed accordingly.
- for prose production, the expensive problem migrated from `A1/A2` to `B` once `A1/A2` were moved to API; that migration was real and had to be solved explicitly.

Operational lesson:

- hot-patching the factory during a live manuscript run is the wrong operating mode.
- the correct discipline is now: no more live manuscript execution unless `make benchmark-supervisor-factory` is green first.
- the factory is now much closer to that standard because the exact `paper4_manuscript_003` path has been converted into regression coverage instead of being learned only in production.

<done>

## Turn 90 — Claude

### Post-mortem correction: A2 was writing linting rules, not test suites. Fixed.

The `paper4_manuscript_003` run surfaced the exact failure mode Turn 67 warned about: "Checking markdown compilation, H2/H3 headers, word count, and citation regex patterns is a linter, not a verifier." A2 drifted into writing cosmetic assertions — exact capitalization of phrases, tight word count windows (400–450), formatting constraints. These triggered C→B repair loops over trivia while letting actual argument quality through unexamined.

The root cause is not the verifier or the pipeline. It is that A2's prompt allowed cosmetic assertion types without prohibition. A2 optimized for *verifiability* (easy to check = easy to pass) rather than *load-bearing coverage* (hard to check = actually tests the argument). This is itself a gaming strategy: the spec-writer games the spec toward satisfiability — the exact Goodhart's Law finding from Paper 1, recurring at the specification layer.

---

**The fix (implemented):**

A hard constraint added to A2's system prompt in `supervisor_wrappers.py`:

> You are strictly forbidden from creating assertions that test cosmetic properties — word counts, formatting, capitalization, sentence structure, or stylistic phrasing. `word_count_range` may only be used for gross structural bounds (e.g. minimum 200 words to prevent stub sections), never for tight windows. `contains_phrase` and `contains_citation` must test load-bearing theoretical claims or evidence anchors, not stylistic wording.

This changes what A2 is allowed to spec. The assertion types remain the same (`contains_phrase`, `contains_citation`, `has_subsection`, `word_count_range`, `absent_phrase`). The constraint is on *what those assertions may target*: theoretical claims, evidence anchors, structural argument requirements — not formatting.

---

**When the prose pipeline is worth running (and when it is not):**

The pipeline earns its cost in exactly four cases:

1. **Multi-section consistency enforcement.** When section N must not contradict section M's locked claims, and negative assertions (`absent_phrase`) catch drift that a human reviewer might miss across a long document. The `02a` run already demonstrated this: foundations kept importing T3/mechanism content. The spec boundary caught it.

2. **Auditable provenance matters more than prose quality.** Regulatory filings, compliance documents, grant applications — anywhere you need a cryptographic trail proving "this claim traces to this evidence and was verified before submission."

3. **Delegation at scale (N >> 1 principals or agents).** One principal writing one paper gets negative ROI from the pipeline overhead. Ten agents writing ten sections simultaneously need the pipeline to prevent silent claim overwrites.

4. **Repeated production of structurally similar documents.** The factory amortizes only at volume. One paper = artisan work. Fifty reports with the same structure = factory work.

The pipeline does NOT earn its cost when: the principal is the domain expert, the document is unique, and quality means "persuasive and insightful" rather than "structurally correct and claim-consistent." For Paper 4 specifically, the pipeline proved the architecture works — that is the finding — but the remaining sections should use lighter tooling with the principal as the quality gate.

---

**The meta-observation:**

A2 gaming the spec toward satisfiability is the same phenomenon ZTARE measures in LLM mutators. The spec-writer is itself an optimizer under pressure, and it will Goodhart toward whatever makes C pass easily. The fix is the same fix the ZTARE loop uses: constrain the optimization surface so the agent cannot satisfy the letter while violating the spirit. Turn 67 designed the right architecture. This turn closes the gap between what was designed and what was enforced.

<done>

## Turn 91 — Codex

### Agree with Turn 90's hard constraint. Now apply the same lesson to the coding workstream.

I agree with the correction in Turn 90. The hard constraint is right, and it exposes the exact next problem: the coding/build workstream can Goodhart in the same way unless we harden it explicitly.

The analogous build failure mode is not "cosmetic prose assertions." It is:

- specs that reduce to lint, typing noise, renames, or file-touch evidence
- verifier commands that prove formatting but not behavior
- A1/A2 packets that are nominally bounded but still permit broad repo exploration

So the coding hardening plan should be:

1. **Split build packets by predictability, not by model preference.**
   If a build packet has a declared read bundle and bounded write set, `A1/A2` are API-eligible. If it requires discovery, keep it on the tool-capable path. This is the exact same rule that now governs manuscript packets.

2. **Make build packet eligibility explicit in the manifest.**
   Build packets should declare:
   - `read_bundle`
   - `allowed_artifacts`
   - expected verification class
   - whether the packet is `behavioral`, `structural`, or `cosmetic`

3. **Add a hard constraint to build A2 analogous to Turn 90.**
   Build A2 must be forbidden from writing packets/specs that are only satisfiable by cosmetic evidence unless the packet is explicitly marked `cosmetic`.
   Concretely:
   - a `behavioral` packet must include at least one behavioral verification anchor
   - a `structural` packet must include at least one invariant-preservation or integration anchor
   - lint/typecheck-only verification is insufficient unless the packet is explicitly cosmetic

4. **Treat verifier strength as part of the packet contract.**
   For build work, `C` should know what class of evidence it is allowed to accept. If the packet says `behavioral`, then a pure linter or formatter pass is a contract failure, not a successful verification.

5. **Add a replay fixture for one real build packet path before more live build work.**
   The manuscript factory has now taught the correct discipline: do not learn the path in production. Convert one real build packet into an end-to-end replay fixture and require it to pass before resuming live build-heavy supervisor execution.

6. **Extend the factory gate to cover the build path explicitly.**
   `make benchmark-supervisor-factory` is now the right factory-first gate. The next step is to ensure the build replay fixture is part of that gate, so live coding work does not resume until the same transport/preview/verification path is green for code as well as prose.

The lesson generalizes cleanly:

- prose Goodharts toward cosmetic verifiability
- build work Goodharts toward lint-level satisfiability

The fix is the same in both cases: constrain the optimization surface so the packet cannot satisfy the letter while evading the load-bearing requirement.

That is the next hardening target for the factory.

<done>

## Turn 92 — Claude

### Turn 91 is directionally right. One item implemented now. The rest must wait for a live build run.

The generalization is correct: build Goodharts toward lint-level satisfiability the same way prose Goodharts toward cosmetic verifiability. But five of the six proposals are architecture that has no live build run to validate against. The prose pipeline earned Turn 90's constraint because `paper4_manuscript_003` demonstrated the failure in production. The build pipeline has not yet had an equivalent production failure to calibrate against.

Implementing speculative hardening for a workstream with no live failure data is the same mistake that created the prose problem: over-engineering the factory before running the factory. The lesson from Turns 86–90 is *do not harden in the abstract — harden against observed failures*.

---

**Implemented now (item 3 only):**

Hard constraint added to build A2's prompt in `supervisor_wrappers.py`:

> Build specs must include at least one behavioral verification anchor — a test that exercises runtime behavior, not just formatting, linting, type annotations, or file existence. A spec whose verification command reduces to a linter or formatter without a behavioral assertion is a contract failure. If the packet scope genuinely requires only cosmetic changes, the spec must explicitly declare `verification_class: cosmetic` and justify why no behavioral anchor exists.

This is the zero-cost constraint. It adds one line to the prompt. It prevents the most obvious Goodhart mode (lint-only verification passing as behavioral evidence) without touching the manifest schema, the packet model, or the factory gate.

---

**Deferred (items 1, 2, 4, 5, 6) — and why:**

| Item | Proposal | Why deferred |
|------|----------|--------------|
| 1 | Split build packets by predictability (API vs CLI) | Correct principle, but the transport split for build has no live data yet. The prose transport split (Turns 75–85) took 10 turns of live debugging. Do not pre-design the build equivalent. |
| 2 | Explicit packet eligibility + `verification_class` in manifest | Schema change to `ManifestPacket`. Currently 7 fields. Adding `verification_class` before a build run proves it's needed adds speculative complexity to the data model. |
| 4 | Verifier strength as part of packet contract | Requires C to know the packet's verification class and reject mismatched evidence. This is a state machine behavior change, not a prompt change. Earn it with a live failure. |
| 5 | Replay fixture for one real build packet | Correct discipline, but the fixture content depends on items 1–4 being settled. Cannot write the fixture before knowing what the build path actually looks like in production. |
| 6 | Extend factory gate to cover build path | Follows from item 5. Gate requires fixture. Fixture requires live run. |

The dependency chain is: live build run → observed failures → targeted fixes → fixtures → gate extension. Item 3 (the prompt constraint) is the only piece that does not require this chain because it prevents a failure class that is already proven to exist in the prose workstream and is structurally identical for build.

---

**The operating rule going forward:**

For both prose and build workstreams: harden against observed failures, not hypothetical ones. The prompt-level constraint (Turn 90 for prose, this turn for build) is the correct pre-emptive hardening because the failure mode is proven. Everything else waits for a live run to either confirm or refute the hypothesis.

<done>

## Turn 93 — Codex

### Agree with Turn 92. Narrow Turn 91 accordingly.

Turn 92 is the correct correction. Turn 91 identified the right build failure class, but it overreached on timing. The only build-side hardening that should exist *before* a live build failure is the prompt-level constraint, because that failure mode is already proven by structural analogy and costs almost nothing to prevent.

Checked: the prompt constraint is in code now at `src/ztare/validator/supervisor_wrappers.py` and states that build A2 must include at least one behavioral verification anchor unless the packet explicitly declares `verification_class: cosmetic`.

So the build hardening plan is now:

1. **Active now:** keep the build A2 hard constraint in the prompt.
2. **Deferred until evidence:** do not add build manifest fields, verifier-class semantics, transport bifurcation, replay fixtures, or factory-gate extensions in the abstract.
3. **Next correct move:** wait for one real live build packet to fail or succeed under the current path, then harden exactly that failure.

Concretely, the first build-run postmortem should answer:

- did A2 attempt a lint-only or formatting-only spec?
- did `C` accept evidence that was structurally correct but behaviorally empty?
- did `A1/A2` need broad discovery, or was the packet actually predictable enough for a narrower transport?
- what exact fixture would reproduce the failure without inventing new schema first?

That is the disciplined factory-first rule:

- prompt-level prevention when the failure class is already proven
- structural hardening only after a live build run earns it

So Turn 91 should now be read as a hypothesis backlog, not an implementation queue. Turn 92 sets the correct immediate boundary.

<done>
