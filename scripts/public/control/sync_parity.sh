#!/usr/bin/env bash
# sync_parity.sh — ONE command: make LOCAL and VPS byte-identical for
# the canonical Lean-harness code, then PROVE parity (sha256 match +
# the 4 machine-safe self-tests green on BOTH). Fail-loud. Safe to run
# alongside a live VPS run: scp + --self-test are NO heavy-Lean and do
# not touch a running process (it already loaded its modules); the
# self-tests isolate their own ledger (no pollution).
#
#   bash scripts/public/control/sync_parity.sh
#
# Ends with the verification line, per the one-command-script rule.
set -uo pipefail

VPS="${ZTARE_VPS_SSH:?set ZTARE_VPS_SSH, for example user@host}"
KEY="${ZTARE_VPS_KEY:?set ZTARE_VPS_KEY}"
CONTROL_PATH="${ZTARE_VPS_CONTROL_PATH:-/tmp/leanmill_sync_parity_%r_%h_%p}"
SSH="ssh -i $KEY -o ConnectTimeout=20 -o ServerAliveInterval=30 -o ControlMaster=auto -o ControlPersist=120 -o ControlPath=$CONTROL_PATH"
SCP="scp -i $KEY -o ConnectTimeout=20 -o ServerAliveInterval=30 -o ControlMaster=auto -o ControlPersist=120 -o ControlPath=$CONTROL_PATH"
LREPO="${ZTARE_LOCAL_REPO:-$(git -C "$(dirname "$0")/../../.." rev-parse --show-toplevel)}"
RREPO="${ZTARE_VPS_REPO:-~/figs_activist_loop}"
CTL="scripts/public/control"

