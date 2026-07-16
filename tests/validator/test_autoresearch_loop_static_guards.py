from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
AUTORESEARCH_LOOP = REPO_ROOT / "src" / "ztare" / "validator" / "autoresearch_loop.py"
TEST_THESIS = REPO_ROOT / "src" / "ztare" / "validator" / "test_thesis.py"
REPAIR_PREFLIGHT = REPO_ROOT / "src" / "ztare" / "validator" / "core" / "repair_preflight.py"
CANDIDATE_PREFLIGHT = REPO_ROOT / "src" / "ztare" / "validator" / "core" / "candidate_preflight.py"
WORLDMODEL_CONTEXT = REPO_ROOT / "src" / "ztare" / "validator" / "core" / "worldmodel_prompt_context.py"
WORLDMODEL_PAYLOAD = REPO_ROOT / "src" / "ztare" / "validator" / "worldmodel_typed_payload.py"
ORCHESTRATOR_PROMPT = REPO_ROOT / "src" / "ztare" / "orchestrator" / "prompt.py"
STRATEGY_DECISION_POLICY = REPO_ROOT / "src" / "ztare" / "research_director" / "strategy_decision_policy.py"
GENERATE_COMMITTEE = REPO_ROOT / "src" / "ztare" / "validator" / "generate_committee.py"
MAKEFILE = REPO_ROOT / "Makefile"


def _main_iteration_loops(tree: ast.AST) -> list[ast.For]:
    loops: list[ast.For] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.For):
            continue
        call = node.iter
        if (
            isinstance(call, ast.Call)
            and isinstance(call.func, ast.Name)
            and call.func.id == "range"
            and len(call.args) == 1
            and isinstance(call.args[0], ast.Name)
            and call.args[0].id == "ITERATIONS"
        ):
            loops.append(node)
    return loops


def test_pre_judge_skip_command_is_iteration_local() -> None:
    """A pre-judge failure must not poison later iterations.

    Regression for the 2026-05-04 Track B false-zero run: iter 1 failed
    pre-judge and rewrote the shared `test_cmd` to `python -c pass`; iter 2/3
    passed pre-judge but still skipped `test_thesis` and re-read stale
    `latest_eval_results.json`.
    """

    source = AUTORESEARCH_LOOP.read_text(encoding="utf-8")
    tree = ast.parse(source)
    loops = _main_iteration_loops(tree)
    assert loops, "Could not find autoresearch_loop main iteration loop"
    main_loop = loops[0]

    skip_ifs = [
        node
        for node in ast.walk(main_loop)
        if isinstance(node, ast.If)
        and "should_skip_judge" in (ast.get_source_segment(source, node.test) or "")
    ]
    assert skip_ifs, "Could not find pre-judge should_skip_judge branch"
    skip_assigned_names = {
        target.id
        for node in ast.walk(skip_ifs[0])
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    }
    assert "test_cmd" not in skip_assigned_names
    assert "iteration_test_cmd" in skip_assigned_names

    run_targets = [
        call.args[0].id
        for call in ast.walk(main_loop)
        if isinstance(call, ast.Call)
        and isinstance(call.func, ast.Attribute)
        and call.func.attr == "run"
        and isinstance(call.func.value, ast.Name)
        and call.func.value.id == "subprocess"
        and call.args
        and isinstance(call.args[0], ast.Name)
    ]
    bound_runner_targets = [
        call.args[0].id
        for call in ast.walk(main_loop)
        if isinstance(call, ast.Call)
        and isinstance(call.func, ast.Name)
        and call.func.id == "_run_test_thesis_command"
        and call.args
        and isinstance(call.args[0], ast.Name)
    ]
    assert "iteration_test_cmd" in (run_targets + bound_runner_targets)


def test_bound_promotion_and_stop_contracts_have_consumers() -> None:
    source = AUTORESEARCH_LOOP.read_text(encoding="utf-8")

    assert "_promotion_decision_present" in source
    assert (
        '_pre_judge_decision.get("candidate_promotion_authorized"), bool'
        in source
    )
    assert 'rubric_data.get("stop_on_gate_pass", False)' in source
    assert '_pre_judge_decision.get("gate_contract_closed") is True' in source


def test_verifier_error_cannot_become_scientific_feedback() -> None:
    source = AUTORESEARCH_LOOP.read_text(encoding="utf-8")

    assert source.count('== "pre_judge_gate_harness_error"') >= 2
    assert "refusing to dispatch" in source
    assert "refusing to convert an apparatus failure into scientific feedback" in source


