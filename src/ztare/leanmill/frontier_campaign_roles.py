"""Canonical identities and artifact paths for frontier campaign roles.

The campaign definition, runtime, and operator observability actions all need
the same answer to two questions: which role identities may exist, and which
direct child directories belong to one of those identities.  Keep those
answers here so an operator surface cannot drift behind a newly executable
role.
"""
from __future__ import annotations

from pathlib import Path
import re


FRONTIER_RUNTIME_ROLES = frozenset(
    {
        "budget_compiler",
        "blueprint_compiler",
        "semantic_reviewer",
        "navigator",
        "lineage_synthesizer",
        "adapter_forge",
        "adapter_reviewer",
        "formalizer",
        "witness_constructor",
        "faithfulness_reviewer",
        "lean_solver",
        "post_freeze_interpreter",
        "external_science_reviewer",
    }
)

_ROLE_NAME = re.compile(r"[a-z][a-z0-9_]{0,63}\Z")
_INSTANCE_NAME = re.compile(r"[a-z0-9][a-z0-9_.-]{0,127}\Z")
MAX_FRONTIER_ROLE_ARTIFACT_DIRECTORIES = 256
MAX_FRONTIER_AGENT_CALL_ROOT_ENTRIES = 4_096


def validate_frontier_runtime_role(value: str) -> str:
    """Return one registered path-safe campaign role identity."""

    if not isinstance(value, str) or _ROLE_NAME.fullmatch(value) is None:
        raise ValueError("frontier campaign role is not a path-safe identity")
    if value not in FRONTIER_RUNTIME_ROLES:
        raise ValueError(f"unregistered frontier campaign role: {value}")
    return value


def validate_frontier_role_instance(value: str) -> str:
    """Validate the optional suffix used for one role's durable lineage."""

    if not isinstance(value, str) or _INSTANCE_NAME.fullmatch(value) is None:
        raise ValueError("frontier campaign role instance is not path-safe")
    if any(part in {"", ".", ".."} for part in value.split(".")):
        raise ValueError("frontier campaign role instance has unsafe segments")
    return value


def frontier_role_artifact_name(role: str, instance: str = "") -> str:
    """Build the direct-child directory name owned by a role invocation."""

    base = validate_frontier_runtime_role(role)
    if not instance:
        return base
    return f"{base}.{validate_frontier_role_instance(instance)}"


def is_frontier_role_artifact_name(name: str, role: str) -> bool:
    """Whether ``name`` is the base or a validated instance of ``role``."""

    base = validate_frontier_runtime_role(role)
    if name == base:
        return True
    prefix = base + "."
    if not isinstance(name, str) or not name.startswith(prefix):
        return False
    try:
        validate_frontier_role_instance(name[len(prefix) :])
    except ValueError:
        return False
    return True


def frontier_role_artifact_directories(
    calls_root: str | Path,
    role: str,
) -> tuple[Path, ...]:
    """Return bounded direct-child directories for one registered role.

    Runtime call directories are never recursively discovered.  Symlinks and
    malformed near-prefix names are excluded, preventing an inspection action
    from escaping ``agent_calls`` or conflating two role identities.
    """

    base = validate_frontier_runtime_role(role)
    root = Path(calls_root)
    if not root.is_dir() or root.is_symlink():
        return ()
    rows: list[Path] = []
    for root_index, path in enumerate(root.iterdir(), start=1):
        if root_index > MAX_FRONTIER_AGENT_CALL_ROOT_ENTRIES:
            raise ValueError("frontier agent-call root entry ceiling exhausted")
        if (
            is_frontier_role_artifact_name(path.name, base)
            and path.is_dir()
            and not path.is_symlink()
        ):
            rows.append(path)
            if len(rows) > MAX_FRONTIER_ROLE_ARTIFACT_DIRECTORIES:
                raise ValueError("frontier role-directory ceiling exhausted")
    return tuple(sorted(rows, key=lambda path: path.name))


__all__ = [
    "FRONTIER_RUNTIME_ROLES",
    "MAX_FRONTIER_AGENT_CALL_ROOT_ENTRIES",
    "MAX_FRONTIER_ROLE_ARTIFACT_DIRECTORIES",
    "frontier_role_artifact_directories",
    "frontier_role_artifact_name",
    "is_frontier_role_artifact_name",
    "validate_frontier_role_instance",
    "validate_frontier_runtime_role",
]
