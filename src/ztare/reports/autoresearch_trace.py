"""Read-only trace over one autoresearch project surface."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shlex
from pathlib import Path
from typing import Any

from ztare.reports.autoresearch_kernel_health import build_autoresearch_kernel_health
from ztare.research_director.autoresearch_plan_preview import (
    build_autoresearch_plan_preview,
)
from ztare.research_director.graph_carrier_actions import graph_carrier_action_rows
from ztare.scaffold.source_check import check_source_project
from ztare.scaffold.substrate_queue import (
    load_project_packet,
    validate_project_packet,
    validate_project_packet_falsifier,
)
from ztare.workspace.evidence_gaps import (
    LOCAL_VERIFICATION_RECOVERY_KIND,
    evidence_gap_recovery_contract,
    evidence_gap_recovery,
)
from ztare.workspace.evidence_output_binding import (
    RECEIPT_FILENAME as EVIDENCE_OUTPUT_BINDING_RECEIPT_FILENAME,
    verify_evidence_output_binding_receipt,
)
from ztare.workspace.evidence_replay import verify_evidence_replay_manifest
from ztare.workspace.claim_support import build_claim_support_audit
from ztare.workspace.source_freshness import (
    artifact_source_freshness,
    source_binding_contract_blocks_kernel,
)
from ztare.validator.probability_dag_carrier import (
    build_probability_dag_graph_carrier,
    summarize_probability_dag_graph_carrier,
)
from ztare.validator.rubric_mode_resolver import apply_rubric_mode_defaults
from ztare.validator.autoresearch_prediction_contract import summarize_prediction_contracts
from ztare.validator.source_claim_graph_carrier import (
    build_source_claim_graph_carrier,
    summarize_source_claim_graph_carrier,
)
from ztare.validator.hypothesis_projection import build_projection


REPO = Path(__file__).resolve().parents[3]
VALIDATE_RUBRIC = REPO / "scripts" / "public" / "validators" / "validate_rubric.py"

_INTAKE_CANONICAL_IDS = {
    "project_packet": "project_intake",
    "blocked_on_project_packet": "blocked_on_project_intake",
    "traceable_but_no_project_packet": "traceable_but_no_project_intake",
    "compiled_evidence_without_admission_packet": "compiled_evidence_without_admission_intake",
    "missing_admission_packet": "missing_admission_intake",
}


def _canonical_intake_id(value: Any) -> str:
    item = str(value or "").strip()
    return _INTAKE_CANONICAL_IDS.get(item, item)


def _canonicalized_blocker(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    canonical_id = _canonical_intake_id(out.get("id"))
    if canonical_id and canonical_id != out.get("id"):
        out["canonical_id"] = canonical_id
    canonical_channel = _canonical_intake_id(out.get("recovery_channel"))
    if canonical_channel and canonical_channel != out.get("recovery_channel"):
        out["canonical_recovery_channel"] = canonical_channel
    return out


def _sha256_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _packet_receipt_with_current_hash(
    packet: Any,
    *,
    repo: Path,
) -> dict[str, Any]:
    if not isinstance(packet, dict):
        return {}
    out = dict(packet)
    expected_sha = str(out.get("packet_sha256") or "").strip()
    if not expected_sha:
        return out
    packet_path = str(out.get("packet_path") or "").strip()
    if not packet_path:
        out["packet_hash_status"] = "unverified_missing_packet_path"
        out["packet_hash_verified"] = False
        return out
    candidate = Path(packet_path)
    if not candidate.is_absolute():
        candidate = repo / packet_path
    current_sha = _sha256_file(candidate)
    if not current_sha:
        out["packet_hash_status"] = "missing_current_packet"
        out["packet_hash_verified"] = False
        return out
    out["packet_current_sha256"] = current_sha
    out["packet_hash_verified"] = current_sha == expected_sha
    out["packet_hash_status"] = (
        "fresh" if current_sha == expected_sha else "stale_current_packet"
    )
    return out


def _kernel_entry_sha256(kernel_entry: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(kernel_entry, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _packet_receipt_with_current_kernel_entry(
    packet: Any,
    *,
    current_kernel_entry_sha256: str,
    mutable_after_launch: bool = False,
) -> dict[str, Any]:
    if not isinstance(packet, dict):
        return {}
    out = dict(packet)
    expected_sha = str(out.get("kernel_entry_sha256") or "").strip()
    if not expected_sha:
        return out
    out["kernel_entry_current_sha256"] = current_kernel_entry_sha256
    if expected_sha == current_kernel_entry_sha256:
        out["kernel_entry_hash_verified"] = True
        out["kernel_entry_hash_status"] = "fresh"
    elif mutable_after_launch:
        out["kernel_entry_hash_verified"] = None
        out["kernel_entry_hash_status"] = "post_run_state_changed"
    else:
        out["kernel_entry_hash_verified"] = False
        out["kernel_entry_hash_status"] = "current_kernel_entry_changed"
    return out


def _recent_loop_with_current_kernel_entry(
    recent_loop: dict[str, Any],
    *,
    kernel_entry: dict[str, Any],
) -> dict[str, Any]:
    if not recent_loop.get("available"):
        return recent_loop
    current_sha = _kernel_entry_sha256(kernel_entry)
    out = dict(recent_loop)
    latest_packet = _packet_receipt_with_current_kernel_entry(
        out.get("latest_run_project_packet"),
        current_kernel_entry_sha256=current_sha,
        mutable_after_launch=True,
    )
    if latest_packet:
        out["latest_run_project_packet"] = latest_packet
    latest_preflight = out.get("latest_preflight_only")
    if isinstance(latest_preflight, dict):
        latest_preflight_out = dict(latest_preflight)
        preflight_packet = _packet_receipt_with_current_kernel_entry(
            latest_preflight_out.get("packet"),
            current_kernel_entry_sha256=current_sha,
        )
        if preflight_packet:
            latest_preflight_out["packet"] = preflight_packet
        out["latest_preflight_only"] = latest_preflight_out
    return out


def _loop_admission_summary(recent_loop: dict[str, Any]) -> dict[str, Any]:
    packets: list[dict[str, Any]] = []
    latest_preflight = recent_loop.get("latest_preflight_only")
    latest_preflight_run_id = None
    preflight_packet = None
    if isinstance(latest_preflight, dict):
        latest_preflight_run_id = latest_preflight.get("run_id")
        preflight_packet = latest_preflight.get("packet")
    latest_packet = recent_loop.get("latest_run_project_packet")
    latest_run_id = recent_loop.get("latest_run_id")
    if (
        latest_preflight_run_id is not None
        and latest_run_id is not None
    ):
        if latest_preflight_run_id >= latest_run_id:
            if isinstance(preflight_packet, dict) and preflight_packet:
                packets.append(preflight_packet)
            latest_packet = None
        elif isinstance(latest_packet, dict) and latest_packet:
            packets.append(latest_packet)
            preflight_packet = None
    else:
        if isinstance(preflight_packet, dict) and preflight_packet:
            packets.append(preflight_packet)
    if (
        not packets
        and latest_preflight_run_id is not None
        and latest_run_id is not None
    ):
        latest_packet = None
    if isinstance(latest_packet, dict) and latest_packet:
        packets.append(latest_packet)

    unique_packets: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for packet in packets:
        key = (
            str(packet.get("packet_path") or ""),
            str(packet.get("packet_sha256") or ""),
            str(packet.get("kernel_entry_sha256") or ""),
        )
        if key in seen:
            continue
        seen.add(key)
        unique_packets.append(packet)

    packet_statuses = _dedupe_strings(
        [packet.get("packet_hash_status") for packet in unique_packets]
    )
    kernel_entry_statuses = _dedupe_strings(
        [packet.get("kernel_entry_hash_status") for packet in unique_packets]
    )
    packet_verified_values = [
        packet.get("packet_hash_verified") for packet in unique_packets
    ]
    kernel_entry_verified_values = [
        packet.get("kernel_entry_hash_verified") for packet in unique_packets
    ]
    packet_hash_verified = _aggregate_verified(packet_verified_values)
    kernel_entry_hash_verified = _aggregate_verified(kernel_entry_verified_values)
    return {
        "available": bool(unique_packets),
        "receipt_count": len(unique_packets),
        "intake_hash_verified": packet_hash_verified,
        "intake_hash_statuses": packet_statuses,
        "packet_hash_verified": packet_hash_verified,
        "packet_hash_statuses": packet_statuses,
        "kernel_entry_hash_verified": kernel_entry_hash_verified,
        "kernel_entry_hash_statuses": kernel_entry_statuses,
    }


def _loop_preflight_admitted(loop_admission: dict[str, Any]) -> bool:
    """Return true when the latest admission proves current preflight passed."""
    if not loop_admission.get("available"):
        return False
    if loop_admission.get("intake_hash_verified") is not True:
        return False
    if loop_admission.get("kernel_entry_hash_verified") is not True:
        return False
    return (
        loop_admission.get("intake_hash_statuses") == ["fresh"]
        and loop_admission.get("kernel_entry_hash_statuses") == ["fresh"]
    )


def _project_intake_alias(project_packet: dict[str, Any]) -> dict[str, Any]:
    out = dict(project_packet)
    out["intake_id"] = out.get("packet_id")
    out["intake_path"] = out.get("path")
    out["legacy_receipt_surface"] = "project_packet"
    return out


def _project_intake_receipt_alias(packet: dict[str, Any]) -> dict[str, Any]:
    out = dict(packet)
    out["intake_id"] = out.get("packet_id")
    out["intake_path"] = out.get("packet_path")
    out["intake_status"] = out.get("packet_status")
    out["legacy_receipt_surface"] = "project_packet"
    return out


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _admission_receipt_context(
    receipt: dict[str, Any],
    *,
    source: str,
    run_id: Any,
    current: bool,
    superseding_source: str | None = None,
    superseding_run_id: Any = None,
) -> dict[str, Any]:
    out = dict(receipt)
    out["admission_source"] = source
    out["admission_run_id"] = run_id
    out["current_admission"] = current
    if not current:
        out["superseded_by_current_admission"] = True
        if superseding_source:
            out["superseding_admission_source"] = superseding_source
        if superseding_run_id is not None:
            out["superseding_admission_run_id"] = superseding_run_id
    return out


def _current_project_intake_admission(
    *,
    latest_run_packet: dict[str, Any] | None,
    latest_run_id: Any,
    latest_preflight_packet: dict[str, Any] | None,
    latest_preflight_run_id: Any,
) -> dict[str, Any] | None:
    run_i = _as_int(latest_run_id)
    preflight_i = _as_int(latest_preflight_run_id)
    if (
        preflight_i is not None
        and run_i is not None
        and preflight_i >= run_i
        and isinstance(latest_preflight_packet, dict)
        and latest_preflight_packet
    ):
        packet = _admission_receipt_context(
            latest_preflight_packet,
            source="latest_preflight_only",
            run_id=latest_preflight_run_id,
            current=True,
        )
        return {
            "source": "latest_preflight_only",
            "run_id": latest_preflight_run_id,
            "intake": _project_intake_receipt_alias(packet),
            "legacy_project_packet": packet,
        }
    if isinstance(latest_run_packet, dict) and latest_run_packet:
        packet = _admission_receipt_context(
            latest_run_packet,
            source="latest_run",
            run_id=latest_run_id,
            current=True,
        )
        return {
            "source": "latest_run",
            "run_id": latest_run_id,
            "intake": _project_intake_receipt_alias(packet),
            "legacy_project_packet": packet,
        }
    if isinstance(latest_preflight_packet, dict) and latest_preflight_packet:
        packet = _admission_receipt_context(
            latest_preflight_packet,
            source="latest_preflight_only",
            run_id=latest_preflight_run_id,
            current=True,
        )
        return {
            "source": "latest_preflight_only",
            "run_id": latest_preflight_run_id,
            "intake": _project_intake_receipt_alias(packet),
            "legacy_project_packet": packet,
        }
    return None


def _aggregate_verified(values: list[Any]) -> bool | None:
    if not values:
        return None
    if any(value is False for value in values):
        return False
    if all(value is True for value in values):
        return True
    return None


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


_EVIDENCE_FETCH_SEVERITY_PRIORITY = ("blocking", "degrading", "enriching")


def _evidence_fetch_severity(
    latest_evidence_gaps: Path,
    *,
    project_dir: Path,
) -> str:
    """Choose the strongest active public evidence-gap severity for fetch."""
    payload = _read_json(latest_evidence_gaps)
    rows = payload.get("evidence_gaps")
    if not isinstance(rows, list):
        return "degrading"
    active_public_severities: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        contract = evidence_gap_recovery_contract(row, project_dir=project_dir)
        if not contract.get("can_public_fetch"):
            continue
        severity = str(row.get("severity") or "").strip().lower()
        if severity:
            active_public_severities.add(severity)
    for severity in _EVIDENCE_FETCH_SEVERITY_PRIORITY:
        if severity in active_public_severities:
            return severity
    return "degrading"


def _source_index_receipt_summary(
    *,
    receipt: dict[str, Any],
    receipt_path: Path,
    source_index_path: Path,
    workspace_meta_path: Path,
    repo: Path,
) -> dict[str, Any]:
    if not receipt:
        return {
            "exists": False,
            "path": _rel(receipt_path, repo),
            "status": "missing",
            "verified": False,
            "hash_mismatches": [],
        }
    hash_mismatches: list[str] = []
    missing_artifacts: list[str] = []
    source_index_sha = _sha256_file(source_index_path)
    if source_index_sha is None:
        missing_artifacts.append("source_index")
    elif receipt.get("source_index_sha256") != source_index_sha:
        hash_mismatches.append("source_index")
    if "workspace_meta_sha256" in receipt:
        workspace_meta_sha = _sha256_file(workspace_meta_path)
        if workspace_meta_sha is None:
            missing_artifacts.append("workspace_meta")
        elif receipt.get("workspace_meta_sha256") != workspace_meta_sha:
            hash_mismatches.append("workspace_meta")
    schema_ok = receipt.get("schema") == "ztare-source-index-receipt-v1"
    status_ok = receipt.get("status") == "indexed"
    verified = schema_ok and status_ok and not hash_mismatches and not missing_artifacts
    if verified:
        status = "fresh"
    elif not schema_ok or not status_ok:
        status = "invalid"
    elif missing_artifacts:
        status = "stale_missing_artifact"
    else:
        status = "stale"
    return {
        "exists": True,
        "path": _rel(receipt_path, repo),
        "status": status,
        "verified": verified,
        "schema": receipt.get("schema"),
        "producer": receipt.get("producer"),
        "llm_calls": receipt.get("llm_calls"),
        "source_count": receipt.get("source_count"),
        "merge_status": receipt.get("merge_status"),
        "hash_mismatches": hash_mismatches,
        "missing_artifacts": missing_artifacts,
    }


def _compiled_evidence_output_binding(
    *,
    provenance: dict[str, Any],
    evidence_path: Path,
    repo: Path,
    project_dir: Path,
    binding_receipt: dict[str, Any] | None = None,
    binding_receipt_path: Path | None = None,
) -> dict[str, Any]:
    if not evidence_path.exists():
        return {
            "status": "missing_evidence",
            "verified": False,
            "evidence_path": _rel(evidence_path, repo),
            "hash_mismatch": False,
        }
    current_sha = _sha256_file(evidence_path)
    if not provenance:
        return {
            "status": "missing_provenance",
            "verified": False,
            "evidence_path": _rel(evidence_path, repo),
            "current_sha256": current_sha,
            "expected_sha256": None,
            "hash_mismatch": False,
        }
    expected_sha = str(provenance.get("output_sha256") or "").strip()
    if not expected_sha:
        receipt_summary = verify_evidence_output_binding_receipt(
            receipt=binding_receipt or {},
            receipt_path=binding_receipt_path
            or project_dir / "workspace" / EVIDENCE_OUTPUT_BINDING_RECEIPT_FILENAME,
            project_dir=project_dir,
            repo=repo,
        )
        if receipt_summary.get("verified"):
            return {
                "status": "fresh",
                "verified": True,
                "evidence_path": _rel(evidence_path, repo),
                "current_sha256": current_sha,
                "expected_sha256": None,
                "hash_mismatch": False,
                "output_path": provenance.get("output_path"),
                "packet_output_path": provenance.get("packet_output_path"),
                "binding_source": "evidence_output_binding_receipt",
                "legacy_output_hash_binding": True,
                "receipt": receipt_summary,
                "artifact_bindings": receipt_summary.get("artifact_bindings", []),
                "stale_artifacts": [],
            }
        stale_receipt_statuses = {
            "stale_provenance",
            "missing_primary_artifact",
            "stale_missing_artifact",
            "stale_artifact_hash",
        }
        if receipt_summary.get("exists") and receipt_summary.get("status") in stale_receipt_statuses:
            return {
                "status": "stale",
                "verified": False,
                "evidence_path": _rel(evidence_path, repo),
                "current_sha256": current_sha,
                "expected_sha256": None,
                "hash_mismatch": bool(receipt_summary.get("stale_artifacts")),
                "output_path": provenance.get("output_path"),
                "packet_output_path": provenance.get("packet_output_path"),
                "binding_source": "evidence_output_binding_receipt",
                "legacy_output_hash_binding": True,
                "receipt": receipt_summary,
                "artifact_bindings": receipt_summary.get("artifact_bindings", []),
                "stale_artifacts": receipt_summary.get("stale_artifacts", []),
            }
        return {
            "status": "unverified_missing_output_hash",
            "verified": False,
            "evidence_path": _rel(evidence_path, repo),
            "current_sha256": current_sha,
            "expected_sha256": None,
            "hash_mismatch": False,
            "receipt": receipt_summary,
        }
    primary_binding = {
        "artifact_id": "evidence_output",
        "path": _rel(evidence_path, repo),
        "current_sha256": current_sha,
        "expected_sha256": expected_sha,
        "verified": current_sha == expected_sha,
        "hash_mismatch": current_sha != expected_sha,
        "status": "fresh" if current_sha == expected_sha else "stale",
    }
    artifact_bindings = [primary_binding]
    artifact_bindings.extend(
        binding
        for binding in (
            _compiled_evidence_artifact_binding(
                provenance=provenance,
                path_key="audit_copy_path",
                sha_key="audit_copy_sha256",
                artifact_id="audit_copy",
                evidence_path=evidence_path,
                repo=repo,
            ),
            _compiled_evidence_artifact_binding(
                provenance=provenance,
                path_key="packet_output_path",
                sha_key="packet_output_sha256",
                artifact_id="packet_output",
                evidence_path=evidence_path,
                repo=repo,
            ),
        )
        if binding is not None
    )
    verified = all(bool(binding.get("verified")) for binding in artifact_bindings)
    stale = any(
        binding.get("hash_mismatch") is True or binding.get("status") == "missing_artifact"
        for binding in artifact_bindings
    )
    return {
        "status": "fresh" if verified else ("stale" if stale else "unverified"),
        "verified": verified,
        "evidence_path": _rel(evidence_path, repo),
        "current_sha256": current_sha,
        "expected_sha256": expected_sha,
        "hash_mismatch": any(
            binding.get("hash_mismatch") is True for binding in artifact_bindings
        ),
        "output_path": provenance.get("output_path"),
        "packet_output_path": provenance.get("packet_output_path"),
        "artifact_bindings": artifact_bindings,
        "stale_artifacts": [
            str(binding.get("artifact_id"))
            for binding in artifact_bindings
            if binding.get("hash_mismatch") is True
            or binding.get("status") == "missing_artifact"
        ],
    }


def _trace_evidence_replay_report(
    *,
    project_dir: Path,
    provenance: dict[str, Any],
    repo: Path,
) -> tuple[dict[str, Any], bool]:
    manifest_path = project_dir / "compiled_evidence_replay_manifest.json"
    required = bool(provenance.get("evidence_replay_manifest_path")) or manifest_path.exists()
    report = verify_evidence_replay_manifest(project_dir)
    normalized = dict(report)
    normalized["required"] = required
    if normalized.get("manifest_path"):
        normalized["manifest_path"] = _rel(Path(str(normalized["manifest_path"])), repo)
    artifact_results = normalized.get("artifact_results")
    if isinstance(artifact_results, dict):
        normalized_results: dict[str, dict[str, Any]] = {}
        for key, value in artifact_results.items():
            if not isinstance(value, dict):
                continue
            row = dict(value)
            if row.get("path"):
                row["path"] = _rel(Path(str(row["path"])), repo)
            normalized_results[str(key)] = row
        normalized["artifact_results"] = normalized_results
    return normalized, required


def _trace_evidence_readiness(
    *,
    source_index_freshness: dict[str, Any],
    compile_provenance_freshness: dict[str, Any],
    evidence_output_binding: dict[str, Any],
    evidence_replay: dict[str, Any],
) -> dict[str, Any]:
    replay_required = bool(evidence_replay.get("required"))
    replay_ok = bool(evidence_replay.get("ok")) if replay_required else True
    status = "fresh"
    if str(source_index_freshness.get("status") or "") not in {"", "fresh"}:
        status = "blocked"
    if str(compile_provenance_freshness.get("status") or "") not in {"", "fresh"}:
        status = "blocked"
    if str(evidence_output_binding.get("status") or "") not in {"", "fresh"}:
        status = "blocked"
    if replay_required and not replay_ok:
        status = "blocked"
    return {
        "status": status,
        "source_index_status": source_index_freshness.get("status"),
        "compile_provenance_status": compile_provenance_freshness.get("status"),
        "output_binding_status": evidence_output_binding.get("status"),
        "output_stale_artifacts": list(evidence_output_binding.get("stale_artifacts") or []),
        "replay_required": replay_required,
        "replay_status": evidence_replay.get("status"),
        "replay_ok": replay_ok,
    }


def _compiled_evidence_artifact_binding(
    *,
    provenance: dict[str, Any],
    path_key: str,
    sha_key: str,
    artifact_id: str,
    evidence_path: Path,
    repo: Path,
) -> dict[str, Any] | None:
    raw_path = str(provenance.get(path_key) or "").strip()
    expected_sha = str(provenance.get(sha_key) or "").strip()
    if not raw_path and not expected_sha:
        return None
    if not raw_path:
        return {
            "artifact_id": artifact_id,
            "path": None,
            "expected_sha256": expected_sha or None,
            "verified": False,
            "hash_mismatch": False,
            "status": "unverified_missing_artifact_path",
        }
    artifact_path = _resolve_provenance_artifact_path(
        raw_path,
        evidence_path=evidence_path,
        repo=repo,
    )
    if not artifact_path.exists():
        return {
            "artifact_id": artifact_id,
            "path": _rel(artifact_path, repo),
            "expected_sha256": expected_sha or None,
            "verified": False,
            "hash_mismatch": False,
            "status": "missing_artifact",
        }
    current_artifact_sha = _sha256_file(artifact_path)
    if not expected_sha:
        return {
            "artifact_id": artifact_id,
            "path": _rel(artifact_path, repo),
            "current_sha256": current_artifact_sha,
            "expected_sha256": None,
            "verified": False,
            "hash_mismatch": False,
            "status": "unverified_missing_artifact_hash",
        }
    verified = current_artifact_sha == expected_sha
    return {
        "artifact_id": artifact_id,
        "path": _rel(artifact_path, repo),
        "current_sha256": current_artifact_sha,
        "expected_sha256": expected_sha,
        "verified": verified,
        "hash_mismatch": not verified,
        "status": "fresh" if verified else "stale",
    }


def _resolve_provenance_artifact_path(
    raw_path: str,
    *,
    evidence_path: Path,
    repo: Path,
) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    project_candidate = evidence_path.parent / path
    if project_candidate.exists():
        return project_candidate
    repo_candidate = repo / path
    if repo_candidate.exists():
        return repo_candidate
    return repo_candidate


def _project_dir(repo: Path, project: str) -> Path:
    candidate = Path(project)
    if candidate.exists():
        return candidate.resolve()
    return (repo / "projects" / project).resolve()


def _rubric_path(repo: Path, rubric: str | None) -> Path | None:
    if not rubric:
        return None
    candidate = Path(rubric)
    if candidate.exists():
        return candidate.resolve()
    repo_candidate = repo / rubric
    if repo_candidate.exists():
        return repo_candidate.resolve()
    rubrics_candidate = repo / "rubrics" / rubric
    if rubrics_candidate.exists():
        return rubrics_candidate.resolve()
    if not rubric.endswith(".json"):
        rubrics_json = repo / "rubrics" / f"{rubric}.json"
        if rubrics_json.exists():
            return rubrics_json.resolve()
    return None


def _count_raw_files(raw_dir: Path) -> int:
    if not raw_dir.is_dir():
        return 0
    return sum(
        1
        for path in raw_dir.rglob("*")
        if path.is_file() and path.name != "source_type_map.json"
    )


def _eval_history_rows(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def _read_jsonl_dicts(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _dedupe_strings(values: list[Any]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        item = str(value or "").strip()
        if not item or item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def _dedupe_fallback_events(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        for event in row.get("mutator_fallback_events", []) or []:
            if not isinstance(event, dict):
                continue
            src = str(event.get("from") or "").strip()
            dst = str(event.get("to") or "").strip()
            if not src or not dst or (src, dst) in seen:
                continue
            seen.add((src, dst))
            out.append({"from": src, "to": dst})
    return out


def _int_from_mapping(mapping: Any, key: str) -> int:
    if not isinstance(mapping, dict):
        return 0
    try:
        return int(mapping.get(key) or 0)
    except (TypeError, ValueError):
        return 0


def _provider_failure_signature(
    row: dict[str, Any],
    *,
    requested_model_id: str,
    effective_model_ids: list[str],
    fallback_events: list[dict[str, str]],
) -> dict[str, Any] | None:
    usage = row.get("mutator_usage")
    input_tokens = _int_from_mapping(usage, "input_tokens")
    output_tokens = _int_from_mapping(usage, "output_tokens")
    if (
        not requested_model_id
        or input_tokens <= 0
        or output_tokens > 0
        or effective_model_ids
        or fallback_events
    ):
        return None
    return {
        "failure_class": "mutator_charged_no_output_no_effective_model",
        "model_id": requested_model_id,
        "input_tokens_charged": input_tokens,
        "output_tokens": output_tokens,
        "fallback_observed": False,
        "pending_loop_action": row.get("pending_loop_action"),
        "information_yield_rationale": row.get("information_yield_rationale", ""),
        "estimated_cost_usd": row.get("estimated_cost_usd"),
        "interpretation": "provider_runtime_failure_not_research_signal",
        "recovery_kind": "provider_timeout_retry_budget",
        "retry_scope": "same_model_before_cross_model_fallback",
        "recommended_retry_budget": {
            "same_model_retries": 1,
            "allow_cross_model_fallback": False,
        },
        "run_id": row.get("run_id"),
        "iteration": row.get("iteration_index") or row.get("iteration"),
    }


def _dedupe_provider_failure_signatures(
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[tuple[Any, Any, str, str]] = set()
    for row in rows:
        requested_model = str(
            row.get("mutator_model_id")
            or row.get("mutator_requested_model_id")
            or ""
        ).strip()
        effective_models = _dedupe_strings(
            list(row.get("mutator_effective_model_ids", []) or [])
        )
        fallback_events = _dedupe_fallback_events([row])
        signature = _provider_failure_signature(
            row,
            requested_model_id=requested_model,
            effective_model_ids=effective_models,
            fallback_events=fallback_events,
        )
        if not signature:
            continue
        key = (
            signature.get("run_id"),
            signature.get("iteration"),
            str(signature.get("model_id") or ""),
            str(signature.get("failure_class") or ""),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(signature)
    return out


def _recent_loop_summary(workspace: Path, *, repo: Path) -> dict[str, Any]:
    eval_rows = _read_jsonl_dicts(workspace / "eval_history.jsonl")
    telemetry_stream = _read_jsonl_dicts(workspace / "iteration_telemetry.jsonl")
    telemetry_rows = [row for row in telemetry_stream if row.get("record_type") == "iteration"]
    run_start_rows = [row for row in telemetry_stream if row.get("record_type") == "run_start"]
    run_end_rows = [row for row in telemetry_stream if row.get("record_type") == "run_end"]
    if not eval_rows and not telemetry_rows and not run_start_rows and not run_end_rows:
        return {"available": False}

    recent_eval = eval_rows[-20:]
    recent_telemetry = telemetry_rows[-20:]
    latest_eval = eval_rows[-1] if eval_rows else {}
    latest_telemetry = telemetry_rows[-1] if telemetry_rows else {}
    latest = latest_telemetry or latest_eval
    latest_run_id = latest.get("run_id")
    if latest_run_id is None and run_end_rows:
        latest_run_id = run_end_rows[-1].get("run_id")
    latest_run_end = next(
        (
            row
            for row in reversed(run_end_rows)
            if latest_run_id is not None and row.get("run_id") == latest_run_id
        ),
        {},
    )
    latest_run_start = next(
        (
            row
            for row in reversed(run_start_rows)
            if latest_run_id is not None and row.get("run_id") == latest_run_id
        ),
        {} if latest_run_id is not None else (run_start_rows[-1] if run_start_rows else {}),
    )
    latest_preflight_end = next(
        (row for row in reversed(run_end_rows) if row.get("preflight_only") is True),
        {},
    )
    latest_preflight_start = next(
        (
            row
            for row in reversed(run_start_rows)
            if latest_preflight_end.get("run_id") is not None
            and row.get("run_id") == latest_preflight_end.get("run_id")
        ),
        {},
    )
    latest_run_project_packet = latest_run_start.get("project_packet")
    latest_run_project_packet = _packet_receipt_with_current_hash(
        latest_run_project_packet,
        repo=repo,
    )
    latest_preflight_packet = _packet_receipt_with_current_hash(
        latest_preflight_start.get("project_packet"),
        repo=repo,
    )
    latest_preflight_run_id = latest_preflight_end.get("run_id")
    failed_gate_ids = _dedupe_strings(
        list(latest.get("failed_gate_ids", []) or [])
        + list(latest_eval.get("failed_gate_ids", []) or [])
    )
    requested_models = _dedupe_strings(
        [row.get("mutator_model_id") for row in recent_telemetry]
        + [row.get("mutator_requested_model_id") for row in recent_eval]
    )
    effective_models = _dedupe_strings(
        [
            model
            for row in recent_telemetry + recent_eval
            for model in (row.get("mutator_effective_model_ids", []) or [])
        ]
    )
    fallback_events = _dedupe_fallback_events(recent_telemetry + recent_eval)
    provider_failure_signatures = _dedupe_provider_failure_signatures(
        recent_telemetry + recent_eval
    )
    latest_requested_model = (
        latest.get("mutator_model_id")
        or latest.get("mutator_requested_model_id")
        or latest_eval.get("mutator_requested_model_id")
        or ""
    )
    latest_effective_models = _dedupe_strings(
        list(latest.get("mutator_effective_model_ids", []) or [])
        + list(latest_eval.get("mutator_effective_model_ids", []) or [])
    )
    latest_fallback_events = _dedupe_fallback_events([latest, latest_eval])
    latest_provider_failure_signature = _provider_failure_signature(
        latest,
        requested_model_id=str(latest_requested_model or ""),
        effective_model_ids=latest_effective_models,
        fallback_events=latest_fallback_events,
    )
    gate_zeroed_keys: set[tuple[Any, Any]] = set()
    for row in recent_telemetry + recent_eval:
        if row.get("score") != 0 or not row.get("failed_gate_ids"):
            continue
        key = (row.get("run_id"), row.get("iteration_index") or row.get("iteration"))
        gate_zeroed_keys.add(key)
    latest_score = latest.get("score")
    latest_raw_judge_score = latest.get("raw_judge_score")
    latest_score_delta_from_raw = None
    if isinstance(latest_score, (int, float)) and isinstance(latest_raw_judge_score, (int, float)):
        latest_score_delta_from_raw = latest_raw_judge_score - latest_score
    summary = {
        "available": True,
        "eval_history_rows": len(eval_rows),
        "telemetry_iteration_rows": len(telemetry_rows),
        "latest_run_id": latest_run_id,
        "latest_iteration": latest.get("iteration_index") or latest.get("iteration"),
        "latest_score": latest_score,
        "latest_raw_judge_score": latest_raw_judge_score,
        "latest_score_delta_from_raw": latest_score_delta_from_raw,
        "latest_score_cap_reason": latest.get("score_cap_reason", ""),
        "latest_score_cap_source": latest.get("score_cap_source", ""),
        "latest_run_final_score": latest_run_end.get("final_score"),
        "latest_run_exit_reason": latest_run_end.get("run_exit_reason"),
        "latest_score_is_gate_zeroed": bool(
            latest_score == 0 and (latest.get("gate_failure_count") or failed_gate_ids)
        ),
        "latest_failed_gate_ids": failed_gate_ids,
        "latest_pending_loop_action": latest.get("pending_loop_action"),
        "latest_information_yield_rationale": latest.get("information_yield_rationale", ""),
        "recent_gate_zeroed_count": len(gate_zeroed_keys),
        "latest_mutator_requested_model_id": latest_requested_model,
        "latest_mutator_effective_model_ids": latest_effective_models,
        "latest_mutator_fallback_events": latest_fallback_events,
        "latest_provider_fallback_observed": bool(latest_fallback_events),
        "latest_provider_failure_signature": latest_provider_failure_signature,
        "latest_provider_failure_observed": latest_provider_failure_signature is not None,
        "recent_mutator_requested_model_ids": requested_models,
        "recent_mutator_effective_model_ids": effective_models,
        "recent_mutator_fallback_events": fallback_events,
        "provider_fallback_observed": bool(fallback_events),
        "recent_provider_failure_signatures": provider_failure_signatures,
        "provider_failure_observed": bool(provider_failure_signatures),
        "next_command": (
            "ztare autoresearch hillclimb-audit "
            "--project "
            f"{workspace.parent.name} --recovery-queue --recovery-limit 10 --json"
            if latest.get("pending_loop_action") in {"UNDERIDENTIFIED", "REFRESH_SPECIALISTS", "PIVOT_REQUIRED"}
            else None
        ),
    }
    if latest_run_project_packet:
        summary["latest_run_project_packet"] = latest_run_project_packet
        summary["latest_run_project_intake"] = _project_intake_receipt_alias(
            latest_run_project_packet
        )
    if latest_preflight_end:
        summary["latest_preflight_only"] = {
            "run_id": latest_preflight_end.get("run_id"),
            "run_exit_reason": latest_preflight_end.get("run_exit_reason"),
            "timestamp_utc": latest_preflight_end.get("timestamp_utc"),
            "packet": latest_preflight_packet or None,
            "intake": (
                _project_intake_receipt_alias(latest_preflight_packet)
                if latest_preflight_packet
                else None
            ),
        }
    current_admission = _current_project_intake_admission(
        latest_run_packet=latest_run_project_packet if latest_run_project_packet else None,
        latest_run_id=latest_run_id,
        latest_preflight_packet=(
            latest_preflight_packet if latest_preflight_packet else None
        ),
        latest_preflight_run_id=latest_preflight_run_id,
    )
    if current_admission:
        summary["current_project_intake_admission"] = current_admission
    return summary


def _first_existing_path(paths: list[Path]) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


def _rel(path: Path, repo: Path) -> str:
    try:
        return str(path.relative_to(repo))
    except ValueError:
        return str(path)


def _normalize_slug(value: str | None) -> str:
    if not value:
        return ""
    raw = str(value).strip()
    path = Path(raw)
    if path.suffix == ".json":
        return path.stem
    return path.name if path.parts else raw


def _quote(value: str) -> str:
    return shlex.quote(value)


def _packet_bound_command(command: str, *, packet_path: str) -> str:
    if not command or not packet_path:
        return command
    try:
        tokens = shlex.split(command)
    except ValueError:
        return command
    if tokens[:3] not in (
        ["ztare", "autoresearch", "route"],
        ["ztare", "autoresearch", "run"],
    ):
        return command
    if "--intake" in tokens:
        return command
    if "--packet" in tokens:
        tokens = list(tokens)
        tokens[tokens.index("--packet")] = "--intake"
        return shlex.join(tokens)
    return f"{command} --intake {_quote(packet_path)}"


def _is_autoresearch_run_command(command: str) -> bool:
    try:
        tokens = shlex.split(command)
    except ValueError:
        return False
    return tokens[:3] == ["ztare", "autoresearch", "run"]


def _with_bool_flag(command: str, flag: str) -> str:
    if not command:
        return command
    try:
        tokens = shlex.split(command)
    except ValueError:
        return command
    if flag in tokens:
        return command
    return f"{command} {flag}"


def _source_init_command(*, project: str, rubric: str | None = None) -> str:
    command = f"ztare project source-init --project {_quote(project)}"
    if rubric:
        command += f" --rubric {_quote(rubric)}"
    return command


_SOURCE_PREFLIGHT_SHAPE_BLOCKERS = {
    "project directory is missing",
    "raw source directory is missing",
    "no supported text-like source files found under raw",
    "no non-empty supported source files found under raw",
}
_PREDICTION_AUTHORITY_ISSUE_CODES = {
    "invalid_certification_claim",
    "invalid_decision_use_bypass_claim",
    "invalid_membrane_claim",
    "invalid_routing_authority_claim",
    "membrane_claim_requires_certification",
    "missing_forecast_pool_authority_anchor",
    "invalid_scratch_certification_claim",
}


def _source_preflight_blocks_kernel(source_preflight: dict[str, Any]) -> list[str]:
    return [
        str(item)
        for item in source_preflight.get("blocking", [])
        if str(item) not in _SOURCE_PREFLIGHT_SHAPE_BLOCKERS
    ]


def _prediction_authority_issue_codes(prediction_summary: dict[str, Any]) -> list[str]:
    codes: list[str] = []
    for issue in prediction_summary.get("issues", []):
        if not isinstance(issue, dict):
            continue
        code = str(issue.get("code") or "")
        if code in _PREDICTION_AUTHORITY_ISSUE_CODES and code not in codes:
            codes.append(code)
    return codes


def _source_preflight_for_trace(*, project_dir: Path, repo: Path) -> dict[str, Any]:
    project_ref = _rel(project_dir, repo)
    try:
        return check_source_project(project=project_ref, repo=repo)
    except Exception as exc:  # noqa: BLE001
        blocker = f"source preflight unavailable for trace path: {type(exc).__name__}: {exc}"
        return {
            "schema": "ztare-source-check-v1",
            "ok": False,
            "status": "unavailable_for_trace_path",
            "blocking": [blocker],
            "warnings": [],
            "source_evidence_count": 0,
            "untyped_source_count": 0,
            "next_commands": [f"ztare project source-check --project {project_dir.name} --json"],
        }


def _load_validate_rubric_project():
    spec = importlib.util.spec_from_file_location(
        "_ztare_trace_validate_rubric",
        VALIDATE_RUBRIC,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load validator at {VALIDATE_RUBRIC}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validate_rubric_project


def _launch_preflight_for_trace(
    *,
    project_dir: Path,
    rubric_path: Path | None,
    repo: Path,
) -> dict[str, Any]:
    if rubric_path is None:
        return {
            "ok": False,
            "status": "missing_rubric",
            "errors": ["rubric path could not be resolved"],
            "warnings": [],
            "launch_contract": None,
            "next_command": None,
        }
    if project_dir.parent != repo / "projects":
        project_rel = _rel(project_dir, repo)
        rubric_rel = _rel(rubric_path, repo)
        return {
            "ok": False,
            "status": "unavailable_for_trace_path",
            "errors": [
                "launch preflight is only available for projects under the repo "
                f"projects directory; got {project_rel}"
            ],
            "warnings": [],
            "launch_contract": None,
            "next_command": f"make validate-rubric PROJECT={project_dir.name} RUBRIC={rubric_rel}",
        }
    try:
        validate_rubric_project = _load_validate_rubric_project()
        result = validate_rubric_project(
            project_dir.name,
            rubric=rubric_path,
            repo=repo,
            rubric_only=False,
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "status": "unavailable",
            "errors": [f"{type(exc).__name__}: {exc}"],
            "warnings": [],
            "launch_contract": None,
            "next_command": (
                f"make validate-rubric PROJECT={project_dir.name} RUBRIC={_rel(rubric_path, repo)}"
            ),
        }
    errors = [str(item).strip() for item in result.get("errors", [])]
    warnings = [str(item).strip() for item in result.get("warnings", [])]
    launch_contract = result.get("launch_contract")
    if not isinstance(launch_contract, dict):
        launch_contract = None
    return {
        "ok": bool(result.get("ok")),
        "status": "ok" if result.get("ok") else "blocked",
        "errors": errors,
        "warnings": warnings,
        "launch_contract": launch_contract,
        "next_command": (
            f"make validate-rubric PROJECT={project_dir.name} RUBRIC={_rel(rubric_path, repo)}"
        ),
    }


def _trace_local_health(
    *,
    project: str,
    source_preflight: dict[str, Any],
    source_preflight_blocking: list[str],
) -> dict[str, Any]:
    status = "needs_attention" if source_preflight_blocking else "ok"
    evidence_gaps = []
    if source_preflight_blocking:
        evidence_gaps.append(
            {
                "id": "source_preflight",
                "status": "needs_attention",
                "recovery_kind": LOCAL_VERIFICATION_RECOVERY_KIND,
                "recovery_channel": "source_preflight",
                "next_command": f"ztare project source-check --project {project} --json",
            }
        )
    return {
        "summary": {
            "overall_status": status,
            "component_count": 1,
            "mode": "trace_local",
            "source_preflight_status": source_preflight.get("status"),
            "source_preflight_blocking_count": len(source_preflight_blocking),
        },
        "evidence_gaps": evidence_gaps,
    }


def _packet_candidates(repo: Path, project_dir: Path, project: str) -> list[Path]:
    project_slug = _normalize_slug(project_dir.name or project)
    return [
        project_dir / "project_intake.json",
        project_dir / f"{project_slug}_intake.json",
        repo / f"{project_slug}_intake.json",
        repo / "examples" / "project_packets" / f"{project_slug}_intake.json",
        repo / "examples" / "project_packets" / f"ready_{project_slug}_intake.json",
        project_dir / "project_packet.json",
        project_dir / f"{project_slug}_packet.json",
        repo / f"{project_slug}_packet.json",
        repo / "examples" / "project_packets" / f"{project_slug}_packet.json",
        repo / "examples" / "project_packets" / f"ready_{project_slug}_packet.json",
        repo / "examples" / "substrate_packets" / f"{project_slug}_packet.json",
        repo / "examples" / "substrate_packets" / f"ready_{project_slug}_packet.json",
    ]


def _resolve_packet_path(
    *,
    packet: str | None,
    repo: Path,
    project_dir: Path,
    project: str,
) -> Path | None:
    if packet:
        candidate = Path(packet)
        if candidate.exists():
            return candidate.resolve()
        repo_candidate = repo / packet
        return repo_candidate.resolve() if repo_candidate.exists() else candidate.resolve()
    return _first_existing_path(_packet_candidates(repo, project_dir, project))


def _first_local_packet_ref_selector(payload: dict[str, Any]) -> str | None:
    for key in ("evidence_refs", "source_refs"):
        refs = payload.get(key)
        if not isinstance(refs, list):
            continue
        for idx, ref in enumerate(refs, start=1):
            if isinstance(ref, str) and ref.strip() and "://" not in ref:
                return f"{key}[{idx}]"
    return None


def _project_packet_falsifier_summary(
    path: Path,
    payload: dict[str, Any],
    *,
    repo: Path,
) -> dict[str, Any]:
    selector = _first_local_packet_ref_selector(payload)
    if selector is None:
        return {
            "required": False,
            "ok": True,
            "status": "skipped_no_local_refs",
            "remove_ref": None,
            "removed_ref": None,
            "errors": [],
            "falsified_errors": [],
        }
    try:
        result = validate_project_packet_falsifier(
            path,
            remove_ref=selector,
            repo_root=repo,
            require_source_preflight=False,
        )
    except SystemExit as exc:
        return {
            "required": True,
            "ok": False,
            "status": "error",
            "remove_ref": selector,
            "removed_ref": None,
            "errors": [str(exc)],
            "falsified_errors": [],
        }
    errors = list(result.get("errors") or [])
    falsified_errors: list[str] = []
    falsified = result.get("falsified")
    if isinstance(falsified, dict):
        falsified_errors.extend(str(error) for error in (falsified.get("errors") or []))
    return {
        "required": True,
        "ok": bool(result.get("ok")),
        "status": "passed" if result.get("ok") else "failed",
        "remove_ref": result.get("remove_ref"),
        "removed_ref": result.get("removed_ref") or result.get("removed_value"),
        "expected_error_fragment": result.get("expected_error_fragment"),
        "path_safety": result.get("path_safety") or {},
        "errors": errors,
        "falsified_errors": falsified_errors,
    }


def _project_packet_summary(
    *,
    packet: str | None,
    repo: Path,
    project_dir: Path,
    project: str,
    rubric: str | None,
) -> dict[str, Any]:
    path = _resolve_packet_path(packet=packet, repo=repo, project_dir=project_dir, project=project)
    if path is None:
        return {
            "available": False,
            "path": None,
            "status": "not_found",
            "ok": False,
            "errors": [],
            "warnings": [],
            "packet_id": None,
            "matches_project": False,
            "matches_rubric": False if rubric else None,
        }
    if not path.exists():
        return {
            "available": True,
            "path": _rel(path, repo),
            "status": "missing_packet_file",
            "ok": False,
            "errors": ["project-intake file does not exist"],
            "warnings": [],
            "packet_id": None,
            "matches_project": False,
            "matches_rubric": False if rubric else None,
        }

    try:
        payload = load_project_packet(path)
    except SystemExit as exc:
        return {
            "available": True,
            "path": _rel(path, repo),
            "status": "invalid_json",
            "ok": False,
            "errors": [str(exc)],
            "warnings": [],
            "packet_id": None,
            "matches_project": False,
            "matches_rubric": False if rubric else None,
        }

    validation = validate_project_packet(
        payload,
        base_dir=path.parent,
        repo_root=repo,
        require_source_preflight=False,
    )
    errors = list(validation.get("errors") or [])
    warnings = list(validation.get("warnings") or [])
    packet_project = str(payload.get("project") or "")
    packet_rubric = str(payload.get("rubric") or "")
    project_matches = packet_project in {project, _normalize_slug(project), project_dir.name}
    rubric_matches = None
    if rubric:
        rubric_matches = packet_rubric in {rubric, _normalize_slug(rubric)}
    if not project_matches:
        errors.append("project intake does not match traced project")
    if rubric and not rubric_matches:
        errors.append("project intake does not match traced rubric")
    falsifier = _project_packet_falsifier_summary(path, payload, repo=repo)
    if validation.get("ok") and falsifier["required"] and not falsifier["ok"]:
        errors.append("project-intake missing-ref falsifier did not fire")

    return {
        "available": True,
        "path": _rel(path, repo),
        "status": "valid_packet" if validation.get("ok") and not errors else "invalid_packet",
        "ok": validation.get("ok") and not errors,
        "errors": errors,
        "warnings": warnings,
        "packet_id": payload.get("packet_id"),
        "project": packet_project,
        "rubric": packet_rubric,
        "task": payload.get("task"),
        "bounded_claim": payload.get("bounded_claim"),
        "source_ref_count": len(payload.get("source_refs") or []),
        "evidence_ref_count": len(payload.get("evidence_refs") or []),
        "non_claim_count": len(payload.get("non_claims") or []),
        "next_falsifier_present": bool(str(payload.get("next_falsifier") or "").strip()),
        "evidence_gap_contract_count": len(validation.get("evidence_gap_contracts") or []),
        "evidence_gap_contracts": validation.get("evidence_gap_contracts") or [],
        "evidence_gap_recovery_policy": validation.get("evidence_gap_recovery_policy") or {},
        "missing_ref_falsifier": falsifier,
        "expected_command": payload.get("expected_command"),
        "matches_project": project_matches,
        "matches_rubric": rubric_matches,
    }


def _readiness_from_missing(
    *,
    project_packet: dict[str, Any],
    missing: list[str],
) -> tuple[str, list[str], list[str]]:
    history_missing = [item for item in missing if item == "eval_history"]
    blocking_missing = [item for item in missing if item != "eval_history"]
    surface_blockers = [item for item in blocking_missing if item != "project_packet"]

    if "out_of_loop_evidence_recovery" in blocking_missing:
        return "blocked_on_out_of_loop_prep", blocking_missing, history_missing
    non_launch_surface_blockers = [
        item for item in surface_blockers if item != "launch_preflight"
    ]
    if non_launch_surface_blockers:
        return "blocked_on_project_surfaces", blocking_missing, history_missing
    if "launch_preflight" in blocking_missing:
        return "blocked_on_launch_preflight", blocking_missing, history_missing
    if project_packet["available"] and not project_packet["ok"]:
        return "blocked_on_project_packet", blocking_missing, history_missing
    if not project_packet["available"]:
        return "traceable_but_no_project_packet", blocking_missing, history_missing
    if history_missing:
        return "ready_for_first_in_loop_run", blocking_missing, history_missing
    return "ready_for_in_loop_candidate", blocking_missing, history_missing


def _kernel_entry_contract(
    *,
    project: str,
    rubric: str | None,
    readiness: str,
    blocking_missing: list[str],
    history_missing: list[str],
    project_packet: dict[str, Any],
    source_preflight: dict[str, Any],
    launch_preflight: dict[str, Any],
    graph_rd_actions: list[dict[str, str]],
    recovery_actions: list[dict[str, str]],
    route_preview: dict[str, Any],
) -> dict[str, Any]:
    recovery_by_id = {
        str(action.get("id")): action
        for action in recovery_actions
        if isinstance(action, dict) and action.get("id")
    }
    source_index_recovery_command = recovery_by_id.get("source_index", {}).get(
        "next_command"
    )
    evidence_prepare_recovery_command = recovery_by_id.get("evidence_prepare", {}).get(
        "next_command"
    )
    evidence_replay_recovery_command = recovery_by_id.get("evidence_replay", {}).get(
        "next_command"
    )
    evidence_output_bind_recovery_command = recovery_by_id.get(
        "evidence_output_bind", {}
    ).get("next_command")
    source_index_surface_ids = {
        "source_index",
        "source_index_stale",
        "source_index_unverified",
        "source_index_receipt_stale",
        "workspace_meta",
    }
    evidence_prepare_surface_ids = {
        "evidence_compile_provenance",
        "evidence_compile_stale",
        "evidence_compile_unverified",
        "evidence_output_stale",
    }
    evidence_output_bind_surface_ids = {
        "evidence_output_unverified",
    }
    evidence_replay_surface_ids = {
        "evidence_replay_stale",
    }
    prediction_surface_ids = {
        "prediction_authority_claim_invalid",
    }
    blockers = [
        {
            "id": item,
            "recovery_channel": (
                "project_packet"
                if item == "project_packet"
                else "source_preflight"
                if item == "source_preflight"
                else "launch_preflight"
                if item == "launch_preflight"
                else "out_of_loop_evidence_recovery"
                if item == "out_of_loop_evidence_recovery"
                else "evidence_prepare"
                if item in evidence_prepare_surface_ids
                else "evidence_output_bind"
                if item in evidence_output_bind_surface_ids
                else "evidence_replay"
                if item in evidence_replay_surface_ids
                else "prediction_contracts"
                if item in prediction_surface_ids
                else "project_surface"
            ),
            "next_command": (
                recovery_by_id.get(item, {}).get("next_command")
                or (
                    source_index_recovery_command
                    if item in source_index_surface_ids
                    else None
                )
                or (
                    evidence_prepare_recovery_command
                    if item in evidence_prepare_surface_ids
                    else None
                )
                or (
                    evidence_output_bind_recovery_command
                    if item in evidence_output_bind_surface_ids
                    else None
                )
                or (
                    evidence_replay_recovery_command
                    if item in evidence_replay_surface_ids
                    else None
                )
            ),
        }
        for item in blocking_missing
    ]
    packet_falsifier = project_packet.get("missing_ref_falsifier")
    if not isinstance(packet_falsifier, dict):
        packet_falsifier = {}
    source_ready = bool(source_preflight.get("ok")) and not list(
        source_preflight.get("blocking") or []
    )
    launch_ready = bool(launch_preflight.get("ok"))
    packet_ready = bool(project_packet.get("available")) and bool(project_packet.get("ok"))
    if not packet_ready and not any(row["id"] == "project_packet" for row in blockers):
        blockers.append(
            {
                "id": "project_packet",
                "recovery_channel": "project_packet",
                "next_command": recovery_by_id.get("project_packet", {}).get("next_command"),
            }
        )
    if not source_ready and not any(row["id"] == "source_preflight" for row in blockers):
        next_commands = source_preflight.get("next_commands") or []
        blockers.append(
            {
                "id": "source_preflight",
                "recovery_channel": "source_preflight",
                "next_command": (
                    recovery_by_id.get("source_preflight", {}).get("next_command")
                    or (str(next_commands[0]) if next_commands else None)
                    or f"ztare project source-check --project {project} --json"
                ),
            }
        )
    if not launch_ready and not any(row["id"] == "launch_preflight" for row in blockers):
        blockers.append(
            {
                "id": "launch_preflight",
                "recovery_channel": "launch_preflight",
                "next_command": recovery_by_id.get("launch_preflight", {}).get("next_command"),
            }
        )
    blockers = [_canonicalized_blocker(row) for row in blockers]
    can_enter = (
        bool(route_preview.get("can_run_now"))
        and packet_ready
        and source_ready
        and launch_ready
    )
    in_loop_focus_receipts = [
        action
        for action in graph_rd_actions
        if isinstance(action, dict)
        and action.get("action_type") == "in_loop_focus_receipt"
        and action.get("work_mode") == "in_loop"
    ]
    launch_contract = launch_preflight.get("launch_contract")
    if not isinstance(launch_contract, dict):
        launch_contract = None
    return {
        "schema": "ztare-kernel-entry-contract-v1",
        "entry_surface": "in_loop_autoresearch",
        "project": project,
        "rubric": rubric,
        "intake_id": project_packet.get("packet_id"),
        "intake_path": project_packet.get("path"),
        "packet_id": project_packet.get("packet_id"),
        "packet_path": project_packet.get("path"),
        "status": "ready" if can_enter else "blocked",
        "can_enter_kernel": can_enter,
        "readiness": readiness,
        "readiness_canonical": _canonical_intake_id(readiness),
        "submission_contract": launch_contract,
        "allowed_work_modes": (
            ["inspection_only", "in_loop_autoresearch_gate"]
            if can_enter
            else ["inspection_only", "pre_kernel_project_prep"]
        ),
        "disallowed_work_modes": [
            "rd_out_of_loop_execution",
            "untyped_source_to_kernel_entry",
            "project_prep_queue_as_research_execution",
        ],
        "prerequisites": {
            "project_intake_ok": packet_ready,
            "project_intake_matches_project": bool(project_packet.get("matches_project")),
            "project_intake_matches_rubric": (
                project_packet.get("matches_rubric")
                if project_packet.get("matches_rubric") is not None
                else None
            ),
            "project_packet_ok": packet_ready,
            "project_packet_matches_project": bool(project_packet.get("matches_project")),
            "project_packet_matches_rubric": (
                project_packet.get("matches_rubric")
                if project_packet.get("matches_rubric") is not None
                else None
            ),
            "missing_ref_falsifier_ok": (
                bool(packet_falsifier.get("ok"))
                if packet_falsifier.get("required")
                else True
            ),
            "source_preflight_ok": source_ready,
            "source_preflight_status": source_preflight.get("status"),
            "source_evidence_count": source_preflight.get("source_evidence_count", 0),
            "launch_preflight_ok": launch_ready,
            "launch_preflight_status": launch_preflight.get("status"),
            "submission_contract_kind": (
                launch_contract.get("submission_contract_kind")
                if launch_contract
                else None
            ),
            "requires_i_model": (
                launch_contract.get("requires_i_model") if launch_contract else None
            ),
            "registered_substrate_abi": (
                launch_contract.get("registered_substrate_abi")
                if launch_contract
                else None
            ),
        },
        "blockers": blockers,
        "history_debt": history_missing,
        "in_loop_focus_receipts": in_loop_focus_receipts if can_enter else [],
        "withheld_in_loop_focus_receipts": [] if can_enter else in_loop_focus_receipts,
        "entry_command": route_preview.get("route_command") if can_enter else None,
        "preflight_command": route_preview.get("preflight_command") if can_enter else None,
        "run_command": route_preview.get("run_command") if can_enter else None,
        "inspection_command": (
            "ztare autoresearch trace --project "
            f"{project}"
            + (f" --rubric {rubric}" if rubric else "")
            + (
                f" --intake {project_packet['path']}"
                if project_packet.get("path")
                else ""
            )
            + " --json"
        ),
    }


def _recovery_command_by_id(
    recovery_actions: list[dict[str, str]],
    *ids: str,
) -> str | None:
    wanted = set(ids)
    for action in recovery_actions:
        if str(action.get("id") or "") in wanted:
            return action.get("next_command")
    return None


def _source_claim_graph_receipt(graph_carriers: list[dict[str, Any]]) -> dict[str, Any]:
    for graph in graph_carriers:
        if graph.get("graph_kind") == "source_claim_graph":
            receipt = graph.get("decision_receipt")
            return receipt if isinstance(receipt, dict) else {}
    return {}


def _latest_mutator_briefing_records(workspace: Path, *, repo: Path) -> dict[str, Any]:
    latest: tuple[int, Path] | None = None
    for path in workspace.glob("mutator_briefing_iter_*_records.json"):
        parts = path.stem.split("_")
        if len(parts) < 5:
            continue
        try:
            iter_index = int(parts[3])
        except ValueError:
            continue
        if latest is None or iter_index > latest[0]:
            latest = (iter_index, path)
    if latest is None:
        return {
            "available": False,
            "status": "missing",
            "iter_index": None,
            "path": None,
            "record_count": 0,
            "providers": [],
            "graph_focus_record_count": 0,
            "graph_focus_gap_ids": [],
            "graph_focus_targets": [],
        }
    iter_index, path = latest
    payload = _read_json(path)
    records = payload.get("records")
    if not isinstance(records, list):
        records = []
    providers = sorted(
        {
            str(row.get("provider") or "").strip()
            for row in records
            if isinstance(row, dict) and str(row.get("provider") or "").strip()
        }
    )
    graph_focus_records = [
        row
        for row in records
        if isinstance(row, dict)
        and (
            row.get("provider") == "graph_focus_receipt"
            or row.get("record_type") == "graph_focus_receipt"
        )
    ]
    gap_ids: list[str] = []
    targets: list[str] = []
    for row in graph_focus_records:
        for value, dest in (
            (row.get("gap_ids"), gap_ids),
            (row.get("targets"), targets),
        ):
            for item in str(value or "").split(","):
                item = item.strip()
                if item and item not in dest:
                    dest.append(item)
    return {
        "available": True,
        "status": "available",
        "iter_index": iter_index,
        "path": _rel(path, repo),
        "record_count": len(records),
        "providers": providers,
        "graph_focus_record_count": len(graph_focus_records),
        "graph_focus_gap_ids": gap_ids,
        "graph_focus_targets": targets,
    }


def _carrier_chain_summary(
    *,
    project_dir: Path,
    raw_file_count: int,
    source_preflight: dict[str, Any],
    source_preflight_blocking: list[str],
    source_index: dict[str, Any],
    source_index_receipt_summary: dict[str, Any],
    source_index_freshness: dict[str, Any],
    compile_provenance: Path | None,
    compile_provenance_freshness: dict[str, Any],
    evidence_path: Path,
    evidence_output_binding: dict[str, Any],
    evidence_replay: dict[str, Any],
    claim_support: dict[str, Any],
    graph_carriers: list[dict[str, Any]],
    project_packet: dict[str, Any],
    launch_preflight: dict[str, Any],
    mutator_briefing: dict[str, Any],
    prediction_summary: dict[str, Any],
    eval_history: Path,
    loop_admission: dict[str, Any],
    recovery_actions: list[dict[str, str]],
    missing: list[str],
) -> list[dict[str, Any]]:
    missing_set = set(missing)
    source_graph_receipt = _source_claim_graph_receipt(graph_carriers)
    evidence_gap_blocked = "out_of_loop_evidence_recovery" in missing_set
    if source_graph_receipt:
        gap_status = (
            "active_public_gap"
            if evidence_gap_blocked
            else str(source_graph_receipt.get("effect") or "available")
        )
    else:
        gap_status = "not_reported"
    return [
        {
            "surface": "project_dir",
            "status": "present" if project_dir.exists() else "missing",
            "blocking": "project_dir" in missing_set,
            "next_command": _recovery_command_by_id(recovery_actions, "project_dir"),
        },
        {
            "surface": "raw_sources",
            "status": "present" if raw_file_count > 0 else "missing",
            "count": raw_file_count,
            "blocking": "raw_sources" in missing_set or "raw_or_evidence" in missing_set,
            "next_command": _recovery_command_by_id(recovery_actions, "raw_sources"),
        },
        {
            "surface": "source_preflight",
            "status": source_preflight.get("status") or "not_checked",
            "blocking": bool(source_preflight_blocking),
            "blocking_items": source_preflight_blocking,
            "next_command": _recovery_command_by_id(recovery_actions, "source_preflight"),
        },
        {
            "surface": "source_index",
            "status": (
                str(source_index_freshness.get("status") or "present")
                if source_index
                else "missing"
            ),
            "count": len(source_index.get("sources", [])),
            "blocking": any(
                item in missing_set
                for item in {"source_index", "source_index_stale", "source_index_unverified"}
            ),
            "next_command": _recovery_command_by_id(recovery_actions, "source_index"),
        },
        {
            "surface": "source_index_receipt",
            "status": source_index_receipt_summary.get("status") or "missing",
            "blocking": "source_index_receipt_stale" in missing_set,
            "next_command": _recovery_command_by_id(recovery_actions, "source_index")
            or (
                f"ztare project source-index --project {project_dir.name}"
                if source_index
                and (source_index_receipt_summary.get("status") or "missing") == "missing"
                else None
            ),
        },
        {
            "surface": "compile_provenance",
            "status": (
                str(compile_provenance_freshness.get("status") or "present")
                if compile_provenance is not None
                else "missing"
            ),
            "blocking": any(
                item in missing_set
                for item in {
                    "evidence_compile_provenance",
                    "evidence_compile_stale",
                    "evidence_compile_unverified",
                }
            ),
            "next_command": _recovery_command_by_id(recovery_actions, "evidence_prepare"),
        },
        {
            "surface": "evidence_output",
            "status": (
                str(evidence_output_binding.get("status") or "present")
                if evidence_path.exists()
                else "missing"
            ),
            "binding_source": evidence_output_binding.get("binding_source"),
            "blocking": any(
                item in missing_set
                for item in {"evidence_output_unverified", "evidence_output_stale"}
            ),
            "next_command": _recovery_command_by_id(
                recovery_actions,
                "evidence_output_bind",
                "evidence_prepare",
            ),
        },
        {
            "surface": "evidence_replay",
            "status": str(evidence_replay.get("status") or "missing_manifest"),
            "required": bool(evidence_replay.get("required")),
            "blocking": "evidence_replay_stale" in missing_set,
            "next_command": _recovery_command_by_id(
                recovery_actions,
                "evidence_replay",
                "evidence_prepare",
            ),
        },
        {
            "surface": "claim_support",
            "status": claim_support.get("status") or "not_checked",
            "blocking": False,
            "claim_count": claim_support.get("claim_count", 0),
            "weak_or_unsourced_count": claim_support.get("weak_or_unsourced_count", 0),
            "source_context_blocked_count": claim_support.get(
                "source_context_blocked_count",
                0,
            ),
            "status_counts": claim_support.get("status_counts", {}),
            "source_context_status_counts": claim_support.get(
                "source_context_status_counts",
                {},
            ),
            "next_command": f"ztare project claim-support --project {project_dir.name} --json",
        },
        {
            "surface": "evidence_gaps",
            "status": gap_status,
            "blocking": evidence_gap_blocked,
            "decision_receipt": source_graph_receipt or None,
            "next_command": _recovery_command_by_id(
                recovery_actions,
                "out_of_loop_evidence_recovery",
            ),
        },
        {
            "surface": "project_intake",
            "legacy_surface": "project_packet",
            "status": project_packet.get("status") or "not_found",
            "blocking": "project_packet" in missing_set or not bool(project_packet.get("ok")),
            "next_command": _recovery_command_by_id(recovery_actions, "project_packet"),
        },
        {
            "surface": "launch_preflight",
            "status": launch_preflight.get("status") or "not_checked",
            "blocking": "launch_preflight" in missing_set,
            "next_command": _recovery_command_by_id(recovery_actions, "launch_preflight"),
        },
        {
            "surface": "mutator_briefing",
            "status": mutator_briefing.get("status") or "missing",
            "blocking": False,
            "record_count": mutator_briefing.get("record_count", 0),
            "graph_focus_record_count": mutator_briefing.get(
                "graph_focus_record_count",
                0,
            ),
            "graph_focus_gap_ids": mutator_briefing.get("graph_focus_gap_ids", []),
            "graph_focus_targets": mutator_briefing.get("graph_focus_targets", []),
        },
        {
            "surface": "prediction_contracts",
            "status": prediction_summary.get("status") or "no_prediction_contracts",
            "blocking": "prediction_authority_claim_invalid" in missing_set,
            "row_count": prediction_summary.get("row_count", 0),
            "scoreable_count": prediction_summary.get("scoreable_count", 0),
            "measurement_policy": prediction_summary.get(
                "measurement_policy",
                "score_only_no_routing",
            ),
            "next_command": _recovery_command_by_id(
                recovery_actions,
                "prediction_authority_claim_invalid",
            ),
        },
        {
            "surface": "eval_history",
            "status": "present" if eval_history.exists() else "missing",
            "blocking": False,
            "history_debt": "eval_history" in missing_set,
        },
        {
            "surface": "loop_admission",
            "status": "available" if loop_admission.get("available") else "missing",
            "blocking": False,
            "receipt_count": loop_admission.get("receipt_count", 0),
        },
    ]


def build_autoresearch_trace(
    *,
    project: str,
    rubric: str | None = None,
    model: str = "gemini",
    evidence_search_backend: str = "auto",
    packet: str | None = None,
    repo: Path = REPO,
    full_health: bool = False,
) -> dict[str, Any]:
    repo = repo.resolve()
    project_dir = _project_dir(repo, project)
    rubric_resolved = _rubric_path(repo, rubric)
    workspace = project_dir / "workspace"
    raw_dir = project_dir / "raw"
    evidence_path = project_dir / "evidence.txt"
    workspace_meta_path = workspace / "workspace_meta.json"
    source_index_path = workspace / "source_index.json"
    source_index_receipt_path = workspace / "source_index_receipt.json"
    evidence_output_binding_receipt_path = workspace / EVIDENCE_OUTPUT_BINDING_RECEIPT_FILENAME
    compile_provenance_candidates = [
        project_dir / "compiled_evidence_provenance.json",
        workspace / "evidence_compile_provenance.json",
    ]
    compile_provenance = _first_existing_path(compile_provenance_candidates)
    compile_provenance_read_path = compile_provenance or compile_provenance_candidates[0]
    compile_provenance_payload = _read_json(compile_provenance_read_path)
    project_packet = _project_packet_summary(
        packet=packet,
        repo=repo,
        project_dir=project_dir,
        project=project,
        rubric=rubric,
    )
    workspace_meta = _read_json(workspace_meta_path)
    source_index = _read_json(source_index_path)
    source_index_receipt = _read_json(source_index_receipt_path)
    evidence_output_binding_receipt = _read_json(evidence_output_binding_receipt_path)
    source_index_receipt_summary = _source_index_receipt_summary(
        receipt=source_index_receipt,
        receipt_path=source_index_receipt_path,
        source_index_path=source_index_path,
        workspace_meta_path=workspace_meta_path,
        repo=repo,
    )
    derived_constraints = _read_json(workspace / "derived_constraints.json")
    eval_history = workspace / "eval_history.jsonl"
    latest_evidence_gaps = workspace / "latest_evidence_gaps.json"
    recent_loop = _recent_loop_summary(workspace, repo=repo)
    raw_file_count = _count_raw_files(raw_dir)
    source_preflight = _source_preflight_for_trace(project_dir=project_dir, repo=repo)
    source_preflight_blocking = _source_preflight_blocks_kernel(source_preflight)
    source_index_freshness = artifact_source_freshness(
        source_preflight=source_preflight,
        artifact_sources=source_index.get("sources", []),
        artifact_name="workspace/source_index.json",
        project_dir=project_dir,
        repo=repo,
    )
    compile_provenance_freshness = artifact_source_freshness(
        source_preflight=source_preflight,
        artifact_sources=compile_provenance_payload.get("sources", []),
        artifact_name=_rel(compile_provenance_read_path, repo),
        project_dir=project_dir,
        repo=repo,
    )
    evidence_output_binding = _compiled_evidence_output_binding(
        provenance=compile_provenance_payload,
        evidence_path=evidence_path,
        repo=repo,
        project_dir=project_dir,
        binding_receipt=evidence_output_binding_receipt,
        binding_receipt_path=evidence_output_binding_receipt_path,
    )
    evidence_replay, evidence_replay_required = _trace_evidence_replay_report(
        project_dir=project_dir,
        provenance=compile_provenance_payload,
        repo=repo,
    )
    evidence_readiness = _trace_evidence_readiness(
        source_index_freshness=source_index_freshness,
        compile_provenance_freshness=compile_provenance_freshness,
        evidence_output_binding=evidence_output_binding,
        evidence_replay=evidence_replay,
    )
    claim_support = build_claim_support_audit(
        project_dir,
        evidence_readiness=evidence_readiness,
    )
    if rubric_resolved is not None:
        launch_preflight = _launch_preflight_for_trace(
            project_dir=project_dir,
            rubric_path=rubric_resolved,
            repo=repo,
        )
    else:
        launch_preflight = {
            "ok": True,
            "status": "not_checked_without_resolved_rubric",
            "errors": [],
            "warnings": [],
            "launch_contract": None,
            "next_command": None,
        }
    effective_rubric_data = None
    if rubric_resolved is not None:
        raw_rubric_data = _read_json(rubric_resolved)
        if raw_rubric_data:
            effective_rubric_data = apply_rubric_mode_defaults(dict(raw_rubric_data))
    probability_dag_carrier = build_probability_dag_graph_carrier(
        project_dir=project_dir,
        workspace_dir=workspace,
        repo=repo,
        rubric_data=effective_rubric_data,
    )
    source_claim_carrier = build_source_claim_graph_carrier(
        project_dir=project_dir,
        workspace_dir=workspace,
        repo=repo,
        intake_gap_contracts=project_packet.get("evidence_gap_contracts") or [],
        intake_gap_contract_source=str(project_packet.get("path") or ""),
        intake_gap_recovery_policy=project_packet.get("evidence_gap_recovery_policy") or {},
    )
    graph_carriers = []
    if probability_dag_carrier is not None:
        graph_carriers.append(summarize_probability_dag_graph_carrier(probability_dag_carrier))
    if source_claim_carrier is not None:
        graph_carriers.append(summarize_source_claim_graph_carrier(source_claim_carrier))
    graph_rd_actions = graph_carrier_action_rows(graph_carriers)
    prediction_summary = summarize_prediction_contracts(
        project_dir=project_dir,
        workspace_dir=workspace,
        repo=repo,
    )
    prediction_authority_issues = _prediction_authority_issue_codes(prediction_summary)

    projection_summary: dict[str, Any] = {"available": False}
    if eval_history.exists():
        try:
            projection = build_projection(project_dir)
            projection_summary = {
                "available": True,
                "node_count": projection.summary.node_count,
                "admitted_count": projection.summary.admitted_count,
                "rejected_count": projection.summary.rejected_count,
                "negative_constraint_count": projection.summary.negative_constraint_count,
                "open_frontier_constraint_count": projection.summary.open_frontier_constraint_count,
            }
        except Exception as exc:
            projection_summary = {
                "available": False,
                "error": f"{type(exc).__name__}: {exc}",
            }

    if full_health:
        health = build_autoresearch_kernel_health(
            repo=repo,
            project=project,
            workspace=str(workspace) if workspace.exists() else None,
            rubric=str(rubric_resolved) if rubric_resolved else rubric,
            packet=packet,
        )
    else:
        health = _trace_local_health(
            project=project,
            source_preflight=source_preflight,
            source_preflight_blocking=source_preflight_blocking,
        )

    missing: list[str] = []
    if not project_dir.exists():
        missing.append("project_dir")
    if not raw_dir.exists() and not evidence_path.exists():
        missing.append("raw_or_evidence")
    elif raw_file_count == 0:
        missing.append("raw_sources")
    if raw_file_count > 0 and not source_index:
        missing.append("source_index")
    if source_index and source_index_freshness.get("status") == "stale":
        missing.append("source_index_stale")
    if (
        not source_preflight_blocking
        and source_index
        and source_binding_contract_blocks_kernel(source_index_freshness)
        and "source_index_stale" not in missing
    ):
        missing.append("source_index_unverified")
    if (
        source_index_receipt_summary.get("exists")
        and not source_index_receipt_summary.get("verified")
    ):
        missing.append("source_index_receipt_stale")
    if raw_file_count > 0 and not workspace_meta:
        missing.append("workspace_meta")
    if evidence_path.exists() and compile_provenance is None:
        missing.append("evidence_compile_provenance")
    if (
        compile_provenance is not None
        and compile_provenance_freshness.get("status") == "stale"
    ):
        missing.append("evidence_compile_stale")
    if (
        compile_provenance is not None
        and not source_preflight_blocking
        and source_binding_contract_blocks_kernel(compile_provenance_freshness)
        and "evidence_compile_stale" not in missing
    ):
        missing.append("evidence_compile_unverified")
    if evidence_output_binding.get("status") == "stale":
        missing.append("evidence_output_stale")
    if evidence_replay_required and not bool(evidence_replay.get("ok")):
        missing.append("evidence_replay_stale")
    if (
        compile_provenance is not None
        and not source_preflight_blocking
        and bool(compile_provenance_freshness.get("kernel_entry_ok"))
        and evidence_output_binding.get("status")
        in {"unverified", "unverified_missing_output_hash"}
    ):
        missing.append("evidence_output_unverified")
    if source_preflight_blocking:
        missing.append("source_preflight")
    if rubric and rubric_resolved is None:
        missing.append("rubric")
    if not bool(launch_preflight.get("ok")):
        missing.append("launch_preflight")
    if prediction_authority_issues:
        missing.append("prediction_authority_claim_invalid")
    if not eval_history.exists():
        missing.append("eval_history")
    if packet and not project_packet["ok"]:
        missing.append("project_packet")

    recovery_actions: list[dict[str, str]] = []
    if "project_dir" in missing:
        recovery_actions.append(
            {
                "id": "project_dir",
                "reason": "project directory is absent",
                "next_command": "ztare project new --help",
            }
        )
    if project_packet["status"] == "not_found" and rubric:
        recovery_actions.append(
            {
                "id": "project_packet",
                "reason": "create bounded project intake before treating the trace as an in-loop candidate",
                "next_command": (
                    f"ztare project walkthrough --project {project} --rubric {rubric} "
                    "--task '<bounded task>' --bounded-claim '<bounded claim>' "
                    f"--intake-out {project}_intake.json"
                ),
            }
        )
    elif project_packet["available"] and not project_packet["ok"]:
        recovery_actions.append(
            {
                "id": "project_packet",
                "reason": "fix the project-intake validation errors before run readiness",
                "next_command": f"ztare project intake validate --path {project_packet['path']}",
            }
        )
    if "raw_or_evidence" in missing or "raw_sources" in missing:
        if latest_evidence_gaps.exists():
            severity = _evidence_fetch_severity(
                latest_evidence_gaps,
                project_dir=project_dir,
            )
            recovery_actions.append(
                {
                    "id": "raw_sources",
                    "reason": "fetch public sources for recorded evidence gaps",
                    "next_command": (
                        f"make evidence-fetch PROJECT={project} SEVERITY={severity} "
                        f"MAX_FETCHES=3 MODEL={model} "
                        f"EVIDENCE_SEARCH_BACKEND={evidence_search_backend}"
                    ),
                }
            )
        else:
            recovery_actions.append(
                {
                    "id": "raw_sources",
                    "reason": (
                        "initialize the source-ingest surface, then add typed source "
                        "documents under the project raw directory"
                    ),
                    "next_command": _source_init_command(project=project, rubric=rubric),
                }
            )
    if source_preflight_blocking:
        recovery_actions.append(
            {
                "id": "source_preflight",
                "reason": "fix raw source typing before workspace update or evidence compilation",
                "next_command": f"ztare project source-check --project {project} --json",
            }
        )
    if raw_file_count > 0 and (
        "source_index" in missing
        or "source_index_stale" in missing
        or "source_index_unverified" in missing
        or "source_index_receipt_stale" in missing
        or "workspace_meta" in missing
    ):
        recovery_actions.append(
            {
                "id": "source_index",
                "reason": (
                    "write deterministic workspace source index and metadata "
                    "from typed raw sources"
                ),
                "next_command": f"ztare project source-index --project {project}",
            }
        )
    if not bool(launch_preflight.get("ok")):
        recovery_actions.append(
            {
                "id": "launch_preflight",
                "reason": "fix the same rubric/project preflight that make experiment-loop enforces",
                "next_command": str(
                    launch_preflight.get("next_command")
                    or f"make validate-rubric PROJECT={project} RUBRIC={rubric or project}"
                ),
            }
        )
    if raw_file_count > 0 and (
        "evidence_compile_provenance" in missing
        or "evidence_compile_stale" in missing
        or "evidence_compile_unverified" in missing
        or "evidence_output_stale" in missing
        or not evidence_path.exists()
    ):
        recovery_actions.append(
            {
                "id": "evidence_prepare",
                "reason": "refresh workspace source index and compiled evidence from raw sources",
                "next_command": f"make evidence-prepare PROJECT={project} MODEL={model}",
            }
        )
    if (
        "evidence_output_unverified" in missing
        and evidence_output_binding.get("status") == "unverified_missing_output_hash"
        and bool(compile_provenance_freshness.get("kernel_entry_ok"))
    ):
        recovery_actions.append(
            {
                "id": "evidence_output_bind",
                "reason": (
                    "bind current rendered evidence output bytes to fresh compile "
                    "provenance without recompiling evidence"
                ),
                "next_command": f"ztare project evidence-bind --project {project} --json",
            }
        )
    if "evidence_replay_stale" in missing:
        recovery_actions.append(
            {
                "id": "evidence_replay",
                "reason": (
                    "compiled evidence replay manifest is stale or invalid; "
                    "inspect the stale artifact, then rerun evidence preparation "
                    "after fixing the project inputs"
                ),
                "next_command": f"ztare project evidence-replay --project {project} --json",
            }
        )
    if prediction_authority_issues:
        recovery_actions.append(
            {
                "id": "prediction_authority_claim_invalid",
                "reason": (
                    "prediction rows claim forecast-pool, membrane, or routing "
                    "authority but fail authority checks: "
                    + ", ".join(prediction_authority_issues)
                ),
                "next_command": "ztare audit forecast-capability --json",
            }
        )

    out_of_loop_graph_actions = [
        action
        for action in graph_rd_actions
        if action.get("action_type") == "out_of_loop_evidence_recovery"
    ]
    if out_of_loop_graph_actions:
        missing.append("out_of_loop_evidence_recovery")
        severity = _evidence_fetch_severity(
            latest_evidence_gaps,
            project_dir=project_dir,
        )
        recovery_actions.append(
            {
                "id": "out_of_loop_evidence_recovery",
                "reason": out_of_loop_graph_actions[0].get(
                    "reason",
                    "source-claim graph selected evidence recovery before run readiness",
                ),
                "next_command": (
                    f"make evidence-fetch PROJECT={project} SEVERITY={severity} "
                    f"MAX_FETCHES=3 MODEL={model} "
                    f"EVIDENCE_SEARCH_BACKEND={evidence_search_backend}"
                ),
            }
        )

    readiness, blocking_missing, history_missing = _readiness_from_missing(
        project_packet=project_packet,
        missing=missing,
    )
    packet_expected_command = (
        str(project_packet.get("expected_command") or "").strip()
        if project_packet.get("ok")
        else ""
    )
    packet_expected_is_run = _is_autoresearch_run_command(packet_expected_command)
    effective_rubric = rubric or (
        str(project_packet.get("rubric") or "").strip()
        if project_packet.get("ok")
        else ""
    )
    packet_path = str(project_packet.get("path") or "").strip()
    trace_route_command = _packet_bound_command(
        packet_expected_command
        or (
            f"ztare autoresearch route --task '<bounded task>' --project {project} --rubric {effective_rubric}"
            if effective_rubric
            else ""
        ),
        packet_path=packet_path if project_packet.get("ok") else "",
    )
    trace_run_command = None
    trace_preflight_command = None
    if effective_rubric and project_packet.get("ok") and packet_path:
        if packet_expected_is_run:
            trace_run_command = _packet_bound_command(
                packet_expected_command,
                packet_path=packet_path,
            )
            trace_preflight_command = _with_bool_flag(
                trace_run_command,
                "--preflight-only",
            )
        else:
            trace_run_command = (
                "ztare autoresearch run "
                f"--project {_quote(project)} "
                f"--rubric {_quote(effective_rubric)} "
                f"--intake {_quote(packet_path)} --iters 10"
            )
            trace_preflight_command = (
                "ztare autoresearch run "
                f"--project {_quote(project)} "
                f"--rubric {_quote(effective_rubric)} "
                f"--intake {_quote(packet_path)} --preflight-only"
            )
    route_preview = {
        "available": bool(trace_route_command),
        "source": "project_intake" if packet_expected_command else ("trace_placeholder" if effective_rubric else None),
        "source_name": "project_intake" if packet_expected_command else ("trace_placeholder" if effective_rubric else None),
        "route_command": trace_route_command or None,
        "preflight_command": trace_preflight_command,
        "run_command": trace_run_command,
        "can_run_now": readiness in {"ready_for_first_in_loop_run", "ready_for_in_loop_candidate"},
    }
    if packet_expected_command:
        route_preview["legacy_source"] = "project_packet"
    kernel_entry = _kernel_entry_contract(
        project=project,
        rubric=rubric,
        readiness=readiness,
        blocking_missing=blocking_missing,
        history_missing=history_missing,
        project_packet=project_packet,
        source_preflight=source_preflight,
        launch_preflight=launch_preflight,
        graph_rd_actions=graph_rd_actions,
        recovery_actions=recovery_actions,
        route_preview=route_preview,
    )
    recent_loop = _recent_loop_with_current_kernel_entry(
        recent_loop,
        kernel_entry=kernel_entry,
    )
    loop_admission = _loop_admission_summary(recent_loop)
    preflight_admitted = _loop_preflight_admitted(loop_admission)
    mutator_briefing = _latest_mutator_briefing_records(workspace, repo=repo)
    carrier_chain = _carrier_chain_summary(
        project_dir=project_dir,
        raw_file_count=raw_file_count,
        source_preflight=source_preflight,
        source_preflight_blocking=source_preflight_blocking,
        source_index=source_index,
        source_index_receipt_summary=source_index_receipt_summary,
        source_index_freshness=source_index_freshness,
        compile_provenance=compile_provenance,
        compile_provenance_freshness=compile_provenance_freshness,
        evidence_path=evidence_path,
        evidence_output_binding=evidence_output_binding,
        evidence_replay=evidence_replay,
        claim_support=claim_support,
        graph_carriers=graph_carriers,
        project_packet=project_packet,
        launch_preflight=launch_preflight,
        mutator_briefing=mutator_briefing,
        prediction_summary=prediction_summary,
        eval_history=eval_history,
        loop_admission=loop_admission,
        recovery_actions=recovery_actions,
        missing=missing,
    )

    next_commands: list[str] = []
    next_command_seen: set[str] = set()

    def append_next_command(command: Any) -> None:
        item = str(command or "").strip()
        if not item or item in next_command_seen:
            return
        next_command_seen.add(item)
        next_commands.append(item)

    for action in recovery_actions:
        append_next_command(action.get("next_command"))
    if kernel_entry["can_enter_kernel"]:
        if (
            kernel_entry.get("entry_command")
            and kernel_entry.get("entry_command") != kernel_entry.get("run_command")
        ):
            append_next_command(kernel_entry["entry_command"])
        if kernel_entry.get("preflight_command") and not preflight_admitted:
            append_next_command(kernel_entry["preflight_command"])
        if kernel_entry["run_command"]:
            append_next_command(kernel_entry["run_command"])
    if eval_history.exists():
        append_next_command(f"ztare autoresearch projection --project {project}")
    if recent_loop.get("next_command"):
        append_next_command(recent_loop["next_command"])
    append_next_command(
        "ztare autoresearch health --project "
        f"{project}"
        + (f" --rubric {rubric}" if rubric else "")
        + (f" --intake {_quote(packet_path)}" if packet_path else "")
        + " --json"
    )
    plan_preview = build_autoresearch_plan_preview(
        project=project,
        rubric=rubric,
        route_command=route_preview.get("route_command"),
        preflight_command=route_preview.get("preflight_command"),
        run_command=route_preview.get("run_command"),
        can_run_now=bool(route_preview.get("can_run_now")),
        preflight_admitted=preflight_admitted,
        missing=missing,
        blocking_missing=blocking_missing,
        source=route_preview.get("source_name") or route_preview.get("source"),
        provider_failure_observed=bool(recent_loop.get("provider_failure_observed")),
    )
    review_artifacts = _review_artifacts_for_project(project_dir, repo=repo)

    return {
        "schema": "ztare-autoresearch-trace-v1",
        "project": project,
        "project_dir": str(project_dir),
        "rubric": rubric,
        "rubric_path": str(rubric_resolved) if rubric_resolved else None,
        "status": "complete_trace" if not missing else "partial_trace",
        "readiness": readiness,
        "readiness_canonical": _canonical_intake_id(readiness),
        "missing": missing,
        "blocking_missing": blocking_missing,
        "history_missing": history_missing,
        "project_intake": _project_intake_alias(project_packet),
        "project_packet": project_packet,
        "review_artifacts": review_artifacts,
        "route_preview": route_preview,
        "plan_preview": plan_preview,
        "kernel_entry": kernel_entry,
        "loop_admission": loop_admission,
        "carrier_chain": carrier_chain,
        "surfaces": {
            "project_dir_exists": project_dir.exists(),
            "raw_file_count": raw_file_count,
            "evidence_exists": evidence_path.exists(),
            "evidence_sha256": _sha256_file(evidence_path),
            "compile_provenance_exists": compile_provenance is not None,
            "compile_provenance_path": (
                str(compile_provenance) if compile_provenance is not None else None
            ),
            "compile_source_count": _read_json(compile_provenance_read_path).get("source_count"),
            "workspace_meta_exists": bool(workspace_meta),
            "workspace_merge_status": workspace_meta.get("merge_status"),
            "workspace_source_count": workspace_meta.get("source_count"),
            "source_index_exists": bool(source_index),
            "source_index_count": len(source_index.get("sources", [])),
            "source_index_receipt": source_index_receipt_summary,
            "source_index_freshness": source_index_freshness,
            "evidence_compile_freshness": compile_provenance_freshness,
            "evidence_output_binding": evidence_output_binding,
            "evidence_replay": evidence_replay,
            "evidence_readiness": evidence_readiness,
            "claim_support": claim_support,
            "evidence_search_backend_selector": evidence_search_backend,
            "source_preflight_ok": bool(source_preflight.get("ok")),
            "source_preflight_status": source_preflight.get("status"),
            "source_preflight_blocking": source_preflight.get("blocking", []),
            "source_preflight_warnings": source_preflight.get("warnings", []),
            "source_evidence_count": source_preflight.get("source_evidence_count", 0),
            "untyped_source_count": source_preflight.get("untyped_source_count", 0),
            "launch_preflight_ok": bool(launch_preflight.get("ok")),
            "launch_preflight_status": launch_preflight.get("status"),
            "launch_preflight_errors": launch_preflight.get("errors", []),
            "launch_preflight_warnings": launch_preflight.get("warnings", []),
            "launch_contract": launch_preflight.get("launch_contract"),
            "launch_submission_contract_kind": (
                (launch_preflight.get("launch_contract") or {}).get(
                    "submission_contract_kind"
                )
                if isinstance(launch_preflight.get("launch_contract"), dict)
                else None
            ),
            "launch_requires_i_model": (
                (launch_preflight.get("launch_contract") or {}).get("requires_i_model")
                if isinstance(launch_preflight.get("launch_contract"), dict)
                else None
            ),
            "launch_registered_substrate_abi": (
                (launch_preflight.get("launch_contract") or {}).get(
                    "registered_substrate_abi"
                )
                if isinstance(launch_preflight.get("launch_contract"), dict)
                else None
            ),
            "mutator_briefing": mutator_briefing,
            "derived_constraints_exists": bool(derived_constraints),
            "confirmed_constraint_count": int(
                derived_constraints.get("confirmed_constraint_count") or 0
            ),
            "provisional_constraint_count": int(
                derived_constraints.get("provisional_constraint_count") or 0
            ),
            "eval_history_exists": eval_history.exists(),
            "eval_history_rows": _eval_history_rows(eval_history),
        },
        "projection": projection_summary,
        "recent_loop": recent_loop,
        "graph_carriers": graph_carriers,
        "graph_rd_actions": graph_rd_actions,
        "prediction_summary": prediction_summary,
        "health_summary": health.get("summary", {}),
        "health_evidence_gaps": [
            {
                "id": row.get("id"),
                "status": row.get("status"),
                "recovery_kind": row.get("recovery_kind"),
                "recovery_channel": row.get("recovery_channel"),
                "next_command": row.get("next_command"),
            }
            for row in health.get("evidence_gaps", [])
            if isinstance(row, dict)
        ],
        "recovery_actions": recovery_actions,
        "next_commands": next_commands,
    }


def _table_cell(value: Any, *, max_len: int = 72) -> str:
    if value is None or value == "":
        return "-"
    if isinstance(value, bool):
        text = "yes" if value else "no"
    elif isinstance(value, (list, tuple, set)):
        text = ",".join(str(item) for item in value)
    elif isinstance(value, dict):
        text = json.dumps(value, sort_keys=True, separators=(",", ":"))
    else:
        text = str(value)
    text = " ".join(text.split())
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rstrip() + "..."


def _review_artifacts_for_project(project_dir: Path, *, repo: Path) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    candidates = [
        ("claim_summary", project_dir / "public" / "CLAIM_SUMMARY.md"),
        ("project_readme", project_dir / "README.md"),
    ]
    for artifact_type, path in candidates:
        if not path.exists():
            continue
        try:
            rel = str(path.resolve().relative_to(repo.resolve()))
        except ValueError:
            rel = str(path)
        artifacts.append(
            {
                "type": artifact_type,
                "path": rel,
                "status": "present",
            }
        )
    return artifacts


def _render_carrier_chain_table(rows: list[dict[str, Any]]) -> list[str]:
    headers = ("surface", "status", "block", "next")
    prepared: list[tuple[str, str, str, str]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        prepared.append(
            (
                _table_cell(row.get("surface"), max_len=32),
                _table_cell(row.get("status"), max_len=36),
                _table_cell(bool(row.get("blocking")), max_len=5),
                _table_cell(row.get("next_command"), max_len=96),
            )
        )
    if not prepared:
        return ["  (no carrier rows)"]
    widths = [
        max(len(headers[idx]), *(len(row[idx]) for row in prepared))
        for idx in range(len(headers))
    ]
    lines = [
        "  "
        + "  ".join(headers[idx].ljust(widths[idx]) for idx in range(len(headers)))
    ]
    for row in prepared:
        lines.append(
            "  "
            + "  ".join(row[idx].ljust(widths[idx]) for idx in range(len(headers)))
        )
    return lines


def _render_brief(report: dict[str, Any]) -> list[str]:
    kernel_entry = report.get("kernel_entry") or {}
    surfaces = report.get("surfaces") or {}
    recent_loop = report.get("recent_loop") or {}
    graph_actions = report.get("graph_rd_actions") or []
    prediction = report.get("prediction_summary") or {}
    health = report.get("health_summary") or {}
    review_artifacts = report.get("review_artifacts") or []
    project_packet = report.get("project_packet") or {}
    packet_gap_contracts = project_packet.get("evidence_gap_contracts") or []
    evidence_compile_status = surfaces.get("evidence_compile_freshness", {}).get("status")
    evidence_output_status = surfaces.get("evidence_output_binding", {}).get("status")
    evidence_replay = surfaces.get("evidence_replay", {})
    evidence_replay_status = evidence_replay.get("status")
    evidence_replay_required = bool(evidence_replay.get("required"))
    evidence_replay_display = (
        evidence_replay_status if evidence_replay_required else "not_required"
    )
    claim_support = surfaces.get("claim_support") or {}
    evidence_readiness = "fresh"
    if evidence_compile_status not in {None, "", "fresh"}:
        evidence_readiness = "blocked"
    if evidence_output_status not in {None, "", "fresh"}:
        evidence_readiness = "blocked"
    if evidence_replay_required and evidence_replay_status != "ok":
        evidence_readiness = "blocked"

    lines = [
        f"Autoresearch trace: {report.get('project')} / {report.get('rubric')}",
        f"- status: {report.get('status')}",
        f"- readiness: {report.get('readiness_canonical') or report.get('readiness')}",
        f"- run readiness: {kernel_entry.get('status')} (can_enter={_table_cell(kernel_entry.get('can_enter_kernel'), max_len=8)})",
        f"- source preflight: {surfaces.get('source_preflight_status')} ({surfaces.get('source_evidence_count', 0)} source evidence, {surfaces.get('untyped_source_count', 0)} untyped)",
        (
            f"- evidence readiness: {evidence_readiness} "
            f"(compile={evidence_compile_status}, output={evidence_output_status}, "
            f"replay={evidence_replay_display})"
        ),
        (
            f"- claim support: {claim_support.get('status') or 'not_checked'} "
            f"({claim_support.get('claim_count', 0)} claims, "
            f"{claim_support.get('weak_or_unsourced_count', 0)} weak/unsourced, "
            f"{claim_support.get('source_context_blocked_count', 0)} source-context blocked)"
        ),
        f"- health: {health.get('overall_status') or '-'}",
    ]

    blockers = kernel_entry.get("blockers") or report.get("blocking_missing") or []
    if blockers:
        lines.append("- blockers:")
        lines.extend(f"  {_table_cell(blocker, max_len=120)}" for blocker in blockers)
    else:
        lines.append("- blockers: none")

    if review_artifacts:
        lines.append("- review artifacts:")
        for artifact in review_artifacts:
            if isinstance(artifact, dict):
                lines.append(
                    "  "
                    + _table_cell(artifact.get("type"), max_len=24)
                    + ": "
                    + _table_cell(artifact.get("path"), max_len=120)
                )

    if packet_gap_contracts:
        lines.append("- intake gap contracts:")
        for contract in packet_gap_contracts:
            if not isinstance(contract, dict):
                continue
            lines.append(
                "  "
                + _table_cell(contract.get("target"), max_len=48)
                + " -> "
                + _table_cell(contract.get("recovery_kind"), max_len=28)
                + " / "
                + _table_cell(contract.get("required_surface"), max_len=48)
            )

    if graph_actions:
        lines.append("- graph actions:")
        for action in graph_actions:
            if not isinstance(action, dict):
                continue
            reason = action.get("reason") or action.get("action_type")
            actor = action.get("recommended_actor") or "-"
            targets = action.get("targets") or action.get("gap_ids") or "-"
            lines.append(
                "  "
                + _table_cell(action.get("action_type"), max_len=32)
                + f" actor={_table_cell(actor, max_len=32)}"
                + f" targets={_table_cell(targets, max_len=72)}"
            )
            if reason:
                lines.append(f"    reason={_table_cell(reason, max_len=120)}")
    else:
        lines.append("- graph actions: none")

    if prediction:
        lines.append(
            "- prediction rows: "
            + _table_cell(prediction.get("status"), max_len=40)
            + f" ({prediction.get('row_count', 0)} rows, policy={_table_cell(prediction.get('measurement_policy'), max_len=40)})"
        )

    if recent_loop.get("available"):
        latest_score = recent_loop.get("latest_score")
        final_score = recent_loop.get("latest_run_final_score")
        if latest_score is None and final_score is not None:
            score_text = (
                "iteration_score=- "
                f"final_score={_table_cell(final_score, max_len=16)}"
            )
        elif final_score is not None and final_score != latest_score:
            score_text = (
                f"iteration_score={_table_cell(latest_score, max_len=16)} "
                f"final_score={_table_cell(final_score, max_len=16)}"
            )
        else:
            score_text = f"score={_table_cell(latest_score, max_len=16)}"
        lines.append(
            "- latest loop: "
            + score_text
            + " "
            + f"exit={_table_cell(recent_loop.get('latest_run_exit_reason'), max_len=32)} "
            + f"provider_failure={_table_cell(recent_loop.get('provider_failure_observed'), max_len=8)}"
        )
        risk_rows = recent_loop.get("recent_provider_failure_signatures") or []
        if risk_rows:
            first = risk_rows[0]
            if isinstance(first, dict):
                lines.append(
                    "  runtime risk="
                    + _table_cell(first.get("failure_class"), max_len=72)
                    + " recovery="
                    + _table_cell(first.get("recovery_kind"), max_len=72)
                )
    else:
        lines.append("- latest loop: none")

    plan_preview = report.get("plan_preview") or {}
    recommended = plan_preview.get("recommended_first_command")
    if recommended:
        lines.append("- recommended first command:")
        lines.append(f"  {recommended}")

    next_commands = report.get("next_commands") or []
    if next_commands:
        lines.append("- next commands:")
        lines.extend(f"  {command}" for command in next_commands[:4])
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, help="Project slug or path.")
    parser.add_argument("--rubric", help="Rubric slug or path.")
    parser.add_argument(
        "--model",
        default="gemini",
        help="Model label to render in suggested evidence recovery commands. No model call is made.",
    )
    parser.add_argument(
        "--evidence-search-backend",
        default="auto",
        choices=["auto", "openai", "anthropic"],
        help=(
            "Search backend to render in suggested evidence-fetch commands. "
            "No model call is made."
        ),
    )
    parser.add_argument(
        "--intake",
        "--packet",
        dest="packet",
        help="Optional project-intake JSON to validate as the in-loop readiness boundary.",
    )
    parser.add_argument(
        "--full-health",
        action="store_true",
        help="Also run aggregate autoresearch health. Default trace health is local and bounded.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    parser.add_argument("--brief", action="store_true", help="Emit a compact human-readable trace.")
    args = parser.parse_args(argv)

    report = build_autoresearch_trace(
        project=args.project,
        rubric=args.rubric,
        model=args.model,
        evidence_search_backend=args.evidence_search_backend,
        packet=args.packet,
        full_health=args.full_health,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif args.brief:
        print("\n".join(_render_brief(report)))
    else:
        print(f"Autoresearch trace: project={report['project']} status={report['status']}")
        print("readiness=" + json.dumps(report["readiness"]))
        print("missing=" + json.dumps(report["missing"]))
        print("blocking_missing=" + json.dumps(report["blocking_missing"]))
        print("history_missing=" + json.dumps(report["history_missing"]))
        project_intake = report.get("project_intake")
        if not isinstance(project_intake, dict):
            project_intake = _project_intake_alias(dict(report.get("project_packet") or {}))
        print("project_intake=" + json.dumps(project_intake, sort_keys=True))
        print(
            "legacy_project_packet="
            + json.dumps(report["project_packet"], sort_keys=True)
        )
        print("route_preview=" + json.dumps(report["route_preview"], sort_keys=True))
        print("plan_preview=" + json.dumps(report.get("plan_preview", {}), sort_keys=True))
        print("kernel_entry=" + json.dumps(report["kernel_entry"], sort_keys=True))
        print(
            "loop_admission="
            + json.dumps(report.get("loop_admission", {}), sort_keys=True)
        )
        print("carrier_chain_table:")
        for line in _render_carrier_chain_table(report["carrier_chain"]):
            print(line)
        print("carrier_chain=" + json.dumps(report["carrier_chain"], sort_keys=True))
        print("surfaces=" + json.dumps(report["surfaces"], sort_keys=True))
        print("projection=" + json.dumps(report["projection"], sort_keys=True))
        print("recent_loop=" + json.dumps(report["recent_loop"], sort_keys=True))
        print("graph_carriers=" + json.dumps(report["graph_carriers"], sort_keys=True))
        print("graph_rd_actions=" + json.dumps(report["graph_rd_actions"], sort_keys=True))
        print("prediction_summary=" + json.dumps(report["prediction_summary"], sort_keys=True))
        print("health_summary=" + json.dumps(report["health_summary"], sort_keys=True))
        print("next_commands:")
        for command in report["next_commands"]:
            print(f"  {command}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
