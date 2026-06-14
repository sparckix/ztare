"""Fixture regression for the GP-030 deterministic charter-gate first slice.

Covers the pure parser, the harness invocation contract, the
fail-closed semantics, and the soft-cap translation. The harness
contract is exercised against a real ``test_model.py`` written into a
tempdir so the subprocess path is real (no mocks). Mocking subprocess
would defeat the purpose: the harness contract is the decision-critical
piece per Codex Turn 2, and the things that break in practice
(--emit-deterministic-gates flag handling, JSON shape, exit code) are
exactly what subprocess mocking elides.
"""

from __future__ import annotations

import sys
import tempfile
import textwrap
from pathlib import Path

from src.ztare.gates.deterministic_charter_gates import (
    GATE_FAILURE_SCORE_CAP,
    DeterministicGateSpec,
    declared_gate_names,
    evaluate_deterministic_charter_gates,
    gate_results_to_dicts,
    parse_deterministic_gates_from_charter,
    soft_cap_entries_for_evaluation,
)


# ---------------------------------------------------------------------------
# Charter parsing
# ---------------------------------------------------------------------------


_VALID_CHARTER = """\
# project_charter

Some prose.

## Anchor Proxies

- foo
- bar

## Deterministic Gates

```yaml
deterministic_gates:
  - name: global_residual
    metric: max_abs_residual
    threshold: 0.05
    operator: lt
    evidence_source: evidence.txt
    scope: all_sweeps
  - name: peak_location
    metric: relative_error
    threshold: 0.15
    operator: lt
    evidence_source: evidence.txt
    scope: phi_peak_per_sweep
```

## Other Section

ignored.
"""


def test_parse_two_well_formed_gates() -> None:
    gates = parse_deterministic_gates_from_charter(_VALID_CHARTER)
    assert len(gates) == 2, gates
    assert gates[0].name == "global_residual"
    assert gates[0].metric == "max_abs_residual"
    assert gates[0].threshold == 0.05
    assert gates[0].operator == "lt"
    assert gates[0].evidence_source == "evidence.txt"
    assert gates[0].scope == "all_sweeps"
    assert gates[1].name == "peak_location"
    assert gates[1].threshold == 0.15


def test_parse_returns_empty_when_no_section() -> None:
    text = "# proj\n\n## Anchor Proxies\n\n- foo\n"
    assert parse_deterministic_gates_from_charter(text) == []


def test_parse_returns_empty_when_section_has_no_fence() -> None:
    text = "# proj\n\n## Deterministic Gates\n\nfree-form prose, no block.\n"
    assert parse_deterministic_gates_from_charter(text) == []


def test_parse_drops_malformed_gate_with_unknown_operator() -> None:
    text = """\
## Deterministic Gates

```yaml
deterministic_gates:
  - name: bad_gate
    metric: foo
    threshold: 0.1
    operator: somewhere_between
  - name: good_gate
    metric: bar
    threshold: 0.2
    operator: le
```
"""
    gates = parse_deterministic_gates_from_charter(text)
    assert len(gates) == 1, gates
    assert gates[0].name == "good_gate"
    assert gates[0].operator == "le"


def test_parse_drops_gate_with_non_numeric_threshold() -> None:
    text = """\
## Deterministic Gates

```yaml
deterministic_gates:
  - name: bad
    metric: foo
    threshold: not_a_number
    operator: lt
```
"""
    assert parse_deterministic_gates_from_charter(text) == []


def test_parse_handles_none_charter() -> None:
    assert parse_deterministic_gates_from_charter(None) == []


# ---------------------------------------------------------------------------
# Harness invocation — fail-closed paths
# ---------------------------------------------------------------------------


def test_evaluator_no_op_when_charter_has_no_gates() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        evaluation = evaluate_deterministic_charter_gates(
            charter_text="# project\n\nNo gates here.\n",
            test_model_path=Path(tmpdir) / "test_model.py",
        )
    assert evaluation.declared == ()
    assert evaluation.results == ()
    assert evaluation.harness_invoked is False
    assert evaluation.any_failed is False
    assert soft_cap_entries_for_evaluation(evaluation) == []


