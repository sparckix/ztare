from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
AUTORESEARCH_LOOP = REPO_ROOT / "src" / "ztare" / "validator" / "autoresearch_loop.py"
TEST_THESIS = REPO_ROOT / "src" / "ztare" / "validator" / "test_thesis.py"
GENERATE_COMMITTEE = REPO_ROOT / "src" / "ztare" / "validator" / "generate_committee.py"


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