# canonical set — everything that defines gate/prover/wedge behavior
FILES=(
  "$CTL/authoritative_axioms.py"
  "src/ztare/common/subscription_agent_runtime.py"
  "$CTL/coherent_rung1.py"
  "$CTL/governance_in_context.py"
  "$CTL/authoritative_two_half.py"
  "$CTL/tool_router.py"
  "$CTL/tool_router_smoke.py"
  "$CTL/deterministic_tool_router_ablation.py"
  "$CTL/exact_gap_trace_judge.py"
  "$CTL/external_backend_adapter_smoke.py"
  "$CTL/feedback_only_ablation.py"
  "$CTL/lean_action_routing_dataset.py"
  "$CTL/lean_action_routing_eval.py"
  "$CTL/lean_action_routing_mine_void.py"
  "$CTL/lean_action_routing_predict.py"
  "$CTL/lean_action_routing_score_predictions.py"
  "$CTL/lean_action_routing_two_stage.py"
  "$CTL/lean_env_parity.py"
  "$CTL/build_module_context_benchmark.py"
  "$CTL/leansearch_action_batch.py"
  "$CTL/leansearch_factory_consume.py"
  "$CTL/leansearch_factory_intake.py"
  "$CTL/leansearch_mcb_source_pipeline.py"
  "$CTL/leansearch_mcb_partial_microbatch.sh"
  "$CTL/leansearch_mcb_factory_watchdog.py"
  "$CTL/leansearch_llm_template_proposer.py"
  "$CTL/leansearch_factory_mill.py"
  "$CTL/leansearch_factory_ops_timeseries.py"
  "$CTL/leansearch_factory_p0_rollup.py"
  "$CTL/leansearch_factory_scoreboard.py"
  "$CTL/leansearch_factory_residual_plan.py"
  "$CTL/leansearch_factory_status.py"
  "$CTL/leansearch_factory_live_state.py"
  "$CTL/leansearch_source_quality_dashboard.py"
  "$CTL/leansearch_source_quality_filter.py"
  "$CTL/leansearch_residual_family_source_planner.py"
  "$CTL/leansearch_path_c_residual_compiler.py"
  "$CTL/leansearch_repair_family_registry.py"
  "analytics/public/leanmill/repair_families/asymptotics_bigo_eq_mul_planner.yaml"
  "analytics/public/leanmill/repair_families/ennreal_tsum_condensation_planner.yaml"
  "analytics/public/leanmill/repair_families/interval_alignment_planner.yaml"
  "analytics/public/leanmill/repair_families/qparam_tendsto_norm_exp_planner.yaml"
  "analytics/public/leanmill/repair_families/cusp_function_qparam_periodic_planner.yaml"
  "analytics/public/leanmill/repair_families/spectral_rayleigh_spectrum_planner.yaml"
  "analytics/public/leanmill/repair_families/spectral_rayleigh_extremum_planner.yaml"
  "analytics/public/leanmill/repair_families/spectral_rayleigh_singular_values_planner.yaml"
  "$CTL/leansearch_factory.py"
  "$CTL/real_prover_practice_adapter.py"
  "$CTL/leansearch_action_smoke.py"
  "$CTL/leansearch_candidate_static_filter.py"
  "$CTL/leansearch_mcb_queue.py"
  "$CTL/leansearch_mcb_refill_and_mill.sh"
  "$CTL/leansearch_row_context_filter.py"
  "$CTL/leansearch_source_adapter.py"
  "$CTL/leanmill_agent_repair_worker.py"
  "$CTL/leanmill_24x7_runner.py"
  "$CTL/leanmill_canary_validator_worker.py"
  "$CTL/leanmill_de_experiment_contract.py"
  "$CTL/leanmill_family_spec_gate.py"
  "$CTL/leanmill_family_specs.py"
  "$CTL/leanmill_governance_worker.py"
  "$CTL/leanmill_heldout_receipt_gate.py"
  "$CTL/leanmill_llm_proposal_gate.py"
  "$CTL/leanmill_llm_proposal_worker.py"
  "$CTL/leanmill_probe_worker.py"
  "$CTL/leanmill_registry_worker.py"
  "$CTL/leanmill_regression_gate.py"
  "$CTL/leanmill_residual_lifecycle.py"
  "$CTL/leanmill_source_family_allocator.py"
  "$CTL/leanmill_source_inventory.py"
  "$CTL/leanmill_source_worker.py"
  "$CTL/leanmill_station_action_contract.py"
  "$CTL/leanmill_station_health_dashboard.py"
  "$CTL/leanmill_station_scheduler.py"
  "$CTL/leanmill_vnext_coverage_gate.py"
  "$CTL/lean_proofstate_feature_extract.py"
  "$CTL/lean_repair_policy_score.py"
  "$CTL/lean_repair_trajectory_dataset.py"
  "$CTL/lean_trace_feature_extract.py"
  "$CTL/path_c_curriculum_queue.py"
  "$CTL/path_c_canary_replay.py"
  "$CTL/path_c_temporal_basin_scorer.py"
  "$CTL/prepare_lean_backends.py"
  "$CTL/phaseB_fix_probe.py"
  "$CTL/four_arm_wedge.py"
  "$CTL/sync_parity.sh"
  "$CTL/gold_proof_control.py"
  "$CTL/gate_real_validation.py"
  "$CTL/ratify_throughput_solved.py"
  "$CTL/codex_proofstate_pilot.py"
  "$CTL/codex_proofstate_pilot_fast.py"
  "deploy/prepare_lean_backends.sh"
  "src/ztare/formal/lean_persistent.py"
  # Solver-lane core + governance (extracted to src/ in #37; added to the parity set 2026-06-05 so the
  # governed entry, the strategist-move generators, and the integrity/compile-probe kernel stay
  # byte-identical local↔VPS — this is the prover/gate behavior the parity proof exists to protect).
  "src/ztare/leanmill/solver/solver_core.py"
  "src/ztare/leanmill/solver/governed_dag_search.py"
  "src/ztare/leanmill/solver/conjecture.py"
  "src/ztare/leanmill/solver/statement_integrity.py"
  "src/ztare/leanmill/solver/agentic_leaf.py"
  "src/ztare/leanmill/solver/proof_state.py"
  "src/ztare/leanmill/solver/move_calibration.py"
  "src/ztare/leanmill/solver/isomorphism_decompose.py"
  "src/ztare/leanmill/solver/failure_class.py"
  "src/ztare/leanmill/solver/no_good_store.py"
  "src/ztare/leanmill/solver/outcome_link.py"
  "src/ztare/leanmill/solver/witness_transport.py"
  "src/ztare/common/symbolic_witness.py"
  "src/ztare/gates/lean_compile_primitives.py"
  "src/ztare/gates/v33_preflight_risk_detector.py"
)

