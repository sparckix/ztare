# H80 Neural Basin Jaccard Graph

Recorded: `2026-05-11`

Verdict: `jaccard_basin_navigation_built_not_evidence`

- nodes: `245`
- edges: `815`
- components: `1`
- visualization: `analytics/public/queries/neural_hunt/h80_neural_basin_jaccard_graph_2026_05_11.html`

## Bridge Candidates

| similarity | source | target | tags |
|---:|---|---|---|
| 0.902 | `H74` h74_residual_cell_features_cached_2026_05_11 | `H75` h75_residual_cell_features_cached_2026_05_11 | `activation, packet_gate, schema_interface` |
| 0.684 | `H73` build_h73_h68_promotion_prompt_packet | `H75` build_h75_h68_doc_balanced_prompt_packet | `activation, jaccard_graph, literature_boundary, observability, packet_gate, schema_interface` |
| 0.620 | `H72` build_h72_h68_activation_prompt_packet | `H73` build_h73_h68_promotion_prompt_packet | `activation, jaccard_graph, literature_boundary, observability, packet_gate, schema_interface` |
| 0.611 | `H74` h74_residual_cell_feature_analysis_2026_05_11 | `H75` h75_residual_cell_feature_analysis_2026_05_11 | `activation, literature_boundary, packet_gate, response_mode` |
| 0.547 | `H72` build_h72_h68_activation_prompt_packet | `H75` build_h75_h68_doc_balanced_prompt_packet | `activation, jaccard_graph, literature_boundary, observability, packet_gate, schema_interface` |
| 0.531 | `H51` run_h51_datadecide_fixed_size_residual_map | `H52` run_h52_datadecide_fixed_size_residual_null_audit | `activation, law_curve` |
| 0.513 | `H41` run_h41_datadecide_boolq_axis_robustness | `H48` run_h48_datadecide_single_size_boolq_residual | `activation, observability, response_mode, schema_interface` |
| 0.500 | `H43` run_h43_olmo_public_boolq_projection | `run_h43b_olmo_public_boolq_proje` run_h43b_olmo_public_boolq_projection_sensitivity | `activation, law_curve, schema_interface` |
| 0.492 | `H73` h73_h68_promotion_prompt_packet_manifest_2026_05_11 | `H75` h75_h68_doc_balanced_prompt_packet_manifest_2026_05_11 | `jaccard_graph, literature_boundary, observability, packet_gate` |
| 0.492 | `H72` h72_h68_activation_prompt_packet_manifest_2026_05_11 | `H73` h73_h68_promotion_prompt_packet_manifest_2026_05_11 | `activation, jaccard_graph, literature_boundary, observability, packet_gate` |
| 0.487 | `H76` analyze_h76_h75_rank_delta_target_link | `H77` analyze_h77_h75_family_centered_signal | `activation, observability, response_mode` |
| 0.483 | `H41` run_h41_datadecide_boolq_axis_robustness | `H42` run_h42_datadecide_boolq_schema_artifact_audit | `activation, observability, response_mode, schema_interface` |
| 0.477 | `H39` run_h39_datadecide_size_conditioned_mode_flow | `H40` run_h40_datadecide_post_size_residual_axis | `activation, observability, response_mode, schema_interface` |
| 0.450 | `H37` run_h37_datadecide_response_residual_void | `H39` run_h39_datadecide_size_conditioned_mode_flow | `activation, literature_boundary, observability, response_mode` |
| 0.436 | `H22` h22_targeted_checkpoint_eval_packet_2026_05_08 | `H27` h27_cost_capped_checkpoint_eval_packet_2026_05_10 | `activation, observability, schema_interface` |
| 0.433 | `H40` run_h40_datadecide_post_size_residual_axis | `H41` run_h41_datadecide_boolq_axis_robustness | `activation, observability, response_mode, schema_interface` |
| 0.429 | `H72` h72_h68_activation_prompt_packet_2026_05_11 | `H73` h73_h68_promotion_prompt_packet_2026_05_11 | `activation, jaccard_graph, literature_boundary, packet_gate, schema_interface` |
| 0.429 | `H41` h41_datadecide_boolq_axis_robustness_2026_05_10 | `H42` h42_datadecide_boolq_schema_artifact_audit_2026_05_10 | `activation, observability, response_mode, schema_interface` |
| 0.425 | `run_h43b_olmo_public_boolq_proje` run_h43b_olmo_public_boolq_projection_sensitivity | `H54` run_h54_olmo_public_h53_signature_projection | `law_curve, response_mode, schema_interface` |
| 0.412 | `H72` h72_h68_activation_prompt_packet_manifest_2026_05_11 | `H75` h75_h68_doc_balanced_prompt_packet_manifest_2026_05_11 | `jaccard_graph, literature_boundary, observability, packet_gate` |

