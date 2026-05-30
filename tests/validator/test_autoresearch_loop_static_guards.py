from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
AUTORESEARCH_LOOP = REPO_ROOT / "src" / "ztare" / "validator" / "autoresearch_loop.py"


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

