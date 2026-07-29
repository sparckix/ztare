from __future__ import annotations

from pathlib import Path

import pytest

from ztare.leanmill.frontier_campaign_roles import (
    FRONTIER_RUNTIME_ROLES,
    frontier_role_artifact_directories,
    frontier_role_artifact_name,
    validate_frontier_runtime_role,
)


def test_every_declared_role_has_a_path_safe_artifact_identity(tmp_path: Path) -> None:
    for role in FRONTIER_RUNTIME_ROLES:
        base = tmp_path / frontier_role_artifact_name(role)
        instance = tmp_path / frontier_role_artifact_name(
            role, "lineage-000.wave-001"
        )
        base.mkdir()
        instance.mkdir()

        assert frontier_role_artifact_directories(tmp_path, role) == (
            base,
            instance,
        )


def test_role_artifact_discovery_rejects_near_prefixes_and_symlinks(
    tmp_path: Path,
) -> None:
    (tmp_path / "navigator").mkdir()
    (tmp_path / "navigator_evil").mkdir()
    (tmp_path / "navigator..wave-001").mkdir()
    outside = tmp_path.parent / "outside-navigator-calls"
    outside.mkdir(exist_ok=True)
    (tmp_path / "navigator.wave-002").symlink_to(outside, target_is_directory=True)

    assert frontier_role_artifact_directories(tmp_path, "navigator") == (
        tmp_path / "navigator",
    )


@pytest.mark.parametrize(
    "role",
    ("../navigator", "navigator/../../formalizer", "not_registered"),
)
def test_role_identity_rejects_traversal_and_unregistered_names(role: str) -> None:
    with pytest.raises(ValueError):
        validate_frontier_runtime_role(role)