def test_theorem_packet_substrates_skip_parametric_form_r1_preflight() -> None:
    """Theorem-packet projects must not be bounced on legacy PARAMETRIC_FORM.

    Regression guard for Track B proof-packet substrates: the contract is a
    set of top-level theorem functions plus a project-local harness.  If a
    mutator includes a stale PARAMETRIC_FORM compatibility string, scalar-fit
    AST validation must not hijack the retry prompt away from the theorem
    packet API.
    """

    source = AUTORESEARCH_LOOP.read_text(encoding="utf-8")
    assert "_skip_parametric_form_r1_for_theorem_packet" in source
    assert "theorem_packet_contract" in source
    assert "required_top_level_functions" in source
    assert "require_i_model_in_submission" in source

    skip_pos = source.index("_skip_parametric_form_r1_for_theorem_packet")
    safe_compile_pos = source.index("_ffp_safe_compile", skip_pos)
    assert skip_pos < safe_compile_pos
    guarded_extract = (
        "None\n"
        "                        if _skip_parametric_form_r1_for_theorem_packet\n"
        "                        else _ffp_extract_form"
    )
    assert guarded_extract in source

def test_linear_observable_coercivity_dispatch_uses_literal_label_key() -> None:
    source = AUTORESEARCH_LOOP.read_text(encoding="utf-8")
    assert "enable_linear_observable_coercivity_gate" in source
    assert "linear_observable_coercivity_targets" in source
    assert "linear_observable_coercivity_strict" in source
    assert "_loc_res[\"label\"]" in source or "_loc_res['label']" in source
    assert "_loc_res[label]" not in source
    assert "linear_observable_coercivity.json" in source


def test_mutator_safe_mutate_routes_through_dispatch_model_before_api_call() -> None:
    source = AUTORESEARCH_LOOP.read_text(encoding="utf-8")
    assert "dispatch_env_for_call_site" in source
    assert 'capability = resolve_dispatch_capability("mutator")' in source
    assert "result = dispatch_model(" in source
    assert 'enabled_env=dispatch_env_for_call_site("mutator")' in source

    safe_mutate_start = source.index("def safe_mutate(")
    dispatch_pos = source.index("result = dispatch_model(", safe_mutate_start)
    api_call_pos = source.index("response = RUNTIME.call_text(", safe_mutate_start)
    assert dispatch_pos < api_call_pos


def test_mutator_effective_model_telemetry_uses_call_events_not_set_delta() -> None:
    source = AUTORESEARCH_LOOP.read_text(encoding="utf-8")

    assert "SESSION_MUTATOR_MODEL_EVENTS: list[str] = []" in source
    assert "_CURRENT_ITERATION_MUTATOR_MODEL_EVENT_START = len(SESSION_MUTATOR_MODEL_EVENTS)" in source
    assert "def _record_mutator_effective_model(model_id: str)" in source
    assert "SESSION_MUTATOR_MODEL_EVENTS.append(normalized)" in source

    helper_start = source.index("def _current_iteration_mutator_effective_models()")
    helper_end = source.index("def _record_mutator_effective_model", helper_start)
    helper_source = source[helper_start:helper_end]
    assert "SESSION_MUTATOR_MODEL_EVENTS[_CURRENT_ITERATION_MUTATOR_MODEL_EVENT_START:]" in helper_source
    assert "SESSION_MUTATOR_MODELS_USED" not in helper_source
    assert "current - prior" not in helper_source


def test_r1_retry_prompt_receives_same_iteration_error_history() -> None:
    source = AUTORESEARCH_LOOP.read_text(encoding="utf-8")
    assert "_r1_error_history: list[str] = []" in source
    assert "_r1_error_history.append(_r1_last_error)" in source
    assert "retry_error_history=_r1_error_history" in source

    append_pos = source.index("_r1_error_history.append(_r1_last_error)")
    format_pos = source.index("retry_error_history=_r1_error_history", append_pos)
    retry_call_pos = source.index("new_content = safe_mutate(", format_pos)
    assert append_pos < format_pos < retry_call_pos


