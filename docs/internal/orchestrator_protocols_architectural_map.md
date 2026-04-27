---
id: GP-157
status: active
summary: GP-101 self-model for src/ztare/orchestrator/protocols.py (Layer 1 typed Protocols + adapt())
---

# orchestrator/protocols.py — architectural map

GP-157 v5.0 Layer 1 self-model. Runtime-checkable PEP 544 Protocols
(`ScalarModel`, `FeatureModel`) + `adapt()` boundary validator.
Pairs with `contract_table.py` (the registry) and
`render_evidence_template.py` (evidence.txt §D rendering).

## Region map

region: scalar_model_proto  lines: 25-30  entry: class ScalarModel
region: feature_model_proto  lines: 33-37  entry: class FeatureModel
region: contract_error  lines: 43-72  entry: class ContractError
region: error_codes  lines: 75-84  entry: CONTRACT_ERROR_CODES
region: signature_match  lines: 90-115  entry: def _signature_matches
region: adapt  lines: 118-185  entry: def adapt

## Function/method index

func: adapt  sig: (module, spec) -> Callable
func: _signature_matches  sig: (observed, abi) -> bool

## Drift policy

Registered as label `protocols`. Run `make arch-validate` after edits.
