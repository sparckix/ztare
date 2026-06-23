#!/usr/bin/env python3
"""Render a static local forensic-workbench snapshot.

This D4 read model consumes one selected project's
intake, autoresearch trace, review receipt, and report-support contract outputs,
then renders file-backed snapshot artifacts for the local workbench.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PYTHON = os.environ.get("PYTHON", sys.executable)
DEFAULT_PROJECT = "ops_root_cause_diagnosis_demo"
DEFAULT_RUBRIC = "ops_root_cause_diagnosis_demo"
DEFAULT_INTAKE = ""
DEFAULT_RENDERER = "decision_brief"
DEFAULT_OUT = "docs/landings/forensic_workbench_prototype.html"


def validate_project_slug(project: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", project):
        raise ValueError(f"invalid project slug: {project!r}")
    return project


def default_intake_for_project(project: str) -> str:
    project = validate_project_slug(project)
    discovered = discover_intake_for_project(project)
    if discovered:
        return discovered
    return f"projects/{project}/{project}_intake.json"


def discover_intake_for_project(project: str) -> str:
    project = validate_project_slug(project)
    candidates = [
        REPO / "projects" / project / f"{project}_intake.json",
        REPO / "projects" / project / "project_intake.json",
        REPO / "examples" / "project_packets" / f"{project}_intake.json",
        REPO / "examples" / "project_packets" / f"ready_{project}_intake.json",
    ]
    for path in candidates:
        if path.exists():
            return rel(path)
    return ""


def discover_project_intakes(project: str) -> list[str]:
    project = validate_project_slug(project)
    project_dir = REPO / "projects" / project
    if not project_dir.exists():
        return []
    candidates = [
        project_dir / f"{project}_intake.json",
        project_dir / "project_intake.json",
        *sorted(project_dir.glob("*_intake.json")),
    ]
    seen: set[str] = set()
    intakes: list[str] = []
    for path in candidates:
        if not path.exists() or not path.is_file():
            continue
        intake = rel(path)
        if intake in seen:
            continue
        seen.add(intake)
        intakes.append(intake)
    return intakes


def project_slug_from_example_intake(path: Path) -> str:
    stem = path.stem
    if not stem.endswith("_intake"):
        return ""
    project = stem[: -len("_intake")]
    if project.startswith("ready_"):
        project = project[len("ready_") :]
    try:
        return validate_project_slug(project)
    except ValueError:
        return ""


def public_example_intakes() -> list[tuple[str, Path]]:
    examples_dir = REPO / "examples" / "project_packets"
    if not examples_dir.exists():
        return []
    entries: list[tuple[str, Path]] = []
    for path in sorted(examples_dir.glob("ready_*_intake.json")):
        project = project_slug_from_example_intake(path)
        if project:
            entries.append((project, path))
    return entries


def intake_source_for_path(project: str, intake: str | Path | None) -> str:
    path = rel(intake)
    if path.startswith(f"projects/{project}/"):
        return "project_local_intake"
    if path.startswith("examples/project_packets/"):
        return "public_example_intake"
    return "unknown_intake_source"


def list_project_entries() -> list[dict[str, Any]]:
    entries_by_case: dict[str, dict[str, Any]] = {}
    local_projects: set[str] = set()

    def latest_path_for_case(path: Path, *, project: str, intake: str) -> str:
        if not path.exists():
            return ""
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return rel(path)
        if not isinstance(payload, dict):
            return rel(path)
        return rel(path) if receipt_matches_case(payload, project=project, intake=intake) else ""

    def upsert_project_entry(project: str, intake: str, *, source: str) -> None:
        project = validate_project_slug(project)
        project_dir = REPO / "projects" / project
        latest_review = latest_review_path(project)
        latest_action = latest_row_action_path(project)
        latest_intake_edit = latest_intake_edit_path(project)
        latest_source_import = latest_source_import_path(project)
        latest_source_edit = latest_source_edit_path(project)
        latest_source_action = latest_source_action_path(project)
        latest_case_file_write = latest_case_file_write_path(project)
        report_contract = project_dir / "synthesis" / "report_support_contract.json"
        entry_key = case_key(project, intake)
        entry = entries_by_case.get(entry_key)
        if entry is None:
            entries_by_case[entry_key] = {
                "project": project,
                "rubric": project,
                "project_dir": rel(project_dir) if project_dir.exists() else "",
                "intake": intake,
                "intake_source": source,
                "latest_review": latest_path_for_case(latest_review, project=project, intake=intake),
                "latest_row_action": latest_path_for_case(latest_action, project=project, intake=intake),
                "latest_intake_edit": latest_path_for_case(latest_intake_edit, project=project, intake=intake),
                "latest_source_import": latest_path_for_case(latest_source_import, project=project, intake=intake),
                "latest_source_edit": latest_path_for_case(latest_source_edit, project=project, intake=intake),
                "latest_source_action": latest_path_for_case(latest_source_action, project=project, intake=intake),
                "latest_case_file_write": latest_path_for_case(latest_case_file_write, project=project, intake=intake),
                "report_contract": rel(report_contract) if report_contract.exists() else "",
            }
            return
        if project_dir.exists():
            entry["project_dir"] = rel(project_dir)
        if source == "project_local_intake":
            entry["intake"] = intake
            entry["intake_source"] = source
        for key, path in (
            ("latest_review", latest_review),
            ("latest_row_action", latest_action),
            ("latest_intake_edit", latest_intake_edit),
            ("latest_source_import", latest_source_import),
            ("latest_source_edit", latest_source_edit),
            ("latest_source_action", latest_source_action),
            ("latest_case_file_write", latest_case_file_write),
        ):
            latest_for_case = latest_path_for_case(path, project=project, intake=str(entry.get("intake") or intake))
            if latest_for_case:
                entry[key] = latest_for_case
            elif str(entry.get("intake") or "") == intake:
                entry[key] = ""
        if report_contract.exists():
            entry["report_contract"] = rel(report_contract)

    for project, path in public_example_intakes():
        upsert_project_entry(project, rel(path), source="public_example_intake")

    projects_dir = REPO / "projects"
    if not projects_dir.exists():
        return [entries_by_case[key] for key in sorted(entries_by_case)]
    for project_dir in sorted(path for path in projects_dir.iterdir() if path.is_dir()):
        project = project_dir.name
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", project):
            continue
        intakes = discover_project_intakes(project)
        if not intakes:
            continue
        local_projects.add(project)
        for intake in intakes:
            intake_source = intake_source_for_path(project, intake)
            upsert_project_entry(project, intake, source=intake_source)
    return [
        entry
        for _key, entry in sorted(entries_by_case.items())
        if not (entry.get("intake_source") == "public_example_intake" and entry.get("project") in local_projects)
    ]


def run(cmd: list[str], *, timeout: int = 90) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            cmd,
            cwd=REPO,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=124,
            stdout=stdout,
            stderr=(stderr + f"\ncommand timed out after {timeout}s").strip(),
        )


def extract_last_json_object(text: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    parsed: list[dict[str, Any]] = []
    for match in re.finditer(r"(?m)^\{", text):
        try:
            obj, _end = decoder.raw_decode(text[match.start() :])
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            parsed.append(obj)
    if not parsed:
        raise ValueError(f"could not find JSON object in output:\n{text}")
    return parsed[-1]


def rel(path: str | Path | None) -> str:
    if not path:
        return ""
    value = Path(str(path))
    if value.is_absolute():
        try:
            return str(value.relative_to(REPO))
        except ValueError:
            return str(value)
    return str(value)


def href_for(output_path: Path, target: str | Path | None) -> str:
    path = rel(target)
    if not path:
        return ""
    target_path = REPO / path
    try:
        return os.path.relpath(target_path, start=output_path.parent)
    except ValueError:
        return path


def shell_join(cmd: list[str]) -> str:
    return " ".join(cmd)


def display_python() -> str:
    value = rel(PYTHON)
    if value == PYTHON:
        return value
    return value if value.startswith(".") else f"./{value}"


def collect_trace(project: str, rubric: str, intake: str) -> tuple[dict[str, Any], str]:
    display_command = (
        "ztare autoresearch trace "
        f"--project {project} --rubric {rubric} --intake {intake} --json"
    )
    command = [
        PYTHON,
        "-m",
        "src.ztare.cli",
        "autoresearch",
        "trace",
        "--project",
        project,
        "--rubric",
        rubric,
        "--intake",
        intake,
        "--json",
    ]
    proc = run(command)
    if proc.returncode != 0:
        raise SystemExit(
            "forensic workbench trace command failed\n"
            f"command: {shell_join(command)}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )
    return json.loads(proc.stdout), display_command


def collect_report_contract(project: str, renderer: str) -> tuple[dict[str, Any], str]:
    display_command = (
        "make synth-contract "
        f"PROJECT={project} RENDERER={renderer} PYTHON={display_python()}"
    )
    command = [
        "make",
        "synth-contract",
        f"PROJECT={project}",
        f"RENDERER={renderer}",
        f"PYTHON={PYTHON}",
    ]
    proc = run(command)
    try:
        payload = extract_last_json_object(proc.stdout)
    except ValueError as exc:
        if proc.returncode != 0:
            reason = (proc.stderr or proc.stdout or str(exc)).strip()
            payload = {
                "ok": False,
                "status": "blocked",
                "status_reasons": ["report_support_unavailable"],
                "report_support_contract": "",
                "synthesis_input_binding": {
                    "schema": "ztare-synthesis-input-binding-status-v1",
                    "status": "unavailable",
                    "reason": reason,
                },
                "error": reason,
            }
            return payload, display_command
        raise SystemExit(
            "forensic workbench report-support command returned no JSON\n"
            f"command: {shell_join(command)}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        ) from exc
    if proc.returncode == 0 and payload.get("status") == "blocked":
        raise SystemExit(f"report-support command returned inconsistent success: {payload}")
    return payload, display_command


def status_kind(status: str) -> str:
    normalized = status.lower()
    if any(token in normalized for token in ("blocked", "missing", "stale", "unbound", "attention", "unreadable")):
        return "attention"
    if any(token in normalized for token in ("ready", "fresh", "ok", "verified", "present", "available", "applied")):
        return "ready"
    return "neutral"


DISPLAY_STATUS_OVERRIDES = {
    "valid_packet": "valid intake",
    "invalid_packet": "invalid intake",
    "ready_for_in_loop_candidate": "ready for run",
    "ready_for_evidence_prepare": "ready for evidence prep",
    "report_blockers_present": "report blockers present",
    "synthesis_input_binding_unbound": "input binding unbound",
    "runtime_risks_present": "runtime risks present",
}


def display_status(status: str) -> str:
    return DISPLAY_STATUS_OVERRIDES.get(status, status.replace("_", " "))


def make_row(
    label: str,
    status: str,
    detail: str,
    *,
    file: str | Path | None = None,
    source: str | Path | None = None,
    evidence: str | Path | None = None,
    command: str | None = None,
    receipt: str | None = None,
    review_artifact: str | Path | None = None,
    warning: str | None = None,
) -> dict[str, str]:
    provenance = []
    if file:
        provenance.append(f"file={rel(file)}")
    if source:
        provenance.append(f"source={rel(source)}")
    if evidence:
        provenance.append(f"evidence={rel(evidence)}")
    if command:
        provenance.append(f"command={command}")
    if receipt:
        provenance.append(f"receipt={receipt}")
    if review_artifact:
        provenance.append(f"review_artifact={rel(review_artifact)}")
    if warning:
        provenance.append(f"warning={warning}")
    if not provenance:
        raise ValueError(f"row has no provenance: {label}")
    return {
        "label": label,
        "status": status,
        "kind": status_kind(status),
        "detail": detail,
        "file": rel(file),
        "source": rel(source),
        "evidence": rel(evidence),
        "command": command or "",
        "receipt": receipt or "",
        "review_artifact": rel(review_artifact),
        "warning": warning or "",
        "provenance": " | ".join(provenance),
    }


def latest_review_path(project: str) -> Path:
    return REPO / "projects" / project / "workspace" / "forensic_workbench_latest_review.json"


def latest_row_action_path(project: str) -> Path:
    return REPO / "projects" / project / "workspace" / "forensic_workbench_latest_row_action.json"


def latest_intake_edit_path(project: str) -> Path:
    return REPO / "projects" / project / "workspace" / "forensic_workbench_latest_intake_edit.json"


def latest_source_import_path(project: str) -> Path:
    return REPO / "projects" / project / "workspace" / "forensic_workbench_latest_source_import.json"


def latest_source_edit_path(project: str) -> Path:
    return REPO / "projects" / project / "workspace" / "forensic_workbench_latest_source_edit.json"


def latest_source_action_path(project: str) -> Path:
    return REPO / "projects" / project / "workspace" / "forensic_workbench_latest_source_action.json"


def latest_case_file_write_path(project: str) -> Path:
    return REPO / "projects" / project / "workspace" / "forensic_workbench_latest_case_file_write.json"


def case_key(project: str, intake: str | Path | None) -> str:
    intake_value = str(intake or "").strip()
    return f"{project}::{intake_value}" if intake_value else project


def receipt_matches_case(payload: dict[str, Any], *, project: str, intake: str | Path | None = None) -> bool:
    if payload.get("project") and payload.get("project") != project:
        return False
    intake_value = str(intake or "").strip()
    if not intake_value:
        return True
    payload_case_key = str(payload.get("case_key") or "").strip()
    if payload_case_key:
        return payload_case_key == case_key(project, intake_value)
    payload_intake = str(payload.get("intake") or "").strip()
    if payload_intake:
        return payload_intake == intake_value
    return True


def load_latest_review(project: str, intake: str | Path | None = None) -> tuple[dict[str, Any] | None, str]:
    path = latest_review_path(project)
    rel_path = rel(path)
    if not path.exists():
        return None, rel_path
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {
            "schema": "invalid-json",
            "status": "unreadable",
            "error": "latest review receipt is not valid JSON",
        }, rel_path
    if not isinstance(payload, dict):
        return {
            "schema": "invalid-json",
            "status": "unreadable",
            "error": "latest review receipt must be a JSON object",
        }, rel_path
    if not receipt_matches_case(payload, project=project, intake=intake):
        return None, rel_path
    return payload, rel_path


def load_latest_row_action(project: str, intake: str | Path | None = None) -> tuple[dict[str, Any] | None, str]:
    path = latest_row_action_path(project)
    rel_path = rel(path)
    if not path.exists():
        return None, rel_path
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {
            "schema": "invalid-json",
            "status": "unreadable",
            "error": "latest row action receipt is not valid JSON",
        }, rel_path
    if not isinstance(payload, dict):
        return {
            "schema": "invalid-json",
            "status": "unreadable",
            "error": "latest row action receipt must be a JSON object",
        }, rel_path
    if not receipt_matches_case(payload, project=project, intake=intake):
        return None, rel_path
    return payload, rel_path


def load_latest_intake_edit(project: str, intake: str | Path | None = None) -> tuple[dict[str, Any] | None, str]:
    path = latest_intake_edit_path(project)
    rel_path = rel(path)
    if not path.exists():
        return None, rel_path
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {
            "schema": "invalid-json",
            "status": "unreadable",
            "error": "latest intake edit receipt is not valid JSON",
        }, rel_path
    if not isinstance(payload, dict):
        return {
            "schema": "invalid-json",
            "status": "unreadable",
            "error": "latest intake edit receipt must be a JSON object",
        }, rel_path
    if not receipt_matches_case(payload, project=project, intake=intake):
        return None, rel_path
    return payload, rel_path


def build_rows(
    trace: dict[str, Any],
    report_contract: dict[str, Any],
    *,
    trace_command: str,
    report_command: str,
    latest_review: dict[str, Any] | None = None,
    latest_review_artifact_path: str | Path | None = None,
    latest_action: dict[str, Any] | None = None,
    latest_action_artifact_path: str | Path | None = None,
    latest_intake_edit: dict[str, Any] | None = None,
    latest_intake_edit_artifact_path: str | Path | None = None,
) -> list[dict[str, str]]:
    project = str(trace.get("project") or "")
    intake = trace.get("project_intake") or {}
    kernel = trace.get("kernel_entry") or {}
    surfaces = trace.get("surfaces") or {}
    readiness = surfaces.get("evidence_readiness") or {}
    source_receipt = surfaces.get("source_index_receipt") or {}
    loop = trace.get("loop_admission") or {}
    recent_loop = trace.get("recent_loop") or {}
    report_path = report_contract.get("report_support_contract")
    binding = report_contract.get("synthesis_input_binding") or {}
    intake_path = intake.get("intake_path") or intake.get("path")
    source_receipt_path = surfaces.get("source_index_receipt", {}).get("path")
    compile_provenance_path = surfaces.get("compile_provenance_path")
    review_artifact_path = rel(
        latest_review_artifact_path
        or f"projects/{project}/workspace/forensic_workbench_latest_review.json"
    )
    action_artifact_path = rel(
        latest_action_artifact_path
        or f"projects/{project}/workspace/forensic_workbench_latest_row_action.json"
    )
    intake_edit_artifact_path = rel(
        latest_intake_edit_artifact_path
        or f"projects/{project}/workspace/forensic_workbench_latest_intake_edit.json"
    )
    review_receipt_schema = str((latest_review or {}).get("schema") or "ztare-forensic-workbench-review-receipt-v1")
    if latest_review:
        review_decision = str(latest_review.get("decision") or "unknown")
        review_row = str(latest_review.get("row") or "unknown row")
        review_status = (
            "applied"
            if review_receipt_schema == "ztare-forensic-workbench-review-receipt-v1"
            else str(latest_review.get("status") or "unreadable")
        )
        review_detail = (
            f"{review_row}: {review_decision}; "
            f"evidence_refs={latest_review.get('evidence_ref_count', 0)}; "
            f"sha256={latest_review.get('review_file_sha256', 'missing')}"
        )
        review_warning = str(latest_review.get("error") or "")
    else:
        review_status = "no_review_applied"
        review_detail = "No saved review receipt has been applied for this project snapshot."
        review_warning = "no applied review receipt"
    action_receipt_schema = str((latest_action or {}).get("schema") or "ztare-forensic-workbench-row-action-receipt-v1")
    if latest_action:
        action_name = str(latest_action.get("action") or "unknown")
        action_row = str(latest_action.get("row") or "unknown row")
        action_status = (
            "applied"
            if action_receipt_schema == "ztare-forensic-workbench-row-action-receipt-v1"
            else str(latest_action.get("status") or "unreadable")
        )
        action_detail = (
            f"{action_row}: {action_name}; "
            f"evidence_refs={latest_action.get('evidence_ref_count', 0)}; "
            f"sha256={latest_action.get('action_file_sha256', 'missing')}"
        )
        action_warning = str(latest_action.get("error") or "")
    else:
        action_status = "no_action_saved"
        action_detail = "No saved row action has been applied for this project snapshot."
        action_warning = "no saved row action"
    intake_edit_receipt_schema = str((latest_intake_edit or {}).get("schema") or "ztare-forensic-workbench-intake-edit-receipt-v1")
    if latest_intake_edit:
        updated_fields = latest_intake_edit.get("updated_fields") or []
        if not isinstance(updated_fields, list):
            updated_fields = []
        intake_edit_status = (
            "applied"
            if intake_edit_receipt_schema == "ztare-forensic-workbench-intake-edit-receipt-v1"
            else str(latest_intake_edit.get("status") or "unreadable")
        )
        intake_edit_detail = (
            f"updated_fields={','.join(str(item) for item in updated_fields) or 'none'}; "
            f"after_sha256={latest_intake_edit.get('after_sha256', 'missing')}"
        )
        intake_edit_warning = str(latest_intake_edit.get("error") or "")
    else:
        intake_edit_status = "no_intake_edit_saved"
        intake_edit_detail = "No saved intake edit receipt has been applied for this project snapshot."
        intake_edit_warning = "no saved intake edit"

    bounded_claim = str(intake.get("bounded_claim") or "bounded claim unavailable")
    next_falsifier = intake.get("missing_ref_falsifier") or {}
    next_falsifier_status = str(next_falsifier.get("status") or "not surfaced")

    rows = [
        make_row(
            "Project",
            "present",
            f"{project} with rubric {trace.get('rubric')}",
            file=trace.get("project_dir"),
        ),
        make_row(
            "Bounded claim",
            str(intake.get("status") or "unknown"),
            bounded_claim,
            file=intake_path,
            source=intake_path,
        ),
        make_row(
            "Non-claims",
            f"{intake.get('non_claim_count', 0)} recorded",
            "Non-claim count is read from the intake boundary object.",
            file=intake_path,
            source=intake_path,
        ),
        make_row(
            "Source readiness",
            str(surfaces.get("source_preflight_status") or "unknown"),
            f"raw files={surfaces.get('raw_file_count', 0)}; untyped={surfaces.get('untyped_source_count', 0)}",
            command=trace_command,
            file=source_receipt_path,
            source=source_receipt_path,
            receipt=str(source_receipt.get("schema") or "source-index receipt"),
        ),
        make_row(
            "Evidence readiness",
            str(readiness.get("status") or "unknown"),
            (
                f"source_index={readiness.get('source_index_status')}; "
                f"output_binding={readiness.get('output_binding_status')}; "
                f"replay={readiness.get('replay_status')}"
            ),
            command=trace_command,
            file=compile_provenance_path,
            source=source_receipt_path,
            evidence=compile_provenance_path,
        ),
        make_row(
            "Run readiness",
            str(kernel.get("status") or trace.get("readiness") or "unknown"),
            f"ready_for_run={kernel.get('can_enter_kernel')}; readiness={kernel.get('readiness')}",
            command=trace_command,
            receipt=str(kernel.get("schema") or "run-readiness contract"),
        ),
        make_row(
            "Preflight",
            "available" if kernel.get("preflight_command") else "missing",
            str(kernel.get("preflight_command") or "no preflight command surfaced"),
            command=str(kernel.get("preflight_command") or trace_command),
            receipt="loop admission preflight path",
        ),
        make_row(
            "Loop admission",
            "available" if loop.get("available") else "missing",
            f"receipt_count={loop.get('receipt_count', 0)}; intake_hash_verified={loop.get('intake_hash_verified')}",
            command=trace_command,
            receipt="loop_admission",
        ),
        make_row(
            "Run history",
            "available" if recent_loop.get("available") else "missing",
            (
                f"eval_history_rows={recent_loop.get('eval_history_rows', 0)}; "
                f"latest_exit={recent_loop.get('latest_run_exit_reason')}"
            ),
            file=f"projects/{project}/workspace/eval_history.jsonl",
            evidence=f"projects/{project}/workspace/eval_history.jsonl",
        ),
        make_row(
            "Next falsifier",
            next_falsifier_status,
            str(next_falsifier.get("expected_error_fragment") or trace.get("readiness") or "no falsifier surfaced"),
            file=intake_path,
            source=intake_path,
        ),
        make_row(
            "Report/export",
            str(report_contract.get("status") or "unknown"),
            (
                "support contract blocks stale reports"
                if report_contract.get("status") == "blocked"
                else "support contract allows current report promotion"
            ),
            command=report_command,
            file=report_path,
            evidence=report_path,
            receipt=str(binding.get("schema") or "report support contract"),
            review_artifact=review_artifact_path,
        ),
        make_row(
            "Latest review receipt",
            review_status,
            review_detail,
            file=review_artifact_path if latest_review else None,
            review_artifact=review_artifact_path if latest_review else None,
            receipt=review_receipt_schema,
            warning=review_warning,
        ),
        make_row(
            "Latest row action",
            action_status,
            action_detail,
            file=action_artifact_path if latest_action else None,
            receipt=action_receipt_schema,
            warning=action_warning,
        ),
        make_row(
            "Latest intake edit",
            intake_edit_status,
            intake_edit_detail,
            file=intake_edit_artifact_path if latest_intake_edit else None,
            receipt=intake_edit_receipt_schema,
            warning=intake_edit_warning,
        ),
    ]
    return rows


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def render_row(row: dict[str, str], output_path: Path) -> str:
    path_links = []
    for key, label in (("file", "file"), ("source", "source"), ("evidence", "evidence"), ("review_artifact", "review")):
        if row.get(key):
            href = href_for(output_path, row[key])
            path_links.append(f'<span>{esc(label)}</span><a href="{esc(href)}">{esc(row[key])}</a>')
    command = f"<code>{esc(row['command'])}</code>" if row.get("command") else ""
    receipt = f"<code>{esc(row['receipt'])}</code>" if row.get("receipt") else ""
    warning = f"<span>{esc(row['warning'])}</span>" if row.get("warning") else ""
    evidence = " ".join(part for part in (*path_links, command, receipt, warning) if part)
    return "\n".join(
        [
            f'      <article class="row {esc(row["kind"])}" data-provenance="{esc(row["provenance"])}">',
            '        <div class="row-main">',
            f'          <div class="row-label">{esc(row["label"])}</div>',
            f'          <div class="row-detail">{esc(row["detail"])}</div>',
            f'          <div class="row-evidence">{evidence}</div>',
            "        </div>",
            f'        <div class="status">{esc(display_status(row["status"]))}</div>',
            "      </article>",
        ]
    )


def snapshot_payload(
    trace: dict[str, Any],
    report_contract: dict[str, Any],
    rows: list[dict[str, str]],
    *,
    output_path: Path,
    latest_review: dict[str, Any] | None = None,
    latest_review_artifact_path: str | Path | None = None,
    latest_action: dict[str, Any] | None = None,
    latest_action_artifact_path: str | Path | None = None,
    latest_intake_edit: dict[str, Any] | None = None,
    latest_intake_edit_artifact_path: str | Path | None = None,
) -> dict[str, Any]:
    project = str(trace.get("project") or DEFAULT_PROJECT)
    intake = (trace.get("project_intake") or {}).get("intake_path") or (trace.get("project_intake") or {}).get("path") or ""
    return {
        "schema": "ztare-forensic-workbench-snapshot-v1",
        "snapshot_scope": "single_project_read_model",
        "project": project,
        "project_source": f"projects/{project}",
        "intake": intake,
        "intake_source": intake_source_for_path(project, intake),
        "rubric": trace.get("rubric") or DEFAULT_RUBRIC,
        "readiness": trace.get("readiness_canonical") or trace.get("readiness") or "unknown",
        "report_status": report_contract.get("status") or "unknown",
        "status_reasons": report_contract.get("status_reasons") or [],
        "latest_review": latest_review or None,
        "latest_review_artifact": rel(latest_review_artifact_path) if latest_review_artifact_path else "",
        "latest_row_action": latest_action or None,
        "latest_row_action_artifact": rel(latest_action_artifact_path) if latest_action_artifact_path else "",
        "latest_intake_edit": latest_intake_edit or None,
        "latest_intake_edit_artifact": rel(latest_intake_edit_artifact_path) if latest_intake_edit_artifact_path else "",
        "rows": rows,
        "html_output": rel(output_path),
    }


def render_html(
    trace: dict[str, Any],
    report_contract: dict[str, Any],
    rows: list[dict[str, str]],
    *,
    output_path: Path,
) -> str:
    project = str(trace.get("project") or DEFAULT_PROJECT)
    rubric = str(trace.get("rubric") or DEFAULT_RUBRIC)
    readiness = str(trace.get("readiness_canonical") or trace.get("readiness") or "unknown")
    report_status = str(report_contract.get("status") or "unknown")
    blockers = report_contract.get("status_reasons") or []
    row_html = "\n".join(render_row(row, output_path).strip("\n") for row in rows)
    blocker_html = "".join(f"<li>{esc(item)}</li>" for item in blockers)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ZTARE Forensic Workbench Prototype</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #17201c;
      --muted: #5e6a64;
      --line: #ccd8d1;
      --ready: #176b4d;
      --attention: #9a4f11;
      --panel: #f7f9f6;
      --paper: #ffffff;
      --rail: #24483d;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--ink);
      background: #eef3ef;
      letter-spacing: 0;
    }}
    main {{
      min-height: 100vh;
      display: grid;
      grid-template-columns: minmax(260px, 340px) 1fr;
    }}
    aside {{
      background: #dfe9e3;
      border-right: 1px solid var(--line);
      padding: 24px;
    }}
    section {{
      padding: 24px;
    }}
    h1 {{
      margin: 0 0 10px;
      font-size: 30px;
      line-height: 1.1;
    }}
    h2 {{
      margin: 0 0 12px;
      font-size: 18px;
    }}
    p {{
      color: var(--muted);
      line-height: 1.45;
    }}
    code {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 12px;
      white-space: normal;
      overflow-wrap: anywhere;
    }}
    .summary {{
      display: grid;
      gap: 10px;
      margin-top: 24px;
    }}
    .metric {{
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.52);
      padding: 10px;
    }}
    .metric b {{
      display: block;
      font-size: 12px;
      text-transform: uppercase;
      color: var(--muted);
    }}
    .metric span {{
      display: block;
      margin-top: 4px;
      font-weight: 650;
      overflow-wrap: anywhere;
    }}
    .path {{
      display: grid;
      gap: 10px;
    }}
    .row {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(120px, 190px);
      gap: 16px;
      align-items: start;
      border: 1px solid var(--line);
      background: var(--paper);
      padding: 14px;
      border-left: 6px solid var(--rail);
    }}
    .row.ready {{ border-left-color: var(--ready); }}
    .row.attention {{ border-left-color: var(--attention); }}
    .row-label {{
      font-weight: 750;
      font-size: 16px;
    }}
    .row-detail {{
      margin-top: 4px;
      color: var(--muted);
      line-height: 1.35;
    }}
    .row-evidence {{
      display: grid;
      gap: 5px;
      margin-top: 9px;
      font-size: 12px;
    }}
    .status {{
      justify-self: end;
      border: 1px solid var(--line);
      background: var(--panel);
      padding: 7px 9px;
      font-size: 12px;
      font-weight: 700;
      overflow-wrap: anywhere;
      max-width: 190px;
    }}
    .blockers {{
      border: 1px solid var(--line);
      background: var(--panel);
      margin-top: 18px;
      padding: 14px;
    }}
    .blockers ul {{
      margin: 8px 0 0;
      padding-left: 18px;
      color: var(--muted);
    }}
    a {{ color: #14513e; }}
    @media (max-width: 860px) {{
      main {{ grid-template-columns: 1fr; }}
      aside {{ border-right: 0; border-bottom: 1px solid var(--line); }}
      .row {{ grid-template-columns: 1fr; }}
      .status {{ justify-self: start; max-width: 100%; }}
    }}
  </style>
</head>
<body>
  <main>
    <aside>
      <h1>Forensic Workbench Prototype</h1>
      <p>Local claim/evidence state for one bounded project. Every row exposes a file, command, receipt, or explicit warning.</p>
      <div class="summary">
        <div class="metric"><b>Project</b><span>{esc(project)}</span></div>
        <div class="metric"><b>Rubric</b><span>{esc(rubric)}</span></div>
        <div class="metric"><b>Run readiness</b><span>{esc(readiness)}</span></div>
        <div class="metric"><b>Report/export</b><span>{esc(report_status)}</span></div>
      </div>
      <div class="blockers">
        <h2>Export Blockers</h2>
        <ul>{blocker_html or "<li>none surfaced</li>"}</ul>
      </div>
    </aside>
    <section>
      <h2>First Five-Minute Path</h2>
      <div class="path">
{row_html}
      </div>
    </section>
  </main>
</body>
</html>
"""