def test_workbench_action_receipt_triggers_new_synthesis_turn_not_stale_validation() -> None:
    source = AUTORESEARCH_LOOP.read_text(encoding="utf-8")

    receipt_pos = source.index("if _r1_receipt_only:")
    retry_prompt_pos = source.index("_retry_prompt = format_r1_retry_skeleton(", receipt_pos)
    retry_call_pos = source.index("new_content = safe_mutate(", retry_prompt_pos)
    receipt_branch = source[receipt_pos:retry_prompt_pos]

    assert "_auto_carry_leaf_workbench_receipts(" not in receipt_branch
    assert "re-running validation without another mutator call" not in source
    assert receipt_pos < retry_prompt_pos < retry_call_pos


def test_strategy_decision_policy_imports_optional_kernels_through_single_door() -> None:
    source = STRATEGY_DECISION_POLICY.read_text(encoding="utf-8")

    assert "import_optional_kernel_module" in source
    assert "sys.path" not in source
    assert "ZTARE_COGNITIVE_FIRM_SRC" not in source
    assert "Path(__file__)" not in source
    assert "importlib.import_module" not in source


def test_single_mutator_route_avoids_parallel_wrapper_until_rubric_triggers() -> None:
    source = AUTORESEARCH_LOOP.read_text(encoding="utf-8")

    assert "should_run_parallel" in source
    assert "_run_parallel_mutator" in source
    assert "_parallel_reason" in source

    policy_pos = source.index("_run_parallel_mutator, _parallel_k, _parallel_reason = should_run_parallel(")
    direct_single_pos = source.index('new_content = _single_mutate("")', policy_pos)
    dispatch_pos = source.index("dispatch_mutator_blitz(BlitzDispatchInputs(", policy_pos)
    assert direct_single_pos < dispatch_pos


def test_worldmodel_bounded_discriminator_prompt_uses_transition_contract() -> None:
    source = AUTORESEARCH_LOOP.read_text(encoding="utf-8")
    prompt_source = ORCHESTRATOR_PROMPT.read_text(encoding="utf-8")

    assert "is_worldmodel_submission_contract" in source
    selector_pos = source.index("_specialized_submission_prompt = select_specialized_submission_prompt(")
    numeric_pos = source.index("choose one accepted numeric declaration", selector_pos)
    assert selector_pos < numeric_pos
    assert "CRITICAL OUTPUT REQUIREMENT (THE EXECUTABLE TRANSITION LAW)" not in source

    worldmodel_pos = prompt_source.index(
        "CRITICAL OUTPUT REQUIREMENT (THE EXECUTABLE TRANSITION LAW)"
    )
    worldmodel_block = prompt_source[worldmodel_pos:]
    assert "WORLD_MODEL_SPEC, PROGRAM, or step(grid, action, t)" in worldmodel_block
    assert "PARAMETRIC_FORM, LAGRANGIAN, MODEL_PARAMS" in worldmodel_block
    assert "assertion-only suites" in worldmodel_block
    assert "deterministic replay over visible transitions plus held-out rollout" in worldmodel_block


def test_mutator_document_context_quarantines_stale_root_artifacts_when_candidate_memory_exists() -> None:
    source = AUTORESEARCH_LOOP.read_text(encoding="utf-8")
    context_source = WORLDMODEL_CONTEXT.read_text(encoding="utf-8")

    assert "deterministic_patch_base_document_context" in source
    assert "def deterministic_patch_base_document_context(" in context_source
    assert "candidate_memory.json" in context_source
    assert "ztare-candidate-memory-v1" in context_source
    assert "admissible_candidate_memory_records(" in context_source
    assert "require_submission_source=True" in context_source
    assert "ROOT ARTIFACTS QUARANTINED" in context_source
    assert "Root prose omitted from mutation context" in context_source
    assert "`## Deterministic Candidate Memory` patch base" in context_source
    assert "root_prose_matches_patch_base" in context_source
    assert "root_test_model_matches_patch_base" in context_source
    assert "or anchor in current_test_model" not in context_source
    assert "return None\n    root_code_matches_patch_base" not in context_source

    import_pos = source.index("deterministic_patch_base_document_context")
    call_pos = source.index("authority_document_context = deterministic_patch_base_document_context(", import_pos)
    default_pos = source.index("default_document_context =", call_pos)
    normal_doc_pos = source.index("document_context = default_document_context", default_pos)
    assert import_pos < call_pos < default_pos < normal_doc_pos


