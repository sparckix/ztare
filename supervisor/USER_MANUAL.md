# Supervisor User Manual

This is the practical manual for using the supervisor instead of typing `ur turn`.

## Active Run Location

Use in-repo active runs under:

- `supervisor/active_runs/<run_id>/`

Reason:

- wrapper sandboxes can reliably read and write these files
- `/tmp/` staging can trigger permission-denied failures for otherwise valid turns

These active-run files are ignored by git and are not part of the permanent tracked record.

## What The Supervisor Owns

The supervisor owns:

- routing
- state transitions
- revision checks
- scope checks
- human gates

Agents do **not** write supervisor state directly.

## Control Artifacts

- `supervisor/program_registry.json`
- `supervisor/program_genesis/`
- `supervisor/program_manifests/`
- `supervisor/model_pricing.json`
- `research_areas/program_plans/`
- `research_areas/proposal_plans/`
- `research_areas/seed_registry.json`
- `research_areas/seeds/**/*.md`
- `research_areas/debates/**/*.md`

## Three Layers

1. seed layer
   - human-authored strategic intent
2. program layer
   - accepted routable programs with genesis and debate
3. supervisor layer
   - typed routing and commit control

## RACI

`A = Accountable`, `R = Responsible`, `C = Consulted`, `I = Informed`

| Activity | Human | Spec Agent | Implementation Agent | Verifier | Supervisor |
|---|---|---|---|---|---|
| Select or revise seed specs in `research_areas/seeds/**/*.md` / decide whether a new program should exist | A/R | C | C | I | I |
| Write genesis and add program to registry | A/R | C | C | I | I |
| A1/A2: append the next bounded debate turn in `research_areas/debates/**` and lock the next spec | C | R | I | I | A |
| B: write approved draft / implementation artifacts in `research_areas/drafts/**` or declared implementation paths | I | C | R | I | A |
| C: verify deterministic conformance, fail, or route to human gate | I | I | I | R | A |
| D: resolve human gate, approve freeze, or redirect work | A/R | C | C | C | I |
| Commit state transition and archive the staged request | I | I | I | I | A/R |

Artifact intent stays separated:

- `research_areas/seeds/**` = strategic seed layer
- `research_areas/debates/**` = bounded tactical argument history
- `research_areas/specs/**` = deterministic contracts
- `research_areas/drafts/**` = generated research/manuscript artifacts

Do not let debate or draft outputs mutate seed specs.

## How A New Program Is Born

1. write or select a seed spec under `research_areas/seeds/`
2. ensure it is represented in `research_areas/seed_registry.json`
3. decide to open a real program
4. write `supervisor/program_genesis/<program_id>.json`
5. add the program to `supervisor/program_registry.json`
6. initialize supervisor state for that program

Do **not** add a program directly from a folder idea or a chat mention.

## How To Run A Program

### 1. Initialize

```bash
python -m src.ztare.validator.supervisor_loop init \
  --status-path supervisor/active_runs/<run>/status.json \
  --run-id <run_id> \
  --program <program_id> \
  --target <target_name>
```

### 2. Inspect Current State

```bash
python -m src.ztare.validator.supervisor_loop show \
  --status-path supervisor/active_runs/<run>/status.json
```

### 2a. Ask "What Next?"

```bash
python -m src.ztare.validator.supervisor_what_next \
  --status-path supervisor/active_runs/<run>/status.json
```

Use this when you want the next bounded packet without rereading the entire debate file. If a manifest exists, this command surfaces the next pending packet or tells you the program is ready for promotion/closure.

### 2b. Draft Or Refresh A Program Backlog

```bash
python -m src.ztare.validator.supervisor_backlog \
  --program <program_id>
```

Optional execution:

```bash
python -m src.ztare.validator.supervisor_backlog \
  --program <program_id> \
  --execute
```

This does three things:

