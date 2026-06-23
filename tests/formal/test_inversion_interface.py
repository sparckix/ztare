"""The shared Popper INVERSION contract (common.inversion) + its two substrate instances.

Regression-locks the autoresearch refactor (2026-06-06): `inverter_agent.run_inverter` was refactored to
delegate through `ThesisInverter` via `common.inversion.run_inversion`. This test pins that its OUTPUT
dict + side effects (inverter_review.json) are UNCHANGED for a fixed (mocked) LLM response, and that both
substrate inverters conform to the one `Inverter` protocol. Run: PYTHONPATH=src python3 -m pytest
tests/formal/test_inversion_interface.py  (or execute directly).
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
for p in (str(REPO), str(REPO / "src")):
    if p not in sys.path:
        sys.path.insert(0, p)


def test_contract_selftest_passes():
    from ztare.common.inversion import _selftest
    assert _selftest() == 0


def test_lean_falsifier_conforms():
    from ztare.common.inversion import Inverter
    from ztare.leanmill.solver.conjecture import LeanFalsifier
    lf = LeanFalsifier({"target_theorem_name": "t"}, Path("/tmp"), 5)
    assert isinstance(lf, Inverter)


def test_thesis_inverter_conforms_and_run_inverter_output_preserved(tmp_path, monkeypatch):
    """The refactored run_inverter must (1) delegate through the contract and (2) return the SAME dict
    shape + write inverter_review.json, for a fixed LLM response — the regression lock."""
    import ztare.validator.inverter_agent as ia
    from ztare.common.inversion import Inverter

    # ThesisInverter conforms to the shared protocol.
    inv = ia.ThesisInverter(tmp_path, champion_score=80)
    assert isinstance(inv, Inverter)

    # Mock the LLM to a FIXED, valid inverter JSON (so the test is deterministic + offline).
    fixed = {
        "tests": [{"category": "measurement_artifact", "munger_inversion": "m",
                   "popper_test": "p", "procedure": "do x", "pass_criterion": "pc",
                   "fail_criterion": "fc", "auto_testable": True, "estimated_cost": "cheap"}],
        "overall_assessment": "moderately vulnerable",
        "confidence_the_champion_survives": 0.6,
    }

    class _FakeResp:
        text = json.dumps(fixed)

    class _FakeRuntime:
        def call_text(self, *a, **k):
            return _FakeResp()

    monkeypatch.setattr(ia, "LLMRuntime", _FakeRuntime)
    monkeypatch.setattr(ia, "resolve_model_id", lambda m: "fake-model")

    result = ia.run_inverter(tmp_path, champion_thesis="X causes Y", champion_score=80)

    # Output-shape regression: the dict the autoresearch loop consumes is unchanged.
    assert result["tests"] == fixed["tests"]
    assert result["overall_assessment"] == "moderately vulnerable"
    assert result["confidence_the_champion_survives"] == 0.6
    assert result["champion_score"] == 80
    assert result["inverter_model"] == "gpt4.1"
    assert result["total_tests_proposed"] == 1
    assert result["auto_testable_count"] == 1
    assert "timestamp" in result
    # Side effect preserved: inverter_review.json written with the same content.
    review = tmp_path / "workspace" / "inverter_review.json"
    assert review.exists()
    assert json.loads(review.read_text())["overall_assessment"] == "moderately vulnerable"


def test_run_inverter_skip_path(tmp_path):
    import ztare.validator.inverter_agent as ia
    out = ia.run_inverter(tmp_path, "thesis", champion_score=10, skip_if_score_below=50)
    assert out.get("skipped") is True


if __name__ == "__main__":
    # Lightweight runner (no pytest dependency): exercise the offline checks.
    import tempfile

    test_contract_selftest_passes()
    print("[PASS] contract selftest")
    test_lean_falsifier_conforms()
    print("[PASS] LeanFalsifier conforms")

    class _MP:
        def setattr(self, obj, name, val):
            setattr(obj, name, val)

    with tempfile.TemporaryDirectory() as d:
        test_thesis_inverter_conforms_and_run_inverter_output_preserved(Path(d), _MP())
    print("[PASS] ThesisInverter conforms + run_inverter output preserved")
    with tempfile.TemporaryDirectory() as d:
        test_run_inverter_skip_path(Path(d))
    print("[PASS] run_inverter skip path")
    print("ALL PASS")
