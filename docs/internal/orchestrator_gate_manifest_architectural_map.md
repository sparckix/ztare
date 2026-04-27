---
id: GP-157
status: active
summary: GP-101 self-model for src/ztare/orchestrator/gate_manifest.py (Layer 3 declarative gate manifest)
---

# orchestrator/gate_manifest.py — architectural map

GP-157 v5.0 Layer 3 self-model. Sibling of L1 (`contract_table.py`,
substrate ABI) and L2 (`evidence_contract.py`, evidence text format).
Replaces operator-authored imperative `gate_harness.py` files with a
declarative, type-checked gate manifest the Cage dispatcher reads from
the rubric.

Per Gemini Pro panel (2026-04-25 night): the gp160-class intent /
mechanism translation gap (operator renames a gate but forgets to flip
the threshold; LLM 'semantic alignment' meta-gates hallucinate) is
solved structurally by removing per-substrate imperative gate code
entirely. The mechanism IS the type — operator cannot declare
`BOUNDS_CHECK` and execute `EXTRAPOLATION_MRE`.

## Region map

region: gate_type_enum  lines: 43-106  entry: class GateType(Enum)
region: evaluative_gate_spec  lines: 109-135  entry: class EvaluativeGateSpec
region: parameter_schemas  lines: 142-184  entry: PARAMETER_SCHEMAS:
region: gate_contract_error  lines: 187-207  entry: class GateContractError
region: validate_gate_spec  lines: 210-263  entry: def validate_gate_spec
region: gate_context_protocol  lines: 270-281  entry: class GateContext(Protocol)
region: bounds_check_impl  lines: 284-306  entry: def _eval_bounds_check
region: holdout_mre_impl  lines: 309-341  entry: def _eval_holdout_mre
region: anti_retrieval_impl  lines: 344-365  entry: def _eval_anti_retrieval
region: gate_registry  lines: 375-379  entry: GATE_REGISTRY:
region: evaluate_gate_dispatcher  lines: 382-391  entry: def evaluate_gate
region: list_helpers  lines: 394-400  entry: def list_gate_types

## Function/method index

func: validate_gate_spec  sig: (spec_dict: Mapping[str, Any]) -> EvaluativeGateSpec
func: evaluate_gate  sig: (ctx: GateContext, spec: EvaluativeGateSpec) -> dict
func: list_gate_types  sig: () -> tuple[str, ...]
func: list_registered_gate_types  sig: () -> tuple[str, ...]

## Closed enum — GateType

10 unanimous-WIRE gates from panel triage. Linus-syscall numbering:
monotonic, never renumbered. Adding a gate = appending an enum value +
registering an impl. Removing/renaming requires DECISION_LOG entry +
substrate migration (any rubric referencing the old name fails seal).

| ID | GateType | Status |
|---|---|---|
| 1 | BOUNDS_CHECK | impl shipped |
| 2 | HOLDOUT_MRE | impl shipped |
| 3 | EXTRAPOLATION_MRE | spec only |
| 4 | ASYMPTOTIC_DISCIPLINE | spec only |
| 5 | MONOTONICITY | spec only |
| 6 | POSITIVITY | spec only |
| 7 | PARAMETER_COUNT | spec only |
| 8 | ANTI_RETRIEVAL | impl shipped |
| 9 | FRAME_INVARIANCE | spec only |
| 10 | DIMENSIONAL_CONSISTENCY | spec only |

`validate_gate_spec` accepts all 10 (strict-typed parameter schemas).
`evaluate_gate` raises `GateContractError[GATE_TYPE_NOT_REGISTERED]`
for the 7 spec-only types. Add impls incrementally as substrates need
them.

## Error taxonomy

GateContractError canonical codes:

| Code | When |
|---|---|
| UNKNOWN_GATE_TYPE | rubric `type` field not in GateType enum |
| MISSING_PARAMETER | required key absent from `parameters` |
| WRONG_PARAMETER_TYPE | parameter value not isinstance of schema type |
| EXTRA_PARAMETER | unexpected key in `parameters` (strict — no extras) |
| GATE_TYPE_NOT_REGISTERED | spec-only type invoked via evaluate_gate |

## Wire-in (post-ship)

This module ships the foundation only. Subsequent commits:

1. `scripts/validate_evidence.py` — Check #17: validate every entry in
   `rubric_data["evaluative_gates"]` via `validate_gate_spec`. Refuse
   seal on any GateContractError.
2. `autoresearch_loop.py` Phase 2 dispatch — replace `gate_harness.py`
   subprocess invocation with `evaluate_gate(ctx, spec)` calls against
   the FrozenFittedModel from Phase 1.
3. Substrate migration sweep — convert each project's gate_harness.py
   into rubric `evaluative_gates: [...]` block. Deprecate gate_harness.py
   once all substrates migrated.

## Drift policy

Run `make arch-validate` after edits — registry contains
(`gate_manifest`, this map, `gate_manifest.py`). Region line ranges are
checked with ±30 line tolerance.

## Companion files

| Layer | Module | Map |
|---|---|---|
| L1 | orchestrator/contract_table.py | orchestrator_contract_table_architectural_map.md |
| L1 | orchestrator/protocols.py | orchestrator_protocols_architectural_map.md |
| L2 | orchestrator/evidence_contract.py | orchestrator_evidence_contract_architectural_map.md |
| L3 | orchestrator/gate_manifest.py | (this file) |
