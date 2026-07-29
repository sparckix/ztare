from __future__ import annotations

import os
from pathlib import Path

import pytest

from ztare.leanmill import reviewed_construction_campaign as campaign_module
from ztare.leanmill.reviewed_construction_campaign import (
    _persist_exact,
    _persisted_parameterization_execution,
    _read_bounded_authority_slot,
    validate_persisted_family_execution_slot,
)
from ztare.leanmill.frontier_campaign_runner import (
    _MAX_REVIEWED_CONSTRUCTION_ARTIFACT_BYTES,
    _existing_reviewed_family_member_ratification_aggregate,
    _read_bounded_reviewed_construction_artifact,
)


def test_exact_authority_slot_is_create_only_bounded_and_link_safe(
    tmp_path: Path,
) -> None:
    path = tmp_path / "authority.json"
    row = {"schema": "fixture.authority.v1", "value": 1}

    _persist_exact(path, row, context="fixture authority", max_bytes=256)
    _persist_exact(path, row, context="fixture authority", max_bytes=256)
    with pytest.raises(ValueError, match="identity conflicts"):
        _persist_exact(
            path,
            {**row, "value": 2},
            context="fixture authority",
            max_bytes=256,
        )

    link = tmp_path / "authority-link.json"
    link.symlink_to(path)
    with pytest.raises(ValueError, match="authority slot is unavailable"):
        _read_bounded_authority_slot(
            link, max_bytes=256, context="linked fixture"
        )

    oversized = tmp_path / "oversized.json"
    oversized.write_bytes(b'{"value":"' + b"x" * 64 + b'"}')
    with pytest.raises(ValueError, match="exceeds its byte ceiling"):
        _read_bounded_authority_slot(
            oversized, max_bytes=32, context="oversized fixture"
        )


def test_exact_authority_reader_catches_growth_after_descriptor_stat(
    tmp_path: Path, monkeypatch
) -> None:
    path = tmp_path / "growing.json"
    path.write_bytes(b'{}')
    original_fstat = os.fstat
    grew = False

    def grow_after_stat(fd: int):
        nonlocal grew
        metadata = original_fstat(fd)
        if not grew:
            grew = True
            with path.open("ab") as handle:
                handle.write(b" " * 64)
                handle.flush()
                os.fsync(handle.fileno())
        return metadata

    monkeypatch.setattr(campaign_module.os, "fstat", grow_after_stat)
    with pytest.raises(ValueError, match="exceeds its byte ceiling"):
        _read_bounded_authority_slot(
            path, max_bytes=16, context="growing fixture"
        )


def test_family_and_parameterization_execution_slots_use_bounded_reader(
    tmp_path: Path,
) -> None:
    family_ref = "a" * 64
    family_path = tmp_path / "family-execution.json"
    family_path.write_text(
        '{"family_receipt_sha256":"' + family_ref + '"}',
        encoding="utf-8",
    )
    assert validate_persisted_family_execution_slot(
        family_path, family_receipt_sha256=family_ref
    ) == {"family_receipt_sha256": family_ref}

    linked_family = tmp_path / "linked-family-execution.json"
    linked_family.symlink_to(family_path)
    with pytest.raises(ValueError, match="authority slot is unavailable"):
        validate_persisted_family_execution_slot(
            linked_family, family_receipt_sha256=family_ref
        )

    parameterization_ref = "b" * 64
    current_path = tmp_path / (
        "construction_parameterization_execution_by_parameterization_"
        + parameterization_ref[:16]
        + ".json"
    )
    current_path.symlink_to(family_path)
    parameterization = {
        "receipt_sha256": parameterization_ref,
        "resource_limits": {"max_execution_receipt_bytes": 1_024},
    }
    with pytest.raises(ValueError, match="authority slot is unavailable"):
        _persisted_parameterization_execution(
            tmp_path,
            parameterization=parameterization,
            witness_schema={},
        )


