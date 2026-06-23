"""Bind rendered evidence artifacts to a current compile provenance file."""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from ztare.common.paths import REPO_ROOT
from ztare.workspace.compile_evidence import (
    read_json,
    resolve_project_dir,
    sha256_file,
    write_json,
)


SCHEMA = "ztare-evidence-output-binding-receipt-v1"
RECEIPT_FILENAME = "evidence_output_binding_receipt.json"
PRODUCER = "ztare.workspace.evidence_output_binding::write_evidence_output_binding_receipt"


def _rel(path: Path, repo: Path = REPO_ROOT) -> str:
    try:
        return path.resolve().relative_to(repo.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _resolve_artifact_path(raw_path: str, *, project_dir: Path, repo: Path) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    project_candidate = project_dir / path
    if project_candidate.exists():
        return project_candidate
    return repo / path


def _first_existing_provenance(project_dir: Path) -> Path:
    for candidate in (
        project_dir / "compiled_evidence_provenance.json",
        project_dir / "workspace" / "evidence_compile_provenance.json",
    ):
        if candidate.exists():
            return candidate
    raise SystemExit(
        "cannot bind evidence outputs: compile provenance is missing; "
        "run evidence prepare first"
    )


def _artifact_specs(provenance: dict[str, Any]) -> list[tuple[str, str, str, bool]]:
    return [
        ("evidence_output", "output_path", "evidence.txt", True),
        ("audit_copy", "audit_copy_path", "compiled_evidence.txt", False),
        ("packet_output", "packet_output_path", "compiled_evidence_packet.json", False),
    ]


def build_evidence_output_binding_receipt(
    *,
    project_dir: Path,
    provenance_path: Path | None = None,
    repo: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Return a receipt that freezes current rendered evidence bytes.

    This is a no-LLM compatibility receipt for older compile manifests that
    tracked source provenance but did not hash the rendered outputs. It does not
    claim that evidence was regenerated; it only binds current artifact bytes to
    the current compile provenance file hash.
    """

    project = project_dir.name
    provenance = provenance_path or _first_existing_provenance(project_dir)
    if not provenance.is_absolute():
        provenance = repo / provenance
    provenance_payload = read_json(provenance)
    artifacts: list[dict[str, Any]] = []
    for artifact_id, path_key, fallback, required in _artifact_specs(provenance_payload):
        raw_path = str(provenance_payload.get(path_key) or fallback).strip()
        artifact_path = _resolve_artifact_path(
            raw_path,
            project_dir=project_dir,
            repo=repo,
        )
        if not artifact_path.exists():
            if required:
                raise SystemExit(
                    f"cannot bind evidence outputs: required artifact missing: "
                    f"{_rel(artifact_path, repo)}"
                )
            continue
        artifacts.append(
            {
                "artifact_id": artifact_id,
                "path": _rel(artifact_path, repo),
                "sha256": sha256_file(artifact_path),
            }
        )
    if not any(row.get("artifact_id") == "evidence_output" for row in artifacts):
        raise SystemExit("cannot bind evidence outputs: evidence_output artifact absent")
    return {
        "schema": SCHEMA,
        "status": "bound",
        "producer": PRODUCER,
        "project": project,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "llm_calls": False,
        "binding_mode": "current_artifact_freeze",
        "provenance_path": _rel(provenance, repo),
        "provenance_sha256": sha256_file(provenance),
        "artifacts": artifacts,
        "limitations": [
            "does_not_recompile_evidence",
            "does_not_prove_original_compile_time_output",
            "does_not_change_compile_provenance_sources",
        ],
    }


def verify_evidence_output_binding_receipt(
    *,
    receipt: dict[str, Any],
    receipt_path: Path,
    project_dir: Path,
    repo: Path = REPO_ROOT,
) -> dict[str, Any]:
    if not receipt:
        return {
            "exists": False,
            "path": _rel(receipt_path, repo),
            "status": "missing",
            "verified": False,
            "artifact_bindings": [],
        }
    artifact_bindings: list[dict[str, Any]] = []
    schema_ok = receipt.get("schema") == SCHEMA
    status_ok = receipt.get("status") == "bound"
    project_verified = str(receipt.get("project") or "") == project_dir.name
    raw_provenance_path = str(receipt.get("provenance_path") or "").strip()
    provenance_path = (
        _resolve_artifact_path(raw_provenance_path, project_dir=project_dir, repo=repo)
        if raw_provenance_path
        else project_dir / "compiled_evidence_provenance.json"
    )
    current_provenance_sha = sha256_file(provenance_path) if provenance_path.exists() else None
    expected_provenance_sha = str(receipt.get("provenance_sha256") or "").strip()
    provenance_verified = (
        bool(current_provenance_sha)
        and bool(expected_provenance_sha)
        and current_provenance_sha == expected_provenance_sha
    )
    rows = receipt.get("artifacts")
    if not isinstance(rows, list):
        rows = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        artifact_id = str(row.get("artifact_id") or "").strip()
        raw_path = str(row.get("path") or "").strip()
        expected_sha = str(row.get("sha256") or "").strip()
        artifact_path = _resolve_artifact_path(
            raw_path,
            project_dir=project_dir,
            repo=repo,
        )
        current_sha = sha256_file(artifact_path) if artifact_path.exists() else None
        verified = bool(current_sha) and bool(expected_sha) and current_sha == expected_sha
        artifact_bindings.append(
            {
                "artifact_id": artifact_id,
                "path": _rel(artifact_path, repo),
                "current_sha256": current_sha,
                "expected_sha256": expected_sha or None,
                "verified": verified,
                "hash_mismatch": bool(current_sha and expected_sha and current_sha != expected_sha),
                "status": (
                    "fresh"
                    if verified
                    else ("missing_artifact" if current_sha is None else "stale")
                ),
            }
        )
    has_primary = any(
        row.get("artifact_id") == "evidence_output" for row in artifact_bindings
    )
    artifact_verified = bool(artifact_bindings) and all(
        bool(row.get("verified")) for row in artifact_bindings
    )
    verified = bool(
        schema_ok
        and status_ok
        and project_verified
        and provenance_verified
        and has_primary
        and artifact_verified
    )
    if verified:
        status = "fresh"
    elif not schema_ok or not status_ok or not project_verified:
        status = "invalid"
    elif not provenance_verified:
        status = "stale_provenance"
    elif not has_primary:
        status = "missing_primary_artifact"
    elif any(row.get("status") == "missing_artifact" for row in artifact_bindings):
        status = "stale_missing_artifact"
    elif any(row.get("hash_mismatch") is True for row in artifact_bindings):
        status = "stale_artifact_hash"
    else:
        status = "unverified"
    return {
        "exists": True,
        "path": _rel(receipt_path, repo),
        "schema": receipt.get("schema"),
        "status": status,
        "verified": verified,
        "producer": receipt.get("producer"),
        "llm_calls": receipt.get("llm_calls"),
        "binding_mode": receipt.get("binding_mode"),
        "project": receipt.get("project"),
        "project_verified": project_verified,
        "provenance_path": _rel(provenance_path, repo),
        "provenance_current_sha256": current_provenance_sha,
        "provenance_expected_sha256": expected_provenance_sha or None,
        "provenance_verified": provenance_verified,
        "artifact_bindings": artifact_bindings,
        "stale_artifacts": [
            str(row.get("artifact_id"))
            for row in artifact_bindings
            if row.get("hash_mismatch") is True
            or row.get("status") == "missing_artifact"
        ],
    }


def write_evidence_output_binding_receipt(
    *,
    project_dir: Path,
    provenance_path: Path | None = None,
    receipt_path: Path | None = None,
    repo: Path = REPO_ROOT,
) -> dict[str, Any]:
    receipt = build_evidence_output_binding_receipt(
        project_dir=project_dir,
        provenance_path=provenance_path,
        repo=repo,
    )
    output = receipt_path or project_dir / "workspace" / RECEIPT_FILENAME
    output.parent.mkdir(parents=True, exist_ok=True)
    write_json(output, receipt)
    return {"path": _rel(output, repo), "receipt": receipt}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bind current rendered evidence outputs without an LLM call.",
    )
    parser.add_argument("--project", required=True)
    parser.add_argument("--provenance")
    parser.add_argument("--receipt")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    project_dir = resolve_project_dir(args.project)
    provenance_path = Path(args.provenance) if args.provenance else None
    receipt_path = Path(args.receipt) if args.receipt else None
    result = write_evidence_output_binding_receipt(
        project_dir=project_dir,
        provenance_path=provenance_path,
        receipt_path=receipt_path,
    )
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        receipt = result["receipt"]
        print(f"Evidence output binding receipt: {result['path']}")
        print(f"Artifacts bound: {len(receipt['artifacts'])}")
        print("LLM calls: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
