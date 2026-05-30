# GP-036 Findings Runner / Supervisor Convergence Spec

## Status

Active

## Scope

- converge the findings runner (`supervisor_findings_runner.py`) onto shared supervisor infrastructure
- add token-budgeted context injection so debate agents see cross-seam relationships, workspace artifacts, and board state
- add an `--agent-mode` flag: `claude_gemini` (existing two-provider mode) vs `single_claude` (new, Claude plays both seats using the automated-skeptic persona file)
- **packet split 2026-04-15:** originally scoped as one bounded packet. Now **Slice A** (active: D2, D4, D5, D6, D7, D8) and **Slice B** (deferred: D1, D3) to contain implementation risk per `feedback_automated_skeptic_persona.md` overreach patterns.
- **D8 added 2026-04-17:** `--reviewer-domains` flag for domain-specific skeptic lenses (shipped same day).
- **D4 pulled forward 2026-04-15 (post Gemini-Pro review):** the executive-inbox gate-escalation adapter was originally Slice B, but the stepping-out use case (operator runs sandbox 6/7/8/9 unattended overnight and reads results in the morning) requires a durable on-disk escalation record. Without D4, a `COST_BUDGET` or `ESCALATED_CAP` exit only emits a stdout note that disappears with the terminal session. D4 is now Slice A; the implementation writes `ztare_workspace/gates/pending/gate_<seam>.json` from both exit paths and is operator-pulled (no automatic supervisor wiring).

Does not cover:

- Tier 4 code-snippet injection (deferred behind flag)
- full agentic tool use for debate agents (MCP, function calling)
- `SeedPipelineType` registration for findings debates
- merging `check_convergence` with `prose_verifier` (different primitives, different exit contracts)
- supervisor state-machine changes
- auto-promotion (still human-gated)

## Decision

Extract a shared raw transport layer from the findings runner only (runner-first, slice 1). Converge write-scope, cost tracking, and escalation onto existing supervisor utilities. Add a separate token-budgeted context builder module (`findings_context.py`) that enriches debate prompts with related seams, workspace artifacts, and board rows — runner is the only consumer in slice 1. Supervisor wrapper migration is a future optional follow-on, not part of this packet.

## Problem

GP-031 shipped the findings runner with ~95% new code instead of the promised ~70% supervisor reuse:

- **Transport:** bespoke `call_claude()` (~80 lines) and `call_gemini()` (~80 lines) duplicate the API call + telemetry capture pattern from `supervisor_wrappers.py`
- **Write-scope:** runner writes to seam files with no scope check (supervisor has `write_scope_ok`)
- **Cost tracking:** inline `max_cost_usd` check instead of the supervisor's cost-ledger pattern
- **Escalation:** `RunnerStopReason` enum with print-and-exit instead of typed escalation compatible with `HumanGateReason`

Second problem: runner agents are context-starved. They receive only the seam text. GP-034 demonstrated the quality gap: hand-written turns (with full repo access) produced 3 new claims in 2 turns; runner-generated turns produced 0 new claims in 6 turns of "I agree."

Both problems share root cause: runner built as standalone system instead of supervisor layer.

## Why It Matters

- Duplication calcifies. Two parallel transport stacks means two places to update when API contracts change, two cost-tracking paths to reconcile, two write-scope policies to audit.
- Context-starved agents produce low-quality debate turns that waste cost budget without advancing the seam. The runner's mechanical convergence detection fires correctly (all sentinels match), but convergence on nothing is not useful convergence.
- The transport extraction creates the natural attachment point for context injection — the wrapper already assembles context payloads, so extending them is incremental.

## Constraints

From converged seam debate (GP-036 Turns 1-4):

