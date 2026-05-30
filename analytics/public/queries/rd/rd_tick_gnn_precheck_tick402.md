# RD Tick GNN Precheck

**Status:** `pass_warn`

Use top candidates as premise/navigation context only. Prefer atomic primitives and adapters; treat endpoint, event-per-node, and guard recommendations as danger/context unless separately justified.

## Overfit Guards

- `retraining_in_tick`: `False`
- `uses_frozen_packet`: `True`
- `gpu_validation_present`: `False`
- `non_ns_v52_guard_present`: `False`
- `endpoint_candidates_are_warnings`: `True`
- `event_per_node_tautology_is_warning`: `True`

## Packet

- `path`: `analytics/public/leanmill/results/v52_ns_advisory_packet.json`
- `version`: `gnn_lemma_relevance_v52_ns_advisory_packet_2026_05_11`
- `best_epoch`: `40`
- `best_val_hit10`: `0.5357142857142857`
- `n_pairs_extracted`: `300`
- `n_pairs_with_lemmas_in_vocab`: `192`

## Remote CPU Sanity

- `available`: `True`
- `path`: `analytics/public/leanmill/results/v52_residual_hetero_gnn_remote_cpu_sanity.json`

## Graph

- `path`: `projects/ns_millennium_hunt/workspace/queries/ns_l3a_same_tree_obligation_graph.json`
- `missing_tags`: `[]`
- `thin_tags`: `[]`
- atomic nodes detected:
  - `FreshComparablePacketForNonflatNonInheritedNode`
  - `FreshComparablePacketForNonflatNonInheritedNode.nonflat`
  - `FreshComparablePacketForNonflatNonInheritedNode.inherited`
  - `FreshComparablePacketForNonflatNonInheritedNode.flat`
  - `FreshComparablePacketForNonflatNonInheritedNode.partitionFixedBeforeRadiusAccounting`
  - `FreshComparablePacketForNonflatNonInheritedNode.inheritedAlternativePreselected`
  - `FreshComparablePacketForNonflatNonInheritedNode.flatAlternativePreselected`
  - `FreshComparablePacketForNonflatNonInheritedNode.freshEvent`
  - `FreshComparablePacketForNonflatNonInheritedNode.frequencyComparableToNodeRadius`
  - `FreshComparablePacketForNonflatNonInheritedNode.weightComparableToNodeRadius`
  - `FreshComparablePacketForNonflatNonInheritedNode.packetCostIsIndependentPDEBudget`
  - `FreshComparablePacketForNonflatNonInheritedNode.gainControlsNodeBeta`
  - `FreshComparablePacketForNonflatNonInheritedNode.freshPacketAtComparableFrequency`
  - `FreshComparablePacketForNonflatNonInheritedNode.generatedFromDuhamelBernsteinSource`
  - `FreshComparablePacketForNonflatNonInheritedNode.generatedBeforeRadiusAccounting`
  - `FreshComparablePacketForNonflatNonInheritedNode.sameCarrierAsNormalizedExcessTree`
  - `FreshComparablePacketForNonflatNonInheritedNode.notDefinedFromBadCenterBetaRadiusSum`
  - `freshFrequencyEventSameTreeLockUsesDisplayedSubprimitives`

## v5.3 Guarded Filter

- `available`: `True`
- `status`: `pass_guarded_filter`
- `path`: `analytics/public/leanmill/results/v53_guarded_advisory_filter.json`
- raw hit@10: `0.625`
- filtered hit@10: `0.625`
- raw clean actionability: `0.19166666666666668`
- filtered clean actionability: `0.5`
- raw danger fraction: `0.325`
- filtered danger fraction: `0.05`

## v5.4 Typed-Symmetry Audit

- `available`: `True`
- `status`: `warn_typed_symmetry_audit`
- `path`: `analytics/public/leanmill/results/v54_typed_symmetry_audit.json`
- `missing_clean_required_roles`: `['bounded_fanout', 'pressure_lock']`
- `wrong_equivariance_risks`: `['duhamel_budget_visible_without_clean_pressure_lock', 'fresh_packet_visible_without_clean_bounded_fanout']`
- `collapse_risk_count`: `0`

## v5.5 Typed-Symmetry Canary

- `available`: `True`
- `status`: `pass_typed_symmetry_canary`
- `path`: `analytics/public/leanmill/results/v55_typed_symmetry_perturbation_canary.json`
- `namespace_prefix` role preservation: `1.0`
- `binder_suffix` role preservation: `1.0`
- `semantic_alias` role preservation: `0.8583333333333334`
- `roadmap_decision`: `{'reason': 'no measured typed-symmetry gap beyond v5.4 role coverage', 'v6_generic_equivariant_architecture': 'blocked', 'v6_typed_symmetry_residual': 'not_yet_justified'}`

## v5.4 Audit on v5.6 Repaired Queue

- `available`: `True`
- `status`: `pass_typed_symmetry_audit`
- `path`: `analytics/public/leanmill/results/v54_on_v56_top7_typed_symmetry_audit.json`
- `missing_clean_required_roles`: `[]`
- `wrong_equivariance_risks`: `[]`
- `collapse_risk_count`: `0`
- `explicit_role_bridge_count`: `37`

## v5.5 Canary on v5.6 Repaired Queue

- `available`: `True`
- `status`: `pass_typed_symmetry_canary`
- `path`: `analytics/public/leanmill/results/v55_on_v56_top7_typed_symmetry_perturbation_canary.json`
- `semantic_alias` role preservation: `0.8988095238095238`

## v5.6 Typed-Role Repair Queue

- `available`: `True`
- `status`: `typed_role_repaired_queue`
- `path`: `analytics/public/leanmill/results/v56_typed_role_repaired_queue.json`
- `missing_roles_repaired`: `['bounded_fanout', 'pressure_lock']`
- repair `FreshFrequencyBoundedFanoutNoLogReuse` `structure` line `4438`
- repair `FreshFrequencyPressureDuhamelSameCarrierLock` `structure` line `4285`

## v5.7 Patch Attribution

- `available`: `True`
- `status`: `seed_created_no_attribution_yet`
- `path`: `analytics/public/leanmill/results/v57_patch_attribution_seed.json`
- `rows`: `12`
- `successful_attributions`: `0`
- `anti_overfit_rule`: `Do not train or promote a GNN version from plausibility metrics alone. Require nonzero compile-safe patch attribution or keep the lane advisory.`

## v6 Typed-Symmetry Residual Contract

- `available`: `True`
- `status`: `design_eligible_after_role_repair_no_training`
- `path`: `analytics/public/leanmill/results/v60_typed_symmetry_residual_contract.json`
- `architecture_decision`: `{'base': 'v4.1_or_v5.2_scores', 'consumption_surface': 'v5.3_guarded_queue', 'generic_e3_equivariant_gnn': 'blocked', 'plain_gnn_from_scratch': 'blocked', 'reason': 'raw typed roles were missing, same-tree role repair recovers coverage, and semantic alias robustness now passes after role-map repair; the justified model is still a residual over typed role metadata, not a coordinate equivariant CFD layer', 'typed_symmetry_residual': 'design_eligible_after_role_repair_no_training'}`
- `next_no_gpu_step`: `Stage a small external LeanRank/LeanDojo benchmark sample and evaluate endpoint-occluded generated-patch attribution before any training proposal.`

## v6.1 Typed-Obligation Hypergraph Contract

- `available`: `True`
- `status`: `contract_ready_no_training`
- `path`: `analytics/public/leanmill/results/v61_typed_obligation_hypergraph_contract.json`
- `training_allowed`: `False`
- `successful_patch_attributions`: `4`
- `general_purpose_use`: `An RD should embed a substrate by mapping its carrier, index/scale, incidence, budget, lock, freshness, adapter, and guard roles into the library, then running the same endpoint-occluded and attribution gates before training.`

## v6.2 Typed-Obligation Work Packet

