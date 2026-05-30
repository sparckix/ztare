from __future__ import annotations

import importlib.util
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO / "scripts/public/control/rd_forecast_tick_close.py"


def load_module():
    spec = importlib.util.spec_from_file_location("rd_forecast_tick_close", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def start_row(**signals):
    return {"start_declared_signals": signals}


def write_receipt(
    payload: Path,
    orientation: object,
    stress: object | None = None,
    verification: object | None = None,
    pattern_action_contract: object | None = None,
) -> None:
    payload.mkdir(parents=True, exist_ok=True)
    contract_path = payload / "artifacts" / "pattern_action_contract.json"
    contract_path.parent.mkdir(parents=True, exist_ok=True)
    if not contract_path.exists():
        contract_path.write_text(
            json.dumps(
                {
                    "problem_surfaces": ["hard_mathematical_residual"],
                    "pattern_chain": ["PATTERN-028"],
                    "evidence_carriers": [
                        {
                            "name": "orientation",
                            "required": True,
                            "artifact_slot": "orientation_artifact",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
    receipt = {
        "tick_id": "T",
        "contract_id": "C",
        "min_recursive_loops": 1,
        "pattern_action_contract": (
            pattern_action_contract or "artifacts/pattern_action_contract.json"
        ),
        "stop_reason": "diminishing_information_yield",
        "stop_rule": "Stop only after a tool or adversary changes no next move.",
        "why_enough": (
            "The last loop moved the live residual into a named next vector "
            "and another immediate loop would repeat the same diagnostic."
        ),
        "remaining_live_vectors": ["next discriminating vector"],
        "loops": [
            {
                "orientation_artifact": orientation,
                "stress_test_artifact": stress or orientation,
                "verification_artifact": verification or orientation,
                "new_information": (
                    "The recursive pass changed the formal surface and exposed "
                    "a concrete remaining residual."
                ),
                "next_question_or_kill": "Attack the named remaining residual next.",
            }
        ],
    }
    (payload / "research_done.json").write_text(json.dumps(receipt), encoding="utf-8")


def write_artifacts(payload: Path) -> tuple[str, str, str]:
    paths = []
    for name in ("orientation.md", "stress.md", "verification.md"):
        path = payload / "artifacts" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(name, encoding="utf-8")
        paths.append(f"artifacts/{name}")
    return tuple(paths)


def test_research_done_only_required_for_generic_signal_or_present(tmp_path, monkeypatch):
    mod = load_module()
    monkeypatch.setattr(mod, "REPO", tmp_path)
    monkeypatch.setattr(mod, "STORE", tmp_path / "store")

    payload = tmp_path / "payload"
    payload.mkdir()
    assert mod._research_done_error(payload, start_row(), "T", "C") is None
    assert "missing research_done.json" in mod._research_done_error(
        payload, start_row(hard_research_residual=True), "T", "C"
    )


def test_research_done_rejects_prose_urls_and_arbitrary_absolute_paths(tmp_path, monkeypatch):
    mod = load_module()
    monkeypatch.setattr(mod, "REPO", tmp_path)
    monkeypatch.setattr(mod, "STORE", tmp_path / "store")

    payload = tmp_path / "payload"
    a1, a2, a3 = write_artifacts(payload)
    write_receipt(payload, "this is a prose artifact and should not be accepted", a2, a3)
    assert "orientation_artifact" in mod._research_done_error(
        payload, start_row(hard_research_residual=True), "T", "C"
    )

    write_receipt(payload, "https://example.invalid/artifact", a2, a3)
    assert "orientation_artifact" in mod._research_done_error(
        payload, start_row(hard_research_residual=True), "T", "C"
    )

    write_receipt(payload, "/etc/passwd", a2, a3)
    assert "orientation_artifact" in mod._research_done_error(
        payload, start_row(hard_research_residual=True), "T", "C"
    )


def test_research_done_accepts_payload_relative_artifacts(tmp_path, monkeypatch):
    mod = load_module()
    monkeypatch.setattr(mod, "REPO", tmp_path)
    monkeypatch.setattr(mod, "STORE", tmp_path / "store")

    payload = tmp_path / "payload"
    write_receipt(payload, *write_artifacts(payload))
    assert mod._research_done_error(
        payload, start_row(hard_research_residual=True), "T", "C"
    ) is None


def test_research_done_requires_pattern_action_contract_artifact(tmp_path, monkeypatch):
    mod = load_module()
    monkeypatch.setattr(mod, "REPO", tmp_path)
    monkeypatch.setattr(mod, "STORE", tmp_path / "store")

    payload = tmp_path / "payload"
    write_receipt(payload, *write_artifacts(payload))
    data = json.loads((payload / "research_done.json").read_text(encoding="utf-8"))
    data.pop("pattern_action_contract")
    (payload / "research_done.json").write_text(json.dumps(data), encoding="utf-8")
    assert "pattern_action_contract" in mod._research_done_error(
        payload, start_row(hard_research_residual=True), "T", "C"
    )


def test_research_done_requires_required_contract_carriers(tmp_path, monkeypatch):
    mod = load_module()
    monkeypatch.setattr(mod, "REPO", tmp_path)
    monkeypatch.setattr(mod, "STORE", tmp_path / "store")

    payload = tmp_path / "payload"
    a1, a2, a3 = write_artifacts(payload)
    contract = payload / "artifacts" / "pattern_action_contract.json"
    contract.parent.mkdir(parents=True, exist_ok=True)
    contract.write_text(
        json.dumps(
            {
                "problem_surfaces": ["hard_mathematical_residual"],
                "pattern_chain": ["PATTERN-028"],
                "evidence_carriers": [
                    {
                        "name": "tool_pass",
                        "required": True,
                        "artifact_slot": "tool_pass_artifact",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    write_receipt(payload, a1, a2, a3)
    assert "does not fill required pattern carrier" in mod._research_done_error(
        payload, start_row(hard_research_residual=True), "T", "C"
    )

    tool_artifact = payload / "artifacts" / "tool.md"
    tool_artifact.write_text("tool", encoding="utf-8")
    data = json.loads((payload / "research_done.json").read_text(encoding="utf-8"))
    data["carrier_artifacts"] = {
        "tool_pass": {"root": "payload", "path": "artifacts/tool.md"}
    }
    (payload / "research_done.json").write_text(json.dumps(data), encoding="utf-8")
    assert mod._research_done_error(
        payload, start_row(hard_research_residual=True), "T", "C"
    ) is None


def test_research_done_accepts_typed_carrier_schema_receipt(tmp_path, monkeypatch):
    mod = load_module()
    monkeypatch.setattr(mod, "REPO", tmp_path)
    monkeypatch.setattr(mod, "STORE", tmp_path / "store")

    payload = tmp_path / "payload"
    a1, a2, a3 = write_artifacts(payload)
    contract = payload / "artifacts" / "pattern_action_contract.json"
    contract.parent.mkdir(parents=True, exist_ok=True)
    contract.write_text(
        json.dumps(
            {
                "problem_surfaces": ["meta_language_edge_carrier"],
                "pattern_chain": ["mm_03"],
                "evidence_carriers": [
                    {
                        "name": "meta_language_edge_receipt",
                        "required": True,
                        "artifact_slot": "meta_language_edge_artifact",
                        "required_fields": [
                            "observed_state",
                            "candidate_edge",
                            "required_check",
                            "forbidden_sibling",
                            "permitted_update_if_paid",
                            "stop_rule",
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    write_receipt(payload, a1, a2, a3)
    data = json.loads((payload / "research_done.json").read_text(encoding="utf-8"))
    data["carrier_schema_receipts"] = {
        "meta_language_edge_receipt": {
            "observed_state": "surface labels are recurring",
            "candidate_edge": "residual-to-check edge selects a typed schema",
            "required_check": "field-complete schema receipt",
            "forbidden_sibling": "pattern label only",
            "permitted_update_if_paid": "allow the schema-selected check",
            "stop_rule": "stop if the schema cannot reject the sibling",
        }
    }
    (payload / "research_done.json").write_text(json.dumps(data), encoding="utf-8")

    assert mod._research_done_error(
        payload, start_row(hard_research_residual=True), "T", "C"
    ) is None


def test_research_done_rejects_incomplete_typed_carrier_schema_receipt(
    tmp_path, monkeypatch
):
    mod = load_module()
    monkeypatch.setattr(mod, "REPO", tmp_path)
    monkeypatch.setattr(mod, "STORE", tmp_path / "store")

    payload = tmp_path / "payload"
    a1, a2, a3 = write_artifacts(payload)
    contract = payload / "artifacts" / "pattern_action_contract.json"
    contract.parent.mkdir(parents=True, exist_ok=True)
    contract.write_text(
        json.dumps(
            {
                "problem_surfaces": ["claim_boundary_schema_receipt"],
                "pattern_chain": ["OP-CBM-01"],
                "evidence_carriers": [
                    {
                        "name": "claim_boundary_typed_rows",
                        "required": True,
                        "artifact_slot": "claim_boundary_schema_artifact",
                        "required_fields": [
                            "claim_kind",
                            "answer_object",
                            "success_criterion",
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    write_receipt(payload, a1, a2, a3)
    data = json.loads((payload / "research_done.json").read_text(encoding="utf-8"))
    data["carrier_schema_receipts"] = {
        "claim_boundary_typed_rows": {
            "claim_kind": "narrow",
            "answer_object": "restricted witness",
        }
    }
    (payload / "research_done.json").write_text(json.dumps(data), encoding="utf-8")

    error = mod._research_done_error(
        payload, start_row(hard_research_residual=True), "T", "C"
    )
    assert "needs rows[]" in error


def test_research_done_rejects_schema_placeholder_values(tmp_path, monkeypatch):
    mod = load_module()
    monkeypatch.setattr(mod, "REPO", tmp_path)
    monkeypatch.setattr(mod, "STORE", tmp_path / "store")

    payload = tmp_path / "payload"
    a1, a2, a3 = write_artifacts(payload)
    contract = payload / "artifacts" / "pattern_action_contract.json"
    contract.parent.mkdir(parents=True, exist_ok=True)
    contract.write_text(
        json.dumps(
            {
                "problem_surfaces": ["hard_research_residual"],
                "pattern_chain": ["PATTERN-028"],
                "evidence_carriers": [
                    {
                        "name": "tool_pass",
                        "required": True,
                        "artifact_slot": "tool_pass_artifact",
                        "required_fields": ["first_failed_line"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    write_receipt(payload, a1, a2, a3)
    data = json.loads((payload / "research_done.json").read_text(encoding="utf-8"))
    data["carrier_schema_receipts"] = {
        "tool_pass": {"first_failed_line": "REPLACE_ME"}
    }
    (payload / "research_done.json").write_text(json.dumps(data), encoding="utf-8")

    error = mod._research_done_error(
        payload, start_row(hard_research_residual=True), "T", "C"
    )
    assert "missing required fields" in error


def test_research_done_enforces_claim_boundary_row_semantics(tmp_path, monkeypatch):
    mod = load_module()
    monkeypatch.setattr(mod, "REPO", tmp_path)
    monkeypatch.setattr(mod, "STORE", tmp_path / "store")

    payload = tmp_path / "payload"
    a1, a2, a3 = write_artifacts(payload)
    contract = payload / "artifacts" / "pattern_action_contract.json"
    contract.parent.mkdir(parents=True, exist_ok=True)
    contract.write_text(
        json.dumps(
            {
                "problem_surfaces": ["claim_boundary_schema_receipt"],
                "pattern_chain": ["OP-CBM-01"],
                "evidence_carriers": [
                    {
                        "name": "claim_boundary_typed_rows",
                        "required": True,
                        "artifact_slot": "claim_boundary_schema_artifact",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    write_receipt(payload, a1, a2, a3)
    data = json.loads((payload / "research_done.json").read_text(encoding="utf-8"))
    valid_rows = [
        {
            "claim_kind": "broad",
            "claim_text": "the broad route works",
            "answer_object": "full route certificate",
            "success_criterion": "all branches paid",
            "evidence_available": "partial receipt only",
            "missing_evidence_or_blocker": "unpaid anti-laundering",
            "permitted_status": "BLOCKED",
            "pass_fail_boundary": "requires anti-laundering receipt",
        },
        {
            "claim_kind": "narrow",
            "claim_text": "the schema rejects a confuser",
            "answer_object": "confuser rejection receipt",
            "success_criterion": "broad row remains blocked",
            "evidence_available": "typed schema present",
            "missing_evidence_or_blocker": "not a full route certificate",
            "permitted_status": "PERMITTED",
            "pass_fail_boundary": "only confuser rejection is licensed",
        },
    ]
    data["carrier_schema_receipts"] = {
        "claim_boundary_typed_rows": {"rows": valid_rows}
    }
    (payload / "research_done.json").write_text(json.dumps(data), encoding="utf-8")
    assert mod._research_done_error(
        payload, start_row(hard_research_residual=True), "T", "C"
    ) is None

    bad = json.loads((payload / "research_done.json").read_text(encoding="utf-8"))
    bad["carrier_schema_receipts"]["claim_boundary_typed_rows"]["rows"][0][
        "permitted_status"
    ] = "PERMITTED"
    (payload / "research_done.json").write_text(json.dumps(bad), encoding="utf-8")
    error = mod._research_done_error(
        payload, start_row(hard_research_residual=True), "T", "C"
    )
    assert "broad row must be BLOCKED" in error


def test_research_done_rejects_meta_edge_label_as_required_check(
    tmp_path, monkeypatch
):
    mod = load_module()
    monkeypatch.setattr(mod, "REPO", tmp_path)
    monkeypatch.setattr(mod, "STORE", tmp_path / "store")

    payload = tmp_path / "payload"
    a1, a2, a3 = write_artifacts(payload)
    contract = payload / "artifacts" / "pattern_action_contract.json"
    contract.parent.mkdir(parents=True, exist_ok=True)
    contract.write_text(
        json.dumps(
            {
                "problem_surfaces": ["meta_language_edge_carrier"],
                "pattern_chain": ["mm_03"],
                "evidence_carriers": [
                    {
                        "name": "meta_language_edge_receipt",
                        "required": True,
                        "artifact_slot": "meta_language_edge_artifact",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    write_receipt(payload, a1, a2, a3)
    data = json.loads((payload / "research_done.json").read_text(encoding="utf-8"))
    data["carrier_schema_receipts"] = {
        "meta_language_edge_receipt": {
            "observed_state": "surface labels are recurring",
            "candidate_edge": "residual-to-check edge",
            "required_check": "mm label",
            "forbidden_sibling": "pattern label only",
            "permitted_update_if_paid": "allow check",
            "stop_rule": "stop if only label remains",
        }
    }
    (payload / "research_done.json").write_text(json.dumps(data), encoding="utf-8")
    error = mod._research_done_error(
        payload, start_row(hard_research_residual=True), "T", "C"
    )
    assert "required_check cannot be a label" in error


def test_research_done_rejects_repo_artifact_not_sync_allowlisted(tmp_path, monkeypatch):
    mod = load_module()
    monkeypatch.setattr(mod, "REPO", tmp_path)
    monkeypatch.setattr(mod, "STORE", tmp_path / "store")

    deploy = tmp_path / "deploy"
    deploy.mkdir()
    (deploy / "vps_sync_files.txt").write_text(
        "allowed/orientation.md\nallowed/stress.md\nallowed/verification.md\n",
        encoding="utf-8",
    )
    for rel in (
        "allowed/orientation.md",
        "allowed/stress.md",
        "allowed/verification.md",
        "scratch/pack.md",
    ):
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rel, encoding="utf-8")

    payload = tmp_path / "payload"
    write_receipt(
        payload,
        {"root": "repo", "path": "scratch/pack.md"},
        {"root": "repo", "path": "allowed/stress.md"},
        {"root": "repo", "path": "allowed/verification.md"},
    )
    assert "not VPS-sync allowlisted" in mod._research_done_error(
        payload, start_row(hard_research_residual=True), "T", "C"
    )

    write_receipt(
        payload,
        {"root": "repo", "path": "allowed/orientation.md"},
        {"root": "repo", "path": "allowed/stress.md"},
        {"root": "repo", "path": "allowed/verification.md"},
    )
    assert mod._research_done_error(
        payload, start_row(hard_research_residual=True), "T", "C"
    ) is None


def test_research_done_rejects_reused_refs_and_verifies_sha(tmp_path, monkeypatch):
    mod = load_module()
    monkeypatch.setattr(mod, "REPO", tmp_path)
    monkeypatch.setattr(mod, "STORE", tmp_path / "store")

    payload = tmp_path / "payload"
    a1, a2, a3 = write_artifacts(payload)
    write_receipt(payload, a1, a1, a3)
    assert "reuses artifact ref" in mod._research_done_error(
        payload, start_row(hard_research_residual=True), "T", "C"
    )

    path = payload / a1
    good_sha = hashlib.sha256(path.read_bytes()).hexdigest()
    write_receipt(payload, {"path": a1, "sha256": good_sha}, a2, a3)
    assert mod._research_done_error(
        payload, start_row(hard_research_residual=True), "T", "C"
    ) is None

    write_receipt(payload, {"path": a1, "sha256": "0" * 64}, a2, a3)
    assert "sha256 mismatch" in mod._research_done_error(
        payload, start_row(hard_research_residual=True), "T", "C"
    )


def test_research_done_rejects_symlink_escape(tmp_path, monkeypatch):
    mod = load_module()
    monkeypatch.setattr(mod, "REPO", tmp_path)
    monkeypatch.setattr(mod, "STORE", tmp_path / "store")

    payload = tmp_path / "payload"
    a1, a2, a3 = write_artifacts(payload)
    outside = tmp_path / "outside.md"
    outside.write_text("outside", encoding="utf-8")
    link = payload / "artifacts/link.md"
    link.symlink_to(outside)
    write_receipt(payload, "artifacts/link.md", a2, a3)
    assert "resolves outside declared root" in mod._research_done_error(
        payload, start_row(hard_research_residual=True), "T", "C"
    )


def test_f_row_date_normalizes_plain_iso_before_freeze(tmp_path):
    mod = load_module()
    payload = tmp_path / "payload"
    payload.mkdir()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    row = payload / "f_row.txt"
    row.write_text(f"F-ROW\nowner: codex:RD\ndate: {today}\n", encoding="utf-8")

    assert mod._ensure_f_row_date(payload, write=True) is None
    assert f"date: `{today}`" in row.read_text(encoding="utf-8")


def test_premature_negative_witness_that_argues_nonapplicability_is_rejected(
    monkeypatch,
):
    mod = load_module()
    monkeypatch.setattr(
        mod,
        "_start_obligation_specs",
        lambda _start: {
            "premature_settled_negative": {
                "witness_schema": {
                    "required": [
                        "constructed_falsifier_or_derived_obstruction",
                        "why_not_consensus_gravity",
                    ]
                },
                "why_not_enum": ["not_a_negative_claim"],
            }
        },
    )

    err = mod._obligation_payload_error(
        {},
        {
            "premature_settled_negative": {
                "constructed_falsifier_or_derived_obstruction": "bounded boundary",
                "why_not_consensus_gravity": (
                    "This is not a consensus negative; it preserves the live "
                    "construction target."
                ),
            }
        },
        {},
    )
    assert "Move this discharge to why_not" in err
