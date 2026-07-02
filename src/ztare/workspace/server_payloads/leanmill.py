"""LeanMill payloads for the local Workbench API."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ztare.leanmill.workbench_actions import latest_jobs, start_action
from ztare.leanmill.workbench_target import (
    TARGET_HISTORY_SCHEMA,
    list_project_leanmill_areas,
    scaffold_project_leanmill_area,
    target_payload,
)


LEANMILL_STATE_SCHEMA = "ztare-forensic-workbench-leanmill-state-v1"


def repo_rel(path: Path, *, storage: Any) -> str:
    return storage.rel(path)


def display_label(value: Any) -> str:
    return str(value or "").replace("_", " ").replace("-", " ").strip()


def read_json_object(path: Path, *, storage: Any) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(storage.read_text(path))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def read_jsonl_objects(path: Path, *, storage: Any, limit: int = 100) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in storage.read_text(path).splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows[-limit:]


def file_row(path: Path, *, root: Path, storage: Any) -> dict[str, Any]:
    return {
        "path": repo_rel(path, storage=storage),
        "name": path.name,
        "group": path.parent.relative_to(root).as_posix() if path.parent != root else ".",
        "size_bytes": path.stat().st_size if path.exists() else 0,
    }


def workbench_root(repo: Path) -> Path:
    return repo / "analytics" / "public" / "leanmill" / "workbench"


def target_request_payload(request: dict[str, Any], *, repo: Path, storage: Any) -> dict[str, Any]:
    return target_payload(request, repo=repo, storage=storage)


def project_areas_payload(repo: Path, *, storage: Any) -> dict[str, Any]:
    """User project-local LeanMill areas (projects/<slug>/leanmill), distinct
    from the curated example formalizations."""
    areas = list_project_leanmill_areas(repo)
    return {
        "kind": "user_projects",
        "label": "Project formalization areas",
        "note": "LeanMill work that lives under a selected autoresearch project.",
        "count": len(areas),
        "areas": areas,
        "scaffold_route": "POST /api/leanmill/scaffold",
        "scaffold_cli": "ztare leanmill target --project <slug> --title <title> --target <statement>",
        "root_template": "projects/{project}/leanmill",
    }


def scaffold_payload(request: dict[str, Any], *, repo: Path, storage: Any) -> dict[str, Any]:
    """Create the projects/<slug>/leanmill folder contract for a user project."""
    project = str(request.get("project") or "").strip()
    if not request.get("confirmed") is True:
        return {
            "schema": "ztare-forensic-workbench-leanmill-area-scaffold-v1",
            "ok": True,
            "status": "needs_confirmation",
            "accepted": False,
            "requires_confirmation": True,
            "project": project,
            "preview": {
                "root_template": "projects/{project}/leanmill",
                "creates": ["targets/", "lean/", "notes/", "history/", "README.md"],
                "boundary": "Creates the project-local LeanMill folder contract; no proof job is launched.",
            },
        }
    result = scaffold_project_leanmill_area(project, repo=repo, storage=storage)
    result["status"] = "scaffolded"
    result["accepted"] = True
    result["requires_confirmation"] = False
    return result


def autoformalize_payload(request: dict[str, Any], *, repo: Path, storage: Any) -> dict[str, Any]:
    return start_action("autoformalize_notes", request, repo=repo, storage=storage)


def solve_adhoc_payload(request: dict[str, Any], *, repo: Path, storage: Any) -> dict[str, Any]:
    return start_action("solve_adhoc", request, repo=repo, storage=storage)


def ratify_payload(request: dict[str, Any], *, repo: Path, storage: Any) -> dict[str, Any]:
    """Kernel-ratify a finished proof (L1 compile + L2 axiom-allowlist + L3 anti-laundering) as a background
    job — proofs are slow, so it never blocks. Wiring only; the `proof_audit` action lives in the kernel."""
    return start_action("proof_audit", request, repo=repo, storage=storage)


def state_payload(*, repo: Path, storage: Any) -> dict[str, Any]:
    """Return LeanMill state for the Workbench proof section."""

    formalization_root = repo / "ztare_proofs" / "leanmill-formalizations"
    analytics_root = repo / "analytics" / "public" / "leanmill"
    query_root = repo / "analytics" / "public" / "queries"
    experiments_root = repo / "projects" / "leanmill_experiments" / "public"

    lean_files = (
        sorted(path for path in formalization_root.rglob("*.lean") if path.is_file())
        if formalization_root.exists()
        else []
    )
    blueprint_files = (
        sorted((formalization_root / "blueprints").glob("*.md"))
        if (formalization_root / "blueprints").exists()
        else []
    )
    ui_state_path = query_root / "leanmill_ui_state.json"
    solver_results_path = query_root / "leanmill_solver_lane_results.json"
    typed_exits_path = query_root / "leanmill_solver_lane_typed_exits.json"
    closure_cert_path = query_root / "adhoc_closure_certificates.jsonl"
    claim_register_path = repo / "docs" / "public_claim_register.md"

    ui_state = read_json_object(ui_state_path, storage=storage)
    solver_results = read_json_object(solver_results_path, storage=storage)
    typed_exits = read_json_object(typed_exits_path, storage=storage)
    closure_certs = read_jsonl_objects(closure_cert_path, storage=storage, limit=8)
    target_history_path = workbench_root(repo) / "leanmill_blueprint_receipts.jsonl"
    latest_target_path = workbench_root(repo) / "latest_leanmill_blueprint.json"
    target_history = read_jsonl_objects(target_history_path, storage=storage, limit=8)
    recent_jobs = latest_jobs(repo=repo, limit=8)
    solver_rows = solver_results.get("results") if isinstance(solver_results.get("results"), list) else []
    typed_exit_rows = typed_exits.get("exits") if isinstance(typed_exits.get("exits"), list) else []
    lane_b = ui_state.get("lane_b") if isinstance(ui_state.get("lane_b"), dict) else {}
    corpus_mandates = ui_state.get("corpus_mandates") if isinstance(ui_state.get("corpus_mandates"), dict) else {}
    mandates = corpus_mandates.get("mandates") if isinstance(corpus_mandates.get("mandates"), list) else []

    receipt_paths = [
        analytics_root / "results" / "governance_redteam.md",
        analytics_root / "results" / "certified_faithfulness_demo.md",
        analytics_root / "results" / "certify_policy_corpus_run.md",
        analytics_root / "results" / "decidability_router.md",
        analytics_root / "results" / "iam_refinement_run.md",
        query_root / "leanmill_solver_lane_typed_exits.json",
        query_root / "leanmill_ui_state.json",
        query_root / "adhoc_closure_certificates.jsonl",
    ]
    experiment_paths = sorted(experiments_root.glob("*.py")) if experiments_root.exists() else []
    available_receipts = [path for path in receipt_paths if path.exists()]

    launch_actions = [
        {
            "id": "write_target",
            "label": "Write target and notes",
            "status": "enabled",
            "reason": "Saves a formal target, research notes, and saved history. It does not launch a proof job.",
        },
        {
            "id": "autoformalize_from_notes",
            "label": "Autoformalize from notes",
            "status": "enabled",
            "route": "POST /api/leanmill/autoformalize-notes",
            "reason": "Starts a background job from a saved target-and-notes file and writes job, log, result, and saved-history files.",
        },
        {
            "id": "solve_ad_hoc",
            "label": "Solve ad hoc target",
            "status": "enabled",
            "route": "POST /api/leanmill/solve-adhoc",
            "reason": "Starts a governed proof attempt for a selected Lean file and records the job outputs.",
        },
    ]
    work_items: list[dict[str, Any]] = []
    for path in blueprint_files[:8]:
        work_items.append(
            {
                "id": f"target:{path.stem}",
                "kind": "target",
                "label": display_label(path.stem.removesuffix("_blueprint")).title(),
                "status": "draft",
                "path": repo_rel(path, storage=storage),
                "action_label": "Open target",
            }
        )
    for path in lean_files[:8]:
        work_items.append(
            {
                "id": f"formalization:{path.stem}",
                "kind": "formalization",
                "label": display_label(path.stem).title(),
                "status": "formal file",
                "path": repo_rel(path, storage=storage),
                "action_label": "Open formalization",
            }
        )
    for row in typed_exit_rows[:4]:
        if not isinstance(row, dict):
            continue
        target = str(row.get("target") or row.get("name") or row.get("next_lever") or "").strip()
        if not target:
            continue
        work_items.append(
            {
                "id": f"typed_exit:{target}",
                "kind": "outcome",
                "label": display_label(target),
                "status": display_label(row.get("credit_status") or row.get("typed_exit_kind") or "outcome"),
                "path": repo_rel(typed_exits_path, storage=storage),
                "action_label": "Open outcome file",
            }
        )

    current_status = "inspectable"
    if not lean_files and not available_receipts and not ui_state:
        current_status = "not loaded"
    return {
        "schema": LEANMILL_STATE_SCHEMA,
        "ok": True,
        "mode": "inspect_and_write_targets",
        "status": current_status,
        "title": "LeanMill",
        "summary": "Write formalization targets with research notes, inspect proof files, and see which attempts are ready to trust.",
        "storage": {
            "scope": "leanmill",
            "primary_root": repo_rel(formalization_root, storage=storage),
            "target_root": repo_rel(formalization_root / "blueprints", storage=storage),
            "blueprint_root": repo_rel(formalization_root / "blueprints", storage=storage),
            "history_root": repo_rel(workbench_root(repo), storage=storage),
            "autoresearch_projects_root": "projects/",
            "project_root_template": "projects/{project}/leanmill",
            "note": "LeanMill can be used globally or from a selected project. Project-local targets live under projects/<project>/leanmill/.",
        },
        "work_items": work_items[:16],
        "boundary": {
            "writes_project_files": False,
            "writes_repo_files": True,
            "browser_writes": False,
            "launch_enabled": False,
            "background_launch_enabled": True,
            "target_write_enabled": True,
            "target_boundary": "Saved targets and research notes write to ztare_proofs/leanmill-formalizations/blueprints and append saved history.",
            "blueprint_write_enabled": True,
            "blueprint_boundary": "Saved targets and research notes write to ztare_proofs/leanmill-formalizations/blueprints and append saved history.",
            "launch_boundary": "Proof work starts as a background job and writes job, result, stdout, stderr, and saved-history files.",
        },
        "claim_boundary": {
            "current_claim": "Formal work can be inspected through saved records and curated Lean files.",
            "non_claims": [
                "This view does not claim benchmark improvement.",
                "This view does not launch distributed LeanMill jobs.",
                "Unchecked proof candidates stay as guidance until accepted records exist.",
            ],
            "source": repo_rel(claim_register_path, storage=storage),
        },
        "formalizations": {
            "kind": "examples",
            "label": "Example formalizations",
            "note": "Curated showcase blueprints and Lean files. Read-only references, not user project work.",
            "root": repo_rel(formalization_root, storage=storage),
            "lean_file_count": len(lean_files),
            "target_count": len(blueprint_files),
            "blueprint_count": len(blueprint_files),
            "lean_files": [file_row(path, root=formalization_root, storage=storage) for path in lean_files[:12]],
            "targets": [file_row(path, root=formalization_root, storage=storage) for path in blueprint_files[:12]],
            "blueprints": [file_row(path, root=formalization_root, storage=storage) for path in blueprint_files[:12]],
        },
        "project_areas": project_areas_payload(repo, storage=storage),
        "target_writes": target_write_payload(target_history, target_history_path, latest_target_path, storage=storage),
        "blueprint_writes": blueprint_write_payload(target_history, target_history_path, latest_target_path, storage=storage),
        "public_receipts": {
            "available_count": len(available_receipts),
            "paths": [repo_rel(path, storage=storage) for path in available_receipts],
            "experiment_scripts": [repo_rel(path, storage=storage) for path in experiment_paths],
        },
        "ui_state": ui_state_payload(ui_state, ui_state_path, lane_b, mandates, storage=storage),
        "solver_lane": solver_lane_payload(solver_results, solver_results_path, solver_rows, storage=storage),
        "typed_exits": typed_exits_payload(typed_exits, typed_exits_path, typed_exit_rows, storage=storage),
        "closure_certificates": {
            "path": repo_rel(closure_cert_path, storage=storage),
            "recent_count": len(closure_certs),
        },
        "jobs": jobs_payload(recent_jobs, repo=repo, storage=storage),
        "launch_actions": launch_actions,
    }


def target_write_payload(
    target_history: list[dict[str, Any]],
    target_history_path: Path,
    latest_target_path: Path,
    *,
    storage: Any,
) -> dict[str, Any]:
    return {
        "enabled": True,
        "route": "POST /api/leanmill/target",
        "compatibility_route": "POST /api/leanmill/blueprint",
        "cli": "ztare leanmill target --title <title> --target <statement> --notes-file <notes.md> --json",
        "project_cli": "ztare leanmill target --project <project> --title <title> --target <statement> --notes-file <notes.md> --json",
        "autoformalize_cli": "ztare leanmill autoformalize-notes <target-notes.md>",
        "autoformalize_job_cli": "ztare leanmill workbench-action autoformalize-notes <target-notes.md> --save --json",
        "solve_adhoc_cli": "ztare leanmill solve-adhoc --target <decl_name> --source-file <target.lean>",
        "target_template": "ztare_proofs/leanmill-formalizations/blueprints/{slug}_blueprint.md",
        "history_path": repo_rel(target_history_path, storage=storage),
        "receipt_path": repo_rel(target_history_path, storage=storage),
        "latest_path": repo_rel(latest_target_path, storage=storage),
        "recent_count": len(target_history),
        "recent": [
            {
                "applied_at": str(row.get("applied_at") or ""),
                "slug": str(row.get("slug") or ""),
                "title": str(row.get("title") or ""),
                "target_path": str(row.get("target_path") or row.get("blueprint_path") or ""),
                "content_changed": bool(row.get("content_changed")),
            }
            for row in target_history
            if isinstance(row, dict)
        ],
    }


def blueprint_write_payload(
    target_history: list[dict[str, Any]],
    target_history_path: Path,
    latest_target_path: Path,
    *,
    storage: Any,
) -> dict[str, Any]:
    return {
        "enabled": True,
        "route": "POST /api/leanmill/target",
        "compatibility_route": "POST /api/leanmill/blueprint",
        "cli": "ztare leanmill target --title <title> --target <statement> --notes-file <notes.md> --json",
        "project_cli": "ztare leanmill target --project <project> --title <title> --target <statement> --notes-file <notes.md> --json",
        "target_template": "ztare_proofs/leanmill-formalizations/blueprints/{slug}_blueprint.md",
        "receipt_path": repo_rel(target_history_path, storage=storage),
        "latest_path": repo_rel(latest_target_path, storage=storage),
        "recent_count": len(target_history),
        "recent": [
            {
                "applied_at": str(row.get("applied_at") or ""),
                "slug": str(row.get("slug") or ""),
                "title": str(row.get("title") or ""),
                "blueprint_path": str(row.get("blueprint_path") or row.get("target_path") or ""),
                "content_changed": bool(row.get("content_changed")),
            }
            for row in target_history
            if isinstance(row, dict)
        ],
    }


def ui_state_payload(
    ui_state: dict[str, Any],
    ui_state_path: Path,
    lane_b: dict[str, Any],
    mandates: list[Any],
    *,
    storage: Any,
) -> dict[str, Any]:
    return {
        "available": bool(ui_state),
        "path": repo_rel(ui_state_path, storage=storage),
        "generated_at": str(ui_state.get("generated_at") or ""),
        "lane_b": {
            "available": bool(lane_b.get("available")),
            "targets": lane_b.get("n_targets"),
            "audit_clean": lane_b.get("audit_clean"),
            "status_summary": lane_b.get("summary_by_status") if isinstance(lane_b.get("summary_by_status"), dict) else {},
        },
        "mandates": [
            {
                "mandate_id": str(row.get("mandate_id") or ""),
                "status": str(row.get("status") or ""),
                "row_count": row.get("row_count"),
                "credit_lanes_allowed": row.get("credit_lanes_allowed") or [],
            }
            for row in mandates[:6]
            if isinstance(row, dict)
        ],
    }


def solver_lane_payload(
    solver_results: dict[str, Any],
    solver_results_path: Path,
    solver_rows: list[Any],
    *,
    storage: Any,
) -> dict[str, Any]:
    return {
        "available": bool(solver_results),
        "path": repo_rel(solver_results_path, storage=storage),
        "generated_at": str(solver_results.get("generated_at") or ""),
        "credit_boundary": str(solver_results.get("credit_boundary") or ""),
        "result_count": len(solver_rows),
        "recent": [
            {
                "target": str(row.get("target_name") or row.get("name") or ""),
                "outcome": str(row.get("outcome") or ""),
                "provider": str(row.get("provider") or ""),
                "compile_ok": row.get("compile_ok"),
            }
            for row in solver_rows[:8]
            if isinstance(row, dict)
        ],
    }


def typed_exits_payload(
    typed_exits: dict[str, Any],
    typed_exits_path: Path,
    typed_exit_rows: list[Any],
    *,
    storage: Any,
) -> dict[str, Any]:
    return {
        "available": bool(typed_exits),
        "path": repo_rel(typed_exits_path, storage=storage),
        "count": len(typed_exit_rows),
        "recent": [
            {
                "target": str(row.get("target_name") or row.get("attempt_id") or ""),
                "typed_exit_kind": str(row.get("typed_exit_kind") or ""),
                "credit_status": str(row.get("credit_status") or ""),
                "next_lever": str(row.get("next_lever") or ""),
            }
            for row in typed_exit_rows[:8]
            if isinstance(row, dict)
        ],
    }


def jobs_payload(recent_jobs: list[dict[str, Any]], *, repo: Path, storage: Any) -> dict[str, Any]:
    root = workbench_root(repo)
    return {
        "history_path": repo_rel(root / "leanmill_action_history.jsonl", storage=storage),
        "latest_path": repo_rel(root / "latest_leanmill_action.json", storage=storage),
        "job_root": repo_rel(root / "jobs", storage=storage),
        "recent": [
            {
                "action": str(row.get("action") or ""),
                "label": str(row.get("label") or ""),
                "status": str(row.get("status") or ""),
                "created_at": str(row.get("created_at") or ""),
                "started_at": str(row.get("started_at") or ""),
                "target_name": str(row.get("target_name") or ""),
                "notes_path": str(row.get("notes_path") or ""),
                "source_file": str(row.get("source_file") or ""),
                "job_path": str((row.get("paths") or {}).get("job") or row.get("job_path") or ""),
                "result_path": str((row.get("paths") or {}).get("result") or row.get("result_path") or ""),
                "stdout_path": str((row.get("paths") or {}).get("stdout") or ""),
                "stderr_path": str((row.get("paths") or {}).get("stderr") or ""),
            }
            for row in recent_jobs
            if isinstance(row, dict)
        ],
    }