- `available`: `True`
- `status`: `work_packet_ready_advisory_only`
- `path`: `analytics/public/leanmill/results/v62_ns_typed_obligation_work_packet.json`
- `training_allowed`: `False`
- tactical `single_positive_patch_attribution_exists` `continue_local_ns_not_training`
- tactical `fresh_packet_covered_but_needs_side_condition_audit` `work_locally_not_endpoint`
- tactical `beta_payment_covered_but_needs_side_condition_audit` `work_locally_not_endpoint`
- tactical `bounded_fanout_covered_but_needs_side_condition_audit` `work_locally_not_endpoint`
- tactical `pressure_lock_covered_but_needs_side_condition_audit` `work_locally_not_endpoint`
- tactical `fresh_packet_creation_is_the_atomic_ns_test` `primary_ns_probe`
- tactical `semantic_alias_brittleness` `generality_blocker`

## v6.4 Tri-Arm Usefulness Pilot

- `available`: `True`
- `status`: `three_edit_pilot_not_statistical_evidence`
- `path`: `analytics/public/leanmill/results/v64_tri_arm_usefulness_pilot.json`
- `arms`: `{'graph_alone': {'pilot_credit': 'partial'}, 'gnn_alone': {'pilot_credit': 'weak_partial'}, 'gnn_plus_graph': {'pilot_credit': 'positive'}}`
- `pilot_read`: Across three local compile-checked edits, GNN+graph beat either arm alone because it combined graph-local tagged declarations with typed-obligation ranking that chose smaller side-condition splits and structured-lock wiring. This is not enough to train or promote; it justifies using the combo for the next NS local edit while continuing attribution.

## Compile-Checked Patch Attributions

- `analytics/public/leanmill/results/v63_gnn_graph_combo_patch_attribution.json` status `positive_compile_checked_patch_attribution` compile `True`
  - `NonflatInheritedFlatBadNodePartition`
  - `FreshFrequencyEventSelectionRule`
  - `FreshFrequencyPacketPaymentCarrierLocks`
  - `FreshComparablePacketForNonflatNonInheritedNode.ofPartitionSelectionPayment`
  - `FreshComparablePacketSideConditionAudit`
  - `FreshComparablePacketSideConditionAudit.toFreshComparablePacket`
- `analytics/public/leanmill/results/v65_gnn_graph_combo_beta_payment_patch_attribution.json` status `positive_compile_checked_patch_attribution` compile `True`
  - `FreshPacketGainPaysNonflatBeta.ofFreshComparablePacket`
  - `FreshPacketGainPaysNonflatBeta.ofFreshPacketSideConditionAudit`
- `analytics/public/leanmill/results/v66_gnn_graph_combo_structured_lock_patch_attribution.json` status `positive_compile_checked_patch_attribution` compile `True`
  - `FreshPacketGainPaysNonflatBeta.ofFreshPacketSideConditionAuditAndLocks`
- `analytics/public/leanmill/results/v70_non_ns_generated_patch_attribution.json` status `positive_compile_checked_generated_non_ns_patch_attribution` compile `True`
  - `forwardChar_mul_conj_self`
  - `trigPoly_packet_mul_conj_split`
- `analytics/public/leanmill/results/v86_gnn_graph_combo_pressure_duhamel_audit_patch_attribution.json` status `positive_compile_checked_ns_patch_attribution` compile `True`
  - `FreshFrequencyPressureTailEventAssignment`
  - `FreshFrequencyDuhamelErrorEventAssignment`
  - `LerayHeatFreshFrequencyCarrierCompatibility`
  - `FreshFrequencyPressureDuhamelBudgetReceipt`
  - `FreshFrequencyPressureDuhamelSameCarrierAudit`
  - `FreshFrequencyPressureDuhamelSameCarrierLock.ofAudit`
  - `PressureDuhamelSameCarrierLock.ofFreshFrequencyLock`
- `analytics/public/leanmill/results/v87_non_ns_ortho_generated_patch_attribution.json` status `positive_compile_checked_generated_non_ns_patch_attribution` compile `True`
  - `forwardChar_mul_conj_self`
  - `forwardChar_zero`
  - `forwardChar_mul_conj_self_eq_one`
- `analytics/public/leanmill/results/v89_non_ns_charmulconj_generated_patch_attribution.json` status `positive_compile_checked_generated_non_ns_patch_attribution` compile `True`
  - `forwardChar_sum_sub`
  - `star_exp_forwardChar_exponent`
- `analytics/public/leanmill/results/v91_ns_leray_heat_tent_geometry_patch_attribution.json` status `positive_compile_checked_ns_patch_attribution` compile `True`
  - `LerayHeatFreshFrequencyEventTentGeometry`
  - `LerayHeatFreshFrequencyCarrierCompatibility.ofEventTentGeometry`

## v6.7/v7 Roadmap

- `available`: `True`
- `status`: `roadmap_no_training`
- `path`: `analytics/public/leanmill/results/v67_gnn_roadmap.json`
- `next_versions`: `{'v6_7': {'name': 'endpoint_occluded_attribution_harness', 'gpu': False, 'goal': 'Recover compile-checked local cuts from frozen graph/GNN packets while hiding endpoint declarations and guard restatements.'}, 'v6_8': {'name': 'non_ns_role_map_canary', 'gpu': False, 'goal': 'Validate the role algebra on a non-NS Lean substrate before training.'}, 'v7': {'name': 'typed_obligation_incidence_residual_scorer', 'gpu': 'gated', 'learned_unit': '(proof_state, unmet_typed_obligation, candidate_adapter, attribution_context) -> usefulness + role_delta + risk_flags + side_conditions'}}`
- `gpu_trigger`: `['at least 8 compile-checked patch attributions', 'not all attributions from NS and at least one non-NS attribution is generated or patch-like, not only existing-proof attribution', 'endpoint-occluded held-out recovery >= 0.5', 'semantic alias robustness materially improves over v5.5', 'one non-NS role-map canary passes and one real non-NS Lean attribution is present', 'graph-alone, gnn-alone, and combo arms remain separately logged']`
- `do_not_train_yet`: `['three positive attributions are NS-local only', 'semantic alias canary is still brittle', 'non-NS role-map validation now includes one generated patch attribution, but the count is still too small and semantic-alias brittleness remains']`

## v6.7 Endpoint-Occluded Harness

- `available`: `True`
- `status`: `pass_endpoint_occluded_ns_pilot`
- `hit_at_3`: `1.0`
- `training_decision`: `still_blocked_until_non_ns_canary_and_more_patch_attributions`

## v6.8 Non-NS Role-Map Canary

- `available`: `True`
- `status`: `pass_synthetic_non_ns_role_canary`
- `substrates_tested`: `['probability_filtration', 'harmonic_analysis_tiles', 'category_diagram', 'optimization_projection']`
- `training_decision`: `blocked`

## v6.9 Real Non-NS Lean Canary

- `available`: `True`
- `status`: `pass_real_non_ns_lean_attribution_canary`
- `substrate`: `almost_periodic_harmonic_analysis`
- `role_hit_rate`: `1.0`
- `training_decision`: `blocked_but_non_ns_evidence_improved`

## v7.0 Non-NS Generated Patch

- `available`: `True`
- `status`: `positive_compile_checked_generated_non_ns_patch_attribution`
- `substrate`: `almost_periodic_harmonic_analysis`
- `compile_checked`: `True`
- `added_declarations`: `['forwardChar_mul_conj_self', 'trigPoly_packet_mul_conj_split']`

## v7.1 External Benchmark Intake

- `available`: `True`
- `status`: `partial_external_benchmarks_detected`
- `bench_root`: `analytics/public/leanmill/external_benchmarks`
- `training_decision`: `blocked_until_external_benchmark_sample_staged_and_evaluated`

## v7.2 MathlibGraph Baseline

- `available`: `True`
- `status`: `mathlibgraph_external_baseline_extracted`
- `network_r10`: `0.5200779274690902`
- `all_features_r10`: `0.5246824912435099`
- `hard_network_r10`: `0.5103782600858937`
- `hard_all_features_r10`: `0.5203356738855442`

## v7.3 Scientific-Yield Gate

