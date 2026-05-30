# GP-036 Findings Runner / Supervisor Convergence Seam

> **Seam metadata** · `seam_id:` GP-036 · `track:` apparatus · `status:` `active` (n=1 with operator-granted exception - same basis a · `last_updated:` 2026-05-08


**Track:** findings
**Status:** `active` (n=1 with operator-granted exception — same basis as GP-031: building the bridge before n=2 is cheaper than letting the duplication calcify)
**Origin:** operator review of GP-031 first-slice implementation (2026-04-12)
**Trigger:** operator observed that the findings runner reimplemented ~95% of its stack instead of the promised ~70% reuse of the supervisor

---

## Problem Snapshot

GP-031 opened with a clear architectural contract (Turn 1, confirmed by Codex Turn 2):

> "Reuses ~70% of the supervisor; adds ~30% as sibling primitives."

The specific reuse targets named in the seam:

- **Router** (`actor_for_pipeline_state`) — reuse
- **Cost tracking** (`TurnUsageTelemetry`, `program_cost_usd`, `refinement_cost_usd`) — reuse
- **Write-scope enforcement** (`write_scope_ok`, `unauthorized_repo_paths`) — reuse
- **Human gates** (`HumanGateReason` enum) — reuse
- **Wrapper transport** (`_call_anthropic_research_b_api`, etc.) — reuse
- **Refinement caps** — add a sibling mode (the 30%)

What actually shipped in `supervisor_findings_runner.py` (672 lines):

- **Router** — NOT reused. Runner has its own agent-alternation logic.
- **Cost tracking** — partially reused. `TurnUsageTelemetry` and `estimate_cost_usd` are imported. But the budget envelope is a local `max_cost_usd` parameter instead of the supervisor's `refinement_cost_usd` ledger.
- **Write-scope enforcement** — NOT reused. Runner writes directly to seam files with no write-scope check.
- **Human gates** — NOT reused. Runner has its own `RunnerStopReason` enum.
- **Wrapper transport** — NOT reused. Runner has bespoke `call_claude()` and `call_gemini()` functions (~80 lines each) that duplicate the API call pattern from `supervisor_wrappers.py`.
- **Refinement caps** — added as a sibling (`HARD_TURN_CAP = 12` in the debate primitive). This is the one piece that landed as designed.

The deviation is not hostile — it was a first-slice shortcut to avoid touching the supervisor during a live Planck run. But the shortcut has now shipped, the run is over, and the duplication should be addressed before it calcifies into a permanent parallel system.

## Second problem: context-awareness

The findings runner's agents (Claude via Anthropic API, Gemini via Google GenAI API) receive only the seam text as input. They cannot:

1. **Read other files.** An agent debating GP-034 cannot see GP-035's seam, the ZTARE board, or any related seam. It cannot discover that GP-034 is a downstream symptom of GP-035.
2. **Grep the codebase.** An agent proposing a fix to `information_yield.py` cannot verify whether the function signature it assumes still exists.
3. **Read workspace artifacts.** An agent reasoning about `latent_distance.jsonl` patterns cannot read the actual file to check whether the numbers it cites are correct.
4. **See the ZTARE board.** An agent has no context on what's in-flight, what's blocked, or what seam its finding connects to.

This explains the quality gap between hand-written and runner-generated debate turns observed on GP-034:

- Turns 1-2 (hand-written, Claude Code + Codex CLI with full repo access): identified mechanism, proposed name, proposed fix architecture, filed status — 3 new claims in 2 turns.
- Turns 3-8 (runner-generated, API-only): six turns of "I agree" with zero new claims. Every turn confirmed what was already in the seam because the agents had no external information to contribute.

The runner's mechanical convergence detection worked correctly (all six turns carried the sentinel, CONVERGED fired). But the debate quality was poor because the agents were context-starved.

## Why these are the same seam

Both problems share the same root cause: the findings runner was built as a standalone system instead of as a layer on top of the existing supervisor infrastructure. The supervisor's wrapper transport already has the pattern for giving agents context (staging context JSON with file paths, debate history, artifact pointers). The runner should have reused that pattern to inject relevant context alongside the seam text, and reused the transport itself to make the API calls.

Converging the transport also creates a natural attachment point for context injection: the wrapper already assembles a context payload before calling the API. Extending that payload with related seams, workspace artifacts, and board state is an incremental change to the wrapper, not a new system.

## Constraints

1. Do not break the existing supervisor state machine. The findings runner converges onto the supervisor infrastructure; the supervisor does not move toward the runner.
2. Do not make findings-debate a `SeedPipelineType` in this slice. The pre-seed / post-seed object boundary (Codex Turn 2, GP-031) is still decisive. Convergence is at the transport and utility layer, not at the registry layer.
3. Do not add full agentic tool use (MCP, function calling) to the debate agents in the first slice. That is a much larger architectural change. Context injection via prompt enrichment is the proportionate first move.
4. The convergence detector (`check_convergence` with sentinel-based semantic convergence) is genuinely different from `prose_verifier` (structural conformance). Do not merge them. They are different primitives for different exit contracts.

## Conjectured fix (two parts)

### Part 1: Transport and utility convergence

1. **Decouple the wrapper transport from `HandoffStatus`.** The existing `_call_anthropic_research_b_api` and `_call_gemini` functions in `supervisor_wrappers.py` are currently bound to `HandoffStatus` and tool-use schemas. Extract the raw API call + telemetry capture into a shared transport layer that both the supervisor wrappers and the findings runner can call.
2. **Reuse `write_scope_ok` in the runner.** The runner currently writes to seam files with no scope check. It should validate that the seam path is within the expected findings directory.
3. **Unify cost tracking.** The runner's `max_cost_usd` inline check should use the same cost-ledger pattern as the supervisor's `refinement_cost_usd`, adapted for pre-seed objects (keyed to seam path rather than seed ID).
4. **Map `RunnerStopReason` to `HumanGateReason` at the boundary.** When the runner exits with `ESCALATED_CAP` or `COST_BUDGET`, that is structurally equivalent to a human gate. The runner should emit a typed escalation that the operator can resolve through the existing gate-resolution path rather than a bespoke print-and-exit.

### Part 2: Context injection

1. **Related seams.** When the runner builds a prompt for a debate turn, it should also read the seam's "Relationship to other seams" section and inject the first ~200 lines of each referenced seam file. This gives the agent cross-seam awareness without full repo access.
2. **Workspace artifacts.** If the seam's "Evidence" section references specific file paths, the runner should read those files and include them (or a truncated summary) in the prompt. The agent debating GP-034 should see the actual `latent_distance.jsonl` data, not just the seam's prose description of it.
3. **ZTARE board context.** Inject the relevant row(s) from the private ZTARE board so the agent knows the seam's status, n-count, and relationship to in-flight work.
4. **Codebase snippets (stretch).** For seams that reference specific functions or files in `src/`, the runner could grep for the referenced symbol and inject the relevant code block. This is the most expensive context injection and should be gated on a flag.

## What this does NOT fix

- **Full agentic tool use.** The agents still cannot dynamically explore the repo. They get richer context but cannot decide to look somewhere the prompt didn't anticipate. That is a future architectural decision (and has its own laundering risk — an agent with `grep` access during a debate can selectively cite evidence).
- **Codex as a debate participant.** Codex CLI was rejected for input-token-wall reasons. That constraint still holds. Gemini remains the second voice.
- **Auto-promotion.** Still human-gated. This seam does not touch the promotion path.

## Next action

Debate this seam to convergence. The key design questions for Turn 2:

1. **Is the transport decoupling worth the refactor cost now, or should the runner just import and call the existing wrapper functions with a shim?** The clean path is decoupling; the fast path is a thin adapter.
2. **How much context is too much?** The runner's agents already receive the full seam text. Adding related seams + workspace artifacts + board rows could push the prompt to 50k+ tokens. Should there be a context budget, or should the agents get everything and the cost cap handle it?
3. **Should context injection be a separate module or built into the runner?** If it's a module, the supervisor wrappers could also use it (e.g., injecting ZTARE board context into A1/A2 turns). If it's runner-specific, it stays narrow but duplicates again.

## Debate Log

### Turn 1 — Claude (2026-04-12) — Opening

This seam is opened because the operator correctly identified two failures in the GP-031 first-slice implementation:

1. The findings runner reimplemented ~95% of its stack instead of reusing the supervisor's existing infrastructure as the GP-031 debate converged on.
2. The runner's API-only agents are context-starved, producing low-quality debate turns because they cannot see anything beyond the seam text.

Both failures share the same root cause: the runner was built as a standalone system instead of as a layer on the supervisor. The transport convergence creates the natural attachment point for context injection — the wrapper already assembles context payloads, and extending those payloads is incremental.

The conjectured fix has two parts: (1) converge the transport, cost tracking, write-scope, and escalation paths onto the existing supervisor utilities, and (2) add context injection (related seams, workspace artifacts, board rows, optionally code snippets) to the prompt builder so the agents have something to work with beyond the seam prose.

The key tension is scope: Part 1 is a refactor of existing code with clear boundaries. Part 2 is a new capability that could sprawl if not capped. My lean is to do Part 1 first (it's the debt payment) and Part 2 as a follow-on (it's the capability lift), because Part 1 creates the attachment point that makes Part 2 clean.

Codex or Gemini: push back on whether the transport decoupling is worth the refactor cost now, whether the context budget should be token-based or file-count-based, and whether context injection should be a shared module or runner-specific.

### Turn 2 — Codex (2026-04-12 01:19:47 EDT) — Extract, don’t shim; budget by tokens; shared context builder, runner-first consumer

The seam is real. The root-cause framing is right: the runner was built as a standalone system, so it duplicated transport/state utilities and ended up with context-starved debate agents.

My answers to the three design questions:

1. **Transport decoupling vs shim**

   Do **not** just shim the findings runner into the current supervisor wrapper functions. The existing `_call_anthropic_research_a1_api`, `_call_anthropic_research_b_api`, and `_call_openai_research_a2_api` functions are not generic transports; they are already opinionated around tool-use payloads and `HandoffStatus`-shaped outputs. Shimming the runner onto them would preserve the wrong abstraction boundary.

   But also do **not** do a full wrapper rewrite. The proportionate fix is:

   - extract the raw provider-call + telemetry normalization layer into a shared transport helper
   - leave packet/tool-use schema parsing in `supervisor_wrappers.py`
   - leave debate-turn prompt shaping in `supervisor_findings_runner.py`

   So the recommendation is **narrow decoupling now**, not a thin shim and not a big-bang convergence.

2. **How much context is too much**

   Budget by **tokens / characters**, not by file count.

   File count is the wrong yardstick because one board row and one seam excerpt are not remotely comparable to one `latent_distance.jsonl` or one code snippet. The right first slice is a tiered budget:

   - Tier 0: full seam text (mandatory)
   - Tier 1: current private-board row for the seam (small, mandatory)
   - Tier 2: referenced related-seam excerpts (bounded)
   - Tier 3: explicitly cited workspace artifact excerpts (bounded)
   - Tier 4: code snippets only behind an explicit flag

   That gives the runner a deterministic context budget instead of "include everything and let cost cap handle it," which is too sloppy for a runner that already had a duplication problem.

3. **Shared module or runner-specific**

   Context injection should be a **separate module**, but with the findings runner as the **only consumer in slice 1**.

   Reason:

   - if you build it into the runner, you hard-code the second duplication seam immediately
   - if you try to wire it into the whole supervisor now, scope will sprawl

   So the right middle path is:

   - new shared `findings_context.py` or similar
   - only `supervisor_findings_runner.py` calls it in the first slice
   - later reuse by supervisor wrappers is optional, not part of this packet

Two additional boundary corrections:

4. **Do not force findings debates into `HumanGateReason` internally.**

   I agree with mapping at the boundary, not with sharing the enum internally. `RunnerStopReason` is still the correct local object because findings debate is not a supervisor program state. Emit an adapter record that *can* be translated into `HumanGateReason` if the operator wants to route it through gate resolution later.

5. **Do not force seam-local budget into `refinement_cost_usd` yet.**

   Reuse `TurnUsageTelemetry`, yes. Reuse the exact seed-ledger field, no. Pre-seed objects should stay pre-seed. A seam-local cost ledger keyed by seam path is the right first slice. Promotion-time rollup into seed-side fields can happen later if needed.

So my net recommendation is:

- **Part 1 and Part 2 should not be strictly serial.**
- The next packet should be a **narrow convergence packet** containing:
  - shared raw transport extraction
  - seam-path write-scope enforcement
  - token-budgeted context builder
  - board-row + related-seam + cited-artifact injection
- **Do not include code-grep/snippet injection in slice 1.**

That gives you the debt payment and the quality lift in one bounded move without dragging findings debate into full supervisor-state convergence.

### Turn 3 — Claude (2026-04-12) — Accept all five, converge on the packet shape

Turn 2 is clean. I accept all five decisions without modification:

1. **Narrow decoupling:** extract raw provider-call + telemetry normalization into a shared transport helper. Leave packet parsing in `supervisor_wrappers.py`, leave debate-turn shaping in `supervisor_findings_runner.py`. Not a shim, not a full rewrite.
2. **Token-budgeted tiers (0-4):** mandatory seam text + board row at Tier 0-1, bounded related-seam excerpts at Tier 2, bounded cited-artifact excerpts at Tier 3, code snippets only behind an explicit flag at Tier 4. No Tier 4 in slice 1.
3. **Shared module, runner-first consumer:** new `findings_context.py` (or similar). Only the runner calls it in slice 1. Supervisor wrappers can adopt later but are not in scope.
4. **`RunnerStopReason` stays local:** adapter record at the boundary that *can* translate to `HumanGateReason`, but no internal enum merge. Findings debate is not a supervisor program state.
5. **Seam-local cost ledger:** keyed by seam path, not forced into `refinement_cost_usd`. Reuse `TurnUsageTelemetry` and `estimate_cost_usd` for the individual-turn accounting, add a seam-scoped accumulator for budget enforcement.

**On combining Part 1 and Part 2 into one packet:** agreed. The transport extraction is the precondition that makes context injection clean, but they can ship as a single bounded packet rather than two serial ones. The shared transport gives the context builder a natural call site.

**Packet scope (proposed for the spec):**

The convergence packet should contain exactly these deliverables:

1. **Shared transport helper** — extracts raw Anthropic/Google API call + response normalization + `TurnUsageTelemetry` capture from both `supervisor_wrappers.py` and `supervisor_findings_runner.py` into a common module. Both callers are then thin wrappers over the shared transport.
2. **Write-scope enforcement** — the runner validates seam file paths against `write_scope_ok` (or its equivalent) before writing. No more unguarded writes.
3. **Seam-local cost ledger** — accumulates `estimate_cost_usd` per turn, keyed by seam path, enforces `max_cost_usd` budget. Replaces the current inline check.
4. **`RunnerStopReason` → `HumanGateReason` adapter** — emits a typed escalation record when the runner exits on `ESCALATED_CAP` or `COST_BUDGET`, translatable to the gate-resolution path but not internally merged.
5. **Token-budgeted context builder** (`findings_context.py`) — assembles the tiered context payload (seam text, board row, related seam excerpts, cited artifact excerpts) within a declared token budget. Called by `build_turn_prompt()` in the runner.
6. **Runner prompt enrichment** — `build_turn_prompt()` calls the context builder and injects the result alongside the seam text. Agents now see cross-seam relationships, workspace data, and board state.

**What this packet does NOT include:**

- No Tier 4 code-snippet injection (deferred behind flag, not in slice 1).
- No full agentic tool use for debate agents (still prompt enrichment, not dynamic exploration).
- No `SeedPipelineType` registration for findings debates.
- No `prose_verifier` / `check_convergence` merger.
- No supervisor state-machine changes.

**On critical path:** this packet is NOT on the Planck v3 critical path. It is parallel work that improves debate quality and pays down the GP-031 duplication debt. It does not block GP-035 implementation, 3b substrate-swap, or Sandbox 03. It should be scheduled based on when the operator next wants to use the runner for real debate turns, not based on the Planck timeline.

**Next action:** this debate is essentially converged. The next artifact should be a spec at `research_areas/private/specs/active/GP-036_findings_runner_supervisor_convergence_spec.md` following the standard format. Codex Turn 4 should either ratify and close the debate, or flag anything in the packet scope that is wrong or missing.

### Turn 4 — Codex (2026-04-12 16:15:00 EDT) — Ratify packet, add provenance and non-autonomous escalation constraints

The packet shape is right. I ratify Turns 2-3 with two additional constraints that should be locked before the spec is written.

1. **Injected context must carry provenance labels.**

   The context builder should not just concatenate excerpts. Every injected block needs a compact source header, e.g.:

   - `BOARD_ROW`
   - `RELATED_SEAM_EXCERPT`
   - `CITED_ARTIFACT_EXCERPT`

   and each block should include its path. Without that, the runner gets more context but loses source discipline, which makes later auditing harder and encourages vague debate turns that cannot be traced back to a cold artifact.

   This matters because GP-036 is not only a quality seam. It is also a trust seam. Better prompts that are less auditable are not a win.

2. **The adapter record must not auto-route anything.**

   I agree with the `RunnerStopReason -> HumanGateReason` adapter, but the emitted record should be advisory only in slice 1. No automatic gate creation, no automatic queueing into supervisor resolution, no implicit program state transition. The output should be:

   - typed
   - inspectable
   - available for later routing

   but still operator-pulled, not operator-bypassed.

Those constraints leave the packet otherwise unchanged:

- shared raw transport extraction
- seam-path write-scope enforcement
- seam-local cost ledger
- token-budgeted context builder
- runner prompt enrichment

One more scope line to keep clean in the spec:

- **No artifact discovery beyond explicit citations in slice 1.**

  The runner may include cited artifacts and explicitly named related seams, but it should not start doing fuzzy workspace discovery or broad `rg`-style expansion on its own. That would turn a bounded convergence packet into a silent retrieval system.

So my state is:

- debate: converged
- next artifact: `research_areas/private/specs/active/GP-036_findings_runner_supervisor_convergence_spec.md`
- implementation stance: reasonable after spec, but not straight from seam text

---

## Amendment — 2026-04-15 — Agent-mode flag + slice A/B split

**Why this amendment exists.** The original seam assumed the runner would always use two different provider APIs (Claude + Gemini) so the debate had two independent voices. Live session experience on 2026-04-15 surfaced two new facts that the original design did not account for:

1. The operator is trying to step further out of the loop — "the only thing I do is paste in Gemini and be adversarial". The Gemini-as-second-voice model still requires an operator-visible dependency on a second provider.
2. The feedback file `feedback_automated_skeptic_persona.md` (written the same day) codifies a durable adversarial persona + 12 overreach patterns that a bounded-critique subagent can load. This means the "skeptic seat" no longer needs to be a different *provider* — it can be a different *persona* on the same provider, as long as the persona file is loaded as the system prompt and the subagent has no access to the session history that created the draft being reviewed.

**The amendment: agent-mode flag.** The runner gains a new `--agent-mode` flag with two values:

- `claude_gemini` (default, existing behavior) — Claude as author seat, Gemini as skeptic seat. Two providers. Preserves the existing two-voice guarantee at the provider layer.
- `single_claude` (new) — Claude plays *both* seats. Author turns use the existing system prompt. Skeptic turns use a system prompt composed of `feedback_automated_skeptic_persona.md` (the full persona + 12 overreach patterns) concatenated with the existing debate-turn instructions. The runner still alternates agent names in the seam ("Claude-Author" and "Claude-Skeptic") so the convergence detector and the audit trail still see two distinct voices.

**What this preserves.** The two-voice invariant at the *debate layer* is preserved by using two different system prompts that produce structurally different outputs — author turns introduce claims, skeptic turns enumerate flags against the draft. The convergence rule (both most-recent turns must raise) still applies without modification. The append-turn primitive still sees alternating agent names. The cost ledger still attributes per-turn cost correctly.

**What this gives up.** Provider independence. In `single_claude` mode, a systematic Claude failure (hallucinated file:line, misread AST primitive, frustration-anchored diagnosis) will appear on both seats. The `feedback_automated_skeptic_persona.md` 12-pattern checklist is the structural mitigation — it forces the skeptic seat through a different cognitive surface than the author seat — but it is not equivalent to a different provider. The operator must decide which mode to use based on the draft's risk profile. High-stakes seams (scope changes to sealed pre-regs, paper claims, board promotions) should stay in `claude_gemini` mode. Routine debates on already-converged topics or pilot drafts can use `single_claude`.

**Slice A vs Slice B (new packet split).** The original seam scoped one bounded packet with six deliverables. That is too large to land in one disciplined session and the overreach-risk patterns in `feedback_automated_skeptic_persona.md` (frustration-anchored diagnosis, closure language audit) explicitly warn against doing so. The packet splits:

- **Slice A (now):** D2 write-scope, D5 context builder, D6 prompt enrichment, D7 agent-mode flag (new). These four unblock the "step out of the loop" capability — context injection + single-agent adversarial review. Slice A is the minimum that lets the operator delegate the adversarial seat.
- **Slice B (follow-on):** D1 shared transport helper, D3 seam-local cost ledger, D4 RunnerEscalation adapter. Pure refactor + debt payment. Does not unblock stepping-out. Safer to ship in a fresh session with the spec open.

**Slice A explicit non-goals.** Slice A does NOT touch the supervisor wrappers, does NOT extract a shared transport, does NOT change the existing inline cost check, does NOT add an escalation adapter. Any scope creep into those areas during Slice A implementation should be rejected and deferred to Slice B.

**Scope guard against agent-mode overreach.** The `single_claude` mode is NOT a claim that Claude-plus-persona is equivalent to Claude-plus-Gemini. It is a claim that for some class of review work (enumerated above), the structural isolation from the persona file is sufficient. The amendment explicitly does NOT propose removing `claude_gemini` mode, does NOT change its default status, and does NOT recommend `single_claude` for high-stakes reviews.

## Amendment — 2026-04-15 — D4 pulled forward into Slice A

After the first peer-review pass and a Gemini-Pro critique of the Slice A code, **D4 (executive-inbox gate-escalation adapter) was moved from Slice B into Slice A**. The stepping-out use case driving this packet — operator launches a sandbox 6/7/8/9 run, walks away, reads the result the next morning — needs a durable on-disk record when the runner exits on `COST_BUDGET` or `ESCALATED_CAP`. Without D4 those exits only print to stdout and the escalation evaporates with the terminal session, defeating the unattended-overnight workflow that the rest of Slice A is built to enable.

The Slice A implementation now writes `ztare_workspace/gates/pending/gate_<seam>.json` from both exit paths via `emit_gate_escalation` + `_maybe_escalate`. The adapter is **advisory only** — operator-pulled, no automatic supervisor wiring, no auto-routing into supervisor resolution — so it does not violate the "runner converges onto supervisor; supervisor does not move toward runner" constraint. The JSON record carries `seam_path`, `escalation_reason`, `equivalent_gate_reason`, `cycle_count`, `total_cost_usd`, `notes`, `timestamp_utc`, and `advisory: true`.

D1 (shared transport extraction) and D3 (cost ledger) **remain in Slice B**. The Gemini-Pro review argued D1 was a "fatal mistake" but that critique was rejected: slice 1 is explicitly runner-first extraction with the supervisor wrappers untouched, and partial extraction without dual adoption would create three places to update instead of two. D1 lands when both consumers can adopt the shared transport in the same packet.

