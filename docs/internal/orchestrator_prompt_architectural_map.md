---
id: GP-157
status: active
summary: GP-101 self-model for src/ztare/orchestrator/prompt.py (Phase 4d substrate-contract-hint)
---

# orchestrator/prompt.py — architectural map

GP-157 v5.0 Phase 4d self-model. Real fix for the gp159 mutator-empty-Python
bug surfaced by the parallel agent 2026-04-25 night.

## Purpose

Tell the mutator the I_model OVERRIDE contract when the substrate is
custom (cage_meta.class in {nd_features, audit, literature, proof_target})
AND no fit primitive is engaged. Empty hint in all other cases — existing
prompt blocks already cover those cases.

The standard mutator prompt describes Contract A (assert-based discriminator
suite, legacy 1D substrates). Custom substrates use Contract B
(`I_model(features) -> float`). Without this hint, the mutator gets
contradictory instructions ("evidence.txt says override, prompt says assert")
and writes nothing → I_model returns NaN → all iterations fail.

## Region map

region: imports  lines: 60-65  entry: from __future__ import annotations
region: override_classes  lines: 60-79  entry: _OVERRIDE_CONTRACT_CLASSES
region: scalar_classes  lines: 80-80  entry: _SCALAR_OVERRIDE_CONTRACT_CLASSES
region: scalar_hint_text  lines: 83-142  entry: _I_MODEL_SCALAR_CONTRACT_HINT
region: contract_hint_text  lines: 144-192  entry: _I_MODEL_OVERRIDE_CONTRACT_HINT
region: needs_check  lines: 210-225  entry: def needs_override_contract_hint
region: needs_scalar_check  lines: 227-265  entry: def needs_scalar_contract_hint
region: select  lines: 267-285  entry: def select_substrate_contract_hint
region: verify_consistency  lines: 383-470  entry: def verify_class_consistency_with_substrate

## Function/method index

func: needs_override_contract_hint  sig: (rubric_data: Mapping[str, Any]) -> bool
func: needs_scalar_contract_hint  sig: (rubric_data, project_dir=None) -> bool
func: select_substrate_contract_hint  sig: (rubric_data, project_dir=None) -> str
func: verify_class_consistency_with_substrate  sig: (cage_meta_class: str, project_dir: Path) -> Optional[str]

## Exit list

(No raises — selector is total over rubric_data shape; malformed
cage_meta returns False/empty rather than raising.)

## Drift policy

This file is registered in `scripts/validate_autoresearch_arch_map.py`
MAP_REGISTRY as label `prompt`. Run `make arch-validate` after edits.

## Wire site

`src/ztare/validator/autoresearch_loop.py:mutate_thesis` reads the hint
once near the top of the function and injects it into the f-string
between `fit_primitive_features_context` and `structural_memory_prompt`.
