from __future__ import annotations

import hashlib

import pytest

from ztare.worldmodel.carrier_loader import (
    CarrierEvidenceIdentityError,
    lower_carrier_namespace,
    require_current_carrier_evidence_binding,
    resolve_current_carrier_evidence_identity,
)


def _project(tmp_path):
    (tmp_path / "test_model.py").write_text("VALUE = 1\n", encoding="utf-8")
    episodes = tmp_path / "raw" / "episodes"
    episodes.mkdir(parents=True)
    (episodes / "episode_001.jsonl").write_text('{"row": 1}\n', encoding="utf-8")
    return tmp_path


def test_current_identity_uses_full_carrier_and_evidence_digests(tmp_path):
    project = _project(tmp_path)

    identity = resolve_current_carrier_evidence_identity(project)

    assert identity.carrier_sha256 == hashlib.sha256(
        (project / "test_model.py").read_bytes()
    ).hexdigest()
    assert len(identity.evidence_epoch_sha256) == 64
    assert require_current_carrier_evidence_binding(
        {"carrier_evidence_identity": identity.to_dict()}, identity
    ) == identity.to_dict()


def test_prefix_path_only_and_historical_epoch_do_not_join(tmp_path):
    identity = resolve_current_carrier_evidence_identity(_project(tmp_path))
    invalid = [
        {"carrier_sha256": identity.carrier_sha256[:12],
         "evidence_epoch_sha256": identity.evidence_epoch_sha256},
        {"carrier_ref": "test_model.py"},
        {"carrier_sha256": identity.carrier_sha256,
         "evidence_epoch_sha256": "0" * 64},
    ]

    for receipt in invalid:
        with pytest.raises(CarrierEvidenceIdentityError):
            require_current_carrier_evidence_binding(receipt, identity)


def test_adapter_identity_remains_opaque_but_participates_in_equality(tmp_path):
    project = _project(tmp_path)
    (project / "opaque.carrier").write_bytes(b"domain-defined carrier")
    identity = resolve_current_carrier_evidence_identity(
        project,
        carrier_ref="opaque.carrier",
        adapter_identity={"chart": "domain://three-dimensional/epoch-7"},
    )
    binding = identity.to_dict()

    assert require_current_carrier_evidence_binding(
        {"carrier_evidence_identity": binding}, identity
    )["adapter_identity"] == {"chart": "domain://three-dimensional/epoch-7"}
    binding["adapter_identity"] = {"chart": "another-epoch"}
    with pytest.raises(CarrierEvidenceIdentityError):
        require_current_carrier_evidence_binding(
            {"carrier_evidence_identity": binding}, identity
        )


def test_lowered_extension_carriers_keep_their_own_registry_snapshot(tmp_path):
    """Loading a rival cannot change an earlier carrier's operation meaning."""
    from ztare.worldmodel.grid_dsl import EXTENSIONS

    def source(replacement: int) -> str:
        return (
            "def extension(grid):\n"
            "    return tuple(tuple("
            f"{replacement} if cell == 1 else cell "
            "for cell in row) for row in grid)\n"
        )

    def ambient(grid):
        return tuple(tuple(4 if cell == 1 else cell for cell in row) for row in grid)

    EXTENSIONS["ambient_test_operation"] = ambient
    try:
        ambient_carrier = lower_carrier_namespace(
            {"PROGRAM": ("ext", "ambient_test_operation", ("s",))},
            project_dir=tmp_path,
            attach_projection=False,
        )
        first = lower_carrier_namespace(
            {
                "EXTENSIONS_SRC": {"replace_one": source(2)},
                "PROGRAM": ("ext", "replace_one", ("s",)),
            },
            project_dir=tmp_path,
            attach_projection=False,
        )
        second = lower_carrier_namespace(
            {
                "EXTENSIONS_SRC": {"replace_one": source(3)},
                "PROGRAM": ("ext", "replace_one", ("s",)),
            },
            project_dir=tmp_path,
            attach_projection=False,
        )
        grid = ((1, 0), (0, 1))
        assert first(grid, 0, 0) == ((2, 0), (0, 2))
        assert second(grid, 0, 0) == ((3, 0), (0, 3))
        assert first(grid, 0, 0) == ((2, 0), (0, 2))
        assert EXTENSIONS["ambient_test_operation"] is ambient
        assert "replace_one" not in EXTENSIONS
        EXTENSIONS["ambient_test_operation"] = lambda value: value
        assert ambient_carrier(grid, 0, 0) == ((4, 0), (0, 4))
    finally:
        EXTENSIONS.pop("ambient_test_operation", None)
