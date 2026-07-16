#!/usr/bin/env python3
"""Local API for the D4 Project Workbench."""
from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import math
import mimetypes
import os
import re
import subprocess
import shlex
import sys
import tempfile
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import parse_qs, urlparse

# The workbench is routinely launched as a script (Makefile/live helper), where
# Python otherwise prefers an installed `ztare` distribution over this checkout.
# Put the checkout's source tree first before importing any kernel module.
_WORKBENCH_REPO = Path(__file__).resolve().parents[3]
for _path in (str(_WORKBENCH_REPO), str(_WORKBENCH_REPO / "src")):
    if _path in sys.path:
        sys.path.remove(_path)
    sys.path.insert(0, _path)

import forensic_workbench_snapshot as snapshot
import forensic_workbench_review as review
import reasoning_compiler_capability_audit as capability_audit
from ztare.workspace import project_brief as project_brief_core
from ztare.workspace import project_charter as project_charter_core
from ztare.workspace import project_check as project_check_core
from ztare.workspace import project_file as project_file_core
from ztare.workspace import recent_changes as recent_changes_core
from ztare.workspace import report_actions as report_actions_core
from ztare.workspace import research_map as research_map_core
from ztare.workspace import scoring_guide as scoring_guide_core
from ztare.workspace import source_actions as source_actions_core
from ztare.workspace import source_files as source_files_core
from ztare.workspace import workbench_settings as settings_core
from ztare.workspace import workbench_contracts as workbench_contracts_core
from ztare.workspace.server_payloads import leanmill as leanmill_payloads
from ztare.common.storage import FileStorage
from ztare.workspace import claim_support as claim_support_core
from ztare.workspace import claim_card as claim_card_core
from ztare.workspace.compile_evidence import load_active_evidence_gaps
from ztare.validator.core.compression_progress import (
    CompressionObservation,
    evaluate_compression_progress,
)
from ztare.reports.compression_progress_report import dag_observations_from_history

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
DEFAULT_DEV_ORIGIN = "http://127.0.0.1:5174"
MAX_PREVIEW_BYTES = 200_000
WORKBENCH_ROOT = snapshot.REPO / "forensic-workbench"
WORKBENCH_DIST = WORKBENCH_ROOT / "dist"
WORKBENCH_PUBLIC = WORKBENCH_ROOT / "public"
PUBLIC_PROJECTS_PATH = WORKBENCH_ROOT / "public-projects.json"
PROJECT_SCOPE = str(os.environ.get("ZTARE_WORKBENCH_PROJECT_SCOPE") or "local").strip().lower()
PROJECT_ALLOWLIST = {
    item.strip()
    for item in str(os.environ.get("ZTARE_WORKBENCH_PROJECTS") or "").split(",")
    if item.strip()
}
FILE_PREVIEW_ALLOWED_ROOTS = recent_changes_core.FILE_PREVIEW_ALLOWED_ROOTS
FILE_PREVIEW_ALLOWED_FILES = recent_changes_core.FILE_PREVIEW_ALLOWED_FILES
FILE_PREVIEW_BLOCKED_PARTS = recent_changes_core.FILE_PREVIEW_BLOCKED_PARTS
INTAKE_EDIT_SCHEMA = project_brief_core.INTAKE_EDIT_SCHEMA
CHARTER_SCHEMA = "ztare-forensic-workbench-charter-v1"
CHARTER_EDIT_SCHEMA = project_charter_core.CHARTER_EDIT_SCHEMA
RECEIPT_HISTORY_SCHEMA = "ztare-forensic-workbench-receipt-history-v1"
REPORT_CONTRACT_SCHEMA = "ztare-forensic-workbench-report-contract-v1"
REPORT_CONTRACT_REFRESH_RECEIPT_SCHEMA = report_actions_core.REPORT_CONTRACT_REFRESH_RECEIPT_SCHEMA
REPORT_SYNTHESIS_SCHEMA = report_actions_core.REPORT_SYNTHESIS_SCHEMA
PROJECT_TEST_SCHEMA = project_check_core.PROJECT_TEST_SCHEMA
PROJECT_TEST_RECEIPT_SCHEMA = project_check_core.PROJECT_TEST_RECEIPT_SCHEMA
PREFLIGHT_SCHEMA = "ztare-forensic-workbench-preflight-v1"
BOUNDED_RUN_SCHEMA = "ztare-forensic-workbench-bounded-run-v1"
RUN_HISTORY_SCHEMA = "ztare-forensic-workbench-run-history-v1"
CLAIM_SUPPORT_SCHEMA = "ztare-forensic-workbench-claim-support-v1"
CLAIM_CARD_RECEIPT_SCHEMA = claim_card_core.CLAIM_CARD_RECEIPT_SCHEMA
EVIDENCE_GAP_LIST_SCHEMA = "ztare-forensic-workbench-evidence-gap-list-v1"
EVIDENCE_GAP_JUSTIFY_SCHEMA = "ztare-forensic-workbench-evidence-gap-justify-v1"
EVIDENCE_FETCH_SCHEMA = "ztare-forensic-workbench-evidence-fetch-v1"
EVIDENCE_FETCH_RECEIPT_SCHEMA = "ztare-forensic-workbench-evidence-fetch-receipt-v1"
WORKBENCH_SETTINGS_SCHEMA = settings_core.WORKBENCH_SETTINGS_SCHEMA
SCORING_GUIDE_SCHEMA = "ztare-forensic-workbench-scoring-guide-v1"
SCORING_GUIDE_RECEIPT_SCHEMA = scoring_guide_core.SCORING_GUIDE_RECEIPT_SCHEMA
RESEARCH_MAP_SCHEMA = research_map_core.RESEARCH_MAP_SCHEMA
RESEARCH_MAP_RECEIPT_SCHEMA = research_map_core.RESEARCH_MAP_RECEIPT_SCHEMA
SOURCE_ACTION_SCHEMA = source_actions_core.SOURCE_ACTION_SCHEMA
PROJECT_CREATE_SCHEMA = "ztare-forensic-workbench-project-create-v1"
PROJECT_RECOVERY_DRAFT_SCHEMA = "ztare-forensic-workbench-project-recovery-draft-v1"
SOURCE_IMPORT_SCHEMA = source_files_core.SOURCE_IMPORT_SCHEMA
SOURCE_LIST_SCHEMA = "ztare-forensic-workbench-source-list-v1"
SOURCE_FILE_SCHEMA = "ztare-forensic-workbench-source-file-v1"
SOURCE_EDIT_SCHEMA = source_files_core.SOURCE_EDIT_SCHEMA
SOURCE_ACTION_RECEIPT_SCHEMA = source_actions_core.SOURCE_ACTION_RECEIPT_SCHEMA
CASE_FILE_SCHEMA = project_file_core.CASE_FILE_SCHEMA
CASE_FILE_WRITE_SCHEMA = "ztare-forensic-workbench-case-file-write-receipt-v1"
PROJECT_FILE_SCHEMA = project_file_core.PROJECT_FILE_SCHEMA
PROJECT_FILE_WRITE_SCHEMA = project_file_core.PROJECT_FILE_WRITE_SCHEMA
SERVER_STATUS_SCHEMA = "ztare-forensic-workbench-server-status-v1"
PRINCIPLE_RAIL_SCHEMA = "ztare-forensic-workbench-principle-rail-v1"
WORKFLOW_SCHEMA = "ztare-forensic-workbench-workflow-v1"
WORKBENCH_STORAGE_SCHEMA = "ztare-forensic-workbench-storage-v1"
WORKBENCH_ENV_PATH = settings_core.WORKBENCH_ENV_PATH
ACTION_INTELLIGENCE_STATE_DIR = Path("analytics/public/action_intelligence/state")
SERVER_PYTHON = str(snapshot.REPO / "venv" / "bin" / "python") if (snapshot.REPO / "venv" / "bin" / "python").exists() else snapshot.PYTHON
WORKBENCH_UI_SECTIONS = {
    "projects": {"Current project", "Projects", "Connect project", "Files", "Settings", "Plugins"},
    "overview": {"Overview", "Charter", "Thesis", "Assumptions", "Evidence summary", "Research map"},
    "sources": {"Prepare files", "Project brief", "Add file", "Edit file"},
    "run": {"Ready to run", "Scoring guide", "Run settings", "Check readiness", "Start run", "Fix warnings"},
    "leanmill": {"Start", "Draft target", "Proof files", "Proof status"},
    "review": {"Things to review", "Save review", "Save next step", "Saved history"},
    "save": {"Report readiness", "Report inputs", "Project file"},
}
WORKBENCH_UI_WORKSPACE_ALIASES = {
    "case": "projects",
    "cases": "projects",
}
WORKBENCH_UI_SUBSECTION_ALIASES = {
    "projects": {
        "All projects": "Projects",
        "Project library": "Projects",
        "Add intake": "Connect project",
        "Intake": "Connect project",
    },
    "overview": {
        "Status": "Overview",
        "Diagnosis": "Thesis",
        "Evidence": "Evidence summary",
        "Evidence map": "Evidence summary",
    },
    "sources": {
        "Readiness": "Prepare files",
        "Prepare sources": "Prepare files",
        "Check files": "Prepare files",
        "File check": "Prepare files",
        "Add source": "Add file",
        "Add source file": "Add file",
        "Edit source": "Edit file",
        "Edit source file": "Edit file",
    },
    "run": {
        "Plan": "Ready to run",
        "Can it run?": "Ready to run",
        "Preflight": "Check readiness",
        "Advisories": "Fix warnings",
        "Suggested fixes": "Fix warnings",
    },
    "review": {
        "Review points": "Things to review",
        "Project checks": "Things to review",
        "Open issues": "Things to review",
        "Review": "Save review",
        "Next step": "Save next step",
        "Receipts": "Saved history",
    },
    "save": {
        "Report support": "Report readiness",
        "Support check": "Report readiness",
        "Report/export": "Report readiness",
        "Report": "Report inputs",
    },
    "leanmill": {
        "Overview": "Start",
        "Blueprint": "Draft target",
        "Formalizations": "Proof files",
        "History": "Proof status",
        "Saved history": "Proof status",
        "Receipts": "Proof status",
    },
}
INTAKE_EDIT_FIELDS = project_brief_core.INTAKE_EDIT_FIELDS
INTAKE_LIST_FIELDS = project_brief_core.INTAKE_LIST_FIELDS
EXTERNAL_REF_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*://")
SOURCE_IMPORT_FILENAME_RE = source_files_core.SOURCE_IMPORT_FILENAME_RE
SOURCE_IMPORT_TYPES = source_files_core.SOURCE_IMPORT_TYPES
DOCUMENT_IMPORT_FILENAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,120}\.(?:md|txt|csv|tsv|json|log|pdf|docx|pptx|xlsx)$", re.I)
MAX_JSON_BODY_BYTES = 16 * 1024 * 1024
SOURCE_ARTIFACT_KINDS = source_files_core.SOURCE_ARTIFACT_KINDS
LOCAL_DEV_ORIGIN_RE = re.compile(r"^http://(127\.0\.0\.1|localhost):51(7[3-9]|8[0-9])$")
model_option = settings_core.model_option
WORKBENCH_MODEL_OPTIONS = settings_core.WORKBENCH_MODEL_OPTIONS
WORKBENCH_SETTINGS_FIELDS = settings_core.WORKBENCH_SETTINGS_FIELDS
WORKBENCH_SECRET_KEYS = settings_core.WORKBENCH_SECRET_KEYS
WRITE_POST_ENDPOINTS = {
    "/api/review",
    "/api/charter",
    "/api/intake",
    "/api/item-action",
    "/api/next-step",
    "/api/row-action",
    "/api/preflight",
    "/api/run",
    "/api/job-cancel",
    "/api/settings",
    "/api/run-config",
    "/api/scoring-guide",
    "/api/rubric-review",
    "/api/falsify-claim",
    "/api/project-draft",
    "/api/source-action",
    "/api/report-synthesis",
    "/api/claim-card",
    "/api/evidence-fetch",
    "/api/report-contract",
    "/api/evidence-gap-justify",
    "/api/project-create",
    "/api/source-import",
    "/api/source-edit",
    "/api/project-file",
    "/api/case-file",
    "/api/research-map",
    "/api/leanmill/target",
    "/api/leanmill/blueprint",
    "/api/leanmill/blueprint-save",
    "/api/leanmill/blueprint-draft",
    "/api/leanmill/scaffold",
    "/api/leanmill/autoformalize-notes",
    "/api/leanmill/solve-adhoc",
    "/api/leanmill/ratify",
    "/api/leanmill/campaign-run",
    "/api/leanmill/campaign-verify",
    "/api/leanmill/campaign-replay",
    "/api/leanmill/campaign-stop",
    "/api/leanmill/campaign-retire",
    "/api/leanmill/campaign-resume",
    "/api/leanmill/campaign-recover",
    "/api/leanmill/campaign-recheck",
    "/api/leanmill/campaign-interpret",
    "/api/scenario-reingest-promote",
    "/api/scenario-deliverable-editorial",
}
SOURCE_ACTIONS = source_actions_core.SOURCE_ACTIONS


# The project store is the shared common.storage.FileStorage (one provider interface, S3/DB-swappable). The
# workbench keeps its historical metadata schema string for back-compat with the snapshot contract + settings.
# Lazy root (a callable) so it tracks snapshot.REPO — several tests monkeypatch that to a tmp dir; matches the
# prior FileWorkbenchStorage.root property behavior.
WORKBENCH_STORE = FileStorage(lambda: snapshot.REPO, schema=WORKBENCH_STORAGE_SCHEMA)


def json_bytes(payload: dict[str, Any], status: int = 200) -> tuple[int, bytes]:
    return status, (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def first_param(params: dict[str, list[str]], key: str, default: str) -> str:
    values = params.get(key)
    if not values:
        return default
    return values[0] or default


def repo_rel(path: Path) -> str:
    return WORKBENCH_STORE.rel(path)


def display_path(value: Any) -> str:
    raw = str(value or "")
    if not raw:
        return ""
    path = Path(raw)
    if path.is_absolute():
        try:
            return path.relative_to(snapshot.REPO).as_posix()
        except ValueError:
            try:
                return repo_rel(path)
            except ValueError:
                return raw
    return raw


def display_text(value: Any) -> str:
    text = str(value or "")
    if not text:
        return ""
    repo = str(snapshot.REPO.resolve())
    text = text.replace(repo + "/", "").replace(repo, ".")
    replacements: list[tuple[str, str, int]] = [
        (
            r"Run the model-free launch preflight to verify local setup\.?",
            "Run the local readiness check to verify setup.",
            re.IGNORECASE,
        ),
        (
            r"Run the model-free launch preflight\.?:",
            "Run the local readiness check:",
            re.IGNORECASE,
        ),
        (
            r"Run the model-free launch preflight\b",
            "Run the local readiness check",
            re.IGNORECASE,
        ),
        (
            r"Run the local preflight before starting a project run\.",
            "Run the local readiness check before starting a project run.",
            re.IGNORECASE,
        ),
        (
            r"\bpreflight receipts\b",
            "readiness checks",
            re.IGNORECASE,
        ),
        (
            r"\bPreflight receipt\b",
            "Readiness check",
            0,
        ),
        (
            r"\bRun preflight\b",
            "Check readiness",
            re.IGNORECASE,
        ),
        (
            r"\bPreflight\b",
            "Check readiness",
            0,
        ),
        (
            r"\bpreflight\b",
            "readiness check",
            0,
        ),
        (
            r"\bgating test\b",
            "decisive test",
            re.IGNORECASE,
        ),
        (
            r"\bReport support\b",
            "Report readiness",
            0,
        ),
        (
            r"\breport support\b",
            "report readiness",
            0,
        ),
        (
            r"\bnext review surface\b",
            "next review step",
            re.IGNORECASE,
        ),
        (
            r"\breceipt checks\b",
            "saved-history checks",
            re.IGNORECASE,
        ),
        (
            r"\breview receipt\b",
            "review saved work",
            re.IGNORECASE,
        ),
        (
            r"\bsaved-record paths\b",
            "history paths",
            re.IGNORECASE,
        ),
        (
            r"\bsaved-record path\b",
            "history path",
            re.IGNORECASE,
        ),
        (
            r"\bsaved records\b",
            "saved changes",
            re.IGNORECASE,
        ),
        (
            r"\bsaved record\b",
            "saved work",
            re.IGNORECASE,
        ),
        (
            r"\breceipt trail\b",
            "saved history",
            re.IGNORECASE,
        ),
        (
            r"\breceipt paths\b",
            "saved-history paths",
            re.IGNORECASE,
        ),
        (
            r"\breceipt path\b",
            "saved-history path",
            re.IGNORECASE,
        ),
        (
            r"\breceipts\b",
            "saved changes",
            re.IGNORECASE,
        ),
        (
            r"\breceipt\b",
            "saved work",
            re.IGNORECASE,
        ),
        (
            r"\bsource refs\b",
            "original files",
            re.IGNORECASE,
        ),
        (
            r"\bevidence refs\b",
            "evidence summaries",
            re.IGNORECASE,
        ),
        (
            r"\bwork artifact\b",
            "work file",
            re.IGNORECASE,
        ),
        (
            r"\bartifact links\b",
            "file links",
            re.IGNORECASE,
        ),
    ]
    for pattern, replacement, flags in replacements:
        text = re.sub(pattern, replacement, text, flags=flags)
    return text


def env_file_path() -> Path:
    return settings_core.env_file_path(root=snapshot.REPO)


def parse_env_line(line: str) -> tuple[str, str] | None:
    return settings_core.parse_env_line(line)


def read_env_file_values() -> dict[str, str]:
    return settings_core.read_env_file_values(root=snapshot.REPO, storage=WORKBENCH_STORE)


def setting_default(key: str) -> str:
    return settings_core.setting_default(key)


def normalize_setting_value(key: str, value: Any) -> str:
    return settings_core.normalize_setting_value(key, value)


def normalize_provider_key_value(key: str, value: Any) -> str:
    return settings_core.normalize_provider_key_value(key, value)


def workbench_settings_values() -> dict[str, str]:
    return settings_core.workbench_settings_values(root=snapshot.REPO, storage=WORKBENCH_STORE)


def project_run_config_root(project: str) -> Path:
    return snapshot.REPO / "projects" / snapshot.validate_project_slug(project)


def project_run_overrides(project: str) -> dict[str, str]:
    try:
        root = project_run_config_root(project)
    except Exception:
        return {}
    return settings_core.read_project_run_overrides(root, storage=WORKBENCH_STORE)


def workbench_command_context(project: str, rubric: str | None = None) -> dict[str, str]:
    values = workbench_settings_values()
    # Layer per-project run overrides on top of the global settings. Saved by the run-config panel,
    # not the .env, so a researcher can tune one project's run without touching global defaults.
    project_overrides = project_run_overrides(project)
    if project_overrides:
        values = {**values, **project_overrides}
    auto_compile = values["ZTARE_WORKBENCH_AUTO_COMPILE"]
    return {
        "project": project,
        "rubric": rubric or project,
        "model": values["ZTARE_WORKBENCH_MODEL"],
        "report_model": values["ZTARE_WORKBENCH_REPORT_MODEL"] or values["ZTARE_WORKBENCH_MODEL"],
        "model_fallback": values["ZTARE_WORKBENCH_MODEL_FALLBACK"],
        "evidence_llm_timeout": values["ZTARE_WORKBENCH_EVIDENCE_LLM_TIMEOUT"],
        "evidence_llm_retries": values["ZTARE_WORKBENCH_EVIDENCE_LLM_RETRIES"],
        "evidence_search_backend": values["ZTARE_EVIDENCE_SEARCH_BACKEND"],
        "fetch_severity": values["ZTARE_WORKBENCH_FETCH_SEVERITY"],
        "max_fetches": values["ZTARE_WORKBENCH_MAX_FETCHES"],
        "auto_compile": auto_compile,
        "auto_compile_flag": "" if auto_compile == "1" else " AUTO_COMPILE=0",
        "run_mutator_model": values["ZTARE_WORKBENCH_RUN_MUTATOR_MODEL"],
        "run_judge_model": values["ZTARE_WORKBENCH_RUN_JUDGE_MODEL"],
        "run_inverter_model": values["ZTARE_WORKBENCH_RUN_INVERTER_MODEL"],
        "run_committee_model": values["ZTARE_WORKBENCH_RUN_COMMITTEE_MODEL"],
        "run_transport": values["ZTARE_WORKBENCH_RUN_TRANSPORT"],
        "run_judging": values["ZTARE_WORKBENCH_RUN_JUDGING"],
        "run_rubric_mode": values["ZTARE_WORKBENCH_RUN_RUBRIC_MODE"],
        "run_cross_family": values["ZTARE_WORKBENCH_RUN_CROSS_FAMILY"],
        "run_iters": values["ZTARE_WORKBENCH_RUN_ITERS"],
        "autoresearch_llm_timeout": values["ZTARE_WORKBENCH_AUTORESEARCH_LLM_TIMEOUT"],
        "autoresearch_llm_retries": values["ZTARE_WORKBENCH_AUTORESEARCH_LLM_RETRIES"],
    }


def workbench_status_command_context(project: str = "{project}", rubric: str | None = "{rubric}") -> dict[str, str]:
    context = workbench_command_context(project, rubric)
    if context["model"]:
        context["model"] = "<settings_evidence_model>"
    if context["report_model"]:
        context["report_model"] = "<settings_report_model>"
    if context["run_mutator_model"]:
        context["run_mutator_model"] = "<settings_run_proposer_model>"
    if context["run_judge_model"]:
        context["run_judge_model"] = "<settings_run_judge_model>"
    if context["run_inverter_model"]:
        context["run_inverter_model"] = "<settings_run_inverter_model>"
    return context


def empty_make_assignment(part: str) -> bool:
    return re.fullmatch(r"[A-Z0-9_]+=", part) is not None


def command_from_template(parts: list[str], context: dict[str, str]) -> list[str]:
    command: list[str] = []
    for part in parts:
        formatted = part.format(**context)
        if formatted and not empty_make_assignment(formatted):
            command.append(formatted)
    return command


def display_command(parts: list[str]) -> str:
    return " ".join(shlex.quote(display_path(part) or str(part)) for part in parts)


def display_command_from_template(parts: list[str], context: dict[str, str]) -> str:
    return display_command(command_from_template(parts, context))


def set_cli_option(parts: list[str], flag: str, value: str) -> list[str]:
    output: list[str] = []
    index = 0
    while index < len(parts):
        if parts[index] == flag:
            index += 2
            continue
        output.append(parts[index])
        index += 1
    if value:
        output.extend([flag, value])
    return output


def set_cli_boolean(parts: list[str], flag: str, enabled: bool) -> list[str]:
    output = [part for part in parts if part != flag]
    if enabled:
        output.append(flag)
    return output


def cli_has_option(parts: list[str], flag: str) -> bool:
    return flag in parts


def cli_option_value(parts: list[str], flag: str) -> str:
    try:
        index = parts.index(flag)
    except ValueError:
        return ""
    next_index = index + 1
    if next_index >= len(parts):
        return ""
    return str(parts[next_index])


def setting_was_explicit(key: str) -> bool:
    return settings_core.setting_was_explicit(key, root=snapshot.REPO, storage=WORKBENCH_STORE)


def apply_setting_option(parts: list[str], flag: str, setting_key: str, value: str) -> list[str]:
    if cli_has_option(parts, flag) and not setting_was_explicit(setting_key):
        return parts
    return set_cli_option(parts, flag, value)


def apply_model_setting_option(parts: list[str], flag: str, value: str) -> list[str]:
    """Workbench model roles are owned by Settings; blank means runtime default."""

    return set_cli_option(parts, flag, value)


def apply_run_settings_to_autoresearch_command(display_command: Any, project: str = "{project}") -> str:
    parts = shlex.split(str(display_command or ""))
    if len(parts) < 3 or parts[:3] != ["ztare", "autoresearch", "run"]:
        return str(display_command or "")
    # Pass the real project so per-project run overrides resolve; the "{project}" placeholder (used by
    # templated/status commands) just falls back to global settings.
    context = workbench_command_context(project, "{rubric}")
    parts = apply_model_setting_option(parts, "--mutator", context["run_mutator_model"])
    parts = apply_model_setting_option(parts, "--judge", context["run_judge_model"])
    parts = apply_model_setting_option(parts, "--inverter", context["run_inverter_model"])
    parts = apply_model_setting_option(parts, "--committee-model", context["run_committee_model"])
    parts = apply_setting_option(parts, "--llm-timeout-seconds", "ZTARE_WORKBENCH_AUTORESEARCH_LLM_TIMEOUT", context["autoresearch_llm_timeout"])
    parts = apply_setting_option(parts, "--llm-retries", "ZTARE_WORKBENCH_AUTORESEARCH_LLM_RETRIES", context["autoresearch_llm_retries"])
    if setting_was_explicit("ZTARE_WORKBENCH_MODEL_FALLBACK") or "--allow-model-fallback" not in parts:
        parts = set_cli_boolean(parts, "--allow-model-fallback", context["model_fallback"] == "1")
    # Run engine: 'subscription' routes the run's model calls through the local Codex/Claude CLI worker
    # via the --agent-* flags. 'api' (default) leaves them off and calls the provider API directly.
    subscription = context.get("run_transport") == "subscription"
    for flag in ("--agent-mutator", "--agent-judge", "--agent-inverter", "--agent-committee"):
        parts = set_cli_boolean(parts, flag, subscription)
    # Iterations: override the project default only when the workbench setting is non-blank.
    run_iters = str(context.get("run_iters") or "").strip()
    if run_iters:
        parts = apply_setting_option(parts, "--iters", "ZTARE_WORKBENCH_RUN_ITERS", run_iters)
    # Judging committee (3-panel), rotating/auto-evolving rubric, and mixed-model committee. All default off.
    parts = set_cli_boolean(parts, "--dynamic", context.get("run_judging") == "committee")
    parts = set_cli_boolean(parts, "--auto-evolve", context.get("run_rubric_mode") == "rotating")
    parts = set_cli_boolean(parts, "--cross-family", context.get("run_cross_family") == "1" and context.get("run_judging") == "committee")
    return " ".join(shlex.quote(part) for part in parts)


def load_workbench_env() -> dict[str, str]:
    return settings_core.load_workbench_env(root=snapshot.REPO, storage=WORKBENCH_STORE)


def run_workbench_command(
    command: list[str],
    *,
    timeout: int = 90,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            cwd=cwd or snapshot.REPO,
            env=load_workbench_env(),
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
            args=command,
            returncode=124,
            stdout=stdout,
            stderr=(stderr + f"\ncommand timed out after {timeout}s").strip(),
        )


def settings_payload() -> dict[str, Any]:
    return settings_core.settings_payload(root=snapshot.REPO, storage=WORKBENCH_STORE)


def quote_env_value(value: str) -> str:
    return settings_core.quote_env_value(value)


def save_settings_payload(raw_values: Any) -> dict[str, Any]:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json") as staged:
        json.dump(raw_values, staged)
        staged.flush()
        payload = ztare_cli_payload([
            "forensic-workbench", "settings", "save",
            "--from", staged.name,
            "--repo", str(snapshot.REPO),
            "--json",
        ], timeout=90)
    if payload.get("ok") is False:
        raise ValueError(str(payload.get("error") or "settings save was refused"))
    return payload


RUN_CONFIG_SCHEMA = "ztare-forensic-workbench-run-config-v1"


def run_config_write_boundary(config_path: Path, *, saved: bool = False) -> dict[str, Any]:
    rel = WORKBENCH_STORE.rel(config_path)
    return {
        "schema": "ztare-forensic-workbench-write-boundary-v1",
        "writes_project_files": True,
        "writes_repo_files": False,
        "browser_writes": False,
        "write_paths": [rel],
        "receipt_path": "",
        "latest_path": "",
        "no_change_boundary": (
            "Inspecting run config writes no files. Saving writes only this project's run-config file; "
            "global Settings and the .env are never touched."
        ),
        "read_only_actions": ["inspect run config"],
    }


def run_config_payload(project: str) -> dict[str, Any]:
    project = snapshot.validate_project_slug(project)
    global_values = workbench_settings_values()
    overrides = project_run_overrides(project)
    fields = []
    for field in WORKBENCH_SETTINGS_FIELDS:
        key = str(field["key"])
        if key not in settings_core.PROJECT_RUN_CONFIG_KEYS:
            continue
        overridden = key in overrides
        fields.append(
            {
                **field,
                "global_value": global_values[key],
                "value": overrides[key] if overridden else global_values[key],
                "overridden": overridden,
                "source": "project_override" if overridden else "global_default",
            }
        )
    config_path = project_run_config_root(project) / settings_core.PROJECT_RUN_CONFIG_FILENAME
    return {
        "schema": RUN_CONFIG_SCHEMA,
        "ok": True,
        "project": project,
        "fields": fields,
        "global_values": {key: global_values[key] for key in settings_core.PROJECT_RUN_CONFIG_KEYS},
        "overrides": overrides,
        "override_count": len(overrides),
        "config_path": WORKBENCH_STORE.rel(config_path),
        "config_exists": config_path.exists(),
        "write_boundary": run_config_write_boundary(config_path),
    }


def save_run_config_payload(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("run config request must include a project and values")
    project = snapshot.validate_project_slug(str(raw.get("project") or ""))
    root = project_run_config_root(project)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json") as staged:
        json.dump(raw.get("values"), staged)
        staged.flush()
        saved = ztare_cli_payload([
            "forensic-workbench", "settings", "project-save",
            "--project", project,
            "--from", staged.name,
            "--repo", str(snapshot.REPO),
            "--json",
        ], project=project, timeout=90)
    if saved.get("ok") is False:
        raise ValueError(str(saved.get("error") or "run settings save was refused"))
    overrides = saved.get("overrides") if isinstance(saved.get("overrides"), dict) else {}
    payload = run_config_payload(project)
    config_path = root / settings_core.PROJECT_RUN_CONFIG_FILENAME
    payload.update(
        {
            "saved": True,
            "updated_keys": sorted(overrides),
            "write_boundary": run_config_write_boundary(config_path, saved=True),
        }
    )
    return payload


def project_display_label(project: Any) -> str:
    text = str(project or "").strip()
    if not text:
        return "Local project"
    text = re.sub(r"^_+", "", text)
    text = re.sub(r"[_-]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return str(project)
    phrase_replacements = {
        "load bearing": "key",
    }
    for raw, rendered in phrase_replacements.items():
        text = re.sub(rf"\b{raw}\b", rendered, text, flags=re.IGNORECASE)
    replacements = {
        "operator": "system",
        "packet": "project brief",
        "case": "project",
    }
    for raw, rendered in replacements.items():
        text = re.sub(rf"\b{raw}\b", rendered, text, flags=re.IGNORECASE)
    acronyms = {
        "ai": "AI", "api": "API", "arc": "ARC", "aws": "AWS", "eu": "EU", "gpu": "GPU",
        "hbr": "HBR", "llm": "LLM", "ns": "NS", "pde": "PDE", "roi": "ROI",
        "capex": "CapEx",
    }
    words = [acronyms.get(word.lower(), word) for word in text.split()]
    if words and words[0].lower() not in acronyms:
        words[0] = words[0][:1].upper() + words[0][1:]
    return " ".join(words)


def project_charter_rel(project: str) -> str:
    return project_charter_core.charter_rel(project)


def project_charter_path(project: str) -> Path:
    return project_charter_core.charter_path(project, root=snapshot.REPO)


def ensure_project_charter(
    *,
    project: str,
    task: str,
    bounded_claim: str,
    next_falsifier: str,
    notes: str = "",
    source_refs: list[str] | None = None,
    evidence_refs: list[str] | None = None,
    non_claims: list[str] | None = None,
) -> str | None:
    return project_charter_core.ensure_charter(
        project=project,
        title=project_display_label(project),
        task=task,
        bounded_claim=bounded_claim,
        next_falsifier=next_falsifier,
        notes=notes,
        source_refs=source_refs,
        evidence_refs=evidence_refs,
        non_claims=non_claims,
        root=snapshot.REPO,
        storage=WORKBENCH_STORE,
    )


def project_status_label(status: Any, *, intake_source: Any = "") -> str:
    raw = str(status or "")
    if raw in {"case_ready", "intake_ready"}:
        return "project brief ready"
    if raw == "needs_intake":
        return "needs project brief"
    if str(intake_source or "") == "public_example_intake":
        return "example project brief"
    if str(intake_source or "") == "project_local_intake":
        return "project brief"
    return display_value(raw or "project")


def project_status_value(status: Any) -> str:
    raw = str(status or "")
    if raw in {"case_ready", "intake_ready"}:
        return "intake_ready"
    return raw or "project"


def project_folder_next_action(folder: dict[str, Any]) -> dict[str, Any]:
    project = str(folder.get("project") or "")
    has_files = bool(
        folder.get("has_project_files")
        or folder.get("has_project_material")
        or folder.get("has_case_material")
        or folder.get("raw_exists")
        or folder.get("workspace_exists")
        or folder.get("source_type_map_exists")
        or folder.get("root_source_file_count")
        or folder.get("source_preview_files")
    )
    if folder.get("openable"):
        if folder.get("intake_error"):
            return {
                "id": "fix_project_brief",
                "label": "Fix project brief",
                "detail": "The project brief loaded with attention. Open the project, inspect the brief, and repair the listed issue.",
                "workspace": "projects",
                "subsection": "Connect project",
            }
        return {
            "id": "open_project",
            "label": "Open project",
            "detail": "Open the project state: thesis, files, evidence, runs, report readiness, and saved history.",
            "workspace": "projects",
            "subsection": "Current project",
        }
    if has_files:
        return {
            "id": "create_project_brief",
            "label": "Create project brief",
            "detail": "This folder already has useful files. Create a project brief before editing the thesis, evidence summary, runs, or report readiness.",
            "workspace": "projects",
            "subsection": "Connect project",
        }
    return {
        "id": "inspect_folder",
        "label": "Inspect folder",
        "detail": "This folder does not look ready for project work yet. Inspect it before creating a project brief.",
        "workspace": "projects",
        "subsection": "Projects",
    }


def background_project_folder(project: Any) -> bool:
    text = str(project or "")
    return (
        text.startswith("_")
        or text.startswith("backtest_")
        or text.startswith("recursive_bayesian_")
        or text.startswith("simulation_god_")
        or text.startswith("tsmc_fragility_")
    )


def display_data(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): display_data(item) for key, item in value.items()}
    if isinstance(value, list):
        return [display_data(item) for item in value]
    if isinstance(value, str):
        return display_text(value)
    return value


def safe_child_path(root: Path, request_path: str) -> Path:
    normalized = request_path.strip("/")
    pure = PurePosixPath(normalized)
    if any(part in {"", ".", ".."} for part in pure.parts):
        raise ValueError("static path is not allowed")
    resolved = (root / Path(*pure.parts)).resolve()
    if not path_under(resolved, root):
        raise ValueError("static path escapes workbench root")
    return resolved


def static_workbench_path(request_path: str) -> Path | None:
    if request_path in {"", "/", "/index.html"}:
        return WORKBENCH_DIST / "index.html"
    if request_path == "/workbench_snapshot.json":
        return WORKBENCH_PUBLIC / "workbench_snapshot.json"
    if request_path.startswith("/assets/"):
        return safe_child_path(WORKBENCH_DIST, request_path)
    return None


def live_row_payload_with_case(
    payload: dict[str, Any],
    *,
    project: str,
    rubric: str | None,
    intake: str | None,
) -> dict[str, Any]:
    scoped_payload = dict(payload)
    if str(scoped_payload.get("project") or "") != project:
        raise ValueError("project-check file project must match request project")

    existing_rubric = str(scoped_payload.get("rubric") or "").strip()
    if rubric and existing_rubric and existing_rubric != rubric:
        raise ValueError("project-check file rubric must match request rubric")
    if rubric and not existing_rubric:
        scoped_payload["rubric"] = rubric

    if intake:
        expected_case_key = case_key(project, intake)
        existing_intake = str(scoped_payload.get("intake") or "").strip()
        if existing_intake and existing_intake != intake:
            raise ValueError("project-check file intake must match request intake")
        existing_project_key = str(scoped_payload.get("project_key") or "").strip()
        if existing_project_key and existing_project_key != expected_case_key:
            raise ValueError("project-check file project key must match the requested project brief")
        existing_case_key = str(scoped_payload.get("case_key") or "").strip()
        if existing_case_key and existing_case_key != expected_case_key:
            raise ValueError("project-check file compatibility key must match the requested project brief")
        scoped_payload["intake"] = intake
        scoped_payload["project_key"] = expected_case_key
        scoped_payload["project_file_key"] = expected_case_key
        scoped_payload["case_key"] = expected_case_key
    return scoped_payload


def live_project_check_payload(payload: dict[str, Any], *, slug: str) -> dict[str, Any]:
    scoped_payload = dict(payload)
    check_slug = str(slug or "").strip()
    check_label = receipt_check_label(
        str(scoped_payload.get("project_check_label") or scoped_payload.get("item_label") or ""),
        check_slug,
        str(scoped_payload.get("row") or ""),
    )
    if check_slug:
        for key in ("project_check_slug", "item_slug", "row_slug"):
            if not str(scoped_payload.get(key) or "").strip():
                scoped_payload[key] = check_slug
    if check_label:
        for key in ("project_check_label", "item_label"):
            if not str(scoped_payload.get(key) or "").strip():
                scoped_payload[key] = check_label
    return scoped_payload


def case_file_payload_with_case(
    payload: dict[str, Any],
    *,
    project: str,
    rubric: str | None = None,
    intake: str | None = None,
) -> dict[str, Any]:
    scoped_payload = dict(payload)
    if str(scoped_payload.get("project") or "") != project:
        raise ValueError("project_file project must match request project")

    rubric_value = str(rubric or scoped_payload.get("rubric") or "").strip()
    existing_rubric = str(scoped_payload.get("rubric") or "").strip()
    if rubric and existing_rubric and existing_rubric != rubric:
        raise ValueError("project_file rubric must match request rubric")
    if rubric_value:
        scoped_payload["rubric"] = rubric_value

    intake_value = str(intake or scoped_payload.get("intake") or "").strip()
    existing_intake = str(scoped_payload.get("intake") or "").strip()
    if intake and existing_intake and existing_intake != intake:
        raise ValueError("project_file intake must match request intake")
    if intake_value:
        expected_case_key = case_key(project, intake_value)
        existing_project_key = str(scoped_payload.get("project_key") or "").strip()
        if existing_project_key and existing_project_key != expected_case_key:
            raise ValueError("project_file project key must match the requested project brief")
        existing_case_key = str(scoped_payload.get("case_key") or "").strip()
        if existing_case_key and existing_case_key != expected_case_key:
            raise ValueError("project_file compatibility key must match the requested project brief")
        scoped_payload["intake"] = intake_value
        scoped_payload["project_key"] = expected_case_key
        scoped_payload["project_file_key"] = expected_case_key
        scoped_payload["case_key"] = expected_case_key
    return scoped_payload


def stamp_case_file_live_state(
    case_file: dict[str, Any],
    *,
    project: str,
    rubric: str | None,
    intake: str | None,
) -> dict[str, Any]:
    """Bind saved project files to the server's current project object."""

    stamped = dict(case_file)
    live_context = stamped.get("live_context")
    if not isinstance(live_context, dict):
        live_context = {}
    else:
        live_context = dict(live_context)
    try:
        workflow = workflow_payload_for_project(
            project=project,
            rubric=rubric or stamped.get("rubric") or project,
            intake=intake or stamped.get("intake") or snapshot.default_intake_for_project(project),
            mode="fast",
        )
    except Exception as exc:  # noqa: BLE001 - saving should still return an inspectable artifact.
        live_context["project_state_error"] = display_text(exc)
        stamped["live_context"] = live_context
        return stamped

    project_state = workflow.get("project_state") if isinstance(workflow.get("project_state"), dict) else {}
    if project_state:
        live_context["project_state"] = project_state
    project_object_contract = (
        workflow.get("project_object_contract")
        if isinstance(workflow.get("project_object_contract"), dict)
        else {}
    )
    if project_object_contract:
        live_context["project_object_contract"] = project_object_contract
    try:
        live_context["report_contract"] = report_contract_payload_for_project(
            project=project,
            rubric=rubric or stamped.get("rubric") or project,
            intake=intake or stamped.get("intake") or snapshot.default_intake_for_project(project),
            renderer="decision_brief",
        )
    except Exception as exc:  # noqa: BLE001 - project files should still save without report support.
        live_context["report_contract_error"] = display_text(exc)
    live_context["workflow"] = {
        "schema": workflow.get("schema") or "",
        "mode": workflow.get("mode") or "",
        "summary": workflow.get("summary") if isinstance(workflow.get("summary"), dict) else {},
        "next_step": workflow.get("next_step") if isinstance(workflow.get("next_step"), dict) else {},
        "steps": workflow.get("steps") if isinstance(workflow.get("steps"), list) else [],
        "errors": workflow.get("errors") if isinstance(workflow.get("errors"), list) else [],
    }
    stamped["live_context"] = live_context
    stamped["project_summary"] = saved_project_summary_payload(
        project=project,
        intake=str(stamped.get("intake") or intake or ""),
        project_state=project_state,
        project_object_contract=project_object_contract,
        case_file=stamped,
    )
    return stamped


def latest_receipt_summary(receipts: list[Any], kind: str) -> dict[str, Any]:
    accepted = {"row_action", "next_step"} if kind == "next_step" else {kind}
    for receipt in receipts:
        if not isinstance(receipt, dict) or str(receipt.get("kind") or "") not in accepted:
            continue
        label = str(
            receipt.get("project_check_label")
            or receipt.get("check_label")
            or receipt.get("display_label")
            or receipt.get("item_label")
            or receipt.get("row")
            or ""
        )
        return {
            "kind": str(receipt.get("kind") or ""),
            "label": display_guidance_text(label),
            "summary": display_guidance_text(receipt.get("display_summary") or receipt.get("summary") or ""),
            "decision": str(receipt.get("display_decision") or receipt.get("decision") or ""),
            "action": display_guidance_text(receipt.get("display_action") or receipt.get("action") or ""),
            "applied_at": str(receipt.get("applied_at") or ""),
            "path": str(receipt.get("path") or ""),
        }
    return {}


def compact_project_axioms(project: str) -> dict[str, Any]:
    """Run-learned axioms and constraints for the selected project."""

    project_root = snapshot.REPO / "projects" / project
    latest_eval_path = project_root / "latest_eval_results.json"
    verified_axioms_path = project_root / "verified_axioms.json"
    constraints_path = project_root / "workspace" / "derived_constraints.json"
    latest_eval = read_optional_json_object(latest_eval_path)
    verified_file_payload = read_optional_json_value(verified_axioms_path)
    constraints_payload = read_optional_json_object(constraints_path)

    def text_items(value: Any, *, limit: int = 8) -> list[str]:
        if isinstance(value, list):
            return [display_text(item) for item in value if display_text(item)][:limit]
        if isinstance(value, str) and value.strip():
            return [value.strip()][:limit]
        return []

    def constraint_items(value: Any, *, limit: int = 8) -> list[dict[str, str]]:
        rows = value if isinstance(value, list) else []
        items: list[dict[str, str]] = []
        for row in rows:
            if isinstance(row, dict):
                text = display_text(row.get("constraint") or row.get("text") or row.get("summary") or row)
                applies_to = display_text(row.get("applies_to") or row.get("target") or "")
                severity = display_text(row.get("severity") or "")
            else:
                text = display_text(row)
                applies_to = ""
                severity = ""
            if text:
                items.append({"text": text, "applies_to": applies_to, "severity": severity})
            if len(items) >= limit:
                break
        return items

    verified = text_items(latest_eval.get("verified_axioms"))
    if not verified:
        verified = text_items(verified_file_payload)
    retired = text_items(latest_eval.get("retired_axioms_approved"))
    derived = constraint_items(latest_eval.get("derived_constraints"))
    if constraints_payload:
        derived = constraint_items(
            constraints_payload.get("confirmed_constraints")
            or constraints_payload.get("derived_constraints")
            or constraints_payload.get("provisional_constraints")
        ) or derived
    verified_count = len(verified)
    retired_count = len(retired)
    derived_count = len(derived)
    file_path = ""
    if latest_eval:
        file_path = repo_rel(latest_eval_path)
    elif verified_file_payload:
        file_path = repo_rel(verified_axioms_path)
    elif constraints_payload:
        file_path = repo_rel(constraints_path)
    backing_files = []
    if latest_eval:
        backing_files.append(repo_rel(latest_eval_path))
    if verified_file_payload:
        backing_files.append(repo_rel(verified_axioms_path))
    if constraints_payload:
        backing_files.append(repo_rel(constraints_path))
    summary = (
        f"{verified_count} verified axioms; {retired_count} retired; {derived_count} derived constraints."
        if file_path
        else "No run-learned axioms or derived constraints are loaded yet."
    )
    return {
        "status": "recorded" if verified_count or retired_count or derived_count else ("none recorded" if file_path else "not loaded"),
        "summary": summary,
        "file": file_path,
        "verified": verified,
        "retired": retired,
        "derived_constraints": derived,
        "backing_files": unique_values(backing_files),
        "verified_count": verified_count,
        "retired_count": retired_count,
        "derived_constraint_count": derived_count,
    }


def saved_project_summary_payload(
    *,
    project: str,
    intake: str,
    project_state: dict[str, Any],
    project_object_contract: dict[str, Any],
    case_file: dict[str, Any],
) -> dict[str, Any]:
    """Small reader-facing summary at the top of a saved project file."""

    def section(name: str) -> dict[str, Any]:
        value = project_state.get(name)
        return value if isinstance(value, dict) else {}

    charter = section("charter")
    thesis = section("thesis")
    change_test = section("change_test")
    sources = section("sources")
    evidence = section("evidence")
    thesis_support = section("thesis_support")
    recent_changes = section("recent_changes")
    if not isinstance(recent_changes.get("substantive_inspection"), dict):
        substantive_rows = [
            row
            for row in [
                recent_changes.get("latest_source_or_evidence_change"),
                recent_changes.get("latest_run"),
            ]
            if isinstance(row, dict) and row.get("status") == "recorded"
        ]
        latest_substantive = max(substantive_rows, key=change_row_time) if substantive_rows else {}
        recent_changes = dict(recent_changes)
        recent_changes["substantive_inspection"] = recent_change_inspection_target(latest_substantive, {})
    admission = section("admission")
    run = section("run")
    report = section("report")
    assumptions = section("assumptions")
    axioms = section("axioms")
    formalization = section("formalization")
    files = section("files")
    next_action = section("next_action")
    action_summary = section("action_summary")
    actions = project_state.get("actions") if isinstance(project_state.get("actions"), list) else []
    file_items = files.get("items") if isinstance(files.get("items"), list) else []
    previewable_files = [
        item
        for item in file_items
        if isinstance(item, dict) and item.get("previewable") and item.get("path")
    ]
    recent_receipts = case_file.get("recent_receipts") if isinstance(case_file.get("recent_receipts"), list) else []
    live_context = case_file.get("live_context") if isinstance(case_file.get("live_context"), dict) else {}
    report_contract = live_context.get("report_contract") if isinstance(live_context.get("report_contract"), dict) else {}
    report_authority = {
        "status": str(report_contract.get("display_status") or report_contract.get("status") or report.get("status") or ""),
        "allowed_count": len(report_contract.get("allowed_actions") or []),
        "conditional_count": len(report_contract.get("conditional_actions") or []),
        "deferred_count": len(report_contract.get("deferred_actions") or []),
        "forbidden_count": len(report_contract.get("forbidden_upgrades") or []),
        "first_allowed_action": str(((report_contract.get("allowed_actions") or [{}])[0] or {}).get("label") or ""),
        "first_conditional_rule": str(((report_contract.get("conditional_actions") or [{}])[0] or {}).get("label") or ""),
        "first_forbidden_upgrade": str(((report_contract.get("forbidden_upgrades") or [{}])[0] or {}).get("label") or ""),
        "contract": str(report_contract.get("report_support_contract") or report.get("contract") or ""),
    }
    pending_intake = (
        live_context.get("pending_intake_edit")
        if isinstance(live_context.get("pending_intake_edit"), dict)
        else {}
    )
    pending_source_import = (
        live_context.get("pending_source_import")
        if isinstance(live_context.get("pending_source_import"), dict)
        else {}
    )
    pending_source_edit = (
        live_context.get("pending_source_edit")
        if isinstance(live_context.get("pending_source_edit"), dict)
        else {}
    )
    pending_gap = (
        live_context.get("pending_evidence_gap_justification")
        if isinstance(live_context.get("pending_evidence_gap_justification"), dict)
        else {}
    )
    pending_work_items = [
        "intake" if pending_intake.get("status") == "pending_unsaved" else "",
        "file draft" if pending_source_import.get("status") == "pending_unsaved" else "",
        "file edit" if pending_source_edit.get("status") == "pending_unsaved" else "",
        "evidence-gap justification" if pending_gap.get("status") == "pending_unsaved" else "",
    ]
    pending_work_items = [item for item in pending_work_items if item]
    proof_paths: list[str] = []
    for action in actions[:5]:
        if not isinstance(action, dict):
            continue
        for path in action.get("receipt_paths") or []:
            if path:
                proof_paths.append(str(path))
        for ref in action.get("evidence_refs") or []:
            if isinstance(ref, dict):
                ref_path = ref.get("path") or ref.get("value")
                if ref_path:
                    proof_paths.append(str(ref_path))
            elif ref:
                proof_paths.append(str(ref))
        source = str(action.get("source") or "")
        if source:
            proof_paths.append(source)
    for path in [
        charter.get("file"),
        evidence.get("file"),
        evidence.get("gap_file"),
        thesis_support.get("evidence_support_file_path"),
        thesis_support.get("source_index_path"),
        recent_changes.get("latest_receipt_path"),
        (recent_changes.get("latest_review") or {}).get("receipt_path") if isinstance(recent_changes.get("latest_review"), dict) else "",
        (recent_changes.get("latest_review") or {}).get("artifact_path") if isinstance(recent_changes.get("latest_review"), dict) else "",
        (recent_changes.get("latest_next_step") or {}).get("receipt_path") if isinstance(recent_changes.get("latest_next_step"), dict) else "",
        (recent_changes.get("latest_next_step") or {}).get("artifact_path") if isinstance(recent_changes.get("latest_next_step"), dict) else "",
        (recent_changes.get("latest_source_or_evidence_change") or {}).get("receipt_path") if isinstance(recent_changes.get("latest_source_or_evidence_change"), dict) else "",
        (recent_changes.get("latest_source_or_evidence_change") or {}).get("artifact_path") if isinstance(recent_changes.get("latest_source_or_evidence_change"), dict) else "",
        (recent_changes.get("latest_project_check") or {}).get("receipt_path") if isinstance(recent_changes.get("latest_project_check"), dict) else "",
        (recent_changes.get("latest_project_check") or {}).get("artifact_path") if isinstance(recent_changes.get("latest_project_check"), dict) else "",
        (recent_changes.get("latest_project_file") or {}).get("receipt_path") if isinstance(recent_changes.get("latest_project_file"), dict) else "",
        (recent_changes.get("latest_project_file") or {}).get("artifact_path") if isinstance(recent_changes.get("latest_project_file"), dict) else "",
        report.get("contract"),
        axioms.get("file"),
        *[path for path in axioms.get("backing_files") or [] if path],
    ]:
        if path:
            proof_paths.append(str(path))
    for item in previewable_files[:12]:
        proof_paths.append(str(item.get("path") or ""))
    unique_proof_paths = unique_values(proof_paths)
    project_audit = project_to_thesis_audit_payload(
        project_state=project_state,
        project_object_contract=project_object_contract,
    )
    return {
        "schema": "ztare-saved-project-summary-v1",
        "project": project,
        "intake": intake,
        "display_label": project.replace("_", " "),
        "charter": {
            "status": str(charter.get("status") or ""),
            "summary": str(charter.get("summary") or ""),
            "file": str(charter.get("file") or ""),
            "exists": bool(charter.get("exists")),
        },
        "thesis": str(thesis.get("text") or ""),
        "change_test": str(change_test.get("text") or ""),
        "non_claims": [str(item) for item in assumptions.get("non_claims") or [] if item],
        "axioms": {
            "status": str(axioms.get("status") or ""),
            "summary": str(axioms.get("summary") or ""),
            "file": str(axioms.get("file") or ""),
            "backing_files": [str(path) for path in axioms.get("backing_files") or [] if path],
            "verified_count": safe_int(axioms.get("verified_count")),
            "retired_count": safe_int(axioms.get("retired_count")),
            "derived_constraint_count": safe_int(axioms.get("derived_constraint_count")),
        },
        "formalization": {
            "status": str(formalization.get("status") or ""),
            "summary": str(formalization.get("summary") or ""),
            "preferred_root": str(formalization.get("preferred_root") or ""),
            "target_template": str(formalization.get("target_template") or ""),
            "target_count": safe_int(formalization.get("target_count")),
            "lean_file_count": safe_int(formalization.get("lean_file_count")),
            "files": formalization.get("files") if isinstance(formalization.get("files"), list) else [],
        },
        "thesis_support": {
            "status": str(thesis_support.get("status") or ""),
            "summary": (
                f"{safe_int(thesis_support.get('supported_count'))} supported; "
                f"{safe_int(thesis_support.get('weak_or_open_count'))} weak/open."
                if thesis_support
                else ""
            ),
            "claim_count": safe_int(thesis_support.get("claim_count")),
            "supported_count": safe_int(thesis_support.get("supported_count")),
            "weak_or_open_count": safe_int(thesis_support.get("weak_or_open_count")),
            "evidence_support_file_path": str(thesis_support.get("evidence_support_file_path") or ""),
            "source_index_path": str(thesis_support.get("source_index_path") or ""),
        },
        "file_inventory": {
            "schema": str(files.get("schema") or ""),
            "item_count": safe_int(files.get("item_count")),
            "previewable_count": safe_int(files.get("previewable_count")),
            "missing_count": safe_int(files.get("missing_count")),
            "role_counts": files.get("role_counts") if isinstance(files.get("role_counts"), dict) else {},
            "previewable_files": [
                {
                    "label": str(item.get("label") or ""),
                    "role": str(item.get("role") or ""),
                    "path": str(item.get("path") or ""),
                    "display_kind": str(item.get("display_kind") or ""),
                    "format": str(item.get("format") or ""),
                }
                for item in previewable_files[:12]
            ],
        },
        "next_action": {
            "label": str(next_action.get("label") or ""),
            "detail": str(next_action.get("detail") or ""),
            "workspace": str(next_action.get("workspace") or ""),
            "subsection": str(next_action.get("subsection") or ""),
        },
        "readiness": {
            "sources": str(sources.get("status") or ""),
            "evidence": str(evidence.get("status") or ""),
            "admission": str(admission.get("status") or ""),
            "run": str(run.get("status") or ""),
            "report": str(report.get("status") or ""),
        },
        "report_authority": report_authority,
        "open_action_count": safe_int(action_summary.get("total_count")) if action_summary else len(actions),
        "open_project_repair_count": safe_int(action_summary.get("project_repair_count")),
        "open_project_inspect_count": safe_int(action_summary.get("project_inspect_count")),
        "open_advisory_count": safe_int(action_summary.get("advisory_count")),
        "recent_receipt_count": len(recent_receipts),
        "recent_changes": {
            "status": str(recent_changes.get("status") or ""),
            "recorded_count": safe_int(recent_changes.get("recorded_count")),
            "receipt_count": safe_int(recent_changes.get("receipt_count")),
            "summary": str(recent_changes.get("summary") or ""),
            "latest_receipt_path": str(recent_changes.get("latest_receipt_path") or ""),
            "latest_review": recent_changes.get("latest_review") if isinstance(recent_changes.get("latest_review"), dict) else {},
            "latest_next_step": recent_changes.get("latest_next_step") if isinstance(recent_changes.get("latest_next_step"), dict) else {},
            "latest_source_or_evidence_change": recent_changes.get("latest_source_or_evidence_change")
            if isinstance(recent_changes.get("latest_source_or_evidence_change"), dict)
            else {},
            "latest_project_check": recent_changes.get("latest_project_check")
            if isinstance(recent_changes.get("latest_project_check"), dict)
            else {},
            "substantive_inspection": recent_changes.get("substantive_inspection")
            if isinstance(recent_changes.get("substantive_inspection"), dict)
            else {},
            "latest_project_file": recent_changes.get("latest_project_file")
            if isinstance(recent_changes.get("latest_project_file"), dict)
            else {},
        },
        "pending_work": {
            "status": "pending" if pending_work_items else "clean",
            "items": pending_work_items,
            "count": len(pending_work_items),
            "intake_changed_fields": [
                str(item)
                for item in pending_intake.get("changed_fields", [])
                if item
            ] if pending_intake else [],
            "pending_source_filename": str(pending_source_import.get("filename") or ""),
            "pending_source_type": str(pending_source_import.get("source_type") or ""),
            "pending_source_gap": pending_source_import.get("evidence_gap")
            if isinstance(pending_source_import.get("evidence_gap"), dict)
            else {},
            "pending_gap_index": str(pending_gap.get("index") or ""),
            "pending_gap_evidence_refs": [
                str(item)
                for item in pending_gap.get("evidence_refs", [])
                if item
            ] if pending_gap else [],
        },
        "latest_review": latest_receipt_summary(recent_receipts, "review"),
        "latest_next_step": latest_receipt_summary(recent_receipts, "next_step"),
        "project_object_ok": bool(project_object_contract.get("ok")),
        "project_object_failed_count": safe_int(project_object_contract.get("failed_count")),
        "project_object_failed_checks": (
            project_object_contract.get("failed_checks")
            if isinstance(project_object_contract.get("failed_checks"), list)
            else []
        ),
        "project_to_thesis_audit": project_audit,
        "proof_path_count": len(unique_proof_paths),
        "proof_paths": unique_proof_paths[:20],
    }


def path_under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


preview_path_allowed = recent_changes_core.preview_path_allowed


def file_preview_kind(path: str) -> str:
    text = path.lower()
    name = PurePosixPath(path).name.lower()
    if name == "thesis.md":
        return "thesis"
    if name == "current_iteration.md":
        return "current_draft"
    if name == "test_model.py":
        return "project_test"
    if name.endswith("_intake.json") or name == "intake.json":
        return "project_intake"
    if name == "source_index.json":
        return "source_index"
    if name == "source_index_receipt.json":
        return "source_index_receipt"
    if "/source_notes/" in text:
        return "source_note"
    if re.fullmatch(r"forensic_workbench_(?:case|project)_file_[a-f0-9]{12}\.json", name):
        return "project_file"
    if "evidence_fetch" in text or "forensic_workbench_evidence_fetches" in text:
        return "evidence_fetch"
    if name == "evidence_gap_resolutions.json":
        return "evidence_gap_resolution"
    if "evidence_gap" in text:
        return "evidence_gap"
    if "compiled_evidence" in text or name in {"evidence.txt", "evidence.md", "evidence.json"}:
        return "evidence"
    if name == "source_health.json":
        return "source_warnings"
    if name == "shadow_recommendations.json":
        return "suggested_next_moves"
    if "/action_intelligence/" in text:
        return "action_guidance"
    if name.endswith("_packet.json"):
        return "project_launch_bundle"
    if "/raw/" in text:
        return "source"
    if "latest_eval_results" in text or "eval_history" in text or "run_history" in text or "iteration_telemetry" in text:
        return "run_results"
    if "latest_information_yield" in text:
        return "information_yield"
    if "cold_shot_runs" in text:
        return "run_policy_decisions"
    if "post_run_synthesis_attempts" in text:
        return "report_synthesis_attempts"
    if "probability_dag" in text:
        return "probability_model"
    if "derived_constraints" in text or "axiom" in text:
        return "axioms_constraints"
    if text.startswith("rubrics/"):
        return "rubric"
    if text.startswith("docs/") or name in {"readme.md", "priority_roadmap.md"}:
        return "guide"
    if "report" in text or "/synthesis/" in text:
        return "report"
    if "receipt" in text or "forensic_workbench_" in text:
        return "receipt"
    if name.endswith(".json"):
        return "project_data"
    return "project_file"


def file_preview_display_kind(kind: str) -> str:
    return {
        "thesis": "Thesis",
        "current_draft": "Current draft",
        "project_test": "Project test",
        "project_intake": "Project brief",
        "evidence_fetch": "Evidence fetch",
        "evidence_gap": "Evidence gap",
        "evidence_gap_resolution": "Evidence-gap history",
        "evidence": "Evidence",
        "source_warnings": "File and evidence warnings",
        "suggested_next_moves": "Suggested next moves",
        "action_guidance": "Action guidance",
        "project_launch_bundle": "Project launch bundle",
        "source": "Source",
        "source_index": "Source index",
        "source_index_receipt": "File-index history",
        "source_note": "Source note",
        "run_results": "Run results",
        "information_yield": "Truth-yield signal",
        "run_policy_decisions": "Run setup choices",
        "report_synthesis_attempts": "Report synthesis attempts",
        "probability_model": "Probability model",
        "axioms_constraints": "Axioms and constraints",
        "rubric": "Scoring guide",
        "report": "Report",
        "receipt": "Saved work",
        "guide": "Guide",
        "project_data": "Project data",
        "project_file": "Project file",
    }.get(kind, "Project file")


def file_preview_format(path: str) -> str:
    suffix = PurePosixPath(path).suffix.lower()
    if suffix == ".md":
        return "Markdown"
    if suffix == ".jsonl":
        return "JSON lines"
    if suffix == ".json":
        return "JSON"
    if suffix == ".csv":
        return "CSV"
    if suffix in {".yaml", ".yml"}:
        return "YAML"
    if suffix == ".txt":
        return "Text"
    return "Text"


REPO_PATH_REF_RE = re.compile(
    r"\b(?:analytics/public|docs|examples|forensic-workbench|projects|rubrics|ztare_proofs/leanmill-formalizations)"
    r"/[A-Za-z0-9_./+=:@#-]+\.(?:md|txt|json|jsonl|csv|yaml|yml|lean)\b"
)


JSON_PREVIEW_PATH_KEY_RE = re.compile(
    r"(^|_)(path|paths|file|files|artifact|artifacts|receipt|receipts|manifest|manifests|ref|refs)($|_)"
)


def preview_referenced_paths(text: str, *, source_path: str = "", limit: int = 12) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    source_parts = PurePosixPath(source_path).parts if source_path else ()

    def resolved_preview_path(path: str, *, require_exists: bool = False) -> str:
        candidates = [path]
        if len(source_parts) >= 2 and source_parts[0] == "projects":
            project_root = f"projects/{source_parts[1]}"
            source_parent = PurePosixPath(*source_parts[:-1]).as_posix() if len(source_parts) > 1 else ""
            if path.startswith("raw/"):
                candidates.append(f"{project_root}/{path}")
            elif path.startswith("source_notes/"):
                candidates.append(f"{project_root}/workspace/{path}")
            elif "/" not in path and PurePosixPath(path).suffix:
                candidates.append(f"{project_root}/raw/{path}")
            if source_parent and not path.startswith(("projects/", "docs/", "examples/", "analytics/", "rubrics/", "forensic-workbench/", "ztare_proofs/")):
                candidates.append(f"{source_parent}/{path}")
        for candidate in candidates:
            normalized = PurePosixPath(candidate).as_posix()
            if not preview_path_allowed(normalized):
                continue
            if require_exists and not (snapshot.REPO / normalized).is_file():
                continue
            return normalized
        return ""

    def add(value: Any, *, require_exists: bool = False) -> None:
        if len(found) >= limit:
            return
        path = str(value or "").strip()
        if not path or "<" in path or ">" in path:
            return
        if require_exists and (len(path) > 320 or "\n" in path):
            return
        path = resolved_preview_path(path, require_exists=require_exists)
        if not path or path in seen:
            return
        seen.add(path)
        found.append(path)

    def add_json_path_values(value: Any, *, depth: int = 0) -> None:
        if len(found) >= limit or depth > 6:
            return
        if isinstance(value, dict):
            for key, child in value.items():
                if len(found) >= limit:
                    return
                key_text = str(key)
                if JSON_PREVIEW_PATH_KEY_RE.search(key_text):
                    if isinstance(child, str):
                        add(child, require_exists=True)
                    elif isinstance(child, list):
                        for item in child:
                            if isinstance(item, str):
                                add(item, require_exists=True)
                            elif isinstance(item, dict):
                                add_json_path_values(item, depth=depth + 1)
                add_json_path_values(child, depth=depth + 1)
        elif isinstance(value, list):
            for item in value[:80]:
                add_json_path_values(item, depth=depth + 1)

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, dict):
        if PurePosixPath(source_path).name == "source_index.json":
            for source in parsed.get("sources") or []:
                if not isinstance(source, dict):
                    continue
                add(source.get("path") or source.get("source_path"), require_exists=True)
                add(source.get("note_path"), require_exists=True)
        summary = parsed.get("project_summary")
        if isinstance(summary, dict):
            recent_changes = summary.get("recent_changes")
            if isinstance(recent_changes, dict):
                for key in (
                    "latest_source_or_evidence_change",
                    "substantive_inspection",
                    "latest_review",
                    "latest_next_step",
                    "latest_project_file",
                ):
                    row = recent_changes.get(key)
                    if not isinstance(row, dict):
                        continue
                    add(row.get("preview_path"))
                    add(row.get("artifact_path"))
                    add(row.get("receipt_path"))
            for path in summary.get("proof_paths") or []:
                add(path)
            file_inventory = summary.get("file_inventory")
            previewable_files = (
                file_inventory.get("previewable_files")
                if isinstance(file_inventory, dict)
                else []
            )
            for item in previewable_files or []:
                if isinstance(item, dict):
                    add(item.get("path"))
        for gap in list(parsed.get("evidence_gaps") or []) + list(parsed.get("active_gaps") or []):
            if not isinstance(gap, dict):
                continue
            contract = gap.get("recovery_contract")
            if not isinstance(contract, dict):
                contract = {}
            add(gap.get("required_surface") or contract.get("required_surface"), require_exists=True)
    if parsed is not None:
        add_json_path_values(parsed)

    for match in REPO_PATH_REF_RE.finditer(text):
        value = match.group(0).strip().rstrip(").,;:")
        add(value, require_exists=True)
        if len(found) >= limit:
            break
    return found


def file_preview_reference_item(path: str) -> dict[str, Any]:
    normalized = PurePosixPath(path).as_posix()
    kind = file_preview_kind(normalized)
    display_kind = file_preview_display_kind(kind)
    resolved = snapshot.REPO / normalized
    return {
        "path": normalized,
        "kind": kind,
        "display_kind": display_kind,
        "format": file_preview_format(normalized),
        "exists": resolved.is_file(),
        "label": f"{display_kind}: {PurePosixPath(normalized).name}",
    }


def file_preview_payload(path: str) -> dict[str, Any]:
    if not path:
        raise ValueError("path is required")
    require_visible_repo_path(path)
    candidate = Path(path)
    if candidate.is_absolute():
        raise ValueError("path must be relative to the repository")
    normalized = PurePosixPath(path).as_posix()
    if not preview_path_allowed(normalized):
        raise ValueError("path is outside the workbench preview roots")
    resolved = (snapshot.REPO / candidate).resolve()
    repo = snapshot.REPO.resolve()
    if resolved != repo and repo not in resolved.parents:
        raise ValueError("path escapes the repository")
    if not resolved.exists():
        raise FileNotFoundError(f"path does not exist: {path}")
    if not resolved.is_file():
        raise ValueError(f"path is not a file: {path}")
    raw = WORKBENCH_STORE.read_bytes(resolved)
    truncated = len(raw) > MAX_PREVIEW_BYTES
    preview_bytes = raw[:MAX_PREVIEW_BYTES]
    try:
        text = preview_bytes.decode("utf-8")
        encoding = "utf-8"
    except UnicodeDecodeError:
        text = preview_bytes.decode("utf-8", errors="replace")
        encoding = "utf-8-replacement"
    kind = file_preview_kind(normalized)
    preview_lines = text.splitlines()
    line_count = len(preview_lines)
    non_empty_line_count = sum(1 for line in preview_lines if line.strip())
    referenced_paths = [
        ref for ref in preview_referenced_paths(text, source_path=normalized)
        if not project_from_repo_path(ref) or project_is_visible(project_from_repo_path(ref))
    ]
    return {
        "schema": "ztare-forensic-workbench-file-preview-v1",
        "ok": True,
        "served_from": "local_api",
        "path": snapshot.rel(resolved),
        "kind": kind,
        "display_kind": file_preview_display_kind(kind),
        "format": file_preview_format(normalized),
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "line_count": line_count,
        "non_empty_line_count": non_empty_line_count,
        "truncated": truncated,
        "encoding": encoding,
        "referenced_paths": referenced_paths,
        "referenced_items": [file_preview_reference_item(ref) for ref in referenced_paths],
        "text": text,
    }


def project_file_inventory_priority(*, path: str, role: str, label: str, kind: str) -> int:
    name = PurePosixPath(path).name.lower()
    label_text = str(label or "").lower()
    if role == "charter":
        return 8
    if role == "intake":
        return 10
    if role == "thesis":
        return 12
    if role == "source":
        if name == "source_type_map.json":
            return 80
        return 20
    if role == "evidence":
        if "compiled_evidence_packet" in name or label_text in {"compiled evidence", "thesis support"}:
            return 10
        if "provenance" in name:
            return 20
        if "replay" in name:
            return 30
        if "source_index" in name:
            return 40
        return 50
    if role == "evidence_gap":
        return 10 if "active" in label_text else 20
    if role == "run":
        return 10 if kind == "run_results" else 30
    if role == "axiom":
        return 10
    if role == "formalization":
        return 10 if kind in {"markdown", "lean", "text"} else 30
    if role == "report":
        return 10 if "support" in label_text or "report_support_contract" in name else 30
    if role == "project_file":
        return 10
    if role == "receipt":
        return 20
    return 50


def project_file_inventory_role_order(role: str) -> int:
    return {
        "charter": 8,
        "intake": 10,
        "thesis": 12,
        "evidence": 20,
        "evidence_gap": 25,
        "source": 30,
        "run": 40,
        "axiom": 45,
        "formalization": 47,
        "report": 50,
        "research_map": 52,
        "project_file": 55,
        "receipt": 60,
    }.get(role, 90)


def project_file_inventory_item(path: str, *, role: str, label: str, reason: str = "") -> dict[str, Any] | None:
    normalized = PurePosixPath(str(path or "").strip()).as_posix()
    if not normalized or "<" in normalized or ">" in normalized or not preview_path_allowed(normalized):
        return None
    kind = file_preview_kind(normalized)
    item: dict[str, Any] = {
        "path": normalized,
        "role": role,
        "label": label or file_preview_display_kind(kind),
        "reason": reason,
        "kind": kind,
        "display_kind": file_preview_display_kind(kind),
        "format": file_preview_format(normalized),
        "priority": project_file_inventory_priority(path=normalized, role=role, label=label, kind=kind),
        "role_order": project_file_inventory_role_order(role),
        "exists": False,
        "previewable": False,
    }
    if role == "evidence_gap" and label == "Needed evidence":
        item["kind"] = "evidence_gap"
        item["display_kind"] = "Needed evidence"
    try:
        resolved = WORKBENCH_STORE.resolve(normalized)
    except ValueError:
        return None
    if resolved.is_file():
        stat = resolved.stat()
        item.update(
            {
                "exists": True,
                "previewable": True,
                "bytes": stat.st_size,
                "sha256": hashlib.sha256(WORKBENCH_STORE.read_bytes(resolved)).hexdigest(),
            }
        )
    return item


def leanmill_file_row(path: Path, *, root: Path) -> dict[str, Any]:
    """Compact file row for a project-local LeanMill file (name, repo path, group, size)."""
    return {
        "path": repo_rel(path),
        "name": path.name,
        "group": path.parent.relative_to(root).as_posix() if path.parent != root else ".",
        "size_bytes": path.stat().st_size if path.exists() else 0,
    }


def project_formalization_payload(project: str, *, limit: int = 24) -> dict[str, Any]:
    """Project-local formal targets and proof files.

    Preferred shape is ``projects/<project>/leanmill/``. Existing project-local
    folders are still detected so old work remains inspectable.
    """

    project = snapshot.validate_project_slug(project)
    project_root = snapshot.REPO / "projects" / project
    preferred_root = project_root / "leanmill"
    candidate_roots = [
        ("project_leanmill", preferred_root),
        ("workspace_targets", project_root / "workspace" / "leanmill_targets"),
        ("lean4", project_root / "lean4"),
        ("formalizations", project_root / "formalizations"),
    ]
    roots = [
        {"kind": kind, "path": repo_rel(root), "rel": repo_rel(root), "exists": root.exists()}
        for kind, root in candidate_roots
    ]
    files: list[Path] = []
    for _, root in candidate_roots:
        if not root.exists():
            continue
        files.extend(
            sorted(
                path
                for path in root.rglob("*")
                if path.is_file()
                and path.suffix.lower() in {".md", ".txt", ".lean", ".json", ".yaml", ".yml"}
                and ".lake" not in path.parts
            )
        )
    unique_files = []
    seen: set[str] = set()
    for path in files:
        rel = repo_rel(path)
        if rel in seen:
            continue
        seen.add(rel)
        unique_files.append(path)
    target_files = [
        path
        for path in unique_files
        if path.suffix.lower() in {".md", ".txt"}
        and any(token in path.name.lower() for token in ("target", "blueprint", "formal", "notes"))
    ]
    lean_files = [path for path in unique_files if path.suffix.lower() == ".lean"]
    history_files = [
        path
        for path in unique_files
        if path.suffix.lower() in {".json", ".yaml", ".yml"}
        or "history" in path.parts
    ]
    preferred_target_template = f"projects/{project}/leanmill/targets/{{slug}}_target.md"
    history_path = f"projects/{project}/leanmill/history/leanmill_targets.jsonl"
    latest_path = f"projects/{project}/leanmill/history/latest_leanmill_target.json"
    status = "attached" if unique_files else ("ready for targets" if preferred_root.exists() else "not started")
    return {
        "schema": "ztare-project-formalization-v1",
        "project": project,
        "status": status,
        "summary": (
            f"{len(target_files)} target/note file(s), {len(lean_files)} Lean file(s)."
            if unique_files
            else "No project-local LeanMill files yet. Use this project when the thesis has a theorem, definition, or proof surface worth checking."
        ),
        "preferred_root": repo_rel(preferred_root),
        "folder_contract": {
            "root": repo_rel(preferred_root),
            "targets": f"projects/{project}/leanmill/targets",
            "lean": f"projects/{project}/leanmill/lean",
            "notes": f"projects/{project}/leanmill/notes",
            "history": f"projects/{project}/leanmill/history",
            "readme": f"projects/{project}/leanmill/README.md",
            "description": "Project-local LeanMill files: formal targets and notes in targets/, Lean files in lean/, supporting notes in notes/, saved history in history/.",
        },
        "target_template": preferred_target_template,
        "history_path": history_path,
        "latest_path": latest_path,
        "root_count": sum(1 for row in roots if row["exists"]),
        "roots": roots,
        "target_count": len(target_files),
        "lean_file_count": len(lean_files),
        "history_file_count": len(history_files),
        "files": [leanmill_file_row(path, root=project_root) for path in unique_files[:limit]],
        "targets": [leanmill_file_row(path, root=project_root) for path in target_files[:limit]],
        "lean_files": [leanmill_file_row(path, root=project_root) for path in lean_files[:limit]],
        "history_files": [leanmill_file_row(path, root=project_root) for path in history_files[:limit]],
        "write": {
            "enabled": True,
            "route": "POST /api/leanmill/target",
            "cli": f"ztare leanmill target --project {project} --title <title> --target <statement> --notes-file <notes.md> --json",
            "target_template": preferred_target_template,
            "history_path": history_path,
            "latest_path": latest_path,
            "no_change_boundary": "Previewing a target does not write files. Saving writes only the project-local LeanMill target and history files.",
        },
    }


PROJECT_FILE_GROUP_DEFINITIONS: tuple[dict[str, Any], ...] = (
    {
        "id": "all",
        "label": "All files",
        "roles": None,
        "help": "Every project file the workbench can inspect.",
        "action_workspace": "sources",
        "action_subsection": "Prepare files",
        "action_label": "Open file work",
    },
    {
        "id": "overview",
        "label": "Charter, thesis & brief",
        "roles": ("charter", "intake", "thesis"),
        "help": "The human project charter, thesis, limits, and source files the project is built around.",
        "action_workspace": "overview",
        "action_subsection": "Charter",
        "action_label": "Open charter",
    },
    {
        "id": "source",
        "label": "Source material",
        "roles": ("source",),
        "help": "Raw notes, imports, and source-role maps before they become evidence.",
        "action_workspace": "sources",
        "action_subsection": "Prepare files",
        "action_label": "Prepare source files",
    },
    {
        "id": "evidence",
        "label": "Evidence",
        "roles": ("evidence", "evidence_gap"),
        "help": "The compiled view of what the source files support, weaken, or leave missing.",
        "action_workspace": "sources",
        "action_subsection": "Prepare files",
        "action_label": "Open evidence",
    },
    {
        "id": "run",
        "label": "Runs & lessons",
        "roles": ("run",),
        "help": "Scores, run output, learned constraints, and the next check suggested by a run.",
        "action_workspace": "run",
        "action_subsection": "Ready to run",
        "action_label": "Open pressure-test",
    },
    {
        "id": "report",
        "label": "Report readiness",
        "roles": ("report",),
        "help": "Files that show whether the report matches the current project state.",
        "action_workspace": "save",
        "action_subsection": "Report readiness",
        "action_label": "Open report readiness",
    },
    {
        "id": "research_map",
        "label": "Research map",
        "roles": ("research_map",),
        "help": "Portable map of the thesis, support, gaps, runs, report state, formal work, graph context, and next action.",
        "action_workspace": "overview",
        "action_subsection": "Research map",
        "action_label": "Open research map",
    },
    {
        "id": "saved",
        "label": "Saved project",
        "roles": ("project_file",),
        "help": "Saved project files that package the current project state.",
        "action_workspace": "review",
        "action_subsection": "Saved history",
        "action_label": "Open saved work",
    },
    {
        "id": "receipt",
        "label": "Saved history",
        "roles": ("receipt",),
        "help": "Saved edits, reviews, next steps, and file-change records.",
        "action_workspace": "review",
        "action_subsection": "Saved history",
        "action_label": "Open saved history",
    },
    {
        "id": "axiom",
        "label": "Assumptions",
        "roles": ("axiom",),
        "help": "Run-learned assumptions and constraints that should be inspected before reuse.",
        "action_workspace": "overview",
        "action_subsection": "Assumptions",
        "action_label": "Open assumptions",
    },
    {
        "id": "formalization",
        "label": "Formal work",
        "roles": ("formalization",),
        "help": "Project-local LeanMill targets, research notes, and Lean files.",
        "action_workspace": "leanmill",
        "action_subsection": "Draft target",
        "action_label": "Open formal work",
    },
)


def project_file_groups_payload(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    for definition in PROJECT_FILE_GROUP_DEFINITIONS:
        raw_roles = definition.get("roles")
        roles = {str(role) for role in raw_roles} if raw_roles else set()
        group_items = [
            item
            for item in items
            if isinstance(item, dict) and (not roles or str(item.get("role") or "") in roles)
        ]
        groups.append(
            {
                "id": str(definition["id"]),
                "label": str(definition["label"]),
                "roles": sorted(roles) if roles else [],
                "help": str(definition["help"]),
                "count": len(group_items),
                "previewable_count": sum(1 for item in group_items if item.get("previewable")),
                "missing_count": sum(1 for item in group_items if not item.get("exists")),
                "action": {
                    "workspace": str(definition["action_workspace"]),
                    "subsection": str(definition["action_subsection"]),
                    "label": str(definition["action_label"]),
                },
            }
        )
    return groups


def evidence_gap_required_surface_path(project: str, required_surface: str) -> str:
    surface = PurePosixPath(str(required_surface or "").strip()).as_posix()
    if not surface:
        return ""
    if surface.startswith("projects/"):
        return surface
    if "/" in surface:
        return f"projects/{project}/{surface}"
    return f"projects/{project}/raw/{surface}"


def latest_project_file_paths_payload(project: str, receipts: dict[str, Any]) -> dict[str, Any]:
    workspace = snapshot.REPO / "projects" / project / "workspace"
    current_latest = workspace / "forensic_workbench_latest_project_file_write.json"
    legacy_latest = workspace / "forensic_workbench_latest_case_file_write.json"
    latest_path_obj = current_latest if current_latest.exists() else legacy_latest if legacy_latest.exists() else current_latest
    latest_write_path = repo_rel(latest_path_obj)
    receipt_rows = receipts.get("receipts") if isinstance(receipts.get("receipts"), list) else []
    latest_row = latest_receipt_by_kind(receipt_rows, {"project_file", "case_file"})
    latest_payload: dict[str, Any] = {}
    if latest_path_obj.exists():
        try:
            latest_payload = read_json_object(latest_path_obj, repo_rel(latest_path_obj))
        except (OSError, ValueError):
            latest_payload = {}
    receipt_paths = receipts.get("paths") if isinstance(receipts.get("paths"), dict) else {}
    receipt_path = str(
        latest_row.get("path")
        or latest_payload.get("path")
        or receipt_paths.get("project_file")
        or receipt_paths.get("case_file")
        or repo_rel(workspace / "forensic_workbench_project_files.jsonl")
    )
    artifact_path = str(
        latest_row.get("project_file_path")
        or latest_row.get("case_file_path")
        or latest_row.get("artifact_path")
        or latest_payload.get("project_file_path")
        or latest_payload.get("case_file_path")
        or ""
    )
    return {
        "status": "recorded" if artifact_path or latest_path_obj.exists() or latest_row else "missing",
        "latest_project_file": artifact_path,
        "latest_project_file_receipt": receipt_path,
        "latest_project_file_write": latest_write_path,
        "latest_project_file_summary": str(latest_row.get("display_summary") or latest_row.get("summary") or ""),
        "latest_project_file_applied_at": str(latest_row.get("applied_at") or latest_payload.get("applied_at") or ""),
    }


def project_file_inventory_payload(
    *,
    project: str,
    intake: str,
    source_list: dict[str, Any],
    evidence_readiness: dict[str, Any],
    evidence_gap_recovery: dict[str, Any],
    report: dict[str, Any],
    run_history: dict[str, Any],
    receipts: dict[str, Any],
    axiom_state: dict[str, Any],
    thesis_support: dict[str, Any],
    formalization_state: dict[str, Any] | None = None,
    limit: int = 80,
) -> dict[str, Any]:
    project_root = snapshot.REPO / "projects" / project
    seen: set[str] = set()
    items: list[dict[str, Any]] = []

    def add(path: Any, *, role: str, label: str, reason: str = "") -> None:
        raw = str(path or "").strip()
        if raw and "/" not in raw:
            candidate = project_root / "raw" / raw
            if candidate.exists():
                raw = repo_rel(candidate)
        item = project_file_inventory_item(raw, role=role, label=label, reason=reason)
        if not item or item["path"] in seen:
            return
        seen.add(item["path"])
        items.append(item)

    add(project_charter_rel(project), role="charter", label="Project charter", reason="Human project mandate used by the autoresearch loop.")
    add(intake, role="intake", label="Project brief", reason="Defines the thesis, caveats, source files, and evidence files.")
    add(f"projects/{project}/thesis.md", role="thesis", label="Thesis", reason="Readable project thesis when present.")
    add(f"projects/{project}/raw/source_type_map.json", role="source", label="Source role map", reason="Maps raw files to source roles.")
    latest_project_file_paths = latest_project_file_paths_payload(project, receipts)
    add(
        latest_project_file_paths.get("latest_project_file"),
        role="project_file",
        label="Latest saved project",
        reason="Packaged project state from the latest workbench save.",
    )
    add(
        latest_project_file_paths.get("latest_project_file_write"),
        role="receipt",
        label="Latest project file",
        reason="Most recent saved history for the saved project file.",
    )

    for source in source_list.get("sources") or []:
        if isinstance(source, dict):
            label = str(source.get("relative_raw_path") or PurePosixPath(str(source.get("path") or "")).name or "Source")
            add(source.get("path"), role="source", label=label, reason=str(source.get("source_type") or "source file"))
    if not source_list.get("sources"):
        raw_dir = project_root / "raw"
        if raw_dir.exists():
            for source_path in sorted(path for path in raw_dir.iterdir() if path.is_file())[:40]:
                label = source_path.name
                if label == "source_type_map.json":
                    continue
                add(repo_rel(source_path), role="source", label=label, reason="Project raw source file.")

    for key, label in [
        ("compile_provenance", "Evidence provenance"),
        ("compiled_packet", "Compiled evidence"),
        ("compiled_evidence", "Compiled evidence"),
        ("replay_manifest", "Evidence replay manifest"),
        ("source_index", "Source index"),
        ("source_receipt", "File-index history"),
    ]:
        add(evidence_readiness.get(key), role="evidence", label=label, reason="Evidence readiness backing file.")

    thesis_support_state = thesis_support if isinstance(thesis_support, dict) else {}
    for key, label in [
        ("evidence_support_file_path", "Thesis support"),
        ("evidence_file_path", "Evidence file"),
        ("source_index_path", "Source index"),
    ]:
        add(thesis_support_state.get(key), role="evidence", label=label, reason="Thesis support backing file.")

    add(evidence_gap_recovery.get("file"), role="evidence_gap", label="Active evidence gaps", reason="Current gaps to fetch or justify.")
    for gap in evidence_gap_recovery.get("gaps") or []:
        if not isinstance(gap, dict):
            continue
        required_surface = str(gap.get("required_surface") or "")
        surface_path = evidence_gap_required_surface_path(project, required_surface)
        if surface_path:
            add(
                surface_path,
                role="evidence_gap",
                label="Needed evidence",
                reason=(
                    f"Needed to resolve the active gap for {gap.get('target') or 'this project'}."
                ),
            )

    for key, path in (run_history.get("paths") or {}).items():
        add(path, role="run", label=display_text(key), reason="Run history or run result backing file.")
    for run in run_history.get("recent_runs") or []:
        if isinstance(run, dict):
            for path in run.get("artifact_refs") or []:
                artifact_kind = file_preview_kind(str(path or ""))
                if artifact_kind == "axioms_constraints":
                    add(
                        path,
                        role="axiom",
                        label="Run-learned assumptions",
                        reason="Generated by a recent run; inspect before relying on the constraint.",
                    )
                else:
                    add(path, role="run", label="Run file", reason="Referenced by a recent run.")

    add(report.get("report_support_contract"), role="report", label="Report readiness", reason="Current readiness file for the report.")
    renderer = str(report.get("renderer") or snapshot.DEFAULT_RENDERER or "decision_brief").strip()
    add(
        f"projects/{project}/Report.{renderer}.md",
        role="report",
        label="Decision report",
        reason="Current rendered decision report when one has been generated.",
    )
    add(
        f"projects/{project}/synthesis/claim_card.md",
        role="report",
        label="Claim card",
        reason="Portable claim card when one has been generated.",
    )
    for backing in report.get("backing_files") or []:
        if isinstance(backing, dict):
            add(backing.get("path"), role="report", label=str(backing.get("label") or "Report backing file"), reason="Report readiness backing file.")

    research_paths = research_map_paths(project)
    add(research_paths["markdown"], role="research_map", label="Research map", reason="Portable Markdown map for GitHub and Obsidian.")
    add(research_paths["json"], role="research_map", label="Research map data", reason="Structured project map rendered by the workbench.")

    for path in (axiom_state.get("backing_files") or []):
        add(path, role="axiom", label="Run-learned axiom backing file", reason="Backs run-learned axioms or derived constraints.")

    formalization_state = formalization_state if isinstance(formalization_state, dict) else project_formalization_payload(project)
    for file_row in formalization_state.get("files") or []:
        if isinstance(file_row, dict):
            add(
                file_row.get("path"),
                role="formalization",
                label=str(file_row.get("name") or "Formal work"),
                reason="Project-local LeanMill target, research note, saved history, or Lean file.",
            )

    for key, path in (receipts.get("paths") or {}).items():
        add(path, role="receipt", label=display_text(key), reason="Workbench saved-history file.")
    for receipt in receipts.get("receipts") or []:
        if isinstance(receipt, dict):
            add(receipt.get("path"), role="receipt", label=display_text(receipt.get("display_kind") or receipt.get("kind") or "Saved work"), reason=display_text(receipt.get("display_summary") or "Recent saved work."))
            add(receipt.get("manifest_path"), role="receipt", label="Saved-work manifest", reason="Manifest named by recent saved work.")

    items.sort(
        key=lambda item: (
            safe_int(item.get("role_order")),
            safe_int(item.get("priority")),
            0 if item.get("exists") else 1,
            str(item.get("label") or ""),
            str(item.get("path") or ""),
        )
    )

    role_counts: dict[str, int] = {}
    previewable_count = 0
    missing_count = 0
    for item in items:
        role = str(item.get("role") or "project_file")
        role_counts[role] = role_counts.get(role, 0) + 1
        previewable_count += 1 if item.get("previewable") else 0
        missing_count += 0 if item.get("exists") else 1

    return {
        "schema": "ztare-project-file-inventory-v1",
        "project": project,
        **latest_project_file_paths,
        "item_count": len(items),
        "visible_count": min(len(items), limit),
        "previewable_count": previewable_count,
        "missing_count": missing_count,
        "role_counts": role_counts,
        "file_groups": project_file_groups_payload(items),
        "items": items[:limit],
    }


def research_map_paths(project: str) -> dict[str, str]:
    paths = research_map_core.map_paths(project, root=snapshot.REPO)
    return {key: repo_rel(path) for key, path in paths.items()}


def markdown_repo_link(path: str, label: str | None = None) -> str:
    clean = PurePosixPath(str(path or "").strip()).as_posix()
    if not clean or "<" in clean or ">" in clean:
        return ""
    return f"[{label or PurePosixPath(clean).name}]({clean})"


def research_map_file_refs(*paths: str) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    seen: set[str] = set()
    for path in paths:
        clean = PurePosixPath(str(path or "").strip()).as_posix()
        if not clean or clean in seen or not preview_path_allowed(clean):
            continue
        seen.add(clean)
        refs.append({"path": clean, "label": PurePosixPath(clean).name})
    return refs


def research_map_status(value: dict[str, Any], *, default: str = "not loaded") -> str:
    if not isinstance(value, dict):
        return default
    return str(value.get("status") or value.get("display_status") or default)


def research_map_packet(*paths: str) -> dict[str, Any]:
    for path in paths:
        clean = PurePosixPath(str(path or "").strip()).as_posix()
        if not clean or not preview_path_allowed(clean):
            continue
        try:
            payload = read_optional_json_object(WORKBENCH_STORE.resolve(clean))
        except (OSError, ValueError):
            payload = {}
        if payload:
            payload["_path"] = clean
            return payload
    return {}


def research_map_text(row: Any) -> str:
    if isinstance(row, dict):
        return str(
            row.get("claim")
            or row.get("unknown")
            or row.get("text")
            or row.get("topic")
            or row.get("summary")
            or row.get("why_it_matters")
            or ""
        ).strip()
    return str(row or "").strip()


def project_research_map_payload(project_state: dict[str, Any], *, trace: dict[str, Any] | None = None) -> dict[str, Any]:
    project = snapshot.validate_project_slug(str(project_state.get("project") or snapshot.DEFAULT_PROJECT))
    paths = research_map_paths(project)
    trace = trace if isinstance(trace, dict) else {}
    thesis = project_state.get("thesis") if isinstance(project_state.get("thesis"), dict) else {}
    change_test = project_state.get("change_test") if isinstance(project_state.get("change_test"), dict) else {}
    charter = project_state.get("charter") if isinstance(project_state.get("charter"), dict) else {}
    assumptions = project_state.get("assumptions") if isinstance(project_state.get("assumptions"), dict) else {}
    evidence = project_state.get("evidence") if isinstance(project_state.get("evidence"), dict) else {}
    thesis_support = project_state.get("thesis_support") if isinstance(project_state.get("thesis_support"), dict) else {}
    source_health = project_state.get("source_health") if isinstance(project_state.get("source_health"), dict) else {}
    run = project_state.get("run") if isinstance(project_state.get("run"), dict) else {}
    report = project_state.get("report") if isinstance(project_state.get("report"), dict) else {}
    review = project_state.get("review") if isinstance(project_state.get("review"), dict) else {}
    recent = project_state.get("recent_changes") if isinstance(project_state.get("recent_changes"), dict) else {}
    next_action = project_state.get("next_action") if isinstance(project_state.get("next_action"), dict) else {}
    formalization = project_state.get("formalization") if isinstance(project_state.get("formalization"), dict) else {}
    graph_summaries = [
        row for row in trace.get("graph_carriers", []) if isinstance(row, dict)
    ][:4]
    project_artifacts = project_source_artifacts(project, limit=8)
    packet = research_map_packet(
        str(thesis_support.get("evidence_support_file_path") or ""),
        str(evidence.get("file") or ""),
        f"projects/{project}/compiled_evidence_packet.json",
    )
    non_claims = [str(item).strip() for item in assumptions.get("non_claims") or [] if str(item).strip()]
    supported_points = [row for row in thesis_support.get("supported_points") or [] if isinstance(row, dict)]
    weak_points = [row for row in thesis_support.get("weak_or_open_points") or [] if isinstance(row, dict)]
    derived_constraints = [
        row for row in (project_state.get("axioms") or {}).get("derived_constraints", [])
        if isinstance(row, dict)
    ]
    contradictions = [
        row for row in packet.get("identified_contradictions", [])
        if isinstance(row, dict)
    ]
    candidate_claims = [
        row for row in packet.get("candidate_claims_to_test", [])
        if isinstance(row, dict)
    ]
    epistemic_voids = [
        row for row in packet.get("epistemic_voids", [])
        if isinstance(row, dict)
    ]
    report_reasons = [str(item).strip() for item in report.get("support_reasons") or [] if str(item).strip()]
    source_warnings = [
        str(row.get("summary") or row.get("display_issue_type") or row.get("issue_type") or "").strip()
        for row in source_health.get("issues") or []
        if isinstance(row, dict)
    ]
    tension_rows = [
        *[research_map_text(row) for row in contradictions],
        *[research_map_text(row) for row in weak_points],
        *report_reasons,
        *source_warnings,
        *[str(row.get("text") or "").strip() for row in derived_constraints[:3] if str(row.get("text") or "").strip()],
    ]
    branch_rows = [
        *[research_map_text(row) for row in candidate_claims],
        *[research_map_text(row) for row in epistemic_voids],
        str(next_action.get("detail") or next_action.get("label") or "").strip(),
    ]
    support_summary = (
        f"{safe_int(thesis_support.get('supported_count'))} supported point(s) across "
        f"{safe_int(thesis_support.get('source_count'))} source file(s)."
        if thesis_support
        else str(evidence.get("summary") or "No support summary loaded.")
    )
    tension_count = len([row for row in tension_rows if row])
    branch_count = len([row for row in branch_rows if row])
    file_refs = research_map_file_refs(
        str(charter.get("file") or ""),
        str(thesis.get("file") or ""),
        str(change_test.get("file") or ""),
        str(evidence.get("file") or ""),
        str(evidence.get("gap_file") or ""),
        str(packet.get("_path") or ""),
        f"projects/{project}/workspace/contradictions.md",
        str(report.get("contract") or ""),
        str(formalization.get("preferred_root") or ""),
    )
    graph_refs = research_map_file_refs(
        *[
            str(ref)
            for row in graph_summaries
            for ref in (row.get("source_artifacts") or row.get("artifact_refs") or [])
            if ref
        ]
    )
    artifact_details = [
        " - ".join(
            part
            for part in [
                str(row.get("path") or ""),
                display_value(row.get("artifact_kind") or "project_note"),
                f"created by {row.get('created_by')}" if row.get("created_by") else "",
            ]
            if part
        )
        for row in project_artifacts
    ]
    sections = [
        {
            "id": "orientation",
            "label": "Orientation",
            "status": "bounded" if thesis.get("text") and change_test.get("text") else "needs setup",
            "summary": str(thesis.get("text") or "No thesis loaded."),
            "details": [
                str(change_test.get("text") or ""),
                *[f"Not claiming: {item}" for item in non_claims[:4]],
            ],
            "files": research_map_file_refs(str(charter.get("file") or ""), str(thesis.get("file") or ""), str(change_test.get("file") or "")),
        },
        {
            "id": "project_work",
            "label": "Project work",
            "status": "loaded" if project_artifacts else "not loaded",
            "summary": (
                f"{len(project_artifacts)} project file(s) carry work-kind metadata from notes, agents, notebooks, reports, proof work, or raw evidence."
                if project_artifacts
                else "No project-work metadata loaded from raw files yet."
            ),
            "details": artifact_details,
            "files": research_map_file_refs(*[str(row.get("path") or "") for row in project_artifacts]),
        },
        {
            "id": "strongest_support",
            "label": "Strongest support",
            "status": research_map_status(thesis_support, default=research_map_status(evidence)),
            "summary": support_summary,
            "details": [research_map_text(row) for row in supported_points[:4] if research_map_text(row)],
            "files": research_map_file_refs(str(evidence.get("file") or ""), str(thesis_support.get("evidence_support_file_path") or ""), str(thesis_support.get("source_index_path") or "")),
        },
        {
            "id": "tensions",
            "label": "Tensions",
            "status": "needs review" if tension_count else "quiet",
            "summary": f"{tension_count} tension(s): source conflicts, weak support, caveats, or report limits.",
            "details": [row for row in tension_rows if row][:8],
            "files": research_map_file_refs(str(packet.get("_path") or ""), f"projects/{project}/workspace/contradictions.md", str(evidence.get("gap_file") or ""), str(source_health.get("source_path") or ""), str(report.get("contract") or "")),
        },
        {
            "id": "branches",
            "label": "Branches to test",
            "status": "actionable" if branch_count else "not loaded",
            "summary": str(next_action.get("detail") or next_action.get("label") or "No next action loaded."),
            "details": [row for row in branch_rows if row][:7],
            "files": research_map_file_refs(str(packet.get("_path") or ""), str(report.get("contract") or "")),
        },
        {
            "id": "run_lessons",
            "label": "Run lessons",
            "status": research_map_status(run),
            "summary": str(run.get("latest_weakest_point") or run.get("summary") or "No run history loaded."),
            "details": [
                str(run.get("compression_progress_summary") or ""),
                *[str(row.get("text") or "").strip() for row in derived_constraints[:5] if str(row.get("text") or "").strip()],
            ],
            "files": research_map_file_refs(*[str(path) for path in (project_state.get("axioms") or {}).get("backing_files", []) if path]),
        },
        {
            "id": "synthesis",
            "label": "Synthesis",
            "status": research_map_status(report),
            "summary": str(report.get("summary") or "No report readiness loaded."),
            "details": [
                *report_reasons,
                str(recent.get("summary") or ""),
            ],
            "files": research_map_file_refs(str(report.get("contract") or ""), str(review.get("latest_receipt") or "")),
        },
        {
            "id": "handoffs",
            "label": "Handoffs",
            "status": "loaded" if graph_summaries or formalization.get("status") else "not loaded",
            "summary": (
                f"{formalization.get('summary') or 'No formal work loaded.'} "
                f"{len(graph_summaries)} graph summar{'y' if len(graph_summaries) == 1 else 'ies'} available."
            ),
            "details": [
                *[str(row.get("summary") or row.get("graph_kind") or "").strip() for row in graph_summaries if str(row.get("summary") or row.get("graph_kind") or "").strip()],
            ],
            "files": research_map_file_refs(str(formalization.get("preferred_root") or ""), *[ref["path"] for ref in graph_refs]),
        },
    ]
    nodes = [{"id": row["id"], "label": row["label"], "status": row["status"]} for row in sections]
    edges = [
        {"from": "orientation", "to": "project_work", "relation": "organized into"},
        {"from": "project_work", "to": "strongest_support", "relation": "may support"},
        {"from": "strongest_support", "to": "tensions", "relation": "limited by"},
        {"from": "tensions", "to": "branches", "relation": "selects"},
        {"from": "branches", "to": "run_lessons", "relation": "updates"},
        {"from": "run_lessons", "to": "synthesis", "relation": "constrains"},
        {"from": "synthesis", "to": "handoffs", "relation": "can hand off to"},
    ]
    lines = [
        f"# Research map: {project}",
        "",
        f"- **Thesis:** {str(thesis.get('text') or 'No thesis loaded.')}",
        f"- **What would change it:** {str(change_test.get('text') or 'No change test loaded.')}",
        f"- **Scope limits (not claiming):** {len(non_claims)}",
        f"- **Tensions to resolve:** {tension_count}",
        f"- **Next action:** {str(next_action.get('label') or 'No next action loaded.')}",
        "",
    ]
    for section in sections:
        lines.extend([f"## {section['label']}", "", f"Status: {section['status']}", "", str(section["summary"] or ""), ""])
        details = [str(item).strip() for item in section.get("details") or [] if str(item).strip()]
        if details:
            lines.extend(["Key points:", *[f"- {item}" for item in details[:8]], ""])
        links = [markdown_repo_link(ref["path"], ref["label"]) for ref in section.get("files") or []]
        links = [link for link in links if link]
        if links:
            lines.extend(["Files:", *[f"- {link}" for link in links], ""])
    markdown = "\n".join(lines).rstrip() + "\n"
    payload = {
        "schema": RESEARCH_MAP_SCHEMA,
        "project": project,
        "rubric": str(project_state.get("rubric") or ""),
        "intake": str(project_state.get("intake") or ""),
        "status": "ready",
        "summary": (
            f"{tension_count} tension(s), {branch_count} branch(es), "
            f"{safe_int(thesis_support.get('supported_count'))} supported point(s), "
            f"{len(project_artifacts)} project work file(s); next action: {next_action.get('label') or 'not loaded'}."
        ),
        "target_path": paths["markdown"],
        "json_path": paths["json"],
        "ledger_path": paths["ledger"],
        "latest_path": paths["latest"],
        "sections": sections,
        "nodes": nodes,
        "edges": edges,
        "file_refs": file_refs,
        "graph_refs": graph_refs,
        "graph_summary_count": len(graph_summaries),
        "next_action": {
            "label": str(next_action.get("label") or ""),
            "detail": str(next_action.get("detail") or ""),
            "workspace": str(next_action.get("workspace") or ""),
            "subsection": str(next_action.get("subsection") or ""),
        },
        "markdown": markdown,
        "write_boundary": write_boundary_payload(
            writes_project_files=True,
            write_paths=[paths["markdown"], paths["json"], paths["ledger"], paths["latest"]],
            receipt_path=paths["ledger"],
            latest_path=paths["latest"],
            read_only_actions=["preview research map", "copy markdown"],
            no_change_boundary="Previewing the research map writes no files. Saving writes only the project research-map files and saved history.",
        ),
    }
    return research_map_core.enrich_research_map_payload(payload)


def project_intake_target_path(project: str, intake: str | None = None, *, allow_examples: bool = False) -> Path:
    project = snapshot.validate_project_slug(project)
    intake_path = intake or snapshot.default_intake_for_project(project)
    candidate = Path(intake_path)
    if candidate.is_absolute():
        raise ValueError("project-brief path must be relative to the repository")
    resolved = (snapshot.REPO / candidate).resolve()
    project_root = (snapshot.REPO / "projects" / project).resolve()
    examples_root = (snapshot.REPO / "examples" / "project_packets").resolve()
    if not path_under(resolved, project_root):
        if not allow_examples or not path_under(resolved, examples_root):
            raise ValueError("project-brief path must stay inside the selected project")
    return resolved


def project_intake_path(project: str, intake: str | None = None, *, allow_examples: bool = False) -> Path:
    intake_path = intake or snapshot.default_intake_for_project(project)
    resolved = project_intake_target_path(project, intake, allow_examples=allow_examples)
    if not resolved.exists():
        raise FileNotFoundError(f"project-brief path does not exist: {intake_path}")
    if not resolved.is_file():
        raise ValueError(f"project-brief path is not a file: {intake_path}")
    return resolved


def read_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(WORKBENCH_STORE.read_text(path))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object")
    return payload


def capability_display_label(row: dict[str, Any]) -> str:
    row_id = str(row.get("id") or "")
    labels = {
        "claim_boundary_compiler": "Project claim boundaries",
        "source_evidence_compiler": "Files and evidence",
        "run_readiness_compiler": "Ready to run",
        "expression_grammar_compiler": "Expression rules",
        "run_result_compiler": "Run results",
        "compression_progress_compiler": "Compression progress",
        "report_support_compiler": "Report readiness",
        "review_history_compiler": "Reviews and saved history",
        "gaming_evaluator_compiler": "Evaluator hardening",
        "reflexive_advisory_compiler": "Warnings and next moves",
        "primitive_compiler": "Reusable reasoning tools",
        "repository_memory_compiler": "Repository memory",
    }
    if row_id in labels:
        return labels[row_id]
    label = str(row.get("label") or "Project test").strip()
    return re.sub(r"\s+compiler$", "", label, flags=re.IGNORECASE) or "Project test"


def scenario_surface_payload(project: str) -> dict[str, Any]:
    """Surface a project's assumptions by COMPOSING its compiled evidence packet (the compiler's
    candidate_claims_to_test) + the deterministic span-anchor gate — read-only, no LLM (the compiler already
    ran). The intake view of the round-trip. Returns anchored claims (each a thesis to test)."""
    return scenario_cli_payload(["surface", "--project", project, "--json"], project=project)


def scenario_reingest_payload(project: str, doc: str) -> dict[str, Any]:
    """Re-gate an AI-polished deliverable against a project's governed research map — every prose sentence must
    align to a governed element or it is flagged UNGOVERNED (fail-closed, no LLM judge). The workbench's
    forged-edit catch. Read-only: computes, writes nothing."""
    import tempfile

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".md") as staged:
        staged.write(doc or "")
        staged.flush()
        return scenario_cli_payload(["reingest", staged.name, "--project", project, "--json"],
                                    project=project)


def scenario_reingest_promote_payload(project: str, doc: str, base_hash: str,
                                      source_path: str = "") -> dict[str, Any]:
    """Promote a trace-clean rendering without laundering it into the graph.

    The client must present the base hash returned by ``scenario_reingest_payload``.  A changed governed
    state refuses the write, and the strict sentence gate is recomputed server-side immediately before the
    artifact and audit receipt are written.
    """
    import tempfile

    from ztare.common.paths import REPO_ROOT

    source_name = Path(str(source_path or "")).stem or "edited_copy"
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", source_name).strip("._-") or "edited_copy"
    out_dir = REPO_ROOT / "projects" / project / "workspace" / "deliverables"
    out_path = out_dir / f"{safe_name}.current.md"
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".md") as staged:
        staged.write(doc or "")
        staged.flush()
        return scenario_cli_payload(
            ["reingest", staged.name, "--project", project, "--promote", str(out_path),
             "--base-hash", str(base_hash or ""), "--json"], project=project)


def scenario_annotate_payload(project: str, doc: str, model: str = "") -> dict[str, Any]:
    """The annotated round-trip (a document-annotation view): a pasted document → each sentence tagged with its claim
    LIFECYCLE (backed / contradicted / surfaced-untested / inert) against the project's governed map. A doc is
    INPUT — it never 'fails'; the headline is the load-bearing-assumption COUNT. Spans come from the doc via the
    live proposer when `model` is set, else read-only by composing the project's compiled packet claims (gated
    against this doc). Deterministic annotate; surfacing degrades to []-spans if no LLM/packet."""
    if not (doc or "").strip():
        return {"ok": False, "error": "empty document"}
    import tempfile

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".md") as staged:
        staged.write(doc or "")
        staged.flush()
        args = ["annotate", staged.name, "--project", project, "--json"]
        if model:
            args.extend(["--model", model])
        return scenario_cli_payload(args, project=project, timeout=180 if model else 30)


def scenarios_payload() -> dict[str, Any]:
    """Read-only scenario index for the workbench picker: name + description + resolved rubric / evidence /
    renderer per scenario. Best-effort per row — a broken manifest is flagged, never breaks the endpoint."""
    return scenario_cli_payload(["list", "--json"])


def scenario_baseline_status_payload(project: str) -> dict[str, Any]:
    """Read the saved comparison reference without writing a new one."""
    return scenario_cli_payload(["baseline", "--project", project, "--status", "--json"], project=project)


def scenario_baseline_payload(project: str) -> dict[str, Any]:
    """Snapshot the project's governed state as a DECISION BASELINE (the frozen argument at decision time) so it
    can be recompiled against later. Read-of-map + write-of-snapshot; no LLM."""
    return scenario_cli_payload(["baseline", "--project", project, "--json"], project=project)


def scenario_recompile_payload(project: str) -> dict[str, Any]:
    """The stale-decision diff (incremental recompile): recompile the CURRENT governed map against the stored
    baseline — did the decision go stale, which claims flipped, what to test next. Deterministic, no LLM."""
    return scenario_cli_payload(["recompile", "--project", project, "--json"], project=project)


def scenario_recheck_payload(project: str, now: str = "", half_life_days: "int | None" = None) -> dict[str, Any]:
    """Re-earn / demote / expire the project's re-executable (W1) warrants by re-running each bound recheck
    capability (e.g. a covenant recompute). Writes the recheck-owned overlay slice; returns the receipts + the
    fresh strength status/profile so the panel can show the profile MOVE. Deterministic, no LLM. Parity with
    `ztare scenario recheck`."""
    args = ["recheck", "--project", project, "--json"]
    if now:
        args.extend(["--now", now])
    if half_life_days is not None:
        args.extend(["--half-life-days", str(half_life_days)])
    return scenario_cli_payload(args, project=project, timeout=120)


def scenario_rice_payload(request: dict[str, Any]) -> dict[str, Any]:
    """Governed RICE — Reach x Impact x Confidence / Effort where Confidence is READ from backing strength, never
    typed, and each row names its weakest-backed factor. POST `{items:[{project,label,reach,impact,effort}]}` for
    a portfolio (each item its own decision; Confidence = its thesis strength), or `{project: slug}` to rank the
    claims inside one decision. Deterministic, no LLM. Parity with `ztare scenario rice`."""
    items = request.get("items")
    if isinstance(items, list) and items:
        return scenario_cli_payload(["rice", "--items-json", json.dumps(items, separators=(",", ":")), "--json"])
    project = str(request.get("project") or "")
    if not project:
        return {"ok": False, "error": "provide items[] (a portfolio) or a project slug"}
    return scenario_cli_payload(["rice", "--project", project, "--json"], project=project)


def scenario_rice_update_payload(request: dict[str, Any]) -> dict[str, Any]:
    """Persist bounded PM prioritization inputs; warrants are recomputed from the governed graph on read."""
    project = str(request.get("project") or "").strip()
    claim_id = str(request.get("claim_id") or "").strip()
    factors = request.get("factors") if isinstance(request.get("factors"), dict) else {}
    if not project or not claim_id:
        return {"ok": False, "error": "choose a project and initiative"}
    update = json.dumps({"claim_id": claim_id, "factors": factors}, separators=(",", ":"))
    return scenario_cli_payload(["rice", "--project", project, "--update-json", update, "--json"],
                                project=project)


def scenario_next_agenda_payload(project: str) -> dict[str, Any]:
    """The unified 'what to test next' agenda (implicit + declared + loop, Pareto frontier). Parity with the CLI
    `scenario agenda` next-test list. Deterministic, no LLM."""
    return scenario_cli_payload(["agenda", "--project", project, "--json"], project=project)


def scenario_deliverables_payload(project: str, declared: "list[str] | None" = None,
                                  scenario: str = "") -> dict[str, Any]:
    """The compose-vs-loop deliverable gap map: for each REQUIRED deliverable, can it be composed from the
    current governed state now, or does it need the loop / a template? Read-only, no LLM. (See
    `production.deliverable_gaps`.) A user adds a required deliverable via /api/scenario-deliverable-add."""
    args = ["deliverables", "--project", project, "--json"]
    if scenario:
        args.extend(["--scenario", scenario])
    if declared:
        args.extend(["--declared", ",".join(str(name) for name in declared if str(name).strip())])
    return scenario_cli_payload(args, project=project)


def scenario_deliverable_add_payload(project: str, name: str, scenario: str = "") -> dict[str, Any]:
    """Add a required deliverable to a project (the 'add a required deliverable to an existing project' action);
    persists to workspace/required_deliverables.json and returns the fresh gap map so the user sees immediately
    whether it composes now or needs the loop."""
    args = ["deliverables", "--project", project, "--add", str(name or "").strip(), "--json"]
    if scenario:
        args.extend(["--scenario", scenario])
    return scenario_cli_payload(args, project=project)


def scenario_deliverable_generate_payload(project: str, name: str, scenario: str = "") -> dict[str, Any]:
    """Generate ONE required deliverable WITH PERMISSION: compose it from the governed state now if it composes
    (no loop, never fabricated), else report that it needs the loop / a template. Writes only a composable,
    firewall-passing artifact to workspace/deliverables/. Never ships ungoverned prose."""
    args = ["deliverables", "--project", project, "--generate", name, "--json"]
    if scenario:
        args.extend(["--scenario", scenario])
    return scenario_cli_payload(args, project=project, timeout=120)


def scenario_deliverable_editorial_payload(project: str, name: str, scenario: str = "") -> dict[str, Any]:
    """Shape one checked draft for its audience through the scenario CLI contract."""
    args = ["deliverables", "--project", project, "--editorial", name, "--json"]
    if scenario:
        args.extend(["--scenario", scenario])
    return scenario_cli_payload(args, project=project, timeout=180)


def scenario_agenda_payload(project: str) -> dict[str, Any]:
    """The argument-kernel analysis for a project's governed map — grounded verdict, minimal cores, dominators,
    warrant ceiling, and the test agenda. Workbench parity with `ztare scenario agenda`."""
    return scenario_cli_payload(["agenda", "--project", project, "--json"], project=project)


def scenario_preview_payload(name: str) -> dict[str, Any]:
    """The authoring mirror: what a scenario BINDS (rubric, run config, gate package, capabilities) plus its
    rubric EFFECT (judge dimensions + persona) — the same wiring a real run honors, surfaced before a run so an
    author can see the effect first. Thin wrapper over the resolver's pure `scenario_effect`; no LLM, no run."""
    return scenario_cli_payload(["show", name, "--effect", "--json"])


def scenario_attribution_payload(project: str) -> dict[str, Any]:
    """The authoring mirror's other half: what scenario/rubric actually drove a project's PAST run and its
    score trend — read straight off existing run artifacts, nothing recomputed or fabricated. Thin wrapper over
    the pure `scenario_attribution`."""
    return scenario_cli_payload(["attribution", "--project", project, "--json"], project=project)


def scenario_provenance_payload(project: str) -> dict[str, Any]:
    """The anti-cherry-pick teeth, surfaced: per currently-declared deliverable, whether it was PRE-REGISTERED
    (pinned at a run-start, with the earliest run) or ADDED LATER — a COMPUTED fact off the append-only receipt,
    never self-reported — plus the input-contract drift (charter changed / deliverables added since the last pin)."""
    return scenario_cli_payload(["deliverables", "--project", project, "--provenance", "--json"],
                                project=project)


def scenario_map_query_payload(project: str, question: str) -> dict[str, Any]:
    """No-LLM natural-language query over the research map's SPO triples (PRD §7.6): maps the question's keywords
    to the graph's relation vocabulary + an anchor node and traverses the edges — deterministic, zero model cost.
    Thin wrapper over `research_graph_query.query_graph` on the built carrier. Surfaces the CLI (`ztare research
    map-query`) into the workbench Ask box the spec described but never wired."""
    if not str(question or "").strip():
        return {"ok": False, "error": "ask a question about the map"}
    return ztare_cli_payload(
        ["research", "map-query", "--project", project, "--q", str(question).strip(), "--json"],
        project=project)


def scenario_produce_all_payload(project: str, scenario: str = "") -> dict[str, Any]:
    """Produce the FULL declared set at once so the set-completeness firewall actually FIRES (the per-deliverable
    generate button passes a singleton and can never catch a silent drop). The declared set is the PINNED set when
    a run-start receipt exists, else the current resolved set. Never fabricates — a deliverable that can't compose
    is written as an accounted stub."""
    args = ["deliverables", "--project", project, "--produce-all", "--json"]
    if scenario:
        args.extend(["--scenario", scenario])
    return scenario_cli_payload(args, project=project, timeout=120)


def charter_lint_payload(project: str) -> dict[str, Any]:
    """What the KERNEL parses out of this project's charter — the machine contracts the loop enforces (forecast
    type, anchor proxies, asymptotic claim) — and what did NOT parse. An IDE-lint over the prose blob (Fable's
    C-as-lint): the charter stays free prose; this shows what actually lands, without a form fighting the loop's
    own writes to the charter."""
    from ztare.common.paths import PROJECTS_DIR
    from ztare.validator.core.charter_parsing import (
        extract_anchor_proxies_from_charter,
        extract_asymptotic_claim_contract_from_charter,
        extract_forecast_type_from_charter,
    )

    charter = PROJECTS_DIR / project / "project_charter.md"
    if not charter.is_file():
        return {"ok": True, "project": project, "has_charter": False, "contracts": []}
    text = charter.read_text(encoding="utf-8")
    forecast = extract_forecast_type_from_charter(text)
    proxies = extract_anchor_proxies_from_charter(text)
    asymptotic = extract_asymptotic_claim_contract_from_charter(text)
    asy_claim = getattr(asymptotic, "asymptotic_claim", None)
    asy_tail = getattr(asymptotic, "farther_tail_contract", None)
    contracts = [
        {"name": "Forecast type", "parsed": bool(forecast),
         "value": forecast or "(not declared — defaults apply)",
         "enforces": "whether bounded-tilt vs point-% claims are in bounds"},
        {"name": "Anchor proxies", "parsed": bool(proxies),
         "value": ", ".join(proxies) if proxies else "(none — no mathematical drift detection)",
         "enforces": "drift detection against these proxies"},
        {"name": "Asymptotic claim", "parsed": bool(asy_claim or asy_tail),
         "value": (f"asymptotic_claim={asy_claim}, farther_tail={asy_tail}" if (asy_claim or asy_tail)
                   else "(not declared)"),
         "enforces": "the asymptotic-behavior contract the scorer checks"},
    ]
    return {"ok": True, "project": project, "has_charter": True, "contracts": contracts}


def ztare_cli_payload(args: list[str], *, project: str = "", timeout: int = 30) -> dict[str, Any]:
    """Run one top-level CLI JSON contract. The HTTP server owns transport only."""
    command = [SERVER_PYTHON, "-m", "src.ztare.cli", *args]
    # Code and project data are separate concerns. Tests and remote deployments may
    # point the data root elsewhere; the CLI must still resolve from this checkout.
    proc = run_workbench_command(command, timeout=timeout, cwd=_WORKBENCH_REPO)
    stdout = (proc.stdout or "").strip()
    if stdout:
        try:
            payload = json.loads(stdout)
            if isinstance(payload, dict):
                return payload
        except json.JSONDecodeError:
            pass
    return {"ok": False, "project": project,
            "error": (proc.stderr or stdout or "ZTARE CLI returned no JSON")[:500]}


def scenario_cli_payload(args: list[str], *, project: str = "", timeout: int = 30) -> dict[str, Any]:
    """Run one scenario CLI JSON contract through the shared transport."""
    return ztare_cli_payload(["scenario", *args], project=project, timeout=timeout)


def scenario_strength_payload(project: str) -> dict[str, Any]:
    """The graded DECISION read — strength profile + status, what it rests on (Shapley), independent
    corroboration per warrant tier, hard cruxes, and the challenge queue by drag. Workbench parity with
    `ztare scenario strength`. CLI-first (never a direct kernel-file read), mirroring `research_graph_payload`."""
    return scenario_cli_payload(
        ["strength", "--project", project, "--json", "--snapshot"], project=project)


def scenario_bind_payload(request: dict[str, Any]) -> dict[str, Any]:
    """Bind an excerpt from an indexed project source to a claim. Source bytes are loaded and hashed server-side;
    a caller cannot certify text it supplied in the same request. Exact claim text earns W2. A quote that merely
    appears relevant is preserved as W3 until an inference admission checks that connective. No LLM."""
    import tempfile

    project = str(request.get("project") or "").strip()
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json") as staged:
        json.dump(request, staged)
        staged.flush()
        return scenario_cli_payload(["bind", "--spec", staged.name, "--json"], project=project)


def scenario_wagers_payload(project: str) -> dict[str, Any]:
    """The project's WAGERS — protected thin-evidence bets on a BLOCKED claim, ranked by what would settle the
    decision (info-yield, then cost). Also returns the BLOCKED claims (candidates for a new wager) and any
    inadmissible bets with the reason. Workbench parity with `ztare scenario wager list`. Read-only, no LLM."""
    return scenario_cli_payload(["wager", "list", "--project", project, "--json"], project=project)


def scenario_wager_register_payload(project: str, wager: dict[str, Any]) -> dict[str, Any]:
    """Register a wager (declared JSON from the workbench form). The kernel simulates every outcome; a wager is
    persisted ONLY if admissible (a real test that moves the decision). Returns the receipt either way."""
    return scenario_cli_payload(
        ["wager", "add", "--project", project, "--spec-json", json.dumps(wager or {}), "--json"],
        project=project)


def scenario_wager_expire_payload(project: str, now: str = "") -> dict[str, Any]:
    """Sweep: any open wager past its deadline auto-expires to the ordinary BLOCKED backlog (anti-laundering)."""
    args = ["wager", "expire", "--project", project, "--json"]
    if now:
        args.extend(["--now", now])
    payload = scenario_cli_payload(args, project=project)
    if payload.get("ok") and "now" not in payload:
        payload["now"] = now
    return payload


def scenario_wager_execute_payload(request: dict[str, Any]) -> dict[str, Any]:
    """Preview or execute one declared wager outcome. Writes require an explicit confirmed=true boundary."""
    project = str(request.get("project") or "").strip()
    wager_id = str(request.get("wager_id") or request.get("id") or "").strip()
    outcome_id = str(request.get("outcome_id") or request.get("outcome") or "").strip()
    if not (project and wager_id and outcome_id):
        return {"ok": False, "error": "choose a project, wager, and observed outcome"}
    action = "execute" if bool(request.get("confirmed", False)) else "preview"
    return scenario_cli_payload(
        ["wager", action, "--project", project, "--id", wager_id, "--outcome", outcome_id, "--json"],
        project=project)


def scenario_brief_payload(project: str) -> dict[str, Any]:
    """Return the CLI-owned governed brief; the server is transport, never a second kernel caller."""
    if not str(project or "").strip():
        return {"ok": False, "error": "choose a project"}
    project = str(project).strip()
    return scenario_cli_payload(["brief", "--project", project, "--json"], project=project)


def plugins_payload() -> dict[str, Any]:
    """Everything installed across the three plugin kinds — SCENARIOS (yaml), RUBRICS (json), CAPABILITIES
    (@capability code incl. plugin dirs). The workbench plugin manager reads this; install/reload update it."""
    return scenario_cli_payload(["plugins", "--json"])


def install_plugin_payload(kind: str, name: str, spec: "dict[str, Any]", *, overwrite: bool = False) -> dict[str, Any]:
    """Install a DATA plugin from the UI — a scenario (yaml) or a rubric (json) — validated then written to its
    filesystem registry, then discovery reloaded so it's live. Local-first: the name is slug-sanitized (no path
    traversal) and the content is validated before write. Code plugins are NOT installed via web form (arbitrary
    code) — they drop into a plugin dir + reload."""
    import tempfile

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json") as staged:
        json.dump(spec, staged)
        staged.flush()
        args = ["plugins", "--install", kind, "--name", name, "--spec", staged.name, "--json"]
        if overwrite:
            args.append("--overwrite")
        return scenario_cli_payload(args, timeout=60)


def plugin_detail_payload(kind: str, name: str) -> dict[str, Any]:
    """The current spec of an installed DATA plugin (scenario / rubric) — so the UI can open it in an edit modal
    pre-filled, then save back via /api/plugin-install (which overwrites). Read-only."""
    return scenario_cli_payload(["plugins", "--detail", kind, "--name", name, "--json"])


def plugins_reload_payload() -> dict[str, Any]:
    """Re-run capability discovery (pick up a just-dropped code plugin) and return the fresh installed set."""
    payload = scenario_cli_payload(["plugins", "--reload", "--json"])
    return {"ok": bool(payload.get("ok")), "installed": payload,
            **({"error": payload.get("error")} if not payload.get("ok") else {})}


def reasoning_capability_payload() -> dict[str, Any]:
    map_path = capability_audit.DEFAULT_MAP
    anchors_path = capability_audit.DEFAULT_RESEARCH_ANCHORS
    payload = read_json_object(map_path, repo_rel(map_path))
    anchors_payload = read_json_object(anchors_path, repo_rel(anchors_path))
    audit_report = capability_audit.audit(map_path, anchors_path)
    anchor_details: dict[str, dict[str, str]] = {}
    for anchor in anchors_payload.get("anchors") or []:
        if not isinstance(anchor, dict):
            continue
        anchor_id = str(anchor.get("id") or "").strip()
        if not anchor_id:
            continue
        sources = [source for source in anchor.get("sources") or [] if isinstance(source, dict)]
        anchor_details[anchor_id] = {
            "id": anchor_id,
            "label": display_text(anchor.get("label") or anchor_id),
            "design_lesson": display_text(anchor.get("design_lesson") or ""),
            "ztare_implication": display_text(anchor.get("ztare_implication") or ""),
            "source_count": len(sources),
            "sources": [
                {
                    "title": display_text(source.get("title") or ""),
                    "year": source.get("year"),
                    "url": str(source.get("url") or ""),
                }
                for source in sources[:3]
            ],
        }
    rows = [
        {
            "id": str(row.get("id") or ""),
            "label": str(row.get("label") or ""),
            "display_label": capability_display_label(row),
            "user_problem": display_text(row.get("user_problem") or ""),
            "input_object": display_text(row.get("input_object") or ""),
            "check_or_transform": display_text(row.get("check_or_transform") or ""),
            "output_object": display_text(row.get("output_object") or ""),
            "falsifier": display_text(row.get("falsifier") or ""),
            "workbench_requirement": display_text(row.get("workbench_requirement") or ""),
            "user_visible_proof": display_text(row.get("user_visible_proof") or ""),
            "current_boundary": display_text(row.get("current_boundary") or ""),
            "workbench_surface": display_text(row.get("workbench_surface") or ""),
            "research_anchor_ids": [str(value) for value in row.get("research_anchor_ids") or [] if str(value or "").strip()],
            "research_anchors": [
                anchor_details[str(value)]
                for value in row.get("research_anchor_ids") or []
                if str(value or "").strip() in anchor_details
            ],
            "research_anchor_labels": [
                anchor_details[str(value)]["label"]
                for value in row.get("research_anchor_ids") or []
                if str(value or "").strip() in anchor_details
            ],
            "evidence_refs": [str(value) for value in row.get("evidence_refs") or [] if str(value or "").strip()],
            "runnable_anchors": [str(value) for value in row.get("runnable_anchors") or [] if str(value or "").strip()],
        }
        for row in payload.get("capabilities") or []
        if isinstance(row, dict)
    ]
    research_anchors = audit_report.get("research_anchors") if isinstance(audit_report.get("research_anchors"), dict) else {}
    return {
        "schema": "ztare-forensic-workbench-capabilities-v1",
        "ok": bool(audit_report.get("ok")),
        "path": repo_rel(map_path),
        "research_anchors_path": repo_rel(anchors_path),
        "purpose": display_text(payload.get("purpose") or ""),
        "capability_count": len(rows),
        "capabilities": rows,
        "audit": {
            "ok": bool(audit_report.get("ok")),
            "finding_count": int(audit_report.get("finding_count") or 0),
            "failing_capability_count": int(audit_report.get("failing_capability_count") or 0),
        },
        "research_anchors": {
            "ok": bool(research_anchors.get("ok")),
            "anchor_count": int(research_anchors.get("anchor_count") or 0),
            "coverage_status": str(research_anchors.get("coverage_status") or ""),
        },
    }


def read_optional_json_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return read_json_object(path, repo_rel(path))


def read_optional_json_value(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(WORKBENCH_STORE.read_text(path))
    except json.JSONDecodeError:
        return None


def workbench_principles_payload(surface: str = "") -> dict[str, Any]:
    path = snapshot.REPO / "docs" / "evidence_atlas" / "workbench_principles.json"
    payload = read_optional_json_object(path)
    rows: list[dict[str, Any]] = []
    wanted_surface = str(surface or "").strip().lower()
    raw_rows = payload.get("principles") if isinstance(payload.get("principles"), list) else []
    for row in raw_rows:
        if not isinstance(row, dict):
            continue
        row_surface = str(row.get("surface") or "general").strip().lower() or "general"
        text = display_text(row.get("text") or "")
        if not text:
            continue
        if wanted_surface and row_surface not in {wanted_surface, "general"}:
            continue
        rows.append(
            {
                "id": str(row.get("id") or ""),
                "surface": row_surface,
                "text": text,
                "attribution": display_text(row.get("attribution") or ""),
                "source_path": str(row.get("source_path") or ""),
                "source_note": display_text(row.get("source_note") or ""),
            }
        )
    return {
        "schema": PRINCIPLE_RAIL_SCHEMA,
        "ok": bool(rows),
        "path": repo_rel(path),
        "surface": wanted_surface or "all",
        "principles": rows,
    }


def read_jsonl_objects(path: Path, *, limit: int = 100) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in WORKBENCH_STORE.read_text(path).splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows[-limit:]


def unsafe_local_ref_reason(ref: str) -> str | None:
    raw = str(ref or "").strip().replace("\\", "/")
    if not raw:
        return "empty reference"
    path = PurePosixPath(raw)
    if path.is_absolute():
        return "absolute paths are not allowed"
    if any(part in {"", ".", ".."} for part in path.parts):
        return "path traversal or empty path segment is not allowed"
    return None


def inside_any_root(path: Path, roots: list[Path]) -> bool:
    try:
        resolved = path.resolve()
    except OSError:
        return False
    for root in roots:
        try:
            resolved.relative_to(root)
            return True
        except ValueError:
            continue
    return False


def intake_ref_status(ref: str, *, key: str, index: int, intake_path: Path) -> dict[str, Any]:
    ref = str(ref or "").strip()
    row: dict[str, Any] = {
        "key": key,
        "index": index,
        "ref": ref,
        "kind": "local",
        "status": "missing",
        "previewable": False,
        "preview_path": "",
        "reason": "",
    }
    if EXTERNAL_REF_RE.match(ref):
        row.update({"kind": "external", "status": "external", "reason": "external reference"})
        return row
    unsafe_reason = unsafe_local_ref_reason(ref)
    if unsafe_reason is not None:
        row.update({"status": "unsafe", "reason": unsafe_reason})
        return row
    raw = Path(ref)
    candidates = [intake_path.parent / raw, snapshot.REPO / raw]
    roots = [intake_path.parent.resolve(), snapshot.REPO.resolve()]
    for candidate in candidates:
        if not candidate.exists():
            continue
        if not inside_any_root(candidate, roots):
            row.update({"status": "unsafe", "reason": "resolved path escapes allowed roots"})
            return row
        row.update(
            {
                "status": "present",
                "previewable": candidate.is_file(),
                "preview_path": repo_rel(candidate) if candidate.is_file() else "",
                "reason": "file found" if candidate.is_file() else "path is not a file",
            }
        )
        return row
    row.update({"reason": "local path does not exist"})
    return row


def intake_reference_status(payload: dict[str, Any], *, intake_path: Path) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for key in ("source_refs", "evidence_refs"):
        refs = [str(item) for item in payload.get(key) or []]
        groups[key] = [
            intake_ref_status(ref, key=key, index=index, intake_path=intake_path)
            for index, ref in enumerate(refs, start=1)
        ]
    rows = [row for group in groups.values() for row in group]
    return {
        "schema": "ztare-forensic-workbench-intake-ref-status-v1",
        "ok": True,
        "source_refs": groups["source_refs"],
        "evidence_refs": groups["evidence_refs"],
        "summary": {
            "total": len(rows),
            "present": sum(1 for row in rows if row["status"] == "present"),
            "missing": sum(1 for row in rows if row["status"] == "missing"),
            "external": sum(1 for row in rows if row["status"] == "external"),
            "unsafe": sum(1 for row in rows if row["status"] == "unsafe"),
        },
    }


def intake_payload_for_project(project: str, intake: str | None = None, *, allow_examples: bool = True) -> dict[str, Any]:
    path = project_intake_path(project, intake, allow_examples=allow_examples)
    payload = read_json_object(path, "project brief")
    if payload.get("project") and payload.get("project") != project:
        raise ValueError(f"intake project mismatch: expected {project!r}, got {payload.get('project')!r}")
    editable = path_under(path, snapshot.REPO / "projects" / project)
    return {
        "schema": "ztare-forensic-workbench-intake-v1",
        "ok": True,
        "served_from": "local_api",
        "project": project,
        "path": repo_rel(path),
        "editable": editable,
        "editable_fields": {
            "bounded_claim": str(payload.get("bounded_claim") or ""),
            "next_falsifier": str(payload.get("next_falsifier") or ""),
            "notes": str(payload.get("notes") or ""),
            "non_claims": [str(item) for item in payload.get("non_claims") or []],
            "source_refs": [str(item) for item in payload.get("source_refs") or []],
            "evidence_refs": [str(item) for item in payload.get("evidence_refs") or []],
        },
        "reference_status": intake_reference_status(payload, intake_path=path),
    }


def project_research_standing(project: str) -> dict[str, Any]:
    """Cheap per-project research STANDING for the index tiles — so the list reads as stress-tested claims,
    not a file browser. One small file read (the champion probability DAG): how likely the champion says the
    thesis holds. Confidence, NOT the gameable judge score. `tier` ∈ verified|usable|thin|unrun."""
    proot = snapshot.REPO / "projects" / project
    dag = read_optional_json_object(proot / "champion_probability_dag.json") or read_optional_json_object(proot / "latest_probability_dag.json")
    outcome = dag.get("outcome") if isinstance(dag, dict) else None
    p = outcome.get("probability") if isinstance(outcome, dict) else None
    if not isinstance(p, (int, float)):
        return {"tested": False, "tier": "unrun", "label": "Not pressure-tested"}
    p = float(p)
    tier = "verified" if p >= 0.85 else "usable" if p >= 0.6 else "thin"
    return {"tested": True, "tier": tier, "confidence": round(p, 2),
            "label": {"verified": "Verified", "usable": "Usable", "thin": "Thin"}[tier]}


def public_project_names() -> set[str]:
    """Projects an intentionally shared Workbench may disclose.

    Local mode remains the operator's full workspace. Public mode is fail-closed and uses a tracked manifest
    rather than `.gitignore`: ignored local work may exist in a deployment volume, and Git metadata is commonly
    absent from Docker images.
    """
    if PROJECT_ALLOWLIST:
        return set(PROJECT_ALLOWLIST)
    try:
        payload = json.loads(PUBLIC_PROJECTS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    projects = payload.get("projects") if isinstance(payload, dict) else []
    return {
        str(project).strip()
        for project in (projects if isinstance(projects, list) else [])
        if re.fullmatch(r"[A-Za-z0-9_.-]+", str(project).strip())
    }


def project_is_visible(project: str) -> bool:
    project = str(project or "").strip()
    if not project:
        return True
    if PROJECT_SCOPE == "local":
        return True
    if PROJECT_SCOPE == "public":
        return project in public_project_names()
    return project in PROJECT_ALLOWLIST


def require_visible_project(project: str) -> None:
    if not project_is_visible(project):
        # Do not reveal whether a hidden project exists.
        raise FileNotFoundError("project is not available in this Workbench")


def project_from_repo_path(value: Any) -> str:
    """Return a project slug only when a repository path addresses projects/<slug>/... ."""
    text = str(value or "").strip().split("#", 1)[0]
    if not text:
        return ""
    parts = PurePosixPath(text).parts
    try:
        index = parts.index("projects")
    except ValueError:
        return ""
    return str(parts[index + 1]) if len(parts) > index + 1 else ""


def require_visible_repo_path(value: Any) -> None:
    project = project_from_repo_path(value)
    if project:
        require_visible_project(project)


def project_index_payload() -> dict[str, Any]:
    projects = []
    visible_names = None if PROJECT_SCOPE == "local" else public_project_names()
    all_entries = snapshot.list_project_entries(project_names=visible_names)
    entries = [entry for entry in all_entries if project_is_visible(str(entry.get("project") or ""))]
    for entry in entries:
        row = dict(entry)
        row["status"] = project_status_value(row.get("status") or "intake_ready")
        row["project_status"] = project_status_value(row.get("status"))
        row["display_label"] = project_display_label(row.get("display_label") or row.get("project"))
        row["status_label"] = project_status_label(row.get("status"), intake_source=row.get("intake_source"))
        row["display_status"] = row["status_label"]
        row["openable"] = True
        row["next_action"] = project_folder_next_action(row)
        row["standing"] = project_research_standing(str(row.get("project") or ""))
        row["latest_project_check"] = str(row.get("latest_project_check") or row.get("latest_item_action") or row.get("latest_row_action") or "")
        row["latest_project_file_write"] = str(row.get("latest_project_file_write") or row.get("latest_case_file_write") or "")
        try:
            intake_payload = intake_payload_for_project(
                str(row.get("project") or ""),
                str(row.get("intake") or "") or None,
                allow_examples=True,
            )
            row["intake_editable"] = bool(intake_payload.get("editable"))
            row["intake_ref_summary"] = (intake_payload.get("reference_status") or {}).get("summary") or {}
        except Exception as exc:  # noqa: BLE001 - project index should surface per-project errors.
            row["intake_editable"] = False
            row["intake_ref_summary"] = {}
            row["intake_error"] = display_text(exc)
        projects.append(row)
    project_folders = [
        folder
        for folder in snapshot.list_project_folders(all_entries, project_names=visible_names)
        if project_is_visible(str(folder.get("project") or ""))
    ]
    for folder in project_folders:
        folder["display_label"] = project_display_label(folder.get("display_label") or folder.get("project"))
        folder["project_status"] = project_status_value(folder.get("status"))
        folder["status_label"] = project_status_label(folder.get("status"), intake_source=folder.get("intake_source"))
        folder["display_status"] = folder["status_label"]
        folder["hidden_by_default"] = background_project_folder(folder.get("project"))
        folder["latest_project_check"] = str(folder.get("latest_project_check") or folder.get("latest_item_action") or folder.get("latest_row_action") or "")
        folder["latest_project_file_write"] = str(folder.get("latest_project_file_write") or folder.get("latest_case_file_write") or "")
        folder["has_project_files"] = bool(
            folder.get("raw_exists")
            or folder.get("workspace_exists")
            or folder.get("source_type_map_exists")
            or folder.get("intake_count")
            or folder.get("root_source_file_count")
            or folder.get("source_preview_files")
        )
        folder["has_project_material"] = folder["has_project_files"]
        folder["has_case_material"] = folder["has_project_files"]
    openable_projects = {str(row.get("project") or "") for row in projects if row.get("project")}
    entries_by_project = {str(row.get("project") or ""): row for row in projects if row.get("project")}
    for folder in project_folders:
        project = str(folder.get("project") or "")
        ready_entry = entries_by_project.get(project)
        folder["openable"] = project in openable_projects
        if ready_entry:
            for key in (
                "intake",
                "intake_source",
                "intake_editable",
                "intake_ref_summary",
                "intake_error",
                "latest_review",
                "latest_project_check",
                "latest_item_action",
                "latest_row_action",
                "latest_intake_edit",
                "latest_source_import",
                "latest_source_edit",
                "latest_source_action",
                "latest_project_file_write",
                "latest_case_file_write",
                "report_contract",
            ):
                if key in ready_entry:
                    folder[key] = ready_entry.get(key)
            ready_entry["openable"] = True
            ready_entry["has_project_files"] = bool(folder.get("has_project_files"))
            ready_entry["has_project_material"] = bool(folder.get("has_project_material"))
            ready_entry["raw_exists"] = bool(folder.get("raw_exists"))
            ready_entry["workspace_exists"] = bool(folder.get("workspace_exists"))
            ready_entry["source_type_map_exists"] = bool(folder.get("source_type_map_exists"))
            ready_entry["root_source_file_count"] = safe_int(folder.get("root_source_file_count"))
        elif folder.get("has_project_files") and not folder.get("hidden_by_default"):
            # PERF: skip the ~4KB recovery-actions block for hidden background/_bench folders (746 of ~950) —
            # they're not shown by default and never recovered from the picker, and it dominated the payload
            # (13.4MB → ~2MB). The UI handles a missing recovery_actions (treats it as []); a hidden folder that
            # is un-hidden re-fetches its recovery draft via /api/project-recovery-draft on demand.
            project_dir = str(folder.get("project_dir") or f"projects/{project}")
            recovery_write_paths = [
                project_dir,
                f"projects/{project}/raw",
                f"projects/{project}/workspace",
                f"projects/{project}/raw/source_type_map.json",
                f"projects/{project}/{project}_intake.json",
            ] if project else []
            preview_source = next(
                (
                    path
                    for path in [
                        *(folder.get("source_preview_files") or []),
                        *(folder.get("raw_preview_files") or []),
                        *(folder.get("root_preview_files") or []),
                    ]
                    if path
                ),
                "",
            )
            preview_workspace = next((path for path in folder.get("workspace_preview_files") or [] if path), "")
            folder["recovery_actions"] = [
                project_action(
                    action_id="add_intake",
                    label="Create project brief",
                    area="recovery",
                    detail="This project folder has files, but no project brief yet. Review the draft, save the project brief, then open the project normally.",
                    workspace="projects",
                    subsection="Connect project",
                    primary_label="Create project brief",
                    source=project_dir,
                    rule="An existing project folder can be inspected first. Runs stay blocked until the project brief names the thesis, source files, evidence files, caveats, and change test.",
                    receipt_paths=[f"projects/{project}/{project}_intake.json"] if project else [],
                    write_boundary=write_boundary_payload(
                        writes_project_files=True,
                        write_paths=recovery_write_paths,
                        receipt_path=f"projects/{project}/{project}_intake.json" if project else "",
                        latest_path=f"projects/{project}/{project}_intake.json" if project else "",
                        read_only_actions=["inspect existing files", "draft project-brief fields", "preview source"],
                    ) if recovery_write_paths else None,
                )
            ]
            if preview_source:
                folder["recovery_actions"].append(
                    project_action(
                        action_id="preview_source",
                        label="Preview source",
                        area="recovery",
                        detail="Inspect an existing source file before connecting the project.",
                        workspace="projects",
                        subsection="Projects",
                        primary_label="Preview source",
                        source=preview_source,
                        write_boundary=write_boundary_payload(
                            writes_project_files=False,
                            read_only_actions=["preview source", "copy path"],
                        ),
                    )
                )
            if preview_workspace:
                folder["recovery_actions"].append(
                    project_action(
                        action_id="preview_workspace",
                        label="Preview workspace",
                        area="recovery",
                        detail="Inspect an existing workspace file before connecting the project.",
                        workspace="projects",
                        subsection="Projects",
                        primary_label="Preview workspace",
                        source=preview_workspace,
                        write_boundary=write_boundary_payload(
                            writes_project_files=False,
                            read_only_actions=["preview workspace file", "copy path"],
                        ),
                    )
                )
        folder["next_action"] = project_folder_next_action(folder)
    project_folders.sort(key=lambda row: project_inventory_sort_key(row, openable_projects=openable_projects))
    pending_project_folders = [
        row
        for row in project_folders
        if str(row.get("project") or "") not in openable_projects
    ]
    folder_summary = project_folder_summary(project_folders, openable_projects=openable_projects)
    compact_folders = [
        compact_project_folder(row)
        for row in project_folders
        if bool(row.get("openable")) or not bool(row.get("hidden_by_default"))
    ]
    return {
        "schema": "ztare-forensic-workbench-project-index-v1",
        "schema_version": "ztare-forensic-workbench-project-index-v1",
        "ok": True,
        "default_project": snapshot.DEFAULT_PROJECT if project_is_visible(snapshot.DEFAULT_PROJECT)
        else str(projects[0].get("project") or "") if projects else "",
        "project_inventory_scope": PROJECT_SCOPE,
        "project_visibility": {
            "scope": PROJECT_SCOPE,
            "manifest": repo_rel(PUBLIC_PROJECTS_PATH) if PROJECT_SCOPE == "public" else "",
            "operator_local": PROJECT_SCOPE == "local",
        },
        "inventory_root": "projects/",
        "inventory_includes_all_project_folders": PROJECT_SCOPE == "local",
        "ready_count": len(projects),
        "intake_ready_count": len(projects),
        "project_count": len(project_folders),
        "folder_count": len(project_folders),
        "visible_folder_count": len(compact_folders),
        "hidden_folder_count": len(project_folders) - len(compact_folders),
        "pending_folder_count": len(pending_project_folders),
        "folder_summary": folder_summary,
        "project_folder_summary": folder_summary,
        "projects": projects,
        # Full recovery detail is loaded for one folder on demand through /api/project-recovery-draft instead
        # of multiplying it across the project picker.
        "project_folders": compact_folders,
        "project_folders_compact": True,
        "project_folder_detail_field": "project_folders",
    }


def compact_project_folder(row: dict[str, Any]) -> dict[str, Any]:
    """Compatibility project-folder row without heavy preview arrays."""

    keys = [
        "project",
        "project_dir",
        "display_label",
        "status",
        "status_label",
        "display_status",
        "project_status",
        "openable",
        "hidden_by_default",
        "has_project_files",
        "has_project_material",
        "has_case_material",
        "intake_count",
        "latest_review",
        "latest_project_check",
        "latest_project_file_write",
        "raw_exists",
        "root_source_file_count",
        "workspace_exists",
        "source_type_map_exists",
        "next_action",
    ]
    compact = {key: row.get(key) for key in keys if key in row}
    compact["source_preview"] = next((path for path in [
        *(row.get("source_preview_files") or []),
        *(row.get("raw_preview_files") or []),
        *(row.get("root_preview_files") or []),
    ] if path), "")
    compact["workspace_preview"] = next((path for path in (row.get("workspace_preview_files") or []) if path), "")
    return compact


def project_inventory_sort_key(row: dict[str, Any], *, openable_projects: set[str]) -> tuple[int, int, int, int, str]:
    project = str(row.get("project") or "")
    openable = project in openable_projects or bool(row.get("openable") or row.get("intake_count"))
    hidden = bool(row.get("hidden_by_default") or background_project_folder(project))
    has_files = bool(row.get("has_project_files") or row.get("has_project_material") or row.get("has_case_material"))
    default_rank = 0 if project == snapshot.DEFAULT_PROJECT else 1
    return (
        0 if openable else 1,
        default_rank,
        1 if hidden else 0,
        0 if has_files else 1,
        project,
    )


def project_folder_summary(project_folders: list[dict[str, Any]], *, openable_projects: set[str] | None = None) -> dict[str, Any]:
    openable_projects = openable_projects or set()
    pending = [
        row
        for row in project_folders
        if str(row.get("project") or "") not in openable_projects
    ]
    with_material = [
        row
        for row in pending
        if row.get("has_project_files")
        or row.get("has_project_material")
        or row.get("has_case_material")
        or row.get("raw_exists")
        or row.get("workspace_exists")
        or row.get("source_type_map_exists")
        or row.get("intake_count")
    ]
    generated = [row for row in pending if row.get("hidden_by_default") or background_project_folder(row.get("project"))]
    return {
        "total": len(project_folders),
        "openable": len(openable_projects),
        "needs_intake": len(pending),
        "needs_intake_with_files": len(with_material),
        "needs_intake_empty": max(0, len(pending) - len(with_material)),
        "generated_hidden_by_default": len(generated),
    }


def recovery_excerpt(path: Path, *, limit: int = 900) -> str:
    if not path.exists() or not path.is_file():
        return ""
    text = WORKBENCH_STORE.read_text(path, errors="replace")
    lines: list[str] = []
    in_frontmatter = False
    in_fence = False
    for index, raw_line in enumerate(text.splitlines()):
        line = raw_line.strip()
        if index == 0 and line == "---":
            in_frontmatter = True
            continue
        if in_frontmatter:
            if line == "---":
                in_frontmatter = False
            continue
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or not line:
            continue
        if re.fullmatch(r"#+\s*(thesis|evidence|notes|current iteration|fit declaration)\s*", line, flags=re.IGNORECASE):
            continue
        if line.startswith("<!--"):
            continue
        lines.append(line.lstrip("#").strip())
        if len("\n".join(lines)) >= limit:
            break
    return display_text("\n".join(lines))[:limit].strip()


def noisy_recovery_line(line: str) -> bool:
    normalized = re.sub(r"[^A-Za-z0-9]+", " ", line).strip().lower()
    if not normalized:
        return True
    if len(normalized) < 12 or len(normalized.split()) < 3:
        return True
    if normalized in {"charter", "project charter"}:
        return True
    noisy_phrases = {
        "i ll analyze",
        "i will analyze",
        "i am going to analyze",
        "rebuild from first principles",
        "root cause analysis",
        "previous thesis failed",
        "new derivation from observable properties",
        "topological pivot executed",
        "symbolic mapping",
        "load bearing variables",
        "state incompatibility assumed",
        "required pivot frame",
        "contrarian position",
        "core argument",
        "the equation",
        "axioms previously verified truths",
        "critical constraint the axiomatic",
        "causal mechanism",
        "rival hypothesis",
        "named discriminator",
        "observable proxy",
        "gatekeeper reality",
        "verified by the firing squad",
        "you are forbidden",
        "topological pivot",
    }
    if any(phrase in normalized for phrase in noisy_phrases):
        return True
    if normalized in {
        "thesis",
        "evidence",
        "notes",
        "current iteration",
        "fit declaration",
        "core question",
        "problem description",
        "root cause analysis",
        "success states",
        "failure states",
        "out of scope",
    }:
        return True
    if re.match(r"^\d+\s+axiom\b", normalized):
        return True
    if normalized.startswith("axiom "):
        return True
    if re.match(r"^(step|criterion)\s+\d+\b", normalized):
        return True
    if normalized.startswith(("the previous thesis", "the fitted parameters", "compute finite differences")):
        return True
    if line.endswith(":") and len(normalized.split()) <= 8:
        return True
    return normalized.startswith(("retired axiom", "axiom retirement", "primary degree of freedom"))


def recovery_claim_excerpt(path: Path, *, limit: int = 420) -> str:
    if not path.exists() or not path.is_file():
        return ""
    text = WORKBENCH_STORE.read_text(path, errors="replace")
    explicit_candidates: list[str] = []
    fallback_candidates: list[str] = []
    in_frontmatter = False
    in_fence = False
    for index, raw_line in enumerate(text.splitlines()):
        line = raw_line.strip().strip("*_")
        if index == 0 and line == "---":
            in_frontmatter = True
            continue
        if in_frontmatter:
            if line == "---":
                in_frontmatter = False
            continue
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or not line or line.startswith("<!--"):
            continue
        line = re.sub(r"^#+\s*", "", line).strip()
        line = re.sub(r"^[-*]\s*", "", line).strip()
        if noisy_recovery_line(line):
            continue
        lower = line.lower()
        explicit = lower.startswith("thesis:") or "## thesis:" in lower
        if lower.startswith("thesis:"):
            line = line.split(":", 1)[1].strip()
        if not line:
            continue
        if explicit:
            explicit_candidates.append(display_text(line))
        else:
            fallback_candidates.append(display_text(line))
    claim = " ".join(explicit_candidates[:1] or fallback_candidates[:1])
    claim = re.sub(r"\s+", " ", claim).strip()
    return claim[:limit].strip()


def recovery_file_role(path: Path) -> str:
    rel = repo_rel(path)
    name = path.name.lower()
    if name == "thesis.md":
        return "thesis"
    if name == "current_iteration.md":
        return "current draft"
    if name == "project_charter.md":
        return "project charter"
    if name.startswith("evidence") or name.startswith("compiled_evidence"):
        return "evidence"
    if name.endswith("_evidence_gaps.json"):
        return "evidence gap"
    if name in {"latest_eval_results.json", "champion_eval_results.json", "eval_history.jsonl"}:
        return "run result"
    if name.startswith("fit_result"):
        return "fit history"
    if name in {"iteration_telemetry.jsonl", "loop_events.jsonl", "latest_information_yield.json"}:
        return "run history"
    if name in {"derived_constraints.json", "structural_memory.json", "verified_axioms.json"}:
        return "assumption"
    if "probability_dag" in name:
        return "probability model"
    if name in {"claim_summary.md"} or rel.endswith("/public/CLAIM_SUMMARY.md"):
        return "project summary"
    if "/workspace/" in rel:
        return "workspace note"
    if "/raw/" in rel:
        return "source"
    return "project note"


def is_recovery_metadata_file(path: Path) -> bool:
    name = path.name.lower()
    return name in {
        "source_type_map.json",
        "workspace_meta.json",
        "source_index.json",
        "source_index_receipt.json",
    } or name.endswith("_receipt.json")


def is_recovery_source_file(path: Path) -> bool:
    if is_recovery_metadata_file(path):
        return False
    if path.name in {"compiled_evidence_packet.json", "compiled_evidence_provenance.json"}:
        return False
    return path.suffix.lower() in {".md", ".txt", ".json", ".jsonl"}


def is_recovery_evidence_file(path: Path) -> bool:
    if is_recovery_metadata_file(path):
        return False
    rel = repo_rel(path)
    name = path.name
    lower_name = name.lower()
    return (
        lower_name.startswith("evidence")
        or name in {"compiled_evidence_packet.json", "compiled_evidence_provenance.json"}
        or lower_name.endswith("_evidence_gaps.json")
        or lower_name in {
            "latest_eval_results.json",
            "champion_eval_results.json",
            "latest_probability_dag.json",
            "champion_probability_dag.json",
            "eval_history.jsonl",
            "iteration_telemetry.jsonl",
            "fit_result.json",
            "structural_memory.json",
            "derived_constraints.json",
            "latest_information_yield.json",
        }
        or lower_name.startswith("fit_result_iter_")
        or lower_name.startswith("semantic_gate")
        or lower_name.startswith("latest_constraint")
        or ("/raw/" in rel and path.suffix.lower() in {".md", ".txt", ".json", ".jsonl"})
    )


def recovery_candidate_priority(path: Path, project_root: Path) -> tuple[int, int, str]:
    rel = repo_rel(path)
    name = path.name.lower()
    priority = 900
    if name == "thesis.md":
        priority = 10
    elif name == "evidence.txt":
        priority = 20
    elif name.startswith("evidence"):
        priority = 30
    elif name == "project_charter.md":
        priority = 40
    elif name == "current_iteration.md":
        priority = 50
    elif name == "claim_summary.md" or rel.endswith("/public/CLAIM_SUMMARY.md"):
        priority = 55
    elif name in {"latest_eval_results.json", "champion_eval_results.json"}:
        priority = 60
    elif "probability_dag" in name:
        priority = 70
    elif name.endswith("_evidence_gaps.json"):
        priority = 80
    elif name.startswith("fit_result_iter_"):
        priority = 90
    elif name in {"fit_result.json", "iteration_telemetry.jsonl", "eval_history.jsonl"}:
        priority = 100
    elif name in {"derived_constraints.json", "structural_memory.json", "latest_information_yield.json"}:
        priority = 110
    elif "/raw/" in rel:
        priority = 140
    elif name.endswith((".md", ".txt")):
        priority = 180
    return (priority, fit_result_iteration(path), rel)


def recovery_candidate_paths(project_root: Path) -> list[Path]:
    explicit = [
        project_root / "thesis.md",
        project_root / "evidence.txt",
        project_root / "evidence_holdout.txt",
        project_root / "evidence_farther_tail.txt",
        project_root / "project_charter.md",
        project_root / "current_iteration.md",
        project_root / "public" / "CLAIM_SUMMARY.md",
        project_root / "latest_eval_results.json",
        project_root / "champion_eval_results.json",
        project_root / "latest_probability_dag.json",
        project_root / "champion_probability_dag.json",
        project_root / "semantic_gate_summary.json",
        project_root / "compiled_evidence_packet.json",
        project_root / "compiled_evidence_provenance.json",
        project_root / "verified_axioms.json",
        project_root / "workspace" / "candidate_claims.md",
        project_root / "workspace" / "contradictions.md",
        project_root / "workspace" / "latest_evidence_gaps.json",
        project_root / "workspace" / "champion_evidence_gaps.json",
        project_root / "workspace" / "derived_constraints.json",
        project_root / "workspace" / "structural_memory.json",
        project_root / "workspace" / "latest_information_yield.json",
        project_root / "workspace" / "latest_constraint_proposals.json",
        project_root / "workspace" / "fit_result.json",
        project_root / "workspace" / "iteration_telemetry.jsonl",
        project_root / "workspace" / "eval_history.jsonl",
        project_root / "workspace" / "loop_events.jsonl",
    ]
    candidates: list[Path] = list(explicit)
    workspace = project_root / "workspace"
    if workspace.exists():
        patterns = [
            "fit_result_iter_*.json",
            "evidence_gaps_*.json",
            "rubric_review_*.json",
            "cap_kind_iter_*.json",
            "obligation_contract_iter_*.json",
            "structural_anti_pattern_iter_*.json",
            "*_telemetry.jsonl",
        ]
        for pattern in patterns:
            candidates.extend(sorted(workspace.glob(pattern), key=lambda path: recovery_candidate_priority(path, project_root))[:24])
    raw_dir = project_root / "raw"
    if raw_dir.exists():
        candidates.extend(
            sorted(
                (path for path in raw_dir.glob("*") if path.suffix.lower() in {".md", ".txt", ".json", ".jsonl"}),
                key=lambda path: recovery_candidate_priority(path, project_root),
            )[:30]
        )
    return sorted(unique_path_values(candidates), key=lambda path: recovery_candidate_priority(path, project_root))


def unique_path_values(paths: list[Path]) -> list[Path]:
    seen: set[str] = set()
    result: list[Path] = []
    for path in paths:
        key = path.as_posix()
        if key in seen:
            continue
        seen.add(key)
        result.append(path)
    return result


def existing_project_recovery_draft(project: str) -> dict[str, Any]:
    project = snapshot.validate_project_slug(project)
    project_root = snapshot.REPO / "projects" / project
    if not project_root.exists():
        raise FileNotFoundError(f"project folder does not exist: projects/{project}")
    charter_path = project_charter_path(project)
    charter_missing = not charter_path.exists()
    intake_path = Path(snapshot.default_intake_for_project(project))
    if not intake_path.is_absolute():
        intake_path = snapshot.REPO / intake_path
    can_add_intake = not intake_path.exists()
    intake_status = "needs project brief" if can_add_intake else "project brief already exists"
    candidate_paths = recovery_candidate_paths(project_root)
    existing = [
        path
        for path in candidate_paths
        if (
            path.exists()
            and path.is_file()
            and path_under(path, snapshot.REPO)
            and not is_recovery_metadata_file(path)
        )
    ]
    source_refs = unique_values(
        repo_rel(path)
        for path in existing
        if is_recovery_source_file(path)
    )
    evidence_refs = unique_values(
        repo_rel(path)
        for path in existing
        if is_recovery_evidence_file(path)
    )
    candidate_files = [
        {
            "path": repo_rel(path),
            "role": recovery_file_role(path),
            "previewable": True,
            "binds_as_source": repo_rel(path) in source_refs,
            "binds_as_evidence": repo_rel(path) in evidence_refs,
        }
        for path in existing[:30]
    ]
    thesis_text = recovery_claim_excerpt(project_root / "thesis.md")
    workspace_claim_text = recovery_excerpt(project_root / "workspace" / "candidate_claims.md", limit=650)
    charter_claim_text = recovery_claim_excerpt(project_root / "project_charter.md")
    iteration_claim_text = recovery_claim_excerpt(project_root / "current_iteration.md")
    bounded_claim = thesis_text or workspace_claim_text or charter_claim_text or iteration_claim_text
    review_file_lines = [
        f"- {file['role']}: {file['path']}"
        for file in candidate_files[:8]
    ]
    note_lines = [
        f"Recovered from existing folder: projects/{project}",
        "Review these files before saving the project brief:\n" + "\n".join(review_file_lines) if review_file_lines else "",
        (
            f"Draft uses {len(source_refs)} source file"
            f"{'' if len(source_refs) == 1 else 's'} and {len(evidence_refs)} evidence file"
            f"{'' if len(evidence_refs) == 1 else 's'}."
        ),
        "After connecting the project, prepare the source and evidence files before relying on the thesis.",
    ]
    summary_text = (
        f"{display_text(intake_status)}; found {len(candidate_files)} useful file"
        f"{'' if len(candidate_files) == 1 else 's'}, suggested {len(source_refs)} source file"
        f"{'' if len(source_refs) == 1 else 's'} and {len(evidence_refs)} evidence file"
        f"{'' if len(evidence_refs) == 1 else 's'}."
    )
    after_connect_steps = [
        {
            "label": "Review draft",
            "detail": "Check the project charter, thesis, change test, source files, evidence files, and caveats before saving.",
            "workspace": "projects",
            "subsection": "Connect project",
        },
        {
            "label": "Inspect source files",
            "detail": "Open the recovered source files and source-role map before running a project iteration.",
            "workspace": "sources",
            "subsection": "Prepare files",
        },
        {
            "label": "Prepare files",
            "detail": "Prepare source files and rebuild the evidence summary after the project brief is saved.",
            "workspace": "sources",
            "subsection": "Prepare files",
        },
    ]
    add_intake_write_paths = [
        repo_rel(project_root),
        repo_rel(project_root / "raw"),
        repo_rel(project_root / "workspace"),
        repo_rel(project_root / "raw" / "source_type_map.json"),
        *([repo_rel(charter_path)] if charter_missing else []),
        repo_rel(intake_path),
    ]
    add_intake_boundary = write_boundary_payload(
        writes_project_files=True,
        write_paths=add_intake_write_paths,
        receipt_path=repo_rel(intake_path),
        latest_path=repo_rel(intake_path),
        read_only_actions=["inspect existing files", "edit draft fields", "preview source"],
    )
    return {
        "schema": PROJECT_RECOVERY_DRAFT_SCHEMA,
        "ok": True,
        "served_from": "local_api",
        "project": project,
        "display_label": project_display_label(project),
        "project_dir": repo_rel(project_root),
        "status": intake_status,
        "can_add_intake": can_add_intake,
        "summary": summary_text,
        "task": f"Review {project_display_label(project)}",
        "bounded_claim": bounded_claim,
        # A missing change test is setup work, not permission to synthesize one.
        # Recovery can identify files and draft a claim, but only project-specific
        # evidence can define what would overturn that claim.
        "next_falsifier": "",
        "notes": "\n\n".join(line for line in note_lines if line),
        "source_refs": source_refs[:30],
        "evidence_refs": evidence_refs[:30],
        "non_claims": [
            "not reviewed against a fresh project brief yet",
            "not ready for a run until source and evidence files are prepared",
        ],
        "source_file_count": len(source_refs),
        "evidence_file_count": len(evidence_refs),
        "source_ref_count": len(source_refs),
        "evidence_ref_count": len(evidence_refs),
        "candidate_file_count": len(candidate_files),
        "preview_files": source_refs[:6],
        "candidate_files": candidate_files,
        "after_connect_steps": after_connect_steps,
        "recovery_summary": {
            "folder": repo_rel(project_root),
            "intake_target": repo_rel(intake_path),
            "drafted_from_file_count": len(candidate_files),
            "source_file_count": len(source_refs),
            "evidence_file_count": len(evidence_refs),
            "bounded_claim_drafted": bool(bounded_claim),
            "summary": summary_text,
            "next_action": "Review the suggested fields, preview the key files, then connect the project.",
        },
        "write_boundary": write_boundary_payload(
            writes_project_files=False,
            read_only_actions=["inspect existing files", "edit draft fields", "connect project"],
        ),
        "add_intake_action": project_action(
            action_id="add_intake",
            label="Create project brief",
            area="recovery",
            detail="Save the project brief that lets this existing folder enter the normal project flow.",
            workspace="projects",
            subsection="Connect project",
            primary_label="Create project brief",
            source=repo_rel(project_root),
            rule="An existing project folder can be inspected first. Runs stay blocked until the project brief names the thesis, source files, evidence files, caveats, and change test.",
            receipt_paths=[
                *([repo_rel(charter_path)] if charter_missing else []),
                repo_rel(intake_path),
            ],
            write_boundary=add_intake_boundary,
        ) if can_add_intake else None,
        "add_intake_write_boundary": add_intake_boundary if can_add_intake else None,
    }


def server_status_payload() -> dict[str, Any]:
    app_built = (WORKBENCH_DIST / "index.html").exists()
    snapshot_path = WORKBENCH_PUBLIC / "workbench_snapshot.json"
    snapshot_available = snapshot_path.exists()
    project_error = ""
    projects: list[dict[str, Any]] = []
    project_folders: list[dict[str, Any]] = []
    project_folder_summary_payload: dict[str, Any] = {}
    pending_folder_count = 0
    default_project = snapshot.DEFAULT_PROJECT
    try:
        project_index = project_index_payload()
        projects = list(project_index.get("projects") or [])
        project_folders = list(project_index.get("project_folders") or [])
        project_folder_summary_payload = dict(project_index.get("project_folder_summary") or {})
        pending_folder_count = int(project_index.get("pending_folder_count") or 0)
        default_project = str(project_index.get("default_project") or default_project)
    except Exception as exc:  # noqa: BLE001 - status should report readiness, not crash.
        project_error = display_text(exc)
    checks = {
        "api_ready": bool(project_folders),
        "app_built": app_built,
        "snapshot_available": snapshot_available,
        "projects_available": bool(project_folders),
        "storage_ready": WORKBENCH_STORE.exists("projects"),
    }
    primary_endpoints = [
        "GET /api/status",
        "GET /api/settings",
        "GET /api/capabilities",
        "GET /api/principles",
        "GET /api/projects",
        "GET /api/project-recovery-draft",
        "GET /api/snapshot",
        "GET /api/health",
        "GET /api/trace",
        "GET /api/workflow",
        "GET /api/report-contract",
        "GET /api/charter",
        "GET /api/intake",
        "GET /api/sources",
        "GET /api/source-file",
        "GET /api/receipts",
        "GET /api/run-history",
        "GET /api/evidence-support",
        "GET /api/evidence-gaps",
        "GET /api/leanmill",
        "GET /api/leanmill/campaigns",
        "GET /api/leanmill/campaign",
        "GET /api/leanmill/blueprints",
        "GET /api/leanmill/blueprint-read",
        "GET /api/file",
        "POST /api/leanmill/target",
        "POST /api/leanmill/blueprint",
        "POST /api/leanmill/blueprint-save",
        "POST /api/leanmill/blueprint-draft",
        "POST /api/leanmill/autoformalize-notes",
        "POST /api/leanmill/solve-adhoc",
        "POST /api/leanmill/ratify",
        "POST /api/leanmill/campaign-preflight",
        "POST /api/leanmill/campaign-run",
        "POST /api/leanmill/campaign-verify",
        "POST /api/leanmill/campaign-replay",
        "POST /api/leanmill/campaign-stop",
        "POST /api/leanmill/campaign-retire",
        "POST /api/leanmill/campaign-resume",
        "POST /api/leanmill/campaign-recover",
        "POST /api/leanmill/campaign-recheck",
        "POST /api/leanmill/campaign-interpret",
        "POST /api/charter",
        "POST /api/project-create",
        "POST /api/source-import",
        "POST /api/source-edit",
        "POST /api/source-action",
        "POST /api/evidence-fetch",
        "POST /api/evidence-gap-justify",
        "POST /api/intake",
        "POST /api/preflight",
        "POST /api/run",
        "POST /api/report-contract",
        "POST /api/report-synthesis",
        "POST /api/settings",
        "POST /api/project-file",
        "POST /api/review",
        "POST /api/next-step",
    ]
    compatibility_endpoints = [
        "GET /api/claim-support",
        "POST /api/case-file",
        "POST /api/item-action",
        "POST /api/row-action",
    ]
    settings_context = workbench_status_command_context("{project}", "{rubric}")
    action_contracts = workbench_contracts_core.build_action_contracts(
        env_path=WORKBENCH_ENV_PATH,
        source_actions=SOURCE_ACTIONS,
        evidence_prepare_command_template=display_command_from_template(
            SOURCE_ACTIONS["evidence_prepare"]["command"],
            settings_context,
        ),
        evidence_fetch_command_template=display_command(evidence_fetch_command_from_context(settings_context)),
        evidence_fetch_write_path_templates=evidence_fetch_expected_paths(
            "{project}",
            auto_compile=settings_context["auto_compile"],
        ),
    )
    def action_writes_files(contract: dict[str, Any]) -> bool:
        return bool(contract.get("writes_project_files") or contract.get("writes_repo_files"))

    def action_behavior(contract: dict[str, Any]) -> str:
        if contract.get("requires_confirmation"):
            return "asks before writing"
        if action_writes_files(contract):
            return "writes files or saved history"
        return "read-only"

    def contract_receipt_path_template(contract: dict[str, Any]) -> str:
        templates = [
            str(path)
            for path in contract.get("write_path_templates") or []
            if str(path or "").strip()
        ]
        if not templates:
            return ""
        preferred_tokens = (
            "forensic_workbench_project_files",
            "forensic_workbench_case_files",
            "forensic_workbench_reviews",
            "forensic_workbench_row_actions",
            "forensic_workbench_intake_edits",
            "forensic_workbench_source_imports",
            "forensic_workbench_source_edits",
            "forensic_workbench_source_actions",
            "forensic_workbench_evidence_fetches",
            "forensic_workbench_report_support_checks",
            "forensic_workbench_report_synthesis",
            "evidence_gap_resolutions",
            "iteration_telemetry",
            "source_index_receipt",
            "evidence_output_binding_receipt",
            "leanmill_blueprint_receipts",
            "leanmill_action_history",
            "report_support_contract",
            "_intake.json",
            ".env",
        )
        for token in preferred_tokens:
            match = next((path for path in templates if token in path), "")
            if match:
                return match
        return templates[-1]

    def contract_latest_path_template(contract: dict[str, Any]) -> str:
        templates = [
            str(path)
            for path in contract.get("write_path_templates") or []
            if str(path or "").strip()
        ]
        if not templates:
            return ""
        latest = next((path for path in templates if "latest" in path.lower()), "")
        return latest or contract_receipt_path_template(contract)

    for contract in action_contracts.values():
        contract["behavior"] = action_behavior(contract)
        templates = contract.get("write_path_templates")
        if isinstance(templates, list):
            contract["display_write_path_templates"] = [
                display_write_path_template(template)
                for template in templates
                if template
            ]
        if action_writes_files(contract):
            writes_saved_record = contract.get("writes_saved_record") is not False
            receipt_template = contract_receipt_path_template(contract) if writes_saved_record else ""
            latest_template = contract_latest_path_template(contract) if writes_saved_record else ""
            boundary = write_boundary_payload(
                writes_project_files=bool(contract.get("writes_project_files")),
                writes_repo_files=bool(contract.get("writes_repo_files")),
                write_paths=[
                    str(path)
                    for path in contract.get("write_path_templates") or []
                    if str(path or "").strip()
                ],
                receipt_path=receipt_template,
                latest_path=latest_template,
                no_change_boundary=(
                    "Preview, refresh, validation failure, and failed saves write no files. "
                    "Accepted settings saves can change only the local .env settings file."
                    if not writes_saved_record
                    else ""
                ),
            )
            contract["receipt_path_template"] = receipt_template
            contract["latest_path_template"] = latest_template
            contract["no_change_boundary"] = boundary["no_change_boundary"]
            contract["write_boundary_template"] = boundary
            contract["write_boundary"] = boundary
    summary_contracts = [row for row in action_contracts.values() if not row.get("compatibility_only")]
    read_only_actions = [row["label"] for row in summary_contracts if not action_writes_files(row)]
    write_actions = [
        row["label"]
        for row in summary_contracts
        if action_writes_files(row) and not row["requires_confirmation"]
    ]
    confirmation_actions = [row["label"] for row in summary_contracts if row["requires_confirmation"]]
    file_change_summary = {
        "read_only_count": len(read_only_actions),
        "write_count": len(write_actions),
        "ask_first_count": len(confirmation_actions),
        "read_only_steps": read_only_actions,
        "write_steps": write_actions,
        "ask_first_steps": confirmation_actions,
        "browser_writes": False,
    }
    payload: dict[str, Any] = {
        "schema": SERVER_STATUS_SCHEMA,
        "ok": checks["api_ready"],
        "app_name": "Project Workbench",
        "workflow_label": "Project path",
        "project_inventory_scope": PROJECT_SCOPE,
        "project_visibility": {
            "scope": PROJECT_SCOPE,
            "visible_project_count": len(projects),
            "allowlist_hash": (
                hashlib.sha256("\n".join(sorted(PROJECT_ALLOWLIST)).encode("utf-8")).hexdigest()
                if PROJECT_SCOPE == "allowlist" else ""
            ),
        },
        "inventory_root": "projects/",
        "inventory_includes_all_project_folders": PROJECT_SCOPE == "local",
        "project_count": len(project_folders),
        "intake_ready_count": len(projects),
        "pending_folder_count": pending_folder_count,
        "default_project": default_project,
        "server": {
            "name": "Project Workbench",
            "version": "0.1",
            "implementation": "React/Vite + local Python API",
        },
        "api_ready": checks["api_ready"],
        "app_built": checks["app_built"],
        "snapshot_available": checks["snapshot_available"],
        "projects_available": checks["projects_available"],
        "checks": checks,
        "storage": WORKBENCH_STORE.metadata(),
        "app": {
            "url_path": "/",
            "index_path": display_path(WORKBENCH_DIST / "index.html"),
        },
        "snapshot": {
            "url_path": "/workbench_snapshot.json",
            "path": display_path(snapshot_path),
        },
        "api": {
            "primary_route_count": len(primary_endpoints),
            "compatibility_route_count": len(compatibility_endpoints),
            "project_inventory_scope": PROJECT_SCOPE,
            "inventory_root": "projects/",
            "inventory_includes_all_project_folders": PROJECT_SCOPE == "local",
            "project_count": len(project_folders),
            "intake_ready_count": len(projects),
            "pending_folder_count": pending_folder_count,
            "folder_summary": project_folder_summary_payload,
            "primary_live_routes": {
                "settings": "GET /api/settings -> POST /api/settings",
                "principles": "GET /api/principles",
                "project_inventory": "GET /api/projects",
                "snapshot": "GET /api/snapshot",
                "workflow": "GET /api/workflow",
                "evidence_support": "GET /api/evidence-support",
                "evidence_gaps": "GET /api/evidence-gaps",
                "leanmill": "GET /api/leanmill",
                "leanmill_target": "POST /api/leanmill/target",
                "leanmill_blueprint": "POST /api/leanmill/blueprint",
                "leanmill_autoformalize_notes": "POST /api/leanmill/autoformalize-notes",
                "leanmill_solve_adhoc": "POST /api/leanmill/solve-adhoc",
                "leanmill_ratify": "POST /api/leanmill/ratify",
                "evidence_fetch": "POST /api/evidence-fetch",
                "intake_edit": "POST /api/intake",
                "source_import": "POST /api/source-import",
                "source_edit": "POST /api/source-edit",
                "source_check": "POST /api/source-action",
                "source_index": "POST /api/source-action",
                "evidence_bind": "POST /api/source-action",
                "evidence_replay": "POST /api/source-action",
                "evidence_gap_justify": "POST /api/evidence-gap-justify",
                "preflight": "POST /api/preflight",
                "run_preview_and_confirm": "POST /api/run",
                "report_support_refresh": "POST /api/report-contract",
                "report_synthesis": "POST /api/report-synthesis",
                "research_map": "GET /api/research-map -> POST /api/research-map",
                "review": "POST /api/review",
                "next_step": "POST /api/next-step",
                "project_file": "POST /api/project-file",
                "project_create": "POST /api/project-create",
            },
            "action_contracts": action_contracts,
            "action_summary": {
                "read_only_count": len(read_only_actions),
                "write_without_confirmation_count": len(write_actions),
                "confirmation_required_count": len(confirmation_actions),
                "read_only_actions": read_only_actions,
                "write_without_confirmation_actions": write_actions,
                "confirmation_required_actions": confirmation_actions,
            },
            "file_change_summary": file_change_summary,
            "write_contract": {
                "browser_writes": False,
                "requires_explicit_server_write": True,
                "action_count": len(action_contracts),
                "write_action_count": sum(1 for row in action_contracts.values() if action_writes_files(row)),
                "write_without_confirmation_count": sum(
                    1
                    for row in action_contracts.values()
                    if action_writes_files(row) and not row["requires_confirmation"]
                ),
                "read_only_action_count": sum(1 for row in action_contracts.values() if not action_writes_files(row)),
                "confirmation_required_count": sum(1 for row in action_contracts.values() if row["requires_confirmation"]),
            },
            "file_preview": {
                "mode": "bounded repo preview",
                "max_preview_bytes": MAX_PREVIEW_BYTES,
                "allowed_roots": list(FILE_PREVIEW_ALLOWED_ROOTS),
                "allowed_root_files": sorted(FILE_PREVIEW_ALLOWED_FILES),
                "blocked_path_parts": sorted(FILE_PREVIEW_BLOCKED_PARTS),
            },
            "endpoints": primary_endpoints,
            "compatibility_endpoints": compatibility_endpoints,
        },
        "projects": {
            "project_count": len(project_folders),
            "project_inventory_scope": PROJECT_SCOPE,
            "inventory_root": "projects/",
            "inventory_includes_all_project_folders": PROJECT_SCOPE == "local",
            "ready_count": len(projects),
            "intake_ready_count": len(projects),
            "count": len(project_folders),
            "folder_count": len(project_folders),
            "pending_folder_count": pending_folder_count,
            "folder_summary": project_folder_summary_payload,
            "default_project": default_project,
        },
    }
    if project_error:
        payload["projects"]["error"] = project_error
    return payload


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    WORKBENCH_STORE.append_jsonl(path, row)


def case_key(project: str, intake: str | None) -> str:
    intake_value = str(intake or "").strip()
    return f"{project}::{intake_value}" if intake_value else project


def case_file_stem(project: str, intake: str | None) -> str:
    digest = hashlib.sha256(case_key(project, intake).encode("utf-8")).hexdigest()[:12]
    return f"forensic_workbench_project_file_{digest}"


def add_case_context(
    receipt: dict[str, Any],
    *,
    project: str,
    rubric: str | None = None,
    intake: str | None = None,
) -> dict[str, Any]:
    rubric_value = str(rubric or "").strip()
    intake_value = str(intake or "").strip()
    if rubric_value:
        receipt["rubric"] = rubric_value
    if intake_value:
        receipt["intake"] = intake_value
    key = case_key(project, intake_value)
    receipt["project_key"] = key
    receipt["project_file_key"] = key
    receipt["case_key"] = key
    return receipt


def write_boundary_payload(
    *,
    writes_project_files: bool,
    writes_repo_files: bool = False,
    write_paths: list[str] | None = None,
    receipt_path: str = "",
    latest_path: str = "",
    read_only_actions: list[str] | None = None,
    no_change_boundary: str = "",
) -> dict[str, Any]:
    clean_write_paths: list[str] = []
    for path in write_paths or []:
        if path and path not in clean_write_paths:
            clean_write_paths.append(path)
    if not no_change_boundary:
        no_change_boundary = (
            "Preview, cancellation, validation failure, and refused confirmation write no files. "
            "Accepted actions can change only the listed paths; saved-history-only actions may append saved work "
            "even when project content is otherwise unchanged."
            if writes_project_files or writes_repo_files
            else "This action is read-only unless a separate confirmed write is requested."
        )
    return {
        "schema": "ztare-forensic-workbench-write-boundary-v1",
        "storage": WORKBENCH_STORE.metadata(),
        "storage_backend": WORKBENCH_STORE.backend,
        "storage_write_mode": WORKBENCH_STORE.metadata()["write_mode"],
        "detachable_storage": True,
        "writes_project_files": bool(writes_project_files),
        "writes_repo_files": bool(writes_repo_files),
        "browser_writes": False,
        "write_paths": clean_write_paths,
        "receipt_path": receipt_path,
        "latest_path": latest_path,
        "no_change_boundary": no_change_boundary,
        "read_only_actions": read_only_actions or ["preview", "copy", "download"],
    }


def source_action_write_boundary(project: str, rubric: str, action: str) -> dict[str, Any]:
    spec = SOURCE_ACTIONS.get(action) or {}
    write_paths = [
        str(path).format(project=project, rubric=rubric)
        for path in spec.get("write_path_templates") or []
        if path
    ]
    receipt_path = next(
        (path for path in write_paths if "forensic_workbench_source_actions" in path),
        (
            str(spec.get("receipt_path_template") or "").format(project=project, rubric=rubric)
            if spec.get("receipt_path_template")
            else next((path for path in write_paths if "receipt" in path), "")
        ),
    )
    latest_path = next((path for path in write_paths if "latest" in path.lower()), "")
    return write_boundary_payload(
        writes_project_files=bool(spec.get("writes") and write_paths),
        write_paths=write_paths,
        receipt_path=receipt_path,
        latest_path=latest_path,
        read_only_actions=["preview command", "confirm in app"],
    )


def failed_write_boundary_payload(
    *,
    write_paths: list[str] | None = None,
    receipt_path: str = "",
    latest_path: str = "",
    read_only_actions: list[str] | None = None,
) -> dict[str, Any]:
    return write_boundary_payload(
        writes_project_files=False,
        write_paths=write_paths or [],
        receipt_path=receipt_path,
        latest_path=latest_path,
        read_only_actions=read_only_actions or ["inspect error", "fix inputs", "retry"],
        no_change_boundary=(
            "This request failed before an accepted write. No files changed; "
            "a corrected retry can change only the listed paths."
        ),
    )


def post_error_payload(path: str, exc: BaseException) -> dict[str, Any]:
    payload: dict[str, Any] = {"ok": False, "error": display_text(exc)}
    if path in WRITE_POST_ENDPOINTS:
        payload["write_boundary"] = write_boundary_payload(
            writes_project_files=False,
            read_only_actions=["inspect error", "preview", "copy"],
        )
    return payload


def preflight_telemetry_path(project: str) -> str:
    return f"projects/{project}/workspace/iteration_telemetry.jsonl"


def preflight_write_paths(trace_payload: dict[str, Any] | None) -> list[str]:
    trace_payload = trace_payload or {}
    loop = trace_payload.get("loop_admission") or trace_payload.get("preflight_receipt") or {}
    if not isinstance(loop, dict):
        return []
    paths: list[str] = []
    for key in ("path", "receipt_path", "preflight_receipt_path", "loop_admission_path", "latest", "ledger"):
        value = display_path(loop.get(key))
        if value and value not in paths:
            paths.append(value)
    if loop.get("receipt_count") and trace_payload.get("project"):
        telemetry_path = preflight_telemetry_path(str(trace_payload["project"]))
        if telemetry_path not in paths:
            paths.append(telemetry_path)
    return paths


def read_receipt_ledger(path: Path, *, kind: str) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    rel_path = repo_rel(path)
    for line_number, line in enumerate(WORKBENCH_STORE.read_text(path).splitlines(), start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            rows.append(
                {
                    "kind": "unreadable",
                    "source_kind": kind,
                    "applied_at": "",
                    "path": rel_path,
                    "line": line_number,
                    "summary": f"Unreadable saved-history line: {exc}",
                }
            )
            continue
        if not isinstance(payload, dict):
            rows.append(
                {
                    "kind": "unreadable",
                    "source_kind": kind,
                    "applied_at": "",
                    "path": rel_path,
                    "line": line_number,
                    "summary": "Saved-history line is not a JSON object.",
                }
            )
            continue
        rows.append(normalize_receipt_row(payload, kind=kind, path=rel_path, line=line_number))
    return rows


def read_evidence_gap_resolution_receipts(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rel_path = repo_rel(path)
    try:
        payload = read_json_object(path, "evidence-gap resolution saved history")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return [
            {
                "kind": "unreadable",
                "source_kind": "evidence_gap_resolution",
                "applied_at": "",
                "path": rel_path,
                "line": 0,
                "summary": f"Unreadable evidence-gap history: {display_text(exc)}",
            }
        ]
    resolutions = payload.get("resolutions")
    if not isinstance(resolutions, list):
        return [
            {
                "kind": "unreadable",
                "source_kind": "evidence_gap_resolution",
                "applied_at": "",
                "path": rel_path,
                "line": 0,
                "summary": "Evidence-gap history has no resolutions list.",
            }
        ]
    rows: list[dict[str, Any]] = []
    for index, resolution in enumerate(resolutions, start=1):
        if not isinstance(resolution, dict):
            rows.append(
                {
                    "kind": "unreadable",
                    "source_kind": "evidence_gap_resolution",
                    "applied_at": "",
                    "path": rel_path,
                    "line": index,
                    "summary": "Evidence-gap resolution is not a JSON object.",
                }
            )
            continue
        row_payload = {
            **resolution,
            "schema": str(payload.get("schema") or resolution.get("schema") or ""),
            "project": str(payload.get("project") or resolution.get("project") or ""),
        }
        rows.append(normalize_receipt_row(row_payload, kind="evidence_gap_resolution", path=rel_path, line=index))
    return rows


def receipt_check_label(label: str, slug: str = "", row_label: str = "") -> str:
    raw_slug = str(slug or "")
    if raw_slug in {"report_export", "report_support"}:
        return "Report readiness"
    raw_row_label = snapshot.display_check_label(str(row_label or ""))
    if raw_row_label and raw_row_label.lower() != "unknown check":
        return raw_row_label
    raw_label = snapshot.display_check_label(str(label or ""))
    if raw_label and raw_label.lower() != "unknown check":
        return raw_label
    if str(label or "").strip():
        return display_value(label)
    return ""


def compact_receipt_note(value: Any, *, limit: int = 180) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def evidence_fetch_manifest_reason_fields(manifest: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    failure_counts = manifest.get("failure_counts") if isinstance(manifest.get("failure_counts"), dict) else {}
    fetches = manifest.get("fetches") if isinstance(manifest.get("fetches"), list) else []
    recovery_hints = [
        str(row.get("recovery_hint") or "")
        for row in fetches
        if isinstance(row, dict) and row.get("recovery_hint")
    ]
    return failure_counts, list(dict.fromkeys(hint for hint in recovery_hints if hint))


def evidence_fetch_manifest_diagnostics(manifest_path: Any) -> tuple[dict[str, Any], list[str]]:
    path = display_path(manifest_path)
    if not path:
        return {}, []
    try:
        resolved = WORKBENCH_STORE.resolve(path)
    except ValueError:
        return {}, []
    if not resolved.exists():
        return {}, []
    try:
        manifest = read_json_object(resolved, "evidence fetch manifest")
    except (OSError, json.JSONDecodeError, ValueError):
        return {}, []
    return evidence_fetch_manifest_reason_fields(manifest)


def normalize_receipt_row(payload: dict[str, Any], *, kind: str, path: str, line: int) -> dict[str, Any]:
    display_kind = {
        "review": "review",
        "row_action": "next step",
        "intake_edit": "intake change",
        "source_import": "new source",
        "source_edit": "file edit",
        "source_action": "source check",
        "evidence_fetch": "evidence fetch",
        "report_synthesis": "report input refresh",
        "report_support_refresh": "report readiness check",
        "claim_card": "claim card",
        "project_test": "project test",
        "evidence_gap_resolution": "evidence gap",
        "case_file": "project file",
        "project_file": "project file",
        "unreadable": "unreadable saved history",
    }.get(kind, display_value(kind))
    project_key = str(payload.get("project_key") or payload.get("case_key") or "")
    compatibility_key = str(payload.get("case_key") or payload.get("project_key") or "")
    row: dict[str, Any] = {
        "kind": kind,
        "display_kind": display_kind,
        "schema": str(payload.get("schema") or ""),
        "applied_at": str(payload.get("applied_at") or ""),
        "project": str(payload.get("project") or ""),
        "rubric": str(payload.get("rubric") or ""),
        "intake": str(payload.get("intake") or payload.get("intake_path") or ""),
        "project_key": project_key,
        "case_key": compatibility_key,
        "path": path,
        "line": line,
        "summary": "",
    }
    if kind == "review":
        item_label = str(payload.get("project_check_label") or payload.get("item_label") or payload.get("row") or "")
        item_slug = str(payload.get("project_check_slug") or payload.get("item_slug") or payload.get("row_slug") or "")
        check_label = receipt_check_label(item_label, item_slug, str(payload.get("row") or ""))
        row.update(
            {
                "project_check_label": str(payload.get("project_check_label") or check_label or item_label),
                "project_check_slug": str(payload.get("project_check_slug") or item_slug),
                "item_label": item_label,
                "item_slug": item_slug,
                "check_label": check_label,
                "display_label": check_label,
                "row": str(payload.get("row") or ""),
                "row_slug": str(payload.get("row_slug") or item_slug),
                "decision": str(payload.get("decision") or ""),
                "display_decision": display_value(payload.get("decision") or ""),
                "note": str(payload.get("note") or ""),
                "review_file_path": display_path(payload.get("review_file_path")),
                "evidence_ref_count": safe_int(payload.get("evidence_ref_count")),
                "sha256": str(payload.get("review_file_sha256") or ""),
            }
        )
        note = compact_receipt_note(row["note"])
        row["summary"] = f"{display_value(row['decision'])} on {check_label or item_slug or 'project test'}"
        if note:
            row["summary"] = f"{row['summary']}: {note}"
    elif kind == "row_action":
        item_label = str(payload.get("project_check_label") or payload.get("item_label") or payload.get("row") or "")
        item_slug = str(payload.get("project_check_slug") or payload.get("item_slug") or payload.get("row_slug") or "")
        check_label = receipt_check_label(item_label, item_slug, str(payload.get("row") or ""))
        row.update(
            {
                "project_check_label": str(payload.get("project_check_label") or check_label or item_label),
                "project_check_slug": str(payload.get("project_check_slug") or item_slug),
                "item_label": item_label,
                "item_slug": item_slug,
                "check_label": check_label,
                "display_label": check_label,
                "row": str(payload.get("row") or ""),
                "row_slug": str(payload.get("row_slug") or item_slug),
                "action": str(payload.get("action") or ""),
                "display_action": display_value(payload.get("action") or ""),
                "note": str(payload.get("note") or ""),
                "action_file_path": display_path(payload.get("action_file_path")),
                "evidence_ref_count": safe_int(payload.get("evidence_ref_count")),
                "sha256": str(payload.get("action_file_sha256") or ""),
            }
        )
        note = compact_receipt_note(row["note"])
        row["summary"] = f"{display_value(row['action'])} on {check_label or item_slug or 'check'}"
        if note:
            row["summary"] = f"{row['summary']}: {note}"
    elif kind == "intake_edit":
        fields = [str(item) for item in payload.get("updated_fields") or []]
        row.update(
            {
                "intake_path": str(payload.get("intake_path") or ""),
                "updated_fields": fields,
                "sha256": str(payload.get("after_sha256") or ""),
            }
        )
        row["summary"] = f"Updated {', '.join(fields) if fields else 'intake'}"
    elif kind in {"source_import", "source_edit"}:
        row.update(
            {
                "source_path": str(payload.get("source_path") or ""),
                "source_type": str(payload.get("source_type") or ""),
                "display_source_type": display_value(payload.get("source_type") or ""),
                "artifact_kind": str(payload.get("artifact_kind") or ""),
                "display_artifact_kind": display_value(payload.get("artifact_kind") or ""),
                "created_by": str(payload.get("created_by") or ""),
                "chars": safe_int(payload.get("chars")),
                "sha256": str(payload.get("sha256") or ""),
            }
        )
        verb = "Imported" if kind == "source_import" else "Edited"
        kind_label = display_value(row["artifact_kind"] or row["source_type"])
        creator = f" from {row['created_by']}" if row["created_by"] else ""
        row["summary"] = f"{verb} {row['source_path'] or 'source'} as {kind_label}{creator}"
    elif kind == "source_action":
        row.update(
            {
                "action": str(payload.get("action") or ""),
                "display_action": display_value(payload.get("action") or ""),
                "label": str(payload.get("label") or ""),
                "display_label": display_value(payload.get("label") or payload.get("action") or ""),
                "accepted": bool(payload.get("accepted")),
                "display_status": "accepted" if payload.get("accepted") else "needs attention",
                "returncode": safe_int(payload.get("returncode")),
                "source_path": str(payload.get("source_path") or ""),
                "source_receipt_path": str(payload.get("source_receipt_path") or ""),
                "source_sha256": str(payload.get("source_sha256") or ""),
                "source_receipt_sha256": str(payload.get("source_receipt_sha256") or ""),
                "sha256": str(payload.get("source_sha256") or payload.get("source_receipt_sha256") or ""),
            }
        )
        status = "accepted" if row["accepted"] else "attention"
        row["summary"] = (
            f"{display_value(row['label'] or row['action'])} {status}; "
            f"file={row['source_path'] or row['source_receipt_path'] or 'not loaded'}"
        )
    elif kind == "evidence_gap_resolution":
        target = str(payload.get("target") or payload.get("gap_id") or "Evidence gap")
        status = str(payload.get("status") or "")
        evidence_refs = payload.get("evidence_refs") if isinstance(payload.get("evidence_refs"), list) else []
        row.update(
            {
                "applied_at": str(payload.get("resolved_at") or payload.get("applied_at") or ""),
                "resolution_id": str(payload.get("resolution_id") or ""),
                "gap_id": str(payload.get("gap_id") or ""),
                "target": target,
                "display_label": target,
                "status": status,
                "display_status": display_value(status),
                "reason": str(payload.get("reason") or ""),
                "gap_sha256": str(payload.get("gap_sha256") or ""),
                "gap_source_path": str(payload.get("gap_source_path") or ""),
                "evidence_ref_count": len(evidence_refs),
                "sha256": str(payload.get("gap_sha256") or ""),
                "receipt_file_path": path,
            }
        )
        row["summary"] = f"{display_value(status)} evidence gap: {target}"
    elif kind == "evidence_fetch":
        accepted = bool(payload.get("accepted"))
        failure_counts = payload.get("failure_counts") if isinstance(payload.get("failure_counts"), dict) else {}
        recovery_hints = [str(item) for item in payload.get("recovery_hints") or [] if item]
        if not failure_counts or not recovery_hints:
            manifest_failure_counts, manifest_recovery_hints = evidence_fetch_manifest_diagnostics(payload.get("manifest_path"))
            if not failure_counts:
                failure_counts = manifest_failure_counts
            if not recovery_hints:
                recovery_hints = manifest_recovery_hints
        row.update(
            {
                "accepted": accepted,
                "display_status": "accepted" if accepted else "needs attention",
                "returncode": safe_int(payload.get("returncode")),
                "manifest_path": str(payload.get("manifest_path") or ""),
                "manifest_sha256": str(payload.get("manifest_sha256") or ""),
                "total_attempted": safe_int(payload.get("total_attempted")),
                "total_accepted": safe_int(payload.get("total_accepted")),
                "skipped_duplicates": safe_int(payload.get("skipped_duplicates")),
                "search_backend": str(payload.get("search_backend") or ""),
                "severity": str(payload.get("severity") or ""),
                "failure_counts": failure_counts,
                "recovery_hints": recovery_hints,
                "sha256": str(payload.get("manifest_sha256") or ""),
            }
        )
        status = "accepted" if accepted else "attention"
        failure_text = ""
        if failure_counts:
            failure_text = "; " + ", ".join(f"{display_value(key)}={value}" for key, value in sorted(failure_counts.items()))
        hint_text = ""
        if row.get("recovery_hints"):
            hint_text = f"; next: {row['recovery_hints'][0]}"
        row["summary"] = (
            f"Evidence fetch {status}; accepted {row['total_accepted']} of "
            f"{row['total_attempted']} attempted{failure_text}{hint_text}"
        )
    elif kind in {"report_synthesis", "report_support_refresh"}:
        accepted = bool(payload.get("accepted"))
        row.update(
            {
                "accepted": accepted,
                "display_status": "accepted" if accepted else "needs attention",
                "returncode": safe_int(payload.get("returncode")),
                "report_support_contract": str(payload.get("report_support_contract") or ""),
                "report_support_sha256": str(payload.get("report_support_sha256") or ""),
                "status": str(payload.get("status") or ""),
                "model": str(payload.get("model") or ""),
                "sha256": str(payload.get("report_support_sha256") or ""),
            }
        )
        if kind == "report_synthesis":
            model_text = f" with {row['model']}" if row["model"] else ""
            row["summary"] = f"Report inputs refreshed{model_text}; {'accepted' if accepted else 'needs attention'}"
        else:
            row["summary"] = f"Report readiness check {'accepted' if accepted else 'needs attention'}"
    elif kind == "claim_card":
        verification_ok = bool(payload.get("verification_ok") or payload.get("status") == "accepted")
        evidence_count = safe_int(payload.get("evidence_count"))
        row.update(
            {
                "accepted": verification_ok,
                "display_status": "accepted" if verification_ok else "needs attention",
                "status": str(payload.get("status") or ""),
                "card_hash": str(payload.get("card_hash") or ""),
                "json_path": str(payload.get("json_path") or ""),
                "markdown_path": str(payload.get("markdown_path") or ""),
                "html_path": str(payload.get("html_path") or ""),
                "receipt_path": str(payload.get("receipt_path") or ""),
                "latest_path": str(payload.get("latest_path") or ""),
                "evidence_count": evidence_count,
                "sha256": str(payload.get("card_hash") or ""),
            }
        )
        status = "verified" if verification_ok else "needs attention"
        evidence_text = f" against {evidence_count} evidence file{'s' if evidence_count != 1 else ''}" if evidence_count else ""
        row["summary"] = f"Built shareable claim card; {status}{evidence_text}."
    elif kind == "project_test":
        accepted = bool(payload.get("accepted") or payload.get("status") == "accepted")
        action_label = display_guidance_text(payload.get("action_label") or "")
        row.update(
            {
                "accepted": accepted,
                "display_status": "accepted" if accepted else "needs attention",
                "returncode": safe_int(payload.get("returncode")),
                "action_id": str(payload.get("action_id") or ""),
                "action_label": action_label,
                "test_path": str(payload.get("test_path") or ""),
                "command": str(payload.get("command") or ""),
                "stdout_tail": str(payload.get("stdout_tail") or ""),
                "stderr_tail": str(payload.get("stderr_tail") or ""),
            }
        )
        result = "passed" if accepted else "needs attention"
        output = compact_receipt_note(row["stdout_tail"] or row["stderr_tail"], limit=140)
        row["summary"] = f"Project test {result}"
        if accepted and "counterexample" in action_label.lower():
            output = "no counterexample was found by the saved project test"
        elif accepted and "parameter" in action_label.lower() and "test" in action_label.lower():
            output = "the saved parameter-space test did not find a blocking case"
        if output:
            row["summary"] = f"{row['summary']}: {output}"
    elif kind in {"case_file", "project_file"}:
        project_check_count = safe_int(payload.get("project_check_count") or payload.get("item_count") or payload.get("row_count"))
        item_label = "open issue" if project_check_count == 1 else "open issues"
        project_state_action_count = safe_int(payload.get("project_state_action_count"))
        project_state_repair_count = safe_int(payload.get("project_state_project_repair_count"))
        project_state_inspect_count = safe_int(payload.get("project_state_project_inspect_count"))
        project_state_advisory_count = safe_int(payload.get("project_state_advisory_count"))
        project_state_next_action = str(payload.get("project_state_next_action") or "")
        row.update(
            {
                "project_file_path": str(payload.get("project_file_path") or payload.get("case_file_path") or ""),
                "project_file_sha256": str(payload.get("project_file_sha256") or payload.get("case_file_sha256") or ""),
                "case_file_path": str(payload.get("case_file_path") or ""),
                "project_check_count": project_check_count,
                "item_count": project_check_count,
                "row_count": project_check_count,
                "command_count": safe_int(payload.get("command_count")),
                "receipt_count": safe_int(payload.get("receipt_count")),
                "project_state_schema": str(payload.get("project_state_schema") or ""),
                "project_state_next_action": project_state_next_action,
                "project_state_action_count": project_state_action_count,
                "project_state_project_repair_count": project_state_repair_count,
                "project_state_project_inspect_count": project_state_inspect_count,
                "project_state_advisory_count": project_state_advisory_count,
                "project_file_inventory_count": safe_int(payload.get("project_file_inventory_count")),
                "project_file_previewable_count": safe_int(payload.get("project_file_previewable_count")),
                "project_file_missing_count": safe_int(payload.get("project_file_missing_count")),
                "sha256": str(payload.get("project_file_sha256") or payload.get("case_file_sha256") or ""),
            }
        )
        if row["project_state_schema"] or project_state_action_count:
            next_action = project_state_next_action or "not loaded"
            action_bits = [f"{project_state_action_count} open actions"]
            if project_state_repair_count:
                action_bits.append(f"{project_state_repair_count} repairs")
            if project_state_inspect_count:
                action_bits.append(f"{project_state_inspect_count} inspections")
            if project_state_advisory_count:
                action_bits.append(f"{project_state_advisory_count} guidance items")
            if row["project_file_inventory_count"]:
                action_bits.append(
                    f"{row['project_file_inventory_count']} files "
                    f"({row['project_file_previewable_count']} previewable, "
                    f"{row['project_file_missing_count']} missing)"
                )
            row["summary"] = f"Saved project file; next action {next_action}; {', '.join(action_bits)}"
        else:
            row["summary"] = (
                f"Saved project file with {row['project_check_count']} {item_label}, "
                f"{row['command_count']} commands, {row['receipt_count']} saved changes"
            )
    else:
        row["summary"] = kind.replace("_", " ")
    row["display_summary"] = display_guidance_text(row.get("summary") or "")
    return row


def display_value(value: Any) -> str:
    raw = str(value or "recorded")
    overrides = {
        "blocked": "hold report",
        "next_step": "next step",
        "needs_source": "needs source",
        "ready_to_run": "ready to run",
        "export_blocker": "fix report readiness",
    }
    return overrides.get(raw, raw.replace("_", " "))


def display_status(value: Any) -> str:
    raw = str(value or "unknown")
    plain_overrides = {
        "out_of_loop_evidence_recovery": "evidence gap needs fetch or justification",
        "blocked_on_out_of_loop_prep": "blocked until evidence gaps are resolved",
    }
    if raw in plain_overrides:
        return plain_overrides[raw]
    if raw == "unbound":
        return "not connected"
    if raw == "missing_packet":
        return "missing evidence file"
    if raw == "blocked_before_kernel_entry":
        return "blocked before run"
    return snapshot.display_status(raw)


def display_surface(value: Any) -> str:
    raw = str(value or "")
    surface_overrides = {
        "project_dir": "project folder",
        "raw_sources": "source files",
        "source_preflight": "file status",
        "source_index": "file index",
        "source_index_receipt": "file-index history",
        "compile_provenance": "evidence history",
        "evidence_output": "evidence output",
        "evidence_replay": "evidence replay",
        "claim_support": "evidence support",
        "evidence_gaps": "evidence gaps",
        "project_intake": "project brief",
        "project_trace": "project run history",
        "launch_preflight": "readiness check",
        "mutator_briefing": "run briefing",
        "prediction_contracts": "forecast records",
        "eval_history": "run history",
    }
    return surface_overrides.get(raw, display_value(raw or "check"))


def plan_step_display_status(row: dict[str, Any], plan_status: str) -> str:
    status = str(row.get("status") or "").strip()
    if status:
        return display_status(status)
    step_id = str(row.get("id") or "").strip()
    has_command = bool(str(row.get("command") or "").strip())
    model_calls = bool(row.get("model_calls"))
    if step_id == "intake_declared_run":
        return "ready"
    if step_id == "repair_surfaces":
        if plan_status.startswith("blocked"):
            return "needs action" if has_command else "needs review"
        return "not needed"
    if step_id == "preflight_only":
        if plan_status == "ready_for_preflight":
            return "next local check"
        if plan_status == "ready_for_bounded_run":
            return "accepted"
        return "after recovery"
    if step_id == "bounded_loop_run":
        if plan_status == "ready_for_bounded_run":
            return "ready after confirmation"
        if plan_status.startswith("blocked"):
            return "waits for recovery"
        return "after preflight"
    if step_id == "trace_health_review":
        return "after run"
    if model_calls:
        return "after confirmation"
    if has_command:
        return "available"
    return "not checked"


def display_action_label(value: Any) -> str:
    raw = str(value or "")
    action_overrides = {
        "weak_gp233_linkage": "evidence links need repair",
        "stale_trajectory_output": "run-history archive is stale",
        "unconsumed_surface": "work log is missing",
        "source_compilation_defect": "source compilation needs repair",
        "repair_source_emitter": "repair source logs",
        "split_contract": "split into a smaller question",
        "ask_another_independent_agent": "ask for another independent check",
        "defer": "defer",
        "surface_trajectory_cluster": "review related run history",
        "diagnostic_only": "diagnostic only",
        "none_advisory_only": "advisory only",
        "gp230_read_model": "forecast record summary",
        "gp233": "evidence ledger",
        "trajectory_surfacing": "run-history surfacing",
        "forecast_ops": "forecast records",
        "warning": "warning",
    }
    return action_overrides.get(raw, display_surface(raw))


def source_health_recommended_action_label(issue_type: Any, recommended_action: Any) -> str:
    issue_overrides = {
        "weak_gp233_linkage": "repair evidence links",
        "stale_trajectory_output": "refresh run-history archive",
        "unconsumed_surface": "record work-log use",
    }
    raw_issue = str(issue_type or "")
    if raw_issue in issue_overrides:
        return issue_overrides[raw_issue]
    return display_action_label(recommended_action)


def display_guidance_text(value: Any) -> str:
    text = display_text(value)
    replacements = {
        "markdown-only GP-233 linkage": "doc-only evidence ledger linkage",
        "GP-233": "evidence ledger",
        "gp233": "evidence ledger",
        "GP-230": "forecast record",
        "gp230": "forecast record",
        "trajectory outputs": "run-history outputs",
        "trajectory/primitives surfacing": "run-history work",
        "trajectory surfacing": "run-history work",
        "shown surfaces": "shown work",
        "surfacing event ledger": "work ledger",
        "surfacing-event ledger": "work ledger",
        "diagnostic-only": "diagnostic only",
        "non-diagnostic": "stronger",
        "R1 declaration": "run declaration",
        "the " + "CHG-142" + " change": "the recorded change",
        "project packet": "project brief",
        "packet": "project brief",
        "Report support": "Report readiness",
        "report support": "report readiness",
        "report-support": "report readiness",
        "support-contract": "support contract",
    }
    for raw, rendered in replacements.items():
        text = text.replace(raw, rendered)
    text = text.replace("diagnostic only surfacing", "diagnostic guidance")
    text = text.replace("stronger recommendations", "stronger suggestions")
    text = text.replace("shown work are logged", "shown work is logged")
    return text


def display_evidence_ref(value: Any) -> dict[str, str]:
    path = display_path(value)
    lower = path.lower()
    if "gp-233_evidence_ledger" in lower or "research_yield_decomposition" in lower:
        label = "Evidence ledger file"
    elif "forecast_pool/aggregates" in lower:
        label = "Forecast summary file"
    elif "forecast_pool/contracts" in lower:
        label = "Forecast question file"
    elif "forecast_pool/market_state" in lower:
        label = "Forecast market file"
    elif "trajectory_archive" in lower:
        label = "Run-history archive"
    elif "surfacing_event_ledger" in lower:
        label = "Work log"
    else:
        label = "Evidence file"
    return {"label": label, "path": path}


def display_write_path_template(value: Any) -> dict[str, str]:
    path = display_path(value)
    lower = path.lower()
    if path == WORKBENCH_ENV_PATH or lower == ".env" or lower.endswith("/.env"):
        label = "Settings file"
    elif path == "{intake}" or "_intake.json" in lower:
        label = "Project brief"
    elif "compiled_evidence_provenance" in lower:
        label = "Evidence provenance"
    elif "compiled_evidence_packet" in lower or lower.endswith("/evidence.txt"):
        label = "Compiled evidence file"
    elif "compiled_evidence_replay_manifest" in lower:
        label = "Evidence replay manifest"
    elif "evidence_fetch_manifest" in lower:
        label = "Evidence-fetch manifest"
    elif "forensic_workbench_evidence_fetches" in lower:
        label = "Evidence-fetch ledger"
    elif "forensic_workbench_latest_evidence_fetch" in lower:
        label = "Latest evidence fetch"
    elif "report_support_contract" in lower:
        label = "Report readiness file"
    elif "forensic_workbench_report_support_checks" in lower:
        label = "Report readiness history"
    elif "forensic_workbench_latest_report_support_check" in lower:
        label = "Latest report readiness record"
    elif "/raw/source_type_map.json" in lower:
        label = "Source role map"
    elif "/raw/" in lower:
        label = "Source file"
    elif "source_index_receipt" in lower:
        label = "File-index history"
    elif "source_index.json" in lower:
        label = "File index"
    elif "workspace_meta.json" in lower:
        label = "Workspace metadata"
    elif "evidence_output_binding_receipt" in lower:
        label = "Evidence connection history"
    elif "evidence_gap_resolutions" in lower:
        label = "Evidence-gap history"
    elif "iteration_telemetry" in lower:
        label = "Run telemetry"
    elif "latest_eval_results" in lower:
        label = "Latest run result"
    elif "eval_results" in lower:
        label = "Run result history"
    elif "forensic_workbench_applied" in lower and "_review_" in lower:
        label = "Review handoff file"
    elif "forensic_workbench_reviews" in lower:
        label = "Review ledger"
    elif "forensic_workbench_latest_review" in lower:
        label = "Latest review"
    elif "forensic_workbench_applied" in lower and "_action_" in lower:
        label = "Next-step handoff file"
    elif "forensic_workbench_row_actions" in lower:
        label = "Next-step ledger"
    elif "forensic_workbench_latest_row_action" in lower:
        label = "Latest next step"
    elif "forensic_workbench_intake_edits" in lower:
        label = "Project-brief ledger"
    elif "forensic_workbench_latest_intake_edit" in lower:
        label = "Latest project-brief change"
    elif "forensic_workbench_source_imports" in lower:
        label = "Source-add ledger"
    elif "forensic_workbench_latest_source_import" in lower:
        label = "Latest added file"
    elif "forensic_workbench_source_edits" in lower:
        label = "Source-edit ledger"
    elif "forensic_workbench_latest_source_edit" in lower:
        label = "Latest edited file"
    elif "forensic_workbench_source_actions" in lower:
        label = "File-check ledger"
    elif "forensic_workbench_latest_source_action" in lower:
        label = "Latest file check"
    elif "forensic_workbench_project_file_" in lower or "forensic_workbench_case_file_" in lower:
        label = "Project file"
    elif "forensic_workbench_project_files" in lower or "forensic_workbench_case_files" in lower:
        label = "Project-file ledger"
    elif "forensic_workbench_latest_project_file_write" in lower or "forensic_workbench_latest_case_file_write" in lower:
        label = "Latest project file"
    elif "forensic_workbench_claim_cards" in lower:
        label = "Claim-card history"
    elif "forensic_workbench_latest_claim_card" in lower:
        label = "Latest claim card"
    elif "ztare_proofs/leanmill-formalizations/blueprints" in lower:
        label = "LeanMill target and notes"
    elif "leanmill_blueprint_receipts" in lower:
        label = "LeanMill target-save history"
    elif "latest_leanmill_blueprint" in lower:
        label = "Latest LeanMill target"
    elif path.endswith("/workspace"):
        label = "Workspace folder"
    elif path.endswith("/raw"):
        label = "Source folder"
    elif path.startswith("projects/") and "/" not in path[len("projects/") :]:
        label = "Project folder"
    else:
        label = "File path"
    return {"label": label, "path_template": path}


def safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def tail_text(value: str, *, max_chars: int = 4000) -> str:
    value = value or ""
    if len(value) <= max_chars:
        return value
    return value[-max_chars:]


def tail_display_text(value: str, *, max_chars: int = 4000) -> str:
    return display_text(tail_text(value, max_chars=max_chars))


def text_lines(value: Any, *, limit: int = 20) -> list[str]:
    if isinstance(value, list):
        raw = value
    else:
        raw = str(value or "").splitlines()
    return [str(item).strip() for item in raw if str(item).strip()][:limit]


def display_text_lines(value: Any, *, limit: int = 20) -> list[str]:
    return [display_text(item) for item in text_lines(value, limit=limit)]


def report_issue_text(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("reason") or value.get("label") or value.get("id") or "").strip()
    return str(value or "").strip()


def report_support_issues(payload: dict[str, Any], binding: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    seen_issue_keys: set[tuple[str, str]] = set()
    raw_blockers = payload.get("blockers") or []
    raw_status_reasons = payload.get("status_reasons") or []
    runtime_risks = text_lines(payload.get("runtime_risks") or [], limit=4)
    for index, raw in enumerate(raw_blockers or raw_status_reasons):
        text = report_issue_text(raw)
        if not text:
            continue
        issue_id = raw.get("id") if isinstance(raw, dict) else f"report_issue_{index + 1}"
        status = raw.get("status") if isinstance(raw, dict) else "needs_support"
        display_reason = display_status(text)
        why_it_matters = ""
        what_to_check = ""
        done_when = ""
        if text == "runtime_risks_present" and runtime_risks:
            display_reason = f"Run coverage is still thin: {runtime_risks[0]}"
            why_it_matters = (
                "The report can be reviewed, but it should not be treated as final "
                "until the open run/frontier risk is checked or explicitly deferred."
            )
            what_to_check = (
                "Open the report readiness file and run or record the next allowed "
                "check named there."
            )
            done_when = (
                "A saved review or next-step record explains whether the runtime "
                "risk was resolved, deferred, or left as a report hold."
            )
        issue_key = (str(status or "needs_support"), text)
        if issue_key in seen_issue_keys:
            continue
        seen_issue_keys.add(issue_key)
        issue = {
            "id": str(issue_id or f"report_issue_{index + 1}"),
            "status": str(status or "needs_support"),
            "display_status": display_status(status or "needs_support"),
            "reason": text,
            "display_reason": display_reason,
        }
        if why_it_matters:
            issue["why_it_matters"] = why_it_matters
        if what_to_check:
            issue["what_to_check"] = what_to_check
        if done_when:
            issue["done_when"] = done_when
        if runtime_risks and text == "runtime_risks_present":
            issue["runtime_risks"] = runtime_risks
        issues.append(issue)
    if binding.get("status") == "unbound" and binding.get("reason"):
        binding_reason = str(binding.get("reason") or "")
        if not any(issue.get("reason") == binding_reason for issue in issues):
            issues.append(
                {
                    "id": "synthesis_input_binding",
                    "status": "unbound",
                    "display_status": display_status("unbound"),
                    "reason": binding_reason,
                    "display_reason": display_status(binding_reason),
                }
            )
    return issues


def normalize_report_action_command(
    command: str,
    *,
    project: str | None = None,
    rubric: str | None = None,
    intake: str | None = None,
) -> str:
    text = str(command or "").strip()
    if not text or not project:
        return text
    try:
        parts = shlex.split(text)
    except ValueError:
        return text
    if len(parts) >= 3 and parts[:3] == ["ztare", "autoresearch", "run"]:
        parts = set_cli_option(parts, "--project", "")
        parts = set_cli_option(parts, "--rubric", "")
        parts = set_cli_option(parts, "--intake", "")
        scoped_parts = parts[:3] + ["--project", project, "--rubric", rubric or project]
        if intake:
            scoped_parts.extend(["--intake", intake])
        scoped_parts.extend(parts[3:])
        return apply_run_settings_to_autoresearch_command(" ".join(shlex.quote(part) for part in scoped_parts), project)
    if len(parts) >= 3 and parts[:3] in (
        ["ztare", "autoresearch", "health"],
        ["ztare", "autoresearch", "projection"],
    ):
        is_health = parts[:3] == ["ztare", "autoresearch", "health"]
        parts = set_cli_option(parts, "--project", "")
        parts = set_cli_option(parts, "--rubric", "")
        if is_health:
            parts = set_cli_option(parts, "--intake", "")
        scoped_parts = parts[:3] + ["--project", project, "--rubric", rubric or project]
        if intake and is_health:
            scoped_parts.extend(["--intake", intake])
        scoped_parts.extend(parts[3:])
        return " ".join(shlex.quote(part) for part in scoped_parts)
    if len(parts) >= 4 and parts[:4] == ["ztare", "project", "intake", "validate"]:
        if intake:
            parts = set_cli_option(parts, "--path", "")
            parts = parts[:4] + ["--path", intake] + parts[4:]
        return " ".join(shlex.quote(part) for part in parts)
    return text


def compact_report_allowed_actions(
    payload: dict[str, Any],
    *,
    project: str | None = None,
    rubric: str | None = None,
    intake: str | None = None,
    limit: int = 8,
) -> list[dict[str, Any]]:
    authority = payload.get("report_action_authority") if isinstance(payload.get("report_action_authority"), dict) else {}
    rows = authority.get("allowed_now") if isinstance(authority.get("allowed_now"), list) else []
    actions: list[dict[str, str]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        label = str(row.get("label") or "").strip()
        if not label:
            continue
        clean_label, command = split_report_action_command(label)
        command = normalize_report_action_command(command, project=project, rubric=rubric, intake=intake)
        if not command:
            command = inferred_project_test_command(project or "", clean_label)
        source = str(row.get("source") or "")
        backing_refs = report_allowed_action_backing_refs(project or "", clean_label, source) if project else []
        workspace, subsection, primary_label = report_allowed_action_destination(command, label=clean_label)
        actions.append(
            {
                "id": str(row.get("action_id") or ""),
                "label": display_guidance_text(clean_label),
                "source": source,
                "evidence_refs": [ref["path"] for ref in backing_refs],
                "display_evidence_refs": backing_refs,
                "command": command,
                "workspace": workspace,
                "subsection": subsection,
                "primary_label": primary_label,
                "write_boundary": report_allowed_action_write_boundary(project or "", command),
            }
        )
        if len(actions) >= limit:
            break
    return actions


def first_runnable_report_action(actions: list[dict[str, str]]) -> dict[str, str] | None:
    for action in actions:
        if not isinstance(action, dict):
            continue
        if report_action_completed(action):
            continue
        command = str(action.get("command") or "").strip()
        if not command:
            continue
        workspace, _, _ = report_allowed_action_destination(command)
        if workspace == "run":
            return action
    return None


def report_action_completed(action: dict[str, Any]) -> bool:
    return str(action.get("status") or "") == "completed" or bool(action.get("completed_by"))


def first_open_report_action(actions: list[dict[str, Any]]) -> dict[str, Any] | None:
    for action in actions:
        if isinstance(action, dict) and not report_action_completed(action):
            return action
    return None


def report_action_completion_summary(action: dict[str, Any], receipt: dict[str, Any]) -> str:
    return project_check_core.report_action_completion_summary(action, receipt)


def completed_report_action_summary_for_change(
    actions: list[dict[str, Any]],
    change: dict[str, Any],
) -> str:
    return project_check_core.completed_report_action_summary_for_change(actions, change)


def enrich_recent_project_check_summary(
    recent_changes: dict[str, Any],
    actions: list[dict[str, Any]],
) -> dict[str, Any]:
    return project_check_core.enrich_recent_project_check_summary(recent_changes, actions)


def split_report_action_command(label: str) -> tuple[str, str]:
    text = str(label or "").strip()
    command_start = text.find("ztare ")
    if command_start < 0:
        return text, ""
    command = text[command_start:].strip()
    try:
        parts = shlex.split(command)
    except ValueError:
        return text, ""
    if len(parts) < 2 or parts[0] != "ztare":
        return text, ""
    prefix = text[:command_start].strip(" .:")
    if not prefix:
        prefix = command
    return prefix, command


def inferred_project_test_command(project: str, label: str) -> str:
    return project_check_core.inferred_project_test_command(project, label, root=snapshot.REPO)


def project_test_path_from_command(command: str) -> str:
    return project_check_core.project_test_path_from_command(
        command,
        root=snapshot.REPO,
        python_executable=SERVER_PYTHON,
    )


def passed_project_test_for_action(action: dict[str, Any], receipt_rows: list[dict[str, Any]]) -> dict[str, Any]:
    return project_check_core.passed_project_test_for_action(
        action,
        receipt_rows,
        root=snapshot.REPO,
        python_executable=SERVER_PYTHON,
    )


def annotate_completed_report_actions(
    actions: list[dict[str, Any]],
    receipt_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return project_check_core.annotate_completed_report_actions(
        actions,
        receipt_rows,
        root=snapshot.REPO,
        python_executable=SERVER_PYTHON,
    )


def report_allowed_action_destination(command: str, *, label: str = "") -> tuple[str, str, str]:
    try:
        parts = shlex.split(str(command or ""))
    except ValueError:
        return "save", "Report readiness", "Open report readiness"
    if len(parts) >= 3 and parts[:3] == ["ztare", "autoresearch", "run"]:
        if "--preflight-only" in parts:
            return "run", "Check readiness", "Check readiness"
        return "run", "Start run", "Start run"
    if len(parts) >= 3 and parts[:3] == ["ztare", "autoresearch", "projection"]:
        return "run", "Ready to run", "Open pressure-test"
    if len(parts) >= 3 and parts[:3] == ["ztare", "autoresearch", "health"]:
        return "run", "Fix warnings", "Open warnings"
    if len(parts) >= 2 and parts[0] in {"python", "python3", SERVER_PYTHON} and str(parts[-1]).endswith("/test_model.py"):
        return "run", "Ready to run", "Run project test"
    label_text = str(label or "").lower()
    if "preflight" in label_text:
        return "run", "Check readiness", "Open readiness check"
    if "projection" in label_text or "loop results" in label_text or "run history" in label_text:
        return "run", "Ready to run", "Open pressure-test"
    if "evidence health" in label_text or "claim-support" in label_text or "stale artifact" in label_text:
        return "run", "Fix warnings", "Open warnings"
    if "validation run" in label_text or "in-loop validation" in label_text or "parameter-space test" in label_text:
        return "run", "Start run", "Open readiness"
    return "save", "Report readiness", "Open report readiness"


def report_allowed_action_backing_refs(project: str, label: str, source: str) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []

    def add(label_text: str, path: str) -> None:
        normalized = PurePosixPath(str(path or "").strip()).as_posix()
        if normalized and preview_path_allowed(normalized):
            refs.append({"label": label_text, "path": normalized})

    project_root = snapshot.REPO / "projects" / project
    label_text = str(label or "").lower()
    source_text = str(source or "")
    if source_text and not preview_path_allowed(source_text):
        add("Report readiness file", f"projects/{project}/synthesis/report_support_contract.json")
    if "parameter" in label_text and "cache" in label_text:
        for label_text_item, relative in [
            ("Fixture discriminator", "test_model.py"),
            ("Cache isolation source", "raw/cache_isolation_check.md"),
            ("Generation-rule audit", "raw/S009_generation_rules.md"),
            ("Evidence-gap state", "workspace/champion_evidence_gaps.json"),
        ]:
            path = project_root / relative
            if path.exists():
                add(label_text_item, repo_rel(path))
    if "evidence health" in label_text or "claim-support" in label_text or "stale artifact" in label_text:
        for label_text_item, relative in [
            ("Compiled evidence", "compiled_evidence_packet.json"),
            ("Evidence provenance", "compiled_evidence_provenance.json"),
            ("Source index", "workspace/source_index.json"),
        ]:
            path = project_root / relative
            if path.exists():
                add(label_text_item, repo_rel(path))
    if not refs and source_text and preview_path_allowed(source_text):
        add("Backing file", source_text)
    seen: set[str] = set()
    unique: list[dict[str, str]] = []
    for ref in refs:
        path = ref["path"]
        if path in seen:
            continue
        seen.add(path)
        unique.append(ref)
    return unique


def unique_display_evidence_refs(refs: list[Any]) -> list[dict[str, str]]:
    seen: set[str] = set()
    unique: list[dict[str, str]] = []
    for ref in refs:
        if not isinstance(ref, dict):
            continue
        path = str(ref.get("path") or "")
        if not path or path in seen:
            continue
        seen.add(path)
        unique.append({"label": str(ref.get("label") or "Backing evidence"), "path": path})
    return unique


def report_allowed_action_write_boundary(project: str, command: str) -> dict[str, Any] | None:
    try:
        parts = shlex.split(str(command or ""))
    except ValueError:
        return None
    if len(parts) >= 3 and parts[:3] == ["ztare", "autoresearch", "run"]:
        write_paths = [f"projects/{project}/workspace/iteration_telemetry.jsonl"]
        return write_boundary_payload(
            writes_project_files=True,
            write_paths=write_paths,
            receipt_path=write_paths[0],
            read_only_actions=["inspect readiness", "copy command"],
        )
    if len(parts) >= 2 and parts[0] in {"python", "python3", SERVER_PYTHON} and str(parts[-1]).endswith("/test_model.py"):
        write_paths = [
            f"projects/{project}/workspace/forensic_workbench_project_tests.jsonl",
            f"projects/{project}/workspace/forensic_workbench_latest_project_test.json",
        ]
        return write_boundary_payload(
            writes_project_files=True,
            write_paths=write_paths,
            receipt_path=write_paths[0],
            latest_path=write_paths[1],
            read_only_actions=["preview test file", "copy command"],
        )
    return write_boundary_payload(
        writes_project_files=False,
        read_only_actions=["inspect report readiness", "copy command", "save review after doing it"],
    )


def compact_report_authority_rows(
    payload: dict[str, Any],
    key: str,
    *,
    limit: int = 4,
) -> list[dict[str, str]]:
    authority = payload.get("report_action_authority") if isinstance(payload.get("report_action_authority"), dict) else {}
    rows = authority.get(key) if isinstance(authority.get(key), list) else []
    actions: list[dict[str, str]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        label = str(row.get("label") or "").strip()
        if not label:
            continue
        actions.append(
            {
                "id": str(row.get("action_id") or ""),
                "label": display_guidance_text(label),
                "source": str(row.get("source") or ""),
                "condition": display_guidance_text(row.get("condition") or ""),
            }
        )
        if len(actions) >= limit:
            break
    return actions


def report_workflow_detail(report: dict[str, Any]) -> str:
    allowed_actions = report.get("allowed_actions") if isinstance(report.get("allowed_actions"), list) else []
    for action in allowed_actions:
        if not isinstance(action, dict):
            continue
        label = str(action.get("label") or "").strip()
        if label:
            return display_guidance_text(f"Next report action: {label}")
    support_issues = report.get("support_issues") if isinstance(report.get("support_issues"), list) else []
    report_allowed_actions = report.get("allowed_actions") if isinstance(report.get("allowed_actions"), list) else []
    for issue in support_issues:
        if not isinstance(issue, dict):
            continue
        reason = str(issue.get("display_reason") or issue.get("reason") or "").strip()
        if reason:
            return display_guidance_text(reason)
    display_reasons = report.get("display_status_reasons") if isinstance(report.get("display_status_reasons"), list) else []
    for reason in display_reasons:
        text = str(reason or "").strip()
        if text:
            return display_guidance_text(text)
    reasons = report.get("status_reasons") if isinstance(report.get("status_reasons"), list) else []
    for reason in reasons:
        text = str(reason or "").strip()
        if text:
            return display_status(text)
    status = str(report.get("status") or "")
    return display_status(status) if status else "report readiness not loaded"


def report_contract_blockers(report_path: str) -> list[Any]:
    if not report_path:
        return []
    try:
        path = (snapshot.REPO / report_path).resolve()
        path.relative_to(snapshot.REPO.resolve())
        payload = read_json_object(path, "report support contract")
    except (OSError, ValueError, json.JSONDecodeError):
        return []
    blockers = payload.get("blockers")
    return blockers if isinstance(blockers, list) else []


def report_action_cli_display(project: str, action: str, renderer: str) -> str:
    return display_command(
        [
            "ztare",
            "forensic-workbench",
            "report-action",
            "--project",
            project,
            "--action",
            action,
            "--renderer",
            renderer,
            "--confirmed",
            "--json",
        ]
    )


def report_synthesis_needed(support_issues: list[dict[str, Any]]) -> bool:
    binding_statuses = {"unbound", "digest_mismatch", "path_mismatch"}
    for issue in support_issues:
        if not isinstance(issue, dict):
            continue
        if issue.get("id") == "synthesis_input_binding" and str(issue.get("status") or "") in binding_statuses:
            return True
        reason = str(issue.get("reason") or "")
        if "synthesis_input_binding_" in reason or "content-hash binding" in reason:
            return True
    return False


def report_repair_actions(
    *,
    project: str,
    rubric: str | None,
    intake: str | None,
    renderer: str,
    report_contract: str,
    command: str,
    allowed_actions: list[dict[str, str]],
    support_issues: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    if allowed_actions:
        first = allowed_actions[0]
        command_text = normalize_report_action_command(first.get("command") or "", project=project, rubric=rubric, intake=intake)
        workspace, subsection, primary_label = report_allowed_action_destination(
            command_text,
            label=str(first.get("label") or ""),
        )
        actions.append(
            {
                "id": "follow_report_next_action",
                "label": "Do next report action",
                "detail": display_guidance_text(str(first.get("label") or "Follow the report readiness next action.")),
                "workspace": workspace,
                "subsection": subsection,
                "primary_label": primary_label,
                "source": str(first.get("source") or report_contract),
                "receipt_paths": [report_contract] if report_contract else [],
                "command": command_text,
                "writes_project_files": bool(command_text and " autoresearch run " in f" {command_text} "),
            }
        )
        runnable_action = first_runnable_report_action(allowed_actions)
        if runnable_action and runnable_action is not first:
            command_text = normalize_report_action_command(
                runnable_action.get("command") or "",
                project=project,
                rubric=rubric,
                intake=intake,
            )
            workspace, subsection, primary_label = report_allowed_action_destination(
                command_text,
                label=str(runnable_action.get("label") or ""),
            )
            actions.append(
                {
                    "id": "run_report_allowed_check",
                    "label": primary_label,
                    "detail": display_guidance_text(str(runnable_action.get("label") or "Run the report readiness check.")),
                    "workspace": workspace,
                    "subsection": subsection,
                    "primary_label": primary_label,
                    "source": str(runnable_action.get("source") or report_contract),
                    "receipt_paths": [report_contract] if report_contract else [],
                    "command": command_text,
                    "writes_project_files": bool(command_text and " autoresearch run " in f" {command_text} "),
                }
            )
    elif support_issues:
        first_issue = support_issues[0]
        actions.append(
            {
                "id": "inspect_report_issue",
                "label": "Inspect report readiness issue",
                "detail": display_guidance_text(str(first_issue.get("display_reason") or first_issue.get("reason") or "")),
                "workspace": "save",
                "subsection": "Report readiness",
                "primary_label": "Open issue",
                "source": report_contract,
                "receipt_paths": [report_contract] if report_contract else [],
                "command": "",
                "writes_project_files": False,
            }
        )
    if report_synthesis_needed(support_issues):
        actions.append(
            {
                "id": "refresh_report_inputs",
                "label": "Refresh report inputs",
                "detail": "Rebuild the report ledger and support contract from current project files.",
                "workspace": "save",
                "subsection": "Report inputs",
                "primary_label": "Preview full refresh",
                "source": report_contract,
                "receipt_paths": [
                    report_contract,
                    f"projects/{project}/workspace/forensic_workbench_report_synthesis.jsonl",
                    f"projects/{project}/workspace/forensic_workbench_latest_report_synthesis.json",
                ],
                "command": report_action_cli_display(project, "refresh_inputs", renderer),
                "writes_project_files": True,
                "requires_confirmation": True,
            }
        )
    actions.append(
        {
            "id": "rerun_report_support",
            "label": "Check report readiness",
            "detail": "Refresh the report readiness file from current project files, then review the new status.",
            "workspace": "save",
            "subsection": "Report readiness",
            "primary_label": "Preview refresh",
            "source": report_contract,
            "receipt_paths": [
                report_contract,
                f"projects/{project}/workspace/forensic_workbench_report_support_checks.jsonl",
                f"projects/{project}/workspace/forensic_workbench_latest_report_support_check.json",
            ],
            "command": report_action_cli_display(project, "check_readiness", renderer),
            "writes_project_files": True,
            "requires_confirmation": True,
        }
    )
    actions.append(
        {
            "id": "save_report_review",
            "label": "Save review",
            "detail": "Record whether the report issue is reviewed, deferred, or still holding the report.",
            "workspace": "review",
            "subsection": "Save review",
            "primary_label": "Save review",
            "source": report_contract,
            "receipt_paths": [
                f"projects/{project}/workspace/forensic_workbench_reviews.jsonl",
                f"projects/{project}/workspace/forensic_workbench_latest_review.json",
            ],
            "command": "",
            "writes_project_files": True,
        }
    )
    return actions


def receipt_matches_case(row: dict[str, Any], *, project: str, intake: str | None = None) -> bool:
    if row.get("project") and row.get("project") != project:
        return False
    intake_value = str(intake or "").strip()
    if not intake_value:
        return True
    row_case_key = str(row.get("project_key") or row.get("case_key") or "").strip()
    if row_case_key:
        return row_case_key == case_key(project, intake_value)
    row_intake = str(row.get("intake") or "").strip()
    if row_intake:
        return row_intake == intake_value
    return True


def latest_receipt_by_kind(receipts: list[dict[str, Any]], kinds: set[str]) -> dict[str, Any]:
    for receipt in receipts:
        if str(receipt.get("kind") or "") in kinds:
            return receipt
    return {}


def compact_receipt_digest_row(label: str, receipt: dict[str, Any], empty: str) -> dict[str, Any]:
    if not receipt:
        return {
            "label": label,
            "status": "missing",
            "summary": empty,
            "receipt_path": "",
            "artifact_path": "",
            "applied_at": "",
            "kind": "",
        }
    artifact_path = str(
        receipt.get("review_file_path")
        or receipt.get("action_file_path")
        or receipt.get("project_file_path")
        or receipt.get("case_file_path")
        or receipt.get("source_path")
        or receipt.get("intake_path")
        or receipt.get("manifest_path")
        or receipt.get("report_support_contract")
        or receipt.get("html_path")
        or receipt.get("markdown_path")
        or receipt.get("json_path")
        or receipt.get("test_path")
        or receipt.get("source_receipt_path")
        or ""
    )
    return {
        "label": label,
        "status": "recorded",
        "kind": str(receipt.get("kind") or ""),
        "summary": str(receipt.get("display_summary") or receipt.get("summary") or ""),
        "receipt_path": str(receipt.get("path") or ""),
        "artifact_path": artifact_path,
        "applied_at": str(receipt.get("applied_at") or ""),
        "target": display_guidance_text(
            receipt.get("check_label")
            or receipt.get("display_label")
            or receipt.get("item_label")
            or receipt.get("project_check_label")
            or receipt.get("row")
            or ""
        ),
    }


def compact_run_change_row(run_history: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(run_history, dict):
        run_history = {}
    summary = run_history.get("summary") if isinstance(run_history.get("summary"), dict) else {}
    paths = run_history.get("paths") if isinstance(run_history.get("paths"), dict) else {}
    run_count = safe_int(summary.get("run_rows"))
    latest_score = summary.get("latest_score")
    latest_run_id = summary.get("latest_run_id")
    latest_iteration = summary.get("latest_iteration")
    latest_timestamp = str(summary.get("latest_timestamp") or "")
    latest_gap_count = safe_int(summary.get("latest_evidence_gap_count"))
    weakest = str(summary.get("latest_weakest_point") or "")
    if not run_count and latest_score is None:
        return {
            "label": "Latest run",
            "status": "missing",
            "summary": "No project run saved yet.",
            "receipt_path": "",
            "artifact_path": "",
            "applied_at": "",
            "kind": "",
        }
    score_text = "no score" if latest_score is None else f"score {latest_score}"
    latest_eval_path = str(paths.get("latest_eval") or "")
    latest_eval_abs = snapshot.REPO / latest_eval_path if latest_eval_path else None
    if latest_eval_abs and latest_eval_abs.exists():
        latest_timestamp = datetime.fromtimestamp(
            latest_eval_abs.stat().st_mtime,
            tz=timezone.utc,
        ).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    run_label = f"run {latest_run_id}" if latest_run_id else "latest run"
    if latest_iteration is not None:
        run_label = f"{run_label}, iteration {latest_iteration}"
    gap_text = f"; {latest_gap_count} evidence gap{'s' if latest_gap_count != 1 else ''}" if latest_gap_count else ""
    weak_text = f"; weakest point: {compact_recent_text(weakest, 150)}" if weakest else ""
    return {
        "label": "Latest run",
        "status": "recorded",
        "kind": "project_run",
        "summary": f"{display_text(run_label)} recorded {score_text}{gap_text}{weak_text}.",
        "receipt_path": str(paths.get("iteration_telemetry") or ""),
        "artifact_path": latest_eval_path,
        "applied_at": latest_timestamp,
        "target": "Project run",
    }


change_row_time = recent_changes_core.change_row_time


def compact_recent_text(value: Any, limit: int = 150) -> str:
    text = display_text(value)
    return text if len(text) <= limit else f"{text[: max(0, limit - 1)].rstrip()}…"


recent_change_inspection_reason = recent_changes_core.recent_change_inspection_reason
recent_change_inspection_target = recent_changes_core.recent_change_inspection_target


def project_recent_changes_payload(receipts: dict[str, Any], run_history: dict[str, Any] | None = None) -> dict[str, Any]:
    """Compact recent-change state for project handoff and UI recovery."""

    receipt_rows = receipts.get("receipts") if isinstance(receipts.get("receipts"), list) else []
    summary = receipts.get("summary") if isinstance(receipts.get("summary"), dict) else receipt_history_summary(receipt_rows)
    summary_rows = summary.get("rows") if isinstance(summary.get("rows"), list) else []

    def row_by_label(label: str) -> dict[str, Any]:
        for row in summary_rows:
            if isinstance(row, dict) and str(row.get("label") or "") == label:
                return row
        return {}

    latest_review = row_by_label("Latest review")
    latest_next_step = row_by_label("Latest next step")
    latest_source_or_evidence_change = row_by_label("Latest source or evidence change")
    latest_project_check = row_by_label("Latest project test")
    latest_project_file = row_by_label("Latest project file")
    latest_run = compact_run_change_row(run_history or {})
    latest_receipt = receipt_rows[0] if receipt_rows and isinstance(receipt_rows[0], dict) else {}
    recorded_count = safe_int(summary.get("recorded_count"))
    change_rows = [row for row in [*summary_rows, latest_run] if isinstance(row, dict)]
    recorded_rows = [row for row in change_rows if row.get("status") == "recorded"]
    latest_change = max(recorded_rows, key=change_row_time) if recorded_rows else {}
    next_inspection = recent_change_inspection_target(latest_change, latest_receipt)
    substantive_rows = [
        row
        for row in [latest_source_or_evidence_change, latest_project_check, latest_run]
        if isinstance(row, dict) and row.get("status") == "recorded"
    ]
    latest_substantive_change = max(substantive_rows, key=change_row_time) if substantive_rows else {}
    substantive_inspection = recent_change_inspection_target(latest_substantive_change, latest_receipt)
    return {
        "schema": "ztare-project-recent-changes-v1",
        "status": "recorded" if recorded_rows else "none recorded",
        "recorded_count": len(recorded_rows),
        "receipt_count": len(receipt_rows),
        "latest_receipt_path": str(latest_change.get("receipt_path") or latest_receipt.get("path") or ""),
        "latest_receipt_summary": str(
            latest_change.get("summary")
            or latest_receipt.get("display_summary")
            or latest_receipt.get("summary")
            or ""
        ),
        "latest_review": latest_review,
        "latest_next_step": latest_next_step,
        "latest_source_or_evidence_change": latest_source_or_evidence_change,
        "latest_project_check": latest_project_check,
        "latest_run": latest_run,
        "latest_project_file": latest_project_file,
        "summary": str(latest_change.get("summary") or "No saved project changes yet."),
        "next_inspection": next_inspection,
        "substantive_inspection": substantive_inspection,
        "changes": change_rows,
    }


def receipt_history_summary(receipts: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [
        compact_receipt_digest_row("Latest review", latest_receipt_by_kind(receipts, {"review"}), "No review saved yet."),
        compact_receipt_digest_row(
            "Latest next step",
            latest_receipt_by_kind(receipts, {"row_action", "next_step"}),
            "No next step saved yet.",
        ),
        compact_receipt_digest_row(
            "Latest source or evidence change",
            latest_receipt_by_kind(
                receipts,
                {"charter_edit", "source_action", "source_import", "source_edit", "evidence_fetch", "evidence_gap_resolution", "report_synthesis", "report_support_refresh", "claim_card"},
            ),
            "No source or evidence change saved yet.",
        ),
        compact_receipt_digest_row(
            "Latest project test",
            latest_receipt_by_kind(receipts, {"project_test"}),
            "No project test saved yet.",
        ),
        compact_receipt_digest_row("Latest project file", latest_receipt_by_kind(receipts, {"case_file", "project_file"}), "No project file saved yet."),
    ]
    return {
        "schema": "ztare-forensic-workbench-receipt-history-summary-v1",
        "recorded_count": sum(1 for row in rows if row["status"] == "recorded"),
        "rows": rows,
    }


def receipt_history_payload(*, project: str, limit: int = 12, intake: str | None = None) -> dict[str, Any]:
    project = snapshot.validate_project_slug(project)
    limit = max(1, min(limit, 50))
    workspace = snapshot.REPO / "projects" / project / "workspace"
    ledgers = {
        "review": workspace / "forensic_workbench_reviews.jsonl",
        "row_action": workspace / "forensic_workbench_row_actions.jsonl",
        "charter_edit": workspace / "forensic_workbench_charter_edits.jsonl",
        "intake_edit": workspace / "forensic_workbench_intake_edits.jsonl",
        "source_import": workspace / "forensic_workbench_source_imports.jsonl",
        "source_edit": workspace / "forensic_workbench_source_edits.jsonl",
        "source_action": workspace / "forensic_workbench_source_actions.jsonl",
        "evidence_fetch": workspace / "forensic_workbench_evidence_fetches.jsonl",
        "report_synthesis": workspace / "forensic_workbench_report_synthesis.jsonl",
        "report_support_refresh": workspace / "forensic_workbench_report_support_checks.jsonl",
        "claim_card": workspace / "forensic_workbench_claim_cards.jsonl",
        "project_test": workspace / "forensic_workbench_project_tests.jsonl",
        "project_file": workspace / "forensic_workbench_project_files.jsonl",
    }
    paths = {kind: repo_rel(path) for kind, path in ledgers.items()}
    paths["case_file"] = paths["project_file"]
    paths["case_file_compatibility"] = repo_rel(workspace / "forensic_workbench_case_files.jsonl")
    paths["evidence_gap_resolution"] = repo_rel(workspace / "evidence_gap_resolutions.json")
    paths["next_step"] = paths["row_action"]
    paths["project_check"] = paths["project_test"]
    paths["item_action"] = paths["row_action"]
    receipts: list[dict[str, Any]] = []
    for kind, path in ledgers.items():
        receipts.extend(read_receipt_ledger(path, kind=kind))
    receipts.extend(read_receipt_ledger(workspace / "forensic_workbench_case_files.jsonl", kind="case_file"))
    receipts.extend(read_evidence_gap_resolution_receipts(workspace / "evidence_gap_resolutions.json"))
    total_receipt_count = len(receipts)
    receipts = [row for row in receipts if receipt_matches_case(row, project=project, intake=intake)]
    receipts.sort(key=lambda row: (str(row.get("applied_at") or ""), str(row.get("kind") or ""), int(row.get("line") or 0)), reverse=True)
    summary = receipt_history_summary(receipts)
    return {
        "schema": RECEIPT_HISTORY_SCHEMA,
        "ok": True,
        "served_from": "local_api",
        "project": project,
        "intake": str(intake or ""),
        "limit": limit,
        "receipt_count": len(receipts),
        "total_receipt_count": total_receipt_count,
        "receipts": receipts[:limit],
        "summary": summary,
        "paths": paths,
    }


def apply_intake_edit(*, project: str, intake: str | None, raw_patch: Any, rubric: str | None = None) -> dict[str, Any]:
    project = snapshot.validate_project_slug(project)
    rubric = rubric or project
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json") as staged:
        json.dump(raw_patch, staged)
        staged.flush()
        args = [
            "forensic-workbench", "brief-edit",
            "--project", project,
            "--rubric", rubric,
            "--patch-file", staged.name,
            "--repo", str(snapshot.REPO),
            "--json",
        ]
        if intake:
            args.extend(["--intake", intake])
        payload = ztare_cli_payload(args, project=project, timeout=90)
    if payload.get("ok") is False:
        raise ValueError(str(payload.get("error") or "project brief edit was refused"))
    intake_rel = str(payload.get("intake_path") or intake or snapshot.default_intake_for_project(project))
    return {
        "ok": True,
        "intake": intake_payload_for_project(project, intake_rel, allow_examples=False),
        "ledger": str(payload.get("ledger") or ""),
        "latest": str(payload.get("latest") or ""),
        "receipt": payload.get("receipt") or {},
        "write_boundary": write_boundary_payload(
            writes_project_files=True,
            write_paths=list(payload.get("write_paths") or []),
            receipt_path=str(payload.get("receipt_path") or payload.get("ledger") or ""),
            latest_path=str(payload.get("latest_path") or payload.get("latest") or ""),
        ),
    }


def charter_validation_payload(path: Path) -> dict[str, Any]:
    return project_charter_core.validation_payload(path, root=snapshot.REPO, storage=WORKBENCH_STORE)


def charter_payload_for_project(project: str) -> dict[str, Any]:
    project = snapshot.validate_project_slug(project)
    path = project_charter_path(project)
    text = WORKBENCH_STORE.read_text(path, errors="replace") if path.exists() else ""
    validation = charter_validation_payload(path)
    return {
        "schema": CHARTER_SCHEMA,
        "ok": path.exists(),
        "project": project,
        "path": repo_rel(path),
        "text": text,
        "exists": path.exists(),
        "editable": True,
        "validation": validation,
        "write_boundary": write_boundary_payload(
            writes_project_files=True,
            write_paths=[
                repo_rel(path),
                f"projects/{project}/workspace/forensic_workbench_charter_edits.jsonl",
                f"projects/{project}/workspace/forensic_workbench_latest_charter_edit.json",
            ],
            receipt_path=f"projects/{project}/workspace/forensic_workbench_charter_edits.jsonl",
            latest_path=f"projects/{project}/workspace/forensic_workbench_latest_charter_edit.json",
            read_only_actions=["read charter", "copy charter text"],
        ),
    }


def apply_charter_edit(*, project: str, text: str, rubric: str | None = None, intake: str | None = None) -> dict[str, Any]:
    project = snapshot.validate_project_slug(project)
    rubric = rubric or project
    intake_value = intake or snapshot.default_intake_for_project(project)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".md") as staged:
        staged.write(text)
        staged.flush()
        result = ztare_cli_payload([
            "forensic-workbench", "save-charter",
            "--project", project,
            "--rubric", rubric,
            "--intake", intake_value,
            "--from", staged.name,
            "--repo", str(snapshot.REPO),
            "--json",
        ], project=project, timeout=90)
    if result.get("ok") is False:
        raise ValueError(str(result.get("error") or "charter edit was refused"))
    return {
        "ok": True,
        "project": project,
        "charter": charter_payload_for_project(project),
        "ledger": str(result.get("ledger") or ""),
        "latest": str(result.get("latest") or ""),
        "receipt": result.get("receipt") or {},
        "write_boundary": write_boundary_payload(
            writes_project_files=True,
            write_paths=list(result.get("write_paths") or []),
            receipt_path=str(result.get("ledger") or ""),
            latest_path=str(result.get("latest") or ""),
        ),
    }


_SNAPSHOT_CACHE: "dict[tuple, tuple[float, dict]]" = {}  # (project,rubric,intake,renderer) -> (content_mtime, payload)


def _project_content_mtime(project: str) -> float:
    """Newest mtime across the project's files — the snapshot cache key. ANY project-local change (research map,
    evidence, a governed_overlay bind, a saved review) bumps it and invalidates the cache. Skips __pycache__/.git;
    O(files) stat calls (~ms) vs the ~9s rebuild it saves. ponytail: mtime-keyed is coarse but correct for
    project-local edits; global-state changes would need a manual Refresh (rare)."""
    root = snapshot.REPO / "projects" / project
    if not root.is_dir():
        return 0.0
    latest = 0.0
    for p in root.rglob("*"):
        # skip the build's OWN derived output (synthesis/*) — else every build bumps the key and the cache never
        # hits; INPUT files (research map, evidence, thesis, workspace/governed_overlay from a bind) still count.
        if "__pycache__" in p.parts or ".git" in p.parts or "synthesis" in p.parts:
            continue
        try:
            m = p.stat().st_mtime
        except OSError:
            continue
        if m > latest:
            latest = m
    return latest


def snapshot_payload_for_project(
    *,
    project: str,
    rubric: str | None = None,
    intake: str | None = None,
    renderer: str | None = None,
) -> dict[str, Any]:
    project = snapshot.validate_project_slug(project)
    rubric = rubric or project
    intake = intake or snapshot.default_intake_for_project(project)
    renderer = renderer or snapshot.DEFAULT_RENDERER
    # Cache the ~9s snapshot per project, keyed on the newest project-file mtime — a repeat load of an unchanged
    # project is instant; any project-local edit (incl. a bind writing governed_overlay.json) invalidates it.
    _cache_key = (project, rubric, intake, renderer)
    _mtime = _project_content_mtime(project)
    _cached = _SNAPSHOT_CACHE.get(_cache_key)
    if _cached is not None and _cached[0] == _mtime:
        return _cached[1]
    output_path = snapshot.REPO / snapshot.DEFAULT_OUT
    (
        _html,
        rows,
        trace,
        report_contract,
        latest_review,
        latest_review_path,
        latest_action,
        latest_action_path,
        latest_intake_edit,
        latest_intake_edit_path,
    ) = snapshot.build_snapshot(
        project,
        rubric,
        intake,
        renderer,
        output_path,
    )
    payload = snapshot.snapshot_payload(
        trace,
        report_contract,
        rows,
        output_path=output_path,
        latest_review=latest_review,
        latest_review_artifact_path=latest_review_path,
        latest_action=latest_action,
        latest_action_artifact_path=latest_action_path,
        latest_intake_edit=latest_intake_edit,
        latest_intake_edit_artifact_path=latest_intake_edit_path,
    )
    payload["ok"] = True
    payload["served_from"] = "local_api"
    _SNAPSHOT_CACHE[_cache_key] = (_mtime, payload)
    return payload


def review_payload_from_request(request: dict[str, Any]) -> dict[str, Any]:
    project = str(request.get("project") or "")
    rubric = str(request.get("rubric") or "") or None
    intake = str(request.get("intake") or "") or None
    row = str(request.get("project_check_slug") or request.get("item_slug") or request.get("row_slug") or "")
    review_file = request.get("review_file")
    if not isinstance(review_file, dict):
        raise ValueError("review_file must be a JSON object")
    review_errors = review.validate_review_file(review_file, project=project, row=row, intake=intake)
    if review_errors:
        raise ValueError("invalid review file: " + "; ".join(review_errors))
    review_file = live_project_check_payload(
        live_row_payload_with_case(review_file, project=project, rubric=rubric, intake=intake),
        slug=row,
    )
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json") as staged:
        json.dump(review_file, staged)
        staged.flush()
        args = [
            "forensic-workbench", "apply-review",
            "--project", project,
            "--project-check", row,
            "--from", staged.name,
            "--repo", str(snapshot.REPO),
            "--json",
        ]
        if intake:
            args.extend(["--intake", intake])
        review_result = ztare_cli_payload(args, project=project, timeout=90)
    if review_result.get("ok") is False:
        raise ValueError(str(review_result.get("error") or "review save was refused"))
    review_file_path = str(review_result.get("input_path") or (review_result.get("receipt") or {}).get("review_file_path") or "")
    response = {
        "ok": True,
        "review": review_result,
        "endpoint": "/api/review",
        "project_check_label": str(review_file.get("project_check_label") or review_file.get("item_label") or review_file.get("row") or ""),
        "project_check_slug": str(review_file.get("project_check_slug") or review_file.get("item_slug") or row),
        "item_slug": row,
        "row_slug": row,
        "write_boundary": write_boundary_payload(
            writes_project_files=True,
            write_paths=[
                review_file_path,
                str(review_result.get("ledger") or ""),
                str(review_result.get("latest") or ""),
            ],
            receipt_path=str(review_result.get("ledger") or ""),
            latest_path=str(review_result.get("latest") or ""),
        ),
        "snapshot": None,
    }
    try:
        response["snapshot"] = snapshot_payload_for_project(project=project, rubric=rubric, intake=intake)
    except SystemExit as exc:
        response["snapshot_error"] = display_text(exc)
    except Exception as exc:  # noqa: BLE001 - receipt write already succeeded.
        response["snapshot_error"] = display_text(exc)
    return response


def item_action_payload_from_request(request: dict[str, Any]) -> dict[str, Any]:
    project = str(request.get("project") or "")
    rubric = str(request.get("rubric") or "") or None
    intake = str(request.get("intake") or "") or None
    row = str(request.get("project_check_slug") or request.get("item_slug") or request.get("row_slug") or "")
    action_file = request.get("action_file")
    if not isinstance(action_file, dict):
        raise ValueError("action_file must be a JSON object")
    action_errors = review.validate_action_file(action_file, project=project, row=row, intake=intake)
    if action_errors:
        raise ValueError("invalid item action file: " + "; ".join(action_errors))
    action_file = live_project_check_payload(
        live_row_payload_with_case(action_file, project=project, rubric=rubric, intake=intake),
        slug=row,
    )
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json") as staged:
        json.dump(action_file, staged)
        staged.flush()
        args = [
            "forensic-workbench", "save-next-step",
            "--project", project,
            "--project-check", row,
            "--from", staged.name,
            "--repo", str(snapshot.REPO),
            "--json",
        ]
        if intake:
            args.extend(["--intake", intake])
        action_result = ztare_cli_payload(args, project=project, timeout=90)
    if action_result.get("ok") is False:
        raise ValueError(str(action_result.get("error") or "next-step save was refused"))
    action_file_path = str(action_result.get("input_path") or (action_result.get("receipt") or {}).get("action_file_path") or "")
    response = {
        "ok": True,
        "action": action_result,
        "endpoint": "/api/next-step",
        "project_check_label": str(action_file.get("project_check_label") or action_file.get("item_label") or action_file.get("row") or ""),
        "project_check_slug": str(action_file.get("project_check_slug") or action_file.get("item_slug") or row),
        "item_slug": row,
        "row_slug": row,
        "write_boundary": write_boundary_payload(
            writes_project_files=True,
            write_paths=[
                action_file_path,
                str(action_result.get("ledger") or ""),
                str(action_result.get("latest") or ""),
            ],
            receipt_path=str(action_result.get("ledger") or ""),
            latest_path=str(action_result.get("latest") or ""),
        ),
        "snapshot": None,
    }
    try:
        response["snapshot"] = snapshot_payload_for_project(project=project, rubric=rubric, intake=intake)
    except SystemExit as exc:
        response["snapshot_error"] = display_text(exc)
    except Exception as exc:  # noqa: BLE001 - receipt write already succeeded.
        response["snapshot_error"] = display_text(exc)
    return response


def report_contract_payload_for_project(
    *,
    project: str,
    rubric: str | None = None,
    intake: str | None = None,
    renderer: str | None = None,
) -> dict[str, Any]:
    project = snapshot.validate_project_slug(project)
    rubric = rubric or project
    intake = intake or snapshot.default_intake_for_project(project)
    if intake:
        project_intake_path(project, intake, allow_examples=True)
    renderer = renderer or snapshot.DEFAULT_RENDERER
    command = report_action_cli_display(project, "check_readiness", renderer)
    report_contract_path = snapshot.REPO / "projects" / project / "synthesis" / "report_support_contract.json"
    if report_contract_path.exists():
        payload = read_json_object(report_contract_path, "report support contract")
    else:
        payload = {
            "ok": False,
            "status": "not_loaded",
            "status_reasons": ["report_support_contract_missing"],
            "report_support_contract": repo_rel(report_contract_path),
            "synthesis_input_binding": {
                "schema": "ztare-synthesis-input-binding-status-v1",
                "status": "unavailable",
                "reason": "Run report readiness check to create the readiness file.",
            },
        }
    binding = payload.get("synthesis_input_binding") or {}
    report_path = snapshot.rel(payload.get("report_support_contract") or report_contract_path)
    support_payload = {**payload, "blockers": report_contract_blockers(report_path) or payload.get("blockers") or []}
    support_issues = report_support_issues(support_payload, binding)
    reasons = [str(issue.get("reason") or "") for issue in support_issues if issue.get("reason")]
    status = payload.get("status") or "unknown"
    binding_status = binding.get("status") or "unknown"
    allowed_actions = compact_report_allowed_actions(payload, project=project, rubric=rubric, intake=intake)
    try:
        receipt_payload = receipt_history_payload(project=project, intake=intake)
        receipt_rows = receipt_payload.get("receipts") if isinstance(receipt_payload.get("receipts"), list) else []
        allowed_actions = annotate_completed_report_actions(allowed_actions, receipt_rows)
    except Exception:  # noqa: BLE001 - report readiness should still load without saved-history annotation.
        receipt_rows = []
    conditional_actions = compact_report_authority_rows(payload, "conditional")
    deferred_actions = compact_report_authority_rows(payload, "deferred")
    forbidden_upgrades = compact_report_authority_rows(payload, "forbidden_upgrades")
    return {
        "schema": REPORT_CONTRACT_SCHEMA,
        "served_from": "local_api",
        "project": project,
        "rubric": rubric,
        "intake": intake,
        "project_key": case_key(project, intake),
        "case_key": case_key(project, intake),
        "report_scope": "project_report_support",
        "intake_scoped_command": False,
        "renderer": renderer,
        "command": command,
        "ok": bool(payload.get("ok")),
        "status": status,
        "display_status": display_status(status),
        "status_reasons": reasons,
        "display_status_reasons": [display_status(reason) for reason in reasons],
        "support_issues": support_issues,
        "allowed_actions": allowed_actions,
        "completed_allowed_action_count": sum(1 for action in allowed_actions if isinstance(action, dict) and report_action_completed(action)),
        "conditional_actions": conditional_actions,
        "deferred_actions": deferred_actions,
        "forbidden_upgrades": forbidden_upgrades,
        "repair_actions": report_repair_actions(
            project=project,
            rubric=rubric,
            intake=intake,
            renderer=renderer,
            report_contract=report_path,
            command=command,
            allowed_actions=allowed_actions,
            support_issues=support_issues,
        )
        if status in {"blocked", "not_loaded"} or support_issues
        else [],
        "report_support_contract": report_path,
        "backing_files": [
            {"label": "Report contract", "path": report_path}
        ] if report_path else [],
        "synthesis_input_binding": {
            "schema": binding.get("schema"),
            "ok": bool(binding.get("ok")),
            "status": binding_status,
            "display_status": display_status(binding_status),
            "reason": binding.get("reason") or "",
            "artifact_count": binding.get("artifact_count"),
            "current_digest": binding.get("current_digest"),
            "ledger_digest": binding.get("ledger_digest"),
        },
        "write_boundary": write_boundary_payload(
            writes_project_files=False,
            read_only_actions=["inspect report readiness", "preview backing files", "copy command"],
        ),
    }


def report_contract_refresh_payload_for_project(
    *,
    project: str,
    rubric: str | None = None,
    intake: str | None = None,
    renderer: str | None = None,
    confirmed: bool = False,
) -> dict[str, Any]:
    project = snapshot.validate_project_slug(project)
    rubric = rubric or project
    intake = intake or snapshot.default_intake_for_project(project)
    renderer = renderer or snapshot.DEFAULT_RENDERER
    preview_action = report_actions_core.run_report_action(
        project=project,
        action="check_readiness",
        rubric=rubric,
        intake=intake,
        renderer=renderer,
        root=snapshot.REPO,
        storage=WORKBENCH_STORE,
        python_executable=SERVER_PYTHON,
    )
    write_paths = list(preview_action.get("write_paths") or [])
    preview = {
        "schema": REPORT_CONTRACT_SCHEMA,
        "served_from": "local_api",
        "project": project,
        "rubric": rubric,
        "intake": intake,
        "renderer": renderer,
        "label": "Rerun report readiness",
        "command": str(preview_action.get("command") or ""),
        "requires_confirmation": True,
        "writes": True,
        "accepted": False,
        "ok": False,
        "returncode": None,
        "stdout_tail": "",
        "stderr_tail": "",
        "write_boundary": write_boundary_payload(
            writes_project_files=False,
            read_only_actions=["review files that may change", "copy command", "confirm in app"],
        ),
        "confirmed_write_boundary": write_boundary_payload(
            writes_project_files=True,
            write_paths=write_paths,
            receipt_path=str(preview_action.get("receipt_path") or ""),
            latest_path=str(preview_action.get("latest") or ""),
            read_only_actions=["review files that may change", "copy command"],
        ),
    }
    if not confirmed:
        preview.update({"status": "needs_confirmation", "ok": True})
        return preview
    result = report_actions_core.run_report_action(
        project=project,
        action="check_readiness",
        rubric=rubric,
        intake=intake,
        renderer=renderer,
        confirmed=True,
        root=snapshot.REPO,
        storage=WORKBENCH_STORE,
        python_executable=SERVER_PYTHON,
    )
    workspace = snapshot.REPO / "projects" / project / "workspace"
    contract_path = f"projects/{project}/synthesis/report_support_contract.json"
    ledger_path = workspace / "forensic_workbench_report_support_checks.jsonl"
    latest_path = workspace / "forensic_workbench_latest_report_support_check.json"
    payload = report_contract_payload_for_project(project=project, rubric=rubric, intake=intake, renderer=renderer)
    payload.update(
        {
            "requires_confirmation": True,
            "writes": True,
            "accepted": bool(result.get("accepted")),
            "ok": bool(result.get("ok")),
            "returncode": result.get("returncode"),
            "stdout_tail": tail_display_text(str(result.get("stdout_tail") or "")),
            "stderr_tail": tail_display_text(str(result.get("stderr_tail") or "")),
            "parsed_output": display_data(result.get("parsed_output") or {}),
            "receipt": result.get("receipt") or {},
            "receipt_path": str(result.get("receipt_path") or ""),
            "latest": str(result.get("latest") or ""),
            "write_boundary": write_boundary_payload(
                writes_project_files=True,
                write_paths=list(result.get("write_paths") or [contract_path, repo_rel(ledger_path), repo_rel(latest_path)]),
                receipt_path=str(result.get("receipt_path") or repo_rel(ledger_path)),
                latest_path=str(result.get("latest") or repo_rel(latest_path)),
            ),
        }
    )
    return payload


def report_synthesis_payload_for_project(
    *,
    project: str,
    rubric: str | None = None,
    intake: str | None = None,
    renderer: str | None = None,
    confirmed: bool = False,
    instructions: str = "",
) -> dict[str, Any]:
    project = snapshot.validate_project_slug(project)
    rubric = rubric or project
    intake = intake or snapshot.default_intake_for_project(project)
    if intake:
        project_intake_path(project, intake, allow_examples=True)
    renderer = renderer or snapshot.DEFAULT_RENDERER
    preview_action = report_actions_core.run_report_action(
        project=project,
        action="refresh_inputs",
        rubric=rubric,
        intake=intake,
        renderer=renderer,
        root=snapshot.REPO,
        storage=WORKBENCH_STORE,
        python_executable=SERVER_PYTHON,
    )
    write_paths = list(preview_action.get("write_paths") or [])
    command_display = str(preview_action.get("command") or "")
    model = str(preview_action.get("model") or "")
    preview = {
        "schema": REPORT_SYNTHESIS_SCHEMA,
        "served_from": "local_api",
        "project": project,
        "rubric": rubric,
        "intake": intake,
        "renderer": renderer,
        "model": model,
        "label": "Refresh report inputs",
        "command": command_display,
        "requires_confirmation": True,
        "writes": True,
        "accepted": False,
        "ok": False,
        "returncode": None,
        "stdout_tail": "",
        "stderr_tail": "",
        "write_boundary": write_boundary_payload(
            writes_project_files=False,
            read_only_actions=["review files that may change", "copy command", "confirm in app"],
        ),
        "confirmed_write_boundary": write_boundary_payload(
            writes_project_files=True,
            write_paths=write_paths,
            receipt_path=str(preview_action.get("receipt_path") or ""),
            latest_path=str(preview_action.get("latest") or ""),
            read_only_actions=["review files that may change", "copy command"],
        ),
    }
    if not confirmed:
        preview.update({"status": "needs_confirmation", "ok": True})
        return preview
    result = report_actions_core.run_report_action(
        project=project,
        action="refresh_inputs",
        rubric=rubric,
        intake=intake,
        renderer=renderer,
        confirmed=True,
        root=snapshot.REPO,
        storage=WORKBENCH_STORE,
        python_executable=SERVER_PYTHON,
        instructions=instructions,
    )
    workspace = snapshot.REPO / "projects" / project / "workspace"
    ledger_path = workspace / "forensic_workbench_report_synthesis.jsonl"
    latest_path = workspace / "forensic_workbench_latest_report_synthesis.json"
    payload = report_contract_payload_for_project(project=project, rubric=rubric, intake=intake, renderer=renderer)
    payload.update(
        {
            "schema": REPORT_SYNTHESIS_SCHEMA,
            "requires_confirmation": True,
            "writes": True,
            "accepted": bool(result.get("accepted")),
            "ok": bool(result.get("ok")),
            "returncode": result.get("returncode"),
            "stdout_tail": tail_display_text(str(result.get("stdout_tail") or "")),
            "stderr_tail": tail_display_text(str(result.get("stderr_tail") or "")),
            "parsed_output": display_data(result.get("parsed_output") or {}),
            "receipt": result.get("receipt") or {},
            "receipt_path": str(result.get("receipt_path") or ""),
            "latest": str(result.get("latest") or ""),
            "model": str(result.get("model") or model),
            "command": str(result.get("command") or command_display),
            "write_boundary": write_boundary_payload(
                writes_project_files=True,
                write_paths=list(result.get("write_paths") or write_paths),
                receipt_path=str(result.get("receipt_path") or repo_rel(ledger_path)),
                latest_path=str(result.get("latest") or repo_rel(latest_path)),
            ),
        }
    )
    return payload


def trace_payload_for_project(
    *,
    project: str,
    rubric: str | None = None,
    intake: str | None = None,
) -> dict[str, Any]:
    project = snapshot.validate_project_slug(project)
    rubric = rubric or project
    intake = intake or snapshot.default_intake_for_project(project)
    trace, trace_command = snapshot.collect_trace(project, rubric, intake)
    kernel = trace.get("kernel_entry") or {}
    plan = trace.get("plan_preview") or {}
    surfaces = trace.get("surfaces") or {}
    readiness = surfaces.get("evidence_readiness") or {}
    source_receipt = surfaces.get("source_index_receipt") or {}
    prediction = trace.get("prediction_summary") or {}
    readiness_checks = [
        {
            "surface": row.get("surface"),
            "display_surface": display_surface(row.get("surface")),
            "status": row.get("status"),
            "display_status": display_status(row.get("status")),
            "blocking": bool(row.get("blocking")),
            "next_command": row.get("next_command"),
            "count": row.get("count"),
            "receipt_count": row.get("receipt_count"),
        }
        for row in trace.get("carrier_chain", [])
        if isinstance(row, dict)
    ]
    graph_summaries = [
        {
            "graph_id": row.get("graph_id"),
            "graph_kind": row.get("graph_kind"),
            "node_count": row.get("node_count"),
            "edge_count": row.get("edge_count"),
            "source_artifacts": [snapshot.rel(path) for path in (row.get("source_artifacts") or [])],
            "validation_ok": (row.get("validation") or {}).get("ok"),
        }
        for row in trace.get("graph_carriers", [])
        if isinstance(row, dict)
    ]
    preflight_receipt = trace.get("loop_admission") or {}
    readiness_status = trace.get("readiness_canonical") or trace.get("readiness") or "unknown"
    kernel_status = kernel.get("status") or "unknown"
    kernel_readiness = kernel.get("readiness_canonical") or kernel.get("readiness") or "unknown"
    plan_status = plan.get("status") or "unknown"
    raw_run_command = str(kernel.get("run_command") or "")
    adjusted_run_command = apply_run_settings_to_autoresearch_command(raw_run_command, project) if raw_run_command else ""
    return {
        "schema": "ztare-forensic-workbench-trace-v1",
        "ok": True,
        "served_from": "local_api",
        "project": project,
        "rubric": rubric,
        "intake": intake,
        "trace_command": trace_command,
        "readiness": readiness_status,
        "display_readiness": display_status(readiness_status),
        "blocking_missing": trace.get("blocking_missing") or trace.get("missing") or [],
        "next_commands": trace.get("next_commands") or [],
        "readiness_checks": readiness_checks,
        "carrier_chain": readiness_checks,
        "kernel_entry": {
            "schema": kernel.get("schema"),
            "status": kernel_status,
            "display_status": display_status(kernel_status),
            "can_enter_kernel": kernel.get("can_enter_kernel"),
            "readiness": kernel_readiness,
            "display_readiness": display_status(kernel_readiness),
            "entry_surface": kernel.get("entry_surface"),
            "preflight_command": kernel.get("preflight_command"),
            "run_command": adjusted_run_command or kernel.get("run_command"),
            "raw_run_command": raw_run_command,
            "inspection_command": kernel.get("inspection_command"),
            "blockers": kernel.get("blockers") or [],
            "allowed_work_modes": kernel.get("allowed_work_modes") or [],
            "disallowed_work_modes": kernel.get("disallowed_work_modes") or [],
        },
        "plan_preview": {
            "schema": plan.get("schema"),
            "status": plan_status,
            "display_status": display_status(plan_status),
            "available": bool(plan.get("available")),
            "recommended_first_command": plan.get("recommended_first_command"),
            "model_calls_before_confirmation": plan.get("model_calls_before_confirmation"),
            "largest_quality_drop_risk": plan.get("largest_quality_drop_risk"),
            "risk_reason": plan.get("risk_reason"),
            "worker_count": plan.get("worker_count"),
            "dependency_order": [
                {
                    "id": row.get("id"),
                    "status": row.get("status"),
                    "display_status": plan_step_display_status(row, plan_status),
                    "model_calls": bool(row.get("model_calls")),
                    "command": row.get("command"),
                    "description": row.get("description"),
                }
                for row in plan.get("dependency_order", [])
                if isinstance(row, dict)
            ],
        },
        "preflight_receipt": preflight_receipt,
        "loop_admission": preflight_receipt,
        "recent_loop": trace.get("recent_loop") or {},
        "surfaces": {
            "source_preflight_status": surfaces.get("source_preflight_status"),
            "display_source_preflight_status": display_status(surfaces.get("source_preflight_status")),
            "raw_file_count": surfaces.get("raw_file_count"),
            "source_index_status": readiness.get("source_index_status"),
            "display_source_index_status": display_status(readiness.get("source_index_status")),
            "evidence_status": readiness.get("status"),
            "display_evidence_status": display_status(readiness.get("status")),
            "output_binding_status": readiness.get("output_binding_status"),
            "display_output_binding_status": display_status(readiness.get("output_binding_status")),
            "replay_status": readiness.get("replay_status"),
            "display_replay_status": display_status(readiness.get("replay_status")),
            "source_index_receipt_path": source_receipt.get("path"),
            "compile_provenance_path": snapshot.rel(surfaces.get("compile_provenance_path")),
        },
        "graph_summaries": graph_summaries,
        "graph_carriers": graph_summaries,
        "prediction_summary": {
            "available": bool(prediction.get("available")),
            "status": prediction.get("status"),
            "row_count": prediction.get("row_count"),
            "scoreable_count": prediction.get("scoreable_count"),
            "measurement_policy": prediction.get("measurement_policy"),
        },
    }


def action_intelligence_recommendations(limit: int = 6) -> dict[str, Any]:
    path = snapshot.REPO / ACTION_INTELLIGENCE_STATE_DIR / "shadow_recommendations.json"
    if not path.exists():
        return {"generated_at": None, "counts": {}, "recommendations": [], "source_path": snapshot.rel(path)}
    payload = json.loads(WORKBENCH_STORE.read_text(path))
    if not isinstance(payload, dict):
        raise ValueError("shadow recommendations read model must be a JSON object")
    rows = payload.get("recommendations") or []
    if not isinstance(rows, list):
        rows = []
    recommendations = []
    for row in rows[:limit]:
        if not isinstance(row, dict):
            continue
        externality = row.get("externality_checks") or {}
        gp230 = row.get("gp230") or {}
        recommendations.append(
            {
                "recommendation_id": row.get("recommendation_id"),
                "decision_id": row.get("decision_id"),
                "domain": row.get("domain"),
                "display_domain": display_action_label(row.get("domain")),
                "recommended_action": row.get("recommended_action"),
                "display_recommended_action": display_action_label(row.get("recommended_action")),
                "confidence": row.get("confidence"),
                "display_confidence": display_action_label(row.get("confidence")),
                "execution_authority": row.get("execution_authority"),
                "display_execution_authority": display_action_label(row.get("execution_authority")),
                "rationale": row.get("rationale"),
                "display_rationale": display_guidance_text(row.get("rationale")),
                "blocking_checks": row.get("blocking_checks") or [],
                "display_blocking_checks": [display_action_label(item) for item in row.get("blocking_checks") or []],
                "evidence_refs": row.get("evidence_refs") or [],
                "display_evidence_refs": [display_evidence_ref(item) for item in row.get("evidence_refs") or []],
                "source": row.get("source"),
                "display_source": display_action_label(row.get("source")),
                "p_success": gp230.get("p_success"),
                "expected_cost_agent_minutes": gp230.get("expected_cost_agent_minutes"),
                "effective_n": gp230.get("effective_n"),
                "goodhart_risk": externality.get("goodhart_risk"),
                "sample_size": externality.get("sample_size"),
            }
        )
    return {
        "generated_at": payload.get("generated_at"),
        "counts": payload.get("counts") or {},
        "recommendations": recommendations,
        "source_path": snapshot.rel(path),
    }


def action_intelligence_health_read_model() -> dict[str, Any]:
    path = snapshot.REPO / ACTION_INTELLIGENCE_STATE_DIR / "source_health.json"
    if not path.exists():
        return {
            "generated_at": None,
            "counts": {},
            "issues": [],
            "source_paths": {},
            "source_path": snapshot.rel(path),
        }
    payload = json.loads(WORKBENCH_STORE.read_text(path))
    if not isinstance(payload, dict):
        raise ValueError("source health read model must be a JSON object")
    return {
        "generated_at": payload.get("generated_at"),
        "counts": payload.get("counts") or {},
        "issues": payload.get("issues") or [],
        "source_paths": payload.get("source_paths") or {},
        "source_path": snapshot.rel(path),
    }


def kernel_health_from_trace(*, project: str, rubric: str, intake: str) -> dict[str, Any]:
    recompute_command = (
        "make autoresearch-kernel-health "
        f"PROJECT={project} RUBRIC={rubric} INTAKE={intake} JSON=1"
    )
    try:
        trace = trace_payload_for_project(project=project, rubric=rubric, intake=intake)
    except Exception as exc:  # noqa: BLE001 - health is advisory in the workbench.
        return {
            "summary": {
                "overall_status": "attention",
                "component_status": "attention",
                "component_count": 1,
                "component_counts": {"attention": 1, "ok": 0},
                "source": "trace_read_model",
                "recompute_command": recompute_command,
            },
            "attention_components": [
                {
                    "component": "run_trace",
                    "status": "attention",
                    "action": f"Trace read failed: {display_text(exc)}",
                    "next_command": recompute_command,
                }
            ],
            "component_count": 1,
        }

    attention_components: list[dict[str, Any]] = []
    readiness_checks = [row for row in trace.get("readiness_checks") or [] if isinstance(row, dict)]
    for row in readiness_checks:
        if not row.get("blocking"):
            continue
        attention_components.append(
            {
                "component": row.get("surface") or "readiness",
                "status": row.get("status") or "attention",
                "action": "Inspect readiness blocker.",
                "next_command": row.get("next_command") or recompute_command,
            }
        )

    recent_loop = trace.get("recent_loop") if isinstance(trace.get("recent_loop"), dict) else {}
    pending_action = str(recent_loop.get("latest_pending_loop_action") or "")
    latest_rationale = str(recent_loop.get("latest_information_yield_rationale") or "")
    if pending_action or "failed" in latest_rationale.lower():
        attention_components.append(
            {
                "component": "project_trace",
                "status": "attention",
                "action": latest_rationale or f"Inspect pending run action: {pending_action}",
                "next_command": trace.get("trace_command") or recompute_command,
            }
        )

    status = "attention" if attention_components else "ok"
    component_count = max(len(readiness_checks), 1)
    return {
        "summary": {
            "overall_status": status,
            "component_status": status,
            "component_count": component_count,
            "component_counts": {
                "attention": len(attention_components),
                "ok": max(component_count - len(attention_components), 0),
            },
            "source": "trace_read_model",
            "recompute_command": recompute_command,
        },
        "attention_components": attention_components,
        "component_count": component_count,
    }


def health_payload_for_project(
    *,
    project: str,
    rubric: str | None = None,
    intake: str | None = None,
) -> dict[str, Any]:
    project = snapshot.validate_project_slug(project)
    rubric = rubric or project
    intake = intake or snapshot.default_intake_for_project(project)
    kernel_payload = kernel_health_from_trace(project=project, rubric=rubric, intake=intake)
    action_payload = action_intelligence_health_read_model()
    action_source_paths = dict(action_payload.get("source_paths") or {})
    if action_payload.get("source_path"):
        action_source_paths.setdefault("source_health", action_payload.get("source_path"))
    recommendation_payload = action_intelligence_recommendations()

    attention_components = [
        {
            "component": row.get("component"),
            "display_component": display_surface(row.get("component")),
            "status": row.get("status"),
            "display_status": display_status(row.get("status")),
            "action": row.get("action"),
            "display_action": display_guidance_text(row.get("action")),
            "next_command": row.get("next_command"),
        }
        for row in kernel_payload.get("attention_components", [])
    ]
    action_issues = []
    for issue in action_payload.get("issues", []):
        issue_type = str(issue.get("issue_type") or issue.get("recommended_action") or "source_warning")
        guidance = source_health_issue_guidance(issue_type)
        action_issues.append(
            {
                "issue_id": issue.get("issue_id"),
                "issue_type": issue.get("issue_type"),
                "display_label": display_action_label(issue.get("issue_type")),
                "display_issue_type": display_action_label(issue.get("issue_type")),
                "severity": issue.get("severity"),
                "display_severity": display_action_label(issue.get("severity")),
                "scope": issue.get("scope"),
                "display_scope": display_action_label(issue.get("scope")),
                "domain": issue.get("domain"),
                "display_domain": display_action_label(issue.get("domain")),
                "affected_domains": issue.get("affected_domains") or [],
                "display_affected_domains": [display_action_label(item) for item in issue.get("affected_domains") or []],
                "blocking_rule": issue.get("blocking_rule"),
                "display_blocking_rule": display_guidance_text(issue.get("blocking_rule")),
                "denominator": issue.get("denominator"),
                "display_denominator": display_guidance_text(issue.get("denominator")),
                "observed_count": issue.get("observed_count"),
                "expected_count": issue.get("expected_count"),
                "freshness_window_days": issue.get("freshness_window_days"),
                "evidence_refs": issue.get("evidence_refs") or [],
                "display_evidence_refs": [display_evidence_ref(item) for item in issue.get("evidence_refs") or []],
                "recommended_action": issue.get("recommended_action"),
                "display_recommended_action": source_health_recommended_action_label(
                    issue.get("issue_type"),
                    issue.get("recommended_action"),
                ),
                **guidance,
            }
        )
    action_guidance = {
        "counts": action_payload.get("counts") or {},
        "issues": action_issues,
        "recommendations": recommendation_payload.get("recommendations") or [],
        "recommendation_counts": recommendation_payload.get("counts") or {},
        "recommendations_generated_at": recommendation_payload.get("generated_at"),
        "recommendations_source_path": recommendation_payload.get("source_path"),
        "source_paths": action_source_paths,
    }
    return {
        "schema": "ztare-forensic-workbench-health-v1",
        "ok": True,
        "served_from": "local_api",
        "project": project,
        "rubric": rubric,
        "intake": intake,
        "kernel": {
            "summary": kernel_payload.get("summary") or {},
            "attention_components": attention_components,
            "component_count": int(kernel_payload.get("component_count") or 0),
        },
        "action_guidance": action_guidance,
        "action_intelligence": action_guidance,
    }


def command_result_payload(proc: Any) -> dict[str, Any]:
    parsed_output: dict[str, Any] = {}
    try:
        parsed_output = snapshot.extract_last_json_object(proc.stdout)
    except Exception:
        parsed_output = {}
    return {
        "returncode": proc.returncode,
        "accepted": proc.returncode == 0,
        "stdout_tail": tail_display_text(proc.stdout),
        "stderr_tail": tail_display_text(proc.stderr),
        "parsed_output": display_data(parsed_output),
    }


def source_check_after_write(
    *,
    project: str,
    rubric: str | None = None,
    intake: str | None = None,
    renderer: str | None = None,
) -> dict[str, Any]:
    try:
        return source_action_payload_for_project(
            project=project,
            action="source_check",
            rubric=rubric,
            intake=intake,
            renderer=renderer,
        )
    except SystemExit as exc:
        error = display_text(exc)
    except Exception as exc:  # noqa: BLE001 - the source write already succeeded.
        error = display_text(exc)
    return {
        "schema": SOURCE_ACTION_SCHEMA,
        "served_from": "local_api",
        "project": project,
        "rubric": rubric or project,
        "intake": intake or "",
        "action": "source_check",
        "label": SOURCE_ACTIONS["source_check"]["label"],
        "writes": False,
        "command": SOURCE_ACTIONS["source_check"]["display"].format(project=project),
        "returncode": None,
        "accepted": False,
        "error": error,
        "stdout_tail": "",
        "stderr_tail": "",
        "parsed_output": {},
        "trace": None,
        "snapshot": None,
    }


def import_source_payload(
    *,
    project: str,
    filename: str,
    source_type: str,
    body: str,
    artifact_kind: str = "project_note",
    created_by: str = "",
    rubric: str | None = None,
    intake: str | None = None,
    renderer: str | None = None,
) -> dict[str, Any]:
    project = snapshot.validate_project_slug(project)
    rubric = rubric or project
    intake = intake or snapshot.default_intake_for_project(project)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".md") as staged:
        staged.write(body)
        staged.flush()
        payload = ztare_cli_payload([
            "project", "source-file", "add",
            "--project", project,
            "--rubric", rubric,
            "--intake", intake,
            "--filename", filename,
            "--source-type", source_type,
            "--kind", artifact_kind,
            "--created-by", created_by,
            "--body-file", staged.name,
            "--repo", str(snapshot.REPO),
            "--json",
        ], project=project, timeout=90)
    if payload.get("ok") is False:
        return payload
    source_check = source_check_after_write(
        project=project,
        rubric=rubric,
        intake=intake,
        renderer=renderer,
    )
    payload["served_from"] = "local_api"
    payload["write_boundary"] = write_boundary_payload(
        writes_project_files=True,
        write_paths=list(payload.get("write_paths") or []),
        receipt_path=str(payload.get("receipt_path") or ""),
        latest_path=str(payload.get("latest") or ""),
    )
    payload["source_check"] = source_check
    payload["snapshot"] = source_check.get("snapshot")
    payload["trace"] = source_check.get("trace")
    payload["decision_checkpoint"] = scenario_strength_payload(project)
    return payload


def source_raw_dir(project: str) -> Path:
    project = snapshot.validate_project_slug(project)
    return snapshot.REPO / "projects" / project / "raw"


def validate_raw_source_relative(value: str) -> str:
    value = str(value or "").strip().replace("\\", "/")
    unsafe_reason = unsafe_local_ref_reason(value)
    if unsafe_reason is not None:
        raise ValueError(f"invalid source file path: {unsafe_reason}")
    path = PurePosixPath(value)
    if path.name == "source_type_map.json":
        raise ValueError("source_type_map.json is edited by the workbench, not as a source")
    if path.suffix.lower() not in {".md", ".txt"}:
        raise ValueError("source file path must end in .md or .txt")
    return path.as_posix()


def raw_source_path(project: str, relative_path: str) -> Path:
    raw_dir = source_raw_dir(project)
    relative_path = validate_raw_source_relative(relative_path)
    path = (raw_dir / relative_path).resolve()
    if not path_under(path, raw_dir):
        raise ValueError("source file path escapes the project source file directory")
    return path


def read_source_type_map(raw_dir: Path) -> dict[str, Any]:
    path = raw_dir / "source_type_map.json"
    if not path.exists():
        return {}
    return read_json_object(path, repo_rel(path))


def split_source_frontmatter(text: str, *, fallback_source_type: str = "untyped") -> tuple[str, str]:
    source_type = fallback_source_type if fallback_source_type in SOURCE_IMPORT_TYPES else "untyped"
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            frontmatter = text[4:end].splitlines()
            for line in frontmatter:
                key, sep, value = line.partition(":")
                if sep and key.strip() == "source_type" and value.strip() in SOURCE_IMPORT_TYPES:
                    source_type = value.strip()
            body = text[end + len("\n---\n") :]
            if body.startswith("\n"):
                body = body[1:]
            if body.endswith("\n"):
                body = body[:-1]
            return source_type, body
    if text.endswith("\n"):
        text = text[:-1]
    return source_type, text


def source_frontmatter_metadata(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}
    metadata: dict[str, str] = {}
    for line in text[4:end].splitlines():
        key, sep, value = line.partition(":")
        if sep:
            metadata[key.strip()] = value.strip()
    return metadata


def project_source_artifacts(project: str, *, limit: int = 30) -> list[dict[str, str]]:
    project = snapshot.validate_project_slug(project)
    raw_dir = source_raw_dir(project)
    if not raw_dir.exists():
        return []
    rows: list[dict[str, str]] = []
    for path in sorted(raw_dir.rglob("*")):
        if not path.is_file() or path.name == "source_type_map.json" or path.suffix.lower() not in {".md", ".txt"}:
            continue
        metadata = source_frontmatter_metadata(WORKBENCH_STORE.read_text(path))
        artifact_kind = metadata.get("artifact_kind") if metadata.get("artifact_kind") in SOURCE_ARTIFACT_KINDS else ""
        created_by = metadata.get("created_by") or ""
        if not artifact_kind and not created_by:
            continue
        rows.append(
            {
                "path": repo_rel(path),
                "relative_path": path.relative_to(raw_dir).as_posix(),
                "artifact_kind": artifact_kind or "project_note",
                "created_by": created_by,
                "source_type": metadata.get("source_type") or "",
            }
        )
        if len(rows) >= limit:
            break
    return rows


def source_list_payload(*, project: str) -> dict[str, Any]:
    project = snapshot.validate_project_slug(project)
    command = [
        SERVER_PYTHON,
        "-m",
        "src.ztare.cli",
        "project",
        "source-check",
        "--project",
        project,
        "--json",
        "--no-fail",
    ]
    proc = snapshot.run(command, timeout=90)
    parsed = snapshot.extract_last_json_object(proc.stdout) if proc.stdout.strip() else {}
    raw_dir = source_raw_dir(project)
    sources = display_data(parsed.get("sources")) if isinstance(parsed.get("sources"), list) else []
    source_type_counts: dict[str, int] = {}
    invalid_source_type_count = 0
    artifact_rows = project_source_artifacts(project, limit=200)
    artifact_by_relative = {row["relative_path"]: row for row in artifact_rows}
    for row in sources:
        if not isinstance(row, dict):
            continue
        source_type = str(row.get("source_type") or "untyped")
        source_type_counts[source_type] = source_type_counts.get(source_type, 0) + 1
        if row.get("invalid_source_type_declaration"):
            invalid_source_type_count += 1
        artifact = artifact_by_relative.get(str(row.get("path") or ""))
        if artifact:
            row["artifact_kind"] = artifact.get("artifact_kind") or ""
            row["created_by"] = artifact.get("created_by") or ""
    return {
        "schema": SOURCE_LIST_SCHEMA,
        "ok": True,
        "served_from": "local_api",
        "project": project,
        "raw_dir": repo_rel(raw_dir) if raw_dir.exists() else f"projects/{project}/raw",
        "source_count": len(sources),
        "source_type_counts": source_type_counts,
        "untyped_source_count": source_type_counts.get("untyped", 0),
        "invalid_source_type_count": invalid_source_type_count,
        "command": f"ztare project source-check --project {project} --json --no-fail",
        "returncode": proc.returncode,
        "accepted": proc.returncode == 0,
        "stdout_tail": tail_display_text(proc.stdout),
        "stderr_tail": tail_display_text(proc.stderr),
        "source_check": display_data(parsed),
        "artifact_count": len(artifact_rows),
        "artifacts": artifact_rows,
        "sources": sources,
    }


def source_file_payload(*, project: str, relative_path: str) -> dict[str, Any]:
    project = snapshot.validate_project_slug(project)
    path = raw_source_path(project, relative_path)
    if not path.exists():
        raise FileNotFoundError(f"source file does not exist: {repo_rel(path)}")
    raw_dir = source_raw_dir(project)
    type_map = read_source_type_map(raw_dir)
    relative_path = str(path.relative_to(raw_dir.resolve()))
    fallback_type = str(type_map.get(relative_path) or type_map.get(path.name) or "untyped")
    raw_text = WORKBENCH_STORE.read_text(path)
    source_type, body = split_source_frontmatter(raw_text, fallback_source_type=fallback_type)
    metadata = source_frontmatter_metadata(raw_text)
    return {
        "schema": SOURCE_FILE_SCHEMA,
        "ok": True,
        "served_from": "local_api",
        "project": project,
        "relative_raw_path": relative_path,
        "source_path": repo_rel(path),
        "source_type": source_type,
        "artifact_kind": metadata.get("artifact_kind") if metadata.get("artifact_kind") in SOURCE_ARTIFACT_KINDS else "",
        "created_by": metadata.get("created_by") or "",
        "body": body,
    }


def edit_source_payload(
    *,
    project: str,
    relative_path: str,
    source_type: str,
    body: str,
    artifact_kind: str | None = None,
    created_by: str | None = None,
    rubric: str | None = None,
    intake: str | None = None,
    renderer: str | None = None,
) -> dict[str, Any]:
    project = snapshot.validate_project_slug(project)
    rubric = rubric or project
    intake = intake or snapshot.default_intake_for_project(project)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".md") as staged:
        staged.write(body)
        staged.flush()
        args = [
            "project", "source-file", "edit",
            "--project", project,
            "--rubric", rubric,
            "--intake", intake,
            "--relative", relative_path,
            "--source-type", source_type,
            "--body-file", staged.name,
            "--repo", str(snapshot.REPO),
            "--json",
        ]
        if artifact_kind:
            args.extend(["--kind", artifact_kind])
        if created_by is not None:
            args.extend(["--created-by", created_by])
        payload = ztare_cli_payload(args, project=project, timeout=90)
    if payload.get("ok") is False:
        return payload
    source_check = source_check_after_write(
        project=project,
        rubric=rubric,
        intake=intake,
        renderer=renderer,
    )
    payload["served_from"] = "local_api"
    payload["write_boundary"] = write_boundary_payload(
        writes_project_files=True,
        write_paths=list(payload.get("write_paths") or []),
        receipt_path=str(payload.get("receipt_path") or ""),
        latest_path=str(payload.get("latest") or ""),
    )
    payload["source_check"] = source_check
    payload["snapshot"] = source_check.get("snapshot")
    payload["trace"] = source_check.get("trace")
    payload["decision_checkpoint"] = scenario_strength_payload(project)
    return payload


def create_project_payload(
    *,
    project: str,
    rubric: str | None = None,
    task: str = "",
    bounded_claim: str = "",
    next_falsifier: str = "",
    notes: str = "",
    source_refs: Any = None,
    evidence_refs: Any = None,
    non_claims: Any = None,
    uploaded_sources: Any = None,
    renderer: str | None = None,
) -> dict[str, Any]:
    project = snapshot.validate_project_slug(project)
    rubric = snapshot.validate_project_slug(rubric or project)
    task = str(task or "").strip()
    bounded_claim = str(bounded_claim or "").strip()
    next_falsifier = str(next_falsifier or "").strip()
    notes = str(notes or "").strip()
    if not task:
        raise ValueError("task is required")
    if not bounded_claim:
        raise ValueError("bounded_claim is required")
    if not next_falsifier:
        raise ValueError("next_falsifier is required")
    source_ref_lines = text_lines(source_refs)
    evidence_ref_lines = text_lines(evidence_refs)
    non_claim_lines = text_lines(non_claims)
    uploaded_source_rows = uploaded_source_rows_for_project(uploaded_sources)
    project_root = snapshot.REPO / "projects" / project
    project_existed_before = project_root.exists()
    if project_existed_before and snapshot.discover_project_intakes(project):
        raise ValueError(f"project already has an intake: {project}")
    intake = f"projects/{project}/{project}_intake.json"
    expected_command = (
        "ztare autoresearch run "
        f"--project {project} --rubric {rubric} --intake {intake} --iters 1"
    )
    source_init_command = [
        SERVER_PYTHON,
        "-m",
        "src.ztare.cli",
        "project",
        "source-init",
        "--project",
        project,
        "--rubric",
        rubric,
        "--json",
    ]
    source_proc = snapshot.run(source_init_command, timeout=90)
    source_result = command_result_payload(source_proc)
    intake_result: dict[str, Any] | None = None
    recovered_source_write_paths: list[str] = []
    uploaded_source_write_paths: list[str] = []
    uploaded_source_refs: list[str] = []
    uploaded_evidence_refs: list[str] = []
    source_refs_for_intake = list(source_ref_lines)
    if source_proc.returncode == 0:
        source_refs_for_intake, recovered_source_write_paths = stage_recovered_source_refs(project, source_ref_lines)
        uploaded_source_refs, uploaded_evidence_refs, uploaded_source_write_paths = stage_uploaded_source_rows(
            project,
            uploaded_source_rows,
        )
        source_refs_for_intake = unique_values([*source_refs_for_intake, *uploaded_source_refs])
        evidence_ref_lines = unique_values([*evidence_ref_lines, *uploaded_evidence_refs])
        intake_command = [
            SERVER_PYTHON,
            "-m",
            "src.ztare.cli",
            "project",
            "intake",
            "create",
            "--path",
            intake,
            "--project",
            project,
            "--rubric",
            rubric,
            "--task",
            task,
            "--bounded-claim",
            bounded_claim,
            "--next-falsifier",
            next_falsifier,
            "--expected-command",
            expected_command,
            "--json",
        ]
        if notes:
            intake_command.extend(["--notes", notes])
        for ref in source_refs_for_intake:
            intake_command.extend(["--source-ref", ref])
        for ref in evidence_ref_lines:
            intake_command.extend(["--evidence-ref", ref])
        for item in non_claim_lines:
            intake_command.extend(["--non-claim", item])
        intake_proc = snapshot.run(intake_command, timeout=90)
        intake_result = {
            "command": (
                "ztare project intake create "
                f"--path {intake} --project {project} --rubric {rubric} "
                "--task <task> --bounded-claim <claim> --next-falsifier <falsifier> "
                "--expected-command <command> --json"
            ),
            **command_result_payload(intake_proc),
        }
    source_init_accepted = source_proc.returncode == 0
    intake_path_obj = snapshot.REPO / intake
    intake_create_accepted = bool(intake_result and intake_result["accepted"])
    intake_file_exists = intake_path_obj.exists()
    accepted = source_init_accepted and bool(intake_create_accepted or intake_file_exists)
    source_output = source_result.get("parsed_output") if isinstance(source_result.get("parsed_output"), dict) else {}
    source_write_paths = [
        str(path)
        for path in [
            *(source_output.get("created_dirs") or []),
            *(source_output.get("created_files") or []),
        ]
        if path
    ]
    if source_init_accepted and not source_write_paths and not project_existed_before:
        source_write_paths = [
            repo_rel(project_root),
            repo_rel(project_root / "raw"),
            repo_rel(project_root / "workspace"),
        ]
    write_paths = source_write_paths if source_init_accepted else []
    write_paths.extend(recovered_source_write_paths)
    write_paths.extend(uploaded_source_write_paths)
    charter_write_path: str | None = None
    if accepted:
        charter_write_path = ensure_project_charter(
            project=project,
            task=task,
            bounded_claim=bounded_claim,
            next_falsifier=next_falsifier,
            notes=notes,
            source_refs=source_refs_for_intake,
            evidence_refs=evidence_ref_lines,
            non_claims=non_claim_lines,
        )
        if charter_write_path:
            write_paths.append(charter_write_path)
    if accepted:
        write_paths.append(intake)
    write_paths = unique_values(write_paths)
    payload: dict[str, Any] = {
        "schema": PROJECT_CREATE_SCHEMA,
        "served_from": "local_api",
        "project": project,
        "rubric": rubric,
        "intake": intake,
        "created_mode": "add_intake" if project_existed_before else "create_project",
        "project_existed_before": project_existed_before,
        "ok": accepted,
        "accepted": accepted,
        "creation_complete": accepted,
        "source_init_accepted": source_init_accepted,
        "intake_create_accepted": intake_create_accepted,
        "intake_file_exists": intake_file_exists,
        "created_paths": write_paths,
        "recovered_source_refs": source_refs_for_intake,
        "recovered_source_write_paths": recovered_source_write_paths,
        "uploaded_source_refs": uploaded_source_refs,
        "uploaded_evidence_refs": uploaded_evidence_refs,
        "uploaded_source_write_paths": uploaded_source_write_paths,
        "write_boundary": write_boundary_payload(
            writes_project_files=bool(write_paths),
            write_paths=write_paths,
            receipt_path=intake if accepted else "",
            latest_path=intake if accepted else "",
            read_only_actions=["preview", "copy"],
        ),
        "source_init": {
            "command": f"ztare project source-init --project {project} --rubric {rubric} --json",
            **source_result,
        },
        "intake_create": intake_result,
        "project_index": None,
        "snapshot": None,
    }
    if accepted:
        try:
            payload["project_index"] = project_index_payload()
        except Exception as exc:  # noqa: BLE001 - creation result should still be inspectable.
            payload["project_index_error"] = display_text(exc)
        try:
            payload["snapshot"] = snapshot_payload_for_project(
                project=project,
                rubric=rubric,
                intake=intake,
                renderer=renderer,
            )
        except Exception as exc:  # noqa: BLE001 - creation result should still be inspectable.
            payload["snapshot_error"] = display_text(exc)
    return payload


def preflight_payload_for_project(
    *,
    project: str,
    rubric: str | None = None,
    intake: str | None = None,
    renderer: str | None = None,
) -> dict[str, Any]:
    project = snapshot.validate_project_slug(project)
    rubric = rubric or project
    intake = intake or snapshot.default_intake_for_project(project)
    project_intake_path(project, intake, allow_examples=True)
    command = [
        SERVER_PYTHON,
        "-m",
        "src.ztare.cli",
        "autoresearch",
        "run",
        "--project",
        project,
        "--rubric",
        rubric,
        "--intake",
        intake,
        "--preflight-only",
    ]
    display_command = (
        "ztare autoresearch run "
        f"--project {project} --rubric {rubric} --intake {intake} --preflight-only"
    )
    proc = snapshot.run(command, timeout=120)
    accepted = proc.returncode == 0 and "autoresearch preflight-only" in proc.stdout
    fallback_preflight_path = preflight_telemetry_path(project)
    payload: dict[str, Any] = {
        "schema": PREFLIGHT_SCHEMA,
        "served_from": "local_api",
        "project": project,
        "rubric": rubric,
        "intake": intake,
        "command": display_command,
        "returncode": proc.returncode,
        "accepted": accepted,
        "ok": accepted,
        "stdout_tail": tail_display_text(proc.stdout),
        "stderr_tail": tail_display_text(proc.stderr),
        "write_boundary": (
            write_boundary_payload(
                writes_project_files=True,
                write_paths=[fallback_preflight_path],
                receipt_path=fallback_preflight_path,
                latest_path=fallback_preflight_path,
                read_only_actions=["Copy command", "Inspect output"],
            )
            if accepted
            else failed_write_boundary_payload(
                write_paths=[fallback_preflight_path],
                receipt_path=fallback_preflight_path,
                latest_path=fallback_preflight_path,
                read_only_actions=["Copy command", "Inspect output", "fix readiness blocker"],
            )
        ),
        "trace": None,
        "snapshot": None,
    }
    try:
        payload["trace"] = trace_payload_for_project(project=project, rubric=rubric, intake=intake)
        preflight_paths = preflight_write_paths(payload["trace"])
        if accepted and preflight_paths:
            payload["write_boundary"] = write_boundary_payload(
                writes_project_files=True,
                write_paths=preflight_paths,
                receipt_path=preflight_paths[0],
                latest_path=preflight_paths[0],
                read_only_actions=["Copy command", "Inspect output"],
            )
        elif not accepted and preflight_paths:
            payload["write_boundary"] = failed_write_boundary_payload(
                write_paths=preflight_paths,
                receipt_path=preflight_paths[0],
                latest_path=preflight_paths[0],
                read_only_actions=["Copy command", "Inspect output", "fix readiness blocker"],
            )
    except SystemExit as exc:
        payload["trace_error"] = display_text(exc)
    except Exception as exc:  # noqa: BLE001 - preflight result should still be inspectable.
        payload["trace_error"] = display_text(exc)
    try:
        payload["snapshot"] = snapshot_payload_for_project(
            project=project,
            rubric=rubric,
            intake=intake,
            renderer=renderer,
        )
    except SystemExit as exc:
        payload["snapshot_error"] = display_text(exc)
    except Exception as exc:  # noqa: BLE001 - preflight result should still be inspectable.
        payload["snapshot_error"] = display_text(exc)
    return payload


def project_test_write_boundary(project: str) -> dict[str, Any]:
    paths = project_check_core.project_test_write_paths(project)
    write_paths = paths["write_paths"]
    return write_boundary_payload(
        writes_project_files=True,
        write_paths=write_paths,
        receipt_path=paths["receipt_path"],
        latest_path=paths["latest_path"],
        read_only_actions=["preview test file", "copy command"],
    )


def project_test_payload_for_project(
    *,
    project: str,
    rubric: str | None = None,
    intake: str | None = None,
    renderer: str | None = None,
    action_id: str | None = None,
    action_label: str | None = None,
) -> dict[str, Any]:
    project = snapshot.validate_project_slug(project)
    rubric = rubric or project
    intake = intake or snapshot.default_intake_for_project(project)
    project_intake_path(project, intake, allow_examples=True)
    payload = project_check_core.run_project_check(
        project=project,
        rubric=rubric,
        intake=intake,
        action_id=action_id,
        action_label=display_guidance_text(action_label or ""),
        python_executable=SERVER_PYTHON,
        root=snapshot.REPO,
    )
    payload["served_from"] = "local_api"
    payload["write_boundary"] = project_test_write_boundary(project)
    try:
        payload["snapshot"] = snapshot_payload_for_project(
            project=project,
            rubric=rubric,
            intake=intake,
            renderer=renderer,
        )
    except SystemExit as exc:
        payload["snapshot_error"] = display_text(exc)
    except Exception as exc:  # noqa: BLE001 - test result should remain inspectable.
        payload["snapshot_error"] = display_text(exc)
    return payload


def ztare_run_command_from_display(display_command: Any) -> list[str]:
    parts = shlex.split(str(display_command or ""))
    if len(parts) < 3 or parts[:3] != ["ztare", "autoresearch", "run"]:
        raise ValueError("readiness command did not surface a bounded autoresearch command")
    return [SERVER_PYTHON, "-m", "src.ztare.cli", *parts[1:]]


def bounded_run_effective_settings(display_command: Any) -> dict[str, str]:
    parts = shlex.split(str(display_command or ""))
    transport = "subscription" if "--agent-judge" in parts or "--agent-mutator" in parts else "api"
    return {
        "mutator": cli_option_value(parts, "--mutator"),
        "judge": cli_option_value(parts, "--judge"),
        "inverter": cli_option_value(parts, "--inverter"),
        "llm_timeout_seconds": cli_option_value(parts, "--llm-timeout-seconds"),
        "llm_retries": cli_option_value(parts, "--llm-retries"),
        "model_fallback": "1" if "--allow-model-fallback" in parts else "0",
        "transport": transport,
        "judging": "committee" if "--dynamic" in parts else "single",
        "rubric_mode": "rotating" if "--auto-evolve" in parts else "fixed",
        "cross_family": "1" if "--cross-family" in parts else "0",
    }


def bounded_run_write_paths(project: str) -> list[str]:
    return [
        f"projects/{project}/workspace/iteration_telemetry.jsonl",
        f"projects/{project}/latest_eval_results.json",
        f"projects/{project}/workspace/eval_history.jsonl",
    ]


def run_status_payload(project: str = "") -> dict[str, Any]:
    """Live run progress for a project, FROM TELEMETRY (not process grepping). Shells out to
    `ztare autoresearch run-progress`, which reads iteration_telemetry.jsonl."""
    project = (project or snapshot.DEFAULT_PROJECT or "").strip()
    if not project:
        return {"ok": True, "running": False, "active": False, "runs": []}
    command = [SERVER_PYTHON, "-m", "src.ztare.cli", "autoresearch", "run-progress", "--project", project, "--json"]
    try:
        proc = snapshot.run(command, timeout=15)
        data = json.loads((proc.stdout or "").strip())
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "running": False, "active": False, "project": project, "error": str(exc)[:200]}
    data["running"] = bool(data.get("active"))
    # keep the legacy `runs` array shape so existing UI code stays happy
    data["runs"] = [data] if data.get("active") else []
    return data


def score_trajectory_payload(project: str) -> dict[str, Any]:
    """Score evolution within/across runs + rubric-change flag. Delegates to the CLI
    (`ztare autoresearch score-trajectory`) so the workbench and CLI stay in parity — this is a thin
    shell-out, not a re-implementation."""
    command = [
        SERVER_PYTHON,
        "-m",
        "src.ztare.cli",
        "autoresearch",
        "score-trajectory",
        "--project",
        project,
        "--json",
    ]
    try:
        proc = snapshot.run(command, timeout=30)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "project": project, "runs": [], "run_count": 0, "error": str(exc)[:300]}
    stdout = (proc.stdout or "").strip()
    if proc.returncode == 0 and stdout:
        try:
            return json.loads(stdout)
        except Exception:  # noqa: BLE001
            pass
    return {
        "ok": False,
        "project": project,
        "runs": [],
        "run_count": 0,
        "error": (proc.stderr or "score-trajectory CLI returned no JSON")[:300],
    }


def eval_results_payload(project: str, facet: str = "full") -> dict[str, Any]:
    """The run's epistemic payload (score, weakest_point, constraints ledger, …). Delegates to the CLI
    (`ztare autoresearch eval-results`) so workbench/CLI stay in parity — a thin shell-out, never a
    direct read of latest_eval_results.json."""
    safe_facet = facet if facet in (
        "full", "weakest", "debate", "trust", "constraints", "contract", "axioms", "dag",
        "open-questions", "discriminators", "inverter", "charter-drift", "meta-audit", "coherence"
    ) else "full"
    command = [
        SERVER_PYTHON, "-m", "src.ztare.cli", "autoresearch", "eval-results",
        "--project", project, "--facet", safe_facet, "--json",
    ]
    try:
        proc = snapshot.run(command, timeout=30)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "project": project, "error": str(exc)[:300]}
    stdout = (proc.stdout or "").strip()
    if stdout:
        try:
            return json.loads(stdout)
        except Exception:  # noqa: BLE001
            pass
    return {"ok": False, "project": project, "error": (proc.stderr or "eval-results CLI returned no JSON")[:300]}


def research_graph_payload(project: str) -> dict[str, Any]:
    """The research-landscape graph — a typed node/edge projection over the project's artifacts.
    Delegates to `ztare autoresearch research-graph` (CLI-first; never a direct kernel-file read)."""
    command = [
        SERVER_PYTHON, "-m", "src.ztare.cli", "autoresearch", "research-graph",
        "--project", project, "--json",
    ]
    try:
        proc = snapshot.run(command, timeout=30)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "project": project, "error": str(exc)[:300]}
    stdout = (proc.stdout or "").strip()
    if stdout:
        try:
            carrier = json.loads(stdout)
            return carrier
        except Exception:  # noqa: BLE001
            pass
    return {"ok": False, "project": project, "error": (proc.stderr or "research-graph CLI returned no JSON")[:300]}


def export_obsidian_payload(project: str) -> dict[str, Any]:
    """Export the verified research graph as an Obsidian vault (default: projects/<slug>/exports/obsidian).
    Delegates to `ztare autoresearch export-obsidian` (CLI-first)."""
    project = snapshot.validate_project_slug(project)
    command = [
        SERVER_PYTHON, "-m", "src.ztare.cli", "autoresearch", "export-obsidian",
        "--project", project, "--json",
    ]
    try:
        proc = snapshot.run(command, timeout=60)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "project": project, "error": str(exc)[:300]}
    stdout = (proc.stdout or "").strip()
    if stdout:
        try:
            return json.loads(stdout)
        except Exception:  # noqa: BLE001
            pass
    return {"ok": False, "project": project, "error": (proc.stderr or "export-obsidian CLI returned no JSON")[:300]}


def leanmill_state_via_cli() -> dict[str, Any]:
    """CLI-master: the LeanMill panel state comes from `ztare leanmill workbench-state --json` (a thin CLI
    door over the same kernel `state_payload`), not an in-process kernel-file read. Falls back to the
    in-process payload only if the CLI path is unavailable, so the panel never goes blank."""
    command = [SERVER_PYTHON, "-m", "src.ztare.cli", "leanmill", "workbench-state", "--json"]
    try:
        proc = snapshot.run(command, timeout=30)
        stdout = (proc.stdout or "").strip()
        if stdout:
            return json.loads(stdout)
    except Exception:  # noqa: BLE001 — fall back rather than blank the panel
        pass
    return leanmill_payloads.state_payload(repo=snapshot.REPO, storage=WORKBENCH_STORE)


def blocked_run_next_action(trace: dict[str, Any]) -> dict[str, str]:
    plan = trace.get("plan_preview") if isinstance(trace.get("plan_preview"), dict) else {}
    kernel = trace.get("kernel_entry") if isinstance(trace.get("kernel_entry"), dict) else {}
    blockers = [row for row in kernel.get("blockers") or [] if isinstance(row, dict)]
    blocker = next((row for row in blockers if row.get("next_command") or row.get("recovery_channel") or row.get("id")), {})
    command = str(blocker.get("next_command") or plan.get("recommended_first_command") or "")
    blocker_id = str(blocker.get("id") or blocker.get("recovery_channel") or "")
    if not blocker_id:
        missing = trace.get("blocking_missing")
        if isinstance(missing, list) and missing:
            blocker_id = str(missing[0] or "")
    label = "Run the first recovery step" if command else "Review run blockers"
    workspace = "run"
    subsection = "Ready to run"
    local_step = label
    if blocker_id == "out_of_loop_evidence_recovery":
        label = "Fetch or justify evidence gaps"
        workspace = "sources"
        subsection = "Prepare files"
        local_step = "Open evidence gaps"
    elif blocker_id == "evidence_prepare":
        label = "Prepare evidence"
        workspace = "sources"
        subsection = "Prepare files"
        local_step = "Prepare evidence"
    elif blocker_id == "scoring_guide":
        label = "Fix scoring guide"
        workspace = "run"
        subsection = "Ready to run"
        local_step = "Fix scoring guide"
    elif "preflight" in command:
        label = "Check readiness"
        workspace = "run"
        subsection = "Check readiness"
        local_step = "Check readiness"
    detail = f"Project is not ready for a run. First: {label}."
    return {
        "id": blocker_id or "blocked_before_run",
        "label": label,
        "detail": detail,
        "command": command,
        "workspace": workspace,
        "subsection": subsection,
        "local_step": local_step,
    }


def blocked_run_explanation(
    *,
    project: str,
    rubric: str,
    intake: str,
    next_action: dict[str, str],
) -> dict[str, Any]:
    blocker_id = str(next_action.get("id") or "")
    base: dict[str, Any] = {
        "schema": "ztare-forensic-workbench-run-blocker-explanation-v1",
        "blocker_id": blocker_id or "blocked_before_run",
        "summary": str(next_action.get("detail") or "Project is not ready for a run."),
        "why_it_blocks": "A run can only start after the project inputs and recovery steps are inspectable.",
        "closes_when": "Complete the named recovery step, then refresh run readiness.",
        "workspace": str(next_action.get("workspace") or ""),
        "subsection": str(next_action.get("subsection") or ""),
        "command": str(next_action.get("command") or ""),
        "receipt_paths": [],
        "write_paths": [],
    }
    if blocker_id != "out_of_loop_evidence_recovery":
        return base
    try:
        gap_payload = evidence_gap_list_payload_for_project(project=project, rubric=rubric, intake=intake)
    except Exception as exc:  # noqa: BLE001 - run blocker should remain readable.
        base["error"] = display_text(exc)
        return base
    active_gaps = gap_payload.get("active_gaps") if isinstance(gap_payload.get("active_gaps"), list) else []
    first_gap = next((row for row in active_gaps if isinstance(row, dict)), {})
    contract = first_gap.get("recovery_contract") if isinstance(first_gap.get("recovery_contract"), dict) else {}
    required_surface = str(first_gap.get("required_surface") or contract.get("required_surface") or "")
    fetch_query = str(first_gap.get("fetch_query") or "")
    target = str(first_gap.get("target") or contract.get("target") or "evidence gap")
    description = display_guidance_text(first_gap.get("description") or first_gap.get("producer_rationale") or "")
    base.update(
        {
            "summary": str(gap_payload.get("summary") or next_action.get("detail") or ""),
            "why_it_blocks": (
                "The project has an active evidence gap. Starting a run now would let the run treat "
                "missing support as if it had already been fetched or justified."
            ),
            "closes_when": (
                "Fetch a source for the missing surface, or save a hash-bound justification that explains "
                "why the gap no longer holds the project."
            ),
            "target": target,
            "missing_surface": required_surface,
            "question_to_answer": fetch_query,
            "description": description,
            "receipt_paths": [str(path) for path in gap_payload.get("receipt_paths") or [] if path],
            "write_paths": [str(path) for path in gap_payload.get("write_paths") or [] if path],
        }
    )
    return base


def bounded_run_payload_for_project(
    *,
    project: str,
    rubric: str | None = None,
    intake: str | None = None,
    renderer: str | None = None,
    scenario: str | None = None,
    confirmed: bool = False,
) -> dict[str, Any]:
    project = snapshot.validate_project_slug(project)
    rubric = rubric or project
    intake = intake or snapshot.default_intake_for_project(project)
    project_intake_path(project, intake, allow_examples=True)
    trace_before = trace_payload_for_project(project=project, rubric=rubric, intake=intake)
    plan = trace_before.get("plan_preview") or {}
    kernel = trace_before.get("kernel_entry") or {}
    display_command = apply_run_settings_to_autoresearch_command(
        str(kernel.get("run_command") or plan.get("recommended_first_command") or ""),
        project,
    )
    # A picked --scenario supplies the rubric + run bundle: strip the kernel's default --rubric and add
    # --scenario, so the scenario's rubric/config drive the run (matches the CLI precedence). display_command
    # is both shown and executed (below), so this threads the picker end-to-end. Cosmetic-safe: never raises.
    if scenario:
        try:
            _sp = shlex.split(display_command)
            if _sp[:3] == ["ztare", "autoresearch", "run"]:
                _sp = set_cli_option(_sp, "--rubric", "")
                if "--scenario" not in _sp:
                    _sp = _sp[:3] + ["--scenario", scenario] + _sp[3:]
                display_command = " ".join(shlex.quote(part) for part in _sp)
        except Exception:  # noqa: BLE001 — never break the run payload over command assembly
            pass
    plan_status = str(plan.get("status") or "")
    can_run = plan_status == "ready_for_bounded_run" and bool(kernel.get("can_enter_kernel"))
    run_paths = bounded_run_write_paths(project) if can_run else []
    run_receipt_path = run_paths[0] if run_paths else ""
    run_latest_path = run_paths[1] if len(run_paths) > 1 else run_receipt_path
    write_boundary = write_boundary_payload(
        writes_project_files=bool(can_run and confirmed),
        write_paths=run_paths if confirmed else [],
        receipt_path=run_receipt_path if can_run and confirmed else "",
        latest_path=run_latest_path if can_run and confirmed else "",
        read_only_actions=["Inspect readiness", "Copy command"],
    )
    confirmed_write_boundary = write_boundary_payload(
        writes_project_files=bool(can_run),
        write_paths=run_paths,
        receipt_path=run_receipt_path,
        latest_path=run_latest_path,
        read_only_actions=["Inspect readiness", "Copy command"],
    )
    payload: dict[str, Any] = {
        "schema": BOUNDED_RUN_SCHEMA,
        "served_from": "local_api",
        "project": project,
        "rubric": rubric,
        "intake": intake,
        "project_key": case_key(project, intake),
        "case_key": case_key(project, intake),
        "label": "Project run",
        "command": display_command,
        "effective_settings": bounded_run_effective_settings(display_command),
        "plan_status": plan_status,
        "can_run": can_run,
        "requires_confirmation": bool(can_run and not confirmed),
        "accepted": False,
        "returncode": None,
        "stdout_tail": "",
        "stderr_tail": "",
        "writes": False,
        "trace_before": trace_before,
        "trace": None,
        "run_history": None,
        "snapshot": None,
        "write_boundary": write_boundary,
        "confirmed_write_boundary": confirmed_write_boundary,
        "model_spend_starts_at": "confirmed_project_run",
    }
    if not can_run:
        next_action = blocked_run_next_action(trace_before)
        blocker_explanation = blocked_run_explanation(
            project=project,
            rubric=rubric,
            intake=intake,
            next_action=next_action,
        )
        payload["ok"] = False
        payload["status"] = "blocked_before_run"
        payload["display_status"] = "blocked before run"
        payload["next_action"] = next_action
        payload["blocker_explanation"] = blocker_explanation
        payload["error"] = next_action["detail"]
        return payload
    if not confirmed:
        payload["ok"] = True
        payload["status"] = "needs_confirmation"
        payload["display_status"] = "needs confirmation"
        payload["message"] = "Review the project run before starting model work."
        return payload
    command = ztare_run_command_from_display(display_command)
    proc = snapshot.run(command, timeout=1800)
    payload.update(
        {
            "ok": proc.returncode == 0,
            "accepted": proc.returncode == 0,
            "returncode": proc.returncode,
            "writes": True,
            "stdout_tail": tail_display_text(proc.stdout),
            "stderr_tail": tail_display_text(proc.stderr),
        }
    )
    try:
        payload["trace"] = trace_payload_for_project(project=project, rubric=rubric, intake=intake)
    except SystemExit as exc:
        payload["trace_error"] = display_text(exc)
    except Exception as exc:  # noqa: BLE001 - run output should still be inspectable.
        payload["trace_error"] = display_text(exc)
    try:
        payload["run_history"] = run_history_payload_for_project(project=project, rubric=rubric, intake=intake)
    except SystemExit as exc:
        payload["run_history_error"] = display_text(exc)
    except Exception as exc:  # noqa: BLE001 - run output should still be inspectable.
        payload["run_history_error"] = display_text(exc)
    try:
        payload["snapshot"] = snapshot_payload_for_project(
            project=project,
            rubric=rubric,
            intake=intake,
            renderer=renderer,
        )
    except SystemExit as exc:
        payload["snapshot_error"] = display_text(exc)
    except Exception as exc:  # noqa: BLE001 - run output should still be inspectable.
        payload["snapshot_error"] = display_text(exc)
    return payload


def _workbench_jobs_root() -> Path:
    return snapshot.REPO / ".workbench" / "jobs"


def bounded_run_job_payload(*, project: str, rubric: str | None = None, intake: str | None = None,
                            renderer: str | None = None, scenario: str | None = None) -> dict[str, Any]:
    """Launch the already-previewed kernel command behind the shared durable job contract."""
    from ztare.workspace.jobs import launch_job

    preview = bounded_run_payload_for_project(
        project=project, rubric=rubric, intake=intake, renderer=renderer, scenario=scenario, confirmed=False,
    )
    if not preview.get("can_run"):
        return preview
    command = ztare_run_command_from_display(str(preview.get("command") or ""))
    job = launch_job(
        root=_workbench_jobs_root(), command=command, cwd=snapshot.REPO, env=load_workbench_env(),
        kind="autoresearch_run", project=project, label="Project run",
        context={"rubric": rubric or project, "intake": intake or "", "renderer": renderer or "",
                 "scenario": scenario or "", "write_boundary": preview.get("confirmed_write_boundary") or {}},
    )
    return {**preview, "ok": True, "accepted": True, "status": "queued", "job": job,
            "writes": True, "write_boundary": preview.get("confirmed_write_boundary") or {}}


def workbench_job_payload(job_id: str) -> dict[str, Any]:
    from ztare.workspace.jobs import read_job

    try:
        job = read_job(_workbench_jobs_root(), job_id)
        require_visible_project(str(job.get("project") or ""))
        return {"ok": True, "job": job}
    except (OSError, ValueError) as exc:
        return {"ok": False, "error": f"unknown job: {display_text(exc)}"}


def workbench_job_cancel_payload(job_id: str) -> dict[str, Any]:
    from ztare.workspace.jobs import cancel_job, read_job

    try:
        existing = read_job(_workbench_jobs_root(), job_id)
        require_visible_project(str(existing.get("project") or ""))
        return {"ok": True, "job": cancel_job(_workbench_jobs_root(), job_id)}
    except (OSError, ValueError) as exc:
        return {"ok": False, "error": f"unknown job: {display_text(exc)}"}


def workbench_jobs_payload(project: str = "") -> dict[str, Any]:
    from ztare.workspace.jobs import list_jobs

    jobs = list_jobs(_workbench_jobs_root(), project=project)
    return {"ok": True, "jobs": [job for job in jobs if project_is_visible(str(job.get("project") or ""))]}


def file_sha256_for_display_path(value: Any) -> str:
    path_text = display_path(value)
    if not path_text:
        return ""
    path = Path(path_text)
    if not path.is_absolute():
        path = snapshot.REPO / path
    try:
        resolved = path.resolve()
        if not path_under(resolved, snapshot.REPO.resolve()) or not resolved.is_file():
            return ""
        return hashlib.sha256(WORKBENCH_STORE.read_bytes(resolved)).hexdigest()
    except (OSError, ValueError):
        return ""


def first_bound_artifact(receipt: dict[str, Any]) -> tuple[str, str]:
    artifacts = receipt.get("artifacts") or []
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            continue
        artifact_path = display_path(artifact.get("path"))
        if artifact_path:
            return artifact_path, str(artifact.get("sha256") or "")
    return "", ""


def source_action_payload_for_project(
    *,
    project: str,
    action: str,
    rubric: str | None = None,
    intake: str | None = None,
    renderer: str | None = None,
    confirmed: bool = False,
) -> dict[str, Any]:
    project = snapshot.validate_project_slug(project)
    rubric = rubric or project
    intake = intake or snapshot.default_intake_for_project(project)
    project_intake_path(project, intake, allow_examples=True)
    command_context = workbench_command_context(project, rubric)
    core_payload = source_actions_core.run_source_action(
        project=project,
        action=action,
        rubric=rubric,
        intake=intake,
        confirmed=confirmed,
        root=snapshot.REPO,
        storage=WORKBENCH_STORE,
        python_executable=SERVER_PYTHON,
        context=command_context,
    )
    payload: dict[str, Any] = {
        **core_payload,
        "served_from": "local_api",
        "stdout_tail": tail_display_text(str(core_payload.get("stdout_tail") or "")),
        "stderr_tail": tail_display_text(str(core_payload.get("stderr_tail") or "")),
        "parsed_output": display_data(core_payload.get("parsed_output") or {}),
        "trace": None,
        "snapshot": None,
    }
    if payload.get("requires_confirmation") and not confirmed:
        payload["write_boundary"] = write_boundary_payload(
            writes_project_files=False,
            read_only_actions=["review files that may change", "copy command", "confirm in app"],
        )
        payload["confirmed_write_boundary"] = write_boundary_payload(
            writes_project_files=True,
            write_paths=list(payload.get("write_paths") or []),
            receipt_path=str(payload.get("receipt_path") or ""),
            latest_path=str(payload.get("latest") or ""),
            read_only_actions=["review files that may change", "copy command"],
        )
        payload["model_spend_starts_at"] = "confirmed_source_action"
        payload["confirmation_reason"] = "This action can call configured models while preparing evidence."
        return payload
    if payload.get("writes"):
        payload.update(
            {
                "write_boundary": write_boundary_payload(
                    writes_project_files=True,
                    write_paths=list(payload.get("write_paths") or []),
                    receipt_path=str(payload.get("receipt_path") or ""),
                    latest_path=str(payload.get("latest") or ""),
                ),
            }
        )
    else:
        payload["write_boundary"] = write_boundary_payload(
            writes_project_files=False,
            read_only_actions=["inspect server response", "preview", "copy"],
        )
    try:
        payload["trace"] = trace_payload_for_project(project=project, rubric=rubric, intake=intake)
    except SystemExit as exc:
        payload["trace_error"] = display_text(exc)
    except Exception as exc:  # noqa: BLE001 - action result should still be inspectable.
        payload["trace_error"] = display_text(exc)
    try:
        payload["snapshot"] = snapshot_payload_for_project(
            project=project,
            rubric=rubric,
            intake=intake,
            renderer=renderer,
        )
    except SystemExit as exc:
        payload["snapshot_error"] = display_text(exc)
    except Exception as exc:  # noqa: BLE001 - action result should still be inspectable.
        payload["snapshot_error"] = display_text(exc)
    return payload


def evidence_fetch_expected_paths(project: str, *, auto_compile: str = "1") -> list[str]:
    paths = [
        f"projects/{project}/evidence.txt",
        f"projects/{project}/raw/evidence_fetch_<timestamp>.md",
        f"projects/{project}/workspace/evidence_fetch_manifest_<timestamp>.json",
        f"projects/{project}/workspace/forensic_workbench_evidence_fetches.jsonl",
        f"projects/{project}/workspace/forensic_workbench_latest_evidence_fetch.json",
    ]
    if auto_compile == "1":
        paths.extend(
            [
                f"projects/{project}/workspace/source_index.json",
                f"projects/{project}/workspace/source_index_receipt.json",
                f"projects/{project}/workspace/workspace_meta.json",
                f"projects/{project}/compiled_evidence_provenance.json",
                f"projects/{project}/compiled_evidence_packet.json",
                f"projects/{project}/compiled_evidence_replay_manifest.json",
            ]
        )
    return paths


def evidence_fetch_command(
    project: str, rubric: str | None = None, *, target: str = ""
) -> tuple[list[str], str, dict[str, str]]:
    context = workbench_command_context(project, rubric)
    command = evidence_fetch_command_from_context(context, target=target)
    return command, display_command(command), context


def evidence_fetch_command_from_context(context: dict[str, str], *, target: str = "") -> list[str]:
    command = [
        SERVER_PYTHON,
        "-m",
        "src.ztare.cli",
        "project",
        "evidence-fetch",
        "--project",
        context["project"],
        "--severity",
        context["fetch_severity"],
        "--max-fetches",
        context["max_fetches"],
        "--search-backend",
        context["evidence_search_backend"],
    ]
    if context["model"]:
        command.extend(["--model", context["model"]])
    if context["auto_compile"] != "1":
        command.append("--no-auto-compile")
    # A single-gap fetch from the Evidence surface overrides the severity batch:
    # the user already picked this gap, so fetch it whatever its severity.
    if (target or "").strip():
        command.extend(["--target", target.strip(), "--max-fetches", "1"])
    return command


def latest_evidence_fetch_manifest(workspace: Path) -> Path | None:
    manifests = sorted(
        workspace.glob("evidence_fetch_manifest_*.json"),
        key=lambda path: path.stat().st_mtime if path.exists() else 0,
        reverse=True,
    )
    return manifests[0] if manifests else None


def evidence_fetch_payload_for_project(
    *,
    project: str,
    rubric: str | None = None,
    intake: str | None = None,
    renderer: str | None = None,
    confirmed: bool = False,
    target: str = "",
) -> dict[str, Any]:
    project = snapshot.validate_project_slug(project)
    rubric = rubric or project
    intake = intake or snapshot.default_intake_for_project(project)
    try:  # a bare/scenario project has no intake — fetch still works: it reads workspace gaps or a --target, and fetch_evidence bootstraps raw/
        project_intake_path(project, intake, allow_examples=True)
        intake_present = True
    except FileNotFoundError:
        intake_present = False
    project_root = snapshot.REPO / "projects" / project
    workspace = project_root / "workspace"
    command, command_display, context = evidence_fetch_command(project, rubric, target=target)
    write_paths = evidence_fetch_expected_paths(project, auto_compile=context["auto_compile"])
    gap_payload: dict[str, Any] = {}
    gap_payload_error = ""
    try:
        gap_payload = evidence_gap_list_payload_for_project(project=project, rubric=rubric, intake=intake)
    except Exception as exc:  # noqa: BLE001 - fetch preview should still show command/boundary.
        gap_payload_error = display_text(exc)
    preview_boundary = write_boundary_payload(
        writes_project_files=False,
        read_only_actions=["review active gaps", "copy command", "confirm in app"],
    )
    confirmed_boundary = write_boundary_payload(
        writes_project_files=True,
        write_paths=write_paths,
        receipt_path=f"projects/{project}/workspace/forensic_workbench_evidence_fetches.jsonl",
        latest_path=f"projects/{project}/workspace/forensic_workbench_latest_evidence_fetch.json",
        read_only_actions=["review active gaps", "copy command"],
    )
    payload: dict[str, Any] = {
        "schema": EVIDENCE_FETCH_SCHEMA,
        "served_from": "local_api",
        "project": project,
        "rubric": rubric,
        "intake": intake,
        "intake_present": intake_present,
        "label": "Fetch evidence",
        "command": command_display,
        "settings": context,
        "writes": True,
        "requires_confirmation": True,
        "accepted": False,
        "ok": False,
        "returncode": None,
        "stdout_tail": "",
        "stderr_tail": "",
        "parsed_output": {},
        "evidence_gaps": gap_payload,
        "evidence_gaps_error": gap_payload_error,
        "gap_count": safe_int(gap_payload.get("gap_count")) if gap_payload else 0,
        "active_gap_count": safe_int(gap_payload.get("active_gap_count")) if gap_payload else 0,
        "gap_summary": str(gap_payload.get("summary") or "") if gap_payload else "",
        "active_gaps": gap_payload.get("active_gaps", []) if gap_payload else [],
        "write_boundary": preview_boundary,
        "confirmed_write_boundary": confirmed_boundary,
        "model_spend_starts_at": "confirmed_evidence_fetch",
        "confirmation_reason": "This action can call configured web-search/model providers and write evidence files.",
    }
    if not confirmed:
        payload.update({"status": "needs_confirmation", "ok": True})
        return payload

    before_manifest = latest_evidence_fetch_manifest(workspace)
    proc = run_workbench_command(command, timeout=900)
    after_manifest = latest_evidence_fetch_manifest(workspace)
    manifest_path = after_manifest if after_manifest and after_manifest != before_manifest else after_manifest
    manifest: dict[str, Any] = {}
    if manifest_path and manifest_path.exists():
        try:
            manifest = read_json_object(manifest_path, "evidence fetch manifest")
        except Exception:
            manifest = {}
    total_attempted = safe_int(manifest.get("total_attempted"))
    total_accepted = safe_int(manifest.get("total_accepted"))
    failure_counts, recovery_hints = evidence_fetch_manifest_reason_fields(manifest)
    fetch_accepted = proc.returncode == 0 and (total_attempted == 0 or total_accepted > 0)
    fetch_status = "accepted" if fetch_accepted else ("no_new_evidence" if proc.returncode == 0 else "failed")
    ledger_path = workspace / "forensic_workbench_evidence_fetches.jsonl"
    latest_path = workspace / "forensic_workbench_latest_evidence_fetch.json"
    receipt = add_case_context(
        {
            "schema": EVIDENCE_FETCH_RECEIPT_SCHEMA,
            "applied_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "project": project,
            "command": command_display,
            "returncode": proc.returncode,
            "accepted": fetch_accepted,
            "status": fetch_status,
            "manifest_path": repo_rel(manifest_path) if manifest_path else "",
            "manifest_sha256": file_sha256_for_display_path(repo_rel(manifest_path)) if manifest_path else "",
            "total_attempted": total_attempted,
            "total_accepted": total_accepted,
            "skipped_duplicates": safe_int(manifest.get("skipped_duplicates")),
            "search_backend": str(manifest.get("search_backend") or context["evidence_search_backend"]),
            "severity": context["fetch_severity"],
            "failure_counts": failure_counts,
            "recovery_hints": recovery_hints,
        },
        project=project,
        rubric=rubric,
        intake=intake,
    )
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json") as staged:
        json.dump(receipt, staged)
        staged.flush()
        receipt_result = ztare_cli_payload([
            "forensic-workbench", "record-evidence-fetch",
            "--project", project,
            "--from", staged.name,
            "--repo", str(snapshot.REPO),
            "--json",
        ], project=project, timeout=90)
    if receipt_result.get("ok") is False:
        payload.update({
            "ok": False,
            "accepted": False,
            "status": "receipt_failed",
            "returncode": proc.returncode,
            "error": str(receipt_result.get("error") or "evidence fetch completed but its receipt could not be recorded"),
        })
        return payload
    ledger_path = snapshot.REPO / str(receipt_result.get("receipt_path"))
    latest_path = snapshot.REPO / str(receipt_result.get("latest"))
    payload.update(
        {
            "ok": proc.returncode == 0,
            "accepted": fetch_accepted,
            "status": fetch_status,
            "returncode": proc.returncode,
            "stdout_tail": tail_display_text(proc.stdout),
            "stderr_tail": tail_display_text(proc.stderr),
            "parsed_output": display_data(manifest),
            "manifest_path": repo_rel(manifest_path) if manifest_path else "",
            "receipt_path": repo_rel(ledger_path),
            "latest": repo_rel(latest_path),
            "receipt": receipt,
            "write_boundary": write_boundary_payload(
                writes_project_files=True,
                write_paths=[
                    *(path for path in write_paths if "<timestamp>" not in path),
                    repo_rel(manifest_path) if manifest_path else "",
                ],
                receipt_path=repo_rel(ledger_path),
                latest_path=repo_rel(latest_path),
            ),
        }
    )
    if gap_payload_error:
        payload["evidence_gaps_error"] = gap_payload_error
    else:
        try:
            payload["evidence_gaps"] = evidence_gap_list_payload_for_project(project=project, rubric=rubric, intake=intake)
        except Exception as exc:  # noqa: BLE001 - fetch result should still be inspectable.
            payload["evidence_gaps_error"] = display_text(exc)
    try:
        payload["claim_support"] = claim_support_payload_for_project(project=project, rubric=rubric, intake=intake)
    except Exception as exc:  # noqa: BLE001 - fetch result should still be inspectable.
        payload["claim_support_error"] = display_text(exc)
    try:
        payload["snapshot"] = snapshot_payload_for_project(project=project, rubric=rubric, intake=intake, renderer=renderer)
    except Exception as exc:  # noqa: BLE001 - fetch result should still be inspectable.
        payload["snapshot_error"] = display_text(exc)
    return payload


def evidence_fetch_job_payload(*, project: str, rubric: str | None = None, intake: str | None = None,
                               renderer: str | None = None, target: str = "") -> dict[str, Any]:
    """Launch a confirmed evidence fetch behind the shared durable job contract."""
    from ztare.workspace.jobs import launch_job

    preview = evidence_fetch_payload_for_project(
        project=project, rubric=rubric, intake=intake, renderer=renderer, confirmed=False, target=target)
    if not preview.get("ok"):
        return preview
    command, _display, context = evidence_fetch_command(project, rubric or project, target=target)
    job = launch_job(
        root=_workbench_jobs_root(), command=command, cwd=snapshot.REPO, env=load_workbench_env(),
        kind="evidence_fetch", project=project, label="Evidence fetch",
        context={"rubric": rubric or project, "intake": intake or "", "renderer": renderer or "",
                 "target": target, "settings": context,
                 "write_boundary": preview.get("confirmed_write_boundary") or {}},
    )
    return {**preview, "ok": True, "accepted": True, "status": "queued", "job": job,
            "writes": True, "write_boundary": preview.get("confirmed_write_boundary") or {}}


def evidence_gap_list_payload_for_project(
    *,
    project: str,
    rubric: str | None = None,
    intake: str | None = None,
) -> dict[str, Any]:
    project = snapshot.validate_project_slug(project)
    rubric = rubric or project
    intake = intake or snapshot.default_intake_for_project(project)
    if intake:  # soft: evidence gaps live in the workspace store, not the intake — list them even with no intake file
        try:
            project_intake_path(project, intake, allow_examples=True)
        except FileNotFoundError:
            pass
    command = [
        SERVER_PYTHON,
        "-m",
        "src.ztare.cli",
        "project",
        "evidence-gap",
        "list",
        "--project",
        project,
        "--json",
    ]
    proc = snapshot.run(command, timeout=90)
    parsed: dict[str, Any] = {}
    try:
        parsed = snapshot.extract_last_json_object(proc.stdout)
    except Exception:
        parsed = {}
    project_root = snapshot.REPO / "projects" / project
    local_recovery = local_evidence_gap_recovery_payload(project=project, project_root=project_root)
    parsed_gaps = parsed.get("evidence_gaps") if isinstance(parsed.get("evidence_gaps"), list) else []
    local_gaps = local_recovery.get("gaps") if isinstance(local_recovery.get("gaps"), list) else []
    gaps = parsed_gaps or local_gaps
    active_count = safe_int(parsed.get("active_evidence_gap_count") or len(gaps) or local_recovery.get("gap_count"))
    source_path = display_path(parsed.get("source_path")) or str(local_recovery.get("file") or "")
    status = str(local_recovery.get("status") or ("needs evidence recovery" if active_count else "none"))
    fetch_command = evidence_fetch_command(project, rubric)[1]
    result: dict[str, Any] = {
        "schema": EVIDENCE_GAP_LIST_SCHEMA,
        "served_from": "local_api",
        "project": project,
        "rubric": rubric,
        "intake": intake,
        "project_key": case_key(project, intake),
        "case_key": case_key(project, intake),
        "command": f"ztare project evidence-gap list --project {project} --json",
        "returncode": proc.returncode,
        "accepted": proc.returncode == 0,
        "ok": proc.returncode == 0,
        "status": status,
        "display_status": display_status(status),
        "source_path": source_path,
        "gap_count": active_count,
        "active_gap_count": active_count,
        "active_evidence_gap_count": active_count,
        "warnings": display_text_lines(parsed.get("warnings") or [], limit=8),
        "evidence_gaps": display_data(gaps[:12]),
        "active_gaps": display_data(gaps[:12]),
        "receipt_paths": [str(path) for path in local_recovery.get("receipt_paths", []) if path],
        "write_paths": [str(path) for path in local_recovery.get("write_paths", []) if path],
        "fetch_receipt_paths": [str(path) for path in local_recovery.get("fetch_receipt_paths", []) if path],
        "fetch_write_paths": [str(path) for path in local_recovery.get("fetch_write_paths", []) if path],
        "justify_receipt_paths": [str(path) for path in local_recovery.get("justify_receipt_paths", []) if path],
        "justify_write_paths": [str(path) for path in local_recovery.get("justify_write_paths", []) if path],
        "summary": str(local_recovery.get("summary") or ""),
        "fetch_command": fetch_command,
        "next_action": display_data(parsed.get("next_action") if isinstance(parsed.get("next_action"), dict) else {}),
        "stdout_tail": tail_display_text(proc.stdout),
        "stderr_tail": tail_display_text(proc.stderr),
        "write_boundary": write_boundary_payload(
            writes_project_files=False,
            read_only_actions=["inspect active evidence gaps", "preview source", "copy recovery step"],
        ),
    }
    return result


def evidence_gap_justify_command_display(
    *,
    project: str,
    selector_flag: str,
    selector_value: str,
    status: str,
    reason: str,
    evidence_refs: list[str],
) -> str:
    parts = [
        "ztare",
        "project",
        "evidence-gap",
        "justify",
        "--project",
        project,
        "--source",
        "active",
        selector_flag,
        selector_value,
        "--status",
        status,
        "--reason",
        reason,
    ]
    for ref in evidence_refs:
        parts.extend(["--evidence-ref", ref])
    parts.append("--json")
    return " ".join(shlex.quote(part) for part in parts)


def evidence_gap_justify_payload_for_project(
    *,
    project: str,
    selector: dict[str, Any],
    reason: str,
    status: str = "justified",
    evidence_refs: list[str] | None = None,
    rubric: str | None = None,
    intake: str | None = None,
) -> dict[str, Any]:
    project = snapshot.validate_project_slug(project)
    rubric = rubric or project
    intake = intake or snapshot.default_intake_for_project(project)
    if intake:
        project_intake_path(project, intake, allow_examples=True)
    normalized_reason = " ".join(str(reason or "").strip().split())
    if len(normalized_reason) < 16:
        raise ValueError("Evidence-gap justification needs a specific reason of at least 16 characters.")
    normalized_status = str(status or "justified").strip().lower()
    if normalized_status not in {"justified", "not_applicable", "waived"}:
        raise ValueError("Evidence-gap status must be justified, not_applicable, or waived.")
    refs = unique_values([str(ref or "").strip() for ref in (evidence_refs or [])])
    selector_flag = ""
    selector_value = ""
    if selector.get("gap_id"):
        selector_flag = "--gap-id"
        selector_value = str(selector.get("gap_id") or "").strip()
    elif selector.get("target"):
        selector_flag = "--target"
        selector_value = str(selector.get("target") or "").strip()
    else:
        index_value = selector.get("index")
        if index_value is None:
            raise ValueError("Choose an evidence gap to justify.")
        selector_flag = "--index"
        selector_value = str(int(index_value))
    if not selector_value:
        raise ValueError("Choose an evidence gap to justify.")

    command = [
        SERVER_PYTHON,
        "-m",
        "src.ztare.cli",
        "project",
        "evidence-gap",
        "justify",
        "--project",
        project,
        "--source",
        "active",
        selector_flag,
        selector_value,
        "--status",
        normalized_status,
        "--reason",
        normalized_reason,
    ]
    for ref in refs:
        command.extend(["--evidence-ref", ref])
    command.append("--json")
    proc = snapshot.run(command, timeout=90)
    parsed: dict[str, Any] = {}
    try:
        parsed = snapshot.extract_last_json_object(proc.stdout)
    except Exception:
        parsed = {}
    receipt_path = display_path(parsed.get("path")) or f"projects/{project}/workspace/evidence_gap_resolutions.json"
    receipt_sha256 = file_sha256_for_display_path(receipt_path)
    resolution = parsed.get("resolution") if isinstance(parsed.get("resolution"), dict) else {}
    response: dict[str, Any] = {
        "schema": EVIDENCE_GAP_JUSTIFY_SCHEMA,
        "served_from": "local_api",
        "project": project,
        "rubric": rubric,
        "intake": intake,
        "project_key": case_key(project, intake),
        "case_key": case_key(project, intake),
        "command": evidence_gap_justify_command_display(
            project=project,
            selector_flag=selector_flag,
            selector_value=selector_value,
            status=normalized_status,
            reason=normalized_reason,
            evidence_refs=refs,
        ),
        "returncode": proc.returncode,
        "accepted": proc.returncode == 0,
        "ok": proc.returncode == 0,
        "receipt_path": receipt_path,
        "receipt_sha256": receipt_sha256,
        "resolution": display_data(resolution),
        "resolution_count": safe_int(parsed.get("resolution_count")),
        "stdout_tail": tail_display_text(proc.stdout),
        "stderr_tail": tail_display_text(proc.stderr),
        "write_boundary": (
            write_boundary_payload(
                writes_project_files=True,
                write_paths=[receipt_path],
                receipt_path=receipt_path,
                latest_path=receipt_path,
            )
            if proc.returncode == 0
            else failed_write_boundary_payload(
                write_paths=[receipt_path],
                receipt_path=receipt_path,
                latest_path=receipt_path,
                read_only_actions=["inspect error", "fix reason or evidence path", "retry"],
            )
        ),
        "evidence_gaps": None,
        "snapshot": None,
    }
    if proc.returncode == 0:
        try:
            response["evidence_gaps"] = evidence_gap_list_payload_for_project(project=project, rubric=rubric, intake=intake)
        except Exception as exc:  # noqa: BLE001 - saved resolution should still be inspectable.
            response["evidence_gaps_error"] = display_text(exc)
        try:
            response["snapshot"] = snapshot_payload_for_project(
                project=project,
                rubric=rubric,
                intake=intake,
                renderer=snapshot.DEFAULT_RENDERER,
            )
        except Exception as exc:  # noqa: BLE001 - saved resolution should still be inspectable.
            response["snapshot_error"] = display_text(exc)
    return response


def raw_recovery_filename(raw_dir: Path, source_path: Path) -> str:
    base = source_path.name
    if not SOURCE_IMPORT_FILENAME_RE.fullmatch(base):
        stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", source_path.stem).strip("._-") or "source"
        base = f"{stem[:80]}{source_path.suffix.lower()}"
    candidate = base
    index = 2
    while (raw_dir / candidate).exists():
        if (raw_dir / candidate).resolve() == source_path.resolve():
            return candidate
        candidate = f"{Path(base).stem}_{index}{Path(base).suffix}"
        index += 1
    return candidate


def unique_values(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def uploaded_source_rows_for_project(value: Any, *, limit: int = 20) -> list[dict[str, Any]]:
    if value in (None, ""):
        return []
    if not isinstance(value, list):
        raise ValueError("uploaded_sources must be a list")
    rows: list[dict[str, str]] = []
    for index, item in enumerate(value[:limit], start=1):
        if not isinstance(item, dict):
            raise ValueError(f"uploaded source {index} must be an object")
        filename = str(item.get("filename") or "").strip()
        source_type = str(item.get("source_type") or "source_evidence").strip()
        if source_type not in SOURCE_IMPORT_TYPES:
            raise ValueError(f"uploaded source {index} source_type must be one of: {', '.join(sorted(SOURCE_IMPORT_TYPES))}")
        original_base64 = str(item.get("original_base64") or "").strip()
        if original_base64:
            original_filename = str(item.get("original_filename") or filename).strip()
            if not DOCUMENT_IMPORT_FILENAME_RE.fullmatch(original_filename):
                raise ValueError(f"uploaded source {index} has an unsupported or nested document filename")
            try:
                original_bytes = base64.b64decode(original_base64, validate=True)
            except (binascii.Error, ValueError) as exc:
                raise ValueError(f"uploaded source {index} is not valid base64") from exc
            from ztare.workspace.document_ingest import extract_document_bytes
            extraction = extract_document_bytes(original_filename, original_bytes)
            filename = extraction["extracted_filename"]
            body = extraction["text"]
            rows.append({"filename": filename, "source_type": source_type, "body": body,
                         "original_filename": original_filename, "original_bytes": original_bytes,
                         "original_sha256": extraction["sha256"],
                         "extraction_method": extraction["extraction_method"],
                         "extraction_truncated": extraction["truncated"]})
            continue
        if not SOURCE_IMPORT_FILENAME_RE.fullmatch(filename):
            raise ValueError(f"uploaded source {index} filename must be a flat .md or .txt name")
        body = str(item.get("body") or "")
        if not body.strip():
            raise ValueError(f"uploaded source {index} body is required")
        rows.append({"filename": filename, "source_type": source_type, "body": body})
    return rows


def stage_uploaded_source_rows(project: str, rows: list[dict[str, Any]]) -> tuple[list[str], list[str], list[str]]:
    if not rows:
        return [], [], []
    project_root = snapshot.REPO / "projects" / project
    raw_dir = project_root / "raw"
    if not raw_dir.exists():
        raise FileNotFoundError(f"source file directory does not exist: {repo_rel(raw_dir)}")
    source_refs: list[str] = []
    evidence_refs: list[str] = []
    write_paths: list[str] = []
    for row in rows:
        source_type = row["source_type"]
        filename = str(row["filename"])
        target = raw_dir / filename
        body = row["body"].rstrip()
        if target.exists():
            existing_type, existing_body = split_source_frontmatter(
                WORKBENCH_STORE.read_text(target),
                fallback_source_type=source_type,
            )
            if existing_body.rstrip() == body:
                source_type = existing_type if existing_type in SOURCE_IMPORT_TYPES else source_type
                ref = repo_rel(target)
                (evidence_refs if source_type == "source_evidence" else source_refs).append(ref)
                continue
            filename = raw_recovery_filename(raw_dir, project_root / "uploads" / filename)
        args = [
            "project", "source-file", "add",
            "--project", project,
            "--rubric", project,
            "--intake", snapshot.default_intake_for_project(project),
            "--filename", filename,
            "--source-type", source_type,
            "--kind", "raw_evidence",
            "--repo", str(snapshot.REPO),
            "--json",
        ]
        original_bytes = row.get("original_bytes")
        if isinstance(original_bytes, bytes):
            with tempfile.NamedTemporaryFile("wb", suffix=Path(str(row["original_filename"])).suffix) as staged_original, tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".md") as staged_body:
                staged_original.write(original_bytes)
                staged_original.flush()
                staged_body.write(body)
                staged_body.flush()
                result = ztare_cli_payload([
                    *args,
                    "--body-file", staged_body.name,
                    "--original-file", staged_original.name,
                    "--original-filename", str(row["original_filename"]),
                    "--extraction-method", str(row.get("extraction_method") or ""),
                    *(["--extraction-truncated"] if row.get("extraction_truncated") else []),
                ], project=project, timeout=90)
        else:
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".md") as staged_body:
                staged_body.write(body)
                staged_body.flush()
                result = ztare_cli_payload([*args, "--body-file", staged_body.name], project=project, timeout=90)
        if result.get("ok") is False:
            raise ValueError(str(result.get("error") or "uploaded source was refused"))
        ref = str(result.get("source_path") or f"projects/{project}/raw/{filename}")
        write_paths.extend(str(path) for path in (result.get("write_paths") or []) if path)
        if source_type == "source_evidence":
            evidence_refs.append(ref)
        else:
            source_refs.append(ref)
    return unique_values(source_refs), unique_values(evidence_refs), unique_values(write_paths)


def stage_recovered_source_refs(project: str, refs: list[str]) -> tuple[list[str], list[str]]:
    """Copy selected historical project files into raw/ so source-check can see them."""

    project_root = snapshot.REPO / "projects" / project
    raw_dir = project_root / "raw"
    if not raw_dir.exists():
        raise FileNotFoundError(f"source file directory does not exist: {repo_rel(raw_dir)}")
    staged_refs: list[str] = []
    write_paths: list[str] = []
    for ref in refs:
        ref = str(ref or "").strip()
        if not ref:
            continue
        if EXTERNAL_REF_RE.match(ref):
            staged_refs.append(ref)
            continue
        source_path = (snapshot.REPO / ref).resolve()
        if (
            not source_path.exists()
            or not source_path.is_file()
            or source_path.suffix.lower() not in {".md", ".txt"}
            or not path_under(source_path, project_root)
        ):
            staged_refs.append(ref)
            continue
        if path_under(source_path, raw_dir):
            staged_refs.append(repo_rel(source_path))
            continue
        source_text = WORKBENCH_STORE.read_text(source_path)
        source_type, body = split_source_frontmatter(source_text, fallback_source_type="source_evidence")
        if not body.strip():
            continue
        if source_type == "untyped":
            source_type = "source_evidence"
        filename = source_path.name
        target = raw_dir / filename
        if target.exists():
            _existing_type, existing_body = split_source_frontmatter(
                WORKBENCH_STORE.read_text(target), fallback_source_type=source_type,
            )
            if existing_body.rstrip() == body.rstrip():
                staged_refs.append(repo_rel(target))
                continue
            filename = raw_recovery_filename(raw_dir, source_path)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".md") as staged_body:
            staged_body.write(body)
            staged_body.flush()
            result = ztare_cli_payload([
                "project", "source-file", "add",
                "--project", project,
                "--rubric", project,
                "--intake", snapshot.default_intake_for_project(project),
                "--filename", filename,
                "--source-type", source_type,
                "--kind", "raw_evidence",
                "--body-file", staged_body.name,
                "--repo", str(snapshot.REPO),
                "--json",
            ], project=project, timeout=90)
        if result.get("ok") is False:
            raise ValueError(str(result.get("error") or "recovered source was refused"))
        staged_refs.append(str(result.get("source_path") or f"projects/{project}/raw/{filename}"))
        write_paths.extend(str(path) for path in (result.get("write_paths") or []) if path)
    return staged_refs, unique_values(write_paths)


def save_case_file_payload(
    *,
    project: str,
    case_file: Any,
    rubric: str | None = None,
    intake: str | None = None,
) -> dict[str, Any]:
    project = snapshot.validate_project_slug(project)
    if not isinstance(case_file, dict):
        raise ValueError("project_file must be a JSON object")
    if str(case_file.get("schema") or "") not in {PROJECT_FILE_SCHEMA, CASE_FILE_SCHEMA}:
        raise ValueError("project_file schema is not compatible with this workbench")
    case_file = {**case_file, "schema": PROJECT_FILE_SCHEMA}
    case_file = case_file_payload_with_case(case_file, project=project, rubric=rubric, intake=intake)
    case_file = stamp_case_file_live_state(
        case_file,
        project=project,
        rubric=rubric,
        intake=intake,
    )
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json") as staged:
        json.dump(case_file, staged)
        staged.flush()
        args = [
            "forensic-workbench", "save-project-file",
            "--project", project,
            "--from", staged.name,
            "--repo", str(snapshot.REPO),
            "--json",
        ]
        if rubric:
            args.extend(["--rubric", rubric])
        if intake:
            args.extend(["--intake", intake])
        result = ztare_cli_payload(args, project=project, timeout=90)
    if result.get("ok") is False:
        raise ValueError(str(result.get("error") or "project file save was refused"))
    content_changed = bool(result.get("content_changed"))
    previous_case_sha256 = str(result.get("project_file_previous_sha256") or "")
    case_sha256 = str(result.get("project_file_sha256") or "")
    write_paths = list(result.get("write_paths") or [])
    return {
        "schema": PROJECT_FILE_WRITE_SCHEMA,
        "served_from": "local_api",
        "ok": True,
        "project": project,
        "path": str(result.get("path") or ""),
        "project_file_path": str(result.get("project_file_path") or ""),
        "project_file_sha256": case_sha256,
        "project_file_previous_sha256": previous_case_sha256,
        "project_file_content_changed": content_changed,
        "content_changed": content_changed,
        "project_file_key": str(result.get("project_file_key") or ""),
        "project_state_schema": str(result.get("project_state_schema") or ""),
        "project_state_next_action": str(result.get("project_state_next_action") or ""),
        "project_state_action_count": safe_int(result.get("project_state_action_count")),
        "project_state_project_repair_count": safe_int(result.get("project_state_project_repair_count")),
        "project_state_project_inspect_count": safe_int(result.get("project_state_project_inspect_count")),
        "project_state_advisory_count": safe_int(result.get("project_state_advisory_count")),
        "project_file_inventory_count": safe_int(result.get("project_file_inventory_count")),
        "project_file_previewable_count": safe_int(result.get("project_file_previewable_count")),
        "project_file_missing_count": safe_int(result.get("project_file_missing_count")),
        "project_object_contract_ok": bool(result.get("project_object_contract_ok")),
        "project_object_contract_failed_count": safe_int(result.get("project_object_contract_failed_count")),
        "project_object_contract_failed_checks": result.get("project_object_contract_failed_checks") if isinstance(result.get("project_object_contract_failed_checks"), list) else [],
        "project_to_thesis_audit_ok": bool(result.get("project_to_thesis_audit_ok")),
        "project_to_thesis_audit_failed_count": safe_int(result.get("project_to_thesis_audit_failed_count")),
        "project_to_thesis_audit_summary": str(result.get("project_to_thesis_audit_summary") or ""),
        "item_count": safe_int(result.get("item_count")),
        "receipt_count": safe_int(result.get("receipt_count")),
        "receipt": result.get("receipt") or {},
        "receipt_path": str(result.get("receipt_path") or ""),
        "latest": str(result.get("latest") or ""),
        "write_boundary": {
            **write_boundary_payload(
                writes_project_files=True,
                write_paths=write_paths,
                receipt_path=str(result.get("receipt_path") or ""),
                latest_path=str(result.get("latest") or ""),
            ),
            "primary_path": str(result.get("project_file_path") or ""),
            "previous_sha256": previous_case_sha256,
            "new_sha256": case_sha256,
            "content_changed": content_changed,
            "no_change": not content_changed,
        },
    }


def compact_eval_payload(payload: dict[str, Any]) -> dict[str, Any]:
    gaps = payload.get("evidence_gaps") or []
    if not isinstance(gaps, list):
        gaps = []
    probability = payload.get("probability_dag") or {}
    outcome = probability.get("outcome") if isinstance(probability, dict) else {}
    if not isinstance(outcome, dict):
        outcome = {}
    return {
        "score": payload.get("score"),
        "weakest_point": str(payload.get("weakest_point") or ""),
        "evidence_gap_count": len(gaps),
        "evidence_gaps": [
            {
                "target": str(row.get("target") or ""),
                "severity": str(row.get("severity") or ""),
                "description": str(row.get("description") or ""),
                "required_surface": str(row.get("required_surface") or ""),
            }
            for row in gaps[:5]
            if isinstance(row, dict)
        ],
        "probability_outcome": {
            "label": str(outcome.get("label") or ""),
            "probability": outcome.get("probability"),
        },
    }


def compact_eval_history_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_id": row.get("run_id"),
        "iteration": row.get("iteration"),
        "score": row.get("score"),
        "timestamp": str(row.get("timestamp") or ""),
        "weakest_point": str(row.get("weakest_point") or ""),
        "gate_failure_count": safe_int(row.get("gate_failure_count")),
        "worker_capabilities": [str(item) for item in row.get("worker_capability_set") or []],
        "worker_transports": [str(item) for item in row.get("worker_transport_set") or []],
        "matched_run_role": str(row.get("matched_run_role") or ""),
        "artifact_refs": [snapshot.rel(path) for path in (row.get("artifact_refs") or [])[:8]],
    }


def latest_preflight_summary(rows: list[dict[str, Any]], telemetry_path: Path) -> dict[str, Any]:
    starts_by_run: dict[str, dict[str, Any]] = {}
    ends_by_run: dict[str, dict[str, Any]] = {}
    latest_run_key = ""
    for row in rows:
        if not isinstance(row, dict) or not row.get("preflight_only"):
            continue
        run_key = str(row.get("run_id") or row.get("run_uuid") or "")
        if not run_key:
            continue
        latest_run_key = run_key
        record_type = str(row.get("record_type") or "")
        if record_type == "run_start":
            starts_by_run[run_key] = row
        elif record_type == "run_end":
            ends_by_run[run_key] = row
    latest_start = starts_by_run.get(latest_run_key, {})
    latest_end = ends_by_run.get(latest_run_key, {})
    if not latest_start and not latest_end:
        return {}
    run_id = latest_end.get("run_id") or latest_start.get("run_id")
    exit_reason = str(latest_end.get("run_exit_reason") or "")
    accepted = bool(exit_reason == "preflight_only" or (latest_start and not latest_end))
    return {
        "status": "accepted" if accepted else "recorded",
        "run_id": run_id,
        "timestamp": str(latest_end.get("timestamp_utc") or latest_start.get("timestamp_utc") or ""),
        "exit_reason": exit_reason,
        "mutator_model": str(latest_start.get("mutator_model") or ""),
        "judge_model": str(latest_start.get("judge_model") or ""),
        "packet_status": str((latest_start.get("project_packet") or {}).get("packet_status") or ""),
        "kernel_entry_status": str((latest_start.get("project_packet") or {}).get("kernel_entry_status") or ""),
        "file": repo_rel(telemetry_path),
    }


def compact_claim_support_source(row: dict[str, Any]) -> dict[str, Any]:
    preview = row.get("preview") if isinstance(row.get("preview"), dict) else {}
    return {
        "source_id": str(row.get("source_id") or ""),
        "status": str(row.get("status") or ""),
        "source_type": str(row.get("source_type") or ""),
        "path": display_path(row.get("path")),
        "relative_raw_path": str(row.get("relative_raw_path") or ""),
        "line_count": safe_int(row.get("line_count")),
        "hash_matches_index": row.get("hash_matches_index"),
        "preview": {
            "line_start": safe_int(preview.get("line_start")),
            "line_end": safe_int(preview.get("line_end")),
            "text": str(preview.get("text") or "")[:800],
            "truncated": bool(preview.get("truncated")),
        },
    }


def compact_claim_support_row(row: dict[str, Any]) -> dict[str, Any]:
    return claim_support_core.compact_claim_support_row(row, path_display=display_path)


def claim_support_row_is_weak(row: dict[str, Any]) -> bool:
    return claim_support_core.claim_support_row_is_weak(row)


def claim_card_payload(row: dict[str, Any], index: int) -> dict[str, Any]:
    return claim_support_core.claim_card_payload(
        row,
        index,
        path_display=display_path,
        value_display=display_value,
    )


def compact_thesis_support_payload(claim_support: dict[str, Any] | None) -> dict[str, Any]:
    return claim_support_core.compact_thesis_support_payload(
        claim_support,
        path_display=display_path,
        value_display=display_value,
    )


def claim_support_payload_for_project(
    *,
    project: str,
    rubric: str | None = None,
    intake: str | None = None,
) -> dict[str, Any]:
    project = snapshot.validate_project_slug(project)
    rubric = rubric or project
    intake = intake or snapshot.default_intake_for_project(project)
    if intake:
        project_intake_path(project, intake, allow_examples=True)
    command = [
        SERVER_PYTHON,
        "-m",
        "src.ztare.cli",
        "project",
        "claim-support",
        "--project",
        project,
        "--json",
    ]
    proc = snapshot.run(command, timeout=90)
    parsed: dict[str, Any] = {}
    try:
        parsed = snapshot.extract_last_json_object(proc.stdout)
    except Exception:
        parsed = {}
    source_context = parsed.get("source_context") if isinstance(parsed.get("source_context"), dict) else {}
    evidence_file_path = display_path(parsed.get("packet_path"))
    status = str(parsed.get("status") or ("ok" if proc.returncode == 0 else "attention"))
    # Surface all per-claim rows (not a 12-row sample) so Verdict can list every claim that needs
    # verification — the CLI classifies each; the workbench only selects which to show.
    rows = [compact_claim_support_row(row) for row in (parsed.get("rows") or [])[:80] if isinstance(row, dict)]
    return {
        "schema": CLAIM_SUPPORT_SCHEMA,
        "served_from": "local_api",
        "project": project,
        "rubric": rubric,
        "intake": intake,
        "project_key": case_key(project, intake),
        "case_key": case_key(project, intake),
        "support_scope": "project_compiled_evidence",
        "intake_scoped_command": False,
        "command": f"ztare project claim-support --project {project} --json",
        "returncode": proc.returncode,
        "accepted": proc.returncode == 0,
        "ok": bool(parsed.get("ok")),
        "status": status,
        "display_status": display_status(status),
        "claim_count": safe_int(parsed.get("claim_count")),
        "weak_or_unsourced_count": safe_int(parsed.get("weak_or_unsourced_count")),
        "source_context_blocked_count": safe_int(parsed.get("source_context_blocked_count")),
        "status_counts": parsed.get("status_counts") if isinstance(parsed.get("status_counts"), dict) else {},
        "reliability": parsed.get("reliability") if isinstance(parsed.get("reliability"), dict) else {},
        "source_context_status_counts": (
            parsed.get("source_context_status_counts")
            if isinstance(parsed.get("source_context_status_counts"), dict)
            else {}
        ),
        "errors": display_text_lines(parsed.get("errors") or [], limit=8),
        "evidence_support_file_path": evidence_file_path,
        "evidence_file_path": evidence_file_path,
        "packet_path": evidence_file_path,
        "source_index_path": display_path(parsed.get("source_index_path")),
        "rows": rows,
        "claim_cards": [claim_card_payload(row, index) for index, row in enumerate(rows[:8], start=1)],
        "source_context": [
            compact_claim_support_source(row)
            for row in list(source_context.values())[:12]
            if isinstance(row, dict)
        ],
        "stdout_tail": tail_display_text(proc.stdout),
        "stderr_tail": tail_display_text(proc.stderr),
    }


FIT_RESULT_ITER_RE = re.compile(r"_iter_(\d+)\.json$")


def finite_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        candidate = float(value)
    elif isinstance(value, str):
        try:
            candidate = float(value.strip())
        except ValueError:
            return None
    else:
        return None
    return candidate if math.isfinite(candidate) else None


def fit_result_iteration(path: Path) -> int:
    match = FIT_RESULT_ITER_RE.search(path.name)
    return int(match.group(1)) if match else 0


def fit_bic_proxy(payload: dict[str, Any]) -> float | None:
    direct = finite_float(payload.get("bic"))
    if direct is not None:
        return direct
    rmse = finite_float(payload.get("rmse"))
    if rmse is None or rmse <= 0:
        return None
    n_rows = safe_int(payload.get("n_fit_rows"))
    residual_map = payload.get("residual_map")
    if not n_rows and isinstance(residual_map, list):
        n_rows = len(residual_map)
    k_params = safe_int(payload.get("k_params"))
    params = payload.get("parameter_names")
    if not k_params and isinstance(params, list):
        k_params = len(params)
    if n_rows < 2 or k_params <= 0:
        return None
    return float(n_rows) * math.log(rmse * rmse) + float(k_params) * math.log(float(n_rows))


def compact_compression_advice(row: dict[str, Any]) -> dict[str, Any]:
    advice = row.get("compression_progress_advice") if isinstance(row, dict) else None
    if not isinstance(advice, dict):
        return {}
    return {
        "status": str(advice.get("status") or ""),
        "recommendation": str(advice.get("recommendation") or ""),
        "rationale": str(advice.get("rationale") or ""),
        "usable_observations": safe_int(advice.get("usable_observations")),
        "stagnation_length": advice.get("stagnation_length"),
        "last_drop_iteration": advice.get("last_drop_iteration"),
        "future_progress_weight": advice.get("future_progress_weight"),
    }


def compression_controller_alignment(
    *,
    compression_recommendation: str,
    loop_action: str,
) -> dict[str, str]:
    compression_warns = compression_recommendation in {"measure_before_continuing", "narrow_or_pivot"}
    loop_warns = loop_action in {"REFRESH_SPECIALISTS", "PIVOT_REQUIRED", "UNDERIDENTIFIED"}
    if not compression_recommendation or compression_recommendation == "no_signal":
        return {
            "status": "no_compression_signal",
            "label": "No compression comparison",
            "summary": "The run controller has no BIC/MDL-style compression signal to compare against yet.",
        }
    if compression_warns and not loop_warns:
        return {
            "status": "compression_warns_first",
            "label": "Simpler-explanation signal warns first",
            "summary": (
                "The run controller allowed continuation, but compression progress says the route may be stale."
            ),
        }
    if loop_warns and not compression_warns:
        return {
            "status": "run_controller_warns_first",
            "label": "Truth-yield signal warns first",
            "summary": (
                "The run controller asked for intervention even though the compression signal has not crossed its warning threshold."
            ),
        }
    if compression_warns and loop_warns:
        return {
            "status": "both_warn",
            "label": "Both signals warn",
            "summary": "The next run should narrow the evidence boundary, change route, or repair the blocking state first.",
        }
    return {
        "status": "both_allow",
        "label": "Both signals allow continuation",
        "summary": "The latest run-control state and compression-progress state both support another measured step.",
    }


def compression_progress_payload_for_project(
    *,
    project: str,
    telemetry_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    project = snapshot.validate_project_slug(project)
    workspace = snapshot.REPO / "projects" / project / "workspace"
    observations: list[CompressionObservation] = []
    source_refs: list[str] = []
    profile_points: list[dict[str, Any]] = []
    cumulative_seconds = 0.0
    cumulative_cost_usd = 0.0
    telemetry_by_iteration = {
        safe_int(row.get("iteration_index")): row
        for row in telemetry_rows
        if isinstance(row, dict) and row.get("record_type") == "iteration"
    }
    for path in sorted(workspace.glob("fit_result_iter_*.json"), key=fit_result_iteration):
        payload = read_optional_json_object(path)
        complexity = fit_bic_proxy(payload)
        if complexity is None:
            continue
        iteration_index = fit_result_iteration(path)
        row = telemetry_by_iteration.get(iteration_index, {})
        cumulative_seconds += finite_float(row.get("wall_clock_seconds")) or 0.0
        cumulative_cost_usd += finite_float(row.get("estimated_cost_usd")) or 0.0
        observations.append(
            CompressionObservation(
                iteration_index=iteration_index,
                complexity=complexity,
                novelty=bool(row.get("score_improved") or row.get("champion_promoted")),
                family="fit_bic",
                label=path.name,
                effort=cumulative_seconds if cumulative_seconds else None,
                effort_unit="seconds" if cumulative_seconds else "",
            )
        )
        source_ref = repo_rel(path)
        source_refs.append(source_ref)
        profile_points.append({
            "iteration": iteration_index,
            "complexity": complexity,
            "complexity_family": "fit_bic",
            "cumulative_effort_seconds": round(cumulative_seconds, 6),
            "cumulative_cost_usd": round(cumulative_cost_usd, 6),
            "score": row.get("score"),
            "score_improved": bool(row.get("score_improved") or row.get("champion_promoted")),
            "loop_action": str(row.get("pending_loop_action") or ""),
            "recorded_advice": compact_compression_advice(row),
            "source": source_ref,
        })

    # Universal fallback: projects that didn't run the fit domain have no fit_bic history, but EVERY project
    # has per-iteration probability-DAG snapshots. Reuse the kernel's two-part-MDL series (ex-post) so the
    # signal covers all projects — one shared computation, not a second implementation.
    expost = False
    if not observations:
        dag_obs = dag_observations_from_history(snapshot.REPO / "projects" / project / "history")
        if len(dag_obs) >= 2:
            observations = dag_obs
            expost = True
            profile_points = [{
                "iteration": o.iteration_index, "complexity": o.complexity, "complexity_family": "dag_mdl",
                "cumulative_effort_seconds": 0.0, "cumulative_cost_usd": 0.0,
                "score": None, "score_improved": False, "loop_action": "",
                "recorded_advice": {}, "source": o.label,
            } for o in dag_obs]

    decision = evaluate_compression_progress(observations)
    latest = observations[-1] if observations else None
    latest_row = telemetry_by_iteration.get(latest.iteration_index, {}) if latest else {}
    prior_loop_action = str(latest_row.get("pending_loop_action") or "")
    latest_iteration_advice = compact_compression_advice(latest_row)
    alignment = compression_controller_alignment(
        compression_recommendation=(
            latest_iteration_advice.get("recommendation") or decision.recommendation
        ),
        loop_action=prior_loop_action,
    )
    status = "no_signal"
    label = "Not enough history yet"
    summary = "Needs at least two iterations with a usable complexity reading."
    next_action: dict[str, Any] = {}
    if decision.recommendation == "continue":
        status = "improving"
        label = "Worth another pass"
        summary = "The last iteration still made the explanation simpler — the search is compressing."
    elif decision.recommendation == "watch":
        status = "watch"
        label = "Maybe — watch it"
        summary = (
            f"No simpler explanation for {decision.stagnation_length} iteration"
            f"{'' if decision.stagnation_length == 1 else 's'}, but not yet a flat stretch."
        )
    elif decision.recommendation == "measure_before_continuing":
        status = "needs_measurement"
        label = "Measure first"
        summary = "Recent moves were different but didn't simplify anything — check the novelty is real before spending another pass."
    elif decision.recommendation == "narrow_or_pivot":
        status = "needs_narrowing"
        label = "Diminishing returns"
        summary = (
            f"No compression improvement for {decision.stagnation_length} iteration"
            f"{'' if decision.stagnation_length == 1 else 's'}; the next run should narrow the evidence boundary or use a simpler model."
        )
        next_action = project_action(
            action_id="compression_progress_narrow",
            label="Narrow or simplify",
            area="run",
            detail=summary,
            workspace="run",
            subsection="Ready to run",
            primary_label="Save next step",
            source=source_refs[-1] if source_refs else repo_rel(workspace),
            rule="Compression-progress is advisory. It does not block a run unless combined with source, evidence, or readiness blockers.",
            evidence_refs=source_refs[-5:],
            write_boundary=write_boundary_payload(
                writes_project_files=False,
                read_only_actions=["inspect fit history", "save review", "save next step"],
            ),
        )

    return {
        "schema": "ztare-forensic-workbench-compression-progress-v1",
        "status": status,
        "label": label,
        "summary": summary,
        "how_computed": (
            "Complexity is a two-part MDL of the champion probability DAG — the bits to describe its "
            "structure plus the surprisal of its conclusion; it drops when added structure buys enough "
            "explanatory power to pay for itself. “Compression progress” is that number falling. We "
            "count iterations since the last fall: a few flat ones mean diminishing returns. Advisory, "
            "computed from run history — not the judge score (which this tool treats as gameable)."
            if decision.family == "dag_mdl" else
            "Complexity is the fit model's BIC/MDL (lower is simpler). “Compression progress” is that "
            "value falling across iterations; several flat iterations mean diminishing returns. Advisory, "
            "computed from fit history — not the judge score."
        ),
        "source_mode": "history_dag_expost" if expost else "fit_iter",
        "recommendation": decision.recommendation,
        "family": decision.family,
        "usable_observations": decision.usable_observations,
        "observation_count": len(observations),
        "best_complexity": decision.best_complexity,
        "latest_complexity": decision.latest_complexity,
        "best_effort": decision.best_effort,
        "latest_effort": decision.latest_effort,
        "effort_unit": decision.effort_unit,
        "total_effort_seconds": round(cumulative_seconds, 6),
        "total_cost_usd": round(cumulative_cost_usd, 6),
        "last_drop_iteration": decision.last_drop_iteration,
        "stagnation_length": decision.stagnation_length,
        "compression_drop_count": decision.compression_drop_count,
        "future_progress_weight": decision.future_progress_weight,
        "prior_loop_action": prior_loop_action,
        "latest_iteration_advice": latest_iteration_advice,
        "controller_alignment": alignment,
        "source_refs": source_refs[-12:],
        "latest_source": source_refs[-1] if source_refs else "",
        "complexity_runtime_profile": profile_points[-20:],
        "rationale": decision.rationale,
        "next_action": next_action,
        "control_policy": (
            "Use as a warning beside score and weakest-point history. Do not treat as a hard stop by itself."
        ),
    }


def information_yield_payload_for_project(project: str) -> dict[str, Any]:
    """Latest run-control decision about whether the project is still learning."""

    project = snapshot.validate_project_slug(project)
    workspace = snapshot.REPO / "projects" / project / "workspace"
    path = workspace / "latest_information_yield.json"
    payload = read_optional_json_object(path)
    source = repo_rel(path)
    if not payload:
        return {
            "schema": "ztare-forensic-workbench-information-yield-v1",
            "status": "not_loaded",
            "action": "",
            "label": "No truth-yield signal",
            "summary": "No latest information-yield decision is available for this project yet.",
            "source": source,
            "next_action": {},
        }

    signal = payload.get("signal") if isinstance(payload.get("signal"), dict) else {}
    decision = payload.get("decision") if isinstance(payload.get("decision"), dict) else {}
    latent_motion = (
        payload.get("latent_motion_summary")
        if isinstance(payload.get("latent_motion_summary"), dict)
        else {}
    )
    action = str(decision.get("action") or "").strip()
    normalized_action = action.upper()
    action_labels = {
        "CONTINUE": "Continue measured run",
        "REFRESH_SPECIALISTS": "Refresh route before continuing",
        "PIVOT_REQUIRED": "Pivot before another run",
        "UNDERIDENTIFIED": "Evidence may be underidentified",
    }
    status = {
        "CONTINUE": "continue",
        "REFRESH_SPECIALISTS": "needs_refresh",
        "PIVOT_REQUIRED": "needs_pivot",
        "UNDERIDENTIFIED": "underidentified",
    }.get(normalized_action, "recorded" if normalized_action else "not_loaded")
    rationale = str(decision.get("rationale") or "")
    weakest = str(signal.get("weakest_point") or "")
    score = signal.get("score")
    stagnant_window = safe_int(decision.get("stagnant_window"))
    final_action = str(latent_motion.get("final_action") or latent_motion.get("base_action") or normalized_action)
    motion_classes = [
        str(item)
        for item in (latent_motion.get("motion_classes") or [])
        if str(item or "").strip()
    ]
    summary_bits = [
        action_labels.get(normalized_action, display_text(normalized_action or "recorded")),
        rationale,
    ]
    summary = ". ".join(bit.rstrip(".") for bit in summary_bits if bit).strip()
    if summary:
        summary += "."
    else:
        summary = "The latest run-control decision was recorded, but no rationale was supplied."
    next_action: dict[str, Any] = {}
    if normalized_action and normalized_action != "CONTINUE":
        next_action = project_action(
            action_id="information_yield_next_step",
            label=action_labels.get(normalized_action, "Inspect truth-yield signal"),
            area="run",
            detail=summary,
            workspace="run",
            subsection="Ready to run",
            primary_label="Save next step",
            source=source,
            rule="Truth-yield is advisory until saved as a project review or next step.",
            evidence_refs=[source],
            write_boundary=write_boundary_payload(
                writes_project_files=False,
                read_only_actions=["inspect information-yield decision", "save review", "save next step"],
            ),
        )

    return {
        "schema": "ztare-forensic-workbench-information-yield-v1",
        "status": status,
        "action": normalized_action,
        "label": action_labels.get(normalized_action, display_text(normalized_action or "Truth-yield signal")),
        "summary": summary,
        "rationale": rationale,
        "stagnant_window": stagnant_window,
        "score": score,
        "score_improved": bool(signal.get("score_improved")),
        "weakest_point": weakest,
        "falsification_mode": str(signal.get("falsification_mode") or ""),
        "final_action": final_action,
        "latent_motion_veto_applied": bool(latent_motion.get("veto_applied")),
        "motion_classes": motion_classes,
        "source": source,
        "next_action": next_action,
    }


def run_history_payload_for_project(
    *,
    project: str,
    rubric: str | None = None,
    intake: str | None = None,
    limit: int = 8,
) -> dict[str, Any]:
    project = snapshot.validate_project_slug(project)
    rubric = rubric or project
    intake = intake or snapshot.default_intake_for_project(project)
    intake_available = True
    if intake:
        try:
            project_intake_path(project, intake, allow_examples=True)
        except FileNotFoundError:
            intake_available = False
    limit = max(1, min(limit, 25))
    project_root = snapshot.REPO / "projects" / project
    workspace = project_root / "workspace"
    eval_history_path = workspace / "eval_history.jsonl"
    telemetry_path = workspace / "iteration_telemetry.jsonl"
    latest_eval_path = project_root / "latest_eval_results.json"
    champion_eval_path = project_root / "champion_eval_results.json"
    synthesis_history_path = project_root / "synthesis" / "history_summary.json"

    rows = [compact_eval_history_row(row) for row in read_jsonl_objects(eval_history_path, limit=limit)]
    telemetry_rows = read_jsonl_objects(telemetry_path, limit=500)
    latest_preflight = latest_preflight_summary(telemetry_rows, telemetry_path)
    compression_progress = compression_progress_payload_for_project(
        project=project,
        telemetry_rows=telemetry_rows,
    )
    information_yield = information_yield_payload_for_project(project)
    latest_eval = compact_eval_payload(read_optional_json_object(latest_eval_path))
    champion_eval = compact_eval_payload(read_optional_json_object(champion_eval_path))
    synthesis_history = read_optional_json_object(synthesis_history_path)
    latest_row = rows[-1] if rows else {}
    score_candidates = [row.get("score") for row in rows if isinstance(row.get("score"), (int, float))]
    # The append-only run history is the authority for latest iteration state
    # once it exists. latest_eval_results.json can be a later-written overlay or
    # champion snapshot on historical projects, so using it first makes CLI and
    # workbench disagree about the latest score.
    latest_score = latest_row.get("score") if latest_row else latest_eval.get("score")
    if isinstance(latest_score, (int, float)):
        score_candidates.append(latest_score)
    if isinstance(champion_eval.get("score"), (int, float)):
        score_candidates.append(champion_eval["score"])
    best_score = max(score_candidates) if score_candidates else None
    observed_run_count = len(rows)
    if observed_run_count == 0 and (latest_eval or champion_eval):
        observed_run_count = 1
    latest_eval_score = latest_eval.get("score")
    latest_eval_disagrees = bool(
        latest_row
        and isinstance(latest_score, (int, float))
        and isinstance(latest_eval_score, (int, float))
        and latest_eval_score != latest_score
    )
    return {
        "schema": RUN_HISTORY_SCHEMA,
        "ok": True,
        "served_from": "local_api",
        "project": project,
        "rubric": rubric,
        "intake": intake,
        "project_key": case_key(project, intake),
        "case_key": case_key(project, intake),
        "run_scope": "project_run_history",
        "intake_scoped_files": False,
        "intake_available": intake_available,
        "limit": limit,
        "paths": {
            "eval_history": repo_rel(eval_history_path),
            "iteration_telemetry": repo_rel(telemetry_path),
            "latest_eval": repo_rel(latest_eval_path),
            "champion_eval": repo_rel(champion_eval_path),
            "synthesis_history": repo_rel(synthesis_history_path),
            "compression_progress": compression_progress.get("latest_source") or "",
            "information_yield": information_yield.get("source") or "",
        },
        "summary": {
            "run_rows": observed_run_count,
            "eval_history_rows": len(rows),
            "latest_score": latest_score,
            "best_score": best_score,
            "latest_run_id": latest_row.get("run_id"),
            "latest_iteration": latest_row.get("iteration"),
            "latest_timestamp": latest_row.get("timestamp"),
            "latest_weakest_point": latest_row.get("weakest_point") or latest_eval.get("weakest_point") or "",
            "latest_evidence_gap_count": 0 if latest_row else latest_eval.get("evidence_gap_count") or 0,
            "latest_eval_overlay_score": latest_eval_score,
            "latest_eval_overlay_disagrees": latest_eval_disagrees,
            "latest_eval_overlay_note": (
                "latest_eval_results.json differs from append-only run history; run history is used for latest score."
                if latest_eval_disagrees
                else ""
            ),
            "latest_preflight_status": latest_preflight.get("status") or "",
            "latest_preflight_run_id": latest_preflight.get("run_id"),
            "latest_preflight_timestamp": latest_preflight.get("timestamp") or "",
            "compression_progress_status": compression_progress.get("status") or "",
            "compression_progress_label": compression_progress.get("label") or "",
            "information_yield_status": information_yield.get("status") or "",
            "information_yield_label": information_yield.get("label") or "",
        },
        "latest_preflight": latest_preflight,
        "information_yield": information_yield,
        "compression_progress": compression_progress,
        "latest_eval": latest_eval,
        "champion_eval": champion_eval,
        "recent_runs": rows,
        "synthesis_history": {
            "summary_scope": str(synthesis_history.get("summary_scope") or ""),
            "recurring_failures": [str(item) for item in (synthesis_history.get("recurring_failures") or [])[:5]],
            "major_pivots": [str(item) for item in (synthesis_history.get("major_pivots") or [])[:5]],
            "cross_run_patterns": [str(item) for item in (synthesis_history.get("cross_run_patterns") or [])[:5]],
        },
    }


def project_source_count(project_root: Path) -> int:
    raw_dir = project_root / "raw"
    if not raw_dir.exists():
        return 0
    return sum(
        1
        for path in raw_dir.iterdir()
        if path.is_file() and path.name != "source_type_map.json"
    )


def workflow_step(
    *,
    step_id: str,
    label: str,
    status: str,
    route: str,
    detail: str,
    write_boundary: dict[str, Any] | None = None,
    source_status: str = "",
    local_action: str = "",
    ui_destination: dict[str, str] | None = None,
) -> dict[str, Any]:
    local = local_action or workflow_local_action(step_id)
    return {
        "id": step_id,
        "label": label,
        "status": status,
        "display_status": display_status(status),
        "route": route,
        "detail": detail,
        "local_step": local,
        "local_action": local,
        "ui_destination": ui_destination or workflow_ui_destination(step_id, status),
        "write_boundary": write_boundary or write_boundary_payload(writes_project_files=False),
        "source_status": source_status,
    }


def workflow_local_action(step_id: str) -> str:
    labels = {
        "open_project": "Load project",
        "connect_project": "Create project brief",
        "prepare_files": "Edit project files",
        "preflight": "Check readiness",
        "project_run": "Start or inspect run",
        "review_report": "Review report readiness",
        "save_project": "Save project file",
    }
    return labels.get(str(step_id or ""), "Open project step")


def workflow_ui_destination(step_id: str, status: str) -> dict[str, str]:
    if step_id == "open_project":
        return {"workspace": "projects", "subsection": "Projects"}
    if step_id == "connect_project":
        return {"workspace": "projects", "subsection": "Connect project"}
    if step_id == "prepare_files":
        return {"workspace": "sources", "subsection": "Project brief" if status == "ready" else "Prepare files"}
    if step_id == "preflight":
        return {"workspace": "run", "subsection": "Check readiness"}
    if step_id == "project_run":
        return {"workspace": "run", "subsection": "Ready to run" if status == "done" else "Start run"}
    if step_id == "review_report":
        return {
            "workspace": "review" if status == "ready" else "save",
            "subsection": "Save review" if status == "ready" else "Report readiness",
        }
    if step_id == "save_project":
        return {"workspace": "save", "subsection": "Project file"}
    return {"workspace": "overview", "subsection": "Overview"}


def normalized_workbench_destination(workspace: Any, subsection: Any) -> tuple[str, str]:
    workspace_id = WORKBENCH_UI_WORKSPACE_ALIASES.get(str(workspace or "").strip(), str(workspace or "").strip())
    subsection_name = str(subsection or "").strip()
    subsection_name = WORKBENCH_UI_SUBSECTION_ALIASES.get(workspace_id, {}).get(subsection_name, subsection_name)
    if workspace_id not in WORKBENCH_UI_SECTIONS or subsection_name not in WORKBENCH_UI_SECTIONS[workspace_id]:
        return "", ""
    return workspace_id, subsection_name


def valid_workbench_destination(workspace: Any, subsection: Any) -> bool:
    workspace_id, subsection_name = normalized_workbench_destination(workspace, subsection)
    return bool(workspace_id and subsection_name)


def workflow_next_step(steps: list[dict[str, Any]]) -> dict[str, Any]:
    priority = {
        "needs_attention": 0,
        "failed": 0,
        "blocked": 0,
        "not_run": 1,
        "waiting": 2,
        "ready": 3,
        "not_saved": 4,
        "done": 9,
        "reviewed": 9,
    }
    project_run_done = any(
        str(step.get("id") or "") == "project_run" and str(step.get("status") or "") == "done"
        for step in steps
    )
    candidates = []
    for step in steps:
        step_id = str(step.get("id") or "")
        status = str(step.get("status") or "")
        if step_id == "open_project" or status in {"done", "reviewed"}:
            continue
        if step_id == "prepare_files" and status == "ready" and str(step.get("source_status") or "") == "ready":
            continue
        if step_id == "preflight" and project_run_done:
            continue
        candidates.append(step)
    if not candidates:
        return {}
    return min(
        candidates,
        key=lambda step: (
            priority.get(str(step.get("status") or ""), 5),
            steps.index(step),
        ),
    )


def workflow_summary_payload(steps: list[dict[str, Any]]) -> dict[str, Any]:
    statuses = [str(step.get("status") or "") for step in steps]
    next_step = workflow_next_step(steps)
    write_paths = ((next_step.get("write_boundary") or {}).get("write_paths") or []) if next_step else []
    return {
        "step_count": len(steps),
        "ready_count": sum(1 for status in statuses if status in {"ready", "done", "reviewed"}),
        "attention_count": sum(1 for status in statuses if status in {"needs_attention", "failed", "blocked"}),
        "next_step_id": str(next_step.get("id") or ""),
        "next_step_label": str(next_step.get("label") or ""),
        "next_step_status": str(next_step.get("status") or ""),
        "next_step_display_status": str(next_step.get("display_status") or ""),
        "next_step_detail": str(next_step.get("detail") or ""),
        "next_step_local_step": str(next_step.get("local_step") or next_step.get("local_action") or ""),
        "next_step_local_action": str(next_step.get("local_action") or next_step.get("local_step") or ""),
        "next_step_ui_destination": next_step.get("ui_destination") or {},
        "next_step_write_path_count": len([path for path in write_paths if path]),
        "can_start_run": any(step.get("id") == "project_run" and step.get("status") == "ready" for step in steps),
        "project_file_saved": any(step.get("id") == "save_project" and step.get("status") == "done" for step in steps),
    }


def local_evidence_readiness_payload(project_root: Path) -> dict[str, Any]:
    workspace = project_root / "workspace"
    compiled_packet = project_root / "compiled_evidence_packet.json"
    compiled_text = project_root / "compiled_evidence.txt"
    replay_manifest = project_root / "compiled_evidence_replay_manifest.json"
    compile_provenance_candidates = [
        project_root / "compiled_evidence_provenance.json",
        workspace / "evidence_compile_provenance.json",
    ]
    compile_provenance = next((path for path in compile_provenance_candidates if path.exists()), None)
    source_index = workspace / "source_index.json"
    source_receipt = workspace / "source_index_receipt.json"

    blockers: list[str] = []
    if not source_index.exists():
        blockers.append("file index")
    if not source_receipt.exists():
        blockers.append("file-index history")
    if compile_provenance is None:
        blockers.append("evidence compile provenance")
    if not compiled_packet.exists():
        blockers.append("compiled evidence file")
    if not replay_manifest.exists():
        blockers.append("evidence replay manifest")

    status = "usable" if not blockers else "needs evidence prep"
    if not blockers:
        summary = "Compiled evidence, provenance, and replay manifest are present."
    elif source_index.exists() or source_receipt.exists():
        summary = f"Source files are indexed; missing {', '.join(blockers)}."
    else:
        summary = f"Missing {', '.join(blockers)}."

    return {
        "status": status,
        "summary": summary,
        "blocking": blockers,
        "source_index": repo_rel(source_index) if source_index.exists() else "",
        "source_receipt": repo_rel(source_receipt) if source_receipt.exists() else "",
        "compile_provenance": repo_rel(compile_provenance) if compile_provenance is not None else "",
        "compiled_packet": repo_rel(compiled_packet) if compiled_packet.exists() else "",
        "compiled_text": repo_rel(compiled_text) if compiled_text.exists() else "",
        "replay_manifest": repo_rel(replay_manifest) if replay_manifest.exists() else "",
    }


def rubric_path_for_workbench(rubric: str) -> Path:
    rubric = str(rubric or "").strip()
    if not rubric:
        return snapshot.REPO / "rubrics" / "missing.json"
    candidate = Path(rubric)
    if candidate.suffix == ".json" or len(candidate.parts) > 1:
        return (snapshot.REPO / candidate).resolve()
    return (snapshot.REPO / "rubrics" / f"{rubric}.json").resolve()


def local_scoring_guide_readiness_payload(*, project: str, rubric: str) -> dict[str, Any]:
    rubric_path = rubric_path_for_workbench(rubric)
    rel_path = repo_rel(rubric_path) if path_under(rubric_path, snapshot.REPO) else str(rubric_path)
    command = f"make validate-rubric PROJECT={project} RUBRIC={rel_path}"
    if not rubric_path.exists():
        return {
            "status": "needs scoring guide",
            "summary": "Scoring guide file is missing.",
            "blocking": ["scoring guide file"],
            "file": rel_path,
            "command": command,
        }
    try:
        rubric_payload = read_json_object(rubric_path, rel_path)
    except Exception as exc:  # noqa: BLE001 - the UI should surface the repair target.
        return {
            "status": "needs scoring guide",
            "summary": f"Scoring guide is not valid JSON: {display_text(exc)}",
            "blocking": ["scoring guide JSON"],
            "file": rel_path,
            "command": command,
        }
    dimensions = rubric_payload.get("dimensions")
    blockers: list[str] = []
    if not isinstance(dimensions, list) or not dimensions:
        blockers.append("scoring guide dimensions")
    else:
        weights: list[float] = []
        for dimension in dimensions:
            if not isinstance(dimension, dict):
                blockers.append("dimension shape")
                continue
            if not str(dimension.get("name") or "").strip():
                blockers.append("dimension names")
            if not str(dimension.get("description") or "").strip():
                blockers.append("dimension descriptions")
            try:
                weight = float(dimension.get("weight"))
            except (TypeError, ValueError):
                blockers.append("dimension weights")
                continue
            if weight <= 0:
                blockers.append("dimension weights")
            weights.append(weight)
        if weights and abs(sum(weights) - 100.0) > 0.01:
            blockers.append("dimension weights")
    blockers = sorted(set(blockers))
    if not blockers:
        return {
            "status": "usable",
            "summary": "Scoring guide dimensions are ready for run readiness.",
            "blocking": [],
            "file": rel_path,
            "command": command,
        }
    if blockers == ["scoring guide dimensions"]:
        summary = "Scoring guide needs a non-empty dimensions list before a run."
    else:
        summary = f"Scoring guide needs repair: {', '.join(blockers)}."
    return {
        "status": "needs scoring guide",
        "summary": summary,
        "blocking": blockers,
        "file": rel_path,
        "command": command,
    }


def scoring_guide_path_for_edit(rubric: str) -> Path:
    return scoring_guide_core.rubric_path_for_edit(rubric, root=snapshot.REPO)


def scoring_guide_no_change_boundary() -> str:
    return (
        "Preview, cancellation, JSON parse failure, and refused save write no files. "
        "A saved scoring guide can still need validation repairs; saved history keeps the validator result."
    )


def default_scoring_guide_text(project: str) -> str:
    title = project_display_label(project)
    payload = {
        "persona": f"Careful reviewer for {title}",
        "criteria": f"Score whether {title} is bounded, source-backed, explicit about uncertainty, and clear about what would change the conclusion.",
        "dimensions": [
            {
                "name": "Boundary",
                "weight": 25,
                "description": "The thesis is specific, scoped, and avoids claims the project has not earned.",
            },
            {
                "name": "Source support",
                "weight": 30,
                "description": "The thesis is backed by named project sources and compiled evidence.",
            },
            {
                "name": "Alternatives",
                "weight": 20,
                "description": "Important objections, rival explanations, and missing evidence are handled directly.",
            },
            {
                "name": "Next test",
                "weight": 25,
                "description": "The project names the next check or evidence that would weaken or strengthen the thesis.",
            },
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=False) + "\n"


def scoring_committee_for_project(project: str) -> list[dict[str, Any]]:
    """The per-thesis adversarial panel `make autoresearch-run --dynamic` generates from the thesis
    (generate_committee.py → rubrics/dynamic_<project>.json). Empty until a committee run happens."""
    path = snapshot.REPO / "rubrics" / f"dynamic_{project}.json"
    if not path.exists():
        return []
    try:
        payload = read_json_object(path, repo_rel(path))
    except Exception:  # noqa: BLE001 - a malformed committee file just shows no panel.
        return []
    committee = payload.get("committee")
    if not isinstance(committee, list):
        return []
    members = [m for m in committee if isinstance(m, dict) and (m.get("role") or m.get("persona"))]
    return display_data(members)


def scoring_guide_payload_for_project(*, project: str, rubric: str | None = None, intake: str | None = None) -> dict[str, Any]:
    project = snapshot.validate_project_slug(project)
    rubric = rubric or project
    intake = intake or snapshot.default_intake_for_project(project)
    project_intake_path(project, intake, allow_examples=True)
    rubric_path = scoring_guide_path_for_edit(rubric)
    rel_path = repo_rel(rubric_path)
    exists = rubric_path.exists()
    text = WORKBENCH_STORE.read_text(rubric_path, errors="replace") if exists else default_scoring_guide_text(project)
    parsed: dict[str, Any] = {}
    parse_error = ""
    try:
        loaded = json.loads(text)
        if isinstance(loaded, dict):
            parsed = display_data(loaded)
        else:
            parse_error = "scoring guide must be a JSON object"
    except json.JSONDecodeError as exc:
        parse_error = display_text(exc)
    readiness = local_scoring_guide_readiness_payload(project=project, rubric=rubric)
    return {
        "schema": SCORING_GUIDE_SCHEMA,
        "served_from": "local_api",
        "ok": True,
        "project": project,
        "rubric": rubric,
        "intake": intake,
        "path": rel_path,
        "exists": exists,
        "text": text,
        "parsed": parsed,
        "parse_error": parse_error,
        "committee": scoring_committee_for_project(project),
        "readiness": readiness,
        "command": readiness.get("command") or f"make validate-rubric PROJECT={project} RUBRIC={rel_path}",
        "write_boundary": write_boundary_payload(
            writes_project_files=False,
            writes_repo_files=True,
            write_paths=[rel_path],
            receipt_path=f"projects/{project}/workspace/forensic_workbench_scoring_guides.jsonl",
            latest_path=f"projects/{project}/workspace/forensic_workbench_latest_scoring_guide.json",
            read_only_actions=["preview scoring guide", "copy validation command"],
            no_change_boundary=scoring_guide_no_change_boundary(),
        ),
    }


def save_scoring_guide_payload(
    *,
    project: str,
    rubric: str | None = None,
    intake: str | None = None,
    text: Any = "",
) -> dict[str, Any]:
    project = snapshot.validate_project_slug(project)
    rubric = rubric or project
    intake = intake or snapshot.default_intake_for_project(project)
    project_intake_path(project, intake, allow_examples=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json") as staged:
        staged.write(str(text or ""))
        staged.flush()
        result = ztare_cli_payload([
            "forensic-workbench", "save-scoring-guide",
            "--project", project,
            "--rubric", rubric,
            "--intake", intake,
            "--from", staged.name,
            "--repo", str(snapshot.REPO),
            "--json",
        ], project=project, timeout=120)
    if result.get("ok") is False:
        raise ValueError(str(result.get("error") or "scoring guide save was refused"))
    payload = scoring_guide_payload_for_project(project=project, rubric=rubric, intake=intake)
    payload.update(
        {
            "saved": True,
            "accepted": bool(result.get("accepted")),
            "returncode": safe_int(result.get("returncode")),
            "stdout_tail": tail_display_text(str(result.get("stdout") or "")),
            "stderr_tail": tail_display_text(str(result.get("stderr") or "")),
            "receipt": result.get("receipt") or {},
            "receipt_path": str(result.get("receipt_path") or ""),
            "latest": str(result.get("latest") or ""),
            "write_boundary": write_boundary_payload(
                writes_project_files=False,
                writes_repo_files=True,
                write_paths=list(result.get("write_paths") or []),
                receipt_path=str(result.get("receipt_path") or ""),
                latest_path=str(result.get("latest") or ""),
                read_only_actions=["preview scoring guide", "copy validation command"],
                no_change_boundary=scoring_guide_no_change_boundary(),
            ),
        }
    )
    try:
        payload["workflow"] = workflow_payload_for_project(project=project, rubric=rubric, intake=intake, mode="fast")
    except Exception as exc:  # noqa: BLE001 - rubric save already succeeded.
        payload["workflow_error"] = display_text(exc)
    return payload


def local_evidence_gap_recovery_payload(*, project: str, project_root: Path) -> dict[str, Any]:
    workspace = project_root / "workspace"
    gap_path = workspace / "latest_evidence_gaps.json"
    champion_gap_path = workspace / "champion_evidence_gaps.json"
    command_context = workbench_command_context(project)
    if not gap_path.exists() and not champion_gap_path.exists():
        return {
            "status": "none",
            "summary": "No active evidence-gap file is loaded.",
            "gap_count": 0,
            "file": "",
            "command": "",
            "receipt_paths": [],
            "gaps": [],
        }
    payload, active_gap_path, warnings = load_active_evidence_gaps(workspace)
    warning_text = "; ".join(warnings)
    if payload is None:
        source_path = active_gap_path or (champion_gap_path if champion_gap_path.exists() else gap_path)
        return {
            "status": "none" if warning_text else "needs review",
            "summary": (
                display_text(warning_text)
                if warning_text
                else "No active evidence gaps are listed."
            ),
            "gap_count": 0,
            "file": repo_rel(source_path),
            "command": f"ztare project evidence-gap list --project {project} --json",
            "receipt_paths": [repo_rel(workspace / "evidence_gap_resolutions.json")],
            "gaps": [],
        }
    gaps = payload.get("evidence_gaps") if isinstance(payload.get("evidence_gaps"), list) else []
    active_gaps = [gap for gap in gaps if isinstance(gap, dict)]
    if not active_gaps:
        return {
            "status": "none",
            "summary": display_text(warning_text) if warning_text else "No active evidence gaps are listed.",
            "gap_count": 0,
            "file": repo_rel(active_gap_path or gap_path),
            "command": f"ztare project evidence-gap list --project {project} --json",
            "receipt_paths": [repo_rel(workspace / "evidence_gap_resolutions.json")],
            "gaps": [],
        }
    severity_counts: dict[str, int] = {}
    for gap in active_gaps:
        severity = str(gap.get("severity") or "unrated")
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
    severity_text = ", ".join(f"{count} {severity}" for severity, count in sorted(severity_counts.items()))
    gap_count = len(active_gaps)
    gap_noun = "gap" if gap_count == 1 else "gaps"
    gap_verb = "needs" if gap_count == 1 else "need"
    fetch_write_paths = evidence_fetch_expected_paths(project, auto_compile=command_context["auto_compile"])
    fetch_receipt_paths = [
        f"projects/{project}/workspace/evidence_fetch_manifest_<timestamp>.json",
        f"projects/{project}/workspace/forensic_workbench_evidence_fetches.jsonl",
        f"projects/{project}/workspace/forensic_workbench_latest_evidence_fetch.json",
    ]
    justify_write_paths = [
        repo_rel(workspace / "evidence_gap_resolutions.json"),
        repo_rel(workspace / "evidence_gap_action.json"),
        repo_rel(workspace / "evidence_gap_brief.md"),
    ]
    receipt_paths = list(dict.fromkeys([*fetch_receipt_paths, *justify_write_paths]))
    write_paths = list(dict.fromkeys([*fetch_write_paths, *justify_write_paths]))
    return {
        "status": "needs evidence recovery",
        "summary": f"{gap_count} active evidence {gap_noun} {gap_verb} fetch or justification ({severity_text}).",
        "gap_count": gap_count,
        "file": repo_rel(active_gap_path or gap_path),
        "command": display_command(evidence_fetch_command_from_context(command_context)),
        "receipt_paths": receipt_paths,
        "write_paths": write_paths,
        "fetch_receipt_paths": fetch_receipt_paths,
        "fetch_write_paths": fetch_write_paths,
        "justify_receipt_paths": justify_write_paths,
        "justify_write_paths": justify_write_paths,
        "gaps": [
            {
                "target": str(gap.get("target") or ""),
                "severity": str(gap.get("severity") or ""),
                "fetch_query": str(gap.get("fetch_query") or ""),
                "required_surface": str(
                    gap.get("required_surface")
                    or (
                        gap.get("recovery_contract", {}).get("required_surface")
                        if isinstance(gap.get("recovery_contract"), dict)
                        else ""
                    )
                    or ""
                ),
            }
            for gap in active_gaps[:5]
        ],
    }


def is_evidence_fetch_command(command: str, project: str) -> bool:
    text = str(command or "")
    return "evidence-fetch" in text and (
        f"PROJECT={project}" in text or f"--project {project}" in text
    )


def is_evidence_prepare_command(command: str, project: str) -> bool:
    text = str(command or "")
    return "evidence-prepare" in text and f"PROJECT={project}" in text


def normalize_admission_command(
    command: str,
    *,
    project: str,
    rubric: str | None = None,
    evidence_gap_recovery: dict[str, Any],
) -> str:
    text = str(command or "")
    if is_evidence_prepare_command(text, project):
        command_context = workbench_command_context(project, rubric)
        return display_command_from_template(SOURCE_ACTIONS["evidence_prepare"]["command"], command_context)
    configured_evidence_fetch = str(evidence_gap_recovery.get("command") or "")
    if configured_evidence_fetch and is_evidence_fetch_command(text, project):
        return configured_evidence_fetch
    if text.startswith("ztare autoresearch run "):
        return apply_run_settings_to_autoresearch_command(text, project)
    return text


def admission_summary_payload(
    *,
    project: str,
    rubric: str,
    intake: str,
    trace: dict[str, Any],
    evidence_readiness: dict[str, Any],
    scoring_guide_readiness: dict[str, Any],
    evidence_gap_recovery: dict[str, Any],
    input_ready: bool,
    run_can_start: bool,
) -> dict[str, Any]:
    """Compact run-readiness state for the shared project object."""

    command_context = workbench_command_context(project, rubric)
    kernel = trace.get("kernel_entry") if isinstance(trace.get("kernel_entry"), dict) else {}
    plan = trace.get("plan_preview") if isinstance(trace.get("plan_preview"), dict) else {}
    if kernel or plan:
        blockers = [
            {
                "id": str(row.get("id") or ""),
                "next_command": normalize_admission_command(
                    str(row.get("next_command") or ""),
                    project=project,
                    rubric=rubric,
                    evidence_gap_recovery=evidence_gap_recovery,
                ),
                "recovery_channel": str(row.get("recovery_channel") or ""),
            }
            for row in kernel.get("blockers") or []
            if isinstance(row, dict)
        ]
        next_commands = [
            normalize_admission_command(str(command), project=project, rubric=rubric, evidence_gap_recovery=evidence_gap_recovery)
            for command in trace.get("next_commands") or []
            if command
        ]
        recommended_first_command = normalize_admission_command(
            next((row["next_command"] for row in blockers if row.get("next_command")), "")
            or plan.get("recommended_first_command")
            or "",
            project=project,
            rubric=rubric,
            evidence_gap_recovery=evidence_gap_recovery,
        )
        if (
            recommended_first_command == "ztare project new --help"
            and evidence_readiness.get("status")
            and evidence_readiness.get("status") != "usable"
        ):
            recommended_first_command = display_command_from_template(
                SOURCE_ACTIONS["evidence_prepare"]["command"],
                command_context,
            )
        can_enter = bool(kernel.get("can_enter_kernel")) and not blockers
        status = str(kernel.get("readiness") or plan.get("status") or ("ready_for_bounded_run" if can_enter else "blocked_before_kernel_entry"))
        return {
            "status": status,
            "display_status": display_status(status),
            "can_enter_kernel": can_enter,
            "can_start_run": bool(plan.get("status") == "ready_for_bounded_run" and can_enter),
            "allowed_work_modes": [str(row) for row in kernel.get("allowed_work_modes") or []],
            "blockers": blockers,
            "next_commands": next_commands,
            "recommended_first_command": recommended_first_command,
            "model_calls_before_confirmation": bool(plan.get("model_calls_before_confirmation")),
            "model_spend_starts_at": "bounded_loop_run",
            "source": "trace",
        }

    blockers: list[dict[str, str]] = []
    if evidence_readiness.get("status") and evidence_readiness.get("status") != "usable":
        blockers.append(
            {
                "id": "evidence_prepare",
                "next_command": display_command_from_template(SOURCE_ACTIONS["evidence_prepare"]["command"], command_context),
                "recovery_channel": "evidence_prepare",
            }
        )
    if safe_int(evidence_gap_recovery.get("gap_count")) > 0:
        blockers.append(
            {
                "id": "out_of_loop_evidence_recovery",
                "next_command": str(evidence_gap_recovery.get("command") or ""),
                "recovery_channel": "out_of_loop_evidence_recovery",
            }
        )
    if scoring_guide_readiness.get("status") and scoring_guide_readiness.get("status") != "usable":
        blockers.append(
            {
                "id": "scoring_guide",
                "next_command": str(scoring_guide_readiness.get("command") or ""),
                "recovery_channel": "scoring_guide_repair",
            }
        )
    if not input_ready and not blockers:
        blockers.append(
            {
                "id": "project_files",
                "next_command": f"ztare project source-check --project {project} --json",
                "recovery_channel": "source_file_repair",
            }
        )
    can_enter = bool(run_can_start and not blockers)
    status = "ready_for_bounded_run" if can_enter else "blocked_before_kernel_entry"
    preflight_command = (
        "ztare autoresearch run "
        f"--project {project} --rubric {rubric} --intake {intake} --iters 1 --preflight-only"
    )
    next_commands = [row["next_command"] for row in blockers if row.get("next_command")]
    return {
        "status": status,
        "display_status": display_status(status),
        "can_enter_kernel": can_enter,
        "can_start_run": can_enter,
        "allowed_work_modes": ["inspection_only", "pre_kernel_project_prep"] if blockers else ["inspection_only", "preflight"],
        "blockers": blockers,
        "next_commands": next_commands,
        "recommended_first_command": next_commands[0] if next_commands else preflight_command,
        "model_calls_before_confirmation": False,
        "model_spend_starts_at": "bounded_loop_run",
        "source": "local_project_state",
    }


def project_object_contract_payload(
    *,
    project: str,
    intake: str,
    project_key: str,
    steps: list[dict[str, Any]],
    summary: dict[str, Any],
    project_state: dict[str, Any],
) -> dict[str, Any]:
    """Compact drift audit for the live project object shared by CLI/API/UI."""

    checks: list[dict[str, Any]] = []

    def add_check(check_id: str, label: str, ok: bool, detail: str) -> None:
        checks.append(
            {
                "id": check_id,
                "label": label,
                "ok": bool(ok),
                "status": "ready" if ok else "needs attention",
                "detail": detail,
            }
        )

    next_step = workflow_next_step(steps)
    next_action = project_state.get("next_action") if isinstance(project_state.get("next_action"), dict) else {}
    state_actions = project_state.get("actions") if isinstance(project_state.get("actions"), list) else []
    required_sections = [
        "charter",
        "thesis",
        "change_test",
        "assumptions",
        "axioms",
        "thesis_support",
        "sources",
        "source_health",
        "evidence",
        "admission",
        "run",
        "report",
        "review",
        "research_map",
        "recent_changes",
        "next_action",
        "files",
    ]
    missing_sections = [
        section
        for section in required_sections
        if not isinstance(project_state.get(section), dict) or not project_state.get(section)
    ]
    state_key = str(project_state.get("project_key") or "")
    state_project = str(project_state.get("project") or "")
    state_intake = str(project_state.get("intake") or "")
    next_step_destination = next_step.get("ui_destination") if isinstance(next_step.get("ui_destination"), dict) else {}
    next_step_id = str(next_step.get("id") or "")
    next_step_label = str(next_step.get("label") or "")
    next_action_id = str(next_action.get("id") or "")
    next_action_label = str(next_action.get("label") or "")
    next_action_workspace = str(next_action.get("workspace") or "")
    next_action_subsection = str(next_action.get("subsection") or "")
    recovery_required = bool(project_state.get("recovery")) and next_step_id == "connect_project"
    support_issue_count = safe_int((project_state.get("report") or {}).get("support_issue_count"))
    report_state = project_state.get("report") if isinstance(project_state.get("report"), dict) else {}
    report_allowed_action_count = safe_int(report_state.get("allowed_action_count"))
    research_map_state = project_state.get("research_map") if isinstance(project_state.get("research_map"), dict) else {}
    source_health_state = project_state.get("source_health") if isinstance(project_state.get("source_health"), dict) else {}
    thesis_support_state = project_state.get("thesis_support") if isinstance(project_state.get("thesis_support"), dict) else {}
    claim_cards = claim_support_core.claim_card_audit(thesis_support_state)
    source_health_issues = [
        issue
        for issue in source_health_state.get("issues") or []
        if isinstance(issue, dict)
    ]
    source_health_issue_count = max(safe_int(source_health_state.get("issue_count")), len(source_health_issues))
    source_health_action_count = sum(
        1
        for row in state_actions
        if isinstance(row, dict)
        and str(row.get("id") or "").startswith("source_health_")
        and valid_workbench_destination(row.get("workspace"), row.get("subsection"))
        and (
            [ref for ref in row.get("evidence_refs") or [] if ref]
            or str(row.get("source") or "").strip()
        )
    )
    recent_changes = project_state.get("recent_changes") if isinstance(project_state.get("recent_changes"), dict) else {}
    latest_source_change = (
        recent_changes.get("latest_source_or_evidence_change")
        if isinstance(recent_changes.get("latest_source_or_evidence_change"), dict)
        else {}
    )
    latest_project_check = (
        recent_changes.get("latest_project_check")
        if isinstance(recent_changes.get("latest_project_check"), dict)
        else {}
    )
    latest_run_change = recent_changes.get("latest_run") if isinstance(recent_changes.get("latest_run"), dict) else {}
    substantive_inspection = (
        recent_changes.get("substantive_inspection")
        if isinstance(recent_changes.get("substantive_inspection"), dict)
        else {}
    )
    substantive_target_paths = [
        path
        for path in [
            str(latest_source_change.get("artifact_path") or ""),
            str(latest_source_change.get("receipt_path") or ""),
            str(latest_project_check.get("artifact_path") or ""),
            str(latest_project_check.get("receipt_path") or ""),
            str(latest_run_change.get("artifact_path") or ""),
            str(latest_run_change.get("receipt_path") or ""),
        ]
        if path
    ]
    substantive_preview_path = str(substantive_inspection.get("preview_path") or "")
    evidence_blockers = (project_state.get("evidence") or {}).get("blocking")
    if not isinstance(evidence_blockers, list):
        evidence_blockers = []
    action_ids = {str(row.get("id") or "") for row in state_actions if isinstance(row, dict)}
    save_step = next((step for step in steps if step.get("id") == "save_project"), {})
    save_boundary = save_step.get("write_boundary") if isinstance(save_step.get("write_boundary"), dict) else {}
    save_paths = [path for path in (save_boundary.get("write_paths") or []) if path]
    workflow_steps_missing_write_boundary = []
    workflow_steps_missing_receipt_path = []
    receipt_step_ids = {"preflight", "project_run", "review_report", "save_project"}
    for step in steps:
        if not isinstance(step, dict):
            continue
        step_id = str(step.get("id") or step.get("label") or "step")
        boundary = step.get("write_boundary") if isinstance(step.get("write_boundary"), dict) else {}
        writes_files = bool(boundary.get("writes_project_files") or boundary.get("writes_repo_files"))
        if not writes_files:
            continue
        if not [path for path in boundary.get("write_paths") or [] if path] or not str(boundary.get("no_change_boundary") or "").strip():
            workflow_steps_missing_write_boundary.append(step_id)
        if step_id in receipt_step_ids and not str(boundary.get("receipt_path") or "").strip():
            workflow_steps_missing_receipt_path.append(step_id)
    write_capable_actions = [
        row
        for row in state_actions
        if isinstance(row, dict)
        and (
            [path for path in row.get("receipt_paths") or [] if path]
            or (
                isinstance(row.get("write_boundary"), dict)
                and (
                    (row.get("write_boundary") or {}).get("writes_project_files")
                    or (row.get("write_boundary") or {}).get("writes_repo_files")
                )
            )
        )
    ]
    actions_missing_write_boundary = [
        str(row.get("id") or row.get("label") or "action")
        for row in write_capable_actions
        if not isinstance(row.get("write_boundary"), dict)
        or not str((row.get("write_boundary") or {}).get("no_change_boundary") or "").strip()
        or (
            (
                (row.get("write_boundary") or {}).get("writes_project_files")
                or (row.get("write_boundary") or {}).get("writes_repo_files")
            )
            and not [path for path in (row.get("write_boundary") or {}).get("write_paths") or [] if path]
        )
    ]
    workflow_steps_with_dead_routes = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        destination = step.get("ui_destination") if isinstance(step.get("ui_destination"), dict) else {}
        if not valid_workbench_destination(destination.get("workspace"), destination.get("subsection")):
            workflow_steps_with_dead_routes.append(str(step.get("id") or step.get("label") or "step"))
    actions_with_dead_routes = [
        str(row.get("id") or row.get("label") or "action")
        for row in state_actions
        if isinstance(row, dict)
        and not valid_workbench_destination(row.get("workspace"), row.get("subsection"))
    ]
    file_state = project_state.get("files") if isinstance(project_state.get("files"), dict) else {}
    file_groups = file_state.get("file_groups") if isinstance(file_state.get("file_groups"), list) else []
    expected_file_group_ids = {str(row["id"]) for row in PROJECT_FILE_GROUP_DEFINITIONS}
    actual_file_group_ids = {
        str(row.get("id") or "")
        for row in file_groups
        if isinstance(row, dict) and str(row.get("id") or "")
    }
    missing_file_group_ids = sorted(expected_file_group_ids - actual_file_group_ids)
    file_groups_with_dead_routes = []
    file_groups_with_bad_counts = []
    for group in file_groups:
        if not isinstance(group, dict):
            continue
        group_id = str(group.get("id") or group.get("label") or "file_group")
        action = group.get("action") if isinstance(group.get("action"), dict) else {}
        if not valid_workbench_destination(action.get("workspace"), action.get("subsection")):
            file_groups_with_dead_routes.append(group_id)
        for count_key in ("count", "previewable_count", "missing_count"):
            count = group.get(count_key)
            if not isinstance(count, int) or count < 0:
                file_groups_with_bad_counts.append(f"{group_id}:{count_key}")
    files_item_count = safe_int(file_state.get("item_count"))
    files_previewable_count = safe_int(file_state.get("previewable_count"))
    files_missing_count = safe_int(file_state.get("missing_count"))

    add_check(
        "state_schema",
        "Project state schema",
        project_state.get("schema") == "ztare-project-workbench-state-v1",
        "The API and CLI expose the v1 live project-state object."
        if project_state.get("schema") == "ztare-project-workbench-state-v1"
        else "The live project-state object is missing or uses an unexpected schema.",
    )
    add_check(
        "project_identity",
        "Project identity",
        state_project == project and state_intake == intake and state_key == project_key,
        "Project, intake, and project key agree across workflow and project state."
        if state_project == project and state_intake == intake and state_key == project_key
        else "Project, intake, or project key drifted between workflow and project state.",
    )
    add_check(
        "required_sections",
        "Core project fields",
        not missing_sections,
        "Charter, thesis, change test, assumptions, axioms, thesis support, sources, file/evidence warnings, evidence, run readiness, run, report, review, research map, files, recent changes, and next action are present."
        if not missing_sections
        else f"Project state is missing: {', '.join(missing_sections)}.",
    )
    add_check(
        "substantive_inspection",
        "Recent work file",
        not substantive_target_paths or substantive_preview_path in substantive_target_paths,
        "Recent file, evidence, or run work has a previewable file target."
        if not substantive_target_paths or substantive_preview_path in substantive_target_paths
        else "Recent file, evidence, or run work is recorded, but the project object does not point to its file.",
    )
    add_check(
        "next_action",
        "Next action agrees",
        next_step_id == next_action_id and next_step_label == next_action_label,
        "Workflow next step and project-state next action name the same work."
        if next_step_id == next_action_id and next_step_label == next_action_label
        else "Workflow next step and project-state next action disagree.",
    )
    add_check(
        "next_destination",
        "Next action destination",
        str(next_step_destination.get("workspace") or "") == next_action_workspace
        and str(next_step_destination.get("subsection") or "") == next_action_subsection,
        "The next action opens the same workbench panel from workflow and project state."
        if str(next_step_destination.get("workspace") or "") == next_action_workspace
        and str(next_step_destination.get("subsection") or "") == next_action_subsection
        else "The next action panel drifts between workflow and project state.",
    )
    add_check(
        "workflow_destinations",
        "Workflow routes",
        not workflow_steps_with_dead_routes,
        "Workflow steps point to existing workbench sections."
        if not workflow_steps_with_dead_routes
        else f"Workflow steps point to missing sections: {', '.join(workflow_steps_with_dead_routes)}.",
    )
    add_check(
        "action_destinations",
        "Project action routes",
        not actions_with_dead_routes,
        "Project actions point to existing workbench sections."
        if not actions_with_dead_routes
        else f"Project actions point to missing sections: {', '.join(actions_with_dead_routes)}.",
    )
    add_check(
        "file_inventory",
        "Project file inventory",
        bool(file_state)
        and file_state.get("schema") == "ztare-project-file-inventory-v1"
        and files_item_count >= files_previewable_count
        and files_item_count >= files_missing_count,
        "Project files are exposed through the shared project object."
        if bool(file_state)
        and file_state.get("schema") == "ztare-project-file-inventory-v1"
        and files_item_count >= files_previewable_count
        and files_item_count >= files_missing_count
        else "Project files are missing or have inconsistent inventory counts.",
    )
    add_check(
        "research_map",
        "Research map",
        research_map_state.get("schema") == RESEARCH_MAP_SCHEMA
        and safe_int(research_map_state.get("section_count")) > 0
        and isinstance(research_map_state.get("project_meaning"), dict)
        and isinstance(research_map_state.get("next_action"), dict),
        "Research map summarizes project meaning, support, tensions, branches, and next action."
        if research_map_state.get("schema") == RESEARCH_MAP_SCHEMA
        and safe_int(research_map_state.get("section_count")) > 0
        and isinstance(research_map_state.get("project_meaning"), dict)
        and isinstance(research_map_state.get("next_action"), dict)
        else "Research map is missing structured project meaning or next action.",
    )
    add_check(
        "file_group_routes",
        "Project file viewer groups",
        bool(file_groups)
        and not missing_file_group_ids
        and not file_groups_with_dead_routes
        and not file_groups_with_bad_counts,
        "File viewer groups have counts and open existing workbench sections."
        if bool(file_groups)
        and not missing_file_group_ids
        and not file_groups_with_dead_routes
        and not file_groups_with_bad_counts
        else "File viewer groups need attention: "
        + ", ".join(
            [
                *(f"missing:{group_id}" for group_id in missing_file_group_ids),
                *(f"dead_route:{group_id}" for group_id in file_groups_with_dead_routes),
                *(f"bad_count:{group_id}" for group_id in file_groups_with_bad_counts),
            ]
        )
        + ".",
    )
    add_check(
        "report_repair_action",
        "Report readiness action",
        support_issue_count == 0 or "repair_report_support" in action_ids,
        "Report readiness issues have a visible inspect or rerun action."
        if support_issue_count == 0 or "repair_report_support" in action_ids
        else "Report readiness is blocked but no inspect or rerun action is exposed.",
    )
    add_check(
        "report_next_action_surface",
        "Report readiness next action",
        report_allowed_action_count == 0 or "follow_report_next_action" in action_ids,
        "Report readiness next actions are exposed in the project action list."
        if report_allowed_action_count == 0 or "follow_report_next_action" in action_ids
        else "Report readiness names a next action, but the project action list hides it.",
    )
    add_check(
        "evidence_repair_action",
        "Evidence repair action",
        recovery_required
        or not evidence_blockers
        or bool({"prepare_evidence", "repair_project_files", "bind_evidence"} & action_ids),
        "Evidence repair waits until the project brief is saved."
        if recovery_required
        else "Evidence blockers have a visible repair action."
        if not evidence_blockers or bool({"prepare_evidence", "repair_project_files", "bind_evidence"} & action_ids)
        else "Evidence is blocked but no repair action is exposed.",
    )
    add_check(
        "source_health_actions",
        "File/evidence warning actions",
        recovery_required
        or source_health_issue_count == 0
        or (
            source_health_action_count >= min(source_health_issue_count, len(source_health_issues) or source_health_issue_count)
            and valid_workbench_destination("run", "Fix warnings")
        ),
        "File and evidence warnings wait until the project brief is saved."
        if recovery_required
        else "File and evidence warnings have visible inspect actions with backing evidence."
        if source_health_issue_count == 0
        or (
            source_health_action_count >= min(source_health_issue_count, len(source_health_issues) or source_health_issue_count)
            and valid_workbench_destination("run", "Fix warnings")
        )
        else "File or evidence warnings exist, but the project action list does not expose matching warning actions.",
    )
    add_check(
        "claim_cards",
        "Claim cards",
        bool(claim_cards.get("ok")),
        str(claim_cards.get("detail") or ""),
    )
    add_check(
        "save_receipt_paths",
        "Project-file history paths",
        len(save_paths) >= 2,
        "Saving the project advertises target and history paths."
        if len(save_paths) >= 2
        else "Saving the project does not advertise enough target/history paths.",
    )
    add_check(
        "workflow_write_boundaries",
        "Workflow write boundaries",
        not workflow_steps_missing_write_boundary and not workflow_steps_missing_receipt_path,
        "Write-capable workflow steps advertise target paths, history paths, and no-change behavior."
        if not workflow_steps_missing_write_boundary and not workflow_steps_missing_receipt_path
        else "Workflow steps missing write boundary data: "
        + ", ".join(
            [
                *(f"{step_id}:target_or_no_change" for step_id in workflow_steps_missing_write_boundary),
                *(f"{step_id}:receipt_path" for step_id in workflow_steps_missing_receipt_path),
            ]
        )
        + ".",
    )
    add_check(
        "action_write_boundaries",
        "Action write boundaries",
        not actions_missing_write_boundary,
        "Write-capable project actions advertise target paths and no-change behavior."
        if not actions_missing_write_boundary
        else f"Actions missing write boundaries: {', '.join(actions_missing_write_boundary)}.",
    )

    failed = [row for row in checks if not row["ok"]]
    failed_checks = [
        {
            "id": str(row.get("id") or ""),
            "label": str(row.get("label") or ""),
            "detail": str(row.get("detail") or ""),
        }
        for row in failed
    ]
    return {
        "schema": "ztare-project-object-contract-v1",
        "ok": not failed,
        "project": project,
        "intake": intake,
        "project_key": project_key,
        "next_action_label": next_action_label,
        "next_action_destination": {
            "workspace": next_action_workspace,
            "subsection": next_action_subsection,
        },
        "check_count": len(checks),
        "failed_count": len(failed),
        "failed_checks": failed_checks,
        "checks": checks,
        "summary": "Project object is coherent across workflow and project state."
        if not failed
        else f"{len(failed)} project-object check{'s' if len(failed) != 1 else ''} need attention.",
    }


def nonempty_project_value(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return value is not None


def project_to_thesis_audit_payload(
    *,
    project_state: dict[str, Any],
    project_object_contract: dict[str, Any],
) -> dict[str, Any]:
    """Reader-facing proof that a project file carries the full thesis path."""

    actions = [item for item in project_state.get("actions") or [] if isinstance(item, dict)]
    project_actions = [item for item in actions if str(item.get("action_type") or "").startswith("project_")]
    repair_actions = [item for item in actions if str(item.get("action_type") or "") == "project_repair"]
    write_actions = [
        item
        for item in project_actions
        if isinstance(item.get("write_boundary"), dict)
        and (
            item["write_boundary"].get("writes_project_files")
            or item["write_boundary"].get("writes_repo_files")
            or item["write_boundary"].get("receipt_path")
            or item["write_boundary"].get("write_paths")
        )
    ]
    write_actions_with_boundary = [
        item
        for item in write_actions
        if item.get("write_boundary", {}).get("no_change_boundary")
        and (
            item.get("write_boundary", {}).get("write_paths")
            or item.get("write_boundary", {}).get("receipt_path")
        )
    ]

    def section(name: str) -> dict[str, Any]:
        value = project_state.get(name)
        return value if isinstance(value, dict) else {}

    next_action = section("next_action")
    charter = section("charter")
    thesis = section("thesis")
    thesis_support = section("thesis_support")
    sources = section("sources")
    evidence = section("evidence")
    source_health = section("source_health")
    run = section("run")
    report = section("report")
    files = section("files")
    recent_changes = section("recent_changes")
    recovery = section("recovery")
    has_recovery_connect_action = bool(recovery) and any(
        str(item.get("id") or "") == "add_intake"
        and isinstance(item.get("write_boundary"), dict)
        and (
            item["write_boundary"].get("write_paths")
            or item["write_boundary"].get("receipt_path")
        )
        for item in actions
    )
    charter_visible_or_recoverable = (
        nonempty_project_value(charter.get("file"))
        and nonempty_project_value(charter.get("status"))
        and (charter.get("exists") is not False or has_recovery_connect_action)
    )
    charter_detail = str(charter.get("summary") or charter.get("status") or "")
    if charter.get("exists") is False and has_recovery_connect_action:
        charter_detail = "Project charter will be created when the project brief is saved."

    checks = [
        {
            "id": "project_object",
            "label": "Project object coherent",
            "ok": bool(project_object_contract.get("ok")),
            "detail": str(project_object_contract.get("summary") or ""),
        },
        {
            "id": "charter",
            "label": "Project charter visible",
            "ok": charter_visible_or_recoverable,
            "detail": charter_detail,
        },
        {
            "id": "thesis",
            "label": "Thesis visible",
            "ok": nonempty_project_value(thesis.get("text")) and nonempty_project_value(thesis.get("status")),
            "detail": str(thesis.get("status") or ""),
        },
        {
            "id": "source_and_evidence",
            "label": "Source and evidence state visible",
            "ok": nonempty_project_value(sources.get("status"))
            and (
                nonempty_project_value(evidence.get("status"))
                or nonempty_project_value(thesis_support.get("status"))
                or nonempty_project_value(thesis_support.get("display_status"))
            ),
            "detail": f"sources={sources.get('status') or ''}; evidence={evidence.get('status') or thesis_support.get('display_status') or thesis_support.get('status') or ''}",
        },
        {
            "id": "source_health",
            "label": "File and evidence warnings visible",
            "ok": nonempty_project_value(source_health.get("status")) and "issue_count" in source_health,
            "detail": str(source_health.get("summary") or ""),
        },
        {
            "id": "run_state",
            "label": "Run state visible",
            "ok": nonempty_project_value(run.get("status")) and ("run_count" in run or "latest_score" in run or "blocking" in run),
            "detail": str(run.get("summary") or run.get("status") or ""),
        },
        {
            "id": "report_state",
            "label": "Report readiness visible",
            "ok": nonempty_project_value(report.get("status")),
            "detail": str(report.get("summary") or report.get("status") or ""),
        },
        {
            "id": "next_action",
            "label": "Next action visible",
            "ok": nonempty_project_value(next_action.get("label")) and nonempty_project_value(next_action.get("workspace")),
            "detail": f"{next_action.get('label') or ''} -> {next_action.get('workspace') or ''}/{next_action.get('subsection') or ''}",
        },
        {
            "id": "repair_actions",
            "label": "Repair actions visible",
            "ok": bool(repair_actions),
            "detail": f"{len(repair_actions)} repair action(s), {len(actions)} total action(s)",
        },
        {
            "id": "write_boundaries",
            "label": "Write boundaries visible",
            "ok": len(write_actions_with_boundary) == len(write_actions),
            "detail": f"{len(write_actions_with_boundary)}/{len(write_actions)} write-capable action(s) name target or history paths and no-change behavior",
        },
        {
            "id": "latest_change",
            "label": "Latest change visible",
            "ok": nonempty_project_value(recent_changes.get("summary")) or nonempty_project_value(recent_changes.get("latest_run")),
            "detail": str(recent_changes.get("summary") or ""),
        },
        {
            "id": "files",
            "label": "Project files visible",
            "ok": safe_int(files.get("item_count")) > 0 and nonempty_project_value(files.get("file_groups")),
            "detail": f"{safe_int(files.get('item_count'))} files; {safe_int(files.get('previewable_count'))} previewable",
        },
    ]
    if recovery:
        checks.append(
            {
                "id": "recovery_path",
                "label": "Recovery path visible",
                "ok": nonempty_project_value(recovery.get("intake_target"))
                and any(str(item.get("id") or "") == "add_intake" for item in actions),
                "detail": str(recovery.get("summary") or ""),
            }
        )
    failed = [item for item in checks if not item.get("ok")]
    return {
        "schema": "ztare-project-to-thesis-audit-v1",
        "ok": not failed,
        "check_count": len(checks),
        "failed_count": len(failed),
        "failed_checks": failed,
        "checks": checks,
        "action_counts": {
            "total": len(actions),
            "project_repair": len(repair_actions),
            "write_capable": len(write_actions),
            "write_boundary_ready": len(write_actions_with_boundary),
        },
        "summary": (
            "Project path is inspectable."
            if not failed
            else f"Project path has {len(failed)} missing part(s)."
        ),
    }


def workflow_row(rows: list[dict[str, Any]], label: str) -> dict[str, Any]:
    aliases = {
        "Report readiness": {"Report readiness", "Report support"},
        "Report support": {"Report readiness", "Report support"},
    }
    accepted = aliases.get(label, {label})
    for row in rows:
        if row.get("label") in accepted:
            return row
    return {}


def workflow_row_status(row: dict[str, Any], fallback: str = "not loaded") -> str:
    if not row:
        return fallback
    return str(row.get("display_status") or display_status(str(row.get("status") or fallback)))


def workflow_row_detail(row: dict[str, Any], fallback: str = "") -> str:
    if not row:
        return fallback
    return display_text(row.get("display_detail") or row.get("detail") or fallback)


def project_action(
    *,
    action_id: str,
    label: str,
    area: str,
    detail: str,
    workspace: str,
    subsection: str,
    primary_label: str = "Open",
    source: str = "",
    rule: str = "",
    evidence_refs: list[Any] | None = None,
    display_evidence_refs: list[dict[str, str]] | None = None,
    receipt_paths: list[str] | None = None,
    outcome_receipt_paths: list[str] | None = None,
    command: str = "",
    write_boundary: dict[str, Any] | None = None,
    source_label: str = "",
) -> dict[str, Any]:
    payload = {
        "id": action_id,
        "label": label,
        "area": area,
        "detail": display_guidance_text(detail),
        "primary_label": primary_label,
        "workspace": workspace,
        "subsection": subsection,
        "source": source,
        "source_label": source_label,
        "evidence_refs": evidence_refs or [],
        "display_evidence_refs": display_evidence_refs or [],
        "receipt_paths": [path for path in (receipt_paths or []) if path],
        "outcome_receipt_paths": [path for path in (outcome_receipt_paths or []) if path],
        "command": command,
    }
    if write_boundary is not None:
        payload["write_boundary"] = write_boundary
    write_boundary_obj = write_boundary if isinstance(write_boundary, dict) else {}
    writes_files = bool(
        write_boundary_obj.get("writes_project_files")
        or write_boundary_obj.get("writes_repo_files")
    )
    if area == "advisory":
        payload["action_type"] = "advisory"
    elif writes_files or payload["receipt_paths"] or (str(command or "").strip() and write_boundary is None):
        payload["action_type"] = "project_repair"
    else:
        payload["action_type"] = "project_inspect"
    if not rule:
        if payload["action_type"] == "advisory":
            rule = "Guidance actions inspect backing evidence; they do not change project state."
        elif payload["action_type"] == "project_inspect":
            rule = "Inspection actions read backing files before a separate write is allowed."
        else:
            rule = "Repair actions must name the target file, history path, and no-change boundary before they run."
    payload["rule"] = display_guidance_text(rule)
    return payload


def source_health_issue_guidance(issue_type: str) -> dict[str, str]:
    if issue_type == "weak_gp233_linkage":
        return {
            "what_to_check": (
                "Open the evidence ledger and look for a concrete decision, run, or project file "
                "linked to the warning, not only a prose note."
            ),
            "done_when": (
                "The ledger links the warning to inspectable evidence that can support or demote a "
                "recommendation."
            ),
        }
    if issue_type == "stale_trajectory_output":
        return {
            "what_to_check": (
                "Open the run-history archive and compare its timestamp with the latest project run "
                "records."
            ),
            "done_when": (
                "The run-history archive has been refreshed from current run records, or the warning "
                "is left as diagnostic only."
            ),
        }
    if issue_type == "unconsumed_surface":
        return {
            "what_to_check": (
                "Open the work log and check whether the surfaced warning or suggestion was actually "
                "recorded as used, rejected, or deferred."
            ),
            "done_when": (
                "The surfaced work has a backing log entry, or the recommendation stays advisory."
            ),
        }
    return {
        "what_to_check": "Open the backing source file and inspect the evidence behind this warning.",
        "done_when": "The warning has a project-local repair, a logged deferral, or remains advisory.",
    }


def source_health_project_action(issue: dict[str, Any], *, index: int, source_path: str) -> dict[str, Any]:
    issue_type = str(issue.get("issue_type") or issue.get("recommended_action") or "source_warning")
    rule = str(issue.get("blocking_rule") or issue.get("recommended_action") or issue_type or "Inspect file or evidence warning.")
    evidence_refs = [str(ref) for ref in issue.get("evidence_refs") or [] if ref]
    display_refs = [display_evidence_ref(ref) for ref in evidence_refs]
    backing_source = evidence_refs[0] if evidence_refs else source_path
    backing_source_label = display_refs[0]["label"] if display_refs else "File/evidence warning read model"
    guidance = source_health_issue_guidance(issue_type)
    if issue_type == "weak_gp233_linkage":
        action = project_action(
            action_id=f"source_health_{index}",
            label="Inspect evidence-link warning",
            area="advisory",
            detail=(
                f"Guidance only; not a project blocker. {rule}. "
                "The backing evidence ledger needs stronger links before this warning can justify stronger action."
            ),
            workspace="run",
            subsection="Fix warnings",
            primary_label="Open backing evidence",
            source=backing_source,
            source_label=backing_source_label,
            rule="File/evidence warning links are global guidance until stronger ledger linkage exists.",
            evidence_refs=evidence_refs,
            display_evidence_refs=display_refs,
            write_boundary=write_boundary_payload(
                writes_project_files=False,
                read_only_actions=["open backing evidence", "copy evidence path"],
            ) if evidence_refs else None,
        )
        action.update(guidance)
        return action
    if issue_type == "stale_trajectory_output":
        action = project_action(
            action_id=f"source_health_{index}",
            label="Inspect stale run-history warning",
            area="advisory",
            detail=(
                f"Guidance only; not a project blocker. {rule}. "
                "Treat run-history suggestions as diagnostic until the backing archive is refreshed."
            ),
            workspace="run",
            subsection="Fix warnings",
            primary_label="Open backing evidence",
            source=backing_source,
            source_label=backing_source_label,
            rule="Stale run-history archives can inform inspection, but they cannot justify stronger project claims.",
            evidence_refs=evidence_refs,
            display_evidence_refs=display_refs,
            write_boundary=write_boundary_payload(
                writes_project_files=False,
                read_only_actions=["open backing evidence", "copy evidence path"],
            ) if evidence_refs else None,
        )
        action.update(guidance)
        return action
    if issue_type == "unconsumed_surface":
        action = project_action(
            action_id=f"source_health_{index}",
            label="Inspect work-log warning",
            area="advisory",
            detail=(
                f"Guidance only; not a project blocker. {rule}. "
                "Treat this as diagnostic until the surfaced work is recorded in the backing work log."
            ),
            workspace="run",
            subsection="Fix warnings",
            primary_label="Open backing evidence",
            source=backing_source,
            source_label=backing_source_label,
            rule="Surfaced work only becomes stronger evidence after it is recorded in the backing work log.",
            evidence_refs=evidence_refs,
            display_evidence_refs=display_refs,
            write_boundary=write_boundary_payload(
                writes_project_files=False,
                read_only_actions=["open backing evidence", "copy evidence path"],
            ) if evidence_refs else None,
        )
        action.update(guidance)
        return action
    action_label = display_action_label(issue_type)
    if action_label:
        action_label = action_label[0].upper() + action_label[1:]
    action = project_action(
        action_id=f"source_health_{index}",
        label=action_label or "Inspect file or evidence warning",
        area="advisory",
        detail=f"Guidance only; not a project blocker. {rule}",
        workspace="run",
        subsection="Fix warnings",
        primary_label="Open warning guidance",
        source=backing_source,
        source_label=backing_source_label,
        rule="File and evidence warnings are inspect-only until a project-local repair or promoted control exists.",
        evidence_refs=evidence_refs,
        display_evidence_refs=display_refs,
        write_boundary=write_boundary_payload(
            writes_project_files=False,
            read_only_actions=["open backing evidence", "copy evidence path"],
        ) if evidence_refs else None,
    )
    action.update(guidance)
    return action


def source_health_state_payload(source_health: dict[str, Any]) -> dict[str, Any]:
    issues = [row for row in source_health.get("issues") or [] if isinstance(row, dict)]
    counts = source_health.get("counts") if isinstance(source_health.get("counts"), dict) else {}
    issue_types = unique_values([str(row.get("issue_type") or row.get("recommended_action") or "") for row in issues])
    status = "needs attention" if issues else "ready"
    if issues:
        readable_issues = ", ".join(display_action_label(issue_type) for issue_type in issue_types[:3])
        summary = (
            f"{len(issues)} file/evidence warning{'s' if len(issues) != 1 else ''}: {readable_issues}."
            if readable_issues
            else f"{len(issues)} file/evidence warning{'s' if len(issues) != 1 else ''}."
        )
    else:
        summary = "File/evidence warning model has no active warnings."
    return {
        "status": status,
        "summary": summary,
        "issue_count": len(issues),
        "warning_count": safe_int(counts.get("warning")),
        "blocking_count": safe_int(counts.get("blocking")),
        "issue_types": issue_types,
        "display_issue_types": [display_action_label(issue_type) for issue_type in issue_types],
        "source_path": str(source_health.get("source_path") or ""),
        "source_paths": source_health.get("source_paths") if isinstance(source_health.get("source_paths"), dict) else {},
        "issues": [
            {
                "issue_id": str(row.get("issue_id") or ""),
                "issue_type": str(row.get("issue_type") or row.get("recommended_action") or ""),
                "display_issue_type": display_action_label(row.get("issue_type") or row.get("recommended_action")),
                "severity": str(row.get("severity") or ""),
                "summary": display_guidance_text(row.get("blocking_rule") or row.get("recommended_action") or ""),
                "evidence_refs": [str(ref) for ref in row.get("evidence_refs") or [] if ref],
            }
            for row in issues[:5]
        ],
    }


def _intake_claim_fields(
    project: str,
    intake: str,
    assumptions_row: dict[str, Any],
) -> dict[str, Any]:
    intake_target_path = project_intake_target_path(project, intake, allow_examples=True)
    intake_payload = read_optional_json_object(intake_target_path)
    intake_thesis = str(
        intake_payload.get("bounded_claim")
        or intake_payload.get("thesis")
        or intake_payload.get("claim")
        or ""
    ).strip()
    intake_change_test = str(
        intake_payload.get("next_falsifier")
        or intake_payload.get("change_test")
        or intake_payload.get("falsifier")
        or ""
    ).strip()
    intake_non_claims_raw = intake_payload.get("non_claims") or intake_payload.get("non_claim") or []
    if isinstance(intake_non_claims_raw, list):
        intake_non_claims = [str(item).strip() for item in intake_non_claims_raw if str(item).strip()]
    elif isinstance(intake_non_claims_raw, str):
        intake_non_claims = [line.strip() for line in intake_non_claims_raw.splitlines() if line.strip()]
    else:
        intake_non_claims = []
    assumption_summary = workflow_row_detail(assumptions_row, "")
    if intake_non_claims:
        shown_non_claims = "; ".join(intake_non_claims[:4])
        extra_count = max(0, len(intake_non_claims) - 4)
        assumption_summary = (
            f"Scope limits (not claiming): {shown_non_claims}"
            + (f"; +{extra_count} more" if extra_count else "")
        )
    if not assumption_summary:
        assumption_summary = "No assumptions or constraints file is loaded yet."
    return {
        "thesis": intake_thesis,
        "change_test": intake_change_test,
        "non_claims": intake_non_claims,
        "assumption_summary": assumption_summary,
    }


def _report_block(
    *,
    report: dict[str, Any],
    report_row: dict[str, Any],
    report_reasons: list[str],
    report_allowed_actions: list[dict[str, Any]],
    report_contract: str,
) -> dict[str, Any]:
    report_status_text = str(report.get("display_status") or report.get("status") or workflow_row_status(report_row, "not loaded"))
    report_detail_text = report_workflow_detail(report) if report else "Report readiness has not been loaded yet."
    report_summary_text = workflow_row_detail(report_row, report_detail_text)
    if report_reasons:
        report_summary_text = report_reasons[0]
    elif report_status_text not in {"ready", "fresh", "current", "ok"}:
        report_summary_text = report_detail_text
    return {
        "status": report_status_text,
        "summary": report_summary_text,
        "support_issue_count": len(report_reasons),
        "support_reasons": report_reasons[:5],
        "allowed_action_count": len(report_allowed_actions),
        "completed_allowed_action_count": sum(1 for action in report_allowed_actions if isinstance(action, dict) and report_action_completed(action)),
        "first_allowed_action": str(
            (first_open_report_action(report_allowed_actions) or {}).get("label") if report_allowed_actions else ""
        ),
        "contract": report_contract,
    }


def _review_block(receipt_rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "receipt_count": len(receipt_rows),
        "latest_receipt": str((receipt_rows[0] or {}).get("path") or "") if receipt_rows else "",
        "saved_review_count": sum(1 for row in receipt_rows if isinstance(row, dict) and row.get("kind") == "review"),
        "saved_next_step_count": sum(1 for row in receipt_rows if isinstance(row, dict) and row.get("kind") in {"row_action", "next_step"}),
        "latest_review": latest_receipt_summary(receipt_rows, "review"),
        "latest_next_step": latest_receipt_summary(receipt_rows, "next_step"),
    }


def _action_summary_block(actions: list[dict[str, Any]]) -> dict[str, Any]:
    action_area_counts: dict[str, int] = {}
    action_type_counts: dict[str, int] = {}
    for action in actions:
        if not isinstance(action, dict):
            continue
        area = str(action.get("area") or "project")
        action_area_counts[area] = action_area_counts.get(area, 0) + 1
        action_type = str(action.get("action_type") or ("advisory" if area == "advisory" else "project_repair"))
        action_type_counts[action_type] = action_type_counts.get(action_type, 0) + 1
    return {
        "total_count": len(actions),
        "visible_count": len(actions),
        "hidden_count": 0,
        "project_repair_count": action_type_counts.get("project_repair", 0),
        "project_inspect_count": action_type_counts.get("project_inspect", 0),
        "advisory_count": action_type_counts.get("advisory", 0),
        "area_counts": action_area_counts,
        "action_type_counts": action_type_counts,
    }


def _evidence_status_block(
    *,
    trace: dict[str, Any],
    evidence_readiness: dict[str, Any],
    source_list: dict[str, Any],
    source_row: dict[str, Any],
    evidence_row: dict[str, Any],
    input_status: str,
) -> dict[str, Any]:
    trace_surfaces = trace.get("surfaces") if isinstance(trace.get("surfaces"), dict) else {}
    output_binding_status = str(trace_surfaces.get("output_binding_status") or "")
    if not output_binding_status:
        trace_evidence_readiness = trace_surfaces.get("evidence_readiness") if isinstance(trace_surfaces.get("evidence_readiness"), dict) else {}
        output_binding_status = str(trace_evidence_readiness.get("output_binding_status") or "")
    output_binding_ready = output_binding_status in {"fresh", "verified_fresh", "ok"}
    evidence_blockers = [str(row) for row in evidence_readiness.get("blocking") or [] if row]
    source_index_ready = bool(evidence_readiness.get("source_index")) and bool(evidence_readiness.get("source_receipt"))
    source_ready = (
        bool(source_list.get("accepted"))
        or workflow_row_status(source_row, "").startswith("ready")
        or source_index_ready
    )
    source_status = workflow_row_status(source_row, "usable" if source_ready else "needs review")
    evidence_summary = (
        str(evidence_readiness.get("summary") or "Evidence files are listed in the project brief; run the file check for the full support summary.")
        if not evidence_row and input_status == "usable"
        else str(evidence_readiness.get("summary") or "Evidence support has not been checked yet.")
    )
    evidence_files_ready = (
        not evidence_blockers
        and bool(evidence_readiness.get("source_index"))
        and bool(evidence_readiness.get("source_receipt"))
        and bool(evidence_readiness.get("compile_provenance"))
        and bool(evidence_readiness.get("compiled_packet"))
        and bool(evidence_readiness.get("replay_manifest"))
    )
    if evidence_files_ready and source_status in {"ready_for_evidence_prepare", "ready for evidence prep"}:
        source_status = "ready"
    return {
        "output_binding_ready": output_binding_ready,
        "source_ready": source_ready,
        "source_status": source_status,
        "evidence_summary": evidence_summary,
        "evidence_files_ready": evidence_files_ready,
    }


def _run_status_block(
    run_row: dict[str, Any],
    run_summary: dict[str, Any],
    run_history: dict[str, Any],
) -> dict[str, Any]:
    latest_preflight = run_history.get("latest_preflight") if isinstance(run_history.get("latest_preflight"), dict) else {}
    preflight_status = str(latest_preflight.get("status") or "")
    run_history_count = safe_int(run_summary.get("run_rows"))
    run_history_latest_score = run_summary.get("latest_score")
    run_status = workflow_row_status(run_row, "not run")
    run_summary_text = workflow_row_detail(run_row, "Run readiness has not been checked yet.")
    if run_status == "not run" and (run_history_count or run_history_latest_score is not None):
        score_text = "no score" if run_history_latest_score is None else f"latest score {run_history_latest_score}"
        if run_history_count:
            run_status = "run recorded"
            run_summary_text = f"{score_text}; {run_history_count} run{'s' if run_history_count != 1 else ''} found."
        else:
            run_status = "run file recorded"
            run_summary_text = f"Latest eval file reports {score_text}; no run-history rows found."
    elif run_status == "not run" and preflight_status:
        run_status = "readiness accepted" if preflight_status == "accepted" else "readiness recorded"
        run_summary_text = (
            "Latest readiness check accepted; project run has not started yet."
            if preflight_status == "accepted"
            else "A readiness check exists; review it before starting a project run."
        )
    return {
        "latest_preflight": latest_preflight,
        "status": run_status,
        "summary_text": run_summary_text,
    }


def _run_block(
    *,
    run_state: dict[str, Any],
    scoring_guide_readiness: dict[str, Any],
    run_summary: dict[str, Any],
    compression_progress: dict[str, Any],
) -> dict[str, Any]:
    compression_alignment = (
        compression_progress.get("controller_alignment")
        if isinstance(compression_progress.get("controller_alignment"), dict)
        else {}
    )
    return {
        "status": run_state["status"],
        "summary": run_state["summary_text"],
        "blocking": list(scoring_guide_readiness.get("blocking") or []),
        "scoring_guide_status": str(scoring_guide_readiness.get("status") or ""),
        "scoring_guide_summary": str(scoring_guide_readiness.get("summary") or ""),
        "scoring_guide_file": str(scoring_guide_readiness.get("file") or ""),
        "latest_preflight": run_state["latest_preflight"],
        "run_count": safe_int(run_summary.get("run_rows")),
        "latest_score": run_summary.get("latest_score"),
        "best_score": run_summary.get("best_score"),
        "latest_iteration": run_summary.get("latest_iteration"),
        "latest_weakest_point": str(run_summary.get("latest_weakest_point") or ""),
        "compression_progress_status": str(compression_progress.get("status") or ""),
        "compression_progress_label": str(compression_progress.get("label") or ""),
        "compression_progress_summary": str(compression_progress.get("summary") or ""),
        "compression_progress_recommendation": str(compression_progress.get("recommendation") or ""),
        "compression_controller_alignment": compression_alignment,
    }


def _next_action_block(
    *,
    next_step: dict[str, Any],
    next_destination: dict[str, Any],
    source_ready: bool,
    source_total: int,
    input_status: str,
) -> dict[str, Any]:
    next_action_label = str(next_step.get("label") or "")
    next_action_detail = str(next_step.get("detail") or "")
    next_action_local = str(next_step.get("local_step") or next_step.get("local_action") or "")
    if (
        str(next_step.get("id") or "") == "prepare_files"
        and source_ready
        and source_total > 0
        and input_status != "usable"
        and next_action_label != "Fetch or justify evidence gaps"
    ):
        next_action_label = "Prepare evidence summary"
        next_action_detail = "Source files are ready; the evidence summary still needs compile, binding, or gap repair."
        next_action_local = "Prepare evidence summary"
    return {
        "id": str(next_step.get("id") or ""),
        "label": next_action_label,
        "status": str(next_step.get("display_status") or next_step.get("status") or ""),
        "detail": next_action_detail,
        "local_step": next_action_local,
        "workspace": str(next_destination.get("workspace") or ""),
        "subsection": str(next_destination.get("subsection") or ""),
    }


def _project_actions(
    *,
    project: str,
    rubric: str,
    intake: str,
    charter_exists: bool,
    charter_rel: str,
    intake_thesis: str,
    prepare_status: str,
    prepare_step: dict[str, Any],
    evidence_files_ready: bool,
    source_ready: bool,
    source_total: int,
    input_status: str,
    output_binding_ready: bool,
    evidence_readiness: dict[str, Any],
    scoring_guide_readiness: dict[str, Any],
    evidence_gap_recovery: dict[str, Any],
    report: dict[str, Any],
    report_reasons: list[str],
    report_allowed_actions: list[dict[str, Any]],
    report_contract: str,
    source_health: dict[str, Any],
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    if not charter_exists:
        actions.append(
            project_action(
                action_id="add_project_charter",
                label="Add project charter",
                area="intake",
                detail="The project is missing the human charter used as mandatory context for project runs.",
                workspace="overview",
                subsection="Charter",
                primary_label="Open charter",
                source=charter_rel,
                rule="A project should have a project charter before new runs rely on its thesis, scope limits, or change test.",
                write_boundary=write_boundary_payload(
                    writes_project_files=True,
                    write_paths=[charter_rel],
                    receipt_path=charter_rel,
                    latest_path=charter_rel,
                    read_only_actions=["inspect charter", "copy charter path"],
                ),
            )
        )
    if not intake_thesis:
        actions.append(
            project_action(
                action_id="add_thesis",
                label="Add thesis",
                area="intake",
                detail="The project brief does not yet state what should be checked.",
                workspace="sources",
                subsection="Project brief",
                primary_label="Edit project brief",
                source=intake,
                rule="A project cannot run until the project brief states the bounded thesis or change test.",
            )
        )
    if prepare_status and prepare_status != "ready" and not evidence_files_ready:
        source_side_ready = source_ready and source_total > 0
        command_context = workbench_command_context(project, rubric)
        prepare_receipt_paths = [
            f"projects/{project}/workspace/forensic_workbench_source_actions.jsonl",
            f"projects/{project}/workspace/forensic_workbench_latest_source_action.json",
            f"projects/{project}/compiled_evidence_provenance.json",
            f"projects/{project}/compiled_evidence_packet.json",
            f"projects/{project}/compiled_evidence_replay_manifest.json",
        ] if source_side_ready else []
        prepare_write_boundary = source_action_write_boundary(project, rubric, "evidence_prepare") if source_side_ready else None
        actions.append(
            project_action(
                action_id="prepare_evidence" if source_side_ready else "repair_project_files",
                label="Prepare evidence summary" if source_side_ready else "Fix project files",
                area="evidence" if source_side_ready else "sources",
                detail=(
                    str(evidence_readiness.get("summary") or "Source files are ready. Compile or connect the evidence summary before running or relying on the report.")
                    if source_side_ready
                    else str(prepare_step.get("detail") or "Source or evidence files need review.")
                ),
                workspace="sources",
                subsection="Prepare files",
                primary_label="Prepare evidence summary" if source_side_ready else "Prepare files",
                rule=(
                    "Source files listed in the project brief are not enough by themselves; compiled evidence, provenance, and replay state must exist before a run."
                    if source_side_ready
                    else "Project files must be inspectable before evidence preparation or a run can be trusted."
                ),
                command=display_command_from_template(SOURCE_ACTIONS["evidence_prepare"]["command"], command_context) if source_side_ready else "",
                receipt_paths=prepare_receipt_paths,
                write_boundary=prepare_write_boundary,
            )
        )
    elif source_total == 0:
        actions.append(
            project_action(
                action_id="add_source",
                label="Add file",
                area="sources",
                detail="No local source file is loaded for this project.",
                workspace="sources",
                subsection="Add file",
                primary_label="Add file",
                rule="A project needs at least one local source file before evidence support can be checked.",
            )
        )
    if input_status != "usable" and not output_binding_ready:
        bind_action = SOURCE_ACTIONS["evidence_bind"]
        actions.append(
            project_action(
                action_id="bind_evidence",
                label="Bind evidence",
                area="evidence",
                detail="Connect source files to the compiled evidence file before running or relying on the report.",
                workspace="sources",
                subsection="Prepare files",
                primary_label="Bind evidence",
                rule="Compiled evidence must be bound to project outputs before report or run support can rely on it.",
                command=bind_action["display"].format(project=project),
                receipt_paths=[path.format(project=project) for path in bind_action["write_path_templates"]],
                write_boundary=write_boundary_payload(
                    writes_project_files=True,
                    write_paths=[path.format(project=project) for path in bind_action["write_path_templates"]],
                    receipt_path=f"projects/{project}/workspace/evidence_output_binding_receipt.json",
                    read_only_actions=["preview command", "open file readiness"],
                ),
            )
        )
    if scoring_guide_readiness.get("status") and scoring_guide_readiness.get("status") != "usable":
        scoring_guide_path = str(scoring_guide_readiness.get("file") or "")
        scoring_guide_ledger = f"projects/{project}/workspace/forensic_workbench_scoring_guides.jsonl"
        scoring_guide_latest = f"projects/{project}/workspace/forensic_workbench_latest_scoring_guide.json"
        actions.append(
            project_action(
                action_id="fix_scoring_guide",
                label="Fix scoring guide",
                area="checks",
                detail=str(scoring_guide_readiness.get("summary") or "Scoring guide needs review before a run."),
                workspace="run",
                subsection="Scoring guide",
                primary_label="Open scoring guide",
                source=scoring_guide_path,
                rule="Full runs require a current scoring guide with usable dimensions before launch.",
                command="GET /api/scoring-guide -> POST /api/scoring-guide",
                receipt_paths=[scoring_guide_ledger, scoring_guide_latest, scoring_guide_path],
                write_boundary=write_boundary_payload(
                    writes_project_files=False,
                    writes_repo_files=True,
                    write_paths=[path for path in [scoring_guide_path, scoring_guide_ledger, scoring_guide_latest] if path],
                    receipt_path=scoring_guide_ledger,
                    latest_path=scoring_guide_latest,
                    read_only_actions=["open scoring guide", "copy validation command"],
                    no_change_boundary=scoring_guide_no_change_boundary(),
                ) if scoring_guide_path else None,
            )
        )
    if safe_int(evidence_gap_recovery.get("gap_count")) > 0:
        receipt_paths = [
            str(path)
            for path in evidence_gap_recovery.get("receipt_paths", [])
            if path
        ]
        write_paths = [
            str(path)
            for path in evidence_gap_recovery.get("write_paths", receipt_paths)
            if path
        ]
        primary_receipt_path = next((path for path in receipt_paths if "forensic_workbench_evidence_fetches" in path), "")
        if not primary_receipt_path:
            primary_receipt_path = receipt_paths[0] if receipt_paths else ""
        latest_receipt_path = next((path for path in receipt_paths if "latest_evidence_fetch" in path), "")
        if not latest_receipt_path:
            latest_receipt_path = receipt_paths[-1] if receipt_paths else ""
        actions.append(
            project_action(
                action_id="recover_evidence_gaps",
                label="Fetch or justify evidence gaps",
                area="evidence",
                detail=str(evidence_gap_recovery.get("summary") or "Active evidence gaps need fetch or justification."),
                workspace="sources",
                subsection="Prepare files",
                primary_label="Review gaps",
                source=str(evidence_gap_recovery.get("file") or ""),
                rule="Active evidence gaps must be fetched or hash-justified before the project can claim stronger evidence support.",
                command=str(evidence_gap_recovery.get("command") or ""),
                receipt_paths=receipt_paths,
                write_boundary=write_boundary_payload(
                    writes_project_files=True,
                    write_paths=write_paths,
                    receipt_path=primary_receipt_path,
                    latest_path=latest_receipt_path,
                    read_only_actions=["inspect active gaps", "copy command", "preview source"],
                ) if write_paths else None,
            )
        )
    if report and (str(report.get("status") or "") == "blocked" or report_reasons):
        report_outcome_receipt_paths = [
            f"projects/{project}/workspace/forensic_workbench_reviews.jsonl",
            f"projects/{project}/workspace/forensic_workbench_latest_review.json",
        ]
        open_report_action = first_open_report_action(report_allowed_actions)
        report_repair_detail = (
            f"Next report action: {open_report_action.get('label')}"
            if open_report_action and open_report_action.get("label")
            else report_reasons[0] if report_reasons else "Report readiness needs review before the report is safe to use."
        )
        if open_report_action:
            first_report_action = open_report_action
            first_report_action_source = str(first_report_action.get("source") or "")
            first_report_backing_refs = (
                first_report_action.get("display_evidence_refs")
                if isinstance(first_report_action.get("display_evidence_refs"), list)
                else []
            )
            if not first_report_backing_refs:
                first_report_backing_refs = report_allowed_action_backing_refs(
                    project,
                    str(first_report_action.get("label") or ""),
                    first_report_action_source,
                )
            first_report_evidence_refs = [
                str(ref.get("path") or "")
                for ref in first_report_backing_refs
                if isinstance(ref, dict) and ref.get("path")
            ]
            if not first_report_evidence_refs:
                first_report_evidence_refs = [first_report_action_source or report_contract]
            first_report_action_command = normalize_report_action_command(
                first_report_action.get("command") or "",
                project=project,
                rubric=rubric,
                intake=intake,
            )
            workspace, subsection, primary_label = report_allowed_action_destination(first_report_action_command)
            actions.append(
                project_action(
                    action_id="follow_report_next_action",
                    label="Do next report action",
                    area="report",
                    detail=str(first_report_action.get("label") or "Follow the report readiness next action."),
                    workspace=workspace,
                    subsection=subsection,
                    primary_label=primary_label,
                    source=report_contract,
                    source_label="Report readiness file",
                    rule="The report readiness file names this as the next allowed report action; record the outcome with a review or saved next step after doing it.",
                    command=first_report_action_command,
                    outcome_receipt_paths=report_outcome_receipt_paths,
                    evidence_refs=first_report_evidence_refs,
                    display_evidence_refs=first_report_backing_refs
                    or [
                        {
                            "label": "Report readiness next action",
                            "path": first_report_action_source or report_contract,
                        }
                    ],
                    write_boundary=report_allowed_action_write_boundary(project, first_report_action_command)
                    if report_contract
                    else None,
                )
            )
            runnable_action = first_runnable_report_action(report_allowed_actions)
            if runnable_action and runnable_action is not first_report_action:
                command_text = normalize_report_action_command(
                    runnable_action.get("command") or "",
                    project=project,
                    rubric=rubric,
                    intake=intake,
                )
                workspace, subsection, primary_label = report_allowed_action_destination(command_text)
                command_source = str(runnable_action.get("source") or "")
                runnable_backing_refs = (
                    runnable_action.get("display_evidence_refs")
                    if isinstance(runnable_action.get("display_evidence_refs"), list)
                    else []
                )
                if not runnable_backing_refs:
                    runnable_backing_refs = report_allowed_action_backing_refs(
                        project,
                        str(runnable_action.get("label") or ""),
                        command_source,
                    )
                runnable_evidence_refs = [
                    str(ref.get("path") or "")
                    for ref in runnable_backing_refs
                    if isinstance(ref, dict) and ref.get("path")
                ]
                if not runnable_evidence_refs:
                    runnable_evidence_refs = [command_source or report_contract]
                actions.append(
                    project_action(
                        action_id="run_report_allowed_check",
                        label=primary_label,
                        area="report",
                        detail=str(runnable_action.get("label") or "Run the report readiness check."),
                        workspace=workspace,
                        subsection=subsection,
                        primary_label=primary_label,
                        source=report_contract,
                        source_label="Report readiness file",
                        rule="This command is listed as an allowed report action; run it through the matching workbench panel and save a review or next-step record after.",
                        command=command_text,
                        outcome_receipt_paths=report_outcome_receipt_paths,
                        evidence_refs=runnable_evidence_refs,
                        display_evidence_refs=runnable_backing_refs
                        or [
                            {
                                "label": "Report readiness check",
                                "path": command_source or report_contract,
                            }
                        ],
                        write_boundary=report_allowed_action_write_boundary(project, command_text)
                        if report_contract
                        else None,
                    )
                )
        report_support_display_refs = unique_display_evidence_refs(
            [
                ref
                for action in report_allowed_actions[:3]
                if isinstance(action, dict)
                for ref in (
                    action.get("display_evidence_refs")
                    if isinstance(action.get("display_evidence_refs"), list)
                    else report_allowed_action_backing_refs(
                        project,
                        str(action.get("label") or ""),
                        str(action.get("source") or ""),
                    )
                )
            ]
        )
        report_support_evidence_refs = [ref["path"] for ref in report_support_display_refs]
        if not report_support_evidence_refs:
            report_support_evidence_refs = unique_values(
                [
                    str(ref)
                    for action in report_allowed_actions[:3]
                    if isinstance(action, dict)
                    for ref in (action.get("evidence_refs") or [action.get("source") or ""])
                    if ref
                ]
            )
        actions.append(
            project_action(
                action_id="repair_report_support",
                label="Inspect report readiness issue",
                area="report",
                detail=report_repair_detail,
                workspace="save",
                subsection="Report readiness",
                primary_label="Open report readiness",
                source=report_contract,
                rule="A report readiness issue keeps the report inspect-only until the issue is reviewed or the readiness file is refreshed.",
                evidence_refs=report_support_evidence_refs,
                display_evidence_refs=report_support_display_refs,
                write_boundary=write_boundary_payload(
                    writes_project_files=False,
                    read_only_actions=["inspect report readiness", "open issue source", "copy next action"],
                ) if report_contract else None,
            )
        )
        actions.append(
            project_action(
                action_id="rerun_report_support",
                label="Check report readiness",
                area="report",
                detail="Refresh the report readiness file from the current project state, then review the new issues.",
                workspace="save",
                subsection="Report inputs",
                primary_label="Open rerun",
                source=report_contract,
                rule="Refreshing report readiness is allowed only through the fixed readiness command and history path.",
                command=report_action_cli_display(project, "check_readiness", "decision_brief"),
                receipt_paths=[
                    report_contract,
                    f"projects/{project}/workspace/forensic_workbench_report_support_checks.jsonl",
                    f"projects/{project}/workspace/forensic_workbench_latest_report_support_check.json",
                ]
                if report_contract
                else [],
                write_boundary=write_boundary_payload(
                    writes_project_files=True,
                    write_paths=[
                        report_contract,
                        f"projects/{project}/workspace/forensic_workbench_report_support_checks.jsonl",
                        f"projects/{project}/workspace/forensic_workbench_latest_report_support_check.json",
                    ],
                    receipt_path=f"projects/{project}/workspace/forensic_workbench_report_support_checks.jsonl",
                    latest_path=f"projects/{project}/workspace/forensic_workbench_latest_report_support_check.json",
                    read_only_actions=["preview report readiness", "copy command"],
                ) if report_contract else None,
            )
        )
        review_receipt_paths = [
            f"projects/{project}/workspace/forensic_workbench_reviews.jsonl",
            f"projects/{project}/workspace/forensic_workbench_latest_review.json",
        ]
        actions.append(
            project_action(
                action_id="save_report_review",
                label="Save review",
                area="review",
                detail="Record whether the report issue is reviewed, deferred, or holding the report.",
                workspace="review",
                subsection="Save review",
                primary_label="Save review",
                source=report_contract,
                rule="A report readiness issue becomes a recorded project decision only after a review is saved.",
                receipt_paths=review_receipt_paths,
                write_boundary=write_boundary_payload(
                    writes_project_files=True,
                    write_paths=review_receipt_paths,
                    receipt_path=review_receipt_paths[0],
                    latest_path=review_receipt_paths[1],
                    read_only_actions=["preview review", "edit review note"],
                ),
            )
        )
    for index, issue in enumerate([row for row in source_health.get("issues") or [] if isinstance(row, dict)][:3]):
        actions.append(source_health_project_action(issue, index=index + 1, source_path=source_health.get("source_path") or ""))
    return actions


def project_state_payload(
    *,
    project: str,
    rubric: str,
    intake: str,
    rows: list[dict[str, Any]],
    steps: list[dict[str, Any]],
    report: dict[str, Any],
    run_history: dict[str, Any],
    source_list: dict[str, Any],
    receipts: dict[str, Any],
    source_count: int,
    trace: dict[str, Any] | None = None,
    input_ready: bool = False,
    run_can_start: bool = False,
    evidence_readiness: dict[str, Any] | None = None,
    scoring_guide_readiness: dict[str, Any] | None = None,
    evidence_gap_recovery: dict[str, Any] | None = None,
    thesis_support: dict[str, Any] | None = None,
) -> dict[str, Any]:
    thesis_row = workflow_row(rows, "Bounded claim")
    falsifier_row = workflow_row(rows, "Next falsifier")
    source_row = workflow_row(rows, "Source readiness")
    evidence_row = workflow_row(rows, "Evidence readiness")
    assumptions_row = workflow_row(rows, "Assumptions and constraints")
    run_row = workflow_row(rows, "Run readiness")
    report_row = workflow_row(rows, "Report readiness")
    next_step = workflow_next_step(steps)
    prepare_step = next((step for step in steps if step.get("id") == "prepare_files"), {})
    run_summary = run_history.get("summary") if isinstance(run_history.get("summary"), dict) else {}
    compression_progress = (
        run_history.get("compression_progress")
        if isinstance(run_history.get("compression_progress"), dict)
        else {}
    )
    receipt_rows = receipts.get("receipts") if isinstance(receipts.get("receipts"), list) else []
    recent_changes_state = project_recent_changes_payload(receipts, run_history=run_history)
    support_issues = report.get("support_issues") if isinstance(report.get("support_issues"), list) else []
    report_allowed_actions = report.get("allowed_actions") if isinstance(report.get("allowed_actions"), list) else []
    recent_changes_state = enrich_recent_project_check_summary(recent_changes_state, report_allowed_actions)
    raw_sources = source_list.get("sources") if isinstance(source_list.get("sources"), list) else []
    trace = trace if isinstance(trace, dict) else {}
    evidence_readiness = evidence_readiness if isinstance(evidence_readiness, dict) else {}
    scoring_guide_readiness = scoring_guide_readiness if isinstance(scoring_guide_readiness, dict) else {}
    evidence_gap_recovery = evidence_gap_recovery if isinstance(evidence_gap_recovery, dict) else {}
    thesis_support_state = compact_thesis_support_payload(thesis_support)
    axiom_state = compact_project_axioms(project)
    source_health = action_intelligence_health_read_model()
    source_health_state = source_health_state_payload(source_health)
    source_total = len(raw_sources) if raw_sources else source_count
    charter_rel = project_charter_rel(project)
    charter_path_obj = project_charter_path(project)
    charter_exists = charter_path_obj.exists()
    intake_claim = _intake_claim_fields(project, intake, assumptions_row)
    intake_thesis = intake_claim["thesis"]
    intake_change_test = intake_claim["change_test"]
    intake_non_claims = intake_claim["non_claims"]
    assumption_summary = intake_claim["assumption_summary"]
    report_reasons = [
        display_guidance_text(issue.get("display_reason") or issue.get("reason") or "")
        for issue in support_issues
        if isinstance(issue, dict) and (issue.get("display_reason") or issue.get("reason"))
    ]
    next_destination = next_step.get("ui_destination") if isinstance(next_step.get("ui_destination"), dict) else {}
    prepare_status = str(prepare_step.get("status") or "")
    input_status = "usable" if prepare_status == "ready" else "needs review"
    local_evidence_status = str(evidence_readiness.get("status") or "")
    if local_evidence_status:
        input_status = "usable" if local_evidence_status == "usable" else local_evidence_status
    evidence_state = _evidence_status_block(
        trace=trace,
        evidence_readiness=evidence_readiness,
        source_list=source_list,
        source_row=source_row,
        evidence_row=evidence_row,
        input_status=input_status,
    )
    output_binding_ready = evidence_state["output_binding_ready"]
    source_ready = evidence_state["source_ready"]
    source_status = evidence_state["source_status"]
    evidence_summary = evidence_state["evidence_summary"]
    evidence_files_ready = evidence_state["evidence_files_ready"]
    thesis_status = workflow_row_status(thesis_row, "recorded" if intake_thesis else "missing")
    change_test_status = workflow_row_status(falsifier_row, "recorded" if intake_change_test else "missing")
    report_contract = str(report.get("report_support_contract") or report_row.get("file") or "")
    if report and not report_contract:
        report_contract = f"projects/{project}/synthesis/report_support_contract.json"
    run_state = _run_status_block(run_row, run_summary, run_history)
    next_action_state = _next_action_block(
        next_step=next_step,
        next_destination=next_destination,
        source_ready=source_ready,
        source_total=source_total,
        input_status=input_status,
    )
    admission = admission_summary_payload(
        project=project,
        rubric=rubric,
        intake=intake,
        trace=trace,
        evidence_readiness=evidence_readiness,
        scoring_guide_readiness=scoring_guide_readiness,
        evidence_gap_recovery=evidence_gap_recovery,
        input_ready=input_ready,
        run_can_start=run_can_start,
    )
    actions = _project_actions(
        project=project,
        rubric=rubric,
        intake=intake,
        charter_exists=charter_exists,
        charter_rel=charter_rel,
        intake_thesis=intake_thesis,
        prepare_status=prepare_status,
        prepare_step=prepare_step,
        evidence_files_ready=evidence_files_ready,
        source_ready=source_ready,
        source_total=source_total,
        input_status=input_status,
        output_binding_ready=output_binding_ready,
        evidence_readiness=evidence_readiness,
        scoring_guide_readiness=scoring_guide_readiness,
        evidence_gap_recovery=evidence_gap_recovery,
        report=report,
        report_reasons=report_reasons,
        report_allowed_actions=report_allowed_actions,
        report_contract=report_contract,
        source_health=source_health,
    )
    action_summary = _action_summary_block(actions)
    formalization_state = project_formalization_payload(project)
    file_inventory = project_file_inventory_payload(
        project=project,
        intake=intake,
        source_list=source_list,
        evidence_readiness=evidence_readiness,
        evidence_gap_recovery=evidence_gap_recovery,
        report=report,
        run_history=run_history,
        receipts=receipts,
        axiom_state=axiom_state,
        thesis_support=thesis_support if isinstance(thesis_support, dict) else {},
        formalization_state=formalization_state,
    )
    project_state = {
        "schema": "ztare-project-workbench-state-v1",
        "project": project,
        "rubric": rubric,
        "intake": intake,
        "project_key": case_key(project, intake),
        "charter": {
            "status": "recorded" if charter_exists else "missing",
            "summary": (
                "Project charter is present and can be inspected with the project files."
                if charter_exists
                else "Project charter is missing. Create it before relying on new project runs."
            ),
            "file": charter_rel,
            "exists": charter_exists,
        },
        "thesis": {
            "status": thesis_status,
            "text": workflow_row_detail(thesis_row, intake_thesis or "No thesis is recorded in the project brief."),
            "file": str(thesis_row.get("file") or intake),
        },
        "change_test": {
            "status": change_test_status,
            "text": workflow_row_detail(falsifier_row, intake_change_test or "No change test is recorded yet."),
            "file": str(falsifier_row.get("file") or intake),
        },
        "assumptions": {
            "status": "recorded" if intake_non_claims else workflow_row_status(assumptions_row, "not loaded"),
            "summary": assumption_summary,
            "file": intake if intake_non_claims else str(assumptions_row.get("file") or ""),
            "non_claims": intake_non_claims,
        },
        "axioms": axiom_state,
        "formalization": formalization_state,
        "thesis_support": thesis_support_state,
        "sources": {
            "status": source_status,
            "summary": workflow_row_detail(source_row, f"{source_total} source files loaded."),
            "source_count": source_total,
            "untyped_source_count": safe_int(source_list.get("untyped_source_count")),
            "invalid_source_type_count": safe_int(source_list.get("invalid_source_type_count")),
        },
        "source_health": source_health_state,
        "evidence": {
            "status": workflow_row_status(evidence_row, input_status),
            "summary": workflow_row_detail(evidence_row, evidence_summary),
            "file": str(
                evidence_row.get("evidence")
                or evidence_row.get("file")
                or evidence_readiness.get("compile_provenance")
                or evidence_readiness.get("compiled_packet")
                or ""
            ),
            "blocking": list(evidence_readiness.get("blocking") or []),
            "gap_count": safe_int(evidence_gap_recovery.get("gap_count")),
            "gap_summary": str(evidence_gap_recovery.get("summary") or ""),
            "gap_file": str(evidence_gap_recovery.get("file") or ""),
        },
        "admission": admission,
        "run": _run_block(
            run_state=run_state,
            scoring_guide_readiness=scoring_guide_readiness,
            run_summary=run_summary,
            compression_progress=compression_progress,
        ),
        "report": _report_block(
            report=report,
            report_row=report_row,
            report_reasons=report_reasons,
            report_allowed_actions=report_allowed_actions,
            report_contract=report_contract,
        ),
        "review": _review_block(receipt_rows),
        "recent_changes": recent_changes_state,
        "next_action": next_action_state,
        "action_summary": action_summary,
        "actions": actions,
        "files": file_inventory,
    }
    project_state["research_map"] = project_research_map_payload(project_state, trace=trace)
    return project_state


def recovery_workflow_payload_for_project(
    *,
    project: str,
    rubric: str,
    intake: str,
    mode: str,
    missing_reason: str,
) -> dict[str, Any]:
    project_root = snapshot.REPO / "projects" / project
    workspace = project_root / "workspace"
    recovery = existing_project_recovery_draft(project)
    evidence_readiness = local_evidence_readiness_payload(project_root)
    evidence_gap_recovery = local_evidence_gap_recovery_payload(project=project, project_root=project_root)
    scoring_guide_readiness = local_scoring_guide_readiness_payload(project=project, rubric=rubric)
    try:
        run_history = run_history_payload_for_project(project=project, rubric=rubric, intake=intake)
    except Exception:  # noqa: BLE001 - recovery should still render.
        run_history = {}
    try:
        source_list = source_list_payload(project=project)
    except Exception:  # noqa: BLE001 - raw file inventory still appears below.
        source_list = {}
    try:
        receipts = receipt_history_payload(project=project, intake=intake)
    except Exception:  # noqa: BLE001
        receipts = {"receipts": []}
    project_digest = hashlib.sha256(case_key(project, intake).encode("utf-8")).hexdigest()[:12]
    project_file_paths = [
        repo_rel(workspace / f"forensic_workbench_project_file_{project_digest}.json"),
        repo_rel(workspace / "forensic_workbench_project_files.jsonl"),
        repo_rel(workspace / "forensic_workbench_latest_project_file_write.json"),
    ]
    thesis_support = {
        "status": "not loaded",
        "display_status": "needs project brief",
        "errors": [missing_reason],
    }
    run_summary = run_history.get("summary") if isinstance(run_history.get("summary"), dict) else {}
    run_count = safe_int(run_summary.get("run_rows"))
    latest_score = run_summary.get("latest_score")
    if run_count or latest_score is not None:
        score_text = "no score" if latest_score is None else f"latest score {latest_score}"
        count_text = (
            f"{run_count} historical run{'s' if run_count != 1 else ''}"
            if run_count
            else "a historical run file"
        )
        run_readiness_detail = (
            f"Found {count_text} with {score_text}. New runs stay blocked until the project brief is connected."
        )
    else:
        run_readiness_detail = "Runs stay blocked until the project brief is connected."
    rows = [
        {
            "label": "Bounded claim",
            "status": "needs_attention" if not recovery.get("bounded_claim") else "drafted",
            "detail": recovery.get("bounded_claim") or "Review the folder and save a project brief before running.",
            "file": recovery.get("project_dir") or f"projects/{project}",
        },
        {
            "label": "Next falsifier",
            "status": "drafted",
            "detail": recovery.get("next_falsifier") or "Save a change test in the project brief.",
            "file": recovery.get("project_dir") or f"projects/{project}",
        },
        {
            "label": "Assumptions and constraints",
            "status": "drafted",
            "detail": "; ".join(recovery.get("non_claims") or []) or "Caveats must be reviewed before this folder enters the normal project flow.",
            "file": recovery.get("project_dir") or f"projects/{project}",
        },
        {
            "label": "Source readiness",
            "status": "needs_attention",
            "detail": recovery.get("summary") or "Review recovered source files before saving the project brief.",
            "file": recovery.get("project_dir") or f"projects/{project}",
        },
        {
            "label": "Evidence readiness",
            "status": "needs_attention",
            "detail": "Evidence can be inspected now; source and evidence preparation stays blocked until the project brief is saved.",
            "file": recovery.get("project_dir") or f"projects/{project}",
        },
        {
            "label": "Run readiness",
            "status": "blocked",
            "detail": run_readiness_detail,
            "file": recovery.get("project_dir") or f"projects/{project}",
        },
    ]
    add_intake_action = recovery.get("add_intake_action") if isinstance(recovery.get("add_intake_action"), dict) else {}
    connect_boundary = (
        add_intake_action.get("write_boundary")
        if isinstance(add_intake_action.get("write_boundary"), dict)
        else recovery.get("add_intake_write_boundary") if isinstance(recovery.get("add_intake_write_boundary"), dict)
        else write_boundary_payload(writes_project_files=False)
    )
    steps = [
        workflow_step(
            step_id="open_project",
            label="Open project",
            status="ready",
            route="GET /api/projects -> GET /api/project-recovery-draft",
            detail="Existing project folder loaded from local files.",
        ),
        workflow_step(
            step_id="connect_project",
            label="Create project brief",
            status="needs_attention" if recovery.get("can_add_intake") else "done",
            route="GET /api/project-recovery-draft -> POST /api/project-create",
            detail=recovery.get("summary") or "Save the project brief before normal project work can run.",
            write_boundary=connect_boundary,
            local_action="Create project brief",
            ui_destination={"workspace": "projects", "subsection": "Connect project"},
        ),
        workflow_step(
            step_id="prepare_files",
            label="Prepare files",
            status="waiting",
            route="GET /api/sources, POST /api/source-action",
            detail="Prepare source and evidence files after the project brief is saved.",
        ),
        workflow_step(
            step_id="preflight",
            label="Check readiness",
            status="waiting",
            route="POST /api/preflight",
            detail="The readiness check is waiting for a saved project brief.",
        ),
        workflow_step(
            step_id="project_run",
            label="Project run",
            status="waiting",
            route="POST /api/run",
            detail="Project runs are blocked until the folder is connected.",
        ),
        workflow_step(
            step_id="review_report",
            label="Review report",
            status="waiting",
            route="GET /api/report-contract -> POST /api/review",
            detail="Report readiness can be reviewed after the project brief is saved.",
        ),
        workflow_step(
            step_id="save_project",
            label="Save project",
            status="not_saved",
            route="POST /api/project-file",
            detail="Save the project file after the folder is connected.",
            write_boundary=write_boundary_payload(
                writes_project_files=True,
                write_paths=project_file_paths,
                receipt_path=project_file_paths[1],
                latest_path=project_file_paths[2],
            ),
        ),
    ]
    summary = workflow_summary_payload(steps)
    project_state = project_state_payload(
        project=project,
        rubric=rubric,
        intake=intake,
        rows=rows,
        steps=steps,
        report={},
        run_history=run_history,
        source_list=source_list,
        receipts=receipts,
        source_count=project_source_count(project_root),
        input_ready=False,
        run_can_start=False,
        evidence_readiness=evidence_readiness,
        scoring_guide_readiness=scoring_guide_readiness,
        evidence_gap_recovery=evidence_gap_recovery,
        thesis_support=thesis_support,
    )
    recovery_action = recovery.get("add_intake_action") if isinstance(recovery.get("add_intake_action"), dict) else None
    if recovery_action:
        # Recovery mode starts with one action: save the project brief. Later
        # repairs are useful only after that write makes the folder a project.
        project_state["actions"] = [recovery_action]
        project_state["action_summary"] = {
            "total_count": 1,
            "visible_count": 1,
            "hidden_count": 0,
            "project_repair_count": 1,
            "project_inspect_count": 0,
            "advisory_count": 0,
            "area_counts": {"recovery": 1},
            "action_type_counts": {"project_repair": 1},
        }
    project_state["recovery"] = recovery.get("recovery_summary") or {}
    project_object_contract = project_object_contract_payload(
        project=project,
        intake=intake,
        project_key=case_key(project, intake),
        steps=steps,
        summary=summary,
        project_state=project_state,
    )
    project_state = {**project_state, "project_object_contract": project_object_contract}
    return {
        "schema": WORKFLOW_SCHEMA,
        "ok": True,
        "served_from": "local_api",
        "mode": mode,
        "recovery_required": True,
        "project": project,
        "rubric": rubric,
        "intake": intake,
        "project_key": case_key(project, intake),
        "case_key": case_key(project, intake),
        "steps": steps,
        "summary": summary,
        "project_state": project_state,
        "project_object_contract": project_object_contract,
        "recovery": recovery,
        **summary,
        "next_step": workflow_next_step(steps),
        "errors": [missing_reason],
    }


def workflow_payload_for_project(
    *,
    project: str,
    rubric: str | None = None,
    intake: str | None = None,
    renderer: str | None = None,
    mode: str = "full",
) -> dict[str, Any]:
    project = snapshot.validate_project_slug(project)
    rubric = rubric or project
    intake = intake or snapshot.default_intake_for_project(project)
    renderer = renderer or snapshot.DEFAULT_RENDERER
    mode = str(mode or "fast").strip().lower()
    if mode not in {"fast", "full"}:
        raise ValueError("workflow mode must be fast or full")
    try:
        project_intake_path(project, intake, allow_examples=True)
    except FileNotFoundError as exc:
        return recovery_workflow_payload_for_project(
            project=project,
            rubric=rubric,
            intake=intake,
            mode=mode,
            missing_reason=display_text(exc),
        )
    intake_target_path = project_intake_target_path(project, intake, allow_examples=True)
    project_root = snapshot.REPO / "projects" / project
    workspace = project_root / "workspace"
    evidence_readiness = local_evidence_readiness_payload(project_root)
    scoring_guide_readiness = local_scoring_guide_readiness_payload(project=project, rubric=rubric)
    evidence_gap_recovery = local_evidence_gap_recovery_payload(project=project, project_root=project_root)

    errors: list[str] = []
    rows: list[dict[str, Any]] = []
    trace: dict[str, Any] = {}
    report: dict[str, Any] = {}
    receipts: dict[str, Any] = {}
    run_history: dict[str, Any] = {}
    source_list: dict[str, Any] = {}
    thesis_support: dict[str, Any] = {}

    input_ready = False
    preflight_ready = False
    preflight_done = False
    run_done = False
    report_status = ""
    report_ready = False
    run_can_start = False
    source_count = project_source_count(project_root)

    if mode == "full":
        try:
            snapshot_payload = snapshot_payload_for_project(project=project, rubric=rubric, intake=intake, renderer=renderer)
            rows = list(snapshot_payload.get("rows") or [])
        except Exception as exc:  # noqa: BLE001 - workflow should still return route/write contracts.
            errors.append(f"project data: {display_text(exc)}")
        try:
            trace = trace_payload_for_project(project=project, rubric=rubric, intake=intake)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"trace: {display_text(exc)}")
        try:
            report = report_contract_payload_for_project(project=project, rubric=rubric, intake=intake, renderer=renderer)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"report: {display_text(exc)}")
        try:
            run_history = run_history_payload_for_project(project=project, rubric=rubric, intake=intake)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"run history: {display_text(exc)}")
        try:
            source_list = source_list_payload(project=project)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"sources: {display_text(exc)}")

        source_row = next((row for row in rows if row.get("label") == "Source readiness"), {})
        evidence_row = next((row for row in rows if row.get("label") == "Evidence readiness"), {})
        input_ready = bool(
            source_row
            and evidence_row
            and source_row.get("kind") != "attention"
            and evidence_row.get("kind") != "attention"
        )
        if evidence_readiness.get("status") != "usable":
            input_ready = False
        plan = trace.get("plan_preview") if isinstance(trace.get("plan_preview"), dict) else {}
        preflight_receipt = trace.get("preflight_receipt") or trace.get("loop_admission") or {}
        if not isinstance(preflight_receipt, dict):
            preflight_receipt = {}
        preflight_ready = bool(
            preflight_receipt.get("receipt_count")
            or preflight_receipt.get("available")
            or plan.get("status") == "ready_for_bounded_run"
        )
        run_summary = run_history.get("summary") if isinstance(run_history.get("summary"), dict) else {}
        latest_preflight = run_history.get("latest_preflight") if isinstance(run_history.get("latest_preflight"), dict) else {}
        preflight_done = bool(
            preflight_receipt.get("receipt_count")
            or preflight_receipt.get("available")
            or latest_preflight.get("status") == "accepted"
        )
        run_done = bool(safe_int(run_summary.get("run_rows")) or run_summary.get("latest_score") is not None)
        report_status = str(report.get("status") or "")
        report_ready = bool(report_status and report_status != "blocked")
        run_can_start = plan.get("status") == "ready_for_bounded_run"
        source_count = len(source_list.get("sources") or []) if isinstance(source_list.get("sources"), list) else source_count
    else:
        try:
            intake_payload = intake_payload_for_project(project, intake, allow_examples=True)
            ref_summary = ((intake_payload.get("reference_status") or {}).get("summary") or {})
            source_refs = (intake_payload.get("editable_fields") or {}).get("source_refs") or []
            evidence_refs = (intake_payload.get("editable_fields") or {}).get("evidence_refs") or []
            input_ready = bool(
                source_refs
                and evidence_refs
                and safe_int(ref_summary.get("missing")) == 0
                and safe_int(ref_summary.get("unsafe")) == 0
            )
            if evidence_readiness.get("status") != "usable":
                input_ready = False
        except Exception as exc:  # noqa: BLE001
            errors.append(f"intake: {display_text(exc)}")
        preflight_done = (workspace / "iteration_telemetry.jsonl").exists()
        preflight_ready = (workspace / "source_index_receipt.json").exists() or preflight_done
        run_done = (project_root / "latest_eval_results.json").exists() or (workspace / "eval_history.jsonl").exists()
        report = read_optional_json_object(project_root / "synthesis" / "report_support_contract.json")
        if report:
            binding = report.get("synthesis_input_binding") if isinstance(report.get("synthesis_input_binding"), dict) else {}
            support_issues = report_support_issues(report, binding)
            report["support_issues"] = support_issues
            report["allowed_actions"] = compact_report_allowed_actions(report, project=project, rubric=rubric, intake=intake)
            report["display_status_reasons"] = [
                str(issue.get("display_reason") or issue.get("reason") or "")
                for issue in support_issues
                if issue.get("display_reason") or issue.get("reason")
            ]
        report_status = str(report.get("status") or ("ready" if report else ""))
        report_ready = bool(report_status and report_status != "blocked")
        try:
            run_history = run_history_payload_for_project(project=project, rubric=rubric, intake=intake)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"run history: {display_text(exc)}")
            run_history = {}
        run_summary = run_history.get("summary") if isinstance(run_history.get("summary"), dict) else {}
        run_done = bool(safe_int(run_summary.get("run_rows")) or run_summary.get("latest_score") is not None)
        run_can_start = input_ready and preflight_ready
    try:
        thesis_support = claim_support_payload_for_project(project=project, rubric=rubric, intake=intake)
    except Exception as exc:  # noqa: BLE001 - workflow should still load and report unavailable support.
        thesis_support = {
            "status": "not loaded",
            "display_status": "not loaded",
            "errors": [display_text(exc)],
        }
    if scoring_guide_readiness.get("status") != "usable":
        preflight_ready = False
        preflight_done = False
        run_can_start = False

    try:
        receipts = receipt_history_payload(project=project, intake=intake)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"saved history: {display_text(exc)}")
    receipt_rows = receipts.get("receipts") if isinstance(receipts.get("receipts"), list) else []
    if isinstance(report, dict) and isinstance(report.get("allowed_actions"), list):
        report = dict(report)
        report["allowed_actions"] = annotate_completed_report_actions(
            [action for action in report.get("allowed_actions") if isinstance(action, dict)],
            receipt_rows,
        )
        report["completed_allowed_action_count"] = sum(
            1 for action in report["allowed_actions"] if isinstance(action, dict) and report_action_completed(action)
        )
    review_done = any(row.get("kind") == "review" for row in receipt_rows if isinstance(row, dict))
    project_file_done = any(row.get("kind") in {"case_file", "project_file"} for row in receipt_rows if isinstance(row, dict))

    project_digest = hashlib.sha256(case_key(project, intake).encode("utf-8")).hexdigest()[:12]
    project_file_paths = [
        repo_rel(workspace / f"forensic_workbench_project_file_{project_digest}.json"),
        repo_rel(workspace / "forensic_workbench_project_files.jsonl"),
        repo_rel(workspace / "forensic_workbench_latest_project_file_write.json"),
    ]

    evidence_blockers = [str(row) for row in evidence_readiness.get("blocking") or [] if row]
    source_side_prepared = source_count > 0 and (
        bool(source_list.get("accepted"))
        or not {"file index", "file-index history"} & set(evidence_blockers)
    )
    active_evidence_gap_count = safe_int(evidence_gap_recovery.get("gap_count"))
    active_gap_is_first_repair = active_evidence_gap_count > 0 and evidence_readiness.get("status") == "usable"
    if active_gap_is_first_repair:
        gap_receipt_paths = [
            str(path)
            for path in evidence_gap_recovery.get("receipt_paths", [])
            if path
        ]
        gap_write_paths = [
            str(path)
            for path in evidence_gap_recovery.get("write_paths", gap_receipt_paths)
            if path
        ]
        gap_primary_receipt = next((path for path in gap_receipt_paths if "forensic_workbench_evidence_fetches" in path), "")
        if not gap_primary_receipt:
            gap_primary_receipt = gap_receipt_paths[0] if gap_receipt_paths else ""
        gap_latest_receipt = next((path for path in gap_receipt_paths if "latest_evidence_fetch" in path), "")
        if not gap_latest_receipt:
            gap_latest_receipt = gap_receipt_paths[-1] if gap_receipt_paths else ""
        prepare_label = "Fetch or justify evidence gaps"
        prepare_detail = str(evidence_gap_recovery.get("summary") or "Active evidence gaps need fetch or justification.")
        prepare_step_status = "needs_attention"
        prepare_local_action = "Fetch or justify evidence gaps"
        prepare_destination = {"workspace": "sources", "subsection": "Prepare files"}
        prepare_route = "GET /api/evidence-gaps -> POST /api/evidence-fetch or POST /api/evidence-gap-justify"
        prepare_write_boundary = write_boundary_payload(
            writes_project_files=bool(gap_write_paths),
            write_paths=gap_write_paths,
            receipt_path=gap_primary_receipt,
            latest_path=gap_latest_receipt,
            read_only_actions=["open evidence gap panel", "preview gap source", "choose fetch or justify"],
        )
    elif source_side_prepared and evidence_readiness.get("status") != "usable":
        prepare_label = "Prepare evidence summary"
        prepare_detail = str(evidence_readiness.get("summary") or "Source files are ready; the evidence summary still needs preparation.")
        prepare_step_status = "ready" if input_ready else "needs_attention"
        prepare_local_action = "Prepare evidence summary"
        prepare_destination = None
        prepare_route = "POST /api/source-action action=evidence_prepare"
        prepare_write_boundary = source_action_write_boundary(project, rubric, "evidence_prepare")
    else:
        prepare_label = "Prepare files"
        prepare_detail = f"{source_count} source files loaded; evidence summary is {'usable' if input_ready else 'not ready'}."
        prepare_step_status = "ready" if input_ready else "needs_attention"
        prepare_local_action = "Edit intake and source files"
        prepare_destination = None
        prepare_route = "GET /api/sources, POST /api/intake, POST /api/source-import, POST /api/source-edit"
        prepare_write_boundary = write_boundary_payload(
            writes_project_files=True,
            write_paths=[
                repo_rel(intake_target_path),
                repo_rel(workspace / "forensic_workbench_intake_edits.jsonl"),
                repo_rel(workspace / "forensic_workbench_latest_intake_edit.json"),
                repo_rel(project_root / "raw"),
                repo_rel(workspace / "forensic_workbench_source_imports.jsonl"),
                repo_rel(workspace / "forensic_workbench_source_edits.jsonl"),
            ],
            receipt_path=repo_rel(workspace / "forensic_workbench_intake_edits.jsonl"),
            latest_path=repo_rel(workspace / "forensic_workbench_latest_intake_edit.json"),
        )
    preflight_label = (
        "Fix scoring guide"
        if input_ready and scoring_guide_readiness.get("status") != "usable"
        else "Check readiness"
    )
    preflight_status = (
        "needs_attention"
        if input_ready and scoring_guide_readiness.get("status") != "usable"
        else "done" if preflight_done else "ready" if preflight_ready else "not_run"
    )
    preflight_detail = (
        str(scoring_guide_readiness.get("summary") or "Scoring guide needs review before a run can start.")
        if preflight_label == "Fix scoring guide"
        else "Runs the local readiness check only; it does not start model work."
    )
    if preflight_label == "Fix scoring guide":
        scoring_guide_path = f"rubrics/{rubric}.json"
        scoring_guide_ledger = f"projects/{project}/workspace/forensic_workbench_scoring_guides.jsonl"
        scoring_guide_latest = f"projects/{project}/workspace/forensic_workbench_latest_scoring_guide.json"
        preflight_route = "GET /api/scoring-guide -> POST /api/scoring-guide"
        preflight_local_action = "Fix scoring guide"
        preflight_destination = {"workspace": "run", "subsection": "Ready to run"}
        preflight_write_boundary = write_boundary_payload(
            writes_project_files=False,
            writes_repo_files=True,
            write_paths=[scoring_guide_path, scoring_guide_ledger, scoring_guide_latest],
            receipt_path=scoring_guide_ledger,
            latest_path=scoring_guide_latest,
            read_only_actions=["preview scoring guide", "copy validation command"],
            no_change_boundary=scoring_guide_no_change_boundary(),
        )
    else:
        preflight_route = "POST /api/preflight"
        preflight_local_action = ""
        preflight_destination = None
        preflight_write_boundary = None
    review_write_paths = [
        repo_rel(workspace / "forensic_workbench_applied"),
        repo_rel(workspace / "forensic_workbench_reviews.jsonl"),
        repo_rel(workspace / "forensic_workbench_latest_review.json"),
    ]
    preflight_paths = preflight_write_paths(trace) or [preflight_telemetry_path(project)]
    run_write_paths = bounded_run_write_paths(project) if run_can_start else []
    report_allowed_actions_for_workflow = [
        action for action in (report.get("allowed_actions") if isinstance(report.get("allowed_actions"), list) else [])
        if isinstance(action, dict)
    ]
    first_report_action_for_workflow = first_open_report_action(report_allowed_actions_for_workflow) or {}
    first_report_action_label = str(first_report_action_for_workflow.get("label") or "").strip()
    first_report_action_command = normalize_report_action_command(
        first_report_action_for_workflow.get("command") or "",
        project=project,
        rubric=rubric,
        intake=intake,
    ) if first_report_action_for_workflow else ""
    if first_report_action_label:
        report_step_detail = first_report_action_label
        report_step_route = (
            "GET /api/report-contract -> allowed report action"
            if first_report_action_command
            else "GET /api/report-contract"
        )
        report_step_workspace, report_step_subsection, report_step_primary = (
            report_allowed_action_destination(first_report_action_command)
            if first_report_action_command
            else ("save", "Report readiness", "Open report readiness")
        )
        report_step_label = report_step_primary if first_report_action_command else "Do next report action"
        report_step_destination = {
            "workspace": report_step_workspace,
            "subsection": report_step_subsection,
        }
        report_step_local_action = report_step_primary
        report_step_write_boundary = (
            report_allowed_action_write_boundary(project, first_report_action_command)
            if first_report_action_command
            else write_boundary_payload(
                writes_project_files=False,
                read_only_actions=["inspect report readiness", "preview backing files", "copy next action"],
            )
        )
    else:
        report_step_label = "Review report"
        report_step_detail = report_workflow_detail(report)
        report_step_route = "GET /api/report-contract -> POST /api/review"
        report_step_destination = None
        report_step_local_action = ""
        report_step_write_boundary = write_boundary_payload(
            writes_project_files=bool(report),
            write_paths=review_write_paths if report else [],
            receipt_path=review_write_paths[1] if report else "",
            latest_path=review_write_paths[2] if report else "",
            read_only_actions=["inspect report readiness", "preview backing files", "edit review note"],
        )

    steps = [
        workflow_step(
            step_id="open_project",
            label="Open project",
            status="ready",
            route="GET /api/projects -> GET /api/snapshot",
            detail="Project inventory and project data are loaded from the local API.",
        ),
        workflow_step(
            step_id="prepare_files",
            label=prepare_label,
            status=prepare_step_status,
            route=prepare_route,
            detail=prepare_detail,
            write_boundary=prepare_write_boundary,
            source_status=prepare_step_status,
            local_action=prepare_local_action,
            ui_destination=prepare_destination,
        ),
        workflow_step(
            step_id="preflight",
            label=preflight_label,
            status=preflight_status,
            route=preflight_route,
            detail=preflight_detail,
            write_boundary=preflight_write_boundary
            or write_boundary_payload(
                writes_project_files=True,
                write_paths=preflight_paths,
                receipt_path=preflight_paths[0] if preflight_paths else "",
                read_only_actions=["Copy command", "Inspect output"],
            ),
            local_action=preflight_local_action,
            ui_destination=preflight_destination,
        ),
        workflow_step(
            step_id="project_run",
            label="Project run",
            status="done" if run_done else "ready" if run_can_start else "waiting",
            route="POST /api/run",
            detail="First request is a no-write preview; confirmed request may start model work.",
            write_boundary=write_boundary_payload(
                writes_project_files=bool(run_can_start),
                write_paths=run_write_paths,
                receipt_path=run_write_paths[0] if run_write_paths else "",
                latest_path=run_write_paths[1] if len(run_write_paths) > 1 else "",
                read_only_actions=["Inspect readiness", "Copy command"],
            ),
        ),
        workflow_step(
            step_id="review_report",
            label=report_step_label,
            status="ready" if report_ready else "needs_attention",
            route=report_step_route,
            detail=report_step_detail,
            write_boundary=report_step_write_boundary,
            local_action=report_step_local_action,
            ui_destination=report_step_destination,
            source_status="reviewed" if review_done else "",
        ),
        workflow_step(
            step_id="save_project",
            label="Save project",
            status="done" if project_file_done else "not_saved",
            route="POST /api/project-file",
            detail="Saves the project file plus saved history.",
            write_boundary=write_boundary_payload(
                writes_project_files=True,
                write_paths=project_file_paths,
                receipt_path=project_file_paths[1],
                latest_path=project_file_paths[2],
            ),
        ),
    ]
    summary = workflow_summary_payload(steps)
    project_state = project_state_payload(
        project=project,
        rubric=rubric,
        intake=intake,
        rows=rows,
        steps=steps,
        report=report,
        run_history=run_history,
        source_list=source_list,
        receipts=receipts,
        source_count=source_count,
        trace=trace,
        input_ready=input_ready,
        run_can_start=run_can_start,
        evidence_readiness=evidence_readiness,
        scoring_guide_readiness=scoring_guide_readiness,
        evidence_gap_recovery=evidence_gap_recovery,
        thesis_support=thesis_support,
    )
    project_object_contract = project_object_contract_payload(
        project=project,
        intake=intake,
        project_key=case_key(project, intake),
        steps=steps,
        summary=summary,
        project_state=project_state,
    )
    project_state = {**project_state, "project_object_contract": project_object_contract}
    return {
        "schema": WORKFLOW_SCHEMA,
        "ok": True,
        "served_from": "local_api",
        "mode": mode,
        "project": project,
        "rubric": rubric,
        "intake": intake,
        "project_key": case_key(project, intake),
        "case_key": case_key(project, intake),
        "steps": steps,
        "summary": summary,
        "project_state": project_state,
        "project_object_contract": project_object_contract,
        **summary,
        "next_step": workflow_next_step(steps),
        "errors": errors,
    }


def save_research_map_payload(request: dict[str, Any]) -> dict[str, Any]:
    project = snapshot.validate_project_slug(str(request.get("project") or snapshot.DEFAULT_PROJECT))
    rubric = str(request.get("rubric") or project)
    intake = str(request.get("intake") or snapshot.default_intake_for_project(project))
    workflow = workflow_payload_for_project(project=project, rubric=rubric, intake=intake, mode="full")
    project_state = workflow.get("project_state") if isinstance(workflow.get("project_state"), dict) else {}
    research_map = project_state.get("research_map") if isinstance(project_state.get("research_map"), dict) else {}
    if not research_map:
        raise ValueError("research map is not available for this project")
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json") as staged:
        json.dump(research_map, staged)
        staged.flush()
        result = ztare_cli_payload([
            "forensic-workbench", "save-research-map",
            "--project", project,
            "--rubric", rubric,
            "--intake", intake,
            "--from", staged.name,
            "--repo", str(snapshot.REPO),
            "--json",
        ], project=project, timeout=90)
    if result.get("ok") is False:
        raise ValueError(str(result.get("error") or "research map save was refused"))
    return {
        **result,
        "served_from": "local_api",
    }


def advisory_model(project: str) -> str:
    """The single model the advisory trio (eigenquestion, isomorphism, forecast) runs on — the user's
    selected Report model from global settings (falls back to the Evidence model, then gemini). One
    source so all three behave identically; each CLI routes it api/subscription per repo policy."""
    return workbench_command_context(project, project).get("report_model") or "gemini"


def project_draft_payload(*, text: str, confirmed: bool = False) -> dict[str, Any]:
    """Draft the four mandate fields (task, bounded_claim, next_falsifier, non_claims) from a pasted document
    via `ztare project draft` — one model call. Advisory: it pre-fills the create form so the researcher
    refines instead of authoring from a blank page. Nothing is created here; the operator edits + creates."""
    text = str(text or "").strip()
    if not text:
        return {"ok": False, "status": "error", "error": "Paste a document to draft from."}
    model = os.environ.get("ZTARE_WORKBENCH_REPORT_MODEL") or os.environ.get("ZTARE_WORKBENCH_MODEL") or "gemini"
    display = f"ztare project draft --doc <document> --model {model} --json"
    if not confirmed:
        return {"ok": True, "status": "needs_confirmation", "requires_confirmation": True, "writes": False,
                "command": display,
                "note": ("Reads your document and drafts the pivotal question, a tight falsifiable thesis, the "
                         "falsifier, and scope guards — so you refine instead of starting from a blank page. "
                         "One model call; you edit every field before creating.")}
    tmp_path: str | None = None
    proc = None
    try:
        fd, tmp_path = tempfile.mkstemp(suffix=".md", prefix="wb_draft_")
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        cmd = [SERVER_PYTHON, "-m", "src.ztare.cli", "project", "draft", "--doc", tmp_path, "--model", model, "--json"]
        proc = run_workbench_command(cmd, timeout=200)
        match = re.search(r"\{.*\}", proc.stdout or "", re.S)
        data = json.loads(match.group(0)) if match else {}
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
    if not isinstance(data, dict) or not data.get("ok"):
        err = tail_display_text((proc.stderr or proc.stdout) if proc else "drafting failed")
        return {"ok": False, "status": "error", "command": display, "error": err or "drafting produced no fields"}
    data["status"] = "done"
    return data


def document_extract_payload(request: dict[str, Any]) -> dict[str, Any]:
    """Read-only extraction preview for browser uploads. Project creation re-extracts the submitted original
    bytes, so this response is a preview rather than a trust boundary."""
    filename = str(request.get("filename") or "").strip()
    encoded = str(request.get("content_base64") or "").strip()
    if not filename or not encoded:
        return {"ok": False, "error": "filename and document bytes are required"}
    if not DOCUMENT_IMPORT_FILENAME_RE.fullmatch(filename):
        return {"ok": False, "error": "unsupported or nested document filename"}
    try:
        data = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        return {"ok": False, "error": "document bytes are not valid base64"}
    try:
        from ztare.workspace.document_ingest import extract_document_bytes
        return extract_document_bytes(filename, data)
    except Exception as exc:  # noqa: BLE001 — extraction failures are returned as a typed preview result
        return {"ok": False, "error": str(exc)[:300]}


def falsify_claim_payload(*, project: str, claim: str, confirmed: bool = False) -> dict[str, Any]:
    """Advisory: run the adversarial inverter against ONE claim (ztare research falsify) — one model call,
    returns 2-4 concrete falsification tests each with a pre-committed fail criterion. Fast single-claim
    adversarial without a full paid run; no side effects on the project's run artifacts."""
    project = snapshot.validate_project_slug(str(project or ""))
    claim = str(claim or "").strip()
    if not claim:
        return {"ok": False, "status": "error", "error": "No claim to stress-test."}
    model = advisory_model(project)
    cmd = [SERVER_PYTHON, "-m", "src.ztare.cli", "research", "falsify",
           "--project", project, "--claim", claim, "--model", model, "--json"]
    display = f"ztare research falsify --project {project} --claim <claim> --model {model} --json"
    if not confirmed:
        return {"ok": True, "status": "needs_confirmation", "requires_confirmation": True, "writes": False,
                "command": display,
                "note": ("Runs the adversarial inverter against this one claim — it proposes 2-4 concrete "
                         "falsification tests, each with a pre-committed fail criterion. One model call, no "
                         "full run, and it doesn't touch your run history.")}
    proc = run_workbench_command(cmd, timeout=240)
    match = re.search(r"\{.*\}", proc.stdout or "", re.S)
    data = json.loads(match.group(0)) if match else {}
    if not isinstance(data, dict) or not data.get("ok"):
        return {"ok": False, "status": "error", "command": display,
                "error": tail_display_text(proc.stderr or proc.stdout or "falsification failed")}
    data["status"] = "done"
    return data


def rubric_review_payload(*, project: str, rubric: str | None = None, confirmed: bool = False) -> dict[str, Any]:
    """Advisory: run `ztare rubric review` (1 model call) — a PRE-RUN critique of the scoring rubric against
    the charter + workspace. Answers the six that decide whether the measurement can be trusted: gaming-surface
    coverage, evidence-anchor requirement, whether a high score is reachable WITHOUT evidence, criterion
    independence, persona blind spots, charter-spirit coverage. Catches a gameable rubric before a paid run.
    Writes a review + a candidate patch for operator review; never auto-edits the rubric (commit stays CLI)."""
    project = snapshot.validate_project_slug(str(project or ""))
    rubric_name = snapshot.validate_project_slug(str(rubric)) if rubric else project
    model = advisory_model(project)
    cmd = [SERVER_PYTHON, "-m", "src.ztare.cli", "rubric", "review",
           "--project", project, "--rubric", rubric_name, "--model", model, "--json"]
    display = f"ztare rubric review --project {project} --rubric {rubric_name} --model {model} --json"
    if not confirmed:
        return {"ok": True, "status": "needs_confirmation", "requires_confirmation": True, "writes": True,
                "command": display,
                "note": ("Asks the model whether your scoring rubric can be gamed BEFORE you pay for a run — "
                         "gaming coverage, evidence anchoring, whether a high score is reachable without evidence, "
                         "criterion independence, persona blind spots, and charter-spirit coverage. Advisory: "
                         "writes a review + a candidate patch for your review, never edits the rubric.")}
    proc = run_workbench_command(cmd, timeout=240)
    match = re.search(r"\{.*\}", proc.stdout or "", re.S)
    data = json.loads(match.group(0)) if match else {}
    review = data.get("review_payload") if isinstance(data, dict) else None
    if not isinstance(review, dict) or not review:
        return {"ok": False, "status": "error", "command": display,
                "error": tail_display_text(proc.stderr or proc.stdout or "rubric review produced no payload")}
    return {"ok": True, "status": "done", "accepted": True, "command": display,
            "review": review,
            "scenario_failed": bool(data.get("scenario_failed")),
            "review_path": str(data.get("review_path") or ""),
            "patch_path": str(data.get("patch_path") or "")}


def eigenquestion_payload(*, project: str, confirmed: bool = False) -> dict[str, Any]:
    """Advisory: run `ztare research eigenquestion` (1 model call) → the proposed eigenquestion (the
    most pivotal framing question). Operator-reviewed, never auto-adopted into the charter."""
    project = snapshot.validate_project_slug(str(project or ""))
    model = advisory_model(project)
    cmd = [SERVER_PYTHON, "-m", "src.ztare.cli", "research", "eigenquestion", "--project", project, "--model", model]
    display = f"ztare research eigenquestion --project {project} --model {model}"
    if not confirmed:
        return {"ok": True, "status": "needs_confirmation", "requires_confirmation": True, "writes": True,
                "command": display,
                "note": ("Asks the model to propose the one question that most moves the thesis — tailored to "
                         "this project's evidence. Advisory: written to a file for your review, never auto-adopted.")}
    proc = run_workbench_command(cmd, timeout=180)
    if proc.returncode != 0:
        return {"ok": False, "status": "error", "command": display,
                "error": tail_display_text(proc.stderr or proc.stdout or "eigenquestion generation failed")}
    proj_dir = snapshot.REPO / "projects" / project
    files = sorted(proj_dir.glob("proposed_eigenquestion_*.md"), key=os.path.getmtime)
    text = files[-1].read_text(encoding="utf-8") if files else ""
    path = f"projects/{project}/{files[-1].name}" if files else ""
    return {"ok": True, "status": "done", "accepted": True, "command": display,
            "eigenquestion": text.strip(), "path": path}


def isomorphism_payload(*, project: str, confirmed: bool = False) -> dict[str, Any]:
    """Map "what is this like?": build a seam from the project's claim + weakest link, then run
    `ztare research isomorphism --seam … --json` (1 model call) to surface a cross-field analogy and
    its forecastable predict-then-falsify. Advisory — a candidate to forecast and test, never a result."""
    project = snapshot.validate_project_slug(str(project or ""))
    claim = recovery_claim_excerpt(snapshot.REPO / "projects" / project / "thesis.md", limit=300)
    graph = research_graph_payload(project)
    weakest = ""
    ins = graph.get("insights") if isinstance(graph, dict) else None
    if isinstance(ins, dict) and isinstance(ins.get("weakest_link"), dict):
        weakest = str(ins["weakest_link"].get("label") or "")
    seam = (claim or weakest).strip()
    if not seam:
        return {"ok": False, "status": "error",
                "error": "No claim to map yet — draft a thesis or run the loop first."}
    model = advisory_model(project)
    cmd = [SERVER_PYTHON, "-m", "src.ztare.cli", "research", "isomorphism",
           "--seam", seam, "--model", model, "--json"]
    if weakest:
        cmd[cmd.index("--seam") + 2:cmd.index("--seam") + 2] = ["--abstract", weakest]
    display = "ztare research isomorphism --seam " + shlex.quote(seam[:70]) + f" --model {model} --json"
    if not confirmed:
        return {"ok": True, "status": "needs_confirmation", "requires_confirmation": True, "writes": False,
                "command": display, "seam": seam,
                "note": ("Asks the model: what established result in another field has this same structure? "
                         "It deanchors from your discipline and returns an analogy plus a sharp prediction "
                         "whose failure would refute the transport. Advisory — a candidate to forecast and test.")}
    proc = run_workbench_command(cmd, timeout=240)
    if proc.returncode != 0:
        return {"ok": False, "status": "error", "command": display,
                "error": tail_display_text(proc.stderr or proc.stdout or "no cross-field analogy surfaced")}
    match = re.search(r"\{.*\}", proc.stdout or "", re.S)
    rx = json.loads(match.group(0)) if match else {}
    if not rx:
        return {"ok": False, "status": "error", "command": display,
                "error": "No cross-field analogy surfaced for this seam."}
    return {"ok": True, "status": "done", "accepted": True, "command": display, "seam": seam, **rx}


def forecast_scratch_payload(*, project: str, question: str, domain: str = "workbench", confirmed: bool = False) -> dict[str, Any]:
    """On-demand forecast: run `ztare forecast scratch-elicit` (elicit a probability → price via the
    sealed pool) and return the contract. confirmed=false → a preview the UI confirms (it calls a model)."""
    question = str(question or "").strip()
    if not question:
        return {"ok": False, "status": "error", "error": "A question is required to forecast."}
    context = workbench_command_context(project, project) if project else {}
    model = context.get("report_model") or "gemini"
    cmd = [SERVER_PYTHON, "-m", "src.ztare.cli", "forecast", "scratch-elicit",
           "--question", question, "--domain", domain or "workbench", "--model", model, "--json"]
    display = "ztare forecast scratch-elicit --question " + shlex.quote(question[:70]) + " --json"
    if not confirmed:
        return {
            "ok": True, "status": "needs_confirmation", "requires_confirmation": True, "writes": True,
            "command": display, "question": question,
            "note": ("Spins up a fresh forecast: the configured model estimates the probability the claim holds, "
                     "then the sealed forecast pool prices it with tail-risk. Writes a scratch forecast record."),
        }
    proc = run_workbench_command(cmd, timeout=300)
    if proc.returncode != 0:
        return {"ok": False, "status": "error", "command": display,
                "error": tail_display_text(proc.stderr or proc.stdout or "forecast failed")}
    match = re.search(r"\{.*\}", proc.stdout or "", re.S)
    parsed = json.loads(match.group(0)) if match else {}
    elicited = parsed.get("elicited") or {}
    return {
        "ok": True, "status": "done", "accepted": True, "command": display,
        "question": question, "domain": domain,
        "p_success": elicited.get("p_success"),
        "rationale": elicited.get("rationale_short"),
        "tail_insurance_premium": elicited.get("tail_insurance_premium"),
        "tail_loss_magnitude": elicited.get("tail_loss_magnitude"),
        "failure_modes": elicited.get("failure_modes") or {},
        "scratch_id": parsed.get("scratch_id"),
        "contract_path": parsed.get("contract_path"),
    }


def build_claim_card_payload(request: dict[str, Any]) -> dict[str, Any]:
    project = snapshot.validate_project_slug(str(request.get("project") or snapshot.DEFAULT_PROJECT))
    rubric = str(request.get("rubric") or project)
    intake = str(request.get("intake") or snapshot.default_intake_for_project(project))
    payload = ztare_cli_payload([
        "card", "build",
        "--project", project,
        "--format", "all",
        "--record",
        "--rubric", rubric,
        "--intake", intake,
        "--repo", str(snapshot.REPO),
    ], project=project, timeout=90)
    if payload.get("ok") is False:
        return payload
    payload.update({
        "served_from": "local_api",
        "command": f"ztare card build --project {project} --format all --record",
        "write_boundary": write_boundary_payload(
            writes_project_files=True,
            write_paths=list(payload.get("write_paths") or []),
            receipt_path=str(payload.get("receipt_path") or ""),
            latest_path=str(payload.get("latest_path") or ""),
            read_only_actions=["preview existing report readiness", "copy card command"],
            no_change_boundary="Previewing report readiness writes no files. Building the claim card writes only the card files and saved claim-card history.",
        ),
    })
    return payload


def local_dev_origin(origin: str | None) -> str:
    if origin and LOCAL_DEV_ORIGIN_RE.match(origin):
        return origin
    return DEFAULT_DEV_ORIGIN


class WorkbenchHandler(BaseHTTPRequestHandler):
    server_version = "ZTAREProjectWorkbench/0.1"

    def log_message(self, format: str, *args: object) -> None:
        return

    def send_json(self, payload: dict[str, Any], status: int = 200, *, include_body: bool = True) -> None:
        code, body = json_bytes(payload, status)
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", local_dev_origin(self.headers.get("Origin")))
        self.send_header("Vary", "Origin")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        try:
            self.end_headers()
            if include_body:
                self.wfile.write(body)
        except BrokenPipeError:
            return

    def send_static_file(self, path: Path, *, include_body: bool = True) -> None:
        if not path.exists() or not path.is_file():
            if path.name == "index.html":
                self.send_json(
                    {
                        "ok": False,
                        "error": "React app is not built. Run `make forensic-workbench-build`, then reload the workbench server.",
                    },
                    status=404,
                    include_body=include_body,
                )
                return
            self.send_json({"ok": False, "error": f"static file not found: {display_path(path)}"}, status=404, include_body=include_body)
            return
        body = WORKBENCH_STORE.read_bytes(path)
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if path.suffix == ".js":
            content_type = "text/javascript"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store" if path.name == "index.html" else "public, max-age=60")
        self.send_header("Content-Length", str(len(body)))
        try:
            self.end_headers()
            if include_body:
                self.wfile.write(body)
        except BrokenPipeError:
            return

    def do_HEAD(self) -> None:
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/status":
                self.send_json(server_status_payload(), include_body=False)
                return
            static_path = static_workbench_path(parsed.path)
            if static_path is not None:
                self.send_static_file(static_path, include_body=False)
                return
            if not parsed.path.startswith("/api/"):
                self.send_static_file(WORKBENCH_DIST / "index.html", include_body=False)
                return
            self.send_json({"ok": False, "error": f"unknown endpoint: {parsed.path}"}, status=404, include_body=False)
        except Exception as exc:  # noqa: BLE001 - local server should return structured failures.
            self.send_json({"ok": False, "error": display_text(exc)}, status=500, include_body=False)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", local_dev_origin(self.headers.get("Origin")))
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Vary", "Origin")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def read_json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            raise ValueError("request body is empty")
        if length > MAX_JSON_BODY_BYTES:
            raise ValueError(f"request body exceeds {MAX_JSON_BODY_BYTES // (1024 * 1024)} MB")
        body = self.rfile.read(length)
        payload = json.loads(body.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("request body must be a JSON object")
        require_visible_project(str(payload.get("project") or ""))
        for path_key in ("path", "intake", "source_path", "preview_path"):
            require_visible_repo_path(payload.get(path_key))
        return payload

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        try:
            request_params = parse_qs(parsed.query)
            require_visible_project(first_param(request_params, "project", ""))
            for path_key in ("path", "intake", "source_path"):
                require_visible_repo_path(first_param(request_params, path_key, ""))
            if parsed.path == "/api/status":
                self.send_json(server_status_payload())
                return
            if parsed.path == "/api/settings":
                self.send_json(settings_payload())
                return
            if parsed.path == "/api/run-config":
                params = parse_qs(parsed.query)
                project = first_param(params, "project", snapshot.DEFAULT_PROJECT)
                self.send_json(run_config_payload(project))
                return
            if parsed.path == "/api/capabilities":
                self.send_json(reasoning_capability_payload())
                return
            if parsed.path == "/api/scenarios":
                self.send_json(scenarios_payload())
                return
            if parsed.path == "/api/plugins":
                self.send_json(plugins_payload())
                return
            if parsed.path == "/api/scenario-agenda":
                self.send_json(scenario_agenda_payload(first_param(parse_qs(parsed.query), "project", "")))
                return
            if parsed.path == "/api/scenario-strength":
                self.send_json(scenario_strength_payload(first_param(parse_qs(parsed.query), "project", "")))
                return
            if parsed.path == "/api/scenario-baseline-status":
                self.send_json(scenario_baseline_status_payload(first_param(parse_qs(parsed.query), "project", "")))
                return
            if parsed.path == "/api/scenario-brief":
                self.send_json(scenario_brief_payload(first_param(parse_qs(parsed.query), "project", "")))
                return
            if parsed.path == "/api/scenario-wagers":
                self.send_json(scenario_wagers_payload(first_param(parse_qs(parsed.query), "project", "")))
                return
            if parsed.path == "/api/scenario-preview":
                self.send_json(scenario_preview_payload(first_param(parse_qs(parsed.query), "name", "")))
                return
            if parsed.path == "/api/scenario-attribution":
                self.send_json(scenario_attribution_payload(first_param(parse_qs(parsed.query), "project", "")))
                return
            if parsed.path == "/api/scenario-provenance":
                self.send_json(scenario_provenance_payload(first_param(parse_qs(parsed.query), "project", "")))
                return
            if parsed.path == "/api/charter-lint":
                self.send_json(charter_lint_payload(first_param(parse_qs(parsed.query), "project", "")))
                return
            if parsed.path == "/api/scenario-map-query":
                params = parse_qs(parsed.query)
                self.send_json(scenario_map_query_payload(first_param(params, "project", ""), first_param(params, "q", "")))
                return
            if parsed.path == "/api/plugin":
                params = parse_qs(parsed.query)
                self.send_json(plugin_detail_payload(
                    first_param(params, "kind", ""), first_param(params, "name", "")))
                return
            if parsed.path == "/api/principles":
                params = parse_qs(parsed.query)
                self.send_json(workbench_principles_payload(first_param(params, "surface", "")))
                return
            if parsed.path == "/api/scoring-guide":
                params = parse_qs(parsed.query)
                project = first_param(params, "project", snapshot.DEFAULT_PROJECT)
                rubric = first_param(params, "rubric", project)
                intake = first_param(params, "intake", snapshot.default_intake_for_project(project))
                self.send_json(scoring_guide_payload_for_project(project=project, rubric=rubric, intake=intake))
                return
            if parsed.path == "/api/projects":
                self.send_json(project_index_payload())
                return
            if parsed.path == "/api/project-recovery-draft":
                params = parse_qs(parsed.query)
                project = first_param(params, "project", "")
                self.send_json(existing_project_recovery_draft(project))
                return
            if parsed.path == "/api/snapshot":
                params = parse_qs(parsed.query)
                project = first_param(params, "project", snapshot.DEFAULT_PROJECT)
                rubric = first_param(params, "rubric", project)
                intake = first_param(params, "intake", snapshot.default_intake_for_project(project))
                renderer = first_param(params, "renderer", snapshot.DEFAULT_RENDERER)
                payload = snapshot_payload_for_project(
                    project=project,
                    rubric=rubric,
                    intake=intake,
                    renderer=renderer,
                )
                self.send_json(payload)
                return
            if parsed.path == "/api/health":
                params = parse_qs(parsed.query)
                project = first_param(params, "project", snapshot.DEFAULT_PROJECT)
                rubric = first_param(params, "rubric", project)
                intake = first_param(params, "intake", snapshot.default_intake_for_project(project))
                payload = health_payload_for_project(project=project, rubric=rubric, intake=intake)
                self.send_json(payload)
                return
            if parsed.path == "/api/run-status":
                params = parse_qs(parsed.query)
                project = first_param(params, "project", snapshot.DEFAULT_PROJECT)
                self.send_json(run_status_payload(project))
                return
            if parsed.path == "/api/score-trajectory":
                params = parse_qs(parsed.query)
                project = first_param(params, "project", snapshot.DEFAULT_PROJECT)
                self.send_json(score_trajectory_payload(project))
                return
            if parsed.path == "/api/eval-results":
                params = parse_qs(parsed.query)
                project = first_param(params, "project", snapshot.DEFAULT_PROJECT)
                facet = first_param(params, "facet", "full")
                self.send_json(eval_results_payload(project, facet))
                return
            if parsed.path == "/api/research-graph":
                params = parse_qs(parsed.query)
                project = first_param(params, "project", snapshot.DEFAULT_PROJECT)
                self.send_json(research_graph_payload(project))
                return
            if parsed.path == "/api/trace":
                params = parse_qs(parsed.query)
                project = first_param(params, "project", snapshot.DEFAULT_PROJECT)
                rubric = first_param(params, "rubric", project)
                intake = first_param(params, "intake", snapshot.default_intake_for_project(project))
                payload = trace_payload_for_project(project=project, rubric=rubric, intake=intake)
                self.send_json(payload)
                return
            if parsed.path == "/api/workflow":
                params = parse_qs(parsed.query)
                project = first_param(params, "project", snapshot.DEFAULT_PROJECT)
                rubric = first_param(params, "rubric", project)
                intake = first_param(params, "intake", snapshot.default_intake_for_project(project))
                renderer = first_param(params, "renderer", snapshot.DEFAULT_RENDERER)
                mode = first_param(params, "mode", "full")
                payload = workflow_payload_for_project(
                    project=project,
                    rubric=rubric,
                    intake=intake,
                    renderer=renderer,
                    mode=mode,
                )
                self.send_json(payload)
                return
            if parsed.path == "/api/research-map":
                params = parse_qs(parsed.query)
                project = first_param(params, "project", snapshot.DEFAULT_PROJECT)
                rubric = first_param(params, "rubric", project)
                intake = first_param(params, "intake", snapshot.default_intake_for_project(project))
                workflow = workflow_payload_for_project(project=project, rubric=rubric, intake=intake, mode="full")
                project_state = workflow.get("project_state") if isinstance(workflow.get("project_state"), dict) else {}
                research_map = project_state.get("research_map") if isinstance(project_state.get("research_map"), dict) else {}
                self.send_json(research_map or {"ok": False, "error": "research map unavailable"}, status=200 if research_map else 404)
                return
            if parsed.path == "/api/report-contract":
                params = parse_qs(parsed.query)
                project = first_param(params, "project", snapshot.DEFAULT_PROJECT)
                rubric = first_param(params, "rubric", project)
                intake = first_param(params, "intake", "")
                renderer = first_param(params, "renderer", snapshot.DEFAULT_RENDERER)
                payload = report_contract_payload_for_project(
                    project=project,
                    rubric=rubric,
                    intake=intake or None,
                    renderer=renderer,
                )
                self.send_json(payload)
                return
            if parsed.path == "/api/file":
                params = parse_qs(parsed.query)
                path = first_param(params, "path", "")
                self.send_json(file_preview_payload(path))
                return
            if parsed.path == "/api/charter":
                params = parse_qs(parsed.query)
                project = first_param(params, "project", snapshot.DEFAULT_PROJECT)
                self.send_json(charter_payload_for_project(project))
                return
            if parsed.path == "/api/intake":
                params = parse_qs(parsed.query)
                project = first_param(params, "project", snapshot.DEFAULT_PROJECT)
                intake = first_param(params, "intake", snapshot.default_intake_for_project(project))
                self.send_json(intake_payload_for_project(project, intake, allow_examples=True))
                return
            if parsed.path == "/api/receipts":
                params = parse_qs(parsed.query)
                project = first_param(params, "project", snapshot.DEFAULT_PROJECT)
                intake = first_param(params, "intake", "")
                limit = int(first_param(params, "limit", "12"))
                self.send_json(receipt_history_payload(project=project, limit=limit, intake=intake or None))
                return
            if parsed.path == "/api/sources":
                params = parse_qs(parsed.query)
                project = first_param(params, "project", snapshot.DEFAULT_PROJECT)
                self.send_json(source_list_payload(project=project))
                return
            if parsed.path == "/api/source-file":
                params = parse_qs(parsed.query)
                project = first_param(params, "project", snapshot.DEFAULT_PROJECT)
                relative_path = first_param(params, "relative", "")
                self.send_json(source_file_payload(project=project, relative_path=relative_path))
                return
            if parsed.path == "/api/run-history":
                params = parse_qs(parsed.query)
                project = first_param(params, "project", snapshot.DEFAULT_PROJECT)
                rubric = first_param(params, "rubric", project)
                intake = first_param(params, "intake", "")
                limit = int(first_param(params, "limit", "8"))
                self.send_json(run_history_payload_for_project(project=project, rubric=rubric, intake=intake or None, limit=limit))
                return
            if parsed.path in {"/api/evidence-support", "/api/claim-support"}:
                params = parse_qs(parsed.query)
                project = first_param(params, "project", snapshot.DEFAULT_PROJECT)
                rubric = first_param(params, "rubric", project)
                intake = first_param(params, "intake", "")
                payload = claim_support_payload_for_project(project=project, rubric=rubric, intake=intake or None)
                payload["endpoint"] = parsed.path
                if parsed.path == "/api/claim-support":
                    payload["compatibility_note"] = "Use /api/evidence-support for new clients; /api/claim-support is kept for existing clients."
                self.send_json(payload)
                return
            if parsed.path == "/api/evidence-gaps":
                params = parse_qs(parsed.query)
                project = first_param(params, "project", snapshot.DEFAULT_PROJECT)
                rubric = first_param(params, "rubric", project)
                intake = first_param(params, "intake", "")
                payload = evidence_gap_list_payload_for_project(project=project, rubric=rubric, intake=intake or None)
                self.send_json(payload)
                return
            if parsed.path == "/api/leanmill":
                self.send_json(leanmill_state_via_cli())
                return
            if parsed.path == "/api/jobs":
                params = parse_qs(parsed.query)
                self.send_json(workbench_jobs_payload(first_param(params, "project", "")))
                return
            if parsed.path == "/api/job":
                params = parse_qs(parsed.query)
                self.send_json(workbench_job_payload(first_param(params, "id", "")))
                return
            if parsed.path == "/api/leanmill/campaigns":
                self.send_json(leanmill_payloads.campaigns_list_payload())
                return
            if parsed.path == "/api/leanmill/campaign":
                params = parse_qs(parsed.query)
                self.send_json(leanmill_payloads.campaign_detail_payload(first_param(params, "dir", "")))
                return
            if parsed.path == "/api/leanmill/blueprints":
                self.send_json(leanmill_payloads.blueprint_list_payload(repo=snapshot.REPO, storage=WORKBENCH_STORE))
                return
            if parsed.path == "/api/leanmill/blueprint-read":
                params = parse_qs(parsed.query)
                request = {"path": first_param(params, "path", "")}
                self.send_json(leanmill_payloads.blueprint_read_payload(request, repo=snapshot.REPO, storage=WORKBENCH_STORE))
                return
            static_path = static_workbench_path(parsed.path)
            if static_path is not None:
                self.send_static_file(static_path)
                return
            if not parsed.path.startswith("/api/"):
                self.send_static_file(WORKBENCH_DIST / "index.html")
                return
            self.send_json({"ok": False, "error": "unknown endpoint"}, status=404)
        except SystemExit as exc:
            self.send_json({"ok": False, "error": display_text(exc)}, status=400)
        except Exception as exc:  # noqa: BLE001 - API should return inspectable JSON errors.
            self.send_json({"ok": False, "error": display_text(exc)}, status=400)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/run-config":
                request = self.read_json_body()
                try:
                    self.send_json(save_run_config_payload(request))
                except ValueError as exc:
                    self.send_json({"ok": False, "error": display_text(exc)}, status=400)
                return
            if parsed.path == "/api/settings":
                request = self.read_json_body()
                self.send_json(save_settings_payload(request.get("values")))
                return
            if parsed.path == "/api/scoring-guide":
                request = self.read_json_body()
                response = save_scoring_guide_payload(
                    project=str(request.get("project") or ""),
                    rubric=str(request.get("rubric") or "") or None,
                    intake=str(request.get("intake") or "") or None,
                    text=request.get("text") or "",
                )
                self.send_json(response, status=200 if response.get("saved") else 400)
                return
            if parsed.path in {"/api/leanmill/target", "/api/leanmill/blueprint"}:
                response = leanmill_payloads.target_request_payload(self.read_json_body(), repo=snapshot.REPO, storage=WORKBENCH_STORE)
                status = 200 if response.get("accepted") or response.get("status") == "needs_confirmation" else 400
                self.send_json(response, status=status)
                return
            if parsed.path == "/api/leanmill/blueprint-save":
                response = leanmill_payloads.blueprint_save_payload(self.read_json_body(), repo=snapshot.REPO, storage=WORKBENCH_STORE)
                self.send_json(response, status=200 if response.get("saved") else 400)
                return
            if parsed.path == "/api/leanmill/blueprint-draft":
                response = leanmill_payloads.blueprint_draft_payload(self.read_json_body(), repo=snapshot.REPO, storage=WORKBENCH_STORE)
                status = 200 if response.get("accepted") or response.get("status") == "needs_confirmation" else 400
                self.send_json(response, status=status)
                return
            if parsed.path == "/api/leanmill/scaffold":
                try:
                    response = leanmill_payloads.scaffold_payload(self.read_json_body(), repo=snapshot.REPO, storage=WORKBENCH_STORE)
                    status = 200 if response.get("accepted") or response.get("status") == "needs_confirmation" else 400
                except (ValueError, FileNotFoundError) as exc:
                    response = {"ok": False, "accepted": False, "error": display_text(exc)}
                    status = 400
                self.send_json(response, status=status)
                return
            if parsed.path == "/api/leanmill/autoformalize-notes":
                response = leanmill_payloads.autoformalize_payload(self.read_json_body(), repo=snapshot.REPO, storage=WORKBENCH_STORE)
                status = 200 if response.get("accepted") or response.get("status") == "needs_confirmation" else 400
                self.send_json(response, status=status)
                return
            if parsed.path == "/api/leanmill/solve-adhoc":
                response = leanmill_payloads.solve_adhoc_payload(self.read_json_body(), repo=snapshot.REPO, storage=WORKBENCH_STORE)
                status = 200 if response.get("accepted") or response.get("status") == "needs_confirmation" else 400
                self.send_json(response, status=status)
                return
            if parsed.path == "/api/leanmill/ratify":
                try:
                    response = leanmill_payloads.ratify_payload(self.read_json_body(), repo=snapshot.REPO, storage=WORKBENCH_STORE)
                    status = 200 if response.get("accepted") or response.get("status") == "needs_confirmation" else 400
                except (ValueError, FileNotFoundError) as exc:
                    response = {"ok": False, "accepted": False, "error": display_text(exc)}
                    status = 400
                self.send_json(response, status=status)
                return
            if parsed.path == "/api/leanmill/campaign-preflight":
                response = leanmill_payloads.campaign_preflight_payload(self.read_json_body(), repo=snapshot.REPO, storage=WORKBENCH_STORE)
                self.send_json(response, status=200 if response.get("ok") else 400)
                return
            if parsed.path == "/api/leanmill/campaign-run":
                response = leanmill_payloads.campaign_run_payload(self.read_json_body(), repo=snapshot.REPO, storage=WORKBENCH_STORE)
                status = 200 if response.get("accepted") or response.get("status") == "needs_confirmation" else 400
                self.send_json(response, status=status)
                return
            if parsed.path == "/api/leanmill/campaign-verify":
                self.send_json(leanmill_payloads.campaign_verify_payload(self.read_json_body()))
                return
            if parsed.path == "/api/leanmill/campaign-replay":
                self.send_json(leanmill_payloads.campaign_replay_payload(self.read_json_body()))
                return
            if parsed.path == "/api/leanmill/campaign-stop":
                self.send_json(leanmill_payloads.campaign_stop_payload(self.read_json_body()))
                return
            if parsed.path == "/api/leanmill/campaign-retire":
                self.send_json(leanmill_payloads.campaign_retire_payload(self.read_json_body()))
                return
            if parsed.path == "/api/leanmill/campaign-resume":
                self.send_json(leanmill_payloads.campaign_resume_payload(self.read_json_body()))
                return
            if parsed.path == "/api/leanmill/campaign-recover":
                self.send_json(leanmill_payloads.campaign_recover_payload(self.read_json_body()))
                return
            if parsed.path == "/api/leanmill/campaign-recheck":
                self.send_json(leanmill_payloads.campaign_recheck_payload(self.read_json_body()))
                return
            if parsed.path == "/api/leanmill/campaign-interpret":
                self.send_json(leanmill_payloads.campaign_interpret_payload(self.read_json_body()))
                return
            if parsed.path == "/api/review":
                self.send_json(review_payload_from_request(self.read_json_body()))
                return
            if parsed.path == "/api/intake":
                request = self.read_json_body()
                project = str(request.get("project") or "")
                rubric = str(request.get("rubric") or "") or None
                intake = str(request.get("intake") or "") or None
                edit_result = apply_intake_edit(
                    project=project,
                    intake=intake,
                    raw_patch=request.get("fields"),
                    rubric=rubric,
                )
                response = {
                    "ok": True,
                    "edit": edit_result,
                    "intake": edit_result.get("intake"),
                    "write_boundary": edit_result.get("write_boundary"),
                    "snapshot": None,
                }
                try:
                    response["snapshot"] = snapshot_payload_for_project(project=project, rubric=rubric, intake=intake)
                except SystemExit as exc:
                    response["snapshot_error"] = display_text(exc)
                except Exception as exc:  # noqa: BLE001 - intake write already succeeded.
                    response["snapshot_error"] = display_text(exc)
                self.send_json(response)
                return
            if parsed.path == "/api/charter":
                request = self.read_json_body()
                project = str(request.get("project") or "")
                rubric = str(request.get("rubric") or "") or None
                intake = str(request.get("intake") or "") or None
                edit_result = apply_charter_edit(
                    project=project,
                    rubric=rubric,
                    intake=intake,
                    text=str(request.get("text") or ""),
                )
                response = {
                    "ok": True,
                    "edit": edit_result,
                    "charter": edit_result.get("charter"),
                    "write_boundary": edit_result.get("write_boundary"),
                    "snapshot": None,
                }
                try:
                    response["snapshot"] = snapshot_payload_for_project(project=project, rubric=rubric, intake=intake)
                except SystemExit as exc:
                    response["snapshot_error"] = display_text(exc)
                except Exception as exc:  # noqa: BLE001 - charter write already succeeded.
                    response["snapshot_error"] = display_text(exc)
                self.send_json(response)
                return
            if parsed.path in {"/api/next-step", "/api/item-action", "/api/row-action"}:
                response = item_action_payload_from_request(self.read_json_body())
                response["endpoint"] = parsed.path
                if parsed.path in {"/api/item-action", "/api/row-action"}:
                    response["compatibility_note"] = "Use /api/next-step for new clients; this route is kept for existing saved-history clients."
                self.send_json(response)
                return
            if parsed.path == "/api/preflight":
                request = self.read_json_body()
                project = str(request.get("project") or "")
                rubric = str(request.get("rubric") or "") or None
                intake = str(request.get("intake") or "") or None
                renderer = str(request.get("renderer") or "") or None
                response = preflight_payload_for_project(
                    project=project,
                    rubric=rubric,
                    intake=intake,
                    renderer=renderer,
                )
                self.send_json(response, status=200 if response.get("returncode") == 0 else 400)
                return
            if parsed.path == "/api/project-test":
                request = self.read_json_body()
                project = str(request.get("project") or "")
                rubric = str(request.get("rubric") or "") or None
                intake = str(request.get("intake") or "") or None
                renderer = str(request.get("renderer") or "") or None
                action_id = str(request.get("action_id") or "") or None
                action_label = str(request.get("action_label") or "") or None
                response = project_test_payload_for_project(
                    project=project,
                    rubric=rubric,
                    intake=intake,
                    renderer=renderer,
                    action_id=action_id,
                    action_label=action_label,
                )
                self.send_json(response, status=200 if response.get("returncode") == 0 else 400)
                return
            if parsed.path == "/api/scenario-surface":
                request = self.read_json_body()
                self.send_json(scenario_surface_payload(str(request.get("project") or "")))
                return
            if parsed.path == "/api/scenario-reingest":
                request = self.read_json_body()
                self.send_json(scenario_reingest_payload(
                    str(request.get("project") or ""), str(request.get("doc") or "")))
                return
            if parsed.path == "/api/scenario-reingest-promote":
                request = self.read_json_body()
                response = scenario_reingest_promote_payload(
                    str(request.get("project") or ""), str(request.get("doc") or ""),
                    str(request.get("base_hash") or ""), str(request.get("source_path") or ""))
                self.send_json(response, status=200 if response.get("ok") else 409 if response.get("stale") else 400)
                return
            if parsed.path == "/api/scenario-annotate":
                request = self.read_json_body()
                self.send_json(scenario_annotate_payload(
                    str(request.get("project") or ""), str(request.get("doc") or ""),
                    str(request.get("model") or "")))
                return
            if parsed.path == "/api/plugin-install":
                request = self.read_json_body()
                response = install_plugin_payload(
                    str(request.get("kind") or ""), str(request.get("name") or ""),
                    request.get("spec") if isinstance(request.get("spec"), dict) else {},
                    overwrite=bool(request.get("overwrite", False)),
                )
                self.send_json(response, status=200 if response.get("ok") else 400)
                return
            if parsed.path == "/api/plugins-reload":
                self.send_json(plugins_reload_payload())
                return
            if parsed.path == "/api/scenario-baseline":
                request = self.read_json_body()
                self.send_json(scenario_baseline_payload(str(request.get("project") or "")))
                return
            if parsed.path == "/api/scenario-wager-register":
                request = self.read_json_body()
                response = scenario_wager_register_payload(
                    str(request.get("project") or ""),
                    request.get("wager") if isinstance(request.get("wager"), dict) else {})
                self.send_json(response, status=200 if response.get("ok") else 400)
                return
            if parsed.path == "/api/scenario-wager-expire":
                request = self.read_json_body()
                self.send_json(scenario_wager_expire_payload(
                    str(request.get("project") or ""), str(request.get("now") or "")))
                return
            if parsed.path == "/api/scenario-wager-execute":
                response = scenario_wager_execute_payload(self.read_json_body())
                self.send_json(response, status=200 if response.get("ok") else 400)
                return
            if parsed.path == "/api/scenario-recompile":
                request = self.read_json_body()
                self.send_json(scenario_recompile_payload(str(request.get("project") or "")))
                return
            if parsed.path == "/api/scenario-recheck":
                request = self.read_json_body()
                hl = request.get("half_life_days")
                self.send_json(scenario_recheck_payload(
                    str(request.get("project") or ""), str(request.get("now") or ""),
                    int(hl) if isinstance(hl, (int, str)) and str(hl).lstrip("-").isdigit() else None))
                return
            if parsed.path == "/api/scenario-rice":
                self.send_json(scenario_rice_payload(self.read_json_body()))
                return
            if parsed.path == "/api/scenario-rice-inputs":
                response = scenario_rice_update_payload(self.read_json_body())
                self.send_json(response, status=200 if response.get("ok") else 400)
                return
            if parsed.path == "/api/scenario-bind":
                self.send_json(scenario_bind_payload(self.read_json_body()))
                return
            if parsed.path == "/api/scenario-next-agenda":
                self.send_json(scenario_next_agenda_payload(str(self.read_json_body().get("project") or "")))
                return
            if parsed.path == "/api/scenario-deliverables":
                req = self.read_json_body()
                self.send_json(scenario_deliverables_payload(str(req.get("project") or ""), req.get("declared"),
                                                             str(req.get("scenario") or "")))
                return
            if parsed.path == "/api/scenario-deliverable-add":
                req = self.read_json_body()
                self.send_json(scenario_deliverable_add_payload(str(req.get("project") or ""), str(req.get("name") or ""),
                                                                str(req.get("scenario") or "")))
                return
            if parsed.path == "/api/scenario-deliverable-generate":
                req = self.read_json_body()
                self.send_json(scenario_deliverable_generate_payload(str(req.get("project") or ""), str(req.get("name") or ""),
                                                                      str(req.get("scenario") or "")))
                return
            if parsed.path == "/api/scenario-deliverable-editorial":
                req = self.read_json_body()
                response = scenario_deliverable_editorial_payload(
                    str(req.get("project") or ""), str(req.get("name") or ""), str(req.get("scenario") or ""))
                self.send_json(response, status=200 if response.get("ok") else 400)
                return
            if parsed.path == "/api/scenario-produce-all":
                req = self.read_json_body()
                self.send_json(scenario_produce_all_payload(str(req.get("project") or ""), str(req.get("scenario") or "")))
                return
            if parsed.path == "/api/run":
                request = self.read_json_body()
                project = str(request.get("project") or "")
                rubric = str(request.get("rubric") or "") or None
                intake = str(request.get("intake") or "") or None
                renderer = str(request.get("renderer") or "") or None
                scenario = str(request.get("scenario") or "") or None
                confirmed = request.get("confirmed") is True
                response = (bounded_run_job_payload(
                    project=project, rubric=rubric, intake=intake, renderer=renderer, scenario=scenario,
                ) if confirmed and request.get("background") is True else bounded_run_payload_for_project(
                    project=project, rubric=rubric, intake=intake, renderer=renderer,
                    scenario=scenario, confirmed=confirmed,
                ))
                status = 200 if (not confirmed or response.get("accepted")) else 400
                self.send_json(response, status=status)
                return
            if parsed.path == "/api/job-cancel":
                request = self.read_json_body()
                response = workbench_job_cancel_payload(str(request.get("id") or ""))
                self.send_json(response, status=200 if response.get("ok") else 400)
                return
            if parsed.path == "/api/source-action":
                request = self.read_json_body()
                project = str(request.get("project") or "")
                rubric = str(request.get("rubric") or "") or None
                intake = str(request.get("intake") or "") or None
                renderer = str(request.get("renderer") or "") or None
                action = str(request.get("action") or "")
                response = source_action_payload_for_project(
                    project=project,
                    action=action,
                    rubric=rubric,
                    intake=intake,
                    renderer=renderer,
                    confirmed=request.get("confirmed") is True,
                )
                self.send_json(response)
                return
            if parsed.path == "/api/report-contract":
                request = self.read_json_body()
                response = report_contract_refresh_payload_for_project(
                    project=str(request.get("project") or ""),
                    rubric=str(request.get("rubric") or "") or None,
                    intake=str(request.get("intake") or "") or None,
                    renderer=str(request.get("renderer") or "") or None,
                    confirmed=request.get("confirmed") is True,
                )
                status = 200 if response.get("accepted") or response.get("status") == "needs_confirmation" else 400
                self.send_json(response, status=status)
                return
            if parsed.path == "/api/report-synthesis":
                request = self.read_json_body()
                response = report_synthesis_payload_for_project(
                    project=str(request.get("project") or ""),
                    rubric=str(request.get("rubric") or "") or None,
                    intake=str(request.get("intake") or "") or None,
                    renderer=str(request.get("renderer") or "") or None,
                    confirmed=request.get("confirmed") is True,
                    instructions=str(request.get("instructions") or ""),
                )
                status = 200 if response.get("accepted") or response.get("status") == "needs_confirmation" else 400
                self.send_json(response, status=status)
                return
            if parsed.path == "/api/claim-card":
                response = build_claim_card_payload(self.read_json_body())
                self.send_json(response, status=200 if response.get("accepted") else 400)
                return
            if parsed.path == "/api/eigenquestion":
                request = self.read_json_body()
                response = eigenquestion_payload(
                    project=str(request.get("project") or ""),
                    confirmed=request.get("confirmed") is True,
                )
                self.send_json(response, status=200 if response.get("ok") else 400)
                return
            if parsed.path == "/api/project-draft":
                request = self.read_json_body()
                response = project_draft_payload(
                    text=str(request.get("text") or request.get("document") or ""),
                    confirmed=request.get("confirmed") is True,
                )
                self.send_json(response, status=200 if response.get("ok") else 400)
                return
            if parsed.path == "/api/document-extract":
                response = document_extract_payload(self.read_json_body())
                self.send_json(response, status=200 if response.get("ok") else 400)
                return
            if parsed.path == "/api/falsify-claim":
                request = self.read_json_body()
                response = falsify_claim_payload(
                    project=str(request.get("project") or ""),
                    claim=str(request.get("claim") or ""),
                    confirmed=request.get("confirmed") is True,
                )
                self.send_json(response, status=200 if response.get("ok") else 400)
                return
            if parsed.path == "/api/rubric-review":
                request = self.read_json_body()
                response = rubric_review_payload(
                    project=str(request.get("project") or ""),
                    rubric=str(request.get("rubric") or "") or None,
                    confirmed=request.get("confirmed") is True,
                )
                self.send_json(response, status=200 if response.get("ok") else 400)
                return
            if parsed.path == "/api/isomorphism":
                request = self.read_json_body()
                response = isomorphism_payload(
                    project=str(request.get("project") or ""),
                    confirmed=request.get("confirmed") is True,
                )
                self.send_json(response, status=200 if response.get("ok") else 400)
                return
            if parsed.path == "/api/export-obsidian":
                request = self.read_json_body()
                response = export_obsidian_payload(str(request.get("project") or ""))
                self.send_json(response, status=200 if response.get("ok") else 400)
                return
            if parsed.path == "/api/forecast-scratch":
                request = self.read_json_body()
                response = forecast_scratch_payload(
                    project=str(request.get("project") or ""),
                    question=str(request.get("question") or ""),
                    domain=str(request.get("domain") or "workbench"),
                    confirmed=request.get("confirmed") is True,
                )
                self.send_json(response, status=200 if response.get("ok") else 400)
                return
            if parsed.path == "/api/research-map":
                response = save_research_map_payload(self.read_json_body())
                self.send_json(response, status=200 if response.get("accepted") else 400)
                return
            if parsed.path == "/api/evidence-fetch":
                request = self.read_json_body()
                confirmed = request.get("confirmed") is True
                handler = evidence_fetch_job_payload if confirmed else evidence_fetch_payload_for_project
                response = handler(
                    project=str(request.get("project") or ""),
                    rubric=str(request.get("rubric") or "") or None,
                    intake=str(request.get("intake") or "") or None,
                    renderer=str(request.get("renderer") or "") or None,
                    target=str(request.get("target") or ""),
                    **({"confirmed": False} if not confirmed else {}),
                )
                status = 200 if response.get("ok") or response.get("status") == "needs_confirmation" else 400
                self.send_json(response, status=status)
                return
            if parsed.path == "/api/evidence-gap-justify":
                request = self.read_json_body()
                selector = request.get("selector") if isinstance(request.get("selector"), dict) else {}
                response = evidence_gap_justify_payload_for_project(
                    project=str(request.get("project") or ""),
                    rubric=str(request.get("rubric") or "") or None,
                    intake=str(request.get("intake") or "") or None,
                    selector=selector,
                    reason=str(request.get("reason") or ""),
                    status=str(request.get("status") or "justified"),
                    evidence_refs=request.get("evidence_refs") if isinstance(request.get("evidence_refs"), list) else [],
                )
                self.send_json(response, status=200 if response.get("accepted") else 400)
                return
            if parsed.path == "/api/project-create":
                request = self.read_json_body()
                response = create_project_payload(
                    project=str(request.get("project") or ""),
                    rubric=str(request.get("rubric") or "") or None,
                    task=str(request.get("task") or ""),
                    bounded_claim=str(request.get("bounded_claim") or ""),
                    next_falsifier=str(request.get("next_falsifier") or ""),
                    notes=str(request.get("notes") or ""),
                    source_refs=request.get("source_refs"),
                    evidence_refs=request.get("evidence_refs"),
                    non_claims=request.get("non_claims"),
                    uploaded_sources=request.get("uploaded_sources"),
                    renderer=str(request.get("renderer") or "") or None,
                )
                self.send_json(response)
                return
            if parsed.path == "/api/source-import":
                request = self.read_json_body()
                response = import_source_payload(
                    project=str(request.get("project") or ""),
                    rubric=str(request.get("rubric") or "") or None,
                    intake=str(request.get("intake") or "") or None,
                    renderer=str(request.get("renderer") or "") or None,
                    filename=str(request.get("filename") or ""),
                    source_type=str(request.get("source_type") or ""),
                    artifact_kind=str(request.get("artifact_kind") or "project_note"),
                    created_by=str(request.get("created_by") or ""),
                    body=str(request.get("body") or ""),
                )
                self.send_json(response, status=200 if response.get("ok") else 400)
                return
            if parsed.path == "/api/source-edit":
                request = self.read_json_body()
                response = edit_source_payload(
                    project=str(request.get("project") or ""),
                    rubric=str(request.get("rubric") or "") or None,
                    intake=str(request.get("intake") or "") or None,
                    renderer=str(request.get("renderer") or "") or None,
                    relative_path=str(request.get("relative_raw_path") or request.get("relative") or ""),
                    source_type=str(request.get("source_type") or ""),
                    artifact_kind=str(request.get("artifact_kind") or "") or None,
                    created_by=str(request.get("created_by")) if "created_by" in request else None,
                    body=str(request.get("body") or ""),
                )
                self.send_json(response, status=200 if response.get("ok") else 400)
                return
            if parsed.path in {"/api/project-file", "/api/case-file"}:
                request = self.read_json_body()
                response = save_case_file_payload(
                    project=str(request.get("project") or ""),
                    rubric=str(request.get("rubric") or "") or None,
                    intake=str(request.get("intake") or "") or None,
                    case_file=request.get("project_file") or request.get("case_file"),
                )
                response["endpoint"] = parsed.path
                if parsed.path == "/api/case-file":
                    response["compatibility_note"] = "Use /api/project-file for new clients; /api/case-file is kept for existing saved-history clients."
                self.send_json(response)
                return
            self.send_json({"ok": False, "error": "unknown endpoint"}, status=404)
        except SystemExit as exc:
            self.send_json(post_error_payload(parsed.path, exc), status=400)
        except Exception as exc:  # noqa: BLE001 - API should return inspectable JSON errors.
            self.send_json(post_error_payload(parsed.path, exc), status=400)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument(
        "--project-scope",
        choices=("local", "public", "allowlist"),
        default=PROJECT_SCOPE if PROJECT_SCOPE in {"local", "public", "allowlist"} else "local",
        help="Project inventory boundary. 'public' uses forensic-workbench/public-projects.json.",
    )
    parser.add_argument(
        "--projects",
        default=",".join(sorted(PROJECT_ALLOWLIST)),
        help="Comma-separated project allowlist; required with --project-scope allowlist.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    global PROJECT_SCOPE, PROJECT_ALLOWLIST
    args = build_parser().parse_args(argv)
    PROJECT_SCOPE = args.project_scope
    PROJECT_ALLOWLIST = {item.strip() for item in str(args.projects or "").split(",") if item.strip()}
    if PROJECT_SCOPE == "allowlist" and not PROJECT_ALLOWLIST:
        raise SystemExit("--project-scope allowlist requires --projects <slug,...>")
    server = ThreadingHTTPServer((args.host, args.port), WorkbenchHandler)
    print(f"Project Workbench server listening on http://{args.host}:{args.port} (projects: {PROJECT_SCOPE})", flush=True)
    if not (WORKBENCH_DIST / "index.html").exists():
        print("  React app not built yet. Run `make forensic-workbench-build` to serve the UI from this server.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
