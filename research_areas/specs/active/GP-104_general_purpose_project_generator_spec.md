# GP-104 — General Purpose Project Generator Spec

## Status

`active` — implementation pending

## Problem

Every qualitative (non-numerical) ZTARE project requires three gate opt-out keys that aren't obvious and whose absence causes hard fails. The current workflow (`mkdir`, `cp rubrics/template_thesis.json`) produces no opt-outs and no enforced structure. Three projects hit this in one session (2026-04-20).

## Solution

A `generate-gp` Makefile target backed by `src/ztare/scaffold/generate_gp_project.py` that:
1. Creates the project folder scaffold
2. Uses LLM to draft a rubric persona and criteria from the operator's brief
3. Pre-fills all Type B gate opt-outs in the generated rubric
4. Outputs a `make seal`-ready project

Analogous to `make generate-substrate` for science experiments.

---

## Interface

```bash
make generate-gp \
    PROJECT=seattle_v2 \
    BRIEF="Analyze whether Seattle tech firms should face mandatory housing cost internalization" \
    JUDGE_MODEL=gpt4.1
```

**Required parameters:**
- `PROJECT`: slug (will be used as project directory name and rubric filename)
- `BRIEF`: one-paragraph plain-English description of the thesis question

**Optional parameters:**
- `JUDGE_MODEL`: LLM to call for persona/criteria drafting (default: `gpt4.1`)
- `RUBRIC_WEIGHTS`: comma-separated list of `criterion_name:weight` pairs (default: auto from LLM)

---

## Evidence Pipeline Architecture

Qualitative projects have two evidence build paths. The generator scaffolds both:

**Path A — Manual curation (small projects, curated evidence):**
Operator writes `evidence.txt` directly. Suitable when evidence is already structured (e.g., hand-curated facts, analyst summaries).

**Path B — Compile from raw documents (large projects, many sources):**
Operator dumps source documents into `projects/<slug>/raw/`, optionally types them via `source_type_map.json`, then runs `make evidence-compile PROJECT=<slug>` to produce `evidence.txt` via the LLM compiler. This is the Karpathy-wiki-inspired RAM layer: raw documents → compiled evidence brief → loop.

The generator creates the scaffold for both paths. The operator chooses which to use based on their evidence situation. The `make evidence-fetch` target can additionally fetch web sources into `raw/` before the compile step.

**Compile flow (Path B):**
```bash
# Drop documents into raw/
cp my_report.pdf projects/<slug>/raw/
# Optionally type them
echo '{"my_report.pdf": "source_evidence"}' > projects/<slug>/raw/source_type_map.json
# Compile
make evidence-compile PROJECT=<slug> MODEL=gpt4.1
# Then seal and run
make seal PROJECT=<slug> RUBRIC=rubrics/<slug>.json
```

## Artifacts Created

```
projects/<PROJECT>/
    evidence.txt           # blank with instructional header (Path A starting point)
    raw/                   # empty directory for raw source documents (Path B)
    raw/source_type_map.json   # blank type map for evidence compiler
    thesis.md              # template with neutral seed thesis
    project_charter.md     # auto-drafted from BRIEF
    workspace/             # empty directory for runtime outputs

rubrics/<PROJECT>.json     # LLM-drafted persona + criteria + all Type B opt-outs
```

---

## Rubric Template (Type B opt-outs — always pre-filled)

```json
{
  "farther_tail_region": null,
  "farther_tail_region_disable_reason": "qualitative thesis project — no numerical holdout gate",
  "disable_evidence_fit_gate": true,
  "disable_evidence_fit_gate_reason": "qualitative thesis — evidence surface is text, not a numerical curve; global_evidence_fit gate does not apply",
  "disable_uniqueness_gap_gate": true,
  "disable_uniqueness_gap_gate_reason": "qualitative thesis — rival mechanisms are scored by rubric criteria; mathematical-form keyword heuristic does not apply",
  "holdout_hard_gate": false,
  "enable_fit_primitive": false,
  "fit_score_mode": "none",
  "discovery_mode": false,
  "falsification_mode": "bounded_discriminator",
  "composition_stagnation_threshold": 5,
  "gp103_stagnation_threshold": 3,
  "holdout_budget": 0,
  "persona": "<LLM-drafted — adversarial expert in the thesis domain>",
  "dimensions": [<LLM-drafted — 3–5 dimensions with weights summing to 100>],
  "criteria": {<LLM-drafted — one key per dimension, named to include 'rival' in at least one>}
}
```

