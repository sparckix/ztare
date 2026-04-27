"""GP-048 apparatus-feedback surface tests.

Covers all three surfaces (telemetry, cohort injection, farther-tail veto)
without a live LLM. Sanitization checks are load-bearing: they assert that
no true gate name, no hidden value, and no topology enumeration ever leaks
into the rendered veto block.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from src.ztare.reports.gp048_feedback import (
    GP048_TELEMETRY_FILENAME,
    GP048_VETO_MAPPING_FILENAME,
    compute_recent_cohort,
    render_farther_tail_veto_prompt_section,
    render_primitive_cohort_prompt_section,
    write_telemetry_line,
)


def _write_fit_result(
    workspace: Path,
    iteration: int,
    expression: str,
    independent_vars: list[str],
    parameter_names: list[str],
    status: str = "success",
) -> None:
    payload = {
        "status": status,
        "expression": expression,
        "independent_vars": independent_vars,
        "parameter_names": parameter_names,
    }
    (workspace / f"fit_result_iter_{iteration:03d}.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Mode 1 — Telemetry
# ---------------------------------------------------------------------------


def test_write_telemetry_line_no_prior(tmp_path: Path) -> None:
    line = write_telemetry_line(
        tmp_path,
        iteration=1,
        fit_result_data={
            "expression": "a * phi + b",
            "independent_vars": ["phi"],
            "parameter_names": ["a", "b"],
            "status": "success",
        },
    )
    assert line is not None
    assert line.ted_to_prev is None
    assert line.new_primitives_vs_prev == sorted(line.primitives)
    assert line.new_primitives_vs_run == sorted(line.primitives)

    telemetry_path = tmp_path / GP048_TELEMETRY_FILENAME
    lines = telemetry_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["iteration"] == 1
    assert rec["ted_to_prev"] is None
    assert "timestamp_utc" in rec


def test_write_telemetry_line_with_prior(tmp_path: Path) -> None:
    # iter 1: simple polynomial
    _write_fit_result(tmp_path, 1, "a * phi + b", ["phi"], ["a", "b"])
    # iter 2: exp-family — different primitive set
    line = write_telemetry_line(
        tmp_path,
        iteration=2,
        fit_result_data={
            "expression": "a * 2.71828 ** (-b * phi)",
            "independent_vars": ["phi"],
            "parameter_names": ["a", "b"],
            "status": "success",
        },
    )
    assert line is not None
    assert line.ted_to_prev is not None
    # new primitives should include at least one that wasn't in iter 1
    assert line.new_primitives_vs_prev, "expected new primitives vs prior"


def test_write_telemetry_line_skips_malformed(tmp_path: Path) -> None:
    line = write_telemetry_line(
        tmp_path,
        iteration=1,
        fit_result_data={
            "expression": "((((",
            "independent_vars": ["phi"],
            "parameter_names": ["a"],
        },
    )
    assert line is None
    assert not (tmp_path / GP048_TELEMETRY_FILENAME).exists()


# ---------------------------------------------------------------------------
# Mode 2 — Primitive-cohort
# ---------------------------------------------------------------------------


def test_compute_recent_cohort_monopoly(tmp_path: Path) -> None:
    # three iters, all same primitive set (power + additive)
    for idx in range(1, 4):
        _write_fit_result(
            tmp_path, idx, f"a * phi ** 2 + b + {idx}", ["phi"], ["a", "b"]
        )
    summary = compute_recent_cohort(tmp_path, k=5)
    assert summary is not None
    assert summary.is_monopoly is True
    assert summary.last_k == 3
    assert summary.missing, "expected some missing primitives"


def test_compute_recent_cohort_union(tmp_path: Path) -> None:
    _write_fit_result(tmp_path, 1, "a * phi + b", ["phi"], ["a", "b"])
    _write_fit_result(
        tmp_path, 2, "a * 2.71828 ** (-b * phi)", ["phi"], ["a", "b"]
    )
    _write_fit_result(tmp_path, 3, "a / (phi + b)", ["phi"], ["a", "b"])
    summary = compute_recent_cohort(tmp_path, k=5)
    assert summary is not None
    assert summary.is_monopoly is False
    assert summary.last_k == 3


def test_render_cohort_empty_when_below_min_k(tmp_path: Path) -> None:
    _write_fit_result(tmp_path, 1, "a * phi + b", ["phi"], ["a", "b"])
    out = render_primitive_cohort_prompt_section(tmp_path, k=5, min_k_to_fire=3)
    assert out == ""


def test_render_cohort_non_empty_when_above_min_k(tmp_path: Path) -> None:
    for idx in range(1, 5):
        _write_fit_result(
            tmp_path, idx, f"a * phi ** 2 + b + {idx}", ["phi"], ["a", "b"]
        )
    out = render_primitive_cohort_prompt_section(tmp_path, k=5, min_k_to_fire=3)
    assert "GP-048 PRIMITIVE COHORT ANNOTATION" in out
    assert "cohort:" in out
    assert "missing:" in out
    # annotation not instruction
    assert "annotation, not an instruction" in out.lower() or "annotation" in out.lower()


# ---------------------------------------------------------------------------
# Farther-tail veto — sanitization is load-bearing
# ---------------------------------------------------------------------------


_SENSITIVE_GATE_NAMES = [
    "farther_tail_monotone",
    "farther_tail_bounded",
    "farther_tail_positive",
    "farther_tail_asymptote_zero",
]

_TOPOLOGY_WORDS = [
    "monotone",
    "bounded",
    "positive",
    "asymptote",
    "oscillate",
    "up without bound",
    "non-zero floor",
    "down to zero",
]


def test_veto_empty_when_no_payload() -> None:
    assert render_farther_tail_veto_prompt_section(None, visible_threshold=0.05) == ""
    assert render_farther_tail_veto_prompt_section({}, visible_threshold=0.05) == ""


def test_veto_empty_when_no_failing_farther_tail_gates() -> None:
    payload = {
        "gate_results": [
            {"name": "visible_residual", "passed": False},
            {"name": "farther_tail_monotone", "passed": True},
        ]
    }
    assert render_farther_tail_veto_prompt_section(payload, visible_threshold=0.05) == ""


def test_veto_uses_opaque_labels(tmp_path: Path) -> None:
    payload = {
        "gate_results": [
            {"name": name, "passed": False} for name in _SENSITIVE_GATE_NAMES
        ]
    }
    out = render_farther_tail_veto_prompt_section(
        payload, visible_threshold=0.05, workspace_dir=tmp_path, iteration=7
    )
    assert "farther_tail_gate_A (FAILED)" in out
    assert "farther_tail_gate_D (FAILED)" in out


def test_veto_never_leaks_true_gate_names() -> None:
    payload = {
        "gate_results": [
            {"name": name, "passed": False} for name in _SENSITIVE_GATE_NAMES
        ]
    }
    out = render_farther_tail_veto_prompt_section(payload, visible_threshold=0.05)
    for name in _SENSITIVE_GATE_NAMES:
        assert name not in out, f"LEAK: true gate name {name!r} appeared in veto"


def test_veto_never_leaks_topology_enumeration() -> None:
    payload = {
        "gate_results": [
            {"name": "farther_tail_monotone", "passed": False},
        ]
    }
    out = render_farther_tail_veto_prompt_section(payload, visible_threshold=0.05)
    for word in _TOPOLOGY_WORDS:
        assert word not in out.lower(), f"LEAK: topology hint {word!r} in veto"


def test_veto_threshold_is_dynamic() -> None:
    payload = {"gate_results": [{"name": "farther_tail_a", "passed": False}]}
    out_loose = render_farther_tail_veto_prompt_section(payload, visible_threshold=0.05)
    out_tight = render_farther_tail_veto_prompt_section(payload, visible_threshold=0.001)
    assert "0.05" in out_loose
    assert "0.001" in out_tight
    assert "0.05" not in out_tight


def test_veto_writes_mapping_jsonl(tmp_path: Path) -> None:
    payload = {
        "gate_results": [
            {"name": "farther_tail_monotone", "passed": False},
            {"name": "farther_tail_bounded", "passed": False},
        ]
    }
    out = render_farther_tail_veto_prompt_section(
        payload,
        visible_threshold=0.05,
        workspace_dir=tmp_path,
        iteration=12,
    )
    assert out  # non-empty
    mapping_path = tmp_path / GP048_VETO_MAPPING_FILENAME
    assert mapping_path.exists()
    records = [
        json.loads(line)
        for line in mapping_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(records) == 1
    rec = records[0]
    assert rec["iteration"] == 12
    opaque_to_true = {m["opaque"]: m["true_name"] for m in rec["mapping"]}
    assert opaque_to_true["farther_tail_gate_A"] == "farther_tail_monotone"
    assert opaque_to_true["farther_tail_gate_B"] == "farther_tail_bounded"


# ---------------------------------------------------------------------------
# Operator-requested constraint tests (lethal checks)
# ---------------------------------------------------------------------------


def test_veto_sanitization_regex_against_descriptive_names() -> None:
    """Feed the veto highly-descriptive gate names and assert that every
    load-bearing semantic token is absent from the rendered prompt."""

    payload = {
        "gate_results": [
            {"name": "farther_tail_must_decay_to_zero", "passed": False},
            {"name": "farther_tail_concavity_check", "passed": False},
            {"name": "farther_tail_positive_floor_bound", "passed": False},
        ]
    }
    out = render_farther_tail_veto_prompt_section(payload, visible_threshold=0.05)

    forbidden_tokens = [
        r"decay",
        r"zero",
        r"concavity",
        r"positive",
        r"floor",
        r"must",
        r"bound",
        r"check",
    ]
    for token in forbidden_tokens:
        assert re.search(token, out, re.IGNORECASE) is None, (
            f"LEAK: semantic token {token!r} appeared in sanitized veto"
        )

    # And the full names themselves must be absent.
    assert "farther_tail_must_decay_to_zero" not in out
    assert "farther_tail_concavity_check" not in out
    assert "farther_tail_positive_floor_bound" not in out

    # But the opaque labels must be present.
    assert "farther_tail_gate_A" in out
    assert "farther_tail_gate_B" in out
    assert "farther_tail_gate_C" in out


def test_opaque_mapping_stable_across_iterations(tmp_path: Path) -> None:
    """The same true gate must receive the same opaque label in later
    iterations — otherwise the mutator cannot track its own trajectory."""

    iter_15_payload = {
        "gate_results": [
            {"name": "farther_tail_alpha", "passed": False},
            {"name": "farther_tail_beta", "passed": False},
        ]
    }
    out_15 = render_farther_tail_veto_prompt_section(
        iter_15_payload,
        visible_threshold=0.05,
        workspace_dir=tmp_path,
        iteration=15,
    )
    assert "farther_tail_gate_A" in out_15
    assert "farther_tail_gate_B" in out_15

    # Iteration 16 — same underlying gates fail. Must reuse gate_A / gate_B.
    iter_16_payload = {
        "gate_results": [
            {"name": "farther_tail_beta", "passed": False},
            {"name": "farther_tail_alpha", "passed": False},
        ]
    }
    out_16 = render_farther_tail_veto_prompt_section(
        iter_16_payload,
        visible_threshold=0.05,
        workspace_dir=tmp_path,
        iteration=16,
    )
    assert "farther_tail_gate_A" in out_16
    assert "farther_tail_gate_B" in out_16

    # Verify via the mapping file that alpha→A and beta→B are preserved.
    records = [
        json.loads(line)
        for line in (tmp_path / GP048_VETO_MAPPING_FILENAME)
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    # Flatten all mapping entries, first occurrence wins.
    seen: dict[str, str] = {}
    for rec in records:
        for m in rec["mapping"]:
            seen.setdefault(m["true_name"], m["opaque"])
    assert seen["farther_tail_alpha"] == "farther_tail_gate_A"
    assert seen["farther_tail_beta"] == "farther_tail_gate_B"

    # Iteration 17 — a new gate enters. Must get the next unused letter (C),
    # and existing gates must still map to their original labels.
    iter_17_payload = {
        "gate_results": [
            {"name": "farther_tail_alpha", "passed": False},
            {"name": "farther_tail_gamma", "passed": False},
        ]
    }
    out_17 = render_farther_tail_veto_prompt_section(
        iter_17_payload,
        visible_threshold=0.05,
        workspace_dir=tmp_path,
        iteration=17,
    )
    assert "farther_tail_gate_A" in out_17  # alpha retains A
    assert "farther_tail_gate_C" in out_17  # gamma gets the next free letter
    assert "farther_tail_gate_B" not in out_17  # beta didn't fail this iter


def test_threshold_injection_no_hardcoded_fallback() -> None:
    """Assert the threshold rendered in the prompt is exactly the value
    passed in, and that no hardcoded fallback survives when a tighter
    threshold is supplied."""

    payload = {"gate_results": [{"name": "farther_tail_x", "passed": False}]}

    out_loose = render_farther_tail_veto_prompt_section(payload, visible_threshold=0.05)
    assert "0.05" in out_loose

    out_tight = render_farther_tail_veto_prompt_section(payload, visible_threshold=0.01)
    assert "0.01" in out_tight
    assert "0.05" not in out_tight, "hardcoded 0.05 leaked into tight-threshold prompt"

    out_very_tight = render_farther_tail_veto_prompt_section(
        payload, visible_threshold=1e-6
    )
    assert "1e-06" in out_very_tight or "0.000001" in out_very_tight
    assert "0.05" not in out_very_tight
    assert "0.01" not in out_very_tight


# ---------------------------------------------------------------------------
# Integration tests against the REAL latest_eval_results.json shape
# (score_contract.deterministic_charter_gates.results). These are the tests
# that would have caught the bug Codex found — synthetic top-level payloads
# are insufficient.
# ---------------------------------------------------------------------------


def _real_shape_payload(
    failing_farther_tail: list[str],
    visible_threshold: float = 0.05,
) -> dict:
    """Build a payload matching the real runner shape. Mirrors
    projects/gp023_planck_sandbox_03/latest_eval_results.json."""
    results = [
        {
            "name": "hidden_global_residual",
            "passed": True,
            "actual": 0.01,
            "threshold": visible_threshold,
            "operator": "lt",
            "reason": "",
        },
    ]
    for gate_name in failing_farther_tail:
        results.append(
            {
                "name": gate_name,
                "passed": False,
                "actual": 0.2,
                "threshold": 0.1,
                "operator": "lt",
                "reason": "",
            }
        )
    return {
        "score_contract": {
            "deterministic_charter_gates": {
                "declared": len(results),
                "results": results,
                "any_failed": True,
                "failure_count": len(failing_farther_tail),
            }
        }
    }


def test_veto_reads_nested_score_contract_shape(tmp_path: Path) -> None:
    payload = _real_shape_payload(
        failing_farther_tail=[
            "farther_tail_global_residual",
            "farther_tail_terminal_value_psi_1_80",
        ]
    )
    out = render_farther_tail_veto_prompt_section(
        payload, workspace_dir=tmp_path, iteration=1
    )
    assert out, "veto should fire on real nested shape"
    assert "farther_tail_gate_A" in out
    assert "farther_tail_gate_B" in out
    # Load-bearing sanitization: the real descriptive names must never leak.
    assert "farther_tail_global_residual" not in out
    assert "farther_tail_terminal_value_psi_1_80" not in out
    assert "terminal_value" not in out
    assert "global_residual" not in out


def test_veto_self_extracts_threshold_from_payload() -> None:
    payload = _real_shape_payload(
        failing_farther_tail=["farther_tail_global_residual"],
        visible_threshold=0.01,
    )
    out = render_farther_tail_veto_prompt_section(payload)
    assert "0.01" in out
    assert "0.05" not in out


def test_veto_fail_closed_when_threshold_not_discoverable() -> None:
    """If neither the caller nor the payload provides a threshold, the
    renderer must skip the block rather than render a hardcoded lie."""
    payload_missing_visible_gate = {
        "score_contract": {
            "deterministic_charter_gates": {
                "results": [
                    {
                        "name": "farther_tail_some_gate",
                        "passed": False,
                        "operator": "lt",
                    },
                ],
            }
        }
    }
    out = render_farther_tail_veto_prompt_section(payload_missing_visible_gate)
    assert out == ""


def test_veto_real_fixture_from_sandbox_03() -> None:
    """Load an actual latest_eval_results.json from a closed sandbox and
    verify the renderer handles it without exceptions. Skips if no
    fixture is available on this machine."""
    candidates = [
        Path("projects/gp023_planck_sandbox_03/latest_eval_results.json"),
        Path("projects/gp023_planck_sandbox_02/latest_eval_results.json"),
    ]
    fixture = next((p for p in candidates if p.exists()), None)
    if fixture is None:
        return  # skip — no real artifact available
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    out = render_farther_tail_veto_prompt_section(payload, visible_threshold=0.05)
    # Regardless of whether any farther_tail gates failed in that specific
    # run, the renderer must return a string without raising. If it fires,
    # it must not leak the real gate names.
    assert isinstance(out, str)
    for leaky in (
        "farther_tail_global_residual",
        "farther_tail_terminal_value_psi_0_60",
        "farther_tail_terminal_value_psi_1_00",
        "farther_tail_terminal_value_psi_1_80",
    ):
        assert leaky not in out


def test_veto_handles_status_fail_encoding() -> None:
    payload = {
        "deterministic_gate_results": [
            {"name": "farther_tail_monotone", "status": "fail"},
        ]
    }
    out = render_farther_tail_veto_prompt_section(payload, visible_threshold=0.05)
    assert "FAILED" in out
    assert "farther_tail_monotone" not in out