- reads the seed, genesis, debate file, and current manifest
- refreshes `research_areas/program_plans/<program_id>.md`
- optionally asks the `Spec Agent` to revise `supervisor/program_manifests/<program_id>.json` and append a planning receipt turn to the debate file

Use this when the backlog itself is unclear. Use `supervisor-what-next` when the backlog already exists and you just need the next packet.

### 2d. Standalone Prose Verification

There is now a deterministic prose-spec checker for research artifacts:

- `src/ztare/validator/prose_spec.py`
- `src/ztare/validator/prose_verifier.py`
- `src/ztare/validator/document_assembler.py`

The verifier only checks deterministic conformance:

- required headers
- required subsections
- required citations
- required phrases
- banned phrases
- word-count bounds

Run the fixture suite with:

```bash
make benchmark-prose-verifier
```

Current runtime boundary:

- research programs can prefill `spec_path`, draft markdown artifact paths, and a deterministic prose verifier command
- research `A2` must emit the canonical `ProseSpec` schema with exact phrase/citation strings
- research `B` must include those exact strings verbatim when the spec requires them
- `State C` remains pure Python
- only reversible canonicalization such as newline and trailing-space normalization is allowed in `C`
- deterministic document assembly belongs after verified fragment packets, not inside an LLM turn
- cross-model `A1/A2` debate is still not enforced by the runtime
- optional ZTARE pressure-testing of a locked section spec remains a manual operator step

### 2c. Draft A Proposal From A Seed

```bash
python -m src.ztare.validator.supervisor_proposal \
  --seed-id <seed_id> \
  --program-id <proposed_program_id>
```

Optional execution:

```bash
python -m src.ztare.validator.supervisor_proposal \
  --seed-id <seed_id> \
  --program-id <proposed_program_id> \
  --execute
```

This is pre-registry planning.

Outputs:
- `supervisor/proposed_manifests/<program_id>.json`
- `research_areas/proposal_plans/<program_id>.md`
- `research_areas/debates/planning/<program_id>.md`

Use this when you have a seed but no accepted program yet.

Important:
- it does **not** create a routable program
- it does **not** edit `program_registry.json`
- it does **not** write genesis
- promotion from proposal to real program is still human-gated

### 3. Emit The Next Staging Request

```bash
python -m src.ztare.validator.supervisor_loop emit-staging \
  --status-path supervisor/active_runs/<run>/status.json \
  --staging-dir supervisor/active_runs/<run>/staging
```

This replaces asking “whose turn is it?”.

If a manifest exists for the active program, `show`, `emit-staging`, and `launch-staging` also surface the next pending packet so the `Spec Agent` does not have to invent the backlog.

### 4. Have The Actor Fill The Staged Request

The actor edits the staged JSON request only.

It does **not** edit supervisor state directly.

### 5. Commit Through The Supervisor

```bash
python -m src.ztare.validator.supervisor_loop commit-staging \
  --status-path supervisor/active_runs/<run>/status.json \
  --events-path supervisor/active_runs/<run>/events.jsonl \
  --staging-dir supervisor/active_runs/<run>/staging \
  --staging-path supervisor/active_runs/<run>/staging/<actor_state>.json
```

The supervisor then:

- validates revision
- validates actor ownership
- validates declared scope
- applies the transition or fails closed

On a successful verifier commit (`C -> A1` or `C -> D`), the supervisor now also advances the active manifest:

- marks the just-verified packet `complete`
- unblocks dependent `blocked` packets whose dependencies are now complete
- refreshes `research_areas/program_plans/<program_id>.md`

### 6. Optional: Launch Without Copy/Paste

```bash
python -m src.ztare.validator.supervisor_loop launch-staging \
  --status-path supervisor/active_runs/<run>/status.json \
  --staging-dir supervisor/active_runs/<run>/staging
```

This emits staging and prepares the next actor invocation automatically.

- for `Spec Agent` / `Implementation Agent`, the wrapper writes a prompt file and, when run with `--execute`, invokes the configured CLI
- for `Verifier`, the wrapper can run the recorded verification command locally and prefill the verifier request
- when usage telemetry is available from the CLI output, the wrapper writes:
  - `staging/launch/<actor>_<state>_usage.json`
  - `turn_usage` into the staged request JSON