def validate_rows(rows: list[dict[str, str]]) -> list[str]:
    errors: list[str] = []
    labels = {row.get("label") for row in rows}
    required = {
        "Project",
        "Bounded claim",
        "Source readiness",
        "Evidence readiness",
        "Run readiness",
        "Preflight",
        "Loop admission",
        "Report/export",
    }
    missing = sorted(required - labels)
    if missing:
        errors.append(f"missing rows: {missing}")
    for row in rows:
        if not row.get("provenance"):
            errors.append(f"row lacks provenance: {row.get('label')}")
    return errors


def build_snapshot(
    project: str,
    rubric: str,
    intake: str,
    renderer: str,
    output_path: Path,
) -> tuple[
    str,
    list[dict[str, str]],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any] | None,
    str,
    dict[str, Any] | None,
    str,
    dict[str, Any] | None,
    str,
]:
    project = validate_project_slug(project)
    intake = intake or default_intake_for_project(project)
    trace, trace_command = collect_trace(project, rubric, intake)
    report_contract, report_command = collect_report_contract(project, renderer)
    latest_review, latest_review_artifact_path = load_latest_review(project, intake)
    latest_action, latest_action_artifact_path = load_latest_row_action(project, intake)
    latest_intake_edit, latest_intake_edit_artifact_path = load_latest_intake_edit(project, intake)
    rows = build_rows(
        trace,
        report_contract,
        trace_command=trace_command,
        report_command=report_command,
        latest_review=latest_review,
        latest_review_artifact_path=latest_review_artifact_path,
        latest_action=latest_action,
        latest_action_artifact_path=latest_action_artifact_path,
        latest_intake_edit=latest_intake_edit,
        latest_intake_edit_artifact_path=latest_intake_edit_artifact_path,
    )
    errors = validate_rows(rows)
    if errors:
        raise SystemExit("forensic workbench snapshot contract failed: " + "; ".join(errors))
    html_text = render_html(trace, report_contract, rows, output_path=output_path)
    return (
        html_text,
        rows,
        trace,
        report_contract,
        latest_review,
        latest_review_artifact_path,
        latest_action,
        latest_action_artifact_path,
        latest_intake_edit,
        latest_intake_edit_artifact_path,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=DEFAULT_PROJECT)
    parser.add_argument("--rubric", default=DEFAULT_RUBRIC)
    parser.add_argument("--intake", default=DEFAULT_INTAKE)
    parser.add_argument("--renderer", default=DEFAULT_RENDERER)
    parser.add_argument("--out", default=DEFAULT_OUT)
    parser.add_argument("--json-out", default="", help="Optional JSON payload for the React prototype.")
    parser.add_argument("--check", action="store_true", help="Build and validate without writing the HTML file.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        validate_project_slug(args.project)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    output_path = (REPO / args.out).resolve() if not Path(args.out).is_absolute() else Path(args.out)
    (
        html_text,
        rows,
        trace,
        report_contract,
        latest_review,
        latest_review_artifact_path,
        latest_action,
        latest_action_artifact_path,
        latest_intake_edit,
        latest_intake_edit_artifact_path,
    ) = build_snapshot(
        args.project,
        args.rubric,
        args.intake,
        args.renderer,
        output_path,
    )
    payload = {
        "ok": True,
        "project": args.project,
        "rubric": args.rubric,
        "row_count": len(rows),
        "output": rel(output_path),
        "json_output": rel(args.json_out) if args.json_out else "",
        "written": not args.check,
    }
    if not args.check:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html_text, encoding="utf-8")
        if args.json_out:
            json_path = (REPO / args.json_out).resolve() if not Path(args.json_out).is_absolute() else Path(args.json_out)
            json_path.parent.mkdir(parents=True, exist_ok=True)
            data = snapshot_payload(
                trace,
                report_contract,
                rows,
                output_path=output_path,
                latest_review=latest_review,
                latest_review_artifact_path=latest_review_artifact_path,
                latest_action=latest_action,
                latest_action_artifact_path=latest_action_artifact_path,
                latest_intake_edit=latest_intake_edit,
                latest_intake_edit_artifact_path=latest_intake_edit_artifact_path,
            )
            json_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
