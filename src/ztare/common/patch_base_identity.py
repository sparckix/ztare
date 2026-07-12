from __future__ import annotations

import ast
import hashlib
from pathlib import Path
from typing import Any


def resolve_patch_base_ref(project_dir: str | Path, ref: object) -> Path:
    if not isinstance(ref, str) or not ref.strip():
        raise ValueError("PATCH_BASE requires non-empty source_ref/path.")
    raw = Path(ref)
    if raw.is_absolute() or ".." in raw.parts:
        raise ValueError("PATCH_BASE source_ref must be a project-relative path.")
    if len(raw.parts) < 3 or raw.parts[:2] != ("workspace", "submissions"):
        raise ValueError(
            "PATCH_BASE source_ref must point to an immutable "
            "workspace/submissions artifact."
        )
    project = Path(project_dir)
    path = (project / raw).resolve()
    root = project.resolve()
    if root != path and root not in path.parents:
        raise ValueError("PATCH_BASE source_ref escapes project_dir.")
    if not path.is_file():
        raise ValueError(f"PATCH_BASE source_ref not found: {ref}")
    return path


def verify_patch_base_digest(
    path: Path,
    expected: object,
    *,
    allow_legacy_prefix: bool = False,
) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if expected is None or not str(expected).strip():
        raise ValueError("PATCH_BASE requires full sha256 for referenced artifact.")
    declared = str(expected).strip().lower()
    if _is_full_digest(declared):
        if digest != declared:
            raise ValueError("PATCH_BASE sha256 does not match referenced artifact.")
        return digest
    if allow_legacy_prefix and _is_legacy_prefix(declared) and digest.startswith(declared):
        return digest
    raise ValueError("PATCH_BASE sha256 must be the full 64-hex digest.")


def patch_base_fields_from_source(source: str) -> tuple[str, object] | None:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        names = [target.id for target in node.targets if isinstance(target, ast.Name)]
        if "PATCH_BASE" in names and isinstance(node.value, ast.Dict):
            try:
                spec = ast.literal_eval(node.value)
            except Exception:  # noqa: BLE001
                return None
            if isinstance(spec, dict):
                return _fields_from_mapping(spec)
        if "PATCH_BASE_REF" in names or "PATCH_BASE_PATH" in names:
            try:
                ref = ast.literal_eval(node.value)
            except Exception:  # noqa: BLE001
                return None
            sha: object = None
            for sibling in tree.body:
                if not isinstance(sibling, ast.Assign):
                    continue
                sibling_names = [
                    target.id for target in sibling.targets if isinstance(target, ast.Name)
                ]
                if not (
                    "PATCH_BASE_SHA256" in sibling_names
                    or "PATCH_BASE_SHA" in sibling_names
                    or "PATCH_BASE_SHA256_PREFIX" in sibling_names
                ):
                    continue
                try:
                    sha = ast.literal_eval(sibling.value)
                except Exception:  # noqa: BLE001
                    sha = None
                break
            return (str(ref), sha) if ref else None
    return None


def patch_base_fields_from_namespace(namespace: dict[str, Any]) -> tuple[str, object] | None:
    spec = namespace.get("PATCH_BASE")
    if isinstance(spec, dict):
        return _fields_from_mapping(spec)
    ref = namespace.get("PATCH_BASE_REF") or namespace.get("PATCH_BASE_PATH")
    if ref:
        return str(ref), (
            namespace.get("PATCH_BASE_SHA256")
            or namespace.get("PATCH_BASE_SHA256_PREFIX")
            or namespace.get("PATCH_BASE_SHA")
        )
    return None


def _fields_from_mapping(spec: dict[str, Any]) -> tuple[str, object] | None:
    ref = (
        spec.get("source_ref")
        or spec.get("path")
        or spec.get("submission")
        or spec.get("artifact")
    )
    sha = (
        spec.get("sha256")
        or spec.get("sha256_prefix")
        or spec.get("sha")
        or spec.get("source_sha")
    )
    return (str(ref), sha) if ref else None


def _is_full_digest(value: str) -> bool:
    return len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


def _is_legacy_prefix(value: str) -> bool:
    return 12 <= len(value) < 64 and all(ch in "0123456789abcdef" for ch in value)