- `available`: `True`
- `status`: `hold_gpu_continue_no_spend`
- `gpu_training_allowed`: `False`
- `novelty_claim_allowed`: `False`
- `evidence`: `{'action_delta_type_probe_contract': {'candidate_equals_target_self_matches_excluded': True, 'candidate_names_used_for_evaluation_only': True, 'candidate_names_used_for_scoring': False, 'full_tactic_trace': False, 'lean_environment_probe': True}, 'action_delta_type_probe_interpretation': 'This v10.4-lite probe asks whether Lean-derived type/action compatibility can replace bootstrap role edges.  Self-target matches are excluded, so success requires nontrivial interaction with another patch declaration in the row.', 'action_delta_type_probe_metrics': {'emitted_probe_count': 1790, 'hit_at_7': 0.75, 'mrr': 0.3379446138211382, 'nonself_exact_matches': 40, 'nonself_head_matches': 267, 'probe_count': 1790, 'row_count': 8}, 'action_probe_tie_audit_metrics': {'v107_tactic_probe': {'average_tie': {'hit_at_1': 0.0, 'hit_at_7': 0.125, 'mean_rank': 37.4375, 'mrr': 0.062461984954750374}, 'large_tie_rows_ge_10': 5, 'optimistic': {'hit_at_1': 0.625, 'hit_at_7': 0.75, 'mean_rank': 12.875, 'mrr': 0.6719304078014184}, 'worst_tie': {'hit_at_1': 0.0, 'hit_at_7': 0.125, 'mean_rank': 62.0, 'mrr': 0.05471346766554723}, 'zero_score_gold_tie_rows': 5}, 'v109_failure_taxonomy': {'average_tie': {'hit_at_1': 0.0, 'hit_at_7': 0.125, 'mean_rank': 37.4375, 'mrr': 0.062461984954750374}, 'large_tie_rows_ge_10': 5, 'optimistic': {'hit_at_1': 0.625, 'hit_at_7': 0.75, 'mean_rank': 12.875, 'mrr': 0.6719304078014184}, 'worst_tie': {'hit_at_1': 0.0, 'hit_at_7': 0.125, 'mean_rank': 62.0, 'mrr': 0.05471346766554723}, 'zero_score_gold_tie_rows': 5}, 'v110_failure_aware_raw': {'average_tie': {'hit_at_1': 0.125, 'hit_at_7': 0.75, 'mean_rank': 17.5, 'mrr': 0.38346633645202716}, 'large_tie_rows_ge_10': 1, 'optimistic': {'hit_at_1': 0.25, 'hit_at_7': 0.75, 'mean_rank': 17.75, 'mrr': 0.46236659220650284}, 'worst_tie': {'hit_at_1': 0.125, 'hit_at_7': 0.75, 'mean_rank': 18.5, 'mrr': 0.3552237350636457}, 'zero_score_gold_tie_rows': 0}}, 'action_selection_overfit_audit': {'decision': 'Do not promote v11.5 as a 10x result until it survives more rows and a name/alias/leave-domain stress. Use it as the next hypothesis.', 'global': {'hit_at_7_delta': 0.125, 'hybrid': {'hit_at_7': 0.875, 'mrr': 0.65, 'n': 8}, 'mrr_delta': 0.025000000000000022, 'v115': {'hit_at_7': 1.0, 'mrr': 0.675, 'n': 8}}, 'overfit_read': 'high_risk_single_row_gain', 'row_delta_summary': {'negative_row_ids': ['v91_ns_leray_heat_tent_geometry_patch_attribution'], 'negative_rows': 1, 'neutral_rows': 6, 'positive_row_ids': ['v87_non_ns_ortho_generated_patch_attribution'], 'positive_rows': 1}}, 'actual_declaration_pool_metrics': {'lexical_hit_at_1': 0.5, 'lexical_hit_at_7': 0.75, 'typed_hit_at_1': 0.25, 'typed_hit_at_7': 0.375}, 'antifailure_repair_router_contract': {'action_only_mode_nonbootstrap': True, 'gold_labels_used_for_evaluation_only': True, 'mixed_mode_uses_declaration_text_for_adapter_risk_prior': True, 'no_gpu': True, 'self_target_tautology_block_inherited_from_v104_v105': True}, 'antifailure_repair_router_interpretation': 'Raw action compatibility is positive but over-ranks context objects. The mixed anti-failure router tests whether adding explicit adapter/risk priors reduces that failure.  Because mixed mode uses declaration text, it is advisory and must be stress-tested under name anonymization before any stronger claim.', 'antifailure_repair_router_metrics': {'action_only': {'hit_at_7': 0.75, 'mrr': 0.5250554078014185, 'non_ns_hit_at_7': 1.0, 'ns_hit_at_7': 0.6, 'row_count': 8}, 'mixed_antifailure': {'hit_at_7': 0.5, 'mrr': 0.22277146464646463, 'non_ns_hit_at_7': 0.3333333333333333, 'ns_hit_at_7': 0.6, 'row_count': 8}}, 'combined_action_delta_router_contract': {'candidate_names_used_only_for_output_and_deterministic_tiebreak': True, 'gold_labels_used_for_evaluation_only': True, 'no_declaration_text_role_priors': True, 'no_gpu': True, 'self_target_tautology_block_inherited_from_component_probes': True}, 'combined_action_delta_router_interpretation': 'Combining observed Lean action channels is the right direction only if it beats the strongest single channel without using declaration-text role priors.  Penalized/set-cover variants test two anti-failure ideas: demote context-only structures and diversify the tail by observed action roles.', 'combined_action_delta_router_metrics': {'combined_penalized': {'hit_at_7': 0.75, 'mrr': 0.46296439230215086, 'non_ns_hit_at_7': 1.0, 'ns_hit_at_7': 0.6, 'row_count': 8}, 'combined_raw': {'hit_at_7': 0.75, 'mrr': 0.46296439230215086, 'non_ns_hit_at_7': 1.0, 'ns_hit_at_7': 0.6, 'row_count': 8}, 'setcover_tail': {'hit_at_7': 0.75, 'mrr': 0.5254643923021509, 'non_ns_hit_at_7': 1.0, 'ns_hit_at_7': 0.6, 'row_count': 8}}, 'compile_checked_patch_attributions': 8, 'compressed_affordance_policy_metrics': {'accepted_non_gold_progress_by_policy': {}, 'best_target_aware_budget10': {'policy': 'compressed_v115', 'success_count': 8}, 'best_target_aware_budget25': {'policy': 'compressed_v115', 'success_count': 8}, 'generic_budget10_success_count': 5, 'probe_count': 800, 'row_count': 8, 'sort_closure_count': 0}, 'compressed_affordance_policy_status': 'compressed_affordance_policy_eval_passed', 'convert_selectivity_audit_interpretation': "v11.9's bundle success is useful but not yet proof-quality evidence. The expanded action inventory creates many non-gold progress bundles, especially through convert-style actions.  The next experiment must capture before/after goal deltas and require role-compatible local side-condition progress before counting a convert bundle as success.", 'convert_selectivity_audit_metrics': {'candidate_with_progress_count': 117, 'overbroad_candidate_count': 65, 'v115_budget7_false_progress_count': 22, 'v115_budget7_progress_precision': 0.3888888888888889, 'v115_budget7_true_progress_count': 14}, 'discriminating_action_selection_interpretation': 'This tests action selection rather than action scoring. The router only inserts action candidates when Lean provides positive, discriminating evidence, while the hybrid retrieval+typed queue remains the fallback.', 'discriminating_action_selection_metrics': {'hit_at_1': 0.5, 'hit_at_7': 1.0, 'mean_first_gold_rank': 2.25, 'mrr': 0.675, 'row_count': 8}, 'endpoint_occluded_hit_at_3': 1.0, 'expanded_action_bundle_router_contract': {'bundle_success_requires_gold_candidate_and_observed_action_progress': True, 'fixed_probe_budgets': [7, 10, 25, 50, 'exhaustive'], 'no_gpu': True, 'no_training': True, 'unit': 'candidate_action_bundle'}, 'expanded_action_bundle_router_interpretation': 'Expanded actions make repair-bundle routing measurable.  The result should be read against the v11.8 ceiling: two rows still lack any gold progress witness, so no current router can exceed 6/8 without richer proof-state probes or new row annotations.', 'expanded_action_bundle_router_metrics': {'expanded_action_only': {'10': {'budget_success': 0.625, 'bundle_success_at_7': 0.625, 'mean_first_gold_repair_probe_count': 2.6, 'row_count': 8}, '25': {'budget_success': 0.75, 'bundle_success_at_7': 0.625, 'mean_first_gold_repair_probe_count': 4.666666666666667, 'row_count': 8}, '50': {'budget_success': 0.75, 'bundle_success_at_7': 0.625, 'mean_first_gold_repair_probe_count': 4.666666666666667, 'row_count': 8}, '7': {'budget_success': 0.625, 'bundle_success_at_7': 0.625, 'mean_first_gold_repair_probe_count': 2.6, 'row_count': 8}, 'exhaustive': {'budget_success': 0.75, 'bundle_success_at_7': 0.625, 'mean_first_gold_repair_probe_count': 4.666666666666667, 'row_count': 8}}, 'generic_fixed_action_order': {'10': {'budget_success': 0.5, 'bundle_success_at_7': 0.375, 'mean_first_gold_repair_probe_count': 4.5, 'row_count': 8}, '25': {'budget_success': 0.5, 'bundle_success_at_7': 0.375, 'mean_first_gold_repair_probe_count': 4.5, 'row_count': 8}, '50': {'budget_success': 0.625, 'bundle_success_at_7': 0.375, 'mean_first_gold_repair_probe_count': 9.0, 'row_count': 8}, '7': {'budget_success': 0.375, 'bundle_success_at_7': 0.375, 'mean_first_gold_repair_probe_count': 3.0, 'row_count': 8}, 'exhaustive': {'budget_success': 0.75, 'bundle_success_at_7': 0.375, 'mean_first_gold_repair_probe_count': 41.0, 'row_count': 8}}, 'hybrid_expanded_affordance': {'10': {'budget_success': 0.625, 'bundle_success_at_7': 0.625, 'mean_first_gold_repair_probe_count': 2.0, 'row_count': 8}, '25': {'budget_success': 0.625, 'bundle_success_at_7': 0.625, 'mean_first_gold_repair_probe_count': 2.0, 'row_count': 8}, '50': {'budget_success': 0.75, 'bundle_success_at_7': 0.625, 'mean_first_gold_repair_probe_count': 7.5, 'row_count': 8}, '7': {'budget_success': 0.625, 'bundle_success_at_7': 0.625, 'mean_first_gold_repair_probe_count': 2.0, 'row_count': 8}, 'exhaustive': {'budget_success': 0.75, 'bundle_success_at_7': 0.625, 'mean_first_gold_repair_probe_count': 7.5, 'row_count': 8}}, 'v115_expanded_affordance': {'10': {'budget_success': 0.75, 'bundle_success_at_7': 0.75, 'mean_first_gold_repair_probe_count': 2.0, 'row_count': 8}, '25': {'budget_success': 0.75, 'bundle_success_at_7': 0.75, 'mean_first_gold_repair_probe_count': 2.0, 'row_count': 8}, '50': {'budget_success': 0.75, 'bundle_success_at_7': 0.75, 'mean_first_gold_repair_probe_count': 2.0, 'row_count': 8}, '7': {'budget_success': 0.75, 'bundle_success_at_7': 0.75, 'mean_first_gold_repair_probe_count': 2.0, 'row_count': 8}, 'exhaustive': {'budget_success': 0.75, 'bundle_success_at_7': 0.75, 'mean_first_gold_repair_probe_count': 2.0, 'row_count': 8}}}, 'expanded_tactic_action_probe_contract': {'actions': ['exact_tac', 'apply_tac', 'convert_using1', 'have_fact'], 'actual_tactic_execution': True, 'candidate_equals_target_self_matches_excluded_from_progress': True, 'candidate_names_used_for_scoring': False, 'have_fact_success_not_counted_as_progress': True, 'no_gpu': True}, 'expanded_tactic_action_probe_interpretation': 'This extends the action inventory beyond rewrite/simp.  The useful observable is the number of rows whose gold declarations now have positive non-self action progress, not raw candidate hit@7.', 'expanded_tactic_action_probe_metrics': {'failure_class_counts': {'generic_tactic_failure': 1729, 'type_mismatch': 2809}, 'gold_progress_witness_rate': 0.75, 'hit_at_7': 0.25, 'mrr': 0.09923746555584259, 'ok_by_action': {'apply_tac': 61, 'convert_using1': 710, 'exact_tac': 61, 'have_fact': 1790}, 'ok_tactic_attempt_count': 2622, 'probe_count': 1790, 'progress_by_action': {'apply_tac': 40, 'convert_using1': 689, 'exact_tac': 40}, 'progress_tactic_attempt_count': 769, 'row_count': 8, 'rows_with_gold_progress_witness': 6, 'tactic_attempt_count': 7160}, 'focused_proof_state_witness_interpretation': "The focused witness probe turns v11.9's progress-like bundles into quality-filtered proof-state deltas.  If small/selective filters destroy bundle success, v11.9 was mostly broad convert progress; if they preserve success while raising precision, the controller is a stronger novelty candidate.", 'focused_proof_state_witness_metrics': {'closed_only': {'bundle_success_at_7': 0.125, 'false_kept_count': 12, 'precision': 0.3333333333333333, 'true_kept_count': 6}, 'selective_action': {'bundle_success_at_7': 0.5, 'false_kept_count': 9, 'precision': 0.5, 'true_kept_count': 9}, 'small_and_selective': {'bundle_success_at_7': 0.5, 'false_kept_count': 8, 'precision': 0.5, 'true_kept_count': 8}, 'small_delta': {'bundle_success_at_7': 0.5, 'false_kept_count': 12, 'precision': 0.45454545454545453, 'true_kept_count': 10}, 'success_any': {'bundle_success_at_7': 0.75, 'false_kept_count': 22, 'precision': 0.3888888888888889, 'true_kept_count': 14}}, 'full_goal_snapshot_witness_interpretation': "Full proof-state snapshots test whether the controller's emitted bundles create role-compatible local side conditions rather than only broad action success. Passing the strict filter would justify external public candidate-source integration; failing keeps the novelty claim paused and GPU blocked.", 'full_goal_snapshot_witness_metrics': {'closed_only': {'bundle_success_at_7': 0.125, 'false_kept_count': 12, 'precision': 0.3333333333333333, 'true_kept_count': 6}, 'role_compatible_snapshot': {'bundle_success_at_7': 0.75, 'false_kept_count': 22, 'precision': 0.3888888888888889, 'true_kept_count': 14}, 'small_snapshot': {'bundle_success_at_7': 0.5, 'false_kept_count': 12, 'precision': 0.45454545454545453, 'true_kept_count': 10}, 'strict_selective_snapshot': {'bundle_success_at_7': 0.5, 'false_kept_count': 8, 'precision': 0.5294117647058824, 'true_kept_count': 9}, 'strict_selective_sort_guarded_snapshot': {'bundle_success_at_7': 0.375, 'false_kept_count': 0, 'precision': 1.0, 'true_kept_count': 5}, 'strict_snapshot': {'bundle_success_at_7': 0.5, 'false_kept_count': 12, 'precision': 0.4782608695652174, 'true_kept_count': 11}, 'strict_sort_guarded_snapshot': {'bundle_success_at_7': 0.375, 'false_kept_count': 0, 'precision': 1.0, 'true_kept_count': 5}, 'success_any': {'bundle_success_at_7': 0.75, 'false_kept_count': 22, 'precision': 0.3888888888888889, 'true_kept_count': 14}}, 'full_goal_snapshot_witness_status': 'full_snapshot_witness_gate_failed', 'full_target_unit_rewrite_metrics': {'action_success_counts': {'apply_tac': 8, 'convert_using1': 8}, 'gold_witness_success_count': 8, 'gold_witness_success_rate': 1.0, 'probe_count': 24, 'row_count': 8, 'total_sort_closure_count': 0}, 'full_target_unit_rewrite_status': 'full_target_unit_rewrite_passed', 'generated_non_ns_patch_present': True, 'generated_non_ns_rows': 3, 'hybrid_repair_router_metrics': {'hybrid_hit_at_7': 0.875, 'hybrid_mean_first_gold_rank': 1.8571428571428572, 'hybrid_top1_gold': 0.5, 'lexical_hit_at_7': 0.75, 'lexical_mean_first_gold_rank': 9.0, 'lexical_top1_gold': 0.5, 'typed_hit_at_7': 0.375, 'typed_mean_first_gold_rank': 20.125, 'typed_top1_gold': 0.25}, 'label_blind_hard_decoy_decision': 'proxy_pass_but_gpu_still_blocked_by_structural_occlusion', 'label_blind_hard_decoy_metrics': {'all_pools_ge_50': True, 'all_pools_gt_7': True, 'hybrid_hit_at_7': 0.875, 'hybrid_mrr': 0.65, 'hybrid_top1': 0.5, 'lexical_hit_at_7': 0.75, 'lexical_mrr': 0.6328431372549019, 'lexical_top1': 0.5, 'min_pool_size': 50, 'row_count': 8, 'typed_hit_at_7': 0.375, 'typed_mrr': 0.34837213485455854, 'typed_top1': 0.25}, 'label_leakage_static_audit': {'pre_metric_prohibited_hit_count': 0, 'temporal_context_risk_count': 6}, 'label_leakage_static_audit_status': 'no_pre_metric_label_leakage_but_temporal_context_risk', 'lean_environment_rows_resolved': {'row_count': 8, 'rows_resolved': 8}, 'lean_expr_ast_graph_summary': {'ast_edge_count': 10302, 'ast_node_count': 10448, 'candidate_count': 146, 'const_occurrence_count': 2755, 'resolved_candidate_count': 146}, 'leanrank_best_safe_delta_vs_graph': {'hit@1': 0.0, 'hit@10': 0.11120000000000008, 'hit@3': 0.05180000000000007, 'hit@5': 0.0474, 'mrr': 0.019515591630591578}, 'leanrank_best_safe_policy': 'tail_after_top1', 'leanrank_bm25_best_safe_metrics': {'hit@1': 0.3864, 'hit@10': 0.9476, 'hit@3': 0.6588, 'hit@5': 0.7692, 'mean_rank': 3.4788, 'mrr': 0.5620543506493506, 'n': 5000}, 'leanrank_bm25_best_safe_policy': 'graph_tail_after_top1_bm25', 'literature_positioning_status': 'positioning_complete_no_novelty_overclaim', 'mathlibgraph_network_r10': 0.5200779274690902, 'metavar_action_delta_probe_contract': {'actions': ['exact_assignIfDefEq', 'apply_MVarId_apply'], 'candidate_equals_target_self_matches_excluded': True, 'candidate_names_used_for_evaluation_only': True, 'candidate_names_used_for_scoring': False, 'full_tactic_trace': False, 'lean_metavariable_goal_probe': True}, 'metavar_action_delta_probe_interpretation': 'v10.5 upgrades from static/interface compatibility to actual Lean metavariable actions.  It observes exact/apply success and side-goal heads, giving the first proof-obstruction motif signal without candidate-name role bootstrap.', 'metavar_action_delta_probe_metrics': {'emitted_probe_count': 1790, 'hit_at_7': 0.5, 'mrr': 0.2637653711023276, 'nonself_apply_ok': 40, 'nonself_exact_ok': 40, 'probe_count': 1790, 'row_count': 8}, 'name_erased_ast_backtest_metrics': {'ast_shape_hit_at_7': 0.625, 'ast_shape_mrr': 0.48054181929181927}, 'non_ns_signals': 3, 'nonbootstrap_interface_role_contract': {'candidate_declaration_names_used_for_evaluation_only': True, 'candidate_declaration_names_used_for_scoring': False, 'candidate_role_sources': ['declaration_kind', 'name-erased Expr node counts', 'bucketed global constants', 'LOCAL_PROJECT opaque reference count'], 'local_project_constant_names_erased': True}, 'nonbootstrap_interface_role_interpretation': 'This is the first stricter non-bootstrap interface extractor.  If it remains weak, the missing evidence is action-delta/proof-state behavior, not another static declaration graph.', 'nonbootstrap_interface_role_metrics': {'hit_at_7': 0.0, 'mrr': 0.032021416083916086, 'row_count': 8}, 'policy_gap_decomposition_metrics': {'accepted_non_gold_progress_by_policy': {}, 'action_order_bottleneck_rows': 2, 'candidate_queue_bottleneck_rows': 1, 'class_counts': {'action_order_needed_but_late': 1, 'action_order_saves_budget_on_hybrid_queue': 1, 'already_solved_by_generic_budget10': 5, 'candidate_queue_v115_saves_budget': 1}, 'dominant_class': 'already_solved_by_generic_budget10', 'dominant_count': 5, 'recommended_next_target': 'action_affordance_repair', 'row_count': 8, 'sort_closure_count': 0}, 'policy_gap_decomposition_status': 'policy_gap_decomposition_actionable', 'probe_budget_repair_bundle_harness': {'ceiling': {'ceiling_bundle_success_rate': 0.25, 'row_count': 8, 'rows_with_gold_progress_witness': 2, 'rows_with_hybrid_candidate_hit_at_7': 7}, 'interpretation': 'The current exact/apply/rw/simp probe inventory is too sparse for a solver claim: most rows have a candidate hit but no gold declaration with positive Lean-observed action evidence.  The next useful work is new action execution coverage (refine/convert/have/constructor and real before-after proof-state witnesses), not GPU training.', 'metrics': {'action_affordance_only': {'10': {'budget_success': 0.25, 'bundle_success_at_7': 0.25, 'mean_first_gold_repair_probe_count': 1.0, 'row_count': 8}, '25': {'budget_success': 0.25, 'bundle_success_at_7': 0.25, 'mean_first_gold_repair_probe_count': 1.0, 'row_count': 8}, '50': {'budget_success': 0.25, 'bundle_success_at_7': 0.25, 'mean_first_gold_repair_probe_count': 1.0, 'row_count': 8}, '7': {'budget_success': 0.25, 'bundle_success_at_7': 0.25, 'mean_first_gold_repair_probe_count': 1.0, 'row_count': 8}, 'exhaustive': {'budget_success': 0.25, 'bundle_success_at_7': 0.25, 'mean_first_gold_repair_probe_count': 1.0, 'row_count': 8}}, 'failure_transition_router': {'10': {'budget_success': 0.125, 'bundle_success_at_7': 0.0, 'mean_first_gold_repair_probe_count': 10.0, 'row_count': 8}, '25': {'budget_success': 0.125, 'bundle_success_at_7': 0.0, 'mean_first_gold_repair_probe_count': 10.0, 'row_count': 8}, '50': {'budget_success': 0.25, 'bundle_success_at_7': 0.0, 'mean_first_gold_repair_probe_count': 22.0, 'row_count': 8}, '7': {'budget_success': 0.0, 'bundle_success_at_7': 0.0, 'mean_first_gold_repair_probe_count': None, 'row_count': 8}, 'exhaustive': {'budget_success': 0.25, 'bundle_success_at_7': 0.0, 'mean_first_gold_repair_probe_count': 22.0, 'row_count': 8}}, 'retrieval_exhaustive_probes': {'10': {'budget_success': 0.0, 'bundle_success_at_7': 0.0, 'mean_first_gold_repair_probe_count': None, 'row_count': 8}, '25': {'budget_success': 0.0, 'bundle_success_at_7': 0.0, 'mean_first_gold_repair_probe_count': None, 'row_count': 8}, '50': {'budget_success': 0.125, 'bundle_success_at_7': 0.0, 'mean_first_gold_repair_probe_count': 46.0, 'row_count': 8}, '7': {'budget_success': 0.0, 'bundle_success_at_7': 0.0, 'mean_first_gold_repair_probe_count': None, 'row_count': 8}, 'exhaustive': {'budget_success': 0.25, 'bundle_success_at_7': 0.0, 'mean_first_gold_repair_probe_count': 108.0, 'row_count': 8}}, 'retrieval_fixed_action_order': {'10': {'budget_success': 0.0, 'bundle_success_at_7': 0.0, 'mean_first_gold_repair_probe_count': None, 'row_count': 8}, '25': {'budget_success': 0.0, 'bundle_success_at_7': 0.0, 'mean_first_gold_repair_probe_count': None, 'row_count': 8}, '50': {'budget_success': 0.125, 'bundle_success_at_7': 0.0, 'mean_first_gold_repair_probe_count': 46.0, 'row_count': 8}, '7': {'budget_success': 0.0, 'bundle_success_at_7': 0.0, 'mean_first_gold_repair_probe_count': None, 'row_count': 8}, 'exhaustive': {'budget_success': 0.25, 'bundle_success_at_7': 0.0, 'mean_first_gold_repair_probe_count': 108.0, 'row_count': 8}}, 'v115_action_selection': {'10': {'budget_success': 0.25, 'bundle_success_at_7': 0.25, 'mean_first_gold_repair_probe_count': 2.0, 'row_count': 8}, '25': {'budget_success': 0.25, 'bundle_success_at_7': 0.25, 'mean_first_gold_repair_probe_count': 2.0, 'row_count': 8}, '50': {'budget_success': 0.25, 'bundle_success_at_7': 0.25, 'mean_first_gold_repair_probe_count': 2.0, 'row_count': 8}, '7': {'budget_success': 0.25, 'bundle_success_at_7': 0.25, 'mean_first_gold_repair_probe_count': 2.0, 'row_count': 8}, 'exhaustive': {'budget_success': 0.25, 'bundle_success_at_7': 0.25, 'mean_first_gold_repair_probe_count': 2.0, 'row_count': 8}}}}, 'repair_router_alias_stress_metrics': {'identity_hit_at_7': 0.875, 'name_anonymized_hit_at_7': 0.875, 'semantic_alias_hit_at_7': 0.875}, 'repair_router_structural_occlusion_metrics': {'docless_name_anonymized_hit_at_7': 0.5, 'identity_hit_at_7': 0.875, 'role_token_alias_signature_hit_at_7': 0.625, 'signature_names_erased_hit_at_7': 0.625}, 'robust_competitor_verdict': {'cold_shot_now': True, 'cold_shot_reason': 'The local benchmark now has a nontrivial negative: action-probe MRR was tie-inflated, and the robust winner is a cheap hybrid retrieval+typed proxy.  External critique should attack the benchmark and suggest the next non-tautological action-router test.', 'current_winner': 'hybrid_retrieval_typed_proxy', 'gpu_training_now': False, 'next_local_build': 'Action selection, not action scoring: decide whether a candidate should be probed by rw/simp/apply/refine/convert before ranking it.'}, 'row_obligation_seeded_role_interpretation': 'Row obligation labels can seed role matching without gold-candidate prototypes.  Candidate role edges remain bootstrap-weak, so this is evidence for building non-bootstrap role extraction, not for GPU.', 'row_obligation_seeded_role_metrics': {'hit_at_7': 0.375, 'mrr': 0.3334437378555026, 'row_count': 8}, 'same_sample_competitor_harness_best_by_hit': 'C_hybrid_v84_retrieval_typed_proxy', 'same_sample_competitor_harness_best_by_mrr': 'D_action_v107_tactic_probe', 'same_sample_competitor_harness_metrics': {'A_lexical_retrieval_proxy': {'hit_at_1': 0.5, 'hit_at_7': 0.75, 'mean_first_gold_rank': 9.0, 'mrr': 0.6328431372549019, 'row_count': 8}, 'B_endpoint_demoted_retrieval_proxy': {'hit_at_1': 0.5, 'hit_at_7': 0.75, 'mean_first_gold_rank': 9.0, 'mrr': 0.6328431372549019, 'row_count': 8}, 'C_hybrid_v84_retrieval_typed_proxy': {'hit_at_1': 0.5, 'hit_at_7': 0.875, 'mean_first_gold_rank': 1.8571428571428572, 'mrr': 0.65, 'row_count': 8}, 'D_action_v107_tactic_probe': {'hit_at_1': 0.625, 'hit_at_7': 0.75, 'mean_first_gold_rank': 12.875, 'mrr': 0.6719304078014184, 'row_count': 8}, 'E_action_v109_failure_taxonomy': {'hit_at_1': 0.625, 'hit_at_7': 0.75, 'mean_first_gold_rank': 12.875, 'mrr': 0.6719304078014184, 'row_count': 8}, 'F_action_v110_failure_aware': {'hit_at_1': 0.25, 'hit_at_7': 0.75, 'mean_first_gold_rank': 17.75, 'mrr': 0.46236659220650284, 'row_count': 8}, 'G_combined_retrieval_action': {'hit_at_1': 0.5, 'hit_at_7': 0.75, 'mean_first_gold_rank': 6.875, 'mrr': 0.6356818181818182, 'row_count': 8}}, 'semantic_alias_preservation': 0.8988095238095238, 'symbolic_expr_graph_backtest_modes': {'full_const': {'hit_at_7': 0.625, 'mrr': 0.47012515262515264}, 'local_redacted_const': {'hit_at_7': 0.625, 'mrr': 0.47012515262515264}, 'namespace_const': {'hit_at_7': 0.625, 'mrr': 0.47012515262515264}}, 'tactic_failure_taxonomy_contract': {'actions': ['rw_fwd', 'rw_rev', 'simp_only'], 'actual_tactic_execution': True, 'candidate_names_used_for_scoring': False, 'gold_labels_used_for_evaluation_only': True, 'no_gpu': True, 'same_probe_matrix_as_v107': True}, 'tactic_failure_taxonomy_interpretation': 'The useful question is whether Lean failures separate into actionable anti-failure classes.  If the other_failure rate remains high, the runner is still too coarse for training; if it drops, those classes can feed the next set-cover router.', 'tactic_failure_taxonomy_metrics': {'failure_class_counts': {'invalid_rewrite_argument': 1056, 'no_equation_theorem': 2436, 'no_occurrence': 85, 'simp_no_progress': 1770}, 'hit_at_7': 0.75, 'mrr': 0.6719304078014184, 'ok_tactic_attempt_count': 23, 'other_failure_rate': 0.0, 'probe_count': 1790, 'row_count': 8, 'tactic_attempt_count': 5370}, 'tactic_rewrite_delta_probe_contract': {'actions': ['rw_fwd', 'rw_rev', 'simp_only'], 'actual_tactic_execution': True, 'candidate_equals_target_self_matches_excluded': True, 'candidate_names_used_for_evaluation_only': True, 'candidate_names_used_for_scoring': False, 'no_gpu': True}, 'tactic_rewrite_delta_probe_interpretation': 'v10.7 turns Lean into a failure-mode instrument for rewrite-like actions.  The value is less the raw rank score than the explicit failure histogram and per-candidate action/failure signatures.', 'tactic_rewrite_delta_probe_metrics': {'failure_class_counts': {'no_occurrence': 85, 'other_failure': 5262}, 'hit_at_7': 0.75, 'mrr': 0.6719304078014184, 'ok_tactic_attempt_count': 23, 'probe_count': 1790, 'row_count': 8, 'tactic_attempt_count': 5370}, 'tactic_rewrite_failure_classifier_read': 'too_coarse', 'target_aware_policy_eval_metrics': {'accepted_non_gold_progress_by_policy': {}, 'best_target_aware_budget10': {'policy': 'target_aware_typed', 'success_count': 6}, 'best_target_aware_budget25': {'policy': 'target_aware_v115', 'success_count': 8}, 'generic_budget10_success_count': 5, 'probe_count': 800, 'row_count': 8, 'sort_closure_count': 0}, 'target_aware_policy_eval_status': 'target_aware_policy_eval_failed', 'target_unit_audit_interpretation': 'Sort-like target rows make declaration-type goals a poor proxy for local repair progress. Rows with structure/type declarations should be rebuilt around executable local obligations, fields, or tactic states before action-router promotion.', 'target_unit_audit_metrics': {'row_count': 8, 'rows_all_sort_like': 0, 'rows_with_proof_like_target': 3, 'rows_with_sort_like_target': 3, 'target_class_counts': {'object_like': 8, 'proof_like': 7, 'sort_like': 10}, 'target_count': 25, 'v123_strict_false_positive_rows': ['v63_gnn_graph_combo_patch_attribution', 'v91_ns_leray_heat_tent_geometry_patch_attribution'], 'v123_strict_false_positive_rows_with_sort_like_target': ['v63_gnn_graph_combo_patch_attribution', 'v91_ns_leray_heat_tent_geometry_patch_attribution']}, 'target_unit_audit_status': 'mixed_target_unit_gap_confirmed', 'target_unit_repair_packet_interpretation': 'The repaired targets test the intended proof-workstation unit: after local parameters are introduced, an adapter should expose a specific lower side obligation. Passing this packet permits a full 8-row v12.5 benchmark rewrite; it does not justify GPU or public candidate integration by itself.', 'target_unit_repair_packet_metrics': {'repaired_row_count': 2, 'repaired_rows_exposing_intended_obligation': 2, 'repaired_success_rate': 1.0, 'total_sort_closure_count': 0}, 'target_unit_repair_packet_status': 'target_unit_repair_packet_passed', 'typed_neighborhood_jaccard_interpretation': {'non_name_signal': 'weak', 'role_signal': 'strong_but_bootstrap_derived', 'uses_existing_primitive': 'src.ztare.motion.set_distance.jaccard_distance'}, 'typed_neighborhood_jaccard_modes': {'ast': {'hit_at_7': 0.375, 'mrr': 0.3414986839146595}, 'combined_non_name_role': {'hit_at_7': 0.875, 'mrr': 0.7318262411347518}, 'const_family': {'hit_at_7': 0.375, 'mrr': 0.3382839613012027}, 'non_name': {'hit_at_7': 0.375, 'mrr': 0.34584106369820655}, 'role': {'hit_at_7': 1.0, 'mrr': 0.8541666666666666}}, 'typed_obligation_expr_graph': {'edge_count': 24089, 'edge_type_counts': None, 'node_count': 295, 'status': 'typed_obligation_expr_graph_built'}, 'typed_obligation_ppr_interpretation': 'weak under current high-degree/all-role seeding; retry only with row-specific unmet-obligation seed nodes', 'typed_obligation_ppr_modes': {'combined': {'hit_at_7': 0.375, 'mrr': 0.22768743793445878}, 'non_name': {'hit_at_7': 0.375, 'mrr': 0.27892014532103204}, 'role': {'hit_at_7': 0.375, 'mrr': 0.22488761238761237}}}`

