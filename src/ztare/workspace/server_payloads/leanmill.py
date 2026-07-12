"""LeanMill payloads for the local Workbench API."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from ztare.leanmill.workbench_actions import latest_jobs, repo_env, start_action
from ztare.leanmill.workbench_target import (
    TARGET_HISTORY_SCHEMA,
    list_project_leanmill_areas,
    scaffold_project_leanmill_area,
    target_payload,
)


LEANMILL_STATE_SCHEMA = "ztare-forensic-workbench-leanmill-state-v1"
CAMPAIGNS_SCHEMA = "ztare-forensic-workbench-leanmill-campaigns-v1"
CAMPAIGN_DETAIL_SCHEMA = "ztare-forensic-workbench-leanmill-campaign-detail-v1"
JOURNAL_TAIL_LIMIT = 20


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


def axiompack_campaign_root() -> Path:
    # ponytail: hardcoded to match `ztare.leanmill.cli`'s own `--output-root` default exactly, so a
    # workbench-triggered run and this list endpoint always agree without new config to keep in sync.
    # Upgrade to an env override if a second campaign root is ever needed.
    return Path("/tmp/axiompack_campaigns")


def resolve_campaign_dir(dir_param: Any) -> Path:
    """Validate a campaign `dir` request field: must resolve under the campaign root (no path
    traversal) and must already exist. Shared by every per-campaign action below."""
    raw = str(dir_param or "").strip()
    if not raw:
        raise ValueError("dir is required")
    directory = Path(raw).resolve()
    root = axiompack_campaign_root().resolve()
    if directory != root and root not in directory.parents:
        raise ValueError("dir must be a campaign attempt directory under the campaign root")
    if not directory.is_dir():
        raise ValueError(f"campaign attempt directory not found: {directory}")
    return directory


def campaigns_list_payload() -> dict[str, Any]:
    """List AxiomPack frontier-campaign attempt dirs under the shared campaign root, each with its
    `frontier_campaign_status` headline. Pure directory scan + the existing read-model per attempt —
    no state of our own (GP-251 M6)."""
    from ztare.leanmill.common import read_json
    from ztare.leanmill.frontier_campaign_actions import frontier_campaign_status

    root = axiompack_campaign_root()
    rows: list[dict[str, Any]] = []
    if root.is_dir():
        attempt_dirs = sorted(
            (path for path in root.iterdir() if path.is_dir()),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        for directory in attempt_dirs:
            manifest = read_json(directory / "campaign_manifest.json", {})
            if isinstance(manifest, dict) and manifest.get("lane") == "formalize":
                continue  # formalize-lane campaigns already show under Proof status
            if not (directory / "run.json").exists() and not (directory / "budget.json").exists():
                continue  # not a campaign attempt directory
            try:
                status = frontier_campaign_status(directory)
            except Exception as exc:  # noqa: BLE001 — one unreadable attempt shouldn't blank the list
                rows.append({"attempt_dir": str(directory), "status": "unreadable", "error": str(exc)})
                continue
            rows.append(
                {
                    "attempt_dir": status["attempt_dir"],
                    "campaign_id": status.get("campaign_id"),
                    "status": status.get("status"),
                    "budget": status.get("budget") or {},
                    # Keep the list a useful cold-safe progress read model. These
                    # are already projected by frontier_campaign_status; exposing
                    # them here avoids a detail request just to draw a live row.
                    "run": status.get("run") or {},
                    "boundary_completion": status.get("boundary_completion") or {},
                    "adapter_forge_completion": status.get("adapter_forge_completion") or {},
                    "attempt_lease": status.get("attempt_lease") or {},
                }
            )
    return {
        "schema": CAMPAIGNS_SCHEMA,
        "ok": True,
        "root": str(root),
        "count": len(rows),
        "campaigns": rows,
    }


def journal_tail_payload(directory: Path, *, limit: int = JOURNAL_TAIL_LIMIT) -> dict[str, Any]:
    """Read-model over the campaign journal (§12): the last `limit` events, via the existing
    `TheoryCampaignJournal` reader — never re-parsed by hand."""
    from ztare.leanmill.theory_campaign_journal import TheoryCampaignJournal

    path = directory / "events.jsonl"
    events = TheoryCampaignJournal(path).replay() if path.exists() else ()
    tail = events[-limit:]
    return {
        "path": str(path),
        "total_count": len(events),
        "events": [event.to_json() for event in tail],
    }


def campaign_detail_payload(dir_param: Any) -> dict[str, Any]:
    """Full read-model for one campaign attempt: status + budget, the cold-safe inspection view, the raw
    budget caps (for a usage meter), and the journal tail. Every field is read straight off disk through
    the existing frontier_campaign_actions functions or a direct file read — nothing computed here."""
    from ztare.leanmill.common import read_json
    from ztare.leanmill.frontier_campaign_actions import (
        frontier_campaign_status,
        inspect_frontier_campaign,
    )

    directory = resolve_campaign_dir(dir_param)
    status = frontier_campaign_status(directory)
    try:
        inspection = inspect_frontier_campaign(directory)
    except ValueError:
        inspection = None  # budget ledger not written yet (very early campaign)
    budget_row = read_json(directory / "budget.json", {})
    return {
        "schema": CAMPAIGN_DETAIL_SCHEMA,
        "ok": True,
        "attempt_dir": str(directory),
        "status": status,
        "budget_caps": {
            "wall_clock_s": budget_row.get("wall_clock_s"),
            "hard_caps": budget_row.get("hard_caps") or {},
        }
        if budget_row
        else None,
        "inspection": inspection,
        "journal": journal_tail_payload(directory),
    }


def campaign_preflight_payload(request: dict[str, Any], *, repo: Path, storage: Any) -> dict[str, Any]:
    """Shell `ztare leanmill preflight <blueprint>` — validates a campaign contract with zero provider
    dispatch. Creates no attempt dir; nothing to poll afterward."""
    blueprint_raw = str(request.get("blueprint") or "").strip()
    if not blueprint_raw:
        raise ValueError("blueprint is required")
    blueprint_path = storage.resolve(blueprint_raw)
    if not blueprint_path.exists() or not blueprint_path.is_file():
        raise ValueError(f"blueprint not found: {storage.rel(blueprint_path)}")
    completed = subprocess.run(
        [sys.executable, "-m", "ztare.leanmill.cli", "preflight", storage.rel(blueprint_path)],
        cwd=str(repo),
        env=repo_env(repo),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if completed.returncode != 0:
        return {"ok": False, "error": (completed.stderr or completed.stdout or "preflight failed").strip()}
    try:
        parsed = json.loads((completed.stdout or "").strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError) as exc:
        return {"ok": False, "error": f"preflight produced no JSON: {exc}", "stdout": completed.stdout}
    return {"ok": True, **parsed}


def campaign_run_payload(request: dict[str, Any], *, repo: Path, storage: Any) -> dict[str, Any]:
    """Trigger the existing `ztare leanmill campaign` orchestration as a background job — the SAME
    async-job door `autoformalize-notes`/`solve-adhoc`/`ratify` already use. The heavy run lives entirely
    in that CLI process; this only starts and tracks it."""
    return start_action("campaign_run", request, repo=repo, storage=storage)


# ── Axiom-discovery blueprint authoring — author the lane:axiompack blueprint IN the workbench (no path typing).
#    A blueprint is a plain Markdown file (leanmill.campaign.v1 frontmatter + a prose research direction); these
#    payloads list/read/write it under the blueprints dir. The heavy work is still the CLI preflight/campaign —
#    this only edits the input file, no campaign state of its own.
DISCOVERY_BLUEPRINT_SCHEMA = "ztare-forensic-workbench-leanmill-blueprints-v1"

# Starting scaffold for a NEW axiom-discovery blueprint. Frontmatter is the shared control envelope with
# lane: axiompack; the body is the mathematical research direction. This alone is NOT a runnable campaign:
# source_mode: structure_first also requires a typed_blueprint.json (the formula grammar + model/observation
# strata AxiomPack searches over) saved next to this file and referenced by the `typed_blueprint:` field below
# — see research_areas/pre_registrations/axiompack_gp251_smoke_20260710/{campaign.md,typed_blueprint.json} for
# a worked example. Preflight is the validator: it will report "requires a structure-first typed blueprint"
# until that file exists and is wired in. Generated fields (frozen_context_ref) are omitted — the compiler
# produces them.
DISCOVERY_BLUEPRINT_TEMPLATE = """---
schema: leanmill.campaign.v1
lane: axiompack
profile: smoke_20m
source_mode: structure_first
created_by: user
typed_blueprint: typed_blueprint.json  # REQUIRED: author this file alongside the saved blueprint; Preflight fails without it
budget:
  wall_clock: 20m
  provider_calls: 16
  agent_turns: 16
