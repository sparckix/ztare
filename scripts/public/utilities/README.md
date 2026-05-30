# scripts/public/utilities/

> **Up:** [scripts/](../../README.md) · **Subdirs:** [framer/](framer/README.md) · [gpu/](gpu/README.md) · [examples/](examples/README.md) · **Siblings:** [control/](../control/README.md) · [lean/](../lean/README.md)

One-shot linters, bulk migrations, prompt wrappers, and catalog
generators. Run occasionally, not every cycle. A file going quiet here
is expected (one-shots are done once); keep it unless it is both
unreferenced and superseded by a newer migration.

| Script | What it does |
|---|---|
| `auxiliary_object_catalog.py` | pec_a generator: the auxiliary-comparison-object catalog (closed the largest GP-219 gap). |
| `falsifier_first_prompter.py` | pec_e generator: instead of proving the obligation, actively try to falsify it (sharpness-witness construction). |
| `bulk_migrate_evidence_contract.py` | GP-157 v5.0 bulk migration: add an `evidence_contract` block to every rubric that lacks one. |
| `check_cross_scale_aliases.py` | GP-216f auto cross-reference linter: documented cross-scale aliases must resolve on both sides. |
| `context_deidentifier.py` | De-identifies context to bypass the "this is an open problem" model refusal (per the Gemini scientific-research method). |
| `curriculum_generator.py` | Generates easier toy-case variants of an obligation (borrowed from RL theorem provers). |
| `failure_cluster_analyzer.py` | Clusters the typed-endpoint failure log to find systematic apparatus gaps. |
| `gate_from_metric.py` | GP-216f gate-from-metric generator: mechanizes converting a graph-derived metric into an advisory gate. |
| `instance_gate_harness.py` | Substrate-agnostic harness that runs the shipped ZTARE gate stack on one instance-construction candidate. |
| `negative_prompting_wrapper.py` | Iterative method-exhaustion wrapper (Gemini PDF 2.7 / 6.1): force the model past its first method. |
| `scaffold_rubric.py` | Emits a canonical-format rubric skeleton (mechanizes the layout in the rubric specification). |

## Subdirectories

- [framer/](framer/README.md), GP-152 Framer MDL frame-invariance checks.
- [gpu/](gpu/README.md), external GPU / API run bootstrap and registration.
- [examples/](examples/README.md), input fixtures for `instance_gate_harness.py`.

## Related

- Concept: [rubric specification](../../../docs/concepts/rubric_specification.md)
