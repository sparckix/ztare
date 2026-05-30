# Constraint Memory Benchmark

This benchmark tests the evaluator, not the full mutator loop.

The question is narrow and empirical:
- does the hardened evaluator catch known exploit families more reliably than the soft baseline?
- do deterministic score gates and approved primitives reduce false accepts without collapsing into reject-all behavior?
- can we distinguish exact exploit-family recognition from acceptable fatal structural kills?

## Conditions
- `A_baseline_soft_judge`: rubric-only judge, no deterministic gates, no primitives
- `B_deterministic_gates`: deterministic Python score gates, no primitives
- `C_gates_plus_primitives`: deterministic gates plus approved attacker/judge-side primitives

## Specimens
Each specimen is a fixed thesis package:
- `specimen.json`: metadata and expected exploit markers
- `thesis.md`: the thesis under evaluation
- `evidence.txt`: bounded evidence for the thesis
- `test_model.py`: the specimen's own falsification suite
- `verified_axioms.json`: optional local axioms

## What the runner does
For each specimen and each condition, the runner:
1. stages a temporary benchmark project under `projects/`
2. copies the specimen files into the project
3. runs `python -m src.ztare.validator.test_thesis`
4. saves `eval_results.json`, stdout, stderr, and the debate log into `benchmarks/constraint_memory/runs/<run_id>/`
5. computes summary metrics

## Metrics
- exploit family detection rate on bad specimens
- fatal structural detection rate on bad specimens
- false accept rate on bad specimens
- false reject rate on good specimens
- score decoupling rate in Condition A

The benchmark now tracks two different success modes on bad specimens:
- `family_detected`: the evaluator identified the expected exploit family or a close taxonomic equivalent
- `structural_detected`: the evaluator identified an acceptable, genuinely fatal structural flaw, even if it used a different label

This avoids the "Al Capone" measurement error where a thesis is correctly killed for the wrong taxonomic reason and gets counted as a miss.

## Run
```bash
python benchmarks/constraint_memory/run_benchmark.py --judge-model gemini
```

Optional:
```bash
python benchmarks/constraint_memory/run_benchmark.py --judge-model claude --specimen unidirectional_decay
```

Run only the derived subtlety sensitivity tests:
```bash
python benchmarks/constraint_memory/run_benchmark.py --judge-model gemini --suite derived_subtle --adjudicator-model gemini
```

Run only the historical claim-test-mismatch mini-suite:
```bash
python benchmarks/constraint_memory/run_benchmark.py --judge-model gemini --suite claim_test_mismatch --adjudicator-model gemini
```

Run only the out-of-distribution stress-test suite:
```bash
python benchmarks/constraint_memory/run_benchmark.py --judge-model gemini --suite ood --adjudicator-model gemini
```

Run only the auxiliary historical holdout suite:
```bash
python benchmarks/constraint_memory/run_benchmark.py --judge-model gemini --suite auxiliary_historical --adjudicator-model gemini
```

Include the experimental crux-first primitive condition (`C2`):
```bash
python benchmarks/constraint_memory/run_benchmark.py --judge-model gemini --suite claim_test_mismatch --adjudicator-model gemini --include-crux-first-condition
```

Optional semantic exploit adjudication:
```bash
python benchmarks/constraint_memory/run_benchmark.py --judge-model gemini --adjudicator-model gemini
```

This adds a second lightweight LLM pass that decides whether the evaluator semantically caught the exploit family, even if it used different wording than the keyword list.

## Safe Harbor
Good controls are intentionally narrow local components. The benchmark rubric and prompt include an evidentiary safe harbor:
- consuming upstream booleans or status tokens is not automatically a trust leak
- bounded deterministic mappings and fail-closed gates may be proven by exhaustive local tests
- they should only fail if they overclaim, smuggle in upstream truthfulness, or pretend local execution proves whole-system validity

## Corpus Mining
Use the existing paper/corpus outputs to seed a less hand-curated bad-specimen vault:

```bash
python benchmarks/constraint_memory/mine_specimens.py
```

This mines the full-thesis cognitive-camouflage corpus into:
- `benchmarks/constraint_memory/specimens/corpus_bad/`

Current mined families include:
- recursive Bayesian reasoning
- AI inference collapse
- TSMC fragility
- simulation god
- epistemic engine v3

## Claim-Test-Mismatch Suite
The repository also contains a separate historical mini-suite in:
- `benchmarks/constraint_memory/claim_test_mismatch/`

This suite focuses on a different exploit family than threshold rigging:
- selective rigor
- tests that prove scaffolding rather than the central claim
- tautological or straw-man falsification

## OOD Suite
The repository also contains a separate out-of-distribution stress-test suite in:
- `benchmarks/constraint_memory/specimens/ood/`

These cases are intentionally **not** included in the main historical benchmark.
They are for targeted transfer checks, such as:
- `domain_leakage`
- future held-out exploit families that should not silently change the main benchmark rates

## Auxiliary Historical Suite
The repository also contains a separate historical expansion suite in:
- `benchmarks/constraint_memory/auxiliary_historical/`

These are additional mined historical candidates that are **not** part of the frozen main benchmark.
Use this suite to test:
- whether new historical cases are genuinely benchmark-worthy
- whether they add distinct exploit coverage
- whether they should remain auxiliary or graduate into a later benchmark revision

## Derived Subtlety Suite
The repository also contains a separate synthetic sensitivity suite in:
- `benchmarks/constraint_memory/derived_subtle/`

This suite is for controlled adversarial variants, not historical corpus reproduction.

<!-- AUTO-INDEX:START (auto-generated; edit prose OUTSIDE this block) -->

## Index

**Sub-folders**

- [`auxiliary_historical/`](auxiliary_historical/) - 25 file(s)
- [`claim_test_mismatch/`](claim_test_mismatch/) - 19 file(s)
- [`derived_subtle/`](derived_subtle/) - 15 file(s)
- [`specimens/`](specimens/) - 72 file(s)
- [`stage1_ood/`](stage1_ood/) - 12 file(s)
- [`stage3_ood/`](stage3_ood/) - 4 file(s)

**Documents**

- [Historical Candidate Review](historical_candidate_review.md)
- [mine_auxiliary_historical.py](mine_auxiliary_historical.py)
- [mine_claim_test_mismatch.py](mine_claim_test_mismatch.py)
- [mine_specimens.py](mine_specimens.py)
- [run_benchmark.py](run_benchmark.py)

<sub>6 sub-folder(s), 5 document(s). Auto-generated; re-run `gen_folder_index.py` after adding files.</sub>
<!-- AUTO-INDEX:END -->
