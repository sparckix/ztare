#!/usr/bin/env python3
"""Print the Project Workbench state object for one project."""
from __future__ import annotations

import argparse
import json
from typing import Any

import forensic_workbench_snapshot as snapshot
import forensic_workbench_server as server
from ztare.workspace import claim_support as claim_support_core


def safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def nonempty(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return value is not None


def project_to_thesis_audit(state: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    actions = [item for item in state.get("actions") or [] if isinstance(item, dict)]
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
    next_action = state.get("next_action") if isinstance(state.get("next_action"), dict) else {}
    charter = state.get("charter") if isinstance(state.get("charter"), dict) else {}
    thesis = state.get("thesis") if isinstance(state.get("thesis"), dict) else {}
    thesis_support = state.get("thesis_support") if isinstance(state.get("thesis_support"), dict) else {}
    claim_cards = claim_support_core.claim_card_audit(thesis_support)
    sources = state.get("sources") if isinstance(state.get("sources"), dict) else {}
    evidence = state.get("evidence") if isinstance(state.get("evidence"), dict) else {}
    source_health = state.get("source_health") if isinstance(state.get("source_health"), dict) else {}
    source_health_issues = [item for item in source_health.get("issues") or [] if isinstance(item, dict)]
    source_health_issue_count = max(safe_int(source_health.get("issue_count")), len(source_health_issues))
    source_health_action_count = sum(
        1
        for item in actions
        if isinstance(item, dict)
        and str(item.get("id") or "").startswith("source_health_")
        and nonempty(item.get("workspace"))
        and nonempty(item.get("subsection"))
        and (nonempty(item.get("evidence_refs")) or nonempty(item.get("source")))
    )
    run = state.get("run") if isinstance(state.get("run"), dict) else {}
    report = state.get("report") if isinstance(state.get("report"), dict) else {}
    review = state.get("review") if isinstance(state.get("review"), dict) else {}
    research_map = state.get("research_map") if isinstance(state.get("research_map"), dict) else {}
    files = state.get("files") if isinstance(state.get("files"), dict) else {}
    recent_changes = state.get("recent_changes") if isinstance(state.get("recent_changes"), dict) else {}
    recovery = state.get("recovery") if isinstance(state.get("recovery"), dict) else {}
    has_recovery_connect_action = bool(recovery) and any(
        str(item.get("id") or "") == "add_intake"
        and isinstance(item.get("write_boundary"), dict)
        and (
            item["write_boundary"].get("write_paths")
            or item["write_boundary"].get("receipt_path")
        )
        for item in actions
    )
    recovery_waits_for_project_brief = has_recovery_connect_action and str(next_action.get("id") or "") == "connect_project"
    charter_visible_or_recoverable = (
        nonempty(charter.get("file"))
        and nonempty(charter.get("status"))
        and (charter.get("exists") is not False or has_recovery_connect_action)
    )
    charter_detail = str(charter.get("summary") or charter.get("status") or "")
    if charter.get("exists") is False and has_recovery_connect_action:
        charter_detail = "Project charter will be created when the project brief is saved."

    checks = [
        {
            "id": "project_object",
            "label": "Project object coherent",
            "ok": bool(contract.get("ok")),
            "detail": str(contract.get("summary") or ""),
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
            "ok": nonempty(thesis.get("text")) and nonempty(thesis.get("status")),
            "detail": str(thesis.get("status") or ""),
        },
        {
            "id": "source_and_evidence",
            "label": "Source and evidence state visible",
            "ok": nonempty(sources.get("status"))
            and (
                nonempty(evidence.get("status"))
                or nonempty(thesis_support.get("status"))
                or nonempty(thesis_support.get("display_status"))
            ),
            "detail": f"sources={sources.get('status') or ''}; evidence={evidence.get('status') or thesis_support.get('display_status') or thesis_support.get('status') or ''}",
        },
        {
            "id": "source_health",
            "label": "File and evidence warnings visible",
            "ok": nonempty(source_health.get("status")) and "issue_count" in source_health,
            "detail": str(source_health.get("summary") or ""),
        },
        {
            "id": "source_health_actions",
            "label": "File and evidence warning actions visible",
            "ok": recovery_waits_for_project_brief
            or source_health_issue_count == 0
            or source_health_action_count >= min(source_health_issue_count, len(source_health_issues) or source_health_issue_count),
            "detail": (
                "File and evidence warnings wait until the project brief is saved."
                if recovery_waits_for_project_brief
                else "No file/evidence warnings."
                if source_health_issue_count == 0
                else f"{source_health_action_count}/{source_health_issue_count} warning action(s) expose backing evidence"
            ),
        },
        {
            "id": "claim_cards",
            "label": "Claim cards visible",
            "ok": bool(claim_cards.get("ok")),
            "detail": str(claim_cards.get("detail") or ""),
        },
        {
            "id": "run_state",
            "label": "Run state visible",
            "ok": nonempty(run.get("status")) and ("run_count" in run or "latest_score" in run or "blocking" in run),
            "detail": str(run.get("summary") or run.get("status") or ""),
        },
        {
            "id": "report_state",
            "label": "Report readiness visible",
            "ok": nonempty(report.get("status")),
            "detail": str(report.get("summary") or report.get("status") or ""),
        },
        {
            "id": "research_map",
            "label": "Research map visible",
            "ok": recovery_waits_for_project_brief
            or research_map.get("schema") == server.RESEARCH_MAP_SCHEMA
            and safe_int(research_map.get("section_count")) > 0
            and isinstance(research_map.get("project_meaning"), dict)
            and isinstance(research_map.get("next_action"), dict),
            "detail": (
                "Research map waits until the project brief is saved."
                if recovery_waits_for_project_brief
                else str(research_map.get("summary") or "")
            ),
        },
        {
            "id": "next_action",
            "label": "Next action visible",
            "ok": nonempty(next_action.get("label")) and nonempty(next_action.get("workspace")),
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
            "ok": nonempty(recent_changes.get("summary")) or nonempty(recent_changes.get("latest_run")),
            "detail": str(recent_changes.get("summary") or ""),
        },
        {
            "id": "files",
            "label": "Project files visible",
            "ok": safe_int(files.get("item_count")) > 0 and nonempty(files.get("file_groups")),
            "detail": f"{safe_int(files.get('item_count'))} files; {safe_int(files.get('previewable_count'))} previewable",
        },
    ]
    if recovery:
        checks.append(
            {
                "id": "recovery_path",
                "label": "Recovery path visible",
                "ok": nonempty(recovery.get("intake_target"))
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


def project_state_for_args(args: argparse.Namespace) -> dict[str, Any]:
    project = snapshot.validate_project_slug(args.project)
    rubric = args.rubric or project
    intake = args.intake or snapshot.default_intake_for_project(project)
    payload = server.workflow_payload_for_project(
        project=project,
        rubric=rubric,
        intake=intake,
        renderer=args.renderer or snapshot.DEFAULT_RENDERER,
        mode=args.mode,
    )
    state = payload.get("project_state") if isinstance(payload.get("project_state"), dict) else {}
    contract = (
        payload.get("project_object_contract")
        if isinstance(payload.get("project_object_contract"), dict)
        else {}
    )
    contract_ok = bool(contract.get("ok")) if contract else bool(state)
    failed_count = contract.get("failed_count") if isinstance(contract.get("failed_count"), int) else (0 if contract_ok else None)
    failed_checks = contract.get("failed_checks") if isinstance(contract.get("failed_checks"), list) else []
    first_failed_check = failed_checks[0] if failed_checks and isinstance(failed_checks[0], dict) else {}
    next_action = state.get("next_action") if isinstance(state.get("next_action"), dict) else {}
    report = state.get("report") if isinstance(state.get("report"), dict) else {}
    recent_changes = state.get("recent_changes") if isinstance(state.get("recent_changes"), dict) else {}
    thesis = state.get("thesis") if isinstance(state.get("thesis"), dict) else {}
    evidence = state.get("evidence") if isinstance(state.get("evidence"), dict) else {}
    sources = state.get("sources") if isinstance(state.get("sources"), dict) else {}
    run = state.get("run") if isinstance(state.get("run"), dict) else {}
    files = state.get("files") if isinstance(state.get("files"), dict) else {}
    formalization = state.get("formalization") if isinstance(state.get("formalization"), dict) else {}
    research_map = state.get("research_map") if isinstance(state.get("research_map"), dict) else {}
    file_groups = files.get("file_groups") if isinstance(files.get("file_groups"), list) else []
    file_summary = (
        f"{safe_int(files.get('item_count'))} files; "
        f"{safe_int(files.get('previewable_count'))} previewable; "
        f"{safe_int(files.get('missing_count'))} missing"
        if files
        else ""
    )
    project_audit = project_to_thesis_audit(state, contract)
    return {
        "ok": contract_ok and bool(project_audit.get("ok")),
        "schema": "ztare-forensic-workbench-project-state-cli-v1",
        "served_from": "local_cli",
        "project": project,
        "rubric": rubric,
        "intake": intake,
        "status": "ready" if contract_ok else "attention",
        "failed_check_count": failed_count,
        "failed_checks": failed_checks,
        "first_failed_check": first_failed_check,
        "project_to_thesis_audit": project_audit,
        "next_action": next_action,
        "report": report,
        "recent_changes": recent_changes,
        "files": {
            "schema": str(files.get("schema") or ""),
            "item_count": safe_int(files.get("item_count")),
            "previewable_count": safe_int(files.get("previewable_count")),
            "missing_count": safe_int(files.get("missing_count")),
            "file_groups": [
                {
                    "id": str(group.get("id") or ""),
                    "label": str(group.get("label") or ""),
                    "count": safe_int(group.get("count")),
                    "previewable_count": safe_int(group.get("previewable_count")),
                    "missing_count": safe_int(group.get("missing_count")),
                    "action": group.get("action") if isinstance(group.get("action"), dict) else {},
                }
                for group in file_groups
                if isinstance(group, dict)
            ],
        },
        "summary": {
            "thesis": str(thesis.get("text") or ""),
            "sources": str(sources.get("status") or ""),
            "evidence": str(evidence.get("status") or ""),
            "run": str(run.get("status") or ""),
            "report": str(report.get("status") or ""),
            "formalization": str(formalization.get("summary") or formalization.get("status") or ""),
            "research_map": str(research_map.get("summary") or research_map.get("status") or ""),
            "files": file_summary,
            "next_action": str(next_action.get("label") or ""),
            "latest_change": str(recent_changes.get("summary") or ""),
        },
        "workflow_schema": payload.get("schema"),
        "project_state": state,
        "project_object_contract": contract,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=snapshot.DEFAULT_PROJECT, help="Project slug under projects/.")
    parser.add_argument("--rubric", help="Rubric slug. Defaults to --project.")
    parser.add_argument("--intake", help="Project intake path. Defaults to the project's intake.")
    parser.add_argument("--renderer", default=snapshot.DEFAULT_RENDERER)
    parser.add_argument("--mode", choices=("fast", "full"), default="full")
    parser.add_argument("--json", action="store_true", help="Accepted for consistency; output is always JSON.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero if the shared project object is not coherent.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = project_state_for_args(args)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload.get("ok") or not args.strict else 1


if __name__ == "__main__":
    raise SystemExit(main())
