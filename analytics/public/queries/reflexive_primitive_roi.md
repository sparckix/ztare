# Reflexive Primitive ROI Scorecard

_Generated 2026-05-16T21:37:35.984935+00:00_  
_Since:_ 2026-04-18T21:37:35.846776+00:00  
_Projects scanned:_ 157

## By verdict

| Verdict | Count |
|---|---:|
| `dead` | 7 |
| `insufficient_data` | 7 |
| `engagement_high` | 4 |

## Per primitive

| Primitive | Eligible projects | Eligible iters | Engaged | Refused | Findings | Engagement rate | Verdict |
|---|---:|---:|---:|---:|---:|---:|---|
| `contract_adherence` (contract_adherence) | 157 | 1527 | 651 | 0 | 651 | 42.63% | `engagement_high` |
| `R13` (substrate_critic) | 129 | 1473 | 578 | 444 | 0 | 39.24% | `engagement_high` |
| `R14` (noise_profile) | 129 | 1473 | 578 | 444 | 0 | 39.24% | `engagement_high` |
| `GP-180` (dag_steering) | 24 | 453 | 345 | 0 | 345 | 76.16% | `engagement_high` |
| `ansatz_survivor` (ansatz_survivor) | 157 | 1527 | 67 | 487 | 0 | 4.39% | `dead` |
| `R8` (feature_coverage_adequacy) | 0 | 0 | 0 | 0 | 0 | 0.00% | `insufficient_data` |
| `R9` (target_convention_homogeneity) | 0 | 0 | 0 | 0 | 0 | 0.00% | `insufficient_data` |
| `R10` (cross_class_extrapolation) | 157 | 1527 | 0 | 511 | 0 | 0.00% | `dead` |
| `R11` (per_class_mre_ceiling) | 3 | 54 | 0 | 280 | 0 | 0.00% | `dead` |
| `R12` (symbolic_logic_cage) | 0 | 0 | 0 | 0 | 0 | 0.00% | `insufficient_data` |
| `R15` (analogy) | 3 | 54 | 0 | 280 | 0 | 0.00% | `dead` |
| `R16` (framer_1d) | 4 | 103 | 0 | 280 | 0 | 0.00% | `dead` |
| `R20` (withheld_value_leakage) | 0 | 0 | 0 | 0 | 0 | 0.00% | `insufficient_data` |
| `R21` (effective_parameter_count) | 0 | 0 | 0 | 0 | 0 | 0.00% | `insufficient_data` |
| `R22` (apparatus_meta_runner) | 157 | 1527 | 0 | 511 | 0 | 0.00% | `dead` |
| `R23` (sparse_cell_exclusion) | 157 | 1527 | 0 | 511 | 0 | 0.00% | `dead` |
| `R24` (feature_bump_pattern) | 0 | 0 | 0 | 0 | 0 | 0.00% | `insufficient_data` |
| `GP-076` (predictive_divergence_sweep) | 0 | 0 | 0 | 0 | 0 | 0.00% | `insufficient_data` |

## Honest caveats

- score_lift not yet computed — needs join with per-iter score deltas + mutator briefing context. v1.0 surfaces engagement + hit rate (deterministic).
- Cage-routed primitives without per-primitive findings logs treat engagement as the finding signal (hit_rate==1.0 when engaged>0).
- verdict bands are placeholders without action_rate / score_lift; promote primitives to load_bearing only when those metrics ship.

