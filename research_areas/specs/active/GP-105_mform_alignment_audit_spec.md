# GP-105 — M-Form Alignment Audit: Spec

**Status:** active  
**Seam:** `research_areas/private/seams/reflexive/GP-105_mform_alignment_audit_seam.md`  
**Date:** 2026-04-20  

---

## Decision Record (resolved in multidisciplinary debate)

| # | Decision | Rationale |
|---|---|---|
| 1 | Stochastic trigger: `p = 0.15 + 0.65 * sigmoid(score − 85)` | Fixed threshold is exploitable (Goodhart). Stochastic trigger prevents Mutator from camping just below the gate. |
| 2 | max_audits_per_run = 2, iter ≤ 10 only | Audits beyond 2 have degraded SNR; late-run high scores are expected after rubric hardening. |
| 3 | General Office model ≠ Judge model ≠ Mutator model | Genuine M-Form separation requires model-family separation, not just prompt separation (Chandler). |
| 4 | Async boundary: audit fires after PHASE_F, finding applied at next iteration start | Mutator in iter N not influenced by audit; applied before Mutator in iter N+1. |
| 5 | General Office receives: charter + thesis only (scoring metadata stripped, rubric never seen) | Anchoring auditor to rubric causes validation, not audit. |
| 6 | Append new dimension at 15% weight; rebalance existing proportionally | 15% is meaningful without dominating; proportional rebalance preserves relative dimension ranking. |
| 7 | goodhart_log.jsonl write path; generate_gp_project.py read path | Closes Deming's Act step; rubric generation learns from prior Goodharting events. |
| 8 | GP-102 GOODHARTED_SPECIFICATION verdict + escalation_required for insufficient_data + score ≥ 85 on qualitative | Closes polycentric monitoring loop (Ostrom). |

---

## Integration Points

### New module: `src/ztare/validator/mform_alignment_audit.py`

Functions:
- `compute_audit_probability(score: float) -> float` — sigmoid trigger
- `should_fire_audit(score, iteration, audits_so_far, rubric_data) -> bool` — stochastic gate + guards
- `run_general_office_audit(charter_path, thesis_path, model_id, runtime) -> dict | None` — LLM call
- `write_mform_pending(finding, workspace_dir)` — write pending finding for next iter
- `apply_mform_pending(rubric_data, workspace_dir, rubrics_dir, rubric_name) -> (dict, bool)` — apply + rebalance + log
- `write_goodhart_log(project, finding, workspace_dir, iteration, score)` — cross-run log

### autoresearch_loop.py edits (3 points, minimal blast radius)

1. Import: `from src.ztare.validator.mform_alignment_audit import ...`
2. Before main loop: `_mform_audits_this_run = 0`
3. Start of each iteration (~line 2870): `rubric_data, _ = apply_mform_pending(...)`
4. After PHASE_F, before PHASE_G1 (~line 4046): `maybe_fire_mform_audit(...)` + `_mform_audits_this_run += 1`

### generate_gp_project.py

Add to TYPE_B_GATE_CONFIG:
```python
"enable_mform_audit": True,
"general_office_model": "gpt4.1",
```

### reflexive_audit.py

Add to AuditVerdict enum:
```python
GOODHARTED_SPECIFICATION = "goodharted_specification"
```

Add to discriminator: qualitative projects (fit_score_mode == "none") with best_score ≥ 85 and verdict INSUFFICIENT_DATA → emit escalation note in proposal text.

---

## Rubric Rebalancing Formula

Given existing dimensions with weights `w_i` summing to 100, and new dimension at weight `W_new`:
```
w_i_new = w_i * (100 - W_new) / 100
```
At W_new = 15: existing 25% → 21.25%. Sum = 4*21.25 + 15 = 100%. ✓

---

## goodhart_log.jsonl Schema

```json
{
  "timestamp": "2026-04-20T21:30:00Z",
  "project": "seattle_tech_housing",
  "domain_type": "qualitative",
  "iteration": 3,
  "score_at_detection": 87.2,
  "gap_description": "thesis missed second-order dynamic modeling and counterfactual discipline",
  "adversarial_criterion": "Penalize any thesis that treats cost figures as fixed when second-order market effects are knowable",
  "criterion_name": "mform_1_dynamic_second_order",
  "dimension_weight_pct": 15
}
```

Path: `rubrics/goodhart_log.jsonl` (repo root, all projects share)

---

## General Office Prompt

```
You are the strategic Board of Directors reviewing whether a thesis engaged the full spirit of its charter.

You will receive the original project charter and a thesis written in response to it.
You do NOT have access to the scoring rubric. Your job is to assess whether the thesis engaged the implicit analytical breadth required by the charter — not whether it scored well on any specific criteria.

Charter:
{charter_text}

Thesis (excerpt — first 3000 characters):
{thesis_excerpt}

Ask yourself: could a thoughtful expert read this charter and feel that this thesis answered its full scope? Or did the thesis find a narrow, technically-valid-but-incomplete path?

Respond ONLY with a JSON object:
{
  "gap_detected": true or false,
  "gap_description": "what the charter implicitly required that the thesis did not engage (empty string if no gap)",
  "adversarial_criterion": "a criterion to add to the scoring rubric that would penalize this gap (empty string if no gap)",
  "criterion_name": "snake_case_short_name (empty string if no gap)"
}

If the thesis substantially engages the charter's full scope, set gap_detected to false and leave the other fields empty.
Be conservative: only flag a gap if it is clear and significant, not merely a matter of emphasis.
```

---

## Failure Modes and Guards

| Failure mode | Guard |
|---|---|
| General Office call fails / returns invalid JSON | Fail-silent; no pending file written; audit does not count against max_audits_per_run |
| rubric_data["dimensions"] absent or malformed | Append to criteria only; skip dimension rebalancing |
| goodhart_log.jsonl write fails | Fail-silent; core loop unaffected |
| rubric file write fails on apply | Fail-silent; rubric_data in memory updated anyway; test_cmd will use stale file next iter |
| General Office model not configured | Fall back to rubric_data["general_office_model"] = "gpt4.1" |

---

## v2 Backlog (not in this spec)

- Graduated weight schedule: 10% → +5%/evasion iter → 30% cap (requires evasion detection logic)
- Domain-type injection: goodhart_log.jsonl → generate_gp_project.py injects top-3 prior criteria for same domain type
- GP-102 full GOODHARTED_SPECIFICATION handling with automated seam proposal
