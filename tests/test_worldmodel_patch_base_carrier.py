from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from ztare.fit.mdl import description_units
from ztare.worldmodel.patch_base_carrier import (
    compact_literal_patch_prefix,
    compose_patch_base_carrier,
    composed_carrier_description_length,
    resolved_patch_base_paths,
)
from ztare.worldmodel.carrier_loader import load_carrier_from_source


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


def test_patch_base_carrier_transports_base_consumer_projection(
    tmp_path: Path,
) -> None:
    base, digest = _write_base(tmp_path)
    projection = object()

    def load_with_projection(namespace):
        program = namespace["step"]
        program._ztare_factored_projection = projection
        return program

    carrier = compose_patch_base_carrier(
        {
            "PATCH_BASE": {
                "source_ref": str(base.relative_to(tmp_path)),
                "sha256": digest,
            },
            "PATCH_DELTA": lambda base_next, _state, _action: base_next,
        },
        project_dir=tmp_path,
        load_program_from_namespace=load_with_projection,
        call_program=_call_program,
    )

    assert carrier is not None
    assert carrier._ztare_factored_projection is projection
    assert carrier._ztare_factored_projection_transport == {
        "kind": "patch_base_interface_transport",
        "source_ref": str(base.relative_to(tmp_path)),
        "source_sha256": digest,
        "compatibility_guard": "search_factored_noncommutation",
    }


def test_patch_base_carrier_composes_literal_catalog_delta(tmp_path: Path) -> None:
    base = tmp_path / "workspace" / "submissions" / "moving_base.py"
    base.parent.mkdir(parents=True)
    base.write_text(
        "def step(grid, action, t):\n"
        "    out = [list(row) for row in grid]\n"
        "    if action == 1:\n"
        "        out[0][0], out[0][1] = 0, 7\n"
        "    return tuple(tuple(row) for row in out)\n",
        encoding="utf-8",
    )
    digest = hashlib.sha256(base.read_bytes()).hexdigest()
    namespace = {
        "PATCH_BASE": {
            "source_ref": str(base.relative_to(tmp_path)),
            "sha256": digest,
        },
        "PATCH_DELTA_SPEC": {
            "actions": {},
            "always": [
                {
                    "op": "region_event",
                    "mover_colors": [7],
                    "rect": [0, 1, 0, 1],
                    "edge": "enter",
                    "writes": [[9, [[1, 1]]]],
                }
            ],
        },
    }

    carrier = compose_patch_base_carrier(
        namespace,
        project_dir=tmp_path,
        load_program_from_namespace=_load_program,
        call_program=_call_program,
    )

    assert carrier is not None
    assert carrier(((7, 0), (0, 0)), 1, 0) == ((0, 7), (0, 9))
    assert carrier(((0, 7), (0, 0)), 0, 0) == ((0, 7), (0, 0))


def test_patch_base_partial_state_machine_severs_unsupported_base_image(
    tmp_path: Path,
) -> None:
    base = tmp_path / "workspace" / "submissions" / "totalized_base.py"
    base.parent.mkdir(parents=True)
    base.write_text(
        "def step(grid, action, t):\n"
        "    out = [list(row) for row in grid]\n"
        "    if action == 1:\n"
        "        out[0][0], out[0][1] = 0, 7\n"
        "    return tuple(tuple(row) for row in out)\n",
        encoding="utf-8",
    )
    digest = hashlib.sha256(base.read_bytes()).hexdigest()
    namespace = {
        "PATCH_BASE": {
            "source_ref": str(base.relative_to(tmp_path)),
            "sha256": digest,
        },
        "PATCH_DELTA_SPEC": {
            "actions": {},
            "always": [{
                "op": "region_event",
                "mover_colors": [7],
                "rect": [0, 1, 0, 1],
                "edge": "enter",
                "region": [1, 0, 1, 1],
                "content_states": [[0, 1], [1, 0]],
                "state_transition": [[0, 1]],
            }],
        },
    }

    carrier = compose_patch_base_carrier(
        namespace,
        project_dir=tmp_path,
        load_program_from_namespace=_load_program,
        call_program=_call_program,
    )

    assert carrier is not None
    assert carrier(((7, 0), (0, 1)), 1, 0) == ((0, 7), (1, 0))
    assert carrier(((7, 0), (1, 0)), 1, 0) is None