1. **Runner converges onto supervisor; supervisor does not move toward runner.** Do not break the existing supervisor state machine.
2. **Narrow decoupling, not a shim, not a big-bang rewrite.** Extract raw provider-call + telemetry normalization into a shared transport helper. Leave packet/tool-use schema parsing in `supervisor_wrappers.py`. Leave debate-turn prompt shaping in `supervisor_findings_runner.py`.
3. **`RunnerStopReason` stays local.** Adapter record at the boundary that CAN translate to `HumanGateReason`, but no internal enum merge. Findings debate is not a supervisor program state.
4. **Seam-local cost ledger.** Keyed by seam path, not forced into `refinement_cost_usd`. Reuse `TurnUsageTelemetry` and `estimate_cost_usd` for individual-turn accounting, add a seam-scoped accumulator for budget enforcement.
5. **Injected context must carry provenance labels.** Every block gets a source header (`BOARD_ROW`, `RELATED_SEAM_EXCERPT`, `CITED_ARTIFACT_EXCERPT`) and its file path. Trust seam, not just quality seam.
6. **Adapter record is advisory only in slice 1.** No automatic gate creation, no automatic queueing into supervisor resolution. Typed, inspectable, available for later routing, but operator-pulled.
7. **No artifact discovery beyond explicit citations.** Runner may include cited artifacts and explicitly named related seams. No fuzzy workspace discovery or broad grep expansion.

## Options

### Option A — Thin shim onto existing wrapper functions

**Description**

Import and call `_call_anthropic_research_b_api` etc. with a minimal adapter.

**Pros**

- Fastest path, minimal code change

**Cons**

- Wrong abstraction boundary. Existing wrappers are bound to `HandoffStatus` and tool-use schemas — seed-side concepts that findings debate should not import.
- Shim hides the real problem (transport is not factored) instead of fixing it.

**Verdict**

Rejected (Codex Turn 2).

### Option B — Full supervisor wrapper rewrite

**Description**

Rewrite all of `supervisor_wrappers.py` to expose clean transport primitives.

**Pros**

- Cleanest long-term architecture

**Cons**

- Touches a live system mid-program
- Scope far exceeds what GP-036 needs
- Risk of regressions in supervisor state machine

**Verdict**

Rejected. Disproportionate to the problem.

### Option C — Narrow extraction + shared context builder

**Description**

Extract raw API call + telemetry normalization into a shared transport helper. Build a separate `findings_context.py` module for token-budgeted context assembly. Runner is the only consumer in slice 1.

**Pros**

- Pays the transport debt without touching supervisor state machine
- Context builder is reusable but not forced onto supervisor in slice 1
- Bounded scope, clear deliverables

**Cons**

- Two new modules (transport helper, context builder)
- Supervisor wrappers still contain their own call logic until they adopt the shared transport (optional future migration)

**Verdict**

Recommended.

## Recommendation

Option C. Originally six deliverables in one packet; **amended 2026-04-15** to split into Slice A (D2 + D5 + D6 + D7 + D8, active) and Slice B (D1 + D3 + D4, deferred to a follow-on session). Slice A lands the stepping-out capability; Slice B is pure refactor and debt payment. D8 (reviewer domain lenses) added and shipped 2026-04-17.

## Deliverable 7 (added 2026-04-15) — Agent-mode flag

New CLI flag `--agent-mode` with two values:

- `claude_gemini` (default): existing behavior. Alternates Claude and Gemini via their respective APIs.
- `single_claude`: Claude plays both seats. Author seat uses the existing system prompt. Skeptic seat uses a system prompt loaded from the operator's Claude Code memory directory (`feedback_automated_skeptic_persona.md`, full persona + 12-pattern overreach checklist) concatenated with a format-reconciliation note and the existing debate-turn instructions. The default path resolves under `Path.home() / ".claude" / "projects" / ...` so it tracks whichever operator account is running the runner; a `--skeptic-persona-path` flag overrides it for non-default layouts.

Runner-side implementation:

1. Extend `choose_next_agent` to return `"Claude-Author"` / `"Claude-Skeptic"` in `single_claude` mode. Existing Claude/Gemini return values are unchanged in `claude_gemini` mode.
2. Extend the dispatch so `"Claude-Author"` and `"Claude-Skeptic"` both route to `call_claude` with different system prompts.
3. Load the persona file at runner start in `single_claude` mode. If the file does not exist, abort with a clear error message — the mode requires the persona. Do not fall back silently.
4. The append-turn primitive records the agent name verbatim, so the seam shows `### Turn N — Claude-Skeptic (YYYY-MM-DD)`, preserving a clean audit trail.
5. The convergence rule is unchanged: both most-recent turns must raise their sentinel. Author-Skeptic alternation replaces Claude-Gemini alternation in `single_claude` mode.

**Why the persona file path is hardcoded.** The file is operator-managed and lives in the Claude Code memory directory. Hardcoding the path is honest about the dependency; making it configurable would invite drift between the persona the runner loads and the persona the operator's bounded-critique agents load. The two must stay identical or the structural isolation argument collapses.

**Explicit non-goal of D7.** `single_claude` mode is not equivalent to `claude_gemini` mode for high-stakes reviews. The spec does not recommend `single_claude` as the default and does not propose removing `claude_gemini` mode. Mode selection is an operator decision per seam.

## Deliverable 8 (added 2026-04-17) — Reviewer domain lenses

New CLI flag `--reviewer-domains` (comma-separated list of domain names) that injects domain-specific mental models into the skeptic's system prompt in `single_claude` mode.

Each domain name maps to `config/prompts/reviewer_domain_{name}.md`. Available domains as of 2026-04-17:

- `philosophy_of_science` — Popper, Lakatos, Duhem-Quine, observation vs oracle, Kolmogorov complexity
- `systems_ml` — BIC/AIC/MDL assumptions, oracle contamination analysis, GT vs observation dependence, flat fitness landscapes
- `symbolic_regression` — Pareto fronts, compositional search, exhaustive enumeration, active learning, extrapolation as falsification
- `munger_multidisciplinary` — inversion, man-with-a-hammer, incentive structures, biological analogs, lollapalooza effects

Implementation (shipped 2026-04-17):

1. `load_reviewer_domains(domains: list[str]) -> str` — reads matching files from `config/prompts/`, raises `FileNotFoundError` with available-domain listing if a name does not resolve.
2. `build_single_claude_system_prompt()` accepts optional `reviewer_domains_text` kwarg. When non-empty and role is `"skeptic"`, the domain text is injected between the role header and the format note under a `=== DOMAIN LENSES ===` header.
3. `--reviewer-domains` parsed as comma-separated string in `cmd_run_findings_debate`, split and passed through `run_findings_debate()`.
4. Domain lenses are loaded once at runner start and are NOT injected into the author prompt (author stays domain-neutral; domain expertise is an adversarial tool).

**Why skeptic-only.** The domain lenses are adversarial analysis tools: each one is a checklist of ways the Author's claims could be wrong from a specific disciplinary perspective. Injecting them into the Author would bias the Author toward the same framing and reduce the diversity of the debate.

**Explicit non-goal of D8.** This deliverable does not add per-domain author seats (one author per domain lens). If multi-domain authoring is needed, it is a separate capability.

## Implementation Sketch

### Deliverable 1: Shared transport helper

New module: `src/ztare/validator/llm_transport.py`

Runner-first extraction from `supervisor_findings_runner.py`. The supervisor wrappers also have an OpenAI transport path; slice 1 does NOT extract from `supervisor_wrappers.py` — only the runner's Anthropic and Google transports are in scope.

```python
def call_anthropic(
    *,
    model: str,
    system: str | None = None,
    messages: list[dict],
    max_tokens: int = 2000,
) -> tuple[str, TurnUsageTelemetry]:
    """Raw Anthropic API call + telemetry normalization."""

def call_google_genai(
    *,
    model: str,
    prompt: str,
    max_tokens: int | None = None,
) -> tuple[str, TurnUsageTelemetry]:
    """Raw Google GenAI API call + telemetry normalization."""
```

Both functions:
- Make the API call
- Capture `TurnUsageTelemetry` (input_tokens, output_tokens, cache_read, cache_write)
- Call `estimate_cost_usd` on the telemetry
- Return (response_text, telemetry)