def test_patch_base_regression_preflight_is_in_r1_retry_path() -> None:
    source = AUTORESEARCH_LOOP.read_text(encoding="utf-8")
    candidate_preflight_source = CANDIDATE_PREFLIGHT.read_text(encoding="utf-8")
    repair_preflight_source = REPAIR_PREFLIGHT.read_text(encoding="utf-8")

    assert "run_candidate_preflights(" in source
    assert "CandidatePreflightRequest(" in source
    assert "patch_base_regression_retry_message" in candidate_preflight_source
    assert "PATCH_BASE_IMPROVEMENT_PRECHECK" in repair_preflight_source
    preflight_pos = source.index("run_candidate_preflights(")
    retry_pos = source.index("format_r1_retry_skeleton", preflight_pos)
    pre_judge_pos = source.index("run_pre_judge_gate_harness", retry_pos)
    assert preflight_pos < retry_pos < pre_judge_pos


def test_leaf_workbench_preflight_uses_substrate_injected_markers() -> None:
    source = AUTORESEARCH_LOOP.read_text(encoding="utf-8")
    preflight_source = REPAIR_PREFLIGHT.read_text(encoding="utf-8")
    candidate_preflight_source = CANDIDATE_PREFLIGHT.read_text(encoding="utf-8")

    assert "leaf_workbench_retry_message" in candidate_preflight_source
    assert "WORLD_MODEL_LEAF_WORKBENCH_FACT_MARKERS" in candidate_preflight_source
    assert "is_worldmodel_contract=is_worldmodel_submission_contract(rubric_data)" in source
    assert "fact_markers" in preflight_source
    assert "mandatory patch base" not in preflight_source
    assert "inspect_worldmodel_" not in preflight_source

    preflight_pos = source.index("run_candidate_preflights(")
    retry_pos = source.index("format_r1_retry_skeleton", preflight_pos)
    preflight_block = source[preflight_pos:retry_pos]
    assert "_pre_judge_probe_test_model.py" not in preflight_block


def test_mutator_briefing_routes_candidate_memory_visibility_to_machinery_cards() -> None:
    source = AUTORESEARCH_LOOP.read_text(encoding="utf-8")

    assert "candidate_memory.json" in source
    assert "from ztare.worldmodel.machinery_contradictions import detect_and_card as _detect_machinery" in source
    assert "candidate_memory_records=memory_records" in source
    assert "prompt_text=_briefing_block" in source

    render_pos = source.index("_briefing_render = render_default_briefing_context")
    detector_pos = source.index("candidate_memory_records=memory_records", render_pos)
    context_pos = source.index("mutator_briefing_context = _briefing_block", detector_pos)
    assert render_pos < detector_pos < context_pos


def test_strategy_card_receipts_are_prompted_outside_python_blocks() -> None:
    source = AUTORESEARCH_LOOP.read_text(encoding="utf-8")
    prompt_source = ORCHESTRATOR_PROMPT.read_text(encoding="utf-8")
    context_source = WORLDMODEL_CONTEXT.read_text(encoding="utf-8")
    candidate_preflight_source = CANDIDATE_PREFLIGHT.read_text(encoding="utf-8")

    assert "select_specialized_submission_prompt" in source
    assert "strategy_card_obligation_prompt(project_dir)" in prompt_source
    assert "Place the `STRATEGY_CARD_DISCHARGE:` line in markdown outside the Python" in context_source
    assert "Never put this receipt inside a string literal, comment," in context_source
    assert "strategy_card_retry_message" in candidate_preflight_source
    assert "Worldmodel typed payload contract" in source


def test_worldmodel_mutator_uses_typed_payload_contract() -> None:
    source = AUTORESEARCH_LOOP.read_text(encoding="utf-8")
    prompt_source = ORCHESTRATOR_PROMPT.read_text(encoding="utf-8")
    payload_source = WORLDMODEL_PAYLOAD.read_text(encoding="utf-8")

    assert "select_specialized_submission_prompt" in source
    assert "worldmodel_typed_payload_contract_prompt()" in prompt_source
    assert "WORLDMODEL TYPED PAYLOAD CONTRACT" in payload_source
    assert "`control_receipts`: list" in payload_source
    assert "`test_model_py`: string" in payload_source
    assert "WORLD_MODEL_SPEC` means a literal catalog spec with non-empty `actions`" in payload_source
    assert "_parse_worldmodel_payload_with_retry" in source
    assert "render_worldmodel_typed_payload(payload_obj)" in source
    assert "Worldmodel typed payload contract reject" in source
    assert "validate_worldmodel_carrier_source(python_code)" in source