## v7.6 LeanRank Gated Residual

- `available`: `True`
- `status`: `gated_typed_residual_eval_complete`
- `best_safe_policy`: `tail_after_top1`
- `best_safe_delta`: `{'hit@1': 0.0, 'hit@10': 0.11120000000000008, 'hit@3': 0.05180000000000007, 'hit@5': 0.0474, 'mrr': 0.019515591630591578}`

## v7.9 Repair Benchmark Seed

- `available`: `True`
- `status`: `repair_benchmark_seed_created`
- `row_count`: `8`
- `generated_non_ns_rows`: `3`
- `training_decision`: `blocked_seed_too_small`

## v8.0 LeanRank BM25 Gated Eval

- `available`: `True`
- `status`: `bm25_gated_eval_complete`
- `rows_scored`: `5000`
- `graph_top1_bm25_tail_metrics`: `{'hit@1': 0.3864, 'hit@10': 0.9476, 'hit@3': 0.6588, 'hit@5': 0.7692, 'mean_rank': 3.4788, 'mrr': 0.5620543506493506, 'n': 5000}`
- `graph_top1_bm25_tail_delta`: `{'hit@1': 0.0, 'hit@10': 0.13980000000000004, 'hit@3': 0.13540000000000008, 'hit@5': 0.139, 'mrr': 0.051468448773448694}`

