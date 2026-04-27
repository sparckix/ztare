---
id: GP-157
status: active
summary: GP-101 self-model for src/ztare/orchestrator/contract_adherence.py
---

# orchestrator/contract_adherence.py — architectural map

GP-157 v5.0 — substrate-contract adherence telemetry. Operator concern
2026-04-25 night: prompt has ~15 sections, mutator may skim past the
contract hint. This module emits empirical signal about whether the
hint is effective.

## Region map

region: imports  lines: 21-30  entry: from __future__ import annotations
region: violation_codes  lines: 33-40  entry: VIOLATION_CODES
region: adherence_report  lines: 43-60  entry: @dataclass(frozen=True)
region: resolve_active_contract  lines: 65-85  entry: def _resolve_active_contract
region: check_contract_adherence  lines: 88-180  entry: def check_contract_adherence
region: runtime_check  lines: 184-291  entry: def runtime_check_imodel
region: emit_adherence  lines: 294-318  entry: def emit_adherence
region: format_summary  lines: 321-333  entry: def format_adherence_summary

## Function/method index

func: _resolve_active_contract  sig: (rubric_data, project_dir) -> str
func: check_contract_adherence  sig: (test_model_text, rubric_data, project_dir) -> list[str]
func: runtime_check_imodel  sig: (test_model_path: Path, *, sample_count: int = 3) -> list[str]
func: emit_adherence  sig: (ctx: IterContext, test_model_text: str) -> AdherenceReport
func: format_adherence_summary  sig: (report: AdherenceReport) -> Optional[str]
func: to_jsonl_line  sig: (self) -> str

## Exit list

(No raises — all checks return diagnostic codes; emit appends to JSONL
with mkdir parents=True. autoresearch_loop wraps the call site in
try/except so telemetry failure never aborts a run.)

## Drift policy

Registered in MAP_REGISTRY as label `contract_adherence`. Run
`make arch-validate` after edits.
