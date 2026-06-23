from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
AUTORESEARCH_LOOP = REPO_ROOT / "src" / "ztare" / "validator" / "autoresearch_loop.py"
TEST_THESIS = REPO_ROOT / "src" / "ztare" / "validator" / "test_thesis.py"
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
    assert "iteration_test_cmd" in run_targets


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


def test_single_mutator_route_avoids_parallel_wrapper_until_rubric_triggers() -> None:
    source = AUTORESEARCH_LOOP.read_text(encoding="utf-8")

    assert "should_run_parallel" in source
    assert "_run_parallel_mutator" in source
    assert "_parallel_reason" in source

    policy_pos = source.index("_run_parallel_mutator, _parallel_k, _parallel_reason = should_run_parallel(")
    direct_single_pos = source.index('new_content = _single_mutate("")', policy_pos)
    dispatch_pos = source.index("dispatch_mutator_blitz(BlitzDispatchInputs(", policy_pos)
    assert direct_single_pos < dispatch_pos


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


def test_primitive_class_rotation_tracks_judged_candidates_not_only_champions() -> None:
    source = AUTORESEARCH_LOOP.read_text(encoding="utf-8")
    assert source.count("maybe_track_primitive_class_rotation(") == 1

    r3_branch_pos = source.index("if not selection_record.candidate_admissible:")
    r3_track_pos = source.index("_track_primitive_class_rotation_candidate(", r3_branch_pos)
    r3_continue_pos = source.index("continue", r3_branch_pos)
    assert r3_track_pos < r3_continue_pos
    assert 'outcome="r3_rejected"' in source[r3_track_pos:r3_continue_pos]

    candidate_improved_pos = source.index("_candidate_improved = _capped_strict")
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