## v8.1 Repair Router Protocol

- `available`: `True`
- `status`: `protocol_debug_complete_not_evidence`
- `row_count`: `4`
- `cheap_baseline_success_at_1`: `0.0`
- `typed_router_success_at_1`: `1.0`
- `interpretation`: `This only validates the benchmark mechanics.  The candidate pools are protocol decoys, not an external heldout sample.  Next step is adding real generated non-NS repair rows and deriving candidate pools from actual Lean declarations/obligation contexts.`

## v8.2 Actual-Declaration Repair Pool

- `available`: `True`
- `status`: `actual_declaration_pool_proxy_not_training_evidence`
- `row_count`: `8`
- `metrics`: `{'lexical_hit_at_1': 0.5, 'lexical_hit_at_7': 0.75, 'typed_hit_at_1': 0.25, 'typed_hit_at_7': 0.375}`

## v8.3 Constrained Repair Queue

- `available`: `True`
- `status`: `constrained_repair_queue_proxy_not_training_evidence`
- `row_count`: `8`
- `metrics`: `{'constrained_hit_at_7': 0.75, 'constrained_mean_first_gold_rank': 1.3333333333333333, 'constrained_top1_gold': 0.5, 'lexical_hit_at_7': 0.75, 'lexical_mean_first_gold_rank': 9.0, 'lexical_top1_gold': 0.5, 'typed_hit_at_7': 0.375, 'typed_mean_first_gold_rank': 20.125, 'typed_top1_gold': 0.25}`

