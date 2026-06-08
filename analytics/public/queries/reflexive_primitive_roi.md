# Reflexive Primitive ROI Scorecard

_Generated 2026-06-04T21:03:16.833900+00:00_  
_Since:_ 2026-05-07T21:03:16.715989+00:00  
_Projects scanned:_ 160

## By verdict

| Verdict | Count |
|---|---:|
| `insufficient_data` | 18 |

## Per primitive

| Primitive | Eligible projects | Eligible iters | Engaged | Refused | Findings | Engagement rate | Verdict |
|---|---:|---:|---:|---:|---:|---:|---|
| `contract_adherence` (contract_adherence) | 160 | 4 | 651 | 0 | 651 | 16275.00% | `insufficient_data` |
| `GP-180` (dag_steering) | 24 | 0 | 345 | 0 | 345 | 0.00% | `insufficient_data` |
| `R15` (analogy) | 3 | 0 | 98 | 0 | 98 | 0.00% | `insufficient_data` |
| `R13` (substrate_critic) | 129 | 4 | 4 | 8 | 4 | 100.00% | `insufficient_data` |
| `R14` (noise_profile) | 129 | 4 | 4 | 8 | 4 | 100.00% | `insufficient_data` |
| `R16` (framer_1d) | 4 | 0 | 3 | 0 | 3 | 0.00% | `insufficient_data` |
| `R8` (feature_coverage_adequacy) | 0 | 0 | 0 | 0 | 0 | 0.00% | `insufficient_data` |
| `R9` (target_convention_homogeneity) | 0 | 0 | 0 | 0 | 0 | 0.00% | `insufficient_data` |
| `R10` (cross_class_extrapolation) | 160 | 4 | 0 | 4 | 0 | 0.00% | `insufficient_data` |
| `R11` (per_class_mre_ceiling) | 3 | 0 | 0 | 0 | 0 | 0.00% | `insufficient_data` |
| `R12` (symbolic_logic_cage) | 0 | 0 | 0 | 0 | 0 | 0.00% | `insufficient_data` |
| `R20` (withheld_value_leakage) | 0 | 0 | 0 | 0 | 0 | 0.00% | `insufficient_data` |
| `R21` (effective_parameter_count) | 0 | 0 | 0 | 0 | 0 | 0.00% | `insufficient_data` |
| `R22` (apparatus_meta_runner) | 160 | 4 | 0 | 4 | 0 | 0.00% | `insufficient_data` |
| `R23` (sparse_cell_exclusion) | 160 | 4 | 0 | 4 | 0 | 0.00% | `insufficient_data` |
| `R24` (feature_bump_pattern) | 0 | 0 | 0 | 0 | 0 | 0.00% | `insufficient_data` |
| `ansatz_survivor` (ansatz_survivor) | 160 | 4 | 0 | 4 | 0 | 0.00% | `insufficient_data` |
| `GP-076` (predictive_divergence_sweep) | 0 | 0 | 0 | 0 | 0 | 0.00% | `insufficient_data` |

## Honest caveats

- score_lift not yet computed — needs join with per-iter score deltas + mutator briefing context. v1.0 surfaces engagement + hit rate (deterministic).
- Cage-routed primitives without per-primitive findings logs treat engagement as the finding signal (hit_rate==1.0 when engaged>0).
- verdict bands are placeholders without action_rate / score_lift; promote primitives to load_bearing only when those metrics ship.