stop:
  max_finalists: 8
  low_yield_patience: 3
  coverage_target: "0.9"
runtime:
  transport: subscription_agent_runtime
  profile: smoke
---

# Two-law theories over one binary operation

Explore the anonymous landscape of two-law theories for a single total binary
operation. Seek small, independent axiom pairs whose conjunction forces
consequences that neither law produces alone. Freeze the finalists and their
boundary questions before revealing any established theory names or literature —
that cold discipline is what makes this a discovery and not a lookup.

- Region: one set with one total binary operation (no assumed identity, inverse, or commutativity).
- Phenomenon: pairs of equational laws that jointly force new structure.
- Examples in scope: associativity + a fixed-point law; medial + idempotent.
- Out of scope: importing named textbook axiom lists, or any literature lookup before the finalist freeze.

Edit this region to your own, then Preflight (validates the contract, zero provider calls) and Run.
"""


def _blueprints_dir(repo: Path) -> Path:
    return repo / "ztare_proofs" / "leanmill-formalizations" / "blueprints"


def _blueprint_lane(text: str) -> str:
    """Sniff the declared lane from a blueprint's frontmatter (cheap, first ~40 lines)."""
    for line in text.splitlines()[:40]:
        s = line.strip()
        if s.startswith("lane:"):
            return s.split(":", 1)[1].strip() or "unknown"
    return "unknown"