After extraction:
- `supervisor_findings_runner.py` calls the shared transport and adds debate-turn shaping on top
- `supervisor_wrappers.py` migration to shared transport is a future optional follow-on, NOT part of this slice

### Deliverable 2: Write-scope enforcement

In `supervisor_findings_runner.py`, before any seam file write.

Note: `write_scope_ok` is a field on request/state objects in the live code, not a standalone callable. Introduce a new shared validator helper:

```python
# In llm_transport.py or a shared utility module
ALLOWED_FINDINGS_DIRS = [
    "research_areas/seams/",
    "research_areas/private/seams/",
]

def validate_findings_write_scope(path: Path, repo_root: Path) -> None:
    """Raise if path is outside allowed findings directories."""
    rel = str(path.relative_to(repo_root))
    if not any(rel.startswith(d) for d in ALLOWED_FINDINGS_DIRS):
        raise ValueError(f"Runner write-scope violation: {rel}")
```

Applied at every `append_turn` call site.

### Deliverable 3: Seam-local cost ledger

New sidecar file per seam: `<seam_dir>/.cost_ledger/<seam_slug>.jsonl`

Each line:
```json
{
    "timestamp_utc": "ISO 8601",
    "turn_index": 3,
    "agent": "claude",
    "model": "claude-sonnet-4-6",
    "telemetry": {"input_tokens": 12000, "output_tokens": 800, ...},
    "cost_usd": 0.042,
    "cumulative_cost_usd": 0.158
}
```

Budget enforcement: before each API call, read cumulative from ledger, check against `max_cost_usd`. Replaces inline check.

### Deliverable 4: RunnerStopReason adapter

New dataclass emitted when runner exits on `ESCALATED_CAP` or `COST_BUDGET`:

```python
@dataclass
class RunnerEscalation:
    """Advisory escalation record — inspectable, not auto-routed."""
    seam_path: str
    stop_reason: RunnerStopReason
    equivalent_gate_reason: str  # HumanGateReason value name, for reference
    cumulative_cost_usd: float
    turn_count: int
    timestamp_utc: str
```

Written to `<seam_dir>/.cost_ledger/<seam_slug>_escalation.json`. Operator reads it and decides routing. No automatic gate creation.

### Deliverable 5: Token-budgeted context builder

New module: `src/ztare/validator/findings_context.py`

```python
@dataclass
class ContextTier:
    label: str          # "BOARD_ROW", "RELATED_SEAM_EXCERPT", "CITED_ARTIFACT_EXCERPT"
    source_path: str    # file path
    content: str        # the injected text
    token_estimate: int # rough char/4 estimate

def build_findings_context(
    *,
    seam_path: Path,
    seam_text: str,
    token_budget: int = 30_000,
) -> list[ContextTier]:
    """Assemble tiered context for a findings debate turn.

    Tier 0: full seam text (mandatory, not counted against budget)
    Tier 1: current ZTARE board row for this seam (mandatory, small)
    Tier 2: related seam excerpts (bounded by budget)
    Tier 3: cited artifact excerpts (bounded by remaining budget)
    """
```

Tier assembly:
1. **Tier 1 — Board row:** Parse `ZTARE_BOARD.md` (private), find the row matching this seam's GP-ID, extract the full row.
2. **Tier 2 — Related seams:** Parse the seam's "Relationship to other seams" section. For each referenced seam path, read the first 200 lines. Deduct from budget.
3. **Tier 3 — Cited artifacts:** Only explicitly cited workspace artifacts (paths matching `projects/*/workspace/*` that appear verbatim in the seam text). No `src/ztare/*` code excerpts in slice 1 — code-snippet injection is behind Tier 4 flag. For each cited artifact, read first 100 lines. Deduct from remaining budget.

All tiers carry provenance headers in the formatted output:

