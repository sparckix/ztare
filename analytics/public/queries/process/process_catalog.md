# Process-Loop Catalog (auto-classified, no-git)

_Generated 2026-05-09T23:24:02.337669+00:00_  
_Artifacts:_ 810  _Inferred kinds:_ {'recently_authored': 444, 'unclassified': 326, 'periodic': 5, 'loop': 29, 'one_shot': 6}  _Seed disagreements:_ 1

## Loops detected

| Path | Confidence | Frontmatter recurrence | Code-loop hits |
|---|---:|---|---:|
| `org/key_results/manager_weekly_okr_walk.md` | 0.818 | P7D | 0 |
| `org/key_results/rd_apparatus_l2_review.md` | 0.818 | P7D | 0 |
| `org/key_results/rd_mathlib_reconnaissance_refresh.md` | 0.818 | P30D | 0 |
| `org/key_results/rd_reflexive_audit_periodic.md` | 0.818 | P14D | 0 |
| `org/key_results/rd_seam_health_periodic.md` | 0.818 | P30D | 0 |
| `org/objectives/role_duty_cadence.md` | 0.667 | — | 0 |
| `scripts/public/mining/mine_trajectory_curves.py` | 0.6 | — | 1 |
| `src/ztare/gates/derived_constraints.py` | 1.0 | — | 3 |
| `src/ztare/gates/derived_constraints_fixture_regression.py` | 1.0 | — | 1 |
| `src/ztare/gates/negative_space_extractor.py` | 1.0 | — | 1 |
| `src/ztare/gates/potential_function_monotonicity_gate.py` | 0.6 | — | 1 |
| `src/ztare/gates/r8_r9_substrate_validators.py` | 0.6 | — | 1 |
| `src/ztare/gates/registry.py` | 1.0 | — | 1 |
| `src/ztare/gates/stagnation_special_case_hint_gate.py` | 0.6 | — | 1 |
| `src/ztare/gates/structural_constraint_extractor.py` | 1.0 | — | 1 |
| `src/ztare/orchestrator/blitz_dispatch.py` | 1.0 | — | 1 |
| `src/ztare/orchestrator/briefing_providers/cold_llm_seed.py` | 0.6 | — | 1 |
| `src/ztare/orchestrator/briefing_providers/embedding_history.py` | 0.6 | — | 1 |
| `src/ztare/orchestrator/briefing_providers/forced_reframe.py` | 0.6 | — | 1 |
| `src/ztare/orchestrator/cold_llm_seed_requery.py` | 0.6 | — | 1 |
| `src/ztare/orchestrator/derived_constraints_refresh.py` | 0.6 | — | 2 |
| `src/ztare/orchestrator/discriminator_queue.py` | 1.0 | — | 1 |
| `src/ztare/orchestrator/forced_reframe.py` | 0.778 | — | 3 |
| `src/ztare/orchestrator/gp087_tail_correction.py` | 0.6 | — | 1 |
| `src/ztare/orchestrator/iter_context.py` | 1.0 | — | 1 |
| `src/ztare/orchestrator/iter_signal_helpers.py` | 0.6 | — | 1 |
| `src/ztare/orchestrator/iteration_telemetry.py` | 0.6 | — | 1 |
| `src/ztare/orchestrator/loop_event_recorder.py` | 0.6 | — | 1 |
| `src/ztare/orchestrator/mutator_briefing.py` | 0.6 | — | 1 |
| `src/ztare/orchestrator/mutator_briefing_fixture_regression.py` | 1.0 | — | 1 |

## Recursion candidates (one-shots in operator-loop namespaces)

| Path | Inferred kind | Age (d) | Confidence | Frontmatter |
|---|---|---:|---:|---|
| `src/ztare/gates/deterministic_charter_gates.py` | `unclassified` | 20 | 0.0 | `status=—` |
| `src/ztare/gates/deterministic_charter_gates_fixture_regression.py` | `unclassified` | 20 | 0.0 | `status=—` |
| `src/ztare/gates/structural_anti_pattern_gates_fixture_regression.py` | `unclassified` | 8 | 0.0 | `status=—` |
| `src/ztare/orchestrator/charter_critic.py` | `one_shot` | 2 | 0.714 | `status=—` |

## Seed disagreements (heuristic vs seed)

| Path | Seed kind | Inferred | Confidence | Notes |
|---|---|---|---:|---|
| `scripts/public/mining/mine_closure_patterns.py` | `periodic` | `recently_authored` | 1.0 | seed declared 'periodic' but heuristic inference is 'recently_authored' (confide |

