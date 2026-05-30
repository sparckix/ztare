# Reflexive Primitive ROI Scorecard

_Generated 2026-05-06T17:49:41.815019+00:00_  
_Since:_ 2026-04-08T17:49:41.758900+00:00  
_Projects scanned:_ 156

## By verdict

| Verdict | Count |
|---|---:|
| `dead` | 7 |
| `insufficient_data` | 7 |
| `decorative_candidate` | 2 |
| `engagement_high` | 2 |

## Per primitive

| Primitive | Eligible projects | Eligible iters | Engaged | Refused | Findings | Engagement rate | Verdict |
|---|---:|---:|---:|---:|---:|---:|---|
| `R13` (substrate_critic) | 128 | 1734 | 663 | 226 | 1 | 38.24% | `decorative_candidate` |
| `R14` (noise_profile) | 128 | 1734 | 663 | 226 | 1 | 38.24% | `decorative_candidate` |
| `contract_adherence` (contract_adherence) | 156 | 1881 | 593 | 0 | 593 | 31.53% | `engagement_high` |
| `GP-180` (dag_steering) | 22 | 438 | 312 | 0 | 312 | 71.23% | `engagement_high` |
| `ansatz_survivor` (ansatz_survivor) | 156 | 1881 | 16 | 491 | 0 | 0.85% | `dead` |
| `R8` (feature_coverage_adequacy) | 0 | 0 | 0 | 0 | 0 | 0.00% | `insufficient_data` |
| `R9` (target_convention_homogeneity) | 0 | 0 | 0 | 0 | 0 | 0.00% | `insufficient_data` |
| `R10` (cross_class_extrapolation) | 156 | 1881 | 0 | 444 | 0 | 0.00% | `dead` |
| `R11` (per_class_mre_ceiling) | 5 | 66 | 0 | 294 | 0 | 0.00% | `dead` |
| `R12` (symbolic_logic_cage) | 0 | 0 | 0 | 0 | 0 | 0.00% | `insufficient_data` |
| `R15` (analogy) | 8 | 110 | 0 | 325 | 0 | 0.00% | `dead` |
| `R16` (framer_1d) | 4 | 103 | 0 | 280 | 0 | 0.00% | `dead` |
| `R20` (withheld_value_leakage) | 0 | 0 | 0 | 0 | 0 | 0.00% | `insufficient_data` |
| `R21` (effective_parameter_count) | 0 | 0 | 0 | 0 | 0 | 0.00% | `insufficient_data` |
| `R22` (apparatus_meta_runner) | 156 | 1881 | 0 | 444 | 0 | 0.00% | `dead` |
| `R23` (sparse_cell_exclusion) | 156 | 1881 | 0 | 444 | 0 | 0.00% | `dead` |
| `R24` (feature_bump_pattern) | 0 | 0 | 0 | 0 | 0 | 0.00% | `insufficient_data` |
| `GP-076` (predictive_divergence_sweep) | 0 | 0 | 0 | 0 | 0 | 0.00% | `insufficient_data` |

## Honest caveats

- score_lift not yet computed — needs join with per-iter score deltas + mutator briefing context. v1.0 surfaces engagement + hit rate (deterministic).
- Cage-routed primitives without per-primitive findings logs treat engagement as the finding signal (hit_rate==1.0 when engaged>0).
- verdict bands are placeholders without action_rate / score_lift; promote primitives to load_bearing only when those metrics ship.

