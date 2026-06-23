from __future__ import annotations

import json
from pathlib import Path

from ztare.workspace.evidence_gaps import (
    EVIDENCE_GAP_RECOVERY_CONTRACT_SCHEMA,
    INACTIVE_RECOVERY_KIND,
    LOCAL_VERIFICATION_RECOVERY_KIND,
    PUBLIC_EVIDENCE_RECOVERY_KIND,
    canonicalize_evidence_gap_recovery_contract,
    evidence_gap_activity,
    evidence_gap_is_active,
    evidence_gap_recovery,
    evidence_gap_recovery_contract,
)


def test_missing_local_artifact_gap_retires_when_artifact_exists(tmp_path: Path) -> None:
    project = tmp_path / "projects" / "demo"
    project.mkdir(parents=True)
    (project / "test_model.py").write_text("def I_model():\n    return 1.0\n", encoding="utf-8")
    gap = {
        "target": "test_model.py",
        "description": "Falsification suite is missing.",
        "severity": "degrading",
    }

    state = evidence_gap_activity(gap, project_dir=project)

    assert state == {
        "active": False,
        "status": "resolved_by_local_artifact",
        "target": "test_model.py",
        "artifact": "test_model.py",
    }
    assert evidence_gap_is_active(gap, project_dir=project) is False


def test_path_safety_gap_retires_when_local_verifier_receipt_covers_policy(
    tmp_path: Path,
) -> None:
    project = tmp_path / "projects" / "demo"
    workspace = project / "workspace"
    workspace.mkdir(parents=True)
    (workspace / "packet_falsifier_receipt.json").write_text(
        json.dumps(
            {
                "status": "resolved",
                "path_safety": {
                    "absolute_local_refs_allowed": False,
                    "parent_traversal_allowed": False,
                    "symlink_escape_allowed": False,
                },
            }
        ),
        encoding="utf-8",
    )
    gap = {
        "target": "preflight path resolution",
        "description": (
            "No test of malicious symlinks, ../ traversals, or circular references "
            "that could bypass local-path checks."
        ),
        "producer_rationale": "Local path validation must be machine-enforced.",
        "recovery_kind": "local_verification",
        "severity": "degrading",
    }

    state = evidence_gap_activity(gap, project_dir=project)
    recovery = evidence_gap_recovery(gap, project_dir=project)

    assert state == {
        "active": False,
        "status": "resolved_by_local_verifier_receipt",
        "target": "preflight path resolution",
        "artifact": "workspace/packet_falsifier_receipt.json",
        "receipt_type": "project_packet_falsifier",
        "verified_policy": "path_safety",
    }
    assert recovery["recovery_kind"] == INACTIVE_RECOVERY_KIND
    assert evidence_gap_is_active(gap, project_dir=project) is False


def test_local_verifier_receipt_does_not_retire_unrelated_local_gap(
    tmp_path: Path,
) -> None:
    project = tmp_path / "projects" / "demo"
    workspace = project / "workspace"
    workspace.mkdir(parents=True)
    (workspace / "packet_falsifier_receipt.json").write_text(
        json.dumps(
            {
                "status": "resolved",
                "path_safety": {
                    "absolute_local_refs_allowed": False,
                    "parent_traversal_allowed": False,
                    "symlink_escape_allowed": False,
                },
            }
        ),
        encoding="utf-8",
    )
    gap = {
        "target": "judge calibration",
        "description": "Local verifier still needs a unit test for judge score caps.",
        "recovery_kind": "local_verification",
        "severity": "degrading",
    }

    assert evidence_gap_activity(gap, project_dir=project) == {
        "active": True,
        "status": "active",
    }
    assert evidence_gap_recovery(gap, project_dir=project)["recovery_kind"] == (
        LOCAL_VERIFICATION_RECOVERY_KIND
    )


def test_external_or_semantic_gap_stays_active_even_if_target_names_file(
    tmp_path: Path,
) -> None:
    project = tmp_path / "projects" / "demo"
    project.mkdir(parents=True)
    (project / "test_model.py").write_text("def I_model():\n    return 1.0\n", encoding="utf-8")
    semantic_gap = {
        "target": "test_model.py",
        "description": "The suite needs stronger adversarial coverage.",
        "severity": "degrading",
    }
    external_gap = {
        "target": "https://example.test/paper",
        "description": "The public source is missing.",
        "severity": "degrading",
    }

    assert evidence_gap_is_active(semantic_gap, project_dir=project) is True
    assert evidence_gap_is_active(external_gap, project_dir=project) is True