```
--- BOARD_ROW (source: research_areas/private/ZTARE_BOARD.md) ---
| GP-034 | findings | n=1 | note | ...

--- RELATED_SEAM_EXCERPT (source: research_areas/private/seams/GP-035_mutator_missing_fit_primitive_seam.md) ---
[first 200 lines]

--- CITED_ARTIFACT_EXCERPT (source: projects/gp023_planck_sandbox_02/workspace/latent_distance.jsonl) ---
[first 100 lines]
```

### Deliverable 6: Runner prompt enrichment

Modify `build_turn_prompt()` in `supervisor_findings_runner.py`:

```python
def build_turn_prompt(*, seam_text: str, agent: str, debate_state: DebateState) -> str:
    context_tiers = build_findings_context(
        seam_path=debate_state.seam_path,
        seam_text=seam_text,
    )
    enriched_context = format_context_tiers(context_tiers)

    # Existing prompt construction + enriched_context appended
    ...
```

The context block is appended after the seam text and before the agent instructions, so the agent sees it as background material, not as the primary task.

## Open Questions

1. Should the shared transport helper live in `src/ztare/validator/` or `src/ztare/common/`? Validator is where both consumers live; common is architecturally cleaner. Default to validator for now.
2. Should the cost ledger sidecar live next to the seam file or in a central location? Next to seam keeps locality; central makes cross-seam cost queries easier. Default to next-to-seam.
3. Should `supervisor_wrappers.py` be migrated to use the shared transport in this slice, or only the runner? Default to runner-only in slice 1; supervisor migration is optional follow-on.
4. What is the right `token_budget` default for context injection? 30k tokens leaves room for the agent's own reasoning. Calibrate after first real use.

## Review Notes

### 2026-04-12 12:49:59 EDT — Codex

The packet shape is still basically right, but the current spec has three concrete contract bugs:

1. **Transport scope is internally inconsistent.**
   The spec says transport is extracted from both `supervisor_wrappers.py` and `supervisor_findings_runner.py`, but the implementation sketch only defines Anthropic and Google helpers. The wrappers also have an OpenAI transport path. So slice 1 must do one of:
   - include OpenAI in the shared transport layer
   - or narrow the spec honestly to runner-first extraction only

   Right now it claims broader convergence than the deliverables actually cover.

2. **`write_scope_ok` is not a callable utility.**
   The sketch imports it as if it were a function from `supervisor_state.py`, but in the live code it is a field carried on request/state objects, not a standalone validator. So Deliverable 2 is specified against the wrong interface. The spec should either:
   - introduce a real shared validator helper
   - or describe reuse of the existing request-validation pattern more abstractly

3. **Tier 3 reintroduces exactly the slice-1 behaviors the seam rejected.**
   The context builder currently says:
   - scan seam text for file paths matching `projects/*/workspace/*` or `src/ztare/*`
   - read first 100 lines

   That is too broad in two ways:
   - it quietly brings code-snippet injection back into slice 1
   - it drifts from “explicit citations only” toward a lightweight retrieval system

   Slice 1 should stay narrower:
   - cited artifact excerpts only
   - no `src/ztare/*` code excerpts unless an explicit code-snippet flag exists

So my judgment is:

- architecture: right
- packet scope: right
- implementation sketch: needs correction before coding

### 2026-04-12 13:13:41 EDT — Codex

Re-check after revision:

The three concrete contract bugs I flagged earlier are now materially fixed:

- transport scope is now honestly runner-first
- write-scope is specified via a real validator helper rather than the nonexistent `write_scope_ok` callable
- Tier 3 is narrowed to explicitly cited workspace artifacts, with no slice-1 `src/ztare/*` code injection

One smaller consistency issue remains:

1. **Top-level decision text still slightly overclaims convergence.**
   The `Decision` section still says “Extract a shared raw transport layer from both the supervisor wrappers and the findings runner,” while the implementation sketch correctly narrows slice 1 to runner extraction only and leaves wrapper migration as a future follow-on. The decision line should be tightened so the summary matches the packet.

Updated state:

- architecture: right
- packet: ready after one wording cleanup
- remaining issue: narrow the top-level decision text to runner-first extraction