## v8.4 Hybrid Repair Router

- `available`: `True`
- `status`: `hybrid_repair_router_proxy_not_training_evidence`
- `row_count`: `8`
- `metrics`: `{'hybrid_hit_at_7': 0.875, 'hybrid_mean_first_gold_rank': 1.8571428571428572, 'hybrid_top1_gold': 0.5, 'lexical_hit_at_7': 0.75, 'lexical_mean_first_gold_rank': 9.0, 'lexical_top1_gold': 0.5, 'typed_hit_at_7': 0.375, 'typed_mean_first_gold_rank': 20.125, 'typed_top1_gold': 0.25}`

## v8.5 Literature Positioning

- `available`: `True`
- `status`: `positioning_complete_no_novelty_overclaim`
- `positioning`: `The 10x candidate is not a better generic premise selector.  It is a typed repair debugger: retrieve candidates with established methods, then route around unmet carrier/index/incidence/budget/freshness obligations with endpoint/guard/wrong-carrier risk flags.`
- `next_test`: `Freeze a 12-row endpoint-occluded repair benchmark with actual declaration pools and compare: retrieval/BM25 baseline, typed-only tail, and hybrid repair-router.  Kill or demote learned training if the hybrid router does not beat the cheap baseline on repair-bundle success and alias stability.`