def test_evaluator_fail_closed_when_test_model_missing() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        evaluation = evaluate_deterministic_charter_gates(
            charter_text=_VALID_CHARTER,
            test_model_path=Path(tmpdir) / "nonexistent_test_model.py",
        )
    assert evaluation.harness_invoked is True
    assert evaluation.failure_count == 2
    assert "missing" in evaluation.harness_failure_reason
    caps = soft_cap_entries_for_evaluation(evaluation)
    assert len(caps) == 2
    for cap in caps:
        assert cap["cap"] == GATE_FAILURE_SCORE_CAP
        assert "fail-closed" in cap["reason"]


def test_evaluator_fail_closed_when_harness_does_not_support_flag() -> None:
    # Legacy harness: ignores unknown flags and exits 0 with no JSON.
    # The first slice still fails closed because the JSON shape is
    # absent. This is the GP-030 first-slice contract: declared gates
    # against a non-cooperating harness must cap the score.
    legacy_harness = textwrap.dedent(
        """\
        import sys
        print("legacy harness running tests")
        sys.exit(0)
        """
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test_model.py"
        path.write_text(legacy_harness, encoding="utf-8")
        evaluation = evaluate_deterministic_charter_gates(
            charter_text=_VALID_CHARTER,
            test_model_path=path,
        )
    assert evaluation.harness_invoked is True
    assert evaluation.failure_count == 2
    assert "JSON" in evaluation.harness_failure_reason


def test_evaluator_fail_closed_when_harness_exits_nonzero() -> None:
    broken_harness = textwrap.dedent(
        """\
        import sys
        print("boom", file=sys.stderr)
        sys.exit(2)
        """
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test_model.py"
        path.write_text(broken_harness, encoding="utf-8")
        evaluation = evaluate_deterministic_charter_gates(
            charter_text=_VALID_CHARTER,
            test_model_path=path,
        )
    assert evaluation.harness_invoked is True
    assert evaluation.failure_count == 2
    assert "exited" in evaluation.harness_failure_reason


# ---------------------------------------------------------------------------
# Harness invocation — happy paths
# ---------------------------------------------------------------------------


_GP030_HARNESS_PASS = textwrap.dedent(
    """\
    import json
    import sys
    if "--emit-deterministic-gates" in sys.argv:
        payload = {
            "gates": [
                {
                    "name": "global_residual",
                    "passed": True,
                    "actual": 0.012,
                    "threshold": 0.05,
                    "operator": "lt",
                    "reason": "max abs residual 0.012 within 0.05",
                },
                {
                    "name": "peak_location",
                    "passed": True,
                    "actual": 0.04,
                    "threshold": 0.15,
                    "operator": "lt",
                    "reason": "peak relative error 0.04 within 0.15",
                },
            ]
        }
        print(json.dumps(payload))
        sys.exit(0)
    sys.exit(0)
    """
)


_GP030_HARNESS_FAIL = textwrap.dedent(
    """\
    import json
    import sys
    if "--emit-deterministic-gates" in sys.argv:
        payload = {
            "gates": [
                {
                    "name": "global_residual",
                    "passed": False,
                    "actual": 1.79,
                    "threshold": 0.05,
                    "operator": "lt",
                    "reason": "max abs residual 1.79 exceeds 0.05 on psi=1.8 sweep",
                },
                {
                    "name": "peak_location",
                    "passed": True,
                    "actual": 0.04,
                    "threshold": 0.15,
                    "operator": "lt",
                    "reason": "peak relative error 0.04 within 0.15",
                },
            ]
        }
        print(json.dumps(payload))
        sys.exit(0)
    sys.exit(0)
    """
)


def test_evaluator_passes_when_all_gates_satisfied() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test_model.py"
        path.write_text(_GP030_HARNESS_PASS, encoding="utf-8")
        evaluation = evaluate_deterministic_charter_gates(
            charter_text=_VALID_CHARTER,
            test_model_path=path,
        )
    assert evaluation.harness_invoked is True
    assert evaluation.harness_failure_reason == ""
    assert evaluation.failure_count == 0
    assert evaluation.any_failed is False
    assert soft_cap_entries_for_evaluation(evaluation) == []
    dicts = gate_results_to_dicts(evaluation)
    assert dicts[0]["passed"] is True
    assert dicts[0]["actual"] == 0.012


def test_evaluator_caps_score_when_one_gate_fails() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test_model.py"
        path.write_text(_GP030_HARNESS_FAIL, encoding="utf-8")
        evaluation = evaluate_deterministic_charter_gates(
            charter_text=_VALID_CHARTER,
            test_model_path=path,
        )
    assert evaluation.harness_invoked is True
    assert evaluation.failure_count == 1
    assert evaluation.any_failed is True
    caps = soft_cap_entries_for_evaluation(evaluation)
    assert len(caps) == 1
    assert caps[0]["cap"] == GATE_FAILURE_SCORE_CAP
    assert "global_residual" in caps[0]["reason"]
    assert "1.79" in caps[0]["reason"]


def test_declared_gate_names_returns_charter_order() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test_model.py"
        path.write_text(_GP030_HARNESS_PASS, encoding="utf-8")
        evaluation = evaluate_deterministic_charter_gates(
            charter_text=_VALID_CHARTER,
            test_model_path=path,
        )
    assert declared_gate_names(evaluation) == ["global_residual", "peak_location"]


def test_evaluator_fails_gate_missing_from_payload() -> None:
    # Harness only emits one of the two declared gates. The missing
    # gate must fail closed because the charter declared it.
    partial_harness = textwrap.dedent(
        """\
        import json
        import sys
        if "--emit-deterministic-gates" in sys.argv:
            payload = {"gates": [{
                "name": "global_residual",
                "passed": True,
                "actual": 0.01,
                "threshold": 0.05,
                "operator": "lt",
                "reason": "ok"
            }]}
            print(json.dumps(payload))
        sys.exit(0)
        """
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test_model.py"
        path.write_text(partial_harness, encoding="utf-8")
        evaluation = evaluate_deterministic_charter_gates(
            charter_text=_VALID_CHARTER,
            test_model_path=path,
        )
    assert evaluation.failure_count == 1
    failed_names = {r.name for r in evaluation.results if not r.passed}
    assert failed_names == {"peak_location"}


_TESTS = (
    test_parse_two_well_formed_gates,
    test_parse_returns_empty_when_no_section,
    test_parse_returns_empty_when_section_has_no_fence,
    test_parse_drops_malformed_gate_with_unknown_operator,
    test_parse_drops_gate_with_non_numeric_threshold,
    test_parse_handles_none_charter,
    test_evaluator_no_op_when_charter_has_no_gates,
    test_evaluator_fail_closed_when_test_model_missing,
    test_evaluator_fail_closed_when_harness_does_not_support_flag,
    test_evaluator_fail_closed_when_harness_exits_nonzero,
    test_evaluator_passes_when_all_gates_satisfied,
    test_evaluator_caps_score_when_one_gate_fails,
    test_declared_gate_names_returns_charter_order,
    test_evaluator_fails_gate_missing_from_payload,
)


def main() -> int:
    failed = 0
    for test in _TESTS:
        try:
            test()
        except AssertionError as exc:
            failed += 1
            print(f"FAIL {test.__name__}: {exc}")
        except Exception as exc:  # pragma: no cover - surfaced to operator
            failed += 1
            print(f"ERROR {test.__name__}: {type(exc).__name__}: {exc}")
        else:
            print(f"PASS {test.__name__}")
    print(f"\n{len(_TESTS) - failed}/{len(_TESTS)} passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
