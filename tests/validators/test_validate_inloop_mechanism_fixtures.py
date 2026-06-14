from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "public" / "validators" / "validate_inloop_mechanism_fixtures.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("validate_inloop_mechanism_fixtures_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_mechanism_status_summary_classifies_every_fixture() -> None:
    module = _load_module()
    results = [
        module.FixtureResult(
            name=name,
            passed=True,
            detail=f"{name} passed",
            evidence={},
        )
        for name in module.MECHANISM_STATUS
    ]

    summary = module.mechanism_status_summary(results)

    assert summary["unmapped_fixtures"] == []
    assert summary["missing_fixture_results"] == []
    assert summary["by_status"]["active"]["total"] >= 1
    assert summary["by_status"]["advisory"]["total"] >= 1
    assert summary["by_status"]["diagnostic"]["total"] >= 1
    for row in summary["rows"]:
        assert row["try_command"]
        assert row["test_reference"]


def test_render_text_includes_status_coverage() -> None:
    module = _load_module()
    results = [
        module.FixtureResult(
            name="pivot_heuristics",
            passed=True,
            detail="pivot ok",
            evidence={},
        )
    ]
    payload = {
        "passed": True,
        "num_passed": 1,
        "num_fixtures": 1,
        "results": [module.asdict(result) for result in results],
        "mechanism_status": module.mechanism_status_summary(results),
    }

    rendered = module.render_text(payload)

    assert "coverage: active=1/1" in rendered
    assert "[active; stagnation pivot routing]" in rendered
    assert "try: make inloop-fixture-validate JSON=1" in rendered
    assert "test: src/ztare/validator/tests/pivot_heuristics_fixture_regression.py" in rendered


def test_static_wiring_fixture_ignores_comment_only_markers(tmp_path, monkeypatch) -> None:
    module = _load_module()
    loop = tmp_path / "loop.py"
    blitz = tmp_path / "blitz.py"
    rubric = tmp_path / "rubric.py"
    loop.write_text(
        """
# apply_rubric_mode_defaults validate_rubric_mode_contract
# _primitive_class_history_packet maybe_track_primitive_class_rotation
# dispatch_mutator_blitz _materialize_blitz_survival_report_for_run
# resolve_stagnation_pivot_state
def main():
    return None
""",
        encoding="utf-8",
    )
    blitz.write_text(
        """
# should_run_parallel recombine enable_recombination
def main():
    return None
""",
        encoding="utf-8",
    )
    rubric.write_text(
        """
# rubric_mode='newton'
# Kepler-mode rubric
def main():
    return None
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "AUTORESEARCH_LOOP", loop)
    monkeypatch.setattr(module, "BLITZ_DISPATCH", blitz)
    monkeypatch.setattr(module, "RUBRIC_MODE_RESOLVER", rubric)

    result = module._fixture_static_autoresearch_wiring()

    assert result.passed is False
    assert "autoresearch_loop.rubric_mode_defaults" in result.evidence["missing"]
    assert "autoresearch_loop.r1_retry_error_history" in result.evidence["missing"]
    assert "blitz_dispatch.parallel_trigger" in result.evidence["missing"]
    assert "rubric_mode_resolver.newton_gate" in result.evidence["missing"]


def test_static_wiring_fixture_accepts_executable_calls(tmp_path, monkeypatch) -> None:
    module = _load_module()
    loop = tmp_path / "loop.py"
    blitz = tmp_path / "blitz.py"
    rubric = tmp_path / "rubric.py"
    loop.write_text(
        """
def main():
    apply_rubric_mode_defaults(rubric_data)
    validate_rubric_mode_contract(rubric_data)
    _primitive_class_history_packet()
    maybe_track_primitive_class_rotation()
    dispatch_mutator_blitz()
    _materialize_blitz_survival_report_for_run()
    resolve_stagnation_pivot_state()
    render_loop_control_prompt_context()
    _r1_error_history.append(_r1_last_error)
    retry_error_history=_r1_error_history
    thesis_control_mode = "x"
""",
        encoding="utf-8",
    )
    blitz.write_text(
        """
def main():
    should_run_parallel()
    if rubric_data.get("enable_recombination"):
        recombine()
""",
        encoding="utf-8",
    )
    rubric.write_text(
        """
NEWTON = "rubric_mode='newton'"
KEPLER = "Kepler-mode rubric"
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "AUTORESEARCH_LOOP", loop)
    monkeypatch.setattr(module, "BLITZ_DISPATCH", blitz)
    monkeypatch.setattr(module, "RUBRIC_MODE_RESOLVER", rubric)

    result = module._fixture_static_autoresearch_wiring()

    assert result.passed is True
    assert result.evidence["missing"] == {}