- wrapper execution now also records:
  - `modified_repo_paths`
  - `unauthorized_repo_paths`
  - `write_scope_ok`
- `B` and `C` commits now append compact receipt turns into the debate file so implementation / verifier work is visible in the human-readable log

If an agent writes outside its allowed repo artifact set, the later `commit-staging` fails closed with:

- `human_gate_reason = unauthorized_artifact_write`

The supervisor still does **not** commit automatically. Commit remains a separate explicit step.

### Optional: Attended Autoloop

If you want to remove repetitive `launch` / `commit` command entry without giving up the manual gate model, use the attended autoloop:

```bash
python -m src.ztare.validator.supervisor_attended_autoloop \
  --status-path /tmp/<run>/status.json \
  --events-path /tmp/<run>/events.jsonl \
  --staging-dir /tmp/<run>/staging \
  --execute \
  --auto-commit
```

Properties:

- it is a consumer of the existing supervisor CLI/kernel, not a change to the state machine
- `D` is always manual: the loop stops before any transition that would land in `D`
- unauthorized writes, fail-closed previews, non-zero launch exits, and budget / duration caps stop the loop
- each cycle appends a readable summary record under:
  - `staging/autoloop/cycle_summaries.jsonl`

If `--auto-commit` is omitted, the autoloop runs one launch cycle and prints the exact next manual `make supervisor-commit ...` command.

### Optional: Read-Only Founder Report

```bash
python -m src.ztare.validator.supervisor_report \
  --status-path /tmp/<run>/status.json \
  --events-path /tmp/<run>/events.jsonl
```

Optional outputs:

```bash
python -m src.ztare.validator.supervisor_report \
  --status-path /tmp/<run>/status.json \
  --events-path /tmp/<run>/events.jsonl \
  --output-path /tmp/<run>/founder_memo.md \
  --json-out /tmp/<run>/founder_memo.json
```

This is read-only. It does not advance state. It renders:

- current run / gate / next action
- manifest progress
- recent transition receipts
- recorded costs
- artifact pointers

### Resolve A Human Gate

To close, freeze, or resume a run parked at `D`:

```bash
python -m src.ztare.validator.supervisor_gate_resolution \
  --status-path /tmp/<run>/status.json \
  --events-path /tmp/<run>/events.jsonl \
  --decision close
```

Other decisions:

- `--decision freeze`
- `--decision resume`

Optional note:

```bash
python -m src.ztare.validator.supervisor_gate_resolution \
  --status-path /tmp/<run>/status.json \
  --events-path /tmp/<run>/events.jsonl \
  --decision close \
  --note "Promotion accepted. Program closed."
```

Behavior:

- `close` / `freeze`
  - append a human turn to the debate file
  - mark the current manifest packet complete if needed
  - refresh the program plan markdown
  - update `supervisor/program_registry.json`
- `resume`
  - append a human turn
  - route `D -> A1`
  - update the registry entry back to `active`

### Optional: Budget-Aware Refinement

The supervisor now supports an optional refinement budget ledger.

- default: disabled
- why disabled: `supervisor/model_pricing.json` ships with `"enabled": false`, so no fake cost estimates are enforced
- live default breaker remains:
  - max `2` refinement rounds

To enable a real refinement budget later:

1. populate `supervisor/model_pricing.json`
2. initialize with `--max-refinement-cost-usd <usd>`

Example:

```bash
python -m src.ztare.validator.supervisor_loop init \
  --status-path /tmp/<run>/status.json \
  --run-id <run_id> \
  --program <program_id> \
  --target <target_name> \
  --max-refinement-cost-usd 1.50
```

### Optional: Exit Gate On Verifier Pass

If an `A2` packet should stop at human review when verification passes, set:

- `gate_on_verifier_pass: true`