## Frontier Bridge Candidates

These are cross-era traversal candidates from H72+ activation/packet work back into H31-H66 response/schema/law basins. They are not evidence; each requires the listed discriminator.

| score | similarity | recent | older | shared | complement | discriminator |
|---:|---:|---|---|---|---|---|
| 0.436 | 0.221 | `H78` run_h78_family_controlled_activation_evaluator | `H39` run_h39_datadecide_size_conditioned_mode_flow | `activation, response_mode, schema_interface` | `literature_boundary, observability, packet_gate` | Does the recent activation/packet artifact predict a held-out response/schema residual that the older artifact measured, after controlling for family and checkpoint maturity? |
| 0.415 | 0.240 | `H77` analyze_h77_h75_family_centered_signal | `H55` run_h55_olmo_public_panel_schema_split | `activation, observability, response_mode` | `schema_interface` | Does the recent activation/packet artifact predict a held-out response/schema residual that the older artifact measured, after controlling for family and checkpoint maturity? |
| 0.410 | 0.165 | `H75` build_h75_h68_doc_balanced_prompt_packet | `H48` run_h48_datadecide_single_size_boolq_residual | `activation, observability, schema_interface` | `jaccard_graph, law_curve, literature_boundary, packet_gate, response_mode` | Does the recent activation/packet artifact predict a held-out response/schema residual that the older artifact measured, after controlling for family and checkpoint maturity? |
| 0.408 | 0.233 | `H76` analyze_h76_h75_rank_delta_target_link | `H55` run_h55_olmo_public_panel_schema_split | `activation, observability, response_mode` | `schema_interface` | Does the recent activation/packet artifact predict a held-out response/schema residual that the older artifact measured, after controlling for family and checkpoint maturity? |
| 0.405 | 0.140 | `H75` build_h75_h68_doc_balanced_prompt_packet | `H31` run_h31_source_state_acquisition_matrix | `activation, literature_boundary, observability, packet_gate, schema_interface` | `jaccard_graph, response_mode` | Does the recent activation/packet artifact predict a held-out response/schema residual that the older artifact measured, after controlling for family and checkpoint maturity? |
| 0.405 | 0.110 | `H79` h79_learning_mechanics_positioning_2026_05_11 | `H38` h38_learning_mechanics_pioneer_pattern_map_2026_05_10 | `activation, jaccard_graph, law_curve, literature_boundary, response_mode` | `observability, packet_gate, schema_interface` | Does the recent activation/packet artifact predict a held-out response/schema residual that the older artifact measured, after controlling for family and checkpoint maturity? |
| 0.405 | 0.190 | `H78` run_h78_family_controlled_activation_evaluator | `H40` run_h40_datadecide_post_size_residual_axis | `activation, response_mode, schema_interface` | `law_curve, observability, packet_gate` | Does the recent activation/packet artifact predict a held-out response/schema residual that the older artifact measured, after controlling for family and checkpoint maturity? |
| 0.404 | 0.189 | `H75` build_h75_h68_doc_balanced_prompt_packet | `H55` run_h55_olmo_public_panel_schema_split | `activation, observability, schema_interface` | `jaccard_graph, literature_boundary, packet_gate, response_mode` | Does the recent activation/packet artifact predict a held-out response/schema residual that the older artifact measured, after controlling for family and checkpoint maturity? |
| 0.404 | 0.254 | `H78` run_h78_family_controlled_activation_evaluator | `H45` run_h45_olmo_public_level_rate_sensitivity | `response_mode, schema_interface` | `activation, law_curve, literature_boundary, packet_gate` | Does the recent activation/packet artifact predict a held-out response/schema residual that the older artifact measured, after controlling for family and checkpoint maturity? |
| 0.399 | 0.194 | `H75` build_h75_h68_doc_balanced_prompt_packet | `H56` run_h56_olmo_packet_schema_readiness_audit | `activation, packet_gate, schema_interface` | `jaccard_graph, law_curve, literature_boundary, observability` | Does the recent activation/packet artifact predict a held-out response/schema residual that the older artifact measured, after controlling for family and checkpoint maturity? |
| 0.398 | 0.183 | `H78` run_h78_family_controlled_activation_evaluator | `H55` run_h55_olmo_public_panel_schema_split | `activation, response_mode, schema_interface` | `observability, packet_gate` | Does the recent activation/packet artifact predict a held-out response/schema residual that the older artifact measured, after controlling for family and checkpoint maturity? |
| 0.397 | 0.157 | `H75` build_h75_h68_doc_balanced_prompt_packet | `H39` run_h39_datadecide_size_conditioned_mode_flow | `activation, literature_boundary, observability, schema_interface` | `jaccard_graph, packet_gate, response_mode` | Does the recent activation/packet artifact predict a held-out response/schema residual that the older artifact measured, after controlling for family and checkpoint maturity? |
| 0.396 | 0.181 | `H78` run_h78_family_controlled_activation_evaluator | `H48` run_h48_datadecide_single_size_boolq_residual | `activation, response_mode, schema_interface` | `law_curve, observability, packet_gate` | Does the recent activation/packet artifact predict a held-out response/schema residual that the older artifact measured, after controlling for family and checkpoint maturity? |
| 0.394 | 0.219 | `H75` build_h75_h68_doc_balanced_prompt_packet | `H64` run_h64_h62_public_heldout_contrast_audit | `literature_boundary, packet_gate, schema_interface` | `activation, jaccard_graph, observability` | Does the recent activation/packet artifact predict a held-out response/schema residual that the older artifact measured, after controlling for family and checkpoint maturity? |
| 0.393 | 0.148 | `H75` build_h75_h68_doc_balanced_prompt_packet | `H42` run_h42_datadecide_boolq_schema_artifact_audit | `activation, observability, schema_interface` | `jaccard_graph, law_curve, literature_boundary, packet_gate, response_mode` | Does the recent activation/packet artifact predict a held-out response/schema residual that the older artifact measured, after controlling for family and checkpoint maturity? |

