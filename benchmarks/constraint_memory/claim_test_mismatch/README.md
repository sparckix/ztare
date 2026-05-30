# Claim-Test-Mismatch Suite

This suite isolates a narrower exploit family than the main benchmark:

- selective rigor
- legitimacy halo / halo validation
- tautological verification
- tests aimed at scaffolding or downstream arithmetic rather than the load-bearing claim

Unlike `derived_subtle/`, these are historical specimens mined from real runs rather than synthetic variants.

Purpose:
- test whether the evaluator can detect that a thesis is proving the wrong thing
- compare `A`, `B`, and `C` on claim-test mismatch without changing the main corpus benchmark

Regenerate the suite with:

```bash
python benchmarks/constraint_memory/mine_claim_test_mismatch.py
```

<!-- AUTO-INDEX:START (auto-generated; edit prose OUTSIDE this block) -->

## Index

**Sub-folders**

- [`selective_rigor_recursive_bayesian/`](selective_rigor_recursive_bayesian/) - 6 file(s)
- [`selective_rigor_simulation_god/`](selective_rigor_simulation_god/) - 6 file(s)
- [`tautological_verification_central_station/`](tautological_verification_central_station/) - 6 file(s)

**Documents**

- [index.json](index.json)

<sub>3 sub-folder(s), 1 document(s). Auto-generated; re-run `gen_folder_index.py` after adding files.</sub>
<!-- AUTO-INDEX:END -->
