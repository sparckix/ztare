# GP-070 Meta-Supervisor Goal Orchestrator — Specification

**Status:** `active` — spec drafted from converged 27-constraint debate (2026-04-16)
**Origin seam:** `research_areas/private/seams/GP-070_meta_supervisor_goal_orchestrator_seam.md`
**Debate convergence:** Turn 14 (27 constraints, Author + Skeptic + Operator)

---

## 1. Architecture — OS / Config / App

Three layers with distinct change costs:

| Layer | Artifact | Change mechanism | Audit posture |
|-------|----------|-----------------|---------------|
| **OS** (Core) | Python code in `src/ztare/orchestration/` | seam → spec → program pipeline | Every change reviewed |
| **Config** | YAML goal-type files in `research_areas/private/goal_types/` | Operator writes in session | Validated by `validate_goal_config` CLI |
| **App** | Claude Code / Codex sessions | Ephemeral | Agent traces kept per-goal |

The OS layer is the only layer that writes to `state.json` and `transitions.jsonl`. The Config layer is parsed at goal-create time. The App layer (Claude Code / Codex / human) interacts with the OS layer exclusively through the three-command CLI interface.

## 2. Converged Constraints

### 2.1 Core State Machine (from B-debate, Turns 1–6)

**C-1.** Dispatch callables return `StageResult(success: bool, next_stage: Optional[str], gate_reason: Optional[str])`. The orchestrator applies all transitions. Callables that mutate `goal_state` directly are a bug.

**C-2.** Next-stage overrides in `StageResult` are validated against the module's declared stage DAG. The DAG must be acyclic with exactly one entry stage and at least one terminal stage. Validation happens at registration time (config parse), not at runtime. An override that would skip a gate stage is a hard runtime error.

**C-3.** All adapter/module callables (`dispatch`, `gate_artifacts`, `closure_criteria`) are pure with respect to `goal_state`. Only the orchestrator mutates state, through the `StageResult` → transition-write path.

**C-4.** `gate_artifacts` is a pure callable: `gate_artifacts(goal_state, stage) -> List[Path]`. Returns instance-specific artifact paths. The orchestrator hashes these at gate-escalation time and records hashes in `transitions.jsonl`. Empty list is valid (no artifact-backed gate).

**C-5.** A synthetic test module is committed as a permanent fixture at `src/ztare/orchestration/modules/test_module.py` (or config equivalent). It is the primary integration test harness for the orchestrator core.

**C-6.** Write-ahead log ordering: `transitions.jsonl` (append) is written before `state.json` (overwrite). Per-stage `idempotent: bool` flag on each dispatch entry. Restart protocol: if `transitions.jsonl` is ahead of `state.json`, check idempotency — re-dispatch if idempotent, escalate with `RESTART_NON_IDEMPOTENT_STAGE` if not.

**C-7.** Unconditional startup consistency check on every orchestrator invocation. `state.json` stage must equal the result of replaying `transitions.jsonl` from the beginning. If inconsistent: halt and escalate with `AUDIT_INTEGRITY_VIOLATION`. No automatic repair. Operator decides.

### 2.2 Config Layer (from Operator Reframe Turn 7 + Turns 8–10)

**C-8.** Three-layer architecture: OS (code) / Config (declarative) / App (Claude Code). The OS layer is agent-agnostic.

**C-9.** Goal types are declarative config files (YAML), not Python modules. A new goal type is a config file, not a code change.

**C-10.** Built-in adapter set per runner family (`findings_runner_adapter`, `autoresearch_adapter`, `program_autoloop_adapter`). Claude Code / Codex is the default dispatch target. Stages with no explicit `dispatch` line run in the agent runtime (Claude Code).