## Overclusters

| H pair | edges | mean similarity |
|---|---:|---:|
| `H62 ↔ H64` | 12 | 0.183 |
| `H74 ↔ H75` | 11 | 0.433 |
| `H13 ↔ H14` | 7 | 0.173 |
| `H31 ↔ H32` | 6 | 0.164 |
| `H28 ↔ H31` | 6 | 0.157 |
| `H72 ↔ H73` | 5 | 0.395 |
| `H73 ↔ H75` | 5 | 0.390 |
| `H60 ↔ H62` | 5 | 0.371 |
| `H72 ↔ H75` | 5 | 0.335 |
| `H68 ↔ H74` | 5 | 0.310 |
| `H54 ↔ H55` | 5 | 0.247 |
| `H61 ↔ H62` | 5 | 0.224 |
| `H12 ↔ H13` | 5 | 0.182 |
| `H68 ↔ H73` | 5 | 0.165 |
| `H63 ↔ H65` | 5 | 0.115 |
| `H44 ↔ H45` | 4 | 0.386 |
| `H68 ↔ H75` | 4 | 0.321 |
| `H76 ↔ H77` | 4 | 0.217 |
| `H43 ↔ h43b_olmo_public_boolq_projectio` | 4 | 0.207 |
| `H39 ↔ H47` | 4 | 0.203 |

## Anti-Tautology Read

High similarity means shared vocabulary, not shared mechanism. Use bridge candidates only when they propose a new discriminator. Current expected use: connect H75/H78 activation-contract artifacts back to H50-H55 response/schema surfaces, then ask what held-out feature would separate family/schema compression from checkpoint residual geometry.
