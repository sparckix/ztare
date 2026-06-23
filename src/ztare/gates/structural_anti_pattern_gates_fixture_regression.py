"""Regression checks for structural anti-pattern gate precision."""

from __future__ import annotations

from ztare.gates.structural_anti_pattern_gates import run_apparatus_meta_match


def _codes(form: str) -> set[str]:
    return {m["code"] for m in run_apparatus_meta_match(form).matches}


def test_rh17_flags_literal_lookup() -> None:
    form = "1.23 if features['study'] == 'kaplan2020' else 0.98"
    assert "RH-17" in _codes(form)


def test_rh17_allows_declared_param_offset_with_zero_baseline() -> None:
    form = (
        "params['pC'] if features['fit_convention'] == "
        "'chinchilla_parametric' else 0.0"
    )
    assert "RH-17" not in _codes(form)


def test_rh17_allows_declared_param_branch() -> None:
    form = "params['a'] if features['modality'] == 'text' else params['b']"
    assert "RH-17" not in _codes(form)


if __name__ == "__main__":
    test_rh17_flags_literal_lookup()
    test_rh17_allows_declared_param_offset_with_zero_baseline()
    test_rh17_allows_declared_param_branch()
    print("structural_anti_pattern_gates_fixture_regression: PASS")