def test_evidence_gap_recovery_classifies_public_vs_local_verifier() -> None:
    public_gap = {
        "target": "baseline corpus",
        "description": "More public evidence is needed.",
        "severity": "degrading",
    }
    local_gap = {
        "target": "packet_elements",
        "description": (
            "No evidence that source/evidence references were actually checked "
            "for existence and correctness."
        ),
        "producer_rationale": "Existence of labels treated as proof",
        "severity": "degrading",
    }

    assert (
        evidence_gap_recovery(public_gap)["recovery_kind"]
        == PUBLIC_EVIDENCE_RECOVERY_KIND
    )
    assert (
        evidence_gap_recovery(local_gap)["recovery_kind"]
        == LOCAL_VERIFICATION_RECOVERY_KIND
    )


def test_evidence_gap_recovery_classifies_packet_reference_resolution_as_local() -> None:
    gap = {
        "target": "intake readiness",
        "description": (
            "Thesis commits syntactic checklist fallacy by treating enumeration "
            "of packet elements as sufficient evidence of validation; no "
            "demonstration that references resolve or are consistent beyond naming."
        ),
        "producer_rationale": (
            "The mechanism must be tested by local source/evidence references, "
            "not fetched as a new public source."
        ),
        "severity": "degrading",
    }

    recovery = evidence_gap_recovery(gap)
    contract = evidence_gap_recovery_contract(gap)

    assert recovery["recovery_kind"] == LOCAL_VERIFICATION_RECOVERY_KIND
    assert recovery["classification_source"] == "legacy_text"
    assert contract["classification_source"] == "legacy_text"
    assert contract["classification_strength"] == "fallback_inference"
    assert contract["schema_promotion_required"] is True
    assert contract["advisories"] == ["schema_promotion_required_for_recovery_route"]


def test_evidence_gap_recovery_classifies_fixture_extension_as_local_prep() -> None:
    cache_gap = {
        "target": "support_console_cache_independence",
        "description": "No fixture record tests whether cache_miss_rate > 0.10 can occur with batch_duration < 400 s",
        "fetch_query": "extend fixture with cache_miss under healthy export",
    }
    code_gap = {
        "target": "chg_142_batching_flag",
        "description": "S001 lacks documentation of what the batching flag does or how it produces 900 s timeouts",
        "fetch_query": "change documentation or code for CHG-142",
    }

    cache_recovery = evidence_gap_recovery(cache_gap)
    code_recovery = evidence_gap_recovery(code_gap)

    assert cache_recovery["recovery_kind"] == LOCAL_VERIFICATION_RECOVERY_KIND
    assert cache_recovery["classification_source"] == "legacy_text"
    assert code_recovery["recovery_kind"] == LOCAL_VERIFICATION_RECOVERY_KIND
    assert code_recovery["classification_source"] == "legacy_text"


def test_evidence_gap_recovery_uses_explicit_schema_before_text() -> None:
    public_gap = {
        "target": "local_preflight_fixture",
        "description": "Verification wording appears here but this row needs external evidence.",
        "recovery_channel": "out_of_loop_evidence_recovery",
    }
    local_gap = {
        "target": "https://example.test/source",
        "description": "A URL can still be a local source-preflight integrity target.",
        "recovery": {"action_type": "in_loop_focus_receipt"},
    }

    public_recovery = evidence_gap_recovery(public_gap)
    local_recovery = evidence_gap_recovery(local_gap)

    assert public_recovery["recovery_kind"] == PUBLIC_EVIDENCE_RECOVERY_KIND
    assert public_recovery["classification_source"] == "explicit_schema"
    assert local_recovery["recovery_kind"] == LOCAL_VERIFICATION_RECOVERY_KIND
    assert local_recovery["classification_source"] == "explicit_schema"
    assert evidence_gap_recovery_contract(public_gap)["schema_promotion_required"] is False
    assert evidence_gap_recovery_contract(local_gap)["schema_promotion_required"] is False


