from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ztare.common.patch_base_identity import (
    patch_base_fields_from_source,
    resolve_patch_base_ref,
    verify_patch_base_digest,
)
from ztare.common.worldmodel_carrier_purity import carrier_contract_error


def load_candidate_memory(project: str | Path) -> list[dict[str, Any]]:
    path = Path(project) / "workspace" / "candidate_memory.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    records = payload.get("records") if isinstance(payload, dict) else None
    if not isinstance(records, list):
        return []
    return [rec for rec in records if isinstance(rec, dict)]


def admissible_candidate_memory_records(
    project: str | Path,
    records: list[dict[str, Any]] | None = None,
    *,
    source_types: set[str] | None = None,
    require_submission_source: bool = False,
) -> list[dict[str, Any]]:
    """Candidate-memory records selectable by current worldmodel contracts.

    Historical candidate memory is an audit trail. Reader surfaces may only use
    a row as an active prior when the stored carrier source still satisfies the
    current transition-function contract.
    """
    root = Path(project)
    rows = records if records is not None else load_candidate_memory(root)
    allowed = source_types or {"full_survivor", "deterministic_near_miss"}
    out: list[dict[str, Any]] = []
    for rec in rows:
        if rec.get("source_type") not in allowed:
            continue
        if require_submission_source and not _is_submission_source_ref(rec):
            continue
        source = candidate_memory_source(root, rec)
        if source and _carrier_chain_contract_error(root, source):
            continue
        out.append(rec)
    return out


def candidate_memory_contract_error(project: str | Path, rec: dict[str, Any]) -> str | None:
    source = candidate_memory_source(project, rec)
    if not source:
        return "candidate memory source unavailable"
    return _carrier_chain_contract_error(Path(project), source)


def candidate_memory_source(project: str | Path, rec: dict[str, Any]) -> str:
    root = Path(project)
    rel = str(rec.get("submission") or "").strip()
    candidates: list[Path] = []
    if rel:
        candidates.append(root / rel)
        candidates.append(root / "workspace" / rel)
    for path in candidates:
        try:
            if path.exists() and path.is_file():
                return path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
    return str(rec.get("source_excerpt") or "")


def _is_submission_source_ref(rec: dict[str, Any]) -> bool:
    ref = str(rec.get("submission") or "").strip().replace("\\", "/")
    return ref.startswith("workspace/submissions/") and ".." not in Path(ref).parts


def _carrier_chain_contract_error(
    project: Path,
    source: str,
    *,
    _seen: set[Path] | None = None,
) -> str | None:
    err = carrier_contract_error(source)
    if err:
        return err
    fields = patch_base_fields_from_source(source)
    if not fields:
        return None
    ref, expected_sha = fields
    try:
        path = resolve_patch_base_ref(project, ref)
    except ValueError as exc:
        return str(exc)
    if _seen is None:
        _seen = set()
    if path in _seen:
        return "PATCH_BASE chain cycle."
    _seen.add(path)
    try:
        data = path.read_bytes()
        nested = data.decode("utf-8", errors="ignore")
    except Exception as exc:  # noqa: BLE001
        return f"PATCH_BASE source_ref unreadable: {exc}"
    try:
        verify_patch_base_digest(path, expected_sha, allow_legacy_prefix=True)
    except ValueError as exc:
        return str(exc)
    return _carrier_chain_contract_error(project, nested, _seen=_seen)
