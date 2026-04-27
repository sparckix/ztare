---
id: GP-157
status: active
summary: GP-101 self-model for src/ztare/orchestrator/render_evidence_template.py (Layer 1 evidence.txt §D rendering from ContractSpec)
---

# orchestrator/render_evidence_template.py — architectural map

GP-157 v5.0 Layer 1 self-model. Generates evidence.txt §D from
`ContractSpec` — single source of truth for the test_model.py contract
seen by the mutator. Eliminates the gp159-class divergence between
hand-authored evidence templates and apparatus-side rules.

## Region map

region: render_evidence_set_d  lines: 32-42  entry: def render_evidence_set_d
region: render_imodel  lines: 45-100  entry: def _render_imodel
region: render_non_imodel  lines: 102-115  entry: def _render_non_imodel
region: render_active_label  lines: 118-130  entry: def render_active_contract_label

## Function/method index

func: render_evidence_set_d  sig: (spec: ContractSpec) -> str
func: render_active_contract_label  sig: (spec: ContractSpec) -> str

## Drift policy

Registered as label `render_evidence_template`. Run `make arch-validate`
after edits.
