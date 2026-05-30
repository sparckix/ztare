import importlib.util
from pathlib import Path


def load_demo_module():
    script = Path("scripts/public/control/current_engine_demo.py").resolve()
    spec = importlib.util.spec_from_file_location("current_engine_demo", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_current_engine_demo_demotes_sota_claim() -> None:
    module = load_demo_module()
    payload = module.build_demo_payload()

    assert payload["ok"] is True
    assert payload["model_free"] is True
    assert payload["writes_persistent_runtime_state"] is False
    assert payload["decision"]["verdict"] == "demote_to_bounded_non_sota_wording"
    assert payload["decision"]["claim_allowed"] is False
    assert "not a SOTA claim" in payload["decision"]["non_claims"]
    assert payload["source_readiness"]["summary"]["blocked"] >= 1
    assert payload["promotion_guard"]["promotion_ready"] is False
    assert any(not check["passes"] for check in payload["claim_discipline_checks"])
