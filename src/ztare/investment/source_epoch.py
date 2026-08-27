"""Content-bound publication epoch for current investment observations."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from ztare.common.equivariance import stable_sha256

from .observation_index import observation_source_sha256


SOURCE_EPOCH_SCHEMA = "jaggedthoughts-public-source-epoch-v1"
DERIVATION_COMPILER_VERSION = "jaggedthoughts-source-derivation-v1"
CACHED_RECEIPT_PROJECTION = "cached-yahoo-receipt-projection"
_DIGEST_CACHE: dict[tuple[str, int, int, int], str] = {}


def _read_mapping(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON artifact must be an object: {path}")
    return payload


def _relative(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as error:
        raise ValueError(f"source-epoch artifact escapes workspace: {path}") from error


def file_sha256(path: Path) -> str:
    """Hash a file, caching only while its filesystem identity is unchanged."""
    before = path.stat()
    key = (str(path.resolve()), before.st_ino, before.st_size, before.st_mtime_ns)
    cached = _DIGEST_CACHE.get(key)
    if cached:
        return cached
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    after = path.stat()
    if (before.st_ino, before.st_size, before.st_mtime_ns) != (
        after.st_ino, after.st_size, after.st_mtime_ns,
    ):
        raise RuntimeError(f"source-epoch artifact changed while hashing: {path}")
    value = digest.hexdigest()
    _DIGEST_CACHE[key] = value
    return value


def derivation_identity(
    signal_definitions: object, *, derive_metrics: bool, metric_universe_sha256: str,
    pipeline_id: str = "source-refresh",
) -> dict[str, Any]:
    body = {
        "compiler_version": DERIVATION_COMPILER_VERSION,
        "pipeline_id": pipeline_id,
        "derive_metrics": bool(derive_metrics),
        "signal_definitions_sha256": stable_sha256(signal_definitions),
        "metric_universe_sha256": str(metric_universe_sha256),
    }
    return {**body, "derivation_sha256": stable_sha256(body)}


def compile_source_epoch(
    workspace: Path,
    *,
    source_run_path: Path,
    projection_path: Path,
    observations_path: Path,
    receipt_heads_path: Path,
    source_manifest_path: Path,
    derivation: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind the completed source run to every artifact used as current evidence."""
    root = workspace.resolve()
    source_run = _read_mapping(source_run_path)
    projection = _read_mapping(projection_path)
    receipt_heads = _read_mapping(receipt_heads_path)
    source_manifest = source_manifest_path.read_bytes()
    run_body = dict(source_run)
    declared_run_hash = str(run_body.pop("run_sha256", ""))
    if not declared_run_hash or stable_sha256(run_body) != declared_run_hash:
        raise ValueError("source run hash is invalid")
    if projection.get("as_of") != source_run.get("as_of"):
        raise ValueError("source run and current projection have different as_of epochs")
    if (
        int(projection.get("observation_count") or -1)
        != int(source_run.get("observation_count") or -2)
        and derivation.get("pipeline_id") != CACHED_RECEIPT_PROJECTION
    ):
        raise ValueError("source run and current projection have different observation counts")
    derivation_body = dict(derivation)
    declared_derivation_hash = str(derivation_body.pop("derivation_sha256", ""))
    if not declared_derivation_hash or stable_sha256(derivation_body) != declared_derivation_hash:
        raise ValueError("derivation identity hash is invalid")
    body = {
        "schema": SOURCE_EPOCH_SCHEMA,
        "as_of": source_run["as_of"],
        "published_at": source_run["retrieved_at"],
        "source_run": {
            "path": _relative(root, source_run_path), "sha256": declared_run_hash,
        },
        "latest_projection": {
            "path": _relative(root, projection_path), "sha256": stable_sha256(projection),
        },
        "observation_store": {
            "path": _relative(root, observations_path),
            "sha256": observation_source_sha256(observations_path),
            "byte_count": observations_path.stat().st_size,
        },
        "receipt_heads": {
            "path": _relative(root, receipt_heads_path), "sha256": stable_sha256(receipt_heads),
        },
        "source_manifest": {
            "path": _relative(root, source_manifest_path),
            "sha256": hashlib.sha256(source_manifest).hexdigest(),
        },
        "derivation_identity": dict(derivation),
        "historical_store": "data/observations.csv",
        "paper_policy_authority": False,
        "capital_authority": False,
    }
    return {**body, "source_epoch_sha256": stable_sha256(body)}