def test_patch_base_carrier_rejects_ambiguous_callable_and_catalog_delta(
    tmp_path: Path,
) -> None:
    base, digest = _write_base(tmp_path)
    namespace = {
        "PATCH_BASE": {
            "source_ref": str(base.relative_to(tmp_path)),
            "sha256": digest,
        },
        "PATCH_DELTA": lambda base_next, _state, _action: base_next,
        "PATCH_DELTA_SPEC": {
            "actions": {"0": [{"op": "identity"}]}
        },
    }

    with pytest.raises(ValueError, match="not both"):
        compose_patch_base_carrier(
            namespace,
            project_dir=tmp_path,
            load_program_from_namespace=_load_program,
            call_program=_call_program,
        )


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


def test_composed_description_length_counts_immutable_base_closure(
    tmp_path: Path,
) -> None:
    base, digest = _write_base(tmp_path)
    candidate = tmp_path / "candidate.py"
    candidate.write_text(
        "PATCH_BASE = {\n"
        f"    'source_ref': '{base.relative_to(tmp_path)}',\n"
        f"    'sha256': '{digest}',\n"
        "}\n"
        "def PATCH_DELTA(base_next, state, action):\n"
        "    return base_next\n",
        encoding="utf-8",
    )

    assert composed_carrier_description_length(
        candidate,
        project_dir=tmp_path,
    ) == description_units(candidate.read_text(), base.read_text())


def test_resolved_patch_base_paths_uses_execution_chain_identity(
    tmp_path: Path,
) -> None:
    base, base_digest = _write_base(tmp_path)
    middle = tmp_path / "workspace" / "submissions" / "middle.py"
    middle.write_text(
        "PATCH_BASE = {\n"
        f"    'source_ref': '{base.relative_to(tmp_path)}',\n"
        f"    'sha256': '{base_digest}',\n"
        "}\n"
        "def PATCH_DELTA(base_next, state, action):\n"
        "    return base_next\n",
        encoding="utf-8",
    )
    middle_digest = hashlib.sha256(middle.read_bytes()).hexdigest()
    candidate = tmp_path / "candidate.py"
    candidate.write_text(
        "PATCH_BASE = {\n"
        f"    'source_ref': '{middle.relative_to(tmp_path)}',\n"
        f"    'sha256': '{middle_digest}',\n"
        "}\n"
        "def PATCH_DELTA(base_next, state, action):\n"
        "    return base_next\n",
        encoding="utf-8",
    )

    assert resolved_patch_base_paths(
        candidate,
        project_dir=tmp_path,
    ) == (middle.resolve(), base.resolve())


def test_literal_patch_prefix_compaction_preserves_composed_behavior(
    tmp_path: Path,
) -> None:
    base, base_digest = _write_base(tmp_path)
    first = tmp_path / "workspace" / "submissions" / "first_spec.py"
    first.write_text(
        "PATCH_BASE = "
        + repr({"source_ref": str(base.relative_to(tmp_path)), "sha256": base_digest})
        + "\nPATCH_DELTA_SPEC = "
        + repr({
            "actions": {},
            "always": [{"op": "recolor_map", "mapping": {2: 4}}],
        })
        + "\n",
        encoding="utf-8",
    )
    first_digest = hashlib.sha256(first.read_bytes()).hexdigest()
    second = tmp_path / "workspace" / "submissions" / "second_spec.py"
    second.write_text(
        "PATCH_BASE = "
        + repr({"source_ref": str(first.relative_to(tmp_path)), "sha256": first_digest})
        + "\nPATCH_DELTA_SPEC = "
        + repr({
            "actions": {},
            "always": [{"op": "recolor_map", "mapping": {3: 5}}],
        })
        + "\n",
        encoding="utf-8",
    )

    compacted_source = compact_literal_patch_prefix(
        second,
        project_dir=tmp_path,
    )
    assert compacted_source is not None
    compacted = tmp_path / "workspace" / "submissions" / "compacted.py"
    compacted.write_text(compacted_source, encoding="utf-8")
    original = load_carrier_from_source(
        second.read_text(),
        second,
        tmp_path,
        attach_projection=False,
    )
    flattened = load_carrier_from_source(
        compacted_source,
        compacted,
        tmp_path,
        attach_projection=False,
    )

    probes = [(((1, 2),), 0, 0), (((3, 7),), 1, 9)]
    assert [original(*probe) for probe in probes] == [
        flattened(*probe) for probe in probes
    ]
    assert len(resolved_patch_base_paths(compacted, project_dir=tmp_path)) == 1