def test_worldmodel_contract_skips_bounded_discriminator_suite_validation() -> None:
    source = AUTORESEARCH_LOOP.read_text(encoding="utf-8")

    assert "is_worldmodel_contract = is_worldmodel_submission_contract(rubric_data)" in source
    assert "Worldmodel submission missing executable transition carrier" in source
    assert (
        "python_code is not None\n"
        "        and not is_worldmodel_contract\n"
        "        and (falsification_mode or \"numerical_proof\")"
    ) in source


def test_leaf_workbench_capability_proposals_sync_before_missing_carrier_reject() -> None:
    source = AUTORESEARCH_LOOP.read_text(encoding="utf-8")

    sync_pos = source.index("candidate_thesis_pre_carrier")
    reject_pos = source.index("Worldmodel submission missing executable transition carrier")
    assert sync_pos < reject_pos


def test_blocked_strategy_card_defers_patch_base_precheck() -> None:
    source = CANDIDATE_PREFLIGHT.read_text(encoding="utf-8")

    assert "strategy_card_retry_message" in source
    assert "patch_base_regression_retry_message" in source
    strategy_pos = source.index("strategy_card_retry_message")
    patch_pos = source.index("patch_base_regression_retry_message", strategy_pos)
    assert strategy_pos < patch_pos


def test_strategy_card_preflight_uses_executable_carrier_identity() -> None:
    source = AUTORESEARCH_LOOP.read_text(encoding="utf-8")
    candidate_preflight_source = CANDIDATE_PREFLIGHT.read_text(encoding="utf-8")

    assert "_executable_candidate_source = _ensure_canonical_model_aliases(python_code or \"\")" in source
    assert "_receipt_candidate_source" not in source
    assert "executable_candidate_source=_executable_candidate_source" in source
    assert "never the surrounding" in candidate_preflight_source
    call_pos = candidate_preflight_source.index("strategy_card_retry_message(")
    call_block = candidate_preflight_source[call_pos: candidate_preflight_source.index(")", call_pos) + 1]
    assert "candidate_source=candidate_source" in call_block


def test_test_thesis_uses_deterministic_gate_payload_for_pre_judge_projects() -> None:
    source = TEST_THESIS.read_text(encoding="utf-8")

    assert "def run_project_local_deterministic_gate_harness(" in source
    helper_pos = source.index("def run_project_local_deterministic_gate_harness(")
    pre_call_pos = source.index(
        "pre_prose_deterministic_gate = run_project_local_deterministic_gate_harness(",
        helper_pos,
    )
    attacker_pos = source.index("if pre_prose_deterministic_gate and pre_prose_deterministic_gate[\"candidate_failed\"]:", pre_call_pos)
    dynamic_attacker_pos = source.index("elif args.dynamic and os.path.exists(DYNAMIC_RUBRIC_PATH):", attacker_pos)
    level3_reuse_pos = source.index("if pre_prose_deterministic_gate is not None:", dynamic_attacker_pos)

    assert helper_pos < pre_call_pos < attacker_pos < dynamic_attacker_pos < level3_reuse_pos
    helper_block = source[helper_pos:pre_call_pos]
    assert "--emit-deterministic-gates" in helper_block
    assert "Candidate failed the project-local" in helper_block
    assert "deterministic gate harness did not" in helper_block
    assert '"test_suite_status": "fail_assert"' in helper_block
    assert "consume_pre_judge_gate_receipt(" in helper_block
    assert "timeout=120" in helper_block
    assert "bound_gate_payload = load_bound_pre_judge_gate_payload()" in helper_block


def test_make_autoresearch_loop_disables_model_fallback_by_default() -> None:
    source = MAKEFILE.read_text(encoding="utf-8")

    assert "MODEL_FALLBACK ?= 0" in source
    assert "AUTORESEARCH_MODEL_FALLBACK_FLAG := $(if $(filter 1 true yes,$(MODEL_FALLBACK)),,--no_model_fallback)" in source
    assert "MODEL_FALLBACK_ENV := ZTARE_DISABLE_MODEL_FALLBACK=$(if $(filter 1 true yes,$(MODEL_FALLBACK)),0,1)" in source
    assert "EVIDENCE_SEARCH_BACKEND ?= auto" in source
    assert "$(AUTORESEARCH_MODEL_FALLBACK_FLAG)" in source
    assert "$(MODEL_FALLBACK_ENV) $(PYTHON) -m ztare.workspace.compile_evidence" in source
    assert "$(MODEL_FALLBACK_ENV) $(PYTHON) -m ztare.workspace.fetch_evidence" in source
    assert "--search-backend $(EVIDENCE_SEARCH_BACKEND)" in source
    assert "MODEL_FALLBACK=$(MODEL_FALLBACK)" in source