def validate_source_epoch(workspace: Path, epoch_path: Path) -> dict[str, Any]:
    """Load an epoch and reject any artifact drift or mixed-run projection."""
    root = workspace.resolve()
    epoch = _read_mapping(epoch_path)
    if epoch.get("schema") != SOURCE_EPOCH_SCHEMA:
        raise ValueError("unsupported source epoch schema")
    body = dict(epoch)
    declared_epoch_hash = str(body.pop("source_epoch_sha256", ""))
    if not declared_epoch_hash or stable_sha256(body) != declared_epoch_hash:
        raise ValueError("source epoch hash is invalid")

    def artifact(name: str) -> tuple[Path, str]:
        row = epoch.get(name)
        if not isinstance(row, Mapping):
            raise ValueError(f"source epoch is missing {name}")
        path = (root / str(row.get("path") or "")).resolve()
        _relative(root, path)
        return path, str(row.get("sha256") or "")

    run_path, run_hash = artifact("source_run")
    projection_path, projection_hash = artifact("latest_projection")
    store_path, store_hash = artifact("observation_store")
    heads_path, heads_hash = artifact("receipt_heads")
    manifest_path, manifest_hash = artifact("source_manifest")
    source_run = _read_mapping(run_path)
    projection = _read_mapping(projection_path)
    run_body = dict(source_run)
    if run_body.pop("run_sha256", None) != run_hash or stable_sha256(run_body) != run_hash:
        raise ValueError("source epoch source-run binding is invalid")
    if stable_sha256(projection) != projection_hash:
        raise ValueError("source epoch projection binding is invalid")
    if observation_source_sha256(store_path) != store_hash:
        raise ValueError("source epoch observation-store binding is invalid")
    if stable_sha256(_read_mapping(heads_path)) != heads_hash:
        raise ValueError("source epoch receipt-head binding is invalid")
    if hashlib.sha256(manifest_path.read_bytes()).hexdigest() != manifest_hash:
        raise ValueError("source epoch source-manifest binding is invalid")
    derivation = dict(epoch.get("derivation_identity") or {})
    if projection.get("as_of") != source_run.get("as_of") or (
        int(projection.get("observation_count") or -1)
        != int(source_run.get("observation_count") or -2)
        and derivation.get("pipeline_id") != CACHED_RECEIPT_PROJECTION
    ):
        raise ValueError("source epoch contains a mixed-run projection")
    declared_derivation_hash = str(derivation.pop("derivation_sha256", ""))
    if not declared_derivation_hash or stable_sha256(derivation) != declared_derivation_hash:
        raise ValueError("source epoch derivation binding is invalid")
    return {"manifest": epoch, "source_run": source_run, "projection": projection}


def current_source_epoch(workspace: Path) -> dict[str, Any] | None:
    """Return the canonical epoch, with a legacy search only before migration."""
    root = workspace.resolve()
    head = root / "data" / "latest_source_epoch.json"
    if head.is_file():
        return validate_source_epoch(root, head)["manifest"]
    candidates = tuple(root.rglob("latest_source_epoch.json"))
    if not candidates:
        return None
    valid = []
    for path in candidates:
        try:
            valid.append(validate_source_epoch(root, path)["manifest"])
        except (OSError, TypeError, ValueError, RuntimeError, json.JSONDecodeError):
            continue
    if not valid:
        raise ValueError("no published source epoch matches the current observation store")
    return max(valid, key=lambda row: (
        str(row.get("published_at") or ""), str(row.get("source_epoch_sha256") or ""),
    ))
