"""Verify compiled-evidence replay manifests against current files."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from ztare.common.paths import PROJECTS_DIR
from ztare.workspace.compile_evidence import (
    EVIDENCE_REPLAY_MANIFEST_FILENAME,
    EVIDENCE_REPLAY_MANIFEST_SCHEMA,
    sha256_file,
    stable_json_sha256,
)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_project_dir(project: str) -> Path:
    candidate = Path(project)
    if candidate.exists():
        return candidate.resolve()
    fallback = PROJECTS_DIR / project
    if fallback.exists():
        return fallback.resolve()
    raise SystemExit(f"project not found: {project}")


def _hash_file(path: Path) -> str | None:
    return sha256_file(path) if path.exists() else None


def verify_evidence_replay_manifest(project_dir: Path) -> dict[str, Any]:
    manifest_path = project_dir / EVIDENCE_REPLAY_MANIFEST_FILENAME
    if not manifest_path.exists():
        return {
            "schema": "ztare-evidence-replay-check-v1",
            "project": project_dir.name,
            "ok": False,
            "status": "missing_manifest",
            "manifest_path": str(manifest_path),
            "errors": [
                f"missing {EVIDENCE_REPLAY_MANIFEST_FILENAME}; rerun compile-evidence"
            ],
        }

    manifest = read_json(manifest_path)
    errors: list[str] = []
    warnings: list[str] = []
    if manifest.get("schema") != EVIDENCE_REPLAY_MANIFEST_SCHEMA:
        errors.append(
            f"unexpected manifest schema: {manifest.get('schema')!r}"
        )

    input_projection = manifest.get("input_projection")
    if not isinstance(input_projection, dict):
        errors.append("manifest input_projection is missing or not an object")
        input_projection = {}
    support_counts = manifest.get("support_projection_counts")
    if not isinstance(support_counts, dict):
        errors.append("manifest support_projection_counts is missing or not an object")
    artifact_hashes = manifest.get("artifact_hashes")
    if not isinstance(artifact_hashes, dict):
        errors.append("manifest artifact_hashes is missing or not an object")
        artifact_hashes = {}

    expected_input_hash = manifest.get("input_binding_sha256")
    actual_input_hash = stable_json_sha256(input_projection)
    if expected_input_hash != actual_input_hash:
        errors.append("input_binding_sha256 does not match input_projection")

    source_binding = input_projection.get("source_binding")
    if isinstance(source_binding, dict):
        expected_source_hash = manifest.get("source_binding_sha256")
        actual_source_hash = stable_json_sha256(source_binding)
        if expected_source_hash != actual_source_hash:
            errors.append("source_binding_sha256 does not match source_binding")
    else:
        errors.append("input_projection.source_binding is missing or not an object")

    expected_artifacts = {
        "evidence_txt": project_dir / "evidence.txt",
        "audit_copy": project_dir / "compiled_evidence.txt",
        "packet_json": project_dir / "compiled_evidence_packet.json",
        "evidence_gap_action": project_dir / "workspace" / "evidence_gap_action.json",
    }
    artifact_results: dict[str, dict[str, Any]] = {}
    for key, path in expected_artifacts.items():
        expected_hash = artifact_hashes.get(key)
        actual_hash = _hash_file(path)
        ok = expected_hash == actual_hash
        artifact_results[key] = {
            "path": str(path),
            "expected_sha256": expected_hash,
            "actual_sha256": actual_hash,
            "ok": ok,
        }
        if expected_hash is not None and actual_hash is None:
            errors.append(f"{key} is missing: {path}")
        elif expected_hash != actual_hash:
            errors.append(f"{key} hash mismatch: {path}")

    mode = str(manifest.get("mode") or "unknown")
    if mode == "workspace":
        snapshot_path = project_dir / "workspace" / "workspace_snapshot.json"
        expected_snapshot = input_projection.get("workspace_snapshot_sha256")
        actual_snapshot = _hash_file(snapshot_path)
        if expected_snapshot != actual_snapshot:
            errors.append(f"workspace snapshot hash mismatch: {snapshot_path}")
    elif mode == "raw":
        cache_key = input_projection.get("cache_key")
        if not cache_key:
            errors.append("raw replay manifest is missing cache_key")
        else:
            cache_root = project_dir / "workspace" / "compiled_evidence_cache" / str(cache_key)
            cache_packet = cache_root / "packet.json"
            cache_manifest = cache_root / "manifest.json"
            for key, path in {
                "raw_cache_packet": cache_packet,
                "raw_cache_manifest": cache_manifest,
            }.items():
                expected_hash = artifact_hashes.get(key)
                actual_hash = _hash_file(path)
                if expected_hash != actual_hash:
                    errors.append(f"{key} hash mismatch: {path}")
    else:
        warnings.append(f"unknown replay mode: {mode}")

    return {
        "schema": "ztare-evidence-replay-check-v1",
        "project": project_dir.name,
        "ok": not errors,
        "status": "ok" if not errors else "stale_or_invalid",
        "manifest_path": str(manifest_path),
        "mode": mode,
        "replay_mode": manifest.get("replay_mode"),
        "input_binding_sha256": manifest.get("input_binding_sha256"),
        "support_binding_sha256": manifest.get("support_binding_sha256"),
        "artifact_results": artifact_results,
        "errors": errors,
        "warnings": warnings,
    }


def render_text(report: dict[str, Any]) -> str:
    lines = [
        f"Evidence replay: {report.get('project')}",
        f"Status: {report.get('status')}",
        f"Manifest: {report.get('manifest_path')}",
    ]
    if report.get("input_binding_sha256"):
        lines.append(f"Input binding: {report['input_binding_sha256']}")
    if report.get("support_binding_sha256"):
        lines.append(f"Support binding: {report['support_binding_sha256']}")
    errors = report.get("errors") or []
    if errors:
        lines.extend(["", "Errors:"])
        lines.extend(f"- {error}" for error in errors)
    warnings = report.get("warnings") or []
    if warnings:
        lines.extend(["", "Warnings:"])
        lines.extend(f"- {warning}" for warning in warnings)
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify compiled_evidence_replay_manifest.json against current project files."
    )
    parser.add_argument("--project", required=True, help="Project name or explicit project path.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    args = parser.parse_args(argv)

    project_dir = resolve_project_dir(args.project)
    report = verify_evidence_replay_manifest(project_dir)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_text(report), end="")
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