def test_control_followup_records_allow_and_block_decisions() -> None:
    source = AUTORESEARCH_LOOP.read_text(encoding="utf-8")

    pivot_decision_pos = source.index(
        "_pivot_followup_decision = evaluate_control_followup("
    )
    pivot_record_pos = source.index(
        "record_control_followup_decision(",
        pivot_decision_pos,
    )
    pivot_block_pos = source.index(
        "if not _pivot_followup_decision.allowed:",
        pivot_decision_pos,
    )
    assert pivot_decision_pos < pivot_record_pos < pivot_block_pos

    blitz_decision_pos = source.index(
        "_blitz_followup_decision = evaluate_control_followup("
    )
    blitz_record_pos = source.index(
        "record_control_followup_decision(",
        blitz_decision_pos,
    )
    blitz_block_pos = source.index(
        "if not _blitz_followup_decision.allowed:",
        blitz_decision_pos,
    )
    assert blitz_decision_pos < blitz_record_pos < blitz_block_pos


def test_baseline_eval_materializes_eval_history_before_iteration_loop() -> None:
    source = AUTORESEARCH_LOOP.read_text(encoding="utf-8")

    baseline_eval_pos = source.index('context_label="baseline latest_eval_results.json"')
    baseline_append_pos = source.index("_append_eval_history_record(", baseline_eval_pos)
    iteration_loop_pos = source.index("for i in range(ITERATIONS):", baseline_eval_pos)
    baseline_block = source[
        baseline_append_pos:source.index("best_score = res", baseline_append_pos)
    ]

    assert baseline_eval_pos < baseline_append_pos < iteration_loop_pos
    assert '"iteration": 0' in baseline_block
    assert '"artifact_refs": _eval_history_artifact_refs(' in baseline_block
    assert "LATEST_EVAL_RESULTS_PATH" in baseline_block


def test_baseline_eval_uses_pre_judge_gate_before_test_thesis() -> None:
    source = AUTORESEARCH_LOOP.read_text(encoding="utf-8")

    baseline_cmd_pos = source.index("baseline_test_cmd = list(test_cmd)")
    gate_call_pos = source.index(
        "baseline_pre_judge_gate_result = run_pre_judge_gate_harness(",
        baseline_cmd_pos,
    )
    skip_pos = source.index(
        "baseline_test_cmd = [sys.executable, \"-c\", \"pass\"]",
        gate_call_pos,
    )
    run_pos = source.index("_run_test_thesis_command(", skip_pos)
    load_pos = source.index('context_label="baseline latest_eval_results.json"', run_pos)

    assert baseline_cmd_pos < gate_call_pos < skip_pos < run_pos < load_pos
    gate_block = source[gate_call_pos:run_pos]
    assert "latest_eval_results_path=LATEST_EVAL_RESULTS_PATH" in gate_block
    assert 'candidate_path=f"{PROJECT_DIR}/test_model.py"' in gate_block
    assert "baseline_pre_judge_gate_result.payload" in source[run_pos:load_pos]


def test_baseline_eval_cache_binds_to_gate_footprint_before_skip() -> None:
    source = AUTORESEARCH_LOOP.read_text(encoding="utf-8")

    import_pos = source.index("evaluation_cache_key as _evaluation_cache_key")
    key_pos = source.index("baseline_eval_cache_key = _evaluation_cache_key(", import_pos)
    load_pos = source.index("_cached_baseline_eval = _load_cached_evaluation(", key_pos)
    write_pos = source.index("Path(LATEST_EVAL_RESULTS_PATH).write_text(", load_pos)
    skip_pos = source.index("baseline_test_cmd = [sys.executable, \"-c\", \"pass\"]", write_pos)
    store_pos = source.index("_store_cached_evaluation(", skip_pos)

    assert import_pos < key_pos < load_pos < write_pos < skip_pos < store_pos
    cache_block = source[key_pos:load_pos]
    assert "gate_payload=baseline_pre_judge_gate_result.payload" in cache_block
    assert "rubric_path=MAIN_RUBRIC_PATH" in cache_block
    assert "WORKING_PATH" in cache_block
    assert "EVIDENCE_PATH" in cache_block
    assert "PROJECT_CHARTER_PATH" in cache_block
    assert "strategy_experiments.jsonl" in cache_block


