# GP-107 Synthesis Charter-Renderer Seam

> **Seam metadata** · `seam_id:` GP-107 · `track:` engine · `status:` First slice shipped (2026-04-21). Live verification pending: · `last_updated:` 2026-05-17


## Problem Snapshot

Two bugs discovered in live qualitative policy project (seattle_tech_housing, ~40 iterations, champion score 90).

### Bug 1: Renderer sniff picks wrong renderer for qualitative policy projects

`sniff_context` uses `heuristic_project_type` which keyword-matches the project name and the first 3000 chars of thesis artifacts. For policy projects, the mutator rewrites `current_iteration.md` into a discriminator/mechanism paper with sections like "RIVAL HYPOTHESIS", triggering the `research_hypothesis` heuristic branch instead of `policy_scenario`. The LLM sniff then sees the mechanism-heavy prose and confirms `mechanism_brief`.

Result: `make synth` on a policy project with no explicit `RENDERER` argument silently produces the wrong output format.

**Fix:** Added `synthesis_renderer` field to the rubric JSON. `sniff_context` now reads this field via `best_iteration_rubric` before any heuristic or LLM sniff. Rubric field wins; sniff is only used when no rubric pin is present.

```python
# sniff_context, before heuristic:
rubric_name = best_iteration_rubric(project_dir)
if rubric_name:
    rubric_path = RUBRICS_DIR / f"{rubric_name}.json"
    rubric_data = json.loads(rubric_path.read_text())
    pinned = rubric_data.get("synthesis_renderer", "")
    if pinned:
        renderer_override = pinned
```

### Bug 2: Charter not injected into renderer, LLM cannot fulfill charter requirements

`render_artifact` passes the insight ledger, planning brief, and history summary to the renderer LLM. The project charter is never included. The charter specifies required output structure (civic externality ledger, distributional breakdown, concrete policy mechanism with dollar scale, irreversibility carve-out), without it, the renderer produces whatever the ledger distills, which is the discriminator protocol, not the ledger.

The charter is the contract. The renderer LLM cannot satisfy a contract it has never read.

**Fix:** `render_artifact` now injects `project_charter.md` into the prompt when the file exists:

```python
charter_path = project_dir / "project_charter.md"
if charter_path.exists():
    charter_text = charter_path.read_text(encoding="utf-8").strip()
    if charter_text:
        prompt_parts.append(
            "Project charter (required output structure, your report MUST fulfill every section):\n"
            + charter_text
        )
```

---

## Root Cause

The synthesis pipeline was designed for science/math projects where the champion thesis IS the output. For qualitative policy projects, the champion thesis is the epistemic scaffolding, the actual output is a different artifact (the ledger + policy recommendation) that must be constructed from all accumulated evidence per the charter, not distilled from the thesis prose.

The inversion: for science projects, synthesize = compress best thesis. For policy projects, synthesize = construct required deliverable from all evidence, using best thesis as scaffolding.

---

## Files Changed

- `src/ztare/synthesis/synthesize.py`, two changes:
  1. `sniff_context`: reads `synthesis_renderer` from rubric JSON before heuristic/LLM sniff
  2. `render_artifact`: injects `project_charter.md` into renderer prompt when present
- `rubrics/seattle_tech_housing.json`, added `"synthesis_renderer": "policy_essay"`

---

## Status

First slice shipped (2026-04-21). Live verification pending: re-run `make synth` on seattle_tech_housing and confirm `Report.policy_essay.md` now includes civic externality ledger, distributional breakdown, and concrete JumpStart mechanism with dollar scale.

### Bug 3: extract_ledger uses startup-oriented schema for all project types

`extract_ledger.md` has a `company`/`stage_assessment`/`PMF` schema. For policy projects this produces a JSON ledger with no credit/debit columns, no distributional breakdown, no irreversibility items, no policy mechanism fields. The renderer receives structurally wrong JSON and cannot produce the charter deliverables regardless of prompt quality.

**Fix:** `extract_ledger` now routes to `extract_ledger_{project_type}.md` if the file exists, falling back to the generic prompt. Created `config/prompts/extract_ledger_policy_scenario.md` with a policy-specific schema:
- `externality_ledger.credit_column[]` / `debit_column[]` / `net_balance`
- `distributional_breakdown[]` (named strata, demographics, neighborhoods)
- `irreversibility_items[]` (separate from dollar balance)
- `causal_attribution` (tech-attributable share + peer city comparison)
- `policy_proposal` (mechanism + annual_cost_low/high_usd + gap_addressed)

Charter also injected into the `extract_ledger` prompt so the LLM knows what content to look for in the debate logs.

---

## Files Changed

- `src/ztare/synthesis/synthesize.py`, three changes:
  1. `sniff_context`: reads `synthesis_renderer` from rubric JSON before heuristic/LLM sniff
  2. `render_artifact`: injects `project_charter.md` into renderer prompt when present
  3. `extract_ledger`: routes to `extract_ledger_{project_type}.md` if exists; injects charter
- `rubrics/seattle_tech_housing.json`, added `"synthesis_renderer": "policy_essay"`
- `config/prompts/extract_ledger_policy_scenario.md`, new policy-specific ledger schema
