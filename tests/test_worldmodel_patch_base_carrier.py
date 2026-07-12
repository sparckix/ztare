from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from ztare.worldmodel.patch_base_carrier import compose_patch_base_carrier


def _write_base(project: Path) -> tuple[Path, str]:
    base = project / "workspace" / "submissions" / "base.py"
    base.parent.mkdir(parents=True)
    base.write_text(
        "def step(grid, action, t):\n"
        "    return tuple(tuple(cell + 1 for cell in row) for row in grid)\n",
        encoding="utf-8",
    )
    return base, hashlib.sha256(base.read_bytes()).hexdigest()


def _load_program(ns):
    return ns["step"]


def _call_program(program, grid, action, t):
    return program(grid, action, t)


def test_patch_base_carrier_composes_gate_owned_base_and_delta(tmp_path: Path) -> None:
    base, digest = _write_base(tmp_path)
    namespace = {
        "PATCH_BASE": {
            "source_ref": str(base.relative_to(tmp_path)),
            "sha256": digest,
        },
    }

    def _delta(base_next, _grid, action, _t):
        out = [list(row) for row in base_next]
        if action == 1:
            out[0][0] = 99
        return tuple(tuple(row) for row in out)

    namespace["PATCH_DELTA"] = _delta

    carrier = compose_patch_base_carrier(
        namespace,
        project_dir=tmp_path,
        load_program_from_namespace=_load_program,
        call_program=_call_program,
    )

    assert carrier is not None
    assert carrier(((1, 2),), 0, 0) == ((2, 3),)
    assert carrier(((1, 2),), 1, 0) == ((99, 3),)


def test_patch_base_carrier_rejects_hash_mismatch(tmp_path: Path) -> None:
    base, _digest = _write_base(tmp_path)
    namespace = {
        "PATCH_BASE_REF": str(base.relative_to(tmp_path)),
        "PATCH_BASE_SHA256": "deadbeef",
        "PATCH_DELTA": lambda base_next, _grid, _action, _t: base_next,
    }

    with pytest.raises(ValueError, match="sha256"):
        compose_patch_base_carrier(
            namespace,
            project_dir=tmp_path,
            load_program_from_namespace=_load_program,
            call_program=_call_program,
        )


def test_patch_base_carrier_rejects_live_root_candidate(tmp_path: Path) -> None:
    root_candidate = tmp_path / "test_model.py"
    root_candidate.write_text(
        "def step(grid, action, t):\n    return grid\n",
        encoding="utf-8",
    )
    digest = hashlib.sha256(root_candidate.read_bytes()).hexdigest()
    namespace = {
        "PATCH_BASE": {
            "source_ref": "test_model.py",
            "sha256": digest,
        },
        "PATCH_DELTA": lambda base_next, _grid, _action, _t: base_next,
    }

    with pytest.raises(ValueError, match="workspace/submissions"):
        compose_patch_base_carrier(
            namespace,
            project_dir=tmp_path,
            load_program_from_namespace=_load_program,
            call_program=_call_program,
        )


def test_patch_base_carrier_rejects_sha256_prefix_alias(tmp_path: Path) -> None:
    base, digest = _write_base(tmp_path)
    namespace = {
        "PATCH_BASE": {
            "source_ref": str(base.relative_to(tmp_path)),
            "sha256_prefix": digest[:12],
        },
        "PATCH_DELTA": lambda base_next, _state, _action, _t: base_next,
    }

    with pytest.raises(ValueError, match="full 64-hex"):
        compose_patch_base_carrier(
            namespace,
            project_dir=tmp_path,
            load_program_from_namespace=_load_program,
            call_program=_call_program,
        )


def test_patch_base_carrier_rejects_path_escape(tmp_path: Path) -> None:
    namespace = {
        "PATCH_BASE_REF": "../outside.py",
        "PATCH_DELTA": lambda base_next, _grid, _action, _t: base_next,
    }

    with pytest.raises(ValueError, match="project-relative|escapes"):
        compose_patch_base_carrier(
            namespace,
            project_dir=tmp_path,
            load_program_from_namespace=_load_program,
            call_program=_call_program,
        )
