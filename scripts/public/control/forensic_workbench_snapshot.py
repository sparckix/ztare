#!/usr/bin/env python3
"""Render a static local forensic-workbench snapshot.

This D4 read model consumes one selected project's
intake, autoresearch trace, saved review record, and report-support contract outputs,
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
        REPO / "projects" / project / f"{project}_packet.json",
        REPO / "projects" / project / "project_packet.json",
        REPO / "examples" / "project_packets" / f"{project}_packet.json",
        REPO / "examples" / "project_packets" / f"ready_{project}_packet.json",
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

    def latest_receipt_path_for_case(primary: Path, ledger: Path, *, project: str, intake: str) -> str:
        primary_path = latest_path_for_case(primary, project=project, intake=intake)
        if primary_path:
            return primary_path
        payload, ledger_rel = latest_receipt_from_ledger(ledger, project=project, intake=intake)
        return ledger_rel if payload else ""

    def upsert_project_entry(project: str, intake: str, *, source: str) -> None:
        project = validate_project_slug(project)
        project_dir = REPO / "projects" / project
        latest_review = latest_review_path(project)
        latest_action = latest_row_action_path(project)
        latest_intake_edit = latest_intake_edit_path(project)
        latest_source_import = latest_source_import_path(project)
        latest_source_edit = latest_source_edit_path(project)
        latest_source_action = latest_source_action_path(project)
        latest_project_file_write = latest_project_file_write_path(project)
        latest_case_file_write = latest_case_file_write_path(project)
        report_contract = project_dir / "synthesis" / "report_support_contract.json"
        latest_action_receipt = latest_receipt_path_for_case(
            latest_action,
            row_action_ledger_path(project),
            project=project,
            intake=intake,
        )
        entry_key = case_key(project, intake)
        entry = entries_by_case.get(entry_key)
        if entry is None:
            entries_by_case[entry_key] = {
                "project": project,
                "rubric": project,
                "project_dir": rel(project_dir) if project_dir.exists() else "",
                "intake": intake,
                "intake_source": source,
                "latest_review": latest_receipt_path_for_case(
                    latest_review,
                    review_ledger_path(project),
                    project=project,
                    intake=intake,
                ),
                "latest_project_check": latest_action_receipt,
                "latest_item_action": latest_action_receipt,
                "latest_row_action": latest_action_receipt,
                "latest_intake_edit": latest_receipt_path_for_case(
                    latest_intake_edit,
                    intake_edit_ledger_path(project),
                    project=project,
                    intake=intake,
                ),
                "latest_source_import": latest_receipt_path_for_case(
                    latest_source_import,
                    source_import_ledger_path(project),
                    project=project,
                    intake=intake,
                ),
                "latest_source_edit": latest_receipt_path_for_case(
                    latest_source_edit,
                    source_edit_ledger_path(project),
                    project=project,
                    intake=intake,
                ),
                "latest_source_action": latest_receipt_path_for_case(
                    latest_source_action,
                    source_action_ledger_path(project),
                    project=project,
                    intake=intake,
                ),
                "latest_project_file_write": (
                    latest_receipt_path_for_case(
                        latest_project_file_write,
                        project_file_ledger_path(project),
                        project=project,
                        intake=intake,
                    )
                    or latest_receipt_path_for_case(
                        latest_case_file_write,
                        case_file_ledger_path(project),
                        project=project,
                        intake=intake,
                    )
                ),
                "latest_case_file_write": (
                    latest_receipt_path_for_case(
                        latest_project_file_write,
                        project_file_ledger_path(project),
                        project=project,
                        intake=intake,
                    )
                    or latest_receipt_path_for_case(
                        latest_case_file_write,
                        case_file_ledger_path(project),
                        project=project,
                        intake=intake,
                    )
                ),
                "report_contract": rel(report_contract) if report_contract.exists() else "",
            }
            return
        if project_dir.exists():
            entry["project_dir"] = rel(project_dir)
        if source == "project_local_intake":
            entry["intake"] = intake
            entry["intake_source"] = source
        entry_intake = str(entry.get("intake") or intake)
        for key, primary, ledger in (
            ("latest_review", latest_review, review_ledger_path(project)),
            ("latest_row_action", latest_action, row_action_ledger_path(project)),
            ("latest_intake_edit", latest_intake_edit, intake_edit_ledger_path(project)),
            ("latest_source_import", latest_source_import, source_import_ledger_path(project)),
            ("latest_source_edit", latest_source_edit, source_edit_ledger_path(project)),
            ("latest_source_action", latest_source_action, source_action_ledger_path(project)),
            ("latest_project_file_write", latest_project_file_write, project_file_ledger_path(project)),
            ("latest_case_file_write", latest_case_file_write, case_file_ledger_path(project)),
        ):
            latest_for_case = latest_receipt_path_for_case(
                primary,
                ledger,
                project=project,
                intake=entry_intake,
            )
            if latest_for_case:
                entry[key] = latest_for_case
                if key == "latest_row_action":
                    entry["latest_project_check"] = latest_for_case
                    entry["latest_item_action"] = latest_for_case
            elif entry_intake == intake:
                entry[key] = ""
                if key == "latest_row_action":
                    entry["latest_project_check"] = ""
                    entry["latest_item_action"] = ""
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


def list_project_folders(project_entries: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    projects_dir = REPO / "projects"
    if not projects_dir.exists():
        return []
    indexed_projects = {
        str(entry.get("project") or "")
        for entry in (project_entries or [])
        if entry.get("project")
    }
    folders: list[dict[str, Any]] = []
    for project_dir in sorted(path for path in projects_dir.iterdir() if path.is_dir()):
        project = project_dir.name
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", project):
            continue
        intakes = discover_project_intakes(project)
        raw_dir = project_dir / "raw"
        workspace_dir = project_dir / "workspace"
        raw_exists = raw_dir.exists()
        workspace_exists = workspace_dir.exists()
        source_type_map_exists = (raw_dir / "source_type_map.json").exists()
        raw_file_count, raw_file_count_capped = bounded_file_count(raw_dir, exclude_names={"source_type_map.json"})
        raw_source_file_count, raw_source_file_count_capped = bounded_file_count(
            raw_dir,
            suffixes={".md", ".txt"},
            exclude_names={"source_type_map.json"},
        )
        workspace_file_count, workspace_file_count_capped = bounded_file_count(workspace_dir)
        raw_preview_files = bounded_file_samples(
            raw_dir,
            suffixes={".md", ".txt"},
            exclude_names={"source_type_map.json"},
        )
        root_source_file_count, root_source_file_count_capped = bounded_project_root_source_count(project_dir)
        root_preview_files = bounded_project_root_source_samples(project_dir)
        source_preview_files = raw_preview_files or root_preview_files
        workspace_preview_files = bounded_file_samples(workspace_dir)
        folders.append(
            {
                "project": project,
                "project_dir": rel(project_dir),
                "intake_count": len(intakes),
                "raw_exists": raw_exists,
                "raw_file_count": raw_file_count,
                "raw_file_count_capped": raw_file_count_capped,
                "raw_source_file_count": raw_source_file_count,
                "raw_source_file_count_capped": raw_source_file_count_capped,
                "raw_preview_files": raw_preview_files,
                "root_source_file_count": root_source_file_count,
                "root_source_file_count_capped": root_source_file_count_capped,
                "root_preview_files": root_preview_files,
                "source_preview_files": source_preview_files,
                "workspace_exists": workspace_exists,
                "workspace_file_count": workspace_file_count,
                "workspace_file_count_capped": workspace_file_count_capped,
                "workspace_preview_files": workspace_preview_files,
                "source_type_map_exists": source_type_map_exists,
                "openable": project in indexed_projects,
                "status": "intake_ready" if project in indexed_projects else "needs_intake",
            }
        )
    return folders


def project_root_source_candidates(root: Path) -> list[Path]:
    if not root.exists() or not root.is_dir():
        return []
    allowed_suffixes = {".md", ".txt", ".json"}
    excluded_names = {
        "project_intake.json",
        "source_type_map.json",
    }
    priority_names = {
        "thesis.md": 0,
        "project_charter.md": 1,
        "evidence.txt": 2,
        "current_iteration.md": 3,
        "latest_eval_results.json": 4,
        "latest_probability_dag.json": 5,
    }
    candidates = [
        path
        for path in root.iterdir()
        if path.is_file()
        and path.suffix.lower() in allowed_suffixes
        and path.name not in excluded_names
        and not path.name.endswith("_intake.json")
    ]
    return sorted(candidates, key=lambda path: (priority_names.get(path.name, 50), path.name.lower()))


def bounded_project_root_source_count(root: Path, *, limit: int = 500) -> tuple[int, bool]:
    count = len(project_root_source_candidates(root))
    return (min(count, limit), count >= limit)


def bounded_project_root_source_samples(root: Path, *, limit: int = 3) -> list[str]:
    return [rel(path) for path in project_root_source_candidates(root)[:limit]]


def bounded_file_count(
    root: Path,
    *,
    suffixes: set[str] | None = None,
    exclude_names: set[str] | None = None,
    limit: int = 500,
) -> tuple[int, bool]:
    if not root.exists() or not root.is_dir():
        return 0, False
    suffixes = {suffix.lower() for suffix in suffixes or set()}
    exclude_names = exclude_names or set()
    count = 0
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.name in exclude_names:
            continue
        if suffixes and path.suffix.lower() not in suffixes:
            continue
        count += 1
        if count >= limit:
            return count, True
    return count, False


def bounded_file_samples(
    root: Path,
    *,
    suffixes: set[str] | None = None,
    exclude_names: set[str] | None = None,
    limit: int = 3,
) -> list[str]:
    if not root.exists() or not root.is_dir():
        return []
    suffixes = {suffix.lower() for suffix in suffixes or set()}
    exclude_names = exclude_names or set()
    samples: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.name in exclude_names:
            continue
        if suffixes and path.suffix.lower() not in suffixes:
            continue
        samples.append(rel(path))
        if len(samples) >= limit:
            break
    return samples


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


def read_repo_json_field(path: str | Path | None, field: str) -> str:
    if not path:
        return ""
    value = Path(str(path))
    target = value if value.is_absolute() else REPO / value
    try:
        resolved = target.resolve()
        resolved.relative_to(REPO.resolve())
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return ""
    if not isinstance(payload, dict):
        return ""
    return str(payload.get(field) or "").strip()


def read_repo_json(path: str | Path | None) -> dict[str, Any]:
    if not path:
        return {}
    value = Path(str(path))
    target = value if value.is_absolute() else REPO / value
    try:
        resolved = target.resolve()
        resolved.relative_to(REPO.resolve())
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def project_assumption_summary(project: str) -> dict[str, str]:
    workspace_constraints = Path("projects") / project / "workspace" / "derived_constraints.json"
    latest_eval = Path("projects") / project / "latest_eval_results.json"
    constraints_payload = read_repo_json(workspace_constraints)
    eval_payload = read_repo_json(latest_eval)
    if constraints_payload:
        confirmed = constraints_payload.get("confirmed_constraints") or []
        provisional = constraints_payload.get("provisional_constraints") or []
        confirmed_count = len(confirmed) if isinstance(confirmed, list) else 0
        provisional_count = len(provisional) if isinstance(provisional, list) else 0
        return {
            "status": "recorded" if confirmed_count or provisional_count else "none recorded",
            "detail": f"{confirmed_count} confirmed constraints; {provisional_count} provisional constraints.",
            "file": rel(workspace_constraints),
        }
    derived = eval_payload.get("derived_constraints") or []
    verified = eval_payload.get("verified_axioms") or []
    retired = eval_payload.get("retired_axioms_approved") or []
    derived_count = len(derived) if isinstance(derived, list) else 0
    verified_count = len(verified) if isinstance(verified, list) else 0
    retired_count = len(retired) if isinstance(retired, list) else 0
    if eval_payload:
        return {
            "status": "recorded" if derived_count or verified_count or retired_count else "none recorded",
            "detail": (
                f"{verified_count} verified assumptions; {retired_count} retired; "
                f"{derived_count} derived constraints."
            ),
            "file": rel(latest_eval),
        }
    return {
        "status": "not loaded",
        "detail": "No assumptions or constraints file is loaded for this project yet.",
        "file": f"projects/{project}",
    }


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
    if proc.returncode != 0 or not proc.stdout.strip():
        raise SystemExit(
            "forensic workbench trace command failed\n"
            f"command: {shell_join(command)}\n"
            f"returncode: {proc.returncode}\n"
            f"PYTHON env: {os.environ.get('PYTHON')!r}  MAKEFLAGS: {os.environ.get('MAKEFLAGS')!r}\n"
            f"STDOUT[:400]: {proc.stdout[:400]!r}\n"
            f"STDERR[:1200]:\n{proc.stderr[:1200]}"
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
    "blocked": "needs support",
    "valid_packet": "valid project brief",
    "missing_packet": "missing evidence file",
    "invalid_packet": "invalid project brief",
    "ready_for_in_loop_candidate": "ready for run",
    "ready_for_evidence_prepare": "ready for evidence prep",
    "report_blockers_present": "report needs support",
    "synthesis_input_binding_unbound": "report input is not connected",
    "runtime_risks_present": "runtime risks present",
    "loop_admission": "readiness check",
    "no_action_saved": "no next step saved",
    "no_intake_edit_saved": "no saved project brief change",
    "no_review_applied": "no review saved",
}


def display_status(status: str) -> str:
    return DISPLAY_STATUS_OVERRIDES.get(status, status.replace("_", " "))


def display_detail(value: object) -> str:
    text = str(value or "")
    for raw, rendered in sorted(DISPLAY_STATUS_OVERRIDES.items(), key=lambda item: len(item[0]), reverse=True):
        text = re.sub(rf"\b{re.escape(raw)}\b", rendered, text)
    return (
        text.replace("Report/export", "Report readiness")
        .replace("Report support", "Report readiness")
        .replace("report support", "report readiness")
        .replace("evidence refs", "evidence files")
        .replace("next review surface", "next review step")
        .replace("receipt checks", "saved-history checks")
        .replace("Reject or demote the claim if ", "Revise the diagnosis if ")
        .replace("ready_for_run=True", "ready for run: yes")
        .replace("ready_for_run=False", "ready for run: no")
        .replace("intake_hash_verified=True", "intake hash verified: yes")
        .replace("intake_hash_verified=False", "intake hash verified: no")
        .replace("receipt_count=", "saved changes: ")
        .replace("readiness saved records", "readiness checks")
        .replace("saved records", "saved changes")
        .replace("saved record", "saved work")
        .replace("next_step", "next step")
        .replace("ready_to_run", "ready to run")
        .replace("needs_source", "needs source")
        .replace("export_blocker", "fix report readiness")
        .replace("eval_history_rows=", "run records: ")
        .replace("latest_exit=", "latest exit: ")
        .replace("source_index=", "file index: ")
        .replace("source index:", "file index:")
        .replace("output_binding=", "evidence connection: ")
        .replace("output binding:", "evidence connection:")
        .replace("replay=", "replay: ")
        .replace("readiness=", "readiness: ")
        .replace("evidence_refs[", "evidence file ")
        .replace("]", "")
        .replace("row action", "next step")
        .replace("row-action", "next-step")
        .replace("item action", "next step")
        .replace("blocked", "needs attention")
    )


def display_check_label(label: str) -> str:
    label_overrides = {
        "Bounded claim": "Working diagnosis",
        "Non-claims": "Ruled-out alternatives",
        "Assumptions and constraints": "Assumptions and constraints",
        "Source readiness": "Source files",
        "Evidence readiness": "Evidence files",
        "Run readiness": "Run check",
        "Loop admission": "Readiness check",
        "Next falsifier": "What would change it",
        "Latest saved review": "Latest review",
        "Latest intake edit": "Latest intake change",
    }
    if label in label_overrides:
        return label_overrides[label]
    if label in {"Report/export", "Report support"}:
        return "Report readiness"
    return label or "unknown check"


def display_review_decision(decision: str) -> str:
    if decision == "blocked":
        return "hold report"
    return display_status(decision)


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
    rendered_detail = display_detail(detail)
    return {
        "label": label,
        "display_label": display_check_label(label),
        "status": status,
        "display_status": display_status(status),
        "kind": status_kind(status),
        "detail": detail,
        "display_detail": rendered_detail,
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


def review_ledger_path(project: str) -> Path:
    return REPO / "projects" / project / "workspace" / "forensic_workbench_reviews.jsonl"


def row_action_ledger_path(project: str) -> Path:
    return REPO / "projects" / project / "workspace" / "forensic_workbench_row_actions.jsonl"


def intake_edit_ledger_path(project: str) -> Path:
    return REPO / "projects" / project / "workspace" / "forensic_workbench_intake_edits.jsonl"


def source_import_ledger_path(project: str) -> Path:
    return REPO / "projects" / project / "workspace" / "forensic_workbench_source_imports.jsonl"


def source_edit_ledger_path(project: str) -> Path:
    return REPO / "projects" / project / "workspace" / "forensic_workbench_source_edits.jsonl"


def source_action_ledger_path(project: str) -> Path:
    return REPO / "projects" / project / "workspace" / "forensic_workbench_source_actions.jsonl"


def case_file_ledger_path(project: str) -> Path:
    return REPO / "projects" / project / "workspace" / "forensic_workbench_case_files.jsonl"


def project_file_ledger_path(project: str) -> Path:
    return REPO / "projects" / project / "workspace" / "forensic_workbench_project_files.jsonl"


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


def latest_project_file_write_path(project: str) -> Path:
    return REPO / "projects" / project / "workspace" / "forensic_workbench_latest_project_file_write.json"


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


def latest_receipt_from_ledger(
    ledger_path: Path,
    *,
    project: str,
    intake: str | Path | None = None,
) -> tuple[dict[str, Any] | None, str]:
    rel_path = rel(ledger_path)
    if not ledger_path.exists():
        return None, rel_path
    rows = ledger_path.read_text(encoding="utf-8").splitlines()
    for line in reversed(rows):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and receipt_matches_case(payload, project=project, intake=intake):
            return payload, rel_path
    return None, rel_path


def load_latest_review(project: str, intake: str | Path | None = None) -> tuple[dict[str, Any] | None, str]:
    path = latest_review_path(project)
    rel_path = rel(path)
    if not path.exists():
        return latest_receipt_from_ledger(review_ledger_path(project), project=project, intake=intake)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {
            "schema": "invalid-json",
            "status": "unreadable",
            "error": "latest saved review is not valid JSON",
        }, rel_path
    if not isinstance(payload, dict):
        return {
            "schema": "invalid-json",
            "status": "unreadable",
            "error": "latest saved review must be a JSON object",
        }, rel_path
    if not receipt_matches_case(payload, project=project, intake=intake):
        fallback, fallback_path = latest_receipt_from_ledger(
            review_ledger_path(project),
            project=project,
            intake=intake,
        )
        return fallback, fallback_path if fallback else rel_path
    return payload, rel_path


def load_latest_row_action(project: str, intake: str | Path | None = None) -> tuple[dict[str, Any] | None, str]:
    path = latest_row_action_path(project)
    rel_path = rel(path)
    if not path.exists():
        return latest_receipt_from_ledger(row_action_ledger_path(project), project=project, intake=intake)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {
            "schema": "invalid-json",
            "status": "unreadable",
            "error": "latest saved next-step receipt is not valid JSON",
        }, rel_path
    if not isinstance(payload, dict):
        return {
            "schema": "invalid-json",
            "status": "unreadable",
            "error": "latest saved next-step receipt must be a JSON object",
        }, rel_path
    if not receipt_matches_case(payload, project=project, intake=intake):
        fallback, fallback_path = latest_receipt_from_ledger(
            row_action_ledger_path(project),
            project=project,
            intake=intake,
        )
        return fallback, fallback_path if fallback else rel_path
    return payload, rel_path


def load_latest_intake_edit(project: str, intake: str | Path | None = None) -> tuple[dict[str, Any] | None, str]:
    path = latest_intake_edit_path(project)
    rel_path = rel(path)
    if not path.exists():
        return latest_receipt_from_ledger(intake_edit_ledger_path(project), project=project, intake=intake)
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
        fallback, fallback_path = latest_receipt_from_ledger(
            intake_edit_ledger_path(project),
            project=project,
            intake=intake,
        )
        return fallback, fallback_path if fallback else rel_path
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
        review_decision = display_review_decision(str(latest_review.get("decision") or "unknown"))
        review_row = display_check_label(str(latest_review.get("row") or "unknown check"))
        review_status = (
            "applied"
            if review_receipt_schema == "ztare-forensic-workbench-review-receipt-v1"
            else str(latest_review.get("status") or "unreadable")
        )
        review_detail = (
            f"{review_row}: {review_decision}; "
            f"{latest_review.get('evidence_ref_count', 0)} evidence files; "
            f"hash {latest_review.get('review_file_sha256', 'missing')}"
        )
        review_warning = str(latest_review.get("error") or "")
    else:
        review_status = "no_review_applied"
        review_detail = "No saved review record has been applied for this project data."
        review_warning = "no saved review record"
    action_receipt_schema = str((latest_action or {}).get("schema") or "ztare-forensic-workbench-row-action-receipt-v1")
    if latest_action:
        action_name = str(latest_action.get("action") or "unknown")
        action_row = display_check_label(str(latest_action.get("row") or "unknown check"))
        action_status = (
            "applied"
            if action_receipt_schema == "ztare-forensic-workbench-row-action-receipt-v1"
            else str(latest_action.get("status") or "unreadable")
        )
        action_detail = (
            f"{action_row}: {action_name}; "
            f"{latest_action.get('evidence_ref_count', 0)} evidence files; "
            f"hash {latest_action.get('action_file_sha256', 'missing')}"
        )
        action_warning = str(latest_action.get("error") or "")
    else:
        action_status = "no_action_saved"
        action_detail = "No saved next step has been applied for this project data."
        action_warning = "no saved next step"
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
            f"changed fields: {', '.join(str(item) for item in updated_fields) or 'none'}; "
            f"after hash {latest_intake_edit.get('after_sha256', 'missing')}"
        )
        intake_edit_warning = str(latest_intake_edit.get("error") or "")
    else:
        intake_edit_status = "no_intake_edit_saved"
        intake_edit_detail = "No saved project-brief edit has been applied for this project data."
        intake_edit_warning = "no saved intake edit"

    bounded_claim = str(intake.get("bounded_claim") or "bounded claim unavailable")
    next_falsifier = intake.get("missing_ref_falsifier") or {}
    next_falsifier_text = str(intake.get("next_falsifier") or "").strip() or read_repo_json_field(intake_path, "next_falsifier")
    next_falsifier_status = "recorded" if next_falsifier_text else str(next_falsifier.get("status") or "not loaded")
    next_falsifier_detail = next_falsifier_text or str(
        next_falsifier.get("expected_error_fragment") or trace.get("readiness") or "no falsifier surfaced"
    )
    next_falsifier_warning = "" if next_falsifier_text else str(next_falsifier.get("expected_error_fragment") or "")
    assumption_summary = project_assumption_summary(project)

    rows = [
        make_row(
            "Project",
            "present",
            f"{project}; scoring guide {trace.get('rubric')}",
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
            f"{intake.get('non_claim_count', 0)} alternatives are recorded as weaker, out of scope, or not supported.",
            file=intake_path,
            source=intake_path,
        ),
        make_row(
            "Assumptions and constraints",
            assumption_summary["status"],
            assumption_summary["detail"],
            file=assumption_summary["file"],
            evidence=assumption_summary["file"],
        ),
        make_row(
            "Source readiness",
            str(surfaces.get("source_preflight_status") or "unknown"),
            (
                f"{surfaces.get('raw_file_count', 0)} source files; "
                f"{surfaces.get('untyped_source_count', 0)} untyped"
            ),
            command=trace_command,
            file=source_receipt_path,
            source=source_receipt_path,
            receipt=str(source_receipt.get("schema") or "source-index saved work"),
        ),
        make_row(
            "Evidence readiness",
            str(readiness.get("status") or "unknown"),
            (
                f"file index: {display_status(str(readiness.get('source_index_status') or 'unknown'))}; "
                f"evidence connection: {display_status(str(readiness.get('output_binding_status') or 'unknown'))}; "
                f"replay: {display_status(str(readiness.get('replay_status') or 'unknown'))}"
            ),
            command=trace_command,
            file=compile_provenance_path,
            source=source_receipt_path,
            evidence=compile_provenance_path,
        ),
        make_row(
            "Run readiness",
            str(kernel.get("status") or trace.get("readiness") or "unknown"),
            (
                f"ready for run: {'yes' if kernel.get('can_enter_kernel') else 'no'}; "
                f"readiness: {display_status(str(kernel.get('readiness') or 'unknown'))}"
            ),
            command=trace_command,
            receipt=str(kernel.get("schema") or "run-readiness contract"),
        ),
        make_row(
            "Readiness check",
            "available" if kernel.get("preflight_command") else "missing",
            "Run the readiness check before starting a project run."
            if kernel.get("preflight_command")
            else "No readiness check command is available yet.",
            command=str(kernel.get("preflight_command") or trace_command),
            receipt="loop admission readiness path",
        ),
        make_row(
            "Readiness history",
            "available" if loop.get("available") else "missing",
            f"readiness checks: {loop.get('receipt_count', 0)}; project brief hash verified: {'yes' if loop.get('intake_hash_verified') else 'no'}",
            command=trace_command,
            receipt="loop_admission",
        ),
        make_row(
            "Run history",
            "available" if recent_loop.get("available") else "missing",
            (
                f"{recent_loop.get('eval_history_rows', 0)} run records; "
                f"latest exit: {display_status(str(recent_loop.get('latest_run_exit_reason') or 'unknown'))}"
            ),
            file=f"projects/{project}/workspace/eval_history.jsonl",
            evidence=f"projects/{project}/workspace/eval_history.jsonl",
        ),
        make_row(
            "Next falsifier",
            next_falsifier_status,
            next_falsifier_detail,
            file=intake_path,
            source=intake_path,
            warning=next_falsifier_warning,
        ),
        make_row(
            "Report readiness",
            str(report_contract.get("status") or "unknown"),
            (
                "The report needs refreshed support before it is safe to use."
                if report_contract.get("status") == "blocked"
                else "Report readiness is current."
            ),
            command=report_command,
            file=report_path,
            evidence=report_path,
            receipt=str(binding.get("schema") or "report support contract"),
            review_artifact=review_artifact_path,
        ),
        make_row(
            "Latest saved review",
            review_status,
            review_detail,
            file=review_artifact_path if latest_review else None,
            review_artifact=review_artifact_path if latest_review else None,
            receipt=review_receipt_schema,
            warning=review_warning,
        ),
        make_row(
            "Latest next step",
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


def display_receipt_label(value: object) -> str:
    text = str(value or "").strip()
    receipt_overrides = {
        "loop_admission": "readiness check",
        "loop admission preflight path": "readiness history path",
        "loop admission readiness path": "readiness history path",
        "ztare-forensic-workbench-row-action-receipt-v1": "next-step saved work",
        "ztare-forensic-workbench-review-receipt-v1": "review saved work",
        "ztare-forensic-workbench-intake-edit-receipt-v1": "project-brief saved work",
        "ztare-forensic-workbench-source-import-receipt-v1": "source-import saved work",
        "ztare-forensic-workbench-source-edit-receipt-v1": "source-edit saved work",
        "ztare-forensic-workbench-source-action-receipt-v1": "source/evidence saved work",
        "ztare-forensic-workbench-project-file-write-receipt-v1": "project-file saved work",
        "ztare-forensic-workbench-case-file-write-receipt-v1": "project-file saved work",
        "ztare-source-index-receipt-v1": "source-index saved work",
        "ztare-kernel-entry-contract-v1": "run readiness history",
        "ztare-synthesis-input-binding-status-v1": "report readiness history",
    }
    return receipt_overrides.get(text, display_detail(text))


def render_row(row: dict[str, str], output_path: Path) -> str:
    path_links = []
    for key, label in (("file", "file"), ("source", "source"), ("evidence", "evidence"), ("review_artifact", "review")):
        if row.get(key):
            href = href_for(output_path, row[key])
            path_links.append(f'<span>{esc(label)}</span><a href="{esc(href)}">{esc(row[key])}</a>')
    command = f"<code>{esc(row['command'])}</code>" if row.get("command") else ""
    receipt = f"<code>{esc(display_receipt_label(row['receipt']))}</code>" if row.get("receipt") else ""
    warning = f"<span>{esc(row['warning'])}</span>" if row.get("warning") else ""
    evidence = " ".join(part for part in (*path_links, command, receipt, warning) if part)
    return "\n".join(
        [
            f'      <article class="row {esc(row["kind"])}" data-provenance="{esc(row["provenance"])}">',
            '        <div class="row-main">',
            f'          <div class="row-label">{esc(display_check_label(row["label"]))}</div>',
            f'          <div class="row-detail">{esc(display_detail(row["detail"]))}</div>',
            f'          <div class="row-evidence">{evidence}</div>',
            "        </div>",
            f'        <div class="status">{esc(display_status(row["status"]))}</div>',
            "      </article>",
        ]
    )


def display_receipt_payload(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not payload:
        return None
    rendered = dict(payload)
    row_label = display_check_label(str(rendered.get("row") or ""))
    slug = str(rendered.get("item_slug") or rendered.get("row_slug") or "")
    if slug in {"report_export", "report_support"}:
        row_label = "Report readiness"
    if row_label:
        rendered["row"] = row_label
        rendered["check_label"] = row_label
        rendered["display_label"] = row_label
        if str(rendered.get("item_label") or "") in {"", "Report", "Report/export", "Report support"}:
            rendered["item_label"] = row_label
    if rendered.get("note"):
        rendered["note"] = display_detail(rendered.get("note"))
    return rendered


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
    items = rows
    display_readiness = display_status(str(trace.get("readiness_canonical") or trace.get("readiness") or "unknown"))
    display_report_status = display_status(str(report_contract.get("status") or "unknown"))
    return {
        "schema": "ztare-forensic-workbench-snapshot-v1",
        "snapshot_scope": "single_project_read_model",
        "project": project,
        "project_source": f"projects/{project}",
        "intake": intake,
        "intake_source": intake_source_for_path(project, intake),
        "rubric": trace.get("rubric") or DEFAULT_RUBRIC,
        "readiness": trace.get("readiness_canonical") or trace.get("readiness") or "unknown",
        "display_readiness": display_readiness,
        "report_status": report_contract.get("status") or "unknown",
        "display_report_status": display_report_status,
        "status_reasons": report_contract.get("status_reasons") or [],
        "latest_review": display_receipt_payload(latest_review),
        "latest_review_artifact": rel(latest_review_artifact_path) if latest_review_artifact_path else "",
        "latest_project_check": display_receipt_payload(latest_action),
        "latest_project_check_artifact": rel(latest_action_artifact_path) if latest_action_artifact_path else "",
        "latest_item_action": display_receipt_payload(latest_action),
        "latest_item_action_artifact": rel(latest_action_artifact_path) if latest_action_artifact_path else "",
        "latest_row_action": display_receipt_payload(latest_action),
        "latest_row_action_artifact": rel(latest_action_artifact_path) if latest_action_artifact_path else "",
        "project_check_count": len(items),
        "latest_intake_edit": latest_intake_edit or None,
        "latest_intake_edit_artifact": rel(latest_intake_edit_artifact_path) if latest_intake_edit_artifact_path else "",
        "item_count": len(items),
        "row_count": len(items),
        "project_checks": items,
        "items": items,
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
    blocker_html = "".join(f"<li>{esc(display_status(str(item)))}</li>" for item in blockers)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ZTARE Project Workbench</title>
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
      <h1>Project Workbench</h1>
      <p>Local project state. Every check exposes a file, local step plan, saved history, or explicit warning.</p>
      <div class="summary">
        <div class="metric"><b>Project</b><span>{esc(project)}</span></div>
        <div class="metric"><b>Scoring</b><span>{esc(rubric)}</span></div>
        <div class="metric"><b>Run check</b><span>{esc(display_status(readiness))}</span></div>
        <div class="metric"><b>Report readiness</b><span>{esc(display_status(report_status))}</span></div>
      </div>
      <div class="blockers">
        <h2>Report readiness</h2>
        <ul>{blocker_html or "<li>none open</li>"}</ul>
      </div>
    </aside>
    <section>
      <h2>Project path</h2>
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
        "Readiness check",
        "Readiness history",
        "Report readiness",
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
    # `collect_trace` (~8s) and `collect_report_contract` (~7s) are INDEPENDENT, I/O-bound subprocess shell-outs
    # (the profiler showed 15.7s of the 15.7s total is select.poll waiting on these two, run sequentially). They
    # release the GIL while waiting, so running them concurrently makes the snapshot bound by the SLOWER one
    # (~8s) instead of their sum (~16s) — a 2x cut to the loading spinner, no logic change. (2026-07-10 perf.)
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=2) as _pool:
        _trace_future = _pool.submit(collect_trace, project, rubric, intake)
        _report_future = _pool.submit(collect_report_contract, project, renderer)
        trace, trace_command = _trace_future.result()
        report_contract, report_command = _report_future.result()
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
        "item_count": len(rows),
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