**Invariant:** At least one criterion key must contain "rival" in its name so the `global_uniqueness_gap` gate auto-passes without needing `disable_uniqueness_gap_gate`. The LLM prompt must enforce this.

---

## LLM Prompt Design

### System prompt:

```
You are a ZTARE rubric designer. Generate an adversarial evaluation rubric for a qualitative thesis project.

Rules:
1. The persona must be a domain expert who is HOSTILE to easy answers. Give them a specific methodological commitment that rules out at least two common rhetorical moves in this domain.
2. Generate 3–5 dimensions. Weights must sum exactly to 100. Each dimension has: name, weight (int), description (2–3 sentences naming what earns full points and what gets penalized).
3. Generate a criteria dict with one key per dimension. AT LEAST ONE key must contain the word "rival" (e.g., "rival_mechanism_enumeration" or "rival_hypothesis_falsification").
4. Output valid JSON only. No prose outside the JSON object.
5. Do not use domain-generic criteria like "logical consistency" or "evidence quality." Every criterion must be specific to the thesis question provided.
```

### User prompt:
```
Project brief: {brief}

Output the rubric JSON body — only the "persona", "dimensions", and "criteria" fields. The caller will inject all gate configuration keys.
```

---

## thesis.md Template

```markdown
# Thesis — {slug}

## Core Claim

[State your core thesis here. Be specific: name the mechanism, the direction of effect, and the scope conditions.]

## Evidence Base

[Summarize the key evidence. Reference specific items from evidence.txt by line number or label.]

## Rival Hypotheses

[Name at least two rival explanations for the same observed pattern. Explain why each fails on your evidence.]

## Strongest Objection

[State the single strongest objection to your thesis. Explain why it does not overturn the core claim.]

## Fit Declaration

```json
{"variables": [], "expression": "0", "parameter_names": []}
```
```

---

## project_charter.md Template

```markdown
# Project Charter — {slug}

## Core Question

{brief}

## Observable

[What would confirm or disconfirm the core claim? Name at least one observable that would move you.]

## Task

Propose a thesis that:
1. Identifies the strongest causal mechanism
2. Enumerates and falsifies rival explanations
3. Delivers a specific verdict with a justification

## Constraints

- Use only evidence in evidence.txt
- Do not import frameworks or data not cited in the evidence
- The most interesting finding is a genuine falsification, not a rubber-stamp confirmation
```

---

## evidence.txt Template

```
# Evidence for {slug}
# Add one observation per line. Use consistent format: [source] [date] [claim]
# Example:
# [Seattle Times 2024-03] Amazon HQ2 announcement: 25,000 jobs committed in Arlington VA
#
# Paste raw evidence below:
```

---

## Implementation Notes

- Script location: `src/ztare/scaffold/generate_gp_project.py`
- Makefile target: `generate-gp`
- LLM call: use the same API wrapper as `autoresearch_loop.py` (OpenAI client for gpt4.1)
- After generating, print the `make seal` command the operator should run next
- If the project directory already exists, abort with an error (no silent overwrite)
- If the LLM call fails, write a rubric with placeholder `persona` and `criteria` fields and warn the operator

---

## Makefile Target

```makefile
generate-gp:
ifndef PROJECT
	$(error PROJECT is required: make generate-gp PROJECT=name BRIEF="...")
endif
ifndef BRIEF
	$(error BRIEF is required: make generate-gp PROJECT=name BRIEF="...")
endif
	$(PYTHON) -m src.ztare.scaffold.generate_gp_project \
		--slug $(PROJECT) \
		--brief "$(BRIEF)" \
		--judge-model $(or $(JUDGE_MODEL),gpt4.1)
	@echo ""
	@echo "Next: add your evidence to projects/$(PROJECT)/evidence.txt, then:"
	@echo "  make seal PROJECT=$(PROJECT) RUBRIC=rubrics/$(PROJECT).json"
```

---

## Quickstart Update

Add to `docs/guides/quickstart.md` under "Five-Minute Setup: Domain Thesis":

```bash
make generate-gp \
    PROJECT=my_project \
    BRIEF="Your one-paragraph thesis question here" \
    JUDGE_MODEL=gpt4.1

# Add evidence to projects/my_project/evidence.txt, then:
make seal PROJECT=my_project RUBRIC=rubrics/my_project.json
make loop PROJECT=my_project RUBRIC=rubrics/my_project.json ITERS=10 \
    MUTATOR_MODEL=gemini-pro JUDGE_MODEL=gpt4.1
```

---

## Closure

Closed when `generate-gp` target works end-to-end: project scaffold created, Type B opt-outs present, seal passes, loop runs without global gate misfires.