echo "=== 1. SYNC local -> VPS ==="
fail=0
for f in "${FILES[@]}"; do
  if [ ! -f "$LREPO/$f" ]; then echo "  SKIP (absent local): $f"; continue; fi
  scp_log="/tmp/leanmill_sync_parity_scp.$$.log"
  $SCP "$LREPO/$f" "$VPS:$RREPO/$f" >"$scp_log" 2>&1 \
    && echo "  synced $f" || { echo "  SCP FAIL $f :: $(tail -1 "$scp_log")"; fail=1; }
  rm -f "$scp_log"
done

echo "=== 2. PARITY CHECK (sha256 local vs VPS) ==="
for f in "${FILES[@]}"; do
  [ -f "$LREPO/$f" ] || continue
  L=$(shasum -a 256 "$LREPO/$f" | awk '{print $1}')
  R=$($SSH "$VPS" "shasum -a 256 $RREPO/$f 2>/dev/null | awk '{print \$1}'" 2>/dev/null)
  if [ "$L" = "$R" ] && [ -n "$L" ]; then echo "  OK  $f"
  else echo "  DRIFT  $f  (local=$L vps=$R)"; fail=1; fi
done

echo "=== 3. SELF-TESTS on BOTH (machine-safe, no Lean) ==="
st() { # $1 = where, $2 = label, $3 = cmd
  test_log="/tmp/leanmill_sync_parity_test.$$.log"
  if eval "$3" >"$test_log" 2>&1; then
    out=$(tail -1 "$test_log")
    if echo "$out" | grep -qiE '(^|[^[:alpha:]])PASS([^[:alpha:]]|$)|all PASS|__SELFTEST_PASS__' \
      && ! echo "$out" | grep -qiE '(self-test|logic self-test)[[:space:]]+FAIL'; then
      echo "  [$1] $2 PASS"
    else echo "  [$1] $2 FAIL :: $out"; fail=1; fi
  else
    out=$(tail -20 "$test_log" | tr '\n' ' ' | sed 's/  */ /g')
    echo "  [$1] $2 FAIL :: $out"; fail=1
  fi
  rm -f "$test_log"
}
LST="cd $LREPO &&"
RST="$SSH $VPS 'cd $RREPO &&"
for pair in \
  "authoritative_axioms.py||python3 $CTL/authoritative_axioms.py" \
  "subscription_agent_runtime.py||python3 -m src.ztare.common.subscription_agent_runtime --self-test" \
  "coherent_rung1.py||python3 $CTL/coherent_rung1.py --self-test" \
  "governance_in_context.py||python3 $CTL/governance_in_context.py" \
  "authoritative_two_half.py||python3 $CTL/authoritative_two_half.py --self-test" \
  "tool_router_smoke.py||python3 $CTL/tool_router_smoke.py --self-test" \
  "deterministic_tool_router_ablation.py||python3 $CTL/deterministic_tool_router_ablation.py --self-test" \
  "exact_gap_trace_judge.py||python3 $CTL/exact_gap_trace_judge.py --self-test" \
  "external_backend_adapter_smoke.py||python3 $CTL/external_backend_adapter_smoke.py --self-test" \
  "feedback_only_ablation.py||python3 $CTL/feedback_only_ablation.py --self-test" \
  "lean_action_routing_dataset.py||python3 $CTL/lean_action_routing_dataset.py --self-test" \
  "lean_action_routing_eval.py||python3 $CTL/lean_action_routing_eval.py --self-test" \
  "lean_action_routing_mine_void.py||python3 $CTL/lean_action_routing_mine_void.py --self-test" \
  "lean_action_routing_predict.py||python3 $CTL/lean_action_routing_predict.py --self-test" \
  "lean_action_routing_score_predictions.py||python3 $CTL/lean_action_routing_score_predictions.py --self-test" \
  "lean_action_routing_two_stage.py||python3 $CTL/lean_action_routing_two_stage.py --self-test" \
  "lean_env_parity.py||python3 $CTL/lean_env_parity.py --self-test" \
  "build_module_context_benchmark.py||python3 -m py_compile $CTL/build_module_context_benchmark.py && echo self-test PASS" \
  "leansearch_action_batch.py||python3 $CTL/leansearch_action_batch.py --self-test" \
  "leansearch_factory_consume.py||python3 $CTL/leansearch_factory_consume.py --self-test" \
  "leansearch_factory_intake.py||python3 $CTL/leansearch_factory_intake.py --self-test" \
  "leansearch_mcb_source_pipeline.py||python3 $CTL/leansearch_mcb_source_pipeline.py --self-test" \
  "leansearch_mcb_partial_microbatch.sh||bash -n $CTL/leansearch_mcb_partial_microbatch.sh && echo self-test PASS" \
  "leansearch_mcb_factory_watchdog.py||python3 $CTL/leansearch_mcb_factory_watchdog.py --self-test" \
  "leansearch_llm_template_proposer.py||python3 $CTL/leansearch_llm_template_proposer.py --self-test" \
  "leansearch_factory_mill.py||python3 $CTL/leansearch_factory_mill.py --self-test" \
  "leansearch_factory_ops_timeseries.py||python3 $CTL/leansearch_factory_ops_timeseries.py --self-test" \
  "leansearch_factory_p0_rollup.py||python3 $CTL/leansearch_factory_p0_rollup.py --self-test" \
  "leansearch_factory_scoreboard.py||python3 $CTL/leansearch_factory_scoreboard.py --self-test" \
  "leansearch_factory_residual_plan.py||python3 $CTL/leansearch_factory_residual_plan.py --self-test" \
  "leansearch_factory_status.py||python3 $CTL/leansearch_factory_status.py --self-test" \
  "leansearch_factory_live_state.py||python3 $CTL/leansearch_factory_live_state.py --self-test" \
  "leansearch_source_quality_dashboard.py||python3 $CTL/leansearch_source_quality_dashboard.py --self-test" \
  "leansearch_source_quality_filter.py||python3 $CTL/leansearch_source_quality_filter.py --self-test" \
  "leansearch_residual_family_source_planner.py||python3 $CTL/leansearch_residual_family_source_planner.py --self-test" \
  "leansearch_path_c_residual_compiler.py||python3 $CTL/leansearch_path_c_residual_compiler.py --self-test" \
  "leansearch_repair_family_registry.py||python3 $CTL/leansearch_repair_family_registry.py --self-test" \
  "leansearch_factory.py||python3 $CTL/leansearch_factory.py --self-test" \
  "real_prover_practice_adapter.py||python3 $CTL/real_prover_practice_adapter.py --self-test" \
  "leansearch_action_smoke.py||python3 $CTL/leansearch_action_smoke.py --self-test" \
  "leansearch_candidate_static_filter.py||python3 $CTL/leansearch_candidate_static_filter.py --self-test" \
  "leansearch_mcb_queue.py||python3 $CTL/leansearch_mcb_queue.py --self-test" \
  "leansearch_mcb_refill_and_mill.sh||bash -n $CTL/leansearch_mcb_refill_and_mill.sh && echo self-test PASS" \
  "leansearch_row_context_filter.py||python3 $CTL/leansearch_row_context_filter.py --self-test" \
  "leansearch_source_adapter.py||python3 $CTL/leansearch_source_adapter.py --self-test" \
  "leanmill_agent_repair_worker.py||python3 $CTL/leanmill_agent_repair_worker.py --self-test" \
  "leanmill_24x7_runner.py||python3 $CTL/leanmill_24x7_runner.py --self-test" \
  "leanmill_canary_validator_worker.py||python3 $CTL/leanmill_canary_validator_worker.py --self-test" \
  "leanmill_de_experiment_contract.py||python3 $CTL/leanmill_de_experiment_contract.py --self-test" \
  "leanmill_family_spec_gate.py||python3 $CTL/leanmill_family_spec_gate.py --self-test" \
  "leanmill_governance_worker.py||python3 $CTL/leanmill_governance_worker.py --self-test" \
  "leanmill_heldout_receipt_gate.py||python3 $CTL/leanmill_heldout_receipt_gate.py --self-test" \
  "leanmill_llm_proposal_gate.py||python3 $CTL/leanmill_llm_proposal_gate.py --self-test" \
  "leanmill_llm_proposal_worker.py||python3 $CTL/leanmill_llm_proposal_worker.py --self-test" \
  "leanmill_probe_worker.py||python3 $CTL/leanmill_probe_worker.py --self-test" \
  "leanmill_registry_worker.py||python3 $CTL/leanmill_registry_worker.py --self-test" \
  "leanmill_regression_gate.py||python3 $CTL/leanmill_regression_gate.py --self-test" \
  "leanmill_residual_lifecycle.py||python3 $CTL/leanmill_residual_lifecycle.py --self-test" \
  "leanmill_source_family_allocator.py||python3 $CTL/leanmill_source_family_allocator.py --self-test" \
  "leanmill_source_inventory.py||python3 $CTL/leanmill_source_inventory.py --self-test" \
  "leanmill_source_worker.py||python3 $CTL/leanmill_source_worker.py --self-test" \
  "leanmill_station_action_contract.py||python3 $CTL/leanmill_station_action_contract.py --self-test" \
  "leanmill_station_health_dashboard.py||python3 $CTL/leanmill_station_health_dashboard.py --self-test" \
  "leanmill_station_scheduler.py||python3 $CTL/leanmill_station_scheduler.py --self-test" \
  "leanmill_vnext_coverage_gate.py||python3 $CTL/leanmill_vnext_coverage_gate.py --self-test" \
  "lean_proofstate_feature_extract.py||python3 $CTL/lean_proofstate_feature_extract.py --self-test" \
  "lean_repair_policy_score.py||python3 $CTL/lean_repair_policy_score.py --self-test" \
  "lean_repair_trajectory_dataset.py||python3 $CTL/lean_repair_trajectory_dataset.py --self-test" \
  "lean_trace_feature_extract.py||python3 $CTL/lean_trace_feature_extract.py --self-test" \
  "path_c_curriculum_queue.py||python3 $CTL/path_c_curriculum_queue.py --self-test" \
  "path_c_canary_replay.py||python3 $CTL/path_c_canary_replay.py --self-test" \
  "path_c_temporal_basin_scorer.py||python3 $CTL/path_c_temporal_basin_scorer.py --self-test" \
  "prepare_lean_backends.py||python3 $CTL/prepare_lean_backends.py --self-test"; do
  lbl="${pair%%||*}"; cmd="${pair##*||}"
  st LOCAL "$lbl" "$LST $cmd"
  st VPS   "$lbl" "$RST $cmd'"
done

echo "=== VERDICT ==="
if [ "$fail" = "0" ]; then
  echo "PARITY OK — local and VPS are byte-identical on all canonical"
  echo "harness files and all self-tests pass identically on both."
  exit 0
else
  echo "PARITY FAILED — see DRIFT/FAIL lines above. Re-run after fix;"
  echo "do NOT run a cross-machine experiment until this is OK."
  exit 1
fi
