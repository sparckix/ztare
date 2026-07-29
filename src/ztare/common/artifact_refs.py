from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Iterable


PROMPT_PACK_FILE_REFS: frozenset[str] = frozenset(
    {
        "ASKS.json",
        "ATTENTION.md",
        "CONTEXT.md",
        "MANIFEST.json",
        "RECORDS.json",
        "TASK.md",
        "WORKBENCH_TOOLS.md",
        "visible_manifest.json",
    }
)

_SHA256_REF_RE = re.compile(r"(?:sha256:)?([0-9a-fA-F]{64})\Z")
_EMBEDDED_SHA256_REF_RE = re.compile(
    r"(?<![0-9a-fA-F])(?:sha256:)?([0-9a-fA-F]{64})(?![0-9a-fA-F])"
)
_TYPED_FRAGMENT_RE = re.compile(r"\A(.+\.(?:jsonl?|md|py|txt)):[^/].*\Z")


def canonical_sha256_ref(value: object) -> str:
    """Normalize bare and prefixed SHA-256 identities to one reference form."""

    match = _SHA256_REF_RE.fullmatch(str(value or "").strip())
    if match is None:
        raise ValueError("value is not a SHA-256 identity")
    return "sha256:" + match.group(1).lower()


def extract_sha256_refs(value: object) -> tuple[str, ...]:
    """Extract canonical digest identities from a scalar typed evidence ref."""

    return tuple(
        dict.fromkeys(
            "sha256:" + match.group(1).lower()
            for match in _EMBEDDED_SHA256_REF_RE.finditer(
                str(value or "").strip()
            )
        )
    )


def normalize_artifact_ref(ref: object) -> str:
    """Return the path-bearing part of an artifact ref."""

    text = str(ref or "").strip().replace("\\", "/")
    if "#" in text:
        text = text.split("#", 1)[0].strip()
    fragment = _TYPED_FRAGMENT_RE.fullmatch(text)
    if fragment is not None:
        text = fragment.group(1)
    return text


def project_ref_requires_resolution(ref: object) -> bool:
    """Whether a local-looking evidence ref must exist under the project root."""

    normalized = normalize_artifact_ref(ref)
    if not normalized or "://" in normalized or normalized.startswith("#"):
        return False
    if normalized.startswith(("/", "../", "./../")):
        return False
    if normalized.startswith(("workspace/", "raw/", "history/")):
        return True
    if normalized in PROMPT_PACK_FILE_REFS:
        return True
    return normalized.endswith((".json", ".jsonl", ".md", ".py", ".txt"))


def resolve_project_artifact_ref(project_dir: str | Path, ref: object) -> Path | None:
    """Resolve a project-relative artifact ref without allowing root escape."""

    normalized = normalize_artifact_ref(ref)
    if not normalized:
        return None
    root = Path(project_dir).resolve()
    candidate = (root / normalized).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate


def project_artifact_ref_exists(project_dir: str | Path, ref: object) -> bool:
    path = resolve_project_artifact_ref(project_dir, ref)
    return bool(path and path.is_file())


def missing_project_artifact_refs(
    project_dir: str | Path,
    refs: Iterable[object],
) -> tuple[str, ...]:
    missing: list[str] = []
    for ref in refs:
        normalized = normalize_artifact_ref(ref)
        if (
            project_ref_requires_resolution(normalized)
            and not project_artifact_ref_exists(project_dir, normalized)
        ):
            missing.append(normalized)
    return tuple(dict.fromkeys(missing))


ARTIFACT_REF_KEYS: frozenset[str] = frozenset(
    {
        "evidence_ref",
        "evidence_refs",
        "evidence_analysis_ref",
        "evidence_analysis_refs",
        "input_ref",
        "input_refs",
        "kernel_receipt_ref",
        "new_evidence_ref",
        "new_evidence_refs",
        "output_ref",
        "ref",
        "receipt_ref",
        "receipt_refs",
        "source_ref",
        "source_refs",
        "visible_receipt_ref",
        "visible_receipt_refs",
    }
)


def collect_artifact_refs(payload: object) -> tuple[str, ...]:
    """Collect local artifact refs from a structured receipt payload."""

    refs: list[str] = []

    def visit(value: object, *, key: str = "") -> None:
        if isinstance(value, Mapping):
            for child_key, child_value in value.items():
                visit(child_value, key=str(child_key))
            return
        if isinstance(value, list | tuple):
            if key in ARTIFACT_REF_KEYS or key.endswith("_refs"):
                for item in value:
                    if isinstance(item, (Mapping, list, tuple)):
                        # A ref collection may use scalar paths or typed ref
                        # objects carrying status/authority alongside ``ref``.
                        # Preserve the object category and traverse it; string
                        # coercion manufactures a path from its repr.
                        visit(item)
                    else:
                        text = str(item or "").strip()
                        if text:
                            refs.append(text)
                return
            for item in value:
                visit(item, key=key)
            return
        if key in ARTIFACT_REF_KEYS or key.endswith("_ref"):
            text = str(value or "").strip()
            if text:
                refs.append(text)

    visit(payload)
    return tuple(dict.fromkeys(refs))


def collect_artifact_refs_from_text(text: str) -> tuple[str, ...]:
    """Collect artifact refs from structured text, preferring JSON payloads."""

    stripped = (text or "").strip()
    if not stripped:
        return ()
    try:
        return collect_artifact_refs(json.loads(stripped))
    except json.JSONDecodeError:
        pass
    refs = re.findall(r"(?<![A-Za-z0-9_./-])(?:workspace|raw|history)/[A-Za-z0-9_./:+-]+", stripped)
    return tuple(dict.fromkeys(ref.rstrip(".,);]}'\"") for ref in refs))


def visible_workbench_authority_project(workbench: str | Path, *, fallback: str | Path) -> Path:
    """Resolve the authority project declared by a visible workbench pack."""

    workbench_path = Path(workbench)
    fallback_path = Path(fallback)
    manifest_path = workbench_path / "MANIFEST.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback_path
    if not isinstance(manifest, dict):
        return fallback_path
    raw = str(manifest.get("authority_project_path") or "").strip()
    if not raw:
        return fallback_path
    project = Path(raw).expanduser()
    if not project.is_absolute():
        project = (fallback_path / project).resolve()
    return project.resolve()