## v8.8 Repair Router Alias Stress

- `available`: `True`
- `status`: `alias_stress_proxy_complete`
- `row_count`: `8`
- `metrics`: `{'identity_hit_at_7': 0.875, 'name_anonymized_hit_at_7': 0.875, 'semantic_alias_hit_at_7': 0.875}`

## v9.0 Structural Occlusion Stress

- `available`: `True`
- `status`: `structural_occlusion_proxy_complete`
- `row_count`: `8`
- `metrics`: `{'docless_name_anonymized_hit_at_7': 0.5, 'identity_hit_at_7': 0.875, 'role_token_alias_signature_hit_at_7': 0.625, 'signature_names_erased_hit_at_7': 0.625}`

## v9.2 Label-Blind Hard-Decoy Audit

- `available`: `True`
- `status`: `label_blind_hard_decoy_audit_complete`
- `decision`: `proxy_pass_but_gpu_still_blocked_by_structural_occlusion`
- `static_label_blind_check`: `{'checked_functions': ['build_pool', 'lexical_score', 'typed_score'], 'evaluator_label_access': {'build_pool': False, 'lexical_score': False, 'typed_score': False}, 'passes': True}`
- `metrics`: `{'all_pools_ge_50': True, 'all_pools_gt_7': True, 'hybrid_hit_at_7': 0.875, 'hybrid_mrr': 0.65, 'hybrid_top1': 0.5, 'lexical_hit_at_7': 0.75, 'lexical_mrr': 0.6328431372549019, 'lexical_top1': 0.5, 'min_pool_size': 50, 'row_count': 8, 'typed_hit_at_7': 0.375, 'typed_mrr': 0.34837213485455854, 'typed_top1': 0.25}`

## v9.3 Kernel-Shape Feature Probe

- `available`: `True`
- `status`: `kernel_shape_feature_probe_complete`
- `metrics`: `{'combo_hit_at_7': 0.75, 'combo_mrr': 0.6218434343434344, 'lexical_hit_at_7': 0.75, 'lexical_mrr': 0.6328431372549019, 'row_count': 8, 'shape_hit_at_7': 0.5, 'shape_mrr': 0.3202020202020202, 'typed_hit_at_7': 0.375, 'typed_mrr': 0.34837213485455854}`