def test_eval_history_writer_carries_artifact_refs_and_reports_errors() -> None:
    source = AUTORESEARCH_LOOP.read_text(encoding="utf-8")

    loop_pos = source.index("for i in range(ITERATIONS):")
    per_iter_pos = source.index("_append_eval_history_record(", loop_pos)
    per_iter_block = source[per_iter_pos:source.index("record_latent_distance(", per_iter_pos)]

    assert "_eval_history_artifact_refs(" in per_iter_block
    assert '"artifact_refs": _eval_history_artifact_refs(' in per_iter_block
    assert "test_model_path" in per_iter_block
    assert "_submission_snapshot_py_path" in per_iter_block
    assert "eval_history iteration append error" in per_iter_block
    assert "pass  # fail-silent telemetry" not in per_iter_block
    assert '"weakest_point": new_eval.get("weakest_point") or ""' in per_iter_block
    assert 'weakest_point") or "")[:200]' not in source


def test_judge_safe_generate_routes_through_dispatch_model_before_api_call() -> None:
    source = TEST_THESIS.read_text(encoding="utf-8")
    assert "dispatch_env_for_call_site" in source
    assert 'capability = resolve_dispatch_capability("judge")' in source
    assert 'enabled_env=dispatch_env_for_call_site("judge")' in source
    assert "ZTARE_AUTORESEARCH_JUDGE_AGENT_RUNTIME" in source
    assert "RESPONSE CONTRACT FOR SUBSCRIPTION WORKER" in source

    safe_generate_start = source.index("def safe_generate(")
    dispatch_pos = source.index("result = dispatch_model(", safe_generate_start)
    api_call_pos = source.index("response = RUNTIME.call_text(", safe_generate_start)
    assert dispatch_pos < api_call_pos


def test_project_local_deterministic_gate_failure_short_circuits_prose_judge() -> None:
    source = TEST_THESIS.read_text(encoding="utf-8")

    assert "def deterministic_gate_failure_evaluation(" in source
    assert '"deterministic_gate_short_circuit": True' in source
    assert '"judge_skipped": True' in source
    assert "project-local deterministic gate failed" in source
    assert "Pre-prose deterministic gate failed; skipping attacker critique." in source
    assert "Prose attacker skipped: project-local deterministic gates already" in source

    fail_flag_pos = source.index(
        "_project_local_deterministic_gate_failed = bool("
    )
    short_circuit_pos = source.index(
        "if args.deterministic_score_gates and _project_local_deterministic_gate_failed:",
        fail_flag_pos,
    )
    synthetic_eval_pos = source.index(
        "evaluation = deterministic_gate_failure_evaluation(",
        short_circuit_pos,
    )
    judge_call_pos = source.index(
        "evaluation = run_meta_judge(",
        short_circuit_pos,
    )
    level3_append_pos = source.index(
        "### LEVEL 3 QUANTITATIVE UNIT TEST RESULTS:",
        fail_flag_pos,
    )

    assert fail_flag_pos < level3_append_pos < short_circuit_pos < synthetic_eval_pos < judge_call_pos


def test_test_thesis_does_not_materialize_projects_symlink_shim() -> None:
    source = TEST_THESIS.read_text(encoding="utf-8")

    assert "symlink_to" not in source
    assert "PROJECT_DIR/projects" not in source
    assert "projects/<slug>/... are a" in source


