"""Recent-change finalization shared by the CLI and the workbench server.

When a project file is saved, its `recent_changes` block must be brought to a
stable, recorded state: the saved-file row is recorded, the recorded/receipt
counts are recomputed from the rows that actually carry recorded work, and a
single "what to inspect next" target is chosen. The workbench server and the
project-file writer both need this, so it lives here as one implementation.

`preview_path_allowed` is the same allow-list the file-preview API uses; the
inspection target reuses it so a recent change never points the reader at a
path the preview surface would refuse to open.
"""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any

FILE_PREVIEW_ALLOWED_ROOTS = (
    "analytics/public",
    "docs",
    "examples",
    "forensic-workbench",
    "projects",
    "rubrics",
    "ztare_proofs/leanmill-formalizations",
)
FILE_PREVIEW_ALLOWED_FILES = {
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "README.md",
    "RELEASE_CHECKLIST.md",
    "SECURITY.md",
    "priority_roadmap.md",
}
FILE_PREVIEW_BLOCKED_PARTS = {".git", ".agents", ".codex", "internal", "research_areas"}


def preview_path_allowed(path: str) -> bool:
    normalized = PurePosixPath(path)
    parts = normalized.parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        return False
    if any(part in FILE_PREVIEW_BLOCKED_PARTS for part in parts):
        return False
    if len(parts) == 1 and parts[0] in FILE_PREVIEW_ALLOWED_FILES:
        return True
    preview_root = "/".join(parts[:2]) if len(parts) > 1 else parts[0]
    return preview_root in FILE_PREVIEW_ALLOWED_ROOTS or parts[0] in FILE_PREVIEW_ALLOWED_ROOTS


def change_row_time(row: dict[str, Any]) -> str:
    return str(row.get("applied_at") or row.get("timestamp") or "")


def recent_change_inspection_reason(*, label: str, kind: str, preview_kind: str) -> str:
    text = f"{label} {kind}".lower()
    if preview_kind == "artifact":
        if "claim card" in text or "claim_card" in text:
            return "Open the shareable claim card to inspect the public summary and verification details."
        if "report" in text:
            return "Open the report file to inspect the readiness summary and supporting evidence."
        if "project test" in text or "project_test" in text:
            return "Open the project test file to inspect what ran; open saved history to see the result."
        if "source" in text or "evidence" in text:
            return "Open the source or evidence file to see what changed."
        if "run" in text:
            return "Open the run file to see the latest score, weakest point, and evidence gaps."
        if "review" in text:
            return "Open the saved review file to see the recorded decision."
        if "next step" in text:
            return "Open the saved next-step file to see what should happen next."
        if "project file" in text or "case_file" in text:
            return "Open the saved project file to inspect the packaged project state."
        return "Open the changed file to see what changed."
    if preview_kind == "receipt":
        return "Open saved history to see what changed and when."
    return "The latest change has no previewable file path."


def recent_change_inspection_target(change: dict[str, Any], fallback_receipt: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(change, dict):
        change = {}
    if not isinstance(fallback_receipt, dict):
        fallback_receipt = {}
    artifact_path = str(change.get("artifact_path") or "")
    receipt_path = str(change.get("receipt_path") or fallback_receipt.get("path") or "")
    preview_path = artifact_path or receipt_path
    if not preview_path_allowed(preview_path):
        preview_path = receipt_path if preview_path_allowed(receipt_path) else ""
    if not change and not receipt_path:
        return {
            "status": "missing",
            "label": "No saved work yet",
            "summary": "No saved project change is available to inspect.",
            "receipt_path": "",
            "artifact_path": "",
            "preview_path": "",
            "preview_kind": "",
            "reason": "Save a review, next step, run, evidence change, or project file first.",
        }
    preview_kind = "artifact" if preview_path and preview_path == artifact_path else "receipt" if preview_path else ""
    label = str(change.get("label") or fallback_receipt.get("display_kind") or fallback_receipt.get("kind") or "Latest change")
    summary = str(change.get("summary") or fallback_receipt.get("display_summary") or fallback_receipt.get("summary") or "")
    return {
        "status": "recorded" if (change or receipt_path) else "missing",
        "label": label,
        "summary": summary,
        "receipt_path": receipt_path,
        "artifact_path": artifact_path,
        "preview_path": preview_path,
        "preview_kind": preview_kind,
        "reason": recent_change_inspection_reason(label=label, kind=str(change.get("kind") or ""), preview_kind=preview_kind),
    }


def finalize_recent_changes(
    value: dict[str, Any],
    *,
    latest_project_file: dict[str, Any],
    latest_receipt_path: str,
    saved_summary: str,
) -> dict[str, Any]:
    """Record the saved-file row, recompute counts, and pick the inspection target.

    Mirrors the workbench server's `stable_recent_changes`: the saved project
    file becomes the latest recorded change, recorded/receipt counts are derived
    from the rows that actually carry recorded work (never the client's claimed
    count), and `substantive_inspection` points at the most recent source,
    project-test, or run change when the caller has not already chosen one.
    """

    changes = dict(value)
    changes["latest_project_file"] = dict(latest_project_file)
    changes["latest_receipt_path"] = latest_receipt_path
    changes["latest_receipt_summary"] = saved_summary
    changes["summary"] = saved_summary
    changes["status"] = "recorded"
    if isinstance(changes.get("changes"), list):
        normalized_changes = []
        project_file_seen = False
        for row in changes["changes"]:
            if isinstance(row, dict) and str(row.get("label") or "") == "Latest project file":
                if not project_file_seen:
                    normalized_changes.append(dict(latest_project_file))
                    project_file_seen = True
                continue
            normalized_changes.append(row)
        if not project_file_seen:
            normalized_changes.append(dict(latest_project_file))
        changes["changes"] = normalized_changes
    recorded_rows = [
        row
        for row in [
            changes.get("latest_review"),
            changes.get("latest_next_step"),
            changes.get("latest_source_or_evidence_change"),
            changes.get("latest_project_check"),
            changes.get("latest_run"),
            changes.get("latest_project_file"),
        ]
        if isinstance(row, dict) and row.get("status") == "recorded"
    ]
    if not isinstance(changes.get("substantive_inspection"), dict):
        substantive_rows = [
            row
            for row in [
                changes.get("latest_source_or_evidence_change"),
                changes.get("latest_project_check"),
                changes.get("latest_run"),
            ]
            if isinstance(row, dict) and row.get("status") == "recorded"
        ]
        latest_substantive = max(substantive_rows, key=change_row_time) if substantive_rows else {}
        changes["substantive_inspection"] = recent_change_inspection_target(latest_substantive, {})
    changes["recorded_count"] = len(recorded_rows)
    changes["receipt_count"] = len(recorded_rows)
    return changes
