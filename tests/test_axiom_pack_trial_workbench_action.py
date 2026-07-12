from __future__ import annotations

import hashlib
import json

import pytest

from ztare.leanmill.contracts.proof_gap import (
    PROOF_GAP_RECEIPT_BUNDLE_SCHEMA,
    ProofGapReceipt,
    RegisteredGapFamily,
)
from ztare.leanmill.formalization_admission import ADMITTED, FormalizationAdmission
from ztare.leanmill.lean_source import extract_signature, strip_comments
from ztare.leanmill import workbench_actions as actions


def _sha(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _admission(name: str, task: str, conclusion: str) -> FormalizationAdmission:
    source = f"theorem {name} (n : Nat) : {conclusion} := by sorry\n"
    signature = " ".join(strip_comments(extract_signature(source, name)).split())
    return FormalizationAdmission(
        task_digest=_sha("task:" + task),
        intent_text="establish " + conclusion,
        context_digest=_sha("context"),
        status=ADMITTED,
        target_name=name,
        source_text=source,
        target_signature=signature,
        faithfulness_reason="admitted",
        faithfulness_checks_json="{}",
        refine_trace_json="[]",
        advisory_audits_json="{}",
    )


def _family() -> RegisteredGapFamily:
    return RegisteredGapFamily(
        family_id="priority_uncrossing",
        structure_adapter_id="leanmill.order.priority_uncrossing.v1",
        gap_kind="missing_composition_law",
        registry_digest=_sha("registry"),
        base_theory_digest=_sha("base"),
        substrate_digest=_sha("substrate"),
    )


def _receipt(name: str, task: str, conclusion: str) -> dict:
    admission = _admission(name, task, conclusion)
    return ProofGapReceipt.from_firewall_result(
        family=_family(),
        admission=admission,
        result={
            "lean_statement": admission.source_text,
            "faithful": True,
            "outcome": "admitted_and_exact_gap",
            "solved": "exact_gap",
            "failure_class": {
                "class": "math",
                "error_class": "unsolved_goals",
                "reason": "kernel dead-end (unsolved_goals)",
            },
            "budget_killed": False,
            "governance": {"governance_kernel": {"passed": False}},
            "closure_certificate": None,
        },
    ).to_json()


def _bundle_bytes(*, two_receipts: bool = True) -> bytes:
    receipts = [_receipt("gapA", "a", "n + 0 = n")]
    if two_receipts:
        receipts.append(_receipt("gapB", "b", "0 + n = n"))
    return (
        json.dumps(
            {"schema": PROOF_GAP_RECEIPT_BUNDLE_SCHEMA, "receipts": receipts},
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def test_preview_replays_evaluator_without_writing(tmp_path) -> None:
    source = tmp_path / "inputs" / "proof_gaps.json"
    source.parent.mkdir(parents=True)
    source.write_bytes(_bundle_bytes())

    payload = actions.start_action(
        "prepare_axiom_pack_trial",
        {"receipt_bundle_path": "inputs/proof_gaps.json", "confirmed": False},
        repo=tmp_path,
    )

    assert payload["status"] == "needs_confirmation"
    assert payload["accepted"] is False
    job = payload["job"]
    assert job["preview_eligible"] is True
    assert job["artifact_promotion_status"] == "quarantined"
    assert job["receipt_bundle_sha256"] == actions.sha256_ref_bytes(source.read_bytes())
    assert job["expected_preparation_artifact_digest"].removeprefix("sha256:") in job["expected_artifact"]
    assert job["command"][3] == "execute-axiom-pack-trial"
    assert job["expected_artifact"] in payload["write_boundary"]["write_paths"]
    assert payload["write_boundary"]["domain_artifact_path"] == job["expected_artifact"]
    assert not (tmp_path / job["paths"]["job"]).exists()
    assert not (tmp_path / job["expected_artifact"]).exists()


def test_execution_writes_content_bound_quarantined_packet_only(tmp_path) -> None:
    source = tmp_path / "inputs" / "proof_gaps.json"
    source.parent.mkdir(parents=True)
    source.write_bytes(_bundle_bytes())
    expected = actions.sha256_ref_bytes(source.read_bytes())

    packet = actions.prepare_axiom_pack_trial_file(
        "inputs/proof_gaps.json",
        expected_input_sha256=expected,
        repo=tmp_path,
    )
    output = actions.axiom_pack_trial_artifact_path(packet, repo=tmp_path)

    assert json.loads(output.read_text()) == packet
    assert packet["receipt_bundle_sha256"] == expected
    assert packet["evaluation"]["eligible"] is True
    assert packet["promotion_status"] == "quarantined"
    assert packet["routing_only"] is True
    assert packet["proof_credit_eligible"] is False
    assert packet["theorem_campaign_admissible"] is False
    assert packet["theory_mutation_allowed"] is False
    assert packet["family_inferred"] is False
    assert packet["discovery_started"] is False
    assert packet["evaluation_packet_digest"] == actions.sha256_ref_bytes(
        actions.canonical_json_bytes(packet["evaluation"])
    )
    core = dict(packet)
    artifact_digest = core.pop("preparation_artifact_digest")
    assert artifact_digest == actions.sha256_ref_bytes(actions.canonical_json_bytes(core))
    files = sorted(
        path.relative_to(tmp_path).as_posix()
        for path in tmp_path.rglob("*")
        if path.is_file()
    )
    assert files == sorted(
        ["inputs/proof_gaps.json", output.relative_to(tmp_path).as_posix()]
    )


def test_execution_rejects_bytes_changed_after_preview(tmp_path) -> None:
    source = tmp_path / "proof_gaps.json"
    source.write_bytes(_bundle_bytes())
    expected = actions.sha256_ref_bytes(source.read_bytes())
    source.write_bytes(_bundle_bytes(two_receipts=False))

    with pytest.raises(ValueError, match="changed after action preview"):
        actions.prepare_axiom_pack_trial_file(
            "proof_gaps.json",
            expected_input_sha256=expected,
            repo=tmp_path,
        )
    assert not actions.axiom_pack_trial_root(repo=tmp_path).exists()


def test_blocked_bundle_still_prepares_without_starting_discovery(tmp_path) -> None:
    source = tmp_path / "proof_gaps.json"
    source.write_bytes(_bundle_bytes(two_receipts=False))

    packet = actions.prepare_axiom_pack_trial_file(
        "proof_gaps.json",
        expected_input_sha256=actions.sha256_ref_bytes(source.read_bytes()),
        repo=tmp_path,
    )

    assert packet["evaluation"]["eligible"] is False
    assert packet["evaluation"]["status"] == "blocked"
    assert packet["discovery_started"] is False
    assert packet["promotion_status"] == "quarantined"


def test_confirmed_start_uses_existing_background_job_boundary(tmp_path, monkeypatch) -> None:
    source = tmp_path / "proof_gaps.json"
    source.write_bytes(_bundle_bytes())

    class _Process:
        pid = 12345

    calls: list[tuple] = []

    def _popen(*args, **kwargs):
        calls.append((args, kwargs))
        return _Process()

    monkeypatch.setattr(actions.subprocess, "Popen", _popen)
    payload = actions.start_action(
        "prepare_axiom_pack_trial",
        {"receipt_bundle_path": "proof_gaps.json", "confirmed": True},
        repo=tmp_path,
    )

    assert payload["status"] == "started"
    assert payload["accepted"] is True
    assert payload["job"]["status"] == "running"
    assert calls and calls[0][0][0][-2] == "run-job"
    assert (tmp_path / payload["job"]["paths"]["job"]).exists()
    assert not (tmp_path / payload["job"]["expected_artifact"]).exists()


def test_cli_wrapper_routes_preview_to_start_action(monkeypatch, capsys) -> None:
    captured: dict = {}

    def _start(action, request):
        captured.update({"action": action, "request": request})
        return {
            "status": "needs_confirmation",
            "job": {"paths": {"job": "j.json", "result": "r.json"}},
        }

    monkeypatch.setattr(actions, "start_action", _start)
    assert actions.main(["prepare-axiom-pack-trial", "bundle.json", "--json"]) == 0
    assert captured == {
        "action": "prepare_axiom_pack_trial",
        "request": {
            "project": "",
            "receipt_bundle_path": "bundle.json",
            "confirmed": False,
        },
    }
    assert '"status": "needs_confirmation"' in capsys.readouterr().out
