"""Shared evidence-gap state helpers for workspace and trace paths."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any


EVIDENCE_GAP_RESOLUTION_SCHEMA = "ztare-evidence-gap-resolutions-v1"
EVIDENCE_GAP_RESOLUTION_FILENAME = "evidence_gap_resolutions.json"
EVIDENCE_GAP_RECOVERY_CONTRACT_SCHEMA = "ztare-evidence-gap-recovery-contract-v1"

INACTIVE_EVIDENCE_GAP_STATUSES = {
    "accepted",
    "closed",
    "fetched",
    "ignored",
    "justified",
    "not_applicable",
    "resolved",
    "skipped_duplicate",
    "waived",
}

PUBLIC_EVIDENCE_RECOVERY_KIND = "public_evidence"
LOCAL_VERIFICATION_RECOVERY_KIND = "local_verification"
INACTIVE_RECOVERY_KIND = "inactive"
PUBLIC_EVIDENCE_RECOVERY_CHANNEL = "out_of_loop_evidence_recovery"
LOCAL_VERIFICATION_RECOVERY_CHANNEL = "in_loop_focus_receipt"

RECOVERY_KIND_FIELDS = (
    "recovery_kind",
    "recovery_channel",
    "repair_channel",
    "recovery_path",
    "action_type",
)

PUBLIC_EVIDENCE_RECOVERY_ALIASES = {
    PUBLIC_EVIDENCE_RECOVERY_KIND,
    "external_evidence",
    "external_source",
    "fetch_evidence",
    "out_of_loop_evidence_recovery",
    "public_source",
    "public_source_recovery",
    "source_fetch",
}

LOCAL_VERIFICATION_RECOVERY_ALIASES = {
    LOCAL_VERIFICATION_RECOVERY_KIND,
    "in_loop_focus",
    "in_loop_focus_receipt",
    "kernel_preflight",
    "local_kernel",
    "local_preflight",
    "local_repair",
    "local_verifier",
    "source_preflight",
    "trace_local",
}

LOCAL_ARTIFACT_ABSENCE_MARKERS = (
    "missing",
    "absence",
    "absent",
    "does not exist",
    "not found",
    "not present",
    "no such file",
    "lacks",
    "without",
)

LOCAL_VERIFICATION_GAP_MARKERS = (
    "audit gate",
    "checked for existence",
    "cannot be executed or falsified",
    "contract_enforcement",
    "content drift",
    "executability",
    "falsifier",
    "file existence",
    "file-path",
    "filepath",
    "change documentation or code",
    "code for",
    "gatekeeper",
    "kernel",
    "labels treated as proof",
    "operational definition",
    "path existence",
    "path validation",
    "pattern-based floor",
    "intake readiness",
    "preflight",
    "provenance",
    "reference resolution",
    "references resolve",
    "reference integrity",
    "runtime",
    "extend fixture",
    "fixture record",
    "source/evidence references",
    "source references",
    "syntactic checklist",
    "syntactic listing",
    "test suite",
    "unit test",
    "verification",
    "yield floor",
)

LOCAL_PATH_SAFETY_GAP_MARKERS = (
    "../",
    "local path",
    "local-path",
    "malicious symlink",
    "parent traversal",
    "path resolution",
    "path traversal",
    "path validation",
    "preflight path",
    "reference resolution",
    "references resolve",
    "symlink",
    "traversal",
)


def evidence_gap_activity(
    gap: dict[str, Any],
    *,
    project_dir: Path | None = None,
) -> dict[str, Any]:
    """Return the current activity state for an evidence-gap row.

    Explicit statuses are authoritative. For local missing-artifact gaps, the
    current project surface can also retire the row once the named artifact
    exists. External evidence gaps stay active unless explicitly closed.
    """
    status = str(gap.get("status") or gap.get("resolution_status") or "").strip().lower()
    if status in INACTIVE_EVIDENCE_GAP_STATUSES:
        return {"active": False, "status": status or "inactive_status"}
    if str(gap.get("resolved_at") or "").strip():
        return {"active": False, "status": "resolved_at"}
    if str(gap.get("justified_at") or "").strip():
        return {"active": False, "status": "justified_at"}
    if project_dir is not None:
        resolution = _evidence_gap_receipt_resolution(gap, project_dir=project_dir)
        if resolution is not None:
            return {
                "active": False,
                "status": "resolved_by_evidence_gap_receipt",
                **resolution,
            }
        resolution = _local_artifact_resolution(gap, project_dir=project_dir)
        if resolution is not None:
            return {
                "active": False,
                "status": "resolved_by_local_artifact",
                **resolution,
            }
        resolution = _local_verifier_receipt_resolution(gap, project_dir=project_dir)
        if resolution is not None:
            return {
                "active": False,
                "status": "resolved_by_local_verifier_receipt",
                **resolution,
            }
    return {"active": True, "status": "active"}


def evidence_gap_recovery(
    gap: dict[str, Any],
    *,
    project_dir: Path | None = None,
) -> dict[str, Any]:
    """Classify how an evidence-gap row should be recovered.

    ``public_evidence`` rows are suitable for evidence-fetch. ``local_verification``
    rows should stay inside the autoresearch loop or local kernel preflight.
    Inactive rows should not drive either path.
    """
    activity = evidence_gap_activity(gap, project_dir=project_dir)
    if not bool(activity.get("active")):
        return {
            **activity,
            "recovery_kind": INACTIVE_RECOVERY_KIND,
            "target": _gap_target(gap),
        }
    explicit_kind = explicit_evidence_gap_recovery_kind(gap)
    if explicit_kind is not None:
        return {
            **activity,
            "recovery_kind": explicit_kind,
            "target": _gap_target(gap),
            "classification_source": "explicit_schema",
        }
    if evidence_gap_is_local_verification(gap):
        return {
            **activity,
            "recovery_kind": LOCAL_VERIFICATION_RECOVERY_KIND,
            "target": _gap_target(gap),
            "classification_source": "legacy_text",
        }
    return {
        **activity,
        "recovery_kind": PUBLIC_EVIDENCE_RECOVERY_KIND,
        "target": _gap_target(gap),
        "classification_source": "default_public",
    }


def explicit_evidence_gap_recovery_kind(gap: dict[str, Any]) -> str | None:
    """Return a schema-declared recovery kind, if one is present."""
    for value in _declared_recovery_values(gap):
        if value in PUBLIC_EVIDENCE_RECOVERY_ALIASES:
            return PUBLIC_EVIDENCE_RECOVERY_KIND
        if value in LOCAL_VERIFICATION_RECOVERY_ALIASES:
            return LOCAL_VERIFICATION_RECOVERY_KIND
    for source in _recovery_bool_sources(gap):
        declared_public_fetch = optional_bool(source.get("can_public_fetch"))
        declared_in_loop = optional_bool(source.get("in_loop_consumable"))
        if declared_public_fetch is True and declared_in_loop is False:
            return PUBLIC_EVIDENCE_RECOVERY_KIND
        if declared_public_fetch is False and declared_in_loop is True:
            return LOCAL_VERIFICATION_RECOVERY_KIND
    return None


def evidence_gap_is_local_verification(gap: dict[str, Any]) -> bool:
    """Return whether the active gap belongs to local verifier repair."""
    explicit_kind = explicit_evidence_gap_recovery_kind(gap)
    if explicit_kind is not None:
        return explicit_kind == LOCAL_VERIFICATION_RECOVERY_KIND
    text = _gap_semantic_text(gap)
    if "://" in text:
        return False
    return any(marker in text for marker in LOCAL_VERIFICATION_GAP_MARKERS)


def evidence_gap_is_active(
    gap: dict[str, Any],
    *,
    project_dir: Path | None = None,
) -> bool:
    """Return whether an evidence-gap row should still drive recovery.

    Missing or unknown status stays active. Explicit closure, waiver,
    justification, a resolution timestamp, or a repaired local missing-artifact
    target makes the row inactive.
    """
    return bool(evidence_gap_activity(gap, project_dir=project_dir)["active"])


def normalize_evidence_gap_recovery_kind(value: str | None) -> str | None:
    normalized = (value or "").strip().lower()
    if normalized in {PUBLIC_EVIDENCE_RECOVERY_KIND, LOCAL_VERIFICATION_RECOVERY_KIND}:
        return normalized
    return None


def optional_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    if isinstance(value, (int, float)) and value in {0, 1}:
        return bool(value)
    text = str(value).strip().lower()
    if text in {"true", "yes", "1"}:
        return True
    if text in {"false", "no", "0"}:
        return False
    return None


def recovery_channel_for_gap(kind: str) -> str:
    if kind == LOCAL_VERIFICATION_RECOVERY_KIND:
        return LOCAL_VERIFICATION_RECOVERY_CHANNEL
    return PUBLIC_EVIDENCE_RECOVERY_CHANNEL


def required_surface_for_gap(kind: str, gap_type: str) -> str:
    if kind == INACTIVE_RECOVERY_KIND:
        return "inactive"
    if kind == LOCAL_VERIFICATION_RECOVERY_KIND:
        return "local_verifier_or_fixture"
    if gap_type in {
        "missing_external_comparator",
        "missing_independent_taxonomy",
        "missing_external_validation",
    }:
        return "public_source"
    return "public_or_local_source"


def evidence_gap_recovery_contract(
    gap: dict[str, Any],
    *,
    project_dir: Path | None = None,
) -> dict[str, Any]:
    """Return the first-class recovery-routing contract for an evidence gap.

    This is the strict interface consumers should use. Text fallback may still
    classify legacy rows, but the result is carried as a contract with an
    explicit source and conflict warnings instead of being re-inferred by each
    caller.
    """
    recovery = evidence_gap_recovery(gap, project_dir=project_dir)
    kind = normalize_evidence_gap_recovery_kind(str(recovery.get("recovery_kind") or ""))
    if kind is None:
        kind = (
            INACTIVE_RECOVERY_KIND
            if recovery.get("recovery_kind") == INACTIVE_RECOVERY_KIND
            else PUBLIC_EVIDENCE_RECOVERY_KIND
        )
    active = bool(recovery.get("active"))
    recovery_channel = (
        "inactive"
        if kind == INACTIVE_RECOVERY_KIND
        else recovery_channel_for_gap(kind)
    )
    can_public_fetch = active and kind == PUBLIC_EVIDENCE_RECOVERY_KIND
    in_loop_consumable = active and kind == LOCAL_VERIFICATION_RECOVERY_KIND
    required_surface = (
        _declared_required_surface(gap)
        or required_surface_for_gap(kind, str(gap.get("gap_type") or "other"))
    )
    existing_warnings = gap.get("recovery_contract_warnings")
    warnings = _recovery_contract_warnings(
        gap,
        expected_channel=recovery_channel,
        expected_public_fetch=can_public_fetch,
        expected_in_loop=in_loop_consumable,
    )
    if isinstance(existing_warnings, list):
        warnings.extend(str(item) for item in existing_warnings if str(item).strip())
    contract_source = (
        str(gap.get("recovery_contract_source") or "")
        or str(recovery.get("classification_source") or "")
        or str(recovery.get("status") or "")
        or "unknown"
    )
    fallback_sources = {"default_public", "legacy_text", "sanitized_inference"}
    schema_promotion_required = active and contract_source in fallback_sources
    advisories = (
        ["schema_promotion_required_for_recovery_route"]
        if schema_promotion_required
        else []
    )
    return {
        "schema": EVIDENCE_GAP_RECOVERY_CONTRACT_SCHEMA,
        "contract_ok": not warnings,
        "gap_sha256": evidence_gap_fingerprint(_without_nested_recovery_contract(gap)),
        "active": active,
        "activity_status": recovery.get("status"),
        "recovery_kind": kind,
        "recovery_channel": recovery_channel,
        "required_surface": required_surface,
        "can_public_fetch": can_public_fetch,
        "in_loop_consumable": in_loop_consumable,
        "target": recovery.get("target") or _gap_target(gap),
        "classification_source": contract_source,
        "classification_strength": (
            "fallback_inference" if schema_promotion_required else "explicit_or_resolved"
        ),
        "schema_promotion_required": schema_promotion_required,
        "advisories": advisories,
        "warnings": sorted(set(warnings)),
    }


def canonicalize_evidence_gap_recovery_contract(
    gap: dict[str, Any],
    *,
    recovery_kind: str | None = None,
    recovery_channel: str | None = None,
    required_surface: str | None = None,
    can_public_fetch: Any = None,
    in_loop_consumable: Any = None,
    project_dir: Path | None = None,
) -> dict[str, Any]:
    """Return a copy of ``gap`` with canonical recovery-routing fields.

    Producer-declared ``recovery_kind`` is authoritative over prose. Contradictory
    channel/boolean fields are normalized to the kind and recorded as warnings so
    public fetch cannot accidentally consume an in-loop repair row.
    """
    row = dict(gap)
    normalized_kind = normalize_evidence_gap_recovery_kind(
        recovery_kind if recovery_kind is not None else str(row.get("recovery_kind") or "")
    )
    supplied_channel = str(
        recovery_channel if recovery_channel is not None else row.get("recovery_channel") or ""
    ).strip()
    had_explicit_contract = normalized_kind is not None or bool(supplied_channel)
    if normalized_kind is not None:
        row["recovery_kind"] = normalized_kind
    if supplied_channel:
        row["recovery_channel"] = supplied_channel

    recovery = evidence_gap_recovery(row, project_dir=project_dir)
    resolved_kind = normalize_evidence_gap_recovery_kind(
        str(recovery.get("recovery_kind") or "")
    ) or PUBLIC_EVIDENCE_RECOVERY_KIND
    expected_channel = recovery_channel_for_gap(resolved_kind)
    expected_public_fetch = resolved_kind == PUBLIC_EVIDENCE_RECOVERY_KIND
    expected_in_loop = resolved_kind == LOCAL_VERIFICATION_RECOVERY_KIND
    warning_row = dict(row)
    if can_public_fetch is not None:
        warning_row["can_public_fetch"] = can_public_fetch
    if in_loop_consumable is not None:
        warning_row["in_loop_consumable"] = in_loop_consumable
    warnings = _recovery_contract_warnings(
        warning_row,
        expected_channel=expected_channel,
        expected_public_fetch=expected_public_fetch,
        expected_in_loop=expected_in_loop,
    )

    row["recovery_kind"] = resolved_kind
    row["recovery_channel"] = expected_channel
    row["required_surface"] = (
        str(required_surface or row.get("required_surface") or "").strip()
        or required_surface_for_gap(resolved_kind, str(row.get("gap_type") or "other"))
    )
    row["can_public_fetch"] = expected_public_fetch
    row["in_loop_consumable"] = expected_in_loop
    row["recovery_contract_source"] = (
        "explicit_schema" if had_explicit_contract else "sanitized_inference"
    )
    if warnings:
        row["recovery_contract_warnings"] = sorted(set(warnings))
    else:
        row.pop("recovery_contract_warnings", None)
    row["recovery_contract"] = evidence_gap_recovery_contract(row, project_dir=project_dir)
    return row


def apply_evidence_gap_recovery_policy(
    gap: dict[str, Any],
    policy: dict[str, Any] | None,
    *,
    project_dir: Path | None = None,
) -> dict[str, Any]:
    """Apply an intake-declared recovery policy to a gap row.

    This lets a project packet constrain how later judge-emitted gaps should be
    recovered. It is useful for synthetic/local fixtures where "fetch docs" or
    "run a scenario" means local fixture/verifier work, not public web search.
    """
    if not isinstance(policy, dict) or not policy:
        return gap
    applies_to = str(policy.get("applies_to") or "").strip()
    if applies_to not in {"all_latest_gaps", "all_project_generated_gaps"}:
        return gap
    if optional_bool(policy.get("override_latest_gap_recovery")) is not True:
        return gap
    kind = normalize_evidence_gap_recovery_kind(
        str(policy.get("default_recovery_kind") or "")
    )
    if kind is None:
        return gap
    channel = str(policy.get("default_recovery_channel") or "").strip()
    required_surface = str(policy.get("default_required_surface") or "").strip()
    return canonicalize_evidence_gap_recovery_contract(
        gap,
        recovery_kind=kind,
        recovery_channel=channel or recovery_channel_for_gap(kind),
        required_surface=required_surface or None,
        can_public_fetch=(kind == PUBLIC_EVIDENCE_RECOVERY_KIND),
        in_loop_consumable=(kind == LOCAL_VERIFICATION_RECOVERY_KIND),
        project_dir=project_dir,
    )


def evidence_gap_fingerprint(gap: dict[str, Any]) -> str:
    """Return a stable hash for the exact evidence-gap row."""
    return hashlib.sha256(
        json.dumps(gap, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _evidence_gap_receipt_resolution(
    gap: dict[str, Any],
    *,
    project_dir: Path,
) -> dict[str, str] | None:
    receipt_path = project_dir / "workspace" / EVIDENCE_GAP_RESOLUTION_FILENAME
    try:
        payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    if payload.get("schema") != EVIDENCE_GAP_RESOLUTION_SCHEMA:
        return None
    if str(payload.get("project") or "") != project_dir.name:
        return None
    rows = payload.get("resolutions")
    if not isinstance(rows, list):
        return None
    gap_sha = evidence_gap_fingerprint(gap)
    gap_id = str(gap.get("id") or "").strip()
    target = _gap_target(gap)
    for row in rows:
        if not isinstance(row, dict):
            continue
        status = str(row.get("status") or "").strip().lower()
        if status not in INACTIVE_EVIDENCE_GAP_STATUSES:
            continue
        if str(row.get("gap_sha256") or "").strip() != gap_sha:
            continue
        if gap_id and str(row.get("gap_id") or "").strip() != gap_id:
            continue
        if target and str(row.get("target") or "").strip() != target:
            continue
        reason = str(row.get("reason") or "").strip()
        if len(reason) < 16:
            continue
        if not _resolution_evidence_refs_verified(row, project_dir=project_dir):
            continue
        return {
            "target": target,
            "artifact": f"workspace/{EVIDENCE_GAP_RESOLUTION_FILENAME}",
            "receipt_type": "evidence_gap_resolution",
            "resolution_status": status,
            "resolution_id": str(row.get("resolution_id") or ""),
        }
    return None


def _resolution_evidence_refs_verified(
    row: dict[str, Any],
    *,
    project_dir: Path,
) -> bool:
    refs = row.get("evidence_refs")
    if refs is None:
        return True
    if not isinstance(refs, list):
        return False
    project_root = project_dir.resolve()
    for ref in refs:
        if not isinstance(ref, dict):
            return False
        raw_path = str(ref.get("path") or "").strip()
        expected_sha = str(ref.get("sha256") or "").strip()
        if not raw_path or not expected_sha:
            return False
        path = PurePosixPath(raw_path.replace("\\", "/"))
        if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
            return False
        candidate = project_dir / path.as_posix()
        try:
            resolved = candidate.resolve()
            resolved.relative_to(project_root)
        except ValueError:
            return False
        if not resolved.is_file():
            return False
        current_sha = hashlib.sha256(resolved.read_bytes()).hexdigest()
        if current_sha != expected_sha:
            return False
    return True


def _local_artifact_resolution(
    gap: dict[str, Any],
    *,
    project_dir: Path,
) -> dict[str, str] | None:
    target = _safe_local_artifact_target(gap.get("target"), project_dir=project_dir)
    if target is None:
        return None
    if not _gap_text_implies_missing_artifact(gap):
        return None
    project_root = project_dir.resolve()
    candidates = [
        project_dir / target,
        project_dir / "workspace" / target,
        project_dir / "raw" / target,
    ]
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
            resolved.relative_to(project_root)
        except ValueError:
            continue
        if resolved.exists():
            return {
                "target": target,
                "artifact": str(resolved.relative_to(project_root)),
            }
    return None


def _local_verifier_receipt_resolution(
    gap: dict[str, Any],
    *,
    project_dir: Path,
) -> dict[str, str] | None:
    if not evidence_gap_is_local_verification(gap):
        return None
    if not _gap_text_matches_path_safety_target(gap):
        return None
    receipt_path = project_dir / "workspace" / "packet_falsifier_receipt.json"
    try:
        payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    status = str(payload.get("status") or "").strip().lower()
    if status not in {"ok", "passed", "resolved"} | INACTIVE_EVIDENCE_GAP_STATUSES:
        return None
    path_safety = payload.get("path_safety")
    if not isinstance(path_safety, dict):
        return None
    required_false = (
        "absolute_local_refs_allowed",
        "parent_traversal_allowed",
        "symlink_escape_allowed",
    )
    if any(path_safety.get(key) is not False for key in required_false):
        return None
    return {
        "target": _gap_target(gap) or "local_path_resolution",
        "artifact": "workspace/packet_falsifier_receipt.json",
        "receipt_type": "project_packet_falsifier",
        "verified_policy": "path_safety",
    }


def _gap_text_matches_path_safety_target(gap: dict[str, Any]) -> bool:
    text = _gap_semantic_text(gap)
    return any(marker in text for marker in LOCAL_PATH_SAFETY_GAP_MARKERS)


def _safe_local_artifact_target(
    value: Any,
    *,
    project_dir: Path,
) -> str | None:
    raw = str(value or "").strip().replace("\\", "/")
    if not raw or "://" in raw or "\n" in raw or "\r" in raw:
        return None
    project_prefix = f"projects/{project_dir.name}/"
    if raw.startswith(project_prefix):
        raw = raw[len(project_prefix):]
    if raw.startswith("./"):
        raw = raw[2:]
    path = PurePosixPath(raw)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        return None
    if "/" not in raw and not path.suffix:
        return None
    return path.as_posix()


def _gap_text_implies_missing_artifact(gap: dict[str, Any]) -> bool:
    text_parts = [
        gap.get("description"),
        gap.get("producer_rationale"),
        gap.get("weakest_point"),
        gap.get("fetch_query"),
        gap.get("reason"),
        gap.get("summary"),
    ]
    text = " ".join(str(part or "") for part in text_parts).lower()
    return any(marker in text for marker in LOCAL_ARTIFACT_ABSENCE_MARKERS)


def _gap_semantic_text(gap: dict[str, Any]) -> str:
    return " ".join(
        str(gap.get(key) or "")
        for key in (
            "target",
            "gap_type",
            "failure_family",
            "description",
            "producer_rationale",
            "fetch_query",
            "applies_to",
        )
    ).lower()


def _declared_recovery_values(gap: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for key in RECOVERY_KIND_FIELDS:
        values.extend(_normalize_recovery_value(gap.get(key)))
    recovery = gap.get("recovery")
    if isinstance(recovery, dict):
        for key in RECOVERY_KIND_FIELDS:
            values.extend(_normalize_recovery_value(recovery.get(key)))
    return values


def _recovery_bool_sources(gap: dict[str, Any]) -> list[dict[str, Any]]:
    sources = [gap]
    recovery = gap.get("recovery")
    if isinstance(recovery, dict):
        sources.append(recovery)
    return sources


def _without_nested_recovery_contract(gap: dict[str, Any]) -> dict[str, Any]:
    row = dict(gap)
    row.pop("recovery_contract", None)
    return row


def _declared_required_surface(gap: dict[str, Any]) -> str:
    direct = str(gap.get("required_surface") or "").strip()
    if direct:
        return direct
    recovery = gap.get("recovery")
    if isinstance(recovery, dict):
        nested = str(recovery.get("required_surface") or "").strip()
        if nested:
            return nested
    return ""


def _recovery_contract_warnings(
    gap: dict[str, Any],
    *,
    expected_channel: str,
    expected_public_fetch: bool,
    expected_in_loop: bool,
) -> list[str]:
    warnings: list[str] = []
    supplied_channels = [
        str(value).strip()
        for value in [gap.get("recovery_channel")]
        if str(value or "").strip()
    ]
    recovery = gap.get("recovery")
    if isinstance(recovery, dict) and str(recovery.get("recovery_channel") or "").strip():
        supplied_channels.append(str(recovery.get("recovery_channel")).strip())
    if any(channel != expected_channel for channel in supplied_channels):
        warnings.append("recovery_channel_conflicted_with_recovery_kind")
    declared_public_fetch_values = [
        optional_bool(source.get("can_public_fetch"))
        for source in _recovery_bool_sources(gap)
        if source.get("can_public_fetch") is not None
    ]
    declared_in_loop_values = [
        optional_bool(source.get("in_loop_consumable"))
        for source in _recovery_bool_sources(gap)
        if source.get("in_loop_consumable") is not None
    ]
    if any(
        value is not None and value != expected_public_fetch
        for value in declared_public_fetch_values
    ):
        warnings.append("can_public_fetch_conflicted_with_recovery_kind")
    if any(value is not None and value != expected_in_loop for value in declared_in_loop_values):
        warnings.append("in_loop_consumable_conflicted_with_recovery_kind")
    return sorted(set(warnings))


def _normalize_recovery_value(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        out: list[str] = []
        for item in value:
            out.extend(_normalize_recovery_value(item))
        return out
    text = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    return [text] if text else []


def _gap_target(gap: dict[str, Any]) -> str:
    return str(gap.get("target") or gap.get("applies_to") or "").strip()