in the staged `A2` request.

Effect:
- `B -> C` runs normally
- if `C` passes, supervisor routes to `D`
- `human_gate_reason = contract_promotion`

Use this for terminal packets that should pause instead of automatically returning to `A1`.

## Findings-Debate Runner (Pre-Seed Layer)

The findings-debate runner automates the "ur turn" loop for findings-track seams. It replaces the manual operator cycle of copy-pasting debate turns between Claude and Gemini.

### Lifecycle: When To Use What

The supervisor has two layers with a hard boundary between them:

```
  FINDINGS RUNNER (pre-seed)              M-FORM SUPERVISOR (post-seed)
  ──────────────────────────              ────────────────────────────
  1. Operator creates a seam file         4. promote_findings_seam() writes
     with a ## Debate Log header             seed_registry.json entry
                                          5. Write program_genesis/<id>.json
  2. Runner debates the seam:             6. Add to program_registry.json
     Claude + Gemini alternate            7. Supervisor executes:
     turns → sentinel convergence            A1 → A2 → B → C → D
                                             (all existing infrastructure)
  3. Runner exits:
     CONVERGED / ESCALATED_CAP /
     MAX_CYCLES / COST_BUDGET
        ↓
     Operator reviews result
        ↓
     If converged: promote (step 4)
     If not: re-run or close
```

**The promotion edge is the type boundary.** Before promotion, the object is a debated finding (a seam file). After promotion, it becomes a seed in the supervisor's registry and the existing A1/A2/B/C/D machinery takes over.

**Decision guide:**

| You want to... | Use |
|---|---|
| Debate a new runtime-discovered finding to convergence | Findings runner |
| Execute a converged finding as an implementation program | M-form supervisor (after promotion) |
| Draft/revise a paper section or manuscript | M-form supervisor (research pipeline) |
| Build a kernel feature from a spec | M-form supervisor (build pipeline) |

### Architecture Note: Shared Utilities and Duplication

The findings runner currently shares only two utilities with the supervisor stack:

- `TurnUsageTelemetry` (token count / cost tracking dataclass)
- `estimate_cost_usd` (pricing lookup)

It does **not** use the supervisor's state machine (`SupervisorState` A1/A2/B/C/D), actor routing (`actor_for_pipeline_state`), wrapper transport (`_call_anthropic_research_b_api`), prose verifier, write-scope guard, human gates, refinement caps, or manifest/packet sequencing. Instead it has its own LLM call functions, its own state enum (`DebateStatus`), and its own stop-condition logic.

This duplication was a deliberate first-slice decision (GP-031 Turn 2: keep findings-debate outside the seed registry so the object boundary is preserved). The convergence detector is genuinely different from `prose_verifier` (semantic sentinel vs. structural conformance) and is not duplication. The LLM transport and state tracking are duplication that should converge. The natural path is to decouple the wrapper transport from `HandoffStatus` so the runner can reuse it without pretending the seam is a seed.

### Commands

**Run a findings debate:**

```bash
python -m src.ztare.validator.supervisor_findings_runner \
  --seam-path research_areas/private/seams/<SEAM_FILE>.md \
  --max-cycles 6 \
  --max-cost-usd 0.50 \
  --execute
```

Flags:

- `--seam-path`: path to a seam file with a `## Debate Log` header (required)
- `--max-cycles`: per-run cap on appended turns (default 6; hard cap is 12 total in the debate primitive)
- `--max-cost-usd`: per-run dollar budget (default $0.50; checked pre-call so the limit is never breached)
- `--claude-model`: default `claude-sonnet-4-6`
- `--gemini-model`: default `gemini-2.5-flash`
- `--execute`: required for real API calls; without it, dry-run only
- `--today`: override today's date in ISO form (for the turn header)

Without `--execute`, the runner parses the seam, checks convergence state, and reports what it would do. Useful for verifying the seam is parseable before spending tokens.

**Promote a converged finding to a seed:**

