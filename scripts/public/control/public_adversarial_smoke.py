#!/usr/bin/env python3
"""Adversarial smoke checks for the public ZTARE runtime.

The normal smoke target proves that the core scripts can run. This check tries
to catch the ways a smoke can become misleading: leaked runtime artifacts,
accidental dependence on private stores, missing Makefile wiring, and stale
public docs.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib
from pathlib import Path
from typing import Iterable


REPO = Path(__file__).resolve().parents[3]
PYTHON = os.environ.get("PYTHON", sys.executable)
TEST_PREFIX = "test_runtime_smoke"

RUNTIME_ARTIFACT_DIRS = [
    REPO / "org/tasks/active",
    REPO / "ztare_workspace/gates/pending",
    REPO / "ztare_workspace/gates/resolved",
]

REQUIRED_MAKE_SNIPPETS = [
    "First-run path:",
    "smoke-public:",
    "scripts/public/control/runtime_smoke_test.py",
    "scripts/public/control/forecast/pool.py smoke",
    "scripts/public/control/action_intelligence.py smoke",
    "public-adversarial-smoke:",
    "scripts/public/control/public_adversarial_smoke.py",
    "first-run:",
    "$(MAKE) hello",
    "$(MAKE) gaming-catalog-audit",
    "$(MAKE) benchmark-evidence",
    "$(MAKE) reasoning-compiler-capability-audit",
    "$(MAKE) evaluator-hardening-frozen-check",
    "$(MAKE) scope-boundary-audit",
    "$(MAKE) public-terminology-audit",
    "$(MAKE) smoke-public",
    "$(MAKE) public-adversarial-smoke",
    "$(MAKE) docs-check",
    "benchmark-evidence:",
    "scripts/public/control/benchmark_evidence_check.py",
    "scripts/public/control/gaming_catalog_audit.py",
    "benchmark-ordinary-review-freeze-check:",
    "scripts/public/control/ordinary_review_freeze_check.py",
    "gaming-catalog-audit:",
    "reasoning-compiler-capability-audit:",
    "scripts/public/control/reasoning_compiler_capability_audit.py",
    "demo:",
    "scripts/public/control/golden_path_demo.py",
    "demo-claim-discipline:",
    "scripts/public/control/claim_discipline_demo.py",
    "smoke-docker:",
    "bash scripts/public/control/docker_smoke.sh",
    "gates:",
    "scripts/private/test_publish_safety.py",
    "scripts/private/validate_seam_spec_format.py",
    "scripts/public/validators/validate_markdown_links.py",
    "scripts/public/control/gaming_catalog_audit.py",
    "research-move-routing-drift-audit:",
    "hello:",
    "scripts/public/control/hello_value_demo.py",
    "source-check:",
    "ztare.scaffold.source_check",
    "$(MAKE) source-check PROJECT=$(PROJECT)",
    "source-check + workspace-update + evidence-compile",
    "evaluator-hardening-frozen-check:",
    "scripts/public/control/evaluator_hardening_frozen_check.py",
    "scope-boundary-audit:",
    "scripts/public/control/scope_boundary_audit.py",
    "public-terminology-audit:",
    "scripts/public/control/public_terminology_audit.py",
    "query-graph:",
    "scripts/public/control/query_graph.py",
    "move-card-atlas-build:",
    "scripts/public/control/primitive_operator_cards.py --build-atlas",
    "compile-src:",
    "$(PYTHON) -m compileall -q src/ztare",
    "gates: compile-src flakes flakes-leanmill",
    "scripts/public/control/undefined_name_gate.py",
    "forensic-workbench-snapshot:",
    "forensic-workbench-data:",
    "forensic-workbench-state:",
    "forensic-workbench-build:",
    "forensic-workbench-dev:",
    "forensic-workbench-api:",
    "forensic-workbench-live:",
    "scripts/public/control/forensic_workbench_snapshot.py",
    "scripts/public/control/forensic_workbench_state.py",
    "scripts/public/control/forensic_workbench_server.py",
    "scripts/public/control/forensic_workbench_live.py",
]

FORBIDDEN_MAKEFILE_SNIPPETS = [
    "/tmp/",
]

REQUIRED_DOCKER_SMOKE_SNIPPETS = [
    "docker build",
    "docker run --rm",
    "make smoke-public PYTHON=python",
]

REQUIRED_USER_DOC_SNIPPETS = [
    "make first-run",
    "make hello",
    "make demo",
    "make smoke-public",
]

REQUIRED_REFERENCE_DOC_SNIPPETS = [
    "## Public first-run path",
    "make first-run",
    "make hello",
    "make demo",
    "make smoke-public",
    "make public-adversarial-smoke",
    "make smoke-docker",
    "make compile-src",
    "make benchmark-evidence",
    "make gaming-catalog-audit",
    "make evaluator-hardening-frozen-check",
    "make benchmark-ordinary-review-freeze-check",
    "make scope-boundary-audit",
    "make public-terminology-audit",
    "make benchmark-ordinary-review",
    "make move-card-atlas-build",
    "make forensic-workbench-snapshot",
    "make forensic-workbench-data",
    "make forensic-workbench-state",
    "make forensic-workbench-build",
    "make forensic-workbench-dev",
    "make forensic-workbench-api",
    "make forensic-workbench-live",
    "make gates",
]

REQUIRED_QUICKSTART_SNIPPETS = [
    "ztare project intake create --path <project>_intake.json",
    "ztare autoresearch trace --project <project> --rubric <rubric> --intake <project>_intake.json --json",
    "Run plan_preview.recommended_first_command.",
    "ztare autoresearch run --project <project> --rubric <rubric>",
    "--intake <project>_intake.json --preflight-only",
    "--intake <project>_intake.json --iters 10",
]

REQUIRED_FORENSIC_WORKBENCH_SNIPPETS = [
    "# Project Workbench Interface",
    "project -> working diagnosis -> source and evidence files",
    "open `demo_claims` or `ops_root_cause_diagnosis_demo`",
    "see the working diagnosis and ruled-out alternatives",
    "project and scoring-guide identity",
    "Every visible check must carry one of:",
    "`ztare project intake validate --path <intake.json> --json`",
    "`ztare project intake falsify --path <intake.json> ...`",
    "`ztare project source-check --project <project> --json`",
    "`ztare project source-index --project <project> --json`",
    "`ztare project evidence-replay --project <project> --json`",
    "`ztare project claim-support --project <project> --json` (compatibility CLI)",
    "`ztare autoresearch trace --project <project> --rubric <rubric> --intake <intake.json> --json`",
    "`ztare autoresearch run ... --preflight-only`",
    "`ztare autoresearch run ... --iters <n>`",
    "`ztare forensic-workbench report-action --project <project> --action check_readiness --renderer <renderer> --confirmed --json`",
    "`ztare forensic-workbench apply-review --project <project> --project-check <project_check_slug> --from <review.json>`",
    "`make forensic-workbench-data WORKBENCH_PROJECT=<project>`",
    "`make forensic-workbench-state WORKBENCH_PROJECT=<project>`",
    "GET /api/status",
    "GET /api/principles",
    "GET /api/projects",
    "project_inventory_scope: all_projects_directory",
    "inventory_includes_all_project_folders: true",
    "`all_project_folders`",
    "`project_folders` is a compact compatibility list",
    "GET /api/workflow",
    "POST /api/project-create",
    "POST /api/source-import",
    "GET /api/sources?project=<project>",
    "GET /api/source-file?project=<project>&relative=<relative_raw_path>",
    "POST /api/source-edit",
    "GET /api/snapshot?project=<project>&rubric=<rubric>&intake=<intake>",
    "GET /api/health?project=<project>&rubric=<rubric>&intake=<intake>",
    "GET /api/trace?project=<project>&rubric=<rubric>&intake=<intake>",
    "POST /api/preflight",
    "POST /api/run",
    "POST /api/source-action",
    "GET /api/report-contract?project=<project>&renderer=<renderer>",
    "GET /api/evidence-support?project=<project>",
    "GET /api/leanmill",
    "POST /api/leanmill/target",
    "POST /api/leanmill/blueprint",
    "GET /api/file?path=<repo-relative-path>",
    "GET /api/receipts?project=<project>",
    "GET /api/run-history?project=<project>",
    "POST /api/project-file",
    "POST /api/case-file",
    "POST /api/review",
    "POST /api/next-step",
    "POST /api/item-action",
    "POST /api/row-action",
    "Review and next-step POST bodies should send `project_check_slug`",
    "`project_check_label`",
    "`project_check_slug`",
    "Snapshot responses and browser project files should expose `project_checks` and",
    "Saved history should expose `next_step` and",
    "An incomplete intake disables launch and names the missing evidence.",
    "Source-ready, evidence-ready, and loop-ready are visually distinct.",
    "A stale or unsupported report stays in needs-support state when the support",
    "The offline snapshot and `workbench_snapshot.json` use product-facing",
    "display `Project key`",
    "latest saved review",
    "latest next step",
    "Supervisor, multi-role, multi-user, hosted, billing, and background-agent",
]

REQUIRED_FORENSIC_WORKBENCH_CLI_FAMILIES = [
    ("project", "intake", "--help"),
    ("project", "source-check", "--help"),
    ("project", "source-index", "--help"),
    ("project", "evidence-replay", "--help"),
    ("project", "claim-support", "--help"),
    ("autoresearch", "run", "--help"),
]

REQUIRED_FORENSIC_WORKBENCH_SNAPSHOT_SNIPPETS = [
    "Project Workbench",
    "Project path",
    "data-provenance=",
    "Project",
    "Working diagnosis",
    "Ruled-out alternatives",
    "Source files",
    "Evidence files",
    "Run check",
    "Readiness check",
    "readiness history path",
    "Report readiness",
    "Latest review",
    "Latest next step",
    "Report readiness is current.",
    "report readiness history",
]

REQUIRED_FORENSIC_WORKBENCH_REACT_SNIPPETS = [
    '"name": "ztare-forensic-workbench"',
    '"dev": "vite"',
    '"build": "vite build"',
    'fetch("/api/projects"',
    'fetch("/api/project-create"',
    'fetch("/api/source-import"',
    'fetch("/api/source-edit"',
    'endpointUrl("/api/sources"',
    'endpointUrl("/api/source-file"',
    'endpointUrl("/api/snapshot"',
    'endpointUrl("/api/health"',
    'endpointUrl("/api/trace"',
    'endpointUrl("/api/report-contract"',
    'endpointUrl("/api/file"',
    'endpointUrl("/api/intake"',
    'endpointUrl("/api/receipts"',
    'fetch("/api/principles"',
    'fetch("/api/leanmill"',
    'fetch("/api/leanmill/target"',
    "what LeanMill tried",
    'fetch("/api/project-file"',
    "loaded_reference_status",
    "reference_status",
    "intake_ref_summary",
    "Project-local briefs only",
    "project-switchboard",
    "Open project",
    "No changed project-brief fields to write.",
    "intakeChangedFields",
    "preview_path",
    "Run history",
    "File and evidence warnings",
    "Project setup",
    "project-identity",
    "Add intake",
    "add_intake_write_boundary",
    "Existing files to review",
    "Diagnosis",
    "write-boundary",
    "side-subnav",
    "side-subnav-list",
    "mobile-project-picker",
    "All projects",
    "Open project",
    "Report",
    "issues",
    "Next step",
    "Evidence summary",
    "Preview, copy, and download do not write project files.",
    "Evidence summary",
    "Source files",
    "TraceConsolePanel",
    "Suggested next moves",
    "Proof path",
    "Copy path",
    "Boundary:",
    "Project Workbench",
    "report-contract-panel",
    "ztare-forensic-workbench-report-contract-v1",
    "Saved history",
    "history-row",
    "Project file",
    "Save to project folder",
    "Download project file",
    "Latest saved project",
    "Saved history",
    "saved-history path",
    "ztare-forensic-workbench-project-file-v1",
    "ztare-forensic-workbench-project-file-write-receipt-v1",
    "ztare-forensic-workbench-project-create-v1",
    "source-import-panel",
    "raw-source-editor",
    "ztare-forensic-workbench-source-action-receipt-v1",
    "project_context",
    "Evidence summary",
    "intake_editable",
    "/api/source-import",
    "/api/source-edit",
    "live_context",
    "audit_commands",
    "command_queue",
    "display_label",
    "project_check_label",
    "project_check_count",
    "project_checks",
    "latest_project_check",
    "readiness_checks",
    "graph_summaries",
    "preflight_receipt",
    "preflight_result",
    "project_file_write_plan",
    "live_context.project_state",
    "project_to_thesis_audit",
    "ztare forensic-workbench project-state",
    "source_count",
    "relative_raw_path",
    "latest_source_action",
    "latest_case_file_write",
    "latest_source_import",
    "latest_source_edit",
    "source_edit",
    "latest_source_action",
    "Latest project file",
    "Live project state",
    "Refresh from local project files",
    "Saved project summary",
    "Recent saved changes",
    "run_history",
    "Loaded project context",
    '"/workbench_snapshot.json"',
    "Project Workbench",
    "ZTARE",
    "Open a project, connect a folder, or create a new project",
    "Project path",
    "projectWorkflowSteps",
    "Open a connected project",
    "Project library",
    "visible of",
    "Latest saved review",
    "make forensic-workbench-api",
    "make forensic-workbench-live",
    "save-flow-head",
    "save-flow-choices",
    "Edit project brief",
    "Save project brief",
    "source files",
    "evidence files",
    "Latest intake edit",
    "/api/projects",
    "/api/project-create",
    "/api/source-import",
    "/api/sources",
    "/api/source-file",
    "/api/source-edit",
    "/api/snapshot",
    "/api/health",
    "/api/trace",
    "/api/preflight",
    "/api/run",
    "/api/source-action",
    "/api/claim-support",
    "/api/report-contract",
    "/api/file",
    "/api/intake",
    "/api/receipts",
    "/api/run-history",
    "/api/case-file",
    "/api/review",
    "/api/next-step",
    "Apply",
    "Save next step",
    "Open project",
    "Create project",
    "Add source",
    "Edit file",
    "Save file",
    "Check readiness",
    "source_check",
    "source_index",
    "evidence_bind",
    "evidence_replay",
    "Run history",
    "Evidence summary",
    "Evidence result",
    "Evidence summary",
    "Weakest point",
    "Patterns across runs",
    "What's still unbacked",
    "EvidenceSupportPanel",
    "Save review",
    "report-contract-file",
    "Current focus",
    "local step plans",
    "Copy detail",
    "Can it run?",
    "Copy detail",
    "Needs support",
    "holding the report",
    "issues",
    "Preview source",
    "Review note",
    "Next-step note",
    "Latest saved project",
    "source_edit:",
    "Latest project brief change",
    "history-weakspot",
    "Preview latest",
    "What this saves",
    "Prefer the terminal? Show the equivalent command",
    "terminal-equivalent",
    "File preview",
    "Preview",
    "file-preview",
    "ztare-forensic-workbench-review-v1",
    "ztare-forensic-workbench-row-action-v1",
    "ztare forensic-workbench apply-review --project",
    "ztare forensic-workbench save-next-step --project",
    "--item",
    "--from",
    "Report readiness",
    "Workbench sections",
    "Evidence",
    "workbench_snapshot.json",
    "ztare-forensic-workbench-snapshot-v1",
    "single_project_read_model",
    "local_api",
    "ops_root_cause_diagnosis_demo",
    "Report readiness",
    "Latest saved review",
    "Latest next step",
]

REQUIRED_SYSTEM_POSITION_SNIPPETS = [
    "# System position and module map",
    "turning important reasoning into durable",
    "inspectable state",
    "ZTARE turns messy reasoning work into durable state",
    "what was being decided",
    "what supported it",
    "what failed",
    "what changed",
    "what should be checked next",
    "Project Workbench is one interface",
    "Kernel is the trusted boundary",
    "Engine is runnable machinery",
    "Apparatus is an experiment setup",
    "code has compilers, and reasoning needs similar",
    "## Product boundary",
    "ChatGPT, Claude",
    "Codex, Claude Code",
    "LangSmith",
    "bounded claim -> source intake -> attempt -> adversarial check",
    "workers, judges, or input",
    "durable decision trail over local sources",
    "weakest links, replayable checks, demotions, saved review records",
    "and next falsifiers",
    "## Neuro-symbolic boundary",
    "neural systems propose, search, summarize, critique, rank, translate, and",
    "symbolic and file-backed systems define the objects that survive a run",
    "No layer self-certifies.",
    "model-produced sentence is not a claim until it is",
    "bound to sources and checked.",
]

REQUIRED_PUBLIC_ROADMAP_SNIPPETS = [
    "# ZTARE Public Roadmap",
    "**Planning horizon:** next 4-6 weeks",
    "what most improves trust, leverage, and product legibility per unit effort?",
    "call the whole repo/system **ZTARE**",
    "local app the **Project Workbench**, the trusted checks and",
    "**kernel**, runnable subsystems **engines**, and historical experiment setups",
    "**apparatus**",
    "Scores use a RICE-style 1-5 scale:",
    "**Reach:** how much of the first public user path the lane affects.",
    "**Impact:** how much the lane improves claim safety or reviewer value.",
    "**Confidence:** how much current runnable evidence supports the lane.",
    "**Effort:** implementation and review cost, where 5 is highest cost.",
    "| Lane | Reach | Impact | Confidence | Effort | Current call |",
    "| First-run value | 5 | 5 | 5 | 2 | Keep green through release. |",
    "| Project brief and evidence readiness | 4 | 5 | 4 | 3 | Treat as the main review-entry path inside the project-to-thesis lane. |",
    "| Project Workbench app | 4 | 4 | 4 | 3 | Shipped in v1.0 as the local React/server app; v1.1 should deepen the live state it consumes rather than treating UI polish as the whole product. |",
    "project brief -> source files and evidence check -> run readiness",
    "`v1.0.0` shipped the Project Workbench release path",
    "The current planning path is v1.1.",
    "Do not claim general autonomous research performance.",
    "Do not stage release groups broadly while holdbacks remain in the dirty tree.",
]

REQUIRED_GLOSSARY_TAXONOMY_SNIPPETS = [
    "Layer Taxonomy (workbench / kernel / engine / apparatus)",
    "These words are not synonyms.",
    "Workbench is the user-facing view",
    "Kernel is the trusted core",
    "Engine is runnable machinery",
    "Apparatus is the historical research setup",
    "Default wording: call the product a workbench",
]

REQUIRED_PUBLIC_WORKFLOW_SNIPPETS = [
    "python -m pip install -e .",
    "make first-run PYTHON=python",
]

FORBIDDEN_PUBLIC_WORKFLOW_SNIPPETS = [
    "python -m pip install -e . PyYAML",
]

REQUIRED_PACKAGE_DEPENDENCIES = [
    "PyYAML>=6.0",
]

REQUIRED_IGNORE_SNIPPETS = [
    "ztare_workspace/transitions.jsonl",
    "ztare_workspace/gates/pending/*.json",
    "ztare_workspace/gates/resolved/*.json",
    "org/tasks/active/*",
    "orbit/node_modules/",
    "analytics/private/",
    "research_areas/private/",
]

FORBIDDEN_PUBLIC_TERMS = [
    "unsupported superlative claim",
    "cheating catalog",
    "adversarial reasoning engine",
    "adversarial-reasoning engine",
    "adversarial-reasoning",
    "apparatus deployment",
    "apparatus evidence",
    "autonomous research engine",
    "current-engine",
    "docs/internal",
    "dogfood",
    "evidence packet",
    "evidence packets",
    "evidence-packets",
    "general-purpose engine users",
    "gp_example",
    "lands hard",
    "load-bearing",
    "principal-orchestrator",
    "real work",
    "research-engine",
    "research operating system",
    "research_areas/private",
    "research-engineer",
    "substrate packet intake",
    "substrate prep ledger",
    "substrate-prober",
    "workbench workflow",
    "apparatus-lift",
    "tm" + "lr",
    "world class",
]

FORBIDDEN_PUBLIC_PATTERNS = [
    (
        re.compile(r"--project\s+[a-z0-9]+(?:_[a-z0-9]+)*_\d{4}\b", re.IGNORECASE),
        "dated project-specific CLI example",
    ),
    (
        re.compile(r"\bepistemic engine\b", re.IGNORECASE),
        "epistemic engine product label",
    ),
]

FORBIDDEN_DOC_COMMAND_PATTERNS = [
    re.compile(r"python3?\s+-m\s+src\.ztare"),
    re.compile(r"\./venv/bin/python\s+-m\s+src\.ztare"),
    re.compile(r"python\s+-c\s+['\"]from\s+src\.ztare"),
]

DOCUMENTED_MODULE_RE = re.compile(r"python3?\s+-m\s+(ztare\.[A-Za-z0-9_\.]+)")
UNIX_TEMP_COMMAND_PATH_RE = re.compile(r"(^|\s|[=>])/?tmp/")
INTAKE_AWARE_TRACE_EXAMPLE_RE = re.compile(
    r"ztare\s+autoresearch\s+trace\b"
    r"(?=[^\n]*--project\s+(?:demo_claims|<slug>|<project>))"
    r"(?=[^\n]*--rubric\s+(?:demo_claims|<slug>|<rubric>))",
)
PUBLIC_FIRST_RUN_MAKE_RE = re.compile(
    r"make\s+experiment-loop\b"
    r"(?=[^\n]*PROJECT=(?:<project>|<slug>|my_project|demo_claims)\b)"
    r"(?=[^\n]*RUBRIC=(?:<rubric>|<slug>|rubrics/my_project\.json|demo_claims)\b)"
)
PUBLIC_AUTORESEARCH_RUN_RE = re.compile(r"^ztare\s+autoresearch\s+run\b")
PUBLIC_SUBSTRATE_COMMAND_RE = re.compile(r"ztare\s+substrate\b")

REQUIRED_RESEARCHER_CROSS_REF_SNIPPETS = [
    "`docs/guides/for_researchers.md` §4 (charter contamination)",
    "`docs/guides/for_researchers.md` §4 and §6 plus AGENTS.md hard rules",
]

FORBIDDEN_RESEARCHER_CROSS_REF_SNIPPETS = [
    "`docs/guides/for_researchers.md` §2 (charter contamination)",
    "`docs/guides/for_researchers.md` §2",
    "`docs/guides/for_researchers.md` §4 and AGENTS.md §7",
]

PUBLIC_MARKDOWN_ROOTS = [
    REPO / "README.md",
    REPO / "CONTRIBUTING.md",
    REPO / "SECURITY.md",
    REPO / "CHANGELOG.md",
    REPO / "RELEASE_CHECKLIST.md",
    REPO / "priority_roadmap.md",
    REPO / "docs",
    REPO / "examples",
]

USERLAND_BIAS_SCAN_ROOTS = [
    REPO / "README.md",
    REPO / "priority_roadmap.md",
    REPO / "docs/guides",
    REPO / "examples",
    REPO / "src/ztare/cli.py",
]

FORBIDDEN_USERLAND_PROJECT_TERMS = [
    # Historical project slugs are allowed in archives and ledgers, but the
    # public first-run/userland path must stay project-agnostic.
    "old_example_project_2026",
    "gp023_planck_sandbox",
    "gp096_kww",
    "gp0nn",
    "ns_l3a",
    "n3_high_worry",
]

REQUIRED_CLI_HELP_SNIPPETS = [
    "ZTARE \u2014 zero-trust workbench for generating, stress-testing, and auditing claims.",
    "forecast",
    "leanmill",
    "autoresearch",
    "project",
    "substrate",
    "completion",
    "LeanMill governed proof search",
    "Project userland",
    "Compatibility alias",
]

REQUIRED_PROJECT_HELP_SNIPPETS = [
    "ztare project <verb> [args...]",
    "intake    \u2192 create, draft, validate, falsify, or enqueue bounded project intake",
    "Legacy: `project packet` still works as an alias for `project intake`",
    "prep-ledger \u2192 optional append-only prep ledger before run readiness",
    "queue     \u2192 compatibility alias for prep-ledger",
    "source-init \u2192 create source-ingest project files",
    "source-check \u2192 inspect raw source typing before evidence compilation",
    "source-index \u2192 write workspace source index from typed raw sources",
    "claim-support \u2192 classify compiled-evidence claims by source support",
    "legacy readiness aliases live here for compatibility; prefer `prep-ledger`",
    "not RD execution and not an",
]

FORBIDDEN_PROJECT_HELP_SNIPPETS = [
    "packet    \u2192 legacy alias for intake",
    "(create-packet | validate-packet | enqueue-packet | add | add-from-route | list | next | resolve-next)",
    "ztare substrate <verb>",
    "substrate/reproduction preparation",
]

REQUIRED_PROJECT_PREP_LEDGER_HELP_SNIPPETS = [
    "Filesystem-backed intake ledger for project/data preparation.",
    "analytics/public/queues/project_prep",
    "enqueue one project/data prep item",
    "not RD out-of-loop execution",
    "not a general",
]

FORBIDDEN_CLI_HELP_SNIPPETS = [
    "GP-",
    "adversarial scientific-reasoning engine",
    "Subcommands wrap the apparatus",
]

FORBIDDEN_PROJECT_PREP_LEDGER_HELP_SNIPPETS = [
    "analytics/public/queues/substrate_prep",
    "substrate/reproduction preparation",
    "enqueue one substrate/reproduction prep item",
    "substrate-prep queue item",
]

REQUIRED_CLI_COMMAND_CONTRACTS = [
    (
        ("version",),
        (
            "ztare 0.2.0",
            "python",
        ),
    ),
    (
        ("project", "intake", "--help"),
        (
            "Project intake makes the boundary explicit before in-loop",
            "ztare project intake create",
            "bounded claim",
            "next falsifier",
            "expected command",
            "source-preflight",
        ),
    ),
    (
        ("project", "packet", "--help"),
        (
            "Project intake makes the boundary explicit before in-loop",
            "prefer `project intake`",
            "bounded claim",
            "next falsifier",
            "expected command",
            "source-preflight",
        ),
    ),
    (
        ("substrate", "packet", "--help"),
        (
            "Project intake makes the boundary explicit before in-loop",
            "bounded claim",
            "next falsifier",
            "expected command",
            "source-preflight",
        ),
    ),
    (
        ("project", "source-init", "--help"),
        (
            "Initialize source-ingest project files",
            "--project",
            "--dry-run",
            "source_type_map",
            "does not launch",
        ),
    ),
    (
        ("project", "source-check", "--help"),
        (
            "Offline source-ingest preflight",
            "--project",
            "--no-fail",
            "does not compile evidence",
        ),
    ),
    (
        ("project", "source-index", "--help"),
        (
            "Incrementally update a project workspace from raw sources",
            "--index-only",
            "without LLM calls",
        ),
    ),
    (
        ("project", "evidence-replay", "--help"),
        (
            "Verify compiled_evidence_replay_manifest.json",
            "--project",
            "--json",
        ),
    ),
    (
        ("project", "claim-support", "--help"),
        (
            "Classify compiled-evidence claim rows by source support",
            "--project",
            "--json",
            "does not call a model",
        ),
    ),
    (
        ("autoresearch", "run", "--help"),
        (
            "Run a full in-loop experiment loop",
            "--intake <path>",
            "legacy alias for --intake",
            "kernel_entry.can_enter_kernel",
        ),
    ),
    (
        ("autoresearch", "route", "--help"),
        (
            "invoke in-loop autoresearch",
            "prepare missing project input",
            "stay",
            "--intake <path>",
            "--queue-dir <path>          optional project/data prep ledger directory",
        ),
    ),
    (
        ("autoresearch", "health", "--help"),
        (
            "source-preflight",
            "--project <slug>",
            "raw/source typing preflight",
        ),
    ),
    (
        ("forensic-workbench", "apply-review", "--help"),
        (
            "Apply a file-backed Project Workbench review file",
            "--project PROJECT",
            "--row ITEM",
            "--from REVIEW_FILE_PATH",
            "Review file JSON saved from the workbench",
            "latest-receipt JSON",
        ),
    ),
    (
        ("forensic-workbench", "save-next-step", "--help"),
        (
            "Apply a file-backed Project Workbench next-step file",
            "--project PROJECT",
            "--row ITEM",
            "--from ACTION_FILE_PATH",
            "Next-step JSON saved from the workbench",
            "latest next-step JSON",
        ),
    ),
    (
        ("forensic-workbench", "report-action", "--help"),
        (
            "Run a Project Workbench report action.",
            "--project PROJECT",
            "--action {check_readiness,refresh_inputs}",
            "--confirmed",
            "--json",
        ),
    ),
    (
        ("primitive", "--help"),
        (
            "run catalog health + atlas freshness checks",
            "parent-utility",
            "--semantic-live",
        ),
    ),
    (
        ("audit", "graph-capability", "--json"),
        (
            "ztare-graph-capability-audit-v1",
            "not_framework_replacement",
            "standard_algorithm_rows",
        ),
    ),
    (
        ("audit", "forecast-capability", "--json"),
        (
            "ztare-forecast-capability-audit-v1",
            "not_hidden_scheduler",
            "ready_receipt_paths",
        ),
    ),
    (
        ("audit", "move-card-router", "--json"),
        (
            "ztare-move-card-router-audit-v1",
            "deterministic_router_is_baseline",
            "primary_pass_count",
        ),
    ),
]

REQUIRED_COMPLETION_SNIPPETS = [
    "forecast",
    "f47-run",
    "leanmill",
    "proof-audit",
    "source-scout",
    "autoresearch",
    "route",
    "dispatch-parity",
    "project",
    "substrate",
    "forensic-workbench",
    "packet",
    "source-check",
    "evidence-replay",
    "eigenquestion",
    "status",
    "primitive",
    "parent-utility",
    "audit",
    "coverage",
    "arch-validate",
    "ex-post",
]

READY_PROJECT_INTAKE_FIXTURE = REPO / "examples/project_packets/ready_demo_claims_intake.json"
MALFORMED_PROJECT_INTAKE_FIXTURE = (
    REPO / "examples/project_packets/malformed_missing_evidence_intake.json"
)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def fail(message: str) -> None:
    raise SystemExit(f"public adversarial smoke failed: {message}")


def check_progress(message: str) -> None:
    print(f"public-adversarial-smoke: {message}", file=sys.stderr, flush=True)


def run(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    timeout: int = 60,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            cmd,
            cwd=cwd or REPO,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        timeout_msg = (
            f"command timed out after {timeout}s: "
            + " ".join(str(part) for part in cmd)
        )
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=124,
            stdout=stdout or "",
            stderr=(stderr + "\n" + timeout_msg).strip(),
        )


def extract_last_json_object(text: str) -> dict[str, object]:
    decoder = json.JSONDecoder()
    parsed: list[dict[str, object]] = []
    for match in re.finditer(r"(?m)^\{", text):
        idx = match.start()
        try:
            obj, _end = decoder.raw_decode(text[idx:])
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            parsed.append(obj)
    if not parsed:
        fail(f"could not find a JSON object in command output:\n{text}")
    return parsed[-1]


def ztare_command_from_rendered(command: str) -> list[str]:
    parts = shlex.split(command)
    if parts and parts[0] == "ztare":
        return [PYTHON, "-m", "src.ztare.cli", *parts[1:]]
    return parts


def runtime_artifacts() -> list[str]:
    found: list[str] = []
    for directory in RUNTIME_ARTIFACT_DIRS:
        if not directory.exists():
            continue
        for path in directory.glob(f"{TEST_PREFIX}*"):
            found.append(str(path.relative_to(REPO)))
    return sorted(found)


def require_snippets(path: Path, snippets: Iterable[str], *, case_sensitive: bool = True) -> list[str]:
    text = read(path)
    if not case_sensitive:
        folded = text.casefold()
        return [snippet for snippet in snippets if snippet.casefold() not in folded]
    return [snippet for snippet in snippets if snippet not in text]


def extract_make_target_recipe(makefile_text: str, target: str) -> list[str]:
    """Return normalized command lines for a simple Makefile target recipe."""
    recipe: list[str] = []
    in_target = False
    for line in makefile_text.splitlines():
        if not in_target:
            if re.match(rf"^{re.escape(target)}\s*:", line):
                in_target = True
            continue
        if not line.strip():
            continue
        if not line.startswith("\t"):
            break
        command = line.strip()
        command = command.replace("$(MAKE)", "make")
        recipe.append(command)
    return recipe


def extract_first_run_reference_commands(reference_text: str) -> list[str]:
    marker = "`make first-run` runs the full offline public path:"
    if marker not in reference_text:
        fail("make-target reference missing first-run expansion marker")
    after_marker = reference_text.split(marker, 1)[1]
    match = re.search(r"```bash\n(?P<body>.*?)\n```", after_marker, re.DOTALL)
    if not match:
        fail("make-target reference missing first-run command block")
    return [
        line.strip()
        for line in match.group("body").splitlines()
        if line.strip()
    ]


def check_first_run_reference_matches_makefile() -> dict[str, object]:
    makefile_recipe = extract_make_target_recipe(read(REPO / "Makefile"), "first-run")
    if not makefile_recipe:
        fail("Makefile first-run target has no parseable recipe")
    reference_commands = extract_first_run_reference_commands(
        read(REPO / "docs/reference/make_targets.md")
    )
    if makefile_recipe != reference_commands:
        fail(
            "docs/reference/make_targets.md first-run commands drifted from "
            f"Makefile: makefile={makefile_recipe!r} docs={reference_commands!r}"
        )
    return {"ok": True, "checked_commands": len(makefile_recipe)}


def check_makefile_wiring() -> dict[str, object]:
    makefile_text = read(REPO / "Makefile")
    missing = [snippet for snippet in REQUIRED_MAKE_SNIPPETS if snippet not in makefile_text]
    if missing:
        fail(f"Makefile missing required wiring: {missing}")
    forbidden = [
        snippet
        for snippet in FORBIDDEN_MAKEFILE_SNIPPETS
        if snippet in makefile_text
    ]
    if forbidden:
        fail(
            "Makefile public command defaults should use repo-local or "
            f"caller-supplied paths, not Unix-only temp roots: {forbidden}"
        )
    docker_missing = require_snippets(
        REPO / "scripts/public/control/docker_smoke.sh",
        REQUIRED_DOCKER_SMOKE_SNIPPETS,
    )
    if docker_missing:
        fail(f"docker_smoke.sh missing required wiring: {docker_missing}")
    return {
        "ok": True,
        "checked_makefile": len(REQUIRED_MAKE_SNIPPETS),
        "checked_forbidden_makefile": len(FORBIDDEN_MAKEFILE_SNIPPETS),
        "checked_docker_smoke": len(REQUIRED_DOCKER_SMOKE_SNIPPETS),
    }


def check_docs_wiring() -> dict[str, object]:
    user_paths = [
        REPO / "README.md",
        REPO / "docs/guides/first-30-minutes.md",
    ]
    user_text = "\n".join(read(path) for path in user_paths if path.exists())
    missing = [snippet for snippet in REQUIRED_USER_DOC_SNIPPETS if snippet not in user_text]
    if missing:
        fail(f"user docs missing public smoke snippets: {missing}")

    reference_path = REPO / "docs/reference/make_targets.md"
    reference_missing = require_snippets(reference_path, REQUIRED_REFERENCE_DOC_SNIPPETS)
    if reference_missing:
        fail(f"make-target reference missing maintainer command snippets: {reference_missing}")
    quickstart_path = REPO / "docs/guides/quickstart.md"
    quickstart_missing = require_snippets(quickstart_path, REQUIRED_QUICKSTART_SNIPPETS)
    if quickstart_missing:
        fail(f"quickstart missing intake-first in-loop snippets: {quickstart_missing}")
    first_run_match = check_first_run_reference_matches_makefile()

    checked_paths = user_paths + [reference_path, quickstart_path]
    return {
        "ok": True,
        "checked_files": [str(p.relative_to(REPO)) for p in checked_paths],
        "first_run_recipe": first_run_match,
    }


def check_forensic_workbench_interface_contract() -> dict[str, object]:
    path = REPO / "docs/concepts/forensic_workbench_interface.md"
    missing = require_snippets(path, REQUIRED_FORENSIC_WORKBENCH_SNIPPETS, case_sensitive=False)
    if missing:
        fail(f"forensic workbench interface doc missing required contract snippets: {missing}")

    cli_contracts = {tuple(args) for args, _snippets in REQUIRED_CLI_COMMAND_CONTRACTS}
    missing_cli_families = [
        "ztare " + " ".join(args)
        for args in REQUIRED_FORENSIC_WORKBENCH_CLI_FAMILIES
        if tuple(args) not in cli_contracts
    ]
    if missing_cli_families:
        fail(
            "forensic workbench interface references command families that are "
            f"not covered by CLI front-door contracts: {missing_cli_families}"
        )

    makefile = read(REPO / "Makefile")
    required_make = [
        "synth-contract:",
        "make synth-contract PROJECT=<project> RENDERER=decision_brief",
        "--support-contract-only",
    ]
    missing_make = [snippet for snippet in required_make if snippet not in makefile]
    if missing_make:
        fail(f"forensic workbench report/export contract missing Makefile support: {missing_make}")

    return {
        "ok": True,
        "checked_file": str(path.relative_to(REPO)),
        "checked_snippets": len(REQUIRED_FORENSIC_WORKBENCH_SNIPPETS),
        "checked_cli_families": [
            "ztare " + " ".join(args)
            for args in REQUIRED_FORENSIC_WORKBENCH_CLI_FAMILIES
        ],
        "checked_make_snippets": len(required_make),
    }


def check_forensic_workbench_snapshot_contract() -> dict[str, object]:
    path = REPO / "docs/landings/forensic_workbench_prototype.html"
    missing = require_snippets(path, REQUIRED_FORENSIC_WORKBENCH_SNAPSHOT_SNIPPETS)
    if missing:
        fail(f"forensic workbench prototype HTML missing required snippets: {missing}")

    proc = run([
        PYTHON,
        "scripts/public/control/forensic_workbench_snapshot.py",
        "--check",
    ], timeout=90)
    if proc.returncode != 0:
        fail(
            "forensic workbench snapshot generator failed\n"
            f"STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        fail(f"forensic workbench snapshot generator returned non-JSON: {exc}\n{proc.stdout}")
    if payload.get("ok") is not True or int(payload.get("row_count") or 0) < 8:
        fail(f"forensic workbench snapshot generator returned weak payload: {payload}")

    return {
        "ok": True,
        "checked_file": str(path.relative_to(REPO)),
        "checked_snippets": len(REQUIRED_FORENSIC_WORKBENCH_SNAPSHOT_SNIPPETS),
        "row_count": payload.get("row_count"),
    }


def check_forensic_workbench_react_contract() -> dict[str, object]:
    src = REPO / "forensic-workbench/src"
    files = [
        REPO / "forensic-workbench/package.json",
        REPO / "forensic-workbench/public/workbench_snapshot.json",
        REPO / "forensic-workbench/README.md",
        *sorted(src.rglob("*.js")),
        *sorted(src.rglob("*.jsx")),
    ]
    joined = "\n".join(read(path) for path in files)
    missing = [snippet for snippet in REQUIRED_FORENSIC_WORKBENCH_REACT_SNIPPETS if snippet not in joined]
    if missing:
        fail(f"forensic workbench React prototype missing required snippets: {missing}")
    try:
        payload = json.loads(read(REPO / "forensic-workbench/public/workbench_snapshot.json"))
    except json.JSONDecodeError as exc:
        fail(f"forensic workbench React payload is not JSON: {exc}")
    if payload.get("schema") != "ztare-forensic-workbench-snapshot-v1":
        fail(f"forensic workbench React payload has wrong schema: {payload}")
    rows = payload.get("rows") or []
    if len(rows) < 8:
        fail(f"forensic workbench React payload has too few rows: {payload}")
    missing_provenance = [row.get("label") for row in rows if not row.get("provenance")]
    if missing_provenance:
        fail(f"forensic workbench React rows missing provenance: {missing_provenance}")
    return {
        "ok": True,
        "checked_files": [str(path.relative_to(REPO)) for path in files],
        "checked_snippets": len(REQUIRED_FORENSIC_WORKBENCH_REACT_SNIPPETS),
        "row_count": len(rows),
    }


def create_public_smoke_recovery_project(project: str) -> Path:
    project_dir = REPO / "projects" / project
    if project_dir.exists():
        fail(f"public-smoke recovery fixture already exists: {project_dir}")
    raw_dir = project_dir / "raw"
    raw_dir.mkdir(parents=True)
    (project_dir / "thesis.md").write_text(
        "# Smoke Recovery Thesis\n\n"
        "The recovery path should draft a project brief from existing files before a run.\n",
        encoding="utf-8",
    )
    (project_dir / "project_charter.md").write_text(
        "# Smoke Recovery Charter\n\n"
        "Use the existing files to connect this folder before any project run.\n",
        encoding="utf-8",
    )
    (raw_dir / "source_note.md").write_text(
        "---\nsource_type: source_evidence\n---\n"
        "This note is a small tracked-smoke substitute for a historical folder with files but no project brief.\n",
        encoding="utf-8",
    )
    return project_dir


def check_forensic_workbench_state_contract() -> dict[str, object]:
    recovery_project = "_public_smoke_recovery_project"
    projects = ["ops_root_cause_diagnosis_demo", recovery_project]
    summaries: dict[str, object] = {}
    recovery_dir = create_public_smoke_recovery_project(recovery_project)
    try:
        for project in projects:
            proc = run(
                [
                    PYTHON,
                    "scripts/public/control/forensic_workbench_state.py",
                    "--project",
                    project,
                    "--json",
                    "--strict",
                ],
                timeout=90,
            )
            if proc.returncode != 0:
                fail(
                    f"forensic workbench state contract failed for {project}\n"
                    f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
                )
            try:
                payload = json.loads(proc.stdout)
            except json.JSONDecodeError as exc:
                fail(f"forensic workbench state returned non-JSON for {project}: {exc}\n{proc.stdout}")
            audit = payload.get("project_to_thesis_audit")
            if not isinstance(audit, dict) or not audit.get("ok"):
                fail(f"forensic workbench project-to-thesis audit failed for {project}: {audit}")
            summaries[project] = {
                "next_action": (payload.get("summary") or {}).get("next_action", ""),
                "failed_count": audit.get("failed_count", 0),
                "check_count": audit.get("check_count", 0),
            }
    finally:
        shutil.rmtree(recovery_dir, ignore_errors=True)
    return {
        "ok": True,
        "checked_projects": projects,
        "summaries": summaries,
    }


def check_system_position_contract() -> dict[str, object]:
    path = REPO / "docs/concepts/system_position_and_module_map.md"
    missing = require_snippets(path, REQUIRED_SYSTEM_POSITION_SNIPPETS, case_sensitive=False)
    if missing:
        fail(f"system-positioning doc missing required boundary snippets: {missing}")
    return {
        "ok": True,
        "checked_file": str(path.relative_to(REPO)),
        "checked_snippets": len(REQUIRED_SYSTEM_POSITION_SNIPPETS),
    }


def check_public_roadmap_contract() -> dict[str, object]:
    path = REPO / "priority_roadmap.md"
    missing = require_snippets(path, REQUIRED_PUBLIC_ROADMAP_SNIPPETS)
    if missing:
        fail(f"public roadmap missing required release-priority snippets: {missing}")
    return {
        "ok": True,
        "checked_file": str(path.relative_to(REPO)),
        "checked_snippets": len(REQUIRED_PUBLIC_ROADMAP_SNIPPETS),
    }


def check_glossary_taxonomy_contract() -> dict[str, object]:
    path = REPO / "docs/concepts/glossary.md"
    missing = require_snippets(path, REQUIRED_GLOSSARY_TAXONOMY_SNIPPETS, case_sensitive=False)
    if missing:
        fail(f"glossary missing layer-taxonomy snippets: {missing}")
    return {
        "ok": True,
        "checked_file": str(path.relative_to(REPO)),
        "checked_snippets": len(REQUIRED_GLOSSARY_TAXONOMY_SNIPPETS),
    }


def check_researcher_workflow_cross_refs() -> dict[str, object]:
    path = REPO / "docs/guides/experiment_cookbook.md"
    text = read(path)
    missing = [
        snippet for snippet in REQUIRED_RESEARCHER_CROSS_REF_SNIPPETS
        if snippet not in text
    ]
    forbidden = [
        snippet for snippet in FORBIDDEN_RESEARCHER_CROSS_REF_SNIPPETS
        if snippet in text
    ]
    if missing:
        fail(
            "experiment cookbook lost current researcher-guide cross "
            f"references: {missing}"
        )
    if forbidden:
        fail(
            "experiment cookbook has stale researcher-guide cross references: "
            f"{forbidden}"
        )
    return {
        "ok": True,
        "checked_file": str(path.relative_to(REPO)),
        "required_snippets": len(REQUIRED_RESEARCHER_CROSS_REF_SNIPPETS),
        "forbidden_snippets": len(FORBIDDEN_RESEARCHER_CROSS_REF_SNIPPETS),
    }


def check_public_workflow_wiring() -> dict[str, object]:
    workflow = REPO / ".github/workflows/public-smoke.yml"
    missing = require_snippets(workflow, REQUIRED_PUBLIC_WORKFLOW_SNIPPETS)
    if missing:
        fail(f"public GitHub workflow missing reviewer commands: {missing}")
    text = read(workflow)
    forbidden = [
        snippet
        for snippet in FORBIDDEN_PUBLIC_WORKFLOW_SNIPPETS
        if snippet in text
    ]
    if forbidden:
        fail(
            "public GitHub workflow should rely on package metadata, not "
            f"ad hoc installs: {forbidden}"
        )
    return {
        "ok": True,
        "checked_file": str(workflow.relative_to(REPO)),
        "checked_commands": len(REQUIRED_PUBLIC_WORKFLOW_SNIPPETS),
        "checked_forbidden": len(FORBIDDEN_PUBLIC_WORKFLOW_SNIPPETS),
    }


def check_package_metadata() -> dict[str, object]:
    pyproject = tomllib.loads(read(REPO / "pyproject.toml"))
    dependencies = pyproject.get("project", {}).get("dependencies", [])
    missing = [
        dependency
        for dependency in REQUIRED_PACKAGE_DEPENDENCIES
        if dependency not in dependencies
    ]
    if missing:
        fail(f"pyproject.toml missing public runtime dependencies: {missing}")
    return {
        "ok": True,
        "checked_file": "pyproject.toml",
        "checked_dependencies": len(REQUIRED_PACKAGE_DEPENDENCIES),
    }


def check_gitignore_boundaries() -> dict[str, object]:
    missing = require_snippets(REPO / ".gitignore", REQUIRED_IGNORE_SNIPPETS)
    if missing:
        fail(f".gitignore missing runtime/private boundaries: {missing}")
    return {"ok": True, "checked": len(REQUIRED_IGNORE_SNIPPETS)}


def check_public_language() -> dict[str, object]:
    checked_paths = sorted(
        {
            *iter_public_markdown_paths(),
            REPO / "pyproject.toml",
            REPO / "CITATION.cff",
            REPO / "src/ztare/cli.py",
        }
    )
    hits: list[str] = []
    for path in checked_paths:
        if not path.exists():
            continue
        text = read(path).lower()
        for term in FORBIDDEN_PUBLIC_TERMS:
            if term in text:
                hits.append(f"{path.relative_to(REPO)} contains {term!r}")
        for pattern, label in FORBIDDEN_PUBLIC_PATTERNS:
            if pattern.search(text):
                hits.append(f"{path.relative_to(REPO)} contains {label}")
    if hits:
        fail("; ".join(hits))
    return {"ok": True, "checked_files": [str(p.relative_to(REPO)) for p in checked_paths if p.exists()]}


def check_cli_front_door() -> dict[str, object]:
    help_proc = run([PYTHON, "-m", "src.ztare.cli", "--help"])
    if help_proc.returncode != 0:
        fail(f"ztare --help failed\nSTDOUT:\n{help_proc.stdout}\nSTDERR:\n{help_proc.stderr}")
    missing_help = [snippet for snippet in REQUIRED_CLI_HELP_SNIPPETS if snippet not in help_proc.stdout]
    if missing_help:
        fail(f"ztare --help missing public snippets: {missing_help}")
    forbidden_help = [snippet for snippet in FORBIDDEN_CLI_HELP_SNIPPETS if snippet in help_proc.stdout]
    if forbidden_help:
        fail(f"ztare --help contains stale/internal snippets: {forbidden_help}")

    project_help_proc = run([PYTHON, "-m", "src.ztare.cli", "project", "--help"])
    if project_help_proc.returncode != 0:
        fail(
            "ztare project --help failed\n"
            f"STDOUT:\n{project_help_proc.stdout}\nSTDERR:\n{project_help_proc.stderr}"
        )
    missing_project_help = [
        snippet
        for snippet in REQUIRED_PROJECT_HELP_SNIPPETS
        if snippet not in project_help_proc.stdout
    ]
    if missing_project_help:
        fail(f"ztare project --help missing public snippets: {missing_project_help}")
    forbidden_project_help = [
        snippet
        for snippet in FORBIDDEN_PROJECT_HELP_SNIPPETS
        if snippet in project_help_proc.stdout
    ]
    if forbidden_project_help:
        fail(
            "ztare project --help contains stale/internal snippets: "
            f"{forbidden_project_help}"
        )

    prep_ledger_help_proc = run([PYTHON, "-m", "src.ztare.cli", "project", "prep-ledger", "--help"])
    if prep_ledger_help_proc.returncode != 0:
        fail(
            "ztare project prep-ledger --help failed\n"
            f"STDOUT:\n{prep_ledger_help_proc.stdout}\nSTDERR:\n{prep_ledger_help_proc.stderr}"
        )
    missing_prep_ledger_help = [
        snippet
        for snippet in REQUIRED_PROJECT_PREP_LEDGER_HELP_SNIPPETS
        if snippet not in prep_ledger_help_proc.stdout
    ]
    if missing_prep_ledger_help:
        fail(f"ztare project prep-ledger --help missing public snippets: {missing_prep_ledger_help}")
    forbidden_prep_ledger_help = [
        snippet
        for snippet in FORBIDDEN_PROJECT_PREP_LEDGER_HELP_SNIPPETS
        if snippet in prep_ledger_help_proc.stdout
    ]
    if forbidden_prep_ledger_help:
        fail(
            "ztare project prep-ledger --help contains stale/internal snippets: "
            f"{forbidden_prep_ledger_help}"
        )

    command_contracts: dict[str, int] = {}
    for args, snippets in REQUIRED_CLI_COMMAND_CONTRACTS:
        proc = run([PYTHON, "-m", "src.ztare.cli", *args])
        label = "ztare " + " ".join(args)
        if proc.returncode != 0:
            fail(f"{label} failed\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
        combined = proc.stdout + proc.stderr
        missing = [snippet for snippet in snippets if snippet not in combined]
        if missing:
            fail(f"{label} missing command-contract snippets: {missing}")
        command_contracts[label] = len(snippets)

    completion_checks: dict[str, int] = {}
    for shell in ("bash", "zsh", "fish"):
        proc = run([PYTHON, "-m", "src.ztare.cli", "completion", shell])
        if proc.returncode != 0:
            fail(f"ztare completion {shell} failed\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
        missing_completion = [
            snippet for snippet in REQUIRED_COMPLETION_SNIPPETS
            if snippet not in proc.stdout
        ]
        if missing_completion:
            fail(f"ztare completion {shell} missing snippets: {missing_completion}")
        completion_checks[shell] = len(REQUIRED_COMPLETION_SNIPPETS)
    return {
        "ok": True,
        "checked_help_snippets": len(REQUIRED_CLI_HELP_SNIPPETS),
        "checked_forbidden_help_snippets": len(FORBIDDEN_CLI_HELP_SNIPPETS),
        "checked_project_help_snippets": len(REQUIRED_PROJECT_HELP_SNIPPETS),
        "checked_forbidden_project_help_snippets": len(FORBIDDEN_PROJECT_HELP_SNIPPETS),
        "checked_project_prep_ledger_help_snippets": len(REQUIRED_PROJECT_PREP_LEDGER_HELP_SNIPPETS),
        "checked_forbidden_project_prep_ledger_help_snippets": len(FORBIDDEN_PROJECT_PREP_LEDGER_HELP_SNIPPETS),
        "checked_command_contracts": command_contracts,
        "checked_completion_snippets": completion_checks,
    }


def load_cli_module():
    spec = importlib.util.spec_from_file_location(
        "ztare_cli_for_public_smoke",
        REPO / "src/ztare/cli.py",
    )
    if not spec or not spec.loader:
        fail("could not load src/ztare/cli.py for command inventory check")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_cli_guide_command_inventory() -> dict[str, object]:
    cli_module = load_cli_module()
    actual = set(cli_module._SUBCOMMANDS)
    guide = read(REPO / "docs/guides/cli.md")
    documented = set(
        re.findall(r"\| `ztare ([a-z][a-z-]*)(?: [^`]*)?` \|", guide)
    )
    missing = sorted(actual.difference(documented))
    if missing:
        fail(f"docs/guides/cli.md missing top-level CLI commands: {missing}")
    return {
        "ok": True,
        "command_count": len(actual),
        "documented_command_count": len(documented),
    }


def check_capabilities_catalog_count() -> dict[str, object]:
    index_path = REPO / "analytics/public/index/architecture_index.jsonl"
    row_count = sum(1 for line in read(index_path).splitlines() if line.strip())
    expected = f"generated {row_count}-row capability catalog"
    capabilities = read(REPO / "docs/concepts/capabilities.md")
    if expected not in capabilities:
        fail(
            "docs/concepts/capabilities.md capability-catalog count drifted: "
            f"expected phrase {expected!r}"
        )
    return {
        "ok": True,
        "architecture_index_rows": row_count,
    }


def iter_public_markdown_paths() -> list[Path]:
    paths: list[Path] = []
    for root in PUBLIC_MARKDOWN_ROOTS:
        if root.is_file():
            paths.append(root)
            continue
        if root.is_dir():
            paths.extend(
                path
                for path in root.rglob("*.md")
                if "internal" not in path.relative_to(REPO).parts
                and "_archive" not in path.relative_to(REPO).parts
            )
    return sorted(set(paths))


def iter_userland_bias_scan_paths() -> list[Path]:
    paths: list[Path] = []
    for root in USERLAND_BIAS_SCAN_ROOTS:
        if root.is_file():
            paths.append(root)
            continue
        if root.is_dir():
            paths.extend(
                path
                for path in root.rglob("*")
                if path.suffix in {".md", ".py"}
                and "internal" not in path.relative_to(REPO).parts
                and "_archive" not in path.relative_to(REPO).parts
            )
    return sorted(set(paths))


def check_userland_project_bias() -> dict[str, object]:
    hits: list[str] = []
    checked_paths = iter_userland_bias_scan_paths()
    for path in checked_paths:
        text = read(path).lower()
        for term in FORBIDDEN_USERLAND_PROJECT_TERMS:
            if term in text:
                hits.append(f"{path.relative_to(REPO)} contains project-specific userland anchor {term!r}")
    if hits:
        fail("; ".join(hits))
    return {
        "ok": True,
        "checked_files": [str(path.relative_to(REPO)) for path in checked_paths],
        "checked_terms": len(FORBIDDEN_USERLAND_PROJECT_TERMS),
    }


def check_public_command_examples() -> dict[str, object]:
    stale: list[str] = []
    nonportable_temp_paths: list[str] = []
    intakeless_first_run_traces: list[str] = []
    unguarded_first_runs: list[str] = []
    stale_project_front_door: list[str] = []
    modules: set[str] = set()
    checked_paths = iter_public_markdown_paths()
    checked_paths.append(REPO / "src/ztare/cli.py")
    for path in sorted(set(checked_paths)):
        text = read(path)
        rel = path.relative_to(REPO)
        for pattern in FORBIDDEN_DOC_COMMAND_PATTERNS:
            match = pattern.search(text)
            if match:
                stale.append(f"{rel}: stale command form {match.group(0)!r}")
        lines = text.splitlines()
        for line_no, line in enumerate(lines, start=1):
            if (
                UNIX_TEMP_COMMAND_PATH_RE.search(line)
                and "rather than `/tmp/`" not in line
            ):
                nonportable_temp_paths.append(f"{rel}:{line_no}: {line.strip()}")
            if INTAKE_AWARE_TRACE_EXAMPLE_RE.search(line) and "--intake" not in line:
                intakeless_first_run_traces.append(f"{rel}:{line_no}: {line.strip()}")
            if (
                PUBLIC_FIRST_RUN_MAKE_RE.search(line)
                and str(rel) != "docs/reference/make_targets.md"
            ):
                unguarded_first_runs.append(f"{rel}:{line_no}: {line.strip()}")
            stripped_line = line.strip()
            if PUBLIC_AUTORESEARCH_RUN_RE.search(stripped_line):
                command_window = " ".join(lines[line_no - 1: min(len(lines), line_no + 3)])
                if "--intake" not in command_window:
                    unguarded_first_runs.append(f"{rel}:{line_no}: {line.strip()}")
            if PUBLIC_SUBSTRATE_COMMAND_RE.search(line):
                context = " ".join(
                    lines[max(0, line_no - 2): min(len(lines), line_no + 1)]
                ).lower()
                is_source_comment = (
                    str(rel) == "src/ztare/cli.py"
                    and line.lstrip().startswith("#")
                )
                if "compatibility" not in context and not is_source_comment:
                    stale_project_front_door.append(f"{rel}:{line_no}: {line.strip()}")
        modules.update(DOCUMENTED_MODULE_RE.findall(text))
    missing_modules = sorted(
        module for module in modules if importlib.util.find_spec(module) is None
    )
    if stale:
        fail("; ".join(stale))
    if nonportable_temp_paths:
        fail(
            "public command examples use Unix-only temp paths; use repo-local "
            f"or caller-supplied paths instead: {nonportable_temp_paths}"
        )
    if intakeless_first_run_traces:
        fail(
            "first-run/demo/template autoresearch trace examples must include "
            f"--intake so intake readiness is explicit: {intakeless_first_run_traces}"
        )
    if unguarded_first_runs:
        fail(
            "copyable public run examples must use the intake-gated CLI path "
            f"or live in the Make target reference: {unguarded_first_runs}"
        )
    if stale_project_front_door:
        fail(
            "public copyable project commands should use `ztare project ...`; "
            "`ztare substrate ...` is allowed only in compatibility notes: "
            f"{stale_project_front_door}"
        )
    if missing_modules:
        fail(f"public docs reference missing python -m modules: {missing_modules}")
    return {
        "ok": True,
        "checked_files": len(set(checked_paths)),
        "checked_modules": len(modules),
        "checked_intake_aware_trace_examples": True,
        "checked_intake_gated_run_examples": True,
        "checked_project_front_door_commands": True,
    }


def check_runtime_smoke_cleanup() -> dict[str, object]:
    before = runtime_artifacts()
    if before:
        fail(f"pre-existing runtime smoke artifacts block the check: {before}")
    proc = run([PYTHON, "scripts/public/control/runtime_smoke_test.py", "--json"])
    if proc.returncode != 0:
        fail(f"runtime_smoke_test.py failed\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        fail(f"runtime smoke did not emit JSON: {exc}")
    if not payload.get("ok"):
        fail(f"runtime smoke JSON reported failure: {payload}")
    after = runtime_artifacts()
    if after:
        fail(f"runtime smoke left artifacts behind: {after}")
    cleanup = payload.get("cleanup") or {}
    removed = cleanup.get("removed") or []
    if not removed:
        fail("runtime smoke did not report cleanup removals")
    return {"ok": True, "removed_count": len(removed)}


def check_forecast_pool_isolation() -> dict[str, object]:
    proc = run([PYTHON, "scripts/public/control/forecast/pool.py", "smoke"])
    if proc.returncode != 0:
        fail(f"forecast_pool.py smoke failed\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
    if '"smoke": "pass"' not in proc.stdout:
        fail("forecast_pool smoke did not report pass")
    if "forecast_pool_smoke_" not in proc.stdout:
        fail("forecast_pool smoke did not report a temporary isolated root")
    repo_root_fragment = str(REPO / "analytics/public/forecast_pool")
    if repo_root_fragment in proc.stdout:
        fail("forecast_pool smoke wrote or reported the repo forecast-pool root")
    return {"ok": True, "isolated_root": "internal_tempdir"}


def check_action_intelligence_contracts() -> dict[str, object]:
    proc = run([PYTHON, "scripts/public/control/action_intelligence.py", "smoke"])
    if proc.returncode != 0:
        fail(f"action_intelligence.py smoke failed\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        fail(f"action intelligence smoke did not emit JSON: {exc}")
    if not payload.get("ok"):
        fail(f"action intelligence smoke JSON reported failure: {payload}")
    checked = payload.get("checked") or []
    required = {
        "decision_use_to_action_impact",
        "shadow_policy_live_row_rejection",
        "override_without_reason_rejection",
        "surfacing_event_to_action_impact",
    }
    missing = sorted(required.difference(checked))
    if missing:
        fail(f"action intelligence smoke missing contract checks: {missing}")
    return {"ok": True, "checked": checked}


def check_project_intake_cli() -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="ztare_project_intake_smoke_") as tmp:
        root = Path(tmp)
        project = "public_smoke_claims"
        raw_dir = root / "projects" / project / "raw"
        workspace_dir = root / "projects" / project / "workspace"
        raw_dir.mkdir(parents=True)
        workspace_dir.mkdir(parents=True)
        (raw_dir / "source.md").write_text(
            "Primary source text for the public intake smoke.\n",
            encoding="utf-8",
        )
        (raw_dir / "source_type_map.json").write_text(
            json.dumps({"source.md": "source_evidence"}, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (workspace_dir / "receipt.json").write_text(
            json.dumps({"ok": True, "kind": "public_intake_smoke"}, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        intake = root / "intake.json"
        walkthrough_intake = root / "walkthrough_intake.json"
        queue_dir = root / "queue"
        common = [PYTHON, "-m", "src.ztare.cli", "project", "intake"]
        cli_env = {
            **os.environ,
            "PYTHONPATH": str(REPO),
            "ZTARE_REPO": str(root),
        }
        walkthrough_demo = run([
            PYTHON,
            "-m",
            "src.ztare.cli",
            "project",
            "walkthrough",
        ], cwd=root, env=cli_env)
        if walkthrough_demo.returncode != 0:
            fail(
                "project walkthrough demo failed\n"
                f"STDOUT:\n{walkthrough_demo.stdout}\nSTDERR:\n{walkthrough_demo.stderr}"
            )
        if (
            "validate_ready_intake:" not in walkthrough_demo.stdout
            or "validate_malformed_intake:" not in walkthrough_demo.stdout
        ):
            fail(
                "project walkthrough demo lost intake-facing labels\n"
                f"STDOUT:\n{walkthrough_demo.stdout}\nSTDERR:\n{walkthrough_demo.stderr}"
            )
        if "validate_ready_packet" in walkthrough_demo.stdout or "validate_malformed_packet" in walkthrough_demo.stdout:
            fail(
                "project walkthrough demo reintroduced packet-facing labels\n"
                f"STDOUT:\n{walkthrough_demo.stdout}\nSTDERR:\n{walkthrough_demo.stderr}"
            )
        walkthrough = run([
            PYTHON,
            "-m",
            "src.ztare.cli",
            "project",
            "walkthrough",
            "--project",
            project,
            "--rubric",
            project,
            "--task",
            "test a bounded public-smoke claim",
            "--bounded-claim",
            "the smoke intake validates on fixture evidence",
            "--source-ref",
            f"projects/{project}/raw/source.md",
            "--evidence-ref",
            f"projects/{project}/workspace/receipt.json",
            "--non-claim",
            "not a full replication",
            "--next-falsifier",
            "remove the evidence ref and validation must fail",
            "--intake-out",
            str(walkthrough_intake),
            "--json",
        ], cwd=root, env=cli_env)
        if walkthrough.returncode != 0:
            fail(
                "project walkthrough failed\n"
                f"STDOUT:\n{walkthrough.stdout}\nSTDERR:\n{walkthrough.stderr}"
            )
        walkthrough_payload = json.loads(walkthrough.stdout)
        phases = {
            row.get("phase"): row
            for row in walkthrough_payload.get("command_plan") or []
            if isinstance(row, dict)
        }
        for phase in ("source_and_evidence_prep", "read_only_trace", "in_loop_gate"):
            if phase not in phases:
                fail(f"project walkthrough missing command-plan phase {phase}: {walkthrough_payload}")
            if phases[phase].get("ready") is not True:
                fail(f"project walkthrough phase {phase} is not ready: {walkthrough_payload}")

        source_index = run([
            PYTHON,
            "-m",
            "src.ztare.cli",
            "project",
            "source-index",
            "--project",
            str(root / "projects" / project),
            "--json",
        ], cwd=root, env=cli_env)
        if source_index.returncode != 0:
            fail(
                "project source-index failed\n"
                f"STDOUT:\n{source_index.stdout}\nSTDERR:\n{source_index.stderr}"
            )
        source_index_payload = json.loads(source_index.stdout)
        receipt_path = Path(str(source_index_payload.get("source_index_receipt") or ""))
        if source_index_payload.get("llm_calls") is not False:
            fail(f"project source-index JSON lost offline contract: {source_index_payload}")
        if not receipt_path.exists():
            fail(f"project source-index did not write receipt: {source_index_payload}")
        receipt_payload = json.loads(receipt_path.read_text(encoding="utf-8"))
        if receipt_payload.get("schema") != "ztare-source-index-receipt-v1":
            fail(f"project source-index receipt has wrong schema: {receipt_payload}")
        if receipt_payload.get("status") != "indexed":
            fail(f"project source-index receipt has wrong status: {receipt_payload}")
        if receipt_payload.get("source_index_sha256") is None:
            fail(f"project source-index receipt missing source-index hash: {receipt_payload}")

        workspace_snapshot = {
            "project": project,
            "compiler_summary": "public smoke workspace snapshot",
            "immutable_ground_truth": [
                {
                    "statement": "The smoke intake has one typed source.",
                    "strength": "fixture",
                    "source_ids": ["S001"],
                }
            ],
            "numerical_ranges_and_constraints": [],
            "identified_contradictions": [],
            "epistemic_voids": [],
            "provenance": [
                {
                    "source_id": "S001",
                    "path": "source.md",
                    "kind": "md",
                    "source_type": "source_evidence",
                    "summary": "Fixture source for public smoke.",
                }
            ],
            "candidate_claims_to_test": [
                {
                    "claim": "the smoke intake validates on fixture evidence",
                    "priority": "high",
                    "source_ids": ["S001"],
                }
            ],
        }
        (workspace_dir / "workspace_snapshot.json").write_text(
            json.dumps(workspace_snapshot, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        compile_evidence = run([
            PYTHON,
            "-m",
            "ztare.workspace.compile_evidence",
            "--project",
            str(root / "projects" / project),
            "--mode",
            "workspace",
        ], cwd=root, env=cli_env)
        if compile_evidence.returncode != 0:
            fail(
                "project compile-evidence workspace mode failed\n"
                f"STDOUT:\n{compile_evidence.stdout}\nSTDERR:\n{compile_evidence.stderr}"
            )
        provenance_path = root / "projects" / project / "compiled_evidence_provenance.json"
        evidence_path = root / "projects" / project / "evidence.txt"
        audit_copy_path = root / "projects" / project / "compiled_evidence.txt"
        packet_output_path = root / "projects" / project / "compiled_evidence_packet.json"
        provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
        expected_hashes = {
            "output_sha256": evidence_path,
            "audit_copy_sha256": audit_copy_path,
            "packet_output_sha256": packet_output_path,
        }
        for field, artifact_path in expected_hashes.items():
            observed = provenance.get(field)
            expected = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
            if observed != expected:
                fail(
                    "project compile-evidence provenance hash mismatch "
                    f"{field}: observed={observed!r} expected={expected!r}"
                )
        (workspace_dir / "latest_evidence_gaps.json").write_text(
            json.dumps(
                {
                    "project": project,
                    "evidence_gaps": [
                        {
                            "id": "gap1",
                            "severity": "degrading",
                            "target": "external comparator",
                            "description": "Need another public comparator.",
                        }
                    ],
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        gap_resolution = run([
            PYTHON,
            "-m",
            "src.ztare.cli",
            "project",
            "evidence-gap",
            "justify",
            "--project",
            str(root / "projects" / project),
            "--gap-id",
            "gap1",
            "--reason",
                    "The comparator is outside the bounded public smoke intake.",
            "--json",
        ], cwd=root, env=cli_env)
        if gap_resolution.returncode != 0:
            fail(
                "project evidence-gap justify failed\n"
                f"STDOUT:\n{gap_resolution.stdout}\nSTDERR:\n{gap_resolution.stderr}"
            )
        gap_resolution_payload = json.loads(gap_resolution.stdout)
        gap_resolution_path = Path(str(gap_resolution_payload.get("path") or ""))
        if not gap_resolution_path.exists():
            fail(f"project evidence-gap justify did not write receipt: {gap_resolution_payload}")
        gap_resolution_receipt = json.loads(gap_resolution_path.read_text(encoding="utf-8"))
        if gap_resolution_receipt.get("schema") != "ztare-evidence-gap-resolutions-v1":
            fail(f"project evidence-gap receipt has wrong schema: {gap_resolution_receipt}")
        resolution = gap_resolution_payload.get("resolution")
        if not isinstance(resolution, dict) or resolution.get("status") != "justified":
            fail(f"project evidence-gap justify returned wrong resolution: {gap_resolution_payload}")
        drafted_intake = root / "drafted_from_compiled_intake.json"
        draft = run([
            *common,
            "draft-from-compiled",
            "--project",
            project,
            "--path",
            str(drafted_intake),
            "--json",
        ], cwd=root, env=cli_env)
        if draft.returncode != 0:
            fail(
                "project-intake draft-from-compiled command failed\n"
                f"STDOUT:\n{draft.stdout}\nSTDERR:\n{draft.stderr}"
            )
        drafted = json.loads(draft.stdout)
        if not drafted.get("validation", {}).get("ok"):
            fail(f"project-intake draft-from-compiled returned invalid intake: {drafted}")
        draft_source = drafted.get("packet", {}).get("draft_source", {})
        if draft_source.get("kind") != "compiled_evidence_artifact":
            fail(f"project-intake draft-from-compiled missing draft source: {drafted}")

        create = run([
            *common,
            "create",
            "--path",
            str(intake),
            "--project",
            project,
            "--rubric",
            project,
            "--task",
            "test a bounded public-smoke claim",
            "--bounded-claim",
            "the smoke intake validates on fixture evidence",
            "--source-ref",
            f"projects/{project}/raw/source.md",
            "--evidence-ref",
            f"projects/{project}/workspace/receipt.json",
            "--non-claim",
            "not a full replication",
            "--next-falsifier",
            "remove the evidence ref and validation must fail",
            "--expected-command",
            "ztare autoresearch route --task 'test a bounded public-smoke claim' --project public_smoke_claims --rubric public_smoke_claims",
            "--json",
        ], cwd=root, env=cli_env)
        if create.returncode != 0:
            fail(f"project-intake create command failed\nSTDOUT:\n{create.stdout}\nSTDERR:\n{create.stderr}")
        created = json.loads(create.stdout)
        if not created.get("validation", {}).get("ok"):
            fail(f"project-intake create returned invalid intake: {created}")

        validate = run([*common, "validate", "--path", str(intake), "--json"], cwd=root, env=cli_env)
        if validate.returncode != 0:
            fail(f"project-intake validate command failed\nSTDOUT:\n{validate.stdout}\nSTDERR:\n{validate.stderr}")
        validation = json.loads(validate.stdout)
        if not validation.get("ok"):
            fail(f"project-intake validate reported failure: {validation}")

        falsify = run([
            *common,
            "falsify",
            "--path",
            str(intake),
            "--remove-ref",
            "evidence_refs[1]",
            "--write-workspace-receipt",
            "--json",
        ], cwd=root, env=cli_env)
        if falsify.returncode != 0:
            fail(
                "project-intake falsify receipt command failed\n"
                f"STDOUT:\n{falsify.stdout}\nSTDERR:\n{falsify.stderr}"
            )
        falsifier_payload = json.loads(falsify.stdout)
        receipt_path = workspace_dir / "packet_falsifier_receipt.json"
        if not receipt_path.exists():
            fail(f"project-intake falsifier did not write receipt: {falsifier_payload}")
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if receipt.get("status") != "resolved":
            fail(f"project-intake falsifier receipt is not resolved: {receipt}")
        if receipt.get("remove_ref") != "evidence_refs[1]":
            fail(f"project-intake falsifier receipt selected wrong ref: {receipt}")
        if "local path does not exist" not in str(receipt.get("expected_failure") or ""):
            fail(f"project-intake falsifier receipt missing expected failure: {receipt}")
        path_safety = receipt.get("path_safety") if isinstance(receipt, dict) else {}
        if not isinstance(path_safety, dict) or path_safety.get("symlink_escape_allowed") is not False:
            fail(f"project-intake falsifier receipt missing path-safety policy: {receipt}")
        if "--write-workspace-receipt" not in str(receipt.get("command") or ""):
            fail(f"project-intake falsifier receipt command is not reproducible: {receipt}")

        enqueue = run([
            *common,
            "enqueue",
            "--queue-dir",
            str(queue_dir),
            "--path",
            str(intake),
            "--json",
        ], cwd=root, env=cli_env)
        if enqueue.returncode != 0:
            fail(f"project-intake enqueue command failed\nSTDOUT:\n{enqueue.stdout}\nSTDERR:\n{enqueue.stderr}")
        item = json.loads(enqueue.stdout)
        if item.get("kind") != "project_intake":
            fail(f"project-intake enqueue returned wrong kind: {item}")

        resolve = run([
            PYTHON,
            "-m",
            "src.ztare.cli",
            "project",
            "prep-ledger",
            "--queue-dir",
            str(queue_dir),
            "resolve-next",
            "--result",
            "ready_for_autoresearch",
            "--reason",
            "public smoke intake validated",
            "--artifact-ref",
            str(intake),
            "--json",
        ], cwd=root, env=cli_env)
        if resolve.returncode != 0:
            fail(f"project prep-ledger resolve-next failed\nSTDOUT:\n{resolve.stdout}\nSTDERR:\n{resolve.stderr}")
        resolved = json.loads(resolve.stdout)
        if resolved.get("status") != "ready_for_autoresearch":
            fail(f"project prep-ledger resolve-next returned wrong status: {resolved}")
    return {
        "ok": True,
        "checked": [
            "project walkthrough",
            "project walkthrough demo intake labels",
            "project source-index receipt",
            "project evidence compile output binding",
            "project evidence-gap justification",
            "project-intake create",
            "project-intake draft-from-compiled",
            "project-intake validate",
            "project-intake falsify workspace receipt",
            "project-intake enqueue",
            "project prep-ledger resolve-next",
        ],
        "isolated_root": "internal_tempdir",
    }


def check_public_project_intake_fixtures() -> dict[str, object]:
    ready = run([
        PYTHON,
        "-m",
        "src.ztare.cli",
        "project",
        "intake",
        "validate",
        "--path",
        str(READY_PROJECT_INTAKE_FIXTURE),
        "--json",
    ])
    if ready.returncode != 0:
        fail(
            "ready project-intake fixture failed validation\n"
            f"STDOUT:\n{ready.stdout}\nSTDERR:\n{ready.stderr}"
        )
    ready_payload = json.loads(ready.stdout)
    if not ready_payload.get("ok"):
        fail(f"ready project-intake fixture reported invalid: {ready_payload}")

    trace = run([
        PYTHON,
        "-m",
        "src.ztare.cli",
        "autoresearch",
        "trace",
        "--project",
        str(ready_payload.get("project") or "demo_claims"),
        "--rubric",
        str(ready_payload.get("rubric") or "demo_claims"),
        "--intake",
        str(READY_PROJECT_INTAKE_FIXTURE),
        "--json",
    ])
    if trace.returncode != 0:
        fail(
            "ready project-intake fixture failed autoresearch trace\n"
            f"STDOUT:\n{trace.stdout}\nSTDERR:\n{trace.stderr}"
        )
    trace_payload = json.loads(trace.stdout)
    allowed_readiness = {"ready_for_first_in_loop_run", "ready_for_in_loop_candidate"}
    if trace_payload.get("readiness") not in allowed_readiness:
        fail(f"ready project-intake trace is not ready for in-loop routing: {trace_payload}")
    if trace_payload.get("readiness_canonical") not in allowed_readiness:
        fail(f"ready project-intake trace is missing canonical readiness: {trace_payload}")
    if trace_payload.get("blocking_missing"):
        fail(f"ready project-intake trace has blocking missing project inputs: {trace_payload}")
    route_preview = trace_payload.get("route_preview") or {}
    if (
        route_preview.get("source") != "project_intake"
        or route_preview.get("source_name") != "project_intake"
        or route_preview.get("legacy_source") != "project_packet"
        or route_preview.get("can_run_now") is not True
    ):
        fail(f"ready project-intake trace has invalid route preview: {trace_payload}")
    preflight_command = route_preview.get("preflight_command")
    run_command = route_preview.get("run_command")
    if not isinstance(preflight_command, str) or "--preflight-only" not in preflight_command:
        fail(f"ready project-intake trace does not expose preflight-only command: {trace_payload}")
    if not isinstance(run_command, str) or "--iters 10" not in run_command:
        fail(f"ready project-intake trace does not expose full run command: {trace_payload}")
    next_commands = list(trace_payload.get("next_commands") or [])
    if run_command not in next_commands:
        fail(f"ready project-intake next commands omit full run command: {trace_payload}")
    plan_preview = trace_payload.get("plan_preview") or {}
    if plan_preview.get("schema") != "ztare-autoresearch-plan-preview-v1":
        fail(f"ready project-intake trace is missing plan-preview contract: {trace_payload}")
    plan_status = plan_preview.get("status")
    if plan_status not in {"ready_for_preflight", "ready_for_bounded_run"}:
        fail(f"ready project-intake plan preview has invalid ready status: {trace_payload}")
    if plan_preview.get("model_calls_before_confirmation") is not False:
        fail(f"ready project-intake plan preview allows pre-confirmation model calls: {trace_payload}")
    if plan_status == "ready_for_preflight":
        if preflight_command not in next_commands:
            fail(f"ready project-intake next commands omit preflight-only command: {trace_payload}")
        if next_commands.index(preflight_command) > next_commands.index(run_command):
            fail(f"ready project-intake next commands put full run before preflight: {trace_payload}")
        if plan_preview.get("recommended_first_command") != preflight_command:
            fail(f"ready project-intake plan preview does not recommend preflight first: {trace_payload}")
    if plan_status == "ready_for_bounded_run":
        if plan_preview.get("recommended_first_command") != run_command:
            fail(f"ready project-intake plan preview does not recommend bounded run after admission: {trace_payload}")
    budget = plan_preview.get("budget") or {}
    if budget.get("model_fallback_policy") != "disabled_by_default":
        fail(f"ready project-intake plan preview changed fallback policy: {trace_payload}")
    dependency_ids = [
        step.get("id")
        for step in plan_preview.get("dependency_order") or []
        if isinstance(step, dict)
    ]
    if "preflight_only" not in dependency_ids or "bounded_loop_run" not in dependency_ids:
        fail(f"ready project-intake plan preview lost preflight/run dependency order: {trace_payload}")
    if dependency_ids.index("preflight_only") > dependency_ids.index("bounded_loop_run"):
        fail(f"ready project-intake plan preview puts paid run before preflight: {trace_payload}")
    kernel_entry = trace_payload.get("kernel_entry") or {}
    if kernel_entry.get("schema") != "ztare-kernel-entry-contract-v1":
        fail(f"ready project-intake trace is missing run-readiness contract: {trace_payload}")
    if kernel_entry.get("can_enter_kernel") is not True or kernel_entry.get("status") != "ready":
        fail(f"ready project-intake run-readiness contract is not ready: {trace_payload}")
    if kernel_entry.get("readiness_canonical") not in allowed_readiness:
        fail(f"ready project-intake run-readiness lost canonical readiness: {trace_payload}")
    if kernel_entry.get("entry_command") != route_preview.get("route_command"):
        fail(f"run-readiness contract drifted from route preview: {trace_payload}")
    if kernel_entry.get("preflight_command") != preflight_command:
        fail(f"run-readiness contract drifted from preflight preview: {trace_payload}")
    if kernel_entry.get("run_command") != run_command:
        fail(f"run-readiness contract drifted from run preview: {trace_payload}")
    allowed_work_modes = set(kernel_entry.get("allowed_work_modes") or [])
    if "in_loop_autoresearch_gate" not in allowed_work_modes:
        fail(f"run-readiness contract does not allow the in-loop gate: {trace_payload}")
    disallowed_work_modes = set(kernel_entry.get("disallowed_work_modes") or [])
    if "rd_out_of_loop_execution" not in disallowed_work_modes:
        fail(f"run-readiness contract lost the RD out-of-loop boundary: {trace_payload}")

    # The bounded-loop preflight below imports the full research stack
    # (numpy/scipy/...). The public path is lean by design (requirements-public-smoke.txt:
    # "full autoresearch runs need the heavy research stack ... out of scope"), so when
    # that stack is absent we stop after verifying the readiness contract rather than
    # running the in-loop preflight. Malformed-intake rejection is covered by `make hello`.
    if importlib.util.find_spec("numpy") is None:
        return {
            "ok": True,
            "ready_intake_project": ready_payload.get("project"),
            "readiness": trace_payload.get("readiness"),
            "bounded_run_preflight": "skipped: research stack absent (lean public path)",
        }

    ready_preflight = run(ztare_command_from_rendered(preflight_command))
    if ready_preflight.returncode != 0:
        fail(
            "ready project-intake preflight-only run failed\n"
            f"STDOUT:\n{ready_preflight.stdout}\nSTDERR:\n{ready_preflight.stderr}"
        )
    trace_after_preflight = run([
        PYTHON,
        "-m",
        "src.ztare.cli",
        "autoresearch",
        "trace",
        "--project",
        str(ready_payload.get("project") or "demo_claims"),
        "--rubric",
        str(ready_payload.get("rubric") or "demo_claims"),
        "--intake",
        str(READY_PROJECT_INTAKE_FIXTURE),
        "--json",
    ])
    if trace_after_preflight.returncode != 0:
        fail(
            "ready project-intake fixture failed trace after preflight-only run\n"
            f"STDOUT:\n{trace_after_preflight.stdout}\nSTDERR:\n{trace_after_preflight.stderr}"
        )
    trace_after_preflight_payload = json.loads(trace_after_preflight.stdout)
    loop_admission = trace_after_preflight_payload.get("loop_admission") or {}
    if not loop_admission.get("available"):
        loop_admission = trace_payload.get("loop_admission") or {}
    if loop_admission.get("available") is not True:
        fail(
            "ready project-intake trace is missing loop admission receipt "
            f"after preflight-only run: {trace_after_preflight_payload}"
        )
    if int(loop_admission.get("receipt_count") or 0) < 1:
        fail(
            "ready project-intake trace has no admitted loop receipts "
            f"after preflight-only run: {trace_after_preflight_payload}"
        )
    if loop_admission.get("intake_hash_verified") is False:
        fail(
            "ready project-intake trace reports stale admitted intake bytes "
            f"after preflight-only run: {trace_after_preflight_payload}"
        )
    intake_statuses = set(loop_admission.get("intake_hash_statuses") or [])
    if intake_statuses - {"fresh"}:
        fail(
            "ready project-intake trace has unexpected intake admission status "
            f"after preflight-only run: {trace_after_preflight_payload}"
        )
    if loop_admission.get("kernel_entry_hash_verified") is False:
        fail(
            "ready project-intake trace reports stale run-readiness receipt "
            f"after preflight-only run: {trace_after_preflight_payload}"
        )
    kernel_entry_statuses = set(loop_admission.get("kernel_entry_hash_statuses") or [])
    if kernel_entry_statuses - {"fresh"}:
        fail(
            "ready project-intake trace has unexpected run-readiness receipt status "
            f"after preflight-only run: {trace_after_preflight_payload}"
        )
    post_plan = trace_after_preflight_payload.get("plan_preview") or {}
    if post_plan.get("status") != "ready_for_bounded_run":
        fail(
            "ready project-intake trace did not advance to bounded run after "
            f"preflight-only run: {trace_after_preflight_payload}"
        )
    if post_plan.get("recommended_first_command") != run_command:
        fail(
            "ready project-intake trace does not recommend bounded run after "
            f"preflight-only run: {trace_after_preflight_payload}"
        )

    malformed = run([
        PYTHON,
        "-m",
        "src.ztare.cli",
        "project",
        "intake",
        "validate",
        "--path",
        str(MALFORMED_PROJECT_INTAKE_FIXTURE),
        "--json",
    ])
    if malformed.returncode == 0:
        fail("malformed project-intake fixture unexpectedly validated")
    malformed_payload = json.loads(malformed.stdout)
    errors = malformed_payload.get("errors") or []
    if "missing required non-empty list: evidence_refs" not in errors:
        fail(f"malformed project-intake failed for the wrong reason: {malformed_payload}")

    blocked_run = run([
        PYTHON,
        "-m",
        "src.ztare.cli",
        "autoresearch",
        "run",
        "--project",
        str(ready_payload.get("project") or "demo_claims"),
        "--rubric",
        str(ready_payload.get("rubric") or "demo_claims"),
        "--intake",
        str(MALFORMED_PROJECT_INTAKE_FIXTURE),
        "--iters",
        "1",
    ])
    if blocked_run.returncode == 0:
        fail("malformed project-intake unexpectedly launched autoresearch run")
    if "blocked by run-readiness contract" not in blocked_run.stderr:
        fail(
            "malformed project-intake run failed for the wrong reason\n"
            f"STDOUT:\n{blocked_run.stdout}\nSTDERR:\n{blocked_run.stderr}"
        )
    if (
        "readiness: blocked_on_project_intake" not in blocked_run.stderr
        or "project_intake (project_intake)" not in blocked_run.stderr
    ):
        fail(
            "malformed project-intake blocker lost intake-facing labels\n"
            f"STDOUT:\n{blocked_run.stdout}\nSTDERR:\n{blocked_run.stderr}"
        )

    return {
        "ok": True,
        "checked": [
            str(READY_PROJECT_INTAKE_FIXTURE.relative_to(REPO)),
            "ztare autoresearch trace --project demo_claims --rubric demo_claims --intake examples/project_packets/ready_demo_claims_intake.json",
            "trace run-readiness contract",
            "trace canonical intake readiness",
            "ready intake preflight-only creates loop admission receipt",
            "trace loop admission receipt",
            "trace plan_preview respects preflight and bounded-run phases",
            "ztare autoresearch run --intake malformed fixture blocks before launch",
            "malformed intake blocker uses intake labels",
            str(MALFORMED_PROJECT_INTAKE_FIXTURE.relative_to(REPO)),
        ],
    }


def check_autoresearch_carrier_replay_cli() -> dict[str, object]:
    proc = run([
        PYTHON,
        "-m",
        "src.ztare.cli",
        "autoresearch",
        "carrier-replay",
        "--project",
        "demo_claims",
        "--json",
    ])
    if proc.returncode != 0:
        fail(
            "autoresearch carrier-replay CLI failed\n"
            f"STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        fail(f"autoresearch carrier-replay CLI returned non-JSON: {exc}\n{proc.stdout}")
    if payload.get("schema") != "ztare-autoresearch-carrier-replay-v1":
        fail(f"carrier replay returned wrong schema: {payload}")
    summary = payload.get("summary") or {}
    if summary.get("project_count") != 1:
        fail(f"carrier replay did not report exactly one project: {payload}")
    # The carrier-completeness assertions below require demo_claims to be a
    # model-prepared fixture (compiled_evidence_packet.json + workspace_snapshot,
    # produced by `make evidence-prepare`, which needs a model). The public path is
    # lean by design, so when the demo is not model-prepared we verify the CLI
    # contract (schema + single project) and stop rather than asserting a carrier
    # state a lean checkout cannot reach.
    if not (REPO / "projects" / "demo_claims" / "compiled_evidence_packet.json").exists():
        return {
            "ok": True,
            "checked": ["ztare autoresearch carrier-replay --project demo_claims --json"],
            "current_carrier_assertions": "skipped: demo_claims not model-prepared (lean public path)",
        }
    if summary.get("current_carrier_complete_count") != 1:
        fail(f"carrier replay did not report current carrier readiness: {payload}")
    if summary.get("current_carrier_missing_count") != 0:
        fail(f"carrier replay reported missing current carriers for demo fixture: {payload}")
    rows = payload.get("projects") or []
    if len(rows) != 1 or rows[0].get("project") != "demo_claims":
        fail(f"carrier replay returned wrong project rows: {payload}")
    row = rows[0]
    current = row.get("current_carrier") or {}
    if current.get("available") is not True or current.get("status") != "complete":
        fail(f"carrier replay lost complete current-carrier status: {payload}")
    missing = row.get("missing_carrier_fields") or {}
    if int(missing.get("artifact_refs") or 0) <= 0:
        fail(f"demo fixture no longer exercises legacy carrier debt: {payload}")
    if row.get("next_action") != "legacy_carrier_backfill_optional_current_rows_ok":
        fail(f"carrier replay lost legacy/current distinction: {payload}")
    return {
        "ok": True,
        "checked": [
            "ztare autoresearch carrier-replay --project demo_claims --json",
            "carrier replay current-carrier readiness",
            "carrier replay legacy/current distinction",
        ],
    }


def parse_hello_machine_summary(stdout: str) -> dict[str, object]:
    marker = "Machine summary for CI/review:"
    if marker not in stdout:
        fail("hello_value_demo.py output missing machine summary marker")
    summary_text = stdout.split(marker, 1)[1].strip()
    try:
        payload = json.loads(summary_text)
    except json.JSONDecodeError as exc:
        fail(f"hello_value_demo.py machine summary is not JSON: {exc}")
    if not isinstance(payload, dict):
        fail(f"hello_value_demo.py machine summary is not an object: {payload!r}")
    return payload


def check_hello_expected_output_doc() -> dict[str, object]:
    hello = run([PYTHON, "scripts/public/control/hello_value_demo.py"])
    if hello.returncode != 0:
        fail(
            "hello_value_demo.py failed while checking expected-output docs\n"
            f"STDOUT:\n{hello.stdout}\nSTDERR:\n{hello.stderr}"
        )
    if "Malformed intake: blocked" not in hello.stdout or "\n  intake: " not in hello.stdout:
        fail(f"hello_value_demo.py stdout lost intake wording:\n{hello.stdout}")
    if "Malformed packet: blocked" in hello.stdout or "\n  packet: " in hello.stdout:
        fail(f"hello_value_demo.py stdout reintroduced packet wording:\n{hello.stdout}")
    payload = parse_hello_machine_summary(hello.stdout)
    if payload.get("ready_intake_ok") is not True:
        fail(f"hello_value_demo.py lost ready_intake_ok: {payload}")
    if payload.get("ready_intake_falsifier_ok") is not True:
        fail(f"hello_value_demo.py lost ready_intake_falsifier_ok: {payload}")
    if payload.get("malformed_intake_ok") is not False:
        fail(f"hello_value_demo.py lost malformed_intake_ok=false: {payload}")
    packet_path = REPO / "docs/evidence_atlas/packets/evaluator_hardening.md"
    packet_text = read(packet_path)
    verdict = payload.get("verdict")
    claim_allowed = payload.get("claim_allowed")
    writes_runtime_state = payload.get("writes_persistent_runtime_state")
    expected = [
        f"verdict: `{verdict}`",
        f"`claim_allowed: {claim_allowed}`",
        f"`writes_persistent_runtime_state: {str(writes_runtime_state).lower()}`",
    ]
    missing = [snippet for snippet in expected if snippet not in packet_text]
    if missing:
        fail(
            "evaluator hardening packet drifted from hello_value_demo.py "
            f"machine summary: missing {missing}"
        )
    return {
        "ok": True,
        "checked_file": str(packet_path.relative_to(REPO)),
        "verdict": verdict,
        "claim_allowed": claim_allowed,
        "writes_persistent_runtime_state": writes_runtime_state,
        "ready_intake_ok": payload.get("ready_intake_ok"),
        "ready_intake_falsifier_ok": payload.get("ready_intake_falsifier_ok"),
        "malformed_intake_ok": payload.get("malformed_intake_ok"),
    }


def check_ops_demo_report_support_contract_surfaces_runtime_risk() -> dict[str, object]:
    # report-action reads a synthesis context produced by `make synth` (a model
    # step). The public path is lean by design, so when the ops demo has no
    # committed synthesis context we skip this model-prepared assertion rather
    # than requiring a model run in a clean checkout.
    if not (REPO / "projects" / "ops_root_cause_diagnosis_demo" / "synthesis" / "report_support_contract.json").exists():
        return {
            "ok": True,
            "report_readiness_assertions": "skipped: ops demo synthesis context absent (lean public path)",
        }
    proc = run([
        str(PYTHON),
        "-m",
        "src.ztare.cli",
        "forensic-workbench",
        "report-action",
        "--project",
        "ops_root_cause_diagnosis_demo",
        "--action",
        "check_readiness",
        "--renderer",
        "decision_brief",
        "--confirmed",
        "--json",
    ], timeout=90)
    if proc.returncode != 0:
        fail(
            "ops_root_cause_diagnosis_demo report-action should refresh the "
            f"readiness file and keep runtime risk advisory\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )
    payload = extract_last_json_object(proc.stdout)
    if payload.get("ok") is not True or payload.get("status") != "attention":
        fail(f"ops demo report readiness file lost advisory-attention status: {payload}")
    reasons = payload.get("status_reasons") or []
    if "runtime_risks_present" not in reasons:
        fail(f"ops demo report readiness file lost runtime-risk warning: {payload}")
    binding = payload.get("synthesis_input_binding") or {}
    if not isinstance(binding, dict) or binding.get("status") != "fresh":
        fail(f"ops demo report readiness file lost fresh input-binding status: {payload}")
    return {
        "ok": True,
        "checked": [
            "ztare forensic-workbench report-action --project ops_root_cause_diagnosis_demo --action check_readiness --renderer decision_brief --confirmed --json",
            "zero-exit report-readiness refresh",
            "runtime_risks_present",
            "synthesis input binding fresh",
        ],
        "status": payload.get("status"),
        "status_reasons": reasons,
    }


def check_ops_demo_kernel_health_read_models() -> dict[str, object]:
    proc = run([
        "make",
        "autoresearch-kernel-health",
        "PROJECT=ops_root_cause_diagnosis_demo",
        "RUBRIC=ops_root_cause_diagnosis_demo",
        "INTAKE=projects/ops_root_cause_diagnosis_demo/ops_root_cause_diagnosis_demo_packet.json",
        "JSON=1",
        f"PYTHON={PYTHON}",
    ], timeout=90)
    if proc.returncode != 0:
        fail(
            "ops_root_cause_diagnosis_demo kernel health failed\n"
            f"STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )
    payload = extract_last_json_object(proc.stdout)
    if payload.get("schema") != "ztare-autoresearch-kernel-health-v1":
        fail(f"ops demo kernel health returned wrong schema: {payload}")
    summary = payload.get("summary") or {}
    if summary.get("overall_status") not in {"attention", "needs_attention"}:
        fail(f"ops demo kernel health should surface advisory or explicit repair attention: {payload}")
    components = {
        str(row.get("component")): row
        for row in (payload.get("components") or [])
        if isinstance(row, dict)
    }
    project_trace = (components.get("project_trace") or {}).get("summary") or {}
    trace_blockers = {
        str(row.get("id") or row.get("recovery_channel") or "")
        for row in (project_trace.get("blockers") or [])
        if isinstance(row, dict)
    }
    trace_ready = project_trace.get("can_enter_kernel") is True and project_trace.get("kernel_entry_status") == "ready"
    trace_blocked_on_evidence = (
        project_trace.get("can_enter_kernel") is False
        and project_trace.get("kernel_entry_status") == "blocked"
        and "out_of_loop_evidence_recovery" in trace_blockers
    )
    # Run-readiness state and provider-runtime-risk signatures require a
    # model/run-prepared demo (evidence-replay manifest + a run's provider
    # failure signatures). The public path is lean by design, so assert these only
    # when the ops demo has run history; the source-health checks below stay
    # unconditional.
    demo_run_prepared = (
        REPO / "projects" / "ops_root_cause_diagnosis_demo" / "workspace" / "eval_history.jsonl"
    ).exists()
    if demo_run_prepared:
        if not (trace_ready or trace_blocked_on_evidence):
            fail(f"ops demo kernel health lost inspectable run-readiness status: {payload}")
        if int(project_trace.get("provider_failure_signature_count") or 0) < 1:
            fail(f"ops demo kernel health no longer surfaces provider-runtime risk: {payload}")

    operations = (components.get("operations_intelligence") or {}).get("summary") or {}
    if int(operations.get("source_health_blockers") or 0) != 0:
        fail(f"ops demo source-health warnings must not block the release path: {payload}")
    warning_count = int(operations.get("source_health_warnings") or 0)
    issue_types = set((operations.get("source_health_issue_type_counts") or {}).keys())
    expected_issue_types = {
        "weak_gp233_linkage",
        "stale_trajectory_output",
        "unconsumed_surface",
    }
    if warning_count < len(expected_issue_types) or not expected_issue_types.issubset(issue_types):
        fail(f"ops demo source-health warnings lost expected issue types: {payload}")
    if (components.get("operations_intelligence") or {}).get("status") != "ok":
        fail(f"ops demo operations-intelligence component should stay non-blocking: {payload}")

    return {
        "ok": True,
        "checked": [
            "make autoresearch-kernel-health PROJECT=ops_root_cause_diagnosis_demo JSON=1",
            "run readiness ready or explicit evidence-recovery blocker surfaced",
            "provider runtime risk is advisory attention",
            "source-health warnings are non-blocking",
        ],
        "overall_status": summary.get("overall_status"),
        "source_health_warnings": warning_count,
        "source_health_issue_types": sorted(issue_types),
    }


def check_ordinary_review_freeze_checker() -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="ztare_ordinary_review_freeze_smoke_") as tmp:
        root = Path(tmp)
        source_run = root / "source_run"
        source_run.mkdir()
        (source_run / "results.json").write_text(
            json.dumps([
                {"condition": "A_baseline_soft_judge", "specimen_id": "demo"},
            ]) + "\n",
            encoding="utf-8",
        )

        run_root = root / "run"
        row_dir = run_root / "demo" / "D_ordinary_review"
        row_dir.mkdir(parents=True)
        prompt_path = row_dir / "ordinary_review_prompt.txt"
        raw_path = row_dir / "ordinary_review.raw.json"
        eval_path = row_dir / "eval_results.json"
        prompt_text = "ordinary-review smoke prompt\n"
        reviewed_at = "2026-06-19T00:00:00Z"
        prompt_path.write_text(prompt_text, encoding="utf-8")
        raw_path.write_text('{"score": 25}\n', encoding="utf-8")
        eval_path.write_text('{"returncode": 0}\n', encoding="utf-8")
        (run_root / "results.json").write_text(
            json.dumps([
                {
                    "condition": "D_ordinary_review",
                    "specimen_id": "demo",
                    "label": "bad",
                    "score": 25,
                    "passed_threshold": False,
                    "structural_detected": True,
                    "family_detected": False,
                    "ordinary_review_source": "imported",
                    "ordinary_review_model": "external-reviewer",
                    "ordinary_review_reviewed_at": reviewed_at,
                }
            ]) + "\n",
            encoding="utf-8",
        )
        (run_root / "metrics_summary.json").write_text(
            json.dumps({
                "conditions": {
                    "D_ordinary_review": {
                        "num_specimens": 1,
                        "error_count": 0,
                        "false_accept_rate": 0.0,
                    }
                }
            }) + "\n",
            encoding="utf-8",
        )
        manifest = {
            "arm_id": "D_ordinary_review",
            "source_run_bound": True,
            "can_promote_to_frozen_suite": True,
            "promotion_blockers": [],
            "error_count": 0,
            "selected_specimen_count": 1,
            "expected_source_specimen_count": 1,
            "selected_specimen_ids": ["demo"],
            "expected_source_specimen_ids": ["demo"],
            "missing_source_specimen_ids": [],
            "extra_specimen_ids": [],
            "review_sources": ["imported"],
            "rows": [
                {
                    "specimen_id": "demo",
                    "prompt_sha256": sha256_text(prompt_text),
                    "prompt_path": str(prompt_path),
                    "raw_review_path": str(raw_path),
                    "eval_results_path": str(eval_path),
                    "source": "imported",
                    "model": "external-reviewer",
                    "reviewed_at": reviewed_at,
                    "provider_runtime": "external",
                }
            ],
        }
        manifest_path = run_root / "ordinary_review_freeze_manifest.json"
        manifest_path.write_text(json.dumps(manifest) + "\n", encoding="utf-8")

        ok_proc = run([
            PYTHON,
            "scripts/public/control/ordinary_review_freeze_check.py",
            str(run_root),
            "--source-run",
            str(source_run),
        ])
        if ok_proc.returncode != 0:
            fail(f"ordinary_review_freeze_check.py rejected valid fixture\nSTDOUT:\n{ok_proc.stdout}\nSTDERR:\n{ok_proc.stderr}")
        ok_payload = json.loads(ok_proc.stdout)
        if not ok_payload.get("ok"):
            fail(f"ordinary-review freeze check did not report ok: {ok_payload}")

        manifest["can_promote_to_frozen_suite"] = False
        manifest["promotion_blockers"] = ["smoke blocker"]
        manifest_path.write_text(json.dumps(manifest) + "\n", encoding="utf-8")
        bad_proc = run([
            PYTHON,
            "scripts/public/control/ordinary_review_freeze_check.py",
            str(run_root),
            "--source-run",
            str(source_run),
        ])
        if bad_proc.returncode == 0:
            fail("ordinary_review_freeze_check.py accepted blocked fixture")

    return {
        "ok": True,
        "checked": [
            "ordinary review freeze check accepts promotion-ready fixture",
            "ordinary review freeze check rejects blocked fixture",
        ],
        "isolated_root": "internal_tempdir",
    }


def check_research_move_routing_drift_audit() -> dict[str, object]:
    proc = run([PYTHON, "scripts/public/control/research_move_routing_drift_audit.py", "--json"])
    if proc.returncode != 0:
        fail(
            "research_move_routing_drift_audit.py failed\n"
            f"STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        fail(f"research move routing drift audit returned non-JSON: {exc}\n{proc.stdout}")
    if not payload.get("ok"):
        fail(f"research move routing drift audit reported findings: {payload}")
    return {
        "ok": True,
        "metrics": payload.get("metrics", {}),
        "advisory_count": len(payload.get("advisories", []) or []),
    }


def run_named_check(name: str, check_fn) -> dict[str, object]:
    check_progress(f"start {name}")
    started = time.monotonic()
    payload = check_fn()
    elapsed_seconds = round(time.monotonic() - started, 2)
    check_progress(f"ok {name} {elapsed_seconds}s")
    if isinstance(payload, dict):
        payload = {**payload, "elapsed_seconds": elapsed_seconds}
    return payload


def main() -> int:
    check_plan = [
        ("makefile_wiring", check_makefile_wiring),
        ("docs_wiring", check_docs_wiring),
        ("forensic_workbench_interface_contract", check_forensic_workbench_interface_contract),
        ("forensic_workbench_snapshot_contract", check_forensic_workbench_snapshot_contract),
        ("forensic_workbench_react_contract", check_forensic_workbench_react_contract),
        ("forensic_workbench_state_contract", check_forensic_workbench_state_contract),
        ("system_position_contract", check_system_position_contract),
        ("public_roadmap_contract", check_public_roadmap_contract),
        ("glossary_taxonomy_contract", check_glossary_taxonomy_contract),
        ("researcher_workflow_cross_refs", check_researcher_workflow_cross_refs),
        ("public_workflow_wiring", check_public_workflow_wiring),
        ("package_metadata", check_package_metadata),
        ("gitignore_boundaries", check_gitignore_boundaries),
        ("public_language", check_public_language),
        ("cli_front_door", check_cli_front_door),
        ("cli_guide_command_inventory", check_cli_guide_command_inventory),
        ("capabilities_catalog_count", check_capabilities_catalog_count),
        ("userland_project_bias", check_userland_project_bias),
        ("public_command_examples", check_public_command_examples),
        ("runtime_smoke_cleanup", check_runtime_smoke_cleanup),
        ("forecast_pool_isolation", check_forecast_pool_isolation),
        ("action_intelligence_contracts", check_action_intelligence_contracts),
        ("project_intake_cli", check_project_intake_cli),
        ("public_project_intake_fixtures", check_public_project_intake_fixtures),
        ("autoresearch_carrier_replay_cli", check_autoresearch_carrier_replay_cli),
        ("hello_expected_output_doc", check_hello_expected_output_doc),
        ("ops_demo_report_support_contract", check_ops_demo_report_support_contract_surfaces_runtime_risk),
        ("ops_demo_kernel_health_read_models", check_ops_demo_kernel_health_read_models),
        ("ordinary_review_freeze_checker", check_ordinary_review_freeze_checker),
        ("research_move_routing_drift_audit", check_research_move_routing_drift_audit),
    ]
    checks = {
        name: run_named_check(name, check_fn)
        for name, check_fn in check_plan
    }
    print(json.dumps({"ok": True, "checks": checks}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
