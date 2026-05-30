# Cross-Audit Synthesis Dashboard

_Generated 2026-05-09T23:24:02.295716+00:00_  
_Scorecards joined:_ 8  _Entities flagged:_ 44  _Convergent signals (≥2 scorecards):_ 9

## Convergent signals (≥2 independent scorecards)

| Severity | Kind | Entity | # sources | Sources | Detail |
|---|---|---|---:|---|---|
| `warn` | `primitive` | `R10 (cross_class_extrapolation)` | 2 | gate_telemetry, primitive_roi | verdict=dead engagement=0.00% engaged=0 refused=444 | gate_telemetry alias of cross_class_extrapolation → R10_cross_class_extrapolation (count=552) | gate_telemetry alias of per_class_farther_tail → R |
| `warn` | `primitive` | `R11 (per_class_mre_ceiling)` | 2 | gate_telemetry, primitive_roi | verdict=dead engagement=0.00% engaged=0 refused=294 | gate_telemetry alias of cross_class_extrapolation → R11_per_class_mre_ceiling (count=552) | gate_telemetry alias of per_class_farther_tail → R11_p |
| `warn` | `primitive` | `R13 (substrate_critic)` | 2 | gate_telemetry, primitive_roi | verdict=decorative_candidate engagement=38.24% engaged=663 refused=226 | gate_telemetry alias of substrate_critic → R13_substrate_critic_post_fit (count=552) | gate_telemetry alias of substrate_critic |
| `warn` | `primitive` | `R14 (noise_profile)` | 2 | gate_telemetry, primitive_roi | verdict=decorative_candidate engagement=38.24% engaged=663 refused=226 | gate_telemetry alias of noise_profile → R14_noise_profile_post_fit (count=552) | gate_telemetry alias of noise_profile → R14_no |
| `warn` | `primitive` | `R15 (analogy)` | 2 | gate_telemetry, primitive_roi | verdict=dead engagement=0.00% engaged=0 refused=325 | gate_telemetry alias of analogy → R15_analogy (count=552) |
| `warn` | `primitive` | `R16 (framer_1d)` | 2 | gate_telemetry, primitive_roi | verdict=dead engagement=0.00% engaged=0 refused=280 | gate_telemetry alias of framer_1d → R16_framer_pre_fit (count=552) |
| `warn` | `primitive` | `R22 (apparatus_meta_runner)` | 2 | gate_telemetry, primitive_roi | verdict=dead engagement=0.00% engaged=0 refused=444 | gate_telemetry alias of apparatus_meta_runner → R22_apparatus_meta_runner (count=552) |
| `warn` | `primitive` | `R23 (sparse_cell_exclusion)` | 2 | gate_telemetry, primitive_roi | verdict=dead engagement=0.00% engaged=0 refused=444 | gate_telemetry alias of sparse_cell_exclusion → R23_sparse_cell_exclusion (count=552) |
| `warn` | `target` | `TrackBProfileDecompositionObligation` | 2 | endpoint_compression, triangulation | compounding_score=4 events=1 | GP-223 Layer 3 candidate: field=threshold_defect_of_family_no_arbitrage pattern=X_of_Y |

## Top single-source flags

| Kind | Entity | # flags | Sources |
|---|---|---:|---|
| `gate_name` | `cross_class_extrapolation` | 2 | gate_telemetry |
| `primitive` | `R24 (feature_bump_pattern)` | 2 | gate_telemetry |
| `gate_name` | `noise_profile` | 2 | gate_telemetry |
| `gate_name` | `per_class_farther_tail` | 2 | gate_telemetry |
| `gate_name` | `substrate_critic` | 2 | gate_telemetry |
| `primitive` | `ansatz_survivor` | 1 | primitive_roi |
| `seam` | `GP-130` | 1 | seam_health |
| `seam` | `GP-140` | 1 | seam_health |
| `seam` | `GP-173` | 1 | seam_health |
| `seam` | `GP-188` | 1 | seam_health |
| `seam` | `GP-192` | 1 | seam_health |
| `miner` | `scripts/mining/mine_climb_triggers.py` | 1 | miner_roi |
| `miner` | `scripts/mining/mine_pivot_effectiveness.py` | 1 | miner_roi |
| `miner` | `scripts/mining/mine_score_ceilings.py` | 1 | miner_roi |
| `miner` | `scripts/mining/mine_judge_stratified.py` | 1 | miner_roi |
| `miner` | `scripts/mining/mine_lollapalooza_hypothesis.py` | 1 | miner_roi |
| `miner` | `scripts/mining/mine_trajectories.py` | 1 | miner_roi |
| `miner` | `scripts/mining/mine_champion_trajectory_sequence.py` | 1 | miner_roi |
| `miner` | `scripts/mining/mine_cross_provider_classifier_agreement.py` | 1 | miner_roi |
| `miner` | `scripts/audits/audit_gate_coverage.py` | 1 | miner_roi |
| `miner` | `scripts/audits/audit_gate_effectiveness.py` | 1 | miner_roi |

