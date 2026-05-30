---
description: "Specification for a harness, the deterministic pre-judge evaluator."
---
# ZTARE Harness Specification

> **Up:** [Documentation map](../README.md)

**Status:** living document.
**Last updated:** 2026-05-05 13:58:00.
**Authoritative source:** project `gate_harness.py` files are executable, but new harnesses must use shared gate modules in `src/ztare/gates/` whenever a matching primitive exists. If this spec and code disagree, code wins and this spec should be corrected in the same session.

---

## 1. Purpose

A harness is a deterministic pre-judge evaluator. It is allowed to block judge spend, so it has a higher reliability burden than rubric prose. A harness must be small, replayable against an immutable candidate snapshot, and grounded in a documented contract.

Harnesses are not rubrics. A rubric decides how to score a thesis. A harness decides whether the thesis is eligible to spend judge budget.

---

## 2. Required CLI

Every project harness must support:

```bash
python projects/<slug>/gate_harness.py --emit-deterministic-gates --candidate-path <path>
python projects/<slug>/gate_harness.py --run-smoke-test --candidate-path <path>
```

The emitted JSON must include:

- `harness_ok: true`
- `all_gates_pass: bool`
- `gates: list[{"name", "passed", "value", "threshold", "operator", "near_miss"}]`

The autoresearch loop runs the harness against the immutable saved submission snapshot, not mutable `projects/<slug>/test_model.py`.

---

## 3. Shared Modules First

Do not copy AST extraction, polarity filtering, or generic gate logic into a project harness.

Use:

- `src/ztare/gates/claim_polarity.py` for positive-vs-rejected phrase detection.
- `src/ztare/gates/theorem_packet_gate.py` for qualitative theorem-packet contracts with required top-level functions, cross-function obligation groups, and semantic banned-claim checks.
- `src/ztare/gates/substrate_evaluation.py` for quantitative substrate evaluation where applicable.

A project harness should usually be a thin adapter: define the project-specific `TheoremPacketGateSpec` or numeric thresholds, call the shared evaluator, then render the standard JSON payload.

---

## 4. Theorem-Packet Harness Rules

For qualitative theorem substrates, declare the API in `rubrics/<slug>.json`:

```json
"theorem_packet_contract": {
  "required_top_level_functions": ["..."],
  "reason": "..."
},
"require_i_model_in_submission": false
```

The same function names must appear in:

- `projects/<slug>/evidence.txt`
- `projects/<slug>/test_model.py`
- `projects/<slug>/gate_harness.py`

Use `src/ztare/gates/theorem_packet_gate.py` to enforce:

- required module-scope function presence;
- obligations that must live in a specific function;
- obligations that may be satisfied across the declared theorem packet;
- polarity-aware banned-claim detection;
- project-specific overclaim/tautology hooks.
- optional semantic near-miss budgets for qualitative content markers.

Do not require every keyword to live in one exact function if the theorem packet naturally separates declaration, branch proof, and dual certificate. That is the Track B false-zero failure mode from 2026-05-04.

Hard-fail only the mechanically reliable layer by default:

- missing required module-scope functions;
- copied baseline skeletons;
- placeholder/unknown content;
- banned affirmative claims after polarity filtering;
- project-specific tautology or overclaim hooks.

For theorem-packet content groups, prefer `semantic_near_miss_missing_group_budget`
over endlessly expanding synonym lists. A small content-marker miss should emit
`content_warnings` and `near_miss: true` so the judge can evaluate the packet.
A large miss still blocks before judge spend. This is the right compromise for
qualitative theorem packets: deterministic gates police shape and obvious
invalidity, while the judge handles semantic adequacy.

R1 retry prompts must preserve the theorem-packet API. They must not teach the mutator to replace the packet with scalar `PARAMETRIC_FORM`, `LAGRANGIAN`, or `I_model` scaffolding.

Candidate extraction must also preserve theorem-packet source for judge review. In theorem-packet mode, top-level Python functions are not incidental execution scaffolding; they are the submitted theorem packet. `candidate_extraction.preserve_theorem_packet_source()` appends the selected source to the judge-visible thesis whenever the rubric declares `theorem_packet_contract`.

---

## 5. Anti-Tautology

Harnesses should block self-referential proof packets before judge spend when the tautology is mechanically recognizable. Example pattern:

- bad: define the pricing kernel as the target defect inequality itself and declare the missing lemma solved;
- acceptable: state the exact missing dual kernel or matrix-block charging lemma as an infrastructure gap.

The harness blocks clear fake closure. Ambiguous mathematical quality still belongs to the judge.

---

## 6. Validation

Before launching a paid run:

```bash
make validate-rubric PROJECT=<slug>
python projects/<slug>/gate_harness.py --run-smoke-test
```

After editing shared gate logic or a harness:

```bash
./venv/bin/python3 -m pytest tests/gates -q
make arch-validate PYTHON=./venv/bin/python3
```

If a run scores zero unexpectedly, replay the saved submission:

```bash
python projects/<slug>/gate_harness.py --emit-deterministic-gates --candidate-path projects/<slug>/workspace/submissions/iter_*.py
```

Then inspect the actual submission and prompt before modifying apparatus.

---

## 7. Common Mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| Local AST parser copied into a project harness | Similar bugs recur across projects | Move the parser into `src/ztare/gates/` or reuse an existing helper |
| Keyword gate tied to one function body | Valid theorem packet hard-fails because content lives in another required function | Use `FunctionContract.packet_scope` in `theorem_packet_gate.py` |
| Banned phrase detection ignores polarity | “degree-only scaling is forbidden” gets blocked as degree-only scaling | Use `claim_polarity.hard_positive_phrase_group_labels` |
| Theorem-packet code stripped before judging | Harness passes but judge says thesis is empty | Preserve selected theorem-packet source in the judge-visible thesis |
| Harness reads mutable `test_model.py` | Saved submissions do not reproduce gate results | Use `--candidate-path`; autoresearch passes immutable snapshots |
| Harness accepts fake proof closure | Judge spend wasted or false high score | Add an overclaim/tautology hook scoped to the project |
