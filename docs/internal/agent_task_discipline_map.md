# Agent Task Discipline Map

```
purpose:    procedural self-audit FOR agents; mirrors autoresearch_arch_map pattern
read_pre:   starting any non-trivial task (experiment, substrate build, paper edit, seam update)
check_post: before declaring task complete to principal
verifier:   scripts/validate_agent_task_discipline.py {pre,post,show}
format:     typed task → required_steps → completion_check; NO narrative
seam:       GP-164 (reflexive primitive 6)
discipline: if a step is marked required and not done, the verifier flags it; agent must fix or explain
source:     AGENTS.md §0a, §0b, §1-§7 (standing rules)
```

## TASK TYPE REGISTRY

Each task type has a set of REQUIRED steps derived from AGENTS.md.
The agent declares its task type at the start; the post-check
verifies all required steps were completed.

```
task_type: experiment_run
  description: Running a ZTARE experiment (make loop / make experiment-loop)
  required_pre:
    - hypothesis_registered: "H-row in hypothesis ledger BEFORE run starts (§0a)"
    - rubric_validated: "make validate-rubric passed (§0b)"
    - substrate_sealed: "make seal passed OR justification for skip"
    - evidence_validated: "scripts/validate_evidence.py passed"
  required_post:
    - e_row_written: "E-row in EXPERIMENT_TRACK_RECORD.md (§0b step 2)"
    - f_row_evaluated: "F-row written if result changes beliefs; explicit 'no F-row needed' if not (§0b step 3)"
    - ins_row_evaluated: "INS-row if paper-grade; explicit skip if not (§0b step 3b)"
    - thesis_updated: "best-iteration marker or null-result note (§0b step 4)"
    - workspace_frozen: "no post-hoc edits to workspace (§0b step 1)"
  anti_patterns:
    - "Declaring 'done' without E-row"
    - "Moving to next experiment before closure"
    - "Updating thesis.md with fabricated content on null result"

task_type: substrate_build
  description: Building a new project substrate (charter, evidence, test_model, gate_harness, rubric)
  required_pre:
    - runbook_consulted: "docs/guides/experiment_cookbook.md read"
    - division_ab_separation: "GT-aware artifacts separated from mutator-visible (§cookbook §1-§2)"
  required_post:
    - evidence_validated: "scripts/validate_evidence.py passed"
    - rubric_validated: "scripts/validate_rubric.py passed"
    - gate_harness_smoke: "gate_harness.py --run-smoke-test exit 0"
    - leak_sentinel: "make seal passed or leaks fixed"
    - triumvirate_aligned: "I_model signature matches across test_model.py, gate_harness.py, evidence.txt"
    - denylist_present: ".denylist file with domain terms"
  anti_patterns:
    - "Copying gate_harness.py as test_model.py (infinite recursion)"
    - "GT constants in evidence.txt code examples"
    - "cage_meta.class mismatching actual substrate type"
    - "Missing farther_tail_region null opt-out"

task_type: paper_edit
  description: Editing paper5 or paper6 (draft.md or main.tex)
  required_pre:
    - ledger_read: "docs/internal/paper5_epistemic_ledger.md read"
    - invariants_checked: "§5 invariants reviewed for the section being edited"
  required_post:
    - ledger_updated: "paper5_epistemic_ledger.md updated if structure changed"
    - both_formats: "both draft.md AND main.tex updated (not just one)"
    - invariants_preserved: "no invariant from §5 violated by the edit"
  anti_patterns:
    - "Editing draft.md without updating main.tex"
    - "Adding quantitative claims (invariant 5)"
    - "Using 'observed' instead of 'abductively proposed' (invariant 1)"
    - "Em-dashes or 'it wasn't X; it was Y' patterns (invariant 11)"

task_type: seam_update
  description: Creating or updating a seam file
  required_pre:
    - board_checked: "ZTARE_BOARD.md checked for existing row"
    - no_duplicate: "No existing seam covers the same finding"
  required_post:
    - board_row: "Row added/updated on ZTARE_BOARD.md"
    - visibility_correct: "Open seam → private; closed seam → public (feedback_seam_visibility.md)"
    - debate_log: "At least one debate turn documented"
  anti_patterns:
    - "Creating seam without board row"
    - "Duplicating content from an existing seam"

task_type: recording
  description: Recording findings in track record, insights ledger, or memory
  required_pre:
    - source_verified: "Claims verified against actual run artifacts (champion_eval_results.json etc)"
  required_post:
    - track_record_updated: "E-row and/or F-row in EXPERIMENT_TRACK_RECORD.md"
    - public_board_current: "ZTARE_BOARD.md not stale for the affected items"
    - memory_updated: "MEMORY.md updated if cross-session relevant"
  anti_patterns:
    - "Recording from memory instead of reading the artifact (feedback_recap_from_artifact_not_memory.md)"
    - "Approving quantitative claims without checking source (feedback_verify_before_approving.md)"

task_type: infrastructure
  description: Modifying apparatus code (autoresearch_loop, gates, fit primitive, etc.)
  required_pre:
    - arch_map_read: "autoresearch_loop_architectural_map.md read for affected region"
    - no_parallel_conflict: "No other agent editing same files (feedback_no_parallel_agents_same_file.md)"
  required_post:
    - arch_map_updated: "If region/line ranges changed, update the map"
    - tests_pass: "Existing tests still pass"
    - validate_arch_map: "scripts/validate_autoresearch_arch_map.py ex-post"
  anti_patterns:
    - "Editing autoresearch_loop.py without reading the map"
    - "Adding a rubric field without wiring it in the loop"
    - "Skipping hooks (--no-verify)"
```

## COMPRESSED SESSION LOG FORMAT

Each session, the agent maintains a compressed log at
`workspace/agent_session_log.jsonl` (gitignored). Each entry:

```json
{
  "task": "short description",
  "task_type": "experiment_run | substrate_build | paper_edit | seam_update | recording | infrastructure",
  "started": "ISO timestamp",
  "agents_md_sections": ["0b", "4a"],
  "files_touched": ["projects/gp163d/...", "rubrics/..."],
  "pre_checks": {"rubric_validated": true, "evidence_validated": true},
  "post_checks": {"e_row_written": false, "f_row_evaluated": false},
  "status": "in_progress | completed | blocked",
  "notes": "any deviations or skipped steps with justification"
}
```

The validator reads this log and flags incomplete post_checks.

## RELATIONSHIP TO EXISTING PRIMITIVES

This is Reflexive Primitive 6: Procedural Self-Audit.

| Existing Primitive | What it inspects | This primitive |
|---|---|---|
| P1: Token-Optimized Self-Modeling | Agent's understanding of code | Agent's understanding of its own work discipline |
| P2: Inception Pattern | Agent's environment model | Agent's compliance with AGENTS.md |
| P5: Reflexive Orchestration | Goal config friction | Task closure friction |

The move: apply Compress (Leg 2) to the agent's own procedural
compliance. The compressed log is the self-model; the validator is
the gate; AGENTS.md is the specification.

---

*Created: 2026-04-26. Update whenever a new task type is added or AGENTS.md rules change.*