```python
from src.ztare.validator.supervisor_findings_promotion import promote_findings_seam

promote_findings_seam(
    seam_path="research_areas/private/seams/GP-034_..._seam.md",
    spec_path="research_areas/specs/active/GP-034_..._spec.md",
    seed_id="gp034_dual_channel_loop_control",
    pipeline_type="build",
    # allow_unconverged=True  # only if operator overrides an ESCALATED_CAP
)
```

Five fail-closed guardrails: seam must exist, debate must be CONVERGED (unless `allow_unconverged=True`), spec must exist on disk, seed_id must not already be in the registry, closed-on-arrival promotions are refused.

After promotion, the seed is in `seed_registry.json` and the standard supervisor workflow takes over (genesis → registry → A1/A2/B/C/D).

### Debate Agents

The runner alternates **Claude** (Anthropic Messages API) and **Gemini** (Google GenAI SDK). Each agent reads the full seam text and contributes one debate turn, ending with:

- `SENTINEL_DECISION: raise`: no new load-bearing claim; ready to converge from this agent's side
- `SENTINEL_DECISION: hold`: still introducing or rebutting a load-bearing claim

Convergence requires both agents to raise in consecutive turns with a minimum of 2 turns per agent. At the hard cap (12 total turns), the runner exits with `ESCALATED_CAP` and the operator decides.

Codex (OpenAI CLI) is intentionally not a runner participant. Findings debates exceed Codex's input-token wall. Codex's role is operator-level review at convergence/promotion time.

### Validation

```bash
make benchmark-supervisor-findings-debate
make benchmark-supervisor-findings-runner
```

## Current State

Active work is tracked on the ZTARE Board:
- Public: `research_areas/ZTARE_BOARD.md`
- Full detail: `research_areas/private/ZTARE_BOARD.md`

Seeds in the seed layer stay there until a genesis file is written and a human accepts opening them.

## Start A Program

```bash
python -m src.ztare.validator.supervisor_loop init \
  --status-path supervisor/active_runs/<run>/status.json \
  --run-id <run_id> \
  --program <program_id> \
  --target <target_name>

python -m src.ztare.validator.supervisor_loop emit-staging \
  --status-path supervisor/active_runs/<run>/status.json \
  --staging-dir supervisor/active_runs/<run>/staging

python -m src.ztare.validator.supervisor_loop launch-staging \
  --status-path supervisor/active_runs/<run>/status.json \
  --staging-dir supervisor/active_runs/<run>/staging
```

After the actor fills the emitted staging request:

```bash
python -m src.ztare.validator.supervisor_loop commit-staging \
  --status-path supervisor/active_runs/<run>/status.json \
  --events-path supervisor/active_runs/<run>/events.jsonl \
  --staging-dir supervisor/active_runs/<run>/staging \
  --staging-path supervisor/active_runs/<run>/staging/<actor_state>.json
```

## Validation Commands

```bash
make benchmark-supervisor
make benchmark-supervisor-registry
make benchmark-supervisor-seed-registry
make benchmark-supervisor-genesis
make benchmark-supervisor-staging
make benchmark-supervisor-wrappers
make benchmark-supervisor-refinement
make benchmark-supervisor-usage
make benchmark-supervisor-findings-debate
make benchmark-supervisor-findings-runner
```

## Rules

- do not scan `projects/` to infer the portfolio
- do not let agents mutate seed specs
- do not open a program without genesis
- do not reopen closed/frozen programs without a human gate
- do not treat the supervisor as a portfolio manager
- keep `A1 -> A2 -> B -> C` as the default path
- if bounded spec refinement is used, cap `A2 -> A1` at `2` rounds before forcing `B` or `D`
- budget-aware refinement is optional and remains off until pricing + telemetry are configured
- exact pricing mode means unknown-model runs stay financially silent rather than inventing cost
- findings-debate runner is for pre-seed work only; do not route it through the seed registry
- promotion from finding to seed is always human-gated; no auto-promotion
