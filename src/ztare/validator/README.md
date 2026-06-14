# Validator Architecture

This directory contains two different kinds of logic:

## 1. Generic Runner Infrastructure

These components are allowed to be shared across projects:
- mutation declaration parsing and validation
- candidate admissibility / retention
- generic selection records
- generic loop control
- generic committee / evaluator plumbing

Examples:
- `mutation_contract.py`
- `runner_selection.py`
- `autoresearch_loop.py`

## 2. Project-Local Contract Logic

These components must stay local to the project or contract track that owns them:
- project-specific mismatch vocabularies
- project-specific fixture corpora
- project-specific typed contract evaluators
- project-specific promotion runners / meta-runners

Examples:
- `stage24_bridge.py`
- `stage24_bridge_fixture_regression.py`

## 3. Extraction and Memory Components

These components harvest structural signals from run history:
- `structural_constraint_extractor.py`: feature-bag intersection across failed families to extract structural constraints
- `negative_space_extractor.py`: detects void operators (operations absent from all tried families)
- `structural_memory.py`, per-iteration structural memory accumulation
- `structural_memory_fixture_regression.py`, fixture regression for structural memory
- `fit_multistart_replay.py`, multi-start fit replay for curve-fitting sandboxes

## Architectural Constraints

### Separation Rule

Do not push project-local semantics into the generic runner just because it is expedient.

If a concept is only needed by one contract track, keep it local to that track.
If a concept is genuinely reusable across tracks, promote it deliberately into shared infrastructure first.

### Evaluator-Scope Matching

The promotion contract must match the actual scope of the claim.

Wrong pattern:
- keep running the wrong evaluator
- then patch the claim or prompt so it survives

Right pattern:
- identify the actual typed contract being claimed
- build or use the evaluator that scores that contract directly

### False-Rigor Rule

A hard kernel inside a soft runner can launder bad orchestration into a confident pass.

So:
- harden what enters the kernel
- harden what survives across iterations
- do not treat runner-side attribution and retention as optional
