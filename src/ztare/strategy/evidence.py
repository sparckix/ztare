"""Source-bound evidence manifests for JaggedThoughts profiles."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from ztare.common.content_identity import content_sha256
from ztare.scenarios.evidence_binding import EvidenceBinding, bind_evidence


class StrategyEvidenceError(ValueError):
    """Raised when a strategy profile cannot bind its declared evidence."""


@dataclass(frozen=True, slots=True)
class StrategySource:
    source_id: str
    relative_path: str
    content_sha256: str
    fetched_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "relative_path": self.relative_path,
            "content_sha256": self.content_sha256,
            "fetched_at": self.fetched_at,
        }


@dataclass(frozen=True, slots=True)
class StrategyEvidence:
    evidence_id: str
    binding: EvidenceBinding

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "source_id": self.binding.source_id,
            "content_sha256": self.binding.content_sha256,
            "excerpt": self.binding.excerpt,
            "fetched_at": self.binding.fetched_at,
        }


@dataclass(frozen=True, slots=True)
class StrategyEvidenceManifest:
    sources: tuple[StrategySource, ...]
    evidence: tuple[StrategyEvidence, ...]
    manifest_sha256: str

    @property
    def evidence_ids(self) -> frozenset[str]:
        return frozenset(item.evidence_id for item in self.evidence)

    def require_refs(self, refs: Iterable[str], *, context: str) -> None:
        missing = sorted(set(refs) - self.evidence_ids)
        if missing:
            raise StrategyEvidenceError(
                f"{context} references unbound evidence IDs: {missing}"
            )

    def by_id(self) -> dict[str, StrategyEvidence]:
        return {item.evidence_id: item for item in self.evidence}

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest_sha256": self.manifest_sha256,
            "sources": [source.to_dict() for source in self.sources],
            "evidence": [item.to_dict() for item in self.evidence],
        }


def _rows(value: Any, label: str) -> tuple[Mapping[str, Any], ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise StrategyEvidenceError(f"{label} must be a list")
    rows: list[Mapping[str, Any]] = []
    for row in value:
        if not isinstance(row, Mapping):
            raise StrategyEvidenceError(f"{label} rows must be mappings")
        rows.append(row)
    return tuple(rows)


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StrategyEvidenceError(f"{label} must be a non-empty string")
    return value.strip()


def _resolve_source(root: Path, relative_path: str) -> Path:
    declared = Path(relative_path)
    if declared.is_absolute():
        raise StrategyEvidenceError("strategy source paths must be relative")
    resolved_root = root.resolve()
    resolved = (resolved_root / declared).resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as error:
        raise StrategyEvidenceError(
            f"strategy source escapes the profile directory: {relative_path}"
        ) from error
    if not resolved.is_file():
        raise StrategyEvidenceError(
            f"strategy source does not exist: {relative_path}"
        )
    return resolved


def compile_evidence_manifest(
    payload: Mapping[str, Any],
    *,
    source_root: Path | None,
) -> StrategyEvidenceManifest:
    """Bind profile excerpts to local source bytes and mint a stable manifest."""
    source_rows = _rows(payload.get("sources"), "sources")
    evidence_rows = _rows(payload.get("evidence"), "evidence")
    if (source_rows or evidence_rows) and source_root is None:
        raise StrategyEvidenceError(
            "source-bound profiles require a source_root or compile_profile_file"
        )
    if not source_rows and evidence_rows:
        raise StrategyEvidenceError("evidence rows require declared sources")

    source_root = source_root or Path(".")
    sources: list[StrategySource] = []
    content_by_source: dict[str, str] = {}
    for row in source_rows:
        source_id = _text(row.get("id"), "source.id")
        if source_id in content_by_source:
            raise StrategyEvidenceError(f"duplicate strategy source: {source_id}")
        relative_path = _text(row.get("path"), "source.path")
        path = _resolve_source(source_root, relative_path)
        content = path.read_text(encoding="utf-8")
        digest = content_sha256(content)
        declared_digest = str(row.get("sha256") or "").strip()
        if declared_digest and declared_digest != digest:
            raise StrategyEvidenceError(
                f"source hash mismatch for {source_id}: {relative_path}"
            )
        fetched_at = _text(row.get("fetched_at"), "source.fetched_at")
        sources.append(StrategySource(
            source_id=source_id,
            relative_path=relative_path,
            content_sha256=digest,
            fetched_at=fetched_at,
        ))
        content_by_source[source_id] = content

    evidence: list[StrategyEvidence] = []
    seen_evidence: set[str] = set()
    for row in evidence_rows:
        evidence_id = _text(row.get("id"), "evidence.id")
        if evidence_id in seen_evidence:
            raise StrategyEvidenceError(
                f"duplicate strategy evidence: {evidence_id}"
            )
        source_id = _text(row.get("source_id"), "evidence.source_id")
        content = content_by_source.get(source_id)
        if content is None:
            raise StrategyEvidenceError(
                f"evidence {evidence_id} references unknown source {source_id}"
            )
        excerpt = _text(row.get("excerpt"), "evidence.excerpt")
        source = next(item for item in sources if item.source_id == source_id)
        binding = bind_evidence(
            source_id,
            content,
            excerpt,
            fetched_at=source.fetched_at,
        )
        if binding is None:
            raise StrategyEvidenceError(
                f"evidence excerpt is absent from source bytes: {evidence_id}"
            )
        evidence.append(StrategyEvidence(evidence_id, binding))
        seen_evidence.add(evidence_id)

    sources_tuple = tuple(sorted(sources, key=lambda item: item.source_id))
    evidence_tuple = tuple(sorted(evidence, key=lambda item: item.evidence_id))
    manifest_sha = content_sha256({
        "sources": [source.to_dict() for source in sources_tuple],
        "evidence": [item.to_dict() for item in evidence_tuple],
    })
    return StrategyEvidenceManifest(
        sources=sources_tuple,
        evidence=evidence_tuple,
        manifest_sha256=manifest_sha,
    )
