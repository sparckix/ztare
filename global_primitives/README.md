# Global Primitives

This directory is a curated library of reusable adversarial precedents.

It is **not** a global truth store.

The purpose of the library is to preserve:

- failure patterns
- attack patterns
- test templates
- narrow causal motifs that survived enough scrutiny to be worth re-testing elsewhere

The purpose of the library is **not** to store universally valid axioms.

## Core Rule

Primitives are:

- reusable
- defeasible
- scoped
- reviewable

Primitives are not:

- evidence
- axioms
- automatically portable truths

## Relationship To The Workspace

The project workspace stores **project knowledge**:

- facts
- ranges
- contradictions
- open questions
- candidate claims

The primitives library stores **cross-project meta-patterns**:

- how things break
- how they are attacked
- what kind of test exposed them

So:

- `workspace/` = content memory
- `global_primitives/` = meta-pattern memory

## Relationship To The Gaming Catalog

`global_primitives/` is related to the gaming catalog, but it is downstream of it.

- `docs/cheating_catalog.md` explains the public catalog of gaming behaviors.
- `analytics/public/queries/gaming_vector_catalog.jsonl` records live vector status and gate lineage.
- `global_primitives/incidents/` records extracted occurrences that can support reusable patterns.
- `global_primitives/approved/` stores approved attack/failure/test templates that may be reused in validator roles.

So a pattern such as `cooked_books` can appear in both places: as a gaming behavior in the catalog and as an approved attack template in this primitive library. The primitive file does not decide whether the vector is gated; it only says the pattern is reusable enough to retrieve as a precedent.

## Promotion Model

Promotion is intentionally hybrid:

1. Python extracts incident records from project artifacts.
2. An LLM drafts candidate primitive cards from grouped incidents.
3. A human reviews and promotes or rejects.

This prevents the system from auto-promoting elegant but false abstractions.

## Directory Layout

```text
global_primitives/
  primitive_incident.schema.json
  primitive_candidate.schema.json
  README.md
  incidents/
  review/
  approved/
  rejected/
```

## Engine Usage Boundary

Approved primitives may later be used in the engine, but only under these constraints:

1. they are never injected as evidence
2. they are never treated as project-local axioms
3. they are retrieved as `TRANSFER HYPOTHESES` or attack/test templates
4. applicability must be justified in-domain
5. the firing squad must be able to attack transfer validity explicitly

The safe use is:

- mutator sees them as optional structural hints
- firing squad sees them as attack prompts
- judge penalizes unearned transfer

## Minimal Workflow

1. extract incidents
```bash
python -m src.ztare.workspace.extract_incidents
```

2. draft primitive candidates
```bash
python -m src.ztare.primitives.draft_primitives --model gemini
```

3. review candidate cards in `global_primitives/review/`

4. approve or reject candidates
```bash
python -m src.ztare.primitives.approve_primitive --primitive-key cooked_books --decision approved
python -m src.ztare.primitives.approve_primitive --primitive-key domain_leakage --decision rejected --note "Too local to architecture runs."
```

5. optionally enable approved primitives in the validator
```bash
python -m src.ztare.validator.autoresearch_loop --project my_project --rubric my_rubric --use_primitives
```

By default this only arms the attacker/judge side with approved precedents.

To also expose transfer hypotheses to the mutator, opt in explicitly:
```bash
python -m src.ztare.validator.autoresearch_loop --project my_project --rubric my_rubric --use_primitives --use_transfer_hypotheses
```

## First Recommendation

Start with:

- gaming strategies from the paper
- repeated attack/test patterns from startup and architecture runs

Do not start with broad cross-domain causal laws. Those are the easiest to overgeneralize.

<!-- AUTO-INDEX:START (auto-generated; edit prose OUTSIDE this block) -->

## Index

**Sub-folders**

- [`approved/`](approved/) - 18 file(s)
- [`incidents/`](incidents/) - 3 file(s)
- [`rejected/`](rejected/) - 2 file(s)
- [`review/`](review/) - 4 file(s)

**Documents**

- [primitive_candidate.schema.json](primitive_candidate.schema.json)
- [primitive_incident.schema.json](primitive_incident.schema.json)

<sub>4 sub-folder(s), 2 document(s). Auto-generated; re-run `gen_folder_index.py` after adding files.</sub>
<!-- AUTO-INDEX:END -->