**C-11.** `context_insufficient` is NOT a first-class transition type. If it ever materializes in a live run, it is a gate request with reason string `CONTEXT_INSUFFICIENT` — handled by existing gate-escalation machinery. No new code path. (Task #64 remains deferred, not absorbed.)

**C-12.** Closure predicates are visible to the agent as structural checklists (e.g., "must have scope section, test plan, no unresolved TODOs"). Numeric scores, if any, are core-internal and not visible to the agent. Goodhart prevention via predicate design (compositional, substance-linked), not information hiding.

**C-13.** `validate_goal_config` CLI command — **Slice A deliverable**. Checks: (a) schema conformance against `schema_version`, (b) DAG acyclicity + single entry + at least one terminal, (c) all `dispatch` targets name registered adapters, (d) all `closure_predicate` names resolve in registered primitive whitelist, (e) all gate stages have non-empty `gate_description` fields. Runs offline, in CI, and at goal-create time.

**C-14.** Predicate composition grammar — **Slice A deliverable**. Primitives: `has_section(name)`, `no_unresolved_todos`, `min_words(n)`, `artifact_exists(path_template)`. Combinators: `all_of`, `any_of`, `not`. Covers `science_sandbox` and `kernel_hardening` configs. New primitives require a code PR.

**C-15.** LBC-5 narrowed: "Adding a goal type requires no code change if its closure predicates compose from registered primitives." New predicate primitives are engine-layer changes. This boundary is explicit and testable.

**C-16.** Config schema versioned with `schema_version: 1` field. Configs live in workspace (`research_areas/private/goal_types/`), not in engine source tree.

**C-17.** Slice A scope: core + config parser + validator CLI + predicate grammar + synthetic test module + `science_sandbox` config (manual-advance + runner-wired stages). Agent runtime deferred to Slice B.

**C-18.** Natural-language stage descriptions in config are shown to operator / Claude Code at stage start. Opaque to the core.

### 2.3 Claude Code as Agent Runtime (from Operator Turn 11 + Turns 12–14)

**C-19.** Agent runtime is Claude Code / Codex, not custom Python. The OS layer is agent-agnostic at the CLI boundary. `ztare goal advance` must work identically when called by Claude Code, Codex, a shell script, or a human.

**C-20.** Three-command CLI interface:
- `ztare goal advance <slug> --to <next_stage> [--artifacts <path>...]` — propose transition. Returns JSON: `{accepted, reason, current_stage, next_stage_description, gate_pending}`.
- `ztare goal resume <slug> [--acknowledge-drift]` — operator clears gate. Checks artifact-hash drift.
- `ztare goal status [<slug>]` — read-only query. Shows current stage, description, pending gates.

**C-21.** Slice B scope: hook wiring + runner post-completion callbacks. Budget: <200 lines new Python (review gate with justification requirement, not hard limit).

**C-22.** Git commit on transition is opt-in (`--git-commit` flag), not default. `transitions.jsonl` is the primary audit trail.

**C-23.** `ztare goal status` is a read-only query for agent situational awareness.

**C-24.** Per-goal filesystem lock (`<goal_dir>/.goal.lock`) using `fcntl.flock`. Both `advance` and `resume` acquire exclusive lock. Timeout: 30s, then error + suggest `ztare goal unlock <slug>` (checks PID, clears if dead).

**C-25.** Diff-on-resume: `ztare goal resume` re-hashes `gate_artifacts` paths and compares against hashes recorded at escalation time. If hashes differ: record `artifact_drift: true, drifted_files: [...]` in transition. Default: flag only. Modules can declare `strict_gate_mode: true` to upgrade drift to a block (requires `--acknowledge-drift` to proceed).

**C-26.** Session-start goal-state injection: `ztare goal advance` and `resume` auto-maintain a `## Active Goals` section in project CLAUDE.md. Updated as part of the transition write path. Claude Code reads this at session start. Section removed when no goals are active.

**C-27.** The <200 line Slice B budget is a review gate, not a hard constraint. If exceeded, the PR must justify against the "are we rebuilding an agent runtime?" test.

## 3. Slice A — Implementation Plan

### 3.1 Deliverables

| # | Deliverable | Description |
|---|------------|-------------|
| A1 | `GoalState` dataclass | `name`, `description`, `target_type`, `current_stage`, `created_at`, `owner`, `schema_version` |
| A2 | `GoalConfig` parser | Reads YAML goal-type config, validates against C-2 (DAG), C-13 (schema), C-14 (predicates) |
| A3 | State machine driver | Walks stage graph, dispatches via adapter callables, returns `StageResult`, writes transitions |
| A4 | Write-ahead log | `transitions.jsonl` append → `state.json` overwrite. Consistency check on startup (C-7) |
| A5 | Per-goal filesystem lock | `fcntl.flock` on `<goal_dir>/.goal.lock` (C-24) |
| A6 | `validate_goal_config` CLI | Offline config validation (C-13) |
| A7 | Predicate composition grammar | `all_of`, `any_of`, `not` + primitive vocabulary (C-14) |
| A8 | Gate escalation | Write gate JSON to `ztare_workspace/gates/pending/` (reuse GP-036 D4 pattern) |
| A9 | `ztare goal advance` command | Universal transition boundary (C-20). Manual-advance mode for operator |
| A10 | `ztare goal resume` command | Gate clearing with diff-on-resume (C-25) |
| A11 | `ztare goal status` command | Read-only query (C-23) |
| A12 | Synthetic test module | Permanent fixture, two stages, one gate, full cycle test (C-5) |
| A13 | `science_sandbox` config | First real goal-type config. Manual-advance + runner-wired stages |

### 3.2 What Slice A Does NOT Include

- Agent runtime (Claude Code wiring, hooks) — Slice B
- Multi-goal parallelism — future
- CLI polish beyond the three core commands — future
- `kernel_hardening` or `public_writeup` configs — Slice B
- Auto-commit to git on transition — Slice B (`--git-commit` flag)
- CLAUDE.md auto-maintenance (C-26) — Slice B

### 3.3 File Layout

```
src/ztare/orchestration/
├── __init__.py
├── core.py              # GoalState, StageResult, state machine driver
├── config_parser.py     # YAML → GoalConfig, DAG validation
├── predicates.py        # Composition grammar + primitive vocabulary
├── persistence.py       # Write-ahead log, consistency check, flock
├── gate_escalation.py   # Inbox JSON writer (reuse GP-036 D4)
├── cli.py               # ztare goal advance|resume|status
├── adapters/
│   ├── __init__.py
│   ├── findings_runner.py
│   ├── autoresearch.py
│   └── program_autoloop.py
└── modules/
    └── test_module.py   # Permanent synthetic test fixture
```

```
research_areas/private/goal_types/
├── science_sandbox.yaml
└── (future: kernel_hardening.yaml, public_writeup.yaml)
```

### 3.4 Execution Order

1. `core.py` + `persistence.py` — GoalState, StageResult, write-ahead log, consistency check, flock
2. `config_parser.py` + `predicates.py` — Config parsing, DAG validation, predicate grammar
3. `gate_escalation.py` — Inbox integration (reuse GP-036)
4. `cli.py` — Three commands wired to core
5. `modules/test_module.py` — Synthetic test, exercises full cycle
6. `science_sandbox.yaml` — First real config, validates against parser
7. Integration tests — Synthetic module full cycle, config validation CLI, restart/consistency

### 3.5 What the Operator Gets After Slice A

After Slice A ships, the operator can:
- Define a goal type in YAML and validate it offline (`validate_goal_config`)
- Create a goal against a validated config
- Advance through stages manually (`ztare goal advance`) or via runner-wired stages
- Hit gates that escalate to the executive inbox
- Resume from gates with artifact-drift detection
- See the full audit trail in `transitions.jsonl`
- Restart after a crash with automatic consistency check

The operator CANNOT expect: an agent that autonomously does work inside a stage and requests transitions. That is Slice B.

## 4. Slice B — Sketch (not for implementation yet)

Slice B wires the OS layer to Claude Code:
1. CLAUDE.md auto-maintenance of `## Active Goals` section (C-26)
2. Claude Code hook / instruction: "run `ztare goal advance` when stage work is complete"
3. Runner post-completion callbacks (~5 lines per runner)
4. `--git-commit` flag for transition-time auto-commits
5. `kernel_hardening.yaml` and `public_writeup.yaml` configs

Budget: <200 lines new Python (C-27).

## 5. Relationship to Existing Infrastructure

- **Reuses:** findings_runner (GP-036), program_autoloop, autoresearch_loop, executive inbox (GP-036 D4), leak-audit checklist
- **Extends:** `HumanGateReason` enum (module-provided reason strings via config)
- **Does not touch:** runner internals, supervisor program state, pre-reg seal primitive
- **Replaces:** nothing. Frozen v4/bridge meta runners stay frozen.

## 6. Pre-Implementation Gate

Before Slice A begins:
1. GP-036 findings runner has been used on one real seam in single_claude mode, end-to-end.
2. Operator confirms the converged seam is materially different from what Claude alone would produce.
3. This spec has been reviewed by the operator.

---

*Spec sealed: 2026-04-16. 27 constraints from 14-turn debate (Author + Skeptic + Operator).*
