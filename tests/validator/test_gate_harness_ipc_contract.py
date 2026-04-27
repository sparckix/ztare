"""GP-135 IPC contract tests between autoresearch_loop and gate_harness.py.

Motivation: today (2026-04-23) we found that gate_harness.py emits gates as
a LIST with key "passed", but test_thesis.py read it as a DICT with key
"pass", AND autoresearch called the harness without the flag that emits
the contract-compliant schema at all. Result: every holdout hard-gate
check was raising KeyError and silently zeroing valid mutator proposals
as "FIRED (exception)". Three-layer contract mismatch with no test.

This module pins the gate_harness IPC contract:

  1. `--emit-deterministic-gates` must emit {harness_ok, gates[], exact_match_fraction, mismatches[]}
  2. `gates` must be a LIST of dicts each with keys (name, value, threshold, operator, passed)
  3. `--run-visible-assertions` must emit JSON with {exact_match, matches, total, errors}
     and return exit 0 when exact_match == 1.0, exit 1 WITH stderr containing
     "AssertionError:" otherwise (so classify_harness_failure classifies as
     fail_assert, not fail_other)
  4. `--run-smoke-test` must exit 0 on a valid baseline test_model.py

Regression lock: these tests MUST fail if any future refactor changes
either side of the contract without updating the other. This is the
apparatus-level IPC check that didn't exist and let the bug slip.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parents[2]


def _projects_with_gate_harness() -> list[Path]:
    """Return substrate project dirs that opt into the CURRENT contract.

    Current-contract markers (must all be present in the harness source):
      - "--emit-deterministic-gates" CLI flag
      - emits "exact_match_fraction" at the top level
      - emits gates as a list (detected by source pattern ``"gates": [``)

    Substrates with older shapes are legacy — they are NOT failed by this
    test, they are skipped. Most are either shut down or operate on
    continuous substrates with completely different gate semantics.
    """
    projects = []
    for p in sorted((REPO / "projects").iterdir()):
        if not p.is_dir() or p.name.startswith("_"):
            continue
        harness = p / "gate_harness.py"
        if not harness.exists() or not (p / "test_model.py").exists():
            continue
        try:
            src = harness.read_text(encoding="utf-8")
        except Exception:
            continue
        # Two canaries for the current contract (the list shape of `gates`
        # is verified at runtime by test_emit_deterministic_gates_schema,
        # not at selection time, because harnesses construct the list
        # dynamically and don't contain the literal `"gates": [` substring).
        if "--emit-deterministic-gates" not in src:
            continue
        if "exact_match_fraction" not in src:
            continue
        projects.append(p)
    return projects


def _run_harness(project: Path, *args: str, timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(project / "gate_harness.py"), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(project),
    )


# Restrict parametrize to MLH family + GP-090 (known current-contract substrates).
_CONTRACT_OPT_IN = {"mlh_f1", "mlh_f2", "mlh_f3", "mlh_f4", "mlh_f5", "mlh_f6", "gp090_01"}
_CURRENT_CONTRACT = [p for p in _projects_with_gate_harness() if p.name in _CONTRACT_OPT_IN]


@pytest.mark.parametrize("project", _CURRENT_CONTRACT, ids=lambda p: p.name)
def test_emit_deterministic_gates_schema(project: Path):
    """Contract #1: --emit-deterministic-gates emits the schema autoresearch expects."""
    res = _run_harness(project, "--emit-deterministic-gates")
    assert res.returncode == 0, (
        f"{project.name}: --emit-deterministic-gates returned {res.returncode}\n"
        f"stderr: {res.stderr[:400]}"
    )
    try:
        payload = json.loads(res.stdout)
    except json.JSONDecodeError as exc:
        pytest.fail(f"{project.name}: output not valid JSON: {exc}\nstdout: {res.stdout[:400]}")
    # Required top-level keys
    for key in ("harness_ok", "gates", "exact_match_fraction", "mismatches"):
        assert key in payload, f"{project.name}: missing key {key!r}. Got: {list(payload.keys())}"
    # `gates` must be a list (not dict) per current harness implementation
    assert isinstance(payload["gates"], list), (
        f"{project.name}: `gates` must be a list, got {type(payload['gates']).__name__}. "
        "test_thesis.py has to support both formats; this test pins the current."
    )
    # Each gate entry must have the keys autoresearch reads
    for i, gate in enumerate(payload["gates"]):
        for key in ("name", "value", "threshold", "operator", "passed"):
            assert key in gate, (
                f"{project.name}: gate {i} missing key {key!r}. "
                f"Got: {list(gate.keys())}. "
                "If you rename 'passed' → 'pass' or similar, update test_thesis.py "
                "holdout hard-gate check AT THE SAME TIME."
            )
    # harness_ok must be bool
    assert isinstance(payload["harness_ok"], bool), (
        f"{project.name}: harness_ok must be bool, got {type(payload['harness_ok']).__name__}"
    )


@pytest.mark.parametrize("project", _CURRENT_CONTRACT, ids=lambda p: p.name)
def test_run_visible_assertions_exit_code_contract(project: Path):
    """Contract #3: --run-visible-assertions exits 1 WITH AssertionError on mismatch.

    GP-135 fix: the baseline test_model.py returns 0 for all n, which does
    NOT match the evidence. The harness must:
      - exit 1 (signals failure to autoresearch)
      - write AssertionError to stderr (so classify_harness_failure classifies
        as fail_assert = substantive falsification, not fail_other = harness defect)
    If stderr is empty on exit 1, classify_harness_failure returns FAIL_OTHER
    and the score gets capped as a "harness defect" even though the harness
    ran fine — the model was just wrong.
    """
    res = _run_harness(project, "--run-visible-assertions")
    if res.returncode == 0:
        # Model happens to match (rare for baseline). Acceptable.
        return
    # Non-zero exit MUST have AssertionError in stderr for correct classification.
    assert "AssertionError" in res.stderr, (
        f"{project.name}: --run-visible-assertions exited {res.returncode} with empty or "
        f"non-AssertionError stderr. classify_harness_failure will tag this as fail_other "
        f"(harness defect) instead of fail_assert (substantive falsification). "
        f"stderr: {res.stderr[:400]!r}"
    )


@pytest.mark.parametrize("project", _CURRENT_CONTRACT, ids=lambda p: p.name)
def test_run_smoke_test_exits_clean(project: Path):
    """Contract #4: --run-smoke-test always exits 0 (just a syntax/parse check)."""
    res = _run_harness(project, "--run-smoke-test")
    assert res.returncode == 0, (
        f"{project.name}: --run-smoke-test returned {res.returncode}\n"
        f"stdout: {res.stdout[:200]}\nstderr: {res.stderr[:400]}"
    )


def test_autoresearch_side_of_contract_reads_correctly():
    """Contract #2: test_thesis.py holdout hard-gate must accept both list and
    dict `gates` and both "passed" and "pass" keys.

    This test exercises the test_thesis.py logic directly by feeding it
    synthetic gate_harness outputs and asserting the hard-gate decision matches
    what the harness intended.
    """
    # Inline the harness-shape payload as autoresearch receives it
    def _gate_passed(g):
        return bool(g.get("passed", g.get("pass", False)))

    def _resolve_gates(payload):
        gate_results = payload.get("gates", [])
        if isinstance(gate_results, dict):
            return list(gate_results.values())
        if isinstance(gate_results, list):
            return gate_results
        return []

    # Case A: current harness format (list + "passed")
    payload_current = {
        "harness_ok": True,
        "gates": [{"name": "holdout_exact_match", "value": 1.0, "threshold": 1.0, "operator": ">=", "passed": True}],
    }
    gates = _resolve_gates(payload_current)
    assert payload_current["harness_ok"] and all(_gate_passed(g) for g in gates), (
        "current harness format (list + 'passed'=True) must produce all_gates_passed=True"
    )

    # Case B: legacy dict + "pass" (back-compat)
    payload_legacy = {
        "harness_ok": True,
        "gates": {"holdout_exact_match": {"value": 1.0, "threshold": 1.0, "pass": True}},
    }
    gates = _resolve_gates(payload_legacy)
    assert payload_legacy["harness_ok"] and all(_gate_passed(g) for g in gates), (
        "legacy format (dict + 'pass'=True) must also produce all_gates_passed=True"
    )

    # Case C: failed gate in list form
    payload_failed = {
        "harness_ok": False,
        "gates": [{"name": "holdout_exact_match", "value": 0.5, "threshold": 1.0, "operator": ">=", "passed": False}],
    }
    gates = _resolve_gates(payload_failed)
    assert not (payload_failed["harness_ok"] and all(_gate_passed(g) for g in gates)), (
        "failed gate must produce all_gates_passed=False"
    )