## v9.4 Post-Patch Dependency Probe

- `available`: `True`
- `status`: `post_patch_dependency_attribution_probe_complete`
- `metrics`: `{'dependency_hit_at_7': 0.375, 'dependency_mrr': 0.18485023041474655, 'row_count': 8}`

## Candidate Risk

- `targets_emitted`: `5`
- `known_used_ranked_first`: `2`
- `known_used_any_topk`: `4`
- `danger_counts`: `{'endpoint_or_carleson': 6, 'guard_not_constructor': 3}`
- `role_counts`: `{'constructor': 7, 'context': 9, 'danger_or_guard': 9}`

## Consumption Protocol

- Start from `actionable_candidate_names`, not the raw top-candidate list.
- Use danger candidates only as guards or context.
- Prefer declarations also present in the same-tree obligation graph.
- Do not launch GPU/API/autoresearch spend from this precheck alone.
- After a patch, record whether a top candidate actually influenced the edit.

## Actionable Candidates

- `NormalizedExcessBadCenterSelection.ofNonadaptiveCarrier` (`3` hits)
- `BadCenterMonotoneFrequencyDrop.ofEventRecurrenceLedgerBridge` (`1` hits)
- `BadCenterEventRecurrenceLedgerBridge.ofSplitWitness` (`1` hits)
- `BadCenterLowerDensityForSelectedNodes.ofNonadaptiveCarrier` (`1` hits)
- `BadCenterEventBudgetedBetaSquarePrefixBridge.ofPointwiseDuhamelCoverage` (`1` hits)

## Danger Candidates

- `BadCenterBetaSquareCarlesonDrop.ofEventBudgetedPrefixData` (`4` hits)
- `BadCenterNonadaptiveConstructionGuard.ofNonadaptiveCarrier` (`3` hits)
- `BadCenterBetaSquareCarlesonDrop.ofMonotoneFrequencyDrop` (`1` hits)
- `BadCenterBetaSquareCarlesonDrop.ofSameTreeEventBudgetedPrefixData` (`1` hits)

## Warnings

- top candidates include endpoint/guard/tautology danger terms
- v5.4 typed-symmetry audit has missing roles or collapse risks
- v6 contract blocks generic E3/CFD equivariant GNN for theorem search
- v6.1 typed-obligation hypergraph contract is ready for design only, not training
- v6.2 typed-obligation work packet is advisory only
- v8.1 repair-router protocol is mechanics-only; do not treat as evidence
- v8.2 actual-declaration repair pool is proxy evidence only
- v8.3 constrained repair queue is proxy evidence only
- v8.4 hybrid repair router is proxy evidence only
- v8.8 repair-router semantic-alias stress is below robustness gate
- v8.8 repair-router name-anonymization stress is below robustness gate
- v9.0 structural occlusion stress is below robustness gate
- v9.0 role-token alias signature stress is below robustness gate
- v9.3 kernel-shape proxy does not beat lexical
- v9.4 post-patch dependency proxy is weak
- v9.7 name-erased AST-shape signal is below router gate
- v9.8 local-redacted symbolic Expr graph signal is below router gate
- v10.0 non-name typed-neighborhood Jaccard is below router gate
- v10.0 role-neighborhood Jaccard depends on bootstrap role edges
- v10.1 PPR graph baseline is below router gate
- v10.2 row-obligation seeded role matching is below router gate
- v10.3 non-bootstrap static interface roles are below router gate
- v10.5 raw exact/apply action probe is below router gate
- v10.6 mixed text-prior router underperforms action-only; treat text priors as overfit risk
- v10.7 failure classifier is too coarse; split other_failure before training
- v10.8 combination does not beat v10.7 tactic-probe MRR; split failures before adding weights
- v11.7 old action inventory has low repair-bundle ceiling; use expanded actions
- v12.0 convert selectivity precision is low; do not trust raw convert progress
- v12.1 focused witness precision is below promotion gate
- v12.6 full target-unit rewrite passed; repaired benchmark unit is available
- v12.7 target-aware policy eval failed strict gate; do not expand benchmark or use GPU
- v12.8 decomposition says next target is action-affordance compression plus v87 queue repair
- v12.9 compressed affordance passed repaired seed; robustness stress is next, not GPU
- v12.10 found temporal/current-file candidate-pool risk; use pre-patch/scrubbed pools next
- GPU v5.1/v5.2 validation pending; do not promote beyond advisory use
- non-NS v5.2 guard pending; keep scope at NS/math workstation assistance

## Top Targets

### `BadCenterBetaSquareCarlesonDrop.ofEventRecurrenceLedgerBridge`

- `BadCenterBetaSquareCarlesonDrop.ofEventBudgetedPrefixData` (danger_or_guard; warnings: endpoint_or_carleson)
- `BadCenterMonotoneFrequencyDrop.ofEventRecurrenceLedgerBridge` (constructor; warnings: -)
- `BadCenterBetaSquareCarlesonDrop.ofMonotoneFrequencyDrop` (danger_or_guard; warnings: endpoint_or_carleson)
- `badCenterEventBetaSquarePrefix_le_eventBudget_ofDuhamelIncidenceSource` (context; warnings: -)
- `BadCenterEventRecurrenceLedgerBridge.ofSplitWitness` (constructor; warnings: -)

### `BadCenterBetaSquareCarlesonDrop.ofSameTreeEventBudgetedPrefixData`

- `BadCenterBetaSquareCarlesonDrop.ofEventBudgetedPrefixData` (danger_or_guard; warnings: endpoint_or_carleson)
- `badCenterEventBetaSquarePrefix_le_eventBudget_ofDuhamelIncidenceSource` (context; warnings: -)
- `NormalizedExcessBadCenterSelection.ofNonadaptiveCarrier` (constructor; warnings: -)
- `BadCenterNonadaptiveConstructionGuard.ofNonadaptiveCarrier` (danger_or_guard; warnings: guard_not_constructor)
- `BadCenterLowerDensityForSelectedNodes.ofNonadaptiveCarrier` (constructor; warnings: -)

### `BadCenterEventBudgetedBetaSquarePrefixBridge.ofPointwiseDuhamelCoverage`

- `BadCenterBetaSquareCarlesonDrop.ofEventBudgetedPrefixData` (danger_or_guard; warnings: endpoint_or_carleson)
- `badCenterEventBetaSquarePrefix_le_eventBudget_ofDuhamelIncidenceSource` (context; warnings: -)
- `BadCenterBetaSquareCarlesonDrop.ofSameTreeEventBudgetedPrefixData` (danger_or_guard; warnings: endpoint_or_carleson)
- `NormalizedExcessBadCenterSelection.ofNonadaptiveCarrier` (constructor; warnings: -)
- `BadCenterNonadaptiveConstructionGuard.ofNonadaptiveCarrier` (danger_or_guard; warnings: guard_not_constructor)

### `BadCenterEventBudgetedBetaSquarePrefixBridge.ofPointwiseDuhamelCoverageNonCircular`

- `BadCenterBetaSquareCarlesonDrop.ofEventBudgetedPrefixData` (danger_or_guard; warnings: endpoint_or_carleson)
- `badCenterEventBetaSquarePrefix_le_eventBudget_ofDuhamelIncidenceSource` (context; warnings: -)
- `BadCenterEventBudgetedBetaSquarePrefixBridge.ofPointwiseDuhamelCoverage` (constructor; warnings: -)
- `NormalizedExcessBadCenterSelection.ofNonadaptiveCarrier` (constructor; warnings: -)
- `BadCenterNonadaptiveConstructionGuard.ofNonadaptiveCarrier` (danger_or_guard; warnings: guard_not_constructor)

### `BadCenterEventPriceDropDuhamelIncidenceSource.eventCertificate`

- `BadCenterEventPriceDropDuhamelIncidenceSource` (context; warnings: -)
- `BadCenterEventPriceDropIdentification` (context; warnings: -)
- `badCenterEventBetaSquarePrefix_le_eventBudget_ofDuhamelIncidenceSource` (context; warnings: -)
- `BadCenterEventRecurrenceLedgerBridge` (context; warnings: -)
- `BadCenterEventNodeIdentification` (context; warnings: -)
