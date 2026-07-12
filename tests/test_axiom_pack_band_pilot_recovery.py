from __future__ import annotations

import json
import importlib.util
from pathlib import Path

import pytest


_PATH = Path(__file__).parents[1] / "scripts/public/control/leanmill/axiom_pack_band_pilot.py"
_SPEC = importlib.util.spec_from_file_location("axiom_pack_band_pilot", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
pilot = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(pilot)


def test_recovered_attempt_is_immutable_and_idempotent(tmp_path, capsys):
    prepared = pilot.prepare(state_dir=tmp_path, model="never-called", reasoning_effort="low")
    outputs = {
        "proposer": json.dumps(
            {
                "typed_axiom_proposals": [
                    {
                        "source_ref": "finite_band_short_word_rewrite",
                        "axiom_name": "candidate",
                        "lhs_word": "xyx",
                        "rhs_word": "xy",
                        "nl_intent": "remove the final repeated variable",
                        "kill_condition": "a retained finite model refutes the equation",
                    }
                ]
            }
        ),
        "semantic_checker": json.dumps(
            {
                "faithful": True,
                "rationale": "the equation has the requested short-word shape",
                "evidence_refs": ["recovered-calibration-bytes"],
            }
        ),
    }
    first = pilot.execute(
        prepared_dir=prepared,
        provider_call_timeout_s=0,
        recovered_outputs=outputs,
        recovery_source="unit-test",
    )
    second = pilot.execute(
        prepared_dir=prepared,
        provider_call_timeout_s=0,
        recovered_outputs={"proposer": "different", "semantic_checker": "different"},
        recovery_source="must-not-be-consumed",
    )
    assert second == first
    assert (prepared / "run_result.json").is_file()
    assert first["provider_calls"]["proposer"]["runtime"] == "recovered_response_bytes"
    assert pilot.main(["status", "--prepared-dir", str(prepared)]) == 0
    status = json.loads(capsys.readouterr().out)
    assert status["attempt_status"] == "completed"
    assert status["roles"] == {"proposer": "not_started", "semantic_checker": "not_started"}


def test_historical_evidence_verification_does_not_rebuild_the_codec(tmp_path):
    prepared_dir = pilot.prepare(
        state_dir=tmp_path, model="never-called", reasoning_effort="low"
    )
    pilot.execute(
        prepared_dir=prepared_dir,
        provider_call_timeout_s=0,
        recovered_outputs={
            "proposer": json.dumps(
                {
                    "typed_axiom_proposals": [
                        {
                            "source_ref": "finite_band_short_word_rewrite",
                            "axiom_name": "candidate",
                            "lhs_word": "xyx",
                            "rhs_word": "xy",
                            "nl_intent": "remove the final repeated variable",
                            "kill_condition": "a retained finite model refutes the equation",
                        }
                    ]
                }
            ),
            "semantic_checker": json.dumps(
                {
                    "faithful": True,
                    "rationale": "the equation has the requested short-word shape",
                    "evidence_refs": ["historical-codec-test"],
                }
            ),
        },
        recovery_source="unit-test",
    )

    prepared = pilot._read_json(prepared_dir / "prepared.json")
    prepared["transport_contract"]["historical_extension"] = {"codec_revision": 0}
    prepared["execution_contract"]["transport_contract_digest"] = pilot._sha(
        prepared["transport_contract"]
    )
    manifest_private = (prepared_dir / "private" / "manifest.pem").read_text(
        encoding="utf-8"
    )
    prepared["execution_contract_signature"] = pilot.sign_transport_contract(
        prepared["execution_contract"], manifest_private
    )
    pilot._write_json(prepared_dir / "prepared.json", prepared)
    completed = pilot._read_json(prepared_dir / "run_result.json")
    completed["execution_contract_digest"] = pilot._sha(prepared["execution_contract"])
    pilot._write_json(prepared_dir / "run_result.json", completed)

    with pytest.raises(ValueError, match="transport contract digest"):
        pilot._load_prepared(prepared_dir)
    loaded, result = pilot._load_completed_historical_evidence(prepared_dir)
    assert loaded["transport_contract"]["historical_extension"]["codec_revision"] == 0
    assert result["execution_contract_digest"] == pilot._sha(
        loaded["execution_contract"]
    )
