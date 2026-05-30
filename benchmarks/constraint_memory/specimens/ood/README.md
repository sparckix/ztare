# OOD Suite

This directory holds out-of-distribution stress tests that are **not** part of the main historical benchmark.

Purpose:
- keep the `N=9` main suite stable
- test whether primitives transfer to a new exploit family or domain without contaminating the main rate table
- report OOD results as a separate case study or appendix subsection

Run only the OOD suite with:

```bash
python benchmarks/constraint_memory/run_benchmark.py --judge-model gemini --suite ood --adjudicator-model gemini
```

<!-- AUTO-INDEX:START (auto-generated; edit prose OUTSIDE this block) -->

## Index

**Sub-folders**

- [`domain_leakage_logistics/`](domain_leakage_logistics/) - 6 file(s)
- [`oncology_biomarker_progression_cutoff/`](oncology_biomarker_progression_cutoff/) - 4 file(s)

**Documents**

- [index.json](index.json)

<sub>2 sub-folder(s), 1 document(s). Auto-generated; re-run `gen_folder_index.py` after adding files.</sub>
<!-- AUTO-INDEX:END -->
