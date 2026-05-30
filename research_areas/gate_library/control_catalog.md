# Control Catalog

Private first-slice inventory of implemented controls.

Scope discipline:

- only live controls
- only repo-backed enforcement surfaces
- uncertain provenance marked `TBD`
- no aspirational controls

Last updated: 2026-04-12 13:11:05 EDT

## Deterministic Charter Gates

| Control | Type | Enforcement Surface | Trigger | Fail-Closed Behavior | Origin | Precedent |
|---|---|---|---|---|---|---|
| `charter_declared_metric_thresholds` | threshold gate family | `src/ztare/validator/deterministic_charter_gates.py`, `src/ztare/validator/test_thesis.py` | project charter declares machine-readable deterministic gates | per failed gate, add a `soft_score_caps` entry at `50`; gate details preserved in `score_contract.deterministic_charter_gates` | `GP-030` | `criterion_reinterpretation_laundering` |
| `charter_harness_fail_closed` | harness contract gate | `src/ztare/validator/deterministic_charter_gates.py`, `src/ztare/validator/test_thesis.py` | gate harness missing payload or exits non-zero | declared gates fail closed with failing results and score cap `50` | `GP-030` | `gp037_invalid_smoke_contract_failure` |
| `declared_gate_name_inventory` | attestation / audit surface | `src/ztare/validator/deterministic_charter_gates.py`, `src/ztare/validator/test_thesis.py` | deterministic gates evaluated | declared gate names and results written into `score_contract` for later audit | `GP-030` | `criterion_reinterpretation_laundering` |

## Score Caps And Semantic Guards

| Control | Type | Enforcement Surface | Trigger | Fail-Closed Behavior | Origin | Precedent |
|---|---|---|---|---|---|---|
| `hard_self_reference_zero` | hard fail | `src/ztare/validator/semantic_gate_stabilization.py`, `src/ztare/validator/test_thesis.py` | semantic gate derives `hard_self_reference` | score forced to `0` via `hard_fail_reasons` | `TBD (repo-local; exact seam origin not yet cataloged)` | `hard_self_reference` |
| `self_referential_proof_cap_25` | soft cap | `src/ztare/validator/test_thesis.py` | proof marked self-referential but not hard-self-reference | total score capped at `25` | `TBD (repo-local; exact seam origin not yet cataloged)` | `hard_self_reference` |
| `quarantine_laundering_cap_67` | soft cap | `src/ztare/validator/test_thesis.py` | quarantined dependency still gates named discriminator or falsification environment | total score capped at `67` | `GP-012` | `quarantine_laundering` |
| `quarantine_laundering_cap_83` | soft cap | `src/ztare/validator/test_thesis.py` | quarantined dependency still gates central causal mechanism or remains unclearly central | total score capped at `83` | `GP-012` | `quarantine_laundering` |
| `deferred_confirmation_cap_67` | soft cap | `src/ztare/validator/test_thesis.py` | decisive confirmation deferred to a forward observable without direct present confirmation | total score capped at `67` | `GP-014` | `deferred_confirmation_laundering` |
| `deferred_confirmation_cap_83` | soft cap | `src/ztare/validator/test_thesis.py` | decisive confirmation deferred and current support is only directional | total score capped at `83` | `GP-014` | `deferred_confirmation_laundering` |
| `directional_forecast_point_probability_cap_50` | soft cap | `src/ztare/validator/test_thesis.py`, `src/ztare/validator/charter_parsing.py` | project charter is `directional_forecast` and thesis emits unsupported `%` / point probability | total score capped at `50` | `GP-022` | `directional_forecast_overclaim` |
| `anchor_proxy_drift_cap_50` | soft cap | `src/ztare/validator/test_thesis.py`, `src/ztare/validator/proxy_signature.py` | active suite covers less than `ANCHOR_PROXY_MIN_COVERAGE` of declared anchor proxies | total score capped at `50` | `TBD (repo-local; no dedicated seam recorded)` | `anchor_proxy_drift` |

## Runner Admission Guards