def test_family_execution_dual_replay_has_one_aggregate_ceiling(
    tmp_path: Path, monkeypatch
) -> None:
    family_ref = "d" * 64
    current = tmp_path / "current-family-execution.json"
    legacy = tmp_path / "legacy-family-execution.json"
    payload = '{"family_receipt_sha256":"' + family_ref + '"}'
    current.write_text(payload, encoding="utf-8")
    legacy.write_text(payload, encoding="utf-8")
    monkeypatch.setattr(
        campaign_module,
        "_MAX_FAMILY_EXECUTION_REPLAY_AGGREGATE_BYTES",
        current.stat().st_size + legacy.stat().st_size - 1,
    )
    aggregate_budget = {"bytes": 0}
    assert validate_persisted_family_execution_slot(
        current,
        family_receipt_sha256=family_ref,
        aggregate_budget=aggregate_budget,
    ) == {"family_receipt_sha256": family_ref}
    with pytest.raises(ValueError, match="replay aggregate byte ceiling"):
        validate_persisted_family_execution_slot(
            legacy,
            family_receipt_sha256=family_ref,
            aggregate_budget=aggregate_budget,
        )


def test_authority_slot_accepts_exact_ceiling_and_rejects_one_more_byte(
    tmp_path: Path,
) -> None:
    path = tmp_path / "boundary-size.json"
    payload = b'{"value":"boundary"}'
    path.write_bytes(payload)
    assert _read_bounded_authority_slot(
        path, max_bytes=len(payload), context="boundary-size fixture"
    ) == ({"value": "boundary"}, len(payload))

    path.write_bytes(payload + b" ")
    with pytest.raises(ValueError, match="exceeds its byte ceiling"):
        _read_bounded_authority_slot(
            path, max_bytes=len(payload), context="boundary-size fixture"
        )


def test_recovery_ceiling_covers_all_reviewed_construction_producers() -> None:
    from ztare.leanmill.construction_parameterization import (
        _MAX_PARAMETERIZATION_ENVELOPE_BYTES,
    )
    from ztare.leanmill.finite_construction_family import (
        _MAX_FAMILY_EXECUTION_MEMBER_BYTES,
        _MAX_FAMILY_PROTOCOL_BYTES,
    )

    assert campaign_module._MAX_CONSTRUCTION_AUTHORITY_SLOT_BYTES >= max(
        _MAX_PARAMETERIZATION_ENVELOPE_BYTES,
        _MAX_FAMILY_EXECUTION_MEMBER_BYTES,
        _MAX_FAMILY_PROTOCOL_BYTES,
    )
    assert _MAX_REVIEWED_CONSTRUCTION_ARTIFACT_BYTES >= max(
        _MAX_PARAMETERIZATION_ENVELOPE_BYTES,
        _MAX_FAMILY_EXECUTION_MEMBER_BYTES,
        _MAX_FAMILY_PROTOCOL_BYTES,
    )


def test_runner_owner_slot_reader_is_link_safe_and_boundary_inclusive(
    tmp_path: Path, monkeypatch
) -> None:
    from ztare.leanmill import frontier_campaign_runner as runner_module

    path = tmp_path / "runner-owner.json"
    payload = b'{"value":"owner"}'
    path.write_bytes(payload)
    monkeypatch.setattr(
        runner_module,
        "_MAX_REVIEWED_CONSTRUCTION_ARTIFACT_BYTES",
        len(payload),
    )
    assert _read_bounded_reviewed_construction_artifact(
        path, label="runner owner fixture"
    ) == {"value": "owner"}

    link = tmp_path / "runner-owner-link.json"
    link.symlink_to(path)
    with pytest.raises(ValueError, match="authority slot is unavailable"):
        _read_bounded_reviewed_construction_artifact(
            link, label="linked runner owner fixture"
        )

    path.write_bytes(payload + b" ")
    with pytest.raises(ValueError, match="exceeds its byte ceiling"):
        _read_bounded_reviewed_construction_artifact(
            path, label="oversized runner owner fixture"
        )


def test_legacy_ratification_lookup_stops_at_candidate_ceiling(
    tmp_path: Path, monkeypatch
) -> None:
    from ztare.leanmill import frontier_campaign_runner as runner_module

    for index in range(2):
        (tmp_path / f"reviewed_family_member_ratification.{index:016x}.json").write_text(
            "{}", encoding="utf-8"
        )
    monkeypatch.setattr(
        runner_module,
        "_MAX_REVIEWED_CONSTRUCTION_LEGACY_CANDIDATES",
        1,
    )

    with pytest.raises(ValueError, match="legacy candidate ceiling exceeded"):
        _existing_reviewed_family_member_ratification_aggregate(
            tmp_path,
            {"receipt_sha256": "c" * 64},
        )
