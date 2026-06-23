import importlib.util
import json
from pathlib import Path


def load_script_module(name: str, relpath: str):
    script = Path(relpath).resolve()
    spec = importlib.util.spec_from_file_location(name, script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_demo_module():
    return load_script_module(
        "claim_discipline_demo",
        "scripts/public/control/claim_discipline_demo.py",
    )


def test_claim_discipline_demo_demotes_broad_best_system_claim() -> None:
    module = load_demo_module()
    payload = module.build_demo_payload()

    assert payload["ok"] is True
    assert payload["model_free"] is True
    assert payload["writes_persistent_runtime_state"] is False
    assert payload["decision"]["verdict"] == "demote_to_bounded_wording"
    assert payload["decision"]["claim_allowed"] is False
    assert "not a best-system claim" in payload["decision"]["non_claims"]
    assert payload["source_readiness"]["summary"]["blocked"] >= 1
    assert payload["promotion_guard"]["promotion_ready"] is False
    assert any(not check["passes"] for check in payload["claim_discipline_checks"])


def test_hello_value_demo_prints_bounded_nonpersistent_summary(capsys) -> None:
    module = load_script_module(
        "hello_value_demo",
        "scripts/public/control/hello_value_demo.py",
    )

    assert module.main() == 0
    out = capsys.readouterr().out

    assert "ZTARE hello: offline claim review in one run" in out
    assert "Ready intake: accepted" in out
    assert "source-preflight: ready_for_evidence_prepare (1 source evidence, 0 untyped)" in out
    assert "Ready intake missing-ref falsifier: passed" in out
    assert "Expected missing-ref failure" in out
    assert "Malformed intake: blocked" in out
    assert "missing required non-empty list: evidence_refs" in out
    assert "Verdict: demote_to_bounded_wording" in out
    assert "Claim allowed: False" in out
    assert "What a reviewer can say" in out
    assert "failed_check_count" in out
    assert "ready_intake_falsifier_ok" in out
    assert "writes_persistent_runtime_state" in out
    assert "ready_packet_falsifier_ok" not in out
    assert "symlink_escape_allowed" not in out
    assert "ANTI-PATTERN" not in out
    assert "SOTA" not in out
    assert "sota" not in out

    assert module.main(["--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ready_intake_falsifier_path_safety"][
        "symlink_escape_allowed"
    ] is False
    assert payload["ready_packet_falsifier_ok"] is True
    assert payload["ready_packet_falsifier_path_safety"][
        "symlink_escape_allowed"
    ] is False