def test_evidence_gap_recovery_uses_boolean_contract_fields() -> None:
    public_gap = {
        "target": "external benchmark",
        "description": "The description mentions a local fixture but the route is public.",
        "can_public_fetch": True,
        "in_loop_consumable": False,
    }
    local_gap = {
        "target": "source-preflight receipt",
        "description": "More public evidence is needed, but this row is a local verifier task.",
        "can_public_fetch": False,
        "in_loop_consumable": True,
    }

    assert evidence_gap_recovery(public_gap)["recovery_kind"] == (
        PUBLIC_EVIDENCE_RECOVERY_KIND
    )
    assert evidence_gap_recovery(local_gap)["recovery_kind"] == (
        LOCAL_VERIFICATION_RECOVERY_KIND
    )
    assert evidence_gap_recovery_contract(public_gap)["can_public_fetch"] is True
    assert evidence_gap_recovery_contract(local_gap)["in_loop_consumable"] is True


def test_evidence_gap_recovery_contract_records_schema_and_conflicts() -> None:
    gap = {
        "gap_type": "other",
        "target": "source-preflight receipt",
        "description": "The local checker needs a fixture.",
        "recovery_kind": "local_verification",
        "recovery_channel": "out_of_loop_evidence_recovery",
        "can_public_fetch": True,
        "in_loop_consumable": False,
    }

    contract = evidence_gap_recovery_contract(gap)

    assert contract["schema"] == EVIDENCE_GAP_RECOVERY_CONTRACT_SCHEMA
    assert contract["contract_ok"] is False
    assert contract["recovery_kind"] == LOCAL_VERIFICATION_RECOVERY_KIND
    assert contract["recovery_channel"] == "in_loop_focus_receipt"
    assert contract["can_public_fetch"] is False
    assert contract["in_loop_consumable"] is True
    assert contract["warnings"] == [
        "can_public_fetch_conflicted_with_recovery_kind",
        "in_loop_consumable_conflicted_with_recovery_kind",
        "recovery_channel_conflicted_with_recovery_kind",
    ]


def test_evidence_gap_contract_canonicalizes_explicit_local_route() -> None:
    gap = {
        "gap_type": "other",
        "target": "support_console_cache_independence",
        "description": "No fixture record tests whether cache_miss_rate can occur under healthy export.",
        "fetch_query": "extend fixture with cache_miss under healthy export",
    }

    row = canonicalize_evidence_gap_recovery_contract(
        gap,
        recovery_kind="local_verification",
        recovery_channel="in_loop_focus_receipt",
        can_public_fetch="false",
        in_loop_consumable="true",
    )

    assert row["recovery_kind"] == LOCAL_VERIFICATION_RECOVERY_KIND
    assert row["recovery_channel"] == "in_loop_focus_receipt"
    assert row["required_surface"] == "local_verifier_or_fixture"
    assert row["can_public_fetch"] is False
    assert row["in_loop_consumable"] is True
    assert row["recovery_contract_source"] == "explicit_schema"
    assert "recovery_contract_warnings" not in row
    assert row["recovery_contract"]["schema"] == EVIDENCE_GAP_RECOVERY_CONTRACT_SCHEMA
    assert row["recovery_contract"]["contract_ok"] is True
    assert row["recovery_contract"]["in_loop_consumable"] is True
    assert row["recovery_contract"]["classification_source"] == "explicit_schema"
    assert row["recovery_contract"]["schema_promotion_required"] is False


def test_evidence_gap_contract_normalizes_contradictory_route_fields() -> None:
    gap = {
        "gap_type": "other",
        "target": "chg_142_batching_flag",
        "description": "The local code path is not documented or tested.",
    }

    row = canonicalize_evidence_gap_recovery_contract(
        gap,
        recovery_kind="local_verification",
        recovery_channel="out_of_loop_evidence_recovery",
        can_public_fetch="true",
        in_loop_consumable="false",
    )

    assert row["recovery_kind"] == LOCAL_VERIFICATION_RECOVERY_KIND
    assert row["recovery_channel"] == "in_loop_focus_receipt"
    assert row["can_public_fetch"] is False
    assert row["in_loop_consumable"] is True
    assert row["recovery_contract_source"] == "explicit_schema"
    assert row["recovery_contract_warnings"] == [
        "can_public_fetch_conflicted_with_recovery_kind",
        "in_loop_consumable_conflicted_with_recovery_kind",
        "recovery_channel_conflicted_with_recovery_kind",
    ]
    assert row["recovery_contract"]["contract_ok"] is False
    assert row["recovery_contract"]["warnings"] == row["recovery_contract_warnings"]