def blueprint_list_payload(*, repo: Path, storage: Any) -> dict[str, Any]:
    """List saved blueprints (*.md) under the blueprints dir, each annotated with its declared lane, so the
    author can pick one to edit/launch instead of typing a path. Read-only. Ships the new-blueprint template."""
    directory = _blueprints_dir(repo)
    rows: "list[dict[str, Any]]" = []
    if directory.exists():
        for path in sorted(directory.glob("*.md")):
            try:
                lane = _blueprint_lane(storage.read_text(path))
            except Exception:  # noqa: BLE001
                lane = "unknown"
            rows.append({"path": storage.rel(path), "name": path.name, "lane": lane})
    return {"schema": DISCOVERY_BLUEPRINT_SCHEMA, "ok": True,
            "dir": storage.rel(directory), "blueprints": rows, "template": DISCOVERY_BLUEPRINT_TEMPLATE}


def blueprint_read_payload(request: dict[str, Any], *, repo: Path, storage: Any) -> dict[str, Any]:
    """Read one saved blueprint's Markdown for editing. Read-only; confined to the blueprints dir."""
    rel = str(request.get("path") or "").strip()
    if not rel:
        raise ValueError("path is required")
    path = storage.resolve(rel)
    directory = _blueprints_dir(repo).resolve()
    if directory not in path.resolve().parents:
        raise ValueError("blueprint path must live under the blueprints dir")
    if not path.exists() or not path.is_file():
        raise ValueError(f"blueprint not found: {storage.rel(path)}")
    text = storage.read_text(path)
    return {"ok": True, "path": storage.rel(path), "name": path.name, "text": text, "lane": _blueprint_lane(text)}