def test_committee_generation_routes_through_dispatch_model_before_api_call() -> None:
    source = GENERATE_COMMITTEE.read_text(encoding="utf-8")
    assert "dispatch_env_for_call_site" in source
    assert 'capability = resolve_dispatch_capability("committee")' in source
    assert 'enabled_env=dispatch_env_for_call_site("committee")' in source
    assert "ZTARE_AUTORESEARCH_COMMITTEE_AGENT_RUNTIME" in source
    assert "RESPONSE CONTRACT FOR SUBSCRIPTION WORKER" in source

    safe_generate_start = source.index("def safe_generate_committee(")
    dispatch_pos = source.index("result = dispatch_model(", safe_generate_start)
    api_call_pos = source.index("_RUNTIME.call_text(", safe_generate_start)
    assert dispatch_pos < api_call_pos

    # Provider decoupling must not silently change the established Gemini
    # structured-output or deadline semantics. Google is imported only after
    # subscription dispatch has been ruled out; other providers receive the
    # array schema as a prompt contract rather than an incompatible
    # chat-completions `json_object` constraint.
    google_import_pos = source.index("from google import genai", safe_generate_start)
    gemini_call_pos = source.index("client.models.generate_content", google_import_pos)
    assert dispatch_pos < google_import_pos < gemini_call_pos
    assert "types.GenerateContentConfig(**config)" in source[google_import_pos:gemini_call_pos]
    assert "future.result(timeout=150)" in source[gemini_call_pos:]
    non_google_block = source[api_call_pos:google_import_pos]
    assert "full_prompt = _prompt_with_response_config_hint(prompt, config)" in source[safe_generate_start:api_call_pos]
    assert "config=config" not in non_google_block


def test_primitive_class_rotation_tracks_judged_candidates_not_only_champions() -> None:
    source = AUTORESEARCH_LOOP.read_text(encoding="utf-8")
    assert source.count("maybe_track_primitive_class_rotation(") == 1

    r3_branch_pos = source.index("if not selection_record.candidate_admissible:")
    r3_track_pos = source.index("_track_primitive_class_rotation_candidate(", r3_branch_pos)
    r3_continue_pos = source.index("continue", r3_branch_pos)
    assert r3_track_pos < r3_continue_pos
    assert 'outcome="r3_rejected"' in source[r3_track_pos:r3_continue_pos]

    promotion_verdict_pos = source.index(
        '_promotion_decision_present = isinstance('
    )
    candidate_improved_pos = source.index(
        "_candidate_improved = bool(", promotion_verdict_pos
    )
    assert "candidate_promotion_authorized" in source[
        promotion_verdict_pos:candidate_improved_pos + 240
    ]
    judged_track_pos = source.index(
        "_track_primitive_class_rotation_candidate(",
        candidate_improved_pos,
    )
    champion_branch_pos = source.index("if _candidate_improved:", judged_track_pos)
    assert judged_track_pos < champion_branch_pos
    assert '"non_improving_candidate"' in source[judged_track_pos:champion_branch_pos]
    assert '"champion_promoted"' in source[judged_track_pos:champion_branch_pos]


def test_global_soft_penalties_apply_before_post_harness_import_fallback() -> None:
    source = AUTORESEARCH_LOOP.read_text(encoding="utf-8")

    soft_branch_pos = source.index(
        'elif _global_gate_payload.get("failure_count", 0) > 0:'
    )
    score_mutation_pos = source.index('new_eval["score"] = _adjusted_score', soft_branch_pos)
    score_cap_pos = source.index(
        '_record_deterministic_score_override(',
        soft_branch_pos,
    )
    post_harness_pos = source.index("# GP-157 Cage post-harness dispatch.", soft_branch_pos)
    assert soft_branch_pos < score_cap_pos < score_mutation_pos < post_harness_pos

    post_harness_block = source[
        post_harness_pos:source.index("except Exception as _gg_exc:", post_harness_pos)
    ]
    assert 'new_eval["score"] = max(0, int(new_eval.get("score", 0)) + _penalty)' not in post_harness_block


def test_control_only_turn_cannot_be_coerced_through_candidate_snapshot_or_gate() -> None:
    source = AUTORESEARCH_LOOP.read_text(encoding="utf-8")

    assert (
        '_control_only_sentinel is None\n'
        '        and os.environ.get("MUTATOR_SUBMISSION_SNAPSHOT", "1") != "0"'
        in source
    )
    assert "if _control_only_sentinel is None and _adherence_path.exists():" in source
    assert (
        'if rubric_data.get("pre_judge_gate_harness") and _control_only_sentinel is None:'
        in source
    )


def test_bound_pre_judge_promotion_authority_fences_champion_selection() -> None:
    source = AUTORESEARCH_LOOP.read_text(encoding="utf-8")

    assert '"candidate_promotion_authorized"' in source
    promotion_block = source[
        source.index("_pre_judge_payload = new_eval.get"):
        source.index("_track_primitive_class_rotation_candidate", source.index("_pre_judge_payload = new_eval.get"))
    ]
    assert "_candidate_improved = bool(" in promotion_block
    assert "_promotion_authorized" in promotion_block