| Control | Type | Enforcement Surface | Trigger | Fail-Closed Behavior | Origin | Precedent |
|---|---|---|---|---|---|---|
| `runner_r1_mutation_declaration_required` | admission guard | `src/ztare/validator/autoresearch_loop.py`, `src/ztare/validator/mutation_contract.py` | `--runner_r1_contract` enabled and mutator omits declaration header | candidate rejected before kernel scoring | `GP-020` | `scope_slip_without_declared_mutation` |
| `runner_r1_declared_vs_actual_scope_guard` | admission guard | `src/ztare/validator/autoresearch_loop.py`, `src/ztare/validator/mutation_contract.py` | declared mutation scope does not match touched artifacts / primitive use | candidate rejected before kernel scoring | `GP-020` | `scope_slip_without_declared_mutation` |
| `suite_presence_guard` | admission guard | `src/ztare/validator/mutation_suite_guard.py`, `src/ztare/validator/autoresearch_loop.py` | missing Python suite or no-suite sentinel emitted | candidate rejected before evaluation | `GP-026` | `no_suite_mutation_admission` |
| `bounded_discriminator_stdlib_guard` | admission guard | `src/ztare/validator/autoresearch_loop.py` | bounded-discriminator suite imports non-stdlib dependencies or uses relative imports | candidate rejected before evaluation | `TBD (repo-local bounded-discriminator hardening)` | `portable_suite_drift` |
| `bounded_discriminator_profile_pre_run_assert` | pre-run assert | `src/ztare/validator/autoresearch_loop.py`, `src/ztare/catch_grammar/rule_3_profile_check.py` | bounded-discriminator profile missing required heuristic modules | run refuses to start | `GP-020` + `GP-021` | `sealed_profile_drift` |

## Promotion Guards

| Control | Type | Enforcement Surface | Trigger | Fail-Closed Behavior | Origin | Precedent |
|---|---|---|---|---|---|---|
| `findings_promotion_requires_convergence` | promotion guard | `src/ztare/validator/supervisor_findings_promotion.py` | seam not `CONVERGED` and no explicit override | promotion refused | `GP-031` | `pre_seed_promotion_without_closed_debate` |
| `findings_promotion_requires_spec` | promotion guard | `src/ztare/validator/supervisor_findings_promotion.py` | `spec_path` missing on disk | promotion refused | `GP-031` | `pre_seed_promotion_without_contract` |
| `findings_seed_id_uniqueness` | promotion guard | `src/ztare/validator/supervisor_findings_promotion.py` | `seed_id` already present in seed registry | promotion refused | `GP-031` | `duplicate_seed_identity` |
| `findings_no_closed_on_arrival` | promotion guard | `src/ztare/validator/supervisor_findings_promotion.py` | request tries to promote directly as `CLOSED` | promotion refused | `GP-031` | `closed_on_arrival_type_confusion` |

## Prompt-Level Contracts

| Control | Type | Enforcement Surface | Trigger | Fail-Closed Behavior | Origin | Precedent |
|---|---|---|---|---|---|---|
| `bounded_discriminator_output_contract` | prompt contract | `src/ztare/validator/autoresearch_loop.py` | rubric `falsification_mode = bounded_discriminator` | mutator must produce regime/rival/discriminator/observable structure and executable discriminator suite; noncompliant suites later hit runner guards or score caps | `TBD (verify against GP-021 / hardening lineage before public surfacing)` | `portable_suite_drift` |
| `anchor_proxy_preservation_contract` | prompt contract | `src/ztare/validator/autoresearch_loop.py` | project charter declares anchor proxies | mutator is explicitly warned that dropping below 50% anchor coverage will cap score; deterministic check enforced later in `test_thesis.py` | `TBD (repo-local; paired with anchor proxy drift cap)` | `anchor_proxy_drift` |
| `fit_declaration_required_when_enabled` | prompt contract | `src/ztare/validator/autoresearch_loop.py`, `src/ztare/validator/fit_primitive.py` | rubric enables fit primitive | mutator must emit `FIT_DECLARATION`; omission writes typed fit-failure artifact and fit does not run | `GP-035` | `missing_fit_declaration_contract` |

## Notes

- This inventory is deliberately file-level. It avoids pseudo call chains until a second pass verifies every function boundary.
- `TBD` provenance is allowed in slice 1 only where the control is live but the exact seam-of-origin has not yet been reconstructed from the repo history.
- Machine-readable gate catalogs are explicitly deferred. This file is the first audit surface, not a runtime registry.
