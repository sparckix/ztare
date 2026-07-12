from __future__ import annotations

from ztare.validator.core.mutation_contract import parse_mutation_declaration
from ztare.validator.core.runner_r1_lifecycle import (
    RunnerR1State,
    ensure_committed_runner_r1_declaration,
    render_runner_r1_lifecycle_surface,
)


def _declaration():
    return parse_mutation_declaration(
        {
            "scope_delta": "EVIDENCE_BOUNDARY",
            "claim_delta_type": "NARROWING",
            "thesis_control_mode": "NARROW_EVIDENCE_BOUNDARY",
            "primitive_invoked": None,
            "touched_artifacts": "runner_runtime",
        }
    )


def test_runner_r1_payload_retry_carries_committed_declaration() -> None:
    carried = ensure_committed_runner_r1_declaration(
        '{"test_model_py": "def step(grid, action, t):\\n    return grid"}',
        _declaration(),
    )

    assert carried.startswith("```json")
    assert '"scope_delta": "EVIDENCE_BOUNDARY"' in carried
    assert '"touched_artifacts": [' in carried
    assert '"runner_runtime"' in carried
    assert '{"test_model_py"' in carried


def test_runner_r1_retry_cannot_reopen_declaration() -> None:
    attempted_reopen = """```json
{"scope_delta":"MULTI_ARTIFACT","claim_delta_type":"WIDENING","thesis_control_mode":"EXPLOIT_CURRENT_THESIS","primitive_invoked":null,"touched_artifacts":["other"]}
```

{"test_model_py": "def step(grid, action, t):\\n    return grid"}
"""

    carried = ensure_committed_runner_r1_declaration(attempted_reopen, _declaration())

    assert '"scope_delta": "EVIDENCE_BOUNDARY"' in carried
    assert "MULTI_ARTIFACT" not in carried
    assert "WIDENING" not in carried
    assert '{"test_model_py"' in carried


def test_runner_r1_lifecycle_surface_exposes_transition_table() -> None:
    surface = render_runner_r1_lifecycle_surface(
        state=RunnerR1State.PAYLOAD_RETRY,
        declaration=_declaration(),
        last_error="candidate payload regressed",
    )

    assert "ztare-runner-r1-lifecycle-v1" in surface
    assert "payload_retry_generated" in surface
    assert "declaration becomes immutable control state" in surface
    assert "candidate payload regressed" in surface
