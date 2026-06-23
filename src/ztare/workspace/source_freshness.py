"""Freshness checks for source-bound workspace artifacts."""
from __future__ import annotations

from pathlib import Path
from typing import Any


SOURCE_BINDING_CONTRACT_SCHEMA = "ztare-artifact-source-binding-contract-v1"


def raw_relative_path(raw_value: Any, *, project_dir: Path, repo: Path) -> str:
    """Normalize an artifact source path to a project raw-relative path."""
    raw = str(raw_value or "").strip().replace("\\", "/")
    if not raw:
        return ""
    raw_dir = project_dir / "raw"
    project_prefix = f"projects/{project_dir.name}/raw/"
    if raw.startswith(project_prefix):
        return raw[len(project_prefix):]
    if raw.startswith("raw/"):
        return raw[len("raw/"):]
    path = Path(raw)
    candidates = [path] if path.is_absolute() else [repo / path, raw_dir / path]
    for candidate in candidates:
        try:
            return candidate.resolve().relative_to(raw_dir.resolve()).as_posix()
        except ValueError:
            pass
    return raw


def source_binding_contract(
    *,
    artifact_name: str,
    checked: bool,
    verified: bool,
    status: str,
    current_source_count: int,
    artifact_source_count: int,
) -> dict[str, Any]:
    """Return the kernel-entry contract for an artifact/source binding row.

    ``ok`` on the legacy freshness payload means "not proven stale." This
    contract is stricter: kernel entry needs byte/hash-verified bindings, not
    skipped or count-only diagnostics.
    """
    status = str(status or "").strip() or "unknown"
    required = current_source_count > 0
    if verified:
        contract_status = "verified_fresh"
        blockers: list[str] = []
    elif not required:
        contract_status = "not_applicable_no_current_sources"
        blockers = []
    elif not checked:
        contract_status = status
        blockers = [status]
    else:
        contract_status = status
        blockers = [status]
    contract_ok = bool(verified or not required)
    kernel_entry_ok = bool(verified) if required else True
    return {
        "schema": SOURCE_BINDING_CONTRACT_SCHEMA,
        "artifact": artifact_name,
        "status": contract_status,
        "contract_ok": contract_ok,
        "kernel_entry_ok": kernel_entry_ok,
        "required": required,
        "checked": checked,
        "verified": verified,
        "current_source_count": current_source_count,
        "artifact_source_count": artifact_source_count,
        "blockers": blockers if not contract_ok else [],
    }


def source_binding_contract_blocks_kernel(freshness: dict[str, Any]) -> bool:
    contract = freshness.get("source_binding_contract")
    if isinstance(contract, dict):
        return not bool(contract.get("kernel_entry_ok"))
    return not bool(freshness.get("verified"))


def artifact_source_freshness(
    *,
    source_preflight: dict[str, Any],
    artifact_sources: Any,
    artifact_name: str,
    project_dir: Path,
    repo: Path,
) -> dict[str, Any]:
    """Compare artifact source rows against current source-preflight rows."""
    current_rows = [
        row
        for row in source_preflight.get("sources", [])
        if isinstance(row, dict) and row.get("relative_raw_path")
    ]
    artifact_rows = [row for row in artifact_sources or [] if isinstance(row, dict)]
    if not current_rows:
        status = "skipped_no_current_sources"
        verified = False
        contract = source_binding_contract(
            artifact_name=artifact_name,
            checked=False,
            verified=verified,
            status=status,
            current_source_count=0,
            artifact_source_count=len(artifact_rows),
        )
        return {
            "checked": False,
            "ok": True,
            "verified": verified,
            "status": status,
            "contract_ok": contract["contract_ok"],
            "kernel_entry_ok": contract["kernel_entry_ok"],
            "source_binding_contract": contract,
            "artifact": artifact_name,
            "current_source_count": 0,
            "artifact_source_count": len(artifact_rows),
        }
    if not artifact_rows:
        status = "unverified_no_artifact_sources"
        verified = False
        contract = source_binding_contract(
            artifact_name=artifact_name,
            checked=False,
            verified=verified,
            status=status,
            current_source_count=len(current_rows),
            artifact_source_count=0,
        )
        return {
            "checked": False,
            "ok": True,
            "verified": verified,
            "status": status,
            "contract_ok": contract["contract_ok"],
            "kernel_entry_ok": contract["kernel_entry_ok"],
            "source_binding_contract": contract,
            "artifact": artifact_name,
            "current_source_count": len(current_rows),
            "artifact_source_count": 0,
        }

    current_by_path = {str(row["relative_raw_path"]): row for row in current_rows}
    artifact_by_path = {
        raw_relative_path(raw_path, project_dir=project_dir, repo=repo): row
        for row in artifact_rows
        if (raw_path := (row.get("path") or row.get("relative_raw_path")))
    }
    missing_from_artifact = sorted(set(current_by_path) - set(artifact_by_path))
    deleted_from_raw = sorted(set(artifact_by_path) - set(current_by_path))
    hash_mismatches: list[str] = []
    source_type_mismatches: list[str] = []
    unverifiable_paths: list[str] = []

    for path, current in sorted(current_by_path.items()):
        artifact = artifact_by_path.get(path)
        if artifact is None:
            continue
        current_hash = str(current.get("sha256") or "").strip()
        artifact_hash = str(
            artifact.get("sha256") or artifact.get("full_sha256") or ""
        ).strip()
        if not current_hash or not artifact_hash:
            unverifiable_paths.append(path)
        elif current_hash != artifact_hash:
            hash_mismatches.append(path)
        current_type = str(current.get("source_type") or "").strip()
        artifact_type = str(artifact.get("source_type") or "").strip()
        if current_type and artifact_type and current_type != artifact_type:
            source_type_mismatches.append(path)

    stale = bool(
        missing_from_artifact
        or deleted_from_raw
        or hash_mismatches
        or source_type_mismatches
    )
    verified = not stale and not unverifiable_paths
    if stale:
        status = "stale"
    elif verified:
        status = "fresh"
    else:
        status = "unverified_missing_hash"
    contract = source_binding_contract(
        artifact_name=artifact_name,
        checked=True,
        verified=verified,
        status=status,
        current_source_count=len(current_rows),
        artifact_source_count=len(artifact_rows),
    )
    return {
        "checked": True,
        "ok": not stale,
        "verified": verified,
        "status": status,
        "contract_ok": contract["contract_ok"],
        "kernel_entry_ok": contract["kernel_entry_ok"],
        "source_binding_contract": contract,
        "artifact": artifact_name,
        "current_source_count": len(current_rows),
        "artifact_source_count": len(artifact_rows),
        "missing_from_artifact": missing_from_artifact,
        "deleted_from_raw": deleted_from_raw,
        "hash_mismatches": hash_mismatches,
        "source_type_mismatches": source_type_mismatches,
        "unverifiable_paths": unverifiable_paths,
    }