def _blueprint_slug(name: str, *, default: str = "campaign") -> str:
    import re

    slug = re.sub(r"\.md$", "", name)
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", slug).strip("_")
    return slug or default


def blueprint_save_payload(request: dict[str, Any], *, repo: Path, storage: Any) -> dict[str, Any]:
    """Write an authored blueprint's Markdown to blueprints/<slug>.md. Confined to the blueprints dir (slug is
    sanitized — no traversal); returns the rel path so Preflight/Run can target it. No provider calls."""
    name = str(request.get("name") or "").strip()
    text = request.get("text")
    if not name:
        raise ValueError("name is required")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("text is required")
    saved = _blueprints_dir(repo) / f"{_blueprint_slug(name)}.md"
    storage.write_text(saved, text)
    return {"ok": True, "saved": True, "path": storage.rel(saved), "name": saved.name, "lane": _blueprint_lane(text)}


def blueprint_draft_payload(request: dict[str, Any], *, repo: Path, storage: Any) -> dict[str, Any]:
    """Draft a lane:axiompack blueprint FROM A PLAIN-LANGUAGE DIRECTION — the NL-first door onto
    `ztare.leanmill.cli draft`, which shells the real explore_axiom_space compiler/reviewer role pair
    (frontier_agent_role + compile_frontier_blueprint) with zero navigation, then writes a
    structure_first blueprint + typed_blueprint.json sidecar Preflight/Run can replay deterministically.
    Runs as a BACKGROUND job (the compile makes live provider calls, so it must not block the request) —
    same job shape and spawn mechanics `campaign_run_payload` gets from `start_action`, reused directly
    here (`_base_job`/`write_job`/`append_history`/`action_write_boundary` are already action-agnostic)
    because `start_action`'s `build_job` dispatch is a closed registry of existing action names and
    registering a new one there is outside this door's file scope."""
    import subprocess
    import sys

    from ztare.leanmill.workbench_actions import (
        ACTION_SCHEMA,
        _base_job,
        action_write_boundary,
        append_history,
        repo_env,
        utc_now,
        write_job,
    )

    direction = str(request.get("direction") or "").strip()
    if not direction:
        raise ValueError("direction is required")
    profile = str(request.get("profile") or "smoke_20m").strip() or "smoke_20m"
    out_path = _blueprints_dir(repo) / f"{_blueprint_slug(str(request.get('name') or 'my_discovery'))}.md"

    job = _base_job("blueprint_draft", request, repo=repo, storage=storage)
    job.update(
        {
            "label": "Draft an axiom-discovery blueprint from a description",
            "direction": direction,
            "blueprint_path": storage.rel(out_path),
            "timeout_s": 300,
            "command": [
                sys.executable, "-m", "ztare.leanmill.cli", "draft", direction,
                "--out", storage.rel(out_path), "--profile", profile,
            ],
        }
    )
    confirmed = request.get("confirmed") is True
    job["requires_confirmation"] = not confirmed
    if not confirmed:
        return {
            "schema": ACTION_SCHEMA,
            "ok": True,
            "status": "needs_confirmation",
            "accepted": False,
            "requires_confirmation": True,
            "job": job,
            "write_boundary": action_write_boundary(job, repo=repo, storage=storage),
        }
    job["status"] = "starting"
    write_job(job, storage=storage)
    runner_cmd = [sys.executable, "-m", "ztare.leanmill.workbench_actions", "run-job", job["paths"]["job"]]
    process = subprocess.Popen(
        runner_cmd,
        cwd=str(repo),
        env=repo_env(repo),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    job["status"] = "running"
    job["started_at"] = utc_now()
    job["pid"] = process.pid
    job["runner_command"] = runner_cmd
    write_job(job, storage=storage)
    history = append_history(job, repo=repo, storage=storage)
    return {
        "schema": ACTION_SCHEMA,
        "ok": True,
        "status": "started",
        "accepted": True,
        "requires_confirmation": False,
        "job": job,
        "history": history,
        "write_boundary": action_write_boundary(job, repo=repo, storage=storage),
    }


def campaign_verify_payload(request: dict[str, Any]) -> dict[str, Any]:
    from ztare.leanmill.frontier_campaign_runner import execute_frontier_campaign_verification

    directory = resolve_campaign_dir(request.get("dir"))
    lean_root = str(request.get("lean_root") or "").strip() or None
    result = execute_frontier_campaign_verification(
        directory, with_lean=bool(request.get("with_lean")), lean_root=lean_root
    )
    return {"ok": True, **result}


def campaign_replay_payload(request: dict[str, Any]) -> dict[str, Any]:
    from ztare.leanmill.frontier_campaign_actions import replay_frontier_campaign

    directory = resolve_campaign_dir(request.get("dir"))
    result = replay_frontier_campaign(directory)
    return {"ok": True, **result}


def campaign_stop_payload(request: dict[str, Any]) -> dict[str, Any]:
    from ztare.leanmill.frontier_campaign_actions import request_frontier_campaign_stop

    directory = resolve_campaign_dir(request.get("dir"))
    authority_ref = str(request.get("authority_ref") or "").strip()
    if not authority_ref:
        raise ValueError("authority_ref is required to request a campaign stop")
    result = request_frontier_campaign_stop(directory, authority_ref=authority_ref)
    return {"ok": True, **result}


def campaign_retire_payload(request: dict[str, Any]) -> dict[str, Any]:
    from ztare.leanmill.frontier_campaign_actions import retire_frontier_campaign

    directory = resolve_campaign_dir(request.get("dir"))
    result = retire_frontier_campaign(
        directory,
        authority_ref=str(request.get("authority_ref") or "").strip(),
        reason=str(request.get("reason") or "").strip(),
    )
    return {"ok": True, **result}


# ponytail: recheck/interpret/resume all run their frontier-runner call SYNCHRONOUSLY, in-process, inside
# the request handler (matching campaign-verify's existing behavior) — Lean recompilation and the literature
# review model call both block until done. Acceptable for a local single-user workbench; make it a background
# job (the autoformalize-notes/campaign-run door) later if a run turns out to be slow enough to want polling.
def campaign_resume_payload(request: dict[str, Any]) -> dict[str, Any]:
    from ztare.leanmill.frontier_campaign_actions import frontier_campaign_status
    from ztare.leanmill.frontier_campaign_runner import resume_frontier_campaign_navigation

    directory = resolve_campaign_dir(request.get("dir"))
    resume_frontier_campaign_navigation(directory)
    return {"ok": True, **frontier_campaign_status(directory)}


def campaign_recover_payload(request: dict[str, Any]) -> dict[str, Any]:
    from ztare.leanmill.frontier_campaign_actions import frontier_campaign_status
    from ztare.leanmill.frontier_campaign_runner import materialize_frontier_navigation_from_journal

    directory = resolve_campaign_dir(request.get("dir"))
    materialize_frontier_navigation_from_journal(directory)
    return {"ok": True, **frontier_campaign_status(directory)}


def campaign_recheck_payload(request: dict[str, Any]) -> dict[str, Any]:
    from ztare.leanmill.frontier_campaign_runner import recheck_frontier_boundary_governance

    directory = resolve_campaign_dir(request.get("dir"))
    lean_root = str(request.get("lean_root") or "").strip()
    if not lean_root:
        raise ValueError("lean_root is required for a governance recheck")
    timeout_s = int(request.get("timeout_s") or 180)
    result = recheck_frontier_boundary_governance(directory, lean_root=lean_root, timeout_s=timeout_s)
    return {"ok": True, **result}


def campaign_interpret_payload(request: dict[str, Any]) -> dict[str, Any]:
    from ztare.leanmill.frontier_campaign_runner import run_post_freeze_literature_review

    directory = resolve_campaign_dir(request.get("dir"))
    model = str(request.get("model") or "").strip() or "gpt-5.5"
    reasoning_effort = str(request.get("reasoning_effort") or "").strip() or "medium"
    result = run_post_freeze_literature_review(
        directory,
        model=model,
        reasoning_effort=reasoning_effort,
        retry_inconclusive=bool(request.get("retry_inconclusive")),
    )
    return {"ok": True, **result}


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

    def audit_receipt(row: dict[str, Any]) -> dict[str, Any] | None:
        """Project the existing proof-audit receipt without inventing proof credit.

        The job is provider-neutral, but a ratification job has a domain artifact
        with three independent checks. Keep that detail behind a small read-model
        so the Workbench can show compile, axiom policy, and L3 closure separately.
        """
        if str(row.get("action") or "") != "proof_audit":
            return None
        expected = str(row.get("expected_artifact") or "").strip()
        if not expected:
            return {"status": "missing_path"}
        try:
            # The CLI read-only shim intentionally exposes only `read_text`/`rel`.
            # Keep the richer provider path first, with a bounded local fallback
            # for that shim rather than importing server storage into the CLI.
            if hasattr(storage, "is_file"):
                present = storage.is_file(expected)
                text = storage.read_text(expected) if present else ""
            else:
                candidate = Path(expected)
                candidate = candidate if candidate.is_absolute() else repo / candidate
                present = candidate.is_file()
                text = candidate.read_text(encoding="utf-8") if present else ""
            if not present:
                return {"status": "pending", "path": expected}
            payload = json.loads(text)
        except Exception as exc:  # noqa: BLE001 — an unreadable receipt is visible, never a pass
            return {"status": "unreadable", "path": expected, "error": f"{type(exc).__name__}: {exc}"}
        if not isinstance(payload, dict):
            return {"status": "unreadable", "path": expected, "error": "receipt is not an object"}
        compile_payload = payload.get("compile") if isinstance(payload.get("compile"), dict) else {}
        policy_payload = payload.get("kernel_axiom_policy") if isinstance(payload.get("kernel_axiom_policy"), dict) else {}
        l3_payload = payload.get("l3_audit") if isinstance(payload.get("l3_audit"), dict) else {}
        return {
            "status": str(payload.get("status") or "unknown"),
            "path": expected,
            "target_sha256": str(payload.get("target_sha256") or ""),
            "generated_at_epoch": payload.get("generated_at_epoch"),
            "compile": {"ok": compile_payload.get("ok")},
            "axioms": {"allowlist_ok": policy_payload.get("allowlist_ok")},
            "closure": {
                "status": str(l3_payload.get("status") or "unknown"),
                "confirmed_blockers": len(l3_payload.get("confirmed_blockers") or []),
                "review_flags": len(l3_payload.get("review_flags") or []),
            },
            # This is intentionally prominent in the payload: an audit is evidence,
            # not a governed proof-credit decision.
            "credit_boundary": str(payload.get("credit_boundary") or ""),
        }

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
                "finished_at": str(row.get("finished_at") or ""),
                "target_name": str(row.get("target_name") or ""),
                "notes_path": str(row.get("notes_path") or ""),
                "source_file": str(row.get("source_file") or ""),
                "job_path": str((row.get("paths") or {}).get("job") or row.get("job_path") or ""),
                "result_path": str((row.get("paths") or {}).get("result") or row.get("result_path") or ""),
                "stdout_path": str((row.get("paths") or {}).get("stdout") or ""),
                "stderr_path": str((row.get("paths") or {}).get("stderr") or ""),
                "audit_receipt": audit_receipt(row),
            }
            for row in recent_jobs
            if isinstance(row, dict)
        ],
    }
